from data.text.dialog import Dialog


class LeftFaceGuardDialog(Dialog):
    def __init__(self, player, map_name):
        super().__init__(player, None)
        match map_name:
            case 'TantegelThroneRoom':
                self.dialog_text = (
                    "'If thou hast collected all the Treasure Chests, a key will be found.'",
                    "'Once used, the key will disappear, but the door will be open and thou may pass through.'"
                )
            case 'TantegelCourtyard':
                self.dialog_text = (
                    "'Welcome to Tantegel Castle.'",
                )
