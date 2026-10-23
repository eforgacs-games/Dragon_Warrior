"""
The music and sound effects checked against the NES (nmikstas disassembly), issues #236 and #317.

Each test names the NES routine it follows. The music played on each map is ResumeMusicTbl (Bank00, LB1AE), which
MapChngNoSound/MapChngWithSound (LB10E) also use to start a map's music.
"""
import unittest
from unittest.mock import MagicMock, call, patch

import pygame

from src.battle import Battle
from src.config.test_config import test_config
from src.directories import Directories
from src.maps import map_lookup
from src.music_player import MusicPlayer
from src.sound import SFX_CHANNEL, Sound
from src.waiting import NES_FPS
from tests.helpers import new_game
from tests.mock_map import MockMap


def setUpModule():
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_mode((800, 600))


def tearDownModule():
    pygame.quit()


# NES ResumeMusicTbl, by map: the music each map plays (the Directories attribute holding it)
RESUME_MUSIC_TBL = {
    'Alefgard': 'overworld_music',  # MSC_OUTDOOR
    'CharlockB1': 'dungeon_floor_1_music',  # dragonlord castle, ground floor: MSC_DUNGEON1
    'Hauksness': 'dungeon_floor_4_music',  # MSC_DUNGEON4
    'TantegelCourtyard': 'tantegel_castle_courtyard_music',  # MSC_TANTAGEL2
    'TantegelThroneRoom': 'tantegel_castle_throne_room_music',  # MSC_THRN_ROOM
    'CharlockB8': 'dungeon_floor_8_music',  # dragonlord castle, bottom floor: MSC_DUNGEON8
    'Kol': 'village_music',  # MSC_VILLAGE
    'Brecconary': 'village_music',
    'Garinham': 'village_music',
    'Cantlin': 'village_music',
    'Rimuldar': 'village_music',
    'TantegelCellar': 'tantegel_castle_courtyard_music',  # Tantagel castle, sublevel: MSC_TANTAGEL2
    'StaffOfRainCave': 'tantegel_castle_courtyard_music',  # MSC_TANTAGEL2
    'MagicTemple': 'tantegel_castle_courtyard_music',  # rainbow drop cave: MSC_TANTAGEL2
    'CharlockB2': 'dungeon_floor_2_music',  # sublevel 1: MSC_DUNGEON2
    'CharlockB3': 'dungeon_floor_3_music',
    'CharlockB4': 'dungeon_floor_4_music',
    'CharlockB5': 'dungeon_floor_5_music',
    'CharlockB6': 'dungeon_floor_6_music',
    'CharlockB7Wide': 'dungeon_floor_7_music',  # sublevel 6: MSC_DUNGEON7
    'CharlockB7Narrow': 'dungeon_floor_7_music',  # also sublevel 6
    'SwampCave': 'dungeon_floor_1_music',  # MSC_DUNGEON1
    'MountainCaveB1': 'dungeon_floor_1_music',  # rock mountain cave B1: MSC_DUNGEON1
    'MountainCaveB2': 'dungeon_floor_2_music',  # rock mountain cave B2: MSC_DUNGEON2
    'GarinsGraveB1': 'dungeon_floor_1_music',  # cave of Garinham B1: MSC_DUNGEON1
    'GarinsGraveB2': 'dungeon_floor_2_music',  # B2: MSC_DUNGEON2
    'GarinsGraveB3': 'dungeon_floor_3_music',  # B3: MSC_DUNGEON3
    'GarinsGraveB4': 'dungeon_floor_4_music',  # B4: MSC_DUNGEON4
    'ErdricksCaveB1': 'dungeon_floor_1_music',  # MSC_DUNGEON1
    'ErdricksCaveB2': 'dungeon_floor_2_music',  # MSC_DUNGEON2
}


