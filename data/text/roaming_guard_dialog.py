from data.text.dialog import Dialog


class RoamingGuardDialog(Dialog):
    def __init__(self, player, map_name):
        super().__init__(player)
        if map_name == 'TantegelThroneRoom':
            self.dialog_text = (
                # TODO: Fix roaming guard talk function. Only able to talk to the roaming guard's initial position.
                # know_about_princess = input("'Dost thou know about Princess Gwaelin?'")
                # if not know_about_princess:
                #     print_with_beep_sfx("'Half a year now hath passed since the Princess was kidnapped by the enemy.'")
                #     print_with_beep_sfx("'Never does the King speak of it, but he must be suffering much.'")
                # else:
                #     print_with_beep_sfx(f"'{self.player.name}, please save the Princess.'")
                # TODO: Reset this later to use input(), but just for testing it out we can leave it this way for now.
                "'Dost thou know about Princess Gwaelin?'",
                "'Half a year now hath passed since the Princess was kidnapped by the enemy.'",
                "'Never does the King speak of it, but he must be suffering much.'"

            )
