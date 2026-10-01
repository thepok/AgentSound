"""Hero leads: song.carve (a keyed dynamic EQ: band-mode compressor), vibrato on every sampler layer of a stack,
articulation.throws (echo throws at phrase ends), the layered/hero_sax + bus/hero_plate library entries
(agentsound/patches/hero.py) and THE hero wrapper (agentsound.heroes: presets, the shared chain with its 'air' breath
stage, the mix rules and their switches, the old hero patches pinned unchanged, determinism, the songs that use
them). Synthetic .sfz / .wav in a temp folder; the library checks do not need the samples (packs that are missing
skip the compile checks; the air-stage render needs the built engine)."""

import math
import pathlib
import shutil
import struct
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import array  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402

from agentsound import Clip, Song, cli, heroes, library, patches  # noqa: E402
from agentsound import articulation as art  # noqa: E402
from agentsound.patches import hero, inst, layer  # noqa: E402
from agentsound.song import dumps  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]


def _wav(path: pathlib.Path, freq: float = 440.0, seconds: float = 0.5, sr: int = 48000):
    n = int(seconds * sr)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b''.join(struct.pack('<h', int(12000 * math.sin(2 * math.pi * freq * i / sr))) for i in range(n)))


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_hero_'))
        self.addCleanup(shutil.rmtree, self.dir, True)
        _wav(self.dir / 'a.wav')
        (self.dir / 'x.sfz').write_text('<region> sample=a.wav lokey=40 hikey=90 pitch_keycenter=69\n', encoding='utf-8')

    def sampler(self):
        return inst.sfz(str(self.dir / 'x.sfz'), mono='legato')


class Carve(Base):
    def test_carve_adds_a_keyed_band_compressor(self):
        s = Song('c', tempo=120)
        a = s.section('a', bars=2)
        lead = s.track('lead', self.sampler())
        bed = s.track('bed', inst.va())
        keys = s.track('keys', inst.va())
        lead.note('A4', a.start, 4)
        bed.note('C4', a.start, 8)
        keys.note('E4', a.start, 8)
        s.carve(bed, keys, key=lead, freq=2400, q=0.8, depth=5, release=300)
        r = s.compile()
        for tid in ('bed', 'keys'):
            t = next(x for x in r['tracks'] if x['id'] == tid)
            c = t['fx'][-1]
            self.assertEqual(c['type'], 'compressor')
            self.assertEqual(c['sidechain'], 'lead')
            self.assertEqual(c['params']['band'], 2400)
            self.assertEqual(c['params']['bandq'], 0.8)
            self.assertEqual(c['params']['range'], 5)
            self.assertEqual(c['params']['release'], 300)
        with self.assertRaises(ComposeError):
            s.carve(key=lead)
        with self.assertRaises(ComposeError):
            s.carve(lead, key=lead)


class StackVibrato(Base):
    def test_vibrato_reaches_every_sampler_layer(self):
        s = Song('v', tempo=120)
        a = s.section('a', bars=2)
        t = s.track('sax', inst.stack(layer(self.sampler(), 'main'), layer(self.sampler(), 'dbl', level=-10, fine=8),
                                      layer(inst.va(), 'synth', level=-20)))
        self.assertEqual(art.vibrato_prefixes(t), ['instrument.layers.main', 'instrument.layers.dbl'])
        line = Clip([(0, 0.5, 'C5', 100), (0.5, 3, 'E5', 110)], length=8)
        art.perform(t, line, a, vib=dict(depth=20))
        targets = {x[0] for x in t._auto}
        self.assertIn('instrument.layers.main.vibrato', targets)
        self.assertIn('instrument.layers.dbl.vibratorate', targets)
        self.assertNotIn('instrument.vibrato', targets)
        r = s.compile()
        lanes = {x['target'] for x in r['tracks'][0]['automation']}
        self.assertIn('instrument.layers.main.vibrato', lanes)
        # a plain sampler keeps the plain target; a synth has none
        self.assertEqual(art.vibrato_prefixes(s.track('solo', self.sampler())), ['instrument'])
        self.assertEqual(art.vibrato_prefixes(s.track('synth', inst.va())), [])


