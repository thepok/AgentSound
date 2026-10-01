import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound.patterns import (Clip, Motif, Note, arp, bassline, beats, chords, crash, drums, euclid, grid,
                                 melody, snare_roll, tom_fill)
from agentsound.theory import ComposeError, Key, Progression


class Durations(unittest.TestCase):
    def test_note_values(self):
        self.assertEqual(beats('1/16'), 0.25)
        self.assertEqual(beats('1/4'), 1.0)
        self.assertEqual(beats('1/2'), 2.0)
        self.assertEqual(beats('3/8'), 1.5)
        self.assertAlmostEqual(beats('1/8t'), 1 / 3)
        self.assertEqual(beats('1/8.'), 0.75)
        self.assertEqual(beats(0.5), 0.5)
        self.assertEqual(beats('2'), 2.0)
        for bad in ('eighth', '1/0', -1, True, None):
            with self.assertRaises(ComposeError, msg=repr(bad)):
                beats(bad)


class DrumGrids(unittest.TestCase):
    def test_basic_grid(self):
        c = drums({'kick': 'x...x...', 'snare': '....X...', 'hat': 'o.o.o.o.'})
        self.assertEqual(c.length, 2.0)
        kick = [n for n in c if n.pitch == 36]
        self.assertEqual([n.start for n in kick], [0.0, 1.0])
        self.assertEqual([n.vel for n in kick], [100, 100])
        snare = [n for n in c if n.pitch == 38]
        self.assertEqual([(n.start, n.vel) for n in snare], [(1.0, 118)])
        hats = [n for n in c if n.pitch == 42]
        self.assertEqual([n.start for n in hats], [0.0, 0.5, 1.0, 1.5])
        self.assertTrue(all(n.vel == 62 for n in hats))
        self.assertTrue(all(n.dur == 0.25 for n in c))

    def test_tiling_bars_and_separators(self):
        c = drums({'kick': 'x... x... | x... x...', 'hat': '..x.'})
        self.assertEqual(c.length, 4.0)
        self.assertEqual([n.start for n in c if n.pitch == 42], [0.5, 1.5, 2.5, 3.5])
        c2 = drums({'kick': 'x...'}, bars=2)
        self.assertEqual(c2.length, 8.0)
        self.assertEqual(len(c2), 8)

    def test_multiline_and_numbers_and_levels(self):
        c = drums('''kick:  x.......
                     clap:  ....x...
                     46:    ......9.''', step='1/8')
        self.assertEqual(c.length, 4.0)
        self.assertEqual([(n.start, n.pitch) for n in c], [(0.0, 36), (2.0, 39), (3.0, 46)])
        self.assertEqual(c[2].vel, 126)
        loud = drums({'kick': 'x'}, vel=50)
        self.assertEqual(loud[0].vel, 50)

    def test_errors(self):
        with self.assertRaises(ComposeError):
            drums({'kick': 'x..y'})
        with self.assertRaises(ComposeError):
            drums({'kik': 'x...'})
        with self.assertRaises(ComposeError):
            drums('x...x...')

    def test_vel_is_a_percentage_not_a_ratio(self):
        # regression (songs/lamplight-avenue): drums(..., vel=0.8) played every hit at velocity 1
        for bad in (0.8, 1, 0, -50, 250, True, 'loud'):
            with self.assertRaises(ComposeError, msg=repr(bad)):
                drums({'kick': 'x...'}, vel=bad)
            with self.assertRaises(ComposeError, msg=repr(bad)):
                grid('x...', 'A2', vel=bad)
        with self.assertRaisesRegex(ComposeError, r'vel=80'):
            drums({'snare': '....x...'}, vel=0.8)
        self.assertEqual(drums({'kick': 'x'}, vel=80)[0].vel, 80)
        self.assertEqual(drums({'kick': 'X'}, vel=200)[0].vel, 127)
        for bad in (0.9, 0, 128):
            with self.assertRaises(ComposeError):
                crash(vel=bad)
        self.assertEqual(crash(vel=100)[0].vel, 100)

    def test_pitched_grid_ties(self):
        c = grid('x__.x...', 'A2', step='1/16', gate=1.0)
        self.assertEqual([(n.start, n.dur, n.pitch) for n in c], [(0.0, 0.75, 45), (1.0, 0.25, 45)])
        stab = grid('x.', ['A3', 'C4', 'E4'])
        self.assertEqual(stab.pitches, [57, 60, 64])


