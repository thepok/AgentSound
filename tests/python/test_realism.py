"""Realism: per-note articulations (keyswitch notes at compile), legato / glide / detached marks, expression and
vibrato lanes (agentsound/articulation.py), live SFZ dynamics and keyswitches (sfz.py), inst.sfz_multi, the jazz
horn wiring. Synthetic .sfz / .wav sets in a temp folder (always run); engine renders when the engine is built."""

import cmath
import json
import math
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Clip, Song, cli, jazz, sfz  # noqa: E402
from agentsound import articulation as art  # noqa: E402
from agentsound.patches import inst  # noqa: E402
from agentsound.song import dumps  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402


def write_wav(path: pathlib.Path, freq: float, seconds: float = 1.0, sr: int = 48000, amp: float = 0.5):
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(seconds * sr)
    data = b''.join(struct.pack('<h', int(round(amp * 32767 * math.sin(2 * math.pi * freq * i / sr)))) for i in range(n))
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data)
    return path


def engine_or_none():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except Exception:  # noqa: BLE001 - CliError when the engine is not built
        return None


class Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_realism_'))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def sfz(self, name: str, text: str, wavs: dict) -> str:
        for f, hz in wavs.items():
            if not (self.dir / f).exists():
                write_wav(self.dir / f, hz)
        p = self.dir / name
        p.write_text(text, encoding='utf-8')
        return str(p)

    def ks_file(self) -> str:
        return self.sfz('ks.sfz', '''<global> sw_lokey=24 sw_hikey=26 sw_default=24
<group> sw_last=24 sw_label=Sustain
<region> sample=sus.wav lokey=48 hikey=84 pitch_keycenter=69
<group> sw_last=25 sw_label=Staccato
<region> sample=stac.wav lokey=48 hikey=84 pitch_keycenter=69
<group> sw_last=26 sw_label=Pizzicato
<region> sample=pizz.wav lokey=48 hikey=84 pitch_keycenter=69
''', {'sus.wav': 440.0, 'stac.wav': 660.0, 'pizz.wav': 880.0})


# ------------------------------------------------------------------------------------------------ marks

