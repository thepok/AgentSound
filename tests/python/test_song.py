import json
import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import (FX, ComposeError, Patch, Song, chord, drums, exp_ramp, fx, inst, lfo, per_section, ramp,
                        riser, snare_roll)
from agentsound.song import dumps

ID_RE = re.compile(r'^[a-z0-9_-]+$')


def small_song(seed=7) -> Song:
    s = Song('Test Song', tempo=104, key='A minor', seed=seed)
    intro = s.section('intro', bars=4)
    verse = s.section('verse', bars=8)
    chorus = s.section('chorus', bars=8)
    hall = s.hall()
    kit = s.track('drums', inst.drums(kit='synthwave'), gain_db=-3).groove('laidback').humanize(3, 5)
    kit.loop(drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'hat': '..x.'}), verse, chorus)
    kit.play(snare_roll(2, build=True), chorus.beat(-2), replace=True)
    prog = s.prog('i VI III VII')
    bass = s.track('bass', inst.va(cutoff=800), gain_db=-6)
    bass.loop(prog.bass('octave', rate='1/16'), verse, chorus)
    pad = s.track('pad', inst.va(unison=5), fx=[fx.chorus(mix=0.4), fx.filter(name='lp', cutoff=8000)],
                  sends={hall: -10})
    pad.loop(prog.block(), intro, verse, chorus)
    pad.automate('fx.lp.cutoff', exp_ramp(intro.start, verse.start, 400, 8000), riser(chorus.start, 4, 300, 12000))
    pad.automate('instrument.cutoff', lfo(verse.start, verse.end, 300, 2400, period='1/2', log=True))
    pad.automate('fx.chorus.mix', per_section({intro: 0.2, verse: 0.4, chorus: 0.5}, glide=2))
    lead = s.track('lead', inst.dx7('E.PIANO 1'), sends={'hall': -14}, pan=0.2)
    lead.play(s.motif('1:1/8 3:1/8 5:1/4 r:1/4 8:1/2 7:1/4 5:1/4 3:1/2 _:1/2').clip(octave=5), chorus)
    lead.automate('send.hall', ramp(chorus.start, chorus.end, -20, -8))
    s.sidechain(pad, bass, key=kit, pitches='kick', depth=9)
    s.master.add(fx.limiter(gain=3))
    return s


