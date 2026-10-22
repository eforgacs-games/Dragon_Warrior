# Static menu images: inventory and conversion plan

These are the NES screenshots and window images in `data/images` that the game draws as menus, windows or screens. We are replacing them with windows generated from the NES window data (`src/windows.py`, `src/window_renderer.py`).

**The rule:** a screenshot may be replaced only once the generated version matches it with **0 differing pixels**, at every scale (`tests/nes_screen_diff.py`). The screenshots stay in the repo as test references.

Window data labels are from Bank01 `WndwDataPtrTbl`. Line numbers are as of this document's commit.

## How a screenshot is checked

- `tests/nes_screen_diff.py` `compare_with_screenshot(generated, screenshot, nes_pixel, window_color, area, diff_dir, name)`:
  - counts the differing pixels;
  - saves a diff image (screenshot | generated | differences in magenta) when any pixel differs.
- Its only colour mapping is explicit and exact: the screenshots' white (255, 254, 255) becomes `WHITE`. Nothing else is mapped, and there is no tolerance.
- The low-HP red variant is derived from a screenshot by replacing `WHITE` with the window colour, exactly the NES palette swap.
- `tests/test_generated_windows.py` `TestTileVocabulary` checks one screenshot of every family below: each 8x8 tile must be one the renderer can draw (a border tile, the cursor, `TL_NAME_PLACEHOLDER` or a font tile). **Every family passes.** So every window screenshot is made only of tiles we have; what remains is layout and content.

## Battle (5 files): done in phase 1

| File(s) | Used at | Shows | NES window | Variants | Status |
|---|---|---|---|---|---|
| `menus/battle_menu/battle_menu_static.png` | test reference only | COMMAND title, FIGHT/SPELL, RUN/ITEM, no cursor. 128x48 (8x3 blocks) | CmdCmbtDat ($B095) | cursor hidden / none | **generated**: `COMBAT_COMMAND_LAYOUT` |
| `menus/battle_menu/battle_menu_{fight,spell,run,item}.png` | test reference only | the same window, with the arrow at each command | CmdCmbtDat ($B095) | 4 cursor positions | **generated** |

The game now draws this window with `draw_window(..., COMBAT_COMMAND_LAYOUT, ...)` in three places:
- `BattleController.draw_command_window`;
- `Battle.display_battle_window`;
- `Game.handle_death`.

## Title, main menu and adventure logs (18 files): don't convert yet

