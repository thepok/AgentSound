import pathlib
import statistics
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import drummer  # noqa: E402
from agentsound.patches import Instrument, inst  # noqa: E402
from agentsound.song import Song  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

BPM = 120
FORM = [('intro', 4), ('verse', 8), ('pre', 2), ('chorus', 8), ('verse2', 8), ('pre2', 2), ('chorus2', 8),
        ('bridge', 8), ('break', 2), ('chorus3', 8), ('end', 2)]
GM = drummer.Kit.of('gm')


def section_bounds(form=FORM, bpb=4.0):
    out, t = {}, 0.0
    for name, bars in form:
        out[name] = (t, t + bars * bpb)
        t += bars * bpb
    return out


def hits_in(part, a, b, tag=None, piece=None):
    return [h for h in part.hits if a - 1e-6 <= h.t < b - 1e-6 and (tag is None or h.tag == tag)
            and (piece is None or h.piece == piece)]


class TestKit(unittest.TestCase):
    def test_gm_and_named_kits(self):
        self.assertEqual(GM.key('kick'), 36)
        self.assertEqual(GM.key('hat_open'), 46)
        self.assertEqual(GM.key('tom1'), 50)
        self.assertEqual(GM.key('floor'), 41)
        br = drummer.Kit.of('big_rusty')
        self.assertEqual(br.key('rimshot'), 40)
        self.assertEqual(br.toms, (47, 45, 43, 41))
        self.assertIsNone(br.key('clap', fallback=False))
        self.assertEqual(GM.key('rimshot'), 38)             # no rimshot key in GM: the snare
        self.assertFalse(GM.has('rimshot'))

    def test_custom_kit_and_errors(self):
        k = drummer.Kit.of({'kick': 36, 'snare': 38, 'hat': 42, 'toms': [48, 45], 'floor': 41})
        self.assertEqual(k.toms, (48, 45, 41))
        self.assertEqual(k.key('ride'), None)
        self.assertEqual(k.key('crash'), None)
        g = drummer.Kit.of({'kick': 'kick', 'snare': 'snare2', 'hat': 'closed_hat', 'bell': 'ride_bell',
                            'toms': ['tom_hi', 'tom_floor']})
        self.assertEqual((g.key('snare'), g.key('hat'), g.key('bell'), g.toms), (40, 42, 53, (48, 41)))
        with self.assertRaises(ComposeError):
            drummer.Kit.of({'cowbell_xl': 60})
        with self.assertRaises(ComposeError):
            drummer.Kit.of({'snare': 'snareXL'})
        with self.assertRaises(ComposeError):
            drummer.Kit.of('nope')

    def test_detects_available_keys_of_a_sampler(self):
        zones = [dict(lo=k, hi=k, root=k, file=f'k{k}.wav') for k in (36, 38, 42, 46, 49)]
        zones += [dict(lo=47, hi=47, root=47, file='tom.wav'), dict(lo=48, hi=48, root=48, file='tom.wav'),
                  dict(lo=41, hi=41, root=41, file='floor.wav')]
        k = drummer.Kit.of(Instrument('sampler', {'samples': zones}))
        self.assertTrue(k.has('hat_open'))
        self.assertFalse(k.has('ride'))
        self.assertFalse(k.has('hat_pedal'))
        self.assertEqual(k.toms, (48, 41))                 # 47 is a copy of 48: one tom
        self.assertEqual(k.key('bell'), None)

    def test_a_key_that_copies_another_pieces_samples_is_not_a_second_piece(self):
        # Big Rusty / Unruly / the outrun kit: 57 plays the 49 crash's samples - a 'crash2' final hit would just
        # double the crash (+6 dB, phasing)
        zones = [dict(lo=k, hi=k, root=k, file=f'k{k}.wav') for k in (36, 38, 40, 42, 44, 46, 51)]
        zones += [dict(lo=49, hi=49, root=49, file='crash.wav'), dict(lo=57, hi=57, root=57, file='crash.wav'),
                  dict(lo=37, hi=37, root=37, file='k38.wav')]
        k = drummer.Kit.of(Instrument('sampler', {'samples': zones}))
        self.assertTrue(k.has('crash'))
        self.assertFalse(k.has('crash2'))
        self.assertEqual(k.key('crash2'), 49)
        self.assertFalse(k.has('side'))                         # 37 copies the snare: no side stick
        p = drummer.arrange(FORM, bpm=BPM, style='rock', density=0.8, seed=1, kit=k)
        self.assertNotIn(57, {n.pitch for n in p.clip})
        end = section_bounds()['end'][0]
        final = [n.pitch for n in p.clip if abs(n.start - end) < 0.05]
        self.assertEqual(final.count(49), 1, final)

    def test_engine_drum_machine(self):
        k = drummer.Kit.of(inst.drums())
        self.assertTrue(k.has('ride'))
        self.assertFalse(k.has('bell'))
        self.assertEqual(k.key('bell'), 51)


