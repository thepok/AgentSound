"""The endless quality score (stage 1 of the learned-generator roadmap): composer.score - one number 0-100 from the
notes (the blind test's tells, breath, body, the lead sheet's checks) weighed by a per-style DATA table
(genres.SCORES), hard rules capping it -, the runner's best-of-N (run.candidates: compose + perform N tunes for one
slot without audio, render the best) and `python -m agentsound score`."""
import pickle
import contextlib
import io
import json
import pathlib
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agentsound import cli, endless  # noqa: E402
from agentsound.endless import composer, genres, run  # noqa: E402

JAZZ = endless.genre('jazz-piano')


class Table(unittest.TestCase):
    def test_every_style_has_a_well_formed_table(self):
        styles = set(genres.STYLES) | {g.style for g in genres.GENRES.values()}
        self.assertLessEqual(set(genres.STYLES), set(genres.SCORES))
        self.assertLessEqual(set(genres.SCORES), styles)
        for style, table in genres.SCORES.items():
            for k, spec in table.items():
                self.assertIn(len(spec), (4, 5), (style, k))
                lo, hi, w, hard = spec[:4]
                self.assertLessEqual(lo, hi, (style, k))
                self.assertGreater(w, 0, (style, k))
                self.assertIsInstance(hard, bool, (style, k))
                if len(spec) == 5:
                    self.assertGreater(spec[4], 0, (style, k))
                else:
                    self.assertGreater(hi, lo, (style, k))     # (a point range needs its unit)

    def test_the_formula(self):
        t = {'a': (0, 1, 1, False), 'b': (0, 0, 1, True, 1)}
        self.assertEqual(composer.score(None, metrics={'a': 0.5, 'b': 0}, table=t, style='jazz')['score'], 100.0)
        r = composer.score(None, metrics={'a': 2.0, 'b': 0}, table=t, style='jazz')    # d = 1 unit: sub 0.5
        self.assertEqual(r['parts']['a'], (2.0, 0.5, 1))
        self.assertEqual(r['score'], 75.0)
        self.assertEqual(r['worst'][0]['metric'], 'a')
        # a broken hard rule scales the score into 0 .. SCORE_HARD_CAP x its sub-score
        r = composer.score(None, metrics={'a': 0.5, 'b': 1}, table=t, style='jazz')
        self.assertEqual(r['hard'], ['b'])
        self.assertAlmostEqual(r['score'], round(r['mean'] * genres.SCORE_HARD_CAP * 0.5 / 100, 1))
        self.assertEqual(r['worst'][0]['metric'], 'b')                          # hard offenders first
        self.assertEqual(composer.score(None, metrics={'a': 0.5}, table=t, style='jazz')['missing'], ['b'])


class OnTunes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.made = {}
        for style, name in genres.STYLES.items():
            g = endless.genre(name)
            t = composer.compose(g, 101)
            cls.made[style] = (t, endless.song(t), g)

    def test_every_style_measures_its_table(self):
        for style, (t, s, g) in self.made.items():
            r = composer.score(s, t, g)
            self.assertEqual(r['style'], style)
            self.assertTrue(0 <= r['score'] <= 100, (style, r['score']))
            # every table metric is measured (reharm_col only with a reharm, a_ends with an A1 + A2)
            self.assertLessEqual(set(r['missing']), {'reharm_col', 'a_ends'}, (style, r['missing']))
            self.assertLessEqual(len(r['worst']), 5)
            self.assertEqual(composer.score(s, t, g)['score'], r['score'])      # deterministic

    def test_degrading_a_tune_lowers_its_score(self):
        t, s, g = self.made['jazz']
        base = composer.score(s, t, g)['score']
        tr = s.tracks['piano']
        orig = list(tr._notes)
        try:
            solo = s['solo']
            line = sorted((n for n in orig if solo.start <= n.start < solo.end), key=lambda n: n.start)
            wrap = {id(n) for i, n in enumerate(line) if i % 7 == 3 and n.dur <= 0.6}
            tr._notes = [n._replace(vel=64, pitch=n.pitch + 12 if id(n) in wrap else n.pitch) for n in orig]
            r = composer.score(s, t, g)
        finally:
            tr._notes = orig
        self.assertLess(r['score'], base - 15, (base, r['score'], r['worst']))
        self.assertIn('wraps', r['hard'])

    def test_a_composed_reference_scores_high(self):
        song, tune, g = run.load_scored(ROOT / 'songs' / 'pro2-piano-waltz')
        self.assertEqual(g.name, 'jazz-piano')
        r = composer.score(song, tune, g)
        self.assertGreaterEqual(r['score'], 95, r['worst'])


