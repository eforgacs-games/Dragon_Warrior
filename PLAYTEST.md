# Playtest checklist

A pass through the whole critical path in about 40 minutes, using checkpoints instead of a full playthrough.

`tests/test_story_run.py` and `tests/test_checkpoints.py` already check the story logic headless: items, flags,
warps, dialog order and the credits list. This checklist covers what they can't check: how it **looks**, how it
**sounds**, and how the dialog **reads**.

## Setup

```bash
python src/game.py --dev --checkpoint <name>
```

- `--dev` turns on god mode, turns off random battles, prints your coordinates in the terminal, and turns on the
  debug keys below. To feel the real fights (the Dragonlord, for example), leave out `--dev`. The checkpoint still
  loads, but you take damage and the debug keys are off.
- A checkpoint is a save file in `data/checkpoints/`, loaded the same way as a saved game. The game opens straight on
  the map, with no title screen. If you save with King Lorik, the save goes to the system temp folder
  (`dragon_warrior_checkpoint_saves`), so your real save slots in `src/saves/` aren't touched.
- The hero is called **Arthur** in every checkpoint, or **검객** when the game is in Korean. Both names give the
  strongest name stats (full strength and HP, +3 to agility and MP after the cut), so fights go quickly. Erdrick (로토)
  is the hero's ancestor, not the hero.
- Keys: arrows/WASD move, **K** opens the command menu (TALK, SEARCH, STAIRS, ITEM...), **J** closes it, **Enter**
  talks, opens a door or takes a chest in front of you, **H** lists the controls, **1-5** change the game speed (handy for
  long walks).
