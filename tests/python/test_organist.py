"""The organist (agentsound.organist) and its vocabulary (agentsound.organ_vocab): fast, no audio."""
import random
import unittest

from agentsound import Song, bands, organ_vocab as ov, organist
from agentsound.bandlib import orchestra as orch
from agentsound.theory import ComposeError, note

TUNE = 'G4:2 G4:1 F#4:1 E4:1 D4:1 G4:1 A4:1 B4:3 -:1 B4:1 B4:1 A4:1 G4:1 C5:1 B4:1 A4:2 G4:3 -:1'
CHART = [(0, 4, 'G'), (4, 4, 'D'), (8, 4, 'G'), (12, 4, 'C'), (16, 4, 'D'), (20, 4, 'G')]


def melody():
    out, t = [], 0.0
    for tok in TUNE.split():
        n, d = tok.split(':')
        if n != '-':
            out.append((t, float(d), note(n)))
        t += float(d)
    return out


class Vocabulary(unittest.TestCase):
    def setUp(self):
        self.mel = melody()
        self.slots = ov.harmonize(self.mel, CHART, 'G major', ends=[8, 20], seed=1)
        self.v = ov.satb(self.slots, self.mel, 'G major')

    def test_satb_voice_leading(self):
        self.assertEqual(self.v['S'], self.mel)
        lines = [self.v[k] for k in 'SATB']
        self.assertEqual(organist.parallel_motion([(k, self.v[k]) for k in 'SATB']), [])
        for k, (lo, hi) in ov.RANGES.items():
            self.assertTrue(all(lo <= p <= hi for _, _, p in self.v[k]), k)
        # the final chord: root position on the tonic
        self.assertEqual(self.v['B'][-1][2] % 12, note('G2') % 12)
        self.assertTrue(all(len(x) for x in lines))

    def test_flow_and_counterline_and_bass(self):
        f = ov.flow(self.v, self.slots, 'G major', per_bar=1.5, seed=2)
        self.assertGreater(sum(len(f[k]) for k in 'ATB'), sum(len(self.v[k]) for k in 'ATB'))
        cl = ov.counterline([self.v['S'], self.v['B']], self.slots, 'G major', lo='A3', hi='E5', motif='suspirans',
                            above=self.v['S'], below=self.v['B'], seed=3)
        self.assertTrue(cl and all(note('A3') <= p <= note('E5') for _, _, p in cl))
        b = ov.bass_line(self.slots, 'G major', walk=0.4, against=self.mel, seed=4)
        self.assertEqual(organist.parallel_motion([('t', self.mel), ('b', b)]), [])

    def test_toccata_figures(self):
        for fig in ov.TOCCATA_FIGURES:
            f = ov.toccata(self.slots, 'G major', figure=fig, register=('C5', 'C6'), seed=1)
            self.assertTrue(f['rh'] and f['lh'], fig)
            self.assertTrue(all(abs(d - 0.25) < 1e-9 for _, d, _ in f['rh']), fig)
        with self.assertRaises(ComposeError):
            ov.toccata(self.slots, 'G major', figure='nope')

    def test_fugue_exposition(self):
        subject = [(0, 1, note('D4')), (1, 0.5, note('A4')), (1.5, 0.5, note('G4')), (2, 1, note('F4')),
                   (3, 1, note('E4')), (4, 2, note('D4'))]
        fu = ov.fugue(subject, 'D minor', voices=3, seed=1)
        self.assertEqual(len(fu['entries']), 3)
        self.assertEqual(fu['entries'][1][2], 'answer')


