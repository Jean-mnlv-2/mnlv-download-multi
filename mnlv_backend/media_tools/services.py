import os
import subprocess
from pathlib import Path
from django.conf import settings
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TYER, APIC
import requests

class MediaService:
    """
    Service pour la conversion audio et l'édition de métadonnées.
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
    def update_metadata(file_path: str, metadata: dict):
        """
        Met à jour les tags ID3 d'un fichier MP3 existant.
        """
        path = Path(file_path)
        if not path.exists() or path.suffix.lower() != '.mp3':
            raise ValueError("Fichier invalide ou non MP3")

        try:
            audio = MP3(path, ID3=ID3)
            try:
                audio.add_tags()
            except Exception:
                pass

            if 'title' in metadata:
                audio.tags.add(TIT2(encoding=3, text=metadata['title']))
            if 'artist' in metadata:
                audio.tags.add(TPE1(encoding=3, text=metadata['artist']))
            if 'album' in metadata:
                audio.tags.add(TALB(encoding=3, text=metadata['album']))
            if 'year' in metadata:
                audio.tags.add(TYER(encoding=3, text=str(metadata['year'])))

            # Pochette si URL fournie
            if 'cover_url' in metadata and metadata['cover_url']:
                response = requests.get(metadata['cover_url'], timeout=10)
                if response.status_code == 200:
                    audio.tags.add(APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,
                        desc='Front Cover',
                        data=response.content
                    ))
            
            audio.save()
        except Exception as e:
            raise Exception(f"Erreur Mutagen : {str(e)}")
