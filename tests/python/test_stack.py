"""Layered instruments in the compose layer: inst.stack / layer() / Patch.layered, layer addressing in .but(),
automation and modulators, per-layer zone pruning, credits, the layered/* library, and the engine accepting it all."""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from agentsound import Song, cli, delivery, fx, inst, layer, patches, ramp  # noqa: E402
from agentsound.patches import LAYER_KEYS, Layer, Patch  # noqa: E402
from agentsound.song import dumps  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402
from dx7_banks import needs_dx7  # noqa: E402


def _pad():
    return inst.va(cutoff=1500, unison=3)


def _stack():
    return inst.stack(layer('synthwave/epiano', 'keys'),
                      layer(_pad(), 'pad', level=-12, delay=40, fx=[fx.chorus(mix=0.3)], pedal=False),
                      layer(inst.dx7('TUB BELLS'), transpose=12, level=-10, bend=False, keys=('C4', 'C7')))


class StackBuilder(unittest.TestCase):
    def test_render_json_shape(self):
        d = _stack().to_dict()
        self.assertEqual(d['type'], 'stack')
        ls = d['params']['layers']
        self.assertEqual([x['id'] for x in ls], ['keys', 'pad', 'dx7'])
        ep = patches.get('synthwave/epiano')
        self.assertEqual(ls[0]['instrument'], ep.instrument.to_dict())          # a patch layer brings its instrument
        self.assertEqual([f['type'] for f in ls[0]['fx']], [f.type for f in ep.fx])  # ... and its fx chain
        self.assertEqual(ls[1]['level'], -12)
        self.assertEqual(ls[1]['delay'], 40)
        self.assertIs(ls[1]['follow.pedal'], False)
        self.assertEqual(ls[1]['fx'], [{'type': 'chorus', 'params': {'mix': 0.3}}])
        self.assertEqual((ls[2]['keylo'], ls[2]['keyhi'], ls[2]['transpose']), (60, 96, 12))
        self.assertIs(ls[2]['follow.bend'], False)
        self.assertNotIn('level', ls[0])                                          # 0 dB gain folds to nothing

    def test_patch_gain_and_pan_fold_into_the_layer(self):
        p = Patch('test/x', instrument=inst.va(), gain_db=-3, pan=0.2)
        x = layer(p, level=-2)
        self.assertEqual((x.params['level'], x.params['pan'], x.id), (-5, 0.2, 'x'))

    def test_kwargs_split_layer_and_child_params(self):
        x = layer(_pad(), 'pad', level=-6, cutoff=900, amp__attack=0.2, vel=(20, 90), velfade=10)
        self.assertEqual(x.params, {'level': -6, 'vello': 20, 'velhi': 90, 'velfade': 10})
        self.assertEqual((x.instrument.params['cutoff'], x.instrument.params['amp.attack']), (900, 0.2))
        self.assertTrue(set(x.params) <= set(LAYER_KEYS))

    def test_ids_are_unique(self):
        s = inst.stack(layer(_pad()), layer(_pad()), _pad(), 'synthwave/epiano')
        self.assertEqual([x.id for x in s.params['layers']], ['va', 'va2', 'va3', 'epiano'])

    def test_but_addresses_layers(self):
        s = _stack()
        b = s.but(**{'layers.pad.cutoff': 700, 'layers.keys.level': -2, 'layers.1.delay': 10,
                     'layers.pad.fx.chorus.mix': 0.5, 'layers.keys.fx.0.mix': 0.1, 'pedal': 1})
        L = {x.id: x for x in b.params['layers']}
        self.assertEqual(L['pad'].instrument.params['cutoff'], 700)
        self.assertEqual(L['pad'].params['delay'], 10)
        self.assertEqual(L['pad'].fx[0].params['mix'], 0.5)
        self.assertEqual(L['keys'].params['level'], -2)
        self.assertEqual(b.params['pedal'], 1)
        self.assertEqual({x.id: x for x in s.params['layers']}['pad'].instrument.params['cutoff'], 1500)  # a copy
        with self.assertRaises(ComposeError):
            s.but(**{'layers.nope.cutoff': 1})
        with self.assertRaises(ComposeError):
            s.but(**{'layers.pad.fx.reverb.mix': 1})

    def test_patch_layered_and_layer_helper(self):
        p = Patch.layered('test/layered', 'synthwave/epiano', layer('synthwave/dx_bells', 'bell', transpose=12),
                          fx=[fx.compressor()], sends={'hall': -12}, gain_db=-1)
        self.assertEqual(p.instrument.type, 'stack')
        q = p.layer('bell', level=-9, transpose=24)
        bell = q.instrument.params['layers'][1]
        self.assertEqual((bell.params['level'], bell.params['transpose']), (-9, 24))
        self.assertEqual(p.instrument.params['layers'][1].params['transpose'], 12)
        self.assertIn('stack of', patches.describe('layered/piano_glass_lead'))

    def test_copies_and_equality(self):
        a = _stack()
        self.assertEqual(a, inst.stack(*[x.copy() for x in a.params['layers']]))
        self.assertEqual(Layer.coerce(a.params['layers'][1].to_dict()), a.params['layers'][1])
        b = Patch('test/s', instrument=a).copy()
        self.assertEqual(b.instrument, a)

    def test_validation(self):
        with self.assertRaises(ComposeError):
            inst.stack()
        with self.assertRaises(ComposeError):
            inst.stack(*[_pad() for _ in range(9)])
        with self.assertRaises(ComposeError):
            layer(inst.stack(_pad()))
        with self.assertRaises(ComposeError):
            layer(_pad(), fx=[fx.compressor(sidechain='kick')])
        with self.assertRaises(ComposeError):
            layer(_pad(), 'Bad Id')
        with self.assertRaises(ComposeError):
            layer(_pad(), keys=(60,))


