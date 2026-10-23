"""Save states (src/save_state.py): Shift + F1/F2/F3 saves the game into slot 1/2/3, F1/F2/F3 loads it. Not NES."""
import json
import os
import random
import tempfile
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_DOWN, K_F1, K_F2, K_F3, K_UP, K_k, KEYDOWN, KMOD_SHIFT
from pygame.event import Event

from src.battle_controller import BattleOutcome
from src.config.test_config import test_config
from src.direction import Direction
from src.maps import map_lookup
from src.save_state import STATE_FORMAT_VERSION, VERSION_KEY, StateError, decode_snapshot, read_state, \
    state_path, take_snapshot
from src.virtual_joypad import VirtualJoypad
from src.waiting import WINDOW_CONTEXT
from tests import helpers

# Grass by Tantegel Castle (see tests/test_auto_grind.py): one step down is grass too
ALEFGARD_GRASS = (50, 44)
SEED = 1234


def key(pressed_key, mod=0):
    return Event(KEYDOWN, key=pressed_key, mod=mod, unicode='', scancode=0)


class HeldKeys:
    """What key.get_pressed() returns: the keys in ``held`` are down."""

    def __init__(self, held=()):
        self.held = set(held)

    def __getitem__(self, pressed_key):
        return pressed_key in self.held


def walk_script(frame: int) -> set[int]:
    """Back and forth: down for 2 steps, up for 2 steps, with a frame now and then with nothing held."""
    phase = frame % 80
    if phase < 32:
        return {K_DOWN}
    if 40 <= phase < 72:
        return {K_UP}
    return set()


def comparable(snapshot: dict) -> dict:
    """A snapshot as it reads back from a state file."""
    return json.loads(json.dumps(snapshot))


class SaveStateTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()

    def setUp(self):
        pygame.event.clear()
        self.save_dir = tempfile.mkdtemp()
        self.messages: list[str] = []
        self.game = self.new_game()
        self.addCleanup(patch.stopall)

    def new_game(self):
        game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True,
                                 'SAVE_DIR': self.save_dir})
        patch.object(game, 'draw_temporary_text', side_effect=self.messages.append).start()
        return game

    def go_to(self, game, map_name, coordinates=None, direction=Direction.DOWN.value):
        next_map = map_lookup[map_name](game.config)
        game.change_map(next_map, destination_coordinates=coordinates or next_map.initial_coordinates,
                        direction=direction)
        game.player.direction_value = direction

    def run_frames(self, game, frames: int, first_frame: int = 0, script=walk_script) -> list[dict]:
        """Run the main loop's frames (a map frame, then the draw), the hero walking by script (walk_script unless
        given), and return the game's snapshot after each one."""
        trace = []
        with patch('src.movement.key') as movement_key:
            for frame in range(first_frame, first_frame + frames):
                movement_key.get_pressed.return_value = HeldKeys(script(frame))
                game.map_frame()
                game.drawer.draw_all(game, game.movement.sprites_animate)
                game.loop_count += 1
                trace.append(comparable(take_snapshot(game)))
        return trace


