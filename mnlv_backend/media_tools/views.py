from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .services import MediaService
import os
from pathlib import Path

class MediaConvertWavView(APIView):
    """
    Endpoint POST /api/media/convert-wav/
    Upload un fichier et le retourne converti en WAV.
    """
    parser_classes = [MultiPartParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file_obj = request.data.get('file')
        if not file_obj:
            return Response({"error": "Aucun fichier fourni"}, status=status.HTTP_400_BAD_REQUEST)

        # Sauvegarde temporaire
        path = default_storage.save(f'tmp/convert_{file_obj.name}', ContentFile(file_obj.read()))
        full_path = os.path.join(default_storage.location, path)

        try:
            wav_path = MediaService.convert_to_wav(full_path)
            relative_wav_path = os.path.relpath(wav_path, default_storage.location)
            
            return Response({
                "message": "Conversion réussie",
                "download_url": f"/media/{relative_wav_path}"
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            # On garde le fichier temporaire un moment ou on nettoie via une tâche Celery plus tard
            pass

class MediaEditTagsView(APIView):
    """
    Endpoint POST /api/media/edit-tags/
    Modifie les tags d'un fichier MP3 uploadé.
    """
    parser_classes = [MultiPartParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file_obj = request.data.get('file')
        if not file_obj:
            return Response({"error": "Aucun fichier fourni"}, status=status.HTTP_400_BAD_REQUEST)

        metadata = {
            'title': request.data.get('title'),
            'artist': request.data.get('artist'),
            'album': request.data.get('album'),
            'year': request.data.get('year'),
            'cover_url': request.data.get('cover_url'),
        }

        path = default_storage.save(f'tmp/edit_{file_obj.name}', ContentFile(file_obj.read()))
        full_path = os.path.join(default_storage.location, path)

        try:
            MediaService.update_metadata(full_path, metadata)
            relative_path = os.path.relpath(full_path, default_storage.location)
            
            return Response({
                "message": "Tags mis à jour avec succès",
                "download_url": f"/media/{relative_path}"
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
