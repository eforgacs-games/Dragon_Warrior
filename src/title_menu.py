"""The title menu (NES Bank03 StartMenu): BEGIN A NEW QUEST, CONTINUE A QUEST, CHANGE MESSAGE SPEED, COPY A QUEST and
ERASE AN ADVENTURE LOG, run before the game starts.

The title menu, BEGIN A NEW QUEST's open logs window and CONTINUE A QUEST's used logs window with one log are generated
from the NES window data (src/title_windows.py) and chosen from with GameFunctions.main_menu_selection; the other
windows that open over the title menu (the log lists, message speed, YES/NO) are src/options_screen.py.

The saves the entries read, copy and erase are the adventure logs in the save folder (src/save_file.py). Starting the
quest is the Game's: a new quest starts in the throne room (Game.start_at_throne_room) and a continued one loads its
save (Game.load_game).
"""
from dataclasses import replace
import os
import shutil
from typing import Any, Protocol
from collections.abc import Callable

from pygame import Surface

from src.directories import Directories
from src.common import set_gettext_language
from src.game_functions import MENU_BACK, GameFunctions
from src.menu_functions import NameSelection
from src.options_screen import DEFAULT_OPTIONS, MESSAGE_SPEED_SAVE_KEY, OptionsScreen, apply_options, \
    message_speed_from_save
from src.player.player_stats import get_level_by_experience
from src.save_file import ADVENTURE_LOGS, EXPERIENCE_KEY, NAME_KEY, load_save, read_save, save_files, save_path, \
    save_slot_number, used_logs, write_save
from src.save_file import save_file_name as save_file_name_for
from src.sound import Sound
from src.title_windows import draw_title_windows, title_menu_layout, title_translate
from src.waiting import menu_ticks  # the cursor blink starts on menu time (src/cursor.py BlinkingCursor)
from src.windows import WindowLayout, open_logs_layout, used_logs_layout

# Returned by a title menu entry that goes back to the title menu when it's done (NES WndBackToMain)
BACK_TO_TITLE_MENU = object()
# COPY A QUEST's place in the title menu with a log open (FullMenuDat); with none open it isn't there
COPY_ENTRY = 3
# BEGIN A NEW QUEST's place in the title menu: alone in NewQuestDat, third in FullMenuDat
BEGIN_ENTRY_WITH_NO_LOG = 0
BEGIN_ENTRY = 2


class TitleMenuGame(Protocol):
    """What the title menu uses of the Game. TitleMenu reads them from the Game each time, since the Game replaces some
    of them (a fullscreen toggle makes a new screen, a map change a new CommandMenu)."""
    config: dict
    screen: Surface
    player: Any
    cmd_menu: Any
    sound: Sound
    directories: Directories
    game_functions: GameFunctions

    def load_game(self, save_file: dict, direction: int | None = None) -> None: ...

    def start_at_throne_room(self) -> None: ...


