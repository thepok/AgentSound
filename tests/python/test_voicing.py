import pathlib
import sys
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import voicing as vc
from agentsound.theory import ComposeError, chord

CADENCE = [(2, 'C', 'E5', 'C3'), (2, 'F/A', None, 'A2'), (1, 'G7', 'D5', 'G2'), (2, 'C', 'C5', 'C3')]


def at(notes, t):
    return vc._sounding(notes, t)


class Notation(unittest.TestCase):
    def test_line_and_length(self):
        self.assertEqual(vc.line('C4:1 r:.5 E4:.5 | G4:2', 4), [(4.0, 1.0, 60), (5.5, 0.5, 64), (6.0, 2.0, 67)])
        self.assertEqual(vc.line('C4:1', shift=12), [(0.0, 1.0, 72)])
        self.assertEqual(vc.length('C4:1 r:.5 E4:.5 | G4:2'), 4.0)
        with self.assertRaises(ComposeError):
            vc.line('C4 1')

    def test_timeline_harmony_merge(self):
        tl = vc.timeline([(2, 'C'), (1, None), (1, 'G7')], 8)
        self.assertEqual(tl, [(8.0, 2, 'C'), (11.0, 1, 'G7')])
        self.assertEqual(vc.harmony_at(tl, 9.5), 'C')
        self.assertIsNone(vc.harmony_at(tl, 10.5))
        self.assertEqual(vc.merge_ties([(0, 1, 60), (1, 1, 60), (2, 1, 62)]), [(0, 2, 60), (2, 1, 62)])

    def test_chord_info(self):
        ci = vc.info('G7/B')
        self.assertEqual((ci.root, ci.bass, ci.third, ci.fifth, ci.seventh), (7, 11, 11, 2, 5))
        self.assertTrue(ci.major)
        self.assertTrue(vc.info('Bdim7').dim7)
        self.assertEqual(vc.leading_tone('C minor'), 11)
        self.assertEqual(vc.leading_tone('D minor'), 1)


class Voicer(unittest.TestCase):
    def test_satb_cadence(self):
        parts = vc.chorale(CADENCE, key='C major')
        self.assertEqual(list(parts), ['S', 'A', 'T', 'B'])
        for v, (lo, hi, _) in vc.SATB.items():
            self.assertTrue(all(lo <= p <= hi for _, _, p in parts[v]), v)
        self.assertEqual([p for _, _, p in parts['S']][0], 76)                 # the written top voice
        self.assertEqual([p for _, _, p in parts['B']], [48, 45, 43, 48])      # the written bass
        for i, (t, d, sym) in enumerate(vc.timeline(CADENCE)):
            ps = [parts[v][i][2] for v in 'SATB']
            self.assertEqual(ps, sorted(ps, reverse=True))                     # no crossing
            ci = vc.info(sym)
            self.assertIn(ci.third, {p % 12 for p in ps}, sym)                 # complete
            self.assertIn(ci.root, {p % 12 for p in ps}, sym)
            if sym == 'G7':
                self.assertEqual(sum(p % 12 == 11 for p in ps), 1)             # the leading tone once
                self.assertIn(5, {p % 12 for p in ps})                         # the 7th present
        issues = vc.check(parts, vc.timeline(CADENCE), voices=vc.SATB)
        self.assertFalse([i for i in issues if i.kind.startswith('parallel')], issues)
        self.assertFalse([i for i in issues if i.kind in ('range', 'crossing', 'non_chord')], issues)

    def test_fixed_voices_kept_and_tie(self):
        table = [(1, 'C', 'G5', 'C3', {'T': 'E3'}), (1, 'C', 'G5', 'C3'), (2, 'G', 'G5', 'G2')]
        parts = vc.chorale(table, tie=True)
        self.assertEqual(parts['S'], [(0.0, 4, 79)])                           # held G5 tied over 4 beats
        self.assertEqual(parts['T'][0][2], 52)

    def test_avoid_and_lt_per_step(self):
        steps = [{'chord': 'C', 'fixed': {'S': 72, 'B': 48}},
                 {'chord': 'G', 'fixed': {'S': 74, 'B': 43}, 'avoid': [66]}]
        out = vc.voice(steps)
        self.assertTrue(all(abs(p - 66) > 2 for v, p in out[1].items() if v in 'AT'))

    def test_orchestral_sets(self):
        table = [(2, 'Cm', None, None), (2, 'Ab', None, None), (2, 'Fm/Ab', None, None), (1, 'G7', None, None),
                 (1, 'Cm', None, None)] * 3
        for voices in (vc.STRINGS, vc.WINDS, vc.HORNS, vc.BRASS):
            parts = vc.chorale(table, voices=voices, key='C minor')
            self.assertEqual(list(parts), list(voices))
        t0 = time.perf_counter()
        parts = vc.chorale(table, voices=vc.WINDS8, key='C minor')
        self.assertLess(time.perf_counter() - t0, 5.0)                         # eight voices stay fast
        self.assertEqual(len(parts), 8)
        for i in range(len(parts['fl1'])):
            ps = [parts[v][i][2] for v in vc.WINDS8]
            self.assertEqual(ps, sorted(set(ps), reverse=True))
        issues = vc.check(parts, voices=vc.WINDS8, clashes=False)
        self.assertFalse([i for i in issues if i.kind in ('range', 'crossing')])

    def test_unison_doublings(self):
        table = [(2, 'Ab', 'C5', 'Ab2')]                          # eight winds between C5 and Ab2: too narrow
        with self.assertRaises(ComposeError):
            vc.chorale(table, voices=vc.WINDS8)
        parts = vc.chorale(table, voices=vc.WINDS8, unison=True)  # oboe 2 / clarinet 1 may share a note
        ps = [parts[v][0][2] for v in vc.WINDS8]
        self.assertEqual(ps, sorted(ps, reverse=True))             # never crossing
        self.assertLess(len(set(ps)), 8)
        self.assertEqual((ps[0], ps[-1]), (72, 44))

    def test_errors(self):
        with self.assertRaises(ComposeError):
            vc.voice([{'chord': 'C', 'fixed': {'S': 60, 'A': 70}}])            # fixed voices out of order
        with self.assertRaises(ComposeError):
            vc.voice([{'chord': 'C', 'active': ('S', 'X')}])
        with self.assertRaises(ComposeError):
            vc.chorale([(1, 'C', None, None)], voices={'a': (70, 60)})


