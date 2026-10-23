"""
What is on screen while a saved game (or a playtest checkpoint) loads, frame by frame.

NES ContinueReset (Bank03) clears CharDirection to 0 (up). After the save is chosen, MainGameEngine calls
StartAtThroneRoom (LCB47), which loads BlackPalPtr at once (the screen goes black, with no fade out), sets the start
position and changes maps with MapChngNoSound (Bank00, LB091). That skips ScreenFadeOut, draws the whole map while the
palette is black and ends with one PalFadeIn. So the first frame with anything on it is the throne room with the hero
facing up, toward King Lorik, and there is exactly one fade, a fade in.
"""
import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame

from src.checkpoints import read_checkpoint
from src.config.test_config import test_config
from src.direction import Direction
from src.game import Game
from src.visual_effects import screen_fade


class StopMainLoop(Exception):
    pass


def new_game() -> Game:
    with patch('src.game.SCALED'):
        return Game(test_config)


class TestLoadSaveFrames(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = False  # draw for real, so black frames can be told apart from the map
        self.addCleanup(test_config.__setitem__, 'NO_BLIT', True)
        self.addCleanup(test_config.__setitem__, 'SAVE_DIR', test_config['SAVE_DIR'])
        self.frames: list[tuple[str, str, tuple[str, str] | None]] = []  # map, facing, which hero image is shown
        self.fades: list[bool] = []

    def record_frames(self, game: Game):
        """At every display.flip and display.update that shows anything but black, record the map, the hero's facing
        and which sprite sheet and direction the hero's image comes from. Also record every fade (True for a fade
        out)."""
        real_flip, real_update = pygame.display.flip, pygame.display.update
        sheets = {'UNARMED': game.directories.UNARMED_HERO_PATH, 'ARMED': game.directories.ARMED_HERO_PATH,
                  'UNARMED_WITH_SHIELD': game.directories.UNARMED_HERO_WITH_SHIELD_PATH,
                  'ARMED_WITH_SHIELD': game.directories.ARMED_HERO_WITH_SHIELD_PATH}
        # AnimatedSprite.set_images: the sheet's rows are down, left, up, right
        rows = (Direction.DOWN, Direction.LEFT, Direction.UP, Direction.RIGHT)
        image_names = {pygame.image.tobytes(image, 'RGBA'): (sheet_name, rows[row].name)
                       for sheet_name, path in sheets.items()
                       for row, images in enumerate(game.current_map.scale_sprite_sheet(path)[:4])
                       for image in images}

        def record():
            if pygame.transform.average_color(game.screen)[:3] == (0, 0, 0):
                return
            self.frames.append((game.current_map.identifier, Direction(game.player.direction_value).name,
                                image_names.get(pygame.image.tobytes(game.player.image, 'RGBA'))))

        def flip(*args, **kwargs):
            record()
            return real_flip(*args, **kwargs)

        def update(*args, **kwargs):
            record()
            return real_update(*args, **kwargs)

        def counted_fade(*args, **kwargs):
            self.fades.append(kwargs['fade_out'])
            return screen_fade(*args, **kwargs)

        for target, replacement in (('pygame.display.flip', flip), ('pygame.display.update', update),
                                    ('src.map_manager.screen_fade', counted_fade)):
            patcher = patch(target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def run_main_loop(game: Game, frames: int):
        """Run Game.main for a few frames: the King waits for a button before speaking (NES FirstInputLoop)."""
        loops = []

        def get_events():
            if len(loops) == frames:
                raise StopMainLoop
            loops.append(1)
            Game.get_events(game)

        game.get_events = get_events  # type: ignore[method-assign]
        game.clock = MagicMock()  # don't wait for the frame rate
        try:
            game.main()
        except StopMainLoop:
            pass

    def assert_every_frame_shows(self, map_name: str, facing: Direction, sheet: str):
        self.assertTrue(self.frames)
        for number, frame in enumerate(self.frames):
            self.assertEqual(frame, (map_name, facing.name, (sheet, facing.name)), f"frame {number}")
        self.assertEqual(self.fades, [False], "the NES fades the map in once (PalFadeIn) and never fades out")

    def test_continue_a_quest(self):
        game = new_game()
        game.player.name = "Erdrick"
        game.player.weapon = "Club"
        game.story_flags.left_throne_room = True
        game.player.adventure_log = 1
        with tempfile.TemporaryDirectory() as save_dir:
            game.cmd_menu.directories.save_dir = save_dir
            game.cmd_menu.save()
            with open(os.path.join(save_dir, 'save_slot_1.json')) as save_file:
                self.assertEqual(json.load(save_file)['Weapon'], "Club")

            loaded = new_game()
            loaded.directories.save_dir = save_dir
            loaded.save_dir_contents = os.listdir(save_dir)
            self.record_frames(loaded)
            with patch.object(loaded.game_functions, 'main_menu_selection', return_value=0), \
                    patch.object(loaded.cmd_menu.__class__, 'show_text_in_dialog_box'):
                loaded.continue_quest()
                self.run_main_loop(loaded, frames=3)
        self.assert_every_frame_shows('TantegelThroneRoom', Direction.UP, 'ARMED')
        self.assertTrue(loaded.story_flags.left_throne_room)

    def test_checkpoint_faces_its_own_way_from_the_first_frame(self):
        name = 'swamp_cave'
        facing = Direction[read_checkpoint(name)['Facing']]
        self.assertNotEqual(facing, Direction.DOWN)
        game = new_game()
        self.record_frames(game)
        game.load_checkpoint(name)
        sheet = ('ARMED' if game.player.weapon else 'UNARMED') + ('_WITH_SHIELD' if game.player.shield else '')
        self.assert_every_frame_shows('Alefgard', facing, sheet)

    def test_begin_a_new_quest(self):
        """NES MainGameEngine runs StartAtThroneRoom for a new quest too: after the name and the message speed window
        the menu cuts to black (no fade out) and the throne room fades in once."""
        game = new_game()
        facing = Direction(game.player.direction_value)
        self.record_frames(game)
        with patch.object(game, 'select_adventure_log'), patch('src.game.NameSelection') as name_selection, \
                patch.object(game, 'choose_new_quest_options'), \
                patch.object(game.cmd_menu.__class__, 'show_text_in_dialog_box'):
            name_selection.return_value.select_name.return_value = "Erdrick"
            game.begin_new_quest()
            self.run_main_loop(game, frames=3)
        self.assert_every_frame_shows('TantegelThroneRoom', facing, 'UNARMED')
        self.assertEqual(game.player.name, "Erdrick")
