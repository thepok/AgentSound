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


class ExpressionRules(unittest.TestCase):
    """docs/PIANIST_RULES.md: the rule families Score.perform plays by."""

    def test_travel_time_softer_is_later(self):
        self.assertGreater(rom.travel_ms(36), rom.travel_ms(66))
        self.assertGreater(rom.travel_ms(66), rom.travel_ms(100))
        self.assertTrue(18 < rom.travel_ms(36) - rom.travel_ms(66) < 35)       # a voiced melody leads ~20-30 ms

    def test_spread_loudest_first_within_the_cap(self):
        ch = Clip([(4.0, 2.0, 'G5', 90), (4.0, 2.0, 'Eb5', 60), (4.0, 2.0, 'Bb4', 58), (8.0, 1.0, 'C5', 70)])
        out = sorted(rom.spread(ch, BPM, seed=1), key=lambda n: n.start)
        top = next(n for n in out if n.pitch == note('G5'))
        self.assertEqual(top.start, 4.0)
        for n in out:
            if n.pitch in (note('Eb5'), note('Bb4')):
                ms = (n.start - 4.0) * 60000.0 / BPM
                self.assertTrue(10 < ms <= rom.ASYNC['max_ms'], ms)
                self.assertAlmostEqual(n.start + n.dur, 6.0)            # the release stays
        self.assertIn(8.0, [n.start for n in out])                      # a single note does not move
        self.assertEqual(list(rom.spread(ch, BPM, seed=1)), list(rom.spread(ch, BPM, seed=1)))

    def test_melodic_and_harmonic_charge(self):
        mel = Clip([(0, 1, 'C5', 60), (1, 1, 'D5', 60), (2, 1, 'B4', 60), (3, 1, 'G4', 60)])
        out = {n.pitch: n.vel for n in rom.melodic_charge(mel, lambda b: 'Cmaj7', vel=2.0)}
        self.assertEqual(out[note('C5')], 60)                            # the root rests
        self.assertGreater(out[note('B4')], out[note('D5')])            # the major 7th leans more than the 9th
        self.assertGreater(out[note('D5')], out[note('G4')])            # ... the 9th more than the 5th
        line = Clip([(b, 1, 'C5', 60) for b in range(12)])
        hc = rom.harmonic_charge(line, [(0, 'C'), (4, 'Db'), (8, 'C')], 'C major')
        v = [n.vel for n in sorted(hc, key=lambda n: n.start)]
        self.assertEqual(v[0], 60)
        self.assertGreater(v[4], v[2])                                  # a crescendo into the Neapolitan
        self.assertGreater(v[4], v[10])                                 # ... and relaxing after it

    def test_articulate_repeats_leaps_and_legato(self):
        line = Clip([(0, 1.0, 'G4', 70), (1, 1.0, 'G4', 70), (2, 1.0, 'E5', 70), (3, 1.0, 'D5', 70), (4, 1, 'C5', 70)])
        out = sorted(rom.articulate(line, 60, seed=2), key=lambda n: n.start)
        gap = lambda a, b: (b.start - (a.start + a.dur)) * 1000.0        # ms at 60 BPM
        self.assertTrue(40 <= gap(out[0], out[1]) <= 90)                # the repeated key comes up first
        self.assertTrue(15 <= gap(out[1], out[2]) <= 45)                # the hand leaves before the 9th leap
        for a, b in ((out[2], out[3]), (out[3], out[4])):                # finger legato: an overlap of tens of ms
            self.assertTrue(12 <= -gap(a, b) <= 100, gap(a, b))

    def test_pedal_delay_half_and_vary(self):
        pts = rom.pedal_changes([0, 2, 4], end=8.0, lift_ms=100, bpm=60, delay_ms=60, half=[6.0])
        self.assertIn((0.06, 0.0, 'step'), pts)                          # up 60 ms after the change
        self.assertIn((2.16, 1.0, 'step'), pts)                          # ... down 100 ms later
        self.assertIn((6.06, 0.6, 'step'), pts)                          # a half change
        a = rom.pedal_changes([0, 2, 4], end=8.0, lift_ms=100, bpm=60, delay_ms=60, vary=0.25, seed=3)
        self.assertEqual(a, rom.pedal_changes([0, 2, 4], end=8.0, lift_ms=100, bpm=60, delay_ms=60, vary=0.25,
                                              seed=3))
        ups = [p[0] - c for p, c in zip([p for p in a if p[1] == 0.0], [0, 2, 4])]
        self.assertGreater(len({round(u, 4) for u in ups}), 1)           # the foot is no clock

    def test_perform_rules_override_strict(self):
        s = Song('t', tempo=60, key='C major', seed=1)
        s.section('a', 2)
        rh, lh = s.track('rh', inst.va()), s.track('lh', inst.va())
        sc = rom.score(Clip([(0, 2, 'E5', 80), (2, 2, 'D5', 80), (4, 4, 'C5', 80)]), meter='4/4', key='C major',
                       phrases=[(1, 2)])
        figs = [(0.0, 4.0, 'C', 'flow'), (4.0, 4.0, 'G7', 'flow')]
        with self.assertRaisesRegex(ComposeError, 'unknown key'):
            sc.perform(s, rh, lh, figures=figs, rules={'async': {'lead_ms': 3}})
        with self.assertRaisesRegex(ComposeError, 'unknown family'):
            sc.perform(s, rh, lh, figures=figs, rules={'touch': {}})

    def test_melody_leads_the_left_hand(self):
        s = Song('t', tempo=60, key='C major', seed=1)
        s.section('a', 4)
        rh, lh = s.track('rh', inst.va()), s.track('lh', inst.va())
        mel = Clip([(b * 2.0, 2.0, p, 80) for b, p in enumerate(['E5', 'G5', 'F5', 'D5', 'E5', 'C5', 'D5', 'C5'])])
        sc = rom.score(mel, meter='4/4', key='C major', phrases=[(1, 4)])
        figs = [(k * 4.0, 4.0, c, 'flow') for k, c in enumerate(['C', 'F', 'G7', 'C'])]
        quiet = {'anticipate': 0.0, 'peak_ms': 0.0, 'sync_ms': 0.0, 'lean_ms': 0.0}     # the lead rule alone
        out = sc.perform(s, rh, lh, figures=figs, touch=dict(lo=60, hi=90), rules={'async': quiet})
        lhs = {round(n.start, 1): n.start for n in out['lh']}
        leads = [(lhs[round(round(n.start), 1)] - n.start) * 1000.0 for n in out['rh'] if round(round(n.start), 1) in lhs]
        leads = leads[1:]                                                # (beat 0 cannot move earlier)
        self.assertTrue(all(x > 0.0 for x in leads), leads)             # the melody sounds first (ms)
        self.assertTrue(8.0 < statistics.mean(leads) < 45.0, leads)

    def test_left_hand_rolls_drawn_per_chord(self):
        # a left-hand chord: near-simultaneous or bottom-up (never the fixed top-down crest order), the cadence
        # chord at a phrase end sometimes arpeggiated (beyond max_ms)
        ch = Clip([(b * 2.0, 2.0, p, v) for b in range(60) for p, v in (('C3', 50), ('G3', 36), ('E4', 44))])
        out = sorted(rom.spread(ch, BPM, seed=3, hand='lh', ends=[2.0 * b for b in range(0, 60, 4)]),
                     key=lambda n: (n.start, n.pitch))
        kinds = {'together': 0, 'up': 0, 'down': 0, 'other': 0}
        arps = 0
        for b in range(60):
            g = sorted((n for n in out if b * 2.0 - 1e-9 <= n.start < b * 2.0 + 0.5), key=lambda n: n.pitch)
            ms = [(n.start - b * 2.0) * 60000.0 / BPM for n in g]
            self.assertEqual(min(ms), 0.0)                              # the chord starts where it is written
            if max(ms) < 8:
                kinds['together'] += 1
            elif ms == sorted(ms):
                kinds['up'] += 1
                arps += max(ms) > rom.ASYNC['max_ms']
            elif ms == sorted(ms, reverse=True):
                kinds['down'] += 1
            else:
                kinds['other'] += 1                                     # the softer inner voice a little late
        self.assertEqual(kinds['down'], 0, kinds)
        self.assertGreater(kinds['together'], 15)
        self.assertGreater(kinds['up'], 10)
        self.assertGreater(arps, 0)                                     # an arpeggiated cadence chord
        with self.assertRaisesRegex(ComposeError, 'hand'):
            rom.spread(ch, BPM, hand='both')

    def test_harmonic_charge_tension(self):
        line = Clip([(b, 1, 'C3', 50) for b in range(12)])
        plain = [n.vel for n in sorted(rom.harmonic_charge(line, [(0, 'C'), (4, 'G7'), (8, 'C')], 'C major'),
                                       key=lambda n: n.start)]
        tense = [n.vel for n in sorted(rom.harmonic_charge(line, [(0, 'C'), (4, 'G7'), (8, 'C')], 'C major',
                                                           tension=4.0), key=lambda n: n.start)]
        self.assertEqual(tense[4] - plain[4], 4)                         # the dominant 7th swells ...
        self.assertEqual(tense[2] - plain[2], 2)                         # ... the way into it grows
        self.assertEqual(tense[9], plain[9])                             # ... and the resolution relaxes

    def test_left_hand_follows_the_phrase_and_stays_under(self):
        s = Song('t', tempo=60, key='C major', seed=1)
        s.section('a', 8)
        rh, lh = s.track('rh', inst.va()), s.track('lh', inst.va())
        mel = Clip([(b * 2.0, 2.0, p, 80) for b, p in enumerate(['E5', 'G5', 'A5', 'C6', 'B5', 'G5', 'F5', 'E5'] * 2)])
        sc = rom.score(mel, meter='4/4', key='C major', phrases=[(1, 4), (5, 8)])
        figs = [(k * 4.0, 4.0, c, 'flow') for k, c in enumerate(['C', 'F', 'G7', 'C'] * 2)]
        out = sc.perform(s, rh, lh, figures=figs, touch=dict(lo=50, hi=95))
        top = {}
        for n in out['rh']:
            top[round(n.start)] = max(top.get(round(n.start), 0), n.vel)
        for a in (0.0, 16.0):                                           # every phrase: the hand under the tune
            m = statistics.median(v for b, v in top.items() if a <= b < a + 16)
            h = statistics.median(n.vel for n in out['lh'] if a <= n.start < a + 16)
            self.assertLess(20 * math.log10(h / m), -rom.ACCOMPANIMENT['below_db'] + 0.5)
        bars = [statistics.mean(n.vel for n in out['lh'] if k * 4 <= n.start < k * 4 + 4) for k in range(8)]
        self.assertGreater(20 * math.log10(max(bars) / min(bars)), 1.5)  # it moves with the phrase, not flat

    def test_balance_plan_moves_the_hands(self):
        """balance=: a phrase's hands at its span's dB (note energy, both ways: the left hand may lead), and the
        give and take - the hand swells under a held melody note, recedes under one just struck."""
        def play(balance, ac=None):
            s = Song('t', tempo=60, key='C major', seed=1)
            s.section('a', 8)
            rh, lh = s.track('rh', inst.va()), s.track('lh', inst.va())
            # a phrase of quarters, then one of whole notes (the melody holds: room for the left hand)
            mel = Clip([(b * 1.0, 1.0, p, 80) for b, p in enumerate(['E5', 'G5', 'A5', 'C6'] * 4)] +
                       [(16.0 + b * 4.0, 4.0, p, 80) for b, p in enumerate(['B5', 'G5', 'F5', 'E5'])])
            sc = rom.score(mel, meter='4/4', key='C major', phrases=[(1, 4), (5, 8)])
            figs = [(k * 4.0, 4.0, c, 'flow') for k, c in enumerate(['C', 'F', 'G7', 'C'] * 2)]
            return sc.perform(s, rh, lh, figures=figs, touch=dict(lo=50, hi=95), balance=balance,
                              rules={'accompaniment': ac} if ac else None)

        def bal(out, a):
            e = lambda ns: sum(rom._energy(n.vel) for n in ns if a <= n.start < a + 16)   # noqa: E731
            return 10 * math.log10(e(out['rh']) / e(out['lh']))
        out = play([(0, 16, 6.0), (16, 32, -2.0)])
        self.assertAlmostEqual(bal(out, 0.0), 6.0, delta=0.6)
        self.assertAlmostEqual(bal(out, 16.0), -2.0, delta=0.6)          # the left hand leads the second phrase

        def swell(out):                                 # the hand late in a held melody note over the hand at its onset
            held = [n.vel for n in out['lh'] if 16 <= n.start and (n.start - 16) % 4 >= 2]
            struck = [n.vel for n in out['lh'] if 16 <= n.start and (n.start - 16) % 4 < 0.3]
            return statistics.mean(held) / statistics.mean(struck)
        flat = play([(0, 16, 6.0), (16, 32, -2.0)], {'give': 1.0, 'take': 1.0, 'lead_end': 0.0})
        self.assertGreater(swell(out), swell(flat) * 1.15)              # it swells into the held note
        with self.assertRaisesRegex(ComposeError, 'balance'):
            play([(0, 16)])