class StackInSongs(unittest.TestCase):
    def _song(self, sound):
        s = Song('Stack', tempo=120, seed=2)
        a = s.section('a', bars=2)
        t = s.track('lead', sound)
        for i, (k, v) in enumerate([(48, 60), (60, 90), (64, 110), (79, 30)]):
            t.note(k, a.start + i, 1, vel=v)
        return s, t

    def test_targets_resolve_to_layer_ids(self):
        s, t = self._song(_stack())
        t.automate('instrument.layers.1.cutoff', ramp(0, 8, 400, 3000))
        t.automate('instrument.layers.pad.fx.chorus.mix', ramp(0, 8, 0, 0.5))
        t.modulate('instrument.layers.keys.level', patches_lfo())
        r = s.compile()
        tr = r['tracks'][0]
        self.assertEqual({a['target'] for a in tr['automation']},
                         {'instrument.layers.pad.cutoff', 'instrument.layers.pad.fx.0.mix'})
        m = tr['modulators'][0]
        self.assertEqual((m['target'], m['base']), ('instrument.layers.keys.level', 0.0))   # the engine default
        s2, t2 = self._song(_stack())
        t2.automate('instrument.layers.zz.cutoff', ramp(0, 8, 400, 3000))
        with self.assertRaises(ComposeError):
            s2.compile()

    def test_zone_pruning_per_layer(self):
        zones = [{'file': '*sine', 'root': k, 'lo': k - 2, 'hi': k + 2} for k in range(26, 126, 5)]
        sampler = inst.sampler(zones=zones)
        s, _ = self._song(inst.stack(layer(sampler, 'low', keys=(0, 59)),
                                     layer(sampler, 'oct', transpose=12, vel=(80, 127)),
                                     layer(inst.va(), 'va')))
        ls = s.compile()['tracks'][0]['instrument']['params']['layers']
        roots = lambda x: sorted(z['root'] for z in x['instrument']['params']['samples'])   # noqa: E731
        self.assertEqual(roots(ls[0]), [46])            # key 48 only (the low layer ends at 59)
        self.assertEqual(roots(ls[1]), [71, 76])        # 60 / 64 at velocity >= 80, +12: keys 72 and 76
        self.assertNotIn('transpose', ls[1]['instrument']['params'])   # (the child keeps its own params)
        self.assertEqual(ls[2]['instrument']['type'], 'va')

    def test_credits_see_layer_assets(self):
        s, _ = self._song(inst.stack(layer(inst.sf2('Grand Piano')), layer(inst.va())))
        refs = delivery.asset_refs(s.compile())
        self.assertIn(('sf2', 'GeneralUser-GS.sf2'), refs)


