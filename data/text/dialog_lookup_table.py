from data.text.king_lorik_dialog import KingLorikDialog
from data.text.left_face_guard_dialog import LeftFaceGuardDialog
from data.text.right_face_guard_dialog import RightFaceGuardDialog
from data.text.roaming_guard_dialog import RoamingGuardDialog


class DialogLookupTable:
    def __init__(self, player):
        self.dialog_lookup = {
            'TantegelThroneRoom': {'KING_LORIK': KingLorikDialog(player,
                                                                 is_initial_dialog=False,
                                                                 throne_room_door_locked=True),
                                   'RIGHT_FACE_GUARD': RightFaceGuardDialog(player, 'TantegelThroneRoom'),
                                   'LEFT_FACE_GUARD': LeftFaceGuardDialog(player, 'TantegelThroneRoom'),
                                   'ROAMING_GUARD': RoamingGuardDialog(player, 'TantegelThroneRoom'),
                                   },
            'TantegelCourtyard': {},
            'Alefgard': {},
            'Brecconary': {}

        }
