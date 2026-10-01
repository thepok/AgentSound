"""agentsound.notation: the grammar (pitches, durations, rests / ties, bars, repeats, velocity, dynamics, marks,
ornaments, gestures, chords, tuplets, slurs, graces, voices, phrases), its error messages, the compatibility with
the formats songs used before (Motif strings, voicing.line, the ph() lines, grid lines), format() <-> notes() round
trips - over synthetic clips and over EVERY track of EVERY song (the expressiveness guard) - and the foundation
helpers that came with it (Clip.window / vel_add / arch / roll, harmonize keep / fit / fold, Song.at, (section,
beats) positions, automate(at=), track.cut / clear(cut=), Song.breath, fx['type'].set(), hold())."""

import importlib.util
import math
import os
import random
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from agentsound import (Clip, ComposeError, Key, Motif, Song, articulation as art, fx, hold, inst, midifx, notation,
                        notes, phrases, pianist, romantic, voicing)
from agentsound.notation import Line, format as fmt


def rows(c):
    return [(n.start, n.dur, n.pitch, n.vel, art.articulation_of(n), art.glide_of(n)) for n in c]


def key(c):
    return sorted(rows(c), key=lambda r: (r[0], r[2], r[1], r[3], str(r[4]), r[5] or 0))


class Pitches(unittest.TestCase):
    def test_absolute_and_enharmonics(self):
        c = notes('C4 C#4 Db4 Fb4 E#4 B#3 Cbb5 G9 C-1', dur='1/4')
        self.assertEqual([n.pitch for n in c], [60, 61, 61, 64, 65, 60, 70, 127, 0])

    def test_relative_octaves_nearest_letter(self):
        c = notes('C5/8 D E F G A B C D G, B C\' ')
        self.assertEqual([n.pitch for n in c], [72, 74, 76, 77, 79, 81, 83, 84, 86, 79, 83, 96])

    def test_relative_start_and_marks(self):
        self.assertEqual([n.pitch for n in notes('A C')], [57, 60])          # A nearest C4 (oct=4) is A3
        self.assertEqual([n.pitch for n in notes('A C', oct=5)], [69, 72])
        self.assertEqual([n.pitch for n in notes("C4'' E,")], [84, 76])

    def test_degrees_follow_motif(self):
        spec = '1 3 5 8 -1 b3 #4 9 bb7 12'
        self.assertEqual([n.pitch for n in notes(spec, key='F# minor')], Motif(spec, 'F# minor').pitches(4))
        self.assertEqual([n.pitch for n in notes("1 1' 1, 5", key='C major', oct=3)], [48, 60, 36, 55])

    def test_degree_needs_key(self):
        with self.assertRaisesRegex(ComposeError, "needs a key"):
            notes('1 3 5')

    def test_drums(self):
        self.assertEqual([n.pitch for n in notes('[kick hat]/16 hat snare hat')], [36, 42, 42, 38, 42])

    def test_not_a_pitch(self):
        with self.assertRaisesRegex(ComposeError, r"not a pitch: 'H4'"):
            notes('C4 H4')
        with self.assertRaisesRegex(ComposeError, "outside MIDI"):
            notes('G9 tr=+1 G9')


