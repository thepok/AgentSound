"""Silent notes, compile-time ear (agentsound.silent_notes): notes that reach no sample zone / drum piece / unmuted
stack layer are song.warnings and the render JSON's analysis.silentNotes; the drummer warns about the pieces a kit
lacks. No samples needed (zone files are only names here)."""
import os
import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from agentsound import Song, cli, drummer, inst, layer, silent_notes  # noqa: E402
from agentsound.patches import Instrument  # noqa: E402


def _kit(keys=(36, 38, 42, 46)):
    """A one-shot kit like inst.kit builds: one unpitched zone per key (80s pop kit A: no cymbals)."""
    return Instrument('sampler', {'samples': [dict(file=f'samples/x/k{k}.wav', lo=k, hi=k, root=k, loop='oneshot',
                                                   pitchKeytrack=0) for k in keys]})


def _song(sound, notes, **kw):
    s = Song('silent', tempo=120)
    s.section('a', bars=8)
    t = s.track('t', sound, **kw)
    for n in notes:
        t.note(*n)
    return s, t


def _silent(render):
    return (render.get('analysis') or {}).get('silentNotes') or []


class CompileTime(unittest.TestCase):
    def test_kit_without_cymbals(self):
        s, _ = _song(_kit(), [(36, 0, 0.25), (49, 0, 0.25), (38, 1, 0.25), (49, 16, 0.25), (42, 2, 0.25), (57, 20, 0.25)])
        r = s.compile()
        found = _silent(r)
        self.assertEqual(len(found), 1)
        f = found[0]
        self.assertEqual((f['track'], f['kind'], f['pitches'], f['count']), ('t', 'no_sound', [49, 57], 3))
        self.assertEqual(f['beats'], [0.0, 16.0, 20.0])
        self.assertIn('2 on crash (49)', f['message'])          # GM names on a kit
        self.assertIn('1 on crash2 (57)', f['message'])
        self.assertIn('at 1:1, 5:1, 6:1', f['message'])         # bar:beat
        self.assertIn('map crash', f['message'])
        self.assertTrue(any(w.startswith("silent notes: 't'") for w in s.warnings))

    def test_every_key_covered_is_quiet(self):
        s, _ = _song(_kit(), [(36, 0), (38, 1), (42, 2)])
        self.assertEqual(_silent(s.compile()), [])
        self.assertNotIn('analysis', s.compile())

    def test_out_of_range_on_a_multisample(self):
        zones = [dict(file='samples/x/c4.wav', root=60, lo=60, hi=66), dict(file='samples/x/g4.wav', root=67, lo=67, hi=72)]
        s, _ = _song(inst.sampler(zones=zones), [(62, 0), (50, 1), (48, 2), (70, 3)])
        f = _silent(s.compile())[0]
        self.assertEqual((f['pitches'], f['count']), ([48, 50], 2))
        self.assertIn('D3 (50)', f['message'])                   # note names on a pitched instrument
        self.assertIn('cover C4-C5 (60-72) only', f['message'])
        self.assertIn('transpose=+12', f['message'])

    def test_transpose_param_and_velocity_gaps(self):
        zones = [dict(file='samples/x/a.wav', root=60, lo=60, hi=72, vello=64, velhi=127)]
        s, _ = _song(inst.sampler(zones=zones, transpose=12), [(50, 0, 1, 100), (50, 1, 1, 30), (40, 2, 1, 100)])
        f = _silent(s.compile())[0]
        self.assertEqual((f['pitches'], f['count']), ([40, 50], 2))   # 50+12 = 62 at velocity 100 sounds
        self.assertIn('velocity 30', f['message'])
        # layers='dynamics': the velocity picks no zone, every velocity is covered
        s, _ = _song(inst.sampler(zones=zones, transpose=12, layers='dynamics'), [(50, 0, 1, 30)])
        self.assertEqual(_silent(s.compile()), [])

    def test_silence_zones_do_not_count(self):
        zones = [dict(file='samples/x/a.wav', root=60, lo=60, hi=72), dict(file='*silence', lo=40, hi=59)]
        s, _ = _song(inst.sampler(zones=zones), [(45, 0)])
        self.assertEqual(_silent(s.compile())[0]['pitches'], [45])

    def test_keyswitch_articulation(self):
        zones = [dict(file='samples/x/leg.wav', root=60, lo=60, hi=72, swLast=24, swDefault=24),
                 dict(file='samples/x/stac.wav', root=50, lo=40, hi=72, swLast=25)]
        # the default articulation (24) has no zone on 50; after the keyswitch 25 it plays; keyswitch notes never count
        s, _ = _song(inst.sampler(zones=zones), [(50, 0), (25, 3.9, 0.1), (50, 4), (24, 7.9, 0.1), (50, 8)])
        f = _silent(s.compile())[0]
        self.assertEqual((f['pitches'], f['count'], f['beats']), ([50], 2, [0.0, 8.0]))
        self.assertIn('articulation', f['message'])

    def test_engine_drum_machine(self):
        s, _ = _song(inst.drums(), [(36, 0), (70, 1), (49, 2)])
        f = _silent(s.compile())[0]
        self.assertEqual(f['pitches'], [70])
        self.assertIn('maracas (70)', f['message'])

    def test_stack_layer_ranges_and_muted_layers(self):
        smp = inst.sampler(zones=[dict(file='samples/x/a.wav', root=60, lo=60, hi=72)])
        st = inst.stack(layer(smp, 'smp', keys=(55, 80)), layer(inst.va(), 'low', keys=(30, 50)))
        # 40: the va layer; 56: the sampler layer takes it but has no zone there; 52: no layer takes it; 62 sounds
        s, _ = _song(st, [(40, 0), (56, 1), (52, 2), (62, 3)])
        f = _silent(s.compile())[0]
        self.assertEqual((f['kind'], f['pitches']), ('no_sound', [52, 56]))
        st = inst.stack(layer(smp, 'smp', keys=(55, 80)), layer(inst.va(), 'low', keys=(30, 50), mute=True))
        s, _ = _song(st, [(40, 0), (62, 3)])
        found = _silent(s.compile())
        self.assertEqual([(f['kind'], f['pitches']) for f in found], [('muted_layers', [40])])
        self.assertIn("'low'", found[0]['message'])
        # a mute lane that opens the layer: the note after it sounds
        s, t = _song(st, [(40, 0), (40, 8)])
        t.automate('instrument.layers.low.mute', [(0, 1), (6, 0, 'step')])
        self.assertEqual(_silent(s.compile())[0]['beats'], [0.0])

    def test_stack_velocity_curve_and_fade_edges(self):
        smp = inst.sampler(zones=[dict(file='samples/x/a.wav', root=60, lo=0, hi=127, vello=40)])
        # velcurve 2: velocity 64 reaches the child as ~32 (no zone under 40)
        s, _ = _song(inst.stack(layer(smp, 'smp', velcurve=2.0)), [(60, 0, 1, 64), (60, 1, 1, 120)])
        f = _silent(s.compile())[0]
        self.assertEqual(f['count'], 1)
        # a key fade starts at gain 0 on keylo itself (the engine's gainAt): that key needs another layer
        s, _ = _song(inst.stack(layer(inst.va(), 'a', keys=(60, 127), keyfade=5)), [(60, 0), (61, 1)])
        self.assertEqual(_silent(s.compile())[0]['pitches'], [60])

    def test_muted_tracks_are_not_checked(self):
        s, _ = _song(_kit(), [(49, 0)], mute=True)
        self.assertEqual(_silent(s.compile()), [])

    def test_apply_analysis_keeps_the_compilers_list(self):
        s, _ = _song(_kit(), [(49, 0)])
        r = s.compile()
        cli.apply_analysis(r, {'profile': 'synthwave'})
        self.assertEqual(r['analysis']['profile'], 'synthwave')
        self.assertEqual(r['analysis']['silentNotes'][0]['pitches'], [49])
        with self.assertRaises(cli.CliError):
            cli.check_analysis({'silentNotes': []})              # a song file can't write it


