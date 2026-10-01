"""romantic.score: a written piano score (the nocturne etude's language and pipeline in the library) on top of the
notation (notes(expand=False): the ornaments as written, for a player). songs/nocturne-etude and gymnopedie-etude were
migrated with byte-identical render JSON; these tests pin the pieces."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Song, romantic as rom  # noqa: E402
from agentsound.patterns import Clip  # noqa: E402
from agentsound.theory import ComposeError, note  # noqa: E402

RH = {0: 'Bb4:1',
      1: 'G5:5 F5:1 G5:1 F5:2 Eb5:2^tr(lower=-1) Bb4:1',
      2: '{F5 G5 F5 E5 F5 G5}:3^fig(even) C5:1^turn(upper=1, lower=-1) [C6 C7]:2!^roll(60) G5:3 Ab5:2 G5:1?'}
LH = {1: 'Eb2:Bb3.Eb4.G4 Eb2:B3.D4.Ab4 Eb2:Bb3.Eb4.G4 D2:A3.C4.F#4|bc | '
         'C2:Bb3.E4.G4 C2:Bb3.E4.G4/Bb3.Db4.E4 -:Bb3.Db4.E4@0+1|c;F2:Ab3.C4.F4@1+2|bc F2:Ab3.C4.F4'}
DYN = [(0, 0, 'p'), (1, 6, 'mf'), (2, 0, 'mp'), (2, 9, 'p')]


def score():
    return rom.score(RH, LH, DYN, meter='12/8', pickup='1/8', key='Eb major', phrases=[(1, 2)])


class Reading(unittest.TestCase):
    def test_bars_events_entries_dyn(self):
        sc = score()
        self.assertEqual((sc.bar(0), sc.bar(1), sc.bar(2), sc.end), (0.0, 0.5, 6.5, 12.5))
        self.assertEqual(sc.bars, 2)
        self.assertEqual([e.kind for e in sc.in_bar(2)], ['fig', 'turn', 'roll', 'note', 'note', 'note'])
        trill = next(e for e in sc.events if e.kind == 'trill')
        self.assertEqual((trill.at, trill.dur, trill.kw), (5.0, 1.0, {'lower': -1}))
        roll = next(e for e in sc.events if e.kind == 'roll')
        self.assertEqual((roll.top, round(roll.factor, 6)), (note('C7'), 1.1))
        self.assertAlmostEqual(sc.events[-1].factor, 0.72)                       # the ghost
        g5 = sc.events[1]
        self.assertEqual((g5.kind, g5.at, g5.dur), ('note', 0.5, 2.5))
        self.assertEqual(len(sc.entries), 9)                                      # one beat holds two entries
        st, ln, bass, c1, c2, pat = sc.entries[3]
        self.assertEqual((st, ln, bass, pat), (5.0, 1.5, 'D2', 'bc'))
        split = [e for e in sc.entries if e[0] >= 9.5 and e[0] < 11.0]
        self.assertEqual([(e[0], e[1], e[2]) for e in split], [(9.5, 0.5, None), (10.0, 1.0, 'F2')])
        self.assertEqual(sc.dyn[1], (3.5, 'mf'))
        with self.assertRaisesRegex(ComposeError, '3 left-hand slots, the meter has 4'):
            rom.score(lh={1: 'Eb2:G3.Bb3 Eb2:G3.Bb3 Eb2:G3.Bb3'}, meter='12/8')
        with self.assertRaisesRegex(ComposeError, 'every bar once'):
            rom.score({1: 'C5:12', 3: 'C5:12'}, meter='12/8')
        with self.assertRaisesRegex(ComposeError, 'unknown level'):
            rom.score(dyn=[(1, 0, 'loud')])


class Performing(unittest.TestCase):
    def play(self, **kw):
        s = Song('t', tempo=50, key='Eb major', seed=2, time_sig='12/8')
        s.section('pickup', 1, meter=(1, 8))
        s.section('a', 2)
        rh = s.track('rh', {'type': 'va', 'params': {}})
        lh = s.track('lh', {'type': 'va', 'params': {}})
        return s, rh, lh, score().perform(s, rh, lh, **kw)

    def test_perform(self):
        s, rh, lh, out = self.play()
        self.assertTrue(out['lh'] and out['rh'] and out['pedal'])
        self.assertEqual(len(rh.notes), len(out['rh']))
        self.assertGreater(len(rh.notes), 20)                                  # the trill / fig / turn played
        trill = [n for n in out['rh'] if 5.0 - 0.2 <= n.start < 6.0 and n.pitch in (note('Eb5'), note('F5'),
                                                                                      note('D5'))]
        self.assertGreaterEqual(len(trill), 6)
        self.assertTrue(all(n.vel <= 112 for n in out['rh']))                  # the cap
        self.assertEqual(len(out['figures']), 2)                               # the trill and the fioritura
        self.assertEqual([t for t, _ in rh._auto], ['instrument.pedal'])
        self.assertEqual(rh._auto[0][1], lh._auto[0][1])

    def test_plain_baseline_differs(self):
        _, rh, _, out = self.play(plain=True)
        _, rh2, _, out2 = self.play()
        self.assertNotEqual(sorted(out['rh']), sorted(out2['rh']))
        fig = out['figures'][1][0]
        gaps = {round(b.start - a.start, 6) for a, b in zip(fig, list(fig)[1:])}
        self.assertEqual(len(gaps), 1)                                        # on an even grid


class Phrases(unittest.TestCase):
    def test_rubato_spans_and_touch(self):
        sc = rom.score(meter='3/4', phrases=[(1, 4), (5, 8), (8, 10)])

        class S:
            calls = []

            def rubato(self, span, **kw):
                self.calls.append((span, kw))
        s = S()
        sc.rubato(s, depth=0.04, phrase='breath', overlap=2, bars=(1, 9))
        self.assertEqual([c[0] for c in s.calls], [(0.0, 12.0), (12.0, 23.0)])  # (8, 10) is out of range
        s.calls = []
        sc.rubato(s, depth=0.1, shapes=('lean', 'arch'), seed='bar')
        self.assertEqual([(c[1]['phrase'], c[1]['seed']) for c in s.calls], [('lean', 1), ('arch', 5), ('lean', 8)])
        mel = Clip([(sc.bar(n) + 1, 1, 'F#5', 64) for n in range(1, 11)])
        out = sc.touch(mel, {(1, 4): (40, 80), (5, 8): (0, 0), (8, 10): (50, 90)}, gap=16)
        self.assertEqual([(p, at, len(ns)) for p, at, ns in out], [((1, 4), 0.0, 4), ((8, 10), 21.0, 2)])
        self.assertEqual(sc.phrase_of(8), (5, 8))
        with self.assertRaises(ComposeError):
            sc.phrase_of(11)


if __name__ == '__main__':
    unittest.main()