Other work is changing these screens: the options screen, message speed, and save slots and logs (#234).

All of them are full 256x240 screenshots: white windows on black. `GameFunctions.main_menu_selection` (`src/game_functions.py:40`) swaps between the image with the arrow at entry N and the `-1_unselected` image, which is how the cursor blinks.

| File(s) | Used at | NES window(s) | Variants | Difficulty |
|---|---|---|---|---|
| `menus/main_menu/empty_log/{-1_unselected,0_begin_quest}.png` (2) | `Game.show_main_menu_screen` (`src/game.py` ~245) | NewQuestDat ($B2A8) | hidden / entry 0 | easy |
| `menus/main_menu/partially_full_log/{-1_unselected,0..4}.png` (6) | `show_main_menu_screen` (~259) | FullMenuDat ($B249) | hidden + 5 | easy |
| `menus/main_menu/full_log/{-1_unselected,0..2}.png` (4) | `show_main_menu_screen` (~276) | ContChngErsDat ($B20B) | hidden + 3 | easy |
| `menus/main_menu/empty_log/adventure_log/{-1_unselected,0..2}.png` (4) | `copy_quest`, `erase_quest`, `select_adventure_log` (`src/game.py` ~347-384) | NewQuestDat ($B2A8), with its arrow held on, + LogList123Dat1 ($B385) | hidden + 3 | medium (2 windows) |
| `menus/main_menu/partially_full_log/one_adventure_log/{-1_unselected,0_adventure_log_1}.png` (2) | `Game.continue_quest` (~310), with `AdventureLogOverlay` drawing the name | FullMenuDat ($B249) + LogList1Dat2 ($B3BF) | hidden / on | medium (name and level from the save) |

Things the NES does differently from these screens:
- Copy, erase and log selection always show the empty-log screenshot, with all 3 logs listed.
- On the NES, those flows list only the used logs (or only the free ones) with the matching LogList??Dat1/Dat2 window. Erase also shows EraseLogDat ($B4D4).
- There are no screenshots for MsgSpeedDat, YesNo2Dat or the 2-log variants.

Generating these screens will fix all of that, because any LogList variant can be built from its data.

## Name entry (72 files)

| File(s) | Used at | NES window(s) | Variants | Difficulty |
|---|---|---|---|---|
| `menus/name_selection/0_upper_A.png` … `62_END.png` (63) | `NameSelection` lookup (`src/menu_functions.py:34-96`), `blink_with_name`, `draw_image_with_name`, `toggle_joystick_input` | NewQuestDat + LogList123Dat1 behind, AlphabetDat ($B10D) + NameEntryDat ($B1F7), composed full screen | 63 cursor positions | medium |
| `menus/name_selection/63_static_image_len_0.png` … `71_static_image_len_8.png` (9) | `select_name` (`menu_functions.py:106`, `:114-124`) | same | name length 0-8 (placeholders `TL_NAME_PLACEHOLDER` $41, the underline is TL_TOP1) | medium |

Notes:
- The cursor images always show an empty name. The typed name is drawn over them, off the tile grid (`TILE_SIZE*6.01, TILE_SIZE*4.3`, `menu_functions.py:251`).
- The windows behind are always the "3 free logs" variant.
- The NES alphabet uses the NES j, k, p, t and apostrophe. The TTF font doesn't have them, so they are in `NES_GLYPHS` (see below).

## Shops (40 files)

| File(s) | Used at | NES window | Variants | Difficulty |
|---|---|---|---|---|
| `shops/<town>/weapons/<town>_shop.png` (6: Brecconary, Garinham, Kol, Rimuldar, Cantlin north and south) | `data/text/dialog_lookup_table.py` `check_buy_weapons_armor` → `open_store_inventory` (`create_window` ~870, with the NES cursor drawn over it) | ShopInvDat ($B0DA), variable height | one per shop, 4-7 items | medium (item names in two halves, right-aligned prices; must match `src/shops.py`) |
| `shops/<town>/weapons/<town>_shop_<item>.png` (34) | **never drawn**: `'menu_image'` in `src/shops.py:44-134`, only checked for presence (`dialog_lookup_table.py` ~853) | ShopInvDat ($B0DA) | arrow at each item | medium |

The item shops already draw ShopInvDat as text on a nine-sliced background (`select_shop_item`), so only the weapon/armor shops still use screenshots.

## Miscellaneous (23 files)

| File(s) | Used at | NES window | Difficulty |
|---|---|---|---|
| `dialog_box_background.png` (192x80) | `CommandMenu.draw_dialog_window` (`src/menu.py` ~401) | DialogDat ($B04B) | easy (border only) |
| `command_menu_static.png` (128x80) | `refresh_window_color` (`menu.py` ~188), redrawn during the drop-up | CmdNonCmbtDat ($B054) | easy |
| `command_menu_background.png` | **unused** | CmdNonCmbtDat border | easy |
| `confirmation.png` (64x48) | `data/text/dialog.py:17`, `CommandMenu.draw_yes_no_window` (`menu.py` ~645) | YesNo1Dat ($B0EB); YesNo2Dat ($B50D) is the same window elsewhere | easy |
| `confirmation_yes.png`, `confirmation_no.png` | test reference (`tests/test_cursor.py`) / **unused** | YesNo1Dat ($B0EB) | easy |
| `hovering_stats_window.png` (64x96) | `Drawer.draw_hovering_stats_window` (`src/drawer.py:111`) | PopupDat ($AFB0) | easy (name in the top border; values) |
| `status_window_background.png` (160x176) | `CommandMenu.draw_status_window` (`menu.py` ~1120) | StatusDat ($AFC7) | easy |
| `menus/item_menu/item_menu_background_5.png` | nine-sliced: `draw_item_menu`, the COMMAND frame, `draw_window_background` | border of SpellDat ($B0BA), PlayerInvDat ($B0CC), ShopInvDat, BuySellDat ($B0FB)… | easy (border only) |
| `menus/item_menu/item_menu_background_{1,2}.png` | **unused** (`item_menu_background_lookup` is never read) | SpellDat / PlayerInvDat | easy |
| `intro_banner/intro_banner.png`, `intro_banner_with_dragon.png` (248x92) | `Intro.show_start_screen`, `show_intro_dragon_banner_with_text` (`src/intro.py:42`, `:60`) | title screen art, not a window | hard |
| `intro_banner/sparkle/*_{1..8}.png` (8) | `Intro.banner_sparkle` (`intro.py` ~100) | title screen art | hard |
| `title_menu.png` (504x142) | **unused** | not NES resolution | n/a |
| `nes-font.png` (464x8) | **unused** | an uppercase font strip | n/a |

## Counts

| Group | Files | Drawn by the game (before this PR) | Unused or test-only |
|---|---|---|---|
| Battle | 5 | 2 (now 0) | 3, now 5 |
| Title, main menu and adventure logs | 18 | 18 | 0 |
| Name entry | 72 | 72 | 0 |
| Shops | 40 | 6 | 34 |
| Miscellaneous | 23 | 15 | 8 |
| **Total** | **158** | **113** | **45** |

## Phase 2 plan

1. **Miscellaneous windows: easy.**
   - These are single fixed windows: dialog, COMMAND, YES/NO, popup stats, status and the SPELL/ITEM border.
   - Each needs a `WindowLayout` from its window data, plus its dynamic text (values, name).
   - Any window whose border is now nine-sliced from `item_menu_background_5.png` can use `render_window` with no text.
2. **Shops: medium.**
   - Write a ShopInvDat layout builder: the variable height, two-half item names (`name_halves`) and costs right-aligned at `SHOP_COST_RIGHT_TILE_COLUMN`.
   - Diff it against the 6 shop screenshots, and against the per-item arrow images.
3. **Name entry: medium.**
   - This is a composite of 4 windows: NewQuestDat, LogList123Dat1, AlphabetDat and NameEntryDat, drawn in NES order on black.
   - AlphabetDat's layout (a 3-tile column spacing) and the name underline (TL_TOP1 under the selected slot, LAEB8) are new.
   - Every tile it needs is already known.
4. **Title, main menu and adventure logs: easy to medium, but blocked** until the options screen and #234 land.
   - These are 1-2 windows each. The log list windows have 7 variants each.
5. **Intro banner: hard. Leave it as an image.**
   - It is title art made of sprites and background tiles in other palettes (grey, orange), not window tiles.
   - It could be reproduced only from the CHR ROM and the title screen nametable. Neither is in the repo nor in the disassembly.

## What may not be reproducible exactly

- **The font.**
  - `data/fonts/dragon-quest.ttf` at 8 px is pixel-exact for every character except **j, k, p, t** and the **apostrophe**. Those come from `NES_GLYPHS` in `src/window_renderer.py`, copied from two independent screenshots that agree.
  - Any other character missing from the screenshots can't be verified. The disassembly has no CHR data.
  - The game's own `draw_text` still uses the TTF, so dialog text currently shows the wrong j, k, p, t and `'`.
- **Korean.** Translated text (unifont) has no NES reference, so it can only be generated, never diffed. The screenshots are English only.
- **The intro banner and sparkle frames:** see Phase 2, item 5.
- **Screens that never existed as screenshots** (MsgSpeedDat, YesNo2Dat, the LogList Dat2 variants):
  - We can only check them tile by tile against the window data, not against an image.
  - A real NES capture would be needed to add a reference.
