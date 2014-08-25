web: gunicorn thezombies.wsgi:application --log-file -
celery: celery -A thezombies worker --loglevel=info -P gevent