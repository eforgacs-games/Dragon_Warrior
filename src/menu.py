import functools
import json
import random
from os.path import join

from src.spells import Spell
from typing import Any, Callable, Collection, Iterable, Tuple, List

from pygame import Surface, display, KEYDOWN, Rect, event, K_UP, K_DOWN, K_w, K_s, USEREVENT, time, transform
from pygame.sprite import Group
from src.waiting import game_ticks as get_ticks  # game time: runs N times as fast at speed N

from data.text.dialog_lookup_table import DialogLookup
from src.calculation import Calculation, get_tile_id_by_coordinates
from src.color import BLACK
from src.common import A_OR_B_KEYS, ANY_BUTTON_KEYS, accept_keys, reject_keys, Graphics, set_gettext_language
from src.command_window import WND_ABORT, CommandWindow
from src.cursor import BlinkingCursor, draw_cursor_tile
from src.waiting import is_any_key_held, quit_if_requested, wait
from src.directories import Directories
from src.items import DEATH_NECKLACE_GOLD, GOLD, INVENTORY_SLOTS, MAX_GOLD, MAX_HERBS, MAX_KEYS, \
    NON_DISCARDABLE_ITEMS, UNSLOTTED_ITEMS, armor, hidden_items, inventory_list, roll_treasure_gold, treasure
from src.constants import DUNGEON_MAPS, FAIRY_WATER_TIMER, OUTSIDE_DESTINATIONS, RAINBOW_BRIDGE_COORDINATES, \
    RAINBOW_DROP_COORDINATES, REPEL_SPELL_TIMER, RETURN_DESTINATION, SILVER_HARP_ENEMIES
from src.dialog_box import ARROW_COLUMN, DIALOG_COLUMNS, DIALOG_ROWS, OPEN_QUOTES, SCROLL_ROWS_PER_FRAME, \
    DialogBuffer, DialogStep, ScrollStep, frames_per_character
from src.direction import Direction
from src.maps import CharlockB1, DragonWarriorMap, map_lookup
from src.maps_functions import get_center_point
from src.menu_functions import get_opposite_direction
from src.options_screen import MODERN, options_from_config, options_to_save
from src.sound import Sound
from src.story_flags import SAVE_KEY as STORY_FLAGS_SAVE_KEY
from src.text import draw_text, set_font_by_ascii_chars
from src.waiting import handle_speed_key
from src.window_renderer import draw_window
from src.windows import COMMAND_BORDER_LAYOUT, COMMAND_CURSOR_TILES, COMMAND_ENTRIES, COMMAND_LAYOUT, COMMAND_TITLE, \
    COMMAND_WINDOW, COUNTED_ITEMS, DIALOG_LAYOUT, ITEM_COUNT_TILE_COLUMN, ITEM_MENU_CURSOR_TILE_COLUMN, \
    ITEM_MENU_TEXT_TILE_COLUMN, \
    ITEM_MENU_X, ITEM_MENU_Y, ITEM_NAME_HALVES, POPUP_WINDOW, SPELL_MENU_TITLE_TILE_COLUMN, \
    STATUS_EQUIPMENT_TILE_COLUMN, STATUS_EQUIPMENT_TILE_ROWS, STATUS_LAYOUT, STATUS_NAME_TILE_COLUMN, \
    STATUS_NAME_TILE_ROW, STATUS_VALUE_RIGHT_TILE_COLUMN, STATUS_VALUE_TILE_ROWS, STATUS_WINDOW, YES_NO_LAYOUT, \
    YES_NO_WINDOW, item_menu_entry_tile_row, item_menu_layout, item_menu_window, Window, name_halves

arrow_fade = USEREVENT + 1
# The COMMAND window's commands, in WndSelResults order (NCC_TALK $00 to NCC_TAKE $07; src/windows.py COMMAND_ENTRIES):
# the CommandMenu methods Bank03 NCCmdSelected and CheckCmdWndResults run for each
COMMAND_METHODS = ('talk', 'status', 'stairs', 'search', 'spell', 'item', 'door', 'take')

# The dialog window: x, y, width, height in 16x16 blocks (NES WND_DIALOG, screen tiles 4-27 x 18-27)
DIALOG_WINDOW = (2, 9, 12, 5)
DIALOG_FPS = 60


class Menu:
    def __init__(self):
        self.launch_signaled = False
        self.skip_text = False
        time.set_timer(arrow_fade, 530)


