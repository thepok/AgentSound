"""The sampled guitars and basses (agentsound/patches/sampled_guitars.py) and the sfz_multi program options they use
('zone' overrides, 'keygain'). The library imports without samples; the patches compile to render JSON when their
packs are installed ($AGENTSOUND_SAMPLES or assets/samples) and are skipped cleanly when they are not (run the suite
with AGENTSOUND_SAMPLES pointing to an empty folder to see the skips)."""

import json
import math
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Song, cli, library, patches  # noqa: E402
from agentsound import articulation as art  # noqa: E402
from agentsound.patches import inst  # noqa: E402
from agentsound.patches import sampled_guitars as guitars  # noqa: E402
from agentsound.song import dumps  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

NAMES = ('steel_guitar', 'concert_guitar', 'archtop_guitar', 'jazz_guitar', 'clean_guitar', 'dist_guitar',
         'fuzz_guitar', 'gretsch_guitar', 'hofner_guitar', 'rock_guitar', 'crunch_guitar', 'metal_guitar',
         'blues_guitar', 'jangle_guitar', 'lead_guitar', 'archtop_electric', 'metal_rhythm', 'metal_lead',
         'finger_bass', 'rock_bass', 'round_bass', 'slap_bass', 'flatwound_bass', 'picked_bass', 'hollow_bass',
         'bass_vi', 'short_scale_bass', 'sneaky_bass', 'electric_upright')

# a note each patch can play (inside its range) and the articulations it must offer
PLAY = {n: 'E2' if 'guitar' in n or n == 'metal_rhythm' else 'A1' for n in NAMES}
PLAY.update({'metal_lead': 'E4', 'lead_guitar': 'E4', 'concert_guitar': 'A2'})
ARTS = {'rock_guitar': ['open', 'palm mute', 'dead note'], 'gretsch_guitar': ['twang', 'staccato', 'hammer-on',
                                                                            'palm mute'],
        'hofner_guitar': ['twang', 'staccato', 'behind the bridge', 'palm mute'],
        'finger_bass': ['sustain', 'staccato', 'mute'], 'picked_bass': ['pluck', 'staccato', 'ghost',
                                                                        'behind the bridge'],
        'electric_upright': ['pizz', 'arco'], 'bass_vi': ['picked', 'muted', 'fingered', 'roundwound'],
        'sneaky_bass': ['pluck', 'ghost', 'mute', 'fingering noise'], 'metal_rhythm': ['open', 'palm mute'],
        'archtop_guitar': ['open', 'muted']}


def _packs(p) -> set:
    """The sample packs a patch needs: its instrument's files and its effects' impulse responses."""
    out = set()

    def add(path):
        if not isinstance(path, str):
            return
        text = path.replace('\\', '/')
        if text.startswith('samples/'):
            out.add(text.split('/')[1])
        else:
            root = library.SAMPLES.as_posix().rstrip('/') + '/'
            if text.startswith(root):
                out.add(text[len(root):].split('/')[0])

    ins = p.instrument
    spec = ins.lazy or {}
    add(spec.get('path'))
    add(spec.get('source'))
    for prog in (spec.get('programs') or {}).values():
        add(prog['path'] if isinstance(prog, dict) else prog)
    for z in spec.get('zones') or []:
        add(z['file'])
    samples = ins.params.get('samples')
    for z in samples if isinstance(samples, list) else []:
        add(z.get('file'))
    for f in p.fx:
        ir = f.params.get('ir')
        for x in ir if isinstance(ir, list) else [ir]:
            add(x)
    return out


def _installed(pack: str) -> bool:
    return (library.SAMPLES / pack / 'SOURCE.json').is_file()


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


