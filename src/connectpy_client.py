# -*- coding: utf-8 -*-

import requests
import argparse
import time
import sys
import signal
import yaml

from termios import tcflush, TCIFLUSH


class PlayerClient(object):
    def __init__(self, player_id, server_url):
        self.game_state = {}
        self.last_game_state = {}
        self.id = player_id
        self.server_url = server_url

    @property
    def opposing_player(self):
        for player_id, indicator in self.game_state['players'].items():
            if player_id != self.id:
                return player_id
        else:
            return None

    @property
    def can_move(self):
        return self.game_state['turn'] == self.id

    def make_request(self, endpoint, data):
        resp = requests.post(
            self.server_url + endpoint, json=data)
        if resp:
            self.last_game_state = self.game_state
            self.game_state = resp.json()

        return resp

    def join_server(self):
        return self.make_request('/join', {'player_id': self.id})

    def update_status(self):
        return self.make_request('/status', {'player_id': self.id})

    def make_move(self, column):
        return self.make_request(
            '/move', {'player_id': self.id, 'column': column})

    def close_game(self):
        return self.make_request(
            '/close', {'player_id': self.id})

    def wait_for_opponent(self):
        while not self.opposing_player:
            self.update_status()
            time.sleep(1)

    def printable_state(self):
        s = [['[   ]' if e == 0
             else '[ {} ]'.format(play_piece(e)) for e in row]
             for row in self.game_state['game']]
        s.append(['[ {} ]'.format(n + 1) for n in range(
            self.game_state['columns'])])
        lens = [max(map(len, col)) for col in zip(*s)]
        fmt = ' '.join('{{:{}}}'.format(x) for x in lens)
        table = [fmt.format(*row) for row in s]
        return '\n'.join(table)

    def get_move(self):
        column = None
        while not column:
            try:
                tcflush(sys.stdin, TCIFLUSH)
                number = int(input(
                    "Pick a column ^, or press 0 to end game: "))
                if number == 0:
                    self.close_game()
                    column = number
                    break
                elif not 1 <= number <= self.game_state['columns']:
                    print('Out of bounds! - Pick again...')
                else:
                    column = number
            except ValueError:
                print('Not an integer! - Pick again...')

        return column - 1


def play_piece(player_indicator):
        return 'x' if player_indicator == 1 else 'o'


def get_player_client(server_url):
    player_id = input("Please enter your name: ")
    player_client = PlayerClient(player_id, server_url)

    return player_client


def try_join_game(server_url):
    player_client = get_player_client(server_url)
    print("Hi {}! - Connecting to game...".format(player_client.id))
    resp = player_client.join_server()

    if resp.status_code == 409:
        print(resp.json()['error'])
        new_player_id = None
        while new_player_id == player_client.id:
            new_player_id = input("Please enter a different name: ")
        player_client.id = new_player_id
        resp = player_client.join_server()

    if resp:
        print("Player {} joined successfully!".format(player_client.id))
        print("Waiting for opponent...")
        player_client.wait_for_opponent()
        print("Your opponent is {}, good luck!".format(
            player_client.opposing_player))
        print(player_client.printable_state())
        return player_client
    else:
        print(resp.json()['error'])
        return False


def print_state_change(player_client):
    if player_client.game_state != player_client.last_game_state:
        print(player_client.printable_state())
    else:
        print('Waiting for opponent...\r', end="")


def run_client(
        server_url='http://localhost:5000', interval=0.5, wait_timeout=30):
    player_client = None
    while not player_client:
        player_client = try_join_game(server_url)

    time_waiting = 0

    while True:
        if player_client.can_move:
            time_waiting = 0
            column = player_client.get_move()
            resp = player_client.make_move(column)
            if not resp:
                print(resp.json()['error'])
        else:
            time_waiting += interval
            if time_waiting >= wait_timeout:
                player_client.close_game()
                print("Closing game due to inactiviy...")
            player_client.update_status()

        winner = player_client.game_state['winner']
        if winner:
            print("{} Wins! - Resetting".format(winner))

        player_closed = player_client.game_state['closed']
        if player_closed:
            print("Game closed by {}, goodbye!".format(player_closed))
            break

        print_state_change(player_client)
        time.sleep(interval)


def get_config(config_path):
    config = {}
    if config_path:
        with open(config_path) as f:
            config.update(yaml.load(f))
    else:
        print("No config specified, defaults will be used")
    return config


def main():
    parser = argparse.ArgumentParser(description='ConnectPy user client')
    parser.add_argument(
        '-c',
        dest='config_path',
        action='store',
        help='ConnectPy client config'
    )
    args = parser.parse_args()
    config = get_config(args.config_path)
    run_client(**config)

if __name__ == '__main__':
    main()