class Euclid(unittest.TestCase):
    def test_known_patterns(self):
        self.assertEqual(euclid(3, 8), 'x..x..x.')
        self.assertEqual(euclid(5, 8), 'x.xx.xx.')
        self.assertEqual(euclid(4, 16), 'x...x...x...x...')
        self.assertEqual(euclid(0, 4), '....')
        self.assertEqual(euclid(4, 4), 'xxxx')
        self.assertEqual(euclid(3, 8, rotate=1), '..x..x.x')

    def test_counts_and_spacing(self):
        for k in range(0, 17):
            p = euclid(k, 16)
            self.assertEqual(p.count('x'), k)
            if k:
                idx = [i for i, c in enumerate(p) if c == 'x']
                gaps = [(b - a) % 16 for a, b in zip(idx, idx[1:] + idx[:1])] if k > 1 else [16]
                self.assertLessEqual(max(gaps) - min(gaps), 1, p)
        with self.assertRaises(ComposeError):
            euclid(5, 4)


class Arps(unittest.TestCase):
    def test_up_down_updown(self):
        up = arp('Am', 'up', rate='1/16', register=(57, 76), length=4)
        self.assertEqual(len(up), 16)
        first = [n.pitch for n in up][:6]
        self.assertEqual(first[:3], sorted(first[:3]))
        self.assertEqual(first[3], first[0])
        tones = sorted(set(n.pitch for n in up))
        self.assertEqual({p % 12 for p in tones}, {9, 0, 4})
        down = arp('Am', 'down', register=(57, 76), length=1)
        dp = [n.pitch for n in down]
        self.assertEqual(dp[:3], sorted(dp[:3], reverse=True))
        self.assertEqual(dp[0], max(tones))
        ud = arp([57, 60, 64], 'updown', length=2)
        self.assertEqual([n.pitch for n in ud], [57, 60, 64, 60] * 2)

    def test_octaves_gate_pattern(self):
        a = arp([57, 60, 64], 'up', octaves=2, gate=0.5, length=2)
        self.assertEqual([n.pitch for n in a][:6], [57, 60, 64, 69, 72, 76])
        self.assertTrue(all(abs(n.dur - 0.125) < 1e-9 for n in a))
        p = arp([57, 60, 64], pattern=[0, 2, None, -1, 3], length=1.25)
        self.assertEqual([(n.start, n.pitch) for n in p], [(0.0, 57), (0.25, 64), (0.75, 52), (1.0, 69)])

    def test_accent_on_beats(self):
        a = arp([60, 64, 67], 'up', vel=100, accent=1.2, length=1)
        self.assertEqual([n.vel for n in a], [120, 100, 100, 100])

    def test_random_is_seeded(self):
        a = arp('Am', 'random', length=8, seed=5)
        b = arp('Am', 'random', length=8, seed=5)
        c = arp('Am', 'random', length=8, seed=6)
        self.assertEqual(a, b)
        self.assertNotEqual([n.pitch for n in a], [n.pitch for n in c])
        self.assertTrue(all(x.pitch != y.pitch for x, y in zip(a, list(a)[1:])))

    def test_over_progression(self):
        p = Progression('Am F C G')
        a = arp(p, 'up', rate='1/8')
        self.assertEqual(a.length, 16)
        self.assertEqual(len(a), 32)
        for n in a:
            self.assertIn(n.pitch % 12, p.at(n.start).pcs)
        with self.assertRaises(ComposeError):
            arp(p, 'sideways')


