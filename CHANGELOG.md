# Changelog

All notable changes to this project are written down here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html): from 1.0 on, adventure logs and save states made by any
1.x version load in every later 1.x version.

## [1.0.0] - 2026-11-11

The first release: the whole of *Dragon Warrior*, from King Lorik's throne room to the Dragonlord and the ending,
playable start to finish, alone as on the NES or with a friend as a co-op party, with downloads for Windows, macOS
and Linux.

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
- **Auto-grind** (G): walk and fight until HP gets low or something needs you. **AUTO-HEAL** casts HEAL or HEALMORE
  instead of stopping, and **AUTO-INN** walks to the nearest inn, stays the night and walks back
  ([#499](https://github.com/eforgacs-games/Dragon_Warrior/pull/499),
  [#500](https://github.com/eforgacs-games/Dragon_Warrior/pull/500)).
- A **quest journal** (Q) with what to do next, and a mode that only shows what the hero has learned so far. It keeps
  Erdrick's tablet and King Lorik's charge to read again, and each hint names who told it
  ([#501](https://github.com/eforgacs-games/Dragon_Warrior/pull/501)). A **message log** (L) of the last 50 messages;
  a **dungeon map** (M) that fills in as you explore.
- A **stats page** (P) for each adventure: play time, steps, fights won, fled and lost, deaths, gold earned and
  spent, chests opened and monsters defeated by type ([#488](https://github.com/eforgacs-games/Dragon_Warrior/pull/488)).
- **Achievements** (T): 21 of them, for the story, challenges (such as the Dragonlord without dying, or at level 20 or
  lower), every kind of monster and milestones, with a banner when one unlocks. They're kept for whoever plays on the
  computer, across adventure logs, and nothing unlocks while a cheat is on
  ([#505](https://github.com/eforgacs-games/Dragon_Warrior/pull/505)).
- **RANDOMNESS**: NES (the default) makes every roll from the NES's own random number, which moves on every frame, so
  when you press a button changes what happens, as on the NES. SEEDED gives the hero and the world separate seeded
  generators, and `--seed` on the command line replays the same rolls
  ([#503](https://github.com/eforgacs-games/Dragon_Warrior/pull/503),
  [#504](https://github.com/eforgacs-games/Dragon_Warrior/pull/504)).
- A **shop preview** of the attack or defense power a weapon or armor would give you, part of the presets (off with
  NES, on with MODERN).
- **QUICK ACTION** and **SMART A**: talk, take, open a door or take the stairs with one key. A pressed while walking
  acts where the step ends, as the NES reads commands only between steps
  ([#527](https://github.com/eforgacs-games/Dragon_Warrior/pull/527),
  [#528](https://github.com/eforgacs-games/Dragon_Warrior/pull/528)).
- Townspeople who step aside, stairs taken by stepping on them, a run button, a bigger bag (16 slots), an always-on
  status window, encounters at half or off, x2 or x4 experience and gold, and a modern dialog style.
- Name entry where a full name waits on END so you can still change it.
- Cheats (F4 auto-battle, F9 invulnerability) are off unless you switch them on in the options.
- FAST is the default message speed.

### Co-op and network play

Not on the NES either: a new game is one hero unless you choose otherwise.

- **A party of two heroes** (HEROES: 2): a second hero with their own name, stats, equipment, items and spells, saved
  with the adventure log. Player 2 plays on the numpad or a second controller
  ([#506](https://github.com/eforgacs-games/Dragon_Warrior/pull/506)–[#511](https://github.com/eforgacs-games/Dragon_Warrior/pull/511),
  [#515](https://github.com/eforgacs-games/Dragon_Warrior/pull/515)).
  - **PARTY** (the default CO-OP): the second hero follows one step behind. Both fight, each choosing their own
    command, and the fight is lost only when both fall. Inns, shops, chests, STATUS, ITEM and SPELL all work for two,
    and player 2 has the second hero's ITEM, SPELL and STATUS on the map.
  - **FALLEN HEROES**: a hero who falls stays down until an inn (INN, the default), or gets back up with 1 HP after
    the fight (GET UP) ([#516](https://github.com/eforgacs-games/Dragon_Warrior/pull/516)).
  - **FREE ROAM** (CO-OP): each hero goes their own way in one shared world, on a split screen, each fighting and
    talking on their own while the other plays on. Save states and the rewind are off while they're apart
    ([#517](https://github.com/eforgacs-games/Dragon_Warrior/pull/517)–[#522](https://github.com/eforgacs-games/Dragon_Warrior/pull/522)).
- **Network play**: `--host` on one computer and `--join <address>` on the other. Player 2 sees the host's game (in free
  roam, only their own hero's half) and hears its music and sounds, played from their own copy of the game
  ([#512](https://github.com/eforgacs-games/Dragon_Warrior/pull/512),
  [#514](https://github.com/eforgacs-games/Dragon_Warrior/pull/514),
  [#521](https://github.com/eforgacs-games/Dragon_Warrior/pull/521)).
- Adventure logs with a second hero are save format 2. Logs from earlier versions load as one-hero logs, and an older
  version never writes over a format 2 log.

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

- Six languages, switched at any time in the options:
  - **English**, the NES script.
  - **Korean** (한국어), **Japanese** (日本語), **Traditional Chinese** (繁體中文) and **Simplified Chinese** (简体中文), with
    the names and terms of the official *Dragon Quest* in each language
    ([#491](https://github.com/eforgacs-games/Dragon_Warrior/pull/491),
    [#494](https://github.com/eforgacs-games/Dragon_Warrior/pull/494)).
  - **English (2014)**: the wording and names of the 2014 remake's official English script, drawn in the NES font
    ([#495](https://github.com/eforgacs-games/Dragon_Warrior/pull/495)).
- The translations are drawn with GNU Unifont, and every window is checked to fit in every language. Chinese text
  wraps between characters, as Chinese is written.
- The game starts in your system's language; `--language` on the command line (`English`, `Korean`, `Japanese`,
  `"Traditional Chinese"`, `"Simplified Chinese"` or `English2014`) chooses the language for that run.

### Platforms and builds

- Ready-to-play downloads for **Windows (x64)**, **macOS (Apple Silicon)** and **Linux (x64)**, with nothing else to
  install. Every build is tested before release by starting it and playing a few scenes in every
  language.
- Saves and settings go in your user folders (see the README). Adventure logs from earlier versions of the game still
  load, and a save from a newer version is never written over.
- If the game crashes, it writes a crash log and tells you where it is, to attach to a bug report.

### Licensing

- The source code is licensed under the GNU General Public License v3.0 or later. The game's graphics, music, text and
  other assets belong to their owners and aren't covered by it: [ASSETS.md](ASSETS.md) lists them and where they come
  from. This is an unofficial fan project, not affiliated with or endorsed by Square Enix or Nintendo.

[1.0.0]: https://github.com/eforgacs-games/Dragon_Warrior/releases/tag/v1.0.0
