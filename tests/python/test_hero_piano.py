"""The hero pianos (agentsound/patches/hero_piano.py): every patch registers without the samples, is a key-split stack of
lazy Salamander layers (+ strings), carries the house notes and calibration, carve() applies the mix rules; with the
packs installed ($AGENTSOUND_SAMPLES or assets/samples) the patches compile to render JSON the engine accepts.
Patches whose packs are missing are skipped (an empty $AGENTSOUND_SAMPLES skips them all)."""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Song, cli, library, patches  # noqa: E402
from agentsound.patches import hero_piano  # noqa: E402
from agentsound.song import dumps  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

PATCHES = {'sampled/hero_piano': ('salamander-grand',), 'sampled/hero_piano_pop': ('salamander-grand',),
           'layered/hero_piano_strings': ('salamander-grand', 'vpo-wav', 'vpo-scripts-standard')}


def _installed(pack: str) -> bool:
    return (library.SAMPLES / pack / 'SOURCE.json').is_file()


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


def _layers(p):
    return {x.id: x for x in p.instrument.params['layers']}


class Registration(unittest.TestCase):
    def test_every_patch_registers_without_samples(self):
        self.assertGreaterEqual(hero_piano.VERSION, 1)
        for name in PATCHES:
            with self.subTest(patch=name):
                p = patches.get(name)
                self.assertEqual(p.instrument.type, 'stack')
                self.assertIn('Measured -18.0 LUFS', p.notes)
                self.assertTrue(p.notes.startswith(f'v{hero_piano.VERSION}.'))
                self.assertIn('Alexander Holm', p.notes)                      # CC-BY credit
                self.assertIn(p.audition.get('notes'), ('phrase', 'chord'))
                self.assertLessEqual(set(p.sends), {'plate', 'hall'})
                self.assertEqual(p.gain_db, hero_piano.LEVELS[name.split('/')[1]])

    def test_key_split_layers(self):
        for name in PATCHES:
            with self.subTest(patch=name):
                ls = _layers(patches.get(name))
                self.assertIn('low', ls)
                self.assertIn('high', ls)
                for lid in ('low', 'high'):
                    ins = ls[lid].instrument
                    self.assertEqual(ins.type, 'sampler')
                    self.assertTrue(ins.lazy, 'library patches read their samples lazily')
                    self.assertIn('salamander-grand', ins.lazy['path'])
                # the melody layer is narrower than the harmony layer (a solid centre)
                self.assertLess(ls['high'].instrument.params['width'], ls['low'].instrument.params['width'])

    def test_named_effects_for_tweaks(self):
        for name in ('sampled/hero_piano', 'sampled/hero_piano_pop'):
            p = patches.get(name)
            names = [f.name for f in p.fx]
            for n in ('tone', 'catch', 'glue'):
                self.assertIn(n, names)
            p.but_fx('tone', **{'hp.freq': 90})                           # the notes' band tweak works
            p.layer('high', width=0.6)

    def test_strings_layer_follows_keys_not_pedal(self):
        s = _layers(patches.get('layered/hero_piano_strings'))['strings']
        self.assertEqual(s.params.get('follow.pedal'), 0)
        self.assertGreater(s.params.get('delay', 0), 0)

    def test_missing_pack_names_the_pack(self):
        from agentsound import sfz
        with tempfile.TemporaryDirectory() as d, mock.patch.object(library, 'SAMPLES', pathlib.Path(d)), \
                mock.patch.object(sfz, 'ASSETS', pathlib.Path(d)):
            with self.assertRaisesRegex(ComposeError, 'samples fetch salamander-grand'):
                patches.get('sampled/hero_piano').instrument.to_dict()


class Carve(unittest.TestCase):
    def test_carve_ducks_and_dips_the_bed(self):
        s = Song('carve', tempo=100, key='C major', seed=1)
        s.section('a', bars=1)
        hero = s.track('lead', 'synthwave/soft_lead')
        pad = s.track('pad', 'synthwave/warm_pad')
        hero_piano.carve(s, hero, pad)
        types = [f.type for f in pad.fx]
        self.assertIn('ducker', types)
        dip = [f for f in pad.fx if f.name == 'hero_dip']
        self.assertEqual(len(dip), 1)
        self.assertLess(dip[0].params['peak2.gain'], 0)
        duck = [f for f in pad.fx if f.type == 'ducker'][0]
        self.assertEqual(duck.params['depth'], 2.5)

    def test_carve_options(self):
        s = Song('carve2', tempo=100, key='C major', seed=1)
        s.section('a', bars=1)
        hero = s.track('lead', 'synthwave/soft_lead')
        pad = s.track('pad', 'synthwave/warm_pad')
        n0 = len(pad.fx)
        hero_piano.carve(s, hero)                                          # nothing to carve: no-op
        hero_piano.carve(s, hero, pad, duck=0, dip=0)
        self.assertEqual(len(pad.fx), n0)


class Compile(unittest.TestCase):
    def test_installed_patches_compile_to_valid_render_json(self):
        engine = _engine()
        seen = 0
        for name, packs in PATCHES.items():
            if not all(_installed(p) for p in packs):
                continue
            seen += 1
            with self.subTest(patch=name):
                s = Song('hero piano', tempo=90, key='C major', seed=1)
                sec = s.section('a', bars=1)
                s.hall('hall')
                s.plate('plate')
                t = s.track('lead', name)
                t.note('C3', sec.start, 2, vel=70).note('E5', sec.start, 2, vel=100)
                t.automate('instrument.pedal', [(0, 1, 'step')])
                render = s.compile()
                ins = render['tracks'][0]['instrument']
                self.assertEqual(ins['type'], 'stack')
                for lay in ins['params']['layers']:
                    self.assertTrue(lay['instrument']['params']['samples'], f'{name}: a layer has no zones')
                if engine is None:
                    continue
                d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_hero_'))
                self.addCleanup(shutil.rmtree, d, True)
                rj = d / 'song.render.json'
                rj.write_text(dumps(render), encoding='utf-8')
                proc = subprocess.run([str(engine), 'validate', str(rj)], capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, f'{name}: {proc.stderr}')
        if not seen:
            self.skipTest('no salamander-grand pack installed ($AGENTSOUND_SAMPLES)')


if __name__ == '__main__':
    unittest.main()
