"""Network play (co-op, #438): player 2 on another computer. Not NES.

The host runs the game as always (``--host``, src/game.py); player 2 runs a thin client (``--join HOST``) that runs no
game of its own: it shows the pictures the host sends and sends back player 2's NES buttons. Nothing has to be kept
in step between the two, so nothing can drift apart: there is one game, the host's (and the NES's random number stays
in use: the RANDOMNESS option isn't locked).

The host (NetHost):
- listens on PORT (52528 by default) and takes one client at a time; a client that leaves can join again;
- sends the screen: ``display.flip`` and ``display.update`` are wrapped (as src/frame_recorder.py does: the game
  always presents through them), and after each the picture is taken at the NES's own size (the screen surface is
  NES_RES * SCALE: every SCALE-th pixel), at most MAX_FPS a second. A picture the throttle skipped is taken on the next
  frame any of the game's loops passes (src/waiting.py set_frame_listener), so a screen that then waits for a button
  is sent too. Only a picture that changed is sent, compressed (zlib), from a thread of its own; if the client is
  slower than the game, the pictures it hasn't had yet are skipped for the newest;
- reads player 2's buttons: each press or release of an NES button (A, B, START, SELECT and the D-pad) presses or lets
  go of player 2's key for it (src/controls.py PLAYER_TWO_ACTIONS: by default the numpad's), as a second controller
  does (src/gamepad.py), through the same hook (RemoteJoypad). So the client is player 2 wherever player 2's joypad is
  read: the second hero's turns in a fight (src/battle_controller.py). Its keys are let go when it leaves.

The client (run_client) opens a window, shows each picture, scaled by whole multiples, and sends a press or a release
whenever one of player 2's NES buttons goes down or up: the keys and the controller are the client player's own
controls (their player 1 keys, from their own settings file). It has no sound: the music and the sounds play on the
host.

The messages, both ways: a 4-byte big-endian length, then a type byte and the payload. HELLO (``H``, JSON
``{"game": GAME, "version": VERSION}``) from each side first: a peer that isn't this game at this protocol version is
closed. FRAME (``F``, host to client): width and height, two big-endian 16-bit numbers, then the RGB picture,
zlib-compressed. BUTTON (``B``, client to host): JSON ``{"button": "A", "down": true}``. A message over MAX_MESSAGE
bytes, a picture that decompresses to anything but its width * height * 3 bytes, or a button that isn't an NES button
closes the connection or is ignored.

The host trusts whoever connects with player 2's buttons and nothing else; it listens on every network interface, so
play on a local network, or over a VPN (Tailscale, WireGuard), rather than opening the port to the internet.
"""
import json
import queue
import socket
import struct
import threading
import zlib
from collections.abc import Callable
from time import perf_counter
from typing import Any

import pygame
from pygame import KEYDOWN, KEYUP, display

from src import controls
from src.waiting import set_frame_listener

GAME = 'dragon-warrior'
VERSION = 1
PORT = 52528
MAX_FPS = 60
MAX_MESSAGE = 8 * 1024 * 1024
NES_WIDTH, NES_HEIGHT = 256, 240
CLIENT_ZOOM = 3

HELLO, FRAME, BUTTON = b'H', b'F', b'B'
NES_BUTTONS = tuple(controls.PLAYER_TWO_ACTIONS)  # A, B, START, SELECT, UP, DOWN, LEFT, RIGHT
NET = 'net'  # set on the key events the remote player's buttons post


class ProtocolError(Exception):
    """A peer that broke the protocol: the connection is closed."""


# Messages

def send_message(sock: socket.socket, kind: bytes, payload: bytes = b'') -> None:
    sock.sendall(struct.pack('>I', len(payload) + 1) + kind + payload)


