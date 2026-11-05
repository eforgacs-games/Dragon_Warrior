"""
BattleController — owns all in-battle logic that previously lived on Game.

Holds the battle-specific state variables and every method that is only
called during the battle loop.  Game keeps a reference to this object and
delegates to it; BattleController holds a back-reference to Game so it can
reach shared resources (player, cmd_menu, screen, sound, drawer, …).
"""

from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING, Any

from pygame import KEYDOWN, Surface, display, event, key, time

from src.battle import Battle, calculate_enemy_attack_damage, enemy_dodges, enemy_flees, player_acts_first
from src.color import LOW_HP_RED
from src.controls import PLAYER_ONE, input_player, player_input, pressed
from src.common import A_BUTTON_KEYS, DOWN_KEYS, LEFT_KEYS, RIGHT_KEYS, UP_KEYS, reject_keys, singular_or_plural
from src.menu import BATTLE_LINE
from src.cursor import BlinkingCursor
from src.direction import Direction
from src.constants import (
    AUTO_BATTLE_DELAY_MS,
)
from src.encounters import pick_enemy
from src.enemy_lookup import enemy_repel_lookup
from src.enemy_spells import enemy_spell_lookup
from src.game_events import FightLost, FightWon, RanAway
from src.guardians import escape_coordinates, record_victory
from src.maps import map_lookup
from src.party import acting, free_roaming, heroes, in_party_mode, input_for, living, stays_down
from src.random_streams import hero_random
from src.selection import frame_events, next_frame
from src.sound import SPELL_SFX_FRAMES
from src.spells import Spell
from src.translated_window import draw_translated_window
from src.windows import COMBAT_COMMAND_LAYOUT, COMBAT_COMMAND_WINDOW
from src.visual_effects import player_hit_shake
from src.waiting import handle_speed_key, poll_virtual_joypad, scaled_ms, with_virtual_keys
from src.zoom import handle_zoom_event

from src.cursor import IN_A, IN_B, IN_DOWN, IN_LEFT, IN_RIGHT, IN_UP, SelectionButtons, first_button
from src.nes_random import coin_flip

if TYPE_CHECKING:
    from src.game import Game  # src.game imports this module


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
    (IN_UP, UP_KEYS),
    (IN_DOWN, DOWN_KEYS),
    (IN_LEFT, LEFT_KEYS),
    (IN_RIGHT, RIGHT_KEYS),
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
    pressed = with_virtual_keys(key.get_pressed())
    return joypad_buttons(lambda button_key: pressed[button_key])


# NES DoEnemyAttack: the spells in EnSpell's upper bits (chance in bits 4-5), rolled first, and those in its lower bits
# (chance in bits 0-1)
UPPER_ENEMY_SPELLS = frozenset({Spell.SLEEP, Spell.STOPSPELL, Spell.HEAL, Spell.HEALMORE})


def enemy_spell_slots(pattern: list) -> tuple[tuple | None, tuple | None]:
    """The (chance in percent, spell, condition) entries of an Enemy.set_pattern for its upper and its lower spell
    (None where it has none)."""
    spells = [entry for entry in pattern if isinstance(entry, tuple)]
    upper = next((entry for entry in spells if entry[1] in UPPER_ENEMY_SPELLS), None)
    lower = next((entry for entry in spells if entry[1] not in UPPER_ENEMY_SPELLS), None)
    return upper, lower


def chance_in_quarters(slot: tuple) -> int:
    """A pattern entry's chance as EnSpell holds it: 25% is 1, 50% 2, 75% 3 (and a test's 100% 4: always)."""
    return slot[0] // 25


