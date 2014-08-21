#!/usr/bin/env python

import os.path
import json

from flask import Flask, render_template
from flask_sockets import Sockets
from flask.ext.assets import Environment, Bundle

from thezombies.models import agencies

app = Flask(__name__)
sockets = Sockets(app)
assets = Environment(app)

FOUNDATION_ASSETS_ROOT = 'bower_components/foundation/'
FOUNDATION_VENDOR_DIR = os.path.join(FOUNDATION_ASSETS_ROOT, 'js/vendor/')

js_all = Bundle(os.path.join(FOUNDATION_VENDOR_DIR, 'jquery.js'),
            os.path.join(FOUNDATION_VENDOR_DIR, 'jquery.cookie.js'),
            os.path.join(FOUNDATION_VENDOR_DIR, 'placeholder.js'),
            os.path.join(FOUNDATION_VENDOR_DIR, 'fastclick.js'),
            os.path.join(FOUNDATION_VENDOR_DIR, 'modernizr.js'),
            os.path.join(FOUNDATION_ASSETS_ROOT, 'js/foundation.min.js'),
            'js/main.js',
            filters='uglifyjs', output='js/bundle.min.js')
assets.register('js_all', js_all)

js_audit = Bundle('bower_components/reconnectingWebsocket/reconnecting-websocket.js',
            'js/audit.js',
            filters='uglifyjs', output='js/audit.min.js')
assets.register('js_audit', js_audit)

all_css = Bundle('bower_components/foundation/css/normalize.css',
                 'bower_components/foundation/css/foundation.css',
                 'css/site.css',
                 filters='cssmin', output="css/all.css")
assets.register('all_css', all_css)

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

@sockets.route('/com')
def echo_socket(ws):
    while True:
        message = ws.receive()
        message_obj = json.loads(message)
        json_msg = json.dumps(message_obj)
        ws.send(json_msg)
