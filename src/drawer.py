from statistics import mean
from typing import Any, Protocol
from collections.abc import Iterable

from pygame import display, KEYDOWN, event, Surface, Rect
from pygame.sprite import Group

from src.calculation import Calculation
from src.common import ANY_BUTTON_KEYS, WHITE, BLACK, Graphics
from src.coordinates import Cell, Pixel
from src.directories import Directories
from src.enemy_lookup import enemy_image_position_lookup
from src.game_functions import get_surrounding_rect
from src.command_window import held_buttons
from src.menu import CommandMenu
from src.options_screen import STATUS_WINDOW_ALWAYS
from src.sound import Sound
from src.text import draw_text
from src.view import full_screen, screen_origin_x
from src.visual_effects import cut_to_black, enemy_fade_in, enemy_hit_flash, enemy_spell_flash, screen_fade
from src.waiting import NES_FPS, clear_events_keeping_quit, is_any_key_held, wait
from src.window_renderer import draw_window
from src.windows import COMMAND_WINDOW, POPUP_LAYOUT, POPUP_WINDOW


class TileIndex:
    """Where each tile of a tile group is, so draw_all finds the tiles under the characters without going through
    every tile of their types (Alefgard has 14,400 blocks, most of them grass, trees, hills or water).

    A group's index is made the first time it is asked for and kept while it is the same group with as many tiles.
    The map's groups only change by being replaced with a new one or by having tiles added (DragonWarriorMap.add_tile,
    CommandMenu.set_tile_by_coordinates), and a tile never moves, so that is enough to tell when to index again. The
    group is kept with its index, so it can't be freed and another group made with its id."""

    def __init__(self) -> None:
        self._indexes: dict[int, tuple[Group, int, dict[Pixel, list[tuple[int, Any]]]]] = {}

    def tiles_at(self, group: Group, corners: set[Pixel]) -> list:
        """The tiles of group whose top left corner is one of corners, in the order the group has them (the order
        going through the group would find them in, so they are drawn in the same order)."""
        index = self._index(group)
        found = [entry for corner in corners for entry in index.get(corner, ())]
        found.sort(key=lambda entry: entry[0])
        return [tile for _, tile in found]

    def _index(self, group: Group) -> dict[Pixel, list[tuple[int, Any]]]:
        cached = self._indexes.get(id(group))
        if cached is not None and cached[0] is group and cached[1] == len(group):
            return cached[2]
        index: dict[Pixel, list[tuple[int, Any]]] = {}
        for position, tile in enumerate(group):
            index.setdefault(tile.rect.topleft, []).append((position, tile))
        if len(self._indexes) > 256:  # the groups of maps left long ago
            self._indexes.clear()
        self._indexes[id(group)] = (group, len(group), index)
        return index


class MapDrawingGame(Protocol):
    """What Drawer.draw_all draws a frame of the map from: the Game."""
    screen: Surface
    loop_count: int
    big_map: Any
    current_map: Any
    player: Any
    cmd_menu: Any
    foreground_rects: list
    camera: Any
    initial_dialog_enabled: bool
    events: list
    skip_text: bool
    story_flags: Any
    game_state: Any
    color: Any


