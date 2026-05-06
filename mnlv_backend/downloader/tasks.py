import os
import shutil
from datetime import timedelta
from pathlib import Path
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
    queue='media_processing',
    rate_limit=os.getenv("DOWNLOAD_RATE_LIMIT_HIGH", None) or None,
)
def process_single_track(self, task_id: str):
    """
    Tâche Celery pour traiter un téléchargement unique.
    Utilise la queue 'media_processing' pour limiter la concurrence CPU (FFmpeg).
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
    queue='media_processing',
    rate_limit=os.getenv("DOWNLOAD_RATE_LIMIT_LOW", None) or None,
)
def process_playlist_item(self, task_id: str):
    """
    Tâche Celery pour traiter un élément d'une playlist.
    Utilise aussi la queue 'media_processing' pour le contrôle de concurrence.
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
    Améliorée pour inclure le monitoring de l'espace disque.
    """
    usage = shutil.disk_usage(settings.MEDIA_ROOT)
    free_gb = usage.free / (1024**3)
    percent_free = (usage.free / usage.total) * 100
    
    if percent_free < 10 or free_gb < 2:
        logger.warning(f"ESPACE DISQUE CRITIQUE : {free_gb:.2f} GB libres ({percent_free:.1f}%)")
        is_critical = True
    else:
        is_critical = False

    now = timezone.now()
    audio_ttl = timedelta(minutes=int(os.getenv("FILE_CLEANUP_MINUTES", "30")))
    video_ttl = timedelta(minutes=int(os.getenv("VIDEO_FILE_CLEANUP_MINUTES", "15")))
    tmp_ttl = timedelta(minutes=int(os.getenv("TMP_CLEANUP_MINUTES", "60")))
    
    if is_critical:
        audio_ttl = audio_ttl / 2
        video_ttl = video_ttl / 2
        tmp_ttl = tmp_ttl / 2
        logger.info("Nettoyage agressif activé suite à manque d'espace disque.")
    
    tmp_root = Path(settings.MEDIA_ROOT) / "tmp"
    if tmp_root.exists():
        for folder in tmp_root.iterdir():
            if folder.is_dir() and (now - timezone.datetime.fromtimestamp(folder.stat().st_mtime, tz=timezone.utc)) > tmp_ttl:
                shutil.rmtree(folder, ignore_errors=True)
                logger.info(f"Dossier temporaire orphelin supprimé : {folder.name}")

    expirations = [
        (DownloadTask.MediaType.AUDIO, audio_ttl),
        (DownloadTask.MediaType.VIDEO, video_ttl)
    ]
    
    total_deleted = 0
    for m_type, ttl in expirations:
        expired_tasks = DownloadTask.objects.filter(
            media_type=m_type,
            created_at__lt=now - ttl
        )
        
        for task in expired_tasks:
            if task.result_file:
                file_path = Path(settings.MEDIA_ROOT) / task.result_file.name
                if file_path.exists():
                    file_path.unlink()
            total_deleted += 1
            
        expired_tasks.delete()
    
    if total_deleted > 0:
        logger.info(f"Nettoyage terminé : {total_deleted} tâches et fichiers supprimés.")