- Debug keys (`--dev` only):
  - **F5** warps to any map's entrance.
  - **F6** gives an item, adds gold, sets your level, equips Erdrick's gear, or refills HP and MP.
  - **F7** loads another checkpoint.
  - **F8** starts recording every frame; **F8** again saves them, with a report of any flickers (see "Finding visual
    glitches" in CONTRIBUTING.md).

  F5 to F7 each open a list: type to filter it, use ↑/↓ to move, press Enter to pick, and press Esc to close.

Positions below are `(row, column)`, the same order as the checkpoint files.

---

## 1. `throne_room`: a fresh start (4 min)

Level 1, no gear, no gold, no story flags set.

For the full opening, also run `python src/game.py` once without flags. You should see the title screen, the
adventure log menu and name entry, then King Lorik's opening speech.

- [ ] Throne room music starts. The three chests are visible.
- [ ] TAKE each chest: the gold, the Torch and the Magic Key. Each gives its message and the item sound. The chest
      turns into floor.
- [ ] TALK to King Lorik: his lines break cleanly inside the window, with no word cut in half or running past the
      border.
- [ ] Open the door with the key (**door sound**). Take the stairs down (**stairs sound**, fade out and in). The
      courtyard music starts.
- [ ] Walk out of the south gate. The overworld music starts.

## 2. `garins_grave`: the Silver Harp (5 min)

Level 8, Copper Sword, 2 Magic Keys, the Stones of Sunlight and a Torch. You're in Garinham, just below the stairs to
the grave.

- [ ] STAIRS: the grave is dark, and only the tiles around the hero show.
- [ ] Use the Torch (**torch sound**). The lit area grows.
- [ ] Each floor (B1 to B4) has its own dungeon music, and it changes as you go down.
- [ ] The Silver Harp's chest is on B3, reached by the stairs up from B4. Take it and check the "Thou hast found"
      message and the sound.
- [ ] Use the harp on the overworld: the harp tune plays to the end, then a fight starts. Use it in a town: the tune
      plays, then the town music resumes.

## 3. `swamp_cave`: rescuing Gwaelin (5 min)

Level 12, with the Silver Harp, the Stones of Sunlight and 2 Magic Keys. You're outside the Swamp Cave's south
entrance; walk two steps east.

- [ ] Without `--dev`, the marsh step flashes red and plays the **swamp sound**. With `--dev`, god mode skips both,
      so there's no flash.
- [ ] In the cave, open the door to Gwaelin's room and TALK to her. Answer NO once ("But thou must."), then answer
      YES to "Will thou take me to the castle?" Then you get "Princess Gwaelin embraces thee.", the music stops, and
      the Gwaelin jingle plays. The hero sprite changes to the hero carrying her.
- [ ] Back in the throne room (F5 → `TantegelThroneRoom`, or walk), TALK to King Lorik:
  - [ ] "I'm so happy!", then the **Gwaelin's Love** jingle, then the throne room music again
  - [ ] you receive Gwaelin's Love
  - [ ] Gwaelin appears beside the throne, to the king's right, and the hero sprite goes back to normal.
- [ ] Use Gwaelin's Love on the overworld. The text reads naturally, with the right experience number and line breaks.

## 4. `rainbow_drop_shrine`: the Rainbow Drop (3 min)

Level 16. You have the Staff of Rain, the Stones of Sunlight and Erdrick's Token, and you're facing the sage in the
shrine.

- [ ] TALK. The Stones and the Staff are taken, and the Rainbow Drop is given.
- [ ] **The screen flashes greyscale for about half a second**, then returns to full color with nothing left over.
- [ ] TALK again: he has no business with you now.
- [ ] Optional, without Erdrick's Token: load `swamp_cave` and press F5 → `MagicTemple`, then TALK to the sage. He
      says you aren't the one Erdrick predicted, **the screen flashes white**, and you land outside the shrine.

## 5. `rainbow_bridge`: building the bridge (2 min)

Level 17, with the Rainbow Drop. You're on the tile east of the water gap, across from Charlock.

- [ ] ITEM → Rainbow Drop. The bridge appears on the water tile to the west, and you can walk onto it.
- [ ] Use it anywhere else: you get "But no rainbow appeared here."
- [ ] Enter a town and come back out (or F5 → `Alefgard`): the bridge is still there.
- [ ] Cross the bridge and enter Charlock. Check the music change and the fade.

## 6. `charlock_throne`: the hidden staircase (3 min)

Level 19, with Flame Sword and Erdrick's Armor. You're on Charlock's ground floor, at the Dragonlord's throne. The
Rainbow Bridge is built.

- [ ] SEARCH: "Feel the wind blowing from behind the throne."
- [ ] Walk round to the tile behind the throne, across the barrier tiles. With Erdrick's Armor, barriers don't hurt
      or flash. To see the red flash, start this checkpoint without `--dev`, or load `rainbow_bridge` (no Erdrick's
      Armor) without `--dev` and walk in.
- [ ] SEARCH there: the stairs appear. Take them down. Each floor has its own music, through B7.

## 7. `dragonlord`: the fight (5 min, plus 2 min for the bad ending)

Level 22, with Erdrick's Sword, Erdrick's Armor and the Silver Shield, facing the Dragonlord on B8. For a real fight,
start without `--dev`.

- [ ] TALK. The Dragonlord's speech and the yes/no window read cleanly.
- [ ] Answer NO. "Thou art a fool!" The battle music starts, and his sprite appears.
- [ ] Defeat the first form. The transformation into the second form should look and sound right.
- [ ] Defeat the second form: the Ball of Light text, then a fade out to the overworld outside Charlock. HP and MP are
      full.
- [ ] Without `--dev`: afterwards there are no random fights and no swamp or barrier damage.
- [ ] **Bad ending:** F7 → `dragonlord`, TALK, and answer YES both times. You get "Thy journey is over...". **The
      background turns black, the window border turns red**, and the status window opens. The game then stops
      responding until you close it, which is correct.

## 8. `ending_gwaelin_returned`: the ending after returning Gwaelin (6 min)

The Dragonlord is dead and Gwaelin is in the throne room. You're outside Tantegel.

- [ ] Walk into the castle. TALK to anyone in the courtyard: "Come now, King Lorik awaits." In other towns (F5) NPCs
      say "Hurrah! Hurrah! Long live Erdrick!" or "Thou hast brought us peace, again."
- [ ] King Lorik is downstairs, in the courtyard. Step onto the tile just below him: his speech starts.
- [ ] **Gwaelin comes down the stairs and walks right, one tile at a time and smoothly, until she's beside the
      king.**
- [ ] "May I travel as thy companion?" Answer NO once: "But thou must." Then answer YES. The hero now carries her.
- [ ] "And thus the tale comes to an end...." The hero looks right, then down, and the trumpets sound.
- [ ] **Credits:** the ending music plays. Each screen fades in and out in time with the music, and the text sits
      centred on the screen, not cut off. THE END stays up until you close the window.

## 9. `ending_carrying_gwaelin`: the ending while carrying Gwaelin (3 min)

The same as 8, but you never brought her back. Gwaelin's Love isn't in the inventory.

- [ ] Walk in carrying her: the courtyard sprite is the hero carrying Gwaelin.
- [ ] After the king's speech she's set down beside him, without walking down the stairs. Then she asks to come
      along, and the rest is the same as 8.

---

## Throughout (keep an ear and eye out)

- Music changes on every map change, and the music for each area is correct.
- The sound effects: menu button, text beep, stairs up and down, door, chest, damage, level up, death.
- Dialog: no line runs past the window border, and no word is split. Quotes open with `` ` `` and close with `’`.
  The arrow blinks while more text is waiting.
- The window drop-down and drop-up effects, the fades between maps, and the hero's sprite (armed, with or without a
  shield, or carrying Gwaelin).

## Reporting a bug

Write down:

1. **The checkpoint** you started from, e.g. `rainbow_bridge`, and whether you used `--dev`.
2. **The coordinates.** With `--dev`, `SHOW_COORDINATES` prints `Current coordinates: (column, row)` in the terminal
   on every step. Copy the last line. Note that it prints the column first, unlike this checklist.
3. **The map** (shown in F5's list if you aren't sure of its name).
4. What you did, what you expected, and what happened. Include a screenshot or a short recording for anything visual,
   or a note on what you heard for a sound problem.

Example: *`charlock_throne`, `--dev`, CharlockB1, `Current coordinates: (17, 7)`: searched behind the throne, the
stairs appeared but no sound played.*