class Throws(Base):
    def test_throws_on_phrase_ends_only(self):
        s = Song('t', tempo=120)
        a = s.section('a', bars=4)
        echo = s.echo()
        t = s.track('sax', self.sampler(), sends={echo: -22})
        # 8ths into a held note (beats 1-3.5: only half a beat of rest after it), a phrase ending on beat 6 (a beat of
        # rest after it), the last held note at 8
        line = Clip([(0, .5, 'C5'), (.5, .5, 'D5'), (1, 2.5, 'E5'), (4, .5, 'C5'), (4.5, .5, 'D5'), (5, 1, 'E5'),
                     (6, 1, 'F5'), (8, 3, 'G5')], length=16)
        ends = art.throws(t, line, a, bus=echo, throw=-8)
        self.assertEqual([n.start for n in ends], [6.0, 8.0])
        pts = next(lane for tg, lane in t._auto if tg == 'send.echo')
        vals = [p[1] for p in pts]
        self.assertEqual(min(vals), -22.0)                 # the base: the track's static send
        self.assertEqual(max(vals), -8.0)
        self.assertTrue(all(pts[i][0] <= pts[i + 1][0] for i in range(len(pts) - 1)))
        back = [p[0] for p in pts if p[1] == -22.0 and p[0] > 6.0]
        self.assertTrue(back and back[0] < 8.0)            # the send is down again before the next phrase starts
        self.assertEqual([n.start for n in art.throws(t, line, a, bus=echo, min_rest=0.5)], [1.0, 6.0, 8.0])
        s.compile()


class Library(unittest.TestCase):
    def test_hero_sax_patch(self):
        p = patches.get('layered/hero_sax')
        self.assertEqual(p.instrument.type, 'stack')
        ids = [x.id for x in p.instrument.layers]
        self.assertEqual(ids[0], 'sax')
        for i in ('dbl_l', 'dbl_r', 'octave'):
            self.assertIn(i, ids)
        self.assertEqual([f.type for f in p.fx][:3], ['eq', 'compressor', 'saturator'])
        self.assertIn('Measured -18.0 LUFS', p.notes)
        self.assertEqual(set(p.sends), {'plate', 'hall', 'echo'})
        # the doubles: detuned, late, panned apart, well under the lead
        dl, dr = (next(x for x in p.instrument.layers if x.id == i) for i in ('dbl_l', 'dbl_r'))
        self.assertLess(dl.params['pan'] * dr.params['pan'], 0)
        for d in (dl, dr):
            self.assertLessEqual(d.params['level'], -8)
            self.assertTrue(5 <= abs(d.params['fine']) <= 12)
            self.assertTrue(12 <= d.params['delay'] <= 30)
        # the data the hero wrapper will read
        for k in ('source', 'double', 'eq', 'comp', 'drive', 'presence', 'space', 'mix'):
            self.assertIn(k, hero.HERO_SAX)
        self.assertTrue(patches.has('bus/hero_plate'))
        self.assertIsNone(patches.get('bus/hero_plate').instrument)


# ------------------------------------------------------------------------------------------------ the hero wrapper

PRESETS = {'sax', 'piano', 'piano_pop', 'piano_strings', 'guitar', 'guitar_clean', 'guitar_heavy', 'synth',
           'darksynth', 'piano_synth', 'strings', 'brass', 'woodwind', 'voice', 'organ', 'generic'}
FAMILIES = {'sax', 'piano', 'guitar', 'synth', 'piano_synth', 'strings', 'brass', 'woodwind', 'voice', 'organ',
            'generic'}

# The hero patches that existed before the wrapper, pinned: a digest of their definition (instrument params, layers,
# fx, gain, pan, sends; lazy sample specs by path, sample root and caller file left out) taken before they were
# re-expressed as presets of agentsound.heroes. A change here changes their sound: bump the module's VERSION, say so
# in the notes and update the digest.
LEGACY = {
    'layered/hero_sax': '35b8de3a5891dfaa',
    'bus/hero_plate': 'b3a0ebea156d975d',
    'sampled/hero_piano': 'eeaa092142450e02',
    'sampled/hero_piano_pop': 'ac2ecfbba6c4c5eb',
    'layered/hero_piano_strings': 'fed7abfc43adc3a3',
    'layered/hero_guitar': '8c1c62bbb46f3c3a',
    'sampled/hero_guitar_clean': '6642d2f797248196',
    'layered/hero_guitar_heavy': '5992b02dd31ebed8',
    'hero/synth_lead': '9fd515a86ade6c09',
    'hero/synth_piano': '51b64ff5ea088fe4',
    'hero/darksynth_lead': 'd746426739d3adf0',
}


