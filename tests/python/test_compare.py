import copy
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import cli, compare

HZ = [25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150,
      4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000]


def report(lufs=-10.0, spectrum=None, width=40.0, crest=12.0, low_corr=1.0, hits=(20.0, 10.0, 15.0), decay=None, seconds=60.0,
           tp=-1.0, p10=-3.0):
    db = spectrum or [-20.0 - 0.1 * i for i in range(30)]
    octs = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    return {
        'global': {'truePeakDbtp': tp, 'shortTermMax': lufs + 2, 'plr': tp - lufs, 'spectralTiltDbPerOct': -4.5},
        'render': {'fromSec': 0.0, 'toSec': seconds},
        'measures': {
            'seconds': seconds,
            'spectrum': {'hz': HZ, 'db': [d + lufs for d in db]},
            'stereo': {'octaveHz': octs, 'widthPct': [0, 0, 5, width, width, width, width, width, 20, 10],
                       'correlation': [1, 1, 0.95, 0.4, 0.4, 0.4, 0.4, 0.4, 0.8, 0.9],
                       'above150Hz': {'widthPct': width, 'correlation': 0.4}, 'whole': {'widthPct': width / 2, 'correlation': 0.6},
                       'below120Hz': {'widthPct': 0.0, 'correlation': low_corr}},
            'loudness': {'integratedLufs': lufs, 'loudnessRange': 5.0, 'psrDb': crest - 2, 'shortTermLu': {'p10': p10, 'p95': 1.5},
                         'histogram': {'fromLu': -30, 'stepLu': 1, 'pct': [0] * 40}},
            'transients': {'crestDb': crest, 'lowCrestDb': 12, 'low': {'hitDb': hits[0], 'perSec': 2},
                           'mid': {'hitDb': hits[1], 'perSec': 5}, 'high': {'hitDb': hits[2], 'perSec': 6}},
            'decay': decay or {'robust': False, 'decays': 0},
            'sustain': {'robust': False},
            'tempo': {'bpm': 120, 'confidence': 0.5},
        },
    }


SONG_REPORT = {'nodes': [{'id': 'pad', 'mixSharePct': {'lowmid': 60, 'mid': 30, 'bass': 10}},
                         {'id': 'bass', 'mixSharePct': {'bass': 70, 'sub': 80, 'lowmid': 20}},
                         {'id': 'bus', 'bus': True, 'mixSharePct': {'lowmid': 90}}],
               'reference': {'lufsTarget': [-12, -9]},
               'space': {'opportunities': [{'id': 'pad', 'role': 'bed', 'widthPct': 3, 'widener': 'chorus'}]}}
RENDER = {'master': {'fx': [{'type': 'limiter', 'params': {'gain': 4}}]}}


