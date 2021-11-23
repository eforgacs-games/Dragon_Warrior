from data.text.king_lorik_dialog import KingLorikDialog
from data.text.left_face_guard_dialog import LeftFaceGuardDialog
from data.text.man_dialog import ManDialog
from data.text.merchant_dialog import MerchantDialog
from data.text.right_face_guard_dialog import RightFaceGuardDialog
from data.text.roaming_guard_dialog import RoamingGuardDialog
from data.text.wise_man_dialog import WiseManDialog
from data.text.woman_dialog import WomanDialog


class DialogLookupTable:
    def __init__(self, player, map_name):
        self.dialog_lookup = {'KING_LORIK': KingLorikDialog(player,
                                                            is_initial_dialog=False,
                                                            throne_room_door_locked=True),
                              'RIGHT_FACE_GUARD': RightFaceGuardDialog(player, map_name),
                              'LEFT_FACE_GUARD': LeftFaceGuardDialog(player, map_name),
                              'ROAMING_GUARD': RoamingGuardDialog(player, map_name),
                              'MERCHANT': MerchantDialog(player, map_name),
                              'MAN': ManDialog(player, map_name),
                              'WOMAN': WomanDialog(player, map_name),
                              'WISE_MAN': WiseManDialog(player, map_name)}
