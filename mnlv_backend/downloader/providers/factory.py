from typing import Type, List, Optional
from .base import MusicProvider

import logging

logger = logging.getLogger(__name__)

class ProviderFactory:
    """
    Usine permettant d'instancier dynamiquement le bon provider 
    en fonction de l'URL fournie par l'utilisateur.
    """
    _providers: List[Type[MusicProvider]] = []

    @classmethod
    def register_provider(cls, provider_class: Type[MusicProvider]):
        """Permet d'enregistrer un nouveau provider au démarrage"""
        if provider_class not in cls._providers:
            cls._providers.append(provider_class)

    @staticmethod
    def initialize():
        """
        Découvre et enregistre automatiquement tous les providers
        présents dans le dossier 'providers' et ses sous-dossiers.
        """
        import importlib
        from pathlib import Path

        ProviderFactory._providers = []
        providers_dir = Path(__file__).parent
        
        for provider_path in providers_dir.rglob("provider.py"):
            relative_parts = provider_path.relative_to(providers_dir).parts
            module_name = "." + ".".join([p.replace(".py", "") for p in relative_parts])
            
            try:
                module = importlib.import_module(module_name, package="downloader.providers")
                for name in dir(module):
                    obj = getattr(module, name)
                    if isinstance(obj, type) and issubclass(obj, MusicProvider) and obj is not MusicProvider:
                        ProviderFactory.register_provider(obj)
            except Exception as e:
                logger.exception("Erreur chargement provider depuis %s", provider_path)

    @staticmethod
    def get_provider(url: str, auth_token: Optional[str] = None, refresh_token: Optional[str] = None, user_id: Optional[str] = None) -> MusicProvider:
        """
        Analyse l'URL et retourne une instance du provider correspondant.
        auth_token, refresh_token et user_id peuvent être passés pour les opérations d'écriture.
        """
        if not ProviderFactory._providers:
            ProviderFactory.initialize()

        url = url.strip()

        for ProviderClass in ProviderFactory._providers:
            try:
                try:
                    provider = ProviderClass(auth_token=auth_token, refresh_token=refresh_token, user_id=user_id)
                except TypeError:
                    try:
                        provider = ProviderClass(auth_token=auth_token, refresh_token=refresh_token)
                    except TypeError:
                        provider = ProviderClass(auth_token=auth_token)
                
                if provider.supports_url(url):
                    logger.info(f"Provider détecté : {ProviderClass.__name__} pour l'URL : {url[:30]}...")
                    return provider
            except Exception as e:
                logger.debug(f"Le provider {ProviderClass.__name__} ne supporte pas l'URL ou erreur init: {e}")
                continue
        
        raise ValueError(f"URL non supportée ou provider inconnu : {url}")
