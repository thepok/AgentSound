"""The lead guitarist's techniques (agentsound/fretwork.py) and the shared gesture primitives they use
(agentsound/gesture.py): bend curves (rise, overshoot, settle, pre-bend, release), vibrato shapes (up from the note,
down from a bent pitch, centred for the bar), legato ties (no pick), picked runs with accents, unison bends (the held
string on the twin / latched out of the bend), pinch harmonics and feedback on the 'harm' lane, palm mutes, whammy,
wah, the noise moves, and render(): one lane per target on a hero stack / a plain sampler."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Song, fretwork as fw, gesture as G, guitarist as gtr, library  # noqa: E402
from agentsound.patches import inst  # noqa: E402
from agentsound.soloist import Part  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

BPM = 96
SPB = 60.0 / BPM


def lane(part, ln, t):
    return sum(g.value(ln, t) for g in part.gestures)


def installed(pack):
    return (library.SAMPLES / pack / 'SOURCE.json').is_file()


class Bends(unittest.TestCase):
    def test_bend_rises_overshoots_and_settles_on_pitch(self):
        p = fw.bend('A4', 4, BPM, amount=2, rise_ms=150, overshoot=10, settle_ms=120, vib=None)
        self.assertEqual([n.pitch for n in p.clip], [67], 'written at the fretted pitch (G4)')
        self.assertEqual(lane(p, 'bend', 0.0), 0.0, 'starts at the fretted note')
        top = max(lane(p, 'bend', t / 1000.0) for t in range(0, 600))
        self.assertGreater(top, 2.05, 'overshoots the target a little')
        self.assertLess(top, 2.2)
        self.assertAlmostEqual(lane(p, 'bend', (0.15 + 0.12) / SPB + 0.01), 2.0, places=2, msg='settled on pitch')
        self.assertAlmostEqual(lane(p, 'bend', 3.9), 2.0, places=6, msg='held')

    def test_amounts_half_whole_step_and_a_half(self):
        for k, fretted in ((1, 68), (2, 67), (3, 66)):
            p = fw.bend('A4', 3, BPM, amount=k, vib=None, overshoot=0)
            self.assertEqual(p.clip[0].pitch, fretted)
            self.assertAlmostEqual(lane(p, 'bend', 2.5), k, places=6)
        self.assertLess(fw._RISE[1], fw._RISE[2], 'a wider bend takes longer')
        self.assertLess(fw._RISE[2], fw._RISE[3])

    def test_bend_vibrato_goes_below_the_bent_pitch(self):
        p = fw.bend('A4', 6, BPM, amount=2, vib='wide', overshoot=0)
        vals = [lane(p, 'bend', 1.5 + i * 0.01) for i in range(400)]
        self.assertLessEqual(max(vals), 2.0 + 1e-6, 'never above the target')
        self.assertLess(min(vals), 1.75, 'released a little and pushed back')

    def test_bend_and_release_and_return_before_the_next_note(self):
        p = fw.bend('A4', 4, BPM, amount=2, release=0.6, vib=None, back=4.1)
        self.assertAlmostEqual(lane(p, 'bend', 3.95), 0.0, places=3, msg='released to the fretted note')
        p2 = fw.bend('A4', 4, BPM, amount=2, vib=None, back=4.05)
        self.assertAlmostEqual(lane(p2, 'bend', 4.05), 0.0, places=6, msg='the lane is back before the next onset')

    def test_prebend_is_up_before_the_pick_and_released(self):
        p = fw.prebend('A4', 4, BPM, amount=2, release=0.5, pre_ms=90, vib=None)
        self.assertAlmostEqual(lane(p, 'bend', -0.01), 2.0, places=6, msg='bent silently before the pick')
        self.assertAlmostEqual(lane(p, 'bend', 0.0), 2.0, places=6)
        self.assertAlmostEqual(lane(p, 'bend', 3.5), 0.0, places=6, msg='released down')
        self.assertTrue(any(s.jump for g in p.gestures for s in g.shapes), 'a step in the silence before the note')

    def test_ghost_bend_is_soft_and_swells(self):
        p = fw.ghost_bend('A4', 4, BPM, vel=100)
        self.assertLess(p.clip[0].vel, 70)
        self.assertTrue(any(s.lane == 'air' for g in p.gestures for s in g.shapes))

    def test_unison_bend_on_a_mono_lead_puts_the_held_string_on_the_twin(self):
        p = fw.unison_bend('E5', 3, BPM, amount=2)
        self.assertEqual([n.pitch for n in p.aux['twin']], [76], 'the held E5 on the twin')
        self.assertEqual([n.pitch for n in p.clip], [74], 'the bent D5 on the lead')
        self.assertAlmostEqual(max(lane(p, 'bend', 0.8 + i * 0.01) for i in range(150)), 2.0, delta=0.12)
        poly = fw.unison_bend('E5', 3, BPM, amount=2, mono=False)
        self.assertEqual(sorted(n.pitch for n in poly.clip), [74, 76])
        st = poly.steps['bendfollow']
        self.assertEqual([v for _, v in st], [0.0, 1.0], 'the held string latched out of the bend, then the bent in')
        self.assertTrue(st[0][0] < 0 < st[1][0] < min(n.start for n in poly.clip if n.pitch == 74))

    def test_oblique_bend(self):
        p = fw.oblique_bend('E5', 3, BPM, interval=5, amount=2)
        self.assertEqual([n.pitch for n in p.clip], [69])
        self.assertEqual([n.pitch for n in p.aux['twin']], [76])


class Vibrato(unittest.TestCase):
    def test_finger_vibrato_only_goes_up(self):
        p = fw.vibrato('E5', 6, BPM, style='wide')
        vals = [lane(p, 'bend', i * 0.01) for i in range(600)]
        self.assertGreaterEqual(min(vals), -1e-9, 'never below the note')
        self.assertGreater(max(vals), 0.5, 'a wide push')
        self.assertEqual(lane(p, 'bend', 0.1), 0.0, 'straight at first (delayed)')

    def test_styles_differ_in_rate_and_depth(self):
        def zero_cross_rate(style):
            p = fw.vibrato('E5', 8, BPM, style=style, seed=1)
            vals = [lane(p, 'bend', 3 + i * 0.005) for i in range(800)]
            m = sum(vals) / len(vals)
            n = sum(1 for a, b in zip(vals, vals[1:]) if (a - m) * (b - m) < 0)
            return n / (800 * 0.005 * SPB) / 2.0, max(vals)
        hz_n, d_n = zero_cross_rate('narrow')
        hz_b, d_b = zero_cross_rate('blues')
        self.assertGreater(hz_n, hz_b + 0.8, 'narrow is faster')
        self.assertLess(d_n, d_b * 0.5, 'and much shallower')
        self.assertAlmostEqual(hz_n, fw.VIBRATOS['narrow']['hz'], delta=0.9)

    def test_vibrato_widens_on_a_long_note(self):
        p = fw.vibrato('E5', 12, BPM, style='rock', seed=2)
        early = max(lane(p, 'bend', 1.5 + i * 0.005) for i in range(300))
        late = max(lane(p, 'bend', 9.0 + i * 0.005) for i in range(300))
        self.assertGreater(late, early * 1.15)

    def test_whammy_vibrato_is_centred(self):
        p = fw.whammy_vibrato('E5', 6, BPM, depth=40)
        vals = [lane(p, 'bend', 1.5 + i * 0.005) for i in range(800)]
        self.assertLess(min(vals), -0.25)
        self.assertGreater(max(vals), 0.25)

    def test_gesture_vibrato_shapes_are_checked(self):
        with self.assertRaises(ComposeError):
            G.vibrato(0, 4, BPM, shape='sideways')
        with self.assertRaises(ComposeError):
            G.vibrato(0, 4, BPM, shape='up', lane='vib')
        g = G.vibrato(0, 4, BPM, depth=22)          # the hornist's: unchanged on the 'vib' lane
        self.assertEqual({s.lane for s in g.shapes}, {'vib'})
        self.assertTrue(g.rate)


class LegatoAndPicking(unittest.TestCase):
    def test_hammer_on_is_tied_and_softer(self):
        p = fw.hammer_on('A4', 'C5', 2, BPM, vel=100)
        a, b = sorted(p.clip, key=lambda n: n.start)
        self.assertGreater(a.start + a.dur, b.start, 'tied: no new attack on a legato sampler')
        self.assertLess(b.vel, a.vel)
        with self.assertRaises(ComposeError):
            fw.pull_off('A4', 'C5', 2, BPM)

    def test_legato_run_picks_one_note_per_string(self):
        pitches = ['A4', 'B4', 'C5', 'D5', 'E5', 'F5', 'G5', 'A5', 'B5']
        p = fw.legato_run(pitches, 3, BPM, per_string=3, vel=(96, 96))
        ns = sorted(p.clip, key=lambda n: n.start)
        tied = [a.start + a.dur > b.start for a, b in zip(ns, ns[1:])]
        self.assertEqual(tied, [True, True, False, True, True, False, True, True], 'picked every third note')

    def test_picked_run_re_picks_every_note_with_accents(self):
        p = fw.picked_run(['A4', 'C5', 'D5', 'E5'] * 3, 3, BPM, group=4, vel=(90, 90))
        ns = sorted(p.clip, key=lambda n: n.start)
        self.assertTrue(all(a.start + a.dur < b.start for a, b in zip(ns, ns[1:])), 'every note picked')
        self.assertGreater(ns[4].vel, ns[5].vel, 'the group start accented')
        self.assertTrue(any(s.lane == 'air' for g in p.gestures for s in g.shapes), 'accents after the compressor')

    def test_trill_and_sweep(self):
        t = fw.trill('E5', 2, BPM, upper=2, rate=11)
        self.assertGreater(len(t.clip), 10)
        self.assertEqual({n.pitch for n in t.clip}, {76, 78})
        self.assertTrue(t.tricks and t.tricks[0][2], 'a fast trick')
        s = fw.sweep(['A3', 'E4', 'A4', 'C5', 'E5'], 1.5, BPM)
        self.assertEqual([n.pitch for n in sorted(s.clip, key=lambda n: n.start)], [57, 64, 69, 72, 76, 72, 69, 64, 57])

    def test_slides(self):
        s = fw.slide('A4', 'D5', 2, BPM)
        self.assertTrue(any(getattr(n, 'glide', None) for n in s.clip) or
                        any(gtr._art.glide_of(n) for n in s.clip), 'a glide mark on the target')
        si = fw.slide_in('D5', 2, BPM, frm=-4)
        self.assertAlmostEqual(lane(si, 'bend', 0.0), -4.0, places=6)
        self.assertAlmostEqual(lane(si, 'bend', 1.0), 0.0, places=6)
        so = fw.slide_out('D5', 2, BPM, semis=-7)
        self.assertAlmostEqual(lane(so, 'bend', 2.0), -7.0, places=6)

    def test_rake_and_palm_mute_close_the_tone(self):
        r = fw.rake('E5', 1, BPM, strings=3)
        self.assertEqual(len(r.clip), 4)
        self.assertGreater(lane(r, 'mute', 0.01), 0.5)
        pm = fw.palm_mute(['A2', 'A2', 'E3'], 2, BPM)
        self.assertGreater(lane(pm, 'mute', 1.0), 0.7)
        self.assertEqual(lane(pm, 'mute', 3.0), 0.0, 'opens again after')
        self.assertTrue(all(n.dur <= 0.13 for n in pm.clip), 'short chugs')


class ToneMoves(unittest.TestCase):
    def test_pinch_harmonic(self):
        p = fw.pinch('E4', 2, BPM)
        self.assertEqual(fw.pinch_partial('E4'), 6)
        self.assertEqual(fw.pinch_partial('E5'), 3)
        self.assertGreater(lane(p, 'harm', -0.005), 0.7, 'up before the pick')
        self.assertEqual(lane(p, 'harm', 3.0), 0.0)
        self.assertEqual(p.steps['harmonicnum'][0][1], 6.0)
        self.assertTrue(p.steps['harmonicnum'][0][0] < 0)

    def test_feedback_blooms_after_the_attack(self):
        p = fw.feedback('A4', 8, BPM, partial=2, start=0.3, bloom_s=1.5, amount=0.85)
        self.assertEqual(lane(p, 'harm', 1.0), 0.0)
        self.assertAlmostEqual(lane(p, 'harm', 2.4 + 1.5 / SPB + 0.1), 0.85, places=6)
        self.assertGreater(lane(p, 'air', 6.0), 1.0, 'grows a little louder')

    def test_whammy(self):
        d = fw.whammy_dive('E5', 4, BPM, semis=-12, start=0.25, dive=0.5)
        self.assertAlmostEqual(lane(d, 'bend', 3.0), -12.0, places=6)
        s = fw.whammy_scoop('E5', 2, BPM, semis=-1.5)
        self.assertAlmostEqual(lane(s, 'bend', 0.0), -1.5, places=6)

    def test_wah(self):
        w = fw.wah(4, BPM, kind='swell')
        self.assertLess(lane(w, 'wah', 0.0), lane(w, 'wah', 3.9))
        self.assertAlmostEqual(lane(w, 'wahmix', 2.0), 1.0)
        wk = fw.wah(4, BPM, kind='wacka', grid=0.5)
        self.assertGreater(abs(lane(wk, 'wah', 0.5) - lane(wk, 'wah', 1.0)), 0.5)
        with self.assertRaises(ComposeError):
            fw.wah(4, BPM, kind='talkbox')
        talk = fw.wah_talk(fw.picked_run(['A4', 'C5', 'D5'], 3, BPM).clip, BPM)
        self.assertTrue(talk.gestures)

    def test_noise_moves_go_to_the_aux_track(self):
        s = fw.pick_scrape(2, BPM)
        self.assertEqual(len(s.clip), 0)
        self.assertEqual(len(s.aux['noise']), 2)
        self.assertGreater(s.aux['noise'][0].pitch, s.aux['noise'][1].pitch, 'falling')


class Render(unittest.TestCase):
    def _song(self, patch):
        s = Song('t', tempo=BPM, key='A minor')
        s.section('a', bars=8)
        return s, s.track('lead', patch)

    def test_render_on_a_plain_sampler_writes_one_lane_per_target(self):
        s, lead = self._song(inst.sampler(file='soundfonts/GeneralUser-GS.sf2', sample='Sine-750Hz', loop='forward'))
        parts = [fw.bend('A4', 3, BPM), fw.pinch('E4', 2, BPM).shifted(4), fw.palm_mute(['A3'], 2, BPM).shifted(7),
                 fw.wah(3, BPM).shifted(10), fw.unison_bend('E5', 2, BPM, mono=False).shifted(14)]
        w = fw.render(lead, parts)
        targets = [t for t, _ in lead._auto]
        for t in ('instrument.pitchbend', 'instrument.harmonic', 'instrument.cutoff', 'instrument.harmonicnum',
                  'instrument.bendfollow', 'fx.wah.pedal', 'fx.wah.mix', 'fx.air.gain'):
            self.assertIn(t, targets)
            self.assertEqual(targets.count(t), 1, f"{t}: one lane")
        self.assertEqual(lead.fx[0].type, 'wah', 'the wah ahead of everything')
        self.assertGreater(w['instrument.pitchbend'], 10)
        s.compile()

    @unittest.skipUnless(installed('freepats-fsbs-direct'), 'needs the FSBS DI guitar pack')
    def test_render_on_the_hero_stack_reaches_every_zone(self):
        s, lead = self._song('layered/hero_guitar_heavy')
        fw.render(lead, [fw.pinch('E4', 2, BPM), fw.wah(2, BPM).shifted(3), fw.unison_bend('E5', 2, BPM).shifted(6)])
        targets = {t for t, _ in lead._auto}
        zones = [x.id for x in lead.instrument.params['layers'] if x.instrument.type == 'sampler']
        for z in zones:
            self.assertIn(f'instrument.layers.{z}.harmonic', targets)
            self.assertIn(f'instrument.layers.{z}.fx.0.pedal', targets)
        self.assertIn('lead_twin', s.tracks, 'the held string of the unison bend on the twin')
        from agentsound.patches import get
        self.assertNotIn('wah', [f.type for x in get('layered/hero_guitar_heavy').instrument.params['layers']
                                 for f in x.fx], 'the library patch is untouched')
        s.compile()


class LeadGestures(unittest.TestCase):
    def test_lead_gestures_replace_the_automation(self):
        from agentsound.patterns import Clip
        mel = Clip([(0, 0.5, 'A4', 90), (0.5, 0.5, 'C5', 90), (1, 3, 'E5', 100), (5, 0.5, 'D5', 90),
                    (5.5, 2.5, 'C5', 96)], length=8)
        a = gtr.lead(mel, bpm=BPM, key='A minor', style='rock', seed=4, mono=True, gestures=True,
                     moves={'bend': 3.0})
        self.assertEqual(a.auto, {}, 'no automation points: gestures')
        self.assertTrue(a.gestures)
        b = gtr.lead(mel, bpm=BPM, key='A minor', style='rock', seed=4, mono=True, moves={'bend': 3.0})
        self.assertEqual([n.pitch for n in a.clip], [n.pitch for n in b.clip], 'the same notes')
        self.assertFalse(b.gestures)
        self.assertIsInstance(a.part(), Part)


if __name__ == '__main__':
    unittest.main()
