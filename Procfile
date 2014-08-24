web: gunicorn thezombies.wsgi:application
celery: celery -A thezombies worker --loglevel=info -P gevent