"""
Ending — everything that happens after the Dragonlord's final form is defeated, per the NES.

1. Battle.enemy_defeated hands over to final_boss_defeated (NES NotDL1Defeated): the Ball of Light is found, the
   F_DGNLRD_DEAD story flag is set and the hero is put on the overworld outside the Dragonlord's castle.
2. The hero walks (or flies) back to Tantegel. With the flag set there are no random fights or tile damage, every NPC
   has victory dialog (npc_dialog) and King Lorik waits on the castle's ground floor (TantegelCourtyard). Gwaelin, if
   she's still in the Swamp Cave, can be rescued and carried to him (has_victory_dialog).
3. Stepping in front of him starts the ending (check_for_end_game_trigger, NES CheckForTriggers / EndGameTriggered),
   which plays out differently depending on Princess Gwaelin, then rolls the credits (NES DoEndCredits) and hangs on
   THE END until the game is closed, as the NES does until it's reset.

The story flags themselves live in src/story_flags.py.
"""

import random
import sys

from pygame import QUIT, display, event, quit as pygame_quit, time

from data.text.dialog import confirmation_prompt
from src.common import BLACK, WHITE
from src.constants import DRAGONLORD_DEFEATED_DESTINATION, ENDING_GWAELIN_BESIDE_KING, ENDING_GWAELIN_STAIRS, \
    ENDING_TRIGGER_COORDINATES
from src.direction import Direction
from src.maps import map_lookup
from src.maps_functions import get_center_point
from src.npcs import GWAELIN_RESCUE, SEARCHED_FOR_GWAELIN
from src.text import draw_text
from src.visual_effects import screen_fade
from src.waiting import game_ticks, wait_frames

NES_FPS = 60

# NES DoEndCredits (Bank01) moves on to the next credits screen after a number of "music timing events" in the end
# music (WaitForMusicEnd, $815E): the triangle part (TRIEndGame) has a no-op byte (MCTL_NO_OP, $FC) after every few
# notes, and an event is caught while one is waiting to be read, that is while the note before it plays. Once the note
# is over the sound engine skips the no-op itself and that event is gone. Each event as (the first frame it can be
# caught, the frame it's gone), counted from the start of the end music; worked out by playing the end music the way
# the sound engine does (reference/reference_utility_scripts/end_music_timing.py). The music ends at frame 7237.
END_MUSIC_TIMING_EVENTS = (
    (683, 753), (818, 851), (949, 982), (1080, 1113), (1211, 1244), (1342, 1374), (1473, 1505), (1604, 1636),
    (1734, 1767), (1865, 1882), (1996, 2013), (2127, 2144), (2258, 2274), (2389, 2405), (2520, 2536), (2651, 2684),
    (2782, 2814), (2913, 2945), (3044, 3076), (3174, 3207), (3305, 3338), (3436, 3469), (3567, 3600), (3698, 3731),
    (3829, 3862), (3960, 3993), (4091, 4107), (4222, 4238), (4353, 4369), (4484, 4500), (4614, 4631), (4745, 4762),
    (4876, 4909), (5007, 5040), (5138, 5171), (5269, 5302), (5400, 5433), (5531, 5564), (5662, 5694), (5793, 5825),
    (5924, 5956), (6054, 6087), (6185, 6218), (6316, 6349), (6447, 6480), (6577, 6593), (6697, 6712), (6813, 6843),
    (6945, 6963), (7120, 7137),
)

# NES DoClearPPU and RollCredits: between one screen's fade out and the next one's fade in, ClearPPU waits for two NMIs
# and RollCredits one more before DoPalFadeIn (a screen with a lot of text can fill the PPU buffer and add a frame).
CREDIT_SCREEN_LOAD_FRAMES = 3
# NES FinishCredits: THE END stays up 160 frames ($A0) before DoEndCredits returns and the game spinlocks.
THE_END_FRAMES = 160

