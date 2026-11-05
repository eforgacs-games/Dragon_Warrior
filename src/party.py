"""The party (co-op, #438): the heroes of the adventure. Not on the NES, which has one.

With the HEROES option on 2 (the options overlay's OTHER page, a global setting; 1 is the NES), BEGIN A NEW QUEST
asks for a second name after the first, and the quest starts with two heroes: the first, ``game.player``, who leads
the party on the map and whose adventure log it is, and the second, ``game.companion``. Each has a name, a level, HP,
MP, equipment, items and spells of their own, worked out from their own name as the NES does (LoadStats); the gold is
the party's, kept with the first hero. A log keeps the party it was started with, whatever HEROES says later: the
second hero is saved with it (src/save_file.py COMPANION_KEY), and with the save states, the rewind and the autosave.

This is the party's first part: the second hero is kept and saved. Following the first on the map, fighting beside
them (each choosing a command, the enemy choosing whom it attacks), player 2's controls and the inns, shops and
chests that ask which hero come next.
"""
from typing import TYPE_CHECKING, Any

from src.player.player import Player

if TYPE_CHECKING:
    from src.game import Game  # src.game imports this module

SOLO = 1
PAIR = 2


def new_hero(game: 'Game', name: str = "Player") -> Player:
    """A level 1 hero called ``name``, on the game's map, with the hero's sprites (the stats from the name: LoadStats).
    The second hero is made like the first (Game.__init__), with no god mode: that's the first hero's alone."""
    config = game.game_state.config
    hero = Player(center_point=None, images=game.current_map.scale_sprite_sheet(game.directories.UNARMED_HERO_PATH),
                  current_map=game.current_map, fighters_ring_attack_bonus=config['FIGHTERS_RING_ATTACK_BONUS'])
    hero.name = name
    hero.set_initial_stats()
    return hero


def party_of(player: Player, companion: Player | None) -> list[Player]:
    """The heroes, the first first."""
    return [player] if companion is None else [player, companion]


def starts_as_party(config: dict[str, Any]) -> bool:
    """Whether a new quest starts with two heroes (HEROES)."""
    return config.get('PARTY') == PAIR
