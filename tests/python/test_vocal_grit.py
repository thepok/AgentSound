"""Vocal grit (hero(track, family='vocal', grit='light' | 'crunch' | 'megaphone'), agentsound.heroes grit_spec /
add_grit / grit_trim, agentsound/patches/hero_vocal.py GRIT): the chain composition (the parallel amp bus under the
untouched clean chain, the megaphone's amp stage in the hero chain), the fader sync of the send and the bus, the
errors, and - with the built engine - that every grit renders (strict params) and lands at the clean level."""

import math
import pathlib
import shutil
import struct
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import os  # noqa: E402

from agentsound import Song, cli, heroes, patches, singer  # noqa: E402
from agentsound.patches import hero_vocal, inst  # noqa: E402
from agentsound.song import dumps  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

SR = 48000


def _vowel_wav(path: pathlib.Path, seconds: float = 3.0):
    """A sung-vowel stand-in: E4 (330 Hz) with a falling harmonic series (k^-1.6, the voicebank's spectrum: most energy at 250 Hz-2.5 kHz) and a first-formant bump, a 5 Hz vibrato, a soft
    attack and release."""
    n = int(seconds * SR)
    amps = [(k, k ** -1.6 * (2.0 if k in (2, 3) else 1.0)) for k in range(1, 30)]
    norm = sum(a for _, a in amps)
    frames = []
    ph = 0.0
    for i in range(n):
        t = i / SR
        f = 330.0 * (1.0 + 0.006 * math.sin(2 * math.pi * 5.0 * t))
        ph += 2 * math.pi * f / SR
        env = min(1.0, t / 0.08, (seconds - t) / 0.2)
        v = sum(a * math.sin(k * ph) for k, a in amps) / norm
        frames.append(struct.pack('<h', int(26000 * env * v)))
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b''.join(frames))


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


def _read(path: pathlib.Path):
    with wave.open(str(path), 'rb') as w:
        ch, sw, n = w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        vals = struct.unpack(f'<{len(raw) // 2}h', raw)
        scale = 32768.0
    else:
        vals = [int.from_bytes(raw[i:i + 3], 'little', signed=True) for i in range(0, len(raw), 3)]
        scale = 8388608.0
    return [sum(vals[i + c] for c in range(ch)) / ch / scale for i in range(0, len(vals), ch)]


def _kweighted_db(x, a: float, b: float) -> float:
    """Mean-square level (dB) of the K-weighted signal between a and b seconds (BS.1770's filter, one block)."""
    def biquad(sig, bb, aa):
        y, x1, x2, y1, y2 = [], 0.0, 0.0, 0.0, 0.0
        for v in sig:
            o = bb[0] * v + bb[1] * x1 + bb[2] * x2 - aa[1] * y1 - aa[2] * y2
            x2, x1, y2, y1 = x1, v, y1, o
            y.append(o)
        return y
    # the BS.1770 coefficients at 48 kHz
    y = biquad(x, (1.53512485958697, -2.69169618940638, 1.19839281085285), (1.0, -1.69065929318241, 0.73248077421585))
    y = biquad(y, (1.0, -2.0, 1.0), (1.0, -1.99004745483398, 0.99007225036621))
    seg = y[int(a * SR):int(b * SR)]
    return 10 * math.log10(sum(v * v for v in seg) / len(seg) + 1e-20)


