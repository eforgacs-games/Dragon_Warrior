from data.text.dialog import Dialog


class WomanDialog(Dialog):
    def __init__(self, player, map_name):
        super().__init__(player, None)
        match map_name:
            case 'TantegelCourtyard':
                self.dialog_text = (
                    "'Where oh where can I find Princess Gwaelin?'",
                )
            case 'Brecconary':
                self.dialog_text = (
                    "'Welcome! \n"
                    "Enter the shop and speak to its keeper across the desk.'",
                )
