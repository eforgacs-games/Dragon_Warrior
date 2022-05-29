from data.text.down_face_guard_dialog import DownFaceGuardDialog
from data.text.king_lorik_dialog import KingLorikDialog
from data.text.left_face_guard_dialog import LeftFaceGuardDialog
from data.text.man_dialog import ManDialog
from data.text.merchant_dialog import MerchantDialog
from data.text.right_face_guard_dialog import RightFaceGuardDialog
from data.text.roaming_guard_dialog import RoamingGuardDialog
from data.text.up_face_guard_dialog import UpFaceGuardDialog
from data.text.wise_man_dialog import WiseManDialog
from data.text.woman_dialog import WomanDialog


class DialogLookup:
    # TODO(ELF): This should be totally redone. Maybe a better lookup table would be:
    example_lookup_table = {'TantegelCourtyard': {'MAN_2': ("There was a time when Brecconary was a paradise.\n"
                                                            "Then the Dragonlord's minions came.",
                                                            )}}

    def __init__(self, player, map_name, screen):
        self.lookup_table = {'KING_LORIK': KingLorikDialog(player, map_name, screen,
                                                           throne_room_door_locked=True),
                             'UP_FACE_GUARD': UpFaceGuardDialog(player, map_name, screen),
                             'DOWN_FACE_GUARD': DownFaceGuardDialog(player, map_name, screen),
                             'RIGHT_FACE_GUARD': RightFaceGuardDialog(player, map_name, screen),
                             'RIGHT_FACE_GUARD_2': RightFaceGuardDialog(player, map_name, screen),
                             'LEFT_FACE_GUARD': LeftFaceGuardDialog(player, map_name, screen),
                             'ROAMING_GUARD': RoamingGuardDialog(player, map_name, screen),
                             'MERCHANT': MerchantDialog(player, map_name, screen),
                             'MAN': ManDialog(player, map_name, screen),
                             'MAN_2': ManDialog(player, map_name, screen),
                             'WOMAN': WomanDialog(player, map_name, screen),
                             'WOMAN_2': WomanDialog(player, map_name, screen),
                             'WISE_MAN': WiseManDialog(player, map_name, screen)}

        for character_identifier, character_dialog_object in self.lookup_table.items():
            character_dialog_object.dialog_character = character_identifier
