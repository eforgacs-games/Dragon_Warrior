"""
The victory and level-up fanfares, over many real battles on a real Game, with sound and music on.

On the NES both are music (InitMusicSFX with MSC_VICTORY, MSC_LEVEL_UP; Bank03 EnemyDefeated and ChkLevelUp), and the
music engine has one track, so a fanfare starts every time and is only cut off by the next music: the level-up
fanfare cuts the victory music, and otherwise WaitForMusicEnd lets it finish before the map music resumes
(ResumeMusicTbl). Beating the Dragonlord's first form, the final fight's music cuts it after 80 frames (InitFight).

They used to be played as sound effects (Sound.play_sound, any free mixer channel). Every sound effect file is about
3 seconds long, so a few quick ones (the A press, the attack, the hit, the enemy's attack) could leave no free channel,
and then the fanfare just didn't play. Here the sound effects play on the real mixer (SDL's dummy driver), with NO_WAIT
on, so they come one right after another; they now all take turns in the one SFX slot (NES DoSFX, #317), and none is
left playing on another channel. The music track is a recording stand-in for pygame.mixer.music, so the test can see
exactly when each piece of music starts and stops.
"""
import random
from os.path import basename
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.battle_controller import BattleOutcome
from src.config.test_config import test_config
from src.maps import map_lookup
from src.menu import CommandMenu
from src.music_player import MusicPlayer
from src.player.player_stats import levels_list
from src.sound import SFX_CHANNEL, Sound, sfx_channel
from tests.helpers import new_game, skip_window_frame_waits

VICTORY = '25 Dragon Quest 1 - Victory.mp3'
LEVEL_UP = '26 Dragon Quest 1 - Improvement.mp3'
FANFARES = (VICTORY, LEVEL_UP)


def setUpModule():
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_mode((800, 600))


def tearDownModule():
    pygame.quit()


class MusicTrack:
    """Stand-in for pygame.mixer.music: the one music track, recording what happens to it."""

    def __init__(self, events: list):
        self.events = events
        self.loaded: str | None = None
        self.playing: str | None = None

    def load(self, path):
        self.stop()  # loading stops what was playing
        self.loaded = basename(path)
        self.events.append(('load', self.loaded))

    def play(self, loops=0, *_args, **_kwargs):
        self.playing = self.loaded
        self.events.append(('play', self.loaded))

    def queue(self, path, *_args, **_kwargs):
        self.events.append(('queue', basename(path)))

    def stop(self):
        if self.playing:
            self.events.append(('stop', self.playing))
        self.playing = None

    def get_busy(self):
        return self.playing is not None

    def set_volume(self, *_args):
        pass

    pause = unpause = fadeout = set_volume


