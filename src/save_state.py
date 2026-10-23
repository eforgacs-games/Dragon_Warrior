"""Save states: a complete snapshot of the game on the map, which loading puts back exactly. Not NES.

The adventure log (src/save_file.py) is the NES's save and stays as it is. A save state is this game's own quality of
life feature, like an emulator's: Shift + F1/F2/F3 saves one into slot 1/2/3 and F1/F2/F3 loads it
(Game.handle_save_state_keys). The rewind (src/rewind.py) keeps the same snapshots in memory.

``take_snapshot`` makes the snapshot: a plain dict of JSON values, small enough to keep many of in memory (no
surfaces, no sprites; a map is named, not copied). It holds everything the game's next frames depend on:
- the map and the hero's pixel position, facing and step under way, the camera, and the hero's stats, HP and MP,
  gold, experience, items, equipment, spells and statuses;
- every story flag (src/story_flags.py), the treasure chest history, the door history once the game has one (#369),
  and the map layouts' changes: the doors opened (CommandMenu.door writes them into the layouts), the chests shown
  open and the Rainbow Bridge;
- the repel, radiant and light timers and the curse (the hero's worn cursed items);
- the NPCs on the map: which are there, their pixel positions, facings, steps under way and mobile slots, and the NPC
  schedule (src/npc_schedule.py: FrameCounter, NPCUpdateCntr and the shared walking frame);
- the frame counters step timing depends on (the hill pause, the pop-up window's wait, the step counts the fight rolls
  and the Magic Armor read), the options in force (src/options_screen.py) and the window color;
- the random number generator (Python's ``random``, which every roll in the game reads), so that loading a state and
  pressing the same keys plays out the same way, fights included.

Not kept: the game speed (keys 1 to 5), auto-battle and invulnerability (F4, F9), fullscreen and the zoom, which are
settings of the session rather than of the game, as they aren't saved with the adventure log either.

``restore_snapshot`` puts a snapshot back. It rebuilds the map the way MapManager.change_map does (with no fade out:
the screen cuts to black, the map is drawn and fades in, and its music starts) unless the snapshot is on the map that
is up and its tiles haven't changed, when it just moves everyone back (the rewind's case). Every value is checked
(``decode_snapshot``) before anything is changed, so a state that can't be read is refused, not half loaded.

A state file is ``state_<slot>.json`` in the save folder (SAVE_DIR), holding the snapshot with its format version
(STATE_FORMAT_VERSION). From 1.0 on, a state saved by any 1.x build loads in every later one: a state in an older
format is brought up to date by STATE_MIGRATIONS (``migrate_snapshot``) before it is checked. One from a newer build,
or one that can't be read, is refused with a message. tests/test_save_compatibility.py loads a sample state of every
format, kept in tests/sample_saves/.
"""
import base64
import json
import os
import random
from array import array
from collections.abc import Callable
from typing import Any

from pygame import Rect

from src.camera import Camera
from src.dungeon_map import DungeonMap
from src.items import TreasureChestHistory
from src.map_layouts import MapLayouts
from src.maps import CharlockB1, map_lookup
from src.menu import CommandMenu
from src.options_screen import apply_options, options_from_config, options_from_save, options_to_save
from src.sprites.animated_sprite import AnimatedSprite
from src.story_flags import StoryFlags
from src.visual_effects import cut_to_black, screen_fade

# Raise it whenever what a snapshot holds changes, with a STATE_MIGRATIONS step from the version before (and a sample
# state of that version in tests/sample_saves/), so states saved before load as they should rather than wrong
STATE_FORMAT_VERSION = 1
VERSION_KEY = 'version'
SAVE_STATE_SLOTS = (1, 2, 3)

# The hero's values a snapshot keeps, as they are (numbers, strings, booleans and None)
PLAYER_VALUES = (
    'name', 'level', 'total_experience', 'gold', 'current_hp', 'current_mp', 'max_hp', 'max_mp', 'strength',
    'agility', 'attack_power', 'defense_power', 'weapon', 'armor', 'shield', 'wearing_dragon_scale',
    'wearing_fighters_ring', 'wearing_cursed_belt', 'wearing_death_necklace', 'is_dead', 'is_asleep',
    'is_stopspelled', 'adventure_log', 'direction_value', 'row', 'column', 'is_moving', 'bumped',
    'received_environment_damage', 'next_tile_checked', 'current_tile', 'next_tile_id', 'next_next_tile_id',
    'current_frame',
)
# The hero's (row, column) pairs, which may be None
PLAYER_CELLS = ('step_origin', 'step_destination', 'next_coordinates', 'next_next_coordinates')
PLAYER_LISTS = ('inventory', 'spells')
# A roaming NPC's values and pairs; a fixed one's values
ROAMING_VALUES = ('row', 'column', 'direction_value', 'current_frame', 'is_moving', 'next_tile_checked',
                  'next_tile_id', 'next_next_tile_id', 'current_tile', 'previous_tile', 'previous_previous_tile',
                  'turns_to_rest', 'slot', 'bumped')
