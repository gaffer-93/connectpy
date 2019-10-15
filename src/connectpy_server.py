# -*- coding: utf-8 -*-
import yaml
import os

from flask import Flask, Blueprint, request, current_app, jsonify

connectpy_root = Blueprint('connectpy_root', __name__)

def get_config():
    config_filename = os.environ.get(
        'CONNECTPY-SERVER-SETTINGS', 'conf/connectpy-server.yaml')
    config = {}
    with open(config_filename) as f:
        config.update(yaml.load(f))
    return config

@connectpy_root.before_app_first_request
def init_connectpy_app():
    pass

def create_app():
    config = get_config
    app = Flask(__name__)
    app.config.update(config)
    app.config['PROPOGATE_EXCEPTIONS'] = True
    app.register_blueprint(connectpy_root)
    app.logger.info("URL Mappings: %s" % app.url_map)

    return app