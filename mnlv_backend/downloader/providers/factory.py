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
    def get_provider(url: str, auth_token: Optional[str] = None) -> MusicProvider:
        """
        Analyse l'URL et retourne une instance du provider correspondant.
        auth_token peut être passé pour les opérations d'écriture (playlists).
        """
        if not ProviderFactory._providers:
            ProviderFactory.initialize()

        for ProviderClass in ProviderFactory._providers:
            try:
                provider = ProviderClass(auth_token=auth_token)
            except TypeError:
                provider = ProviderClass()
                
            if provider.supports_url(url):
                return provider
        
        raise ValueError(f"URL non supportée ou provider inconnu : {url}")
