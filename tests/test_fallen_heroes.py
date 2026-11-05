"""FALLEN HEROES (src/party.py): a party's hero who falls in a fight stays down until an inn (INN, the default), or gets
back up with 1 HP once the fight is won or fled (GET UP)."""
import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame

from src.config.test_config import test_config
from src.follower import COMPANION_GREEN
from src.game_options import FALLEN, FALLEN_GET_UP, FALLEN_INN, DEFAULT_OPTIONS
from src.party import new_hero, stays_down
from src.save_file import HeroSave, SaveFile
from src.save_state import restore_snapshot, take_snapshot
from tests import helpers


class FallenTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.addCleanup(patch.stopall)
        self.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})
        self.game.game_state.is_initial_dialog = False
        self.leader = self.game.player
        self.leader.name = 'Ann'
        self.companion = self.game.companion = new_hero(self.game, 'Gwen')
        self.lines = []
        patch.object(self.game.cmd_menu, 'show_line_in_dialog_box',
                     side_effect=lambda line, *args, **kwargs: self.lines.append(line)).start()

    def fall(self, hero):
        hero.current_hp = 0
        hero.is_dead = True


class TestTheOption(TestCase):

    def test_inn_by_default_and_no_preset(self):
        self.assertEqual(FALLEN_INN, DEFAULT_OPTIONS.fallen)
        self.assertIsNone(FALLEN.presets)
        self.assertTrue(stays_down({}))
        self.assertTrue(stays_down({'FALLEN': FALLEN_INN}))
        self.assertFalse(stays_down({'FALLEN': FALLEN_GET_UP}))


@patch('src.battle_controller.Battle')
class TestAfterTheFight(FallenTestCase):

    def win_with_gwen_fallen(self):
        controller = self.game.battle_ctrl
        patch.object(controller, 'start_fight', return_value=False).start()
        patch.object(controller, 'face_down_after_fight').start()
        patch.object(self.game.music_player, 'load_and_play_music').start()

        def turn(run_away, battle):
            self.fall(self.companion)
            battle.enemy.hp = 0
            return False
        with patch.object(controller, 'handle_battle_prompts', side_effect=turn):
            controller.fight_enemy('Slime')

    def test_stays_down(self, battle_class):
        battle_class.return_value.enemy.hp = 5
        battle_class.return_value.enemy.name = 'Slime'
        self.win_with_gwen_fallen()
        self.assertEqual((True, 0), (self.companion.is_dead, self.companion.current_hp))

    def test_gets_up_with_get_up(self, battle_class):
        self.game.config['FALLEN'] = FALLEN_GET_UP
        battle_class.return_value.enemy.hp = 5
        battle_class.return_value.enemy.name = 'Slime'
        self.win_with_gwen_fallen()
        self.assertEqual((False, 1), (self.companion.is_dead, self.companion.current_hp))


class TestTheFirstHeroFallen(FallenTestCase):

    def test_not_the_end_while_the_other_stands(self):
        self.fall(self.leader)
        with patch.object(self.game.music_player, 'play_until_end') as death_music:
            self.game.hero_death.handle_death()
        death_music.assert_not_called()
        self.assertTrue(self.leader.is_dead)

    def test_the_end_when_both_have_fallen(self):
        self.fall(self.leader)
        self.fall(self.companion)
        with patch.object(self.game.music_player, 'play_until_end') as death_music, \
                patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'), \
                patch.object(self.game.hero_death, 'set_post_death_attributes'):
            self.game.hero_death.handle_death()
        death_music.assert_called_once()

    def test_no_swamp_damage(self):
        self.fall(self.leader)
        with patch.object(self.game.hero_damage, 'damage_step') as damage:
            self.game.hero_damage.handle_environment_damage('MARSH')
        damage.assert_not_called()

    def test_grey_on_the_map(self):
        self.game.set_player_images_by_equipment()
        standing = self.leader.images_map[0][0]
        self.fall(self.leader)
        self.game.set_player_images_by_equipment()
        fallen = self.leader.images_map[0][0]
        self.assertIsNot(standing, fallen)
        colors = {tuple(fallen.get_at((x, y)))[:3] for x in range(fallen.get_width()) for y in range(fallen.get_height())
                  if fallen.get_at((x, y))[3]}
        self.assertTrue(all(red == green == blue for red, green, blue in colors))


class TestTheSecondHeroFallen(FallenTestCase):

    def test_grey_on_the_map(self):
        self.game.follower.sync()
        self.fall(self.companion)
        self.game.follower.update_images()
        image = self.companion.images_map[0][0]
        colors = {tuple(image.get_at((x, y)))[:3] for x in range(image.get_width()) for y in range(image.get_height())}
        self.assertNotIn(COMPANION_GREEN, colors)

    def test_cant_use_items_or_spells(self):
        self.fall(self.companion)
        cmd_menu = self.game.cmd_menu
        with patch.object(cmd_menu.dialog_lookup, 'choose_hero', return_value=self.companion), \
                patch.object(cmd_menu, 'use_an_item') as item, patch.object(self.game, 'unlaunch_menu'):
            cmd_menu.item()
        item.assert_not_called()
        self.assertEqual("Gwen hath fallen.\n", self.lines[-1])

    def test_player_2s_window_says_so(self):
        from src.player_two_menu import open_player_two_menu
        self.fall(self.companion)
        with patch('src.player_two_menu.run_selection') as selection:
            open_player_two_menu(self.game)
        selection.assert_not_called()
        self.assertEqual("Gwen hath fallen.\n", self.lines[-1])

    def test_cant_shop(self):
        self.fall(self.companion)
        dialog_lookup = self.game.cmd_menu.dialog_lookup
        with patch.object(dialog_lookup, 'choose_hero', return_value=self.companion), \
                patch.object(dialog_lookup, 'confirm') as confirm:
            dialog_lookup.fairy_water_shop()
        confirm.assert_not_called()

    def test_the_inn_gets_them_up(self):
        self.fall(self.companion)
        dialog_lookup = self.game.cmd_menu.dialog_lookup
        with patch('data.text.dialog_lookup_table.screen_fade'), \
                patch.object(self.game.music_player, 'play_until_end'), \
                patch.object(self.game.music_player, 'load_and_play_music'), \
                patch.object(self.game.cmd_menu, 'show_popup_window'):
            self.leader.gold = 100
            dialog_lookup.inn_sleep(12)
        self.assertEqual((False, self.companion.max_hp), (self.companion.is_dead, self.companion.current_hp))


class TestSaved(FallenTestCase):

    def test_still_down_after_loading_a_log(self):
        self.fall(self.companion)
        save = SaveFile(name='Ann', experience=0, gold=0, inventory=[],
                        companion=HeroSave.from_player(self.companion))
        loaded = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})
        with patch.object(loaded.map_mgr, 'change_map'):
            loaded.load_game(json.loads(json.dumps(save.to_save())))
        self.assertTrue(loaded.companion.is_dead)
        self.assertFalse(loaded.player.is_dead)

    def test_still_down_after_a_save_state(self):
        self.fall(self.companion)
        snapshot = json.loads(json.dumps(take_snapshot(self.game)))
        restore_snapshot(self.game, snapshot, fade_in=False)
        self.assertTrue(self.game.companion.is_dead)

    def test_a_save_with_hp_left_is_up(self):
        hero = MagicMock(max_hp=10, max_mp=0, get_level_by_experience=lambda: 1)
        HeroSave(name='Gwen', experience=0, inventory=[], current_hp=3).restore(hero)
        self.assertFalse(hero.is_dead)
