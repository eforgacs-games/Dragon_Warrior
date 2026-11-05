"""Network play (src/netplay.py): the messages, player 2's buttons on the host, the pictures, and a host and a client
talking over this computer's loopback."""
import json
import os
import socket
import struct
import time
import zlib
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_KP0, K_KP8, KEYDOWN, KEYUP, K_k, K_UP

from src import netplay
from src.controls import reset_controls
from src.gamepad import Gamepads
from src.netplay import (BUTTON, FRAME, HELLO, MAX_MESSAGE, NES_HEIGHT, NES_WIDTH, PORT, NetHost, ProtocolError,
                         RemoteJoypad, button_changes, check_hello, client_button_keys, decode_button, decode_frame,
                         encode_button, encode_frame, hello, nes_picture, parse_address, receive_message,
                         send_message)

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')


def key_events(event_type):
    return [event for event in pygame.event.get(event_type)]


class TestMessages(TestCase):

    def setUp(self):
        self.one, self.two = socket.socketpair()
        self.addCleanup(self.one.close)
        self.addCleanup(self.two.close)

    def test_round_trip(self):
        send_message(self.one, BUTTON, b'payload')
        self.assertEqual((BUTTON, b'payload'), receive_message(self.two))

    def test_hello(self):
        send_message(self.one, HELLO, hello())
        check_hello(self.two)

    def test_another_game_or_version(self):
        for greeting in ({'game': 'other', 'version': 1}, {'game': 'dragon-warrior', 'version': 99}, 'nonsense'):
            with self.subTest(greeting=greeting):
                send_message(self.one, HELLO, json.dumps(greeting).encode())
                self.assertRaises(ProtocolError, check_hello, self.two)

    def test_a_message_too_big(self):
        self.one.sendall(struct.pack('>I', MAX_MESSAGE + 1))
        self.assertRaises(ProtocolError, receive_message, self.two)

    def test_closed(self):
        self.one.close()
        self.assertRaises(ConnectionError, receive_message, self.two)


class TestFrames(TestCase):

    def test_round_trip(self):
        rgb = bytes(range(256)) * 9
        self.assertEqual((32, 24, rgb[:32 * 24 * 3]), decode_frame(encode_frame(32, 24, rgb[:32 * 24 * 3])))

    def test_the_wrong_size(self):
        self.assertRaises(ProtocolError, decode_frame, encode_frame(32, 24, b'\0' * 10))
        self.assertRaises(ProtocolError, decode_frame, b'\0')
        self.assertRaises(ProtocolError, decode_frame, struct.pack('>HH', 2, 2) + b'not zlib')

    def test_no_zip_bomb(self):
        bomb = struct.pack('>HH', 1, 1) + zlib.compress(b'\0' * 50_000_000)
        self.assertRaises(ProtocolError, decode_frame, bomb)

    def test_at_the_nes_size(self):
        pygame.init()
        surface = pygame.Surface((NES_WIDTH * 2, NES_HEIGHT * 2))
        surface.fill((1, 2, 3))
        surface.fill((200, 100, 50), (0, 0, 2, 2))
        width, height, rgb = nes_picture(surface, 2)
        self.assertEqual((NES_WIDTH, NES_HEIGHT), (width, height))
        self.assertEqual(bytes((200, 100, 50, 1, 2, 3)), rgb[:6])


class TestButtons(TestCase):

    def test_round_trip(self):
        self.assertEqual(('START', False), decode_button(encode_button('START', False)))

    def test_only_nes_buttons(self):
        for payload in (b'{"button": "OPTIONS", "down": true}', b'{"button": "A", "down": 1}', b'[]', b'?'):
            with self.subTest(payload=payload):
                self.assertIsNone(decode_button(payload))

    def test_the_client_players_own_keys(self):
        reset_controls()
        keys = client_button_keys()
        press = pygame.event.Event(KEYDOWN, key=K_k)
        self.assertEqual([('A', True)], button_changes(press, keys))
        self.assertEqual([('UP', False)], button_changes(pygame.event.Event(KEYUP, key=K_UP), keys))
        self.assertEqual([], button_changes(pygame.event.Event(pygame.QUIT), keys))


class TestAddresses(TestCase):

    def test_forms(self):
        self.assertEqual(('192.168.0.5', PORT), parse_address('192.168.0.5'))
        self.assertEqual(('host.local', 6000), parse_address('host.local:6000'))
        self.assertEqual(('::1', 6000), parse_address('[::1]:6000'))
        self.assertEqual(('::1', PORT), parse_address('[::1]'))


