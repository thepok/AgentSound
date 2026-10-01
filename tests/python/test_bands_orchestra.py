"""Orchestra band presets (agentsound/bandlib/orchestra.py): every preset builds on a fresh song and compiles, with
its roles, articulations, seating, hall and analysis profile; the playing helpers (perform, dynamics, ring, rebow,
lead) and the zone fix-ups (VSCO layer levels, the SSO dynamics curve on mixed-in programs). Tests that need the
sample packs skip when they are not installed ($AGENTSOUND_SAMPLES or assets/samples)."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentsound import Song, bands, library  # noqa: E402
from agentsound import articulation as art  # noqa: E402
from agentsound.bandlib import orchestra as orch  # noqa: E402
from agentsound.patterns import Clip  # noqa: E402
from agentsound.patches import inst  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402


def have(*packs) -> bool:
    return all((library.SAMPLES / p / 'SOURCE.json').is_file() for p in packs)


PRESETS = {
    'string_quartet': ('sso',),
    'chamber_orchestra': ('vsco2-ce',),
    'symphony_orchestra': ('sso',),
    'film_orchestra': ('sso',),
    'church_organ': ('lars-palo-burea-church',),
}


def song(bars=2, tempo=90) -> tuple:
    s = Song('t', tempo=tempo, seed=1)
    return s, s.section('a', bars=bars)


class TestRegistry(unittest.TestCase):
    def test_registered(self):
        names = bands.list('orchestra')
        for n in PRESETS:
            self.assertIn(n, names)
            p = bands.get(n)
            self.assertEqual(p.requires, PRESETS[n])
        self.assertIn('violin1', bands.get('string_quartet').roles)
        self.assertIn('choir', bands.get('film_orchestra').roles)
        self.assertIn('pedal_full', bands.get('church_organ').roles)

    def test_missing_pack_names_the_fetch_command(self):
        s, _ = song()
        with mock.patch.object(orch.library, 'SAMPLES', Path(__file__).parent / 'no-such-samples'):
            with self.assertRaisesRegex(ComposeError, 'samples fetch sso'):
                bands.make('symphony_orchestra', s)
            with self.assertRaisesRegex(ComposeError, 'samples fetch lars-palo-burea-church'):
                bands.make('church_organ', Song('u', tempo=90))

    def test_dyn_markings(self):
        self.assertEqual(orch.dyn('mf'), orch.DYN['mf'])
        self.assertEqual(orch.dyn(0.25), 0.25)
        with self.assertRaises(ComposeError):
            orch.dyn('mezzo')
        with self.assertRaises(ComposeError):
            orch.dyn(1.5)

    def test_rebow_and_lead(self):
        c = Clip([(0, 16, 'C4', 80), (16, 1, 'D4', 80)], length=20)
        r = orch.rebow(c, bpm=60, max_seconds=6)
        long = [n for n in r if n.pitch == 60]
        self.assertEqual(len(long), 3)                         # 16 s -> three bow strokes
        self.assertAlmostEqual(long[-1].start + long[-1].dur, 16.0)
        self.assertTrue(all(n.dur < 6 for n in long))
        led = orch.lead(Clip([(4, 2, 'C4', 80), (6, 0.25, 'D4', 80)], length=8), bpm=60, ms=100)
        ln, sh = sorted(led, key=lambda n: n.start)
        self.assertAlmostEqual(ln.start, 3.9)                  # the long note starts 100 ms early ...
        self.assertAlmostEqual(ln.start + ln.dur, 6.0)         # ... and still ends on the beat
        self.assertAlmostEqual(sh.start, 6.0)                  # shorts stay on the beat


class _PresetCase(unittest.TestCase):
    preset = ''

    def setUp(self):
        if not have(*PRESETS[self.preset]):
            self.skipTest(f"sample packs {PRESETS[self.preset]} not installed")

    def make(self, **kw):
        s, a = song()
        return s, a, bands.make(self.preset, s, **kw)

    def check_band(self, b, profile):
        self.assertEqual(b.analysis, {'profile': profile})
        self.assertIn('hall', b.buses)
        for key in ('articulations', 'range', 'sweet', 'lead_ms', 'kind', 'seating', 'sound', 'dyn', 'hall'):
            self.assertIn(key, b.info)
        for role, t in b.roles.items():
            self.assertEqual(set(b.info['seating'][role]), {'pan', 'width', 'hall_send', 'high_shelf'})
            self.assertTrue(any(fx.type == 'eq' for fx in t.fx), role)
        self.assertIn(b.preset, b.describe())

    def play_all(self, b, a):
        """Every role plays a note in its sweet spot with each of its articulations; the song compiles."""
        from agentsound.theory import note as nn
        for role, t in b.roles.items():
            lo, hi = b.info['sweet'][role]
            p = (nn(lo) + nn(hi)) // 2
            arts = b.info['articulations'][role] or [None]
            notes = [art.note(i * 0.5, 0.4, p, 90, name) for i, name in enumerate(arts)]
            t.play(Clip._raw(notes, 8), a)
        return b.song.compile()


class TestStringQuartet(_PresetCase):
    preset = 'string_quartet'

    def test_build_and_compile(self):
        s, a, b = self.make()
        self.check_band(b, 'classical')
        self.assertEqual(list(b.roles), ['violin1', 'violin2', 'viola', 'cello'])
        self.assertEqual(sorted(b.info['mono']), ['cello', 'viola', 'violin1', 'violin2'])
        for role in b.roles:                                    # the core articulations in every player
            for name in ('sustain', 'legato', 'staccato', 'spiccato', 'pizzicato'):
                self.assertIn(name, b.info['articulations'][role])
        pans = [b.info['seating'][r]['pan'] for r in ('violin1', 'violin2', 'viola', 'cello')]
        self.assertEqual(pans, sorted(pans))                    # seated left to right
        d = self.play_all(b, a)
        for t in d['tracks']:
            self.assertEqual(t['instrument']['params'].get('mono'), 'legato')

    def test_perform_plays_legato_with_live_dynamics(self):
        s, a, b = self.make()
        line = Clip([(0, 1, 'A4', 60), (1, 1, 'C5', 70), (2, 2, 'E5', 90), (4, 2, 'D5', 70)], length=8)
        played = orch.perform(b, 'violin1', line, a, humanize_ms=0)
        ns = sorted(played, key=lambda n: n.start)
        self.assertTrue(all(x.start + x.dur > y.start for x, y in zip(ns, ns[1:])))   # tied: legato transitions
        targets = {t for t, _ in b.violin1._auto}
        self.assertIn('instrument.dynamics', targets)
        self.assertIn('instrument.vibrato', targets)
        pts = dict((t, p) for t, p in b.violin1._auto)['instrument.dynamics']
        self.assertLess(min(p[1] for p in pts), max(p[1] for p in pts))              # the lane moves
        s.compile()

    def test_tremolo_follows_the_dynamics_lane(self):
        """The viola / cello tremolo comes from the VSCO section (the SSO solo sets have none): in the legato
        player (layers='dynamics') its p / f layers ARE the dynamics - no SSO dynGain on top (that counted the
        dynamics twice: a tremolo swelling out of -60 dB), the soft layer at most 14 dB under the loud one."""
        if not have('vsco2-ce'):
            self.skipTest('vsco2-ce not installed')
        s, a, b = self.make()
        for role in ('viola', 'cello'):
            ins = b[role].instrument
            self.assertEqual(ins.params['layers'], 'dynamics')
            keys = ins.info['sfz']['keyswitches']
            trem = [z for z in ins.params['samples'] if z.get('swLast') == keys['tremolo']]
            self.assertTrue(trem)
            self.assertFalse(any('dynGain' in z for z in trem), role)
            by_region: dict = {}
            for z in trem:
                lv = orch._zone_level(z)
                if lv is not None:
                    by_region.setdefault((z['lo'], z['hi']), {})[z.get('vello', 0)] = lv
            gaps = [max(v.values()) - min(v.values()) for v in by_region.values() if len(v) > 1]
            self.assertTrue(gaps)
            self.assertLessEqual(max(gaps), 14.5, role)

    def test_without_sounds_ids(self):
        s, a, b = self.make(without=('viola',), ids={'cello': 'vc'}, sounds={'violin2': 'sampled/solo_cello'})
        self.assertNotIn('viola', b)
        self.assertEqual(b.cello.id, 'vc')
        self.assertEqual(b.info['sound']['violin2'], 'custom')
        self.assertTrue(any(fx.type == 'eq' for fx in b.violin2.fx))                  # the role's chain kept
        self.assertIn('Pizzicato', b.info['articulations']['violin2'])                # read from the custom sound
        with self.assertRaises(ComposeError):
            bands.make('string_quartet', Song('x', tempo=90), colour='dark')


class TestChamberOrchestra(_PresetCase):
    preset = 'chamber_orchestra'

    def test_build_and_compile(self):
        s, a, b = self.make()
        self.check_band(b, 'classical')
        self.assertEqual(len(b.roles), 11)
        self.assertEqual(b.info['articulations']['timpani'], ['hit', 'roll'])
        self.play_all(b, a)

    def test_vsco_layers_are_a_dynamics_stack(self):
        """VSCO boosts soft layers by 11-29 dB for velocity playing; as a dynamics stack every layer sits UNDER the
        louder ones by the same (measured, median) distance in every key range, the softest at most 14 dB down:
        a crescendo from the p to the f recording grows, and it grows alike over the whole keyboard."""
        s, a, b = self.make()
        for role in ('clarinets', 'horns', 'violins1'):
            ins = b[role].instrument
            self.assertEqual(ins.params['layers'], 'dynamics')
            sus = ins.info['sfz']['keyswitches']['sustain']
            regions: dict = {}
            for z in ins.params['samples']:
                if z.get('swLast') == sus and z.get('trigger') != 'release':
                    lv = orch._zone_level(z)
                    if lv is not None:
                        regions.setdefault((z['lo'], z['hi']), {})[(z.get('vello', 0), z.get('velhi', 127))] = lv
            dist: dict = {}
            for layers in regions.values():
                if len(layers) < 2:
                    continue
                top = layers[max(layers, key=lambda k: (k[1], k[0]))]
                for k, lv in layers.items():
                    self.assertLessEqual(lv, top + 0.01, role)             # softer layers are not louder
                    self.assertGreaterEqual(lv, top - 14.01, role)          # ... nor 30 dB down
                    dist.setdefault(k, []).append(round(lv - top, 1))
            self.assertTrue(dist, role)
            for k, v in dist.items():                                      # the same distance in every key range
                self.assertLess(max(v) - min(v), 0.3, (role, k, v))

    def test_notes_are_even(self):
        """The VSCO recordings jump up to 15 dB from note to note (and round robin to round robin); _even_notes
        puts every key range of an articulation (the layer played at mf) on a straight line over the keyboard."""
        s, a, b = self.make()
        ins = b.horns.instrument
        ref = round(127 * orch.DYN['mf'])
        for art_name in ('sustain', 'staccato'):
            sw = ins.info['sfz']['keyswitches'][art_name]
            pts = {}
            for z in ins.params['samples']:
                if z.get('swLast') == sw and z.get('trigger') != 'release' and \
                        z.get('vello', 0) <= ref <= z.get('velhi', 127):
                    lv = orch._zone_level(z)
                    if lv is not None:
                        pts.setdefault((z['lo'] + z['hi']) / 2, []).append(lv)
            xs = sorted(pts)
            ys = [max(pts[x]) for x in xs]
            self.assertGreater(len(xs), 3)
            n = len(xs)
            mx, my = sum(xs) / n, sum(ys) / n
            slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
            resid = [y - (my + slope * (x - mx)) for x, y in zip(xs, ys)]
            self.assertLess(max(abs(r) for r in resid), 2.0, (art_name, resid))     # (corrections cap at 10 dB)

    def test_dynamics_and_ring(self):
        s, a, b = self.make()
        orch.dynamics(b, orch.STRINGS + ('timpani',), [(0, 'pp'), (4, 'ff', 'smooth')], at=a)
        for r in ('violins1', 'violas', 'basses'):
            pts = dict(b[r]._auto)['instrument.dynamics']
            self.assertEqual([p[1] for p in pts], [orch.DYN['pp'], orch.DYN['ff']])
        self.assertNotIn('instrument.dynamics', dict(b.timpani._auto))          # struck: velocity is dynamics
        orch.ring(b, a.bar(1), length=2, db=4)
        send = dict(b.violins1._auto)['send.hall']
        self.assertEqual(send[-1][1], b.info['seating']['violins1']['hall_send'] + 4)
        base = b.info['seating']['violas']['hall_send']
        orch.ring(b, 6.5, length=0.5, db=3, roles=['violas'], back=7.75)   # a mid-song fermata: given back
        send = dict(b.violas._auto)['send.hall']
        self.assertEqual([p[1] for p in send[-4:]], [base, base + 3, base + 3, base])
        self.assertEqual(send[-1][0], 7.75)
        with self.assertRaises(ComposeError):
            orch.ring(b, 1, length=2, roles=['violas'], back=3)
        for r in b.roles:
            b[r].note(60 if r != 'basses' else 40, a.start, 2)
        s.compile()


class TestSymphonyOrchestra(_PresetCase):
    preset = 'symphony_orchestra'

    def test_build_and_compile(self):
        s, a, b = self.make()
        self.check_band(b, 'classical')
        self.assertEqual(len(b.roles), 17)
        for r in ('violins1', 'violas', 'cellos'):
            for name in ('sustain', 'staccato', 'marcato', 'pizzicato', 'tremolo', 'col legno'):
                self.assertIn(name, b.info['articulations'][r])
        # seating: brass and percussion further back (more hall, softer top) than the strings
        seat = b.info['seating']
        self.assertGreater(seat['trumpets']['hall_send'], seat['violins1']['hall_send'])
        self.assertLess(seat['horns']['high_shelf'], seat['violins1']['high_shelf'])
        self.assertLess(seat['violins1']['pan'], 0)
        self.assertGreater(seat['cellos']['pan'], 0)
        self.assertEqual(b.info['keys']['crash'], 49)
        self.play_all(b, a)

    def test_perform_sections(self):
        s = Song('t', tempo=90, seed=1)
        s.section('intro', bars=1)
        a = s.section('a', bars=2)
        b = bands.symphony_orchestra(s)
        chords = Clip([(0, 4, 'D4', 80), (0, 4, 'F#4', 80), (4, 0.25, 'A4', 100), (4.5, 0.25, 'A4', 90)], length=8)
        played = orch.perform(b, 'violins2', chords, a, humanize_ms=0)
        self.assertIn('staccato', {art.articulation_of(n) for n in played})             # the 16ths
        placed = [n for n in b.violins2.notes if n.dur > 3]
        lead = b.info['lead_ms']['violins2'] / 1000 * 90 / 60
        self.assertTrue(all(abs(n.start - (a.start - lead)) < 1e-6 for n in placed))     # early: slow attack
        self.assertTrue(all(abs(n.start + n.dur - (a.start + 4)) < 1e-6 for n in placed))  # ... ends in time
        orch.perform(b, 'timpani', Clip([(0, 4, 'D2', 90)], length=4), a, articulations='roll')
        self.assertEqual(art.articulation_of(b.timpani.notes[0]), 'roll')
        s.compile()

    def test_fallbacks_without_vsco(self):
        """timpani / percussion / harp fall back to the SSO sets when vsco2-ce is missing (the oboes to the SSO
        sustain); the song still compiles."""
        real = orch.installed
        with mock.patch.object(orch, 'installed', lambda p: False if p == 'vsco2-ce' else real(p)):
            s, a, b = self.make()
            for r in ('oboes', 'timpani', 'harp'):
                b[r].note(70 if r == 'oboes' else 50, a.start, 2)
            d = s.compile()
        self.assertIn('fallback', b.info['sound']['timpani'])
        self.assertIn('fallback', b.info['sound']['oboes'])
        self.assertEqual(set(b.roles), set(bands.get('symphony_orchestra').roles))
        files = {z['file'] for t in d['tracks'] if t['id'] == 'oboes' for z in t['instrument']['params']['samples']}
        self.assertFalse(any('vsco2-ce' in f for f in files))

    def test_fallbacks_without_vpo(self):
        """The violas / cellos / basses sustains come from Virtual Playing Orchestra (vpo-scripts-standard +
        vpo-wav); without them the SSO sustain plays (the preset must not need a pack it does not require)."""
        real = orch.installed
        gone = ('vpo-scripts-standard', 'vpo-wav')
        with mock.patch.object(orch, 'installed', lambda p: False if p in gone else real(p)):
            s, a, b = self.make()
            for r in ('violas', 'cellos', 'basses'):
                b[r].note(50, a.start, 2)
            d = s.compile()
        for r in ('violas', 'cellos', 'basses'):
            self.assertIn('fallback', b.info['sound'][r])
        files = {z['file'] for t in d['tracks'] for z in t['instrument']['params'].get('samples', [])}
        self.assertFalse(any('vpo-' in f for f in files))

    def test_custom_sound_without_a_dynamics_lane(self):
        """sounds= with a non-sampler (a SoundFont / synth) keeps the role's chain; the role becomes kind 'plain':
        orch.dynamics skips it and perform plays velocities (the engine rejects 'instrument.dynamics' there)."""
        s, a, b = self.make(sounds={'violins1': 'gm/warm_pad'})
        self.assertEqual(b.info['kind']['violins1'], 'plain')
        self.assertEqual(b.info['articulations']['violins1'], [])
        orch.dynamics(b, orch.STRINGS, [(0, 'p'), (4, 'f')], at=a)
        orch.perform(b, 'violins1', Clip([(0, 2, 'C5', 80)], length=4), a)
        self.assertNotIn('instrument.dynamics', dict(b.violins1._auto))
        self.assertIn('instrument.dynamics', dict(b.violas._auto))
        s.compile()

    def test_two_bands_on_one_song(self):
        """A second preset on the same song gets its own hall bus and keeps the master chain the first one set."""
        s, a, b = self.make()
        if not have('lars-palo-burea-church'):
            self.skipTest('lars-palo-burea-church not installed')
        org = bands.make('church_organ', s, ids={r: 'organ_' + r for r in bands.get('church_organ').roles})
        self.assertEqual(b.buses['hall'].id, 'hall')
        self.assertEqual(org.buses['hall'].id, 'hall_church_organ')
        self.assertEqual(sum(1 for f in s.master.fx if f.type == 'limiter'), 1)
        orch.ring(org, a.start)
        self.assertIn('send.hall_church_organ', dict(org.principal._auto))
        org.principal.note('C4', a.start, 2)
        b.violins1.note('C5', a.start, 2)
        s.compile()


class TestFilmOrchestra(_PresetCase):
    preset = 'film_orchestra'

    def test_build_and_compile(self):
        s, a, b = self.make()
        self.check_band(b, 'film')
        self.assertNotIn('sub', b)
        self.assertIn('choir', b)
        self.assertEqual(b.info['hybrid'], False)
        self.assertTrue(any(fx.type == 'compressor' for fx in s.master.fx))
        self.play_all(b, a)

    def test_hybrid_roles_need_hybrid(self):
        """sounds= / ids= for 'sub' / 'pulse' without hybrid=True is an error, not silently ignored."""
        for kw in ({'sounds': {'sub': 'gm/warm_pad'}}, {'ids': {'pulse': 'p'}}):
            with self.assertRaisesRegex(ComposeError, 'hybrid=True'):
                bands.make('film_orchestra', Song('x', tempo=90), **kw)
        s, a, b = self.make(without=('sub',))                  # without= a hybrid role is harmless
        self.assertNotIn('sub', b)

    def test_hybrid(self):
        s, a, b = self.make(hybrid=True)
        self.assertIn('sub', b)
        self.assertIn('pulse', b)
        self.assertEqual(b.sub.instrument.type, 'va')
        b.sub.note('D1', a.start, 2, 120)
        b.pulse.note('A2', a.start, 0.25, 100)
        s.compile()


class TestChurchOrgan(_PresetCase):
    preset = 'church_organ'

    def test_build_and_compile(self):
        s, a, b = self.make()
        self.check_band(b, 'classical')
        self.assertEqual(list(b.roles), ['soft', 'principal', 'full', 'pedal', 'pedal_full'])
        self.assertEqual(b.info['organ'], 'burea')
        orch.dynamics(b, list(b.roles), [(0, 'p')])             # organ roles: no dynamics lane (registration)
        self.assertFalse(any(t == 'instrument.dynamics' for r in b.roles for t, _ in b[r]._auto))
        for r in b.roles:
            orch.perform(b, r, Clip([(0, 2, 'C3' if r.startswith('pedal') else 'C4', 90)], length=4), a)
        s.compile()

    def test_options(self):
        with self.assertRaisesRegex(ComposeError, 'organ must be'):
            bands.make('church_organ', Song('x', tempo=90), organ='notre-dame')
        if have('lars-palo-pitea-mhs'):
            s, a, b = self.make(organ='pitea', tremulant=True)
            self.assertEqual(b.info['organ'], 'pitea')
            b.soft.note('C4', a.start, 2)
            s.compile()


if __name__ == '__main__':
    unittest.main()
