"""The sampled keys library (agentsound/patches/sampled_keys.py): every patch registers without the samples; with its
pack installed ($AGENTSOUND_SAMPLES or assets/samples) it compiles to render JSON the engine accepts. Patches whose
pack is missing are skipped (an empty $AGENTSOUND_SAMPLES skips them all)."""

import importlib
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
from agentsound.song import dumps  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

EXPECTED = {
    'soft_piano': 'osiris-piano', 'studio_piano': 'headroom-piano', 'recital_grand': 'headroom-piano', 'concert_grand': 'splendid-grand-piano',
    'upright_yamaha': 'vcsl', 'honky_tonk': 'freepats-old-piano-fb', 'rhodes_vibrato': 'jrhodes3d',
    'cp80': 'greg-sullivan-epianos', 'pianet': 'greg-sullivan-epianos', 'clavinet': 'lithalean-clavinet',
    'tonewheel_organ': 'freepats-drawbar-organ', 'jazz_organ': 'freepats-percussive-organ',
    'chamber_organ': 'lars-palo-burea-choir-organ', 'renaissance_organ': 'vcsl', 'harpsichord': 'vcsl',
    'mellotron_strings': 'mellotron-sfz', 'mellotron_flute': 'mellotron-sfz', 'mellotron_choir': 'mellotron-sfz',
    'mellotron_cello': 'mellotron-sfz', 'solina_strings': 'sampleradar-976-classic-synth',
    'poly_synth': 'sampleradar-analogue-polysynths', 'soft_poly': 'sampleradar-analogue-polysynths',
}

# a note inside each instrument's range (the rest: middle C)
PITCH = {'mellotron_cello': 'C3', 'chamber_organ': 'C4', 'renaissance_organ': 'C4', 'harpsichord': 'C4'}


def _pack_of(spec: dict) -> str:
    """Pack id of a lazy instrument spec ('samples/<pack>/...')."""
    if 'programs' in spec:
        first = next(iter(spec['programs'].values()))
        path = first['path'] if isinstance(first, dict) else first
    else:
        path = spec.get('path') or spec.get('source')
    return path.replace('\\', '/').split('/')[1]


def _installed(pack: str) -> bool:
    return (library.SAMPLES / pack / 'SOURCE.json').is_file()


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


class Registration(unittest.TestCase):
    def test_every_patch_registers_without_samples(self):
        mod = importlib.import_module('agentsound.patches.sampled_keys')
        self.assertGreaterEqual(mod.VERSION, 1)
        for short, pack in EXPECTED.items():
            with self.subTest(patch=short):
                p = patches.get(f'sampled/{short}')
                self.assertEqual(p.instrument.type, 'sampler')
                self.assertTrue(p.instrument.lazy, 'library patches read their samples lazily')
                self.assertEqual(_pack_of(p.instrument.lazy), pack)
                self.assertIn('Measured -18.0 LUFS', p.notes)
                self.assertTrue(p.notes.startswith('v1.'))
                self.assertLessEqual(set(p.sends), {'hall', 'plate', 'echo', 'gated'})
                self.assertIn(p.audition.get('notes'), ('chord', 'stab', 'arp', 'phrase'))

    def test_notes_flag_restricted_licences(self):
        for short in ('rhodes_vibrato',):
            self.assertIn('NC', patches.get(f'sampled/{short}').notes)
        for short in ('clavinet',):
            self.assertIn('License not stated', patches.get(f'sampled/{short}').notes)
        for short in ('mellotron_strings', 'solina_strings', 'poly_synth'):
            self.assertIn('commercial' if 'mellotron' in short else 'redistributed',
                          patches.get(f'sampled/{short}').notes)
        for short in ('studio_piano', 'recital_grand', 'cp80', 'pianet', 'chamber_organ'):
            self.assertRegex(patches.get(f'sampled/{short}').notes, r'Credit|credit')

    def test_recital_grand_is_the_measured_classical_voicing(self):
        from agentsound.patches.sampled_keys import RECITAL
        params = patches.get('sampled/recital_grand').instrument.params
        for k, v in RECITAL.items():
            self.assertEqual(params[k], v)
        self.assertEqual(RECITAL['velsens'], 1.0)          # studio_piano's 0.7 flattened a p-mp melody
        self.assertGreater(RECITAL['sympathetic'], 0.0)     # the pedal halo

    def test_leslie_is_automatable_by_name(self):
        p = patches.get('sampled/tonewheel_organ')
        names = [f.name for f in p.fx]
        self.assertIn('leslie', names)
        self.assertIn('leslie_am', names)

    def test_missing_pack_names_the_pack(self):
        from agentsound import sfz
        with tempfile.TemporaryDirectory() as d, mock.patch.object(library, 'SAMPLES', pathlib.Path(d)), \
                mock.patch.object(sfz, 'ASSETS', pathlib.Path(d)):
            with self.assertRaisesRegex(ComposeError, 'samples fetch splendid-grand-piano'):
                patches.get('sampled/concert_grand').instrument.to_dict()


class Compile(unittest.TestCase):
    def test_installed_patches_compile_to_valid_render_json(self):
        engine = _engine()
        seen = 0
        for short, pack in EXPECTED.items():
            if not _installed(pack):
                continue
            seen += 1
            with self.subTest(patch=short):
                s = Song(f'keys {short}', tempo=100, key='C major', seed=1)
                sec = s.section('a', bars=1)
                s.hall('hall')
                s.plate('plate')
                t = s.track('k', f'sampled/{short}')
                t.note(PITCH.get(short, 'C4'), sec.start, 2, vel=90)
                render = s.compile()
                ins = render['tracks'][0]['instrument']
                self.assertEqual(ins['type'], 'sampler')
                self.assertTrue(ins['params']['samples'], f'{short}: no zones for its note')
                if engine is None:
                    continue
                d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_keys_'))
                self.addCleanup(shutil.rmtree, d, True)
                rj = d / 'song.render.json'
                rj.write_text(dumps(render), encoding='utf-8')
                proc = subprocess.run([str(engine), 'validate', str(rj)], capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, f'{short}: {proc.stderr}')
        if not seen:
            self.skipTest('no keys sample packs installed ($AGENTSOUND_SAMPLES)')


if __name__ == '__main__':
    unittest.main()
