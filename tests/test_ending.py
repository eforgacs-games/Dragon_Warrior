from unittest import TestCase
from unittest.mock import patch

import pygame

from src.battle import Battle
from src.config.test_config import test_config
from src.direction import Direction
from src.ending import CREDITS, credit_screen_music_events
from src.game import Game
from src.maps import map_lookup


class TestEnding(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()

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
        self.lines = []
        show_line = patch('src.menu.CommandMenu.show_line_in_dialog_box', side_effect=self.record_line).start()
        patch('src.menu.CommandMenu.wait_for_button').start()
        self.addCleanup(patch.stopall)
        self.show_line = show_line

    def record_line(self, line, *args, **kwargs):
        if isinstance(line, str):
            self.lines.append(line)
        else:
            line()

    def where(self):
        tile_size = self.game.tile_size
        rect = self.game.player.rect
        return self.game.current_map.identifier, (rect.y // tile_size, rect.x // tile_size)

    def defeat_dragonlord(self):
        battle = Battle(self.game.config, 'Dragonlord 2', self.game.current_map)
        battle.enemy.hp = 0
        battle.enemy_defeated(self.game.cmd_menu, self.game.screen, self.game.player, False, battle.enemy)

    def stand_before_king(self, column=17):
        self.game.change_map(map_lookup['TantegelCourtyard'](self.game.config), destination_coordinates=(15, column))
        self.game.player.row, self.game.player.column = 15, column

    def run_ending(self, answers=(True,)):
        answers = list(answers)
        prompts = []

        def confirmation_prompt(command_menu, prompt_line, yes_path_function, no_path_function, **kwargs):
            prompts.append(prompt_line)
            (yes_path_function if answers.pop(0) else no_path_function)()

        with patch('src.ending.confirmation_prompt', side_effect=confirmation_prompt), \
                patch.object(self.game.ending, 'roll_credits') as roll_credits, \
                patch.object(self.game.ending, 'wait_for_reset') as wait_for_reset:
            ran = self.game.ending.check_for_end_game_trigger()
        return ran, prompts, roll_credits, wait_for_reset

    # 1. Defeating the Dragonlord

    def test_defeating_dragonlord_2_starts_the_ending(self):
        with patch.object(self.game.ending, 'final_boss_defeated') as final_boss_defeated:
            self.defeat_dragonlord()
        final_boss_defeated.assert_called_once()
        self.assertEqual(self.lines[0], 'Thou hast done well in defeating the Dragonlord.\n')

    def test_other_enemies_do_not_start_the_ending(self):
        battle = Battle(self.game.config, 'Slime', self.game.current_map)
        with patch.object(self.game.ending, 'final_boss_defeated') as final_boss_defeated:
            battle.enemy_defeated(self.game.cmd_menu, self.game.screen, self.game.player, False, battle.enemy)
        final_boss_defeated.assert_not_called()
        self.assertFalse(self.game.story_flags.dragonlord_defeated)

    def test_ball_of_light_and_return_to_overworld(self):
        player = self.game.player
        player.current_hp, player.current_mp = 1, 0
        inventory = list(player.inventory)
        self.defeat_dragonlord()
        self.assertEqual(self.lines[1:], [
            'Thou hast found the Ball of Light.',
            'Radiance streams forth as thy hands touch the object and hold it aloft.',
            'Across the land spreads the brilliance until all shadows are banished and peace is restored.'])
        self.assertTrue(self.game.story_flags.dragonlord_defeated)
        # NES: no experience or gold, HP and MP maxed out, and the Ball of Light isn't an inventory item
        self.assertEqual((player.total_experience, player.gold), (0, 0))
        self.assertEqual((player.current_hp, player.current_mp), (player.max_hp, player.max_mp))
        self.assertEqual(player.inventory, inventory)
        self.assertEqual(self.where(), ('Alefgard', (55, 56)))
        self.assertEqual(player.direction_value, Direction.DOWN.value)

    # 2. The world after the Dragonlord

    def test_no_random_battles_after_the_dragonlord(self):
        self.game.story_flags.dragonlord_defeated = True
        self.game.change_map(map_lookup['Alefgard'](self.game.config), destination_coordinates=(55, 56))
        self.game.tiles_moved_since_spawn = 1
        with patch.object(self.game.battle_ctrl, 'run_battle') as run_battle, \
                patch.dict(self.game.game_state.config, FORCE_BATTLE=True):
            self.game.handle_battles()
        run_battle.assert_not_called()

    def test_tantegel_after_the_dragonlord(self):
        self.game.story_flags.dragonlord_defeated = True
        self.stand_before_king()
        characters = self.game.current_map.characters
        self.assertEqual(characters['KING_LORIK']['coordinates'], (14, 18))
        self.assertNotIn('WISE_MAN', characters)
        self.assertEqual(sum(name.startswith('GUARD') for name in characters), 11)
        self.assertEqual(self.game.ending.npc_dialog('GUARD', self.game.current_map), 'Come now, King Lorik awaits.')

    def test_npc_dialog_elsewhere_after_the_dragonlord(self):
        brecconary = map_lookup['Brecconary'](self.game.config)
        self.assertEqual(self.game.ending.npc_dialog('GUARD', brecconary), '....')
        with patch('src.ending.random.randint', return_value=1):
            self.assertEqual(self.game.ending.npc_dialog('MAN', brecconary), 'Hurrah!\nHurrah!\nLong live Edward!')
        with patch('src.ending.random.randint', return_value=0):
            self.assertEqual(self.game.ending.npc_dialog('MAN', brecconary), 'Thou hast brought us peace, again.')

    def talk_after_the_dragonlord(self, map_name, character):
        self.game.story_flags.dragonlord_defeated = True
        new_map = map_lookup[map_name](self.game.config)
        self.game.change_map(new_map, destination_coordinates=next(iter(new_map.staircases)))
        self.lines.clear()
        with patch('src.ending.random.randint', return_value=0):
            self.game.cmd_menu.launch_dialog(character, self.game.current_map)

    def test_npcs_with_their_own_dialog_only_cheer_after_the_dragonlord(self):
        # NES LD134 overrides every NPC on maps 4 to 14 (ValidateNPC), shops, inns and quest NPCs included
        player = self.game.player
        player.gold = 1000
        player.inventory.append('Silver Harp')
        for map_name, character in (('TantegelThroneRoom', 'KING_LORIK'),  # saving
                                    ('Brecconary', 'WISE_MAN'),  # curse remover
                                    ('Brecconary', 'MERCHANT'),  # weapon and armor shop
                                    ('Brecconary', 'MERCHANT_2'),  # inn
                                    ('Brecconary', 'WOMAN'),  # Fairy Water
                                    ('StaffOfRainCave', 'WISE_MAN'),
                                    ('MagicTemple', 'WISE_MAN')):
            with self.subTest(map_name=map_name, character=character):
                self.assertTrue(self.game.ending.has_victory_dialog(character, map_lookup[map_name](self.game.config)))
                self.talk_after_the_dragonlord(map_name, character)
                self.assertEqual(self.lines, ['Thou hast brought us peace, again.'])
        self.assertEqual(player.gold, 1000)
        self.assertIn('Silver Harp', player.inventory)

    def test_gwaelin_can_still_be_rescued_after_the_dragonlord(self):
        # NES DoTalkResults: she's a map block (BLK_PRINCESS), checked before the NPCs and LD134
        self.assertFalse(self.game.ending.has_victory_dialog('PRINCESS_GWAELIN',
                                                             map_lookup['SwampCave'](self.game.config)))
        prompts = []

        def confirmation_prompt(command_menu, prompt_line, yes_path_function, no_path_function, **kwargs):
            prompts.append(prompt_line)
            yes_path_function()

        with patch('data.text.dialog_lookup_table.confirmation_prompt', side_effect=confirmation_prompt), \
                patch('data.text.dialog_lookup_table.mixer'), patch('data.text.dialog_lookup_table.time.wait'):
            self.talk_after_the_dragonlord('SwampCave', 'PRINCESS_GWAELIN')
        self.assertEqual(self.lines[:2],
                         ['Thou art brave indeed to rescue me, Edward.', 'I am Gwaelin, daughter of Lorik.'])
        self.assertEqual(prompts, ['Will thou take me to the castle?'])
        self.assertIn("I'm so happy!", self.lines)
        self.assertTrue(self.game.story_flags.carrying_gwaelin)
        self.assertNotIn('PRINCESS_GWAELIN', self.game.current_map.characters)

    def test_dragonlord_is_gone_from_charlock(self):
        self.game.story_flags.dragonlord_defeated = True
        self.game.change_map(map_lookup['CharlockB8'](self.game.config), destination_coordinates=(33, 16))
        self.assertNotIn('DRAGONLORD', self.game.current_map.characters)

    # 3. King Lorik's ending scene

    def test_ending_needs_the_dragonlord_defeated(self):
        self.stand_before_king()
        ran, *_ = self.run_ending()
        self.assertFalse(ran)

    def test_ending_needs_the_spot_below_the_king(self):
        self.game.story_flags.dragonlord_defeated = True
        self.stand_before_king()
        self.game.player.row, self.game.player.column = 16, 17
        ran, *_ = self.run_ending()
        self.assertFalse(ran)

    def test_king_scene_without_gwaelin(self):
        self.game.story_flags.dragonlord_defeated = True
        self.stand_before_king(column=18)
        ran, prompts, roll_credits, wait_for_reset = self.run_ending()
        self.assertTrue(ran)
        self.assertEqual(self.lines, [
            'The legends have proven true.',
            'Thou art indeed of the line of Erdrick.',
            'It is thy right to rule over this land.',
            'Will thou take my place?',
            'Edward thought carefully before answering.',
            '`I cannot,’\nsaid Edward.',
            'If ever I am to rule a country, it must be a land that I myself find.',
            'And thus the tale comes to an end....\nunless the dragons return again.'])
        self.assertEqual(prompts, [])
        roll_credits.assert_called_once()
        wait_for_reset.assert_called_once()
        # it only plays once
        self.assertFalse(self.game.ending.check_for_end_game_trigger())

    def test_king_scene_carrying_gwaelin(self):
        self.game.story_flags.dragonlord_defeated = True
        self.game.story_flags.carrying_gwaelin = True
        self.stand_before_king()
        ran, prompts, *_ = self.run_ending(answers=(False, True))
        self.assertTrue(ran)
        self.assertEqual(self.lines[7:], [
            'Gwaelin said:\n`Please, wait.’',
            'I wish to go with thee on thy journey.',
            'But thou must.',
            "I'm so happy!",
            'And thus the tale comes to an end....\nunless the dragons return again.'])
        self.assertEqual(prompts, ['May I travel as thy companion?'] * 2)
        # she ends up in the hero's arms again
        self.assertTrue(self.game.story_flags.carrying_gwaelin)
        self.assertNotIn('PRINCESS_GWAELIN', self.game.current_map.characters)

    def test_king_scene_after_returning_gwaelin(self):
        self.game.story_flags.dragonlord_defeated = True
        self.game.story_flags.gwaelin_returned = True
        self.stand_before_king()
        walked_from = []
        walk = self.game.ending.walk_gwaelin_to_king

        def record_walk(gwaelin):
            walked_from.append((gwaelin.row, gwaelin.column))
            walk(gwaelin)
            walked_from.append((gwaelin.row, gwaelin.column))

        with patch.object(self.game.ending, 'walk_gwaelin_to_king', side_effect=record_walk):
            ran, prompts, *_ = self.run_ending()
        self.assertTrue(ran)
        # NES: she comes down the throne room stairs and walks to the king's side
        self.assertEqual(walked_from, [(14, 14), (14, 17)])
        self.assertIn('Gwaelin said:\n`Please, wait.’', self.lines)
        self.assertEqual(prompts, ['May I travel as thy companion?'])
        self.assertTrue(self.game.story_flags.carrying_gwaelin)

    # 4. Credits

    def test_credits(self):
        shown = []
        with patch.object(self.game.ending, 'show_credit_screen', side_effect=shown.append), \
                patch('src.ending.screen_fade'):
            self.game.ending.roll_credits()
        self.assertEqual(len(shown), 19)
        self.assertEqual(shown[0][0], (7, 8, 'CONGRATULATIONS'))
        self.assertEqual(shown[-1], ((13, 12, 'THE END'),))
        self.assertEqual(shown, list(CREDITS))

    def test_credit_screen_timing(self):
        # NES DoEndCredits: music timing events per screen, before THE END
        self.assertEqual([credit_screen_music_events(i) for i in range(18)],
                         [8, 2, 3, 3, 3] + [2] * 9 + [3] * 4)

    def test_show_credit_screen(self):
        self.game.ending.show_credit_screen(CREDITS[0])

    def test_wait_for_reset_ends_on_quit(self):
        with patch('src.ending.event.get', return_value=[pygame.event.Event(pygame.QUIT)]), \
                patch('src.ending.pygame_quit'), self.assertRaises(SystemExit):
            self.game.ending.wait_for_reset()
