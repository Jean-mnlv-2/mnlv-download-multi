import os
import subprocess
from pathlib import Path
from django.conf import settings
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TYER, APIC
from mutagen.mp4 import MP4, MP4Cover
import requests

class MediaService:
    """
    Service pour la conversion audio et l'édition de métadonnées (AUDIO & VIDEO).
    """

    @staticmethod
    def convert_to_format(input_path: str, target_format: str) -> str:
        """
        Convertit un fichier media vers un format cible via FFmpeg.
        Supporte les formats pro (WAV, FLAC, ALAC) et WebRadio/TV (OPUS, AAC).
        Optimisé pour la qualité studio (44.1kHz / 16-bit PCM pour WAV).
        """
        input_file = Path(input_path)
        ext = f".{target_format.lower()}"
        output_file = input_file.with_suffix(ext)
        
        cmd = ['ffmpeg', '-y', '-i', str(input_file)]
        
        if target_format == 'FLAC':
            cmd += ['-c:a', 'flac', '-compression_level', '8']
        elif target_format == 'ALAC':
            cmd += ['-c:a', 'alac']
        elif target_format == 'WAV':
            cmd += ['-c:a', 'pcm_s16le', '-ar', '44100']
        elif target_format == 'OPUS':
            cmd += ['-c:a', 'libopus', '-b:a', '128k', '-vbr', 'on', '-compression_level', '10']
        elif target_format == 'AAC':
            cmd += ['-c:a', 'aac', '-b:a', '256k']
        elif target_format == 'MKV':
            cmd += ['-c:v', 'copy', '-c:a', 'copy']
            
        cmd.append(str(output_file))
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return str(output_file)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Erreur FFmpeg ({target_format}) : {e.stderr.decode()}")

    @staticmethod
    def convert_to_wav(input_path: str) -> str:
        """
        Ancienne méthode pour compatibilité WAV uniquement.
        """
        return MediaService.convert_to_format(input_path, 'WAV')

    @staticmethod
    def apply_metadata(file_path: str, metadata: dict, is_video: bool = False):
        """
        Met à jour les tags (ID3 pour MP3 ou MP4 pour vidéo).
        Accepte un dictionnaire de métadonnées standardisé.
        """
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"Fichier non trouvé : {file_path}")

        try:
            if not is_video:
                # Logique MP3 / ID3
                audio = MP3(path, ID3=ID3)
                try: audio.add_tags()
                except: pass
                
                if metadata.get('title'):
                    audio.tags.add(TIT2(encoding=3, text=metadata['title']))
                if metadata.get('artist'):
                    audio.tags.add(TPE1(encoding=3, text=metadata['artist']))
                if metadata.get('album'):
                    audio.tags.add(TALB(encoding=3, text=metadata['album']))
                if metadata.get('release_year'):
                    audio.tags.add(TYER(encoding=3, text=str(metadata['release_year'])))
                
                # Pochette
                cover_url = metadata.get('cover_url')
                if cover_url:
                    try:
                        r = requests.get(cover_url, timeout=10)
                        if r.status_code == 200:
                            mime_type = r.headers.get('Content-Type', 'image/jpeg')
                            audio.tags.add(APIC(
                                encoding=3, 
                                mime=mime_type, 
                                type=3, 
                                desc='Front Cover', 
                                data=r.content
                            ))
                    except Exception as e:
                        from core.logger_utils import get_mnlv_logger
                        get_mnlv_logger("media_service").warning(f"Échec téléchargement pochette : {e}")
                audio.save()
            else:
                # Logique MP4
                video = MP4(path)
                if metadata.get('title'):
                    video["\xa9nam"] = metadata['title']
                if metadata.get('artist'):
                    video["\xa9ART"] = metadata['artist']
                if metadata.get('album'):
                    video["\xa9alb"] = metadata['album']
                if metadata.get('release_year'):
                    video["\xa9day"] = str(metadata['release_year'])
                
                # Pochette MP4
                cover_url = metadata.get('cover_url')
                if cover_url:
                    try:
                        r = requests.get(cover_url, timeout=10)
                        if r.status_code == 200:
                            video["covr"] = [MP4Cover(r.content, imageformat=MP4Cover.FORMAT_JPEG)]
                    except Exception as e:
                        pass
                video.save()

        except Exception as e:
            from core.logger_utils import get_mnlv_logger
            get_mnlv_logger("media_service").warning(f"Échec tagging non critique sur {file_path}: {e}")

    @staticmethod
    def update_metadata(file_path: str, metadata: dict):
        """
        Compatibilité avec l'ancienne signature (Met à jour les tags ID3 d'un fichier MP3).
        """
        MediaService.apply_metadata(file_path, metadata, is_video=False)
