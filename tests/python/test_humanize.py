import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound.humanize import (GROOVES, Groove, accent, bass_touch, crescendo, groove, humanize, jitter, swing,
                                 touch, vel_jitter)
from agentsound.patterns import Clip, drums
from agentsound.theory import ComposeError


def sixteenths(n=16, pitch=60, vel=100):
    return Clip([(i * 0.25, 0.25, pitch, vel) for i in range(n)], length=n * 0.25)


class Humanize(unittest.TestCase):
    def test_deterministic_by_seed(self):
        c = sixteenths(64)
        a = humanize(c, timing_ms=6, vel=8, bpm=120, seed=11)
        b = humanize(c, timing_ms=6, vel=8, bpm=120, seed=11)
        d = humanize(c, timing_ms=6, vel=8, bpm=120, seed=12)
        self.assertEqual(a, b)
        self.assertNotEqual(a, d)
        self.assertEqual(humanize(c, seed='verse-hats'), humanize(c, seed='verse-hats'))

    def test_bounds(self):
        c = sixteenths(200)
        max_beats = 6 / 1000 * 120 / 60
        j = jitter(c, ms=6, bpm=120, seed=1)
        offs = [x.start - y.start for x, y in zip(sorted(j, key=lambda n: n.vel), c)]  # same order: vel equal
        self.assertTrue(all(abs(o) <= max_beats + 1e-9 for o in offs))
        self.assertTrue(any(abs(o) > 1e-6 for o in offs))
        v = vel_jitter(c, amount=8, seed=1)
        self.assertTrue(all(92 <= n.vel <= 108 for n in v))
        self.assertEqual(len(v), len(c))
        self.assertEqual(humanize(c, timing_ms=0, vel=0), c)


class SwingAndGroove(unittest.TestCase):
    def test_swing_16ths(self):
        s = swing(sixteenths(8), 0.6, '1/16')
        starts = [n.start for n in s]
        self.assertEqual(starts[0::2], [0.0, 0.5, 1.0, 1.5])
        for k, st in enumerate(starts[1::2]):
            self.assertAlmostEqual(st, 0.25 + 0.5 * k + 0.05)
        self.assertAlmostEqual(s[1].dur, 0.2)
        self.assertEqual(swing(sixteenths(4), 58), swing(sixteenths(4), 0.58))
        with self.assertRaises(ComposeError):
            swing(sixteenths(4), 0.9)

    def test_laidback_groove_on_drums(self):
        beat = drums({'kick': 'x...x...', 'snare': '....x...', 'hat': 'x.x.x.x.'})
        g = groove(beat, 'laidback', bpm=100, drums=True)
        late = 9 / 1000 * 100 / 60
        sn = [n for n in g if n.pitch == 38]
        self.assertAlmostEqual(sn[0].start, 1.0 + late)
        kicks = [n for n in g if n.pitch == 36]
        self.assertEqual([k.start for k in kicks], [0.0, 1.0])
        hats = [n for n in g if n.pitch == 42]
        self.assertGreater(hats[0].vel, hats[1].vel)   # 16th-slot velocity accents

    def test_groove_on_melodic_track_shifts_all(self):
        c = Clip([(0, 1, 60), (1, 1, 62)], length=2)
        g = groove(c, 'laidback', bpm=120)
        self.assertAlmostEqual(g[0].start, 4 / 1000 * 2)
        straight = groove(c, 'straight', bpm=120)
        self.assertEqual(straight, c)
        custom = Groove('mine', swing=0.66, grid='1/8')
        self.assertAlmostEqual(groove(Clip([(0.5, 0.5, 60)], length=1), custom)[0].start, 0.66)
        with self.assertRaises(ComposeError):
            groove(c, 'nope')
        self.assertIn('synthwave', GROOVES)


