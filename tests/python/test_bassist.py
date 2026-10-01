import pathlib
import statistics
import sys
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import articulation as art, bassist, library, patches  # noqa: E402
from agentsound.patterns import Clip, walking_bass  # noqa: E402
from agentsound.song import Song  # noqa: E402
from agentsound.theory import Chord, ComposeError, Key, Progression, note  # noqa: E402

BPM = 112
KEY = Key('E minor')
PROG = Progression('Em C G D Em C Am B7', key=KEY)                    # 8 bars
PROGS = ['Em C G D', 'F C Dm Bb', 'Am7 D7 Gmaj7 Cmaj7', 'Fm9 Dbmaj7 Bbm9 Eb7sus4:0.5 Eb7b9:0.5', 'E9 % A9 B7#9',
         'C G/B Am F']
KICKS = [None, 'x.....x.x.......', 'x...x...x...x...', 'x.....x...x..x..', 'x.........x.....']


def fake_track(typ, **params):
    return types.SimpleNamespace(instrument=types.SimpleNamespace(type=typ, params=params))


def plain_onsets(clip):
    """Notes that start a sound (no glide into them, not the soft second note of a legato pair)."""
    ns = sorted(clip, key=lambda n: n.start)
    out = []
    for i, n in enumerate(ns):
        prev = ns[i - 1] if i else None
        tied = prev is not None and prev.start + prev.dur > n.start + 1e-3
        if art.glide_of(n) or tied:
            continue
        out.append(n)
    return out


class TestMoves(unittest.TestCase):
    def test_approach_kinds(self):
        c = bassist.approach('A1', BPM, kind='chromatic', at=3.5)
        self.assertEqual([(n.start, n.pitch) for n in c], [(3.5, note('Ab1'))])
        c = bassist.approach('A1', BPM, kind='chromatic', above=True, notes=2, grid=0.25)
        self.assertEqual([n.pitch for n in c], [note('B1'), note('Bb1')])
        c = bassist.approach('A1', BPM, kind='diatonic', key=KEY)
        self.assertEqual(c[0].pitch, note('G1'))
        c = bassist.approach('A1', BPM, kind='fifth', above=True)
        self.assertEqual(c[0].pitch, note('E2'))
        with self.assertRaises(ComposeError):
            bassist.approach('A1', BPM, kind='bebop')

    def test_walk_up_and_passing(self):
        c = bassist.walk_up('C2', BPM, steps=3, key='C major', at=1.0)
        self.assertEqual([n.pitch for n in c], [note('G1'), note('A1'), note('B1')])
        self.assertEqual([n.start for n in c], [1.0, 2.0, 3.0])
        self.assertLess(c[0].vel, c[-1].vel)                       # a small crescendo into the target
        d = bassist.walk_up('C2', BPM, steps=2, direction='down', key='C major')
        self.assertEqual([n.pitch for n in d], [note('E2'), note('D2')])
        p = bassist.passing('C2', 'G2', 2.0, BPM, key='C major')
        self.assertEqual([n.pitch for n in p], [note('C2'), note('D2'), note('E2'), note('F2')])
        pc = bassist.passing('C2', 'E2', 1.0, BPM, chromatic=True)
        self.assertEqual([n.pitch for n in pc], [36, 37, 38, 39])

    def test_octave_pop_and_slap_levels(self):
        c = bassist.octave_pop('E1', BPM, dur=0.5)
        self.assertEqual([n.pitch for n in c], [28, 40])
        self.assertEqual({art.articulation_of(n) for n in c}, {'staccato'})
        s = bassist.octave_pop('E1', BPM, slap=True, vel=108)
        self.assertTrue(104 <= s[0].vel <= 115 and 116 <= s[1].vel <= 127, [n.vel for n in s])

    def test_slide_is_a_legato_glide(self):
        c = sorted(bassist.slide('A1', 1.0, BPM, by=-2, ms=80, at=4.0), key=lambda n: n.start)
        self.assertEqual([n.pitch for n in c], [note('G1'), note('A1')])
        self.assertEqual(c[0].start, 4.0)
        self.assertEqual(art.glide_of(c[1]), 80.0)
        self.assertGreater(c[0].start + c[0].dur, c[1].start)      # the pluck sounds into the glide
        self.assertLess((c[1].start - c[0].start) * 60 / BPM, 0.03)
        self.assertAlmostEqual(c[1].start + c[1].dur, 5.0, places=6)
        with self.assertRaises(ComposeError):
            bassist.slide('A1', 1.0, BPM, by=0)

    def test_slide_out_falls_at_the_end(self):
        c = sorted(bassist.slide_out('A2', 2.0, BPM, drop=-7, ms=200), key=lambda n: n.start)
        self.assertEqual([n.pitch for n in c], [note('A2'), note('D2')])
        self.assertTrue(art.glide_of(c[1]))
        self.assertLess(c[1].vel, c[0].vel)
        self.assertAlmostEqual(c[1].start + c[1].dur, 2.0, places=6)

    def test_hammer_on_and_pull_off(self):
        h = sorted(bassist.hammer_on('G1', 'A1', 0.5, BPM), key=lambda n: n.start)
        self.assertEqual([n.pitch for n in h], [note('G1'), note('A1')])
        self.assertGreater(h[0].start + h[0].dur, h[1].start)      # legato: no new pluck
        self.assertLess(h[1].vel, h[0].vel)
        p = sorted(bassist.pull_off('A1', 'G1', 0.5, BPM), key=lambda n: n.start)
        self.assertEqual([n.pitch for n in p], [note('A1'), note('G1')])
        with self.assertRaises(ComposeError):
            bassist.hammer_on('G1', 'D2', 0.5, BPM)

    def test_ghost_and_rake(self):
        g = bassist.ghost('E1', BPM, vel=30)
        self.assertEqual(art.articulation_of(g[0]), 'mute')
        self.assertLessEqual(g[0].dur, 0.15)
        r = bassist.rake('E1', 0.75, BPM, at=3.25)
        self.assertEqual(len(r), 3)
        self.assertTrue(all(art.articulation_of(n) == 'mute' and 20 <= n.vel <= 45 for n in r))
        self.assertAlmostEqual(max(n.start for n in r), 3.75)
        self.assertLess(r[0].vel, r[-1].vel)

    def test_fills_lead_into_the_target(self):
        for kind in bassist.FILL_KINDS:
            for tgt in ('E1', 'A1', 'C2', 'F#2'):
                c = bassist.fill(kind, tgt, 2.0, BPM, chord='B7', key=KEY, at=6.0, seed=3)
                self.assertTrue(len(c), kind)
                ns = sorted(c, key=lambda n: n.start)
                self.assertGreaterEqual(ns[0].start, 6.0 - 1e-9, kind)
                self.assertLessEqual(ns[-1].start + ns[-1].dur, 8.0 + 1e-6, kind)
                self.assertTrue(all(28 <= n.pitch <= 55 for n in ns), (kind, tgt, [n.pitch for n in ns]))
                self.assertEqual(bassist.check(c, BPM), [], (kind, tgt))
                if kind not in ('rake', 'octave', 'slide', 'pentatonic', 'sixteenths', 'triplet'):
                    self.assertLessEqual(abs(ns[-1].pitch - note(tgt)), 2, (kind, tgt, [n.pitch for n in ns]))
        with self.assertRaises(ComposeError):
            bassist.fill('solo', 'E1', 1.0, BPM)

    def test_pedal(self):
        c = bassist.pedal('E1', 4.0, BPM, grid=0.5, octave=1.0, seed=2)
        self.assertEqual(len(c), 8)
        self.assertEqual({n.pitch for n in c if n.start % 1 == 0}, {28})
        self.assertEqual({n.pitch for n in c if n.start % 1 != 0}, {40})
        self.assertGreater(c[0].vel, c[1].vel)

    def test_walk_wraps_walking_bass(self):
        p = Progression('Dm7 G7 Cmaj7 A7', key='C major')
        w = bassist.walk(p, BPM, key='C major', seed=4, skip=0.3)
        ref = walking_bass(p, key='C major', seed=4, skip=0.3, vel=90)
        self.assertEqual([n.pitch for n in w], [n.pitch for n in ref])
        skips = [n for n in w if art.articulation_of(n) == 'mute']
        self.assertTrue(skips)
        self.assertTrue(all(24 <= n.vel <= 40 for n in skips))

    def test_moves_registry(self):
        self.assertEqual(set(bassist.MOVES), {'approach', 'walk_up', 'passing', 'octave_pop', 'slide', 'slide_out',
                                              'hammer_on', 'pull_off', 'ghost', 'rake', 'fill', 'pedal', 'walk'})
        for name, fn in bassist.MOVES.items():
            self.assertTrue(fn.__doc__, name)


