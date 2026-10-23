"""The dungeon map (src/dungeon_map.py, #408): the blocks the hero has seen on each dark floor, kept with the adventure
log and in save states, and shown over the map with M. Not NES."""
import json
import os
from contextlib import nullcontext
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_DOWN, K_ESCAPE, K_j, K_m, Rect

from src.config.test_config import test_config
from src.dungeon_map import CHEST_COLOR, FLOOR_COLOR, HERO_COLOR, MAP_WINDOW, STAIRS_UP_COLOR, WALL_COLOR, \
    DungeonMap, DungeonMapOverlay, Floor, block_pixels, draw_floor
from src.save_file import read_save, save_path
from src.save_state import take_snapshot
from tests.test_save_state import HeldKeys, SaveStateTestCase, comparable, key

SWAMP_CAVE_START = (9, 4)  # brick below the Swamp Cave's north stairs, as tools/benchmark.py's dungeon scene
SWAMP_CAVE_STAIRS = (6, 4)


def down_script(frame: int) -> set[int]:
    return {K_DOWN}


class TestFloor(TestCase):

    def test_blocks_are_seen_once_marked(self):
        floor = Floor(5, 7)
        self.assertFalse(floor.seen(2, 3))
        floor.see(2, 3)
        floor.see(4, 6)
        floor.see(-1, 0)  # off the floor: ignored
        floor.see(5, 0)
        self.assertEqual([(2, 3), (4, 6)], floor.seen_cells())
        self.assertFalse(floor.seen(7, 7))

    def test_save_round_trip(self):
        floor = Floor(37, 14)
        for cell in ((0, 0), (36, 13), (9, 4), (18, 5)):
            floor.see(*cell)
        loaded = Floor.from_save(json.loads(json.dumps(floor.to_save())))
        self.assertEqual(floor.seen_cells(), loaded.seen_cells())
        self.assertEqual((37, 14), (loaded.rows, loaded.columns))


class FakeMap:
    def __init__(self, identifier='SwampCave', rows=10, columns=10, is_dark=True):
        self.identifier, self.is_dark = identifier, is_dark
        self.layout = [[3] * columns for _ in range(rows)]


class TestRecord(TestCase):

    def test_the_light_square_around_the_hero_is_seen(self):
        for diameter, cells in ((1, 1), (3, 9), (5, 25), (7, 49)):
            with self.subTest(diameter=diameter):
                dungeon_map = DungeonMap()
                dungeon_map.see(FakeMap(), 5, 5, diameter)
                seen = dungeon_map.floors['SwampCave'].seen_cells()
                self.assertEqual(cells, len(seen))
                radius = (diameter - 1) // 2
                self.assertEqual((5 - radius, 5 - radius), seen[0])

    def test_clipped_at_the_floors_edges(self):
        dungeon_map = DungeonMap()
        dungeon_map.see(FakeMap(), 0, 0, 3)
        self.assertEqual([(0, 0), (0, 1), (1, 0), (1, 1)], dungeon_map.floors['SwampCave'].seen_cells())

    def test_only_dark_maps(self):
        dungeon_map = DungeonMap()
        dungeon_map.see(FakeMap('Alefgard', is_dark=False), 5, 5, 7)
        self.assertEqual({}, dungeon_map.floors)

    def test_each_floor_its_own(self):
        dungeon_map = DungeonMap()
        dungeon_map.see(FakeMap('GarinsGraveB1'), 1, 1, 1)
        dungeon_map.see(FakeMap('GarinsGraveB2'), 2, 2, 1)
        self.assertEqual([(1, 1)], dungeon_map.floors['GarinsGraveB1'].seen_cells())
        self.assertEqual([(2, 2)], dungeon_map.floors['GarinsGraveB2'].seen_cells())

    def test_save_round_trip_and_bad_data(self):
        dungeon_map = DungeonMap()
        dungeon_map.see(FakeMap('GarinsGraveB1'), 1, 1, 3)
        loaded = DungeonMap.from_save(json.loads(json.dumps(dungeon_map.to_save())))
        self.assertEqual(dungeon_map.to_save(), loaded.to_save())
        self.assertEqual({}, DungeonMap.from_save(None).floors)
        self.assertEqual({}, DungeonMap.from_save({'SwampCave': 'nonsense', 'Kol': [0, 3, '']}).floors)
        self.assertEqual(['GarinsGraveB1'], list(DungeonMap.from_save(
            {**dungeon_map.to_save(), 'SwampCave': [1, 2, '!!']}).floors))


