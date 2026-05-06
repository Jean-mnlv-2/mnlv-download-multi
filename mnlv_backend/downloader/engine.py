import os
import shutil
import yt_dlp
import requests
import hashlib
import re
import time
from pathlib import Path
from django.conf import settings
from .models import DownloadTask, TrackMetadata
from .providers.factory import ProviderFactory
from .providers.base import ProviderTrackMetadata, ProviderError, ProviderAuthError, ProviderRateLimitError, ProviderResourceNotFoundError, ProviderAPIError
from .matching.matcher import ISRCMatcher
from media_tools.services import MediaService
from core.logger_utils import get_mnlv_logger
from .realtime import default_notifier

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
        self._last_db_progress = int(self.task.progress or 0)
        self._last_progress_emit = 0
        self._check_ffmpeg()

    def _notify(self, message: str = None, *, force: bool = False, speed: str = None, eta: str = None):
        """Source unique des notifications WS (schéma normalisé + throttle)."""
        default_notifier.send(self.task, message=message, speed=speed, eta=eta, force=force)

    def _set_progress(self, progress: int, *, emit_message: str = None, speed: str = None, eta: str = None):
        progress = max(0, min(100, int(progress)))
        if progress == self._last_db_progress:
            return
        # n'écrit en DB que si changement >= 1%
        self.task.progress = progress
        DownloadTask.objects.filter(id=self.task.id).update(progress=progress)
        self._last_db_progress = progress
        # n'émet que si changement significatif (>=1%) ou étape clé via message
        if emit_message is not None or abs(progress - self._last_progress_emit) >= 1:
            self._notify(emit_message, speed=speed, eta=eta)
            self._last_progress_emit = progress

    def _set_status(self, status: str, *, message: str = None, force_emit: bool = True):
        if self.task.status == status:
            if message:
                self._notify(message)
            return
        self.task.status = status
        DownloadTask.objects.filter(id=self.task.id).update(status=status)
        if force_emit:
            self._notify(message, force=True)

    def _check_ffmpeg(self):
        if not shutil.which("ffmpeg"):
            raise RuntimeError("FFmpeg non trouvé. Indispensable pour la conversion/tagging.")

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            p_str = d.get('_percent_str', '0%').replace('%', '').strip()
            speed = d.get('_speed_str', 'N/A').strip()
            eta = d.get('_eta_str', 'N/A').strip()
            
            try:
                p = int(float(p_str))
                weighted_p = int(p * 0.8)
                self._set_progress(weighted_p, emit_message="Téléchargement en cours...", speed=speed, eta=eta)
            except:
                pass
        elif d['status'] == 'finished':
            if self._last_db_progress < 80:
                self._set_progress(80, emit_message="Téléchargement terminé, début de la conversion...")

    def _stable_cache_key(self, metadata: ProviderTrackMetadata, ext: str) -> str:
        """
        Clé stable pour éviter collisions artist-title.
        Priorise ISRC; sinon hash url+title+artist.
        """
        parts = [
            (metadata.isrc or "").strip().upper(),
            (metadata.artist or "").strip(),
            (metadata.title or "").strip(),
            str(self.task.media_type),
            str(self.task.quality or ""),
            "prefer_video=1" if self.task.prefer_video else "prefer_video=0",
            ext,
        ]
        raw = "|".join(parts)
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def _sanitize_filename(self, s: str) -> str:
        s = (s or "").strip()
        s = re.sub(r"[\\/:*?\"<>|]+", "_", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s[:180] if len(s) > 180 else s

    def _build_final_dest(self, metadata: ProviderTrackMetadata, ext: str) -> Path:
        cache_key = self._stable_cache_key(metadata, ext)
        display = self._sanitize_filename(f"{metadata.artist} - {metadata.title}")
        suffix = f" [{metadata.isrc}]" if metadata.isrc else ""
        filename = f"{cache_key}_{display}{suffix}.{ext}"
        return Path(settings.MEDIA_ROOT) / "downloads" / filename

    def _load_metadata_from_db_if_present(self) -> ProviderTrackMetadata | None:
        """
        Optimisation + idempotence : si la tâche a déjà un TrackMetadata DB,
        on peut reconstruire des métadonnées provider sans recontacter l'API externe.
        """
        if not self.task.track:
            return None
        t = self.task.track
        return ProviderTrackMetadata(
            title=t.title,
            artist=t.artist,
            album=t.album,
            release_year=t.release_year,
            cover_url=t.cover_url,
            duration_ms=t.duration_ms,
            isrc=t.isrc,
            provider=self.task.provider,
            original_url=self.task.original_url,
        )

    def process(self):
        try:
            # idempotence: si déjà complété et fichier présent, on sort proprement
            if self.task.status == DownloadTask.Status.COMPLETED and self.task.result_file:
                try:
                    if Path(self.task.result_file.path).exists():
                        self._notify("Déjà terminé (cache).", force=True)
                        return
                except Exception:
                    pass

            self._set_status(DownloadTask.Status.PROCESSING, message="Initialisation du moteur...")
            self._set_progress(2)

            self._notify("Récupération des métadonnées du provider...")
            self._set_progress(5)
            
            auth_token = None
            refresh_token = None
            if self.task.user:
                from api.models import ProviderAuth
                if "spotify.com" in self.task.original_url:
                    p_name = 'spotify'
                elif "deezer.com" in self.task.original_url:
                    p_name = 'deezer'
                elif "apple.com" in self.task.original_url:
                    p_name = 'apple_music'
                elif "tidal.com" in self.task.original_url:
                    p_name = 'tidal'
                elif "youtube.com" in self.task.original_url or "youtu.be" in self.task.original_url:
                    p_name = 'youtube_music'
                else:
                    p_name = None
                
                if p_name:
                    auth_obj = ProviderAuth.objects.filter(user=self.task.user, provider=p_name).first()
                    if auth_obj:
                        from django.utils import timezone
                        from datetime import timedelta
                        if auth_obj.expires_at and auth_obj.expires_at <= timezone.now() + timedelta(minutes=1):
                            self.logger.info(f"Token {p_name} expiré pour le moteur, rafraîchissement...")
                            try:
                                from api.tasks import refresh_spotify_token, refresh_deezer_token, refresh_tidal_token
                                if p_name == 'spotify':
                                    refresh_spotify_token(auth_obj)
                                elif p_name == 'deezer':
                                    refresh_deezer_token(auth_obj)
                                elif p_name == 'tidal':
                                    refresh_tidal_token(auth_obj)
                                auth_obj.refresh_from_db()
                            except Exception as e:
                                self.logger.error(f"Échec du refresh automatique dans le moteur: {e}")
                        
                        auth_token = auth_obj.access_token
                        refresh_token = auth_obj.refresh_token
                        user_id = auth_obj.provider_user_id

            metadata = self._load_metadata_from_db_if_present()
            if metadata is None:
                provider = ProviderFactory.get_provider(self.task.original_url, auth_token=auth_token, refresh_token=refresh_token, user_id=user_id)
                metadata = provider.get_track_info_cached(self.task.original_url)
            
            track_meta = None
            if metadata.isrc:
                self._notify(f"ISRC identifié : {metadata.isrc}")
                self._set_progress(8)
                track_meta, _ = TrackMetadata.objects.update_or_create(
                    isrc=metadata.isrc,
                    defaults={ 
                        "title": metadata.title,
                        "artist": metadata.artist,
                        "album": metadata.album,
                        "release_year": metadata.release_year,
                        "cover_url": metadata.cover_url,
                        "duration_ms": metadata.duration_ms,
                    }
                )
            self.task.track = track_meta
            DownloadTask.objects.filter(id=self.task.id).update(track=track_meta)
            self._notify(f"Titre : {metadata.title} - {metadata.artist}")
            self._set_progress(10)

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

            final_dest = self._build_final_dest(metadata, ext)
            
            if final_dest.exists():
                rel = f"downloads/{final_dest.name}"
                DownloadTask.objects.filter(id=self.task.id).update(
                    result_file=rel,
                    status=DownloadTask.Status.COMPLETED,
                    progress=100,
                    error_message=None,
                    error_code=None,
                )
                self.task.result_file = rel
                self.task.status = DownloadTask.Status.COMPLETED
                self.task.progress = 100
                self._notify("Fichier récupéré depuis le cache MNLV.", force=True)
                return

            self._notify("Recherche de la meilleure correspondance sur YouTube...")
            self._set_progress(15)
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
                    'retries': 3,
                    'fragment_retries': 3,
                    'socket_timeout': 20,
                    'continuedl': True,
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
                    'retries': 3,
                    'fragment_retries': 3,
                    'socket_timeout': 20,
                    'continuedl': True,
                }

            self._notify("Connexion aux serveurs de streaming...")
            self._set_progress(20)
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
                self._notify("Tentative de secours sans filtres de format...")
                self._set_progress(25)
                ydl_opts['format'] = 'best'
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([search_query])
                
                for f in self.temp_dir.glob(f"{self.task.id}.*"):
                    downloaded_file = f
                    break

            if not downloaded_file:
                raise FileNotFoundError("Aucun flux compatible n'a pu être extrait.")

            self._notify("Traitement du fichier source...")
            self._set_progress(82)
            pro_formats = [
                DownloadTask.MediaType.FLAC, 
                DownloadTask.MediaType.ALAC, 
                DownloadTask.MediaType.OPUS, 
                DownloadTask.MediaType.AAC,
                DownloadTask.MediaType.WAV
            ]
            
            final_file = downloaded_file
            if self.task.media_type in pro_formats:
                self._notify(f"Encodage haute fidélité ({self.task.media_type})...")
                self._set_progress(85)
                final_file = Path(MediaService.convert_to_format(str(downloaded_file), self.task.media_type))

            if self.task.media_type in [DownloadTask.MediaType.AUDIO, DownloadTask.MediaType.VIDEO]:
                self._notify("Injection des métadonnées et de la pochette HD...")
                self._set_progress(90)
                MediaService.apply_metadata(
                    str(final_file), 
                    metadata.__dict__, 
                    is_video=is_video_mode
                )

            final_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(final_file), str(final_dest))
            
            rel = f"downloads/{final_dest.name}"
            DownloadTask.objects.filter(id=self.task.id).update(
                result_file=rel,
                status=DownloadTask.Status.COMPLETED,
                progress=100,
                error_message=None,
                error_code=None,
            )
            self.task.result_file = rel
            self.task.status = DownloadTask.Status.COMPLETED
            self.task.progress = 100
            self._notify("Téléchargement prêt !", force=True)

        except ProviderError as e:
            # Erreurs spécifiques aux providers (Spotify, Tidal, etc.)
            err = str(e)
            code = e.code or "PROVIDER_ERROR"
            
            # Message plus convivial pour l'utilisateur
            friendly_msg = err
            if isinstance(e, ProviderAuthError):
                friendly_msg = f"Erreur d'authentification {self.task.provider} : Veuillez reconnecter votre compte."
            elif isinstance(e, ProviderRateLimitError):
                friendly_msg = f"Le service {self.task.provider} limite temporairement les requêtes. Réessayez plus tard."
            elif isinstance(e, ProviderResourceNotFoundError):
                friendly_msg = "Le contenu demandé est introuvable sur la plateforme source."

            DownloadTask.objects.filter(id=self.task.id).update(
                status=DownloadTask.Status.FAILED,
                error_message=friendly_msg,
                error_code=code,
            )
            self.task.status = DownloadTask.Status.FAILED
            self.task.error_message = friendly_msg
            self.task.error_code = code
            self._notify(friendly_msg, force=True)
            raise

        except Exception as e:
            # classification simple et actionnable
            err = str(e)
            code = "UNKNOWN"
            if isinstance(e, FileNotFoundError):
                code = "FILESYSTEM"
            elif "FFmpeg" in err or "ffmpeg" in err:
                code = "FFMPEG"
            elif "YouTube" in err or "yt-dlp" in err or "Erreur YouTube" in err:
                code = "YTDLP"
            elif "Aucun flux compatible" in err or "matching" in err.lower():
                code = "NO_MATCH"

            DownloadTask.objects.filter(id=self.task.id).update(
                status=DownloadTask.Status.FAILED,
                error_message=err,
                error_code=code,
            )
            self.task.status = DownloadTask.Status.FAILED
            self.task.error_message = err
            self.task.error_code = code
            self._notify("Échec du téléchargement.", force=True)
            raise
        finally:
            # ne doit jamais masquer l'erreur initiale
            try:
                if self.temp_dir.exists():
                    shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception:
                pass
