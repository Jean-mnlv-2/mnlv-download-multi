from rest_framework.response import Response
from rest_framework import status
from core.logger_utils import get_mnlv_logger

logger = get_mnlv_logger("api_errors")

class StandardizedErrorMixin:
    """
    Mixin pour standardiser les réponses d'erreur dans les vues DRF.
    Fournit des méthodes helper pour logger et retourner des erreurs uniformes.
    """
    
    def error_response(self, message: str, status_code=status.HTTP_400_BAD_REQUEST, error_code=None, data=None):
        """
        Retourne une réponse d'erreur standardisée.
        """
        response_data = {
            "error": message,
            "status": "error"
        }
        if error_code:
            response_data["code"] = error_code
        if data:
            response_data["details"] = data
            
        logger.error(f"API Error [{status_code}]: {message}")
        return Response(response_data, status=status_code)

    def handle_exception(self, exc):
        """
        Intercepte les exceptions non gérées pour retourner une erreur propre.
        """
        from rest_framework.exceptions import APIException
        if isinstance(exc, APIException):
            return super().handle_exception(exc)
            
        exc_str = str(exc).lower()
        auth_error_keywords = [
            "expired", "401", "unauthorized", 
            "expiré", "authentifiée", "reconnecter", "connexion requise",
            "token requis", "authentification échouée"
        ]
        
        if any(kw in exc_str for kw in auth_error_keywords):
            return self.error_response(
                message="Votre session avec le service de musique a expiré ou nécessite une reconnexion. Veuillez reconnecter votre compte.",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="AUTH_EXPIRED"
            )

        logger.exception(f"Exception non gérée : {exc}")
        return self.error_response(
            message=f"Erreur interne du serveur : {str(exc)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="SERVER_ERROR"
        )
