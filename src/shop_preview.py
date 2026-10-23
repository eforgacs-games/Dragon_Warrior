"""The shop stat preview (SHOP PREVIEW in the options overlay, SHOP_PREVIEW in the config). Not on the NES.

While the hero browses a weapon and armor shop's list (NES ShopInvDat, DialogLookup.select_shop_item), a small window
in the top left corner of the screen shows what the highlighted item would make the hero's attack power (a weapon)
or defense power (armor or a shield), with the NES formulas (Player.attack_power_with, Player.defense_power_with):

    +----------+
    | ATTACK   |
    | 12→20    |
    +----------+

Now on the left of the arrow, with the item on the right; it follows the shop's cursor, and it goes when the list
does. It's only information: the shop's windows, their layout and the shop's flow are the NES's whether it's on or off.

The window is 6 blocks wide and 2 high at block (0, 0): above the pop-up status window (POPUP_WINDOW, from block row
2) and left of the COMMAND window (COMMAND_WINDOW, from block column 6), the only place no NES window covers while a
shop's list is open. It's laid out like the status window: single spaced, the text after a blank tile. The NES font has
no arrow, so in English the arrow is drawn as a tile of its own (RIGHT_ARROW); translated text is drawn in Unifont,
which has one (src/translated_window.py).
"""
from collections.abc import Callable
from typing import NamedTuple

from pygame import Rect, Surface

from src.translated_window import draw_translated_window
from src.window_renderer import draw_window, tile_surface
from src.windows import Window, WindowLayout, WindowText

SHOP_PREVIEW_WINDOW = Window(0, 0, 6, 2)
PREVIEW_TEXT_COLUMN = 2
LABEL_ROW = 1
NUMBERS_ROW = 2

ATTACK_LABEL = "ATTACK"
DEFENSE_LABEL = "DEFENSE"
ARROW = "→"

# Not an NES tile: an arrow in the NES font's style (2 pixel strokes, a blank row at the top and bottom)
RIGHT_ARROW = (
    "........",
    "....#...",
    "....##..",
    ".######.",
    ".######.",
    "....##..",
    "....#...",
    "........",
)


class StatPreview(NamedTuple):
    """The stat the item changes (ATTACK_LABEL or DEFENSE_LABEL), the hero's now, and the hero's with the item."""
    label: str
    now: int
    with_item: int


def stat_preview(player, item_name: str, item_type: str) -> StatPreview | None:
    """What the item would make the hero's attack or defense power, if it were equipped in place of the hero's
    weapon, armor or shield (an item the hero has equipped changes nothing). None for anything else (a tool)."""
    if item_type == 'weapon':
        return StatPreview(ATTACK_LABEL, player.attack_power_with(player.weapon), player.attack_power_with(item_name))
    now = player.defense_power_with(player.armor, player.shield)
    if item_type == 'armor':
        return StatPreview(DEFENSE_LABEL, now, player.defense_power_with(item_name, player.shield))
    if item_type == 'shield':
        return StatPreview(DEFENSE_LABEL, now, player.defense_power_with(player.armor, item_name))
    return None


def preview_layout(preview: StatPreview) -> WindowLayout:
    """The window, with the label on the first row and "now→with the item" on the second."""
    return WindowLayout(window=SHOP_PREVIEW_WINDOW, texts=(
        WindowText(preview.label, PREVIEW_TEXT_COLUMN, LABEL_ROW),
        WindowText(f"{preview.now}{ARROW}{preview.with_item}", PREVIEW_TEXT_COLUMN, NUMBERS_ROW)))


def draw_shop_preview(screen: Surface, preview: StatPreview, color: tuple, config: dict,
                      translate: Callable[[str], str]) -> Rect:
    """Draw the window (nothing with NO_BLIT). Returns its rect on the screen, for display.update."""
    layout = preview_layout(preview)
    if translate(preview.label) != preview.label:
        return draw_translated_window(screen, layout, color, config, translate)
    numbers = layout.texts[1]
    rect = draw_window(screen, layout._replace(texts=(layout.texts[0], numbers._replace(
        text=numbers.text.replace(ARROW, ' ')))), color, config)
    if not config.get('NO_BLIT'):
        nes_pixel = config['TILE_SIZE'] // 16
        nes_tile = 8 * nes_pixel
        column = SHOP_PREVIEW_WINDOW.x * 2 + numbers.column + numbers.text.index(ARROW)
        row = SHOP_PREVIEW_WINDOW.y * 2 + numbers.row
        screen.blit(tile_surface(RIGHT_ARROW, color, nes_pixel), (column * nes_tile, row * nes_tile))
    return rect


def preview_texts() -> list[str]:
    """The window's text to translate, for the translation catalog (catalog_tools.dynamic_messages)."""
    return [ATTACK_LABEL, DEFENSE_LABEL]
