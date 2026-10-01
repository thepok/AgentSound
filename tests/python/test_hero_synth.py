"""Hero synth leads (agentsound/patches/hero_synth.py): the patches register with their notes and calibration, compile
into songs (sampled layers only when their pack is installed: skipped cleanly otherwise), the engine accepts them, and
the matching player (hero_synth.perform) shapes a line the way the notes describe."""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from agentsound import Song, cli, patches  # noqa: E402
from agentsound.patches import Patch  # noqa: E402
from agentsound.patches import hero_synth  # noqa: E402
from agentsound.song import dumps  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

NAMES = ('hero/synth_lead', 'hero/synth_piano', 'hero/darksynth_lead')


def _installed(p: Patch) -> bool:
    try:
        p.instrument.to_dict()
        return True
    except ComposeError:     # a layer's sample pack is not installed
        return False


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


def _song(name: str) -> Song:
    s = Song('Hero', tempo=110, key='F# minor', seed=1)
    a = s.section('a', bars=2)
    p = patches.get(name)
    for bus in p.sends:
        {'hall': s.hall, 'plate': s.plate, 'echo': s.echo}[bus]()
    line = s.motif('5:1/8. 7:1/8. 8:1/4 7:1/8 5:1/4 | 6:1/8. 8:1/8. 12:1/2 r:1/8').clip(octave=5)
    s.track('lead', p).play(hero_synth.perform(line, double=-12 if name == 'hero/synth_piano' else None), a)
    return s


class HeroSynthLibrary(unittest.TestCase):
    def test_patches_register(self):
        # the old names + the hero wrapper's unified names of the same presets (hero/synth, hero/darksynth)
        self.assertEqual(set(patches.list('hero/synth')) | set(patches.list('hero/darksynth')),
                         set(NAMES) | {'hero/synth', 'hero/darksynth'})
        for n in NAMES:
            p = patches.get(n)
            self.assertEqual(p.instrument.type, 'stack', n)
            layers = p.instrument.params['layers']
            self.assertGreaterEqual(len(layers), 2, n)
            self.assertEqual(len({x.id for x in layers}), len(layers), n)
            self.assertIn('Measured -18.0 LUFS', p.notes, n)
            for word in ('How to play', 'Mix', 'Tweak'):
                self.assertIn(word, p.notes, n)
            self.assertEqual(p.gain_db, hero_synth.LEVELS[n.split('/')[1]], n)
            self.assertTrue(p.audition and p.audition.get('notes'), n)
            self.assertLessEqual(set(p.sends), {'hall', 'plate', 'echo'}, n)
            self.assertIn('echo', p.sends, n)          # the dotted-8th throws are part of the sound

    def test_synth_layers_ignore_the_pedal_and_follow_velocity(self):
        for n in NAMES:
            for x in patches.get(n).instrument.params['layers']:
                if x.instrument.type != 'va':
                    continue
                self.assertEqual(x.params.get('follow.pedal'), 0, f"{n}: layer {x.id!r} follows the pedal")
                self.assertGreaterEqual(x.instrument.params.get('amp.velocity', 0.5), 0.7, f"{n}: {x.id}")

    def test_pure_synth_heroes_always_compile(self):
        for n in ('hero/synth_lead', 'hero/darksynth_lead'):
            self.assertTrue(_installed(patches.get(n)), n)
            d = _song(n).compile()
            lead = next(t for t in d['tracks'] if t['id'] == 'lead')
            self.assertEqual(lead['instrument']['type'], 'stack')

    def test_sampled_hero_compiles_or_skips(self):
        p = patches.get('hero/synth_piano')
        if not _installed(p):
            self.skipTest('sample pack for sampled/piano_lead not installed')
        _song('hero/synth_piano').compile()

    def test_layers_are_addressable(self):
        p = patches.get('hero/synth_lead').layer('octave', level=-4).but(**{'layers.voice.mod.vib.amount': 24})
        ls = {x.id: x for x in p.instrument.params['layers']}
        self.assertEqual(ls['octave'].params['level'], -4)
        self.assertEqual(ls['voice'].instrument.params['mod.vib.amount'], 24)


class HeroSynthPlayer(unittest.TestCase):
    def test_perform_shapes_velocities_and_ties_leaps(self):
        s = Song('P', tempo=120, key='F# minor')
        line = s.motif('5:1/4 8:1/4 7:1/4 5:1/4 | 5:1/4 12:1/2 r:1/4').clip(octave=5, vel=100)
        c = sorted(hero_synth.perform(line, lo=60, hi=110, tie='leaps'), key=lambda n: n.start)
        vels = [n.vel for n in c]
        self.assertGreaterEqual(max(vels) - min(vels), 15)          # real dynamics, not one velocity
        self.assertEqual(max(c, key=lambda n: n.vel).pitch, max(n.pitch for n in c))   # the summit sings out
        # C#5 -> F#5 is a leap of 5: held into the next note (legato glide); E5 -> C#5 (3) is played detached
        self.assertGreater(c[0].start + c[0].dur, c[1].start)
        self.assertLess(c[2].start + c[2].dur, c[3].start)
        plain = sorted(hero_synth.perform(line), key=lambda n: n.start)      # default: detached, every note re-attacks
        self.assertTrue(all(a.start + a.dur < b.start for a, b in zip(plain, plain[1:])))
        doubled = hero_synth.perform(line, double=-12)
        self.assertEqual(len(doubled), 2 * len(line))
        with self.assertRaises(ValueError):
            hero_synth.perform(line, tie='sometimes')


@unittest.skipIf(_engine() is None, 'engine not built')
class HeroSynthEngine(unittest.TestCase):
    def test_engine_accepts_the_heroes(self):
        for n in NAMES:
            if not _installed(patches.get(n)):
                continue
            d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_hero_'))
            rj = d / 'song.render.json'
            rj.write_text(dumps(_song(n).compile()), encoding='utf-8')
            proc = subprocess.run([str(_engine()), 'validate', str(rj)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"{n}: {proc.stderr}")


if __name__ == '__main__':
    unittest.main()
