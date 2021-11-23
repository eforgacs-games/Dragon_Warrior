from data.text.dialog import Dialog


class WiseManDialog(Dialog):
    def __init__(self, player, map_name):
        super().__init__(player)
        if map_name == 'Brecconary':
            self.dialog_text = (
                "'If thou art cursed, come again.'",
            )
