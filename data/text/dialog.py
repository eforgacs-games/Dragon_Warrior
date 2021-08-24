class Dialog:
    def __init__(self, player_name):
        self.player_name = player_name
        self.dialog_lookup = {
            'KING_LORIK': self.king_lorik_spoken_to_dialog,
            'RIGHT_FACE_GUARD': self.right_face_guard_tantegel_throne_room,
            'LEFT_FACE_GUARD': self.left_face_guard_tantegel_throne_room
        }

    def king_lorik_initial_dialog(self):
        input("'Descendant of Erdrick, listen now to my words.'")
        input("'It is told that in ages past Erdrick fought demons with a Ball of Light.'")
        input("'Then came the Dragonlord who stole the precious globe and hid it in the darkness.'")
        input("'Now, <player name>, thou must help us recover the Ball of Light and restore peace to our land.'")
        input("'The Dragonlord must be defeated.'")
        input("'Take now whatever thou may find in these Treasure Chests to aid thee in thy quest.'")
        input("'Then speak with the guards, for they have much knowledge that may aid thee.'")
        input(f"'May the light shine upon thee, {self.player_name}.'")

    def king_lorik_spoken_to_dialog(self):
        points_remaining_to_next_level = 0
        input(f"'I am greatly pleased that thou hast returned, {self.player_name}.'")
        input(f"'Before reaching thy next level of experience thou must gain {points_remaining_to_next_level} Points.'")
        deeds = input("'Will thou tell me now of thy deeds so they won't be forgotten?'")
        if deeds == "Y":
            print("'Thy deeds have been recorded on the Imperial Scrolls of Honor.'")
        continuing = input("'Dost thou wish to continue thy quest?'")
        if continuing == "Y":
            f"'Goodbye now, {self.player_name}.\nTake care and tempt not the Fates.'"
        elif continuing == "N":
            "'Rest then for awhile.'"

    def right_face_guard_tantegel_throne_room(self):
        input("'East of this castle is a town where armor, weapons, and many other items may be purchased.'")
        input(f"'Return to the Inn for a rest if thou art wounded in battle, {self.player_name}.'")
        input("'Sleep heals all.'")

    def left_face_guard_tantegel_throne_room(self):
        input("'If thou hast collected all the Treasure Chests, a key will be found.'")
        input("'Once used, the key will disappear, but the door will be open and thou may pass through.'")
