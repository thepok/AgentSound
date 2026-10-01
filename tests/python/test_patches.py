import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from agentsound import Song, cli, patches
from agentsound.patches import FX, Instrument, Patch, fx, inst
from agentsound.song import dumps
from agentsound.theory import ComposeError
from dx7_banks import missing_dx7


def lead() -> Patch:
    return Patch('test/lead', instrument={'type': 'va', 'params': {'cutoff': 3000, 'filter.type': 'ladder'}},
                 fx=[fx.chorus(mix=0.3)], gain_db=-4, pan=0.1, sends={'hall': -12},
                 notes='Test lead.\nSecond line.')


class PatchCopies(unittest.TestCase):
    def test_but_deep_copies(self):
        p = lead()
        q = p.but(cutoff=1200, **{'filter.resonance': 0.4}, amp__release=0.9)
        self.assertEqual(q.instrument.params, {'cutoff': 1200, 'filter.type': 'ladder', 'filter.resonance': 0.4,
                                               'amp.release': 0.9})
        self.assertEqual(p.instrument.params, {'cutoff': 3000, 'filter.type': 'ladder'})
        self.assertIsNot(q.instrument, p.instrument)
        self.assertIsNot(q.instrument.params, p.instrument.params)
        self.assertIsNot(q.fx[0], p.fx[0])
        q.fx[0].params['mix'] = 0.9
        q.sends['hall'] = 0
        self.assertEqual(p.fx[0].params['mix'], 0.3)
        self.assertEqual(p.sends['hall'], -12)
        self.assertEqual(q.name, p.name)

    def test_with_fx_and_mix(self):
        p = lead()
        self.assertEqual([f.type for f in p.with_fx(fx.delay(mix=0.2)).fx], ['chorus', 'delay'])
        self.assertEqual([f.type for f in p.with_fx(fx.eq(), first=True).fx], ['eq', 'chorus'])
        self.assertEqual([f.type for f in p.with_fx({'type': 'phaser'}, replace=True).fx], ['phaser'])
        self.assertEqual(len(p.fx), 1)
        m = p.with_mix(gain_db=-8, sends={'hall': None, 'echo': -20})
        self.assertEqual((m.gain_db, m.sends), (-8.0, {'echo': -20.0}))
        self.assertEqual(p.sends, {'hall': -12.0})
        with self.assertRaises(ComposeError):
            p.with_mix(pan=2)

    def test_chain_patch_but_targets_first_fx(self):
        c = Patch('bus/test_room', fx=[fx.reverb(type='room', mix=1.0)])
        self.assertTrue(c.is_chain)
        self.assertEqual(c.but(decay=1.2).fx[0].params, {'type': 'room', 'mix': 1.0, 'decay': 1.2})

    def test_validation(self):
        with self.assertRaises(ComposeError):
            Patch('Bad Name', {'type': 'va'})
        with self.assertRaises(ComposeError):
            Patch('test/x', {'type': 'va', 'params': {'cutoff': float('inf')}})
        with self.assertRaises(ComposeError):
            Patch('test/x', {'kind': 'va'})
        with self.assertRaises(ComposeError):
            Patch('test/x', {'type': 'va'}, fx=['reverb'])


class Descriptors(unittest.TestCase):
    def test_fx_factory(self):
        self.assertEqual(fx.reverb(type='plate', mix=1).to_dict(), {'type': 'reverb', 'params': {'type': 'plate', 'mix': 1}})
        self.assertEqual(fx('eq', {'low.gain': 2}, high__gain=-1).params, {'low.gain': 2, 'high.gain': -1})
        c = fx.compressor(threshold=-20, sidechain='kick')
        self.assertEqual(c.to_dict(), {'type': 'compressor', 'params': {'threshold': -20}, 'sidechain': 'kick'})
        self.assertEqual(fx.filter(name='sweep').name, 'sweep')
        self.assertEqual(FX.coerce({'type': 'delay', 'params': {'time': 0.75}}).params, {'time': 0.75})
        with self.assertRaises(ComposeError):
            FX('Reverb!')

    def test_inst_factory(self):
        self.assertEqual(inst.dx7('E.PIANO 1').to_dict(), {'type': 'dx7', 'params': {'voice': 'E.PIANO 1'}})
        self.assertEqual(inst.va(osc1__wave='saw', mode='mono').params, {'osc1.wave': 'saw', 'mode': 'mono'})
        self.assertEqual(Instrument.coerce({'type': 'drums'}).to_dict(), {'type': 'drums', 'params': {}})
        self.assertEqual(inst.va(cutoff=100).but(cutoff=200).params, {'cutoff': 200})


