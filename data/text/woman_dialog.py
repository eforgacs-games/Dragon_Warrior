from data.text.dialog import Dialog


class WomanDialog(Dialog):
    def __init__(self, player, map_name, screen):
        super().__init__(player, screen)
        match map_name:
            case 'TantegelCourtyard':
                match self.dialog_character:
                    case 'WOMAN_2':
                        self.dialog_text = (
                            "Where oh where can I find Princess Gwaelin?",
                        )
            case 'Brecconary':
                self.dialog_text = (
                    "Welcome! \n"
                    "Enter the shop and speak to its keeper across the desk.",
                )
