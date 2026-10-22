"""
The three fixed guardian fights (NES Bank03 MovementUpdates: CheckAxeKnight, CheckGrnDragon, CheckGolem; EnemyDefeated;
RunSuccessful), played on a real Game: the hero takes a real step onto the guardian's tile and the fight that follows
is a real one. Only the windows that wait for a key press are replaced.
"""
import os
from collections import defaultdict
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_DOWN, K_LEFT, K_RETURN, K_RIGHT, K_UP

from src.battle_controller import BattleOutcome
from src.config.test_config import test_config
from src.direction import Direction
from src.game import Game
from src.game_functions import set_character_position
from src.guardians import AXE_KNIGHT, GOLEM, GREEN_DRAGON, GUARDIANS, escape_coordinates, guardian_at, \
    record_victory
from src.map_layouts import MapLayouts
from src.maps import map_lookup
from src.menu import CommandMenu
from src.story_flags import StoryFlags

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

STEP_KEYS = {Direction.UP.value: K_UP, Direction.DOWN.value: K_DOWN,
             Direction.LEFT.value: K_LEFT, Direction.RIGHT.value: K_RIGHT}


def setUpModule():
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_mode((800, 600))


def tearDownModule():
    pygame.quit()


class TestGuardianTable(TestCase):
    """The guardians' tiles, checked against the layouts and the NES coordinates."""

    def test_tiles_are_the_nes_ones(self):
        # Overworld (x, y) is (y + 7, x + 8), Swamp Cave (y + 6, x + 4), Hauksness (y + 8, x + 9)
        self.assertEqual(GOLEM.coordinates, (100 + 7, 73 + 8))
        self.assertEqual(GREEN_DRAGON.coordinates, (14 + 6, 4 + 4))
        self.assertEqual(AXE_KNIGHT.coordinates, (12 + 8, 18 + 9))

    def test_escape_moves_one_block_back(self):
        # NES RunSuccessful: DEC CharXPos in Hauksness, DEC CharYPos (MovePlyrUp1Block) for the other two
        self.assertEqual(AXE_KNIGHT.escape_coordinates, (20, 26))
        self.assertEqual(GREEN_DRAGON.escape_coordinates, (19, 8))
        self.assertEqual(GOLEM.escape_coordinates, (106, 81))

    def test_guardians_stand_on_walkable_chokepoints(self):
        layouts = MapLayouts().map_layout_lookup
        for guardian in GUARDIANS:
            game_map = map_lookup[guardian.map_identifier](test_config)
            layout = layouts[guardian.map_identifier]
            for row, column in (guardian.coordinates, guardian.escape_coordinates):
                self.assertNotIn(game_map.get_tile_by_value(layout[row][column]), ('WALL', 'WATER', 'MOUNTAINS'),
                                 guardian.enemy_name)
        # The Golem stands in the one gap in the wall around Cantlin, the Green Dragon in the one-tile passage to
        # Gwaelin's door
        alefgard = map_lookup['Alefgard'](test_config)
        self.assertEqual([alefgard.get_tile_by_value(layouts['Alefgard'][107][column]) for column in range(79, 84)],
                         ['WALL', 'WALL', 'GRASS', 'WALL', 'WALL'])
        swamp_cave = map_lookup['SwampCave'](test_config)
        self.assertEqual([swamp_cave.get_tile_by_value(layouts['SwampCave'][20][column]) for column in range(4, 10)],
                         ['BRICK', 'WALL', 'WALL', 'WALL', 'BRICK', 'WALL'])

    def test_guardian_at(self):
        flags = StoryFlags()
        self.assertIs(guardian_at('Alefgard', (107, 81), flags), GOLEM)
        self.assertIs(guardian_at('SwampCave', (20, 8), flags), GREEN_DRAGON)
        self.assertIs(guardian_at('Hauksness', (20, 27), flags), AXE_KNIGHT)
        self.assertIsNone(guardian_at('Alefgard', (108, 81), flags))
        self.assertIsNone(guardian_at('Hauksness', (107, 81), flags))

    def test_beaten_guardians_stay_away_but_the_axe_knight_comes_back(self):
        flags = StoryFlags(golem_defeated=True, green_dragon_defeated=True)
        self.assertIsNone(guardian_at('Alefgard', (107, 81), flags))
        self.assertIsNone(guardian_at('SwampCave', (20, 8), flags))
        self.assertIs(guardian_at('Hauksness', (20, 27), flags), AXE_KNIGHT)
        # No push back off a beaten guardian's tile either (RunSuccessful checks the flags too)
        self.assertIsNone(escape_coordinates('Alefgard', (107, 81), flags))
        self.assertIsNone(escape_coordinates('SwampCave', (20, 8), flags))
        self.assertEqual(escape_coordinates('Hauksness', (20, 27), flags), (20, 26))

    def test_no_guardians_once_the_dragonlord_is_dead(self):
        # NES CheckForTriggers skips MovementUpdates once F_DGNLRD_DEAD is set
        flags = StoryFlags(dragonlord_defeated=True)
        for guardian in GUARDIANS:
            self.assertIsNone(guardian_at(guardian.map_identifier, guardian.coordinates, flags))

    def test_victory_flags_follow_enemy_defeated(self):
        flags = StoryFlags()
        record_victory('Green Dragon', 'Alefgard', flags)  # a random Green Dragon on the overworld
        record_victory('Golem', 'SwampCave', flags)
        record_victory('Axe Knight', 'Hauksness', flags)
        self.assertEqual(flags, StoryFlags())
        record_victory('Green Dragon', 'SwampCave', flags)
        self.assertEqual(flags, StoryFlags(green_dragon_defeated=True))
        record_victory('Golem', 'Alefgard', flags)
        self.assertEqual(flags, StoryFlags(green_dragon_defeated=True, golem_defeated=True))


