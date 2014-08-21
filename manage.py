#!/usr/bin/env python

from flask.ext.script import Manager
from flask.ext.assets import ManageAssets

from thezombies.site import app
from thezombies.staticfiles import assets

manager = Manager(app)
# manager.add_command("assets", ManageAssets(assets))

if __name__ == "__main__":
    manager.run()