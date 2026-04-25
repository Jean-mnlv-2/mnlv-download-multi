import os
import shutil
import yt_dlp
import requests
from pathlib import Path
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import DownloadTask, TrackMetadata
from .providers.factory import ProviderFactory
from .matching.matcher import ISRCMatcher
from media_tools.services import MediaService
from core.logger_utils import get_mnlv_logger

class DownloadEngine:
    """
    Moteur de téléchargement optimisé.
    Support MP3/MP4, matching ISRC, cache disque et tagging complet.
    """

    def __init__(self, task_id: str, logger=None):
        self.task = DownloadTask.objects.get(id=task_id)
        self.logger = logger or get_mnlv_logger(f"engine.{task_id}")
        self.temp_dir = Path(settings.MEDIA_ROOT) / "tmp" / str(task_id)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.matcher = ISRCMatcher(logger=self.logger)
        self.channel_layer = get_channel_layer()
        self._check_ffmpeg()

    def _notify(self, message: str, status: str = None, progress: int = None, error: str = None, result_file: str = None, speed: str = None, eta: str = None):
        """Envoie une notification en temps réel via WebSocket"""
        data = {
            "task_id": str(self.task.id),
            "message": message,
            "status": status or self.task.status,
            "progress": progress if progress is not None else self.task.progress,
            "error": error or self.task.error_message,
            "result_file": result_file or (self.task.result_file.url if self.task.result_file else None),
            "speed": speed,
            "eta": eta
        }
        group_name = f"user_{self.task.user.id}_tasks"
        async_to_sync(self.channel_layer.group_send)(
            group_name,
            {
                "type": "task_update",
                "data": data
            }
        )

    def _check_ffmpeg(self):
        if not shutil.which("ffmpeg"):
            raise RuntimeError("FFmpeg non trouvé. Indispensable pour la conversion/tagging.")

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            p_str = d.get('_percent_str', '0%').replace('%', '').strip()
            speed = d.get('_speed_str', 'N/A').strip()
            eta = d.get('_eta_str', 'N/A').strip()
            
            try:
                # Forcer le rafraîchissement des métriques à chaque fois pour le frontend
                p = int(float(p_str))
                weighted_p = int(p * 0.8)
                self.task.progress = weighted_p
                self.task.save(update_fields=['progress'])
                self._notify(f"Téléchargement en cours...", progress=weighted_p, speed=speed, eta=eta)
            except:
                pass
        elif d['status'] == 'finished':
            if self.task.progress < 80:
                self.task.progress = 80
                self.task.save(update_fields=['progress'])
                self._notify("Téléchargement terminé, début de la conversion...", progress=80)

    def process(self):
        try:
            self.task.status = DownloadTask.Status.PROCESSING
            self.task.save(update_fields=['status'])
            self._notify("Initialisation du moteur...", progress=2)

            self._notify("Récupération des métadonnées du provider...", progress=5)
            provider = ProviderFactory.get_provider(self.task.original_url)
            metadata = provider.get_track_info_cached(self.task.original_url)
            
            track_meta = None
            if metadata.isrc:
                self._notify(f"ISRC identifié : {metadata.isrc}", progress=8)
                track_meta, _ = TrackMetadata.objects.update_or_create(
                    isrc=metadata.isrc,
                    defaults={ 
                        "title": metadata.title,
                        "artist": metadata.artist,
                        "album": metadata.album,
                        "release_year": metadata.release_year,
                        "cover_url": metadata.cover_url,
                    }
                )
            self.task.track = track_meta
            self.task.save(update_fields=['track'])
            self._notify(f"Titre : {metadata.title} - {metadata.artist}", progress=10)

            is_video_mode = (
                self.task.media_type in [DownloadTask.MediaType.VIDEO, DownloadTask.MediaType.MKV] or 
                (metadata.is_video and self.task.prefer_video)
            )
            
            if self.task.media_type == DownloadTask.MediaType.AUDIO:
                ext = "mp3"
            elif self.task.media_type == DownloadTask.MediaType.VIDEO:
                ext = "mp4"
            else:
                ext = self.task.media_type.lower()
            
            safe_name = f"{metadata.artist} - {metadata.title}.{ext}".replace("/", "_").replace("\\", "_")
            final_dest = Path(settings.MEDIA_ROOT) / "downloads" / safe_name
            
            if final_dest.exists():
                self.task.result_file = f"downloads/{safe_name}"
                self.task.status = DownloadTask.Status.COMPLETED
                self.task.progress = 100
                self.task.save(update_fields=['result_file', 'status', 'progress', 'updated_at'])
                self._notify("Fichier récupéré depuis le cache MNLV.", progress=100)
                return

            self._notify("Recherche de la meilleure correspondance sur YouTube...", progress=15)
            search_query = self.matcher.find_best_match(metadata)
            
            output_template = str(self.temp_dir / f"{self.task.id}.%(ext)s")
            
            if not is_video_mode:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': output_template,
                    'noplaylist': True,
                    'progress_hooks': [self._progress_hook],
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3' if self.task.media_type == DownloadTask.MediaType.AUDIO else 'wav',
                        'preferredquality': self.task.quality or '192',
                    }],
                    'ignoreerrors': True,
                }
            else:
                res = self.task.quality if self.task.quality in ['360', '720', '1080'] else '720'
                ydl_opts = {
                    'format': f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={res}]+bestaudio/best/best',
                    'outtmpl': output_template,
                    'noplaylist': True,
                    'progress_hooks': [self._progress_hook],
                    'merge_output_format': 'mp4' if self.task.media_type == DownloadTask.MediaType.VIDEO else 'mkv',
                    'ignoreerrors': True,
                }

            self._notify("Connexion aux serveurs de streaming...", progress=20)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([search_query])
                except yt_dlp.utils.DownloadError as e:
                    err_msg = str(e)
                    if "Geo-restricted" in err_msg:
                        raise ValueError("Contenu restreint géographiquement.")
                    elif "age restricted" in err_msg:
                        raise ValueError("Vérification d'âge requise par YouTube.")
                    elif "Copyright" in err_msg:
                        raise ValueError("Contenu bloqué par les droits d'auteur.")
                    raise ValueError(f"Erreur YouTube : {err_msg}")

            downloaded_file = None
            for f in self.temp_dir.glob(f"{self.task.id}.*"):
                downloaded_file = f
                break
            
            if not downloaded_file:
                self._notify("Tentative de secours sans filtres de format...", progress=25)
                ydl_opts['format'] = 'best'
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([search_query])
                
                for f in self.temp_dir.glob(f"{self.task.id}.*"):
                    downloaded_file = f
                    break

            if not downloaded_file:
                raise FileNotFoundError("Aucun flux compatible n'a pu être extrait.")

            self._notify("Traitement du fichier source...", progress=82)
            pro_formats = [
                DownloadTask.MediaType.FLAC, 
                DownloadTask.MediaType.ALAC, 
                DownloadTask.MediaType.OPUS, 
                DownloadTask.MediaType.AAC,
                DownloadTask.MediaType.WAV
            ]
            
            final_file = downloaded_file
            if self.task.media_type in pro_formats:
                self._notify(f"Encodage haute fidélité ({self.task.media_type})...", progress=85)
                final_file = Path(MediaService.convert_to_format(str(downloaded_file), self.task.media_type))

            if self.task.media_type in [DownloadTask.MediaType.AUDIO, DownloadTask.MediaType.VIDEO]:
                self._notify("Injection des métadonnées et de la pochette HD...", progress=90)
                MediaService.apply_metadata(
                    str(final_file), 
                    metadata.__dict__, 
                    is_video=is_video_mode
                )

            final_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(final_file), str(final_dest))
            
            self.task.result_file = f"downloads/{safe_name}"
            self.task.status = DownloadTask.Status.COMPLETED
            self.task.progress = 100
            self.task.save(update_fields=['result_file', 'status', 'progress'])
            self._notify("Téléchargement prêt !", progress=100)

        except Exception as e:
            self.task.status = DownloadTask.Status.FAILED
            self.task.error_message = str(e)
            self.task.save(update_fields=['status', 'error_message'])
            raise e
        finally:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
