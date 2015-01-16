from __future__ import absolute_import

import os

from celery import Celery

try:
    import dotenv
    dotenv.read_dotenv('/projects/thezombies/.env')
except ImportError:
    pass
except Exception:
    pass

from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thezombies.settings')

app = Celery('thezombies', task_cls='django_atomic_celery:PostTransactionTask')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('celeryconfig')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
