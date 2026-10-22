"""
A headless run through the whole story, in NES order, from the throne room to the credits.

Each step calls what the player's commands would (TAKE, DOOR, STAIRS, SEARCH, TALK, ITEM, the overworld entrances and
the scripted Dragonlord fight) on a real Game, and checks the story state afterwards. Walking isn't what's being tested,
so the hero is put straight onto the tile each command is used from. Only what can't run headless is replaced: drawing,
the blocking text and yes/no windows (each prompt is answered by STORY_ANSWERS), long pauses, and the battle menu,
where every enemy simply loses all its HP so the real victory and ending code runs.

If a step breaks, the failure names it, e.g. "Story step 10 (use the Rainbow Drop to build the bridge) failed".
"""
import os
from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.constants import ENDING_TRIGGER_COORDINATES, GWAELIN_THRONE_ROOM_COORDINATES, RAINBOW_BRIDGE_COORDINATES, \
    RAINBOW_DROP_COORDINATES
from src.direction import Direction
from src.ending import CREDITS
from src.game import Game
from src.game_functions import set_character_position
from src.maps import CharlockB1, map_lookup
from src.maps_functions import get_center_point
from src.menu import CommandMenu

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

UP, DOWN, LEFT, RIGHT = Direction.UP.value, Direction.DOWN.value, Direction.LEFT.value, Direction.RIGHT.value

# How each yes/no window on the way is answered (True = YES). "Dost thou wish to purchase more?" at the key shop is
# answered by TestStoryRun.answer.
STORY_ANSWERS = {
    "Magic keys! They will unlock any door.\nDost thou wish to purchase one for 85 GOLD?": True,
    "Will thou take me to the castle?": True,
    "Will thou tell me now of thy deeds so they won't be forgotten?": False,  # saving isn't part of this run
    "Dost thou wish to continue thy quest?": True,
    "What sayest thou?\nWill the great warrior stand with me?": False,
    "May I travel as thy companion?": True,
}


# Story flags, read in one place (the save-story-progress work moves them all onto game.story_flags)

def rainbow_bridge_built(game) -> bool:
    return game.rainbow_bridge_built


def charlock_stairs_revealed(game) -> bool:
    return game.charlock_stairs_revealed


def carrying_gwaelin(game) -> bool:
    return game.player.is_carrying_princess


def gwaelin_returned(game) -> bool:
    return game.story_flags.gwaelin_returned


def dragonlord_defeated(game) -> bool:
    return game.story_flags.dragonlord_defeated


