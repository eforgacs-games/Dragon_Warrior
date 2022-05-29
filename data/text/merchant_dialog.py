from data.text.dialog import Dialog


class MerchantDialog(Dialog):
    def __init__(self, player, map_name, dialog_character, screen):
        super().__init__(player, dialog_character, screen)
        match map_name:
            case 'TantegelCourtyard':
                self.dialog_text = (
                    "'We are merchants who have traveled much in this land. Many of our colleagues have been killed by servants of the Dragonlord.'",
                )
            case 'Brecconary':
                self.dialog_text = (
                    "'We deal in weapons and armor. \n"
                    "Dost thou wish to buy anything today?'",
                )
            case 'Garinham':
                match self.dialog_character:
                    case 'MERCHANT':
                        self.dialog_text = (
                            "'Welcome.\n"
                            "We deal in tools.\n"
                            "What can I do for thee?'",
                        )
                    case 'MERCHANT_2':
                        self.dialog_text = (
                            "'Welcome to the traveler's Inn."
                            "Room and board is 25 GOLD per night."
                            "Dost thou want a room?'",
                        )
                    case 'MERCHANT_3':
                        self.dialog_text = (
                            "'We deal in weapons and armor.\n"
                            "Dost thou wish to buy anything today?'",
                        )
