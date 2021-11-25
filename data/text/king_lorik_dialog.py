from data.text.dialog import Dialog
from src.common import print_with_beep_sfx


class KingLorikDialog(Dialog):
    def __init__(self, player, is_initial_dialog, throne_room_door_locked):
        super().__init__(player, None)
        self.is_initial_dialog = is_initial_dialog
        self.throne_room_door_locked = throne_room_door_locked
        if self.throne_room_door_locked:
            if self.is_initial_dialog:
                self.dialog_text = (
                    "'Descendant of Erdrick, listen now to my words.'",
                    "'It is told that in ages past Erdrick fought demons with a Ball of Light.'",
                    "'Then came the Dragonlord who stole the precious globe and hid it in the darkness.'",
                    f"'Now, {self.player.name}, thou must help us recover the Ball of Light and restore peace to our land.'",
                    "'The Dragonlord must be defeated.'",
                    "'Take now whatever thou may find in these Treasure Chests to aid thee in thy quest.'",
                    "'Then speak with the guards, for they have much knowledge that may aid thee.'",
                    f"'May the light shine upon thee, {self.player.name}.'"
                )
            else:
                self.dialog_text = (
                    "'When thou art finished preparing for thy departure, please see me.\nI shall wait.'",
                )
        else:
            self.dialog_text = (
                f"'I am greatly pleased that thou hast returned, {self.player.name}.'",
                f"'Before reaching thy next level of experience thou must gain {self.player.points_to_next_level} Points.'"
            )

    def say_dialog(self):
        for line in self.dialog_text:
            print_with_beep_sfx(line)
        if not self.throne_room_door_locked and not self.is_initial_dialog:
            self.prompt_for_save()

    def prompt_for_save(self):
        deeds = input("'Will thou tell me now of thy deeds so they won't be forgotten?'").lower().strip()
        if deeds == "y":
            print_with_beep_sfx("'Thy deeds have been recorded on the Imperial Scrolls of Honor.'")
        continuing = input("'Dost thou wish to continue thy quest?'").lower().strip()
        if continuing == "y":
            print_with_beep_sfx(f"'Goodbye now, {self.player.name}.\n'Take care and tempt not the Fates.'")
        elif continuing == "N":
            print_with_beep_sfx("'Rest then for awhile.'")
