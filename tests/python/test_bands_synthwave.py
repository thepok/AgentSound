"""Synthwave band presets (agentsound/bandlib/synthwave.py): every preset builds and compiles, with the installed
sample packs and with none (the synthesized fallbacks), the common options (without / sounds / ids) and the preset
options work, and every demo song under songs/_bands/ compiles with the analysis profile its preset names.
Compile only (no engine needed); the renders and reference comparisons are in the demo songs' docstrings."""

import contextlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agentsound import Song, bands, drums, library  # noqa: E402
from agentsound.bandlib import synthwave as sw  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

PRESETS = ('outrun', 'dreamwave', 'darksynth', 'retrowave', 'scifi')


def _song(tempo=108):
    s = Song('t', tempo=tempo, key='A minor', seed=1)
    a = s.section('a', bars=2)
    return s, a


def _play(band, sec):
    """A note on every role (a kick + snare on the kit), so every track and return renders something."""
    for role, t in band.roles.items():
        if role == 'drums':
            t.loop(drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'}), sec)
        else:
            t.note(57 if role in ('bass',) else 64, sec.start, 4)


def _load_demo(name):
    path = ROOT / 'songs' / '_bands' / name / 'song.py'
    spec = importlib.util.spec_from_file_location(f'_band_demo_{name}', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestSynthwaveBands(unittest.TestCase):
    def test_registered(self):
        self.assertTrue(set(PRESETS) <= set(bands.list('synthwave')))
        for n in PRESETS:
            p = bands.get(n)
            self.assertEqual(p.genre, 'synthwave')
            self.assertIn('drums', p.roles)
            self.assertIn('lead', p.roles)
            self.assertTrue(p.tuned)
            self.assertEqual(p.requires, (), 'every sampled sound has a synthesized fallback')
        text = bands.describe_all('synthwave')
        for n in PRESETS:
            self.assertIn(n, text)

    def test_every_preset_builds_and_compiles(self):
        for n in PRESETS:
            with self.subTest(preset=n):
                s, a = _song()
                b = bands.make(n, s)
                self.assertEqual(set(b.roles), set(bands.get(n).roles))
                self.assertIn(b.analysis['profile'], ('synthwave', 'dreamwave', 'darksynth'))
                self.assertTrue(b.notes.strip())
                self.assertIn('Calibrated', b.notes)
                _play(b, a)
                r = s.compile()
                ids = {t['id'] for t in r['tracks']}
                self.assertTrue(set(b.roles) <= ids)
                # the master chain is the preset's, ending in a limiter
                self.assertEqual(r['master']['fx'][-1]['type'], 'limiter')
                # the kick pumps the bass (ghost key track of the kit's kick)
                bass = next(t for t in r['tracks'] if t['id'] == 'bass')
                self.assertTrue(any(f['type'] == 'ducker' for f in bass['fx']), n)
                self.assertTrue(any(t['id'].startswith('drums-key') for t in r['tracks']), n)
                # the bass is mono in the preset's chain
                self.assertTrue(any(f['type'] == 'utility' and f['params'].get('mono') == 'on' for f in bass['fx']))
                # every send goes to a bus the preset created
                buses = {x['id'] for x in r['buses']}
                for t in r['tracks']:
                    self.assertTrue(set(t.get('sends') or {}) <= buses, (n, t['id']))

    def test_fallbacks_without_sample_packs(self):
        with tempfile.TemporaryDirectory() as empty, mock.patch.object(library, 'SAMPLES', Path(empty)):
            for n in PRESETS:
                with self.subTest(preset=n):
                    s, a = _song()
                    b = bands.make(n, s)
                    self.assertIn('drums', b.info['fallbacks'])
                    self.assertEqual(b.info['packs'], [])
                    self.assertIn('samples fetch', b.notes)
                    # no IR returns without their packs: the algorithmic halls / plates take over
                    for bus in b.buses.values():
                        self.assertFalse(any(f.type == 'convolver' for f in bus.fx), (n, bus.id))
                    _play(b, a)
                    r = s.compile()
                    kit = next(t for t in r['tracks'] if t['id'] == 'drums')
                    self.assertEqual(kit['instrument']['type'], 'drums')

    def test_sampled_sounds_when_installed(self):
        if not sw._have(sw._LINN, sw._909):
            self.skipTest('LinnDrum / TR-909 packs not installed')
        s, a = _song()
        b = bands.outrun(s)
        self.assertEqual(b.info['fallbacks'], {})
        self.assertIn(sw._LINN, b.info['packs'])
        self.assertEqual(b.drums.instrument.type, 'sampler')

    def test_common_options(self):
        s, a = _song()
        b = bands.outrun(s, without=('arp', 'keys'), sounds={'lead': 'synthwave/sync_lead'}, ids={'drums': 'kit'})
        self.assertNotIn('arp', b)
        self.assertNotIn('keys', b)
        self.assertEqual(b.drums.id, 'kit')
        self.assertIn('kit', s.tracks)
        # the replaced sound keeps the role's chain: sync_lead's own eq + microshift, then the role's eq
        types = [f.type for f in b.lead.fx]
        self.assertEqual(types[:2], ['eq', 'microshift'])
        self.assertEqual(types[-1], 'eq')
        self.assertEqual(b.lead.gain_db, 2.0)
        # without the keys (the only plate sender besides the kit) the returns still exist for the kit
        self.assertIn('plate', b)
        _play(b, a)
        s.compile()
        with self.assertRaisesRegex(ComposeError, 'unknown roles'):
            bands.outrun(Song('u', tempo=100), without=('sax',))
        with self.assertRaisesRegex(ComposeError, 'unknown option'):
            bands.outrun(Song('u', tempo=100), lead_sound='x')
        with self.assertRaisesRegex(ComposeError, "lead must be"):
            bands.outrun(Song('u', tempo=100), lead='kazoo')

    def test_sound_override_skips_default_movement(self):
        s, a = _song()
        b = bands.scifi(s, sounds={'pad': 'gm/strings'})
        self.assertEqual(b.pad.instrument.type, 'sf2')
        _play(b, a)
        s.compile()           # the sweep pad's cutoff drift is not applied to a sound without that cutoff

    def test_without_drums_has_no_pump_or_gate(self):
        s, a = _song()
        b = bands.outrun(s, without=('drums',))
        self.assertNotIn('gated', b)
        _play(b, a)
        r = s.compile()
        bass = next(t for t in r['tracks'] if t['id'] == 'bass')
        self.assertFalse(any(f['type'] == 'ducker' for f in bass['fx']))

    def test_existing_bus_is_reused(self):
        s, a = _song()
        hall = s.hall()
        b = bands.outrun(s)
        self.assertIs(b.buses['hall'], hall)

    def test_retrowave_options(self):
        s, a = _song()
        b = bands.retrowave(s, lead='sax', choir='synth')
        _play(b, a)
        s.compile()
        s, a = _song()
        b = bands.retrowave(s, lead='supersaw', choir='vocoder', voice=None)
        self.assertEqual(b.choir.fx[0].type, 'vocoder')
        # the robot choir is keyed by any track; here the kit's rhythm talks through it
        s2, a2 = _song()
        voice = s2.track('voice', 'synthwave/drums_outrun')
        b2 = bands.retrowave(s2, choir='vocoder', voice=voice)
        self.assertEqual(b2.choir.fx[0].sidechain, 'voice')
        self.assertTrue(voice.mute)
        _play(b2, a2)
        voice.loop(drums({'snare': 'x.x.x.x.'}), a2)
        s2.compile()
        with self.assertRaisesRegex(ComposeError, "choir='vocoder'"):
            bands.retrowave(Song('u', tempo=100), voice=voice)
        with self.assertRaisesRegex(ComposeError, 'choir must be'):
            bands.retrowave(Song('u', tempo=100), choir='monks')

    def test_retrowave_lead_chains(self):
        # the brass lead gets presence; the (already bright) supersaw a 3.5 kHz dip and +1 dB fader instead
        # (with the brass lead's lift it read +4 dB presence vs the synthwave profile: a 'harsh presence' warning)
        eqs = {}
        for lead in ('brass', 'supersaw'):
            s, a = _song()
            b = bands.retrowave(s, lead=lead)
            eqs[lead] = (b.lead.fx[-1].params['peak3.gain'], b.lead.gain_db)
        self.assertGreater(eqs['brass'][0], 0)
        self.assertLess(eqs['supersaw'][0], 0)
        self.assertGreater(eqs['supersaw'][1], eqs['brass'][1])

    def test_piano_lead_on_every_preset(self):
        """lead='piano': the sampled melody piano (salamander-grand) with plate + hall + echo sends on every preset,
        gm/piano_lead (sf2) when the pack is missing; unknown lead values raise."""
        have = sw._have(sw._GRAND)
        for packs in (True, False):
            with tempfile.TemporaryDirectory() as empty:
                ctx = mock.patch.object(library, 'SAMPLES', Path(empty)) if not packs else contextlib.nullcontext()
                with ctx:
                    for n in PRESETS:
                        with self.subTest(preset=n, packs=packs):
                            s, a = _song()
                            b = bands.make(n, s, lead='piano')
                            sampled = packs and have
                            self.assertEqual(b.lead.instrument.type, 'sampler' if sampled else 'sf2')
                            self.assertEqual(b.lead.patch, 'sampled/piano_lead' if sampled else 'gm/piano_lead')
                            self.assertEqual('lead' in b.info['fallbacks'], not sampled)
                            if sampled:
                                self.assertIn(sw._GRAND, b.info['packs'])
                            self.assertEqual(set(b.lead.sends), {'plate', 'hall', 'echo'})
                            self.assertIn('plate', b)
                            _play(b, a)
                            b.lead.note(84, a.start, 1, vel=105).note(72, a.start, 1, vel=84)
                            r = s.compile()
                            lead = next(t for t in r['tracks'] if t['id'] == 'lead')
                            self.assertEqual(set(lead['sends']), {'plate', 'hall', 'echo'})
        for n in PRESETS:
            with self.subTest(preset=n):
                with self.assertRaisesRegex(ComposeError, 'lead must be'):
                    bands.make(n, Song('u', tempo=100), lead='kazoo')

    def test_default_leads_unchanged(self):
        """The piano option leaves the defaults alone: the default synth leads, and no plate return on scifi."""
        expect = {'outrun': 'synthwave/supersaw_lead', 'dreamwave': 'synthwave/soft_lead',
                  'darksynth': 'synthwave/sync_lead', 'retrowave': 'synthwave/brass_lead', 'scifi': 'synthwave/soft_lead'}
        for n, patch in expect.items():
            with self.subTest(preset=n):
                s, a = _song()
                b = bands.make(n, s)
                self.assertEqual(b.lead.patch, patch)
        s, a = _song()
        self.assertNotIn('plate', bands.scifi(s))
        s, a = _song()
        self.assertEqual(bands.darksynth(s, lead='sync').lead.patch, 'synthwave/sync_lead')

    def test_wide_masters_narrow_the_hall_return(self):
        """Under the wide masters (width 1.25-1.5) the decorrelated hall return is narrowed, so pad-only intros keep a
        correlation >= 0; with and without the IR packs. Outrun / darksynth (narrower masters) keep it as it is."""
        def hall_width(n):
            s, a = _song()
            b = bands.make(n, s)
            last = b.hall.fx[-1]
            return last.params['width'] if last.type == 'width' else None

        for packs in (True, False):
            with self.subTest(packs=packs):
                with tempfile.TemporaryDirectory() as empty:
                    ctx = mock.patch.object(library, 'SAMPLES', Path(empty)) if not packs else contextlib.nullcontext()
                    with ctx:
                        for n in ('dreamwave', 'scifi', 'retrowave'):
                            w = hall_width(n)
                            self.assertIsNotNone(w, n)
                            self.assertLess(w, 1.0, n)
                        for n in ('outrun', 'darksynth'):
                            self.assertIsNone(hall_width(n), n)
        # a hall the song already has is used as it is (not narrowed)
        s, a = _song()
        hall = s.hall()
        n_fx = len(hall.fx)
        bands.dreamwave(s)
        self.assertEqual(len(hall.fx), n_fx)

    def test_sound_overrides_of_every_kind(self):
        from agentsound import patches
        s, a = _song()
        b = bands.outrun(s, sounds={'keys': patches.get('synthwave/dx_brass'),       # a Patch object
                                    'arp': patches.get('synthwave/arp_glass').instrument,  # an Instrument
                                    'drums': 'synthwave/drums_909'})               # another kit by name
        self.assertEqual(b.keys.instrument.type, 'dx7')
        self.assertEqual(b.arp.instrument.type, 'dx7')
        self.assertEqual(b.drums.instrument.type, 'drums')
        # the role's chain, pan and sends stay; the patch's own sends are replaced by the role's
        self.assertEqual(b.keys.pan, -0.3)
        self.assertEqual(b.keys.fx[-1].type, 'eq')
        _play(b, a)
        r = s.compile()
        keys = next(t for t in r['tracks'] if t['id'] == 'keys')
        self.assertEqual(set(keys['sends']), {'plate', 'hall'})
        # the kit swap still keys the gated snare and the pump
        self.assertTrue(any(t['id'].startswith('drums-key') for t in r['tracks']))
        with self.assertRaisesRegex(ComposeError, 'fx chain, not an instrument'):
            bands.outrun(Song('u', tempo=100), sounds={'lead': 'master/synthwave'})
        with self.assertRaisesRegex(ComposeError, 'a sound is'):
            bands.outrun(Song('u', tempo=100), sounds={'lead': 42})

    def test_default_movement_is_applied(self):
        s, a = _song()
        b = bands.scifi(s)
        _play(b, a)
        r = s.compile()
        pad = next(t for t in r['tracks'] if t['id'] == 'pad')
        self.assertEqual([m['target'] for m in pad['modulators']], ['instrument.cutoff'])

    def test_catalog_and_cli(self):
        import contextlib
        import io

        from agentsound import catalog, cli
        self.assertIn('bands', catalog.SECTIONS)
        text = catalog.overview(['bands'])
        for n in PRESETS:
            self.assertIn(n, text)
        self.assertIn('bands.darksynth(song)', catalog.search(['perturbator'], only='bands'))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(['bands', 'synthwave']), 0)
        self.assertIn('retrowave', out.getvalue())
        self.assertIn('The Midnight', out.getvalue())

    def test_demo_songs_compile_with_the_preset_profile(self):
        for n in PRESETS:
            with self.subTest(preset=n):
                mod = _load_demo(n)
                s = mod.build()
                s.compile()
                probe = Song('p', tempo=100)
                self.assertEqual(mod.ANALYSIS, bands.make(n, probe).analysis)


if __name__ == '__main__':
    unittest.main()