class Pure(unittest.TestCase):
    def test_identical_is_quiet(self):
        c = compare.compare_reports(report(), report())
        self.assertEqual(c['suggestions'], [])
        self.assertTrue(all(d == 0 for d in c['spectrum']['diffDb'] if d is not None))
        self.assertEqual(c['loudnessMatch']['offsetDb'], 0.0)

    def test_loudness_matched_spectrum(self):
        # Same shape, 6 dB louder overall: after loudness matching there is no tonal difference.
        c = compare.compare_reports(report(lufs=-8.0), report(lufs=-14.0), song_report={'reference': {'lufsTarget': [-12, -6]}})
        self.assertTrue(all(abs(d) < 1e-9 for d in c['spectrum']['diffDb'] if d is not None))
        self.assertFalse(any(s['area'] == 'tone' for s in c['suggestions']))

    def test_low_mid_bump_becomes_a_cut_on_the_carrier(self):
        spec = [-20.0 - 0.1 * i for i in range(30)]
        for i in (11, 12, 13, 14):       # 315-630 Hz
            spec[i] += 4.0
        c = compare.compare_reports(report(spectrum=spec), report(), song_report=SONG_REPORT)
        tone = [s for s in c['suggestions'] if s['area'] == 'tone']
        self.assertEqual(len(tone), 1)
        s = tone[0]
        self.assertEqual(s['fix']['type'], 'eq')
        gain = [v for k, v in s['fix']['params'].items() if k.endswith('.gain')][0]
        self.assertLess(gain, -2.0)
        freq = [v for k, v in s['fix']['params'].items() if k.endswith('.freq')][0]
        self.assertTrue(250 <= freq <= 700, freq)
        self.assertIn("'pad'", s['text'])
        self.assertNotIn("'bus'", s['text'])
        self.assertEqual(c['spectrum']['regions'][0]['band'], 'lowmid')

    def test_shelves_at_the_ends(self):
        spec = [-20.0 - 0.1 * i for i in range(30)]
        for i in range(0, 5):
            spec[i] -= 5.0            # less sub
        for i in range(25, 29):
            spec[i] += 4.0            # more air
        c = compare.compare_reports(report(spectrum=spec), report())
        kinds = sorted(r['eq']['kind'] for r in c['spectrum']['regions'])
        self.assertEqual(kinds, ['high shelf', 'low shelf'])
        low = next(r for r in c['spectrum']['regions'] if r['eq']['kind'] == 'low shelf')
        self.assertGreater(low['eq']['params']['low.gain'], 0)

    def test_band_limited_reference_not_judged(self):
        ref = [-20.0 - 0.1 * i for i in range(30)]
        for i in range(28, 30):
            ref[i] -= 40.0            # 16 kHz low-pass (mp3)
        c = compare.compare_reports(report(), report(spectrum=ref))
        self.assertEqual(c['reference']['bandLimitedAboveHz'], 16000)
        self.assertFalse(c['spectrum']['valid'][28])
        self.assertFalse(any(s['area'] == 'tone' for s in c['suggestions']))
        self.assertTrue(any('nothing above' in n for n in c['notes']))

    def test_width_density_punch_lowend(self):
        c = compare.compare_reports(report(width=20.0, crest=15.0, low_corr=0.6, hits=(20, 10, 9)),
                                    report(width=55.0, crest=10.0, hits=(20, 10, 16)), song_report=SONG_REPORT, render=RENDER)
        areas = [s['area'] for s in c['suggestions']]
        self.assertIn('stereo', areas)
        widen = next(s for s in c['suggestions'] if s['area'] == 'stereo' and 'wider' in s['text'])
        self.assertGreater(widen['fix']['params']['width'], 1.2)
        self.assertIn("'pad'", widen['text'])
        self.assertTrue(any('monobass' in s['text'] for s in c['suggestions']))
        dens = next(s for s in c['suggestions'] if s['area'] == 'dynamics')
        self.assertEqual(dens['fix']['type'], 'compressor')
        self.assertTrue(any(s['area'] == 'punch' and 'hats' in s['text'] for s in c['suggestions']))
        scores = [s['score'] for s in c['suggestions']]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual([s['priority'] for s in c['suggestions']], list(range(1, len(scores) + 1)))

    def test_mono_reference_skips_width(self):
        c = compare.compare_reports(report(width=40.0), report(width=0.5))
        self.assertFalse(any(s['area'] == 'stereo' and 'wider' in s['text'] for s in c['suggestions']))
        self.assertTrue(any('mono' in n for n in c['notes']))

    def test_loudness_advice_respects_the_target(self):
        # Reference much quieter (old master): keep the mix inside its target.
        c = compare.compare_reports(report(lufs=-10.0), report(lufs=-20.0), song_report=SONG_REPORT, render=RENDER)
        s = next(s for s in c['suggestions'] if s['area'] == 'loudness')
        self.assertIn('keep it', s['text'])
        # Reference louder than the target: only up to the top of the target.
        c = compare.compare_reports(report(lufs=-13.0), report(lufs=-7.0), song_report=SONG_REPORT, render=RENDER)
        s = next(s for s in c['suggestions'] if s['area'] == 'loudness')
        self.assertEqual(s['fix']['params']['gain'], 8.0)   # 4 dB now + 4 dB (-13 -> -9)
        # Plain match inside the window.
        c = compare.compare_reports(report(lufs=-12.0), report(lufs=-10.0), song_report=SONG_REPORT, render=RENDER)
        s = next(s for s in c['suggestions'] if s['area'] == 'loudness')
        self.assertEqual(s['fix']['params']['gain'], 6.0)

    def test_loudness_advice_edge_cases(self):
        # Mix below its target, the reference even quieter: raise to the bottom of the target, never "inside".
        c = compare.compare_reports(report(lufs=-16.0), report(lufs=-20.0), song_report=SONG_REPORT, render=RENDER)
        s = next(s for s in c['suggestions'] if s['area'] == 'loudness')
        self.assertNotIn('keep it', s['text'])
        self.assertIn('Raise', s['text'])
        self.assertEqual(s['fix']['params']['gain'], 8.0)   # 4 dB now + 4 dB (-16 -> -12)
        # Mix already at the top of its target, the reference louder still: keep it, and say the reference is louder.
        c = compare.compare_reports(report(lufs=-9.2), report(lufs=-6.0), song_report=SONG_REPORT, render=RENDER)
        s = next(s for s in c['suggestions'] if s['area'] == 'loudness')
        self.assertIn('keep it', s['text'])
        self.assertIn('louder', s['text'])
        self.assertNotIn('quieter', s['text'])
        # Too loud without a master limiter: the fix is the master gain, not "add a limiter and raise it".
        c = compare.compare_reports(report(lufs=-6.0), report(lufs=-10.0), song_report=SONG_REPORT, render={'master': {'fx': []}})
        s = next(s for s in c['suggestions'] if s['area'] == 'loudness')
        self.assertIn('Lower', s['text'])
        self.assertNotIn('raise its gain', s['text'])
        self.assertEqual(s['fix'], {'target': 'master', 'gainDbChange': -4.0})   # to the reference's -10 (inside the target)

    def test_bells_get_distinct_eq_bands(self):
        # Two low regions (both would ask for peak1) and a mid one: one eq can take all three moves.
        spec = [-20.0 - 0.1 * i for i in range(30)]
        for i in (5, 6, 7):          # 80-125 Hz
            spec[i] += 4.0
        for i in (11, 12, 13):       # 315-500 Hz
            spec[i] -= 4.0
        for i in (17, 18, 19):       # 1.25-2 kHz
            spec[i] += 4.0
        c = compare.compare_reports(report(spectrum=spec), report())
        bells = [r for r in c['spectrum']['regions'] if r['eq']['kind'] == 'bell']
        self.assertEqual(len(bells), 3)
        bands = sorted({k.split('.')[0] for r in bells for k in r['eq']['params']})
        self.assertEqual(bands, ['peak1', 'peak2', 'peak3'])
        # The suggestion text carries the renamed params too.
        tone = ' '.join(s['text'] for s in c['suggestions'] if s['area'] == 'tone')
        for b in ('peak1', 'peak2', 'peak3'):
            self.assertIn(b + '.freq', tone)

    def test_space_only_when_robust(self):
        d_mix = {'robust': True, 'tailT60Sec': 0.4, 't60Sec': 0.3}
        d_ref = {'robust': True, 'tailT60Sec': 1.2, 't60Sec': 0.9}
        c = compare.compare_reports(report(decay=d_mix), report(decay=d_ref))
        self.assertTrue(any(s['area'] == 'space' for s in c['suggestions']))
        c = compare.compare_reports(report(decay=d_mix), report(decay=dict(d_ref, robust=False)))
        self.assertFalse(any(s['area'] == 'space' for s in c['suggestions']))

    def test_errors_and_helpers(self):
        with self.assertRaises(compare.CompareError):
            compare.compare_reports({'global': {}}, report())
        with self.assertRaises(compare.CompareError):
            compare.compare_reports(report(lufs=-90.0), report())
        self.assertEqual(compare.parse_time('1:02.5'), 62.5)
        self.assertEqual(compare.parse_time('90'), 90.0)
        with self.assertRaises(compare.CompareError):
            compare.parse_time('1:xx')
        self.assertEqual(compare.slug('Gerry Rafferty - Baker Street (Official Video)'), 'gerry_rafferty_-_baker_street_official_v')
        lines = compare.summary_lines(compare.compare_reports(report(), report(crest=16)), None, pathlib.Path('c.json'))
        self.assertTrue(any('suggestions' in ln for ln in lines))

    def test_title_full_width_quotes_are_folded(self):
        # YouTube titles carry full-width quotes (Perturbator - "Dangerous Days" with U+FF02): Windows' ANSI argv maps
        # them to a bare '"' and splits --title; NFKC folds them to ASCII, which subprocess escapes.
        from unittest import mock
        seen = {}

        def run(cmd, **kw):
            seen['cmd'] = cmd
            return mock.Mock(returncode=0, stdout='{}', stderr='')
        with mock.patch.object(compare.subprocess, 'run', run):
            compare.run_analyze(pathlib.Path('engine'), pathlib.Path('a.wav'), pathlib.Path('out'),
                                title='Perturbator - ＂Dangerous Days＂ (12:59-17:47)')
        title = seen['cmd'][seen['cmd'].index('--title') + 1]
        self.assertEqual(title, 'Perturbator - "Dangerous Days" (12:59-17:47)')
        self.assertTrue(title.isascii())


