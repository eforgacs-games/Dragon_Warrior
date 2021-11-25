from data.text.dialog import Dialog


class WiseManDialog(Dialog):
    def __init__(self, player, map_name):
        super().__init__(player, None)
        match map_name:
            case 'Brecconary':
                self.dialog_text = (
                    "'If thou art cursed, come again.'",
                )
            case 'Garinham':
                self.dialog_text = (
                    "'Many believe that Princess Gwaelin is hidden away in a cave.'",
                )
