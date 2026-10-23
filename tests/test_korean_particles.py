import string
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from data.text.locales import catalog_tools
from src.common import set_gettext_language
from src.korean_particles import PARTICLES, KoreanText, format_with_particles, get_postposition, has_final_consonant, \
    particle


class TestParticle(TestCase):

    def test_hangul_with_a_batchim(self):
        self.assertEqual(particle('검객', '은/는'), '은')
        self.assertEqual(particle('골렘', '이/가'), '이')
        self.assertEqual(particle('용왕', '을/를'), '을')
        self.assertEqual(particle('용왕', '와/과'), '과')
        self.assertEqual(particle('용왕', '(으)로'), '으로')

    def test_hangul_without_a_batchim(self):
        self.assertEqual(particle('용사', '은/는'), '는')
        self.assertEqual(particle('슬라임 베스', '이/가'), '가')
        self.assertEqual(particle('약초', '을/를'), '를')
        self.assertEqual(particle('약초', '와/과'), '와')
        self.assertEqual(particle('약초', '(으)로'), '로')

    def test_rieul_takes_ro(self):
        # ㄹ is a batchim for every particle except (으)로, which takes 로 after it
        self.assertEqual(particle('횃불', '(으)로'), '로')
        self.assertEqual(particle('횃불', '을/를'), '을')
        self.assertEqual(particle('횃불', '은/는'), '은')

    def test_latin_names(self):
        self.assertEqual(particle('Edward', '은/는'), '는')  # 에드워드
        self.assertEqual(particle('Arthur', '이/가'), '가')  # 아서
        self.assertEqual(particle('Mark', '을/를'), '를')  # 마크
        self.assertEqual(particle('Adam', '은/는'), '은')  # 아담
        self.assertEqual(particle('ERDRICK', '은/는'), '는')  # 에드릭; case doesn't matter
        self.assertEqual(particle('Ryan', '이/가'), '이')  # 라이언
        self.assertEqual(particle('Sterling', '을/를'), '을')  # 스털링
        self.assertEqual(particle('Michael', '은/는'), '은')  # 마이클
        self.assertEqual(particle('Michael', '(으)로'), '로')

    def test_numbers_are_read_in_sino_korean(self):
        self.assertEqual(particle('1', '이/가'), '이')  # 일
        self.assertEqual(particle('2', '이/가'), '가')  # 이
        self.assertEqual(particle('3', '을/를'), '을')  # 삼
        self.assertEqual(particle('5', '을/를'), '를')  # 오
        self.assertEqual(particle('7', '(으)로'), '로')  # 칠
        self.assertEqual(particle('6', '(으)로'), '으로')  # 육
        self.assertEqual(particle('10', '을/를'), '을')  # 십
        self.assertEqual(particle('100', '을/를'), '을')  # 백
        self.assertEqual(particle('12', '을/를'), '를')  # 십이
        self.assertEqual(particle('0', '이/가'), '이')  # 영

    def test_unknown_endings_keep_the_combined_form(self):
        self.assertEqual(particle('', '을/를'), '을/를')
        self.assertEqual(particle('?!', '을/를'), '을/를')

    def test_has_final_consonant_and_get_postposition(self):
        self.assertTrue(has_final_consonant('갈'))
        self.assertFalse(has_final_consonant('가'))
        self.assertEqual(get_postposition('갈', '을', '를'), '을')
        self.assertEqual(get_postposition('가', '을', '를'), '를')


