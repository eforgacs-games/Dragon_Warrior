# The player's ROM, and a free set of assets without it

A design for running the game on assets the player provides, written before any code. Not decided yet: this is a
proposal for after 1.x has settled, likely as 2.0.

Contents:

1. [Summary](#1-summary)
2. [Why](#2-why)
3. [What the game uses today](#3-what-the-game-uses-today)
4. [What the ROM can give, and what it can't](#4-what-the-rom-can-give-and-what-it-cant)
5. [Asset sets](#5-asset-sets)
6. [The ROM set](#6-the-rom-set)
7. [Text without the English as keys](#7-text-without-the-english-as-keys)
8. [The free set](#8-the-free-set)
9. [Tests and CI](#9-tests-and-ci)
10. [Removing the assets from the repository](#10-removing-the-assets-from-the-repository)
11. [Phased plan](#11-phased-plan)
12. [Open questions](#12-open-questions)

## 1. Summary

- **The repository and the downloads stop shipping Square Enix's material.** The game is this project's code,
  plus the files the player brings.
- **The player provides a *Dragon Warrior* NES ROM**, their own copy. On first start the game checks it and
  extracts what it needs (graphics, music, sound effects, the English text, maps and game data) to a folder next to
  the saves. From then on the game plays exactly as it does today: same formulas, same NES accuracy.
- **Without a ROM, the game runs on a free set**: original graphics, music, sound, text and maps under free
  licences, its own small adventure on the same engine. It's what CI tests, what a browser demo shows, and what a
  player sees before they've provided a ROM.
- **The game loads everything through asset sets**: one interface, three sources (the ROM, the free set, and for
  now the bundled files). The code doesn't care which one is in use.
- **The other soundtracks and the official translations become optional extras** the player points the game at
  (section 4).

Other projects have done this, and have lasted: DevilutionX (*Diablo*, needs `DIABDAT.MPQ`), Ship of Harkinian
(*Ocarina of Time*, needs the ROM), OpenMW (*Morrowind*). OpenTTD and Freedoom show the free set side: OpenTTD
ships free graphics, sound and music and uses the original game's when present; Freedoom is a complete free game
for any Doom engine.

## 2. Why

The game ships Square Enix's graphics, music and text today (see [ASSETS.md](../ASSETS.md)). A small GitHub project
is easy to leave alone. A game people play in their browser (#477), on itch.io (#439), on handhelds or on stream is
much more visible, and much more likely to get a takedown notice. Most of the post-1.0 ideas make the project more
visible, so this comes first.

This lowers the risk, it doesn't remove it. Nobody on this project is a lawyer; section 12 lists what's left.

## 3. What the game uses today

Everything is read from `data/` through `src/paths.py` (`data_path`) and `src/directories.py` (`Directories`):

| What | Where today | Read by |
|---|---|---|
| Tiles, sprites, menu and shop screens, the title banner, the NES font sheet | `data/images/` | `src/directories.py` paths, then pygame |
| NES music and its sound engine | `data/sound/music/NES/dragon_warrior.nsf` | `src/chiptune_soundtracks.py` (`nes_nsf_path`), libgme |
| SFC music | `data/sound/music/SFC/*.spc` | `src/chiptune_soundtracks.py`, libgme |
| Orchestral music | `data/sound/music/orchestra/` | `src/soundtrack.py` |
| Sound effects | `data/sound/sfx/*.mp3` (recordings), two `.wav` this project made | `src/sound.py` |
| English text | in the code (`data/text/dialog_lookup_table.py`, `intro_lookup_table.py`, `dialog.py`) and as the msgids of every catalog | `src/catalog.py`, gettext |
| Translations | `data/text/locales/*/LC_MESSAGES/base.po` | `src/catalog.py` |
| The 2014 smartphone script | `data/text/official_script/` | the translators (the `#. official:` lines) |
| Maps, NPC placements | `src/map_layouts.py`, `tests/nes_map_data.py` | `src/maps.py`, the tests |
| Monsters, items, spells, shops | `src/enemy_lookup.py`, `src/items.py`, `src/spells.py`, `src/shops.py` | throughout |
| Fonts | `data/fonts/` | the text drawing |

Two things make this harder than swapping a folder:

- **Game data is Python.** Maps, monsters, items and shops are tables in `src/`, not files. They have to become data
  the game loads.
- **The English text is the key of every translation.** gettext looks a line up by its English original, so each
  `.po` file holds the NES English text (section 7).

## 4. What the ROM can give, and what it can't

The US *Dragon Warrior* cartridge is an MMC1 board: 64 KB of program ROM in four 16 KB banks (the disassembly's
`Bank00.asm` to `Bank03.asm`) and 16 KB of graphics ROM. The disassembly documents where everything is.

**From the ROM:**

| Asset | How |
|---|---|
| Tiles and sprites | Decode the graphics ROM's 8×8 tiles with the NES palettes the game uses. The whole-screen images (menus, shops, the title banner) are drawn from tiles instead; `src/window_renderer.py` already draws windows that way. |
| NES music | Build the NSF from the ROM: its sound engine and music data, plus a 128-byte header pointing at the engine's init and play routines. The bundled NSF is exactly that, so the spike can compare byte for byte. libgme plays it as it does now. |
| Sound effects | The same NSF: the NES's sound effects run on the same engine. This replaces the `.mp3` recordings with the real thing. |
| English text | Decode the ROM's text with the disassembly's character table. |
| Maps, NPCs | Decode the map data (`MapDatTbl`, the overworld's run-length rows `WrldMapPtrTbl`, `NPCMobPtrTbl`, `NPCStatPtrTbl`). `reference/reference_utility_scripts/extract_nes_map_data.py` already does this from the disassembly's source; reading the ROM's bytes is the same work. |
| Monsters, items, spells, shops, levels | Read the ROM's tables (enemy stats, item prices, shop lists, the level-up table). |
| The NES font | It's tiles in the graphics ROM. |

**Not in the ROM:**

| Asset | Without it | As an extra |
|---|---|---|
| SFC soundtrack | NES music | The player points the game at a folder of the *Dragon Quest I & II* SPCs |
| Orchestral recordings | NES music | The player points the game at their own album |
| The official 2014 lines (`#. official:`) in the translations | The project's own translation of that line | Read from the player's copy of the smartphone app's data, if that's ever worth the work |
| Japanese with kana as on the Famicom | The current Japanese catalog | A second, optional ROM: the Famicom *Dragon Quest* |
| Korean, Chinese and the other translations | See section 7 and open question 3 | |

## 5. Asset sets

One interface, `AssetSet`, answers every request for a file or a table: the tileset, a sprite, the NSF, a sound
effect, a catalog, a map, the monster table. Three kinds:

1. **The ROM set**: extracted from the player's ROM into a cache folder (section 6).
2. **The free set**: shipped with the game (section 8).
3. **The bundled set**: today's `data/`, for the migration only. Each phase moves one kind of asset off it, and it's
   deleted at the end (section 10).

`data_path` and `Directories` become the bundled set's implementation. `nes_nsf_path`, `po_path` and the map, monster,
item and shop tables go through the set in use. The set in use is chosen at start, like the soundtrack:

- `--assets rom|free` on the command line, then the setting, then: the ROM set if a checked ROM has been extracted,
  otherwise the free set.
- The options screen shows which set is in use and offers "Load a ROM...".

Later, a mod is just another asset set (a folder with the same layout as the free set), which is most of the
modding kit idea.

**Saves.** An adventure log records which set it was made with, and only loads in the same one: a hero from the free
adventure can't walk into Tantegel. The 1.x promise (every 1.x log loads in later versions) carries over: a 1.x log
loads in the ROM set.

## 6. The ROM set

**Providing the ROM.** The game can't bundle a file picker easily (tkinter isn't in the builds), so any of:

- drag the ROM onto the game window (pygame's `DROPFILE` event, in every SDL build);
- `--rom path/to/rom.nes` on the command line;
- put it in the user data folder (`roms/`, next to `saves/`), which the first-start screen names.

**Checking it.** The game hashes the ROM (without its 16-byte iNES header, which dumps don't always agree on) and
compares the hash with the dumps it supports. Whether the US cartridge had more than one revision, and how they
differ in what the game uses, is open question 2. An unknown ROM gets a clear message: which revisions work, and that headered and
headerless dumps are both fine.

**Extracting.** Into `user_data_dir()/assets/<rom hash>/<extractor version>/`: PNG tile sheets and sprites, the
NSF, the decoded text as a catalog, maps and tables as JSON. Extraction runs once, takes a second or two, and is
redone when the extractor's version changes. Extracting to files rather than decoding at every start keeps the
game's loading code the same for every set, and makes the extracted files easy to inspect.

**Checking the extraction.** The repository keeps a hash of each extracted file for each supported revision (hashes
aren't the material itself). The extractor's tests compare against them when a ROM is present.

## 7. Text without the English as keys

Today every line is looked up by its English text: `_("Thou art dead.")` in the code, `msgid "Thou art dead."` in
every catalog. Without the English in the repository, every line needs a plain ID instead:

```
# src/hero_death.py
message(text('death.thou_art_dead'))

# data/text/locales/ko/LC_MESSAGES/base.po
msgid "death.thou_art_dead"
msgstr "..."
```

- **English comes from the ROM**: the extractor writes an English catalog with the same IDs. A table in the code
  maps each ID to where its text is in the ROM (the disassembly's text block and entry).
- **The free set has its own English catalog** with its own IDs (or shared IDs where a line means the same, like the
  menus: FIGHT, SPELL, ITEM).
- **Text the NES doesn't have** (this game's options, the stats page, co-op) is this project's own, stays in the
  repository and keeps working in every set.
- **Translators** lose the English beside each line in the `.po` file. A tool can put it back as an extracted
  comment (`#.`) in their local copy, from their own ROM, without committing it.

This is the largest single change: about 580 `_()` calls in 27 files, and 847 entries in each of the five translated
catalogs. It's
mechanical, and can be done by a script in one pull request per area of the game.

## 8. The free set

Everything in it under a free licence (CC0, CC-BY, OFL), each source in `ASSETS.md`:

| Part | Source |
|---|---|
| Music | Written for it in FamiTracker and exported as an NSF, so libgme plays it and nothing in the music code changes |
| Sound effects | sfxr, as `text_beep.wav` and `radiant.wav` are already made |
| Font | An OFL pixel font, plus GNU Unifont (already shipped, OFL) |
| Tiles and sprites | Drawn for it, or CC0/CC-BY sets from OpenGameArt, licences checked one by one |
| Story, names, dialog, maps | Written for it |

**Its own adventure.** It can't be *Dragon Warrior* with new graphics: the story, the names (Tantegel, Erdrick,
the Dragonlord) and the dialog are Square Enix's, and copying the maps' layouts is doubtful. It uses the engine's
rules (the NES formulas, which are this project's code), and the kinds of things the engine knows: towns, shops,
inns, dungeons, a captive to rescue, guardians, items that open the way, a final boss. Which of those the engine can
take from data, and which are written into the code for *Dragon Warrior*, is open question 5.

**Two stages:**

1. **Placeholder**: plain programmer art, a few chiptune loops, one town, one field, one cave, one boss. Enough for
   every test and the smoke test to run on it. Not meant to be played for fun.
2. **The demo**: a short, real adventure, for the browser build and itch.io. When it ends, it says how to play the
   full *Dragon Warrior* with a ROM. This is where artists, chiptune composers and translators can help, and it
   never blocks the rest.

## 9. Tests and CI

The ROM can't be in CI: not in the repository, not in a secret. So:

- **Most tests run on the free set** (or on small fixtures made for the test). Mechanics tests (formulas, menus,
  movement, co-op, saves) don't need *Dragon Warrior*'s content, only some content.
- **Tests that check the NES data** (the maps against the disassembly, the story run in `tests/test_story_run.py`,
  the checkpoints) are marked `rom` and skipped without one. They run locally when a ROM is in the user data folder.
  `tests/nes_map_data.py` goes away: those tests read the extracted maps.
- **The extractor's tests** compare against the stored hashes (section 6), locally.
- **Coverage.** CI's 95% bar counts the tests CI runs. The `rom` tests mustn't hide code from it: the free set has to
  reach the same code paths. How much of the suite depends on the content today (84 of 184 test files name Tantegel,
  the Dragonlord or Gwaelin) is the first thing to measure (phase 0).
- **The release builds** smoke-test on the free set. A maintainer runs the smoke test on the ROM set before tagging,
  as part of the release-candidate playthrough (`PLAYTEST.md`).

## 10. Removing the assets from the repository

Deleting the files from `main` leaves them in every earlier commit, and in every earlier release download. Choices:

1. **Delete from `main` only.** Simple, keeps history as it is. The material stays reachable in old commits.
2. **Rewrite the history** to remove `data/images/`, `data/sound/`, the official script and the English text from
   every commit. Every fork and clone breaks, every commit hash changes, and the rulesets on `main` need lifting for
   it. Only with the owner's explicit decision.
3. **Start a new repository** for 2.0, and archive this one.

The old releases' downloads (1.x) contain the assets too: keep them, or delete them when 2.0 is out.

## 11. Phased plan

**Phase 0: the spike.** `tools/extract_rom.py`: read a ROM, check its hash, write the tileset, the NSF and the decoded
English text, and compare them with `data/`. Measure how much of the test suite depends on the content. No change to
the game. If the extracted files match, the rest is engineering.

**Phase 1: asset sets.** The `AssetSet` interface, with the bundled set behind it. No change to what the game does.

**Phase 2: the ROM set for graphics and sound.** First-start screen, `--rom`, drag and drop, hash check, extraction,
the tiles, sprites, NSF and sound effects from the ROM. The bundled set still provides the rest.

**Phase 3: text IDs.** Every `_()` call and catalog moves to IDs, area by area. English from the ROM.

**Phase 4: game data.** Maps, NPCs, monsters, items, spells and shops from the ROM, as data files; `src/map_layouts.py`
and the tables in `src/` become loaders. The `rom` test mark.

**Phase 5: the placeholder free set.** CI runs on it.

**Phase 6: 2.0.** Delete the bundled set and `data/text/official_script/`. The SFC and orchestral soundtracks become
extras. `ASSETS.md` lists only the free set and the libraries. Decide section 10.

**Ongoing: the demo adventure**, then the browser build (#477) and itch.io (#439) on it.

## 12. Open questions

1. **The name.** *Dragon Warrior* is Square Enix's trademark, and it's the project's name, the repository's and the
   window title's. Ship of Harkinian and DevilutionX both chose their own. Keep it, or rename for 2.0?
2. **Which ROM revisions?** The spike finds the known good dumps of the US cartridge (No-Intro's list) and whether
   any revision differs in what the game uses. A Japanese or European ROM is out of scope at first.
3. **The translations.** The Korean, Japanese and Chinese catalogs are this project's translations of Square Enix's
   text, which makes them derivative works too. Fan translations have long been shared as patches; keeping ours in the
   repository is the same practice, but it isn't risk-free. Keep them (and drop only the `#. official:` lines), or
   move them out as optional downloads?
4. **The free set's name for things.** The menus and the rules are generic (FIGHT, HP, an inn), but how close may the
   free adventure's structure come to *Dragon Warrior*'s before it's a copy in new clothes?
5. **How much story is code?** Gwaelin, the Rainbow Bridge, the guardians, the ending: how much is written into
   `src/` for *Dragon Warrior*, and how much has to become data for the free adventure to have its own? An audit
   belongs in phase 0.
6. **The browser build.** Can a browser page take the ROM (a file input), and keep the extracted files (IndexedDB)?
   Until it can, the browser build is free set only.
7. **The SFC soundtrack from a ROM.** An SPC is a snapshot of the SNES sound chip's memory, not a slice of the ROM;
   making one from the *Dragon Quest I & II* ROM means running the game's sound code. Worth it, or folder of SPCs
   only?
