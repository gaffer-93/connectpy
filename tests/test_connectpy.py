#!/usr/bin/env python
# -*- coding: utf-8 -*-

import flask_testing
import connectpy_server
import connectpy_game
import unittest
import os
import mock


class TestConnectpyServer(flask_testing.TestCase):

    def create_app(self):
        self.dir = os.path.dirname(os.path.abspath(__file__))
        os.environ['CONNECTPY_SETTINGS'] = os.path.join(self.dir, 'test.cfg')
        return connectpy_server.create_app()

    def setUp(self):
        self.mock_response = mock.Mock()
        self.mock_game_obj = mock.Mock()
        self.app.game = self.mock_game_obj
        self.player_id = 'deadbeef'
        self.client = self.app.test_client()

    def _test_not_joined(self, endpoint):
        data = {'player_id': self.player_id, 'column': 1}
        self.app.game.get_player_indicator.side_effect = \
            connectpy_server.conn_py.PlayerInvalidException
        rv = self.client.post(endpoint, json=data)
        self.assertEqual(rv.status_code, 403)

    def _test_bad_mimetype(self, endpoint):
        data = {'player_id': self.player_id}
        rv = self.client.post(endpoint, data=data)
        self.assertEqual(rv.status_code, 415)

    def _test_required_fields(self, endpoint, data):
        rv = self.client.post(endpoint, json=data)
        self.assertEqual(rv.status_code, 400)

    def test_status_player_not_joined(self):
        self._test_not_joined('/status')

    def test_status_bad_mimetype(self):
        self._test_bad_mimetype('/status')

    def test_status_required_fields(self):
        self._test_required_fields('/status', {})

    def test_status_ok(self):
        test_data = {'test': 'ok'}
        self.app.game.dict = test_data

        rv = self.client.post('/status', json={'player_id': self.player_id})
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json, test_data)

    def test_join_required_fields(self):
        self._test_required_fields('/join', {})

    def test_join_bad_mimetype(self):
        self._test_bad_mimetype('/join')

    def test_join_game_started(self):
        self.app.game.closed = False
        self.app.game.started = True
        self.app.game.players_ready = True

        rv = self.client.post('/join', json={'player_id': self.player_id})
        self.assertEqual(rv.status_code, 503)

    def test_join_game_already_joined(self):
        self.app.game.closed = False
        self.app.game.started = False
        self.app.game.players_ready = False
        self.app.game.add_player.side_effect = \
            connectpy_server.conn_py.AlreadyJoinedException

        rv = self.client.post('/join', json={'player_id': self.player_id})
        self.assertEqual(rv.status_code, 409)

    def test_join_game_ok(self):
        self.app.game.closed = False
        self.app.game.started = False
        self.app.game.players_ready = False
        test_data = {'test': 'ok'}
        self.app.game.dict = test_data

        rv = self.client.post('/join', json={'player_id': self.player_id})
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json, test_data)

    def test_move_player_not_joined(self):
        self._test_not_joined('/move')

    def test_move_bad_mimetype(self):
        self._test_bad_mimetype('/move')

    def test_move_required_fields(self):
        self._test_required_fields('/move', {})

    def test_move_not_your_turn(self):
        self.app.game.is_turn.return_value = False

        rv = self.client.post(
            '/move', json={'player_id': self.player_id, 'column': 1})
        self.assertEqual(rv.status_code, 420)

    def test_move_invalid(self):
        self.app.game.is_turn.return_value = True

        # Test FullColumnException
        self.app.game.drop_disc.side_effect = \
            connectpy_server.conn_py.FullColumnException
        rv = self.client.post(
            '/move', json={'player_id': self.player_id, 'column': 1})
        self.assertEqual(rv.status_code, 400)

        # Test ColumnOutOfBoundsException
        self.app.game.drop_disc.side_effect = \
            connectpy_server.conn_py.ColumnOutOfBoundsException
        rv = self.client.post(
            '/move', json={'player_id': self.player_id, 'column': 1})
        self.assertEqual(rv.status_code, 400)

    def test_move_ok(self):
        self.app.game.is_turn.return_value = True
        test_data = {'test': 'ok'}
        self.app.game.dict = test_data

        # Test normal move
        self.app.game.drop_disc.return_value = False
        rv = self.client.post(
            '/move', json={'player_id': self.player_id, 'column': 1})
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json, test_data)

        # Test winning move
        self.app.game.drop_disc.return_value = True
        rv = self.client.post(
            '/move', json={'player_id': self.player_id, 'column': 1})
        self.assertEqual(rv.status_code, 200)
        self.app.game.reset_game.assert_called_once()

    def test_close_player_not_joined(self):
        self._test_not_joined('/close')

    def test_close_bad_mimetype(self):
        self._test_bad_mimetype('/close')

    def test_close_required_fields(self):
        self._test_required_fields('/close', {})

    def test_close_ok(self):
        test_data = {'test': 'ok'}
        self.app.game.dict = test_data

        rv = self.client.post('/close', json={'player_id': self.player_id})
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json, test_data)


