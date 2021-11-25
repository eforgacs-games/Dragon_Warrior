from src.common import print_with_beep_sfx


class Dialog:
    def __init__(self, player, dialog_character):
        self.player = player
        self.dialog_character = dialog_character
        self.dialog_text = []

    def say_dialog(self):
        if self.dialog_text:
            for line in self.dialog_text:
                print_with_beep_sfx(line)
        else:
            print("Character has no dialog.")
