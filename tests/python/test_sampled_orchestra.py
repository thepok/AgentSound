"""Sampled orchestra & winds library (agentsound/patches/sampled_orchestra.py) and the per-zone levelling it uses
(agentsound/patches/_levelling.py, the lazy 'post' hook): every patch registers without reading samples, carries its
notes, level calibration and a valid audition hint; with the sample packs installed every patch compiles to a render
JSON whose zones exist, with the measured corrections applied. Tests that need the packs skip when they are not
installed ($AGENTSOUND_SAMPLES or assets/samples); the hook, the table and the CLI hint are tested without samples."""
import json
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentsound import Song, library, patches  # noqa: E402
from agentsound import articulation as art  # noqa: E402
from agentsound.cli import CliError, audition_hint  # noqa: E402
from agentsound.patches import Instrument, Patch, _levelling, inst  # noqa: E402
from agentsound.patches import sampled_orchestra as orch  # noqa: E402
from agentsound.theory import note  # noqa: E402

POST_CALLS = []


def _mark(ins):
    """A post hook for the tests: records the call and tags the zones."""
    POST_CALLS.append(len(ins.params['samples']))
    for z in ins.params['samples']:
        z['gain'] = z.get('gain', 0.0) + 1.5


def packs_of(p: Patch) -> set:
    spec = p.instrument.lazy or {}
    paths = [spec['path']] if 'path' in spec else [v if isinstance(v, str) else v['path']
                                                   for v in (spec.get('programs') or {}).values()]
    out = set()
    for path in paths:
        pack = path.split('/')[1]
        out.add(pack)
        if pack.startswith('vpo-scripts'):
            out.add('vpo-wav')
    return out


def installed(packs) -> bool:
    return all((library.SAMPLES / p / 'SOURCE.json').is_file() for p in packs)


def playable(p: Patch) -> tuple:
    """(low, high) MIDI keys of the patch's own range: the zones of its first articulation (read now)."""
    ins = Instrument.coerce(p.instrument)
    ins.expand()
    zs = [z for z in ins.params['samples'] if z.get('trigger') != 'release']
    first = min((z.get('swLast', 0) for z in zs), default=0)
    zs = [z for z in zs if z.get('swLast', 0) == first] or zs
    tr = int(ins.params.get('transpose', 0) or 0)
    return min(z['lo'] for z in zs) - tr, max(z['hi'] for z in zs) - tr


class TestRegistry(unittest.TestCase):
    def test_every_patch_registers_lazily(self):
        self.assertGreaterEqual(len(orch.PATCHES), 30)
        existing = set(patches.list('sampled/')) - set(orch.PATCHES)
        for name in orch.PATCHES:
            self.assertTrue(name.startswith('sampled/'), name)
            self.assertTrue(patches.has(name), name)
            p = patches.get(name)
            self.assertEqual(p.instrument.type, 'sampler', name)
            self.assertIsNotNone(p.instrument.lazy, f"{name}: must not read samples at import")
            self.assertTrue(any(f.type == 'eq' for f in p.fx), f"{name}: clean-up EQ")
            self.assertTrue(p.sends, f"{name}: sends")
            self.assertIn('Measured -18.0 LUFS', p.notes, name)
            self.assertIn('License', p.notes, name)
            audition_hint(p)                                     # a valid hint (raises CliError otherwise)
            self.assertTrue(packs_of(p), name)
        self.assertEqual(len(set(orch.PATCHES)), len(orch.PATCHES))
        self.assertFalse(existing & set(orch.PATCHES))

    def test_levelled_patches_use_the_table(self):
        for name in orch.CALIBRATION:
            p = patches.get(name)
            self.assertEqual(p.instrument.lazy.get('post'), ['agentsound.patches.sampled_orchestra:_fix'], name)
        table = json.loads(orch.LEVEL_TABLE.read_text(encoding='utf-8'))
        self.assertTrue(table)
        for k, v in table.items():
            self.assertIsInstance(v, (int, float), k)
            self.assertLessEqual(abs(v), 60.0, k)
            self.assertIn('|', k)
        self.assertTrue(any(k.endswith('|tune') for k in table))

    def test_legato_soloists_are_mono(self):
        for name in ('sampled/bassoon', 'sampled/solo_trumpet', 'sampled/solo_horn', 'sampled/tuba',
                     'sampled/english_horn', 'sampled/solo_viola', 'sampled/bari_sax'):
            self.assertEqual(patches.get(name).instrument.params.get('mono'), 'legato', name)

    def test_find_lists_them(self):
        from agentsound import catalog
        self.assertIn('sampled/english_horn', catalog.search(['english', 'horn'], only='patches'))
        self.assertIn('sampled/glockenspiel', catalog.search(['glockenspiel'], only='patches'))