ROAMING_CELLS = ('step_origin', 'step_destination')
FIXED_VALUES = ('row', 'column', 'direction_value', 'current_frame', 'bumped')
# GameState's values (src/game_state.py): the light and radiant timer, the step count and the king's dialogs
GAME_STATE_VALUES = ('tiles_moved_total', 'light_diameter', 'radiant_timer', 'lit_diameter', 'light_redraw_frame',
                     'is_initial_dialog', 'is_post_death_dialog', 'automatic_initial_dialog_run', 'enable_movement',
                     'enable_animate', 'enable_roaming')
# Game's values: the step counts the fight rolls read, the repel timer, Magic Armor's step count
GAME_VALUES = ('tiles_moved_since_spawn', 'last_amount_of_tiles_moved', 'repel_timer', 'magic_armor_steps',
               'last_zone', 'initial_dialog_enabled')
# MovementController's frame counters (src/movement.py)
MOVEMENT_VALUES = ('hero_standing', 'step_ends', 'hill_pause_frames', 'freeze_wait_frames')

_pristine_layouts: dict[str, list[list[int]]] | None = None


class StateError(Exception):
    """A save state that can't be loaded: from another format version, or unreadable."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


OLD_VERSION = 'old version'
UNREADABLE = 'unreadable'


# STATE_MIGRATIONS[n] turns a snapshot in format n into format n + 1, for every version from 1 (the first, in 1.0) up to
# STATE_FORMAT_VERSION
STATE_MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def migrate_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """A snapshot in the current format: the STATE_MIGRATIONS from its own format on, in order. Raises StateError
    (OLD_VERSION) for one with no version, or from a newer build than this one."""
    version = snapshot.get(VERSION_KEY)
    if not isinstance(version, int) or isinstance(version, bool) or not 1 <= version <= STATE_FORMAT_VERSION:
        raise StateError(OLD_VERSION)
    for from_version in range(version, STATE_FORMAT_VERSION):
        snapshot = STATE_MIGRATIONS[from_version](snapshot)
        snapshot[VERSION_KEY] = from_version + 1
    return snapshot


def pristine_layouts() -> dict[str, list[list[int]]]:
    """Every map's layout as it is in a new game, decoded once and never changed."""
    global _pristine_layouts
    if _pristine_layouts is None:
        _pristine_layouts = MapLayouts().map_layout_lookup
    return _pristine_layouts


def map_layout_changes(map_name: str, layout: list[list[int]]) -> list[list[int]]:
    """One map's tiles that differ from a new game's, as [row, column, tile value]. Whole rows are compared first, so
    only changed rows are looked at tile by tile."""
    return [[row, column, value]
            for row, (current_row, pristine_row) in enumerate(zip(layout, pristine_layouts()[map_name]))
            if current_row != pristine_row
            for column, (value, pristine_value) in enumerate(zip(current_row, pristine_row))
            if value != pristine_value]


def layout_changes(layouts: dict[str, list[list[int]]]) -> dict[str, list[list[int]]]:
    """The tiles of every map's layout that differ from a new game's, for each map that has any."""
    changes = {map_name: map_layout_changes(map_name, layouts[map_name]) for map_name in pristine_layouts()}
    return {map_name: changed for map_name, changed in changes.items() if changed}


def apply_layout_changes(layouts: dict[str, list[list[int]]], changes: dict[str, list[list[int]]]) -> None:
    """Make the layouts a new game's plus these changes, in place: each map's layout stays the same list, which the
    map on screen may be using."""
    for map_name, pristine in pristine_layouts().items():
        layout = layouts[map_name]
        for current_row, pristine_row in zip(layout, pristine):
            if current_row != pristine_row:
                current_row[:] = pristine_row
        for row, column, value in changes.get(map_name, ()):
            layout[row][column] = value


def _cell(value: Any) -> tuple[int, int] | None:
    if value is None:
        return None
    row, column = value
    return int(row), int(column)


