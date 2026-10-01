"""The drummer's solo technique: the stroke language, the hands' physics, rudiments, feet, hi-hat openness,
chokes, the solo moves, DrumMotif and perform()."""
import pathlib
import statistics
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import drummer  # noqa: E402
from agentsound.song import Song  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

BPM = 112
RUSTY = drummer.Kit.of('big_rusty_kit')


def hand_hits(hs):
    return sorted((h for h in hs if h.limb in ('R', 'L') and h.tag not in ('grace', 'bounce')), key=lambda h: h.t)


class TestStrokeLanguage(unittest.TestCase):
    def test_tokens_kinds_limbs(self):
        hs = drummer.strokes('>R l R@tom1 L+K - P', grid=0.25, kit=RUSTY, energy=0.8)
        self.assertEqual([(h.t, h.limb, h.kind, h.piece) for h in hs],
                         [(0.0, 'R', 'A', 'snare'), (0.25, 'L', 'G', 'snare'), (0.5, 'R', 'T', 'tom1'),
                          (0.75, 'L', 'T', 'snare'), (0.75, 'RF', 'T', 'kick'), (1.25, 'LF', 'T', 'hat_pedal')])
        acc, ghost, tap = hs[0].vel, hs[1].vel, hs[2].vel
        self.assertTrue(acc > tap > ghost)
        self.assertTrue(15 <= ghost <= 35)

    def test_split_steps_voices_rimshot_flags(self):
        hs = drummer.strokes('RL ^R fL@2 dR zL', grid=0.5, kit=RUSTY)
        self.assertEqual([round(h.t, 3) for h in hs], [0.0, 0.25, 0.5, 1.0, 1.5, 2.0])
        self.assertEqual(hs[2].piece, 'rimshot')
        self.assertEqual(hs[3].piece, 'tom2')            # @2 = the kit's voice 2 (snare 0, tom1 1, tom2 2)
        self.assertEqual([h.fx for h in hs[3:]], ['f', 'd', 'z'])

    def test_bad_tokens(self):
        for bad in ('X', 'R@', '>', 'Rq'):
            with self.assertRaises(ComposeError):
                drummer.strokes(bad)

    def test_orchestrations(self):
        split = drummer.strokes('R L R L', kit=RUSTY, orchestrate='split')
        self.assertEqual({h.piece for h in split if h.limb == 'R'}, {'tom4'})
        self.assertEqual({h.piece for h in split if h.limb == 'L'}, {'snare'})
        acc = drummer.strokes('>R l >L r >R l', kit=RUSTY, orchestrate='accents')
        self.assertEqual([h.piece for h in acc if h.kind == 'A'], ['tom1', 'tom2', 'tom3'])
        self.assertEqual({h.piece for h in acc if h.kind == 'G'}, {'snare'})
        down = drummer.strokes('R L R L ' * 5, kit=RUSTY, orchestrate='down', group=4)
        order = []
        for h in down:
            if not order or order[-1] != h.piece:
                order.append(h.piece)
        self.assertEqual(order, ['snare', 'tom1', 'tom2', 'tom3', 'tom4'])

    def test_shape(self):
        hs = drummer.strokes('R L ' * 8, kit=RUSTY, shape='cresc', seed=1)
        self.assertLess(hs[0].vel, hs[-1].vel * 0.75)