class Check(unittest.TestCase):
    def test_parallels_between_any_pair(self):
        parts = {'S': [(0, 1, 79), (1, 1, 81)], 'A': [(0, 1, 64), (1, 1, 65)], 'T': [(0, 1, 60), (1, 1, 62)],
                 'B': [(0, 1, 48), (1, 1, 50)]}
        issues = vc.check(parts)
        kinds = {(i.kind, i.voices) for i in issues}
        self.assertIn(('parallel_8ve', ('T', 'B')), kinds)                     # C-C -> D-D
        self.assertIn(('parallel_5th', ('S', 'T')), kinds)                     # G5/C4 -> A5/D4: a compound fifth
        self.assertIn(('parallel_5th', ('S', 'B')), kinds)                     # non-adjacent voices too
        self.assertNotIn(('parallel_5th', ('S', 'A')), kinds)

    def test_contrary_motion_is_fine(self):
        parts = {'S': [(0, 1, 67), (1, 1, 72)], 'B': [(0, 1, 48), (1, 1, 41)]}   # 5th -> 5th in contrary motion
        self.assertEqual(vc.check(parts), [])

    def test_clash_non_chord_range_crossing(self):
        parts = {'S': [(0, 2, 72), (2, 1, 61)], 'A': [(0, 1, 71), (1, 2, 64)], 'B': [(0, 3, 48)]}
        harm = [(0, 3, 'C')]
        issues = vc.check(parts, harm, voices={'S': (65, 84), 'A': (55, 74), 'B': (40, 60)})
        kinds = [i.kind for i in issues]
        self.assertIn('clash', kinds)                                         # C5 against B4
        self.assertIn('non_chord', kinds)                                     # B4 on beat 0 in C
        self.assertIn('range', kinds)                                         # C#4 under the soprano's range
        self.assertIn('crossing', kinds)                                      # C#4 under E4
        self.assertIn('clash', vc.summary(issues))
        self.assertEqual(vc.summary([]), 'clean')
        self.assertEqual(vc.check(parts, harm, span=(5, 9)), [])


class Counterpoint(unittest.TestCase):
    def test_passing_eighths(self):
        parts = {'S': [(0.0, 2.0, 72), (2.0, 2.0, 76)], 'B': [(0.0, 4.0, 48)]}
        free = {('S', 0.0)}
        added = vc.passing_eighths(parts, free, 0.0, 'C major', order=('S', 'B'))
        self.assertEqual(added, [(1.5, 'S', 74)])
        self.assertEqual(parts['S'], [(0.0, 1.5, 72), (1.5, 0.5, 74), (2.0, 2.0, 76)])

    def test_passing_eighths_avoid_parallels(self):
        parts = {'S': [(0.0, 2.0, 72), (2.0, 2.0, 76)], 'B': [(0.0, 1.5, 60), (1.5, 0.5, 62), (2.0, 2.0, 64)]}
        self.assertEqual(vc.passing_eighths(parts, {('S', 0.0)}, 0.0, 'C major', order=('S', 'B')), [])

    def test_arpeggiate(self):
        parts = {'S': [(0.0, 4.0, 72), (4.0, 2.0, 74)], 'B': [(0.0, 4.0, 48), (4.0, 2.0, 43)]}
        free = {('S', 0.0)}
        added = vc.arpeggiate(parts, free, [(0, 4, 'C'), (4, 2, 'G')], 0.0, voices={'S': (60, 81), 'B': (40, 60)})
        self.assertEqual(len(added), 1)
        t, v, p = added[0]
        self.assertEqual((t, v), (3.0, 'S'))
        self.assertIn(p % 12, (0, 4, 7))
        self.assertIn(('S', 3.0), free)