# NES EndCreditDat (Bank01): one entry per screen, each line as (name table row, name table column, text) from its PPU
# address ($2000 + row * 32 + column). The Chun Soft and Enix logos and the large THE END are tiles, drawn as text here.
CREDITS = (
    ((7, 8, "CONGRATULATIONS"), (10, 7, "THOU HAST RESTORED"), (12, 6, "PEACE UNTO THE WORLD"),
     (15, 4, "BUT THERE ARE MANY ROADS"), (17, 9, "YET TO TRAVEL."), (20, 9, "MAY THE LIGHT"),
     (22, 8, "SHINE UPON THEE.")),
    ((12, 8, "DRAGON WARRIOR"), (15, 13, "STAFF")),
    ((12, 6, "SCENARIO WRITTEN BY"), (15, 11, "YUJI HORII")),
    ((12, 5, "CHARACTER DESIGNED BY"), (15, 9, "AKIRA TORIYAMA")),
    ((12, 7, "MUSIC COMPOSED BY"), (15, 8, "KOICHI SUGIYAMA")),
    ((9, 10, "PROGRAMED BY"), (13, 8, "KOICHI NAKAMURA"), (16, 10, "KOJI YOSHIDA"), (19, 7, "TAKENORI YAMAMORI")),
    ((12, 9, "CG DESIGNED BY"), (15, 9, "TAKASHI YASUNO")),
    ((12, 6, "SCENARIO ASSISTED BY"), (15, 8, "HIROSHI MIYAOKA")),
    ((10, 10, "ASSISTED BY"), (14, 10, "RIKA SUZUKI"), (17, 8, "TADASHI FUKUZAWA")),
    ((12, 7, "SPECIAL THANKS TO"), (15, 7, "KAZUHIKO TORISHIMA")),
    ((12, 10, "TRANSLATION"), (15, 13, "STAFF")),
    ((6, 6, "TRANSLATED BY"), (8, 8, "TOSHIKO WATSON"), (12, 6, "REVISED TEXT BY"), (14, 8, "SCOTT PELLAND"),
     (18, 6, "TECHNICAL SUPPORT BY"), (20, 8, "DOUG BAKER")),
    ((10, 8, "PROGRAMED BY"), (14, 10, "KENICHI MASUTA"), (17, 10, "MANABU YAMANA")),
    ((9, 5, "CG DESIGNED BY"), (12, 10, "SATOSHI FUDABA"), (16, 5, "SPECIAL THANKS TO"), (19, 10, "HOWARD PHILLIPS")),
    ((12, 10, "DIRECTED BY"), (15, 8, "KOICHI NAKAMURA")),
    ((12, 10, "PRODUCED BY"), (15, 9, "YUKINOBU CHIDA")),
    ((4, 5, "BASED ON DRAGON QUEST"), (8, 11, "COPYRIGHT"), (11, 3, "ARMOR PROJECT"), (11, 20, "1986 1989"),
     (14, 3, "BIRD STUDIO"), (14, 20, "1986 1989"), (17, 3, "KOICHI SUGIYAMA"), (17, 20, "1986 1989"),
     (20, 3, "CHUN SOFT"), (20, 20, "1986 1989"), (24, 9, "ENIX"), (24, 16, "1986 1989")),
    ((16, 14, "ENIX"),),
    ((13, 12, "THE END"),),
)


def credit_screen_music_events(screen_index: int) -> int:
    """NES DoEndCredits: how many music timing events each credits screen stays up for (EndCreditCount checks)."""
    if screen_index == 0:
        return 8
    if screen_index == 1:
        return 2
    if screen_index in (2, 3, 4):
        return 3
    if screen_index <= 13:
        return 2
    return 3


class EndMusicTimingEvents:
    """NES WaitForMusicEnd during the credits: waits for the end music's timing events (END_MUSIC_TIMING_EVENTS), going
    by the time since the music started. An event that went by while the credits weren't waiting for one is gone, and
    one that is still waiting to be read when the wait starts is caught at once."""

    def __init__(self, config):
        self.config = config
        self.music_started = game_ticks()
        self.events = list(END_MUSIC_TIMING_EVENTS)

    def frames_since_music_started(self) -> float:
        return (game_ticks() - self.music_started) * NES_FPS / 1000

    def wait(self, count: int) -> None:
        for _ in range(count):
            now = self.frames_since_music_started()
            while self.events and self.events[0][1] <= now:
                self.events.pop(0)  # its note is over: skipped by the sound engine
            if not self.events:
                return  # the music is over (the NES would wait forever)
            first_frame, _ = self.events.pop(0)
            wait_frames(max(0.0, first_frame - now), self.config, NES_FPS)


