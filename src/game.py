import random
import sys
from typing import List, Tuple

from pygame import FULLSCREEN, K_1, K_2, K_3, K_4, K_DOWN, K_LEFT, K_RIGHT, K_UP, K_a, K_d, K_i, K_j, K_k, K_s, \
    K_u, K_w, QUIT, RESIZABLE, Surface, display, event, image, init, key, mixer, quit, K_F1, time, KEYDOWN, Rect, \
    SCALED, K_RETURN
from pygame.display import set_mode, set_caption
from pygame.event import get
from pygame.sprite import Group
from pygame.time import Clock
from pygame.time import get_ticks
from pygame.transform import scale

from data.text.dialog import blink_switch
from src import maps, menu_functions
from src.camera import Camera
from src.common import BLACK, Direction, ICON_PATH, intro_overture, is_facing_laterally, \
    is_facing_medially, menu_button_sfx, stairs_down_sfx, stairs_up_sfx, village_music, get_next_tile_identifier, \
    UNARMED_HERO_PATH, \
    convert_to_frames_since_start_time, BEGIN_QUEST_SELECTED_PATH, BEGIN_QUEST_PATH, ADVENTURE_LOG_1_PATH, \
    ADVENTURE_LOG_PATH, ADVENTURE_LOG_2_PATH, ADVENTURE_LOG_3_PATH, swamp_sfx, death_sfx, RED, ARMED_HERO_PATH, \
    ARMED_HERO_WITH_SHIELD_PATH, \
    UNARMED_HERO_WITH_SHIELD_PATH, WHITE, torch_sfx, battle_music, victory_sfx, attack_sfx, hit_sfx, improvement_sfx, \
    BATTLE_BACKGROUND_PATH, BATTLE_MENU_STATIC_PATH, BATTLE_MENU_FIGHT_PATH, BATTLE_MENU_SPELL_PATH, \
    BATTLE_MENU_RUN_PATH, BATTLE_MENU_ITEM_PATH, missed_sfx, missed_2_sfx, \
    prepare_attack_sfx, receive_damage_2_sfx, excellent_move_sfx, create_window
from src.common import get_tile_id_by_coordinates, is_facing_up, is_facing_down, is_facing_left, is_facing_right
from src.config import NES_RES, SHOW_FPS, SPLASH_SCREEN_ENABLED, SHOW_COORDINATES, INITIAL_DIALOG_ENABLED, \
    ENABLE_DARKNESS, FORCE_BATTLE, NO_BATTLES
from src.config import SCALE, TILE_SIZE, FULLSCREEN_ENABLED, MUSIC_ENABLED, FPS
from src.drawer import Drawer, replace_characters_with_underlying_tiles, \
    get_surrounding_tile_values, convert_numeric_tile_list_to_unique_tile_values, \
    get_all_roaming_character_surrounding_tiles, get_fixed_character_underlying_tiles, handle_menu_launch, \
    set_to_save_prompt, handle_post_death_dialog
from src.enemy_lookup import enemy_territory_map, enemy_string_lookup
from src.game_functions import set_character_position, get_next_coordinates, select_from_vertical_menu, \
    get_surrounding_rect
from src.intro import Intro, controls
from src.map_layouts import MapLayouts
from src.maps import map_lookup
from src.menu import CommandMenu, Menu
from src.menu_functions import convert_list_to_newline_separated_string
from src.movement import bump_and_reset
from src.player.player import Player
from src.player.player_stats import levels_list
from src.sound import bump, play_sound
from src.sprites.fixed_character import FixedCharacter
from src.sprites.roaming_character import RoamingCharacter
from src.visual_effects import fade, flash_transparent_color


class GameState:
    # TODO: Add music_enabled
    def __init__(self):
        self.enable_movement = True
        self.enable_animate = True
        self.enable_roaming = True
        self.is_initial_dialog = True
        self.is_post_death_dialog = False
        self.automatic_initial_dialog_run = False

    def unpause_all_movement(self) -> None:
        """
        Unpause movement of animation, roaming, and character.
        :return: None
        """
        self.enable_animate, self.enable_roaming, self.enable_movement = True, True, True

    def pause_all_movement(self) -> None:
        """
        Pause movement of animation, roaming, and character.
        :return: None
        """
        self.enable_animate, self.enable_roaming, self.enable_movement = False, False, False


