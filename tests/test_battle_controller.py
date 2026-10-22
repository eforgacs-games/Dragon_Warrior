import unittest
from unittest.mock import MagicMock, Mock, patch

from pygame import KEYDOWN, K_DOWN, K_LEFT, K_RETURN
from pygame.event import Event

from src import enemy as enemies
from src.battle_controller import BattleController
from src.enemy_lookup import enemy_string_lookup
from src.pygame_compat import arrow_fade
from src.spells import Spell


def make_game():
    game = MagicMock()
    game._ = lambda s: s
    game.auto_battle = False
    game.config = {"MUSIC_ENABLED": False}
    game.game_state.config = {"TILE_SIZE": 32}
    player = game.player
    player.name = "Erdrick"
    player.strength = 4
    player.current_hp = 15
    player.armor = "Clothes"
    player.inventory = []
    player.is_asleep = False
    player.asleep_turns = 0
    player.is_dead = False
    player.is_stopspelled = False
    return game


def make_battle(enemy=None):
    battle = Mock()
    if enemy is None:
        enemy = Mock(hp=3, attack=5, pattern=[], dodge=0, is_asleep=False, is_stopspelled=False)
        enemy.name = "Slime"
    battle.enemy = enemy
    battle.turn = 0
    battle.last_turn = 0
    battle.no_op = False
    return battle


def key(k):
    return Event(KEYDOWN, key=k)


def patterned_enemy(pattern):
    enemy = Mock(hp=10, max_hp=10, attack=5, dodge=0, pattern=list(pattern), is_asleep=False,
                 is_stopspelled=False)
    enemy.name = "Magician"
    return enemy


