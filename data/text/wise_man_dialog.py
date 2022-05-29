from data.text.dialog import Dialog


class WiseManDialog(Dialog):
    def __init__(self, player, map_name):
        super().__init__(player, None, None)
        match map_name:
            case 'TantegelCourtyard':
                self.dialog_text = (
                    f"'{self.player.name}'s coming was foretold by legend. May the light shine upon this brave warrior.'",
                )
            #     make screen flash 8 times
                self.player.current_mp = self.player.max_mp
            case 'Brecconary':
                self.dialog_text = (
                    "'If thou art cursed, come again.'",
                )
            case 'Garinham':
                self.dialog_text = (
                    "'Many believe that Princess Gwaelin is hidden away in a cave.'",
                )
