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


class DialogLookupTable:

    def __init__(self, player, map_name, dialog_character):
        self.dialog_lookup = {'KING_LORIK': KingLorikDialog(player,
                                                            is_initial_dialog=False,
                                                            throne_room_door_locked=True),
                              'UP_FACE_GUARD': UpFaceGuardDialog(player, map_name, dialog_character),
                              'DOWN_FACE_GUARD': DownFaceGuardDialog(player, map_name, dialog_character),
                              'RIGHT_FACE_GUARD': RightFaceGuardDialog(player, map_name, dialog_character),
                              'LEFT_FACE_GUARD': LeftFaceGuardDialog(player, map_name),
                              'ROAMING_GUARD': RoamingGuardDialog(player, map_name),
                              'MERCHANT': MerchantDialog(player, map_name, dialog_character),
                              'MAN': ManDialog(player, map_name),
                              'WOMAN': WomanDialog(player, map_name),
                              'WISE_MAN': WiseManDialog(player, map_name)}
