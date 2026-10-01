import contextlib
import io
import json
import math
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Song, cli, fx, inst, mastering
from agentsound.theory import ComposeError

HZ = [25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150,
      4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000]


def report(*, lufs=-10.0, tp=-1.1, lra=6.0, plr=None, window=(-12, -9), lra_range=(3, 15), plr_min=6.0, corr=0.5,
           low_corr=0.98, width=30.0, clipped=0, dc=(0.0, 0.0), vs_ref=None, bands=None, profile='default',
           width_targets=(30, 100), width_above=55.0):
    return {
        'global': {'lufsIntegrated': lufs, 'truePeakDbtp': tp, 'loudnessRange': lra,
                   'plr': plr if plr is not None else tp - lufs, 'stereoCorrelation': corr, 'lowEndCorrelation': low_corr,
                   'widthPct': width, 'clippedSamples': clipped, 'dcOffset': list(dc), 'subsonicPct': 0.0,
                   'bandsVsRefDb': bands or {'sub': 0.0, 'bass': 0.0, 'lowmid': 0.0, 'mid': 0.0, 'presence': 0.0,
                                             'brilliance': 0.0, 'air': 0.0},
                   'thirdOctave': {'hz': HZ, 'vsRefDb': vs_ref or [0.0] * len(HZ)}},
        'reference': {'profile': profile, 'lufsTarget': list(window), 'lraRangeLu': list(lra_range), 'plrMinDb': plr_min,
                      'bandLimitsDb': {'sub': {'high': 5.0, 'low': -9.0}, 'bass': {'high': 4.0, 'low': -6.0}}},
        'space': {'widthAbove150HzPct': width_above, 'targets': {'widthAbove150HzPct': list(width_targets)}},
    }


def codes(findings, severity=None):
    return [f['code'] for f in findings if severity is None or f['severity'] == severity]


class EqModel(unittest.TestCase):
    def test_bell_and_shelves(self):
        self.assertAlmostEqual(mastering._bell_db(1000, 1000, 3.0, 0.7), 3.0, places=6)
        self.assertAlmostEqual(mastering._bell_db(1000, 1000, -2.5, 1.0), -2.5, places=6)
        self.assertLess(abs(mastering._bell_db(50, 1000, 3.0, 1.0)), 0.05)
        self.assertAlmostEqual(mastering._shelf_db(10, 200, -3.0, 0.7071, False), -3.0, places=2)
        self.assertLess(abs(mastering._shelf_db(10000, 200, -3.0, 0.7071, False)), 0.01)
        self.assertAlmostEqual(mastering._shelf_db(200, 200, 4.0, 0.7071, False), 2.0, places=6)   # half gain at the corner
        self.assertAlmostEqual(mastering._shelf_db(20000, 3000, 2.0, 0.7071, True), 2.0, places=1)
        self.assertLess(abs(mastering._shelf_db(100, 3000, 2.0, 0.7071, True)), 0.01)

    def test_eq_response_sums_the_bands(self):
        p = {'low.freq': 100, 'low.gain': -2.0, 'peak2.freq': 1000, 'peak2.gain': 1.5, 'peak2.q': 0.7}
        r = mastering.eq_response_db(p, [20, 1000, 15000])
        self.assertAlmostEqual(r[1], 1.5 + mastering._shelf_db(1000, 100, -2.0, 0.7071, False), places=6)
        self.assertLess(r[0], -1.5)
        self.assertEqual(mastering.eq_response_db({}, [100, 1000]), [0.0, 0.0])


class Correction(unittest.TestCase):
    def test_dead_band_and_clamp(self):
        valid = [True] * len(HZ)
        small = [0.8 * math.sin(i) for i in range(len(HZ))]
        wanted, _ = mastering.correction_curve(HZ, small, valid, dead_db=1.0, strength=0.75, max_db=3.0)
        self.assertTrue(all(w == 0 for w in wanted if w is not None))
        big = [12.0 if f < 150 else 0.0 for f in HZ]            # 12 dB too much bass
        wanted, centre = mastering.correction_curve(HZ, big, valid, dead_db=1.0, strength=1.0, max_db=3.0)
        self.assertEqual(centre, 0.0)                           # the median is the anchor
        self.assertEqual(min(w for w in wanted if w is not None), -3.0)
        self.assertTrue(all(w <= 0 for w in wanted if w is not None))

    def test_nothing_judged_at_16k_and_above(self):
        wanted, _ = mastering.correction_curve(HZ, [0.0] * 27 + [10.0, 20.0, 30.0], [True] * len(HZ), dead_db=1.0,
                                               strength=0.75, max_db=3.0)
        self.assertIsNone(wanted[HZ.index(16000)])
        self.assertIsNone(wanted[HZ.index(20000)])
        self.assertIsNone(wanted[HZ.index(25)])

    def test_recentred_on_the_mids(self):
        # A mix 2 dB louder everywhere is not a tonal difference.
        wanted, centre = mastering.correction_curve(HZ, [2.0] * len(HZ), [True] * len(HZ), dead_db=1.0, strength=0.75,
                                                    max_db=3.0)
        self.assertAlmostEqual(centre, 2.0)
        self.assertTrue(all(w == 0 for w in wanted if w is not None))


