"""HeroDeath: the hero's death and his return to King Lorik, which used to live on Game.

Once a frame (Game's post-move checks), handle_death looks for a hero at 0 HP, whether a battle, a swamp or a force
field brought him there: NES PlayerHasDied's death music and "Thou art dead.", then DeathText's half of the gold and
StartAtThroneRoom's return to the throne room (set_post_death_attributes).
"""
from typing import TYPE_CHECKING

from pygame import display

from src.common import A_OR_START_KEYS
from src.direction import Direction
from src.maps import map_lookup
from src.waiting import clear_events_keeping_quit

if TYPE_CHECKING:
    from src.game import Game  # src.game imports this module


class HeroDeath:
    """The hero dying, on the map or in a battle, and starting again in the throne room."""

    def __init__(self, game: 'Game') -> None:
        self.game = game

    def handle_death(self) -> None:
        game = self.game
        player = game.player
        if player.current_hp <= 0:
            player.current_hp = 0
            player.is_dead = True
            game.auto_grind.hero_died()
            game.load_window_palette()  # 0 HP is always low
            if game.battle_ctrl.launch_battle and not game.game_state.config["NO_BATTLES"]:
                # NES PlayerHasDied (LED9C): the battle screen stays as the deathblow left it. The command window isn't
                # drawn again: every command removed it (PlyrFight LE5FE and the others), and the death music and
                # "Thou art dead." follow in the dialog window.
                game.battle_ctrl.launch_battle = False
                display.flip()
            else:
                game.drawer.draw_all_tiles_in_current_map(game.current_map, game.drawer.background)
                display.flip()
            game.game_state.enable_movement = False
            # NES PlayerHasDied / InitDeathSequence: MSC_DEATH, then WaitForMusicEnd. It plays once, and "Thou art
            # dead." only comes once it has finished.
            game.music_player.play_until_end(game.directories.death_music, game.game_state.config)
            clear_events_keeping_quit()  # keys pressed during the death music are dropped (a window close isn't)

            # NES DeathText: the game then loops until JoypadBtns AND #$09, A or START (held or not)
            game.cmd_menu.show_text_in_dialog_box(game._("Thou art dead."), disable_sound=True,
                                                  advance_keys=A_OR_START_KEYS)
            self.set_post_death_attributes()
        else:
            player.is_dead = False

    def set_post_death_attributes(self) -> None:
        game = self.game
        player = game.player
        # NES DeathText: dying clears F_GOT_GWAELIN, so Gwaelin is back in the Swamp Cave (F_RTN_GWAELIN is untouched)
        game.story_flags.carrying_gwaelin = False
        game.repel_timer = 0  # NES StartAtThroneRoom (SetStartPos) clears RepelTimer
        player.gold = player.gold // 2
        # NES StartAtThroneRoom sets HP before MapChngNoSound fades the throne room in, so the fade's palette load
        # (ChkLowHPPal) sees the new HP: a cursed hero comes back with 1 HP, which is always low, so the king's words
        # are in red windows; anyone else comes back with full HP and white windows. DeathText sets ThisStrtStat to
        # STRT_FULL_HP, so StartAtThroneRoom (LCB78-LCB87) fills MP as well as HP; for a cursed hero it sets HP to 1
        # and skips that step (LCB71-LCB75), so MP stays as it was.
        if player.is_cursed:
            player.current_hp = 1
        else:
            player.current_hp = player.max_hp
            player.current_mp = player.max_mp
        game.load_window_palette()
        # NES DeathText -> StartAtThroneRoom (LEDDE): the screen cuts to black and the throne room fades in once
        next_map = map_lookup['TantegelThroneRoom'](game.config)
        game.change_map(next_map, fade_out_first=False)
        player.is_dead = False
        if player.is_cursed:
            # NES DeathText: the king then says "Thou hast failed and thou art cursed." and ChangeMaps puts the player
            # outside the castle, facing down.
            game.cmd_menu.show_text_in_dialog_box(
                (game._("Thou hast failed and thou art cursed."), game._("Leave at once!")), add_quotes=True,
                skip_text=game.skip_text)
            game.leave_tantegel(direction=Direction.DOWN.value)
            return
        game.game_state.is_post_death_dialog = True
