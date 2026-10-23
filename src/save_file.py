"""The save file: what CommandMenu.save writes for an adventure log and Game.load_game reads back, and where the logs
are kept.

NES SaveData (Bank03) writes the hero's experience, gold, items, equipment, name, HP and MP, plus the ModsnSpells,
PlayerFlags and StoryFlags bytes whole (game slot offsets $00-$18 in reference/sram-doc.txt), and the message speed
(offset $16). Here each adventure log is one JSON file, save_slot_<n>.json in the save folder, holding SaveFile.to_save():
the hero's stats and equipment under the *_KEY names below, the position (this game starts where the save was made),
the story bits as one StoryFlags entry (src/story_flags.py) and the log's options (src/options_screen.py). Like the NES,
the treasure chest history and the repel timer aren't saved.

Saves and the playtest checkpoints in data/checkpoints/ (src/checkpoints.py) are read with SaveFile.from_save, which
gives a key a save doesn't have the value Game.load_game always gave it, so older saves load as they always have.
"""
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

from src.options_screen import Options, options_from_save, options_to_save
from src.story_flags import SAVE_KEY as STORY_FLAGS_SAVE_KEY
from src.story_flags import StoryFlags

# The save file keys, in the order CommandMenu.save writes them; the StoryFlags entry and the options keys follow
NAME_KEY = 'Name'
EXPERIENCE_KEY = 'Experience'
GOLD_KEY = 'Gold'
CURRENT_HP_KEY = 'CurrentHP'
CURRENT_MP_KEY = 'CurrentMP'
WEAPON_KEY = 'Weapon'
ARMOR_KEY = 'Armor'
SHIELD_KEY = 'Shield'
WEARING_DRAGON_SCALE_KEY = 'WearingDragonScale'
WEARING_FIGHTERS_RING_KEY = 'WearingFightersRing'
WEARING_CURSED_BELT_KEY = 'WearingCursedBelt'
WEARING_DEATH_NECKLACE_KEY = 'WearingDeathNecklace'
INVENTORY_KEY = 'Inventory'
SPELLS_KEY = 'Spells'
CURRENT_MAP_KEY = 'CurrentMap'
PLAYER_ROW_KEY = 'PlayerRow'
PLAYER_COLUMN_KEY = 'PlayerColumn'

# The NES has three adventure logs (reference/sram-doc.txt), numbered 1 to 3 on screen
ADVENTURE_LOGS = (1, 2, 3)
# Only the three adventure logs are saves; a save_slot_0.json or save_slot_4.json is ignored like any other stray file
SAVE_FILE_PATTERN = re.compile(r'save_slot_([123])\.json')


