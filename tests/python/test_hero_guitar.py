"""The hero guitar (agentsound/patches/hero_guitar.py): the three patches register and import without samples, the
velocity zones of the driven heroes are contiguous and get harder / hotter / louder upwards, the performance helpers
(play, lead, lock_ties) write what a stack needs (plain notes, per-layer glide and vibrato lanes, pitch bends, echo
throws) and keep ties inside one zone. With the sample packs installed ($AGENTSOUND_SAMPLES or assets/samples) the
patches and a played solo compile to render JSON (and pass the engine's validation when it is built); without them
those tests skip cleanly (run the suite with AGENTSOUND_SAMPLES pointing to an empty folder to see the skips)."""

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Song, cli, library, patches  # noqa: E402
from agentsound import articulation as art  # noqa: E402
from agentsound import guitarist as gtr  # noqa: E402
from agentsound.patches import hero_guitar as hero  # noqa: E402
from agentsound.patterns import Clip  # noqa: E402

NAMES = ('layered/hero_guitar', 'sampled/hero_guitar_clean', 'layered/hero_guitar_heavy')
PACKS = {'layered/hero_guitar': ('freepats-fsbs-direct', 'jester-emerald-ir-pack'),
         'sampled/hero_guitar_clean': ('freepats-fsbs-direct', 'overdriven-112-celestion-h30-tubepreamp2-v1-2'),
         'layered/hero_guitar_heavy': ('freepats-fsbs-direct', 'jester-emerald-ir-pack',
                                       'sampleradar-heavy-metal-guitar')}


def _installed(*packs) -> bool:
    return all((library.SAMPLES / p / 'SOURCE.json').is_file() for p in packs)


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


def _song(patch='layered/hero_guitar'):
    s = Song('hero test', tempo=90, key='A minor', seed=3)
    sec = s.section('solo', bars=4)
    t = s.track('lead', patch)
    return s, sec, t


def _auto(track, target):
    pts = []
    for tgt, p in track._auto:
        if tgt == target:
            pts += list(p)
    return sorted(pts, key=lambda q: q[0])


class Library(unittest.TestCase):
    def test_registered_and_documented(self):
        for name in NAMES:
            p = patches.get(name)
            self.assertIn('Measured -18.0 LUFS', p.notes, name)
            self.assertIn('MIX:', p.notes, name)
            self.assertTrue(p.notes.startswith(f'v{hero.VERSION}.'), name)
            self.assertEqual(p.audition, {'notes': 'phrase'})
            self.assertIn('hall', p.sends)
            self.assertTrue(any(f.name == 'echo' and f.type == 'delay' for f in p.fx), name)   # the throw target
        self.assertEqual(patches.get('layered/hero_guitar').instrument.type, 'stack')
        self.assertEqual(patches.get('layered/hero_guitar_heavy').instrument.type, 'stack')
        self.assertEqual(patches.get('sampled/hero_guitar_clean').instrument.type, 'sampler')
        self.assertEqual(patches.get('sampled/hero_guitar_clean').instrument.params['mono'], 'off')   # polyphonic

    def test_lazy_without_samples(self):
        # defining the patches reads no sample file: the sampler layers are lazy until a render needs them
        for name in NAMES:
            p = patches.get(name)
            ins = p.instrument
            kids = [x.instrument for x in ins.layers] if ins.type == 'stack' else [ins]
            for k in kids:
                self.assertIsNotNone(k.lazy, name)
                self.assertNotIn('samples', k.params, name)

    def test_zones_contiguous_and_rising(self):
        for name, table in (('layered/hero_guitar', hero.ZONES), ('layered/hero_guitar_heavy', hero.HEAVY_ZONES)):
            s, sec, t = _song(name)
            zs = hero.zones(t)
            self.assertEqual(zs, [(lo, hi) for lo, hi, *_ in table])
            self.assertEqual(zs[0][0], 1)
            self.assertEqual(zs[-1][1], 127)
            for (a, b), (c, _) in zip(zs, zs[1:]):
                self.assertEqual(c, b + 1)                        # no gap, no overlap: one main instance per note
            drives = [x[2] for x in table]
            brights = [x[3] for x in table]
            levels = [x[4] for x in table]
            self.assertEqual(drives, sorted(drives))              # harder picking: more gain ...
            self.assertEqual(brights, sorted(brights))            # ... a brighter amp input ...
            self.assertEqual(levels, sorted(levels))              # ... louder after the amp
            self.assertEqual(levels[-1], 0.0)
            for x in t.instrument.layers:
                if x.id.startswith('z'):
                    self.assertNotIn('velfade', x.params)        # a crossfade would break the legato line
                    self.assertEqual(x.instrument.params['mono'], 'legato')
        heavy = patches.get('layered/hero_guitar_heavy').instrument
        dbl = [x for x in heavy.layers if x.id == 'double'][0]
        self.assertNotIn('vello', dbl.params)                     # the double plays every velocity
        self.assertLess(dbl.params['level'], -3)


