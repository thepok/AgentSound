import contextlib
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Song, cli, patches
from agentsound.patches import Instrument, Patch, inst
from agentsound.theory import ComposeError

HERE = pathlib.Path(__file__).resolve().parent


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


class Sf2Constructor(unittest.TestCase):
    def test_by_name_and_numbers(self):
        self.assertEqual(inst.sf2('Grand Piano').to_dict(), {'type': 'sf2', 'params': {'preset': 'Grand Piano'}})
        self.assertEqual(inst.sf2(bank=0, program=48).params, {'bank': 0, 'program': 48})
        self.assertEqual(inst.sf2(program=48).params, {'bank': 0, 'program': 48})
        self.assertEqual(inst.sf2(bank=128, program=25).params, {'bank': 128, 'program': 25})
        self.assertEqual(inst.sf2('0:48').params, {'preset': '0:48'})
        self.assertEqual(inst.sf2('Warm Pad', level=-3, width=1.2).params, {'preset': 'Warm Pad', 'level': -3, 'width': 1.2})
        self.assertEqual(inst.sf2('Pad', file='My.sf2').params['file'], 'My.sf2')
        local = inst.sf2('Pad', file='./fonts/x.sf2').params['file']
        self.assertEqual(local, (HERE / 'fonts' / 'x.sf2').as_posix())

    def test_errors(self):
        with self.assertRaises(ComposeError):
            inst.sf2('Grand Piano', program=3)
        with self.assertRaises(ComposeError):
            inst.sf2(bank=8)
        with self.assertRaises(ComposeError):
            inst.sf2('  ')
        with self.assertRaises(ComposeError):
            inst.sf2('Piano', file='')


class SamplerConstructor(unittest.TestCase):
    def test_dir(self):
        self.assertEqual(inst.sampler(dir='samples/909').to_dict(),
                         {'type': 'sampler', 'params': {'samples': {'dir': 'samples/909'}}})
        i = inst.sampler(dir='samples/909', oneshot='on', level=-6, loop='none')
        self.assertEqual(i.params, {'samples': {'dir': 'samples/909', 'loop': 'none'}, 'oneshot': 'on', 'level': -6})

    def test_local_paths(self):
        self.assertEqual(inst.sampler(dir='./kit').params['samples']['dir'], (HERE / 'kit').as_posix())
        self.assertEqual(inst.sampler(dir='../kit').params['samples']['dir'], (HERE.parent / 'kit').as_posix())
        absolute = (HERE / 'abs.wav').as_posix()
        self.assertEqual(inst.sampler(file=absolute).params['samples']['file'], absolute)
        self.assertEqual(inst.sampler(file=pathlib.Path('samples') / 'x.wav').params['samples']['file'], 'samples/x.wav')

    def test_file_and_zones(self):
        self.assertEqual(inst.sampler(file='samples/pad.wav', root='A3', loop='forward').params['samples'],
                         {'file': 'samples/pad.wav', 'root': 57, 'loop': 'forward'})
        z = inst.sampler(zones=[{'file': 'samples/p/C3.wav', 'root': 'C3', 'hi': 'F#3'},
                                {'file': 'samples/p/C4.wav', 'root': 60, 'lo': 'G3', 'vello': 90, 'gain': -2}])
        self.assertEqual(z.params['samples'], [{'file': 'samples/p/C3.wav', 'root': 48, 'hi': 54},
                                               {'file': 'samples/p/C4.wav', 'root': 60, 'lo': 55, 'vello': 90, 'gain': -2}])
        sf = inst.sampler(file='soundfonts/GeneralUser-GS.sf2', sample='Orchestra Hit-2', oneshot='on')
        self.assertEqual(sf.params['samples'], {'file': 'soundfonts/GeneralUser-GS.sf2', 'sample': 'Orchestra Hit-2'})

    def test_errors(self):
        with self.assertRaisesRegex(ComposeError, 'exactly one of'):
            inst.sampler()
        with self.assertRaisesRegex(ComposeError, 'exactly one of'):
            inst.sampler(dir='a', file='b.wav')
        with self.assertRaises(ComposeError):
            inst.sampler(dir='a', root=60)
        with self.assertRaises(ComposeError):
            inst.sampler(zones=[])
        with self.assertRaises(ComposeError):
            inst.sampler(zones=['x.wav'])
        with self.assertRaises(ComposeError):
            inst.sampler(zones=[{'root': 60}])
        with self.assertRaises(ComposeError):
            inst.sampler(zones=[{'file': 'a.wav'}], root=60)
        with self.assertRaises(ComposeError):
            inst.sampler(file='a.wav', root='H9')
        with self.assertRaises(ComposeError):
            Instrument('sampler', {'samples': {'dir': object()}})
        with self.assertRaises(ComposeError):
            Instrument('sampler', {'samples': [float('nan')]})
        with self.assertRaises(ComposeError):  # only 'samples' may be structured
            Instrument('sf2', {'preset': {'name': 'x'}})

    def test_structured_params_are_deep_copies(self):
        zones = [{'file': 'a.wav', 'root': 60}]
        p = Patch('test/sampler', inst.sampler(zones=zones))
        zones[0]['root'] = 1
        self.assertEqual(p.instrument.params['samples'][0]['root'], 60)
        q = p.but(level=-3)
        q.instrument.params['samples'][0]['root'] = 2
        self.assertEqual(p.instrument.params['samples'][0]['root'], 60)
        self.assertEqual(q.instrument.params['level'], -3)
        d = Instrument.coerce({'type': 'sampler', 'params': {'samples': {'dir': 'samples/kit'}}})
        self.assertEqual(d.params, {'samples': {'dir': 'samples/kit'}})
        self.assertEqual(p.but(samples={'dir': 'samples/other'}).instrument.params['samples'], {'dir': 'samples/other'})

    def test_song_compile(self):
        s = Song('Samples', tempo=100, key='C major')
        sec = s.section('a', bars=1)
        s.track('piano', inst.sf2('Grand Piano')).note('C4', sec, 2)
        s.track('hit', inst.sampler(file='soundfonts/GeneralUser-GS.sf2', sample='Orchestra Hit-2', oneshot='on')).note('C4', 0, 1)
        r = s.compile()
        tracks = {t['id']: t for t in r['tracks']}
        self.assertEqual(tracks['piano']['instrument'], {'type': 'sf2', 'params': {'preset': 'Grand Piano'}})
        self.assertEqual(tracks['hit']['instrument']['params']['samples'],
                         {'file': 'soundfonts/GeneralUser-GS.sf2', 'sample': 'Orchestra Hit-2'})
        from agentsound.song import dumps
        self.assertEqual(json.loads(dumps(r))['tracks'][1]['instrument']['params']['oneshot'], 'on')


