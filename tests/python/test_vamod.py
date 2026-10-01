import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import ComposeError, Song, cli, inst, patches, ramp
from agentsound import lfo as track_lfo  # the song-level modulator (not the va's own vamod.lfo)
from agentsound import vamod as vm
from agentsound.patches import Patch
from agentsound.song import dumps
from dx7_banks import missing_dx7


class Builders(unittest.TestCase):
    def test_lfo_rates_and_defaults(self):
        self.assertEqual((vm.lfo('sine', rate='1/8') >> ('pitch', 15)).to_json(),
                         {'source': {'type': 'lfo', 'shape': 'sine', 'rateBeats': 0.5}, 'target': 'pitch', 'amount': 15})
        self.assertEqual(vm.lfo('tri', rate='1/4.').to_json(), {'type': 'lfo', 'shape': 'triangle', 'rateBeats': 1.5})
        self.assertEqual(vm.lfo('saw_up', rate='3 beats').data['rateBeats'], 3)
        self.assertEqual(vm.lfo('square', rate=2).data['rateBeats'], 2)
        self.assertEqual(vm.lfo('sh', rate='5hz').data, {'type': 'lfo', 'shape': 'samplehold', 'rateHz': 5})
        self.assertEqual(vm.lfo('saw_down', hz=0.3, mode='global', phase=0.25, delay=0.3, fade=0.5, unipolar=True).data,
                         {'type': 'lfo', 'shape': 'saw', 'rateHz': 0.3, 'phase': 0.25, 'delay': 0.3, 'fade': 0.5,
                          'mode': 'global', 'unipolar': True})
        self.assertEqual(vm.lfo('smooth', rate='1/8t').data['shape'], 'smoothrandom')
        self.assertAlmostEqual(vm.lfo('sine', rate='1/8t').data['rateBeats'], 1 / 3, places=9)

    def test_other_sources(self):
        self.assertEqual(vm.env(a=0, d=0.08).to_json(),
                         {'type': 'env', 'attack': 0, 'decay': 0.08, 'sustain': 0, 'release': 0.08})
        self.assertEqual(vm.env(0.01, 0.2, 0.5, 1.5, curve='linear').to_json(),
                         {'type': 'env', 'attack': 0.01, 'decay': 0.2, 'sustain': 0.5, 'release': 1.5, 'curve': 'linear'})
        self.assertEqual(vm.velocity().to_json(), {'type': 'velocity'})
        self.assertEqual(vm.key().to_json(), {'type': 'key'})
        self.assertEqual(vm.key('C3', 'C6').to_json(), {'type': 'key', 'low': 48, 'high': 84})
        self.assertEqual(vm.random().to_json(), {'type': 'random'})
        self.assertEqual(vm.random(seed=7, unipolar=True).to_json(), {'type': 'random', 'seed': 7, 'unipolar': True})
        self.assertEqual(vm.macro(3).to_json(), {'type': 'macro', 'index': 3})

    def test_routes_and_ids(self):
        r = vm.lfo('sine', hz=5.5, id='vib') >> ('pitch', 15)
        self.assertEqual(r.to_json()['id'], 'vib')
        self.assertEqual((vm.velocity() >> ('cutoff', 1.5, 'vel')).to_json(),
                         {'source': {'type': 'velocity'}, 'target': 'cutoff', 'amount': 1.5, 'id': 'vel'})
        self.assertEqual(vm.velocity().to(target='amp', amount=-6).to_json()['amount'], -6)
        self.assertEqual((vm.random() >> ('pan', 0.3)).named('spread').id, 'spread')
        self.assertEqual(vm.lfo('sine', hz=0.2, mode='global') >> ('hpf', 1), vm.lfo('sine', hz=0.2, mode='global') >> ('hpf', 1))
        self.assertIn('mod.vib.amount', vm.describe([r]))
        self.assertIn('mod.1.amount', vm.describe([r, vm.macro(1) >> ('cutoff', 2)]))

    def test_errors(self):
        bad = [
            lambda: vm.lfo('sine'),                                   # no rate
            lambda: vm.lfo('sine', rate='1/8', hz=3),                 # both
            lambda: vm.lfo('sine', rate='2 bars'),                    # bars: the meter is unknown
            lambda: vm.lfo('wobble', hz=1),
            lambda: vm.lfo('sine', hz=0),
            lambda: vm.lfo('sine', hz=1, phase=1.5),
            lambda: vm.lfo('sine', hz=1, mode='poly'),
            lambda: vm.lfo('sine', hz=1, id='Vib'),
            lambda: vm.env(s=2),
            lambda: vm.env(curve='log'),
            lambda: vm.key('C4'),
            lambda: vm.key('C5', 'C4'),
            lambda: vm.random(seed=-1),
            lambda: vm.macro(9),
            lambda: vm.velocity() >> ('cutof', 1),
            lambda: vm.velocity() >> ('cutoff', 11),
            lambda: vm.velocity() >> ('amp', 30),
            lambda: vm.velocity() >> 'cutoff',
            lambda: vm.velocity() >> ('hpf', 1),                       # global target needs a global source
            lambda: vm.lfo('sine', hz=1) >> ('hpf', 1),
            lambda: vm.lfo('sine', hz=1, mode='global', delay=0.5) >> ('hpf', 1),
            lambda: vm.normalize_mods([vm.velocity()]),                # a source without target
            lambda: vm.normalize_mods([vm.velocity() >> ('cutoff', 1, 'a'), vm.key() >> ('pan', 1, 'a')]),
            lambda: vm.normalize_mods([vm.velocity() >> ('cutoff', 0.1)] * 65),
            lambda: vm.normalize_mods([{'source': {'type': 'lfo', 'rate': 1}, 'target': 'cutoff', 'amount': 1}]),
            lambda: vm.normalize_mods([{'source': {'type': 'wobble'}, 'target': 'cutoff', 'amount': 1}]),
            lambda: vm.normalize_mods([{'source': {'type': 'velocity'}, 'target': 'cutoff'}]),
            lambda: vm.normalize_mods('lfo'),
        ]
        for i, f in enumerate(bad):
            with self.subTest(i=i), self.assertRaises(ComposeError):
                f()
        self.assertEqual(len(vm.normalize_mods([vm.velocity() >> ('cutoff', 0.1)] * 64)), 64)
        self.assertTrue(vm.macro(2) >> ('hpf', 2))
        self.assertTrue(vm.lfo('sine', hz=0.2, mode='global') >> ('hpf', 2))


