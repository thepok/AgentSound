"""Kit builder, pack converters and sampled patches (agentsound/kits.py, agentsound/organ.py, inst.kit / inst.organ /
inst.multisample, the `kit` CLI, patches/sampled_kits.py + sampled_synths.py).

Synthetic one-shot folders, Hydrogen / DrumGizmo kits and GrandOrgue organs are built in a temp folder and always
run; renders need the engine; tests on the real packs run only when the pack is installed ($AGENTSOUND_SAMPLES or
assets/samples)."""

import contextlib
import io
import json
import math
import os
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Song, cli, kits, library, organ, patches  # noqa: E402
from agentsound.patches import inst  # noqa: E402
from agentsound.patterns import drums  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

SR = 44100


def tone(freq: float, seconds: float = 0.3, amp: float = 0.5, decay: float = 12.0, noise: float = 0.0,
         seed: int = 1, fade: bool = True) -> list[float]:
    """A drum-like hit: a decaying sine (+ noise); fade=False stops it mid-waveform."""
    n = int(seconds * SR)
    x, r = [], seed
    for i in range(n):
        t = i / SR
        r = (r * 1103515245 + 12345) & 0x7fffffff
        v = math.sin(2 * math.pi * freq * t) * (1 - noise) + noise * (r / 0x3fffffff - 1.0)
        env = math.exp(-decay * t) if fade else 1.0
        x.append(amp * v * env)
    if fade:
        for i in range(min(64, n)):
            x[n - 1 - i] *= i / 64
    return x


def write(path: pathlib.Path, chans, sr: int = SR, smpl=None, cue=None) -> pathlib.Path:
    """16-bit WAV; chans: one list (mono) or a list of channel lists. smpl=(unity, loopStart, loopEnd inclusive),
    cue=frame of a cue point."""
    if chans and not isinstance(chans[0], list):
        chans = [chans]
    path.parent.mkdir(parents=True, exist_ok=True)
    nc, n = len(chans), len(chans[0])
    data = bytearray()
    for i in range(n):
        for c in range(nc):
            data += struct.pack('<h', max(-32767, min(32767, int(round(chans[c][i] * 32767)))))
    chunks = bytearray()
    chunks += b'fmt ' + struct.pack('<IHHIIHH', 16, 1, nc, sr, sr * 2 * nc, 2 * nc, 16)
    if cue is not None:
        chunks += b'cue ' + struct.pack('<II', 28, 1) + struct.pack('<II4sIII', 1, cue, b'data', 0, 0, cue)
    if smpl is not None:
        unity, ls, le = smpl
        chunks += b'smpl' + struct.pack('<I', 60) + struct.pack('<9I', 0, 0, 22675, unity, 0, 0, 0, 1, 0)
        chunks += struct.pack('<6I', 0, 0, ls, le, 0, 0)
    chunks += b'data' + struct.pack('<I', len(data)) + bytes(data)
    path.write_bytes(b'RIFF' + struct.pack('<I', 4 + len(chunks)) + b'WAVE' + bytes(chunks))
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


