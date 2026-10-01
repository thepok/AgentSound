import contextlib
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Clip, ComposeError, Key, Progression, drums, midifx
from agentsound.theory import note
from dx7_banks import needs_dx7

A_MINOR = Key('A minor')
C_MAJOR = Key('C major')


def held(*names, dur=4.0, start=0.0, vel=100, length=None) -> Clip:
    return Clip([(start, dur, n, vel) for n in names], length=length if length is not None else start + dur)


def pitches(c: Clip) -> list[int]:
    return [n.pitch for n in c]


def P(*names) -> list[int]:
    return [note(n) for n in names]


AM = held('A3', 'C4', 'E4')
LINE = Clip([(0, 0.5, 'A4'), (0.5, 0.5, 'B4'), (1, 0.5, 'C5'), (1.5, 0.5, 'D5'),
             (2, 0.5, 'E5'), (2.5, 0.5, 'F5'), (3, 0.5, 'G5')], length=4)


class Arpeggiate(unittest.TestCase):
    def test_held_am_chord_sixteenths(self):
        a = AM.arpeggiate('up', rate='1/16')
        self.assertEqual(len(a), 16)                                    # one bar of 16ths
        self.assertEqual(pitches(a), (P('A3', 'C4', 'E4') * 6)[:16])    # cycling A C E
        self.assertEqual([n.start for n in a], [k * 0.25 for k in range(16)])
        self.assertTrue(all(abs(n.dur - 0.25 * 0.7) < 1e-9 for n in a))
        self.assertTrue(all(n.vel == 100 for n in a))                   # vel=None keeps the held velocity
        self.assertEqual(a.length, 4.0)

    def test_modes(self):
        A, C, E = P('A3', 'C4', 'E4')
        cases = {'down': [E, C, A, E, C, A], 'updown': [A, C, E, C, A, C], 'downup': [E, C, A, C, E, C],
                 'converge': [A, E, C, A, E, C], 'diverge': [C, E, A, C, E, A], 'pinky': [A, E, C, E, A, E],
                 'thumb': [A, C, A, E, A, C]}
        for mode, want in cases.items():
            self.assertEqual(pitches(AM.arpeggiate(mode, rate='1/16'))[:6], want, mode)

    def test_octaves(self):
        a = AM.arpeggiate('up', rate='1/16', octaves=2)
        self.assertEqual(pitches(a)[:7], P('A3', 'C4', 'E4', 'A4', 'C5', 'E5', 'A3'))
        top = held('C9', 'E9').arpeggiate('up', rate='1/4', octaves=2)   # octave copies above 127 are skipped
        self.assertTrue(all(0 <= p <= 127 for p in pitches(top)))
        with self.assertRaises(ComposeError):
            AM.arpeggiate(octaves=0)

    def test_chord_changes_retrigger(self):
        blk = held('A3', 'C4', 'E4') + held('F3', 'A3', 'C4')           # Am for a bar, then F
        a = blk.arpeggiate('up', rate='1/16')
        self.assertEqual(len(a), 32)
        for n in a:
            want = {57, 60, 64} if n.start < 4 else {53, 57, 60}
            self.assertIn(n.pitch, want, n)
        self.assertEqual(a[16].pitch, note('F3'))                      # restarts on the new chord
        cont = blk.arpeggiate('up', rate='1/16', retrigger=False)
        self.assertEqual(cont[16].pitch, note('A3'))                   # counter 16 -> index 1 of F A C
        self.assertEqual(pitches(cont)[:16], pitches(a)[:16])

    def test_chord_change_between_steps(self):
        c = Clip([(0, 1.1, 'A3'), (0, 1.1, 'C4'), (1.1, 2.9, 'F3'), (1.1, 2.9, 'A3')], length=4)
        a = c.arpeggiate('up', rate='1/16')
        self.assertEqual([(n.start, n.pitch) for n in a][:6],
                         [(0.0, 57), (0.25, 60), (0.5, 57), (0.75, 60), (1.0, 57), (1.25, 53)])

    def test_legato_overlap_does_not_leak_into_next_chord(self):
        c = Clip(list(held('A3', 'C4', 'E4', dur=4.02, length=4)) + list(held('F3', 'A3', 'C4', start=4, dur=4)),
                 length=8)                                               # Am overlaps F by 0.02 (legato)
        a = c.arpeggiate('up', rate='1/16')
        self.assertEqual(a[16].pitch, note('F3'))
        self.assertTrue(all(n.pitch in (53, 57, 60) for n in a if n.start >= 4))

    def test_gaps_and_latch(self):
        c = Clip([(0, 1, 'A3'), (0, 1, 'E4'), (2, 1, 'C4'), (2, 1, 'G4')], length=4)
        a = c.arpeggiate('up', rate='1/16')
        self.assertEqual([n.start for n in a], [0.0, 0.25, 0.5, 0.75, 2.0, 2.25, 2.5, 2.75])
        lat = c.arpeggiate('up', rate='1/16', latch=True)
        self.assertEqual(len(lat), 16)
        self.assertEqual({n.pitch for n in lat if 1 <= n.start < 2}, set(P('A3', 'E4')))
        self.assertEqual({n.pitch for n in lat if n.start >= 3}, set(P('C4', 'G4')))

    def test_short_notes_are_not_lost(self):
        c = Clip([(0.1, 0.05, 'A3'), (0.1, 0.05, 'C4')], length=2)
        a = c.arpeggiate('chord', rate='1/16')
        self.assertEqual([(n.start, n.pitch) for n in a], [(0.25, 57), (0.25, 60)])

    def test_order_chord_random(self):
        c = Clip([(0, 4, 'E4'), (0.25, 3.75, 'A3'), (0.5, 3.5, 'C4')], length=4)
        self.assertEqual(pitches(c.arpeggiate('order', rate='1/16'))[:6], P('E4', 'E4', 'E4', 'A3', 'C4', 'E4'))
        self.assertEqual(pitches(c.arpeggiate('order', rate='1/16', retrigger=False))[:4], P('E4', 'A3', 'C4', 'E4'))
        ch = AM.arpeggiate('chord', rate='1/4', gate=0.5)
        self.assertEqual(len(ch), 12)
        self.assertEqual(sorted({n.start for n in ch}), [0.0, 1.0, 2.0, 3.0])
        r1 = held('A3', 'C4', 'E4', 'G4', dur=8).arpeggiate('random', seed=4)
        r2 = held('A3', 'C4', 'E4', 'G4', dur=8).arpeggiate('random', seed=4)
        r3 = held('A3', 'C4', 'E4', 'G4', dur=8).arpeggiate('random', seed=5)
        self.assertEqual(r1, r2)
        self.assertNotEqual(pitches(r1), pitches(r3))
        self.assertTrue(all(a.pitch != b.pitch for a, b in zip(r1, list(r1)[1:])))

    def test_index_pattern(self):
        a = AM.arpeggiate(pattern=[0, 2, None, -1, 3], rate='1/4')      # None = rest, -1 / 3 wrap by octaves
        self.assertEqual([(n.start, n.pitch) for n in a], [(0.0, 57), (1.0, 64), (3.0, 52)])
        first = [(n.start, n.pitch) for n in AM.arpeggiate(pattern=[0, 2, None, -1, 3], rate='1/16')][:5]
        self.assertEqual(first, [(0.0, 57), (0.25, 64), (0.75, 52), (1.0, 69), (1.25, 57)])
        self.assertEqual(pitches(AM.arpeggiate('pattern', pattern=[2, 1], rate='1/16'))[:4], P('E4', 'C4', 'E4', 'C4'))
        for bad in (dict(mode='pattern'), dict(mode='sideways'), dict(mode='down', pattern=[0, 1]),
                    dict(pattern=[0, 'x']), dict(pattern=[]), dict(rate=0), dict(pattern='x.y')):
            with self.assertRaises(ComposeError, msg=repr(bad)):
                AM.arpeggiate(**bad)

    def test_rhythm_pattern_ties_and_levels(self):
        a = AM.arpeggiate('up', rate='1/16', pattern='x.x_', gate=1.0)
        self.assertEqual([(n.start, n.dur, n.pitch) for n in a][:4],
                         [(0.0, 0.25, 57), (0.5, 0.5, 60), (1.0, 0.25, 64), (1.5, 0.5, 57)])
        self.assertEqual(len(a), 8)                                     # rests don't advance the order
        lv = AM.arpeggiate('up', rate='1/16', pattern='Xxo5')
        self.assertEqual([n.vel for n in lv][:4], [118, 100, 62, 70])

    def test_velocity_and_accent(self):
        soft = held('A3', 'C4', vel=60).arpeggiate('up', rate='1/16')
        self.assertTrue(all(n.vel == 60 for n in soft))
        fixed = held('A3', 'C4', vel=60).arpeggiate('up', vel=90)
        self.assertTrue(all(n.vel == 90 for n in fixed))
        acc = AM.arpeggiate('up', rate='1/16', vel=100, accent=1.2)
        self.assertEqual([n.vel for n in acc][:5], [120, 100, 100, 100, 120])
        lst = AM.arpeggiate('up', rate='1/16', vel=100, accent=[1.2, 0.5])
        self.assertEqual([n.vel for n in lst][:4], [120, 50, 120, 50])
        mixed = Clip([(0, 4, 'A3', 110), (0, 4, 'E4', 50)], length=4).arpeggiate('up', octaves=2, rate='1/16')
        self.assertEqual([(n.pitch, n.vel) for n in mixed][:4], [(57, 110), (64, 50), (69, 110), (76, 50)])

    def test_pure_and_deterministic(self):
        before = list(AM)
        a, b = AM.arpeggiate('updown', octaves=2), AM.arpeggiate('updown', octaves=2)
        self.assertEqual(a, b)
        self.assertEqual(list(AM), before)
        self.assertIsNot(a, AM)
        self.assertEqual(midifx.arpeggiate(AM, 'updown', octaves=2), a)


