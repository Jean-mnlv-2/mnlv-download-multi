from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from downloader.models import DownloadTask

class ApiViewsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.force_authenticate(user=self.user)

    def test_submit_download_invalid_url(self):
        """Vérifie le rejet d'une URL invalide"""
        url = reverse('api:submit_download')
        response = self.client.post(url, {'url': 'not-a-url'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'error')

    def test_submit_download_unauthorized(self):
        """Vérifie que l'auth est requise"""
        self.client.force_authenticate(user=None)
        url = reverse('api:submit_download')
        response = self.client.post(url, {'url': 'https://spotify.com/track/1'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_task_status_not_found(self):
        """Vérifie l'erreur 404 sur une tâche inexistante"""
        import uuid
        url = reverse('api:task_status', kwargs={'id': uuid.uuid4()})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_provider_status_view(self):
        """Vérifie le retour du statut des providers"""
        from api.models import ProviderAuth
        ProviderAuth.objects.create(user=self.user, provider='spotify', access_token='token')
        ProviderAuth.objects.create(user=self.user, provider='boomplay', access_token='token')
        
        url = reverse('api:provider_status')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['spotify'])
        self.assertTrue(response.data['boomplay'])
        self.assertFalse(response.data['deezer'])
        self.assertFalse(response.data['tidal'])
        self.assertFalse(response.data['amazon_music'])
        self.assertFalse(response.data['youtube_music'])
        self.assertFalse(response.data['soundcloud'])
