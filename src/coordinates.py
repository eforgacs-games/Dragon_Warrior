"""Names for the three kinds of int pairs that positions come in, which are easy to mix up.

- ``Cell``: (row, column) of a block in one of this project's map layouts, i.e. ``layout[row][column]``. Note the
  order: row (the vertical position) first. Player.row/column, staircase and NPC positions, treasure chests, guardian
  tiles and covered areas all use it.
- ``NesPosition``: (x, y) of a block on the NES map, i.e. the NES's CharXPos/CharYPos and the positions in the NES
  data tables (MapEntryTbl, the NPC tables). X (the horizontal position) first. A map's ``nes_origin`` converts
  between the two: NES (x, y) is layout (y + origin row, x + origin column).
- ``Pixel``: (x, y) in pixels on the map surface or the screen, as pygame takes them (Rect.topleft, blit
  destinations). X first.
"""

type Cell = tuple[int, int]  # (row, column) in a map layout
type NesPosition = tuple[int, int]  # (x, y) on the NES map: CharXPos, CharYPos
type Pixel = tuple[int, int]  # (x, y) in pixels
