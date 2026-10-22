"""
The three fixed guardian fights: the Axe Knight at Erdrick's Armor in Hauksness, the Green Dragon in front of Princess
Gwaelin's door in the Swamp Cave, and the Golem in front of Cantlin.

All of it follows Bank03 of the nmikstas disassembly:
- MovementUpdates (run by CheckForTriggers after every completed step, but only while the Dragonlord is alive) checks
  CheckAxeKnight, CheckGrnDragon and CheckGolem, in that order, and jumps straight to InitFight with the guardian's
  enemy number when the hero has just stepped onto its tile. Searching, or arriving on the tile any other way, doesn't
  start a fight.
- The Green Dragon and the Golem check their StoryFlags bit first (F_GDRG_DEAD, F_GOLEM_DEAD), so once beaten they
  are gone for good. The Axe Knight has no flag: he fights every time the hero steps onto the armor's tile, even after
  he's been beaten and the armor has been found.
- EnemyDefeated sets F_GDRG_DEAD for any Green Dragon beaten in the Swamp Cave and F_GOLEM_DEAD for any Golem beaten
  on the overworld. Neither is a random encounter there, so in practice only the guardian fights set them.
- RunSuccessful (ChkMapHauksness, ChkMapSwampCave, ChkMapOverworld): running away from the fight moves the hero one
  block back (left for the Axe Knight, "so they cannot search for Erdrick's armor after running"; up for the Green
  Dragon and the Golem, so they can't get past) and reloads the map with the stairs sound (MapChngWithSound).
- Dying needs nothing special: no flag is set, so the guardian is waiting the next time.

Coordinates here are (row, column) in this game's layouts. The NES (x, y) of each tile is noted with the map's offset.
"""
from dataclasses import dataclass

from src.story_flags import StoryFlags


@dataclass(frozen=True)
class Guardian:
    enemy_name: str
    map_identifier: str
    coordinates: tuple[int, int]
    # Where RunSuccessful puts the hero after running away
    escape_coordinates: tuple[int, int]
    # The StoryFlags field that keeps the guardian away once beaten (None: he always comes back)
    defeated_flag: str | None

    def is_defeated(self, story_flags: StoryFlags) -> bool:
        return self.defeated_flag is not None and getattr(story_flags, self.defeated_flag)


# In MovementUpdates order
AXE_KNIGHT = Guardian(
    # NES CheckAxeKnight: Hauksness (18, 12), the tile Erdrick's Armor is found on (SrchEdrckArmor). Hauksness (x, y)
    # is (y + 8, x + 9) here. ChkMapHauksness: DEC CharXPos.
    'Axe Knight', 'Hauksness', (20, 27), escape_coordinates=(20, 26), defeated_flag=None)
GREEN_DRAGON = Guardian(
    # NES CheckGrnDragon: Swamp Cave (4, 14), the one-tile passage to Gwaelin's door. Swamp Cave (x, y) is
    # (y + 6, x + 4) here. ChkMapSwampCave/MovePlyrUp1Block: DEC CharYPos.
    'Green Dragon', 'SwampCave', (20, 8), escape_coordinates=(19, 8), defeated_flag='green_dragon_defeated')
GOLEM = Guardian(
    # NES CheckGolem: overworld (73, 100), the gap in the wall north of Cantlin (whose gate is at (73, 102)). Overworld
    # (x, y) is (y + 7, x + 8) here. ChkMapOverworld branches to MovePlyrUp1Block.
    'Golem', 'Alefgard', (107, 81), escape_coordinates=(106, 81), defeated_flag='golem_defeated')

GUARDIANS = (AXE_KNIGHT, GREEN_DRAGON, GOLEM)


def _guardian_on_tile(map_identifier: str, coordinates: tuple[int, int],
                      story_flags: StoryFlags) -> Guardian | None:
    for guardian in GUARDIANS:
        if (guardian.map_identifier, guardian.coordinates) == (map_identifier, coordinates) and \
                not guardian.is_defeated(story_flags):
            return guardian
    return None


def guardian_at(map_identifier: str, coordinates: tuple[int, int], story_flags: StoryFlags) -> Guardian | None:
    """NES CheckForTriggers/MovementUpdates: the guardian who fights the hero for stepping onto this tile, if any."""
    if story_flags.dragonlord_defeated:
        # CheckForTriggers only jumps to MovementUpdates while F_DGNLRD_DEAD is clear
        return None
    return _guardian_on_tile(map_identifier, coordinates, story_flags)


def escape_coordinates(map_identifier: str, coordinates: tuple[int, int],
                       story_flags: StoryFlags) -> tuple[int, int] | None:
    """NES RunSuccessful: where the hero is moved after running away on this tile, or None to stay put. Like the
    NES, this looks only at the map, the tile and the story flags, not at which enemy it was."""
    guardian = _guardian_on_tile(map_identifier, coordinates, story_flags)
    return guardian.escape_coordinates if guardian is not None else None


def record_victory(enemy_name: str, map_identifier: str, story_flags: StoryFlags) -> None:
    """NES EnemyDefeated: beating a Green Dragon in the Swamp Cave or a Golem on the overworld sets its story flag."""
    for guardian in (GREEN_DRAGON, GOLEM):
        if (enemy_name, map_identifier) == (guardian.enemy_name, guardian.map_identifier):
            assert guardian.defeated_flag is not None
            setattr(story_flags, guardian.defeated_flag, True)