def _json_cell(value: Any) -> list[int] | None:
    return None if value is None else [int(value[0]), int(value[1])]


def _json_history(history: Any) -> list | None:
    """A TreasureChestHistory's or OpenDoorHistory's slots: (map name, (row, column)) or None each."""
    if history is None:
        return None
    return [None if slot is None else [slot[0], _json_cell(slot[1])] for slot in history.slots]


def _history(slots: list) -> list[tuple[str, tuple[int, int] | None] | None]:
    return [None if slot is None else (str(slot[0]), _cell(slot[1])) for slot in slots]


def _restore_histories(game: Any, state: dict[str, Any]) -> None:
    game.chest_history.slots = list(state['chest_history'])
    door_history = getattr(game, 'door_history', None)
    if door_history is not None and state['door_history'] is not None:
        door_history.slots = list(state['door_history'])


def _rect(sprite: Any) -> list[int]:
    return [sprite.rect.x, sprite.rect.y]


def encode_random_state(state: tuple) -> list:
    """random.getstate() as JSON: the Mersenne Twister's 625 words packed into base64 (3.3 KB, where a list of them
    would be about 7 KB of JSON and 25 KB of Python ints in memory)."""
    version, internal_state, gauss_next = state
    words = array('I', internal_state)
    return [version, base64.b64encode(words.tobytes()).decode('ascii'), gauss_next]


def decode_random_state(encoded: list) -> tuple:
    version, packed, gauss_next = encoded
    words = array('I')
    words.frombytes(base64.b64decode(packed))
    if len(words) != 625:
        raise ValueError("not a random number generator state")
    return int(version), tuple(words), None if gauss_next is None else float(gauss_next)


def take_snapshot(game: Any) -> dict[str, Any]:
    """The game as it is now (see the module docstring), as JSON values. Taken between two map frames."""
    current_map = game.current_map
    player = game.player
    hero = {name: getattr(player, name) for name in PLAYER_VALUES}
    hero.update({name: _json_cell(getattr(player, name)) for name in PLAYER_CELLS})
    hero.update({name: list(getattr(player, name)) for name in PLAYER_LISTS})
    hero['inventory'] = player.inventory.with_empty_slots()  # the NES slots, with None for an emptied one (#390)
    hero['rect'] = _rect(player)
    roaming = []
    for character in current_map.roaming_characters:
        values: dict[str, Any] = {name: getattr(character, name, None) for name in ROAMING_VALUES}
        values.update({name: _json_cell(getattr(character, name)) for name in ROAMING_CELLS})
        last_rect = character.last_rect
        values.update(identifier=character.identifier, rect=_rect(character),
                      last_rect=None if last_rect is None else [last_rect.x, last_rect.y, last_rect.w, last_rect.h])
        roaming.append(values)
    fixed = [{'identifier': character.identifier, 'rect': _rect(character),
              **{name: getattr(character, name, None) for name in FIXED_VALUES}}
             for character in current_map.fixed_characters]
    schedule = game.movement.npc_schedule
    return {
        VERSION_KEY: STATE_FORMAT_VERSION,
        'map': current_map.identifier,
        'layout_changes': layout_changes(game.layouts.map_layout_lookup),
        'hero': hero,
        'hero_underlying_tile': current_map.character_key['HERO']['underlying_tile'],
        'roaming': roaming,
        'fixed': fixed,
        'camera': list(game.camera.pos),
        'story_flags': game.story_flags.to_save(),
        'chest_history': _json_history(game.chest_history),
        # The door history (OpenDoorHistory, #369), once the game has one; the opened doors are in the layouts too
        'door_history': _json_history(getattr(game, 'door_history', None)),
        'game': {name: getattr(game, name) for name in GAME_VALUES},
        'color': list(game.color),
        'game_state': {**{name: getattr(game.game_state, name) for name in GAME_STATE_VALUES},
                       'pending_light_redraws': list(game.game_state.pending_light_redraws)},
        'movement': {**{name: getattr(game.movement, name) for name in MOVEMENT_VALUES},
                     'frame_counter': schedule.frame_counter, 'update_counter': schedule.update_counter,
                     'walk_frame': AnimatedSprite.walk_frame},
        'fought_on_stairs': _json_cell(game.map_mgr.fought_on_stairs),
        'last_battle_action': game.battle_ctrl.last_battle_action,
        'pending_scripted_battle': game.battle_ctrl.pending_scripted_battle,
        'pop_up_window': game.drawer.display_hovering_stats,
        'options': options_to_save(options_from_config(game.game_state.config)),
        'random': encode_random_state(random.getstate()),
        # What the hero has seen of each dark floor (src/dungeon_map.py)
        'dungeon_map': game.dungeon_map.to_save() if hasattr(game, 'dungeon_map') else {},
    }


