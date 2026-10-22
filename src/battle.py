import random

from pygame import display, time, mixer, Surface

from src.common import BLACK, set_gettext_language
from src.constants import (
    EXCELLENT_MOVE_PROBABILITY, EXCELLENT_MOVE_THRESHOLD,
    BATTLE_MENU_X, BATTLE_MENU_Y, BATTLE_MENU_WIDTH, BATTLE_MENU_HEIGHT,
)
from src.directories import Directories
from src.enemy import enemy_groups
from src.enemy_lookup import enemy_string_lookup
from src.maps import DragonWarriorMap
from src.menu import CommandMenu
from src.player.player import Player
from src.player.player_stats import levels_list
from src.sound import Sound
from src.waiting import check_for_quit, wait, wait_frames

DRAGONLORD_TRANSFORM_WAIT_FRAMES = 80  # NES EnemyDefeated: 80 frames between the two Dragonlord fights


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
        self.enemy.hp = randomize_enemy_hp(self.enemy)
        self.tile_size = config['TILE_SIZE']
        self.current_map = current_map
        self.no_op = False
        # Add graphics for image caching
        from src.common import Graphics
        self.graphics = Graphics(config)

    def play_battle_music(self):
        if self.config["MUSIC_ENABLED"]:
            # NES InitFight: the Dragonlord's final form gets the end boss music (MSC_END_BOSS); every other
            # fight, including his first form, gets the regular fight music (MSC_ENTR_FGHT).
            music = self.directories.end_boss_music if self.enemy.name == 'Dragonlord 2' else \
                self.directories.battle_music
            mixer.music.load(music)
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
            check_for_quit()
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
        """Attempt to run from a battle (NES PlyrRun)."""
        self.sound.play_sound(self.directories.stairs_down_sfx)
        cmd_menu.show_line_in_dialog_box(self._("{} started to run away.\n").format(player.name), add_quotes=False,
                                         hide_arrow=True, disable_sound=True)

        # NES PlyrRun: running from a sleeping enemy always works.
        if current_battle.enemy.is_asleep:
            return True

        if not can_run_away(player.agility, current_battle.enemy.defense,
                            self.get_group_factor(current_battle.enemy.name)):
            cmd_menu.show_line_in_dialog_box(self._("But was blocked in front.").format(current_battle.enemy.name),
                                             add_quotes=False, hide_arrow=True, disable_sound=True)
            if cmd_menu.game.enemy_move(current_battle):
                return True
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
        # NES: 1 in 32 chance of an excellent move, except against either form of the Dragonlord
        if random.randint(0, EXCELLENT_MOVE_THRESHOLD) == EXCELLENT_MOVE_PROBABILITY and enemy.name not in (
                'Dragonlord', 'Dragonlord 2'):
            self.sound.play_sound(self.directories.excellent_move_sfx)
            cmd_menu.show_line_in_dialog_box(self._("Excellent move!\n"), add_quotes=False, disable_sound=True)
            # Damage = attack - (attack / 2 * rand(255)) / 256, i.e. about half to all of attack power
            return player.attack_power - (player.attack_power // 2) * random.randint(0, 255) // 256

        # NES PlyrCalcHitDmg
        base_attack = player.attack_power - enemy.defense // 2
        if base_attack < 2:
            # Weak attack: the enemy's defense is too high, so 0 or 1 damage, 50/50.
            return random.randint(0, 1)
        return normal_attack_damage(base_attack, random.randint(0, 255))

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
        if enemy.name == 'Dragonlord 2':
            # NES NotDL1Defeated: the final boss gives no experience or gold; the ending takes over from here
            cmd_menu.game.ending.final_boss_defeated()
            return
        gold = randomize_enemy_gold(enemy.gold)
        exp_and_gold = self._("Thy experience increases by {}.\n").format(enemy.xp) + self._(
            "Thy GOLD increases by {}.\n").format(gold)
        cmd_menu.show_line_in_dialog_box(exp_and_gold, add_quotes=False, disable_sound=True, hide_arrow=True)
        player.total_experience += enemy.xp
        player.gold += gold
        self.check_player_level_up(cmd_menu, player, music_enabled)

    def dragonlord_first_form_defeated(self, cmd_menu, screen):
        """NES EnemyDefeated for EN_DRAGONLORD1: "Thou hast done well in defeating the Dragonlord.", the victory
        music, then an 80-frame wait. No experience or gold is given: the routine jumps straight to InitFight
        with EN_DRAGONLORD2 instead of RegEnDefeated."""
        cmd_menu.show_line_in_dialog_box(self.get_enemy_defeated_string(self.enemy), add_quotes=False,
                                         disable_sound=True, hide_arrow=True)
        mixer.music.stop()
        self.sound.play_sound(self.directories.victory_sfx)
        self.make_enemy_image_disappear(screen)
        wait_frames(DRAGONLORD_TRANSFORM_WAIT_FRAMES, self.config)

    def get_enemy_defeated_string(self, enemy):
        """Get the enemy defeated string based on language."""
        # NES: both of the Dragonlord's forms are named "Dragonlord"
        enemy_name = 'Dragonlord' if enemy.name == 'Dragonlord 2' else enemy.name
        if self.config['LANGUAGE'] == 'Korean':
            ko_enemy_name = self._(enemy_name)
            ko_enemy_name += get_postposition(ko_enemy_name, "을", "를")
            return f"{ko_enemy_name} 물리쳤다!\n"
        return self._("Thou hast done well in defeating the {}.\n").format(self._(enemy_name))

    def check_player_level_up(self, cmd_menu, player, music_enabled):
        """Check if the player levels up."""
        if player.level + 1 < 30 and player.total_experience >= levels_list[player.level + 1]['total_exp']:
            self.sound.play_sound(self.directories.improvement_sfx)
            wait(2000)
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
        # NES LoadCombatBckgrnd: no battle background is drawn for the Dragonlord's final form.
        if self.enemy.name != 'Dragonlord 2':
            self.transition_battle_background_image_effect(screen)
        # NES LoadEnemyGFX: the enemy fades in from a black shadow, twice.
        drawer.fade_in_enemy(screen, self.enemy.name)
        cmd_menu.show_line_in_battle_dialog_box(self.get_enemy_draws_near_string())
        # drop down for the hovering stats window
        cmd_menu.window_drop_down_effect(1, 2, 4, 6)
        # drop down for the battle menu
        cmd_menu.window_drop_down_effect(BATTLE_MENU_X, BATTLE_MENU_Y, BATTLE_MENU_WIDTH, BATTLE_MENU_HEIGHT)
        graphics.create_window(BATTLE_MENU_X, BATTLE_MENU_Y, BATTLE_MENU_WIDTH, BATTLE_MENU_HEIGHT,
                                directories.BATTLE_MENU_FIGHT_PATH, screen, color)
        drawer.hovering_stats_displayed = True
        drawer.draw_hovering_stats_window(screen, player, color)


def randomize_enemy_hp(enemy) -> int:
    """Starting HP for a battle, per the NES ModEnHitPoints routine: 75% to 100% of the enemy's listed HP.
    The Dragonlord's final form always starts at full HP."""
    if enemy.name == 'Dragonlord 2':
        return enemy.max_hp
    return enemy.max_hp - (enemy.max_hp * random.randint(0, 255) // 256) // 4


def randomize_enemy_gold(base_gold: int) -> int:
    """Gold dropped by a defeated enemy, per the NES CalcPlyrGold routine (Bank03 RegEnDefeated): the base gold
    byte times (192 + rand(0-63)) / 256, i.e. 75% to just under 100% of the base value, rounded down."""
    return base_gold * (192 + random.randint(0, 63)) // 256


def can_run_away(player_agility: int, enemy_defense: int, enemy_group: int) -> bool:
    """NES TryRun: the run works when rand(0-255) * the player's agility is at least the enemy's roll times its
    defense. The enemy's roll gets bigger the further down the enemy list it is: 0-63 for the first group,
    0-94 for Drollmagi to Werewolf, 0-127 for Green Dragon to Blue Dragon, and the full 0-255 for Stoneman,
    Armored Knight, Red Dragon and both forms of the Dragonlord (CalcNextOdds)."""
    if enemy_group == 4:
        enemy_roll = random.randint(0, 255)
    elif enemy_group == 3:
        enemy_roll = random.randint(0, 255) & 0x7F
    elif enemy_group == 2:
        enemy_roll = (random.randint(0, 255) & 0x3F) + (random.randint(0, 255) & 0x1F)
    else:
        enemy_roll = random.randint(0, 255) & 0x3F
    player_roll = random.randint(0, 255)
    return player_roll * player_agility >= enemy_roll * enemy_defense


def normal_attack_damage(base_attack: int, random_number: int) -> int:
    """NES NormalAttack, shared by player and enemy hits: base_attack / 4 to base_attack / 2."""
    return ((base_attack + 1) * random_number // 256 + base_attack) // 4


def calculate_enemy_attack_damage(player, enemy):
    """Calculate the damage of an enemy's physical attack, following the NES EnCalcHitDmg routine."""
    base_attack = enemy.attack - player.defense_power // 2
    random_number = random.randint(0, 255)
    if base_attack < enemy.attack // 2 + 1:
        # Weak attack: the player's defense is high compared to the enemy's attack.
        return ((enemy.attack // 2 + 1) * random_number // 256 + 2) // 3
    return normal_attack_damage(base_attack, random_number)