class TestHands(unittest.TestCase):
    def test_weak_hand_softer_and_later(self):
        hs = drummer.strokes('R L ' * 64, grid=0.25, energy=0.7, seed=2)
        drummer.perform_hits(hs, BPM, hands=drummer.Hands(weak=0.6), seed=2)
        r = [h for h in hs if h.limb == 'R']
        l_ = [h for h in hs if h.limb == 'L']
        self.assertGreater(statistics.mean(h.vel for h in r), statistics.mean(h.vel for h in l_))
        self.assertGreater(statistics.mean(h.off for h in l_), statistics.mean(h.off for h in r))
        self.assertGreater(statistics.pstdev(h.off for h in l_), statistics.pstdev(h.off for h in r))

    def test_double_rebound_weaker_than_first(self):
        hs = drummer.strokes('RR LL ' * 32, grid=0.25, energy=0.7, seed=3)
        drummer.perform_hits(hs, BPM, hands=drummer.Hands(evenness=0.3, height=0.0), seed=3)
        firsts = [h.vel for i, h in enumerate(hand_hits(hs)) if i % 2 == 0]
        seconds = [h.vel for i, h in enumerate(hand_hits(hs)) if i % 2 == 1]
        self.assertLess(statistics.mean(seconds), statistics.mean(firsts) * 0.95)

    def test_flam_drag_buzz(self):
        hs = drummer.strokes('fR - dL - zR - -', grid=0.5, energy=0.7, seed=4)
        drummer.perform_hits(hs, BPM, seed=4)
        main = {h.t: h for h in hs if h.tag != 'grace' and h.tag != 'bounce'}
        graces = [h for h in hs if h.tag == 'grace']
        flam = [g for g in graces if g.main is main[0.0]]
        self.assertEqual(len(flam), 1)
        self.assertEqual(flam[0].limb, 'L')
        gap = (0.0 - flam[0].t) * 60000 / BPM
        self.assertTrue(16 <= gap <= 31, gap)
        self.assertLess(flam[0].vel, main[0.0].vel * 0.5)
        drag = [g for g in graces if g.main is main[1.0]]
        self.assertEqual(len(drag), 2)
        self.assertEqual({g.limb for g in drag}, {'R'})
        bounces = [h for h in hs if h.tag == 'bounce']
        self.assertTrue(3 <= len(bounces) <= 6)
        self.assertTrue(all(b.vel < main[2.0].vel for b in bounces))
        gaps = [bounces[i + 1].t - bounces[i].t for i in range(len(bounces) - 1)]
        self.assertTrue(all(gaps[i + 1] <= gaps[i] + 1e-9 for i in range(len(gaps) - 1)))   # bounces close in

    def test_upstroke_limits_fast_accents(self):
        slow = drummer.strokes('R >R', grid=1.0, energy=0.8)
        fast = drummer.strokes('R >R', grid=0.25, energy=0.8)
        h0 = drummer.Hands(height=0.0, timing_ms=0.0)
        drummer.perform_hits(slow, 60, hands=h0)
        drummer.perform_hits(fast, 240, hands=h0)
        self.assertGreater(slow[1].vel - slow[0].vel, (fast[1].vel - fast[0].vel) * 1.4)

    def test_speed_limits(self):
        self.assertEqual(drummer.sticking_problems(drummer.strokes('R L ' * 8, grid=0.125), 120), [])
        probs = drummer.sticking_problems(drummer.strokes('R L ' * 8, grid=0.125), 260)
        self.assertTrue(probs and 'needs 70 ms' in probs[0])
        self.assertEqual(drummer.sticking_problems(drummer.strokes('RR LL ' * 4, grid=0.25), 160), [])
        self.assertTrue(drummer.sticking_problems(drummer.strokes('R+R@tom1'), 120))       # one hand, two drums
        self.assertTrue(drummer.sticking_problems(drummer.strokes('K K K K', grid=0.125), 200))

    def test_named_hands_and_errors(self):
        self.assertLess(drummer.HANDS['master'].weak, drummer.HANDS['student'].weak)
        with self.assertRaises(ComposeError):
            drummer.Hands(lead='X')
        with self.assertRaises(ComposeError):
            drummer.Hands(weak=2)


class TestRudiments(unittest.TestCase):
    def test_every_rudiment_plays(self):
        for name in drummer.RUDIMENTS:
            c = drummer.rudiment(name, 100, beats=4, kit=RUSTY, seed=1)
            self.assertGreater(len(c), 3, name)

    def test_paradiddle_sticking_and_mirror(self):
        hs = drummer.strokes(drummer.RUDIMENTS['paradiddle'][0])
        self.assertEqual(''.join(h.limb for h in hs), 'RLRRLRLL')
        c = drummer.rudiment('paradiddle', BPM, kit=RUSTY, orchestrate='split', seed=1)
        self.assertEqual([n.pitch for n in c][:4], [41, 38, 41, 41])
        cl = drummer.rudiment('paradiddle', BPM, kit=RUSTY, orchestrate='split', lead='L', seed=1)
        self.assertEqual([n.pitch for n in cl][:4], [38, 41, 38, 38])

    def test_too_fast_raises_with_limit(self):
        with self.assertRaises(ComposeError) as cm:
            drummer.rudiment('single_stroke_roll', 260, grid=0.125, beats=2)
        self.assertIn('single_ms', str(cm.exception))
        with self.assertRaises(ComposeError):
            drummer.rudiment('paradidle', 100)

    def test_flam_accent_has_graces(self):
        c = drummer.rudiment('flam_accent', 100, beats=2, kit=RUSTY, seed=2)
        starts = sorted(n.start for n in c)
        close = [b - a for a, b in zip(starts, starts[1:]) if (b - a) * 60000 / 100 < 35]
        self.assertGreaterEqual(len(close), 2)


