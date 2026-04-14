from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser
from .services import FileParserService
from downloader.models import DownloadTask
from downloader.tasks import process_single_track

class CSVUploadView(APIView):
    """
    Endpoint POST /api/csv/upload/
    Reçoit un fichier CSV, l'analyse, cherche les morceaux sur Spotify et lance les téléchargements.
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

            return Response({
                "message": f"Fichier analysé : {len(resolved_tracks)} morceaux trouvés.",
                "tracks": resolved_tracks
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Erreur lors du traitement du fichier : {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
