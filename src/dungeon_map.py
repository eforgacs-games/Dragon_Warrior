"""The dungeon map (#408): a map of the dark dungeons that fills in as the hero explores. Not NES.

Recording (DungeonMap.see, from Game.map_frame): on a dark map (DragonWarriorMap.is_dark: the caves, Garin's Grave,
the Dragonlord's castle below its ground floor), every block the light shows is marked seen on that floor, each
frame: the square of lit_diameter blocks around the hero (src/game_state.py; 1 without a torch, up to 7 with RADIANT).
Each floor (map) keeps its own record, as a bit per block of its layout.

Keeping it: the record goes with the adventure log (SAVE_KEY in the save file, src/save_file.py) and with save states
and the rewind (src/save_state.py), so it is what the hero has seen in that game. A new quest starts with none.

Showing it (DungeonMapOverlay): M on a dark map, when START would pause the game, with the DUNGEON MAP option ON
(the options overlay; DUNGEON_MAP in the config, kept with the global settings, src/settings.py). Like the options
overlay it waits for the hero and the NPCs to finish their steps, then runs its own loop over the darkened map
frame: a window titled MAP with this floor's seen blocks, one small square each, the stairs in their own colours,
and the hero blinking where he stands. M, B, Esc, SELECT or Tab close it, and the map frame is put back exactly as it
was. Off (NES), M does nothing; the record is kept all the same, so turning it on shows everything seen before.
"""
import base64
from collections.abc import Callable

from pygame import K_ESCAPE, KEYDOWN, SRCALPHA, Rect, Surface, display

from src.color import BLACK
from src.common import B_BUTTON_KEYS, SELECT_BUTTON_KEYS, set_gettext_language
from src.controls import KeySet
from src.cursor import BlinkingCursor
from src.selection import frame_events, next_frame
from src.translated_window import draw_translated_window
from src.windows import Window, WindowLayout, WindowText

DUNGEON_MAP_KEYS = KeySet('MAP')  # M, as bound (src/controls.py)
CLOSE_KEYS = DUNGEON_MAP_KEYS + B_BUTTON_KEYS + SELECT_BUTTON_KEYS + (K_ESCAPE,)
SAVE_KEY = 'DungeonMap'
DEFAULT_DUNGEON_MAP = True  # DUNGEON_MAP: ON; OFF is the NES

# How dark the map gets behind the window, as the options overlay
OVERLAY_ALPHA = 160
# The window: 14 blocks wide and 13 high from block (1, 1), the title in the top border like OPTIONS
MAP_WINDOW = Window(1, 1, 14, 13)
MAP_TITLE = WindowText("MAP", 4, 0)
# A block on the map is at most this many NES pixels square, and smaller if the floor needs it to fit
MAX_BLOCK_PIXELS = 6
# The colours, NES palette colours: walls light grey ($10), floors dark grey ($00), stairs down light blue ($21), stairs
# up green ($2A), chests yellow ($28), doors orange ($27), and the hero red ($16)
WALL_COLOR = (188, 188, 188)
FLOOR_COLOR = (116, 116, 116)
STAIRS_DOWN_COLOR = (60, 188, 252)
STAIRS_UP_COLOR = (76, 220, 72)
CHEST_COLOR = (240, 188, 60)
DOOR_COLOR = (252, 116, 96)
HERO_COLOR = (228, 0, 88)
TILE_COLORS = {
    'WALL': WALL_COLOR, 'ROOF': WALL_COLOR, 'BRICK_STAIR_DOWN': STAIRS_DOWN_COLOR, 'BRICK_STAIR_UP': STAIRS_UP_COLOR,
    'TREASURE_BOX': CHEST_COLOR, 'DOOR': DOOR_COLOR,
}


class Floor:
    """One floor's record: a bit per block of its layout (rows x columns), set once the block has been seen."""

    def __init__(self, rows: int, columns: int, bits: bytearray | None = None) -> None:
        self.rows, self.columns = rows, columns
        size = (rows * columns + 7) // 8
        self.bits = bits if bits is not None and len(bits) == size else bytearray(size)

    def see(self, row: int, column: int) -> None:
        if 0 <= row < self.rows and 0 <= column < self.columns:
            index = row * self.columns + column
            self.bits[index >> 3] |= 1 << (index & 7)

    def seen(self, row: int, column: int) -> bool:
        if not (0 <= row < self.rows and 0 <= column < self.columns):
            return False
        index = row * self.columns + column
        return bool(self.bits[index >> 3] & (1 << (index & 7)))

    def seen_cells(self) -> list[tuple[int, int]]:
        return [(row, column) for row in range(self.rows) for column in range(self.columns) if self.seen(row, column)]

    def to_save(self) -> list:
        return [self.rows, self.columns, base64.b64encode(bytes(self.bits)).decode('ascii')]

    @classmethod
    def from_save(cls, saved) -> 'Floor':
        rows, columns, packed = saved
        rows, columns = int(rows), int(columns)
        if rows <= 0 or columns <= 0:
            raise ValueError("not a floor's size")
        return cls(rows, columns, bytearray(base64.b64decode(packed, validate=True)))


