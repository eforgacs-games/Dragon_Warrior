import os
from contextlib import ExitStack
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import KEYDOWN, K_RETURN, event

from src.config.test_config import test_config
from src.game import Game
from tests.mock_map import MockMap

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class TestCommandMenu(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        cls.screen = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self) -> None:
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.current_map = MockMap(self.game.config)
        self.game.current_map.load_map(self.game.player, (0, 0), self.game.game_state.config["TILE_SIZE"])

    # def test_take(self):
    # pygame.key.get_pressed = create_key_mock(pygame.K_s)
    # self.game.cmd_menu.take()
    # pygame.key.get_pressed = create_key_mock(pygame.K_k)
    # self.assertEqual(self.game.current_map.tile_key['BRICK']['val'],
    #                  self.game.current_map.layout[0][1])

    def test_npc_is_across_counter(self):
        self.assertFalse(self.game.cmd_menu.npc_is_across_counter(self.game.current_map.characters['HERO']))

    def test_dragon_scale(self):
        defense_before = self.game.player.defense_power
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.dragon_scale()
            self.assertTrue(self.game.player.wearing_dragon_scale)
            self.assertEqual(self.game.player.defense_power, defense_before + 2)
            self.assertEqual(show_text.call_args.args[0],
                             f"{self.game.player.name} donned the scale of the dragon.")

            self.game.cmd_menu.dragon_scale()
            self.assertEqual(self.game.player.defense_power, defense_before + 2)
            self.assertEqual(show_text.call_args.args[0], "Thou art already wearing the scale of the dragon.")

    def test_fighters_ring_has_no_stat_effect(self):
        attack_before = self.game.player.attack_power
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.fighters_ring()
            self.assertTrue(self.game.player.wearing_fighters_ring)
            self.assertEqual(show_text.call_args.args[0], f"{self.game.player.name} put on the Fighter's Ring.")

            self.game.cmd_menu.fighters_ring()
            self.assertEqual(show_text.call_args.args[0],
                             f"{self.game.player.name} adjusted the position of the Fighter's Ring.")
        self.assertEqual(self.game.player.attack_power, attack_before)

    def test_fighters_ring_with_attack_bonus_option(self):
        self.game.player.fighters_ring_attack_bonus = 2
        attack_before = self.game.player.attack_power
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'):
            self.game.cmd_menu.fighters_ring()
            self.game.cmd_menu.fighters_ring()
        self.assertEqual(self.game.player.attack_power, attack_before + 2)

    def test_take_item(self):
        self.assertEqual([], self.game.player.inventory)
        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        with patch.object(event, 'get', return_value=[mocked_return]):
            self.game.cmd_menu.take_item("test_item")
        self.assertIn("test_item", self.game.player.inventory)

    def test_take_gold(self):
        self.assertEqual(0, self.game.player.gold)
        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        with patch.object(event, 'get', return_value=[mocked_return]):
            self.game.cmd_menu.take_gold({'item': 'GOLD', 'gold': (120, 0)})
        self.assertEqual(120, self.game.player.gold)

    def open_chest_at(self, map_name, coordinates, roll=None):
        """Stand on a chest and TAKE it. Returns the text shown."""
        cmd_menu = self.game.cmd_menu
        cmd_menu.map_name = map_name
        self.game.player.row, self.game.player.column = coordinates
        self.game.player.current_tile = 'TREASURE_BOX'
        with ExitStack() as stack:
            stack.enter_context(patch.object(cmd_menu, 'set_tile_by_coordinates'))
            show_text = stack.enter_context(patch.object(cmd_menu, 'show_text_in_dialog_box'))
            if roll is not None:
                stack.enter_context(patch('src.menu.random.randint', return_value=roll))
                stack.enter_context(patch('src.items.random.randint', return_value=roll))
            cmd_menu.take()
        return [call.args[0] for call in show_text.call_args_list]

    def test_take_rolls_gold_when_opened(self):
        # NES TRSR_GLD4: 500 + (random AND $FF)
        self.open_chest_at('CharlockB8', (16, 17), roll=0x2A)
        self.assertEqual(self.game.player.gold, 542)
        self.assertTrue(self.game.chest_history.is_opened('CharlockB8', (16, 17)))

    def test_take_gold_caps_at_65535(self):
        self.game.player.gold = 65500
        self.open_chest_at('CharlockB8', (16, 17), roll=0)
        self.assertEqual(self.game.player.gold, 65535)

    def test_opened_chest_is_not_taken_twice(self):
        self.open_chest_at('TantegelThroneRoom', (10, 15))
        self.assertEqual(self.game.player.inventory, ['Torch'])
        # the chest becomes brick, so a second TAKE finds nothing
        self.game.player.current_tile = 'BRICK'
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.take()
        self.assertEqual(show_text.call_args.args[0], f"There is nothing to take here, {self.game.player.name}.")
        self.assertEqual(self.game.player.inventory, ['Torch'])

    def test_full_history_leaves_chest_in_place(self):
        for column in range(8):
            self.game.chest_history.record('Elsewhere', (0, column))
        with patch.object(self.game.cmd_menu, 'set_tile_by_coordinates') as set_tile:
            self.game.cmd_menu.map_name = 'Garinham'
            self.game.player.row, self.game.player.column = (5, 18)
            self.game.player.current_tile = 'TREASURE_BOX'
            with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'):
                self.game.cmd_menu.take()
        set_tile.assert_not_called()
        self.assertEqual(self.game.player.inventory, ['Torch'])

    def test_seventh_key_chest_is_empty(self):
        self.game.player.inventory = ['Magic Key'] * 6
        messages = self.open_chest_at('TantegelThroneRoom', (7, 16))
        self.assertEqual(messages, ['Unfortunately, it is empty.'])
        self.assertEqual(self.game.player.inventory.count('Magic Key'), 6)
        self.assertTrue(self.game.chest_history.is_opened('TantegelThroneRoom', (7, 16)))

    def test_herb_chest(self):
        self.open_chest_at('MountainCaveB1', (6, 14))
        self.assertEqual(self.game.player.inventory, ['Herb'])

    def test_death_necklace_one_in_32(self):
        self.open_chest_at('MountainCaveB2', (7, 2), roll=0x20)  # low 5 bits zero
        self.assertIn('Death Necklace', self.game.player.inventory)
        self.assertTrue(self.game.story_flags.death_necklace_found)
        # once found, the chest only ever holds 100-131 gold
        self.game.chest_history = type(self.game.chest_history)()
        self.game.story_flags.death_necklace_found = True
        self.open_chest_at('MountainCaveB2', (7, 2), roll=0x20)
        self.assertEqual(self.game.player.gold, 100)
        self.assertEqual(self.game.player.inventory.count('Death Necklace'), 1)

    def test_death_necklace_chest_gives_gold_otherwise(self):
        self.open_chest_at('MountainCaveB2', (7, 2), roll=0x01)
        self.assertNotIn('Death Necklace', self.game.player.inventory)
        self.assertEqual(self.game.player.gold, 101)
        self.assertFalse(self.game.story_flags.death_necklace_found)

    def test_erdricks_sword_is_equipped(self):
        self.open_chest_at('CharlockB3', (8, 8))
        self.assertEqual(self.game.player.weapon, "Erdrick's Sword")
        self.assertNotIn("Erdrick's Sword", self.game.player.inventory)
        self.game.chest_history = type(self.game.chest_history)()
        messages = self.open_chest_at('CharlockB3', (8, 8))
        self.assertEqual(messages, ['Unfortunately, it is empty.'])

    def test_silver_harp_chest_empty_once_traded(self):
        self.game.player.inventory = ['Staff of Rain']
        messages = self.open_chest_at('GarinsGraveB3', (7, 14))
        self.assertEqual(messages, ['Unfortunately, it is empty.'])
        self.assertNotIn('Silver Harp', self.game.player.inventory)

    def test_stones_of_sunlight_chest_empty_with_rainbow_drop(self):
        self.game.player.inventory = ['Rainbow Drop']
        self.assertEqual(self.open_chest_at('TantegelCellar', (6, 5)), ['Unfortunately, it is empty.'])

    def test_staff_of_rain_chest_always_gives(self):
        # NES ChkTrsrNonGold: no check for an existing Staff of Rain
        self.game.player.inventory = ['Staff of Rain']
        self.open_chest_at('StaffOfRainCave', (6, 5))
        self.assertEqual(self.game.player.inventory.count('Staff of Rain'), 2)

    def test_tablet_is_read_not_kept(self):
        with patch.object(self.game.cmd_menu, 'tablet') as tablet:
            self.open_chest_at('ErdricksCaveB2', (4, 10))
        tablet.assert_called_once()
        self.assertEqual(self.game.player.inventory, [])

    def test_full_inventory_give_up_item(self):
        self.game.player.inventory = ['Torch'] * 8 + ['Herb']
        with patch.object(self.game.cmd_menu, 'prompt_yes_no', return_value=False):
            messages = self.open_chest_at('Rimuldar', (31, 32))
        self.assertEqual(messages[-1], 'Thou hast given up thy Wings.')
        self.assertNotIn('Wings', self.game.player.inventory)
        self.assertTrue(self.game.chest_history.is_opened('Rimuldar', (31, 32)))

    def test_full_inventory_discard_item(self):
        self.game.player.inventory = ['Silver Harp'] + ['Torch'] * 7
        with patch.object(self.game.cmd_menu, 'prompt_yes_no', return_value=True), \
                patch.object(self.game.cmd_menu, 'display_item_menu', side_effect=['Silver Harp', 'Torch']):
            messages = self.open_chest_at('Rimuldar', (31, 32))
        self.assertIn('That is much too important to throw away.', messages)
        self.assertEqual(messages[-1], ('Thou hast dropped thy Torch.', 'And obtained the Wings.'))
        self.assertEqual(self.game.player.inventory.count('Torch'), 6)
        self.assertIn('Wings', self.game.player.inventory)
        self.assertIn('Silver Harp', self.game.player.inventory)

    def test_full_inventory_cannot_discard_worn_cursed_item(self):
        self.game.player.inventory = ['Cursed Belt'] + ['Torch'] * 7
        self.game.player.wearing_cursed_belt = True
        with patch.object(self.game.cmd_menu, 'prompt_yes_no', return_value=True), \
                patch.object(self.game.cmd_menu, 'display_item_menu', side_effect=['Cursed Belt', 'Torch']):
            messages = self.open_chest_at('Rimuldar', (31, 32))
        self.assertIn('A curse is upon thy body.', messages)
        self.assertIn('Cursed Belt', self.game.player.inventory)
        self.assertIn('Wings', self.game.player.inventory)

    def test_chest_not_in_nes_table(self):
        self.game.cmd_menu.map_name = 'Kol'
        self.game.player.current_tile = 'TREASURE_BOX'
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.take()
        self.assertEqual(show_text.call_args.args[0], f"There is nothing to take here, {self.game.player.name}.")

    def cast_sleep(self, enemy, roll):
        battle = MagicMock(no_op=False)
        battle.enemy = enemy
        self.game.cmd_menu.current_battle = battle
        with patch('src.menu.random.randint', return_value=roll), \
                patch.object(self.game.cmd_menu, 'show_line_in_dialog_box') as show_line:
            self.game.cmd_menu.sleep()
        return battle, [c.args[0] for c in show_line.call_args_list]

    def test_sleep_puts_enemy_to_sleep(self):
        from src.enemy import Slime
        slime = Slime()
        battle, messages = self.cast_sleep(slime, roll=0)
        self.assertTrue(slime.is_asleep)
        self.assertTrue(battle.no_op)
        self.assertEqual(messages, ['Thou hast put the Slime to sleep.', 'The Slime is asleep.'])

    def test_sleep_fails_against_resistance(self):
        # Metal Slime resists sleep 15/16: only a roll of 15 succeeds
        from src.enemy import MetalSlime
        metal_slime = MetalSlime()
        battle, messages = self.cast_sleep(metal_slime, roll=14)
        self.assertFalse(metal_slime.is_asleep)
        self.assertFalse(battle.no_op)
        self.assertEqual(messages, ['The spell will not work.'])
        self.cast_sleep(metal_slime, roll=15)
        self.assertTrue(metal_slime.is_asleep)

    def test_sleep_outside_battle(self):
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.sleep()
        self.assertEqual(show_text.call_args.args[0], 'But nothing happened.')

    def test_casting_with_low_mp_outside_battle_does_not_crash(self):
        self.game.player.spells = ["HEAL"]
        self.game.player.current_mp = 0
        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        with patch.object(event, 'get', return_value=[mocked_return]), \
                patch.object(self.game.cmd_menu, 'show_line_in_dialog_box') as show_line:
            self.game.cmd_menu.display_item_menu('spells')
        self.assertEqual(show_line.call_args.args[0], 'Thy MP is too low.')

    def in_battle_with(self, enemy):
        battle = MagicMock(no_op=False)
        battle.enemy = enemy
        self.game.cmd_menu.current_battle = battle
        return battle

    def cast(self, spell, rolls):
        with patch('src.menu.random.randint', side_effect=rolls) as randint, \
                patch.object(self.game.cmd_menu, 'show_line_in_dialog_box') as show_line, \
                patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            getattr(self.game.cmd_menu, spell)()
        lines = [c.args[0] for c in show_line.call_args_list + show_text.call_args_list]
        return randint, lines

    def test_hurt_damages_enemy(self):
        from src.enemy import Slime
        slime = Slime()
        slime.hp = 20
        self.in_battle_with(slime)
        randint, lines = self.cast('hurt', [0, 9])
        self.assertEqual(randint.call_args_list[1].args, (5, 12))
        self.assertEqual(slime.hp, 11)
        self.assertEqual(lines, ["The Slime's Hit Points have been reduced by 9.\n"])

    def test_hurtmore_damage_range(self):
        from src.enemy import Slime
        slime = Slime()
        slime.hp = 100
        self.in_battle_with(slime)
        randint, _ = self.cast('hurtmore', [0, 60])
        self.assertEqual(randint.call_args_list[1].args, (58, 65))
        self.assertEqual(slime.hp, 40)

    def test_hurt_resisted(self):
        # Metal Slime resists HURT 15/16: only a roll of 15 succeeds
        from src.enemy import MetalSlime
        metal_slime = MetalSlime()
        self.in_battle_with(metal_slime)
        _, lines = self.cast('hurt', [14])
        self.assertEqual(metal_slime.hp, metal_slime.max_hp)
        self.assertEqual(lines, ['The spell will not work.'])

    def test_stopspell_blocks_enemy_spells(self):
        from src.enemy import Magician
        magician = Magician()
        self.in_battle_with(magician)
        _, lines = self.cast('stopspell', [0])
        self.assertTrue(magician.is_stopspelled)
        self.assertEqual(lines, ["The Magician's spell hath been blocked."])

    def test_stopspell_resisted(self):
        # Slime resists STOPSPELL 15/16
        from src.enemy import Slime
        slime = Slime()
        self.in_battle_with(slime)
        _, lines = self.cast('stopspell', [14])
        self.assertFalse(slime.is_stopspelled)
        self.assertEqual(lines, ['The spell will not work.'])

    def test_battle_spells_outside_battle(self):
        for spell in ('hurt', 'hurtmore', 'stopspell'):
            with self.subTest(spell=spell):
                _, lines = self.cast(spell, [])
                self.assertEqual(lines, ['But nothing happened.'])

    def test_heal_and_healmore_ranges(self):
        for spell, expected_range in (('heal', (10, 17)), ('healmore', (85, 100))):
            with self.subTest(spell=spell):
                self.game.player.max_hp = 200
                self.game.player.current_hp = 50
                randint, _ = self.cast(spell, [expected_range[1]])
                self.assertEqual(randint.call_args.args, expected_range)
                self.assertEqual(self.game.player.current_hp, 50 + expected_range[1])

    def test_healmore_does_not_exceed_max_hp(self):
        self.game.player.max_hp = 60
        self.game.player.current_hp = 10
        self.cast('healmore', [100])
        self.assertEqual(self.game.player.current_hp, 60)

    def test_herb_heals_and_is_used_up(self):
        self.game.player.inventory = ["Herb", "Herb"]
        self.game.player.max_hp = 100
        self.game.player.current_hp = 10
        randint, _ = self.cast('herb', [30])
        self.assertEqual(randint.call_args.args, (23, 30))
        self.assertEqual(self.game.player.current_hp, 40)
        self.assertEqual(self.game.player.inventory, ["Herb"])

    def test_stopspelled_player_spends_mp_but_spell_is_blocked(self):
        from src.enemy import Slime
        slime = Slime()
        slime.hp = 20
        self.in_battle_with(slime)
        self.game.player.is_stopspelled = True
        self.game.player.spells = ["HURT"]
        self.game.player.current_mp = 10
        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        with patch.object(event, 'get', return_value=[mocked_return]), \
                patch.object(self.game.cmd_menu, 'show_line_in_dialog_box') as show_line:
            self.game.cmd_menu.display_item_menu('spells')
        self.assertEqual(self.game.player.current_mp, 8)
        self.assertEqual(slime.hp, 20)
        self.assertEqual(show_line.call_args.args[0], 'But that spell hath been blocked.')

    def test_learned_spell_name_in_dialog(self):
        # Learned spells are Spell enum members; on Python 3.11+ they used to format as "Spell.HEAL"
        from src.spells import Spell
        self.game.player.spells = [Spell.HEAL]
        self.game.player.current_mp = 10
        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        with patch.object(event, 'get', return_value=[mocked_return]), \
                patch.object(self.game.cmd_menu, 'show_line_in_dialog_box') as show_line:
            self.game.cmd_menu.display_item_menu('spells')
        self.assertEqual(show_line.call_args_list[0].args[0], f"{self.game.player.name} chanted the spell of HEAL.")

    def test_repel_and_fairy_water_set_the_repel_timer(self):
        self.game.cmd_menu.repel()
        self.assertEqual(self.game.repel_timer, 255)
        self.game.player.inventory = ["Fairy Water"]
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.fairy_water()
        self.assertEqual(self.game.repel_timer, 254)
        self.assertEqual(self.game.player.inventory, [])
        self.assertEqual(show_text.call_args.args[0],
                         f"{self.game.player.name} sprinkled the Fairy Water over his body.")

    def test_radiant_lights_up_a_dark_place(self):
        self.game.cmd_menu.current_map.is_dark = True
        self.game.cmd_menu.radiant()
        self.assertEqual(self.game.game_state.light_diameter, 7)
        self.assertEqual(self.game.game_state.radiant_timer, 0x50)
        self.assertEqual(self.game.game_state.pending_light_redraws, [3, 5, 7])

    def test_radiant_does_nothing_in_a_lit_place(self):
        self.game.cmd_menu.current_map.is_dark = False
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.radiant()
        self.assertEqual(show_text.call_args.args[0], "But nothing happened.")
        self.assertEqual(self.game.game_state.light_diameter, 1)
        self.assertEqual(self.game.game_state.radiant_timer, 0)

    def test_torch_lights_up_a_dark_place(self):
        self.game.cmd_menu.current_map.is_dark = True
        self.game.player.inventory = ["Torch", "Herb"]
        self.game.cmd_menu.radiant()
        self.game.cmd_menu.torch()
        self.assertEqual(self.game.player.inventory, ["Herb"])
        # NES UseTorch clears the radiant timer and sets the light to 3 blocks
        self.assertEqual(self.game.game_state.light_diameter, 3)
        self.assertEqual(self.game.game_state.radiant_timer, 0)
        self.assertEqual(self.game.game_state.pending_light_redraws, [3])

    def test_torch_can_only_be_used_in_dark_places(self):
        self.game.cmd_menu.current_map.is_dark = False
        self.game.player.inventory = ["Torch"]
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.torch()
        self.assertEqual(show_text.call_args.args[0], "A torch can be used only in dark places.")
        self.assertEqual(self.game.player.inventory, ["Torch"])
        self.assertEqual(self.game.game_state.light_diameter, 1)

    def test_field_spells_cannot_be_used_in_battle(self):
        from src.enemy import Slime
        from src.spells import Spell
        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        for spell in (Spell.RADIANT, Spell.REPEL, Spell.OUTSIDE, Spell.RETURN):
            with self.subTest(spell=spell):
                battle = self.in_battle_with(Slime())
                self.game.player.spells = [spell]
                self.game.player.current_mp = 10
                with patch.object(event, 'get', return_value=[mocked_return]), \
                        patch.object(self.game.cmd_menu, 'show_line_in_dialog_box') as show_line:
                    self.game.cmd_menu.display_item_menu('spells')
                self.assertEqual(self.game.player.current_mp, 10)
                self.assertTrue(battle.no_op)
                self.assertEqual([c.args[0] for c in show_line.call_args_list], ['That cannot be used in battle.'])

    def use_in_battle(self, item_name, rolls=()):
        with patch('src.menu.random.randint', side_effect=list(rolls)), \
                patch('src.menu.mixer'), \
                patch.object(self.game.cmd_menu, 'show_line_in_dialog_box') as show_line, \
                patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.use_item_in_battle(item_name)
        show_text.assert_not_called()  # battle text goes in battle lines, not the field dialog box
        return [c.args[0] for c in show_line.call_args_list]

    def test_herb_in_battle(self):
        from src.enemy import Slime
        battle = self.in_battle_with(Slime())
        self.game.player.inventory = ["Herb", "Torch"]
        self.game.player.max_hp = 100
        self.game.player.current_hp = 10
        lines = self.use_in_battle("Herb", rolls=[25])
        self.assertEqual(lines, [f"{self.game.player.name} used the Herb."])
        self.assertEqual(self.game.player.current_hp, 35)
        self.assertEqual(self.game.player.inventory, ["Torch"])
        self.assertFalse(battle.no_op)  # the enemy takes its turn

    def test_items_that_cannot_be_used_in_battle(self):
        from src.enemy import Slime
        for item in ("Torch", "Wings", "Fairy Water", "Magic Key", "Rainbow Drop", "Erdrick's Token"):
            with self.subTest(item=item):
                battle = self.in_battle_with(Slime())
                self.game.player.inventory = [item]
                lines = self.use_in_battle(item)
                self.assertEqual(lines, ["That cannot be used in battle."])
                self.assertEqual(self.game.player.inventory, [item])
                self.assertTrue(battle.no_op)  # the player acts again

    def test_silver_harp_in_battle(self):
        from src.enemy import Slime
        battle = self.in_battle_with(Slime())
        self.game.player.inventory = ["Silver Harp"]
        with patch.object(self.game.battle_ctrl, 'queue_scripted_battle') as queue_battle:
            lines = self.use_in_battle("Silver Harp")
        self.assertEqual(lines, [f"{self.game.player.name} played a sweet melody on the harp.",
                                 "The Slime looks happy."])
        queue_battle.assert_not_called()
        self.assertEqual(self.game.player.inventory, ["Silver Harp"])
        self.assertFalse(battle.no_op)

    def test_dragon_scale_in_battle(self):
        from src.enemy import Slime
        self.in_battle_with(Slime())
        self.game.player.inventory = ["Dragon's Scale"]
        defense = self.game.player.defense_power
        lines = self.use_in_battle("Dragon's Scale")
        self.assertEqual(lines, [f"{self.game.player.name} donned the scale of the dragon."])
        self.assertEqual(self.game.player.defense_power, defense + 2)

    def test_closing_item_menu_in_battle_returns_turn(self):
        from pygame import K_ESCAPE
        from src.enemy import Slime
        battle = self.in_battle_with(Slime())
        self.game.player.inventory = ["Herb"]
        escape = MagicMock()
        escape.type = KEYDOWN
        escape.key = K_ESCAPE
        with patch.object(event, 'get', return_value=[escape]):
            self.game.cmd_menu.display_item_menu('inventory')
        self.assertTrue(battle.no_op)
        self.assertEqual(self.game.player.inventory, ["Herb"])
