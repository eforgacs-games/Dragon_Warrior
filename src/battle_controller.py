"""
BattleController — owns all in-battle logic that previously lived on Game.

Holds the battle-specific state variables and every method that is only
called during the battle loop.  Game keeps a reference to this object and
delegates to it; BattleController holds a back-reference to Game so it can
reach shared resources (player, cmd_menu, screen, sound, drawer, …).
"""

import random
from enum import Enum

from pygame import KEYDOWN, display, event, mixer, time

from src.battle import Battle, calculate_enemy_attack_damage
from src.common import BLACK, RED, accept_keys, reject_keys
from src.waiting import quit_if_requested, wait
from src.constants import (
    ARROW_BLINK_INTERVAL_MS, AUTO_BATTLE_DELAY_MS,
    BATTLE_MENU_HEIGHT, BATTLE_MENU_WIDTH, BATTLE_MENU_X, BATTLE_MENU_Y,
    ENEMY_FLEE_PROBABILITY,
)
from src.encounters import pick_enemy
from src.enemy_lookup import enemy_repel_lookup
from src.enemy_spells import enemy_spell_lookup
from src.guardians import escape_coordinates, record_victory
from src.maps import map_lookup
from src.pygame_compat import arrow_fade
from src.spells import Spell

from pygame import K_DOWN, K_LEFT, K_RIGHT, K_UP, K_a, K_d, K_s, K_w


class BattleOutcome(Enum):
    """How a fight ended."""
    VICTORY = 'victory'  # the enemy's HP reached 0
    DEFEAT = 'defeat'  # the player died
    ESCAPED = 'escaped'  # the player ran away or the enemy fled
    REPELLED = 'repelled'  # REPEL / Fairy Water kept the enemy away; no fight happened