class DungeonMap:
    """What the hero has seen of each dark floor (see the module docstring)."""

    def __init__(self) -> None:
        self.floors: dict[str, Floor] = {}
        # The last (map, row, column, lit diameter) recorded, so standing still records nothing again
        self._last_seen: tuple | None = None

    def see(self, current_map, row: int, column: int, lit_diameter: int) -> None:
        """Mark the blocks the light shows around the hero at (row, column) seen, on a dark map."""
        if not current_map.is_dark:
            return
        seen = (current_map.identifier, row, column, lit_diameter)
        if seen == self._last_seen:
            return
        self._last_seen = seen
        floor = self.floor(current_map)
        radius = (max(1, lit_diameter) - 1) // 2
        for seen_row in range(row - radius, row + radius + 1):
            for seen_column in range(column - radius, column + radius + 1):
                floor.see(seen_row, seen_column)

    def floor(self, current_map) -> Floor:
        """The map's record, made empty the first time."""
        layout = current_map.layout
        floor = self.floors.get(current_map.identifier)
        if floor is None or (floor.rows, floor.columns) != (len(layout), len(layout[0])):
            floor = self.floors[current_map.identifier] = Floor(len(layout), len(layout[0]))
        return floor

    def to_save(self) -> dict[str, list]:
        return {map_name: floor.to_save() for map_name, floor in sorted(self.floors.items())}

    @classmethod
    def from_save(cls, saved) -> 'DungeonMap':
        """A saved record. Anything that can't be read (an older save has none) is left out: those floors start
        unexplored."""
        dungeon_map = cls()
        if isinstance(saved, dict):
            for map_name, floor in saved.items():
                try:
                    dungeon_map.floors[str(map_name)] = Floor.from_save(floor)
                except (TypeError, ValueError):
                    continue
        return dungeon_map

    def copy(self) -> 'DungeonMap':
        return DungeonMap.from_save(self.to_save())


def dungeon_map_enabled(config: dict) -> bool:
    return bool(config.get('DUNGEON_MAP', DEFAULT_DUNGEON_MAP))


def map_layout() -> WindowLayout:
    return WindowLayout(window=MAP_WINDOW, title=MAP_TITLE)


def block_pixels(floor: Floor, scale: int) -> int:
    """The size of a block on the map, in screen pixels: as big as fits in the window, MAX_BLOCK_PIXELS at most."""
    inner_width = (MAP_WINDOW.width * 16 - 16) * scale
    inner_height = (MAP_WINDOW.height * 16 - 16) * scale
    fits = min(inner_width // floor.columns, inner_height // floor.rows)
    return max(scale, min(MAX_BLOCK_PIXELS * scale, fits // scale * scale))


def draw_floor(screen: Surface, current_map, floor: Floor, hero: tuple[int, int], hero_visible: bool,
               scale: int, tile_size: int) -> Rect:
    """The floor's seen blocks, centred in the window, and the hero. Returns where the map is."""
    size = block_pixels(floor, scale)
    window_rect = Rect(MAP_WINDOW.x * tile_size, MAP_WINDOW.y * tile_size, MAP_WINDOW.width * tile_size,
                       MAP_WINDOW.height * tile_size)
    map_rect = Rect(0, 0, floor.columns * size, floor.rows * size)
    map_rect.center = window_rect.center
    layout = current_map.layout
    for row, column in floor.seen_cells():
        value = layout[row][column]
        tile = current_map.get_tile_by_value(value) if value < len(current_map.floor_tile_key) else None
        color = TILE_COLORS.get(tile, FLOOR_COLOR) if tile is not None else FLOOR_COLOR
        screen.fill(color, Rect(map_rect.x + column * size, map_rect.y + row * size, size, size))
    if hero_visible:
        row, column = hero
        screen.fill(HERO_COLOR, Rect(map_rect.x + column * size, map_rect.y + row * size, size, size))
    return map_rect


def darken(screen: Surface) -> None:
    shade = Surface(screen.get_size(), SRCALPHA)
    shade.fill((*BLACK, OVERLAY_ALPHA))
    screen.blit(shade, (0, 0))


def overlay_texts() -> list[str]:
    """Every text the window shows, for the translation catalog."""
    return [MAP_TITLE.text]


class DungeonMapOverlay:
    """The map over the dungeon, run until it's closed (see the module docstring)."""

    def __init__(self, game) -> None:
        self.game = game
        self.config: dict = game.game_state.config
        self._: Callable[[str], str] = set_gettext_language(self.config.get('LANGUAGE'))

    def run(self) -> None:
        screen = self.game.screen
        background = screen.copy()
        blink = BlinkingCursor()
        drawn: bool | None = None
        while True:
            visible = blink.visible()
            if visible != drawn:
                self.draw(background, visible)
                drawn = visible
            next_frame()
            for current_event in frame_events():
                if current_event.type == KEYDOWN and current_event.key in CLOSE_KEYS:
                    self.close(background)
                    return

    def draw(self, background: Surface, hero_visible: bool) -> None:
        """The map frame the overlay opened over, darkened, then the window and this floor."""
        if self.config.get('NO_BLIT'):
            return
        game = self.game
        screen = game.screen
        screen.blit(background, (0, 0))
        darken(screen)
        draw_translated_window(screen, map_layout(), game.color, self.config, self._)
        floor = game.dungeon_map.floor(game.current_map)
        draw_floor(screen, game.current_map, floor, (game.player.row, game.player.column), hero_visible,
                   self.config['SCALE'], self.config['TILE_SIZE'])
        display.update(Rect(0, 0, screen.get_width(), screen.get_height()))

    def close(self, background: Surface) -> None:
        if self.config.get('NO_BLIT'):
            return
        screen = self.game.screen
        screen.blit(background, (0, 0))
        display.update(Rect(0, 0, screen.get_width(), screen.get_height()))
