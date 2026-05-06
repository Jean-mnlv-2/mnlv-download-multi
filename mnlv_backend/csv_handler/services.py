import csv
import io
import pandas as pd
import logging
from typing import List, Dict
from django.core.cache import cache
from downloader.providers.spotify import SpotifyProvider

logger = logging.getLogger("api")

class FileParserService:
    """
    Service pour parser les fichiers locaux (CSV, Excel) et extraire les informations musicales.
    """
    
    @staticmethod
    def parse_file(file_obj) -> List[Dict[str, str]]:
        """
        Détecte le format et parse le fichier (CSV ou Excel).
        """
        filename = file_obj.name.lower()
        logger.info(f"Parsing file: {filename}")
        
        try:
            if filename.endswith(('.csv', '.txt')):
                content = file_obj.read()
                return list(FileParserService.parse_csv(content))
            elif filename.endswith(('.xlsx', '.xls')):
                return FileParserService.parse_excel(file_obj)
            else:
                raise ValueError(f"Format de fichier non supporté ({filename}). Utilisez .csv, .txt ou .xlsx")
        except Exception as e:
            logger.error(f"Error parsing file {filename}: {str(e)}")
            raise

    @staticmethod
    def parse_csv(file_content: bytes):
        """
        Parse un fichier CSV et retourne un générateur de dictionnaires {artist, title, url}.
        Optimisé pour la mémoire avec io.StringIO et le streaming.
        """
        if not file_content:
            logger.warning("Empty CSV content")
            return

        try:
            decoded_file = file_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                decoded_file = file_content.decode('latin-1')
            except Exception:
                decoded_file = file_content.decode('utf-8', errors='ignore')
            
        io_string = io.StringIO(decoded_file)
        
        try:
            sample = decoded_file[:4096]
            dialect = csv.Sniffer().sniff(sample)
            delimiter = dialect.delimiter
            logger.debug(f"Detected delimiter: '{delimiter}'")
        except Exception as e:
            logger.debug(f"Delimiter detection failed: {e}, defaulting to ','")
            delimiter = ','
            
        io_string.seek(0)
        
        has_header = False
        try:
            if len(decoded_file) > 10:
                has_header = csv.Sniffer().has_header(decoded_file[:8192])
        except Exception:
            pass
        
        logger.debug(f"Has header: {has_header}")

        if has_header:
            reader = csv.DictReader(io_string, delimiter=delimiter)
            for row in reader:
                normalized_row = {str(k).lower().strip(): str(v).strip() for k, v in row.items() if k}
                
                title = normalized_row.get('title') or normalized_row.get('track') or normalized_row.get('nom') or normalized_row.get('titre')
                artist = normalized_row.get('artist') or normalized_row.get('artiste')
                url = normalized_row.get('url') or normalized_row.get('link') or normalized_row.get('lien')
                
                if not title and not artist:
                    for key, value in normalized_row.items():
                        if value and ' - ' in value:
                            parts = value.split(' - ', 1)
                            artist = parts[0].strip()
                            title = parts[1].strip()
                            break

                track_info = {'title': title, 'artist': artist, 'url': url}
                if track_info['title'] or track_info['url']:
                    yield track_info
        else:
            reader = csv.reader(io_string, delimiter=delimiter)
            for row in reader:
                if not row: continue
                track_info = {'title': None, 'artist': None, 'url': None}
                for col in row:
                    val = col.strip()
                    if not val: continue
                    if val.startswith(('http://', 'https://')):
                        track_info['url'] = val
                    elif ' - ' in val and not track_info['title']:
                        parts = val.split(' - ', 1)
                        track_info['artist'], track_info['title'] = parts[0].strip(), parts[1].strip()
                
                if not track_info['title'] and not track_info['url'] and row:
                    track_info['title'] = row[0].strip()

                if track_info['title'] or track_info['url']:
                    yield track_info

    @staticmethod
    def parse_excel(file_obj) -> List[Dict[str, str]]:
        """
        Parse un fichier Excel (.xlsx) via pandas.
        """
        try:
            df = pd.read_excel(file_obj)
            raw_data = df.to_dict(orient='records')
            
            tracks = []
            for row in raw_data:
                normalized_row = {str(k).lower().strip(): v for k, v in row.items()}
                
                title = normalized_row.get('title') or normalized_row.get('track') or normalized_row.get('nom') or normalized_row.get('titre')
                artist = normalized_row.get('artist') or normalized_row.get('artiste')
                url = normalized_row.get('url') or normalized_row.get('link') or normalized_row.get('lien')
                
                if not title and not artist:
                    for key, value in normalized_row.items():
                        val_str = str(value).strip() if value is not None else ""
                        if val_str and ' - ' in val_str:
                            parts = val_str.split(' - ', 1)
                            artist = parts[0].strip()
                            title = parts[1].strip()
                            break

                track_info = {
                    'title': str(title).strip() if title else None,
                    'artist': str(artist).strip() if artist else None,
                    'url': str(url).strip() if url else None
                }
                if track_info['title'] or track_info['url']:
                    tracks.append(track_info)
            return tracks
        except Exception as e:
            logger.error(f"Excel parsing error: {e}")
            raise ValueError(f"Erreur lors de la lecture du fichier Excel : {str(e)}")

    @staticmethod
    def resolve_tracks(track_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Analyse une liste de morceaux et tente de les compléter.
        Si une URL est déjà présente, on tente de deviner le provider.
        """
        resolved_tracks = []
        
        for item in track_list:
            # Si URL présente, on identifie le provider
            if item.get('url'):
                url = item['url'].strip()
                provider_name = 'unknown'
                lower_url = url.lower()
                if 'spotify.com' in lower_url: provider_name = 'spotify'
                elif 'deezer.com' in lower_url: provider_name = 'deezer'
                elif 'apple.com' in lower_url: provider_name = 'apple_music'
                elif 'tidal.com' in lower_url: provider_name = 'tidal'
                elif 'youtube.com' in lower_url or 'youtu.be' in lower_url: provider_name = 'youtube_music'
                elif 'soundcloud.com' in lower_url: provider_name = 'soundcloud'
                
                resolved_tracks.append({
                    **item,
                    'url': url,
                    'provider': provider_name,
                    'status': 'ready'
                })
            elif item.get('title'):
                resolved_tracks.append({
                    **item,
                    'provider': 'search',
                    'status': 'ready'
                })
                
        return resolved_tracks

