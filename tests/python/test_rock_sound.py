"""The rock pass (songs/the-drummer-speaks/ROCK.md): the library's one guitar amp (sampled_guitars.amp, the cab/*
chains on the engine's tube 'amp'), the bass rig (DI + amp blend), the palm mute emulation, Big Rusty's velocity
calibration (kits.velocity_map), and the riff player / double-tracked wall (agentsound/guitar_riff.py). Pure Python:
no samples or engine needed."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Song, guitarist as gtr, kits, patches  # noqa: E402
from agentsound import articulation as art  # noqa: E402
from agentsound import guitar_riff  # noqa: E402
from agentsound.bandlib import rock  # noqa: E402
from agentsound.patches import Instrument, sampled_drums, sampled_guitars as sg, space_ir  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

SPEC = 'E> - . E . . G> - - . A - G E - . | D> - . B - . A - . . E . G A# B> -'


class Amp(unittest.TestCase):
    def test_cab_patches_are_amp_chains(self):
        for kind, cab in space_ir.CABS.items():
            p = patches.get(cab)
            with self.subTest(cab=cab):
                self.assertEqual([f.type for f in p.fx], ['amp', 'convolver', 'eq'])
                self.assertNotIn('saturator', [f.type for f in p.fx])

    def test_amp_helper(self):
        for kind in sg.AMPS:
            ch = sg.amp(kind)
            with self.subTest(kind=kind):
                self.assertEqual([f.type for f in ch], ['amp', 'convolver', 'eq'])
                self.assertEqual(ch[0].name, 'amp')
                self.assertAlmostEqual(ch[0].params['output'], space_ir.AMP_OUTPUT[kind] + sg.AMP_TRIM[kind])
        ch = sg.amp('crunch', gain=7.5, cab='cab/rock_4x12', mic={'hp.freq': 70, 'lp.freq': 5000})
        self.assertEqual(ch[0].params['gain'], 7.5)
        self.assertEqual(ch[1].params['ir'], patches.get('cab/rock_4x12').fx[1].params['ir'])
        self.assertEqual(ch[2].params, {'hp.freq': 70, 'lp.freq': 5000})
        with self.assertRaises(ComposeError):
            sg.amp('fuzzbox')
        with self.assertRaises(ComposeError):
            sg.amp('rock', cab='bus/ir_hall')
        self.assertIs(rock.amp, sg.amp)                  # one amp for the library: the band presets use it

    def test_no_guitar_on_the_old_waveshaper_amp(self):
        """Every amped DI patch and the heroes run the tube amp; no saturator 'amp' is left in a guitar chain."""
        for n in ('rock_guitar', 'crunch_guitar', 'metal_guitar', 'blues_guitar', 'jangle_guitar', 'lead_guitar',
                  'archtop_electric'):
            p = patches.get(f'sampled/{n}')
            with self.subTest(patch=n):
                types = [f.type for f in p.fx]
                self.assertIn('amp', types)
                self.assertNotIn('saturator', types)
        for name in ('layered/hero_guitar', 'layered/hero_guitar_heavy'):
            st = patches.get(name).instrument
            zones = [x for x in st.params['layers'] if x.id.startswith('z')]
            for x in zones:
                with self.subTest(patch=name, zone=x.id):
                    types = [f.type for f in x.fx]
                    self.assertIn('amp', types)
                    self.assertNotIn('saturator', types)
        clean = patches.get('sampled/hero_guitar_clean')
        self.assertIn('amp', [f.type for f in clean.fx])

    def test_bass_rig(self):
        ch = sg.bass_rig()
        self.assertEqual([f.type for f in ch], ['amp', 'eq'])
        self.assertEqual(ch[0].params['mix'], 0.35)
        self.assertGreaterEqual(ch[0].params['tight'], 150)       # the amp side carries no lows: the DI does
        self.assertEqual(sg.bass_rig(mix=0.6, gain=5.0)[0].params['gain'], 5.0)
        s = Song('t', tempo=120)
        s.section('a', bars=1)
        try:
            b = rock.rock_band(s, without=('keys', 'lead'))
        except ComposeError as e:
            self.skipTest(f'rock_band packs missing: {e}')
        types = [f.type for f in b.bass.fx]                 # eq -> the rig -> compressor (no saturator)
        self.assertIn('amp', types)
        self.assertNotIn('saturator', types)
        names = [f.name for f in b.drums.fx]
        self.assertIn('punch', names)
        self.assertEqual([f.name for f in s.buses['drum_bus'].fx][:2], ['crush', 'tape'])
        self.assertIn('room_crush', [f.name for f in s.buses['room'].fx])


class PalmMute(unittest.TestCase):
    def test_one_palm_emulation(self):
        self.assertEqual({k: v for k, v in rock.GUITAR_ARTICULATIONS['palm mute'].items() if k != 'gain'}, sg.PALM)
        p = sg.PALM
        self.assertLess(p['cutoff'], 1000)            # the thump stays, the upper partials go
        self.assertLessEqual(p['decay'], 0.3)          # short: through a high-gain amp ~100 ms flat, then the cut
        self.assertEqual(p['sustain'], 0.0)
        self.assertGreater(p['filterEnv'][0], 0)       # the pick opens the filter


class VelocityMap(unittest.TestCase):
    def _ins(self):
        z = [{'file': 'x.wav', 'lo': 38, 'hi': 38, 'vello': 0, 'velhi': 13, 'gain': -6.0,
              'velcurve': [[1, 0.4], [13, 1.0]]},
             {'file': 'y.wav', 'lo': 38, 'hi': 38, 'vello': 14, 'velhi': 25, 'gain': -4.0,
              'velcurve': [[14, 0.4], [25, 1.0]]},
             {'file': 'k.wav', 'lo': 36, 'hi': 36, 'vello': 0, 'velhi': 127, 'gain': 0.0},
             {'file': 'n.wav', 'lo': 45, 'hi': 45, 'vello': 0, 'velhi': 127, 'gain': 1.0}]
        return Instrument('sampler', {'samples': z})

    def test_relevels_layers(self):
        ins = kits.velocity_map(self._ins(), {38: [(1, 2.0), (13, 0.0), (14, -2.0), (25, -2.0)], 45: [(1, -4), (127, -2)]})
        z = ins.params['samples']
        self.assertAlmostEqual(z[0]['gain'], -6.0)                  # correction at velhi 13 = 0
        self.assertAlmostEqual(z[0]['velcurve'][0][1], round(0.4 * 10 ** (2 / 20), 6))   # the layer's low end +2 dB
        self.assertAlmostEqual(z[1]['gain'], -6.0)                  # -2 dB at its velhi
        self.assertAlmostEqual(z[1]['velcurve'][0][1], 0.4)        # flat correction inside the layer
        self.assertEqual(z[2]['gain'], 0.0)                         # an unmapped key is untouched
        self.assertAlmostEqual(z[3]['gain'], 1.0 - 3.0)             # no velcurve: the mean of its two edges
        with self.assertRaises(ComposeError):
            kits.velocity_map(self._ins(), {38: [(200, 1.0)]})

    def test_big_rusty_table(self):
        t = sampled_drums.BIG_RUSTY_VELOCITY
        self.assertEqual(set(t), {38, 41, 43, 45, 47, 48, 50})
        for k, pts in t.items():
            with self.subTest(key=k):
                self.assertTrue(all(abs(d) <= 8 for _, d in pts))
        p = patches.get('sampled/big_rusty_kit')
        self.assertEqual(p.instrument.lazy['post'], ['agentsound.patches.sampled_drums:_rusty_levels'])


class Riff(unittest.TestCase):
    def test_parse(self):
        steps = guitar_riff.parse(SPEC)
        self.assertEqual(len(steps), 32)
        notes = [s for s in steps if s[0] == 'note']
        self.assertEqual([s[1] for s in notes][:4], [40, 40, 43, 45])      # E2 E2 G2 A2: on the low string
        self.assertEqual(notes[0][3], 1)                                    # 'E> -': held one step
        self.assertIn('>', notes[0][2])
        self.assertEqual(guitar_riff.parse('D', tuning='drop_d')[0][1], 38)  # drop D: the open D2
        self.assertEqual(guitar_riff.parse('C3')[0][1], 48)
        for bad in ('', '- E', 'H', 'E>q'):
            with self.assertRaises(ComposeError):
                guitar_riff.parse(bad)

    def test_energy_mapping(self):
        quiet = gtr.riff(SPEC, bpm=116, energy=0.4, grid='1/16')
        drive = gtr.riff(SPEC, bpm=116, energy=0.62, grid='1/16')
        loud = gtr.riff(SPEC, bpm=116, energy=0.9, grid='1/16')
        palm = lambda r: sum(1 for n in r.clip if art.articulation_of(n) == 'palm')
        # verse: single notes, nearly all palm-muted; pre: power chords, short ones chugged; chorus: power + octave
        self.assertEqual(len(quiet.clip), 13)          # one string per step
        self.assertGreaterEqual(palm(quiet), 12)
        self.assertEqual(max(len({n.pitch for n in quiet.clip if abs(n.start - x.start) < 0.05}) for x in quiet.clip), 1)
        self.assertGreater(len(drive.clip), len(quiet.clip))
        self.assertGreater(palm(drive), 0)
        self.assertEqual(palm(loud), 0)
        self.assertIn(52, {n.pitch for n in loud.clip})                     # the octave on top of E2
        self.assertGreater(min(n.vel for n in loud.clip if n.start < 0.05), max(n.vel for n in quiet.clip if n.start < 0.05))
        self.assertEqual(gtr.riff(SPEC, bpm=116, section='verse').energy, 0.45)
        self.assertIn('quiet single', [m[3] for m in quiet.moves])

    def test_marks_win(self):
        r = gtr.riff('E! - - - Ap G^', bpm=120, energy=0.4)
        arts = [(n.pitch, art.articulation_of(n)) for n in r.clip]
        self.assertIn((40, None), arts)            # '!' rings open even in a quiet verse
        self.assertIn((45, 'palm'), arts)
        self.assertIn('dead', [a for _, a in arts])   # '^': the hit is choked (a dead scratch where it stops)

    def test_take_and_cell(self):
        r = gtr.riff(SPEC, bpm=116, energy=0.9, grid='1/16', seed=3)
        t2 = r.take(2)
        self.assertEqual([n.pitch for n in r.clip], [n.pitch for n in t2.clip])
        self.assertNotEqual([n.start for n in r.clip], [n.start for n in t2.clip])
        self.assertEqual(r.cell('1/16'), 'x..x..x...x.xx..x..x..x...x.xxx.')
        self.assertEqual(gtr.cell(r.clip, '1/8'), r.cell('1/8'))

    def test_length_loops_and_fills(self):
        r = gtr.riff(SPEC, bpm=116, energy=0.62, grid='1/16', length=16, end='choke')
        self.assertEqual(r.clip.length, 16)
        self.assertIn((15.0, 16.0, 'fill', 'choke'), r.moves)
        mem = gtr.Memory()
        r1 = gtr.riff(SPEC, bpm=116, section='verse', length=16, into='chorus', memory=mem, seed=5, at=0)
        self.assertTrue(any(m[2] == 'fill' for m in r1.moves))
        # a second fill right after is over the budget (one per 4 bars)
        r2 = gtr.riff(SPEC, bpm=116, section='verse', length=4, end='slide', memory=mem, at=16)
        self.assertTrue(any(m[2] == 'dropped' for m in r2.moves))
        with self.assertRaises(ComposeError):
            gtr.riff(SPEC, bpm=116, end='explode')
        with self.assertRaises(ComposeError):
            gtr.riff(SPEC, bpm=116, kind='seventh')

    def test_vocabulary(self):
        spec = gtr.pedal(['G', 'A', 'B'], rhythm='PPM', bars=1)
        self.assertEqual(spec, 'Ep Ep G> Ep Ep A> Ep Ep')
        h = gtr.hits('x..x..X.', 'E', 120, grid='1/8')
        starts = sorted({round(n.start, 1) for n in h if art.articulation_of(n) != 'dead'})
        self.assertEqual(starts, [0.0, 1.5, 3.0])
        self.assertEqual(sum(1 for n in h if art.articulation_of(n) == 'dead'), 2)   # the 'x' stops are choked
        bu = gtr.build_up('E', 4, 120)
        v = [n.vel for n in sorted(bu, key=lambda n: n.start) if n.pitch == 40]
        self.assertLess(v[0], v[-1])                                             # crescendo
        self.assertEqual(art.articulation_of(sorted(bu, key=lambda n: n.start)[-1]), None)   # the last one opens
        with self.assertRaises(ComposeError):
            gtr.hits('x?x', 'E', 120)


class Double(unittest.TestCase):
    def test_two_takes(self):
        s = Song('d', tempo=116)
        sec = s.section('a', bars=4)
        a = s.track('gtr_l', 'synthwave/arp_pluck')
        b = s.track('gtr_r', 'synthwave/arp_pluck')
        r = gtr.riff(SPEC, bpm=116, energy=0.9, grid='1/16', length=16)
        out = gtr.double(r, (a, b), sec, seed=1)
        ca, cb = out[0][1], out[1][1]
        self.assertEqual([n.pitch for n in ca], [n.pitch for n in cb])
        d = [abs(x.start - y.start) * 60 / 116 * 1000 for x, y in zip(ca, cb)]
        self.assertGreater(max(d), 3.0)              # two performances, not a copy
        self.assertLess(max(d), 40.0)                # but tight: a few ms apart
        self.assertGreater(len({round(x, 1) for x in d}), 5)   # drifting, not a fixed offset
        lanes = {t.id: [tgt for tgt, _ in t._auto] for t in (a, b)}
        self.assertIn('instrument.pitchbend', lanes['gtr_l'])
        pa = dict(a._auto)['instrument.pitchbend']
        pb = dict(b._auto)['instrument.pitchbend']
        self.assertNotEqual(pa[0][1], pb[0][1])       # tuned differently
        self.assertTrue(all(abs(p[1]) <= 0.08 for p in pa + pb))   # a few cents
        with self.assertRaises(ComposeError):
            gtr.double(r, (a,), 0)


if __name__ == '__main__':
    unittest.main()