class Library(unittest.TestCase):
    """Always runs: the module needs no samples to import and register."""

    def test_every_patch_registers(self):
        have = set(patches.list('sampled/'))
        for n in NAMES:
            with self.subTest(patch=n):
                self.assertIn(f'sampled/{n}', have)
                p = patches.get(f'sampled/{n}')
                self.assertEqual(p.instrument.type, 'sampler')
                self.assertIn('Measured -18.0 LUFS', p.notes)
                self.assertTrue(p.notes.startswith('v1. '), p.notes[:40])
                self.assertTrue(p.sends)
                self.assertTrue(_packs(p), 'no sample pack found for the patch')
                self.assertIn(n, guitars.LEVELS)

    def test_lazy_without_samples(self):
        """Importing reads no sample file: every patch is lazy (metal_rhythm: explicit zones looked up at render)."""
        for n in NAMES:
            p = patches.get(f'sampled/{n}')
            with self.subTest(patch=n):
                self.assertIsNotNone(p.instrument.lazy)
                self.assertNotIn('samples', p.instrument.params)
        p = patches.get('sampled/metal_rhythm')
        self.assertEqual(len(p.instrument.lazy['zones']), 40)
        self.assertEqual(p.instrument.info['sfz']['keyswitches'], {'open': 0, 'palm mute': 1})

    def test_amped_patches_trim_their_output(self):
        """The DI + amp patches keep their amp input level (the drive) and calibrate with a final 'trim'."""
        for n in ('rock_guitar', 'crunch_guitar', 'metal_guitar', 'blues_guitar', 'jangle_guitar', 'lead_guitar',
                  'archtop_electric'):
            p = patches.get(f'sampled/{n}')
            with self.subTest(patch=n):
                self.assertEqual(p.fx[-1].name, 'trim')
                self.assertEqual(p.fx[-1].params['gain'], guitars.LEVELS[n])
                self.assertIn('convolver', [f.type for f in p.fx])
                self.assertIn(p.instrument.params['level'], guitars.DI_LEVEL.values())

    def test_catalog_lists_them(self):
        from agentsound import catalog
        text = catalog.overview(['patches'])
        line = next(x for x in text.splitlines() if x.strip().startswith('sampled/'))
        for n in NAMES:
            self.assertIn(f' {n},' if n != NAMES[-1] else f' {n}', line.replace(':', ',') + ',')
        found = catalog.search(['palm'], only='patches', limit=200)
        for n in ('sampled/rock_guitar', 'sampled/metal_rhythm'):
            self.assertIn(n, found)


class InstalledPacks(unittest.TestCase):
    """Each patch whose packs are installed compiles to a valid render JSON (and passes the engine's validation
    when the engine is built); a patch whose pack is missing is skipped - or, for the lazy ones, fails at use with
    the pack named."""

    def test_patches_compile(self):
        compiled = []
        s = Song('guitars', tempo=100, key='E minor', seed=1)
        a = s.section('a', bars=2)
        for n in NAMES:
            p = patches.get(f'sampled/{n}')
            missing = sorted(x for x in _packs(p) if not _installed(x))
            with self.subTest(patch=n):
                if missing:
                    if missing[0] in str(p.instrument.lazy):
                        s2 = Song('missing', tempo=100)
                        s2.section('a', bars=1)
                        s2.track('t', p.with_mix(sends={k: None for k in p.sends})).note(PLAY[n], 0, 1)
                        with self.assertRaises(ComposeError) as cm:
                            s2.compile()
                        self.assertIn(missing[0], str(cm.exception))
                    continue
                t = s.track(n, p.with_mix(sends={k: None for k in p.sends}))
                t.note(PLAY[n], a.start, 1, vel=100)
                for i, name in enumerate(ARTS.get(n, [])[1:]):
                    t.note(PLAY[n], 2 + i * 0.5, 0.25, vel=90, art=name.split()[0])
                if n in ARTS:
                    self.assertEqual(sorted(art.available(p)), sorted(ARTS[n]))
                compiled.append(n)
        if compiled:
            d = s.compile()
            for tr in d['tracks']:
                with self.subTest(patch=tr['id']):
                    zones = tr['instrument']['params']['samples']
                    self.assertTrue(zones)
                    for z in zones:
                        self.assertTrue(os.path.isfile(z['file']) or z['file'].startswith('*'), z['file'])
                    if tr['id'] in ARTS:
                        self.assertGreater(len({z.get('swLast') for z in zones}), 1)
            json.loads(dumps(d))
            eng = _engine()
            if eng is not None:
                tmp = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_gtr_'))
                self.addCleanup(shutil.rmtree, tmp, True)
                (tmp / 'r.json').write_text(dumps(d), encoding='utf-8')
                proc = subprocess.run([str(eng), 'validate', str(tmp / 'r.json')], capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
        if not compiled:
            self.skipTest(f'no guitar / bass pack installed in {library.SAMPLES}')


def _wav(path: pathlib.Path, hz: float, sr: int = 48000, seconds: float = 0.2):
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(sr * seconds)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b''.join(struct.pack('<h', int(12000 * math.sin(2 * math.pi * hz * i / sr))) for i in range(n)))