def render(song: Song) -> tuple[list[float], list[float]]:
    """Render a song with the engine: (left, right) of mix.wav."""
    r = song.compile()
    with tempfile.TemporaryDirectory(prefix='agentsound_kit_render_') as tmp:
        rj = pathlib.Path(tmp) / 'r.json'
        rj.write_text(json.dumps(r), encoding='utf-8')
        proc = subprocess.run([str(engine_or_none()), 'render', str(rj), '--out', tmp, '--no-analysis', '--no-png',
                               '--quiet'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        if proc.returncode != 0:
            raise AssertionError(proc.stderr or proc.stdout)
        with wave.open(str(pathlib.Path(tmp) / 'mix.wav'), 'rb') as w:
            nc, sw, n = w.getnchannels(), w.getsampwidth(), w.getnframes()
            raw = w.readframes(n)
    vals = []
    for i in range(0, len(raw), sw):
        b = raw[i:i + sw]
        v = int.from_bytes(b, 'little', signed=True)
        vals.append(v / float(1 << (8 * sw - 1)))
    return vals[0::nc], vals[1::nc]


def peak(x, a, b):
    return max(abs(v) for v in x[a:b])


class Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='agentsound_kits_')
        self.dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


# --------------------------------------------------------------------------------------------- names

class Names(unittest.TestCase):
    CASES = {
        'kick': 'kick', 'Kick 01': 'kick', 'BD_808_Long_01': 'kick', 'bd': 'kick', 'Bass Drum': 'kick',
        'BassDrum1': 'kick', 'CR8KBASS': 'kick', 'DR110KIK': 'kick', 'kickme': 'kick', 'cr': 'crash',
        'snare': 'snare', 'SD_Tight': 'snare', 'sdh': 'snare', 'Snr-03': 'snare', 'KPRSNARE': 'snare',
        '80PD_GatedSnare-05': 'snare', 'Flam': 'snare',
        'rim': 'rim', 'RimShot': 'rim', 'sst': 'rim', 'Side Stick': 'rim', 'SdSt-01': 'rim',
        'Snare Rimshot': 'rim', 'rimshot - snares on - 3': 'rim', 'SnareRim': 'rim', 'Rim Click': 'rim',
        'X-Stick': 'rim', 'Stick': 'perc', 'Sticks 2': 'perc',
        'rack tom - snares off - 2': 'tom', 'floor tom - snares on': 'tom', 'kick - snares on - 1': 'kick',
        'snare - snares off - 4': 'snare',
        'clap': 'clap', 'HANDCLP1': 'clap', 'CP': 'clap', 'hand clap 505': 'clap',
        'chh': 'hat_closed', 'HH_Closed_01': 'hat_closed', 'Closed Hat': 'hat_closed', 'KPRCLHH': 'hat_closed',
        'DR110CHT': 'hat_closed', 'HhC': 'hat_closed', 'hh': 'hat_closed', 'HHCD4': 'hat_closed',
        'ohh': 'hat_open', 'OH_02': 'hat_open', 'Open Hat': 'hat_open', 'HhO': 'hat_open', 'HHOD6': 'hat_open',
        'KPROPHH': 'hat_open', 'Hi-Hat Open': 'hat_open', 'OpHat': 'hat_open',
        'PdHat': 'hat_pedal', 'Hi-Hat Pedal': 'hat_pedal', 'HiHatFoot-0': 'hat_pedal',
        'HfHat': 'hat_half', 'Hi-Hat Semiopen': 'hat_half',
        'tom': 'tom', 'Tom Hi': 'tom', 'toml': 'tom', 'LT3D7': 'tom', 'Floor Tom': 'tom', 'CR8KLOTM': 'tom',
        'crash': 'crash', 'CSHD8': 'crash', 'Cymbal 01': 'crash', 'CR8KCYMB': 'crash',
        'ride': 'ride', 'RIDED6': 'ride', 'Ride Bell': 'ride_bell', 'Cup Cymbal': 'ride_bell',
        'China Cymbal': 'china', 'Splash10-4': 'splash',
        'cowb': 'cowbell', 'CowBell': 'cowbell', 'tamb': 'tambourine', 'Tamborine': 'tambourine',
        'shaker': 'shaker', 'Marcas': 'maracas', 'cabasa': 'cabasa', 'congahh': 'conga', 'hi conga 505': 'conga',
        'Hi Bongo': 'bongo', 'Lo Timbale': 'timbale', 'Hi Agogo': 'agogo', 'Claves': 'claves', 'Clave': 'claves',
        'triangle': 'triangle', 'Perc 03': 'perc', 'Scratch01': 'fx',
    }

    def test_roles(self):
        for name, role in self.CASES.items():
            with self.subTest(name=name):
                self.assertEqual(kits.classify(name)[0], role, name)

    def test_folder_fallback_and_unknown(self):
        self.assertEqual(kits.classify('Bassdrum-01', ('bd',))[0], 'kick')
        self.assertEqual(kits.classify('Linn 2', ('sd', 'LinnDrum'))[0], 'snare')
        role, _, why = kits.classify('sample 3', ('oh', 'RolandTR808'))
        self.assertEqual((role, why), ('hat_open', "folder 'oh'"))
        self.assertIsNone(kits.classify('reallinn')[0])

    def test_pitch_hints(self):
        self.assertLess(kits.classify('Tom Lo')[1], kits.classify('Tom Mid')[1])
        self.assertLess(kits.classify('Tom Mid')[1], kits.classify('Tom Hi')[1])
        self.assertLess(kits.classify('Floor Tom')[1], kits.classify('Tom Lo')[1])
        self.assertLess(kits.classify('tomll')[1], kits.classify('tomhh')[1])

    def test_markers(self):
        self.assertEqual(kits._markers('Snare_v3_rr2')[:2], (3, 2))
        self.assertEqual(kits._markers('Kick Vel12')[:2], (12, None))
        self.assertEqual(kits._markers('HH take4')[:2], (None, 4))
        soft, hard = kits._markers('Snare soft')[0], kits._markers('Snare hard')[0]
        self.assertLess(soft, hard)
        pp, ff = kits._markers('Crash pp')[0], kits._markers('Crash ff')[0]
        self.assertLess(pp, ff)
        self.assertEqual(kits._markers('Kick 01')[:2], (None, None))
        self.assertEqual(kits._markers('k_vl10_rr3')[:2], (10, 3))            # Karoryfer / Big Rusty style
        self.assertEqual(kits._markers('snare_hit_vl2_rr1')[:2], (2, 1))

    def test_note_names(self):
        self.assertEqual(kits.note_of('Pad C3'), 48)
        self.assertEqual(kits.note_of('Str_F#2'), 42)
        self.assertEqual(kits.note_of('Bb1'), 34)
        self.assertEqual(kits.note_of('036-C'), 36)
        self.assertEqual(kits.note_of('pad_60'), 60)
        self.assertIsNone(kits.note_of('ORCH5'))
        self.assertEqual(kits._note_parse('pad_60'), (60, False))
        self.assertEqual(kits._note_parse('Pad C3'), (48, True))


# --------------------------------------------------------------------------------------------- one-shot folders

class OneShots(Tmp):
    def make_kit(self) -> pathlib.Path:
        k = self.dir / 'kit'
        for i, amp in enumerate((0.1, 0.3, 0.9), 1):
            write(k / f'Kick_v{i}.wav', tone(55, amp=amp))
        write(k / 'Snare_rr1.wav', tone(200, noise=0.6, amp=0.5, seed=3))
        write(k / 'Snare_rr2.wav', tone(200, noise=0.6, amp=0.5, seed=4))
        write(k / 'HH closed.wav', tone(8000, 0.08, noise=0.9, amp=0.3))
        write(k / 'HH open.wav', tone(8000, 0.6, noise=0.9, amp=0.3, decay=4))
        write(k / 'Pedal Hat.wav', tone(7000, 0.06, noise=0.9, amp=0.2))
        write(k / 'Tom Hi.wav', tone(220))
        write(k / 'Tom Lo.wav', tone(90))
        write(k / 'Tom Mid.wav', tone(140))
        write(k / 'Clap 01.wav', tone(1200, 0.2, noise=0.8, amp=0.9, seed=5))
        write(k / 'Clap 02.wav', tone(500, 0.35, noise=0.3, amp=0.9, decay=5, seed=6))
        for i, amp in enumerate((0.05, 0.12, 0.3, 0.8), 1):
            write(k / f'Crash-0{i}.wav', tone(3000, 0.8, noise=0.95, amp=amp, decay=3, seed=10 + i))
        write(k / 'cowbell.wav', tone(800, 0.2))
        write(k / 'mystery.wav', tone(333, 0.2))
        write(k / 'Beat 120bpm.wav', tone(100, 1.0))
        return k

    def zones_on(self, zones, key):
        return [z for z in zones if z['lo'] == key]

    def test_mapping(self):
        zones, info = kits.build(str(self.make_kit()))
        by = {k: v for k, v in info['keys'].items()}
        # velocity layers from v1..v3, ordered, contiguous, with the gentler ampVeltrack
        kick = sorted(self.zones_on(zones, 36), key=lambda z: z.get('vello', 0))
        self.assertEqual([os.path.basename(z['file']) for z in kick], ['Kick_v1.wav', 'Kick_v2.wav', 'Kick_v3.wav'])
        self.assertEqual([(z.get('vello', 0), z.get('velhi', 127)) for z in kick], [(0, 42), (43, 84), (85, 127)])
        self.assertTrue(all(z['ampVeltrack'] == 0.45 for z in kick))
        # round robin from rr1 / rr2
        snare = self.zones_on(zones, 38)
        self.assertEqual(sorted((z['seqLength'], z['seqPosition']) for z in snare), [(2, 1), (2, 2)])
        # hats on 42 / 44 / 46 choke each other
        for key, name in ((42, 'HH closed.wav'), (44, 'Pedal Hat.wav'), (46, 'HH open.wav')):
            z = self.zones_on(zones, key)
            self.assertEqual([os.path.basename(x['file']) for x in z], [name])
            self.assertEqual(z[0]['choke'], 1)
        # toms by their names low -> high
        self.assertEqual(os.path.basename(self.zones_on(zones, 41)[0]['file']), 'Tom Lo.wav')
        self.assertEqual(os.path.basename(self.zones_on(zones, 45)[0]['file']), 'Tom Mid.wav')
        self.assertEqual(os.path.basename(self.zones_on(zones, 48)[0]['file']), 'Tom Hi.wav')
        self.assertEqual(by[43]['filledFrom'], 45)                      # retuned fills on the other tom keys
        self.assertLess(self.zones_on(zones, 43)[0]['tune'], 0)
        # two different normalized claps: variants (39 + a spare key), not round robins
        self.assertEqual(os.path.basename(self.zones_on(zones, 39)[0]['file']), 'Clap 01.wav')
        spare = [k for k, v in by.items() if k >= 88 and v['role'] == 'clap']
        self.assertEqual(len(spare), 1)
        # 4 crash hits recorded at rising strength: one crash with velocity layers
        crash = self.zones_on(zones, 49)
        self.assertEqual(len(crash), 4)
        self.assertEqual(len({(z.get('vello'), z.get('velhi')) for z in crash}), 4)
        self.assertEqual(os.path.basename(min(crash, key=lambda z: z.get('vello', 0))['file']), 'Crash-01.wav')
        self.assertEqual(by[56]['role'], 'cowbell')
        self.assertEqual(by[35]['filledFrom'], 36)
        # nothing dropped silently: the unknown file is on a spare key and listed, the loop is skipped and listed
        self.assertIn('mystery.wav', info['unmapped'])
        self.assertTrue(any(v['sound'] == 'mystery.wav' for k, v in by.items() if k >= 88))
        self.assertTrue(any('Beat 120bpm' in s for s in info['skipped']))
        self.assertFalse(any('Beat' in z['file'] for z in zones))
        for z in zones:
            self.assertEqual((z['loop'], z['pitchKeytrack'], z['lo']), ('oneshot', 0, z['hi']))
        self.assertEqual(info['names']['kick'], 36)

    def test_numbered_modes(self):
        k = self.make_kit()
        zones, _ = kits.build(str(k), numbered='variants')
        self.assertEqual(len(self.zones_on(zones, 49)), 1)              # each crash hit its own sound
        zones, _ = kits.build(str(k), numbered='rr')
        clap = self.zones_on(zones, 39)
        self.assertEqual(sorted(z['seqPosition'] for z in clap), [1, 2])
        zones, _ = kits.build(str(k), numbered='random')
        clap = self.zones_on(zones, 39)
        self.assertEqual(sorted((z['lorand'], z['hirand']) for z in clap), [(0.0, 0.5), (0.5, 1.0)])
        with self.assertRaises(ComposeError):
            kits.build(str(k), numbered='maybe')

    def test_naming_conventions(self):
        k = self.dir / 'conv'
        # Karoryfer-style vl / rr markers: one kick, 3 layers x 2 round robins
        for v in (1, 2, 3):
            for r in (1, 2):
                write(k / 'kick' / f'k_vl{v}_rr{r}.wav', tone(55, amp=0.1 * 3 ** (v - 1), seed=v * 10 + r))
        # hit indices in front ('1-Snare' .. '6-Snare', MuldjordKit / DrumGizmo exports): one snare, rising layers
        for i in range(1, 7):
            write(k / 'snare' / f'{i}-Snare.wav', tone(200, noise=0.6, amp=0.02 * 2 ** i, seed=i))
        # machine names in front ('808 Cowbell', '909 Cowbell') stay separate sounds
        write(k / 'cb' / '808 Cowbell.wav', tone(560, 0.2, amp=0.8))
        write(k / 'cb' / '909 Cowbell.wav', tone(800, 0.2, amp=0.8))
        zones, info = kits.build(str(k))
        kick = self.zones_on(zones, 36)
        self.assertEqual(len(kick), 6)
        self.assertEqual(len({(z.get('vello'), z.get('velhi')) for z in kick}), 3)
        self.assertEqual(sorted({z['seqLength'] for z in kick}), [2])
        snare = self.zones_on(zones, 38)
        self.assertEqual(len(snare), 6)
        self.assertIn('1-Snare', min(snare, key=lambda z: z.get('vello', 0))['file'])
        self.assertFalse(any('Snare' in v['sound'] for kk, v in info['keys'].items() if kk != 38))
        cow = [v['sound'] for v in info['keys'].values() if v['role'] == 'cowbell']
        self.assertEqual(sorted(cow), ['808 Cowbell.wav', '909 Cowbell.wav'])

    def test_acoustic_takes_and_rims(self):
        # takes of an acoustic drum at one strength (natural, uneven peaks and lengths): one drum with round robins,
        # not 6 'variants' on spare keys; the snare-wire words do not make toms snares
        k = self.dir / 'jazz'
        for i, amp in enumerate((0.8, 0.7, 0.62, 0.75, 0.66, 0.58), 1):
            write(k / f'kick - snares on - {i}.wav', tone(60, 0.4 + 0.05 * i, amp=amp, decay=8, seed=i))
            write(k / f'rack tom - snares off - {i}.wav', tone(160, 0.5 + 0.04 * i, amp=amp, decay=6, seed=20 + i))
        write(k / 'snare - snares on - 1.wav', tone(200, noise=0.6, amp=0.7, seed=40))
        write(k / 'rimshot - snares on - 1.wav', tone(400, noise=0.5, amp=0.9, seed=41))
        write(k / 'xstick - snares on - 1.wav', tone(900, 0.1, noise=0.3, amp=0.5, seed=42))
        write(k / 'sticks.wav', tone(2000, 0.05, noise=0.2, amp=0.5, seed=43))
        zones, info = kits.build(str(k))
        kick = self.zones_on(zones, 36)
        self.assertEqual(len(kick), 6)
        self.assertEqual({z['seqLength'] for z in kick}, {6})
        self.assertFalse(any(v['role'] == 'kick' for kk, v in info['keys'].items() if kk >= 88))
        toms = {kk for kk, v in info['keys'].items() if v['role'] == 'tom' and 'filledFrom' not in v}
        self.assertEqual(len(toms), 1)
        self.assertIn('xstick', self.zones_on(zones, 37)[0]['file'])     # side stick on GM 37
        self.assertIn('rimshot', self.zones_on(zones, 40)[0]['file'])    # the rimshot on 40
        self.assertIn('snare - snares on', self.zones_on(zones, 38)[0]['file'])
        self.assertEqual(info['keys'][[kk for kk, v in info['keys'].items() if v['sound'] == 'sticks.wav'][0]]['role'],
                         'perc')

    def test_stereo_one_shots_keep_their_placement(self):
        k = self.dir / 'st'
        hat = tone(8000, 0.1, noise=0.9, amp=0.3)
        write(k / 'hh closed.wav', [hat, hat])                                   # dual mono: panned like mono
        write(k / 'ride.wav', [tone(3000, 0.5, noise=0.9, amp=0.3, seed=1), tone(3000, 0.5, noise=0.9, amp=0.3, seed=2)])
        zones, _ = kits.build(str(k), spread=1.0)
        self.assertLess(self.zones_on(zones, 42)[0]['pan'], 0)
        self.assertNotIn('pan', self.zones_on(zones, 51)[0])                   # a real stereo file: as recorded

    def test_strict_options(self):
        k = self.make_kit()
        with self.assertRaisesRegex(ComposeError, "gains= key 'hatz'"):
            kits.build(str(k), gains={'hatz': -3})
        zones, _ = kits.build(str(k), gains={'bd': 3, 'open_hat': -2, 'tambourine': 1})    # aliases, GM names, roles
        self.assertTrue(all(z['gain'] == 3.0 for z in self.zones_on(zones, 36)))
        self.assertTrue(all(z['gain'] == -2.0 for z in self.zones_on(zones, 46)))
        with self.assertRaisesRegex(ComposeError, 'kit= picks one kit file of a DrumGizmo'):
            kits.build(str(k), kit='basic')
        loops = self.dir / 'loops'
        write(loops / 'Beat 120bpm.wav', tone(100, 0.5))
        with self.assertRaisesRegex(ComposeError, '1 files skipped: loops'):
            kits.build(str(loops))

    def test_map_overrides(self):
        k = self.make_kit()
        outside = write(self.dir / 'other' / 'boom.wav', tone(45, 0.5))
        zones, info = kits.build(str(k), map={'snare': 'Clap 02', 'clap': None, 40: str(outside),
                                              'cowbell': {'files': ['mystery'], 'gain': -6, 'tune': 100}})
        self.assertEqual([os.path.basename(z['file']) for z in self.zones_on(zones, 38)], ['Clap 02.wav'])
        self.assertEqual(self.zones_on(zones, 39), [])
        self.assertEqual([os.path.basename(z['file']) for z in self.zones_on(zones, 40)], ['boom.wav'])
        cb = self.zones_on(zones, 56)
        self.assertEqual((os.path.basename(cb[0]['file']), cb[0]['gain'], cb[0]['tune']), ('mystery.wav', -6.0, 100.0))
        # the displaced automatic snares move on (38 is taken): nothing is lost
        self.assertTrue(any('Snare_rr1' in z['file'] for z in zones))
        with self.assertRaisesRegex(ComposeError, "no file matches 'Snaer'"):
            kits.build(str(k), map={'snare': 'Snaer'})
        with self.assertRaisesRegex(ComposeError, 'unknown key'):
            kits.build(str(k), map={'snaredrum': 'Clap 02'})
        with self.assertRaisesRegex(ComposeError, 'dict needs'):
            kits.build(str(k), map={'snare': {'file': 'x'}})

    def test_extras_gains_spread(self):
        k = self.make_kit()
        zones, info = kits.build(str(k), extras=False, gains={'hats': -6, 'kick': 2}, spread=0.0)
        self.assertFalse(any(z['lo'] >= 88 for z in zones))
        self.assertIn('mystery.wav', info['unused'])
        self.assertTrue(all(z['gain'] == -6.0 for z in zones if z['lo'] in (42, 46)))
        self.assertTrue(all(z['gain'] == 2.0 for z in zones if z['lo'] == 36))
        self.assertFalse(any('pan' in z for z in zones))
        zones, _ = kits.build(str(k), spread=1.0)
        self.assertLess(self.zones_on(zones, 42)[0]['pan'], 0)          # drummer's perspective: hats left

    def test_cut_files_fade(self):
        k = self.dir / 'cut'
        write(k / 'kick.wav', tone(60, 0.25, fade=False))
        write(k / 'snare.wav', tone(200, 0.25, noise=0.5, decay=40))
        zones, _ = kits.build(str(k))
        kick = self.zones_on(zones, 36)[0]
        self.assertEqual((kick['sustain'], kick['decay']), (0.0, 0.012))
        self.assertAlmostEqual(kick['hold'], 0.25 - 0.014, delta=0.003)
        self.assertNotIn('hold', self.zones_on(zones, 38)[0])

    def test_file_list_and_errors(self):
        k = self.make_kit()
        zones, info = kits.build([str(k / 'Tom Hi.wav'), str(k / 'mystery.wav')], map={'kick': 'mystery'})
        self.assertEqual({z['lo'] for z in zones if 'mystery' in z['file']}, {35, 36})   # + the kick-2 fill
        with self.assertRaisesRegex(ComposeError, 'not found'):
            kits.build(str(self.dir / 'nope'))
        (self.dir / 'empty').mkdir()
        with self.assertRaisesRegex(ComposeError, 'no .wav files'):
            kits.build(str(self.dir / 'empty'))

    def test_pack_hint(self):
        from agentsound import sfz
        # both lookup roots empty (in the main checkout the library IS assets/samples)
        with mock.patch.object(library, 'SAMPLES', self.dir / 'lib'), mock.patch.object(sfz, 'ASSETS', self.dir / 'lib'):
            with self.assertRaisesRegex(ComposeError, 'samples fetch tidal-drum-machines'):
                kits.build('samples/tidal-drum-machines/machines/RolandTR808')


# --------------------------------------------------------------------------------------------- Hydrogen

H2 = '''<?xml version="1.0" encoding="UTF-8"?>
<drumkit_info xmlns="http://www.hydrogen-music.org/drumkit">
 <name>Test Kit</name><author>me</author><license>CC0</license>
 <instrumentList>
  <instrument><id>0</id><name>Kick</name><volume>1</volume><gain>1</gain><pan_L>1</pan_L><pan_R>1</pan_R>
   <muteGroup>-1</muteGroup><midiOutNote>35</midiOutNote>
   <layer><filename>kick-soft.aiff</filename><min>0</min><max>0.5</max><gain>0.5</gain><pitch>0</pitch></layer>
   <layer><filename>kick-hard.wav</filename><min>0.5</min><max>1</max><gain>1</gain><pitch>-1</pitch></layer>
  </instrument>
  <instrument><id>1</id><name>Hat Closed</name><volume>1</volume><gain>1</gain><pan_L>1</pan_L><pan_R>0.5</pan_R>
   <muteGroup>0</muteGroup>
   <instrumentComponent><drumkitComponent>0</drumkitComponent><gain>1</gain>
    <layer><filename>hat1.wav</filename><min>0</min><max>1</max><gain>1</gain><pitch>0</pitch></layer>
    <layer><filename>hat2.wav</filename><min>0</min><max>1</max><gain>1</gain><pitch>0</pitch></layer>
   </instrumentComponent>
  </instrument>
  <instrument><id>2</id><name>Hat Open</name><muteGroup>0</muteGroup>
   <layer><filename>ohat.wav</filename><min>0</min><max>1</max><gain>1</gain><pitch>0</pitch></layer>
  </instrument>
  <instrument><id>3</id><name>Weird Thing</name>
   <layer><filename>weird.wav</filename><min>0</min><max>1</max></layer>
  </instrument>
 </instrumentList>
</drumkit_info>
'''


class Hydrogen(Tmp):
    def test_drumkit_xml(self):
        k = self.dir / 'h2'
        write(k / 'kick-soft.wav', tone(55, amp=0.2))          # the kit names .aiff: the downloader converted it
        write(k / 'kick-hard.wav', tone(55, amp=0.8))
        for n in ('hat1', 'hat2', 'ohat'):
            write(k / f'{n}.wav', tone(8000, 0.1, noise=0.9))
        write(k / 'weird.wav', tone(700, 0.1))
        (k / 'drumkit.xml').write_text(H2, encoding='utf-8')
        zones, info = kits.build(str(k))
        self.assertEqual(info['kind'], 'hydrogen')
        self.assertEqual(info['name'], 'Test Kit')
        kick = sorted((z for z in zones if z['lo'] == 36), key=lambda z: z.get('vello', 0))
        self.assertEqual([(z.get('vello', 0), z.get('velhi', 127)) for z in kick], [(0, 63), (64, 127)])
        self.assertAlmostEqual(kick[0]['gain'], 20 * math.log10(0.5), places=2)
        self.assertEqual(kick[1]['tune'], -100.0)
        hats = [z for z in zones if z['lo'] == 42]
        self.assertEqual(sorted(z['seqPosition'] for z in hats), [1, 2])     # same range: round robin
        self.assertEqual({z['choke'] for z in zones if z['lo'] in (42, 46)}, {20})
        self.assertLess(hats[0]['pan'], 0)
        self.assertIn('Weird Thing', info['unmapped'])
        self.assertTrue(any(z['lo'] == 39 and 'weird' in z['file'] for z in zones))    # Hydrogen's default: 36 + id
        with self.assertRaisesRegex(ComposeError, 'map= is for one-shot folders'):
            kits.build(str(k), map={'kick': 'x'})
        # the xml itself works too
        z2, _ = kits.build(str(k / 'drumkit.xml'))
        self.assertEqual(len(z2), len(zones))


# --------------------------------------------------------------------------------------------- DrumGizmo

DG_KIT = '''<?xml version='1.0' encoding='UTF-8'?>
<drumkit name="TestDG" version="2.0" samplerate="44100">
 <channels>
  <channel name="AmbL"/><channel name="AmbR"/><channel name="OHL"/><channel name="OHR"/>
  <channel name="Kick"/><channel name="SnareTop"/>
 </channels>
 <instruments>
  <instrument name="KDrum" file="Instr/kdrum.xml">
   <channelmap in="AmbL" out="AmbL"/><channelmap in="AmbR" out="AmbR"/><channelmap in="OHL" out="OHL"/>
   <channelmap in="OHR" out="OHR"/><channelmap in="Kick" out="Kick" main="true"/><channelmap in="Snare" out="SnareTop"/>
  </instrument>
  <instrument name="Snare" file="Instr/snare.xml">
   <channelmap in="AmbL" out="AmbL"/><channelmap in="AmbR" out="AmbR"/><channelmap in="OHL" out="OHL"/>
   <channelmap in="OHR" out="OHR"/><channelmap in="Kick" out="Kick"/><channelmap in="Snare" out="SnareTop" main="true"/>
  </instrument>
  <instrument name="HihatClosed" group="hihat" file="Instr/hhc.xml"/>
  <instrument name="HihatOpen" group="hihat" file="Instr/hho.xml"/>
 </instruments>
</drumkit>
'''
DG_MAP = '''<?xml version='1.0' encoding='UTF-8'?>
<midimap><map note="36" instr="KDrum"/><map note="35" instr="KDrum"/><map note="38" instr="Snare"/>
<map note="42" instr="HihatClosed"/><map note="46" instr="HihatOpen"/></midimap>
'''


def dg_instrument(name: str, samples: list[tuple[str, float, str]]) -> str:
    chans = ['AmbL', 'AmbR', 'OHL', 'OHR', 'Kick', 'Snare']
    out = [f'<?xml version="1.0" encoding="UTF-8"?>\n<instrument version="2.0" name="{name}"><samples>']
    for sname, power, file in samples:
        out.append(f'<sample name="{sname}" power="{power}">')
        for i, ch in enumerate(chans):
            out.append(f'<audiofile channel="{ch}" file="{file}" filechannel="{i + 1}"/>')
        out.append('</sample>')
    out.append('</samples></instrument>')
    return '\n'.join(out)


class DrumGizmo(Tmp):
    def make(self) -> pathlib.Path:
        k = self.dir / 'dg' / 'TestKit'
        specs = {'kdrum': ('KDrum', 55), 'snare': ('Snare', 200), 'hhc': ('HihatClosed', 6000), 'hho': ('HihatOpen', 6000)}
        for short, (name, f0) in specs.items():
            samples = []
            n = 6 if short == 'kdrum' else 3
            for i in range(n):
                amp = 0.05 * (1.8 ** i)
                chans = [tone(f0 + 20 * c, 0.2, amp=min(0.9, amp) * (0.3 if c < 4 else 1.0), seed=i * 7 + c)
                         for c in range(6)]
                rel = f'../Samples/{short}/{i + 1}-{short}.wav'
                write(k / 'Samples' / short / f'{i + 1}-{short}.wav', chans)
                samples.append((f'{name}-{i + 1}', amp * amp, rel))
            (k / 'Instr').mkdir(parents=True, exist_ok=True)
            (k / 'Instr' / f'{short}.xml').write_text(dg_instrument(name, samples), encoding='utf-8')
        (k / 'TestKit_full.xml').write_text(DG_KIT, encoding='utf-8')
        (k / 'Midimap_full.xml').write_text(DG_MAP, encoding='utf-8')
        return self.dir / 'dg'

    def test_kit(self):
        zones, info = kits.build(str(self.make()))
        self.assertEqual(info['kind'], 'drumgizmo')
        self.assertEqual(info['channels'], ['AmbL', 'AmbR', 'OHL', 'OHR', 'Kick', 'SnareTop'])
        self.assertEqual(info['midimap'], 'Midimap_full.xml')
        kick = [z for z in zones if z['lo'] == 36]
        self.assertTrue(kick and all(len(z['channels']) == 6 for z in kick))
        amb_l = kick[0]['channels'][0]
        self.assertEqual(amb_l[0], 0)
        self.assertAlmostEqual(amb_l[1], 1.0, places=4)            # the room pair hard left / right
        self.assertAlmostEqual(amb_l[2], 0.0, places=4)
        close = kick[0]['channels'][4]
        self.assertAlmostEqual(close[1], close[2], places=4)       # the kick mic in the centre
        layers = {(z.get('vello', 0), z.get('velhi', 127)) for z in kick}
        self.assertGreaterEqual(len(layers), 3)                    # power -> velocity layers
        self.assertEqual(sorted({z['lo'] for z in zones if 'kdrum' in z['file']}), [35, 36])   # the midimap's 2 notes
        self.assertEqual(len({z['choke'] for z in zones if z['lo'] in (42, 46)}), 1)            # group 'hihat'
        self.assertTrue(all('choke' not in z for z in kick))
        # soft hits sit on low velocities
        soft = min(kick, key=lambda z: z.get('vello', 0))
        self.assertIn('1-kdrum', soft['file'])
        # microphones: mute the room, lower the overheads
        zones2, info2 = kits.build(str(self.make()), mics={'room': None, 'overheads': -6.0206})
        k2 = [z for z in zones2 if z['lo'] == 36][0]
        self.assertEqual([c[0] for c in k2['channels']], [2, 3, 4, 5])
        self.assertAlmostEqual(k2['channels'][0][1], 0.5, places=3)
        self.assertIsNone(info2['mix']['AmbL'])
        with self.assertRaisesRegex(ComposeError, 'unknown microphone'):
            kits.build(str(self.make()), mics={'bogus': 0})
        with self.assertRaisesRegex(ComposeError, 'mics= is for DrumGizmo'):
            write(self.dir / 'plain' / 'kick.wav', tone(60))
            kits.build(str(self.dir / 'plain'), mics={'room': -3})

    @unittest.skipIf(engine_or_none() is None, 'engine not built')
    def test_render_mix(self):
        root = self.make()
        s = Song('dg', tempo=120)
        s.section('a', bars=1)
        s.master.add(patches.fx.limiter())
        t = s.track('k', inst.kit(str(root), mics={'room': None, 'overheads': None, 'SnareTop': None}))
        t.note(36, 0, 0.5, vel=127)
        left, right = render(s)
        self.assertGreater(peak(left, 0, 4000), 0.01)
        self.assertAlmostEqual(peak(left, 0, 4000), peak(right, 0, 4000), delta=0.01)   # only the centred kick mic


# --------------------------------------------------------------------------------------------- multisamples

class Multisample(Tmp):
    def test_notes_layers_and_root(self):
        d = self.dir / 'pad'
        for n, f in (('C3', 130.8), ('E3', 164.8), ('G#3', 207.7)):
            write(d / f'Pad {n}.wav', tone(f, 0.3, decay=0))
        write(d / 'Pad C4 v1.wav', tone(261.6, 0.3, amp=0.2, decay=0))
        write(d / 'Pad C4 v2.wav', tone(261.6, 0.3, amp=0.8, decay=0))
        zones, info = kits.multisample(str(d))
        self.assertEqual(info['roots'], [48, 52, 56, 60])
        c3 = next(z for z in zones if z['root'] == 48)
        self.assertEqual((c3['lo'], c3['hi']), (0, 50))
        top = [z for z in zones if z['root'] == 60]
        self.assertEqual(sorted((z['vello'], z['velhi']) for z in top), [(0, 63), (64, 127)])
        self.assertEqual(top[0]['hi'], 127)
        zones, info = kits.multisample(str(d), octave=1, keys=(24, 96))
        self.assertEqual(info['roots'][0], 60)
        self.assertEqual(min(z['lo'] for z in zones), 24)
        one = write(self.dir / 'ORCH5.wav', tone(220, 0.5, decay=0))
        z, _ = kits.multisample(str(one), root='A3', loop='pingpong', loop_start=100, loop_end=9000)
        self.assertEqual((z[0]['root'], z[0]['loop'], z[0]['loopStart'], z[0]['loopEnd']), (57, 'pingpong', 100, 9000))
        with self.assertRaisesRegex(ComposeError, 'root= gives'):
            kits.multisample(str(one))
        with self.assertRaises(ComposeError):
            kits.multisample(str(one), root='A3', loop='none', loop_start=5)


# --------------------------------------------------------------------------------------------- organ

ODF = '''[Organ]
ChurchName=Test Church
NumberOfManuals=1
HasPedals=Y
NumberOfTremulants=1
NumberOfRanks=1

[Tremulant001]
Name=Tremulant
Period=200
AmpModDepth=20

[Manual000]
Name=Pedal
FirstAccessibleKeyMIDINoteNumber=36
FirstAccessibleKeyLogicalKeyNumber=1
NumberOfAccessibleKeys=3
NumberOfStops=1
Stop001=001

[Manual001]
Name=Huvudverk
FirstAccessibleKeyMIDINoteNumber=36
FirstAccessibleKeyLogicalKeyNumber=1
NumberOfAccessibleKeys=3
NumberOfStops=2
Stop001=002
Stop002=003

[Stop001]
Name=Principal 8'
NumberOfAccessiblePipes=3
FirstAccessiblePipeLogicalPipeNumber=1
FirstAccessiblePipeLogicalKeyNumber=1
NumberOfLogicalPipes=3
AmplitudeLevel=50
Pipe001=ped\\036.wav
Pipe001ReleaseCount=2
Pipe001Release001=ped\\rel1.wav
Pipe001Release001MaxKeyPressTime=250
Pipe001Release002=ped\\rel2.wav
Pipe001Release002MaxKeyPressTime=500
Pipe002=ped\\037.wav
Pipe002LoadRelease=N
Pipe002ReleaseCount=2
Pipe002Release001=ped\\rel1.wav
Pipe002Release001MaxKeyPressTime=250
Pipe002Release002=ped\\rel2.wav
Pipe002Release002MaxKeyPressTime=500
Pipe003=ped\\038.wav

[Stop002]
Name=Principal 8'
NumberOfAccessiblePipes=3
FirstAccessiblePipeLogicalPipeNumber=1
FirstAccessiblePipeLogicalKeyNumber=1
NumberOfLogicalPipes=3
AmplitudeLevel=100
Pipe001=hv\\036.wav
Pipe002=hv\\037.wav
Pipe002AmplitudeLevel=200
Pipe003=DUMMY

[Stop003]
Name=Rörflöjt 4'
NumberOfRanks=1
Rank001=001
Rank001FirstPipeNumber=1
Rank001PipeCount=2
Rank001FirstAccessibleKeyNumber=2
PitchTuning=-10

[Rank001]
Name=Rorflojt 4
NumberOfLogicalPipes=2
Pipe001=REF:001:001:001
Pipe002=hv\\rf.wav
'''


class Organ(Tmp):
    def make(self) -> pathlib.Path:
        o = self.dir / 'organ'
        for rel, f in (('ped/036.wav', 65.4), ('ped/037.wav', 69.3), ('ped/038.wav', 73.4), ('hv/036.wav', 65.4),
                       ('hv/037.wav', 69.3), ('hv/rf.wav', 293.7)):
            x = tone(f, 1.0, decay=0)
            tail = tone(f, 0.5, decay=6)
            write(o / rel, [x + tail, x + tail], smpl=(60, 11025, 33074), cue=len(x))
        for rel in ('ped/rel1.wav', 'ped/rel2.wav'):
            write(o / rel, [tone(65.4, 0.5, decay=6), tone(65.4, 0.5, decay=6)])
        (o / 'Test.organ').write_bytes(ODF.encode('latin-1'))
        return o

    def test_one_release_per_note_off(self):
        # 'MultipleReleases' definitions: several release samples per pipe chosen by the key-press time; the sampler
        # would play them all at once, so one is kept: the pipe file's own release, else the longest one
        o = self.make()
        z, _ = organ.load(str(o), ['Principal 8'], manual='pedal', extend='none')
        rel36 = [x for x in z if x['lo'] == 36 and x.get('trigger') == 'release']
        self.assertEqual(len(rel36), 1)
        self.assertIn('offset', rel36[0])                                    # the in-file release (cue)
        rel37 = [x for x in z if x['lo'] == 37 and x.get('trigger') == 'release']
        self.assertEqual([os.path.basename(x['file']) for x in rel37], ['rel2.wav'])
        sus37 = [x for x in z if x['lo'] == 37 and x.get('trigger') != 'release'][0]
        self.assertEqual((sus37['loop'], sus37['release']), ('sustain', 0.07))   # fades under the release sample
        self.assertEqual(organ._pick_release([('a', 250), ('b', -1), ('c', 500)], False), ['b'])
        self.assertEqual(organ._pick_release([('a', 250), ('c', 500)], True), [])

    def test_stops_and_zones(self):
        o = self.make()
        rows = organ.stops(str(o))
        self.assertEqual([(r['manual'], r['stop']) for r in rows],
                         [('Pedal', "Principal 8'"), ('Huvudverk', "Principal 8'"), ('Huvudverk', "Rörflöjt 4'")])
        zones, info = organ.load(str(o), ['principal 8'], extend='none')     # a non-pedal manual wins
        self.assertEqual(info['stops'], ["Huvudverk: Principal 8'"])
        attack = [z for z in zones if z.get('trigger') != 'release']
        rel = [z for z in zones if z.get('trigger') == 'release']
        self.assertEqual(sorted(z['lo'] for z in attack), [36, 37])          # DUMMY pipe skipped
        a = attack[0]
        self.assertEqual((a['loop'], a['end'], a['root'], a['lo'], a['hi']), ('forward', 44100, a['lo'], a['lo'], a['lo']))
        self.assertEqual(rel[0]['offset'], 44100)
        self.assertEqual(rel[0]['trigger'], 'release')
        loud = next(z for z in attack if z['lo'] == 37)
        self.assertAlmostEqual(loud['gain'], 6.0206, places=3)                # PipeAmplitudeLevel 200 %
        # pedal by manual= and by 'manual: stop'; stop level 50 %
        z1, _ = organ.load(str(o), ['Principal 8'], manual='pedal', extend='none')
        z2, _ = organ.load(str(o), ['ped: Principal 8'], extend='none')
        self.assertEqual(z1, z2)
        self.assertAlmostEqual(z1[0]['gain'], -6.0206, places=3)
        # ranks, REF pipes, accents and foot marks ignored, stop tuning
        z3, info3 = organ.load(str(o), ['Rorflojt 4'], extend='none')
        att = sorted((z for z in z3 if z.get('trigger') != 'release'), key=lambda z: z['lo'])
        self.assertEqual([z['lo'] for z in att], [37, 38])
        self.assertTrue(att[0]['file'].replace('\\', '/').endswith('hv/036.wav'))    # REF:001:001:001 = manual 1, stop 1
        self.assertEqual(att[0]['tune'], -10.0)
        # extend: keys outside the compass play the nearest octave's pipe (at its own pitch, or stretched)
        z4, _ = organ.load(str(o), ['Principal 8'], manual='pedal')
        low = [z for z in z4 if z['lo'] == 24 and z.get('trigger') != 'release']
        self.assertEqual((low[0]['root'], os.path.basename(low[0]['file'])), (24, '036.wav'))
        z5, _ = organ.load(str(o), ['Principal 8'], manual='pedal', extend='stretch')
        self.assertEqual([z['root'] for z in z5 if z['lo'] == 24 and z.get('trigger') != 'release'], [36])
        # stereo flip, tremulant
        z6, info6 = organ.load(str(o), ['Principal 8'], stereo='flip', tremulant=True, extend='none')
        self.assertEqual(z6[0]['channels'], [[0, 1, 0], [1, 0, -1]])
        self.assertEqual(z6[0]['tremolo'][1], 5.0)                           # Period 200 ms
        self.assertGreater(z6[0]['vibrato'][0], 0)
        self.assertNotIn('tremolo', [k for z in z6 if z.get('trigger') == 'release' for k in z])

    def test_errors(self):
        o = self.make()
        with self.assertRaisesRegex(ComposeError, "no stop 'Trumpet'"):
            organ.load(str(o), ['Trumpet'])
        with self.assertRaisesRegex(ComposeError, 'no manual'):
            organ.load(str(o), ['Principal 8'], manual='Swell')
        with self.assertRaisesRegex(ComposeError, 'choose stops'):
            organ.load(str(o))
        with self.assertRaisesRegex(ComposeError, 'no GrandOrgue definition'):
            organ.load(str(self.dir), ['x'])
        with self.assertRaisesRegex(ComposeError, 'stereo='):
            organ.load(str(o), ['Principal 8'], stereo='wide')
        with self.assertRaisesRegex(ComposeError, 'not one of the chosen stops'):
            organ.load(str(o), ['Principal 8'], stereo={'Rorflojt 4': 'left'})
        with self.assertRaisesRegex(ComposeError, 'stereo= per stop'):
            organ.load(str(o), ['Principal 8'], stereo={'Principal 8': 'mono'})

    def test_stereo_modes(self):
        o = self.make()
        z, info = organ.load(str(o), ['Principal 8', 'Rorflojt 4'], stereo={'Rorflojt 4': 'left'}, extend='none')
        self.assertEqual(info['stereo'], {"Huvudverk: Principal 8'": 'asis', "Huvudverk: Rörflöjt 4'": 'left'})
        hv = [x for x in z if x['file'].replace('\\', '/').endswith('hv/037.wav') and x['lo'] == 37]
        self.assertTrue(any('channels' not in x for x in hv))                  # Principal 8 as recorded
        self.assertTrue(any(x.get('channels') == [[0, 1, 1]] for x in z))       # the flute: one microphone, mono
        z2, _ = organ.load(str(o), ['Principal 8'], stereo='right', extend='none')
        self.assertTrue(all(x['channels'] == [[1, 1, 1]] for x in z2))

    def test_wavpack_metadata(self):
        riff = (b'RIFF\x00\x00\x00\x00WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 2, 44100, 176400, 4, 16)
                + b'cue ' + struct.pack('<II', 28, 1) + struct.pack('<II4sIII', 1, 900, b'data', 0, 0, 900)
                + b'smpl' + struct.pack('<I', 60) + struct.pack('<9I', 0, 0, 22675, 60, 0, 0, 0, 1, 0)
                + struct.pack('<6I', 0, 0, 100, 799, 0, 0) + b'data' + struct.pack('<I', 4000))
        sub = bytes([0x21, len(riff) // 2]) + riff
        flags = 0x800 | 0x1000 | (9 << 23) | 1
        head = b'wvpk' + struct.pack('<IHBBIIIII', 24 + len(sub), 0x410, 0, 0, 1000, 0, 1000, flags, 0)
        p = self.dir / 'pipe.wav'
        p.write_bytes(head + sub)
        info = organ.sample_info(str(p))
        self.assertEqual((info['frames'], info['rate'], info['channels'], info['loop'], info['cue']),
                         (1000, 44100, 2, (100, 800), 900))

    @unittest.skipIf(engine_or_none() is None, 'engine not built')
    def test_render_release(self):
        o = self.make()
        s = Song('org', tempo=60)
        s.section('a', bars=2)
        s.master.add(patches.fx.limiter())
        t = s.track('o', inst.organ(str(o), stops=['Principal 8'], extend='none'))
        t.note(36, 0, 2.0, vel=100)
        left, _ = render(s)
        sr = 48000
        self.assertGreater(peak(left, int(1.0 * sr), int(1.9 * sr)), 0.05)      # the loop sustains past the file's cue
        self.assertGreater(peak(left, int(2.1 * sr), int(2.3 * sr)), 0.02)      # the release sample after the key-up
        self.assertLess(peak(left, int(3.2 * sr), int(3.9 * sr)), 0.01)


# --------------------------------------------------------------------------------------------- constructors, CLI

class Constructors(Tmp):
    def test_inst_kit_lazy_and_compile(self):
        k = self.dir / 'kit'
        write(k / 'kick.wav', tone(55))
        write(k / 'snare.wav', tone(200, noise=0.5))
        write(k / 'hat.wav', tone(8000, 0.05, noise=0.9))
        i = inst.kit(str(k), level=-3)
        self.assertEqual(i.type, 'sampler')
        self.assertEqual(i.params['level'], -3)
        self.assertEqual(i.params['polyphony'], 96)
        self.assertEqual(i.info['kit']['names']['snare'], 38)
        lazy = inst.kit(str(self.dir / 'later'), lazy=True)
        self.assertIn("kit=", repr(lazy))
        with self.assertRaisesRegex(ComposeError, 'not found'):
            lazy.to_dict()
        with self.assertRaisesRegex(ComposeError, "can't be replaced"):
            inst.kit(str(k), lazy=True).but(samples=[])
        s = Song('t', tempo=120)
        s.section('a', bars=1)
        s.master.add(patches.fx.limiter())
        t = s.track('d', inst.kit(str(k), lazy=True))
        t.play(drums({'kick': 'x...', 'hat': 'x.x.'}), 0)
        r = s.compile()
        keys = {z['lo'] for z in r['tracks'][0]['instrument']['params']['samples']}
        self.assertEqual(keys, {36, 42})                                        # pruned to the played keys
        with self.assertRaisesRegex(ComposeError, "'samples' can't be given"):
            inst.kit(str(k), samples=[])
        with self.assertRaisesRegex(ComposeError, 'source must be'):
            inst.kit('')

    def test_inst_multisample_and_organ(self):
        write(self.dir / 'ms' / 'Lead A3.wav', tone(220, 0.3, decay=0))
        m = inst.multisample(str(self.dir / 'ms'), release=0.2)
        self.assertEqual((m.params['samples'][0]['root'], m.params['release']), (57, 0.2))
        self.assertTrue(inst.organ(str(self.dir / 'none'), stops=['x'], lazy=True).lazy)

    def test_cli(self):
        k = self.dir / 'kit'
        write(k / 'Kick_v1.wav', tone(55, amp=0.2))
        write(k / 'Kick_v2.wav', tone(55, amp=0.8))
        write(k / 'what.wav', tone(55))
        code, out, _ = run_cli(['kit', str(k)])
        self.assertEqual(code, 0)
        self.assertIn('2 velocity layers', out)
        self.assertIn('not recognized', out)
        code, out, _ = run_cli(['kit', str(k), '--json', '--map', 'snare=what'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['keys']['38']['sound'], 'what.wav')
        code, _, err = run_cli(['kit', str(k), '--map', 'snare'])
        self.assertNotEqual(code, 0)
        write(self.dir / 'ms' / 'Pad C3.wav', tone(130.8))
        code, out, _ = run_cli(['kit', str(self.dir / 'ms'), '--multisample'])
        self.assertEqual(code, 0)
        self.assertIn('roots C3', out)
        o = Organ.make(self)
        code, out, _ = run_cli(['kit', str(o)])
        self.assertEqual(code, 0)
        self.assertIn("manual 1 Huvudverk", out)


@unittest.skipIf(engine_or_none() is None, 'engine not built')
class Renders(Tmp):
    def test_round_robin_and_velocity_layers_alternate(self):
        k = self.dir / 'kit'
        write(k / 'Snare_rr1.wav', tone(200, 0.2, amp=0.3))
        write(k / 'Snare_rr2.wav', tone(200, 0.2, amp=0.6))
        write(k / 'Kick_v1.wav', tone(60, 0.2, amp=0.2))
        write(k / 'Kick_v2.wav', tone(60, 0.2, amp=0.8))
        s = Song('rr', tempo=60)
        s.section('a', bars=2)
        s.master.add(patches.fx.limiter(ceiling=0))
        t = s.track('d', inst.kit(str(k), humanize=False, velsens=0))
        for i in range(4):
            t.note(38, i, 0.5, vel=100)
        t.note(36, 4, 0.5, vel=20)
        t.note(36, 5, 0.5, vel=120)
        left, right = render(s)
        sr = 48000
        hits = [peak(left, int(i * sr), int(i * sr + 0.15 * sr)) for i in range(6)]
        # snare hits alternate between the two takes, the kick layers follow the velocity
        self.assertGreater(hits[1], hits[0] * 1.5)
        self.assertLess(hits[2], hits[1] / 1.5)
        self.assertGreater(hits[3], hits[2] * 1.5)
        self.assertGreater(hits[5], hits[4] * 2.5)


# --------------------------------------------------------------------------------------------- real packs

def _pack(pack_id: str) -> pathlib.Path | None:
    d = library.SAMPLES / pack_id
    return d if (d / 'SOURCE.json').is_file() else None


class InstalledPacks(unittest.TestCase):
    def test_machine_and_hydrogen_kits(self):
        seen = 0
        for pack, want in (('hyperreal-linndrum', {36, 38, 42, 46, 49}), ('hyperreal-tr707', {36, 38, 39, 42, 46}),
                           ('hydrogen-forzee-stereo', {36, 38, 42, 44, 46, 49, 51}),
                           ('hydrogen-bja-pacific', {36, 38, 42, 46})):
            if _pack(pack) is None:
                continue
            seen += 1
            with self.subTest(pack=pack):
                zones, info = kits.build(f'samples/{pack}')
                self.assertLessEqual(want, set(info['keys']))
        if not seen:
            self.skipTest('no drum packs installed')

    def test_acoustic_one_shot_packs(self):
        """Real acoustic one-shot folders: hit indices in front (MuldjordKit) and natural takes (Orange Tree) become
        velocity layers / round robins of one drum, not dozens of spare keys."""
        seen = 0
        if _pack('muldjordkit') is not None:
            seen += 1
            zones, info = kits.build('samples/muldjordkit/samples')
            self.assertGreaterEqual(info['keys'][38]['layers'], 5)
            self.assertGreaterEqual(info['keys'][38]['rr'], 3)
            self.assertLess(len(info['keys']), 90)
        if _pack('orangetree-jazz-funk-kit') is not None:
            seen += 1
            zones, info = kits.build('samples/orangetree-jazz-funk-kit')
            self.assertGreaterEqual(info['keys'][36]['rr'], 6)
            self.assertIn('xstick', info['keys'][37]['sound'])
            self.assertIn('rimshot', info['keys'][40]['sound'])
            self.assertLess(len(info['keys']), 60)
        if not seen:
            self.skipTest('no acoustic one-shot packs installed')

    def test_organ(self):
        if _pack('lars-palo-burea-church') is None:
            self.skipTest('lars-palo-burea-church not installed')
        zones, info = organ.load('samples/lars-palo-burea-church', ['Principal 8', 'Oktava 4'], extend='none')
        self.assertEqual(info['stops'], ["Huvudverk: Principal 8'", 'Huvudverk: Oktava 4\''])
        self.assertGreaterEqual(len([z for z in zones if z.get('trigger') == 'release']), 100)   # 2 x 56 pipes, most with a release cue
        a = next(z for z in zones if z['lo'] == 60 and 'Principal8' in z['file'])
        self.assertEqual((a['loop'], a['end']), ('forward', 257783))

    def test_library_patches_expand(self):
        names = patches.list('sampled/')
        for want in ('linndrum', 'tr808', 'tr909', 'tr707', 'dmx', 'studio_kit', 'forzee_kit', 'fairlight_orch5',
                     'fairlight_choir', 'church_organ', 'organ_pedal'):
            self.assertIn(f'sampled/{want}', names)
        for n in names:
            p = patches.get(n)
            spec = p.instrument.lazy
            if not spec or spec.get('kind', 'sfz') == 'sfz':
                continue
            src = spec['source'] if isinstance(spec['source'], str) else spec['source'][0]
            pack = src.split('/')[1]
            if _pack(pack) is None:
                continue
            with self.subTest(patch=n):
                d = p.instrument.to_dict()
                self.assertTrue(d['params']['samples'])


if __name__ == '__main__':
    unittest.main()