class TestRemoteJoypad(TestCase):

    def setUp(self):
        pygame.init()
        pygame.display.set_mode((16, 16))
        reset_controls()
        pygame.event.clear()

    def test_player_2s_keys(self):
        joypad = RemoteJoypad()
        joypad.received.put(('A', True))
        joypad.received.put(('UP', True))
        joypad.poll()
        self.assertEqual({K_KP0, K_KP8}, joypad.held)
        self.assertEqual([K_KP0, K_KP8], [event.key for event in key_events(KEYDOWN)])
        joypad.received.put(('A', False))
        joypad.poll()
        self.assertEqual({K_KP8}, joypad.held)
        self.assertEqual([K_KP0], [event.key for event in key_events(KEYUP)])

    def test_let_go_when_the_client_leaves(self):
        joypad = RemoteJoypad()
        joypad.received.put(('B', True))
        joypad.poll()
        joypad.received.put(None)
        joypad.poll()
        self.assertEqual(set(), joypad.held)
        self.assertEqual(1, len(key_events(KEYUP)))

    def test_read_with_the_controllers(self):
        gamepads = Gamepads()
        joypad = RemoteJoypad()
        gamepads.add(joypad)
        joypad.received.put(('START', True))
        gamepads.poll()
        self.assertEqual(joypad.held, gamepads.held)


class TestThrottle(TestCase):

    def test_at_most_max_fps_and_the_rest_on_the_next_frame(self):
        host = NetHost(scale=2, max_fps=60)
        host.client = object()
        with patch.object(host, 'capture') as capture:
            host.presented(now=10.0)
            capture.assert_called_once()
            host._last_capture = 10.0
            host.presented(now=10.001)
            capture.assert_called_once()
            self.assertTrue(host._pending)

    def test_nothing_without_a_client(self):
        host = NetHost(scale=2)
        with patch.object(host, 'capture') as capture:
            host.presented(now=10.0)
        capture.assert_not_called()


class TestOverLoopback(TestCase):
    """A real host and a client socket on 127.0.0.1."""

    def setUp(self):
        pygame.init()
        self.screen = pygame.display.set_mode((NES_WIDTH * 2, NES_HEIGHT * 2))
        self.host = NetHost(scale=2, port=0, address='127.0.0.1', log=lambda message: None)
        self.host.start()
        self.addCleanup(self.host.stop)
        self.client = socket.create_connection(('127.0.0.1', self.host.port), timeout=5)
        self.addCleanup(self.client.close)
        self.assertEqual(HELLO, receive_message(self.client)[0])
        send_message(self.client, HELLO, hello())
        deadline = time.monotonic() + 5
        while self.host.client is None and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertIsNotNone(self.host.client)

    def test_the_picture_reaches_the_client(self):
        self.screen.fill((10, 20, 30))
        pygame.display.flip()  # wrapped by the host
        kind, payload = receive_message(self.client)
        self.assertEqual(FRAME, kind)
        width, height, rgb = decode_frame(payload)
        self.assertEqual((NES_WIDTH, NES_HEIGHT), (width, height))
        self.assertEqual(bytes((10, 20, 30)), rgb[:3])

    def test_the_buttons_reach_the_host(self):
        send_message(self.client, BUTTON, encode_button('A', True))
        received = self.host.joypad.received.get(timeout=5)
        self.assertEqual(('A', True), received)

    def test_leaving_lets_go(self):
        self.client.close()
        self.assertIsNone(self.host.joypad.received.get(timeout=5))
        deadline = time.monotonic() + 5
        while self.host.client is not None and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertIsNone(self.host.client)

    def test_the_display_is_put_back(self):
        self.host.stop()
        self.assertIsNot(self.host._flip, pygame.display.flip)


class TestTheCommandLine(TestCase):

    def test_join_runs_only_the_client(self):
        with patch('sys.argv', ['game', '--join', 'example:6000']), \
                patch('src.game.run_client', return_value=0) as run_client, patch('src.game.Game') as game:
            from src.game import run
            self.assertRaises(SystemExit, run)
        self.assertEqual('example:6000', run_client.call_args.args[0])
        game.assert_not_called()

    def test_host_starts_the_host(self):
        with patch('sys.argv', ['game', '--host']), patch('src.game.start_host') as start_host, \
                patch('src.game.Game') as game:
            from src.game import run
            run()
        start_host.assert_called_once_with(game.return_value, netplay.PORT)
        game.return_value.main.assert_called_once()
