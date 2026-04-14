from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()

class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        token = None
        for param in query_string.split("&"):
            if param.startswith("token="):
                token = param.split("=")[1]
                break
        
        if token:
            scope["user"] = await self.get_user(token)
        else:
            scope["user"] = AnonymousUser()
            
        return await self.app(scope, receive, send)

    @database_sync_to_async
    def get_user(self, token):
        try:
            access_token = AccessToken(token)
            return User.objects.get(id=access_token["user_id"])
        except Exception:
            return AnonymousUser()
