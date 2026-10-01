import importlib.util
import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import jazz  # noqa: E402
from agentsound.humanize import jazz_groove, layback_ms, phrase_dynamics, swing_ratio  # noqa: E402
from agentsound.patterns import Clip, chords  # noqa: E402
from agentsound.song import Song  # noqa: E402
from agentsound.theory import (ComposeError, Key, Progression, check_voicing, chord, chord_kind,  # noqa: E402
                               chord_scale_name, guide_tones, jazz_voicings, mud, note, note_name, rootless, voice)

REPO = pathlib.Path(__file__).resolve().parents[2]


def names(ps):
    return ' '.join(note_name(p, flats=True) for p in ps)


def pcs(ps):
    return {p % 12 for p in ps}


def pc_names(ps):
    return {note_name(p, flats=True)[:-1] for p in ps}


# every quality the parser accepts that a jazz tune uses
JAZZ_SYMBOLS = ['Cmaj7', 'Cmaj9', 'Cmaj13', 'Cmaj7#11', 'Cmaj7#5', 'C6', 'C6/9', 'C', 'Cadd9', 'Cm', 'Cm7', 'Cm9',
                'Cm11', 'Cm13', 'Cm6', 'Cm6/9', 'Cm(maj7)', 'CmMaj9', 'Cm7b5', 'Cø', 'Cø9', 'Cdim', 'Cdim7', 'C+',
                'C7', 'C9', 'C11', 'C13', 'C7b9', 'C7#9', 'C7alt', 'C7b13', 'C7#5', 'C7b5', 'C7#11', 'C9#11', 'C13#11',
                'C13b9', 'C7b9b13', 'C7#9b13', 'C7b9#11', 'C7(b9,#11)', 'Csus4', 'C7sus4', 'C9sus4', 'C13sus4',
                'C7sus4b9', 'C5', 'Fmaj7/A', 'Bb7', 'F#m7b5', 'Ebmaj7', 'Ab13', 'Db7alt', 'Gm6', 'Em7']


