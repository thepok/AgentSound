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

    def test_swing_moves_a_rolled_chord_whole(self):
        # the lower voices of a roll (a few ms before the off-beat 8th) are swung with the top note
        roll = Clip([(0.47, 0.5, 60), (0.49, 0.5, 64), (0.5, 0.5, 67), (1.0, 0.5, 69)], length=2)
        g = groove(roll, Groove('sw', swing=0.6, grid='1/8'), bpm=120)
        self.assertEqual([round(n.start, 3) for n in g], [0.57, 0.59, 0.6, 1.0])
        lone = groove(Clip([(0.4, 0.5, 60)], length=1), Groove('sw', swing=0.6, grid='1/8'), bpm=120)
        self.assertEqual(lone[0].start, 0.4)                      # nothing on the line: not a roll

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

    def test_touch_levels_move_whole_phrases(self):
        # levels=[(beat, shift)]: each phrase (split at rests) moves by the shift in force at its first note
        ph = [(0, 0.5, 72, 80), (0.5, 0.5, 74, 80), (1, 1, 76, 80)]
        line = Clip(ph + [(t + 4, d, p, v) for t, d, p, v in ph] + [(t + 8, d, p, v) for t, d, p, v in ph], length=12)
        flat = {(n.start, n.pitch): n.vel for n in touch(line, 50, 100)}
        moved = {(n.start, n.pitch): n.vel for n in touch(line, 50, 100, levels=[(3.5, -10), (7.5, 0)])}
        for t, d, p, _ in ph:
            self.assertEqual(moved[(t, p)], flat[(t, p)])                  # before the first step: as written
            self.assertEqual(moved[(t + 4, p)], flat[(t + 4, p)] - 10)     # the quiet phrase
            self.assertEqual(moved[(t + 8, p)], flat[(t + 8, p)])
        with self.assertRaises(ComposeError):
            touch(line, 50, 100, levels=[(0, 60)])

    def test_touch_follows_the_contour_not_the_beat(self):
        # a long 8th-note line up and down by steps: no on-beat accent, no loud / soft zig-zag, small neighbour steps
        ps = [60, 62, 64, 65, 67, 69, 71, 72, 74, 72, 71, 69, 67, 65, 64, 62] * 2
        line = Clip([(i * 0.5, 0.5, p, 80) for i, p in enumerate(ps)], length=16)
        vs = [n.vel for n in sorted(touch(line, 50, 100), key=lambda n: n.start)]
        on, off = vs[0::2], vs[1::2]
        self.assertLess(abs(sum(on) / len(on) - sum(off) / len(off)), 3.0)
        ds = [b - a for a, b in zip(vs, vs[1:])]
        self.assertLess(sum(1 for a, b in zip(ds, ds[1:]) if a * b < 0) / (len(ds) - 1), 0.6)
        self.assertLessEqual(max(abs(d) for i, d in enumerate(ds) if i + 1 != 8), 15)   # the summit (8) may stand out

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


def phrase_line():
    """Two phrases of 8ths (a rise to a loud middle and back), a rest between, then a held end before beat 16."""
    a = [(i * 0.5, 0.45, 60 + (i % 5), 70 + 2 * min(i, 12 - i)) for i in range(13)]
    b = [(8 + i * 0.5, 0.45, 62 + (i % 4) + (12 if i == 6 else 0), 72 + 2 * min(i, 10 - i)) for i in range(11)]
    return Clip(a + b + [(13.5, 2.0, 67, 70)], length=16)


