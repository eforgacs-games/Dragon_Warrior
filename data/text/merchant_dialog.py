from data.text.dialog import Dialog


class MerchantDialog(Dialog):
    def __init__(self, player, map_name):
        super().__init__(player)
        match map_name:
            case 'TantegelCourtyard':
                self.dialog_text = (
                    "'We are merchants who have traveled much in this land. Many of our colleagues have been killed by servants of the Dragonlord.'",
                )
            case 'Brecconary':
                self.dialog_text = (
                    "'We deal in weapons and armor."
                    "Dost thou wish to buy anything today?'",
                )
            case 'Garinham':
                self.dialog_text = (
                    "'Welcome.\n"
                    "We deal in tools.\n"
                    "What can I do for thee?'",
                )