class TestMapMusic(unittest.TestCase):

    def test_every_map_plays_its_resume_music_tbl_music(self):
        config = {**test_config, 'ORCHESTRA_MUSIC_ENABLED': False}  # the NES music has a track for each floor
        directories = Directories(config)
        playable_maps = {name for name, map_class in map_lookup.items() if 'layout' not in
                         map_class.__init__.__code__.co_varnames}
        self.assertEqual(set(RESUME_MUSIC_TBL), playable_maps)
        for name, attribute in RESUME_MUSIC_TBL.items():
            with self.subTest(map=name):
                self.assertEqual(map_lookup[name](config).music_file_path, getattr(directories, attribute))

    def test_every_dungeon_floor_has_its_own_nes_music(self):
        config = {**test_config, 'ORCHESTRA_MUSIC_ENABLED': False}
        directories = Directories(config)
        floors = [getattr(directories, f'dungeon_floor_{floor}_music') for floor in range(1, 9)]
        self.assertEqual(len(set(floors)), 8)


class TestMapChangeMusic(unittest.TestCase):
    """NES MapChngNoSound/MapChngWithSound: nothing silences the music before the new map's music starts (LB10E), and
    that always starts from the beginning, within Tantegel Castle too."""

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game({**test_config, 'ORCHESTRA_MUSIC_ENABLED': False})

    def test_the_new_maps_music_is_the_only_music_change(self):
        for (from_map, from_coordinates), (to_map, to_coordinates) in (
                (('TantegelThroneRoom', (10, 13)), ('TantegelCourtyard', (14, 14))),
                (('TantegelCourtyard', (14, 14)), ('Alefgard', (50, 50))),
                (('Alefgard', (50, 50)), ('Brecconary', (23, 10)))):
            with self.subTest(to_map=to_map):
                self.game.change_map(map_lookup[from_map](self.game.config), destination_coordinates=from_coordinates)
                with patch.object(self.game, 'music_player') as music_player:
                    self.game.change_map(map_lookup[to_map](self.game.config), destination_coordinates=to_coordinates)
                self.assertEqual(music_player.mock_calls,
                                 [call.load_and_play_music(self.game.current_map.music_file_path)])


class TestFightMusic(unittest.TestCase):
    """NES InitFight (MSC_ENTR_FGHT, whose opening runs into the fight loop, or MSC_END_BOSS) and ChkUseFlute,
    ChkUseHarp, ChkUseBelt and ChkUseNecklace (MSC_REG_FGHT, the loop without the opening)."""

    def setUp(self):
        self.config = {**test_config, 'ORCHESTRA_MUSIC_ENABLED': False}
        self.directories = Directories(self.config)

    def test_the_two_fight_tracks(self):
        self.assertTrue(self.directories.battle_music.endswith('14 Dragon Quest 1 - A Monster Draws Near.mp3'))
        self.assertTrue(self.directories.regular_fight_music.endswith('24 Dragon Quest 1 - Monster Battle.mp3'))

    def test_a_fight_starts_with_the_opening_then_loops_the_fight_music(self):
        music_player = MagicMock()
        Battle(self.config, 'Slime', MagicMock()).play_battle_music(music_player)
        music_player.load_and_play_music.assert_called_once_with(self.directories.battle_music,
                                                                 then_loop=self.directories.regular_fight_music)

    def test_the_fight_music_comes_back_without_the_opening(self):
        for enemy, music in (('Slime', self.directories.regular_fight_music),
                             ('Dragonlord', self.directories.regular_fight_music),
                             ('Dragonlord 2', self.directories.end_boss_music)):
            with self.subTest(enemy=enemy):
                music_player = MagicMock()
                Battle(self.config, enemy, MagicMock()).resume_battle_music(music_player)
                music_player.load_and_play_music.assert_called_once_with(music)

    @patch('src.music_player.mixer')
    def test_music_player_queues_the_loop(self, mock_mixer):
        player = MusicPlayer({'MUSIC_ENABLED': True, 'SOUND_ENABLED': False, 'ORCHESTRA_MUSIC_ENABLED': False})
        player.load_and_play_music('opening.mp3', then_loop='loop.mp3')
        self.assertEqual(mock_mixer.music.mock_calls, [call.stop(), call.load('opening.mp3'), call.set_volume(0.5),
                                                       call.play(), call.queue('loop.mp3', loops=-1)])
        mock_mixer.reset_mock()
        player.load_and_play_music('loop.mp3', then_loop='loop.mp3')
        mock_mixer.music.play.assert_called_once_with(-1)
        mock_mixer.music.queue.assert_not_called()


