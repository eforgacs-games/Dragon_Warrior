import random

from pygame import image, display, time, mixer, Surface
from pygame.transform import scale

from src.common import BLACK, set_gettext_language
from src.directories import Directories
from src.enemy import enemy_groups
from src.enemy_lookup import enemy_string_lookup
from src.maps import DragonWarriorMap
from src.menu import CommandMenu
from src.player.player import Player
from src.player.player_stats import levels_list
from src.sound import Sound

# Constants for probabilities and thresholds
EXCELLENT_MOVE_PROBABILITY = 0
EXCELLENT_MOVE_THRESHOLD = 31
GROUP_FACTOR_LOOKUP = {1: 0.25, 2: 0.375, 3: 0.5, 4: 1.0}
MISS_SFX_PROBABILITY = 0.5
MIN_DAMAGE = 1


def has_final_consonant(char: str) -> bool:
    """Check if a Korean character has a final consonant."""
    if len(char) != 1:
        raise ValueError("Function expects a single character")
    code = ord(char) - 0xAC00
    return (code % 28) != 0


def get_postposition(name: str, consonant_josa: str, vowel_josa: str) -> str:
    """Get the correct postposition for a Korean character.
    :param name: The name.
    :param consonant_josa: The postposition for a consonant. e.g. "을"
    :param vowel_josa: The postposition for a vowel. e.g. "를"
    :return: The correct postposition.
    """
    last_char = name[-1]
    return consonant_josa if has_final_consonant(last_char) else vowel_josa