class TestSnapshot(SaveStateTestCase):

    def test_save_change_everything_load(self):
        game = self.game
        self.go_to(game, 'Brecconary')
        random.seed(SEED)
        self.run_frames(game, 50)
        player = game.player
        player.inventory.append('Magic Key')
        game.repel_timer = 9
        game.game_state.radiant_timer = 12
        player.wearing_cursed_belt = True
        saved = comparable(take_snapshot(game))
        game.save_state(1)
        self.assertEqual(["State 1 saved"], self.messages)
        self.assertTrue(os.path.exists(state_path(self.save_dir, 1)))

        # change everything a snapshot keeps
        self.run_frames(game, 37, first_frame=50)
        player.current_hp, player.current_mp, player.gold, player.total_experience = 1, 0, 9999, 5000
        player.inventory = ['Herb'] * 6
        player.weapon, player.armor, player.wearing_cursed_belt = 'Club', 'Leather Armor', False
        game.story_flags.rainbow_bridge_built = game.story_flags.golem_defeated = True
        game.chest_history.record('TantegelThroneRoom', (8, 5))
        game.layouts.map_layout_lookup['Garinham'][3][3] = 0
        game.repel_timer = game.game_state.radiant_timer = 0
        game.game_state.light_diameter = 7
        game.config['AUTO_STAIRS'] = not game.config['AUTO_STAIRS']
        game.config['TEXT_SPEED'] = 'Slow'
        game.movement.npc_schedule.frame_counter = 77
        for npc in game.current_map.roaming_characters:
            npc.rect.x += 3
            npc.direction_value = Direction.LEFT.value
        random.seed(99)
        self.go_to(game, 'Alefgard', ALEFGARD_GRASS, direction=Direction.RIGHT.value)

        game.load_state(1)
        self.assertEqual("State 1 loaded", self.messages[-1])
        self.assertEqual(saved, comparable(take_snapshot(game)))
        self.assertEqual('Brecconary', game.current_map.identifier)
        self.assertIn('Magic Key', game.player.inventory)
        self.assertEqual(9, game.repel_timer)
        self.assertTrue(game.player.is_cursed)
        self.assertFalse(game.story_flags.rainbow_bridge_built)
        self.assertNotEqual(0, game.layouts.map_layout_lookup['Garinham'][3][3])

    def test_npcs_and_the_hero_are_put_back_pixel_for_pixel(self):
        game = self.game
        self.go_to(game, 'Brecconary')
        random.seed(SEED)
        self.run_frames(game, 60)
        positions = [(npc.identifier, npc.rect.topleft, npc.direction_value, npc.is_moving)
                     for npc in game.current_map.roaming_characters]
        hero = game.player.rect.topleft, game.player.direction_value, game.camera.pos
        game.save_state(2)
        self.run_frames(game, 100, first_frame=60)
        game.load_state(2)
        self.assertEqual(positions, [(npc.identifier, npc.rect.topleft, npc.direction_value, npc.is_moving)
                                     for npc in game.current_map.roaming_characters])
        self.assertEqual(hero, (game.player.rect.topleft, game.player.direction_value, game.camera.pos))

    def test_an_opened_door_stays_open(self):
        game = self.game
        self.go_to(game, 'Brecconary')
        door_row, door_column = 3, 3
        layout = game.layouts.map_layout_lookup['Brecconary']
        layout[door_row][door_column] = game.current_map.floor_tile_key['BRICK']['val']
        game.save_state(1)
        layout[door_row][door_column] = game.current_map.floor_tile_key['DOOR']['val']
        game.load_state(1)
        self.assertEqual(game.current_map.floor_tile_key['BRICK']['val'],
                         game.layouts.map_layout_lookup['Brecconary'][door_row][door_column])
        self.assertIs(game.current_map.layout, game.layouts.map_layout_lookup['Brecconary'])

    def test_a_removed_npc_stays_removed(self):
        game = self.game
        self.go_to(game, 'Brecconary')
        removed = game.current_map.roaming_characters[0]
        game.cmd_menu.dialog_lookup.remove_npc(removed.identifier)
        slots = [(npc.identifier, npc.slot) for npc in game.current_map.roaming_characters]
        game.save_state(1)
        self.go_to(game, 'Alefgard', ALEFGARD_GRASS)
        game.load_state(1)
        self.assertNotIn(removed.identifier, game.current_map.characters)
        self.assertEqual(slots, [(npc.identifier, npc.slot) for npc in game.current_map.roaming_characters])


class TestRedraw(SaveStateTestCase):

    def test_the_loaded_screen_is_the_saved_screen(self):
        """No ghosts: the map drawn after loading is what was on screen when the state was saved, even when the
        state is loaded over another map (and the hero and NPCs have walked off meanwhile)."""
        self.game.config['NO_BLIT'] = False
        pygame.display.set_mode((256 * 3, 240 * 3))
        game = self.game
        game.screen = pygame.display.get_surface()
        self.go_to(game, 'Brecconary')
        random.seed(SEED)
        self.run_frames(game, 70)
        saved_screen = pygame.image.tobytes(game.screen, 'RGB')
        self.assertGreater(len(set(saved_screen)), 3)  # the map is on it
        game.save_state(1)
        for other_map in ('Brecconary', 'TantegelCourtyard'):
            with self.subTest(other_map=other_map):
                if other_map != 'Brecconary':
                    self.go_to(game, other_map)
                self.run_frames(game, 45, first_frame=70)
                self.assertNotEqual(saved_screen, pygame.image.tobytes(game.screen, 'RGB'))
                game.load_state(1)
                game.drawer.draw_all(game, game.movement.sprites_animate)
                self.assertEqual(saved_screen, pygame.image.tobytes(game.screen, 'RGB'))


