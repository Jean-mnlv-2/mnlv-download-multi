import os
import shutil
import yt_dlp
import requests
from pathlib import Path
from django.conf import settings
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
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        if not shutil.which("ffmpeg"):
            raise RuntimeError("FFmpeg non trouvé. Indispensable pour la conversion/tagging.")

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            p_str = d.get('_percent_str', '0%').replace('%', '').strip()
            try:
                p = int(float(p_str))
                weighted_p = int(p * 0.8)
                if weighted_p >= self.task.progress + 5 or weighted_p >= 75:
                    self.task.progress = weighted_p
                    self.task.save(update_fields=['progress'])
            except:
                pass
        elif d['status'] == 'finished':
            if self.task.progress < 80:
                self.task.progress = 80
                self.task.save(update_fields=['progress'])

    def process(self):
        try:
            self.task.status = DownloadTask.Status.PROCESSING
            self.task.save(update_fields=['status'])

            provider = ProviderFactory.get_provider(self.task.original_url)
            metadata = provider.get_track_info_cached(self.task.original_url)
            
            track_meta = None
            if metadata.isrc:
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

            is_video_mode = (
                self.task.media_type == DownloadTask.MediaType.VIDEO or 
                (metadata.is_video and self.task.prefer_video)
            )
            
            ext = "mp3" if not is_video_mode else "mp4"
            safe_name = f"{metadata.artist} - {metadata.title}.{ext}".replace("/", "_").replace("\\", "_")
            final_dest = Path(settings.MEDIA_ROOT) / "downloads" / safe_name
            
            if final_dest.exists():
                self.task.result_file = f"downloads/{safe_name}"
                self.task.status = DownloadTask.Status.COMPLETED
                self.task.progress = 100
                self.task.save(update_fields=['result_file', 'status', 'progress'])
                return

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
                        'preferredcodec': 'mp3',
                        'preferredquality': self.task.quality or '192',
                    }],
                }
            else:
                res = self.task.quality if self.task.quality in ['360', '720', '1080'] else '720'
                ydl_opts = {
                    'format': f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'outtmpl': output_template,
                    'noplaylist': True,
                    'progress_hooks': [self._progress_hook],
                    'merge_output_format': 'mp4',
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([search_query])

            final_file = self.temp_dir / f"{self.task.id}.{ext}"
            if not final_file.exists():
                found = list(self.temp_dir.glob(f"{self.task.id}.*"))
                if found: final_file = found[0]
                else: raise FileNotFoundError("Le moteur n'a pas pu générer le fichier final.")

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

        except Exception as e:
            self.task.status = DownloadTask.Status.FAILED
            self.task.error_message = str(e)
            self.task.save(update_fields=['status', 'error_message'])
            raise e
        finally:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
