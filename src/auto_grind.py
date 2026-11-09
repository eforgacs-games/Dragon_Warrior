"""Auto-grind: G on the map walks back and forth and fights until a decision is the player's to make. Not NES.

G starts it when START or the COMMAND window would be accepted on the map (MapHotkeys.press_auto_grind, resolved
with the pause and the options overlay in MovementController.resolve_pending_freezes), on a map with random fights,
with HP above the GRIND STOP threshold and a safe tile next to the hero (``safe_partner``). It then drives the game
with a virtual joypad (src/virtual_joypad.py), so everything runs through the game's own code: the walking, the
encounter rolls, the step effects, every window and wait.

- On the map it holds the direction from the hero's tile to the partner tile and back, at walking speed.
- Anywhere else (a fight, its dialog lines, the victory wait, a message) it taps A every TAP_PERIOD_FRAMES frames,
  which chooses FIGHT in the battle's command window (the cursor starts on FIGHT every turn) and moves every dialog
  on. F4 auto-battle is ignored meanwhile (BattleController.handle_battle_prompts).

G also starts it at the battle's command window (BattleController.handle_battle_prompts), but in a scripted fight
(``start_in_fight``): it fights on from that turn, then paces from the hero's tile.

HP at or below the GRIND STOP option's line (AUTO_GRIND_STOP; DANGER works it out from the monsters:
src/grind_safety.py) is checked at the start of every player turn (``player_turn_starts``, so the battle's command
window is the player's), after every fight (``after_fight``) and after every step (``after_step``). With AUTO-HEAL
(AUTO_HEAL) on it then heals (``heal_or_stop``): it steers the windows to HEAL or HEALMORE with the virtual joypad as
the player would (``steer_heal``: SPELL in the battle's command window, or A then SPELL in the COMMAND window on the
map, then the spell in the SPELL window), and checks again after the spell, until HP is out of danger. The spell and
when to cast it are src/grind_safety.py choose_heal's.

With AUTO-INN (AUTO_INN) on, when it can't go on on the map (HP low with no heal to cast, or with AUTO-HEAL on no MP
left for a heal), it walks to the nearest inn it can pay for, stays the night and walks back (src/inn_trip.py), then
paces again.

It stops, with the menu button sound and a message saying why, and hands the game back on the screen it is at:
- HP at or below the line, with no heal to cast (AUTO-HEAL off, no healing spell, MP too low or kept in reserve, or
  in a fight no heal that surely gets HP out of danger) and no trip to an inn (AUTO-INN off, in a fight, or no inn it
  can pay for and get to: NO_INN), or on the way to one where fights can start;
- the hero asleep at the start of a turn, or STOPSPELL working on the hero (``stopspell_hit``);
- a scripted fight, a guardian or the Dragonlord (``scripted_fight_starts``), before its first command;
- a level up (``level_up``), before the promotion and the stat lines, which wait for the player; G goes on;
- any key the player presses (G included) but the game speed keys 1 to 5 and the zoom keys (``real_key``);
- the hero dying, or being somewhere he wasn't walking to (a map change), without a message for a death;
- an inn trip that loses its way (LOST: no way back, or TALK or STAIRS that keep doing nothing).
"""
from enum import Enum
from typing import TYPE_CHECKING

from pygame import K_CAPSLOCK, K_LALT, K_LCTRL, K_LGUI, K_LSHIFT, K_MODE, K_NUMLOCK, K_RALT, K_RCTRL, K_RGUI, \
    K_RSHIFT, KMOD_CTRL
from pygame.event import Event

from src.color import is_low_hp
from src.common import A_BUTTON_KEYS, D_PAD_KEYS
from src.controls import first_binding
from src.direction import Direction
from src.coordinates import Cell
from src.windows import COMMAND_ROWS
from src.encounters import ENEMY_GROUPS, encounter_group
from src.enemy_lookup import enemy_string_lookup
from src.grind_route import RouteMaps
from src.grind_safety import HERO_HEALS, choose_heal, heal_reserve, worst_enemy_damage, worst_group_damage
from src.inn_trip import InnTrip, TripResult
from src.guardians import guardian_at
from src.movement import DIRECTION_KEYS
from src.npc_movement import step
from src.game_options import AUTO_GRIND_STOP_VALUES, AUTO_HEAL_KEEP_ONE, AUTO_HEAL_OFF, ENCOUNTERS_OFF
from src.menu import COMMAND_METHODS
from src.spells import Spell
from src.virtual_joypad import VirtualJoypad
from src.waiting import MAP_CONTEXT, requested_speed