class Registry(unittest.TestCase):
    def tearDown(self):
        for n in [n for n in patches._REGISTRY if n.startswith('test/')]:
            del patches._REGISTRY[n]

    def test_register_get_list(self):
        patches.register(lead())
        patches.register(Patch('test/pad', {'type': 'va'}))
        self.assertTrue(patches.has('test/lead'))
        self.assertEqual(patches.list('test/'), ['test/lead', 'test/pad'])
        got = patches.get('test/lead')
        got.instrument.params['cutoff'] = 1
        self.assertEqual(patches.get('test/lead').instrument.params['cutoff'], 3000)
        self.assertEqual(patches.get('test/lead').but(cutoff=2500).instrument.params['cutoff'], 2500)
        self.assertIn('Test lead.', patches.describe('test/lead'))
        with self.assertRaises(ComposeError):
            patches.register(lead())
        patches.register(lead().with_mix(gain_db=-1), replace=True)
        self.assertEqual(patches.get('test/lead').gain_db, -1)

    def test_unknown_suggests(self):
        patches.register(lead())
        with self.assertRaisesRegex(ComposeError, "did you mean 'test/lead'"):
            patches.get('test/leed')


# ------------------------------------------------------------------------------ the lush library

RETURNS = ['bus/echo', 'bus/echo_quarter', 'bus/gated', 'bus/hall', 'bus/hall_lush', 'bus/plate', 'bus/plate_80s',
           'bus/shimmer', 'bus/tape_echo', 'bus/wide']
MASTERS = ['master/audition', 'master/darksynth', 'master/dreamwave', 'master/synthwave']
WIDENERS = {'chorus', 'ensemble', 'dimension', 'microshift', 'width'}
STEREO_FX = {'chorus', 'ensemble', 'dimension', 'microshift', 'flanger', 'phaser'}


class LushLibrary(unittest.TestCase):
    def test_returns_and_masters_registered(self):
        for n in RETURNS + MASTERS + ['bus/drums', 'bus/music']:
            self.assertTrue(patches.has(n), n)
            self.assertTrue(patches.get(n).is_chain, n)

    def test_return_helpers_keep_the_calibration(self):
        s = Song('t')
        s.section('a', bars=1)
        hall = s.hall(decay=4.5, predelay=40)
        lib = patches.get('bus/hall')
        self.assertEqual([f.type for f in hall.fx], [f.type for f in lib.fx])     # the calibration eq stays
        self.assertEqual(hall.fx[-1].params, lib.fx[-1].params)
        reverb = next(f for f in hall.fx if f.type == 'reverb')
        self.assertEqual((reverb.params['decay'], reverb.params['predelay'], reverb.params['mix']), (4.5, 40, 1.0))
        self.assertEqual(next(f for f in s.echo(time=0.5).fx if f.type == 'delay').params['time'], 0.5)
        self.assertEqual(next(f for f in s.plate(decay=1.2).fx if f.type == 'reverb').params['decay'], 1.2)
        self.assertEqual(next(f for f in s.gated(hold=250).fx if f.type == 'gatedreverb').params['hold'], 250)
        self.assertEqual(hall.gain_db, 0.0)                                          # the fader stays the composer's

    def test_sustained_synths_are_wide_and_the_low_end_is_mono(self):
        sustained = ('pad', 'strings', 'choir', 'epiano', 'bells', 'arp', 'lead', 'stab', 'brass', 'organ', 'piano',
                     'guitar', 'box', 'marimba', 'seq')
        for n in patches.list('synthwave/') + patches.list('gm/'):
            p = patches.get(n)
            kinds = {f.type for f in p.fx}
            if any(f.type == 'vocoder' and f.params.get('mode', 'classic') == 'classic' and f.params.get('width', 0.5) > 0
                   for f in p.fx):
                kinds.add('width')  # (a classic vocoder spreads its bands left / right: its own widener)
            short = n.rsplit('/', 1)[1]
            if 'bass' in short or short in ('fretless', 'impact') or short.startswith('drums'):
                self.assertFalse(kinds & STEREO_FX, f"{n} must stay mono-centred")
            elif any(w in short for w in sustained):
                self.assertTrue(kinds & WIDENERS, f"{n}: a sustained part needs its own width (chorus/dimension/...)")

    def test_space_returns_stay_mono_compatible(self):
        # A reverb/shimmer/delay return widened past 1.0 reads correlation < -0.1 (partly out of phase in mono); the
        # library's returns keep the effect's natural width (bus/gated's deliberate 1.2 burst is the one exception).
        for n in patches.list('bus/'):
            for f in patches.get(n).fx:
                if f.type in ('reverb', 'shimmer', 'delay'):
                    self.assertLessEqual(f.params.get('width', 1.0), 1.0, f"{n}: {f.type} width")

    def test_default_sends_target_the_standard_returns(self):
        # song.hall()/plate()/echo()/gated() create these ids, and the audition command creates a bus per send
        for n in patches.list('synthwave/') + patches.list('gm/'):
            self.assertLessEqual(set(patches.get(n).sends), {'hall', 'plate', 'echo', 'gated'}, n)

    def test_starter_and_demo_songs_use_only_library_sounds(self):
        for slug in ('_template', '_demo_lush'):
            song = cli.load_song(REPO / 'songs' / slug / 'song.py')
            render = song.compile()
            self.assertEqual(song.warnings, [], slug)            # no patch send dropped for a missing bus
            for t in song.tracks.values():
                self.assertIsNotNone(t.patch, f"{slug}: track {t.id!r} must be a library patch")
            self.assertEqual({b['id'] for b in render['buses']} >= {'hall', 'plate', 'echo', 'shimmer', 'gated'}, True)
            self.assertEqual([f['type'] for f in render['master']['fx']],
                             [f.type for f in patches.get('master/synthwave').fx])


