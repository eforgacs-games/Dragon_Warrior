from data.text.dialog import Dialog


class RightFaceGuardDialog(Dialog):
    def __init__(self, player, map_name):
        super().__init__(player)
        if map_name == 'TantegelThroneRoom':
            self.dialog_text = (
                "'East of this castle is a town where armor, weapons, and many other items may be purchased.'",
                f"'Return to the Inn for a rest if thou art wounded in battle, {self.player.name}.'",
                "'Sleep heals all.'"
            )