def decode_snapshot(snapshot: Any) -> dict[str, Any]:
    """Check a snapshot and turn its JSON values back into the game's (tuples, the random state), without changing
    the game. Raises StateError for one from a newer format version or one that can't be read."""
    if not isinstance(snapshot, dict):
        raise StateError(UNREADABLE)
    snapshot = migrate_snapshot(snapshot)
    try:
        if snapshot['map'] not in map_lookup:
            raise ValueError(f"unknown map {snapshot['map']!r}")
        layouts = pristine_layouts()
        changes = {}
        for map_name, map_changes in snapshot['layout_changes'].items():
            layout = layouts[map_name]
            changes[map_name] = [[int(row), int(column), int(value)] for row, column, value in map_changes]
            for row, column, _ in changes[map_name]:
                layout[row][column]  # an IndexError if it's off the map
        hero = dict(snapshot['hero'])
        for name in PLAYER_VALUES:
            hero[name]  # a KeyError if it's missing
        for name in PLAYER_CELLS:
            hero[name] = _cell(hero[name])
        for name in PLAYER_LISTS:
            hero[name] = [None if value is None and name == 'inventory' else str(value) for value in hero[name]]
        hero['rect'] = [int(value) for value in hero['rect']]
        roaming = []
        for values in snapshot['roaming']:
            values = dict(values)
            for name in ROAMING_VALUES:
                values[name]
            for name in ROAMING_CELLS:
                values[name] = _cell(values[name])
            values['rect'] = [int(value) for value in values['rect']]
            values['last_rect'] = None if values['last_rect'] is None else [int(v) for v in values['last_rect']]
            str(values['identifier'])
            roaming.append(values)
        fixed = []
        for values in snapshot['fixed']:
            values = dict(values)
            for name in FIXED_VALUES:
                values[name]
            values['rect'] = [int(value) for value in values['rect']]
            fixed.append(values)
        decoded = {
            'map': snapshot['map'],
            'layout_changes': changes,
            'hero': hero,
            'hero_underlying_tile': str(snapshot['hero_underlying_tile']),
            'roaming': roaming,
            'fixed': fixed,
            'camera': tuple(snapshot['camera']),
            'story_flags': StoryFlags.from_save({'StoryFlags': dict(snapshot['story_flags'])}),
            'chest_history': _history(snapshot['chest_history']),
            'door_history': None if snapshot.get('door_history') is None else _history(snapshot['door_history']),
            'game': {name: snapshot['game'][name] for name in GAME_VALUES},
            'color': tuple(int(value) for value in snapshot['color']),
            'game_state': {**{name: snapshot['game_state'][name] for name in GAME_STATE_VALUES},
                           'pending_light_redraws': [int(value) for value in
                                                     snapshot['game_state']['pending_light_redraws']]},
            'movement': {name: snapshot['movement'][name]
                         for name in (*MOVEMENT_VALUES, 'frame_counter', 'update_counter', 'walk_frame')},
            'fought_on_stairs': _cell(snapshot['fought_on_stairs']),
            'last_battle_action': snapshot['last_battle_action'],
            'pending_scripted_battle': snapshot['pending_scripted_battle'],
            'pop_up_window': bool(snapshot['pop_up_window']),
            'options': options_from_save(dict(snapshot['options'])),
            'random': decode_random_state(snapshot['random']),
            # a state saved before the dungeon map has none: every floor unexplored
            'dungeon_map': DungeonMap.from_save(snapshot.get('dungeon_map', {})),
        }
        if len(decoded['chest_history']) != len(TreasureChestHistory().slots) or len(decoded['camera']) != 2 \
                or len(decoded['color']) != 3:
            raise ValueError("wrong size")
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
        raise StateError(UNREADABLE) from error
    return decoded


