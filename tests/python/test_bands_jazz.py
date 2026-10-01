"""Jazz band presets (agentsound/bandlib/jazz.py): every preset builds and compiles - on the installed sample packs
and on the GeneralUser fallback -, the options, the helpers and jazz.band()'s sampled sounds."""
import importlib.util
import pathlib
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from agentsound import Clip, Song, bands, jazz, library  # noqa: E402
from agentsound.bandlib import jazz as jb  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

PRESETS = ('jazz_trio', 'jazz_quartet', 'jazz_ballad', 'bossa')


@contextmanager
def samples(packs=()):
    """library.SAMPLES pointed at an empty folder where only `packs` look installed (a SOURCE.json each)."""
    with tempfile.TemporaryDirectory() as tmp:
        for p in packs:
            (pathlib.Path(tmp) / p).mkdir()
            (pathlib.Path(tmp) / p / 'SOURCE.json').write_text('{}')
        with mock.patch.object(library, 'SAMPLES', pathlib.Path(tmp)):
            yield pathlib.Path(tmp)


def installed(*packs) -> bool:
    return all((library.SAMPLES / p / 'SOURCE.json').is_file() for p in packs)


def play_everything(s, b, sec):
    """A bar of idiomatic material on every role of a jazz band."""
    prog = s.prog('Dm7:0.5 G7:0.5')
    kit = b.info.get('kit', jazz.GM_BRUSH)
    for role, t in b.roles.items():
        if role == 'comp' or role == 'guitar':
            t.play(jazz.comp(prog, seed=1), sec)
        elif role == 'bass':
            t.play(jazz.walking_bass(prog, key=s.key, seed=1), sec)
        elif role == 'drums':
            t.play(jb.brushes(b, 1, seed=1), sec)
        elif role in ('rim', 'shaker'):
            t.play(jb.bossa_groove(1, b)[role], sec)
        elif role == 'sax':
            jazz.horn_line(Clip([(0, 2, 'F4', 90), (2, 2, 'A4', 90)], length=4), s.tempo,
                           **b.info['horn']).place(t, sec)
        else:
            t.play(Clip([(0.5, 1, 'A4', 80), (2, 2, 'C5', 80)], length=4), sec)