class Bass(unittest.TestCase):
    def test_octave_bass(self):
        b = bassline(Progression('Am F'), 'octave', rate='1/8')
        self.assertEqual(len(b), 16)
        ps = [n.pitch for n in b]
        self.assertEqual(ps[:4], [33, 45, 33, 45])
        self.assertEqual(ps[8:10], [29, 41])
        self.assertTrue(all(28 <= n.pitch <= 39 for n in b if n.start % 0.5 == 0 and ps.index(n.pitch) % 2 == 0))

    def test_styles(self):
        p = Progression('C/E G')
        root = bassline(p, 'root')
        self.assertEqual([(n.start, n.pitch) for n in root], [(0.0, 28), (4.0, 31)])
        off = bassline(p, 'offbeat')
        self.assertTrue(all(n.start % 1 == 0.5 for n in off))
        gal = bassline(Progression('Am'), 'gallop')
        self.assertEqual([n.start for n in gal][:3], [0.0, 0.5, 0.75])
        walk = bassline(Progression('C F'), 'walk', low='C2')
        self.assertEqual(len(walk), 8)
        self.assertEqual(walk[0].pitch, 36)
        self.assertEqual(abs(walk[3].pitch - walk[4].pitch), 1)  # chromatic approach
        fifth = bassline(Progression('Am'), 'fifth')
        self.assertEqual([n.pitch for n in fifth][:2], [33, 40])
        with self.assertRaises(ComposeError):
            bassline(p, 'funky')

    def test_pattern(self):
        b = bassline(Progression('Am'), pattern='r.oR f_.l', rate='1/16', vel=100, accent=1.0)
        self.assertEqual([(n.start, n.pitch, n.vel) for n in b][:5],
                         [(0.0, 33, 100), (0.5, 45, 100), (0.75, 33, 120), (1.0, 40, 100), (1.75, 21, 100)])
        self.assertAlmostEqual(b[3].dur, 0.5 * 0.7)


class BlockChords(unittest.TestCase):
    def test_block_and_rhythm(self):
        p = Progression('Am F C G')
        c = chords(p, voices=4)
        self.assertEqual(len(c), 16)
        self.assertEqual(c.length, 16)
        starts = sorted({n.start for n in c})
        self.assertEqual(starts, [0.0, 4.0, 8.0, 12.0])
        st = chords(Progression('Am'), rhythm='x..x..x.', step='1/8', voices=3)
        self.assertEqual(sorted({n.start for n in st}), [0.0, 1.5, 3.0])
        strum = chords(Progression('C'), voicing='close', voices=3, strum=0.05)
        self.assertEqual(sorted(n.start for n in strum), [0.0, 0.05, 0.1])


class Clips(unittest.TestCase):
    def setUp(self):
        self.a = Clip([(0, 1, 'C4'), (1, 1, 'E4', 90)], length=2)

    def test_construct(self):
        self.assertEqual(self.a[0], Note(0.0, 1.0, 60, 100))
        self.assertEqual(Clip([(0, 1.5, 60)]).length, 2.0)
        for bad in ([(0, 0, 60)], [(0, 1, 60, 0)], [(0, 1, 200)], ['x']):
            with self.assertRaises(ComposeError, msg=repr(bad)):
                Clip(bad)

    def test_combine(self):
        s = self.a + self.a
        self.assertEqual(s.length, 4)
        self.assertEqual([n.start for n in s], [0, 1, 2, 3])
        o = self.a | Clip([(0, 4, 48)])
        self.assertEqual(o.length, 4)
        self.assertEqual(len(o), 3)
        self.assertEqual(len(self.a * 3), 6)
        self.assertEqual((self.a * 3).length, 6)

    def test_slice_loop_transforms(self):
        s = (self.a * 2).slice(1, 3)
        self.assertEqual([(n.start, n.pitch) for n in s], [(0, 64), (1, 60)])
        lp = self.a.loop(3)
        self.assertEqual([(n.start, n.dur) for n in lp], [(0, 1), (1, 1), (2, 1)])
        self.assertEqual(self.a.transpose(12).pitches, [72, 76])
        with self.assertRaises(ComposeError):
            self.a.transpose(100)
        self.assertEqual(self.a.transpose_scale(2, 'C major').pitches, [64, 67])
        self.assertEqual([n.start for n in self.a.reverse()], [0, 1])
        self.assertEqual(self.a.reverse()[0].pitch, 64)
        self.assertEqual(self.a.stretch(2).length, 4)
        self.assertEqual([n.vel for n in self.a.velocity(0.5)], [50, 45])
        self.assertEqual([n.dur for n in self.a.gate(0.5)], [0.5, 0.5])
        beat = drums({'kick': 'x...', 'snare': '..x.'})
        self.assertEqual(beat.only('kick').pitches, [36])
        self.assertEqual(beat.without('kick').pitches, [38])

    def test_legato_and_fit(self):
        src = Clip([(0, 0.2, 60), (1, 0.2, 62), (3, 0.2, 64)], length=4)
        self.assertEqual([n.dur for n in src.legato(0)], [1, 2, 1])
        # default: a 0.02-beat overlap so mono / legato synths glide into the next note
        self.assertEqual([round(n.dur, 6) for n in src.legato()], [1.02, 2.02, 1.02])
        chord_then_note = Clip([(0, 0.5, 60), (0, 0.5, 64), (2, 0.5, 67)], length=4).legato(0)
        self.assertEqual([n.dur for n in chord_then_note], [2, 2, 2])
        line = Clip([(0, 1, 61), (1, 0.5, 66), (1.5, 0.5, 70)], length=2)
        fitted = line.fit(Progression('Am'), key='A minor')
        self.assertEqual([n.pitch for n in fitted], [60, 64, 69])  # C# -> C, F# -> E (chord), A# -> A (scale)


