"""
BattleController — owns all in-battle logic that previously lived on Game.

Holds the battle-specific state variables and every method that is only
called during the battle loop.  Game keeps a reference to this object and
delegates to it; BattleController holds a back-reference to Game so it can
reach shared resources (player, cmd_menu, screen, sound, drawer, …).
"""

import random
from collections.abc import Callable
from enum import Enum

from pygame import KEYDOWN, display, event, key, time

from src.battle import Battle, calculate_enemy_attack_damage, enemy_dodges, enemy_flees, player_acts_first
from src.color import LOW_HP_RED
from src.common import A_BUTTON_KEYS, reject_keys, singular_or_plural
from src.cursor import BlinkingCursor
from src.waiting import wait
from src.constants import (
    AUTO_BATTLE_DELAY_MS,
)
from src.encounters import pick_enemy
from src.enemy_lookup import enemy_repel_lookup
from src.enemy_spells import enemy_spell_lookup
from src.guardians import escape_coordinates, record_victory
from src.maps import map_lookup
from src.selection import frame_events, next_frame
from src.spells import Spell
from src.translated_window import draw_translated_window
from src.windows import COMBAT_COMMAND_LAYOUT
from src.visual_effects import player_hit_shake
from src.waiting import handle_speed_key, scaled_ms

from pygame import K_DOWN, K_LEFT, K_RIGHT, K_UP, K_a, K_d, K_s, K_w
from src.cursor import IN_A, IN_B, IN_DOWN, IN_LEFT, IN_RIGHT, IN_UP, SelectionButtons, first_button


class BattleOutcome(Enum):
    """How a fight ended."""
    VICTORY = 'victory'  # the enemy's HP reached 0
    DEFEAT = 'defeat'  # the player died
    ESCAPED = 'escaped'  # the player ran away or the enemy fled
    REPELLED = 'repelled'  # REPEL / Fairy Water kept the enemy away; no fight happened


# CmdCmbtDat: the commands, by row and column (WndCalcSelResult: CC_FIGHT, CC_SPELL, CC_RUN, CC_ITEM)
BATTLE_MENU_OPTIONS = (('Fight', 'Spell'), ('Run', 'Item'))

# The joypad on the keyboard, for the command window's SelectionButtons. A is K and Enter; START (I) is no button
# here: Bank01 WndProcessInput skips SELECT and START, like the field COMMAND window (src/command_window.py).
COMMAND_WINDOW_BUTTON_KEYS = (
    (IN_A, A_BUTTON_KEYS),
    (IN_B, reject_keys),
    (IN_UP, (K_UP, K_w)),
    (IN_DOWN, (K_DOWN, K_s)),
    (IN_LEFT, (K_LEFT, K_a)),
    (IN_RIGHT, (K_RIGHT, K_d)),
)


def joypad_buttons(is_down: Callable[[int], object]) -> int:
    """The NES buttons (JoypadBtns bits) whose keys ``is_down(key)`` says are down."""
    buttons = 0
    for button, keys in COMMAND_WINDOW_BUTTON_KEYS:
        if any(is_down(button_key) for button_key in keys):
            buttons |= button
    return buttons


def key_joypad_buttons(pressed_key: int) -> int:
    """The NES button(s) a key stands for (0 for none)."""
    return joypad_buttons(lambda button_key: button_key == pressed_key)


