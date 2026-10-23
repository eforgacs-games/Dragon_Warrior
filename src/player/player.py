from collections.abc import Iterable
from typing import cast

from pygame import Surface

from src.calculation import Calculation
from src.direction import Direction
from src.items import Inventory, weapons, armor, shields
from src.maps import DragonWarriorMap
from src.player.player_stats import get_level_by_experience, get_stats_for_level, levels_list
from src.sprites.animated_sprite import AnimatedSprite


class Player(AnimatedSprite):

    def __init__(self, center_point, images: tuple[Surface, Surface, Surface, Surface], current_map: DragonWarriorMap,
                 direction_value=Direction.DOWN.value,
                 god_mode=False, fighters_ring_attack_bonus=0):
        AnimatedSprite.__init__(self, center_point, direction_value, images, identifier='HERO')

        # map/collision-related attributes

        self.row, self.column = current_map.initial_coordinates
        self.next_tile_checked = False
        self.is_moving = False
        self.next_coordinates = None
        self.next_next_coordinates = None
        self.current_tile = None
        self.calculation = Calculation(current_map.config)
        self.next_tile_id = self.calculation.get_next_tile_identifier(self.column, self.row, self.direction_value,
                                                                      current_map)
        self.next_next_tile_id = self.calculation.get_next_tile_identifier(self.column, self.row, self.direction_value,
                                                                           current_map,
                                                                           offset=2)
        self.bumped = False
        self.received_environment_damage = False

        self.adventure_log = 0

        # character attributes
        self.name = "Player"
        # status menu
        self.strength = 0  # attack power
        self.agility = 0  # defense power
        self.max_hp = 0
        self.max_mp = 0
        self.weapon = ""
        self.armor = ""
        self.shield = ""
        self.wearing_dragon_scale = False
        self.wearing_fighters_ring = False  # no stat effect on the NES; only changes NPC dialog
        self.fighters_ring_attack_bonus = fighters_ring_attack_bonus
        # Curse state, NES ModsnSpells bit 6 (F_CRSD_BELT) and bit 7 (F_DTH_NECKLACE). Neither changes any stat:
        # LoadStats never reads them. Like the other worn items (bits 4 and 5) they're saved with the hero.
        self.wearing_cursed_belt = False
        self.wearing_death_necklace = False

        # set name-based initial stats and growth stats

        self.set_initial_stats()
        self.attack_power = self.strength
        self.defense_power = self.agility // 2

        # set power based on equipment
        self.update_attack_power()
        self.update_defense_power()

        # hovering status window stats
        self.level = 0
        self.current_hp = self.max_hp
        self.current_mp = self.max_mp
        self.gold = 0
        self.total_experience = 0
        self.is_dead = False

        self.is_asleep = False
        self.is_stopspelled = False

        self.level = self.get_level_by_experience()

        self.spells: list[str] = []
        self.inventory = []  # an Inventory, in NES slot order (see the inventory property)
        self.god_mode = god_mode
        if god_mode:
            self.total_experience = 65536
            self.level = self.get_level_by_experience()
            self.update_stats_to_current_level()
            self.max_hp = 99_999
            self.current_hp = self.max_hp

            self.max_mp = 99_999
            self.current_mp = self.max_mp

            self.gold = 99_999

    def update_attack_power(self):
        if self.weapon == "":
            self.attack_power = self.strength
        elif weapons.get(self.weapon):
            self.attack_power = self.strength + weapons[self.weapon]['offense']
        else:
            print(f"ERROR: {self.weapon} is not a valid weapon.")
            self.attack_power = self.strength
        if self.wearing_fighters_ring:
            self.attack_power += self.fighters_ring_attack_bonus

    def update_defense_power(self):
        # NES: defense = agility / 2 + armor bonus + shield bonus
        self.defense_power = self.agility // 2
        if armor.get(self.armor):
            self.defense_power += armor[self.armor]['defense']
        if shields.get(self.shield):
            self.defense_power += shields[self.shield]['defense']
        if self.wearing_dragon_scale:
            self.defense_power += 2

    @property
    def is_cursed(self) -> bool:
        """NES: ModsnSpells AND #$C0, i.e. wearing the Cursed Belt or the Death Necklace."""
        return self.wearing_cursed_belt or self.wearing_death_necklace

    def is_wearing_cursed_item(self, item_name: str) -> bool:
        """Whether item_name is a cursed item the player has put on. NES ChkSellBelt/ChkSellNecklace and the
        discard checks (LE0B9) refuse to part with a worn cursed item ("A curse is upon thy body."); an unworn one can
        be sold or dropped like any other item."""
        return (item_name == "Cursed Belt" and self.wearing_cursed_belt) or \
            (item_name == "Death Necklace" and self.wearing_death_necklace)

    def remove_curse(self) -> None:
        """NES CursedDialog: the worn cursed items are taken from the inventory and both curse flags cleared."""
        if self.wearing_death_necklace and "Death Necklace" in self.inventory:
            self.inventory.remove("Death Necklace")
        if self.wearing_cursed_belt and "Cursed Belt" in self.inventory:
            self.inventory.remove("Cursed Belt")
        self.wearing_cursed_belt = False
        self.wearing_death_necklace = False

    @property
    def inventory(self) -> Inventory:
        """The hero's items in NES slot order: adding fills the first empty slot, removing leaves its slot empty
        (Inventory, NES AddInvItem/RemoveInvItem)."""
        return self._inventory

    @inventory.setter
    def inventory(self, items: Iterable[str | None]) -> None:
        self._inventory = items if isinstance(items, Inventory) else Inventory(items)

    def get_points_to_next_level(self) -> int:
        """GetExpRemaining (LF134): the next level's LevelUpTbl entry minus the experience. 0 at level 30."""
        if levels_list.get(self.level + 1):
            return max(0, cast(int, levels_list[self.level + 1]['total_exp']) - self.total_experience)
        return 0

    @property
    def points_to_next_level(self) -> int:
        return self.get_points_to_next_level()

    def get_level_by_experience(self) -> int:
        return get_level_by_experience(self.total_experience)

    def set_initial_stats(self):
        """Stats for a new hero: level 1, with the name applied (LoadStats), and full HP and MP. LoadStats also works
        out the attack and defense power, which depend on the name through strength and agility. Run again once the
        name is chosen, so nothing is left over from the placeholder name; loading a game doesn't come through here,
        so a saved game keeps its saved HP and MP."""
        self.set_stats_by_level(1)
        self.update_attack_power()
        self.update_defense_power()
        self.restore_hp()
        self.restore_mp()

    def update_stats_to_current_level(self):
        self.set_stats_by_level(self.level)

    def set_stats_by_level(self, level):
        """NES LoadStats (LF050): the stats come from BaseStatsTbl for the level and the first four letters of the
        name, worked out afresh each time, so a saved game only needs the name and the experience."""
        self.update_stats_by_level(level)
        for i in range(1, level + 1):
            if levels_list[i].get('spell'):
                if levels_list[i]['spell'] not in self.spells:
                    self.spells.append(levels_list[i]['spell'])

    def update_stats_by_level(self, level: int | None = None):
        stats = get_stats_for_level(self.name, self.level if level is None else level)
        self.strength = stats['strength']
        self.agility = stats['agility']
        self.max_hp = stats['max_hp']
        self.max_mp = stats['max_mp']

    def restore_hp(self):
        self.current_hp = self.max_hp

    def restore_mp(self):
        self.current_mp = self.max_mp