class TestFeetHatChoke(unittest.TestCase):
    def test_double_bass_alternates_feet(self):
        hs = drummer._feet('double', 0.0, 4.0, 0.8, 4, BPM, drummer.Hands())
        self.assertEqual([h.limb for h in hs][:4], ['RF', 'LF', 'RF', 'LF'])
        self.assertEqual({h.piece for h in hs}, {'kick'})
        self.assertEqual(len(drummer.double_bass(4, BPM, kit=RUSTY)), 16 + 3)

    def test_chick_clave(self):
        ch = drummer._feet('chick', 0.0, 8.0, 0.5, 4, BPM, drummer.Hands())
        self.assertEqual([h.t for h in ch], [1.0, 3.0, 5.0, 7.0])
        cl = drummer._feet('clave', 0.0, 8.0, 0.5, 4, BPM, drummer.Hands())
        self.assertEqual(sorted(h.t for h in cl if h.piece == 'kick'), [0.0, 1.5, 3.0, 5.0, 6.0])
        with self.assertRaises(ComposeError):
            drummer.feet('waltz', 1, BPM)

    def test_hat_lane_live_and_fixed(self):
        self.assertTrue(RUSTY.live_hat)
        hs = drummer.strokes('R@hat R@hat_half R@hat_open R@hat_open R@hat_half', kit=RUSTY)
        pts = drummer.hat_lane(hs, RUSTY, BPM)
        self.assertEqual([p[1] for p in pts], [1.0, 0.55, 1.0, 0.55, 1.0])      # back to open after the last
        self.assertTrue(all(p[2] == 'step' for p in pts))
        self.assertLess(pts[1][0], 0.25)                         # a step lands before its stroke
        clip = drummer._to_clip(hs, RUSTY, BPM, 2.0)
        self.assertEqual([n.pitch for n in clip], [42, 46, 46, 46, 46])
        gm = drummer.Kit.of('gm')
        self.assertEqual(drummer.hat_lane(hs, gm, BPM), [])
        self.assertEqual([n.pitch for n in drummer._to_clip(hs, gm, BPM, 2.0)], [42, 46, 46, 46, 46])

    def test_choke(self):
        c = drummer.choke(BPM, kit=RUSTY, after=1.0)
        pitches = [n.pitch for n in c]
        self.assertIn(49, pitches)
        self.assertIn(36, pitches)
        self.assertIn(88, pitches)
        self.assertGreater([n.start for n in c if n.pitch == 88][0], 0.9)

    def test_hand_keys(self):
        mf = drummer.Kit.of('mf_natural')
        self.assertEqual(mf.key('snare', limb='R'), 40)
        self.assertEqual(mf.key('snare', limb='L'), 38)
        c = drummer.pattern('R L R L', BPM, kit=mf)
        self.assertEqual([n.pitch for n in c], [40, 38, 40, 38])
        custom = drummer.Kit.of({'snare': 38, 'kick': 36, 'hand_keys': {38: {'R': 40}}})
        self.assertEqual(custom.key('snare', limb='R'), 40)
        with self.assertRaises(ComposeError):
            drummer.Kit.of({'snare': 38, 'hand_keys': {38: {'X': 40}}})

    def test_hat_dance_writes_a_lane(self):
        p = drummer.perform([('hat_dance', 2, 0.6)], bpm=BPM, kit=RUSTY, seed=1)
        self.assertIn('instrument.dynamics', p.lanes)
        s = Song('t', tempo=BPM)
        s.section('a', bars=2)
        tr = s.track('kit', 'sampled/big_rusty_kit')
        p.play(tr)
        self.assertTrue(any(t == 'instrument.dynamics' for t, _ in tr._auto))


class TestMotif(unittest.TestCase):
    def test_make_and_vary(self):
        m = drummer.DrumMotif.make(5)
        self.assertEqual(m.beats, 4.0)
        self.assertEqual(m.pattern(), drummer.DrumMotif.make(5).pattern())
        for how in drummer.MOTIF_VARIATIONS:
            v = m.vary(how, kit=RUSTY, seed=1)
            self.assertAlmostEqual(v.beats, 4.0 if how != 'augment' else 4.0)
            drummer.strokes(v.tokens, grid=v.grid, kit=RUSTY)          # parses
        self.assertEqual(m.vary('diminish').grid, 0.125)
        orch = m.vary('orchestrate', kit=RUSTY)
        self.assertTrue(any('@tom' in t for t in orch.tokens))
        with self.assertRaises(ComposeError):
            m.vary('twist')
        with self.assertRaises(ComposeError):
            drummer.DrumMotif.make(1, cell='x-x')