class Structure(unittest.TestCase):
    def setUp(self):
        self.song = small_song()
        self.r = self.song.compile()

    def test_top_level(self):
        r = self.r
        self.assertEqual(r['format'], 'agentsound.render')
        self.assertEqual(r['version'], 1)
        self.assertEqual(r['tempo'], 104.0)
        self.assertEqual(r['lengthBeats'], 80.0)
        self.assertEqual(r['seed'], 7)
        self.assertEqual(set(r), {'format', 'version', 'title', 'sampleRate', 'tempo', 'lengthBeats', 'tailSeconds',
                                  'seed', 'sections', 'tracks', 'buses', 'master', 'export'})
        self.assertEqual(r['sections'], [{'name': 'intro', 'startBeat': 0.0, 'endBeat': 16.0},
                                         {'name': 'verse', 'startBeat': 16.0, 'endBeat': 48.0},
                                         {'name': 'chorus', 'startBeat': 48.0, 'endBeat': 80.0}])
        self.assertEqual(r['export'], {'stems': False, 'bitDepth': 24})
        self.assertEqual(r['master']['fx'], [{'type': 'limiter', 'params': {'gain': 3}}])

    def test_ids_and_keys(self):
        ids = [t['id'] for t in self.r['tracks']] + [b['id'] for b in self.r['buses']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(ID_RE.match(i) for i in ids))
        track_keys = {'id', 'instrument', 'fx', 'gainDb', 'pan', 'mute', 'output', 'sends', 'notes', 'automation'}
        for t in self.r['tracks']:
            self.assertTrue(set(t) <= track_keys, set(t) - track_keys)
            self.assertIn(t['output'], {'master'} | {b['id'] for b in self.r['buses']})
        for b in self.r['buses']:
            self.assertTrue(set(b) <= {'id', 'fx', 'gainDb', 'pan', 'mute', 'output', 'sends', 'automation'})

    def test_notes_format(self):
        L = self.r['lengthBeats']
        for t in self.r['tracks']:
            prev = None
            for n in t['notes']:
                self.assertEqual(len(n), 4)
                start, dur, pitch, vel = n
                self.assertIsInstance(start, float)
                self.assertIsInstance(dur, float)
                self.assertIs(type(pitch), int)
                self.assertIs(type(vel), int)
                self.assertTrue(0 <= start < L)
                self.assertGreater(dur, 0)
                self.assertTrue(0 <= pitch <= 127 and 1 <= vel <= 127)
                if prev is not None:
                    self.assertLessEqual(prev, (start, pitch))
                prev = (start, pitch)

    def test_automation_sorted_and_resolved(self):
        pad = next(t for t in self.r['tracks'] if t['id'] == 'pad')
        targets = [a['target'] for a in pad['automation']]
        self.assertEqual(targets, ['fx.1.cutoff', 'instrument.cutoff', 'fx.0.mix'])
        for t in self.r['tracks'] + self.r['buses']:
            for a in t['automation']:
                beats = [p[0] for p in a['points']]
                self.assertTrue(all(b > a_ for a_, b in zip(beats, beats[1:])), a['target'])
                for p in a['points']:
                    self.assertIn(len(p), (2, 3))
                    if len(p) == 3:
                        self.assertIn(p[2], ('exp', 'smooth', 'step'))
        lead = next(t for t in self.r['tracks'] if t['id'] == 'lead')
        self.assertEqual(lead['automation'][0]['target'], 'send.hall')

    def test_sidechain_ghost_key(self):
        ghost = next(t for t in self.r['tracks'] if t['id'] == 'drums-key')
        self.assertTrue(ghost['mute'])
        self.assertTrue(ghost['notes'])
        self.assertEqual({n[2] for n in ghost['notes']}, {36})
        drums_t = next(t for t in self.r['tracks'] if t['id'] == 'drums')
        self.assertEqual(len(ghost['notes']), sum(1 for n in drums_t['notes'] if n[2] == 36))
        pad = next(t for t in self.r['tracks'] if t['id'] == 'pad')
        self.assertEqual(pad['fx'][-1], {'type': 'ducker', 'params': {'depth': 9}, 'sidechain': 'drums-key'})
        self.assertNotIn('mute', drums_t)

    def test_deterministic_and_seeded(self):
        self.assertEqual(json.dumps(small_song().compile()), json.dumps(small_song().compile()))
        a = next(t for t in small_song(1).compile()['tracks'] if t['id'] == 'drums')['notes']
        b = next(t for t in small_song(2).compile()['tracks'] if t['id'] == 'drums')['notes']
        self.assertNotEqual(a, b)

    def test_dumps_roundtrip(self):
        text = dumps(self.r)
        self.assertEqual(json.loads(text), self.r)
        self.assertIn('\n        [16.', text)  # one note per line

    def test_describe(self):
        d = self.song.describe()
        self.assertIn('verse', d)
        self.assertIn('ducker<-drums-key', d)


class Sections(unittest.TestCase):
    def test_coordinates(self):
        s = Song('x', tempo=120, time_sig='3/4')
        a = s.section('a', bars=4)
        b = s.section('b', bars=2)
        self.assertEqual((a.start, a.end, a.length), (0.0, 12.0, 12.0))
        self.assertEqual((b.start, b.end), (12.0, 18.0))
        self.assertEqual(b.bar(1), 15.0)
        self.assertEqual(b.bar(1, beat=2), 17.0)
        self.assertEqual(b.bar(-1), 15.0)
        self.assertEqual(a.beat(-2), 10.0)
        self.assertEqual(a.bar_starts(2), [0.0, 6.0])
        self.assertEqual(s.length, 18.0)
        self.assertEqual(s['b'], b)
        self.assertIn(13, b)
        with self.assertRaises(ComposeError):
            b.bar(3)
        with self.assertRaises(ComposeError):
            s.section('a', 2)
        with self.assertRaises(ComposeError):
            s['nope']

    def test_placement_in_section_coordinates(self):
        s = Song('x', tempo=120)
        s.section('intro', 2)
        v = s.section('verse', 4)
        t = s.track('t', inst.va())
        t.note('A4', v.bar(1, 2), dur=1)
        t.play(chord('Am'), v)
        t.loop(drums({'kick': 'x...'}), v.bar(2), bars=1)
        notes = s.compile()['tracks'][0]['notes']
        self.assertIn([14.0, 1.0, 69, 100], notes)
        self.assertEqual(sorted({n[0] for n in notes if n[2] == 36}), [16.0, 17.0, 18.0, 19.0])
        self.assertEqual(min(n[0] for n in notes), 8.0)


