import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentsound import Song, bands  # noqa: E402
from agentsound.bands import Band  # noqa: E402
from agentsound.patches import inst  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402


def _toy(song, *, without=(), sounds=None, ids=None, **opts):
    b = Band(song, 'toytest', analysis={'profile': 'default'})
    ids = ids or {}
    for role in ('lead', 'pad'):
        if role in without:
            continue
        snd = (sounds or {}).get(role, inst.va())
        b.add(role, song.track(ids.get(role, role), snd))
    b.bus('hall', song.hall())
    return b


class TestBands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bands._load()
        if 'toytest' not in bands._REGISTRY:
            bands.register('toytest', _toy, genre='test', roles=('lead', 'pad'), description='test preset')

    def test_make_roles_and_errors(self):
        s = Song('t', tempo=100)
        s.section('a', bars=1)
        b = bands.make('toytest', s, without=('pad',), ids={'lead': 'ld'})
        self.assertEqual(b.lead.id, 'ld')
        self.assertNotIn('pad', b)
        self.assertIn('hall', b)
        with self.assertRaisesRegex(ComposeError, 'no role'):
            b['pad']
        with self.assertRaisesRegex(ComposeError, 'unknown roles'):
            bands.make('toytest', Song('u', tempo=100), without=('drums',))
        with self.assertRaisesRegex(ComposeError, 'no band preset'):
            bands.make('nope', s)
        self.assertIn('band toytest', b.describe())

    def test_attribute_access(self):
        s = Song('t', tempo=100)
        s.section('a', bars=1)
        b = bands.toytest(s)
        self.assertEqual(set(b.roles), {'lead', 'pad'})
        self.assertIn('toytest', bands.list('test'))

    def test_library_presets_build(self):
        """Every registered library preset builds on a fresh song and compiles (packs permitting)."""
        from agentsound import library
        for name in bands.list():
            if bands.get(name).genre == 'test':
                continue
            p = bands.get(name)
            if any(not (library.SAMPLES / r / 'SOURCE.json').is_file() for r in p.requires):
                continue
            s = Song('t', tempo=110)
            a = s.section('a', bars=1)
            b = bands.make(name, s)
            for t in b.roles.values():
                t.note(60 if t.instrument.type != 'drums' else 36, a.start, 1)
            s.compile()


def _track(render: dict, tid: str) -> dict:
    return next(t for t in render['tracks'] if t['id'] == tid)


def _lane(d: dict, target: str) -> list:
    return next(a['points'] for a in d['automation'] if a['target'] == target)


class GainDbIsRelative(unittest.TestCase):
    """Every 'gainDb' value a song writes (automation, modulator base / min / max / steps) is dB on the node's
    gain_db - a band preset's level for a role, a patch level, the song's own. Regression: songs/perry-street-rain
    automated its jazz_trio bass at -4 dB for +1 dB in the bass solo, but the preset's fader was -5: the lane
    replaced the fader and raised the bass by 1 dB for the whole song."""

    def test_jazz_trio_bass_lane_is_relative_to_the_preset_level(self):
        s = Song('t', tempo=120)
        a = s.section('a', bars=4)
        b = bands.make('jazz_trio', s)
        g = b.bass.gain_db
        self.assertNotEqual(g, 0.0)                                   # the preset's level for the bass
        b.bass.note('A1', a.start, 1)
        b.bass.automate('gainDb', [(0, 0.0), (7, 0.0), (8, 1.0, 'smooth'), (12, 1.0), (13, 0.0, 'smooth')])
        d = _track(s.compile(), 'bass')
        self.assertAlmostEqual(d['gainDb'], g, places=4)
        self.assertEqual([p[1] for p in _lane(d, 'gainDb')], [round(g + x, 6) for x in (0, 0, 1, 1, 0)])
        b.bass.gain_db -= 1.0                                         # the lane follows the fader
        d = _track(s.compile(), 'bass')
        self.assertEqual([p[1] for p in _lane(d, 'gainDb')], [round(g - 1 + x, 6) for x in (0, 0, 1, 1, 0)])

    def test_every_gain_value_is_on_the_fader(self):
        from agentsound import envelope, jazz, lfo, steps
        s = Song('t', tempo=120)
        a = s.section('a', bars=2)
        kit = s.track('kit', inst.drums(kit='synthwave'), gain_db=-3)
        kit.note(36, a.start, 0.5)
        pad = s.track('pad', inst.va(), gain_db=-5)
        pad.note(60, a.start, 4)
        pad.modulate('gainDb', lfo('sine', rate='1/4', depth=3))                       # base: the fader
        pad.modulate('gainDb', lfo('sine', rate='1/2', min=-4, max=0), window=(0, 2))  # absolute values: on it
        pad.modulate('gainDb', steps([0, -2], rate='1/8'), window=(2, 4))
        pad.modulate('gainDb', envelope(decay='1/4', trigger=kit, pitches='kick', depth=-4))
        pad.automate('mod.1.max', [(0, 0.0), (2, 1.0)])
        pad.automate('gainDb', [(0, 0.0), (4, -6.0)])
        horn = s.track('horn', inst.va(), gain_db=-2)
        horn.note(60, a.start, 4)
        jazz.Expression().add_swell('gainDb', [(0, -6), (2, 0), (4, -3)]).apply(horn)   # swells: dB offsets
        r = s.compile()
        d = _track(r, 'pad')
        self.assertEqual(d['gainDb'], -5.0)
        self.assertEqual([p[1] for p in _lane(d, 'gainDb')], [-5.0, -11.0])
        m0, m1, m2, _ = d['modulators']
        self.assertNotIn('base', m0)                                  # the lane is its base
        self.assertEqual((m1['min'], m1['max']), (-9.0, -5.0))
        self.assertEqual(m2['source']['values'], [-5.0, -7.0])
        self.assertEqual([p[1] for p in _lane(d, 'mod.1.max')], [-5.0, -4.0])
        self.assertEqual(_track(r, 'kit-key')['gainDb'], -3.0)        # the ghost key plays at the key's fader
        self.assertEqual([p[1] for p in _lane(_track(r, 'horn'), 'gainDb')], [-8.0, -2.0, -5.0])
        s2 = Song('t', tempo=120)
        s2.section('a', bars=1)
        t = s2.track('t', inst.va(), gain_db=-6)
        t.note(60, 0, 1)
        t.modulate('gainDb', lfo('sine', rate='1/4', depth=2))
        self.assertEqual(_track(s2.compile(), 't')['modulators'][0]['base'], -6.0)
        t.automate('gainDb', [(0, 0.0), (2, -118.0)])                 # -124 dB on the -6 dB fader
        with self.assertRaisesRegex(ComposeError, 'outside'):
            s2.compile()


if __name__ == '__main__':
    unittest.main()