class TestCommandMenuAudio(unittest.TestCase):

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()
        self.directories = self.game.directories
        self.addCleanup(patch.stopall)
        self.music_player = patch.object(self.game, 'music_player').start()
        self.patch_menu()

    def patch_menu(self):
        """The COMMAND menu, with its text and sound effects patched out. A change of map makes a new one."""
        self.cmd_menu = self.game.cmd_menu
        patch.object(self.cmd_menu, 'show_text_in_dialog_box').start()
        patch.object(self.cmd_menu, 'show_line_in_dialog_box').start()
        self.play_sound = patch.object(self.cmd_menu.sound, 'play_sound').start()

    def go_to(self, map_name, coordinates):
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates)
        self.music_player.reset_mock()
        self.patch_menu()

    def in_battle_with(self, enemy_name):
        battle = Battle(self.game.config, enemy_name, self.game.current_map)
        self.cmd_menu.current_battle = battle
        return battle

    def test_cursed_item_in_a_fight_brings_back_the_regular_fight_music(self):
        # NES ChkUseBelt/ChkUseNecklace: MSC_REG_FGHT, even against the Dragonlord's final form
        for enemy_name in ('Slime', 'Dragonlord 2'):
            with self.subTest(enemy=enemy_name):
                self.music_player.reset_mock()
                self.in_battle_with(enemy_name)
                self.cmd_menu.cursed_belt()
                self.assertEqual(self.music_player.mock_calls[-1],
                                 call.load_and_play_music(self.directories.regular_fight_music))

    def test_flute_in_a_fight_brings_back_the_regular_fight_music(self):
        self.in_battle_with('Slime')
        self.cmd_menu.fairy_flute()
        self.assertEqual(self.music_player.mock_calls,
                         [call.play_until_end(self.directories.flute_music, self.game.game_state.config),
                          call.load_and_play_music(self.directories.regular_fight_music)])

    def test_rainbow_drop_plays_the_rainbow_bridge_music(self):
        # NES ChkDrop: MSC_RNBW_BRDG, the rainbow flash while it plays (LDEC5-LDEFB), WaitForMusicEnd, MSC_OUTDOOR,
        # then ModMapBlock puts the bridge down
        self.go_to('Alefgard', (50, 50))
        from src.constants import RAINBOW_DROP_COORDINATES
        self.game.player.row, self.game.player.column = RAINBOW_DROP_COORDINATES
        events = []
        self.music_player.play_clip.side_effect = lambda *args: events.append('rainbow bridge music')
        self.music_player.wait_for_music_end.side_effect = lambda *args: events.append('music end')
        self.music_player.load_and_play_music.side_effect = lambda *args: events.append('overworld music')
        with patch.object(self.cmd_menu, 'set_tile_by_coordinates',
                          side_effect=lambda *args: events.append('bridge')), \
                patch('src.menu.rainbow_bridge_flash', side_effect=lambda *args: events.append('flash')):
            self.cmd_menu.rainbow_drop()
        self.assertEqual(events, ['rainbow bridge music', 'flash', 'music end', 'overworld music', 'bridge'])
        self.assertEqual(self.music_player.mock_calls,
                         [call.play_clip(self.directories.rainbow_bridge_music),
                          call.wait_for_music_end(self.game.game_state.config),
                          call.load_and_play_music(self.directories.overworld_music)])

    def test_rainbow_drop_in_the_wrong_place_plays_nothing(self):
        self.cmd_menu.current_map = MockMap(self.game.config)
        self.cmd_menu.rainbow_drop()
        self.assertEqual(self.music_player.mock_calls, [])

    def test_return_and_wings_play_the_wyvern_wing_sound(self):
        # NES DoReturn: SFX_WVRN_WNG, then MapChngFadeNoSound
        for use in ('return_', 'wings'):
            with self.subTest(use=use):
                self.go_to('Brecconary', (23, 10))
                self.game.player.inventory = ['Wings']
                with patch.object(self.cmd_menu, 'warp', side_effect=lambda *args: self.play_sound('warp')):
                    getattr(self.cmd_menu, use)()
                self.assertEqual(self.play_sound.call_args_list,
                                 [call(self.directories.wyvern_wing_sfx), call('warp')])

    def test_outside_plays_the_stairs_sound_after_the_fade(self):
        # NES ChangeMaps -> SetPlyrPixelLoc -> MapChngWithSound: the sound comes once the screen has faded out
        self.go_to('ErdricksCaveB1', (1, 1))
        events = []
        with patch.object(self.game.sound, 'play_sound', side_effect=events.append), \
                patch('src.map_manager.screen_fade',
                      side_effect=lambda fade_out, **kwargs: events.append('fade out' if fade_out else 'fade in')):
            self.cmd_menu.outside()
        self.play_sound.assert_not_called()  # nothing before the fade
        self.assertEqual(events, ['fade out', self.directories.stairs_sfx, 'fade in'])
        self.assertEqual(self.game.current_map.identifier, 'Alefgard')

    def test_outside_where_it_fails_plays_nothing(self):
        self.go_to('Brecconary', (23, 10))
        with patch.object(self.cmd_menu, 'warp') as warp:
            self.cmd_menu.outside()
        warp.assert_not_called()
        self.play_sound.assert_not_called()


