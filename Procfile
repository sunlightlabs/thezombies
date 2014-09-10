web: gunicorn thezombies.wsgi:application --log-file -
worker: celery -A thezombies worker --loglevel=info --concurrency=4 -P eventlet -n worker1.%h
worker: celery -A thezombies worker --loglevel=info --concurrency=4 -P eventlet -n worker2.%h
worker: celery -A thezombies worker --loglevel=info --concurrency=4 -P eventlet -n worker3.%h
worker: celery -A thezombies worker --loglevel=info --concurrency=4 -P eventlet -n worker4.%h
worker: celery -A thezombies worker --loglevel=info --concurrency=4 -P eventlet -n worker5.%h
worker: celery -A thezombies worker --loglevel=info --concurrency=4 -P eventlet -n worker6.%h
