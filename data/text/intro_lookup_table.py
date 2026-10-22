from src.common import set_gettext_language


class ControlInfo:
    def __init__(self, config):
        _ = set_gettext_language(config['LANGUAGE'])
        self.config = config
        self.push_start = _("-PUSH START-")
        self.a_button = _("K key: A Button")
        self.b_button = _("J key: B Button")
        self.start_button = _("I key: Start")
        self.arrow_keys_move_buttons = _("WASD / Arrow Keys: Move")
        self.help_button = _("F1: Show Controls")
        self.auto_stairs_toggle = _("F2: Toggle Auto-Stairs")
        self.auto_battle_toggle = _("F3: Toggle Auto-Battle")
        self.invulnerability_toggle = _("F4: Toggle Invulnerability")
        self.fullscreen_toggle = _("F11: Toggle Fullscreen")
        self.speed_controls = _("1-4: Adjust Game Speed")
        self.controls: tuple[str, ...] = (
            self.a_button, self.b_button, self.start_button, self.arrow_keys_move_buttons, self.help_button,
            self.auto_stairs_toggle, self.auto_battle_toggle, self.invulnerability_toggle, self.fullscreen_toggle,
            self.speed_controls)
        if config.get('DEBUG_KEYS'):
            # Dev config only (src/debug_tools.py)
            self.controls += (_("F5: Warp"), _("F6: Give item/gold/level"), _("F7: Load checkpoint"))
        self.input_name_prompt = _("Type your name using the keyboard.\n"
                                   "If you are using a joystick, press TAB to switch to joystick input.")