class PhraseTempo(unittest.TestCase):
    """PHRASE_TEMPO: every phrase its own arch, the beat lilt drawn per phrase."""

    def _song(self, seed):
        s = Song('t', tempo=60, key='C major', seed=seed)
        s.section('a', 32)
        sc = rom.score(Clip([(b * 4.0, 4.0, 'C5', 70) for b in range(32)]), meter='4/4', key='C major',
                       phrases=[(k, k + 3) for k in range(1, 33, 4)])
        return s, sc

    def test_phrases_draw_their_own_shape(self):
        s, sc = self._song(4)
        sc.rubato(s, depth=0.06, seed='bar')
        rub = s._tempo_plan.rubatos
        self.assertEqual(len(rub), 8)
        shapes = [r[3] for r in rub]
        self.assertTrue(all(isinstance(p, tuple) and p[0] == 'shaped' for p in shapes), shapes)
        self.assertGreater(len({round(p[1], 3) for p in shapes}), 6)       # the peak moves phrase to phrase
        self.assertGreater(max(r[2] for r in rub) / min(r[2] for r in rub), 1.5)   # ... and the depth
        self.assertGreaterEqual(shapes[-1][2], rom.PHRASE_TEMPO['close']['end'][0])  # the last closes deepest
        tm = s.tempo_map()                                               # the span keeps its time
        for a, b, *_ in rub:
            self.assertAlmostEqual(tm.seconds_at(b) - tm.seconds_at(a), b - a, delta=0.02 * (b - a))
        s2, sc2 = self._song(5)                                          # another piece: other phrases
        sc2.rubato(s2, depth=0.06, seed='bar')
        self.assertNotEqual([r[3] for r in s2._tempo_plan.rubatos], shapes)
        with self.assertRaisesRegex(ComposeError, 'unknown key'):
            sc2.rubato(Song('u', tempo=60, seed=1), table={'arch': 1})

    def test_lilt_drawn_per_phrase(self):
        s, sc = self._song(4)
        sc.lilt(s, (0.0, 128.0), beats={3: 0.03}, jitter=0.03)
        lilts = s._tempo_plan.lilts
        self.assertEqual(len(lilts), 8)                                  # one per phrase
        beat3 = [bars[0][2][1] for _, _, bars in lilts]
        self.assertGreater(max(beat3) - min(beat3), 0.01)                # not one fixed delay in every bar
        self.assertTrue(all(abs(d) <= 0.03 * rom.PHRASE_TEMPO['lilt'][1] + 0.05 for d in beat3), beat3)


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
