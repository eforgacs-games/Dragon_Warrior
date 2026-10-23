from unittest import TestCase
from unittest.mock import patch

from data.text.dialog_lookup_table import DialogLookup
from src.config.test_config import test_config
from src.constants import GWAELIN_THRONE_ROOM_COORDINATES
from src.maps import TantegelCellar, TantegelCourtyard, TantegelThroneRoom
from tests.nes_maps import nes_npcs
from tests.test_shop_dialog import npc_identifiers
from tests.town_dialog import TownDialogMixin

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
    0x1F: "We are merchants who have traveled much in this land.\nMany of our colleagues have been killed by "
          "servants of the Dragonlord.",
    0x20: "Rumor has it that entire towns have been destroyed by the Dragonlord's servants.",
    0x21: "Welcome to Tantegel Castle.",
    0x22: "In Garinham,look for the grave of Garin.\nThou must push on a wall of darkness there.",
    0x71: "If thou art planning to take a rest, first see King Lorik.",
    0x72: "When entering the cave, take with thee a torch.",
}

EAST_OF_THIS_CASTLE = ["East of this castle is a town where armor, weapons, and many other items may be purchased.",
                       "Return to the Inn for a rest if thou art wounded in battle, Edward.",
                       "Sleep heals all."]
TREASURE_CHESTS_KEY = ["If thou hast collected all the Treasure Chests,\na key will be found.",
                       "Once used, the key will disappear, but the door will be open and thou may pass through."]
STRONG_ENOUGH = "Thou art strong enough!\nWhy can thou not defeat the Dragonlord?"


def throne_room_coordinates(x, y):
    return y + 6, x + 10


def courtyard_coordinates(x, y):
    return y + 7, x + 7


def cellar_coordinates(x, y):
    return y + 1, x + 1


class TestThroneRoomNPCs(TownDialogMixin, TestCase):
    map_class = TantegelThroneRoom
    # ThRmStatTbl's Princess Gwaelin ($6F) is only there once she's been returned
    not_on_the_map = frozenset({0x6F})


class TestCellarNPCs(TownDialogMixin, TestCase):
    map_class = TantegelCellar


class TestTantegelDialog(TownDialogMixin, TestCase):
    map_class = TantegelCourtyard
    text = COURTYARD_TEXT

    def setUp(self):
        super().setUp()
        self.game.player.name = 'Edward'
        self.dialog_lookup = DialogLookup(self.game.cmd_menu, test_config)  # with the hero's name
        self.throne_room = TantegelThroneRoom(test_config)
        self.courtyard = self.town
        self.cellar = TantegelCellar(test_config)

    def test_npcs_after_the_dragonlord(self):
        # TaDLMobTbl and TaDLStatTbl
        self.courtyard.apply_dragonlord_defeated()
        expected = {courtyard_coordinates(x, y): sprite for sprite, x, y, *_ in nes_npcs('TantegelCourtyard_DL')}
        self.assertEqual(self.courtyard.npc_coordinates, expected)
        identifiers = npc_identifiers(self.courtyard)
        roaming = [identifiers[courtyard_coordinates(x, y)] for _, x, y, _, mobile, _ in nes_npcs('TantegelCourtyard_DL')
                   if mobile]
        self.assertEqual(self.courtyard.roaming_character_list, roaming)

    def dialog(self, game_map, to_map, x, y):
        identifier = npc_identifiers(game_map)[to_map(x, y)]
        return self.dialog_lookup.lookup_table[game_map.identifier][identifier]['dialog']

    def test_gwaelin_on_the_throne(self):
        # ThRmStatTbl: Princess Gwaelin at 6,3 ($6F), placed once F_RTN_GWAELIN is set
        self.assertEqual(GWAELIN_THRONE_ROOM_COORDINATES, throne_room_coordinates(6, 3))

    def test_key_shop(self):
        # NES KeysDialog: dialog byte $0E is KeyCostTbl entry 2, 85 GOLD
        entry, = self.dialog(self.courtyard, courtyard_coordinates, 24, 1)
        self.assertEqual(entry.func.__name__, 'check_buy_magic_keys')
        self.assertEqual(entry.args, (85,))

    def test_mp_restoring_wizard(self):
        # NES ChkMagicDialog ($6A): TextBlock11 entry 13, then MP is maxed out
        self.assertEqual(self.dialog(self.courtyard, courtyard_coordinates, 20, 26), (
            "Edward's coming was foretold by legend.\nMay the light shine upon this brave warrior.",
            self.dialog_lookup.flash_and_restore_mp))

    def test_mp_restoring_wizard_flashes_black_and_white_then_restores_mp(self):
        # NES ChkMagicDialog (LD2D7): BWScreenFlash, then MagicPoints = DisplayedMaxMP, then Dowindow WND_POPUP
        calls = []
        player = self.dialog_lookup.player
        with patch.object(self.dialog_lookup, 'bw_screen_flash', side_effect=lambda: calls.append('flash')), \
                patch.object(player, 'restore_mp', side_effect=lambda: calls.append('mp')), \
                patch.object(self.dialog_lookup.command_menu, 'show_popup_window',
                             side_effect=lambda: calls.append('window')):
            self.dialog_lookup.flash_and_restore_mp()
        self.assertEqual(['flash', 'mp', 'window'], calls)

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
        self.game.player.level = level  # points_to_next_level follows (a property since #256)
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

    def test_king_with_one_point_left_says_point(self):
        # NES TextBlock13 entry 1 (AMTP) and TextBlock18 entry 2 (PNTS): "Point" when exactly 1 is left
        self.game.player.total_experience = 6  # level 2 is at 7
        king_lorik = self.king_lorik(1)
        experience_line = "Before reaching thy next level of experience thou must gain 1 Point."
        self.assertEqual(king_lorik['returned_dialog'][1], experience_line)
        self.assertEqual(king_lorik['load_from_save_dialog'][1], experience_line)
        self.assertEqual(king_lorik['post_death_dialog'][2],
                         "To reach the next level, thy Experience Point must increase by 1.")

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
