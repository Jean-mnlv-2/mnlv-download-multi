import os
import shutil
import yt_dlp
import requests
from pathlib import Path
from django.conf import settings
from .models import DownloadTask, TrackMetadata
from .providers.factory import ProviderFactory
from .matching.matcher import ISRCMatcher
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TYER, APIC
from mutagen.mp4 import MP4, MP4Cover

class DownloadEngine:
    """
    Moteur de téléchargement optimisé.
    Support MP3/MP4, matching ISRC, cache disque et tagging complet.
    """

    def __init__(self, task_id: str, logger=None):
        self.task = DownloadTask.objects.get(id=task_id)
        self.logger = logger
        self.temp_dir = Path(settings.MEDIA_ROOT) / "tmp" / str(task_id)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.matcher = ISRCMatcher(logger=logger)
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
            metadata = provider.get_track_info(self.task.original_url)
            
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

            ext = "mp3" if self.task.media_type == DownloadTask.MediaType.AUDIO else "mp4"
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
            
            if self.task.media_type == DownloadTask.MediaType.AUDIO:
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

            self._apply_metadata(final_file, metadata, self.task.media_type)

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

    def _apply_metadata(self, file_path: Path, metadata, media_type):
        """Injection des tags et de la pochette"""
        try:
            if media_type == DownloadTask.MediaType.AUDIO:
                audio = MP3(file_path, ID3=ID3)
                try: audio.add_tags()
                except: pass
                audio.tags.add(TIT2(encoding=3, text=metadata.title))
                audio.tags.add(TPE1(encoding=3, text=metadata.artist))
                if metadata.album: audio.tags.add(TALB(encoding=3, text=metadata.album))
                if metadata.release_year: audio.tags.add(TYER(encoding=3, text=str(metadata.release_year)))
                if metadata.cover_url:
                    r = requests.get(metadata.cover_url, timeout=10)
                    if r.status_code == 200:
                        audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=r.content))
                audio.save()
            else:
                video = MP4(file_path)
                video["\xa9nam"] = metadata.title
                video["\xa9ART"] = metadata.artist
                if metadata.album: video["\xa9alb"] = metadata.album
                if metadata.release_year: video["\xa9day"] = str(metadata.release_year)
                if metadata.cover_url:
                    r = requests.get(metadata.cover_url, timeout=10)
                    if r.status_code == 200:
                        video["covr"] = [MP4Cover(r.content, imageformat=MP4Cover.FORMAT_JPEG)]
                video.save()
        except Exception as e:
            if self.logger: self.logger.warning(f"Tagging non bloquant échoué : {e}")