class JazzVoicings(unittest.TestCase):
    def test_two_five_one_rootless_pitches(self):
        self.assertEqual(names(rootless('Dm7', 'A')), 'F3 A3 C4 E4')        # 3 5 7 9
        self.assertEqual(names(rootless('G7', 'B')), 'F3 A3 B3 E4')         # 7 9 3 13
        self.assertEqual(names(rootless('Cmaj7', 'A')), 'E3 G3 B3 D4')      # 3 5 7 9
        self.assertEqual(names(rootless('Dm7', 'B')), 'C4 E4 F4 A4')        # 7 9 3 5
        self.assertEqual(pc_names(rootless('G7', 'A')), {'B', 'E', 'F', 'A'})

    def test_every_symbol_voices_against_its_label(self):
        for sym in JAZZ_SYMBOLS:
            for form in ('A', 'B'):
                v = rootless(sym, form)
                self.assertEqual(len(set(v)), len(v), (sym, form, names(v)))
                self.assertTrue(3 <= len(v) <= 4, (sym, form, names(v)))
                self.assertEqual(check_voicing(sym, v), [], (sym, form, names(v)))
                self.assertTrue(all(43 <= p <= 77 for p in v), (sym, form, names(v)))
            for style in ('shell', 'quartal', 'rootless'):
                if chord_kind(sym) == 'power' and style == 'shell':
                    continue
                v = voice(sym, style, bass=False)
                self.assertTrue(v and v == sorted(v), (sym, style, v))
        # every root: the same qualities transposed stay clean (no mud at the bottom of the left-hand zone)
        for root in ('Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'):
            for sym in JAZZ_SYMBOLS:
                if not sym.startswith('C') or '/' in sym:
                    continue
                s = root + sym[1:]
                for form in ('A', 'B'):
                    self.assertEqual(check_voicing(s, rootless(s, form)), [], (s, form))

    def test_spelled_colours(self):
        self.assertEqual(pc_names(rootless('G7alt', 'A')), {'B', 'Eb', 'F', 'Bb'})     # 3 b13 b7 #9
        self.assertEqual(pc_names(rootless('G7b9', 'A')), {'B', 'E', 'F', 'Ab'})       # 3 13 b7 b9
        self.assertEqual(pc_names(rootless('G7#9', 'B')), {'F', 'Bb', 'B', 'E'})       # b7 #9 3 13
        self.assertEqual(pc_names(rootless('Bm7b5', 'A')), {'D', 'F', 'A', 'B'})       # b3 b5 b7 1
        self.assertEqual(pc_names(rootless('Bø9', 'A')), {'D', 'F', 'A', 'Db'})        # b3 b5 b7 9
        self.assertEqual(pc_names(rootless('C6/9', 'A')), {'E', 'G', 'A', 'D'})
        self.assertEqual(pc_names(rootless('Cm(maj7)', 'A')), {'Eb', 'G', 'B', 'D'})
        self.assertEqual(pc_names(rootless('Cmaj7#11', 'A')), {'E', 'Gb', 'B', 'D'})
        self.assertEqual(pc_names(rootless('G7sus4', 'B')), {'F', 'A', 'C', 'D'})      # no 3rd
        self.assertEqual(pc_names(rootless('C11', 'A')), {'F', 'G', 'Bb', 'D'})        # C11 = C9sus4
        self.assertEqual(pc_names(rootless('Cdim7', 'A')), {'Eb', 'Gb', 'A', 'C'})
        self.assertNotIn(0, pcs(rootless('Cmaj7', 'A')))                               # rootless
        self.assertIn(9, pcs(rootless('C13', 'A')))                                    # the 13 is there

    def test_minor_resolution_colours_the_dominant(self):
        vs = jazz_voicings(['Bm7b5', 'E7b9', 'Am6'])
        self.assertIn(0, pcs(vs[1]))              # C = b13 of E, not C# (the natural 13)
        self.assertNotIn(1, pcs(vs[1]))
        self.assertEqual(chord_scale_name('G7', resolve_minor=True), 'phrygian_dominant')
        vs = jazz_voicings(['Dm7', 'G7', 'Cmaj7'])
        self.assertIn(4, pcs(vs[1]))              # E = the natural 13 of G going to major

    def test_sequence_alternates_forms_and_guide_tones_step(self):
        seq = ['Dm7', 'G7', 'Cmaj7', 'Cmaj7', 'Em7', 'A7', 'Dm7', 'G7']
        vs = jazz_voicings(seq)
        self.assertEqual([names(v) for v in vs[:3]], ['F3 A3 C4 E4', 'F3 A3 B3 E4', 'E3 G3 B3 D4'])
        for (a, va), (b, vb) in zip(zip(seq, vs), zip(seq[1:], vs[1:])):
            if (chord(b).root - chord(a).root) % 12 not in (5, 7):
                continue                                        # the rule is for roots moving by 4ths / 5ths
            ga, gb = guide_tones(a), guide_tones(b)
            for g in ga:
                pa = [p for p in va if p % 12 == g]
                if not pa:
                    continue
                dist = min(abs(x - y) for x in pa for y in vb if y % 12 in gb)
                self.assertLessEqual(dist, 2, (a, b, names(va), names(vb)))
        # a long cycle of 5ths stays in the left-hand zone (octave shifts instead of drifting away)
        cyc = ['Fmaj7', 'Em7b5', 'A7b9', 'Dm7', 'G7', 'Cm7', 'F7', 'Bbmaj7', 'Bbm7', 'Eb7', 'Am7', 'D7', 'Abm7',
               'Db7', 'Gm7', 'C7'] * 2
        for v in jazz_voicings(cyc):
            self.assertTrue(all(45 <= p <= 74 for p in v), names(v))
            self.assertEqual(mud(v), [], names(v))

    def test_shell_quartal_so_what(self):
        self.assertEqual(pc_names(jazz.shell('Dm7', '37')), {'F', 'C'})
        s = jazz.shell('G7', '73')
        self.assertEqual(s[0] % 12, 5)                                  # 7th at the bottom
        self.assertEqual(pc_names(jazz.shell('Bm7b5')), {'D', 'F', 'A'})  # the b5 tells ø from m7
        bp = jazz.shell('G7', root=True)
        self.assertEqual(names(bp), 'G2 F3 B3')                          # Bud Powell: 1 7 10
        self.assertEqual(pc_names(jazz.quartal('Dm7')), {'D', 'G', 'C', 'F'})
        self.assertEqual(pc_names(jazz.quartal('G7')), {'F', 'B', 'E', 'A'})
        self.assertEqual(pc_names(jazz.quartal('Cmaj7')), {'B', 'E', 'A', 'D'})
        self.assertEqual(pc_names(jazz.quartal('G7alt')), {'B', 'F', 'Bb', 'Eb'})
        q = jazz.quartal('Dm7')
        self.assertEqual([b - a for a, b in zip(q, q[1:])], [5, 5, 5])
        sw = jazz.so_what('Dm7')
        self.assertEqual([b - a for a, b in zip(sw, sw[1:])], [5, 5, 5, 4])
        self.assertEqual(sw[0] % 12, 2)
        self.assertEqual(pc_names(jazz.so_what('Cmaj7')), {'E', 'A', 'D', 'G', 'B'})

    def test_block_chords(self):
        self.assertEqual(names(jazz.block('C6', 'C5', 'close')), 'E4 G4 A4 C5')
        self.assertEqual(names(jazz.block('C6', 'C5', 'drop2')), 'A3 E4 G4 C5')
        self.assertEqual(names(jazz.block('C6', 'C5', 'locked')), 'C4 E4 G4 A4 C5')
        self.assertEqual(names(jazz.block('Cmaj7', 'B4', 'close')), 'C4 E4 G4 B4')    # maj7 melody: maj7 set
        self.assertEqual(names(jazz.block('C6', 'D5', 'close')), 'E4 G4 A4 D5')       # 9 replaces the root
        self.assertEqual(pc_names(jazz.block('C6', 'F5', 'close')), {'F', 'Ab', 'B', 'D'})   # passing: dim7
        self.assertEqual(names(jazz.block('G7', 'E5', 'close')), 'F4 G4 B4 E5')       # 13 replaces the 5th
        v = jazz.block('G7', 'Ab5', 'drop24')
        self.assertEqual(v[-1], note('Ab5'))
        with self.assertRaises(ComposeError):
            jazz.block('C6', 'C5', 'weird')

    def test_upper_structures(self):
        u = jazz.upper_structure('G7alt')
        self.assertEqual(pc_names(u[:2]), {'B', 'F'})
        self.assertEqual(pc_names(u[2:]), {'Eb', 'G', 'Bb'})           # bVI
        self.assertTrue(u[2] > u[1])
        self.assertEqual(pc_names(jazz.upper_structure('G7b9')[2:]), {'E', 'Ab', 'B'})       # VI
        self.assertEqual(pc_names(jazz.upper_structure('G13#11')[2:]), {'A', 'Db', 'E'})     # II
        self.assertEqual(pc_names(jazz.upper_structure('G7', triad='bV')[2:]), {'Db', 'F', 'Ab'})
        with self.assertRaises(ComposeError):
            jazz.upper_structure('Cmaj7')
        with self.assertRaises(ComposeError):
            jazz.upper_structure('G7')            # natural dominant: say which triad
        u = jazz.upper_structure('G7alt', top='Bb5')
        self.assertEqual(u[-1], note('Bb5'))

    def test_mud_and_limits(self):
        self.assertEqual(mud([note('E3'), note('F3')]), [])
        self.assertEqual(len(mud([note('E2'), note('F2')])), 1)
        self.assertEqual(len(mud([note('C2'), note('E2')])), 1)
        self.assertEqual(mud([note('Bb1'), note('F2')]), [])            # a 5th is fine down there
        self.assertIn('muddy', ' '.join(check_voicing('Cmaj7', [40, 43, 47, 50])))

    def test_parser_additions(self):
        self.assertEqual(chord('Cø9').intervals, (0, 3, 6, 10, 14))
        self.assertEqual(chord('Cm7(11)').intervals, chord('Cm11').intervals[:4] + (17,))
        self.assertEqual(set(chord('C7(13)').intervals), {0, 4, 7, 10, 21})
        k = Key('C major')
        self.assertEqual(k.chord('iim7b5').symbol, 'Dm7b5')
        self.assertEqual(k.chord('ivm7').symbol, 'Fm7')
        self.assertEqual(set(Key('A minor').chord('im(maj7)').intervals), {0, 3, 7, 11})
        with self.assertRaises(ComposeError):
            chord('C3')

    def test_chord_scales(self):
        cases = {'G7': 'mixolydian', 'G7alt': 'altered', 'G7b9': 'half_whole', 'G7#11': 'lydian_dominant',
                 'G7b13': 'mixolydian_b6', 'G7#5': 'whole_tone', 'Bm7b5': 'locrian', 'Bø9': 'locrian_2',
                 'C6/9': 'ionian', 'Cmaj7#11': 'lydian', 'Cm(maj7)': 'melodic_minor', 'Dm7': 'dorian',
                 'Cdim7': 'whole_half', 'G7sus4': 'mixolydian'}
        for sym, want in cases.items():
            self.assertEqual(chord_scale_name(sym), want, sym)
        self.assertNotIn(5, jazz.available_tensions('Cmaj7'))            # the 11 over a major 3rd
        self.assertIn(1, jazz.available_tensions('C7alt'))

    def test_progression_integration(self):
        p = Progression('Dm7 G7 Cmaj7')
        v = p.voiced('rootless', register=(48, 72))
        self.assertEqual([names(x) for _, _, x in v], ['F3 A3 C4 E4', 'F3 A3 B3 E4', 'E3 G3 B3 D4'])
        c = chords(p, voicing='shell', register=(48, 72))
        self.assertEqual(len(c), 6)
        self.assertEqual(voice('G7', 'rootless_b', bass=False), rootless('G7', 'B'))
        with self.assertRaises(ComposeError):
            jazz.jazz_voicings(['Dm7'], 'weird')


