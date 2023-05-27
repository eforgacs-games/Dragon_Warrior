from pygame import image, display
from pygame.transform import scale

from src.common import convert_to_frames_since_start_time


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