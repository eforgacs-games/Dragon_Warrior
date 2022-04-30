from data.text.dialog import Dialog


class UpFaceGuardDialog(Dialog):
    def __init__(self, player, map_name, dialog_character):
        super().__init__(player, dialog_character)
        if map_name == 'TantegelCourtyard':
            self.dialog_text = (
                "'If thou art planning to take a rest, first see King Lorik.'",
            )
