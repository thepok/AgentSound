import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import (ComposeError, Mod, Song, drums, envelope, follow, fx, gate, inst, lfo, per_section, ramp,
                        sample_hold, steps)
from agentsound import cli
from agentsound.modulation import gate_values, parse_rate
from agentsound.song import dumps


def base_song(time_sig='4/4') -> tuple:
    s = Song('Mod Test', tempo=120, key='A minor', seed=3, time_sig=time_sig)
    verse = s.section('verse', bars=4)
    chorus = s.section('chorus', bars=4)
    kit = s.track('drums', inst.drums(kit='synthwave'))
    kit.loop(drums({'kick': 'x...x...x...x...', 'hat': '..x.'}), verse, chorus)
    pad = s.track('pad', inst.va(cutoff=2200, unison=3), fx=[fx.filter(name='lp', cutoff=9000), fx.chorus(mix=0.3)],
                  gain_db=-7, pan=0.1)
    pad.loop(s.prog('i VI').block(), verse, chorus)
    s.master.add(fx.limiter())
    return s, verse, chorus, kit, pad


def track_dict(render: dict, tid: str) -> dict:
    return next(t for t in render['tracks'] if t['id'] == tid)


class Rates(unittest.TestCase):
    def test_note_values_bars_beats_hz(self):
        self.assertEqual(parse_rate('1/16'), ('beats', 0.25))
        self.assertEqual(parse_rate('1/8.'), ('beats', 0.75))
        self.assertAlmostEqual(parse_rate('1/8t')[1], 1 / 3)
        self.assertEqual(parse_rate('1/4'), ('beats', 1.0))
        self.assertEqual(parse_rate('1 bar'), ('bars', 1.0))
        self.assertEqual(parse_rate('2 bars'), ('bars', 2.0))
        self.assertEqual(parse_rate('1/2 bar'), ('bars', 0.5))
        self.assertEqual(parse_rate('3 beats'), ('beats', 3.0))
        self.assertEqual(parse_rate('0.5 beat'), ('beats', 0.5))
        self.assertEqual(parse_rate('5hz'), ('hz', 5.0))
        self.assertEqual(parse_rate('5.5 Hz'), ('hz', 5.5))
        self.assertEqual(parse_rate(2), ('beats', 2.0))
        self.assertEqual(parse_rate('4'), ('beats', 4.0))
        for bad in ('fast', 0, -1, True, '0 bars', '1/0', '', 'bars', None, [1]):
            with self.assertRaises(ComposeError, msg=repr(bad)):
                parse_rate(bad)

    def test_rates_resolve_with_the_meter(self):
        for sig, bar in (('4/4', 4.0), ('3/4', 3.0), ('6/8', 3.0)):
            s, verse, chorus, kit, pad = base_song(sig)
            pad.modulate('pan', lfo('sine', rate='2 bars', depth=0.5))
            pad.modulate('gainDb', steps([0, -1], rate='1/2 bar', depth=6))
            mods = track_dict(s.compile(), 'pad')['modulators']
            self.assertEqual(mods[0]['source']['rateBeats'], 2 * bar, sig)
            self.assertEqual(mods[1]['source']['stepBeats'], bar / 2, sig)
        s, *_, pad = base_song()
        pad.modulate('instrument.cutoff', lfo('triangle', rate='6hz', depth=0.2, curve='exp'))
        src = track_dict(s.compile(), 'pad')['modulators'][0]['source']
        self.assertEqual(src, {'type': 'lfo', 'shape': 'triangle', 'rateHz': 6.0})
        with self.assertRaises(ComposeError):
            steps([0, 1], rate='4hz', depth=1)          # steps live on the beat grid
        with self.assertRaises(ComposeError):
            lfo('sine', rate='90hz', depth=1)           # no audio-rate modulation


