"""The pop / synthwave package (phase 2 of compact song code): section progressions and plans (track.chords / arp /
bassline / plan), section lanes (node.lane / levels), track.rise and Song.transitions, speech.voice + Words.robot,
articulation.perform(preset=) / throws(spans=), pianist.Player / top_leads / arrange(doubles=), bassist.Player,
Song.beat_at, Song.breath(cut=). The migrated songs (chrome-leviathan, children-of-neon, skyline-heartbeat,
midnight-interstate, ghosts-of-ocean-drive, polaroid-summer, orbital-station, matryoshka, the demos) were checked
byte-identical against their hand-written render JSON; these tests pin the behaviour of the pieces."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import articulation as art  # noqa: E402
from agentsound import bassist, pianist, speech  # noqa: E402
from agentsound.automation import JUMP, normalize, riser  # noqa: E402
from agentsound.patterns import Clip, crash, drums, snare_roll, tom_fill  # noqa: E402
from agentsound.patches import inst  # noqa: E402
from agentsound.sections import lane_points, per  # noqa: E402
from agentsound.song import Song  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]


def rows(track_or_clip):
    notes = track_or_clip.notes if hasattr(track_or_clip, '_notes') else list(track_or_clip)
    return sorted((round(n.start, 6), round(n.dur, 6), n.pitch, n.vel) for n in notes)


def song():
    s = Song('t', tempo=120, key='A minor', seed=3)
    verse_prog = s.prog('i VI III VII')
    s.section('intro', 4, prog=verse_prog)
    s.section('verse', 8, prog=verse_prog)
    s.section('chorus', 8, prog='VI VII i i')
    s.section('outro', 2)
    return s


class SectionProgs(unittest.TestCase):
    def test_section_prog(self):
        s = song()
        self.assertEqual(s['chorus'].prog.length, 16.0)
        self.assertEqual([c.symbol for _, _, c in s['chorus'].prog], ['F', 'G', 'Am', 'Am'])
        self.assertIsNone(s['outro'].prog)
        with self.assertRaises(ComposeError):
            s.section('x', 4, prog='i NOPE')

    def test_per_section_values(self):
        s = song()
        intro, verse = s['intro'], s['verse']
        v = {intro: 1, 'verse': 2, '*': 3}
        self.assertEqual([per(s, v, x) for x in s.sections], [1, 2, 3, 3])
        self.assertEqual(per(s, 7, verse), 7)
        missing = per(s, {intro: 1}, verse)
        self.assertNotIn(missing, (None, 1))
        with self.assertRaises(ComposeError):
            per(s, {'bridge': 1}, verse)


class Plans(unittest.TestCase):
    def test_chords_fill_the_section(self):
        s = song()
        intro, verse, chorus = s['intro'], s['verse'], s['chorus']
        pad = s.track('pad', inst.va())
        pad.chords(intro, verse, chorus, voicing='spread', register=('C3', 'C5'), vel={'*': 80, chorus: 90})
        ref = s.track('ref', inst.va())
        block = s.prog('i VI III VII').block(voicing='spread', register=('C3', 'C5'), vel=80)
        ref.loop(block, intro).loop(block, verse)
        ref.loop(s.prog('VI VII i i').block(voicing='spread', register=('C3', 'C5'), vel=90), chorus)
        self.assertEqual(rows(pad), rows(ref))

    def test_bars_window_transpose_scale_prog(self):
        s = song()
        verse = s['verse']
        a, b = s.track('a', inst.va()), s.track('b', inst.va())
        a.chords(verse, bars=(4, 8), transpose=2, scale=0.5, prog=s.prog('i iv'), voices=3)
        c = s.prog('i iv').block(voices=3)
        b.play(c.loop(32).slice(16, 32), verse.bar(4), transpose=2, vel=0.5)
        self.assertEqual(rows(a), rows(b))
        self.assertTrue(all(n.start >= verse.bar(4) for n in a.notes))
        with self.assertRaises(ComposeError):
            a.chords(s['outro'])                     # no progression
        with self.assertRaises(ComposeError):
            a.chords(verse, bars=(4, 12))            # outside the section

    def test_then_before_crescendo_after_and_cut(self):
        s = song()
        verse = s['verse']
        a, b, c = (s.track(x, inst.va()) for x in 'abc')
        a.bassline('octave', verse, rate='1/8', then=lambda x: x.legato(0.03), crescendo=(0.5, 1.0), bars=(0, 4))
        line = verse.prog.bass('octave', rate='1/8').legato(0.03)
        b.play(line.loop(32).slice(0, 16).crescendo(0.5, 1.0), verse)
        self.assertEqual(rows(a), rows(b))
        long_ = Clip([(0, 33, 'A2', 90)], length=32)
        c.chords(verse, prog=s.prog('i'), then=lambda x: long_)
        self.assertEqual(c.notes[0].dur, 32.0)       # cut at the section end
        d = s.track('d', inst.va())
        d.chords(verse, prog=s.prog('i'), then=lambda x: long_, cut=False)
        self.assertEqual(d.notes[0].dur, 33.0)

    def test_arp_modes_per_section(self):
        s = song()
        verse, chorus = s['verse'], s['chorus']
        a, b = s.track('a', inst.va()), s.track('b', inst.va())
        a.arp({'*': 'up', chorus: 'updown'}, verse, chorus, rate='1/16', octaves={chorus: 2})
        b.loop(verse.prog.arp('up', rate='1/16'), verse)
        b.loop(chorus.prog.arp('updown', rate='1/16', octaves=2), chorus)
        self.assertEqual(rows(a), rows(b))

    def test_plan_loops_fills_crashes(self):
        s = song()
        intro, verse, chorus = s['intro'], s['verse'], s['chorus']
        g1 = drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'})
        g2 = drums({'kick': 'x...x...x...x...', 'hat': 'xxxxxxxxxxxxxxxx'})
        a, b = s.track('a', inst.drums()), s.track('b', inst.drums())
        a.plan({intro: (2, g2), verse: [g1, (4, g2, 2)], chorus: g1},
               fills={verse: (4, tom_fill(1), tom_fill(2)), chorus.bar(7): (snare_roll(4), ('snare',))},
               crashes={verse: 100, chorus: 118})
        b.loop(g2, intro.bar(2), bars=2).loop(g1, verse, bars=4).loop(g2, verse.bar(4), bars=2).loop(g1, chorus)
        b.play(tom_fill(1), verse.bar(3, 3), replace=True).play(tom_fill(2), verse.bar(7, 2), replace=True)
        b.clear(chorus.bar(7), chorus.end, pitches=['snare']).play(snare_roll(4), chorus.bar(7))
        b.play(crash(100), verse).play(crash(118), chorus)
        self.assertEqual(rows(a), rows(b))

    def test_plan_keep_and_rules_with_budget(self):
        s = Song('t', tempo=120)
        v1, v2 = s.section('v1', 8), s.section('v2', 8)
        g = drums({'kick': 'x...x...x...x...', 'hat': 'x.x.x.x.x.x.x.x.'})
        a = s.track('a', inst.drums())
        a.plan({v1: g}, fills={v1.bar(7): tom_fill(4)}, keep=('kick',))
        under = [n for n in a.notes if n.start >= v1.bar(7)]
        self.assertTrue(any(n.pitch == 36 for n in under) and not any(n.pitch == 42 for n in under))
        b = s.track('b', inst.drums())
        b.plan({v1: g, v2: g}, fills={'section': tom_fill(2), 'phrase': snare_roll(1)}, phrase=4)
        fill_pitches = {n.pitch for n in tom_fill(2)} | {n.pitch for n in snare_roll(1)}
        starts = sorted({n.start for n in b.notes if n.pitch in fill_pitches})
        self.assertEqual(sum(1 for t in (15.0, 30.0, 47.0, 62.0) if t in starts), 4)
        c = s.track('c', inst.drums())
        c.plan({v1: g, v2: g}, fills={'section': tom_fill(2), 'phrase': snare_roll(1)}, phrase=4, fill_every=8)
        rolls = {n.start for n in c.notes if n.pitch == 38}
        self.assertNotIn(15.0, rolls)                # a phrase fill 4 bars before a section fill: budget
        self.assertNotIn(47.0, rolls)


class Lanes(unittest.TestCase):
    def test_dict_lanes(self):
        s = song()
        pts = lane_points(s, {'intro': 0, 'verse': [(0, -3), (4, -1.5)], 'chorus': (-2, 0)})
        self.assertEqual(pts, [(0.0, 0.0, 'step'), (16.0, -3.0, 'step'), (32.0, -1.5, 'step'), (48.0, -2.0, 'step'),
                               (80.0, 0.0, 'linear')])
        held = lane_points(s, {'verse': -3, 'chorus': 1}, hold=True, default=0, end=True, drops=['chorus'])
        self.assertEqual(held, [(0.0, 0.0), (16.0, 0.0), (16.0, -3.0), (48.0, -3.0), (48.0, 1.0), (79.0, 1.0),
                                (79.0, -60.0), (80.0, -60.0), (80.0, 0.0), (88.0, 0.0)])
        glide = lane_points(s, {'intro': 2, 'chorus': 5}, glide=1, base=-1)
        self.assertEqual(glide, [(0.0, 1.0), (47.0, 1.0), (48.0, 4.0, 'smooth')])
        with self.assertRaises(ComposeError):
            lane_points(s, {'bridge': 1})

    def test_mark_lanes_and_levels(self):
        s = song()
        verse = s['verse']
        pts = lane_points(s, [(0, 3), (verse, 0, 'smooth'), ((verse, 4), -1)], base=-9)
        self.assertEqual(pts, [(0.0, -6.0), (16.0, -9.0, 'smooth'), (20.0, -10.0, 'step')])
        pad = s.track('pad', inst.va(), gain_db=-2)
        pad.levels({'verse': -3}, default=0)
        out = s.compile()
        lane = next(a for t in out['tracks'] if t['id'] == 'pad' for a in t['automation'] if a['target'] == 'gainDb')
        self.assertEqual(lane['points'][0], [0.0, -2.0, 'step'])          # dB on the fader (gain_db -2)
        self.assertIn([16.0, -5.0, 'step'], lane['points'])

    def test_steps_and_holds_render_the_same_lane(self):
        """The two jump encodings (a 'step' point / the old value written again) are one lane."""
        s = song()
        a = normalize(lane_points(s, {'intro': 0, 'verse': -3, 'chorus': 1}))
        b = normalize(lane_points(s, {'intro': 0, 'verse': -3, 'chorus': 1}, hold=True))

        def value(pts, t):
            v = pts[0][1]
            for p in pts:
                if p[0] <= t + 1e-12:
                    v = p[1]
            return v
        for t in [x * 0.25 for x in range(0, 360)]:
            self.assertEqual(value(a, t), value(b, t))


class Transitions(unittest.TestCase):
    def test_rise(self):
        s = song()
        r = s.track('riser', 'synthwave/noise_riser')
        r.rise(s['verse'], 16, pitch='A3', dur=15, vel=90)
        self.assertEqual(rows(r), [(0.0, 15.0, 57, 90)])
        auto = {t: p for t, p in r._auto}
        self.assertEqual(auto['instrument.cutoff'], riser(16.0, length=16.0, lo=300.0, hi=12000.0))
        self.assertEqual(auto['instrument.hpf'], riser(16.0, length=16.0, lo=20.0, hi=1500.0))

    def test_into(self):
        s = song()
        pad = s.track('pad', inst.va())
        pad.chords(s['intro'], s['verse'], s['chorus'])
        fxh = s.transitions(riser=True, impact=True, reverse='synthwave/noise_riser', pitch='A3')
        fxh.into(s['chorus'], riser=dict(beats=15, end=-1), reverse=2, impact=('D2', 120), breath=1)
        self.assertEqual([t.id for t in fxh.tracks], ['riser', 'reverse', 'impact'])
        self.assertEqual(rows(fxh.riser), [(32.0, 15.0, 57, 100)])
        self.assertEqual(rows(fxh.reverse), [(46.0, 2.0, 57, 100)])
        self.assertEqual(rows(fxh.impact), [(48.0, 4.0, 38, 120)])
        self.assertFalse(any(47 <= n.start < 48 for n in pad.notes))           # the breath
        self.assertTrue(all(n.start + n.dur <= 47 + 1e-9 for n in pad.notes if n.start < 47))
        with self.assertRaises(ComposeError):
            fxh.into(s['verse'], down=('A3', 8, 100))                          # no downlifter track


class Players(unittest.TestCase):
    def test_perform_preset(self):
        s = song()
        a, b = s.track('a', inst.va()), s.track('b', inst.va())
        line = Clip([(0, 1, 'A4', 90), (1, 2, 'E5', 100), (3, 1, 'C5', 96)], length=4)
        art.perform(a, line, s['verse'], preset='sax', seed=2, vib={'depth': 10})
        art.perform(b, line, s['verse'], glide_leaps=5, glide_ms=90, humanize_ms=8, late_ms=6, seed=2,
                    vib={'depth': 10, 'rate': 5.0, 'delay': 0.4})
        self.assertEqual(rows(a), rows(b))
        with self.assertRaises(ComposeError):
            art.perform(a, line, 0, preset='kazoo')

    def test_throws_spans(self):
        s = song()
        lead = s.track('lead', inst.va())
        s.echo()
        pts = art.throws(lead, spans=[(s['verse'], 2), ((s['chorus'], 4), 1)], base=-12, throw=-4)
        self.assertEqual(pts, [(0.0, -12.0), (16.0, -4.0, 'step'), (18.0, -12.0, 'step'), (52.0, -4.0, 'step'),
                               (53.0, -12.0, 'step')])
        held = art.throws(s.track('l2', inst.va()), spans=[(16, 2)], base=-12, throw=-4, hold=True)
        self.assertEqual(held, [(0.0, -12.0), (16.0, -12.0), (16.0, -4.0), (18.0, -4.0), (18.0, -12.0)])

    def test_top_leads_and_doubles(self):
        c = Clip([(0, 1, 'C4', 100), (0.02, 1, 'C5', 100), (1, 1, 'E4', 90), (2, 1, 'G4', 80)], length=4)
        t = pianist.top_leads(c, 0.5)
        self.assertEqual([n.vel for n in t], [50, 100, 90, 80])
        s = song()
        m = s.motif('8:1/4 7:1/4 5:1/2 | 8:1').clip(octave=4)
        kw = dict(bpm=120, key=s.key, seed=4, density=0.7, devices={'octave': 3.0})
        a = pianist.arrange(m, s.prog('i VI'), doubles=0.7, **kw)
        b = pianist.arrange(m, s.prog('i VI'), **kw)
        self.assertEqual(rows(a.rh), rows(pianist.top_leads(b.rh, 0.7)))

    def test_pianist_player(self):
        s = song()
        verse, chorus = s['verse'], s['chorus']
        p1, p2 = s.track('p1', inst.va()), s.track('p2', inst.va())
        pp = pianist.Player(p1, bpm=120, key=s.key, doubles=0.8)
        pp.play('8:1/4 7:1/4 5:1/2 | 8:1', verse.prog, verse, lo=60, hi=90, seed=1, until=6)
        pp.play('5:1/2 8:1/2 | 7:1', chorus.prog, chorus, lo=70, hi=100, seed=2)
        pp.pedal()
        from agentsound.humanize import touch
        mem = pianist.Memory()
        pts = []
        arr = pianist.arrange(touch(s.motif('8:1/4 7:1/4 5:1/2 | 8:1').clip(octave=4, gate=0.95), 60, 90),
                              verse.prog, bpm=120, key=s.key, memory=mem, at=verse, seed=1, doubles=0.8)
        p2.play(arr.rh.slice(0, 6), verse)
        pts += [p for p in arr.pedal(verse.prog, verse) if p[0] < verse.start + 6] + [(verse.start + 6, 0.0)]
        arr = pianist.arrange(touch(s.motif('5:1/2 8:1/2 | 7:1').clip(octave=4, gate=0.95), 70, 100),
                              chorus.prog, bpm=120, key=s.key, memory=mem, at=chorus, seed=2, doubles=0.8)
        p2.play(arr.rh, chorus)
        pts += arr.pedal(chorus.prog, chorus)
        self.assertEqual(rows(p1), rows(p2))
        self.assertEqual(len(pp.arrangements), 2)
        ped = dict(p1._auto)['instrument.pedal']
        self.assertEqual(ped[0], tuple(sorted(pts)[0][:2]))

    def test_bassist_player(self):
        s = song()
        verse = s['verse']
        b1, b2 = s.track('b1', inst.va()), s.track('b2', inst.va())
        bp = bassist.Player(b1, bpm=120, key=s.key, style='synth')
        bp.play(verse.prog, verse, 'verse', seed=3)
        ln = bassist.arrange(verse.prog, bpm=120, key=s.key, style='synth', part='verse', memory=bassist.Memory(),
                             at=verse, seed=3)
        ln.place(b2, verse)
        self.assertEqual(rows(b1), rows(b2))


class SongHelpers(unittest.TestCase):
    def test_beat_at(self):
        s = song()
        self.assertAlmostEqual(s.beat_at(s.seconds(30.5)), 30.5)
        s.ritardando((s['chorus'].bar(4), s['chorus'].end), to=0.7, a_tempo=False)
        for b in (10.0, 60.0, 77.3):
            self.assertAlmostEqual(s.beat_at(s.seconds(b)), b, places=9)
        self.assertAlmostEqual(s.beat_at(2.0, before=60.0), s.beat_at(s.seconds(60.0) - 2.0), places=12)

    def test_breath_cut(self):
        s = song()
        a, b = s.track('a', inst.va()), s.track('b', inst.va())
        for t in (a, b):
            t.note('A3', 40, 8).note('C4', 47.5, 1)
        s.breath(before=s['chorus'], tracks=[a])
        s.breath(before=s['chorus'], tracks=[b], cut=False)
        self.assertEqual(rows(a), [(40.0, 7.0, 57, 100)])
        self.assertEqual(rows(b), [(40.0, 8.0, 57, 100)])


class Robot(unittest.TestCase):
    CACHE = REPO / 'songs' / '_demo_vocoder' / 'samples' / 'speech'

    @unittest.skipUnless((REPO / 'songs' / '_demo_vocoder' / 'samples' / 'speech').is_dir(), 'no cached speech')
    def test_voice_and_robot(self):
        s = song()
        vox = speech.voice(s, ['neon lights', 'city nights', 'midnight drive', 'midnight', 'drive'], voice='zira',
                           rate=-2, cache_dir=self.CACHE)
        self.assertEqual(vox.track.id, 'voice')
        robot = s.track('robot', 'synthwave/vocoder_choir')
        vox.robot(robot, say={s['verse']: 'neon lights', s['chorus']: ({0: 'city nights', 4: 'drive'}, 96)},
                  chords={s['verse']: ('A3 C4 E4', 7.5), s['chorus']: ('F3 A3 C4', 4, 70)}, shift=-2)
        self.assertEqual(rows(vox.track), [(16.0, 1.0, 36, 127), (48.0, 1.0, 37, 96), (52.0, 1.0, 40, 96)])
        self.assertEqual(rows(robot), [(16.0, 7.5, 57, 96), (16.0, 7.5, 60, 96), (16.0, 7.5, 64, 96),
                                       (48.0, 4.0, 53, 70), (48.0, 4.0, 57, 70), (48.0, 4.0, 60, 70)])
        self.assertTrue(vox.track.mute)
        voc = robot.fx['vocoder']
        self.assertEqual(voc.sidechain, 'voice')
        self.assertEqual(voc.params['shift'], -2)
        with self.assertRaises(speech.SpeechError):
            speech.words(['neon lights'], voice='zira', rate=-2, cache_dir=self.CACHE).robot(robot)


if __name__ == '__main__':
    unittest.main()