class Drummer(unittest.TestCase):
    FORM = [('verse', 8), ('chorus', 8)]

    def test_missing_piece_plays_the_fallback_and_says_so(self):
        k = drummer.Kit.of({'kick': 36, 'snare': 38, 'hat': 42, 'hat_open': 46})
        p = drummer.arrange(self.FORM, bpm=120, style='rock', density=0.6, seed=1, kit=k)
        self.assertTrue(p.crashes)
        self.assertNotIn(49, {n.pitch for n in p.clip})
        w = [x for x in p.warnings if 'no crash' in x]
        self.assertEqual(len(w), 1, p.warnings)
        self.assertIn('hat_open (46)', w[0])

    def test_part_for_another_kit_on_a_track(self):
        s = Song('d', tempo=120)
        s.section('verse', bars=8)
        s.section('chorus', bars=8)
        t = s.track('drums', _kit())
        p = drummer.arrange(s, style='rock', density=0.6, seed=1)          # General MIDI: crash on 49
        self.assertEqual(p.warnings, [])
        p.play(t)
        adv = [w for w in s.advice if 'crash' in w]
        self.assertTrue(adv and 'arrange with kit=<the track>' in adv[0] and 'hat_open (46)' in adv[0], s.advice)
        s.compile()
        self.assertIn(adv[0], s.warnings)                                  # kept by every compile
        s.compile()
        self.assertEqual(s.warnings.count(adv[0]), 1)
        # arranged for the track itself: the fallback, no silent notes
        s2 = Song('d', tempo=120)
        s2.section('verse', bars=8)
        s2.section('chorus', bars=8)
        t2 = s2.track('drums', _kit())
        drummer.arrange(s2, style='rock', density=0.6, seed=1, kit=t2).play(t2)
        self.assertEqual(_silent(s2.compile()), [])
        self.assertTrue(any('play on hat_open (46)' in w for w in s2.warnings), s2.warnings)


class PackFallback(unittest.TestCase):
    def test_the_same_packs_other_kits_are_offered(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = pathlib.Path(tmp) / 'pack'
            for rel in ('Kit A/KitA-Kick.wav', 'Kit A/KitA-Snare.wav', 'Kit C/KitC-Crash01.wav', 'Kit C/KitC-Kick.wav'):
                (pack / rel).parent.mkdir(parents=True, exist_ok=True)
                (pack / rel).write_bytes(b'')
            (pack / 'SOURCE.json').write_text('{}')
            got = silent_notes.fallback_files(pack / 'Kit A', 'crash')
            self.assertEqual(len(got), 1)
            self.assertTrue(got[0].endswith('Kit C/KitC-Crash01.wav'), got)
            self.assertEqual(silent_notes.fallback_files(pack / 'Kit A', 'ride'), [])
            self.assertEqual(silent_notes.fallback_files(pathlib.Path(tmp) / 'nopack', 'crash'), [])


if __name__ == '__main__':
    unittest.main()