class Comping(unittest.TestCase):
    PROG = Progression('Dm7 G7 Cmaj7 A7 | Dm7 G7 Em7:0.5 A7:0.5 Dm7:0.5 G7:0.5', key='C major')

    def test_deterministic_and_chord_tones(self):
        a = jazz.comp(self.PROG, seed=3)
        self.assertEqual(a, jazz.comp(self.PROG, seed=3))
        self.assertNotEqual(a, jazz.comp(self.PROG, seed=4))
        self.assertEqual(a.length, self.PROG.length)
        for n in a:
            here = self.PROG.at(n.start)
            nxt = self.PROG.at(n.start + 0.5)
            ok = set()
            for c in (here, nxt):
                ok |= {(c.root + i) % 12 for i in c.intervals} | {(c.root + t) % 12 for t in jazz.available_tensions(c)}
                ok |= set(guide_tones(c)) - {None}
                ok |= {(c.root + t) % 12 for t in jazz.available_tensions(c, resolve_minor=True)}
            self.assertIn(n.pitch % 12, ok, (n, here, nxt))
            self.assertTrue(43 <= n.pitch <= 77)

    def test_density_and_intensity(self):
        long = self.PROG * 4
        sparse = jazz.comp(long, density=0.05, seed=1)
        busy = jazz.comp(long, density=1.0, seed=1)
        onsets = lambda c: len({round(n.start, 3) for n in c})  # noqa: E731
        self.assertLess(onsets(sparse), onsets(busy))
        soft = jazz.comp(long, intensity=0.0, seed=1)
        hard = jazz.comp(long, intensity=1.0, seed=1)
        mean = lambda c: sum(n.vel for n in c) / len(c)  # noqa: E731
        self.assertLess(mean(soft) + 15, mean(hard))

    def test_styles(self):
        prog = Progression('Cmaj7 Am7 Dm7 G7', key='C major') * 4
        ch = jazz.comp(prog, style='charleston', density=0.5, seed=2)
        starts = {round(n.start % 4, 3) for n in ch}
        self.assertIn(0.0, starts)
        self.assertIn(1.5, starts)
        g = jazz.comp(prog, style='garland', density=0.5, seed=2)
        offbeats = sum(1 for n in g if abs(n.start % 1 - 0.5) < 1e-6)
        self.assertGreater(offbeats, len(g) * 0.6)
        b = jazz.comp(prog, style='bossa', seed=2)
        self.assertTrue({round(n.start % 8, 3) for n in b} <= {0.0, 1.5, 3.0, 5.0, 6.5, 7.5})
        w = jazz.comp(Progression('Dm7 G7 Cmaj7', key='C major', beats_per_bar=3), style='waltz', seed=1)
        self.assertEqual(w.length, 9)
        with self.assertRaises(ComposeError):
            jazz.comp(Progression('Dm7 G7', beats_per_bar=3), style='swing')
        with self.assertRaises(ComposeError):
            jazz.comp(self.PROG, style='funk')
        with self.assertRaises(ComposeError):
            jazz.comp(self.PROG, density=2)

    def test_anticipation_plays_the_next_chord(self):
        prog = Progression('Dm7 G7 Cmaj7 Cmaj7', key='C major') * 8
        c = jazz.comp(prog, style='swing', density=0.6, seed=5)
        pushes = [n for n in c if abs(n.start % 4 - 3.5) < 1e-6 and n.start + n.dur > (n.start // 4 + 1) * 4 + 0.2]
        self.assertTrue(pushes)
        for n in pushes:
            nxt = prog.at(n.start + 0.5)
            self.assertIn(n.pitch % 12, {(nxt.root + i) % 12 for i in nxt.intervals}
                          | {(nxt.root + t) % 12 for t in jazz.available_tensions(nxt)} | set(guide_tones(nxt)))
            downbeat = (n.start // 4 + 1) * 4
            self.assertFalse([m for m in c if abs(m.start - downbeat) < 1e-6],
                             'an anticipated chord is not struck again on the downbeat')

    def test_answer_the_melody(self):
        prog = Progression('Dm7 G7 Cmaj7 Cmaj7', key='C major') * 2
        mel = Clip([(0, 3, 'A4', 90), (4, 3, 'B4', 90), (8, 1.5, 'C5', 90), (9.5, 0.5, 'D5', 90), (16, 6, 'E5', 90)],
                   length=32)
        c = jazz.comp(prog, style='swing', density=0.7, answer=mel, seed=2)
        for n in c:
            inside = [m for m in mel if m.start - 1e-6 <= n.start < m.start + m.dur + 0.25 - 1e-6]
            if inside:
                self.assertTrue(any(abs(n.start - s) < 1e-6 for s, _, _ in prog) or n.dur <= 0.5 + 1e-6, n)
        for a, b in ((3.25, 4), (7.25, 8), (10.25, 16), (22.25, 32)):
            if b - a >= 1.0:
                self.assertTrue([n for n in c if a - 1e-6 <= n.start < b], f"no answer in the rest {a}..{b}")

    def test_touch_varies_the_hits_not_the_notes(self):
        prog = self.PROG * 4
        flat = jazz.comp(prog, style='swing', density=0.6, seed=7, touch=0)
        felt = jazz.comp(prog, style='swing', density=0.6, seed=7)
        self.assertEqual([(n.start, n.dur, n.pitch) for n in flat], [(n.start, n.dur, n.pitch) for n in felt])

        def spread(c):                                  # 10-90 % of the hits' top-voice velocities
            hits = {}
            for n in c:
                hits[round(n.start, 3)] = max(hits.get(round(n.start, 3), 0), n.vel)
            v = sorted(hits.values())
            return v[int(0.9 * len(v))] - v[int(0.1 * len(v))]
        self.assertGreater(spread(felt), spread(flat) + 8)                     # hit-to-hit dynamics
        energy = lambda c: sum(n.vel ** 4 for n in c) / len(c)  # noqa: E731
        self.assertLess(abs(10 * math.log10(energy(felt) / energy(flat))), 1.0)   # the loudness stays
        with self.assertRaises(ComposeError):
            jazz.comp(prog, touch=2)


class WalkingBass(unittest.TestCase):
    KEY = Key('Bb major')
    PROG = KEY.prog('Imaj7 vi7 ii7 V7 | iii7 VI7 ii7 V7 | Imaj7 IV7 iii7:0.5 VI7:0.5 ii7:0.5 V7:0.5 | Imaj7:2')

    def test_walk_rules(self):
        line = jazz.walking_bass(self.PROG, key=self.KEY, seed=4, skip=0.0)
        main = [n for n in line]
        self.assertEqual(len(main), int(self.PROG.length))                  # one note per beat
        self.assertEqual([n.start for n in main], [float(i) for i in range(int(self.PROG.length))])
        self.assertTrue(all(note('E1') <= n.pitch <= note('G3') for n in main))
        segs = [(s, d, c) for s, d, c in self.PROG]
        for i, (s, d, c) in enumerate(segs):
            first = next(n for n in main if abs(n.start - s) < 1e-6)
            if i == 0 or segs[i - 1][2].symbol != c.symbol:
                self.assertEqual(first.pitch % 12, c.bass_pc, (s, c))
            if i + 1 < len(segs) and segs[i + 1][2].symbol != c.symbol:
                last = next(n for n in main if abs(n.start - (s + d - 1)) < 1e-6)
                tgt = next(n for n in main if abs(n.start - (s + d)) < 1e-6)
                self.assertIn(abs(last.pitch - tgt.pitch), (1, 2, 5, 7), (s, c, last, tgt))
        leaps = [abs(b.pitch - a.pitch) for a, b in zip(main, main[1:])]
        self.assertLessEqual(max(leaps), 12)
        self.assertLess(sum(1 for x in leaps if x > 7), len(leaps) * 0.15)
        self.assertLess(sum(1 for x in leaps if x == 0), len(leaps) * 0.15)
        self.assertTrue(all(n.dur < 1.0 for n in main))                  # slightly detached

    def test_deterministic_and_options(self):
        a = jazz.walking_bass(self.PROG, key=self.KEY, seed=1)
        self.assertEqual(a, jazz.walking_bass(self.PROG, key=self.KEY, seed=1))
        self.assertNotEqual(a, jazz.walking_bass(self.PROG, key=self.KEY, seed=2))
        sk = jazz.walking_bass(self.PROG, key=self.KEY, seed=1, skip=1.0)
        ghosts = [n for n in sk if abs(n.start % 1 - 0.5) < 1e-6]
        self.assertTrue(ghosts)
        self.assertTrue(all(g.vel < 60 for g in ghosts))
        for bad in (dict(feel='three'), dict(approach='wild'), dict(skip=2), dict(low='C3', high='E3')):
            with self.assertRaises(ComposeError):
                jazz.walking_bass(self.PROG, key=self.KEY, **bad)

    def test_two_feel_and_pedal(self):
        two = jazz.walking_bass(self.PROG, key=self.KEY, feel='two', skip=0.0, seed=3)
        self.assertTrue(all(n.start % 2 == 0 for n in two))
        self.assertTrue(all(n.dur > 1.5 for n in two if n.start + 2 <= 16))
        ped = jazz.walking_bass(self.PROG, key=self.KEY, pedal=[(0, 8, 'F2')], skip=0.0, seed=3)
        self.assertTrue(all(n.pitch % 12 == 5 for n in ped if n.start < 7))
        self.assertIn(ped[7].pitch % 12, (11, 1, 5))    # the last pedal beat approaches the next root (C)

    def test_touch_gives_the_line_dynamics(self):
        prog = self.PROG * 2
        flat = jazz.walking_bass(prog, key=self.KEY, seed=5, touch=0)
        felt = jazz.walking_bass(prog, key=self.KEY, seed=5)
        self.assertEqual([(n.start, n.dur, n.pitch) for n in flat], [(n.start, n.dur, n.pitch) for n in felt])
        vf, vt = [n.vel for n in flat if n.dur > 0.4], [n.vel for n in felt if n.dur > 0.4]
        self.assertLess(max(vf) - min(vf), 12)                                   # the old line: one level
        self.assertGreater(max(vt) - min(vt), 25)                                # arcs, accents, approaches
        energy = lambda c: sum(n.vel ** 4 for n in c) / len(c)  # noqa: E731
        self.assertLess(abs(10 * math.log10(energy(felt) / energy(flat))), 0.5)   # vel keeps the loudness
        two = jazz.walking_bass(prog, key=self.KEY, feel='two', skip=0.0, seed=5)
        ones = [n.vel for n in two if n.start % 4 == 0]
        threes = [n.vel for n in two if n.start % 4 == 2]
        self.assertGreater(sum(ones) / len(ones), sum(threes) / len(threes))    # two-feel: 1 leads, 3 answers
        with self.assertRaises(ComposeError):
            jazz.walking_bass(prog, key=self.KEY, touch=-1)


class BrushesAndRide(unittest.TestCase):
    def test_gm_brush_groove(self):
        c = jazz.brushes(8, seed=1)
        self.assertEqual(c.length, 32)
        sweeps = sorted(n.start for n in c if n.pitch == 40)
        self.assertEqual(sweeps, [float(x) for x in range(0, 32, 2)])
        self.assertTrue(all(n.dur < 2 for n in c if n.pitch == 40))       # retriggered, never overlapping
        taps = [n for n in c if n.pitch == 38 and n.start % 1 == 0]
        self.assertTrue(all(n.start % 2 == 1 for n in taps))              # 2 and 4
        self.assertTrue({1.0, 3.0, 5.0} <= {n.start for n in taps})
        self.assertEqual({n.start % 2 for n in c if n.pitch == 44}, {1.0})
        self.assertTrue(all(n.vel <= 30 for n in c if n.pitch == 36 and n.start < 28))   # feathered
        fill = [n for n in c if 30 <= n.start < 32 and n.pitch in (38, 39)]
        self.assertGreaterEqual(len(fill), 2)                              # the phrase-end fill

    def test_kits_and_errors(self):
        c = jazz.brushes(4, kit=jazz.SWIRLY_BRUSH, sweep='bar', seed=2)
        self.assertEqual(sorted(n.start for n in c if n.pitch == 60), [0.0, 4.0, 8.0, 12.0])
        with self.assertRaises(ComposeError) as e:
            jazz.brushes(4, kit={'tap': 38}, seed=1)
        self.assertIn('sweep', str(e.exception))
        with self.assertRaises(ComposeError):
            jazz.brushes(4, style='rock')
        rr = jazz.brushes(2, kit=dict(jazz.GM_BRUSH, tap=[38, 39]), sweep=False, fills=False, seed=1)
        self.assertEqual({n.pitch for n in rr if n.start % 2 == 1 and n.start % 1 == 0 and n.pitch in (38, 39)},
                         {38, 39})

    def test_ride_and_fills(self):
        r = jazz.ride_pattern(2, variation=0.0)
        self.assertEqual(sorted({n.start % 4 for n in r}), [0.0, 1.0, 1.5, 2.0, 3.0, 3.5])
        on2 = [n.vel for n in r if n.start % 4 == 1.0]
        on1 = [n.vel for n in r if n.start % 4 == 0.0]
        skip = [n.vel for n in r if n.start % 4 == 1.5]
        self.assertGreater(min(on2), max(skip))
        self.assertGreater(sum(on2) / len(on2), sum(on1) / len(on1))
        for kind in jazz.FILL_KINDS:
            f = jazz.brush_fill(kind, 2)
            self.assertTrue(f.notes and all(0 <= n.start < 2 for n in f), kind)
        t = jazz.brush_fill('triplets', 1, vel=(30, 90))
        self.assertEqual([round(n.start, 3) for n in t], [0.0, 0.333, 0.667])
        self.assertLess(t[0].vel, t[1].vel)
        with jazz_brush_error(self):
            jazz.brush_fill('rimshot', 2)
        with_ride = jazz.brushes(2, ride=True, seed=1)
        self.assertTrue([n for n in with_ride if n.pitch == 51])
        self.assertFalse([n for n in with_ride if n.pitch == 38 and n.start % 2 == 1 and n.start % 1 == 0])


class jazz_brush_error:
    def __init__(self, tc):
        self.tc = tc

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        self.tc.assertIs(et, ComposeError)
        return True


class Feel(unittest.TestCase):
    def test_swing_ratio_by_tempo(self):
        self.assertAlmostEqual(swing_ratio(60), 0.66)
        self.assertAlmostEqual(swing_ratio(140), 0.61)
        self.assertAlmostEqual(swing_ratio(220), 0.555)
        vals = [swing_ratio(b) for b in range(50, 320, 10)]
        self.assertEqual(vals, sorted(vals, reverse=True))
        self.assertEqual(layback_ms('sax', 70), 35.0)
        self.assertEqual(layback_ms('sax', 140), 22.0)
        self.assertLess(layback_ms('bass', 140), 0)
        self.assertTrue(10 <= layback_ms('piano', 140) <= 25)
        with self.assertRaises(ComposeError):
            layback_ms('kazoo', 120)

    def test_groove_applied_at_compile(self):
        s = Song('t', tempo=140, key='C major')
        s.section('a', bars=1)
        t = s.track('p', {'type': 'sf2', 'params': {}})
        t.play(Clip([(1.0, 0.5, 60, 90), (1.5, 0.5, 62, 90)], length=4))
        t.groove(jazz_groove('piano', 140))
        notes = s.compile()['tracks'][0]['notes']
        late = 16.0 / 1000 * 140 / 60
        self.assertAlmostEqual(notes[0][0], 1.0 + late, places=4)
        self.assertAlmostEqual(notes[1][0], 1.0 + 0.61 + late, places=4)
        g = jazz_groove('bass', 140)
        self.assertEqual(g.vel[2], 1.04)
        self.assertEqual(jazz_groove('bossa' if False else 'comp', 140, ratio=0.5).swing, 0.5)

    def test_feel_object(self):
        f = jazz.Feel(140)
        self.assertAlmostEqual(f.ratio, 0.61)
        c = f.apply(Clip([(0, 0.5, 60, 90), (0.5, 0.5, 62, 90)], length=1), 'bass')
        self.assertEqual(c[0].start, 0.0)                                   # never before the clip start
        self.assertAlmostEqual(c[1].start, 0.61 - 3.0 / 1000 * 140 / 60, places=5)
        f2 = jazz.Feel(140, ratio=0.66, layback={'sax': 40})
        self.assertEqual(f2.late_ms('sax'), 40)
        self.assertEqual(f2.groove('sax').late_ms, 40)

    def test_phrase_dynamics(self):
        line = Clip([(i * 0.5, 0.5, p, 80) for i, p in enumerate([60, 62, 64, 72, 65, 64, 62, 60])] +
                    [(8, 1, 60, 80)], length=12)
        d = phrase_dynamics(line, arch=0.2, peak=1.1, end=0.85)
        v = [n.vel for n in d]
        self.assertGreater(v[3], v[0])                  # arch + peak on the top note
        self.assertLess(v[7], v[4])                     # soft short phrase end
        self.assertEqual(len(jazz.phrases(line, gap=0.5)), 2)
        g = phrase_dynamics(Clip([(0, 0.5, 64, 80), (0.5, 0.5, 60, 80), (1, 0.5, 65, 80)], length=2), arch=0,
                            peak=1, ghost=0.6)
        self.assertLess(g[1].vel, g[0].vel * 0.8)
        b = jazz.backbeat(Clip([(i, 0.5, 60, 80) for i in range(4)], length=4), 1.2)
        self.assertEqual([n.vel for n in b], [80, 96, 80, 96])
        w = jazz.backbeat(Clip([(i, 0.5, 60, 80) for i in range(6)], length=6), 1.2, beats_per_bar=3)
        self.assertEqual([n.vel for n in w], [80, 96, 96, 80, 96, 96])            # waltz: 2 and 3
        self.assertEqual(jazz_groove('bass', 150, beats_per_bar=3).vel, (1.0, 1.0, 1.04, 1.0, 1.04, 1.0))
        self.assertEqual(jazz.Feel(150, beats_per_bar=3).groove('bass').vel, (1.0, 1.0, 1.04, 1.0, 1.04, 1.0))


class HornExpression(unittest.TestCase):
    MEL = Clip([(0.5, 0.5, 'D4', 90), (1.0, 0.5, 'F4', 90), (1.5, 2.5, 'A4', 90),
                (4.5, 0.5, 'G4', 90), (5.0, 0.5, 'F4', 90), (5.5, 0.5, 'D4', 90), (6.0, 1.5, 'Bb3', 90),
                (8.0, 4.0, 'C4', 90)], length=16)

    def test_point_generators(self):
        self.assertEqual(jazz.scoop(4, -80, 0.25), [(4.0, 0.0), (4.0, -0.8, 'step'), (4.25, 0.0, 'smooth')])
        from agentsound.automation import normalize
        self.assertEqual(normalize(jazz.scoop(4, -80, 0.25)),
                         [[3.999, 0.0], [4.0, -0.8, 'step'], [4.25, 0.0, 'smooth']])
        f = jazz.fall(8, -3, 0.5, back=8.5)
        self.assertEqual(f, [(7.5, 0.0), (8.0, -3.0, 'smooth'), (8.5, 0.0, 'step')])
        sw = jazz.swell(0, 4, -6, 0, -8)
        self.assertEqual([p[1] for p in sw], [0.0, -6, 0, -8, 0.0])
        d, r = jazz.vibrato(0, 4, 120, depth=0.2, hz=5.0, delay=0.4, grow=0.5)
        self.assertEqual(d[0][1], 0.0)
        self.assertAlmostEqual(d[1][0], 0.8)                 # 0.4 s at 120 BPM
        self.assertAlmostEqual(max(p[1] for p in d), 0.2)
        self.assertEqual(d[-1][1], 0.0)
        self.assertAlmostEqual(r[0][1], 120 / 60 / 5.0)
        self.assertEqual(jazz.vibrato(0, 0.5, 120), ([], []))     # too short for a vibrato

    def test_horn_line_performance(self):
        line = jazz.horn_line(self.MEL, 140, scoop=1.0, fall=1.0, seed=1, param='level')
        c = line.clip
        late = 22.0 / 1000 * 140 / 60
        self.assertAlmostEqual(c[0].start, 0.61 + late, places=4)            # swung & laid back
        self.assertAlmostEqual(c[1].start, 1.0 + late, places=4)
        self.assertGreater(c[0].start + c[0].dur, c[1].start)                 # legato inside the phrase
        a4 = next(n for n in c if n.pitch == note('A4'))
        g4 = next(n for n in c if n.pitch == note('G4'))
        self.assertGreaterEqual(g4.start - (a4.start + a4.dur), 0.4 - 1e-6)  # a breath before the next phrase
        e = line.expr
        self.assertIn('instrument.pitchbend', e.lanes)
        bends = e.lanes['instrument.pitchbend']
        self.assertTrue(any(p[1] < -0.4 for p in bends))                      # a scoop
        self.assertTrue(any(p[1] <= -2.9 for p in bends))                     # the fall on the last note
        self.assertIn('level', e.swells)
        self.assertEqual(len(e.vibratos), 1)                                  # one lfo for the whole line

    def test_place_on_a_track_compiles(self):
        s = Song('horn', tempo=140, key='Bb major')
        a = s.section('a', bars=4)
        b = s.section('b', bars=4)
        sax = s.track('sax', {'type': 'sf2', 'params': {'preset': 'Tenor Sax', 'level': 2.0, 'mono': 'on'}})
        line = jazz.horn_line(self.MEL, 140, scoop=1.0, fall=1.0, param='level', seed=2)
        line.place(sax, a)
        line.place(sax, b)                                                    # head in and head out
        d = s.compile()
        tr = d['tracks'][0]
        targets = {x['target'] for x in tr['automation']}
        self.assertIn('instrument.pitchbend', targets)
        self.assertIn('instrument.level', targets)
        self.assertTrue(any(t.startswith('mod.') and t.endswith('.depth') for t in targets))
        self.assertEqual(len(tr['modulators']), 2)
        self.assertTrue(all(m['target'] == 'instrument.pitchbend' and m['mode'] == 'offset' for m in tr['modulators']))
        lvl = next(x for x in tr['automation'] if x['target'] == 'instrument.level')
        self.assertTrue(all(-60 <= p[1] <= 12 for p in lvl['points']))
        self.assertLessEqual(max(p[1] for p in lvl['points']), 2.0 + 1e-6)   # relative to the sound's level
        self.assertEqual(lvl['points'][0][1], 2.0)                           # the sound's own level until a gesture
        bend = next(x for x in tr['automation'] if x['target'] == 'instrument.pitchbend')
        self.assertEqual(bend['points'][0][1], 0.0)                          # in tune until the first scoop
        self.assertEqual(bend['points'][-1][1], 0.0)
        s2 = Song('x', tempo=100)
        s2.section('a', bars=4)
        t2 = s2.track('sax', {'type': 'sf2', 'params': {}})
        jazz.horn_line(self.MEL, 100, seed=1).place(t2, 0)
        self.assertIn('instrument.expression', {x['target'] for x in s2.compile()['tracks'][0]['automation']})
        with self.assertRaises(ComposeError):
            jazz.horn_line(self.MEL, 140, param='volume')

    def test_breathe_and_legato(self):
        c = Clip([(i, 1.0, 60 + i, 90) for i in range(12)], length=12)
        b = jazz.breathe(c, 120, breath_ms=200, max_phrase=8)
        gaps = [b[i + 1].start - (b[i].start + b[i].dur) for i in range(len(b) - 1)]
        self.assertTrue(any(g >= 0.4 - 1e-6 for g in gaps))                # a breath inside the long phrase
        lg = jazz.legato_phrases(Clip([(0, 0.4, 60, 90), (0.5, 0.4, 62, 90), (3, 1, 64, 90)], length=4))
        self.assertAlmostEqual(lg[0].dur, 0.52)
        self.assertAlmostEqual(lg[1].dur, 0.4)                              # before a rest: unchanged


class MelodyHelpers(unittest.TestCase):
    MEL = Clip([(0, 2, 'D4', 90), (2, 2, 'F4', 90), (4, 1, 'A4', 90), (5, 3, 'G4', 90), (9, 3, 'C5', 90)],
               length=12)

    def test_paraphrase(self):
        a = jazz.paraphrase(self.MEL, seed=1, key='Bb major')
        self.assertEqual(a, jazz.paraphrase(self.MEL, seed=1, key='Bb major'))
        self.assertTrue({n.pitch for n in self.MEL} <= {n.pitch for n in a})
        ant = jazz.paraphrase(self.MEL, seed=1, anticipate=1.0, delay=0.0, embellish=0.0)
        self.assertIn(1.5, [n.start for n in ant])                           # F4 on beat 3 came an 8th early
        emb = jazz.paraphrase(self.MEL, seed=2, anticipate=0.0, delay=0.0, embellish=1.0, key='Bb major')
        self.assertGreater(len(emb), len(self.MEL))
        self.assertTrue(all(n.start >= 0 for n in emb))

    def test_progressions_and_arg_checks(self):
        k = Key('Bb major')
        lengths = {n: k.prog(sp).length / 4 for n, sp in jazz.JAZZ_PROGRESSIONS.items()}
        self.assertEqual(lengths['blues'], 12)
        self.assertEqual(lengths['rhythm_a'], 8)
        self.assertTrue(all(v == int(v) for v in lengths.values()), lengths)
        self.assertEqual([c.symbol for c in k.prog(jazz.JAZZ_PROGRESSIONS['ii_v_i']).chords], ['Cm7', 'F7', 'Bbmaj7'])
        with self.assertRaises(ComposeError):
            jazz.paraphrase(self.MEL, anticipate=2)                  # validated even if never used
        kinds = set()
        for seed in range(8):
            enc = jazz.paraphrase(Clip([(0, 1.5, 'C4', 90), (2, 2, 'E4', 90)], length=4), seed=seed, anticipate=0,
                                  delay=0, embellish=1.0, key='C major')
            kinds.add(len(enc))
            ends = sorted((n.start, n.start + n.dur) for n in enc)
            for (a0, a1), (b0, _) in zip(ends, ends[1:]):
                self.assertLessEqual(a1, b0 + 1e-6, 'pickups never overlap the note before them')
            self.assertEqual(max(enc, key=lambda n: n.start).pitch, note('E4'))
        self.assertEqual(kinds, {3, 4})           # a chromatic pickup (Eb) or an enclosure (F Eb) before the E

    def test_solo_line(self):
        k = Key('Bb major')
        prog = k.prog('Imaj7 vi7 ii7 V7 | iii7 VI7 ii7 V7') * 2
        a = jazz.solo_line(prog, key=k, seed=3)
        self.assertEqual(a, jazz.solo_line(prog, key=k, seed=3))
        self.assertNotEqual(a, jazz.solo_line(prog, key=k, seed=4))
        self.assertEqual(a.length, prog.length)
        self.assertTrue(all(note('C4') <= n.pitch <= note('C6') for n in a))
        self.assertTrue(all(abs(n.start * 6 - round(n.start * 6)) < 1e-6 for n in a))    # 8th / triplet grid
        good = total = 0
        for n in a:
            if abs(n.start - round(n.start)) < 1e-9:
                c = prog.at(n.start)
                ok = {(c.root + i) % 12 for i in c.intervals} | set(guide_tones(c)) | \
                     {(c.root + t) % 12 for t in jazz.available_tensions(c)}
                total += 1
                good += n.pitch % 12 in ok
        self.assertGreater(good / total, 0.8)              # chord tones / tensions on the beats
        ph = jazz.phrases(a, gap=1.0)
        self.assertGreater(len(ph), 3)                     # phrases with room between them
        for p_ in ph:
            last = p_[-1]
            c = prog.at(last.start)
            self.assertIn(last.pitch % 12, {(c.root + i) % 12 for i in c.intervals} | set(guide_tones(c))
                          | {(c.root + t) % 12 for t in jazz.available_tensions(c)}, last)
        mot = Clip([(0, 0.5, 'D4', 90), (0.5, 0.5, 'F4', 90), (1.0, 1.0, 'A4', 90)], length=2)
        m = jazz.solo_line(prog, key=k, seed=5, motif=mot, motif_prob=1.0, register=('D4', 'D6'))
        firsts = [p_[:3] for p_ in jazz.phrases(m, gap=1.0) if len(p_) >= 3]
        self.assertTrue(any([round(x.start - f[0].start, 3) for x in f] == [0.0, 0.5, 1.0] for f in firsts))
        with self.assertRaises(ComposeError):
            jazz.solo_line(prog, density=3)
        with self.assertRaises(ComposeError):
            jazz.solo_line(prog, register=('C4', 'F4'))

    def test_block_chords_clip(self):
        prog = Progression('Bb6 Gm7 Cm7 F7', key='Bb major')
        mel = Clip([(0, 1, 'D5', 90), (1, 1, 'F5', 90), (4, 2, 'Bb4', 90), (12, 0.25, 'A4', 90)], length=16)
        bc = jazz.block_chords(mel, prog, style='locked', min_dur=0.5)
        tops = {}
        for n in bc:
            tops.setdefault(n.start, []).append(n.pitch)
        self.assertEqual(len(tops[0.0]), 5)
        self.assertEqual(max(tops[0.0]), note('D5'))
        self.assertEqual(len(tops[12.0]), 1)                                 # a short note stays single


class Band(unittest.TestCase):
    def test_band_setup_compiles(self):
        s = Song('band', tempo=150, key='F major')
        a = s.section('a', bars=4)
        b = jazz.band(s, sax=True)
        self.assertEqual({'comp', 'piano', 'bass', 'drums', 'sax'}, set(s.tracks))
        self.assertEqual({'room', 'plate'}, set(s.buses))
        self.assertIsNone(b.sax._groove)
        self.assertAlmostEqual(b.bass._groove.swing, swing_ratio(150))
        prog = s.prog('Fmaj7 D7 Gm7 C7')
        b.comp.play(jazz.comp(prog, seed=1), a)
        b.bass.play(jazz.walking_bass(prog, key=s.key, seed=1), a)
        b.drums.play(jazz.brushes(4, seed=1), a)
        b.piano.play(Clip([(0, 1, 'A4', 90)], length=4), a)
        jazz.horn_line(Clip([(0, 2, 'C5', 90)], length=4), 150, param='level').place(b.sax, a)
        d = s.compile()
        self.assertEqual(len(d['tracks']), 5)
        trio = Song('trio', tempo=120)
        trio.section('a', bars=1)
        t = jazz.band(trio, room=False, plate=False, ids={'comp': 'lh'})
        self.assertIsNone(t.sax)
        self.assertIn('lh', trio.tracks)
        self.assertFalse(trio.buses)

    def test_sampled_sounds(self):
        from unittest import mock
        import tempfile
        from agentsound import library
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(library, 'SAMPLES', pathlib.Path(tmp)):
                with self.assertRaises(ComposeError) as e:
                    jazz.sampled('piano')
                self.assertIn('samples fetch salamander-grand-v3-sf2', str(e.exception))
                pack, fname = jazz.SAMPLED_SOUNDS['sax'][:2]
                (pathlib.Path(tmp) / pack).mkdir()
                (pathlib.Path(tmp) / pack / fname).write_bytes(b'RIFF')
                i = jazz.sampled('sax', level=-1.0)
                self.assertEqual(i.params['mono'], 'on')
                self.assertEqual(i.params['level'], -1.0)
                self.assertTrue(i.params['file'].endswith(fname))
                s = Song('x', tempo=120)
                s.section('a', bars=1)
                with self.assertRaises(ComposeError):
                    jazz.band(s, sax=True, sampled_sounds=True)      # the piano pack is missing
        with self.assertRaises(ComposeError):
            jazz.sampled('bass')

    def test_demo_song_compiles(self):
        path = REPO / 'songs' / '_demo_jazz' / 'song.py'
        spec = importlib.util.spec_from_file_location('demo_jazz', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        s = mod.build()
        d = s.compile()
        self.assertEqual([x['name'] for x in d['sections']][:3], ['intro', 'A1', 'A2'])
        self.assertFalse([w for w in s.warnings if 'no notes' in w])


def same_pitch_overlaps(clip):
    """Notes of one pitch that start while an earlier note of that pitch still sounds (the instrument would play
    both voices at once: a doubled, phasey re-strike)."""
    by: dict[int, list] = {}
    for n in clip:
        by.setdefault(n.pitch, []).append(n)
    bad = []
    for ns in by.values():
        ns.sort(key=lambda n: n.start)
        bad += [(a, b) for a, b in zip(ns, ns[1:]) if b.start < a.start + a.dur - 1e-6]
    return bad


class ReviewRegressions(unittest.TestCase):
    """Defects found in review of the jazz toolkit."""

    PROG = Progression('Bbmaj7 Gm7 Cm7 F7 | Dm7:0.5 G7b9:0.5 Cm7:0.5 F7:0.5 Bbmaj7:0.5 G7alt:0.5 Cm7:0.5 F7:0.5 | '
                       'Ebmaj7 Ebm7:0.5 Ab7:0.5 Dm7 G7b9', key='Bb major')

    def test_comp_never_restrikes_a_held_chord(self):
        # a push on the & of 4 used to ring 1.25 beats into the next bar's & of 1 hit of the same chord
        for style in ('swing', 'charleston', 'garland', 'ballad', 'sparse', 'bossa'):
            for seed in range(12):
                for dens in (0.1, 0.5, 0.9):
                    c = jazz.comp(self.PROG, style=style, density=dens, seed=seed)
                    self.assertEqual(same_pitch_overlaps(c), [], (style, seed, dens))
        mel = Clip([(0, 1.5, 'D5', 90), (6, 1, 'F5', 90), (12, 2, 'A5', 90)], length=24)
        self.assertEqual(same_pitch_overlaps(jazz.comp(self.PROG, answer=mel, seed=1)), [])

    def test_so_what_on_sixth_chords_and_triads(self):
        # m6 used the minor root shape (with the b7); a triad's implied 6th rejected the real So What shape
        for sym in ('Cm6', 'Cm6/9', 'Fm6'):
            v = jazz.so_what(sym)
            self.assertEqual(check_voicing(sym, v), [], (sym, names(v)))
            self.assertNotIn((chord(sym).root + 10) % 12, pcs(v), sym)
        self.assertEqual([b - a for a, b in zip(jazz.so_what('C'), jazz.so_what('C')[1:])], [5, 5, 5, 4])
        self.assertEqual(pc_names(jazz.so_what('C')), {'E', 'A', 'D', 'G', 'B'})

    def test_strict_numbers(self):
        with self.assertRaises(ComposeError):
            jazz.walking_bass('C7', vel=float('nan'))
        with self.assertRaises(ComposeError):
            jazz.comp('C7', vel=200)
        with self.assertRaises(ComposeError):
            jazz.brushes('4')
        with self.assertRaises(ComposeError):
            jazz.ride_pattern(0)
        with self.assertRaises(ComposeError):
            jazz.brushes(2, ride='yes')
        with self.assertRaises(ComposeError):
            jazz.brush_fill('slap', 2, vel=(40, 300))
        with self.assertRaises(ComposeError):
            jazz.solo_line('C7', vel=0)
        with self.assertRaises(ComposeError):
            jazz.walking_bass('C7', gate=0)
        # derived levels are clamped, not errors: a hot brush part with the ride still builds
        hot = jazz.brushes(8, vel=3.0, ride=2.0, seed=1)
        self.assertTrue(all(1 <= n.vel <= 127 for n in hot))
        self.assertEqual(jazz.brushes(4, ride=0.0, seed=1), jazz.brushes(4, ride=False, seed=1))

    def test_sampled_piano_is_not_widened_out_of_phase(self):
        # the Salamander (spaced pair, low L/R correlation) measured 360 % wide / correlation -0.65 at sf2 width
        # 1.4 + band()'s 1.7 widener: sampled / passed-in pianos keep their own image
        self.assertLessEqual(jazz.SAMPLED_SOUNDS['piano'][2]['width'], 1.0)
        s = Song('w', tempo=120)
        s.section('a', bars=1)
        b = jazz.band(s, piano=jazz.inst.sf2('Grand Piano'))
        widths = [f.params['width'] for f in b.piano.fx if f.type == 'width']
        self.assertEqual(widths, [jazz.PIANO_WIDTH['other']])
        s2 = Song('w2', tempo=120)
        s2.section('a', bars=1)
        b2 = jazz.band(s2, sampled_sounds=False)
        self.assertEqual([f.params['width'] for f in b2.comp.fx if f.type == 'width'],
                         [jazz.PIANO_WIDTH['generaluser']])
        s3 = Song('w3', tempo=120)
        s3.section('a', bars=1)
        b3 = jazz.band(s3, piano_width=1.3)
        self.assertEqual([f.params['width'] for f in b3.piano.fx if f.type == 'width'], [1.3])
        with self.assertRaises(ComposeError):
            jazz.band(Song('w4', tempo=120), piano_width=3)


if __name__ == '__main__':
    unittest.main()
