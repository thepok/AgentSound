import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentsound import library, patches
from agentsound.patches import FX, fx
from agentsound.patches import space_ir
from agentsound.theory import ComposeError


class TestIrPaths(unittest.TestCase):
    def test_sample_paths_become_absolute_in_the_library(self):
        # 'samples/...' stays symbolic in the patch and resolves in the render JSON (the folder in effect then)
        f = fx.convolver(ir='samples/some-pack/Hall.wav', mix=1)
        self.assertEqual(f.params['ir'], 'samples/some-pack/Hall.wav')
        self.assertEqual(f.to_dict()['params']['ir'], (library.SAMPLES / 'some-pack/Hall.wav').as_posix())
        self.assertTrue(os.path.isabs(f.to_dict()['params']['ir']))
        two = fx.convolver(ir=['samples/p/a.L.wav', 'samples/p/a.R.wav'])
        self.assertEqual(two.to_dict()['params']['ir'],
                         [(library.SAMPLES / 'p/a.L.wav').as_posix(), (library.SAMPLES / 'p/a.R.wav').as_posix()])
        self.assertEqual(f.but(ir='samples/q/x.wav').to_dict()['params']['ir'], (library.SAMPLES / 'q/x.wav').as_posix())
        self.assertEqual(f.copy(), f)                        # resolving an absolute path again changes nothing
        self.assertEqual(FX.coerce(f.to_dict()).to_dict()['params']['ir'], f.to_dict()['params']['ir'])

    def test_other_paths(self):
        self.assertEqual(fx.convolver(ir='ir/room.wav').params['ir'], 'ir/room.wav')   # relative to assets/: the engine's job
        absolute = str(Path(tempfile.gettempdir()) / 'x.wav')
        self.assertEqual(fx.convolver(ir=absolute).params['ir'], absolute.replace(os.sep, '/'))
        here = Path(__file__).resolve().parent
        self.assertEqual(Path(fx.convolver(ir='./my_room.wav').params['ir']), here / 'my_room.wav')  # next to the song

    def test_bad_values(self):
        for bad in (3, [], [1, 2], True, ['a.wav', 'b.wav', 'c.wav'], ['a.wav'] * 5):
            with self.assertRaises(ComposeError):
                fx.convolver(ir=bad)
        self.assertEqual(len(fx.convolver(ir=('samples/p/a.wav', 'samples/p/b.wav')).params['ir']), 2)  # a tuple is a list


class TestSpaceIrPatches(unittest.TestCase):
    def test_library(self):
        returns = patches.list('bus/ir_')
        for name in ('bus/ir_hall', 'bus/ir_plate', 'bus/ir_chamber', 'bus/ir_room', 'bus/ir_inverse'):
            self.assertIn(name, returns)
        for name in returns:
            p = patches.get(name)
            conv = [f for f in p.fx if f.type == 'convolver']
            self.assertEqual(len(conv), 1, name)
            self.assertEqual(conv[0].params['mix'], 1.0, name)
            ir = conv[0].to_dict()['params']['ir']
            files = ir if isinstance(ir, list) else [ir]
            self.assertIn(len(files), (1, 4), name)                         # 224XL: true stereo in 4 files
            self.assertTrue(all(os.path.isabs(x) for x in files), name)
            self.assertRegex(p.notes, r'^v\d', name)
            installed = all(os.path.isfile(x) for x in files)
            self.assertEqual('NOT INSTALLED' not in p.notes, installed, name)   # the catalog says which ones render
        cabs = patches.list('cab/')
        self.assertGreaterEqual(len(cabs), 5)
        for name in cabs:
            self.assertEqual([f.type for f in patches.get(name).fx], ['amp', 'convolver', 'eq'], name)

    def test_224xl_file_order_and_missing_packs(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            pack = tmp / 'little-devil-test'
            pack.mkdir()
            (pack / 'SOURCE.json').write_text('{}')
            for v in (1, 2):
                for i in (1, 2):
                    for o in 'LR':
                        (pack / f'Plate V{v}.{i}-01.{o}.wav').write_bytes(b'RIFF')
            with mock.patch.object(library, 'SAMPLES', tmp):
                files = space_ir._xl('little-devil-test', 2)
                self.assertEqual([Path(f).name for f in files],
                                 ['Plate V2.1-01.L.wav', 'Plate V2.1-01.R.wav', 'Plate V2.2-01.L.wav', 'Plate V2.2-01.R.wav'])
                self.assertTrue(all(f.startswith('samples/little-devil-test/') for f in files))
                missing = space_ir._xl('not-installed-pack')          # keeps the pattern: the render names the pack
                self.assertEqual(missing[0], 'samples/not-installed-pack/* V1.1*.L.wav')
                self.assertEqual(space_ir._pack_note(files), '')
                self.assertIn("NOT INSTALLED: pack 'not-installed-pack'", space_ir._pack_note(missing))
                note = space_ir._with_pack_note('v1 (gain estimated). A hall.', missing)
                self.assertTrue(note.startswith("v1 (gain estimated) [NOT INSTALLED: pack 'not-installed-pack'"), note)
                self.assertTrue(note.endswith('. A hall.'), note)
                # archives that unpack into a folder of their own: found below the pack root too
                sub = tmp / 'nested-pack' / 'Impulses' / '48k'
                sub.mkdir(parents=True)
                (tmp / 'nested-pack' / 'SOURCE.json').write_text('{}')
                (sub / 'Cab 1.wav').write_bytes(b'RIFF')
                self.assertEqual(space_ir._files('nested-pack', 'Cab 1.wav'), 'samples/nested-pack/Impulses/48k/Cab 1.wav')
        finally:
            shutil.rmtree(tmp)


if __name__ == '__main__':
    unittest.main()
