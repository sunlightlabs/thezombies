#!/usr/bin/env python

from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager, Shell
from flask.ext.migrate import Migrate, MigrateCommand

from thezombies.factory import create_app
from thezombies import models
from thezombies.models import db
from thezombies.staticfiles import assets

app = create_app(__name__)
manager = Manager(app)
migrate = Migrate(app, db)

@manager.shell
def make_shell_context():
    return dict(app=app, db=db, models=models)

manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)
# manager.add_command("assets", ManageAssets(assets))


if __name__ == "__main__":
    manager.run()