@patch('src.battle_controller.display')
@patch('src.battle_controller.time')
class TestHandleBattlePrompts(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.controller = BattleController(self.game)
        self.battle = make_battle()
        self.events = patch('src.battle_controller.event.get', return_value=[]).start()
        self.random = patch('src.battle_controller.random.random', return_value=0.99).start()
        self.addCleanup(patch.stopall)

    def patch_enemy_move(self, fled=False):
        return patch.object(self.controller, 'enemy_move', return_value=fled)

    def press(self, *keys):
        self.events.return_value = [key(k) for k in keys]
        return self.controller.handle_battle_prompts(False, self.battle)

    def test_no_input_does_nothing(self, mock_time, mock_display):
        self.assertFalse(self.controller.handle_battle_prompts(False, self.battle))
        self.assertEqual(self.battle.turn, 0)
        self.game.receive_damage.assert_not_called()

    def test_down_toggles_menu_row_without_taking_turn(self, mock_time, mock_display):
        self.press(K_DOWN)
        self.assertEqual(self.controller.battle_menu_row, 1)
        self.press(K_DOWN)
        self.assertEqual(self.controller.battle_menu_row, 0)
        self.assertEqual(self.battle.turn, 0)

    def test_left_toggles_menu_column(self, mock_time, mock_display):
        self.press(K_LEFT)
        self.assertEqual(self.controller.battle_menu_column, 1)

    def test_arrow_fade_event_toggles_arrow(self, mock_time, mock_display):
        self.game.show_arrow = True
        self.events.return_value = [Event(arrow_fade)]
        self.controller.handle_battle_prompts(False, self.battle)
        self.assertFalse(self.game.show_arrow)

    def test_fight_attacks_then_enemy_moves(self, mock_time, mock_display):
        with patch.object(self.controller, 'fight') as fight, self.patch_enemy_move() as enemy_move:
            self.assertFalse(self.press(K_RETURN))
        fight.assert_called_once_with(self.battle)
        enemy_move.assert_called_once_with(self.battle)
        self.assertEqual(self.battle.turn, 1)
        self.assertEqual(self.controller.last_battle_action, 'Fight')

    def test_killing_enemy_skips_enemy_turn(self, mock_time, mock_display):
        def kill(battle):
            battle.enemy.hp = 0
        with patch.object(self.controller, 'fight', side_effect=kill), \
                self.patch_enemy_move() as enemy_move:
            self.assertFalse(self.press(K_RETURN))
        enemy_move.assert_not_called()

    def test_player_dies_when_enemy_reduces_hp_to_zero(self, mock_time, mock_display):
        def lethal(battle):
            self.game.player.current_hp = 0
        with patch.object(self.controller, 'fight'), patch.object(self.controller, 'enemy_move', side_effect=lethal):
            self.press(K_RETURN)
        self.assertTrue(self.game.player.is_dead)

    def test_spell_selection_casts_spell(self, mock_time, mock_display):
        self.controller.battle_menu_column = 1
        with self.patch_enemy_move():
            self.press(K_RETURN)
        self.battle.battle_spell.assert_called_once_with(self.game.cmd_menu, self.game.player, self.battle)
        self.assertEqual(self.controller.last_battle_action, 'Spell')

    def test_spell_no_op_skips_enemy_turn(self, mock_time, mock_display):
        self.controller.battle_menu_column = 1
        self.battle.battle_spell.side_effect = lambda *args: setattr(self.battle, 'no_op', True)
        with self.patch_enemy_move() as enemy_move:
            self.press(K_RETURN)
        enemy_move.assert_not_called()

    def test_enemy_attacks_again_after_skipped_turn(self, mock_time, mock_display):
        # no_op must be cleared after a skipped turn (failed run, empty item menu, failed spell),
        # or the enemy never attacks again that battle.
        self.controller.battle_menu_row = 1
        self.battle.battle_run.return_value = False
        with patch.object(self.controller, 'fight'), self.patch_enemy_move() as enemy_move:
            self.press(K_RETURN)
            self.controller.battle_menu_row = 0
            self.press(K_RETURN)
        enemy_move.assert_called_once_with(self.battle)

    def test_successful_run_ends_battle(self, mock_time, mock_display):
        self.controller.battle_menu_row = 1
        self.battle.battle_run.return_value = True
        with self.patch_enemy_move() as enemy_move:
            self.assertTrue(self.press(K_RETURN))
        enemy_move.assert_not_called()
        self.game.music_player.load_and_play_music.assert_called_once_with(self.game.current_map.music_file_path)

    def test_failed_run_does_not_give_enemy_a_second_turn(self, mock_time, mock_display):
        # battle_run already lets the enemy attack when the run fails (regression test for #179)
        self.controller.battle_menu_row = 1
        self.battle.battle_run.return_value = False
        with self.patch_enemy_move() as enemy_move:
            self.assertFalse(self.press(K_RETURN))
        enemy_move.assert_not_called()
        self.assertEqual(self.battle.turn, 1)

    def test_item_with_empty_inventory_skips_enemy_turn(self, mock_time, mock_display):
        self.controller.battle_menu_row = 1
        self.controller.battle_menu_column = 1
        with self.patch_enemy_move() as enemy_move:
            self.press(K_RETURN)
        self.assertIn('Nothing of use', self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0])
        enemy_move.assert_not_called()

    def test_item_with_inventory_opens_item_menu(self, mock_time, mock_display):
        self.controller.battle_menu_row = 1
        self.controller.battle_menu_column = 1
        self.game.player.inventory = ["Herb"]
        with self.patch_enemy_move():
            self.press(K_RETURN)
        self.game.cmd_menu.display_item_menu.assert_called_once_with('inventory')

    def test_auto_battle_repeats_last_action_without_input(self, mock_time, mock_display):
        self.game.auto_battle = True
        self.controller.last_battle_action = 'Fight'
        with patch.object(self.controller, 'fight') as fight, self.patch_enemy_move():
            self.controller.handle_battle_prompts(False, self.battle)
        fight.assert_called_once()
        self.events.assert_not_called()

    def test_asleep_player_loses_turn_on_any_key(self, mock_time, mock_display):
        self.game.player.is_asleep = True
        with patch.object(self.controller, 'fight') as fight, \
                self.patch_enemy_move() as enemy_move, \
                patch('src.battle_controller.random.randint', return_value=0):
            self.press(K_DOWN)
        fight.assert_not_called()
        enemy_move.assert_called_once()
        self.assertEqual(self.controller.last_battle_action, 'Fight')
        self.assertTrue(self.game.player.is_asleep)
        self.assertEqual(self.game.player.asleep_turns, 1)

    def test_asleep_player_can_wake_up(self, mock_time, mock_display):
        self.game.player.is_asleep = True
        with self.patch_enemy_move(), patch('src.battle_controller.random.randint', return_value=1):
            self.press(K_RETURN)
        self.assertFalse(self.game.player.is_asleep)
        self.assertEqual(self.game.player.asleep_turns, 0)
        self.assertIn('awakes', self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0])

    def test_asleep_player_always_wakes_after_six_turns(self, mock_time, mock_display):
        self.game.player.is_asleep = True
        self.game.player.asleep_turns = 5
        with self.patch_enemy_move(), patch('src.battle_controller.random.randint', return_value=0):
            self.press(K_RETURN)
        self.assertFalse(self.game.player.is_asleep)

    def test_enemy_does_not_flee_before_player_acts(self, mock_time, mock_display):
        # NES checks for fleeing at the start of the enemy's turn, not while waiting for the player.
        self.game.player.strength = 10
        self.random.return_value = 0
        with patch.object(self.controller, 'enemy_run_away') as run_away:
            self.assertFalse(self.controller.handle_battle_prompts(False, self.battle))
        run_away.assert_not_called()

    def test_enemy_fleeing_on_its_turn_ends_battle(self, mock_time, mock_display):
        with patch.object(self.controller, 'fight'), self.patch_enemy_move(fled=True):
            self.assertTrue(self.press(K_RETURN))
        self.assertFalse(self.game.player.is_dead)


