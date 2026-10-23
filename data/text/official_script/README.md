# The official DRAGON QUEST script, in five languages

Every message of Square Enix's smartphone *DRAGON QUEST* (the 2014 remake of the first game, Android
`com.square_enix.android_googleplay.dq1_gp` version 1.1.4), in the game's five languages, lined up message by message:

| File | Language |
|---|---|
| `ja.json` | Japanese |
| `en.json` | English |
| `ko.json` | Korean |
| `zh1.json`, `zh2.json` | Chinese (the game's two Chinese text sets, Traditional and Simplified) |
| `script.tsv` | All five side by side, one message per row |

The Nintendo Switch *DRAGON QUEST* (2019) is a port of this version, so it has the same script; the Korean is the
official Korean translation. It isn't the NES script this project reproduces: the remake rewrote the dialog, so lines
correspond in meaning more or less closely, and names and terms carry over (Gwaelin is 로라, the Dragonlord 용왕). The
project's own Korean translation (`data/text/locales/ko/`) takes its names and terms from this script.

## Layout

The game stores its text in two parts, and both files keep that structure:

- `data`: system, battle, menu and item text, in 17 sections.
- `map`: what people say, in 35 sections, one per map.

Each section is a list of groups and each group a list of messages, so in the JSON a message is
`script["data" or "map"][section][group][message]`. In `script.tsv` the `id` column gives the same path, e.g.
`map.0.1.2`. The message at a given path is the same message in every language.

## Control codes

Messages are UTF-8 with the game's control codes written as `<` and two hex digits, sometimes followed by an argument.
The ones whose meaning is clear from the text:

| Code | Meaning |
|---|---|
| `\n` | New line |
| `<1A` | Wait for a button, with the blinking arrow |
| `<0C` | End of a message (wait for a button and clear the window) |
| `<07` | The hero's name |
| `<03` | A number (gold, experience, damage...) |
| `<5A` … `<70` … `<71` | A choice by number: in English, the singular and plural forms (`coin<5A<70s<71`) |
| `<70` … `<71` (Korean) | A choice of particle for the word before it (`<6A는<70은<71`: 는 or 은) |
| `<11`, `<12` | Start of a spoken line and of a narrated line |

The other codes are engine commands (sounds, names of items and monsters, layout, flags) whose exact meaning hasn't been
worked out yet. They're left as they are, so the text is exactly as the game has it.