class Marks(unittest.TestCase):
    LINE = Clip([(0, 1, 'A4', 80), (1, 0.5, 'B4', 90), (1.5, 0.5, 'C5', 90), (2, 2, 'E5', 100)], length=4)

    def test_marks_survive_transforms(self):
        c = self.LINE.articulate('Staccato', span=(1, 2))
        self.assertEqual([art.articulation_of(n) for n in c], [None, 'staccato', 'staccato', None])
        t = c.transpose(2).shift(4).velocity(0.8).gate(0.9).humanize(4, 3, bpm=100, seed=1)
        self.assertEqual(sorted(str(art.articulation_of(n)) for n in t), ['None', 'None', 'staccato', 'staccato'])
        self.assertEqual([art.articulation_of(n) for n in art.plain(c)], [None] * 4)
        self.assertEqual(c, self.LINE)   # marks are not part of the note values
        g = self.LINE.glide(150, where=art.leaps(4))
        self.assertEqual([art.glide_of(n) for n in g], [None, None, None, 150.0])   # C5 -> E5: a leap of 4
        with self.assertRaises(ComposeError):
            self.LINE.glide(5000)
        n = art.note(0, 1, 'C4', 90, 'pizz', glide_ms=80)
        self.assertEqual((art.articulation_of(n), art.glide_of(n), n.pitch), ('pizz', 80.0, 60))

    def test_legato_and_detached(self):
        c = Clip([(0, 0.9, 60, 90), (1, 0.4, 62, 90), (1.5, 0.5, 64, 90), (3, 1, 65, 90)], length=4)
        tied = art.legato(c, overlap=0.05)
        self.assertEqual([round(n.dur, 3) for n in tied], [1.05, 0.55, 0.5, 1.0])   # the rest before beat 3 stays
        marked = art.legato(c.articulate('spiccato', span=(1, 1.4)), overlap=0.05)
        self.assertEqual([round(n.dur, 3) for n in marked], [0.9, 0.4, 0.5, 1.0])   # nothing ties into / out of it
        self.assertTrue(art.detached('staccato') and art.detached('Pizzicato') and not art.detached('sustain'))

    def test_bow_changes_and_humanized_starts(self):
        c = art.legato(Clip([(i, 1, 60 + i % 5, 90) for i in range(12)], length=12), overlap=0.05)
        bowed = art.bow_changes(c, bpm=60, max_seconds=4.0, gap_ms=100)
        cut = [n for n in bowed if n.start + n.dur < n.start + 1.0]
        self.assertEqual(len(cut), 2)                                              # every ~4 s a new bow
        self.assertAlmostEqual(cut[0].start + cut[0].dur, cut[0].start + 1 - 0.1, places=6)
        h = sorted(art.humanize_starts(c, bpm=100, ms=10, late_ms=20, seed=3))
        for a, b in zip(sorted(c), h):
            self.assertTrue(0.0 <= (b.start - a.start) * 600 <= 30.0 + 1e-6)      # 20 ms late +- 10 ms
        for k in range(len(h) - 1):                                                # tied notes keep their overlap
            self.assertAlmostEqual(h[k].start + h[k].dur - h[k + 1].start, 0.05, places=9)
        self.assertAlmostEqual(h[-1].start + h[-1].dur, 12.0, places=9)           # a phrase end stays put
        loose = Clip([(0, 0.5, 60, 90), (1, 0.5, 62, 90)], length=2)
        for a, b in zip(sorted(loose), sorted(art.humanize_starts(loose, bpm=100, ms=10, seed=1))):
            self.assertAlmostEqual(a.start + a.dur, b.start + b.dur, places=9)     # untied notes: the ends stay

    def test_auto_articulate(self):
        c = Clip([(0, 0.25, 60, 90), (0.25, 0.25, 62, 90), (1, 2, 64, 90), (3, 0.5, 67, 120)], length=4)
        out = art.auto_articulate(c, names=['Sustain Vibrato', 'Spiccato', 'Marcato (looped)'], short=0.5)
        self.assertEqual([art.articulation_of(n) for n in out],
                         ['spiccato', 'spiccato', 'sustain vibrato', 'marcato (looped)'])
        out = art.auto_articulate(c, names=['long', 'short'])
        self.assertEqual([art.articulation_of(n) for n in out], ['short', 'short', 'long', 'long'])
        with self.assertRaises(ComposeError):
            art.auto_articulate(c, inst.va())


class Lanes(unittest.TestCase):
    def test_expression_shapes_and_continuity(self):
        c = Clip([(0, 2, 60, 127), (4, 1, 62, 64), (5, 3, 64, 64)], length=8)
        pts = art.expression_points(c, ['cresc', 'flat', 'dim'], lo=0.0, hi=1.0)
        self.assertEqual(pts[0][:2], (0.0, 0.5))                      # cresc starts at half the level
        self.assertAlmostEqual(pts[1][1], 1.0)                        # ... and ends at 1.2 x (clamped)
        self.assertEqual(pts[2], (4.0, round(64 / 127, 5), 'step'))  # after a rest: a step to its level
        tied = art.legato(c)
        tp = art.expression_points(tied, ['flat', 'flat', 'swell'], lo=0.0, hi=1.0)
        at5 = [p for p in tp if abs(p[0] - 5.0) < 1e-9]
        self.assertEqual(at5[0][1], round(64 / 127, 5))              # a tied note continues from the line's level
        self.assertNotEqual(at5[0][2], 'step')
        for kind in art.SHAPES:
            self.assertTrue(art.expression_points(c, kind))
        with self.assertRaises(ComposeError):
            art.expression_points(c, 'wobble')

    def test_vibrato_points(self):
        c = Clip([(0, 0.5, 60, 90), (1, 3, 62, 90)], length=4)
        lanes = art.vibrato_points(c, bpm=60, depth=20, rate=5, delay=0.5, grow=1.0, spread=0.0, rise=0.0)
        d = lanes['instrument.vibrato']
        self.assertEqual(d[0], (0.0, 0.0))
        self.assertIn((1.0, 0.0, 'step'), d)                           # the long note starts straight
        self.assertIn((1.5, 0.0), d)                                  # delay 0.5 s
        self.assertTrue(any(abs(p[1] - 20.0) < 1e-6 for p in d))      # full depth after the growth
        self.assertEqual(lanes['instrument.vibratorate'][0], (1.0, 5.0, 'step'))
        self.assertEqual(art.vibrato_points(Clip([(0, 0.5, 60, 90)], length=1), bpm=60), {})


