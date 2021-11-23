from src.common import print_with_beep_sfx


class Dialog:
    def __init__(self, player):
        self.player = player
        self.dialog_text = None

    def say_dialog(self):
        if self.dialog_text:
            for line in self.dialog_text:
                print_with_beep_sfx(line)
        else:
            print("Character has no dialog.")

    @staticmethod
    def roaming_guard_tantegel_throne_room():
        # TODO: Fix roaming guard talk function. Only able to talk to the roaming guard's initial position.
        # know_about_princess = input("'Dost thou know about Princess Gwaelin?'")
        # if not know_about_princess:
        #     print_with_beep_sfx("'Half a year now hath passed since the Princess was kidnapped by the enemy.'")
        #     print_with_beep_sfx("'Never does the King speak of it, but he must be suffering much.'")
        # else:
        #     print_with_beep_sfx(f"'{self.player.name}, please save the Princess.'")
        # TODO: Reset this later to use input(), but just for testing it out we can leave it this way for now.
        print_with_beep_sfx("'Dost thou know about Princess Gwaelin?'")
        print_with_beep_sfx("'Half a year now hath passed since the Princess was kidnapped by the enemy.'")
        print_with_beep_sfx("'Never does the King speak of it, but he must be suffering much.'")