class Strum(unittest.TestCase):
    def test_down_offsets_keep_ends(self):
        s = AM.strum(ms=30, bpm=120)                                   # 30 ms at 120 BPM = 0.06 beats
        self.assertEqual(pitches(s), P('A3', 'C4', 'E4'))
        self.assertEqual([round(n.start, 6) for n in s], [0.0, 0.06, 0.12])
        self.assertTrue(all(abs(n.start + n.dur - 4.0) < 1e-9 for n in s))

    def test_up_alternate_beats(self):
        up = AM.strum(beats='1/64', direction='up')
        self.assertEqual([(n.start, n.pitch) for n in up], [(0.0, 64), (0.0625, 60), (0.125, 57)])
        two = held('A3', 'C4', 'E4', dur=2) + held('F3', 'A3', 'C4', dur=2)
        alt = two.strum(beats=0.05, direction='alternate')
        first = sorted((n for n in alt if n.start < 2), key=lambda n: n.start)
        second = sorted((n for n in alt if n.start >= 2), key=lambda n: n.start)
        self.assertEqual([n.pitch for n in first], P('A3', 'C4', 'E4'))
        self.assertEqual([n.pitch for n in second], P('C4', 'A3', 'F3'))

    def test_vel_decay_single_notes_and_cap(self):
        s = AM.strum(beats=0.1, vel_decay=0.1)
        self.assertEqual([n.vel for n in s], [100, 90, 81])
        self.assertEqual(LINE.strum(ms=40), LINE)                         # single notes untouched
        short = held('A3', 'C4', 'E4', 'A4', dur=0.2).strum(beats=0.1)
        self.assertTrue(all(n.dur >= 0.2 * 0.25 - 1e-9 for n in short))
        with self.assertRaises(ComposeError):
            AM.strum(direction='sideways')