class Performance(unittest.TestCase):
    def test_lock_ties_clamps_small_crossings(self):
        zs = [(1, 69), (70, 89), (90, 106), (107, 127)]      # (a zone table like ZONES)
        c = Clip([(0, 1.03, 64, 92), (1, 1.03, 66, 86), (2, 1, 67, 100)], length=3)   # tied, 92 -> 86 crosses 90
        out, clamped, repicked = hero.lock_ties(c, zs, 90)
        self.assertEqual((clamped, repicked), (1, 0))
        vels = [n.vel for n in sorted(out, key=lambda n: n.start)]
        self.assertEqual(vels, [92, 90, 100])                     # clamped to the zone edge, the rest untouched
        self.assertEqual([n.dur for n in sorted(out, key=lambda n: n.start)][:2], [1.03, 1.03])

    def test_lock_ties_repicks_big_jumps_and_keeps_glides(self):
        zs = [(1, 69), (70, 89), (90, 106), (107, 127)]      # (a zone table like ZONES)
        c = Clip([(0, 1.03, 64, 60), (1, 1, 67, 112)], length=2)                       # 60 -> 112: dig in
        out, clamped, repicked = hero.lock_ties(c, zs, 90)
        self.assertEqual((clamped, repicked), (0, 1))
        first = sorted(out, key=lambda n: n.start)[0]
        self.assertLess(first.start + first.dur, 1.0)             # a gap before the new pick
        g = art.glide(Clip([(0, 1.03, 64, 60), (1, 1, 67, 112)], length=2), 120, where=lambda n: n.pitch == 67)
        out, clamped, repicked = hero.lock_ties(g, zs, 90)
        self.assertEqual((clamped, repicked), (1, 0))             # a slide stays on the string: clamped
        self.assertEqual(sorted(out, key=lambda n: n.start)[1].vel, 69)
        self.assertEqual(art.glide_of(sorted(out, key=lambda n: n.start)[1]), 120)
        rest = Clip([(0, 0.9, 64, 60), (1, 1, 67, 112)], length=2)                    # not tied: nothing to do
        self.assertEqual(hero.lock_ties(rest, zs, 90)[1:], (0, 0))

    def test_play_on_a_stack_writes_layer_lanes(self):
        s, sec, t = _song()
        line = art.legato(Clip([(0, 1, 69, 90), (1, 1, 72, 95), (2, 2, 76, 100)], length=4), overlap=0.04)
        line = line.glide(120, where=art.leaps(3))
        hero.play(t, line, sec.bar(1), vib={'depth': 25, 'rate': 5.5}, throws=True)
        self.assertEqual(len(t._notes), 3)
        self.assertTrue(all(art.glide_of(n) is None and art.articulation_of(n) is None for n in t._notes))
        ids = hero.sampler_layers(t)
        self.assertEqual(ids, [f'z{i + 1}' for i in range(len(hero.ZONES))])
        for lid in ids:
            gl = _auto(t, f'instrument.layers.{lid}.glide')
            self.assertTrue(any(p[1] == 120 for p in gl), lid)   # the glide is set just before the leap ...
            b = sec.bar(1) + 2
            self.assertTrue(any(p[1] == 120 and b - 0.1 < p[0] < b for p in gl))
            self.assertEqual(gl[-1][1], 0.0)                      # ... and reset after it
            self.assertTrue(_auto(t, f'instrument.layers.{lid}.vibrato'))
            self.assertTrue(_auto(t, f'instrument.layers.{lid}.vibratorate'))
        self.assertFalse(_auto(t, 'instrument.vibrato'))          # not a stack param
        thr = _auto(t, 'fx.echo.mix')
        self.assertTrue(thr and max(p[1] for p in thr) > 0.3)     # the throw after the last note

    def test_lead_on_a_stack_is_mono_and_zoned(self):
        s, sec, t = _song()
        prog = s.prog('Am F C G')
        mel = s.motif('5:1 6:0.5 8:0.5 9:2 | 8:1 6:1 5:2 | 5:0.5 6:0.5 8:1 10:2 | 9:1 8:1 5:2').clip(octave=4)
        arr = hero.lead(t, mel, prog, style='rock', section=sec, seed=4, climax=True)
        self.assertTrue(arr.clip.notes)
        self.assertEqual(len(t._notes), len(arr.clip))
        vels = sorted({n.vel for n in t._notes})
        self.assertGreater(vels[-1] - vels[0], 15)                # touch() phrase dynamics reach the zones
        # a mono player: never two notes starting together (no emulated slides / double stops)
        starts = sorted(round(n.start, 6) for n in t._notes)
        self.assertEqual(len(starts), len(set(starts)))
        again_s, again_sec, again_t = _song()
        hero.lead(again_t, mel, again_s.prog('Am F C G'), style='rock', section=again_sec, seed=4, climax=True)
        self.assertEqual([tuple(n) for n in t._notes], [tuple(n) for n in again_t._notes])   # deterministic

    def test_play_on_a_plain_sampler(self):
        s, sec, t = _song('sampled/hero_guitar_clean')
        lick = gtr.bend('A5', 2, s.tempo, rise_ms=150)
        hero.play(t, lick, sec.bar(2))
        self.assertTrue(_auto(t, 'instrument.pitchbend'))
        self.assertTrue(_auto(t, 'instrument.vibrato'))           # a sampler takes its own vibrato
        c = art.glide(art.legato(Clip([(0, 1, 69, 90), (1, 1, 74, 95)], length=2)), 100)
        hero.play(t, c, sec.bar(3))
        self.assertTrue(any(art.glide_of(n) for n in t._notes))  # marks kept: the compiler writes the glides