class TestReplay(SaveStateTestCase):
    """Loading a state and pressing the same keys plays out exactly as the game did after it was saved."""

    def replay(self, map_name, coordinates=None):
        rolls: list = []
        fights: list = []

        def start(game):
            real_roll = __import__('src.game', fromlist=['roll_encounter']).roll_encounter

            def roll(*args):
                result = real_roll(*args)
                rolls.append((game.current_map.identifier, args[2:], result))
                return result
            patch('src.game.roll_encounter', side_effect=roll).start()
            patch.object(game.battle_ctrl, 'run_battle',
                         side_effect=lambda enemies: fights.append(enemies) or BattleOutcome.ESCAPED).start()
            self.go_to(game, map_name, coordinates)
            random.seed(SEED)

        # without saving or loading
        reference = self.new_game()
        start(reference)
        self.run_frames(reference, 50)
        rolls.clear()
        expected = self.run_frames(reference, 200, first_frame=50)
        expected_rolls = list(rolls)
        patch.stopall()

        # saving at frame 50 changes nothing
        rolls.clear()
        saver = self.new_game()
        start(saver)
        self.run_frames(saver, 50)
        saver.save_state(1)
        rolls.clear()
        self.assertEqual(expected, self.run_frames(saver, 200, first_frame=50))
        self.assertEqual(expected_rolls, rolls)
        patch.stopall()

        # a new game somewhere else, loading that state, plays the same 200 frames
        rolls.clear()
        loader = self.new_game()
        start(loader)
        random.seed(5)
        self.go_to(loader, 'TantegelCourtyard')
        loader.load_state(1)
        rolls.clear()
        self.assertEqual(expected, self.run_frames(loader, 200, first_frame=50))
        self.assertEqual(expected_rolls, rolls)
        return expected_rolls

    def test_npcs_replay_the_same(self):
        self.replay('Brecconary')

    def test_encounter_rolls_replay_the_same(self):
        rolls = self.replay('Alefgard', ALEFGARD_GRASS)
        self.assertGreater(len(rolls), 5)


class TestSlots(SaveStateTestCase):

    def test_slots_are_independent(self):
        game = self.game
        self.go_to(game, 'Brecconary')
        game.player.gold = 1
        game.save_state(1)
        game.player.gold = 2
        game.save_state(2)
        game.player.gold = 3
        game.save_state(3)
        for slot in (2, 1, 3, 2):
            game.load_state(slot)
            self.assertEqual(slot, game.player.gold)
        self.assertEqual({1, 2, 3}, {slot for slot in (1, 2, 3) if os.path.exists(state_path(self.save_dir, slot))})

    def test_empty_slot(self):
        game = self.game
        self.go_to(game, 'Brecconary')
        before = comparable(take_snapshot(game))
        game.load_state(3)
        self.assertEqual(["State 3 is empty"], self.messages)
        self.assertEqual(before, comparable(take_snapshot(game)))

    def test_old_version_is_refused(self):
        game = self.game
        self.go_to(game, 'Brecconary')
        game.save_state(1)
        with open(state_path(self.save_dir, 1)) as state_file:
            snapshot = json.load(state_file)
        snapshot[VERSION_KEY] = STATE_FORMAT_VERSION - 1
        with open(state_path(self.save_dir, 1), 'w') as state_file:
            json.dump(snapshot, state_file)
        game.player.gold = 77
        game.load_state(1)
        self.assertEqual("State 1 is from another version\nand can't be loaded", self.messages[-1])
        self.assertEqual(77, game.player.gold)

    def test_corrupt_files_are_refused(self):
        game = self.game
        self.go_to(game, 'Brecconary')
        game.save_state(1)
        with open(state_path(self.save_dir, 1)) as state_file:
            snapshot = json.load(state_file)
        broken_snapshots = [
            "{not json",
            "[1, 2, 3]",
            json.dumps({**snapshot, 'hero': {}}),
            json.dumps({**snapshot, 'map': 'Narnia'}),
            json.dumps({**snapshot, 'random': [3, 'AAAA', None]}),
            json.dumps({**snapshot, 'layout_changes': {'Brecconary': [[999, 999, 1]]}}),
        ]
        game.player.gold = 55
        before = comparable(take_snapshot(game))
        for broken in broken_snapshots:
            with self.subTest(broken=broken[:40]):
                with open(state_path(self.save_dir, 1), 'w') as state_file:
                    state_file.write(broken)
                game.load_state(1)
                self.assertEqual("State 1 can't be read", self.messages[-1])
                self.assertEqual(before, comparable(take_snapshot(game)))

    def test_decode_refuses_without_changing_anything(self):
        with self.assertRaises(StateError):
            decode_snapshot({VERSION_KEY: STATE_FORMAT_VERSION})
        self.assertIsNone(read_state(self.save_dir, 2))