class TestMotifClips(unittest.TestCase):
    def test_from_clip_takes_the_rhythm_and_accents(self):
        from agentsound.patterns import Clip
        riff = Clip([(0.0, 0.5, 40, 110), (0.75, 0.25, 40, 80), (1.5, 0.75, 43, 104), (2.5, 0.5, 45, 100),
                     (3.0, 0.25, 43, 78), (3.25, 0.5, 40, 80)], length=4)
        m = drummer.DrumMotif.from_clip(riff, kit=RUSTY)
        self.assertEqual(m.grid, 0.25)
        acc = [i for i, t in enumerate(m.tokens) if t.startswith('>')]
        self.assertEqual(acc, [0, 6, 10])
        self.assertEqual([i for i, t in enumerate(m.tokens) if t != '-'], [0, 3, 6, 10, 12, 13])

    def test_round_trip_and_drums(self):
        m = drummer.DrumMotif.make(3, cell='x..x..x...x.x...')
        c = m.to_clip(RUSTY)
        self.assertEqual(c.length, 4.0)
        back = drummer.DrumMotif.from_clip(c, kit=RUSTY)
        self.assertEqual([i for i, t in enumerate(back.tokens) if t.startswith('>')],
                         [i for i, t in enumerate(m.tokens) if t.startswith('>')])
        toms = m.vary('orchestrate', kit=RUSTY).to_clip(RUSTY)
        self.assertTrue(set(n.pitch for n in toms) & set(RUSTY.toms))
        self.assertTrue(any('@' in t for t in drummer.DrumMotif.from_clip(toms, kit=RUSTY).tokens))


try:
    from agentsound import soloist  # noqa: E402
except ImportError:          # the instrument-agnostic solo wrapper (the guitar agent's) is not merged yet
    soloist = None


@unittest.skipIf(soloist is None, 'agentsound.soloist not available')
class TestVocabulary(unittest.TestCase):
    def test_soloist_plays_the_drummer(self):
        voc = drummer.vocabulary(RUSTY, hands='master')
        self.assertEqual({m.name for m in voc.moves}, set(drummer.SOLO_ROLES))
        s = Song('t', tempo=BPM)
        sec = s.section('solo', bars=16)
        kit = s.track('kit', 'sampled/big_rusty_kit')
        riff = drummer.DrumMotif.make(2, cell='x..x..x...x.x...').to_clip(RUSTY)
        perf = soloist.solo(s, kit, voc, at=sec, motif=riff, seed=4)
        self.assertGreater(len(perf.clip), 100)
        self.assertEqual(perf.warnings, [])
        stages = [st[0] for st in perf.stages]
        self.assertEqual(stages[0], 'statement')
        self.assertIn('climax', stages)
        kinds = {m[3] for m in perf.moves}
        self.assertGreaterEqual(len(kinds), 4)
        with self.assertRaises(ComposeError):
            drummer.vocabulary(RUSTY, moves=['juggle'])


PLAN = [('time', 4, 0.5), ('motif', 2, 0.45), ('develop', 4, 0.55),
        ('rudiment', 2, 0.6, {'rudiment': 'paradiddle', 'orchestrate': 'split'}), ('flam_toms', 1, 0.7),
        ('tom_melody', 2, 0.6), ('call_response', 2, 0.65), ('hat_dance', 2, 0.5), ('three_over_four', 2, 0.7),
        ('fives', 2, 0.72), ('quintuplets', 1, 0.75), ('half_double', 4, 0.75), ('silence', 1),
        ('gated_toms', 2, 0.9), ('bonham', 1, 0.85), ('linear', 2, 0.8), ('double_bass', 2, 0.95),
        ('speed_burst', 1, 0.95), ('buzz', 1, 0.85), ('swell', 1, 0.7), ('finish', 2, 1.0), ('hit_choke', 1, 1.0)]


