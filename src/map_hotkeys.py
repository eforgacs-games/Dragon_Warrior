"""The keys read on the map (Game.handle_keypresses): the NES buttons, and this game's own keys, none of them NES.

Each key press goes through every handler in KEY_HANDLERS, in order; a handler does nothing unless the press is its
key. While the game is paused only START and the fullscreen key are read (NES GamePaused only reads START), and while
rewinding, nothing is (only letting go of Backspace does anything, Game._handle_pygame_events).

Some keys open a window or start a mode on the map (MAP_REQUESTS: the options overlay, the dungeon map, the message log,
the stats page and auto-grind), and a save state is saved or loaded from it. They're only taken when START would pause
the game (MovementController.map_held: no window open or about to open, the game not paused, the light not growing), and
like the pause (NES PausePrepLoop) they wait for the hero and the NPCs to finish their steps: the key sets a request on
the game (request), and MovementController.resolve_pending_freezes opens what was asked for once everyone is on a tile.
The play time (src/play_stats.py) doesn't count while what they open is up.
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pygame import FULLSCREEN, RESIZABLE, SCALED
from pygame.display import set_caption
from pygame.event import Event

from data.text.intro_lookup_table import ControlInfo
from src.achievements import AchievementsScreen
from src.party import free_roaming, in_party_mode
from src.player_two_menu import open_player_two_menu
from src.controls import LOAD_STATE_ACTIONS, SAVE_STATE_ACTIONS, actions_for_event, pressed
from src.display_filters import PRESENTER
from src.dungeon_map import DungeonMapOverlay, dungeon_map_enabled
from src.menu import STAIR_TILES
from src.message_log import MessageLogScreen
from src.options_overlay import OPTIONS_KEYS, OptionsOverlay
from src.save_state import LOAD, SAVE
from src.stats_screen import StatsScreen
from src.quest_journal import JOURNAL_HINTS, JOURNAL_OFF, game_progress, journal_pages
from src.records import GOALS_ENTRY, Record, choose_journal_page, known_records
from src.languages import language_named
from src.waiting import requested_speed, set_game_speed, speed_keys_enabled
from src.zoom import remember_windowed_size, restore_windowed_size

if TYPE_CHECKING:
    from src.game import Game  # src.game imports this module


@dataclass(frozen=True, slots=True)
class MapRequest:
    """Something a key opens or starts from the map once everyone is on a tile: ``flag`` is the Game attribute that is
    True while it waits, ``opener`` the MapHotkeys method resolve_pending_freezes then calls."""
    flag: str
    opener: str
    play: bool = False  # whether the play time counts while it's open (it's play, not a page about it)


# In the order MovementController.resolve_pending_freezes opens them (only one can be waiting at a time: once one is,
# the map is held and the others' keys do nothing)
MAP_REQUESTS = (
    MapRequest('options_requested', 'open_options'),  # SELECT or Tab
    MapRequest('dungeon_map_requested', 'open_dungeon_map'),  # M
    MapRequest('message_log_requested', 'open_message_log'),  # L
    MapRequest('play_stats_requested', 'open_play_stats'),  # P
    MapRequest('achievements_requested', 'open_achievements'),  # T
    MapRequest('auto_grind_requested', 'start_auto_grind'),  # G
    MapRequest('player_two_menu_requested', 'open_player_two_menu', play=True),  # player 2's A (co-op)
)

# The save state keys: (SAVE or LOAD, slot) for each action
STATE_ACTIONS = ((SAVE, SAVE_STATE_ACTIONS), (LOAD, LOAD_STATE_ACTIONS))


class MapHotkeys:
    """The map's key handlers (see the module docstring). The requests they make are kept on the game, where
    MovementController reads them."""

    def __init__(self, game: 'Game') -> None:
        self.game = game

    @property
    def config(self) -> dict:
        return self.game.game_state.config

    def handle_keydown(self, keydown_event: Event) -> None:
        game = self.game
        if game.rewind.active:
            return  # only letting go of Backspace does anything while rewinding
        if game.paused:
            # NES GamePaused only reads START until the game is unpaused
            self.press_start(keydown_event)
            self.toggle_fullscreen(keydown_event)
            return
        for handler in KEY_HANDLERS:
            getattr(self, handler)(keydown_event)
        if game.debug_tools is not None:
            # Dev config only (DEBUG_KEYS): F5 warp, F6 give, F7 load a checkpoint
            game.debug_tools.handle_keydown(keydown_event)

    def request(self, flag: str, value: Any = True) -> None:
        """Ask for something that opens from the map (MAP_REQUESTS, or a save state): only when START would pause the
        game, and once the hero and the NPCs have finished their steps (resolve_pending_freezes)."""
        if self.game.movement.map_held:
            return
        setattr(self.game, flag, value)
        self.game.movement.resolve_pending_freezes()

    def open_requested(self) -> bool:
        """Open the first of MAP_REQUESTS that is waiting, if one is (resolve_pending_freezes, once everyone is on a
        tile). Returns whether one was. The play time doesn't count while it's up."""
        for map_request in MAP_REQUESTS:
            if getattr(self.game, map_request.flag) is True:
                setattr(self.game, map_request.flag, False)
                if map_request.play:
                    getattr(self, map_request.opener)()
                else:
                    with self.game.play_clock.stopped():
                        getattr(self, map_request.opener)()
                return True
        return False

    def clear_requests(self) -> None:
        """Forget what MAP_REQUESTS is waiting for (START pauses instead, or a snapshot is put back)."""
        for map_request in MAP_REQUESTS:
            setattr(self.game, map_request.flag, False)

    # The NES buttons

    def press_a(self, keydown_event: Event) -> None:
        """A: the COMMAND window, once the hero and the NPCs have finished their steps (resolve_pending_freezes). With
        SMART A on (not NES), that's when TALK, TAKE, DOOR or STAIRS runs instead, if one applies there
        (run_smart_command). The SMART A key (Enter) is the A button on the map too unless QUICK ACTION is on
        (press_smart_a_key)."""
        game = self.game
        if not (pressed(keydown_event, 'A') or (pressed(keydown_event, 'SMART_A') and not self.config.get('QUICK_ACTION'))):
            return
        if game.movement.world_frozen or game.pause_requested or game.options_requested or game.auto_grind_requested:
            return
        game.cmd_menu_requested = True
        game.smart_a_pending = bool(game.config.get('SMART_A'))
        game.movement.resolve_pending_freezes()

    def press_start(self, keydown_event: Event) -> None:
        """START: pause, or unpause. NES CheckInputs: START only pauses from the map, not while a window is up or the
        light grows. The hero finishes the step under way first (resolve_pending_freezes), and the pause takes the
        place of anything else asked for."""
        if not pressed(keydown_event, 'START'):
            return
        game = self.game
        if game.paused:
            game.paused = False
        elif not (game.cmd_menu.launch_signaled or game.cmd_menu.menu.is_enabled() or game.movement.light_growing):
            game.pause_requested = True
            game.cmd_menu_requested = False
            self.clear_requests()
            game.movement.resolve_pending_freezes()

    def press_select(self, keydown_event: Event) -> None:
        """SELECT (U) or Tab: the options overlay (src/options_overlay.py), not NES (the NES map ignores SELECT)."""
        if keydown_event.key in OPTIONS_KEYS:
            self.request('options_requested')

    # This game's keys

    def press_message_log(self, keydown_event: Event) -> None:
        """L (MESSAGE LOG): the message log (src/message_log.py), when the MESSAGE LOG option is on."""
        if pressed(keydown_event, 'MESSAGE_LOG') and self.game.config.get('MESSAGE_LOG'):
            self.request('message_log_requested')

    def press_play_stats(self, keydown_event: Event) -> None:
        """P (STATS): the stats page (src/stats_screen.py), when the STATS PAGE option is on."""
        if pressed(keydown_event, 'PLAY_STATS') and self.config.get('STATS_PAGE'):
            self.request('play_stats_requested')

    def press_player_two(self, keydown_event: Event) -> None:
        """Player 2's A (co-op, src/player_two_menu.py): the second hero's command window, in a party."""
        if pressed(keydown_event, 'P2_A') and in_party_mode(self.game):
            self.request('player_two_menu_requested')

    def press_trophies(self, keydown_event: Event) -> None:
        """T (TROPHIES): the achievements page (src/achievements.py), when the ACHIEVEMENTS option is on."""
        if pressed(keydown_event, 'TROPHIES') and self.config.get('ACHIEVEMENTS'):
            self.request('achievements_requested')

    def press_auto_grind(self, keydown_event: Event) -> None:
        """G: auto-grind (src/auto_grind.py), when the AUTO-GRIND option is on. While it runs, G (or any key but 1 to
        5) stops it before it gets here (AutoGrind.real_key)."""
        if pressed(keydown_event, 'AUTO_GRIND') and self.config.get('AUTO_GRIND'):
            self.request('auto_grind_requested')

    def press_dungeon_map(self, keydown_event: Event) -> None:
        """M: the dungeon map (src/dungeon_map.py). Only on a dark map, with the DUNGEON MAP option ON."""
        if pressed(keydown_event, 'MAP') and self.game.current_map.is_dark and dungeon_map_enabled(self.config):
            self.request('dungeon_map_requested')

    def press_save_state(self, keydown_event: Event) -> None:
        """Shift + F1/F2/F3 saves a save state in slot 1/2/3 and F1/F2/F3 loads it (src/save_state.py), when the SAVE
        STATES option is on. It's carried out at the end of the map frame once it's due (run_due_state_request)."""
        names = actions_for_event(keydown_event)
        state_request = next(((kind, slots[name]) for name in names for kind, slots in STATE_ACTIONS if name in slots),
                             None)
        if state_request is not None and self.config.get('SAVE_STATES') and not free_roaming(self.game):
            # Not while the heroes roam apart (src/sessions.py): a state is one hero's play
            self.request('state_request', state_request)

    def press_rewind(self, keydown_event: Event) -> None:
        """Backspace: start rewinding (src/rewind.py), when the REWIND option is on and the map isn't held. It goes on
        until Backspace is let go (Game._handle_pygame_events)."""
        if pressed(keydown_event, 'REWIND') and not free_roaming(self.game):
            self.game.rewind.start()  # not while the heroes roam apart: the rewind is one hero's play

    def press_help(self, keydown_event: Event) -> None:
        """H: the controls, one dialog box page per group of keys, with the keys as they are bound
        (data/text/intro_lookup_table.py)."""
        if pressed(keydown_event, 'HELP'):
            control_info = ControlInfo(self.game.config)
            # one page per group of keys, so nothing runs past the bottom of the dialog box; not kept in the
            # message log, which is for what the NPCs said
            with self.game.cmd_menu.not_logged(), self.game.play_clock.stopped():
                self.game.cmd_menu.show_text_in_dialog_box(control_info.help_pages)

    def press_quest_journal(self, keydown_event: Event) -> None:
        """Q (the JOURNAL key): the quest journal (src/quest_journal.py): one dialog box page per goal the hero has
        learned of, with what was said of it and who said it if QUEST JOURNAL is set to HINTS. Once the hero has a
        record to read again (src/records.py: Erdrick's Tablet, King Lorik's charge), the JOURNAL window first asks
        for the goals or a record. With it OFF (the NES), Q does nothing."""
        if not pressed(keydown_event, 'QUEST_JOURNAL'):
            return
        setting = self.game.config.get('QUEST_JOURNAL', JOURNAL_OFF)
        if setting == JOURNAL_OFF:
            return
        game = self.game
        # the message log is for what the NPCs said, and the play time for what is played
        with game.cmd_menu.not_logged(), game.play_clock.stopped():
            records = known_records(game.story_flags, game.dungeon_map)
            chosen = choose_journal_page(game, records) if records else GOALS_ENTRY
            if chosen is None:
                return
            if isinstance(chosen, Record):
                pages = list(chosen.pages(game.player.name, game._))
            else:
                quote = language_named(game.config.get('LANGUAGE')).quote
                pages = journal_pages(game_progress(game), hints=setting == JOURNAL_HINTS, _=game._, quote=quote)
            game.cmd_menu.show_text_in_dialog_box(pages)

    def press_smart_a_key(self, keydown_event: Event) -> None:
        """QUICK ACTION: the SMART A key (Enter, src/controls.py) on the map runs TALK, TAKE, DOOR or STAIRS when one
        applies (smart_command). Unlike A with SMART A on, it opens nothing when none does. With QUICK ACTION off the
        key is the A button (press_a)."""
        if pressed(keydown_event, 'SMART_A') and self.config.get('QUICK_ACTION'):
            self.run_smart_command()

    def smart_command(self) -> str | None:
        """The command that applies where the hero stands, in this order: TALK if someone is in front of him (or
        across a counter), TAKE on a treasure chest, DOOR next to a locked door with a Magic Key to open it, STAIRS on
        stairs; None if none does."""
        game = self.game
        player = game.player
        if game.cmd_menu.check_across_from_npc() and not game.game_state.is_initial_dialog:
            return 'TALK'
        if player.current_tile == 'TREASURE_BOX':
            return 'TAKE'
        if game.cmd_menu.find_door() is not None and 'Magic Key' in player.inventory:
            return 'DOOR'
        if player.current_tile in STAIR_TILES and (player.row, player.column) in game.current_map.staircases:
            return 'STAIRS'
        return None

    def run_smart_command(self) -> bool:
        """Do the smart command (smart_command), as if chosen in the COMMAND window: the menu button sound
        (WndAPressed), and the stats window for the ones that show a dialog. Returns whether one ran.

        It follows the A button's rule: NES GameEngineLoop only reads commands between steps (DoJoyUp etc. move a
        whole tile before returning to CheckInputs). Mid-step, or while a pause or the command window is pending or
        open (where Enter picks a menu item), nothing runs."""
        game = self.game
        if game.player.is_moving or game.movement.world_frozen or game.movement.freeze_pending:
            return False
        # A freeze pending at the end of a step resolves before the frame's post-move checks, so the tiles in front of
        # the hero would still be from before the step: TALK would find the hero himself in front of him
        game.update_hero_facing()
        command = self.smart_command()
        if command is None:
            return False
        cmd_menu = game.cmd_menu
        if command in ('TALK', 'TAKE'):
            game.drawer.draw_hovering_stats_window(game.screen, game.player, color=game.color)
        cmd_menu.play_menu_button_sound()
        {'TALK': cmd_menu.talk, 'TAKE': cmd_menu.take, 'DOOR': cmd_menu.door, 'STAIRS': cmd_menu.stairs}[command]()
        return True

    def press_speed_key(self, keydown_event: Event) -> None:
        """Keys 1 to 5, when the GAME SPEED option is on: normal, 2x, 4x, 8x or 16x game speed (60.1, 120.2, 240.4,
        480.8 or 961.6 FPS). It applies everywhere: the map, battles, dialogs, menus and effects (src/waiting.py reads
        these keys in their loops and waits too, without this text)."""
        speed = requested_speed(keydown_event)
        if speed is None or not speed_keys_enabled():
            return
        set_game_speed(speed)
        self.announce_game_speed(speed)

    def announce_game_speed(self, speed: int) -> None:
        """Say the new game speed over the map: after a speed key (press_speed_key), or the gamepad's NEXT SPEED
        button (SPEED_CHANGED, src/waiting.py step_game_speed)."""
        _ = self.game._
        fps = f'{self.game.fps:.1f}'
        if speed == 1:
            speed_text = _("Game set to normal speed.\n({} FPS)").format(fps)
        else:
            speed_text = _("Game set to {}x speed.\n({} FPS)").format(speed, fps)
        self.game.draw_temporary_text(speed_text)

    def toggle_fullscreen(self, keydown_event: Event) -> None:
        """F11: between fullscreen and a window, kept with the global settings."""
        if not pressed(keydown_event, 'FULLSCREEN'):
            return
        game = self.game
        game.fullscreen_enabled = not game.fullscreen_enabled
        if game.fullscreen_enabled:
            remember_windowed_size()
            game.flags = FULLSCREEN | SCALED
            mode_text = game._("Fullscreen mode enabled")
        else:
            game.flags = RESIZABLE | SCALED
            mode_text = game._("Windowed mode enabled")
        # Recreate the window with new flags, in the view it had (src/view.py). The display filters let go of the old
        # window's renderer first, and take the new one at the next frame (src/display_filters.py).
        PRESENTER.release()
        nes_res = self.config["NES_RES"]
        win_width, win_height = nes_res[0] * game.scale, nes_res[1] * game.scale
        game.screen = game.set_screen(win_height, win_width)
        game.cmd_menu.screen = game.screen
        game.camera.screen = game.screen
        # back in a window: the zoom it had before going fullscreen (src/zoom.py)
        restore_windowed_size()
        set_caption(game._("Dragon Warrior"))
        game.settings.update(fullscreen=game.fullscreen_enabled)
        game.draw_temporary_text(mode_text)

    def toggle_auto_battle(self, keydown_event: Event) -> None:
        """F4 (AUTO FIGHT), with CHEATS on: auto-battle on or off."""
        if not (pressed(keydown_event, 'AUTO_BATTLE') and self.config.get('CHEAT_KEYS')):
            return
        game = self.game
        game.auto_battle = not game.auto_battle
        if game.auto_battle:
            mode_text = game._("Auto-battle enabled\n(Repeats: {})").format(game.battle_ctrl.last_battle_action)
        else:
            mode_text = game._("Auto-battle disabled")
        game.draw_temporary_text(mode_text)

    def toggle_invulnerability(self, keydown_event: Event) -> None:
        """F9 (INVINCIBLE), with CHEATS on: invulnerability on or off."""
        if not (pressed(keydown_event, 'INVULNERABLE') and self.config.get('CHEAT_KEYS')):
            return
        game = self.game
        game.invulnerable = not game.invulnerable
        mode_text = game._("Invulnerability enabled") if game.invulnerable else game._("Invulnerability disabled")
        game.draw_temporary_text(mode_text)

    # What MAP_REQUESTS open: each runs its own loop over the map until it's closed, so nothing else runs meanwhile

    def open_options(self) -> None:
        """The options overlay (src/options_overlay.py): the map, the NPCs, the timers and the pop-up window all wait,
        as they do for a dialog."""
        OptionsOverlay(self.game).run()
        self.game.set_view()  # the VIEW row: the map is drawn across the new width from the next frame

    def open_dungeon_map(self) -> None:
        DungeonMapOverlay(self.game).run()

    def open_message_log(self) -> None:
        MessageLogScreen(self.game).run()

    def open_play_stats(self) -> None:
        StatsScreen(self.game).run()

    def open_player_two_menu(self) -> None:
        open_player_two_menu(self.game)

    def open_achievements(self) -> None:
        AchievementsScreen(self.game).run()

    def start_auto_grind(self) -> None:
        self.game.auto_grind.start()


# The MapHotkeys methods every key press goes through, in this order (looked up by name, so a test can patch one). B does
# nothing on the map: in the COMMAND window it is read with the other buttons (CommandMenu.select_command).
KEY_HANDLERS = (
    'press_a',
    'press_start',
    'press_select',
    'press_message_log',
    'press_play_stats',
    'press_trophies',
    'press_player_two',
    'press_auto_grind',
    'press_dungeon_map',
    'press_help',
    'press_quest_journal',
    'press_smart_a_key',
    'press_speed_key',
    'toggle_fullscreen',
    'toggle_auto_battle',
    'toggle_invulnerability',
    'press_save_state',
    'press_rewind',
)
