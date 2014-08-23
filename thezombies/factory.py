import os

from celery import Celery
from flask import Flask
from flask.ext.socketio import SocketIO
from flask.ext.sqlalchemy import SQLAlchemy
from thezombies.staticfiles import assets
from flask.ext.script import Manager

db = SQLAlchemy()
socketio = SocketIO()


def create_app(package_name, settings_override=None):
    app = Flask(package_name, instance_relative_config=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')
    app.config['CELERY_BROKER_URL'] = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    app.config['CELERY_RESULT_BACKEND'] = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    app.config['DEBUG'] = os.environ.get('DEBUG', 'False') == 'True'
    app.config.from_object(settings_override)

    db.init_app(app)
    assets.init_app(app)
    socketio.init_app(app)

    return app


def create_celery_app(app=None):
    app = app or create_app(__name__)
    celery = Celery(__name__, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