class Gates(unittest.TestCase):
    def test_gate_strings(self):
        self.assertEqual(gate_values('x.x.'), [0.0, -1.0, 0.0, -1.0])
        self.assertEqual(gate_values('X-x.'), [0.0, -1.0, 0.0, -1.0])
        self.assertEqual(gate_values('x_..'), [0.0, 0.0, -1.0, -1.0])
        self.assertEqual(gate_values('x x | . x'), [0.0, 0.0, -1.0, 0.0])
        self.assertEqual(gate_values('90'), [0.0, -1.0])
        self.assertAlmostEqual(gate_values('3')[0], 3 / 9 - 1, places=6)
        for bad in ('', '  |', '_x', 'x.o.', 'xyz', 5, None):
            with self.assertRaises(ComposeError, msg=repr(bad)):
                gate_values(bad)

    def test_gate_compiles_to_offset_steps_on_the_fader(self):
        s, verse, chorus, kit, pad = base_song()
        pad.modulate('gainDb', gate('x.x.xx.x.x.xx.x.', rate='1/16', depth=18))
        m = track_dict(s.compile(), 'pad')['modulators'][0]
        self.assertEqual(m['target'], 'gainDb')
        self.assertEqual(m['mode'], 'offset')
        self.assertEqual(m['depth'], 18.0)
        self.assertEqual(m['base'], -7.0)              # the fader level, filled in
        self.assertEqual(m['source']['type'], 'steps')
        self.assertEqual(m['source']['stepBeats'], 0.25)
        self.assertEqual(m['source']['values'][:6], [0.0, -1.0, 0.0, -1.0, 0.0, 0.0])
        self.assertEqual(len(m['source']['values']), 16)