# ------------------------------------------------------------------------------------------------ compile

class Compile(Tmp):
    def song(self, sound, clip, **kw):
        s = Song('t', tempo=120)
        a = s.section('a', bars=2)
        t = s.track('x', sound, **kw)
        t.play(clip, a)
        return s, t

    def test_keyswitch_insertion_and_pruning(self):
        ins = inst.sfz(self.ks_file())
        self.assertEqual(ins.info['sfz']['keyswitches'], {'Sustain': 24, 'Staccato': 25, 'Pizzicato': 26})
        line = Clip([(0, 1, 'A4', 90), (1, 0.5, 'B4', 90), (1.5, 0.5, 'C5', 90), (2, 1, 'D5', 90)], length=8)
        s, _ = self.song(ins, line.articulate('stac', span=(1, 2)))
        d = s.compile()['tracks'][0]
        self.assertEqual(d['notes'], [[0.0, 1.0, 69, 90], [1.0, 1.0, 25, 1], [1.0, 0.5, 71, 90], [1.5, 0.5, 72, 90],
                                      [2.0, 6.0, 24, 1], [2.0, 1.0, 74, 90]])
        files = sorted(os.path.basename(z['file']) for z in d['instrument']['params']['samples'])
        self.assertEqual(files, ['stac.wav', 'sus.wav'])              # pizzicato is never selected: not loaded
        s2, _ = self.song(inst.sfz(self.ks_file()), line)            # no marks: only the default articulation
        d2 = s2.compile()['tracks'][0]
        self.assertEqual([n[2] for n in d2['notes']], [69, 71, 72, 74])
        self.assertEqual([os.path.basename(z['file']) for z in d2['instrument']['params']['samples']], ['sus.wav'])
        for bad in ('legato', 30):
            s3, _ = self.song(inst.sfz(self.ks_file()), line.articulate(bad))
            with self.assertRaises(ComposeError):
                s3.compile()
        s4, _ = self.song(inst.va(), line.articulate('staccato'))
        with self.assertRaisesRegex(ComposeError, 'sampler'):
            s4.compile()
        # keyswitch notes written by hand switch too: their articulation's zones are not pruned
        s5, _ = self.song(inst.sfz(self.ks_file()), Clip([(0, 4, 26, 1), (0, 1, 'A4', 90), (2, 1, 'B4', 90)], length=8))
        d5 = s5.compile()['tracks'][0]
        self.assertEqual(sorted(os.path.basename(z['file']) for z in d5['instrument']['params']['samples']),
                         ['pizz.wav', 'sus.wav'])

    def test_track_note_art_and_groove_keep_marks(self):
        s = Song('t', tempo=120)
        a = s.section('a', bars=1)
        t = s.track('x', inst.sfz(self.ks_file())).groove('swing8')
        t.note('A4', a.start, 0.5, art='pizz').note('A4', a.start + 0.5, 0.5).note('A4', a.start + 1.5, 0.5, art='stac')
        notes = s.compile()['tracks'][0]['notes']
        ks = [(n[0], n[2]) for n in notes if n[2] < 30]
        self.assertEqual([k for _, k in ks], [26, 24, 25])
        regular = {n[0] for n in notes if n[2] >= 30}
        self.assertTrue(all(b in regular for b, _ in ks))              # each switch lands exactly on its note

    def test_glide_marks_and_detached_notes(self):
        ins = inst.sfz(self.ks_file(), mono='legato')
        line = art.legato(Clip([(0, 1, 'A4', 90), (1, 1, 'E5', 90), (2, 0.5, 'D5', 90), (2.5, 0.5, 'C5', 90)],
                               length=4).articulate('stac', span=(2, 3)))
        line = line.glide(140, where=art.leaps(5))
        s, _ = self.song(ins, line)
        d = s.compile()['tracks'][0]
        auto = {a['target']: a['points'] for a in d['automation']}
        self.assertIn('instrument.glide', auto)
        g = auto['instrument.glide']
        self.assertEqual(g[0], [0.0, 0.0])
        self.assertTrue(any(p[1] == 140.0 and 0.5 <= p[0] < 1.0 for p in g))   # up just before the leap note
        self.assertTrue(any(p[1] == 0.0 and 1.0 < p[0] < 1.01 for p in g))     # back right after it
        regular = [n for n in d['notes'] if n[2] >= 30]
        d5 = [n for n in regular if n[2] == 74][0]
        self.assertLess(d5[0] + d5[1], 2.5 - 0.005)                   # a staccato note never touches the next one
        s2, t2 = self.song(inst.sfz(self.ks_file()), line)
        s2.compile()
        self.assertTrue(any("mono='legato'" in w for w in s2.warnings))
        s3, t3 = self.song(inst.sfz(self.ks_file(), mono='legato'), line)
        t3.automate('instrument.glide', [(0, 50)])
        with self.assertRaises(ComposeError):
            s3.compile()
        self.assertFalse(any('no note sounding into them' in w for w in s.warnings))
        # a glide into a note after a rest (or after a detached note) bends from nothing: a warning names it
        loose = Clip([(0, 1, 'A4', 90), (2, 1, 'E5', 90)], length=4).glide(120, span=(2, 3))
        s6, _ = self.song(inst.sfz(self.ks_file(), mono='legato'), loose)
        s6.compile()
        self.assertTrue(any('no note sounding into them' in w and 'beat(s) 2' in w for w in s6.warnings), s6.warnings)

    def test_sfz_multi(self):
        a = self.sfz('a.sfz', '<region> sample=a1.wav key=60 group=1 off_by=1\n<region> sample=a2.wav key=62\n',
                     {'a1.wav': 262.0, 'a2.wav': 294.0})
        b = self.sfz('b.sfz', '<region> sample=b1.wav key=60 group=1 off_by=1\n', {'b1.wav': 523.0})
        ins = inst.sfz_multi({'legato': a, 'short': {'path': b, 'gain': -3}}, keyswitch='C0', default='legato',
                             mono='legato')
        zones = ins.params['samples']
        self.assertEqual(ins.info['sfz']['keyswitches'], {'legato': 12, 'short': 13})
        self.assertEqual([z['swLast'] for z in zones], [12, 12, 13])
        self.assertEqual({z['swDefault'] for z in zones}, {12})
        self.assertEqual((zones[0]['swLo'], zones[0]['swHi']), (12, 13))
        self.assertEqual([(z.get('group'), z.get('offBy')) for z in zones], [(1, 1), (None, None), (2, 2)])
        self.assertEqual(zones[2]['gain'], -3)
        lazy = inst.sfz_multi({'legato': a, 'short': b}, lazy=True)
        self.assertIsNotNone(lazy.lazy)
        self.assertEqual(lazy.to_dict()['params']['samples'][2]['swLast'], 1)
        self.assertEqual(art.available(lazy), ['legato', 'short'])
        with self.assertRaises(ComposeError):
            inst.sfz_multi({'a': a}, default='b')
        with self.assertRaises(ComposeError):
            inst.sfz_multi({'a': {'file': a}})

    def test_perform(self):
        s = Song('t', tempo=90)
        a = s.section('a', bars=2)
        sus = self.sfz('s.sfz', '<region> sample=sus.wav lokey=40 hikey=90 pitch_keycenter=69\n', {'sus.wav': 440.0})
        stac = self.sfz('t.sfz', '<region> sample=stac.wav lokey=40 hikey=90 pitch_keycenter=69\n', {'stac.wav': 660.0})
        t = s.track('x', inst.sfz_multi({'sustain': sus, 'staccato': stac}, mono='legato', layers='dynamics'))
        line = Clip([(0, 1, 'A4', 90), (1, 0.25, 'B4', 90), (1.25, 0.25, 'C5', 90), (2, 3, 'E5', 100)], length=8)
        played = art.perform(t, line, a, humanize_ms=0, seed=1)
        self.assertEqual([art.articulation_of(n) for n in played], ['sustain', 'staccato', 'staccato', 'sustain'])
        d = s.compile()['tracks'][0]
        targets = {x['target'] for x in d['automation']}
        self.assertTrue({'instrument.dynamics', 'instrument.vibrato', 'instrument.vibratorate'} <= targets)
        self.assertEqual([n[2] for n in d['notes'] if n[2] < 30], [1, 0])   # switches: to staccato and back