class InstrumentsAndPatches(unittest.TestCase):
    def test_instrument_params(self):
        i = inst.va(unison=3, mods=[vm.lfo('sine', rate='1/8', delay=0.3) >> ('osc1.pitch', 15),
                                    {'source': {'type': 'velocity'}, 'target': 'cutoff', 'amount': 1.5}])
        self.assertEqual(i.params['mods'][0], {'source': {'type': 'lfo', 'shape': 'sine', 'rateBeats': 0.5, 'delay': 0.3},
                                               'target': 'osc1.pitch', 'amount': 15})
        self.assertEqual(i.params['mods'][1]['source'], {'type': 'velocity'})
        json.dumps(i.to_dict())  # plain JSON
        self.assertEqual(i.but(mods=[]).params['mods'], [])
        self.assertEqual(len(i.params['mods']), 2)
        with self.assertRaises(ComposeError):
            inst.dx7('E.PIANO 1', mods=[vm.velocity() >> ('cutoff', 1)])
        with self.assertRaises(ComposeError):
            inst.va(mods=vm.velocity())  # a source, not a route

    def test_with_mods_appends_and_replaces_by_id(self):
        p = Patch('test/vamod_lead', inst.va(mods=[vm.lfo('sine', hz=5, id='vib') >> ('pitch', 10)]))
        q = p.with_mods(vm.velocity() >> ('cutoff', 1), vm.lfo('sine', hz=6, delay=0.4, id='vib') >> ('pitch', 20))
        self.assertEqual([m.get('id') for m in q.instrument.params['mods']], ['vib', None])
        self.assertEqual(q.instrument.params['mods'][0]['amount'], 20)
        self.assertEqual(q.instrument.params['mods'][0]['source']['delay'], 0.4)
        self.assertEqual(len(p.instrument.params['mods']), 1)               # the original is untouched
        self.assertEqual(len(p.with_mods(vm.key() >> ('cutoff', 0.5), replace=True).instrument.params['mods']), 1)
        self.assertEqual(p.but(**{'mod.vib.amount': 25}).instrument.params['mod.vib.amount'], 25)
        # a later with_mods() route wins over an earlier flat amount override of the same id (not the other way)
        o = p.but(**{'mod.vib.amount': 25, 'mod.0.amount': 5}).with_mods(vm.lfo('sine', hz=6, id='vib') >> ('pitch', 12))
        self.assertNotIn('mod.vib.amount', o.instrument.params)
        self.assertEqual(o.instrument.params['mod.0.amount'], 5)   # (indices of kept routes are unchanged)
        self.assertEqual(o.instrument.params['mods'][0]['amount'], 12)
        r = p.but(**{'mod.0.amount': 5}).with_mods(vm.key() >> ('cutoff', 0.5), replace=True)
        self.assertNotIn('mod.0.amount', r.instrument.params)
        self.assertEqual(o.with_mods(vm.velocity() >> ('amp', 3)).but(**{'mod.vib.amount': 30}).instrument.params['mod.vib.amount'], 30)
        with self.assertRaises(ComposeError):
            Patch('bus/x', fx=[]).with_mods(vm.velocity() >> ('cutoff', 1))
        with self.assertRaises(ComposeError):
            inst.dx7('E.PIANO 1').with_mods(vm.velocity() >> ('cutoff', 1))

    def test_library_has_no_fixed_lfo_params(self):
        for name in patches.list():
            p = patches.get(name)
            if p.instrument is None or p.instrument.type != 'va':
                continue
            for k in p.instrument.params:
                self.assertFalse(k.startswith(('lfo1.', 'lfo2.')) or k in ('fenv.pitch', 'fenv.osc2'), f"{name}: {k}")
            if 'mods' in p.instrument.params:
                self.assertEqual(vm.normalize_mods(p.instrument.params['mods']), p.instrument.params['mods'])

    def test_migrated_patches(self):
        mods = patches.get('synthwave/pulse_lead').instrument.params['mods']
        self.assertEqual(mods, [{'source': {'type': 'lfo', 'shape': 'sine', 'rateHz': 5.5, 'delay': 0.3, 'fade': 0.45},
                                 'target': 'pitch', 'amount': 16, 'id': 'vib'}])
        laser = patches.get('synthwave/laser').instrument.params['mods']
        self.assertEqual([m['target'] for m in laser], ['pitch', 'osc2.pitch'])
        self.assertEqual(laser[0]['source'], laser[1]['source'])  # one shared envelope, like the old fenv.pitch/osc2
        sweep = patches.get('synthwave/sweep_pad').instrument.params['mods'][0]
        self.assertEqual(sweep['source'], {'type': 'lfo', 'shape': 'triangle', 'rateBeats': 8, 'mode': 'global'})