class Ending:
    def __init__(self, game):
        self.game = game
        self.started = False

    @property
    def player(self):
        return self.game.player

    @property
    def config(self):
        return self.game.config

    @property
    def _(self):
        return self.game._

    def wait_frames(self, frames: int) -> None:
        wait_frames(frames, self.config, NES_FPS)

    def quote(self, text: str) -> str:
        """Quote marks the way CommandMenu adds them, for lines that are only partly quoted."""
        if self.config['LANGUAGE'] == 'Korean' and not text.isascii():
            return f"'{text}'"
        return f"`{text}’"

    def say(self, line: str, quoted: bool = True, wait_for_key: bool = True, hide_arrow: bool = False) -> None:
        """One message. It waits with the arrow for A or B (TXT_WAIT, DoWait), or with hide_arrow for any button, the
        way the NES waits once a message ends (TXT_END1, then WaitForBtnRelease)."""
        self.game.cmd_menu.show_line_in_dialog_box(line, add_quotes=quoted, skip_text=not wait_for_key,
                                                   hide_arrow=hide_arrow)

    def redraw(self) -> None:
        game = self.game
        game.drawer.draw_all(game, game.game_state.enable_animate)
        display.flip()

    # ------------------------------------------------------------------ #
    #  1. Defeating the Dragonlord                                         #
    # ------------------------------------------------------------------ #

    def final_boss_defeated(self) -> None:
        """NES NotDL1Defeated (Bank03): after the usual "Thou hast done well in defeating the Dragonlord." and the
        victory music, the boss is erased, the Ball of Light is found (it's text only; the NES has no inventory item for
        it) and F_DGNLRD_DEAD is set. HP and MP are maxed out and ChangeMaps puts the hero outside the Dragonlord's
        castle facing down. No experience or gold is given."""
        _ = self._
        # TextBlock18, entry 10: TXT_WAIT after the first two lines (A or B), TXT_END1 after the last, and then LE9F8
        # WaitForBtnRelease (any button)
        self.say(_("Thou hast found the Ball of Light."), quoted=False)
        self.say(_("Radiance streams forth as thy hands touch the object and hold it aloft."), quoted=False)
        self.say(_("Across the land spreads the brilliance until all shadows are banished and peace is restored."),
                 quoted=False, hide_arrow=True)
        self.game.story_flags.dragonlord_defeated = True
        self.player.restore_hp()
        self.player.restore_mp()
        map_name, coordinates = DRAGONLORD_DEFEATED_DESTINATION
        # ChangeMaps -> SetPlyrPixelLoc -> MapChngWithSound: the stairs sound, once the screen has faded out
        self.game.change_map(map_lookup[map_name](self.config), destination_coordinates=coordinates,
                             direction=Direction.DOWN.value, stairs_sound=True)

    # ------------------------------------------------------------------ #
    #  2. The world after the Dragonlord                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def has_victory_dialog(dialog_character: str, current_map) -> bool:
        """Whether npc_dialog replaces this character's dialog once the Dragonlord is dead.

        NES CheckTalk: LD134 runs only for the NPC tables of maps 4 to 14 (ValidateNPC), which hold every NPC with
        dialog (shops, inns, the King, the old men and so on). Gwaelin in the Swamp Cave (MAP_SWAMPCAVE, $15) isn't an
        NPC there but a map block: DoTalkResults checks for BLK_PRINCESS before any NPC (and before LD134) and goes
        straight to DoGwaelinRescue, and GetBaseBlockID only turns that block into brick once F_DONE_GWAELIN is set,
        whatever F_DGNLRD_DEAD says. So she can still be rescued after the Dragonlord's defeat, and then carried to
        King Lorik for the ending (ChkCarryGwaelin)."""
        npc = current_map.npc(dialog_character)
        return npc is None or npc.dialog != GWAELIN_RESCUE

    def npc_dialog(self, dialog_character: str, current_map) -> str:
        """NES LD134: every NPC's dialog once the Dragonlord is dead (see has_victory_dialog for who's exempt)."""
        _ = self._
        if current_map.identifier == 'TantegelCourtyard':
            return _("Come now, King Lorik awaits.")
        npc = current_map.npc(dialog_character)
        if npc is not None and npc.dialog == SEARCHED_FOR_GWAELIN:
            # NES TantEndDialog: the guard in Brecconary who searched for Gwaelin has nothing more to say
            return "...."
        # NES RandEndDialog: the low bit of a random number picks one of two lines
        if random.randint(0, 1):
            return _("Hurrah!\nHurrah!\nLong live {}!").format(self.player.name)
        return _("Thou hast brought us peace, again.")

    # ------------------------------------------------------------------ #
    #  3. King Lorik's ending scene                                        #
    # ------------------------------------------------------------------ #

    def check_for_end_game_trigger(self) -> bool:
        """NES CheckForTriggers: with the Dragonlord dead, standing just below King Lorik on Tantegel's ground floor
        starts the ending. Returns whether it ran."""
        if self.started or not self.game.story_flags.dragonlord_defeated:
            return False
        if self.game.current_map.identifier != 'TantegelCourtyard' or self.player.is_moving:
            return False
        if (self.player.row, self.player.column) not in ENDING_TRIGGER_COORDINATES:
            return False
        self.started = True
        self.king_lorik_scene()
        self.roll_credits()
        self.wait_for_reset()
        return True

    def king_lorik_scene(self) -> None:
        """NES EndGameTriggered (Bank03)."""
        _ = self._
        name = self.player.name
        self.game.music_player.stop_music()
        self.game.game_state.pause_all_movement()
        self.game.cmd_menu.window_drop_down_effect(2, 9, 12, 5)
        # TextBlock18, entry 11
        self.say(_("The legends have proven true."))
        self.say(_("Thou art indeed of the line of Erdrick."))
        self.say(_("It is thy right to rule over this land."))
        self.say(_("Will thou take my place?"))
        self.say(_("{} thought carefully before answering.").format(name), quoted=False)
        self.say(self.quote(_("I cannot,")) + "\n" + _("said {}.").format(name), quoted=False)
        self.say(_("If ever I am to rule a country, it must be a land that I myself find."))

        if self.game.story_flags.gwaelin_returned:
            # NES: Gwaelin, already returned (F_RTN_GWAELIN), comes down the throne room stairs and walks to the king
            gwaelin = self.place_gwaelin(*ENDING_GWAELIN_STAIRS)
            self.gwaelin_says_wait()
            self.walk_gwaelin_to_king(gwaelin)
            self.gwaelin_joins()
        elif self.game.story_flags.carrying_gwaelin:
            # NES ChkCarryGwaelin: the hero sets her down beside the king
            self.game.story_flags.carrying_gwaelin = False
            self.reset_hero_images()
            self.place_gwaelin(*ENDING_GWAELIN_BESIDE_KING)
            self.gwaelin_says_wait()
            self.gwaelin_joins()

        self.tale_end()

    def gwaelin_says_wait(self) -> None:
        # TextBlock18, entry 12. The NES doesn't wait for a button here; this waits so the line can be read.
        self.say(self._("Gwaelin said:") + "\n" + self.quote(self._("Please, wait.")), quoted=False)

    def place_gwaelin(self, row: int, column: int):
        current_map = self.game.current_map
        current_map.center_pt = get_center_point(column, row, self.game.tile_size)
        current_map.map_npc('PRINCESS_GWAELIN', Direction.DOWN.value, 'BRICK',
                            current_map.character_key['PRINCESS_GWAELIN']['path'], False, (row, column), False)
        self.redraw()
        return current_map.characters['PRINCESS_GWAELIN']['character']

    def walk_gwaelin_to_king(self, gwaelin) -> None:
        """NES GwaelinMoveLoop: she moves right one pixel every two frames until she's beside the king."""
        tile_size = self.game.tile_size
        row, target_column = ENDING_GWAELIN_BESIDE_KING
        while gwaelin.column < target_column:
            for _ in range(16):  # 16 NES pixels to a tile
                gwaelin.rect.x += tile_size // 16
                self.redraw()
                self.wait_frames(2)
            gwaelin.column += 1
            gwaelin.rect.center = get_center_point(gwaelin.column, row, tile_size)
        self.game.current_map.characters['PRINCESS_GWAELIN']['coordinates'] = (row, target_column)
        self.redraw()

    def gwaelin_joins(self) -> None:
        # NES GwaelinJoin: TextBlock18, entry 13
        self.say(self._("I wish to go with thee on thy journey."))
        self.ask_to_travel_together()

    def ask_to_travel_together(self) -> None:
        # NES GwaelinDecline: TextBlock18, entry 14, asked until the answer is yes
        confirmation_prompt(self.game.cmd_menu, self._("May I travel as thy companion?"),
                            yes_path_function=self.gwaelin_accepted,
                            no_path_function=self.gwaelin_refused,
                            config=self.config, show_arrow=self.game.show_arrow, color=self.game.color)

    def gwaelin_refused(self) -> None:
        self.say(self._("But thou must."))
        self.ask_to_travel_together()

    def gwaelin_accepted(self) -> None:
        """NES GwaelinAccept: she's taken off the map and drawn in the hero's arms."""
        self.say(self._("I'm so happy!"))
        current_map = self.game.current_map
        gwaelin = current_map.characters.pop('PRINCESS_GWAELIN')['character']
        if gwaelin in current_map.fixed_characters:
            current_map.fixed_characters.remove(gwaelin)
        self.game.story_flags.carrying_gwaelin = True
        self.game.set_player_images_by_equipment()
        self.redraw()

    def reset_hero_images(self) -> None:
        # set_player_images_by_equipment doesn't cover an unarmed hero without a shield
        self.player.images = self.game.current_map.scale_sprite_sheet(self.game.directories.UNARMED_HERO_PATH)
        self.player.set_images(self.player.images)
        self.game.set_player_images_by_equipment()

    def tale_end(self) -> None:
        """NES TaleEnd: TextBlock19, entry 2, then the hero looks right and down before the trumpets sound."""
        self.say(self._("And thus the tale comes to an end....") + "\n" +
                 self._("unless the dragons return again."), quoted=False, wait_for_key=False)
        self.wait_frames(120)
        self.player.direction_value = Direction.RIGHT.value
        self.redraw()
        self.wait_frames(30)
        self.player.direction_value = Direction.DOWN.value
        self.redraw()
        self.wait_frames(30)

    # ------------------------------------------------------------------ #
    #  4. Credits                                                          #
    # ------------------------------------------------------------------ #

    def roll_credits(self) -> None:
        """NES DoEndCredits (Bank01): the end music starts, and at its first timing event the king's scene fades out
        (LoadCreditsPals' PalFadeOut). Then each screen fades in, stays for some of the music's timing events
        (credit_screen_music_events) and fades out. The last one, THE END, stays up."""
        self.game.music_player.load_and_play_music(self.game.directories.ending_music, loop=0)
        music_events = EndMusicTimingEvents(self.config)
        music_events.wait(1)
        screen_fade(fade_out=True, screen=self.game.screen, config=self.config)  # LoadCreditsPals ($AA62)
        for screen_index, credit_screen in enumerate(CREDITS):
            self.wait_frames(CREDIT_SCREEN_LOAD_FRAMES)
            self.show_credit_screen(credit_screen)
            if screen_index == len(CREDITS) - 1:
                self.wait_frames(THE_END_FRAMES)
                return
            music_events.wait(credit_screen_music_events(screen_index))
            screen_fade(fade_out=True, screen=self.game.screen, config=self.config)  # DoPalFadeOut ($AA43)

    def show_credit_screen(self, credit_screen) -> None:
        screen = self.game.screen
        nes_tile = self.game.tile_size // 2
        screen.fill(BLACK)
        for row, column, text in credit_screen:
            draw_text(text, column * nes_tile, (row + 0.5) * nes_tile, screen, self.config, color=WHITE,
                      text_wrap_length=32, letter_by_letter=False, disable_sound=True)
        screen_fade(fade_out=False, screen=screen, config=self.config)  # DoPalFadeIn ($AA3D)

    def wait_for_reset(self) -> None:
        """NES Spinlock1: after the credits the game does nothing more until it's reset; here, until it's closed."""
        while True:
            for current_event in event.get():
                if current_event.type == QUIT:
                    pygame_quit()
                    sys.exit()
            time.wait(16)
