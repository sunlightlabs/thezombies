web: gunicorn --worker-class socketio.sgunicorn.GeventSocketIOWorker thezombies.site:app
celery: celery -A thezombies.tasks worker --loglevel=info