class MultiOptions(unittest.TestCase):
    """sfz_multi program options 'zone' (articulations made from the same samples) and 'keygain' (even out notes)."""

    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_multi_'))
        self.addCleanup(shutil.rmtree, self.dir, True)
        _wav(self.dir / 'lo.wav', 110.0)
        _wav(self.dir / 'hi.wav', 440.0)
        _wav(self.dir / 'rel.wav', 1000.0)
        self.path = self.dir / 'g.sfz'
        self.path.write_text('<region> sample=lo.wav lokey=40 hikey=56 pitch_keycenter=45\n'
                             '<region> sample=hi.wav lokey=57 hikey=80 pitch_keycenter=69\n'
                             '<region> sample=rel.wav lokey=40 hikey=80 trigger=release\n', encoding='utf-8')

    def test_zone_overrides_attack_zones_only(self):
        ins = inst.sfz_multi({'open': str(self.path),
                              'palm': {'path': str(self.path), 'zone': guitars.PALM, 'gain': 2.0}})
        zones = ins.params['samples']
        palm = [z for z in zones if z['swLast'] == 1]
        self.assertEqual(len(palm), 3)
        for z in palm:
            if z.get('trigger') == 'release':
                self.assertNotIn('filter', z)
            else:
                self.assertEqual((z['filter'], z['cutoff'], z['sustain']), ('lpf_2p', 1600.0, 0.0))
            self.assertEqual(z['gain'], 2.0)
        self.assertFalse(any('filter' in z for z in zones if z['swLast'] == 0))
        for bad in ({'lo': 3}, {'gain': 3}, {'trigger': 'release'}, ['cutoff']):
            with self.subTest(bad=bad), self.assertRaises(ComposeError):
                inst.sfz_multi({'a': {'path': str(self.path), 'zone': bad}})

    def test_lazy_sampler_zones(self):
        """inst.sampler(zones=..., lazy=True): nothing is looked up until the render JSON is built; a missing file is
        a ComposeError then."""
        ins = inst.sampler(zones=[{'file': str(self.dir / 'lo.wav'), 'root': 'A2', 'swLast': 0}], lazy=True, level=-3)
        self.assertEqual(ins.lazy['kind'], 'zones')
        self.assertNotIn('samples', ins.params)
        d = ins.to_dict()
        self.assertEqual(d['params']['samples'][0]['root'], 45)
        self.assertEqual(d['params']['level'], -3)
        gone = inst.sampler(zones=[{'file': 'samples/no-such-pack/x.wav'}], lazy=True)
        with self.assertRaisesRegex(ComposeError, 'samples fetch no-such-pack'):
            gone.to_dict()
        with self.assertRaises(ComposeError):
            inst.sampler(file=str(self.dir / 'lo.wav'), lazy=True)

    def test_keygain(self):
        ins = inst.sfz_multi({'a': {'path': str(self.path), 'keygain': [[45, 0.0], [69, 6.0]]}})
        by_root = {z['root']: z.get('gain', 0.0) for z in ins.params['samples'] if z.get('trigger') != 'release'}
        self.assertEqual(by_root, {45: 0.0, 69: 6.0})
        mid = inst.sfz_multi({'a': {'path': str(self.path), 'keygain': [[33, 0.0], [81, 12.0]]}})
        g = {z['root']: z.get('gain', 0.0) for z in mid.params['samples'] if z.get('trigger') != 'release'}
        self.assertAlmostEqual(g[45], 3.0)
        self.assertAlmostEqual(g[69], 9.0)
        for bad in ([[60, 0], [50, 3]], [[60, 99]], 'x', [[60]]):
            with self.subTest(bad=bad), self.assertRaises(ComposeError):
                inst.sfz_multi({'a': {'path': str(self.path), 'keygain': bad}})


if __name__ == '__main__':
    unittest.main()