class TestKeys(SaveStateTestCase):

    def setUp(self):
        super().setUp()
        self.go_to(self.game, 'Brecconary')

    def press(self, pressed_key, mod=0):
        self.game.handle_keypresses(key(pressed_key, mod))

    def until_message(self, frames=20):
        """Stand still until a save state message is shown, as it is once the NPCs' turn ends."""
        shown = len(self.messages)
        for _ in range(frames):
            self.run_frames(self.game, 1, script=lambda frame: set())
            if len(self.messages) > shown:
                return
        self.fail("no message")

    def test_shift_f_keys_save_and_f_keys_load(self):
        game = self.game
        for slot, f_key in ((1, K_F1), (2, K_F2), (3, K_F3)):
            with self.subTest(slot=slot):
                game.player.gold = slot * 10
                self.press(f_key, KMOD_SHIFT)
                self.until_message()
                self.assertTrue(os.path.exists(state_path(self.save_dir, slot)))
                self.assertEqual(f"State {slot} saved", self.messages[-1])
        game.player.gold = 0
        self.press(K_F2)
        self.until_message()
        self.assertEqual("State 2 loaded", self.messages[-1])
        self.assertEqual(20, game.player.gold)

    def test_waits_for_the_step_to_finish(self):
        game = self.game
        self.run_frames(game, 20)  # partway through the second step down
        self.assertTrue(game.player.is_moving)
        self.press(K_F1, KMOD_SHIFT)
        self.assertFalse(os.path.exists(state_path(self.save_dir, 1)))
        for _ in range(40):
            self.run_frames(game, 1, first_frame=20)
            if os.path.exists(state_path(self.save_dir, 1)):
                break
        self.assertTrue(os.path.exists(state_path(self.save_dir, 1)))
        snapshot = read_state(self.save_dir, 1)
        assert snapshot is not None
        self.assertFalse(snapshot['hero']['is_moving'])
        self.assertEqual(0, snapshot['hero']['rect'][1] % game.tile_size)

    def test_not_with_the_command_window_open(self):
        game = self.game
        game.cmd_menu.launch_signaled = True
        self.press(K_F1, KMOD_SHIFT)
        self.press(K_F1)
        self.assertIsNone(game.state_request)
        self.assertEqual([], self.messages)

    def test_not_while_paused(self):
        game = self.game
        game.paused = True
        self.press(K_F1, KMOD_SHIFT)
        self.assertIsNone(game.state_request)

    def test_not_in_a_dialog(self):
        """A dialog reads the keys in its own loop, which doesn't save on Shift + F1 (A closes the dialog here)."""
        game = self.game
        with patch.object(game, 'handle_save_state_keys') as handle_save_state_keys:
            pygame.event.post(key(K_F1, KMOD_SHIFT))
            pygame.event.post(key(K_k))
            game.cmd_menu.show_text_in_dialog_box("Hello")
            handle_save_state_keys.assert_not_called()
        self.assertFalse(os.path.exists(state_path(self.save_dir, 1)))

    def test_not_in_a_battle(self):
        """A fight reads the keys in its own loops: Shift + F1 there saves nothing."""
        game = self.game
        player = game.player
        player.total_experience = 65535
        player.level = player.get_level_by_experience()
        player.update_stats_to_current_level()
        player.restore_hp()
        player.weapon = "Erdrick's Sword"
        player.update_attack_power()

        class FightDriver:
            def __init__(self):
                self.pressed_f1 = False

            def update(self, joypad, context):
                if not self.pressed_f1:
                    self.pressed_f1 = True
                    pygame.event.post(key(K_F1, KMOD_SHIFT))
                if context == WINDOW_CONTEXT and K_k not in joypad.held:
                    joypad.tap(K_k, 2)

            def real_key(self, current_event):
                return True

        joypad = VirtualJoypad(FightDriver())
        joypad.connect()
        self.addCleanup(joypad.disconnect)
        with patch.object(game, 'handle_save_state_keys') as handle_save_state_keys:
            outcome = game.battle_ctrl.launch_fight('Slime')
            handle_save_state_keys.assert_not_called()
        self.assertIn(outcome, (BattleOutcome.VICTORY, BattleOutcome.ESCAPED))
        self.assertIsNone(game.state_request)
        self.assertFalse(os.path.exists(state_path(self.save_dir, 1)))
