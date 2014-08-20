#!/usr/bin/env python

from flask import Flask, render_template
from flask_sockets import Sockets

from thezombies.models import agencies

app = Flask(__name__)

sockets = Sockets(app)

@app.route('/')
def main():
    return render_template('home.html', agencies=agencies)

@app.route('/agency/<slug>')
def agency(slug):
    matches = list(filter(lambda x: getattr(x, 'slug', None) == slug, agencies))
    if len(matches) == 1:
        return render_template('agency.html', agency=matches[0])
    else:
        abort(404)

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@sockets.route('/echo')
def echo_socket(ws):
    while True:
        message = ws.receive()
        ws.send(message)
