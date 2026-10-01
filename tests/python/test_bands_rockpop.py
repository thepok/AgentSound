"""Rock and pop band presets (agentsound/bandlib/rock.py, pop.py): every preset builds and compiles, its roles,
buses, master chain and analysis profile are set, the articulation / kit helpers work, overrides and fallbacks behave.
Presets whose required sample packs are missing are skipped (python -m agentsound samples)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentsound import Clip, Song, bands, drums, library  # noqa: E402
from agentsound import articulation as art  # noqa: E402
from agentsound.bandlib import pop, rock  # noqa: E402
from agentsound.patches import Instrument, fx, inst  # noqa: E402
from agentsound.theory import ComposeError, Key  # noqa: E402

PRESETS = {
    'rock_band': ('rock', ('drums', 'bass', 'gtr_l', 'gtr_r', 'lead', 'keys')),
    'indie_band': ('rock', ('drums', 'bass', 'gtr_l', 'gtr_r', 'lead', 'keys')),
    'power_ballad': ('rock', ('piano', 'strings', 'pad', 'drums', 'bass', 'lead')),
    'pop_band': ('pop', ('drums', 'perc', 'bass', 'keys', 'pad', 'pluck', 'lead')),
    'funk_band': ('pop', ('drums', 'bass', 'keys', 'gtr', 'horns', 'lead')),
}


def _available(name: str) -> bool:
    return all(rock.installed(p) for p in bands.get(name).requires)


def _song(bars: int = 2) -> tuple:
    s = Song('t', tempo=120, key='E minor', seed=3)
    a = s.section('a', bars=bars)
    return s, a


def _play_something(b, a) -> None:
    for role, t in b.roles.items():
        if role in ('drums', 'perc'):
            t.play(drums({'kick': 'x...x...', 'snare': '..x...x.', 'hat': 'xxxxxxxx'}, step='1/8'), a)
        else:
            t.play(Clip([(0, 1, 'E3', 100), (0, 1, 'B3', 100), (1, 1, 'G3', 90)], length=4), a)


class TestRegistry(unittest.TestCase):
    def test_registered(self):
        for name, (genre, roles) in PRESETS.items():
            p = bands.get(name)
            self.assertEqual(p.genre, genre, name)
            self.assertEqual(p.roles, roles, name)
            self.assertTrue(p.description and p.tuned, name)

    def test_describe_all_lists_them(self):
        text = bands.describe_all()
        for name in PRESETS:
            self.assertIn(name, text)


class TestPresetsBuild(unittest.TestCase):
    def test_every_preset_builds_and_compiles(self):
        for name, (genre, roles) in PRESETS.items():
            with self.subTest(preset=name):
                if not _available(name):
                    self.skipTest(f"{name}: packs {bands.get(name).requires} missing")
                s, a = _song()
                b = bands.make(name, s)
                self.assertEqual(tuple(b.roles), roles)
                self.assertEqual(b.analysis, {'profile': genre})
                self.assertIn('How to play it', b.notes)
                self.assertTrue(b.buses)
                self.assertTrue(s.master.fx, 'the preset sets a master chain')
                self.assertEqual(s.master.fx[-1].type, 'limiter')
                for role, t in b.roles.items():
                    self.assertTrue(any(f.type == 'utility' and f.name == 'trim' for f in t.fx),
                                    f"{role}: the balance sits in the 'trim' utility")
                    self.assertEqual(t.gain_db, 0.0, f"{role}: the fader is left to the song")
                _play_something(b, a)
                out = s.compile()
                self.assertTrue(out['tracks'])

    def test_without_ids_and_sounds(self):
        name = 'pop_band'
        s, a = _song()
        b = bands.make(name, s, without=('pluck', 'perc'), ids={'lead': 'hook'},
                       sounds={'keys': inst.sf2('Grand Piano')})
        self.assertNotIn('pluck', b)
        self.assertNotIn('perc', b)
        self.assertEqual(b.lead.id, 'hook')
        self.assertEqual(b.keys.instrument.type, 'sf2')
        self.assertIn('utility', [f.type for f in b.keys.fx], 'an overridden sound keeps the role chain')
        _play_something(b, a)
        s.compile()

    def test_options_are_checked(self):
        for name, bad in (('rock_band', {'keys': 'harp'}), ('rock_band', {'gain': 'insane'}),
                          ('indie_band', {'keys': 'cello'}), ('pop_band', {'lead': 'kazoo'}),
                          ('pop_band', {'bass': 'tuba'}), ('funk_band', {'keys': 'harp'}),
                          ('funk_band', {'bass': 'fretless'})):
            with self.subTest(preset=name, opt=bad):
                with self.assertRaises(ComposeError):
                    bands.make(name, _song()[0], without=bands.get(name).roles, **bad)

    def test_options_build(self):
        variants = [('rock_band', {'keys': 'piano', 'gain': 'high'}), ('indie_band', {'keys': 'organ'}),
                    ('pop_band', {'keys': 'piano', 'bass': 'synth', 'lead': 'sax', 'sub': 'F1'}),
                    ('pop_band', {'keys': 'wurli', 'lead': 'guitar', 'sub': False}),
                    ('funk_band', {'keys': 'wurli', 'bass': 'slap', 'lead': 'synth'})]
        for name, opts in variants:
            with self.subTest(preset=name, opts=opts):
                if not _available(name) or (opts.get('lead') == 'guitar' and not rock.installed('karoryfer-emilyguitar')
                                            and not rock.installed('freepats-fsbs-direct')):
                    self.skipTest('packs missing')
                s, a = _song()
                b = bands.make(name, s, **opts)
                _play_something(b, a)
                s.compile()

    def test_missing_required_pack_names_the_fetch(self):
        with tempfile.TemporaryDirectory() as empty, mock.patch.object(library, 'SAMPLES', Path(empty)):
            with self.assertRaisesRegex(ComposeError, 'samples fetch freepats-fsbs-direct'):
                bands.make('rock_band', _song()[0])
            # the roles that need no pack still build: the guitars left out
            s, a = _song()
            b = bands.make('rock_band', s, without=('gtr_l', 'gtr_r', 'lead'))
            self.assertEqual(set(b.roles), {'drums', 'bass', 'keys'})
            _play_something(b, a)
            s.compile()
            # pop_band falls back to engine / GeneralUser sounds entirely
            s, a = _song()
            b = bands.make('pop_band', s)
            _play_something(b, a)
            s.compile()

    def test_bus_reused_when_the_song_has_it(self):
        s, _ = _song()
        mine = s.bus('plate', [fx.reverb(type='plate', mix=1.0)])
        b = bands.make('pop_band', s, without=('perc', 'bass', 'keys', 'pad', 'pluck', 'lead', 'drums'))
        self.assertIs(b.buses['plate'], mine)


@unittest.skipUnless(rock.installed('freepats-fsbs-direct'), 'freepats-fsbs-direct not installed')
class TestGuitarArticulations(unittest.TestCase):
    def test_di_guitar_keyswitches(self):
        g = rock.di_guitar(rock.FSBS_DI)
        self.assertEqual(art.available(g), ['open', 'palm mute', 'dead note'])
        zones = g.params['samples']
        by_sw = {}
        for z in zones:
            by_sw.setdefault(z['swLast'], []).append(z)
        self.assertEqual(len(by_sw[0]), len(by_sw[1]))
        self.assertTrue(all(z.get('filter') == 'lpf_2p' and z.get('sustain') == 0.0 for z in by_sw[1]))
        self.assertTrue(all('filter' not in z for z in by_sw[0]))
        # dead notes: real muted-string scratches (Emilyguitar installed) or the short filtered blip
        self.assertTrue(all('/noises/muted' in z['file'].replace('\\', '/') or z.get('decay', 1) < 0.2
                            for z in by_sw[2]))

    def test_palm_mute_notes_get_keyswitches(self):
        s, a = _song()
        t = s.track('g', rock.di_guitar(rock.FSBS_DI))
        chug = Clip([(i * 0.5, 0.4, 'E2', 100) for i in range(8)], length=4).chordify('power')
        t.play(chug.articulate('palm', span=(0, 2)), a)
        notes = s.compile()['tracks'][0]['notes']
        self.assertIn(1, {n[2] if isinstance(n, list) else n['pitch'] for n in notes})

    def test_unknown_articulation(self):
        with self.assertRaisesRegex(ComposeError, 'unknown articulation'):
            rock.di_guitar(rock.FSBS_DI, articulations=('tapping',))

    def test_palm_mute_keeps_the_pick_attack(self):
        g = rock.di_guitar(rock.FSBS_DI)
        palm = [z for z in g.params['samples'] if z.get('swLast') == 1 and z.get('trigger') != 'release']
        # the rock pass: a 900 Hz resonant low-pass keeps the chug's thump, its pick envelope (+3600 ct for ~60 ms)
        # keeps the attack: through the amp as bright as the open chord (centroid ratio 1.02), not a muffled synth
        self.assertTrue(all(z['cutoff'] >= 800 and z['filterEnv'][0] >= 2400 for z in palm), 'the palm mute lost its pick')

    def test_di_sets_hit_the_amp_at_the_same_level(self):
        self.assertEqual(rock.di_guitar(rock.FSBS_DI).params['level'], rock.DI_LEVEL[rock.FSBS_DI])
        self.assertEqual(rock.di_guitar(rock.FSBS_DI, level=-2.0).params['level'], rock.DI_LEVEL[rock.FSBS_DI] - 2.0)
        self.assertGreater(rock.DI_LEVEL[rock.EMILY], rock.DI_LEVEL[rock.FSBS_DI] + 6)


def _dead_zones(g):
    key = g.info['sfz']['keyswitches']['dead note']
    return [z for z in g.params['samples'] if z.get('swLast') == key and z.get('trigger') != 'release'
            and z.get('hi', 127) < 90]


@unittest.skipUnless(rock.installed('karoryfer-emilyguitar'), 'karoryfer-emilyguitar not installed')
class TestRealDeadNotes(unittest.TestCase):
    def test_emily_dead_notes_are_its_muted_scratches(self):
        dead = _dead_zones(rock.di_guitar(rock.EMILY))
        self.assertTrue(dead)
        self.assertTrue(all('/noises/muted' in z['file'].replace('\\', '/') for z in dead))
        self.assertTrue(all('filter' not in z for z in dead), 'real scratches, not the filtered blip')
        # the whole playing range is covered, each band by one scratch set with its round robins
        covered = set()
        for z in dead:
            covered.update(range(z['lo'], z['hi'] + 1))
            self.assertLessEqual(abs(z['root'] - (z['lo'] + z['hi']) / 2), 1)
        self.assertTrue(set(range(40, 89)) <= covered)
        self.assertTrue(any('lorand' in z for z in dead))

    @unittest.skipUnless(rock.installed('freepats-fsbs-direct'), 'freepats-fsbs-direct not installed')
    def test_other_sets_borrow_them_at_the_matching_level(self):
        dead = _dead_zones(rock.di_guitar(rock.FSBS_DI))
        self.assertTrue(dead and all('karoryfer-emilyguitar' in z['file'] for z in dead))
        own = _dead_zones(rock.di_guitar(rock.EMILY))
        offset = rock.DI_LEVEL[rock.EMILY] - rock.DI_LEVEL[rock.FSBS_DI]
        self.assertAlmostEqual(dead[0].get('gain', 0.0) - own[0].get('gain', 0.0), offset, places=3)

    def test_fallback_without_emily_is_the_filtered_note(self):
        g = rock.di_guitar(rock.EMILY)
        with mock.patch.object(rock, 'installed', lambda p: False):
            ins = rock.articulated(rock.EMILY, {'dead note': rock.GUITAR_ARTICULATIONS['dead note']})
            for z in ins.params['samples']:      # a set without muted noises of its own
                z['file'] = z['file'].replace('/noises/muted', '/noises/x')
            self.assertFalse(rock.real_dead_notes(ins, 1, 0))
        self.assertTrue(_dead_zones(g))


class TestAmpAndMaster(unittest.TestCase):
    def test_amp_voicing(self):
        chain = rock.amp('crunch')                       # the tube amp (its bright cap + tone stack) -> cab -> mic
        self.assertEqual([(f.type, f.name) for f in chain], [('amp', 'amp'), ('convolver', None), ('eq', 'mic')])
        self.assertEqual(rock.amp('crunch', bright=0)[0].params['bright'], 0)
        self.assertEqual(rock.amp('lead', gain=4.5)[0].params['gain'], 4.5)

    def test_second_preset_keeps_the_master_chain(self):
        s, a = _song()
        b1 = bands.make('pop_band', s, without=('perc', 'pad', 'pluck', 'lead', 'keys', 'bass'))
        n = len(s.master.fx)
        b2 = bands.make('rock_band', s, without=('gtr_l', 'gtr_r', 'lead', 'drums', 'bass'))
        self.assertEqual(len(s.master.fx), n)
        self.assertEqual([f.type for f in s.master.fx].count('limiter'), 1)
        self.assertEqual((b1.info['master'], b2.info['master']), ('set', 'kept'))

    def test_song_master_is_kept(self):
        s, _ = _song()
        s.master.add(fx.limiter(gain=2.0))
        b = bands.make('funk_band', s, without=('gtr', 'lead', 'horns', 'keys', 'bass', 'drums'))
        self.assertEqual(len(s.master.fx), 1)
        self.assertEqual(b.info['master'], 'kept')

    def test_indie_defaults_to_the_full_kit(self):
        import inspect
        self.assertEqual(inspect.signature(rock.indie_band).parameters['kit'].default, 'big_rusty')

    @unittest.skipUnless(rock.installed('karoryfer-unruly-drums'), 'karoryfer-unruly-drums not installed')
    def test_unruly_mic_mix_centres_the_kick(self):
        ins = rock.rock_kit('unruly')
        self.assertEqual(ins.info['sfz']['cc'][72], 10)      # kick overhead down: the low end stays mono
        keys = {z['lo'] for z in ins.params['samples']}
        self.assertTrue({48, 50} <= keys)


class TestHelpers(unittest.TestCase):
    def test_remap_keys_copies_zones(self):
        ins = Instrument('sampler', {'samples': [{'file': 'x.wav', 'lo': 47, 'hi': 47, 'root': 47},
                                                 {'file': 'y.wav', 'lo': 48, 'hi': 48, 'root': 48}]})
        rock.remap_keys(ins, {48: 47, 50: 47})
        keys = sorted((z['lo'], z['file'], z['root']) for z in ins.params['samples'])
        self.assertEqual(keys, [(47, 'x.wav', 47), (48, 'x.wav', 48), (50, 'x.wav', 50)])

    def test_layer_renumbers_groups_and_pans(self):
        a = Instrument('sampler', {'samples': [{'file': 'a.wav', 'group': 1, 'offBy': 1}]})
        b = Instrument('sampler', {'samples': [{'file': 'b.wav', 'group': 1, 'offBy': 1}]})
        out = rock.layer(a, b, gains=[0, -3], pans=[-0.4, 0.4])
        za, zb = out.params['samples']
        self.assertEqual((za['group'], zb['group']), (1, 2))
        self.assertEqual(zb['gain'], -3)
        self.assertEqual((za['pan'], zb['pan']), (-0.4, 0.4))

    def test_kick_sub(self):
        ins = Instrument('sampler', {'samples': [{'file': 'k.wav', 'lo': 36, 'hi': 36}]})
        pop.kick_sub(ins, 'F1')
        sine = ins.params['samples'][-1]
        self.assertEqual(sine['file'], '*sine')
        self.assertEqual(36 - sine['root'] + 60, 29)     # F1 on the kick key
        self.assertEqual(pop.tonic_sub(Key('F major')), 29)
        self.assertEqual(pop.tonic_sub(Key('D minor')), 38)
        drum_machine = inst.drums(kit='modern')
        self.assertIs(pop.kick_sub(drum_machine, 'F1'), drum_machine)

    @unittest.skipUnless(rock.installed('karoryfer-growlybass'), 'karoryfer-growlybass not installed')
    def test_growlybass_sounds_where_written(self):
        ins = rock.rock_bass('t', 'pick')
        self.assertEqual(ins.params['transpose'], 12)
        self.assertEqual(art.available(ins), ['sustain', 'staccato', 'mute'])


if __name__ == '__main__':
    unittest.main()
