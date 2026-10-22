import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from data.text.dialog_lookup_table import DialogLookup
from src.config.test_config import test_config
from src.constants import GWAELIN_THRONE_ROOM_COORDINATES
from src.direction import Direction
from src.game import Game
from src.maps import TantegelCellar, TantegelCourtyard, TantegelThroneRoom
from tests.test_shop_dialog import npc_identifiers

# NES Bank00 NPC tables: (graphic, X, Y, dialog byte, mobile, facing). The fighter is SOLDIER here; the trumpet guards
# and the two "wizards" of TaDLStatTbl get guard sprites on the ground floor (NES GetGuardType), so they're GUARD.
DOWN, UP, LEFT, RIGHT = Direction.DOWN, Direction.UP, Direction.LEFT, Direction.RIGHT

# ThRmMobTbl and ThRmStatTbl, without Gwaelin ($6F), who is only there once she's been returned. NES X,Y is
# (Y + 6, X + 10).
THRONE_ROOM_NPCS = (
    ('GUARD', 7, 5, 0x65, True, DOWN),
    ('KING_LORIK', 3, 3, 0x6E, False, DOWN),
    ('GUARD', 3, 6, 0x23, False, RIGHT),
    ('GUARD', 5, 6, 0x24, False, LEFT),
)

# TantMobTbl and TantStatTbl. NES X,Y is (Y + 7, X + 7).
COURTYARD_NPCS = (
    ('WOMAN', 8, 13, 0x62, True, DOWN),
    ('GUARD', 19, 2, 0x17, True, DOWN),
    ('MAN', 11, 11, 0x1C, True, DOWN),
    ('WISE_MAN', 17, 11, 0x1D, True, DOWN),
    ('MERCHANT', 4, 21, 0x1F, True, DOWN),
    ('SOLDIER', 25, 11, 0x16, True, DOWN),
    ('GUARD', 18, 18, 0x72, True, DOWN),
    ('GUARD', 2, 12, 0x1B, True, DOWN),
    ('MERCHANT', 6, 25, 0x20, True, DOWN),
    ('SOLDIER', 24, 21, 0x22, True, DOWN),
    ('MERCHANT', 24, 1, 0x0E, False, DOWN),
    ('WOMAN', 27, 5, 0x1A, False, DOWN),
    ('GUARD', 8, 6, 0x19, False, DOWN),
    ('MAN', 2, 8, 0x18, False, DOWN),
    ('GUARD', 8, 8, 0x71, False, UP),
    ('GUARD', 26, 15, 0x1E, False, UP),
    ('GUARD', 15, 20, 0x63, False, RIGHT),
    ('WISE_MAN', 20, 26, 0x6A, False, LEFT),
    ('GUARD', 9, 27, 0x21, False, RIGHT),
    ('GUARD', 12, 27, 0x21, False, LEFT),
)

# TaDLMobTbl and TaDLStatTbl, after the Dragonlord's defeat
COURTYARD_AFTER_DRAGONLORD_NPCS = (
    ('GUARD', 19, 2, True), ('MAN', 14, 23, True), ('SOLDIER', 25, 11, True), ('GUARD', 18, 18, True),
    ('GUARD', 2, 12, True), ('MERCHANT', 6, 25, True), ('SOLDIER', 24, 21, True),
    ('KING_LORIK', 11, 7, False), ('GUARD', 9, 9, False), ('GUARD', 9, 11, False), ('GUARD', 9, 13, False),
    ('GUARD', 12, 9, False), ('GUARD', 12, 11, False), ('GUARD', 12, 13, False), ('GUARD', 9, 27, False),
    ('GUARD', 12, 27, False),
)

# TaSLStatTbl (TaSLMobTbl is empty). NES X,Y is (Y + 1, X + 1).
CELLAR_NPCS = (
    ('WISE_MAN', 4, 6, 0x66, False, DOWN),
)

# Bank02 text for the dialog bytes between $16 and $5D (TextBlock entry = byte + $2F), and GuardDialog1/2
COURTYARD_TEXT = {
    0x16: "I am looking for the castle cellar.\nI heard it is not easily found.",
    0x17: "Thou must have a key to open a door.",
    0x18: "To become strong enough to face future trials thou must first battle many foes.",
    0x19: ("King Lorik will record thy deeds in his Imperial Scroll so thou may return to thy quest later.",),
    0x1A: ("When the sun and rain meet, a Rainbow Bridge shall appear.", "It's a legend."),
    0x1B: "Never does a brave person steal.",
    0x1C: "There was a time when Brecconary was a paradise.\nThen the Dragonlord's minions came.",
    0x1D: ("Let us wish the warrior well!", "May the light be thy strength!"),
    0x1E: "If thy Hit Points are high enough, by all means, enter.",
    0x1F: "We are merchants who have traveled much in this land. Many of our colleagues have been killed by servants "
          "of the Dragonlord.",
    0x20: "Rumor has it that entire towns have been destroyed by the Dragonlord's servants.",
    0x21: "Welcome to Tantegel Castle.",
    0x22: "In Garinham,look for the grave of Garin.\nThou must push on a wall of darkness there.",
    0x71: "If thou art planning to take a rest, first see King Lorik.",
    0x72: "When entering the cave, take with thee a torch.",
}

