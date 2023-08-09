import random

from pygame import image, display, time, mixer, Surface
from pygame.transform import scale

from src.common import BATTLE_BACKGROUND_PATH, play_sound, stairs_down_sfx, missed_sfx, missed_2_sfx, \
    excellent_move_sfx, victory_sfx, improvement_sfx, BLACK
from src.player.player_stats import levels_list


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


def battle_background_image_effect(tile_size, screen, is_dark):
    """Spiral effect to introduce battle background."""
    if not is_dark:
        battle_background_image = scale(image.load(BATTLE_BACKGROUND_PATH),
                                        (7 * tile_size, 7 * tile_size))
    else:
        black_surface = Surface((7 * tile_size, 7 * tile_size))
        black_surface.fill(BLACK)
        battle_background_image = black_surface
    spiral_tile_coordinates = ((3, 3), (3, 4), (2, 4), (2, 3), (2, 2), (3, 2), (4, 2), (4, 3), (4, 4), (4, 5),
                               (3, 5), (2, 5), (1, 5), (1, 4), (1, 3), (1, 2), (1, 1), (2, 1), (3, 1), (4, 1),
                               (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6),
                               (0, 6), (0, 5), (0, 4), (0, 3), (0, 2), (0, 1), (0, 0), (1, 0), (2, 0), (3, 0),
                               (4, 0), (5, 0), (6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (6, 5), (6, 6))
    for tile in spiral_tile_coordinates:
        screen.blit(battle_background_image.subsurface(
            (tile[0] * tile_size, tile[1] * tile_size, tile_size, tile_size)),
            ((tile[0] + 5) * tile_size, (tile[1] + 4) * tile_size))
        display.update()
        time.wait(20)


def battle_run(cmd_menu, player):
    play_sound(stairs_down_sfx)
    cmd_menu.show_line_in_dialog_box(f"{player.name} started to run away.\n", add_quotes=False,
                                     hide_arrow=True, disable_sound=True)


def calculate_enemy_attack_damage(player, enemy):
    lower_bound = (enemy.attack - player.agility / 2) // 4
    upper_bound = (enemy.attack - player.agility / 2) // 2
    return select_random_attack_damage_value(lower_bound, upper_bound)


def missed_attack(cmd_menu):
    missed_sfx_number = random.randint(1, 2)
    if missed_sfx_number == 1:
        play_sound(missed_sfx)
    else:
        play_sound(missed_2_sfx)
    cmd_menu.show_line_in_dialog_box("A miss! No damage hath been scored!\n", add_quotes=False,
                                     disable_sound=True, hide_arrow=True)


def calculate_attack_damage(cmd_menu, player, enemy):
    excellent_move_probability = random.randint(0, 31)
    if excellent_move_probability == 0 and enemy.name not in ('Dragonlord', 'Dragonlord 2'):
        play_sound(excellent_move_sfx)
        cmd_menu.show_line_in_dialog_box("Excellent move!\n", add_quotes=False, disable_sound=True)
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
        print(f'lower_bound: {lower_bound}\n'
              f'upper_bound: {upper_bound}\n'
              f'player.attack_power: {player.attack_power}\n'
              f'enemy.speed: {enemy.defense}')
        attack_damage = select_random_attack_damage_value(lower_bound, upper_bound)
    return round(attack_damage)


def battle_spell(cmd_menu, player):
    cmd_menu.show_line_in_dialog_box(f"{player.name} cannot yet use the spell.\n"
                                     f"Command?\n", add_quotes=False, hide_arrow=True, disable_sound=True)


def enemy_defeated(cmd_menu, tile_size, screen, player, music_enabled, current_map, enemy):
    enemy_defeated_string = f"Thou hast done well in defeating the {enemy.name}.\n"
    cmd_menu.show_line_in_dialog_box(enemy_defeated_string, add_quotes=False,
                                     disable_sound=True, hide_arrow=True)
    mixer.music.stop()
    play_sound(victory_sfx)
    if current_map.is_dark:
        black_surface = Surface((7 * tile_size, 7 * tile_size))
        black_surface.fill(BLACK)
        battle_background_image = black_surface
    else:
        battle_background_image = scale(image.load(BATTLE_BACKGROUND_PATH),
                                        (7 * tile_size, 7 * tile_size))
    screen.blit(battle_background_image, (5 * tile_size, 4 * tile_size))
    display.update(battle_background_image.get_rect())
    cmd_menu.show_line_in_dialog_box(f"Thy experience increases by {enemy.xp}.\n"
                                     f"Thy GOLD increases by {enemy.gold}.\n", add_quotes=False,
                                     disable_sound=True, hide_arrow=True)
    player.total_experience += enemy.xp
    player.gold += enemy.gold

    if player.level + 1 < 30 and \
            player.total_experience >= levels_list[player.level + 1]['total_exp']:
        play_sound(improvement_sfx)
        cmd_menu.show_line_in_dialog_box("Courage and wit have served thee well.\n"
                                         "Thou hast been promoted to the next level.\n", add_quotes=False,
                                         disable_sound=True)
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
            mixer.music.load(current_map.music_file_path)
            mixer.music.play(-1)

        if player.strength > old_power:
            cmd_menu.show_line_in_dialog_box(f"Thy power increases by {player.strength - old_power}.\n",
                                             add_quotes=False, disable_sound=True)
        if player.agility > old_agility:
            cmd_menu.show_line_in_dialog_box(
                f"Thy Response Speed increases by {player.agility - old_agility}.\n", add_quotes=False,
                disable_sound=True)
        if player.max_hp > old_max_hp:
            cmd_menu.show_line_in_dialog_box(
                f"Thy Maximum Hit Points increase by {player.max_hp - old_max_hp}.\n", add_quotes=False,
                disable_sound=True)
        if player.max_mp > old_max_mp:
            cmd_menu.show_line_in_dialog_box(
                f"Thy Maximum Magic Points increase by {player.max_mp - old_max_mp}.\n", add_quotes=False,
                disable_sound=True)
        if len(player.spells) > len(old_spells):
            cmd_menu.show_line_in_dialog_box("Thou hast learned a new spell.\n", add_quotes=False,
                                             disable_sound=True)


def get_enemy_draws_near_string(enemy_name):
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
    return enemy_draws_near_string
