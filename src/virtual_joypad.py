"""A virtual joypad: button presses made by the game itself (auto-grind, src/auto_grind.py), not the player. Not NES.

It works like tools/scripted_input.py, but in the real game loop rather than under patches: once connected
(``connect``), src/waiting.py polls it on every read of input (``poll_virtual_joypad`` before the event queue is
read, ``with_virtual_keys`` wherever ``key.get_pressed()`` is), so it acts from inside whichever loop is reading input
at the time: the map loop, a dialog's wait for a button, the battle's command window, a timed wait. Each poll it

- counts game frames (``game_ticks``, so it speeds up with the game speed keys 1 to 5);
- takes the KEYDOWN events off the queue and puts back the ones that should stay: the player's own presses go to the
  driver first (``JoypadDriver.real_key``, which may stop it and use the key up), and its own presses are dropped when
  the map loop reads, so a button meant for a dialog that has closed doesn't open the COMMAND window on the map;
- asks the driver what to press (``JoypadDriver.update``, told who is reading: MAP_CONTEXT or WINDOW_CONTEXT);
- posts the presses and releases that are due, as KEYDOWN and KEYUP events marked ``VIRTUAL``, and keeps the keys it
  holds in ``held``, which ``with_virtual_keys`` adds to the keyboard state.

Every window, wait and loop then reads these presses exactly as it reads the player's keys, so none of them needs to
know about it.
"""
from collections.abc import Iterable
from typing import Any, Protocol

import pygame
from pygame import KEYDOWN, KEYUP

from src.waiting import MAP_CONTEXT, NES_FPS, game_ticks, set_virtual_joypad, virtual_joypad

# Set on the events the virtual joypad posts
VIRTUAL = 'virtual_joypad'
# The most game time counted between two polls: the game polls at least once a frame unless it is busy (loading a
# map), and that time shouldn't make a burst of presses due at once
STALL_MS = 50


def is_virtual(current_event: pygame.event.Event) -> bool:
    """Whether the virtual joypad posted this event."""
    return bool(getattr(current_event, VIRTUAL, False))


class JoypadDriver(Protocol):
    """What decides the virtual joypad's presses."""

    def update(self, joypad: 'VirtualJoypad', context: str) -> None:
        """Hold, release or tap keys (VirtualJoypad.hold, release, tap) for whoever is reading input (context)."""

    def real_key(self, current_event: pygame.event.Event) -> bool:
        """The player pressed a key: return whether it stays queued for the game to read."""


class VirtualJoypad:
    """The joypad (see the module docstring). ``driver`` decides what it presses."""

    def __init__(self, driver: JoypadDriver) -> None:
        self.driver = driver
        self.held: set[int] = set()
        # (frame, is key down, key), in time order
        self.timeline: list[tuple[int, bool, int]] = []
        self.elapsed_ms = 0
        self.last_ticks: int | None = None
        self.now = 0  # the frame of the poll under way (frame)
        self.polling = False

    @property
    def connected(self) -> bool:
        return virtual_joypad() is self

    def connect(self) -> None:
        """Start driving the game: from now on every read of input polls this joypad."""
        self.held.clear()
        self.timeline.clear()
        self.elapsed_ms = 0
        self.last_ticks = None
        self.now = 0
        set_virtual_joypad(self)

    def disconnect(self) -> None:
        """Stop driving the game: let go of every key (posting the KEYUPs) and drop the presses it has posted that
        nothing has read yet, so the player's next read starts clean."""
        if not self.connected:
            return
        set_virtual_joypad(None)
        for held_key in sorted(self.held):
            self.post(KEYUP, held_key)
        self.held.clear()
        self.timeline.clear()
        if pygame.display.get_init():
            self.keep_keydowns(lambda current_event: not is_virtual(current_event))

    def frame(self) -> int:
        """Game frames since connect, leaving out the time the game was busy without reading input."""
        now = game_ticks()
        if self.last_ticks is not None:
            self.elapsed_ms += max(0, min(now - self.last_ticks, STALL_MS))
        self.last_ticks = now
        return self.elapsed_ms * NES_FPS // 1000

    # What the driver can do

    def hold(self, held_key: int) -> None:
        """Press a key and keep it down."""
        if held_key not in self.held:
            self.held.add(held_key)
            self.post(KEYDOWN, held_key)

    def release(self, held_key: int) -> None:
        if held_key in self.held:
            self.held.discard(held_key)
            self.post(KEYUP, held_key)
        self.timeline = [item for item in self.timeline if item[2] != held_key]

    def release_all(self, keys: Iterable[int] | None = None) -> None:
        for held_key in list(self.held if keys is None else keys):
            self.release(held_key)

    def tap(self, tapped_key: int, frames: int) -> None:
        """Press a key now and let it go ``frames`` frames later."""
        self.release(tapped_key)
        self.hold(tapped_key)
        self.timeline.append((self.now + frames, False, tapped_key))
        self.timeline.sort(key=lambda item: item[0])

    # Polling

    def poll(self, context: str) -> None:
        """See the module docstring. Polls made while one is under way (the driver showing a message, say) do
        nothing."""
        if self.polling or not self.connected:
            return
        self.polling = True
        try:
            now = self.now = self.frame()
            self.check_keydowns()
            if not self.connected:
                return
            self.driver.update(self, context)
            if not self.connected:
                return
            if context == MAP_CONTEXT:
                # a press meant for a window that has closed: the map would take it for the player's
                self.keep_keydowns(lambda current_event: not is_virtual(current_event) or
                                   current_event.key in self.held)
            while self.timeline and self.timeline[0][0] <= now:
                _frame, down, timed_key = self.timeline.pop(0)
                if down:
                    self.hold(timed_key)
                else:
                    self.held.discard(timed_key)
                    self.post(KEYUP, timed_key)
        finally:
            self.polling = False

    def check_keydowns(self) -> None:
        """Hand the player's presses to the driver, which says which of them stay queued."""
        def keep(current_event: pygame.event.Event) -> bool:
            if not self.connected:  # the driver stopped it over a key earlier in the queue
                return not is_virtual(current_event)
            return is_virtual(current_event) or self.driver.real_key(current_event)
        self.keep_keydowns(keep)

    @staticmethod
    def keep_keydowns(keep) -> None:
        """Take the queued KEYDOWN events and post back, in order, the ones ``keep`` says stay."""
        queued = pygame.event.get(KEYDOWN)
        for current_event in queued:
            if keep(current_event):
                pygame.event.post(current_event)

    @staticmethod
    def post(event_type: int, posted_key: int) -> None:
        if not pygame.display.get_init():
            return
        name = pygame.key.name(posted_key)
        attributes: dict[str, Any] = {'key': posted_key, 'mod': 0, 'scancode': 0,
                                      'unicode': name if len(name) == 1 else '', VIRTUAL: True}
        pygame.event.post(pygame.event.Event(event_type, attributes))