class TestDragonlordDefeatedSound(unittest.TestCase):

    def test_the_way_out_plays_the_stairs_sound(self):
        # NES NotDL1Defeated: ChangeMaps -> SetPlyrPixelLoc -> MapChngWithSound
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        game = new_game()
        events = []
        with patch.object(game.ending, 'say'), \
                patch.object(game.sound, 'play_sound', side_effect=events.append), \
                patch('src.map_manager.screen_fade',
                      side_effect=lambda fade_out, **kwargs: events.append('fade out' if fade_out else 'fade in')):
            game.ending.final_boss_defeated()
        self.assertEqual(events, ['fade out', game.directories.stairs_sfx, 'fade in'])


class TestStairsSound(unittest.TestCase):
    """NES MapChngWithSound (Bank00, LB097-LB0B6): ScreenFadeOut, the display off, then SFX_STAIRS, and only then the
    new map is drawn and faded in. StairsSFX (Bank01, $839E) is the one stairs sound, up or down; the soundtrack's
    "Stairs Down" is RunSFX ($83C2), the running away sound."""

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()
        self.directories = self.game.directories
        self.addCleanup(patch.stopall)
        patch.object(self.game, 'music_player').start()

    def test_the_two_recordings(self):
        self.assertTrue(self.directories.stairs_sfx.endswith('29 Dragon Quest 1 - Stairs Up.mp3'))
        self.assertTrue(self.directories.run_away_sfx.endswith('30 Dragon Quest 1 - Stairs Down.mp3'))

    def take_stairs(self, map_name, stair_direction):
        current_map = map_lookup[map_name](self.game.config)
        coordinates, staircase = next((coordinates, staircase) for coordinates, staircase in
                                      current_map.staircases.items()
                                      if staircase['stair_direction'] == stair_direction)
        self.game.change_map(current_map, destination_coordinates=current_map.initial_coordinates)
        self.game.player.row, self.game.player.column = coordinates
        events = []
        with patch.object(self.game.sound, 'play_sound', side_effect=events.append), \
                patch('src.map_manager.screen_fade',
                      side_effect=lambda fade_out, **kwargs: events.append('fade out' if fade_out else 'fade in')):
            self.game.map_mgr.process_warp(staircase)
        return events

    def test_stairs_play_the_stairs_sound_after_the_fade_out(self):
        for map_name, stair_direction in (('TantegelThroneRoom', 'down'), ('TantegelCourtyard', 'up')):
            with self.subTest(stair_direction=stair_direction):
                self.assertEqual(self.take_stairs(map_name, stair_direction),
                                 ['fade out', self.directories.stairs_sfx, 'fade in'])

    def test_a_map_change_without_stairs_is_silent(self):
        # NES MapChngNoSound / MapChngFadeNoSound
        events = []
        with patch.object(self.game.sound, 'play_sound', side_effect=events.append), \
                patch('src.map_manager.screen_fade',
                      side_effect=lambda fade_out, **kwargs: events.append('fade out' if fade_out else 'fade in')):
            self.game.change_map(map_lookup['Brecconary'](self.game.config), destination_coordinates=(23, 10))
        self.assertEqual(events, ['fade out', 'fade in'])


