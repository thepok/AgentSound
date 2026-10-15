"""The wavetable synth's compose API: inst.wavetable (tables, file paths), its 'mods' targets (vamod), the
wavetable/ patches, and (with a built engine) a short render: finite, audible, click-free, a file table found next
to the song."""

import json
import math
import os
import pathlib
import runpy
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from agentsound import Song, cli, patches, vamod
from agentsound.patches import inst
from agentsound.song import dumps
from agentsound.theory import ComposeError

PRESETS = ('wavetable/warm_pad', 'wavetable/evolving_pad', 'wavetable/pluck', 'wavetable/bass', 'wavetable/lead')


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


def _write_serum_wav(path: pathlib.Path, frames: int = 4, size: int = 256) -> None:
    """A tiny Serum-style table: 'clm ' chunk + float32 frames (frame f = harmonic f + 1)."""
    data = b''.join(struct.pack('<f', 0.8 * math.sin(2 * math.pi * (f + 1) * n / size))
                    for f in range(frames) for n in range(size))
    clm = f'<!>{size} 10000000 wavetable'.encode()
    fmt = struct.pack('<HHIIHH', 3, 1, 48000, 48000 * 4, 4, 32)
    body = b'WAVE' + b'fmt ' + struct.pack('<I', 16) + fmt + b'clm ' + struct.pack('<I', len(clm)) + clm
    body += b'\0' * (len(clm) % 2)   # (RIFF chunks are padded to even sizes)
    body += b'data' + struct.pack('<I', len(data)) + data
    path.write_bytes(b'RIFF' + struct.pack('<I', len(body)) + body)


class WavetableApi(unittest.TestCase):
    def test_builtin_and_params(self):
        i = inst.wavetable('formant', table2='harmonics', osc1__position=0.3, unison=3)
        self.assertEqual(i.type, 'wavetable')
        self.assertEqual(i.params['osc1.table'], 'formant')
        self.assertEqual(i.params['osc2.table'], 'harmonics')
        self.assertEqual(i.params['osc1.position'], 0.3)
        self.assertNotIn('osc2.table', inst.wavetable('basic').params)

    def test_file_table_relative_to_the_song(self):
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_wtapi_'))
        self.addCleanup(shutil.rmtree, d, True)
        (d / 'song_like.py').write_text("from agentsound.patches import inst\n"
                                        "I = inst.wavetable('./tables/Growl.wav', table2='Pack/Pad.wt')\n",
                                        encoding='utf-8')
        ns = runpy.run_path(str(d / 'song_like.py'))
        p = ns['I'].params
        self.assertEqual(pathlib.Path(p['osc1.table']), (d / 'tables' / 'Growl.wav').resolve())
        self.assertEqual(p['osc2.table'], 'Pack/Pad.wt')   # relative: $AGENTSOUND_WAVETABLES / assets/wavetables/

    def test_mods_targets_per_instrument(self):
        ok = inst.wavetable('basic', mods=[vamod.env(a=1, d=2, s=0.3) >> ('osc1.position', 0.5),
                                           vamod.lfo('sine', hz=0.2, mode='global') >> ('osc2.warp', 0.3)])
        self.assertEqual([r['target'] for r in ok.params['mods']], ['osc1.position', 'osc2.warp'])
        with self.assertRaisesRegex(ComposeError, "not a 'wavetable' target"):
            inst.wavetable('basic', mods=[vamod.lfo('sine', hz=1) >> ('osc1.pw', 0.2)])
        with self.assertRaisesRegex(ComposeError, "not a 'va' target"):
            inst.va(mods=[vamod.lfo('sine', hz=1) >> ('osc1.position', 0.2)])
        self.assertIn('osc1.position', vamod.targets_for('wavetable'))
        self.assertNotIn('fm', vamod.targets_for('wavetable'))
        self.assertNotIn('osc2.warp', vamod.targets_for('va'))
        w = ok.with_mods(vamod.velocity() >> ('cutoff', 1.0, 'vel'))
        self.assertEqual(len(w.params['mods']), 3)
        with self.assertRaisesRegex(ComposeError, "not a 'wavetable' target"):
            ok.with_mods(vamod.lfo('sine', hz=1) >> ('fm', 1.0))
        with self.assertRaisesRegex(ComposeError, 'modulation matrix'):
            inst.dx7('E.PIANO 1', mods=[vamod.lfo('sine', hz=1) >> ('pitch', 10)])

    def test_presets(self):
        self.assertEqual(sorted(patches.list('wavetable/')), sorted(PRESETS))
        for n in PRESETS:
            p = patches.get(n)
            self.assertEqual(p.instrument.type, 'wavetable', n)
            self.assertIn('Measured -18', p.notes, n)
        lead = patches.get('wavetable/lead').instrument.params
        # not a thin beep (HUMAN_FEEDBACK): an octave-down body layer, glide and vibrato
        self.assertEqual(lead['osc2.semi'], -12)
        self.assertGreater(lead['osc2.level'], 0.5)
        self.assertGreater(lead['glide'], 0)
        self.assertIn('pitch', [r['target'] for r in lead['mods']])
        q = patches.get('wavetable/warm_pad').but(**{'osc1.table': 'organ'})
        self.assertEqual(q.instrument.params['osc1.table'], 'organ')


@unittest.skipIf(_engine() is None, 'engine not built (set AGENTSOUND_TEST_ENGINE or build build/agentsound.exe)')
class WavetableEngine(unittest.TestCase):
    def test_presets_and_a_file_table_render(self):
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_wtrender_'))
        self.addCleanup(shutil.rmtree, d, True)
        _write_serum_wav(d / 'tiny.wav')
        s = Song('Wavetable Probe', tempo=110, key='A minor', seed=3)
        a = s.section('a', bars=2)
        for i, n in enumerate(PRESETS):
            t = s.track(f"t{i}", n)
            for k, pitch in enumerate(('A2', 'C3', 'E3', 'A3') if 'bass' not in n else ('A1', 'E2', 'A1', 'G1')):
                t.note(pitch, a.start + 2 * k, 1.5, vel=70 + 10 * k)
        f = s.track('file', inst.wavetable(str(d / 'tiny.wav'), osc1__position=1.0, level=-6))
        f.note('A3', a.start, 4, vel=90)
        rj = d / 'song.render.json'
        rj.write_text(dumps(s.compile()), encoding='utf-8')
        types = {t['id']: t['instrument']['type'] for t in json.loads(rj.read_text(encoding='utf-8'))['tracks']}
        self.assertEqual(set(types.values()), {'wavetable'})
        proc = subprocess.run([str(_engine()), 'render', str(rj), '--out', str(d), '--no-png', '--quiet'],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rep = json.loads((d / 'report.json').read_text(encoding='utf-8'))
        self.assertEqual(rep['clicks'], [])
        self.assertGreater(rep['global']['lufsIntegrated'], -40)

    def test_unknown_table_is_an_error(self):
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_wtbad_'))
        self.addCleanup(shutil.rmtree, d, True)
        s = Song('Bad', tempo=100, key='C major', seed=1)
        a = s.section('a', bars=1)
        s.track('w', inst.wavetable('nonesuch')).note('C4', a.start, 1)
        rj = d / 'song.render.json'
        rj.write_text(dumps(s.compile()), encoding='utf-8')
        proc = subprocess.run([str(_engine()), 'validate', str(rj)], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('nonesuch', proc.stderr + proc.stdout)


if __name__ == '__main__':
    unittest.main()
