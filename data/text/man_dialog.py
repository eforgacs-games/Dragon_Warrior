from data.text.dialog import Dialog


class ManDialog(Dialog):
    def __init__(self, player, map_name, screen):
        super().__init__(player, screen)
        match map_name:
            case 'Brecconary':
                self.dialog_text = (
                    "There is a town where magic keys can be purchased.",
                )
            case 'TantegelCourtyard':
                self.dialog_text = (
                    "There was a time when Brecconary was a paradise.\n"
                    "Then the Dragonlord's minions came.",
                )
