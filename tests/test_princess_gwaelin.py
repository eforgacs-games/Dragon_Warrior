from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.constants import GWAELIN_SWAMP_CAVE_COORDINATES, GWAELIN_THRONE_ROOM_COORDINATES
from src.drawer import set_to_save_prompt
from src.game import Game
from src.maps import map_lookup


class TestPrincessGwaelin(TestCase):
    """Bringing Princess Gwaelin back to Tantegel, per NES DoKingDialog, PrincessDialog and ChkPrncsDialog1-4."""

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
        self.game.player.name = "Edward"
        self.player = self.game.player

    def go_to(self, map_name, coordinates):
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates)

    @property
    def dialog_lookup(self):
        return self.game.cmd_menu.dialog_lookup

    @property
    def king_lorik(self):
        return self.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']

    def carry_princess(self):
        self.game.story_flags.carrying_gwaelin = True

    def spoken_lines(self, function, *args):
        """Run a dialog function and return every line it showed, in order."""
        lines = []

        def record(text, *_args, **_kwargs):
            lines.extend([text] if isinstance(text, str) else [line for line in text if isinstance(line, str)])

        with patch.object(self.game.cmd_menu, 'show_line_in_dialog_box', side_effect=record), \
                patch.object(self.game.cmd_menu, 'show_text_in_dialog_box', side_effect=record):
            function(*args)
        return lines

    # King Lorik

    def test_king_lorik_dialog_when_carrying_princess(self):
        self.go_to('TantegelThroneRoom', (10, 13))
        self.carry_princess()
        # The throne room re-picks the king's dialog every frame once the hero has left it (set_to_save_prompt);
        # carrying Gwaelin must win, as NES DoKingDialog checks F_GOT_GWAELIN first
        set_to_save_prompt(self.game.cmd_menu)
        self.assertIs(self.king_lorik['dialog'], self.king_lorik['carrying_princess_dialog'])
        self.game.cmd_menu.set_king_lorik_dialog()
        self.assertIs(self.king_lorik['dialog'], self.king_lorik['carrying_princess_dialog'])

    def test_king_lorik_dialog_after_gwaelin_returned(self):
        self.go_to('TantegelThroneRoom', (10, 13))
        self.game.story_flags.gwaelin_returned = True
        set_to_save_prompt(self.game.cmd_menu)
        self.assertIs(self.king_lorik['dialog'], self.king_lorik['returned_dialog'])
        self.game.cmd_menu.set_king_lorik_dialog()
        self.assertIs(self.king_lorik['dialog'], self.king_lorik['post_initial_dialog'])

    def test_carrying_princess_dialog_matches_nes(self):
        self.go_to('TantegelThroneRoom', (10, 13))  # rebuilds the dialog with the hero's name
        dialog_lookup = self.dialog_lookup
        self.assertEqual((
            "Forever shall I be grateful for the gift of my daughter returned to her home, Edward.\n"
            "Accept my thanks.",
            "Now, Gwaelin, come to my side.",
            dialog_lookup.princess_whispers,
            "Please accept my love, Edward.",
            dialog_lookup.receive_gwaelins_love,
            dialog_lookup.even_when_we_two_are_parted,
            "Farewell, Edward.",
            dialog_lookup.put_princess_on_throne,
            # NES jumps straight to SaveDialog: no "I am greatly pleased" and no experience report or reward
            dialog_lookup.prompt_for_save,
            dialog_lookup.prompt_to_continue_quest,
        ), self.king_lorik['carrying_princess_dialog'])
        self.assertEqual(self.spoken_lines(dialog_lookup.even_when_we_two_are_parted),
                         ["Even when we two are parted by great distances, I shall be with thee."])

    def test_princess_whispers(self):
        with patch.object(self.game.cmd_menu, 'show_text_line_in_dialog_box') as show_line:
            self.dialog_lookup.princess_whispers()
        self.assertEqual(show_line.call_args.kwargs['line'],
                         "Gwaelin then whispers:\n`Wait a moment,please.\nI would give a present to Edward.’")

    # Gwaelin's Love

    def test_receive_gwaelins_love(self):
        self.player.inventory = ['Torch', 'Herb']
        self.assertEqual(self.spoken_lines(self.dialog_lookup.receive_gwaelins_love), [])
        self.assertEqual(self.player.inventory, ['Torch', 'Herb', "Gwaelin's Love"])

    def test_receive_gwaelins_love_with_full_inventory_takes_an_item(self):
        # NES InvListTbl: Torch is checked before Wings; Herbs and Magic Keys don't take up a slot
        self.player.inventory = ['Silver Harp', 'Wings', 'Torch', 'Rainbow Drop', 'Erdrick\'s Token',
                                 'Stones of Sunlight', 'Fairy Water', 'Wings', 'Herb', 'Magic Key']
        lines = self.spoken_lines(self.dialog_lookup.receive_gwaelins_love)
        self.assertEqual(lines, ["And I would like to have something of thine--a token.",
                                 "Please give me thy Torch."])
        self.assertNotIn('Torch', self.player.inventory)
        self.assertIn("Gwaelin's Love", self.player.inventory)

    def test_receive_gwaelins_love_takes_off_the_dragons_scale(self):
        self.player.inventory = ["Dragon's Scale"] + ['Silver Harp'] * 7
        self.player.wearing_dragon_scale = True
        self.spoken_lines(self.dialog_lookup.receive_gwaelins_love)
        self.assertFalse(self.player.wearing_dragon_scale)
        self.assertNotIn("Dragon's Scale", self.player.inventory)

    def test_receive_gwaelins_love_with_full_inventory_and_nothing_to_take(self):
        inventory = ['Silver Harp', 'Rainbow Drop', "Erdrick's Token", 'Stones of Sunlight', 'Silver Harp',
                     'Rainbow Drop', "Erdrick's Token", 'Stones of Sunlight']
        self.player.inventory = list(inventory)
        self.assertEqual(self.spoken_lines(self.dialog_lookup.receive_gwaelins_love), [])
        self.assertEqual(self.player.inventory, inventory)

    # Gwaelin in the throne room

    def test_put_princess_on_throne(self):
        self.go_to('TantegelThroneRoom', (10, 13))
        self.carry_princess()
        self.assertNotIn('PRINCESS_GWAELIN', self.game.current_map.characters)
        with patch.object(self.game.current_map, 'scale_sprite_sheet',
                          wraps=self.game.current_map.scale_sprite_sheet) as scale_sprite_sheet:
            self.dialog_lookup.put_princess_on_throne()
        self.assertFalse(self.game.story_flags.carrying_gwaelin)
        self.assertTrue(self.game.story_flags.gwaelin_returned)
        # The hero goes back to the normal (here unarmed) sprite
        self.assertIn(self.game.directories.UNARMED_HERO_PATH,
                      [call.args[0] for call in scale_sprite_sheet.call_args_list])
        gwaelin = self.game.current_map.characters['PRINCESS_GWAELIN']
        self.assertEqual(gwaelin['coordinates'], GWAELIN_THRONE_ROOM_COORDINATES)
        self.assertEqual(gwaelin['tile_value'], self.game.current_map.character_key['PRINCESS_GWAELIN']['val'])
        self.assertEqual((gwaelin['character'].row, gwaelin['character'].column), (9, 16))
        self.assertIn(gwaelin['character'], self.game.current_map.fixed_characters)
        self.assertEqual(self.game.current_map.get_tile_by_value(self.game.current_map.layout[9][16]), 'BRICK')

    def test_hero_sprite_while_carrying_princess(self):
        self.go_to('TantegelThroneRoom', (10, 13))
        self.carry_princess()
        self.player.weapon = 'Club'
        with patch.object(self.game.current_map, 'scale_sprite_sheet',
                          wraps=self.game.current_map.scale_sprite_sheet) as scale_sprite_sheet:
            self.game.set_player_images_by_equipment()
        self.assertEqual(scale_sprite_sheet.call_args.args[0], self.game.directories.HERO_CARRYING_PRINCESS_PATH)

    def test_gwaelin_only_in_throne_room_once_returned(self):
        self.go_to('TantegelThroneRoom', (10, 13))
        self.assertNotIn('PRINCESS_GWAELIN', self.game.current_map.characters)
        self.game.story_flags.gwaelin_returned = True
        self.go_to('TantegelCourtyard', (14, 14))
        self.go_to('TantegelThroneRoom', (10, 13))
        self.assertEqual(self.game.current_map.characters['PRINCESS_GWAELIN']['coordinates'],
                         GWAELIN_THRONE_ROOM_COORDINATES)

    def test_gwaelin_leaves_the_swamp_cave(self):
        self.go_to('SwampCave', (6, 4))
        self.assertEqual(self.game.current_map.characters['PRINCESS_GWAELIN']['coordinates'],
                         GWAELIN_SWAMP_CAVE_COORDINATES)
        for carrying, returned in ((True, False), (False, True)):
            with self.subTest(carrying=carrying, returned=returned):
                self.game.story_flags.carrying_gwaelin = carrying
                self.game.story_flags.gwaelin_returned = returned
                self.go_to('SwampCave', (6, 4))
                self.assertNotIn('PRINCESS_GWAELIN', self.game.current_map.characters)

    def test_princess_gwaelin_throne_room_dialog(self):
        self.go_to('TantegelThroneRoom', (10, 13))
        self.game.story_flags.gwaelin_returned = True
        gwaelin_dialog = self.dialog_lookup.lookup_table['TantegelThroneRoom']['PRINCESS_GWAELIN']['dialog']
        self.assertEqual(gwaelin_dialog, (self.dialog_lookup.princess_gwaelin_throne_room,))
        with patch('data.text.dialog_lookup_table.random.randint', return_value=0):
            self.assertEqual(self.spoken_lines(self.dialog_lookup.princess_gwaelin_throne_room),
                             ["Even when we two are parted by great distances, I shall be with thee."])
        with patch('data.text.dialog_lookup_table.random.randint', return_value=3):
            self.assertEqual(self.spoken_lines(self.dialog_lookup.princess_gwaelin_throne_room),
                             ["I love thee, Edward."])
        for random_bits in (1, 2):
            with self.subTest(random_bits=random_bits), \
                    patch('data.text.dialog_lookup_table.random.randint', return_value=random_bits), \
                    patch.object(self.dialog_lookup, 'dost_thou_love_me') as dost_thou_love_me:
                self.dialog_lookup.princess_gwaelin_throne_room()
                dost_thou_love_me.assert_called_once()

    def test_dost_thou_love_me_asks_until_yes(self):
        with patch('data.text.dialog_lookup_table.confirmation_prompt') as prompt:
            self.dialog_lookup.dost_thou_love_me()
        self.assertEqual(prompt.call_args.args[1], "Dost thou love me, Edward?")
        no_path = prompt.call_args.kwargs['no_path_function']
        self.assertEqual(no_path.func, self.dialog_lookup.but_thou_must)
        self.assertEqual(no_path.args, (self.dialog_lookup.dost_thou_love_me,))
        self.assertEqual(prompt.call_args.kwargs['yes_path_function'], self.dialog_lookup.im_so_happy)
        with patch.object(self.dialog_lookup, 'play_gwaelins_love_music') as play_music:
            self.assertEqual(self.spoken_lines(self.dialog_lookup.im_so_happy), ["I'm so happy!"])
        play_music.assert_called_once()

    # Other NPCs

    def npc_lines(self, map_name, coordinates, character):
        self.go_to(map_name, coordinates)
        lines = []

        def record(text, *_args, **_kwargs):
            lines.extend([text] if isinstance(text, str) else list(text))

        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box', side_effect=record):
            for entry in self.dialog_lookup.lookup_table[map_name][character]['dialog']:
                entry()
        return lines

    def test_npc_dialog_changes_once_gwaelin_rescued(self):
        cases = (
            ('TantegelCourtyard', (14, 14), 'WOMAN_2', ["Where oh where can I find Princess Gwaelin?"],
             ["Thank you for saving the Princess."]),
            ('TantegelCourtyard', (14, 14), 'GUARD_4', ["Where oh where can I find Princess Gwaelin?"],
             ["Oh, my dearest Gwaelin!’\n`I hate thee, Edward."]),
            ('Brecconary', (23, 10), 'GUARD', ["Tell King Lorik that the search for his daughter hath failed.",
                                              "I am almost gone...."],
             ["Who touches me?’\n`I see nothing, nor can I hear."]),
        )
        for map_name, coordinates, character, not_saved, saved in cases:
            with self.subTest(character=f'{map_name} {character}'):
                self.game.story_flags.carrying_gwaelin = False
                self.game.story_flags.gwaelin_returned = False
                self.assertEqual(self.npc_lines(map_name, coordinates, character), not_saved)
                # NES F_DONE_GWAELIN: carrying her is already enough
                self.game.story_flags.carrying_gwaelin = True
                self.assertEqual(self.npc_lines(map_name, coordinates, character), saved)
                self.game.story_flags.carrying_gwaelin = False
                self.game.story_flags.gwaelin_returned = True
                self.assertEqual(self.npc_lines(map_name, coordinates, character), saved)

    def test_throne_room_guard_once_gwaelin_rescued(self):
        self.go_to('TantegelThroneRoom', (10, 13))
        self.carry_princess()
        self.assertEqual(self.spoken_lines(self.dialog_lookup.tantegel_throne_room_roaming_guard),
                         ["Oh, brave Edward."])

    def test_gwaelin_rescued_flag(self):
        self.assertFalse(self.game.story_flags.gwaelin_rescued)
        self.carry_princess()
        self.assertTrue(self.game.story_flags.gwaelin_rescued)
        self.game.story_flags.carrying_gwaelin = False
        self.game.story_flags.gwaelin_returned = True
        self.assertTrue(self.game.story_flags.gwaelin_rescued)

    # Edge cases

    def test_dying_while_carrying_princess(self):
        # NES DeathText clears F_GOT_GWAELIN: she's back in the Swamp Cave
        self.go_to('Alefgard', (50, 50))
        self.carry_princess()
        self.player.is_dead = True
        self.game.set_post_death_attributes()
        self.assertFalse(self.game.story_flags.carrying_gwaelin)
        self.assertFalse(self.game.story_flags.gwaelin_returned)
        self.assertFalse(self.game.story_flags.gwaelin_rescued)
        self.go_to('SwampCave', (6, 4))
        self.assertIn('PRINCESS_GWAELIN', self.game.current_map.characters)

    def test_dying_after_returning_princess(self):
        self.go_to('Alefgard', (50, 50))
        self.game.story_flags.gwaelin_returned = True
        self.player.is_dead = True
        self.game.set_post_death_attributes()
        self.assertTrue(self.game.story_flags.gwaelin_returned)
        self.assertIn('PRINCESS_GWAELIN', self.game.current_map.characters)

    def test_warping_keeps_carrying_princess(self):
        # Nothing in the NES RETURN, Wings or OUTSIDE code touches PlayerFlags, so she stays in the hero's arms
        self.player.inventory = ['Wings']
        for map_name, start, warp in (('SwampCave', (6, 4), 'outside'),
                                      ('Brecconary', (7, 23), 'return_'),
                                      ('Garinham', (12, 29), 'wings')):
            with self.subTest(map=map_name):
                self.go_to(map_name, start)
                self.carry_princess()
                with patch('src.menu.CommandMenu.show_text_in_dialog_box'):
                    getattr(self.game.cmd_menu, warp)()
                self.assertEqual(self.game.current_map.identifier, 'Alefgard')
                self.assertTrue(self.game.story_flags.carrying_gwaelin)

    def test_inn_greeting_while_carrying_princess(self):
        self.go_to('Brecconary', (23, 10))
        self.player.gold = 100
        for carrying, greeting in ((False, "Good morning.\nThou seems to have spent a good night."),
                                   (True, "Good morning.\nThou hast had a good night's sleep I hope.")):
            with self.subTest(carrying=carrying):
                self.game.story_flags.carrying_gwaelin = carrying
                with patch.object(self.game.cmd_menu, 'show_line_in_dialog_box'), \
                        patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text, \
                        patch('data.text.dialog_lookup_table.screen_fade'):
                    self.dialog_lookup.inn_sleep(6)
                self.assertEqual(show_text.call_args.args[0], (greeting, "I shall see thee again."))