class CommandMenu(Menu):

    def __init__(self, game):
        super().__init__()
        self.game = game
        self.player = self.game.player

        self.screen = self.game.screen
        self.current_map: DragonWarriorMap = self.game.current_map
        self.current_battle = None
        self.current_tile = self.player.current_tile
        self.characters = self.current_map.characters
        self.map_name = self.current_map.__class__.__name__

        self.graphics = Graphics(self.current_map.config)
        self.dialog_buffer = DialogBuffer()
        self._dialog_frame_deadline = 0.0
        self._dialog_fonts = {}
        self.directories = Directories(self.current_map.config)
        self.sound = Sound(self.current_map.config)
        self.calculation = Calculation(self.current_map.config)
        config: dict = self.game.game_state.config
        self.dialog_lookup = DialogLookup(self, config)
        self._ = set_gettext_language(config['LANGUAGE'])
        # The COMMAND window (CmdNonCmbtDat): whether it is up and selecting, the selected entry, and the NES cursor
        # (src/command_window.py, src/cursor.py); drawn by draw_command_window
        self.menu = CommandWindow()
        self.cursor = self.menu.cursor

    @property
    def camera_position(self) -> tuple[float, float]:
        """Where the map is drawn on the screen: always the game's camera as it is now. NES RemoveWindow (Bank00, $A7A2)
        redraws the blocks under a closing window at their offsets from the hero (StartSignedXPos, from the window
        position relative to the screen's center), so they line up with the map around them and nothing else moves.
        This used to be a copy, taken when the menu was made (before the first step on a map, so the old map's camera)
        and then in Game.move before the camera moved for the frame (one step increment behind); closing the COMMAND
        window then drew the whole map 2 pixels off, or somewhere else on the map entirely, until the next frame."""
        return self.game.camera.pos

    @property
    def background(self) -> Surface:
        """The surface the map is drawn on, the game's own: Drawer.draw_all replaces it on a map's first frame, after
        the new map's CommandMenu is made, so a copy taken here would be the previous one."""
        return self.game.drawer.background

    @property
    def color(self) -> tuple[int, int, int]:
        """The window color: Game.color, which Game.set_window_color sets red or white (see Game.load_window_palette).
        Every window this menu opens (dialogs, the SPELL and ITEM lists, YES/NO, shops) reads it when it's drawn."""
        return self.game.color

    def show_popup_window(self) -> None:
        """NES Dowindow WND_POPUP (Bank03): (re)draw the pop-up status window with the hero's current name, level, HP,
        MP, gold and experience, in the window color. The NES does this right after an event changes them while a
        dialog is open: buying at a shop (BuyInnStay, PurchaseTool, BuyKey, BuyFairyWater, CompWeapPurchase,
        DoneSellingTool), the inn's heal (BuyInnStay, while the screen is faded out), HEAL and HEALMORE (PlyrAddHP),
        an herb (HerbHeal), spending MP on a spell (PlyrCastSpell), the MP wizard (LD2DE) and a chest of gold
        (GainGoldDialog). The window then stays up until the hero moves, like the one the COMMAND window opens."""
        drawer = self.game.drawer
        drawer.display_hovering_stats = True
        drawer.hovering_stats_displayed = True
        drawer.draw_hovering_stats_window(self.screen, self.player, self.color)
        if not self.game.game_state.config['NO_BLIT']:
            tile_size = self.game.game_state.config['TILE_SIZE']
            left, top, width, height = POPUP_WINDOW
            display.update(Rect(left * tile_size, top * tile_size, width * tile_size, height * tile_size))

    def redraw_command_window(self, clip: Rect | None = None) -> None:
        """Redraw the COMMAND window as it is (draw_command_window: its entries and cursor), if it's open, or only its
        part inside ``clip``."""
        config = self.game.game_state.config
        if config['NO_BLIT'] or not self.menu.is_enabled():
            return
        tile_size = config['TILE_SIZE']
        command_rect = Rect(COMMAND_WINDOW.x * tile_size, COMMAND_WINDOW.y * tile_size,
                            COMMAND_WINDOW.width * tile_size, COMMAND_WINDOW.height * tile_size)
        if clip is not None and not clip.colliderect(command_rect):
            return
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(command_rect if clip is None else clip.clip(command_rect))
        self.draw_command_window()
        self.screen.set_clip(previous_clip)

    def remove_window(self, window: Window | tuple[int, int, int, int]) -> None:
        """NES RemoveWindow (Bank00, LA7A2) for a foreground window: WindowSequence (Bank01) calls it as soon as a
        selection window (spells, inventories, YES/NO, BUY/SELL) has been answered. Each of its blocks goes back to
        what it covered: the background windows that are open (ClearWndBuf -> UncoverWindow), or else the map
        (ModWindowBlock). Only that area is redrawn; the windows that are still open stay as they are.

        Here the background windows are the pop-up, the COMMAND window and the dialog window, drawn over the map as
        it is now, at the camera's current position."""
        config = self.game.game_state.config
        if config['NO_BLIT']:
            return
        tile_size = config['TILE_SIZE']
        rect = Rect(window[0] * tile_size, window[1] * tile_size, window[2] * tile_size, window[3] * tile_size)
        screen = self.screen
        previous_clip = screen.get_clip()
        screen.set_clip(rect)
        drawer = self.game.drawer
        screen.fill(BLACK)
        if drawer.background is not None:
            screen.blit(drawer.background, self.game.camera.pos)
        if self.current_map.is_dark and config['ENABLE_DARKNESS']:
            drawer.draw_darkness(screen)
        self.redraw_command_window(rect)
        if drawer.display_hovering_stats:
            drawer.draw_hovering_stats_window(screen, self.player, self.color)
        dialog_rect = Rect(DIALOG_WINDOW[0] * tile_size, DIALOG_WINDOW[1] * tile_size, DIALOG_WINDOW[2] * tile_size,
                           DIALOG_WINDOW[3] * tile_size)
        if rect.colliderect(dialog_rect):
            self.draw_dialog_window()
        screen.set_clip(previous_clip)
        display.update(rect)

    def save(self):
        """NES SaveData (Bank03): the hero's experience, gold, items, equipment, name, HP and MP, plus the ModsnSpells,
        PlayerFlags and StoryFlags bytes whole (game slot offsets $00-$18 in reference/sram-doc.txt). The worn items
        are saved with the hero and the story bits as one StoryFlags entry. Like the NES, the treasure chest history
        and the repel timer aren't saved (Game.load_game)."""
        # TODO: Add multiple save slots.
        save_dict = {
            'Name': self.player.name,
            'Experience': self.player.total_experience,
            'Gold': self.player.gold,
            'CurrentHP': self.player.current_hp,
            'CurrentMP': self.player.current_mp,
            'Weapon': self.player.weapon,
            'Armor': self.player.armor,
            'Shield': self.player.shield,
            'WearingDragonScale': self.player.wearing_dragon_scale,
            'WearingFightersRing': self.player.wearing_fighters_ring,
            'WearingCursedBelt': self.player.wearing_cursed_belt,
            'WearingDeathNecklace': self.player.wearing_death_necklace,
            'Inventory': self.player.inventory,
            'Spells': self.player.spells,
            'CurrentMap': self.game.current_map.identifier,
            'PlayerRow': self.player.row,
            'PlayerColumn': self.player.column,
            STORY_FLAGS_SAVE_KEY: self.game.story_flags.to_save(),
            # NES SaveData (LFA7D): the message speed is saved with each log (offset $16); so are the dialog style
            # and NPCS MAKE WAY (src/options_screen.py)
            **options_to_save(options_from_config(self.game.game_state.config)),
        }
        json_object = json.dumps(save_dict, indent=4)
        with open(join(self.directories.save_dir, f'save_slot_{self.player.adventure_log}.json'),
                  'w') as output_save_file:
            output_save_file.write(json_object)

    def set_king_lorik_dialog(self, left_throne_room: bool = False):
        # NES DoKingDialog: carrying Gwaelin comes first, then whether the hero has left the throne room yet
        king_lorik = self.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']
        if self.game.story_flags.carrying_gwaelin:
            king_lorik['dialog'] = king_lorik['carrying_princess_dialog']
        elif left_throne_room:
            king_lorik['dialog'] = king_lorik['returned_dialog']
        else:
            king_lorik['dialog'] = king_lorik['post_initial_dialog']

    def npc_is_across_counter(self, character_dict):
        return self.player.next_tile_id == 'WOOD' and (
            character_dict['character'].row, character_dict['character'].column) == self.player.next_next_coordinates

    def launch_dialog(self, dialog_character, current_map):
        if self.game.story_flags.dragonlord_defeated and self.game.ending.has_victory_dialog(dialog_character,
                                                                                              current_map):
            # NES LD134: once the Dragonlord is dead, every NPC says one of the victory lines instead (but not
            # Gwaelin in the Swamp Cave, who's a map block on the NES; see Ending.has_victory_dialog)
            self.show_text_in_dialog_box(self.game.ending.npc_dialog(dialog_character, current_map), add_quotes=True,
                                         skip_text=self.skip_text)
            return
        character = self.dialog_lookup.lookup_table[current_map.identifier].get(dialog_character)
        if character:
            if character.get('dialog'):
                self.dialog_lookup.camera_position = self.camera_position
                self.show_text_in_dialog_box(character['dialog'], add_quotes=True, skip_text=self.skip_text)
            else:
                print(f"Character has no dialog: {dialog_character}")
                self.show_text_in_dialog_box(self._("I have nothing to say."), add_quotes=True,
                                             skip_text=self.skip_text)
        else:
            print(f"Character not in lookup table: {dialog_character}")
            self.show_text_in_dialog_box(self._("I have nothing to say."), add_quotes=True, skip_text=self.skip_text)

    def show_line_in_battle_dialog_box(self, line: str):
        """The encounter line. A fight opens a fresh dialog window (NES InitFight: ShowWindow WND_DIALOG, which runs
        ClearDialogOutBuf), so earlier text is gone; the fight's later messages scroll on below this one."""
        self.dialog_buffer.clear()
        self.show_line_in_dialog_box(line, add_quotes=False, skip_text=True, hide_arrow=True, disable_sound=True)

    def show_line_in_dialog_box(self, line: str | functools.partial, add_quotes: bool = True,
                                temp_text_start: int | None = None, skip_text: bool = False, hide_arrow=False,
                                disable_sound=False, letter_by_letter=True,
                                advance_keys: Collection[int] | None = None):
        """Shows a single line in a dialog box.
        :param hide_arrow: Whether to show the continuation arrow
        (blinking down arrow at bottom of dialog box).
        :param line: The line of text to print.
        :param skip_text: Whether to automatically skip the text.
        :param add_quotes: Adds single quotes to be displayed on the screen.
        :param temp_text_start: The time at which temporary text started.
        :param disable_sound: Whether to disable the sound.
        :param letter_by_letter: Whether to print the text letter by letter.
        :param advance_keys: The keys that end the wait for a key, and whether holding one does (see
            wait_for_dialog_key); by default, the NES rule for a wait with or without the arrow.
        """
        tile_size = self.game.game_state.config['TILE_SIZE']
        if line:
            if isinstance(line, str):
                self.show_text_line_in_dialog_box(line, add_quotes, disable_sound, hide_arrow, letter_by_letter,
                                                  skip_text, temp_text_start, tile_size, advance_keys=advance_keys)
            else:
                # if the line is a method
                line()

    def add_dialog_quotes(self, line: str) -> str:
        if self.game.game_state.config['LANGUAGE'] == 'Korean' and not line.isascii():
            return f"'{line}'"
        return f"`{line}’"

    def show_text_line_in_dialog_box(self, line, add_quotes, disable_sound, hide_arrow, letter_by_letter, skip_text,
                                     temp_text_start, tile_size, advance_keys: Collection[int] | None = None):
        """Prints one message into the dialog window the way the NES does (Bank01 DoDialog, see src/dialog_box.py):
        it goes below whatever the window already shows, letter by letter, scrolling the window up when it reaches
        the bottom. Then it waits for a key, with the blinking down arrow unless hide_arrow is set (DoWait)."""
        config = self.game.game_state.config
        if add_quotes:
            line = self.add_dialog_quotes(line)
        animate = letter_by_letter and not config['NO_WAIT']
        waits_for_key = not skip_text and not temp_text_start
        # NES TXT_WAIT (arrow) vs TXT_END1 (no arrow): they move the cursor differently afterwards
        shows_arrow = waits_for_key and not hide_arrow
        frames = frames_per_character(config['TEXT_SPEED'])
        self._dialog_frame_deadline = float(get_ticks())

        if self.modern_dialog:
            # Modern dialog style: every message starts on a fresh window, replacing the one before it
            self.dialog_buffer.clear()
        self.draw_dialog_window()
        self.run_dialog_steps(self.dialog_buffer.print_message(line, quoted=line.startswith(OPEN_QUOTES)),
                              animate, frames, disable_sound)
        if shows_arrow:
            self.run_dialog_steps(self.dialog_buffer.start_wait(), animate, frames, disable_sound)
        else:
            self.run_dialog_steps(self.dialog_buffer.end_message(), animate, frames, disable_sound)
        if not animate:
            self.draw_dialog_window()

        self.wait_for_dialog_key(shows_arrow, skip_text, temp_text_start, disable_sound, advance_keys)

        if shows_arrow:
            self.draw_dialog_arrow(False)  # DoWait: TxtClearArrow
            if not self.modern_dialog:  # (the next modern message clears the window anyway, so it needn't scroll)
                self.run_dialog_steps(self.dialog_buffer.finish_wait(), animate, frames, disable_sound)

    @property
    def modern_dialog(self) -> bool:
        """The Modern dialog style (src/options_screen.py): each message replaces the last one, as this game drew dialog
        before it copied the NES window (src/menu.py and src/text.py before PR #245). Otherwise the text scrolls on below
        what the window shows, like the NES (Classic, the default). Both print letter by letter at the message speed,
        with the NES text beep."""
        return self.game.game_state.config.get('DIALOG_STYLE') == MODERN

    def wait_for_dialog_key(self, shows_arrow: bool, skip_text: bool, temp_text_start: int | None,
                            disable_sound: bool, advance_keys: Collection[int] | None = None) -> None:
        """Waits for one of the NES buttons that end this wait (or not at all with skip_text, or for one second with
        temp_text_start). Other keys are ignored, as the NES ignores the other buttons.

        - With the arrow, NES DoWait (Bank01, reached from WaitFound for TXT_WAIT): TxtCheckInput masks JoypadBtns with
          IN_A_OR_B, so only A or B goes on, and since it reads the buttons as they are, one still held from before
          goes on at once (DoWait checks before it even draws the arrow).
        - Without it, the end of the text, where the NES waits in WaitForBtnRelease / WaitForBtnPress (Bank03, from
          ResumeGamePlay, PlayerInitControl, ExitFight and the like): any button, D-pad, START and SELECT included, but
          only a new press, since a held button has to be let go first.

        :param advance_keys: Other keys to wait for instead (DeathText's A or START, say); holding one of them counts,
            as these waits read JoypadBtns directly too.
        """
        held_counts = shows_arrow or advance_keys is not None
        if advance_keys is None:
            advance_keys = A_OR_B_KEYS if shows_arrow else ANY_BUTTON_KEYS
        while True:
            if skip_text or (temp_text_start and get_ticks() - temp_text_start >= 1000):
                if not skip_text and not disable_sound:
                    self.sound.play_sound(self.directories.menu_button_sfx)
                return
            if held_counts and is_any_key_held(advance_keys):
                break
            if shows_arrow:
                self.draw_dialog_arrow(self.game.show_arrow)
            if self.read_dialog_events(advance_keys):
                break
        if not disable_sound:
            self.sound.play_sound(self.directories.menu_button_sfx)
        event.clear(KEYDOWN)

    def read_dialog_events(self, advance_keys: Collection[int]) -> bool:
        """Takes the queued events, keeping the arrow blinking; returns whether one was a press of advance_keys."""
        for current_event in event.get():
            quit_if_requested(current_event)
            if handle_speed_key(current_event):  # keys 1 to 4: the game speed, nothing else
                continue
            if current_event.type == KEYDOWN and current_event.key in advance_keys:
                return True
            if current_event.type == arrow_fade:
                self.game.show_arrow = not self.game.show_arrow
        return False

    def run_dialog_steps(self, steps: Iterable[DialogStep], animate: bool, frames_per_char: int,
                         disable_sound: bool) -> None:
        """Shows each step of DialogBuffer's printing: a character (with the text beep, when it gets one) and its
        MessageSpeed + 1 frame wait (TextToPPU), or a scroll of the whole window (ScrollDialog).

        TextToPPU starts the text SFX (InitMusicSFX -> DoSFX, which silences any SFX still playing right away), puts the
        tile in the PPU buffer and then waits for the NMI. That first NMI draws the tile and, in UpdateSound, writes the
        new beep to the APU. So the character and its beep appear one frame after the old beep was cut off: with beeps
        two columns apart, each one plays for 2 * (MessageSpeed + 1) - 1 frames, then there is one silent frame."""
        for step in steps:
            if isinstance(step, ScrollStep):
                if animate:
                    self.animate_dialog_scroll()
                continue
            beep = step.beep and not disable_sound
            if beep:
                self.sound.stop_sfx()
            if animate:
                self.wait_dialog_frames(1)
            if beep:
                self.sound.play_sfx(self.directories.text_beep_sfx)
            if animate:
                self.draw_dialog_row(step.row, up_to_column=step.column + 1)
                if frames_per_char > 1:
                    self.wait_dialog_frames(frames_per_char - 1)

    def animate_dialog_scroll(self) -> None:
        """NES ScrollUpdate: one frame, then the 8 rows are redrawn two per frame, top to bottom (5 frames)."""
        self.wait_dialog_frames(1)
        for first_row in range(0, DIALOG_ROWS, SCROLL_ROWS_PER_FRAME):
            for row in range(first_row, first_row + SCROLL_ROWS_PER_FRAME):
                self.draw_dialog_row(row)
            self.wait_dialog_frames(1)

    def wait_dialog_frames(self, frames: int) -> None:
        """Waits whole NES frames, against a running deadline so that the per-character waits don't drift."""
        if self.game.game_state.config['NO_WAIT']:
            return
        now = get_ticks()
        self._dialog_frame_deadline = max(self._dialog_frame_deadline, now) + frames * 1000 / DIALOG_FPS
        delay = int(self._dialog_frame_deadline - now)
        if delay > 0:
            wait(delay)

    def dialog_cell_rect(self, row: int, column: int = 0, columns: int = DIALOG_COLUMNS) -> Rect:
        """Screen rect of dialog text cells. The text starts one NES tile inside the window's border (screen tile
        column 5, row 19), and each character is one NES tile."""
        tile_size = self.game.game_state.config['TILE_SIZE']
        nes_tile = tile_size // 2
        return Rect((DIALOG_WINDOW[0] * 2 + 1 + column) * nes_tile, (DIALOG_WINDOW[1] * 2 + 1 + row) * nes_tile,
                    columns * nes_tile, nes_tile)

    def draw_dialog_window(self) -> None:
        """Draws the dialog window (DialogDat, generated by src/window_renderer.py) and all 8 rows of its text
        buffer."""
        window_rect = draw_window(self.screen, DIALOG_LAYOUT, self.color, self.game.game_state.config)
        for row in range(DIALOG_ROWS):
            self.draw_dialog_row(row, update=False)
        if not self.game.game_state.config['NO_BLIT']:
            display.update(window_rect)

    def draw_dialog_row(self, row: int, up_to_column: int = DIALOG_COLUMNS, update: bool = True) -> None:
        """Draws one row of the dialog buffer, or its first up_to_column characters while it is being printed."""
        cells = self.dialog_buffer.rows[row][:up_to_column]
        if all(len(cell) == 1 for cell in cells):
            self.draw_dialog_text(''.join(cells).rstrip(), self.dialog_cell_rect(row), update)
            return
        # A two-character tile (TXT_PRD_QUOTE, '.’') fills one cell, so draw the row in runs around it
        self.draw_dialog_text('', self.dialog_cell_rect(row), update=False)
        start = 0
        for column, cell in enumerate(cells + ['']):
            if len(cell) != 1:
                if column > start:
                    self.draw_dialog_text(''.join(cells[start:column]), self.dialog_cell_rect(row, start, column - start),
                                          update=False)
                if cell:
                    self.draw_dialog_text(cell, self.dialog_cell_rect(row, column, 1), update=False, squeeze=True)
                start = column + 1
        if update:
            display.update(self.dialog_cell_rect(row))

    def draw_dialog_arrow(self, visible: bool) -> None:
        """NES TxtWaitAnim: the down arrow blinks in the middle of the row the cursor is on. In the Modern dialog
        style it's at the bottom of the window, where this game drew it before PR #245."""
        row = DIALOG_ROWS - 1 if self.modern_dialog else self.dialog_buffer.row
        self.draw_dialog_text('▼' if visible else '', self.dialog_cell_rect(row, ARROW_COLUMN, 1), update=True)

    def draw_dialog_text(self, text: str, cells: Rect, update: bool, squeeze: bool = False) -> None:
        """Draws text left-aligned in the given dialog cells. ``squeeze`` narrows it to fit them (two characters that
        are one NES tile)."""
        config = self.game.game_state.config
        if config['NO_BLIT']:
            return
        self.screen.fill(BLACK, cells)
        if text and config['RENDER_TEXT']:
            is_ascii = text.strip('’(↑ ← ↓ →)▼').isascii()
            if is_ascii not in self._dialog_fonts:
                self._dialog_fonts[is_ascii] = set_font_by_ascii_chars([text], cells.height, None, self.directories)
            text_surface = self._dialog_fonts[is_ascii].render(text, True, self.color)
            if squeeze and text_surface.get_width() > cells.width:
                text_surface = transform.scale(text_surface, (cells.width, text_surface.get_height()))
            previous_clip = self.screen.get_clip()
            self.screen.set_clip(cells)
            self.screen.blit(text_surface, text_surface.get_rect(midleft=cells.midleft))
            self.screen.set_clip(previous_clip)
        if update:
            display.update(cells)

    def show_text_in_dialog_box(self, text: Tuple | List | str, add_quotes=False, temp_text_start=None, skip_text=False,
                                drop_down=True, drop_up=True, disable_sound=False, letter_by_letter=True,
                                advance_keys: Collection[int] | None = None):
        """Shows a passage of text in a dialog box.

        An important distinction between this and show_line_in_dialog_box is that this function
        will show multiple lines of text, whereas show_line_in_dialog_box will only show a single line.
        Additionally, this function will do a drop down and drop up effect by default. Opening the window
        (drop_down) starts it empty and closing it (drop_up) empties it; without them, the text carries on below
        what the window already shows.

        :param disable_sound:
        :param text: The text to print.
        :param skip_text: Whether to automatically skip the text.
        :param add_quotes: Adds single quotes to be displayed on the screen.
        :param temp_text_start: The time at which temporary text started.
        :param drop_down: Whether to display the drop-down effect.
        :param drop_up: Whether to display the drop-up effect.
        :param letter_by_letter: Whether to print the text letter by letter.
        :param advance_keys: The keys that end the wait after the last line, when it isn't the usual any button
            (see wait_for_dialog_key).
        """
        if drop_down:
            self.window_drop_down_effect(*DIALOG_WINDOW)
        if isinstance(text, str):
            self.show_line_in_dialog_box(text, add_quotes, temp_text_start, skip_text, hide_arrow=True,
                                         disable_sound=disable_sound, letter_by_letter=letter_by_letter,
                                         advance_keys=advance_keys)
        else:
            for line_index, line in enumerate(text):
                if line_index == len(text) - 1:
                    self.show_line_in_dialog_box(line, add_quotes, temp_text_start, skip_text, hide_arrow=True,
                                                 disable_sound=disable_sound, letter_by_letter=letter_by_letter,
                                                 advance_keys=advance_keys)
                else:
                    self.show_line_in_dialog_box(line, add_quotes, temp_text_start, skip_text,
                                                 disable_sound=disable_sound, letter_by_letter=letter_by_letter)
        if drop_up:
            self.window_drop_up_effect(*DIALOG_WINDOW)

    def window_drop_down_effect(self, left, top, width, height) -> None:
        """Intro effect for menus. A dialog window always opens empty (NES ShowWindow, WND_DIALOG: ClearDialogOutBuf)."""
        if (left, top, width, height) == DIALOG_WINDOW:
            self.dialog_buffer.clear()
        tile_size = self.game.game_state.config['TILE_SIZE']
        window_rect = Rect(left * tile_size, top * tile_size, width * tile_size, height * tile_size)
        for i in range(height + 1):
            black_box = Surface((tile_size * width, tile_size * i))  # lgtm [py/call/wrong-arguments]
            black_box.fill(BLACK)
            drop_down_start = get_ticks()
            # each "bar" lasts 1 frame
            while self.calculation.convert_to_frames_since_start_time(drop_down_start) < 1:
                if not self.game.game_state.config['NO_BLIT']:
                    self.screen.blit(black_box, (tile_size * left, tile_size * top))
                    display.update(window_rect)

    def window_drop_up_effect(self, left, top, width, height) -> None:
        """Outro effect for menus. Closing the dialog window throws its text away."""
        if (left, top, width, height) == DIALOG_WINDOW:
            self.dialog_buffer.clear()
        # draw all the tiles initially once
        tile_size = self.game.game_state.config['TILE_SIZE']
        camera_screen_rect = Rect(self.player.rect.x - tile_size * 8, self.player.rect.y - tile_size * 7,
                                  self.screen.get_width(), self.screen.get_height())
        if not self.current_map.is_dark:
            # if the map is dark, drawing all the tiles to the screen basically creates an exploit that shows the map
            # tiles lit up, even without a torch or radiant
            # might be good to revisit this later with just a black background?
            group_to_draw: Group = Group()
            for tile, tile_dict in self.current_map.floor_tile_key.items():
                if tile in self.current_map.tile_types_in_current_map and tile_dict.get('group'):
                    for tile_sprite in tile_dict['group']:
                        # Blocks on the other side of a roof (#90) keep the roof or blank draw_all gave them
                        if camera_screen_rect.colliderect(tile_sprite.rect) and not self.current_map.is_hidden_by_cover(
                                tile_sprite.rect.y // tile_size, tile_sprite.rect.x // tile_size):
                            group_to_draw.add(tile_sprite)
            group_to_draw.draw(self.background)

            for i in range(height - 1, -1, -1):
                black_box = Surface((tile_size * width, tile_size * i))  # lgtm [py/call/wrong-arguments]
                black_box.fill(BLACK)
                drop_up_start = get_ticks()
                while self.calculation.convert_to_frames_since_start_time(drop_up_start) < 1:
                    # draw_player_sprites(self.current_map, self.background, self.player.rect.x, self.player.rect.y)
                    if not self.game.game_state.config['NO_BLIT']:
                        for character_dict in self.current_map.characters.values():
                            character = character_dict['character']
                            if camera_screen_rect.colliderect(character.rect) and (
                                    character is self.player or
                                    not self.current_map.is_hidden_by_cover(character.row, character.column)):
                                self.background.blit(character_dict['character_sprites'].sprites()[0].image,
                                                     (character_dict['character'].rect.x,
                                                      character_dict['character'].rect.y))
                            self.screen.blit(self.background, self.camera_position)
                    if self.launch_signaled:
                        # The COMMAND window behind, as it is: the chosen entry's arrow is still on (WndAPressed), as
                        # RemoveWindow puts back the window's tiles
                        self.draw_command_window()
                    if self.game.drawer.display_hovering_stats:
                        self.game.drawer.draw_hovering_stats_window(self.screen, self.player, self.color)
                    if not self.game.game_state.config['NO_BLIT']:
                        display.update(self.screen.blit(black_box, (tile_size * left, tile_size * top)))

    # Treasure chests

    @property
    def chest_history(self):
        return self.game.chest_history

    def open_chest(self) -> None:
        """NES GetTreasure: record the chest as taken, then play the chest sound and turn the chest into brick.
        With all 8 history slots in use the NES records nothing and leaves the chest where it is."""
        if self.chest_history.record(self.map_name, (self.player.row, self.player.column)):
            self.sound.play_sound(self.directories.open_treasure_sfx)
            self.set_tile_by_coordinates('BRICK', self.player.column, self.player.row, self.player)

    def found_item_text(self, item_name: str) -> str:
        return self._("Fortune smiles upon thee, {}.\nThou hast found the {}.").format(self.player.name,
                                                                                     self._(item_name))

    def take_empty_chest(self) -> None:
        # NES GetTreasureChest1: the chest is used up even though nothing is in it
        self.open_chest()
        self.show_text_in_dialog_box(self._("Unfortunately, it is empty."), skip_text=self.skip_text)

    def take_counted_item(self, item_name: str, maximum: int) -> None:
        """NES ChkTrsrKey/ChkTrsrHerb: Herbs and Magic Keys stop at 6. With 6 already, the chest is empty."""
        if self.player.inventory.count(item_name) >= maximum:
            self.take_empty_chest()
            return
        self.player.inventory.insert(0, item_name)
        self.open_chest()
        self.show_text_in_dialog_box(self.found_item_text(item_name), skip_text=self.skip_text)

    def inventory_is_full(self) -> bool:
        return len([item for item in self.player.inventory if item not in UNSLOTTED_ITEMS]) >= INVENTORY_SLOTS

    def take_item(self, item_name: str):
        """NES SetTrsrDescByte: tell the player what was found, then add it to the inventory."""
        self.open_chest()
        self.show_text_in_dialog_box(self.found_item_text(item_name), skip_text=self.skip_text)
        if item_name in UNSLOTTED_ITEMS or not self.inventory_is_full():
            self.player.inventory.insert(0, item_name)
        else:
            self.discard_for_item(item_name)

    def discard_for_item(self, item_name: str) -> None:
        """NES DiscardItem: with a full inventory, the player may drop something to make room.
        The chest has already been opened, so an item given up here is gone until the chest refills."""
        self.show_text_in_dialog_box(
            self._("If thou would take the {}, thou must now discard some other item.").format(self._(item_name)),
            skip_text=self.skip_text)
        if self.prompt_yes_no():
            while True:
                self.show_text_in_dialog_box(self._("What shall thou drop?"), skip_text=self.skip_text)
                item_to_drop = self.display_item_menu('discard')
                if item_to_drop is None:
                    break
                if item_to_drop in NON_DISCARDABLE_ITEMS:
                    self.show_text_in_dialog_box(self._("That is much too important to throw away."),
                                                 skip_text=self.skip_text)
                    continue
                if self.player.is_wearing_cursed_item(item_to_drop):
                    # NES LE0B9: a worn Cursed Belt or Death Necklace can't be dropped
                    self.show_text_in_dialog_box(self._("A curse is upon thy body."), skip_text=self.skip_text)
                    continue
                self.player.inventory.remove(item_to_drop)
                self.player.inventory.insert(0, item_name)
                self.show_text_in_dialog_box((self._("Thou hast dropped thy {}.").format(self._(item_to_drop)),
                                              self._("And obtained the {}.").format(self._(item_name))),
                                             skip_text=self.skip_text)
                return
        self.show_text_in_dialog_box(self._("Thou hast given up thy {}.").format(self._(item_name)),
                                     skip_text=self.skip_text)

    def prompt_yes_no(self) -> bool:
        """A YES/NO window. Returns True for YES; NO or backing out returns False."""
        yes_selected = True
        cursor = BlinkingCursor()  # WndInitSelect
        while True:
            self.draw_yes_no_window(yes_selected, cursor.visible())
            for current_event in event.get():
                quit_if_requested(current_event)
                if handle_speed_key(current_event):  # keys 1 to 4: the game speed, nothing else
                    continue
                if current_event.type != KEYDOWN:
                    continue
                if current_event.key in accept_keys or current_event.key in reject_keys:
                    # WndAPressed/WndBPressed: the arrow is drawn once more and stays on
                    self.draw_yes_no_window(yes_selected, True)
                    self.remove_window(YES_NO_WINDOW)  # then NES WindowSequence: RemoveWindow
                    return yes_selected and current_event.key in accept_keys
                if current_event.key in (K_UP, K_w, K_DOWN, K_s):
                    if yes_selected != (current_event.key in (K_UP, K_w)):
                        yes_selected = not yes_selected
                        cursor.restart()  # WndUpdateCrsrPos

    def draw_yes_no_window(self, yes_selected: bool, cursor_visible: bool) -> None:
        """The YES/NO window (YesNo1Dat, generated by src/window_renderer.py): YES and NO at tile column 2 of rows 2
        and 4, and the NES cursor (src/cursor.py) in the tile before the selected one (cursor home X = 1, Y = 2)."""
        window_rect = draw_window(self.screen, YES_NO_LAYOUT, self.color, self.game.game_state.config,
                                  cursor_index=0 if yes_selected else 1, cursor_visible=cursor_visible)
        if not self.game.game_state.config['NO_BLIT']:
            display.update(window_rect)

    def take_erdricks_sword(self) -> None:
        """NES ChkTrsrErdSword: the sword is equipped at once. If it already is, the chest is empty."""
        if self.player.weapon == "Erdrick's Sword":
            self.take_empty_chest()
            return
        self.player.weapon = "Erdrick's Sword"
        self.player.update_attack_power()
        self.open_chest()
        self.show_text_in_dialog_box(self.found_item_text("Erdrick's Sword"), skip_text=self.skip_text)

    def take_unique_item(self, item_name: str, blocking_items: Tuple[str, ...]) -> None:
        """NES ChkTrsrHarp/ChkTrsrStones: the chest is empty while the player has the item, or what it becomes."""
        if any(item in self.player.inventory for item in blocking_items):
            self.take_empty_chest()
        else:
            self.take_item(item_name)

    def take_death_necklace(self) -> None:
        """NES ChkTrsrNecklace: the first time, there is a 1 in 32 chance of the Death Necklace (the low 5 bits of a
        random byte all zero). Otherwise, and always once it has been found, the chest holds 100-131 gold."""
        if not self.game.story_flags.death_necklace_found and random.randint(0, 255) & 0x1F == 0:
            self.game.story_flags.death_necklace_found = True
            self.take_item('Death Necklace')
        else:
            self.take_gold({'item': GOLD, 'gold': DEATH_NECKLACE_GOLD})

    def tablet(self, found_item_text):
        self.show_text_in_dialog_box((
            found_item_text,
            self._("The tablet reads as follows:"),
            self._("I am Erdrick and thou art my descendant."),
            self._("Three items were needed to reach the Isle of Dragons, which is south of Brecconary."),
            self._("I gathered these items, reached the island, and there defeated a creature of great evil."),
            self._("Now I have entrusted the three items to three worthy keepers."),
            self._("Their descendants will protect the items until thy quest leads thee to seek them out."),
            self._("When a new evil arises, find the three items, then fight!")), drop_down=False)

    def take_tablet(self) -> None:
        # NES ChkTrsrErdTablet: the tablet is read, not kept
        self.open_chest()
        self.tablet(self.found_item_text('Tablet'))

    def take_gold(self, treasure_info: dict):
        """NES GetTrsrGold: the amount is rolled when the chest is opened, and gold stops at 65535."""
        gold_amount = roll_treasure_gold(treasure_info['gold'])
        self.open_chest()
        self.player.gold = min(self.player.gold + gold_amount, MAX_GOLD)
        # NES GainGoldDialog: the message, then Dowindow WND_POPUP with the new gold, then ResumeGamePlay closes the
        # dialog window
        self.show_text_in_dialog_box(self._("Of GOLD thou hast gained {}").format(gold_amount),
                                     skip_text=self.skip_text, drop_up=False)
        self.show_popup_window()
        self.window_drop_up_effect(*DIALOG_WINDOW)

    def set_tile_by_coordinates(self, new_tile_identifier, column, row, player):
        old_tile_identifier = get_tile_id_by_coordinates(column, row, self.current_map)
        if column == player.column and row == player.row:
            self.current_tile = new_tile_identifier
            player.current_tile = new_tile_identifier
        self.current_map.layout[row][column] = \
            self.game.layouts.map_layout_lookup[self.current_map.__class__.__name__][row][column] = \
            self.current_map.floor_tile_key[new_tile_identifier]['val']
        center_pt = get_center_point(column, row, tile_size=self.game.game_state.config['TILE_SIZE'])
        self.current_map.floor_tile_key[old_tile_identifier]['group'] = Group()
        self.current_map.add_tile(self.current_map.floor_tile_key[new_tile_identifier], center_pt)
        for row in range(len(self.current_map.layout)):
            for column in range(len(self.current_map.layout[row])):
                self.current_map.center_pt = get_center_point(column, row,
                                                              tile_size=self.game.game_state.config['TILE_SIZE'])
                if self.current_map.layout[row][column] <= max(
                        self.current_map.floor_tile_key[old_tile_identifier]['val'],
                        self.current_map.floor_tile_key[new_tile_identifier]['val']):
                    self.current_map.map_floor_tiles(column, row)

    def get_dialog_box_underlying_tiles(self, current_map, current_box_height):
        # TODO(ELF): Can be improved further by narrowing the columns to just where the box is, not only the rows.
        box_start_row = 2
        box_end_row = current_box_height + box_start_row
        row_tile_sets = [set(row) for row in
                         current_map.layout[self.player.row + box_start_row:self.player.row + box_end_row]]
        return set([item for sublist in row_tile_sets for item in sublist])

    # Items

    def item_message(self, text: str):
        """Show an item's text as a battle line during a fight, or in the dialog box in the field."""
        if self.current_battle is not None:
            self.show_battle_line(text)
        else:
            self.show_text_in_dialog_box(text, skip_text=self.skip_text)

    def use_item_in_battle(self, item_name: str):
        """NES PlyrItem: only these items work in battle; the enemy then takes its turn. Anything else is refused
        (InvalidCombatSpell) and the player acts again."""
        battle_items = {
            "Herb": self.herb,
            "Fairy Flute": self.fairy_flute,
            "Silver Harp": self.silver_harp_in_battle,
            "Dragon's Scale": self.dragon_scale,
            "Fighter's Ring": self.fighters_ring,
            "Cursed Belt": self.cursed_belt,
            "Death Necklace": self.death_necklace,
        }
        item_function = battle_items.get(item_name)
        if item_function is None:
            self.show_battle_line(self._("That cannot be used in battle."))
            self.current_battle.no_op = True
            return
        item_function()

    def herb(self):
        self.item_message(self._("{} used the Herb.").format(self.player.name))
        # NES HerbHeal: 23 to 30 HP, and the herb is used up
        self.player.inventory.remove("Herb")
        self.recover_health(23, 30)

    def wings(self):
        # NES: same destination as RETURN, and the same places it can't be used
        if not self.can_return():
            self.show_text_in_dialog_box(self._("The Wings of the Wyvern cannot be used here."),
                                         skip_text=self.skip_text)
            return
        self.player.inventory.remove("Wings")
        self.show_text_in_dialog_box(
            self._("{} threw The Wings of the Wyvern up into the sky.").format(self.player.name))
        self.warp(*RETURN_DESTINATION)

    def torch(self):
        if not self.current_map.is_dark:
            self.show_text_in_dialog_box(self._("A torch can be used only in dark places."), skip_text=self.skip_text)
        else:
            self.player.inventory.remove("Torch")
            # NES UseTorch: SFX_RADIANT plays when the light is redrawn (Drawer.handle_darkness)
            self.game.game_state.use_torch()

    def dragon_scale(self):
        if self.player.wearing_dragon_scale:
            self.item_message(self._("Thou art already wearing the scale of the dragon."))
            return
        self.player.wearing_dragon_scale = True
        self.player.update_defense_power()
        self.item_message(self._("{} donned the scale of the dragon.").format(self.player.name))

    def fairy_water(self):
        self.show_text_in_dialog_box(
            self._("{} sprinkled the Fairy Water over his body.").format(self.player.name), skip_text=self.skip_text)
        self.player.inventory.remove("Fairy Water")
        self.game.repel_timer = FAIRY_WATER_TIMER

    def resume_music(self):
        """After a music clip: in a fight, the fight's music again (the end boss music against the Dragonlord's final
        form, ChkUseFlute and ChkUseHarp); on the map, the map's music (ResumeMusicTbl). Both start from the
        beginning."""
        if self.current_battle is not None:
            self.current_battle.play_battle_music()
        else:
            self.game.music_player.load_and_play_music(self.current_map.music_file_path)

    def silver_harp(self):
        # NES ChkHarp: the harp tune plays to the end, then on the overworld a fight starts (InitFight, so REPEL and
        # Fairy Water don't stop it, and it still works after the Dragonlord is dead). Anywhere else the map music
        # resumes and nothing happens. The harp is never used up.
        self.show_text_in_dialog_box(self._("{} played a sweet melody on the harp.").format(self.player.name),
                                     skip_text=self.skip_text)
        self.game.game_state.pause_all_movement()
        self.game.music_player.play_until_end(self.directories.harp_music, self.game.game_state.config)
        self.game.game_state.unpause_all_movement()
        if self.current_map.identifier == 'Alefgard':
            self.game.battle_ctrl.queue_scripted_battle(random.choice(SILVER_HARP_ENEMIES))
            return
        self.resume_music()  # HarpFail: ResumeMusicTbl
        self.show_text_in_dialog_box(self._("But nothing happened."), skip_text=self.skip_text)

    def silver_harp_in_battle(self):
        # NES ChkUseHarp: the harp tune plays to the end (WaitForMusicEnd), the fight music comes back, and the enemy
        # only looks happy
        self.show_battle_line(self._("{} played a sweet melody on the harp.").format(self.player.name))
        self.game.music_player.play_until_end(self.directories.harp_music, self.game.game_state.config)
        self.resume_music()
        self.show_battle_line(self._("The {} looks happy.").format(self._(self.current_battle.enemy.name)))

    def fairy_flute(self):
        # NES ChkFryFlt (field) / ChkUseFlute (battle): play the flute tune to the end (WaitForMusicEnd), then resume
        # the map or battle music
        in_battle = self.current_battle is not None
        say = self.show_battle_line if in_battle else functools.partial(self.show_text_in_dialog_box,
                                                                        skip_text=self.skip_text)
        say(self._("{} blew the Fairies' Flute.").format(self.player.name))
        self.game.game_state.pause_all_movement()
        self.game.music_player.play_until_end(self.directories.flute_music, self.game.game_state.config)
        self.game.game_state.unpause_all_movement()
        self.resume_music()
        if in_battle and self.current_battle.enemy.name == 'Golem':
            # NES ChkUseFlute: the Golem always falls asleep and loses its turn (jumps to EnStillAsleep)
            enemy = self.current_battle.enemy
            enemy.is_asleep = True
            say(self._("Quietly Golem closes his eyes and settles into sleep."))
            say(self._("The {} is asleep.").format(self._(enemy.name)))
            self.current_battle.no_op = True
            return
        say(self._("But nothing happened."))

    def erdricks_token(self):
        self.show_text_in_dialog_box(f"{self.player.name} held the Erdrick's Token tightly.\nBut nothing happened.")

    def rainbow_drop(self):
        # NES ChkDrop: the bridge appears only on the overworld, with the hero on the one tile east of it, and only
        # once (F_RNBW_BRDG). The hero's facing doesn't matter, and the Rainbow Drop is kept either way.
        self.show_text_in_dialog_box(self._("{} held the Rainbow Drop toward the sky.").format(self.player.name),
                                     skip_text=self.skip_text)
        if self.current_map.identifier != 'Alefgard' or self.game.story_flags.rainbow_bridge_built or \
                (self.player.row, self.player.column) != RAINBOW_DROP_COORDINATES:
            # NES RainbowFail
            self.show_text_in_dialog_box(self._("But no rainbow appeared here."), skip_text=self.skip_text)
            return
        self.game.story_flags.rainbow_bridge_built = True
        bridge_row, bridge_column = RAINBOW_BRIDGE_COORDINATES
        self.set_tile_by_coordinates('BRIDGE', bridge_column, bridge_row, self.player)

    def hold_item_tightly(self, item_name: str):
        # NES DoItemDescription: TextBlock5 entry 0 ("<name> held the <item> tightly.") then "But nothing happened."
        self.show_text_in_dialog_box(self._("{} held the {} tightly.\nBut nothing happened.").format(
            self.player.name, self._(item_name)), skip_text=self.skip_text)

    def staff_of_rain(self):
        # NES ChkStaff: the Staff of Rain has no effect when used; it only matters at the Rainbow Drop shrine
        self.hold_item_tightly("Staff of Rain")

    def stones_of_sunlight(self):
        # NES ChkStones: the Stones of Sunlight have no effect when used; they only matter at the Rainbow Drop shrine
        self.hold_item_tightly("Stones of Sunlight")

    def fighters_ring(self):
        if self.player.wearing_fighters_ring:
            self.item_message(self._("{} adjusted the position of the Fighter's Ring.").format(self.player.name))
            return
        self.player.wearing_fighters_ring = True
        self.player.update_attack_power()
        self.item_message(self._("{} put on the Fighter's Ring.").format(self.player.name))

    def cursed_belt(self):
        # NES WearCursedItem: using the belt puts it on (it stays in the inventory) and sets F_CRSD_BELT
        already_worn = self.player.wearing_cursed_belt
        self.player.wearing_cursed_belt = True
        self.put_on_cursed_item("Cursed Belt", already_worn)

    def death_necklace(self):
        # NES ChkDeathNecklace: same as the belt, but sets F_DTH_NECKLACE. No stat or HP change on the NES.
        already_worn = self.player.wearing_death_necklace
        self.player.wearing_death_necklace = True
        self.put_on_cursed_item("Death Necklace", already_worn)

    def put_on_cursed_item(self, item_name: str, already_worn: bool):
        if already_worn:
            # NES DoCursedDialog
            text = self._("The {} is squeezing thy body.").format(self._(item_name))
        else:
            # NES PlayerCursed
            text = self._("{} put on the {} and was cursed!\nThy body is being squeezed.").format(
                self.player.name, self._(item_name))
        self.item_message(text)
        # NES PlayCursedMusic: MSC_CURSED plays to the end either way (WaitForMusicEnd). Then ChkBelt and ChkNecklace
        # resume the map's music (ResumeMusicTbl), and in a fight ChkUseBelt and ChkUseNecklace start MSC_REG_FGHT,
        # the regular fight music even against the Dragonlord's final form.
        self.game.music_player.play_until_end(self.directories.cursed_music, self.game.game_state.config)
        if self.current_battle is not None:
            self.game.music_player.load_and_play_music(self.directories.battle_music)
        else:
            self.resume_music()

    def gwaelins_love(self):
        self.show_text_in_dialog_box(f"Heed my voice, '{self.player.name}, for this is Gwaelin. "
                                     "To reach the next level thou must raise thy Experience Points by "
                                     f"{self.player.points_to_next_level}. "
                                     f"My hope is with thee.'")
        if self.current_map.identifier == 'Alefgard':
            distance_string = "From where thou art now, my castle lies..\n"
            east_west_distance, north_south_distance = self.calculation.get_distance_from_tantegel(self.player.column,
                                                                                                   self.player.row)
            if north_south_distance < 0:
                distance_string += f"{abs(north_south_distance)} to the south and.."
            elif north_south_distance > 0:
                distance_string += f"{abs(north_south_distance)} to the north and.."
            if east_west_distance < 0:
                distance_string += f"{abs(east_west_distance)} to the west."
            elif east_west_distance > 0:
                distance_string += f"{abs(east_west_distance)} to the east."
            self.show_text_in_dialog_box(distance_string)
        self.show_text_in_dialog_box(f"I love thee, {self.player.name}.")

    # spells

    def heal(self):
        # NES DoHeal: 10 to 17 HP
        self.recover_health(10, 17)

    def recover_health(self, lowest: int, highest: int):
        health_addition = random.randint(lowest, highest)
        if self.player.current_hp + health_addition > self.player.max_hp:
            health_addition = self.player.max_hp - self.player.current_hp
        self.player.current_hp += health_addition
        # NES PlyrAddHP (HEAL, HEALMORE) and HerbHeal: LoadRegBGPal right after the new HP is stored, so the windows
        # turn white at once if HP is no longer low. Then they show the new HP: Dowindow WND_POPUP.
        self.game.load_window_palette()
        self.show_popup_window()

    def show_battle_line(self, text: str):
        self.show_line_in_dialog_box(text, add_quotes=False, disable_sound=True, hide_arrow=True)

    def battle_spell_resisted(self, resistance: float) -> bool:
        """NES ChkSpellFail: the spell fails if a 0-15 roll is below the enemy's resistance (n/16)."""
        if random.randint(0, 15) < round(resistance * 16):
            self.show_battle_line(self._("The spell will not work."))
            return True
        return False

    def cast_damage_spell(self, lowest: int, highest: int):
        if self.current_battle is None:
            self.show_text_in_dialog_box(self._("But nothing happened."), skip_text=self.skip_text)
            return
        enemy = self.current_battle.enemy
        if self.battle_spell_resisted(enemy.hurt_resist):
            return
        # Spell damage can't be dodged
        damage = random.randint(lowest, highest)
        self.sound.play_sound(self.directories.hit_sfx)
        # NES SetSpellDmg falls through to PlyrHitEn, so a damage spell flashes the enemy red too
        self.game.drawer.flash_enemy(self.screen, enemy.name)
        self.show_battle_line(self._("The {}'s Hit Points have been reduced by {}.\n").format(self._(enemy.name), damage))
        enemy.hp -= damage

    def hurt(self):
        # NES: 5 to 12 damage
        self.cast_damage_spell(5, 12)

    def sleep(self):
        if self.current_battle is None:
            self.show_text_in_dialog_box(self._("But nothing happened."), skip_text=self.skip_text)
            return
        enemy = self.current_battle.enemy
        enemy_name = self._(enemy.name)
        # NES (ChkSpellFail): the spell fails if a 0-15 roll is below the enemy's sleep resistance (n/16).
        if random.randint(0, 15) < round(enemy.sleep_resist * 16):
            self.show_line_in_dialog_box(self._("The spell will not work."), add_quotes=False,
                                         disable_sound=True, hide_arrow=True)
            return
        enemy.is_asleep = True
        self.show_line_in_dialog_box(self._("Thou hast put the {} to sleep.").format(enemy_name), add_quotes=False,
                                     disable_sound=True, hide_arrow=True)
        # The enemy loses the turn it was put to sleep (NES jumps straight to EnStillAsleep).
        self.show_line_in_dialog_box(self._("The {} is asleep.").format(enemy_name), add_quotes=False,
                                     disable_sound=True, hide_arrow=True)
        self.current_battle.no_op = True

    def radiant(self):
        if self.current_map.is_dark:
            # NES DoSpell: SFX_RADIANT plays for each 2 blocks the light grows (Drawer.handle_darkness)
            self.game.game_state.cast_radiant()
        else:
            self.show_text_in_dialog_box(self._("But nothing happened."), skip_text=self.skip_text)

    def stopspell(self):
        if self.current_battle is None:
            self.show_text_in_dialog_box(self._("But nothing happened."), skip_text=self.skip_text)
            return
        enemy = self.current_battle.enemy
        if self.battle_spell_resisted(enemy.stopspell_resist):
            return
        enemy.is_stopspelled = True
        self.show_battle_line(self._("The {}'s spell hath been blocked.").format(self._(enemy.name)))

    def warp(self, map_name: str, coordinates: tuple):
        """Move the player to another map without using stairs (OUTSIDE, RETURN, Wings of the Wyvern)."""
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates,
                             direction=Direction.DOWN.value)

    def can_return(self) -> bool:
        return self.current_map.identifier not in DUNGEON_MAPS and self.current_map.identifier != 'CharlockB8'

    def outside(self):
        # NES: only works in the caves and below the Dragonlord's castle's ground floor
        destination = OUTSIDE_DESTINATIONS.get(self.current_map.identifier)
        if destination is None:
            self.show_text_in_dialog_box(self._("But nothing happened."), skip_text=self.skip_text)
            return
        self.warp(*destination)

    def return_(self):
        if not self.can_return():
            self.show_text_in_dialog_box(self._("But nothing happened."), skip_text=self.skip_text)
            return
        self.warp(*RETURN_DESTINATION)

    def repel(self):
        self.game.repel_timer = REPEL_SPELL_TIMER

    def healmore(self):
        # NES DoHealmore: 85 to 100 HP
        self.recover_health(85, 100)

    def hurtmore(self):
        # NES: 58 to 65 damage
        self.cast_damage_spell(58, 65)

    # Menu functions

    def talk(self):
        """
        Talk to an NPC.
        :return: None
        """
        self.sound.play_sound(self.directories.menu_button_sfx)
        # dialog = Dialog(player=self.player)

        # for now, implementing using print statements. will be useful for debugging as well.
        across_from_npc = self.check_across_from_npc()
        if across_from_npc:
            for character_identifier, character_dict in self.characters.items():
                if (character_dict['character'].row,
                    character_dict['character'].column) == self.player.next_coordinates or self.npc_is_across_counter(
                    character_dict):
                    if character_dict['character'].direction_value != get_opposite_direction(
                            self.player.direction_value):
                        character_dict['character'].direction_value = get_opposite_direction(
                            self.player.direction_value)
                        character_dict['character'].animate()
                        character_dict['character'].pause()
                    self.launch_dialog(character_identifier, self.current_map)
                    break
        else:

            self.show_text_in_dialog_box(self._("There is no one there."), add_quotes=True, skip_text=self.skip_text)

        self.game.unlaunch_menu(self)
        self.game.game_state.unpause_all_movement()

    def check_across_from_npc(self):
        character_coordinates = [(character_dict['character'].row, character_dict['character'].column) for
                                 character_dict in self.characters.values()]
        across_from_npc = any(c in character_coordinates for c in [self.player.next_coordinates]) or any(
            c in character_coordinates for c in
            [self.player.next_next_coordinates]) and self.player.next_tile_id == 'WOOD'
        return across_from_npc

    def status(self) -> None:
        """
        Display the current player's status.
        :return: None
        """
        self.sound.play_sound(self.directories.menu_button_sfx)
        show_status = True
        x, y, width, height = STATUS_WINDOW
        self.window_drop_down_effect(x, y, width, height)
        window_rect = self.draw_status_window()
        display.update(window_rect)
        while show_status:
            for current_event in event.get():
                quit_if_requested(current_event)
                if handle_speed_key(current_event):  # keys 1 to 4: the game speed, nothing else
                    continue
                # NES LCFA4: the status window waits in WaitForBtnRelease, so any button closes it
                if current_event.type == KEYDOWN and current_event.key in ANY_BUTTON_KEYS:
                    show_status = False
        self.window_drop_up_effect(x, y, width, height)
        # print(f"""
        # NAME: {self.player.name}
        # STRENGTH: {self.player.strength}
        # AGILITY: {self.player.agility}
        # MAXIMUM HP: {self.player.max_hp}
        # MAXIMUM MP: {self.player.max_mp}
        # ATTACK POWER: {self.player.attack_power}
        # DEFENSE POWER: {self.player.defense_power}
        # WEAPON: {self.player.weapon}
        # ARMOR: {self.player.armor}
        # SHIELD: {self.player.shield}
        # """)
        self.game.unlaunch_menu(self)
        self.game.game_state.unpause_all_movement()

    def draw_status_window(self) -> Rect:
        """
        Draw the status window (NES StatusDat). The window and its labels are generated (STATUS_LAYOUT,
        src/window_renderer.py); the values go where StatusDat puts them: the name after "NAME:" at tile column 11 of
        tile row 1, the numbers right-aligned to tile column 18 on every other row from row 3, and the weapon, armor
        and shield in two halves (first half at column 10, second half at column 11 on the next row) from row 15.
        :return: The window's rect on the screen.
        """
        config = self.game.game_state.config
        tile_size = config['TILE_SIZE']
        x, y, width, height = STATUS_WINDOW
        draw_window(self.screen, STATUS_LAYOUT, self.color, config)

        def draw_in_window(text: str, column: int, row: int, alignment: str = 'left') -> None:
            draw_text(text, *self.window_text_position(x, y, column, row), self.screen, config, color=self.color,
                      alignment=alignment, letter_by_letter=False)

        draw_in_window(self.player.name, STATUS_NAME_TILE_COLUMN, STATUS_NAME_TILE_ROW)
        values = (self.player.strength, self.player.agility, self.player.max_hp, self.player.max_mp,
                  self.player.attack_power, self.player.defense_power)
        for row, value in zip(STATUS_VALUE_TILE_ROWS, values):
            draw_in_window(str(value), STATUS_VALUE_RIGHT_TILE_COLUMN, row, alignment='right')
        for row, equipment in zip(STATUS_EQUIPMENT_TILE_ROWS, (self.player.weapon, self.player.armor,
                                                               self.player.shield)):
            if not equipment:
                continue
            first_half, second_half = name_halves(equipment)
            draw_in_window(first_half, STATUS_EQUIPMENT_TILE_COLUMN, row)
            if second_half:
                draw_in_window(second_half, STATUS_EQUIPMENT_TILE_COLUMN + 1, row + 1)
        return Rect(x * tile_size, y * tile_size, width * tile_size, height * tile_size)

    def stairs(self) -> None:
        """
        Go up or down a staircase.
        :return: None
        """
        self.sound.play_sound(self.directories.menu_button_sfx)
        # this might be something we could turn off as one of the "modernization" updates
        if self.player.current_tile in ('BRICK_STAIR_DOWN', 'BRICK_STAIR_UP', 'GRASS_STAIR_DOWN'):
            self.game.process_staircase_warps(staircase_location=(self.game.player.row, self.game.player.column),
                                              staircase_dict=self.game.current_map.staircases[
                                                  (self.game.player.row, self.game.player.column)])
        else:
            # the original game has quotes in this dialog box
            self.show_text_in_dialog_box(self._("There are no stairs here."), add_quotes=True, skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.game_state.unpause_all_movement()

    def search(self) -> None:
        """
        Search the ground for items.
        :return: None
        """
        self.sound.play_sound(self.directories.menu_button_sfx)
        # open a window
        text_to_print = [self._(f"{self.player.name} searched the ground all about."), ]
        # wait for input...
        if self.player.current_tile == 'TREASURE_BOX':
            text_to_print.append(self._(f"There is a {self.player.current_tile.lower().replace('_', ' ')}."))
        elif hidden_item := hidden_items.get(self.current_map.identifier, {}).get((self.player.row, self.player.column)):
            text_to_print.append(self.find_hidden_item(hidden_item))
        elif not (self.current_map.identifier == 'CharlockB1' and self.search_for_secret_passage(text_to_print)):
            text_to_print.append(self._("But there found nothing."))

        self.show_text_in_dialog_box(text_to_print, skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.game_state.unpause_all_movement()

    def search_for_secret_passage(self, text_to_print: list) -> bool:
        """
        NES DoSearch (SrchPassage): on Charlock's ground floor, searching on the throne hints at the passage, and
        searching on the force field behind it (once) turns that block into stairs down.
        :param text_to_print: The search dialog so far, appended to if something is found.
        :return: True if the search found something here, False to fall through to "But there found nothing."
        """
        charlock_ground_floor = self.current_map
        if not isinstance(charlock_ground_floor, CharlockB1):
            return False
        player_coordinates = (self.player.row, self.player.column)
        if player_coordinates == charlock_ground_floor.THRONE_COORDINATES:
            text_to_print.append(self._("Feel the wind blowing from behind the throne."))
            return True
        if player_coordinates != charlock_ground_floor.HIDDEN_STAIRCASE_COORDINATES or \
                self.game.story_flags.charlock_stairs_revealed:
            return False
        self.game.story_flags.charlock_stairs_revealed = True
        text_to_print.append(self._("{} discovers the Secret Passage.").format(self.player.name))
        self.set_tile_by_coordinates('BRICK_STAIR_DOWN', self.player.column, self.player.row, self.player)
        charlock_ground_floor.reveal_hidden_staircase()
        # Like arriving on a map: don't auto-take the new stairs until the player steps off and back on (or uses STAIRS)
        self.game.tiles_moved_since_spawn = 0
        return True

    def find_hidden_item(self, item_name: str) -> str:
        """
        NES DoSearch: pick up (or, for Erdrick's Armor, put on) a hidden item, unless the player already has it.
        :param item_name: The item hidden on the player's tile.
        :return: The line to show after "searched the ground all about."
        """
        if item_name in armor:
            # NES SrchEdrckArmor: found only if not already worn; it's equipped directly (replacing the old armor,
            # which is not kept) instead of going into the inventory
            if self.player.armor == item_name:
                return self._("But there found nothing.")
            self.player.armor = item_name
            self.player.update_defense_power()
        else:
            # NES FoundItem/ItemAlreadyFound: found only if it isn't already in the inventory
            if item_name in self.player.inventory:
                return self._("But there found nothing.")
            self.player.inventory.append(item_name)
        return self._("{} discovers the {}.").format(self.player.name, self._(item_name))

    def spell(self):
        """
        Cast a magic spell.
        """
        self.sound.play_sound(self.directories.menu_button_sfx)
        # the implementation of this will vary upon which spell is being cast.
        if not self.player.spells:
            self.show_text_in_dialog_box(self._("{} cannot yet use the spell.").format(self.player.name),
                                         skip_text=self.skip_text)
        else:
            self.display_item_menu('spells')
        self.game.unlaunch_menu(self)
        self.game.game_state.unpause_all_movement()

    def item(self):
        """
        View/use items. (Not yet implemented)
        :return: To be determined upon implementation
        """
        self.sound.play_sound(self.directories.menu_button_sfx)
        # the implementation of this will vary upon which item is being used.
        if not self.player.inventory:
            self.show_text_in_dialog_box(self._("Nothing of use has yet been given to thee."), skip_text=self.skip_text)
        else:
            self.display_item_menu('inventory')

            # self.show_text_in_dialog_box(inventory_string, skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.game_state.unpause_all_movement()

    def display_item_menu(self, menu_name: str):
        """Display a menu of selectable items.
        :param menu_name: The name of the menu to display: 'inventory', 'spells', or 'discard' (pick an inventory
        item without using it).
        :return: The item chosen, or None if the menu was closed without choosing.
        """
        function_dict: dict[Any, Any] = {}
        chosen_item = None
        if menu_name in ('inventory', 'discard'):
            # NES CreateInvList: Herbs, then Magic Keys, then each inventory slot in order
            entries = inventory_list(self.player.inventory)
            function_dict = {
                # item function map
                "Herb": self.herb,
                "Wings": self.wings,
                "Torch": self.torch,
                "Dragon's Scale": self.dragon_scale,
                "Fairy Water": self.fairy_water,
                "Silver Harp": self.silver_harp,
                "Gwaelin's Love": self.gwaelins_love,
                "Erdrick's Token": self.erdricks_token,
                "Magic Key": self.door,
                "Rainbow Drop": self.rainbow_drop,
                "Staff of Rain": self.staff_of_rain,
                "Stones of Sunlight": self.stones_of_sunlight,
                "Fighter's Ring": self.fighters_ring,
                "Fairy Flute": self.fairy_flute,
                "Cursed Belt": self.cursed_belt,
                "Death Necklace": self.death_necklace,
            }
        elif menu_name == 'spells':
            entries = list(self.player.spells)
            function_dict = {
                # name, function, MP cost
                Spell.HEAL: (self.heal, 4),
                Spell.HURT: (self.hurt, 2),
                Spell.SLEEP: (self.sleep, 2),
                Spell.RADIANT: (self.radiant, 3),
                Spell.STOPSPELL: (self.stopspell, 2),
                Spell.OUTSIDE: (self.outside, 6),
                Spell.RETURN: (self.return_, 8),
                Spell.REPEL: (self.repel, 2),
                Spell.HEALMORE: (self.healmore, 10),
                Spell.HURTMORE: (self.hurtmore, 5)
            }
        else:
            raise ValueError(f"Invalid menu name: {menu_name}")
        item_menu_displayed = True
        current_arrow_position = 0
        drawn_arrow_position = None
        window_rect = Rect(0, 0, 0, 0)
        currently_selected_item = entries[0]
        # The NES cursor (src/cursor.py): visible when the window opens (WndInitSelect)
        cursor = BlinkingCursor()

        def draw_cursor() -> None:
            self.draw_window_cursor(ITEM_MENU_X, ITEM_MENU_Y[menu_name], ITEM_MENU_CURSOR_TILE_COLUMN,
                                    item_menu_entry_tile_row(menu_name, current_arrow_position), cursor.visible())

        while item_menu_displayed:
            if current_arrow_position != drawn_arrow_position:
                # Redraw the window to erase the cursor from the entry it left
                window_rect = self.draw_item_menu(menu_name, entries)
                drawn_arrow_position = current_arrow_position
            draw_cursor()
            display.update(window_rect)
            for current_event in event.get():
                quit_if_requested(current_event)
                if handle_speed_key(current_event):  # keys 1 to 4: the game speed, nothing else
                    continue
                if any([current_event.type == KEYDOWN]):
                    if current_event.key in accept_keys or current_event.key in reject_keys:
                        # WndAPressed/WndBPressed: the arrow is drawn once more and stays on
                        cursor.hold()
                        draw_cursor()
                        display.update(window_rect)
                    if current_event.key in reject_keys:
                        item_menu_displayed = False
                        if self.current_battle is not None:
                            # NES: closing the spell or item window in battle returns to the command window
                            self.current_battle.no_op = True
                    elif current_event.key in accept_keys:
                        if menu_name == 'spells':
                            spell_function, spell_mp_cost = function_dict[currently_selected_item]
                            if self.current_battle is not None and currently_selected_item in (
                                    Spell.RADIANT, Spell.REPEL, Spell.OUTSIDE, Spell.RETURN):
                                # NES: rejected before any MP is spent, and the player acts again
                                self.show_battle_line(self._("That cannot be used in battle."))
                                self.current_battle.no_op = True
                            elif self.player.current_mp < spell_mp_cost:
                                self.show_line_in_dialog_box(self._("Thy MP is too low."),
                                                             skip_text=self.skip_text,
                                                             disable_sound=True,
                                                             hide_arrow=True,
                                                             add_quotes=False)
                                if self.current_battle is not None:
                                    self.current_battle.no_op = True
                            else:
                                self.show_line_in_dialog_box(
                                    (self._("{} chanted the spell of {}.").format(self.player.name,
                                                                                  currently_selected_item)),
                                    add_quotes=False,
                                    disable_sound=True,
                                    hide_arrow=True,
                                    skip_text=self.skip_text)
                                self.sound.play_sound(self.directories.spell_sfx)
                                self.player.current_mp -= spell_mp_cost
                                # NES PlyrCastSpell (LDBB2): the pop-up is redrawn with the MP that is left
                                self.show_popup_window()
                                if self.current_battle is not None and self.player.is_stopspelled:
                                    # NES: the MP is spent, but a stopspelled player's spell is blocked
                                    self.show_battle_line(self._("But that spell hath been blocked."))
                                else:
                                    spell_function()
                        elif menu_name == 'inventory':
                            if self.current_battle is not None:
                                self.use_item_in_battle(currently_selected_item)
                            else:
                                function_dict[currently_selected_item]()
                        chosen_item = currently_selected_item
                        item_menu_displayed = False
                    elif len(menu_name) > 1:
                        if current_event.key in (K_UP, K_w) and current_arrow_position > 0:
                            current_arrow_position -= 1
                            cursor.restart()  # WndUpdateCrsrPos
                        elif current_event.key in (K_DOWN, K_s) and current_arrow_position < len(entries) - 1:
                            current_arrow_position += 1
                            cursor.restart()
                        currently_selected_item = entries[current_arrow_position]
        return chosen_item

    def command_window_in_nes_font(self) -> bool:
        """Whether the COMMAND window's title and entries are shown untranslated, in the NES font, so the whole window is
        generated tile by tile (COMMAND_LAYOUT). A translation (Korean) has no NES tiles; it is drawn as text."""
        return all(self._(text) == text for text in (COMMAND_TITLE.text,) + COMMAND_ENTRIES)

    def draw_command_window(self) -> Rect:
        """
        Draw the COMMAND window (CmdNonCmbtDat) in its place, as the NES builds it (src/window_renderer.py): its border,
        "COMMAND" in the top border and the 8 entries, with the NES cursor (src/cursor.py) in the tile before the
        selected one, blinking, or held on once it has been chosen. All of it is in the window color, red at low HP
        (AddPalByte). Translated, the border is generated and the title and entries are drawn as text where the NES
        puts them.
        :return: The window's rect on the screen, for display.update.
        """
        config = self.game.game_state.config
        cursor = {'cursor_index': self.menu.selected, 'cursor_visible': self.cursor.visible()}
        if self.command_window_in_nes_font():
            return draw_window(self.screen, COMMAND_LAYOUT, self.color, config, **cursor)
        rect = draw_window(self.screen, COMMAND_BORDER_LAYOUT, self.color, config, **cursor)
        x, y = COMMAND_WINDOW.x, COMMAND_WINDOW.y
        self.draw_window_title(self._(COMMAND_TITLE.text), x, y, COMMAND_TITLE.column)
        for entry, (column, row) in zip(COMMAND_ENTRIES, COMMAND_CURSOR_TILES):
            draw_text(self._(entry), *self.window_text_position(x, y, column + 1, row), self.screen, config,
                      color=self.color, letter_by_letter=False)
        return rect

    def select_command(self, events: list) -> None:
        """
        One frame of the COMMAND window's selection (WndDoSelectLoop; src/command_window.py): A runs the chosen
        command (Bank03 NCCmdSelected, choose_command); B closes the window (WND_ABORT: ClrNCCmdWnd, RemoveWindow).
        :param events: This frame's events: the key presses in them count even if the key was let go already.
        """
        result = self.menu.select(events)
        if result == WND_ABORT:
            if not self.game.game_state.config['NO_BLIT']:
                display.update(self.draw_command_window())  # WndBPressed: WndUpdateCrsrPos
            self.game.unlaunch_menu(self)
        elif result is not None:
            self.choose_command(getattr(self, COMMAND_METHODS[result]))

    def choose_command(self, command: Callable[[], Any]) -> None:
        """A COMMAND entry was chosen (WndAPressed): its arrow is drawn and stays on, not blinking, while the
        command runs and the windows it opens are in front of the COMMAND window."""
        self.cursor.hold()
        if not self.game.game_state.config['NO_BLIT']:
            display.update(self.draw_command_window())
        try:
            command()
        finally:
            # If the COMMAND window is still open, it is selecting again, its cursor blinking from the start
            # (WndUpdateCrsrPos)
            self.menu.buttons.moved()

    def draw_window_cursor(self, window_x: int, window_y: int, column: int, row: int, visible: bool = True) -> Rect:
        """
        Draw the NES cursor (src/cursor.py) in a window's tile, in the window color, or blank that tile when the
        cursor is in the "off" half of its blink (UpdateCursorGFX).
        :param window_x: The window's left edge, in blocks.
        :param window_y: The window's top edge, in blocks.
        :param column: The tile column in the window, from 0 (the left border).
        :param row: The tile row in the window, from 0 (the top border).
        :param visible: Whether the arrow is shown.
        :return: The tile's rect on the screen, for display.update.
        """
        config = self.game.game_state.config
        nes_tile = config['TILE_SIZE'] // 2
        x, y = (window_x * 2 + column) * nes_tile, (window_y * 2 + row) * nes_tile
        if config['NO_BLIT']:
            return Rect(x, y, nes_tile, nes_tile)
        return draw_cursor_tile(self.screen, x, y, config['TILE_SIZE'] // 16, self.color, visible)

    def draw_item_menu(self, menu_name: str, entries: list) -> Rect:
        """
        Draw the SPELL or ITEM window and its entries, without the cursor (NES SpellDat, PlayerInvDat).
        :param menu_name: 'spells', 'inventory' or 'discard'.
        :param entries: The spells or items to list, in order (for items, inventory_list).
        :return: The window's rect on the screen.
        """
        config = self.game.game_state.config
        tile_size = config['TILE_SIZE']
        x, y, width, height = item_menu_window(menu_name, len(entries))
        # The border, generated (src/window_renderer.py); the title and the entries are drawn over it
        draw_window(self.screen, item_menu_layout(menu_name, len(entries)), self.color, config)
        if menu_name == 'spells':
            self.draw_window_title(self._('SPELL'), x, y, SPELL_MENU_TITLE_TILE_COLUMN)

        def draw_in_window(text: str, column: int, row: int) -> None:
            draw_text(text, *self.window_text_position(x, y, column, row), self.screen, config, color=self.color,
                      letter_by_letter=False)

        for index, entry in enumerate(entries):
            row = item_menu_entry_tile_row(menu_name, index)
            if menu_name == 'spells':
                draw_in_window(str(entry), ITEM_MENU_TEXT_TILE_COLUMN, row)
                continue
            first_half, second_half = ITEM_NAME_HALVES.get(entry, (entry, ""))
            draw_in_window(first_half, ITEM_MENU_TEXT_TILE_COLUMN, row)
            if entry in COUNTED_ITEMS:
                draw_in_window(str(self.player.inventory.count(entry)), ITEM_COUNT_TILE_COLUMN, row)
            if second_half:
                draw_in_window(second_half, ITEM_MENU_TEXT_TILE_COLUMN + 1, row + 1)
        return Rect(x * tile_size, y * tile_size, width * tile_size, height * tile_size)

    def window_text_position(self, window_x: int, window_y: int, column: int, row: int) -> tuple[float, float]:
        """
        Where draw_text should draw a character in a window's tile (8x8 NES pixels).
        :param window_x: The window's left edge, in blocks.
        :param window_y: The window's top edge, in blocks.
        :param column: The tile column in the window, from 0 (the left border).
        :param row: The tile row in the window, from 0 (the top border).
        :return: (x, y) in screen pixels: the tile's left edge and its vertical middle (draw_text centers text on y).
        """
        nes_tile = self.game.game_state.config['TILE_SIZE'] / 2
        return (window_x * 2 + column) * nes_tile, (window_y * 2 + row + 0.5) * nes_tile

    def draw_window_title(self, title: str, window_x: int, window_y: int, column: int) -> None:
        """
        Draw a title in a window's top border, the way the NES puts text in a border row: the border stops one pixel
        short of the text on each side (TL_TOP2).
        :param title: The title.
        :param window_x: The window's left edge, in blocks.
        :param window_y: The window's top edge, in blocks.
        :param column: The tile column the title starts at.
        """
        config = self.game.game_state.config
        scale = config['SCALE']
        x, y = self.window_text_position(window_x, window_y, column, 0)
        if not config['NO_BLIT']:
            title_width = set_font_by_ascii_chars([title], 16, None, self.directories).size(title)[0]
            self.screen.fill(BLACK, (x - scale, window_y * config['TILE_SIZE'], title_width + 2 * scale,
                                     config['TILE_SIZE'] / 2))
        draw_text(title, x, y, self.screen, config, color=self.color, letter_by_letter=False)

    def door(self) -> None:
        """
        Open a door.
        :return: None
        """
        self.sound.play_sound(self.directories.menu_button_sfx)
        if self.player.next_tile_id == 'DOOR':
            if 'Magic Key' in self.player.inventory:
                # actually open the door
                self.player.inventory.remove('Magic Key')
                self.set_tile_by_coordinates('BRICK', self.player.next_coordinates[1], self.player.next_coordinates[0],
                                             self.player)
                self.sound.play_sound(self.directories.open_door_sfx)
            else:
                self.show_text_in_dialog_box(self._("Thou hast not a key to use."), skip_text=self.skip_text)
        else:
            self.show_text_in_dialog_box(self._("There is no door here."), skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.game_state.unpause_all_movement()

    def take(self) -> None:
        """
        NES DoTake: take what is in the treasure chest the hero is standing on.
        :return: None
        """
        chest = treasure.get(self.map_name, {}).get((self.player.row, self.player.column))
        if self.player.current_tile != 'TREASURE_BOX' or chest is None:
            # NES NoTrsrChest: also for a chest that isn't in the NES treasure table
            self.show_text_in_dialog_box(self._("There is nothing to take here, {}.").format(self.player.name),
                                         skip_text=self.skip_text)
        else:
            self.sound.play_sound(self.directories.menu_button_sfx)
            self.take_chest_contents(str(chest['item']), chest)
        self.game.unlaunch_menu(self)
        self.game.game_state.unpause_all_movement()

    def take_chest_contents(self, item_name: str, chest: dict) -> None:
        match item_name:
            case 'GOLD':
                self.take_gold(chest)
            case 'Magic Key':
                self.take_counted_item(item_name, MAX_KEYS)
            case 'Herb':
                self.take_counted_item(item_name, MAX_HERBS)
            case 'Death Necklace':
                self.take_death_necklace()
            case "Erdrick's Sword":
                self.take_erdricks_sword()
            case 'Silver Harp':
                self.take_unique_item(item_name, ('Silver Harp', 'Staff of Rain', 'Rainbow Drop'))
            case 'Stones of Sunlight':
                self.take_unique_item(item_name, ('Stones of Sunlight', 'Rainbow Drop'))
            case 'Tablet':
                self.take_tablet()
            case _:
                # NES ChkTrsrNonGold: everything else, the Staff of Rain included, is always there to take
                self.take_item(item_name)
