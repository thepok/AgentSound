"""The learned ears (agentsound.ears): JSON plumbing, the combined score and graceful degradation - no torch needed.
The real models run only when AGENTSOUND_EARS_PYTHON points at the ears venv (test_real_models)."""

import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import cli, ears

ROW = {'id': 'x', 'aesthetics': {'PQ': 7.0, 'PC': 3.0, 'CE': 6.0, 'CU': 6.5}, 'clap': {'instrument': 'piano',
                                                                                      'pReal': 0.6}}


def make_song(root: pathlib.Path, tracks=None, sections=None) -> pathlib.Path:
    song = root / 'demo'
    (song / 'out').mkdir(parents=True)
    (song / 'song.py').write_text('# test\n')
    (song / 'out' / 'mix.wav').write_bytes(b'RIFF')
    tracks = tracks if tracks is not None else [{'id': 'piano', 'instrument': {'type': 'sampler'}},
                                                {'id': 'pad', 'instrument': {'type': 'va'}}]
    (song / 'out' / 'song.render.json').write_text(json.dumps({'tracks': tracks}))
    secs = sections if sections is not None else [{'name': 'intro', 'startSec': 0.0, 'endSec': 8.0},
                                                  {'name': 'verse', 'startSec': 8.0, 'endSec': 30.0},
                                                  {'name': 'verse', 'startSec': 30.0, 'endSec': 52.0},
                                                  {'name': 'tag', 'startSec': 52.0, 'endSec': 53.0}]
    (song / 'out' / 'report.json').write_text(json.dumps({'sections': secs, 'warnings': []}))
    return song


FAKE_WORKER = r'''
import json, sys
req = json.load(open(sys.argv[1], encoding='utf-8'))
rows = [{'id': f['id'], 'path': f['path'], 'seconds': 10.0, 'windows': 1,
         'aesthetics': {'PQ': 7.5, 'PC': 3.0, 'CE': 6.5, 'CU': 7.0},
         'clap': {'instrument': f.get('instrument') or 'music', 'pReal': 0.7, 'pairs': []}} for f in req['files']]
json.dump({'ok': True, 'device': 'cpu', 'models': {}, 'files': rows, 'refs': [], 'fad': None},
          open(sys.argv[2], 'w', encoding='utf-8'))
'''


class Score(unittest.TestCase):
    def test_realism_is_the_weighted_clipped_mean(self):
        table = {'PQ': {'weight': 1.0, 'lo': 5.0, 'hi': 9.0}, 'pReal': {'weight': 1.0, 'lo': 0.0, 'hi': 1.0}}
        self.assertAlmostEqual(ears.realism(ROW, table), 100 * (0.5 + 0.6) / 2, places=1)
        hi = {**ROW, 'aesthetics': {'PQ': 99.0}}
        self.assertEqual(ears.realism({**hi, 'clap': {'pReal': 2.0}}, table), 100.0)    # clipped at 1
        self.assertEqual(ears.realism({'aesthetics': {'PQ': 0.0}, 'clap': {'pReal': -1}}, table), 0.0)

    def test_missing_signals_are_left_out_not_zero(self):
        table = {'PQ': {'weight': 1.0, 'lo': 5.0, 'hi': 9.0}, 'pReal': {'weight': 3.0, 'lo': 0.0, 'hi': 1.0}}
        self.assertAlmostEqual(ears.realism({'aesthetics': {'PQ': 7.0}}, table), 50.0)
        self.assertIsNone(ears.realism({}, table))

    def test_default_table_is_well_formed(self):
        self.assertTrue(ears.REALISM)
        for k, spec in ears.REALISM.items():
            self.assertEqual(set(spec), {'weight', 'lo', 'hi'}, k)
            self.assertLess(spec['lo'], spec['hi'], k)
            self.assertGreater(spec['weight'], 0, k)
        self.assertIsNotNone(ears.realism(ROW))