def _canon(x):
    root = library.SAMPLES.as_posix()
    if isinstance(x, patches.Patch):
        return {'instrument': _canon(x.instrument), 'fx': [_canon(f) for f in x.fx], 'gain_db': x.gain_db,
                'pan': x.pan, 'sends': dict(sorted(x.sends.items()))}
    if isinstance(x, patches.Instrument):
        lazy = {k: v for k, v in (x.lazy or {}).items() if k != 'caller'} if x.lazy else None
        return {'type': x.type, 'params': _canon(x.params), 'lazy': _canon(lazy)}
    if isinstance(x, patches.Layer):
        return {'id': x.id, 'instrument': _canon(x.instrument), 'fx': [_canon(f) for f in x.fx],
                'params': _canon(x.params)}
    if isinstance(x, patches.FX):
        return {'type': x.type, 'name': x.name, 'params': _canon(x.params)}
    if isinstance(x, dict):
        return {str(k): _canon(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
    if isinstance(x, (list, tuple)):
        return [_canon(v) for v in x]
    if isinstance(x, str):
        return x.replace(root, '<SAMPLES>')
    return x


def _digest(p) -> str:
    return hashlib.sha256(json.dumps(_canon(p), sort_keys=True).encode()).hexdigest()[:16]


def _compile_or_skip(test, s):
    try:
        return s.compile()
    except ComposeError as e:
        if 'is not installed' in str(e) or 'samples fetch' in str(e):
            test.skipTest(f'sample pack missing: {e}')
        raise


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


class WrapperPresets(unittest.TestCase):
    def test_presets_register(self):
        self.assertEqual(set(heroes.presets()), PRESETS)
        self.assertEqual({heroes.get_preset(n).family for n in PRESETS}, FAMILIES)
        for n in PRESETS:
            with self.subTest(preset=n):
                p = patches.get(f'hero/{n}')                # the unified name of every preset
                self.assertIsNotNone(p.instrument)
                self.assertIn('Measured -18.0 LUFS', p.notes)
                self.assertTrue(p.fx and p.fx[-1].type == 'utility' and p.fx[-1].name == 'air',
                                f'{n}: the air stage is the last fx')
        for alias, name in (('violin', 'strings'), ('trumpet', 'brass'), ('flute', 'woodwind'), ('choir', 'voice'),
                            ('synth_lead', 'synth'), ('synth_piano', 'piano_synth'), ('hero/sax', 'sax'),
                            ('darksynth_lead', 'darksynth'), ('hammond', 'organ')):
            self.assertEqual(heroes.get_preset(alias).name, name)
        with self.assertRaises(ComposeError):
            heroes.get_preset('bagpipe')

    def test_legacy_patches_unchanged(self):
        for name, dig in LEGACY.items():
            with self.subTest(patch=name):
                self.assertEqual(_digest(patches.get(name)), dig)
        # the unified names are the same sound + the air stage (0 dB, last): instrument and the other fx identical
        for n, p in heroes.PRESETS.items():
            if not p.patch:
                continue
            with self.subTest(preset=n):
                old, new = patches.get(p.patch), patches.get(p.canonical)
                self.assertFalse(any(f.name == 'air' for f in old.fx))
                self.assertEqual(new.fx[:-1], old.fx)
                self.assertEqual(new.fx[-1].params, {'gain': 0.0})
                self.assertEqual(_canon(new.instrument), _canon(old.instrument))
                self.assertEqual((new.gain_db, new.sends), (old.gain_db, old.sends))

    def test_every_family_builds_on_its_default(self):
        for n in sorted(PRESETS):
            with self.subTest(preset=n):
                p = heroes.PRESETS[n]
                built = heroes.build(n)
                self.assertEqual(_canon(built), _canon(patches.get(p.canonical)))   # (the notes differ)
                comps = [f for f in built.fx if f.type == 'compressor' and f.name != 'catch']
                for c in comps:                     # the dynamics ear: slow attacks, moderate ratios
                    self.assertGreaterEqual(c.params.get('attack', 0), 15, n)
                    self.assertLessEqual(c.params.get('ratio', 1), 3.0, n)
                s = Song('fam', tempo=100, key='A minor', seed=1)
                a = s.section('a', bars=1)
                for b in built.sends:
                    {'hall': s.hall, 'plate': s.plate, 'echo': s.echo}[b]()
                t = s.track('lead', built)
                t.note('A4', a.start, 1, vel=90).note('C5', a.start + 1, 2, vel=110)
                if n in ('synth', 'darksynth'):
                    s.compile()                     # the pure synth heroes need no samples
                else:
                    _compile_or_skip(self, s)

    def test_new_families_are_plain_samplers_with_options(self):
        for n in ('strings', 'brass', 'woodwind', 'voice', 'organ', 'generic'):
            with self.subTest(preset=n):
                p = patches.get(f'hero/{n}')
                self.assertEqual(p.instrument.type, 'sampler')     # articulations / glides keep working
                self.assertEqual(p.gain_db, heroes.PRESETS[n].gain_db + patches.get(heroes.PRESETS[n].sound).gain_db)
        st = heroes.build('strings', double='takes', octave=True)
        self.assertEqual([x.id for x in st.instrument.layers], ['lead', 'section', 'octave'])
        br = heroes.build('brass', double='takes')
        ids = {x.id: x for x in br.instrument.layers}
        self.assertLess(ids['dbl_l'].params['pan'] * ids['dbl_r'].params['pan'], 0)
        sh = heroes.build('brass', double='shift')
        self.assertEqual(sh.instrument.type, 'sampler')
        self.assertIn('microshift', [f.type for f in sh.fx])
        with self.assertRaises(ComposeError):
            heroes.build('brass', double='triple')

    def test_wrapping_another_sound(self):
        log: list = []
        p = heroes.build('brass', 'sampled/trumpet', log=log)
        self.assertEqual(p.name, 'hero/brass+trumpet')
        self.assertEqual(p.instrument, patches.get('sampled/trumpet').instrument)
        self.assertTrue(any('source: sampled/trumpet' in x for x in log))
        self.assertIn('hero(', p.notes)
        # the sax takes belong to the sax's own source: around another sound they become a micro-pitch double
        tl: list = []
        t = heroes.build('sax', 'sampled/tenor_sax', octave=False, log=tl)
        self.assertEqual(t.instrument.type, 'sampler')
        self.assertIn('microshift', [f.type for f in t.fx])
        self.assertTrue(any("-> 'shift'" in x for x in tl))
        # the family is inferred from the name
        self.assertEqual(heroes.infer('sampled/solo_violin').name, 'strings')
        self.assertEqual(heroes.infer('sampled/trumpet_section').name, 'brass')
        self.assertEqual(heroes.infer('layered/hero_sax').name, 'sax')
        self.assertEqual(heroes.infer('synthwave/supersaw_lead').name, 'synth')
        self.assertEqual(heroes.infer(inst.va()).name, 'synth')
        self.assertEqual(heroes.hero('sampled/solo_flute').name, 'hero/woodwind')     # the preset's own default
        self.assertEqual(heroes.hero('sampled/flute').name, 'hero/woodwind+flute')
        with self.assertRaises(ComposeError):
            heroes.hero()
        with self.assertRaises(ComposeError):
            heroes.hero('sampled/trumpet', bed=['pad'])      # mix rules need the track
        # a layered sound (another hero's stack) is wrapped whole: the chain after its own, no extra layers
        g = heroes.build('generic', 'layered/hero_guitar')
        old = patches.get('layered/hero_guitar')
        self.assertEqual(_canon(g.instrument), _canon(old.instrument))
        self.assertEqual(g.fx[:len(old.fx)], old.fx)
        self.assertEqual(g.fx[-1].name, 'air')
        with self.assertRaises(ComposeError):
            heroes.build('generic', 'layered/hero_guitar', octave=True)
        # a track holding a variant of the family keeps that variant
        s = Song('var', tempo=100)
        s.section('a', bars=1)
        t = heroes.hero(s.track('piano', 'sampled/hero_piano_pop'), family='piano', space=False)
        self.assertEqual((t.hero.preset.name, t.patch), ('piano_pop', 'hero/piano_pop'))


class WrapperMixRules(Base):
    def song(self, **kw):
        s = Song('mix', tempo=120, key='A minor', seed=3)
        verse = s.section('verse', bars=2)
        chorus = s.section('chorus', bars=2)
        pad = s.track('pad', inst.va())
        strings = s.track('strings', inst.va())
        keys = s.track('keys', inst.va())
        for t in (pad, strings, keys):
            t.note('A3', 0, 16)
        lead = heroes.hero(s.track('lead', self.sampler()), family='strings', bed=[pad, strings],
                           competitors=[keys], **kw)
        line = Clip([(0, 1, 'A4', 90), (1, 2, 'C5', 100), (4, 0.5, 'E5', 80), (4.5, 2.5, 'D5', 110)], length=8)
        lead.play(line, verse).play(line, chorus)
        return s, lead, pad, strings, keys

    def test_applies_and_logs_the_mix_rules(self):
        s, lead, pad, strings, keys = self.song(genre='film')
        for bed in (pad, strings):
            duck = [f for f in bed.fx if f.type == 'ducker']
            carve = [f for f in bed.fx if f.type == 'compressor' and 'band' in f.params]
            self.assertEqual([f.sidechain for f in duck], ['lead'])
            self.assertEqual(duck[0].params['depth'], 1.5)             # the film profile's bed duck
            self.assertEqual([f.sidechain for f in carve], ['lead'])
            self.assertEqual(carve[0].params['band'], heroes.PRESETS['strings'].mix['carve_freq'])
        dip = [f for f in keys.fx if f.name == 'hero_dip']
        self.assertEqual(len(dip), 1)
        self.assertLess(dip[0].params['peak1.gain'], 0)
        names = [f.name for f in lead.fx]
        self.assertIn('air', names)
        self.assertIn('hero_ride', names)
        self.assertEqual(lead.patch, 'hero/strings+lead')
        self.assertIn('hero_plate', s.buses)
        self.assertIn('echo', s.buses)
        r = s.compile()
        t = next(x for x in r['tracks'] if x['id'] == 'lead')
        lanes = {a['target']: a['points'] for a in t['automation']}
        ride_idx = names.index('hero_ride')
        self.assertIn(f'fx.{ride_idx}.gain', lanes)
        ride = lanes[f'fx.{ride_idx}.gain']
        self.assertEqual(max(p[1] for p in ride), 1.0)                 # +1 dB in the chorus (film ride)
        self.assertEqual(min(p[1] for p in ride), 0.0)
        self.assertIn('send.echo', lanes)                              # the throws
        self.assertGreater(max(p[1] for p in lanes['send.echo']), min(p[1] for p in lanes['send.echo']))
        text = '\n'.join(heroes.log_lines(s))
        for word in ('sound:', 'space: plate', 'space: echo', 'duck:', 'carve:', 'dips:', 'ride: +1 dB in chorus',
                     'throws:'):
            self.assertIn(word, text)
        self.assertIs(lead.hero.preset, heroes.PRESETS['strings'])
        with self.assertRaises(ComposeError):
            heroes.hero(lead, family='strings')                     # once per track
        # the mixer knows the hero is the lead
        from agentsound import mixer
        roles, why = mixer.infer_roles(s)
        self.assertEqual((roles['lead'], why['lead']), ('lead', 'hero()'))

    def test_genre_profiles_and_disables(self):
        s, lead, pad, strings, keys = self.song(genre='rock')        # rock: no bed duck
        self.assertFalse(any(f.type == 'ducker' for f in pad.fx))
        self.assertTrue(any('duck: off' in x for x in lead.hero.log))
        s, lead, pad, strings, keys = self.song(genre='jazz')        # jazz: no lead ride
        self.assertNotIn('hero_ride', [f.name for f in lead.fx])
        s, lead, pad, strings, keys = self.song(duck=False, carve=False, dips=False, ride=False, throws=False,
                                                space=False)
        self.assertEqual(len(pad.fx), 0)
        self.assertEqual(len(keys.fx), 0)
        self.assertEqual(set(s.buses), set())
        r = s.compile()
        t = next(x for x in r['tracks'] if x['id'] == 'lead')
        self.assertFalse(any(a['target'].startswith('send.') for a in t['automation']))
        self.assertNotIn('hero_ride', [f.name for f in lead.fx])
        for word in ('duck: off', 'carve: off', 'dips: off', 'ride: off', 'throws: off', 'space: unchanged'):
            self.assertTrue(any(word in x for x in lead.hero.log), word)
        # depths as numbers
        s, lead, pad, strings, keys = self.song(duck=4, carve=2, dips=1, ride=2)
        self.assertEqual([f.params['depth'] for f in pad.fx if f.type == 'ducker'], [4.0])
        self.assertEqual([f.params['range'] for f in pad.fx if f.type == 'compressor'], [2.0])
        self.assertEqual([f.params['peak1.gain'] for f in keys.fx if f.name == 'hero_dip'], [-1.0])
        self.assertEqual(lead.hero.ride_db, 2.0)
        # chain=False keeps the sound (the air stage is still added), air=False leaves it out
        s = Song('keep', tempo=120)
        s.section('a', bars=1)
        t = s.track('lead', self.sampler())
        ins = t.instrument
        heroes.hero(t, family='brass', chain=False, space=False)
        self.assertIs(t.instrument, ins)
        self.assertEqual([f.name for f in t.fx if f.type == 'utility'], ['air', 'hero_ride'])
        s2 = Song('noair', tempo=120)
        s2.section('a', bars=1)
        t2 = heroes.hero(s2.track('lead', self.sampler()), family='brass', air=False, space=False)
        self.assertNotIn('air', [f.name for f in t2.fx])
        self.assertFalse(any(f.name == 'air' for f in heroes.build('brass', air=False).fx))

    def test_existing_hero_track_keeps_its_sound(self):
        s = Song('sax', tempo=120)
        s.section('chorus', bars=1)
        pad = s.track('pad', inst.va())
        sax = s.track('sax', 'layered/hero_sax')
        heroes.hero(sax, bed=[pad])                                   # the family inferred from the patch
        self.assertEqual(sax.hero.preset.name, 'sax')
        self.assertEqual(sax.patch, 'hero/sax')
        old = patches.get('layered/hero_sax')
        self.assertEqual(sax.instrument, old.instrument)
        self.assertEqual(sax.fx[:len(old.fx)], old.fx)
        self.assertEqual(sax.fx[len(old.fx)].name, 'air')
        self.assertEqual(sax.gain_db, old.gain_db)
        self.assertEqual(sax.sends, {'hero_plate': -14.0, 'echo': -24.0})
        self.assertNotIn('plate', sax._patch_sends)

    def test_play_uses_the_family_player(self):
        s, lead, pad, strings, keys = self.song()
        s2 = Song('play', tempo=120)
        s2.section('a', bars=4)
        t = heroes.hero(s2.track('lead', self.sampler()), family='brass', space=False)
        line = Clip([(0, 1, 'A4'), (1, 1, 'C5'), (2, 3, 'E5'), (6, 2, 'D5')], length=8)
        played = heroes.play(t, line, 0)
        vels = [n.vel for n in played]
        lo, hi = heroes.PRESETS['brass'].play['vel']
        self.assertTrue(all(lo - 1 <= v <= hi + 1 for v in vels), vels)
        self.assertGreater(max(vels) - min(vels), 10)                # arcs, not one level
        self.assertTrue(any(tg.endswith('vibrato') for tg, _ in t._auto))

    def test_air_helper(self):
        s = Song('air', tempo=120)
        s.section('a', bars=1)
        t = heroes.hero(s.track('lead', self.sampler()), family='woodwind', space=False, ride=False)
        heroes.air(t, [(0, 0), (1, 3, 'smooth'), (2, 0, 'smooth')])
        r = s.compile()
        lane = next(a for a in r['tracks'][0]['automation'] if a['target'].endswith('.gain'))
        self.assertEqual(max(p[1] for p in lane['points']), 3)
        with self.assertRaises(ComposeError):
            heroes.air(s.track('plain', self.sampler()), [(0, 1)])


class WrapperDeterminism(Base):
    def build(self):
        s = Song('det', tempo=110, key='D minor', seed=9)
        v = s.section('verse', bars=2)
        c = s.section('chorus', bars=2)
        pad = s.track('pad', inst.va())
        pad.note('D3', 0, 16)
        lead = heroes.hero(s.track('lead', self.sampler()), family='sax', octave=False, bed=[pad])
        line = Clip([(0, 1, 'A4', 90), (1, 2.5, 'C5', 110), (4, 1, 'D5', 80), (5, 2, 'F5', 115)], length=8)
        heroes.play(lead, line, v)
        heroes.play(lead, line, c)
        return s

    def test_same_song_same_render(self):
        a, b = self.build(), self.build()
        ra, rb = dumps(a.compile()), dumps(b.compile())
        self.assertEqual(ra, rb)
        self.assertEqual(dumps(a.compile()), ra)           # compiling again replaces the hero lanes, never adds
        self.assertEqual(_canon(heroes.build('strings')), _canon(heroes.build('strings')))
        self.assertEqual(_canon(heroes.build('sax', 'sampled/tenor_sax')),
                         _canon(heroes.build('sax', 'sampled/tenor_sax')))


class SongsUnchanged(unittest.TestCase):
    """lamplight-avenue (hero/sax = layered/hero_sax + the air stage, played by agentsound.hornist) and
    children-of-neon (no hero) compile with the pinned sounds (LEGACY); hero() adds nothing to them."""

    def load(self, slug):
        song, _ = cli._load_song(REPO / 'songs' / slug / 'song.py')
        cli.apply_module_mix(song)
        return song

    def test_songs_compile_with_the_old_names(self):
        for slug in ('lamplight-avenue', 'children-of-neon'):
            with self.subTest(song=slug):
                try:
                    song = self.load(slug)
                except cli.CliError as e:
                    if 'is not installed' in str(e) or 'samples fetch' in str(e):
                        self.skipTest(f'sample pack missing: {e}')
                    raise
                if slug == 'lamplight-avenue':
                    # since feat/hornist the sax is hero/sax (= layered/hero_sax + the 'air' breath stage) played
                    # by the wind player: the same sound, its air after the compressor, then hornist's 'mic' stage
                    sax = song.tracks['sax']
                    self.assertEqual(sax.patch, 'hero/sax')
                    old = patches.get('layered/hero_sax')
                    self.assertEqual(_canon(sax.instrument), _canon(old.instrument))
                    self.assertEqual(sax.fx[:len(old.fx)], old.fx)
                    self.assertEqual([f.name for f in sax.fx[len(old.fx):]], ['air', 'mic'])
                _compile_or_skip(self, song)
                self.assertEqual(heroes.log_lines(song), [])          # hero() is not called: nothing added


def _read16(path) -> tuple:
    with wave.open(str(path), 'rb') as w:
        ch, sr = w.getnchannels(), w.getframerate()
        a = array.array('h', w.readframes(w.getnframes()))
    return [sum(a[i:i + ch]) / (ch * 32768.0) for i in range(0, len(a), ch)], sr


def _rms_db(x, sr, t0, t1) -> float:
    seg = x[int(t0 * sr):int(t1 * sr)]
    return 10 * math.log10(sum(v * v for v in seg) / len(seg) + 1e-20)


class AirStage(Base):
    """The breath stage survives the hero compression: a 3 dB 'fx.air.gain' push on a held note measures >= 2.5 dB
    at the output; the same push in front of the compressor (instrument.expression) is squashed."""

    def setUp(self):
        super().setUp()
        _wav(self.dir / 'long.wav', seconds=6.0)
        (self.dir / 'long.sfz').write_text('<region> sample=long.wav lokey=40 hikey=90 pitch_keycenter=69\n',
                                           encoding='utf-8')

    def render(self, how: str):
        s = Song(f'air {how}', tempo=60, key='A minor', seed=1, tail=0.5)
        s.section('a', bars=2)
        s.export(bit_depth=16)
        t = heroes.hero(s.track('lead', inst.sfz(str(self.dir / 'long.sfz'), mono='legato')), family='sax',
                        double=False, octave=False, space=False, ride=False, throws=False)
        t.note('A4', 0, 4.5, vel=110)
        if how == 'air':
            heroes.air(t, [(0, 0.0), (2.0, 3.0, 'step')])
        else:
            t.automate('instrument.expression', [(0, 0.8414), (2.0, 1.0, 'step')])   # expression^2: +3 dB
        r = s.compile()
        comps = [f for f in t.fx if f.type == 'compressor']
        self.assertTrue(comps and comps[0].params['ratio'] >= 3)       # the sax's heavy compression is in there
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_air_'))
        self.addCleanup(shutil.rmtree, d, True)
        rj = d / 'song.render.json'
        rj.write_text(dumps(r), encoding='utf-8')
        cli.run_engine(self.engine, rj, d, render=r)
        x, sr = _read16(d / 'mix.wav')
        return _rms_db(x, sr, 2.4, 3.6) - _rms_db(x, sr, 1.1, 1.8)

    def test_air_push_survives_the_compressor(self):
        self.engine = _engine()
        if self.engine is None:
            self.skipTest('engine not built')
        after = self.render('air')
        before = self.render('expression')
        self.assertGreaterEqual(after, 2.5, f'air push measured {after:.2f} dB')
        self.assertLess(before, 2.0, f'the same push before the compressor measured {before:.2f} dB')


if __name__ == '__main__':
    unittest.main()