class Battle:
    def __init__(self, config, enemy_name: str, current_map: DragonWarriorMap):
        self.config = config
        self.directories = Directories(config)
        self.sound = Sound(config)
        self._ = set_gettext_language(config['LANGUAGE'])
        self.turn = 0
        self.last_turn = 0
        self.enemy = enemy_string_lookup[enemy_name]()
        self.tile_size = config['TILE_SIZE']
        self.current_map = current_map
        self.no_op = False
        # Add graphics for image caching
        from src.common import Graphics
        self.graphics = Graphics(config)

    def play_battle_music(self):
        if self.config["MUSIC_ENABLED"]:
            mixer.music.load(self.directories.battle_music)
            mixer.music.play(-1)

    def transition_battle_background_image_effect(self, screen):
        """Spiral effect to introduce battle background."""
        battle_background_image = self.get_battle_background_image()
        spiral_tile_coordinates = self.get_spiral_tile_coordinates()

        for tile in spiral_tile_coordinates:
            screen.blit(battle_background_image.subsurface(
                (tile[0] * self.tile_size, tile[1] * self.tile_size, self.tile_size, self.tile_size)),
                ((tile[0] + 5) * self.tile_size, (tile[1] + 4) * self.tile_size))
            display.update()
            time.wait(20)

    def get_battle_background_image(self):
        """Get the appropriate battle background image."""
        if not self.current_map.is_dark:
            # Use cached scaled image
            scaled_size = (7 * self.tile_size, 7 * self.tile_size)
            return self.graphics.get_scaled_image(self.directories.BATTLE_BACKGROUND_PATH, scaled_size)
        black_surface = Surface((7 * self.tile_size, 7 * self.tile_size))
        black_surface.fill(BLACK)
        return black_surface

    @staticmethod
    def get_spiral_tile_coordinates():
        """Return the coordinates for the spiral effect."""
        return (
            (3, 3), (3, 4), (2, 4), (2, 3), (2, 2), (3, 2), (4, 2), (4, 3), (4, 4), (4, 5),
            (3, 5), (2, 5), (1, 5), (1, 4), (1, 3), (1, 2), (1, 1), (2, 1), (3, 1), (4, 1),
            (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6),
            (0, 6), (0, 5), (0, 4), (0, 3), (0, 2), (0, 1), (0, 0), (1, 0), (2, 0), (3, 0),
            (4, 0), (5, 0), (6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (6, 5), (6, 6)
        )

    def battle_run(self, cmd_menu: CommandMenu, player: Player, current_battle):
        """Attempt to run from a battle."""
        self.sound.play_sound(self.directories.stairs_down_sfx)
        cmd_menu.show_line_in_dialog_box(self._("{} started to run away.\n").format(player.name), add_quotes=False,
                                         hide_arrow=True, disable_sound=True)
        random_number = random.randint(0, 255)
        group_factor = self.get_group_factor(current_battle.enemy.name)

        if current_battle.enemy.is_asleep:
            return True

        if player.agility * random_number < current_battle.enemy.speed * random_number * GROUP_FACTOR_LOOKUP[
            group_factor]:
            cmd_menu.show_line_in_dialog_box(self._("But was blocked in front.").format(current_battle.enemy.name),
                                             add_quotes=False, hide_arrow=True, disable_sound=True)
            cmd_menu.game.enemy_move(current_battle)
            if player.current_hp <= 0:
                player.is_dead = True
            else:
                cmd_menu.show_line_in_dialog_box(self._("Command?\n"), add_quotes=False, hide_arrow=True,
                                                 disable_sound=True)
            return False
        return True

    @staticmethod
    def get_group_factor(enemy_name):
        """Get the group factor for a given enemy."""
        for group_number, group in enemy_groups.items():
            if enemy_name in group:
                return group_number
        return 1

    def missed_attack(self, cmd_menu):
        """Handle a missed attack."""
        missed_sfx_number = random.randint(1, 2)
        missed_sound = self.directories.missed_sfx if missed_sfx_number == 1 else self.directories.missed_2_sfx
        self.sound.play_sound(missed_sound)
        cmd_menu.show_line_in_dialog_box(self._("A miss! No damage hath been scored!"), add_quotes=False,
                                         disable_sound=True, hide_arrow=True)

    def calculate_attack_damage(self, cmd_menu, player, enemy):
        """Calculate the damage of an attack."""
        if random.randint(0, EXCELLENT_MOVE_THRESHOLD) == EXCELLENT_MOVE_PROBABILITY and enemy.name not in (
                'Dragonlord', 'Dragonlord 2'):
            self.sound.play_sound(self.directories.excellent_move_sfx)
            cmd_menu.show_line_in_dialog_box(self._("Excellent move!\n"), add_quotes=False, disable_sound=True)
            return round(random.randint(player.attack_power // 2, player.attack_power))

        lower_bound = round((player.attack_power - (enemy.defense / 2)) / 2)
        upper_bound = round((player.attack_power - (enemy.defense / 2)) * 2)
        return round(select_random_attack_damage_value(lower_bound, upper_bound))

    def battle_spell(self, cmd_menu: CommandMenu, player: Player, current_battle):
        """Handle casting a spell in battle."""
        self.sound.play_sound(self.directories.menu_button_sfx)
        if not player.spells:
            cmd_menu.show_line_in_dialog_box(self._("{} cannot yet use the spell.").format(player.name),
                                             skip_text=cmd_menu.skip_text, add_quotes=False, hide_arrow=True,
                                             disable_sound=True)
            current_battle.no_op = True
        else:
            cmd_menu.display_item_menu('spells')

    def enemy_defeated(self, cmd_menu, screen, player, music_enabled, enemy):
        """Handle an enemy being defeated."""
        enemy_defeated_string = self.get_enemy_defeated_string(enemy)
        cmd_menu.show_line_in_dialog_box(enemy_defeated_string, add_quotes=False, disable_sound=True, hide_arrow=True)
        mixer.music.stop()
        self.sound.play_sound(self.directories.victory_sfx)
        self.make_enemy_image_disappear(screen)
        exp_and_gold = self._("Thy experience increases by {}.\n").format(enemy.xp) + self._(
            "Thy GOLD increases by {}.\n").format(enemy.gold)
        cmd_menu.show_line_in_dialog_box(exp_and_gold, add_quotes=False, disable_sound=True, hide_arrow=True)
        player.total_experience += enemy.xp
        player.gold += enemy.gold
        self.check_player_level_up(cmd_menu, player, music_enabled)

    def get_enemy_defeated_string(self, enemy):
        """Get the enemy defeated string based on language."""
        if self.config['LANGUAGE'] == 'Korean':
            ko_enemy_name = self._(enemy.name)
            ko_enemy_name += get_postposition(ko_enemy_name, "을", "를")
            return f"{ko_enemy_name} 물리쳤다!\n"
        return self._("Thou hast done well in defeating the {}.\n").format(self._(enemy.name))

    def check_player_level_up(self, cmd_menu, player, music_enabled):
        """Check if the player levels up."""
        if player.level + 1 < 30 and player.total_experience >= levels_list[player.level + 1]['total_exp']:
            self.sound.play_sound(self.directories.improvement_sfx)
            time.wait(2000)
            self.display_level_up_message(cmd_menu, player)
            old_stats = self.get_player_stats(player)
            player.level += 1
            player.set_stats_by_level(player.level)
            player.update_attack_power()
            player.update_defense_power()
            player.points_to_next_level = player.get_points_to_next_level()
            if music_enabled:
                mixer.music.load(self.current_map.music_file_path)
                mixer.music.play(-1)
            self.display_stat_increases(cmd_menu, player, old_stats)

    def display_level_up_message(self, cmd_menu, player):
        """Display the level up message."""
        if self.config['LANGUAGE'] == 'English':
            cmd_menu.show_line_in_dialog_box(
                "Courage and wit have served thee well.\nThou hast been promoted to the next level.\n",
                add_quotes=False, disable_sound=True)
        elif self.config['LANGUAGE'] == 'Korean':
            cmd_menu.show_line_in_dialog_box(f"{player.name}은 {player.level + 1}레벨로 올랐다!", add_quotes=False)

    @staticmethod
    def get_player_stats(player):
        """Get the current stats of the player."""
        return {
            "strength": player.strength,
            "agility": player.agility,
            "max_hp": player.max_hp,
            "max_mp": player.max_mp,
            "spells": player.spells.copy()
        }

    def display_stat_increases(self, cmd_menu, player, old_stats):
        """Display the increases in player's stats."""
        if player.strength > old_stats["strength"]:
            cmd_menu.show_line_in_dialog_box(
                self._("Thy power increases by {}.\n").format(player.strength - old_stats["strength"]),
                add_quotes=False, disable_sound=True)
        if player.agility > old_stats["agility"]:
            cmd_menu.show_line_in_dialog_box(
                self._("Thy Response Speed increases by {}.\n").format(player.agility - old_stats["agility"]),
                add_quotes=False, disable_sound=True)
        if player.max_hp > old_stats["max_hp"]:
            cmd_menu.show_line_in_dialog_box(
                self._("Thy Maximum Hit Points increase by {}.\n").format(player.max_hp - old_stats["max_hp"]),
                add_quotes=False, disable_sound=True)
        if player.max_mp > old_stats["max_mp"]:
            cmd_menu.show_line_in_dialog_box(
                self._("Thy Maximum Magic Points increase by {}.\n").format(player.max_mp - old_stats["max_mp"]),
                add_quotes=False, disable_sound=True)
        if len(player.spells) > len(old_stats["spells"]):
            cmd_menu.show_line_in_dialog_box("Thou hast learned a new spell.\n", add_quotes=False, disable_sound=True)

    def make_enemy_image_disappear(self, screen):
        """Make the enemy image disappear from the screen."""
        battle_background_image = self.get_battle_background_image()
        screen.blit(battle_background_image, (5 * self.tile_size, 4 * self.tile_size))
        display.update(battle_background_image.get_rect())

    def get_enemy_draws_near_string(self):
        """Get string for when an enemy draws near."""
        if self.enemy.name == 'Dragonlord 2':
            return 'The Dragonlord revealed his true self!\n' + self._("Command?\n")

        if self.config['LANGUAGE'] == 'English':
            enemy_draws_near_string = self._('{} draws near!\n').format(self._(self.enemy.name))
            vowels = 'AEIOU'
            if self.enemy.name[0] in vowels:
                return self._('An {}').format(enemy_draws_near_string) + self._("Command?\n")
            return self._('A {}').format(enemy_draws_near_string) + self._("Command?\n")

        if self.config['LANGUAGE'] == 'Korean':
            ko_enemy_name = self._(self.enemy.name)
            ko_enemy_name += get_postposition(ko_enemy_name, "이", "가")
            return self._('{} draws near!\n').format(ko_enemy_name) + self._("Command?\n")

        return self._('{} draws near!\n').format(self._(self.enemy.name)) + self._("Command?\n")

    def display_battle_window(self, screen, drawer, cmd_menu, graphics, directories, color, player):
        """Display the battle window."""
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


def select_random_attack_damage_value(lower_bound: int, upper_bound: int) -> int:
    """Select a random attack damage value within the given bounds."""
    lower_bound, upper_bound = int(lower_bound), int(upper_bound)
    if lower_bound > upper_bound:
        attack_damage = random.randint(upper_bound, lower_bound)
    elif lower_bound == upper_bound:
        attack_damage = lower_bound
    else:
        attack_damage = random.randint(lower_bound, upper_bound)
    if attack_damage < MIN_DAMAGE:
        return MIN_DAMAGE if random.random() < MISS_SFX_PROBABILITY else 0
    return attack_damage


def calculate_enemy_attack_damage(player, enemy):
    """Calculate the damage of an enemy's attack."""
    lower_bound = (enemy.attack - player.agility / 2) // 4
    upper_bound = (enemy.attack - player.agility / 2) // 2
    return select_random_attack_damage_value(lower_bound, upper_bound)
