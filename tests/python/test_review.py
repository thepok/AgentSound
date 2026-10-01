"""Regression tests for defects found in the compose-layer review."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import (Clip, ComposeError, Key, Patch, Progression, Song, bassline, chord, drums, fx, grid,
                        hold, inst, melody, patches, ramp)
from agentsound.automation import normalize
from agentsound.cli import explain_engine_error


class LeadingToneChords(unittest.TestCase):
    def test_vii_dim_in_minor_is_leading_tone(self):
        am = Key('A minor')
        self.assertEqual(am.chord('vii°').pcs, chord('G#dim').pcs)
        self.assertEqual(am.chord('vii°7').pcs, chord('G#dim7').pcs)
        self.assertEqual(am.chord('viiø7').pcs, chord('G#m7b5').pcs)
        self.assertEqual(am.chord('viio7').root, 8)
        self.assertEqual(am.chord('VII').root, 7)            # the plain subtonic major chord is unchanged
        self.assertEqual(am.chord('bVII').root, 7)
        self.assertEqual(Key('D dorian').chord('vii°').root, 1)
        self.assertEqual(Key('C major').chord('vii°7').pcs, chord('Bdim7').pcs)

    def test_secondary_leading_tone_chords(self):
        c = Key('C major')
        self.assertEqual(c.chord('vii°/ii').pcs, chord('C#dim').pcs)   # tonicizing Dm needs C#, not C
        self.assertEqual(c.chord('vii°7/V').pcs, chord('F#dim7').pcs)
        self.assertEqual(Key('A minor').chord('vii°/iv').pcs, chord('C#dim').pcs)

    def test_sharp_key_spelling(self):
        self.assertEqual(Key('F# minor').chord('V7/V').symbol, 'G#7')
        self.assertEqual(Key('C# major').chord('V').symbol, 'G#')
        self.assertEqual(Key('C major').chord('bVII').symbol, 'Bb')
        self.assertEqual(Key('Eb major').chord('V').symbol, 'Bb')

    def test_omit_suffix_is_not_diminished(self):
        self.assertEqual(Key('C major').chord('Iomit3').intervals, (0, 7))


class MoreQualities(unittest.TestCase):
    def test_chart_shorthands(self):
        self.assertEqual(chord('C2').intervals, (0, 2, 7))
        self.assertEqual(chord('C7alt').intervals, (0, 4, 10, 13, 15, 20))
        self.assertEqual(chord('Calt').intervals, (0, 4, 10, 13, 15, 20))
        self.assertEqual(chord('Cdom7').intervals, (0, 4, 7, 10))
        self.assertEqual(chord('G7b9#9').intervals, (0, 4, 7, 10, 13, 15))


class WalkingBass(unittest.TestCase):
    def _check(self, prog, low='E1'):
        line = bassline(prog, 'walk', low=low)
        ps = [n.pitch for n in line]
        self.assertEqual(len(ps), 4 * len(prog))
        roots = [c.bass_note(low) for _, _, c in prog if c is not None]
        for i, r in enumerate(roots):
            self.assertEqual(ps[4 * i], r)                                  # beat 1 = root
            nxt = roots[(i + 1) % len(roots)] if i + 1 < len(roots) else r
            self.assertEqual(abs(ps[4 * i + 3] - nxt), 1)                   # chromatic approach
        leaps = [abs(a - b) for a, b in zip(ps, ps[1:])]
        self.assertLessEqual(max(leaps), 7, ps)
        self.assertGreaterEqual(sum(1 for d in leaps if d <= 3) / len(leaps), 0.75, ps)
        return ps

    def test_walk_is_stepwise_and_approaches_next_root(self):
        self._check(Key('A minor').prog('i VI III VII'))
        self._check(Key('C major').prog('ii7 V7 Imaj7 VI7'))
        self._check(Progression('Am Dm G C F Bdim E7 Am'))

    def test_walk_stays_near_the_bass_register(self):
        ps = [n.pitch for n in bassline(Key('A minor').prog('i VI III VII'), 'walk', low='E1')]
        self.assertGreaterEqual(min(ps), 26)   # never far below E1
        self.assertLessEqual(max(ps), 52)


class PatternFixes(unittest.TestCase):
    def test_digit_levels_scale_with_vel(self):
        self.assertEqual([n.vel for n in drums({'kick': '9...'}, vel=50)], [63])
        self.assertEqual([n.vel for n in drums({'kick': '9...'})], [126])
        self.assertEqual([n.vel for n in grid('5', 'A2', vel=50)], [35])

    def test_reverse_keeps_notes_inside_the_clip(self):
        r = Clip([(0, 1, 60), (3, 2, 62)], length=4).reverse()
        self.assertEqual([(n.start, n.dur, n.pitch) for n in r], [(0.0, 1.0, 62), (3.0, 1.0, 60)])

    def test_melody_does_not_drone(self):
        k = Key('A minor')
        for seed in range(6):
            ps = [n.pitch for n in melody(k.prog('i VI III VII'), k, seed=seed)]
            runs = max(len(list(g)) for g in _groups(ps))
            self.assertLessEqual(runs, 2, (seed, ps))


def _groups(xs):
    out, cur = [], [xs[0]]
    for x in xs[1:]:
        if x == cur[-1]:
            cur.append(x)
        else:
            out.append(cur)
            cur = [x]
    return out + [cur]


class ReturnBusesAndPatches(unittest.TestCase):
    def setUp(self):     # restore the registry afterwards: later tests need the library's bus/* patches
        patches.load_library()
        self._registry = dict(patches._REGISTRY)
        self.addCleanup(lambda: (patches._REGISTRY.clear(), patches._REGISTRY.update(self._registry)))

    def test_hall_params_reach_the_reverb_in_a_library_chain(self):
        patches.register(Patch('bus/hall', fx=[fx.eq(low_cut=200), fx.reverb(type='hall', mix=1.0)]), replace=True)
        s = Song('t')
        s.section('a', bars=1)
        hall = s.hall(decay=4.5)
        self.assertEqual(hall.fx[0].params, {'low_cut': 200})
        self.assertEqual(hall.fx[1].params['decay'], 4.5)
        self.assertIs(s.hall(), hall)
        with self.assertRaises(ComposeError):
            s.hall(decay=2.0)           # params on an existing bus would be silently lost

    def test_but_fx(self):
        p = Patch('test/chain', fx=[fx.eq(), fx.reverb(mix=1.0, name='verb'), fx.reverb(mix=0.5)])
        self.assertEqual(p.but_fx('reverb', decay=3).fx[1].params, {'mix': 1.0, 'decay': 3})
        self.assertEqual(p.but_fx(2, decay=3).fx[2].params, {'mix': 0.5, 'decay': 3})
        self.assertEqual(p.but_fx('verb', size=1).fx[1].params['size'], 1)
        self.assertEqual(p.fx[1].params, {'mix': 1.0})      # original untouched
        with self.assertRaises(ComposeError):
            p.but_fx('delay', mix=0.1)

    def test_track_accepts_single_fx(self):
        s = Song('t')
        s.section('a', bars=1)
        t = s.track('x', inst.va(), fx=fx.chorus(mix=0.3)).note(60, 0)
        self.assertEqual([f.type for f in t.fx], ['chorus'])
        self.assertEqual(s.compile()['tracks'][0]['fx'], [{'type': 'chorus', 'params': {'mix': 0.3}}])


class EngineLimits(unittest.TestCase):
    def test_id_length(self):
        s = Song('t')
        with self.assertRaises(ComposeError):
            s.track('x' * 49, inst.va())
        s.section('a', bars=1)
        kit = s.track('k' * 48, inst.drums())
        kit.play(drums({'kick': 'x...'}))
        pad = s.track('pad', inst.va()).note(60, 0)
        pad.duck(kit, pitches='kick')
        r = s.compile()
        self.assertTrue(all(len(t['id']) <= 48 for t in r['tracks']))

    def test_seed_range_and_empty_song(self):
        with self.assertRaises(ComposeError):
            Song('t', seed=2 ** 32)
        s = Song('t')
        s.section('a', bars=1)
        s.bus('b')
        with self.assertRaises(ComposeError):
            s.compile()


class AutomationJumps(unittest.TestCase):
    def test_hold_wins_regardless_of_order(self):
        want = [[0.0, 0.0], [3.999, 1.0], [4.0, 0.5, 'step'], [8.0, 0.5]]
        self.assertEqual(normalize(ramp(0, 4, 0, 1) + hold(4, 8, 0.5)), want)
        self.assertEqual(normalize(hold(4, 8, 0.5) + ramp(0, 4, 0, 1)), want)

    def test_plain_points_later_wins(self):
        self.assertEqual(normalize([(0, 1), (4, 2), (4, 5), (8, 1)]), [[0.0, 1.0], [3.999, 2.0], [4.0, 5.0, 'step'],
                                                                      [8.0, 1.0]])


class EngineErrorExplained(unittest.TestCase):
    def test_paths_name_nodes(self):
        r = {'tracks': [{'id': 'a', 'fx': []}, {'id': 'pad', 'fx': [{'type': 'eq'}, {'type': 'chorus'}]}],
             'buses': [{'id': 'hall', 'fx': [{'type': 'reverb'}]}], 'master': {'fx': [{'type': 'limiter'}]}}
        msg = explain_engine_error('$.tracks[1].fx[1].params: x; $.buses[0].fx[0]; $.master.fx[0]; $.tracks[7]', r)
        self.assertIn("$.tracks[1].fx[1] (track 'pad', fx #1 'chorus').params", msg)
        self.assertIn("$.buses[0].fx[0] (bus 'hall', fx #0 'reverb')", msg)
        self.assertIn("$.master.fx[0] (master, fx #0 'limiter')", msg)
        self.assertIn('$.tracks[7];', msg + ';')


if __name__ == '__main__':
    unittest.main()
