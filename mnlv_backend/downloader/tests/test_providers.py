from django.test import TestCase
from unittest.mock import MagicMock, patch, PropertyMock
from downloader.providers.factory import ProviderFactory
from downloader.providers.base import ProviderTrackMetadata
from downloader.providers.spotify.provider import SpotifyProvider
from downloader.providers.deezer.provider import DeezerProvider
from downloader.providers.boomplay.provider import BoomplayProvider
from downloader.providers.apple_music.provider import AppleMusicProvider
from downloader.providers.soundcloud.provider import SoundCloudProvider
from downloader.providers.tidal.provider import TidalProvider
from downloader.providers.amazon_music.provider import AmazonMusicProvider
from downloader.providers.youtube_music.provider import YouTubeMusicProvider

class ProviderFactoryTest(TestCase):
    def test_factory_initialization(self):
        """Vérifie que l'usine charge bien les providers"""
        ProviderFactory.initialize()
        self.assertTrue(len(ProviderFactory._providers) >= 8)
        
    def test_get_spotify_provider(self):
        """Vérifie la détection d'une URL Spotify"""
        url = "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"
        provider = ProviderFactory.get_provider(url)
        self.assertIsInstance(provider, SpotifyProvider)

    def test_get_deezer_provider(self):
        """Vérifie la détection d'une URL Deezer"""
        url = "https://www.deezer.com/track/123456"
        provider = ProviderFactory.get_provider(url)
        self.assertIsInstance(provider, DeezerProvider)

    def test_get_boomplay_provider(self):
        """Vérifie la détection d'une URL Boomplay"""
        url = "https://www.boomplay.com/songs/123456"
        provider = ProviderFactory.get_provider(url)
        self.assertIsInstance(provider, BoomplayProvider)

    def test_get_apple_music_provider(self):
        """Vérifie la détection d'une URL Apple Music"""
        url = "https://music.apple.com/us/album/song/123"
        provider = ProviderFactory.get_provider(url)
        self.assertIsInstance(provider, AppleMusicProvider)

    def test_get_soundcloud_provider(self):
        """Vérifie la détection d'une URL SoundCloud"""
        url = "https://soundcloud.com/artist/track"
        provider = ProviderFactory.get_provider(url)
        self.assertIsInstance(provider, SoundCloudProvider)

    def test_get_tidal_provider(self):
        """Vérifie la détection d'une URL Tidal"""
        url = "https://tidal.com/track/123"
        provider = ProviderFactory.get_provider(url)
        self.assertIsInstance(provider, TidalProvider)

    def test_get_amazon_music_provider(self):
        """Vérifie la détection d'une URL Amazon Music"""
        url = "https://music.amazon.com/albums/B000"
        provider = ProviderFactory.get_provider(url)
        self.assertIsInstance(provider, AmazonMusicProvider)

    def test_get_youtube_music_provider(self):
        """Vérifie la détection d'une URL YouTube Music"""
        url = "https://music.youtube.com/watch?v=123"
        provider = ProviderFactory.get_provider(url)
        self.assertIsInstance(provider, YouTubeMusicProvider)

class SpotifyProviderTest(TestCase):
    @patch('spotipy.Spotify')
    def test_map_track(self, mock_spotify):
        """Vérifie le mapping des données Spotify"""
        provider = SpotifyProvider()
        mock_data = {
            'name': 'Test Song',
            'artists': [{'name': 'Test Artist'}],
            'album': {
                'name': 'Test Album',
                'release_date': '2024-01-01',
                'images': [{'url': 'http://example.com/cover.jpg'}]
            },
            'duration_ms': 180000,
            'external_ids': {'isrc': 'USABC1234567'},
            'external_urls': {'spotify': 'http://spotify.com/track/1'}
        }
        
        metadata = provider._map_track(mock_data)
        self.assertEqual(metadata.title, 'Test Song')
        self.assertEqual(metadata.artist, 'Test Artist')
        self.assertEqual(metadata.isrc, 'USABC1234567')
        self.assertEqual(metadata.release_year, 2024)

class DeezerProviderTest(TestCase):
    def test_map_track(self):
        """Vérifie le mapping des données Deezer"""
        provider = DeezerProvider()
        mock_data = {
            'title': 'Deezer Song',
            'artist': {'name': 'Deezer Artist'},
            'album': {
                'title': 'Deezer Album',
                'release_date': '2023-05-05',
                'cover_xl': 'http://deezer.com/cover.jpg'
            },
            'duration': 200,
            'isrc': 'FR1234567890',
            'link': 'http://deezer.com/track/1',
            'explicit_lyrics': True
        }
        
        metadata = provider._map_track(mock_data)
        self.assertEqual(metadata.title, 'Deezer Song')
        self.assertEqual(metadata.isrc, 'FR1234567890')
        self.assertTrue(metadata.explicit)
        self.assertEqual(metadata.duration_ms, 200000)

