"""Cooperative tasks: several of the game's loops running side by side, a frame at a time (free roam co-op, #438). Not
NES.

The game's loops (the battle, the dialogs, the menus, the shops, the map changes) each run until they're done, waiting
for their frames in a few places (src/waiting.py: ``wait``, which ``wait_frames``, ``next_frame`` and every pause
come down to, and ``get_events``, which ``frame_events`` reads). That's how the NES works, and how one hero plays. For
two heroes roaming apart, each hero's play has to go on while the other's is in a loop of its own: hero 1 in a fight,
hero 2 still walking.

So each hero's play can run as a Task: a greenlet (a coroutine with its own stack) that runs the game's code exactly
as it is. The Scheduler runs one frame of each task in turn (run_frame). Inside a task, waiting for game time doesn't
sleep: it hands the frame back to the scheduler (next_task_frame) until the game clock has passed the wait's end, so
the other tasks go on meanwhile; and the events a task reads are its own (Task.events, which whoever runs the
scheduler fills each frame, by player). Outside any task nothing changes: the game runs as it always has, so one
hero's game is the same as before.

A task's context variables are its own (each task starts from a copy of the context it was made in): the player whose
joypad the key sets read (src/controls.py player_input) is one, so each hero's task reads their own player's keys.

An exception in a task goes up through run_frame to whoever runs the scheduler, and the task is over.
"""
from collections.abc import Callable
from contextvars import copy_context
from typing import Any

from greenlet import getcurrent, greenlet
from pygame.event import Event


class Task:
    """One loop running a frame at a time (see the module docstring): ``run`` called in a greenlet of its own."""

    def __init__(self, name: str, run: Callable[[], Any]) -> None:
        self.name = name
        self.run = run
        self.events: list[Event] = []  # what the task reads this frame (src/waiting.py get_events)
        self.done = False
        self.frames = 0  # how many frames it has run
        self.result: Any = None
        self._greenlet: greenlet | None = None

    def start(self, parent: greenlet) -> None:
        self._greenlet = greenlet(self._main, parent=parent)
        self._greenlet.gr_context = copy_context()

    def _main(self) -> None:
        _tasks[getcurrent()] = self
        try:
            self.result = self.run()
        finally:
            self.done = True
            _tasks.pop(getcurrent(), None)

    def take_events(self) -> list[Event]:
        events, self.events = self.events, []
        return events

    def close(self) -> None:
        """End the task now if it isn't done: GreenletExit is raised where it waits, so its ``finally`` blocks and
        ``with`` blocks run at once, not whenever its greenlet is garbage collected."""
        if self._greenlet is not None and not self._greenlet.dead:
            self._greenlet.throw()
        self.done = True

    def resume(self) -> None:
        """Run the task until it waits for its next frame, or ends."""
        assert self._greenlet is not None
        self.frames += 1
        self._greenlet.switch()


class Scheduler:
    """The tasks, run a frame each in turn (see the module docstring)."""

    def __init__(self) -> None:
        self.tasks: list[Task] = []

    def add(self, task: Task) -> Task:
        task.start(parent=getcurrent())
        self.tasks.append(task)
        return task

    def run_frame(self) -> None:
        """One frame of every task that isn't done, in the order they were added; the done ones are let go."""
        for task in list(self.tasks):
            if not task.done:
                task.resume()
        self.tasks = [task for task in self.tasks if not task.done]

    def close(self) -> None:
        """End every task that isn't done (Task.close) and let them go."""
        for task in self.tasks:
            task.close()
        self.tasks = []

    def run_until_done(self, frames: int, between_frames: Callable[[], Any] | None = None) -> None:
        """Run frames until every task is done (at most ``frames``), ``between_frames`` after each (a test moving its
        clock on, say)."""
        for _ in range(frames):
            if not self.tasks:
                return
            self.run_frame()
            if between_frames is not None:
                between_frames()


_tasks: dict[greenlet, Task] = {}


def current_task() -> Task | None:
    """The task the code is running in, or None outside any task (the game as one hero plays it)."""
    return _tasks.get(getcurrent())


def next_task_frame() -> bool:
    """Inside a task: hand the frame back to the scheduler, and come back on the task's next frame. Returns False,
    doing nothing, outside any task."""
    task = current_task()
    if task is None:
        return False
    current = getcurrent()
    assert current.parent is not None
    current.parent.switch()
    return True
