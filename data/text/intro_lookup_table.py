import gettext
import os

from src.config import dev_config

# TODO: Replace with game config
config = dev_config

if config['LANGUAGE'] == 'Korean':
    ko = gettext.translation('base', localedir=os.path.join('../data/text/locales'), languages=['ko'])
    ko.install()
    _ = ko.gettext
else:
    _ = gettext.gettext

push_start = _("-PUSH START-")
a_button = _("K key: A Button")
b_button = _("J key: B Button")
start_button = _("I key: Start")
arrow_keys_move_buttons = _("WASD / Arrow Keys: Move")
controls = a_button, b_button, start_button, arrow_keys_move_buttons
input_name_prompt = _("Type your name using the keyboard.\n"
                      "If you are using a joystick, press the TAB key to switch to joystick input.")
