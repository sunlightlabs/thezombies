#!/usr/bin/env python

import os
import json

from flask import Flask, render_template
from flask_sockets import Sockets

from thezombies.models import db, Agency
from thezombies.staticfiles import assets

app = Flask(__name__)
sockets = Sockets(app)
assets.init_app(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')
db.init_app(app)
app.config['DEBUG'] = os.environ.get('DEBUG') == 'True'


@app.route('/')
def main():
    agencies = Agency.query.all()
    return render_template('home.html', agencies=agencies)

@app.route('/agency/<slug>')
def agency(slug):
    agency = Agency.query.filter_by(slug=slug).first_or_404()
    return render_template('agency.html', agency=agency)

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@sockets.route('/com')
def echo_socket(ws):
    while True:
        message = ws.receive()
        message_obj = json.loads(message)
        json_msg = json.dumps(message_obj)
        ws.send(json_msg)
