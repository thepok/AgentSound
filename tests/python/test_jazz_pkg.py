"""The jazz package (phase 2 of compact song code): song.form / ending / track.feature, Arrangement.place, the
straight-8th walking_bass and brushes, jazz.chorus, slides, last_stir, bombs, pianist.crushes. The migrated songs
(minetta-lane-waltz, perry-street-rain, lanterns-on-carmine ...) were checked byte-identical against their
hand-written render JSON; these tests pin the behaviour of the pieces."""
import pathlib
import random
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import jazz, notes, pianist  # noqa: E402
from agentsound.bandlib import jazz as jazzband  # noqa: E402
from agentsound.patterns import SWIRLY_BRUSH, Clip, brush_colour, brushes, walking_bass  # noqa: E402
from agentsound.song import Part, Song  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

CHANGES = {'A1': 'Dm7 G7 | Cmaj7 A7', 'A2': 'Dm7 G7 | Cmaj7 C7', 'B': 'Fmaj7 Bb7 | Em7 A7',
           'A': 'Dm7 G7 | Cmaj7 Cmaj7', 'intro': 'Dm7 G7', 'tag': 'Em7 A7 Dm7 G7'}


def song(meter=None, **kw):
    s = Song('t', tempo=120, key='C major', seed=3, meter=meter, **kw)
    return s


class Form(unittest.TestCase):
    def test_letters_number_per_section_and_fall_back(self):
        s = song()
        intro, head, out, end = s.form('intro:2 head:AABA out:B,A end:2', parts=CHANGES)
        self.assertEqual([p.name for p in head.parts], ['A1', 'A2', 'B', 'A'])     # no A3: the plain A
        self.assertEqual([p.name for p in out.parts], ['B', 'A'])
        self.assertEqual(head.bars, 16)
        self.assertEqual([p.bar for p in head.parts], [0, 4, 8, 12])
        self.assertEqual([p.start for p in head.parts], [8.0, 24.0, 40.0, 56.0])
        self.assertEqual(head.prog.length, 64.0)
        self.assertEqual([c.symbol for _, _, c in head.part('B').prog], ['Fmaj7', 'Bb7', 'Em7', 'A7'])
        self.assertEqual(intro.prog.length, 8.0)          # 'intro:2' takes parts['intro']
        self.assertIsNone(end.prog)
        self.assertEqual(end.parts, ())
        self.assertIs(head.part(2), head.parts[2])
        self.assertEqual(s.at(head.part('A2')), 24.0)     # a Part is a position
        self.assertIsInstance(head.parts[0], Part)

    def test_meter_and_errors(self):
        s = song()
        (w,) = s.form('w:A', parts={'A': 'Dm9 G13 Cmaj7'}, meter=(3, 4))
        self.assertEqual((w.bars, w.length), (3.0, 9.0))
        with self.assertRaisesRegex(ComposeError, "needs part 'C'"):
            song().form('x:AC', parts=CHANGES)
        with self.assertRaisesRegex(ComposeError, 'name:bars'):
            song().form('intro', parts=CHANGES)
        with self.assertRaisesRegex(ComposeError, 'holds 4 bars, the section 2'):
            song().form('tag:2', parts=CHANGES)
        with self.assertRaisesRegex(ComposeError, 'no part'):
            song().form('h:AB', parts=CHANGES)[0].part('Z')


class Ending(unittest.TestCase):
    def test_one_call_ending(self):
        s = song()
        tag, end = s.form('tag:4 end:2', parts=CHANGES)
        piano, comp, bass, drums = (s.track(n, {'type': 'va', 'params': {}}) for n in ('p', 'c', 'b', 'd'))
        lh = notes('[C3 G3 E4]:8', vel=60)
        rh = notes('[E5 G5 B5 D6]:8', vel=70)
        s.ending(end, chords=[(comp, lh, 60), (piano, rh, 80, 0.25)], bass=(bass, 'C2', 7, 90),
                 drums=(drums, jazz.last_stir(jazz.GM_BRUSH, 8, last=3)), rit=tag.bar(2), to=0.7, hold=2,
                 length=4, room=(-13, -8), send='room')
        starts = sorted(n.start for n in comp.notes)
        self.assertEqual(starts[0], end.start)
        self.assertGreater(starts[-1], end.start)                       # rolled up from the bass
        self.assertGreater(min(n.start for n in piano.notes), end.start + 0.25 - 1e-9)  # the right hand lands later
        self.assertEqual([(n.start, n.pitch, n.vel) for n in bass.notes], [(end.start, 36, 90)])
        self.assertEqual(len(drums.notes), 5)
        pedal = [pts for t, pts in piano._auto if t == 'instrument.pedal'][0]
        self.assertEqual(pedal, [(end.start - 0.05, 0.0, 'step'), (end.start + 0.02, 1.0, 'step')])
        self.assertTrue(any(t == 'send.room' for t, _ in comp._auto))
        self.assertLess(s.tempo_at(end.start), 120 * 0.75)             # the ritardando stays slow
        self.assertEqual(len(s._tempo_plan.fermatas), 1)

    def test_room_needs_an_end_for_a_beat_position(self):
        s = song()
        s.section('a', bars=2)
        t = s.track('p', {'type': 'va', 'params': {}})
        with self.assertRaisesRegex(ComposeError, 'until='):
            s.ending(4.0, chords=[(t, notes('[C4 E4]:2'), 30)], hold=None, room=(-13, -8))
        with self.assertRaisesRegex(ComposeError, r'\(track, clip, ms'):
            s.ending(4.0, chords=[(t, notes('C4'))], hold=None)