class TestFormatWithParticles(TestCase):

    def test_particles_after_placeholders_agree(self):
        self.assertEqual(format_with_particles('{}은/는 {}을/를 발견했다!', ('검객', '약초')), '검객은 약초를 발견했다!')
        self.assertEqual(format_with_particles('{}은/는 {}을/를 발견했다!', ('용사', '횃불')), '용사는 횃불을 발견했다!')

    def test_named_and_numbered_fields(self):
        self.assertEqual(format_with_particles('{1}이/가 {0}', ('a', '골렘')), '골렘이 a')
        self.assertEqual(format_with_particles('{name}이/가 {x:>3}', (), {'name': '슬라임', 'x': 5}), '슬라임이   5')

    def test_text_without_placeholders_or_particles_is_unchanged(self):
        self.assertEqual(format_with_particles('은/는 그대로'), '은/는 그대로')
        self.assertEqual(format_with_particles('{}님', ('Edward',)), 'Edward님')
        self.assertEqual(format_with_particles('{{}}은/는', ()), '{}은/는')

    def test_korean_text_format(self):
        self.assertEqual(KoreanText('{}이/가 몸을 조이고 있다.').format('저주받은 벨트'), '저주받은 벨트가 몸을 조이고 있다.')
        self.assertEqual(KoreanText('{}을/를 버렸다.'), '{}을/를 버렸다.')


class TestKoreanCatalogParticles(TestCase):
    """Lines from the Korean catalog with a name, item, spell or enemy put in front of a particle."""

    @classmethod
    def setUpClass(cls):
        cls._ = staticmethod(set_gettext_language('Korean'))

    def test_placeholders_are_followed_by_the_combined_particle(self):
        # "{}를" is only right for some words; "{}을/를" lets format_with_particles pick
        single_forms = sorted({form for forms in PARTICLES.values() for form in forms}, key=len, reverse=True)
        problems = []
        for msgid, msgstr in catalog_tools.read_po().items():
            for literal, _, _, _ in list(string.Formatter().parse(msgstr))[1:]:
                if not literal.startswith(tuple(PARTICLES)) and literal.startswith(tuple(single_forms)):
                    problems.append(f"{msgid!r} -> {msgstr!r}")
        self.assertFalse(problems, '\n'.join(problems))

    def test_treasure_chest(self):
        _ = self._
        fortune = _("Fortune smiles upon thee, {}.\nThou hast found the {}.")
        self.assertEqual(fortune.format('Edward', _('Herb')), "Edward는 보물 상자를 열었다. 놀랍게도! 약초를 획득했다!")
        self.assertEqual(fortune.format('검객', _('Torch')), "검객은 보물 상자를 열었다. 놀랍게도! 횃불을 획득했다!")

    def test_spells(self):
        _ = self._
        self.assertEqual(_("{} chanted the spell of {}.").format('Edward', _('HURT')), "Edward는 기라를 외쳤다!")
        self.assertEqual(_("{} chants the spell of {}.").format(_('Golem'), _('SLEEP')), "골렘은 라리호를 외쳤다!")
        self.assertEqual(_("{} cannot yet use the spell.").format('Adam'), "Adam은 아직 주문을 사용할 수 없다.")

    def test_items_and_enemies(self):
        _ = self._
        self.assertEqual(_("{} started to run away.\n").format(_('Slime')), "슬라임은 도망쳤다!\n")
        self.assertEqual(_("{} started to run away.\n").format(_('Ghost')), "고스트는 도망쳤다!\n")
        self.assertEqual(_("The {} is squeezing thy body.").format(_('Cursed Belt')), "저주받은 벨트가 몸을 조이고 있다.")
        self.assertEqual(_("Thou hast dropped thy {}.").format(_('Magic Key')), "열쇠를 버렸다.")
        self.assertEqual(_("{} discovers the {}.").format('Michael', _('Fairy Water')), "Michael은 요정의 물을 발견했다!")

    def test_level_up_line(self):
        from src.battle import Battle
        battle = Battle.__new__(Battle)
        battle.config = {'LANGUAGE': 'Korean'}
        cmd_menu = Mock()
        battle.display_level_up_message(cmd_menu, SimpleNamespace(level=1, name='Edward'), 2)
        battle.display_level_up_message(cmd_menu, SimpleNamespace(level=1, name='검객'), 2)
        self.assertEqual([c.args[0] for c in cmd_menu.show_line_in_dialog_box.call_args_list],
                         ["Edward는 2레벨로 올랐다!", "검객은 2레벨로 올랐다!"])
