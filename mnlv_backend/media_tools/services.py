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
    def convert_to_wav(input_path: str) -> str:
        """
        Convertit un fichier audio en WAV via FFmpeg.
        """
        input_file = Path(input_path)
        output_file = input_file.with_suffix('.wav')
        
        try:
            subprocess.run(['ffmpeg', '-y', '-i', str(input_file), str(output_file)], 
                         check=True, capture_output=True)
            return str(output_file)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Erreur FFmpeg : {e.stderr.decode()}")

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
                    r = requests.get(cover_url, timeout=10)
                    if r.status_code == 200:
                        audio.tags.add(APIC(
                            encoding=3, mime='image/jpeg', type=3, 
                            desc='Front Cover', data=r.content
                        ))
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
                    r = requests.get(cover_url, timeout=10)
                    if r.status_code == 200:
                        video["covr"] = [MP4Cover(r.content, imageformat=MP4Cover.FORMAT_JPEG)]
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
