"""Auto-grind: G on the map walks back and forth and fights until a decision is the player's to make. Not NES.

G starts it when START or the COMMAND window would be accepted on the map (Game.handle_auto_grind_key, resolved
with the pause and the options overlay in MovementController.resolve_pending_freezes), on a map with random fights,
with HP above the GRIND STOP threshold and a safe tile next to the hero (``safe_partner``). It then drives the game
with a virtual joypad (src/virtual_joypad.py), so everything runs through the game's own code: the walking, the
encounter rolls, the step effects, every window and wait.

- On the map it holds the direction from the hero's tile to the partner tile and back, at walking speed.
- Anywhere else (a fight, its dialog lines, the victory wait, a message) it taps A every TAP_PERIOD_FRAMES frames,
  which chooses FIGHT in the battle's command window (the cursor starts on FIGHT every turn) and moves every dialog
  on. F4 auto-battle is ignored meanwhile (BattleController.handle_battle_prompts).

It stops, with the menu button sound and a message saying why, and hands the game back on the screen it is at:
- HP at or below the GRIND STOP option's threshold (AUTO_GRIND_STOP): checked at the start of every player turn
  (``player_turn_starts``, so the battle's command window is the player's), after every fight (``after_fight``) and
  after every step (``after_step``);
- the hero asleep at the start of a turn, or STOPSPELL working on the hero (``stopspell_hit``);
- a scripted fight, a guardian or the Dragonlord (``scripted_fight_starts``), before its first command;
- a level up (``level_up``), before the promotion and the stat lines, which wait for the player; G goes on;
- any key the player presses (G included) but the game speed keys 1 to 5 and the zoom keys (``real_key``);
- the hero dying, or being somewhere he wasn't walking to (a map change), without a message for a death.
"""
from enum import Enum

from pygame import K_CAPSLOCK, K_LALT, K_LCTRL, K_LGUI, K_LSHIFT, K_MODE, K_NUMLOCK, K_RALT, K_RCTRL, K_RGUI, \
    K_RSHIFT, K_g, K_k, KMOD_CTRL
from pygame.event import Event

from src.color import is_low_hp
from src.coordinates import Cell
from src.encounters import encounter_group
from src.guardians import guardian_at
from src.movement import DIRECTION_KEYS
from src.npc_movement import step
from src.options_screen import AUTO_GRIND_STOP_VALUES
from src.virtual_joypad import VirtualJoypad
from src.waiting import MAP_CONTEXT, SPEED_KEYS

# The GRIND STOP option (src/options_overlay.py, AUTO_GRIND_STOP): when HP is low enough to stop. RED HP is the NES's
# low HP, where the windows turn red (ChkLowHPPal): HP <= max HP / 4 + 1. HALF HP: HP <= max HP / 2. 3/4 HP:
# HP <= max HP * 3 / 4.
GRIND_STOP_RED_HP, GRIND_STOP_HALF_HP, GRIND_STOP_THREE_QUARTERS_HP = AUTO_GRIND_STOP_VALUES

AUTO_GRIND_KEYS = (K_g,)
A_KEY = K_k
TAP_HOLD_FRAMES = 2  # an A tap is held this long
TAP_PERIOD_FRAMES = 8  # and one starts this often
# Keys that don't count as "any key": the modifiers on their own (Ctrl for the zoom keys, say)
MODIFIER_KEYS = frozenset((K_LSHIFT, K_RSHIFT, K_LCTRL, K_RCTRL, K_LALT, K_RALT, K_LGUI, K_RGUI, K_CAPSLOCK,
                           K_NUMLOCK, K_MODE))

# The hero never paces onto these: they hurt (swamp, force field) or take him off the map (stairs)
UNSAFE_TILES = frozenset(('MARSH', 'BARRIER', 'BRICK_STAIR_DOWN', 'BRICK_STAIR_UP', 'GRASS_STAIR_DOWN'))
# The key for each direction (the first of its keys) and every direction key
WALK_KEYS = {direction: keys[0] for direction, keys in DIRECTION_KEYS}
ALL_DIRECTION_KEYS = frozenset(direction_key for _direction, keys in DIRECTION_KEYS for direction_key in keys)
# The order the partner tile is looked for in, after the direction the hero faces
PARTNER_ORDER = tuple(direction for direction, _keys in DIRECTION_KEYS)


def at_grind_stop_hp(current_hp: int, max_hp: int, setting: str | None) -> bool:
    """Whether HP is at or below the GRIND STOP threshold (RED HP for any other setting)."""
    if setting == GRIND_STOP_HALF_HP:
        return current_hp <= max_hp // 2
    if setting == GRIND_STOP_THREE_QUARTERS_HP:
        return current_hp <= max_hp * 3 // 4
    return is_low_hp(current_hp, max_hp)


class StopReason(Enum):
    HP_LOW = 'hp low'
    ASLEEP = 'asleep'
    STOPSPELL = 'stopspell'
    SCRIPTED_FIGHT = 'scripted fight'
    LEVEL_UP = 'level up'
    KEY = 'key'
    INTERRUPTED = 'interrupted'
    DEATH = 'death'