class Ratchet(unittest.TestCase):
    def test_split_every_note(self):
        r = Clip([(0, 1, 'C4', 100)], length=1).ratchet(4)
        self.assertEqual([(n.start, n.pitch) for n in r], [(0.0, 60), (0.25, 60), (0.5, 60), (0.75, 60)])
        self.assertTrue(all(abs(n.dur - 0.225) < 1e-9 for n in r))
        dec = Clip([(0, 1, 'C4', 100)], length=1).ratchet(3, vel_decay=0.5)
        self.assertEqual([n.vel for n in dec], [100, 50, 25])
        cresc = Clip([(0, 1, 'C4', 60)], length=1).ratchet(2, vel_decay=-0.5)
        self.assertEqual([n.vel for n in cresc], [60, 90])

    def test_where(self):
        beat = drums({'kick': 'x...x...', 'hat': 'x.x.x.x.'})
        hats = beat.ratchet(2, where='hat')
        self.assertEqual(len(hats.only('hat')), 8)
        self.assertEqual(hats.only('kick'), beat.only('kick'))
        pred = LINE.ratchet(2, where=lambda n: n.start >= 3)
        self.assertEqual(len(pred), len(LINE) + 1)
        pat = LINE.ratchet(2, where='.x')                               # every 2nd onset
        self.assertEqual(len(pat), len(LINE) + 3)
        digits = LINE.ratchet(2, where='3..')
        self.assertEqual([n.start for n in digits][:4], [0.0, 0.5 / 3, 1 / 3, 0.5])
        chordy = held('A3', 'C4', dur=1).ratchet(2, where='x')          # a chord is one onset
        self.assertEqual(len(chordy), 4)
        with self.assertRaises(ComposeError):
            LINE.ratchet(2, where=object())


class Echo(unittest.TestCase):
    def test_timing_and_decay(self):
        e = Clip([(0, 0.25, 'C4', 100)], length=4).echo(times=3, delay='1/8.', decay=0.6)
        self.assertEqual([n.start for n in e], [0.0, 0.75, 1.5, 2.25])
        self.assertEqual([n.vel for n in e], [100, 60, 36, 22])
        self.assertEqual(pitches(e), [60] * 4)
        self.assertEqual(e.length, 4)

    def test_transpose_semitones_and_scale(self):
        up = Clip([(0, 0.25, 'C4')], length=4).echo(times=3, delay=0.5, transpose=12)
        self.assertEqual(pitches(up), P('C4', 'C5', 'C6', 'C7'))
        climb = Clip([(0, 0.25, 'A4')], length=4).echo(times=3, delay=0.5, transpose=2, key=A_MINOR)
        self.assertEqual(pitches(climb), P('A4', 'C5', 'E5', 'G5'))

    def test_gate_wrap_and_floor(self):
        long = Clip([(0, 2, 'C4')], length=4).echo(times=2, delay=0.5)
        self.assertEqual([n.dur for n in long], [2, 0.5, 0.5])          # repeats never overlap
        gated = Clip([(0, 2, 'C4')], length=4).echo(times=2, delay='1/8.', gate=0.5)
        self.assertEqual([n.dur for n in gated][1:], [0.375, 0.375])
        wrapped = Clip([(1.5, 0.25, 'C4')], length=2).echo(times=2, delay=0.5, wrap=True)
        self.assertEqual(sorted(n.start for n in wrapped), [0.0, 0.5, 1.5])
        faint = Clip([(0, 0.25, 'C4', 10)], length=4).echo(times=5, delay=0.25, decay=0.3)
        self.assertEqual([n.vel for n in faint], [10, 3])               # 10 x 0.3^2 < 1: dropped
        with self.assertRaises(ComposeError):
            LINE.echo(delay=0)


