"""When roaming NPCs move, and when every character's walking animation changes, frame by frame, as the NES does it.

All of it happens in NES DoSprites (Bank00, $B6DA), which the game calls once a frame whether the hero is standing
(IdleUpdate, Bank03) or walking (DoJoyUp etc. call it on each of a step's 16 frames). It reads FrameCounter, which NMI
increments every frame:

- SprtChkFrameCntr: when FrameCounter & $0F is 0, CharLeftRight += 8. Bit 3 of CharLeftRight picks the walking frame
  (the leg swap) of the hero (GetPlayerAnim) and of every NPC (SprtFacingBaseAddr), so all characters swap legs
  together, every 16 frames, whether they're walking or not.
- UpdateNPCs1 ($B76F): only 2 NPCs are handled per frame, the pair NPCUpdateCntr (0 to 4) picks: mobile NPC slots
  2 * NPCUpdateCntr and 2 * NPCUpdateCntr + 1 (NPCLoopCounter = 2). There are 10 mobile slots; an empty slot (X and Y
  both 0) is skipped but keeps its place, so the pairs come round every 5 turns whatever the number of NPCs.
- NPCMoveLoop: a step can only start when FrameCounter & $0F is 1 (LB78B). Then SetNPCDir picks a random direction
  (RandNumUB AND #$60) and the NPC turns to it; if any check fails (HaltNPCMoveCalcs) it stays put, facing that way.
- NPCProcessCont: an NPC that's moving moves 1 pixel a frame (NPCMidPos), so a step takes the whole 16-frame turn:
  FrameCounter & $0F from 1 round to 0, the turn's last frame, where it arrives on its new block.
- UpdateNPCCounter ($B9FB): at the end of DoSprites, when FrameCounter & $0F is 0, NPCUpdateCntr moves on to the next
  pair, wrapping from 4 to 0.

So each pair gets a 16-frame turn in an 80-frame cycle: the pairs' steps never overlap, both NPCs of a pair step on
the same frames, and an NPC that isn't blocked takes one step every 80 frames (1.33 s).

The hero and the NPCs share FrameCounter, so they keep in step: the hero's steps start on a frame where it is 0
(mod 16) too (DoJoyUp etc.), so they take exactly one NPC turn. FrameCounter is reset to 0 by JoypadCheckLoop after
every step and command, and by a bump, but each time when its low nibble is 0 already or on the frame before DoSprites
would see 1 (PausePrepLoop and DoNCCmdWindow wait for that), so the frames DoSprites sees just keep counting
1, 2, ..., 15, 0, 1, ...; a new map (InitMapData: NPCUpdateCntr = 0, then JoypadCheckLoop) starts with pair 0's turn.
The one jump is IdleUpdate's pop-up window: see Game.do_sprites.

Game.frame_counter is this class's frame_counter; Game.do_sprites runs a frame of it, once per main loop frame, so it
speeds up with the game.
"""
from src.sprites.animated_sprite import AnimatedSprite

FRAMES_PER_TURN = 16  # FrameCounter & $0F
DECISION_FRAME = 1  # NPCMoveLoop: FrameCounter & $0F == 1
NPCS_PER_TURN = 2  # NPCLoopCounter
TURNS_PER_CYCLE = 5  # NPCUpdateCntr counts 0 to 4
MOBILE_NPC_SLOTS = NPCS_PER_TURN * TURNS_PER_CYCLE  # 10
FRAMES_PER_CYCLE = FRAMES_PER_TURN * TURNS_PER_CYCLE  # 80
POP_UP_FRAME = 0x31  # IdleUpdate (Bank03): the frame of standing still on which the pop-up window opens


class NPCSchedule:
    """NES FrameCounter, NPCUpdateCntr and CharLeftRight."""

    def __init__(self) -> None:
        self.frame_counter = 0
        self.update_counter = 0
        AnimatedSprite.walk_frame = 0

    def new_map(self) -> None:
        """InitMapData sets NPCUpdateCntr to 0, and JoypadCheckLoop FrameCounter, so the first frame on a map is pair
        0's decision frame. CharLeftRight carries on."""
        self.frame_counter = 0
        self.update_counter = 0

    @property
    def phase(self) -> int:
        """FrameCounter & $0F."""
        return self.frame_counter % FRAMES_PER_TURN

    @property
    def is_decision_frame(self) -> bool:
        return self.phase == DECISION_FRAME

    @property
    def between_turns(self) -> bool:
        """Whether the last DoSprites was the last frame of a turn: every NPC has finished its step, and the next frame
        starts the next pair's turn. NES PausePrepLoop and DoNCCmdWindow pause or open the window here."""
        return self.phase == 0

    def count_frame(self) -> None:
        """NMI: INC FrameCounter (one byte)."""
        self.frame_counter = (self.frame_counter + 1) & 0xFF

    def start_sprites(self) -> None:
        """The start of DoSprites: every 16th frame the walking animation swaps legs (SprtChkFrameCntr)."""
        if self.phase == 0:
            AnimatedSprite.walk_frame ^= 1

    def end_sprites(self) -> None:
        """The end of DoSprites: after the last frame of a turn, the next pair's turn comes (UpdateNPCCounter)."""
        if self.phase == 0:
            self.update_counter = (self.update_counter + 1) % TURNS_PER_CYCLE

    def slots_on_turn(self) -> range:
        """The mobile NPC slots handled this frame (RoamingCharacter.slot). The slots are in the order of the map's
        mobile NPC table (TantMobTbl etc., Bank00), which is the order of its roaming_character_list."""
        first = self.update_counter * NPCS_PER_TURN
        return range(first, first + NPCS_PER_TURN)

    def give_turn_to(self, slot: int) -> None:
        """Make the next frame the decision frame of the pair `slot` is in (for tests and debugging)."""
        self.frame_counter = 0
        self.update_counter = slot // NPCS_PER_TURN