class Compile(unittest.TestCase):
    def test_no_modulators_no_key(self):
        s, *_ = base_song()
        r = s.compile()
        for t in r['tracks']:
            self.assertNotIn('modulators', t)
        self.assertNotIn('modulators', r['master'])

    def test_lfo_absolute_and_offset(self):
        s, verse, chorus, kit, pad = base_song()
        pad.modulate('instrument.cutoff', lfo('sine', rate='1/4', min=600, max=4000, curve='exp'))
        pad.modulate('pan', lfo('tri', rate='2 bars', depth=0.6, phase=0.25), window=chorus)
        pad.modulate('fx.lp.cutoff', lfo('saw_up', rate='1/8', depth=1, curve='exp', retrigger=True))
        a, b, c = track_dict(s.compile(), 'pad')['modulators']
        self.assertEqual(a, {'target': 'instrument.cutoff', 'source': {'type': 'lfo', 'shape': 'sine', 'rateBeats': 1.0},
                             'mode': 'absolute', 'min': 600.0, 'max': 4000.0, 'curve': 'exp'})
        self.assertEqual(b['source'], {'type': 'lfo', 'shape': 'triangle', 'rateBeats': 8.0, 'phase': 0.25})
        self.assertEqual((b['mode'], b['depth'], b['base']), ('offset', 0.6, 0.1))   # base = the track pan
        self.assertEqual((b['startBeat'], b['endBeat']), (chorus.start, chorus.end))
        self.assertEqual(c['target'], 'fx.0.cutoff')                                  # fx name resolved
        self.assertEqual(c['source']['shape'], 'ramp')
        self.assertEqual(c['source']['retrigger'], 'note')
        self.assertEqual(c['base'], 9000.0)                                           # from the fx params

    def test_legacy_forms_still_make_points(self):
        pts = lfo(0, 4, 300, 2400, period='1/2', log=True)
        self.assertIsInstance(pts, list)
        self.assertTrue(all(isinstance(p, tuple) for p in pts))
        self.assertEqual(lfo(start=0, end=4, lo=1, hi=2, period=1), lfo(0, 4, 1, 2, period=1))
        self.assertEqual(steps({8: 1, 0: 0}), [(0.0, 0, 'step'), (8.0, 1, 'step')])
        self.assertIsInstance(lfo('sine', rate='1/4', depth=1, base=0), Mod)
        self.assertIsInstance(steps([1, 2], rate='1/8'), Mod)
        with self.assertRaises(ComposeError):
            steps({0: 1}, rate='1/8')

    def test_steps_envelope_sample_hold(self):
        s, verse, chorus, kit, pad = base_song()
        arp = s.track('arp', inst.va(osc1__wave='square'))
        arp.loop(s.prog('i VI').arp('up', rate='1/16'), chorus)
        arp.modulate('instrument.cutoff', steps([400, 2400, 800, 3200], rate='1/16', glide=0.3, curve='exp'))
        arp.modulate('instrument.resonance', envelope(decay='1/8', min=0.1, max=0.6))
        arp.modulate('pan', sample_hold('1/16', smooth=0.25, min=-0.4, max=0.4))
        arp.modulate('gainDb', steps([0, -1, 0.5], rate='1/8', loop=False, depth=6))
        a, b, c, d = track_dict(s.compile(), 'arp')['modulators']
        self.assertEqual(a['source'], {'type': 'steps', 'stepBeats': 0.25, 'values': [400.0, 2400.0, 800.0, 3200.0],
                                       'glide': 0.3})
        self.assertEqual((a['mode'], a.get('curve')), ('absolute', 'exp'))
        self.assertNotIn('min', a)
        self.assertEqual(b['source'], {'type': 'envelope', 'attackBeats': 0.0, 'decayBeats': 0.5, 'sustain': 0.0,
                                       'releaseBeats': 0.5, 'trigger': 'note'})
        self.assertEqual(c['source'], {'type': 'random', 'rateBeats': 0.25, 'smooth': 0.25})
        self.assertEqual(d['source']['loop'], False)
        self.assertEqual(d['base'], 0.0)

    def test_follow_and_trigger_with_pitches_use_ghost_key_tracks(self):
        s, verse, chorus, kit, pad = base_song()
        bass = s.track('bass', inst.va(cutoff=700))
        bass.loop(s.prog('i VI').bass('octave', rate='1/8'), verse, chorus)
        bass.modulate('instrument.cutoff', follow(kit, pitches='kick', min=300, max=2500, curve='exp'))
        pad.modulate('gainDb', envelope(decay='1/4', trigger=kit, pitches='kick', depth=-10))
        pad.modulate('instrument.cutoff', follow('bass', attack=2, release=80, gain_db=6, depth=1, curve='exp'))
        r = s.compile()
        ghost = track_dict(r, 'drums-key')
        self.assertTrue(ghost['mute'])
        self.assertTrue(all(n[2] == 36 for n in ghost['notes']))
        fb = track_dict(r, 'bass')['modulators'][0]
        self.assertEqual(fb['source'], {'type': 'follow', 'attackMs': 5.0, 'releaseMs': 120.0, 'node': 'drums-key'})
        env, fol = track_dict(r, 'pad')['modulators']
        self.assertEqual(env['source']['trigger'], 'drums-key')
        self.assertEqual(env['source']['releaseBeats'], env['source']['decayBeats'])
        self.assertEqual(fol['source'], {'type': 'follow', 'attackMs': 2.0, 'releaseMs': 80.0, 'gainDb': 6.0, 'node': 'bass'})
        self.assertEqual(fol['base'], 2200.0)
        self.assertEqual(sum(1 for t in r['tracks'] if t['id'].startswith('drums-key')), 1)   # one shared ghost

    def test_field_automation(self):
        s, verse, chorus, kit, pad = base_song()
        pad.modulate('instrument.cutoff', lfo('sine', rate='1/8', depth=ramp(verse.start, chorus.end, 0, 2),
                                              curve='exp'))
        pad.modulate('pan', lfo('sine', rate='1 bar', depth=0.3, name='sway'))
        pad.automate('mod.sway.depth', per_section({verse: 0.1, chorus: 0.7}))
        pad.automate('mod.sway.rate', ramp(verse.start, chorus.end, 4, 1))
        r = track_dict(s.compile(), 'pad')
        lanes = {a['target']: a['points'] for a in r['automation']}
        self.assertEqual(lanes['mod.0.depth'], [[0.0, 0.0], [32.0, 2.0]])
        self.assertEqual(r['modulators'][0]['depth'], 0.0)
        self.assertEqual(lanes['mod.1.depth'], [[0.0, 0.1], [16.0, 0.7, 'step']])
        self.assertIn('mod.1.rateBeats', lanes)
        s2, *_, pad2 = base_song()
        pad2.modulate('pan', lfo('sine', rate='1 bar', depth=0.3))
        pad2.automate('mod.0.depth', ramp(0, 8, 0, 1))
        self.assertIn('mod.0.depth', [a['target'] for a in track_dict(s2.compile(), 'pad')['automation']])
        for bad in ('mod.nope.depth', 'mod.3.depth', 'mod.0.speed'):
            s3, *_, pad3 = base_song()
            pad3.modulate('pan', lfo('sine', rate='1 bar', depth=0.3))
            pad3.automate(bad, ramp(0, 8, 0, 1))
            with self.assertRaises(ComposeError, msg=bad):
                s3.compile()
        s4, *_, pad4 = base_song()
        pad4.modulate('gainDb', gate('x.', depth=12))
        pad4.automate('mod.0.rate', ramp(0, 8, 1, 2))
        with self.assertRaises(ComposeError):
            s4.compile()                                # a gate's step length can't move

    def test_offset_uses_lane_or_base(self):
        s, verse, chorus, kit, pad = base_song()
        pad.automate('instrument.cutoff', ramp(verse.start, chorus.end, 800, 3000, 'exp'))
        pad.modulate('instrument.cutoff', lfo('sine', rate='1/4', depth=0.5, curve='exp'))
        m = track_dict(s.compile(), 'pad')['modulators'][0]
        self.assertNotIn('base', m)                     # the lane is the base
        s, verse, chorus, kit, pad = base_song()
        pad.automate('pan', ramp(0, 8, -0.2, 0.2))
        pad.modulate('pan', lfo('sine', rate='1/4', depth=0.5, base=0))
        with self.assertRaises(ComposeError):
            s.compile()                                 # base next to a lane is ambiguous
        s, verse, chorus, kit, pad = base_song()
        pad.modulate('instrument.resonance', lfo('sine', rate='1/4', depth=0.2))
        with self.assertRaisesRegex(ComposeError, 'base='):
            s.compile()                                 # resonance isn't set on the instrument: unknown centre
        s, verse, chorus, kit, pad = base_song()
        pad.modulate('instrument.resonance', lfo('sine', rate='1/4', min=0.1, max=0.5), window=chorus)
        with self.assertRaisesRegex(ComposeError, 'outside'):
            s.compile()                                 # unknown value outside the window
        s, verse, chorus, kit, pad = base_song()
        pad.modulate('instrument.cutoff', lfo('sine', rate='1/4', min=500, max=5000), window=chorus)
        self.assertEqual(track_dict(s.compile(), 'pad')['modulators'][0]['base'], 2200.0)

    def test_absolute_modulator_hiding_a_lane_warns(self):
        s, verse, chorus, kit, pad = base_song()
        pad.automate('instrument.cutoff', ramp(verse.start, chorus.end, 800, 3000, 'exp'))
        pad.modulate('instrument.cutoff', lfo('sine', rate='1/4', min=500, max=5000, curve='exp'))
        s.compile()
        self.assertTrue(any('automation lane is ignored' in w for w in s.warnings), s.warnings)
        s, verse, chorus, kit, pad = base_song()
        pad.automate('instrument.cutoff', ramp(verse.start, chorus.end, 800, 3000, 'exp'))
        pad.modulate('instrument.cutoff', lfo('sine', rate='1/4', min=500, max=5000, curve='exp'), window=chorus)
        pad.modulate('instrument.cutoff', lfo('sine', rate='1/8', depth=0.3, curve='exp'))
        s.compile()
        self.assertFalse(any('automation lane is ignored' in w for w in s.warnings), s.warnings)

    def test_windows(self):
        s, verse, chorus, kit, pad = base_song()
        pad.modulate('pan', lfo('sine', rate='1/4', depth=0.2), window=(verse.bar(2), None))
        pad.modulate('gainDb', lfo('sine', rate='1/4', depth=2), window='chorus')
        a, b = track_dict(s.compile(), 'pad')['modulators']
        self.assertEqual(a['startBeat'], 8.0)
        self.assertNotIn('endBeat', a)
        self.assertEqual((b['startBeat'], b['endBeat']), (16.0, 32.0))
        with self.assertRaises(ComposeError):
            pad.modulate('pan', lfo('sine', depth=0.1), window=(chorus, verse))
        with self.assertRaises(ComposeError):
            pad.modulate('pan', lfo('sine', depth=0.1), window=5)

    def test_sends_and_describe(self):
        s, verse, chorus, kit, pad = base_song()
        hall = s.hall()
        pad.send(hall, -12)
        pad.modulate('send.hall', lfo('sine', rate='1 bar', depth=6))
        m = track_dict(s.compile(), 'pad')['modulators'][0]
        self.assertEqual((m['target'], m['base']), ('send.hall', -12.0))
        self.assertIn('mods: send.hall~lfo sine', s.describe())
        s.master.modulate('gainDb', lfo('sine', rate='4 bars', depth=0.5))
        self.assertEqual(s.compile()['master']['modulators'][0]['base'], 0.0)

    def test_errors(self):
        s, verse, chorus, kit, pad = base_song()
        bus = s.bus('grp')
        cases = [
            lambda: lfo('wobble', rate='1/4', depth=1),
            lambda: lfo('sine', rate='1/4'),                                 # no mapping
            lambda: lfo('sine', rate='1/4', min=1, max=2, depth=1),          # both mappings
            lambda: lfo('sine', rate='1/4', min=1),                          # half a range
            lambda: lfo('sine', rate='1/4', min=0, max=100, curve='exp'),    # exp needs > 0
            lambda: lfo('sine', rate='1/4', depth=1, curve='log'),
            lambda: lfo('sine', rate='1/4', depth=20, curve='exp'),          # octaves
            lambda: lfo('sine', rate='1/4', depth=1, phase=1.5),
            lambda: steps([], rate='1/8'),
            lambda: steps([100, 200], rate='1/8', min=1, max=2),
            lambda: steps([0, 2], rate='1/8', depth=1),                     # offset values in -1..1
            lambda: steps([0, 200], rate='1/8', curve='exp'),
            lambda: steps([1, 2], glide=2),
            lambda: steps([1, 2], rate=ramp(0, 4, 0.25, 0.5)),                # step length can't move
            lambda: envelope(decay='soon', depth=1),
            lambda: envelope(sustain=2, depth=1),
            lambda: follow('x', attack=-1, depth=1),
            lambda: sample_hold('1/8', smooth=3, depth=1),
            lambda: lfo('sine', depth=1, name='Bad Name'),
            lambda: pad.modulate('mod.0.depth', lfo('sine', depth=1)),
            lambda: pad.modulate('volume', lfo('sine', depth=1)),
            lambda: pad.modulate('pan'),
            lambda: pad.modulate('pan', ramp(0, 4, 0, 1)),
            lambda: bus.modulate('instrument.cutoff', lfo('sine', min=1, max=2)),
            lambda: bus.modulate('pan', envelope(depth=0.5)),                # a bus has no notes
            lambda: bus.modulate('pan', lfo('sine', depth=0.5, retrigger=True)),
            lambda: pad.modulate('pan', follow('pad', depth=0.5)),           # self
            lambda: pad.modulate('pan', follow('master', depth=0.5)),
            lambda: pad.modulate('pan', follow('nope', pitches='kick', depth=0.5)),
        ]
        for i, case in enumerate(cases):
            with self.assertRaises(ComposeError, msg=f"case #{i}"):
                case()
        pad.modulate('pan', lfo('sine', depth=0.3, name='a'))
        with self.assertRaises(ComposeError):
            pad.modulate('gainDb', lfo('sine', depth=1, name='a'))           # duplicate name

    def test_compile_errors(self):
        def expect(build, pattern):
            s, verse, chorus, kit, pad = base_song()
            build(s, pad, kit)
            with self.assertRaisesRegex(ComposeError, pattern):
                s.compile()
        expect(lambda s, pad, kit: pad.modulate('pan', follow('ghost', depth=0.2)), 'no track or bus')
        expect(lambda s, pad, kit: pad.modulate('pan', envelope(trigger='ghost', depth=0.2)), 'no track')
        expect(lambda s, pad, kit: pad.modulate('pan', lfo('sine', min=-2, max=1)), 'outside the range')
        # 'gainDb' values are dB on the track's gain_db (-7): +32 lands at +25, over the +24 limit
        expect(lambda s, pad, kit: pad.modulate('gainDb', steps([0, 32], rate='1/8')), 'outside the range')
        expect(lambda s, pad, kit: pad.modulate('fx.reverb.mix', lfo('sine', min=0, max=1)), 'no fx')

        def cycle(s, pad, kit):
            grp = s.bus('grp')
            pad.to(grp)
            pad.modulate('pan', follow(grp, depth=0.3))
        expect(cycle, 'routing cycle.*followed')


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


