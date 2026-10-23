from statistics import mean
from typing import Iterable, List, Set, Tuple

from pygame import display, KEYDOWN, event, Surface, Rect
from pygame.sprite import Group

from src.calculation import Calculation
from src.common import ANY_BUTTON_KEYS, WHITE, BLACK, Graphics
from src.directories import Directories
from src.enemy_lookup import enemy_image_position_lookup
from src.game_functions import get_surrounding_rect
from src.command_window import held_buttons
from src.menu import CommandMenu
from src.sound import Sound
from src.text import draw_text
from src.visual_effects import NES_FPS, cut_to_black, enemy_fade_in, enemy_hit_flash, screen_fade
from src.waiting import clear_events_keeping_quit, is_any_key_held, wait
from src.window_renderer import draw_window
from src.windows import COMMAND_WINDOW, POPUP_LAYOUT, POPUP_WINDOW


class Drawer:

    def __init__(self, game_state):

        self.game_state = game_state
        self.scale = self.game_state.config["SCALE"]
        self.display_hovering_stats = False
        self.background = None
        # Where the hero was drawn on the last frame, so the frame a step ends on also redraws it (see draw_all)
        self.last_player_rect: Rect | None = None
        self.hovering_stats_displayed = False
        self.graphics = Graphics(game_state.config)
        self.directories = Directories(game_state.config)
        self.sound = Sound(game_state.config)
        self.calculation = Calculation(game_state.config)

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
        fades the final form in four times, then waits 41 frames."""
        enemy_image, enemy_position = self.get_enemy_image(enemy_name)
        if enemy_name == 'Dragonlord 2':
            screen_fade(fade_out=True, screen=screen, config=self.game_state.config)
            cut_to_black(screen, self.game_state.config)  # LoadBufferRows: the nametable is all blank tiles
            enemy_fade_in(screen, enemy_image, enemy_position, self.game_state.config, repeats=4)
            wait(round(41 * 1000 / NES_FPS), self.game_state.config)
        else:
            enemy_fade_in(screen, enemy_image, enemy_position, self.game_state.config)

    def flash_enemy(self, screen, enemy_name):
        """Flash the enemy red when the hero hits it (NES PlyrHitEn -> PaletteFlash)."""
        enemy_image, enemy_position = self.get_enemy_image(enemy_name)
        enemy_hit_flash(screen, enemy_image, enemy_position, self.game_state.config,
                        keep_black=enemy_name == 'Dragonlord 2')

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
            # show the map as it is before the dialog window opens over it. Only now: draw_all also runs for the frame
            # a map change fades in from, and flipping that would flash the map at full brightness before the fade.
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
            self.sound.play_sound(self.directories.torch_sfx)  # SFX_RADIANT
        self.draw_darkness(screen)

    def draw_darkness(self, screen) -> None:
        """Black out everything outside the current light diameter (see handle_darkness), without updating it."""
        tile_size = self.game_state.config["TILE_SIZE"]
        radius = (self.game_state.lit_diameter - 1) // 2
        darkness = Surface((screen.get_width(), screen.get_height()))  # lgtm [py/call/wrong-arguments]
        darkness_hole = darkness.subsurface((screen.get_width() / 2) - tile_size * radius,
                                            (screen.get_height() / 2) - tile_size * (radius + 0.5),
                                            tile_size * self.game_state.lit_diameter,
                                            tile_size * self.game_state.lit_diameter)
        darkness.fill(BLACK)
        darkness_hole.fill(WHITE)
        darkness.set_colorkey(WHITE)
        screen.blit(darkness, (0, 0)) if not self.game_state.config['NO_BLIT'] else None

    def draw_all(self, screen, loop_count, big_map, current_map, player, cmd_menu, foreground_rects, enable_animate,
                 camera, initial_dialog_enabled, events, skip_text, left_throne_room, game_state, color) -> None:
        """
        Draw map, sprites, background, menu and other surfaces.
        :return: None
        """

        screen.fill(BLACK)
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
        if loop_count == 1:
            self.background = big_map.subsurface(0, 0, current_map.width - width_offset,
                                                 current_map.height - height_offset).convert()
            # draw everything once on the first go-around
            self.draw_all_tiles_in_current_map(current_map, self.background)
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
                # (MovementController.sprites_frame, counted in game frames like the steps) and closes when he moves
                self.display_hovering_stats = False
                if self.hovering_stats_displayed:
                    cmd_menu.window_drop_up_effect(1, 2, 4, 6)
                    self.hovering_stats_displayed = False
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
            # him off where he was drawn last: redraw there too, or the edge of his last frame stays behind.
            player_check_rect = player_check_rect.union(last_player_rect)
        self.last_player_rect = player.rect.copy()
        roaming_last_rects = [rc.last_rect for rc in current_map.roaming_characters if rc.last_rect is not None]
        all_roaming_rects = roaming_character_rects + roaming_last_rects
        # Every character is drawn onto the background each frame, on screen or not, so the tiles under every character
        # are redrawn each frame too, on screen or not. Otherwise a character off screen leaves its old frames on the
        # background, and they show up as a ghost once the camera scrolls over them (#98).
        cells_to_draw = get_cells_under_rects([player_check_rect] + fixed_character_rects + all_roaming_rects,
                                              tile_size)
        tile_types_set = set(tile_types_to_draw)
        cover_cells_to_draw = set()
        for tile, tile_dict in current_map.floor_tile_key.items():
            if tile_dict.get('group') and tile in tile_types_set:
                for tile_to_draw in tile_dict['group']:
                    tile_rect = tile_to_draw.rect
                    if tile_rect.topleft not in cells_to_draw:
                        continue
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
        screen.blit(self.background, camera.pos) if not self.game_state.config['NO_BLIT'] else None
        if current_map.identifier == 'TantegelThroneRoom':
            self.handle_initial_dialog(initial_dialog_enabled, cmd_menu, events, skip_text, left_throne_room)
            self.handle_post_death_dialog(game_state, cmd_menu, events, skip_text)
        if current_map.is_dark and self.game_state.config["ENABLE_DARKNESS"]:
            self.handle_darkness(screen, player)
        if self.display_hovering_stats:
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

    def get_all_roaming_character_surrounding_tiles(self, current_map) -> List[str]:
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

def replace_characters_with_underlying_tiles(tile_types_to_draw: List[str], current_map_character_key) -> List[str]:
    substitution = {k: v['underlying_tile'] for k, v in current_map_character_key.items()}
    return [substitution.get(t, t) for t in tile_types_to_draw]


def get_cells_under_rects(rects: Iterable[Rect], tile_size: int) -> Set[Tuple[int, int]]:
    """The top left corners of the blocks that the given rects overlap."""
    cells = set()
    for rect in rects:
        for x in range(rect.left // tile_size * tile_size, rect.right, tile_size):
            for y in range(rect.top // tile_size * tile_size, rect.bottom, tile_size):
                cells.add((x, y))
    return cells


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


def convert_numeric_tile_list_to_unique_tile_values(current_map, numeric_tile_list: Iterable[int]) -> List[str]:
    converted_tiles = []
    for tile_value in set(numeric_tile_list):
        converted_tiles.append(current_map.get_tile_by_value(tile_value))
    return converted_tiles


def get_fixed_character_underlying_tiles(current_map) -> List[str]:
    all_fixed_character_underlying_tiles = []
    for fixed_character in current_map.fixed_characters:
        fixed_character_coordinates = current_map.characters[fixed_character.identifier]['coordinates']
        all_fixed_character_underlying_tiles.append(
            current_map.get_tile_by_value(
                current_map.layout[fixed_character_coordinates[0]][fixed_character_coordinates[1]]))
    return all_fixed_character_underlying_tiles


def set_to_save_prompt(cmd_menu):
    cmd_menu.set_king_lorik_dialog(left_throne_room=True)


def get_player_block(player, tile_size: int) -> Tuple[int, int]:
    """The (row, column) of the block the hero stands on. While moving, that's still the block the step began on, as
    the NES only updates CharXPos/CharYPos once the step is done."""
    if player.is_moving:
        return player.row, player.column
    return player.rect.y // tile_size, player.rect.x // tile_size


def draw_cover(current_map, background, cells: Iterable[Tuple[int, int]]) -> None:
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


def nes_button_pressed(events: Iterable[event.Event]) -> bool:
    """Whether ``events`` has a press of a key that stands for a joypad button (see src.common.ANY_BUTTON_KEYS)."""
    return any(current_event.type == KEYDOWN and current_event.key in ANY_BUTTON_KEYS for current_event in events)
