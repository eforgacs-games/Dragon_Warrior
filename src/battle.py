import random

from pygame import display, Surface

from src.common import BLACK, set_gettext_language, singular_or_plural
from src.constants import BATTLE_MENU_X, BATTLE_MENU_Y, BATTLE_MENU_WIDTH, BATTLE_MENU_HEIGHT
from src.directories import Directories
from src.enemy import enemy_groups
from src.enemy_lookup import enemy_string_lookup
from src.korean_particles import get_postposition, particle
from src.maps import DragonWarriorMap
from src.translated_window import draw_translated_window
from src.windows import COMBAT_COMMAND_LAYOUT
from src.menu import CommandMenu
from src.player.player import Player
from src.player.player_stats import get_level_by_experience
from src.sound import Sound
from src.waiting import check_for_quit, wait_frames

MAX_EXPERIENCE = 0xFFFF  # NES RegEnDefeated: ExpLB/ExpUB max out at $FFFF
MAX_GOLD = 0xFFFF  # NES RegEnDefeated: GoldLB/GoldUB max out at $FFFF
DRAGONLORD_TRANSFORM_WAIT_FRAMES = 80  # NES EnemyDefeated: 80 frames between the two Dragonlord fights
SPIRAL_LEAD_IN_FRAMES = 1  # NES LoadCombatBckgrnd: WaitForNMI at $E40A, before the first block
SPIRAL_FRAMES_PER_BLOCK = 1  # NES LoadCombatBckgrnd: WaitForNMI at $E43D, once per block
HERO_SCREEN_BLOCK = (8, 7)  # NES DoSprites: the hero's sprites are at x $80, y $6F, the middle of the screen


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
        self.enemy_fled = False  # set by BattleController.enemy_run_away
        # Add graphics for image caching
        from src.common import Graphics
        self.graphics = Graphics(config)

    def play_battle_music(self, music_player):
        """NES InitFight: the Dragonlord's final form gets the end boss music (MSC_END_BOSS); every other fight,
        including his first form, gets the regular fight music (MSC_ENTR_FGHT)."""
        music = self.directories.end_boss_music if self.enemy.name == 'Dragonlord 2' else self.directories.battle_music
        music_player.load_and_play_music(music)

    def transition_battle_background_image_effect(self, screen, player):
        """Spiral effect to introduce battle background (NES LoadCombatBckgrnd, $E3CD).

        The NES waits for one vblank (WaitForNMI at $E40A) before the loop, then waits for one vblank before each
        block ($E43D), so the 49 blocks land on 49 consecutive frames: one block per frame, about 0.83 s in all.

        The hero disappears one frame before the first (centre) block, and stays hidden for the whole spiral. Right
        after $E40A, LoadCombatBckgrnd calls DoSprites ($E40D). The background is already in the window buffer by then,
        so DoSprites sees WinBufRAM+$1D0 (the hero's spot) covered and moves the hero's sprites off screen ($F0). The
        NMI at $E43D copies sprite RAM to the PPU (SetSprtRAM), so he's gone from that frame, and the centre block
        that this NMI's wait queues only reaches the screen at the next one. Nothing calls DoSprites again until the
        fight is over: LoadEnemyGFX only writes the sprites after the hero's ($10 onward).
        """
        battle_background_image = self.get_battle_background_image()
        spiral_tile_coordinates = self.get_spiral_tile_coordinates()

        wait_frames(SPIRAL_LEAD_IN_FRAMES)
        self.hide_hero(screen, player)
        display.update()
        for tile in spiral_tile_coordinates:
            wait_frames(SPIRAL_FRAMES_PER_BLOCK)
            screen.blit(battle_background_image.subsurface(
                (tile[0] * self.tile_size, tile[1] * self.tile_size, self.tile_size, self.tile_size)),
                ((tile[0] + 5) * self.tile_size, (tile[1] + 4) * self.tile_size))
            display.update()
            check_for_quit()

    def hide_hero(self, screen, player):
        """Draw the map block under the hero over him, as NES DoSprites does when a window covers his spot. He's always
        on screen block (8, 7) (DoSprites: x $80, y $6F), the centre of the spiral."""
        tile_size = self.tile_size
        hero_block = (player.rect.x // tile_size * tile_size, player.rect.y // tile_size * tile_size)
        for tile_dict in self.current_map.floor_tile_key.values():
            for tile in tile_dict.get('group') or ():
                if tile.rect.topleft == hero_block:
                    screen.blit(tile.image, (HERO_SCREEN_BLOCK[0] * tile_size, HERO_SCREEN_BLOCK[1] * tile_size))
                    return

    def get_battle_background_image(self):
        """Get the appropriate battle background image.

        NES LoadCombatBckgrnd ($E3E4): the background graphic (CombatBckgndGFX) is only used on the overworld map
        (MAP_OVERWORLD). On every other map (caves, but also Hauksness and the Dragonlord's castle, which aren't dark)
        the 14x14 tiles are all TL_BLANK_TILE1, so the spiral draws black.
        """
        if self.current_map.identifier == 'Alefgard':
            # Use cached scaled image
            scaled_size = (7 * self.tile_size, 7 * self.tile_size)
            return self.graphics.get_scaled_image(self.directories.BATTLE_BACKGROUND_PATH, scaled_size)
        black_surface = Surface((7 * self.tile_size, 7 * self.tile_size))
        black_surface.fill(BLACK)
        return black_surface

    @staticmethod
    def get_spiral_tile_coordinates():
        """Return the coordinates for the spiral effect: NES CmbtBGPlcmntTbl ($F397), one (x, y) per 2x2-tile block,
        starting at the centre and turning clockwise (down, left, up, right) outward."""
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
            if cmd_menu.game.battle_ctrl.enemy_move(current_battle):
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
        """NES ChkPlyrMiss: the hero's hit did no damage. SFX_MISSED1 and "The attack failed and there was no loss
        of Hit Points!" (TextBlock15, entry 7)."""
        self.sound.play_sound(self.directories.missed_sfx)
        cmd_menu.show_line_in_dialog_box(self._("The attack failed and there was no loss of Hit Points!"),
                                         add_quotes=False, disable_sound=True, hide_arrow=True)

    def enemy_missed_attack(self, cmd_menu):
        """NES EnPhysAttack: the enemy's hit did no damage. SFX_MISSED2 and "A miss! No damage hath been scored!"
        (TextBlock16, entry 11)."""
        self.sound.play_sound(self.directories.missed_2_sfx)
        cmd_menu.show_line_in_dialog_box(self._("A miss! No damage hath been scored!"), add_quotes=False,
                                         disable_sound=True, hide_arrow=True)

    def calculate_attack_damage(self, cmd_menu, player, enemy):
        """The hero's FIGHT damage, per NES PlyrFight ($E5FE)."""
        # NES PlyrFight: no excellent moves against either form of the Dragonlord (EN_DRAGONLORD1/2)
        if enemy.name not in ('Dragonlord', 'Dragonlord 2') and is_excellent_move(random.randint(0, 255)):
            self.sound.play_sound(self.directories.excellent_move_sfx)
            cmd_menu.show_line_in_dialog_box(self._("Excellent move!\n"), add_quotes=False, disable_sound=True)
            return excellent_move_damage(player.attack_power, random.randint(0, 255))
        return player_hit_damage(player.attack_power, enemy.defense)

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

    def enemy_defeated(self, cmd_menu, screen, player, enemy):
        """Handle an enemy being defeated."""
        self.announce_enemy_defeated(cmd_menu, screen, enemy)
        if enemy.name == 'Dragonlord 2':
            # NES NotDL1Defeated: the final boss gives no experience or gold; the ending takes over from here
            cmd_menu.game.ending.final_boss_defeated()
            return
        # NES RegEnDefeated: the experience is the enemy's exact base value; the gold is varied (CalcPlyrGold).
        # Both totals stop at 65535.
        gold = randomize_enemy_gold(enemy.gold)
        exp_and_gold = self._("Thy Experience\nincreases by {}.\n").format(enemy.xp) + self._(
            "Thy GOLD\nincreases by {}.\n").format(gold)
        # TB15E15 and TB16E0 end with no WAIT: the victory music goes on playing while they print
        cmd_menu.show_line_in_dialog_box(exp_and_gold, add_quotes=False, disable_sound=True, hide_arrow=True,
                                         skip_text=True)
        player.total_experience = min(player.total_experience + enemy.xp, MAX_EXPERIENCE)
        player.gold = min(player.gold + gold, MAX_GOLD)
        self.check_player_level_up(cmd_menu, player)

    def dragonlord_first_form_defeated(self, cmd_menu, screen):
        """NES EnemyDefeated for EN_DRAGONLORD1: "Thou hast done well in defeating the Dragonlord.", the victory
        music, then an 80-frame wait. No experience or gold is given: the routine jumps straight to InitFight
        with EN_DRAGONLORD2 instead of RegEnDefeated."""
        self.announce_enemy_defeated(cmd_menu, screen, self.enemy)
        wait_frames(DRAGONLORD_TRANSFORM_WAIT_FRAMES, self.config)

    def announce_enemy_defeated(self, cmd_menu, screen, enemy):
        """NES EnemyDefeated (ContEnDefeated): TextBlock15 entry 14, "Thou hast done well in defeating the ENMY.", ends
        with no WAIT, so as soon as it has printed the enemy is erased (ClearSpriteRAM) and the victory music starts
        (MSC_VICTORY), without a button press."""
        cmd_menu.show_line_in_dialog_box(self.get_enemy_defeated_string(enemy), add_quotes=False, disable_sound=True,
                                         hide_arrow=True, skip_text=True)
        self.make_enemy_image_disappear(screen)
        cmd_menu.game.music_player.play_clip(self.directories.victory_music)

    def get_enemy_defeated_string(self, enemy):
        """Get the enemy defeated string based on language."""
        # NES: both of the Dragonlord's forms are named "Dragonlord"
        enemy_name = 'Dragonlord' if enemy.name == 'Dragonlord 2' else enemy.name
        if self.config['LANGUAGE'] == 'Korean':
            ko_enemy_name = self._(enemy_name)
            ko_enemy_name += get_postposition(ko_enemy_name, "을", "를")
            return f"{ko_enemy_name} 물리쳤다!\n"
        return self._("Thou hast done well in defeating the {}.\n").format(self._(enemy_name))

    def check_player_level_up(self, cmd_menu, player):
        """NES ChkLevelUp (RegEnDefeated). LoadStats works the level out from the experience again, so the level can
        jump by more than one, and level 30 can be reached. Without a level up, WaitForMusicEnd lets the victory music
        finish and the map's music resumes (ResumeMusicTbl), then ExitFight waits for a new button press. With one,
        DoLevelUp starts MSC_LEVEL_UP, which cuts the victory music off, waits for it to end (WaitForMusicEnd), resumes
        the map's music, and only then says "Thou hast been promoted to the next level." and the stat increases
        (ChkStrengthUp-ChkMPUp)."""
        music_player = cmd_menu.game.music_player
        new_level = get_level_by_experience(player.total_experience)
        if new_level > player.level:
            music_player.play_until_end(self.directories.level_up_music, self.config)
            self.resume_map_music(music_player)
            # TB16E1 starts with a WAIT: the experience and gold lines stay up, with the arrow, until A or B
            cmd_menu.wait_for_button(shows_arrow=True)
            self.display_level_up_message(cmd_menu, player, new_level)
            old_stats = self.get_player_stats(player)
            player.level = new_level
            player.set_stats_by_level(player.level)
            player.update_attack_power()
            player.update_defense_power()
            self.display_stat_increases(cmd_menu, player, old_stats)
        else:
            music_player.wait_for_music_end(self.config)
            self.resume_map_music(music_player)
            # ExitFight: WaitForBtnRelease, so a button pressed during the music doesn't count; a new press returns
            # to the map
            cmd_menu.wait_for_button(shows_arrow=False)

    def resume_map_music(self, music_player):
        """NES ResumeMusicTbl: the current map's music, from the start."""
        music_player.load_and_play_music(self.current_map.music_file_path)

    def display_level_up_message(self, cmd_menu, player, new_level=None):
        """Display the level up message."""
        if self.config['LANGUAGE'] == 'English':
            cmd_menu.show_line_in_dialog_box(
                self._("Courage and wit have served thee well.\nThou hast been promoted to the next level.\n"),
                add_quotes=False, disable_sound=True)
        elif self.config['LANGUAGE'] == 'Korean':
            new_level = player.level + 1 if new_level is None else new_level
            hero = player.name + particle(player.name, '은/는')
            cmd_menu.show_line_in_dialog_box(f"{hero} {new_level}레벨로 올랐다!", add_quotes=False)

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
        # NES TextBlock18 entries 0 and 1: PNTS prints "Point" for an increase of 1 (Bank01 DoPNTS)
        if player.max_hp > old_stats["max_hp"]:
            increase = player.max_hp - old_stats["max_hp"]
            cmd_menu.show_line_in_dialog_box(
                singular_or_plural(increase, self._("Thy Maximum Hit Point increase by {}.\n"),
                                   self._("Thy Maximum Hit Points increase by {}.\n")).format(increase),
                add_quotes=False, disable_sound=True)
        if player.max_mp > old_stats["max_mp"]:
            increase = player.max_mp - old_stats["max_mp"]
            cmd_menu.show_line_in_dialog_box(
                singular_or_plural(increase, self._("Thy Maximum Magic Point increase by {}.\n"),
                                   self._("Thy Maximum Magic Points increase by {}.\n")).format(increase),
                add_quotes=False, disable_sound=True)
        if len(player.spells) > len(old_stats["spells"]):
            cmd_menu.show_line_in_dialog_box(self._("Thou hast learned a new spell.\n"), add_quotes=False, disable_sound=True)

    def make_enemy_image_disappear(self, screen):
        """Make the enemy image disappear from the screen."""
        battle_background_image = self.get_battle_background_image()
        screen.blit(battle_background_image, (5 * self.tile_size, 4 * self.tile_size))
        display.update(battle_background_image.get_rect())

    def get_enemy_draws_near_string(self):
        """Get string for when an enemy draws near."""
        if self.enemy.name == 'Dragonlord 2':
            return self._('The Dragonlord revealed his true self!\n') + self._("Command?\n")

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
            self.transition_battle_background_image_effect(screen, player)
        # NES LoadEnemyGFX: the enemy fades in from a black shadow, twice.
        drawer.fade_in_enemy(screen, self.enemy.name)
        cmd_menu.show_line_in_battle_dialog_box(self.get_enemy_draws_near_string())
        # drop down for the hovering stats window
        cmd_menu.window_drop_down_effect(1, 2, 4, 6)
        # drop down for the battle menu
        cmd_menu.window_drop_down_effect(BATTLE_MENU_X, BATTLE_MENU_Y, BATTLE_MENU_WIDTH, BATTLE_MENU_HEIGHT)
        # The command window (CmdCmbtDat) opens with the cursor on FIGHT
        draw_translated_window(screen, COMBAT_COMMAND_LAYOUT, color, graphics.config, self._, cursor_index=0)
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
    """NES NormalAttack, shared by player and enemy hits: ((base_attack + 1) * rand(0-255) / 256 + base_attack) / 4,
    i.e. base_attack / 4 to base_attack / 2."""
    return ((base_attack + 1) * random_number // 256 + base_attack) // 4


def is_excellent_move(random_number: int) -> bool:
    """NES PlyrFight: an excellent move happens when the low 5 bits of a random byte are all 0 (1 in 32)."""
    return random_number & 0x1F == 0


def excellent_move_damage(attack_power: int, random_number: int) -> int:
    """NES PlyrFight: attack - (attack / 2 * rand(0-255)) / 256, i.e. half to all of the hero's attack power. The
    enemy's defense isn't used."""
    return attack_power - (attack_power // 2) * random_number // 256


def player_hit_damage(attack_power: int, enemy_defense: int) -> int:
    """NES PlyrCalcHitDmg: base = attack - enemy defense / 2. Below 2 (or negative) it's PlyrWeakAttack, 0 or 1
    damage at 50/50; otherwise NormalAttack."""
    base_attack = attack_power - enemy_defense // 2
    if base_attack < 2:
        return random.randint(0, 255) & 0x01
    return normal_attack_damage(base_attack, random.randint(0, 255))


def calculate_enemy_attack_damage(player, enemy):
    """The damage of an enemy's physical attack, following the NES EnCalcHitDmg routine: base = attack - the hero's
    defense / 2. When the base is below attack / 2 + 1 (or negative) it's EnWeakAttack,
    ((attack / 2 + 1) * rand(0-255) / 256 + 2) / 3, otherwise NormalAttack. The hero can't dodge (EnPhysAttack has no
    dodge check)."""
    base_attack = enemy.attack - player.defense_power // 2
    random_number = random.randint(0, 255)
    if base_attack < enemy.attack // 2 + 1:
        # Weak attack: the player's defense is high compared to the enemy's attack.
        return ((enemy.attack // 2 + 1) * random_number // 256 + 2) // 3
    return normal_attack_damage(base_attack, random_number)


def enemy_dodges(dodge: float, random_number: int) -> bool:
    """NES SetEnDmg1: the enemy dodges when (the low nibble of its magic defense) - 1 is at least a 0-63 roll, so
    a dodge value of n/64 dodges n times in 64, and 0 never does. (A sleeping enemy never gets this roll.)"""
    dodge_nibble = round(dodge * 64)
    return dodge_nibble != 0 and dodge_nibble - 1 >= random_number & 0x3F


def enemy_flees(player_strength: int, enemy_attack: int, random_number: int) -> bool:
    """NES CheckEnRun: when the hero's strength / 2 is at least the enemy's attack, the enemy runs away when the
    low 2 bits of a random byte are 0 (1 in 4)."""
    return player_strength // 2 >= enemy_attack and random_number & 0x03 == 0


def player_acts_first(player_agility: int, enemy_defense: int, enemy_random: int, player_random: int) -> bool:
    """NES CalcWhoIsNext/CalcNextOdds at the start of a fight: the hero acts first when rand(0-255) * agility is at
    least rand(0-63) * the enemy's defense; otherwise the enemy attacks before the hero is ready."""
    return player_random * player_agility >= (enemy_random & 0x3F) * enemy_defense

