from django.test import TestCase
from unittest.mock import MagicMock, patch
from downloader.providers.factory import ProviderFactory
from downloader.providers.base import TrackMetadata
from downloader.providers.spotify.provider import SpotifyProvider
from downloader.providers.deezer.provider import DeezerProvider

class ProviderFactoryTest(TestCase):
    def test_factory_initialization(self):
        """Vérifie que l'usine charge bien les providers"""
        ProviderFactory.initialize()
        self.assertTrue(len(ProviderFactory._providers) > 0)
        
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