# ------------------------------------------------------------------------------------------------ sfz import

class LiveSfz(Tmp):
    def test_live_dynamics_fields(self):
        p = self.sfz('dyn.sfz', '''<control> set_cc1=64
<group> gain_cc1=24 volume=-12 cutoff=800 cutoff_cc1=2400 fil_type=lpf_2p
<region> sample=p.wav key=60 xfout_locc1=40 xfout_hicc1=90
<region> sample=f.wav key=60 xfin_locc1=40 xfin_hicc1=90 xf_cccurve=gain
<region> sample=p.wav key=62 hicc1=63
<region> sample=f.wav key=62 locc1=64 amplitude_oncc1=100
''', {'p.wav': 440.0, 'f.wav': 660.0})
        zones, info = sfz.load(p)
        z0, z1, z2, z3 = zones
        self.assertEqual((z0['xfoutLoDyn'], z0['xfoutHiDyn']), (40, 90))
        self.assertEqual((z1['xfinLoDyn'], z1['xfinHiDyn'], z1['xfDynCurve']), (40, 90, 'gain'))
        self.assertEqual(z0['gain'], -12)                        # the controller's part of the level is live
        self.assertEqual(z0['dynGain'][0], [0, 1.0])
        self.assertAlmostEqual(z0['dynGain'][-1][1], 10 ** (24 / 20), places=4)
        self.assertEqual((z0['cutoff'], z0['dynCutoff']), (800.0, 2400.0))
        self.assertEqual((z2.get('dynHi'), z3.get('dynLo')), (63, 64))
        self.assertAlmostEqual(z3['dynGain'][-1][1], 10 ** (24 / 20), places=4)       # volume x amplitude
        self.assertAlmostEqual(z3['dynGain'][1][1], 8 / 127 * 10 ** (24 * 8 / 127 / 20), places=4)
        self.assertEqual(info['params'], {'dynamics': round(64 / 127, 6), 'dyntone': 0.0})
        static, sinfo = sfz.load(p, dyn_cc=None)
        self.assertEqual(sinfo['params'], {})
        self.assertFalse(any(k in z for z in static for k in ('dynGain', 'xfinLoDyn', 'dynCutoff', 'dynLo')))
        self.assertEqual(len(static), 3)                         # static: the layer condition picks one on key 62
        ins = inst.sfz(p, dynamics=0.2)
        self.assertEqual(ins.params['dynamics'], 0.2)            # given params win over the import's
        self.assertEqual(inst.sfz(p).params['dynamics'], round(64 / 127, 6))

    def test_expression_controller_and_none(self):
        p = self.sfz('cc11.sfz', '<region> sample=p.wav key=60 amplitude_oncc11=100\n', {'p.wav': 440.0})
        zones, info = sfz.load(p)
        self.assertEqual(info['dynamics']['cc'], 11)
        self.assertEqual(info['params'], {'dynamics': 1.0})       # CC11 = 127 by default: the static sound
        q = self.sfz('vib.sfz', '<region> sample=p.wav key=60 pitchlfo_depth_oncc1=50 pitchlfo_freq=5\n', {})
        self.assertNotIn('dynamics', sfz.load(q)[1])              # CC1 as vibrato is no dynamics controller

    def test_expression_target_follows_what_dynamics_moves(self):
        plain = self.sfz('plain.sfz', '<region> sample=p.wav key=60\n', {'p.wav': 440.0})
        lvl = self.sfz('lvl2.sfz', '<region> sample=p.wav key=60 amplitude_oncc1=100\n', {})
        line = Clip([(0, 2, 60, 90)], length=2)
        for sound, want in ((inst.sfz(plain), 'instrument.expression'),            # dynamics would only tilt the tone
                            (inst.sfz(plain, dynrange=12), 'instrument.dynamics'),
                            (inst.sfz(plain, layers='dynamics'), 'instrument.dynamics'),
                            (inst.sfz(lvl), 'instrument.dynamics'),
                            (inst.sfz(lvl, lazy=True), 'instrument.dynamics')):
            s = Song('t', tempo=120)
            a = s.section('a', bars=1)
            t = s.track('x', sound)
            t.play(line, a)
            art.expression(t, line, a, 'swell')
            self.assertEqual([x['target'] for x in s.compile()['tracks'][0]['automation']], [want])

    def test_level_only_controller_below_the_top_keeps_the_default_tone(self):
        # CC1 moves only the level and defaults to 0 (no set_cc1): dynamics starts at 0, where the 'dyntone' tilt
        # would darken the static sound - the import turns it off so the default sound stays the file's own
        p = self.sfz('lvl.sfz', '<region> sample=p.wav key=60 amplitude_oncc1=100\n', {'p.wav': 440.0})
        self.assertEqual(sfz.load(p)[1]['params'], {'dynamics': 0.0, 'dyntone': 0.0})
        self.assertEqual(inst.sfz(p, dyntone=0.6).params['dyntone'], 0.6)    # opt in