class DungeonTestCase(SaveStateTestCase):

    def new_game(self):
        game = super().new_game()
        game.game_state.config['NO_BATTLES'] = True  # no fights in the Swamp Cave while walking
        return game


class TestInTheGame(DungeonTestCase):

    def enter_swamp_cave(self, game):
        self.go_to(game, 'SwampCave', SWAMP_CAVE_START)

    def test_walking_in_the_dark_records_the_path(self):
        game = self.game
        self.enter_swamp_cave(game)
        self.run_frames(game, 1)
        self.assertEqual([SWAMP_CAVE_START], game.dungeon_map.floors['SwampCave'].seen_cells())
        self.run_frames(game, 64, script=down_script)  # steps down, no torch: only the hero's own blocks are seen
        row, column = SWAMP_CAVE_START
        seen = game.dungeon_map.floors['SwampCave'].seen_cells()
        self.assertGreaterEqual(len(seen), 4)
        self.assertEqual([(row + step, column) for step in range(len(seen))], seen)
        self.assertEqual((game.player.row, game.player.column), seen[-1])

    def test_a_torch_lights_more(self):
        game = self.game
        self.enter_swamp_cave(game)
        game.game_state.lit_diameter = 3
        self.run_frames(game, 1)
        self.assertEqual(9, len(game.dungeon_map.floors['SwampCave'].seen_cells()))

    def test_nothing_on_a_lit_map(self):
        game = self.game
        self.go_to(game, 'Brecconary')
        self.run_frames(game, 40)
        self.assertEqual({}, game.dungeon_map.floors)

    def test_kept_with_the_adventure_log(self):
        game = self.game
        self.enter_swamp_cave(game)
        self.run_frames(game, 48, script=down_script)
        game.player.adventure_log = 1
        game.cmd_menu.directories.save_dir = self.save_dir
        game.cmd_menu.save()
        save = read_save(self.save_dir, os.path.basename(save_path(self.save_dir, 1)))
        self.assertEqual(game.dungeon_map.to_save(), save['DungeonMap'])
        loaded = self.new_game()
        loaded.load_game(save)
        self.assertEqual(game.dungeon_map.to_save(), loaded.dungeon_map.to_save())
        # a save from before the dungeon map: nothing seen
        del save['DungeonMap']
        loaded.load_game(save)
        self.assertEqual({}, loaded.dungeon_map.floors)

    def test_kept_in_save_states(self):
        game = self.game
        self.enter_swamp_cave(game)
        self.run_frames(game, 32, script=down_script)
        saved = game.dungeon_map.to_save()
        game.save_state(1)
        self.run_frames(game, 64, script=down_script)
        self.assertNotEqual(saved, game.dungeon_map.to_save())
        game.load_state(1)
        self.assertEqual(saved, game.dungeon_map.to_save())
        self.assertEqual(saved, comparable(take_snapshot(game))['dungeon_map'])

    def test_a_save_state_from_before_has_nothing_seen(self):
        from src.save_state import restore_snapshot
        game = self.game
        self.enter_swamp_cave(game)
        self.run_frames(game, 32, script=down_script)
        snapshot = comparable(take_snapshot(game))
        del snapshot['dungeon_map']
        restore_snapshot(game, snapshot, fade_in=False)
        self.assertEqual({}, game.dungeon_map.floors)


class TestKey(DungeonTestCase):

    def press_m(self, game):
        with patch.object(game, 'open_dungeon_map') as open_dungeon_map:
            game.handle_dungeon_map_key(key(K_m))
            with patch('src.movement.key') as movement_key:
                movement_key.get_pressed.return_value = HeldKeys()
                for _ in range(20):
                    game.map_frame()
        return open_dungeon_map.call_count

    def test_m_opens_it_on_a_dark_map(self):
        game = self.game
        self.go_to(game, 'SwampCave', SWAMP_CAVE_START)
        self.assertEqual(1, self.press_m(game))

    def test_not_on_a_lit_map(self):
        game = self.game
        self.go_to(game, 'Brecconary')
        self.assertEqual(0, self.press_m(game))

    def test_not_with_the_option_off(self):
        game = self.game
        self.go_to(game, 'SwampCave', SWAMP_CAVE_START)
        game.game_state.config['DUNGEON_MAP'] = False
        self.assertEqual(0, self.press_m(game))

    def test_the_overlay_closes_and_puts_the_frame_back(self):
        for close_key in (K_m, K_j, K_ESCAPE):
            with self.subTest(key=pygame.key.name(close_key)):
                game = self.game
                overlay = DungeonMapOverlay(game)
                with patch('src.dungeon_map.next_frame'), \
                        patch('src.dungeon_map.frame_events', side_effect=[[], [key(close_key)]]), \
                        patch.object(overlay, 'close') as close:
                    overlay.run()
                close.assert_called_once()


