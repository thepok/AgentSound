import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound.automation import (JUMP, exp_ramp, fade, hold, lfo, normalize, per_section, ramp, riser, steps,
                                   swell)
from agentsound.theory import ComposeError


def increasing(points):
    return all(b[0] > a[0] for a, b in zip(points, points[1:]))


class Generators(unittest.TestCase):
    def test_ramps(self):
        self.assertEqual(ramp(0, 8, 0.0, 1.0), [(0.0, 0.0), (8.0, 1.0, 'linear')])
        self.assertEqual(exp_ramp(4, 12, 200, 8000), [(4.0, 200), (12.0, 8000, 'exp')])
        with self.assertRaises(ComposeError):
            exp_ramp(0, 4, 0, 100)
        with self.assertRaises(ComposeError):
            ramp(4, 4, 0, 1)
        self.assertEqual(fade(0, 16, -60, 0)[-1], (16.0, 0, 'linear'))
        self.assertEqual(hold(4, 8, 3.0), [(4.0, 3.0, 'step'), (8.0, 3.0)])
        self.assertEqual(steps({8: 1, 0: 0}), [(0.0, 0, 'step'), (8.0, 1, 'step')])

    def test_swell_and_riser(self):
        s = swell(0, 8, 0.1, 0.9)
        self.assertEqual([p[1] for p in s], [0.1, 0.9, 0.1])
        r = riser(32, 8, lo=200, hi=12000)
        self.assertEqual(r, [(24.0, 200), (32.0, 12000, 'exp')])
        rr = riser(32, 8, lo=20, hi=800, reset=20)
        self.assertEqual(rr[-1], (32.0, 20, 'step'))
        self.assertAlmostEqual(rr[-2][0], 32 - JUMP)
        with self.assertRaises(ComposeError):
            riser(4, 8)

    def test_per_section(self):
        class S:
            def __init__(self, start):
                self.start = start
        a, b, c = S(0), S(32), S(64)
        self.assertEqual(per_section({b: 0.5, a: 0.2}), [(0.0, 0.2), (32.0, 0.5, 'step')])
        g = per_section({a: 0.2, b: 0.5, c: 0.9}, glide=4)
        self.assertEqual(g, [(0.0, 0.2), (28.0, 0.2), (32.0, 0.5, 'smooth'), (60.0, 0.5), (64.0, 0.9, 'smooth')])

    def test_lfo_shapes(self):
        for shape in ('sine', 'tri', 'saw', 'saw_down', 'square'):
            pts = normalize(lfo(0, 8, 200, 2000, period=1, shape=shape, log=shape != 'square'), shape)
            self.assertTrue(increasing(pts), shape)
            self.assertTrue(all(199.999 <= p[1] <= 2000.001 for p in pts), shape)
            self.assertAlmostEqual(pts[0][0], 0.0)
            self.assertGreaterEqual(pts[-1][0], 7.0)
        sine = lfo(0, 1, 0, 1, period=1, res=4)
        self.assertEqual([round(p[1], 6) for p in sine], [0.0, 0.5, 1.0, 0.5, 0.0])
        sq = lfo(0, 2, 0, 1, period=1, shape='square')
        self.assertEqual([(p[0], p[1]) for p in sq], [(0.0, 1.0), (0.5, 0.0), (1.0, 1.0), (1.5, 0.0)])
        with self.assertRaises(ComposeError):
            lfo(0, 4, 0, 1, shape='wobbly')


class Normalize(unittest.TestCase):
    def test_sorted_and_formatted(self):
        pts = normalize([(8, 1.0, 'smooth'), (0, 0.0), (4, 0.5)])
        self.assertEqual(pts, [[0.0, 0.0], [4.0, 0.5], [8.0, 1.0, 'smooth']])

    def test_same_beat_becomes_jump(self):
        pts = normalize(ramp(0, 32, 400, 6000, 'exp') + ramp(32, 40, 800, 8000, 'exp'))
        self.assertTrue(increasing(pts))
        self.assertEqual(pts[1], [32 - JUMP, 6000.0, 'exp'])
        self.assertEqual(pts[2], [32.0, 800.0, 'step'])
        self.assertEqual(pts[3], [40.0, 8000.0, 'exp'])
        dup = normalize([(0, 1.0), (0, 1.0), (4, 2.0)])
        self.assertEqual(dup, [[0.0, 1.0], [4.0, 2.0]])
        at_zero = normalize([(0, 1.0), (0, 2.0)])
        self.assertEqual(at_zero, [[0.0, 2.0, 'step']])

    def test_errors(self):
        for bad in ([(0, 1, 'cubic')], [(-1, 1)], [(0, float('nan'))], [(0,)], [('a', 1)]):
            with self.assertRaises(ComposeError, msg=repr(bad)):
                normalize(bad)
        with self.assertRaises(ComposeError):
            normalize([(0, 0.0), (4, 100.0, 'exp')])


if __name__ == '__main__':
    unittest.main()