class GmLibrary(unittest.TestCase):
    NAMES = ['gm/brass_section', 'gm/choir_aahs', 'gm/fretless', 'gm/grand_piano', 'gm/music_box', 'gm/nylon_guitar',
             'gm/orchestra_hit', 'gm/piano_lead', 'gm/strings', 'gm/synth_strings', 'gm/warm_pad']

    def test_registered_and_calibrated(self):
        self.assertEqual(patches.list('gm/'), self.NAMES)
        for n in self.NAMES:
            p = patches.get(n)
            self.assertEqual(p.instrument.type, 'sf2', n)
            self.assertIn('preset', p.instrument.params, n)
            self.assertIn('level', p.instrument.params, n)
            self.assertIn('Measured -18.0 LUFS', p.notes, n)

    def test_audition_songs_compile(self):
        for n in self.NAMES:
            song = cli.audition_song(n)
            r = song.compile()
            self.assertTrue(any(t['notes'] for t in r['tracks']), n)


class CliSf2(unittest.TestCase):
    def test_parser(self):
        args = cli.build_parser().parse_args(['sf2', 'grand', 'piano', '--json', '--samples', '--file', 'X.sf2'])
        self.assertEqual((args.search, args.json, args.samples, args.file), (['grand', 'piano'], True, True, 'X.sf2'))

    def test_missing_engine(self):
        code, out, err = run(['sf2', '--engine', str(HERE / 'missing.exe')])
        self.assertEqual(code, 3)
        self.assertIn('engine not found', err)


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


SONG = '''
from agentsound import *

def build():
    s = Song('Sample Test', tempo=96, key='A minor', seed=3)
    a = s.section('a', bars=2)
    s.hall()
    s.track('piano', 'gm/grand_piano').play(s.prog('i VI').block(), a)
    s.track('strings', 'gm/strings').play(s.prog('i VI').block(), a)
    s.track('hit', inst.sampler(file='soundfonts/GeneralUser-GS.sf2', sample='Orchestra Hit-2', oneshot='on',
                                level=-12), sends={'hall': -10}).note('A4', 0, 0.5).note('A4', 4, 0.5)
    s.master.add(fx.limiter())
    return s
'''


@unittest.skipIf(_engine() is None, 'engine not built (set AGENTSOUND_TEST_ENGINE or build build/agentsound.exe)')
class EngineIntegration(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_sampler_'))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_listings(self):
        code, out, err = run(['sf2', 'grand', 'piano', '--engine', str(_engine())])
        self.assertEqual(code, 0, err)
        self.assertIn('Grand Piano', out)
        self.assertIn('0:0', out)
        code, out, err = run(['sf2', '--json', 'kit', '--engine', str(_engine())])
        kits = json.loads(out)
        self.assertTrue(all(k['bank'] in (120, 128) for k in kits) and len(kits) >= 10)
        code, out, err = run(['sf2', '--samples', 'strloop - c3', '--engine', str(_engine())])
        self.assertEqual(code, 0, err)
        self.assertIn('StrLoop - C3', out)

    def test_build_song_with_samples(self):
        (self.dir / 'song').mkdir()
        (self.dir / 'song' / 'song.py').write_text(SONG, encoding='utf-8')
        code, out, err = run(['build', str(self.dir / 'song'), '--no-mp3', '--engine', str(_engine())])
        self.assertEqual(code, 0, err + out)
        report = json.loads((self.dir / 'song' / 'out' / 'report.json').read_text(encoding='utf-8'))
        nodes = {n['id']: n for n in report['nodes']}
        for t in ('piano', 'strings', 'hit', 'hall'):
            self.assertGreater(nodes[t]['lufs'], -40.0, t)
        self.assertEqual(report['clicks'], [])

    def test_check_rejects_unknown_preset(self):
        (self.dir / 'bad').mkdir()
        (self.dir / 'bad' / 'song.py').write_text(SONG.replace("'gm/grand_piano'", "inst.sf2('Grand Pinao')"), encoding='utf-8')
        code, out, err = run(['check', str(self.dir / 'bad'), '--engine', str(_engine())])
        self.assertEqual(code, 2)
        self.assertIn('did you mean "Grand Piano"', err)
        self.assertIn("(track 'piano')", err)


if __name__ == '__main__':
    unittest.main()
