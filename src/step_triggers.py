"""StepTriggers: what every finished step on the map leads to, which used to live on Game.

The hero's step is counted (MovementController calls count_step when it finishes), and while the Dragonlord is alive,
NES MovementUpdates runs for it: the armor's healing, the low HP palette, Tantegel's curse and the guardians. The
repel and radiant timers tick once the step's fight roll is done (tick_repel_timer_after_step, from Game.map_frame).
The step's damage and fight roll (NES CheckBlockDmg) are src/field_encounters.py and src/hero_damage.py.

The step counts and timers stay on the Game (save states keep them, src/save_state.py GAME_VALUES); StepTriggers
reads and changes them there.
"""
from typing import TYPE_CHECKING

from src.constants import TANTEGEL_CURSED_ROW
from src.game_events import StepTaken
from src.guardians import GOLEM, guardian_at
from src.quest_journal import GOLEM_FIGHT, hear

if TYPE_CHECKING:
    from src.game import Game  # src.game imports this module

# NES MjArmrHP: Magic Armor heals 1 HP every 4th step (when the counter's low 2 bits wrap to 0)
MAGIC_ARMOR_HEAL_STEPS = 4


class StepTriggers:
    """The hero's steps on the map: counting them, and NES MovementUpdates and CheckRepelTimer after each one."""

    def __init__(self, game: 'Game') -> None:
        self.game = game

    def reset_step_count(self) -> None:
        """Start counting steps again from 0, as on arriving on a map (stairs then wait for a step off them).
        handle_battles' record of the last step it rolled for goes back to 0 with it: otherwise, a count that reached it
        again (one step after leaving a map after one step) would look like that already-rolled step, and the step
        would get no CheckBlockDmg (no damage and no fight roll), when on the NES every step onto a block runs it."""
        self.game.tiles_moved_since_spawn = 0
        self.game.last_amount_of_tiles_moved = 0

    def count_step(self) -> None:
        game = self.game
        game.tiles_moved_since_spawn += 1
        game.game_state.tiles_moved_total += 1
        game.event_bus.emit(StepTaken())
        # NES GameEngineLoop: the radiant timer (#216) and CheckRepelTimer are outside CheckForTriggers, so they keep
        # ticking (and wear off) after the Dragonlord's defeat. Both run at the top of the loop (LCA56, LCA6C), after
        # ChkSpecialLoc has rolled this step's fight, so they tick once that roll (and any fight) is done: see
        # tick_repel_timer_after_step
        game.repel_tick_pending = True
        # NES ChkSpecialLoc: a step off the map's edge goes to CheckMapExit instead of CheckForTriggers, so it doesn't
        # heal (MovmtIncHP) or count a Magic Armor step, and gets no damage or fight roll (see handle_battles)
        if not self.stepped_off_the_map():
            self.check_for_triggers()
        game.auto_grind.after_step()

    def stepped_off_the_map(self) -> bool:
        """NES ChkSpecialLoc: whether the step that has just finished took the hero off the map's edge (a town gate).
        The step has only just finished, so the hero's row and column haven't caught up with its rect yet."""
        game = self.game
        return game.current_map.is_map_exit(game.player.rect.y // game.tile_size, game.player.rect.x // game.tile_size)

    def check_for_triggers(self) -> None:
        """NES CheckForTriggers (Bank03, reached from ChkSpecialLoc after every completed step): MovementUpdates only
        runs while F_DGNLRD_DEAD is clear. Once the Dragonlord is dead it branches to ChkCstlEnd instead, which only
        checks for the end-game trigger in front of King Lorik (Ending.check_for_end_game_trigger) and then falls into
        CheckBlockDmg like before.

        CheckBlockDmg isn't here: it's split between handle_warps (map-changing tiles, still checked after the
        Dragonlord), handle_environment_damage and handle_battles, which each stop at ChkOtherBlocks' own
        F_DGNLRD_DEAD check, as the NES does."""
        if self.game.story_flags.dragonlord_defeated:
            return
        self.movement_updates()

    def movement_updates(self) -> None:
        """NES MovementUpdates, in order: the armor's HP regeneration (MovmtIncHP), ChkLowHP (clear_low_hp_palette),
        CheckTantCursed, then the guardian checks (CheckAxeKnight, CheckGrnDragon, CheckGolem). Only runs while the
        Dragonlord is alive (check_for_triggers)."""
        self.armor_step_heal()
        self.game.clear_low_hp_palette()  # NES MovementUpdates: ChkLowHP comes just before CheckTantCursed
        self.check_tantegel_cursed()
        self.check_guardian_fight()

    def armor_step_heal(self) -> None:
        """NES MovementUpdates/MovmtIncHP: Erdrick's Armor heals 1 HP every step. Magic Armor increments MjArmrHP every
        step and heals 1 HP when its low 2 bits wrap to 0, i.e. every 4th step in it. HP is capped at the maximum.
        (ChkLowHP, which comes next, is clear_low_hp_palette.)"""
        game = self.game
        player = game.player
        if player.armor == "Erdrick's Armor":
            heal = True
        elif player.armor == "Magic Armor":
            game.magic_armor_steps = (game.magic_armor_steps + 1) % 256  # MjArmrHP is one byte
            heal = game.magic_armor_steps % MAGIC_ARMOR_HEAL_STEPS == 0
        else:
            heal = False
        if heal:
            player.current_hp = min(player.current_hp + 1, player.max_hp)

    def check_tantegel_cursed(self) -> None:
        """NES CheckTantCursed (part of MovementUpdates, run every step while the Dragonlord is alive): a cursed player
        who reaches Y=27 of Tantegel's ground floor is told "Cursed one,be gone!" and CheckMapExit forces them out of
        the castle."""
        game = self.game
        if game.current_map.identifier != 'TantegelCourtyard' or not game.player.is_cursed:
            return
        if game.player.rect.y // game.tile_size != TANTEGEL_CURSED_ROW:
            return
        game.cmd_menu.show_text_in_dialog_box(game._("Cursed one,be gone!"), add_quotes=True,
                                              skip_text=game.skip_text)
        game.leave_tantegel()

    def check_guardian_fight(self) -> None:
        """NES MovementUpdates (CheckAxeKnight, CheckGrnDragon, CheckGolem): stepping onto a guardian's tile starts
        its fixed fight (InitFight). It's queued so handle_battles starts it this same frame."""
        game = self.game
        # The step has only just finished, so the hero's row and column haven't caught up with its rect yet
        coordinates = game.player.rect.y // game.tile_size, game.player.rect.x // game.tile_size
        guardian = guardian_at(game.current_map.identifier, coordinates, game.story_flags)
        if guardian is not None:
            game.battle_ctrl.queue_scripted_battle(guardian.enemy_name)
            if guardian is GOLEM:
                hear(game.story_flags, GOLEM_FIGHT)  # the quest journal: the hero has met the Golem

    def tick_repel_timer_after_step(self) -> None:
        """NES GameEngineLoop (LCA56) -> CheckRepelTimer (LCA6C), once per step, after that step's fight roll
        (ChkSpecialLoc -> CheckBlockDmg): the radiant timer first, then the repel timer. The step that brings REPEL's
        255 down to 1 is still protected, so it lasts 127 steps, and its message comes after that step's roll; the
        light shrinks after the roll too (#429)."""
        game = self.game
        if game.repel_tick_pending:
            game.repel_tick_pending = False
            game.game_state.tick_radiant_timer()
            self.tick_repel_timer()

    def tick_repel_timer(self) -> None:
        """NES CheckRepelTimer: the timer drops by 2 per step. REPEL (odd start) ends at 1, Fairy Water (even) at 0."""
        game = self.game
        if not game.repel_timer:
            return
        game.repel_timer -= 2
        if game.repel_timer in (0, 1):
            if game.repel_timer:
                message = game._("REPEL has lost its effect.")
            else:
                message = game._("The Fairy Water has lost its effect.")
            game.repel_timer = 0
            game.cmd_menu.show_text_in_dialog_box(message, skip_text=game.skip_text)
