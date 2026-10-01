"""SFZ import (agentsound/sfz.py, inst.sfz, zone pruning, `sfz` CLI, catalog summaries, sampled patches).

The synthetic tests build small .sfz + .wav sets in a temp folder and always run. Tests against the downloaded
packs run only when the pack is installed ($AGENTSOUND_SAMPLES or assets/samples) and, for renders, when the engine
is built."""

import contextlib
import io
import json
import math
import os
import pathlib
import struct
import sys
import tempfile
import unittest
import wave
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Song, catalog, cli, library, patches, sfz  # noqa: E402
from agentsound.patches import inst  # noqa: E402
from agentsound.patterns import drums  # noqa: E402,F401
from agentsound.theory import ComposeError  # noqa: E402


def write_wav(path: pathlib.Path, freq: float = 440.0, seconds: float = 0.25, sr: int = 48000, amp: float = 0.5,
              channels: int = 1) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(seconds * sr)
    frames = bytearray()
    for i in range(n):
        v = int(round(amp * 32767 * math.sin(2 * math.pi * freq * i / sr)))
        frames += struct.pack('<h', v) * channels
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(frames))
    return path


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


def engine_or_none():
    try:
        return cli.find_engine()
    except Exception:  # noqa: BLE001 - CliError when the engine is not built
        return None


class Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='agentsound_sfz_')
        self.dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def sfz(self, text: str, name: str = 'inst.sfz', wavs=()) -> pathlib.Path:
        for w in wavs:
            write_wav(self.dir / w)
        p = self.dir / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        return p


class Hammers(Tmp):
    """inst.sfz(..., hammers=): the piano hammer voicing (user feedback 2026-09-30: "es klingt hart")."""

    def test_velocity_to_brightness_curve(self):
        zones = [{'file': 'x.wav', 'vello': lo, 'velhi': hi} for lo, hi in ((1, 26), (73, 80), (81, 88), (121, 127))]
        zones.append({'file': 'y.wav'})                                   # not velocity-layered: untouched
        zones.append({'file': 'z.wav', 'vello': 121, 'eq': [[500, 1, -2], [900, 1, 1]]})   # no room: kept
        out = sfz.hammers(zones, 0.6)
        soft, mid, above, top, flat, full = out
        self.assertTrue(all(b[2] > 0 for b in soft['eq']))               # the soft layers a little clearer
        self.assertTrue(all(0 <= b[2] < 0.2 for b in mid['eq']))         # ~0 around velocity 80
        self.assertTrue(all(b[2] < 0 for b in above['eq']))
        self.assertEqual([b[0] for b in top['eq']], [3000.0, 7500.0])
        self.assertAlmostEqual(top['eq'][0][2], -7.0 * 0.6, places=3)   # the top layer: the full cut
        self.assertLess(top['eq'][1][2], top['eq'][0][2])               # the glassy top cut most
        self.assertAlmostEqual(top['gain'], sfz.HAMMER_GAIN * 0.6, places=3)   # its loudness kept
        self.assertNotIn('gain', soft)
        self.assertNotIn('eq', flat)
        self.assertEqual(full['eq'], [[500, 1, -2], [900, 1, 1]])
        self.assertNotIn('eq', zones[0])                                  # a copy
        self.assertEqual(sfz.hammers(zones, 0), zones)
        with self.assertRaises(ComposeError):
            sfz.hammers(zones, 1.5)

    def test_inst_sfz_applies_it(self):
        p = self.sfz('<group> lovel=1 hivel=64\n<region> sample=a.wav key=60\n'
                     '<group> lovel=65 hivel=127\n<region> sample=a.wav key=60\n', wavs=['a.wav'])
        plain = inst.sfz(str(p))
        voiced = inst.sfz(str(p), hammers=0.5)
        self.assertFalse(any('eq' in z for z in plain.params['samples']))
        lo, hi = voiced.params['samples']
        self.assertGreater(lo['eq'][0][2], 0)
        self.assertLess(hi['eq'][0][2], 0)
        self.assertEqual(voiced.info['sfz']['hammers'], 0.5)
        self.assertNotIn('hammers', voiced.params)                       # an import setting, not a sampler param
        with self.assertRaises(ComposeError):
            inst.sfz(str(p), hammers=True)


