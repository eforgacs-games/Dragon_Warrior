class DialogLookup:
    def __init__(self, player):
        self.lookup_table = {
            'TantegelThroneRoom': {
                'KING_LORIK': {'dialog': (
                    "Descendant of Erdrick, listen now to my words.",
                    "It is told that in ages past Erdrick fought demons with a Ball of Light.",
                    "Then came the Dragonlord who stole the precious globe and hid it in the darkness.",
                    f"Now, {player.name}, thou must help us recover the Ball of Light and restore peace to our land.",
                    "The Dragonlord must be defeated.",
                    "Take now whatever thou may find in these Treasure Chests to aid thee in thy quest.",
                    "Then speak with the guards, for they have much knowledge that may aid thee.",
                    f"May the light shine upon thee, {player.name}."
                ), 'post_initial_dialog': (
                    "When thou art finished preparing for thy departure, please see me.\n"
                    "I shall wait.",
                ), 'returned_dialog': (
                    f"I am greatly pleased that thou hast returned, {player.name}.",
                    f"Before reaching thy next level of experience thou must gain {player.points_to_next_level} Points."
                ),
                    'is_initial_dialog': True},
                'UP_FACE_GUARD': {'dialog': (
                    "If thou art planning to take a rest, first see King Lorik.",)},
                'DOWN_FACE_GUARD': {'dialog': (
                    "King Lorik will record thy deeds in his Imperial Scroll so thou may return to thy quest later.",)},
                'RIGHT_FACE_GUARD': {'dialog': (
                    "East of this castle is a town where armor, weapons, and many other items may be purchased.",
                    f"Return to the Inn for a rest if thou art wounded in battle, {player.name}.",
                    "Sleep heals all."
                )},
                'LEFT_FACE_GUARD': {'dialog': (
                    "If thou hast collected all the Treasure Chests, a key will be found.",
                    "Once used, the key will disappear, but the door will be open and thou may pass through."
                )},
                'ROAMING_GUARD': {'dialog':
                    (
                        # know_about_princess = input("Dost thou know about Princess Gwaelin?'")
                        # if not know_about_princess:
                        #     print_with_beep_sfx("Half a year now hath passed since the Princess was kidnapped by the enemy.")
                        #     print_with_beep_sfx("Never does the King speak of it, but he must be suffering much.")
                        # else:
                        #     print_with_beep_sfx(f"{self.player.name}, please save the Princess.")
                        # TODO: Reset this later to use input(), but just for testing it out we can leave it this way for now.
                        "Dost thou know about Princess Gwaelin?",
                        "Half a year now hath passed since the Princess was kidnapped by the enemy.",
                        "Never does the King speak of it, but he must be suffering much."

                    )}},
            'TantegelCourtyard': {
                'MERCHANT': {'dialog': ("Magic keys! They will unlock any door. \nDost thou wish to purchase one for 85 GOLD?",)},
                'MERCHANT_2': {'dialog': ("We are merchants who have traveled much in this land. "
                                          "Many of our colleagues have been killed by servants of the Dragonlord.",)},
                'MERCHANT_3': {'dialog': ("Rumor has it that entire towns have been destroyed by the Dragonlord's servants.",)},
                'MAN': {'dialog': ("To become strong enough to face future trials thou must first battle many foes.",)},
                'MAN_2': {'dialog': (
                    "There was a time when Brecconary was a paradise.\nThen the Dragonlord's minions came.",)},
                'WOMAN': {'dialog': ("When the sun and rain meet, a Rainbow Bridge shall appear.", "It's a legend.")},
                'WOMAN_2': {'dialog': ("Where oh where can I find Princess Gwaelin?",)},
                'RIGHT_FACE_GUARD': {'dialog': ("Where oh where can I find Princess Gwaelin?",)},
                'LEFT_FACE_GUARD': {'dialog': ("Welcome to Tantegel Castle.",)},
                'RIGHT_FACE_GUARD_2': {'dialog': ("Welcome to Tantegel Castle.",)},
                'WISE_MAN': {'dialog': (
                    f"{player.name}'s coming was foretold by legend. "
                    f"May the light shine upon this brave warrior.",)}},
            'TantegelCellar': {'WISE_MAN': {'dialog': ("I have been waiting long for one such as thee.", "Take the Treasure Chest.")}},
            'Brecconary': {
                'WOMAN': {'dialog': ("Welcome! \nEnter the shop and speak to its keeper across the desk.",)},
            },
            'Garinham': {
                'MERCHANT': {'dialog': (
                    "Welcome.\n"
                    "We deal in tools.\n"
                    "What can I do for thee?",
                )},
                'MERCHANT_2': {'dialog': (
                    "Welcome to the traveler's Inn.\n"
                    "Room and board is 25 GOLD per night.\n"
                    "Dost thou want a room?",
                )},
                'MERCHANT_3': {'dialog': (
                    "We deal in weapons and armor.\n"
                    "Dost thou wish to buy anything today?",
                )},
                'WISE_MAN': {'dialog': ("Many believe that Princess Gwaelin is hidden away in a cave.",)}

            }
        }

        for map_dict in self.lookup_table.values():
            for character_identifier, character_dict in map_dict.items():
                character_dict['dialog_character'] = character_identifier
