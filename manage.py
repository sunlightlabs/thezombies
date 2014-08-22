#!/usr/bin/env python

from flask.ext.script import Manager
from flask.ext.assets import ManageAssets

from thezombies.site import app, db
from thezombies.models import load_agencies_from_json
from thezombies.staticfiles import assets

manager = Manager(app)
# manager.add_command("assets", ManageAssets(assets))

@manager.command
def createtables():
    db.create_all()

@manager.command
def droptables():
    db.drop_all()

@manager.command
def loaddata():
    objects = load_agencies_from_json()
    db.session.add_all(objects)
    db.session.commit()

if __name__ == "__main__":
    manager.run()