import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentsound import catalog, library


def _wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'RIFF\x00\x00\x00\x00WAVE')   # the index only looks at names


class TestCatalog(unittest.TestCase):
    def test_every_engine_module_has_a_description(self):
        mods = catalog.engine_modules()
        if not mods:
            self.skipTest('engine not built')
        self.assertEqual(sorted(mods), sorted(catalog.MODULES), 'catalog.MODULES must describe exactly the engine types')

    def test_overview_and_search_run(self):
        text = catalog.overview(list(catalog.SECTIONS))
        for head in ('Patches', 'Recipes', 'Python helpers'):
            self.assertIn(head, text)
        self.assertIn('synthwave/juno_pad', catalog.search(['juno', 'pad'], only='patches'))
        self.assertIn('nothing found', catalog.search(['zzzqqqxx']))
        found = catalog.search(['drummer', 'fill'])
        self.assertIn('drummer.tom_run', found)
        self.assertIn('drummer', catalog.helpers())

    def test_index_pack_detects_mappings(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            for n in ('kick', 'snare', 'hat', 'ohh'):
                _wav(tmp / 'kit' / f'{n}.wav')
            for n in ('C3', 'F#3', 'C4'):
                _wav(tmp / 'keys' / f'{n}.wav')
            for n in ('Piano C4 v1', 'Piano C4 v2', 'Piano E4 v1', 'Piano E4 v2'):
                _wav(tmp / 'piano' / f'{n}.wav')
            (tmp / 'piano' / 'piano.sfz').write_text('<region> sample=x.wav')
            idx = catalog.index_pack(tmp)
            by_dir = {f['dir']: f for f in idx['folders']}
            self.assertEqual(by_dir['kit']['mapping'], 'gm-drum-names')
            self.assertEqual(by_dir['keys']['mapping'], 'note-names')
            self.assertEqual(by_dir['keys']['notes'], [48, 60, 3])
            self.assertEqual(by_dir['piano']['mapping'], 'custom')
            self.assertEqual(by_dir['piano']['velocityLayers'], 2)
            self.assertEqual(idx['sfz'], ['piano/piano.sfz'])
            self.assertEqual(idx['audioFiles'], 11)
        finally:
            shutil.rmtree(tmp)


class TestLibraryManifest(unittest.TestCase):
    def _load(self, packs):
        tmp = Path(tempfile.mkdtemp())
        try:
            f = tmp / 'manifest.json'
            f.write_text(json.dumps({'packs': packs}))
            return library.load_manifest(f)
        finally:
            shutil.rmtree(tmp)

    def _pack(self, **kw):
        p = {'id': 'x', 'title': 'X', 'url': 'https://example.org/x.zip', 'license': 'CC0-1.0',
             'licenseUrl': 'https://creativecommons.org/publicdomain/zero/1.0/'}
        p.update(kw)
        return p

    def test_valid_manifest(self):
        packs = self._load([self._pack(), self._pack(id='y', url='https://example.org/y.tar.xz')])
        self.assertEqual(library.archive_kind(packs[0]), 'zip')
        self.assertEqual(library.archive_kind(packs[1]), 'tar')
        self.assertEqual(library.archive_kind(self._pack(url='https://e.org/FluidR3_GM.sf2')), 'file')

    def test_strict_manifest(self):
        with self.assertRaisesRegex(library.LibraryError, 'unknown keys'):
            self._load([self._pack(colour='red')])
        with self.assertRaisesRegex(library.LibraryError, 'duplicate'):
            self._load([self._pack(), self._pack()])
        with self.assertRaisesRegex(library.LibraryError, 'missing'):
            self._load([{'id': 'x'}])

    def test_repo_manifest_is_valid(self):
        # the versioned manifest of the repo (library.MANIFEST follows $AGENTSOUND_SAMPLES, which may be any folder)
        library.load_manifest(library.REPO / 'assets' / 'samples' / 'manifest.json')

    def test_archive_members_cannot_escape(self):
        with self.assertRaises(library.LibraryError):
            library._check_members({'id': 'x'}, ['ok.wav', '../evil.wav'])


if __name__ == '__main__':
    unittest.main()
