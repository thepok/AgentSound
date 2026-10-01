"""Tempo map + meter in the compose layer (agentsound/tempo.py, Song): set_tempo, tempo_ramp, ritardando,
accelerando, fermata, rubato, the exact TempoMap mirror, local-tempo humanize/groove, meters per section with
every bar helper, drum grids in 3/4 and 6/8, and (with the engine built) section times and zoom --beat."""

import contextlib
import io
import json
import math
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import cli  # noqa: E402
from agentsound.modulation import lfo  # noqa: E402
from agentsound.patches import Instrument  # noqa: E402
from agentsound.patterns import Clip, drums  # noqa: E402
from agentsound.song import Song  # noqa: E402
from agentsound.tempo import MeterGrid, TempoMap  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402


def va():
    return Instrument('va', {})


def simpson(f, a, b, n=4000):
    h = (b - a) / n
    s = f(a) + f(b) + sum((4 if i % 2 else 2) * f(a + i * h) for i in range(1, n))
    return s * h / 3


class TempoMapMath(unittest.TestCase):
    def test_constant(self):
        m = TempoMap([[0, 104]])
        self.assertTrue(m.constant)
        self.assertEqual(m.seconds_at(13), 13 * 60 / 104)
        self.assertAlmostEqual(m.beat_at(m.seconds_at(7.25)), 7.25, places=12)

    def test_linear_smooth_step(self):
        m = TempoMap([[0, 120], [4, 120], [12, 60], [16, 60], [20, 140, 'smooth'], [22, 100, 'step']])
        self.assertAlmostEqual(m.seconds_between(4, 12), 60 * 8 / (60 - 120) * math.log(60 / 120), places=12)
        self.assertAlmostEqual(m.seconds_between(16, 20), 60 * 4 / math.sqrt(60 * 140), places=12)
        self.assertEqual(m.bpm_at(8), 90.0)
        self.assertEqual(m.bpm_at(21.999999), 140.0)
        self.assertEqual(m.bpm_at(22), 100.0)
        # numeric integration of 60 / bpm agrees everywhere; beat -> seconds -> beat round trips
        for b in (1.3, 5.5, 11.9, 13.0, 17.2, 19.9, 23.5):
            pieces = [0, 4, 12, 16, 20, 22]
            # piecewise (the tempo jumps at 22: each piece sees its own side of the jump)
            t = sum(simpson(lambda x, c=c: 60 / m.bpm_at(min(x, c - 1e-9)), a, min(c, b))
                    for a, c in zip(pieces, pieces[1:] + [99]) if a < b)
            self.assertAlmostEqual(m.seconds_at(b), t, places=9)
            self.assertAlmostEqual(m.beat_at(m.seconds_at(b)), b, places=9)


