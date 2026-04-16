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
        Intercepte les exceptions non gérées pour retourner une erreur 500 propre.
        Laisse passer les exceptions DRF pour qu'elles retournent leur code (401, 403, etc.).
        """
        from rest_framework.exceptions import APIException
        if isinstance(exc, APIException):
            return super().handle_exception(exc)
            
        logger.exception(f"Exception non gérée : {exc}")
        return self.error_response(
            message=f"Erreur interne du serveur : {str(exc)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="SERVER_ERROR"
        )