class BoomplayProviderTest(TestCase):
    def test_map_track(self):
        """Vérifie le mapping des données Boomplay"""
        provider = BoomplayProvider()
        mock_data = {
            'track_title': 'Boom Song',
            'artists': [{'artist_name': 'Boom Artist'}],
            'album_title': 'Boom Album',
            'artwork': {'url': 'http://boomplay.com/cover.jpg'},
            'duration': '03:30',
            'isrc': 'USBM12345678',
            'web_url': 'http://boomplay.com/songs/1'
        }
        
        metadata = provider._map_track(mock_data)
        self.assertEqual(metadata.title, 'Boom Song')
        self.assertEqual(metadata.artist, 'Boom Artist')
        self.assertEqual(metadata.isrc, 'USBM12345678')
        self.assertEqual(metadata.duration_ms, 210000)
        self.assertEqual(metadata.cover_url, 'http://boomplay.com/cover.jpg')

class AppleMusicProviderTest(TestCase):
    def test_map_track(self):
        """Vérifie le mapping des données Apple Music"""
        provider = AppleMusicProvider()
        mock_attrs = {
            'name': 'Apple Song',
            'artistName': 'Apple Artist',
            'albumName': 'Apple Album',
            'releaseDate': '2022-10-10',
            'artwork': {'url': 'http://apple.com/cover_{w}x{h}.jpg'},
            'durationInMillis': 200000,
            'isrc': 'USAP12345678',
            'contentRating': 'explicit'
        }
        
        metadata = provider._map_track(mock_attrs, "http://apple.com/track/1")
        self.assertEqual(metadata.title, 'Apple Song')
        self.assertEqual(metadata.artist, 'Apple Artist')
        self.assertEqual(metadata.isrc, 'USAP12345678')
        self.assertEqual(metadata.duration_ms, 200000)
        self.assertTrue(metadata.explicit)
        self.assertEqual(metadata.cover_url, 'http://apple.com/cover_1000x1000.jpg')

class SoundCloudProviderTest(TestCase):
    def test_map_track(self):
        """Vérifie le mapping des données SoundCloud"""
        provider = SoundCloudProvider()
        mock_info = {
            'title': 'SC Song',
            'user': {'username': 'SC Artist'},
            'artwork_url': 'http://sc.com/cover-large.jpg',
            'created_at': '2021/01/01 12:00:00 +0000',
            'duration': 150000,
            'kind': 'track',
            'permalink_url': 'http://soundcloud.com/artist/track'
        }
        
        metadata = provider._map_track(mock_info)
        self.assertEqual(metadata.title, 'SC Song')
        self.assertEqual(metadata.artist, 'SC Artist')
        self.assertEqual(metadata.duration_ms, 150000)
        self.assertEqual(metadata.cover_url, 'http://sc.com/cover-t500x500.jpg')

class TidalProviderTest(TestCase):
    def test_map_track(self):
        """Vérifie le mapping des données Tidal"""
        provider = TidalProvider()
        
        mock_track = MagicMock()
        mock_track.name = "Tidal Song"
        mock_track.id = "123"
        mock_artist = MagicMock()
        mock_artist.name = "Tidal Artist"
        mock_track.artists = [mock_artist]
        mock_track.album.name = "Tidal Album"
        mock_track.album.year = 2020
        mock_track.album.image.return_value = "http://tidal.com/cover.jpg"
        mock_track.duration = 180
        mock_track.isrc = "USTI12345678"
        
        metadata = provider._map_track(mock_track)
        self.assertEqual(metadata.title, 'Tidal Song')
        self.assertEqual(metadata.artist, 'Tidal Artist')
        self.assertEqual(metadata.isrc, 'USTI12345678')
        self.assertEqual(metadata.duration_ms, 180000)

class AmazonMusicProviderTest(TestCase):
    @patch('requests.get')
    def test_get_track_info(self, mock_get):
        """Vérifie l'extraction des données Amazon Music via scraping"""
        provider = AmazonMusicProvider()
        
        mock_response = MagicMock()
        mock_response.text = '{"title":"Amazon Song","artistName":"Amazon Artist","albumName":"Amazon Album","image":"http://amazon.com/cover.jpg"}'
        mock_get.return_value = mock_response
        
        metadata = provider.get_track_info("https://music.amazon.com/track/1")
        self.assertEqual(metadata.title, 'Amazon Song')
        self.assertEqual(metadata.artist, 'Amazon Artist')
        self.assertEqual(metadata.provider, 'amazon_music')

class YouTubeMusicProviderTest(TestCase):
    @patch('downloader.providers.youtube_music.provider.YouTubeMusicProvider.yt', new_callable=PropertyMock)
    def test_get_track_info(self, mock_yt_property):
        """Vérifie l'extraction des données YouTube Music"""
        provider = YouTubeMusicProvider()
        
        mock_yt = MagicMock()
        mock_yt.get_song.return_value = {
            'videoDetails': {
                'title': 'YT Song',
                'author': 'YT Artist',
                'lengthSeconds': '240',
                'thumbnail': {'thumbnails': [{'url': 'http://yt.com/cover.jpg'}]}
            },
            'isrc': 'USYT12345678'
        }
        mock_yt_property.return_value = mock_yt
        
        metadata = provider.get_track_info("https://music.youtube.com/watch?v=123")
        self.assertEqual(metadata.title, 'YT Song')
        self.assertEqual(metadata.artist, 'YT Artist')
        self.assertEqual(metadata.isrc, 'USYT12345678')
        self.assertEqual(metadata.duration_ms, 240000)
