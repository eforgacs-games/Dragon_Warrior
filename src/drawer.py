from pygame import image, display
from pygame.transform import scale

from src.common import convert_to_frames_since_start_time
from src.config import TILE_SIZE


class Drawer:

    @staticmethod
    def alternate_blink(image_1, image_2, right_arrow_start, screen):
        while convert_to_frames_since_start_time(right_arrow_start) <= 16:
            selected_image = scale(image.load(image_1), (screen.get_width(), screen.get_height()))
            screen.blit(selected_image, (0, 0))
            # draw_text(">BEGIN A NEW QUEST", screen.get_width() / 2, screen.get_height() / 3, self.screen)
            display.update(selected_image.get_rect())
        while 16 < convert_to_frames_since_start_time(right_arrow_start) <= 32:
            unselected_image = scale(image.load(image_2), (screen.get_width(), screen.get_height()))
            screen.blit(unselected_image, (0, 0))
            # draw_text(" BEGIN A NEW QUEST", screen.get_width() / 2, screen.get_height() / 3, self.screen)
            display.update(unselected_image.get_rect())

    @staticmethod
    def position_and_draw_enemy_image(screen, enemy_image, enemy_name):
        if enemy_name in ('Slime', 'Red Slime', 'Metal Slime'):
            screen.blit(enemy_image, (8 * TILE_SIZE, 7 * TILE_SIZE))
        elif enemy_name in ('Drakee', 'Magidrakee', 'Drakeema'):
            # might need work
            screen.blit(enemy_image, (7.75 * TILE_SIZE, 6.25 * TILE_SIZE))
        elif enemy_name in ('Ghost', 'Poltergeist', 'Specter'):
            screen.blit(enemy_image, (7.8 * TILE_SIZE, 5.9 * TILE_SIZE))
        elif enemy_name in ('Magician', 'Warlock', 'Wizard'):
            screen.blit(enemy_image, (7.3 * TILE_SIZE, 6 * TILE_SIZE))
        elif enemy_name in ('Scorpion', 'Metal Scorpion', 'Rogue Scorpion'):
            screen.blit(enemy_image, (7.4 * TILE_SIZE, 6.5 * TILE_SIZE))
        elif enemy_name in ('Druin', 'Druinlord'):
            screen.blit(enemy_image, (8 * TILE_SIZE, 6.5 * TILE_SIZE))
        elif enemy_name in ('Droll', 'Drollmagi'):
            screen.blit(enemy_image, (7.5 * TILE_SIZE, 6 * TILE_SIZE))
        elif enemy_name in ('Skeleton', 'Wraith', 'Wraith Knight', 'Demon Knight'):
            screen.blit(enemy_image, (7.46 * TILE_SIZE, 5.74 * TILE_SIZE))
        elif enemy_name in ('Wolf', 'Wolflord', 'Werewolf'):
            screen.blit(enemy_image, (7.11 * TILE_SIZE, 5.95 * TILE_SIZE))
        elif enemy_name in ('Goldman', 'Golem', 'Stoneman'):
            screen.blit(enemy_image, (7.1 * TILE_SIZE, 5.6 * TILE_SIZE))
        elif enemy_name in ('Wyvern', 'Magiwyvern', 'Starwyvern'):
            screen.blit(enemy_image, (7.25 * TILE_SIZE, 5.5 * TILE_SIZE))
        elif enemy_name in ('Knight', 'Axe Knight', 'Armored Knight'):
            screen.blit(enemy_image, (7.1 * TILE_SIZE, 5.75 * TILE_SIZE))
        elif enemy_name in ('Green Dragon', 'Blue Dragon', 'Red Dragon'):
            screen.blit(enemy_image, (6.5 * TILE_SIZE, 6.25 * TILE_SIZE))
        elif enemy_name == 'Dragonlord':
            screen.blit(enemy_image, (7.5 * TILE_SIZE, 6 * TILE_SIZE))
        elif enemy_name == 'Dragonlord 2':
            # need to have this blit over the text box on the bottom
            screen.blit(enemy_image, (5.1 * TILE_SIZE, 4 * TILE_SIZE))
        else:
            screen.blit(enemy_image, (7.544 * TILE_SIZE, 6.1414 * TILE_SIZE))