class TestPerform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = drummer.perform(PLAN, bpm=BPM, kit=RUSTY, seed=5)

    def test_every_move_plays_cleanly(self):
        self.assertEqual(set(drummer.SOLO_MOVES), {p[0] for p in PLAN})
        self.assertEqual(self.p.warnings, [])
        self.assertEqual(drummer.check(self.p), [])
        self.assertEqual([m[3] for m in self.p.moves], [p[0] for p in PLAN])
        self.assertEqual(self.p.clip.length, sum(p[1] for p in PLAN) * 4.0)

    def test_moves_fill_their_bars(self):
        for name in ('half_double', 'time', 'gated_toms', 'call_response', 'develop', 'three_over_four'):
            for bars in (1, 2, 3, 5):
                c = drummer.solo_move(name, bars * 4, BPM, kit=RUSTY, seed=3)
                played = {int(n.start // 4) for n in c}
                self.assertEqual(played, set(range(bars)), (name, bars))

    def test_every_move_in_odd_slots(self):
        for name in drummer.SOLO_MOVES:
            for beats in (0.5, 1.0, 2.5, 3.0, 6.0):
                c = drummer.solo_move(name, beats, BPM, kit=RUSTY, seed=2)
                self.assertTrue(all(n.start < beats + 0.05 for n in c), (name, beats))

    def test_deterministic(self):
        q = drummer.perform(PLAN, bpm=BPM, kit=RUSTY, seed=5)
        self.assertEqual(list(q.clip), list(self.p.clip))
        r = drummer.perform(PLAN, bpm=BPM, kit=RUSTY, seed=6)
        self.assertNotEqual(list(r.clip), list(self.p.clip))

    def test_dynamics_follow_the_arc_and_are_never_flat(self):
        def mean_vel(name):
            a, b = next((m[0], m[1]) for m in self.p.moves if m[3] == name)
            v = [n.vel for n in self.p.clip if a <= n.start < b]
            return statistics.mean(v), statistics.pstdev(v)
        for name in ('motif', 'develop', 'tom_melody', 'speed_burst'):
            self.assertGreater(mean_vel(name)[1], 8.0, name)                # accents, taps, ghosts
        self.assertGreater(mean_vel('finish')[0], mean_vel('motif')[0] + 8)
        a, b = next((m[0], m[1]) for m in self.p.moves if m[3] == 'silence')
        self.assertFalse([n for n in self.p.clip if a + 0.05 <= n.start < b - 0.05])

    def test_tom_melody_uses_touch_arc(self):
        p = drummer.perform([('tom_melody', 2, 0.7, {'melody': (1, 2, 3, 4, 3, 2, 1, None)})], bpm=BPM, kit=RUSTY)
        toms = [n for n in p.clip if n.start >= 4.0 and n.pitch in RUSTY.toms]
        self.assertGreater(len(toms), 6)
        self.assertGreater(max(n.vel for n in toms) - min(n.vel for n in toms), 10)

    def test_steps_and_errors(self):
        with self.assertRaises(ComposeError):
            drummer.perform([('juggle', 1)], bpm=BPM)
        with self.assertRaises(ComposeError):
            drummer.perform([], bpm=BPM)
        p = drummer.perform([{'move': 'rudiment', 'bars': 1, 'rudiment': 'six_stroke_roll', 'orchestrate': 'down',
                              'feet': 'four'}], bpm=BPM, kit=RUSTY)
        self.assertTrue(any(n.pitch == 36 for n in p.clip))
        c = drummer.solo_move('gated_toms', 8, BPM, kit=RUSTY, at=4)
        self.assertGreaterEqual(min(n.start for n in c), 3.9)
        m = drummer.DrumMotif.make(1, cell='x..x..x...x.x...')
        f = drummer.perform([('finish', 2, 1.0, {'motif': True})], bpm=BPM, kit=RUSTY, motif=m)
        crash_at = sorted(round(n.start * 4) / 4 for n in f.clip if n.pitch in (49, 57, 52))
        self.assertEqual(crash_at, [0.0, 0.75, 1.5, 2.5, 3.0])

    def test_arrange_fills_with_hands(self):
        form = [('verse', 8), ('chorus', 8)]
        p0 = drummer.arrange(form, bpm=BPM, kit=RUSTY, seed=1)
        p1 = drummer.arrange(form, bpm=BPM, kit=RUSTY, seed=1, hands='student')
        f0 = [h.vel for h in p0.hits if h.tag == 'fill']
        f1 = [h.vel for h in p1.hits if h.tag == 'fill']
        self.assertEqual(len(f0), len(f1))
        self.assertNotEqual(f0, f1)
        self.assertEqual([h.t for h in p0.hits], [h.t for h in p1.hits])      # the feel keeps the timing
        self.assertEqual(drummer.check(p1), [])
        with self.assertRaises(ComposeError):
            drummer.arrange(form, bpm=BPM, hands='octopus')

    def test_arrange_choke_ending_and_loose_hat(self):
        p = drummer.arrange([('verse', 4), ('end', 2)], bpm=BPM, kit=RUSTY, ending='choke',
                            plan={'verse': {'time': 'hat_loose'}}, seed=1)
        self.assertIn(88, [n.pitch for n in p.clip])
        self.assertEqual({p_[1] for p_ in p.lanes['instrument.dynamics']} - {1.0}, {0.45})


if __name__ == '__main__':
    unittest.main()
