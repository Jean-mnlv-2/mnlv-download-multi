from django.test import TestCase
from unittest.mock import MagicMock, patch
from downloader.matching.matcher import ISRCMatcher
from downloader.providers.base import ProviderTrackMetadata

class ISRCMatcherTest(TestCase):
    def setUp(self):
        self.matcher = ISRCMatcher()
        self.metadata = ProviderTrackMetadata(
            title="Blinding Lights",
            artist="The Weeknd",
            isrc="USUM71922222",
            upc="123456789",
            duration_ms=200000
        )

    @patch('yt_dlp.YoutubeDL')
    def test_find_best_match_isrc(self, mock_ydl_class):
        """Vérifie que le matcher priorise l'ISRC"""
        mock_ydl_instance = mock_ydl_class.return_value.__enter__.return_value
        mock_ydl_instance.extract_info.return_value = {
            'entries': [{'webpage_url': 'https://youtube.com/watch?v=isrc_match', 'duration': 200}]
        }
        
        result = self.matcher.find_best_match(self.metadata)
        self.assertEqual(result, 'https://youtube.com/watch?v=isrc_match')
        args, _ = mock_ydl_instance.extract_info.call_args
        self.assertIn('isrc:USUM71922222', args[0])

    @patch('yt_dlp.YoutubeDL')
    def test_find_best_match_fallback(self, mock_ydl_class):
        """Vérifie le fallback textuel si ISRC échoue"""
        mock_ydl_instance = mock_ydl_class.return_value.__enter__.return_value
        mock_ydl_instance.extract_info.return_value = {'entries': []}
        
        result = self.matcher.find_best_match(self.metadata)
        self.assertTrue(result.startswith('ytsearch1:The Weeknd - Blinding Lights'))

    def test_verify_match_success(self):
        """Vérifie la validation de durée"""
        info = {'duration': 205}
        self.assertTrue(self.matcher.verify_match(info, self.metadata))

    def test_verify_match_fail(self):
        """Vérifie le rejet si la durée est trop différente"""
        info = {'duration': 300}
        self.assertFalse(self.matcher.verify_match(info, self.metadata))