class GritChain(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_grit_'))
        self.addCleanup(shutil.rmtree, self.dir, True)
        _vowel_wav(self.dir / 'vowel.wav')

    def song(self, grit=None, **kw):
        s = Song('grit', tempo=60, seed=1, tail=0.5)
        s.section('a', bars=2)
        s.export(bit_depth=16)
        t = s.track('vocal', inst.sampler(file=str(self.dir / 'vowel.wav'), root=60, oneshot='on', velsens=0))
        t.note(60, 0.5, 3.0, vel=127)
        heroes.hero(t, family='vocal', space=False, ride=False, throws=False, grit=grit, **kw)
        return s, t

    def test_presets_and_bus_patches(self):
        p = heroes.get_preset('vocal')
        self.assertEqual(list(p.grit), ['light', 'crunch', 'megaphone'])
        for amount in ('light', 'crunch'):
            bp = patches.get(f'bus/vocal_grit_{amount}')
            self.assertIsNone(bp.instrument)
            self.assertEqual([f.type for f in bp.fx], ['eq', 'amp', 'eq'])
            band = bp.fx[0].params
            self.assertEqual((band['hp.freq'], band['lp.freq']), (300, 5000))     # 300 Hz-5 kHz into the amp
            self.assertLess(bp.fx[2].params['lp.freq'], 5000)                      # the speaker roll-off after it
            self.assertLess(p.grit[amount]['blend'], 0)                            # UNDER the clean vocal
        self.assertGreater(hero_vocal.GRIT_AMP['crunch']['gain'], hero_vocal.GRIT_AMP['light']['gain'])
        self.assertGreater(p.grit['crunch']['blend'], p.grit['light']['blend'])
        self.assertEqual(p.grit['megaphone']['mode'], 'insert')

    def test_trim_keeps_the_sum_at_the_clean_level(self):
        self.assertEqual(heroes.grit_trim(-120), 0.0)
        self.assertAlmostEqual(heroes.grit_trim(0.0), -3.01, places=2)              # two equal uncorrelated parts
        self.assertAlmostEqual(heroes.grit_trim(0.0, 1.0), -6.02, places=2)         # ... and coherent ones
        _, light = heroes.grit_spec('vocal', 'light')
        _, crunch = heroes.grit_spec('vocal', 'crunch')
        self.assertLess(light['trim'], 0)
        self.assertLess(crunch['trim'], light['trim'])                             # more grit, more trim
        _, own = heroes.grit_spec('vocal', {'amount': 'crunch', 'blend': -12})
        self.assertEqual(own['trim'], heroes.grit_trim(-12, crunch['rho']))       # a new blend re-derives the trim
        _, fixed = heroes.grit_spec('vocal', {'amount': 'crunch', 'blend': -12, 'trim': 0})
        self.assertEqual(fixed['trim'], 0)
        self.assertEqual(heroes.grit_spec('vocal', None), (None, None))

    def test_parallel_grit_leaves_the_clean_chain_alone(self):
        _, clean = self.song()
        s, t = self.song('crunch')
        self.assertEqual(t.fx, clean.fx)                     # the clean path: the same vocal chain, no amp in it
        self.assertNotIn('amp', [f.type for f in t.fx])
        _, spec = heroes.grit_spec('vocal', 'crunch')
        self.assertAlmostEqual(t.gain_db, clean.gain_db + spec['trim'], places=4)
        bus = s.buses['vocal_grit']
        self.assertEqual([f.type for f in bus.fx], ['eq', 'amp', 'eq'])
        self.assertAlmostEqual(t.sends['vocal_grit'], -t.gain_db, places=4)            # the fader undone into the amp
        self.assertAlmostEqual(bus.gain_db, spec['blend'] + t.gain_db, places=4)       # ... and put back on the bus
        self.assertTrue(any(x.startswith('grit: crunch - parallel amp bus') for x in t.hero.log))
        # the mix moves the fader later: the compile re-syncs, the amp still sees the same level
        t.gain_db = -7.5
        r = s.compile()
        tr = next(x for x in r['tracks'] if x['id'] == 'vocal')
        bj = next(x for x in r['buses'] if x['id'] == 'vocal_grit')
        self.assertAlmostEqual(tr['sends']['vocal_grit'], 7.5, places=4)
        self.assertAlmostEqual(bj['gainDb'], spec['blend'] - 7.5, places=4)
        # the amp's gain can be changed per song
        s2, _ = self.song({'amount': 'light', 'gain': 5})
        self.assertEqual(next(f for f in s2.buses['vocal_grit'].fx if f.type == 'amp').params['gain'], 5)

    def test_megaphone_is_in_the_chain(self):
        s, t = self.song('megaphone')
        names = [f.name for f in t.fx]
        types = [f.type for f in t.fx]
        self.assertNotIn('vocal_grit', s.buses)
        for n in ('horn_in', 'horn_in2', 'amp', 'horn'):
            self.assertIn(n, names)
        self.assertLess(types.index('compressor'), names.index('horn_in'))   # after the compressor ...
        self.assertLess(names.index('horn'), types.index('saturator'))       # ... before the drive (VOCAL_ORDER)
        self.assertLess(names.index('presence'), types.index('deesser'))     # the de-esser after the boosts
        pres = next(f for f in t.fx if f.name == 'presence')
        self.assertEqual(pres.params['high.gain'], 0.0)                      # a horn has no air
        self.assertEqual(names[-1], 'air')
        p = heroes.hero(inst.sampler(file=str(self.dir / 'vowel.wav'), root=60), family='vocal', grit='megaphone')
        self.assertIn('amp', [f.type for f in p.fx])                         # a Patch: the insert works without a song
        # on a track that is no hero: the amp stage before its utilities
        s3 = Song('g3', tempo=60)
        s3.section('a', bars=1)
        d = s3.track('dbl', inst.sampler(file=str(self.dir / 'vowel.wav'), root=60))
        heroes.grit(d, 'megaphone')
        self.assertEqual([f.name for f in d.fx], ['horn_in', 'horn_in2', 'amp', 'horn'])

    def test_errors(self):
        with self.assertRaises(ComposeError):
            self.song('distortion')                                          # no such amount
        with self.assertRaises(ComposeError):
            self.song({'amount': 'light', 'drive': 3})                       # unknown key
        with self.assertRaises(ComposeError):
            self.song({'amount': 'megaphone', 'blend': -6})                  # an insert has no blend
        with self.assertRaises(ComposeError):
            heroes.hero(inst.sampler(file=str(self.dir / 'vowel.wav'), root=60), family='vocal', grit='light')
        s = Song('g', tempo=60)
        s.section('a', bars=1)
        with self.assertRaises(ComposeError):                                # the sax hero has no grit table
            heroes.hero(s.track('x', inst.sampler(file=str(self.dir / 'vowel.wav'), root=60)), family='sax',
                        grit='light')

    def test_check_counts_the_grit_bus_with_the_vocal(self):
        rep = {'nodes': [{'id': 'vocal', 'mixSharePct': {'presence': 30.0}, 'bandsPct': {'presence': 5.0}},
                         {'id': 'vocal_grit', 'bus': True, 'mixSharePct': {'presence': 25.0}},
                         {'id': 'piano', 'mixSharePct': {'presence': 15.0}}],
               'sections': [], 'warnings': []}
        codes = [f['code'] for f in singer.check(rep)]
        self.assertNotIn('vocal_intelligibility', codes)                     # 30 + 25 % >= 40 %
        rep['nodes'].pop(1)
        self.assertIn('vocal_intelligibility', [f['code'] for f in singer.check(rep)])

    def test_renders_level_matched(self):
        """Every grit renders (the engine is strict about params) and lands near the clean hero:
        calibrated on the voicebank (songs/_demo_vocal/grit_ab.py: within 0.15 LU), on this synthetic vowel the
        parallel grits stay within 1.5 LU (measured +0.6 / +1.0) and the megaphone - a 550 Hz-3.8 kHz band, so its
        level follows the source's spectrum - within 3 LU (-2.4)."""
        engine = _engine()
        if engine is None:
            self.skipTest('engine not built')
        levels = {}
        for grit in (None, 'light', 'crunch', 'megaphone'):
            s, _ = self.song(grit)
            r = s.compile()
            d = self.dir / f'r_{grit}'
            d.mkdir()
            rj = d / 'song.render.json'
            rj.write_text(dumps(r), encoding='utf-8')
            cli.run_engine(engine, rj, d, render=r)
            levels[grit] = _kweighted_db(_read(d / 'mix.wav'), 1.0, 3.0)
        for grit in ('light', 'crunch', 'megaphone'):
            with self.subTest(grit=grit):
                self.assertLess(abs(levels[grit] - levels[None]), 3.0 if grit == 'megaphone' else 1.5,
                                f'{grit}: {levels[grit] - levels[None]:+.2f} dB vs clean')


if __name__ == '__main__':
    unittest.main()