class TestPostHook(unittest.TestCase):
    """The lazy 'post' hook of Instrument.expand() and the levelling table, on a tiny local SFZ (no sample packs)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        with wave.open(str(d / 'a.wav'), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(b''.join(struct.pack('<h', int(8000 * ((i % 100) / 50 - 1))) for i in range(4410)))
        (d / 'x.sfz').write_text('<region> sample=a.wav lokey=60 hikey=72 pitch_keycenter=66\n', encoding='utf-8')
        self.sfz = str(d / 'x.sfz')

    def tearDown(self):
        self.tmp.cleanup()

    def test_post_runs_once_after_expand(self):
        POST_CALLS.clear()
        ins = inst.sfz(self.sfz, lazy=True, level=-3)
        ins.lazy['post'] = [f'{__name__}:_mark']
        copy = Instrument.coerce(ins)                            # carried with the lazy spec
        d = copy.to_dict()
        self.assertEqual(POST_CALLS, [1])
        self.assertAlmostEqual(d['params']['samples'][0]['gain'], 1.5)
        copy.to_dict()                                           # expanded: not again
        self.assertEqual(POST_CALLS, [1])

    def test_apply_adds_gain_and_tune(self):
        ins = inst.sfz(self.sfz)
        z = ins.params['samples'][0]
        key = _levelling._rel(z['file']) + '|'
        _levelling.apply(ins, {key: -2.5, key + '|tune': 12.0})
        self.assertAlmostEqual(z['gain'], -2.5)
        self.assertAlmostEqual(z['tune'], 12.0)

    def test_layer_velocities(self):
        ins = Instrument('sampler', samples=[
            {'file': 'a.wav', 'lo': 60, 'hi': 60, 'root': 60, 'xfoutLo': 0, 'xfoutHi': 83},
            {'file': 'b.wav', 'lo': 60, 'hi': 60, 'root': 60, 'xfinLo': 0, 'xfinHi': 83, 'xfoutLo': 84,
             'xfoutHi': 127},
            {'file': 'c.wav', 'lo': 60, 'hi': 60, 'root': 60, 'xfinLo': 84, 'xfinHi': 127}])
        vs = _levelling._layer_vels(ins, stack=False)
        self.assertIn(12, vs)
        self.assertIn(127, vs)
        self.assertEqual(_levelling._layer_vels(ins, stack=True), [100])
        self.assertEqual(_levelling._vel_weight(ins.params['samples'][2], 40), 0.0)
        self.assertEqual(_levelling._vel_weight(ins.params['samples'][1], 83), 1.0)


class TestAuditionOctave(unittest.TestCase):
    def test_octave_hint(self):
        ok = Patch('t/x', instrument=inst.va(), audition={'notes': 'phrase', 'octave': 2})
        self.assertEqual(audition_hint(ok)['octave'], 2)
        for bad in (9, 2.5, 'low', True):
            with self.assertRaises(CliError):
                audition_hint(Patch('t/y', instrument=inst.va(), audition={'notes': 'phrase', 'octave': bad}))

    def test_phrase_moves_with_the_octave(self):
        from agentsound.cli import audition_song
        low = [n.pitch for n in audition_song('sampled/tuba', 'auto').tracks['patch'].notes]
        high = [n.pitch for n in audition_song('sampled/piccolo', 'auto').tracks['patch'].notes]
        self.assertTrue(low and high)
        self.assertLess(max(low), note('C4'))                   # octave 2: a tuba phrase B2-B3
        self.assertGreater(min(high), note('C5'))                # octave 5: a piccolo phrase B5-B6


class TestWithSamples(unittest.TestCase):
    """Every patch compiles (its zones exist) when its packs are installed; skipped otherwise."""

    def test_compile_every_patch(self):
        missing = []
        for name in orch.PATCHES:
            p = patches.get(name)
            if not installed(packs_of(p)):
                missing.append(name)
                continue
            with self.subTest(patch=name):
                lo, hi = playable(p)
                s = Song('t', tempo=100, seed=1)
                a = s.section('a', bars=2)
                t = s.track('p', p)
                arts = art.available(t) or [None]
                mid = (lo + hi) // 2
                notes = [art.note(i * 0.5, 0.45, mid, 90, n) for i, n in enumerate(arts)]
                notes.append(art.note(len(arts) * 0.5, 0.45, lo, 90, arts[0]))
                notes.append(art.note(len(arts) * 0.5 + 0.5, 0.45, hi, 90, arts[0]))
                from agentsound.patterns import Clip
                t.play(Clip._raw(notes, 8), a)
                r = s.compile()
                tr = next(x for x in r['tracks'] if x['id'] == 'p')
                zones = tr['instrument']['params']['samples']
                self.assertTrue(zones, name)
                for z in zones:
                    self.assertTrue(Path(z['file']).is_file(), z['file'])
        if len(missing) == len(orch.PATCHES):
            self.skipTest('no sample pack of the orchestra library installed')

    def test_table_is_applied(self):
        p = patches.get('sampled/bassoon')
        if not installed(packs_of(p)):
            self.skipTest('vsco2-ce not installed')
        levelled = Instrument.coerce(p.instrument).expand()
        raw = Instrument.coerce(p.instrument)
        raw.lazy = {k: v for k, v in raw.lazy.items() if k != 'post'}
        raw.expand()
        diff = [a.get('gain', 0) - b.get('gain', 0) for a, b in zip(levelled.params['samples'], raw.params['samples'])]
        self.assertTrue(any(abs(d) > 0.5 for d in diff))


if __name__ == '__main__':
    unittest.main()