class EndToEnd(unittest.TestCase):
    """analyze -> compare -> compare.png with the real engine and ffmpeg (skipped without them)."""

    SONG = '''
from agentsound import *

def build():
    s = Song('Compare Test', tempo=120, key='A minor', seed=2)
    a = s.section('verse', bars=4)
    b = s.section('chorus', bars=4)
    s.track('drums', inst.drums(kit='synthwave')).play(drums({'kick': 'x...x...x...x...', 'hat': '..x...x...x...x.'}), 0, times=8)
    t = s.track('pad', inst.va(unison=3))
    t.play(s.prog('i VI III VII').block(), a)
    t.play(s.prog('i VI III VII').block(), b)
    s.master.add(fx.limiter())
    return s
'''

    def setUp(self):
        try:
            self.engine = cli.find_engine()
        except cli.CliError:
            self.skipTest('engine not built')
        if not cli.find_ffmpeg():
            self.skipTest('ffmpeg not found')
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_compare_'))
        (self.dir / 'song').mkdir()
        (self.dir / 'song' / 'song.py').write_text(self.SONG, encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_compare_a_section_with_an_mp3_reference(self):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['build', str(self.dir / 'song'), '--no-mp3']), 0)
            # The reference: the song's own mix encoded to mp3 elsewhere (so it decodes through ffmpeg).
            ref = self.dir / 'ref.mp3'
            ok, err = __import__('agentsound.delivery', fromlist=['x']).encode_mp3(cli.find_ffmpeg(), self.dir / 'song' / 'out' / 'mix.wav', ref)
            self.assertTrue(ok, err)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.main(['compare', str(self.dir / 'song'), '--ref', str(ref), '--section', 'chorus', '--ref-start', '0:08',
                                 '--ref-end', '0:16', '--no-images'])
        self.assertEqual(code, 0)
        d = self.dir / 'song' / 'out' / 'compare' / 'ref'
        self.assertTrue((d / 'compare.json').is_file())
        self.assertTrue((d / 'compare.png').is_file())
        import json
        c = json.loads((d / 'compare.json').read_text(encoding='utf-8'))
        self.assertLess(abs(c['loudnessMatch']['offsetDb']), 0.6)     # the same audio: loudness matches
        valid = [x for x, v in zip(c['spectrum']['diffDb'], c['spectrum']['valid']) if v]
        self.assertLess(max(abs(x) for x in valid), 1.0)             # and so does the spectrum (mp3 aside)
        self.assertFalse(any(s['area'] == 'tone' for s in c['suggestions']))

    def test_bad_section(self):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            cli.main(['build', str(self.dir / 'song'), '--no-mp3'])
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = cli.main(['compare', str(self.dir / 'song'), '--ref', str(self.dir / 'song' / 'out' / 'mix.wav'), '--section', 'bridge'])
        self.assertEqual(code, 1)
        self.assertIn('chorus', err.getvalue())


if __name__ == '__main__':
    unittest.main()