class Errors(unittest.TestCase):
    def base(self):
        s = Song('x', tempo=120)
        s.section('a', 2)
        return s

    def test_cycle_detection(self):
        s = self.base()
        a = s.bus('a')
        b = s.bus('b', output=a)
        a.send(b, -6)
        s.track('t', inst.va()).to(a).note(60, 0)
        with self.assertRaisesRegex(ComposeError, r'routing cycle: .*a.*b'):
            s.compile()

    def test_sidechain_cycle(self):
        s = self.base()
        grp = s.bus('grp')
        t = s.track('t', inst.va(), output=grp).note(60, 0)
        t.add_fx(FX('compressor', sidechain=grp))
        with self.assertRaisesRegex(ComposeError, 'routing cycle'):
            s.compile()

    def test_bad_routes(self):
        s = self.base()
        s.track('t', inst.va(), sends={'nobus': -6}).note(60, 0)
        with self.assertRaisesRegex(ComposeError, "no bus 'nobus'"):
            s.compile()
        s = self.base()
        s.track('u', inst.va()).note(60, 0)
        s.track('t', inst.va(), output='u').note(60, 0)
        with self.assertRaisesRegex(ComposeError, "is a track"):
            s.compile()
        s = self.base()
        s.track('t', inst.va(), fx=[fx.compressor(sidechain='ghost')]).note(60, 0)
        with self.assertRaisesRegex(ComposeError, 'sidechain'):
            s.compile()

    def test_bad_ids(self):
        s = self.base()
        with self.assertRaisesRegex(ComposeError, "'lead_synth'"):
            s.track('Lead Synth', inst.va())
        s.track('lead', inst.va())
        with self.assertRaises(ComposeError):
            s.bus('lead')
        with self.assertRaises(ComposeError):
            s.bus('master')

    def test_notes_out_of_song_point_to_call_site(self):
        s = self.base()
        t = s.track('t', inst.va())
        t.note(60, 7.5)
        t.note(60, 8)
        with self.assertRaisesRegex(ComposeError, r"after the song end.*|placed at test_song.py:\d+"):
            s.compile()
        try:
            s.compile()
        except ComposeError as e:
            self.assertIn('test_song.py:', str(e))

    def test_automation_targets(self):
        s = self.base()
        t = s.track('t', inst.va(), fx=[fx.filter(), fx.filter()]).note(60, 0)
        with self.assertRaisesRegex(ComposeError, "instrument.cutoff"):
            t.automate('cutoff', ramp(0, 4, 1, 2))
        with self.assertRaisesRegex(ComposeError, 'gainDb'):
            t.automate('gain', ramp(0, 4, 1, 2))
        t.automate('fx.filter.cutoff', ramp(0, 4, 100, 200))
        with self.assertRaisesRegex(ComposeError, 'ambiguous'):
            s.compile()
        s = self.base()
        t = s.track('t', inst.va()).note(60, 0)
        t.automate('fx.3.mix', ramp(0, 4, 0, 1))
        with self.assertRaisesRegex(ComposeError, 'no fx #3'):
            s.compile()
        s = self.base()
        t = s.track('t', inst.va()).note(60, 0)
        t.automate('send.hall', ramp(0, 4, -20, -10))
        with self.assertRaisesRegex(ComposeError, 'no send'):
            s.compile()
        s = self.base()
        t = s.track('t', inst.va()).note(60, 0)
        t.automate('gainDb', ramp(0, 4, -200, 0))
        with self.assertRaisesRegex(ComposeError, 'outside'):
            s.compile()
        with self.assertRaises(ComposeError):
            s.bus('b').automate('instrument.cutoff', ramp(0, 1, 1, 2))
        with self.assertRaises(ComposeError):
            s.master.automate('pan', ramp(0, 1, 0, 1))

    def test_song_args(self):
        for kw in ({'tempo': 10}, {'tempo': 400}, {'sample_rate': 22050}, {'seed': -1}, {'time_sig': '4-4'},
                   {'tail': 60}, {'key': 'H minor'}):
            with self.assertRaises(ComposeError, msg=kw):
                Song('x', **kw)
        with self.assertRaises(ComposeError):
            Song('x').compile()


class PatchesInSongs(unittest.TestCase):
    def test_patch_defaults_merge(self):
        p = Patch('test/lead', {'type': 'va', 'params': {'cutoff': 3000}}, fx=[fx.chorus(mix=0.3)],
                  gain_db=-4, pan=0.1, sends={'hall': -12, 'echo': -18})
        s = Song('x')
        s.section('a', 1)
        s.hall()
        t = s.track('lead', p.but(cutoff=2000), fx=[fx.delay(mix=0.2)], gain_db=-2).note(60, 0)
        r = s.compile()
        tr = r['tracks'][0]
        self.assertEqual(tr['instrument'], {'type': 'va', 'params': {'cutoff': 2000}})
        self.assertEqual([f['type'] for f in tr['fx']], ['chorus', 'delay'])
        self.assertEqual(tr['gainDb'], -6.0)
        self.assertEqual(tr['pan'], 0.1)
        self.assertEqual(tr['sends'], {'hall': -12.0})
        self.assertTrue(any("'echo' dropped" in w for w in s.warnings))
        self.assertEqual(t.patch, 'test/lead')

    def test_chain_patch_on_bus_and_tempo_ducker(self):
        chain = Patch('bus/test_verb', fx=[fx.reverb(type='plate', mix=1.0)], gain_db=-3)
        s = Song('x')
        s.section('a', 1)
        b = s.bus('verb', chain)
        t = s.track('t', inst.va(), sends={b: -10}).note(60, 0).duck(rate=1, depth=6)
        r = s.compile()
        self.assertEqual(r['buses'][0]['fx'], [{'type': 'reverb', 'params': {'type': 'plate', 'mix': 1.0}}])
        self.assertEqual(r['buses'][0]['gainDb'], -3.0)
        self.assertEqual(r['tracks'][0]['fx'][-1], {'type': 'ducker', 'params': {'mode': 'tempo', 'rate': 1, 'depth': 6}})
        self.assertEqual(t.id, 't')  # duck() chains
        with self.assertRaises(ComposeError):
            s.track('u', chain)


