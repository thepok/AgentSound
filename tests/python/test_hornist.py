"""The wind player (agentsound/hornist.py): the shapes of the air / pitch / mic moves, the budgets, determinism, the
targets per instrument, and smooth lanes (no zipper)."""
import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Song, hornist, library  # noqa: E402
from agentsound.patches import FX, Instrument, fx, inst  # noqa: E402
from agentsound.patterns import Clip  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

BPM = 112
SPB = 60.0 / BPM          # seconds per beat
HOOK = [(0.0, .5, 'Eb4'), (0.5, .5, 'Bb4'), (1.0, 2.5, 'F5'), (3.5, .5, 'Eb5'), (4.0, 1.0, 'D5'), (5.0, .5, 'Bb4'),
        (5.5, .5, 'C5'), (6.0, 1.5, 'Bb4'), (7.5, .5, 'G4'), (8.0, .5, 'Ab4'), (8.5, .5, 'Eb5'), (9.0, 2.5, 'G5'),
        (11.5, .5, 'F5'), (12.0, 1.5, 'Eb5'), (13.5, .5, 'F5'), (14.0, 1.0, 'D5'), (15.0, .75, 'Bb4'),
        (16.0, .5, 'G4'), (16.5, .5, 'C5'), (17.0, 2.5, 'G5'), (19.5, .5, 'F5'), (20.0, 1.0, 'Eb5'), (21.0, .5, 'C5'),
        (21.5, .5, 'Eb5'), (22.0, 1.5, 'F5'), (23.5, .5, 'Eb5'), (24.0, 1.0, 'C5'), (25.0, .5, 'Ab4'),
        (25.5, .5, 'C5'), (26.0, 1.0, 'D5'), (27.0, 1.0, 'F5'), (28.0, 3.0, 'Eb5')]


def hook(times=1):
    return Clip([(a + 32 * k, d, p, 96) for k in range(times) for a, d, p in HOOK], length=32 * times)


def val(g, lane, t):
    return g.value(lane, t)


def installed(pack):
    return (library.SAMPLES / pack / 'SOURCE.json').is_file()