class Durations(unittest.TestCase):
    def test_note_values_and_sticky(self):
        c = notes('C4/4 D4 E4/8. F4/16 G4/2.. A4/8t B4 C5 D5:3/8 E5:1.5 F5')
        self.assertEqual([n.dur for n in c], [1, 1, 0.75, 0.25, 3.5, 1 / 3, 1 / 3, 1 / 3, 1.5, 1.5, 1.5])
        self.assertEqual(c.length, sum(n.dur for n in c))

    def test_non_sticky_like_motif(self):
        c = notes('C4/4 D4 E4', sticky=False, dur='1/8')
        self.assertEqual([n.dur for n in c], [1, 0.5, 0.5])

    def test_units(self):
        self.assertEqual([n.dur for n in notes('C4:3 D4:1', unit='1/8')], [1.5, 0.5])
        self.assertEqual([n.dur for n in notes('meter=6/8 unit=meter C4:3 D4')], [1.5, 1.5])

    def test_sounding_length(self):
        c = notes('C4/8:0.45 D4:0.5:0.3 E4/4')
        self.assertEqual([(n.start, n.dur) for n in c], [(0, 0.45), (0.5, 0.3), (1.0, 1.0)])
        c = notes('gate=0.9 C4/8 D4 gap=0.1 gate=1 E4/1')
        self.assertEqual([n.dur for n in c], [0.45, 0.45, 3.9])

    def test_rests_ties_holds(self):
        c = notes('C4/4 r D4/8 . E4 - | F4/2. G4/4~ | G4/4 A4/8 _ r/8 _ B4/4 |')
        self.assertEqual([(n.start, n.dur, n.pitch) for n in c],
                         [(0, 1, 60), (2, 0.5, 62), (3, 0.5, 64), (4, 3, 65), (7, 2, 67), (9, 1, 69), (11, 1, 71)])

    def test_tie_needs_a_partner(self):
        with self.assertRaisesRegex(ComposeError, "tie from C4 at beat 0 finds no C4 starting at beat 1"):
            notes('C4/4~ D4')
        with self.assertRaisesRegex(ComposeError, "holds the previous note"):
            notes('_ C4')


class Bars(unittest.TestCase):
    def test_checks_and_errors(self):
        notes('C4/1 | D4/2 E4 | F4/1 |')
        with self.assertRaisesRegex(ComposeError, r"bar 2 holds 3 beats at the bar line, the meter 4/4 wants 4 \(1 missing\)"):
            notes('C4/1 | D4/2 E4/4 | F4')
        with self.assertRaisesRegex(ComposeError, r"bar 1 is 0.5 beats too long"):
            notes('C4/1 D4/8 | E4')
        with self.assertRaisesRegex(ComposeError, r"bar 1 holds 1 beats.*pickup=1"):
            notes('C4/4 | D4/1')

    def test_pickup_and_meter(self):
        c = notes('G4/8 | C5/2. | D5', pickup=0.5, meter='3/4')
        self.assertEqual([n.start for n in c], [-0.5, 0, 3])
        with self.assertRaisesRegex(ComposeError, "pickup ends at beat -0.25"):
            notes('G4/16 | C5/1', pickup=0.5)
        notes('meter=3/4 C4/2. | meter=2/4 D4/2 | E4')        # a meter change at a bar line

    def test_left_out_bar_lines_are_fine(self):
        c = notes('C4/1 D4 | E4 F4 | G4')            # the second bar line skips one: still on the grid
        self.assertEqual(len(c), 5)

    def test_repeats(self):
        c = notes('|: C4/4 D4 E4 F4 :| G4/1')
        self.assertEqual([n.pitch for n in c], [60, 62, 64, 65] * 2 + [67])
        self.assertEqual(len(notes('|: C4/1 :|x3')), 3)
        self.assertEqual([n.start for n in notes('C4/16*4 [C4 E4]/8*2')], [0, 0.25, 0.5, 0.75, 1, 1, 1.5, 1.5])
        with self.assertRaisesRegex(ComposeError, "without a matching"):
            notes('C4 :|')


class Velocity(unittest.TestCase):
    def test_accents_ghosts_exact(self):
        c = notes('vel=100 C4 D4! E4!! F4? G4=33', accent=1.1, ghost=0.5)
        self.assertEqual([n.vel for n in c], [100, 110, 121, 50, 33])

    def test_dynamics_and_hairpins(self):
        L = romantic.LEVELS
        c = notes('vel=100 p C4/4 D4 < E4 F4 G4 A4 f B4 subito pp C5')
        v = [n.vel for n in c]
        self.assertEqual(v[:3], [round(100 * L['p'])] * 3)
        self.assertTrue(v[2] < v[3] < v[4] < v[5] < v[6])
        self.assertEqual(v[6], round(100 * L['f']))
        self.assertEqual(v[7], round(100 * L['pp']))
        d = [n.vel for n in notes('vel=100 ff C4 > D4 E4 p F4')]
        self.assertTrue(d[0] > d[2] > d[3])

    def test_sf_fp(self):
        c = notes('vel=90 C4 sfz D4 E4 fp F4 G4', sfz=1.3)
        self.assertEqual([n.vel for n in c], [90, 117, 90, round(90 * romantic.LEVELS['f']),
                                               round(90 * romantic.LEVELS['p'])])

    def test_dynamics_errors(self):
        with self.assertRaisesRegex(ComposeError, "no target mark"):
            notes('p C4 < D4')
        with self.assertRaisesRegex(ComposeError, "crescendo .* ends on 'p', which is softer"):
            notes('f C4 < D4 p E4')
        with self.assertRaisesRegex(ComposeError, "needs a target mark first"):
            notes('p C4 < D4 subito f E4')