def held_joypad_buttons() -> int:
    """The NES buttons held right now (GetJoypadStatus), from the keyboard state."""
    pressed = key.get_pressed()
    return joypad_buttons(lambda button_key: pressed[button_key])


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
        # The battle command window's NES cursor and joypad reading (src/cursor.py)
        self.command_cursor = BlinkingCursor()
        self.command_buttons = SelectionButtons(self.command_cursor)
        # Whether the command window is selecting (WndDoSelect). It is opened again at the start of each player turn.
        self.command_window_open = False
        # What the command window was last drawn with (row, column, cursor shown, color), so it is drawn on changes only
        self.drawn_command_window: tuple | None = None
        # Set when the enemy has just cast SLEEP on the hero, so it takes another turn straight away.
        self.player_fell_asleep = False

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
    def auto_battle(self):
        return self.game.auto_battle

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
        return self.launch_fight(enemy_name)

    def start_scripted_battle(self, enemy_name: str) -> BattleOutcome:
        """Start a fixed, story-driven fight right now, the way the NES jumps straight to InitFight with a set
        enemy number (the Dragonlord, and the Golem, Green Dragon and Axe Knight guardians). Unlike a random
        encounter it can't be repelled. Running away and dying work exactly as in a random fight."""
        outcome = self.launch_fight(enemy_name)
        self.battle_menu_row = 0
        self.battle_menu_column = 0
        return outcome

    def launch_fight(self, enemy_name: str) -> BattleOutcome:
        """Fight enemy_name with launch_battle set. It stays set only on a defeat, so Game.handle_death draws the
        in-battle death screen; after a win or an escape a death on the map (a swamp step) is shown on the map."""
        self.launch_battle = True
        outcome = self.fight_enemy(enemy_name)
        if outcome != BattleOutcome.DEFEAT:
            self.launch_battle = False
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
        self.player.is_stopspelled = False
        self.player_ran_away = False
        current_battle.play_battle_music(self.music_player)
        # TODO: Group parameters into respective classes.
        current_battle.display_battle_window(self.screen, self.drawer,
                                             self.cmd_menu, self.graphics, self.directories,
                                             self.game.color, self.player)
        self.command_window_open = False  # the first player turn opens the command window (StartPlayerTurn)
        run_away = self.start_fight(current_battle)
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
            current_battle.enemy_defeated(self.cmd_menu, self.screen, self.player, current_battle.enemy)
            outcome = BattleOutcome.VICTORY
        elif self.player.is_dead:
            outcome = BattleOutcome.DEFEAT
        else:
            outcome = BattleOutcome.ESCAPED
        self.cmd_menu.current_battle = None
        if outcome == BattleOutcome.ESCAPED:
            # The one place an escape (the hero ran or the enemy fled) resumes the map's music (ResumeMusicTbl). After
            # a win, Battle.check_player_level_up has already let the victory (or level-up) music end and resumed it,
            # the way the NES does before ExitFight, and beating the Dragonlord's final form ends in
            # Ending.final_boss_defeated's change of map, which starts the overworld music: starting it again here
            # would restart it. A defeat goes on to the death music (Game.handle_death).
            self.music_player.load_and_play_music(self.current_map.music_file_path)
            if current_battle.enemy.name == 'Dragonlord 2':
                self.reload_map_after_running_from_final_form()
        if outcome == BattleOutcome.ESCAPED and self.player_ran_away:
            self.step_back_after_running()
        return outcome

    def reload_map_after_running_from_final_form(self) -> None:
        """NES RunSuccessful (LE8B2-LE8D1): after running from the Dragonlord's final form, BlackPal is loaded at once,
        so the screen cuts to black with no fade out, then MapChngNoSound (Bank00, LB091) reloads the map and fades it
        in (PalFadeIn). The Dragonlord is still alive, so he is back on his throne."""
        tile_size = self.game.tile_size
        coordinates = self.player.rect.y // tile_size, self.player.rect.x // tile_size
        self.game.change_map(map_lookup[self.current_map.identifier](self.config), destination_coordinates=coordinates,
                             direction=self.player.direction_value, fade_out_first=False)

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

    def start_fight(self, current_battle: Battle) -> bool:
        """NES InitFight, after the enemy appears (SetEnHP): CheckEnRun gives a much weaker enemy its chance to run
        away, then CalcWhoIsNext decides whether the enemy attacks before the hero is ready (StartEnemyTurn) or the
        hero gets the first turn. Returns True if the enemy ran away."""
        enemy = current_battle.enemy
        if enemy_flees(self.player.strength, enemy.attack, random.randint(0, 255)):
            return self.enemy_run_away(current_battle, enemy)
        if player_acts_first(self.player.agility, enemy.defense, random.randint(0, 255), random.randint(0, 255)):
            return False
        self.cmd_menu.show_line_in_dialog_box(
            self._("The {} attacked before {} was ready.").format(self._(enemy.name), self.player.name),
            add_quotes=False, disable_sound=True, hide_arrow=True)
        if self.enemy_move(current_battle):
            return True
        if self.player.current_hp <= 0:
            # 0 HP is always low: NES ChkLowHPPal's $26
            self.drawer.draw_hovering_stats_window(self.screen, self.player, LOW_HP_RED)
            self.player.is_dead = True
        return False

    # ------------------------------------------------------------------ #
    #  Battle prompts / menu                                               #
    # ------------------------------------------------------------------ #

    def draw_command_window(self, cursor_visible: bool) -> None:
        """The battle command window (CmdCmbtDat), generated like the NES draws it (src/window_renderer.py), with the
        NES cursor at the selected command (src/cursor.py), in the window color. Translated, its text is drawn over
        the generated border (src/translated_window.py)."""
        rect = draw_translated_window(self.screen, COMBAT_COMMAND_LAYOUT, self.game.color, self.game.game_state.config,
                                      self._, cursor_index=self.battle_menu_row * 2 + self.battle_menu_column,
                                      cursor_visible=cursor_visible)
        display.update(rect)

    def handle_battle_prompts(self, run_away: bool, current_battle: Battle) -> bool:
        selected_executed_option = None
        if self.player.is_asleep:
            # NES StartPlayerTurn: a sleeping hero's turn is the wake roll, at once. Only PlayerAwakes goes on to
            # ShowCmbtCmd, so there is no command window and no button is waited for (sleeping_player_turn).
            selected_executed_option = 'Sleep'
        else:
            if not self.command_window_open:
                self.open_command_window()
            # Drawn when it opens, and again only when the cursor moves or blinks (or the window color changes)
            drawn = (self.battle_menu_row, self.battle_menu_column, self.command_cursor.visible(), self.game.color)
            if drawn != self.drawn_command_window:
                self.draw_command_window(self.command_cursor.visible())
                self.drawn_command_window = drawn
            if self.auto_battle:
                selected_executed_option = self.last_battle_action
                time.wait(scaled_ms(AUTO_BATTLE_DELAY_MS))
            else:
                next_frame()  # one pass of the fight loop per NES frame (src/selection.py)
                tapped = 0  # keys pressed since the last call, which may have been let go already
                for current_event in frame_events():  # quits if the window is closed; 1 to 4 only set the speed
                    if current_event.type == KEYDOWN:
                        tapped |= key_joypad_buttons(current_event.key)
                presses = self.command_buttons.read(held_joypad_buttons(), tapped)  # WndGetButtons
                selected_executed_option = self.process_command_input(presses)

        if selected_executed_option:
            if selected_executed_option != 'Sleep':
                self.last_battle_action = selected_executed_option
                # WndAPressed: the chosen command's arrow is drawn once more and stays on while it runs
                self.command_cursor.hold()
                self.draw_command_window(True)
            if selected_executed_option == 'Fight':
                self.fight(current_battle)
            elif selected_executed_option == 'Spell':
                current_battle.battle_spell(self.cmd_menu, self.player, current_battle)
            elif selected_executed_option == 'Run':
                run_away = current_battle.battle_run(self.cmd_menu, self.player, current_battle)
                if run_away:
                    # The enemy may have fled on its turn after the hero was blocked: that's no escape by the hero
                    self.player_ran_away = not current_battle.enemy_fled
                    return run_away
                else:
                    # enemy already attacked inside battle_run; skip the outer enemy turn
                    current_battle.no_op = True
            elif selected_executed_option == 'Item':
                if not self.player.inventory:
                    self.cmd_menu.show_line_in_dialog_box(
                        self._('Nothing of use has yet been given to thee.\n'),
                        add_quotes=False, hide_arrow=True, disable_sound=True)
                    current_battle.no_op = True
                else:
                    self.cmd_menu.display_item_menu('inventory')
            elif selected_executed_option == 'Sleep':
                self.sleeping_player_turn(current_battle)
            current_battle.last_turn = current_battle.turn
            current_battle.turn += 1
            selected_executed_option = None
            # The next player turn opens the command window again, from FIGHT (StartPlayerTurn, WndInitSelect)
            self.command_window_open = False
            if current_battle.enemy.hp <= 0:
                return False
            elif current_battle.last_turn != current_battle.turn:
                if not current_battle.no_op:
                    if self.enemy_move(current_battle):
                        return True
                    if self.player.current_hp <= 0:
                        # 0 HP is always low: NES ChkLowHPPal's $26
                        self.drawer.draw_hovering_stats_window(self.screen, self.player, LOW_HP_RED)
                        self.player.is_dead = True
                current_battle.no_op = False
        return run_away

    def open_command_window(self) -> None:
        """StartPlayerTurn and ShowCmbtCmd: Dowindow WND_CMD_CMB, whose WndDoSelect starts selecting afresh every
        turn. WndInitSelect puts the cursor back on FIGHT (WndCol = WndRow = 0), whatever was chosen last turn, and
        the joypad is read from scratch (SelectionButtons.open): the NES has no event queue, so keys pressed before
        the window was up (during the walk into the fight, the enemy's fade-in, "draws near", the enemy's turn)
        are dropped, and keys still held are ignored until they are let go or 11 frames have gone by."""
        self.battle_menu_row = 0
        self.battle_menu_column = 0
        for queued_event in event.get(KEYDOWN):
            handle_speed_key(queued_event)  # the speed keys (1 to 4) still count; every other key is dropped
        self.command_buttons.open(held_joypad_buttons())
        self.command_window_open = True
        self.drawn_command_window = None

    def process_command_input(self, presses: int) -> str | None:
        """WndProcessInput for the command window (CmdCmbtDat: 2 columns of 2 rows): only the first of A, B, up,
        down, left and right that is pressed is handled. Returns the command chosen with A, if any.

        The cursor stops at the edges, it doesn't wrap: WndUpPressed does nothing on the top row, WndDownPressed on
        the bottom row (WndHeight - 3) / 2, WndDoLeftPressed in column 0 and WndRightPressed in the last column
        (WndSelNumCols - 1). Only a real move calls WndUpdateCrsrPos, which restarts the cursor's blink."""
        button = first_button(presses)
        if not button:
            return None
        self.command_buttons.handled(button)
        if button == IN_A:  # WndAPressed: the command under the cursor
            self.sound.play_sound(self.directories.menu_button_sfx)
            return BATTLE_MENU_OPTIONS[self.battle_menu_row][self.battle_menu_column]
        if button == IN_B:
            # WndBPressed returns WND_ABORT, which none of StartPlayerTurn's checks matches, so ChkPlyrRun ends in
            # JMP ShowCmbtCmd: "Command?" again and a new selection, from FIGHT.
            self.command_cursor.hold()
            self.draw_command_window(True)
            self.cmd_menu.show_line_in_dialog_box(self._("Command?\n"), add_quotes=False, hide_arrow=True,
                                                  disable_sound=True)
            self.command_window_open = False
            return None
        row, column = self.battle_menu_row, self.battle_menu_column
        if button == IN_UP:
            row = max(0, row - 1)
        elif button == IN_DOWN:
            row = min(len(BATTLE_MENU_OPTIONS) - 1, row + 1)
        elif button == IN_LEFT:
            column = max(0, column - 1)
        elif button == IN_RIGHT:
            column = min(len(BATTLE_MENU_OPTIONS[0]) - 1, column + 1)
        if (row, column) != (self.battle_menu_row, self.battle_menu_column):
            self.battle_menu_row, self.battle_menu_column = row, column
            self.command_buttons.moved()  # WndUpdateCrsrPos
        return None

    def sleeping_player_turn(self, current_battle: Battle) -> None:
        """NES StartPlayerTurn: a sleeping hero wakes when bit 0 of a random byte is set (50%), with no limit on how
        long the sleep can last. On waking, "<player> awakes." then "Command?": the hero takes this turn as usual.
        Otherwise "Thou art still asleep." (PlayerAsleepDialog) and the enemy takes its turn."""
        if random.randint(0, 255) & 0x01:
            self.player.is_asleep = False
            self.cmd_menu.show_line_in_dialog_box(
                self._("{} awakes.\n").format(self.player.name) + self._("Command?\n"),
                add_quotes=False, disable_sound=True, hide_arrow=True)
            # The hero chooses a command next, so the enemy doesn't move this time round.
            current_battle.no_op = True
        else:
            self.cmd_menu.show_line_in_dialog_box(self._("Thou art still asleep.\n"),
                                                  add_quotes=False, disable_sound=True,
                                                  hide_arrow=True, skip_text=True)

    def enemy_run_away(self, current_battle, enemy):
        self.sound.play_sound(self.directories.stairs_down_sfx)
        self.cmd_menu.show_line_in_dialog_box(self._("The {} is running away.").format(self._(enemy.name)),
                                              add_quotes=False, disable_sound=True, hide_arrow=True)
        current_battle.make_enemy_image_disappear(self.screen)
        current_battle.enemy_fled = True
        return True  # fight_enemy resumes the map's music

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
        elif not current_battle.enemy.is_asleep and enemy_dodges(current_battle.enemy.dodge, random.randint(0, 255)):
            # NES SetEnDmg1: a sleeping enemy can't dodge (excellent moves can be dodged too)
            self.sound.play_sound(self.directories.missed_sfx)
            self.cmd_menu.show_line_in_dialog_box(self._("It is dodging!").format(self._(current_battle.enemy.name)),
                                                  add_quotes=False, disable_sound=True, hide_arrow=True)
        else:
            self.sound.play_sound(self.directories.hit_sfx)
            # NES PlyrHitEn: the enemy flashes red (PaletteFlash) before the damage text
            self.drawer.flash_enemy(self.screen, current_battle.enemy.name)
            # NES TextBlock15 entry 6: PNTS prints "Point" for 1 damage (Bank01 DoPNTS)
            self.cmd_menu.show_line_in_dialog_box(
                singular_or_plural(attack_damage, self._("The {}'s Hit Point have been reduced by {}.\n"),
                                   self._("The {}'s Hit Points have been reduced by {}.\n")).format(
                    self._(current_battle.enemy.name), attack_damage),
                add_quotes=False, disable_sound=True, hide_arrow=True)
            current_battle.enemy.hp -= attack_damage

    # ------------------------------------------------------------------ #
    #  Enemy turn                                                          #
    # ------------------------------------------------------------------ #

    def enemy_move(self, current_battle: Battle) -> bool:
        """Take the enemy's turn. Returns True if the enemy ran away, which ends the battle.
        NES EnCastSleep jumps to PlayerAsleepDialog: once the enemy puts the hero to sleep, "Thou art still asleep."
        is shown and the enemy takes another turn at once, before the hero gets any chance to wake up."""
        while True:
            self.player_fell_asleep = False
            if self.enemy_turn(current_battle):
                return True
            if not self.player_fell_asleep or self.player.current_hp <= 0:
                return False
            self.cmd_menu.show_line_in_dialog_box(self._("Thou art still asleep.\n"), add_quotes=False,
                                                  disable_sound=True, hide_arrow=True, skip_text=True)

    def enemy_turn(self, current_battle: Battle) -> bool:
        """One enemy turn (NES StartEnemyTurn). Returns True if the enemy ran away."""
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
        # NES DoEnemyAttack calls CheckEnRun first: an enemy facing a hero with at least double its attack in
        # strength has a 1 in 4 chance to run away.
        if enemy_flees(self.player.strength, enemy.attack, random.randint(0, 255)):
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
                        # NES EnemyAddHP: capped at the enemy's base HP
                        enemy.recover_hp(spell_effect)
                        self.cmd_menu.show_line_in_dialog_box(
                            self._("The {} hath recovered.").format(self._(enemy.name)), add_quotes=False,
                            disable_sound=True, hide_arrow=True)
                    elif current_spell == Spell.SLEEP:
                        # NES EnCastSleep: always works; the enemy moves again straight away (see enemy_move)
                        self.player.is_asleep = True
                        self.player_fell_asleep = True
                        self.cmd_menu.show_line_in_dialog_box(self._("Thou art asleep.\n"), add_quotes=False,
                                                              disable_sound=True, hide_arrow=True)
                    elif current_spell in (Spell.HURT, Spell.HURTMORE):
                        if self.player.armor in ("Magic Armor", "Erdrick's Armor"):
                            spell_effect = spell_effect // 3 * 2  # NES: divide by 3, then double
                        self.game.receive_damage(spell_effect)
                    elif current_spell == Spell.STOPSPELL:
                        # NES EnCastStopspell: Erdrick's Armor always blocks it; otherwise it works when bit 0 of a
                        # random byte is set (50%). It lasts for the rest of the fight.
                        if self.player.armor != "Erdrick's Armor" and random.randint(0, 255) & 0x01:
                            self.player.is_stopspelled = True
                            message = self._("{}'s spell is blocked.").format(self.player.name)
                        else:
                            message = self._("The spell will not work.")
                        self.cmd_menu.show_line_in_dialog_box(message, add_quotes=False, disable_sound=True,
                                                              hide_arrow=True)
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
            current_battle.enemy_missed_attack(self.cmd_menu)
        else:
            self.game.receive_damage(attack_damage)

    def player_hit_effect(self):
        """NES PlayerHit ($ED20): after the hero's HP drops, the screen shakes, and on a deathblow it also flashes
        red. Against the Dragonlord's final form there is no shake and no red flash."""
        current_battle = self.cmd_menu.current_battle
        if current_battle is None:
            return
        enemy_name = current_battle.enemy.name
        is_final_form = enemy_name == 'Dragonlord 2'
        tile_size = self.config["TILE_SIZE"]
        background = None if is_final_form else (current_battle.get_battle_background_image(),
                                                 (5 * tile_size, 4 * tile_size))
        player_hit_shake(self.screen, self.config, deathblow=self.player.current_hp <= 0,
                         enemy=self.drawer.get_enemy_image(enemy_name), background=background,
                         shake=not is_final_form)

    def enemy_attack_message(self, enemy):
        self.sound.play_sound(self.directories.prepare_attack_sfx)
        self.cmd_menu.show_line_in_dialog_box(self._("The {} attacks!\n").format(self._(enemy.name)),
                                              add_quotes=False, disable_sound=True, hide_arrow=True)
