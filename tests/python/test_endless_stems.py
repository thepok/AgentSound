"""Optional stem delivery uses the normal renderer, without changing the mix."""
import json
import io
import pathlib
import sys
import tempfile
import unittest
import wave
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from agentsound import Song, inst, fx
from agentsound import cli
from agentsound.endless import composer, genres, run


class Stems(unittest.TestCase):
    def test_opt_in_parser(self):
        self.assertFalse(cli.build_parser().parse_args(['endless', 'orchestra']).stems)
        self.assertTrue(cli.build_parser().parse_args(['endless', 'orchestra', '--stems']).stems)

    def test_real_render_delivery_and_unchanged_mix(self):
        try:
            engine = cli.find_engine(None)
        except cli.CliError as e:
            self.skipTest(str(e))
        genre = genres.get('orchestra-symphonic')
        tune = composer.compose(genre, 100)
        song = Song('Stem fixture', tempo=120, key='C major', seed=100)
        section = song.section('fixture', bars=1)
        hall = song.hall()
        song.track('violins1', inst.va(), gain_db=-18, sends={hall: -12}).play(
            song.motif('1:1/4 r:1/4 5:1/4 r:1/4').clip(octave=4), section)
        song.track('oboe_solo', inst.va(), gain_db=-20, pan=.3).play(
            song.motif('r:1/4 3:1/4 r:1/4 8:1/4').clip(octave=5), section)
        song.master.add(fx.limiter())
        made = dict(tune=tune, song=song, seed=100, plan=None,
                    score=dict(score=50, style='symphony', hard=[], worst=[], parts={}))
        mixes = []

        def deliver(song, render, engine, out, *_args, **_kwargs):
            mixes.append((out / 'mix.wav').read_bytes())
            (out / 'mix.mp3').write_bytes(b'fixture')
            return []

        with tempfile.TemporaryDirectory() as root, patch.object(run, 'gate', return_value=[]), \
                patch.object(cli, 'deliver_render', side_effect=deliver):
            for index, enabled in enumerate((False, True), 1):
                args = cli.build_parser().parse_args(['endless', 'orchestra', '--engine', str(engine)] +
                                                     (['--stems'] if enabled else []))
                info = run.render_tune(genre, 100, pathlib.Path(root), index, args, lambda _: None, made=made)
                folder = pathlib.Path(info['files']['mp3']).parent
                self.assertFalse((folder / 'mix.wav').exists())
                self.assertFalse((folder / 'song.render.json').exists())
                saved = json.loads((folder / 'tune.json').read_text(encoding='utf-8'))
                if enabled:
                    stems = saved['files']['stems']
                    self.assertEqual(set(stems['tracks']), {'violins1', 'oboe_solo'})
                    self.assertEqual(set(stems['buses']), set(song.buses))
                    frames = []
                    for paths in stems.values():
                        for name, path in paths.items():
                            self.assertEqual(pathlib.Path(path).name, name + '.wav')
                            self.assertEqual(pathlib.Path(path).parent, folder / 'stems')
                            with wave.open(path, 'rb') as wav:
                                frames.append((wav.getnframes(), wav.getframerate(), wav.getnchannels()))
                    self.assertGreater(frames[0][0], 0)
                    self.assertEqual(len(set(frames)), 1)
                    with wave.open(io.BytesIO(mixes[-1]), 'rb') as mix:
                        report = json.loads((folder / 'report.json').read_text(encoding='utf-8'))
                        latency = report['render']['latencySamples']
                        self.assertGreater(latency, 0)
                        self.assertEqual(frames[0], (mix.getnframes() + latency,
                                                    mix.getframerate(), mix.getnchannels()))
                else:
                    self.assertNotIn('stems', saved['files'])
                    self.assertFalse((folder / 'stems').exists())
        self.assertEqual(mixes[0], mixes[1])
        self.assertFalse(song.stems)  # export choice doesn't mutate the composed Song


if __name__ == '__main__':
    unittest.main()
