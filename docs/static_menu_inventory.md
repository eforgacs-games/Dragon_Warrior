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

## Shops (40 files): done in phase 2

| File(s) | Used at | Shows | NES window | Variants | Status |
|---|---|---|---|---|---|
| `shops/<town>/weapons/<town>_shop.png` (6: Brecconary, Garinham, Kol, Rimuldar, Cantlin north and south) | test reference only | the shop's stock, no cursor | ShopInvDat ($B0DA), variable height | one per shop, 4-7 items | **generated**: `shop_inventory_layout` |
| `shops/<town>/weapons/<town>_shop_<item>.png` (34) | test reference only (they were never drawn) | the same window, with the arrow at each item | ShopInvDat ($B0DA) | arrow at each item | **generated** |

`tests/test_generated_shop_windows.py` checks all 40 screenshots: every cursor position, the cursor blinked off and no cursor, at scales 1-3, in white and in red, plus what `open_store_inventory` draws on the game's screen. The screenshots' paths are no longer in `src/shops.py` (`'menu_image'`); the 6 shop screenshots stay in `Directories`, and each per-item one is found next to its shop's.

The game now draws ShopInvDat with `shop_inventory_layout` for **every** shop (`ShopItemsTbl`): the 7 weapon and armor shops, including Cantlin's guard (no screenshot; a 5-digit cost), and the 5 item shops, which drew it as text before. BuySellDat ($B0FB) is generated too (`BUY_SELL_LAYOUT`). It has no screenshot, but with YES and NO in place of BUY and SELL it is pixel-identical to `confirmation.png` and `confirmation_yes.png` (YesNo1Dat, the same window). In a translation (Korean) both are still drawn as text on a nine-sliced background, since the NES font has no Korean. The sell list is PlayerInvDat, the ITEM command's window (see Miscellaneous).

## Miscellaneous (23 files): windows done in phase 2

| File(s) | Used at | NES window | Status |
|---|---|---|---|
| `dialog_box_background.png` (192x80) | test reference only | DialogDat ($B04B) | **generated**: `DIALOG_LAYOUT`, drawn by `CommandMenu.draw_dialog_window` |
| `command_menu_static.png` (128x80) | `refresh_window_color` (`menu.py` ~188), redrawn during the drop-up | CmdNonCmbtDat ($B054) | not converted: the COMMAND window is being fixed separately |
| `command_menu_background.png` | **unused** | CmdNonCmbtDat border | not converted (COMMAND window) |
| `confirmation.png` (64x48) | test reference only | YesNo1Dat ($B0EB); YesNo2Dat ($B50D) is the same window elsewhere | **generated**: `YES_NO_LAYOUT` with no cursor (`data/text/dialog.py` `confirmation_prompt`), or with the cursor hidden |
| `confirmation_yes.png`, `confirmation_no.png` | test reference only | YesNo1Dat ($B0EB) | **generated**: `YES_NO_LAYOUT`, cursor 0 / 1, drawn by `CommandMenu.draw_yes_no_window` |
| `hovering_stats_window.png` (64x96) | test reference only | PopupDat ($AFB0) | **generated**: `POPUP_LAYOUT` (the labels, and TL_TOP2 before the name), drawn by `Drawer.draw_hovering_stats_window`; the name and the values are still drawn over it with `draw_text` |
| `status_window_background.png` (160x176) | test reference only | StatusDat ($AFC7) | **generated**: `STATUS_LAYOUT` (the labels), drawn by `CommandMenu.draw_status_window`; the values are still drawn over it with `draw_text` |
| `menus/item_menu/item_menu_background_5.png` | nine-sliced: the COMMAND frame (`refresh_window_color`) and `DialogLookup.draw_window_background` (BuySellDat, item shops) | border of SpellDat ($B0BA), PlayerInvDat ($B0CC), ShopInvDat, BuySellDat ($B0FB)… | **generated** for the SPELL and ITEM windows: `item_menu_layout`, drawn by `CommandMenu.draw_item_menu` (the SPELL title and the entries are still drawn over it). The two other uses are left to the COMMAND window fix and the shop conversion |
| `menus/item_menu/item_menu_background_{1,2}.png` | test reference only | SpellDat / PlayerInvDat at 1 and 2 entries | **generated**: `item_menu_layout` |
| `intro_banner/intro_banner.png`, `intro_banner_with_dragon.png` (248x92) | `Intro.show_start_screen`, `show_intro_dragon_banner_with_text` (`src/intro.py:42`, `:60`) | title screen art, not a window | hard |
| `intro_banner/sparkle/*_{1..8}.png` (8) | `Intro.banner_sparkle` (`intro.py` ~100) | title screen art | hard |
| `title_menu.png` (504x142) | **unused** | not NES resolution | n/a |
| `nes-font.png` (464x8) | **unused** | an uppercase font strip | n/a |

`tests/test_generated_windows.py` checks every generated window above against its screenshot: 0 differing pixels at scales 1, 2 and 3, white and low HP red, and again as the game draws it on its screen (with the dynamic text off).

The SPELL/ITEM border is verified at 1, 2 and 5 entries (the heights there are screenshots of); the other heights are the same tiles, but have no screenshot.

## Counts

| Group | Files | Drawn by the game (before this PR) | Unused or test-only |
|---|---|---|---|
| Battle | 5 | 2 (now 0) | 3, now 5 |
| Title, main menu and adventure logs | 18 | 18 | 0 |
| Name entry | 72 | 72 | 0 |
| Shops | 40 | 6 | 34 |
| Miscellaneous | 23 | 15 (now 11) | 8 (now 12) |
| **Total** | **158** | **113** (now 109) | **45** (now 49) |

## Phase 2 plan

1. **Miscellaneous windows: done**, except the COMMAND window (see the table above).
   - Dialog, YES/NO, popup stats, status and the SPELL/ITEM border are generated.
   - Their dynamic text (the name, the values, the dialog text, the SPELL title and the entries) is still drawn over them with `draw_text`, so it can be translated. Drawing it with NES tiles too is a possible next step.
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
