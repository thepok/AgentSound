"""agentsound.romantic: the romantic pianist's figures, touch and rubato (the nocturne etude's fixes)."""
import math
import pathlib
import statistics
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Song, romantic as rom  # noqa: E402
from agentsound.patches import inst  # noqa: E402
from agentsound.patterns import Clip, Note  # noqa: E402
from agentsound.theory import ComposeError, Key, note  # noqa: E402

BPM = 48
KEY = Key('Eb major')
RUN = ['Db6', 'C6', 'B5', 'Bb5', 'A5', 'Ab5', 'F5', 'D5', 'B4', 'Bb4']


def iois_s(clip, bpm=BPM):
    ons = sorted({n.start for n in clip})
    return [(b - a) * 60.0 / bpm for a, b in zip(ons, ons[1:])]


class Fioritura(unittest.TestCase):
    def test_keeps_the_written_notes_in_order_and_fits_the_span(self):
        f = rom.fioritura(RUN, 1.5, BPM, at=4.0)
        self.assertEqual([n.pitch for n in sorted(f, key=lambda n: n.start)], [note(p) for p in RUN])
        self.assertAlmostEqual(min(n.start for n in f), 4.0)
        last = max(f, key=lambda n: n.start)
        self.assertLess(last.start, 5.5)
        self.assertGreater(last.start + last.dur, 5.5 - 0.3)     # legato to the landing beat

    def test_arch_is_slower_at_the_ends_and_lighter_in_the_middle(self):
        f = rom.fioritura(RUN, 1.5, BPM, shape='arch', ease=0.8, wobble_ms=0, sing=0)
        g = iois_s(f)
        mid = statistics.mean(g[3:6])
        ends = statistics.mean(g[:2] + g[-2:])
        self.assertGreater(ends / mid, 1.4)                       # a gesture, not a row of equal notes
        ns = sorted(f, key=lambda n: n.start)
        self.assertLess(min(n.vel for n in ns[3:7]), min(ns[0].vel, ns[-1].vel) - 2)
        even = rom.fioritura(RUN, 1.5, BPM, shape='even', wobble_ms=0)
        self.assertLess(statistics.pstdev(iois_s(even)), 0.002)

    def test_real_time_speed_follows_the_tempo(self):
        slow = rom.fioritura(RUN, 1.5, 40, wobble_ms=0)
        fast = rom.fioritura(RUN, 1.5, 80, wobble_ms=0)
        self.assertAlmostEqual(sum(iois_s(slow, 40)) / sum(iois_s(fast, 80)), 2.0, places=3)
        with self.assertRaises(ComposeError):                     # never thinned: too fast is an error
            rom.fioritura(RUN * 4, 0.5, BPM)

    def test_landing_note_on_the_beat(self):
        f = rom.fioritura(['F5', 'G5', 'F5', 'E5'], 1.0, BPM, at=2.0, land='F5', land_dur=0.5)
        self.assertTrue(any(n.pitch == note('F5') and abs(n.start - 3.0) < 1e-9 for n in f))

    def test_deterministic(self):
        a = rom.fioritura(RUN, 1.5, BPM, seed=3)
        b = rom.fioritura(RUN, 1.5, BPM, seed=3)
        self.assertEqual(list(a), list(b))