class Marks(unittest.TestCase):
    def test_articulations_glides_peaks(self):
        c = notes('C4^staccato D4^"Short Spiccato" E4^ks(24) F4^gl(90) G4^gl A4^peak^pizz')
        self.assertEqual([art.articulation_of(n) for n in c], ['staccato', 'short spiccato', 24, None, None, 'pizz'])
        self.assertEqual([art.glide_of(n) for n in c], [None, None, None, 90.0, 120.0, None])
        self.assertEqual(c.peaks, [2.5])

    def test_label_args_rejected(self):
        with self.assertRaisesRegex(ComposeError, "an articulation label takes no arguments"):
            notes('C4^staccatto(3)')
        with self.assertRaisesRegex(ComposeError, "can't read"):
            notes('C4/4#')


class Ornaments(unittest.TestCase):
    def test_need_bpm(self):
        with self.assertRaisesRegex(ComposeError, r"\^trill is played in real time: give the tempo"):
            notes('C5/2^tr')

    def test_map_to_library_moves(self):
        k = Key('C major')
        c = notes('C5/2^tr', bpm=90, key='C major', vel=80)
        self.assertEqual(rows(c), rows(romantic.trill(72, 2.0, 90, at=0.0, key=k, vel=80)))
        c = notes('E5/1^turn(on)', bpm=60, key='C major', vel=70)
        self.assertEqual(rows(c), rows(romantic.turn(76, 4.0, 60, at=0.0, key=k, where='on', vel=70)))
        c = notes('D5/4^mord(upper)', bpm=120, vel=90)
        self.assertEqual(rows(c), rows(pianist.mordent(74, 1.0, 120, upper=True, vel=90)))
        c = notes('E5/4^crush', bpm=120, vel=90)
        self.assertEqual(rows(c), rows(pianist.crush(76, 1.0, 120, vel=90)))
        c = notes('[C4 E4 G4]/1^roll(60, down)', bpm=80, vel=88)
        self.assertEqual(rows(c), rows(pianist.roll([60, 64, 67], 4.0, 80, ms=60, direction='down', vel=88)))
        c = notes('[C4 E4 G4]/1^strum(30)', bpm=100)
        self.assertEqual(rows(c), rows(midifx.strum(notes('[C4 E4 G4]/1'), 30, 'down', bpm=100)))
        c = notes('{Bb5 Ab5 G5 F5 D5}/2^fig(rit)', bpm=50, vel=70)
        self.assertEqual(rows(c), rows(romantic.fioritura([82, 80, 79, 77, 74], 2.0, 50, shape='rit', vel=(70, 70))))

    def test_tempo_function_and_position(self):
        s = Song('t', tempo=60)
        s.section('a', bars=4)
        s.set_tempo(4, 120)
        c = notes('C5/2^tr', bpm=s.tempo_at, at=4, vel=80)
        self.assertEqual(rows(c), rows(romantic.trill(72, 2.0, s.tempo_at, at=4.0).shift(-4)))


