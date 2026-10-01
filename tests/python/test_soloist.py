"""The soloist (agentsound/soloist.py) and the shared budget (agentsound/budget.py): the interface (Move,
Vocabulary, Ctx, Part), the arc (stages in order, required stages, space at phrase ends), motivic development, move
choice by role / energy / density, the budget (spice / fast spacing, fast only in burst / climax, refused moves
replaced and logged), dynamics never flat, determinism, warnings - with a toy vocabulary (instrument-agnostic) and
the guitar's (guitarist.vocabulary)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Song, guitarist as gtr, soloist  # noqa: E402
from agentsound.budget import Budget  # noqa: E402
from agentsound.patterns import Clip, Note  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

BPM = 100
MOTIF = Clip([(0, 0.5, 'A4', 90), (0.5, 0.5, 'C5', 90), (1, 1.5, 'E5', 100), (3, 0.5, 'D5', 90), (3.5, 2, 'C5', 96)],
             length=8)


def toy_vocab(calls=None, flat=False):
    """Every move plays one note per beat (pitch by its energy); calls collects (name, ctx)."""
    def mk(name, pitch):
        def play(ctx):
            if calls is not None:
                calls.append((name, ctx))
            n = max(1, int(ctx.beats))
            v = 90 if flat else None
            return Clip._raw([Note(float(i), 0.9, pitch, v or int(ctx.vel[0] + (ctx.vel[1] - ctx.vel[0]) * i / n))
                              for i in range(n)], ctx.beats)
        return play

    def motif_play(ctx):
        if calls is not None:
            calls.append(('motif', ctx))
        return ctx.motif

    moves = [soloist.Move('motif', 0, 0.4, 0.4, False, motif_play, roles=('motif',)),
             soloist.Move('answer', 0, 0.5, 0.5, False, mk('answer', 60), roles=('answer', 'resolve', 'develop')),
             soloist.Move('run', 0, 0.9, 0.95, True, mk('run', 72), fast=True, roles=('burst',)),
             soloist.Move('scale', 0, 0.75, 0.8, False, mk('scale', 70), roles=('burst', 'develop')),
             soloist.Move('scream', 0, 1.0, 0.3, True, mk('scream', 84), roles=('climax',)),
             soloist.Move('long', 0, 0.8, 0.2, False, mk('long', 79), roles=('climax', 'resolve')),
             soloist.Move('home', 0, 0.35, 0.3, False, mk('home', 57), roles=('resolve',))]
    return soloist.Vocabulary(moves, name='toy')


def song(bars=16):
    s = Song('t', tempo=BPM, key='A minor', seed=2)
    sec = s.section('solo', bars=bars)
    tr = s.track('lead', 'synthwave/supersaw_lead')
    return s, sec, tr


class Interface(unittest.TestCase):
    def test_rest_scale(self):
        def played(rest):
            v = toy_vocab()
            v.rest = rest
            s, sec, tr = song()
            p = soloist.solo(s, tr, v, at=sec, motif=MOTIF, seed=3, place=False)
            return sum(n.dur for n in p.clip)
        self.assertGreater(played(0.4), played(1.0))          # a drummer leaves less space than a horn
        with self.assertRaises(ComposeError):
            soloist.Vocabulary(toy_vocab().moves, rest=1.5)

    def test_move_validation(self):
        with self.assertRaises(ComposeError):
            soloist.Move('x', 0, 1.5, 0.5, False, lambda c: None)
        with self.assertRaises(ComposeError):
            soloist.Move('x', 0, 0.5, 0.5, False, lambda c: None, fast=True)       # fast must be spice
        with self.assertRaises(ComposeError):
            soloist.Move('x', 0, 0.5, 0.5, False, lambda c: None, roles=('chorus',))
        with self.assertRaises(ComposeError):
            soloist.Vocabulary([])
        m = soloist.Move('x', 0, 0.5, 0.5, False, lambda c: None)
        with self.assertRaises(ComposeError):
            soloist.Vocabulary([m, m])

    def test_part_shift_and_merge(self):
        a = soloist.Part(Clip([(0, 1, 60, 90)], length=1), log=[(0, 1, 'x', 'a')], steps={'bendfollow': [(0.0, 1.0)]})
        b = a.shifted(4).merge(soloist.Part(Clip([(1, 1, 62, 90)], length=2)))
        self.assertEqual(sorted(n.start for n in b.clip), [1.0, 4.0])
        self.assertEqual(b.steps['bendfollow'], [(4.0, 1.0)])

    def test_development(self):
        k = 'A minor'
        self.assertEqual([n.pitch for n in soloist.develop(MOTIF, 'sequence', key=k, steps=1)], [71, 74, 77, 76, 74])
        self.assertEqual(len(soloist.develop(MOTIF, 'fragment', beats=2)), 3)
        self.assertEqual([n.pitch for n in soloist.develop(MOTIF, 'octave', steps=1)], [81, 84, 88, 86, 84])
        self.assertEqual(soloist.develop(MOTIF, 'displace', by=0.5)[0].start, 0.5)
        with self.assertRaises(ComposeError):
            soloist.develop(MOTIF, 'mangle')
        for how in soloist.DEVELOPMENTS:
            self.assertTrue(len(soloist.develop(MOTIF, how, key=k)))


class Arc(unittest.TestCase):
    def test_classic_arc_in_order_with_required_stages(self):
        s, sec, tr = song(16)
        p = soloist.solo(s, tr, toy_vocab(), at=sec, motif=MOTIF, seed=1, place=False)
        names = [st for st, *_ in p.stages]
        self.assertEqual(names, ['statement', 'answer', 'develop', 'burst', 'climax', 'resolve'])
        self.assertEqual(p.stages[0][1], 0.0)
        self.assertEqual(p.stages[-1][2], 64.0)
        energies = {st: e for st, _, _, e in p.stages}
        self.assertLess(energies['statement'], energies['develop'])
        self.assertEqual(max(energies, key=energies.get), 'climax')
        short = soloist.solo(s, tr, toy_vocab(), at=(0, 4), motif=MOTIF, arc='classic', seed=1, place=False)
        self.assertIn('climax', [st for st, *_ in short.stages], 'a required stage survives a short solo')
        self.assertIn('resolve', [st for st, *_ in short.stages])
        with self.assertRaises(ComposeError):
            soloist.solo(s, tr, toy_vocab(), at=sec, arc='epic', place=False)

    def test_motif_first_space_and_roles(self):
        calls = []
        s, sec, tr = song(16)
        p = soloist.solo(s, tr, toy_vocab(calls), at=sec, motif=MOTIF, seed=1, place=False)
        self.assertEqual(calls[0][0], 'motif', 'the solo opens with the motif')
        self.assertEqual([n.pitch for n in calls[0][1].motif], [n.pitch for n in MOTIF], 'stated as given')
        by_stage = p.summary()
        self.assertIn(by_stage['burst'][0], ('run', 'scale'))
        self.assertIn(by_stage['climax'][0], ('scream', 'long'))
        # space: every phrase leaves its end silent (the stage's rest share)
        for i in range(8):
            a, b = 8 * i, 8 * (i + 1)
            ends = [n.start + n.dur for n in p.clip if a <= n.start < b]
            if ends:
                self.assertLess(max(ends), b - 0.5, f'phrase {i} breathes')
        # register and dynamics follow the arc
        ctx_of = {c.stage: c for _, c in calls}
        self.assertLess(ctx_of['statement'].register, ctx_of['climax'].register)
        self.assertLess(ctx_of['statement'].vel[1], ctx_of['climax'].vel[1])

    def test_budget_refuses_fast_moves_outside_burst_and_too_close(self):
        s, sec, tr = song(32)
        bud = soloist.Budget(spice_every=1.5, fast_every=8, same_every=16)
        p = soloist.solo(s, tr, toy_vocab(), at=sec, motif=MOTIF, seed=3, budget=bud, place=False)
        fast = [t for t, name in p.budget['kept'] if name == 'run']
        self.assertTrue(all(b - a >= 32 - 1e-6 for a, b in zip(fast, fast[1:])), 'fast moves 8 bars apart')
        runs = [(a, st) for a, st, _, name, _ in p.parts if name == 'run']
        self.assertTrue(all(st in ('burst', 'climax') for _, st in runs))
        # a song-wide budget: a second solo counts the first one's tricks
        p2 = soloist.solo(s, tr, toy_vocab(), at=(64, 4), motif=MOTIF, seed=3, budget=bud, place=False)
        self.assertTrue(all(abs(t - u) >= 6 - 1e-6 for t, _ in p2.budget['kept'] for u, _ in p.budget['kept']))
        tight = soloist.solo(s, tr, toy_vocab(), at=sec, motif=MOTIF, seed=3, place=False,
                             budget={'spice_every': 64, 'fast_every': 64, 'same_every': 64})
        self.assertTrue(tight.budget['dropped'] or len(tight.budget['kept']) <= 1)
        for _, name, sub in tight.budget['dropped']:
            self.assertIsNotNone(sub, f'{name}: replaced by a plain move')

    def test_flat_phrases_get_dynamics_and_determinism(self):
        s, sec, tr = song(16)
        p = soloist.solo(s, tr, toy_vocab(flat=True), at=sec, motif=MOTIF, seed=1, place=False)
        vs = [n.vel for n in p.clip if 8 <= n.start < 16]
        self.assertGreaterEqual(max(vs) - min(vs), 10, 'a flat phrase is shaped (humanize.touch)')
        q = soloist.solo(s, tr, toy_vocab(flat=True), at=sec, motif=MOTIF, seed=1, place=False)
        self.assertEqual(list(p.clip), list(q.clip))

    def test_failing_move_is_a_warning_and_place_adds_advice(self):
        def boom(ctx):
            raise ComposeError('no strings')
        v = soloist.Vocabulary([soloist.Move('motif', 0, 0.4, 0.4, False, boom, roles=('motif',)),
                                soloist.Move('any', 0, 0.5, 0.5, False, lambda c: Clip([(0, 1, 60, 90)], length=1))])
        s, sec, tr = song(8)
        p = soloist.solo(s, tr, v, at=sec, motif=MOTIF, seed=1)
        self.assertTrue(any('no strings' in w for w in p.warnings))
        self.assertTrue(any(w.startswith("soloist on 'lead'") for w in s.advice))
        self.assertGreater(len(tr._notes), 0)

    def test_sections_list_and_tuple(self):
        s = Song('t', tempo=BPM, key='A minor')
        a = s.section('solo1', bars=8)
        s.section('verse', bars=8)
        b = s.section('solo2', bars=8)
        tr = s.track('lead', 'synthwave/supersaw_lead')
        p = soloist.solo(s, tr, toy_vocab(), at=[a, b], motif=MOTIF, seed=1, place=False)
        self.assertFalse(any(32 <= n.start + p.start < 64 for n in p.clip), 'nothing between the sections')
        self.assertEqual(p.stages[-1][0], 'resolve')
        with self.assertRaises(ComposeError):
            soloist.solo(s, tr, toy_vocab(), at='solo1', place=False)


class SharedBudget(unittest.TestCase):
    def test_spacing_slots_scores_saved(self):
        b = Budget({'spice': 8, 'fast': 32}, same_every=64, min_score={'fast': 2.0}, phrase_gap={'fast': 1})
        c = [dict(t=0, cls='spice', name='a', score=1), dict(t=4, cls='spice', name='b', score=2),
             dict(t=10, cls='fast', name='trill', score=1.5), dict(t=12, cls='fast', name='trill', score=2.5, phrase=3),
             dict(t=14, cls='spice', name='c', score=1, slot=('n1',)), dict(t=40, cls='spice', name='d', score=1,
                                                                             slot=('n1',))]
        kept = b.keep(c, base=100)
        self.assertEqual([x['name'] for x in kept], ['trill', 'b', 'c'], 'best first, 8 beats apart, score floor, slots')
        self.assertFalse(b.allows(130, 'fast', 'shake'))
        self.assertTrue(b.allows(150, 'fast', 'shake', phrase=6))
        self.assertFalse(b.allows(150, 'fast', 'trill'), 'same name 64 beats apart')
        b.save(200)
        self.assertFalse(b.allows(190, 'fast', 'x'))
        self.assertTrue(b.allows(190, 'fast', 'x', span=(180, 220)), 'a saved moment is the call that contains it')


class GuitarVocabulary(unittest.TestCase):
    def test_every_move_plays_in_range_and_in_its_slot(self):
        s = Song('t', tempo=BPM, key='A minor', seed=4)
        sec = s.section('solo', bars=8)
        tr = s.track('lead', 'synthwave/supersaw_lead')
        prog = s.prog('Am F C G', bars=2)
        voc = gtr.vocabulary('rock')
        for m in voc.moves:
            for stage, reg in (('statement', 0.2), ('climax', 1.0)):
                bud = soloist.Budget()
                ctx = soloist.Ctx(song=s, track=tr, vocab=voc, at=8.0, beats=6.0, bpm=BPM, bpb=4.0,
                                  key=s.key, prog=prog, stage=stage, role='lead', energy=0.9 if stage == 'climax'
                                  else 0.4, density=0.6, register=reg, vel=(70, 115), motif=MOTIF, phrase=1,
                                  phrases=8, progress=0.3, last=None, next_at=16.0, rng=__import__('random').Random(1),
                                  budget=bud, memory={}, solo_start=0.0, phrase_start=8.0, phrase_beats=8.0,
                                  range=voc.range)
                part = soloist.Part.of(m.play(ctx))
                ps = [n.pitch for n in part.clip]
                self.assertTrue(all(43 <= p <= 90 for p in ps), f"{m.name}: {ps}")
                if m.name not in ('wah',):
                    self.assertTrue(len(part.clip) or part.aux, f"{m.name} played nothing")
                self.assertTrue(all(n.start < 6.0 + 1e-6 for n in part.clip), f"{m.name} starts inside its slot")

    def test_a_rock_solo(self):
        s = Song('t', tempo=BPM, key='A minor', seed=4)
        sec = s.section('solo', bars=16)
        tr = s.track('lead', 'synthwave/supersaw_lead')
        prog = s.prog('Am F C G', bars=2)
        p = soloist.solo(s, tr, gtr.vocabulary('rock'), at=sec, prog=prog, motif=MOTIF, seed=9, place=False)
        self.assertEqual(p.warnings, [])
        played = [name for *_, name, _ in p.parts]
        self.assertEqual(played[0], 'motif')
        self.assertTrue(p.gestures, 'bends / vibrato as gestures')
        names = {g.name for g in p.gestures}
        self.assertIn('vibrato', names)
        with self.assertRaises(ComposeError):
            gtr.vocabulary('polka')
        b = gtr.vocabulary('blues')
        self.assertNotIn('sweep', [m.name for m in b.moves], 'blues: no sweeps')


class OneWrapperManyPlayers(unittest.TestCase):
    def test_the_same_arc_with_the_guitar_and_the_sax(self):
        from agentsound import hornist
        s = Song('t', tempo=BPM, key='A minor', seed=4)
        sec = s.section('solo', bars=16)
        prog = s.prog('Am F C G', bars=2)
        g = s.track('gtr', 'synthwave/supersaw_lead')
        x = s.track('sax', 'synthwave/supersaw_lead')
        pg = soloist.solo(s, g, gtr.vocabulary('rock'), at=sec, prog=prog, motif=MOTIF, seed=9, place=False)
        px = soloist.solo(s, x, hornist.vocabulary('sax', style='hero'), at=sec, prog=prog, motif=MOTIF, seed=9,
                          place=False)
        self.assertEqual(pg.stages, px.stages, 'one arc, whoever plays it')
        self.assertEqual(px.warnings, [])
        self.assertEqual([n for *_, n, _ in px.parts][0], 'motif')
        ps = [n.pitch for n in px.clip]
        self.assertTrue(all(60 - 1 <= p <= 81 + 1 for p in ps), f'inside the sax range: {min(ps)}..{max(ps)}')
        names = {gs.name for gs in px.gestures}
        self.assertTrue(names & {'swell', 'push', 'bloom', 'vibrato'}, f'breath moves: {names}')
        stage_of = {a: st for a, st, *_ in px.parts}
        self.assertTrue(any(st == 'climax' for st in stage_of.values()))

    def test_saved_moment_inside_one_solo(self):
        # budget.save(beat) inside the solo: only the phrase that contains it may spend the fast budget, the
        # phrases before it keep their fast figures fast_every bars away (a saved climax gets the trill)
        s, sec, tr = song(32)
        bud = soloist.Budget(spice_every=1.5, fast_every=8, same_every=16).save(96.0)
        p = soloist.solo(s, tr, toy_vocab(), at=sec, motif=MOTIF, seed=3, budget=bud, place=False)
        fast = [t for t, name in p.budget['kept'] if name == 'run']
        self.assertTrue(all(abs(t - 96.0) >= 32 - 1e-6 or 96.0 <= t < 104.0 for t in fast), fast)

    def test_sax_solo_places_with_the_default_renderer(self):
        from agentsound import hornist
        s = Song('t', tempo=BPM, key='A minor', seed=4)
        sec = s.section('solo', bars=8)
        sax = s.track('sax', 'synthwave/supersaw_lead')
        soloist.solo(s, sax, hornist.vocabulary('trumpet'), at=sec, prog=s.prog('Am F C G', bars=2), motif=MOTIF,
                     seed=2)
        self.assertGreater(len(sax._notes), 8)
        self.assertTrue(any(t.startswith('fx.air') or t == 'instrument.pitchbend' for t, _ in sax._auto))
        s.compile()
        with self.assertRaises(ComposeError):
            hornist.vocabulary('bagpipe')


class PianoVocabulary(unittest.TestCase):
    """pianist.vocabulary(): the soloist's arc played by the pianist's hands (agentsound/piano_vocab.py)."""

    def setUp(self):
        from agentsound import pianist
        self.pianist = pianist
        self.s = Song('t', tempo=126, key='F major', seed=4)
        self.prog = self.s.prog('Fmaj9 Bb9#11 Gm9 C13 | Am7 D7b9 Gm9:0.5 C7b9:0.5 Cm9:0.5 F13:0.5')
        self.sec = self.s.section('solo', bars=16)
        self.rh = self.s.track('piano', 'sampled/jazz_grand')
        self.lh = self.s.track('comp', 'sampled/jazz_grand')
        self.hook = Clip([(0.5, 0.5, 'C5', 90), (1, 1.5, 'A5', 100), (2.5, 0.5, 'G5', 90), (3, 3, 'E5', 96)],
                         length=8)

    def test_every_move_plays_harmonized_in_range_and_in_its_slot(self):
        voc = self.pianist.vocabulary('straight')
        for m in voc.moves:
            for stage, reg, dens in (('statement', 0.2, 0.3), ('climax', 1.0, 0.9)):
                ctx = soloist.Ctx(song=self.s, track=self.rh, vocab=voc, at=8.0, beats=6.0, bpm=126, bpb=4.0,
                                  key=self.s.key, prog=self.prog, stage=stage, role='lead',
                                  energy=0.95 if stage == 'climax' else 0.4, density=dens, register=reg,
                                  vel=(70, 112), motif=self.hook, phrase=1, phrases=8, progress=0.3, last=None,
                                  next_at=16.0, rng=__import__('random').Random(1), budget=soloist.Budget(),
                                  memory={}, solo_start=0.0, phrase_start=8.0, phrase_beats=8.0, range=voc.range)
                part = soloist.Part.of(m.play(ctx))
                self.assertTrue(len(part.clip), f'{m.name} played nothing')
                ps = [n.pitch for n in part.clip]
                self.assertTrue(all(55 <= p <= 90 for p in ps), f'{m.name}: right hand {min(ps)}..{max(ps)}')
                self.assertTrue(all(-0.1 < n.start < 6.0 + 1e-6 for n in part.clip), f'{m.name} inside its slot')
                onsets: dict = {}
                for n in part.clip:
                    onsets.setdefault(round(n.start, 1), set()).add(n.pitch)
                if m.name in ('motif', 'block', 'octaves', 'riff'):
                    self.assertTrue(any(len(v) > 1 for v in onsets.values()), f'{m.name}: harmonized, not a bare line')

    def test_a_piano_solo_with_both_hands_the_pedal_and_the_budget(self):
        s, sec = self.s, self.sec
        mem = self.pianist.Memory()
        bud = soloist.Budget(spice_every=2, fast_every=16, same_every=32).save(48.0)
        voc = self.pianist.vocabulary('straight', lh_track=self.lh, memory=mem, seed=3)
        p = soloist.solo(s, self.rh, voc, at=sec, prog=self.prog, motif=self.hook, seed=5, budget=bud)
        self.assertEqual(p.warnings, [])
        self.assertEqual([n for *_, n, _ in p.parts][0], 'motif')
        fast = [(t, n) for t, n in p.budget['kept'] if n in ('trill', 'tremolo', 'octave_run')]
        self.assertLessEqual(len(fast), 1, f'one fast figure in 16 bars: {fast}')
        self.assertTrue(all(48.0 <= t < 56.0 for t, _ in fast), f'the saved moment spends it: {fast}')
        self.assertGreater(len(self.lh._notes), 8, 'the left hand comps under the solo')
        self.assertTrue(all(n.pitch <= 72 for n in self.lh._notes))
        self.assertTrue(any(t == 'instrument.pedal' for t, _ in self.rh._auto), 'the harmony pedal')
        vs = [n.vel for n in p.clip]
        self.assertGreaterEqual(max(vs) - min(vs), 25, 'dynamics follow the arc')
        q = soloist.solo(s, self.rh, self.pianist.vocabulary('straight', seed=3), at=sec, prog=self.prog,
                         motif=self.hook, seed=5, budget=soloist.Budget(spice_every=2, fast_every=16,
                                                                        same_every=32).save(48.0), place=False)
        self.assertEqual(list(p.clip), list(q.clip), 'deterministic')
        s.compile()

    def test_options(self):
        with self.assertRaises(ComposeError):
            self.pianist.vocabulary('polka')
        with self.assertRaises(ComposeError):
            self.pianist.vocabulary(lh='walking')
        with self.assertRaises(ComposeError):
            self.pianist.vocabulary(moves=['motif', 'shred'])
        v = self.pianist.vocabulary('ballad', weights={'octave_run': 0})
        self.assertNotIn('octave_run', [m.name for m in v.moves])
        self.assertEqual(v.budget['fast_every'], 12)

    def test_held_notes_fit_the_harmony(self):
        # the motif's E held over a D7b9 is an avoid note against the b9: the vocabulary moves it to a chord tone
        from agentsound.piano_vocab import _fit_harmony
        prog = self.s.prog('D7b9')
        ctx = soloist.Ctx(prog=prog, at=0.0, solo_start=0.0, key=self.s.key)
        c = _fit_harmony(ctx, Clip([(0, 2, 'E5', 90), (2.5, 0.5, 'E5', 80)], length=4))
        self.assertNotEqual(c.notes[0].pitch % 12, 4, 'the held E moved')
        self.assertEqual(c.notes[1].pitch % 12, 4, 'a short off-beat passing note stays')


if __name__ == '__main__':
    unittest.main()
