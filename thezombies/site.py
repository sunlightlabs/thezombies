#!/usr/bin/env python

import os
import json

from flask import Flask, render_template
from flask.ext.socketio import SocketIO, emit, send

from thezombies.models import db, Agency
from thezombies.staticfiles import assets
from thezombies.tasks import fetch_url, parse_json_from_job

app = Flask(__name__)
assets.init_app(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')
db.init_app(app)
app.config['DEBUG'] = os.environ.get('DEBUG') == 'True'
socketio = SocketIO(app)

SOCKET_NAMESPACE = '/com'

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

@socketio.on('connect', namespace=SOCKET_NAMESPACE)
def test_connect():
    send('Connection established with server')

@socketio.on('message', namespace=SOCKET_NAMESPACE)
def handle_message(message):
    print('received message: ' + repr(message))
    send('Message received')
