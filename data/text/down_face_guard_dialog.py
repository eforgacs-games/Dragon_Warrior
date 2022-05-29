from data.text.dialog import Dialog


class DownFaceGuardDialog(Dialog):
    def __init__(self, player, map_name, screen):
        super().__init__(player, screen)
        if map_name == 'TantegelCourtyard':
            self.dialog_text = (
                "King Lorik will record thy deeds in his Imperial Scroll so thou may return to thy quest later.",
            )