class TestGuardianFights(TestCase):

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.player = self.game.player
        self.player.name = "Erdrick"
        self.lines: list = []

        def record(_menu, text, *_args, **_kwargs):
            self.lines.append(text)
        for target in ('show_line_in_dialog_box', 'show_text_in_dialog_box'):
            patch.object(CommandMenu, target, autospec=True, side_effect=record).start()
        patch.object(CommandMenu, 'wait_for_button').start()
        patch('src.music_player.mixer').start()
        patch('src.battle_controller.time').start()
        patch('src.waiting.time.wait').start()  # the battle transition and the level-up pause
        # No random fights: the guardians' tiles are in enemy zones, and a random fight would wait for battle input
        patch('src.game.roll_encounter', return_value=None).start()
        # Nor the opening flee and ambush rolls (#232): the hero always gets the first turn
        patch('src.battle_controller.BattleController.start_fight', return_value=False).start()
        self.addCleanup(patch.stopall)
        self.enemies_fought: list = []

    @property
    def where(self):
        tile_size = self.game.tile_size
        return self.game.current_map.identifier, (self.player.rect.y // tile_size, self.player.rect.x // tile_size)

    def go_to(self, map_name, coordinates, facing):
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates,
                             direction=facing)
        self.settle()

    def settle(self):
        """What the game loop does every frame: the hero's row and column follow its rect, then the tiles under and
        in front of the hero are looked up."""
        set_character_position(self.player, self.game.tile_size)
        self.game._handle_post_move_checks()

    def step(self, direction):
        """One real step, the way the game loop takes it: move_player until the hero is on the next tile, then
        handle_battles, which starts any fight the step queued."""
        keys = defaultdict(bool, {STEP_KEYS[direction]: True})
        self.game.move_player(keys)
        for _ in range(1000):
            if not self.player.is_moving:
                break
            self.game.move_player(keys)
        self.assertFalse(self.player.is_moving)
        self.game.handle_battles()
        self.settle()

    def step_onto(self, guardian, prompts):
        """Stand next to the guardian's tile and step onto it, fighting with the given battle-menu stand-in."""
        row, column = guardian.escape_coordinates
        direction = Direction.DOWN.value if column == guardian.coordinates[1] else Direction.RIGHT.value
        self.go_to(guardian.map_identifier, (row, column), direction)
        with patch.object(self.game.battle_ctrl, 'handle_battle_prompts', side_effect=prompts) as battle_prompts:
            self.step(direction)
        return battle_prompts

    # Battle-menu stand-ins

    def win(self, _run_away, current_battle):
        self.enemies_fought.append(current_battle.enemy.name)
        current_battle.enemy.hp = 0
        return False

    def run_away(self, _run_away, current_battle):
        """RUN, through the real PlyrRun path (a sleeping enemy can't block it)."""
        self.enemies_fought.append(current_battle.enemy.name)
        current_battle.enemy.is_asleep = True
        self.game.battle_ctrl.last_battle_action = 'Run'
        with patch.object(self.game, 'auto_battle', True):
            return type(self.game.battle_ctrl).handle_battle_prompts(self.game.battle_ctrl, _run_away,
                                                                      current_battle)

    def die(self, _run_away, current_battle):
        self.enemies_fought.append(current_battle.enemy.name)
        self.player.current_hp = 0
        self.player.is_dead = True
        return False

    # The trigger

    def test_each_guardian_fights_on_its_tile(self):
        for guardian in GUARDIANS:
            with self.subTest(guardian.enemy_name):
                self.enemies_fought.clear()
                self.step_onto(guardian, self.win)
                self.assertEqual(self.enemies_fought, [guardian.enemy_name])
                self.assertEqual(self.where, (guardian.map_identifier, guardian.coordinates))

    def test_no_fight_on_the_tile_before(self):
        # Walking up to the guardian doesn't start anything; only the step onto its tile does
        row, column = GOLEM.escape_coordinates
        self.go_to('Alefgard', (row - 1, column), Direction.DOWN.value)
        with patch.object(self.game.battle_ctrl, 'start_scripted_battle') as start:
            self.step(Direction.DOWN.value)
        start.assert_not_called()
        self.assertEqual(self.where, ('Alefgard', GOLEM.escape_coordinates))

    def test_searching_does_not_start_a_fight(self):
        self.go_to('Hauksness', AXE_KNIGHT.coordinates, Direction.DOWN.value)
        self.game._handle_post_move_checks()
        with patch.object(self.game.battle_ctrl, 'start_scripted_battle') as start:
            self.game.cmd_menu.search()
            self.game.handle_battles()
        start.assert_not_called()
        self.assertEqual(self.player.armor, "Erdrick's Armor")

    def test_the_step_brings_no_random_fight_as_well(self):
        test_config_force = {**self.game.game_state.config, 'FORCE_BATTLE': True}
        with patch.object(self.game.game_state, 'config', test_config_force):
            self.step_onto(GOLEM, self.win)
            with patch.object(self.game.battle_ctrl, 'run_battle') as random_fight:
                self.game.handle_battles()  # the next frame
        random_fight.assert_not_called()
        self.assertEqual(self.enemies_fought, ['Golem'])

    def test_no_guardians_after_the_dragonlord(self):
        self.game.story_flags.dragonlord_defeated = True
        for guardian in GUARDIANS:
            with self.subTest(guardian.enemy_name):
                self.step_onto(guardian, self.win)
                self.assertEqual(self.where, (guardian.map_identifier, guardian.coordinates))
        self.assertEqual(self.enemies_fought, [])

    # Winning

    def test_beating_the_golem_sets_its_flag_and_he_is_gone(self):
        self.step_onto(GOLEM, self.win)
        self.assertTrue(self.game.story_flags.golem_defeated)
        self.assertFalse(self.game.story_flags.green_dragon_defeated)
        self.assertEqual(self.where, ('Alefgard', GOLEM.coordinates))
        self.step_onto(GOLEM, self.win)
        self.assertEqual(self.enemies_fought, ['Golem'])
        self.assertEqual(self.where, ('Alefgard', GOLEM.coordinates))

    def test_beating_the_green_dragon_sets_its_flag_and_it_is_gone(self):
        self.step_onto(GREEN_DRAGON, self.win)
        self.assertTrue(self.game.story_flags.green_dragon_defeated)
        self.assertFalse(self.game.story_flags.golem_defeated)
        self.step_onto(GREEN_DRAGON, self.win)
        self.assertEqual(self.enemies_fought, ['Green Dragon'])

    def test_the_axe_knight_fights_every_time(self):
        # NES CheckAxeKnight has no flag check, so he's back even after he's beaten and the armor is found
        self.step_onto(AXE_KNIGHT, self.win)
        self.assertEqual(self.game.story_flags, StoryFlags(left_throne_room=True))
        self.game.cmd_menu.search()
        self.assertEqual(self.player.armor, "Erdrick's Armor")
        self.step_onto(AXE_KNIGHT, self.win)
        self.assertEqual(self.enemies_fought, ['Axe Knight', 'Axe Knight'])

    def test_beaten_guardians_are_saved(self):
        self.step_onto(GOLEM, self.win)
        self.step_onto(GREEN_DRAGON, self.win)
        flags = StoryFlags.from_save({'StoryFlags': self.game.story_flags.to_save()})
        self.assertTrue(flags.golem_defeated)
        self.assertTrue(flags.green_dragon_defeated)

    # Running away

    def test_running_moves_the_hero_one_block_back(self):
        for guardian in GUARDIANS:
            with self.subTest(guardian.enemy_name):
                with patch.object(self.game.sound, 'play_sound') as play_sound:
                    self.step_onto(guardian, self.run_away)
                self.assertEqual(self.where, (guardian.map_identifier, guardian.escape_coordinates))
                play_sound.assert_any_call(self.game.directories.stairs_down_sfx)  # MapChngWithSound
                if guardian.defeated_flag is not None:
                    self.assertFalse(getattr(self.game.story_flags, guardian.defeated_flag))
                # Still there: the next step onto the tile is another fight
                self.step_onto(guardian, self.win)
        self.assertEqual(self.enemies_fought, ['Axe Knight', 'Axe Knight', 'Green Dragon', 'Green Dragon',
                                               'Golem', 'Golem'])

    def test_running_from_the_axe_knight_keeps_the_hero_off_the_armor(self):
        self.step_onto(AXE_KNIGHT, self.run_away)
        self.game.cmd_menu.search()
        self.assertNotEqual(self.player.armor, "Erdrick's Armor")

    def test_an_enemy_running_away_does_not_move_the_hero(self):
        # NES CheckEnRun goes straight to ExitFight, not RunSuccessful. (No guardian can actually flee: it takes
        # double their attack in strength.)
        def enemy_flees(_run_away, current_battle):
            self.enemies_fought.append(current_battle.enemy.name)
            return True
        self.step_onto(GOLEM, enemy_flees)
        self.assertEqual(self.where, ('Alefgard', GOLEM.coordinates))
        self.assertFalse(self.game.story_flags.golem_defeated)

    # Dying

    def test_dying_sends_the_hero_home_and_the_guardian_waits(self):
        for guardian in (GOLEM, GREEN_DRAGON):
            with self.subTest(guardian.enemy_name):
                self.player.current_hp = self.player.max_hp
                with patch.object(self.game.music_player, 'load_and_play_music'), \
                        patch.object(self.game.calculation, 'convert_to_frames_since_start_time', return_value=318):
                    self.step_onto(guardian, self.die)
                self.assertEqual(self.where, ('TantegelThroneRoom', (10, 13)))
                self.assertFalse(getattr(self.game.story_flags, str(guardian.defeated_flag)))
                self.assertEqual(self.player.current_hp, self.player.max_hp)
                self.step_onto(guardian, self.win)
                self.assertTrue(getattr(self.game.story_flags, str(guardian.defeated_flag)))

    # The Fairy Flute

    def test_the_fairy_flute_puts_the_golem_to_sleep_in_a_real_fight(self):
        """The whole battle menu, driven by key presses: ITEM, the Fairy Flute, then RUN, which a sleeping enemy
        can't block (NES ChkUseFlute, EnStillAsleep, PlyrRun). Running still moves the hero back off the tile, so
        the Golem has to be beaten to reach Cantlin.

        Each read of the event queue is one NES frame (the battle command window reads the joypad once a frame,
        Bank01 WndGetButtons), and each key is tapped after a few frames with nothing pressed."""
        self.player.inventory = ['Fairy Flute']
        presses = []
        for pressed_key in (K_DOWN, K_RIGHT, K_RETURN,  # ITEM
                            K_RETURN,  # the Fairy Flute, the only item
                            K_DOWN, K_RETURN):  # RUN: the next turn's window starts on FIGHT again
            presses += [[], [], [], [pressed_key]]
        calls = {'count': 0}
        golem_asleep = []

        def get_events(*_args, **_kwargs):
            calls['count'] += 1
            self.assertLess(calls['count'], 10000, "the battle menu is waiting for a key that never comes")
            battle = self.game.cmd_menu.current_battle
            if battle is not None:
                golem_asleep.append(battle.enemy.is_asleep)
            if not presses:
                return []
            return [pygame.event.Event(pygame.KEYDOWN, key=key) for key in presses.pop(0)]

        row, column = GOLEM.escape_coordinates
        self.go_to('Alefgard', (row, column), Direction.DOWN.value)
        hp = self.player.current_hp
        with patch.object(pygame.event, 'get', side_effect=get_events), \
                patch('src.cursor.get_ticks', side_effect=lambda: -(-calls['count'] * 1000 // 60)), \
                patch.object(self.game.battle_ctrl, 'fight_enemy',
                             wraps=self.game.battle_ctrl.fight_enemy) as fight_enemy:
            self.step(Direction.DOWN.value)
        fight_enemy.assert_called_once_with('Golem')
        self.assertEqual(presses, [])
        self.assertIn("Erdrick blew the Fairies' Flute.", self.lines)
        self.assertIn("Quietly Golem closes his eyes and settles into sleep.", self.lines)
        self.assertIn("Erdrick started to run away.\n", self.lines)
        self.assertNotIn("The Golem attacks!\n", self.lines)  # asleep, and the flute takes his turn
        self.assertEqual(self.player.current_hp, hp)
        self.assertTrue(golem_asleep[-1])
        self.assertEqual(self.where, ('Alefgard', GOLEM.escape_coordinates))
        self.assertFalse(self.game.story_flags.golem_defeated)

    def test_scripted_outcomes(self):
        # start_scripted_battle reports the guardian fights like any other
        with patch.object(self.game.battle_ctrl, 'handle_battle_prompts', side_effect=self.win):
            self.go_to('Alefgard', GOLEM.coordinates, Direction.DOWN.value)
            self.assertEqual(self.game.battle_ctrl.start_scripted_battle('Golem'), BattleOutcome.VICTORY)
