import os.path

from flask.ext.assets import Environment, Bundle

FOUNDATION_ASSETS_ROOT = 'bower_components/foundation/'
FOUNDATION_VENDOR_DIR = os.path.join(FOUNDATION_ASSETS_ROOT, 'js/vendor/')

assets = Environment()

js_all = Bundle(os.path.join(FOUNDATION_VENDOR_DIR, 'jquery.js'),
            os.path.join(FOUNDATION_VENDOR_DIR, 'jquery.cookie.js'),
            os.path.join(FOUNDATION_VENDOR_DIR, 'placeholder.js'),
            os.path.join(FOUNDATION_VENDOR_DIR, 'fastclick.js'),
            os.path.join(FOUNDATION_VENDOR_DIR, 'modernizr.js'),
            os.path.join(FOUNDATION_ASSETS_ROOT, 'js/foundation.min.js'),
            'js/main.js',
            filters='uglifyjs', output='js/gen/bundle.min.js')
assets.register('js_all', js_all)

js_audit = Bundle('bower_components/reconnectingWebsocket/reconnecting-websocket.js',
            'js/audit.js',
            filters='uglifyjs', output='js/gen/audit.min.js')
assets.register('js_audit', js_audit)

all_css = Bundle('bower_components/foundation/css/normalize.css',
                 'bower_components/foundation/css/foundation.css',
                 'css/site.css',
                 filters='cssmin', output="css/gen/all.css")
assets.register('all_css', all_css)
