"""HeroDamage: the hero losing HP to an enemy's attack or spell, a swamp or a force field, which used to live on Game.

An enemy's hit comes from the battle (BattleController, NES PlayerHit); a swamp or a force field from the block the
hero steps onto (NES CheckBlockDmg, through FieldEncounters.handle_battles, or Game's post-move checks). Neither
hurts in god mode or when INVULNERABLE. A hero brought to 0 HP dies in HeroDeath.handle_death (src/hero_death.py),
later that frame.
"""
from typing import TYPE_CHECKING

from pygame import display

from src.color import RED
from src.common import singular_or_plural
from src.menu import BATTLE_LINE
from src.visual_effects import flash_transparent_color, force_field_flash

if TYPE_CHECKING:
    from src.game import Game  # src.game imports this module

# NES ChkOtherBlocks: a swamp step costs 2 HP (DoSwampDamage, LCDD4), a force field step 15 (LCE2B)
SWAMP_DAMAGE = 2
FORCE_FIELD_DAMAGE = 15


class HeroDamage:
    """The hero's damage from enemies, swamps and force fields."""

    def __init__(self, game: 'Game') -> None:
        self.game = game

    def receive_damage(self, attack_damage: int) -> None:
        game = self.game
        player = game.player
        # God mode or invulnerable: take no damage
        if player.god_mode or game.invulnerable:
            return

        game.sound.play_sound(game.directories.receive_damage_2_sfx)
        player.current_hp -= attack_damage
        if player.current_hp < 0:
            player.current_hp = 0
        game.battle_ctrl.player_hit_effect()  # NES PlayerHit: screen shake, red flash on a deathblow
        game.load_window_palette()  # NES PlayerHit: LoadRegBGPal, after the screen shake (red if HP is now low)
        game.drawer.draw_hovering_stats_window(game.screen, player, game.color)
        # NES TextBlock16 entry 10: "Thy Hit" + PLRL, which adds an "s" unless the damage is 1 (Bank01 DoPLRL)
        damage_line = singular_or_plural(attack_damage, game._("Thy Hit decreased by {}.\n"),
                                         game._("Thy Hits decreased by {}.\n")).format(attack_damage)
        # It ends with no WAIT: PlayerHit goes on to the pop-up and the next player turn (or the death music) at once
        game.cmd_menu.show_line_in_dialog_box(damage_line, **BATTLE_LINE)

    def handle_environment_damage(self, tile: str | None = None) -> None:
        """Swamp and force field damage for the block the hero stands on (current_tile unless tile is given), once
        per step. handle_battles calls it with the block just stepped onto, before the fight roll."""
        game = self.game
        player = game.player
        # NES ChkOtherBlocks: once the Dragonlord is dead, swamps and barriers no longer hurt
        if game.story_flags.dragonlord_defeated:
            return
        if tile is None:
            tile = player.current_tile
        if not player.armor == "Erdrick's Armor":
            if not player.is_moving:
                if tile == 'MARSH':
                    if not player.received_environment_damage:
                        self.damage_step(damage_amount=SWAMP_DAMAGE)
                elif tile == 'BARRIER':
                    if not player.received_environment_damage:
                        self.damage_step(damage_amount=FORCE_FIELD_DAMAGE, force_field=True)
            else:
                player.received_environment_damage = False

    def damage_step(self, damage_amount: int, force_field: bool = False) -> None:
        game = self.game
        player = game.player
        # God mode or invulnerable: take no damage
        if player.god_mode or game.invulnerable:
            return

        # NES ChkOtherBlocks: SFX_FFDAMAGE on a force field (LCE2B), SFX_SWMP_DMG on a swamp (LCDD4)
        game.sound.play_sound(game.directories.barrier_sfx if force_field else game.directories.swamp_sfx)
        player.received_environment_damage = True
        if force_field:
            # NES force field damage (LCE30): the screen flashes red three times, each flash followed by
            # LoadRegBGPal, all before the 15 HP are taken (LCE44). After that the palette is only loaded again if
            # the hero is dead (LCE55; handle_death), so a force field step that leaves HP low doesn't turn the
            # windows red: they stay as they were until the next palette load.
            force_field_flash(RED, game.screen, game.game_state.config)
            game.load_window_palette()
            player.current_hp = max(player.current_hp - damage_amount, 0)
        else:
            # NES DoSwampDamage: one red flash (RedFlashScreen), then the 2 HP (LCDDF), then LoadRegBGPal with the
            # new HP (LCDED)
            flash_transparent_color(RED, game.screen, game.game_state.config)
            player.current_hp = max(player.current_hp - damage_amount, 0)
            game.load_window_palette()
        game.drawer.draw_all(game, game.game_state.enable_animate)
        display.flip()
