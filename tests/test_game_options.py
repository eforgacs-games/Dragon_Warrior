"""The options table (src/game_options.py): every option declared once, and everything derived from it."""
import json
from dataclasses import fields
from unittest import TestCase

from src.config.base_config import base_config
from src.game_options import ALL_OPTIONS, AUTOSAVE, GLOBAL_OPTIONS, LANGUAGE, MUSIC, OPTIONS_BY_CONFIG_KEY, \
    PER_LOG_OPTIONS, SCANLINES, VIEW, Options, apply_options, options_from_config, options_from_save, options_to_save
from src.options_overlay import OPTION_ROWS, PRESET_MODERN, PRESET_NES, preset_values
from src.settings import Settings, put_in_config
from src.soundtrack import Soundtrack


def through_a_file(entries: dict) -> dict:
    """What a save or settings file gives back: the entries written as JSON and read again."""
    return json.loads(json.dumps(entries))


class TestTheTable(TestCase):

    def test_each_option_is_declared_once(self):
        config_keys = [option.config_key for option in ALL_OPTIONS]
        names = [option.name for option in ALL_OPTIONS]
        save_keys = [option.save_key for option in PER_LOG_OPTIONS]
        for keys in (config_keys, names, save_keys):
            self.assertEqual(len(keys), len(set(keys)), keys)
        self.assertEqual(len(ALL_OPTIONS), len(OPTIONS_BY_CONFIG_KEY))

    def test_per_log_options_are_the_options_fields_in_their_order(self):
        # the save file's entries are written in this order, so it's also the order they've always been in
        self.assertEqual([option.name for option in PER_LOG_OPTIONS], [field.name for field in fields(Options)])
        self.assertTrue(all(option.per_log for option in PER_LOG_OPTIONS))

    def test_global_options_are_settings_fields(self):
        settings_fields = {field.name: field for field in fields(Settings)}
        for option in GLOBAL_OPTIONS:
            self.assertFalse(option.per_log)
            self.assertIn(option.name, settings_fields)
            self.assertEqual(option.default, settings_fields[option.name].default, option.name)

    def test_defaults(self):
        for option in PER_LOG_OPTIONS:
            self.assertEqual(option.default, getattr(Options(), option.name), option.name)
        for option in GLOBAL_OPTIONS:
            self.assertEqual(option.default, getattr(Settings(), option.name), option.name)
        # every default is one of the values, but AUTOSAVE's (a save without it keeps the config's) and LANGUAGE's (the
        # system's)
        for option in ALL_OPTIONS:
            if option not in (AUTOSAVE, LANGUAGE):
                self.assertIn(option.default, option.values, option.name)
        self.assertIsNone(AUTOSAVE.default)
        self.assertIsNone(LANGUAGE.default)

    def test_base_config_has_every_option(self):
        for option in ALL_OPTIONS:
            self.assertIn(base_config[option.config_key], option.values, option.config_key)

    def test_the_overlay_shows_every_option_once(self):
        self.assertEqual(sorted(option.config_key for option in ALL_OPTIONS),
                         sorted(row.config_key for row in OPTION_ROWS))
        for row in OPTION_ROWS:
            self.assertIs(OPTIONS_BY_CONFIG_KEY[row.config_key], row.option)
            self.assertEqual(len(row.values), len(row.value_labels), row.label)


class TestPresets(TestCase):

    def test_presets_are_the_options_preset_values(self):
        for preset, which in ((PRESET_NES, 0), (PRESET_MODERN, 1)):
            self.assertEqual({option.config_key: option.presets[which] for option in ALL_OPTIONS
                              if option.presets is not None}, preset_values(preset))

    def test_every_preset_value_is_one_of_the_values(self):
        for option in ALL_OPTIONS:
            if option.presets is not None:
                for value in option.presets:
                    self.assertIn(value, option.values, option.name)

    def test_the_nes_preset_is_the_default(self):
        # a new quest (and a fresh settings file) plays as the NES does until the player switches something on;
        # AUTOSAVE's default leaves the config's, which is the NES's OFF
        for option in ALL_OPTIONS:
            if option.presets is not None:
                expected = base_config[option.config_key] if option is AUTOSAVE else option.default
                self.assertEqual(option.presets[0], expected, option.name)

    def test_options_no_preset_changes(self):
        self.assertEqual({'TEXT_SPEED', 'LANGUAGE', 'SCANLINES', 'SCALING'},
                         {option.config_key for option in ALL_OPTIONS if option.presets is None})


class TestRoundTrips(TestCase):

    def test_every_per_log_value_round_trips_through_a_save(self):
        for option in PER_LOG_OPTIONS:
            for value in option.values:
                with self.subTest(option=option.name, value=value):
                    options = Options(**{option.name: value})
                    loaded = options_from_save(through_a_file(options_to_save(options)))
                    self.assertEqual(options, loaded)
                    self.assertIs(type(value), type(getattr(loaded, option.name)))

    def test_every_per_log_value_round_trips_through_the_config(self):
        for option in PER_LOG_OPTIONS:
            for value in option.values:
                with self.subTest(option=option.name, value=value):
                    # the config always has an AUTOSAVE, so the options it gives always have one too
                    options = Options(**{AUTOSAVE.name: False, option.name: value})
                    config = dict(base_config)
                    apply_options(config, options)
                    self.assertEqual(value, config[option.config_key])
                    self.assertEqual(options_to_save(options), options_to_save(options_from_config(config)))

    def test_a_save_without_an_option_or_with_a_bad_value_loads_its_default(self):
        for save in ({}, {option.save_key: 'not a value' for option in PER_LOG_OPTIONS}):
            self.assertEqual(Options(), options_from_save(save))

    def test_the_save_entries(self):
        # the format the adventure logs have always had: the soundtrack by name, no AUTOSAVE until it's set
        entries = options_to_save(Options(soundtrack=Soundtrack.SFC))
        self.assertEqual('SFC', entries[MUSIC.save_key])
        self.assertNotIn(AUTOSAVE.save_key, entries)
        self.assertEqual([option.save_key for option in PER_LOG_OPTIONS if option is not AUTOSAVE], list(entries))
        self.assertFalse(options_to_save(Options(autosave=False))[AUTOSAVE.save_key])

    def test_every_global_value_round_trips_through_the_settings_file(self):
        for option in GLOBAL_OPTIONS:
            for value in option.values:
                with self.subTest(option=option.name, value=value):
                    settings = Settings(**{option.name: value})
                    self.assertEqual(settings, Settings.from_json(through_a_file(settings.to_json())))

    def test_a_settings_file_with_a_bad_value_loads_the_default(self):
        self.assertEqual(Settings(), Settings.from_json({option.name: 'not a value' for option in GLOBAL_OPTIONS}))

    def test_global_settings_go_into_the_config(self):
        config = dict(base_config)
        put_in_config(Settings(language='Korean', scanlines=True, view='Wide'), config)
        self.assertEqual(('Korean', True, 'Wide'), (config['LANGUAGE'], config[SCANLINES.config_key], config['VIEW']))
        # a default leaves the config's own, and --language wins over the saved language
        config = {**base_config, 'LANGUAGE': 'English', 'VIEW': 'Wide', 'LANGUAGE_FROM_COMMAND_LINE': True}
        put_in_config(Settings(language='Korean', view=VIEW.default), config)
        self.assertEqual(('English', 'Wide'), (config['LANGUAGE'], config['VIEW']))
