"""The guitarist (agentsound/guitarist.py): the fretboard model (playable shapes, voice leading, capo), the strumming
/ picking engine (stroke order and spread, dead strums, palm mutes), the moves, the rhythm arranger (section
awareness, fills, ornaments, anticipations, takes) and the lead arranger (picking vs slurs, bends, vibrato), the
budgets over many seeds, determinism, shaped velocities and human timing bounds."""
import pathlib
import statistics
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Clip, Song, guitarist as g  # noqa: E402
from agentsound.patches import inst  # noqa: E402

from agentsound.theory import Chord, ComposeError, Key, note  # noqa: E402

BPM = 120
PROG = 'C Am F G'
FB = g.Fretboard()
SEEDS = range(40)


def groups(clip, window=0.1):
    """Notes that start together (one stroke), in time order."""
    out = []
    for n in sorted(clip, key=lambda n: (n.start, n.pitch)):
        if out and n.start - out[-1][0].start < window:
            out[-1].append(n)
        else:
            out.append([n])
    return out


def ms(beats, bpm=BPM):
    return beats * 60000.0 / bpm


def spread(vels):
    v = sorted(vels)
    return v[int(len(v) * 0.9) - 1] - v[int(len(v) * 0.1)]


def line(spec, key='E minor', vel=96):
    return Key(key).motif(spec).clip(octave=4, vel=vel)


V_LINE = '5:1 5:0.5 6:0.5 5:1 3:1 | 2:1 3:0.5 2:0.5 1:2 | 5:1 5:0.5 6:0.5 8:1 7:1 | 5:3 r:1'
C_LINE = '8:1.5 7:0.5 8:1 10:1 | 9:2 8:1 7:1 | 5:1.5 6:0.5 7:1 8:1 | 8:3 r:1'


class TestFretboard(unittest.TestCase):
    def test_tunings_capo_positions(self):
        self.assertEqual(FB.open, (40, 45, 50, 55, 59, 64))
        self.assertEqual(g.Fretboard('drop_d').open[0], 38)
        self.assertEqual(g.Fretboard(capo=2).open, (42, 47, 52, 57, 61, 66))
        self.assertIn((5, 5), FB.positions('A4'))
        self.assertIn((4, 10), FB.positions('A4'))
        with self.assertRaises(ComposeError):
            g.Fretboard('banjo')

    def test_fingers_and_barres(self):
        self.assertEqual(FB.fingers((1, 3, 3, 2, 1, 1)), 4)             # F barre: index across fret 1
        self.assertEqual(FB.fingers((None, 3, 2, 0, 1, 0)), 3)          # open C
        self.assertTrue(FB.playable((1, 3, 3, 2, 1, 1)))
        self.assertFalse(FB.playable((1, 5, 6, 2, None, None)))         # beyond one hand's reach
        self.assertFalse(FB.playable((1, 2, 3, 4, 2, None)))            # five fingers

    def test_classic_open_chords(self):
        want = {'C': 'x32010', 'G': '320003', 'D': 'xx0232', 'Am': 'x02210', 'Em': '022000', 'E': '022100',
                'A': 'x02220', 'Dm': 'xx0231', 'C/E': '032010'}
        for c, d in want.items():
            self.assertEqual(g.shape(c).diagram(), d, c)
        self.assertEqual(g.shape('F').diagram(), '133211')

    def test_every_shape_is_playable_and_spells_the_chord(self):
        for c in ('C', 'G', 'D', 'Am', 'Em', 'F', 'Bb', 'Bm', 'F#m', 'E7', 'G7', 'Cmaj7', 'Am7', 'Dsus4', 'Cadd9',
                  'Eb', 'Ab', 'C#m', 'D/F#', 'B7'):
            ch = Chord.parse(c)
            pcs = {(ch.root + i) % 12 for i in ch.intervals} | {ch.bass_pc}
            for kind in g.KINDS:
                for sh in g.shapes(c, kind)[:8]:
                    self.assertTrue(FB.playable(sh.frets), (c, kind, sh))
                    self.assertEqual(len(sh.frets), 6)
                    for s, (f, p) in enumerate(zip(sh.frets, sh.pitches)):
                        self.assertEqual(f is None, p is None)
                        if f is not None:
                            self.assertEqual(p, FB.open[s] + f)
                    self.assertTrue({p % 12 for p in sh.notes} <= pcs, (c, kind, sh))
                    if kind in ('open', 'barre', 'full', 'shell', 'power'):
                        self.assertEqual(sh.notes[0] % 12, ch.bass_pc if kind != 'power' else ch.root,
                                         (c, kind, sh))
                    if kind == 'power':
                        self.assertEqual(sh.notes[1] - sh.notes[0], 7)
                    if kind in ('open', 'barre', 'full'):
                        self.assertGreaterEqual(len(sh.notes), 4)
                        ss = sh.strings
                        self.assertEqual(ss, list(range(ss[0], ss[-1] + 1)), sh)      # strummable: no gaps
                    if kind == 'barre':
                        self.assertEqual(sh.open_strings, 0)

    def test_voice_lead_keeps_the_hand_close(self):
        path = g.voice_lead(['C', 'Am', 'F', 'G'], 'open')
        self.assertEqual([s.diagram() for s in path], ['x32010', 'x02210', '133211', '320003'])
        up = g.voice_lead(['C', 'Am', 'F', 'G'], 'upper')
        pos = [s.pos for s in up]
        self.assertLessEqual(max(pos) - min(pos), 5)

    def test_capo(self):
        self.assertEqual(g.best_capo(['Bb', 'Eb', 'F', 'Gm']), 3)            # G C D Em shapes
        sh = g.shape('Bb', fretboard=g.Fretboard(capo=3))
        self.assertEqual(sh.diagram(), '320003')                           # a G shape at capo 3 sounds Bb
        self.assertEqual(sh.notes[0], note('Bb2'))