class TestPlayable(unittest.TestCase):
    def test_every_style_is_playable_by_two_hands_and_two_feet(self):
        for style in drummer.STYLES:
            for seed in range(4):
                for dens in (0.2, 0.9):
                    p = drummer.arrange(FORM, bpm=BPM, style=style, density=dens, seed=seed)
                    self.assertEqual(drummer.check(p), [], (style, seed, dens))

    def test_limb_rules_hold_on_the_played_times(self):
        p = drummer.arrange(FORM, bpm=140, style='funk', density=1.0, seed=2)
        for limb, gap in (('RF', 80), ('LF', 100)):
            ts = sorted(h.t + h.off / 1000 * 140 / 60 for h in p.hits if h.limb == limb)
            gaps = [(b - a) * 60000 / 140 for a, b in zip(ts, ts[1:])]
            self.assertGreater(min(gaps), gap - 13, limb)
        for c in (h for h in p.hits if h.tag == 'crash'):
            self.assertTrue(any(k.limb == 'RF' and abs(k.t - c.t) < 0.02 for k in p.hits), c)
        opens = [h.t for h in p.hits if h.tag == 'open']
        for h in p.hits:
            if h.piece == 'hat_pedal':
                self.assertFalse(any(abs(h.t - o) < 0.02 for o in opens))

    def test_fast_tempo_hat_falls_back_to_eighths(self):
        p = drummer.arrange([('verse', 4)], bpm=160, style='funk', density=0.5, seed=1)
        hats = sorted(h.t for h in p.hits if h.piece.startswith('hat') and h.limb == 'R')
        self.assertTrue(all(abs((t * 2) - round(t * 2)) < 1e-6 for t in hats), hats[:8])
        self.assertEqual(drummer.check(p), [])

    def test_played_times_keep_the_limb_gaps(self):
        # independent of check()'s constants: after swing and feel, one hand never strikes twice within 55 ms in the
        # groove / 30 ms in a roll, one foot within 70 ms, and no two hands flam the same drum by accident
        for style in drummer.STYLES:
            for bpm in (66, 124, 176):
                p = drummer.arrange(FORM, bpm=bpm, style=style, density=0.9, seed=bpm)
                ms = {id(h): (h.t * 60000 / bpm) + h.off for h in p.hits}
                for limb in ('R', 'L', 'RF', 'LF'):
                    hs = sorted((h for h in p.hits if h.limb == limb and h.tag != 'grace'), key=lambda h: ms[id(h)])
                    for x, y in zip(hs, hs[1:]):
                        roll = {x.tag, y.tag} <= {'fill', 'roll', 'build', 'swell'}
                        need = 30 if roll else 55 if limb in ('R', 'L') else 70
                        self.assertGreaterEqual(ms[id(y)] - ms[id(x)], need, (style, bpm, limb, x, y))
                hands = sorted((h for h in p.hits if h.limb in ('R', 'L') and h.tag != 'grace'),
                               key=lambda h: ms[id(h)])
                for x, y in zip(hands, hands[1:]):
                    if x.piece == y.piece and x.limb != y.limb:
                        self.assertGreater(ms[id(y)] - ms[id(x)], 12, (style, bpm, x, y))

    def test_check_finds_violations(self):
        H = drummer.Hit
        bad = [H(0.0, 'snare', 100, 'L', 'backbeat'), H(0.01, 'snare', 90, 'L', 'backbeat'),
               H(1.0, 'crash', 110, 'R', 'crash')]
        probs = drummer.check(bad, bpm=120)
        self.assertTrue(any('L strikes twice' in p for p in probs), probs)
        self.assertTrue(any('crash without the kick' in p for p in probs), probs)