class Parser(Tmp):
    def test_headers_inheritance_defines_includes_comments(self):
        self.sfz('<region> key=62 sample=d.wav volume=-3\n', 'parts/more.sfz', wavs=['smp/d.wav'])
        p = self.sfz('''// a comment
/* a block
   comment <region> sample=nope.wav */
#define $KEY 60
#define $VOL -6
<control> default_path=smp/ note_offset=0
<global> volume=$VOL   // trailing comment
<group> lovel=1 hivel=64 tune=10
<region> sample=a b.wav key=$KEY
<region> sample=sub\\c.wav lokey=c#4 hikey=d4 pitch_keycenter=c#4 volume=0
<group> lovel=65 hivel=127
<region> sample=a b.wav key=$KEY
#include "parts/more.sfz"
//****** stars are a comment, not a block
''', wavs=['smp/a b.wav', 'smp/sub/c.wav'])
        zones, info = sfz.load(p)
        self.assertEqual(info['regions'], 4)
        self.assertEqual(len(zones), 4)
        a1, c, a2, d = zones
        self.assertEqual((a1['lo'], a1['hi'], a1['root']), (60, 60, 60))
        self.assertEqual((a1.get('vello', 0), a1['velhi']), (0, 64))    # lovel=1: from the lowest velocity
        self.assertAlmostEqual(a1['gain'], -6.0, places=3)          # global volume
        self.assertAlmostEqual(a1['tune'], 10.0)
        self.assertTrue(a1['file'].endswith('smp/a b.wav'))
        self.assertEqual((c['lo'], c['hi'], c['root']), (61, 62, 61))   # note names: c4 = 60
        self.assertAlmostEqual(c.get('gain', 0.0), 0.0, places=3)     # region overrides global
        self.assertTrue(c['file'].replace('\\', '/').endswith('smp/sub/c.wav'))
        self.assertEqual(a2['vello'], 65)
        self.assertEqual(d['lo'], 62)                                 # from the #include
        self.assertTrue(os.path.isabs(a1['file']))

    def test_note_offset_and_octave_offset(self):
        p = self.sfz('<control> note_offset=12\n<region> sample=a.wav key=48\n', wavs=['a.wav'])
        zones, _ = sfz.load(p)
        self.assertEqual((zones[0]['lo'], zones[0]['hi']), (60, 60))

    def test_case_insensitive_files_and_flac_fallback(self):
        p = self.sfz('<region> sample=SMP/Piano.FLAC key=60\n<region> sample=smp\\other.wav key=61\n',
                     wavs=['smp/piano.wav', 'smp/Other.wav'])
        zones, _ = sfz.load(p)
        self.assertTrue(zones[0]['file'].endswith('piano.wav'))
        self.assertTrue(zones[1]['file'].endswith('Other.wav'))

    def test_missing_samples_are_an_error(self):
        p = self.sfz('<region> sample=a.wav key=60\n<region> sample=gone.wav key=61\n', wavs=['a.wav'])
        with self.assertRaisesRegex(ComposeError, r'1 sample file\(s\) missing.*gone\.wav'):
            sfz.load(p)

    def test_missing_file_and_fragments(self):
        with self.assertRaisesRegex(ComposeError, 'not found'):
            sfz.load(self.dir / 'nope.sfz')
        p = self.sfz('#define $X 1\n<control> set_cc1=10\n', 'frag.sfz')
        with self.assertRaisesRegex(ComposeError, 'no <region>'):
            sfz.load(p)

    def test_unsupported_counted_and_strict(self):
        p = self.sfz('<region> sample=a.wav key=60 fancy_opcode=3\n<effect> type=reverb\n', wavs=['a.wav'])
        zones, info = sfz.load(p)
        self.assertEqual(len(zones), 1)
        self.assertIn('fancy_opcode', info['unsupported'])
        self.assertIn('<effect> section', info['unsupported'])
        with self.assertRaisesRegex(ComposeError, 'strict'):
            sfz.load(p, strict=True)

    def test_curve_section(self):
        p = self.sfz('<curve> curve_index=9 v000=0 v127=1\n'
                     '<region> sample=a.wav key=60 amplitude_oncc20=100 amplitude_curvecc20=9\n', wavs=['a.wav'])
        z1, _ = sfz.load(p, cc={20: 127})
        z2, _ = sfz.load(p, cc={20: 64})
        self.assertAlmostEqual(z1[0].get('gain', 0.0), 0.0, places=2)
        self.assertAlmostEqual(z2[0]['gain'], 20 * math.log10(64 / 127), delta=0.2)


