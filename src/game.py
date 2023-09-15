import json
import os
import random
from typing import List, Tuple

from pygame import FULLSCREEN, K_1, K_2, K_3, K_4, K_DOWN, K_LEFT, K_RIGHT, K_UP, K_a, K_d, K_i, K_k, K_s, \
    K_u, K_w, QUIT, RESIZABLE, Surface, display, event, image, init, key, mixer, quit, K_F1, time, KEYDOWN, SCALED, \
    USEREVENT, K_RETURN
from pygame.display import set_mode, set_caption
from pygame.event import get
from pygame.time import Clock
from pygame.time import get_ticks

from data.text.intro_lookup_table import ControlInfo
from src import maps
from src.battle import calculate_enemy_attack_damage, Battle
from src.calculation import Calculation, get_tile_id_by_coordinates
from src.camera import Camera
from src.common import BLACK, accept_keys, reject_keys, Graphics, RED, WHITE, is_facing_medially, is_facing_laterally, \
    set_gettext_language
from src.common import is_facing_up, is_facing_down, is_facing_left, is_facing_right
from src.config import dev_config, prod_config
from src.direction import Direction
from src.directories import Directories
from src.drawer import Drawer
from src.enemy_lookup import enemy_territory_map
from src.enemy_spells import enemy_spell_lookup
from src.game_functions import set_character_position, get_next_coordinates, GameFunctions
from src.game_state import GameState
from src.intro import Intro
from src.map_layouts import MapLayouts
from src.maps import map_lookup
from src.menu import CommandMenu, Menu
from src.menu_functions import convert_list_to_newline_separated_string, NameSelection
from src.movement import Movement
from src.music_player import MusicPlayer
from src.player.player import Player
from src.sound import Sound
from src.sprites.fixed_character import FixedCharacter
from src.sprites.roaming_character import RoamingCharacter
from src.visual_effects import fade, flash_transparent_color

arrow_fade = USEREVENT + 1