class Motifs(unittest.TestCase):
    def setUp(self):
        self.k = Key('A minor')

    def test_parse_and_render(self):
        m = Motif('1:1/8 3:1/8 5:1/4 r:1/4 8:1/2!', self.k)
        self.assertEqual(m.length, 5.0)
        c = m.clip(octave=4, vel=100, gate=1.0)
        self.assertEqual([(n.start, n.dur, n.pitch) for n in c],
                         [(0, 0.5, 69), (0.5, 0.5, 72), (1.0, 1.0, 76), (3.0, 2.0, 81)])
        self.assertEqual(c[3].vel, 120)
        m2 = Motif('5 _ 3 b7 E5 r', self.k, dur='1/8')
        self.assertEqual(m2.pitches(), [76, 72, 78, 76, None])
        self.assertEqual(m2.events[0].dur, 1.0)
        m3 = Motif([(1, 1), (3, '1/8'), None, ('#4', 0.5)], self.k)
        self.assertEqual(m3.pitches(), [69, 72, None, 75])
        with self.assertRaises(ComposeError):
            Motif('0 1 2', self.k)

    def test_transforms(self):
        m = Motif('1 2 3 5', self.k)
        self.assertEqual(m.transpose(1).pitches(), [71, 72, 74, 77])
        self.assertEqual(m.invert().pitches(), [69, 67, 65, 62])
        self.assertEqual(m.retrograde().pitches(), [76, 72, 71, 69])
        seq = m.sequence(0, -1, -2)
        self.assertEqual(len(seq), 12)
        self.assertEqual(seq.pitches()[4:8], [67, 69, 71, 74])
        self.assertEqual(m.rhythm(['1/4', '1/8']).length, 1 + 0.5 + 1 + 0.5)
        self.assertEqual(Motif('5 4 2', self.k).resolve().pitches()[-1], 69)
        self.assertEqual((m + m).length, 2 * m.length)

    def test_vary_is_seeded_and_keeps_length(self):
        m = Motif('1:1/4 3:1/8 5:1/8 6:1/4 5:1/4 3:1/2 2:1/4 1:1/4', self.k)
        a, b = m.vary(seed=3, amount=0.6), m.vary(seed=3, amount=0.6)
        self.assertEqual(a.events, b.events)
        for s in range(10):
            self.assertAlmostEqual(m.vary(seed=s, amount=0.6).length, m.length)
        self.assertTrue(any(m.vary(seed=s, amount=0.6).events != m.events for s in range(10)))


class MelodyAndFills(unittest.TestCase):
    def test_melody(self):
        k = Key('A minor')
        p = k.prog('i VI III VII')
        a = melody(p, k, rhythm='x.x.x..x', seed=4, register=('E4', 'E5'))
        b = melody(p, k, rhythm='x.x.x..x', seed=4, register=('E4', 'E5'))
        self.assertEqual(a, b)
        self.assertEqual(a.length, 16)
        for n in a:
            self.assertTrue(64 <= n.pitch <= 76)
            self.assertTrue(k.contains(n.pitch))
            if n.start % 2 == 0:
                self.assertIn(n.pitch % 12, p.at(n.start).pcs, n)
        self.assertEqual(a[-1].pitch % 12, p.at(a[-1].start).root)

    def test_fills(self):
        r = snare_roll(2, step='1/16', vel=(40, 120))
        self.assertEqual(len(r), 8)
        vels = [n.vel for n in r]
        self.assertEqual(vels, sorted(vels))
        self.assertEqual(r.length, 2)
        rb = snare_roll(4, build=True)
        gaps = [b.start - a.start for a, b in zip(rb, list(rb)[1:])]
        self.assertGreater(gaps[0], gaps[-1])
        t = tom_fill(1)
        self.assertEqual([n.pitch for n in t][0], 48)
        self.assertEqual([n.pitch for n in t][-1], 41)
        self.assertEqual(crash().pitches, [49])


if __name__ == '__main__':
    unittest.main()