class Body(unittest.TestCase):
    def test_profiles_and_strict(self):
        from agentsound.humanize import BODIES, body_profile
        self.assertEqual(set(BODIES), {'calm', 'lyrical', 'swing', 'waltz', 'none'})
        self.assertIsNone(body_profile('none'))
        with self.assertRaises(ComposeError):
            body_profile('wobbly')

    def test_gesture_bounded_coupled_deterministic(self):
        from agentsound.humanize import BODY_MAX_MS, body, body_metrics, gesture
        c = phrase_line()
        for name in ('calm', 'lyrical', 'swing'):
            plan, mo = gesture(c, name, 100, ends=[16])
            notes = list(c)
            for (ms, f), n in zip(plan, notes):
                rit = n.start >= 12.0                       # the final ritardando may add to the late side
                self.assertLessEqual(ms, BODY_MAX_MS + (120 if rit else 0) + 1e-6)
                self.assertGreaterEqual(ms, -BODY_MAX_MS - 1e-6)
                self.assertTrue(0.8 < f < 1.2)
            played = [n._replace(start=n.start + ms / 1000 * 100 / 60, vel=n.vel * f) for n, (ms, f) in zip(notes, plan)]
            m = body_metrics(notes, played, lambda b_: b_ * 0.6, [16])
            self.assertGreater(m['coupling']['note'], 0.2, name)        # faster where louder (Todd)
            self.assertGreater(m['rit']['late_ms'], 10, name)           # it slows into the section end
            starts = [n.start for n in sorted(played, key=lambda n: n.start)]
            self.assertEqual(starts, sorted(starts))
        self.assertEqual(body(c, 'lyrical', 100, seed=3), body(c, 'lyrical', 100, seed=3))
        self.assertNotEqual(body(c, 'lyrical', 100, seed=3), body(c, 'lyrical', 100, seed=4))

    def test_rit_curve_fit_and_leap(self):
        from agentsound.humanize import fit_rit, leap_delay_ms, rit_curve
        xs = [i / 10 for i in range(11)]
        w, q, rms = fit_rit(xs, [rit_curve(x, 0.6, 2.5) for x in xs])
        self.assertAlmostEqual(w, 0.6, places=2)
        self.assertAlmostEqual(q, 2.5, places=2)
        self.assertEqual(leap_delay_ms(4, 2.0, 25), 0.0)
        self.assertEqual(leap_delay_ms(-12, 2.0, 25), 16.0)
        self.assertEqual(leap_delay_ms(24, 2.0, 25), 25.0)

    def test_follower_moves_with_the_lead(self):
        from agentsound.humanize import follow_plan, gesture
        c = phrase_line()
        plan, mo = gesture(c, 'lyrical', 100, ends=[16])
        lead = {round(n.start, 3): ms for n, (ms, _) in zip(list(c), plan)}
        lh = Clip([(0, 2, 48, 60), (2, 2, 50, 60), (8, 2, 43, 60), (9, 1, 45, 60)], length=16)
        fp = follow_plan(lh, mo, 'lyrical', 100)
        for n, (ms, f) in zip(list(lh), fp):
            if round(n.start, 3) in lead:                    # struck together: moved together
                self.assertAlmostEqual(ms, lead[round(n.start, 3)])

    def test_track_body_at_compile(self):
        from agentsound.patches import inst
        from agentsound.song import Song
        s = Song('t', tempo=100, seed=1)
        s.section('a', bars=4)
        rh = s.track('piano', inst.va()).humanize(body='lyrical')
        lh = s.track('comp', inst.va()).humanize(body='lyrical', lead='piano')
        rh.play(phrase_line(), 0)
        lh.play(Clip([(0, 2, 48, 60), (8, 2, 43, 60)], length=16), 0)
        r = s.compile()
        self.assertEqual(r, s.compile())                     # deterministic
        with self.assertRaises(ComposeError):
            s.track('x', inst.va()).humanize(lead='piano')   # a lead needs a body
        s2 = Song('t', tempo=100, seed=1)
        s2.section('a', bars=4)
        s2.track('comp', inst.va()).humanize(body='calm', lead='nobody').play(Clip([(0, 1, 48, 60)]), 0)
        with self.assertRaises(ComposeError):
            s2.compile()


if __name__ == '__main__':
    unittest.main()