@patch('src.battle_controller.Battle')
class TestRunBattle(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.controller = BattleController(self.game)

    def test_defeated_enemy_triggers_victory(self, mock_battle_class):
        battle = mock_battle_class.return_value
        battle.enemy.hp = 3

        def kill(run_away, current_battle):
            current_battle.enemy.hp = 0
            return False
        with patch.object(self.controller, 'handle_battle_prompts', side_effect=kill):
            self.controller.run_battle(['Slime'])
        battle.enemy_defeated.assert_called_once()
        self.game.music_player.load_and_play_music.assert_called_once_with(self.game.current_map.music_file_path)

    def test_force_enemy_overrides_zone_enemies(self, mock_battle_class):
        self.game.config["FORCE_ENEMY"] = "Poltergeist"
        mock_battle_class.return_value.enemy.hp = 3
        with patch.object(self.controller, 'handle_battle_prompts', return_value=True):
            self.controller.run_battle(['Slime'])
        self.assertEqual(mock_battle_class.call_args.args[1], "Poltergeist")

    def test_command_menu_sees_current_battle_only_during_battle(self, mock_battle_class):
        battle = mock_battle_class.return_value
        battle.enemy.hp = 3
        seen = []

        def record(run_away, current_battle):
            seen.append(self.game.cmd_menu.current_battle)
            return True
        with patch.object(self.controller, 'handle_battle_prompts', side_effect=record):
            self.controller.run_battle(['Slime'])
        self.assertEqual(seen, [battle])
        self.assertIsNone(self.game.cmd_menu.current_battle)

    def test_player_status_cleared_at_battle_start(self, mock_battle_class):
        mock_battle_class.return_value.enemy.hp = 3
        player = self.game.player
        player.is_asleep, player.asleep_turns, player.is_stopspelled = True, 3, True
        seen = []

        def record(run_away, current_battle):
            seen.append((player.is_asleep, player.asleep_turns, player.is_stopspelled))
            return True
        with patch.object(self.controller, 'handle_battle_prompts', side_effect=record):
            self.controller.run_battle(['Slime'])
        self.assertEqual(seen, [(False, 0, False)])

    def test_repel_avoids_weak_enemies_on_the_overworld(self, mock_battle_class):
        # Slime repel value 5: repelled when 5 - defense // 2 <= 5 // 2, i.e. defense >= 6
        self.game.repel_timer = 255
        self.game.current_map.identifier = 'Alefgard'
        for defense, repelled in ((5, False), (6, True)):
            with self.subTest(defense=defense):
                self.game.player.defense_power = defense
                self.assertEqual(self.controller.is_repelled('Slime'), repelled)
        self.controller.run_battle(['Slime'])
        mock_battle_class.assert_not_called()

    def test_repel_only_works_on_the_overworld_while_active(self, mock_battle_class):
        self.game.player.defense_power = 100
        self.game.current_map.identifier = 'SwampCave'
        self.game.repel_timer = 255
        self.assertFalse(self.controller.is_repelled('Slime'))
        self.game.current_map.identifier = 'Alefgard'
        self.game.repel_timer = 0
        self.assertFalse(self.controller.is_repelled('Slime'))

    def test_running_away_skips_victory(self, mock_battle_class):
        battle = mock_battle_class.return_value
        battle.enemy.hp = 3
        with patch.object(self.controller, 'handle_battle_prompts', return_value=True):
            self.controller.run_battle(['Slime'])
        battle.enemy_defeated.assert_not_called()
        self.game.music_player.load_and_play_music.assert_called_once()


@patch('src.battle_controller.mixer')
class TestEnemyRunAway(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.controller = BattleController(self.game)
        self.battle = make_battle()

    def test_enemy_run_away(self, mock_mixer):
        self.assertTrue(self.controller.enemy_run_away(self.battle, self.battle.enemy))
        self.game.cmd_menu.show_line_in_dialog_box.assert_called_once()
        self.assertEqual(self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0], 'The Slime is running away.')
        self.battle.make_enemy_image_disappear.assert_called_once_with(self.game.screen)
        mock_mixer.music.play.assert_not_called()

    def test_enemy_run_away_restores_map_music(self, mock_mixer):
        self.game.config["MUSIC_ENABLED"] = True
        self.controller.enemy_run_away(self.battle, self.battle.enemy)
        mock_mixer.music.load.assert_called_once_with(self.game.current_map.music_file_path)
        mock_mixer.music.play.assert_called_once_with(-1)


class TestHeroAttack(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.controller = BattleController(self.game)
        self.battle = make_battle()
        self.battle.enemy.hp = 10
        self.battle.enemy.dodge = 1 / 64

    def test_hit_reduces_enemy_hp(self):
        self.battle.calculate_attack_damage.return_value = 4
        with patch('src.battle_controller.random.random', return_value=0.5):
            self.controller.fight(self.battle)
        self.assertEqual(self.battle.enemy.hp, 6)
        self.game.sound.play_sound.assert_called_with(self.game.directories.hit_sfx)

    def test_zero_damage_misses(self):
        self.battle.calculate_attack_damage.return_value = 0
        self.controller.hero_attack(self.battle)
        self.battle.missed_attack.assert_called_once_with(self.game.cmd_menu)
        self.assertEqual(self.battle.enemy.hp, 10)

    def test_sleeping_enemy_cannot_dodge(self):
        self.battle.enemy.is_asleep = True
        self.battle.calculate_attack_damage.return_value = 4
        with patch('src.battle_controller.random.random', return_value=0):
            self.controller.hero_attack(self.battle)
        self.assertEqual(self.battle.enemy.hp, 6)

    def test_enemy_can_dodge(self):
        self.battle.calculate_attack_damage.return_value = 4
        with patch('src.battle_controller.random.random', return_value=0):
            self.controller.hero_attack(self.battle)
        self.assertEqual(self.battle.enemy.hp, 10)
        self.game.sound.play_sound.assert_called_with(self.game.directories.missed_sfx)
        self.game.drawer.flash_enemy.assert_not_called()

    def test_hit_flashes_enemy_red_before_the_damage_text(self):
        # NES PlyrHitEn: SFX, PaletteFlash, then "The enemy's Hit Points have been reduced"
        self.battle.calculate_attack_damage.return_value = 4
        order = []
        self.game.drawer.flash_enemy.side_effect = lambda *a: order.append('flash')
        self.game.cmd_menu.show_line_in_dialog_box.side_effect = lambda line, **k: order.append(line)
        with patch('src.battle_controller.random.random', return_value=0.5):
            self.controller.hero_attack(self.battle)
        self.game.drawer.flash_enemy.assert_called_once_with(self.game.screen, 'Slime')
        self.assertEqual(order[-2:], ['flash', "The Slime's Hit Points have been reduced by 4.\n"])

    def test_miss_does_not_flash_enemy(self):
        self.battle.calculate_attack_damage.return_value = 0
        self.controller.hero_attack(self.battle)
        self.game.drawer.flash_enemy.assert_not_called()


@patch('src.battle_controller.player_hit_shake')
class TestPlayerHitEffect(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.game.config = {"TILE_SIZE": 32}
        self.controller = BattleController(self.game)
        self.battle = make_battle()
        self.game.cmd_menu.current_battle = self.battle

    def test_hit_shakes_without_red_flash(self, mock_shake):
        self.controller.player_hit_effect()
        mock_shake.assert_called_once_with(
            self.game.screen, self.game.config, deathblow=False,
            enemy=self.game.drawer.get_enemy_image.return_value,
            background=(self.battle.get_battle_background_image.return_value, (160, 128)), shake=True)
        self.game.drawer.get_enemy_image.assert_called_once_with('Slime')

    def test_deathblow_flashes_red(self, mock_shake):
        self.game.player.current_hp = 0
        self.controller.player_hit_effect()
        self.assertTrue(mock_shake.call_args.kwargs['deathblow'])

    def test_final_form_does_not_shake(self, mock_shake):
        # NES PlayerHit/DoShake: no shake and no red flash against EN_DRAGONLORD2
        self.battle.enemy.name = 'Dragonlord 2'
        self.game.player.current_hp = 0
        self.controller.player_hit_effect()
        self.assertFalse(mock_shake.call_args.kwargs['shake'])
        self.assertIsNone(mock_shake.call_args.kwargs['background'])

    def test_no_battle_no_effect(self, mock_shake):
        self.game.cmd_menu.current_battle = None
        self.controller.player_hit_effect()
        mock_shake.assert_not_called()


@patch('src.battle_controller.time')
class TestEnemyMove(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.controller = BattleController(self.game)
        patch('src.battle_controller.wait').start()  # the 1-second pause after an enemy's spell
        self.addCleanup(patch.stopall)

    def move(self, enemy, roll=0, effect=None):
        battle = make_battle(enemy)
        randint = Mock(side_effect=lambda a, b: roll if (a, b) == (0, 99) else (effect if effect is not None else a))
        with patch('src.battle_controller.random.randint', randint), \
                patch('src.battle_controller.calculate_enemy_attack_damage', return_value=2):
            self.controller.enemy_move(battle)
        return battle

    def last_message(self):
        return self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0]

    def test_enemy_without_pattern_attacks(self, mock_time):
        self.move(enemies.Slime())
        self.game.receive_damage.assert_called_once_with(2)
        self.assertEqual(self.last_message(), 'The Slime attacks!\n')

    def test_enemy_attack_can_miss(self, mock_time):
        battle = make_battle()
        with patch('src.battle_controller.calculate_enemy_attack_damage', return_value=0):
            self.controller.enemy_move(battle)
        battle.missed_attack.assert_called_once_with(self.game.cmd_menu)
        self.game.receive_damage.assert_not_called()

    def test_successful_hurt_damages_player(self, mock_time):
        self.move(enemies.Magician(), roll=0, effect=7)
        self.game.receive_damage.assert_called_once_with(7)
        self.game.sound.play_sound.assert_any_call(self.game.directories.spell_sfx)

    def test_failed_spell_roll_falls_through_to_attack(self, mock_time):
        self.move(enemies.Magician(), roll=99)
        self.game.receive_damage.assert_called_once_with(2)
        self.assertEqual(self.last_message(), 'The Magician attacks!\n')

    def test_magic_armor_reduces_hurt(self, mock_time):
        self.game.player.armor = "Magic Armor"
        self.move(enemies.Magician(), roll=0, effect=10)
        self.assertEqual(self.game.receive_damage.call_args.args[0], 6)

    def test_sleep_puts_player_to_sleep(self, mock_time):
        self.move(patterned_enemy([(100, Spell.SLEEP, True), Spell.ATTACK]))
        self.assertTrue(self.game.player.is_asleep)
        self.game.receive_damage.assert_not_called()

    def test_sleep_skipped_when_player_already_asleep(self, mock_time):
        self.game.player.is_asleep = True
        self.move(patterned_enemy([(100, Spell.SLEEP, True), Spell.ATTACK]))
        self.game.receive_damage.assert_called_once_with(2)

    def test_stopspell(self, mock_time):
        self.move(patterned_enemy([(100, Spell.STOPSPELL, True), Spell.ATTACK]), effect=1)
        self.assertTrue(self.game.player.is_stopspelled)

    def test_erdricks_armor_blocks_stopspell(self, mock_time):
        self.game.player.armor = "Erdrick's Armor"
        self.move(patterned_enemy([(100, Spell.STOPSPELL, True), Spell.ATTACK]), effect=1)
        self.assertFalse(self.game.player.is_stopspelled)

    def test_firebreath(self, mock_time):
        self.move(patterned_enemy([(100, Spell.FIREBREATH, True), Spell.ATTACK]), effect=20)
        self.game.receive_damage.assert_called_once_with(20)
        self.game.sound.play_sound.assert_any_call(self.game.directories.breathe_fire_sfx)
        self.assertEqual(self.game.cmd_menu.show_line_in_dialog_box.call_args_list[0].args[0],
                         'The Magician is breathing fire.\n')

    def test_erdricks_armor_reduces_firebreath(self, mock_time):
        self.game.player.armor = "Erdrick's Armor"
        self.move(patterned_enemy([(100, Spell.FIREBREATH, True), Spell.ATTACK]), effect=20)
        self.assertEqual(self.game.receive_damage.call_args.args[0], 12)

    def test_heal_condition_false_skips_to_next_entry(self, mock_time):
        self.move(enemies.Drakeema(), roll=0, effect=5)
        # HEAL is skipped at full HP, so HURT is cast instead
        self.game.receive_damage.assert_called_once_with(5)

    def test_heal_recovers_enemy_hp(self, mock_time):
        # HP drops after the pattern was last built; the heal check must still see the new HP.
        drakeema = enemies.Drakeema()
        drakeema.hp = 1
        self.move(drakeema, roll=0, effect=5)
        self.assertEqual(drakeema.hp, 6)
        self.game.receive_damage.assert_not_called()

    def test_heal_does_not_exceed_max_hp(self, mock_time):
        drakeema = enemies.Drakeema()
        drakeema.hp = 1
        self.move(drakeema, roll=0, effect=25)
        self.assertEqual(drakeema.hp, drakeema.max_hp)

    def test_heal_at_exactly_one_quarter_hp(self, mock_time):
        # NES casts heal when current HP <= max HP // 4 (Drakeema: 20 // 4 = 5).
        drakeema = enemies.Drakeema()
        drakeema.hp = 5
        self.move(drakeema, roll=0, effect=5)
        self.assertEqual(drakeema.hp, 10)

    def test_no_heal_above_one_quarter_hp(self, mock_time):
        drakeema = enemies.Drakeema()
        drakeema.hp = 6
        self.move(drakeema, roll=0, effect=5)
        self.assertEqual(drakeema.hp, 6)

    def test_spell_chance_is_exact_percentage(self, mock_time):
        # A 75% spell casts on rolls 0-74 of 0-99.
        self.move(patterned_enemy([(75, Spell.HURT, True), Spell.ATTACK]), roll=74, effect=7)
        self.game.receive_damage.assert_called_once_with(7)
        self.game.reset_mock()
        self.move(patterned_enemy([(75, Spell.HURT, True), Spell.ATTACK]), roll=75, effect=7)
        self.game.receive_damage.assert_called_once_with(2)

    def test_stopspell_skipped_when_already_stopspelled(self, mock_time):
        self.game.player.is_stopspelled = True
        self.move(patterned_enemy([(100, Spell.STOPSPELL, True), Spell.ATTACK]), effect=1)
        self.game.receive_damage.assert_called_once_with(2)
        self.assertEqual(self.last_message(), 'The Magician attacks!\n')

    def test_sleeping_enemy_stays_asleep(self, mock_time):
        slime = enemies.Slime()
        slime.is_asleep = True
        battle = make_battle(slime)
        with patch('src.battle_controller.random.randint', return_value=2), \
                patch('src.battle_controller.calculate_enemy_attack_damage', return_value=2):
            self.assertFalse(self.controller.enemy_move(battle))
        self.assertTrue(slime.is_asleep)
        self.game.receive_damage.assert_not_called()
        self.assertEqual(self.last_message(), 'The Slime is asleep.')

    def test_sleeping_enemy_wakes_and_attacks(self, mock_time):
        slime = enemies.Slime()
        slime.is_asleep = True
        battle = make_battle(slime)
        with patch('src.battle_controller.random.randint', return_value=1), \
                patch('src.battle_controller.calculate_enemy_attack_damage', return_value=2):
            self.controller.enemy_move(battle)
        self.assertFalse(slime.is_asleep)
        messages = [c.args[0] for c in self.game.cmd_menu.show_line_in_dialog_box.call_args_list]
        self.assertEqual(messages[0], 'Slime hath woken up.')
        self.game.receive_damage.assert_called_once_with(2)

    def test_sleeping_enemy_wakes_one_time_in_three(self, mock_time):
        slime = enemies.Slime()
        slime.is_asleep = True
        with patch('src.battle_controller.random.randint', return_value=1) as randint, \
                patch('src.battle_controller.calculate_enemy_attack_damage', return_value=2):
            self.controller.enemy_move(make_battle(slime))
        self.assertEqual(randint.call_args_list[0].args, (1, 3))

    def test_sleeping_enemy_does_not_flee(self, mock_time):
        self.game.player.strength = 10
        slime = enemies.Slime()
        slime.is_asleep = True
        with patch('src.battle_controller.random.random', return_value=0), \
                patch('src.battle_controller.random.randint', return_value=2), \
                patch.object(self.controller, 'enemy_run_away') as run_away:
            self.assertFalse(self.controller.enemy_move(make_battle(slime)))
        run_away.assert_not_called()

    def test_stopspelled_enemy_chants_but_spell_is_blocked(self, mock_time):
        enemy = patterned_enemy([(100, Spell.HURT, True), Spell.ATTACK])
        enemy.is_stopspelled = True
        self.move(enemy, effect=7)
        self.game.receive_damage.assert_not_called()
        messages = [c.args[0] for c in self.game.cmd_menu.show_line_in_dialog_box.call_args_list]
        self.assertEqual(messages, ['Magician chants the spell of HURT.', 'But that spell hath been blocked.'])

    def test_stopspell_does_not_block_fire_breath(self, mock_time):
        enemy = patterned_enemy([(100, Spell.FIREBREATH, True), Spell.ATTACK])
        enemy.is_stopspelled = True
        self.move(enemy, effect=20)
        self.game.receive_damage.assert_called_once_with(20)

    def test_enemy_flees_from_strong_player(self, mock_time):
        self.game.player.strength = 10
        battle = make_battle(enemies.Slime())
        with patch('src.battle_controller.random.random', return_value=0), \
                patch.object(self.controller, 'enemy_run_away', return_value=True) as run_away:
            self.assertTrue(self.controller.enemy_move(battle))
        run_away.assert_called_once_with(battle, battle.enemy)
        self.game.receive_damage.assert_not_called()

    def test_enemy_attacks_when_flee_roll_fails(self, mock_time):
        self.game.player.strength = 10
        battle = make_battle(enemies.Slime())
        with patch('src.battle_controller.random.random', return_value=0.25), \
                patch('src.battle_controller.calculate_enemy_attack_damage', return_value=2):
            self.assertFalse(self.controller.enemy_move(battle))
        self.game.receive_damage.assert_called_once_with(2)

    def test_enemy_does_not_flee_from_weak_player(self, mock_time):
        self.game.player.strength = 9
        battle = make_battle(enemies.Slime())
        with patch('src.battle_controller.random.random', return_value=0), \
                patch('src.battle_controller.calculate_enemy_attack_damage', return_value=2):
            self.assertFalse(self.controller.enemy_move(battle))
        self.game.receive_damage.assert_called_once_with(2)

    def test_every_enemy_can_take_a_turn(self, mock_time):
        # Every pattern entry must be ATTACK or a (chance, spell, condition) 3-tuple;
        # Metal Slime, Poltergeist and Specter used to crash with 2-tuples.
        for name, enemy_class in enemy_string_lookup.items():
            for roll in (0, 99):
                with self.subTest(enemy=name, roll=roll):
                    self.game.reset_mock()
                    self.move(enemy_class(), roll=roll)

    def test_pattern_survives_refresh(self, mock_time):
        # Patterns assigned in __init__ instead of set_pattern() were wiped after the first turn.
        for enemy_class in (enemies.Magidrakee, enemies.Poltergeist):
            with self.subTest(enemy=enemy_class.__name__):
                enemy = enemy_class()
                original = list(enemy.pattern)
                enemy.refresh_pattern()
                self.assertEqual(enemy.pattern, original)

    def test_starwyvern_acts_at_full_hp(self, mock_time):
        # A bare "FIREBREATH" in Starwyvern's pattern used to make it skip its turn.
        self.move(enemies.Starwyvern(), roll=99)
        self.game.receive_damage.assert_called_once()

    def test_armor_reduced_damage_is_whole_number(self, mock_time):
        self.game.player.armor = "Magic Armor"
        self.move(enemies.Magician(), roll=0, effect=10)
        self.assertIsInstance(self.game.receive_damage.call_args.args[0], int)


if __name__ == '__main__':
    unittest.main()