def check_baseline():
    baseline = json.loads((ROOT / 'tests/python/endless_score_baseline.json').read_text(encoding='utf-8'))
    case = unittest.TestCase()
    from agentsound.bandlib.orchestra import installed
    for style, expected in baseline['styles'].items():
        if style == 'orchestra' and not installed('sso'):        # (its band needs the SSO sections)
            continue
        g = endless.genre({**genres.STYLES, 'orchestra': 'orchestra-film'}.get(style, style))
        for seed, row in expected['tunes'].items():
            t = composer.compose(g, int(seed))
            s = endless.song(t)
            case.assertEqual(composer.score_metrics(s, t, style), row['metrics'], (style, seed))
            case.assertEqual(json.loads(json.dumps(composer.score(s, t, g))), row['score'], (style, seed))
        ranked = run.candidates(g, 300, 3, SimpleNamespace(mood=None, swing=None), lambda _: None)
        case.assertEqual([[c['seed'], c['score']['score']] for c in ranked], expected['candidates'], style)


class MetricParity(unittest.TestCase):
    """Captured on master 7d9fce9 before the NoteView refactor; exact metrics and rankings."""
    def test_master_metrics_scores_and_candidate_order(self):
        # perform's modal LH figure uses set iteration to break ties: fix the hash seed
        # in both the master capture and this measurement, without changing composition.
        code = "import sys; sys.path.insert(0, 'tests/python'); from test_endless_score import check_baseline; check_baseline()"
        checked = subprocess.run([sys.executable, '-c', code], cwd=ROOT,
                                 env=dict(os.environ, PYTHONHASHSEED='0'), capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_renamed_tracks_and_read_only_metrics(self):
        for style, name in genres.STYLES.items():
            t = composer.compose(endless.genre(name), 101)
            s = endless.song(t)
            before = pickle.dumps(s.__dict__)
            expected = composer.score_metrics(s, t, style)
            self.assertEqual(pickle.dumps(s.__dict__), before)
            expected.pop('body_heard', None)
            fn = composer.tells if style == 'jazz' else composer.piano_tells
            expected_tells, expected_breath = fn(s, t), composer.breath(s)
            for melody, accompaniment in (('rh', 'lh'), ('melody', 'accomp')):
                s.tracks[melody] = s.tracks.pop('piano')
                s.tracks[accompaniment] = s.tracks.pop('comp')
                before = pickle.dumps(s.__dict__)
                tracks = dict(s.tracks)
                # Observe every metric entry point: temporary track aliases are forbidden too.
                original = composer.breath
                def observe(view):
                    self.assertEqual(s.tracks, tracks)
                    return original(view)
                with patch.object(composer, 'breath', side_effect=observe) as measured:
                    # A dictionary-only rename retains the compile IDs: body_stats cannot
                    # resolve those IDs by the new key; note metrics must still agree.
                    actual = composer.score_metrics(s, t, style)
                    actual.pop('body_heard', None)
                    self.assertEqual(actual, expected, (style, melody))
                    self.assertEqual(measured.call_count, 1)
                self.assertEqual(pickle.dumps(s.__dict__), before)
                view = composer.NoteView(s, melody, (accompaniment,))
                self.assertEqual(fn(view, t), expected_tells)
                self.assertEqual(composer.breath(view), expected_breath)
                self.assertEqual(pickle.dumps(s.__dict__), before)
                with self.assertRaises(AttributeError):
                    view.rh = ()
                with self.assertRaises(TypeError):
                    view.secs['other'] = None
                s.tracks['piano'] = s.tracks.pop(melody)
                s.tracks['comp'] = s.tracks.pop(accompaniment)


class BestOfN(unittest.TestCase):
    def test_candidates_share_the_slot_and_come_best_first(self):
        lines = []
        args = SimpleNamespace(mood=None, swing=None)
        ranked = run.candidates(JAZZ, 300, 3, args, lines.append)
        self.assertTrue(ranked)
        scores = [c['score']['score'] for c in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))
        slot = {(c['tune'].mood, c['tune'].feel, c['tune'].key, c['tune'].tempo) for c in ranked}
        self.assertEqual(len(slot), 1, slot)                  # one set slot: only the composition differs
        self.assertTrue(any(ln.startswith('best of') for ln in lines), lines)
        first = next((c for c in ranked if c['seed'] == 300), None)
        if first is not None:                                  # the first seed composes as without best-of-N
            self.assertIsNone(first['plan'])
            self.assertEqual(first['tune'].title, composer.compose(JAZZ, 300).title)

    def test_the_cli(self):
        ap = cli.build_parser()
        self.assertEqual(ap.parse_args(['endless', 'jazz-piano', '--candidates', '1']).candidates, 1)
        self.assertIsNone(ap.parse_args(['endless', 'jazz-piano']).candidates)
        # an endless tune folder: the tune composed again from tune.json's compose arguments
        t = composer.compose(JAZZ, 42)
        with tempfile.TemporaryDirectory(dir=ROOT / '.tmp' if (ROOT / '.tmp').is_dir() else None) as d:
            (pathlib.Path(d) / 'tune.json').write_text(json.dumps(
                {'title': t.title, 'genre': t.genre, 'seed': 42,
                 'compose': {'seed': 42, 'mood': None, 'swing': None, 'plan': None}}), encoding='utf-8')
            song, tune, g = run.load_scored(pathlib.Path(d))
            self.assertEqual(tune.title, t.title)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(cli.main(['score', d]), 0)
            self.assertIn('score ', buf.getvalue())
            self.assertIn('worst offenders', buf.getvalue())


if __name__ == '__main__':
    unittest.main()
