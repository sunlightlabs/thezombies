import os

# Basic config
# IMPORTANT: Using pickle exclusively because we are passing objects that are potentially invalid JSON.
BROKER_URL = os.getenv('BROKER_URL', 'amqp://10.64.7.102:5672//')
CELERY_DEFAULT_RATE_LIMIT = '100/s'
CELERY_ACCEPT_CONTENT = ['pickle']
CELERY_MESSAGE_COMPRESSION = 'gzip'
# CELERY_DISABLE_RATE_LIMITS = True
# Tasks
CELERY_TASK_SERIALIZER = 'pickle'
CELERYD_TASK_TIME_LIMIT = 10 * 60
# Results
CELERY_TASK_RESULT_EXPIRES = 7200  # 2 hours.
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'amqp://10.64.7.102:5672//')
CELERY_RESULT_SERIALIZER = 'pickle'