class Harmonize(unittest.TestCase):
    def test_diatonic_thirds_in_a_minor(self):
        h = LINE.harmonize('3rd', key=A_MINOR)
        added = [n for n in h if n not in LINE.notes]
        self.assertEqual([n.pitch for n in sorted(added, key=lambda n: n.start)],
                         P('C5', 'D5', 'E5', 'F5', 'G5', 'A5', 'B5'))
        self.assertTrue(all(n.vel == 80 for n in added))
        self.assertEqual(len(h), 14)
        self.assertEqual(LINE.harmonize(steps=[2], key='A minor'), h)
        self.assertEqual(LINE.harmonize(steps=2, key=A_MINOR), h)

    def test_below_triads_chromatic(self):
        below = Clip([(0, 1, 'C5')], length=1).harmonize('-3rd', key=A_MINOR)
        self.assertEqual(pitches(below), P('A4', 'C5'))
        self.assertEqual(Clip([(0, 1, 'C5')], length=1).harmonize('3rd below', key=A_MINOR), below)
        triad = Clip([(0, 1, 'A4')], length=1).harmonize(['3rd', '5th'], key=A_MINOR)
        self.assertEqual(pitches(triad), P('A4', 'C5', 'E5'))
        octv = LINE.harmonize(semitones=[12], vel=0.5)
        self.assertEqual([n.pitch - 12 for n in octv if n.vel == 50], pitches(LINE))
        sharp = Clip([(0, 1, 'G#4')], length=1).harmonize('3rd', key=A_MINOR)   # alteration kept
        self.assertEqual(pitches(sharp), P('G#4', 'C5'))

    def test_no_duplicates_and_errors(self):
        ce = Clip([(0, 1, 'C4'), (0, 1, 'E4')], length=1).harmonize('3rd', key=C_MAJOR)
        self.assertEqual(pitches(ce), P('C4', 'E4', 'G4'))
        for kw in ({}, dict(interval='3rd', semitones=[12]), dict(interval='3rd'), dict(interval='3th', key=C_MAJOR),
                   dict(interval=3, key=C_MAJOR), dict(steps=[2])):
            with self.assertRaises(ComposeError, msg=repr(kw)):
                LINE.harmonize(**kw)
        with self.assertRaises(ComposeError):
            Clip([(0, 1, 'G9')]).harmonize(semitones=[12])


class Chordify(unittest.TestCase):
    def test_diatonic_triads_and_sevenths(self):
        c = Clip([(0, 1, 'A3'), (1, 1, 'C4'), (2, 1, 'E3')], length=3).chordify('triad', key=A_MINOR)
        self.assertEqual([sorted(n.pitch for n in c if n.start == t) for t in (0, 1, 2)],
                         [P('A3', 'C4', 'E4'), P('C4', 'E4', 'G4'), P('E3', 'G3', 'B3')])
        g7 = Clip([(0, 1, 'G3')], length=1).chordify('7th', key=C_MAJOR)
        self.assertEqual(pitches(g7), P('G3', 'B3', 'D4', 'F4'))

    def test_chromatic_shapes(self):
        one = Clip([(0, 1, 'D3', 100)], length=1)
        self.assertEqual(pitches(one.chordify('power')), P('D3', 'A3', 'D4'))
        self.assertEqual(pitches(one.chordify('m7')), P('D3', 'F3', 'A3', 'C4'))
        self.assertEqual(pitches(one.chordify((0, 4, 7))), P('D3', 'F#3', 'A3'))
        self.assertEqual(pitches(one.chordify('sus4')), P('D3', 'G3', 'A3'))
        self.assertEqual(pitches(one.chordify('sus4', key=C_MAJOR)), P('D3', 'G3', 'A3'))
        with self.assertRaises(ComposeError):
            one.chordify('triad')                                        # diatonic shapes need a key
        with self.assertRaises(ComposeError):
            one.chordify('blorp')

    def test_voicings_and_velocity(self):
        c4 = Clip([(0, 1, 'C4', 100)], length=1)
        self.assertEqual(pitches(c4.chordify('triad', key=C_MAJOR, voicing='open')), P('C4', 'G4', 'E5'))
        self.assertEqual(pitches(c4.chordify('triad', key=C_MAJOR, voicing='spread')), P('C4', 'G4', 'E5'))
        self.assertEqual(pitches(c4.chordify('7th', key=C_MAJOR, voicing='spread')), P('C4', 'G4', 'E5', 'B5'))
        soft = c4.chordify('triad', key=C_MAJOR, vel=0.5)
        self.assertEqual([n.vel for n in soft], [100, 50, 50])
        with self.assertRaises(ComposeError):
            c4.chordify(voicing='drop2', key=C_MAJOR)