@unittest.skipIf(_engine() is None, 'engine not built (set AGENTSOUND_TEST_ENGINE or build build/agentsound.exe)')
class EngineValidation(unittest.TestCase):
    def test_every_generator_passes_the_engine(self):
        s, verse, chorus, kit, pad = base_song()
        hall = s.hall()
        pad.send(hall, -10)
        bass = s.track('bass', inst.va(cutoff=700))
        bass.loop(s.prog('i VI').bass('octave', rate='1/8'), verse, chorus)
        bass.modulate('instrument.cutoff', follow(kit, pitches='kick', min=300, max=2500, curve='exp'))
        bass.modulate('instrument.cutoff', lfo('square', rate='1/8', depth=ramp(chorus.start, chorus.end, 0, 1),
                                               curve='exp'), window=chorus)
        pad.modulate('gainDb', gate('x.x.xx.x.x.xx.x.', depth=18))
        pad.modulate('pan', lfo('triangle', rate='2 bars', depth=0.6), window=chorus)
        pad.modulate('send.hall', envelope(decay='1/2', trigger=kit, pitches='kick', depth=-6))
        pad.modulate('fx.lp.cutoff', steps([4000, 9000, 2000], rate='1/8', glide=0.4, curve='exp'))
        pad.modulate('instrument.cutoff', sample_hold('1/4', smooth=1, depth=0.5, curve='exp', name='drift'))
        pad.automate('mod.drift.depth', ramp(verse.start, chorus.end, 0.1, 0.8))
        s.master.modulate('gainDb', lfo('sine', rate='5hz', depth=0.2))
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_mod_'))
        self.addCleanup(shutil.rmtree, d, True)
        rj = d / 'song.render.json'
        rj.write_text(dumps(s.compile()), encoding='utf-8')
        proc = subprocess.run([str(_engine()), 'validate', str(rj)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_engine_rejects_what_python_cannot_know(self):
        s, verse, chorus, kit, pad = base_song()
        pad.modulate('instrument.cutoff', lfo('sine', min=5, max=4000))    # 5 Hz is below the va cutoff range
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_mod_'))
        self.addCleanup(shutil.rmtree, d, True)
        rj = d / 'song.render.json'
        rj.write_text(json.dumps(s.compile()), encoding='utf-8')
        proc = subprocess.run([str(_engine()), 'validate', str(rj)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn('outside the range 20..20000', proc.stderr)


if __name__ == '__main__':
    unittest.main()
