# Third-party assets

This is an unofficial fan project. It is not affiliated with, endorsed by or sponsored by Square Enix or Nintendo.
*Dragon Warrior* and *Dragon Quest* are trademarks of Square Enix. *Dragon Quest* was published by Enix (now Square
Enix) and developed by Chunsoft, with music by Koichi Sugiyama; the NES version, *Dragon Warrior*, was published in
North America by Nintendo.

## What the GPL covers

The [GNU General Public License v3.0 or later](LICENSE) covers only this project's own source code: the Python in
`src/`, `tests/`, `tools/`, `data/text/*.py` (apart from the game text they contain) and
`reference/reference_utility_scripts/`, along with the build and project files.

The files listed below are **not** covered by the GPL. They belong to their owners and are used under those owners'
terms. Where a file's source couldn't be traced, it says "source unknown".

## Dragon Warrior / Dragon Quest game material (Square Enix)

Owned by Square Enix (formerly Enix). Taken or derived from the games.

| Path | What it is | Source |
|---|---|---|
| `data/images/` (all files, including `enemies/`, `intro_banner/`, `menus/`, `shops/`, `tileset.png`, `nes-font.png`, `walking_hero.gif`) | NES sprites, tilesets, the title banner, menu and shop screens and the NES font sheet | Ripped from the NES game; who made the rips is unknown |
| `data/sound/music/NES/` | NES soundtrack (16 tracks) | Recordings of the NES game's music; source of the rips unknown |
| `data/sound/sfx/*.mp3` | NES jingles and sound effects (tracks 17-46) | Recordings of the NES game; source of the rips unknown |
| `data/sound/sfx/text_beep.wav`, `data/sound/sfx/radiant.wav` | The text and RADIANT sounds | Synthesized by this project's scripts (`reference/reference_utility_scripts/make_text_beep.py`, `tools/make_radiant_sfx.py`) from the NES game's sound data |
| `data/text/dialog_lookup_table.py`, `data/text/intro_lookup_table.py`, `data/text/dialog.py`, `data/text/locales/base.pot`, `data/text/locales/en/` | The NES game's English text (dialog, menus, item, spell and monster names), embedded in the code and in the message catalogs | The NES game |
| `src/map_layouts.py`, `tests/nes_map_data.py`, `tests/nes_maps.py`, and the stat, item, spell and monster tables in `src/` | Maps, NPC placements and game data | Derived from the NES game's data (largely via the [nmikstas disassembly](https://github.com/nmikstas/dragon-warrior-disassembly), which has no license) |
| `data/text/official_script/` (`en.json`, `ja.json`, `ko.json`, `zh1.json`, `zh2.json`, `script.tsv`) | The script of Square Enix's 2014 smartphone *DRAGON QUEST*, in five languages | Extracted from the Android app (see its [README](data/text/official_script/README.md)) |
| `data/text/official_script/glossary_ko.tsv`, the names and terms in `data/text/locales/ko/` | Korean names and terms | Taken from the official Korean script above |

## Orchestral and Super Famicom recordings

Owned by Square Enix and the respective rights holders (composer Koichi Sugiyama, the performers and the record labels).

| Path | What it is | Used by the game |
|---|---|---|
| `data/sound/music/orchestra/01`-`08` | *Symphonic Suite Dragon Quest* performed by the London Philharmonic Orchestra | Yes, with the ORCHESTRA music option |
| `data/sound/music/orchestra/09 Overture March (Original Game Sound).mp3` | The overture in its original game sound version | No |
| `data/sound/music/orchestra/10`-`18` and `data/sound/music/orchestra/SFC/` (the same nine files) | Super Famicom (*Dragon Quest I & II*) versions of the soundtrack | No |
| `data/sound/music/orchestra/Android_iOS/Dragon Quest (Android_iOS) - Intermezzo.mp3` | Intermezzo from the 2014 smartphone version | Yes, with the ORCHESTRA music option |

The source of these rips is unknown.

<!-- NSF / SPC / libgme: if the NES and SFC music moves to NSF/SPC files played through libgme, list those files here
     (they are still Square Enix's music) and add libgme under "Libraries" with its license. -->

## Fonts (`data/fonts/`)

From each font's name table (read with fontTools):

| File | Font | Copyright and license in the file | Used by the game |
|---|---|---|---|
| `dragon-quest.ttf` | "Dragon Quest" by Dale Thiessen (gnarizard), made with FontStruct: <https://fontstruct.com/fontstructions/show/919302/dragon_quest_1> | "Copyright Dale Thiessen 2013", FontStruct Non-Commercial License | Yes: the NES-style font for English text |
| `super_mario_bros__nes_font.ttf` | "Super Mario Bros. NES" by TheWolfBunny, made with FontStruct, based on "Arcade Classic" and "KonaM" by igorcbarros: <https://fontstruct.com/fontstructions/show/1332355/arcade-classic-2-19> | "Copyright TheWolfBunny 2016", Open Font License | Yes: the "(↑ ← ↓ →)" line on the title screen |
| `unifont.ttf` | GNU Unifont, a 2008 TrueType build ("FontForge 2.0 : GNU Unifont : 7-9-2008") | No copyright or license string in the file. GNU Unifont is distributed under the GNU GPL v2 or later with the GNU font embedding exception; the SIL Open Font License 1.1 option was only added in later releases (13.0.04) | Yes: Korean and other text the NES font lacks |
| `Knigqst.ttf` | "Knights Quest" 1.02 | "©GemFonts98"; no license given; source unknown | No (but bundled in the release builds, which include all of `data/fonts/`) |

## Libraries

Used by the game at runtime (`pyproject.toml` dependencies):

- [pygame](https://www.pygame.org/) and the SDL libraries it bundles: GNU LGPL v2.1.

Release builds are made with [PyInstaller](https://pyinstaller.org/) (GPL v2 or later with an exception for the
bootloader it adds to the built program). The development tools (pytest, ruff, mypy, pre-commit) aren't distributed
with the game.

## `reference/`

Notes and documents by other authors, kept for development. Each is under its own author's terms:

| Path | What it is | Author and terms |
|---|---|---|
| `reference/sram-doc.txt` | Dragon Warrior SRAM (save) format | John David Ratliff / emuWorks, 2007, GNU Free Documentation License 1.2 or later |
| `reference/DragonWarriorFormulas.txt` | Dragon Warrior (NES) Formulas v1.0 | Ryan8bit, 2011; no license given |
| `reference/dwbytes.txt` | Dragon Warrior Bytes v1.0 (RAM/ROM addresses) | Sliver X; no license given |
| `reference/names_stats_and_levels.txt` | Names, Stats, and Levels for Dragon Warrior (GameFAQs) | Akira Speirs, 2002, "All rights reserved" |
| `reference/raw_levels_lists/`, `reference/converted_levels_lists/` | Level-up stat tables, by name group | Game data; source of the tables unknown |
| `reference/reference_images/` | Screenshots, maps and tiles from the NES game (Square Enix) | Collected from various websites; sources unknown |
