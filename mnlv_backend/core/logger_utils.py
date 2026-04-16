import logging
import os
from django.conf import settings

def get_mnlv_logger(name: str):
    """
    Retourne un logger configuré pour le projet MNLV.
    S'adapte à l'environnement (DEBUG ou PROD).
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    try:
        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.FileHandler(os.path.join(log_dir, 'mnlv.log'))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        pass

    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logger.setLevel(level)
    
    return logger