def patches_lfo():
    from agentsound import lfo
    return lfo('sine', '1/4', depth=3)


class LayeredLibrary(unittest.TestCase):
    def test_every_layered_patch(self):
        names = patches.list('layered/')
        self.assertGreaterEqual(len(names), 12)
        for n in names:
            p = patches.get(n)
            self.assertEqual(p.instrument.type, 'stack', n)
            ls = p.instrument.params['layers']
            self.assertGreaterEqual(len(ls), 2, n)
            self.assertEqual(len({x.id for x in ls}), len(ls), n)
            self.assertIn('Measured -18.0 LUFS', p.notes, n)
            self.assertIn('Tweak', p.notes, n)
            self.assertTrue(p.audition and p.audition.get('notes'), n)
            self.assertLessEqual(set(p.sends), {'hall', 'plate', 'echo', 'gated'}, n)

    def test_sustaining_synth_layers_ignore_the_pedal(self):
        # a pedalled synth layer that sustains (sustain > 0, no own pedal) piles a melody's notes into a held cluster;
        # the layered library keeps them off the pedal wherever the stack is meant to be pedalled (keys, piano leads)
        for n in patches.list('layered/'):
            p = patches.get(n)
            layers = p.instrument.params['layers']
            if not any(x.instrument.type in ('sampler', 'sf2') and 'piano' in (x.source or '') for x in layers):
                continue   # not a pedalled keyboard stack
            for x in layers:
                if x.instrument.type != 'va' or x.params.get('follow.pedal', 1) == 0:
                    continue
                self.assertEqual(x.instrument.params.get('amp.sustain', 0.8), 0.0,
                                 f"{n}: the sustaining va layer {x.id!r} follows the pedal (layer(..., pedal=False))")


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


def _installed(p: Patch) -> bool:
    try:
        p.instrument.to_dict()
        return True
    except ComposeError:     # a layer's sample pack is not installed
        return False


@unittest.skipIf(_engine() is None, 'engine not built')
class StackEngine(unittest.TestCase):
    def _validate(self, song):
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_stack_'))
        rj = d / 'song.render.json'
        rj.write_text(dumps(song.compile()), encoding='utf-8')
        proc = subprocess.run([str(_engine()), 'validate', str(rj)], capture_output=True, text=True)
        return proc.returncode, proc.stderr

    @needs_dx7
    def test_engine_accepts_stacks_and_layer_targets(self):
        s = Song('Stack', tempo=110, seed=1)
        a = s.section('a', bars=1)
        t = s.track('lead', _stack().but(pedal=0))
        t.note('A4', a.start, 1)
        t.automate('instrument.layers.pad.cutoff', ramp(0, 4, 400, 3000))
        t.automate('instrument.layers.dx7.level', ramp(0, 4, -20, -8))
        t.automate('instrument.pedal', [[0, 1], [2, 0, 'step']])
        code, err = self._validate(s)
        self.assertEqual(code, 0, err)

    def test_layered_library_passes_the_engine(self):
        s = Song('Layered', tempo=100, seed=1)
        a = s.section('a', bars=1)
        for n in patches.list('layered/'):
            p = patches.get(n)
            if not _installed(p):
                continue
            s.track(n.split('/')[1], p).note('A3', a.start, 1)
        self.assertIn('synth_sub_bass', s.tracks)     # (the pure synth stack always works)
        for b in ('hall', 'plate', 'echo'):
            getattr(s, b)()
        code, err = self._validate(s)
        self.assertEqual(code, 0, err)


if __name__ == '__main__':
    unittest.main()
