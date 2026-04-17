from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser
from .services import FileParserService
from .models import PendingFileUpload
from .tasks import process_csv_file_task
import base64

class CSVUploadView(APIView):
    """
    Endpoint POST /api/csv/upload/
    Reçoit un fichier CSV, l'analyse, persiste le résultat et retourne l'aperçu.
    """
    parser_classes = [MultiPartParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        file_obj = request.data.get('file')
        
        if not file_obj:
            return Response({"error": "Aucun fichier fourni"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            track_list = FileParserService.parse_file(file_obj)
            resolved_tracks = FileParserService.resolve_tracks(track_list)
            
            if not resolved_tracks:
                return Response({"error": "Aucun morceau valide trouvé dans le fichier"}, status=status.HTTP_400_BAD_REQUEST)

            PendingFileUpload.objects.create(
                user=request.user,
                filename=file_obj.name,
                data=resolved_tracks
            )

            return Response({
                "message": f"Fichier analysé : {len(resolved_tracks)} morceaux trouvés.",
                "tracks": resolved_tracks
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Erreur lors du traitement du fichier : {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PendingUploadsView(APIView):
    """
    Endpoint GET /api/csv/pending/
    Récupère les uploads en attente de l'utilisateur.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
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
