from django.test import TestCase
from unittest.mock import MagicMock, patch
from media_tools.services import MediaService
from pathlib import Path
import os

class MediaServiceTest(TestCase):
    def setUp(self):
        self.test_file = "test_audio.mp3"
        # Création d'un fichier vide pour les tests
        Path(self.test_file).touch()

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    @patch('media_tools.services.MP3')
    @patch('requests.get')
    def test_apply_metadata_audio(self, mock_get, mock_mp3):
        """Vérifie l'application des tags sur un fichier audio"""
        metadata = {
            'title': 'Test Title',
            'artist': 'Test Artist',
            'album': 'Test Album',
            'release_year': 2024
        }
        
        MediaService.apply_metadata(self.test_file, metadata, is_video=False)
        self.assertTrue(mock_mp3.called)

    @patch('subprocess.run')
    def test_convert_to_wav(self, mock_run):
        """Vérifie l'appel à FFmpeg pour la conversion"""
        MediaService.convert_to_wav(self.test_file)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], 'ffmpeg')
        self.assertIn(self.test_file, args)