@dataclass(slots=True, kw_only=True)
class SaveFile:
    """One adventure log's save. A key the save doesn't have reads as the default here; CurrentHP and CurrentMP read
    as None, which load_game turns into the hero's max HP and MP, and a missing position (None) starts the hero on the
    map the game is showing, or at the saved map's initial coordinates."""
    name: str
    experience: int
    gold: int
    inventory: list[str]
    current_hp: int | None = None
    current_mp: int | None = None
    weapon: str = ''
    armor: str = ''
    shield: str = ''
    wearing_dragon_scale: bool = False
    wearing_fighters_ring: bool = False
    wearing_cursed_belt: bool = False
    wearing_death_necklace: bool = False
    spells: list[str] = field(default_factory=list)
    current_map: str | None = None
    player_row: int | None = None
    player_column: int | None = None
    story_flags: StoryFlags = field(default_factory=StoryFlags)
    options: Options = field(default_factory=Options)

    @classmethod
    def from_game(cls, player: Any, current_map: str, story_flags: StoryFlags, options: Options) -> 'SaveFile':
        """What CommandMenu.save keeps of the running game."""
        return cls(name=player.name, experience=player.total_experience, gold=player.gold, inventory=player.inventory,
                   current_hp=player.current_hp, current_mp=player.current_mp, weapon=player.weapon,
                   armor=player.armor, shield=player.shield, wearing_dragon_scale=player.wearing_dragon_scale,
                   wearing_fighters_ring=player.wearing_fighters_ring,
                   wearing_cursed_belt=player.wearing_cursed_belt,
                   wearing_death_necklace=player.wearing_death_necklace, spells=player.spells,
                   current_map=current_map, player_row=player.row, player_column=player.column,
                   story_flags=story_flags, options=options)

    def to_save(self) -> dict[str, Any]:
        """The save file's JSON object, key for key as CommandMenu.save has always written it."""
        return {
            NAME_KEY: self.name,
            EXPERIENCE_KEY: self.experience,
            GOLD_KEY: self.gold,
            CURRENT_HP_KEY: self.current_hp,
            CURRENT_MP_KEY: self.current_mp,
            WEAPON_KEY: self.weapon,
            ARMOR_KEY: self.armor,
            SHIELD_KEY: self.shield,
            WEARING_DRAGON_SCALE_KEY: self.wearing_dragon_scale,
            WEARING_FIGHTERS_RING_KEY: self.wearing_fighters_ring,
            WEARING_CURSED_BELT_KEY: self.wearing_cursed_belt,
            WEARING_DEATH_NECKLACE_KEY: self.wearing_death_necklace,
            INVENTORY_KEY: self.inventory,
            SPELLS_KEY: self.spells,
            CURRENT_MAP_KEY: self.current_map,
            PLAYER_ROW_KEY: self.player_row,
            PLAYER_COLUMN_KEY: self.player_column,
            STORY_FLAGS_SAVE_KEY: self.story_flags.to_save(),
            # NES SaveData (LFA7D): the message speed is saved with each log (offset $16); so are the dialog style
            # and NPCS MAKE WAY (src/options_screen.py)
            **options_to_save(self.options),
        }

    @classmethod
    def from_save(cls, save: dict[str, Any]) -> 'SaveFile':
        """Read a save file's JSON object. Name, Experience, Gold and Inventory must be there (KeyError if not); the
        rest falls back to the defaults above, the story flags to StoryFlags.from_save's (which also reads older
        saves' flat keys) and the options to NORMAL, CLASSIC and ON."""
        return cls(name=save[NAME_KEY], experience=save[EXPERIENCE_KEY], gold=save[GOLD_KEY],
                   inventory=save[INVENTORY_KEY], current_hp=save.get(CURRENT_HP_KEY),
                   current_mp=save.get(CURRENT_MP_KEY), weapon=save.get(WEAPON_KEY, ''),
                   armor=save.get(ARMOR_KEY, ''), shield=save.get(SHIELD_KEY, ''),
                   wearing_dragon_scale=save.get(WEARING_DRAGON_SCALE_KEY, False),
                   wearing_fighters_ring=save.get(WEARING_FIGHTERS_RING_KEY, False),
                   wearing_cursed_belt=save.get(WEARING_CURSED_BELT_KEY, False),
                   wearing_death_necklace=save.get(WEARING_DEATH_NECKLACE_KEY, False),
                   spells=save.get(SPELLS_KEY, []), current_map=save.get(CURRENT_MAP_KEY),
                   player_row=save.get(PLAYER_ROW_KEY), player_column=save.get(PLAYER_COLUMN_KEY),
                   story_flags=StoryFlags.from_save(save), options=options_from_save(save))

    def restore_player(self, player: Any) -> None:
        """NES LoadSavedData: the hero as saved. The stats are worked out again from the name and experience, and HP
        and MP the save doesn't have are full."""
        player.name = self.name
        player.total_experience = self.experience
        player.level = player.get_level_by_experience()
        player.update_stats_to_current_level()
        player.gold = self.gold
        player.current_hp = player.max_hp if self.current_hp is None else self.current_hp
        player.current_mp = player.max_mp if self.current_mp is None else self.current_mp
        player.weapon = self.weapon
        player.armor = self.armor
        player.shield = self.shield
        player.wearing_dragon_scale = self.wearing_dragon_scale
        player.wearing_fighters_ring = self.wearing_fighters_ring
        player.wearing_cursed_belt = self.wearing_cursed_belt
        player.wearing_death_necklace = self.wearing_death_necklace
        player.update_attack_power()
        player.update_defense_power()
        player.inventory = self.inventory
        player.spells = self.spells


