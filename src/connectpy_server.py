import yaml
import os
import connectpy.connectpy_game as conn_py

from functools import wraps
from flask import Flask, Blueprint, request, jsonify, current_app

paths = Blueprint('paths', __name__)


def game_started(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        if current_app.game.started or current_app.game.players_ready:
            return error_response(
                "ConnectPy game in progress", status=503)
        else:
            resp = func(*args, **kwargs)
        return resp
    return decorator


@paths.route('/join', methods=['POST'])
@game_started
def join():
    player_id = request.json['player_id']

    try:
        current_app.game.add_player(player_id)
    except conn_py.AlreadyJoinedException as e:
        return error_response(str(e), status=409)
    else:
        print("Player {} connected".format(player_id))

    if current_app.game.players_ready:
        current_app.game.start_game()
        print("Game started")
    return ok_response(current_app.game.dict)


@paths.route('/move', methods=['POST'])
def move():
    player_id = request.json['player_id']
    column = request.json['column']

    try:
        current_app.game.get_player_indicator(player_id)
    except conn_py.PlayerInvalidException as e:
        return error_response(str(e), status=403)

    if current_app.game.is_turn(player_id):
        try:
            winner = current_app.game.drop_disc(player_id, column)
        except (conn_py.FullColumnException,
                conn_py.ColumnOutOfBoundsException) as e:
            return error_response(str(e), status=400)

        game_dict = current_app.game.dict
        current_app.game.print_grid()
        if winner:
            print("{} Wins! - Resetting".format(player_id))
            current_app.game.reset_game()
        return ok_response(game_dict)
    else:
        return error_response(
            "Not your turn! - Enhance your calm", status=420)


@paths.route('/close', methods=['POST'])
def close():
    player_id = request.json['player_id']
    if current_app.game.started:
        new_game(current_app)
    print("Game closed by {}".format(player_id))

    return ok_response({'closed': True})


def get_config():
    config_filename = os.environ.get('CONNECTPY_SETTINGS')
    config = {}
    if config_filename:
        with open(config_filename) as f:
            config.update(yaml.load(f))
    else:
        print("No config specified, using defaults")
    return config


def error_response(error_str, status=400):
    resp = jsonify({'error': error_str})
    resp.status_code = status
    return resp


def ok_response(data):
    resp = jsonify(data)
    resp.status_code = 200
    return resp

def new_game(app):
    app.game = conn_py.ConnectPyGame(app.config)


def create_app():
    config = get_config()
    app = Flask(__name__)
    app.config.update(config)
    app.register_blueprint(paths)
    new_game(app)

    return app

if __name__ == '__main__':
    create_app()
