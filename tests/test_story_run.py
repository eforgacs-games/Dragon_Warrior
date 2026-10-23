"""
A headless run through the whole story, in NES order, from the throne room to the credits.

Each step calls what the player's commands would (TAKE, DOOR, STAIRS, SEARCH, TALK, ITEM, the overworld entrances and
the scripted Dragonlord fight) on a real Game, and checks the story state afterwards. Walking isn't what's being tested,
so the hero is put straight onto the tile each command is used from. Only what can't run headless is replaced: drawing,
the blocking text and yes/no windows (each prompt is answered by STORY_ANSWERS), long pauses, and the battle menu,
where every enemy simply loses all its HP so the real victory and ending code runs.

If a step breaks, the failure names it, e.g. "Story step 10 (use the Rainbow Drop to build the bridge) failed".

A second run leaves Gwaelin in the Swamp Cave until the Dragonlord is dead, then carries her to King Lorik, which the
NES allows: she's a map block there, not an NPC, so the victory dialog doesn't replace her rescue (DoTalkResults).
"""
from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.constants import ENDING_GWAELIN_BESIDE_KING, ENDING_GWAELIN_STAIRS, ENDING_TRIGGER_COORDINATES, \
    GWAELIN_THRONE_ROOM_COORDINATES, RAINBOW_BRIDGE_COORDINATES, RAINBOW_DROP_COORDINATES
from src.direction import Direction
from src.ending import CREDITS
from src.game_functions import set_character_position
from src.guardians import AXE_KNIGHT, GOLEM, GREEN_DRAGON
from src.maps import CharlockB1, map_lookup
from src.maps_functions import get_center_point
from src.menu import CommandMenu
from tests.helpers import new_game

UP, DOWN, LEFT, RIGHT = Direction.UP.value, Direction.DOWN.value, Direction.LEFT.value, Direction.RIGHT.value

# How each yes/no window on the way is answered (True = YES). "Dost thou wish to purchase more?" at the key shop is
# answered by StoryRunMixin.answer.
STORY_ANSWERS = {
    "Magic keys! They will unlock any door.\nDost thou wish to purchase one for 85 GOLD?": True,
    "Will thou take me to the castle?": True,
    "Will thou tell me now of thy deeds so they won't be forgotten?": False,  # saving isn't part of this run
    "Dost thou wish to continue thy quest?": True,
    "What sayest thou?\nWill the great warrior stand with me?": False,
    "May I travel as thy companion?": True,
}


# Story flags, read in one place

def rainbow_bridge_built(game) -> bool:
    return game.story_flags.rainbow_bridge_built


def charlock_stairs_revealed(game) -> bool:
    return game.story_flags.charlock_stairs_revealed


def carrying_gwaelin(game) -> bool:
    return game.story_flags.carrying_gwaelin


def gwaelin_returned(game) -> bool:
    return game.story_flags.gwaelin_returned


def dragonlord_defeated(game) -> bool:
    return game.story_flags.dragonlord_defeated