class Quantize(unittest.TestCase):
    def test_strength_and_grid(self):
        c = Clip([(0.1, 0.2, 60), (0.9, 0.2, 62), (1.3, 0.2, 64)], length=2)
        self.assertEqual([round(n.start, 6) for n in c.quantize('1/16')], [0.0, 1.0, 1.25])
        self.assertEqual([round(n.start, 6) for n in c.quantize('1/16', strength=0.5)], [0.05, 0.95, 1.275])
        self.assertEqual([n.dur for n in c.quantize('1/16')], [0.2, 0.2, 0.2])

    def test_ends_and_swing(self):
        c = Clip([(0.1, 0.3, 60), (0.52, 0.05, 62)], length=2).quantize('1/16', ends=True)
        self.assertEqual([(round(n.start, 6), round(n.dur, 6)) for n in c], [(0.0, 0.5), (0.5, 0.25)])
        sw = Clip([(0.26, 0.1, 60), (0.49, 0.1, 62)], length=1).quantize('1/16', swing=0.58)
        self.assertEqual([round(n.start, 6) for n in sw], [0.29, 0.5])
        self.assertEqual(Clip([(0.26, 0.1, 60)], length=1).quantize('1/16', swing=58)[0].start,
                         sw[0].start)
        for bad in (dict(swing=0.3), dict(strength=2), dict(grid=0)):
            with self.assertRaises(ComposeError, msg=repr(bad)):
                c.quantize(**bad)

    def test_scale_quantize(self):
        c = Clip([(0, 1, 'C#4'), (1, 1, 'F#4'), (2, 1, 'E4')], length=3)
        self.assertEqual(pitches(c.scale_quantize(C_MAJOR)), P('C4', 'F4', 'E4'))
        self.assertEqual(pitches(c.scale_quantize('C major', 'up')), P('D4', 'G4', 'E4'))
        self.assertEqual(pitches(c.scale_quantize(C_MAJOR, direction='down')), P('C4', 'F4', 'E4'))
        self.assertEqual(pitches(Clip([(0, 1, 'G#4')]).scale_quantize(A_MINOR)), P('G4'))
        merged = Clip([(0, 1, 'C4'), (0, 2, 'C#4')], length=2).scale_quantize(C_MAJOR)
        self.assertEqual([(n.pitch, n.dur) for n in merged], [(60, 2.0)])
        with self.assertRaises(ComposeError):
            c.scale_quantize(C_MAJOR, 'sideways')
        with self.assertRaises(ComposeError):
            c.scale_quantize(None)


class Density(unittest.TestCase):
    def test_chance(self):
        many = Clip([(k * 0.25, 0.25, 60) for k in range(400)], length=100)
        self.assertEqual(many.chance(1.0), many)
        self.assertEqual(len(many.chance(0.0)), 0)
        half = many.chance(0.5, seed=3)
        self.assertTrue(150 < len(half) < 250, len(half))
        self.assertEqual(half, many.chance(0.5, seed=3))
        self.assertNotEqual(half, many.chance(0.5, seed=4))
        with self.assertRaises(ComposeError):
            many.chance(1.5)

    def test_thin(self):
        c = Clip([(0, 1, 60), (0, 1, 64), (1, 1, 62), (2, 1, 64), (2, 1, 67), (3, 1, 65)], length=4)
        self.assertEqual([(n.start, n.pitch) for n in c.thin(2)], [(0, 60), (0, 64), (2, 64), (2, 67)])
        self.assertEqual([(n.start, n.pitch) for n in c.thin(2, offset=1)], [(1, 62), (3, 65)])
        self.assertEqual(c.thin(1), c)
        with self.assertRaises(ComposeError):
            c.thin(0)


class Register(unittest.TestCase):
    def test_fold(self):
        c = Clip([(0, 1, 40), (1, 1, 90), (2, 1, 'C4'), (3, 1, 'C5')], length=4).fold('C4', 'C5')
        self.assertEqual(pitches(c), [64, 66, 60, 72])
        self.assertTrue(all(60 <= p <= 72 for p in pitches(c)))
        merged = Clip([(0, 1, 'A3'), (0, 1, 'A4')], length=1).fold('C4', 'B4')
        self.assertEqual(pitches(merged), P('A4'))
        with self.assertRaises(ComposeError):
            c.fold('C4', 'G4')

    def test_octave_double(self):
        b = Clip([(0, 1, 'A2', 100)], length=1).octave_double(-12)
        self.assertEqual([(n.pitch, n.vel) for n in b], [(33, 80), (45, 100)])
        both = Clip([(0, 1, 'A3', 100)], length=1).octave_double([12, -12], vel=1.0)
        self.assertEqual(pitches(both), P('A2', 'A3', 'A4'))
        for bad in (7, 0, [12, 5]):
            with self.assertRaises(ComposeError, msg=repr(bad)):
                LINE.octave_double(bad)


