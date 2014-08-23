#!/usr/bin/env python

from flask.ext.script import Manager
# from flask.ext.assets import ManageAssets

from thezombies.site import app
from thezombies.models import load_agencies_from_json
from thezombies.staticfiles import assets

manager = Manager(app)
# manager.add_command("assets", ManageAssets(assets))

# @manager.command
# def createtables():
#     "Creates database tables"
#     db.create_all()

# @manager.command
# def droptables():
#     "Drops database tables"
#     db.drop_all()

# @manager.command
# def loaddata():
#     "Loads some default data into the database"
#     objects = load_agencies_from_json()
#     db.session.add_all(objects)
#     db.session.commit()

if __name__ == "__main__":
    manager.run()