class Guard(unittest.TestCase):
    def test_reference_cannot_push_a_band_past_the_profile(self):
        wanted = [-3.0 if f >= 6000 else (2.0 if 250 <= f < 800 else 0.0) for f in HZ]
        bands = {'brilliance': -4.0, 'air': -5.0, 'lowmid': 2.5, 'sub': 0.0}
        limits = {'brilliance': {'low': -6.0}, 'air': {'low': -6.0}, 'lowmid': {'high': 4.0}}
        out, hit = mastering.profile_guard(HZ, wanted, bands, limits, margin=0.75)
        self.assertAlmostEqual(out[HZ.index(8000)], -1.25)          # brilliance may drop to -5.25 only
        self.assertAlmostEqual(out[HZ.index(16000)], -0.25)         # air already at -5: 0.25 dB left
        self.assertAlmostEqual(out[HZ.index(400)], 0.75)            # lowmid 2.5 + 0.75 = 3.25 = 4 - margin
        self.assertEqual(out[HZ.index(1000)], 0.0)
        self.assertEqual(set(hit), {'brilliance', 'air', 'lowmid'})
        # A band already past its limit is not pushed further out, but may come back.
        out, _ = mastering.profile_guard(HZ, [1.0] * len(HZ), {'lowmid': 5.0}, {'lowmid': {'high': 4.0}})
        self.assertEqual(out[HZ.index(400)], 0.0)
        out, _ = mastering.profile_guard(HZ, [-1.0] * len(HZ), {'lowmid': 5.0}, {'lowmid': {'high': 4.0}})
        self.assertEqual(out[HZ.index(400)], -1.0)


class Fit(unittest.TestCase):
    def test_bass_surplus_gets_a_low_cut(self):
        diff = [6.0 if f <= 125 else 0.0 for f in HZ]
        wanted, _ = mastering.correction_curve(HZ, diff, [True] * len(HZ), dead_db=1.0, strength=0.75, max_db=3.0)
        eq, achieved, rms = mastering.fit_eq(HZ, wanted)
        self.assertTrue(eq)
        lows = [a for a, f in zip(achieved, HZ) if a is not None and f <= 80]
        highs = [a for a, f in zip(achieved, HZ) if a is not None and f >= 2000]
        self.assertLess(max(lows), -1.5)
        self.assertLess(max(abs(h) for h in highs), 0.5)
        for k, v in eq.items():
            if k.endswith('.gain'):
                self.assertLessEqual(abs(v), 3.0)
            if k.endswith('.q') and k.startswith('peak'):
                self.assertLessEqual(v, 1.0)            # broad bells only
        full = mastering.eq_response_db(eq, [f for f in HZ if 31 <= f <= 12600])
        self.assertLessEqual(max(abs(x) for x in full), 3.0 + 1e-6)
        self.assertLess(rms, 1.0)

    def test_dark_mix_gets_a_top_lift_within_limits(self):
        diff = [0.0 if f < 3000 else -8.0 for f in HZ]
        wanted, _ = mastering.correction_curve(HZ, diff, [True] * len(HZ), dead_db=1.0, strength=0.75, max_db=3.0)
        eq, achieved, _ = mastering.fit_eq(HZ, wanted)
        self.assertGreater(achieved[HZ.index(10000)], 2.0)
        self.assertLessEqual(max(abs(a) for a in achieved if a is not None), 3.0 + 1e-6)

    def test_flat_is_no_eq_and_deterministic(self):
        self.assertEqual(mastering.fit_eq(HZ, [0.0] * len(HZ))[0], {})
        wanted = [None if f < 31 or f > 12600 else 2.5 * math.sin(i / 3) for i, f in enumerate(HZ)]
        self.assertEqual(mastering.fit_eq(HZ, wanted), mastering.fit_eq(HZ, wanted))
        eq = mastering.fit_eq(HZ, wanted)[0]
        self.assertLessEqual(sum(1 for k in eq if k.startswith('peak') and k.endswith('.gain')), 3)

    def test_eq_loudness_estimate(self):
        spec = [-20.0] * len(HZ)
        self.assertAlmostEqual(mastering.eq_loudness_change(HZ, spec, {}), 0.0)
        up = {'peak2.freq': 1000, 'peak2.gain': 3.0, 'peak2.q': 0.1}      # very broad: ~ +3 everywhere that counts
        self.assertGreater(mastering.eq_loudness_change(HZ, spec, up), 1.5)
        self.assertAlmostEqual(mastering.width_loudness_change(100.0, 1.0), 0.0)
        self.assertGreater(mastering.width_loudness_change(100.0, 1.2), 0.0)