class TempoApi(unittest.TestCase):
    def song(self, tempo=120, bars=8):
        s = Song('t', tempo=tempo)
        s.section('a', bars=bars)
        s.track('k', va()).note('C4', 0, 1)
        return s

    def test_no_tempo_change_keeps_tempo(self):
        s = self.song()
        d = s.compile()
        self.assertEqual(d['tempo'], 120)
        self.assertNotIn('tempoMap', d)
        self.assertNotIn('meter', d)
        self.assertEqual(s.tempo_at(17), 120)
        self.assertEqual(s.seconds(8), 4.0)

    def test_set_tempo(self):
        s = self.song()
        s.set_tempo(16, 90)
        d = s.compile()
        self.assertNotIn('tempo', d)
        self.assertEqual(d['tempoMap'], [[0.0, 120.0], [16.0, 90.0, 'step']])
        self.assertEqual(s.tempo_at(15.99), 120)
        self.assertEqual(s.tempo_at(16), 90)
        self.assertAlmostEqual(s.seconds(20), 8 + 4 * 60 / 90, places=12)

    def test_ramp_and_ritardando(self):
        s = self.song()
        s.tempo_ramp(8, 16, 60)
        self.assertEqual(s.compile()['tempoMap'], [[0.0, 120.0], [8.0, 120.0], [16.0, 60.0]])
        self.assertAlmostEqual(s.seconds(16) - s.seconds(8), 60 * 8 / (60 - 120) * math.log(0.5), places=12)
        self.assertEqual(s.tempo_at(30), 60)

        s = self.song()
        sec = s['a']
        s.tracks['k'].note('E4', sec.bar(7), 2)
        s.ritardando((sec.bar(4), sec.bar(6)), to=0.75)   # a tempo afterwards (default): music follows
        pts = s.compile()['tempoMap']
        self.assertEqual(pts[:2], [[0.0, 120.0], [16.0, 120.0]])
        self.assertEqual(pts[2][1:], [90.0, 'smooth'])
        self.assertAlmostEqual(pts[2][0], 24 - 1e-4)
        self.assertEqual(pts[3], [24.0, 120.0, 'step'])
        self.assertAlmostEqual(s.tempo_at(20), 105.0, places=2)
        s2 = self.song()
        s2.ritardando(s2['a'], bpm=80, curve='linear', a_tempo=False)
        self.assertEqual(s2.compile()['tempoMap'], [[0.0, 120.0], [32.0, 80.0]])
        self.assertEqual(s2.tempo_at(40), 80)

    def test_a_tempo_returns_where_the_music_goes_on(self):
        def song():
            s = Song('at', tempo=100)
            s.section('a', bars=4)
            t = s.track('p', va())
            for b in range(8):
                t.note('C4', b, 1)
            return s, t
        # the final chord right after the ritardando keeps the slowed tempo (nothing starts after it)
        s, t = song()
        t.note('C3', 8, 8)
        s.ritardando((4, 8), to=0.8)
        self.assertAlmostEqual(s.tempo_at(8), 80.0)
        self.assertAlmostEqual(s.tempo_at(12), 80.0)
        self.assertEqual(s.compile()['tempoMap'][-1], [8.0, 80.0, 'smooth'])
        # rit. - fermata - a tempo: the held chord is at the slowed tempo, the music after it a tempo
        s, t = song()
        t.note('C3', 8, 2).note('D4', 10, 1).note('E4', 11, 1).note('C4', 12, 4)
        s.ritardando((4, 8), to=0.8)
        s.fermata(8, hold=2)                            # the chord spans beats 8..10 (the next onset)
        self.assertAlmostEqual(s.seconds(10) - s.seconds(8), (2 + 2) * 60 / 80, places=6)
        self.assertAlmostEqual(s.tempo_at(10), 100.0)
        self.assertAlmostEqual(s.tempo_at(12), 100.0)
        # without a fermata the tempo returns right at the span end
        s, t = song()
        t.note('C3', 8, 2).note('D4', 10, 1)
        s.ritardando((4, 8), to=0.8)
        self.assertAlmostEqual(s.tempo_at(8), 100.0)
        # a second ritardando starting at the span end continues from the slowed tempo
        s, t = song()
        t.note('C3', 12, 2).note('D4', 14, 1)
        s.ritardando((4, 8), to=0.9)
        s.ritardando((8, 12), to=0.8, a_tempo=False)
        self.assertAlmostEqual(s.tempo_at(12), 72.0)
        # a set_tempo at the span end wins
        s, t = song()
        t.note('C3', 12, 2)
        s.ritardando((4, 8), to=0.9)
        s.set_tempo(8, 130)
        self.assertAlmostEqual(s.tempo_at(8), 130.0)

    def test_constant_tempo_outside_the_tempo_range(self):
        s = self.song()
        s.set_tempo(0, 20)                              # "tempo" is 30..300: a one-point tempo map instead
        d = s.compile()
        self.assertNotIn('tempo', d)
        self.assertEqual(d['tempoMap'], [[0.0, 20.0]])
        s = self.song()
        s.set_tempo(0, 90)
        self.assertEqual(s.compile()['tempo'], 90)

    def test_accelerando_keeps_new_tempo(self):
        s = self.song()
        s.accelerando((8, 16), to=1.25)
        self.assertEqual(s.compile()['tempoMap'], [[0.0, 120.0], [8.0, 120.0], [16.0, 150.0, 'smooth']])
        self.assertEqual(s.tempo_at(20), 150)

    def test_strictness(self):
        s = self.song()
        s.tempo_ramp(8, 16, 90)
        with self.assertRaisesRegex(ComposeError, 'overlaps'):
            s.ritardando((12, 20), to=0.8)
        with self.assertRaisesRegex(ComposeError, 'contains the tempo change|overlaps'):
            s.set_tempo(10, 100)
        with self.assertRaisesRegex(ComposeError, 'factor must be < 1'):
            s.ritardando((20, 24), to=1.2)
        with self.assertRaisesRegex(ComposeError, 'factor must be > 1'):
            s.accelerando((20, 24), to=0.9)
        with self.assertRaisesRegex(ComposeError, "curve must be 'linear' or 'smooth'"):
            s.tempo_ramp(20, 24, 100, curve='exp')
        with self.assertRaisesRegex(ComposeError, 'empty'):
            s.ritardando((24, 24))
        with self.assertRaisesRegex(ComposeError, 'outside'):
            s.set_tempo(20, 5)
        with self.assertRaisesRegex(ComposeError, 'phrase'):
            s.rubato((20, 28), phrase='wobble')

    def test_fermata_holds_the_chord(self):
        s = Song('f', tempo=100)
        s.section('a', bars=4)
        t = s.track('p', va())
        t.play(Clip([(0, 2, 'C4', 90), (2, 2, 'E4', 90), (4, 4, 'G4', 90), (8, 4, 'C5', 90), (12, 4, 'C4', 90)], length=16), 0)
        before = s.seconds(12) - s.seconds(8)
        s.fermata(8, hold=2)                            # the chord at beat 8 rings 2 beats longer (until the next onset)
        self.assertAlmostEqual(s.seconds(12) - s.seconds(8), before + 2 * 60 / 100, places=6)
        self.assertEqual(s.tempo_at(12), 100)           # then the song goes on
        self.assertAlmostEqual(s.seconds(8), 8 * 60 / 100, places=9)
        s.fermata(12, seconds=1.5)                      # the last note: the span is its own length (4 beats)
        self.assertAlmostEqual(s.seconds(16) - s.seconds(12), 4 * 60 / 100 + 1.5, places=6)
        s.fermata(2, hold=1, length=1)                  # length= stretches just [2, 3]
        self.assertAlmostEqual(s.seconds(3) - s.seconds(2), 2 * 60 / 100, places=6)
        self.assertAlmostEqual(s.seconds(4) - s.seconds(3), 60 / 100, places=6)
        with self.assertRaisesRegex(ComposeError, 'overlaps the fermata'):
            s.fermata(10, hold=1)
            s.compile()

    def test_fermata_after_ritardando(self):
        s = Song('rf', tempo=90)
        end = s.section('end', bars=2)
        t = s.track('p', va())
        for b in range(4):
            t.note('C4', b, 1)
        t.note('C3', 4, 4)
        s.ritardando((0, 4), to=0.7, a_tempo=False)
        s.fermata(4, hold=3)                            # the final chord after the rit: 3 more beats at 63 BPM
        self.assertAlmostEqual(s.seconds(end.end) - s.seconds(4), (4 + 3) * 60 / 63, places=6)
        self.assertAlmostEqual(s.tempo_at(6), 63 * 4 / 7, places=6)   # the chord's 4 beats last 7 beats of 63 BPM
        pts = s.compile()['tempoMap']
        self.assertEqual(pts[-2], [4.0, 36.0, 'step'])
        self.assertEqual(pts[-1], [8.0, 63.0, 'step'])

    def test_rubato(self):
        s = self.song(tempo=80, bars=8)
        span = (8.0, 24.0)
        plain = s.seconds(24) - s.seconds(8)
        s.rubato(span, depth=0.05, phrase='arch', seed=3)
        m = s.tempo_map()
        self.assertAlmostEqual(m.seconds_between(*span), plain, delta=plain * 0.003)   # time taken is given back
        self.assertAlmostEqual(s.tempo_at(8), 80, places=6)                          # meets the tempo around it
        self.assertAlmostEqual(s.tempo_at(24), 80, places=6)
        inside = [s.tempo_at(8 + 0.1 * k) for k in range(161)]
        self.assertTrue(max(inside) > 81 and min(inside) < 79 and max(inside) < 80 * 1.1 and min(inside) > 80 * 0.9)
        self.assertGreater(s.tempo_at(12), 80)                                       # arch: forward first ...
        self.assertLess(s.tempo_at(20), 80)                                          # ... then broader
        self.assertEqual(s.compile()['tempoMap'], s.compile()['tempoMap'])           # deterministic
        s2 = self.song(tempo=80, bars=8)
        s2.rubato(span, depth=0.05, phrase='arch', seed=4)
        self.assertNotEqual(s.tempo_points(), s2.tempo_points())
        with self.assertRaisesRegex(ComposeError, 'overlaps the rubato'):
            s.rubato((20, 28))

    def test_rubato_breath(self):
        s = self.song(tempo=80, bars=8)
        plain = s.seconds(24) - s.seconds(8)
        s.rubato((8.0, 24.0), depth=0.04, phrase='breath', seed=1)
        self.assertAlmostEqual(s.tempo_map().seconds_between(8, 24), plain, delta=plain * 0.004)
        self.assertGreater(s.tempo_at(8 + 0.3 * 16), 80.5)              # moves on through the phrase ...
        self.assertLess(s.tempo_at(8 + 0.85 * 16), 79.0)                # ... and breathes at its end

    def test_lilt(self):
        s = Song('w', tempo=60, meter=(3, 4))
        s.section('a', bars=8)
        s.track('k', va()).note('C4', 0, 1)
        s.lilt((3, 15), beats={2: 0.1})
        spb = 1.0
        # beat 2 of every lilted bar arrives 0.1 beat late, beat 3 and the downbeats stay on the grid
        for bar in (1, 2, 3, 4):
            t0 = s.seconds(3 * bar)
            self.assertAlmostEqual(s.seconds(3 * bar + 1) - t0, 1.1 * spb, delta=0.002)
            self.assertAlmostEqual(s.seconds(3 * bar + 2) - t0, 2.0 * spb, delta=0.002)
        self.assertAlmostEqual(s.seconds(15) - s.seconds(3), 12.0, delta=0.002)   # each bar gives its time back
        self.assertAlmostEqual(s.seconds(1), 1.0, places=6)                         # bar 0 is outside the span
        self.assertAlmostEqual(s.tempo_at(3), 60.0, places=3)                       # continuous at the downbeat
        self.assertEqual(s.compile()['tempoMap'], s.compile()['tempoMap'])           # deterministic
        # jitter: seeded per-beat deviations (both hands move together), the bars keep their length
        j1 = Song('w', tempo=60, meter=(3, 4), seed=3)
        j1.section('a', bars=8)
        j1.track('k', va()).note('C4', 0, 1)
        j1.lilt(j1['a'], jitter=0.05)
        devs = [j1.seconds(3 * b + k) - j1.seconds(3 * b) - k for b in range(8) for k in (1, 2)]
        self.assertTrue(0.01 < (sum(d * d for d in devs) / len(devs)) ** 0.5 < 0.12)
        self.assertAlmostEqual(j1.seconds(24), 24.0, delta=0.003)
        j2 = Song('w', tempo=60, meter=(3, 4), seed=4)
        j2.section('a', bars=8)
        j2.track('k', va()).note('C4', 0, 1)
        j2.lilt(j2['a'], jitter=0.05)
        self.assertNotEqual(j1.tempo_points(), j2.tempo_points())
        # 4/4 and a rubato on top: both apply
        r = self.song(tempo=90, bars=4)
        r.rubato((0, 16), depth=0.03, phrase='arch', seed=2)
        base = r.seconds(5) - r.seconds(4)
        r.lilt((0, 16), beats={2: 0.08, 4: -0.05})
        self.assertAlmostEqual(r.seconds(5) - r.seconds(4), base + 0.08 * 60 / 90, delta=0.01)
        self.assertAlmostEqual(r.seconds(16), 16 * 60 / 90, delta=0.01)
        with self.assertRaisesRegex(ComposeError, 'overlaps the lilt'):
            r.lilt((8, 12), beats={2: 0.1})
        with self.assertRaisesRegex(ComposeError, 'inner beat number'):
            self.song().lilt((0, 8), beats={1: 0.1})
        with self.assertRaisesRegex(ComposeError, 'outside'):
            self.song().lilt((0, 8), beats={2: 0.5})
        with self.assertRaisesRegex(ComposeError, 'no whole bar'):
            self.song().lilt((1, 3), beats={2: 0.1})

    def test_humanize_and_groove_use_the_local_tempo(self):
        s = Song('g', tempo=120)
        s.section('fast', bars=4)
        slow = s.section('slow', bars=4)
        s.set_tempo(slow, 60)
        t = s.track('p', va()).groove('laidback')       # melodic parts 4 ms late, wherever they are
        for b in range(32):
            t.note('C4', b, 0.5)
        notes = s.compile()['tracks'][0]['notes']
        for (start, *_), b in zip(notes, range(32)):
            self.assertAlmostEqual((s.seconds(start) - s.seconds(b)) * 1000, 4.0, places=2)
        h = Song('h', tempo=120)
        h.section('fast', bars=4)
        h.set_tempo(h.section('slow', bars=4), 40)
        tr = h.track('p', va()).humanize(timing_ms=10, vel=0, seed=1)
        for b in range(32):
            tr.note('C4', b + 0.5, 0.25)
        for start, *_ in h.compile()['tracks'][0]['notes']:
            b = round(start - 0.5)
            self.assertLessEqual(abs(h.seconds(start) - h.seconds(b + 0.5)), 0.0100001)