def save_file_name(log: int) -> str:
    """The file adventure log number log is saved in."""
    return f'save_slot_{log}.json'


def save_path(save_dir: str, log: int) -> str:
    return os.path.join(save_dir, save_file_name(log))


def save_slot_number(save_file_name: str) -> int:
    """The adventure log number in a save file's name, e.g. 2 for save_slot_2.json."""
    match = SAVE_FILE_PATTERN.fullmatch(save_file_name)
    if match is None:
        raise ValueError(f"Not a save file name: {save_file_name}")
    return int(match.group(1))


def save_files(save_dir: str) -> list[str]:
    """The adventure log save files in the save folder, ignoring anything else that might be there."""
    if not os.path.isdir(save_dir):
        return []
    return sorted(name for name in os.listdir(save_dir) if SAVE_FILE_PATTERN.fullmatch(name))


def read_save(save_dir: str, save_file_name: str) -> dict | None:
    """The save in the save folder with this name, or None if it can't be read."""
    try:
        with open(os.path.join(save_dir, save_file_name)) as save_file:
            save = json.load(save_file)
    except (OSError, ValueError):
        return None
    return save if isinstance(save, dict) else None


def load_save(save_path: str) -> dict:
    """The save file's JSON object; unlike read_save, an unreadable file raises."""
    with open(save_path) as save_file:
        return json.load(save_file)


def read_save_name(save_path: str) -> str | None:
    """The hero's name in a save file, or None if there is no readable save there."""
    try:
        with open(save_path) as save_file:
            name = json.load(save_file).get(NAME_KEY)
    except (OSError, ValueError, AttributeError):
        return None
    return name if isinstance(name, str) else None


def write_save(save_path: str, save: dict) -> None:
    """Write a save file's JSON object, indented by 4 as every save has been."""
    with open(save_path, 'w') as save_file:
        save_file.write(json.dumps(save, indent=4))


def used_logs(save_dir: str, file_names: list[str]) -> list[tuple[int, str]]:
    """ShowUsedLogs: each used adventure log's number and hero's name, for the log window. A save that can't be read
    isn't listed."""
    logs = []
    for file_name in file_names:
        save = read_save(save_dir, file_name)
        if save is not None:
            logs.append((save_slot_number(file_name), str(save.get(NAME_KEY, ''))))
    return logs


def first_open_log(save_dir: str) -> int | None:
    """ShowOpenLogs: the lowest adventure log with no save in save_dir, or None if all three are used."""
    for log in ADVENTURE_LOGS:
        if not os.path.exists(save_path(save_dir, log)):
            return log
    return None


def logs_named(save_dir: str, name: str) -> list[int]:
    """The adventure logs in save_dir whose hero is called name (the save's 'Name', as Game.load_game reads it). A
    save that can't be read matches no name."""
    return [log for log in ADVENTURE_LOGS if read_save_name(save_path(save_dir, log)) == name]


def log_for_unchosen_save(save_dir: str, name: str) -> int | None:
    """The adventure log to save to when none was chosen (the title menu was skipped), never a save_slot_0.json that
    isn't a log: the one log whose hero has this hero's name, else the first open log. None, so nothing is saved, if
    several logs have the name, or if none has it and all three are used: a log with a different hero is never
    overwritten."""
    named = logs_named(save_dir, name)
    if len(named) == 1:
        return named[0]
    if named:
        print(f"Not saved: adventure logs {', '.join(map(str, named))} all have the hero {name}, "
              f"so it isn't clear which one to save to.")
        return None
    open_log = first_open_log(save_dir)
    if open_log is None:
        print(f"Not saved: all three adventure logs are used, and none has the hero {name}.")
    return open_log