class TestVictoryMusic(TestCase):

    def setUp(self):
        random.seed(1985)
        skip_window_frame_waits()
        self.addCleanup(patch.stopall)
        config = {**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True, 'SOUND_ENABLED': True,
                  'MUSIC_ENABLED': True}
        self.game = new_game(config)
        self.player = self.game.player
        self.player.name = "Erdrick"
        self.events: list = []
        self.full_channel_sounds = 0  # sound effects that left a channel other than the SFX slot playing
        patch('pygame.mixer.music', MusicTrack(self.events)).start()
        # Real sounds on the real mixer, not ones another test's mocks may have left in the cache
        patch.dict('src.sound._sound_library', clear=True).start()
        # The hero always gets the first turn (no opening flee or ambush roll, #232), so the fights go as scripted
        patch('src.battle_controller.BattleController.start_fight', return_value=False).start()
        pygame.mixer.stop()
        sfx_channel()  # channel 0 kept for the text beep, as after any dialog that beeped

        def record_line(_menu, text, *_args, **_kwargs):
            self.events.append(('line', text))
        for target in ('show_line_in_dialog_box', 'show_text_in_dialog_box'):
            patch.object(CommandMenu, target, autospec=True, side_effect=record_line).start()
        patch.object(CommandMenu, 'wait_for_button', autospec=True,
                     side_effect=lambda _menu, shows_arrow: self.events.append(('button', shows_arrow))).start()

        real_play_sound, real_wait_for_music_end = Sound.play_sound, MusicPlayer.wait_for_music_end

        def play_sound(sound, path='data/sound/sfx'):
            self.assertNotIn(basename(path), FANFARES, "a fanfare was played as a sound effect")
            real_play_sound(sound, path)
            # Every sound effect takes over the one SFX slot (NES DoSFX), so they never pile up on the other channels
            if any(pygame.mixer.Channel(i).get_busy() for i in range(SFX_CHANNEL + 1, pygame.mixer.get_num_channels())):
                self.full_channel_sounds += 1

        def wait_for_music_end(music_player, config):
            self.events.append(('wait for music end',))
            real_wait_for_music_end(music_player, config)
        patch.object(Sound, 'play_sound', autospec=True, side_effect=play_sound).start()
        patch.object(MusicPlayer, 'wait_for_music_end', autospec=True, side_effect=wait_for_music_end).start()
        patch('src.battle_controller.time').start()
        patch('src.waiting.time.wait').start()  # the battle-start spiral (wait_frames)
        self.addCleanup(patch.stopall)
        self.addCleanup(pygame.mixer.stop)
        self.how = 'attack'

    # Battle-menu stand-in: the A press, then the real attack or spell, then the real enemy turn

    def take_turn(self, _run_away, current_battle):
        controller = self.game.battle_ctrl
        controller.sound.play_sound(self.game.directories.menu_button_sfx)
        if self.how == 'attack':
            controller.hero_attack(current_battle)
        elif self.how == 'flee':
            pass  # the hero does nothing that could hurt the enemy
        elif self.how == 'hurt':
            controller.sound.play_sound(self.game.directories.spell_sfx)
            self.game.cmd_menu.hurt()
        elif self.how == 'hurtmore':
            controller.sound.play_sound(self.game.directories.spell_sfx)
            self.game.cmd_menu.hurtmore()
        if current_battle.enemy.hp <= 0:
            return False
        return controller.enemy_move(current_battle)

    def fight(self, enemy_name, how='attack', level_up=False):
        self.how = how
        self.player.current_hp = self.player.max_hp = 255
        self.player.current_mp = 255
        # NES CheckEnRun: an enemy runs 1 time in 4 from a hero with twice its attack in strength
        self.player.strength = 255 if how == 'flee' else 1
        self.player.attack_power = random.choice([30, 60, 255])
        if level_up:
            self.player.total_experience = levels_list[self.player.level + 1]['total_exp'] - 1
        else:
            self.player.total_experience = levels_list[self.player.level]['total_exp']
        start = len(self.events)
        with patch.object(self.game.battle_ctrl, 'handle_battle_prompts', side_effect=self.take_turn):
            outcome = self.game.battle_ctrl.start_scripted_battle(enemy_name)
        return outcome, self.events[start:]

    # What happened to the music

    def music_after(self, events, index):
        """The music events after events[index], leaving out the text and the waits for a button."""
        return [event for event in events[index + 1:] if event[0] not in ('line', 'button')]

    def assert_fanfares_like_the_nes(self, events, levelled_up, enemy_name):
        map_music = basename(self.game.current_map.music_file_path)
        self.assertEqual(events.count(('play', VICTORY)), 1, events)
        victory = events.index(('play', VICTORY))
        self.assertEqual(events[victory - 1], ('load', VICTORY))
        done_well = [i for i, event in enumerate(events) if event[0] == 'line' and 'done well' in event[1]]
        self.assertEqual(len(done_well), 1)
        self.assertLess(done_well[0], victory)  # right after the done-well line
        after_victory = self.music_after(events, victory)
        if levelled_up:
            # DoLevelUp: MSC_LEVEL_UP takes the victory music's place, WaitForMusicEnd, then ResumeMusicTbl, all
            # before "Courage and wit have served thee well."
            self.assertEqual(after_victory[:6], [('stop', VICTORY), ('load', LEVEL_UP), ('play', LEVEL_UP),
                                                 ('wait for music end',), ('stop', LEVEL_UP),
                                                 ('load', map_music)], events)
            promoted = next(i for i, event in enumerate(events) if event[0] == 'line' and 'promoted' in event[1])
            self.assertLess(events.index(('load', map_music)), promoted)
            # TB16E1's leading WAIT: the arrow, after the music and before "Courage and wit"
            self.assertLess(events.index(('load', map_music)), events.index(('button', True)))
            self.assertLess(events.index(('button', True)), promoted)
            self.assertNotIn(('button', False), events)
        else:
            # WaitForMusicEnd, then ResumeMusicTbl: nothing touches the victory music before it has ended
            self.assertEqual(after_victory[:3], [('wait for music end',), ('stop', VICTORY), ('load', map_music)],
                             events)
            self.assertNotIn(('play', LEVEL_UP), events)
            # The gold line has no WAIT, so it prints while the music plays; ExitFight's button wait comes after
            gold = next(i for i, event in enumerate(events) if event[0] == 'line' and 'GOLD' in event[1])
            self.assertLess(gold, events.index(('wait for music end',)))
            self.assertEqual(events[-1], ('button', False), events)
        # the map music starts once, after the fanfares, and keeps playing
        self.assertEqual(events.count(('load', map_music)), 1, events)
        self.assertEqual(self.music_after(events, -1 - len(events))[-1], ('play', map_music), f"{enemy_name}: {events}")

    # The tests

    def test_every_win_starts_the_victory_music_and_lets_it_finish(self):
        self.game.change_map(map_lookup['Alefgard'](self.game.config), destination_coordinates=(50, 50))
        wins = 0
        for battle_number in range(40):
            enemy_name = random.choice(['Slime', 'Red Slime', 'Drakee', 'Ghost', 'Magician', 'Scorpion', 'Druin',
                                        'Golem', 'Skeleton', 'Wolf'])
            how = random.choice(['attack', 'attack', 'hurt', 'hurtmore'])
            level_up = battle_number % 3 == 0 and self.player.level < 29
            with self.subTest(battle=battle_number, enemy=enemy_name, how=how, level_up=level_up):
                level = self.player.level
                outcome, events = self.fight(enemy_name, how, level_up)
                self.assertEqual(outcome, BattleOutcome.VICTORY)
                self.assertEqual(self.player.level, level + level_up)
                self.assert_fanfares_like_the_nes(events, level_up, enemy_name)
                wins += 1
        self.assertEqual(wins, 40)
        # The sound effects used to fill the mixer channels at times, which left no channel for the fanfares when they
        # were sound effects too (#300), and dropped sound effects (#317); now they only ever use the SFX slot
        self.assertEqual(self.full_channel_sounds, 0)

    def test_a_fleeing_enemy_gives_no_victory_music(self):
        self.game.change_map(map_lookup['Alefgard'](self.game.config), destination_coordinates=(50, 50))
        for battle_number in range(5):
            with self.subTest(battle=battle_number):
                outcome, events = self.fight('Slime', 'flee')
                self.assertEqual(outcome, BattleOutcome.ESCAPED)
                self.assertNotIn(('load', VICTORY), events)
                self.assertEqual(self.music_after(events, -1 - len(events))[-1],
                                 ('play', basename(self.game.current_map.music_file_path)))
        # and the next win still gets its fanfare
        _, events = self.fight('Slime', 'attack')
        self.assert_fanfares_like_the_nes(events, False, 'Slime')

    def test_dragonlord_first_form_victory_music_runs_until_the_final_fight(self):
        self.game.change_map(map_lookup['CharlockB8'](self.game.config), destination_coordinates=(13, 17))

        def take_turn(_run_away, current_battle):
            current_battle.enemy.hp = 0
            return False
        with patch.object(self.game.battle_ctrl, 'handle_battle_prompts', side_effect=take_turn), \
                patch.object(self.game.ending, 'final_boss_defeated') as final_boss_defeated:
            outcome = self.game.battle_ctrl.start_scripted_battle('Dragonlord')
        self.assertEqual(outcome, BattleOutcome.VICTORY)
        final_boss_defeated.assert_called_once()
        end_boss = basename(self.game.directories.end_boss_music)
        first_victory = self.events.index(('play', VICTORY))
        # NES EnemyDefeated: MSC_VICTORY, 80 frames, then InitFight with EN_DRAGONLORD2 starts MSC_END_BOSS
        self.assertEqual(self.music_after(self.events, first_victory)[:3],
                         [('stop', VICTORY), ('load', end_boss), ('play', end_boss)])
        # the final form's defeat starts it again (NotDL1Defeated then hands over to the ending)
        self.assertEqual(self.events.count(('play', VICTORY)), 2)

    def test_back_to_back_fights_after_the_inn(self):
        self.game.change_map(map_lookup['Alefgard'](self.game.config), destination_coordinates=(50, 50))
        self.game.music_player.play_until_end(self.game.directories.inn_music, self.game.game_state.config)
        self.game.music_player.load_and_play_music(self.game.current_map.music_file_path)
        for battle_number, level_up in enumerate((True, False, True, True, False, False)):
            with self.subTest(battle=battle_number, level_up=level_up):
                _, events = self.fight('Slime', 'attack', level_up)
                self.assert_fanfares_like_the_nes(events, level_up, 'Slime')

    def test_item_tunes_are_music_too(self):
        # NES ChkHarp, ChkFryFlt, ChkBelt (field) and ChkUseHarp, ChkUseFlute, ChkUseBelt (fight): the tune takes the
        # music's place, WaitForMusicEnd, then the map's music (ResumeMusicTbl) or the fight music again
        directories = self.game.directories
        harp, flute, cursed = (basename(path) for path in (directories.harp_music, directories.flute_music,
                                                           directories.cursed_music))
        self.game.change_map(map_lookup['Brecconary'](self.game.config), destination_coordinates=(23, 10))
        map_music = basename(self.game.current_map.music_file_path)
        fight_music = basename(directories.battle_music)
        regular_fight_music = basename(directories.regular_fight_music)
        cmd_menu = self.game.cmd_menu
        for use, tune in ((cmd_menu.silver_harp, harp), (cmd_menu.fairy_flute, flute), (cmd_menu.cursed_belt, cursed)):
            with self.subTest(tune=tune):
                start = len(self.events)
                use()
                self.assertEqual(self.music_after(self.events, start - 1),
                                 [('stop', map_music), ('load', tune), ('play', tune), ('wait for music end',),
                                  ('stop', tune),
                                  ('load', map_music), ('play', map_music)])

        def use_in_fight(_run_away, current_battle):
            start = len(self.events)
            for use in (cmd_menu.silver_harp_in_battle, cmd_menu.fairy_flute, cmd_menu.cursed_belt):
                use()
            # ChkUseHarp, ChkUseFlute and ChkUseBelt restart the fight music with MSC_REG_FGHT: the fight loop, without
            # the opening the fight started with (MSC_ENTR_FGHT)
            self.assertEqual(self.music_after(self.events, start - 1), [
                ('stop', fight_music), ('load', harp), ('play', harp), ('wait for music end',), ('stop', harp),
                ('load', regular_fight_music), ('play', regular_fight_music),
                ('stop', regular_fight_music), ('load', flute), ('play', flute), ('wait for music end',),
                ('stop', flute), ('load', regular_fight_music), ('play', regular_fight_music),
                ('stop', regular_fight_music), ('load', cursed), ('play', cursed), ('wait for music end',),
                ('stop', cursed), ('load', regular_fight_music), ('play', regular_fight_music)])
            current_battle.enemy.hp = 0
            return False
        with patch.object(self.game.battle_ctrl, 'handle_battle_prompts', side_effect=use_in_fight):
            self.assertEqual(self.game.battle_ctrl.start_scripted_battle('Slime'), BattleOutcome.VICTORY)