class BattleController:
    def __init__(self, game):
        self.game = game

        # Battle state (moved from Game.__init__)
        self.battle_menu_row = 0
        self.battle_menu_column = 0
        self.launch_battle = False
        self.last_battle_action = "Fight"
        # A scripted fight requested from inside a dialog; it starts once the dialog and menu windows are gone.
        self.pending_scripted_battle: str | None = None
        # Whether the current fight ended with the player's RUN succeeding (NES RunSuccessful), as opposed to the
        # enemy running away (CheckEnRun), which goes straight to ExitFight.
        self.player_ran_away = False

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

    def is_repelled(self, enemy_name: str) -> bool:
        """NES ChkFightRepel: with REPEL or Fairy Water active on the overworld, an enemy is avoided when
        its repel value minus half the player's defense is at most half its repel value."""
        if not self.game.repel_timer or self.current_map.identifier != 'Alefgard':
            return False
        repel = enemy_repel_lookup[enemy_name]
        return repel - self.player.defense_power // 2 <= repel // 2

    def run_battle(self, enemies_in_current_zone) -> BattleOutcome:
        """Random encounter: pick an enemy from the current zone's EnemyGroupsTbl row and fight it."""
        enemy_name = self.config.get("FORCE_ENEMY") or pick_enemy(enemies_in_current_zone)
        if self.is_repelled(enemy_name):
            return BattleOutcome.REPELLED
        return self.fight_enemy(enemy_name)

    def start_scripted_battle(self, enemy_name: str) -> BattleOutcome:
        """Start a fixed, story-driven fight right now, the way the NES jumps straight to InitFight with a set
        enemy number (the Dragonlord, and the Golem, Green Dragon and Axe Knight guardians). Unlike a random
        encounter it can't be repelled. Running away and dying work exactly as in a random fight."""
        self.battle_menu_row = 0
        self.battle_menu_column = 0
        self.launch_battle = True
        outcome = self.fight_enemy(enemy_name)
        if outcome != BattleOutcome.DEFEAT:
            # Keep launch_battle set on a defeat so Game.handle_death draws the in-battle death screen.
            self.launch_battle = False
        self.battle_menu_row = 0
        self.battle_menu_column = 0
        return outcome

    def queue_scripted_battle(self, enemy_name: str) -> None:
        """Ask for a scripted fight to start as soon as the current dialog has closed (the NES removes the dialog,
        command and pop-up windows before InitFight). Game.handle_battles picks it up on the next frame."""
        self.pending_scripted_battle = enemy_name

    def run_pending_scripted_battle(self) -> BattleOutcome | None:
        enemy_name, self.pending_scripted_battle = self.pending_scripted_battle, None
        if enemy_name is None:
            return None
        return self.start_scripted_battle(enemy_name)

    def fight_enemy(self, enemy_name: str) -> BattleOutcome:
        """Fight one enemy to the end, then return to the map."""
        current_battle = Battle(self.config, enemy_name, self.current_map)
        self.cmd_menu.current_battle = current_battle
        # NES clears all combat status flags when a fight starts
        self.player.is_asleep = False
        self.player.asleep_turns = 0
        self.player.is_stopspelled = False
        self.player_ran_away = False
        current_battle.play_battle_music()
        # TODO: Group parameters into respective classes.
        current_battle.display_battle_window(self.screen, self.drawer,
                                             self.cmd_menu, self.graphics, self.directories,
                                             self.game.color, self.player)
        run_away = False
        while current_battle.enemy.hp > 0 and not run_away and not self.player.is_dead:
            run_away = self.handle_battle_prompts(run_away, current_battle)
        if current_battle.enemy.hp <= 0:
            if current_battle.enemy.name == 'Dragonlord':
                # NES EnemyDefeated: beating the Dragonlord's first form goes straight into the final fight
                # (InitFight with EN_DRAGONLORD2) instead of returning to the map.
                current_battle.dragonlord_first_form_defeated(self.cmd_menu, self.screen)
                self.cmd_menu.current_battle = None
                return self.fight_enemy('Dragonlord 2')
            # NES EnemyDefeated: the Green Dragon and Golem guardians' story flags
            record_victory(current_battle.enemy.name, self.current_map.identifier, self.game.story_flags)
            current_battle.enemy_defeated(self.cmd_menu, self.screen, self.player, self.music_enabled,
                                          current_battle.enemy)
            outcome = BattleOutcome.VICTORY
        elif self.player.is_dead:
            outcome = BattleOutcome.DEFEAT
        else:
            outcome = BattleOutcome.ESCAPED
            if current_battle.enemy.name == 'Dragonlord 2':
                # NES RunSuccessful: running from the final form blacks out the screen and reloads the map
                # (MapChngNoSound). The Dragonlord is still alive, so he is back on his throne.
                self.screen.fill(BLACK)
                display.flip()
        self.cmd_menu.current_battle = None
        # TODO: Refactor to music player class.
        self.music_player.load_and_play_music(self.current_map.music_file_path)
        if outcome == BattleOutcome.ESCAPED and self.player_ran_away:
            self.step_back_after_running()
        return outcome

    def step_back_after_running(self) -> None:
        """NES RunSuccessful (ChkMapHauksness, ChkMapSwampCave, ChkMapOverworld): after running from a guardian, the
        hero is moved one block back off its tile and the map is reloaded with the stairs sound (MapChngWithSound),
        so the guardian can't be slipped past and Erdrick's Armor can't be searched for."""
        tile_size = self.game.tile_size  # the fight may have started before row and column caught up with the rect
        coordinates = escape_coordinates(self.current_map.identifier,
                                         (self.player.rect.y // tile_size, self.player.rect.x // tile_size),
                                         self.game.story_flags)
        if coordinates is None:
            return
        self.sound.play_sound(self.directories.stairs_down_sfx)
        self.game.change_map(map_lookup[self.current_map.identifier](self.config),
                             destination_coordinates=coordinates, direction=self.player.direction_value)

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

        if self.auto_battle and not self.player.is_asleep:
            selected_executed_option = self.last_battle_action
            time.wait(AUTO_BATTLE_DELAY_MS)
        else:
            for current_event in event.get():
                quit_if_requested(current_event)
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
                    self.player_ran_away = True
                    self.music_player.load_and_play_music(self.current_map.music_file_path)
                    return run_away
                else:
                    # enemy already attacked inside battle_run; skip the outer enemy turn
                    current_battle.no_op = True
            elif selected_executed_option == 'Item':
                if not self.player.inventory:
                    self.cmd_menu.show_line_in_dialog_box(
                        'Nothing of use has yet been given to thee.\n',
                        add_quotes=False, hide_arrow=True, disable_sound=True)
                    current_battle.no_op = True
                else:
                    self.cmd_menu.display_item_menu('inventory')
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
                    if self.enemy_move(current_battle):
                        return True
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
        elif not current_battle.enemy.is_asleep and random.random() < current_battle.enemy.dodge:
            # NES: a sleeping enemy can't dodge
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

    def enemy_move(self, current_battle: Battle) -> bool:
        """Take the enemy's turn. Returns True if the enemy ran away, which ends the battle."""
        enemy = current_battle.enemy
        # NES (StartEnemyTurn): a sleeping enemy wakes 1 time in 3 (the 2-bit roll is redone on 0) and
        # acts immediately; otherwise it stays asleep and the player gets another turn.
        if enemy.is_asleep:
            if random.randint(1, 3) != 1:
                self.cmd_menu.show_line_in_dialog_box(self._("The {} is asleep.").format(self._(enemy.name)),
                                                      add_quotes=False, disable_sound=True, hide_arrow=True)
                return False
            enemy.is_asleep = False
            self.cmd_menu.show_line_in_dialog_box(self._("{} hath woken up.").format(self._(enemy.name)),
                                                  add_quotes=False, disable_sound=True, hide_arrow=True)
        # NES (CheckEnRun): at the start of the enemy's turn, an enemy facing a player with at least
        # double its attack in strength has a 25% chance to run away.
        if self.player.strength >= enemy.attack * 2 and random.random() < ENEMY_FLEE_PROBABILITY:
            return self.enemy_run_away(current_battle, enemy)
        # Rebuild the pattern so HP-based conditions (e.g. HEAL) reflect damage taken this turn.
        enemy.refresh_pattern()
        if not enemy.pattern:
            self.enemy_attack(current_battle)
        else:
            current_index = 0
            current_enemy_pattern = enemy.pattern[current_index]
            self.execute_enemy_pattern(current_battle, current_enemy_pattern, current_index, enemy)
        return False

    def execute_enemy_pattern(self, current_battle, current_enemy_pattern, current_index, enemy):
        enemy.refresh_pattern()
        if isinstance(current_enemy_pattern, tuple):
            x = current_enemy_pattern[0]
            current_spell = current_enemy_pattern[1]
            z = current_enemy_pattern[2]
            if current_spell == Spell.SLEEP and self.player.is_asleep:
                z = False
            elif current_spell == Spell.STOPSPELL and self.player.is_stopspelled:
                z = False
            if z:
                if random.randint(0, 99) < x:
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
                    wait(1000)
                    if enemy.is_stopspelled and current_spell not in (Spell.FIREBREATH, Spell.FIREBREATH2):
                        # NES: a stopspelled enemy still chants, but the spell is blocked (fire breath isn't a spell)
                        self.cmd_menu.show_line_in_dialog_box(self._("But that spell hath been blocked."),
                                                              add_quotes=False, disable_sound=True, hide_arrow=True)
                        return
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
                            spell_effect = spell_effect // 3 * 2  # NES: divide by 3, then double
                        self.game.receive_damage(spell_effect)
                    elif current_spell == Spell.STOPSPELL:
                        if self.player.armor != "Erdrick's Armor":
                            if random.randint(0, 1) == 1:
                                self.player.is_stopspelled = True
                    elif current_spell in (Spell.FIREBREATH, Spell.FIREBREATH2):
                        if self.player.armor == "Erdrick's Armor":
                            spell_effect = spell_effect // 3 * 2  # NES: divide by 3, then double
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