class TestBudget(unittest.TestCase):
    def test_fills_into_sections_and_budgeted_inside(self):
        bounds = section_bounds()
        starts = sorted(a for a, _ in bounds.values())[1:]
        for seed in range(25):
            p = drummer.arrange(FORM, bpm=BPM, style='rock', density=0.8, seed=seed)
            ends = [round(b, 4) for _, b, _ in p.fills] + [round(m[1], 4) for m in p.moves if m[2] == 'dropout']
            # every section is prepared (a fill / build into it), except the break (a stop) and the end
            for a in starts:
                name = [n for n, (x, _) in bounds.items() if x == a][0]
                if name in ('break', 'end'):
                    continue
                self.assertIn(round(a, 4), ends, (seed, name))
            # phrase fills (not ending on a section start) are at least fill_every (4) bars apart
            phrase = sorted(e for e in ends if e not in [round(x, 4) for x in starts])
            every = sorted(set(ends))
            for x, y in zip(phrase, phrase[1:]):
                self.assertGreaterEqual(y - x, 16.0 - 1e-6, (seed, phrase))
            # never a fill in two bars running: at most one per bar
            bars = [int(e // 4 - 1e-6) for e in every]
            self.assertEqual(len(bars), len(set(bars)), (seed, every))

    def test_flashy_fills_are_rare(self):
        showy = {'toms', 'triplets', 'flams', 'linear'}           # literal: the test must not trust drummer.FLASHY
        for seed in range(30):
            p = drummer.arrange(FORM, bpm=BPM, style='rock', density=1.0, seed=seed)
            fl = sorted((round(a, 4), k) for a, b, k in p.fills if k in showy and b - a >= 2 - 1e-6)
            self.assertEqual(fl, sorted(p.budget['flashy']), seed)
            for (a, k1), (b, k2) in zip(fl, fl[1:]):
                self.assertGreaterEqual(b - a, 8 * 4 - 4 - 1e-6, (seed, fl))       # flashy_every 8 bars
            for i, (a, k1) in enumerate(fl):
                for b, k2 in fl[i + 1:]:
                    if k1 == k2:
                        self.assertGreaterEqual(b - a, 16 * 4 - 4 - 1e-6, (seed, fl))
            total_bars = sum(b for _, b in FORM)
            self.assertLessEqual(len(fl), total_bars // 8 + 1)
            n_fills = len(p.fills)
            self.assertLessEqual(n_fills, len(FORM) + total_bars // 4)
            self.assertLess(n_fills, total_bars / 2.5, (seed, n_fills))

    def test_no_showy_fill_into_a_calm_part(self):
        showy = {'toms', 'triplets', 'flams', 'linear'}
        bounds = section_bounds()
        # the fill from the intro into the verse, and the phrase fills inside the verses and the intro
        calm = [(bounds['verse'][0] - 1, bounds['verse'][0] + 1)] + \
            [(bounds[n][0] + 1, bounds[n][1] - 1) for n in ('intro', 'verse', 'verse2')]
        seen = 0
        for style in ('rock', 'pop', 'ballad', 'funk'):
            for seed in range(20):
                p = drummer.arrange(FORM, bpm=BPM, style=style, density=0.7, seed=seed)
                for a, b, k in p.fills:
                    if any(lo < b < hi for lo, hi in calm):
                        seen += 1
                        self.assertFalse(k in showy and b - a >= 2 - 1e-6, (style, seed, a, b, k))
        self.assertGreater(seen, 80)

    def test_neighbouring_fills_vary(self):
        # kinds are chosen by priority, not in time: the choice still avoids the kind of the fill before / after it
        repeats = 0
        for seed in range(30):
            p = drummer.arrange(FORM, bpm=BPM, style='rock', density=0.6, seed=seed)
            ks = [k for _, _, k in sorted(p.fills) if k != 'build']
            repeats += sum(1 for x, y in zip(ks, ks[1:]) if x == y)
        self.assertLess(repeats / 30, 1.6)             # it was 2.0 when only the last kind chosen was avoided

    def test_a_tighter_budget_keeps_fewer_phrase_fills(self):
        loose = sum(len(drummer.arrange(FORM, bpm=BPM, density=1.0, seed=s, fill_every=4).fills) for s in range(10))
        tight = sum(len(drummer.arrange(FORM, bpm=BPM, density=1.0, seed=s, fill_every=16).fills) for s in range(10))
        none = drummer.arrange(FORM, bpm=BPM, density=1.0, seed=1, phrase_fills=False)
        self.assertLess(tight, loose)
        self.assertEqual(len(none.fills), len([n for n, _ in FORM[1:] if n not in ('break',)]))

    def test_flashy_every_zero_forbids_showy_fills(self):
        for seed in range(10):
            p = drummer.arrange(FORM, bpm=BPM, density=1.0, seed=seed, flashy_every=0)
            self.assertEqual(p.budget['flashy'], [])
            for a, b, kind in p.fills:
                if b - a >= 2 - 1e-6:
                    self.assertNotIn(kind, drummer.FLASHY)

    def test_memory_counts_song_wide(self):
        mem = drummer.Memory()
        drummer.arrange([('verse', 8), ('chorus', 8)], bpm=BPM, density=1.0, seed=3, memory=mem)
        clock = mem.clock
        self.assertEqual(clock, 64.0)
        p2 = drummer.arrange([('verse2', 8), ('chorus2', 8)], bpm=BPM, density=1.0, seed=3, memory=mem)
        self.assertEqual(p2.start, 64.0)
        fl = sorted(t for t, _, f in mem.fills if f)
        for a, b in zip(fl, fl[1:]):
            self.assertGreaterEqual(b - a, 32 - 1e-6)
        with self.assertRaises(ComposeError):
            mem.played(0, 'solo')


class TestSections(unittest.TestCase):
    def setUp(self):
        self.p = drummer.arrange(FORM, bpm=BPM, style='rock', density=0.6, seed=11)
        self.b = section_bounds()

    def test_verse_hat_chorus_ride_crash_on_the_chorus(self):
        va, vb = self.b['verse']
        ca, cb = self.b['chorus']
        self.assertTrue(hits_in(self.p, va, vb, piece='hat'))
        self.assertFalse(hits_in(self.p, va + 4, vb - 4, piece='ride'))
        self.assertGreater(len(hits_in(self.p, ca, cb, piece='ride')), 30)
        crash = [h for h in self.p.hits if h.tag == 'crash' and abs(h.t - ca) < 1e-6]
        self.assertTrue(crash)

    def test_chorus_is_bigger_than_the_verse(self):
        def mean_vel(sec, tag):
            a, b = self.b[sec]
            return statistics.mean(h.vel for h in hits_in(self.p, a, b, tag=tag))
        self.assertGreater(mean_vel('chorus', 'backbeat'), mean_vel('verse', 'backbeat') + 8)
        self.assertGreater(mean_vel('chorus', 'kick'), mean_vel('verse', 'kick') + 5)
        va, vb = self.b['verse']
        ca, cb = self.b['chorus']
        self.assertGreaterEqual(len(hits_in(self.p, ca, cb, tag='kick')), len(hits_in(self.p, va, vb, tag='kick')))

    def test_build_into_the_chorus_stop_on_the_break_and_an_ending(self):
        kinds = {(round(b, 3), n) for a, b, n in self.p.fills}
        self.assertIn((self.b['chorus'][0], 'build'), kinds)
        stops = [m for m in self.p.moves if m[2] == 'stop']
        self.assertEqual(stops[0][0], self.b['break'][0])
        ba, bb = self.b['break']
        first_bar = [h for h in hits_in(self.p, ba, ba + 4) if h.tag not in ('crash', 'kick', 'hit')]
        self.assertEqual([h for h in first_bar if h.t > ba + 0.01 and h.tag not in ('fill', 'grace')], [])
        endings = [m for m in self.p.moves if m[2] == 'ending']
        self.assertEqual(endings[0][0], self.b['end'][0])
        self.assertEqual(endings[0][3], 'roll')

    def test_kick_locks_to_the_bass(self):
        from agentsound.patterns import Clip
        bass = Clip([(0, 0.5, 40, 90), (1.5, 0.5, 40, 90), (2.0, 0.5, 40, 90), (2.75, 0.25, 43, 90),
                     (3.5, 0.5, 40, 90)], length=4).loop(32)
        p = drummer.arrange([('verse', 8)], bpm=110, style='rock', seed=1, lock=bass, human=False, phrase_fills=False)
        bass_at = {0.0, 1.5, 2.0, 3.5}                          # the bass onsets that can take a kick
        kicks = [round(h.t % 4, 2) for h in p.hits if h.piece == 'kick' and h.tag == 'kick' and h.t < 28]
        self.assertTrue(set(kicks) <= bass_at, kicks)         # every kick lands with the bass, not the 16th
        self.assertIn(0.0, kicks)
        free = drummer.arrange([('verse', 8)], bpm=110, style='rock', seed=1, human=False, phrase_fills=False)
        n_free = len([h for h in free.hits if h.piece == 'kick' and h.tag == 'kick' and h.t < 28])
        self.assertLessEqual(len(kicks), n_free)               # the style's density, not every bass note
        ans = drummer.arrange([('verse', 8)], bpm=110, style='rock', seed=1, lock=bass, lock_mode='answer',
                              human=False, phrase_fills=False)
        akicks = [round(h.t % 4, 2) for h in ans.hits if h.piece == 'kick' and h.tag == 'kick' and h.t < 28]
        self.assertIn(0.0, akicks)                              # the one together
        self.assertFalse((set(akicks) - {0.0}).intersection(bass_at), akicks)    # then in the bass's gaps
        with self.assertRaises(ComposeError):
            drummer.arrange([('verse', 8)], bpm=110, lock='bass')
        with self.assertRaises(ComposeError):
            drummer.arrange([('verse', 8)], bpm=110, lock=bass, lock_mode='under')

    def test_every_style_keeps_the_kick_on_one(self):
        # Motown's snare plays every beat: the kick still lands on 1 (and 3) - only 2 and 4 trade places with it
        for style in drummer.STYLES:
            p = drummer.arrange([('verse', 8), ('chorus', 8)], bpm=110, style=style, seed=1, human=False,
                                phrase_fills=False)
            for bar in (0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13):
                self.assertTrue([h for h in p.hits if h.limb == 'RF' and abs(h.t - 4 * bar) < 1e-6], (style, bar))
        m = drummer.arrange([('verse', 4)], bpm=110, style='motown', seed=1, human=False, phrase_fills=False)
        self.assertIn(2.0, {h.t % 4 for h in m.hits if h.piece == 'kick'})

    def test_plan_values_are_strict(self):
        for bad in ({'fill': 'bombs'}, {'fill': True}, {'crash': 'yes'}, {'ghosts': 3}, {'time': 5},
                    {'stop': 1}):
            with self.assertRaises(ComposeError, msg=bad):
                drummer.arrange(FORM, bpm=BPM, plan={'chorus': bad})
        p = drummer.arrange(FORM, bpm=BPM, seed=1, plan={'chorus': {'fill': False}, 'verse2': {'fill': 'toms'}})
        ends = {round(b, 4): k for a, b, k in p.fills}
        self.assertNotIn(self.b['chorus'][0], ends)
        self.assertEqual(ends[self.b['verse2'][0]], 'toms')

    def test_bridge_is_a_variation(self):
        a, b = self.b['bridge']
        self.assertGreater(len(hits_in(self.p, a, b, piece='floor')), 20)      # the floor-tom groove

    def test_plan_overrides(self):
        p = drummer.arrange(FORM, bpm=BPM, style='rock', seed=1,
                            plan={'verse': {'time': 'ride', 'energy': 0.3}, 'bridge': 'half', 'chorus': 'hat16'})
        va, vb = self.b['verse']
        self.assertTrue(hits_in(p, va + 4, vb - 4, piece='ride'))
        ba, bb = self.b['bridge']
        backs = {round((h.t - ba) % 4, 3) for h in hits_in(p, ba, bb - 4, tag='backbeat')}
        self.assertEqual(backs, {2.0})
        with self.assertRaises(ComposeError):
            drummer.arrange(FORM, bpm=BPM, plan={'verse': {'colour': 'red'}})
        with self.assertRaises(ComposeError):
            drummer.arrange(FORM, bpm=BPM, plan={'nosuch': 'half'})

    def test_song_form_and_sections(self):
        s = Song('t', tempo=100)
        s.section('intro', bars=2)
        v = s.section('verse', bars=4)
        c = s.section('chorus', bars=4)
        p = drummer.arrange(s, style='pop', seed=2)
        self.assertEqual(p.start, 0.0)
        self.assertEqual(p.bpm, 100)
        p2 = drummer.arrange([v, c], style='pop', bpm=100, seed=2)
        self.assertEqual(p2.start, v.start)
        self.assertTrue(all(n.start >= 0 for n in p2.clip))
        t = s.track('drums', inst.drums())
        t.humanize(5, 5)
        p2.play(t)
        self.assertEqual(len(t.notes), len(p2.clip))
        self.assertEqual(t._human[:2], (0.0, 0.0))
        with self.assertRaises(ComposeError):
            drummer.arrange([v, c], bpm=100, at=3.0)


class TestTouchAndFeel(unittest.TestCase):
    def test_velocities_are_shaped(self):
        p = drummer.arrange(FORM, bpm=BPM, style='funk', density=0.8, seed=5)
        ghosts = [h.vel for h in p.hits if h.tag == 'ghost']
        self.assertGreater(len(ghosts), 20)
        self.assertTrue(all(15 <= v <= 35 for v in ghosts), (min(ghosts), max(ghosts)))
        backs = [h.vel for h in p.hits if h.tag == 'backbeat']
        self.assertGreater(min(backs), max(ghosts) + 40)
        on = [h.vel for h in p.hits if h.piece == 'hat' and abs(h.t - round(h.t)) < 1e-6]
        off = [h.vel for h in p.hits if h.piece == 'hat' and abs(h.t - round(h.t)) > 0.1]
        self.assertGreater(statistics.mean(on), statistics.mean(off) + 12)
        vels = sorted(n.vel for n in p.clip)
        p10, p90 = vels[len(vels) // 10], vels[9 * len(vels) // 10]
        self.assertGreaterEqual(p90 - p10, 40)
        # repeated strokes are never identical robots: the same stroke role varies
        self.assertGreater(len({round(v) for v in backs}), 10)

    def test_timing_is_human_and_bounded(self):
        p = drummer.arrange(FORM, bpm=BPM, style='rock', density=0.6, seed=9)
        offs = [h.off for h in p.hits if h.tag != 'grace']
        self.assertLessEqual(max(abs(o) for o in offs), 23.0)
        self.assertGreater(statistics.pstdev(offs), 1.5)
        L = statistics.mean(h.off for h in p.hits if h.limb == 'L' and h.tag == 'backbeat')
        R = statistics.mean(h.off for h in p.hits if h.limb == 'R' and h.tag == 'time')
        self.assertGreater(L, R + 1.5)                     # the backbeat sits a little behind the hat
        m = drummer.arrange(FORM, bpm=BPM, style='synthpop', seed=9)
        self.assertLess(statistics.pstdev(h.off for h in m.hits if h.limb != 'X'), 1.0)
        flat = drummer.arrange(FORM, bpm=BPM, style='rock', seed=9, human=False)
        self.assertTrue(all(h.off == 0.0 for h in flat.hits))

    def test_flams_keep_their_grace_before_the_main_stroke(self):
        c = drummer.flam_fill(2, BPM, seed=1, at=1.0)       # the first grace falls just before `at`
        ns = sorted((n for n in c if n.pitch != 36), key=lambda n: n.start)
        self.assertLess(ns[0].start, 1.0)
        self.assertEqual(len(ns), 8)
        for g, m in zip(ns[0::2], ns[1::2]):
            gap_ms = (m.start - g.start) * 60000 / BPM
            self.assertTrue(10 <= gap_ms <= 30, gap_ms)
            self.assertLess(g.vel, m.vel - 25)

    def test_shuffle_swings_the_offbeats(self):
        p = drummer.arrange([('verse', 2)], bpm=100, style='shuffle', seed=1, human=False)
        hats = sorted({round(n.start % 1.0, 3) for n in p.clip if n.pitch == 42})
        self.assertEqual(hats, [0.0, 0.62])

    def test_swing_moves_the_subdivisions_with_the_offbeat(self):
        # a 16th fill in a swung-8th shuffle swings too (0, .31, .62, .81) - never a 16th squeezed against the late
        # & (0, .25, .62, .75); triplets are left alone
        p = drummer.arrange([('verse', 4), ('chorus', 4)], bpm=100, style='shuffle', seed=1, human=False,
                            plan={'chorus': {'fill': 'snare', 'fill_len': 2}}, phrase_fills=False)
        fill = sorted(round(h.t - 14, 3) for h in p.hits if 14 - 1e-6 <= h.t < 16 and h.tag == 'fill')
        self.assertEqual(fill, [0.0, 0.31, 0.62, 0.81, 1.0, 1.31, 1.62, 1.81])
        self.assertEqual(drummer._swing_t(1 / 3, 0.62, 0.5), 1 / 3)
        self.assertAlmostEqual(drummer._swing_t(2.125, 0.62, 0.5), 2.155)

    def test_jazz_on_sticks_stays_behind_the_piano(self):
        # HUMAN_FEEDBACK: the ride and the kick bombs stay soft (45-60) even in the hot chorus
        p = drummer.arrange(FORM, bpm=140, style='jazz', density=0.8, seed=3)
        ride = [h.vel for h in p.hits if h.piece == 'ride' and h.tag == 'time']
        self.assertLessEqual(max(ride), 68)
        crashes = [h.t for h in p.hits if h.tag == 'crash']
        bombs = [h.vel for h in p.hits if h.piece == 'kick' and h.tag == 'kick' and h.vel > 40
                 and not any(abs(h.t - c) < 0.01 for c in crashes)]
        self.assertTrue(bombs)
        self.assertLessEqual(max(bombs), 62)

    def test_deterministic(self):
        a = drummer.arrange(FORM, bpm=BPM, style='pop', density=0.6, seed=4)
        b = drummer.arrange(FORM, bpm=BPM, style='pop', density=0.6, seed=4)
        c = drummer.arrange(FORM, bpm=BPM, style='pop', density=0.6, seed=5)
        self.assertEqual(list(a.clip), list(b.clip))
        self.assertEqual(a.moves, b.moves)
        self.assertNotEqual(list(a.clip), list(c.clip))


class TestMoves(unittest.TestCase):
    def test_registry(self):
        for name, fn in drummer.MOVES.items():
            self.assertTrue(callable(fn), name)
            self.assertTrue(fn.__doc__, name)

    def test_tom_run_descends(self):
        c = drummer.tom_run(2, BPM, seed=1, timing_ms=0)
        ns = sorted(c, key=lambda n: n.start)
        toms = [n.pitch for n in ns if n.pitch != 38 and n.pitch != 36]
        self.assertEqual(toms, sorted(toms, reverse=True))
        self.assertEqual(ns[0].pitch, 38)                   # 2 beats: opens on the snare
        hands = [n for n in ns if n.pitch != 36]
        self.assertLess(hands[0].vel, hands[-1].vel)       # crescendo
        self.assertAlmostEqual(c.length, 2.0)

    def test_linear_fill_never_doubles(self):
        c = drummer.linear_fill(4, BPM, seed=2, timing_ms=0)
        starts = [round(n.start, 4) for n in c]
        self.assertEqual(len(starts), len(set(starts)))
        self.assertIn(36, {n.pitch for n in c})

    def test_build_accelerates_and_crescendos(self):
        c = drummer.build(4, BPM, timing_ms=0)
        sn = sorted((n for n in c if n.pitch == 38), key=lambda n: n.start)
        gaps = [b.start - a.start for a, b in zip(sn, sn[1:])]
        self.assertGreater(gaps[0], gaps[-1] * 3)
        self.assertLess(sn[0].vel, sn[-1].vel - 30)

    def test_small_moves(self):
        ch = drummer.crash_hit(BPM, timing_ms=0)
        self.assertEqual(sorted(n.pitch for n in ch), [36, 49])
        oh = drummer.open_hat(BPM, length=0.5, timing_ms=0)
        self.assertEqual([n.pitch for n in sorted(oh, key=lambda n: n.start)], [46, 44])
        self.assertEqual(len(drummer.count_in(BPM, bars=1)), 4)
        st = drummer.stop(BPM, length=4)
        self.assertEqual({n.pitch for n in st if n.start < 0.1}, {36, 38, 49})
        self.assertTrue(any(n.start > 3 for n in st))       # the pickup into the next bar
        sw = sorted(drummer.swell(4, BPM, timing_ms=0), key=lambda n: n.start)
        self.assertLess(sw[0].vel, 30)
        self.assertGreater(sw[-1].vel, 80)
        self.assertTrue(drummer.pickup(BPM, seed=3))
        self.assertTrue(drummer.roll(2, BPM))
        self.assertTrue(drummer.dropout(BPM))
        self.assertTrue(drummer.snare_run(1, BPM))
        self.assertTrue(drummer.triplet_fill(2, BPM))
        c = drummer.tom_run(1, BPM, at=3.0)
        self.assertGreaterEqual(min(n.start for n in c), 2.95)

    def test_beat_is_time_only(self):
        c = drummer.beat('rock', 4, BPM, role='verse', seed=1, human=False)
        self.assertAlmostEqual(c.length, 16.0)
        self.assertNotIn(49, {n.pitch for n in c})
        self.assertEqual({round(n.start % 4, 3) for n in c if n.pitch == 38 and n.vel > 60}, {1.0, 3.0})

    def test_kit_without_toms_or_ride(self):
        k = drummer.Kit.of({'kick': 36, 'snare': 38, 'hat': 42, 'hat_open': 46, 'crash': 49})
        p = drummer.arrange(FORM, bpm=BPM, style='rock', density=1.0, seed=3, kit=k)
        self.assertEqual(drummer.check(p), [])
        self.assertLessEqual({n.pitch for n in p.clip}, {36, 38, 42, 46, 49})
        self.assertFalse([h for h in p.hits if h.piece.startswith('tom') or h.piece == 'floor'
                          and k.key('floor', fallback=False) is not None])

    def test_brush_kit_jazz(self):
        p = drummer.arrange([('A', 8), ('B', 8)], bpm=132, style='jazz', seed=1, kit='swirly')
        pitches = {n.pitch for n in p.clip}
        self.assertIn(38, pitches)                          # brush taps
        self.assertTrue({60, 64} & pitches)                 # the Swirly stir
        self.assertLess(max(n.vel for n in p.clip if n.pitch == 36), 70)    # the kick stays soft
        waltz = Song('w', tempo=150)
        waltz.section('A', bars=4, meter=(3, 4))
        self.assertEqual(drummer.check(drummer.arrange(waltz, style='jazz', seed=2)), [])
        with self.assertRaises(ComposeError):
            drummer.arrange(waltz, style='rock')

    def test_errors(self):
        with self.assertRaises(ComposeError):
            drummer.arrange(FORM, bpm=BPM, style='polka')
        with self.assertRaises(ComposeError):
            drummer.arrange(FORM, bpm=BPM, feel={'X': 3})
        with self.assertRaises(ComposeError):
            drummer.arrange(FORM, bpm=BPM, fills={'bombs': 1})
        with self.assertRaises(ComposeError):
            drummer.arrange(FORM)                           # no tempo
        with self.assertRaises(ComposeError):
            drummer.arrange(FORM, bpm=BPM, density=2)


if __name__ == '__main__':
    unittest.main()
