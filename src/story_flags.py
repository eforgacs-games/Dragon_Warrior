"""
Story progress that changes the world once it's reached, kept in one place so that saving can persist it.

Mirrors the NES story bits (see Dragon_Warrior_Defines.asm in the nmikstas disassembly). The NES keeps them in three
bytes, and SaveData (Bank03) writes all three to the battery-backed save RAM as they are; LoadSavedData reads them back
the same way (game slot offsets $0B-$0D in reference/sram-doc.txt):
- ModsnSpells ($CF): bits 2 and 3 are below. Its other bits are the Healmore/Hurtmore spells and the four worn items
  (Dragon's Scale, Fighter's Ring, Cursed Belt, Death Necklace), which belong to the hero and live on Player.
- PlayerFlags ($DF): bits 0-3 are below. Bits 4-7 are battle status (asleep/stopspelled), which every fight resets.
- StoryFlags ($E4): bits 1, 2 and 6 are below. The other bits are unused.

Not story flags, and not saved by the NES: the treasure chest history (TrsrXPos, cleared by MainGameEngine on every
start), the door history, and the repel and radiant timers (cleared by StartAtThroneRoom).

One entry here isn't on the NES: heard_goals, the quest journal's (src/quest_journal.py) record of the goals the hero
has been told of, kept with the story so it's saved and loaded with it.
"""

from dataclasses import asdict, dataclass, field, fields
from typing import Any

# The key the flags are saved under. Saves from before it existed stored the first two flags as flat keys.
SAVE_KEY = 'StoryFlags'
LEGACY_SAVE_KEYS = {'RainbowBridgeBuilt': 'rainbow_bridge_built', 'CharlockStairsRevealed': 'charlock_stairs_revealed'}
HEARD_GOALS = 'heard_goals'

# Who told the hero of a goal: an NPC's NES dialog byte (src/npcs.py), or a name for what isn't an NPC's dialog
GoalSource = int | str


@dataclass(slots=True)
class StoryFlags:
    # ModsnSpells bit 2, NES F_PSG_FOUND: the secret passage behind the Dragonlord's throne has been found.
    charlock_stairs_revealed: bool = False
    # ModsnSpells bit 3, NES F_RNBW_BRDG: the Rainbow Drop has built the Rainbow Bridge.
    rainbow_bridge_built: bool = False

    # PlayerFlags bit 0, NES F_GOT_GWAELIN: the hero is carrying Princess Gwaelin. Dying clears it (DeathText).
    carrying_gwaelin: bool = False
    # PlayerFlags bit 1, NES F_RTN_GWAELIN: Princess Gwaelin was carried back to King Lorik.
    gwaelin_returned: bool = False
    # PlayerFlags bit 2, NES F_DTH_NCK_FOUND: the Death Necklace has come out of its chest, which from then on only
    # ever holds gold (ChkTrsrNecklace).
    death_necklace_found: bool = False
    # PlayerFlags bit 3, NES F_LEFT_THROOM: the hero has been beyond the throne room (set by InitMapData). The
    # throne room chests are gone from then on, and King Lorik greets the hero as returning and offers to save.
    left_throne_room: bool = False

    # StoryFlags bit 1, NES F_GOLEM_DEAD: the Golem guarding Cantlin was defeated (EnemyDefeated), so CheckGolem no
    # longer starts his fight. See src/guardians.py.
    golem_defeated: bool = False
    # StoryFlags bit 2, NES F_DGNLRD_DEAD: set as the Ball of Light is found after beating the Dragonlord's final form.
    # From then on there are no random fights or swamp/barrier damage, every NPC has victory dialog, and Tantegel waits
    # for the hero.
    dragonlord_defeated: bool = False
    # StoryFlags bit 6, NES F_GDRG_DEAD: the Green Dragon guarding Gwaelin was defeated (EnemyDefeated), so
    # CheckGrnDragon no longer starts its fight. The Axe Knight has no flag: he fights every time.
    green_dragon_defeated: bool = False

    # Not NES: each goal the hero has been told of (src/quest_journal.py Goal.key), with who told of it. Saves from
    # before it existed load with nothing heard.
    heard_goals: dict[str, GoalSource] = field(default_factory=dict)

    @property
    def gwaelin_rescued(self) -> bool:
        """NES F_DONE_GWAELIN: Gwaelin is being carried or has been returned."""
        return self.carrying_gwaelin or self.gwaelin_returned

    def to_save(self) -> dict[str, Any]:
        return asdict(self)  # a copy: heard_goals too

    @classmethod
    def from_save(cls, save_file: dict[str, Any]) -> 'StoryFlags':
        """Read the flags from a save file. Flags it doesn't mention keep their new-game value.

        Saves from before the flags were kept together have no StoryFlags key: they may have the Rainbow Bridge and
        Charlock flags as flat keys, and the rest is worked out from what they do have. Those saves could only be
        made with King Lorik after leaving the throne room, and only his thanks for returning Gwaelin give Gwaelin's
        Love."""
        flags = cls()
        for legacy_key, name in LEGACY_SAVE_KEYS.items():
            if legacy_key in save_file:
                setattr(flags, name, bool(save_file[legacy_key]))
        saved_flags = save_file.get(SAVE_KEY)
        if saved_flags is None:
            inventory = save_file.get('Inventory', [])
            flags.left_throne_room = True
            flags.gwaelin_returned = "Gwaelin's Love" in inventory
            flags.death_necklace_found = "Death Necklace" in inventory
            return flags
        for name in story_bits():
            if name in saved_flags:
                setattr(flags, name, bool(saved_flags[name]))
        flags.heard_goals = heard_goals_from_save(saved_flags.get(HEARD_GOALS))
        return flags


def story_bits() -> tuple[str, ...]:
    """The names of the flags that are the NES's story bits: every field but heard_goals."""
    return tuple(flag.name for flag in fields(StoryFlags) if flag.name != HEARD_GOALS)


def heard_goals_from_save(saved: Any) -> dict[str, GoalSource]:
    """The heard goals a save has, leaving out any entry that isn't a goal's key and who told of it."""
    if not isinstance(saved, dict):
        return {}
    return {goal: source for goal, source in saved.items()
            if isinstance(goal, str) and type(source) in (int, str)}