class Ornaments(unittest.TestCase):
    def test_trill_starts_slow_speeds_up_and_settles_into_its_termination(self):
        t = rom.trill('F5', 1.5, BPM, key=KEY, land='G5', land_dur=0.5, wobble_ms=0)
        ns = sorted(t, key=lambda n: n.start)
        ps = [n.pitch for n in ns]
        self.assertEqual(ps[0], note('F5'))                        # main-note start
        self.assertEqual(ps[1], note('G5'))
        self.assertEqual(ps[-3:], [note('Eb5'), note('F5'), note('G5')])  # Nachschlag (diatonic) into the landing
        chrom = sorted(rom.trill('F5', 1.5, BPM, key=KEY, lower=-1, land='G5', wobble_ms=0), key=lambda n: n.start)
        self.assertEqual(chrom[-3].pitch, note('E5'))
        self.assertAlmostEqual(ns[-1].start, 1.5)
        g = iois_s([n for n in ns[:-1]])
        mid = statistics.mean(g[len(g) // 3: 2 * len(g) // 3])
        self.assertGreater(g[0] / mid, 1.4)                        # a slower start
        self.assertGreater(g[-1] / mid, 1.15)                      # settling into the termination
        self.assertLess(1.0 / min(g), 13.5)                        # at most ~12 notes/s
        self.assertTrue(all(n.vel < ns[0].vel for n in ns[1:-1]))  # the figure lighter than the principal
        up = rom.trill('F5', 1.5, BPM, key=KEY, start='upper', wobble_ms=0)
        self.assertEqual(sorted(up, key=lambda n: n.start)[0].pitch, note('G5'))

    def test_turn_after_the_note_and_grace_notes_before_the_beat(self):
        t = rom.turn('C5', 0.5, BPM, at=1.0, upper=1, lower=-1)
        ps = [n.pitch for n in sorted(t, key=lambda n: n.start)]
        self.assertEqual(ps, [note('C5'), note('Db5'), note('C5'), note('B4'), note('C5')])
        g = rom.grace(['B4', 'C5', 'Db5'], 'C5', 1.0, BPM, at=2.0, ms=60)
        ns = sorted(g, key=lambda n: n.start)
        self.assertAlmostEqual(ns[-1].start, 2.0)                 # the target on the beat
        self.assertLess(ns[0].start, 2.0)
        self.assertTrue(all(n.vel < ns[-1].vel for n in ns[:-1]))
        on = rom.grace(['B4', 'Db5'], 'C5', 1.0, BPM, at=2.0, on_beat=True)
        self.assertAlmostEqual(min(n.start for n in on), 2.0)


class LeftHand(unittest.TestCase):
    def test_bass_chord_chord_with_touch(self):
        lh = rom.accompany([(0, 1.5, 'Eb2', ['Bb3', 'Eb4', 'G4']), (1.5, 1.5, 'Eb2', ['B3', 'D4', 'Ab4'])], BPM,
                           jitter_ms=0, breathe=0)
        bass = [n for n in lh if n.pitch == note('Eb2')]
        self.assertEqual([round(n.start, 3) for n in bass], [0.0, 1.5])
        self.assertAlmostEqual(bass[0].dur, 1.5)                  # the bass rings through its beat
        chords = [n for n in lh if n.pitch != note('Eb2')]
        self.assertEqual(len(chords), 12)                         # two strikes per beat
        self.assertGreater(min(n.vel for n in bass), max(n.vel for n in chords))
        first = [n for n in chords if n.start < 1.0]
        second = [n for n in chords if 1.0 <= n.start < 1.5]
        self.assertGreater(statistics.mean(n.vel for n in first), statistics.mean(n.vel for n in second))
        rolled = sorted(first, key=lambda n: n.start)
        self.assertLess(rolled[0].start, rolled[-1].start)        # rolled from the bottom
        held = rom.accompany([(0, 3.0, 'Eb1', ['Eb2', 'Bb2', 'G3'])], BPM, pattern='B..', jitter_ms=0)
        self.assertTrue(all(n.start + n.dur > 2.9 for n in held))


class SingingLine(unittest.TestCase):
    def test_cantabile_plays_into_the_decay_and_keeps_ornaments_under_their_principal(self):
        line = Clip([(0, 3.0, 'G5', 80), (3.0, 0.5, 'F5', 80), (3.5, 0.5, 'G5', 80)])
        c = sorted(rom.cantabile(line, BPM), key=lambda n: n.start)
        self.assertLess(c[1].vel, 76)                             # after a 3.75 s G5: softer
        self.assertGreaterEqual(c[1].vel, 80 * 0.72 - 1)
        self.assertEqual(c[2].vel, 80)                            # after a short note: as written
        tr = rom.trill('F5', 1.5, BPM, at=3.0, key=KEY, vel=80, wobble_ms=0)
        both = sorted(rom.cantabile(Clip([(0, 3.0, 'C6', 80)] + [tuple(n) for n in tr]), BPM),
                      key=lambda n: n.start)
        principal = both[1]
        self.assertTrue(all(n.vel <= principal.vel for n in both[2:]))

    def test_lean_on_long_weights_by_length(self):
        line = Clip([(0, 3.0, 'G5', 70), (3.0, 0.3, 'F5', 70), (3.3, 0.3, 'G5', 70)])
        c = sorted(rom.lean_on_long(line, BPM, gain=10), key=lambda n: n.start)
        self.assertEqual(c[0].vel, 80)
        self.assertEqual([c[1].vel, c[2].vel], [70, 70])

    def test_dynamics_marks_and_hairpins(self):
        line = Clip([(b, 0.5, 'C5', 80) for b in range(0, 12)])
        d = sorted(rom.dynamics(line, [(0, 'p'), (6, 'f'), (9, 'p', 'step')]), key=lambda n: n.start)
        self.assertEqual(d[0].vel, round(80 * rom.LEVELS['p']))
        self.assertEqual(d[6].vel, round(80 * rom.LEVELS['f']))
        self.assertLess(d[1].vel, d[3].vel)                       # a crescendo hairpin
        self.assertEqual(d[8].vel, round(80 * rom.LEVELS['f']))   # subito at the step mark
        self.assertEqual(d[9].vel, round(80 * rom.LEVELS['p']))
        with self.assertRaises(ComposeError):
            rom.dynamics(line, [(0, 'loud')])

    def test_decay_model(self):
        self.assertAlmostEqual(rom.decay_db('C5', 0.0), 0.0)
        self.assertGreater(rom.decay_db('C6', 1.0), rom.decay_db('C4', 1.0))
        self.assertTrue(5 < rom.decay_db('C5', 1.0) < 9)


class MelodyRubato(unittest.TestCase):
    def line(self):
        ns = []
        for bar in range(4):
            a = bar * 6.0
            ns += [(a, 2.5, 'G5', 80), (a + 2.5, 0.5, 'F5', 70), (a + 3.0, 1.0, 'Bb5', 80), (a + 4.0, 1.0, 'Ab5', 75),
                   (a + 5.0, 1.0, 'Eb5', 70)]
        return Clip(ns)

    def test_moves_only_the_melody_keeps_order_and_legato(self):
        mel = self.line()
        anchors = [b * 3.0 for b in range(9)]
        r = sorted(rom.melody_rubato(mel, anchors, BPM, seed=1), key=lambda n: n.start)
        o = sorted(mel, key=lambda n: n.start)
        self.assertEqual([n.pitch for n in r], [n.pitch for n in o])
        offs = [(a.start - b.start) * 60000 / BPM for a, b in zip(r, o)]
        self.assertTrue(any(abs(x) > 5 for x in offs))
        self.assertTrue(all(abs(x) < 250 for x in offs))
        for a, b in zip(r, r[1:]):
            self.assertLess(a.start, b.start)
            self.assertAlmostEqual(a.start + a.dur, b.start + 0.03, places=6)     # re-tied legato

    def test_downbeat_offsets_spread_both_ways(self):
        mel = Clip([(b * 6.0, 5.0, 'G5', 80) for b in range(40)] + [(b * 6.0 + 5.0, 1.0, 'F5', 70) for b in range(40)])
        anchors = [b * 3.0 for b in range(81)]
        r = rom.melody_rubato(mel, anchors, BPM, lean_ms=0, agogic_ms=0, peak_ms=0, free_ms=0, seed=5)
        offs = [(n.start - round(n.start / 6.0) * 6.0) * 60000 / BPM for n in r if n.pitch == note('G5')]
        self.assertTrue(any(x < -10 for x in offs) and any(x > 10 for x in offs))
        self.assertTrue(15 < statistics.pstdev(offs) < 45)

    def test_needs_two_anchors(self):
        with self.assertRaises(ComposeError):
            rom.melody_rubato(self.line(), [0], BPM)


class Pedal(unittest.TestCase):
    def test_legato_pedal_changes(self):
        pts = rom.pedal_changes([0, 1.5, 3.0], end=6.0, lift_ms=100, bpm=60)
        self.assertEqual(pts[0], (0.0, 0.0, 'step'))
        self.assertIn((0.1, 1.0, 'step'), pts)
        self.assertIn((1.5, 0.0, 'step'), pts)
        self.assertEqual(pts[-1], (6.0, 0.0, 'step'))
        fl = rom.pedal_changes([0], end=8.0, lift_ms=100, bpm=60, flutter=[(2.0, 4.0)], flutter_ms=500)
        ups = [p[0] for p in fl if p[1] == 0.0 and 2.0 <= p[0] < 4.0]
        self.assertEqual(ups, [2.0, 2.5, 3.0, 3.5])                # cleared every 500 ms inside the window
        self.assertTrue(any(p[0] == 3.6 and p[1] == 1.0 for p in fl))
        half = rom.pedal_changes([0], end=8.0, lift_ms=100, bpm=60, flutter=[(2.0, 3.0)], flutter_ms=500, flutter_to=0.6)
        self.assertIn((2.0, 0.6, 'step'), half)                    # a half pedal at the lifts: the bass rings on


class TempoWhileBuilding(unittest.TestCase):
    def test_tempo_at_before_the_notes_are_placed_returns_a_tempo(self):
        # real-time figures ask the tempo map while the song is still being written: an a-tempo ritardando must
        # not keep its slowed tempo for good just because no note is placed yet (the nocturne's trills got 3x
        # denser bar after bar)
        s = Song('t', tempo=60)
        s.section('a', bars=8)
        s.ritardando((4, 8), to=0.5)
        s.ritardando((12, 16), to=0.5)
        self.assertAlmostEqual(s.tempo_at(10), 60.0)
        self.assertAlmostEqual(s.tempo_at(20), 60.0)
        t = s.track('p', inst.va())
        t.note('C4', 30, 1)
        self.assertAlmostEqual(s.tempo_at(20), 60.0)


class FigureStats(unittest.TestCase):
    def test_stats(self):
        st = rom.figure_stats(rom.fioritura(RUN, 1.5, BPM, wobble_ms=0), BPM)
        self.assertEqual(st['notes'], 10)
        self.assertGreater(st['ends_vs_middle'], 1.2)
        self.assertTrue(math.isfinite(st['cv']))


if __name__ == '__main__':
    unittest.main()