def song_with_mods():
    s = Song('Vamod', tempo=100, key='A minor', seed=3)
    verse = s.section('verse', bars=2)
    chorus = s.section('chorus', bars=2)
    lead = s.track('lead', inst.va(unison=3, osc1__wave='sine', mods=[
        vm.lfo('sine', hz=5.5, delay=0.3, fade=0.4, id='vib') >> ('pitch', 15),
        vm.env(a=0, d=0.08) >> ('pitch', 1200),
        vm.lfo('triangle', hz=0.3, mode='global') >> ('osc2.pw', 0.3),
        vm.velocity() >> ('cutoff', 1.5),
        vm.key('C3', 'C6') >> ('cutoff', 1),
        vm.random() >> ('pan', 0.3),
        vm.macro(1) >> ('cutoff', 2),
        vm.lfo('square', rate='1/16', mode='global', unipolar=True, id='gate') >> ('amp', -12),
        vm.macro(2) >> ('hpf', 2, 'hp'),
        vm.env(0, 0.3, 0, 0.3, id='bell') >> ('fm', 3),
    ]))
    lead.play(s.motif('1:1/4 3:1/4 5:1/2 8:1').clip(octave=4), verse)
    lead.automate('instrument.mod.vib.amount', ramp(verse.start, chorus.end, 0, 25))
    lead.automate('instrument.macro1', ramp(verse.start, chorus.end, 0, 1))
    lead.modulate('instrument.macro2', track_lfo('sine', rate='1 bar', min=0, max=1))  # a track modulator on a macro
    return s


class Compile(unittest.TestCase):
    def test_render_json(self):
        rj = song_with_mods().compile()
        t = rj['tracks'][0]
        self.assertEqual(len(t['instrument']['params']['mods']), 10)
        self.assertIn('instrument.mod.vib.amount', [a['target'] for a in t['automation']])


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


@unittest.skipIf(_engine() is None, 'engine not built (set AGENTSOUND_TEST_ENGINE or build build/agentsound.exe)')
class EngineValidation(unittest.TestCase):
    def validate(self, song):
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_vamod_'))
        self.addCleanup(shutil.rmtree, d, True)
        rj = d / 'song.render.json'
        rj.write_text(dumps(song.compile()), encoding='utf-8')
        return subprocess.run([str(_engine()), 'validate', str(rj)], capture_output=True, text=True)

    def test_every_source_and_target_passes_the_engine(self):
        proc = self.validate(song_with_mods())
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_every_library_patch_passes_the_engine(self):
        s = Song('Library', tempo=100, key='A minor', seed=1)
        sec = s.section('a', bars=1)
        n = 0
        for name in patches.list('synthwave/'):
            p = patches.get(name)
            if p.instrument is None or any(f.type == 'vocoder' for f in p.fx):  # (vocoders need a voice: test_speech)
                continue
            if missing_dx7(p):    # (without the DX7 ROM banks, see assets/dx7/README.md)
                continue
            s.track(f"t{n}", p.but()).note('A3', sec.start, 1)
            n += 1
        proc = self.validate(s)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_engine_rejects_an_unknown_amount_param(self):
        s = Song('Bad amount', tempo=100)
        a = s.section('a', bars=1)
        t = s.track('t', inst.va(mods=[vm.velocity() >> ('cutoff', 1, 'vel')]))
        t.note('A3', a.start, 1)
        t.automate('instrument.mod.nope.amount', ramp(0, 4, 0, 1))
        proc = self.validate(s)
        self.assertEqual(proc.returncode, 2)
        self.assertIn('mod.nope.amount', proc.stderr)


if __name__ == '__main__':
    unittest.main()