class TestDrawing(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((512, 480))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        from tests.test_character_redraw import make_game
        self.game = make_game('SwampCave')

    def test_blocks_fit_the_window(self):
        scale = test_config['SCALE']
        inner = Rect(0, 0, (MAP_WINDOW.width * 16 - 16) * scale, (MAP_WINDOW.height * 16 - 16) * scale)
        for rows, columns in ((37, 14), (26, 26), (7, 16), (11, 11)):
            with self.subTest(size=(rows, columns)):
                size = block_pixels(Floor(rows, columns), scale)
                self.assertLessEqual(rows * size, inner.height)
                self.assertLessEqual(columns * size, inner.width)
                self.assertEqual(0, size % scale)

    def test_seen_blocks_hero_and_stairs(self):
        game = self.game
        current_map = game.current_map
        floor = Floor(len(current_map.layout), len(current_map.layout[0]))
        layout = current_map.layout
        stairs = SWAMP_CAVE_STAIRS
        wall = next((row, column) for row, line in enumerate(layout) for column, value in enumerate(line)
                    if current_map.get_tile_by_value(value) == 'WALL')
        brick = SWAMP_CAVE_START
        chest = next(((row, column) for row, line in enumerate(layout) for column, value in enumerate(line)
                      if current_map.get_tile_by_value(value) == 'TREASURE_BOX'), None)
        for cell in (stairs, wall, brick) + ((chest,) if chest else ()):
            floor.see(*cell)
        scale, tile_size = test_config['SCALE'], test_config['TILE_SIZE']
        hero = (stairs[0] + 1, stairs[1])
        for hero_visible in (True, False):
            self.screen.fill((0, 0, 0))
            map_rect = draw_floor(self.screen, current_map, floor, hero, hero_visible, scale, tile_size)
            size = block_pixels(floor, scale)

            def color_at(cell):
                return tuple(self.screen.get_at((map_rect.x + cell[1] * size + size // 2,
                                                 map_rect.y + cell[0] * size + size // 2)))[:3]
            self.assertEqual(STAIRS_UP_COLOR, color_at(stairs))
            self.assertEqual(WALL_COLOR, color_at(wall))
            self.assertEqual(FLOOR_COLOR, color_at(brick))
            if chest:
                self.assertEqual(CHEST_COLOR, color_at(chest))
            self.assertEqual(HERO_COLOR if hero_visible else (0, 0, 0), color_at(hero))
            self.assertEqual((0, 0, 0), color_at((SWAMP_CAVE_START[0] + 3, SWAMP_CAVE_START[1])))  # not seen

    def test_overlay_draws_and_closes_back_to_the_frame(self):
        game = self.game
        game.config['NO_BLIT'] = False
        from tests.test_character_redraw import draw_frame
        draw_frame(game)
        before = pygame.image.tobytes(game.screen, 'RGB')
        overlay = DungeonMapOverlay(game)
        game.dungeon_map.see(game.current_map, game.player.row, game.player.column, 1)
        with patch('src.dungeon_map.display.update'):
            overlay.draw(game.screen.copy(), True)
            self.assertNotEqual(before, pygame.image.tobytes(game.screen, 'RGB'))
            overlay.close(pygame.image.frombytes(before, game.screen.get_size(), 'RGB'))
        self.assertEqual(before, pygame.image.tobytes(game.screen, 'RGB'))


class TestNesFramesUnchanged(DungeonTestCase):

    def test_recording_draws_nothing(self):
        # The frames on a dark floor are the same whether the record is kept or not
        frames = []
        for keep in (True, False):
            game = self.new_game()
            game.game_state.config['NO_BLIT'] = False
            self.go_to(game, 'SwampCave', SWAMP_CAVE_START)
            pictures = []
            with patch.object(DungeonMap, 'see', autospec=True) if not keep else nullcontext():
                for _ in range(3):
                    self.run_frames(game, 16, script=down_script)
                    pictures.append(pygame.image.tobytes(game.screen, 'RGB'))
            frames.append(pictures)
        self.assertEqual(frames[0], frames[1])


class TestControllerButton(TestCase):

    def test_the_top_face_button_presses_m(self):
        from src.gamepad import Gamepad, PadState
        from tests.test_gamepad import FakeBackend
        self.assertIn(K_m, Gamepad(FakeBackend()).pad_keys(PadState(frozenset({"y"}))))
