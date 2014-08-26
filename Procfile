web: gunicorn thezombies.wsgi:application --log-file -
worker: celery -A thezombies worker --loglevel=info --autoscale=8,3 -P gevent -n worker1.%h
worker: celery -A thezombies worker --loglevel=info --autoscale=8,3 -P gevent -n worker2.%h
worker: celery -A thezombies worker --loglevel=info --autoscale=8,3 -P gevent -n worker3.%h