class Groups(unittest.TestCase):
    def test_chords(self):
        c = notes('[C2:4 G3 C4=50]/4 [E4 G4]/2:0.9')
        self.assertEqual(rows(c)[:3], [(0, 4.0, 36, 96, None, None), (0, 1.0, 55, 96, None, None),
                                       (0, 1.0, 60, 50, None, None)])
        self.assertEqual([(n.start, n.dur) for n in c][3:], [(1, 0.9), (1, 0.9)])

    def test_tuplets(self):
        c = notes('{C5 D5 E5}/4 3:2{C5/8 D5 E5} {C5 D5 E5 F5 G5}/2 C5/4')
        st = [n.start for n in c]
        self.assertAlmostEqual(st[1], 1 / 3)
        self.assertAlmostEqual(st[4], 1 + 1 / 3)
        self.assertEqual(st[6], 2.0)
        self.assertAlmostEqual(st[7], 2 + 0.4)
        self.assertEqual(st[-1], 4.0)
        with self.assertRaisesRegex(ComposeError, "needs its span"):
            notes('{C5 D5 E5}')

    def test_slur_and_glides(self):
        c = notes('(C5/8 D5 E5 F5)^gl(80) G5/4', slur=0.03)
        self.assertEqual([round(n.dur, 6) for n in c], [0.53, 0.53, 0.53, 0.5, 1.0])
        self.assertEqual([art.glide_of(n) for n in c], [None, 80.0, 80.0, 80.0, None])

    def test_graces(self):
        c = notes('vel=100 C5/2 g:D5 E5/4 g:(B4 C5) D5', grace=0.1, gracevel=0.5)
        self.assertEqual([(round(n.start, 6), round(n.dur, 6), n.pitch, n.vel) for n in c],
                         [(0, 1.9, 72, 100), (1.9, 0.1, 74, 50), (2, 0.8, 76, 100), (2.8, 0.1, 71, 50),
                          (2.9, 0.1, 72, 50), (3, 1, 74, 100)])

    def test_voices(self):
        c = notes('S: C5/2 D5 | E5/1 |\nA: E4/1 | C4/2 B3 |')
        self.assertEqual(set(c.voices), {'S', 'A'})
        self.assertEqual([n.pitch for n in c.voices['A']], [64, 60, 59])
        self.assertEqual(len(c), 6)
        d = notes({'S': 'C5/1', 'A': 'E4/2 F4'})
        self.assertEqual(len(d.voices['A']), 2)
        with self.assertRaisesRegex(ComposeError, "bar 1 holds 3 beats"):
            notes('S: C5/1 | A: E4/2. |')

    def test_settings_positions_comments(self):
        c = notes('key=G_major oct=5 1/4 % a comment\n tr=+12 5 @8 st=1 1 vel=40 C4')
        self.assertEqual([(n.start, n.pitch, n.vel) for n in c], [(0, 79, 96), (1, 98, 96), (8, 93, 96), (9, 74, 40)])
        with self.assertRaisesRegex(ComposeError, "unknown setting 'vell'"):
            notes('vell=90 C4')
        with self.assertRaisesRegex(ComposeError, "unknown setting 'vell'"):
            notes('C4', vell=90)
        with self.assertRaisesRegex(ComposeError, "unclosed"):
            notes('[C4 E4')


class Phrases(unittest.TestCase):
    def setUp(self):
        self.H = phrases(a1='5/8 8 r 10 12/4.! 10/8', a2='11/4. 10/8 9/2', c4='_/2 5/8 8 r 10',
                         key='F# minor', gate=0.92, vel=104)

    def test_composition_matches_motif_concatenation(self):
        line = self.H('a1 a2 | c4')
        m = Motif('5:1/8 8:1/8 r:1/8 10:1/8 12:1/4.! 10:1/8 11:1/4. 10:1/8 9:1/2 _:1/2 5:1/8 8:1/8 r:1/8 10:1/8',
                  'F# minor').clip(octave=4, vel=104)
        self.assertEqual(rows(line), rows(m))
        self.assertEqual(line.length, m.length)

    def test_transpositions_and_repeats(self):
        base = [n.pitch for n in self.H['a1']]
        self.assertEqual([n.pitch for n in self.H("a1+12")], [p + 12 for p in base])
        self.assertEqual([n.pitch for n in self.H("a1'")], [p + 12 for p in base])
        up = [n.pitch for n in self.H('a1+2d')]
        k = Key('F# minor')
        self.assertEqual(up, [k.transpose(p, 2) for p in base])
        self.assertEqual(len(self.H('a1*2')), 2 * len(base))
        self.assertEqual(self.H('a1 a1').length, 8)

    def test_variant_and_errors(self):
        H = phrases(x='C4/1 | D4 | E4', vel=90)
        v = H.variant('y', 'x', {2: 'F4/2 G4'})
        self.assertEqual([n.pitch for n in v], [60, 65, 67, 64])
        with self.assertRaisesRegex(ComposeError, "unknown phrase|not a pitch"):
            H('x zz')
        H.add(loop='$loop')
        with self.assertRaisesRegex(ComposeError, "refers to itself"):
            H('loop')
        with self.assertRaisesRegex(ComposeError, "word of the notation"):
            phrases(kick='C4')


