"""The orchestra package: figures (agentsound.figures), voicing.Harmony (s.prog / s.harmony), voicing.fugue /
imitation, Motif.head / fragment, orch.Score (the part buffer + one dynamics map: add, double, colla_parte, winds,
hits, brass, unison, play, stabs, fermata, bed, perform with follow), orch.Choir (speak / sing / lanes / gate /
swells), s.arc, articulation.expression_points(follow=). Most tests use a small stand-in band (plain tracks with
the info a preset hands over); the ones that need the SSO sections skip when the pack is not installed."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentsound import Song, bands, figures, library, voicing  # noqa: E402
from agentsound import articulation as art  # noqa: E402
from agentsound.bandlib import orchestra as orch  # noqa: E402
from agentsound.bands import Band  # noqa: E402
from agentsound.patterns import Clip, Motif  # noqa: E402
from agentsound.patches import inst  # noqa: E402
from agentsound.theory import ComposeError, Progression  # noqa: E402

ROLES = ('violins1', 'violins2', 'violas', 'cellos', 'basses', 'flutes', 'oboes', 'clarinets', 'bassoons', 'horns',
         'trumpets', 'timpani')


def stand_in(sections=(('a', 4), ('b', 4)), key='C minor', tempo=120):
    """A song and a band of plain tracks with the info a preset hands over (articulations, ranges, seating)."""
    s = Song('t', tempo=tempo, key=key, seed=3)
    secs = [s.section(n, bars=b) for n, b in sections]
    b = Band(s, 'stand_in')
    for r in ROLES:
        b.add(r, s.track(r, inst.va()))
    b.bus('hall', s.bus('hall'))
    b.info.update(kind={r: 'plain' for r in ROLES},
                  articulations={r: ['sustain', 'staccato', 'marcato', 'pizzicato'] for r in ROLES},
                  range={r: ('C2', 'C6') for r in ROLES}, seating={r: {'hall_send': -6.0} for r in ROLES})
    return s, secs, b


def have(*packs) -> bool:
    return all((library.SAMPLES / p / 'SOURCE.json').is_file() for p in packs)


class TestFigures(unittest.TestCase):
    def test_repeat_figures_on_tuples(self):
        held = [(0, 2, 60), (2, 1.5, 62, 90)]
        self.assertEqual(figures.figure(held, 'pulse8')[:4],
                         [(0.0, 0.42, 60), (0.5, 0.42, 60), (1.0, 0.42, 60), (1.5, 0.42, 60)])
        self.assertEqual(figures.figure(held, 'offbeats'), [(0.5, 0.42, 60), (1.5, 0.42, 60), (2.5, 0.42, 62, 90)])
        self.assertEqual(figures.figure(held, 'syncope'), [(0.5, 0.85, 60), (1.5, 0.5, 60), (2.5, 0.85, 62, 90)])
        self.assertEqual(figures.figure([(0, 4, 48)], 'beats', every=2, gap=1.2), [(0, 1.2, 48), (2, 1.2, 48)])
        last = figures.figure([(0, 1, 60)], 'beats', gap=0.8, offset=0.5)
        self.assertEqual(last, [(0.5, 0.5, 60)])                      # cut at the note's end

    def test_repeat_figures_on_clips_keep_velocities_and_marks(self):
        c = Clip([(0, 1, 'C4', 77)], length=4).articulate('tremolo')
        f = c.figure('pulse16')
        self.assertIsInstance(f, Clip)
        self.assertEqual(len(f), 4)
        self.assertTrue(all(n.vel == 77 and art.articulation_of(n) == 'tremolo' for n in f))
        self.assertEqual(f.length, 4)

    def test_chord_figures(self):
        h = Progression('Cm Ab', key='C minor')
        b1, b2 = figures.figure(h, 'broken', vel=50, seed=4), figures.figure(h, 'broken', vel=50, seed=4)
        self.assertEqual(b1, b2)                                      # seeded
        self.assertEqual(len(b1), 16)
        self.assertEqual(b1.notes[0].pitch, 36)                      # the root first
        oom, pah = figures.figure(Progression('C G', beats_per_bar=3), 'oompah', low='E2', split=True)
        self.assertEqual([n.start for n in oom], [0.0, 3.0])
        self.assertEqual(sorted({n.start for n in pah}), [1.0, 2.0, 4.0, 5.0])
        self.assertEqual(oom.notes[0].vel, 86)                       # 78 + the accent on every other chord
        ost = figures.figure(Progression('Am'), 'ostinato', low='A2')
        self.assertEqual(len(ost), 8)
        self.assertEqual(ost.notes[3].pitch, ost.notes[0].pitch + 12)
        alb = figures.figure(Progression('C'), 'alberti')
        self.assertEqual([n.pitch for n in alb][:4], [60, 67, 64, 67])
        storm = figures.figure(Progression('Dm'), 'storm16')
        self.assertEqual(len(storm), 16)

    def test_errors(self):
        with self.assertRaisesRegex(ComposeError, 'unknown figure'):
            figures.figure([(0, 1, 60)], 'samba')
        with self.assertRaisesRegex(ComposeError, 'unknown option'):
            figures.figure([(0, 1, 60)], 'pulse8', swing=1)
        with self.assertRaisesRegex(ComposeError, 'voice'):
            voicing.Harmony('C F').figure('pulse8')


class TestHarmony(unittest.TestCase):
    T = [(4, 'Cm', 'C5', 'C3'), (4, 'G7/B', 'D5', 'B2'), (2, None, None, None), (2, 'Fm', 'F5', 'F2')]

    def test_song_prog_is_a_harmony_and_a_progression(self):
        s = Song('t', tempo=100, key='C minor')
        p = s.prog('i VI iv V7')
        self.assertIsInstance(p, voicing.Harmony)
        self.assertIsInstance(p, Progression)
        self.assertEqual(p.at(5).symbol, 'Ab')
        self.assertEqual(p.at(17).symbol, 'Cm')                       # a progression wraps (Progression.at)
        self.assertEqual(p.transpose(2).at(0).symbol, 'Dm')
        self.assertIsInstance(p.transpose(2), voicing.Harmony)
        self.assertIsInstance(p + s.prog('i'), voicing.Harmony)

    def test_table_frame_slices_and_transpose(self):
        h = voicing.Harmony(self.T, key='C minor', at=10)
        self.assertEqual(h.timeline(), [(10.0, 4, 'Cm'), (14.0, 4, 'G7/B'), (20.0, 2, 'Fm')])
        self.assertEqual(h.symbol_at(15), 'G7/B')
        self.assertIsNone(h.at(19))                                   # the rest
        self.assertIsNone(h.at(30))                                   # a table does not wrap
        self.assertEqual(h.info_at(10).root, 0)
        self.assertEqual(h[1:].timeline()[0], (14.0, 4, 'G7/B'))     # a slice keeps where it sounds
        self.assertEqual(h.place(0).timeline()[0][0], 0.0)
        self.assertEqual(h.transpose(-3).table[0], (4, 'Am', 69, 45))

    def test_chorale_under_tutti_voice(self):
        h = voicing.Harmony(self.T, key='C minor', at=8)
        self.assertEqual(h.chorale(voicing.STRINGS, tie=True),
                         voicing.chorale(self.T, 8, voices=voicing.STRINGS, key='C minor', tie=True))
        mel = [(8, 4, 74), (12, 4, 75)]
        under = h.under(mel, voicing.STRINGS)
        self.assertNotIn('violins1', under)                            # the melody is the top voice
        self.assertEqual(set(under), {'violins2', 'violas', 'cellos'})
        self.assertTrue(all(n[2] < 74 for n in under['violins2'] if n[0] < 12))
        blk = voicing.Harmony('Cm').under(Clip([(0, 1, 'G4', 90)], length=4), 3)
        self.assertEqual([n.pitch for n in blk], [60, 63, 67])           # two chord tones under the note
        tp = h.tutti()
        self.assertEqual(len(tp), 8)
        pad = voicing.Harmony('Cm Ab', key='C minor').voice(('G4', 'Eb5'), 2, vel=50)
        self.assertEqual(len(pad), 4)
        self.assertTrue(all(67 <= n.pitch <= 75 for n in pad))

    def test_song_harmony_places_a_table(self):
        s = Song('t', tempo=100, key='C minor')
        a = s.section('a', bars=2)
        s.section('b', bars=4)
        h = s.harmony(self.T, s['b'])
        self.assertEqual(h.origin, 8.0)
        self.assertEqual(h.timeline()[0], (8.0, 4, 'Cm'))
        self.assertEqual(h.key.name, s.key.name)
        del a


class TestFugue(unittest.TestCase):
    SUBJ = 'D4:1 A4:1 Bb4:1.5 A4:.5 G4:.5 F4:.5 E4:.5 D4:.5 C#4:1 D4:1'
    ANS = 'A3:1 D4:1 F4:1.5 E4:.5 D4:.5 C4:.5 B3:.5 A3:.5 G#3:1 A3:1'
    H = [(0, 2, 'Dm'), (2, 2, 'Em7b5'), (4, 2, 'A7'), (6, 1, 'A7'), (7, 1, 'Dm'), (8, 8, 'Am'), (16, 8, 'Dm')]

    def test_entries_free_voices_and_leads(self):
        f = voicing.fugue([('B', 0, 'subject', -12), ('T', 8, 'answer'), ('A', 16, 'subject'),
                           ('B', 8, 'F3:2 E3:2 Eb3:1 D3:1 E3:1 F3:1', -5)],
                          subject=self.SUBJ, answer=self.ANS, harmony=self.H, key='D minor', at=10)
        self.assertEqual(f.leads, [('B', 10.0, 18.0), ('T', 18.0, 26.0), ('A', 26.0, 34.0)])
        self.assertEqual(f['S'], [])                                  # the soprano never enters
        for v in ('B', 'T', 'A'):
            for n in f.written[v]:
                self.assertIn(n[0], [m[0] for m in f[v]])              # the written notes stay (maybe shortened)
        self.assertEqual(f.lead('T', 20), 1)
        self.assertEqual(f.lead('B', 20), -1)
        self.assertEqual(f.lead('B', 40), 0)
        self.assertEqual(f.offset('T')((20, 1, 60)), 8)
        pts = f.emphasis('B', 40)
        self.assertEqual(pts[0], (9.5, 1.0))
        self.assertEqual(pts[-1], (40.0, 1.0))
        self.assertTrue(f.free)
        self.assertIsInstance(f.check(), list)

    def test_subject_harmony_and_final(self):
        f = voicing.fugue([('B', 0, 'subject', -12), ('T', 8, 'subject', -5)], subject=self.SUBJ,
                          subject_harmony=self.H[:5], key='D minor', final={'B': 'D3', 'T': 'A3'}, final_at=16,
                          counterpoint=False)
        self.assertEqual(f.harmony[5][2], 'Am')                       # the second entry's harmony, a fourth down
        with self.assertRaisesRegex(ComposeError, 'harmony'):
            voicing.fugue([('B', 0, 'subject')], subject=self.SUBJ)
        with self.assertRaisesRegex(ComposeError, 'voice set'):
            voicing.fugue([('X', 0, 'subject')], subject=self.SUBJ, harmony=self.H)

    def test_imitation_and_motif_fragments(self):
        im = voicing.imitation('G4:.5 Eb5:1 D5:.5 C5:1', [('ob', 0, 0), ('vn', 4, 12),
                                                         ('va', 8, ('C4', 'A4', 'G4', 'F4')), ('cl', 12, '-2d')],
                               key='C minor')
        self.assertEqual(im['vn'][0], (4.0, 0.5, 79))
        self.assertEqual([n[2] for n in im['va']], [60, 69, 67, 65])
        self.assertEqual(im['cl'][0][2], 63)                           # two scale steps down: Eb4
        m = Motif('1:1/8 3:1/8 r:1/8 5:1/4 4:1/8 3:1/4', 'C major')
        self.assertEqual(len(m.head(2)), 2)
        self.assertEqual(len(m.fragment(1, 3)), 3)                      # 3, the rest, 5
        self.assertEqual(len(m.fragment(-2)), 2)
        with self.assertRaises(ComposeError):
            m.fragment(10)


class TestScore(unittest.TestCase):
    def test_dynamics_map_and_velocities(self):
        s, (a, b_), band = stand_in()
        sc = orch.Score(s, band, {'a': [(0, 'p'), (8, 'f')], 'b': [(0, 40, 'step'), (8, 100)]}, seed=1, jitter=0)
        self.assertEqual(sc.level(0), 40)
        self.assertAlmostEqual(sc.level(4), (40 + 95) / 2)             # a hairpin
        self.assertEqual(sc.level(15.9), 95)                           # held until the step ...
        self.assertEqual(sc.level(16), 40)                             # ... subito
        self.assertEqual(sc.vel(0), 45)                                # the downbeat accent
        self.assertEqual(sc.vel(2), 56)                                # the half bar: 53.75 + 2
        with self.assertRaises(ComposeError):
            orch.Score(s, band, {'a': [(0, 'loud')]})
        sc2 = orch.Score(s, band, {'a': [(0, 'mf')]}, seed=9)
        sc3 = orch.Score(s, band, {'a': [(0, 'mf')]}, seed=9)
        self.assertEqual([sc2.vel(t) for t in range(8)], [sc3.vel(t) for t in range(8)])   # seeded

    def test_add_double_colla_parte(self):
        s, (a, b_), band = stand_in()
        sc = orch.Score(s, band, {'a': [(0, 78)]}, seed=1, jitter=0, phrasing={})
        sc.add('violins1', [(0, 2, 72), (2, 1, 74, 99)], off=4, dur=0.5, sf=[0])
        self.assertEqual(sc.parts['violins1'], [(0, 1.0, 72, 103, 'marcato'), (2, 0.5, 74, 99, 'sustain')])
        sc.add({'violas': [(0, 1, 60)], 'cellos': [(0, 1, 48)]}, 'staccato', off={'violas': -10}, roles=('cellos',))
        self.assertNotIn('violas', sc.parts)
        self.assertEqual(sc.parts['cellos'][0][4], 'staccato')
        sc.add('basses', [(0, 2, 36)], fig='pulse8')
        self.assertEqual(len(sc.parts['basses']), 4)
        sc.double([(4, 1, 67)], {'flutes': (12, -2), 'oboes': 0, 'clarinets': (-12, 0, {'dur': 2})})
        self.assertEqual(sc.parts['flutes'][0][2], 79)
        self.assertEqual(sc.parts['clarinets'][0][1], 2)
        sc.colla_parte({'S': [(8, 1, 72)], 'B': [(8, 1, 48)]},
                       {'violins2': ('S', -4), 'bassoons': (('S', 'B'), 0, -12)})
        self.assertEqual([n[2] for n in sc.parts['bassoons']], [60, 36])

    def test_hits_brass_unison_winds(self):
        s, (a, b_), band = stand_in()
        sc = orch.Score(s, band, {'a': [(0, 100)]}, seed=1)
        h = s.harmony([(4, 'Cm', 'G5', 'C3'), (4, 'G7', 'F5', 'G2')], a)
        sc.hits(h.tutti(), [0, 4], length=0.5, sf=True)
        self.assertEqual({n[4] for n in sc.parts['violins1']}, {'marcato'})
        self.assertEqual(len(sc.parts['basses']), 2)
        sc.brass(h, [0, 4], length=0.7)
        self.assertEqual(sorted(n[2] for n in sc.parts['trumpets'] if n[0] == 0), [72, 79])   # natural C5 G5 on Cm
        self.assertEqual([n[2] for n in sc.parts['timpani']], [48, 43])                       # C3 on Cm, G2 on G7
        sc.unison(8, 2, 'Ab')
        self.assertNotIn(8, [n[0] for n in sc.parts['trumpets']])     # Ab is not a natural note
        self.assertEqual([n[2] for n in sc.parts['violins2'] if n[0] == 8], [68, 80])
        sc.winds(h, roles=('oboes',))
        self.assertTrue(sc.parts['oboes'])
        self.assertNotIn('sustain', {n[4] for n in sc.parts['flutes']})     # roles=: only the oboes
        self.assertEqual(orch.natural_brass('D minor'), (62, 66, 69, 74, 78, 81))
        self.assertEqual(orch.timpani_tuning('D minor'), {2: 50, 9: 45})

    def test_perform_groups_folds_and_falls_back(self):
        s, (a, b_), band = stand_in()
        band.info['articulations']['horns'] = ['sustain']
        sc = orch.Score(s, band, {'a': [(0, 78)]}, seed=1)
        sc.add('horns', [(0, 1, 100)], 'marcato')                     # above C6: folded an octave down
        sc.add('horns', [(1, 1, 60)], 'staccato')
        played = sc.perform()
        ns = sorted(played['horns'], key=lambda n: n.start)
        self.assertEqual(ns[0].pitch, 76)
        self.assertEqual({art.articulation_of(n) for n in ns}, {'sustain'})     # neither exists: sustain

    def test_play_bed_stabs_fermata(self):
        s, (a, b_), band = stand_in()
        sc = orch.Score(s, band)
        self.assertEqual(sc.seed('violas', b_), sum(map(ord, 'violas')) + 16)
        h = s.prog('Cm G7')
        out = orch.bed(sc, h, a, violins2=('G4 Eb5', 2, 50), cellos=('root', 'C2', 60))
        self.assertEqual(set(out), {'violins2', 'cellos'})
        st = sc.stabs(h, b_, [0, 4], vel=110)
        self.assertEqual([n.pitch for n in sorted(st['timpani'], key=lambda n: n.start)], [48, 43])   # C3 / G2
        self.assertTrue(st['violins1'] and st['basses'] and st['horns'])
        fm = sc.fermata('E', b_, 3.9, {'violins1': ('G#5', 'E6'), 'trumpets': ('E4 G#4 B4', 90)}, vel=100, start=8)
        self.assertEqual({n.pitch % 12 for n in fm['violins1']}, {4, 8, 11})
        self.assertEqual({n.vel for n in fm['trumpets']}, {90})
        with self.assertRaises(ComposeError):
            orch.bed(sc, h, a, violas='G4')

    def test_follow_lets_held_notes_follow_the_map(self):
        f = lambda b: 40 + 10 * b                                     # noqa: E731  (a crescendo)
        c = Clip([(0, 4, 'C4', 40)], length=4)
        plain = art.expression_points(c, 'auto', long=8)
        followed = art.expression_points(c, 'auto', long=8, follow=f)
        self.assertEqual(len(plain), 1)
        self.assertGreater(len(followed), 3)
        self.assertGreater(followed[-1][1], followed[0][1])            # it grows inside the note
        flat = art.expression_points(c, 'auto', long=8, follow=lambda b: 70)
        self.assertEqual(flat, plain)                                  # no change in the map: the shape stays

    @unittest.skipUnless(have('sso'), 'needs the SSO pack')
    def test_score_on_the_symphony(self):
        s = Song('t', tempo=120, key='C minor', seed=3)
        s.section('a', bars=4)
        o = bands.symphony_orchestra(s, without=('percussion', 'harp', 'celesta', 'tuba', 'trombones'))
        sc = orch.Score(s, o, {'a': [(0, 'pp'), (16, 'ff')]}, seed=2)
        sc.add('violins1', [(0, 8, 72)])
        sc.perform()
        pts = dict(o.violins1._auto)['instrument.dynamics']
        self.assertGreater(len(pts), 3)                                # the held note follows the crescendo
        s.compile()


class TestChoir(unittest.TestCase):
    def test_speak_writes_the_written_level_on_expression(self):
        s, (a, b_), _ = stand_in()
        tr = s.track('choir', inst.va())
        ch = orch.Choir(s, lane='expression', speak=120)
        ch.speak(tr, Clip([(4, 1, 'C4', 60), (6, 1, 'D4', 120)], length=0))
        self.assertEqual({n.vel for n in tr.clip()}, {120})
        lane = ch.expr['choir']
        self.assertEqual(lane[1][1], 0.5)
        self.assertEqual(lane[-1][1], 1.0)
        ch.lane(tr, [(8, 1.0)]).write()
        self.assertIn('instrument.expression', dict(tr._auto))

    def test_sing_perform_lanes_and_gate(self):
        s, (a, b_), band = stand_in()
        trs = {'S': s.track('s_', inst.va()), 'B': s.track('b_', inst.va())}
        ch = orch.Choir(s, trs, lane='dynamics', speak=116, gate=(0, 32))
        sc = orch.Score(s, band, {'a': [(0, 70)]}, seed=4)
        sc.sing(ch, 'S', [(4, 1, 72), (6, 3, 74), (10, 1, 72)], dur=0.6)
        sc.sing(ch, 'B', [(4, 8, 48)])
        ch.swell('S', [(4, 1, 72)], 4, 12, 4)
        ch.perform()
        auto = dict(trs['S']._auto)
        self.assertIn('instrument.dynamics', auto)
        self.assertIn('instrument.expression', auto)                    # swells + the syllable gate
        self.assertTrue(all(96 <= n.vel <= 124 for n in trs['S'].clip()))
        self.assertLess(min(n.start for n in trs['B'].clip()), 4.0)    # started early
        sw = orch.swells([(0, 1, 72)], 0, 8, 4)
        self.assertEqual(sw[0], (-0.3, 1.0))


class TestOneCalls(unittest.TestCase):
    def test_orch_sing_in_one_call(self):
        s, (a, b_), _ = stand_in()
        tr = s.track('choir', inst.va())
        orch.sing(tr, Clip([(4, 2, 'C4', 50), (6, 2, 'Eb4', 90)], length=0), swell=(4, 8, 4))
        self.assertEqual({n.vel for n in tr.clip()}, {120})
        self.assertIn('instrument.expression', dict(tr._auto))
        tr2 = s.track('choir2', inst.va())
        orch.sing(tr2, [(4, 2, 60, 50), (8, 1, 62, 90)], lane='dynamics', speak=110)
        self.assertIn('instrument.dynamics', dict(tr2._auto))

    def test_module_aliases_and_the_default_bed(self):
        s, (a, b_), band = stand_in()
        sc = orch.Score(s, band, {'a': [(0, 80)]}, seed=1)
        orch.double(sc, [(0, 1, 60)], {'flutes': 12})
        orch.colla_parte(sc, {'S': [(1, 1, 72)]}, {'oboes': ('S', 0)})
        orch.hits(sc, {'v1': [(0, 4, 84)]}, [0], roles=('flutes',))
        orch.unison(sc, 2, 1, 'G')
        self.assertEqual([n[2] for n in sc.parts['flutes']], [72, 84, 79, 91])
        out = orch.bed(band, s.prog('Cm Fm'), b_, vel=50)                # a band: a Score is made for it
        self.assertEqual(list(out), ['violins1', 'violins2', 'violas', 'cellos', 'basses'])
        self.assertTrue(all(55 <= n.pitch <= 64 for n in out['violas']))


class TestArc(unittest.TestCase):
    def test_arc_rides_the_master_input(self):
        s, (a, b_), _ = stand_in()
        s.arc({'a': -1.5, 'b': 2.0}, within={'b': [(4, 0.0, 'smooth')]})
        self.assertEqual(s.master.fx[0].type, 'utility')
        pts = dict(s.master._auto)['fx.arc.gain']
        self.assertEqual(pts, [(0.0, -1.5), (15.5, -1.5), (16.0, 2.0, 'smooth'), (20.0, 0.0, 'smooth')])
        with self.assertRaisesRegex(ComposeError, 'unknown section'):
            s.arc({'chorus': 1.0})


if __name__ == '__main__':
    unittest.main()
