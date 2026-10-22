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
        enemy = Mock(hp=3, attack=5, pattern=[], dodge=0)
        enemy.name = "Slime"
    battle.enemy = enemy
    battle.turn = 0
    battle.last_turn = 0
    battle.no_op = False
    return battle


def key(k):
    return Event(KEYDOWN, key=k)


def patterned_enemy(pattern):
    enemy = Mock(hp=10, max_hp=10, attack=5, dodge=0, pattern=list(pattern))
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
        with patch.object(self.controller, 'fight') as fight, patch.object(self.controller, 'enemy_move') as enemy_move:
            self.assertFalse(self.press(K_RETURN))
        fight.assert_called_once_with(self.battle)
        enemy_move.assert_called_once_with(self.battle)
        self.assertEqual(self.battle.turn, 1)
        self.assertEqual(self.controller.last_battle_action, 'Fight')

    def test_killing_enemy_skips_enemy_turn(self, mock_time, mock_display):
        def kill(battle):
            battle.enemy.hp = 0
        with patch.object(self.controller, 'fight', side_effect=kill), \
                patch.object(self.controller, 'enemy_move') as enemy_move:
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
        with patch.object(self.controller, 'enemy_move'):
            self.press(K_RETURN)
        self.battle.battle_spell.assert_called_once_with(self.game.cmd_menu, self.game.player, self.battle)
        self.assertEqual(self.controller.last_battle_action, 'Spell')

    def test_spell_no_op_skips_enemy_turn(self, mock_time, mock_display):
        self.controller.battle_menu_column = 1
        self.battle.battle_spell.side_effect = lambda *args: setattr(self.battle, 'no_op', True)
        with patch.object(self.controller, 'enemy_move') as enemy_move:
            self.press(K_RETURN)
        enemy_move.assert_not_called()

    @unittest.expectedFailure
    def test_enemy_attacks_again_after_skipped_turn(self, mock_time, mock_display):
        # BUG: no_op is only reset inside the `if not no_op` branch, so once a turn is skipped
        # (failed run, empty item menu, failed spell) the enemy never attacks again that battle.
        self.controller.battle_menu_row = 1
        self.battle.battle_run.return_value = False
        with patch.object(self.controller, 'fight'), patch.object(self.controller, 'enemy_move') as enemy_move:
            self.press(K_RETURN)
            self.controller.battle_menu_row = 0
            self.press(K_RETURN)
        enemy_move.assert_called_once_with(self.battle)

    def test_successful_run_ends_battle(self, mock_time, mock_display):
        self.controller.battle_menu_row = 1
        self.battle.battle_run.return_value = True
        with patch.object(self.controller, 'enemy_move') as enemy_move:
            self.assertTrue(self.press(K_RETURN))
        enemy_move.assert_not_called()
        self.game.music_player.load_and_play_music.assert_called_once_with(self.game.current_map.music_file_path)

    def test_failed_run_does_not_give_enemy_a_second_turn(self, mock_time, mock_display):
        # battle_run already lets the enemy attack when the run fails (regression test for #179)
        self.controller.battle_menu_row = 1
        self.battle.battle_run.return_value = False
        with patch.object(self.controller, 'enemy_move') as enemy_move:
            self.assertFalse(self.press(K_RETURN))
        enemy_move.assert_not_called()
        self.assertEqual(self.battle.turn, 1)

    def test_item_with_empty_inventory_skips_enemy_turn(self, mock_time, mock_display):
        self.controller.battle_menu_row = 1
        self.controller.battle_menu_column = 1
        with patch.object(self.controller, 'enemy_move') as enemy_move:
            self.press(K_RETURN)
        self.assertIn('Nothing of use', self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0])
        enemy_move.assert_not_called()

    def test_auto_battle_repeats_last_action_without_input(self, mock_time, mock_display):
        self.game.auto_battle = True
        self.controller.last_battle_action = 'Fight'
        with patch.object(self.controller, 'fight') as fight, patch.object(self.controller, 'enemy_move'):
            self.controller.handle_battle_prompts(False, self.battle)
        fight.assert_called_once()
        self.events.assert_not_called()

    def test_asleep_player_loses_turn_on_any_key(self, mock_time, mock_display):
        self.game.player.is_asleep = True
        with patch.object(self.controller, 'fight') as fight, \
                patch.object(self.controller, 'enemy_move') as enemy_move, \
                patch('src.battle_controller.random.randint', return_value=0):
            self.press(K_DOWN)
        fight.assert_not_called()
        enemy_move.assert_called_once()
        self.assertEqual(self.controller.last_battle_action, 'Fight')
        self.assertTrue(self.game.player.is_asleep)
        self.assertEqual(self.game.player.asleep_turns, 1)

    def test_asleep_player_can_wake_up(self, mock_time, mock_display):
        self.game.player.is_asleep = True
        with patch.object(self.controller, 'enemy_move'), patch('src.battle_controller.random.randint', return_value=1):
            self.press(K_RETURN)
        self.assertFalse(self.game.player.is_asleep)
        self.assertEqual(self.game.player.asleep_turns, 0)
        self.assertIn('awakes', self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0])

    def test_asleep_player_always_wakes_after_six_turns(self, mock_time, mock_display):
        self.game.player.is_asleep = True
        self.game.player.asleep_turns = 5
        with patch.object(self.controller, 'enemy_move'), patch('src.battle_controller.random.randint', return_value=0):
            self.press(K_RETURN)
        self.assertFalse(self.game.player.is_asleep)

    def test_enemy_flees_from_strong_player(self, mock_time, mock_display):
        self.game.player.strength = 10
        self.random.return_value = 0
        with patch.object(self.controller, 'enemy_run_away', return_value=True) as run_away:
            self.assertTrue(self.controller.handle_battle_prompts(False, self.battle))
        run_away.assert_called_once_with(self.battle, self.battle.enemy)
        self.assertEqual(self.controller.enemy_runaway_attempts, 0)

    def test_enemy_flee_roll_failure_counts_attempt(self, mock_time, mock_display):
        self.game.player.strength = 10
        with patch.object(self.controller, 'enemy_run_away') as run_away:
            self.controller.handle_battle_prompts(False, self.battle)
        run_away.assert_not_called()
        self.assertEqual(self.controller.enemy_runaway_attempts, 1)

    def test_enemy_does_not_flee_from_weak_player(self, mock_time, mock_display):
        self.random.return_value = 0
        with patch.object(self.controller, 'enemy_run_away') as run_away:
            self.controller.handle_battle_prompts(False, self.battle)
        run_away.assert_not_called()
        self.assertEqual(self.controller.enemy_runaway_attempts, 0)


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

    def test_running_away_skips_victory(self, mock_battle_class):
        battle = mock_battle_class.return_value
        battle.enemy.hp = 3
        with patch.object(self.controller, 'handle_battle_prompts', return_value=True):
            self.controller.run_battle(['Slime'])
        battle.enemy_defeated.assert_not_called()
        self.game.music_player.load_and_play_music.assert_called_once()

    @unittest.expectedFailure
    def test_enemy_runaway_attempts_reset_each_battle(self, mock_battle_class):
        # BUG: the counter carries over from the previous battle, so a later enemy
        # can't flee until the turn number catches up with it.
        mock_battle_class.return_value.enemy.hp = 3
        self.controller.enemy_runaway_attempts = 5
        attempts_seen = []

        def record(run_away, current_battle):
            attempts_seen.append(self.controller.enemy_runaway_attempts)
            return True
        with patch.object(self.controller, 'handle_battle_prompts', side_effect=record):
            self.controller.run_battle(['Slime'])
        self.assertEqual(attempts_seen, [0])


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

    def test_enemy_can_dodge(self):
        self.battle.calculate_attack_damage.return_value = 4
        with patch('src.battle_controller.random.random', return_value=0):
            self.controller.hero_attack(self.battle)
        self.assertEqual(self.battle.enemy.hp, 10)
        self.game.sound.play_sound.assert_called_with(self.game.directories.missed_sfx)