EAST_OF_THIS_CASTLE = ["East of this castle is a town where armor, weapons, and many other items may be purchased.",
                       "Return to the Inn for a rest if thou art wounded in battle, Edward.",
                       "Sleep heals all."]
TREASURE_CHESTS_KEY = ["If thou hast collected all the Treasure Chests, a key will be found.",
                       "Once used, the key will disappear, but the door will be open and thou may pass through."]
STRONG_ENOUGH = "Thou art strong enough!\nWhy can thou not defeat the Dragonlord?"


def throne_room_coordinates(x, y):
    return y + 6, x + 10


def courtyard_coordinates(x, y):
    return y + 7, x + 7


def cellar_coordinates(x, y):
    return y + 1, x + 1


class TestTantegelDialog(TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
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
        self.game.player.name = 'Edward'
        self.dialog_lookup = DialogLookup(self.game.cmd_menu, test_config)  # with the hero's name
        self.throne_room = TantegelThroneRoom(test_config)
        self.courtyard = TantegelCourtyard(test_config)
        self.cellar = TantegelCellar(test_config)
        self.lines = []
        self.dialog_lookup.command_menu.show_line_in_dialog_box = lambda line, **kwargs: self.lines.append(line)

    def maps(self):
        return ((self.throne_room, THRONE_ROOM_NPCS, throne_room_coordinates),
                (self.courtyard, COURTYARD_NPCS, courtyard_coordinates),
                (self.cellar, CELLAR_NPCS, cellar_coordinates))

    def dialog(self, game_map, to_map, x, y):
        identifier = npc_identifiers(game_map)[to_map(x, y)]
        return self.dialog_lookup.lookup_table[game_map.identifier][identifier]['dialog']

    def test_every_nes_npc_is_on_the_map(self):
        for game_map, npcs, to_map in self.maps():
            with self.subTest(game_map.identifier):
                expected = {to_map(x, y): graphic for graphic, x, y, *_ in npcs}
                self.assertEqual(game_map.npc_coordinates, expected)

    def test_gwaelin_on_the_throne(self):
        # ThRmStatTbl: Princess Gwaelin at 6,3 ($6F), placed once F_RTN_GWAELIN is set
        self.assertEqual(GWAELIN_THRONE_ROOM_COORDINATES, throne_room_coordinates(6, 3))

    def test_npcs_after_the_dragonlord(self):
        self.courtyard.apply_dragonlord_defeated()
        expected = {courtyard_coordinates(x, y): graphic for graphic, x, y, _ in COURTYARD_AFTER_DRAGONLORD_NPCS}
        self.assertEqual(self.courtyard.npc_coordinates, expected)
        identifiers = npc_identifiers(self.courtyard)
        roaming = {identifiers[courtyard_coordinates(x, y)] for _, x, y, mobile in COURTYARD_AFTER_DRAGONLORD_NPCS
                   if mobile}
        self.assertEqual(set(self.courtyard.roaming_character_list), roaming)

    def test_every_npc_has_dialog(self):
        for game_map, _, _ in self.maps():
            with self.subTest(game_map.identifier):
                identifiers = set(npc_identifiers(game_map).values())
                if game_map is self.throne_room:
                    identifiers.add('PRINCESS_GWAELIN')
                self.assertEqual(identifiers, set(self.dialog_lookup.lookup_table[game_map.identifier]))

    def test_mobile_npcs_roam(self):
        for game_map, npcs, to_map in self.maps():
            with self.subTest(game_map.identifier):
                identifiers = npc_identifiers(game_map)
                roaming = {identifiers[to_map(x, y)] for _, x, y, _, mobile, _ in npcs if mobile}
                self.assertEqual(set(game_map.roaming_character_list), roaming)

    def test_npc_directions(self):
        for game_map, npcs, to_map in self.maps():
            game_map.load_map(self.game.player, None, test_config['TILE_SIZE'])
            identifiers = npc_identifiers(game_map)
            for _, x, y, _, _, facing in npcs:
                identifier = identifiers[to_map(x, y)]
                with self.subTest(f'{game_map.identifier} {identifier}'):
                    self.assertEqual(game_map.characters[identifier]['character'].direction_value, facing.value)

    def test_courtyard_text_matches_nes(self):
        for _, x, y, dialog_byte, _, _ in COURTYARD_NPCS:
            if dialog_byte in COURTYARD_TEXT:
                self.assertEqual(self.dialog(self.courtyard, courtyard_coordinates, x, y), COURTYARD_TEXT[dialog_byte],
                                 f'NES {x},{y} ${dialog_byte:02X}')

    def test_key_shop(self):
        # NES KeysDialog: dialog byte $0E is KeyCostTbl entry 2, 85 GOLD
        entry, = self.dialog(self.courtyard, courtyard_coordinates, 24, 1)
        self.assertEqual(entry.func.__name__, 'check_buy_magic_keys')
        self.assertEqual(entry.args, (85,))

    def test_mp_restoring_wizard(self):
        # NES ChkMagicDialog ($6A): TextBlock11 entry 13, then MP is maxed out
        self.assertEqual(self.dialog(self.courtyard, courtyard_coordinates, 20, 26), (
            "Edward's coming was foretold by legend. May the light shine upon this brave warrior.",
            self.dialog_lookup.flash_and_restore_mp))

    def test_gwaelin_npcs(self):
        # NES ChkPrncsDialog1 ($62) and ChkPrncsDialog2 ($63)
        for x, y in ((8, 13), (15, 20)):
            entry, = self.dialog(self.courtyard, courtyard_coordinates, x, y)
            self.assertEqual(entry.func, self.dialog_lookup.dialog_once_gwaelin_rescued)
        roaming_guard, = self.dialog(self.throne_room, throne_room_coordinates, 7, 5)
        self.assertEqual(roaming_guard, self.dialog_lookup.tantegel_throne_room_roaming_guard)

    def throne_room_guard_lines(self, x, y, left_throne_room):
        self.game.story_flags.left_throne_room = left_throne_room
        self.lines.clear()
        entry, = self.dialog(self.throne_room, throne_room_coordinates, x, y)
        entry()
        return self.lines

    def test_throne_room_guards_before_leaving_the_throne_room(self):
        # NES RegularDialog: TextBlock17 entries 1 and 0 until F_LEFT_THROOM is set
        self.assertEqual(self.throne_room_guard_lines(3, 6, False), EAST_OF_THIS_CASTLE)
        self.assertEqual(self.throne_room_guard_lines(5, 6, False), TREASURE_CHESTS_KEY)

    def test_throne_room_guards_after_leaving_the_throne_room(self):
        # NES DoVariousDialog1: $23 + $2F and $24 + $2F, TextBlock6 entries 2 and 3
        self.assertEqual(self.throne_room_guard_lines(3, 6, True),
                         ["A word of advice.", "Save thy money for more expensive armor."])
        self.assertEqual(self.throne_room_guard_lines(5, 6, True),
                         ["Listen to what people say.\nIt can be of great help."])

    def test_cellar_wizard(self):
        self.assertEqual(self.dialog(self.cellar, cellar_coordinates, 4, 6),
                         (self.dialog_lookup.tantegel_cellar_stones_of_sunlight_guardian,))

    def king_lorik(self, level):
        self.game.player.level = level
        self.game.player.points_to_next_level = self.game.player.get_points_to_next_level()
        return DialogLookup(self.game.cmd_menu, test_config).lookup_table['TantegelThroneRoom']['KING_LORIK']

    def test_king_below_level_30(self):
        king_lorik = self.king_lorik(29)
        points = self.game.player.points_to_next_level
        experience_line = f"Before reaching thy next level of experience thou must gain {points} Points."
        self.assertEqual(king_lorik['returned_dialog'][1], experience_line)
        self.assertEqual(king_lorik['load_from_save_dialog'][1:3],
                         (experience_line, "See me again when thy level has increased."))
        self.assertEqual(king_lorik['post_death_dialog'][2],
                         f"To reach the next level, thy Experience Points must increase by {points}.")

    def test_king_at_level_30(self):
        # NES LeftThRoom (LD41F), MainGameEngine (LCA27) and KingDeathDialog (LEDF6) all check for LVL_30
        king_lorik = self.king_lorik(30)
        self.assertEqual(king_lorik['returned_dialog'][:2],
                         ("I am greatly pleased that thou hast returned, Edward.", STRONG_ENOUGH))
        self.assertEqual(king_lorik['returned_dialog'][2].__name__, 'prompt_for_save')  # then SaveDialog
        self.assertEqual(king_lorik['load_from_save_dialog'], (
            "I am glad thou hast returned.\nAll our hopes are riding on thee.",
            STRONG_ENOUGH,
            "Goodbye now, Edward.\n'Take care and tempt not the Fates."))
        self.assertEqual(king_lorik['post_death_dialog'], (
            "Death should not have taken thee, Edward.",
            "I will give thee another chance.",
            "Now, go, Edward!"))

    def test_after_the_dragonlord_everyone_says_king_lorik_awaits(self):
        # NES LD134: TextBlock19 entry 1 for every NPC on the ground floor
        self.courtyard.apply_dragonlord_defeated()
        for identifier in npc_identifiers(self.courtyard).values():
            self.assertEqual(self.game.ending.npc_dialog(identifier, self.courtyard), "Come now, King Lorik awaits.")