class TestRunAwaySound(unittest.TestCase):
    """NES PlyrRun (LE88B) and an enemy running away (LEFCB): SFX_RUN, RunSFX ($83C2)."""

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()

    def test_the_hero_running_away(self):
        battle = Battle(self.game.config, 'Slime', self.game.current_map)
        battle.enemy.is_asleep = True  # always gets away
        with patch.object(battle.sound, 'play_sound') as play_sound:
            battle.battle_run(MagicMock(), self.game.player, battle)
        play_sound.assert_called_once_with(self.game.directories.run_away_sfx)

    def test_an_enemy_running_away(self):
        controller = self.game.battle_ctrl
        battle = Battle(self.game.config, 'Slime', self.game.current_map)
        with patch.object(controller.sound, 'play_sound') as play_sound, \
                patch.object(controller.cmd_menu, 'show_line_in_dialog_box'), \
                patch.object(controller.cmd_menu, 'wait_for_button'), \
                patch.object(battle, 'make_enemy_image_disappear'):
            controller.enemy_run_away(battle, battle.enemy)
        play_sound.assert_called_once_with(self.game.directories.run_away_sfx)


class TestWaitForSoundEffectEnd(unittest.TestCase):
    """NES WaitForMusicEnd after a sound effect (PlyrCastSpell LDBAC): only what is left of it is waited out, in game
    time."""

    def test_waits_out_the_rest_of_the_sound(self):
        sound = Sound({**test_config, 'SOUND_ENABLED': False})
        config = {'NO_WAIT': False}
        with patch('src.sound.game_ticks', return_value=1000):
            sound.play_sound('spell.mp3')
        with patch('src.sound.game_ticks', return_value=1300), patch('src.sound.wait') as wait:
            sound.wait_for_sfx_end(42, config)  # 698.8 ms
        wait.assert_called_once_with(1000 + 42 * 1000 / NES_FPS - 1300, config)
        with patch('src.sound.game_ticks', return_value=2000), patch('src.sound.wait') as wait:
            sound.wait_for_sfx_end(42, config)  # already over
        wait.assert_called_once_with(0, config)

    def test_nothing_to_wait_for_before_any_sound(self):
        with patch('src.sound.wait') as wait:
            Sound({**test_config, 'SOUND_ENABLED': False}).wait_for_sfx_end(42, {'NO_WAIT': False})
        wait.assert_not_called()


