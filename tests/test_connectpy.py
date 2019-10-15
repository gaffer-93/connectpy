#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

import connectpy


class TestConnectpy(unittest.TestCase):

    def setUp(self):
        # Use import to make flake8 happy with initial tests.
        dir(connectpy)

    def test_something(self):
        pass

    def tearDown(self):
        pass