class Mapping(Tmp):
    def test_engine_fields(self):
        p = self.sfz('''<group> seq_length=2 group=3 off_by=4 off_mode=normal ampeg_attack=0.01 ampeg_decay=0.5
ampeg_sustain=50 ampeg_release=0.8 amp_veltrack=50 loop_mode=loop_continuous loop_start=10 loop_end=7000
<region> sample=a.wav key=60 seq_position=1 offset=100 end=8000 pitch_keytrack=50 pan=-50 transpose=1
<region> sample=a.wav key=60 seq_position=2 lorand=0 hirand=0.5
<region> sample=a.wav key=60 trigger=release rt_decay=6 loop_mode=one_shot
''', wavs=['a.wav'])
        a, b, r = sfz.load(p)[0]
        self.assertEqual((a['seqLength'], a['seqPosition'], b['seqPosition']), (2, 1, 2))
        self.assertEqual((a['group'], a['offBy']), (3, 4))
        self.assertEqual((a['offset'], a['end']), (100, 8001))   # SFZ end is inclusive, the engine's exclusive
        self.assertEqual(a['pitchKeytrack'], 50)
        self.assertAlmostEqual(a['pan'], -0.5)
        self.assertAlmostEqual(a['tune'], 100.0)                  # transpose=1: a semitone up
        self.assertEqual((a['loop'], a['loopStart'], a['loopEnd']), ('forward', 10, 7001))
        self.assertAlmostEqual(a['attack'], 0.01)
        self.assertAlmostEqual(a['sustain'], 0.5)
        self.assertAlmostEqual(a['ampVeltrack'], 0.5)
        self.assertEqual((b.get('lorand', 0), b['hirand']), (0, 0.5))
        self.assertEqual(r['trigger'], 'release')
        self.assertAlmostEqual(r['rtDecay'], 6)
        self.assertEqual(r['loop'], 'oneshot')

    def test_review_fixes(self):
        p = self.sfz('<group> group=7 polyphony=5\n<region> sample=a.wav key=42\n'
                     '<region> sample=a.wav key=43 loop_mode=continuous tune_oncc128=200\n'
                     '<region> sample=a.wav key=44 hivel=0\n', wavs=['a.wav'])
        zones, info = sfz.load(p)
        self.assertEqual(len(zones), 2)                                    # hivel=0: never plays (velocities 1..127)
        self.assertEqual([z['groupPolyphony'] for z in zones], [5, 5])     # SFZ polyphony -> the group's voice limit
        self.assertNotIn('polyphony', ' '.join(info['unsupported']))
        self.assertEqual(zones[1]['loop'], 'forward')                      # non-standard loop_mode=continuous
        self.assertTrue(any('continuous' in k for k in info['approximated']))
        self.assertNotIn('tune', zones[1])                                 # pitch bend (cc 128) rests at the centre
        z2, _ = sfz.load(p, cc={128: 127})
        self.assertAlmostEqual(z2[1]['tune'], 200.0, places=3)

    def test_samples_folder_fallback(self):
        pack = self.dir / 'lib' / 'kpack'
        (pack / 'Programs').mkdir(parents=True)
        (pack / 'SOURCE.json').write_text('{"id": "kpack"}', encoding='utf-8')
        write_wav(pack / 'Samples' / 'electric' / 'a2.wav')
        (pack / 'Programs' / 'main.sfz').write_text('<control> default_path=$sample_dir/\n'
                                                    '<region> sample=electric\\a2.wav key=45\n', encoding='utf-8')
        (pack / 'Programs' / 'broken.sfz').write_text('<region> sample=nowhere\\a2.wav key=45\n', encoding='utf-8')
        with mock.patch.object(library, 'SAMPLES', self.dir / 'lib'):
            zones, info = sfz.load('samples/kpack/Programs/main.sfz')
            self.assertTrue(zones[0]['file'].endswith('Samples/electric/a2.wav'), zones[0]['file'])
            self.assertTrue(any('Samples/' in k for k in info['approximated']))
            with self.assertRaisesRegex(ComposeError, 'missing'):
                sfz.load('samples/kpack/Programs/broken.sfz')

    def test_cc_conditions_and_crossfades(self):
        p = self.sfz('''<control> set_cc30=100
<region> sample=a.wav key=60 locc30=64 hicc30=127
<region> sample=b.wav key=60 locc30=0 hicc30=63
<region> sample=c.wav key=61 xfin_locc1=0 xfin_hicc1=127
<region> sample=c.wav key=62 on_locc64=127 on_hicc64=127
''', wavs=['a.wav', 'b.wav', 'c.wav'])
        zones, info = sfz.load(p)
        files = [os.path.basename(z['file']) for z in zones]
        self.assertIn('a.wav', files)
        self.assertNotIn('b.wav', files)                          # set_cc30 = 100 picks the upper layer
        self.assertEqual(info['cc'][30], 100.0)
        zones, _ = sfz.load(p, cc={30: 10, 1: 127})
        files = [os.path.basename(z['file']) for z in zones]
        self.assertIn('b.wav', files)
        self.assertNotIn('a.wav', files)
        xf = [z for z in zones if z['lo'] == 61]
        self.assertEqual(len(xf), 1)
        self.assertAlmostEqual(xf[0].get('gain', 0.0), 0.0, places=2)
        self.assertFalse([z for z in zones if z['lo'] == 62])     # CC-triggered (pedal noise): skipped
        zones, info = sfz.load(p, cc={1: 0}, dyn_cc=None)         # static: crossfade fully out, silent zone dropped
        self.assertFalse([z for z in zones if z['lo'] == 61])
        self.assertTrue(info['skipped'])
        zones, info = sfz.load(p, cc={1: 0})                      # live (CC1 = dynamics): kept, crossfaded by 'dynamics'
        xf = [z for z in zones if z['lo'] == 61]
        self.assertEqual((xf[0]['xfinLoDyn'], xf[0]['xfinHiDyn']), (0, 127))
        self.assertEqual(info['params'], {'dynamics': 0.0, 'dyntone': 0.0})
        self.assertEqual(info['dynamics']['cc'], 1)

    def test_keyswitch_articulations(self):
        p = self.sfz('''<global> sw_lokey=24 sw_hikey=26 sw_default=24
<group> sw_last=24 sw_label=Sustain
<region> sample=a.wav lokey=48 hikey=72
<group> sw_last=25 sw_label=Staccato
<region> sample=b.wav lokey=48 hikey=72
<group> sw_last=26 sw_label=Pizzicato
<region> sample=c.wav lokey=48 hikey=72
''', wavs=['a.wav', 'b.wav', 'c.wav'])
        arts = sfz.articulations(p)
        self.assertEqual([a['label'] for a in arts], ['Sustain', 'Staccato', 'Pizzicato'])
        self.assertEqual([a['key'] for a in arts], [24, 25, 26])
        zones, info = sfz.load(p, keyswitches='static')
        self.assertEqual([os.path.basename(z['file']) for z in zones], ['a.wav'])   # sw_default
        zones, info = sfz.load(p)                                  # live: every articulation, switched by keyswitches
        self.assertEqual([(os.path.basename(z['file']), z['swLast'], z['swDefault']) for z in zones],
                         [('a.wav', 24, 24), ('b.wav', 25, 24), ('c.wav', 26, 24)])
        self.assertEqual((zones[0]['swLo'], zones[0]['swHi']), (24, 26))
        self.assertEqual(info['keyswitches'], {'Sustain': 24, 'Staccato': 25, 'Pizzicato': 26})
        zones, info = sfz.load(p, articulation='stacc')
        self.assertEqual([os.path.basename(z['file']) for z in zones], ['b.wav'])
        self.assertEqual(info['articulation'], 'Staccato')
        zones, _ = sfz.load(p, articulation=26)
        self.assertEqual([os.path.basename(z['file']) for z in zones], ['c.wav'])
        with self.assertRaises(ComposeError):
            sfz.load(p, articulation='legato')

    def test_mics(self):
        p = self.sfz('''<region> sample=close/k.wav key=36
<region> sample=room/k.wav key=36
<region> sample=close/s.wav key=38
<region> sample=room/s.wav key=38
''', wavs=['close/k.wav', 'room/k.wav', 'close/s.wav', 'room/s.wav'])
        self.assertEqual(sfz.mics(p), {'close': 2, 'room': 2})
        zones, _ = sfz.load(p, mics={'room': None})
        self.assertEqual(len(zones), 2)
        self.assertTrue(all('close' in z['file'] for z in zones))
        zones, _ = sfz.load(p, mics={'room': -6})
        room = [z for z in zones if 'room' in z['file']]
        self.assertAlmostEqual(room[0]['gain'], -6.0, places=3)
        with self.assertRaisesRegex(ComposeError, 'unknown microphone'):
            sfz.load(p, mics={'overhead': 0})