if TYPE_CHECKING:
    from src.game import Game  # src.game imports this module

# The GRIND STOP option (src/options_overlay.py, AUTO_GRIND_STOP): when HP is low enough to stop. RED HP is the NES's
# low HP, where the windows turn red (ChkLowHPPal): HP <= max HP / 4 + 1. HALF HP: HP <= max HP / 2. 3/4 HP:
# HP <= max HP * 3 / 4. DANGER: from what the monsters can do (src/grind_safety.py).
GRIND_STOP_RED_HP, GRIND_STOP_HALF_HP, GRIND_STOP_THREE_QUARTERS_HP, GRIND_STOP_DANGER = AUTO_GRIND_STOP_VALUES

TAP_HOLD_FRAMES = 2  # an A tap is held this long
TAP_PERIOD_FRAMES = 8  # and one starts this often
# Keys that don't count as "any key": the modifiers on their own (Ctrl for the zoom keys, say)
MODIFIER_KEYS = frozenset((K_LSHIFT, K_RSHIFT, K_LCTRL, K_RCTRL, K_LALT, K_RALT, K_LGUI, K_RGUI, K_CAPSLOCK,
                           K_NUMLOCK, K_MODE))

# The hero never paces onto these: they hurt (swamp, force field) or take him off the map (stairs)
UNSAFE_TILES = frozenset(('MARSH', 'BARRIER', 'BRICK_STAIR_DOWN', 'BRICK_STAIR_UP', 'GRASS_STAIR_DOWN'))
# Every direction key, as bound now
ALL_DIRECTION_KEYS = D_PAD_KEYS
# The order the partner tile is looked for in, after the direction the hero faces
PARTNER_ORDER = tuple(direction for direction, _keys in DIRECTION_KEYS)
# Where SPELL is: in the COMMAND window (its entry, src/windows.py COMMAND_ENTRIES order) and in the battle's command
# window (row, column: BattleController BATTLE_MENU_OPTIONS)
COMMAND_SPELL_ENTRY = COMMAND_METHODS.index('spell')
BATTLE_SPELL_CELL = (0, 1)


def a_key() -> int:
    """The key auto-grind taps for A: the A button's first key (src/controls.py)."""
    binding = first_binding('A')
    return binding.key if binding is not None else A_BUTTON_KEYS[0]


def first_binding_key(action: str) -> int | None:
    binding = first_binding(action)
    return binding.key if binding is not None else None


def walk_key_for(direction: int) -> int:
    """The key auto-grind holds to walk this way: the direction's first key."""
    return next(keys[0] for walking, keys in DIRECTION_KEYS if walking == direction)


def at_grind_stop_hp(current_hp: int, max_hp: int, setting: str | None) -> bool:
    """Whether HP is at or below the GRIND STOP threshold (RED HP for any other setting but DANGER, which
    AutoGrind.hp_line works out)."""
    return current_hp <= fraction_line(max_hp, setting)


def fraction_line(max_hp: int, setting: str | None) -> int:
    """The highest HP that is low for a GRIND STOP setting that is a part of max HP (RED HP for any other)."""
    if setting == GRIND_STOP_HALF_HP:
        return max_hp // 2
    if setting == GRIND_STOP_THREE_QUARTERS_HP:
        return max_hp * 3 // 4
    return next(hp for hp in range(max_hp, -1, -1) if is_low_hp(hp, max_hp))


class StopReason(Enum):
    HP_LOW = 'hp low'
    MP_LOW = 'mp low'
    ASLEEP = 'asleep'
    STOPSPELL = 'stopspell'
    SCRIPTED_FIGHT = 'scripted fight'
    LEVEL_UP = 'level up'
    KEY = 'key'
    INTERRUPTED = 'interrupted'
    DEATH = 'death'
    NO_INN = 'no inn'
    LOST = 'lost'