class TestConnectpyGame(unittest.TestCase):

    def setUp(self):
        self.config = {
            "game_columns": 9,
            "game_rows": 6,
            "win_zone": 5
        }
        self.game = connectpy_game.ConnectPyGame(self.config)

    def test_players_ready(self):
        # No players
        self.assertFalse(self.game.players_ready)
        # 1 player
        self.game.players = {"a": 1}
        self.assertFalse(self.game.players_ready)
        # 2 players
        self.game.players["b"] = 2
        self.assertTrue(self.game.players_ready)

    def test_dict(self):
        expected = {
            "game": self.game.grid,
            "turn": self.game.current_turn,
            "players": self.game.players,
            "winner": self.game.winner,
            "started": self.game.started,
            "last_drop": self.game.last_drop,
            "rows": self.game.rows,
            "columns": self.game.columns,
            "closed": self.game.closed
        }
        self.assertEqual(expected, self.game.dict)

    def test_start_game_players_not_ready(self):
        # No players
        with self.assertRaises(connectpy_game.PlayersNotReadyException):
            self.game.start_game()

    def test_start_game_ok(self):
        # Test not initialised
        self.assertFalse(self.game.grid)
        self.assertFalse(self.game.current_turn)
        self.assertFalse(self.game.started)

        # Players ready
        self.game.players = {"a": 1, "b": 2}
        self.game.start_game()
        self.assertTrue(self.game.grid)
        self.assertTrue(self.game.current_turn in self.game.players)
        self.assertTrue(self.game.started)

    def test_reset_grid(self):
        self.game.grid = [['test']]
        self.game.last_drop = (1, 2)
        self.game.winner = "a"
        self.game.reset_game()

        self.assertTrue(
            all([all([n == 0 for n in row]) for row in self.game.grid]))
        self.assertFalse(self.game.last_drop)
        self.assertFalse(self.game.winner)

    def test_drop_disc_bad_move(self):
        self.game.players = {"a": 1, "b": 2}
        self.game.start_game()

        with self.assertRaises(connectpy_game.FullColumnException):
            for _ in range(self.game.rows + 1):
                self.game.drop_disc("a", 1)

        with self.assertRaises(connectpy_game.ColumnOutOfBoundsException):
            self.game.drop_disc("a", self.game.columns + 1)

    def test_drop_disc_ok(self):
        self.game.players = {"a": 1, "b": 2}
        self.game.start_game()

        for i in range(self.game.columns):
            # Drop player's discs and check turn is handed over
            self.game.drop_disc(self.game.current_turn, i)
            last_turn = self.game.current_turn
            last_drop = self.game.last_drop

            self.game.drop_disc(self.game.current_turn, i)
            self.assertFalse(self.game.current_turn == last_turn)
            self.assertFalse(self.game.last_drop == last_drop)

        self.assertEqual(self.game.winner, "b")

        # Test expected game state - last 2 rows filled with respective player
        # indicators
        empty_row = [0 for _ in range(self.game.columns)]
        expected_state = [empty_row for row in range(self.game.rows)]
        expected_state[-1] = [1 for _ in range(self.game.columns)]
        expected_state[-2] = [2 for _ in range(self.game.columns)]
        self.assertEqual(self.game.grid, expected_state)

    def test_axis_has_winner(self):
        self.game.win_zone = 5
        win_axis = [1, 1, 1, 0, 0, 0, 0, 0, 0]
        self.assertFalse(self.game.axis_has_winner(1, win_axis))
        win_axis = [1, 1, 1, 1, 1, 0, 0, 0, 0]
        self.assertTrue(self.game.axis_has_winner(1, win_axis))

    def test_is_winner(self):
        self.game.win_zone = 5

        no_win_state = [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 2, 0, 0, 0, 0, 0, 0],
            [0, 0, 2, 1, 2, 0, 0, 0, 0],
            [0, 0, 2, 2, 2, 1, 1, 0, 0],
            [0, 0, 2, 1, 1, 1, 1, 0, 0]]
        drop_coords = [4, 6]
        self.game.grid = no_win_state
        self.assertFalse(self.game.is_winner(1, drop_coords))

        horizontal_win_state = [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 2, 0, 0, 0, 0, 0, 0],
            [0, 0, 2, 1, 2, 0, 0, 0, 0],
            [0, 0, 2, 2, 2, 1, 0, 0, 0],
            [0, 0, 2, 1, 1, 1, 1, 1, 0]]
        drop_coords = [5, 7]
        self.game.grid = horizontal_win_state
        self.assertTrue(self.game.is_winner(1, drop_coords))

        vertical_win_state = [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 2, 0, 0, 0, 0, 0, 0],
            [0, 0, 2, 0, 0, 0, 0, 0, 0],
            [0, 0, 2, 1, 0, 1, 0, 0, 0],
            [0, 0, 2, 2, 2, 1, 1, 0, 0],
            [0, 0, 2, 1, 1, 1, 2, 0, 0]
        ]
        drop_coords = [1, 2]
        self.game.grid = vertical_win_state
        self.assertTrue(self.game.is_winner(2, drop_coords))

        diagonal_win_state = [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0, 2, 0, 0],
            [0, 0, 2, 0, 0, 2, 2, 0, 0],
            [0, 0, 2, 1, 2, 1, 1, 0, 0],
            [0, 0, 2, 2, 2, 1, 1, 0, 0],
            [0, 1, 2, 1, 1, 1, 2, 0, 0]
        ]
        drop_coords = [1, 6]
        self.game.grid = diagonal_win_state
        self.assertTrue(self.game.is_winner(2, drop_coords))

        diagonal_flip_win_state = [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 1, 1, 0, 0, 1, 0, 0],
            [0, 0, 2, 2, 1, 2, 2, 0, 0],
            [0, 2, 2, 1, 2, 1, 1, 0, 0],
            [0, 2, 2, 2, 2, 1, 1, 0, 0],
            [0, 1, 2, 1, 1, 1, 2, 1, 0]
        ]
        drop_coords = [5, 7]
        self.game.grid = diagonal_flip_win_state
        self.assertTrue(self.game.is_winner(1, drop_coords))


    def test_add_player(self):
        self.game.add_player("a")
        self.assertFalse(self.game.players_ready)
        self.assertEqual(self.game.players["a"], 1)
        self.game.add_player("b")
        self.assertTrue(self.game.players_ready)
        self.assertEqual(self.game.players["b"], 2)

    def test_add_player_already_joined(self):
        self.game.players = {"a": 1}
        with self.assertRaises(connectpy_game.AlreadyJoinedException):
            self.game.add_player("a")

    def test_add_player_full_game(self):
        self.game.players = {"a": 1, "b": 2}
        with self.assertRaises(connectpy_game.FullGameException):
            self.game.add_player("a")

    def test_is_turn(self):
        self.game.current_turn = "a"
        self.assertFalse(self.game.is_turn("b"))
        self.assertTrue(self.game.is_turn("a"))

    def test_next_player(self):
        self.game.players = {"a": 1, "b": 2}
        self.game.start_game()

        self.assertEqual(self.game.next_player(), "b")
        self.assertEqual(self.game.next_player(), "a")

    def test_get_player_indicator_not_joined(self):
        self.game.players = {"a": 1, "b": 2}
        with self.assertRaises(connectpy_game.PlayerInvalidException):
            self.game.get_player_indicator("c")

    def test_get_player_indicator(self):
        self.game.players = {"a": 1, "b": 2}
        self.assertEqual(
            self.game.get_player_indicator("a"),
            self.game.players["a"]
        )

    def test_close(self):
        self.game.players = {"a": 1, "b": 2}
        self.game.start_game()
        self.game.close("a")

        self.assertEqual(self.game.closed, "a")