class Compiled(unittest.TestCase):
    def _compile(self, name):
        if not _installed(*PACKS[name]):
            self.skipTest(f"sample packs {PACKS[name]} not installed")
        s, sec, t = _song(name)
        s.hall()
        s.plate()
        mel = s.motif('5:1 6:0.5 8:0.5 9:2 | 8:1 6:1 5:2 | 5:0.5 6:0.5 8:1 10:2 | 9:1 8:1 5:2').clip(octave=4)
        hero.lead(t, mel, s.prog('Am F C G'), style='rock', section=sec, seed=2, climax=True, throws=True)
        return s, s.compile()

    def test_compile_and_validate(self):
        for name in NAMES:
            with self.subTest(name=name):
                s, render = self._compile(name)
                node = next(n for n in render['tracks'] if n['id'] == 'lead')
                ins = node['instrument']
                if name == 'sampled/hero_guitar_clean':
                    self.assertEqual(ins['type'], 'sampler')
                else:
                    self.assertEqual(ins['type'], 'stack')
                    kids = [x for x in ins['params']['layers'] if x['instrument']['type'] == 'sampler']
                    self.assertTrue(all(x['instrument']['params'].get('samples') for x in kids))
                    targets = {a['target'] for a in node.get('automation', [])}
                    self.assertTrue(any(x.endswith('.vibrato') for x in targets), targets)
                eng = _engine()
                if eng is None:
                    continue
                with tempfile.TemporaryDirectory() as tmp:
                    rj = cli.write_render(render, pathlib.Path(tmp) / 'x.render.json')
                    r = subprocess.run([str(eng), 'validate', str(rj)], capture_output=True, text=True)
                    self.assertEqual(r.returncode, 0, r.stderr + r.stdout)


if __name__ == '__main__':
    unittest.main()
