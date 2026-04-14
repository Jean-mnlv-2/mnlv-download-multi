import os
import shutil
import time
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from celery import shared_task
from celery.utils.log import get_task_logger
from .engine import DownloadEngine
from .models import DownloadTask

logger = get_task_logger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue='high_priority'
)
def process_single_track(self, task_id: str):
    """
    Tâche Celery pour traiter un téléchargement unique.
    Utilise une queue prioritaire.
    """
    try:
        engine = DownloadEngine(task_id, logger=logger)
        engine.process()
    except Exception as exc:
        logger.error(f"Erreur dans la tâche {task_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@shared_task(
    bind=True,
    max_retries=2,
    queue='low_priority'
)
def process_playlist_item(self, task_id: str):
    """
    Tâche Celery pour traiter un élément d'une playlist.
    Utilise une queue de basse priorité pour ne pas bloquer les requêtes uniques.
    """
    try:
        engine = DownloadEngine(task_id, logger=logger)
        engine.process()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)

@shared_task(name="downloader.tasks.cleanup_old_files")
def cleanup_old_files():
    """
    Tâche périodique pour nettoyer les fichiers temporaires et les anciens téléchargements.
    """
    now = timezone.now()
    audio_minutes = int(os.getenv("FILE_CLEANUP_MINUTES", "30"))
    video_minutes = int(os.getenv("VIDEO_FILE_CLEANUP_MINUTES", "15"))
    tmp_minutes = int(os.getenv("TMP_CLEANUP_MINUTES", "60"))
    
    tmp_root = os.path.join(settings.MEDIA_ROOT, "tmp")
    if os.path.exists(tmp_root):
        for folder in os.listdir(tmp_root):
            folder_path = os.path.join(tmp_root, folder)
            if os.path.getmtime(folder_path) < (now - timedelta(minutes=tmp_minutes)).timestamp():
                shutil.rmtree(folder_path, ignore_errors=True)
                logger.info(f"Dossier temporaire supprimé : {folder}")

    tasks = DownloadTask.objects.all()
    deleted_count = 0
    for task in tasks:
        ttl_minutes = video_minutes if task.media_type == DownloadTask.MediaType.VIDEO else audio_minutes
        if task.created_at >= now - timedelta(minutes=ttl_minutes):
            continue
        if task.result_file:
            file_path = os.path.join(settings.MEDIA_ROOT, task.result_file.name)
            if os.path.exists(file_path):
                os.remove(file_path)
        task.delete()
        deleted_count += 1
    
    logger.info(f"Nettoyage terminé : {deleted_count} tâches supprimées.")
