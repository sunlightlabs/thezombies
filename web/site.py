#!/usr/bin/env python

from flask import Flask, render_template
from flask_sockets import Sockets

from thezombies.models import agencies

app = Flask(__name__)
sockets = Sockets(app)

@app.route('/')
def main():
    return render_template('base.html', agencies=agencies)

@sockets.route('/echo')
def echo_socket(ws):
    while True:
        message = ws.receive()
        ws.send(message)
