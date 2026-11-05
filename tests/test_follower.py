"""The party's second hero on the map (src/follower.py): one step behind the first."""
from unittest.mock import patch

import pygame
from pygame import K_DOWN, K_LEFT, K_RIGHT

from src.follower import COMPANION_GREEN, HERO_BLUE, IDENTIFIER, LEADER, direction_between, recolored
from src.direction import Direction
from src.party import new_hero
from tests.test_freeze_movement import FreezeTestCase


class FollowerTestCase(FreezeTestCase):

    def setUp(self):
        super().setUp()
        self.game.companion = new_hero(self.game, 'Gwen')
        self.frame()  # put on the map at the next frame
        self.hero = self.game.player
        self.companion = self.game.companion

    def cell(self, character):
        return character.row, character.column

    def walk(self, direction_key) -> None:
        """Hold a direction until the first hero has taken one step."""
        start = self.cell(self.hero)
        for _ in range(40):
            self.frame(held=(direction_key,))
            if not self.hero.is_moving and self.cell(self.hero) != start:
                self.frame()  # let go
                return
        self.fail("the hero didn't step")


class TestOnTheMap(FollowerTestCase):

    def test_starts_under_the_first_hero(self):
        self.assertEqual(self.cell(self.hero), self.cell(self.companion))
        self.assertEqual(self.hero.rect.topleft, self.companion.rect.topleft)
        self.assertEqual([IDENTIFIER, LEADER], list(self.game.current_map.characters)[-2:])  # drawn under them

    # From the throne room's start, (10, 13): down, then left along row 11 (a guard stands at (12, 13))

    def test_follows_one_step_behind(self):
        start = self.cell(self.hero)
        self.walk(K_DOWN)
        self.assertEqual(start, self.cell(self.companion))  # came out from under the first hero: still there
        first = self.cell(self.hero)
        self.walk(K_LEFT)
        self.assertEqual(first, self.cell(self.companion))
        self.assertEqual(Direction.DOWN.value, self.companion.direction_value)
        second = self.cell(self.hero)
        self.walk(K_LEFT)
        self.assertEqual(second, self.cell(self.companion))
        self.assertEqual(Direction.LEFT.value, self.companion.direction_value)

    def test_in_step_with_the_first_hero(self):
        self.walk(K_DOWN)
        for _ in range(40):
            self.frame(held=(K_LEFT,))
            if self.hero.is_moving:
                break
        for _ in range(5):
            self.frame(held=(K_LEFT,))
        hero_moved = self.hero.rect.x % self.tile_size
        self.assertNotEqual(0, hero_moved)
        self.assertTrue(self.companion.is_moving)
        self.assertEqual(Direction.DOWN.value, self.companion.direction_value)
        self.assertEqual(self.tile_size - hero_moved, self.companion.rect.y % self.tile_size or self.tile_size)

    def test_the_first_hero_can_step_back_onto_them(self):
        self.walk(K_DOWN)
        self.walk(K_LEFT)
        behind = self.cell(self.companion)
        ahead = self.cell(self.hero)
        self.walk(K_RIGHT)
        self.assertEqual(behind, self.cell(self.hero))
        self.assertEqual(ahead, self.cell(self.companion))  # they swapped places

    def test_a_bump_moves_neither(self):
        self.walk(K_DOWN)
        before = self.cell(self.companion)
        with patch.object(self.game.movement, 'is_impassable', return_value=True):
            for _ in range(40):
                self.frame(held=(K_LEFT,))
        self.assertEqual(before, self.cell(self.companion))

    def test_blocks_the_npcs(self):
        self.walk(K_DOWN)
        self.walk(K_LEFT)
        guard = self.guard
        row, column = self.cell(self.companion)
        guard.row, guard.column = row + 1, column
        guard.direction_value = Direction.UP.value
        self.assertTrue(self.game.movement.character_in_path(guard))
        self.hero.direction_value = Direction.RIGHT.value
        self.assertFalse(self.game.movement.character_in_path(self.hero))

    def test_a_new_map_puts_them_under_the_first_hero_again(self):
        self.walk(K_DOWN)
        self.walk(K_LEFT)
        self.game.current_map.characters.pop(IDENTIFIER)  # as a new map's characters are
        self.frame()
        self.assertEqual(self.cell(self.hero), self.cell(self.companion))

    def test_gone_with_no_second_hero(self):
        self.game.companion = None
        self.frame()
        self.assertNotIn(IDENTIFIER, self.game.current_map.characters)

    def test_their_sprites_follow_their_equipment(self):
        image = self.companion.image
        self.companion.weapon = 'Club'
        self.frame()
        self.assertIsNot(image, self.companion.image)


class TestTheirColors(FollowerTestCase):

    def test_green_for_blue(self):
        sheet = pygame.Surface((2, 1))
        sheet.set_at((0, 0), HERO_BLUE)
        sheet.set_at((1, 0), (252, 252, 252))
        copy = recolored(sheet, {HERO_BLUE: COMPANION_GREEN})
        self.assertEqual(COMPANION_GREEN, tuple(copy.get_at((0, 0)))[:3])
        self.assertEqual((252, 252, 252), tuple(copy.get_at((1, 0)))[:3])
        self.assertEqual(HERO_BLUE, tuple(sheet.get_at((0, 0)))[:3])

    def test_the_second_hero_has_no_blue(self):
        image = self.companion.image
        colors = {tuple(image.get_at((x, y)))[:3] for x in range(image.get_width()) for y in range(image.get_height())}
        self.assertNotIn(HERO_BLUE, colors)
        self.assertIn(COMPANION_GREEN, colors)


class TestDirectionBetween(FollowerTestCase):

    def test_neighbors(self):
        self.assertEqual(Direction.DOWN.value, direction_between((1, 1), (2, 1)))
        self.assertEqual(Direction.UP.value, direction_between((1, 1), (0, 1)))
        self.assertEqual(Direction.LEFT.value, direction_between((1, 1), (1, 0)))
        self.assertEqual(Direction.RIGHT.value, direction_between((1, 1), (1, 2)))
        self.assertIsNone(direction_between((1, 1), (3, 1)))


class TestOneHero(FreezeTestCase):

    def test_nothing_on_the_map(self):
        self.frame()
        self.assertNotIn(IDENTIFIER, self.game.current_map.characters)
        self.assertEqual([], self.game.follower.cells())