class ComposeLayer(Tmp):
    def piano(self, keys=range(48, 73)):
        text = ''.join(f'<region> sample=k{k}.wav key={k} lovel={lo} hivel={hi}\n'
                       for k in keys for lo, hi in ((1, 64), (65, 127)))
        return self.sfz(text, wavs=[f'k{k}.wav' for k in keys])

    def test_inst_sfz_and_pruning(self):
        p = self.piano()
        i = inst.sfz(str(p), level=-3, pedal=0)
        self.assertEqual(i.type, 'sampler')
        self.assertEqual(len(i.params['samples']), 50)
        self.assertEqual(i.params['level'], -3)
        self.assertEqual(i.params['polyphony'], 128)
        s = Song('t', tempo=120)
        sec = s.section('a', bars=1)
        t = s.track('p', i)
        t.note(60, 0, 1, vel=100)
        t.note(64, 1, 1, vel=40)
        s.master.add(patches.fx.limiter())
        r = s.compile()
        zones = r['tracks'][0]['instrument']['params']['samples']
        self.assertEqual(sorted((z['lo'], z['vello'] if 'vello' in z else 1) for z in zones), [(60, 65), (64, 1)])
        self.assertTrue(any('2 of 50 zones' in w for w in s.warnings), s.warnings)
        del sec

    def test_velcurve_evens_velocity_layers(self):
        # a pack whose layers each ramp to full level at their top: the file's curve replaced by one smooth response
        text = ''.join(f'<region> sample=k{k}.wav key={k} lovel={lo} hivel={hi} amp_velcurve_{hi}=1\n'
                       for k in (60, 62) for lo, hi in ((1, 64), (65, 127)))
        text += '<region> sample=perc.wav key=72 amp_veltrack=50\n'           # answers every velocity: untouched
        p = self.sfz(text, wavs=['k60.wav', 'k62.wav', 'perc.wav'])
        pts = sfz.even_velcurve([(1, 64, -12.0), (65, 127, -6.0)], power=2.0)
        self.assertEqual([v for v, _ in pts], sorted({v for v, _ in pts}))    # strictly increasing
        gain = dict((v, g) for v, g in pts)
        # level = curve (dB) + layer level: the response is (v/127)^2 across the layer step
        for v, lay in ((64, -12.0), (65, -6.0), (127, -6.0)):
            self.assertAlmostEqual(20 * math.log10(gain[v]) + lay + 6.0, 40 * math.log10(v / 127), places=3)
        i = inst.sfz(str(p), velcurve=pts)
        zs = i.params['samples']
        layered = [z for z in zs if 'vello' in z or 'velhi' in z]
        self.assertEqual(len(layered), 4)
        for z in layered:
            lo, hi = z.get('vello', 0), z.get('velhi', 127)
            vs = [v for v, _ in z['velcurve']]
            self.assertLessEqual(vs[0], max(lo, 1))                          # the points bracket the zone
            self.assertGreaterEqual(vs[-1], hi)
            self.assertNotIn('ampVeltrack', z)
        perc = next(z for z in zs if 'vello' not in z and 'velhi' not in z)
        self.assertNotIn('velcurve', perc)
        self.assertEqual(perc['ampVeltrack'], 0.5)
        lazy = inst.sfz(str(p), velcurve=pts, lazy=True)
        self.assertEqual(lazy.expand().params['samples'], zs)
        for bad in ([(10, 0.5), (5, 0.6)], [(10, 5.0)], [(10.5, 0.5)], [], 'x', [(10,)]):
            with self.assertRaises(ComposeError, msg=bad):
                inst.sfz(str(p), velcurve=bad)
        with self.assertRaises(ComposeError):
            sfz.even_velcurve([(1, 127, 0.0)], power=9)

    def test_lazy_reads_at_compile(self):
        i = inst.sfz(str(self.dir / 'later.sfz'), lazy=True)       # nothing read yet
        self.assertIn('later.sfz', repr(i))
        with self.assertRaisesRegex(ComposeError, 'not found'):
            i.to_dict()
        p = self.piano(range(60, 62))
        i = inst.sfz(str(p), lazy=True, level=2)
        d = i.to_dict()
        self.assertEqual(len(d['params']['samples']), 4)
        self.assertEqual(d['params']['level'], 2)

    def test_unsupported_warning_once_at_compile(self):
        p = self.sfz('<region> sample=a.wav key=60 fancy_opcode=3\n', wavs=['a.wav'])
        s = Song('t', tempo=120)
        s.section('a', bars=1)
        t = s.track('x', inst.sfz(str(p)))
        t.note(60, 0, 1)
        s.master.add(patches.fx.limiter())
        s.compile()
        hits = [w for w in s.warnings if 'fancy_opcode' in w]
        self.assertEqual(len(hits), 1)
        with self.assertRaises(ComposeError):
            inst.sfz(str(p), strict=True)

    def test_samples_path_resolution(self):
        pack = self.dir / 'lib' / 'mypack'
        (pack / 'SOURCE.json').parent.mkdir(parents=True)
        (pack / 'SOURCE.json').write_text('{"id": "mypack"}', encoding='utf-8')
        write_wav(pack / 'a.wav')
        (pack / 'x.sfz').write_text('<region> sample=a.wav key=60\n', encoding='utf-8')
        with mock.patch.object(library, 'SAMPLES', self.dir / 'lib'):
            zones, info = sfz.load('samples/mypack/x.sfz')
            self.assertEqual(len(zones), 1)
            with self.assertRaisesRegex(ComposeError, "pack 'otherpack' is not installed"):
                sfz.load('samples/otherpack/x.sfz')
            with self.assertRaisesRegex(ComposeError, r'\.sfz files in mypack: x\.sfz'):
                sfz.load('samples/mypack/y.sfz')

    def test_cli_sfz(self):
        p = self.sfz('<global> sw_lokey=24 sw_hikey=25 sw_default=24\n<group> sw_last=24 sw_label=Long\n'
                     '<region> sample=a.wav lokey=48 hikey=72 lovel=1 hivel=80\n'
                     '<region> sample=b.wav lokey=48 hikey=72 lovel=81 hivel=127\n'
                     '<group> sw_last=25 sw_label=Short\n<region> sample=b.wav lokey=48 hikey=72\n',
                     wavs=['a.wav', 'b.wav'])
        code, out, _ = run_cli(['sfz', str(p)])
        self.assertEqual(code, 0)
        self.assertIn('velocity layers 2', out)
        self.assertIn('Long', out)
        code, out, _ = run_cli(['sfz', str(p), '--json'])
        d = json.loads(out)
        self.assertEqual(d['keys'], [48, 72])
        self.assertEqual(d['velocityLayers'], 2)
        self.assertEqual([a['label'] for a in d['articulations']], ['Long', 'Short'])
        code, out, _ = run_cli(['sfz', str(p), '--json', '--articulation', 'Short'])
        self.assertEqual(json.loads(out)['zones'], 1)
        self.assertEqual(json.loads(out)['velocityLayers'], 1)   # the summary is of the chosen articulation
        self.assertEqual(json.loads(out)['articulation'], 'Short')
        code, _, err = run_cli(['sfz', str(p), '--articulation', 'Staccatissimo'])
        self.assertNotEqual(code, 0)
        self.assertIn('matches none', err)
        code, _, err = run_cli(['sfz', str(self.dir / 'none.sfz')])
        self.assertNotEqual(code, 0)
        self.assertIn('not found', err)

    def test_catalog_sfz_index(self):
        pack = self.dir / 'lib' / 'mypack'
        pack.mkdir(parents=True)
        (pack / 'SOURCE.json').write_text('{"id": "mypack"}', encoding='utf-8')
        write_wav(pack / 'samples' / 'a.wav')
        (pack / 'Piano.sfz').write_text('<region> sample=samples/a.wav lokey=21 hikey=108 pitch_keycenter=69\n'
                                        '#include "map.sfz"\n', encoding='utf-8')
        (pack / 'map.sfz').write_text('<region> sample=samples/a.wav key=20\n', encoding='utf-8')
        (pack / 'Broken.sfz').write_text('<region> sample=samples/missing.wav key=20\n', encoding='utf-8')
        idx = catalog.index_pack(pack)
        self.assertEqual(idx['sfzFragments'], ['map.sfz'])
        self.assertEqual(idx['sfzPrograms']['Piano.sfz']['keys'], [20, 108])
        self.assertIn('missing', idx['sfzPrograms']['Broken.sfz']['error'])
        line = catalog.sfz_usage('mypack', 'Piano.sfz', idx['sfzPrograms']['Piano.sfz'])
        self.assertTrue(line.startswith("inst.sfz('samples/mypack/Piano.sfz')"), line)
        self.assertIn('cannot import', catalog.sfz_usage('mypack', 'Broken.sfz', idx['sfzPrograms']['Broken.sfz']))