# The stops that hand a fight back to the player because it has turned dangerous (or special): auto-battle (F4, a
# cheat) is turned off with them, or it would pick the last command again the moment auto-grind lets go, and the
# COMMAND window wouldn't really be the player's
SAFETY_STOPS = frozenset({StopReason.HP_LOW, StopReason.MP_LOW, StopReason.ASLEEP, StopReason.STOPSPELL,
                          StopReason.SCRIPTED_FIGHT, StopReason.NO_INN, StopReason.LOST})
TRIP_STOPS = {TripResult.NO_INN: StopReason.NO_INN, TripResult.LOST: StopReason.LOST}


class AutoGrind:
    """Auto-grind for one game (see the module docstring); the virtual joypad's driver."""

    def __init__(self, game: 'Game') -> None:
        self.game = game
        self.joypad = VirtualJoypad(self)
        self.map_identifier: str | None = None
        self.origin: Cell | None = None  # the hero's tile when it started
        self.partner: Cell | None = None  # the safe tile next to it
        self.next_tap_frame = 0
        self.last_stop: StopReason | None = None
        # A stop message waiting to be shown at the next safe point: the next map frame or player turn
        self.pending_message: str | None = None
        # The healing spell AUTO-HEAL is steering the windows to, until it is chosen in the SPELL window
        self.heal_spell: Spell | None = None
        # AUTO-INN: the trip under way, the maps its routes have loaded (kept for the game), and whether a trip for MP
        # found no inn since auto-grind started (it grinds on until HP is low, without looking again every fight)
        self.trip: InnTrip | None = None
        self.route_maps: RouteMaps | None = None
        self.no_inn_for_mp = False

    @property
    def active(self) -> bool:
        return self.joypad.connected

    # Starting and stopping

    def hero_cell(self) -> Cell:
        """The hero's (row, column), from the sprite: a step that has just ended hasn't updated row and column yet."""
        tile_size = self.game.tile_size
        return self.game.player.rect.y // tile_size, self.game.player.rect.x // tile_size

    def hp_line(self, in_fight: bool) -> int:
        """The highest HP that is low (GRIND STOP): a part of max HP, or with DANGER what the enemy's next turn can
        take off in a fight, and twice what any enemy that fights here can on the map (src/grind_safety.py)."""
        player = self.game.player
        setting = self.game.game_state.config.get('AUTO_GRIND_STOP')
        if setting != GRIND_STOP_DANGER:
            return fraction_line(player.max_hp, setting)
        battle = self.game.cmd_menu.current_battle
        if in_fight and battle is not None:
            return worst_enemy_damage(battle.enemy, player.defense_power, player.armor)
        return 2 * worst_group_damage(self.enemies_here(), player.defense_power, player.armor)

    def enemies_here(self) -> set[str]:
        """The enemies that can fight the hero where he paces (or stands, before he starts): both tiles, as they can be
        in two zones of the overworld."""
        cells = [cell for cell in (self.origin, self.partner) if cell is not None] \
            if self.active and self.trip is None else []
        identifier = self.game.current_map.identifier
        groups = {encounter_group(identifier, column, row) for row, column in cells or [self.hero_cell()]}
        return {name for group in groups if group is not None for name in ENEMY_GROUPS[group]
                if name in enemy_string_lookup}

    def hp_low(self, in_fight: bool = False) -> bool:
        return self.game.player.current_hp <= self.hp_line(in_fight)

    def heal_choice(self, in_fight: bool) -> Spell | None:
        """The spell AUTO-HEAL casts now, or None (src/grind_safety.py choose_heal)."""
        setting = self.game.game_state.config.get('AUTO_HEAL', AUTO_HEAL_OFF)
        player = self.game.player
        if setting == AUTO_HEAL_OFF or (in_fight and player.is_stopspelled):
            return None
        # KEEP 1 HEAL keeps its HEAL for the way to the inn: on the way, it's spent
        keep_one = setting == AUTO_HEAL_KEEP_ONE and self.trip is None
        return choose_heal(player.spells, player.current_mp, player.current_hp, player.max_hp, self.hp_line(in_fight),
                           heal_reserve(player.spells, keep_one), in_fight)

    def out_of_heals(self) -> bool:
        """With AUTO-HEAL on: the hero has a healing spell, but not the MP for one (above the reserve)."""
        setting = self.game.game_state.config.get('AUTO_HEAL', AUTO_HEAL_OFF)
        player = self.game.player
        known = [spell for spell in HERO_HEALS if spell in player.spells]
        reserve = heal_reserve(player.spells, setting == AUTO_HEAL_KEEP_ONE)
        return (setting != AUTO_HEAL_OFF and bool(known) and
                all(player.current_mp - HERO_HEALS[spell][0] < reserve for spell in known))

    def heal_or_stop(self, in_fight: bool) -> None:
        """HP is low: heal (steer_heal), or stop. MP LOW when AUTO-HEAL is on and a heal would do with more MP."""
        self.heal_spell = self.heal_choice(in_fight)
        if self.heal_spell is not None:
            return
        if not in_fight and self.trip is None and self.start_trip():
            return
        if self.inn_lets_it_go_on(in_fight):
            return
        player = self.game.player
        mp_short = (self.game.game_state.config.get('AUTO_HEAL', AUTO_HEAL_OFF) != AUTO_HEAL_OFF and
                    not (in_fight and player.is_stopspelled) and
                    choose_heal(player.spells, player.max_mp, player.current_hp, player.max_hp,
                                self.hp_line(in_fight), 0, in_fight) is not None)
        self.stop(StopReason.MP_LOW if mp_short else StopReason.HP_LOW)

    def inn_lets_it_go_on(self, in_fight: bool) -> bool:
        """With AUTO-INN on, HP low with no heal doesn't stop auto-grind while one enemy turn can't end it: in a fight
        it fights on (the trip starts on the map after it), and on the way to the inn it walks on (in a town, always).
        The worst hit is src/grind_safety.py's, whatever GRIND STOP says."""
        if not self.game.game_state.config.get('AUTO_INN'):
            return False
        player = self.game.player
        battle = self.game.cmd_menu.current_battle
        if in_fight:
            return battle is not None and player.current_hp > worst_enemy_damage(battle.enemy, player.defense_power,
                                                                                  player.armor)
        if self.trip is None:
            return False
        return player.current_hp > worst_group_damage(self.enemies_here(), player.defense_power, player.armor)

    def has_random_fights(self) -> bool:
        """Whether a step here can start a random fight (FieldEncounters.roll_for_fight): a map with an encounter
        group, and the Dragonlord alive (ChkOtherBlocks)."""
        row, column = self.hero_cell()
        return (not self.game.story_flags.dragonlord_defeated and
                encounter_group(self.game.current_map.identifier, column, row) is not None)

    def start(self, in_fight: bool = False) -> bool:
        """G on the map, once the hero and the NPCs are on their tiles, or at the battle's command window
        (start_in_fight). Returns whether auto-grind started. With HP already low, it starts if AUTO-HEAL has a heal
        to cast, and casts it first."""
        if self.active:
            return False
        _ = self.game._
        if self.game.game_state.config.get('NO_BATTLES'):
            # dev_config's NO_BATTLES: no step starts a fight, so it would only walk back and forth
            self.show(_("Auto-grind: battles are off (NO_BATTLES)"))
            return False
        if self.game.game_state.config.get('ENCOUNTERS') == ENCOUNTERS_OFF:
            # the ENCOUNTERS option on OFF: the same, from the options overlay
            self.show(_("Auto-grind: ENCOUNTERS are off"))
            return False
        if not self.has_random_fights():
            self.show(_("Auto-grind: no fights here"))
            return False
        hp_low = self.hp_low(in_fight)
        heal = self.heal_choice(in_fight) if hp_low else None
        origin = self.hero_cell()
        partner = self.safe_partner(origin)
        # With HP low and no heal, off to the inn at once, if AUTO-INN is on and there is one (on the map)
        trip = self.new_trip(origin) if hp_low and heal is None and not in_fight and partner is not None else None
        if hp_low and heal is None and trip is None:
            self.show(_("Auto-grind: HP is already low"))
            return False
        if partner is None:
            self.show(_("Auto-grind: no safe tile to walk to"))
            return False
        self.map_identifier = self.game.current_map.identifier
        self.origin, self.partner = origin, partner
        self.last_stop = None
        self.pending_message = None
        self.heal_spell = heal
        self.trip = trip
        self.no_inn_for_mp = False
        self.show(_("Auto-grind on\n(G or any key to stop)") if trip is None else _("Auto-grind: off to the inn"))
        self.next_tap_frame = 0
        self.joypad.connect()
        return True

    # AUTO-INN (src/inn_trip.py)

    def new_trip(self, home: Cell) -> InnTrip | None:
        """A trip to the nearest inn and back to home on this map, if AUTO-INN is on and there is a way to one."""
        if not self.game.game_state.config.get('AUTO_INN'):
            return None
        if self.route_maps is None:
            self.route_maps = RouteMaps(self.game)
        trip = InnTrip(self, (self.game.current_map.identifier, home), self.route_maps)
        return trip if trip.plan() else None

    def start_trip(self) -> bool:
        """Off to the inn from where auto-grind paces (heal_or_stop, after_fight). Returns whether the trip started."""
        assert self.origin is not None
        self.trip = self.new_trip(self.origin)
        if self.trip is None:
            return False
        self.heal_spell = None
        self.show(self.game._("Auto-grind: off to the inn"))
        return True

    def back_home(self) -> None:
        """The trip is over, on the tile auto-grind started on: pace again, with the partner tile if nobody is on it."""
        self.trip = None
        assert self.origin is not None
        if self.partner is None or not self.safe_tile(self.partner):
            self.partner = self.safe_partner(self.origin)
            if self.partner is None:
                self.stop(StopReason.LOST)

    def start_in_fight(self) -> bool:
        """G at the battle's command window (BattleController.handle_battle_prompts): auto-grind takes over from this
        turn, unless the fight is a scripted one (a guardian, the Dragonlord). Returns whether it started."""
        if self.game.battle_ctrl.special_fight:
            self.show(self.game._("Auto-grind: not in this fight"))
            return False
        return self.start(in_fight=True)

    def stop(self, reason: StopReason, show_now: bool = True) -> None:
        """Hand the game back where it is: let go of every key, play the menu button sound and say why (at once, or
        at the next safe point). A stop for safety (SAFETY_STOPS) turns auto-battle off too."""
        if not self.active:
            return
        self.joypad.disconnect()
        self.last_stop = reason
        self.heal_spell = None
        self.trip = None
        if reason in SAFETY_STOPS:
            self.game.auto_battle = False
        if reason == StopReason.DEATH:
            return
        self.game.sound.play_sound(self.game.directories.menu_button_sfx)
        message = self.stop_message(reason)
        if show_now:
            self.show(message)
        else:
            self.pending_message = message

    def stop_message(self, reason: StopReason) -> str:
        _ = self.game._
        match reason:
            case StopReason.HP_LOW:
                return _("Auto-grind stopped: HP low")
            case StopReason.MP_LOW:
                return _("Auto-grind stopped: MP too low to heal")
            case StopReason.ASLEEP:
                return _("Auto-grind stopped: asleep")
            case StopReason.STOPSPELL:
                return _("Auto-grind stopped: STOPSPELL")
            case StopReason.SCRIPTED_FIGHT:
                return _("Auto-grind stopped: special fight")
            case StopReason.LEVEL_UP:
                return _("Auto-grind stopped: level up\n(G to go on)")
            case StopReason.NO_INN:
                return _("Auto-grind stopped: no inn to go to")
            case StopReason.LOST:
                return _("Auto-grind stopped: lost the way")
        return _("Auto-grind stopped")

    def show(self, message: str) -> None:
        """A line in the battle's dialog window during a fight, otherwise a message over the map for a second."""
        cmd_menu = self.game.cmd_menu
        if cmd_menu.current_battle is not None:
            cmd_menu.show_line_in_dialog_box(message + '\n', add_quotes=False, hide_arrow=True, disable_sound=True,
                                             skip_text=True)
        else:
            self.game.draw_temporary_text(message)

    def show_pending(self) -> None:
        if self.pending_message is not None:
            message, self.pending_message = self.pending_message, None
            self.show(message)

    # The game's checks (see the module docstring)

    def player_turn_starts(self) -> None:
        """The start of a player turn in a fight (BattleController.handle_battle_prompts)."""
        self.show_pending()
        if not self.active:
            return
        if self.game.player.is_asleep:
            self.stop(StopReason.ASLEEP)
        elif self.hp_low(in_fight=True):
            self.heal_or_stop(in_fight=True)
        else:
            self.heal_spell = None  # a heal chosen at an earlier turn that was never cast (the enemy fled, say)

    def stopspell_hit(self) -> None:
        self.stop(StopReason.STOPSPELL)

    def scripted_fight_starts(self) -> None:
        self.stop(StopReason.SCRIPTED_FIGHT)

    def level_up(self) -> None:
        # The fight is about to end: the message waits for the map
        self.stop(StopReason.LEVEL_UP, show_now=False)

    def after_fight(self) -> None:
        if self.game.player.current_hp <= 0:
            self.hero_died()  # the death comes next, with no message from auto-grind
            return
        self.heal_spell = None  # the fight's heal, if it never came to it: the map's line decides now
        if self.active and self.hp_low():
            self.heal_or_stop(in_fight=False)
        elif self.active and self.trip is None and not self.no_inn_for_mp and self.out_of_heals():
            # No MP left for a heal: to the inn while HP is still good, or grind on until it isn't
            self.no_inn_for_mp = not self.start_trip()

    def after_step(self) -> None:
        if self.active and self.heal_spell is None and self.hp_low():
            self.heal_or_stop(in_fight=False)

    def hero_died(self) -> None:
        self.stop(StopReason.DEATH)

    # Pacing

    def safe_tile(self, cell: Cell, check_characters: bool = True) -> bool:
        """Whether the hero can pace onto this (row, column) without harm or leaving: passable, no swamp, force field or
        stairs, no map change or exit, no guardian, and nobody standing there or stepping onto or off it."""
        current_map = self.game.current_map
        row, column = cell
        if not (0 <= row < len(current_map.layout) and 0 <= column < len(current_map.layout[0])):
            return False
        tile = current_map.get_tile_by_value(current_map.layout[row][column])
        if tile in current_map.impassable_tiles or tile in UNSAFE_TILES or cell in current_map.staircases:
            return False
        if current_map.is_step_warp(row, column) or current_map.is_map_exit(row, column):
            return False
        if guardian_at(current_map.identifier, cell, self.game.story_flags) is not None:
            return False
        if check_characters:
            for character in (*current_map.fixed_characters, *current_map.roaming_characters):
                if cell in ((character.row, character.column), character.step_origin, character.step_destination):
                    return False
        return True

    def safe_partner(self, origin: Cell) -> Cell | None:
        """The tile to pace to and from: the first safe neighbour, looking the way the hero faces first, or None (also
        when the hero's own tile isn't safe to come back to)."""
        if not self.safe_tile(origin, check_characters=False):
            return None
        facing = self.game.player.direction_value
        for direction in (facing, *(direction for direction in PARTNER_ORDER if direction != facing)):
            neighbour = step(*origin, direction)
            if self.safe_tile(neighbour):
                return neighbour
        return None

    @staticmethod
    def direction_between(start: Cell, end: Cell) -> int | None:
        for direction in PARTNER_ORDER:
            if step(*start, direction) == end:
                return direction
        return None

    # The virtual joypad's driver

    def update(self, joypad: VirtualJoypad, context: str) -> None:
        if context == MAP_CONTEXT:
            self.walk(joypad)
        else:
            joypad.release_all(ALL_DIRECTION_KEYS & joypad.held)
            self.tap(joypad, self.heal_key() if self.heal_spell is not None else a_key())

    def tap(self, joypad: VirtualJoypad, tapped_key: int | None) -> None:
        """Tap a key, if it's time for the next tap (one every TAP_PERIOD_FRAMES)."""
        if tapped_key is not None and joypad.now >= self.next_tap_frame:
            joypad.tap(tapped_key, TAP_HOLD_FRAMES)
            self.next_tap_frame = joypad.now + TAP_PERIOD_FRAMES

    # Healing (AUTO-HEAL)

    def heal_key(self) -> int | None:
        """The key that takes the windows one step closer to casting heal_spell (see the module docstring), or None
        to wait (the COMMAND window on its way). A once the cursor is on it; heal_spell is then cast."""
        cmd_menu = self.game.cmd_menu
        assert self.heal_spell is not None
        selection = cmd_menu.item_menu_selection
        if selection is not None:
            menu_name, index = selection
            if menu_name != 'spells':
                return first_binding_key('B')  # not the SPELL window (the ITEM window): back out of it
            target = list(self.game.player.spells).index(self.heal_spell)
            if index != target:
                return walk_key_for(Direction.DOWN.value if index < target else Direction.UP.value)
            self.heal_spell = None  # chosen: the spell is cast, and HP is checked again after it
            return a_key()
        battle_ctrl = self.game.battle_ctrl
        if cmd_menu.current_battle is not None:
            if not battle_ctrl.command_window_open:
                return a_key()  # a battle line waiting for a press
            return self.cursor_key((battle_ctrl.battle_menu_row, battle_ctrl.battle_menu_column), BATTLE_SPELL_CELL)
        command_window = cmd_menu.menu
        if command_window.is_enabled():
            return self.cursor_key((command_window.row, command_window.column),
                                   (COMMAND_SPELL_ENTRY % COMMAND_ROWS, COMMAND_SPELL_ENTRY // COMMAND_ROWS))
        if self.game.cmd_menu_requested or cmd_menu.launch_signaled:
            return None  # the COMMAND window is opening
        return a_key()

    @staticmethod
    def cursor_key(cell: tuple[int, int], target: tuple[int, int]) -> int:
        """The direction key that moves a window's cursor from (row, column) towards target, or A on it."""
        (row, column), (target_row, target_column) = cell, target
        if row != target_row:
            return walk_key_for(Direction.UP.value if row > target_row else Direction.DOWN.value)
        if column != target_column:
            return walk_key_for(Direction.LEFT.value if column > target_column else Direction.RIGHT.value)
        return a_key()

    def heal_on_the_map(self, joypad: VirtualJoypad) -> None:
        """On the map, once the hero is on his tile: open the COMMAND window and choose SPELL (heal_key)."""
        joypad.release_all(ALL_DIRECTION_KEYS & joypad.held)
        if not self.game.player.is_moving:
            self.tap(joypad, self.heal_key())

    def walk(self, joypad: VirtualJoypad) -> None:
        """Hold the direction to the other tile of the two (or keep holding it while a step is under way). On the map
        with HP low (a heal cast, or the COMMAND window closed after it), heal again or stop first. On an inn trip,
        the trip drives (InnTrip.drive)."""
        if self.trip is None and self.game.current_map.identifier != self.map_identifier:
            self.stop(StopReason.INTERRUPTED, show_now=False)
            return
        if self.heal_spell is None and not self.game.player.is_moving and not self.game.cmd_menu.menu.is_enabled() \
                and self.hp_low():
            self.heal_or_stop(in_fight=False)
            if not self.active:
                return
        if self.heal_spell is not None:
            self.heal_on_the_map(joypad)
            return
        if self.trip is not None:
            result = self.trip.drive(joypad)
            if result == TripResult.HOME:
                self.back_home()
            elif result in TRIP_STOPS:
                self.stop(TRIP_STOPS[result])
            return
        joypad.release_all(joypad.held - ALL_DIRECTION_KEYS)
        if self.game.player.is_moving:
            return
        cell = self.hero_cell()
        if cell == self.origin:
            target = self.partner
        elif cell == self.partner:
            target = self.origin
        else:
            self.stop(StopReason.INTERRUPTED, show_now=False)
            return
        assert target is not None
        direction = self.direction_between(cell, target)
        if direction is None:
            self.stop(StopReason.INTERRUPTED, show_now=False)
            return
        self.hold_direction(joypad, direction)

    def hold_direction(self, joypad: VirtualJoypad, direction: int) -> None:
        """Walk this way: hold its key, and let go of every other key."""
        walk_key = walk_key_for(direction)
        joypad.release_all(joypad.held - {walk_key})
        joypad.hold(walk_key)

    @staticmethod
    def direction_keys_held(joypad: VirtualJoypad) -> set[int]:
        return set(ALL_DIRECTION_KEYS & joypad.held)

    @staticmethod
    def walk_key(direction: int) -> int:
        return walk_key_for(direction)

    @staticmethod
    def a_key() -> int:
        return a_key()

    def real_key(self, current_event: Event) -> bool:
        """The player pressed a key: the speed keys and the zoom keys go on to the game as usual; any other key (G too)
        stops auto-grind and is used up."""
        pressed = getattr(current_event, 'key', None)
        if requested_speed(current_event) is not None or pressed in MODIFIER_KEYS or \
                getattr(current_event, 'mod', 0) & KMOD_CTRL:
            return True
        self.stop(StopReason.KEY, show_now=False)
        return False
