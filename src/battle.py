import random

from pygame import image, display, time, mixer, Surface
from pygame.transform import scale

from src.common import BLACK, set_gettext_language
from src.directories import Directories
from src.enemy import enemy_groups, Enemy
from src.enemy_lookup import enemy_string_lookup
from src.maps import DragonWarriorMap
from src.menu import CommandMenu
from src.player.player import Player
from src.player.player_stats import levels_list
from src.sound import Sound

ko_consonant_ending_chars = ('임', '갈', '롤', '령', '믈', '맨', '렘', '곤', '왕')


# ko_vowel_ending_chars = ('스', '키', '마', '트', '사', '다', '드', '지', '라')


class Battle:
    def __init__(self, config, enemy_name: str, current_map: DragonWarriorMap):
        self.config = config
        self.directories = Directories(config)
        self.sound = Sound(config)
        self._ = _ = set_gettext_language(config['LANGUAGE'])
        self.turn = 0
        self.last_turn = 0
        self.enemy = enemy_string_lookup[enemy_name]()
        self.tile_size = config['TILE_SIZE']
        self.current_map = current_map

    def play_battle_music(self):
        if self.config["MUSIC_ENABLED"]:
            mixer.music.load(self.directories.battle_music)
            mixer.music.play(-1)

    def transition_battle_background_image_effect(self, screen):
        """Spiral effect to introduce battle background."""
        if not self.current_map.is_dark:
            battle_background_image = scale(image.load(self.directories.BATTLE_BACKGROUND_PATH),
                                            (7 * self.tile_size, 7 * self.tile_size))
        else:
            black_surface = Surface((7 * self.tile_size, 7 * self.tile_size))
            black_surface.fill(BLACK)
            battle_background_image = black_surface
        spiral_tile_coordinates = ((3, 3), (3, 4), (2, 4), (2, 3), (2, 2), (3, 2), (4, 2), (4, 3), (4, 4), (4, 5),
                                   (3, 5), (2, 5), (1, 5), (1, 4), (1, 3), (1, 2), (1, 1), (2, 1), (3, 1), (4, 1),
                                   (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6),
                                   (0, 6), (0, 5), (0, 4), (0, 3), (0, 2), (0, 1), (0, 0), (1, 0), (2, 0), (3, 0),
                                   (4, 0), (5, 0), (6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (6, 5), (6, 6))
        for tile in spiral_tile_coordinates:
            screen.blit(battle_background_image.subsurface(
                (tile[0] * self.tile_size, tile[1] * self.tile_size, self.tile_size, self.tile_size)),
                ((tile[0] + 5) * self.tile_size, (tile[1] + 4) * self.tile_size))
            display.update()
            time.wait(20)

    def battle_run(self, cmd_menu: CommandMenu, player: Player, current_battle):
        """Attempt to run from a battle. The formula is as follows:
        If HeroAgility * Random # < EnemyAgility * Random # * GroupFactor, then the
    enemy will block you. (according to https://gamefaqs.gamespot.com/nes/563408-dragon-warrior/faqs/61640)"""
        self.sound.play_sound(self.directories.stairs_down_sfx)
        cmd_menu.show_line_in_dialog_box(self._("{} started to run away.\n").format(player.name), add_quotes=False,
                                         hide_arrow=True, disable_sound=True)
        random_number = random.randint(0, 255)
        group_factor = 1
        group_factor_lookup = {
            1: 0.25,
            2: 0.375,
            3: 0.5,
            4: 1.0,
        }
        for group_number, group in enemy_groups.items():
            if current_battle.enemy.name in group:
                group_factor = group_number
        if current_battle.enemy.is_asleep:
            return True
        else:
            if player.agility * random_number < current_battle.enemy.speed * random_number * group_factor_lookup[group_factor]:
                cmd_menu.show_line_in_dialog_box(self._("But was blocked in front.").format(current_battle.enemy.name),
                                                 add_quotes=False,
                                                 hide_arrow=True, disable_sound=True)
                cmd_menu.game.enemy_move(current_battle)
                if player.current_hp <= 0:
                    player.is_dead = True
                else:
                    cmd_menu.show_line_in_dialog_box(self._("Command?\n"), add_quotes=False, hide_arrow=True,
                                                     disable_sound=True)
                return False
            else:
                return True

    def missed_attack(self, cmd_menu):
        missed_sfx_number = random.randint(1, 2)
        if missed_sfx_number == 1:
            self.sound.play_sound(self.directories.missed_sfx)
        else:
            self.sound.play_sound(self.directories.missed_2_sfx)
        cmd_menu.show_line_in_dialog_box("A miss! No damage hath been scored!\n", add_quotes=False,
                                         disable_sound=True, hide_arrow=True)

    def calculate_attack_damage(self, cmd_menu, player, enemy):
        excellent_move_probability = random.randint(0, 31)
        if excellent_move_probability == 0 and enemy.name not in ('Dragonlord', 'Dragonlord 2'):
            self.sound.play_sound(self.directories.excellent_move_sfx)
            cmd_menu.show_line_in_dialog_box(self._("Excellent move!\n"), add_quotes=False, disable_sound=True)
            attack_damage = random.randint(player.attack_power // 2,
                                           player.attack_power)
        else:
            # (HeroAttack - EnemyAgility / 2) / 4,
            #
            # to:
            #
            # (HeroAttack - EnemyAgility / 2) / 2
            lower_bound = round((player.attack_power - (enemy.defense / 2)) / 2)
            upper_bound = round((player.attack_power - (enemy.defense / 2)) * 2)
            # print(f'lower_bound: {lower_bound}\n'
            #       f'upper_bound: {upper_bound}\n'
            #       f'player.attack_power: {player.attack_power}\n'
            #       f'enemy.speed: {enemy.defense}')
            attack_damage = select_random_attack_damage_value(lower_bound, upper_bound)
        return round(attack_damage)

    def battle_spell(self, cmd_menu: CommandMenu, player: Player):
        self.sound.play_sound(self.directories.menu_button_sfx)
        # the implementation of this will vary upon which spell is being cast.
        if not player.spells:
            cmd_menu.show_text_in_dialog_box(self._("{} cannot yet use the spell.").format(player.name),
                                             skip_text=cmd_menu.skip_text)
        else:
            cmd_menu.display_item_menu('spells')
        # cmd_menu.show_line_in_dialog_box(_("{} cannot yet use the spell.").format(player.name) + "\n" +
        #                                  _("Command?\n"), add_quotes=False,
        #                                  hide_arrow=True,
        #                                  disable_sound=True, skip_text=True)

    def enemy_defeated(self, cmd_menu, screen, player, music_enabled, enemy):
        if self.config['LANGUAGE'] == 'Korean':
            ko_enemy_name = self._(enemy.name)
            if ko_enemy_name.endswith(ko_consonant_ending_chars):
                ko_enemy_name += "을"
            else:
                ko_enemy_name += "를"
            enemy_defeated_string = f"{ko_enemy_name} 물리쳤다!\n"
        elif self.config['LANGUAGE'] == 'English':
            enemy_defeated_string = self._("Thou hast done well in defeating the {}.\n").format(self._(enemy.name))
        else:
            enemy_defeated_string = self._("Thou hast done well in defeating the {}.\n").format(self._(enemy.name))
        cmd_menu.show_line_in_dialog_box(enemy_defeated_string, add_quotes=False,
                                         disable_sound=True, hide_arrow=True)
        mixer.music.stop()
        self.sound.play_sound(self.directories.victory_sfx)
        self.make_enemy_image_disappear(screen)
        exp_and_gold = self._("Thy experience increases by {}.\n").format(enemy.xp) + self._(
            "Thy GOLD increases by {}.\n").format(
            enemy.gold)
        cmd_menu.show_line_in_dialog_box(exp_and_gold,
                                         add_quotes=False,
                                         disable_sound=True,
                                         hide_arrow=True)
        player.total_experience += enemy.xp
        player.gold += enemy.gold

        if player.level + 1 < 30 and \
                player.total_experience >= levels_list[player.level + 1]['total_exp']:
            self.sound.play_sound(self.directories.improvement_sfx)
            time.wait(2000)
            if self.config['LANGUAGE'] == 'English':
                cmd_menu.show_line_in_dialog_box("Courage and wit have served thee well.\n"
                                                 "Thou hast been promoted to the next level.\n", add_quotes=False,
                                                 disable_sound=True)
            elif self.config['LANGUAGE'] == 'Korean':
                cmd_menu.show_line_in_dialog_box(f"{player.name}은 {player.level + 1}레벨로 올랐다!", add_quotes=False)
            old_power = player.strength
            old_agility = player.agility
            old_max_hp = player.max_hp
            old_max_mp = player.max_mp
            old_spells = player.spells

            player.level += 1
            player.set_stats_by_level(player.level)
            player.update_attack_power()
            player.update_defense_power()
            player.points_to_next_level = player.get_points_to_next_level()
            if music_enabled:
                mixer.music.load(self.current_map.music_file_path)
                mixer.music.play(-1)

            if player.strength > old_power:
                cmd_menu.show_line_in_dialog_box(
                    self._("Thy power increases by {}.\n").format(player.strength - old_power),
                    add_quotes=False, disable_sound=True)
            if player.agility > old_agility:
                cmd_menu.show_line_in_dialog_box(
                    self._("Thy Response Speed increases by {}.\n").format(player.agility - old_agility),
                    add_quotes=False,
                    disable_sound=True)
            if player.max_hp > old_max_hp:
                cmd_menu.show_line_in_dialog_box(
                    self._("Thy Maximum Hit Points increase by {}.\n").format(player.max_hp - old_max_hp),
                    add_quotes=False,
                    disable_sound=True)
            if player.max_mp > old_max_mp:
                cmd_menu.show_line_in_dialog_box(
                    self._("Thy Maximum Magic Points increase by {}.\n").format(player.max_mp - old_max_mp),
                    add_quotes=False,
                    disable_sound=True)
            if len(player.spells) > len(old_spells):
                cmd_menu.show_line_in_dialog_box("Thou hast learned a new spell.\n", add_quotes=False,
                                                 disable_sound=True)

    def make_enemy_image_disappear(self, screen):
        if self.current_map.is_dark:
            black_surface = Surface((7 * self.tile_size, 7 * self.tile_size))
            black_surface.fill(BLACK)
            battle_background_image = black_surface
        else:
            battle_background_image = scale(image.load(self.directories.BATTLE_BACKGROUND_PATH),
                                            (7 * self.tile_size, 7 * self.tile_size))
        screen.blit(battle_background_image, (5 * self.tile_size, 4 * self.tile_size))
        display.update(battle_background_image.get_rect())

    def get_enemy_draws_near_string(self):
        """Get string for when an enemy draws near (e.g. 'A Slime draws near!')"""
        if self.enemy.name == 'Dragonlord 2':
            enemy_draws_near_string = 'The Dragonlord revealed his true self!\n'
        else:
            if self.config['LANGUAGE'] == 'English':
                enemy_draws_near_string = self._('{} draws near!\n').format(self._(self.enemy.name))
                vowels = 'AEIOU'
                if self.enemy.name[0] in vowels:
                    enemy_draws_near_string = self._('An {}').format(enemy_draws_near_string)
                else:
                    enemy_draws_near_string = self._('A {}').format(enemy_draws_near_string)
            elif self.config['LANGUAGE'] == 'Korean':
                ko_enemy_name = self._(self.enemy.name)
                if ko_enemy_name.endswith(ko_consonant_ending_chars):
                    ko_enemy_name += "이"
                else:
                    ko_enemy_name += "가"
                enemy_draws_near_string = self._('{} draws near!\n').format(ko_enemy_name)
            else:
                enemy_draws_near_string = self._('{} draws near!\n')
        enemy_draws_near_string += self._("Command?\n")
        return enemy_draws_near_string

    def display_battle_window(self, screen, drawer, cmd_menu, graphics, directories, color, player):
        self.transition_battle_background_image_effect(screen)
        drawer.show_enemy_image(screen, self.enemy.name)
        cmd_menu.show_line_in_battle_dialog_box(self.get_enemy_draws_near_string())
        # drop down for the hovering stats window
        cmd_menu.window_drop_down_effect(1, 2, 4, 6)
        # drop down for the battle menu
        cmd_menu.window_drop_down_effect(6, 1, 8, 3)
        graphics.create_window(6, 1, 8, 3, directories.BATTLE_MENU_FIGHT_PATH, screen, color)
        drawer.hovering_stats_displayed = True
        drawer.draw_hovering_stats_window(screen, player, color)


def select_random_attack_damage_value(lower_bound, upper_bound) -> int:
    if lower_bound > upper_bound:
        attack_damage = random.randint(upper_bound, lower_bound)
    elif lower_bound == upper_bound:
        attack_damage = lower_bound
    else:
        attack_damage = random.randint(lower_bound, upper_bound)
    if attack_damage < 1:
        # fifty-fifty chance of doing 1 damage
        if random.random() < .5:
            attack_damage = 1
        else:
            attack_damage = 0
    return attack_damage


def calculate_enemy_attack_damage(player, enemy):
    lower_bound = (enemy.attack - player.agility / 2) // 4
    upper_bound = (enemy.attack - player.agility / 2) // 2
    return select_random_attack_damage_value(lower_bound, upper_bound)