class TestDeathMusic(unittest.TestCase):

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()

    def test_death_music_plays_once_to_the_end_before_thou_art_dead(self):
        # NES PlayerHasDied / InitDeathSequence: MSC_DEATH, WaitForMusicEnd, then DeathText
        self.game.player.current_hp = 0
        events = []
        with patch.object(self.game, 'drawer'), patch.object(self.game, 'music_player') as music_player, \
                patch('src.game.display'), \
                patch.object(self.game.cmd_menu, 'show_text_in_dialog_box',
                             side_effect=lambda *args, **kwargs: events.append('Thou art dead.')), \
                patch.object(self.game, 'set_post_death_attributes'):
            music_player.play_until_end.side_effect = lambda *args: events.append('death music')
            self.game.handle_death()
        music_player.play_until_end.assert_called_once_with(self.game.directories.death_music,
                                                            self.game.game_state.config)
        music_player.load_and_play_music.assert_not_called()
        self.assertEqual(events, ['death music', 'Thou art dead.'])


class TestEnvironmentDamageSound(unittest.TestCase):

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()
        self.game.player.current_hp = self.game.player.max_hp = 100
        self.game.player.is_moving = False
        self.game.player.received_environment_damage = False
        self.game.player.armor = None

    def test_swamp_and_force_field_sounds(self):
        # NES ChkOtherBlocks: SFX_SWMP_DMG on a swamp, SFX_FFDAMAGE on a force field
        directories = self.game.directories
        for tile, sfx in (('MARSH', directories.swamp_sfx), ('BARRIER', directories.barrier_sfx)):
            with self.subTest(tile=tile):
                self.game.player.received_environment_damage = False
                with patch.object(self.game.sound, 'play_sound') as play_sound, \
                        patch('src.game.flash_transparent_color'), patch.object(self.game, 'drawer'), \
                        patch('src.game.display'):
                    self.game.handle_environment_damage(tile)
                play_sound.assert_called_once_with(sfx)


class TestSoundEffectsAreNeverDropped(unittest.TestCase):
    """#317. NES DoSFX: there is one SFX slot, and every sound effect takes it over from the one before. So a burst of
    sound effects, as at a high game speed, plays each one in turn, cutting the one before short, and none is
    skipped."""

    def setUp(self):
        self.sound = Sound({**test_config, 'SOUND_ENABLED': True})
        patch.dict('src.sound._sound_library', clear=True).start()  # real sounds, not another test's mocks
        self.addCleanup(patch.stopall)
        self.addCleanup(pygame.mixer.stop)
        pygame.mixer.stop()

    def test_a_burst_of_sound_effects_plays_every_one(self):
        directories = self.sound.directories
        burst = [directories.menu_button_sfx, directories.attack_sfx, directories.hit_sfx, directories.missed_sfx,
                 directories.spell_sfx, directories.prepare_attack_sfx, directories.receive_damage_2_sfx,
                 directories.excellent_move_sfx, directories.missed_2_sfx, directories.open_door_sfx,
                 directories.open_treasure_sfx, directories.stairs_sfx]
        self.assertGreater(len(burst), pygame.mixer.get_num_channels())
        sfx_slot = pygame.mixer.Channel(SFX_CHANNEL)
        for path in burst:
            self.sound.play_sound(path)
            # the newest one is the one playing
            self.assertIs(sfx_slot.get_sound(), self.sound_for(path))
            # and nothing piles up on the other channels
            self.assertFalse(any(pygame.mixer.Channel(i).get_busy()
                                 for i in range(pygame.mixer.get_num_channels()) if i != SFX_CHANNEL))

    def test_the_text_beep_takes_over_from_any_sound_effect(self):
        directories = self.sound.directories
        self.sound.play_sound(directories.menu_button_sfx)
        self.sound.play_sfx(directories.text_beep_sfx)
        self.assertIs(pygame.mixer.Channel(SFX_CHANNEL).get_sound(), self.sound_for(directories.text_beep_sfx))

    @staticmethod
    def sound_for(path):
        from src.sound import _sound_library
        return _sound_library[path]


if __name__ == '__main__':
    unittest.main()