class TestMoves(unittest.TestCase):
    def test_downstroke_low_to_high_and_upstroke_lighter(self):
        d = sorted(g.strum('G', 2, BPM, spread_ms=30, seed=1), key=lambda n: n.start)
        self.assertEqual([n.pitch for n in d], sorted(n.pitch for n in d))
        self.assertTrue(10 <= ms(d[-1].start - d[0].start) <= 40)
        u = sorted(g.strum('G', 2, BPM, direction='up', strings='top4', spread_ms=30, seed=1), key=lambda n: n.start)
        self.assertEqual(len(u), 4)
        self.assertEqual([n.pitch for n in u], sorted((n.pitch for n in u), reverse=True))
        self.assertGreater(u[0].vel, u[-1].vel)                            # the top string rings, the rest fade
        self.assertLess(ms(u[-1].start - u[0].start), ms(d[-1].start - d[0].start))

    def test_chuck_is_short(self):
        c = g.chuck('C', BPM)
        self.assertTrue(all(ms(n.dur) <= 60 for n in c))
        c2 = g.chuck('C', BPM, dead='dead note')
        self.assertTrue(all(getattr(n, 'art', None) == 'dead note' for n in c2))

    def test_hammer_chord_and_sus4(self):
        c = sorted(g.hammer_chord('C', 2, BPM), key=lambda n: n.start)
        self.assertIn(note('D3'), [n.pitch for n in c[:5]])                # the open D string first ...
        last = c[-1]
        self.assertEqual((last.pitch, round(last.start, 3)), (note('E3'), 0.5))   # ... then E hammered on
        self.assertLess(last.vel, max(n.vel for n in c[:5]))
        s4 = sorted(g.hammer_chord('D', 2, BPM, sus=4), key=lambda n: n.start)
        self.assertIn(note('G4'), [n.pitch for n in s4[:4]])
        self.assertEqual(s4[-1].pitch, note('F#4'))

    def test_slide_chord_lands_on_time(self):
        c = g.slide_chord('A', 1, BPM, frm=-2, ms=100)
        firsts = sorted({n.pitch for n in c if n.start < 0.01})
        self.assertEqual(firsts, [note('G2'), note('D3'), note('G3')][:len(firsts)])
        land = min(n.start for n in c if n.pitch == note('A2'))
        self.assertAlmostEqual(ms(land), 100, delta=5)

    def test_bass_run_walks_into_the_next_chord(self):
        c = sorted(g.bass_run('G', 'C', 1, BPM, key='C major'), key=lambda n: n.start)
        self.assertEqual([n.pitch for n in c], [note('G2'), note('A2'), note('B2')])
        self.assertLessEqual(max(n.start + n.dur for n in c), 1.0 + 1e-6)

    def test_patterns_parse_and_reject(self):
        for name in g.PATTERNS:
            grid, toks = g._pattern(name)
            self.assertGreater(len(toks), 0)
        with self.assertRaises(ComposeError):
            g.strum_pattern(PROG, BPM, pattern='D . Z u')

    def test_bend_lick(self):
        b = g.bend('A4', 2, BPM, amount=2)
        self.assertEqual([n.pitch for n in b], [note('G4')])               # fretted a whole step lower
        pb = b.auto['instrument.pitchbend']
        self.assertEqual(max(p[1] for p in pb), 2)
        self.assertEqual(pb[-1][1], 0.0)
        self.assertGreaterEqual(pb[-1][0], 2.0)                            # back to 0 once the note is over
        self.assertIn('instrument.vibrato', b.auto)
        s = Song('t', tempo=BPM)
        t = s.track('lead', inst.va())
        b.play(t, 4.0)
        self.assertEqual([n.start for n in t.notes], [4.0])
        self.assertTrue(any(tg == 'instrument.pitchbend' for tg, _ in t._auto))
        self.assertFalse(any(tg == 'instrument.vibrato' for tg, _ in t._auto))   # vibrato needs a sampler

    def test_prebend_is_silent_before_the_pick(self):
        b = g.prebend('A4', 1, BPM, amount=2, release=0.5)
        pb = b.auto['instrument.pitchbend']
        self.assertLess(pb[1][0], 0.0)
        self.assertEqual(pb[1][1], 2)
        self.assertEqual(pb[-1][1], 0.0)

    def test_trill_is_light_and_in_real_time(self):
        c = sorted(g.trill('A4', 2, BPM, rate=11, key='A minor', wobble_ms=0), key=lambda n: n.start)
        self.assertEqual({n.pitch for n in c}, {note('A4'), note('B4')})
        gaps = [b.start - a.start for a, b in zip(c, c[1:-1])]
        for gp in gaps:
            self.assertAlmostEqual(1000.0 / ms(gp), 11.0, delta=0.5)
        self.assertTrue(all(n.vel < c[0].vel for n in c[1:]))

    def test_rake_lick_double_stop_tremolo(self):
        r = sorted(g.rake('A4', 1, BPM, strings=3), key=lambda n: n.start)
        self.assertEqual(r[-1].pitch, note('A4'))
        self.assertTrue(all(n.vel < r[-1].vel and n.dur < 0.05 for n in r[:-1]))
        lk = sorted(g.lick('Am', 1.5, BPM), key=lambda n: n.start)
        self.assertIn(lk[-1].pitch % 12, {9, 0, 4})
        self.assertLessEqual(max(n.start + n.dur for n in lk), 1.5 + 1e-6)
        ds = sorted(g.double_stop('E5', 1, BPM, chord='C'), key=lambda n: n.pitch)
        self.assertEqual([n.pitch for n in ds], [note('C5'), note('E5')])
        tp = g.tremolo_pick('E5', 1, BPM, rate=12)
        self.assertEqual(len(tp), 6)

    def test_moves_registry(self):
        for name, fn in g.MOVES.items():
            self.assertTrue(callable(fn), name)
            self.assertTrue(fn.__doc__, name)


