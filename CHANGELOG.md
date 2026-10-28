# Changelog

All notable changes to this project are written down here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html): from 1.0 on, adventure logs and save states made by any
1.x version load in every later 1.x version.

## [1.0.0] - Unreleased

The first release: the whole of *Dragon Warrior*, from King Lorik's throne room to the Dragonlord and the ending,
playable start to finish, with downloads for Windows, macOS and Linux.

### NES accuracy

- The whole game, checked against a disassembly of the NES original: every map, town, dungeon and treasure chest, every
  townsperson's lines and movement, the random encounter zones and fight chances, and the story from Princess Gwaelin
  and the Rainbow Bridge to the Dragonlord's offer and the ending.
- Battles follow the NES formulas: damage dealt and taken, enemy stats, HP and gold drops, enemy AI and spells,
  running away, sleep and STOPSPELL, the guardians (Golem, Green Dragon, Axe Knight) and the final fight
  ([#183](https://github.com/eforgacs-games/Dragon_Warrior/pull/183),
  [#263](https://github.com/eforgacs-games/Dragon_Warrior/pull/263)).
- Every spell and item works as on the NES, including the cursed items, the Silver Harp, Staff of Rain and Stones of
  Sunlight, SEARCH for hidden items, and the shops (buying, selling, keys and Fairy Water). Stat growth depends on the
  hero's name, as on the NES.
- The screen looks and moves like the NES: windows drawn pixel for pixel where the NES puts them, the NES font and
  scrolling dialog text with its beep, palette fades, the battle spiral, the low-HP red, the growing dungeon light,
  NPC timing and the 16-frame step, at the NES's 60.0988 frames a second.
- Music and sound effects start, stop and wait where the NES does them (fights, fanfares, the inn, stairs, spells).
- Saving with King Lorik, the three adventure logs, and COPY and ERASE work as on the NES.

### Gameplay and conveniences

None of these are on the NES. Each one is an option, with its NES behaviour as one of its values, so it can be switched
off on its own.

- An **options overlay** on the map (Select, U or Tab), in pages, with an **NES** preset (the NES game and nothing else),
  a **MODERN** preset (the recommended conveniences) and your own CUSTOM set
  ([#455](https://github.com/eforgacs-games/Dragon_Warrior/pull/455)). A new game starts with the NES preset.
- **Save states** (three slots), **rewind** (hold Backspace on the map) and an **autosave** when you enter a town or
  castle and every 3 minutes.
- **Game speed** from 1x up to 16x (keys 1 to 5), with the menus kept at normal speed unless you choose otherwise.
- **Auto-grind** (G): walk and fight until HP gets low or something needs you.
- A **quest journal** (Q) with what to do next, and a mode that only shows what the hero has learned so far; a
  **message log** (L) of the last 50 messages; a **dungeon map** (M) that fills in as you explore.
- A **shop preview** of the attack or defense power a weapon or armor would give you, part of the presets (off with
  NES, on with MODERN).
- Townspeople who step aside, stairs taken by stepping on them, QUICK ACTION and SMART A (talk, take, open a door or
  take the stairs with one key), a run button, a bigger bag (16 slots), an always-on status window, encounters at half
  or off, x2 or x4 experience and gold, and a modern dialog style.
- Name entry where a full name waits on END so you can still change it.
- Cheats (F4 auto-battle, F9 invulnerability) are off unless you switch them on in the options.
- FAST is the default message speed.

### Music

- Three soundtracks to choose from: **NES**, **SFC** (the Super Famicom *Dragon Quest I & II* arrangement) and
  **ORCHESTRA** (*Symphonic Suite Dragon Quest*, London Philharmonic Orchestra)
  ([#467](https://github.com/eforgacs-games/Dragon_Warrior/pull/467)).
- NES and SFC aren't recordings: the game plays the original music data (NSF and SPC) through emulated sound chips,
  with libgme ([#469](https://github.com/eforgacs-games/Dragon_Warrior/pull/469)). The downloads include libgme.

### Display and controls

- Zoom the window in whole steps (Ctrl +/-, Ctrl and the mouse wheel), fullscreen (F11), and a window size, zoom and
  game speed remembered for next time.
- A **widescreen view** (VIEW: WIDE) that shows more of the map for 16:9 and 16:10 screens.
- Display filters: optional scanlines and pixel-perfect scaling.
- **Key remapping** on a CONTROLS screen: two keys and a controller button for every action
  ([#447](https://github.com/eforgacs-games/Dragon_Warrior/pull/447)).
- **Gamepad** support for common controllers (Xbox, PlayStation, Switch Pro, Steam Deck, 8BitDo and others), with
  buttons placed as on the NES and SNES pads ([#388](https://github.com/eforgacs-games/Dragon_Warrior/pull/388)).
- H shows the controls as you have them bound.

### Languages

- **English** (the NES script) and **Korean** (한국어), switched at any time in the options. The Korean translation uses
  the names and terms of the official Korean *Dragon Quest*, drawn with GNU Unifont.
- The game starts in your system's language; `--language English` or `--language Korean` on the command line chooses
  the language for that run.

### Platforms and builds

- Ready-to-play downloads for **Windows (x64)**, **macOS (Apple Silicon)** and **Linux (x64)**, with nothing else to
  install. Every build is tested before release by starting it and playing a few scenes in English and in Korean.
- Saves and settings go in your user folders (see the README). Adventure logs from earlier versions of the game still
  load, and a save from a newer version is never written over.
- If the game crashes, it writes a crash log and tells you where it is, to attach to a bug report.

### Licensing

- The source code is licensed under the GNU General Public License v3.0 or later. The game's graphics, music, text and
  other assets belong to their owners and aren't covered by it: [ASSETS.md](ASSETS.md) lists them and where they come
  from. This is an unofficial fan project, not affiliated with or endorsed by Square Enix or Nintendo.

[1.0.0]: https://github.com/eforgacs-games/Dragon_Warrior/releases/tag/v1.0.0
