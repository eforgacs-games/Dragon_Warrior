"""How much HP auto-grind keeps and which heal it casts (src/grind_safety.py). Not NES."""
import random
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from src.battle import calculate_enemy_attack_damage
from src.encounters import ENEMY_GROUPS
from src.enemy_lookup import enemy_string_lookup
from src.grind_safety import HEALMORE_WORTH, choose_heal, heal_reserve, worst_enemy_damage, worst_group_damage, \
    worst_physical_hit, worst_spell_hit
from src.spells import Spell

HEALS = (Spell.HEAL, Spell.HEALMORE)


class TestWorstHit(TestCase):

    def test_the_top_of_every_physical_roll(self):
        # The game's own formula (NES EnCalcHitDmg) at every random byte: its most is worst_physical_hit
        for name, enemy_class in enemy_string_lookup.items():
            enemy = enemy_class()
            for defense in (2, 10, 40, 75, 140):
                hero = SimpleNamespace(defense_power=defense)
                damages = set()
                for roll in range(256):
                    with patch.object(random, 'randint', return_value=roll):
                        damages.add(calculate_enemy_attack_damage(hero, enemy))
                with self.subTest(enemy=name, defense=defense):
                    self.assertEqual(max(damages), worst_physical_hit(enemy.attack, defense))

    def test_spells_and_breath_with_the_armor(self):
        self.assertEqual(45, worst_spell_hit('HURTMORE', 'Leather Armor'))
        self.assertEqual(30, worst_spell_hit('HURTMORE', 'Magic Armor'))  # a third off: 45 // 3 * 2
        self.assertEqual(10, worst_spell_hit('HURT', ''))
        self.assertEqual(6, worst_spell_hit('HURT', "Erdrick's Armor"))
        self.assertEqual(72, worst_spell_hit('FIREBREATH2', 'Magic Armor'))  # only Erdrick's Armor takes fire off
        self.assertEqual(48, worst_spell_hit('FIREBREATH2', "Erdrick's Armor"))
        self.assertEqual(0, worst_spell_hit('SLEEP', ''))
        self.assertEqual(0, worst_spell_hit('HEALMORE', ''))

    def test_an_enemy_turn_is_its_worst_action(self):
        dragon = enemy_string_lookup['Red Dragon']()  # breathes fire (23 at most) and hits hard
        self.assertEqual(max(23, worst_physical_hit(dragon.attack, 50)), worst_enemy_damage(dragon, 50, ''))
        dragonlord = enemy_string_lookup['Dragonlord 2']()  # FIREBREATH2: 72 at most, but its hits are worse
        self.assertEqual(max(72, worst_physical_hit(dragonlord.attack, 50)), worst_enemy_damage(dragonlord, 50, ''))
        self.assertEqual(max(48, worst_physical_hit(dragonlord.attack, 50)),
                         worst_enemy_damage(dragonlord, 50, "Erdrick's Armor"))
        slime = enemy_string_lookup['Slime']()
        self.assertEqual(worst_physical_hit(slime.attack, 4), worst_enemy_damage(slime, 4, ''))

    def test_a_group(self):
        names = ENEMY_GROUPS[0]
        self.assertEqual(max(worst_enemy_damage(enemy_string_lookup[name](), 4, '') for name in names),
                         worst_group_damage(names, 4, ''))
        self.assertEqual(0, worst_group_damage((), 4, ''))


class TestChooseHeal(TestCase):

    def test_heal_when_little_is_missing(self):
        self.assertEqual(Spell.HEAL, choose_heal(HEALS, 50, 70, 100, 75, 0, in_fight=False))

    def test_healmore_when_it_gives_more_for_the_mp(self):
        self.assertEqual(34, HEALMORE_WORTH)
        self.assertEqual(Spell.HEALMORE, choose_heal(HEALS, 50, 100 - HEALMORE_WORTH, 100, 75, 0, in_fight=False))
        self.assertEqual(Spell.HEAL, choose_heal(HEALS, 50, 100 - HEALMORE_WORTH + 1, 100, 75, 0, in_fight=False))

    def test_heal_if_healmore_is_too_dear(self):
        self.assertEqual(Spell.HEAL, choose_heal(HEALS, 9, 10, 100, 75, 0, in_fight=False))

    def test_none_without_the_mp_or_the_spell(self):
        self.assertIsNone(choose_heal(HEALS, 3, 10, 100, 75, 0, in_fight=False))
        self.assertIsNone(choose_heal((Spell.HURT,), 50, 10, 100, 75, 0, in_fight=False))

    def test_the_reserve_is_left_alone(self):
        self.assertEqual(4, heal_reserve(HEALS, keep_one_heal=True))
        self.assertEqual(0, heal_reserve(HEALS, keep_one_heal=False))
        self.assertEqual(0, heal_reserve((Spell.HURT,), keep_one_heal=True))
        self.assertEqual(Spell.HEAL, choose_heal(HEALS, 8, 10, 100, 75, 4, in_fight=False))
        self.assertIsNone(choose_heal(HEALS, 7, 10, 100, 75, 4, in_fight=False))
        # HEALMORE would leave less than the reserve: HEAL instead
        self.assertEqual(Spell.HEAL, choose_heal(HEALS, 12, 10, 100, 75, 4, in_fight=False))

    def test_in_a_fight_only_a_heal_that_surely_gets_out_of_danger(self):
        # HP 20 of 40, out of danger above 29: HEAL's lowest roll (10) gets to 30
        self.assertEqual(Spell.HEAL, choose_heal(HEALS, 50, 20, 40, 29, 0, in_fight=True))
        # above 30 it might not: HEALMORE, or nothing without it
        self.assertEqual(Spell.HEALMORE, choose_heal(HEALS, 50, 20, 40, 30, 0, in_fight=True))
        self.assertIsNone(choose_heal((Spell.HEAL,), 50, 20, 40, 30, 0, in_fight=True))
        # on the map it heals again after, so HEAL will do
        self.assertEqual(Spell.HEAL, choose_heal((Spell.HEAL,), 50, 20, 100, 30, 0, in_fight=False))

    def test_never_when_even_full_hp_is_in_danger(self):
        self.assertIsNone(choose_heal(HEALS, 50, 10, 60, 60, 0, in_fight=False))