class TestArrange(unittest.TestCase):
    def test_deterministic_and_seeded(self):
        a = g.arrange(PROG, bpm=BPM, style='pop', section='chorus', seed=4, length=16)
        b = g.arrange(PROG, bpm=BPM, style='pop', section='chorus', seed=4, length=16)
        c = g.arrange(PROG, bpm=BPM, style='pop', section='chorus', seed=5, length=16)
        self.assertEqual(a.clip, b.clip)
        self.assertNotEqual(a.clip, c.clip)

    def test_take_is_the_same_part_played_again(self):
        a = g.arrange(PROG, bpm=BPM, style='rock', section='chorus', seed=4, length=16)
        t2 = a.take(2)
        self.assertEqual([s for _, s in a.shapes], [s for _, s in t2.shapes])
        self.assertNotEqual([n.start for n in a.clip], [n.start for n in t2.clip])
        self.assertEqual(len(groups(a.clip)), len(groups(t2.clip)))
        self.assertEqual(sorted({n.pitch for n in a.clip}), sorted({n.pitch for n in t2.clip}))

    def test_playable_everywhere(self):
        for style in g.STYLES:
            for sec in ('intro', 'verse', 'chorus', 'outro'):
                a = g.arrange(PROG, bpm=BPM, style=style, section=sec, seed=7, length=16, next_chord='C')
                for _, sh in a.shapes:
                    self.assertTrue(FB.playable(sh.frets), (style, sec, sh))
                # never more than six strings at once, one pitch per string
                pts = sorted({round(n.start, 4) for n in a.clip})
                for t in pts:
                    sounding = [n for n in a.clip if n.start <= t + 1e-6 < n.start + n.dur]
                    self.assertLessEqual(len(sounding), 6, (style, sec, t))
                for n in a.clip:
                    self.assertTrue(FB.lowest <= n.pitch <= FB.highest, (style, sec, n))

    def test_strokes_are_strummed_and_timed_like_a_player(self):
        a = g.arrange(PROG, bpm=BPM, style='pop', section='chorus', seed=3, length=16, section_end=False,
                      anticipate=0.0, ornaments={}, open_change=0.0)
        for grp in groups(a.clip, window=0.03):
            if len(grp) < 3:
                continue
            ts = [n.start for n in grp]
            self.assertLessEqual(ms(max(ts) - min(ts)), 45.0)
            byt = [n.pitch for n in sorted(grp, key=lambda n: n.start)]
            self.assertTrue(byt == sorted(byt) or byt == sorted(byt, reverse=True), byt)   # down or up
            first = min(ts)
            grid = round(first * 2) / 2
            self.assertLessEqual(abs(ms(first - grid)), 25.0)              # within human bounds of the 8th grid

    def test_velocities_are_shaped(self):
        for style, sec in (('pop', 'chorus'), ('rock', 'verse'), ('folk', 'verse'), ('funk', 'verse'),
                           ('ballad', 'verse'), ('reggae', 'verse')):
            a = g.arrange(PROG, bpm=BPM, style=style, section=sec, seed=2, length=16)
            self.assertGreaterEqual(spread([n.vel for n in a.clip]), 14, (style, sec))
        a = g.arrange(PROG, bpm=BPM, style='pop', section='chorus', seed=2, length=16, anticipate=0.0,
                      section_end=False)
        downs = [n.vel for n in a.clip if abs(n.start % 4) < 0.03]
        ups = [n.vel for n in a.clip if abs((n.start - 1.5) % 4) < 0.03]
        self.assertGreater(statistics.mean(downs), statistics.mean(ups))

    def test_sections_shape_the_part(self):
        v = g.arrange(PROG, bpm=BPM, style='rock', section='verse', seed=1, length=16, section_end=False)
        c = g.arrange(PROG, bpm=BPM, style='rock', section='chorus', seed=1, length=16, section_end=False)
        self.assertEqual((v.technique, c.technique), ('chug', 'power'))
        self.assertGreater(statistics.mean(n.vel for n in c.clip), statistics.mean(n.vel for n in v.clip))
        self.assertLess(statistics.mean(n.dur for n in v.clip), statistics.mean(n.dur for n in c.clip))
        pv = g.arrange(PROG, bpm=BPM, style='pop', section='verse', seed=1, length=16)
        pc = g.arrange(PROG, bpm=BPM, style='pop', section='chorus', seed=1, length=16)
        self.assertEqual((pv.technique, pc.technique), ('muted8', 'strum'))
        f = g.arrange(PROG, bpm=BPM, style='folk', section='verse', seed=1, length=16)
        self.assertEqual(f.technique, 'travis')
        s = Song('t', tempo=BPM)
        ch = s.section('chorus 2', bars=4)
        a = g.arrange(PROG, bpm=BPM, style='pop', section=ch, seed=1)
        self.assertEqual((a.technique, a.clip.length), ('strum', 16.0))

    def test_articulations_from_the_sound_or_given(self):
        a = g.arrange(PROG, bpm=BPM, style='rock', section='verse', seed=1, length=8,
                      articulations={'palm': 'palm mute', 'dead': 'dead note'})
        arts = {getattr(n, 'art', None) for n in a.clip}
        self.assertIn('palm mute', arts)
        f = g.arrange(PROG, bpm=BPM, style='funk', section='verse', seed=1, length=8,
                      articulations={'dead': 'dead note'})
        self.assertIn('dead note', {getattr(n, 'art', None) for n in f.clip})
        e = g.arrange(PROG, bpm=BPM, style='funk', section='verse', seed=1, length=8)
        self.assertTrue(all(getattr(n, 'art', None) is None for n in e.clip))

    def test_fill_into_the_next_section(self):
        seen = set()
        for sd in SEEDS:
            a = g.arrange(PROG, bpm=BPM, style='folk', section='chorus', seed=sd, length=16, next_chord='C',
                          fill=1.0, density=1.0)
            fills = [m for m in a.moves if m[2] == 'fill']
            self.assertLessEqual(len(fills), 1)
            for m in fills:
                self.assertGreaterEqual(m[0], 16 - 4.0)
                seen.add(m[3])
        self.assertTrue(seen & {'bass_run', 'build'})
        a = g.arrange(PROG, bpm=BPM, style='folk', section='chorus', seed=1, length=16, section_end=False)
        self.assertEqual(a.count('fill'), 0)

    def test_fills_follow_the_form(self):
        up = [g.arrange(PROG, bpm=BPM, style='pop', section='verse', seed=sd, length=16, into='chorus',
                        next_chord='F').count('fill') for sd in SEEDS]
        down = [g.arrange(PROG, bpm=BPM, style='pop', section='chorus', seed=sd, length=16, into='outro',
                          next_chord='C') for sd in SEEDS]
        self.assertGreaterEqual(sum(up), 30)                               # into a bigger section: announce it
        self.assertLess(sum(a.count('fill') for a in down), sum(up))
        self.assertEqual(sum(a.count('fill', 'build') for a in down), 0)   # no build into a quieter section

    def test_anticipation_takes_the_next_chord(self):
        for sd in SEEDS:
            a = g.arrange(PROG, bpm=BPM, style='pop', section='chorus', seed=sd, length=16, anticipate=1.0,
                          section_end=False, ornaments={})
            pushes = [m for m in a.moves if m[2] == 'anticipation']
            if pushes:
                t, c = pushes[0][0], pushes[0][1]
                self.assertAlmostEqual(c - t, 0.5)
                sh = dict(a.shapes)
                self.assertIn(t, sh)
                return
        self.fail('no anticipation with anticipate=1')

    def test_rhythm_budgets_over_many_seeds(self):
        for style in ('folk', 'pop', 'country', 'rock'):
            every = g.STYLES[style]['spice_every']
            for sd in SEEDS:
                mem = g.Memory()
                for i, sec in enumerate(('verse', 'chorus', 'verse', 'chorus')):
                    g.arrange(PROG, bpm=BPM, style=style, section=sec, seed=sd * 7 + i, length=16, memory=mem,
                              density=1.0, next_chord='C')
                sp = sorted(t for t, c, _ in mem.events if c == 'spice')
                for a, b in zip(sp, sp[1:]):
                    self.assertGreaterEqual(b - a, every * 4 - 1e-6, (style, sd, sp))
                fl = sorted(t for t, c, _ in mem.events if c == 'flash')
                for a, b in zip(fl, fl[1:]):
                    self.assertGreaterEqual(b - a, g.STYLES[style]['fill_every'] * 4 - 1e-6, (style, sd, fl))
                self.assertEqual(mem.clock, 64.0)

    def test_strings_stop_when_the_grip_leaves_them(self):
        # E -> D: the open low E (and the open G / B strings the D grip frets) must not ring on under the D chord
        for prog in ('E D A E', 'Em D C D', 'G D Em C'):
            for style, sec in (('pop', 'chorus'), ('folk', 'verse'), ('ballad', 'verse'), ('country', 'verse')):
                for sd in range(6):
                    a = g.arrange(prog, bpm=100, style=style, section=sec, seed=sd, length=16, section_end=False,
                                  anticipate=0.0, ornaments={})
                    for n in a.clip:
                        for t, sh in a.shapes:
                            if n.start + 0.05 < t < n.start + n.dur - 0.05:
                                self.assertIn(n.pitch, sh.notes, (prog, style, sec, sd, n, sh))
        # a string that keeps its fret rings on through the change (C -> Am: the fretted E on the D string, the open
        # G, the C on the B string)
        hand = g._Hand(BPM)
        c, am = g.shape('C'), g.shape('Am')
        g._stroke(hand, c, 0.0, spread_ms=0)
        hand.change(2.0, c, am)
        ends = {p: t + d for t, d, p, _, _ in hand.notes()}
        self.assertGreater(ends[note('E3')], 3.0)
        self.assertGreater(ends[note('C4')], 3.0)
        self.assertLess(ends[note('C3')], 2.0)                             # the A string: fret 3 -> open

    def test_take_after_the_memory_moved_on(self):
        mem = g.Memory()
        g.arrange('Em C G D', bpm=BPM, style='pop', section='verse', seed=1, length=16, memory=mem, kind='upper')
        c = g.arrange('C G D Em', bpm=BPM, style='pop', section='chorus', seed=2, length=16, memory=mem,
                      kind='upper')
        g.arrange('F#m B', bpm=BPM, style='pop', section='bridge', seed=3, length=8, memory=mem, kind='upper')
        mem.shape = g.shape('B', 'upper', near=14)                         # the hand far up the neck now
        t2 = c.take(2)
        self.assertEqual([s for _, s in c.shapes], [s for _, s in t2.shapes])
        self.assertEqual(sorted(n.pitch for n in c.clip), sorted(n.pitch for n in t2.clip))

    def test_the_hand_has_a_speed_limit(self):
        # 16th strums at 184 BPM would be 12 chord strokes a second: played on the 8th grid instead
        a = g.arrange(PROG, bpm=184, style='indie', section='post', seed=1, length=16, section_end=False,
                      ornaments={}, anticipate=0.0, open_change=0.0)
        self.assertIn('8ths: tempo', [m for m in a.moves if m[2] == 'pattern'][0][3])
        onsets = [grp[0].start for grp in groups(a.clip, window=0.12) if len(grp) >= 3]
        gaps = [ms(y - x, 184) for x, y in zip(onsets, onsets[1:])]
        self.assertGreaterEqual(min(gaps), 90.0)
        slow = g.arrange(PROG, bpm=120, style='indie', section='post', seed=1, length=16, section_end=False)
        self.assertNotIn('tempo', [m for m in slow.moves if m[2] == 'pattern'][0][3])
        b = g.build('E', 2.0, 184)
        onsets = [grp[0].start for grp in groups(b, window=0.12)]
        self.assertGreaterEqual(min(ms(y - x, 184) for x, y in zip(onsets, onsets[1:])), 90.0)
        self.assertEqual(len(groups(g.build('E', 2.0, 120), window=0.08)), 8)   # 16ths where the hand can

    def test_hammered_note_is_heard_before_the_next_stroke(self):
        found = 0
        for sd in SEEDS:
            a = g.arrange('C G Am F', bpm=BPM, style='pop', section='chorus', seed=sd, length=16, technique='eighths',
                          ornaments={'hammer_chord': 1.0}, density=1.0, spice_every=1, section_end=False,
                          anticipate=0.0)
            for t, _, k, nm in a.moves:
                if k != 'ornament' or nm != 'hammer_chord':
                    continue
                hs = [n for n in a.clip if t + 0.15 < n.start < t + 0.48 and n.vel < 90]
                for n in hs:
                    found += 1
                    self.assertGreaterEqual(ms(n.dur), 80.0, (sd, t, n))
        self.assertGreater(found, 0)

    def test_picked_parts_end_gently(self):
        # a ballad arpeggio / folk Travis verse does not end in a hard choke or a 16th build - unless the band lifts
        hard = {'choke', 'build'}
        for style, sec in (('ballad', 'verse'), ('folk', 'verse'), ('pop', 'intro')):
            for sd in range(15):
                for into in (None, 'verse', 'break'):
                    a = g.arrange(PROG, bpm=BPM, style=style, section=sec, seed=sd, length=16, fill=1.0, density=1.0,
                                  into=into, next_chord='C')
                    self.assertFalse({m[3] for m in a.moves if m[2] == 'fill'} & hard, (style, sec, sd, into))
        lifts = [g.arrange(PROG, bpm=BPM, style='pop', section='intro', seed=sd, length=16, into='chorus',
                           next_chord='C') for sd in SEEDS]
        self.assertTrue(any({m[3] for m in a.moves if m[2] == 'fill'} & hard for a in lifts))

    def test_palm_mutes_respect_the_strings(self):
        a = g.arrange('C G Am F', bpm=BPM, style='pop', section='verse', seed=2, length=16, strings='top4',
                      section_end=False)
        self.assertEqual(a.technique, 'muted8')
        self.assertGreaterEqual(min(n.pitch for n in a.clip), note('D3'))

    def test_errors(self):
        with self.assertRaises(ComposeError):
            g.arrange(PROG, bpm=BPM, style='polka')
        with self.assertRaises(ComposeError):
            g.arrange(PROG, bpm=BPM, technique='tapping')
        with self.assertRaises(ComposeError):
            g.arrange(PROG, bpm=BPM, fills={'dive': 1.0})
        with self.assertRaises(ComposeError):
            g.arrange(PROG, bpm=BPM, articulations={'slap': 'x'})