class OlderFormats(unittest.TestCase):
    """Every note format songs used before is expressible: the notation reproduces it exactly."""

    def test_motif_strings(self):
        k = 'F# minor'
        for spec in ('5:1/8 8:1/8 r:1/8 10:1/8 12:1/4.! 10:1/8', 'r:1/2 1:1/8 4:1/8 r:1/8 6:1/8 | 8:1/2. r:1/4',
                     '_:1/2 5:1/8 8:1/8 r:1/8 10:1/8', '#7:1/2. r:1/4 -1:1/4 b3:1/8? 4:1/8'):
            m = Motif(('1:1/4 ' if spec.startswith('_') else '') + spec, k).clip(octave=4, vel=96)
            c = notes(('1:1/4 ' if spec.startswith('_') else '') + spec, key=k, gate=0.92, sticky=False, vel=96)
            self.assertEqual(rows(c), rows(m), spec)

    def test_voicing_line(self):
        spec = 'D4:1 A4:.5 r:1 F4:1.5 | E4:2'
        c = notes(spec)
        self.assertEqual([(n.start, n.dur, n.pitch) for n in c], voicing.line(spec))

    def test_ph_lines(self):
        """The ph() of perry-street-rain / minetta-lane-waltz / lanterns-on-carmine: len in 8ths, g: graces,
        ! / ? factors, triplets (lanterns: /t, /2t)."""
        def ph(spec, vel=90, acc=(1.1, 0.72), g=0.1, gv=0.72, bpb=4.0):
            t, mark, grace, out = 0.0, 0.0, None, []
            for tok in spec.replace('|', ' | ').split():
                if tok == '|':
                    mark += bpb
                    continue
                if tok.startswith('g:'):
                    grace = tok[2:]
                    continue
                a = acc[0] ** tok.count('!') * acc[1] ** tok.count('?')
                tok = tok.replace('!', '').replace('?', '')
                p, _, d = tok.partition('/')
                dur = 0.5 if not d else (float(d[:-1] or 1) / 3.0 if d.endswith('t') else float(d) * 0.5)
                if p != 'r':
                    if grace:
                        if out and out[-1][0] + out[-1][1] > t - g:
                            out[-1][1] = max(0.08, t - g - out[-1][0])
                        out.append([t - g, g, grace, vel * gv])
                    out.append([t, dur, p, vel * a])
                grace = None
                t += dur
            return Clip([(s, d, p, max(1, min(127, int(round(v))))) for s, d, p, v in out],
                        length=max(bpb, -(-t // bpb) * bpb))
        old = ph('r/2 C5 Eb5! G5/3 F5? | Eb5/2 C5 Bb4 r C5 g:F5 G5 F5 | Db5/2 Ab4/2 r G4 Bb4 E5')
        new = notes('r/4 C5/8 Eb5! G5/4. F5/8? | Eb5/4 C5/8 Bb4 r C5 g:F5 G5 F5 | Db5/4 Ab4 r/8 G4 Bb4 E5',
                    vel=90, accent=1.1, ghost=0.72, length='bar')
        self.assertEqual(rows(new), rows(old))
        old = ph('G4/t A4/t B4/t C5/2t D5/2t E5/2t F5/4', acc=(1.12, 0.7), g=0.11, gv=0.78)
        new = notes('G4/8t A4 B4 C5/4t D5 E5 F5/2', vel=90, length='bar', grace=0.11, gracevel=0.78)
        # triplets: ph() adds 1/3 in floats, the notation counts exactly - the same numbers to 1e-15
        self.assertEqual(len(new), len(old))
        for a, b in zip(rows(new), rows(old)):
            self.assertAlmostEqual(a[0], b[0], places=12)
            self.assertEqual(a[1:], b[1:])
        old = ph('D5/2 B4/2 G4/2 | A4/6', bpb=3.0)
        new = notes('D5/4 B4 G4 | A4/2.', vel=90, meter='3/4', length='bar')
        self.assertEqual(rows(new), rows(old))

    def test_grid_lines(self):
        """chrome-leviathan's line(): one token per step, '.' rest, '_' hold, ! / ? absolute levels, gate."""
        def line(spec, step=0.25, vel=100, gate=0.9, acc=118, gh=62):
            out, t = [], 0.0
            for tok in spec.split():
                if tok == '.':
                    pass
                elif tok == '_':
                    out[-1] = (out[-1][0], out[-1][1] + step, out[-1][2], out[-1][3])
                else:
                    v = acc if tok.endswith('!') else gh if tok.endswith('?') else vel
                    out.append((t, step, tok.rstrip('!?'), v))
                t += step
            return Clip([(a, d * gate, p, v) for a, d, p, v in out], length=t)
        old = line('. C#2 C#2 C#2! . C#2 _ C#3 . C#2? C#2 C#2! _ _ B2 G#2')
        new = notes('dur=1/16 gate=0.9 . C#2 C#2 C#2=118 . C#2 _ C#3 . C#2=62 C#2 C#2=118 _ _ B2 G#2', vel=100)
        self.assertEqual(rows(new), rows(old))
        self.assertEqual(new.length, old.length)


class Format(unittest.TestCase):
    def roundtrip(self, c, **kw):
        text = fmt(c, **kw)
        back = notes(text, length=c.length)
        self.assertEqual(key(back), key(c), text)
        self.assertEqual(back.length, c.length)
        return text

    def test_readable_melody(self):
        c = notes('vel=92 C5/8 Eb5 G5/4. F5/8 D5/4 | Eb5/2 C5/4 r')
        self.assertEqual(self.roundtrip(c, key='C minor'), 'vel=92\nC5 Eb5 G5/4. F5/8 D5/4 | Eb5/2 C5/4 r |')

    def test_gate_and_rests(self):
        m = Motif('5:1/8 8:1/8 r:1/8 10:1/8 12:1/4.! 10:1/8', 'F# minor').clip(octave=4, vel=104)
        text = self.roundtrip(m)
        self.assertIn('gate=0.92', text)

    def test_humanized_chords_marks_negative_tiny(self):
        rng = random.Random(5)
        ns = []
        for i in range(60):
            t = i * 0.5 + rng.uniform(-0.03, 0.03)
            ns.append(art.note(t, rng.uniform(0.0004, 2.2), rng.randint(30, 90), rng.randint(1, 127),
                               art=rng.choice([None, 'staccato', 'short spiccato', 24, 'trill']),
                               glide_ms=rng.choice([None, 90.0, 33.3])))
            if i % 7 == 0:
                ns.append(art.note(t, rng.uniform(0.1, 3), rng.randint(30, 90), 77))
        ns.append(art.note(-0.5, 0.25, 60, 50))
        c = Clip._raw(ns, 32.0)
        self.roundtrip(c)
        self.roundtrip(c, drums=True)

    def test_drums_and_tracks(self):
        s = Song('t', tempo=120)
        sec = s.section('a', bars=2)
        kit = s.track('kit', inst.drums())
        kit.play(notes('[kick hat]/8 hat [snare hat] hat=70 ' * 2), sec)
        text = fmt(kit)
        self.assertIn('kick', text)
        self.assertEqual(key(notes(text, length=s.length)), key(Clip._raw(kit._notes, s.length)))


@unittest.skipUnless(any((Path(os.environ.get('AGENTSOUND_SAMPLES') or REPO / 'assets' / 'samples')).glob('*/SOURCE.json')),
                     'the sample library is not installed (songs need it to build)')
class EverySong(unittest.TestCase):
    """The expressiveness guard: every track of every song - its placed notes (with articulation / glide marks)
    and its compiled notes - goes through format() and back unchanged."""

    SKIP = {'kestrel-bay', 'afterglow-express', 'last-table-on-hudson', 'last-train-blue-hour'}

    def test_round_trip(self):
        from agentsound import cli
        songs = sorted(p.parent for p in (REPO / 'songs').glob('*/song.py') if p.parent.name not in self.SKIP)
        self.assertGreater(len(songs), 15)
        clips = 0
        for d in songs:
            for m in [m for m in sys.modules if m in ('score', 'film', 'measure', 'satie_score')]:
                del sys.modules[m]
            song, _ = cli._load_song((d / 'song.py').resolve())
            cli.apply_module_mix(song)
            compiled = {t['id']: t['notes'] for t in song.compile()['tracks']}
            for t in song.tracks.values():
                for label, c, drums in (('notes', Clip._raw(list(t._notes), song.length),
                                         t.instrument.type == 'drums'),
                                        ('compiled', Clip._raw([art.Note(*n) for n in compiled[t.id]], song.length),
                                         False)):
                    text = fmt(c, drums=drums)
                    back = notes(text, length=c.length)
                    self.assertEqual(key(back), key(c), f"{d.name}/{t.id} ({label}) does not round-trip")
                    clips += 1
        self.assertGreater(clips, 300)


class Helpers(unittest.TestCase):
    def song(self):
        s = Song('h', tempo=100)
        self.a, self.b, self.c = s.section('a', bars=2), s.section('b', bars=2), s.section('c', bars=2)
        return s

    def test_window_vel_add_arch_roll(self):
        c = notes('C4/4 D4 E4 F4 | G4 A4 B4 C5')
        w = c.window(2, 6)
        self.assertEqual([n.start for n in w], [2, 3, 4, 5])
        self.assertEqual(w.length, c.length)
        self.assertEqual([n.vel for n in c.vel_add(40)], [127] * 8)
        self.assertEqual([n.vel for n in c.vel_add(-200)], [1] * 8)
        arc = c.with_vel(100).arch(bars=2, depth=0.3)
        want = [max(30, min(120, round(100 * (1 - 0.15 + 0.3 * math.sin(math.pi * ((n.start % 8) / 8) ** 0.8)))))
                for n in c]
        self.assertEqual([n.vel for n in arc], want)
        ch = notes('[C4 E4 G4]/1 [D4 F4 A4]')
        r = random.Random(3)
        ms = random.Random(3).uniform(8, 22)
        self.assertEqual(rows(ch.roll((8, 22), seed=r, bpm=90)), rows(ch.strum(ms=ms, bpm=90, direction='up')))

    def test_harmonize_keep_fit_fold(self):
        line = notes('A4/4 B4 C5 G#4', vel=100)
        v = line.harmonize('-3rd', key='A minor', keep=False, vel=1)
        self.assertEqual([n.pitch for n in v], [65, 67, 69, 65])
        self.assertEqual([n.vel for n in v], [100] * 4)
        self.assertEqual(len(line.harmonize('-3rd', key='A minor')), 8)
        prog = Song('x', key='A minor').prog('Am E')
        f = line.harmonize('-3rd', key='A minor', keep=False, fit=prog)
        self.assertTrue(all(n.pitch % 12 in prog.at(n.start).pcs for n in f))
        lo = line.harmonize('-3rd', key='A minor', keep=False, fold=('C5', 'B5'))
        self.assertTrue(all(72 <= n.pitch <= 83 for n in lo))

    def test_positions_at_and_automate_at(self):
        s = self.song()
        self.assertEqual(s.at(self.b, 2.5), 10.5)
        self.assertEqual(s.at((self.b, 2.5)), 10.5)
        self.assertEqual(s.at(('c', -1)), 15.0)
        t = s.track('t', inst.va())
        t.note('C4', (self.b, 1), 1)
        self.assertEqual(t.notes[0].start, 9.0)
        t.automate('pan', [(0, 0.0), (2, 0.5)], at=self.c)
        self.assertEqual(t._auto[-1][1], [(16.0, 0.0), (18.0, 0.5)])

    def test_cut_clear_breath(self):
        s = self.song()
        pad, riser = s.track('pad', inst.va()), s.track('riser', inst.va())
        pad.play(hold('C4 E4', 12, 80), 0).note('G4', 7, 2)
        riser.note('A3', 0, 8)
        pad.clear(7, 8)
        self.assertEqual([n.dur for n in pad.notes], [12, 12])            # clear alone leaves them ringing
        pad.clear(7, 8, cut=True)
        self.assertEqual([n.dur for n in pad.notes], [7, 7])
        pad.play(hold('C4', 8), 8).cut(12)
        self.assertEqual(pad.notes[-1].dur, 4)
        s.breath(before=[self.c], beats=1, keep=[riser])
        self.assertTrue(all(n.start + n.dur <= 15 + 1e-9 for n in pad.notes))
        self.assertEqual(riser.notes[0].dur, 8)
        with self.assertRaisesRegex(ComposeError, "no track 'nope'"):
            s.breath(before=self.c, keep=['nope'])

    def test_fx_chain_access(self):
        s = self.song()
        t = s.track('t', inst.va(), fx=[fx.compressor(attack=5), fx.eq({'low.gain': 1}), fx.eq({'high.gain': 2})])
        t.fx['compressor'].set(attack=25)
        self.assertEqual(t.fx['compressor'].params['attack'], 25)
        t.fx[1].set({'peak1.gain': -3})
        self.assertEqual(t.fx[1].params['peak1.gain'], -3)
        with self.assertRaisesRegex(ComposeError, "2 'eq' effects"):
            t.fx['eq']
        with self.assertRaisesRegex(ComposeError, "no effect named or of type 'reverb'"):
            t.fx['reverb']
        t.fx = list(t.fx) + [fx.limiter(gain=1)]
        self.assertEqual(t.fx.index_of('limiter'), 3)
        s.master.add(fx.limiter())
        s.master.fx['limiter'].set(gain=5.2)
        self.assertEqual(s.master.compile_gain if False else s.master.fx[-1].params['gain'], 5.2)

    def test_hold_both_ways(self):
        self.assertEqual(hold(0, 4, 3), [(0.0, 3, 'step'), (4.0, 3)])
        h = hold('Ab2=60 Eb3 G3', 7.9, 50, length=8, at=0)
        self.assertEqual([(n.start, n.dur, n.pitch, n.vel) for n in h], [(0, 7.9, 44, 60), (0, 7.9, 51, 50),
                                                                         (0, 7.9, 55, 50)])
        self.assertEqual(h.length, 8)
        self.assertEqual([n.start for n in hold('C4 E4', 2, at=6)], [6, 6])
        with self.assertRaisesRegex(ComposeError, "need a value"):
            hold(0, 4)

    def test_gestures_reach_the_track(self):
        s = self.song()
        t = s.track('lead', inst.va())
        line = notes('C5/2^scoop D5/2^fall(-2) | E5/1^vib')
        self.assertEqual([g['kind'] for g in line.gestures], ['scoop', 'fall', 'vib'])
        t.play(line, self.b)
        lane = [p for tgt, pts in t._auto if tgt == 'instrument.pitchbend' for p in pts]
        self.assertTrue(lane and min(p[1] for p in lane) < -0.5)
        self.assertTrue(any(8 <= p[0] < 9 for p in lane))
        s.compile()
        t2 = s.track('lead2', inst.va())
        t2.loop(notes('C5/1^scoop'), self.a)
        self.assertEqual(sum(1 for tgt, _ in t2._auto if tgt == 'instrument.pitchbend'), 2)


class WrittenOrnaments(unittest.TestCase):
    """notes(expand=False): the ornaments as written, for a player that realizes them its own way (romantic.score)."""

    def test_listed_not_played(self):
        line = notes('unit=1/8 F5:3^tr(lower=-1) G5:2 [C6 C7]:1!^roll(60) {F5 G5 F5 E5}:3^fig(even)', expand=False)
        self.assertEqual([(n.start, n.pitch) for n in line], [(1.5, 79)])          # the ornaments' notes left out
        self.assertEqual([(o['kind'], o['start'], o['dur'], o['pitches'], o['args'], o['kw']) for o in line.ornaments],
                         [('trill', 0.0, 1.5, [77], [], {'lower': -1}), ('roll', 2.5, 0.5, [84, 96], [60], {}),
                          ('fig', 3.0, 1.5, [77, 79, 77, 76], ['even'], {})])
        self.assertEqual(line.ornaments[1]['vel'], round(96 * 1.2))
        moved = line.shift(2.0)
        self.assertEqual([o['start'] for o in moved.ornaments], [2.0, 4.5, 5.0])
        self.assertEqual(moved.ornaments[0]['notes'][0].start, 2.0)
        expanded = notes('unit=1/8 F5:3^tr(lower=-1) G5:2', bpm=60)                 # the default: played
        self.assertGreater(len(expanded), 2)
        self.assertEqual(expanded.ornaments, [])
        with self.assertRaisesRegex(ComposeError, 'real time'):
            notes('F5/2^tr')


if __name__ == '__main__':
    unittest.main()