def receive_exactly(sock: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("the connection was closed")
        data += chunk
    return bytes(data)


def receive_message(sock: socket.socket) -> tuple[bytes, bytes]:
    """The next message's type and payload."""
    (size,) = struct.unpack('>I', receive_exactly(sock, 4))
    if not 1 <= size <= MAX_MESSAGE:
        raise ProtocolError(f"a message of {size} bytes")
    message = receive_exactly(sock, size)
    return message[:1], message[1:]


def hello() -> bytes:
    return json.dumps({'game': GAME, 'version': VERSION}).encode()


def check_hello(sock: socket.socket) -> None:
    """The peer's HELLO: this game, this protocol version, or ProtocolError."""
    kind, payload = receive_message(sock)
    try:
        greeting = json.loads(payload)
    except ValueError as error:
        raise ProtocolError("not a hello") from error
    if kind != HELLO or not isinstance(greeting, dict) or greeting.get('game') != GAME:
        raise ProtocolError("not this game")
    if greeting.get('version') != VERSION:
        raise ProtocolError(f"protocol version {greeting.get('version')}, not {VERSION}")


def encode_frame(width: int, height: int, rgb: bytes) -> bytes:
    return struct.pack('>HH', width, height) + zlib.compress(rgb, 1)


def decode_frame(payload: bytes) -> tuple[int, int, bytes]:
    """A FRAME's width, height and RGB bytes, or ProtocolError."""
    if len(payload) < 4:
        raise ProtocolError("a frame without a size")
    width, height = struct.unpack('>HH', payload[:4])
    expected = width * height * 3
    decompressor = zlib.decompressobj()
    try:
        rgb = decompressor.decompress(payload[4:], expected + 1)
    except zlib.error as error:
        raise ProtocolError("a frame that doesn't decompress") from error
    if len(rgb) != expected or decompressor.unconsumed_tail:
        raise ProtocolError("a frame of the wrong size")
    return width, height, rgb


def encode_button(button: str, down: bool) -> bytes:
    return json.dumps({'button': button, 'down': down}).encode()


def decode_button(payload: bytes) -> tuple[str, bool] | None:
    """A BUTTON's NES button and whether it went down, or None for anything else."""
    try:
        data = json.loads(payload)
    except ValueError:
        return None
    if not isinstance(data, dict) or data.get('button') not in NES_BUTTONS or not isinstance(data.get('down'), bool):
        return None
    return data['button'], data['down']


# The host

def nes_picture(surface: pygame.Surface, scale: int) -> tuple[int, int, bytes]:
    """The screen at the NES's own size (every ``scale``-th pixel) as RGB bytes."""
    width, height = surface.get_width() // scale, surface.get_height() // scale
    small = pygame.transform.scale(surface, (width, height)) if scale != 1 else surface
    return width, height, pygame.image.tobytes(small, 'RGB')


class RemoteJoypad:
    """Player 2's buttons from the client, pressed as player 2's keys (see the module docstring): what src/waiting.py
    reads of a gamepad (``poll`` and ``held``), added to the controllers (src/gamepad.py Gamepads)."""

    def __init__(self) -> None:
        self.received: queue.Queue[tuple[str, bool] | None] = queue.Queue()
        self.held: set[int] = set()

    def poll(self) -> None:
        """Post the presses and releases received since the last poll (None: the client left, let go of every key)."""
        while True:
            try:
                received = self.received.get_nowait()
            except queue.Empty:
                return
            if received is None:
                for key in sorted(self.held):
                    post_key(KEYUP, key)
                self.held.clear()
                continue
            button, down = received
            binding = controls.first_binding(controls.PLAYER_TWO_ACTIONS[button])
            if binding is None:
                continue
            if down and binding.key not in self.held:
                self.held.add(binding.key)
                post_key(KEYDOWN, binding.key)
            elif not down and binding.key in self.held:
                self.held.discard(binding.key)
                post_key(KEYUP, binding.key)

    def disconnect(self) -> None:
        self.held.clear()


def post_key(event_type: int, key: int) -> None:
    if pygame.display.get_init():
        pygame.event.post(pygame.event.Event(event_type, {'key': key, 'mod': 0, 'scancode': 0, 'unicode': '',
                                                          NET: True}))


class NetHost:
    """The host's side (see the module docstring)."""

    def __init__(self, scale: int, port: int = PORT, address: str = '', max_fps: int = MAX_FPS,
                 log: Callable[[str], None] | None = None) -> None:
        self.scale = scale
        self.port = port
        self.address = address
        self.min_interval = 1 / max_fps
        self.log = log or (lambda message: print(message, flush=True))
        self.joypad = RemoteJoypad()
        self.client: socket.socket | None = None
        self.server: socket.socket | None = None
        self.running = False
        self._frame_ready = threading.Condition()
        self._frame: tuple[int, int, bytes] | None = None
        self._last_capture = 0.0
        self._pending = False
        self._sent_crc: int | None = None
        self._real_flip: Any = None
        self._real_update: Any = None

    # Starting and stopping

    def start(self) -> None:
        """Listen, wrap the display's presents and start the threads."""
        self.server = socket.create_server((self.address, self.port), reuse_port=False)
        self.port = self.server.getsockname()[1]
        self.running = True
        self.install()
        set_frame_listener(self.frame_passed, 'netplay')
        threading.Thread(target=self.accept_loop, name='netplay-accept', daemon=True).start()
        threading.Thread(target=self.send_loop, name='netplay-send', daemon=True).start()
        self.log(f"Hosting on port {self.port}: player 2 joins with --join <this computer's address>")

    def stop(self) -> None:
        self.running = False
        set_frame_listener(None, 'netplay')
        self.uninstall()
        for sock in (self.client, self.server):
            if sock is not None:
                try:
                    sock.close()
                except OSError as exc:
                    self.log(f'Failed to close socket during stop: {exc}')
        with self._frame_ready:
            self._frame_ready.notify_all()

    def install(self) -> None:
        self._real_flip, self._real_update = display.flip, display.update
        display.flip, display.update = self._flip, self._update

    def uninstall(self) -> None:
        if display.flip is self._flip and display.update is self._update:
            display.flip, display.update = self._real_flip, self._real_update

    # The pictures (the game's thread)

    def _flip(self) -> None:
        self._real_flip()
        self.presented()

    def _update(self, *args: Any, **kwargs: Any) -> None:
        self._real_update(*args, **kwargs)
        self.presented()

    def presented(self, now: float | None = None) -> None:
        """A picture was presented: take it, unless the last one was taken less than 1/MAX_FPS ago (then on the next
        frame: frame_passed)."""
        if self.client is None:
            return
        now = perf_counter() if now is None else now
        if now - self._last_capture < self.min_interval:
            self._pending = True
            return
        self.capture(now)

    def frame_passed(self) -> None:
        if self._pending and self.client is not None and perf_counter() - self._last_capture >= self.min_interval:
            self.capture(perf_counter())

    def capture(self, now: float) -> None:
        surface = display.get_surface()
        self._pending = False
        self._last_capture = now
        if surface is None:
            return
        frame = nes_picture(surface, self.scale)
        with self._frame_ready:
            self._frame = frame
            self._frame_ready.notify()

    # The threads

    def accept_loop(self) -> None:
        assert self.server is not None
        while self.running:
            try:
                client, address = self.server.accept()
            except OSError:
                return
            if self.client is not None:
                client.close()  # one player 2 at a time
                continue
            try:
                client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                send_message(client, HELLO, hello())
                check_hello(client)
            except (OSError, ConnectionError, ProtocolError) as error:
                self.log(f"Player 2 couldn't join from {address[0]}: {error}")
                client.close()
                continue
            self.log(f"Player 2 joined from {address[0]}")
            self._sent_crc = None
            self.client = client
            self._pending = True  # the picture now on the screen, at the next frame
            threading.Thread(target=self.receive_loop, args=(client,), name='netplay-receive', daemon=True).start()

    def receive_loop(self, client: socket.socket) -> None:
        try:
            while self.running:
                kind, payload = receive_message(client)
                if kind == BUTTON and (button := decode_button(payload)) is not None:
                    self.joypad.received.put(button)
        except (OSError, ConnectionError, ProtocolError):
            pass
        self.drop(client)

    def send_loop(self) -> None:
        while self.running:
            with self._frame_ready:
                while self.running and self._frame is None:
                    self._frame_ready.wait()
                frame, self._frame = self._frame, None
            client = self.client
            if frame is None or client is None:
                continue
            width, height, rgb = frame
            crc = zlib.crc32(rgb, width * 65536 + height)
            if crc == self._sent_crc:
                continue
            try:
                send_message(client, FRAME, encode_frame(width, height, rgb))
                self._sent_crc = crc
            except OSError:
                self.drop(client)

    def drop(self, client: socket.socket) -> None:
        """Player 2 left: let go of their keys."""
        if self.client is client:
            self.client = None
            self.joypad.received.put(None)
            self.log("Player 2 left")
        try:
            client.close()
        except OSError:
            pass


def start_host(game: Any, port: int = PORT) -> NetHost:
    """Host from now on (--host): the game's screen to player 2, player 2's buttons to the game."""
    from src.gamepad import connected_gamepads
    host = NetHost(scale=game.game_state.config['SCALE'], port=port)
    gamepads = connected_gamepads()
    if gamepads is not None:
        gamepads.add(host.joypad)
    host.start()
    return host


# The client

def parse_address(address: str) -> tuple[str, int]:
    """HOST or HOST:PORT (an IPv6 address in brackets: [::1]:52528)."""
    if address.startswith('['):
        host, _, rest = address[1:].partition(']')
        return host, int(rest[1:]) if rest.startswith(':') else PORT
    if address.count(':') == 1:
        host, port = address.split(':')
        return host, int(port)
    return address, PORT


def button_changes(event: pygame.event.Event, button_keys: dict[str, Any]) -> list[tuple[str, bool]]:
    """The NES buttons a key event presses or lets go of, by the client player's keys (``button_keys``: each NES
    button's key set)."""
    if event.type not in (KEYDOWN, KEYUP):
        return []
    return [(button, event.type == KEYDOWN) for button, keys in button_keys.items() if event.key in keys]


def client_button_keys() -> dict[str, Any]:
    from src.common import (A_BUTTON_KEYS, B_BUTTON_KEYS, DOWN_KEYS, LEFT_KEYS, RIGHT_KEYS, SELECT_BUTTON_KEYS,
                            START_BUTTON_KEYS, UP_KEYS)
    return {'A': A_BUTTON_KEYS, 'B': B_BUTTON_KEYS, 'START': START_BUTTON_KEYS, 'SELECT': SELECT_BUTTON_KEYS,
            'UP': UP_KEYS, 'DOWN': DOWN_KEYS, 'LEFT': LEFT_KEYS, 'RIGHT': RIGHT_KEYS}


def run_client(address: str, settings_controls: Any = None) -> int:
    """--join: player 2's window (see the module docstring). Returns the exit status."""
    from src.gamepad import connect_gamepad
    from src.waiting import poll_virtual_joypad
    host, port = parse_address(address)
    pygame.init()
    if settings_controls is not None:
        controls.set_controls(controls.Controls.from_json(settings_controls))
    try:
        sock = socket.create_connection((host, port), timeout=10)
        sock.settimeout(None)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        send_message(sock, HELLO, hello())
        check_hello(sock)
    except (OSError, ConnectionError, ProtocolError) as error:
        print(f"Couldn't join {host}:{port}: {error}")
        return 1
    screen = display.set_mode((NES_WIDTH * CLIENT_ZOOM, NES_HEIGHT * CLIENT_ZOOM), pygame.RESIZABLE)
    display.set_caption(f"Dragon Warrior - player 2 ({host})")
    frames: queue.Queue[tuple[int, int, bytes] | None] = queue.Queue(maxsize=2)

    def receive() -> None:
        try:
            while True:
                kind, payload = receive_message(sock)
                if kind == FRAME:
                    frame = decode_frame(payload)
                    if frames.full():
                        try:
                            frames.get_nowait()  # the newest picture only
                        except queue.Empty:
                            pass
                    frames.put(frame)
        except (OSError, ConnectionError, ProtocolError) as error:
            print(f"Disconnected: {error}")
        frames.put(None)

    threading.Thread(target=receive, name='netplay-client', daemon=True).start()
    connect_gamepad()
    button_keys = client_button_keys()
    clock = pygame.time.Clock()
    while True:
        poll_virtual_joypad()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sock.close()
                return 0
            for button, down in button_changes(event, button_keys):
                try:
                    send_message(sock, BUTTON, encode_button(button, down))
                except OSError:
                    return 1
        try:
            frame = frames.get(timeout=1 / 120)
        except queue.Empty:
            clock.tick(240)
            continue
        if frame is None:
            return 1
        show_frame(display.get_surface() or screen, *frame)
        clock.tick(240)


def show_frame(screen: pygame.Surface, width: int, height: int, rgb: bytes) -> None:
    """The picture, scaled by the biggest whole multiple that fits the window, centred on black."""
    picture = pygame.image.frombytes(rgb, (width, height), 'RGB')
    zoom = max(1, min(screen.get_width() // width, screen.get_height() // height))
    scaled = pygame.transform.scale(picture, (width * zoom, height * zoom))
    screen.fill((0, 0, 0))
    screen.blit(scaled, ((screen.get_width() - scaled.get_width()) // 2,
                         (screen.get_height() - scaled.get_height()) // 2))
    display.flip()
