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


def player_joined(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        try:
            player_id = request.json.get('player_id')
            current_app.game.get_player_indicator(player_id)
            request.player_id = player_id
        except conn_py.PlayerInvalidException as e:
            return error_response(str(e), status=403)
        else:
            resp = func(*args, **kwargs)
        return resp
    return decorator


def required_fields(fields):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            missing = []
            if request.mimetype == 'application/json':
                for field in fields:
                    try:
                        setattr(request, field, request.json[field])
                    except KeyError:
                        missing.append(field)
                if missing:
                    return error_response(
                        "{} field(s) required".format(','.join(missing)),
                        status=400)
            else:
                return error_response(
                    "Unsupported Content-Type - expected: application/json",
                    status=415)
            resp = func(*args, **kwargs)
            return resp
        return wrapper
    return decorator


@paths.route('/join', methods=['POST'])
@required_fields(['player_id'])
@game_started
def join():
    try:
        current_app.game.add_player(request.player_id)
    except conn_py.AlreadyJoinedException as e:
        return error_response(str(e), status=409)
    else:
        print("Player {} connected".format(request.player_id))

    if current_app.game.players_ready:
        current_app.game.start_game()
        print("Game started")

    return ok_response(current_app.game.dict)


@paths.route('/status', methods=['GET'])
@required_fields(['player_id'])
@player_joined
def status():
    return ok_response(current_app.game_dict)


@paths.route('/move', methods=['POST'])
@required_fields(['player_id', 'column'])
@player_joined
def move():
    player_id = request.json['player_id']
    column = request.json['column']

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
@required_fields(['player_id'])
@player_joined
def close():
    new_game(current_app)
    print("Game closed by {}".format(request.player_id))

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