class JazzPresets(unittest.TestCase):
    def test_registered(self):
        self.assertEqual(set(PRESETS), set(bands.list('jazz')))
        for name in PRESETS:
            p = bands.get(name)
            self.assertEqual(p.requires, ())          # every role falls back to GeneralUser GS
            self.assertTrue(p.description and p.tuned)

    def test_every_preset_builds_and_compiles(self):
        """On whatever is installed (the sampled packs with AGENTSOUND_SAMPLES, else the fallbacks)."""
        for name in PRESETS:
            with self.subTest(name):
                s = Song('t', tempo=132, key='F major')
                a = s.section('a', bars=1)
                b = bands.make(name, s)
                self.assertEqual(b.analysis, {'profile': 'jazz'})
                self.assertEqual(set(b.roles), set(bands.get(name).roles))
                self.assertIn('room', b)
                self.assertTrue(b.notes)
                self.assertEqual(set(b.info['sounds']), set(b.roles))
                play_everything(s, b, a)
                d = s.compile()
                self.assertEqual([f['type'] for f in d['master']['fx']], ['eq', 'compressor', 'tape', 'width', 'limiter'])
                self.assertFalse([w for w in s.warnings if 'dropped' in w or 'no bus' in w])

    def test_fallback_without_any_pack(self):
        with samples():
            for name in PRESETS:
                with self.subTest(name):
                    s = Song('t', tempo=66 if name == 'jazz_ballad' else 132, key='F major')
                    a = s.section('a', bars=1)
                    b = bands.make(name, s)
                    self.assertTrue(all('GeneralUser' in d for d in b.info['sounds'].values()), b.info['sounds'])
                    self.assertEqual(b.info['credits'], [])
                    self.assertEqual(b.info['room'], 'algorithmic room 1.2 s')
                    self.assertEqual(b.info['kit'], jazz.GM_BRUSH)
                    if 'sax' in b:
                        self.assertEqual(b.info['horn'], {'param': 'expression', 'vibrato': False})
                    play_everything(s, b, a)
                    s.compile()
            s = Song('t', tempo=70)
            s.section('a', bars=1)
            b = bands.make('jazz_ballad', s, bass='arco')
            self.assertIn('Double Bass', b.info['sounds']['bass'])

    def test_strict_names_the_pack(self):
        with samples():
            with self.assertRaisesRegex(ComposeError, 'samples fetch voxengo-im-reverbs'):
                bands.make('jazz_trio', Song('t', tempo=120), strict=True)
        with samples(['voxengo-im-reverbs']):
            with self.assertRaisesRegex(ComposeError, 'samples fetch salamander-grand'):
                bands.make('jazz_trio', Song('t', tempo=120), strict=True)

    def test_sampled_sounds_when_installed(self):
        packs = ['salamander-grand', 'meatbass', 'swirly-drums', 'mtg-solo-sax', 'voxengo-im-reverbs',
                 'little-devil-224xl-13-cd-plate-a']
        with samples(packs):
            s = Song('t', tempo=120)
            s.section('a', bars=1)
            b = bands.make('jazz_quartet', s)
            self.assertEqual(b.info['kit'], jazz.SWIRLY_BRUSH)
            self.assertEqual(b.info['sweep'], 'half')                   # 120 BPM: a stir every second
            self.assertEqual(b.info['horn'], {'param': 'dynamics', 'vibrato': True, 'glide': 0.2})
            self.assertIn('Salamander', b.info['sounds']['piano'])
            self.assertIn('Meatbass', b.info['sounds']['bass'])
            self.assertIn('MTG', b.info['sounds']['sax'])
            self.assertTrue(any('CC-BY 3.0' in c for c in b.info['credits']))
            self.assertEqual(b.info['room'], 'bus/ir_salon (salon)')
            self.assertEqual(b.info['plate'], 'bus/ir_plate')
            self.assertEqual(b.sax.instrument.params['mono'], 'legato')
            # placed on the stage by the instrument's own pan (a track pan barely moves a stereo recording)
            self.assertEqual(b.piano.instrument.params['pan'], jb._PLACE['piano'])
            self.assertEqual(b.piano.pan, 0.0)
            self.assertLess(b.piano.instrument.params['pan'], 0)
            self.assertGreater(b.drums.instrument.params['pan'], 0)
            # the comping ducks under the sax
            self.assertIn('ducker', [f.type for f in b.comp.fx])
            # a ballad tempo gets a stir per beat (a Swirly stir is a swell the next one must crossfade)
            s2 = Song('b', tempo=62)
            s2.section('a', bars=1)
            self.assertEqual(bands.make('jazz_ballad', s2).info['sweep'], 'beat')
            # stage: sax centre, the cross-stick where the preset puts it (the kit's own side-stick pan zeroed),
            # the shaker opposite the guitar
            self.assertEqual(b.sax.instrument.params['pan'], 0.0)
            with samples(packs + ['avl-blonde-bop', 'freepats-world-percussion', 'freepats-spanish-classical-guitar']):
                s3 = Song('c', tempo=130)
                s3.section('a', bars=1)
                bo = bands.make('bossa', s3)
                self.assertEqual(bo.rim.instrument.params['width'], 0.0)
                self.assertGreater(bo.rim.instrument.params['pan'], 0)
                self.assertGreater(bo.shaker.instrument.params['pan'], 0)
                self.assertLess(bo.guitar.instrument.params['pan'], 0)

    def test_options(self):
        s = Song('t', tempo=140)
        s.section('a', bars=1)
        b = bands.make('jazz_quartet', s, without=('sax',), ids={'comp': 'lh'}, space='room', plate=None,
                       master=False)
        self.assertNotIn('sax', b)
        self.assertEqual(b.comp.id, 'lh')
        self.assertIn('room', s.buses)
        self.assertNotIn('plate', b)
        self.assertEqual(b.info['room'], 'algorithmic room 1.2 s')
        self.assertFalse(s.master.fx)
        self.assertNotIn('ducker', [f.type for f in b.comp.fx])     # nothing to duck under
        with self.assertRaisesRegex(ComposeError, 'unknown option'):
            bands.make('jazz_trio', Song('u', tempo=120), spaces='salon')
        with self.assertRaisesRegex(ComposeError, 'space must be'):
            bands.make('jazz_trio', Song('u', tempo=120), space='cathedral')
        with self.assertRaisesRegex(ComposeError, "bass must be 'pizz' or 'arco'"):
            bands.make('jazz_ballad', Song('u', tempo=60), bass='bowed')
        with self.assertRaisesRegex(ComposeError, 'unknown roles'):
            bands.make('bossa', Song('u', tempo=120), without=('comp',))

    def test_sounds_override_keeps_the_chain(self):
        s = Song('t', tempo=120)
        s.section('a', bars=1)
        grand = jazz.inst.sf2('Grand Piano', level=3.0)
        b = bands.make('jazz_trio', s, sounds={'piano': grand, 'bass': jazz.inst.sf2('Acoustic Bass')})
        self.assertEqual(b.piano.instrument.params['level'], 3.0)
        self.assertEqual(b.comp.instrument.params['level'], 3.0)             # one instrument, two hands
        self.assertIn('override', b.info['sounds']['piano'])
        self.assertEqual([f.type for f in b.bass.fx][-3:], ['eq', 'compressor', 'width'])
        self.assertEqual(b.piano.instrument.params['pan'], jb._PLACE['piano'])
        with self.assertRaisesRegex(ComposeError, 'sounds'):
            bands.make('jazz_trio', Song('u', tempo=120), sounds={'piano': 42})

    def test_feel(self):
        s = Song('t', tempo=150)
        s.section('a', bars=1)
        b = bands.make('jazz_trio', s)
        self.assertAlmostEqual(b.bass._groove.swing, jazz.swing_ratio(150))
        s2 = Song('b', tempo=130)
        s2.section('a', bars=1)
        bo = bands.make('bossa', s2)
        self.assertEqual(bo.info['feel'].ratio, 0.5)                        # bossa plays straight
        self.assertIsNone(bo.sax._groove)                                   # horn_line bakes the feel in