class Meter(unittest.TestCase):
    def test_sections_bars_and_helpers(self):
        s = Song('m', tempo=120)
        a = s.section('a', bars=4)
        w = s.section('waltz', bars=4, meter=(3, 4))
        j = s.section('jig', bars=2, meter='6/8')
        e = s.section('end', bars=2)
        self.assertEqual((w.start, w.end, w.beats_per_bar, w.meter), (16.0, 28.0, 3.0, (3, 4)))
        self.assertEqual((j.start, j.end, j.beats_per_bar), (28.0, 34.0, 3.0))       # 6/8 = 3 quarter-note beats
        self.assertEqual(w.bar(2), 22.0)
        self.assertEqual(w.bar(-1), 25.0)
        self.assertEqual(w.bar_starts(), [16.0, 19.0, 22.0, 25.0])
        self.assertEqual([s.bar(n) for n in (0, 3, 4, 5, 8, 9, 10, 11)], [0, 12, 16, 19, 28, 31, 34, 38])
        self.assertEqual(s.bars_after(12, 2), 19.0)                                  # 1 bar of 4/4, then 1 of 3/4
        self.assertEqual(s.bars_after(w, 5), 31.0)
        self.assertEqual(s.meter_at(30), (6, 8))
        self.assertEqual(s.meter_grid().bar_at(e.start), 10.0)
        t = s.track('p', va())
        t.loop(Clip([(0, 1, 'C4', 90)], length=1), w.start, bars=2)                 # two 3/4 bars = 6 beats
        self.assertEqual(max(n.start for n in t.notes), 21.0)
        prog = s.prog('I IV', meter=w.meter)
        self.assertEqual(prog.length, 6.0)
        d = s.compile()
        self.assertEqual(d['meter'], [[0.0, 4, 4], [16.0, 3, 4], [28.0, 6, 8], [34.0, 4, 4]])
        self.assertIn('waltz', s.describe())

    def test_song_default_meter_and_partial_bars(self):
        s = Song('three', tempo=90, meter=(3, 4))
        a = s.section('a', bars=4)
        self.assertEqual((a.end, s.meter, s.bar(2)), (12.0, (3, 4), 6.0))
        s.track('p', va()).note('C4', 0, 1)
        self.assertEqual(s.compile()['meter'], [[0.0, 3, 4]])
        p = Song('pickup', tempo=100)
        p.section('intro', bars=4.5)                   # 18 beats: half a 4/4 bar at the end
        p.section('waltz', bars=2, meter=(3, 4))
        self.assertEqual(p._meter_points(), [[0.0, 4, 4], [16.0, 2, 4], [18.0, 3, 4]])
        MeterGrid(p._meter_points())                    # valid for the engine's bar lines
        u = Song('upbeat', tempo=100)
        u.section('pickup', bars=0.25)                 # one beat of anacrusis
        u.section('verse', bars=4)
        self.assertEqual(u._meter_points(), [[0.0, 1, 4], [1.0, 4, 4]])   # the verse's bars start at the verse
        q = Song('odd', tempo=100)
        q.section('x', bars=1.3)                       # 5.2 beats: no meter can end there
        q.section('y', bars=1, meter=(3, 4))
        self.assertEqual(q._meter_points(), [[0.0, 4, 4], [4.0, 3, 4]])    # the 3/4 starts at the bar line before

    def test_drum_grids_in_three_and_six_eight(self):
        s = Song('d', tempo=100)
        w = s.section('waltz', bars=4, meter=(3, 4))
        j = s.section('jig', bars=4, meter=(6, 8))
        kit = s.track('kit', Instrument('drums', {}))
        waltz = drums({'kick': 'x...........', 'hat': '....x...x...'}, step='1/16')    # 12 sixteenths = one 3/4 bar
        jig = drums({'kick': 'x.....', 'snare': '...x..'}, step='1/8')                 # 6 eighths = one 6/8 bar
        self.assertEqual((waltz.length, jig.length), (3.0, 3.0))
        kit.loop(waltz, w).loop(jig, j)
        kicks = [n.start for n in kit.notes if n.pitch == 36]
        self.assertEqual(kicks, w.bar_starts() + j.bar_starts())                       # one kick on every bar's "1"
        snares = [n.start for n in kit.notes if n.pitch == 38]
        self.assertEqual(snares, [b + 1.5 for b in j.bar_starts()])                    # 6/8: the second dotted quarter
        self.assertEqual(drums({'kick': 'x'}, bars=1, beats_per_bar=j.beats_per_bar).length, 3.0)

    def test_modulator_bars_follow_the_meter(self):
        s = Song('mb', tempo=100)
        s.section('four', bars=2)
        w = s.section('waltz', bars=4, meter=(3, 4))
        t = s.track('p', va())
        t.note('C4', 0, 4)
        t.modulate('pan', lfo('sine', rate='1 bar', depth=0.3), window=w)
        t.modulate('gainDb', lfo('sine', rate='1 bar', depth=2))
        mods = s.compile()['tracks'][0]['modulators']
        self.assertEqual([m['source']['rateBeats'] for m in mods], [3.0, 4.0])


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