class AutoGrind:
    """Auto-grind for one game (see the module docstring); the virtual joypad's driver."""

    def __init__(self, game) -> None:
        self.game = game
        self.joypad = VirtualJoypad(self)
        self.map_identifier: str | None = None
        self.origin: Cell | None = None  # the hero's tile when it started
        self.partner: Cell | None = None  # the safe tile next to it
        self.next_tap_frame = 0
        self.last_stop: StopReason | None = None
        # A stop message waiting to be shown at the next safe point: the next map frame or player turn
        self.pending_message: str | None = None

    @property
    def active(self) -> bool:
        return self.joypad.connected

    # Starting and stopping

    def hero_cell(self) -> Cell:
        """The hero's (row, column), from the sprite: a step that has just ended hasn't updated row and column yet."""
        tile_size = self.game.tile_size
        return self.game.player.rect.y // tile_size, self.game.player.rect.x // tile_size

    def hp_low(self) -> bool:
        player = self.game.player
        return at_grind_stop_hp(player.current_hp, player.max_hp, self.game.game_state.config.get('AUTO_GRIND_STOP'))

    def has_random_fights(self) -> bool:
        """Whether a step here can start a random fight (Game.roll_for_fight): a map with an encounter group, and the
        Dragonlord alive (ChkOtherBlocks)."""
        row, column = self.hero_cell()
        return (not self.game.story_flags.dragonlord_defeated and
                encounter_group(self.game.current_map.identifier, column, row) is not None)

    def start(self) -> bool:
        """G on the map, once the hero and the NPCs are on their tiles. Returns whether auto-grind started."""
        if self.active:
            return False
        _ = self.game._
        if self.game.game_state.config.get('NO_BATTLES'):
            # dev_config's NO_BATTLES: no step starts a fight, so it would only walk back and forth
            self.game.draw_temporary_text(_("Auto-grind: battles are off (NO_BATTLES)"))
            return False
        if not self.has_random_fights():
            self.game.draw_temporary_text(_("Auto-grind: no fights here"))
            return False
        if self.hp_low():
            self.game.draw_temporary_text(_("Auto-grind: HP is already low"))
            return False
        origin = self.hero_cell()
        partner = self.safe_partner(origin)
        if partner is None:
            self.game.draw_temporary_text(_("Auto-grind: no safe tile to walk to"))
            return False
        self.map_identifier = self.game.current_map.identifier
        self.origin, self.partner = origin, partner
        self.last_stop = None
        self.pending_message = None
        self.game.draw_temporary_text(_("Auto-grind on\n(G or any key to stop)"))
        self.next_tap_frame = 0
        self.joypad.connect()
        return True

    def stop(self, reason: StopReason, show_now: bool = True) -> None:
        """Hand the game back where it is: let go of every key, play the menu button sound and say why (at once, or
        at the next safe point)."""
        if not self.active:
            return
        self.joypad.disconnect()
        self.last_stop = reason
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
            case StopReason.ASLEEP:
                return _("Auto-grind stopped: asleep")
            case StopReason.STOPSPELL:
                return _("Auto-grind stopped: STOPSPELL")
            case StopReason.SCRIPTED_FIGHT:
                return _("Auto-grind stopped: special fight")
            case StopReason.LEVEL_UP:
                return _("Auto-grind stopped: level up\n(G to go on)")
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
        elif self.hp_low():
            self.stop(StopReason.HP_LOW)

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
        elif self.active and self.hp_low():
            self.stop(StopReason.HP_LOW)

    def after_step(self) -> None:
        if self.active and self.hp_low():
            self.stop(StopReason.HP_LOW)

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
            if joypad.now >= self.next_tap_frame:
                joypad.tap(A_KEY, TAP_HOLD_FRAMES)
                self.next_tap_frame = joypad.now + TAP_PERIOD_FRAMES

    def walk(self, joypad: VirtualJoypad) -> None:
        """Hold the direction to the other tile of the two (or keep holding it while a step is under way)."""
        joypad.release_all(joypad.held - ALL_DIRECTION_KEYS)
        if self.game.current_map.identifier != self.map_identifier:
            self.stop(StopReason.INTERRUPTED, show_now=False)
            return
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
        walk_key = WALK_KEYS[direction]
        joypad.release_all(ALL_DIRECTION_KEYS - {walk_key})
        joypad.hold(walk_key)

    def real_key(self, current_event: Event) -> bool:
        """The player pressed a key: the speed keys and the zoom keys go on to the game as usual; any other key (G too)
        stops auto-grind and is used up."""
        pressed = getattr(current_event, 'key', None)
        if pressed in SPEED_KEYS or pressed in MODIFIER_KEYS or getattr(current_event, 'mod', 0) & KMOD_CTRL:
            return True
        self.stop(StopReason.KEY, show_now=False)
        return False