class SampledPatches(unittest.TestCase):
    def test_registered_lazy_and_helpful_when_missing(self):
        names = patches.list('sampled/')
        for want in ('grand_piano', 'upright_piano', 'upright_bass', 'brush_kit', 'jazz_kit', 'tenor_sax', 'strings',
                     'violins', 'cellos', 'flute', 'french_horns', 'timpani'):
            self.assertIn(f'sampled/{want}', names)
        for n in names:
            p = patches.get(n)
            # a sampler, or a stack of samplers (key-split / layered sampled instruments, e.g. sampled/hero_piano)
            ins = [x.instrument for x in p.instrument.params['layers']] if p.instrument.type == 'stack' \
                else [p.instrument]
            for i in ins:
                self.assertEqual(i.type, 'sampler', n)
                self.assertTrue(i.lazy, n)                        # nothing read at import
            self.assertIn('Measured -18.0 LUFS', p.notes, n)
        # both lookup roots empty: the library folder and <repo>/assets (in the main checkout the library IS
        # assets/samples, so mocking only library.SAMPLES would still find installed packs)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(library, 'SAMPLES', pathlib.Path(tmp)),                 mock.patch.object(sfz, 'ASSETS', pathlib.Path(tmp)):
            p = patches.get('sampled/grand_piano')
            with self.assertRaisesRegex(ComposeError, 'samples fetch salamander-grand'):
                p.instrument.to_dict()
            s = Song('t', tempo=100)
            s.section('a', bars=1)
            t = s.track('violin', 'sampled/violins')
            t.note(69, 0, 1)
            with self.assertRaisesRegex(ComposeError, 'vpo-scripts-standard'):
                s.compile()

    def test_upright_bass_follows_velocity(self):
        # the Meatbass layers evened: curve + measured layer level rises with every velocity step (the file alone
        # played velocity 96 ~3 dB louder than 103)
        from agentsound.patches.sampled import MEATBASS_LAYERS
        pts = patches.get('sampled/upright_bass').instrument.lazy['velcurve']

        def level(v):
            g = next(g0 + (g1 - g0) * (v - v0) / (v1 - v0) for (v0, g0), (v1, g1) in zip(pts, pts[1:]) if v0 <= v <= v1)
            return 20 * math.log10(g) + next(db for lo, hi, db in MEATBASS_LAYERS if lo <= v <= hi)
        levels = [level(v) for v in range(20, 128)]
        self.assertTrue(all(b > a for a, b in zip(levels, levels[1:])))
        self.assertGreater(level(103) - level(57), 9.0)

    def test_patches_cli_lists_without_reading(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(library, 'SAMPLES', pathlib.Path(tmp)):
            code, out, _ = run_cli(['patches', 'sampled/'])
        self.assertEqual(code, 0)
        self.assertIn('sampled/grand_piano', out)


@unittest.skipIf(engine_or_none() is None, 'engine not built')
class SyntheticRender(Tmp):
    def test_pitch_check_finds_a_wrong_root(self):
        write_wav(self.dir / 'a440.wav', 440.0, seconds=1.0)
        good = self.sfz('<region> sample=a440.wav lokey=60 hikey=80 pitch_keycenter=69\n', 'good.sfz')
        bad = self.sfz('<region> sample=a440.wav lokey=60 hikey=80 pitch_keycenter=57\n', 'bad.sfz')
        rows = sfz.pitch_check(good, keys=[69, 76])
        self.assertTrue(all(r['ok'] for r in rows), rows)
        rows = sfz.pitch_check(bad, keys=[69])
        self.assertFalse(rows[0]['ok'], rows)
        self.assertAlmostEqual(rows[0]['cents'], 1200.0, delta=30)


def _pack(pack_id: str) -> pathlib.Path | None:
    d = library.SAMPLES / pack_id
    return d if (d / 'SOURCE.json').is_file() else None


class InstalledPacks(unittest.TestCase):
    """Real libraries: every one imports, its pitches are right. Skipped when the pack is not installed."""

    CASES = [
        ('salamander-grand', 'SalamanderGrandPianoV3Retuned.sfz', None, 600),
        ('upright-piano-kw', 'UprightPianoKW-20220221.sfz', None, 60),
        ('meatbass', 'Programs/04_pizz.sfz', None, 200),
        ('mtg-solo-sax', 'MTG Solo Saxophones/MTG Tenor Sax.sfz', None, 200),
        ('swirly-drums', 'Programs/Basic_kit.sfz', {4: 127, 14: 0}, 1000),
        ('avl-blonde-bop', 'BLONDE_BOP.sfz', None, 100),
    ]

    def test_imports(self):
        seen = 0
        for pack, rel, cc, min_zones in self.CASES:
            d = _pack(pack)
            if d is None:
                continue
            seen += 1
            with self.subTest(pack=pack):
                zones, info = sfz.load(f'samples/{pack}/{rel}', cc=cc)
                self.assertGreaterEqual(len(zones), min_zones)
        if not seen:
            self.skipTest('no sample packs installed')

    def test_articulations_of_vpo(self):
        if _pack('vpo-scripts-standard') is None or _pack('vpo-wav') is None:
            self.skipTest('VPO packs not installed')
        path = 'samples/vpo-scripts-standard/Strings/1st-violin-SEC-KS-C2.sfz'
        labels = [a['label'] or a['name'] for a in sfz.articulations(path)]
        self.assertTrue(any('taccato' in x for x in labels), labels)
        zones, info = sfz.load(path, articulation='staccato')
        self.assertIn('taccato', info['articulation'])
        self.assertTrue(zones)

    @unittest.skipIf(engine_or_none() is None, 'engine not built')
    def test_pitch(self):
        seen = 0
        for pack, rel, cc in (('salamander-grand', 'SalamanderGrandPianoV3Retuned.sfz', None),
                              ('upright-piano-kw', 'UprightPianoKW-20220221.sfz', None),
                              ('meatbass', 'Programs/04_pizz.sfz', None),
                              ('mtg-solo-sax', 'MTG Solo Saxophones/MTG Tenor Sax.sfz', None)):
            if _pack(pack) is None:
                continue
            seen += 1
            with self.subTest(pack=pack):
                rows = sfz.pitch_check(f'samples/{pack}/{rel}', count=4, cc=cc)
                self.assertTrue(rows)
                bad = [r for r in rows if not r['ok']]
                self.assertFalse(bad, rows)
        if not seen:
            self.skipTest('no pitched sample packs installed')


if __name__ == '__main__':
    unittest.main()
