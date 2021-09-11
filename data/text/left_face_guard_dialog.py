from data.text.dialog import Dialog


class LeftFaceGuardDialog(Dialog):
    def __init__(self, player, map_name):
        super().__init__(player)
        if map_name == 'TantegelThroneRoom':
            self.dialog_text = (
                "'If thou hast collected all the Treasure Chests, a key will be found.'",
                "'Once used, the key will disappear, but the door will be open and thou may pass through.'"
            )
