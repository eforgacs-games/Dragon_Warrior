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

    def __init__(self, player, map_name, dialog_character, screen):
        self.lookup_table = {'KING_LORIK': KingLorikDialog(player, throne_room_door_locked=True, screen=screen),
                             'UP_FACE_GUARD': UpFaceGuardDialog(player, map_name, dialog_character, screen),
                             'DOWN_FACE_GUARD': DownFaceGuardDialog(player, map_name, dialog_character, screen),
                             'RIGHT_FACE_GUARD': RightFaceGuardDialog(player, map_name, dialog_character, screen),
                             'LEFT_FACE_GUARD': LeftFaceGuardDialog(player, map_name, screen),
                             'ROAMING_GUARD': RoamingGuardDialog(player, map_name, screen),
                             'MERCHANT': MerchantDialog(player, map_name, dialog_character, screen),
                             'MAN': ManDialog(player, map_name, screen),
                             'WOMAN': WomanDialog(player, map_name),
                             'WISE_MAN': WiseManDialog(player, map_name)}