def restore_snapshot(game: Any, snapshot: dict[str, Any], fade_in: bool = True) -> None:
    """Put the game back as it was when the snapshot was taken (see the module docstring). fade_in, for loading a save
    state: the screen cuts to black and the map fades in, as when a saved game is loaded (Game.load_game), and its
    music starts. Without it (the rewind), the map is just drawn, and its music only restarts if the map changes.
    Raises StateError, before anything has changed, if the snapshot can't be loaded."""
    state = decode_snapshot(snapshot)
    old_map = game.current_map
    old_tiles = map_layout_changes(old_map.identifier, old_map.layout) \
        if old_map.identifier in pristine_layouts() else None
    apply_layout_changes(game.layouts.map_layout_lookup, state['layout_changes'])
    game.story_flags = state['story_flags']
    _restore_histories(game, state)
    music_before = game.game_state.config.get('ORCHESTRA_MUSIC_ENABLED')
    apply_options(game.game_state.config, state['options'])
    for config_key in ('GAME_SPEED_KEYS', 'CHEAT_KEYS'):  # the switches that act at once (Game.apply_option)
        game.apply_option(config_key)
    same_map = (not fade_in and old_map.identifier == state['map'] and old_tiles is not None
                and old_tiles == state['layout_changes'].get(state['map'], [])
                and [character.identifier for character in old_map.roaming_characters]
                == [values['identifier'] for values in state['roaming']]
                and [character.identifier for character in old_map.fixed_characters]
                == [values['identifier'] for values in state['fixed']])
    if not same_map:
        _rebuild_map(game, state, cut_to_black_first=fade_in)
    _restore_values(game, state)
    if fade_in:
        # MapManager.change_map: the frame the fade in starts from, which reads no buttons, then PalFadeIn
        game.drawer.drawing_fade_in_frame = True
        try:
            game.drawer.draw_all(game, game.game_state.enable_animate)
        finally:
            game.drawer.drawing_fade_in_frame = False
        screen_fade(fade_out=False, screen=game.screen, config=game.game_state.config)
    if fade_in or game.current_map.identifier != old_map.identifier:
        game.music_player.load_and_play_music(game.current_map.music_file_path)
    elif game.game_state.config.get('ORCHESTRA_MUSIC_ENABLED') != music_before:
        game.apply_option('ORCHESTRA_MUSIC_ENABLED')  # the state's MUSIC setting, on the map that stayed


def _rebuild_map(game: Any, state: dict[str, Any], cut_to_black_first: bool) -> None:
    """Load the snapshot's map the way MapManager.change_map does, with the restored story flags, chest history and
    layouts, and only the NPCs that were on it."""
    map_mgr = game.map_mgr
    game.game_state.pause_all_movement()
    next_map = map_lookup[state['map']](game.config)
    map_mgr.last_map = game.current_map
    game.current_map = next_map
    next_map.layout = game.layouts.map_layout_lookup[next_map.__class__.__name__]
    # These only write into the layouts what the restored layout changes have already, and set left_throne_room as
    # it already is; the chest (and door) history is put back after apply_chest_history's InitMapData step
    map_mgr.apply_rainbow_bridge()
    if isinstance(next_map, CharlockB1) and game.story_flags.charlock_stairs_revealed:
        next_map.reveal_hidden_staircase()
    map_mgr.apply_chest_history()
    _restore_histories(game, state)
    map_mgr.place_princess_gwaelin()
    if game.story_flags.dragonlord_defeated:
        next_map.apply_dragonlord_defeated()
    if cut_to_black_first:
        cut_to_black(game.screen, game.game_state.config)
    map_mgr.set_big_map()
    map_mgr.set_roaming_character_positions()
    hero = state['hero']
    next_map.character_key['HERO']['underlying_tile'] = state['hero_underlying_tile']
    next_map.load_map(game.player, (hero['row'], hero['column']), game.tile_size)
    # NPCs a dialog took off the map (DialogLookup.remove_npc) stay off it; the others keep their mobile slots
    kept = {values['identifier'] for values in (*state['roaming'], *state['fixed'])}
    for identifier in [identifier for identifier in next_map.characters if identifier != 'HERO']:
        if identifier not in kept:
            character = next_map.characters.pop(identifier)['character']
            for characters in (next_map.fixed_characters, next_map.roaming_characters):
                if character in characters:
                    characters.remove(character)
    game.camera = Camera(hero_position=(int(game.player.column), int(game.player.row)), current_map=next_map,
                         screen=game.screen, tile_size=game.tile_size)
    game.cmd_menu = CommandMenu(game)


