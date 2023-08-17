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
        self.controls = self.a_button, self.b_button, self.start_button, self.arrow_keys_move_buttons
        self.input_name_prompt = _("Type your name using the keyboard.\n"
                                   "If you are using a joystick, press TAB to switch to joystick input.")
