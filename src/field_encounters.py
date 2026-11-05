"""FieldEncounters: the fights a step on the map starts, which used to live on Game.

Once a frame (Game.map_frame), handle_battles starts a scripted fight that is waiting (the Dragonlord, the Silver
Harp's, a guardian's), or, once per step, runs NES CheckBlockDmg for the block the hero has just stepped onto: its
swamp or force field damage (src/hero_damage.py), then the fight roll (roll_for_fight, src/encounters.py), which a
hill puts off for a few frames (MovementController.hill_pause_frame). The fight itself is BattleController's.

The step counts it compares and the ENCOUNTERS option's HALF toggle stay on the Game (save states keep them,
src/save_state.py GAME_VALUES).
"""
from typing import TYPE_CHECKING

from src.battle_controller import BattleOutcome
from src.calculation import get_tile_id_by_coordinates
from src.encounters import ENEMY_GROUPS, encounter_group, roll_encounter
from src.game_options import ENCOUNTERS_HALF, ENCOUNTERS_OFF
from src.movement import HILL_PAUSE_FRAMES
from src.random_streams import hero_random

if TYPE_CHECKING:
    from src.game import Game  # src.game imports this module


class FieldEncounters:
    """The fights on the map: scripted ones that are waiting, and the random fight roll after each step."""

    def __init__(self, game: 'Game') -> None:
        self.game = game

    def handle_battles(self) -> None:
        game = self.game
        if game.battle_ctrl.pending_scripted_battle:
            # A fixed fight: the Dragonlord or the Silver Harp, asked for by a dialog that has now closed, or a guardian
            # the hero has just stepped up to.
            game.battle_ctrl.run_pending_scripted_battle()
            # NES: InitFight takes the place of CheckBlockDmg, so this step can't also bring a random fight
            game.last_amount_of_tiles_moved = game.tiles_moved_since_spawn
            return
        if game.tiles_moved_since_spawn > 0 and game.tiles_moved_since_spawn != game.last_amount_of_tiles_moved:
            game.last_amount_of_tiles_moved = game.tiles_moved_since_spawn
            if game.step_triggers.stepped_off_the_map():
                return  # NES ChkSpecialLoc -> CheckMapExit: handle_warps leaves the map, with no damage or fight
            # NES CheckBlockDmg starts with UpdateRandNum on every step, whatever the block; its fight roll reads this
            # RandNumUB (ChkFight2), after the swamp's damage or the hill's pause
            game.step_roll = hero_random.randint(0, 255)
            # NES ChkOtherBlocks: once the Dragonlord is dead, no more damage from the blocks and no more random fights
            if game.story_flags.dragonlord_defeated:
                return
            # NES CheckBlockDmg runs once per step, on the block the player has just stepped onto. The player's
            # column/row and current_tile aren't updated until later in the frame, so read them from the sprite.
            column, row = game.player.rect.x // game.tile_size, game.player.rect.y // game.tile_size
            tile = get_tile_id_by_coordinates(column, row, game.current_map)
            # NES CheckBlockDmg: swamp and force field damage come before the fight roll, and a hero they kill
            # doesn't fight (handle_death, later this frame, shows the death on the map)
            game.hero_damage.handle_environment_damage(tile)
            if game.player.current_hp <= 0:
                return
            if tile == 'HILLS':
                # NES ChkBlkSand: the fight roll waits for the hill's pause (hill_pause_frame)
                game.movement.hill_pause_frames = HILL_PAUSE_FRAMES
                return
            self.roll_for_fight(column, row, tile)

    def roll_for_fight(self, column: int, row: int, tile: str | None) -> None:
        """NES CheckBlockDmg's fight roll for the block the hero has just stepped onto, and the fight if it starts."""
        game = self.game
        group = encounter_group(game.current_map.identifier, column, row)
        if group is None:
            return
        game.last_zone = group
        enemies_in_current_zone = ENEMY_GROUPS[group] if game.game_state.config["FORCE_BATTLE"] else \
            self.thin_encounters(roll_encounter(game.current_map.identifier, tile, column, row, game.step_roll))
        if enemies_in_current_zone is not None and not game.game_state.config["NO_BATTLES"]:
            if game.battle_ctrl.run_battle(enemies_in_current_zone) != BattleOutcome.REPELLED:
                # NES: after the fight the hero is still on this block; stairs wait for STAIRS (or a step off them)
                game.map_mgr.stay_on_stairs(row, column)
                game.auto_grind.after_fight()
        game.battle_ctrl.battle_menu_row = 0
        game.battle_ctrl.battle_menu_column = 0

    def thin_encounters(self, enemies: tuple[str, ...] | None) -> tuple[str, ...] | None:
        """The ENCOUNTERS option (not NES) on a random fight the NES's roll has just started: NES keeps it, OFF skips
        it, HALF skips every other one. The roll itself, the random numbers it takes and the enemy it picks are the
        NES's, so the fights that do start are the ones the NES would start; guardians, the Dragonlord and every other
        scripted fight don't come through here."""
        if enemies is None:
            return None
        setting = self.game.game_state.config.get('ENCOUNTERS')
        if setting == ENCOUNTERS_OFF:
            return None
        if setting == ENCOUNTERS_HALF:
            skipped, self.game.skip_next_encounter = self.game.skip_next_encounter, not self.game.skip_next_encounter
            if skipped:
                return None
        return enemies
