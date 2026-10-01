"""The sampled drum / percussion library (agentsound/patches/sampled_drums.py): every patch registers with its notes
and level; each one whose sample pack is installed compiles to valid render JSON (GM keys sound); with no packs
installed (AGENTSOUND_SAMPLES pointing to an empty folder) the pack tests skip cleanly. Also the keymap= option of
inst.sfz / inst.kit the kits use for GM re-mapping."""

import copy
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentsound import library, patches  # noqa: E402
from agentsound.patches import _apply_keymap, _keymap, inst  # noqa: E402
from agentsound.patches import sampled_drums  # noqa: E402
from agentsound.song import Song  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

NAMES = [f'sampled/{k}' for k in sampled_drums.LEVELS]
# keys to play per patch (default 36 38 42: kick, snare, closed hat)
KEYS = {'tr727': [60, 63, 70], 'phat_hat': [42, 44, 46], 'frankensnare': [38], 'world_percussion': [60, 63, 82],
        'cymbals': [42, 49, 51], 'radio_ready_perc': [36, 60, 82], 'cajon': [36, 38, 40], 'bobobo': [36, 38, 45]}


def _packs(p) -> set[str]:
    """Sample pack ids a patch reads (from its lazy instrument spec)."""
    spec = p.instrument.lazy or {}
    paths = []
    if 'programs' in spec:
        paths = [v['path'] if isinstance(v, dict) else v for v in spec['programs'].values()]
    else:
        src = spec.get('path', spec.get('source'))
        paths = list(src) if isinstance(src, (list, tuple)) else [src]
    return {str(x).replace('\\', '/').split('/')[1] for x in paths if str(x).startswith('samples/')}


def _installed(pack: str) -> bool:
    return (library.SAMPLES / pack / 'SOURCE.json').is_file()


class Registry(unittest.TestCase):
    def test_every_patch_registers_with_notes_and_level(self):
        have = set(patches.list('sampled/'))
        for name in NAMES:
            with self.subTest(patch=name):
                self.assertIn(name, have)
                p = patches.get(name)
                self.assertEqual(p.instrument.type, 'sampler')
                self.assertIsNotNone(p.instrument.lazy, 'library patches read their samples lazily')
                self.assertIn('Measured -18.0 LUFS', p.notes)
                self.assertTrue(p.notes.startswith('v1.'), p.notes[:40])
                self.assertEqual(p.audition, {'notes': 'drums'})
                self.assertTrue(p.fx and p.fx[0].type == 'eq', 'a clean-up EQ first')
                self.assertTrue(_packs(p), 'reads a sample pack')
                self.assertEqual(p.instrument.params.get('level'), sampled_drums.LEVELS[name.split('/')[1]])

    def test_licence_flags_in_notes(self):
        for name in NAMES:
            notes = patches.get(name).notes.lower()
            with self.subTest(patch=name):
                self.assertTrue(any(w in notes for w in ('cc0', 'cc-by', 'licen', 'freeware')), 'licence named')
        self.assertIn('nc-sa', patches.get('sampled/mf_natural_kit').notes.lower())
        self.assertIn('no redistribution', patches.get('sampled/pettinhouse_brushes').notes.lower())
        self.assertIn('unclear', patches.get('sampled/tr606').notes.lower())


class Keymap(unittest.TestCase):
    ZONES = [{'lo': 45, 'hi': 45, 'root': 45, 'file': 'tom.wav'}, {'lo': 50, 'hi': 50, 'root': 50, 'file': 'choke.wav'},
             {'lo': 30, 'hi': 60, 'root': 40, 'file': 'wide.wav'}]

    def test_copies_moves_and_clears_keys(self):
        km = _keymap({50: 45, 'E6': 50, 45: None})
        self.assertEqual(km, {'50': 45, '88': 50, '45': None})
        out = _apply_keymap(copy.deepcopy(self.ZONES), km)
        by = {(z['lo'], z['file']) for z in out}
        self.assertIn((50, 'tom.wav'), by)          # the tom now also sounds on 50 ...
        self.assertIn((88, 'choke.wav'), by)        # ... the choke moved to 88
        self.assertNotIn((45, 'tom.wav'), by)       # 45 cleared
        self.assertNotIn((50, 'choke.wav'), by)
        self.assertIn((30, 'wide.wav'), by)         # ranged zones are left alone
        tom50 = next(z for z in out if z['lo'] == 50)
        self.assertEqual(tom50['root'], 50)         # the root moves with the key: same pitch

    def test_validation(self):
        for bad in ([1, 2], {128: 36}, {36: -1}, {36.5: 36}):
            with self.subTest(keymap=bad), self.assertRaises(ComposeError):
                _keymap(bad)

    def test_lazy_spec_carries_the_keymap(self):
        i = inst.sfz('samples/none/x.sfz', lazy=True, keymap={48: 47})
        self.assertEqual(i.lazy['keymap'], {'48': 47})
        k = inst.kit('samples/none', lazy=True, keymap={48: None})
        self.assertEqual(k.lazy['keymap'], {'48': None})
        self.assertEqual(i.but(level=2).lazy['keymap'], {'48': 47})   # survives copies


class InstalledPacks(unittest.TestCase):
    """Compile every patch whose pack is installed: zones load, the GM keys it plays have zones, the render JSON is
    well-formed. Skipped when no pack is installed (e.g. AGENTSOUND_SAMPLES=<empty dir>)."""

    def test_every_installed_patch_compiles(self):
        seen = 0
        for name in NAMES:
            p = patches.get(name)
            if not all(_installed(k) for k in _packs(p)):
                continue
            seen += 1
            with self.subTest(patch=name):
                s = Song('drums test', tempo=110, key='A minor', seed=1)
                s.section('a', bars=1)
                t = s.track('kit', p)
                keys = KEYS.get(name.split('/')[1], [36, 38, 42])
                for i, k in enumerate(keys):
                    t.note(k, i * 0.5, 0.25, vel=100)
                render = s.compile()
                tr = render['tracks'][0]
                self.assertEqual(tr['instrument']['type'], 'sampler')
                zones = tr['instrument']['params']['samples']
                self.assertTrue(zones, 'zones loaded')
                for k in keys:
                    self.assertTrue(any(z.get('lo', 0) <= k <= z.get('hi', 127) for z in zones), f'key {k} sounds')
                self.assertEqual(len(tr['notes']), len(keys))
        if not seen:
            self.skipTest('no drum sample packs installed')


if __name__ == '__main__':
    unittest.main()