class Player(unittest.TestCase):
    def band(self, **kw):
        s = Song('t', tempo=72, key='G major', tail=4)
        s.section('a', bars=6)
        return s, bands.church_organ(s, registers=('flute', 'cornet', 'oboe', 'strings'), **kw)

    def test_perform_writes_tracks_at_one_velocity(self):
        s, b = self.band()
        mel = melody()
        v = ov.satb(ov.harmonize(mel, CHART, 'G major', ends=[8, 20]), mel, 'G major')
        res = organist.perform(s, b, [organist.Voice(v['S'], 'cornet', 'S', ornaments={14.0: 'trill'}),
                                      organist.Voice(v['A'], 'flute', 'A'), organist.Voice(v['T'], 'flute', 'T'),
                                      organist.Voice(v['B'], 'pedal', 'B')], phrases=[12], seed=1)
        self.assertEqual(set(res), {'cornet', 'flute', 'pedal'})
        self.assertTrue(all(n.vel == organist.ORGAN_VEL for ns in res.values() for n in ns))
        self.assertGreater(len(res['cornet']), len(v['S']))          # the trill written out
        self.assertEqual(len(s.organ_voices), 4)
        # deterministic
        s2, b2 = self.band()
        res2 = organist.perform(s2, b2, [organist.Voice(v['S'], 'cornet', 'S', ornaments={14.0: 'trill'}),
                                         organist.Voice(v['A'], 'flute', 'A'), organist.Voice(v['T'], 'flute', 'T'),
                                         organist.Voice(v['B'], 'pedal', 'B')], phrases=[12], seed=1)
        self.assertEqual(res, res2)

    def test_one_manual_one_registration(self):
        s, b = self.band()
        with self.assertRaises(ComposeError):
            organist.perform(s, b, [organist.Voice([(0, 4, 67)], 'oboe'), organist.Voice([(1, 2, 60)], 'strings')])

    def test_articulation(self):
        ns = [(float(i), 1.0, 60 + i % 3) for i in range(8)]
        bpm = lambda b: 60.0                                      # noqa: E731
        leg = organist.articulate(ns, 'legato', bpm, random.Random(1))
        det = organist.articulate(ns, 'detache', bpm, random.Random(1))
        gap = lambda xs: sum((xs[i + 1][0] - xs[i][0] - xs[i][1]) for i in range(len(xs) - 1))   # noqa: E731
        self.assertLess(gap(leg), gap(det))
        self.assertGreater(gap(det), 0.5)

    def test_one_pipe_per_key_restrikes(self):
        keys = organist._merge([(0.0, 2.0, 60), (1.0, 2.0, 60), (0.02, 1.0, 64), (0.0, 1.0, 64)], lambda b: 60.0)
        sixty = [k for k in keys if k[2] == 60]
        self.assertEqual(len(sixty), 2)                         # re-struck at beat 1, the first released before it
        self.assertLess(sixty[0][0] + sixty[0][1], 1.0)
        self.assertAlmostEqual(sixty[1][0] + sixty[1][1], 3.0)
        self.assertEqual(len([k for k in keys if k[2] == 64]), 1)   # struck together: one key

    def test_accel_keeps_the_span(self):
        v = organist.Voice([(float(i) * 0.25, 0.25, 60 + i) for i in range(8)], 'flute', accel=(1.3, 0.75))
        ns = v.sorted()
        self.assertAlmostEqual(ns[0][0], 0.0)
        self.assertAlmostEqual(ns[-1][0] + ns[-1][1], 2.0)
        self.assertGreater(ns[1][0] - ns[0][0], ns[-1][0] - ns[-2][0])

    def test_swell_and_tremulant(self):
        s, b = self.band(tremulant=('oboe',))
        self.assertEqual(b.info['tremulant'], ['oboe'])
        self.assertEqual(set(b.info['swell']), {'soft', 'oboe', 'strings'})
        orch.swell(b, [(0, 0.2), (8, 1.0, 'smooth')], roles=['oboe'])
        tr = next(t for t in s.compile()['tracks'] if t['id'] == 'oboe')
        targets = {a['target'] for a in tr['automation']}            # (the named eq compiles to its index)
        self.assertIn('instrument.expression', targets)
        self.assertTrue(any(x.startswith('fx.') and x.endswith('.high.gain') for x in targets), targets)
        with self.assertRaises(ComposeError):
            orch.swell(b, [(0, 0.5)], roles=['cornet'])
        with self.assertRaises(ComposeError):
            bands.church_organ(Song('x', tempo=60), tremulant=('nope',))

    def test_registration_hint_in_the_render(self):
        s, b = self.band()
        organist.perform(s, b, [organist.Voice([(0, 4, 67)], 'cornet'), organist.Voice([(0, 4, 43)], 'pedal')])
        self.assertEqual(sorted(s.compile()['analysis']['registration']), ['cornet', 'pedal'])


if __name__ == '__main__':
    unittest.main()