class TestLead(unittest.TestCase):
    def test_deterministic(self):
        m = line(V_LINE)
        a = g.lead(m, 'Em C G D', bpm=126, key='E minor', seed=3, mono=True)
        b = g.lead(m, 'Em C G D', bpm=126, key='E minor', seed=3, mono=True)
        self.assertEqual(a.clip, b.clip)
        self.assertEqual(a.auto, b.auto)

    def test_picked_notes_attack_slurred_notes_tie(self):
        m = line(V_LINE)
        for sd in range(12):
            a = g.lead(m, 'Em C G D', bpm=126, key='E minor', seed=sd, mono=True, moves={'hammer_on': 3.0,
                                                                                         'pull_off': 3.0})
            ns = sorted((n for n in a.clip if n.dur > 0.06), key=lambda n: n.start)
            tied = {round(t, 3) for t, _, k, nm in a.moves if (k == 'move' and nm in ('hammer_on', 'pull_off'))
                    or k == 'phrasing'}
            for x, y in zip(ns, ns[1:]):
                if round(y.start, 3) in tied:
                    self.assertGreater(x.start + x.dur, y.start)           # legato: overlaps, no new attack
                elif y.start - (x.start + x.dur) > -1e-6 or x.start + x.dur <= y.start:
                    pass
                else:
                    self.fail(f"picked note overlaps the next: {x} {y}")

    def test_velocities_shaped_and_timing_human(self):
        m = line(C_LINE, vel=100)                                         # written flat
        a = g.lead(m, 'C G D Em', bpm=126, key='E minor', style='rock', section='chorus', seed=1, mono=True,
                   moves={})
        self.assertGreaterEqual(spread([n.vel for n in a.clip]), 15)
        written = sorted(n.start for n in m)
        played = sorted(n.start for n in a.clip)
        self.assertEqual(len(written), len(played))
        for w, p in zip(written, played):
            self.assertLessEqual(abs(ms(p - w, 126)), 16.0)

    def test_bends_return_before_the_next_note(self):
        m = line(C_LINE)
        for sd in SEEDS:
            a = g.lead(m, 'C G D Em', bpm=126, key='E minor', style='blues', seed=sd, mono=True)
            pb = a.auto.get('instrument.pitchbend', [])
            if not pb:
                continue
            pts = sorted(pb, key=lambda p: p[0])
            self.assertTrue(all(0 <= p[1] <= 2 for p in pts))
            self.assertEqual(pts[-1][1], 0.0)
            # the windows where the string is bent: no other note may start inside one
            wins, w0 = [], None
            for prev, p in zip(pts, pts[1:]):
                if w0 is None and p[1] > 0:
                    w0 = prev[0] if len(p) > 2 and p[2] != 'step' else p[0]
                elif w0 is not None and p[1] == 0:
                    wins.append((w0, p[0]))
                    w0 = None
            self.assertIsNone(w0)
            for a0, a1 in wins:
                inside = [n for n in a.clip if a0 + 0.03 < n.start < a1 - 1e-6 and n.dur > 0.06]
                self.assertEqual(inside, [], (sd, a0, a1))

    def test_lead_budgets_over_many_seeds(self):
        m = line(V_LINE) + line(C_LINE)
        for style in ('rock', 'blues', 'ballad', 'pop', 'country'):
            S = g.LEAD_STYLES[style]
            for sd in SEEDS:
                mem = g.Memory()
                for i in range(3):
                    g.lead(m, 'Em C G D', bpm=126, key='E minor', style=style, seed=sd * 5 + i, mono=False,
                           memory=mem, density=1.0, climax=i == 2)
                for cls, every in (('flash', S['flash_every']), ('spice', S['spice_every']),
                                   ('fast', S['fast_every'])):
                    ts = sorted(t for t, c, _ in mem.events if c == cls)
                    if every == 0:
                        self.assertEqual(ts, [], (style, cls))
                    for a, b in zip(ts, ts[1:]):
                        self.assertGreaterEqual(b - a, every * 4 - 1e-6, (style, sd, cls, ts))
                fast = [t for t, c, _ in mem.events if c == 'fast']
                self.assertLessEqual(len(fast), 2)
                self.assertEqual(mem.clock, 96.0)

    def test_prebend_is_pushed_in_a_rest_never_under_a_sounding_note(self):
        # the pitch wheel moves the whole track: the silent push of a pre-bend must happen while nothing sounds, so
        # the hand needs a rest before it (and nothing may slur into the pre-bent note)
        m = Key('E minor').motif('8:1 7:0.5 6:0.5 5:1 r:1 | 9:1 8:1 5:1 r:1 | 6:1.5 5:0.5 3:1 r:1 | 8:1 7:1 5:2'
                                 ).clip(octave=4, vel=96, gate=1.0)
        n_pre = 0
        for sd in SEEDS:
            for mono in (True, False):
                a = g.lead(m, 'C G D Em', bpm=126, key='E minor', style='blues', seed=sd, mono=mono, density=1.0,
                           moves={'prebend': 3.0, 'hammer_on': 3.0, 'pull_off': 3.0, 'slide': 3.0, 'scoop': 2.0,
                                  'rake': 2.0}, spice_every=0.25, flash_every=0.5)
                n_pre += a.count('move', 'prebend')
                for p in a.auto.get('instrument.pitchbend', []):
                    if len(p) > 2 and p[2] == 'step' and p[1] > 0:
                        sounding = [n for n in a.clip if n.start < p[0] < n.start + n.dur]
                        self.assertEqual(sounding, [], (sd, mono, p))
        self.assertGreater(n_pre, 10)

    def test_gestures_before_the_first_note_need_room(self):
        # a rake / scoop starts before its note: at the very start of a part there is no room (a clip cannot start
        # before 0) - it must not pile its grace notes onto the downbeat
        m = Key('E minor').motif('8:1.5 7:0.5 8:2 | 5:2 r:2 | 8:1 7:1 5:2').clip(octave=4, vel=110, gate=1.0)
        for sd in SEEDS:
            a = g.lead(m, 'C G D Em', bpm=126, key='E minor', style='blues', seed=sd, mono=sd % 2 == 0, density=1.0,
                       moves={'rake': 3.0, 'scoop': 3.0}, flash_every=0.5, spice_every=0.25)
            self.assertEqual(len([n for n in a.clip if n.start < 0.03]), 1, sd)
            for t, _, k, nm in a.moves:
                if nm in ('rake', 'scoop') and k == 'move':
                    self.assertGreaterEqual(t, 0.0)
        # a pre-bend right after the previous part's last note: the memory knows the lead just played
        mem = g.Memory()
        p1 = Clip([(0, 3.9, 'B4', 100)], length=4)
        p2 = Clip([(0, 1, 'A4', 100), (1, 2, 'G4', 90)], length=4)
        g.lead(p1, 'Em', bpm=100, key='E minor', style='blues', seed=1, mono=True, memory=mem, at=0)
        self.assertAlmostEqual(mem.lead_end, 3.9, delta=0.05)
        free = [g.lead(p2, 'Em', bpm=100, key='E minor', style='blues', seed=sd, mono=True, memory=g.Memory(), at=4,
                       moves={'prebend': 4.0}, flash_every=0.5).count('move', 'prebend') for sd in SEEDS]
        self.assertGreater(sum(free), 0)                                   # after a rest it would pre-bend
        for sd in SEEDS:
            m2 = g.Memory()
            m2.lead_end = mem.lead_end
            a = g.lead(p2, 'Em', bpm=100, key='E minor', style='blues', seed=sd, mono=True, memory=m2, at=4,
                       moves={'prebend': 4.0}, flash_every=0.5)
            self.assertEqual(a.count('move', 'prebend'), 0, sd)

    def test_legato_phrasing_stays_on_one_string(self):
        # a tie without a pick is a hammer-on / pull-off: the same string, within the hand's reach, never out of a bend
        m = line(V_LINE, vel=96) + line(C_LINE, vel=100)
        ps = sorted(m, key=lambda n: n.start)
        fing = g._finger([n.pitch for n in ps], FB)
        seen = 0
        for sd in SEEDS:
            a = g.lead(m, 'Em C G D', bpm=90, key='E minor', style='ballad', seed=sd, mono=True, density=1.0)
            bends = {round(t, 1) for t, _, k, nm in a.moves if k == 'move' and nm == 'bend'}
            for t, _, k, nm in a.moves:
                if k != 'phrasing':
                    continue
                j = min(range(len(ps)), key=lambda x: abs(ps[x].start - t))
                seen += 1
                self.assertEqual(fing[j][0], fing[j - 1][0], (sd, t))
                self.assertLessEqual(abs(ps[j].pitch - ps[j - 1].pitch), 4)
                self.assertNotIn(round(ps[j - 1].start + 0.0, 1), {round(b, 1) for b in bends} - {round(t, 1)})
        self.assertGreater(seen, 20)

    def test_bends_where_a_guitarist_can_bend(self):
        # a low line (the wound E and A strings): half-step bends at most; a written double stop is never bent
        low = Key('E minor').motif('4:2 3:2 | 5:2 4:2 | 6:3 r:1').clip(octave=2, vel=96, gate=1.0)
        for sd in SEEDS:
            a = g.lead(low, 'Em C G D', bpm=100, key='E minor', style='blues', seed=sd, mono=True, density=1.0,
                       moves={'bend': 4.0}, flash_every=0.5)
            self.assertLessEqual(max((p[1] for p in a.auto.get('instrument.pitchbend', [])), default=0), 1)
        ds = Clip([(0, 2, 'G4', 96), (0, 2, 'E4', 90), (2, 2, 'A4', 96), (2, 2, 'F#4', 90), (4, 4, 'B4', 100),
                   (4, 4, 'G4', 92)], length=8)
        for sd in SEEDS:
            a = g.lead(ds, 'Em D G', bpm=100, key='E minor', style='blues', seed=sd, mono=False, density=1.0,
                       moves={'bend': 4.0, 'prebend': 4.0}, flash_every=0.5)
            self.assertEqual(a.count('move', 'bend') + a.count('move', 'prebend'), 0, sd)
            self.assertNotIn('instrument.pitchbend', a.auto)

    def test_double_stops_only_on_a_polyphonic_guitar(self):
        m = line(V_LINE)
        ds = {'double_stop': 3.0}
        for sd in SEEDS:
            a = g.lead(m, 'Em C G D', bpm=126, key='E minor', style='country', seed=sd, mono=True, density=1.0,
                       moves=ds)
            self.assertEqual(a.count('move', 'double_stop'), 0)
        found = [g.lead(m, 'Em C G D', bpm=126, key='E minor', style='country', seed=sd, mono=False, density=1.0,
                        moves=ds) for sd in SEEDS]
        self.assertTrue(any(a.count('move', 'double_stop') for a in found))
        for a in found:
            for t, _, k, nm in a.moves:
                if nm == 'double_stop' and k == 'move':
                    two = [n for n in a.clip if abs(n.start - t) < 0.02]
                    self.assertEqual(len(two), 2)
                    self.assertTrue(3 <= two[1].pitch - two[0].pitch <= 9 or 3 <= two[0].pitch - two[1].pitch <= 9)

    def test_fingering_is_on_the_neck(self):
        ps = [note(x) for x in ('E4', 'G4', 'A4', 'B4', 'D5', 'E5', 'G5', 'A5', 'B5')]
        f = g._finger(ps, FB)
        for p, (s, fr) in zip(ps, f):
            self.assertEqual(FB.open[s] + fr, p)
        shifts = [abs(b[1] - a[1]) for a, b in zip(f, f[1:])]
        self.assertLessEqual(max(shifts), 7)

    def test_vibrato_on_long_notes_only(self):
        a = g.lead(line(V_LINE), 'Em C G D', bpm=126, key='E minor', style='ballad', seed=1, mono=True, moves={})
        self.assertIn('instrument.vibrato', a.auto)
        vib = [m for m in a.moves if m[2] == 'vibrato']
        self.assertTrue(all(m[1] - m[0] >= 0.75 - 1e-6 for m in vib))

    def test_errors(self):
        with self.assertRaises(ComposeError):
            g.lead(line(V_LINE), bpm=120, style='shred')
        with self.assertRaises(ComposeError):
            g.lead(line(V_LINE), bpm=120, moves={'tap': 1.0})


if __name__ == '__main__':
    unittest.main()