class Inputs(unittest.TestCase):
    def test_instrument_from_the_sampled_tracks_only(self):
        with tempfile.TemporaryDirectory() as td:
            song = make_song(pathlib.Path(td))
            self.assertEqual(ears.song_instrument(song / 'out' / 'song.render.json'), 'piano')
        with tempfile.TemporaryDirectory() as td:
            song = make_song(pathlib.Path(td), tracks=[{'id': 'lead', 'instrument': {'type': 'va'}}])
            self.assertIsNone(ears.song_instrument(song / 'out' / 'song.render.json'))
        with tempfile.TemporaryDirectory() as td:
            song = make_song(pathlib.Path(td), tracks=[{'id': 'piano', 'instrument': {'type': 'sampler'}},
                                                       {'id': 'drums', 'instrument': {'type': 'sampler'}}])
            self.assertEqual(ears.song_instrument(song / 'out' / 'song.render.json'), 'band')
        with tempfile.TemporaryDirectory() as td:                      # no word in the id: the sample pack's path
            song = make_song(pathlib.Path(td), tracks=[
                {'id': 'melody', 'instrument': {'type': 'sampler', 'params': {'samples': [
                    {'file': 'D:/x/assets/samples/headroom-piano/Samples/HEADROOM PIANO 60.wav'}]}}}])
            self.assertEqual(ears.song_instrument(song / 'out' / 'song.render.json'), 'piano')

    def test_song_sections_and_folders(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            song = make_song(root)
            files, songs = ears.collect([str(song)], section=True)
            self.assertEqual(songs, [song])
            ids = [f['id'] for f in files]
            self.assertEqual(ids, ['demo', 'demo:01_intro', 'demo:02_verse', 'demo:03_verse'])   # tag < 3 s
            self.assertEqual(len(set(ids)), len(ids))
            self.assertEqual((files[2]['start'], files[2]['end']), (8.0, 30.0))
            self.assertTrue(all(f['instrument'] == 'piano' for f in files))
            d = root / 'set'
            (d / 'sub').mkdir(parents=True)
            (d / 'a.mp3').write_bytes(b'x')
            (d / 'sub' / 'b.wav').write_bytes(b'x')
            (d / 'notes.txt').write_text('no audio')
            files, songs = ears.collect([str(d)], instrument='guitar')
            self.assertEqual(sorted(pathlib.Path(f['path']).name for f in files), ['a.mp3', 'b.wav'])
            self.assertEqual({f['instrument'] for f in files}, {'guitar'})
            self.assertEqual(songs, [])

    def test_bad_inputs_are_clear_errors(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ears.EarsError, 'no such'):
                ears.collect([str(pathlib.Path(td) / 'nope')])
            (pathlib.Path(td) / 'empty').mkdir()
            with self.assertRaisesRegex(ears.EarsError, 'no audio'):
                ears.collect([str(pathlib.Path(td) / 'empty')])
            song = make_song(pathlib.Path(td))
            (song / 'out' / 'mix.wav').unlink()
            with self.assertRaisesRegex(ears.EarsError, 'build it first'):
                ears.collect([str(song)])


class Degradation(unittest.TestCase):
    def test_missing_venv_names_the_install(self):
        with self.assertRaises(ears.EarsUnavailable) as cm:
            ears.find_python({ears.ENV_PYTHON: 'Z:/nowhere/python.exe'})
        self.assertIn('pip install', str(cm.exception))
        with mock.patch.object(ears, 'DEFAULT_EARS_PYTHONS', ('Z:/nowhere/python.exe',)):
            with self.assertRaises(ears.EarsUnavailable):
                ears.find_python({})

    def test_cli_exits_3_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            song = make_song(pathlib.Path(td))
            err = io.StringIO()
            with mock.patch.dict(os.environ, {ears.ENV_PYTHON: str(pathlib.Path(td) / 'missing.exe')}), \
                    redirect_stderr(err), redirect_stdout(io.StringIO()):
                code = cli.main(['ears', str(song)])
            self.assertEqual(code, 3)
            self.assertIn('ears need their own venv', err.getvalue())
            self.assertNotIn('Traceback', err.getvalue())

    def test_worker_crash_is_reported(self):
        with tempfile.TemporaryDirectory() as td:
            worker = pathlib.Path(td) / 'crash.py'
            worker.write_text("raise SystemExit('no torch here')")      # dies before writing a response
            with mock.patch.object(ears, 'WORKER', worker):
                with self.assertRaises(ears.EarsUnavailable) as cm:
                    ears.run_worker({'files': []}, py=pathlib.Path(sys.executable), timeout=60)
            self.assertIn('no torch here', str(cm.exception))

    def test_cache_dirs_follow_the_venv(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / 'cache').mkdir()
            py = root / 'agentsound-ears' / 'Scripts' / 'python.exe'
            env = ears.worker_env(py, {'PATH': 'x', 'TMP': 'keep'})
            self.assertEqual(env['HF_HOME'], str(root / 'cache' / 'hf'))
            self.assertEqual(env['TORCH_HOME'], str(root / 'cache' / 'torch'))
            self.assertEqual(env['TMP'], 'keep')                         # set by the caller: kept


class Plumbing(unittest.TestCase):
    def test_fake_worker_end_to_end_writes_ears_json_and_report_block(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            song = make_song(root)
            worker = root / 'fake_worker.py'
            worker.write_text(FAKE_WORKER)
            # the "venv python" is this interpreter; the worker path is swapped for the fake one
            with mock.patch.object(ears, 'WORKER', worker):
                res = ears.run([str(song)], section=True, ffmpeg='ffmpeg', py=pathlib.Path(sys.executable))
            self.assertEqual(len(res['files']), 4)
            self.assertTrue(all(r['realism'] is not None for r in res['files']))
            data = json.loads((song / 'out' / 'ears.json').read_text())
            self.assertEqual(data['files'][0]['clap']['instrument'], 'piano')
            rep = json.loads((song / 'out' / 'report.json').read_text())
            self.assertEqual(rep['warnings'], [])                        # the rest of the report is kept
            self.assertEqual(rep['ears']['realism'], res['files'][0]['realism'])
            self.assertEqual([s['name'] for s in rep['ears']['sections']], ['intro', 'verse', 'verse'])
            self.assertTrue(any('realism' in line for line in ears.summary_lines(res)))

    def test_worker_error_response_raises(self):
        with tempfile.TemporaryDirectory() as td:
            worker = pathlib.Path(td) / 'bad.py'
            worker.write_text("import json,sys; json.dump({'ok': False, 'error': 'boom'}, open(sys.argv[2], 'w'))")
            with mock.patch.object(ears, 'WORKER', worker):
                with self.assertRaisesRegex(ears.EarsError, 'boom'):
                    ears.run_worker({'files': []}, py=pathlib.Path(sys.executable))

    def test_worker_needs_no_agentsound_import(self):
        src = ears.WORKER.read_text(encoding='utf-8')
        self.assertNotIn('import agentsound', src)
        self.assertNotIn('from agentsound', src)
        self.assertNotIn('from .', src)


@unittest.skipUnless(os.environ.get(ears.ENV_PYTHON), f'set {ears.ENV_PYTHON} to the ears venv to run the models')
class RealModels(unittest.TestCase):
    def test_real_models(self):
        from agentsound.cli import find_ffmpeg
        ff = find_ffmpeg()
        if not ff:
            self.skipTest('no ffmpeg')
        with tempfile.TemporaryDirectory() as td:
            wav = pathlib.Path(td) / 'tone.wav'
            import math
            import struct
            import wave
            with wave.open(str(wav), 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(48000)
                w.writeframes(b''.join(struct.pack('<h', int(8000 * math.sin(2 * math.pi * 440 * i / 48000)))
                                       for i in range(48000 * 3)))
            res = ears.run([str(wav)], ffmpeg=ff, instrument='piano', max_windows=1)
            row = res['files'][0]
            self.assertEqual(set(row['aesthetics']), {'PQ', 'PC', 'CE', 'CU'})
            self.assertTrue(0.0 <= row['clap']['pReal'] <= 1.0)
            self.assertTrue(0.0 <= row['realism'] <= 100.0)


if __name__ == '__main__':
    unittest.main()