class TestStoryRun(TestCase):

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
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.player = self.game.player
        self.player.name = "Erdrick"
        self.shown_text: list = []
        self.prompts: list = []
        self.enemies_fought: list = []
        for target, kwargs in (
                # The text and yes/no windows wait for a key press
                ((CommandMenu, 'show_text_line_in_dialog_box'), {'autospec': True, 'side_effect': self.read_text}),
                (('data.text.dialog_lookup_table.confirmation_prompt',), {'side_effect': self.answer}),
                (('src.ending.confirmation_prompt',), {'side_effect': self.answer}),
                # Drawing, music and pauses
                ((CommandMenu, 'window_drop_down_effect'), {}),
                ((CommandMenu, 'window_drop_up_effect'), {}),
                (('data.text.dialog_lookup_table.time.wait',), {}),
                (('data.text.dialog_lookup_table.mixer',), {}),
                (('src.menu.mixer',), {}),
        ):
            (patch.object(*target, **kwargs) if len(target) == 2 else patch(*target, **kwargs)).start()
        self.addCleanup(patch.stopall)

    # Stand-ins for the windows that wait for the player

    def read_text(self, _command_menu, *args, **kwargs):
        self.shown_text.append(kwargs['line'] if 'line' in kwargs else args[0])

    def answer(self, _command_menu, prompt_line, yes_path_function, no_path_function, **_kwargs):
        self.prompts.append(prompt_line)
        if prompt_line == "Here, take this key.\nDost thou wish to purchase more?":
            # Buy keys until there are four, one for each locked door still to come plus a spare
            yes = self.player.inventory.count('Magic Key') < 4
        else:
            yes = STORY_ANSWERS[prompt_line]
        (yes_path_function if yes else no_path_function)()

    def fight_to_the_end(self, _run_away, current_battle):
        """Stand-in for the battle menu: the enemy loses all its HP, then the real victory code runs."""
        self.enemies_fought.append(current_battle.enemy.name)
        current_battle.enemy.hp = 0
        return False

    # Moving around

    @property
    def cmd_menu(self):
        return self.game.cmd_menu  # a new one is made on every map change

    @property
    def where(self):
        return self.game.current_map.identifier, (self.player.row, self.player.column)

    def settle(self, direction=None):
        """What the game loop does every frame: the hero's row and column follow its rect, then the tile under and
        in front of the hero are looked up."""
        if direction is not None:
            self.player.direction_value = direction
        set_character_position(self.player, self.game.tile_size)
        self.game._handle_post_move_checks()

    def stand_at(self, coordinates, facing=DOWN):
        """Put the hero on another tile of the current map."""
        row, column = coordinates
        self.player.rect.center = get_center_point(column, row, self.game.tile_size)
        self.settle(facing)

    def travel_to(self, map_name, coordinates, facing=DOWN):
        """Go straight to another map (for journeys that the map connectivity tests already cover)."""
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates)
        self.settle(facing)

    def walk_onto(self, coordinates):
        """Step onto an overworld entrance or a town gate, which warps without a command."""
        self.stand_at(coordinates)
        self.game.tiles_moved_since_spawn = 3
        self.game.handle_warps()
        self.settle()

    def take_stairs(self, coordinates):
        """The STAIRS command, on the given staircase."""
        self.stand_at(coordinates)
        self.cmd_menu.stairs()
        self.settle()

    def take(self, coordinates):
        self.stand_at(coordinates)
        self.cmd_menu.take()

    def open_door(self, standing_at, facing):
        self.stand_at(standing_at, facing)
        self.cmd_menu.door()

    def talk(self, standing_at, facing):
        self.stand_at(standing_at, facing)
        self.cmd_menu.talk()

    def search(self, coordinates):
        self.stand_at(coordinates)
        self.cmd_menu.search()
        self.settle()

    def tile(self, coordinates):
        row, column = coordinates
        current_map = self.game.current_map
        return current_map.get_tile_by_value(current_map.layout[row][column])

    @contextmanager
    def step(self, name):
        try:
            yield
        except AssertionError as error:
            raise AssertionError(f"Story step {name} failed: {error}") from error

    # The story

    def test_the_game_can_be_finished(self):
        game, player = self.game, self.player

        with self.step("1 (take the throne room chests)"):
            self.assertEqual(self.where, ('TantegelThroneRoom', (10, 13)))
            gold = player.gold
            self.take((10, 14))
            self.take((10, 15))
            self.take((7, 16))
            self.assertEqual(player.gold, gold + 120)
            self.assertIn('Torch', player.inventory)
            self.assertIn('Magic Key', player.inventory)
            self.assertEqual(self.tile((7, 16)), 'BRICK')

        with self.step("2 (unlock the throne room door and go down to the courtyard)"):
            self.open_door((12, 14), DOWN)
            self.assertEqual(self.tile((13, 14)), 'BRICK')
            self.assertNotIn('Magic Key', player.inventory)
            self.take_stairs((14, 18))
            self.assertEqual(self.where, ('TantegelCourtyard', (14, 14)))

        with self.step("3 (buy Magic Keys from the courtyard's key shop)"):
            player.gold = 1000  # stands in for the gold won in fights along the way
            self.talk((10, 31), UP)  # across the shop counter
            self.assertEqual(player.inventory.count('Magic Key'), 4)
            self.assertEqual(player.gold, 1000 - 4 * 85)

        with self.step("4 (open the locked door to the cellar and get the Stones of Sunlight)"):
            self.open_door((14, 25), UP)
            self.assertEqual(self.tile((13, 25)), 'BRICK')
            self.take_stairs((36, 36))
            self.assertEqual(self.where, ('TantegelCellar', (5, 1)))
            self.take((6, 5))
            self.assertIn('Stones of Sunlight', player.inventory)
            self.take_stairs((5, 1))
            self.assertEqual(self.where, ('TantegelCourtyard', (36, 36)))
            self.walk_onto((37, 17))  # the south gate
            self.assertEqual(self.where, ('Alefgard', (50, 51)))

        with self.step("5 (get the Silver Harp in Garin's Grave)"):
            self.walk_onto((9, 10))
            self.assertEqual(self.where, ('Garinham', (14, 9)))
            for stairs, arrival in (((0, 28), ('GarinsGraveB1', (12, 7))),
                                    ((19, 2), ('GarinsGraveB2', (3, 12))),
                                    ((11, 2), ('GarinsGraveB3', (18, 3))),
                                    ((6, 10), ('GarinsGraveB4', (5, 1))),
                                    ((5, 6), ('GarinsGraveB3', (10, 11)))):
                self.take_stairs(stairs)
                self.assertEqual(self.where, arrival)
            self.take((7, 14))
            self.assertIn('Silver Harp', player.inventory)
            self.cmd_menu.outside()
            self.settle()
            self.assertEqual(self.where, ('Garinham', (0, 28)))

        with self.step("6 (trade the Silver Harp for the Staff of Rain)"):
            self.travel_to('Alefgard', (9, 89))
            self.walk_onto((8, 89))
            self.assertEqual(self.where, ('StaffOfRainCave', (11, 6)))
            self.talk((6, 7), LEFT)
            self.assertNotIn('Silver Harp', player.inventory)
            self.assertNotIn('WISE_MAN', game.current_map.characters)
            self.take((6, 5))
            self.assertIn('Staff of Rain', player.inventory)

        with self.step("7 (SEARCH for Erdrick's Token)"):
            self.travel_to('Alefgard', (119, 91))
            self.search((120, 91))
            self.assertIn("Erdrick's Token", player.inventory)
            self.assertIn("Erdrick discovers the Erdrick's Token.", self.shown_text)

        with self.step("8 (trade for the Rainbow Drop at the shrine)"):
            self.walk_onto((116, 116))
            self.assertEqual(self.where, ('MagicTemple', (6, 2)))
            self.talk((7, 5), RIGHT)
            self.assertIn('Rainbow Drop', player.inventory)
            self.assertNotIn('Stones of Sunlight', player.inventory)
            self.assertNotIn('Staff of Rain', player.inventory)
            self.assertIn("Erdrick's Token", player.inventory)

        with self.step("9 (rescue Princess Gwaelin and bring her home; done before the Dragonlord, as afterwards "
                       "every NPC only cheers)"):
            self.travel_to('Alefgard', (51, 111))
            self.walk_onto((51, 112))
            self.assertEqual(self.where, ('SwampCave', (6, 4)))
            self.open_door((27, 9), UP)
            self.assertEqual(self.tile((26, 9)), 'BRICK')
            self.talk((25, 9), UP)
            self.assertTrue(carrying_gwaelin(game))
            self.assertNotIn('PRINCESS_GWAELIN', game.current_map.characters)
            self.travel_to('TantegelThroneRoom', (10, 13), facing=UP)
            self.cmd_menu.set_king_lorik_dialog(left_throne_room=True)  # as the throne room does every frame
            self.talk((10, 13), UP)
            self.assertTrue(gwaelin_returned(game))
            self.assertFalse(carrying_gwaelin(game))
            self.assertIn("Gwaelin's Love", player.inventory)
            self.assertEqual(game.current_map.characters['PRINCESS_GWAELIN']['coordinates'],
                             GWAELIN_THRONE_ROOM_COORDINATES)

        with self.step("10 (use the Rainbow Drop to build the bridge)"):
            self.travel_to('Alefgard', RAINBOW_DROP_COORDINATES)
            self.assertEqual(self.tile(RAINBOW_BRIDGE_COORDINATES), 'WATER')
            self.cmd_menu.rainbow_drop()
            self.assertTrue(rainbow_bridge_built(game))
            self.assertEqual(self.tile(RAINBOW_BRIDGE_COORDINATES), 'BRIDGE')
            self.assertFalse(game.is_impassable('BRIDGE'))
            # The bridge stays after leaving the overworld and coming back (NES ChkRnbwBrdg)
            self.travel_to('Brecconary', (23, 10))
            self.travel_to('Alefgard', (55, 57))
            self.assertEqual(self.tile(RAINBOW_BRIDGE_COORDINATES), 'BRIDGE')

        with self.step("11 (cross to Charlock and SEARCH behind the throne)"):
            self.walk_onto((55, 56))
            self.assertEqual(self.where, ('CharlockB1', (25, 17)))
            self.search(CharlockB1.THRONE_COORDINATES)
            self.assertIn("Feel the wind blowing from behind the throne.", self.shown_text)
            self.search(CharlockB1.HIDDEN_STAIRCASE_COORDINATES)
            self.assertTrue(charlock_stairs_revealed(game))
            self.assertEqual(self.tile(CharlockB1.HIDDEN_STAIRCASE_COORDINATES), 'BRICK_STAIR_DOWN')

        with self.step("12 (go down to the Dragonlord and refuse his offer)"):
            for stairs, arrival in ((CharlockB1.HIDDEN_STAIRCASE_COORDINATES, ('CharlockB2', (3, 12))),
                                    ((22, 11), ('CharlockB3', (3, 8))),
                                    ((3, 6), ('CharlockB4', (3, 10))),
                                    ((9, 4), ('CharlockB5', (12, 3))),
                                    ((5, 5), ('CharlockB6', (3, 12))),
                                    ((3, 3), ('CharlockB7Wide', (5, 3))),
                                    ((5, 12), ('CharlockB8', (33, 16)))):
                self.take_stairs(stairs)
                self.assertEqual(self.where, arrival)
            self.assertIn('DRAGONLORD', game.current_map.characters)
            self.talk((28, 23), LEFT)  # NES DLBFStatTbl: he sits at BF(16,24); this is the tile to his right
            self.assertIn("What sayest thou?\nWill the great warrior stand with me?", self.prompts)
            self.assertIn("Thou art a fool!", self.shown_text)
            self.assertEqual(game.battle_ctrl.pending_scripted_battle, 'Dragonlord')

        with self.step("13 (defeat both of the Dragonlord's forms)"):
            with patch.object(game.battle_ctrl, 'handle_battle_prompts', side_effect=self.fight_to_the_end):
                game.handle_battles()  # the next frame starts the queued fight
            self.settle()
            self.assertEqual(self.enemies_fought, ['Dragonlord', 'Dragonlord 2'])
            self.assertTrue(dragonlord_defeated(game))
            self.assertIn("Thou hast found the Ball of Light.", self.shown_text)
            self.assertEqual(self.where, ('Alefgard', (55, 56)))

        with self.step("14 (walk back to King Lorik and roll the credits)"):
            self.walk_onto((50, 51))
            self.assertEqual(self.where, ('TantegelCourtyard', (36, 18)))
            self.assertEqual(game.current_map.characters['KING_LORIK']['coordinates'], (14, 18))
            self.stand_at(ENDING_TRIGGER_COORDINATES[0], UP)
            credit_screens = []
            with patch.object(game.ending, 'show_credit_screen', side_effect=credit_screens.append), \
                    patch('src.ending.fade'), \
                    patch('src.ending.event.get', return_value=[pygame.event.Event(pygame.QUIT)]), \
                    patch('src.ending.pygame_quit'), \
                    self.assertRaises(SystemExit):  # the game waits on THE END until it's closed
                game.ending.check_for_end_game_trigger()
            self.assertIn("The legends have proven true.", ''.join(self.shown_text))
            self.assertIn("May I travel as thy companion?", self.prompts)
            self.assertTrue(carrying_gwaelin(game))
            self.assertEqual(credit_screens, list(CREDITS))
            self.assertEqual(credit_screens[-1], ((13, 12, "THE END"),))
