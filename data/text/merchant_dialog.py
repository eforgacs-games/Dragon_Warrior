from data.text.dialog import Dialog


class MerchantDialog(Dialog):
    def __init__(self, player, map_name):
        super().__init__(player)
        if map_name == 'Brecconary':
            self.dialog_text = (
                "'We deal in weapons and armor."
                "Dost thou wish to buy anything today?'"
            )