class TestMusicOff(TestCase):
    """MUSIC_ENABLED off: MusicPlayer is the only thing that touches pygame's music, and it leaves it alone. The maps,
    the fights, the fanfares and the item tunes are all silent."""

    def setUp(self):
        config = {**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True, 'MUSIC_ENABLED': False}
        self.game = new_game(config)
        self.music = patch('pygame.mixer.music').start()
        patch('src.battle_controller.BattleController.start_fight', return_value=False).start()
        for target in ('show_line_in_dialog_box', 'show_text_in_dialog_box', 'wait_for_button'):
            patch.object(CommandMenu, target).start()
        patch('src.battle_controller.time').start()
        patch('src.waiting.time.wait').start()
        self.addCleanup(patch.stopall)

    def win(self, enemy_name, level_up):
        player = self.game.player
        player.total_experience = levels_list[player.level + 1]['total_exp'] - 1 if level_up else 0

        def take_turn(_run_away, current_battle):
            current_battle.enemy.hp = 0
            return False
        with patch.object(self.game.battle_ctrl, 'handle_battle_prompts', side_effect=take_turn):
            return self.game.battle_ctrl.start_scripted_battle(enemy_name)

    def test_nothing_touches_pygame_music(self):
        self.game.change_map(map_lookup['Alefgard'](self.game.config), destination_coordinates=(50, 50))
        self.assertEqual(self.win('Slime', level_up=True), BattleOutcome.VICTORY)
        self.assertEqual(self.win('Slime', level_up=False), BattleOutcome.VICTORY)
        cmd_menu = self.game.cmd_menu
        for use in (cmd_menu.silver_harp, cmd_menu.fairy_flute, cmd_menu.cursed_belt):
            use()
        self.game.change_map(map_lookup['Brecconary'](self.game.config), destination_coordinates=(23, 10))
        self.assertEqual(self.music.method_calls, [])
