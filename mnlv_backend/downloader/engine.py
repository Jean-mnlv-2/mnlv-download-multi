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
                        'preferredcodec': 'mp3' if self.task.media_type == DownloadTask.MediaType.AUDIO else 'wav',
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
                    'merge_output_format': 'mp4' if self.task.media_type == DownloadTask.MediaType.VIDEO else 'mkv',
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([search_query])

            downloaded_file = None
            for f in self.temp_dir.glob(f"{self.task.id}.*"):
                downloaded_file = f
                break
            
            if not downloaded_file:
                raise FileNotFoundError("Le moteur n'a pas pu télécharger le fichier source.")

            pro_formats = [
                DownloadTask.MediaType.FLAC, 
                DownloadTask.MediaType.ALAC, 
                DownloadTask.MediaType.OPUS, 
                DownloadTask.MediaType.AAC,
                DownloadTask.MediaType.WAV
            ]
            
            final_file = downloaded_file
            if self.task.media_type in pro_formats:
                self.logger.info(f"Conversion vers format Pro/WebRadio : {self.task.media_type}")
                final_file = Path(MediaService.convert_to_format(str(downloaded_file), self.task.media_type))

            if self.task.media_type in [DownloadTask.MediaType.AUDIO, DownloadTask.MediaType.VIDEO]:
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
