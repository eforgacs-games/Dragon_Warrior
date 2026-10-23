"""TALK turns the NPC toward the hero before the dialog starts (NES PrepTalk -> NPCFacePlayer, LC04A), not after it."""
import os
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame  # noqa: E402

from src.config.test_config import test_config  # noqa: E402
from src.direction import Direction  # noqa: E402
from src.drawer import MapDrawingGame  # noqa: E402
from src.game import Game  # noqa: E402
from src.maps import map_lookup  # noqa: E402
from src.npc_movement import step  # noqa: E402


class TestTalkFacing(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        config = dict(test_config, NO_BLIT=False, NO_WAIT=True, RENDER_TEXT=False)
        with patch('src.game.SCALED', 0):
            self.game = Game(config)
        # Above the guard left of the throne room door, who faces right, toward the other guard
        self.game.change_map(map_lookup['TantegelThroneRoom'](self.game.config), destination_coordinates=(11, 13),
                             direction=Direction.DOWN.value)
        self.game.player.next_coordinates = step(11, 13, Direction.DOWN.value)  # as the end of a step sets it
        self.guard = self.game.current_map.characters['GUARD_2']['character']
        self.assertEqual(((12, 13), Direction.RIGHT.value), ((self.guard.row, self.guard.column),
                                                             self.guard.direction_value))
        self.draw_frame()

    def draw_frame(self) -> None:
        game = self.game
        view = SimpleNamespace(**{name: getattr(game, name) for name in MapDrawingGame.__annotations__})
        view.initial_dialog_enabled, view.events, view.story_flags = False, [], SimpleNamespace(left_throne_room=True)
        game.drawer.draw_all(view, False)

    def guard_on_screen(self) -> bytes:
        rect = self.guard.rect.move(self.game.camera.pos)
        return pygame.image.tobytes(self.game.screen.subsurface(rect), 'RGB')

    def test_the_npc_faces_the_hero_before_the_first_letter(self):
        facing_away = self.guard_on_screen()
        when_the_dialog_starts = []
        with patch.object(self.game.cmd_menu, 'launch_dialog',
                          side_effect=lambda *_args: when_the_dialog_starts.append(self.guard_on_screen())):
            self.game.cmd_menu.talk()
        self.assertEqual(Direction.UP.value, self.guard.direction_value)
        self.draw_frame()  # the guard as the map draws him from now on
        self.assertNotEqual(facing_away, self.guard_on_screen())
        self.assertEqual([self.guard_on_screen()], when_the_dialog_starts)