class TestPlayability(unittest.TestCase):
    def test_check_finds_problems(self):
        self.assertEqual(bassist.check(Clip([(0, 0.5, 'E1', 90), (0.5, 0.5, 'G1', 90)], length=1), BPM), [])
        self.assertTrue(bassist.check(Clip([(0, 0.5, 'C1', 90)], length=1), BPM))           # below E1
        self.assertEqual(bassist.check(Clip([(0, 0.5, 'C1', 90)], length=1), BPM, strings=5), [])
        jump = Clip([(0, 0.2, 'Bb1', 90), (0.25, 0.2, 'G3', 90)], length=1)
        self.assertIn('jump', ' '.join(bassist.check(jump, 200)))
        self.assertEqual(bassist.check(jump.stretch(4), 100), [])                             # slow enough
        self.assertIn('at once', ' '.join(bassist.check(Clip([(0, 1, 'E1', 90), (0, 1, 'A1', 90)], length=1), BPM)))
        self.assertIn('sounding', ' '.join(bassist.check(Clip([(0, 1.5, 'E1', 90), (1, 1, 'A1', 90)], length=2),
                                                         BPM)))

    def test_fingering_stays_in_position(self):
        plan = bassist.fingering(Clip([(0, 0.5, 'E1', 90), (0.5, 0.5, 'G1', 90), (1, 0.5, 'A1', 90),
                                       (1.5, 0.5, 'C2', 90)], length=2), BPM)
        self.assertEqual(plan, [(0, 0), (0, 3), (1, 0), (1, 3)])

    def test_every_style_is_playable_over_many_seeds(self):
        for style in bassist.STYLES:
            for i in range(24):
                pr = PROGS[i % len(PROGS)]
                line = bassist.arrange(pr + ' ' + pr, bpm=(84, 126, 150)[i % 3], style=style,
                                       part=('verse', 'chorus', 'intro', 'bridge')[i % 4], seed=i,
                                       kick=KICKS[i % len(KICKS)], density=(i % 5) / 4,
                                       ending='slide' if i % 7 == 6 else None)
                self.assertEqual(line.problems, [], (style, i))
                lo, hi = bassist.RANGES[4]
                self.assertTrue(all(lo <= n.pitch <= hi for n in line.clip), (style, i))

    def test_five_string_reaches_b0(self):
        line = bassist.arrange('B C D E', bpm=BPM, style='rock', strings=5, low='B0', seed=1, part='verse')
        self.assertEqual(min(n.pitch for n in line.clip if n.start < 0.1), note('B0'))
        self.assertEqual(line.problems, [])
        with self.assertRaises(ComposeError):
            bassist.arrange('B C D E', bpm=BPM, style='rock', low='B0')                   # 4 strings: no B0