class Dynamics(unittest.TestCase):
    def test_crescendo(self):
        c = crescendo(sixteenths(16, vel=100), 0.5, 1.0)
        vels = [n.vel for n in c]
        self.assertEqual(vels, sorted(vels))
        self.assertEqual(vels[0], 50)
        self.assertGreater(vels[-1], 90)
        d = crescendo(sixteenths(16, vel=100), 1.0, 0.4)
        self.assertEqual([n.vel for n in d], sorted([n.vel for n in d], reverse=True))

    def test_accent(self):
        a = accent(sixteenths(8, vel=100), every=1.0, amount=1.2)
        self.assertEqual([n.vel for n in a], [120, 100, 100, 100, 120, 100, 100, 100])

    def test_touch_shapes_a_flat_line(self):
        # a flat-velocity phrase rising to a held top note (on 3) and falling back, then a rest and a lower phrase
        line = Clip([(1, 0.5, 72, 80), (1.5, 0.5, 75, 80), (2, 1.5, 79, 80), (3.5, 0.5, 77, 80), (4, 1, 75, 80),
                     (5, 1, 72, 80), (6.5, 0.1, 71, 80), (6.6, 1.4, 72, 80), (8, 0.5, 67, 80), (8, 0.5, 79, 80)],
                    length=12)
        t = touch(line, 50, 110)
        v = {(n.start, n.pitch): n.vel for n in t}
        self.assertEqual(v[(2, 79)], 110)                          # the summit gets hi
        self.assertLess(v[(1, 72)], v[(1.5, 75)])                  # rises into it ...
        self.assertLess(v[(1.5, 75)], v[(2, 79)])
        self.assertLess(v[(5, 72)], v[(4, 75)])                    # ... and relaxes after it
        self.assertLess(v[(6.5, 71)], 0.7 * v[(6.6, 72)])          # a grace note leans on its target
        self.assertLess(v[(8, 67)], v[(8, 79)])                    # the top of a chord / octave is voiced
        self.assertGreaterEqual(max(v.values()) - min(v.values()), 40)
        self.assertEqual(len(t), len(line))
        with self.assertRaises(ComposeError):
            touch(line, 100, 60)

    def test_bass_touch_shapes_a_flat_bass_line(self):
        # 8 bars of a straight two-feel line at one velocity: root on 1, fifth on 3, an 8th pickup on the & of 4
        # a half step under the next root, one anticipation pushed over a bar line, one short ghost
        notes = []
        for bar in range(8):
            t = bar * 4
            notes += [(t, 1.9, 36, 80), (t + 2, 1.4, 43, 80), (t + 3.5, 0.45, 37 if bar % 2 else 42, 80)]
        notes[-1] = (31.5, 0.9, 41, 80)                                       # tied over the last bar line
        notes.append((13.75, 0.2, 43, 80))                                    # a ghosted skip note
        line = Clip(notes, length=32)
        t = bass_touch(line, 60, 100, seed=1)
        self.assertEqual(t, bass_touch(line, 60, 100, seed=1))                # seeded
        self.assertEqual([(n.start, n.pitch) for n in sorted(t)], [(n.start, n.pitch) for n in sorted(line)])
        v = {(n.start, n.pitch): n.vel for n in t}
        self.assertLess(v[(0, 36)], v[(8, 36)])                               # the 4-bar arc swells ...
        self.assertLess(v[(12, 36)], v[(8, 36)])                              # ... and relaxes
        self.assertLess(v[(10, 43)], v[(8, 36)])                              # beat 3 answers beat 1
        self.assertLess(v[(11.5, 42)], v[(10, 43)])                           # the pickup 8th is lighter
        flat = {(n.start, n.pitch): n.vel for n in bass_touch(line, 60, 100, approach=1.0, seed=1)}
        self.assertLess(v[(7.5, 37)], flat[(7.5, 37)])                        # a chromatic approach is lighter
        self.assertEqual(v[(11.5, 42)], flat[(11.5, 42)])                     # (a leap into the root is not one)
        self.assertLess(v[(13.75, 43)], 0.7 * v[(12, 36)])                    # ghosts stay ghosts
        self.assertGreater(v[(31.5, 41)], v[(30, 43)] * 0.9)                  # the anticipation leans in
        vs = [n.vel for n in t]
        self.assertGreaterEqual(max(vs) - min(vs), 30)
        self.assertLessEqual(max(vs), 108)
        for bad in (dict(lo=100, hi=60), dict(accent='3-4'), dict(ghost=5), dict(phrase=0), dict(peak=2)):
            with self.assertRaises(ComposeError):
                kw = dict(lo=60, hi=100)
                kw.update(bad)
                bass_touch(line, **kw)


if __name__ == '__main__':
    unittest.main()
