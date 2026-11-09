"""How much HP auto-grind (src/auto_grind.py) keeps, and which healing spell it casts to keep it. Not NES.

The GRIND STOP option's DANGER setting works the line out from what the monsters can do, with the NES's own numbers:

- an enemy's worst hit (``worst_enemy_damage``) is the most one enemy turn can take: its physical attack at the top of
  its random roll (NES EnCalcHitDmg: NormalAttack, or EnWeakAttack against a hero whose defense is high), or its worst
  damaging spell or breath (EnCastHurt, EnCastHurtmore, EnCastFire1 and 2: src/enemy_spells.py), less what the hero's
  armor takes off (Magic Armor and Erdrick's Armor take a third off HURT and HURTMORE, Erdrick's Armor off the fire);
- in a fight, HP is in danger when the enemy's next turn could end it: at or below that enemy's worst hit;
- on the map, when the next fight could: at or below twice the worst hit of any enemy that fights here (one hit
  before the hero is ready, NES CalcWhoIsNext, and his first turn must still be out of danger).

SLEEP isn't counted: a sleeping hero stops auto-grind at the start of his turn (AutoGrind.player_turn_starts).

AUTO-HEAL (``choose_heal``) casts HEAL (10-17 HP for 4 MP, NES DoHeal) or HEALMORE (85-100 HP for 10 MP, DoHealmore),
whichever gives more HP for the MP: HEALMORE once at least HEALMORE_WORTH HP are missing, as HEAL gives 13.5 HP for
4 MP on average. It never spends the MP kept in reserve. In a fight a heal must take HP out of danger even at its lowest roll,
or it would only give the enemy another turn; on the map there is no hurry, and it heals again until HP is out of danger.
"""
from collections.abc import Iterable

from src.enemy import Enemy
from src.enemy_lookup import enemy_string_lookup
from src.enemy_spells import enemy_spell_lookup
from src.spells import Spell

# The hero's healing spells: (MP cost, lowest HP, highest HP), as CommandMenu.heal and healmore cast them
HERO_HEALS: dict[Spell, tuple[int, int, int]] = {
    Spell.HEAL: (4, 10, 17),
    Spell.HEALMORE: (10, 85, 100),
}
_HEAL_MP, _HEAL_LOWEST, _HEAL_HIGHEST = HERO_HEALS[Spell.HEAL]
# The missing HP from which HEALMORE gives more HP for its MP than HEAL's average: 13.5 HP / 4 MP * 10 MP = 33.75
HEALMORE_WORTH = -(-(_HEAL_LOWEST + _HEAL_HIGHEST) * HERO_HEALS[Spell.HEALMORE][0] // (2 * _HEAL_MP))
# NES: the armor that takes a third off the enemy's HURT and HURTMORE, and off its fire (BattleController.enemy_move)
HURT_ARMOR = ("Magic Armor", "Erdrick's Armor")
FIRE_ARMOR = ("Erdrick's Armor",)


def worst_physical_hit(enemy_attack: int, hero_defense: int) -> int:
    """The most an enemy's attack can do: NES EnCalcHitDmg (src/battle.py calculate_enemy_attack_damage) with the top
    random roll, 255."""
    base_attack = enemy_attack - hero_defense // 2
    if base_attack < enemy_attack // 2 + 1:
        return ((enemy_attack // 2 + 1) * 255 // 256 + 2) // 3  # EnWeakAttack
    return ((base_attack + 1) * 255 // 256 + base_attack) // 4  # NormalAttack


def worst_spell_hit(spell: str, armor: str) -> int:
    """The most an enemy's spell or breath can take off the hero (0 for the ones that do no damage)."""
    if spell not in (Spell.HURT, Spell.HURTMORE, Spell.FIREBREATH, Spell.FIREBREATH2):
        return 0
    damage = enemy_spell_lookup[Spell(spell)][1]
    reducing_armor = HURT_ARMOR if spell in (Spell.HURT, Spell.HURTMORE) else FIRE_ARMOR
    return damage // 3 * 2 if armor in reducing_armor else damage


def worst_enemy_damage(enemy: Enemy, hero_defense: int, armor: str) -> int:
    """The most one turn of this enemy can take off the hero (see the module docstring)."""
    return max(worst_physical_hit(enemy.attack, hero_defense),
               *(worst_spell_hit(spell, armor) for spell in enemy.spells or ()), 0)


def worst_group_damage(enemy_names: Iterable[str], hero_defense: int, armor: str) -> int:
    """The worst hit of any of these enemies."""
    return max((worst_enemy_damage(enemy_string_lookup[name](), hero_defense, armor) for name in enemy_names),
               default=0)


def choose_heal(spells: Iterable[str], mp: int, hp: int, max_hp: int, line: int, reserve_mp: int,
                in_fight: bool) -> Spell | None:
    """The healing spell to cast with HP at or below ``line`` (see the module docstring), or None if there is none:
    none known, not enough MP above ``reserve_mp``, HP that no heal could ever take above the line, or, in a fight, no
    heal that surely takes it there."""
    if max_hp <= line:
        return None
    known = [spell for spell in (Spell.HEAL, Spell.HEALMORE) if spell in spells]
    affordable = [spell for spell in known if mp - HERO_HEALS[spell][0] >= reserve_mp]
    if max_hp - hp >= HEALMORE_WORTH:
        affordable.reverse()  # HEALMORE first
    for spell in affordable:
        lowest = min(HERO_HEALS[spell][1], max_hp - hp)
        if not in_fight or hp + lowest > line:
            return spell
    return None


def heal_reserve(spells: Iterable[str], keep_one_heal: bool) -> int:
    """The MP AUTO-HEAL leaves alone: one HEAL's worth with KEEP 1 HEAL, if the hero knows HEAL."""
    return _HEAL_MP if keep_one_heal and Spell.HEAL in spells else 0