@patch('src.battle_controller.time')
class TestEnemyMove(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.controller = BattleController(self.game)

    def move(self, enemy, roll=0, effect=None):
        battle = make_battle(enemy)
        randint = Mock(side_effect=lambda a, b: roll if (a, b) == (0, 100) else (effect if effect is not None else a))
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
        self.assertAlmostEqual(self.game.receive_damage.call_args.args[0], 6.6)

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
        self.assertAlmostEqual(self.game.receive_damage.call_args.args[0], 13.2)

    def test_heal_condition_false_skips_to_next_entry(self, mock_time):
        self.move(enemies.Drakeema(), roll=0, effect=5)
        # HEAL is skipped at full HP, so HURT is cast instead
        self.game.receive_damage.assert_called_once_with(5)

    @unittest.expectedFailure
    def test_heal_recovers_enemy_hp(self, mock_time):
        # BUG: Enemy has no recover_hp method, so any HEAL/HEALMORE cast raises AttributeError.
        drakeema = enemies.Drakeema()
        drakeema.hp = 1
        drakeema.refresh_pattern()
        self.move(drakeema, roll=0, effect=20)
        self.assertEqual(drakeema.hp, 21)

    @unittest.expectedFailure
    def test_every_enemy_can_take_a_turn(self, mock_time):
        # BUG: Metal Slime, Poltergeist and Specter use 2-tuple pattern entries, but
        # execute_enemy_pattern reads entry[2], so their turn raises IndexError.
        for name, enemy_class in enemy_string_lookup.items():
            for roll in (0, 99):
                with self.subTest(enemy=name, roll=roll):
                    self.game.reset_mock()
                    self.move(enemy_class(), roll=roll)

    @unittest.expectedFailure
    def test_pattern_survives_refresh(self, mock_time):
        # BUG: Magidrakee and Poltergeist assign self.pattern in __init__ instead of overriding
        # set_pattern(), so refresh_pattern() wipes it after their first turn.
        for enemy_class in (enemies.Magidrakee, enemies.Poltergeist):
            with self.subTest(enemy=enemy_class.__name__):
                enemy = enemy_class()
                original = list(enemy.pattern)
                enemy.refresh_pattern()
                self.assertEqual(enemy.pattern, original)

    @unittest.expectedFailure
    def test_starwyvern_acts_at_full_hp(self, mock_time):
        # BUG: Starwyvern's pattern has a bare "FIREBREATH" string; only "ATTACK" is handled as a
        # bare string, so whenever HEALMORE is skipped the Starwyvern does nothing.
        self.move(enemies.Starwyvern(), roll=99)
        self.game.receive_damage.assert_called_once()

    @unittest.expectedFailure
    def test_armor_reduced_damage_is_whole_number(self, mock_time):
        # BUG: armor multiplies damage by 0.66, so the player can lose fractional HP (e.g. 6.6).
        self.game.player.armor = "Magic Armor"
        self.move(enemies.Magician(), roll=0, effect=10)
        self.assertIsInstance(self.game.receive_damage.call_args.args[0], int)


class TestEncounterRolls(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.controller = BattleController(self.game)
        self.player = self.game.player
        self.player.row = 0
        self.player.column = 0

    def roll_range(self, tile):
        self.player.current_tile = tile
        with patch('src.battle_controller.random.randint', side_effect=lambda a, b: b) as randint:
            self.controller.get_random_integer_by_tile()
        return randint.call_args.args

    def test_random_integer_range_by_tile(self):
        for tile, expected in (('SWAMP', (0, 15)), ('DESERT', (0, 7)), ('HILLS', (0, 7)), ('FOREST', (0, 15)),
                               ('BRICK', (0, 15)), ('BARRIER', (0, 15)), ('GRASS', (0, 31))):
            with self.subTest(tile=tile):
                self.assertEqual(self.roll_range(tile), expected)

    def test_default_tile_range_depends_on_row_parity(self):
        self.player.row = 1
        self.assertEqual(self.roll_range('GRASS'), (0, 15))
        self.player.column = 1
        self.assertEqual(self.roll_range('GRASS'), (0, 15))
        self.player.row = 2
        self.assertEqual(self.roll_range('GRASS'), (0, 31))

    def test_near_tantegel_modifier_returns_one_unless_sub_roll_is_zero(self):
        self.player.current_tile = 'GRASS'
        with patch('src.battle_controller.random.randint', return_value=1):
            self.assertEqual(self.controller.handle_near_tantegel_fight_modifier(), 1)

    def test_near_tantegel_modifier_rolls_tile_on_zero(self):
        self.player.current_tile = 'HILLS'
        with patch('src.battle_controller.random.randint', side_effect=[0, 5]) as randint:
            self.assertEqual(self.controller.handle_near_tantegel_fight_modifier(), 5)
        self.assertEqual(randint.call_args_list[0].args, (0, 3))


if __name__ == '__main__':
    unittest.main()