def _missing_ir_pack(name: str) -> bool:
    """True when a chain patch uses a convolver IR from a sample pack that is not installed."""
    from agentsound import library
    for f in patches.get(name).fx:
        v = f.params.get('ir', [])
        for ir in (v if isinstance(v, list) else [v]):
            ir = str(ir).replace(chr(92), '/')
            if ir.startswith('samples/'):
                rel = ir[len('samples/'):]
            elif '/samples/' in ir:
                rel = ir.split('/samples/', 1)[1]
            else:
                continue
            if not (library.SAMPLES / rel.split('/', 1)[0] / 'SOURCE.json').is_file():
                return True
    return False


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


@unittest.skipIf(_engine() is None, 'engine not built (set AGENTSOUND_TEST_ENGINE or build build/agentsound.exe)')
class LushLibraryEngine(unittest.TestCase):
    def test_every_chain_passes_the_engine(self):
        """Every bus/master chain and every instrument patch (with its fx) passes the engine's strict validation."""
        s = Song('Chains', tempo=100, key='A minor', seed=1)
        a = s.section('a', bars=1)
        for i, n in enumerate(patches.list('bus/')):
            if _missing_ir_pack(n):      # IR returns need their (large, optional) IR pack installed
                continue
            s.bus(f"b{i}", n)
        voice = s.track('voice', inst.va(), mute=True)   # the modulator the vocoder patches need
        for i, n in enumerate(patches.list('gm/') + patches.list('synthwave/')):
            if missing_dx7(patches.get(n)):  # (without the DX7 ROM banks, see assets/dx7/README.md)
                continue
            t = s.track(f"t{i}", n).note('A3', a.start, 1)
            for f in t.fx:
                if f.type == 'vocoder':
                    t.fx[t.fx.index(f)] = f.keyed(voice.id)
        s.master.use('master/synthwave')
        for name in MASTERS:          # every master chain on its own copy of the song
            s.master.use(name)
            d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_lush_'))
            self.addCleanup(shutil.rmtree, d, True)
            rj = d / 'song.render.json'
            rj.write_text(dumps(s.compile()), encoding='utf-8')
            proc = subprocess.run([str(_engine()), 'validate', str(rj)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"{name}: {proc.stderr}")


if __name__ == '__main__':
    unittest.main()