class TestArrange(unittest.TestCase):
    def line(self, **kw):
        a = dict(bpm=BPM, key=KEY, style='rock', part='chorus', seed=3)
        a.update(kw)
        return bassist.arrange(PROG, **a)

    def test_deterministic(self):
        for style in bassist.STYLES:
            a = self.line(style=style, seed=9, kick='x.....x.x.......')
            b = self.line(style=style, seed=9, kick='x.....x.x.......')
            self.assertEqual(a.clip, b.clip, style)
            self.assertEqual(a.moves, b.moves, style)
        self.assertNotEqual(self.line(style='pop', seed=1).clip, self.line(style='pop', seed=2).clip)

    def test_roots_on_the_changes(self):
        for style in ('rock', 'pop', 'country', 'motown', 'disco', 'ballad', 'synth', 'funk'):
            for seed in range(8):
                line = self.line(style=style, seed=seed, timing=False, flash={}, fills={}, approach=0.0,
                                 section_end=False)
                for st, _, ch in PROG:
                    at = [n for n in line.clip if abs(n.start - st) < 0.03 and art.articulation_of(n) != 'mute']
                    self.assertTrue(at, (style, seed, st))
                    self.assertEqual(at[0].pitch % 12, ch.bass_pc, (style, seed, st, ch))

    def test_slash_bass(self):
        line = bassist.arrange('C G/B Am F', bpm=BPM, style='pop', timing=False, seed=1, fills={}, flash={})
        firsts = [min((n for n in line.clip if abs(n.start - b) < 0.03), key=lambda n: n.start).pitch % 12
                  for b in (0, 4, 8, 12)]
        self.assertEqual(firsts, [0, 11, 9, 5])

    def test_locks_to_the_kick(self):
        kick = 'x.....x...x..x..'
        tight = [self.line(style='pop', part='verse', kick=kick, lock=1.0, seed=s).locked for s in range(10)]
        loose = [self.line(style='pop', part='verse', kick=kick, lock=0.0, seed=s).locked for s in range(10)]
        self.assertGreaterEqual(min(tight), 0.9)
        self.assertGreater(statistics.mean(tight), statistics.mean(loose))
        # a drum clip works too (kick notes 36): the verse doubles the kick's rhythm
        from agentsound.patterns import drums
        beat = drums({'kick': 'x.....x.x.......', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'})
        v = [self.line(kick=beat, part='verse', seed=s, cells={'kick': 1.0}, timing=False, flash={}, fills={},
                       approach=0.0, section_end=False) for s in range(3)]
        for ln in v:
            ons = sorted({round(n.start % 4, 3) for n in ln.clip if art.articulation_of(n) != "mute"})
            self.assertEqual(ons, [0.0, 1.5, 2.0])

    def test_funk_interlocks_with_the_kick(self):
        kick = 'x.....x...x..x..'
        later = {1.5, 2.5, 3.25}
        on, total, ones = 0, 0, 0
        for seed in range(8):
            line = self.line(style='funk', part='verse', kick=kick, seed=seed, timing=False, flash={}, fills={},
                             approach=0.0, section_end=False)
            played = [n for n in line.clip if art.articulation_of(n) != 'mute']
            on += sum(1 for n in played if round(n.start % 4, 3) in later)
            ones += sum(1 for n in played if n.start % 4 < 0.01)
            total += 3 * 8
        self.assertLess(on / total, 0.2)                    # the gaps answered, not the kick doubled
        self.assertEqual(ones, 8 * 8)                       # the one together
        rock = [self.line(style='rock', part='verse', kick=kick, seed=s, lock=1.0).locked for s in range(4)]
        self.assertGreaterEqual(min(rock), 0.9)

    def test_velocities_are_shaped(self):
        for style in bassist.STYLES:
            line = self.line(style=style, seed=4, kick='x.....x.x.......', timing=False)
            vs = [n.vel for n in line.clip if art.articulation_of(n) != 'mute']
            q = statistics.quantiles(vs, n=10)
            self.assertGreaterEqual(q[-1] - q[0], 8 if style == 'tumbao' else 10, (style, vs))
            down = [n.vel for n in line.clip if n.start % 4 < 0.01 and art.articulation_of(n) != 'mute']
            off = [n.vel for n in line.clip if abs(n.start % 1 - 0.5) < 0.01 and art.articulation_of(n) != 'mute']
            if down and off:
                self.assertGreater(statistics.mean(down), statistics.mean(off) + 5, style)
            ghosts = [n.vel for n in line.clip if art.articulation_of(n) == 'mute']
            self.assertTrue(all(18 <= v <= 46 for v in ghosts), (style, ghosts))
        slap = self.line(style='funk', technique='slap', seed=2, timing=False, fills={}, flash={})
        thumbs = [n.vel for n in slap.clip if n.start % 1 < 0.01 and art.articulation_of(n) != 'mute']
        self.assertTrue(thumbs and min(thumbs) >= 100, thumbs)

    def test_the_form_verse_calmer_chorus_bigger(self):
        for style in ('rock', 'pop', 'funk', 'motown', 'disco', 'ballad', 'synth'):
            v, c = [], []
            nv, nc = [], []
            for seed in range(8):
                lv = self.line(style=style, part='verse', seed=seed, kick='x.....x.x.......')
                lc = self.line(style=style, part='chorus', seed=seed, kick='x.....x.x.......')
                v += [n.vel for n in lv.clip if art.articulation_of(n) != 'mute']
                c += [n.vel for n in lc.clip if art.articulation_of(n) != 'mute']
                nv.append(len(lv.clip))
                nc.append(len(lc.clip))
            self.assertGreater(statistics.mean(c), statistics.mean(v) + 6, style)
            self.assertGreaterEqual(statistics.mean(nc), statistics.mean(nv), style)

    def test_note_lengths_per_style(self):
        funk = self.line(style='funk', part='verse', seed=1, timing=False)
        short = [n for n in funk.clip if art.articulation_of(n) != 'mute' and n.dur <= 0.5]
        self.assertTrue(short and all(art.articulation_of(n) in ('staccato', None) for n in short))
        self.assertGreater(sum(art.articulation_of(n) == 'staccato' for n in short), len(short) // 2)
        ballad = self.line(style='ballad', part='verse', seed=1, timing=False, flash={})
        ns = sorted(ballad.clip, key=lambda n: n.start)
        ratios = [n.dur / (b.start - n.start) for n, b in zip(ns, ns[1:]) if b.start - n.start >= 1.0]
        self.assertGreater(statistics.mean(ratios), 0.9)                                 # legato
        rock_v = self.line(style='rock', part='verse', seed=5, timing=False, cells={'eighths': 1.0})
        self.assertTrue(any(art.articulation_of(n) == 'staccato' for n in rock_v.clip))  # a verse chugs
        rock_c = self.line(style='rock', part='chorus', seed=5, timing=False, cells={'eighths': 1.0}, flash={})
        self.assertFalse(any(art.articulation_of(n) == 'staccato' for n in rock_c.clip))  # the chorus sustains

    def test_timing_within_human_bounds(self):
        def offsets(line):
            out = []
            for n in plain_onsets(line.clip):
                g = round(n.start * 12) / 12            # 16ths and triplets
                out.append((n.start - g) * 60000 / BPM)
            return out
        for style, lo, hi in (('rock', -8, 8), ('funk', -8, 4), ('reggae', 5, 25), ('ballad', 0, 18),
                              ('motown', -3, 12), ('walking', -12, 6)):
            offs = []
            for seed in range(6):
                offs += offsets(self.line(style=style, seed=seed))
            self.assertTrue(all(lo - 0.5 <= o <= hi + 0.5 for o in offs if o > -30), (style, min(offs), max(offs)))
        reggae = statistics.mean(o for s in range(4) for o in offsets(self.line(style='reggae', seed=s)))
        funk = statistics.mean(o for s in range(4) for o in offsets(self.line(style='funk', seed=s)))
        self.assertGreater(reggae, 8)                   # laid back
        self.assertLess(funk, 1)                        # on top
        grid = self.line(style='rock', seed=1, timing=False)
        self.assertTrue(all(abs(n.start * 4 - round(n.start * 4)) < 1e-6 for n in plain_onsets(grid.clip)))

    def test_budgets_over_many_seeds(self):
        bpb = 4
        for style in bassist.STYLES:
            S = bassist.STYLES[style]
            fle, fe = S['flash_every'], S['fill_every']
            for seed in range(20):
                line = bassist.arrange(PROG * 2, bpm=BPM, key=KEY, style=style, part='chorus', seed=seed,
                                       density=1.0, kick='x.....x...x..x..')
                fl = line.budget['flash']
                for (a, ka), (b, kb) in zip(fl, fl[1:]):
                    self.assertGreaterEqual(b - a, fle * bpb - 1e-6, (style, seed, fl))
                for i, (a, ka) in enumerate(fl):
                    for b, kb in fl[i + 1:]:
                        if ka == kb:
                            self.assertGreaterEqual(b - a, 2 * fle * bpb - 1e-6, (style, seed, fl))
                fi = line.budget['fills']
                for (a, _), (b, _) in zip(fi, fi[1:]):
                    self.assertGreaterEqual(b - a, fe * bpb - 1e-6, (style, seed, fi))
                self.assertLessEqual(len(fl), 16 // fle + 1)
                self.assertEqual(len(line.flashy), len(fl), (style, seed))

    def test_flash_is_spice_not_habit(self):
        n = 0
        bars = 0
        for seed in range(30):
            line = self.line(style='pop', density=0.5, seed=seed)
            n += len(line.flashy)
            bars += 8
        self.assertLess(n / bars, 0.25)                                   # well under one per 4 bars on average

    def test_fill_into_the_next_section(self):
        got = 0
        for seed in range(12):
            line = self.line(seed=seed, density=0.8, into='A')
            f = [x for x in line.fills if x[1] >= 32 - 1e-6]
            if f:
                got += 1
                ns = sorted((n for n in line.clip if n.start >= f[0][0] - 0.02), key=lambda n: n.start)
                self.assertTrue(ns)
                self.assertLessEqual(abs(ns[-1].pitch - note('A1')), 7)   # heads for A
        self.assertGreaterEqual(got, 6)
        none = [len([x for x in self.line(seed=s, section_end=False).fills if x[1] >= 32 - 1e-6]) for s in range(6)]
        self.assertEqual(sum(none), 0)

    def test_memory_counts_song_wide(self):
        mem = bassist.Memory()
        a = bassist.arrange(PROG, bpm=BPM, key=KEY, style='funk', part='verse', seed=1, density=1.0, memory=mem, at=0)
        b = bassist.arrange(PROG, bpm=BPM, key=KEY, style='funk', part='chorus', seed=2, density=1.0, memory=mem, at=32)
        self.assertEqual(mem.clock, 64)
        fl = sorted(mem.flash)
        for (x, _), (y, _) in zip(fl, fl[1:]):
            self.assertGreaterEqual(y - x, bassist.STYLES['funk']['flash_every'] * 4 - 1e-6)
        fi = sorted(mem.fills)
        for (x, _), (y, _) in zip(fi, fi[1:]):
            self.assertGreaterEqual(y - x, bassist.STYLES['funk']['fill_every'] * 4 - 1e-6)
        self.assertEqual(len(a.budget['flash']) + len(b.budget['flash']), len(fl))
        mem.played(40, 'slide')
        self.assertIn((40.0, 'slide'), mem.flash)
        with self.assertRaises(ComposeError):
            mem.played(40, 'trill')

    def test_approaches_and_passing_tones(self):
        n = 0
        for seed in range(10):
            line = self.line(style='motown', seed=seed, density=1.0, timing=False, flash={}, fills={})
            for st, _, ch in list(PROG)[1:]:
                before = [x for x in line.clip if st - 0.6 < x.start < st - 1e-6 and art.articulation_of(x) != 'mute']
                if before and before[-1].pitch % 12 != ch.bass_pc and abs(before[-1].pitch - Chord.parse(ch.symbol)
                                                                             .bass_note('E1')) <= 7:
                    n += 1
        self.assertGreater(n, 20)
        self.assertTrue(any(m[2] == 'approach' for m in self.line(style='motown', seed=1, density=1.0).moves))

    def test_pedal_and_ending(self):
        line = self.line(style='rock', pedal='E1', seed=2, timing=False, fills={}, flash={}, approach=0.0,
                         section_end=False)
        self.assertEqual({n.pitch for n in line.clip if art.articulation_of(n) != 'mute'} - {28, 40}, set())
        ring = self.line(style='rock', ending='ring', seed=2, timing=False)
        last = [n for n in ring.clip if n.start >= 28 - 1e-6]
        self.assertEqual(len(last), 1)
        self.assertGreater(last[0].dur, 3.5)
        self.assertEqual(last[0].pitch % 12, PROG.at(28).bass_pc)
        slide_end = self.line(style='rock', ending='slide', seed=2, timing=False)
        tail = sorted((n for n in slide_end.clip if n.start >= 28 - 1e-6), key=lambda n: n.start)
        self.assertEqual(len(tail), 2)
        self.assertTrue(art.glide_of(tail[1]))

    def test_tumbao_anticipates(self):
        line = bassist.arrange('C F G C', bpm=BPM, key='C major', style='tumbao', seed=1, timing=False, fills={},
                               flash={})
        ons = {round(n.start, 3): n for n in line.clip}
        for bar in range(3):
            self.assertIn(bar * 4 + 1.5, ons)                                # the & of 2: the 5th
            self.assertIn(bar * 4 + 3.0, ons)                                # beat 4: the next chord, anticipated
            nxt = Progression('C F G C').at((bar + 1) * 4)
            self.assertEqual(ons[bar * 4 + 3.0].pitch % 12, nxt.bass_pc)
        for bar in (1, 2, 3):
            self.assertNotIn(float(bar * 4), ons)                            # no new attack on the one

    def test_walking_style(self):
        line = bassist.arrange('Dm7 G7 Cmaj7 A7b9', bpm=160, key='C major', style='walking', part='solo', seed=3,
                               timing=False, fills={}, flash={})
        beats = sorted({round(n.start) for n in line.clip if art.articulation_of(n) != 'mute'})
        self.assertEqual(beats, list(range(16)))
        two = bassist.arrange('Dm7 G7 Cmaj7 A7b9', bpm=160, key='C major', style='walking', part='intro', seed=3)
        self.assertIn('groove:walk_two', two.summary())

    def test_errors(self):
        with self.assertRaises(ComposeError):
            bassist.arrange(PROG, bpm=BPM, style='metal')
        with self.assertRaises(ComposeError):
            bassist.arrange(PROG, bpm=BPM, part='middle8')
        with self.assertRaises(ComposeError):
            bassist.arrange(PROG, bpm=BPM, fills={'solo': 1})
        with self.assertRaises(ComposeError):
            bassist.arrange(PROG, bpm=BPM, flash={'trill': 1})
        with self.assertRaises(ComposeError):
            bassist.arrange(PROG, bpm=BPM, cells={'nope': 1})
        with self.assertRaises(ComposeError):
            bassist.arrange(PROG, bpm=BPM, cells={'kick': 1})               # needs kick=
        with self.assertRaises(ComposeError):
            bassist.arrange(PROG, bpm=BPM, kick='x..y')
        with self.assertRaises(ComposeError):
            bassist.arrange(PROG, bpm=BPM, memory=[])
        with self.assertRaises(ComposeError):
            bassist.arrange(PROG, bpm=BPM, ending='fade')


def played(clip):
    return sorted((n for n in clip if art.articulation_of(n) != 'mute'), key=lambda n: n.start)


class TestReviewed(unittest.TestCase):
    """Rules found broken in review: each test fails on the code before the fix."""

    def test_approach_notes_lead_into_the_next_note(self):
        # an approach note logged in .moves is played and sits a step (chromatic / diatonic) or a 4th / 5th
        # (fifth) from the note it leads into - not the old root left in place
        n = 0
        for style in ('rock', 'pop', 'country', 'motown', 'disco', 'ballad', 'synth', 'funk'):
            for seed in range(10):
                line = bassist.arrange(PROG, bpm=BPM, key=KEY, style=style, part='chorus', seed=seed, density=1.0,
                                       timing=False, flash={}, fills={})
                ns = played(line.clip)
                for a0, _, kind, name in line.moves:
                    if kind != 'approach':
                        continue
                    at = [x for x in ns if abs(x.start - a0) < 1e-6]
                    self.assertTrue(at, (style, seed, a0))
                    nxt = next((x for x in ns if x.start > a0 + 1e-6), None)
                    if nxt is None:
                        continue
                    d = abs(nxt.pitch - at[0].pitch)
                    self.assertTrue(0 < d <= (2 if name in ('chromatic', 'diatonic') else 7),
                                    (style, seed, a0, name, at[0].pitch, nxt.pitch))
                    n += 1
        self.assertGreater(n, 100)

    def test_the_log_matches_what_is_played(self):
        # approaches / dead notes a fill, a walk-up, an ending or the tempo guard replaced leave the log too
        for style in bassist.STYLES:
            for seed in range(6):
                for bpm in (96, 200):
                    line = bassist.arrange(PROG, bpm=bpm, key=KEY, style=style, part='chorus', seed=seed,
                                           density=1.0, timing=False, kick='x.....x...x..x..',
                                           ending='ring' if seed % 3 == 2 else None)
                    starts = [x.start for x in line.clip]
                    for a0, a1, kind, name in line.moves:
                        if kind in ('approach', 'ghost'):
                            self.assertTrue(any(abs(a0 - s) < 1e-6 for s in starts), (style, seed, bpm, kind, a0))
                        if kind == 'fill':
                            self.assertTrue(any(a0 - 1e-6 <= s < a1 for s in starts), (style, seed, bpm, a0))
                    fl = [(round(a, 4), k) for a, _, k in line.fills]
                    self.assertEqual(fl, line.budget['fills'], (style, seed, bpm))
                    if seed % 3 == 2:                                  # the ending owns the last bar
                        self.assertFalse([f for f in line.fills if f[1] > 28 + 1e-6], (style, seed))

    def test_short_fills_step_into_the_target(self):
        # a pentatonic lick / a triplet arpeggio lands on the target by step - no octave leap at the end
        for kind in ('pentatonic', 'triplet'):
            for dur in (1.0, 2.0):
                for tgt in ('E1', 'G1', 'A1', 'D2', 'E2', 'A2', 'D3'):
                    for ch in ('Em7', 'A7', 'C', 'B7#9'):
                        c = sorted(bassist.fill(kind, tgt, dur, BPM, chord=ch, at=2.0), key=lambda x: x.start)
                        ps = [x.pitch for x in c]
                        self.assertLessEqual(abs(ps[-1] - note(tgt)), 3, (kind, dur, tgt, ch, ps))
                        self.assertTrue(all(abs(b - a) <= 7 for a, b in zip(ps, ps[1:])), (kind, dur, tgt, ch, ps))

    def test_one_gesture_at_a_time(self):
        # a flashy move never shares a bar with a fill (the bar before it, the fill, the bar it lands in)
        for style in ('rock', 'pop', 'funk', 'motown', 'country', 'ballad', 'disco'):
            for seed in range(12):
                line = bassist.arrange(PROG * 2, bpm=BPM, key=KEY, style=style, part='chorus', seed=seed,
                                       density=1.0, kick='x.....x...x..x..')
                for f0, _, _ in line.fills:
                    for m0, _, name in line.flashy:
                        self.assertFalse(-4 < m0 - f0 < 6, (style, seed, f0, m0, name))

    def test_fast_tempos(self):
        # playable at punk / salsa tempos: no unreachable jump, no 16th run the plucking hand can't play
        def plucks(line):
            ns = sorted(line.clip, key=lambda x: x.start)
            out = []
            for i, x in enumerate(ns):
                prev = ns[i - 1] if i else None
                if art.glide_of(x) or (prev is not None and prev.start + prev.dur > x.start + 0.02 and
                                       x.vel < prev.vel):
                    continue                                          # glided / hammered: not plucked
                out.append(x.start)
            return out
        for style in bassist.STYLES:
            for i in range(12):
                bpm = (170, 185, 210)[i % 3]
                pr = PROGS[i % len(PROGS)]
                line = bassist.arrange(pr + ' ' + pr, bpm=bpm, style=style, part=('chorus', 'drop')[i % 2],
                                       seed=i, kick=KICKS[i % len(KICKS)], density=1.0, timing=False)
                self.assertEqual(line.problems, [], (style, i, bpm))
                if style == 'synth':
                    continue
                ps = plucks(line)
                runs3 = [a for a, c in zip(ps, ps[2:]) if c - a < 0.5 + 0.03]
                self.assertEqual(runs3, [], (style, i, bpm))
                if bpm > bassist.FAST[2]:
                    runs2 = [a for a, b in zip(ps, ps[1:]) if b - a < 0.25 + 0.03]
                    self.assertEqual(runs2, [], (style, i, bpm))
        # the same line at a moderate tempo keeps its 16th figures
        funk = [bassist.arrange(PROG, bpm=100, key=KEY, style='funk', part='chorus', seed=s, timing=False)
                for s in range(4)]
        self.assertTrue(any(len([a for a, c in zip(plucks(f), plucks(f)[2:]) if c - a < 0.53]) for f in funk))

    def test_fast_octave_shapes_are_refingered(self):
        # 160 bpm disco octaves: a jump from D3 down to F1 in a 16th can't be fingered - the line re-fingers it
        for seed in range(6):
            for kick in KICKS:
                line = bassist.arrange('Am7 D7 Gmaj7 Cmaj7 Am7 D7 Gmaj7 Cmaj7', bpm=160, style='disco',
                                       part='chorus', seed=seed, kick=kick, density=0.0)
                self.assertEqual(line.problems, [], (seed, kick))

    def test_swing_follows_the_drummer(self):
        from agentsound.patterns import drums
        beat = drums({'kick': 'x.....x...x..x..', 'snare': '....x.......x...', 'hat': 'xxxxxxxxxxxxxxxx'}).swing(0.56)
        line = bassist.arrange(PROG, bpm=100, key=KEY, style='funk', part='chorus', kick=beat, seed=3, timing=False,
                               fills={}, flash={}, lock=1.0, interlock=False)
        self.assertAlmostEqual(line.swing, 0.56, places=3)
        offs = {round((n.start % 0.5) - 0.25, 4) for n in line.clip if 0.2 < n.start % 0.5 < 0.35}
        self.assertEqual(offs, {0.03})                                 # the e / a of each beat 0.03 beats late
        self.assertGreaterEqual(line.locked, 0.9)                      # locked on the kick's grid, swung or not
        straight = bassist.arrange(PROG, bpm=100, key=KEY, style='funk', part='chorus', kick=beat, seed=3,
                                   timing=False, fills={}, flash={}, swing=0.5)
        self.assertIsNone(straight.swing)
        self.assertTrue(all(abs(n.start * 4 - round(n.start * 4)) < 1e-6 for n in plain_onsets(straight.clip)))
        pct = bassist.arrange(PROG, bpm=100, key=KEY, style='pop', seed=3, swing=58)
        self.assertAlmostEqual(pct.swing, 0.58)
        with self.assertRaises(ComposeError):
            bassist.arrange(PROG, bpm=100, key=KEY, style='pop', swing=0.9)
        # a slide's pluck and glide stay a pair through the swing
        for seed in range(10):
            ln = bassist.arrange(PROG, bpm=100, key=KEY, style='pop', seed=seed, swing=0.6, density=1.0,
                                 flash={'slide': 1.0, 'hammer_on': 1.0}, timing=False)
            self.assertEqual(ln.problems, [], seed)

    def test_funk_dead_notes_leave_the_later_kicks(self):
        kick = 'x.....x...x..x..'
        ks = {0.0, 1.5, 2.5, 3.25}
        for seed in range(10):
            line = self.line_funk(kick, seed)
            dead = [n.start % 4 for n in line.clip if art.articulation_of(n) == 'mute']
            self.assertFalse([t for t in dead if round(t, 3) in ks - {0.0}], (seed, dead))

    def line_funk(self, kick, seed):
        return bassist.arrange(PROG, bpm=BPM, key=KEY, style='funk', part='verse', seed=seed, kick=kick,
                               timing=False, flash={}, fills={}, section_end=False)

    def test_tumbao_fills_land_on_the_anticipation(self):
        n = 0
        for seed in range(12):
            line = bassist.arrange('Am D7 G C Am D7 G E7', bpm=180, key='A minor', style='tumbao', part='chorus',
                                   seed=seed, density=1.0, timing=False, flash={})
            for f0, f1, _ in line.fills:
                n += 1
                self.assertAlmostEqual(f1 % 4, 3.0, msg=(seed, f0, f1))          # lands on the 4
                land = [x for x in line.clip if abs(x.start - f1) < 1e-6]
                self.assertTrue(land, (seed, f1))
                nxt = Progression('Am D7 G C Am D7 G E7').at(f1 + 1) if f1 + 1 < 32 else Chord.parse('Am')
                self.assertEqual(land[0].pitch % 12, nxt.bass_pc, (seed, f1))
                self.assertFalse([x for x in line.clip if abs(x.start - (f1 + 1)) < 1e-6], (seed, f1))
        self.assertGreater(n, 3)

    def test_motown_sings_the_sixth_on_major_chords(self):
        # Jamerson's 1-3-5-6: no blues b7 over a plain major triad
        prog = Progression('C Am F G C Am F G', key='C major')
        for seed in range(12):
            line = bassist.arrange(prog, bpm=104, key='C major', style='motown', part='chorus', seed=seed,
                                   timing=False, fills={}, flash={}, approach=0.0)
            bb = [n for n in played(line.clip) if n.pitch % 12 == 10 and prog.at(n.start).symbol == 'C'
                  and n.start % 4 < 3.0]                         # (a chromatic approach on the & of 4 may be Bb)
            self.assertEqual(bb, [], seed)


class TestPlace(unittest.TestCase):
    def slide_line(self):
        c = Clip._raw(list(bassist.slide('A1', 1.0, BPM, at=1.0)) + [art.note(0, 0.5, 'E1', 90, 'staccato'),
                                                                    art.note(2.2, 0.1, 'E1', 30, 'mute')], 4)
        return bassist.BassLine(c, [], {}, BPM, None, [])

    def test_bends_on_a_polyphonic_sampler(self):
        clip, pts = self.slide_line().adapted(fake_track('sf2'))
        ns = sorted(clip, key=lambda n: n.start)
        self.assertEqual(len(ns), 3)                                         # the glide merged into its pluck
        self.assertFalse(any(art.glide_of(n) for n in ns))
        pluck = [n for n in ns if abs(n.start - 1.0) < 1e-9][0]
        self.assertEqual(pluck.pitch, note('G1'))
        self.assertAlmostEqual(pluck.start + pluck.dur, 2.0, places=6)
        self.assertEqual(max(p[1] for p in pts), 2.0)                        # bent up a whole step
        self.assertEqual(pts[-1][1], 0.0)                                    # and back before the next pluck
        self.assertLessEqual(pts[-1][0], 2.2)
        self.assertTrue(all(b[0] > a[0] for a, b in zip(pts, pts[1:])))
        # no keyswitches on an sf2: the marks go
        self.assertFalse(any(art.articulation_of(n) for n in ns))

    def test_glides_on_a_legato_sampler(self):
        clip, pts = self.slide_line().adapted(fake_track('sampler', mono='legato'))
        self.assertEqual(pts, [])
        self.assertTrue(any(art.glide_of(n) for n in clip))

    def test_no_bend_instrument_drops_the_slide(self):
        clip, pts = self.slide_line().adapted(fake_track('va'))
        self.assertEqual(pts, [])
        self.assertIn(note('A1'), [n.pitch for n in clip])
        self.assertNotIn(note('G1'), [n.pitch for n in clip])

    def test_place_compiles(self):
        s = Song('t', tempo=BPM, key='E minor')
        verse = s.section('verse', bars=8)
        t = s.track('bass', patches.inst.sf2('Finger Bass'))
        line = None
        for seed in range(12):
            line = bassist.arrange(PROG, bpm=BPM, key=KEY, style='pop', part='chorus', seed=seed, density=1.0,
                                   flash={'slide': 1.0})
            if any(m[3] == 'slide' for m in line.moves):
                break
        self.assertTrue(any(m[3] == 'slide' for m in line.moves))
        line.place(t, verse)
        d = s.compile()
        tr = next(x for x in d['tracks'] if x['id'] == 'bass')
        self.assertEqual(len(tr['notes']), len(line.adapted(t)[0]))
        self.assertTrue(any(a['target'] == 'instrument.pitchbend' for a in tr['automation']))

    def test_articulations_map_to_the_patch(self):
        if not (library.SAMPLES / 'karoryfer-black-and-blue-basses' / 'SOURCE.json').is_file():
            self.skipTest('karoryfer-black-and-blue-basses not installed')
        s = Song('t', tempo=BPM, key='E minor')
        verse = s.section('verse', bars=8)
        t = s.track('bass', 'sampled/picked_bass')                          # pluck / staccato / ghost / btb
        line = bassist.arrange(PROG, bpm=BPM, key=KEY, style='funk', part='verse', seed=1)
        clip, _ = line.adapted(t)
        arts = {art.articulation_of(n) for n in clip}
        self.assertIn('ghost', arts)                                          # 'mute' -> the patch's ghost
        self.assertIn('staccato', arts)
        line.place(t, verse)
        s.compile()


if __name__ == '__main__':
    unittest.main()