class StoryRunMixin:
    """The setup, stand-ins and story steps of the headless run, without any tests, so the classes that reuse them
    (here and in test_checkpoints.py) don't inherit, and rerun, each other's tests. Mix in before TestCase."""

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
        self.game = new_game()
        self.player = self.game.player
        self.player.name = "Erdrick"
        self.shown_text: list = []
        self.prompts: list = []
        self.enemies_fought: list = []
        for target, kwargs in (
                # The text and yes/no windows wait for a key press
                ((CommandMenu, 'show_text_line_in_dialog_box'), {'autospec': True, 'side_effect': self.read_text}),
                ((CommandMenu, 'wait_for_button'), {}),
                (('data.text.dialog_lookup_table.confirmation_prompt',), {'side_effect': self.answer}),
                (('src.ending.confirmation_prompt',), {'side_effect': self.answer}),
                # Drawing, music and pauses
                ((CommandMenu, 'window_drop_down_effect'), {}),
                ((CommandMenu, 'window_drop_up_effect'), {}),
                (('data.text.dialog_lookup_table.time.wait',), {}),
                (('src.music_player.mixer',), {}),
                # The hero always gets the first turn (no CheckEnRun / CalcWhoIsNext roll, #232), so the scripted
                # fights can't go wrong
                (('src.battle_controller.BattleController.start_fight',), {'return_value': False}),
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

    def fight_guardian(self, guardian):
        """Step onto a guardian's tile from the tile before it, which starts its fixed fight (NES MovementUpdates),
        and win it. Returns the enemies fought."""
        fought = []

        def win(run_away, current_battle):
            fought.append(current_battle.enemy.name)
            return self.fight_to_the_end(run_away, current_battle)
        self.stand_at(guardian.escape_coordinates)
        self.stand_at(guardian.coordinates)
        self.game.count_step()  # the end of the step, as move_player counts it
        with patch.object(self.game.battle_ctrl, 'handle_battle_prompts', side_effect=win):
            self.game.handle_battles()  # the queued fight starts this same frame
        self.settle()
        self.enemies_fought.clear()  # only the Dragonlord's fight is checked against this list
        return fought

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

    # The story, a few steps at a time

    def take_the_throne_room_chests(self):
        player = self.player
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

    def get_keys_and_the_stones_of_sunlight(self):
        player = self.player
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

    def get_the_rainbow_drop(self):
        game, player = self.game, self.player
        with self.step("5 (get the Silver Harp in Garin's Grave)"):
            self.walk_onto((9, 10))
            self.assertEqual(self.where, ('Garinham', (15, 9)))
            for stairs, arrival in (((1, 28), ('GarinsGraveB1', (12, 7))),
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
            self.assertEqual(self.where, ('Garinham', (1, 28)))

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

    def beat_the_golem(self):
        game = self.game
        with self.step("8a (beat the Golem guarding Cantlin)"):
            self.travel_to('Alefgard', GOLEM.escape_coordinates)
            self.assertEqual(self.fight_guardian(GOLEM), ['Golem'])
            self.assertTrue(game.story_flags.golem_defeated)
            self.walk_onto((109, 81))  # Cantlin's gate, just past him
            self.assertEqual(self.where, ('Cantlin', (8, 16)))

    def rescue_gwaelin(self, name):
        game = self.game
        with self.step(f"{name} (rescue Princess Gwaelin from the Swamp Cave)"):
            self.travel_to('Alefgard', (51, 111))
            self.walk_onto((51, 112))
            self.assertEqual(self.where, ('SwampCave', (6, 4)))
            if game.story_flags.dragonlord_defeated:
                # NES CheckForTriggers: with the Dragonlord dead, no guardian fights any more
                self.assertEqual(self.fight_guardian(GREEN_DRAGON), [])
            else:
                self.assertEqual(self.fight_guardian(GREEN_DRAGON), ['Green Dragon'])
                self.assertTrue(game.story_flags.green_dragon_defeated)
            self.open_door((27, 9), UP)
            self.assertEqual(self.tile((26, 9)), 'BRICK')
            self.talk((25, 9), UP)
            self.assertIn("Will thou take me to the castle?", self.prompts)
            self.assertTrue(carrying_gwaelin(game))
            self.assertNotIn('PRINCESS_GWAELIN', game.current_map.characters)

    def bring_gwaelin_home(self):
        game, player = self.game, self.player
        with self.step("9b (bring Princess Gwaelin home to King Lorik)"):
            self.travel_to('TantegelThroneRoom', (10, 13), facing=UP)
            self.cmd_menu.set_king_lorik_dialog(left_throne_room=True)  # as the throne room does every frame
            self.talk((10, 13), UP)
            self.assertTrue(gwaelin_returned(game))
            self.assertFalse(carrying_gwaelin(game))
            self.assertIn("Gwaelin's Love", player.inventory)
            self.assertEqual(game.current_map.characters['PRINCESS_GWAELIN']['coordinates'],
                             GWAELIN_THRONE_ROOM_COORDINATES)

    def defeat_the_dragonlord(self):
        game = self.game
        with self.step("10 (use the Rainbow Drop to build the bridge)"):
            self.travel_to('Alefgard', RAINBOW_DROP_COORDINATES)
            self.assertEqual(self.tile(RAINBOW_BRIDGE_COORDINATES), 'WATER')
            self.cmd_menu.rainbow_drop()
            self.assertTrue(rainbow_bridge_built(game))
            self.assertEqual(self.tile(RAINBOW_BRIDGE_COORDINATES), 'BRIDGE')
            self.assertFalse(game.movement.is_impassable('BRIDGE'))
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
            # The hero always gets the first turn (no CheckEnRun / CalcWhoIsNext ambush), so the fight can't go wrong
            with patch.object(game.battle_ctrl, 'handle_battle_prompts', side_effect=self.fight_to_the_end), \
                    patch.object(game.battle_ctrl, 'start_fight', return_value=False):
                game.handle_battles()  # the next frame starts the queued fight
            self.settle()
            self.assertEqual(self.enemies_fought, ['Dragonlord', 'Dragonlord 2'])
            self.assertTrue(dragonlord_defeated(game))
            self.assertIn("Thou hast found the Ball of Light.", self.shown_text)
            self.assertEqual(self.where, ('Alefgard', (55, 56)))

    def roll_the_credits(self):
        """Walk back to King Lorik and run the ending. Returns where the ending put Gwaelin down (place_gwaelin) and
        whether she walked over to the king."""
        game = self.game
        with self.step("14 (walk back to King Lorik and roll the credits)"):
            self.travel_to('Alefgard', (50, 52))
            self.walk_onto((50, 51))
            self.assertEqual(self.where, ('TantegelCourtyard', (36, 18)))
            self.assertEqual(game.current_map.characters['KING_LORIK']['coordinates'], (14, 18))
            self.stand_at(ENDING_TRIGGER_COORDINATES[0], UP)
            credit_screens = []
            with patch.object(game.ending, 'show_credit_screen', side_effect=credit_screens.append), \
                    patch.object(game.ending, 'place_gwaelin', wraps=game.ending.place_gwaelin) as place_gwaelin, \
                    patch.object(game.ending, 'walk_gwaelin_to_king',
                                 wraps=game.ending.walk_gwaelin_to_king) as walk_gwaelin_to_king, \
                    patch('src.ending.screen_fade'), \
                    patch('src.ending.event.get', return_value=[pygame.event.Event(pygame.QUIT)]), \
                    patch('src.ending.pygame_quit'), \
                    self.assertRaises(SystemExit):  # the game waits on THE END until it's closed
                game.ending.check_for_end_game_trigger()
            self.assertIn("The legends have proven true.", ''.join(self.shown_text))
            self.assertIn("Please, wait.", ''.join(self.shown_text))
            self.assertIn("May I travel as thy companion?", self.prompts)
            self.assertTrue(carrying_gwaelin(game))
            self.assertEqual(credit_screens, list(CREDITS))
            self.assertEqual(credit_screens[-1], ((13, 12, "THE END"),))
        return [call.args for call in place_gwaelin.call_args_list], walk_gwaelin_to_king.called


class TestStoryRun(StoryRunMixin, TestCase):

    def test_the_game_can_be_finished(self):
        self.take_the_throne_room_chests()
        self.get_keys_and_the_stones_of_sunlight()
        self.get_the_rainbow_drop()
        self.beat_the_golem()
        self.rescue_gwaelin("9a")
        self.bring_gwaelin_home()
        self.defeat_the_dragonlord()
        gwaelin_put_down_at, gwaelin_walked = self.roll_the_credits()
        # NES EndGameTriggered: the returned Gwaelin comes down the throne room stairs and walks to the king
        self.assertEqual(gwaelin_put_down_at, [ENDING_GWAELIN_STAIRS])
        self.assertTrue(gwaelin_walked)

    def test_the_game_can_be_finished_rescuing_gwaelin_after_the_dragonlord(self):
        """NES DoTalkResults: Gwaelin is a map block, not an NPC, so the victory dialog (LD134) doesn't replace her
        rescue, and the hero can carry her to King Lorik for the ending (ChkCarryGwaelin)."""
        self.take_the_throne_room_chests()
        self.get_keys_and_the_stones_of_sunlight()
        self.get_the_rainbow_drop()
        self.beat_the_golem()
        self.defeat_the_dragonlord()
        self.rescue_gwaelin("13b")
        self.assertNotIn("Thou hast brought us peace, again.", self.shown_text)
        gwaelin_put_down_at, gwaelin_walked = self.roll_the_credits()
        # NES ChkCarryGwaelin: the hero sets her down beside the king
        self.assertFalse(gwaelin_returned(self.game))
        self.assertEqual(gwaelin_put_down_at, [ENDING_GWAELIN_BESIDE_KING])
        self.assertFalse(gwaelin_walked)

    def test_erdricks_armor_is_guarded_by_the_axe_knight(self):
        """Erdrick's Armor isn't needed to finish the game, so it isn't part of the run above."""
        self.travel_to('Hauksness', AXE_KNIGHT.escape_coordinates)
        self.assertEqual(self.fight_guardian(AXE_KNIGHT), ['Axe Knight'])
        self.search(AXE_KNIGHT.coordinates)
        self.assertEqual(self.player.armor, "Erdrick's Armor")
        self.assertIn("Erdrick discovers the Erdrick's Armor.", self.shown_text)
        # NES CheckAxeKnight has no story flag: he's back on every step onto the tile
        self.assertEqual(self.fight_guardian(AXE_KNIGHT), ['Axe Knight'])
