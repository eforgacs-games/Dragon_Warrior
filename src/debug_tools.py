"""
Debug keys for playtesting, only on with the dev config (DEBUG_KEYS):
- F5: warp to the entrance of any map.
- F6: give an item, gold, Erdrick's gear or a level, or refill HP and MP.
- F7: load a playtest checkpoint (src/checkpoints.py).

Each opens a small list: type to filter it, ↑/↓ to choose, Enter to pick, Esc to close.
"""
from typing import Callable, Sequence

from pygame import KEYDOWN, K_BACKSPACE, K_DOWN, K_ESCAPE, K_F5, K_F6, K_F7, K_KP_ENTER, K_RETURN, K_UP, QUIT, \
    Rect, display, draw, event
from pygame.time import Clock

from src.checkpoints import CHECKPOINT_NAMES
from src.color import BLACK, WHITE
from src.constants import RETURN_DESTINATION
from src.items import MAX_GOLD, MAX_HERBS, MAX_KEYS
from src.maps import map_lookup
from src.player.player_stats import levels_list
from src.text import draw_text

# Items that F6 can give, key items first
GIVABLE_ITEMS = ("Magic Key", "Silver Harp", "Stones of Sunlight", "Staff of Rain", "Erdrick's Token", "Rainbow Drop",
                 "Gwaelin's Love", "Fairy Flute", "Herb", "Torch", "Wings", "Fairy Water", "Dragon's Scale",
                 "Fighter's Ring")
ITEM_LIMITS = {"Magic Key": MAX_KEYS, "Herb": MAX_HERBS}
# Consumables can be carried more than once; any other item only once
STACKABLE_ITEMS = ("Magic Key", "Herb", "Torch", "Wings", "Fairy Water")
GOLD_STEP = 1000
ERDRICKS_GEAR = ("Erdrick's Sword", "Erdrick's Armor", "Silver Shield")

REFILL = "Refill HP and MP"
ADD_GOLD = f"Add {GOLD_STEP} gold"
SET_LEVEL = "Set level..."
EQUIP_ERDRICK = "Equip Erdrick's gear"

VISIBLE_ROWS = 16
LINE_HEIGHT = 22


