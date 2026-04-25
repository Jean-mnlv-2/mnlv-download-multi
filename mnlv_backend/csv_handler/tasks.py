import base64
import io
import os
from celery import shared_task
from django.contrib.auth.models import User
from downloader.models import DownloadTask
from downloader.tasks import process_playlist_item
from .services import FileParserService
from core.logger_utils import get_mnlv_logger

logger = get_mnlv_logger("csv_tasks")

class SimpleFile:
    def __init__(self, content, name):
        self.content = content
        self.name = name
    def read(self):
        return self.content

@shared_task(name="csv_handler.tasks.process_csv_file_task", queue='low_priority')
def process_csv_file_task(user_id, file_content_b64, filename):
    """
    Traite un fichier CSV/Excel asynchronement :
    1. Parse le fichier
    2. Résout les titres (Spotify search si besoin)
    3. Crée les DownloadTasks en masse
    4. Lance le traitement Celery pour chaque tâche
    """
    try:
        user = User.objects.get(id=user_id)
        file_content = base64.b64decode(file_content_b64)
        
        file_obj = SimpleFile(file_content, filename)
        
        logger.info(f"Début traitement asynchrone pour {filename} (User: {user.username})")
        
        track_list = FileParserService.parse_file(file_obj)
        logger.info(f"{len(track_list)} lignes extraites de {filename}")
        
        max_tracks = int(os.getenv("MAX_PLAYLIST_TRACKS", "500"))
        track_list = track_list[:max_tracks]
        resolved_tracks = FileParserService.resolve_tracks(track_list)
        
        tasks_to_create = []
        for rt in resolved_tracks:
            if rt.get('status') == 'ready' and rt.get('url'):
                tasks_to_create.append(DownloadTask(
                    user=user,
                    original_url=rt['url'],
                    provider=rt.get('provider', 'unknown'),
                    media_type=DownloadTask.MediaType.AUDIO,
                ))
        
        if not tasks_to_create:
            logger.warning(f"Aucun morceau valide trouvé dans {filename}")
            return
            
        created_tasks = DownloadTask.objects.bulk_create(tasks_to_create)
        logger.info(f"{len(created_tasks)} tâches créées en masse pour {filename}")
        
        for task in created_tasks:
            process_playlist_item.delay(str(task.id))
            
        logger.info(f"Traitement asynchrone de {filename} terminé avec succès.")
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement asynchrone de {filename}: {str(e)}")
        raise
