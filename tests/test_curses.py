import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import KEYDOWN, K_RETURN, event

from src.config.test_config import test_config
from src.constants import TANTEGEL_CURSED_ROW
from src.direction import Direction
from src.game import Game
from src.maps import map_lookup

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class TestCurses(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        cls.screen = pygame.display.set_mode((800, 600))

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
        self.player.name = "Edward"

    # helpers

    def use(self, item_function):
        with patch('src.menu.CommandMenu.show_text_in_dialog_box') as show_text, \
                patch.object(self.game.music_player, 'play_until_end') as play_until_end:
            getattr(self.game.cmd_menu, item_function)()
        return [c.args[0] for c in show_text.call_args_list], [c.args[0] for c in play_until_end.call_args_list]

    def go_to(self, map_name, coordinates):
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates)

    def where(self):
        tile_size = self.game.tile_size
        rect = self.player.rect
        return self.game.current_map.identifier, (rect.y // tile_size, rect.x // tile_size)

    def talk_to_curse_remover(self):
        dialog = self.game.cmd_menu.dialog_lookup.lookup_table['Brecconary']['WISE_MAN']['dialog']
        with patch('src.menu.CommandMenu.show_text_line_in_dialog_box') as show_line:
            self.game.cmd_menu.show_text_in_dialog_box(dialog, add_quotes=True, skip_text=True)
        return [c.args[0] for c in show_line.call_args_list]

    # player state

    def test_not_cursed_by_default(self):
        self.assertFalse(self.player.is_cursed)
        self.assertFalse(self.player.is_wearing_cursed_item("Cursed Belt"))
        self.assertFalse(self.player.is_wearing_cursed_item("Death Necklace"))

    def test_either_item_curses(self):
        self.player.wearing_cursed_belt = True
        self.assertTrue(self.player.is_cursed)
        self.player.wearing_cursed_belt = False
        self.player.wearing_death_necklace = True
        self.assertTrue(self.player.is_cursed)

    # using the items

    def test_cursed_belt_puts_it_on_and_curses(self):
        self.player.inventory = ["Cursed Belt"]
        lines, sounds = self.use('cursed_belt')
        self.assertEqual(lines, ["Edward put on the Cursed Belt and was cursed!\nThy body is being squeezed."])
        self.assertIn(self.game.directories.cursed_music, sounds)
        self.assertTrue(self.player.wearing_cursed_belt)
        self.assertTrue(self.player.is_cursed)
        # NES WearCursedItem doesn't use the item up
        self.assertEqual(self.player.inventory, ["Cursed Belt"])

        lines, sounds = self.use('cursed_belt')
        self.assertEqual(lines, ["The Cursed Belt is squeezing thy body."])
        self.assertIn(self.game.directories.cursed_music, sounds)

    def test_death_necklace_puts_it_on_and_curses(self):
        self.player.inventory = ["Death Necklace"]
        lines, _ = self.use('death_necklace')
        self.assertEqual(lines, ["Edward put on the Death Necklace and was cursed!\nThy body is being squeezed."])
        self.assertTrue(self.player.wearing_death_necklace)
        self.assertFalse(self.player.wearing_cursed_belt)
        self.assertEqual(self.player.inventory, ["Death Necklace"])
        lines, _ = self.use('death_necklace')
        self.assertEqual(lines, ["The Death Necklace is squeezing thy body."])

    def test_death_necklace_changes_no_stats(self):
        # NES LoadStats never reads the curse flags
        self.player.inventory = ["Death Necklace"]
        before = (self.player.strength, self.player.agility, self.player.max_hp, self.player.max_mp,
                  self.player.attack_power, self.player.defense_power, self.player.current_hp)
        self.use('death_necklace')
        self.player.update_attack_power()
        self.player.update_defense_power()
        after = (self.player.strength, self.player.agility, self.player.max_hp, self.player.max_mp,
                 self.player.attack_power, self.player.defense_power, self.player.current_hp)
        self.assertEqual(before, after)

    def test_item_menu_uses_cursed_items(self):
        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        for item_name, function_name in (("Cursed Belt", 'cursed_belt'), ("Death Necklace", 'death_necklace')):
            with self.subTest(item=item_name):
                self.player.inventory = [item_name]
                with patch.object(event, 'get', return_value=[mocked_return]), \
                        patch.object(self.game.cmd_menu, function_name) as item_function:
                    self.game.cmd_menu.display_item_menu('inventory')
                item_function.assert_called_once()

    # selling and dropping

    def test_worn_cursed_items_cannot_be_parted_with(self):
        self.player.inventory = ["Cursed Belt", "Death Necklace"]
        self.player.wearing_cursed_belt = True
        self.assertTrue(self.player.is_wearing_cursed_item("Cursed Belt"))
        # NES: an unworn cursed item can still be sold or dropped
        self.assertFalse(self.player.is_wearing_cursed_item("Death Necklace"))
        self.player.wearing_death_necklace = True
        self.assertTrue(self.player.is_wearing_cursed_item("Death Necklace"))
        self.assertFalse(self.player.is_wearing_cursed_item("Herb"))

    # removing the curse

    def test_curse_remover_when_not_cursed(self):
        self.player.inventory = ["Cursed Belt"]
        self.assertEqual(self.talk_to_curse_remover(), ["If thou art cursed, come again."])
        self.assertEqual(self.player.inventory, ["Cursed Belt"])

    def test_curse_remover_lifts_the_curse_for_free(self):
        self.player.inventory = ["Herb", "Cursed Belt", "Death Necklace"]
        self.player.wearing_cursed_belt = True
        self.player.wearing_death_necklace = True
        self.player.gold = 100
        self.assertEqual(self.talk_to_curse_remover(), ["I will free thee from thy curse.", "Now, go."])
        self.assertFalse(self.player.is_cursed)
        self.assertEqual(self.player.inventory, ["Herb"])
        self.assertEqual(self.player.gold, 100)

    def test_curse_remover_only_takes_worn_items(self):
        # NES CursedDialog removes an item only if its own curse flag is set
        self.player.inventory = ["Cursed Belt", "Death Necklace"]
        self.player.wearing_death_necklace = True
        self.talk_to_curse_remover()
        self.assertEqual(self.player.inventory, ["Cursed Belt"])
        self.assertFalse(self.player.is_cursed)

    # Tantegel

    def walk_onto(self, map_name, coordinates):
        self.go_to(map_name, coordinates)
        with patch('src.menu.CommandMenu.show_text_in_dialog_box') as show_text:
            self.game.count_step()
        return [c.args[0] for c in show_text.call_args_list]

    def test_cursed_player_is_thrown_out_of_tantegel(self):
        self.player.wearing_cursed_belt = True
        self.assertEqual(self.walk_onto('TantegelCourtyard', (TANTEGEL_CURSED_ROW, 18)), ["Cursed one, be gone!"])
        self.assertEqual(self.where(), ('Alefgard', (50, 51)))

    def test_cursed_player_is_not_thrown_out_after_the_dragonlord_is_dead(self):
        # NES CheckForTriggers skips MovementUpdates (and so CheckTantCursed) once F_DGNLRD_DEAD is set
        self.player.wearing_cursed_belt = True
        self.game.story_flags.dragonlord_defeated = True
        self.assertEqual(self.walk_onto('TantegelCourtyard', (TANTEGEL_CURSED_ROW, 18)), [])
        self.assertEqual(self.where(), ('TantegelCourtyard', (TANTEGEL_CURSED_ROW, 18)))

    def test_cursed_player_can_stand_in_the_gateway(self):
        self.player.wearing_death_necklace = True
        self.assertEqual(self.walk_onto('TantegelCourtyard', (TANTEGEL_CURSED_ROW + 1, 18)), [])
        self.assertEqual(self.where(), ('TantegelCourtyard', (TANTEGEL_CURSED_ROW + 1, 18)))

    def test_uncursed_player_may_enter_tantegel(self):
        self.assertEqual(self.walk_onto('TantegelCourtyard', (TANTEGEL_CURSED_ROW, 18)), [])
        self.assertEqual(self.where(), ('TantegelCourtyard', (TANTEGEL_CURSED_ROW, 18)))

    def test_row_check_only_applies_in_tantegel(self):
        self.player.wearing_cursed_belt = True
        self.assertEqual(self.walk_onto('Brecconary', (TANTEGEL_CURSED_ROW, 13)), [])
        self.assertEqual(self.where()[0], 'Brecconary')

    # death

    def die(self):
        self.player.current_hp = 0
        self.player.gold = 101
        self.game.battle_ctrl.launch_battle = False
        with patch.object(self.game, 'drawer'), patch.object(self.game, 'music_player'), \
                patch('src.game.display'), \
                patch('src.menu.CommandMenu.show_text_in_dialog_box') as show_text:
            self.game.handle_death()
        return [c.args[0] for c in show_text.call_args_list]

    def test_cursed_death_sends_player_outside_with_1_hp(self):
        self.player.wearing_cursed_belt = True
        lines = self.die()
        self.assertEqual(lines, ["Thou art dead.",
                                 ("Thou hast failed and thou art cursed.", "Leave at once!")])
        self.assertEqual(self.where(), ('Alefgard', (50, 51)))
        self.assertEqual(self.player.direction_value, Direction.DOWN.value)
        self.assertEqual(self.player.current_hp, 1)
        self.assertEqual(self.player.gold, 50)
        self.assertFalse(self.player.is_dead)
        self.assertFalse(self.game.game_state.is_post_death_dialog)
        self.assertTrue(self.player.is_cursed)

    def test_uncursed_death_returns_to_the_king(self):
        self.die()
        self.assertEqual(self.game.current_map.identifier, 'TantegelThroneRoom')
        self.assertEqual(self.player.current_hp, self.player.max_hp)
        self.assertTrue(self.game.game_state.is_post_death_dialog)
