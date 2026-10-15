"""The orchestra's performance rules (agentsound/bandlib/ensemble.py, docs/ORCHESTRA_RULES.md) and the shared KTH
layer (agentsound/expressive.py): strict rule overrides, families, ensemble timing within its budget and in the
clip's order, legato overlaps / repeat strokes, breaths at phrase points (staggered in chords), ms -> beats through a
tempo change (orch.lead), the dynamics lane at the sampler curve's top, the Score's balance and the charge the pianist
and the orchestra share."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentsound import Song, expressive as ex, romantic  # noqa: E402
from agentsound.bandlib import ensemble as ens  # noqa: E402
from agentsound.bandlib import orchestra as orch  # noqa: E402
from agentsound.bands import Band  # noqa: E402
from agentsound.patches import inst  # noqa: E402
from agentsound.patterns import Clip, Note  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402


def tm(tempo=120):
    s = Song('t', tempo=tempo, seed=1)
    s.section('a', bars=40)
    return s, s.tempo_map()


def clip(notes, length=None):
    ns = [Note(*n) for n in notes]
    return Clip._raw(ns, length or max(n.start + n.dur for n in ns))


class TestRules(unittest.TestCase):
    def test_merged_is_strict(self):
        R = ens.merged({'breath': {'budget_s': {'flutes': (5.0, 7.0)}}, 'legato': {'max_gap': 0.05}})
        self.assertEqual(R['breath']['budget_s']['flutes'], (5.0, 7.0))
        self.assertEqual(R['breath']['budget_s']['oboes'], ens.BREATH['budget_s']['oboes'])   # nested: merged
        self.assertEqual(R['legato']['max_gap'], 0.05)
        self.assertEqual(ens.LEGATO['max_gap'], 0.03)                                         # the table untouched
        with self.assertRaisesRegex(ComposeError, 'unknown table'):
            ens.merged({'breathing': {}})
        with self.assertRaisesRegex(ComposeError, 'unknown key'):
            ens.merged({'breath': {'budget': 3}})

    def test_family_and_style(self):
        self.assertEqual(ens.family('bassoons'), 'woodwinds')       # not 'bass'
        self.assertEqual(ens.family('basses'), 'strings')
        self.assertEqual(ens.family('horn_solo'), 'horns')
        self.assertEqual(ens.family('low_brass'), 'brass')
        self.assertEqual(ens.family('timpani', 'struck'), 'struck')
        s = Song('t', tempo=100)
        b = Band(s, 'x')
        self.assertEqual(ens.style_of(b)['name'], 'classical')
        self.assertTrue(ens.style_of(b, 'baroque')['terrace'])
        with self.assertRaises(ComposeError):
            ens.style_of(b, 'punk')


class TestTiming(unittest.TestCase):
    def test_within_budget_order_kept_seeded(self):
        s, t = tm(90)
        c = clip([(i * 0.5, 0.5, 60 + i % 7, 80) for i in range(64)])
        R = ens.merged()
        a = ens.timing(c, t, s, 'violas', 'strings', R, random.Random(4))
        b = ens.timing(c, t, s, 'violas', 'strings', R, random.Random(4))
        self.assertEqual(list(a), list(b))                                     # deterministic
        self.assertEqual([n.pitch for n in a], [n.pitch for n in c])           # the clip's order
        dev = [(m.start - n.start) * 60000 / 90 for m, n in zip(a, c)]
        self.assertLessEqual(max(abs(d) for d in dev), R['ensemble']['max_ms'] + 1e-6)
        self.assertGreater(max(abs(d) for d in dev), 5.0)                     # it does move
        for m, n in zip(a, c):                                                 # ends stay put
            self.assertAlmostEqual(m.start + m.dur, n.start + n.dur, places=6)

    def test_lead_through_a_tempo_change(self):
        s = Song('t', tempo=60, seed=1)
        s.section('a', bars=2)
        b_ = s.section('b', bars=2)
        s.set_tempo(b_, 180)
        t = s.tempo_map()
        out = orch.lead(clip([(8.0, 2.0, 60), (4.0, 2.0, 62)]), t, 100.0)
        for n in out:
            b = {60: 8.0, 62: 4.0}[n.pitch]
            self.assertAlmostEqual(t.seconds_at(b) - t.seconds_at(n.start), 0.1, places=4)   # exactly 100 ms


class TestConnect(unittest.TestCase):
    def test_overlap_repeat_and_detached(self):
        s, t = tm(60)                                          # 1 beat = 1 s
        c = clip([(0, 1, 60), (1, 1, 62), (2, 1, 62), (3, 0.5, 64), (4, 1, 65)])
        out = sorted(ens.connect(c, t, 'woodwinds', ens.merged({'legato': {'punctuate': False}}), random.Random(1)),
                     key=lambda n: n.start)
        lo, hi = ens.LEGATO['overlap_ms']['woodwinds']
        ov = (out[0].start + out[0].dur - 1.0) * 1000
        self.assertTrue(lo - 1e-6 <= ov <= hi + 1e-6, ov)     # a legato transition: overlaps the next onset
        r_lo, r_hi = ens.BOWING['repeat_ms']
        gap = (2.0 - (out[1].start + out[1].dur)) * 1000
        self.assertTrue(r_lo - 1e-6 <= gap <= r_hi + 1e-6, gap)   # the same pitch again: a new stroke / tongue
        self.assertEqual(out[3].dur, 0.5)                     # written detached: left alone


class TestBreath(unittest.TestCase):
    def test_breaths_at_budget(self):
        s, t = tm(120)                                         # 0.5 s per beat
        c = clip([(i, 1.0, 72 + (i % 5), 70) for i in range(80)])   # 40 s of connected quarters
        R = ens.merged()
        out, breaths = ens.breathe(c, t, 'flutes', R, random.Random(2), bar_of=lambda b: (b % 4) / 4)
        lo, hi = R['breath']['budget_s']['flutes']
        self.assertGreaterEqual(len(breaths), 40 // (hi * R['breath']['over']))
        last = 0.0
        for b in breaths:
            self.assertGreaterEqual((b - last) * 0.5, R['breath']['min_into'] * lo - 1e-6)   # never too early
            self.assertLessEqual((b - last) * 0.5, R['breath']['over'] * hi + 1e-6)         # nor too late
            last = b
        g_lo, g_hi = R['breath']['gap_ms']
        for b in breaths:
            n = next(n for n in out if abs(n.start + 1.0 - b) < 1e-6)
            gap = (b - (n.start + n.dur)) * 500
            self.assertTrue(g_lo - 1e-6 <= gap <= min(g_hi, 0.4 * 500) + 1e-6, gap)

    def test_chords_stagger(self):
        s, t = tm(120)
        c = clip([(i * 4, 4.0, p, 70) for i in range(12) for p in (60, 64, 67)])   # 24 s of held chords
        out, breaths = ens.breathe(c, t, 'trombones', ens.merged(), random.Random(3))
        self.assertTrue(breaths)
        for b in breaths:
            ends = [n.start + n.dur for n in out if abs(n.start + 4.0 - b) < 1e-6]
            self.assertTrue(any(e < b - 1e-6 for e in ends) and any(abs(e - b) < 1e-6 for e in ends))  # never all


class TestLane(unittest.TestCase):
    def test_ff_accent_is_heard_as_a_fall(self):
        s, t = tm(120)
        c = clip([(0, 2.0, 72, 127)])
        from agentsound import articulation as art
        c = Clip._raw([art._mark(n, art='marcato') for n in c], 2.0)
        pts = ens.lane(c, t, 'brass', ens.merged(), random.Random(1))
        self.assertGreater(pts[0][1], pts[1][1] + 0.05)       # the accent falls back ...
        self.assertLess(ens.db_of(pts[1][1]), -1.0)           # ... to a level under the curve's flat top

    def test_detached_notes_step(self):
        s, t = tm(120)
        c = clip([(0, 0.4, 60, 60), (1, 0.4, 62, 100), (2, 1.0, 64, 60), (3, 1.0, 65, 100)])
        pts = ens.lane(c, t, 'strings', ens.merged(), random.Random(1))
        curve = {round(b, 3): cv for b, _, cv in pts}
        self.assertEqual(curve[1.0], 'step')                  # after a gap: the level steps at the onset
        self.assertEqual(curve[3.0], 'smooth')                # legato: a glide into the note


class TestBalance(unittest.TestCase):
    def test_accompaniment_under_the_melody_arc_kept(self):
        s = Song('t', tempo=100, key='C major', seed=3)
        s.section('a', bars=4)
        b = Band(s, 'x')
        for r in ('violins1', 'violas'):
            b.add(r, s.track(r, inst.va()))
        b.info.update(kind={'violins1': 'sustain', 'violas': 'sustain'},
                      articulations={r: ['sustain', 'staccato'] for r in ('violins1', 'violas')})
        sc = orch.Score(s, b, {'a': [(0, 90)]}, seed=1, jitter=0, phrasing={}, charge=False)
        sc.add('violins1', [(i, 1, 72 + i % 5, 90) for i in range(8)])            # a line (auto)
        sc.add('violas', [(0, 4, 60, 100), (4, 4, 62, 90)], line=False)          # a held accompaniment
        sc._apply_balance()
        v = [n[3] for n in sc.parts['violas']]
        self.assertLess(v[0], 100)
        self.assertLess(v[1], 90)
        self.assertGreater(v[0], v[1])                                           # its own arc kept
        self.assertGreaterEqual(ens.db_of(90 / 127) - ens.db_of(v[0] / 127), 0.0)
        self.assertLessEqual(ens.db_of(100 / 127) - ens.db_of(v[0] / 127), ens.BALANCE['max_db'] + 0.2)
        sc2 = orch.Score(s, b, {'a': [(0, 90)]}, seed=1, jitter=0, phrasing={}, balance=False)
        self.assertFalse(sc2.balance)


class TestShared(unittest.TestCase):
    def test_pianist_uses_the_shared_charge(self):
        self.assertIs(romantic.CHARGE, ex.CHARGE)
        self.assertIs(romantic.harmonic_charge, ex.harmonic_charge)
        c = clip([(i, 1, 48, 60) for i in range(8)])
        ch = [(0, 'C'), (2, 'G7'), (4, 'Dm'), (6, 'C')]
        plain = [n.vel for n in ex.harmonic_charge(c, ch, 'C major')]
        tense = [n.vel for n in ex.harmonic_charge(c, ch, 'C major', tension=6)]
        self.assertGreater(tense[2], plain[2])                # G7: a tritone - the swell into it
        self.assertEqual(tense[0], plain[0])                  # the tonic: none
        moving = [n.vel for n in ex.harmonic_charge(c, [(0, 'C', 'C major'), (4, 'C', 'Eb major')], 'C major')]
        self.assertGreater(moving[6], moving[0])              # the same chord, far from the new key's tonic

    def test_punctuation(self):
        c = clip([(0, .5, 60), (.5, .5, 62), (1, 2, 64), (3, .5, 62), (3.5, .5, 60), (4, 1, 72), (5, 1, 71)])
        ends = ex.punctuation(c)
        self.assertIn((1.0, 64), ends)                        # a long note after shorter ones
        self.assertNotIn((3.5, 60), ends)                     # 0.5 beats: under min_beats, no group end


if __name__ == '__main__':
    unittest.main()