class Platforms(unittest.TestCase):
    def test_presets_and_aliases(self):
        self.assertEqual(mastering.get_platform('streaming').lufs, -14.0)
        self.assertEqual(mastering.get_platform('club').name, 'loud')
        self.assertEqual(mastering.get_platform('jazz').name, 'dynamic')
        self.assertEqual(mastering.get_platform(None).name, 'auto')
        for p in mastering.PLATFORMS.values():
            self.assertLessEqual(p.tp, -1.0)
        with self.assertRaises(mastering.MasteringError) as cm:
            mastering.get_platform('vinyl')
        self.assertIn('streaming', str(cm.exception))


class Check(unittest.TestCase):
    def test_clean_master(self):
        f = mastering.check(report())
        self.assertEqual(codes(f, 'warn'), [])
        self.assertIn('true_peak', codes(f, 'ok'))
        note = next(x for x in f if x['code'] == 'normalisation')
        self.assertIn('-14', note['message'])
        self.assertIn('-16', note['message'])
        self.assertIn('turned down 4.0 dB', note['message'])     # -10 LUFS on Spotify & co.

    def test_problems_are_found_with_fixes(self):
        f = mastering.check(report(lufs=-6.0, tp=-0.2, plr=4.0, lra=1.5, clipped=12, dc=(0.004, 0.0), corr=-0.1,
                                   low_corr=0.5), render={'master': {'fx': []}})
        warn = codes(f, 'warn')
        for c in ('true_peak', 'clipping', 'dc_offset', 'loudness_window', 'squashed', 'mono_low_end', 'mono_compat',
                  'no_limiter'):
            self.assertIn(c, warn)
        tp = next(x for x in f if x['code'] == 'true_peak')
        self.assertEqual(tp['fix']['params']['ceiling'], -1.2)
        self.assertEqual(next(x for x in f if x['code'] == 'mono_low_end')['fix']['params']['monobass'], 120)
        order = [{'warn': 0, 'info': 1, 'ok': 2}[x['severity']] for x in f]
        self.assertEqual(order, sorted(order))                            # warn first, ok last

    def test_lra_against_the_genre(self):
        self.assertIn('lra_small', codes(mastering.check(report(lra=2.0), platform='dynamic'), 'warn'))
        self.assertIn('lra_small', codes(mastering.check(report(lra=2.0)), 'info'))
        self.assertIn('lra_large', codes(mastering.check(report(lra=20.0))))

    def test_platform_targets(self):
        f = mastering.check(report(lufs=-10.0), platform='streaming')
        self.assertIn('loudness_platform', codes(f, 'warn'))
        self.assertEqual(next(x for x in f if x['code'] == 'loudness_platform')['fix']['gainDbChange'], -4.0)
        self.assertNotIn('loudness_platform', codes(mastering.check(report(lufs=-14.3), platform='streaming')))

    def test_tone(self):
        vs = [6.0 if f <= 100 else 0.0 for f in HZ]
        f = mastering.check(report(vs_ref=vs, bands={'sub': 7.0, 'bass': 2.0}))
        self.assertIn('tone_profile', codes(f, 'info'))
        self.assertIn('tone_band', codes(f, 'warn'))               # sub over its +5 limit: a mix problem

    def test_reads_a_song_folder(self):
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_mcheck_'))
        try:
            (d / 'out').mkdir()
            (d / 'out' / 'report.json').write_text(json.dumps(report(tp=0.1)), encoding='utf-8')
            (d / 'out' / 'song.render.json').write_text(json.dumps({'master': {'fx': [{'type': 'eq', 'params': {}}]}}),
                                                        encoding='utf-8')
            warn = codes(mastering.check(d), 'warn')
            self.assertIn('true_peak', warn)
            self.assertIn('no_limiter', warn)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        with self.assertRaises(mastering.MasteringError):
            mastering.check(d / 'nothing')


