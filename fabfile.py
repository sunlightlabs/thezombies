from fabric.api import local
from fabric.contrib import django
from fabric.colors import red, yellow, green

django.project('thezombies')
from django.conf import settings

databases = settings.DATABASES
default_db = databases.get('default')
DEFAULT_DB_NAME = default_db.get('NAME', None)


def name():
    print(DEFAULT_DB_NAME)


def bigbang():
    if DEFAULT_DB_NAME:
        local('dropdb {0} -i --if-exists'.format(DEFAULT_DB_NAME))
        print(red('Dropped db {0}'.format(DEFAULT_DB_NAME)))
        local('createdb {0}'.format(DEFAULT_DB_NAME))
        local('psql {0} -f thezombies/db_config.sql'.format(DEFAULT_DB_NAME))
        print(green('Created db {0}'.format(DEFAULT_DB_NAME)))
        local('./manage.py migrate')
        local('./manage.py loaddata thezombies/fixtures/agencies.json')
        print(green('Migrated data and loaded agencies fixtures'))
    else:
        print(yellow('No default database to destroy'))