class Game:
    def __init__(self):
        self.game_state = GameState()
        self.drawer = Drawer(self.game_state)
        # map/graphics
        self.background = None
        self.big_map = None
        self.layouts = MapLayouts()
        self.fullscreen_enabled = FULLSCREEN_ENABLED
        # text
        self.initial_dialog_enabled = INITIAL_DIALOG_ENABLED
        self.skip_text = False

        # intro
        self.start_time = get_ticks()
        self.splash_screen_enabled = SPLASH_SCREEN_ENABLED
        # engine
        self.fps = FPS
        self.last_map = None
        self.last_zone = None
        self.last_amount_of_tiles_moved = 0
        self.tiles_moved_since_spawn = 0
        self.tiles_moved_total = 0
        self.radiant_start = None
        self.loop_count = 1
        self.foreground_rects = []
        self.not_moving_time_start = None
        self.hovering_stats_displayed = False
        self.torch_active = False
        self.radiant_active = False
        self.speed = 2
        self.launch_battle = False
        # debugging
        self.show_coordinates = SHOW_COORDINATES
        init()
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
        self.scale = SCALE
        # video_infos = display.Info()
        # current_screen_width, current_screen_height = video_infos.current_w, video_infos.current_h
        win_width, win_height = NES_RES[0] * self.scale, NES_RES[1] * self.scale
        self.screen = set_mode((win_width, win_height), self.flags)
        # self.screen.set_alpha(None)
        set_caption("Dragon Warrior")

        # self.current_map can be changed to other maps for development purposes

        self.current_map = maps.TantegelThroneRoom()
        # self.current_map = maps.ErdricksCaveB1()
        # self.current_map = maps.TantegelCourtyard()
        # self.current_map = maps.Alefgard()
        # self.current_map = maps.Brecconary()
        # self.current_map = maps.Garinham()
        # self.current_map = maps.Hauksness()
        # self.current_map = maps.Rimuldar()
        # self.current_map = maps.CharlockB1()

        self.set_big_map()

        self.set_roaming_character_positions()

        self.player = Player(center_point=None, images=self.current_map.scale_sprite_sheet(UNARMED_HERO_PATH),
                             current_map=self.current_map)
        self.current_map.load_map(self.player, None)
        self.color = RED if self.player.current_hp <= self.player.max_hp * 0.125 else WHITE

        # Good for debugging,
        # and will be useful later when the player's level increases and the stats need to be increased to match

        # self.player.total_experience = 26000
        # self.player.level = self.player.get_level_by_experience()
        # self.player.update_stats_to_current_level()

        self.player.current_tile = get_tile_id_by_coordinates(self.player.rect.x // TILE_SIZE,
                                                              self.player.rect.y // TILE_SIZE, self.current_map)
        self.camera = Camera((int(self.player.column), int(self.player.row)), self.current_map, self.screen)
        self.cmd_menu = CommandMenu(self)

        self.enable_animate = True
        self.enable_roaming = True
        self.clock = Clock()
        self.music_enabled = MUSIC_ENABLED

        if self.splash_screen_enabled:
            self.load_and_play_music(intro_overture)
        else:
            self.load_and_play_music(self.current_map.music_file_path)
        self.events = get()

        display.set_icon(image.load(ICON_PATH))
        self.player.restore_hp()
        self.allow_save_prompt = False
        # pg.event.set_allowed([pg.QUIT])

    def main(self) -> None:
        """
        Main loop.
        :return: None
        """
        if self.splash_screen_enabled:
            intro = Intro()
            intro.show_start_screen(self.screen, self.start_time, self.clock)
            self.load_and_play_music(village_music)
            self.show_main_menu_screen(self.screen)
        self.draw_all()
        while True:
            self.clock.tick(self.fps)
            self.get_events()
            self.draw_all()
            display.flip()
            self.loop_count += 1

    ####################################################################################################################
    # game methods ^^^^^^^^
    ####################################################################################################################

    def show_main_menu_screen(self, screen) -> None:
        select_from_vertical_menu(get_ticks(), screen, BEGIN_QUEST_PATH, BEGIN_QUEST_SELECTED_PATH, [])
        # adventure_log_blinking = True
        # while adventure_log_blinking:
        self.player.adventure_log = select_from_vertical_menu(get_ticks(), screen, ADVENTURE_LOG_PATH,
                                                              ADVENTURE_LOG_1_PATH,
                                                              [ADVENTURE_LOG_2_PATH, ADVENTURE_LOG_3_PATH]) + 1
        self.player.name = menu_functions.select_name(get_ticks(), screen, self.cmd_menu)
        self.player.set_initial_stats()
        play_sound(menu_button_sfx)
        fade(fade_out=True, screen=self.screen)
        self.load_and_play_music(self.current_map.music_file_path)
        self.cmd_menu = CommandMenu(self)

    def get_events(self) -> None:
        """
        Handle all events in main loop.
        :return: None
        """
        self.events = get()
        for current_event in self.events:
            if current_event.type == QUIT:
                quit()
                sys.exit()
        event.pump()
        current_key = key.get_pressed()
        self.set_text_color()
        self.handle_battles()
        if not self.player.is_moving:
            set_character_position(self.player)
        if self.game_state.enable_movement and not self.paused and not self.cmd_menu.menu.is_enabled():
            self.move_player(current_key)
        if self.enable_roaming and self.current_map.roaming_characters:
            self.move_roaming_characters()
            self.update_roaming_character_positions()

        # currently can't process staircases right next to one another, need to fix
        # a quick fix would be to add an exception in the conditional for
        # the map where staircases right next to each other need to be enabled,
        # as done with Cantlin and others below
        self.handle_warps()

        self.handle_keypresses(current_key)

        self.player.current_tile = get_tile_id_by_coordinates(self.player.rect.x // TILE_SIZE,
                                                              self.player.rect.y // TILE_SIZE, self.current_map)
        self.cmd_menu.current_tile = self.player.current_tile

        self.player.next_tile_id = get_next_tile_identifier(self.player.column, self.player.row,
                                                            self.player.direction_value, self.current_map)

        self.player.next_coordinates = get_next_coordinates(self.player.rect.x // TILE_SIZE,
                                                            self.player.rect.y // TILE_SIZE,
                                                            self.player.direction_value)
        self.player.next_next_coordinates = get_next_coordinates(self.player.rect.x // TILE_SIZE,
                                                                 self.player.rect.y // TILE_SIZE,
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
        if SHOW_FPS:
            print(self.clock.get_fps())

        # This prints out the next_tile, and the next_next_tile.
        # print(f'Next tile: {self.player.next_tile}')
        # print(f'Next next tile: {self.player.next_next_tile}')
        # print(f'{self.get_character_identifier_by_coordinates(self.player.next_coordinates)}')
        # print(f'{self.get_character_identifier_by_coordinates(self.player.next_next_coordinates)}')

        event.pump()

    def set_text_color(self):
        if self.player.current_hp <= self.player.max_hp * 0.125:
            self.cmd_menu.game.color, self.color = RED, RED
        else:
            self.cmd_menu.game.color, self.color = WHITE, WHITE

    def handle_battles(self):
        if self.tiles_moved_since_spawn > 0:
            # TODO: Add other maps with enemies besides Alefgard.
            if self.current_map.identifier == 'Alefgard':
                if self.tiles_moved_since_spawn != self.last_amount_of_tiles_moved:
                    current_zone = self.player.column // 18, self.player.row // 18
                    enemies_in_current_zone = enemy_territory_map.get(current_zone)
                    # "Zone 0" in the original code is zone (3, 2)
                    if current_zone == (3, 2):
                        random_integer = self.handle_near_tantegel_fight_modifier()
                    else:
                        random_integer = self.get_random_integer_by_tile()
                    self.launch_battle = random_integer == 0 or FORCE_BATTLE
                    if self.launch_battle and not NO_BATTLES:
                        enemy_name = random.choice(enemies_in_current_zone)
                        if self.music_enabled:
                            mixer.music.load(battle_music)
                            mixer.music.play(-1)
                        battle_background_image = scale(image.load(BATTLE_BACKGROUND_PATH),
                                                        (7 * TILE_SIZE, 7 * TILE_SIZE))
                        self.screen.blit(battle_background_image, (5 * TILE_SIZE, 4 * TILE_SIZE))
                        display.update(battle_background_image.get_rect())
                        self.drawer.show_enemy_image(self.screen, enemy_name)
                        enemy_draws_near_string = f'{enemy_name} draws near!\n' \
                                                  f'Command?\n'
                        vowels = 'AEIOU'

                        if enemy_name[0] in vowels:
                            enemy_draws_near_string = f'An {enemy_draws_near_string}'
                        else:
                            if enemy_name == 'Dragonlord 2':
                                enemy_draws_near_string = 'The Dragonlord revealed his true self!\n'
                            # show battle window (enemy sprite over background)
                            else:
                                enemy_draws_near_string = f'A {enemy_draws_near_string}'
                        self.cmd_menu.show_line_in_dialog_box(enemy_draws_near_string, add_quotes=False, skip_text=True,
                                                              last_line=True, disable_sound=True)
                        self.cmd_menu.window_drop_down_effect(1, 2, 4, 6)
                        self.cmd_menu.window_drop_down_effect(6, 1, 8, 3)
                        create_window(6, 1, 8, 3, BATTLE_MENU_FIGHT_PATH, self.screen, self.color)
                        self.hovering_stats_displayed = True
                        self.drawer.draw_hovering_stats_window(self.screen, self.player, self.color)

                        enemy = enemy_string_lookup[enemy_name]()

                        battle_menu_options = {'Fight': BATTLE_MENU_FIGHT_PATH, 'Spell': BATTLE_MENU_SPELL_PATH}, \
                            {'Run': BATTLE_MENU_RUN_PATH, 'Item': BATTLE_MENU_ITEM_PATH}
                        current_item_row = 0
                        current_item_column = 0
                        run_away = False
                        blink_start = get_ticks()
                        while enemy.hp > 0 and not run_away and not self.player.is_dead:
                            blink_switch(self.screen, BATTLE_MENU_STATIC_PATH,
                                         list(battle_menu_options[current_item_row].values())[
                                             current_item_column], x=6, y=1, width=8, height=3,
                                         start=blink_start, color=self.color)
                            current_selection = list(battle_menu_options[current_item_row].keys())[current_item_column]
                            selected_executed_option = None
                            for current_event in event.get():
                                if current_event.type == QUIT:
                                    quit()
                                    sys.exit()
                                elif current_event.type == KEYDOWN and not self.player.is_dead and not enemy.hp <= 0:
                                    if current_event.key in (K_RETURN, K_i, K_k):
                                        play_sound(menu_button_sfx)
                                        selected_executed_option = current_selection
                                    elif current_event.key == K_j:
                                        # back up cursor instead of deleting letters
                                        break
                                    elif current_event.key in (K_DOWN, K_s, K_UP, K_w):
                                        if current_item_row == 0:
                                            current_item_row = 1
                                        elif current_item_row == 1:
                                            current_item_row = 0
                                    elif current_event.key in (K_LEFT, K_a, K_RIGHT, K_d):
                                        if current_item_column == 0:
                                            current_item_column = 1
                                        elif current_item_column == 1:
                                            current_item_column = 0
                                    if convert_to_frames_since_start_time(blink_start) > 32:
                                        blink_start = get_ticks()
                                    if selected_executed_option:
                                        if selected_executed_option == 'Fight':
                                            self.fight(enemy)
                                        elif selected_executed_option == 'Spell':
                                            self.battle_spell()
                                        elif selected_executed_option == 'Run':
                                            self.battle_run()
                                            run_away = True
                                            if self.music_enabled:
                                                mixer.music.load(self.current_map.music_file_path)
                                                mixer.music.play(-1)
                                        elif selected_executed_option == 'Item':
                                            if not self.player.inventory:
                                                self.cmd_menu.show_line_in_dialog_box(
                                                    'Nothing of use has yet been given to thee.\n'
                                                    'Command?\n', add_quotes=False, last_line=True, disable_sound=True)
                                        selected_executed_option = None

                        if enemy.hp <= 0:
                            self.enemy_defeated(enemy)
                        if self.music_enabled and not mixer.music.get_busy():
                            mixer.music.load(self.current_map.music_file_path)
                            mixer.music.play(-1)

                    # if self.last_zone != current_zone:
                    #     print(f'Zone: {current_zone}\nEnemies: {enemies_in_current_zone}')
                    self.last_zone = current_zone
                self.last_amount_of_tiles_moved = self.tiles_moved_since_spawn

    def battle_run(self):
        play_sound(stairs_down_sfx)
        self.cmd_menu.show_line_in_dialog_box(f"{self.player.name} started to run away.\n", add_quotes=False,
                                              last_line=True, disable_sound=True)

    def fight(self, enemy):
        play_sound(attack_sfx)
        self.cmd_menu.show_line_in_dialog_box(f"{self.player.name} attacks!\n", add_quotes=False, disable_sound=True)

        attack_damage = self.calculate_attack_damage(enemy)

        if attack_damage <= 0:
            self.missed_attack()
        else:
            play_sound(hit_sfx)
            self.cmd_menu.show_line_in_dialog_box(
                f"The {enemy.name}'s Hit Points have been reduced by {attack_damage}.\n", add_quotes=False,
                disable_sound=True)
            enemy.hp -= attack_damage
            # print(f"{enemy.name} HP: {enemy.hp}/{enemy_string_lookup[enemy.name]().hp}")
        if enemy.hp <= 0:
            return
        else:
            play_sound(prepare_attack_sfx)
            self.cmd_menu.show_line_in_dialog_box(f"The {enemy.name} attacks!\n", add_quotes=False, disable_sound=True)
            # (EnemyAttack - HeroAgility / 2) / 4,
            #
            # to:
            #
            # (EnemyAttack - HeroAgility / 2) / 2

            attack_damage = self.calculate_enemy_attack_damage(enemy)

            if attack_damage <= 0:
                self.missed_attack()
            else:
                self.receive_damage(attack_damage)
            if self.player.current_hp == 0:
                self.drawer.draw_hovering_stats_window(self.screen, self.player, RED)
                self.player.is_dead = True
            else:
                self.cmd_menu.show_line_in_dialog_box(f"Command?\n", add_quotes=False, disable_sound=True)

    def receive_damage(self, attack_damage):
        play_sound(receive_damage_2_sfx)
        self.player.current_hp -= attack_damage
        self.color = RED if self.player.current_hp <= self.player.max_hp * 0.125 else WHITE
        if self.player.current_hp < 0:
            self.player.current_hp = 0
        self.drawer.draw_hovering_stats_window(self.screen, self.player, self.color)
        create_window(6, 1, 8, 3, BATTLE_MENU_FIGHT_PATH, self.screen, self.color)
        self.cmd_menu.show_line_in_dialog_box(f"Thy Hit Points decreased by {attack_damage}.\n",
                                              add_quotes=False, disable_sound=True)
        # print(f"{self.player.name} HP: {self.player.current_hp}/{self.player.max_hp}")

    def calculate_enemy_attack_damage(self, enemy):
        return random.randint((enemy.attack - self.player.agility / 2) // 4,
                              (enemy.attack - self.player.agility / 2) // 2)

    def missed_attack(self):
        missed_sfx_number = random.randint(1, 2)
        if missed_sfx_number == 1:
            play_sound(missed_sfx)
        else:
            play_sound(missed_2_sfx)
        self.cmd_menu.show_line_in_dialog_box("A miss! No damage hath been scored!\n", add_quotes=False,
                                              disable_sound=True)

    def calculate_attack_damage(self, enemy):
        excellent_move_probability = random.randint(0, 31)
        if excellent_move_probability == 0 and enemy.name not in ('Dragonlord', 'Dragonlord 2'):
            play_sound(excellent_move_sfx)
            self.cmd_menu.show_line_in_dialog_box("Excellent move!\n", add_quotes=False, disable_sound=True)
            attack_damage = random.randint(self.player.attack_power // 2,
                                           self.player.attack_power)
        else:
            # (HeroAttack - EnemyAgility / 2) / 4,
            #
            # to:
            #
            # (HeroAttack - EnemyAgility / 2) / 2
            lower_bound = round((self.player.attack_power - (enemy.defense / 2)) / 2)
            upper_bound = round((self.player.attack_power - (enemy.defense / 2)) * 2)
            print(f'lower_bound: {lower_bound}\n'
                  f'upper_bound: {upper_bound}\n'
                  f'player.attack_power: {self.player.attack_power}\n'
                  f'enemy.speed: {enemy.defense}')
            if lower_bound >= upper_bound:
                attack_damage = upper_bound
            else:
                attack_damage = random.randint(lower_bound, upper_bound)
            if attack_damage < 1:
                # fifty-fifty chance of doing 1 damage
                if random.random() < .5:
                    attack_damage = 1
                else:
                    attack_damage = 0
        return round(attack_damage)

    def battle_spell(self):
        self.cmd_menu.show_line_in_dialog_box(f"{self.player.name} cannot yet use the spell.\n"
                                              f"Command?\n", add_quotes=False, last_line=True, disable_sound=True)

    def enemy_defeated(self, enemy):
        mixer.music.stop()
        play_sound(victory_sfx)
        self.cmd_menu.show_line_in_dialog_box(f"Thou hast done well in defeating the {enemy.name}.\n", add_quotes=False,
                                              disable_sound=True)
        battle_background_image = scale(image.load(BATTLE_BACKGROUND_PATH),
                                        (7 * TILE_SIZE, 7 * TILE_SIZE))
        self.screen.blit(battle_background_image, (5 * TILE_SIZE, 4 * TILE_SIZE))
        display.update(battle_background_image.get_rect())
        self.cmd_menu.show_line_in_dialog_box(f"Thy experience increases by {enemy.xp}.\n"
                                              f"Thy GOLD increases by {enemy.gold}.\n", add_quotes=False,
                                              disable_sound=True)
        self.player.total_experience += enemy.xp
        self.player.gold += enemy.gold
        if self.player.total_experience >= levels_list[self.player.level + 1]['total_exp']:
            play_sound(improvement_sfx)
            self.cmd_menu.show_line_in_dialog_box(f"Courage and wit have served thee well.\n"
                                                  f"Thou hast been promoted to the next level.\n", add_quotes=False,
                                                  disable_sound=True)
            old_power = self.player.strength
            old_agility = self.player.agility
            old_max_hp = self.player.max_hp
            old_max_mp = self.player.max_mp
            old_spells = self.player.spells

            self.player.level += 1
            self.player.set_stats_by_level(self.player.level)
            self.player.update_attack_power()
            self.player.update_defense_power()
            self.player.points_to_next_level = self.player.get_points_to_next_level()
            if self.music_enabled:
                mixer.music.load(self.current_map.music_file_path)
                mixer.music.play(-1)

            if self.player.strength > old_power:
                self.cmd_menu.show_line_in_dialog_box(f"Thy power increases by {self.player.strength - old_power}.\n",
                                                      add_quotes=False, disable_sound=True)
            if self.player.agility > old_agility:
                self.cmd_menu.show_line_in_dialog_box(
                    f"Thy Response Speed increases by {self.player.agility - old_agility}.\n", add_quotes=False,
                    disable_sound=True)
            if self.player.max_hp > old_max_hp:
                self.cmd_menu.show_line_in_dialog_box(
                    f"Thy Maximum Hit Points increase by {self.player.max_hp - old_max_hp}.\n", add_quotes=False,
                    disable_sound=True)
            if self.player.max_mp > old_max_mp:
                self.cmd_menu.show_line_in_dialog_box(
                    f"Thy Maximum Magic Points increase by {self.player.max_mp - old_max_mp}.\n", add_quotes=False,
                    disable_sound=True)
            if len(self.player.spells) > len(old_spells):
                self.cmd_menu.show_line_in_dialog_box("Thou hast learned a new spell.\n", add_quotes=False,
                                                      disable_sound=True)

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
                self.player.images = self.current_map.scale_sprite_sheet(ARMED_HERO_WITH_SHIELD_PATH)
                self.player.set_images(self.player.images)

            else:
                self.player.images = self.current_map.scale_sprite_sheet(ARMED_HERO_PATH)
                self.player.set_images(self.player.images)
        elif self.player.shield:
            self.player.images = self.current_map.scale_sprite_sheet(UNARMED_HERO_WITH_SHIELD_PATH)
            self.player.set_images(self.player.images)

    def handle_death(self):
        if self.player.current_hp <= 0:
            self.player.current_hp = 0
            self.player.is_dead = True
            self.color = RED
            if self.launch_battle and not NO_BATTLES:
                create_window(6, 1, 8, 3, BATTLE_MENU_FIGHT_PATH, self.screen, RED)
                self.launch_battle = False
                display.flip()
            else:
                self.drawer.draw_all_tiles_in_current_map(self.current_map, self.background)
                display.flip()
            if self.music_enabled:
                mixer.music.stop()
                mixer.music.load(death_sfx)
                mixer.music.play(1)
            self.game_state.enable_movement = False
            death_start_time = get_ticks()
            while convert_to_frames_since_start_time(death_start_time) < 318:
                time.wait(1)
            event.clear()

            self.cmd_menu.show_text_in_dialog_box(self.cmd_menu.dialog_lookup.thou_art_dead, disable_sound=True)
            self.set_post_death_attributes()
        else:
            self.player.is_dead = False

    def set_post_death_attributes(self):
        next_map = map_lookup['TantegelThroneRoom']()
        self.change_map(next_map)
        self.player.gold = self.player.gold // 2
        # revive player
        self.player.current_hp = self.player.max_hp
        self.player.is_dead = False
        self.game_state.is_post_death_dialog = True

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
        play_sound(swamp_sfx)
        self.player.received_environment_damage = True
        flash_transparent_color(RED, self.screen)
        self.draw_all()
        display.flip()

    def handle_warps(self):
        immediate_move_maps = ('Brecconary', 'Cantlin', 'Hauksness', 'Rimuldar', 'CharlockB1')
        # a quick fix to prevent buggy warping - set to > 2
        if self.tiles_moved_since_spawn > 2 or (
                self.tiles_moved_since_spawn > 1 and self.current_map.identifier in immediate_move_maps):
            for staircase_location, staircase_dict in self.current_map.staircases.items():
                self.process_staircase_warps(staircase_location, staircase_dict)

    def handle_keypresses(self, current_key):
        self.handle_b_button(current_key)
        self.handle_a_button(current_key)
        self.handle_start_button(current_key)
        self.handle_select_button(current_key)
        # TODO: Allow for zoom in and out if Ctrl + PLUS | MINUS is pressed (or scroll wheel is moved). (modernization)
        # if key[pg.K_LCTRL] and (key[pg.K_PLUS] or key[pg.K_KP_PLUS]):
        #     self.scale = self.scale + 1
        self.handle_help_button(current_key)
        self.handle_fps_changes(current_key)

    def handle_help_button(self, current_key):
        if current_key[K_F1]:
            self.cmd_menu.show_text_in_dialog_box(f"Controls:\n{convert_list_to_newline_separated_string(controls)}")

    def handle_b_button(self, current_key):
        if current_key[K_j]:
            # B button
            self.unlaunch_menu(self.cmd_menu)
            # print("J key pressed (B button).")

    def handle_a_button(self, current_key):
        if current_key[K_k]:
            # A button
            # print("K key pressed (A button).")
            if not self.player.is_moving:
                # pause_all_movement may be temporarily commented out for dialog box debugging purposes.
                self.drawer.display_hovering_stats = True
                self.cmd_menu.launch_signaled = True
                self.game_state.pause_all_movement()

    def handle_start_button(self, current_key):
        if current_key[K_i]:
            # Start button
            if self.paused:
                self.game_state.unpause_all_movement()
                self.paused = False
            else:
                self.game_state.pause_all_movement()
                self.paused = True
            print("I key pressed (Start button).")

    @staticmethod
    def handle_select_button(current_key):
        if current_key[K_u]:
            # Select button
            pass

    def handle_fps_changes(self, current_key) -> None:
        if current_key[K_1]:
            self.draw_temporary_text(self.cmd_menu.dialog_lookup.normal_speed_string)
            self.fps = 60
        if current_key[K_2]:
            self.draw_temporary_text(self.cmd_menu.dialog_lookup.double_speed_string)
            self.fps = 120
        if current_key[K_3]:
            self.draw_temporary_text(self.cmd_menu.dialog_lookup.triple_speed_string)
            self.fps = 240
        if current_key[K_4]:
            self.draw_temporary_text(self.cmd_menu.dialog_lookup.quadruple_speed_string)
            self.fps = 480

    def update_roaming_character_positions(self) -> None:
        for character, character_dict in self.current_map.characters.items():
            if character_dict['character'].__class__.__name__ == 'RoamingCharacter':
                if not character_dict['character'].is_moving:
                    set_character_position(character_dict['character'])

    def draw_temporary_text(self, text: Tuple[str] | List[str] | str, add_quotes=False) -> None:
        self.cmd_menu.show_text_in_dialog_box(text, add_quotes=add_quotes, temp_text_start=get_ticks(), skip_text=False)

    def process_staircase_warps(self, staircase_location: tuple, staircase_dict: dict) -> None:
        if (self.player.row, self.player.column) == staircase_location:
            self.player.bumped = False
            match staircase_dict['stair_direction']:
                case 'down':
                    play_sound(stairs_down_sfx)
                case 'up':
                    play_sound(stairs_up_sfx)
            next_map = map_lookup[staircase_dict['map']]()
            self.change_map(next_map)

    def change_map(self, next_map: maps.DragonWarriorMap) -> None:
        """
        Change to a different map.
        :param next_map: The next map to be loaded.
        :return: None
        """
        self.game_state.pause_all_movement()
        self.last_map = self.current_map
        self.current_map = next_map
        if not self.allow_save_prompt:
            if self.last_map.identifier == 'TantegelThroneRoom':
                self.allow_save_prompt = True
        self.current_map.layout = self.layouts.map_layout_lookup[self.current_map.__class__.__name__]
        fade(fade_out=True, screen=self.screen)
        self.set_big_map()
        self.set_roaming_character_positions()
        if self.music_enabled:
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
        self.current_map.load_map(self.player, destination_coordinates)
        if not self.current_map.is_dark:
            self.torch_active = False
            self.radiant_active = False
        self.handle_player_direction_on_map_change(current_map_staircase_dict)
        #  this is probably what we need here:

        #    self.camera = Camera((self.player.rect.x // TILE_SIZE, self.player.rect.y // TILE_SIZE),
        #                              current_map=self.current_map, screen=self.screen)
        self.camera = Camera(hero_position=(int(self.player.column), int(self.player.row)),
                             current_map=self.current_map, screen=self.screen)
        # self.fade(self.current_map.width, self.current_map.height, fade_out=False)
        self.loop_count = 1
        self.game_state.unpause_all_movement()
        self.tiles_moved_since_spawn = 0
        self.cmd_menu = CommandMenu(self)
        self.load_and_play_music(self.current_map.music_file_path)
        if destination_coordinates:
            # really not sure if the 1 and 0 here are supposed to be switched
            self.camera.set_camera_position((destination_coordinates[1], destination_coordinates[0]))

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
        self.background = self.big_map.subsurface(0, 0, self.current_map.width, self.current_map.height).convert_alpha()

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
            set_character_position(roaming_character)

    def load_and_play_music(self, music_path):
        """Loads and plays music on repeat."""
        if self.music_enabled:
            mixer.music.load(music_path)
            mixer.music.play(-1)

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
        self.drawer.draw_all_tiles_in_current_map(self.current_map, self.background)

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
                if curr_pos_y % TILE_SIZE == 0:
                    if not self.player.bumped:
                        # TODO(ELF): sometimes self.tiles_moved_since_spawn gets set to 1 when spawning -
                        #  should always be 0 when the map starts.
                        self.tiles_moved_since_spawn += 1
                        self.tiles_moved_total += 1
                    else:
                        self.player.bumped = False
                    self.player.is_moving, self.player.next_tile_checked = False, False
                    return
            elif is_facing_laterally(self.player):
                if curr_pos_x % TILE_SIZE == 0:
                    if not self.player.bumped:
                        self.tiles_moved_since_spawn += 1
                        self.tiles_moved_total += 1
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
        character.next_tile_id = get_next_tile_identifier(character.column, character.row, character.direction_value,
                                                          self.current_map)
        character.next_next_tile_id = get_next_tile_identifier(character.column, character.row,
                                                               character.direction_value, self.current_map, offset=2)
        if self.is_impassable(character.next_tile_id):
            bump_and_reset(character, character.next_tile_id, character.next_next_tile_id)
        elif self.character_in_path(character):
            bump_and_reset(character, character.next_tile_id, character.next_next_tile_id)
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
            character.next_tile_id = get_next_tile_identifier(character.column, character.row,
                                                              character.direction_value, self.current_map)
        character.next_next_tile_id = get_next_tile_identifier(character.column, character.row,
                                                               character.direction_value, self.current_map, offset=2)

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
        max_x_bound, max_y_bound, min_bound = self.current_map.width - TILE_SIZE, self.current_map.height - TILE_SIZE, 0
        if self.player.rect.x < min_bound:
            self.player.rect.x = min_bound
            bump(self.player)
            next_pos_x += -self.speed
        elif self.player.rect.x > max_x_bound:
            self.player.rect.x = max_x_bound
            bump(self.player)
            next_pos_x += self.speed
        elif self.player.rect.y < min_bound:
            self.player.rect.y = min_bound
            bump(self.player)
            next_pos_y -= self.speed
        elif self.player.rect.y > max_y_bound:
            self.player.rect.y = max_y_bound
            bump(self.player)
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
                    if curr_pos_y % TILE_SIZE == 0:
                        roaming_character.is_moving, roaming_character.next_tile_checked = False, False
                        return
                elif is_facing_laterally(roaming_character):
                    if curr_pos_x % TILE_SIZE == 0:
                        roaming_character.is_moving, roaming_character.next_tile_checked = False, False
                        return
            if is_facing_medially(roaming_character):
                self.move_medially(roaming_character)
            elif is_facing_laterally(roaming_character):
                self.move_laterally(roaming_character)
            # handle_roaming_character_sides_collision(self.current_map, roaming_character)

    ####################################################################################################################
    # draw methods vvvvvvvvvv
    ####################################################################################################################
    def draw_all(self) -> None:
        """
        Draw map, sprites, background, menu and other surfaces.
        :return: None
        """
        self.screen.fill(BLACK)
        width_offset = 0
        height_offset = 0
        if self.loop_count == 1:
            self.background = self.big_map.subsurface(0, 0, self.current_map.width - width_offset,
                                                      self.current_map.height - height_offset).convert()
            # draw everything once on the first go-around
            self.drawer.draw_all_tiles_in_current_map(self.current_map, self.background)
        try:
            surrounding_tile_values = get_surrounding_tile_values(
                (self.player.rect.y // TILE_SIZE, self.player.rect.x // TILE_SIZE), self.current_map.layout)
            player_surrounding_tiles = convert_numeric_tile_list_to_unique_tile_values(self.current_map,
                                                                                       surrounding_tile_values)
            all_roaming_character_surrounding_tiles = get_all_roaming_character_surrounding_tiles(self.current_map)
            all_fixed_character_underlying_tiles = get_fixed_character_underlying_tiles(self.current_map)
            tile_types_to_draw = replace_characters_with_underlying_tiles([self.player.current_tile] +
                                                                          all_roaming_character_surrounding_tiles +
                                                                          all_fixed_character_underlying_tiles,
                                                                          self.current_map.character_key)
            if self.player.is_moving:
                tile_types_to_draw += replace_characters_with_underlying_tiles(
                    list(filter(None, player_surrounding_tiles)), self.current_map.character_key)
                self.not_moving_time_start = None
                self.drawer.display_hovering_stats = False
                if self.hovering_stats_displayed:
                    self.cmd_menu.window_drop_up_effect(1, 2, 4, 6)
                    self.hovering_stats_displayed = False
            else:
                if not self.not_moving_time_start:
                    self.not_moving_time_start = get_ticks()
                else:
                    if convert_to_frames_since_start_time(self.not_moving_time_start) >= 51:
                        self.drawer.display_hovering_stats = True
        except IndexError:
            all_roaming_character_surrounding_tiles = get_all_roaming_character_surrounding_tiles(self.current_map)
            all_fixed_character_underlying_tiles = get_fixed_character_underlying_tiles(self.current_map)
            tile_types_to_draw = replace_characters_with_underlying_tiles([self.player.current_tile] +
                                                                          all_roaming_character_surrounding_tiles +
                                                                          all_fixed_character_underlying_tiles,
                                                                          self.current_map.character_key)

            # tile_types_to_draw = list(filter(lambda x: not self.is_impassable(x), tile_types_to_draw))

        group_to_draw = Group()
        camera_screen_rect = Rect(self.player.rect.x - TILE_SIZE * 8, self.player.rect.y - TILE_SIZE * 7,
                                  self.screen.get_width(), self.screen.get_height())
        double_camera_screen_rect = camera_screen_rect.inflate(camera_screen_rect.width * 0.25,
                                                               camera_screen_rect.height * 0.25)
        fixed_character_rects = [fixed_character.rect for fixed_character in self.current_map.fixed_characters]
        roaming_character_rects = [
            roaming_character.rect if roaming_character.is_moving else get_surrounding_rect(roaming_character) for
            roaming_character in
            self.current_map.roaming_characters]
        # tiles_drawn = []
        for tile, tile_dict in self.current_map.floor_tile_key.items():
            if tile_dict.get('group') and tile in set(tile_types_to_draw):
                for tile_to_draw in tile_dict['group']:
                    if camera_screen_rect.colliderect(tile_to_draw.rect):
                        if self.player.is_moving:
                            if get_surrounding_rect(self.player).colliderect(tile_to_draw.rect):
                                group_to_draw.add(tile_to_draw)
                                # tiles_drawn.append(tile)
                        else:
                            if self.player.rect.colliderect(tile_to_draw.rect):
                                group_to_draw.add(tile_to_draw)
                                # tiles_drawn.append(tile)
                        for fixed_character_rect in fixed_character_rects:
                            if fixed_character_rect.colliderect(tile_to_draw):
                                group_to_draw.add(tile_to_draw)
                                # tiles_drawn.append(tile)

                    if double_camera_screen_rect.colliderect(tile_to_draw.rect):
                        for roaming_character_rect in roaming_character_rects:
                            if roaming_character_rect.colliderect(tile_to_draw):
                                group_to_draw.add(tile_to_draw)
                                # tiles_drawn.append(tile)
        # print(f"{len(tiles_drawn)}: {tiles_drawn}")
        group_to_draw.draw(self.background)
        # to make this work in all maps: draw tile under hero, AND tiles under NPCs
        # in addition to the trajectory of the NPCs
        self.drawer.handle_sprite_drawing_and_animation(self.current_map, self.foreground_rects, self.background,
                                                        self.enable_animate)
        self.screen.blit(self.background, self.camera.get_pos())
        if self.current_map.identifier == 'TantegelThroneRoom':
            self.handle_initial_dialog()
            handle_post_death_dialog(self.game_state, self.drawer, self.cmd_menu, self.events, self.skip_text)
        if self.current_map.is_dark and ENABLE_DARKNESS:
            darkness = Surface((self.screen.get_width(), self.screen.get_height()))  # lgtm [py/call/wrong-arguments]
            if self.torch_active:
                # Light with radius of 1
                darkness_hole = darkness.subsurface((self.screen.get_width() / 2) - TILE_SIZE,
                                                    (self.screen.get_height() / 2) - (TILE_SIZE * 1.5),
                                                    TILE_SIZE * 3,
                                                    TILE_SIZE * 3)
            elif self.radiant_active:
                # Light with radius of 2, expanding to 3...

                # darkness_hole = darkness.subsurface((self.screen.get_width() / 2) - TILE_SIZE * 2, (self.screen.get_height() / 2) - (TILE_SIZE * 2.5),
                #                                     TILE_SIZE * 5,
                #                                     TILE_SIZE * 5)
                # darkness.fill(BLACK)
                # darkness_hole.fill(WHITE)
                # darkness.set_colorkey(WHITE)
                # self.screen.blit(darkness, (0, 0))
                # Light with radius of 3
                darkness_hole = darkness.subsurface((self.screen.get_width() / 2) - TILE_SIZE * 3,
                                                    (self.screen.get_height() / 2) - (TILE_SIZE * 5),
                                                    TILE_SIZE * 7,
                                                    TILE_SIZE * 8.5)

                if self.radiant_start is None:
                    self.radiant_start = self.tiles_moved_total
                    play_sound(torch_sfx)
                    play_sound(torch_sfx)
                else:
                    if self.tiles_moved_total - self.radiant_start >= 200:
                        self.radiant_active = False
                        self.radiant_start = None
                    elif self.tiles_moved_total - self.radiant_start >= 140:
                        # Light with radius of 1
                        darkness_hole = darkness.subsurface((self.screen.get_width() / 2) - TILE_SIZE,
                                                            (self.screen.get_height() / 2) - (TILE_SIZE * 1.5),
                                                            TILE_SIZE * 3,
                                                            TILE_SIZE * 3)
                    elif self.tiles_moved_total - self.radiant_start >= 80:
                        # Light with radius of 2
                        darkness_hole = darkness.subsurface((self.screen.get_width() / 2) - TILE_SIZE * 2,
                                                            (self.screen.get_height() / 2) - (TILE_SIZE * 2.5),
                                                            TILE_SIZE * 5,
                                                            TILE_SIZE * 5)

            else:
                darkness_hole = darkness.subsurface((self.screen.get_width() / 2),
                                                    (self.screen.get_height() / 2) - (TILE_SIZE / 2), TILE_SIZE,
                                                    TILE_SIZE)
            darkness.fill(BLACK)
            darkness_hole.fill(WHITE)
            darkness.set_colorkey(WHITE)
            self.screen.blit(darkness, (0, 0))
        if self.drawer.display_hovering_stats:
            if not self.hovering_stats_displayed:
                self.cmd_menu.window_drop_down_effect(1, 2, 4, 6)
                self.hovering_stats_displayed = True
            self.drawer.draw_hovering_stats_window(self.screen, self.player, self.color)
        handle_menu_launch(self.screen, self.cmd_menu, self.cmd_menu)
        if self.cmd_menu.menu.is_enabled():
            self.cmd_menu.menu.update(self.events)
        else:
            if not self.game_state.is_initial_dialog:
                self.game_state.enable_movement = True

    def handle_initial_dialog(self):
        if self.initial_dialog_enabled:
            if self.game_state.is_initial_dialog:
                display.flip()
                self.drawer.display_hovering_stats = False
                self.cmd_menu.launch_signaled = False
                self.drawer.run_automatic_initial_dialog(self.events, self.skip_text, self.cmd_menu)
                event.clear()
            else:
                if self.allow_save_prompt:
                    set_to_save_prompt(self.cmd_menu)
                else:
                    self.drawer.set_to_post_initial_dialog(self.cmd_menu)

        else:
            self.drawer.set_to_post_initial_dialog(self.cmd_menu)
            if not self.cmd_menu.menu.is_enabled():
                self.game_state.enable_movement = True


def run():
    game = Game()
    game.main()


if __name__ == "__main__":
    run()
