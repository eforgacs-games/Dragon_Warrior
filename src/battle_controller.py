"""
BattleController — owns all in-battle logic that previously lived on Game.

Holds the battle-specific state variables and every method that is only
called during the battle loop.  Game keeps a reference to this object and
delegates to it; BattleController holds a back-reference to Game so it can
reach shared resources (player, cmd_menu, screen, sound, drawer, …).
"""

import random

from pygame import KEYDOWN, display, event, mixer, time

from src.battle import Battle, calculate_enemy_attack_damage
from src.common import RED, accept_keys, reject_keys
from src.constants import (
    ARROW_BLINK_INTERVAL_MS, AUTO_BATTLE_DELAY_MS,
    BATTLE_MENU_HEIGHT, BATTLE_MENU_WIDTH, BATTLE_MENU_X, BATTLE_MENU_Y,
    ENEMY_FLEE_PROBABILITY,
)
from src.enemy_spells import enemy_spell_lookup
from src.pygame_compat import arrow_fade
from src.spells import Spell

from pygame import K_DOWN, K_LEFT, K_RIGHT, K_UP, K_a, K_d, K_s, K_w


class BattleController:
    def __init__(self, game):
        self.game = game

        # Battle state (moved from Game.__init__)
        self.battle_menu_row = 0
        self.battle_menu_column = 0
        self.launch_battle = False
        self.enemy_runaway_attempts = 0
        self.last_battle_action = "Fight"

    # ------------------------------------------------------------------ #
    #  Properties that forward to game for brevity inside this class       #
    # ------------------------------------------------------------------ #

    @property
    def player(self):
        return self.game.player

    @property
    def cmd_menu(self):
        return self.game.cmd_menu

    @property
    def screen(self):
        return self.game.screen

    @property
    def sound(self):
        return self.game.sound

    @property
    def directories(self):
        return self.game.directories

    @property
    def graphics(self):
        return self.game.graphics

    @property
    def drawer(self):
        return self.game.drawer

    @property
    def config(self):
        return self.game.config

    @property
    def _(self):
        return self.game._

    @property
    def show_arrow(self):
        return self.game.show_arrow

    @show_arrow.setter
    def show_arrow(self, value):
        self.game.show_arrow = value

    @property
    def auto_battle(self):
        return self.game.auto_battle

    @property
    def music_enabled(self):
        return self.game.music_enabled

    @property
    def current_map(self):
        return self.game.current_map

    @property
    def music_player(self):
        return self.game.music_player

    # ------------------------------------------------------------------ #
    #  Battle entry point                                                  #
    # ------------------------------------------------------------------ #

    def run_battle(self, enemies_in_current_zone):
        enemy_name = random.choice(enemies_in_current_zone)
        current_battle = Battle(self.config, enemy_name, self.current_map)
        current_battle.play_battle_music()
        # TODO: Group parameters into respective classes.
        current_battle.display_battle_window(self.screen, self.drawer,
                                             self.cmd_menu, self.graphics, self.directories,
                                             self.game.color, self.player)
        run_away = False
        while current_battle.enemy.hp > 0 and not run_away and not self.player.is_dead:
            # TODO: Figure out run away bug (when player attempts to run, enemy always gets one extra turn).
            run_away = self.handle_battle_prompts(run_away, current_battle)
        if current_battle.enemy.hp <= 0:
            current_battle.enemy_defeated(self.cmd_menu, self.screen, self.player, self.music_enabled,
                                          current_battle.enemy)
        # TODO: Refactor to music player class.
        self.music_player.load_and_play_music(self.current_map.music_file_path)

    # ------------------------------------------------------------------ #
    #  Battle prompts / menu                                               #
    # ------------------------------------------------------------------ #

    def handle_battle_prompts(self, run_away: bool, current_battle: Battle) -> bool:
        battle_menu_options = ({'Fight': self.directories.BATTLE_MENU_FIGHT_PATH,
                                'Spell': self.directories.BATTLE_MENU_SPELL_PATH},
                               {'Run': self.directories.BATTLE_MENU_RUN_PATH,
                                'Item': self.directories.BATTLE_MENU_ITEM_PATH})
        x, y, width, height = BATTLE_MENU_X, BATTLE_MENU_Y, BATTLE_MENU_WIDTH, BATTLE_MENU_HEIGHT
        tile_size = self.game.game_state.config["TILE_SIZE"]
        selected_image = list(battle_menu_options[self.battle_menu_row].values())[self.battle_menu_column]
        battle_window_rect = self.graphics.blink_switch(self.screen, selected_image,
                                                        self.directories.BATTLE_MENU_STATIC_PATH, x, y,
                                                        width, height,
                                                        tile_size, self.show_arrow, color=self.game.color)
        current_selection = list(battle_menu_options[self.battle_menu_row].keys())[self.battle_menu_column]
        selected_executed_option = None
        random_number = random.random()
        if self.enemy_runaway_attempts == 0 or self.enemy_runaway_attempts == current_battle.turn:
            if self.player.strength >= (current_battle.enemy.attack * 2):
                if random_number < ENEMY_FLEE_PROBABILITY:
                    self.enemy_runaway_attempts = 0
                    return self.enemy_run_away(current_battle, current_battle.enemy)
                else:
                    self.enemy_runaway_attempts += 1

        if self.auto_battle and not self.player.is_asleep:
            selected_executed_option = self.last_battle_action
            time.wait(AUTO_BATTLE_DELAY_MS)
        else:
            for current_event in event.get():
                if current_event.type == KEYDOWN:
                    if not self.player.is_asleep:
                        if current_event.key in accept_keys:
                            self.sound.play_sound(self.directories.menu_button_sfx)
                            selected_executed_option = current_selection
                        elif current_event.key in reject_keys:
                            break
                        elif current_event.key in (K_DOWN, K_s, K_UP, K_w):
                            self.battle_menu_row = 1 - self.battle_menu_row
                        elif current_event.key in (K_LEFT, K_a, K_RIGHT, K_d):
                            self.battle_menu_column = 1 - self.battle_menu_column
                        time.set_timer(arrow_fade, ARROW_BLINK_INTERVAL_MS)
                    else:
                        selected_executed_option = 'Sleep'
                elif current_event.type == arrow_fade:
                    self.show_arrow = not self.show_arrow

        if selected_executed_option:
            if selected_executed_option != 'Sleep':
                self.last_battle_action = selected_executed_option

            self.graphics.create_window(x, y, width, height, selected_image, self.screen, self.game.color)
            display.update(battle_window_rect)
            time.set_timer(arrow_fade, ARROW_BLINK_INTERVAL_MS)
            if selected_executed_option == 'Fight':
                self.fight(current_battle)
            elif selected_executed_option == 'Spell':
                current_battle.battle_spell(self.cmd_menu, self.player, current_battle)
            elif selected_executed_option == 'Run':
                run_away = current_battle.battle_run(self.cmd_menu, self.player, current_battle)
                if run_away:
                    self.music_player.load_and_play_music(self.current_map.music_file_path)
                    return run_away
            elif selected_executed_option == 'Item':
                if not self.player.inventory:
                    self.cmd_menu.show_line_in_dialog_box(
                        'Nothing of use has yet been given to thee.\n',
                        add_quotes=False, hide_arrow=True, disable_sound=True)
                    current_battle.no_op = True
            elif selected_executed_option == 'Sleep':
                self.cmd_menu.show_line_in_dialog_box(self._("Thou art still asleep.\n"),
                                                      add_quotes=False, disable_sound=True,
                                                      hide_arrow=True, skip_text=True)
            current_battle.last_turn = current_battle.turn
            current_battle.turn += 1
            selected_executed_option = None
            time.set_timer(arrow_fade, ARROW_BLINK_INTERVAL_MS)
            if current_battle.enemy.hp <= 0:
                return False
            elif current_battle.last_turn != current_battle.turn:
                if not current_battle.no_op:
                    self.enemy_move(current_battle)
                    if self.player.current_hp <= 0:
                        self.drawer.draw_hovering_stats_window(self.screen, self.player, RED)
                        self.player.is_dead = True
                    elif self.player.is_asleep:
                        self.player.asleep_turns += 1
                        if self.player.asleep_turns >= 6 or random.randint(0, 1) == 1:
                            self.player.is_asleep = False
                            self.player.asleep_turns = 0
                            self.cmd_menu.show_line_in_dialog_box(
                                self._("{} awakes.\n").format(self.player.name) + "Command?\n",
                                add_quotes=False, disable_sound=True, hide_arrow=True)
                        else:
                            self.cmd_menu.show_line_in_dialog_box(self._("Thou art still asleep.\n"),
                                                                  add_quotes=False, disable_sound=True,
                                                                  hide_arrow=True, skip_text=True)
                    current_battle.no_op = False
        return run_away

    def enemy_run_away(self, current_battle, enemy):
        self.sound.play_sound(self.directories.stairs_down_sfx)
        self.cmd_menu.show_line_in_dialog_box(self._("The {} is running away.").format(self._(enemy.name)),
                                              add_quotes=False, disable_sound=True, hide_arrow=True)
        current_battle.make_enemy_image_disappear(self.screen)
        if self.config["MUSIC_ENABLED"]:
            mixer.music.load(self.current_map.music_file_path)
            mixer.music.play(-1)
        return True

    # ------------------------------------------------------------------ #
    #  Hero attack                                                         #
    # ------------------------------------------------------------------ #

    def fight(self, current_battle):
        self.hero_attack(current_battle)

    def hero_attack(self, current_battle):
        self.sound.play_sound(self.directories.attack_sfx)
        self.cmd_menu.show_line_in_dialog_box(self._("{} attacks!\n").format(self.player.name),
                                              add_quotes=False, disable_sound=True, hide_arrow=True)
        attack_damage = current_battle.calculate_attack_damage(self.cmd_menu, self.player, current_battle.enemy)
        if attack_damage <= 0:
            current_battle.missed_attack(self.cmd_menu)
        elif random.random() < current_battle.enemy.dodge:
            self.sound.play_sound(self.directories.missed_sfx)
            self.cmd_menu.show_line_in_dialog_box(self._("It is dodging!").format(self._(current_battle.enemy.name)),
                                                  add_quotes=False, disable_sound=True, hide_arrow=True)
        else:
            self.sound.play_sound(self.directories.hit_sfx)
            self.cmd_menu.show_line_in_dialog_box(
                self._("The {}'s Hit Points have been reduced by {}.\n").format(
                    self._(current_battle.enemy.name), attack_damage),
                add_quotes=False, disable_sound=True, hide_arrow=True)
            current_battle.enemy.hp -= attack_damage

    # ------------------------------------------------------------------ #
    #  Enemy turn                                                          #
    # ------------------------------------------------------------------ #

    def enemy_move(self, current_battle: Battle):
        if not current_battle.enemy.pattern:
            self.enemy_attack(current_battle)
        else:
            current_index = 0
            current_enemy_pattern = current_battle.enemy.pattern[current_index]
            self.execute_enemy_pattern(current_battle, current_enemy_pattern, current_index, current_battle.enemy)

    def execute_enemy_pattern(self, current_battle, current_enemy_pattern, current_index, enemy):
        enemy.refresh_pattern()
        if isinstance(current_enemy_pattern, tuple):
            x = current_enemy_pattern[0]
            current_spell = current_enemy_pattern[1]
            z = current_enemy_pattern[2]
            if current_spell == Spell.SLEEP and self.player.is_asleep:
                z = False
            if z:
                if random.randint(0, 100) < x:
                    if current_spell not in (Spell.FIREBREATH, Spell.FIREBREATH2):
                        self.cmd_menu.show_line_in_dialog_box(
                            self._("{} chants the spell of {}.").format(self._(enemy.name),
                                                                        self._(current_spell)),
                            add_quotes=False, disable_sound=True, hide_arrow=True)
                        self.sound.play_sound(self.directories.spell_sfx)
                    else:
                        self.cmd_menu.show_line_in_dialog_box(
                            self._("The {} is breathing fire.\n").format(self._(enemy.name)),
                            add_quotes=False, disable_sound=True, hide_arrow=True)
                        self.sound.play_sound(self.directories.breathe_fire_sfx)
                    time.wait(1000)
                    spell_effect_lower_bound, spell_effect_upper_bound = enemy_spell_lookup[current_spell]
                    spell_effect = random.randint(spell_effect_lower_bound, spell_effect_upper_bound)
                    if current_spell in (Spell.HEAL, Spell.HEALMORE):
                        enemy.recover_hp(spell_effect)
                    elif current_spell == Spell.SLEEP:
                        self.player.is_asleep = True
                        self.cmd_menu.show_line_in_dialog_box(self._("Thou art asleep.\n"), add_quotes=False,
                                                              disable_sound=True, hide_arrow=True)
                    elif current_spell in (Spell.HURT, Spell.HURTMORE):
                        if self.player.armor in ("Magic Armor", "Erdrick's Armor"):
                            spell_effect *= 0.66
                        self.game.receive_damage(spell_effect)
                    elif current_spell == Spell.STOPSPELL:
                        if self.player.armor != "Erdrick's Armor":
                            if random.randint(0, 1) == 1:
                                self.player.is_stopspelled = True
                    elif current_spell in (Spell.FIREBREATH, Spell.FIREBREATH2):
                        if self.player.armor == "Erdrick's Armor":
                            spell_effect *= 0.66
                        self.game.receive_damage(spell_effect)
                else:
                    self.increment_and_execute_enemy_pattern(current_battle, current_index, enemy)
            else:
                self.increment_and_execute_enemy_pattern(current_battle, current_index, enemy)
        elif isinstance(current_enemy_pattern, str):
            if current_enemy_pattern == Spell.ATTACK:
                self.enemy_attack(current_battle)

    def increment_and_execute_enemy_pattern(self, current_battle, current_index, enemy):
        current_index += 1
        if enemy.pattern:
            current_enemy_pattern = enemy.pattern[current_index]
            self.execute_enemy_pattern(current_battle, current_enemy_pattern, current_index, enemy)
        else:
            self.enemy_attack(current_battle)

    def enemy_attack(self, current_battle):
        self.enemy_attack_message(current_battle.enemy)
        self.execute_enemy_attack(current_battle)

    def execute_enemy_attack(self, current_battle):
        attack_damage = calculate_enemy_attack_damage(self.player, current_battle.enemy)
        if attack_damage <= 0:
            current_battle.missed_attack(self.cmd_menu)
        else:
            self.game.receive_damage(attack_damage)

    def enemy_attack_message(self, enemy):
        self.sound.play_sound(self.directories.prepare_attack_sfx)
        self.cmd_menu.show_line_in_dialog_box(self._("The {} attacks!\n").format(self._(enemy.name)),
                                              add_quotes=False, disable_sound=True, hide_arrow=True)

    # ------------------------------------------------------------------ #
    #  Battle spawn checks                                                 #
    # ------------------------------------------------------------------ #

    def handle_near_tantegel_fight_modifier(self):
        if self.player.current_tile == 'HILLS':
            sub_random_integer = random.randint(0, 3)
        else:
            sub_random_integer = random.randint(0, 1)
        if sub_random_integer == 0:
            random_integer = self.get_random_integer_by_tile()
        else:
            random_integer = 1
        return random_integer

    def get_random_integer_by_tile(self):
        match self.player.current_tile:
            case 'SWAMP':
                random_integer = random.randint(0, 15)
            case 'DESERT':
                random_integer = random.randint(0, 7)
            case 'HILLS':
                random_integer = random.randint(0, 7)
            case 'FOREST':
                random_integer = random.randint(0, 15)
            case 'BRICK':
                random_integer = random.randint(0, 15)
            case 'BARRIER':
                random_integer = random.randint(0, 15)
            case _:
                if self.player.column % 2 == 0:
                    if self.player.row % 2 == 0:
                        random_integer = random.randint(0, 31)
                    else:
                        random_integer = random.randint(0, 15)
                else:
                    if self.player.row % 2 == 0:
                        random_integer = random.randint(0, 31)
                    else:
                        random_integer = random.randint(0, 15)
        return random_integer