def _restore_values(game: Any, state: dict[str, Any]) -> None:
    """Everything but the map itself: the hero, the NPCs, the counters, the camera, the window color and the random
    number generator."""
    player = game.player
    hero = state['hero']
    game.dungeon_map = state['dungeon_map'].copy()  # a copy: the rewind can put the same snapshot back again
    for name in (*PLAYER_VALUES, *PLAYER_CELLS):
        setattr(player, name, hero[name])
    for name in PLAYER_LISTS:
        setattr(player, name, list(hero[name]))
    player.rect.x, player.rect.y = hero['rect']
    current_map = game.current_map
    for character, values in zip(current_map.roaming_characters, state['roaming']):
        for name in (*ROAMING_VALUES, *ROAMING_CELLS):
            if name == 'bumped' and values[name] is None:
                if hasattr(character, 'bumped'):
                    del character.bumped
                continue
            setattr(character, name, values[name])
        character.rect.x, character.rect.y = values['rect']
        last_rect = values['last_rect']
        character.last_rect = None if last_rect is None else Rect(*last_rect)
    for character, values in zip(current_map.fixed_characters, state['fixed']):
        for name in FIXED_VALUES:
            if name == 'bumped' and values[name] is None:
                if hasattr(character, 'bumped'):
                    del character.bumped
                continue
            setattr(character, name, values[name])
        character.rect.x, character.rect.y = values['rect']
    for name, value in state['game'].items():
        setattr(game, name, value)
    game_state = game.game_state
    for name in GAME_STATE_VALUES:
        setattr(game_state, name, state['game_state'][name])
    game_state.pending_light_redraws = list(state['game_state']['pending_light_redraws'])
    movement = game.movement
    for name in MOVEMENT_VALUES:
        setattr(movement, name, state['movement'][name])
    movement.npc_schedule.frame_counter = state['movement']['frame_counter']
    movement.npc_schedule.update_counter = state['movement']['update_counter']
    AnimatedSprite.walk_frame = state['movement']['walk_frame']
    movement.npc_asked_to_make_way = None
    game.map_mgr.fought_on_stairs = state['fought_on_stairs']
    game.battle_ctrl.last_battle_action = state['last_battle_action']
    game.battle_ctrl.pending_scripted_battle = state['pending_scripted_battle']
    # Nothing is waiting to happen: the snapshot was taken with no window open or asked for
    game.paused = game.pause_requested = game.cmd_menu_requested = game.options_requested = False
    game.auto_grind_requested = False
    game.cmd_menu.launch_signaled = False
    game.camera.pos = state['camera']
    # The map is drawn in full on the next frame, with the pop-up window already open if it was (no drop-down)
    game.loop_count = 1
    game.drawer.display_hovering_stats = game.drawer.hovering_stats_displayed = state['pop_up_window']
    game.drawer.last_player_rect = None
    game.set_window_color(state['color'])
    game.set_player_images_by_equipment()
    for character_dict in current_map.characters.values():
        character_dict['character'].show_facing()
    random.setstate(state['random'])


def state_file_name(slot: int) -> str:
    return f'state_{slot}.json'


def state_path(save_dir: str, slot: int) -> str:
    return os.path.join(save_dir, state_file_name(slot))


def write_state(save_dir: str, slot: int, snapshot: dict[str, Any]) -> None:
    """Write a snapshot to its slot's file, replacing what was there."""
    write_snapshot(state_path(save_dir, slot), snapshot)


def write_snapshot(path: str, snapshot: dict[str, Any]) -> None:
    """Write a snapshot to a file (a save state slot's, or the autosave's: src/autosave.py), replacing what was there.
    It's written to a temporary file first, so a state is never left half written."""
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    temporary_path = path + '.tmp'
    with open(temporary_path, 'w') as state_file:
        json.dump(snapshot, state_file, separators=(',', ':'))
    os.replace(temporary_path, path)


def read_state(save_dir: str, slot: int) -> dict[str, Any] | None:
    """The snapshot saved in a slot, or None if the slot is empty. Raises StateError if the file can't be read or is
    from a newer format version (decode_snapshot checks the rest)."""
    return read_snapshot(state_path(save_dir, slot))


def read_snapshot(path: str) -> dict[str, Any] | None:
    """The snapshot in a file, or None if there's no such file. Raises StateError as read_state does."""
    if not os.path.exists(path):
        return None
    try:
        with open(path) as state_file:
            snapshot = json.load(state_file)
    except (OSError, ValueError) as error:
        raise StateError(UNREADABLE) from error
    if not isinstance(snapshot, dict):
        raise StateError(UNREADABLE)
    return migrate_snapshot(snapshot)
