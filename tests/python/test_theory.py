import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound.theory import (ComposeError, Chord, Key, Progression, chord, note, note_name, pc, scale, voice,
                               voice_lead)


class NoteNames(unittest.TestCase):
    def test_names_to_midi(self):
        cases = {'C4': 60, 'C#4': 61, 'Db4': 61, 'Bb2': 46, 'A4': 69, 'C-1': 0, 'G9': 127, 'B3': 59,
                 'Cb4': 59, 'E#4': 65, 'f#3': 54}
        for name, midi in cases.items():
            self.assertEqual(note(name), midi, name)

    def test_midi_to_names(self):
        self.assertEqual(note_name(61), 'C#4')
        self.assertEqual(note_name(61, flats=True), 'Db4')
        self.assertEqual(note_name(46, flats=True), 'Bb2')
        self.assertEqual(note_name(0), 'C-1')

    def test_bad_notes(self):
        for bad in ('H4', 'C', '', 128, -1, 'A10', 3.5, True):
            with self.assertRaises(ComposeError, msg=repr(bad)):
                note(bad)

    def test_pitch_class(self):
        self.assertEqual(pc('Bb'), 10)
        self.assertEqual(pc('F#'), 6)
        self.assertEqual(pc('A4'), 9)
        self.assertEqual(pc(61), 1)


class ChordSymbols(unittest.TestCase):
    # symbol -> exact root-position pitches with the root in octave 4 (slash bass below)
    CASES = {
        'Am': [69, 72, 76],
        'Am7': [69, 72, 76, 79],
        'Am9': [69, 72, 76, 79, 83],
        'Fmaj7': [65, 69, 72, 76],
        'Fmaj7/A': [57, 65, 69, 72, 76],
        'Gsus4': [67, 72, 74],
        'Gsus2': [67, 69, 74],
        'G7sus4': [67, 72, 74, 77],
        'C/E': [52, 60, 64, 67],
        'Bdim': [71, 74, 77],
        'Bdim7': [71, 74, 77, 80],
        'Bm7b5': [71, 74, 77, 81],
        'Bø7': [71, 74, 77, 81],
        'E7b9': [64, 68, 71, 74, 77],
        'E7#9': [64, 68, 71, 74, 79],
        'Dm11': [62, 65, 69, 72, 76, 79],
        'Cadd9': [60, 64, 67, 74],
        'Cmadd9': [60, 63, 67, 74],
        'C6': [60, 64, 67, 69],
        'Cm6': [60, 63, 67, 69],
        'C6/9': [60, 64, 67, 69, 74],
        'C5': [60, 67],
        'C': [60, 64, 67],
        'C7': [60, 64, 67, 70],
        'C9': [60, 64, 67, 70, 74],
        'C13': [60, 64, 67, 70, 74, 81],
        'Cmaj9': [60, 64, 67, 71, 74],
        'CM7': [60, 64, 67, 71],
        'CΔ7': [60, 64, 67, 71],
        'C-7': [60, 63, 67, 70],
        'Cmin7': [60, 63, 67, 70],
        'Cm(maj7)': [60, 63, 67, 71],
        'CmMaj7': [60, 63, 67, 71],
        'C+': [60, 64, 68],
        'Caug7': [60, 64, 68, 70],
        'C7#5': [60, 64, 68, 70],
        'C7b5': [60, 64, 66, 70],
        'Cmaj7#11': [60, 64, 67, 71, 78],
        'C°': [60, 63, 66],
        'Bb': [70, 74, 77],
        'F#m7b5': [66, 69, 72, 76],
        'Ebmaj7': [63, 67, 70, 74],
        'Am/G': [55, 69, 72, 76],
    }

    def test_exact_pitches(self):
        for sym, want in self.CASES.items():
            self.assertEqual(chord(sym).notes(4), want, sym)

    def test_symbol_roundtrip_and_props(self):
        c = chord('Fmaj7/A')
        self.assertEqual(c.symbol, 'Fmaj7/A')
        self.assertEqual(c.root, 5)
        self.assertEqual(c.bass_pc, 9)
        self.assertEqual(c.pcs, frozenset({5, 9, 0, 4}))
        self.assertTrue(chord('Am').is_minor)
        self.assertEqual(chord('Am7').transpose(2).symbol, 'Bm7')

    def test_bad_symbols(self):
        for bad in ('Hm', 'am', 'Cxyz', 'C7xyz', '', 'C5add9', 'C3'):
            with self.assertRaises(ComposeError, msg=bad):
                chord(bad)

    def test_bass_note_extraction(self):
        self.assertEqual(chord('C/E').bass_note('E1'), 28)
        self.assertEqual(chord('Am').bass_note('E1'), 33)
        self.assertEqual(chord('D').bass_note('E1'), 38)
        self.assertEqual(chord('Fmaj7/A').bass_note('C2'), 45)


def _same(c: Chord, sym: str) -> bool:
    o = chord(sym)
    return c.root == o.root and c.pcs == o.pcs and c.bass_pc == o.bass_pc