class Feature(unittest.TestCase):
    def test_spotlight_lane(self):
        s = song()
        a, solo, b = s.section('a', 4), s.section('solo', 4), s.section('b', 4)
        t = s.track('bass', {'type': 'va', 'params': {}})
        t.feature(solo, db=2.5)
        target, pts = t._auto[0]
        self.assertEqual(target, 'gainDb')
        self.assertEqual(pts, [(0, 0.0), (15.0, 0.0), (16.0, 2.5, 'smooth'), (31.0, 2.5), (32.0, 0.0, 'smooth')])
        with self.assertRaises(ComposeError):
            t.feature()


class Place(unittest.TestCase):
    def test_place_plays_both_hands_and_the_pedal(self):
        s = song()
        (a,) = s.form('a:A1', parts=CHANGES)
        rh, lh = s.track('rh', {'type': 'va', 'params': {}}), s.track('lh', {'type': 'va', 'params': {}})
        mel = notes('E5/2 D5 C5/1 | B4/2 A4 G4/1', vel=80)
        arr = pianist.arrange(mel, a.prog, bpm=120, key=s.key, lh='guide', seed=4, at=a.start)
        self.assertIs(arr.prog, a.prog)
        arr.place(rh, lh)
        self.assertEqual(len(rh.notes), len(arr.rh))
        self.assertEqual(len(lh.notes), len(arr.lh))
        self.assertEqual(rh._auto, [('instrument.pedal', arr.pedal(a.prog, a.start))])
        with self.assertRaisesRegex(ComposeError, 'give at='):
            pianist.arrange(mel, a.prog, bpm=120, key=s.key).place(rh)


class StraightBass(unittest.TestCase):
    def test_44_feels_root_on_one_and_seeded(self):
        s = song()
        p = s.prog('Fm9 Dbmaj7#11 Bbm9 Eb7sus4:0.5 Eb7b9:0.5')
        for feel in ('two', 'push', 'drive'):
            a = walking_bass(p, straight=True, feel=feel, seed=4, vel=86)
            self.assertEqual(list(a), list(walking_bass(p, straight=True, feel=feel, seed=4, vel=86)))
            for st, d, c in p:
                first = min((n for n in a if abs(n.start - st) < 1e-9), key=lambda n: n.pitch, default=None)
                if first is not None:                      # an anticipation may have tied over the bar line
                    self.assertEqual(first.pitch % 12, c.root)
            self.assertTrue(all(28 <= n.pitch <= 55 for n in a))
        flat = walking_bass(p, straight=True, feel='push', seed=4, vel=86, touch=0)
        touched = walking_bass(p, straight=True, feel='push', seed=4, vel=86)
        self.assertEqual([(n.start, n.pitch) for n in flat], [(n.start, n.pitch) for n in touched])
        self.assertNotEqual([n.vel for n in flat], [n.vel for n in touched])
        # 'walk' in 4/4 is the quarter-note walk itself
        self.assertEqual(list(walking_bass(p, straight=True, feel='walk', seed=2)),
                         list(walking_bass(p, feel='four', seed=2)))

    def test_waltz_feels_and_errors(self):
        s = song(meter=(3, 4))
        p = s.prog('Dm9 Bbmaj7#11 Gm9 A7b13')
        for feel, per_bar in (('two', 2), ('walk', 3)):
            line = walking_bass(p, straight=True, feel=feel, seed=7)
            self.assertGreaterEqual(len(line), per_bar * 4)
            self.assertEqual(line.length, 12.0)
        one = walking_bass(p, straight=True, feel='one', seed=7)
        self.assertTrue(all(n.start % 3 in (0.0, 2.0) for n in one))
        with self.assertRaisesRegex(ComposeError, 'feel must be one of one, two, walk'):
            walking_bass(p, straight=True, feel='push')
        with self.assertRaisesRegex(ComposeError, '4/4 or 3/4'):
            walking_bass(song(meter=(5, 4)).prog('Dm7 G7'), straight=True, feel='two')