class DebugTools:
    def __init__(self, game) -> None:
        self.game = game
        self._entrances: dict[str, tuple[int, int]] | None = None

    def handle_keydown(self, keydown_event) -> None:
        actions: dict[int, Callable[[], None]] = {K_F5: self.warp_menu, K_F6: self.give_menu, K_F7: self.checkpoint_menu}
        action = actions.get(keydown_event.key)
        if action is None or self.game.cmd_menu.menu.is_enabled():
            return
        self.game.player.is_moving = False
        action()
        event.clear(KEYDOWN)  # keys pressed in the list shouldn't also move the hero or open the command menu

    # Warp

    @property
    def warp_maps(self) -> list[str]:
        """Every map that can be loaded (map_lookup also holds the base classes, which have no layout)."""
        return sorted(name for name in map_lookup if name in self.game.layouts.map_layout_lookup)

    def entrance(self, map_name: str) -> tuple[int, int]:
        """Where a warp lands: outside Tantegel on the overworld, where the overworld entrance leads for towns and
        caves, and the map's own starting tile (the stairs down to it) for everything else."""
        if map_name == 'Alefgard':
            return RETURN_DESTINATION[1]
        if self._entrances is None:
            self._entrances = {}
            for staircase in map_lookup['Alefgard'](self.game.config).staircases.values():
                self._entrances.setdefault(staircase['map'], staircase['destination_coordinates'])
        if map_name in self._entrances:
            return self._entrances[map_name]
        return map_lookup[map_name](self.game.config).initial_coordinates

    def warp(self, map_name: str) -> None:
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=self.entrance(map_name))

    def warp_menu(self) -> None:
        map_name = self.pick("Warp to", self.warp_maps)
        if map_name:
            self.warp(map_name)

    # Give

    def give_options(self) -> list[str]:
        return [REFILL, ADD_GOLD, SET_LEVEL, EQUIP_ERDRICK] + [f"Give {item}" for item in GIVABLE_ITEMS]

    def give(self, option: str) -> str:
        """Do what the F6 option says. Returns what happened, to show."""
        player = self.game.player
        if option == REFILL:
            player.restore_hp()
            player.restore_mp()
            return "HP and MP restored."
        if option == ADD_GOLD:
            player.gold = min(player.gold + GOLD_STEP, MAX_GOLD)
            return f"Gold: {player.gold}"
        if option == EQUIP_ERDRICK:
            player.weapon, player.armor, player.shield = ERDRICKS_GEAR
            player.update_attack_power()
            player.update_defense_power()
            return "Erdrick's gear equipped."
        item = option.removeprefix("Give ")
        if item not in GIVABLE_ITEMS:
            raise ValueError(f"Unknown option {option!r}")
        return self.give_item(item)

    def give_item(self, item: str) -> str:
        inventory = self.game.player.inventory
        if item in ITEM_LIMITS and inventory.count(item) >= ITEM_LIMITS[item]:
            return f"Already carrying {ITEM_LIMITS[item]} of {item}."
        if item not in STACKABLE_ITEMS and item in inventory:
            return f"Already carrying {item}."
        inventory.append(item)
        return f"Got {item}."

    def set_level(self, level: int) -> str:
        player = self.game.player
        player.total_experience = levels_list[level]['total_exp']
        player.level = level
        player.update_stats_to_current_level()  # also teaches the spells up to this level
        player.update_attack_power()
        player.update_defense_power()
        player.restore_hp()
        player.restore_mp()
        return f"Level {level}"

    def give_menu(self) -> None:
        option = self.pick("Give", self.give_options())
        if not option:
            return
        if option == SET_LEVEL:
            level = self.pick("Level", [str(level) for level in levels_list])
            if not level:
                return
            message = self.set_level(int(level))
        else:
            message = self.give(option)
        self.game.draw_temporary_text(message)

    # Checkpoints

    def checkpoint_menu(self) -> None:
        name = self.pick("Load checkpoint", list(CHECKPOINT_NAMES))
        if name:
            self.game.load_checkpoint(name)

    # The list window

    @staticmethod
    def filter_options(options: Sequence[str], query: str) -> list[str]:
        return [option for option in options if query.lower() in option.lower()]

    def pick(self, title: str, options: Sequence[str]) -> str | None:
        """Show a list until an option is picked (returned) or the list is closed (None)."""
        query, index = "", 0
        matches = list(options)
        clock = Clock()
        while True:
            self.draw_list(title, query, matches, index)
            for current_event in event.get():
                if current_event.type == QUIT:
                    event.post(current_event)  # let the game loop close the game
                    return None
                if current_event.type != KEYDOWN:
                    continue
                if current_event.key == K_ESCAPE:
                    return None
                if current_event.key in (K_RETURN, K_KP_ENTER):
                    if matches:
                        return matches[index]
                elif current_event.key == K_UP and matches:
                    index = (index - 1) % len(matches)
                elif current_event.key == K_DOWN and matches:
                    index = (index + 1) % len(matches)
                elif current_event.key == K_BACKSPACE:
                    query, index = query[:-1], 0
                elif current_event.unicode and current_event.unicode.isprintable():
                    query, index = query + current_event.unicode, 0
                matches = self.filter_options(options, query)
            clock.tick(30)

    def draw_list(self, title: str, query: str, matches: list[str], index: int) -> None:
        screen = self.game.screen
        config = self.game.config
        tile_size = self.game.tile_size
        window = Rect(tile_size // 2, tile_size // 2, screen.get_width() - tile_size, screen.get_height() - tile_size)
        screen.fill(BLACK, window)
        draw.rect(screen, WHITE, window, 2)
        x, y = window.x + tile_size // 2, window.y + tile_size // 3
        header = f"{title}: {query}_" if query else f"{title} (type to filter)"
        draw_text(header, x, y, screen, config, letter_by_letter=False, text_wrap_length=40, disable_sound=True)
        first = max(0, min(index - VISIBLE_ROWS // 2, len(matches) - VISIBLE_ROWS))
        for row, option in enumerate(matches[first:first + VISIBLE_ROWS]):
            marker = ">" if first + row == index else " "
            draw_text(f"{marker} {option}", x, y + (row + 2) * LINE_HEIGHT, screen, config, letter_by_letter=False,
                      text_wrap_length=40, disable_sound=True)
        if not matches:
            draw_text("(no match)", x, y + 2 * LINE_HEIGHT, screen, config, letter_by_letter=False,
                      text_wrap_length=40, disable_sound=True)
        draw_text("Up/Down, Enter: pick  Esc: close", x, window.bottom - tile_size, screen, config,
                  letter_by_letter=False, text_wrap_length=40, disable_sound=True)
        display.flip()