class VelocityAndLength(unittest.TestCase):
    def test_vel_random(self):
        c = Clip([(k, 1, 60, 100) for k in range(64)], length=64)
        r = c.vel_random(10, seed=2)
        self.assertTrue(all(90 <= n.vel <= 110 for n in r))
        self.assertGreater(len({n.vel for n in r}), 5)
        self.assertEqual(r, c.vel_random(10, seed=2))
        self.assertEqual(c.vel_random(0), c)

    def test_vel_pattern(self):
        c = Clip([(k * 0.5, 0.5, 60, 100) for k in range(4)], length=2)
        self.assertEqual([n.vel for n in c.vel_pattern([1.2, 0.8])], [120, 80, 120, 80])
        self.assertEqual([n.vel for n in c.vel_pattern([120, 70, 96])], [120, 70, 96, 120])
        chord = Clip([(0, 1, 60, 100), (0, 1, 64, 100), (1, 1, 62, 100)], length=2).vel_pattern([1.1, 0.5])
        self.assertEqual([n.vel for n in chord], [110, 110, 50])
        offbeat = Clip([(0.5, 0.5, 60, 100), (1.5, 0.5, 60, 100)], length=2).vel_pattern([1.2, 0.6], grid='1/8')
        self.assertEqual([n.vel for n in offbeat], [60, 60])             # both on odd 8ths
        with self.assertRaises(ComposeError):
            c.vel_pattern([])

    def test_staccato(self):
        c = Clip([(0, 1, 60), (1, 0.1, 62)], length=2).staccato('1/16')
        self.assertEqual([n.dur for n in c], [0.25, 0.1])


class PitchOrder(unittest.TestCase):
    def test_retrograde(self):
        self.assertEqual(LINE.retrograde(), LINE.reverse())
        r = LINE.retrograde(rhythm=False)
        self.assertEqual([n.start for n in r], [n.start for n in LINE])
        self.assertEqual(pitches(r), pitches(LINE)[::-1])
        mixed = Clip([(0, 1, 60), (0, 1, 64), (1, 0.5, 67)], length=2).retrograde(rhythm=False)
        self.assertEqual([(n.start, n.pitch) for n in mixed], [(0, 67), (1, 60), (1, 64)])

    def test_invert(self):
        c = Clip([(0, 1, 'A4'), (1, 1, 'C5'), (2, 1, 'E5')], length=3)
        self.assertEqual(pitches(c.invert()), P('A4', 'F#4', 'D4'))              # chromatic around A4
        self.assertEqual(pitches(c.invert(key=A_MINOR)), P('A4', 'F4', 'D4'))    # diatonic steps
        self.assertEqual(pitches(c.invert(pivot='C5', key=A_MINOR)), P('E5', 'C5', 'A4'))
        self.assertEqual(Clip.rest(1).invert(), Clip.rest(1))


class Chaining(unittest.TestCase):
    def test_chain_is_pure_and_keeps_length(self):
        prog = Progression('Am F C G')
        blk = prog.block(voices=3)
        before = list(blk)
        out = (blk.arpeggiate('updown', rate='1/16', octaves=2).fold('A3', 'A5').echo(times=1, delay='1/8.')
               .quantize('1/16').vel_pattern([1.1, 0.9]).chance(0.9, seed=1))
        self.assertIsInstance(out, Clip)
        self.assertEqual(out.length, blk.length)
        self.assertEqual(list(blk), before)
        again = (blk.arpeggiate('updown', rate='1/16', octaves=2).fold('A3', 'A5').echo(times=1, delay='1/8.')
                 .quantize('1/16').vel_pattern([1.1, 0.9]).chance(0.9, seed=1))
        self.assertEqual(out, again)

    def test_every_transform_is_a_clip_method(self):
        for name in ('arpeggiate', 'strum', 'ratchet', 'echo', 'harmonize', 'chordify', 'quantize', 'scale_quantize',
                     'chance', 'thin', 'fold', 'octave_double', 'vel_random', 'vel_pattern', 'staccato',
                     'retrograde', 'invert'):
            self.assertTrue(callable(getattr(Clip, name)), name)
            self.assertTrue(callable(getattr(midifx, name)), name)


# ------------------------------------------------------------------------------ end to end