class StraightBrushes(unittest.TestCase):
    def test_colour_on_the_grid(self):
        c = brush_colour(4, 'ballad', kit=SWIRLY_BRUSH, ghosts=1.0, kick=True, hat8=0.8, ride=0.9, seed=3)
        kind = {v: k for k, v in SWIRLY_BRUSH.items()}
        taps = [n.start % 4 for n in c if kind.get(n.pitch) == 'tap']
        self.assertTrue(taps and all(t % 1 == 0.5 for t in taps))             # ghosts on the &s only
        self.assertEqual(len([n for n in c if kind.get(n.pitch) == 'hat']), 4 * 8)        # 8ths, no fill in 4 bars
        filled = brush_colour(8, 'ballad', kit=SWIRLY_BRUSH, hat8=0.8, seed=3)
        self.assertEqual(len([n for n in filled if n.start >= 28]), 6)               # the fill bar: from 3.0 off
        rides = sorted({n.start % 4 for n in c if kind.get(n.pitch) == 'ride'})
        self.assertEqual(rides, [0.0, 1.0, 1.5, 2.0, 3.0, 3.5])
        self.assertTrue(any(kind.get(n.pitch) == 'dig' for n in c))           # digs come with the ride
        self.assertFalse(any(kind.get(n.pitch) == 'dig'
                             for n in brush_colour(4, kit=SWIRLY_BRUSH, ride=0.9, digs=False, seed=3)))
        waltz = brush_colour(2, 'medium', kit=SWIRLY_BRUSH, ride=1.0, seed=1, beats_per_bar=3)
        self.assertEqual(sorted({n.start % 3 for n in waltz if kind.get(n.pitch) == 'ride'}), [0.0, 1.0, 1.5, 2.0])
        gm = brush_colour(2, kit=jazz.GM_BRUSH, ride=1.0, seed=1)                # no 'dig' in GM: the slap
        self.assertTrue(any(n.pitch == jazz.GM_BRUSH['slap'] for n in gm))

    def test_straight_brushes_and_band_levelling(self):
        plain = brushes(8, 'ballad', kit=SWIRLY_BRUSH, straight=True, fills=False, seed=5)
        self.assertFalse(any(n.pitch == SWIRLY_BRUSH['kick'] for n in plain))   # no kick unless asked
        kicked = brushes(8, 'ballad', kit=SWIRLY_BRUSH, straight=True, kick='even', seed=5)
        self.assertTrue(any(n.pitch == SWIRLY_BRUSH['kick'] and n.start % 4 == 1.5 for n in kicked))
        with self.assertRaisesRegex(ComposeError, 'straight=True'):
            brushes(4, ghosts=0.5)

        class B:                                   # a band with a Swirly kit: the groove is levelled, the colour not
            info = {'kit': SWIRLY_BRUSH, 'sweep': None, 'stir': (1.9, 0.8)}
        lev = jazzband.brushes(B, 8, 'ballad', straight=True, ghosts=1.0, seed=5)
        colour = brush_colour(8, 'ballad', kit=SWIRLY_BRUSH, ghosts=1.0, seed=5)
        raw = brushes(8, 'ballad', kit=SWIRLY_BRUSH, fill='eighths', kick=None, seed=5)
        self.assertEqual(sorted(lev), sorted(jazzband.brushes(B, 8, 'ballad', fill='eighths', kick=None, seed=5)
                                             | colour))
        self.assertNotEqual(sorted(lev), sorted(raw | colour))


