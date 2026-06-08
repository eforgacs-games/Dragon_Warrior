# From https://gamefaqs.gamespot.com/nes/563408-dragon-warrior/faqs/61640
# ~Spells~
#
# NOTE: Enemy HURT and HEAL classes of spells have different ranges than the
# hero's spells.
#
#     HURT does  3 - 10 damage
# HURTMORE does 30 - 45 damage
#
# Both Magic Armor and Erdrick's Armor will reduce HURT spells by 1/3.  So:
#
#     HURT does  2 -  6 damage vs. Erdrick's and Magic Armor
# HURTMORE does 20 - 30 damage vs. Erdrick's and Magic Armor
#
#
# SLEEP always puts you to sleep, and there is no resisting it.  Waking up from
# sleep is a 50/50 chance, but because of the limitations of the game programming
# it's not possible for it to last for more than 6 turns.
#
#
# STOPSPELL has a 50/50 chance of working against you.  If you have Erdrick's
# Armor it has no chance of working.
#
#
#     HEAL recovers 20 - 27 HP
# HEALMORE recovers 85 - 100 HP

from src.spells import Spell

enemy_spell_lookup = {
    Spell.HURT: (3, 10),
    Spell.HURTMORE: (30, 45),
    Spell.SLEEP: (0, 0),
    Spell.STOPSPELL: (0, 0),
    Spell.HEAL: (20, 27),
    Spell.HEALMORE: (85, 100),
    Spell.FIREBREATH: (16, 23),
    Spell.FIREBREATH2: (65, 72),
}