DEMO_SONG = '''
from agentsound import *


def build():
    s = Song('MIDI FX Test', tempo=100, key='A minor', seed=5)
    a = s.section('a', bars=2)
    b = s.section('b', bars=2)
    prog = s.prog('i VI', bars=1) * 2
    kit = s.track('drums', inst.drums(kit='synthwave'), gain_db=-3, sends={'gated': -6})
    s.gated(gain_db=-2, hold=250, key=kit, pitches='snare')
    hall = s.hall(decay=2.0)
    beat = drums({'kick': 'x...x...x...x...', 'snare': '....X.......X...', 'hat': 'x.x.x.x.x.x.x.x.'})
    kit.loop(beat.ratchet(3, where=lambda n: n.pitch == 42 and n.start >= 3.5).vel_pattern([1.0, 0.8], grid='1/8'), a, b)
    held = chords(s.prog('i VI'), voicing='smooth', register=(55, 76))
    pad = s.track('pad', inst.va(unison=3, cutoff=1800, amp__attack=0.3), gain_db=-10, sends={hall: -8})
    pad.loop(held.strum(ms=30, bpm=s.tempo, direction='alternate'), a, b)
    arp = s.track('arp', inst.va(osc1__wave='square', amp__sustain=0, amp__decay=0.2), gain_db=-12)
    arp.loop(held.arpeggiate('updown', rate='1/16', octaves=2, pattern='xxx_').fold('A3', 'A5'), b)
    bass = s.track('bass', inst.va(osc1__wave='saw', cutoff=700), gain_db=-6)
    bass.loop(prog.bass('root').ratchet(8, gate=0.6), a, b)
    lead = s.track('lead', inst.va(mode='legato', glide=0.03), gain_db=-10)
    hook = s.motif('5:1/4 3:1/8 1:1/8 3:1/2 | 2:1/4 3:1/4 5:1/2').clip(octave=5).legato()
    lead.play(hook.harmonize('-3rd', key=s.key).echo(times=2, delay='1/8.', decay=0.5, gate=0.5), b)
    keys = s.track('keys', inst.dx7('E.PIANO 1'), gain_db=-12)
    keys.loop(Clip([(0, 1, 'A3'), (2, 1, 'F3')], length=4).chordify('7th', key=s.key, voicing='spread')
              .quantize('1/8', swing=0.58).vel_random(6, seed=2), a, b)
    s.master.add(fx.limiter(gain=4))
    return s
'''


def _engine():
    from agentsound import cli
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


class ReviewFixes(unittest.TestCase):
    """Musical edge cases found in review."""

    def test_tie_holds_to_the_gate_of_the_last_tied_step(self):
        a = AM.arpeggiate('up', rate='1/16', pattern='x_x.', gate=0.5)
        self.assertEqual([(n.start, n.dur, n.pitch) for n in a][:2], [(0.0, 0.375, 57), (0.5, 0.125, 60)])
        three = AM.arpeggiate('up', rate='1/16', pattern='x__.', gate=0.5)
        self.assertEqual(three[0].dur, 0.625)                           # 2 whole steps + half of the third

    def test_digit_only_rhythm_is_rejected_with_hint(self):
        with self.assertRaisesRegex(ComposeError, r'pattern=\[1, 3, 2, 4\]'):
            AM.arpeggiate(pattern='1 3 2 4')
        self.assertEqual(len(AM.arpeggiate(pattern='7.9.', rate='1/16')), 8)

    def test_long_legato_overlap_does_not_leak(self):
        blk = held('A3', 'C4', 'E4', dur=2) + held('F3', 'A3', 'C4', dur=2)
        for ov in (0.02, 0.05, 0.1):
            a = blk.legato(ov).arpeggiate('up', rate='1/16')
            self.assertEqual([n.pitch for n in a if n.start >= 2][:4], P('F3', 'A3', 'C4', 'F3'), ov)

    def test_latch_is_not_disturbed_by_later_notes(self):
        c = Clip([(0, 0.5, 'A3'), (0, 0.5, 'E4'), (1, 0.1, 'C5')], length=2)
        a = c.arpeggiate('up', rate='1/16', latch=True)
        self.assertEqual([(n.start, n.pitch) for n in a],
                         [(0.0, 57), (0.25, 64), (0.5, 57), (0.75, 64), (1.0, 72), (1.25, 72), (1.5, 72), (1.75, 72)])

    def test_humanized_chords_still_count_as_chords(self):
        hum = Clip([(0.012, 2, 'C4'), (-0.01, 2, 'E4'), (0.0, 2, 'G4'), (2.01, 2, 'D4'), (1.995, 2, 'F4')], length=4)
        s = hum.strum(beats=0.1)
        first = sorted((n for n in s if n.start < 1), key=lambda n: n.start)
        self.assertEqual([n.pitch for n in first], P('C4', 'E4', 'G4'))  # low string first, from the chord start
        self.assertAlmostEqual(first[1].start, -0.01 + 0.1)
        self.assertAlmostEqual(first[2].start, -0.01 + 0.2)
        self.assertTrue(all(abs(n.start + n.dur - (x.start + x.dur)) < 1e-9
                            for n in s for x in hum if x.pitch == n.pitch and abs(x.start - n.start) < 0.5))
        self.assertEqual(len(hum.thin(2)), 3)                            # 2 onsets: keep the first chord
        self.assertEqual([n.vel for n in hum.vel_pattern([1.0, 0.5]) if n.start > 1], [50, 50])

    def test_echo_never_stacks_the_same_pitch(self):
        rep = Clip([(0, 0.5, 'A4', 100), (0.5, 0.5, 'A4', 100)], length=2).echo(times=2, delay='1/8')
        keys = [(n.start, n.pitch) for n in rep]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual([(n.start, n.vel) for n in rep], [(0.0, 100), (0.5, 100), (1.0, 60), (1.5, 36)])
        climb = Clip([(0, 0.5, 'A4', 100), (1, 1, 'C5', 90)], length=4).echo(times=2, delay=1, transpose=2,
                                                                               key=A_MINOR)
        self.assertEqual([(n.start, n.pitch, n.vel) for n in climb],
                         [(0, 69, 100), (1, 72, 90), (2, 76, 54), (3, 79, 32)])

    def test_sus_chords_are_real_sus_chords(self):
        def ch(root, shape, key=None):
            return pitches(Clip([(0, 1, root)], length=1).chordify(shape, key=key))
        self.assertEqual(ch('A2', 'sus4', A_MINOR), P('A2', 'D3', 'E3'))
        self.assertEqual(ch('A2', 'sus2', A_MINOR), P('A2', 'B2', 'E3'))
        self.assertEqual(ch('F2', 'sus4', A_MINOR), P('F2', 'G2', 'C3'))     # Fsus4 needs Bb: in-key Fsus2
        self.assertEqual(ch('E3', 'sus2', A_MINOR), P('E3', 'A3', 'B3'))     # Esus2 needs F#: in-key Esus4
        self.assertEqual(ch('B2', 'sus4', A_MINOR), P('B2', 'E3', 'F#3'))    # no perfect fifth in key: chromatic
        for root in ('A2', 'B2', 'C3', 'D3', 'E3', 'F3', 'G3'):
            for shape in ('sus2', 'sus4'):
                ps = ch(root, shape, A_MINOR)
                self.assertIn(ps[2] - ps[0], (7,), (root, shape, ps))
                self.assertIn(ps[1] - ps[0], (2, 5), (root, shape, ps))

    def test_edge_clips(self):
        empty, rest = Clip(), Clip.rest(4)
        for c in (empty, rest):
            for f in (lambda c: c.arpeggiate(), lambda c: c.strum(), lambda c: c.ratchet(3), lambda c: c.echo(),
                      lambda c: c.harmonize('3rd', key=A_MINOR), lambda c: c.chordify('triad', key=A_MINOR),
                      lambda c: c.quantize(), lambda c: c.scale_quantize(A_MINOR), lambda c: c.chance(),
                      lambda c: c.thin(), lambda c: c.fold('A3', 'A5'), lambda c: c.octave_double(),
                      lambda c: c.vel_random(), lambda c: c.vel_pattern([1, 0.5]), lambda c: c.staccato(),
                      lambda c: c.retrograde(), lambda c: c.retrograde(rhythm=False), lambda c: c.invert()):
                out = f(c)
                self.assertEqual(len(out), 0)
                self.assertEqual(out.length, c.length)
        crossing = Clip([(3, 3, 'A3'), (3, 3, 'C4')], length=4).arpeggiate('up', rate='1/16')
        self.assertEqual([n.start for n in crossing], [3.0, 3.25, 3.5, 3.75])   # steps stop at the clip end