class Chorus(unittest.TestCase):
    def setUp(self):
        self.s = song()
        self.head, = self.s.form('head:AABA', parts=CHANGES)
        self.b = jazz.band(self.s, sampled_sounds=False)
        self.mel = notes(' '.join(['E5/2 D5 C5/1 | B4/2 A4 G4/1 |'] * 2), vel=80)

    def test_piano_parts_seeds_and_overrides(self):
        rec = {}
        out = jazz.chorus(self.b, self.head, [self.mel] * 4, bass=None, record=rec,
                          piano=dict(style='straight', seed=10, lh='guide', density=jazz.each(0.3, 0.5, 0.7, 0.4),
                                     B=dict(seed=99, style='lush')))
        self.assertEqual(list(out), ['A1', 'A2', 'B', 'A'])
        self.assertEqual(sorted(rec), ['head:A', 'head:A1', 'head:A2', 'head:B'])
        mem_free = pianist.arrange(self.mel, self.head.part('A2').prog, bpm=120, key=self.s.key, style='straight',
                                   seed=11, lh='guide', density=0.5, at=self.head.part('A2').start)
        self.assertEqual(list(out['A2'].rh), list(mem_free.rh))                 # seed 10 + 1
        lush = pianist.arrange(self.mel, self.head.part('B').prog, bpm=120, key=self.s.key, style='lush',
                               seed=99, lh='guide', density=0.7, at=self.head.part('B').start)
        self.assertEqual(list(out['B'].rh), list(lush.rh))                      # the part's own seed / style
        self.assertTrue(any(t == 'instrument.pedal' for t, _ in self.b.comp._auto))

    def test_bass_drums_comp_and_rests(self):
        jazz.chorus(self.b, self.head, [self.mel] * 4, comp=dict(style='swing', seed=3, A2=None),
                    bass=dict(seed=5, vel=jazz.each(80, 84, 88, 92), B=None),
                    drums=[(8, dict(seed=1, style='two')), (8, dict(seed=2, ride=True))], lh_pedal=False)
        self.assertFalse(any(self.head.part('B').start <= n.start < self.head.part('B').end for n in self.b.bass.notes))
        self.assertFalse(any(self.head.part('A2').start <= n.start < self.head.part('A2').end for n in self.b.comp.notes))
        first = walking_bass(self.head.part('A1').prog, key=self.s.key, seed=5, vel=80)
        self.assertEqual([(n.start, n.pitch) for n in self.b.bass.notes[:len(first)]],
                         [(n.start + self.head.start, n.pitch) for n in first])
        self.assertTrue(any(n.start >= self.head.bar(8) for n in self.b.drums.notes))
        self.assertFalse(any(t == 'instrument.pedal' for t, _ in self.b.comp._auto))

    def test_errors_and_defaults(self):
        with self.assertRaisesRegex(ComposeError, 'song.form'):
            jazz.chorus(self.b, self.s.section('plain', 4), piano=dict())
        with self.assertRaisesRegex(ComposeError, r'each\(...\) gives 2 values for 4 parts'):
            jazz.chorus(self.b, self.head, self.mel, bass=dict(vel=jazz.each(80, 90)))
        with self.assertRaisesRegex(ComposeError, 'needs a melody'):
            jazz.chorus(self.b, self.head, piano=dict(), bass=None)
        with self.assertRaisesRegex(ComposeError, 'unknown role'):
            jazz.chorus(self.b, self.head, defaults={'sax': {}})
        # defaults lie under the call; an option dict (ornaments) is replaced, not merged
        merged = jazz._merge({'ornaments': {'trill': 1.0}, 'lh': 'guide', 'A1': {'seed': 1}},
                             {'ornaments': {'turn': 1.0}, 'A1': {'style': 'lush'}}, {'A1'})
        self.assertEqual(merged, {'ornaments': {'turn': 1.0}, 'lh': 'guide', 'A1': {'seed': 1, 'style': 'lush'}})


class Pieces(unittest.TestCase):
    def test_slides(self):
        s = song(meter=(3, 4))
        sec = s.section('solo', 8)
        self.assertEqual(jazz.slide(10.0, -2.0), [(9.97, 0.0, 'step'), (9.99, -2.0, 'step'), (10.2, 0.0, 'smooth')])
        pts = jazz.slides(sec, [(1, 0.0, -2.0), (2, 1.5, -1.0)], length=0.22)
        self.assertEqual([p[0] for p in pts[1::3]], [3.0 - 0.01, 7.5 - 0.01])
        with self.assertRaises(ComposeError):
            jazz.slides(sec, [(1, -2.0)])

    def test_last_stir_and_bombs(self):
        c = jazz.last_stir(SWIRLY_BRUSH, 8, crash=30, kick=34, sweeps=(60, 48, 36), last=3)
        sweeps = [(n.start, n.dur, n.vel) for n in c if n.pitch == SWIRLY_BRUSH['sweep']]
        self.assertEqual(sweeps, [(0.0, 2.0, 60), (2.0, 2.0, 48), (4.0, 3.0, 36)])
        self.assertEqual(c.length, 8.0)
        b = jazz.bombs(8, SWIRLY_BRUSH, seed=2, density=0.5, vel=60)
        setups = [n for n in b if n.start % 16 == 15.5]
        self.assertEqual(len(setups), 4)                                    # kick + dig into bars 5 and 9
        self.assertEqual(list(b), list(jazz.bombs(8, SWIRLY_BRUSH, seed=2, density=0.5, vel=60)))

    def test_crushes(self):
        line = notes('C5/4 E5/2. G5/1', vel=90)
        c = pianist.crushes(line, 1.0, seed=1)
        added = [n for n in c if n not in list(line)]
        self.assertEqual([(round(n.start, 6), n.pitch) for n in added], [(0.93, 75), (3.93, 78)])   # a half step under
        self.assertTrue(all(n.vel == int(90 * 0.7) for n in added))
        self.assertEqual(len(pianist.crushes(line, 0.0)), len(line))


if __name__ == '__main__':
    unittest.main()
