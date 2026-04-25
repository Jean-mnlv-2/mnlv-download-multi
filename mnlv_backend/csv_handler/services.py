import csv
import io
import pandas as pd
from typing import List, Dict
from django.core.cache import cache
from downloader.providers.spotify import SpotifyProvider

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
        
        if filename.endswith(('.csv', '.txt')):
            return FileParserService.parse_csv(file_obj.read())
        elif filename.endswith(('.xlsx', '.xls')):
            return FileParserService.parse_excel(file_obj)
        else:
            raise ValueError("Format de fichier non supporté. Utilisez .csv, .txt ou .xlsx")

    @staticmethod
    def parse_csv(file_content: bytes) -> List[Dict[str, str]]:
        """
        Parse un fichier CSV et retourne une liste de dictionnaires {artist, title, url}.
        Supporte le mode Discovery (title/artist) et le mode direct (url).
        """
        try:
            decoded_file = file_content.decode('utf-8')
        except UnicodeDecodeError:
            decoded_file = file_content.decode('latin-1')
            
        io_string = io.StringIO(decoded_file)
        
        try:
            dialect = csv.Sniffer().sniff(decoded_file[:2048])
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ','
            
        io_string.seek(0)
        
        content = io_string.read()
        io_string.seek(0)
        
        has_header = False
        try:
            has_header = csv.Sniffer().has_header(content) if content.strip() else False
        except Exception:
            pass
        
        tracks = []
        if has_header:
            reader = csv.DictReader(io_string, delimiter=delimiter)
            for row in reader:
                normalized_row = {str(k).lower().strip(): str(v).strip() for k, v in row.items() if k}
                
                title = normalized_row.get('title') or normalized_row.get('track') or normalized_row.get('nom')
                artist = normalized_row.get('artist') or normalized_row.get('artiste')
                url = normalized_row.get('url') or normalized_row.get('link') or normalized_row.get('lien')
                
                if not title and not artist:
                    for key, value in normalized_row.items():
                        if 'artist - title' in key or 'artiste - titre' in key:
                            if ' - ' in value:
                                parts = value.split(' - ', 1)
                                artist = parts[0].strip()
                                title = parts[1].strip()
                                break
                        elif ' - ' in value and key not in ['url', 'link', 'lien']:
                            parts = value.split(' - ', 1)
                            artist = parts[0].strip()
                            title = parts[1].strip()
                            break

                track_info = {
                    'title': title,
                    'artist': artist,
                    'url': url
                }
                if track_info['title'] or track_info['url']:
                    tracks.append(track_info)
        else:
            reader = csv.reader(io_string, delimiter=delimiter)
            for row in reader:
                if not row: continue
                
                track_info = {'title': None, 'artist': None, 'url': None}
                
                for col in row:
                    val = col.strip()
                    if not val: continue
                    
                    if val.startswith('http'):
                        track_info['url'] = val
                    elif ' - ' in val:
                        parts = val.split(' - ', 1)
                        track_info['artist'] = parts[0].strip()
                        track_info['title'] = parts[1].strip()
                    
                if not track_info['title'] and not track_info['url'] and row:
                    track_info['title'] = row[0].strip()

                if track_info['title'] or track_info['url']:
                    tracks.append(track_info)
                    
        return tracks

    @staticmethod
    def parse_excel(file_obj) -> List[Dict[str, str]]:
        """
        Parse un fichier Excel (.xlsx) via pandas.
        """
        df = pd.read_excel(file_obj)
        raw_data = df.to_dict(orient='records')
        
        tracks = []
        for row in raw_data:
            normalized_row = {str(k).lower().strip(): v for k, v in row.items()}
            
            title = normalized_row.get('title') or normalized_row.get('track') or normalized_row.get('nom')
            artist = normalized_row.get('artist') or normalized_row.get('artiste')
            url = normalized_row.get('url') or normalized_row.get('link') or normalized_row.get('lien')
            
            if not title and not artist:
                for key, value in normalized_row.items():
                    val_str = str(value).strip() if value else ""
                    if 'artist - title' in key or 'artiste - titre' in key:
                        if ' - ' in val_str:
                            parts = val_str.split(' - ', 1)
                            artist = parts[0].strip()
                            title = parts[1].strip()
                            break
                    elif ' - ' in val_str and key not in ['url', 'link', 'lien']:
                        parts = val_str.split(' - ', 1)
                        artist = parts[0].strip()
                        title = parts[1].strip()
                        break

            track_info = {
                'title': title,
                'artist': artist,
                'url': url
            }
            if track_info['title'] or track_info['url']:
                tracks.append(track_info)
        return tracks

    @staticmethod
    def resolve_tracks(track_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Analyse une liste de morceaux et tente de les compléter.
        Si une URL est déjà présente, on tente de deviner le provider.
        Si aucune URL, on tente une recherche Spotify (optionnel).
        """
        provider = SpotifyProvider()
        resolved_tracks = []
        
        for item in track_list:
            # Si URL présente, on identifie le provider
            if item.get('url'):
                url = item['url']
                provider_name = 'unknown'
                if 'spotify.com' in url: provider_name = 'spotify'
                elif 'deezer.com' in url: provider_name = 'deezer'
                elif 'apple.com' in url: provider_name = 'apple_music'
                elif 'tidal.com' in url: provider_name = 'tidal'
                elif 'youtube.com' in url or 'youtu.be' in url: provider_name = 'youtube_music'
                elif 'soundcloud.com' in url: provider_name = 'soundcloud'
                
                resolved_tracks.append({
                    **item,
                    'provider': provider_name,
                    'status': 'ready'
                })
                continue
                
            if item.get('title'):
                query = f"track:{item['title']}"
                if item.get('artist'):
                    query += f" artist:{item['artist']}"
                
                # Check cache first
                cache_key = f"resolve:{query}"
                cached_track = cache.get(cache_key)
                if cached_track:
                    resolved_tracks.append(cached_track)
                    continue
                
                try:
                    results = provider.client.search(q=query, type='track', limit=1)
                    if results['tracks']['items']:
                        track = results['tracks']['items'][0]
                        res_item = {
                            'title': track['name'],
                            'artist': track['artists'][0]['name'],
                            'url': track['external_urls']['spotify'],
                            'provider': 'spotify',
                            'status': 'ready'
                        }
                        # Cache the result for 24 hours
                        cache.set(cache_key, res_item, timeout=86400)
                        resolved_tracks.append(res_item)
                    else:
                        resolved_tracks.append({
                            **item,
                            'provider': None,
                            'status': 'not_found'
                        })
                except Exception:
                    resolved_tracks.append({
                        **item,
                        'provider': None,
                        'status': 'error'
                    })
            else:
                continue
                    
        return resolved_tracks
