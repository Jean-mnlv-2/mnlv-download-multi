import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('mnlv_backend')

# Utilise une chaîne ici pour que le worker n'ait pas à sérialiser
# l'objet de configuration lors de l'utilisation de Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