class JointLines(unittest.TestCase):
    """Round o19b: the joint voice-leading core (cp_issues / repair / complement_rhythm / counterline)."""
    C = {0, 2, 4, 5, 7, 9, 11}

    def test_issues(self):
        par = {'S': [(0.0, 1.0, 67), (1.0, 1.0, 69)], 'B': [(0.0, 1.0, 48), (1.0, 1.0, 50)]}
        self.assertEqual([i.kind for i in vc.cp_issues(par)], ['parallel_outer'])
        uni = {'S': [(0.0, 3.0, 60)], 'B': [(0.0, 3.0, 48)]}
        self.assertEqual([i.kind for i in vc.cp_issues(uni)], ['unison_run'])
        dis = {'S': [(0.0, 1.0, 62)], 'B': [(0.0, 1.0, 60)]}
        self.assertEqual([i.kind for i in vc.cp_issues(dis)], ['dissonance'])
        # a suspension: held over the bass's move, resolving down by step - no issue
        sus = {'S': [(0.0, 2.0, 65), (2.0, 1.0, 64)], 'B': [(0.0, 1.0, 50), (1.0, 2.0, 55)]}
        self.assertEqual(vc.cp_issues(sus, strong=1.0), [])
        lock = {'S': [(float(i), 1.0, 72 + i % 2) for i in range(5)], 'B': [(float(i), 1.0, 48 - i % 2 * 2)
                                                                           for i in range(5)]}
        self.assertIn('rhythm_lock', [i.kind for i in vc.cp_issues(lock)])
        cross = {'S': [(0.0, 1.0, 55)], 'B': [(0.0, 1.0, 60)]}
        self.assertIn('crossing', [i.kind for i in vc.cp_issues(cross, order=('S', 'B'))])

    def test_repair_moves_the_free_note(self):
        par = {'S': [(0.0, 1.0, 67), (1.0, 1.0, 69)], 'B': [(0.0, 1.0, 48), (1.0, 1.0, 50)]}
        out = vc.repair(par, scale=lambda t: self.C, movable=lambda v, n: v == 'S', order=('S', 'B'))
        self.assertEqual(out['B'], par['B'])                     # (the fixed line kept)
        self.assertEqual(vc.cp_issues(out, order=('S', 'B')), [])
        self.assertNotEqual(out['S'][1][2], 69)

    def test_complement_and_counterline(self):
        subj = [(0.0, 0.5, 60), (0.5, 0.5, 62), (1.0, 0.5, 64), (1.5, 0.5, 65), (2.0, 2.0, 67)]
        rh = vc.complement_rhythm(subj, 0.0, 4.0, grid=0.5, hold=1.0, longest=2.0)
        self.assertEqual(rh[0], (0.0, 2.0))                      # (held while the subject runs)
        self.assertTrue(all(d == 0.5 for a, d in rh if a >= 2.0))   # (moving while it holds)
        self.assertAlmostEqual(sum(d for _, d in rh), 4.0)
        harm = [(0.0, 2.0, 'C'), (2.0, 2.0, 'G')]
        line = vc.counterline({'B': subj}, rh, scale=lambda t: self.C, lo=67, hi=84, harmony=harm, strong=2.0,
                              above=('B',))
        self.assertEqual([(a, d) for a, d, _ in line], rh)
        both = {'S': line, 'B': subj}
        self.assertFalse([i for i in vc.cp_issues(both, order=('S', 'B'), strong=2.0)
                          if i.kind in ('parallel_outer', 'parallel', 'crossing', 'unison_run')])
        self.assertTrue(all(p % 12 in {0, 4, 7} for a, _, p in line if a == 0.0))   # (a chord tone on the downbeat)
        self.assertEqual(line, vc.counterline({'B': subj}, rh, scale=lambda t: self.C, lo=67, hi=84, harmony=harm,
                                              strong=2.0, above=('B',)))      # (deterministic)


if __name__ == '__main__':
    unittest.main()