class Game:
    def __init__(self, config):

        self.config = config
        self.sound = Sound(config)
        self.graphics = Graphics(config)
        self.directories = Directories(config)
        self.calculation = Calculation(config)
        self.game_functions = GameFunctions(config)
        self.movement = Movement(self.config)
        self.show_arrow = True
        self.game_state = GameState(config=config)
        self.music_player = MusicPlayer(config)

        # load/save

        self.save_dir_contents = None

        self._ = _ = set_gettext_language(config['LANGUAGE'])
        self.drawer = Drawer(self.game_state)
        # map/graphics
        self.big_map = None
        self.layouts = MapLayouts()
        self.fullscreen_enabled = self.game_state.config["FULLSCREEN_ENABLED"]
        # text
        self.initial_dialog_enabled = self.game_state.config["INITIAL_DIALOG_ENABLED"]
        self.skip_text = False

        # intro
        self.start_time = get_ticks()
        self.splash_screen_enabled = self.game_state.config["SPLASH_SCREEN_ENABLED"]
        # engine
        self.fps = self.game_state.config["FPS"]
        self.last_map = None
        self.last_zone = None
        self.last_amount_of_tiles_moved = 0
        self.tiles_moved_since_spawn = 0

        self.loop_count = 1
        self.foreground_rects = []
        self.torch_active = False
        self.speed = 2

        # battle
        self.battle_menu_row = 0
        self.battle_menu_column = 0
        self.launch_battle = False
        self.current_enemy_pattern_index = None
        self.enemy_runaway_attempts = 0

        # debugging
        self.show_coordinates = self.game_state.config["SHOW_COORDINATES"]
        init()
        time.set_timer(arrow_fade, 530)
        self.paused = False
        # Create the game window.
        if self.fullscreen_enabled:
            # according to pygame docs: "SCALED is considered an experimental API and may change in future releases."
            self.flags = FULLSCREEN | SCALED
            # self.flags = FULLSCREEN
        else:
            self.flags = RESIZABLE | SCALED
            # self.flags = RESIZABLE
        # flags = RESIZABLE | SCALED allows for the graphics to stretch to fit the window
        # without SCALED, it will show more of the map, but will also not center the camera
        # it might be a nice comfort addition to add to center the camera, while also showing more of the map
        self.scale = self.game_state.config["SCALE"]
        # video_infos = display.Info()
        # current_screen_width, current_screen_height = video_infos.current_w, video_infos.current_h
        nes_res = self.game_state.config["NES_RES"]
        win_width, win_height = nes_res[0] * self.scale, nes_res[1] * self.scale
        self.screen = self.set_screen(win_height, win_width)
        # self.screen.set_alpha(None)
        set_caption(_("Dragon Warrior"))

        # self.current_map can be changed to other maps for development purposes

        self.current_map = maps.TantegelThroneRoom(config)
        # self.current_map = maps.TantegelCourtyard(config)
        # self.current_map = maps.Alefgard(config)

        # towns
        # self.current_map = maps.Brecconary(config)
        # self.current_map = maps.Garinham(config)
        # self.current_map = maps.Kol(config)
        # self.current_map = maps.Rimuldar(config)
        # self.current_map = maps.Hauksness(config)
        # self.current_map = maps.Cantlin(config)

        # caves

        # self.current_map = maps.CharlockB1(config)
        # self.current_map = maps.SwampCave(config)
        # self.current_map = maps.MountainCaveB1(config)

        # self.current_map = maps.MagicTemple(config)

        self.set_big_map()

        self.set_roaming_character_positions()

        self.player = Player(center_point=None,
                             images=self.current_map.scale_sprite_sheet(self.directories.UNARMED_HERO_PATH),
                             current_map=self.current_map, god_mode=self.game_state.config['GOD_MODE'])
        self.player.restore_hp()
        self.tile_size = self.game_state.config["TILE_SIZE"]
        self.current_map.load_map(self.player, None, self.tile_size)
        self.color = self.get_current_color()

        # Good for debugging,
        # and will be useful later when the player's level increases and the stats need to be increased to match

        # self.player.total_experience = 26000
        # self.player.level = self.player.get_level_by_experience()
        # self.player.update_stats_to_current_level()

        self.player.current_tile = get_tile_id_by_coordinates(self.player.rect.x // self.tile_size,
                                                              self.player.rect.y // self.tile_size, self.current_map)
        self.camera = Camera((int(self.player.column), int(self.player.row)), self.current_map, self.screen,
                             self.tile_size)
        self.cmd_menu = CommandMenu(self)

        self.enable_animate = True
        self.enable_roaming = True
        self.clock = Clock()
        self.music_enabled = self.game_state.config["MUSIC_ENABLED"]

        if self.splash_screen_enabled:
            self.music_player.load_and_play_music(self.directories.intro_overture)
        else:
            self.music_player.load_and_play_music(self.current_map.music_file_path)
        self.events = get()

        display.set_icon(image.load(self.directories.ICON_PATH))
        self.allow_save_prompt = False
        # pg.event.set_allowed([pg.QUIT])

    def set_screen(self, win_height, win_width):
        """Stub for setting the screen."""
        return set_mode((win_width, win_height), self.flags)

    def main(self) -> None:
        """
        Main loop.
        :return: None
        """
        if self.splash_screen_enabled:
            intro = Intro(self.config)
            intro.show_start_screen(self.screen, self.start_time, self.clock, self.game_state.config)
            self.music_player.load_and_play_music(self.directories.intermezzo)
            self.show_main_menu_screen(self.screen)
        self.drawer.draw_all(self.screen, self.loop_count, self.big_map, self.current_map, self.player, self.cmd_menu,
                             self.foreground_rects, self.enable_animate, self.camera, self.initial_dialog_enabled,
                             self.events, self.skip_text, self.allow_save_prompt, self.game_state, self.torch_active,
                             self.color)
        while True:
            self.clock.tick(self.fps)
            self.get_events()
            self.drawer.draw_all(self.screen, self.loop_count, self.big_map, self.current_map, self.player,
                                 self.cmd_menu, self.foreground_rects, self.enable_animate, self.camera,
                                 self.initial_dialog_enabled, self.events, self.skip_text, self.allow_save_prompt,
                                 self.game_state, self.torch_active, self.color)
            display.flip()
            self.loop_count += 1

    def show_main_menu_screen(self, screen) -> None:
        self.save_dir_contents = os.listdir(self.directories.save_dir)
        if len(self.save_dir_contents) == 0:
            begin_quest_empty_log_function_lookup = {
                0: self.begin_new_quest,
            }
            selection = self.game_functions.main_menu_selection(get_ticks(), screen,
                                                                self.directories.main_menu_empty_log_unselected,
                                                                self.directories.main_menu_empty_log_0, [],
                                                                no_blit=self.game_state.config['NO_BLIT'])
            begin_quest_empty_log_function_lookup[selection]()
        else:
            if len(self.save_dir_contents) < 3:
                partially_full_log_function_lookup = {
                    0: self.continue_quest,
                    1: self.change_message_speed,
                    2: self.begin_new_quest,
                    3: self.copy_quest,
                    4: self.erase_quest,
                }
                selection = self.game_functions.main_menu_selection(get_ticks(), screen,
                                                                    self.directories.main_menu_partially_full_log_unselected,
                                                                    self.directories.main_menu_partially_full_log_0,
                                                                    [
                                                                        self.directories.main_menu_partially_full_log_1,
                                                                        self.directories.main_menu_partially_full_log_2,
                                                                        self.directories.main_menu_partially_full_log_3,
                                                                        self.directories.main_menu_partially_full_log_4],
                                                                    no_blit=self.game_state.config['NO_BLIT'])
                partially_full_log_function_lookup[selection]()
            elif len(self.save_dir_contents) == 3:
                selection = self.game_functions.main_menu_selection(get_ticks(), screen,
                                                                    self.directories.continue_quest_full_log_unselected,
                                                                    self.directories.continue_quest_full_log_0,
                                                                    [self.directories.continue_quest_full_log_1,
                                                                     self.directories.continue_quest_full_log_2],
                                                                    no_blit=self.game_state.config['NO_BLIT'])
            else:
                print("Error: More than 3 save files detected. Exiting.")
                exit(1)

    def begin_new_quest(self):
        self.select_adventure_log(self.screen)
        name_selection = NameSelection(self.config)
        self.player.name = name_selection.select_name(get_ticks(), self.screen, self.cmd_menu)
        self.player.set_initial_stats()
        self.sound.play_sound(self.directories.menu_button_sfx)
        fade(fade_out=True, screen=self.screen, config=self.game_state.config)
        self.music_player.load_and_play_music(self.current_map.music_file_path)
        self.cmd_menu = CommandMenu(self)

    def continue_quest(self):
        # make the window the right size based on self.save_dir_contents
        # populate the save file list with the player names
        # allow the user to select a save file
        # load the save file
        if len(self.save_dir_contents) == 1:
            self.game_functions.main_menu_selection(get_ticks(), self.screen,
                                                    self.directories.one_adventure_log_unselected,
                                                    self.directories.one_adventure_log_0,
                                                    [],
                                                    no_blit=self.game_state.config['NO_BLIT'])
            with open(os.path.join(self.directories.save_dir, self.save_dir_contents[0])) as save_file:
                loaded_save = json.load(save_file)
                self.load_game(loaded_save)
            self.game_state.game_loaded_from_save = True

        self.sound.play_sound(self.directories.menu_button_sfx)
        fade(fade_out=True, screen=self.screen, config=self.game_state.config)
        self.music_player.load_and_play_music(self.current_map.music_file_path)
        self.cmd_menu = CommandMenu(self)

    def change_message_speed(self):
        # make the window the right size based on self.save_dir_contents
        # populate the save file list with the player names
        # allow the user to select a save file
        # pop up a menu to change the message speed

        # "Which Message Speed Do You Want To Use?"
        # >FAST
        #  NORMAL
        #  SLOW

        pass

    def copy_quest(self):
        # copy the save file to a new save file
        pass

    def erase_quest(self):
        # erase the save file
        pass

    def select_adventure_log(self, screen):
        self.player.adventure_log = self.game_functions.main_menu_selection(get_ticks(), screen,
                                                                            self.directories.empty_log_adventure_log_path,
                                                                            self.directories.ADVENTURE_LOG_1_PATH,
                                                                            [
                                                                                self.directories.ADVENTURE_LOG_2_PATH,
                                                                                self.directories.ADVENTURE_LOG_3_PATH]) + 1

    def get_events(self) -> None:
        """
        Handle all events in main loop.
        :return: None
        """
        self.events = get()
        for current_event in self.events:
            if current_event.type == QUIT:
                quit()
            elif current_event.type == KEYDOWN:
                self.handle_keypresses(current_event)
            elif current_event.type == arrow_fade:
                self.show_arrow = not self.show_arrow
        if self.game_state.enable_movement and not self.paused and not self.cmd_menu.menu.is_enabled():
            current_key = key.get_pressed()
            self.move_player(current_key)
        event.pump()
        self.set_text_color()
        self.handle_battles()
        if not self.player.is_moving:
            set_character_position(self.player, tile_size=self.tile_size)
        if self.enable_roaming and self.current_map.roaming_characters:
            self.move_roaming_characters()
            self.update_roaming_character_positions()

        # currently can't process staircases right next to one another, need to fix
        # a quick fix would be to add an exception in the conditional for
        # the map where staircases right next to each other need to be enabled,
        # as done with Cantlin and others below
        self.handle_warps()

        self.player.current_tile = get_tile_id_by_coordinates(self.player.rect.x // self.tile_size,
                                                              self.player.rect.y // self.tile_size,
                                                              self.current_map)
        self.cmd_menu.current_tile = self.player.current_tile

        self.player.next_tile_id = self.calculation.get_next_tile_identifier(self.player.column, self.player.row,
                                                                             self.player.direction_value,
                                                                             self.current_map)

        self.player.next_coordinates = get_next_coordinates(self.player.rect.x // self.tile_size,
                                                            self.player.rect.y // self.tile_size,
                                                            self.player.direction_value)
        self.player.next_next_coordinates = get_next_coordinates(self.player.rect.x // self.tile_size,
                                                                 self.player.rect.y // self.tile_size,
                                                                 self.player.direction_value, offset_from_character=2)

        self.set_player_images_by_equipment()

        self.handle_environment_damage()

        self.handle_death()

        # Debugging area

        # This prints out the current tile that the player is standing on.
        # print(f"self.player.current_tile: {self.player.current_tile}")

        if self.show_coordinates:
            print(f"{self.player.row, self.player.column}")

        # print(self.camera.get_pos())

        # print(f"Inventory: {self.player.inventory}, Gold: {self.player.gold}")
        # print(self.tiles_moved_since_spawn)

        # This prints out the next coordinates that the player will land on.
        # print(self.player.next_coordinates)

        # This prints out the next tile that the player will land on.
        # print(get_tile_id_by_coordinates(self.player.next_coordinates[1], self.player.next_coordinates[0], self.current_map))

        # This prints out the current FPS.
        if self.game_state.config["SHOW_FPS"]:
            print(self.clock.get_fps())

        # This prints out the next_tile, and the next_next_tile.
        # print(f'Next tile: {self.player.next_tile_id}')
        # print(f'Next next tile: {self.player.next_next_tile_id}')
        # print(f'{get_tile_id_by_coordinates(self.player.next_coordinates[0], self.player.next_coordinates[1], self.current_map)}')
        # print(f'{get_tile_id_by_coordinates(self.player.next_next_coordinates[0], self.player.next_next_coordinates[1], self.current_map)}')

        event.pump()

    def set_text_color(self):
        if self.player.current_hp <= self.player.max_hp * 0.125:
            self.cmd_menu.game.color, self.color = RED, RED
        else:
            self.cmd_menu.game.color, self.color = WHITE, WHITE

    def handle_battles(self):
        maps_with_enemies = (
            'Alefgard', 'Hauksness',
            'CharlockB2', 'CharlockB3', 'CharlockB4', 'CharlockB5', 'CharlockB6', 'CharlockB7Wide', 'CharlockB7Narrow',
            'CharlockB8', 'SwampCave', 'MountainCaveB1')
        if self.current_map.identifier in maps_with_enemies:
            if self.tiles_moved_since_spawn > 0:
                # TODO: Add other maps with enemies besides Alefgard/Hauksness.
                if self.tiles_moved_since_spawn != self.last_amount_of_tiles_moved:
                    if self.current_map.identifier == 'Alefgard':
                        current_zone = self.player.column // 18, self.player.row // 18
                    elif self.current_map.identifier == 'Hauksness':
                        current_zone = (3, 7)  # force dark_blue zone
                    elif self.current_map.identifier == 'SwampCave':
                        current_zone = (-1, -1)
                    else:
                        current_zone = None
                    if current_zone:
                        enemies_in_current_zone = enemy_territory_map.get(current_zone)
                        # "Zone 0" in the original code is zone (3, 2)
                        if current_zone == (3, 2):
                            random_integer = self.handle_near_tantegel_fight_modifier()
                        else:
                            random_integer = self.get_random_integer_by_tile()
                        self.launch_battle = random_integer == 0 or self.game_state.config["FORCE_BATTLE"]
                        if self.launch_battle and not self.game_state.config["NO_BATTLES"]:
                            self.battle(enemies_in_current_zone)
                        self.battle_menu_row = 0
                        self.battle_menu_column = 0
                    # if self.last_zone != current_zone:
                    #     print(f'Zone: {current_zone}\nEnemies: {enemies_in_current_zone}')
                    self.last_zone = current_zone
                self.last_amount_of_tiles_moved = self.tiles_moved_since_spawn

    def battle(self, enemies_in_current_zone):
        enemy_name = random.choice(enemies_in_current_zone)
        current_battle = Battle(self.config, enemy_name, self.current_map)
        current_battle.play_battle_music()
        # TODO: Group parameters into respective classes.
        current_battle.display_battle_window(self.screen, self.drawer,
                                             self.cmd_menu, self.graphics, self.directories,
                                             self.color, self.player)

        run_away = False
        while current_battle.enemy.hp > 0 and not run_away and not self.player.is_dead:
            # TODO: Figure out run away bug (when player attempts to run, enemy always gets one extra turn).
            run_away = self.handle_battle_prompts(run_away, current_battle)
        if current_battle.enemy.hp <= 0:
            current_battle.enemy_defeated(self.cmd_menu, self.screen, self.player, self.music_enabled,
                                          current_battle.enemy)
        # TODO: Refactor to music player class with Swatjen.
        self.music_player.load_and_play_music(self.current_map.music_file_path)

    def handle_battle_prompts(self, run_away: bool, current_battle: Battle) -> bool:
        battle_menu_options = ({'Fight': self.directories.BATTLE_MENU_FIGHT_PATH,
                                'Spell': self.directories.BATTLE_MENU_SPELL_PATH},
                               {'Run': self.directories.BATTLE_MENU_RUN_PATH,
                                'Item': self.directories.BATTLE_MENU_ITEM_PATH})
        x, y, width, height = 6, 1, 8, 3
        tile_size = self.game_state.config["TILE_SIZE"]
        selected_image = list(battle_menu_options[self.battle_menu_row].values())[self.battle_menu_column]
        battle_window_rect = self.graphics.blink_switch(self.screen, selected_image,
                                                        self.directories.BATTLE_MENU_STATIC_PATH, x, y,
                                                        width, height,
                                                        tile_size, self.show_arrow, color=self.color)
        current_selection = list(battle_menu_options[self.battle_menu_row].keys())[self.battle_menu_column]
        selected_executed_option = None
        random_number = random.random()
        if self.enemy_runaway_attempts == 0 or self.enemy_runaway_attempts == current_battle.turn:
            if self.player.strength >= (current_battle.enemy.attack * 2):
                if random_number < 0.25:
                    self.enemy_runaway_attempts = 0
                    return self.enemy_run_away(current_battle, current_battle.enemy)
                else:
                    self.enemy_runaway_attempts += 1
        for current_event in event.get():
            if current_event.type == KEYDOWN:
                if not self.player.is_asleep:
                    if current_event.key in accept_keys:
                        self.sound.play_sound(self.directories.menu_button_sfx)
                        selected_executed_option = current_selection
                    elif current_event.key in reject_keys:
                        break
                    elif current_event.key in (K_DOWN, K_s, K_UP, K_w):
                        self.battle_menu_row = 1 - self.battle_menu_row
                    elif current_event.key in (K_LEFT, K_a, K_RIGHT, K_d):
                        self.battle_menu_column = 1 - self.battle_menu_column
                    time.set_timer(arrow_fade, 530)
                else:
                    selected_executed_option = 'Sleep'
            elif current_event.type == arrow_fade:
                self.show_arrow = not self.show_arrow
            if selected_executed_option:
                self.graphics.create_window(x, y, width, height, selected_image, self.screen, self.color)
                display.update(battle_window_rect)
                time.set_timer(arrow_fade, 530)
                if selected_executed_option == 'Fight':
                    self.fight(current_battle)
                elif selected_executed_option == 'Spell':
                    current_battle.battle_spell(self.cmd_menu, self.player, current_battle)
                elif selected_executed_option == 'Run':
                    run_away = current_battle.battle_run(self.cmd_menu, self.player, current_battle)
                    if run_away:
                        self.music_player.load_and_play_music(self.current_map.music_file_path)
                        return run_away
                elif selected_executed_option == 'Item':
                    if not self.player.inventory:
                        self.cmd_menu.show_line_in_dialog_box(
                            'Nothing of use has yet been given to thee.\n',
                            add_quotes=False, hide_arrow=True, disable_sound=True)
                        current_battle.no_op = True
                elif selected_executed_option == 'Sleep':
                    self.cmd_menu.show_line_in_dialog_box(self._("Thou art still asleep.\n"),
                                                          add_quotes=False, disable_sound=True,
                                                          hide_arrow=True, skip_text=True)
                current_battle.last_turn = current_battle.turn
                current_battle.turn += 1
                selected_executed_option = None
                time.set_timer(arrow_fade, 530)
                if current_battle.enemy.hp <= 0:
                    run_away = False
                    return run_away
                elif current_battle.last_turn != current_battle.turn:
                    if not current_battle.no_op:
                        self.enemy_move(current_battle)
                        if self.player.current_hp <= 0:
                            self.drawer.draw_hovering_stats_window(self.screen, self.player, RED)
                            self.player.is_dead = True

                        elif self.player.is_asleep:
                            self.player.asleep_turns += 1
                            if self.player.asleep_turns >= 6 or random.randint(0, 1) == 1:
                                self.player.is_asleep = False
                                self.player.asleep_turns = 0
                                self.cmd_menu.show_line_in_dialog_box(
                                    self._("{} awakes.\n").format(self.player.name) + "Command?\n",
                                    add_quotes=False, disable_sound=True,
                                    hide_arrow=True)
                            else:
                                self.cmd_menu.show_line_in_dialog_box(self._("Thou art still asleep.\n"),
                                                                      add_quotes=False, disable_sound=True,
                                                                      hide_arrow=True, skip_text=True)
                        else:
                            self.cmd_menu.show_line_in_dialog_box(self._("Command?\n"),
                                                                  add_quotes=False, disable_sound=True, hide_arrow=True,
                                                                  skip_text=True)
                    else:
                        current_battle.no_op = False
                        self.cmd_menu.show_line_in_dialog_box(self._("Command?\n"),
                                                              add_quotes=False, disable_sound=True, hide_arrow=True,
                                                              skip_text=True)
            elif current_event.type == QUIT:
                quit()
        return run_away

    def enemy_run_away(self, current_battle, enemy):
        self.sound.play_sound(self.directories.stairs_down_sfx)
        self.cmd_menu.show_line_in_dialog_box(self._("The {} is running away.").format(self._(enemy.name)),
                                              add_quotes=False, disable_sound=True, hide_arrow=True)
        current_battle.make_enemy_image_disappear(self.screen)
        if self.config["MUSIC_ENABLED"]:
            mixer.music.load(self.current_map.music_file_path)
            mixer.music.play(-1)
        return True

    def fight(self, current_battle):
        self.hero_attack(current_battle)

    def hero_attack(self, current_battle):
        self.sound.play_sound(self.directories.attack_sfx)
        self.cmd_menu.show_line_in_dialog_box(self._("{} attacks!\n").format(self.player.name),
                                              add_quotes=False, disable_sound=True, hide_arrow=True)
        attack_damage = current_battle.calculate_attack_damage(self.cmd_menu, self.player, current_battle.enemy)
        if attack_damage <= 0:
            current_battle.missed_attack(self.cmd_menu)
        elif random.random() < current_battle.enemy.dodge:
            self.sound.play_sound(self.directories.missed_sfx)
            self.cmd_menu.show_line_in_dialog_box(self._("It is dodging!\n").format(self._(current_battle.enemy.name)),
                                                  add_quotes=False, disable_sound=True, hide_arrow=True)
        else:
            self.sound.play_sound(self.directories.hit_sfx)
            self.cmd_menu.show_line_in_dialog_box(
                self._("The {}'s Hit Points have been reduced by {}.\n").format(self._(current_battle.enemy.name),
                                                                                attack_damage),
                add_quotes=False,
                disable_sound=True, hide_arrow=True)
            current_battle.enemy.hp -= attack_damage
            # print(f"{enemy.name} HP: {enemy.hp}/{enemy_string_lookup[enemy.name]().hp}")

    def enemy_move(self, current_battle: Battle):
        if not current_battle.enemy.pattern:
            self.enemy_attack(current_battle)
        else:
            current_index = 0
            current_enemy_pattern = current_battle.enemy.pattern[current_index]
            self.execute_enemy_pattern(current_battle, current_enemy_pattern, current_index, current_battle.enemy)

    def execute_enemy_pattern(self, current_battle, current_enemy_pattern, current_index, enemy):
        enemy.refresh_pattern()
        if isinstance(current_enemy_pattern, tuple):
            # (X% chance to do current_spell if Z)
            x = current_enemy_pattern[0]
            current_spell = current_enemy_pattern[1]
            z = current_enemy_pattern[2]
            if current_spell == "SLEEP" and self.player.is_asleep:
                z = False
            if z:
                if random.randint(0, 100) < x:
                    if current_spell not in ("FIREBREATH", "FIREBREATH2"):
                        self.cmd_menu.show_line_in_dialog_box(
                            self._("{} chants the spell of {}.").format(self._(enemy.name),
                                                                        self._(current_spell)), add_quotes=False,
                            disable_sound=True, hide_arrow=True)

                        self.sound.play_sound(self.directories.spell_sfx)

                    else:
                        self.cmd_menu.show_line_in_dialog_box(
                            self._("The {} is breathing fire.\n").format(self._(enemy.name)),
                            add_quotes=False, disable_sound=True, hide_arrow=True)
                        self.sound.play_sound(self.directories.breathe_fire_sfx)
                    time.wait(1000)
                    spell_effect_lower_bound, spell_effect_upper_bound = enemy_spell_lookup[current_spell]
                    spell_effect = random.randint(spell_effect_lower_bound, spell_effect_upper_bound)
                    if current_spell in ("HEAL", "HEALMORE"):
                        enemy.recover_hp(spell_effect)
                    elif current_spell == "SLEEP":
                        self.player.is_asleep = True
                        self.cmd_menu.show_line_in_dialog_box(self._("Thou art asleep.\n"), add_quotes=False,
                                                              disable_sound=True, hide_arrow=True)
                    elif current_spell in ("HURT", "HURTMORE"):
                        if self.player.armor in ("Magic Armor", "Erdrick's Armor"):
                            spell_effect *= 0.66
                        self.receive_damage(spell_effect)
                    elif current_spell == "STOPSPELL":
                        if self.player.armor != "Erdrick's Armor":
                            if random.randint(0, 1) == 1:
                                self.player.is_stopspelled = True
                    elif current_spell in ("FIREBREATH", "FIREBREATH2"):
                        if self.player.armor == "Erdrick's Armor":
                            spell_effect *= 0.66
                        self.receive_damage(spell_effect)
                else:
                    self.increment_and_execute_enemy_pattern(current_battle, current_index, enemy)
            else:
                self.increment_and_execute_enemy_pattern(current_battle, current_index, enemy)
        elif isinstance(current_enemy_pattern, str):
            # (do X)
            if current_enemy_pattern == "ATTACK":
                self.enemy_attack(current_battle)

            # (EnemyAttack - HeroAgility / 2) / 4,
            #
            # to:
            #
            # (EnemyAttack - HeroAgility / 2) / 2

    def increment_and_execute_enemy_pattern(self, current_battle, current_index, enemy):
        current_index += 1
        # print(f"{enemy.name} current_index: {current_index}")
        # print(f"{enemy.name} pattern: {enemy.pattern}")
        if enemy.pattern:
            current_enemy_pattern = enemy.pattern[current_index]
            self.execute_enemy_pattern(current_battle, current_enemy_pattern, current_index, enemy)
        else:
            self.enemy_attack(current_battle, enemy)

    def enemy_attack(self, current_battle):
        self.enemy_attack_message(current_battle.enemy)
        self.execute_enemy_attack(current_battle)

    def execute_enemy_attack(self, current_battle):
        attack_damage = calculate_enemy_attack_damage(self.player, current_battle.enemy)
        if attack_damage <= 0:
            current_battle.missed_attack(self.cmd_menu)
        else:
            self.receive_damage(attack_damage)

    def enemy_attack_message(self, enemy):
        self.sound.play_sound(self.directories.prepare_attack_sfx)
        self.cmd_menu.show_line_in_dialog_box(self._("The {} attacks!\n").format(self._(enemy.name)),
                                              add_quotes=False, disable_sound=True, hide_arrow=True)

    def receive_damage(self, attack_damage):
        self.sound.play_sound(self.directories.receive_damage_2_sfx)
        self.player.current_hp -= attack_damage
        self.color = self.cmd_menu.color = self.get_current_color()
        if self.player.current_hp < 0:
            self.player.current_hp = 0
        self.drawer.draw_hovering_stats_window(self.screen, self.player, self.color)
        # create_window(6, 1, 8, 3, BATTLE_MENU_FIGHT_PATH, self.screen, self.color)
        self.cmd_menu.show_line_in_dialog_box(self._("Thy Hit Points decreased by {}.\n").format(attack_damage),
                                              add_quotes=False, disable_sound=True, hide_arrow=True, skip_text=True if
            self.player.current_hp == 0 else False)
        # print(f"{self.player.name} HP: {self.player.current_hp}/{self.player.max_hp}")

    def get_current_color(self):
        return RED if self.player.current_hp <= self.player.max_hp * 0.125 else WHITE

    def handle_near_tantegel_fight_modifier(self):
        if self.player.current_tile == 'HILLS':
            sub_random_integer = random.randint(0, 3)
        else:
            sub_random_integer = random.randint(0, 1)
        if sub_random_integer == 0:
            random_integer = self.get_random_integer_by_tile()
        else:
            random_integer = 1
        return random_integer

    def get_random_integer_by_tile(self):
        match self.player.current_tile:
            case 'SWAMP':
                random_integer = random.randint(0, 15)
            case 'DESERT':
                random_integer = random.randint(0, 7)
            case 'HILLS':
                random_integer = random.randint(0, 7)
            case 'FOREST':
                random_integer = random.randint(0, 15)
            case 'BRICK':
                random_integer = random.randint(0, 15)
            case 'BARRIER':
                random_integer = random.randint(0, 15)
            case _:  # default
                if self.player.column % 2 == 0:
                    if self.player.row % 2 == 0:
                        random_integer = random.randint(0, 31)
                    else:
                        random_integer = random.randint(0, 15)
                else:
                    if self.player.row % 2 == 0:
                        random_integer = random.randint(0, 31)
                    else:
                        random_integer = random.randint(0, 15)
        return random_integer

    def set_player_images_by_equipment(self):
        if self.player.weapon:
            if self.player.shield:
                self.player.images = self.current_map.scale_sprite_sheet(self.directories.ARMED_HERO_WITH_SHIELD_PATH)
                self.player.set_images(self.player.images)

            else:
                self.player.images = self.current_map.scale_sprite_sheet(self.directories.ARMED_HERO_PATH)
                self.player.set_images(self.player.images)
        elif self.player.shield:
            self.player.images = self.current_map.scale_sprite_sheet(self.directories.UNARMED_HERO_WITH_SHIELD_PATH)
            self.player.set_images(self.player.images)

    def handle_death(self):
        if self.player.current_hp <= 0:
            self.player.current_hp = 0
            self.player.is_dead = True
            self.color = RED
            if self.launch_battle and not self.game_state.config["NO_BATTLES"]:
                self.graphics.create_window(6, 1, 8, 3, self.directories.BATTLE_MENU_FIGHT_PATH, self.screen, RED)
                self.launch_battle = False
                display.flip()
            else:
                self.drawer.draw_all_tiles_in_current_map(self.current_map, self.drawer.background)
                display.flip()
            self.music_player.load_and_play_music(self.directories.death_sfx, 1)
            self.game_state.enable_movement = False
            death_start_time = get_ticks()
            while self.calculation.convert_to_frames_since_start_time(death_start_time) < 318:
                if not self.game_state.config['NO_WAIT']:
                    time.wait(1)
            event.clear()

            self.cmd_menu.show_text_in_dialog_box(self.cmd_menu.dialog_lookup.thou_art_dead, disable_sound=True)
            self.set_post_death_attributes()
        else:
            self.player.is_dead = False

    def set_post_death_attributes(self):
        next_map = map_lookup['TantegelThroneRoom'](self.config)
        self.change_map(next_map)
        self.player.gold = self.player.gold // 2
        # revive player
        self.player.current_hp = self.player.max_hp
        self.player.is_dead = False
        self.game_state.is_post_death_dialog = True
        self.color = self.cmd_menu.color = WHITE

    def handle_environment_damage(self):
        if not self.player.armor == "Erdrick's Armor":
            if not self.player.is_moving:
                if self.player.current_tile == 'MARSH':
                    if not self.player.received_environment_damage:
                        self.damage_step(damage_amount=2)
                elif self.player.current_tile == 'BARRIER':
                    if not self.player.received_environment_damage:
                        self.damage_step(damage_amount=15)
            else:
                self.player.received_environment_damage = False

    def damage_step(self, damage_amount):
        self.player.current_hp -= damage_amount
        self.sound.play_sound(self.directories.swamp_sfx)
        self.player.received_environment_damage = True
        flash_transparent_color(RED, self.screen, self.calculation, no_blit=self.game_state.config['NO_BLIT'])
        self.drawer.draw_all(self.screen, self.loop_count, self.big_map, self.current_map, self.player, self.cmd_menu,
                             self.foreground_rects, self.enable_animate, self.camera, self.initial_dialog_enabled,
                             self.events, self.skip_text, self.allow_save_prompt, self.game_state, self.torch_active,
                             self.color)
        display.flip()

    def handle_warps(self):
        immediate_move_maps = ('Brecconary', 'Cantlin', 'Hauksness', 'Rimuldar', 'CharlockB1', 'MagicTemple',
                               'Alefgard', 'MountainCaveB1', 'MountainCaveB2')
        # a quick fix to prevent buggy warping - set to > 2
        if self.tiles_moved_since_spawn > 2 or (
                self.tiles_moved_since_spawn > 1 and self.current_map.identifier in immediate_move_maps):
            for staircase_location, staircase_dict in self.current_map.staircases.items():
                if (self.player.row, self.player.column) == staircase_location:
                    self.process_warp(staircase_dict)
                    break

    def process_warp(self, staircase_dict):
        self.player.bumped = False
        match staircase_dict['stair_direction']:
            case 'down':
                self.sound.play_sound(self.directories.stairs_down_sfx)
            case 'up':
                self.sound.play_sound(self.directories.stairs_up_sfx)
        next_map = map_lookup[staircase_dict['map']](self.config)
        self.change_map(next_map)

    def handle_keypresses(self, current_keydown_event):
        self.handle_b_button(current_keydown_event)
        self.handle_a_button(current_keydown_event)
        self.handle_start_button(current_keydown_event)
        self.handle_select_button(current_keydown_event)
        # TODO: Allow for zoom in and out if Ctrl + PLUS | MINUS is pressed (or scroll wheel is moved). (modernization)
        # if key[pg.K_LCTRL] and (key[pg.K_PLUS] or key[pg.K_KP_PLUS]):
        #     self.scale = self.scale + 1
        self.handle_help_button(current_keydown_event)
        self.handle_enter_key(current_keydown_event)
        self.handle_fps_changes(current_keydown_event)

    def handle_help_button(self, keydown_event):
        control_info = ControlInfo(self.config)
        if keydown_event.key == K_F1:
            self.cmd_menu.show_text_in_dialog_box(
                self._("Controls:\n") + convert_list_to_newline_separated_string(control_info.controls))

    def handle_b_button(self, keydown_event):
        if keydown_event.key in reject_keys:
            # B button
            # using reject_keys adds ESC as an option to unlaunch the command menu
            self.unlaunch_menu(self.cmd_menu)
            # print("J key pressed (B button).")

    def handle_a_button(self, keydown_event):
        if keydown_event.key == K_k:
            # A button
            # print("K key pressed (A button).")
            if not self.player.is_moving:
                # pause_all_movement may be temporarily commented out for dialog box debugging purposes.
                self.drawer.display_hovering_stats = True
                self.cmd_menu.launch_signaled = True
                self.game_state.pause_all_movement()

    def handle_start_button(self, keydown_event):
        if keydown_event.key == K_i:
            # Start button
            if self.paused:
                self.game_state.unpause_all_movement()
                self.paused = False
            else:
                self.game_state.pause_all_movement()
                self.paused = True
            print("I key pressed (Start button).")

    def handle_enter_key(self, keydown_event):
        if keydown_event.key == K_RETURN:
            if self.player.current_tile == 'TREASURE_BOX':
                self.drawer.draw_hovering_stats_window(self.screen, self.player, color=self.color)
                self.cmd_menu.take()
            elif self.player.next_tile_id == 'DOOR':
                self.cmd_menu.door()
            elif self.cmd_menu.check_across_from_npc() and not self.game_state.is_initial_dialog:
                self.drawer.draw_hovering_stats_window(self.screen, self.player, color=self.color)
                self.cmd_menu.talk()

    @staticmethod
    def handle_select_button(keydown_event):
        if keydown_event.key == K_u:
            # Select button
            pass

    def handle_fps_changes(self, keydown_event) -> None:
        if keydown_event.key == K_1:
            self.draw_temporary_text(self.cmd_menu.dialog_lookup.normal_speed_string)
            self.fps = 60
        if keydown_event.key == K_2:
            self.draw_temporary_text(self.cmd_menu.dialog_lookup.double_speed_string)
            self.fps = 120
        if keydown_event.key == K_3:
            self.draw_temporary_text(self.cmd_menu.dialog_lookup.triple_speed_string)
            self.fps = 240
        if keydown_event.key == K_4:
            self.draw_temporary_text(self.cmd_menu.dialog_lookup.quadruple_speed_string)
            self.fps = 480

    def update_roaming_character_positions(self) -> None:
        for character, character_dict in self.current_map.characters.items():
            if character_dict['character'].__class__.__name__ == 'RoamingCharacter':
                if not character_dict['character'].is_moving:
                    set_character_position(character_dict['character'], tile_size=self.tile_size)

    def draw_temporary_text(self, text: Tuple[str] | List[str] | str, add_quotes=False) -> None:
        self.cmd_menu.show_text_in_dialog_box(text, add_quotes=add_quotes, temp_text_start=get_ticks(), skip_text=False)

    def process_staircase_warps(self, staircase_location: tuple, staircase_dict: dict) -> None:
        if (self.player.row, self.player.column) == staircase_location:
            self.process_warp(staircase_dict)

    def change_map(self, next_map: maps.DragonWarriorMap) -> None:
        """
        Change to a different map.
        :param next_map: The next map to be loaded.
        :return: None
        """
        if self.last_map is not None:
            came_from_throne_room = self.current_map.identifier == 'TantegelThroneRoom'
            came_from_courtyard = self.current_map.identifier == 'TantegelCourtyard'
        else:
            came_from_throne_room = True
            came_from_courtyard = False
        self.game_state.pause_all_movement()
        self.last_map = self.current_map
        self.current_map = next_map
        moving_within_tantegel_castle = came_from_throne_room or came_from_courtyard
        for character_coordinates, tile_value in self.last_map.character_position_record.items():
            self.last_map.layout[character_coordinates[0]][character_coordinates[1]] = tile_value
        if not self.allow_save_prompt:
            if came_from_throne_room:
                self.allow_save_prompt = True
        self.current_map.layout = self.layouts.map_layout_lookup[self.current_map.__class__.__name__]
        fade(fade_out=True, screen=self.screen, config=self.game_state.config)
        self.set_big_map()
        self.set_roaming_character_positions()
        if self.music_enabled:
            if not moving_within_tantegel_castle and not self.config['ORCHESTRA_MUSIC_ENABLED']:
                mixer.music.stop()
        if not self.player.is_dead:
            current_map_staircase_dict = self.last_map.staircases[(self.player.row, self.player.column)]
            destination_coordinates = current_map_staircase_dict.get('destination_coordinates')
        else:
            current_map_staircase_dict = None
            destination_coordinates = (10, 13)  # TantegelThroneRoom, in front of King Lorik
        self.current_map.destination_coordinates = destination_coordinates
        initial_hero_location = self.current_map.get_initial_character_location('HERO')
        if not initial_hero_location:
            initial_hero_location = self.player.row, self.player.column
        if destination_coordinates:
            if self.current_map.initial_coordinates != destination_coordinates:
                self.reset_initial_hero_location_tile()
            self.set_underlying_tiles_on_map_change(destination_coordinates, initial_hero_location)
            self.current_map.layout[destination_coordinates[0]][destination_coordinates[1]] = 33
        self.current_map.load_map(self.player, destination_coordinates, self.tile_size)
        if not self.current_map.is_dark:
            self.torch_active = False
            self.game_state.radiant_active = False
        self.handle_player_direction_on_map_change(current_map_staircase_dict)
        #  this is probably what we need here:

        #    self.camera = Camera((self.player.rect.x // self.tile_size, self.player.rect.y // self.tile_size),
        #                              current_map=self.current_map, screen=self.screen)
        self.camera = Camera(hero_position=(int(self.player.column), int(self.player.row)),
                             current_map=self.current_map, screen=self.screen, tile_size=self.tile_size)
        # self.fade(self.current_map.width, self.current_map.height, fade_out=False)
        self.loop_count = 1
        self.game_state.unpause_all_movement()
        self.tiles_moved_since_spawn = 0
        self.cmd_menu = CommandMenu(self)
        # TODO: Allow music to continue playing when moving within Tantegel Castle.
        # if not moving_within_tantegel_castle and self.config['ORCHESTRA_MUSIC_ENABLED']:
        self.music_player.load_and_play_music(self.current_map.music_file_path)
        if destination_coordinates:
            # really not sure if the 1 and 0 here are supposed to be switched
            self.camera.set_camera_position((destination_coordinates[1], destination_coordinates[0]), self.tile_size)

    def set_underlying_tiles_on_map_change(self, destination_coordinates, initial_hero_location):
        if self.player.current_tile in ('BRICK_STAIR_DOWN', 'GRASS_STAIR_DOWN', 'CAVE'):
            self.current_map.character_key['HERO']['underlying_tile'] = 'BRICK_STAIR_UP'
        elif self.player.current_tile == 'BRICK_STAIR_UP' and self.current_map.identifier != 'Alefgard':
            self.current_map.character_key['HERO']['underlying_tile'] = 'BRICK_STAIR_DOWN'
        else:
            if destination_coordinates != initial_hero_location:
                self.current_map.character_key['HERO']['underlying_tile'] = self.current_map.get_tile_by_value(
                    self.current_map.layout[destination_coordinates[0]][destination_coordinates[1]])
            else:
                self.current_map.character_key['HERO']['underlying_tile'] = self.current_map.hero_underlying_tile()

    def reset_initial_hero_location_tile(self):
        initial_coordinates = self.current_map.initial_coordinates
        if self.current_map.layout[initial_coordinates[0]][initial_coordinates[1]] != \
                self.current_map.floor_tile_key[self.current_map.character_key['HERO']['underlying_tile']]['val']:
            self.current_map.layout[initial_coordinates[0]][initial_coordinates[1]] = \
                self.current_map.floor_tile_key[self.current_map.character_key['HERO']['underlying_tile']]['val']

    def set_big_map(self):
        self.big_map = Surface(  # lgtm [py/call/wrong-arguments]
            (self.current_map.width, self.current_map.height)).convert()
        self.big_map.fill(BLACK)
        self.drawer.background = self.big_map.subsurface(0, 0, self.current_map.width,
                                                         self.current_map.height).convert_alpha()

    def handle_player_direction_on_map_change(self, current_map_staircase_dict):
        if not self.player.is_dead:
            destination_direction = current_map_staircase_dict.get('direction')
            if destination_direction:
                self.player.direction_value = destination_direction
        else:
            self.player.direction_value = Direction.UP.value

    def set_roaming_character_positions(self):
        for roaming_character in self.current_map.roaming_characters:
            roaming_character.last_roaming_clock_check = get_ticks()
            set_character_position(roaming_character, self.tile_size)

    def unlaunch_menu(self, menu_to_unlaunch: Menu) -> None:
        """
        Un-launch a menu.
        :return: None
        """
        menu_to_unlaunch.launch_signaled = False
        if menu_to_unlaunch.menu.get_id() == 'command':
            if self.cmd_menu.menu.is_enabled():
                self.game_state.unpause_all_movement()
                self.cmd_menu.window_drop_up_effect(6, 1, 8, 5)
                self.cmd_menu.menu.disable()
        self.drawer.draw_all_tiles_in_current_map(self.current_map, self.drawer.background)

    def move_player(self, current_key) -> None:
        """
        Move the player in a specified direction.
        :param current_key: The key currently being pressed by the user.
        """
        # TODO(ELF): Allow for key taps, to just face in a particular direction
        # block establishes direction if needed and whether to start or stop moving
        # TODO(ELF): separate dependency of camera pos and player pos
        curr_pos_x, curr_pos_y = self.camera.get_pos()

        if not self.player.is_moving:
            if current_key[K_UP] or current_key[K_w]:
                self.player.direction_value = Direction.UP.value
            elif current_key[K_DOWN] or current_key[K_s]:
                self.player.direction_value = Direction.DOWN.value
            elif current_key[K_LEFT] or current_key[K_a]:
                self.player.direction_value = Direction.LEFT.value
            elif current_key[K_RIGHT] or current_key[K_d]:
                self.player.direction_value = Direction.RIGHT.value
            else:  # player not moving and no moving key pressed
                return
            self.player.is_moving = True
        else:  # determine if player has reached new tile
            # not sure if setting the player sprites to dirty makes a difference
            self.current_map.player_sprites.dirty = 1
            if is_facing_medially(self.player):
                if curr_pos_y % self.tile_size == 0:
                    if not self.player.bumped:
                        # TODO(ELF): sometimes self.tiles_moved_since_spawn gets set to 1 when spawning -
                        #  should always be 0 when the map starts.
                        self.tiles_moved_since_spawn += 1
                        self.game_state.tiles_moved_total += 1
                    else:
                        self.player.bumped = False
                    self.player.is_moving, self.player.next_tile_checked = False, False
                    return
            elif is_facing_laterally(self.player):
                if curr_pos_x % self.tile_size == 0:
                    if not self.player.bumped:
                        self.tiles_moved_since_spawn += 1
                        self.game_state.tiles_moved_total += 1
                    else:
                        self.player.bumped = False
                    self.player.is_moving, self.player.next_tile_checked = False, False
                    return
        if is_facing_medially(self.player):
            self.move_medially(self.player)
        elif is_facing_laterally(self.player):
            self.move_laterally(self.player)
        self.current_map.player_sprites.dirty = 1

    def move_laterally(self, character: Player | RoamingCharacter) -> None:
        if is_facing_left(character):
            self.move(character, delta_x=-self.speed, delta_y=0)
        elif is_facing_right(character):
            self.move(character, delta_x=self.speed, delta_y=0)

    def move_medially(self, character: Player | RoamingCharacter) -> None:
        if is_facing_up(character):
            self.move(character, delta_x=0, delta_y=self.speed)
        elif is_facing_down(character):
            self.move(character, delta_x=0, delta_y=-self.speed)

    def move(self, character: Player | RoamingCharacter, delta_x: int, delta_y: int) -> None:
        """
        The method that actuates movement of characters from within the move_player method.
        :param character: Character to move
        :param delta_x: Change in x position.
        :param delta_y: Change in y position.
        :return: None
        """
        self.cmd_menu.camera_position = \
            curr_cam_pos_x, curr_cam_pos_y = next_cam_pos_x, next_cam_pos_y = self.camera.get_pos()
        self.check_next_tile(character)
        character.next_tile_id = self.calculation.get_next_tile_identifier(character.column, character.row,
                                                                           character.direction_value,
                                                                           self.current_map)
        character.next_next_tile_id = self.calculation.get_next_tile_identifier(character.column, character.row,
                                                                                character.direction_value,
                                                                                self.current_map, offset=2)
        if self.is_impassable(character.next_tile_id):
            self.movement.bump_and_reset(character, character.next_tile_id, character.next_next_tile_id)
        elif self.character_in_path(character):
            self.movement.bump_and_reset(character, character.next_tile_id, character.next_next_tile_id)
        else:
            if delta_x:
                character.rect.x += delta_x
                # this causes the fade out to happen a square before the player touches a staircase
                next_cam_pos_x = curr_cam_pos_x + -delta_x
                # character.column += delta_x // 2
            if delta_y:
                character.rect.y += -delta_y
                # this causes the fade out to happen a square before the player touches a staircase
                next_cam_pos_y = curr_cam_pos_y + delta_y
                # character.row += -delta_y // 2
        if character.identifier == 'HERO' and self.game_state.enable_movement:
            self.camera.set_pos(self.move_and_handle_sides_collision(next_cam_pos_x, next_cam_pos_y))

    def check_next_tile(self, character: Player | RoamingCharacter) -> None:
        if not character.next_tile_checked or not character.next_tile_id:
            character.next_tile_id = self.calculation.get_next_tile_identifier(character.column, character.row,
                                                                               character.direction_value,
                                                                               self.current_map)
        character.next_next_tile_id = self.calculation.get_next_tile_identifier(character.column, character.row,
                                                                                character.direction_value,
                                                                                self.current_map, offset=2)

    def character_in_path(self, character: RoamingCharacter | FixedCharacter) -> bool:
        fixed_character_locations = [(fixed_character.column, fixed_character.row) for fixed_character in
                                     self.current_map.fixed_characters]
        roaming_character_locations = [(roaming_character.column, roaming_character.row) for roaming_character in
                                       self.current_map.roaming_characters]
        next_coordinates = self.get_next_coordinates(character.column, character.row, character.direction_value)
        return next_coordinates in fixed_character_locations + roaming_character_locations + [
            (self.player.column, self.player.row)]

    def get_next_coordinates(self, character_column: int, character_row: int, direction: int) -> tuple:
        if character_row < len(self.current_map.layout) and character_column < len(self.current_map.layout[0]):
            if direction == Direction.UP.value:
                return character_column, character_row - 1
            elif direction == Direction.DOWN.value:
                return character_column, character_row + 1,
            elif direction == Direction.LEFT.value:
                return character_column - 1, character_row
            elif direction == Direction.RIGHT.value:
                return character_column + 1, character_row

    def is_impassable(self, tile: str) -> bool:
        """
        Check if a tile is impassable (a tile that blocks the player from moving).
        :param tile: Tile to be checked for impassibility.
        :return: bool: A boolean value stating whether the tile is impassable.
        """
        return tile in self.current_map.impassable_tiles

    def move_and_handle_sides_collision(self, next_pos_x: int, next_pos_y: int) -> tuple:
        """
        Move while handling collision with the sides of the map (for the player).
        :type next_pos_x: int
        :type next_pos_y: int
        :param next_pos_x: Next x position (in terms of tile size).
        :param next_pos_y: Next y position (in terms of tile size).
        :return: tuple: The x, y coordinates (in terms of tile size) of the next position of the player.
        """
        max_x_bound, max_y_bound = self.current_map.width - self.tile_size, self.current_map.height - self.tile_size
        min_bound = 0
        if self.player.rect.x < min_bound:
            self.player.rect.x = min_bound
            self.movement.bump(self.player)
            next_pos_x += -self.speed
        elif self.player.rect.x > max_x_bound:
            self.player.rect.x = max_x_bound
            self.movement.bump(self.player)
            next_pos_x += self.speed
        elif self.player.rect.y < min_bound:
            self.player.rect.y = min_bound
            self.movement.bump(self.player)
            next_pos_y -= self.speed
        elif self.player.rect.y > max_y_bound:
            self.player.rect.y = max_y_bound
            self.movement.bump(self.player)
            next_pos_y += self.speed
        return next_pos_x, next_pos_y

    def move_roaming_characters(self) -> None:
        """
        Move all roaming characters in the current map.
        :return: None
        """
        for roaming_character in self.current_map.roaming_characters:
            curr_pos_x, curr_pos_y = roaming_character.rect.x, roaming_character.rect.y
            # set_character_position(roaming_character)
            if roaming_character.last_roaming_clock_check is None or \
                    get_ticks() - roaming_character.last_roaming_clock_check >= 1000:
                roaming_character.last_roaming_clock_check = get_ticks()
                if not roaming_character.is_moving:
                    roaming_character.direction_value = random.choice(list(map(int, Direction)))
                else:  # character not moving and no input
                    return
                roaming_character.is_moving = True
            else:  # determine if character has reached new tile
                if is_facing_medially(roaming_character):
                    if curr_pos_y % self.tile_size == 0:
                        roaming_character.is_moving, roaming_character.next_tile_checked = False, False
                        return
                elif is_facing_laterally(roaming_character):
                    if curr_pos_x % self.tile_size == 0:
                        roaming_character.is_moving, roaming_character.next_tile_checked = False, False
                        return
            if is_facing_medially(roaming_character):
                self.move_medially(roaming_character)
            elif is_facing_laterally(roaming_character):
                self.move_laterally(roaming_character)
            # handle_roaming_character_sides_collision(self.current_map, roaming_character)

    def load_game(self, save_file: dict) -> None:
        """
        Load a game from a save file.
        """
        self.player.name = save_file["Name"]
        self.player.total_experience = save_file["Experience"]
        self.player.gold = save_file["Gold"]
        self.player.inventory = save_file["Inventory"]


def run():
    game = Game(config=prod_config)
    # game = Game(config=dev_config)
    game.main()


if __name__ == "__main__":
    run()