class Apply(unittest.TestCase):
    def song(self):
        s = Song('Apply Test', tempo=120)
        s.section('a', bars=2)
        s.track('pad', inst.va()).play(s.prog('i VI').block(), 0)
        s.master.add(fx.eq({'hp.freq': 25}), fx.width(width=1.1), fx.limiter(ceiling=-1.2, gain=3.0))
        s.master.automate('fx.2.gain', [(0, 3.0), (4, 4.0)])
        return s

    def test_into_the_song_chain(self):
        s = self.song()
        log = mastering.apply(s, eq={'low.freq': 100, 'low.gain': -1.5}, width=1.1, monobass=120,
                              limiter={'ceiling': -1.2, 'release': 150}, loudness_change=1.5)
        self.assertEqual([f.type for f in s.master.fx], ['eq', 'eq', 'width', 'limiter'])
        self.assertEqual(s.master.fx[0].name, 'master_eq')
        self.assertAlmostEqual(s.master.fx[2].params['width'], 1.21)
        self.assertEqual(s.master.fx[2].params['monobass'], 120)
        self.assertEqual(s.master.fx[3].params['gain'], 4.5)
        self.assertEqual(s.master.fx[3].params['release'], 150)
        self.assertEqual(s.master._auto[0][0], 'fx.3.gain')              # the automation follows its limiter
        self.assertTrue(log)
        render = s.compile()
        self.assertEqual(render['master']['automation'][0]['target'], 'fx.3.gain')
        # Applying again replaces the mastering eq instead of stacking a second one.
        mastering.apply(s, eq={'low.freq': 100, 'low.gain': -1.0})
        self.assertEqual([f.type for f in s.master.fx], ['eq', 'eq', 'width', 'limiter'])
        self.assertEqual(s.master.fx[0].params['low.gain'], -1.0)

    def test_song_without_a_chain(self):
        s = Song('Bare', tempo=100)
        s.section('a', bars=1)
        mastering.apply(s, width=1.2, limiter={'ceiling': -1.2}, loudness_change=2.0)
        self.assertEqual([f.type for f in s.master.fx], ['width', 'limiter'])
        self.assertEqual(s.master.fx[1].params['gain'], 2.0)

    def plan(self):
        return mastering.MasterPlan(
            source='x/mix.wav', song_dir=None, out='x/master', profile='default', platform='auto', reference=None,
            measured={'lufs': -12.0}, targets={'lufs': -10.0, 'truePeakDbtp': -1.0},
            eq={'high.freq': 8000, 'high.gain': 1.0, 'high.q': 0.7071}, width={'width': 1.1, 'monobass': 120},
            limiter={'ceiling': -1.2, 'gain': 2.0, 'release': 120.0},
            estimate={'songLimiterGainChange': 2.0, 'maxDriveDb': 3.0}, curve={}, log=['a', 'b'])

    def test_plan_roundtrip_snippet_and_patch(self):
        p = self.plan()
        self.assertEqual([f.type for f in p.chain()], ['eq', 'width', 'limiter'])
        q = mastering.MasterPlan.from_dict(json.loads(json.dumps(p.to_dict())))
        self.assertEqual(q.to_dict(), p.to_dict())
        s = self.song()
        exec(p.snippet(), {'mastering': mastering, 's': s})           # what song.py would run
        self.assertEqual(s.master.fx[0].name, 'master_eq')
        self.assertEqual(s.master.fx[-1].params['gain'], 5.0)
        self.assertEqual(p.patch().fx[-1].type, 'limiter')
        with self.assertRaises(mastering.MasteringError):
            mastering.MasterPlan.from_dict({'format': 'x'})

    def test_postpass_render_json(self):
        p = self.plan()
        r = mastering._postpass_render_json(pathlib.Path('C:/x/mix.wav'), {'rate': 48000, 'frames': 96000, 'channels': 2},
                                            p.chain())
        self.assertEqual(r['lengthBeats'], 2.0)
        self.assertEqual(r['tempo'], 60.0)
        self.assertEqual(r['export']['bitDepth'], 32)
        self.assertEqual([f['type'] for f in r['master']['fx']], ['eq', 'width', 'limiter'])
        self.assertEqual(r['tracks'][0]['notes'], [[0.0, 2.0, 60, 127]])