class BattleController:
    def __init__(self, game: 'Game') -> None:
        self.game = game
        # A party's round (src/party.py): the hero whose turn it is, None for the first one standing
        self.turn_hero: Any = None

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
        # Whether the command window is on the screen, and what it covers there (CommandMenu.covered_area), to put
        # back when it is removed: the NES removes it after every command (RemoveWindow WND_CMD_CMB)
        self.command_window_shown = False
        self.command_window_covered: Surface | None = None
        # Set when the enemy has just cast SLEEP on the hero, so it takes another turn straight away.
        self.player_fell_asleep = False
        # Set by start_scripted_battle for the fight it starts (auto-grind stops before a scripted fight's first
        # command)
        self.scripted_fight = False
        # The fight under way is a scripted one (or the Dragonlord's second form): G can't start auto-grind in it
        self.special_fight = False

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
    def auto_grind(self):
        return self.game.auto_grind

    @property
    def grinding(self) -> bool:
        """Whether auto-grind (src/auto_grind.py) is running: it chooses FIGHT every turn, whatever F4 says."""
        return getattr(getattr(self.game, 'auto_grind', None), 'active', False) is True

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
        self.scripted_fight = True
        outcome = self.launch_fight(enemy_name)
        self.battle_menu_row = 0
        self.battle_menu_column = 0
        return outcome

    def launch_fight(self, enemy_name: str) -> BattleOutcome:
        """Fight enemy_name with launch_battle set. It stays set only on a defeat, so HeroDeath.handle_death draws the
        in-battle death screen; after a win or an escape a death on the map (a swamp step) is shown on the map."""
        rewind = getattr(self.game, 'rewind', None)
        if rewind is not None:
            rewind.fight_starts()  # the snapshot from just before the fight (src/rewind.py)
        self.launch_battle = True
        outcome = self.fight_enemy(enemy_name)
        if outcome != BattleOutcome.DEFEAT:
            self.launch_battle = False
        return outcome

    def queue_scripted_battle(self, enemy_name: str) -> None:
        """Ask for a scripted fight to start as soon as the current dialog has closed (the NES removes the dialog,
        command and pop-up windows before InitFight). FieldEncounters.handle_battles picks it up on the next frame."""
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
        # NES clears all combat status flags when a fight starts (every hero's, in a party: src/party.py)
        for hero in heroes(self.game):
            hero.is_asleep = False
            hero.is_stopspelled = False
        self.player_ran_away = False
        self.turn_hero = None  # the first hero standing has the first turn of a round
        current_battle.play_battle_music(self.music_player)
        # TODO: Group parameters into respective classes.
        current_battle.display_battle_window(self.screen, self.drawer,
                                             self.cmd_menu, self.graphics, self.directories,
                                             self.game.color, self.player)
        scripted, self.scripted_fight = self.scripted_fight, False
        self.special_fight = scripted or enemy_name == 'Dragonlord 2'
        if self.special_fight:
            # Auto-grind never fights a guardian or the Dragonlord: the player chooses from the first command on
            self.auto_grind.scripted_fight_starts()
        # The first player turn opens the command window (StartPlayerTurn): if the enemy attacks first, there is none
        self.command_window_open = False
        self.command_window_shown = False
        self.command_window_covered = None
        run_away = self.start_fight(current_battle)
        while current_battle.enemy.hp > 0 and not run_away and not self.party_fallen():
            # Each hero's turn is played with them as game.player (src/party.py acting), on their player's joypad
            hero = self.hero_to_act()
            with acting(self.game, hero), player_input(input_for(self.game, hero)):
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
            self.game.event_bus.emit(FightWon(current_battle.enemy.name))
            current_battle.enemy_defeated(self.cmd_menu, self.screen, self.player, current_battle.enemy,
                                          heroes=living(self.game))
            outcome = BattleOutcome.VICTORY
        elif self.party_fallen():
            self.game.event_bus.emit(FightLost())
            outcome = BattleOutcome.DEFEAT
        else:
            if self.player_ran_away:
                self.game.event_bus.emit(RanAway())
            outcome = BattleOutcome.ESCAPED
        self.cmd_menu.current_battle = None
        if outcome != BattleOutcome.DEFEAT and not stays_down(self.config):
            self.get_fallen_heroes_up()  # FALLEN HEROES on GET UP; on INN they stay down until an inn
        if outcome == BattleOutcome.ESCAPED and not current_battle.enemy_fled:
            # The one place the hero's escape resumes the map's music (ResumeMusicTbl). An enemy that ran away has
            # already resumed it, before ExitFight's press (enemy_run_away). After a win, Battle.check_player_level_up
            # has already let the victory (or level-up) music end and resumed it, the way the NES does before
            # ExitFight, and beating the Dragonlord's final form ends in Ending.final_boss_defeated's change of map,
            # which starts the overworld music: starting it again here would restart it. A defeat goes on to the death
            # music (HeroDeath.handle_death).
            self.music_player.load_and_play_music(self.current_map.music_file_path)
            if current_battle.enemy.name == 'Dragonlord 2':
                self.reload_map_after_running_from_final_form()
        stepped_back = outcome == BattleOutcome.ESCAPED and self.player_ran_away and self.step_back_after_running()
        if outcome != BattleOutcome.DEFEAT and current_battle.enemy.name != 'Dragonlord 2' and not stepped_back:
            self.face_down_after_fight()
        return outcome

    # ------------------------------------------------------------------ #
    #  The party (src/party.py)                                            #
    # ------------------------------------------------------------------ #

    def party_fallen(self) -> bool:
        """Whether every hero has fallen: the fight is lost (the one hero has, without a party)."""
        return not living(self.game)

    def hero_to_act(self):
        """The hero whose turn it is: the one the round has come to, or the first one standing."""
        standing = living(self.game)
        return self.turn_hero if self.turn_hero in standing else standing[0]

    def next_hero_acts(self) -> bool:
        """After a hero's action: whether another hero standing acts before the enemy this round (they're
        self.turn_hero then)."""
        standing = living(self.game)
        if self.player not in standing:
            return False
        later = standing[standing.index(self.player) + 1:]
        if not later:
            return False
        self.turn_hero = later[0]
        return True

    def enemy_target(self):
        """The hero the enemy acts against: the one hero, or one of the two standing, chosen with bit 0 of a random
        byte (not NES: the NES has one hero)."""
        standing = living(self.game)
        if len(standing) == 1:
            return standing[0]
        return standing[hero_random.randint(0, 255) & 1]

    def enemy_round(self, current_battle: Battle) -> bool:
        """The enemy's turn, against one of the heroes (enemy_target), ending the round: the next one starts from the
        first hero standing. A hero it brings to 0 HP has fallen. Returns True if the enemy ran away."""
        self.turn_hero = None
        # The enemy's turn is on player 1's joypad, whoever acted last (roaming apart, the fighting hero's player's)
        with acting(self.game, self.enemy_target()), \
                player_input(input_player() if free_roaming(self.game) else PLAYER_ONE):
            if self.enemy_move(current_battle):
                return True
            if self.player.current_hp <= 0:
                # 0 HP is always low: NES ChkLowHPPal's $26
                self.drawer.draw_hovering_stats_window(self.screen, self.player, LOW_HP_RED)
                self.player.is_dead = True
                if not self.party_fallen():
                    self.cmd_menu.show_line_in_dialog_box(self._("{} hath fallen.\n").format(self.player.name),
                                                          **BATTLE_LINE)
        return False

    def get_fallen_heroes_up(self) -> None:
        """A party's hero who fell in a fight that was won or fled gets back up with 1 HP (FALLEN HEROES on GET UP; not
        NES)."""
        for hero in heroes(self.game):
            if hero.is_dead:
                hero.is_dead = False
                hero.current_hp = max(hero.current_hp, 1)

    def face_down_after_fight(self) -> None:
        """NES ExitFight / ExitFight2 (LEE82): CharDirection = DIR_DOWN, so the hero faces down on the map after a win,
        after the enemy runs away (CheckEnRun) and after a normal run (RunSuccessful's ChkMapsDone). A run from a
        guardian (step_back_after_running) or from the Dragonlord's final form leaves through MapChng instead and keeps
        the old facing, and beating the final form goes on to the ending."""
        self.player.direction_value = Direction.DOWN.value

    def reload_map_after_running_from_final_form(self) -> None:
        """NES RunSuccessful (LE8B2-LE8D1): after running from the Dragonlord's final form, BlackPal is loaded at once,
        so the screen cuts to black with no fade out, then MapChngNoSound (Bank00, LB091) reloads the map and fades it
        in (PalFadeIn). The Dragonlord is still alive, so he is back on his throne."""
        tile_size = self.game.tile_size
        coordinates = self.player.rect.y // tile_size, self.player.rect.x // tile_size
        self.game.change_map(map_lookup[self.current_map.identifier](self.config), destination_coordinates=coordinates,
                             direction=self.player.direction_value, fade_out_first=False)

    def step_back_after_running(self) -> bool:
        """NES RunSuccessful (ChkMapHauksness, ChkMapSwampCave, ChkMapOverworld): after running from a guardian, the
        hero is moved one block back off its tile and the map is reloaded with the stairs sound (MapChngWithSound),
        so the guardian can't be slipped past and Erdrick's Armor can't be searched for. Returns whether it did."""
        tile_size = self.game.tile_size  # the fight may have started before row and column caught up with the rect
        coordinates = escape_coordinates(self.current_map.identifier,
                                         (self.player.rect.y // tile_size, self.player.rect.x // tile_size),
                                         self.game.story_flags)
        if coordinates is None:
            return False
        self.game.change_map(map_lookup[self.current_map.identifier](self.config),
                             destination_coordinates=coordinates, direction=self.player.direction_value,
                             stairs_sound=True)
        return True

    def start_fight(self, current_battle: Battle) -> bool:
        """NES InitFight, after the enemy appears (SetEnHP): CheckEnRun gives a much weaker enemy its chance to run
        away, then CalcWhoIsNext decides whether the enemy attacks before the hero is ready (StartEnemyTurn) or the
        hero gets the first turn. Returns True if the enemy ran away."""
        enemy = current_battle.enemy
        if self.enemy_runs(enemy):
            return self.enemy_run_away(current_battle, enemy)
        if player_acts_first(self.player.agility, enemy.defense, hero_random.randint(0, 255), hero_random.randint(0, 255)):
            return False
        self.cmd_menu.show_line_in_dialog_box(
            self._("The {} attacked before {} was ready.").format(self._(enemy.name), self.player.name),
            **BATTLE_LINE)  # TB15E4
        return self.enemy_round(current_battle)

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
        if self.player.is_asleep or not self.command_window_open:
            # The start of a player turn: auto-grind stops here if HP is low or the hero is asleep, so the command
            # window is the player's
            self.auto_grind.player_turn_starts()
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
            if self.auto_battle and not self.grinding:
                selected_executed_option = self.last_battle_action
                time.wait(scaled_ms(AUTO_BATTLE_DELAY_MS))
            else:
                next_frame()  # one pass of the fight loop per NES frame (src/selection.py)
                tapped = 0  # keys pressed since the last call, which may have been let go already
                for current_event in frame_events():  # quits if the window is closed; 1 to 5 only set the speed
                    if current_event.type == KEYDOWN:
                        if self.press_auto_grind(current_event):
                            continue
                        tapped |= key_joypad_buttons(current_event.key)
                presses = self.command_buttons.read(held_joypad_buttons(), tapped)  # WndGetButtons
                selected_executed_option = self.process_command_input(presses)

        if selected_executed_option:
            if selected_executed_option != 'Sleep':
                self.last_battle_action = selected_executed_option
                # WndAPressed: the chosen command's arrow is drawn once more and stays on while it runs
                self.command_cursor.hold()
                self.draw_command_window(True)
            if selected_executed_option in ('Fight', 'Run'):
                # PlyrFight (LE5FE), PlyrRun (LE886): RemoveWindow WND_CMD_CMB before anything is shown
                self.remove_command_window()
            match selected_executed_option:
                case 'Fight':
                    self.fight(current_battle)
                case 'Spell':
                    if not self.player.spells:
                        self.remove_command_window()  # PlyrSpell (LE6CB): no spells yet
                    # Otherwise the SPELL window is answered first (CommandMenu.display_item_menu removes both)
                    current_battle.battle_spell(self.cmd_menu, self.player, current_battle)
                case 'Run':
                    party = in_party_mode(self.game)
                    # In a party the round goes on after a blocked run: the other hero, then the enemy
                    run_away = current_battle.battle_run(self.cmd_menu, self.player, current_battle,
                                                         enemy_moves=not party)
                    if run_away:
                        # The enemy may have fled on its turn after the hero was blocked: that's no escape by the hero
                        self.player_ran_away = not current_battle.enemy_fled
                        return run_away
                    elif not party:
                        # enemy already attacked inside battle_run; skip the outer enemy turn
                        current_battle.no_op = True
                case 'Item':
                    if not self.player.inventory:
                        self.remove_command_window()  # PlyrItem (LE7B0): nothing to show
                        self.cmd_menu.show_line_in_dialog_box(self._('Nothing of use has yet been given to thee.\n'),
                                                              **BATTLE_LINE)  # TB4E13
                        current_battle.no_op = True
                    else:
                        self.cmd_menu.display_item_menu('inventory')
                case 'Sleep':
                    self.sleeping_player_turn(current_battle)
            current_battle.last_turn = current_battle.turn
            current_battle.turn += 1
            selected_executed_option = None
            # The next player turn opens the command window again, from FIGHT (StartPlayerTurn, WndInitSelect)
            self.command_window_open = False
            if current_battle.enemy.hp <= 0:
                return False
            elif current_battle.last_turn != current_battle.turn:
                # The next hero standing acts (a party: src/party.py), or the enemy, which ends the round
                if not current_battle.no_op and not self.next_hero_acts() and self.enemy_round(current_battle):
                    return True
                current_battle.no_op = False
        return run_away

    def press_auto_grind(self, current_event) -> bool:
        """G (AUTO_GRIND) at the command window, with the AUTO-GRIND option on: auto-grind takes over from this turn
        (AutoGrind.start_in_fight). Returns whether the key was G's. While auto-grind runs, G stops it before it gets
        here (AutoGrind.real_key)."""
        if not (pressed(current_event, 'AUTO_GRIND') and self.config.get('AUTO_GRIND')) or self.grinding:
            return False
        self.auto_grind.start_in_fight()
        return True

    def open_command_window(self) -> None:
        """StartPlayerTurn and ShowCmbtCmd (LE5EF): "Command?" (TextBlock15 entry 8), then Dowindow WND_CMD_CMB, whose
        WndDoSelect starts selecting afresh every turn. Every player turn comes through here: the first one (unless
        the enemy attacked first), after each enemy turn, after a message that takes no turn ("Thy MP is too low",
        "That cannot be used in battle", "cannot yet use the spell", "Nothing of use"), after B in this window or in
        SPELL or ITEM, and after the hero wakes (PlayerAwakes falls through into ShowCmbtCmd). The text ends with
        TXT_END1, so nothing waits for a button before the window opens.

        WndInitSelect puts the cursor back on FIGHT (WndCol = WndRow = 0), whatever was chosen last turn, and
        the joypad is read from scratch (SelectionButtons.open): the NES has no event queue, so keys pressed before
        the window was up (during the walk into the fight, the enemy's fade-in, "draws near", the enemy's turn,
        "Command?") are dropped, and keys still held are ignored until they are let go or 11 frames have gone by."""
        # A party (src/party.py): whose command it is
        prompt = self._("Command for {}?\n").format(self.player.name) if in_party_mode(self.game) \
            else self._("Command?\n")
        self.cmd_menu.show_line_in_dialog_box(prompt, add_quotes=False, skip_text=True, hide_arrow=True,
                                              disable_sound=True)
        self.battle_menu_row = 0
        self.battle_menu_column = 0
        poll_virtual_joypad()  # a key the player pressed stops auto-grind before the queue is dropped
        for queued_event in event.get(KEYDOWN):
            # the speed keys (1 to 5) and the zoom keys (src/zoom.py) still count; every other key is dropped
            handle_speed_key(queued_event) or handle_zoom_event(queued_event)
        self.command_buttons.open(held_joypad_buttons())
        self.command_window_open = True
        self.drawn_command_window = None
        # NES ShowWindow -> DoWindowPrep (Bank01, LAEFE -> DoBeepSFX LAF15): SFX_MENU_BTN for WND_CMD_CMB before the
        # window is built, every time ShowCmbtCmd opens it, after B too. The field COMMAND window does the same
        # (Drawer.handle_menu_launch).
        self.sound.play_sound(self.directories.menu_button_sfx)
        if not self.command_window_shown:
            # After B (WND_ABORT) it is still on the screen and is only drawn again
            self.command_window_covered = self.cmd_menu.covered_area(COMBAT_COMMAND_WINDOW)
            self.cmd_menu.window_drop_down_effect(*COMBAT_COMMAND_WINDOW)
            self.command_window_shown = True

    def remove_command_window(self) -> None:
        """NES RemoveWindow WND_CMD_CMB: once a command has been chosen (and its SPELL or ITEM window answered), the
        command window is taken off the screen and what it covered is put back, so it isn't there during the hero's
        action, the enemy's turn or while the hero sleeps. The next player turn opens it again."""
        if not self.command_window_shown:
            return
        self.cmd_menu.remove_window(COMBAT_COMMAND_WINDOW, self.command_window_covered)
        self.command_window_shown = False
        self.command_window_covered = None

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
            # JMP ShowCmbtCmd: "Command?" again and a new selection, from FIGHT (open_command_window, next frame).
            self.command_cursor.hold()
            self.draw_command_window(True)
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
        long the sleep can last. On waking, "<player> awakes." (TextBlock17 entry 8), which falls through into
        ShowCmbtCmd: "Command?" and the command window (open_command_window), so the hero takes this turn as usual.
        Otherwise "Thou art still asleep." (PlayerAsleepDialog) and the enemy takes its turn."""
        if coin_flip():
            self.player.is_asleep = False
            self.cmd_menu.show_line_in_dialog_box(self._("{} awakes.\n").format(self.player.name), **BATTLE_LINE)
            # The hero chooses a command next, so the enemy doesn't move this time round.
            current_battle.no_op = True
        else:
            self.cmd_menu.show_line_in_dialog_box(self.still_asleep_line(),
                                                  add_quotes=False, disable_sound=True,
                                                  hide_arrow=True, skip_text=True)

    def still_asleep_line(self) -> str:
        """PlayerAsleepDialog, naming the hero in a party (src/party.py)."""
        if in_party_mode(self.game):
            return self._("{} is still asleep.\n").format(self.player.name)
        return self._("Thou art still asleep.\n")

    def enemy_run_away(self, current_battle, enemy):
        """NES CheckEnRun: the enemy is erased (ClearSpriteRAM), SFX_RUN, "The ENMY is running away." (TB15E3, no WAIT),
        the map's music again (ResumeMusicTbl), then ExitFight: a new press returns to the map."""
        current_battle.make_enemy_image_disappear(self.screen)
        self.sound.play_sound(self.directories.run_away_sfx)  # NES LEFCB: SFX_RUN
        self.cmd_menu.show_line_in_dialog_box(self._("The {} is running away.").format(self._(enemy.name)),
                                              **BATTLE_LINE)
        self.music_player.load_and_play_music(self.current_map.music_file_path)
        self.cmd_menu.wait_for_button(shows_arrow=False)
        current_battle.enemy_fled = True
        return True

    # ------------------------------------------------------------------ #
    #  Hero attack                                                         #
    # ------------------------------------------------------------------ #

    def fight(self, current_battle):
        self.hero_attack(current_battle)

    def hero_attack(self, current_battle):
        self.sound.play_sound(self.directories.attack_sfx)
        self.cmd_menu.show_line_in_dialog_box(self._("{} attacks!\n").format(self.player.name), **BATTLE_LINE)  # TB15E5
        attack_damage = current_battle.calculate_attack_damage(self.cmd_menu, self.player, current_battle.enemy)
        if attack_damage <= 0:
            current_battle.missed_attack(self.cmd_menu)
        elif not current_battle.enemy.is_asleep and self.enemy_dodges_attack(current_battle.enemy):
            # NES SetEnDmg1: a sleeping enemy can't dodge (excellent moves can be dodged too)
            self.sound.play_sound(self.directories.missed_sfx)
            self.cmd_menu.show_line_in_dialog_box(self._("It is dodging!"), **BATTLE_LINE)  # TB17E10
        else:
            self.sound.play_sound(self.directories.hit_sfx)
            # NES PlyrHitEn: the enemy flashes red (PaletteFlash) before the damage text
            self.drawer.flash_enemy(self.screen, current_battle.enemy.name)
            # NES TextBlock15 entry 6: PNTS prints "Point" for 1 damage (Bank01 DoPNTS)
            self.cmd_menu.show_line_in_dialog_box(
                singular_or_plural(attack_damage, self._("The {}'s Hit Point have been reduced by {}.\n"),
                                   self._("The {}'s Hit Points have been reduced by {}.\n")).format(
                    self._(current_battle.enemy.name), attack_damage), **BATTLE_LINE)
            current_battle.enemy.hp -= attack_damage

    def enemy_runs(self, enemy) -> bool:
        """NES CheckEnRun: whether the enemy runs away. It only rolls (UpdateRandNum) when the hero's strength / 2 is
        at least the enemy's attack, so against a stronger enemy no random number is used."""
        if self.player.strength // 2 < enemy.attack:
            return False
        return enemy_flees(self.player.strength, enemy.attack, hero_random.randint(0, 255))

    @staticmethod
    def enemy_dodges_attack(enemy) -> bool:
        """NES SetEnDmg1: the dodge roll keeps 6 bits of RandNumUB and writes them back (STA RandNumUB), so with the
        NES's random number the numbers after it follow from the masked byte."""
        roll = hero_random.randint(0, 255) & 0x3F
        hero_random.store_upper_byte(roll)
        return enemy_dodges(enemy.dodge, roll)

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
            self.cmd_menu.show_line_in_dialog_box(self.still_asleep_line(), add_quotes=False,
                                                  disable_sound=True, hide_arrow=True, skip_text=True)

    def enemy_turn(self, current_battle: Battle) -> bool:
        """One enemy turn (NES StartEnemyTurn). Returns True if the enemy ran away."""
        enemy = current_battle.enemy
        # NES StartEnemyTurn: a sleeping enemy rolls 2 bits of RandNumUB, again while they're 0, and wakes on 1 (1 time
        # in 3) to act at once; otherwise it stays asleep and the player gets another turn.
        if enemy.is_asleep:
            while (wake_roll := hero_random.randint(0, 255) & 0x03) == 0:
                pass
            if wake_roll != 1:
                self.cmd_menu.show_line_in_dialog_box(self._("The {} is asleep.").format(self._(enemy.name)),
                                                      **BATTLE_LINE)  # TB16E8
                return False
            enemy.is_asleep = False
            self.cmd_menu.show_line_in_dialog_box(self._("{} hath woken up.").format(self._(enemy.name)),
                                                  **BATTLE_LINE)  # TB1E0
        # NES DoEnemyAttack calls CheckEnRun first: an enemy facing a hero with at least double its attack in
        # strength has a 1 in 4 chance to run away.
        if self.enemy_runs(enemy):
            return self.enemy_run_away(current_battle, enemy)
        # Rebuild the pattern so HP-based conditions (e.g. HEAL) reflect damage taken this turn.
        enemy.refresh_pattern()
        spell = self.choose_enemy_spell(enemy)
        if spell is None:
            self.enemy_attack(current_battle)
        else:
            self.cast_enemy_spell(current_battle, spell)
        return False

    def choose_enemy_spell(self, enemy) -> str | None:
        """NES DoEnemyAttack, after CheckEnRun: the spell the enemy casts this turn, or None to attack. A roll for its
        upper spell (SLEEP, STOPSPELL, HEAL or HEALMORE): cast when bits 4-5 of RandNumUB are below the spell's chance
        in quarters (EnSpell bits 4-5) and the spell would do something (the hero isn't asleep or stopspelled already,
        the enemy's HP is down to a quarter for a heal); if not, a roll for its lower spell (HURT, HURTMORE or fire)
        on bits 0-1 (EnSpell bits 0-1). Both rolls are made whatever the enemy knows, so one with no spells rolls
        twice before it attacks."""
        upper, lower = enemy_spell_slots(enemy.pattern)
        upper_roll = (hero_random.randint(0, 255) & 0x30) >> 4
        if upper is not None and upper_roll < chance_in_quarters(upper) and self.enemy_may_cast(upper):
            return upper[1]
        lower_roll = hero_random.randint(0, 255) & 0x03
        if lower is not None and lower_roll < chance_in_quarters(lower) and self.enemy_may_cast(lower):
            return lower[1]
        return None

    def enemy_may_cast(self, slot: tuple) -> bool:
        """Whether the spell would do something: its pattern entry's condition (HEAL's and HEALMORE's HP), and the
        hero not already asleep (SLEEP) or stopspelled (STOPSPELL)."""
        _, spell, condition = slot
        if spell == Spell.SLEEP and self.player.is_asleep:
            return False
        if spell == Spell.STOPSPELL and self.player.is_stopspelled:
            return False
        return bool(condition)

    def cast_enemy_spell(self, current_battle, current_spell) -> None:
        """NES EnCastSpell and the spell's own routine (EnCastSleep, EnCastHurt, ...)."""
        enemy = current_battle.enemy
        if current_spell not in (Spell.FIREBREATH, Spell.FIREBREATH2):
            # TB16E12 and TB16E13, both with no WAIT
            self.cmd_menu.show_line_in_dialog_box(
                self._("{} chants the spell of {}.").format(self._(enemy.name), self._(current_spell)),
                **BATTLE_LINE)
            # NES EnCastSpell (LEBFE-LEC11): SFX_SPELL, the enemy flashes grey (PaletteFlash with
            # SplFlshBGPal), then WaitForMusicEnd lets the spell sound finish
            self.sound.play_sound(self.directories.spell_sfx)
            self.drawer.flash_enemy_spell(self.screen, enemy.name)
            self.sound.wait_for_sfx_end(SPELL_SFX_FRAMES, self.config)
        else:
            # NES DoFireSFX (LED14): SFX_FIRE starts before "is breathing fire", and nothing waits for it:
            # PlayerHit's SFX_PLYR_HIT1 cuts it off
            self.sound.play_sound(self.directories.breathe_fire_sfx)
            self.cmd_menu.show_line_in_dialog_box(
                self._("The {} is breathing fire.\n").format(self._(enemy.name)), **BATTLE_LINE)  # TB16E15
        if enemy.is_stopspelled and current_spell not in (Spell.FIREBREATH, Spell.FIREBREATH2):
            # NES: a stopspelled enemy still chants, but the spell is blocked (fire breath isn't a spell)
            self.cmd_menu.show_line_in_dialog_box(self._("But that spell hath been blocked."),
                                                  **BATTLE_LINE)  # TB15E10
            return
        # The HP the spell takes or gives: AND #$07 or #$0F of RandNumUB, plus the spell's least (EnCastHurt, ...).
        # SLEEP and STOPSPELL roll nothing here (STOPSPELL's own roll is below).
        lowest, highest = enemy_spell_lookup[current_spell]
        spell_effect = hero_random.randint(lowest, highest) if highest else 0
        match current_spell:
            case Spell.HEAL | Spell.HEALMORE:
                # NES EnemyAddHP: capped at the enemy's base HP
                enemy.recover_hp(spell_effect)
                self.cmd_menu.show_line_in_dialog_box(
                    self._("The {} hath recovered.").format(self._(enemy.name)), **BATTLE_LINE)  # TB17E9
            case Spell.SLEEP:
                # NES EnCastSleep: always works; the enemy moves again straight away (see enemy_move)
                self.player.is_asleep = True
                self.player_fell_asleep = True
                line = self._("{} is asleep.\n").format(self.player.name) if in_party_mode(self.game) \
                    else self._("Thou art asleep.\n")
                self.cmd_menu.show_line_in_dialog_box(line, **BATTLE_LINE)  # TB17E6
            case Spell.HURT | Spell.HURTMORE:
                if self.player.armor in ("Magic Armor", "Erdrick's Armor"):
                    spell_effect = spell_effect // 3 * 2  # NES: divide by 3, then double
                self.game.hero_damage.receive_damage(spell_effect)
            case Spell.STOPSPELL:
                # NES EnCastStopspell: Erdrick's Armor always blocks it; otherwise it works when bit 0 of a
                # random byte is set (50%). It lasts for the rest of the fight.
                if self.player.armor != "Erdrick's Armor" and coin_flip():
                    self.player.is_stopspelled = True
                    message = self._("{}'s spell is blocked.").format(self.player.name)
                else:
                    message = self._("The spell will not work.")
                self.cmd_menu.show_line_in_dialog_box(message, **BATTLE_LINE)  # TB16E14 or TB15E11
                if self.player.is_stopspelled:
                    self.auto_grind.stopspell_hit()
            case Spell.FIREBREATH | Spell.FIREBREATH2:
                if self.player.armor == "Erdrick's Armor":
                    spell_effect = spell_effect // 3 * 2  # NES: divide by 3, then double
                self.game.hero_damage.receive_damage(spell_effect)

    def enemy_attack(self, current_battle):
        self.enemy_attack_message(current_battle.enemy)
        self.execute_enemy_attack(current_battle)

    def execute_enemy_attack(self, current_battle):
        attack_damage = calculate_enemy_attack_damage(self.player, current_battle.enemy)
        if attack_damage <= 0:
            current_battle.enemy_missed_attack(self.cmd_menu)
        else:
            self.game.hero_damage.receive_damage(attack_damage)

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
                                              **BATTLE_LINE)  # TB16E9