class ReviewFixes(unittest.TestCase):
    """Regressions of the review (feat/bands-jazz-reviewed)."""

    def test_swirly_sweep_keeps_a_stir_about_every_second(self):
        self.assertEqual(jazz.swirly_sweep(144), 'half')        # 0.83 s
        self.assertEqual(jazz.swirly_sweep(120), 'half')        # 1.0 s
        self.assertEqual(jazz.swirly_sweep(100), 'beat')        # a half bar would be 1.2 s
        self.assertEqual(jazz.swirly_sweep(66), 'beat')
        self.assertEqual(jazz.swirly_sweep(240), 'bar')
        self.assertEqual(jazz.swirly_sweep(180, 3), 'bar')     # a waltz bar at 180 = 1.0 s
        for bpm in (56, 66, 90, 110, 144, 200, 260, 320):         # (below ~55 BPM even a beat is > 1.1 s)
            beats = {'bar': 4, 'half': 2, 'beat': 1}[jazz.swirly_sweep(bpm)]
            self.assertLessEqual(beats * 60.0 / bpm, jazz.STIR_EVERY + 1e-9)

    def test_brush_kit_stirs_overlap(self):
        """The patch keeps the stir tail and release long, so a new stir crossfades the last one (at the kit's
        defaults a stir was gone after ~1.3 s: 25-30 dB gaps between one-per-bar stirs)."""
        from agentsound import patches
        cc = patches.get('sampled/brush_kit').instrument.lazy['cc']
        self.assertEqual((cc[56], cc[58], cc[57]), (127, 127, 127))

    def test_overrides_are_recognised_by_file(self):
        """sounds= with an inst.sfz of the Swirly kit / a MTG patch gets the kit keymap / the MTG horn options."""
        s = Song('t', tempo=132)
        s.section('a', bars=1)
        kit = jazz.inst.sfz('samples/swirly-drums/Programs/Basic_kit.sfz', lazy=True)
        b = bands.make('jazz_quartet', s, sounds={'drums': kit, 'sax': 'sampled/tenor_sax'})
        self.assertEqual(b.info['kit'], jazz.SWIRLY_BRUSH)
        self.assertEqual(b.info['sweep'], 'half')
        self.assertEqual(b.info['horn'], {'param': 'dynamics', 'vibrato': True, 'glide': 0.2})
        s2 = Song('t2', tempo=132)
        s2.section('a', bars=1)
        b2 = bands.make('jazz_quartet', s2, sounds={'drums': jazz.inst.sf2(bank=128, program=40),
                                                     'sax': jazz.inst.sf2('Tenor Sax')})
        self.assertEqual(b2.info['kit'], jazz.GM_BRUSH)
        self.assertEqual(b2.info['horn'], {'param': 'expression', 'vibrato': True})

    def test_master_width_and_presence(self):
        s = Song('t', tempo=132)
        s.section('a', bars=1)
        bands.make('jazz_trio', s)
        eq, width = s.master.fx[0], s.master.fx[3]          # the width after the glue and the tape
        self.assertEqual(width.type, 'width')
        self.assertEqual(width.params['monobass'], 150)
        self.assertGreater(eq.params['peak3.gain'], 0)

    def test_pizz_bass_chain_keeps_the_dynamics(self):
        """The pizz bass gets a peak catcher (no levelling compressor: it flattened the walking lines to 0 dB of
        velocity response), the level from a fixed makeup; the bowed bass keeps its gentle compressor."""
        for opt in (None, jb.SOUNDS['bass'][0], jb.SOUNDS['bass'][-1]):
            comp = next(f for f in jb._bass_chain(opt) if f.type == 'compressor')
            self.assertGreaterEqual(comp.params['threshold'], -12)
            self.assertNotIn('automakeup', comp.params)
            self.assertEqual(comp.params['makeup'], jb.BASS_MAKEUP)
        arco = next(f for f in jb._bass_chain(None, arco=True) if f.type == 'compressor')
        self.assertEqual(arco.params['automakeup'], 'on')
        with samples(['meatbass']):
            s = Song('t', tempo=66)
            s.section('a', bars=1)
            b = bands.make('jazz_ballad', s)
            eq = next(f for f in b.bass.fx if f.type == 'eq' and 'low.gain' in f.params)
            self.assertGreater(eq.params['low.gain'], -5.0)                   # the ballad's long notes: more sub

    def test_band_sampled_piano_width(self):
        """jazz.band('auto'): the Salamander at width 0.6 (0.8 measured correlation ~0 on melody lines)."""
        with samples(['salamander-grand']):
            s = Song('t', tempo=120)
            s.section('a', bars=1)
            b = jazz.band(s)
            self.assertEqual(b.piano.instrument.params['width'], 0.6)

    def test_bossa_demo_groove_stops_on_the_last_chord(self):
        path = REPO / 'songs' / '_bands' / 'bossa' / 'song.py'
        spec = importlib.util.spec_from_file_location('demo_bossa_end', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        s = mod.build()
        d = s.compile()
        last_chord = next(x['startBeat'] for x in d['sections'] if x['name'] == 'outro') + 8.0   # outro.bar(2)
        for tid in ('drums', 'rim', 'shaker'):
            t = next(t for t in d['tracks'] if t['id'] == tid)
            self.assertLessEqual(max(n[0] for n in t['notes']), last_chord + 0.6, tid)   # (+ the feel's lay-back)


class Helpers(unittest.TestCase):
    def test_brushes_levels_the_swirly_stir(self):
        swirly = type('B', (), {'info': {'kit': jazz.SWIRLY_BRUSH, 'sweep': 'bar', 'stir': (1.9, 0.8)}})()
        gm = type('B', (), {'info': {'kit': jazz.GM_BRUSH, 'sweep': None, 'stir': (1.0, 1.0)}})()
        raw = jazz.brushes(4, 'medium', kit=jazz.SWIRLY_BRUSH, sweep='bar', seed=3)
        lev = jb.brushes(swirly, 4, 'medium', seed=3)
        self.assertEqual(len(raw), len(lev))
        for a, b in zip(sorted(raw), sorted(lev)):
            if a.pitch == jazz.SWIRLY_BRUSH['sweep']:
                self.assertEqual(b.vel, min(127, round(a.vel * 1.9)))
            elif a.pitch == jazz.SWIRLY_BRUSH['tap']:
                self.assertEqual(b.vel, max(1, round(a.vel * 0.8)))
            else:
                self.assertEqual(a.vel, b.vel)
        self.assertEqual(jb.brushes(gm, 4, 'medium', seed=3), jazz.brushes(4, 'medium', seed=3))
        # jazz.band()'s Band works too
        s = Song('t', tempo=120)
        s.section('a', bars=1)
        jb.brushes(jazz.band(s, sampled_sounds=False), 2)

    def test_pedal_follows_the_harmony(self):
        s = Song('t', tempo=66)
        sec = s.section('a', bars=2)
        s.section('b', bars=1)
        b = bands.make('jazz_ballad', s)
        pts = jb.pedal([b.piano, b.comp], s.prog('Ebmaj7:0.5 Cm7:0.5 Fm7 '), sec)
        self.assertEqual(pts, [(0.0, 0.0, 'step'), (0.1, 1.0, 'step'), (2.0, 0.0, 'step'), (2.1, 1.0, 'step'),
                               (4.0, 0.0, 'step'), (4.1, 1.0, 'step'), (8.0, 0.0, 'step')])
        for t in (b.piano, b.comp):
            self.assertIn('instrument.pedal', [x for x, _ in t._auto])

    def test_bossa_groove(self):
        s = Song('t', tempo=130)
        s.section('a', bars=8)
        b = bands.make('bossa', s)
        g = jb.bossa_groove(8, b, seed=1)
        self.assertEqual(set(g), {'drums', 'rim', 'shaker'})
        self.assertTrue(all(c.length == 32 for c in g.values()))
        rim = sorted(n.start for n in g['rim'] if n.start < 8)
        self.assertEqual(rim, [0.0, 1.5, 3.0, 4.5, 6.0])                    # 1 &2 4 | &1 3
        self.assertEqual({n.pitch for n in g['rim']}, {b.info['rim_keys']['rim']})
        self.assertEqual({n.pitch for n in g['shaker']},
                         {b.info['shaker_keys']['shake'], b.info['shaker_keys']['soft']})
        kicks = sorted(n.start for n in g['drums'] if n.pitch == b.info['kit']['kick'] and n.start < 4)
        self.assertEqual(kicks, [0.0, 1.5, 2.0, 3.5])


class JazzBandSampled(unittest.TestCase):
    """jazz.band(): the SFZ packs when installed (sampled_sounds='auto'), GeneralUser where one is missing."""

    def test_auto_uses_installed_packs(self):
        with samples(['meatbass', 'swirly-drums']):
            s = Song('t', tempo=120)
            s.section('a', bars=1)
            b = jazz.band(s, sax=True)
            self.assertEqual(b.bass.patch, 'sampled/upright_bass')
            self.assertEqual(b.drums.patch, 'sampled/brush_kit')
            self.assertEqual(b.piano.instrument.type, 'sf2')                # Salamander missing: GeneralUser
            self.assertEqual(b.sax.instrument.type, 'sf2')
            self.assertEqual(b.kit, jazz.SWIRLY_BRUSH)
            self.assertEqual(b.sweep, 'half')                           # jazz.swirly_sweep(120)
            self.assertEqual(b.stir, (1.9, 0.8))
            self.assertEqual(b.horn, {'param': 'expression', 'vibrato': False})
            self.assertIn('Meatbass', b.sounds['bass'])
            self.assertEqual(b.sounds['piano'], 'GeneralUser GS')
            self.assertFalse(b.bass.sends.get('plate') is not None and 'plate' not in s.buses)
        with samples(['salamander-grand', 'mtg-solo-sax']):
            s = Song('t', tempo=120)
            s.section('a', bars=1)
            b = jazz.band(s, sax=True)
            self.assertEqual(b.piano.patch, 'sampled/grand_piano')
            self.assertEqual(b.horn, {'param': 'dynamics', 'vibrato': True, 'glide': 0.2})
            self.assertEqual([f.params['width'] for f in b.piano.fx if f.type == 'width'], [jazz.PIANO_WIDTH['other']])
            self.assertEqual(b.kit, jazz.GM_BRUSH)

    def test_modes(self):
        with samples(['meatbass']):
            s = Song('t', tempo=120)
            s.section('a', bars=1)
            b = jazz.band(s, sampled_sounds=False)
            self.assertEqual(b.bass.instrument.type, 'sf2')
            with self.assertRaisesRegex(ComposeError, 'samples fetch salamander-grand'):
                jazz.band(Song('u', tempo=120), sampled_sounds=True)
            with self.assertRaisesRegex(ComposeError, 'sampled_sounds'):
                jazz.band(Song('v', tempo=120), sampled_sounds='yes')

    @unittest.skipUnless(installed('salamander-grand', 'meatbass', 'swirly-drums', 'mtg-solo-sax'),
                         'needs the jazz sample packs (AGENTSOUND_SAMPLES)')
    def test_sampled_band_compiles(self):
        s = Song('t', tempo=138, key='F major')
        a = s.section('a', bars=2)
        b = jazz.band(s, sax=True)
        prog = s.prog('Fmaj7:0.5 D7:0.5 | Gm7:0.5 C7:0.5')
        b.comp.play(jazz.comp(prog, seed=1), a)
        b.bass.play(jazz.walking_bass(prog, key=s.key, seed=1), a)
        b.drums.play(jb.brushes(b, 2, seed=1), a)
        jazz.horn_line(Clip([(0, 2, 'A4', 90), (2, 2, 'C5', 90)], length=8), s.tempo, **b.horn).place(b.sax, a)
        d = s.compile()
        sax = next(t for t in d['tracks'] if t['id'] == 'sax')
        self.assertIn('instrument.dynamics', [x['target'] for x in sax['automation']])


class DemoSongs(unittest.TestCase):
    def test_demos_compile(self):
        for name in PRESETS:
            with self.subTest(name):
                path = REPO / 'songs' / '_bands' / name / 'song.py'
                spec = importlib.util.spec_from_file_location(f'demo_{name}', path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                self.assertEqual(mod.ANALYSIS, {'profile': 'jazz'})
                s = mod.build()
                s.compile()
                self.assertFalse([w for w in s.warnings if 'no notes' in w or 'dropped' in w])


if __name__ == '__main__':
    unittest.main()