class Drawer:

    def __init__(self, game_state):

        self.game_state = game_state
        self.scale = self.game_state.config["SCALE"]
        self.display_hovering_stats = False
        self.background = None
        # Where the hero was drawn on the last frame, so the frame a step ends on also redraws it (see draw_all)
        self.last_player_rect: Rect | None = None
        self.hovering_stats_displayed = False
        self.tile_index = TileIndex()
        # What the background's tiles were the last time a frame drew them all (drawn_tiles_state)
        self._drawn_in_full: tuple | None = None
        # The light around the hero, black around a hole, for each light diameter and screen size (draw_darkness)
        self._darkness: dict[tuple[int, int, int, int], Surface] = {}
        # Whether draw_all is drawing the frame a map change fades in from: the joypad isn't read until the fade-in
        # is over (see handle_initial_dialog)
        self.drawing_fade_in_frame = False
        self.graphics = Graphics(game_state.config)
        self.directories = Directories(game_state.config)
        self.sound = Sound(game_state.config)
        self.calculation = Calculation(game_state.config)

    def drawn_in_full(self, current_map, big_map) -> bool:
        """Whether every tile of the map is already on the background as it would be drawn again now: a map's first
        frame (loop_count 1) draws them all, and the frame a map change fades in from is one (MapManager.change_map),
        so the main loop's first frame after it, loop_count 1 too, used to draw all of Alefgard's 18,358 tiles a second
        time (#431). The background is drawn in full again if anything about its tiles changed in between: another
        map or background, a tile added or replaced, the palette (low HP, the bad ending) or the roofs."""
        return self.background is big_map and self._drawn_in_full == drawn_tiles_state(current_map, self.background)

    def get_enemy_image(self, enemy_name):
        """The enemy's scaled image and its top-left position on the screen."""
        enemy_path = f'{self.directories.IMAGES_ENEMIES_DIR}/{enemy_name.replace(" ", "")}.png'
        enemy_image_base = self.graphics.get_image(enemy_path)
        scaled_size = (enemy_image_base.get_width() * self.scale, enemy_image_base.get_height() * self.scale)
        enemy_image = self.graphics.get_scaled_image(enemy_path, scaled_size)
        tile_size = self.game_state.config["TILE_SIZE"]
        enemy_position = enemy_image_position_lookup.get(enemy_name)
        if not enemy_position:
            enemy_position = (mean(value[0] for value in enemy_image_position_lookup.values()),
                              mean(value[1] for value in enemy_image_position_lookup.values()))
        return enemy_image, (enemy_position[0] * tile_size, enemy_position[1] * tile_size)

    def fade_in_enemy(self, screen, enemy_name):
        """Show the enemy fading in from a black shadow (NES LoadEnemyGFX -> PalFadeIn twice). The final form's
        DoEndFight (Bank00 LoadEndBossGFX, $BABD) first fades the whole screen out (PalFadeOut) and blanks it, then
        fades the final form in four times, then waits 41 frames. Just before the fade-in (LBB86) it plays SFX_FIRE,
        over the end boss music InitFight has started."""
        enemy_image, enemy_position = self.get_enemy_image(enemy_name)
        if enemy_name == 'Dragonlord 2':
            screen_fade(fade_out=True, screen=screen, config=self.game_state.config)
            cut_to_black(screen, self.game_state.config)  # LoadBufferRows: the nametable is all blank tiles
            self.sound.play_sound(self.directories.breathe_fire_sfx)  # SFX_FIRE
            enemy_fade_in(screen, enemy_image, enemy_position, self.game_state.config, repeats=4)
            wait(round(41 * 1000 / NES_FPS), self.game_state.config)
        else:
            enemy_fade_in(screen, enemy_image, enemy_position, self.game_state.config)

    def flash_enemy(self, screen, enemy_name):
        """Flash the enemy red when the hero hits it (NES PlyrHitEn -> PaletteFlash)."""
        enemy_image, enemy_position = self.get_enemy_image(enemy_name)
        enemy_hit_flash(screen, enemy_image, enemy_position, self.game_state.config,
                        keep_black=enemy_name == 'Dragonlord 2')

    def flash_enemy_spell(self, screen, enemy_name):
        """Flash the enemy grey as it casts a spell (NES EnCastSpell -> PaletteFlash with SplFlshBGPalPtr)."""
        enemy_image, enemy_position = self.get_enemy_image(enemy_name)
        enemy_spell_flash(screen, enemy_image, enemy_position, self.game_state.config)

    @staticmethod
    def handle_sprite_animation(enable_animate, character_dict):
        if enable_animate:
            character_dict['character'].animate()
        else:
            character_dict['character'].pause()

    def handle_sprite_drawing_and_animation(self, current_map, foreground_rects, background, enable_animate):
        for identifier, character_dict in current_map.characters.items():
            character = character_dict['character']
            # NES $B957: an NPC on the other side of the cover from the hero isn't drawn
            if identifier == 'HERO' or not current_map.is_hidden_by_cover(character.row, character.column):
                foreground_rects.append(character_dict['character_sprites'].draw(background)[0])
            self.handle_sprite_animation(enable_animate, character_dict)

    @staticmethod
    def draw_all_tiles_in_current_map(current_map, background) -> None:
        for tile, tile_dict in current_map.floor_tile_key.items():
            if tile in current_map.tile_types_in_current_map and tile_dict.get('group'):
                tile_dict['group'].draw(background)
        if current_map.covered_area:
            draw_cover(current_map, background, ((row, column) for row in range(len(current_map.layout))
                                                 for column in range(len(current_map.layout[row]))))

    def draw_hovering_stats_window(self, screen, player, color=WHITE):
        """The pop-up stats window (PopupDat): the window and its labels generated (POPUP_LAYOUT,
        src/window_renderer.py), then the name and the values over it."""
        tile_size = self.game_state.config["TILE_SIZE"]
        draw_window(screen, POPUP_LAYOUT, color, self.game_state.config)
        draw_text(player.name[:4], tile_size * 2.99, tile_size * 2, screen, self.game_state.config, color=color,
                  alignment='center', letter_by_letter=False)
        self.draw_stats_strings_with_alignments(f"{player.level}", 2.99, screen, color=color)
        if len(str(player.current_hp)) < 5:
            self.draw_stats_strings_with_alignments(f"{player.current_hp}", 3.99, screen, color=color)
        else:
            self.draw_stats_strings_with_alignments("∞", 3.99, screen, color=color)
        if len(str(player.current_mp)) < 5:
            self.draw_stats_strings_with_alignments(f"{player.current_mp}", 4.99, screen, color=color)
        else:
            self.draw_stats_strings_with_alignments("∞", 4.99, screen, color=color)
        if len(str(player.gold)) < 5:
            self.draw_stats_strings_with_alignments(f"{player.gold}", 5.99, screen, color=color)
        else:
            self.draw_stats_strings_with_alignments("∞", 5.99, screen, color=color)
        if len(str(player.total_experience)) < 5:
            self.draw_stats_strings_with_alignments(f"{player.total_experience}", 6.99, screen, color=color)
        else:
            self.draw_stats_strings_with_alignments("∞", 6.99, screen, color=color)

    def set_to_post_initial_dialog(self, command_menu: CommandMenu):
        self.game_state.is_initial_dialog = False
        command_menu.set_king_lorik_dialog()
        self.game_state.enable_movement = True
        self.game_state.unpause_all_movement()

    def run_automatic_post_death_dialog(self, events, skip_text, command_menu):
        self.game_state.enable_movement = False
        # Only a joypad button starts the king's words (other keys are ignored, as in run_automatic_initial_dialog).
        if skip_text or nes_button_pressed(events):
            command_menu.show_text_in_dialog_box(
                command_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['post_death_dialog'],
                add_quotes=True, skip_text=skip_text)
            self.game_state.is_post_death_dialog = False
            set_to_save_prompt(command_menu)
            self.game_state.enable_movement = True
            self.show_pop_up_after_automatic_dialog()

    def status_window_always(self) -> bool:
        """The STATUS WINDOW option on ALWAYS (not NES): the pop-up window stays up on the map, walking too, but for
        the throne room's automatic dialogs, which keep it closed as they do on the NES setting. It's drawn on every
        frame (draw_all), so it shows the values as they change; windows open over it as they do over the NES's."""
        return (self.game_state.config.get('STATUS_WINDOW') == STATUS_WINDOW_ALWAYS
                and not self.game_state.is_initial_dialog and not self.game_state.is_post_death_dialog)

    def remove_pop_up(self, cmd_menu: CommandMenu) -> None:
        """NES ChkRemovePopUp (Bank00): take the pop-up window off the screen if it is up (DoRemovePopUp: RemoveWindow,
        FrameCounter kept as it was). With STATUS WINDOW on ALWAYS it stays."""
        if self.status_window_always():
            return
        self.display_hovering_stats = False
        if self.hovering_stats_displayed:
            cmd_menu.window_drop_up_effect(*POPUP_WINDOW)
            self.hovering_stats_displayed = False

    def show_pop_up_after_automatic_dialog(self) -> None:
        """The king's words in the throne room, which start on their own, keep the pop-up window closed while they wait
        for a button (handle_initial_dialog, handle_post_death_dialog). The hero has been standing still all along, so
        it opens as soon as they end."""
        self.display_hovering_stats = True

    def run_automatic_initial_dialog(self, events, skip_text, cmd_menu):
        self.game_state.enable_movement = False
        # NES FirstInputLoop (Bank03 LCBCD): the throne room waits until JoypadBtns isn't 0, so any button starts the
        # king's speech, D-pad, START and SELECT included, and so does one that's still held. Other keys don't.
        key_pressed = nes_button_pressed(events) or is_any_key_held(ANY_BUTTON_KEYS)
        if skip_text or (key_pressed and not self.game_state.automatic_initial_dialog_run):
            # show the map as it is before the dialog window opens over it (never in the frame a map change fades in
            # from: handle_initial_dialog doesn't start the speech until the fade-in is over)
            display.flip()
            # NES MainGameEngine: the king greets a hero who has already been beyond the throne room (F_LEFT_THROOM,
            # kept in the save) as returning, and gives everyone else the opening speech
            if cmd_menu.game.story_flags.left_throne_room:
                cmd_menu.show_text_in_dialog_box(
                    cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['load_from_save_dialog'],
                    add_quotes=True, skip_text=skip_text)
            else:
                cmd_menu.show_text_in_dialog_box(
                    cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'], add_quotes=True,
                    skip_text=skip_text)
            self.set_to_post_initial_dialog(cmd_menu)
            self.game_state.automatic_initial_dialog_run = True
            self.show_pop_up_after_automatic_dialog()

    def handle_initial_dialog(self, initial_dialog_enabled, cmd_menu, events, skip_text, left_throne_room):
        if initial_dialog_enabled:
            if self.game_state.is_initial_dialog:
                self.display_hovering_stats = False
                cmd_menu.launch_signaled = False
                # NES StartAtThroneRoom: the map fades in (PalFadeIn) before FirstInputLoop reads the joypad, so a
                # button held (or pressed) as the throne room loads doesn't start the king's speech before the fade
                if not self.drawing_fade_in_frame:
                    self.run_automatic_initial_dialog(events, skip_text, cmd_menu)
                clear_events_keeping_quit()
            else:
                if left_throne_room:
                    set_to_save_prompt(cmd_menu)
                else:
                    self.set_to_post_initial_dialog(cmd_menu)

        else:
            self.set_to_post_initial_dialog(cmd_menu)
            if not cmd_menu.menu.is_enabled():
                self.game_state.enable_movement = True

    def handle_darkness(self, screen, player) -> None:
        """Black out everything but the light around the hero in a dungeon (NES ChkLightDiameterX/ChkLightDiameterY,
        Bank00): a LightDiameter of 1, 3, 5 or 7 shows a square of that many blocks, centered on the hero."""
        hero_is_stepping = player.is_moving and not player.bumped
        if self.game_state.update_lit_diameter(hero_is_stepping):
            self.sound.play_sound(self.directories.radiant_sfx)  # SFX_RADIANT
        self.draw_darkness(screen)

    def blit_map(self, screen, current_map, camera_pos) -> None:
        """Put the map (the background) on the screen at the camera's position, with its boundary block all around it
        (draw_boundary)."""
        draw_boundary(screen, current_map, camera_pos, self.game_state.config["TILE_SIZE"])
        screen.blit(self.background, camera_pos)

    def draw_darkness(self, screen) -> None:
        """Black out everything outside the current light diameter (see handle_darkness), without updating it."""
        tile_size = self.game_state.config["TILE_SIZE"]
        lit_diameter = self.game_state.lit_diameter
        key = (screen.get_width(), screen.get_height(), tile_size, lit_diameter)
        darkness = self._darkness.get(key)
        if darkness is None:
            radius = (lit_diameter - 1) // 2
            darkness = Surface((screen.get_width(), screen.get_height()))  # lgtm [py/call/wrong-arguments]
            darkness_hole = darkness.subsurface((screen.get_width() / 2) - tile_size * radius,
                                                (screen.get_height() / 2) - tile_size * (radius + 0.5),
                                                tile_size * lit_diameter, tile_size * lit_diameter)
            darkness.fill(BLACK)
            darkness_hole.fill(WHITE)
            darkness.set_colorkey(WHITE)
            self._darkness[key] = darkness
        screen.blit(darkness, (0, 0)) if not self.game_state.config['NO_BLIT'] else None

    def draw_all(self, game: 'MapDrawingGame', enable_animate: bool, events: list | None = None) -> None:
        """
        Draw map, sprites, background, menu and other surfaces.
        :param game: What to draw: the Game (MapDrawingGame).
        :param enable_animate: Whether the characters' walking animation moves on this frame.
        :param events: This frame's events, for the windows drawn from here (the game's own by default).
        :return: None
        """
        screen, loop_count, big_map, current_map, player = (game.screen, game.loop_count, game.big_map,
                                                            game.current_map, game.player)
        cmd_menu, foreground_rects, camera, color = game.cmd_menu, game.foreground_rects, game.camera, game.color
        initial_dialog_enabled, skip_text, game_state = game.initial_dialog_enabled, game.skip_text, game.game_state
        left_throne_room = game.story_flags.left_throne_room
        if events is None:
            events = game.events

        # In the WIDE view (src/view.py) the map is drawn across the whole display, and the screen is its middle
        view, view_x = full_screen(screen), screen_origin_x(screen)
        view.fill(BLACK)
        width_offset = 0
        height_offset = 0
        tile_size = self.game_state.config["TILE_SIZE"]
        # NES DoCoveredArea ($B5FA): once the hero finishes a step onto a block whose cover status differs from
        # CoverStatus, the whole screen is redrawn with the roof (or the outside) swapped
        player_under_cover = current_map.is_covered(*get_player_block(player, tile_size))
        if player_under_cover != current_map.player_under_cover:
            current_map.player_under_cover = player_under_cover
            if loop_count != 1 and self.background is not None:
                self.draw_all_tiles_in_current_map(current_map, self.background)
        if loop_count == 1 and not self.drawn_in_full(current_map, big_map):
            self.background = first_frame_background(big_map, current_map.width - width_offset,
                                                     current_map.height - height_offset)
            # draw everything once on the first go-around
            self.draw_all_tiles_in_current_map(current_map, self.background)
            self._drawn_in_full = drawn_tiles_state(current_map, self.background)
        try:
            surrounding_tile_values = get_surrounding_tile_values(
                (player.rect.y // tile_size, player.rect.x // tile_size), current_map.layout)
            player_surrounding_tiles = convert_numeric_tile_list_to_unique_tile_values(current_map,
                                                                                       surrounding_tile_values)
            all_roaming_character_surrounding_tiles = self.get_all_roaming_character_surrounding_tiles(current_map)
            all_fixed_character_underlying_tiles = get_fixed_character_underlying_tiles(current_map)
            tile_types_to_draw = replace_characters_with_underlying_tiles([player.current_tile] +
                                                                          all_roaming_character_surrounding_tiles +
                                                                          all_fixed_character_underlying_tiles,
                                                                          current_map.character_key)
            if player.is_moving:
                tile_types_to_draw += replace_characters_with_underlying_tiles(
                    list(filter(None, player_surrounding_tiles)), current_map.character_key)
                # The pop-up window opens on the hero's POP_UP_FRAME of standing still
                # (MovementController.sprites_frame, counted in game frames like the steps) and is closed by any
                # direction press (MovementController.move_player), so it is gone once he moves
                self.remove_pop_up(cmd_menu)
        except IndexError:
            all_roaming_character_surrounding_tiles = self.get_all_roaming_character_surrounding_tiles(current_map)
            all_fixed_character_underlying_tiles = get_fixed_character_underlying_tiles(current_map)
            tile_types_to_draw = replace_characters_with_underlying_tiles([player.current_tile] +
                                                                          all_roaming_character_surrounding_tiles +
                                                                          all_fixed_character_underlying_tiles,
                                                                          current_map.character_key)

            # tile_types_to_draw = list(filter(lambda x: not self.is_impassable(x), tile_types_to_draw))

        group_to_draw: Group = Group()
        fixed_character_rects = [fixed_character.rect for fixed_character in current_map.fixed_characters]
        roaming_character_rects = [
            roaming_character.rect if roaming_character.is_moving else get_surrounding_rect(roaming_character,
                                                                                            self.game_state.config[
                                                                                                "TILE_SIZE"]) for
            roaming_character in
            current_map.roaming_characters]
        player_check_rect = get_surrounding_rect(player, tile_size) if player.is_moving else player.rect
        last_player_rect = self.last_player_rect
        if last_player_rect is not None and last_player_rect != player.rect and \
                abs(last_player_rect.x - player.rect.x) <= tile_size and abs(last_player_rect.y - player.rect.y) <= tile_size:
            # The hero arrives on a step's last moving frame (#237), so he's no longer moving on the frame that moved
            # him off where he was drawn last: redraw there too, or the edge of his last frame stays behind. Those
            # blocks can be another type than the one he's on now (a step from grass into the trees), so their types
            # are drawn too.
            player_check_rect = player_check_rect.union(last_player_rect)
            tile_types_to_draw += replace_characters_with_underlying_tiles(
                convert_numeric_tile_list_to_unique_tile_values(
                    current_map, tile_values_under_rect(last_player_rect, current_map.layout, tile_size)),
                current_map.character_key)
        self.last_player_rect = player.rect.copy()
        roaming_last_rects = [rc.last_rect for rc in current_map.roaming_characters if rc.last_rect is not None]
        all_roaming_rects = roaming_character_rects + roaming_last_rects
        # Every character is drawn onto the background each frame, on screen or not, so the tiles under every character
        # are redrawn each frame too, on screen or not. Otherwise a character off screen leaves its old frames on the
        # background, and they show up as a ghost once the camera scrolls over them (#98).
        block_corners_to_draw = block_corners_under_rects([player_check_rect] + fixed_character_rects + all_roaming_rects,
                                              tile_size)
        tile_types_set = set(tile_types_to_draw)
        cover_cells_to_draw = set()
        for tile, tile_dict in current_map.floor_tile_key.items():
            if tile_dict.get('group') and tile in tile_types_set:
                for tile_to_draw in self.tile_index.tiles_at(tile_dict['group'], block_corners_to_draw):
                    tile_rect = tile_to_draw.rect
                    if current_map.covered_area:
                        cell = (tile_rect.y // tile_size, tile_rect.x // tile_size)
                        if current_map.is_hidden_by_cover(*cell):
                            # the hero walking past it: redraw the roof/blank there, not the block itself
                            if player_check_rect.colliderect(tile_rect):
                                cover_cells_to_draw.add(cell)
                            continue
                    group_to_draw.add(tile_to_draw)
        group_to_draw.draw(self.background)
        if cover_cells_to_draw:
            draw_cover(current_map, self.background, cover_cells_to_draw)
        # to make this work in all maps: draw tile under hero, AND tiles under NPCs
        # in addition to the trajectory of the NPCs
        self.handle_sprite_drawing_and_animation(current_map, foreground_rects, self.background,
                                                 enable_animate)
        if not self.game_state.config['NO_BLIT']:
            # the whole view in WIDE (src/view.py), with the map's boundary block past its edges (draw_boundary)
            self.blit_map(view, current_map, (camera.pos[0] + view_x, camera.pos[1]))
        if current_map.identifier == 'TantegelThroneRoom':
            self.handle_initial_dialog(initial_dialog_enabled, cmd_menu, events, skip_text, left_throne_room)
            self.handle_post_death_dialog(game_state, cmd_menu, events, skip_text)
        if current_map.is_dark and self.game_state.config["ENABLE_DARKNESS"]:
            self.handle_darkness(view, player)  # centered on the whole view, so on the hero in the WIDE view too
        if self.display_hovering_stats or self.status_window_always():
            if not self.hovering_stats_displayed:
                cmd_menu.window_drop_down_effect(*POPUP_WINDOW)
                self.hovering_stats_displayed = True
            self.draw_hovering_stats_window(screen, player, color)
        self.handle_menu_launch(screen, cmd_menu, cmd_menu)
        if cmd_menu.menu.is_enabled():
            # The A press that opened the window is still held, or in this frame's events: WndDoSelect ignores it until
            # it is let go (or for 11 frames), so it doesn't also choose TALK (src/command_window.py)
            cmd_menu.select_command(events)
        else:
            if not game_state.is_initial_dialog:
                game_state.enable_movement = True

    def handle_post_death_dialog(self, game_state, cmd_menu, events, skip_text):
        if game_state.is_post_death_dialog:
            self.display_hovering_stats = False
            cmd_menu.launch_signaled = False
            if not self.drawing_fade_in_frame:  # as in handle_initial_dialog: not before the fade-in
                self.run_automatic_post_death_dialog(events, skip_text, cmd_menu)
            clear_events_keeping_quit()

    def draw_stats_strings_with_alignments(self, stat_string, y_position, screen, color):
        tile_size = self.game_state.config["TILE_SIZE"]
        if len(stat_string) > 4:
            draw_text(stat_string, tile_size * 3.2, tile_size * y_position, screen, self.game_state.config, color=color,
                      alignment='center', letter_by_letter=False)
        elif len(stat_string) > 3:
            draw_text(stat_string, tile_size * 3.44, tile_size * y_position, screen, self.game_state.config,
                      color=color, alignment='center', letter_by_letter=False)
        elif len(stat_string) > 2:
            draw_text(stat_string, tile_size * 3.67, tile_size * y_position, screen, self.game_state.config,
                      color=color, alignment='center', letter_by_letter=False)
        elif len(stat_string) > 1:
            draw_text(stat_string, tile_size * 3.99, tile_size * y_position, screen, self.game_state.config,
                      color=color, alignment='center', letter_by_letter=False)
        else:
            draw_text(stat_string, tile_size * 4.2, tile_size * y_position, screen, self.game_state.config, color=color,
                      alignment='center', letter_by_letter=False)

    def get_all_roaming_character_surrounding_tiles(self, current_map) -> list[str]:
        tile_size = self.game_state.config["TILE_SIZE"]
        all_roaming_character_surrounding_tiles = []
        for roaming_character in current_map.roaming_characters:
            roaming_character_surrounding_tile_values = get_surrounding_tile_values(
                (roaming_character.rect.y // tile_size, roaming_character.rect.x // tile_size), current_map.layout)
            all_roaming_character_surrounding_tiles.extend(
                convert_numeric_tile_list_to_unique_tile_values(current_map, roaming_character_surrounding_tile_values))
        return all_roaming_character_surrounding_tiles

    def handle_menu_launch(self, screen, cmd_menu: CommandMenu, menu_to_launch: CommandMenu) -> None:
        """Draw the COMMAND window (CmdNonCmbtDat) if it has been signaled, opening it first (drop down) if it isn't
        open yet: WndDoSelect then reads the joypad from scratch, the buttons held now included (held_buttons)."""
        if menu_to_launch.launch_signaled:
            if not cmd_menu.menu.is_enabled():
                self.sound.play_sound(self.directories.menu_button_sfx)
                cmd_menu.window_drop_down_effect(*COMMAND_WINDOW)
                cmd_menu.menu.enable(held_buttons())
            window_rect = cmd_menu.draw_command_window()
            if not self.game_state.config['NO_BLIT']:
                display.update(window_rect)

def map_surface(width: int, height: int) -> Surface:
    """A black surface the size of a map, in the display's format: the same as ``Surface((width, height)).convert()``,
    without making the surface twice (Alefgard's is 3840 x 3840 pixels, about 60 MB, and each copy takes tens of
    milliseconds). The format is taken from converting a 1 x 1 surface, so it is exactly the one convert gives."""
    surface = Surface((width, height), 0, display_format())
    surface.fill(BLACK)
    return surface


class SpareMapSurface:
    """The biggest map surface a map change has let go of, kept to be the next one of its size (#431). Making a map's
    surface costs most in the system handing over its memory: Alefgard's 4352 x 4320 pixels took about 34 ms to make,
    and filling a kept one black takes about 1.5 ms. Only the biggest is kept, so it is Alefgard's for as long as the
    hero is anywhere else, and the smaller maps' surfaces, quick to make, are let go."""

    def __init__(self) -> None:
        self.surface: Surface | None = None

    def take(self, width: int, height: int) -> Surface:
        """A black surface the size of a map (map_surface): the kept one if it is that size and in the display's
        format still (zooming sets the display mode again), filled black, or a new one."""
        surface, self.surface = self.surface, None
        if surface is not None and surface.get_size() == (width, height) and same_format(surface, display_format()):
            surface.fill(BLACK)
            return surface
        if surface is not None:
            self.surface = surface
        return map_surface(width, height)

    def give_back(self, surface: Surface | None) -> None:
        """Keep a map's surface the game is done with, if it is bigger than the one kept (or the same size)."""
        if not isinstance(surface, Surface) or surface is self.surface:
            return
        if self.surface is None or area(surface) >= area(self.surface):
            self.surface = surface


def area(surface: Surface) -> int:
    width, height = surface.get_size()
    return width * height


def display_format() -> Surface:
    return Surface((1, 1)).convert()


def same_format(surface: Surface, other: Surface) -> bool:
    return (surface.get_bitsize(), surface.get_masks(), surface.get_flags()) == \
        (other.get_bitsize(), other.get_masks(), other.get_flags())


def first_frame_background(big_map, width: int, height: int) -> Surface:
    """The black surface a map's first frame draws every tile on (draw_all with loop_count 1). That was a copy of
    big_map, the black surface MapManager.set_big_map makes for the map, so big_map itself is used (filled black
    again, in case a frame has already been drawn on it): it is in the same format and nothing else draws on it."""
    if isinstance(big_map, Surface) and big_map.get_size() == (width, height):
        big_map.fill(BLACK)
        return big_map
    return big_map.subsurface(0, 0, width, height).convert()


def drawn_tiles_state(current_map, background) -> tuple:
    """What decides how a map's tiles are drawn on a background (Drawer.drawn_in_full): the map and the background,
    each tile group and its size (tiles are only ever added, or a group replaced: see TileIndex), the images of the
    groups' first tiles (a palette change gives every tile of a type its new image, DragonWarriorMap
    update_tile_images), the palettes, and which side of the roofs the hero is on."""
    groups = []
    for tile_dict in current_map.floor_tile_key.values():
        group = tile_dict.get('group')
        if group:
            first_tile = next(iter(group.spritedict))
            groups.append((group, len(group), first_tile.image))
    return (current_map, background, tuple(groups), current_map.low_hp_palette, current_map.bad_ending_window_color,
            current_map.player_under_cover)


def replace_characters_with_underlying_tiles(tile_types_to_draw: list[str], current_map_character_key) -> list[str]:
    substitution = {k: v['underlying_tile'] for k, v in current_map_character_key.items()}
    return [substitution.get(t, t) for t in tile_types_to_draw]


def block_corners_under_rects(rects: Iterable[Rect], tile_size: int) -> set[Pixel]:
    """The pixel top left corners of the blocks that the given rects overlap (pixels, not Cells)."""
    cells = set()
    for rect in rects:
        for x in range(rect.left // tile_size * tile_size, rect.right, tile_size):
            for y in range(rect.top // tile_size * tile_size, rect.bottom, tile_size):
                cells.add((x, y))
    return cells


def tile_values_under_rect(rect: Rect, map_layout, tile_size: int) -> list[int]:
    """The layout values of the blocks that rect overlaps, leaving out any off the map."""
    values = []
    for x, y in block_corners_under_rects([rect], tile_size):
        row, column = y // tile_size, x // tile_size
        if 0 <= row < len(map_layout) and 0 <= column < len(map_layout[row]):
            values.append(map_layout[row][column])
    return values


def get_surrounding_tile_values(coordinates, map_layout):
    x = coordinates[0]
    y = coordinates[1]
    rows = len(map_layout)
    cols = len(map_layout[0]) if rows else 0
    neighbors = []
    if x - 1 >= 0 and y < len(map_layout[x - 1]):
        neighbors.append(map_layout[x - 1][y])
    if y - 1 >= 0 and x < rows:
        neighbors.append(map_layout[x][y - 1])
    if x < rows and y + 1 < len(map_layout[x]):
        neighbors.append(map_layout[x][y + 1])
    if x + 1 < rows and y < len(map_layout[x + 1]):
        neighbors.append(map_layout[x + 1][y])
    if x < rows and y < cols:
        neighbors.append(map_layout[x][y])
    return set(neighbors)


def convert_numeric_tile_list_to_unique_tile_values(current_map, numeric_tile_list: Iterable[int]) -> list[str]:
    return [current_map.get_tile_by_value(tile_value) for tile_value in set(numeric_tile_list)]


def get_fixed_character_underlying_tiles(current_map) -> list[str]:
    all_fixed_character_underlying_tiles = []
    for fixed_character in current_map.fixed_characters:
        fixed_character_coordinates = current_map.characters[fixed_character.identifier]['coordinates']
        all_fixed_character_underlying_tiles.append(
            current_map.get_tile_by_value(
                current_map.layout[fixed_character_coordinates[0]][fixed_character_coordinates[1]]))
    return all_fixed_character_underlying_tiles


def set_to_save_prompt(cmd_menu):
    cmd_menu.set_king_lorik_dialog(left_throne_room=True)


def get_player_block(player, tile_size: int) -> Cell:
    """The (row, column) of the block the hero stands on. While moving, that's still the block the step began on, as
    the NES only updates CharXPos/CharYPos once the step is done."""
    if player.is_moving:
        return player.row, player.column
    return player.rect.y // tile_size, player.rect.x // tile_size


def draw_cover(current_map, background, cells: Iterable[Cell]) -> None:
    """
    Draws over the given cells that are on the other side of the cover from the hero. NES ChkCoveredArea ($A9CD):
    covered blocks become BLK_SML_TILES (this project's ROOF tile) while the hero is outside, and uncovered blocks
    become BLK_BLANK while he's inside.
    """
    tile_size = current_map.config['TILE_SIZE']
    roof_image = current_map.map_tiles[current_map.floor_tile_key['ROOF']['val']][0]
    for row, column in cells:
        if current_map.is_hidden_by_cover(row, column):
            if current_map.player_under_cover:
                background.fill(BLACK, Rect(column * tile_size, row * tile_size, tile_size, tile_size))
            else:
                background.blit(roof_image, (column * tile_size, row * tile_size))


def draw_boundary(screen: Surface, current_map, camera_pos, tile_size: int) -> None:
    """
    Draw the map's boundary block (DragonWarriorMap.boundary_tile) on every block of the screen that is off the
    layout, before the map is blitted over it. NES GetBlockID gives every block off the map the boundary block
    (TrgtOutOfBounds, BoundsChkEnd LABDF), so the NES never shows black past a map's edge. The layouts are padded with
    it, but not always by half a screen.

    Off the map is never covered (HasCoverData's NoCover), so from under a roof it is blank (ChkCoveredArea's
    BLK_BLANK), as the padding is (draw_cover): nothing is drawn then.
    """
    map_x, map_y = int(camera_pos[0]), int(camera_pos[1])
    screen_width, screen_height = screen.get_size()
    if map_x <= 0 and map_y <= 0 and map_x + current_map.width >= screen_width and \
            map_y + current_map.height >= screen_height:
        return  # the map fills the screen
    if current_map.covered_area and current_map.player_under_cover:
        return
    image = current_map.floor_tile_image(current_map.floor_tile_key[current_map.boundary_tile]['val'])
    rows, columns = len(current_map.layout), len(current_map.layout[0])
    for row in range(-map_y // tile_size, (screen_height - map_y - 1) // tile_size + 1):
        for column in range(-map_x // tile_size, (screen_width - map_x - 1) // tile_size + 1):
            if 0 <= row < rows and 0 <= column < columns:
                continue
            screen.blit(image, (map_x + column * tile_size, map_y + row * tile_size))


def nes_button_pressed(events: Iterable[event.Event]) -> bool:
    """Whether ``events`` has a press of a key that stands for a joypad button (see src.common.ANY_BUTTON_KEYS)."""
    return any(current_event.type == KEYDOWN and current_event.key in ANY_BUTTON_KEYS for current_event in events)