class EndToEnd(unittest.TestCase):
    """match -> post-pass render -> check with the real engine and ffmpeg (skipped without them)."""

    SONG = '''
from agentsound import *

TOP = %s

def build():
    s = Song('Master Test', tempo=120, key='A minor', seed=2)
    a = s.section('verse', bars=4)
    b = s.section('chorus', bars=4)
    s.track('drums', inst.drums(kit='synthwave')).play(drums({'kick': 'x...x...x...x...', 'hat': '..x...x...x...x.',
                                                               'snare': '....x.......x...'}), 0, times=8)
    t = s.track('pad', inst.va(unison=3), fx=[fx.chorus(mix=0.3)])
    t.play(s.prog('i VI III VII').block(), a)
    t.play(s.prog('i VI III VII').block(), b)
    if TOP:
        s.master.add(fx.eq({'high.freq': 3000, 'high.gain': TOP}))
    s.master.add(fx.limiter(gain=%s))
    return s
'''

    def setUp(self):
        try:
            self.engine = cli.find_engine()
        except cli.CliError:
            self.skipTest('engine not built')
        if not cli.find_ffmpeg():
            self.skipTest('ffmpeg not found')
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_master_'))
        for name, top, gain in (('song', 0, 0), ('ref', 6, 4)):
            (self.dir / name).mkdir()
            (self.dir / name / 'song.py').write_text(self.SONG % (top, gain), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(['build', str(self.dir / name), '--no-mp3']), 0)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_match_a_brighter_reference_and_render(self):
        ref = self.dir / 'ref' / 'out' / 'mix.wav'
        plan = mastering.match(self.dir / 'song', ref=ref, platform='streaming', profile='synthwave')
        self.assertTrue((pathlib.Path(plan.out) / 'master.json').is_file())
        eqc = mastering.eq_response_db(plan.eq, [8000])[0]
        self.assertGreater(eqc, 1.0)                     # the reference is brighter: the top comes up ...
        self.assertLessEqual(eqc, 3.0 + 1e-6)            # ... gently
        self.assertEqual(plan.targets['lufs'], -14.0)
        res = plan.render(mp3=False, images=False)
        self.assertTrue(pathlib.Path(res['mastered']).is_file())
        self.assertLessEqual(res['after']['truePeakDbtp'], -1.0 + 0.05)
        if not res['cappedByMaxDrive']:
            self.assertLessEqual(abs(res['after']['lufs'] + 14.0), 0.3)
        self.assertLess(res['compare']['after']['spectrumRmsDb'], res['compare']['before']['spectrumRmsDb'])
        # Deterministic: the same plan renders bit-identical audio.
        first = pathlib.Path(res['mastered']).read_bytes()
        res2 = plan.render(mp3=False, images=False)
        self.assertEqual(pathlib.Path(res2['mastered']).read_bytes(), first)
        self.assertEqual(res2['calibration'], res['calibration'])
        f = mastering.check(res['afterReport'], platform='streaming')
        self.assertNotIn('true_peak', codes(f, 'warn'))

    def test_loud_master_stops_at_the_density_floor(self):
        mix = self.dir / 'song' / 'out' / 'mix.wav'
        plan = mastering.match(self.dir / 'song', ref=mix, platform='loud', profile='synthwave',
                               out=self.dir / 'song' / 'out' / 'master_loud')
        floor = plan.targets['crestFloorDb']
        self.assertIsNotNone(floor)
        # The reference is the mix itself: a loud master may get up to 3 dB denser than it.
        self.assertLess(abs(floor - (plan.estimate['crestNowDb'] - 3.0)), 0.25)
        res = plan.render(mp3=False, images=False, backoff=False)
        last = res['calibration'][-1]
        self.assertGreaterEqual(last['crestDb'], floor - 0.35)
        self.assertTrue(res['reachedTarget'] or res['cappedByDensity'] or res['cappedByMaxDrive'])
        self.assertLessEqual(res['after']['truePeakDbtp'], -1.0 + 0.05)

    def test_cli(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['master', str(self.dir / 'song'), '--platform', 'dynamic']), 0)
            self.assertEqual(cli.main(['master', str(self.dir / 'song'), '--check']), 0)
        text = out.getvalue()
        self.assertIn('mastering.apply(s', text)
        self.assertIn('true_peak', text)
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(cli.main(['master', str(self.dir / 'song'), '--section', 'bridge']), 1)
        self.assertIn('chorus', err.getvalue())


if __name__ == '__main__':
    unittest.main()