SONG = '''
from agentsound import *

def build():
    s = Song('Tempo Cli', tempo=112, key='A minor', seed=2)
    a = s.section('a', bars=2)
    b = s.section('waltz', bars=2, meter=(3, 4))
    c = s.section('end', bars=1)
    keys = s.track('keys', inst.va(amp__release=0.2))
    for x in range(int(c.end)):
        keys.note('A4', x, 0.5)
    s.ritardando(b, to=0.7, a_tempo=False)
    s.fermata(c.start, length=2, hold=2)
    s.master.add(fx.limiter())
    return s
'''


@unittest.skipIf(_engine() is None, 'engine not built (set AGENTSOUND_TEST_ENGINE or build build/agentsound.exe)')
class EngineTempo(unittest.TestCase):
    def test_report_times_and_zoom_beat(self):
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_tempo_'))
        self.addCleanup(shutil.rmtree, d, True)
        (d / 'song.py').write_text(SONG, encoding='utf-8')
        out = d / 'out'
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = cli.main(['build', str(d), '--no-mp3', '--out', str(out), '--engine', str(_engine())])
        self.assertEqual(code, 0, err.getvalue())
        song = cli.load_song(d / 'song.py')
        rep = json.loads((out / 'report.json').read_text(encoding='utf-8'))
        secs = {x['name']: x for x in rep['sections']}
        for sec in song.sections:                        # section times in the report = the song's tempo map
            self.assertAlmostEqual(secs[sec.name]['startSec'], song.seconds(sec.start), delta=0.006)
            self.assertAlmostEqual(secs[sec.name]['endSec'], song.seconds(sec.end), delta=0.006)
        self.assertEqual(secs['waltz']['meter'], '3/4')
        self.assertEqual((secs['waltz']['startBar'], secs['end']['startBar']), (3.0, 5.0))
        self.assertIn('tempo map', rep['summary'])
        self.assertIn('tempoMap', rep['render'])
        # zoom --beat through the tempo map: the view is centred on the beat's song time
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(['zoom', str(out / 'mix.wav'), '--beat', '13', '--engine', str(_engine())])
        self.assertEqual(code, 0)
        png = next((out / 'zooms').glob('zoom_beat13_mix.png'))
        self.assertTrue(png.is_file())
        engine_out = cli.subprocess.run([str(_engine()), 'zoom', str(out / 'mix.wav'), '--beat', '13', '--song', str(out / 'report.json'),
                                         '--out', str(d / 'z.png')], capture_output=True, text=True)
        res = json.loads(engine_out.stdout.strip().splitlines()[-1])
        self.assertAlmostEqual(res['sec'], song.seconds(13), places=6)
        self.assertAlmostEqual(res['beat'], 13.0, places=3)
