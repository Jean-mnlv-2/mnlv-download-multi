from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock

class DeezerAuthTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.force_authenticate(user=self.user)

    def test_deezer_login_url_generation(self):
        """Vérifie que l'URL d'auth Deezer utilise les identifiants du .env"""
        url = reverse('api:deezer_login')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auth_url = response.data.get('auth_url')
        
        # Vérification de l'ID de l'app (543210 dans le .env)
        self.assertIn(f"app_id={settings.DEEZER_APP_ID}", auth_url)
        self.assertIn("543210", auth_url)
        
        # Vérification du callback
        expected_callback = f"{settings.BACKEND_URL.rstrip('/')}/api/auth/providers/deezer/callback/"
        self.assertIn(f"redirect_uri={expected_callback}", auth_url)
        
        # Vérification du state (ID utilisateur)
        self.assertIn(f"state={self.user.id}", auth_url)

    @patch('requests.get')
    def test_deezer_callback_success(self, mock_get):
        """Vérifie que le callback traite correctement un code valide (mocké)"""
        # Mock de l'échange de token Deezer
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'access_token': 'fake_deezer_token',
            'expires': '3600'
        }
        mock_get.return_value = mock_response
        
        url = reverse('api:deezer_callback')
        # On simule le retour de Deezer avec code et state (user_id)
        response = self.client.get(f"{url}?code=mock_code&state={self.user.id}")
        
        # Le callback redirige vers le frontend
        self.assertEqual(response.status_code, 302)
        self.assertIn('auth_success=deezer', response.url)
        
        # Vérification en base de données
        from api.models import ProviderAuth
        auth = ProviderAuth.objects.get(user=self.user, provider='deezer')
        self.assertEqual(auth.access_token, 'fake_deezer_token')

    def test_deezer_callback_missing_params(self):
        """Vérifie la gestion d'erreur si des paramètres manquent"""
        url = reverse('api:deezer_callback')
        response = self.client.get(url) # Sans code ni state
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('auth_error=deezer', response.url)
        self.assertIn('reason=missing_parameters', response.url)
