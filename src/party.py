"""The party (co-op, #438): the heroes of the adventure. Not on the NES, which has one.

With the HEROES option on 2 (the options overlay's OTHER page, a global setting; 1 is the NES), BEGIN A NEW QUEST
asks for a second name after the first, and the quest starts with two heroes: the first, ``game.player``, who leads
the party on the map and whose adventure log it is, and the second, ``game.companion``. Each has a name, a level, HP,
MP, equipment, items and spells of their own, worked out from their own name as the NES does (LoadStats); the gold is
the party's, kept with the first hero. A log keeps the party it was started with, whatever HEROES says later: the
second hero is saved with it (src/save_file.py COMPANION_KEY), and with the save states, the rewind and the autosave.

The second hero is kept and saved, follows the first one step behind on the map (src/follower.py) and fights beside
them (src/battle_controller.py): each round, each hero still standing chooses a command and acts, the first first,
then the enemy acts against one of them, chosen at random. The battle code acts on ``game.player``, so a hero's turn,
and the enemy's turn against a hero, run with that hero as ``game.player`` (``acting``). A hero brought to 0 HP has
fallen and sits the fight out; the fight is lost only when both have fallen. Winning gives each hero still standing
the enemy's experience, and the party its gold, once. A hero who fell gets back up with 1 HP once the fight is won or
fled, with FALLEN HEROES on GET UP; on INN, the default, they stay down until the party stays at an inn: greyed on the
map, taking no swamp or barrier damage, and they can't fight, use ITEM, SPELL or a shop. A fallen first hero still
leads the party on the map (they're the adventure log's). A lost fight takes both back to King Lorik, as on the NES.
One successful run gets the party away.

The second hero's turns are player 2's: their command, their SPELL and ITEM windows and their action's messages read
player 2's joypad (src/controls.py player_input: the numpad, or a second controller, src/gamepad.py), the rest of the
fight player 1's.

In the world: an inn charges each hero its price and both rest (data/text/dialog_lookup_table.py); a shop first asks
who is shopping and runs for that hero (``for_a_chosen_hero``), with the party's gold; a chest's item goes to the first
hero with room for it, and the first hero may drop something for it if neither has (CommandMenu.take_item); STATUS
shows each hero's status in turn. ITEM and SPELL on the map first ask which hero (CommandMenu.chosen_hero): the cost is
theirs (their MP, their item), HEAL, HEALMORE and the items of OWN_ITEMS act on them, and the rest act for the party
as the first hero's, where the party stands (CommandMenu.field_effect), the item lent to the first hero for it.
Player 2's A on the map opens the second hero's own ITEM, SPELL and STATUS, on player 2's joypad
(src/player_two_menu.py).
"""
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from src.game_options import FALLEN_GET_UP, FALLEN_INN
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


def companion_of(game: Any) -> Player | None:
    """The game's second hero, if it has one."""
    companion = getattr(game, 'companion', None)
    return companion if isinstance(companion, Player) else None


def in_party_mode(game: Any) -> bool:
    """Whether the game has a second hero."""
    return companion_of(game) is not None


def first_hero(game: Any) -> Any:
    """The first hero, ``game.player`` but while another hero is acting (``acting``)."""
    first = getattr(game, 'first_hero', None)
    return first if isinstance(first, Player) else game.player


def heroes(game: Any) -> list[Player]:
    """The heroes, the first first (Game.party, for any game), whoever is acting."""
    return party_of(first_hero(game), companion_of(game))


def living(game: Any) -> list[Player]:
    """The heroes still standing, the first first."""
    return [hero for hero in heroes(game) if not hero.is_dead]


@contextmanager
def acting(game: Any, hero: Player) -> Iterator[None]:
    """For the length of the block, ``hero`` is the hero the game acts on: ``game.player``, and the CommandMenu's and
    its DialogLookup's ``player``, which the fight, the spells and the items read (src/battle_controller.py), while
    ``game.first_hero`` keeps the first hero (``heroes``). The gold is the party's: the hero has it for the block, and
    what's left goes back. The hero before is put back afterwards, whatever happens. With ``hero`` the one acting
    already, nothing changes."""
    previous = game.player
    if hero is previous:
        yield
        return
    cmd_menu = game.cmd_menu
    dialog_lookup = getattr(cmd_menu, 'dialog_lookup', None)
    outermost = not isinstance(getattr(game, 'first_hero', None), Player)
    if outermost:
        game.first_hero = previous
    hero.gold = previous.gold  # the party's gold, whoever spends it
    game.player = cmd_menu.player = hero
    if dialog_lookup is not None:
        dialog_lookup.player = hero
    try:
        yield
    finally:
        previous.gold = hero.gold
        game.player = cmd_menu.player = previous
        if dialog_lookup is not None:
            dialog_lookup.player = previous
        if outermost:
            game.first_hero = None


def stays_down(config: dict[str, Any]) -> bool:
    """Whether a hero who falls in a fight stays down until an inn (FALLEN HEROES on INN, the default), rather than
    getting back up with 1 HP once the fight is won or fled (GET UP)."""
    return config.get('FALLEN', FALLEN_INN) != FALLEN_GET_UP


def other_hero_standing(game: Any, hero: Any) -> bool:
    """Whether a party's other hero is standing: the party hasn't fallen, so ``hero`` falling isn't the end."""
    return any(other is not hero and not other.is_dead and other.current_hp > 0 for other in heroes(game))


def someone_chosen(game: Any) -> bool:
    """Whether a hero has been chosen to act (``acting`` is under way), so nothing asks again."""
    return isinstance(getattr(game, 'first_hero', None), Player)