class RomanNumerals(unittest.TestCase):
    def test_major(self):
        k = Key('C major')
        cases = {'I': 'C', 'ii': 'Dm', 'iii': 'Em', 'IV': 'F', 'V': 'G', 'vi': 'Am', 'vii°': 'Bdim',
                 'V7': 'G7', 'ii7': 'Dm7', 'Imaj7': 'Cmaj7', 'bVII': 'Bb', 'bVI': 'Ab', 'bIII': 'Eb',
                 'iv': 'Fm', 'V7/V': 'D7', 'V/vi': 'E', 'viiø7': 'Bm7b5', 'IVadd9': 'Fadd9', 'Vsus4': 'Gsus4'}
        for num, sym in cases.items():
            self.assertTrue(_same(k.chord(num), sym), f"{num} -> {k.chord(num)} != {sym}")

    def test_minor(self):
        k = Key('A minor')
        cases = {'i': 'Am', 'ii°': 'Bdim', 'III': 'C', 'iv': 'Dm', 'v': 'Em', 'V': 'E', 'VI': 'F', 'VII': 'G',
                 'bVII': 'G', 'bVI': 'F', 'bIII': 'C', 'iv7': 'Dm7', 'V7': 'E7', 'i9': 'Am9', 'VImaj7': 'Fmaj7',
                 'V7/iv': 'A7'}
        for num, sym in cases.items():
            self.assertTrue(_same(k.chord(num), sym), f"{num} -> {k.chord(num)} != {sym}")

    def test_modes_and_bad(self):
        self.assertTrue(_same(Key('D dorian').chord('IV'), 'G'))
        self.assertTrue(_same(Key('E phrygian').chord('II'), 'F'))
        with self.assertRaises(ComposeError):
            Key('C major').chord('IVxyz')

    def test_diatonic_sevenths(self):
        got = [c.symbol for c in Key('C major').chords(seventh=True)]
        self.assertEqual(got, ['Cmaj7', 'Dm7', 'Em7', 'Fmaj7', 'G7', 'Am7', 'Bm7b5'])


