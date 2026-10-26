"""A block redrawn at once on a dark map (CommandMenu.redraw_character_block: Gwaelin taken off her block, an NPC
turned toward the hero by TALK) stays dark outside the hero's light, as NES ModMapBlock (Bank00) puts a blank block
there (ChkLightDiameterX2/ChkLightDiameterY2)."""
import os
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame  # noqa: E402

from src.config.test_config import test_config  # noqa: E402
from src.constants import GWAELIN_SWAMP_CAVE_COORDINATES  # noqa: E402
from src.direction import Direction  # noqa: E402
from src.drawer import MapDrawingGame  # noqa: E402
from src.game import Game  # noqa: E402
from src.game_state import TORCH_LIGHT_DIAMETER  # noqa: E402
from src.maps import map_lookup  # noqa: E402

BLACK_PIXEL = b'\x00\x00\x00'


class TestDarkMapBlocks(TestCase):

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
        # Right above Gwaelin, facing her, in the dark Swamp Cave
        gwaelin_row, gwaelin_column = GWAELIN_SWAMP_CAVE_COORDINATES
        self.game.change_map(map_lookup['SwampCave'](self.game.config),
                             destination_coordinates=(gwaelin_row - 1, gwaelin_column),
                             direction=Direction.DOWN.value)
        self.gwaelin = self.game.current_map.characters['PRINCESS_GWAELIN']['character']

    def draw_frame(self) -> None:
        game = self.game
        view = SimpleNamespace(**{name: getattr(game, name) for name in MapDrawingGame.__annotations__})
        view.initial_dialog_enabled, view.events, view.story_flags = False, [], SimpleNamespace(left_throne_room=True)
        game.drawer.draw_all(view, False)

    def gwaelins_block_is_dark(self) -> bool:
        rect = self.gwaelin.rect.move(self.game.camera.pos)
        pixels = pygame.image.tobytes(self.game.screen.subsurface(rect), 'RGB')
        return pixels == BLACK_PIXEL * rect.width * rect.height

    def test_an_erased_block_outside_the_light_stays_dark(self):
        self.assertEqual(1, self.game.game_state.lit_diameter)  # no torch: only the hero's own block is lit
        self.draw_frame()
        self.assertTrue(self.gwaelins_block_is_dark())
        self.game.cmd_menu.erase_character_now(self.gwaelin)
        self.assertTrue(self.gwaelins_block_is_dark())

    def test_an_erased_block_inside_the_light_shows_the_floor(self):
        game_state = self.game.game_state
        game_state.light_diameter = game_state.lit_diameter = TORCH_LIGHT_DIAMETER
        self.draw_frame()
        self.game.cmd_menu.erase_character_now(self.gwaelin)
        self.assertFalse(self.gwaelins_block_is_dark())