class DemoSongCompiles(unittest.TestCase):
    def test_demo_compiles_with_keyed_gate(self):
        ns: dict = {}
        exec(compile(DEMO_SONG, 'demo_song.py', 'exec'), ns)
        r = ns['build']().compile()
        gated = next(b for b in r['buses'] if b['id'] == 'gated')
        gr = next(f for f in gated['fx'] if f['type'] == 'gatedreverb')
        self.assertEqual(gr['sidechain'], 'drums-key')
        ghost = next(t for t in r['tracks'] if t['id'] == 'drums-key')
        self.assertTrue(ghost['mute'])
        self.assertEqual({n[2] for n in ghost['notes']}, {38})
        self.assertEqual(len(ghost['notes']), 8)                   # 2 snares x 4 bars


@unittest.skipIf(_engine() is None, 'engine not built (set AGENTSOUND_TEST_ENGINE or build build/agentsound.exe)')
class EndToEnd(unittest.TestCase):
    @needs_dx7
    def test_build_song_with_midi_fx_and_keyed_gated_snare(self):
        from agentsound import cli
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_midifx_'))
        self.addCleanup(shutil.rmtree, d, True)
        (d / 'song.py').write_text(DEMO_SONG, encoding='utf-8')
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(['build', str(d), '--no-mp3', '--out', str(d / 'out'), '--engine', str(_engine())])
        self.assertEqual(code, 0, out.getvalue() + err.getvalue())
        self.assertTrue((d / 'out' / 'mix.wav').is_file())
        report = json.loads((d / 'out' / 'report.json').read_text(encoding='utf-8'))
        errors = [w for w in report.get('warnings', []) if isinstance(w, dict) and w.get('severity') == 'error']
        self.assertEqual(errors, [], errors)
        nodes = {n.get('id'): n for n in report.get('nodes', []) if isinstance(n, dict)}
        self.assertIn('gated', nodes)                                   # the keyed gate produced a burst
        self.assertIn('arp', nodes)


if __name__ == '__main__':
    unittest.main()
