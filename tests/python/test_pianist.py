import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import jazz, pianist  # noqa: E402
from agentsound.humanize import touch  # noqa: E402
from agentsound.patterns import Clip  # noqa: E402
from agentsound.theory import ComposeError, Key, Progression, note  # noqa: E402

BPM = 96
KEY = Key('Ab major')
PROG = ('Fm9 Dbmaj7#11 Bbm9 Eb7sus4:0.5 Eb7b9:0.5 | Abmaj9 Dm7b5:0.5 G7b9:0.5 Cm9:0.5 F7b9:0.5 '
        'Bbm7:0.5 Eb7sus4:0.5')


def ph(spec, vel=80):
    """Tiny line notation: PITCH[/8ths], 'r' rests."""
    t, out = 0.0, []
    for tok in spec.split():
        p, _, d = tok.partition('/')
        dur = 0.5 * (float(d) if d else 1.0)
        if p != 'r':
            out.append((t, dur, p, vel))
        t += dur
    return Clip(out, length=max(4.0, -(-t // 4) * 4))


HEAD = ph("r/2 C5 Eb5 G5/3 F5 Eb5/2 C5/2 r C5 G5 F5 r/2 Bb4 Db5 F5/3 Eb5 Db5/2 Ab4/2 r G4 Bb4 E5 "
          "Eb5/3 C5 Bb4/4 r Ab4 C5 F5 Ab5/2 G5 F5 Eb5/3 D5 C5/2 A4 Gb4 F4/4 Ab4 Bb4 C5 Eb5")


def secs_per_note(clip, pitches):
    ns = sorted((n for n in clip if n.pitch in pitches), key=lambda n: n.start)
    gaps = [b.start - a.start for a, b in zip(ns, ns[1:])]
    return [g * 60.0 / BPM for g in gaps]


class TestMoves(unittest.TestCase):
    def test_trill_is_fast_alternation_ending_with_a_turn(self):
        c = pianist.trill('C5', 2.0, BPM, key=KEY, seed=1)
        ns = sorted(c, key=lambda n: n.start)
        self.assertEqual(ns[0].pitch, 72)                        # starts on the main note
        self.assertEqual({n.pitch for n in ns[:-3]}, {72, 73})   # C and its scale step Db in Ab major
        rates = [1.0 / s for s in secs_per_note(Clip(ns[3:-3]), {72, 73}) if s > 0]
        self.assertTrue(all(10.0 <= r <= 20.0 for r in rates), rates)
        self.assertEqual([n.pitch for n in ns[-2:]], [70, 72])   # the turn: lower neighbour, then the note
        self.assertGreater(ns[-1].dur, 0.4)                       # held
        self.assertAlmostEqual(max(n.start + n.dur for n in ns), 2.0, places=3)
        self.assertGreater(ns[0].vel, ns[1].vel)                 # upper notes lighter
        self.assertEqual(pianist.trill('C5', 2.0, BPM, seed=4), pianist.trill('C5', 2.0, BPM, seed=4))

    def test_trill_accelerates(self):
        c = sorted(pianist.trill('E5', 3.0, BPM, chord='C6', rate=15, seed=2, wobble_ms=0), key=lambda n: n.start)
        g = [b.start - a.start for a, b in zip(c, c[1:])]
        self.assertGreater(g[0], g[5])

    def test_tremolo_alternates_groups(self):
        c = pianist.tremolo(['Ab4', 'C5'], 'Eb5', 2.0, BPM, rate=11, swell='cresc', seed=3)
        ons = {}
        for n in c:
            ons.setdefault(round(n.start, 4), set()).add(n.pitch)
        seq = [ons[t] for t in sorted(ons)]
        self.assertEqual(seq[0], {68, 72})
        self.assertEqual(seq[1], {75})
        self.assertEqual(seq[-1], {68, 72, 75})                    # lands together
        rate = (len(seq) - 1) / (sorted(ons)[-1] * 60.0 / BPM)
        self.assertTrue(8 <= rate <= 14, rate)
        v = [n.vel for n in sorted(c, key=lambda n: n.start) if n.pitch == 75]
        self.assertLess(v[1], v[-2])                               # crescendo
        self.assertGreaterEqual(v[0] - v[1], 20)                   # light: the principal, then the figure under it
        with self.assertRaises(ComposeError):
            pianist.tremolo('C5', 'C4', 1.0, BPM)

    def test_mordent_turn_and_inverted(self):
        m = sorted(pianist.mordent('C5', 1.0, BPM, key=KEY), key=lambda n: n.start)
        self.assertEqual([n.pitch for n in m], [72, 70, 72])
        im = sorted(pianist.inverted_mordent('C5', 1.0, BPM, key=KEY), key=lambda n: n.start)
        self.assertEqual([n.pitch for n in im], [72, 73, 72])
        self.assertLess(m[1].start * 60 / BPM, 0.1)                # fast: ~55 ms per ornament note
        t = sorted(pianist.turn('C5', 1.0, BPM, key=KEY), key=lambda n: n.start)
        self.assertEqual([n.pitch for n in t], [73, 72, 71, 72])   # upper, note, chromatic lower, note
        self.assertAlmostEqual(t[-1].start + t[-1].dur, 1.0)
        with self.assertRaises(ComposeError):
            pianist.mordent('C5', 0.05, BPM)

    def test_crushes_and_slip(self):
        c = sorted(pianist.crush('E5', 1.0, BPM), key=lambda n: (n.start, n.pitch))
        self.assertEqual([n.pitch for n in c], [75, 76])
        self.assertLess(c[0].start, c[1].start)
        bc = pianist.blues_crush('E5', 1.0, BPM, under=['C5', 'G4'])
        at0 = sorted(n.pitch for n in bc if n.start == 0.0)
        self.assertEqual(at0, [67, 72, 75, 76])                    # minor 3rd struck WITH the major 3rd
        g = next(n for n in bc if n.pitch == 75)
        self.assertLess(g.dur * 60 / BPM, 0.1)                     # and released at once
        s = sorted(pianist.slip_note(['C5', 'E5', 'G5'], 1.0, BPM), key=lambda n: (n.start, n.pitch))
        self.assertEqual([n.pitch for n in s if n.start == 0.0], [72, 76, 77])   # G slips up from F
        self.assertEqual(s[-1].pitch, 79)
        self.assertGreater(s[-1].start, 0.0)

    def test_repeated_notes_alternate_hands(self):
        c = sorted(pianist.repeated('G5', 1.0, BPM, rate=9, wobble_ms=0), key=lambda n: n.start)
        self.assertTrue(all(n.pitch == 79 for n in c))
        self.assertGreaterEqual(len(c), 5)
        self.assertGreater(c[0].vel, c[1].vel)                     # R strong, L lighter
        self.assertGreater(c[2].vel, c[1].vel)

    def test_roll_spreads_and_sings_the_top(self):
        c = sorted(pianist.roll(['C3', 'G3', 'E4', 'B4'], 2.0, BPM, ms=30), key=lambda n: n.start)
        self.assertEqual([n.pitch for n in c], [48, 55, 64, 71])
        self.assertAlmostEqual((c[-1].start - c[0].start) * 60 / BPM * 1000, 30, delta=1)
        self.assertGreater(c[-1].vel, c[0].vel)
        self.assertTrue(all(abs(n.start + n.dur - 2.0) < 1e-9 for n in c))

    def test_sweep_and_gliss(self):
        c = sorted(pianist.sweep('Dbmaj9', 2.0, BPM, low='Db3', high='F5'), key=lambda n: n.start)
        ps = [n.pitch for n in c]
        self.assertEqual(ps, sorted(ps))
        self.assertTrue({p % 12 for p in ps} <= {1, 5, 8, 0, 3})
        self.assertTrue(all(b - a >= 2 for a, b in zip(ps, ps[1:])))
        self.assertLessEqual(len(ps) / (2.0 * 60 / BPM), 16.5)
        gl = sorted(pianist.gliss('Ab5', 1.0, BPM, key=KEY), key=lambda n: n.start)
        self.assertTrue(all(n.pitch < 80 for n in gl))             # ends just under the target
        self.assertAlmostEqual(gl[-1].start + gl[-1].dur, 1.0, delta=0.02)
        g = [b.start - a.start for a, b in zip(gl, gl[1:])]
        self.assertGreater(g[0], g[-1])                            # accelerates into the downbeat
        self.assertTrue(all(n.pitch % 12 in KEY.pcs for n in gl))
        landed = pianist.gliss('Ab5', 1.0, BPM, key=KEY, land=True)
        self.assertEqual(max(landed, key=lambda n: n.start).pitch, 80)

    def test_runs(self):
        cr = sorted(pianist.chromatic_run('G5', 'Eb5', 0.5, BPM), key=lambda n: n.start)
        self.assertEqual([n.pitch for n in cr], [79, 78, 77, 76, 75])
        r = sorted(pianist.run('C5', 'C6', 1.0, BPM, key=KEY), key=lambda n: n.start)
        self.assertEqual(r[0].pitch, 72)
        self.assertEqual(r[-1].pitch, 84)
        self.assertTrue(all(n.pitch % 12 in KEY.pcs for n in r))
        o = pianist.octave_run('C5', 'G5', 1.0, BPM, chord='Fm9')
        tops = [n for n in o if n.pitch >= 72]
        self.assertTrue(all(any(m.pitch == n.pitch - 12 and m.start == n.start for m in o) for n in tops))
        pr = sorted(pianist.pentatonic_run('Eb6', 1.0, BPM, chord='Fm9', notes=6), key=lambda n: n.start)
        self.assertTrue(all(n.pitch % 12 in {5, 8, 10, 0, 3} for n in pr))
        self.assertEqual(len(pr), 6)

    def test_fourths_cascade(self):
        c = pianist.fourths('Eb6', 1.0, BPM, chord='Fm9', voices=2)
        ons = {}
        for n in c:
            ons.setdefault(n.start, []).append(n.pitch)
        tops = []
        for t in sorted(ons):
            lo, hi = sorted(ons[t])
            self.assertIn(hi - lo, (5, 6))
            tops.append(hi)
        self.assertEqual(tops, sorted(tops, reverse=True))

    def test_shake_and_alternating_hands(self):
        c = sorted(pianist.shake(['C4', 'Eb4', 'G4', 'C5'], 2.0, BPM, interval=3), key=lambda n: (n.start, n.pitch))
        top = [n.pitch for n in c if n.pitch >= 72]
        self.assertEqual(top[:4], [72, 75, 72, 75])
        self.assertEqual(top[-1], 72)
        self.assertTrue(all(n.dur == 2.0 for n in c if n.pitch < 72))
        h = pianist.alternating_hands('Fm9', 1.5, BPM, top='C6', lh_register=('C3', 'C4'), pattern='RL',
                                      wobble_ms=0)
        ons = {}
        for n in h:
            ons.setdefault(round(n.start, 4), []).append(n.pitch)
        hands = ['R' if min(v) >= 65 else 'L' for _, v in sorted(ons.items())]
        self.assertEqual(hands[:4], ['R', 'L', 'R', 'L'])
        for v in ons.values():
            v = sorted(v)
            self.assertTrue(all(b - a >= 3 for a, b in zip(v, v[1:])), v)

    def test_moves_registry_and_errors(self):
        self.assertEqual(set(pianist.MOVES), {
            'trill', 'tremolo', 'mordent', 'inverted_mordent', 'turn', 'crush', 'blues_crush', 'slip_note',
            'repeated', 'roll', 'sweep', 'gliss', 'run', 'chromatic_run', 'pentatonic_run', 'octave_run', 'fourths',
            'shake', 'alternating_hands'})
        self.assertIs(jazz.MOVES, pianist.MOVES)
        with self.assertRaises(ComposeError):
            pianist.trill('C5', 1.0, 0)
        with self.assertRaises(ComposeError):
            pianist.roll(['C4'], 1.0, BPM, direction='sideways')
        # at= places a move
        a = pianist.mordent('C5', 1.0, BPM, at=3.0)
        self.assertAlmostEqual(min(n.start for n in a), 3.0)


class TestVoicing(unittest.TestCase):
    def test_devices_keep_the_melody_on_top(self):
        for dev in pianist.DEVICES:
            for ch, mel in (('Fm9', 'C5'), ('Eb7b9', 'G5'), ('Dbmaj7#11', 'F5'), ('G7alt', 'Eb5'), ('Cm9', 'D5')):
                v = pianist.voicing(ch, mel, dev, floor='C4', voices=3)
                self.assertEqual(v[-1], note(mel), (dev, ch))
                self.assertTrue(all(q < note(mel) for q in v[:-1]))
                self.assertTrue(all(q >= 60 for q in v[:-1]), (dev, ch, v))
                self.assertTrue(all(b - a >= 2 for a, b in zip(v, v[1:])), (dev, ch, v))
                self.assertFalse(any(note(mel) - q == 13 for q in v))

    def test_device_shapes(self):
        self.assertEqual(pianist.voicing('Fm9', 'C5', 'guide', floor='C4'), [63, 68, 72])   # Eb Ab under C
        self.assertEqual(pianist.voicing('Fm9', 'C5', 'octave', floor='G3')[0], 60)
        th = pianist.voicing('Fm9', 'C5', 'thirds', floor='C4')
        self.assertIn(72 - th[0], (3, 4))
        q = pianist.voicing('Fm9', 'C5', 'quartal', floor='G3', voices=2)
        self.assertEqual([72 - x for x in q], [10, 5, 0])
        with self.assertRaises(ComposeError):
            pianist.voicing('Fm9', 'C5', 'mush')


class TestArrange(unittest.TestCase):
    def arr(self, **kw):
        opts = dict(bpm=BPM, key=KEY, style='straight', density=0.7, seed=5, lh='guide', lead_in=True)
        opts.update(kw)
        return pianist.arrange(touch(HEAD, 50, 96), Progression(PROG, key=KEY), **opts)

    def test_melody_always_on_top(self):
        for style in pianist.STYLES:
            for seed in range(4):
                a = self.arr(style=style, seed=seed)
                orn = a.ornaments
                for m in a.melody:
                    if m.dur <= 0.15 or any(s - 1e-6 <= m.start < e for s, e, _ in orn):
                        continue
                    t = m.start + 0.01
                    sounding = [n for n in a.rh if n.start <= t < n.start + n.dur]
                    self.assertTrue(any(n.pitch == m.pitch for n in sounding), (style, seed, m))
                    self.assertLessEqual(max(n.pitch for n in sounding), m.pitch, (style, seed, m, sounding))

    def test_voicings_in_range_and_no_clusters(self):
        for style in pianist.STYLES:
            a = self.arr(style=style, roll=(0, 0), seed=11)
            mel = {(round(m.start, 4), m.pitch) for m in a.melody}
            special = [(s, e) for s, e, k in a.ornaments if k in ('crush', 'blues_crush', 'slip', 'trill', 'turn',
                                                                    'mordent', 'inverted_mordent')]
            hands = [(s, e) for s, e, k in a.fills if k == 'hands']      # the left hand's strokes of the break
            groups = {}
            for n in a.rh:
                if (round(n.start, 4), n.pitch) in mel or any(s - 1e-6 <= n.start < e for s, e in hands):
                    continue
                self.assertGreaterEqual(n.pitch, 58, (style, n))          # C4 floor (a neighbour note may dip)
                self.assertLessEqual(n.pitch, 108)
                if not any(s - 1e-6 <= n.start < e for s, e in special):
                    groups.setdefault(round(n.start, 4), []).append(n.pitch)
            for m in a.melody:
                if (round(m.start, 4)) in groups:
                    groups[round(m.start, 4)].append(m.pitch)
            for t, ps in groups.items():
                ps = sorted(set(ps))
                self.assertTrue(all(b - a_ >= 2 for a_, b in zip(ps, ps[1:])), (style, t, ps))
            self.assertTrue(all(n.pitch <= 64 for n in a.lh), style)          # the left hand stays under the right

    def test_fills_stay_inside_gaps(self):
        for style in pianist.STYLES:
            for seed in range(5):
                a = self.arr(style=style, seed=seed, density=1.0)
                for s, e, kind in a.fills:
                    for m in a.melody:
                        self.assertFalse(m.start < e - 0.04 and m.start + m.dur > s + 0.04,
                                         (style, seed, kind, s, e, m))

    def test_it_harmonizes_decorates_and_fills(self):
        a = self.arr(density=0.8)
        self.assertGreater(a.harmonized, 0.6)
        self.assertGreater(len(a.rh), 2 * len(a.melody))
        kinds = {k for _, _, k, _ in a.moves}
        self.assertTrue({'device', 'fill', 'ornament'} <= kinds, a.summary())
        sp = self.arr(style='sparse', density=0.2)
        self.assertLess(sp.harmonized, a.harmonized)
        self.assertLess(len(sp.rh), len(a.rh))

    def test_inner_voices_under_the_melody_velocity(self):
        a = self.arr(roll=(0, 0))
        mel = {round(m.start, 4): m for m in a.melody}
        diffs = []
        for n in a.rh:
            m = mel.get(round(n.start, 4))
            if m is not None and n.pitch < m.pitch:
                diffs.append(m.vel - n.vel)
        self.assertTrue(diffs)
        avg = sum(diffs) / len(diffs)
        self.assertTrue(8 <= avg <= 20, avg)

    def test_roll_leads_into_the_melody(self):
        a = self.arr(roll=(20, 20))
        mel = {round(m.start, 4) for m in a.melody}
        early = [n for n in a.rh if 0 < min(abs(n.start - t) for t in mel) * 60 / BPM * 1000 <= 21
                 and any(t > n.start for t in mel)]
        self.assertTrue(early)

    def test_determinism_and_seeds(self):
        self.assertEqual(self.arr(seed=3).rh, self.arr(seed=3).rh)
        self.assertEqual(self.arr(seed=3).lh, self.arr(seed=3).lh)
        self.assertNotEqual(self.arr(seed=3).rh, self.arr(seed=4).rh)

    def test_left_hand_styles(self):
        prog = Progression(PROG, key=KEY)
        for st in pianist.LH_STYLES:
            c = pianist.left_hand(prog, BPM, style=st, seed=2, pedal_note='Eb2' if st == 'pedal' else None)
            self.assertTrue(len(c) > 0, st)
            self.assertTrue(all(28 <= n.pitch <= 72 for n in c), st)
        with self.assertRaises(ComposeError):
            pianist.left_hand(prog, BPM, style='boogie')

    @staticmethod
    def strikes(clip, bar):
        """{bar position (0.25 grid) of each struck chord: its notes} (rolled notes grouped by their first onset)."""
        out: dict = {}
        first = None
        for n in sorted(clip, key=lambda n: n.start):
            if first is None or n.start - first > 0.2:
                first = n.start
            out.setdefault(round(first, 3), []).append(n)
        return {k: v for k, v in out.items()}, (lambda t: round(4 * (t % bar)) / 4 % bar)

    def test_left_hand_answers_in_the_meter(self):
        # 4/4: on 3 or the & of 2 - the held voicing stays under it (unchanged since before the meters)
        prog4 = Progression('Dm9 G13 Cmaj9 A7b9', key=Key('C major'))
        groups, pos = self.strikes(pianist.left_hand(prog4, BPM, answers=1.0, seed=1), 4.0)
        self.assertEqual(sorted({pos(t) for t in groups} - {0.0, 3.5}), [2.0])
        c4 = pianist.left_hand(prog4, BPM, answers=1.0, seed=1)
        self.assertTrue(all(n.dur > 3.0 for n in c4 if pos(n.start) in (0.0, 3.5) and n.start < 15))
        # 3/4 (the progression's 3 beats per bar): oom-pah-pah - a light answer on 2, the & of 2 or 3, the held
        # shell lifted just before it
        prog3 = Progression('Dm9 Bbmaj7#11 Gm9 A7b13 Dm9 G13 Em7b5 A7b9', key=Key('D minor'), beats_per_bar=3)
        per_place = {}
        for seed in range(12):
            c = pianist.left_hand(prog3, BPM, answers=1.0, seed=seed, touch=0)
            groups, pos = self.strikes(c, 3.0)
            answers = {t: ns for t, ns in groups.items() if pos(t) in (1.0, 1.5, 2.0)}
            self.assertEqual(len(answers), 8, seed)                       # every bar answered (answers=1, no rh)
            for t, ns in answers.items():
                per_place[pos(t)] = per_place.get(pos(t), 0) + 1
                bar0 = 3.0 * round((t - pos(t)) / 3.0)
                held = [n for n in c if bar0 - 0.6 <= n.start < bar0 + 0.2]
                self.assertTrue(held)
                self.assertTrue(all(n.start + n.dur <= t - 0.03 for n in held), (seed, t))     # the hand lifts
                self.assertLess(max(n.vel for n in ns), max(n.vel for n in held))            # ... and answers light
        self.assertEqual(set(per_place), {1.0, 1.5, 2.0})
        self.assertGreater(per_place[1.0], per_place[1.5])
        self.assertGreater(per_place[1.5], per_place[2.0])
        # no answers: only the strikes
        groups, pos = self.strikes(pianist.left_hand(prog3, BPM, answers=0.0, seed=1), 3.0)
        self.assertEqual({pos(t) for t in groups} - {0.0, 2.5}, set())
        # the right hand playing on 2 and the & of 2 of every bar: the drawn place is kept free, never hunted for
        rh = Clip([(3.0 * k + x, 0.4, 'A5', 80) for k in range(8) for x in (1.0, 1.5)], length=24)
        groups, pos = self.strikes(pianist.left_hand(prog3, BPM, answers=1.0, rh=rh, seed=3), 3.0)
        self.assertLessEqual({pos(t) for t in groups} - {0.0, 2.5}, {2.0})
        # 6/8 (same 3 beats): on the second dotted quarter; 5/4 (3+2): on 4
        groups, pos = self.strikes(pianist.left_hand(prog3, BPM, answers=1.0, meter='6/8', seed=2), 3.0)
        self.assertEqual({pos(t) for t in groups} - {0.0, 2.5}, {1.5})
        prog5 = Progression('Ebm7 Bbm7 Ebm7 Bbm7', key=Key('Eb minor'), beats_per_bar=5)
        groups, pos = self.strikes(pianist.left_hand(prog5, BPM, answers=1.0, seed=2), 5.0)
        self.assertEqual({pos(t) for t in groups} - {0.0, 4.5}, {3.0})
        with self.assertRaisesRegex(ComposeError, 'beats per bar'):
            pianist.left_hand(prog3, BPM, meter='4/4')
        with self.assertRaises(ComposeError):
            pianist.left_hand(prog3, BPM, answers=2)
        with self.assertRaisesRegex(ComposeError, 'beats per bar'):
            pianist.arrange(Clip([(0, 3, 'A4', 80)], length=24), prog3, bpm=BPM, meter='5/4')

    def test_stride_in_the_meter(self):
        # 3/4: bass on 1, the chord on 2 and 3 (oom-pah-pah), the fifth in the second bar of a long chord
        def split(c):
            """(single bass notes [(beat, pitch)], chord onsets): the chords are 2+ notes on one onset."""
            by: dict = {}
            for n in c:
                by.setdefault(round(n.start, 2), []).append(n.pitch)
            return (sorted((t, ps[0]) for t, ps in by.items() if len(ps) == 1),
                    sorted(t for t, ps in by.items() if len(ps) > 1))
        prog = Progression('Dm7:2 G7', key=Key('C major'), beats_per_bar=3)
        low, chords = split(pianist.left_hand(prog, BPM, style='stride', density=0, seed=1))
        self.assertEqual([t for t, _ in low], [0.0, 3.0, 6.0])
        self.assertEqual(low[1][1] - low[0][1], 7)                       # the fifth on the second bar
        self.assertEqual(chords, [1.0, 2.0, 4.0, 5.0, 7.0, 8.0])
        # 6/8: oom-pah on the dotted quarters
        low, chords = split(pianist.left_hand(prog, BPM, style='stride', density=0, seed=1, meter='6/8'))
        self.assertEqual([t for t, _ in low], [0.0, 3.0, 6.0])
        self.assertEqual(chords, [1.5, 4.5, 7.5])
        # 4/4 as before: bass on 1 and 3 (root, fifth), chords on 2 and 4
        low, chords = split(pianist.left_hand(Progression('Dm7 G7', key=Key('C major')), BPM, style='stride',
                                              density=0, seed=1))
        self.assertEqual([t for t, _ in low], [0.0, 2.0, 4.0, 6.0])
        self.assertEqual(chords, [1.0, 3.0, 5.0, 7.0])

    def test_left_hand_breathes_with_the_right(self):
        prog = Progression(PROG, key=KEY)
        # the right hand: soft for the first half, loud for the second
        half = prog.length / 2
        rh = Clip([(t * 0.5, 0.45, 'C5', 50 if t * 0.5 < half else 100) for t in range(int(prog.length * 2))],
                  length=prog.length)
        flat = pianist.left_hand(prog, BPM, rh=rh, vel=60, seed=4, touch=0)
        felt = pianist.left_hand(prog, BPM, rh=rh, vel=60, seed=4)
        self.assertEqual([(n.start, n.pitch) for n in flat], [(n.start, n.pitch) for n in felt])

        def mean(c, a, b):
            vs = [n.vel for n in c if a <= n.start < b]
            return sum(vs) / len(vs)

        def energy(c):
            return sum(n.vel ** 4 for n in c) / len(c)
        self.assertLess(mean(felt, 0, half - 1), mean(felt, half + 1, prog.length) - 12)
        self.assertLess(abs(mean(flat, 0, half - 1) - mean(flat, half + 1, prog.length)), 6)
        self.assertLess(abs(10 * math.log10(energy(felt) / energy(flat))), 1.0)   # vel keeps the loudness
        with self.assertRaises(ComposeError):
            pianist.left_hand(prog, BPM, touch=3)

    def test_pedal_lifts_for_dry_runs(self):
        prog = Progression('Fm9 Bbm9', key=KEY)
        pts = pianist.pedal(prog, 8.0, dry=[(1.0, 2.0)])
        def state(t):
            v = 0.0
            for x, val, _ in pts:
                if x <= t:
                    v = val
            return v
        self.assertEqual(state(8.5), 1.0)
        self.assertEqual(state(9.5), 0.0)                  # up during the run
        self.assertEqual(state(10.5), 1.0)                 # down again
        self.assertEqual(state(12.05), 0.0)                # changes with the harmony
        self.assertEqual(state(12.5), 1.0)
        self.assertEqual(state(16.1), 0.0)

    def test_errors(self):
        with self.assertRaises(ComposeError):
            self.arr(style='boogie')
        with self.assertRaises(ComposeError):
            self.arr(density=2)
        with self.assertRaises(ComposeError):
            self.arr(devices={'mush': 1})
        with self.assertRaises(ComposeError):
            self.arr(lh='boogie')

    def test_jazz_wrapper(self):
        a = jazz.pianist(HEAD, PROG, bpm=BPM, key=KEY, style='bar', density=0.5, seed=1)
        self.assertIsInstance(a, pianist.Arrangement)
        self.assertEqual(len(a.lh), 0)
        self.assertEqual(a.rh, jazz.pianist(HEAD, PROG, bpm=BPM, key=KEY, style='bar', density=0.5, seed=1).rh)


LONG_PROG = Progression(' | '.join([PROG] * 4), key=KEY)          # 32 bars
LONG_HEAD = Clip([(n.start + 32 * i, n.dur, n.pitch, n.vel) for i in range(4) for n in HEAD], length=128)
# every ornament / fill a fast figure where it fits: the budget has to do the thinning
GREEDY = dict(ornaments={'trill': 3.0, 'tremolo': 3.0, 'shake': 2.0, 'repeated': 2.0, 'turn': 1.0, 'crush': 1.0,
                         'mordent': 1.0, 'roll': 1.0, 'restrike': 0.5},
              fills={'hands': 3.0, 'tremolo': 3.0, 'repeated': 2.0, 'run': 1.0, 'arpeggio': 1.0},
              embellish=1.0, fill=1.0, quick=0.6)


def phrase_pos(melody, t):
    """Phrase number of beat t: i inside phrase i, i + 0.5 in the gap after it (phrases split at rests >= an 8th)."""
    spans = []
    for m in sorted(melody, key=lambda n: n.start):
        if spans and m.start - spans[-1][1] < 0.5 - 1e-6:
            spans[-1][1] = max(spans[-1][1], m.start + m.dur)
        else:
            spans.append([m.start, m.start + m.dur])
    for i, (a, e) in enumerate(spans):
        if t < a - 1e-6:
            return i - 0.5
        if t < e - 1e-6:
            return i
    return len(spans) - 0.5


class TestOrnamentBudget(unittest.TestCase):
    """User feedback 2026-09-30 (perry-street-rain v3): "etwas zu viele von diesen schnellen Zwei-Tasten-Wechseln"."""

    def arr(self, **kw):
        opts = dict(bpm=BPM, key=KEY, style='straight', density=1.0, seed=5, lh='guide', lead_in=True, **GREEDY)
        opts.update(kw)
        return pianist.arrange(touch(LONG_HEAD, 50, 100), LONG_PROG, **opts)

    @staticmethod
    def fast(a):
        return [(s, n) for s, e, k, n in a.moves if k in ('ornament', 'fill') and n in pianist.FAST]

    def test_fast_alternations_per_16_bars(self):
        n_total = 0
        for style in pianist.STYLES:
            every = pianist.STYLES[style]['fast_every']
            for seed in range(10):
                a = self.arr(style=style, seed=seed)
                f = self.fast(a)
                n_total += len(f)
                if every == 0:
                    self.assertEqual(f, [], (style, seed))
                    continue
                ts = sorted(s for s, _ in f)
                self.assertTrue(all(b - x >= every * 4 - 1e-6 for x, b in zip(ts, ts[1:])), (style, seed, f))
                for w in range(0, 128, 4):                               # every 16-bar window
                    inside = [t for t in ts if w <= t < w + 64]
                    self.assertLessEqual(len(inside), -(-16 // every), (style, seed, w, f))
                self.assertEqual(sorted(a.budget['fast']), sorted((round(s, 4), n) for s, n in f))
        self.assertGreater(n_total, 0)                                   # the spice is still there

    def test_never_in_neighbouring_phrases_nor_same_kind_within_32_bars(self):
        for style in ('straight', 'bar', 'lush', 'ballad'):
            for seed in range(8):
                a = self.arr(style=style, seed=seed, fast_every=1)       # only the phrase / kind rules left
                f = sorted(self.fast(a))
                pos = [(phrase_pos(a.melody, s), s, n) for s, n in f]
                for i, (p1, s1, n1) in enumerate(pos):
                    for p2, s2, n2 in pos[i + 1:]:
                        self.assertGreater(abs(p2 - p1), 1.0, (style, seed, f))
                        if n1 == n2:
                            self.assertGreaterEqual(abs(s2 - s1), 32 * 4 - 1e-6, (style, seed, f))

    def test_spice_budget(self):
        for style in pianist.STYLES:
            for seed in range(6):
                a = self.arr(style=style, seed=seed)
                every = pianist.STYLES[style]['spice_every']
                ts = sorted(s for s, e, k, n in a.moves if k == 'ornament' and n in pianist.SPICE)
                self.assertTrue(all(b - x >= every * 4 - 1e-6 for x, b in zip(ts, ts[1:])), (style, seed, ts))
                self.assertEqual(len(ts), a.budget['spice'])

    def test_dropped_moves_are_logged_and_replaced(self):
        a = self.arr(seed=3)
        s = a.summary()
        self.assertTrue(any(k.startswith('dropped:') for k in s), s)
        self.assertEqual(a.budget['fast_every'], 16)
        dropped = {round(t, 4) for t, _, _ in a.budget['dropped']}
        self.assertEqual(dropped, {round(t, 4) for t, _, k, _ in a.moves if k == 'dropped'})
        # a dropped long-note ornament still plays its melody note
        for m in a.melody:
            if round(m.start, 4) in dropped:
                self.assertTrue(any(n.pitch == m.pitch and abs(n.start - m.start) < 0.15 for n in a.rh), m)  # (rolled)
        # without a budget (sparse: fast_every 0; spice_every 0) nothing is budgeted in
        none = self.arr(style='sparse', spice_every=0)
        self.assertFalse(any(k == 'ornament' and n in pianist.FAST + pianist.SPICE for _, _, k, n in none.moves))

    def test_memory_counts_song_wide(self):
        mem = pianist.Memory()
        first = pianist.arrange(touch(HEAD, 50, 100), PROG, bpm=BPM, key=KEY, density=1.0, seed=1, memory=mem,
                                **GREEDY)
        ts = [s for s, _ in self.fast(first)]
        self.assertEqual(mem.clock, 32.0)
        second = pianist.arrange(touch(HEAD, 50, 100), PROG, bpm=BPM, key=KEY, density=1.0, seed=2, memory=mem,
                                 **GREEDY)
        ts += [32.0 + s for s, _ in self.fast(second)]
        ts.sort()
        self.assertTrue(all(b - x >= 64 - 1e-6 for x, b in zip(ts, ts[1:])), ts)
        self.assertEqual([t for t, _, _ in mem.fast], ts)
        # alone, each 8-bar call could have spent its own
        alone = [s for s, _ in self.fast(pianist.arrange(touch(HEAD, 50, 100), PROG, bpm=BPM, key=KEY, density=1.0,
                                                          seed=2, **GREEDY))]
        self.assertGreaterEqual(len(alone), len(self.fast(second)))
        # a booked set piece and a saved climax keep the budget away
        m2 = pianist.Memory().played(0.0, 'trill').save(60.0)
        a = pianist.arrange(touch(HEAD, 50, 100), PROG, bpm=BPM, key=KEY, density=1.0, seed=1, memory=m2, at=4.0,
                            **GREEDY)
        self.assertEqual(self.fast(a), [])
        with self.assertRaises(ComposeError):
            pianist.Memory().played(0.0, 'sweep')

    def test_ornaments_are_light(self):
        c = sorted(pianist.trill('C5', 3.0, BPM, key=KEY, vel=96, seed=2), key=lambda n: n.start)
        inner = [n.vel for n in c[1:-1]]
        self.assertEqual(c[0].vel, 96)
        self.assertTrue(all(96 - 45 <= v <= 96 - 22 for v in inner), inner)
        self.assertLess(c[-1].vel, 96)                                # no hard final note
        t = pianist.tremolo(['Ab4', 'C5'], 'Eb5', 2.0, BPM, vel=90, swell='arch', seed=1)
        top = [n.vel for n in sorted(t, key=lambda n: n.start) if n.pitch == 75]
        self.assertEqual(top[0], 90)
        self.assertTrue(all(v <= 90 - 20 for v in top[1:-1]), top)
        self.assertLess(top[-1], 90)                                  # lands softly
        r = sorted(pianist.run('C5', 'C6', 1.0, BPM, key=KEY, vel=(80, 80), wobble_ms=0), key=lambda n: n.start)
        self.assertLess(r[len(r) // 2].vel, r[0].vel - 5)            # one gesture: lighter in the middle
        m = sorted(pianist.mordent('C5', 1.0, BPM, key=KEY, vel=90), key=lambda n: n.start)
        self.assertGreaterEqual(m[0].vel - m[1].vel, 25)


if __name__ == '__main__':
    unittest.main()