class KeyedGatedReverb(unittest.TestCase):
    BEAT = {'kick': 'x...x...x...x...', 'snare': '....x.......x..o', 'hat': 'x.x.x.x.x.x.x.x.'}

    def song(self):
        s = Song('g', tempo=100)
        s.section('a', bars=2)
        kit = s.track('drums', inst.drums(kit='synthwave'), sends={'gated': -6})
        kit.loop(drums(self.BEAT), s['a'])
        s.master.add(fx.limiter())
        return s, kit

    @staticmethod
    def gate_fx(r, bus='gated'):
        b = next(b for b in r['buses'] if b['id'] == bus)
        return next(f for f in b['fx'] if f['type'] == 'gatedreverb')

    def test_keyed_from_snare_notes(self):
        s, kit = self.song()
        bus = s.gated(gain_db=-2, hold=250, key=kit, pitches='snare')
        r = s.compile()
        g = self.gate_fx(r)
        self.assertEqual(g['sidechain'], 'drums-key')
        self.assertEqual(g['params']['hold'], 250)
        ghost = next(t for t in r['tracks'] if t['id'] == 'drums-key')
        self.assertTrue(ghost['mute'])
        self.assertEqual({n[2] for n in ghost['notes']}, {38})          # snare only, ghost notes included
        self.assertEqual(len(ghost['notes']), 6)
        self.assertEqual(ghost['instrument'], r['tracks'][0]['instrument'])
        self.assertEqual(bus.id, 'gated')
        self.assertIn('gatedreverb<-drums-key', s.describe())

    def test_key_forms_and_reuse(self):
        s, kit = self.song()
        s.gated(key='drums')                                              # whole track as key
        self.assertEqual(self.gate_fx(s.compile())['sidechain'], 'drums')
        s2, kit2 = self.song()
        b = s2.gated()                                                    # created first, keyed later
        self.assertIs(s2.gated(key=kit2, pitches=['snare', 'clap']), b)
        self.assertEqual(self.gate_fx(s2.compile())['sidechain'], 'drums-key')
        self.assertIs(s2.gated(key=kit2, pitches=['clap', 'snare']), b)   # same key again: fine
        s2.sidechain(s2.track('pad', inst.va()).note(60, 0), key=kit2, pitches='kick')
        r = s2.compile()
        ids = {t['id'] for t in r['tracks']}
        self.assertTrue({'drums-key', 'drums-key2'} <= ids)              # separate ghosts per pitch set
        self.assertEqual({n[2] for n in next(t for t in r['tracks'] if t['id'] == 'drums-key')['notes']}, {38})

    def test_errors(self):
        s, kit = self.song()
        with self.assertRaises(ComposeError):
            s.gated(pitches='snare')                                      # pitches need a key track
        s.gated(key=kit, pitches='snare')
        with self.assertRaises(ComposeError):
            s.gated(key=kit, pitches='clap')                              # already keyed from another source
        with self.assertRaises(ComposeError):
            s.gated(key=kit, pitches='snare', hold=100)                   # params only on first creation
        self.assertEqual(len(s._ghosts), 1)                               # failed calls leave no ghost track
        s3, kit3 = self.song()
        s3.bus('gated', [fx.reverb(mix=1.0)])
        with self.assertRaises(ComposeError):
            s3.gated(key=kit3)                                            # no gatedreverb to key
        s4, _ = self.song()
        with self.assertRaises(ComposeError):
            s4.gated(key='nothing', pitches='snare')                      # key track must exist
        with self.assertRaises(ComposeError):
            s4.gated(key='gated')                                         # can't key itself
        self.assertEqual(s4.buses, {})                                    # ... and nothing was created


if __name__ == '__main__':
    unittest.main()
