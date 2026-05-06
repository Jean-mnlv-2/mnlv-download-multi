from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser
from .services import FileParserService
from .models import PendingFileUpload
from .tasks import process_csv_file_task
import base64

from datetime import timedelta
from django.utils import timezone

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class CSVUploadView(APIView):
    """
    Endpoint POST /api/csv/upload/
    Reçoit un fichier CSV, l'analyse, persiste le résultat et retourne l'aperçu.
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        file_obj = request.data.get('file')
        
        if not file_obj:
            return Response({
                "error": "Aucun fichier trouvé dans la requête. Assurez-vous d'utiliser le champ 'file'.",
                "code": "FILE_MISSING"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            track_list = FileParserService.parse_file(file_obj)
            
            if not track_list:
                return Response({
                    "error": "Le fichier est vide ou n'a pas pu être lu.",
                    "code": "FILE_EMPTY"
                }, status=status.HTTP_400_BAD_REQUEST)

            resolved_tracks = FileParserService.resolve_tracks(track_list)
            
            if not resolved_tracks:
                return Response({
                    "error": "Aucun morceau valide trouvé dans le fichier après analyse.",
                    "code": "NO_TRACKS_FOUND"
                }, status=status.HTTP_400_BAD_REQUEST)

            PendingFileUpload.objects.update_or_create(
                user=request.user,
                filename=file_obj.name,
                defaults={'data': resolved_tracks}
            )

            return Response({
                "message": f"Fichier analysé : {len(resolved_tracks)} morceaux trouvés.",
                "tracks": resolved_tracks,
                "filename": file_obj.name
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({
                "error": str(e),
                "code": "INVALID_FORMAT"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import logging
            logger = logging.getLogger("api")
            logger.exception("Error processing file upload")
            return Response({
                "error": f"Erreur interne lors du traitement : {str(e)}",
                "code": "INTERNAL_ERROR"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PendingUploadsView(APIView):
    """
    Endpoint GET /api/csv/pending/
    Récupère les uploads en attente de l'utilisateur.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cutoff = timezone.now() - timedelta(hours=24)
        PendingFileUpload.objects.filter(user=request.user, created_at__lt=cutoff).delete()

        uploads = PendingFileUpload.objects.filter(user=request.user)
        data = [
            {
                "id": str(u.id),
                "filename": u.filename,
                "tracks": u.data,
                "created_at": u.created_at
            }
            for u in uploads
        ]
        return Response(data)

    def delete(self, request):
        """Supprime tous les uploads en attente ou un ID spécifique via ?id="""
        upload_id = request.query_params.get('id')
        if upload_id:
            PendingFileUpload.objects.filter(user=request.user, id=upload_id).delete()
        else:
            PendingFileUpload.objects.filter(user=request.user).delete()
        return Response({"status": "deleted"}, status=status.HTTP_200_OK)
