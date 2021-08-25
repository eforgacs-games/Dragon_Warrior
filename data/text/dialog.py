from src.common import print_with_beep_sfx


class Dialog:
    def __init__(self, player):
        self.player = player
        self.dialog_lookup = {
            'KING_LORIK': self.king_lorik_dialog,
            'RIGHT_FACE_GUARD': self.right_face_guard_tantegel_throne_room,
            'LEFT_FACE_GUARD': self.left_face_guard_tantegel_throne_room,
            'ROAMING_GUARD': self.roaming_guard_tantegel_throne_room
        }
        self.initial_dialog = False
        self.throne_room_door_locked = True

    def king_lorik_dialog(self):
        if self.initial_dialog:
            print_with_beep_sfx("'Descendant of Erdrick, listen now to my words.'")
            print_with_beep_sfx("'It is told that in ages past Erdrick fought demons with a Ball of Light.'")
            print_with_beep_sfx("'Then came the Dragonlord who stole the precious globe and hid it in the darkness.'")
            print_with_beep_sfx(f"'Now, {self.player.name}, thou must help us recover the Ball of Light and restore peace to our land.'")
            print_with_beep_sfx("'The Dragonlord must be defeated.'")
            print_with_beep_sfx("'Take now whatever thou may find in these Treasure Chests to aid thee in thy quest.'")
            print_with_beep_sfx("'Then speak with the guards, for they have much knowledge that may aid thee.'")
            print_with_beep_sfx(f"'May the light shine upon thee, {self.player.name}.'")
        if self.throne_room_door_locked:
            print_with_beep_sfx("'When thou art finished preparing for thy departure, please see me.\nI shall wait.'")
        else:
            print_with_beep_sfx(f"'I am greatly pleased that thou hast returned, {self.player.name}.'")
            print_with_beep_sfx(f"'Before reaching thy next level of experience thou must gain {self.player.points_to_next_level} Points.'")
            deeds = input("'Will thou tell me now of thy deeds so they won't be forgotten?'")
            if deeds == "Y":
                print_with_beep_sfx("'Thy deeds have been recorded on the Imperial Scrolls of Honor.'")
            continuing = input("'Dost thou wish to continue thy quest?'")
            if continuing == "Y":
                print_with_beep_sfx(f"'Goodbye now, {self.player.name}.\n'Take care and tempt not the Fates.'")
            elif continuing == "N":
                print_with_beep_sfx("'Rest then for awhile.'")

    def right_face_guard_tantegel_throne_room(self):
        print_with_beep_sfx("'East of this castle is a town where armor, weapons, and many other items may be purchased.'")
        print_with_beep_sfx(f"'Return to the Inn for a rest if thou art wounded in battle, {self.player.name}.'")
        print_with_beep_sfx("'Sleep heals all.'")

    def roaming_guard_tantegel_throne_room(self):
        # TODO: Fix roaming guard talk function. Only able to talk to the roaming guard's initial position.
        know_about_princess = input("'Dost thou know about Princess Gwaelin?'")
        if not know_about_princess:
            print_with_beep_sfx("'Half a year now hath passed since the Princess was kidnapped by the enemy.'")
            print_with_beep_sfx("'Never does the King speak of it, but he must be suffering much.'")
        else:
            print_with_beep_sfx(f"'{self.player.name}, please save the Princess.'")

    @staticmethod
    def left_face_guard_tantegel_throne_room():
        print_with_beep_sfx("'If thou hast collected all the Treasure Chests, a key will be found.'")
        print_with_beep_sfx("'Once used, the key will disappear, but the door will be open and thou may pass through.'")