# ------------------------------------------------------------------------------------------------ jazz

class JazzWiring(Tmp):
    def test_sampler_vibrato_and_glides(self):
        melody = Clip([(0, 0.5, 'D4', 90), (0.5, 3.5, 'F4', 95), (4, 0.5, 'A3', 90), (4.5, 3.5, 'D4', 95)], length=8)
        line = jazz.horn_line(melody, 90, glide=1.0, scoop=0, fall=0, seed=2)
        self.assertTrue(any(art.glide_of(n) for n in line.clip))
        plain = jazz.horn_line(melody, 90, scoop=0, fall=0, seed=2)
        self.assertEqual(list(plain.clip), list(line.clip))       # glide=1 changes marks only, not the notes
        s = Song('t', tempo=90)
        a = s.section('a', bars=3)
        sx = s.track('sax', inst.sfz(self.ks_file(), mono='legato'))
        line.place(sx, a)
        d = s.compile()['tracks'][0]
        targets = {x['target'] for x in d['automation']}
        self.assertTrue({'instrument.vibrato', 'instrument.vibratorate', 'instrument.glide'} <= targets)
        self.assertNotIn('modulators', d)
        self.assertIn('dynamics', jazz.EXPRESSION_PARAMS)


# ------------------------------------------------------------------------------------------------ engine

