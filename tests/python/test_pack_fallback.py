"""A band that finds its preferred sample pack missing never falls back silently: library.want() records the miss on
the song, Song.compile() raises with the install hint (samples fetch / AGENTSOUND_SAMPLES), and with
$AGENTSOUND_PACK_FALLBACK=1 the substitutes render with an error-level 'pack_fallback' report warning."""
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentsound import Song, bands, cli, jazz, library  # noqa: E402
from agentsound.bandlib import jazz as jb  # noqa: E402
from agentsound.bandlib import rock  # noqa: E402
from agentsound.endless import genre, perform  # noqa: E402
from agentsound.theory import ComposeError, PackMissingError  # noqa: E402


@contextmanager
def no_packs(allow: bool = False):
    """library.SAMPLES pointed at an empty folder (a git worktree without assets/samples); allow: the opt-in env."""
    env = {library.FALLBACK_ENV: '1'} if allow else {}
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(library, 'SAMPLES', Path(tmp)), \
            mock.patch.dict(os.environ, env):
        if not allow:
            os.environ.pop(library.FALLBACK_ENV, None)
        yield Path(tmp)


def newage_song() -> Song:
    """The endless new-age-piano band (the solo_piano grand) with one chord: what songs/pro-newage-* build."""
    s = Song('t', tempo=72, key='C major')
    a = s.section('a', bars=1)
    b = perform.band(s, genre('new-age-piano'), 'gentle', jazz.Feel(72, ratio=0.5))
    b.piano.note(72, a.start, 2, vel=80)
    b.comp.note(48, a.start, 4, vel=60)
    return s


class PackFallback(unittest.TestCase):
    def test_missing_grand_raises_with_the_install_hint(self):
        with no_packs():
            s = newage_song()
            self.assertIn('salamander-grand', s.pack_fallbacks)
            self.assertTrue(any('GeneralUser' in x for x in s.pack_fallbacks['salamander-grand']))
            with self.assertRaises(PackMissingError) as e:      # a ComposeError the reroll loops re-raise
                s.compile()
        msg = str(e.exception)
        for part in ('salamander-grand', 'GeneralUser GS Grand Piano', 'python -m agentsound samples fetch',
                     'AGENTSOUND_SAMPLES', library.FALLBACK_ENV):
            self.assertIn(part, msg)

    def test_opt_in_renders_the_substitute_and_reports_it(self):
        with no_packs(allow=True):
            s = newage_song()
            r = s.compile()
        self.assertTrue(any('salamander-grand' in w for w in s.warnings))
        fb = {f['pack']: f for f in r['analysis']['packFallbacks']}
        self.assertIn('salamander-grand', fb)
        self.assertIn('GeneralUser', fb['salamander-grand']['instead'])
        self.assertEqual(next(t for t in r['tracks'] if t['id'] == 'piano')['instrument']['type'], 'sf2')

    def test_installed_pack_records_nothing(self):
        with no_packs() as root:
            (root / 'salamander-grand').mkdir()
            (root / 'salamander-grand' / 'SOURCE.json').write_text('{}')
            s = Song('t', tempo=72)
            bands.make('solo_piano', s)
        self.assertNotIn('salamander-grand', s.pack_fallbacks)

    def test_checks_outside_a_band_build_record_nothing(self):
        # installed() in a test's skip condition or the catalog: no song is being built, nothing is recorded
        with no_packs():
            s = Song('t', tempo=72)
            self.assertFalse(rock.installed('salamander-grand'))
            self.assertFalse(jb.installed('salamander-grand'))
            self.assertFalse(library.has('salamander-grand'))
        self.assertEqual(s.pack_fallbacks, {})

    def test_strict_presets_still_raise_at_build(self):
        with no_packs(), self.assertRaisesRegex(ComposeError, 'samples fetch '):
            bands.make('solo_piano', Song('t', tempo=72), strict=True)

    def test_jazz_band_auto_records(self):
        with no_packs():
            s = Song('t', tempo=120)
            s.section('a', bars=1)
            jazz.band(s)
            self.assertIn('salamander-grand', s.pack_fallbacks)

    def test_endless_does_not_reroll_on_it(self):
        # endless.run.candidates: a ComposeError means "next seed"; a missing pack stops the run at once
        from agentsound.endless import run
        calls = []

        def prepare(*a, **kw):
            calls.append(1)
            raise PackMissingError('salamander-grand missing')
        args = mock.Mock()
        with mock.patch.object(run, 'prepare', prepare), self.assertRaises(PackMissingError):
            run.candidates(genre('new-age-piano'), 1, 4, args, lambda *_: None)
        self.assertEqual(len(calls), 1)

    def test_allowed_values(self):
        for v, ok in (('1', True), ('true', True), ('on', True), ('0', False), ('', False), ('no', False)):
            with mock.patch.dict(os.environ, {library.FALLBACK_ENV: v}):
                self.assertEqual(library.fallback_allowed(), ok, v)


class PackFallbackReport(unittest.TestCase):
    """The engine turns the render's analysis.packFallbacks into error-level 'pack_fallback' report warnings."""

    def setUp(self):
        try:
            self.engine = cli.find_engine()
        except cli.CliError:
            self.skipTest('engine not built')

    def test_report_error(self):
        with no_packs(allow=True):
            s = newage_song()
            r = s.compile()
        with tempfile.TemporaryDirectory() as out:
            rj = cli.write_render(r, Path(out) / 'song.render.json')
            cli.run_engine(self.engine, rj, Path(out), render=r)
            rep = json.loads((Path(out) / 'report.json').read_text(encoding='utf-8'))
        ws = [w for w in rep['warnings'] if w['code'] == 'pack_fallback']
        self.assertTrue(ws, rep['warnings'])
        self.assertTrue(all(w['severity'] == 'error' for w in ws))
        self.assertTrue(any('salamander-grand' in w['message'] for w in ws))
        self.assertEqual(rep['warnings'][0]['code'], 'pack_fallback')       # ranked first among the errors

    def test_engine_strict_on_the_entries(self):
        with no_packs(allow=True):
            r = newage_song().compile()
        r['analysis']['packFallbacks'][0]['extra'] = 1
        with tempfile.TemporaryDirectory() as out:
            rj = cli.write_render(r, Path(out) / 'song.render.json')
            import subprocess
            p = subprocess.run([str(self.engine), 'validate', str(rj)], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('packFallbacks', p.stdout + p.stderr)


if __name__ == '__main__':
    unittest.main()
