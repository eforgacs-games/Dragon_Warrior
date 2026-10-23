from src.common import set_gettext_language


class ControlInfo:
    def __init__(self, config):
        _ = set_gettext_language(config['LANGUAGE'])
        self.config = config
        self.push_start = _("-PUSH START-")
        self.a_button = _("K key: A Button")
        self.b_button = _("J key: B Button")
        self.start_button = _("I key: Start")
        # SELECT or Tab opens the options overlay on the map (src/options_overlay.py)
        self.select_button = _("U key/Tab: Options")
        self.arrow_keys_move_buttons = _("WASD / Arrow Keys: Move")
        self.help_button = _("H: Show Controls")
        # F4, F9 and F11 are on/off toggles, listed under "Toggle on/off:" in the H help. The STAIRS setting has no key
        # of its own: it's in the options overlay (U/Tab)
        self.auto_battle_toggle = _("F4: Auto-Battle")
        self.invulnerability_toggle = _("F9: Invulnerability")
        self.fullscreen_toggle = _("F11: Fullscreen")
        self.speed_controls = _("1-5: Game Speed")
        # G starts and stops auto-grind on the map (src/auto_grind.py)
        self.auto_grind_key = _("G: Auto-grind")
        # Window zoom (src/zoom.py): Ctrl + / Ctrl - or Ctrl and the mouse wheel, and Ctrl 0 for the normal size
        self.zoom_controls = _("Ctrl +/-/Wheel: Zoom")
        self.zoom_reset = _("Ctrl 0: Reset Zoom")
        self.controls: tuple[str, ...] = (
            self.a_button, self.b_button, self.start_button, self.select_button, self.arrow_keys_move_buttons,
            self.help_button, self.auto_battle_toggle, self.invulnerability_toggle,
            self.fullscreen_toggle, self.speed_controls, self.auto_grind_key, self.zoom_controls, self.zoom_reset)
        # The H help, one string per dialog box page (the A button turns the page). The dialog box fits five rows
        # above the continue arrow, so each page is a short group of related keys. "Controls:\n" keeps its newline
        # so it still matches the existing Korean translation.
        self.help_pages: tuple[str, ...] = (
            "\n".join((_("Controls:\n").rstrip("\n"), self.a_button, self.b_button, self.start_button,
                       self.select_button)),
            "\n".join((self.arrow_keys_move_buttons, self.help_button, self.speed_controls, self.auto_grind_key)),
            "\n".join((_("Toggle on/off:"), self.auto_battle_toggle, self.invulnerability_toggle,
                       self.fullscreen_toggle)),
            "\n".join((_("Window zoom:"), self.zoom_controls, self.zoom_reset)),
        )
        if config.get('DEBUG_KEYS'):
            # Dev config only (src/debug_tools.py), on a page of their own
            debug_controls = (_("F5: Warp"), _("F6: Give item/gold/level"), _("F7: Load checkpoint"))
            self.controls += debug_controls
            self.help_pages += ("\n".join((_("Debug keys:"),) + debug_controls),)
        self.input_name_prompt = _("Type your name using the keyboard.\n"
                                   "If you are using a joystick, press TAB to switch to joystick input.")