class MoveShapes(unittest.TestCase):
    def test_push_rises_db_inside_the_note_and_returns(self):
        g = hornist.push(4.0, 2.5, BPM, db=3.0, ms=160)
        w = 0.16 / SPB
        self.assertGreaterEqual(g.start, 4.0 + 0.25 / SPB - 1e-6, 'after the attack')
        self.assertAlmostEqual(g.start, 5.0, places=6, msg='default: the first beat inside the note')
        self.assertAlmostEqual(g.end - g.start, w, places=6)
        self.assertAlmostEqual(val(g, 'air', g.start + 0.35 * w), 3.0, places=6)
        self.assertEqual(val(g, 'air', g.start), 0.0)
        self.assertAlmostEqual(val(g, 'air', g.end), 0.0, places=9)
        self.assertGreater(val(g, 'bend', g.start + 0.35 * w), 0.04, 'a small pitch lift with the push')
        self.assertAlmostEqual(val(g, 'bright', g.start + 0.35 * w), 3.0 * 0.35, places=6)

    def test_pulse_puts_2_to_4_pushes_on_the_beats(self):
        g = hornist.pulse(8.0, 4.0, BPM, db=2.0)
        peaks = sorted({round(s.t0) for s in g.shapes if s.lane == 'air'})
        self.assertEqual(peaks, [9, 10, 11], 'on the beats after the attack, before the release')
        self.assertTrue(2 <= g.params['n'] <= 4)
        levels = [max(s.keys, key=lambda k: k[1])[1] for s in g.shapes if s.lane == 'air']
        self.assertTrue(all(b < a for a, b in zip(levels, levels[1:])), 'each pulse a little softer')
        self.assertEqual(len(hornist.pulse(0.0, 16.0, BPM).shapes) // 3, 4, 'at most 4')

    def test_swell_grows_and_fades(self):
        g = hornist.swell(0.0, 4.0, BPM, lo=-3, peak=2, end=-2, peak_at=0.5)
        self.assertAlmostEqual(val(g, 'air', 0.0), -3.0)
        self.assertAlmostEqual(val(g, 'air', 2.0), 2.0)
        self.assertAlmostEqual(val(g, 'air', 4.0), -2.0)
        self.assertTrue(g.shapes[0].jump, 'after a rest the note starts under (a step in silence)')
        tied = hornist.swell(0.0, 4.0, BPM, tied=True)
        self.assertFalse(tied.shapes[0].jump, 'a legato note eases down before the transition')
        self.assertAlmostEqual(val(tied, 'air', -0.05 / SPB), 0.0, places=6)
        m = hornist.messa_di_voce(0.0, 4.0, BPM)
        self.assertLess(val(m, 'air', 0.0), -4)
        self.assertLess(val(m, 'air', 4.0), -4)

    def test_fp_cresc_attack_dip_bloom(self):
        g = hornist.fp_cresc(0.0, 4.0, BPM, dip=-6, bloom=2)
        dip_t = 0.18 / SPB
        self.assertGreater(val(g, 'air', 0.012 / SPB), 0.5)
        self.assertAlmostEqual(val(g, 'air', dip_t), -6.0, places=6)
        self.assertAlmostEqual(val(g, 'air', 4.0), 2.0, places=6)

    def test_bloom_starts_under(self):
        g = hornist.bloom(0.0, 2.0, BPM, under=-3, ms=300)
        self.assertAlmostEqual(val(g, 'air', 0.0), -3.0)
        self.assertGreater(val(g, 'air', 0.3 / SPB), 0.0)
        self.assertAlmostEqual(val(g, 'air', 2.0), 0.0, places=6)

    def test_taper_and_breath_release_end_the_phrase_and_come_back_after_the_tail(self):
        g = hornist.taper(0.0, 4.0, BPM, db=-5, frac=0.5, back=6.0)
        self.assertEqual(val(g, 'air', 1.9), 0.0)
        self.assertAlmostEqual(val(g, 'air', 4.0), -5.0)
        self.assertAlmostEqual(val(g, 'air', 4.0 + 0.3 / SPB), -5.0, msg='held through the tail')
        self.assertAlmostEqual(val(g, 'air', 4.0 + 0.6 / SPB), 0.0, places=6)
        r = hornist.breath_release(4.0, BPM, db=-9, back=4.5)
        self.assertAlmostEqual(val(r, 'air', 4.0), -9.0)
        self.assertLess(val(r, 'bend', 4.0), 0.0)
        self.assertLessEqual(r.shapes[0].t1, 4.5, 'back to rest before the next onset')

    def test_vibrato_delayed_and_growing(self):
        g = hornist.vibrato(0.0, 4.0, BPM, depth=25, hz=5.4, delay=0.3, grow=0.5)
        self.assertEqual(val(g, 'vib', 0.2 / SPB), 0.0)
        self.assertAlmostEqual(val(g, 'vib', 1.0 / SPB), 25.0, places=6)
        self.assertEqual(val(g, 'vib', 4.0), 0.0)
        self.assertEqual(g.rate[0][1], 5.4)
        self.assertGreater(g.rate[-1][1], 5.4, 'it quickens on a long note')

    def test_pitch_moves(self):
        s = hornist.scoop(2.0, BPM, cents=-80)
        self.assertAlmostEqual(val(s, 'bend', 2.0), -0.8)
        self.assertTrue(s.shapes[0].jump)
        f = hornist.fall(4.0, BPM, semis=-3)
        self.assertAlmostEqual(val(f, 'bend', 4.0), -3.0)
        self.assertLess(val(f, 'air', 4.0), 0)
        d = hornist.doit(4.0, BPM)
        self.assertEqual(d.name, 'doit')
        self.assertGreater(val(d, 'bend', 4.0), 2.5)
        sh = hornist.shake(0.0, 2.0, BPM, interval=3, hz=6.5)
        vals = [val(sh, 'bend', t / 200) for t in range(0, 400)]
        self.assertGreater(max(vals), 2.5)
        self.assertGreaterEqual(min(vals), -1e-9)
        gr = hornist.growl(0.0, 2.0, BPM, db=1.6)
        self.assertLessEqual(max(abs(val(gr, 'air', t / 500)) for t in range(1000)), 1.6 + 1e-9)

    def test_mic_moves(self):
        li = hornist.lean_in(0.0, 4.0, BPM, db=2, prox=2.5, room=-3)
        self.assertAlmostEqual(val(li, 'mic', 2.0), 2.0)
        self.assertAlmostEqual(val(li, 'prox', 2.0), 2.5)
        self.assertGreater(val(li, 'shelf', 2.0), 0)
        self.assertAlmostEqual(val(li, 'room', 2.0), -3.0)
        ta = hornist.turn_away(0.0, 4.0, BPM, shelf=-3.5, room=2.5)
        self.assertAlmostEqual(val(ta, 'shelf', 2.0), -3.5)
        self.assertGreater(val(ta, 'room', 2.0), 0)
        self.assertLess(val(ta, 'mic', 2.0), 0)
        self.assertEqual(hornist.off_axis(0.0, 4.0, BPM).name, 'off_axis')
        bs = hornist.bell_swing(0.0, 4.0, BPM, seconds=1.2, shelf=-3)
        self.assertAlmostEqual((bs.end - bs.start) * SPB, 1.2, places=6)
        self.assertAlmostEqual(val(bs, 'shelf', (bs.start + bs.end) / 2), -3.0)
        self.assertEqual(val(bs, 'shelf', bs.end), 0.0)
        fa = hornist.fade_away(0.0, 4.0, BPM, back=6)
        self.assertLess(val(fa, 'shelf', 4.0), -3)
        self.assertLess(val(fa, 'mic', 4.0), -3)

    def test_accents_follow_the_velocities(self):
        g = hornist.accents([(0, 1, 80), (1, 1, 100), (2, 1, 120)], BPM, db_per_vel=0.1)
        self.assertAlmostEqual(val(g, 'air', 0.5), -2.0)
        self.assertAlmostEqual(val(g, 'air', 1.5), 0.0)
        self.assertAlmostEqual(val(g, 'air', 2.5), 2.0)

    def test_bad_values_are_errors(self):
        with self.assertRaises(ComposeError):
            hornist.push(0, 2, BPM, ms=5)
        with self.assertRaises(ComposeError):
            hornist.arrange(hook(), BPM, style='bebop')
        with self.assertRaises(ComposeError):
            hornist.arrange(hook(), BPM, family='kazoo')
        with self.assertRaises(ComposeError):
            hornist.arrange(hook(), BPM, pushh=0.5)


class Arranger(unittest.TestCase):
    def test_deterministic(self):
        a = hornist.arrange(hook(), BPM, peaks=(1, 9, 17), seed=3, vel=(84, 118))
        b = hornist.arrange(hook(), BPM, peaks=(1, 9, 17), seed=3, vel=(84, 118))
        self.assertEqual(a.moves, b.moves)
        self.assertEqual(a.lanes(), b.lanes())
        c = hornist.arrange(hook(), BPM, peaks=(1, 9, 17), seed=4, vel=(84, 118))
        self.assertNotEqual(a.lanes(), c.lanes())

    def test_not_every_note_breathes_the_same_and_the_peaks_get_the_most(self):
        p = hornist.arrange(hook(4), BPM, peaks=(1, 9, 17), seed=1, section='chorus')
        held = [n for n in p.clip if n.dur * SPB >= 0.45]
        moved = {round(g.start, 1) for g in p.gestures if g.name in ('push', 'pulse', 'swell', 'bloom', 'fp_cresc')}
        self.assertLess(len(moved), len(held), 'air moves on some held notes, not all')
        self.assertGreater(len(moved), len(held) * 0.3)
        vib = [g for g in p.gestures if g.name == 'vibrato']
        peaks = [g for g in vib if any(abs(g.start - (32 * k + pk)) < 0.2 for k in range(4) for pk in (1, 9, 17))]
        self.assertGreaterEqual(len(peaks), 10, 'vibrato on (almost) every held peak')
        mean = sum(g.params['depth'] for g in peaks) / len(peaks)
        self.assertTrue(20 <= mean <= 32, f'the held peaks sing wide (Baker Street: +-20-30 ct): {mean:.1f}')
        self.assertTrue(all(5.0 <= g.params['hz'] <= 5.8 for g in peaks))

    def test_section_energy_scales_the_air(self):
        def pushes(sec):
            p = hornist.arrange(hook(4), BPM, peaks=(1, 9, 17), seed=2, section=sec, push=1.0)
            g = [g.params['db'] for g in p.gestures if g.name == 'push']
            return sum(g) / len(g)
        self.assertGreater(pushes('climax'), pushes('verse') * 1.15)

    def test_budgets(self):
        p = hornist.arrange(hook(8), BPM, peaks=(1, 9, 17), seed=5, climax=True)
        fast = [m for m in p.moves if m[3] in hornist.FAST]
        self.assertLessEqual(len(fast), 256 / (4 * 24) + 1, 'shakes / growls: at most one per fast_every bars')
        mic = sorted(m[0] for m in p.moves if m[3] in hornist.MIC)
        self.assertTrue(all(b - a >= 16 - 1e-6 for a, b in zip(mic, mic[1:])), 'mic moves >= mic_every bars apart')
        spice = sorted(m[0] for m in p.moves if m[3] in hornist.SPICE)
        self.assertTrue(all(b - a >= 8 - 1e-6 for a, b in zip(spice, spice[1:])))
        self.assertTrue(p.budget['dropped'], 'the budget had to drop some')
        none = hornist.arrange(hook(8), BPM, peaks=(1, 9, 17), seed=5, climax=True, style='ballad')
        self.assertFalse([m for m in none.moves if m[3] in hornist.FAST], 'ballad: no shakes')

    def test_memory_counts_song_wide(self):
        mem = hornist.Memory()
        kw = dict(peaks=(1, 9, 17), seed=1, mic_every=16, section='chorus')
        a = hornist.arrange(hook(), BPM, memory=mem, at=0, **kw)
        b = hornist.arrange(hook(), BPM, memory=mem, at=32, **kw)
        solo = hornist.arrange(hook(), BPM, **kw)
        mic = lambda p: [m for m in p.moves if m[3] in hornist.MIC]  # noqa: E731
        self.assertTrue(mic(a))
        self.assertEqual(len(mic(b)), 0, 'the mic budget is spent within 16 bars of the first call')
        self.assertTrue(mic(solo))
        self.assertEqual(mem.clock, 64)

    def test_phrasing_legato_breaths_and_touch(self):
        p = hornist.arrange(hook(), BPM, vel=(60, 110), seed=1, humanize_ms=0)
        ns = sorted(p.clip, key=lambda n: n.start)
        tied = sum(1 for a, b in zip(ns, ns[1:]) if a.start + a.dur > b.start)
        self.assertGreater(tied, len(ns) // 2, 'legato inside the phrases')
        vels = [n.vel for n in ns]
        self.assertGreater(max(vels) - min(vels), 25, 'touch() velocity arcs')


class Lanes(unittest.TestCase):
    def check_smooth(self, pts, lane, max_slope, max_gap_s=0.0201):
        """Points at most 20 ms apart, and no faster change than max_slope (units per ms) outside the marked steps
        (a scoop / a note starting from silence): the engine glides every change over ~5 ms, so a lane that moves
        at most ~0.3 dB per ms is a smooth curve, never an audible stair (zipper)."""
        for (t0, v0, *r0), (t1, v1, *r1) in zip(pts, pts[1:]):
            if (r1 and r1[0] == 'step') or t1 - t0 < 1e-9:
                continue
            ms = (t1 - t0) * SPB * 1000
            if v0 == v1 == 0.0:
                continue            # at rest between two moves
            self.assertLessEqual(ms, max_gap_s * 1000 + 1e-3, f'{lane}: points every <= 20 ms at {t0}')
            self.assertLessEqual(abs(v1 - v0) / ms, max_slope, f'{lane}: {v0} -> {v1} in {ms:.1f} ms at {t0}')

    def test_no_zipper(self):
        p = hornist.arrange(hook(4), BPM, peaks=(1, 9, 17), seed=7, vel=(80, 120), climax=True)
        lanes = p.lanes()
        for lane, step in (('air', 0.3), ('mic', 0.1), ('shelf', 0.1), ('prox', 0.1), ('room', 0.1), ('vib', 1.0)):
            if lane in lanes:
                self.check_smooth(lanes[lane], lane, step)
        # every window starts and ends at rest
        for lane in ('mic', 'shelf', 'prox', 'room'):
            if lane in lanes:
                self.assertEqual(lanes[lane][0][1], 0.0)
                self.assertEqual(lanes[lane][-1][1], 0.0)

    def test_steps_only_into_silence_or_at_a_scoop(self):
        p = hornist.arrange(hook(2), BPM, peaks=(1, 9, 17), seed=3)
        for lane, pts in p.lanes().items():
            for t, v, *r in pts:
                if r and r[0] == 'step':
                    at_onset = any(abs(n.start - t) < 1e-6 for n in p.clip)
                    self.assertTrue(at_onset, f'{lane}: a step at {t} that is not a note onset')


def track(sound, fxs=(), sends=None):
    s = Song('t', tempo=BPM, key='C major', seed=1)
    s.section('a', bars=8)
    for b in (sends or {}):
        s.bus(b, fx=[fx.reverb()])
    return s, s.track('w', sound, fx=list(fxs), sends=sends)


class Targets(unittest.TestCase):
    def test_compressed_chain_goes_after_the_compressor(self):
        s, t = track(inst.va(), [fx.compressor(threshold=-30, ratio=3)])
        plan = hornist.targets(t)
        self.assertEqual(plan['level'], 'fx.air.gain', "the breath stage (heroes' 'air' utility), inserted")
        self.assertTrue(plan['compressed'])
        self.assertEqual([f.name for f in t.fx], ['mic', None, 'air'],
                         'the mic stage in front of the compressor (where a microphone is), air after it')
        self.assertEqual((t.fx[2].type, t.fx[2].params), ('utility', {'gain': 0.0}))
        hornist.targets(t)
        self.assertEqual(sum(1 for f in t.fx if f.name in ('mic', 'air')), 2, 'inserted once')

    def test_air_stage_wins_when_present(self):
        s, t = track(inst.va(), [fx.compressor(), FX('utility', {'gain': 0}, name='air')])
        self.assertEqual(hornist.targets(t)['level'], 'fx.air.gain')
        s, t = track(inst.va(), [fx.compressor(), FX('eq', {}, name='air')])
        self.assertEqual(hornist.targets(t)['level'], 'fx.air.output')
        s, t = track(inst.va(), [fx.compressor(), FX('exciter', {}, name='air')])
        self.assertEqual(hornist.targets(t)['level'], 'fx.mic.output', "an 'air' exciter is no gain stage")
        s, t = track(inst.va(), [fx.compressor()])
        hornist.mic_stage(t)
        hornist.targets(t)
        self.assertEqual([f.name for f in t.fx], ['mic', None, 'air'], 'the air stage goes in after the compressor')

    def test_live_dynamics_sampler_gets_dynamics_with_headroom(self):
        s, t = track(Instrument('sampler', {'layers': 'dynamics', 'dynrange': 12, 'dynamics': 1.0}))
        plan = hornist.targets(t)
        self.assertEqual(plan['level'], 'instrument.dynamics')
        self.assertLess(plan['home'], 1.0)
        self.assertAlmostEqual(plan['comp'], (1.0 - plan['home']) / plan['per_db'], places=1)
        self.assertEqual(t.fx[-1].params['output'], plan['comp'], 'the mic stage makes the home level good')
        self.assertFalse(plan['tone'], 'the layers carry the tone')
        s, t = track(Instrument('sampler', {'layers': 'dynamics', 'dynrange': 12, 'dynamics': 0.6}))
        plan = hornist.targets(t)
        self.assertEqual(plan['home'], 0.6)
        self.assertEqual(plan['comp'], 0.0, 'enough headroom already')

    def test_plain_sampler_goes_to_the_mic_stage(self):
        s, t = track(Instrument('sampler', {'mono': 'legato'}))
        self.assertEqual(hornist.targets(t)['level'], 'fx.air.gain')
        s, t = track(Instrument('sampler', {'layers': 'dynamics', 'dynrange': 12}), [fx.compressor()])
        self.assertEqual(hornist.targets(t)['level'], 'fx.air.gain', 'a compressed chain: after the compressor')

    def test_room_sends_are_the_reverbs(self):
        s, t = track(inst.va(), sends={'hall': -12, 'echo': -20})
        self.assertEqual(hornist.targets(t)['room'], [('hall', -12.0)])

    def test_place_writes_the_lanes_and_compiles(self):
        s, t = track(inst.va(), [fx.compressor(threshold=-30, ratio=3)], sends={'hall': -12})
        p = hornist.arrange(hook(), BPM, peaks=(1, 9, 17), seed=3, vel=(84, 118))
        p.place(t, 0)
        targets = {x for x, _ in t._auto}
        self.assertIn('fx.air.gain', targets)
        self.assertIn('fx.mic.high.gain', targets)
        self.assertIn('instrument.pitchbend', targets)
        s.compile()
        mods = [m for m in t._mods if m[0] == 'instrument.pitchbend']
        self.assertTrue(mods, 'va: the vibrato as a pitch-bend lfo')

    @unittest.skipUnless(installed('karoryfer-weresax') and installed('mtg-solo-sax'), 'sax packs not installed')
    def test_real_instruments(self):
        for name, level in (('layered/hero_sax', 'fx.air.gain'), ('hero/sax', 'fx.air.gain'),
                            ('sampled/alto_sax', 'fx.air.gain'), ('sampled/tenor_sax', 'instrument.dynamics')):
            s, t = track(name)
            plan = hornist.targets(t)
            self.assertEqual(plan['level'], level, name)
        s, t = track('hero/sax')
        self.assertEqual(len(hornist.targets(t)['vibrato']), 4, 'every sampler layer of the stack')
        names = [f.name for f in t.fx]
        self.assertEqual(names[-1], 'air', "the hero's own air stage stays last")
        self.assertEqual(t.fx[names.index('mic') + 1].type, 'compressor', 'the mic stage in front of the compressor')


if __name__ == '__main__':
    unittest.main()