class TitleMenu:
    """The title menu, run by Game.main before the game starts (show_main_menu_screen)."""

    def __init__(self, game: TitleMenuGame):
        self.game = game
        # The adventure log save files (a list of names), read each time the title menu is shown (show_title_menu);
        # None until then
        self.save_dir_contents: Any = None

    # What the title menu uses of the Game, read from it each time, as the Game's own methods did
    @property
    def config(self) -> dict:
        return self.game.config

    @property
    def screen(self) -> Surface:
        return self.game.screen

    @property
    def player(self) -> Any:
        return self.game.player

    @property
    def sound(self) -> Sound:
        return self.game.sound

    @property
    def directories(self) -> Directories:
        return self.game.directories

    @property
    def game_functions(self) -> GameFunctions:
        return self.game.game_functions

    def show_main_menu_screen(self, screen) -> None:
        """The title menu. Choosing CHANGE MESSAGE SPEED, COPY A QUEST or ERASE AN ADVENTURE LOG, or B in CONTINUE A
        QUEST's log window, comes back to it afterwards (NES WndBackToMain)."""
        while self.show_title_menu(screen) is BACK_TO_TITLE_MENU:
            pass

    def show_title_menu(self, screen) -> object:
        """Shows the title menu once and runs the chosen entry; returns what it returns (BACK_TO_TITLE_MENU to show the
        menu again)."""
        if not os.path.exists(self.directories.save_dir):
            os.makedirs(self.directories.save_dir)
        self.save_dir_contents = self.save_files()
        used = len(self.save_dir_contents)
        if used > len(ADVENTURE_LOGS):
            print(f"Error: More than {len(ADVENTURE_LOGS)} save files detected. Exiting.")
            exit(1)
        if used == 0:
            # NewQuestDat: BEGIN A NEW QUEST
            entries: tuple[Callable[[], object], ...] = (self.begin_new_quest,)
        elif used < len(ADVENTURE_LOGS):
            # FullMenuDat: CONTINUE A QUEST, CHANGE MESSAGE SPEED, BEGIN A NEW QUEST, COPY A QUEST, ERASE A QUEST
            entries = (self.continue_quest, self.change_message_speed, self.begin_new_quest, self.copy_quest,
                       self.erase_quest)
        else:
            # ContChngErsDat, with every log used: CONTINUE A QUEST, CHANGE MESSAGE SPEED, ERASE A QUEST
            entries = (self.continue_quest, self.change_message_speed, self.erase_quest)
        selection = self.game_functions.main_menu_selection(menu_ticks(), screen, title_menu_layout(used))
        return entries[selection]()

    def begin_new_quest(self) -> object:
        """BEGIN A NEW QUEST: an adventure log, the name, then the options. B in the log window, or Escape in the
        name entry, cancels it, back to the title menu with nothing saved."""
        log_window = self.select_adventure_log(self.screen)
        if log_window is BACK_TO_TITLE_MENU:
            return BACK_TO_TITLE_MENU
        # The open logs window stays on the screen behind the name entry, its arrow on the chosen log
        name_selection = NameSelection(self.config, log_window if isinstance(log_window, tuple) else None)
        name = name_selection.select_name(menu_ticks(), self.screen, self.game.cmd_menu)
        if name is None:
            return BACK_TO_TITLE_MENU
        self.player.name = name
        self.choose_new_quest_options()
        self.player.set_initial_stats()
        self.sound.play_sound(self.directories.menu_button_sfx)
        self.game.start_at_throne_room()
        return None

    def save_files(self) -> list[str]:
        """The adventure log save files in the save folder, ignoring anything else that might be there."""
        return save_files(self.directories.save_dir)

    def continue_quest(self) -> object:
        """CONTINUE A QUEST: choose a used adventure log (ShowUsedLogs) and load it. With one log, its window with the
        hero's name (LogList1Dat2, LogList2Dat2 or LogList3Dat2) over the title menu; with several, the log window of
        src/options_screen.py. B in either goes back to the title menu (WndBackToMain)."""
        if len(self.save_dir_contents) == 1:
            logs = self.used_logs()
            if not logs:
                # its save can't be read: there is nothing to continue
                return BACK_TO_TITLE_MENU
            selection = self.game_functions.main_menu_selection(menu_ticks(), self.screen,
                                                                used_logs_layout(tuple(logs)),
                                                                below=[(self.title_layout(), 0)], b_goes_back=True)
            if selection == MENU_BACK:
                return BACK_TO_TITLE_MENU
            save_file_name = save_file_name_for(logs[selection][0])
        elif self.save_dir_contents:
            options_screen = OptionsScreen(self.screen, self.config, self.title_menu_background(0))
            slot = options_screen.choose_log(self.used_logs())
            if slot is None:
                return BACK_TO_TITLE_MENU
            save_file_name = save_file_name_for(slot)
        else:
            self.sound.play_sound(self.directories.menu_button_sfx)
            self.game.start_at_throne_room()
            return None
        loaded_save = load_save(os.path.join(self.directories.save_dir, save_file_name))
        self.sound.play_sound(self.directories.menu_button_sfx)
        # load_game has already cut to black, faded the starting map in, started its music and made a new
        # CommandMenu, as NES StartAtThroneRoom does; fading out again here would show the map twice
        self.game.load_game(loaded_save)
        # Save back to the same log, so continuing and saving doesn't create another save file
        self.player.adventure_log = save_slot_number(save_file_name)
        return None

    def used_logs(self) -> list[tuple[int, str]]:
        """ShowUsedLogs: each used adventure log's number and hero's name, for the log window."""
        return used_logs(self.directories.save_dir, self.save_dir_contents or self.save_files())

    def change_message_speed(self) -> object:
        """NES DoChngMsgSpeed (Bank03): choose a used adventure log (ShowUsedLogs), then its message speed in the NES
        window (WND_MSG_SPEED); ChngMsgSpeed saves it to that log (SaveCurrentGame). B in the log or speed window saves
        nothing. Either way it's back to the title menu (WndBackToMain). See src/options_screen.py."""
        logs = self.used_logs()
        if not logs:
            return BACK_TO_TITLE_MENU
        options_screen = OptionsScreen(self.screen, self.config, self.title_menu_background(1))
        slot = options_screen.choose_log(logs)
        if slot is None:
            return BACK_TO_TITLE_MENU
        log_path = save_path(self.directories.save_dir, slot)
        save = read_save(self.directories.save_dir, save_file_name_for(slot)) or {}
        chosen = options_screen.choose_message_speed(message_speed_from_save(save))
        if chosen is not None:
            save[MESSAGE_SPEED_SAVE_KEY] = chosen
            write_save(log_path, save)
        return BACK_TO_TITLE_MENU

    def choose_new_quest_options(self) -> None:
        """NES NewQuest (LF8D4): after the name, the message speed window with the cursor on NORMAL. The choice is used
        from now on and saved with the log (CommandMenu.save). B keeps NORMAL (the NES goes back to the title menu
        instead). This game's own settings start at their defaults; they're changed during play (src/options_overlay.py)."""
        options_screen = OptionsScreen(self.screen, self.config)
        chosen = options_screen.choose_message_speed(DEFAULT_OPTIONS.message_speed)
        apply_options(self.config, replace(DEFAULT_OPTIONS, message_speed=chosen or DEFAULT_OPTIONS.message_speed))

    def title_layout(self) -> WindowLayout:
        """The title menu window for the logs in use (NewQuestDat, FullMenuDat or ContChngErsDat)."""
        return title_menu_layout(len(self.save_dir_contents or []))

    def title_menu_background(self, entry: int) -> Callable[[Surface], None]:
        """Draws the title menu with this entry chosen (its arrow held on), for the windows to open over: CONTINUE A
        QUEST (0), CHANGE MESSAGE SPEED (1), COPY A QUEST (COPY_ENTRY) or ERASE A QUEST (erase_entry()). With every
        log used the menu has no COPY A QUEST (ContChngErsDat), so ERASE is entry 2 there."""
        layout = self.title_layout()
        translate = title_translate(set_gettext_language(self.config.get('LANGUAGE')))

        def draw(screen: Surface) -> None:
            draw_title_windows(screen, [(layout, entry, True)], self.config, translate)
        return draw

    def erase_entry(self) -> int:
        """ERASE AN ADVENTURE LOG's place in the title menu: last in FullMenuDat (4), or in ContChngErsDat (2)."""
        return 2 if len(self.save_dir_contents or []) >= len(ADVENTURE_LOGS) else 4

    def copy_quest(self) -> object:
        """NES DoCopyGame (Bank03): choose the log to copy from among the used logs (ShowUsedLogs), then the log to
        copy it to among the open logs (ShowOpenLogs, so a used log is never overwritten), then YES or NO (YesNo2Dat).
        Copies on YES (CopyGame). B anywhere, NO, or no open log copies nothing. Either way it's back to the title menu
        (WndBackToMain), never on into a game with no log. The title menu only offers COPY A QUEST while a log is
        open (FullMenuDat)."""
        logs = self.used_logs()
        used = self.save_files()
        open_logs = [log for log in ADVENTURE_LOGS if save_file_name_for(log) not in used]
        if not logs or not open_logs:
            return BACK_TO_TITLE_MENU
        options_screen = OptionsScreen(self.screen, self.config, self.title_menu_background(COPY_ENTRY))
        src_slot = options_screen.choose_log(logs)
        if src_slot is None:
            return BACK_TO_TITLE_MENU
        dst_slot = options_screen.choose_open_log(open_logs)
        if dst_slot is None or not options_screen.confirm():
            return BACK_TO_TITLE_MENU
        shutil.copy2(save_path(self.directories.save_dir, src_slot), save_path(self.directories.save_dir, dst_slot))
        self.save_dir_contents = self.save_files()
        return BACK_TO_TITLE_MENU

    def erase_quest(self) -> object:
        """NES DoEraseGame (Bank03): choose a used log (ShowUsedLogs), then VerifyErase shows its hero's name and
        level (EraseLogDat) and asks YES or NO (YesNo2Dat). Erases it on YES (ClearValidSaves). B, or NO, erases
        nothing. Either way it's back to the title menu (WndBackToMain), never on into a game with no log."""
        logs = self.used_logs()
        if not logs:
            return BACK_TO_TITLE_MENU
        options_screen = OptionsScreen(self.screen, self.config,
                                       self.title_menu_background(self.erase_entry()))
        slot = options_screen.choose_log(logs)
        if slot is None:
            return BACK_TO_TITLE_MENU
        save_file_name = save_file_name_for(slot)
        save = read_save(self.directories.save_dir, save_file_name) or {}
        experience = save.get(EXPERIENCE_KEY)
        level = get_level_by_experience(experience if isinstance(experience, int) else 0)
        if options_screen.confirm_erase(str(save.get(NAME_KEY, '')), level):
            os.remove(os.path.join(self.directories.save_dir, save_file_name))
            self.save_dir_contents = self.save_files()
        return BACK_TO_TITLE_MENU

    def select_adventure_log(self, screen) -> object:
        """BEGIN A NEW QUEST's log window, ShowOpenLogs: the open logs only (LogList??Dat1), so a new quest never
        overwrites a used log. The chosen log becomes the hero's, and the window and the entry chosen in it are
        returned, for the name entry to draw behind it. B goes back to the title menu (DoNewQuest: ShowOpenLogs
        returns WND_ABORT, then WndBackToMain), returning BACK_TO_TITLE_MENU, as does having no open log
        (NoOpenGames)."""
        used = self.save_files()
        open_logs = tuple(log for log in ADVENTURE_LOGS if save_file_name_for(log) not in used)
        if not open_logs:
            return BACK_TO_TITLE_MENU
        layout = open_logs_layout(open_logs)
        begin_entry = BEGIN_ENTRY if used else BEGIN_ENTRY_WITH_NO_LOG
        selection = self.game_functions.main_menu_selection(menu_ticks(), screen, layout,
                                                            below=[(title_menu_layout(len(used)), begin_entry)],
                                                            b_goes_back=True)
        if selection == MENU_BACK:
            return BACK_TO_TITLE_MENU
        self.player.adventure_log = open_logs[selection]
        return layout, selection
