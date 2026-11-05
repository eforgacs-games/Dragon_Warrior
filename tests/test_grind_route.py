"""AUTO-INN's routes (src/grind_route.py): the nearest inn the hero can pay for, across maps, and the way back."""
import os
from unittest import TestCase

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.config.test_config import test_config
from src.direction import Direction
from src.grind_route import TILE_NAMES, Exit, Goal, RouteMaps, find_route, first_leg, inn_goals
from src.maps import map_lookup
from src.npc_movement import step
from src.shops import INN_COSTS
from src.story_flags import StoryFlags
from tests import helpers

BY_TANTEGEL = (50, 44)


def maps_on(route):
    names = []
    for (identifier, _cell), _how in route:
        if not names or names[-1] != identifier:
            names.append(identifier)
    return names


class RouteTestCase(TestCase):
    game = None
    maps = None

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})
        cls.maps = RouteMaps(cls.game)  # kept: the maps a route reaches load once

    def go_to(self, map_name, coordinates):
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates)

    def route_to_an_inn(self, map_name, coordinates, gold=1000, story_flags=None):
        self.go_to(map_name, coordinates)
        goals = inn_goals(self.maps, gold)
        route = find_route(self.maps, (map_name, coordinates), goals, story_flags or StoryFlags())
        return route, goals


class TestTiles(TestCase):

    def test_the_layout_values(self):
        self.assertEqual(36, len(TILE_NAMES))
        self.assertEqual(('ROOF', 'WALL', 'WOOD'), TILE_NAMES[:3])
        self.assertEqual('TOWN', TILE_NAMES[12])


class TestInnGoals(RouteTestCase):

    def test_across_the_counter_facing_the_innkeeper(self):
        goals = inn_goals(self.maps, 1000)
        self.assertEqual(set(INN_COSTS), {goal.town for goal in goals})
        brecconary = [goal for goal in goals if goal.town == 'Brecconary']
        self.assertEqual([Goal(('Brecconary', (29, 18)), Direction.RIGHT.value, 'Brecconary')], brecconary)
        # the counter between the hero and the innkeeper (Brecconary's, at layout (29, 20))
        self.assertEqual('WOOD', self.maps.tile('Brecconary', step(29, 18, Direction.RIGHT.value)))

    def test_only_the_inns_the_gold_pays_for(self):
        self.assertEqual(set(), {goal.town for goal in inn_goals(self.maps, 5)})
        self.assertEqual({'Brecconary'}, {goal.town for goal in inn_goals(self.maps, 6)})
        self.assertEqual({'Brecconary', 'Kol', 'Garinham'}, {goal.town for goal in inn_goals(self.maps, 54)})


class TestRoutes(RouteTestCase):

    def test_by_tantegel_to_brecconary(self):
        route, goals = self.route_to_an_inn('Alefgard', BY_TANTEGEL)
        self.assertEqual(['Alefgard', 'Brecconary'], maps_on(route))
        self.assertEqual(('Brecconary', (29, 18)), route[-1][0])
        # stepping onto the town tile is the way in
        leg = first_leg(route, goals)
        self.assertEqual(Exit.WALK, leg.exit)
        self.assertEqual(BY_TANTEGEL, leg.cells[0])
        self.assertEqual('TOWN', self.maps.tile('Alefgard', leg.cells[-1]))

    def test_every_step_is_to_a_neighbour(self):
        route, _goals = self.route_to_an_inn('Alefgard', BY_TANTEGEL)
        for ((map_a, cell_a), how), ((map_b, cell_b), _) in zip(route, route[1:]):
            if how is None:
                self.assertEqual(map_a, map_b)
                self.assertIn(cell_b, [step(*cell_a, direction) for direction in range(4)])

    def test_the_nearest_it_can_pay_for(self):
        # In the northwest, Garinham is nearer, but 25 gold doesn't pay for a night there
        route, _goals = self.route_to_an_inn('Alefgard', (20, 20), gold=24)
        self.assertEqual('Brecconary', route[-1][0][0])
        route, _goals = self.route_to_an_inn('Alefgard', (20, 20), gold=25)
        self.assertEqual('Garinham', route[-1][0][0])

    def test_no_inn_it_can_pay_for(self):
        route, _goals = self.route_to_an_inn('Alefgard', BY_TANTEGEL, gold=5)
        self.assertIsNone(route)

    def test_out_of_a_cave_by_its_stairs(self):
        route, goals = self.route_to_an_inn('ErdricksCaveB1', (5, 5))
        self.assertEqual(['ErdricksCaveB1', 'Alefgard'], maps_on(route)[:2])
        self.assertEqual(Exit.STAIRS, first_leg(route, goals).exit)

    def test_the_golem_keeps_cantlin_closed_until_beaten(self):
        near_cantlin = (105, 85)
        route, _goals = self.route_to_an_inn('Alefgard', near_cantlin)
        self.assertNotEqual('Cantlin', route[-1][0][0])
        route, _goals = self.route_to_an_inn('Alefgard', near_cantlin, story_flags=StoryFlags(golem_defeated=True))
        self.assertEqual('Cantlin', route[-1][0][0])

    def test_back_to_where_it_started(self):
        self.go_to('Brecconary', (29, 18))
        home = Goal(('Alefgard', BY_TANTEGEL))
        route = find_route(self.maps, ('Brecconary', (29, 18)), [home], StoryFlags())
        self.assertEqual(['Brecconary', 'Alefgard'], maps_on(route))
        self.assertEqual(('Alefgard', BY_TANTEGEL), route[-1][0])
        leg = first_leg(route, [home])
        self.assertEqual(Exit.WALK, leg.exit)  # off the town's edge
        self.assertTrue(self.game.current_map.is_map_exit(*leg.cells[-1]))

    def test_blocked_cells_are_gone_round(self):
        self.go_to('Brecconary', (23, 10))
        home = Goal(('Brecconary', (23, 14)))
        straight = find_route(self.maps, ('Brecconary', (23, 10)), [home], StoryFlags())
        self.assertEqual(5, len(straight))
        around = find_route(self.maps, ('Brecconary', (23, 10)), [home], StoryFlags(), blocked=[(23, 12)])
        self.assertNotIn((('Brecconary', (23, 12)), None), around)
        self.assertGreater(len(around), 5)