def tone(x, sr, start, n, hz):
    acc = 0j
    for i in range(n):
        w = 0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1))
        acc += w * x[start + i] * cmath.exp(-2j * math.pi * hz * i / sr)
    return 4 * abs(acc) / n


@unittest.skipIf(engine_or_none() is None, 'engine not built')
class EngineRender(Tmp):
    def render(self, song) -> tuple[list, int]:
        rj = self.dir / 'song.render.json'
        rj.write_text(dumps(song.compile()), encoding='utf-8')
        out = self.dir / 'out'
        proc = subprocess.run([str(engine_or_none()), 'render', str(rj), '--out', str(out), '--no-analysis', '--no-png',
                               '--quiet'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with wave.open(str(out / 'mix.wav'), 'rb') as w:
            sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
            raw = w.readframes(n)
        if sw == 3:
            vals = [int.from_bytes(raw[i:i + 3], 'little', signed=True) / 8388608 for i in range(0, len(raw), 3)]
        elif sw == 4:
            vals = list(struct.unpack(f'<{len(raw) // 4}f', raw))
        else:
            vals = [v / 32768 for v in struct.unpack(f'<{len(raw) // 2}h', raw)]
        return [sum(vals[i * ch:(i + 1) * ch]) / ch for i in range(len(vals) // ch)], sr

    def test_articulations_switch_per_note(self):
        s = Song('t', tempo=120)
        a = s.section('a', bars=2)
        t = s.track('x', inst.sfz(self.ks_file(), release=0.01))
        t.play(Clip([(0, 0.8, 'A4', 100), (1, 0.8, 'A4', 100), (2, 0.8, 'A4', 100), (3, 0.8, 'A4', 100)],
                    length=8).articulate('stac', span=(1, 2)).articulate('pizz', span=(2, 3)), a)
        x, sr = self.render(s)
        got = []
        for beat in range(4):
            at = int((beat * 0.5 + 0.1) * sr)
            amps = {hz: tone(x, sr, at, 4096, hz) for hz in (440.0, 660.0, 880.0)}
            got.append(max(amps, key=amps.get))
        self.assertEqual(got, [440.0, 660.0, 880.0, 440.0])      # sustain, staccato, pizzicato, back to the default

    def test_glide_mark_reaches_the_engine(self):
        # compile -> render: a glide mark on a tied note bends A4 -> C5 over 200 ms (the 'glide' step lands before
        # the note-on, which latches it)
        p = self.sfz('sine.sfz', '<region> sample=long.wav lokey=40 hikey=90 pitch_keycenter=69 loop_mode=loop_continuous\n',
                     {})
        write_wav(self.dir / 'long.wav', 440.0, seconds=3.0)
        s = Song('t', tempo=120)
        a = s.section('a', bars=1)
        t = s.track('x', inst.sfz(p, mono='legato', glideshape='linear', release=0.05))
        t.play(art.legato(Clip([(0, 1, 'A4', 100), (1, 2, 'C5', 100)], length=4)).glide(200, span=(1, 2)), a)
        x, sr = self.render(s)

        def hz(t0, t1):
            i0, i1 = int(t0 * sr), int(t1 * sr)
            ups = [i for i in range(i0 + 1, i1) if x[i - 1] < 0 <= x[i]]
            return sr * (len(ups) - 1) / (ups[-1] - ups[0])
        mid = 1200 * math.log2(hz(0.59, 0.61) / 440.0)             # halfway through the glide (linear): ~150 ct
        end = 1200 * math.log2(hz(0.9, 1.1) / 440.0)               # at C5: 300 ct
        self.assertAlmostEqual(mid, 150, delta=25)
        self.assertAlmostEqual(end, 300, delta=3)


if __name__ == '__main__':
    unittest.main()