class KeysAndScales(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(Key('Am').name, 'A minor')
        self.assertEqual(Key('F# dorian').intervals, (0, 2, 3, 5, 7, 9, 10))
        self.assertEqual(Key('Eb').name, 'Eb major')
        self.assertEqual(Key('C', 'harmonic minor').intervals, (0, 2, 3, 5, 7, 8, 11))
        self.assertEqual(len(scale('minor pentatonic')), 5)
        self.assertEqual(scale('blues'), (0, 3, 5, 6, 7, 10))
        with self.assertRaises(ComposeError):
            Key('A funky')

    def test_degrees(self):
        k = Key('A minor')
        self.assertEqual(k.degree(1), 69)
        self.assertEqual(k.degree(3), 72)
        self.assertEqual(k.degree(8), 81)
        self.assertEqual(k.degree(-1), 67)
        self.assertEqual(k.degree(1, octave=2), 45)
        with self.assertRaises(ComposeError):
            k.degree(0)

    def test_scale_ops(self):
        c = Key('C major')
        self.assertEqual(c.transpose(60, 2), 64)
        self.assertEqual(c.transpose(64, -2), 60)
        self.assertEqual(c.transpose(61, 1), 63)  # chromatic alteration is kept
        self.assertEqual(c.snap(61), 60)
        self.assertEqual(c.snap(61, 1), 62)
        self.assertTrue(c.contains('E4'))
        self.assertFalse(c.contains('Eb4'))
        self.assertEqual(Key('A minor pentatonic').degree(6), 81)


class Voicings(unittest.TestCase):
    def test_styles(self):
        self.assertEqual(voice('Cmaj7', 'close'), [60, 64, 67, 71])
        self.assertEqual(voice('C', 'close', inversion=1), [64, 67, 72])
        self.assertEqual(voice('Cmaj7', 'drop2'), [55, 60, 64, 71])
        self.assertEqual(voice('Cmaj7', 'open'), [60, 67, 76, 83])
        self.assertEqual(voice('Am7', 'spread'), [57, 64, 72, 79])
        self.assertEqual(voice('C/E', 'close'), [52, 60, 64, 67])
        v = voice('Cmaj9', 'close', register=(48, 72))
        self.assertTrue(all(48 <= p <= 72 for p in v), v)
        self.assertEqual(len(voice('C', 'close', voices=4)), 4)
        with self.assertRaises(ComposeError):
            voice('C', 'weird')

    def test_voice_leading_is_smooth(self):
        seq = ['Am', 'F', 'C', 'G', 'Am', 'Dm7', 'E7', 'Am']
        vs = voice_lead(seq, register=(52, 76), voices=4)
        for sym, v in zip(seq, vs):
            c = chord(sym)
            self.assertEqual(len(v), 4)
            self.assertTrue(all(52 <= p <= 76 for p in v), v)
            self.assertEqual(v, sorted(v))
            self.assertIn(c.root, {p % 12 for p in v})
            third = [i for i in c.intervals if i in (3, 4)][0]
            self.assertIn((c.root + third) % 12, {p % 12 for p in v}, sym)
        moves = [sum(abs(a - b) for a, b in zip(x, y)) for x, y in zip(vs, vs[1:])]
        self.assertLessEqual(max(moves), 8, moves)
        # much smoother than parallel root-position triads
        naive = [voice(c, 'close', voices=4) for c in seq]
        naive_moves = [sum(abs(a - b) for a, b in zip(x, y)) for x, y in zip(naive, naive[1:])]
        self.assertLess(sum(moves), sum(naive_moves))

    def test_narrow_register_doubles_any_tone(self):
        # Regression: F in 55..76 has room for one F only; it used to raise "can't voice F with 4 voices"
        # because the doubled tone (root) was fixed before the search. A3-C4-F4-A4 fits (third doubled).
        from agentsound.patterns import chords
        k = Key('A minor')
        c = chords(k.prog('i VI'), voicing='smooth', register=(55, 76))
        am = sorted(n.pitch for n in c if n.start == 0)
        f = sorted(n.pitch for n in c if n.start == 4)
        for v, ch in ((am, chord('Am')), (f, chord('F'))):
            self.assertEqual(len(v), 4)
            self.assertEqual(len(set(v)), 4, v)
            self.assertTrue(all(55 <= p <= 76 for p in v), v)
            self.assertEqual({p % 12 for p in v}, set(ch.pcs), v)
        self.assertLessEqual(sum(abs(a - b) for a, b in zip(am, f)), 2)       # smooth: one voice moves a step
        vs = voice_lead(['Am', 'F', 'C', 'G', 'Dm', 'E', 'Am'], register=(55, 76), voices=4)
        for sym, v in zip(['Am', 'F', 'C', 'G', 'Dm', 'E', 'Am'], vs):
            self.assertEqual({p % 12 for p in v}, set(chord(sym).pcs), (sym, v))
        moves = [sum(abs(a - b) for a, b in zip(x, y)) for x, y in zip(vs, vs[1:])]
        self.assertLessEqual(max(moves), 6, moves)

    def test_doubling_preference(self):
        from agentsound.theory import _candidates
        # root preferred, then fifth, then third; a doubled 7th costs more still
        cands = dict(_candidates(chord('C'), 48, 72, 4, None))
        self.assertEqual(cands[(48, 60, 64, 67)], 0.0)          # root doubled
        self.assertEqual(cands[(55, 60, 64, 67)], 0.4)          # fifth doubled
        self.assertEqual(cands[(52, 60, 64, 67)], 1.0)          # third doubled
        g7 = dict(_candidates(chord('G7'), 48, 72, 5, None))
        self.assertLess(g7[(55, 59, 62, 65, 67)], g7[(53, 55, 59, 62, 65)])
        # with room for every doubling, the first chord doubles the root
        v = voice_lead(['C'], register=(48, 72), voices=4)[0]
        self.assertEqual(sum(1 for p in v if p % 12 == 0), 2, v)
        v5 = voice_lead(['C5'], register=(52, 76), voices=4)[0]
        self.assertEqual({p % 12 for p in v5}, {0, 7})
        with self.assertRaises(ComposeError):
            voice_lead(['C'], register=(60, 71), voices=6)     # only 3 chord-tone pitches fit

    def test_voice_lead_bass(self):
        vs = voice_lead(['C/E', 'F'], voices=3, bass=True)
        self.assertEqual(vs[0][0] % 12, 4)
        self.assertLess(vs[0][0], vs[0][1])


class Progressions(unittest.TestCase):
    def test_parse_lengths(self):
        k = Key('A minor')
        p = k.prog('i:2 VI III VII | % r iv:0.5 V7:1.5')
        self.assertEqual([c.symbol if c else None for c in p.chords], ['Am', 'F', 'C', 'G', None, 'Dm', 'E7'])
        self.assertEqual([d for _, d in p.items], [8, 4, 4, 8, 4, 2, 6])
        self.assertEqual(p.length, 36)
        self.assertEqual(p.at(9).symbol, 'F')
        self.assertEqual([s for s, _, _ in p][:3], [0, 8, 12])

    def test_symbols_need_no_key_but_romans_do(self):
        self.assertEqual(len(Progression('Am F C G')), 4)
        with self.assertRaises(ComposeError):
            Progression('i VI')
        p = Progression([('Am', 2), 'F', chord('G')], beats_per_bar=3)
        self.assertEqual(p.length, 12)

    def test_transforms(self):
        p = Progression('Am F') * 2 + Progression('G')
        self.assertEqual(len(p), 5)
        self.assertEqual(p.transpose(2).chords[0].symbol, 'Bm')
        roots = Progression('C/E G').roots('E1')
        self.assertEqual([r for _, _, r in roots], [28, 31])


if __name__ == '__main__':
    unittest.main()
