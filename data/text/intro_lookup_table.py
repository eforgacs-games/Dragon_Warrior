from src.common import set_gettext_language
from src.controls import SPEED_ACTIONS, action_keys, directions_label, group_label, keys_label, \
    pad_is_default, pad_name


class ControlInfo:
    def __init__(self, config):
        _ = set_gettext_language(config['LANGUAGE'])
        self.config = config
        self.push_start = _("-PUSH START-")
        # The keys as the player has bound them (src/controls.py; the CONTROLS screen, src/controls_screen.py)
        self.a_button = _("{}: A Button").format(keys_label('A'))
        self.b_button = _("{}: B Button").format(keys_label('B'))
        self.start_button = _("{}: Start").format(keys_label('START'))
        # SELECT or Tab opens the options overlay on the map (src/options_overlay.py)
        self.select_button = _("{}: Options").format(keys_label('SELECT') + '/' + keys_label('OPTIONS')
                                                     if action_keys('OPTIONS') else keys_label('SELECT'))
        self.arrow_keys_move_buttons = _("{}: Move").format(directions_label(_("ARROWS")))
        # Enter: TALK, TAKE or DOOR when one applies (Game.handle_enter_key)
        self.smart_a_button = _("{}: Smart A").format(keys_label('SMART_A'))
        self.help_button = _("{}: Show Controls").format(keys_label('HELP'))
        # F4, F9 and F11 are on/off toggles, listed under "Toggle on/off:" in the H help. The STAIRS setting has no key
        # of its own: it's in the options overlay (U/Tab)
        self.auto_battle_toggle = _("{}: Auto-Battle").format(keys_label('AUTO_BATTLE'))
        self.invulnerability_toggle = _("{}: Invulnerability").format(keys_label('INVULNERABLE'))
        self.fullscreen_toggle = _("{}: Fullscreen").format(keys_label('FULLSCREEN'))
        self.speed_controls = _("{}: Game Speed").format(group_label(tuple(SPEED_ACTIONS), "1-5"))
        # G starts and stops auto-grind on the map (src/auto_grind.py)
        self.auto_grind_key = _("{}: Auto-grind").format(keys_label('AUTO_GRIND'))
        # Q shows the quest journal (src/quest_journal.py), unless QUEST JOURNAL is OFF in the options overlay
        self.quest_journal_key = _("{}: Quest Journal").format(keys_label('QUEST_JOURNAL'))
        # Window zoom (src/zoom.py): Ctrl + / Ctrl - or Ctrl and the mouse wheel, and Ctrl 0 for the normal size
        self.zoom_controls = _("Ctrl +/-/Wheel: Zoom")
        self.zoom_reset = _("Ctrl 0: Reset Zoom")
        # Save states (src/save_state.py): Shift + F1/F2/F3 saves into slot 1/2/3, F1/F2/F3 loads it
        self.save_state_keys = _("{}: Save state").format(
            group_label(('SAVE_STATE_1', 'SAVE_STATE_2', 'SAVE_STATE_3'), "SHIFT+F1-F3"))
        self.load_state_keys = _("{}: Load state").format(
            group_label(('LOAD_STATE_1', 'LOAD_STATE_2', 'LOAD_STATE_3'), "F1-F3"))
        # Hold Backspace on the map to rewind (src/rewind.py)
        self.rewind_key = _("{}: Rewind").format(keys_label('REWIND'))
        # A controller (src/gamepad.py), as bound (the CONTROLS screen's PAD column): NES A and B by position, the right
        # and the bottom face buttons, by default. A button bound elsewhere is named as the CONTROLS screen names it.
        self.controller_a = _("Right Button: A") if pad_is_default('A') else _("{}: A").format(pad_name('A'))
        self.controller_b = _("Bottom Button: B") if pad_is_default('B') else _("{}: B").format(pad_name('B'))
        self.controller_start = _("Start Button: Start") if pad_is_default('START') else _("{}: Start").format(
            pad_name('START'))
        self.controller_select = _("Back Button: Select") if pad_is_default('SELECT') else _("{}: Select").format(
            pad_name('SELECT'))
        self.controller_move = _("D-Pad/Stick: Move") if all(
            pad_is_default(name) for name in ('UP', 'DOWN', 'LEFT', 'RIGHT')) else _("{}/Stick: Move").format(
            ','.join(pad_name(name) for name in ('UP', 'DOWN', 'LEFT', 'RIGHT')))
        self.controller_speed = _("Right Trigger: Speed") if pad_is_default('NEXT_SPEED') else _("{}: Speed").format(
            pad_name('NEXT_SPEED'))
        # The controller's extra buttons: by default the left and right bumpers (shoulder buttons) load and save state
        # 1, and the left trigger, held, rewinds
        self.controller_load_state = _("LB: Load state 1") if pad_is_default('LOAD_STATE_1') else _(
            "{}: Load state 1").format(pad_name('LOAD_STATE_1'))
        self.controller_save_state = _("RB: Save state 1") if pad_is_default('SAVE_STATE_1') else _(
            "{}: Save state 1").format(pad_name('SAVE_STATE_1'))
        self.controller_rewind = _("LT (hold): Rewind") if pad_is_default('REWIND') else _(
            "{} (hold): Rewind").format(pad_name('REWIND'))
        # The dungeon map (src/dungeon_map.py): M, or the controller's top face button, by default, on a dark floor
        self.dungeon_map_key = _("{}: Dungeon map").format(keys_label('MAP'))
        self.controller_dungeon_map = _("Top Button: Dungeon map") if pad_is_default('MAP') else _(
            "{}: Dungeon map").format(pad_name('MAP'))
        # The message log on the map (src/message_log.py): L, or the controller's left face button, by default
        self.message_log_key = _("{}: Message log").format(keys_label('MESSAGE_LOG'))
        self.controller_message_log = _("Left Button: Message log") if pad_is_default('MESSAGE_LOG') else _(
            "{}: Message log").format(pad_name('MESSAGE_LOG'))
        self.controls: tuple[str, ...] = (
            self.a_button, self.b_button, self.start_button, self.select_button, self.arrow_keys_move_buttons,
            self.smart_a_button, self.help_button, self.auto_battle_toggle, self.invulnerability_toggle,
            self.fullscreen_toggle, self.speed_controls, self.auto_grind_key, self.quest_journal_key, self.zoom_controls,
            self.zoom_reset, self.save_state_keys, self.load_state_keys, self.rewind_key,
            self.controller_a, self.controller_b, self.controller_start, self.controller_select, self.controller_move,
            self.controller_speed, self.controller_load_state, self.controller_save_state, self.controller_rewind,
            self.dungeon_map_key, self.controller_dungeon_map, self.message_log_key, self.controller_message_log)
        # The H help, one string per dialog box page (the A button turns the page). The dialog box fits five rows
        # above the continue arrow, so each page is a short group of related keys. "Controls:\n" keeps its newline
        # so it still matches the existing Korean translation.
        self.help_pages: tuple[str, ...] = (
            "\n".join((_("Controls:\n").rstrip("\n"), self.a_button, self.b_button, self.start_button,
                       self.select_button)),
            "\n".join((self.arrow_keys_move_buttons, self.smart_a_button, self.speed_controls, self.auto_grind_key)),
            "\n".join((_("Toggle on/off:"), self.auto_battle_toggle, self.invulnerability_toggle,
                       self.fullscreen_toggle)),
            "\n".join((_("Window zoom:"), self.zoom_controls, self.zoom_reset)),
            "\n".join((_("Save states:"), self.save_state_keys, self.load_state_keys, self.rewind_key)),
            self.quest_journal_key,
            "\n".join((_("Controller:"), self.controller_a, self.controller_b, self.controller_start,
                       self.controller_select)),
            "\n".join((self.controller_move, self.controller_speed, self.controller_load_state,
                       self.controller_save_state, self.controller_rewind)),
            "\n".join((_("Dungeon map:"), self.dungeon_map_key, self.controller_dungeon_map)),
            "\n".join((self.help_button, self.message_log_key, self.controller_message_log)),
        )
        if config.get('DEBUG_KEYS'):
            # Dev config only (src/debug_tools.py), on a page of their own
            debug_controls = (_("F5: Warp"), _("F6: Give item/gold/level"), _("F7: Load checkpoint"))
            self.controls += debug_controls
            self.help_pages += ("\n".join((_("Debug keys:"),) + debug_controls),)
        self.input_name_prompt = _("Type your name using the keyboard.\n"
                                   "If you are using a joystick, press TAB to switch to joystick input.")
