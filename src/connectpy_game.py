# -*- coding: utf-8 -*-

from itertools import islice, cycle

class ColumnOutOfBoundsException(Exception):
    pass

class FullColumnException(Exception):
    pass

class FullGameException(Exception):
    pass

class PlayersNotReadyException(Exception):
    pass

class PlayerInvalidException(Exception):
    pass

class AlreadyJoinedException(Exception):
    pass

def window(seq, n):
    "Returns a sliding window (of width n) over data from the iterable"
    "   s -> (s0,s1,...s[n-1]), (s1,s2,...,sn), ...                   "
    it = iter(seq)
    result = tuple(islice(it, n))
    if len(result) == n:
        yield result
    for elem in it:
        result = result[1:] + (elem,)
        yield result

def surrounding_slice(arr, idx, n):
    return arr[max(idx - n, 0):min(idx + n, len(arr))]

def surrounding_diag(arr, x, y, n, flip=False):
    diag = []
    direction = 1 if flip else -1
    for i in range(-n, n):
        xi, yi = x - i, y + (i * direction)
        try:
            if xi * yi >= 0:
                diag.append(arr[xi][yi])
        except IndexError:
            continue
    return diag

class ConnectPyGame(object):
    def __init__(self, config):
        self.config = config
        self.columns = config.get('game_columns', 9)
        self.rows = config.get('game_rows', 6)
        self.win_zone = config.get('win_zone', 5)
        self.started = False
        self.max_players = 2
        self.players = {}
        self.player_cycle = None
        self.current_turn = None
        self.winner = None
        self.last_drop = None
        self.closed = False
        self.grid = []

    @property
    def players_ready(self):
        return len(self.players) == self.max_players

    @property
    def dict(self):
        return {
            "game": self.grid,
            "turn": self.current_turn,
            "players": self.players,
            "winner": self.winner,
            "started": self.started,
            "last_drop": self.last_drop,
            "rows": self.rows,
            "columns": self.columns,
            "closed": self.closed
        }

    def start_game(self):
        if self.players_ready:
            self.reset_game()
            self.player_cycle = cycle(self.players.keys())
            self.current_turn = self.next_player()
            self.started = True
        else:
            raise PlayersNotReadyException(
                "Calling start_game before all players have connected")

    def reset_game(self):
        self.grid = []
        for row in range(self.rows):
            self.grid.append([0 for column in range(self.columns)])
        self.last_drop = None
        self.winner = None

    def drop_disc(self, player_id, column_idx):
        player_indicator = self.get_player_indicator(player_id)

        drop_coords = None
        try:
            for row_idx, row in reversed(list(enumerate(self.grid))):
                if row[column_idx] == 0:
                    row[column_idx] = player_indicator
                    drop_coords = (row_idx, column_idx)
                    break
            else:
                raise FullColumnException(
                    "Player {} - Column {} full".format(
                        player_id, column_idx))
        except IndexError:
            raise ColumnOutOfBoundsException(
                "Player {} - Column {} out of bounds".format(
                    player_id, column_idx))

        self.current_turn = self.next_player()
        self.last_drop = drop_coords

        is_won = self.is_winner(player_indicator, drop_coords)
        if is_won:
            self.winner = player_id

        return is_won


    def axis_has_winner(self, player, win_axis):
        for seq in window(win_axis, self.win_zone):
            if all(n == player for n in seq):
                return True

    def is_winner(self, player, drop_coords):
        row_idx, column_idx = drop_coords

        # Get the surrounding win zone on the horizontal axis
        win_hor = surrounding_slice(
            self.grid[row_idx], column_idx, self.win_zone)

        # Get the surrounding win zone on the vertical axis
        win_vert = surrounding_slice(
            list(zip(*self.grid))[column_idx], row_idx, self.win_zone)

        # Get the surrounding win zone on the diagonal axis
        win_diag_main = surrounding_diag(
            self.grid, row_idx, column_idx, self.win_zone, flip=False)

        # Get the surrounding win zone on the flipped diagonal axis
        win_diag_flip = surrounding_diag(
            self.grid, row_idx, column_idx, self.win_zone, flip=True)

        # Return true is any win zone axis contains a winning chain
        return any(self.axis_has_winner(player, win_axis) for win_axis in
                   [win_hor, win_vert, win_diag_main, win_diag_flip])

    def add_player(self, player_id):
        if not self.players_ready:
            if player_id not in self.players:
                self.players[player_id] = len(self.players) + 1
            else:
                raise AlreadyJoinedException(
                    "Player {} already joined".format(player_id))
        else:
            raise FullGameException("Maximum players reached")

    def is_turn(self, player_id):
        return self.current_turn == player_id

    def next_player(self):
        return self.player_cycle.__next__()

    def get_player_indicator(self, player_id):
        try:
            return self.players[player_id]
        except KeyError:
            raise PlayerInvalidException(
                "Player ID {} not joined".format(player_id))

    def close(self, player_id):
        self.closed = player_id

