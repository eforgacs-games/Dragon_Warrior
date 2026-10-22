from unittest import TestCase

from src.config.base_config import base_config, language_from_locale


class TestLanguageFromLocale(TestCase):
    def test_locale_codes_map_to_the_language_names_the_game_checks(self):
        # The game compares config['LANGUAGE'] with 'English' and 'Korean'. A raw locale code such as 'en' matched
        # neither, so English-only text ("A Slime draws near!", the level-up message) was never shown.
        for locale_name, language in (('en_US', 'English'), ('en_GB', 'English'), ('ko_KR', 'Korean'),
                                      ('ko', 'Korean'), ('de_DE', 'English'), ('C', 'English'), (None, 'English'),
                                      ('', 'English')):
            with self.subTest(locale_name=locale_name):
                self.assertEqual(language_from_locale(locale_name), language)

    def test_base_config_language_is_a_language_name(self):
        self.assertIn(base_config['LANGUAGE'], ('English', 'Korean'))
