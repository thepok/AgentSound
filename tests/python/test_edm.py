"""EDM (recipes/edm.md): the edm/* patches and master chain, the five band presets (agentsound/bandlib/edm.py: kit,
pump, grooves, master, analysis profile), the drummer's 'house' style, the section lane's glide after a move, and the
vocal chops (singer.chops: slices of a sung part's own takes, pitched to a new line - with the mocked WSL backend of
test_singer, no voicebank needed). Presets whose sample packs are missing fall back to the engine's drum machines."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agentsound import Clip, Song, bands, drummer, patches, singer  # noqa: E402
from agentsound import voicebank as vb  # noqa: E402
from agentsound.bandlib import edm  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402
from test_singer import LINE, TEXT, _Env, _fake_run, _song  # noqa: E402

STYLES = ('house', 'techno', 'big_room', 'future_bass', 'melodic_house')


def _edm_song(style: str):
    s = Song('t', tempo=124, key='A minor', seed=3)
    a = s.section('build', bars=2, prog=s.prog('Am F'))
    d = s.section('drop', bars=2, prog=s.prog('C G'))
    return s, a, d


class Patches(unittest.TestCase):
    def test_registered_with_body_and_levels(self):
        for name in ('edm/bass', 'edm/reese', 'edm/supersaw', 'edm/future_chords', 'edm/pluck', 'edm/lead',
                     'edm/vocal_chop', 'master/edm'):
            self.assertTrue(patches.get(name).notes, name)
        lead = patches.get('edm/lead')
        self.assertIn('body', lead.notes.lower())                          # never a thin beep (HUMAN_FEEDBACK)
        self.assertEqual(set(edm.STYLES), set(STYLES))
        types = [f.type for f in patches.get('master/edm').fx]
        self.assertEqual(types[-1], 'limiter')
        self.assertIn('width', types)
        chop = [f.type for f in patches.get('edm/vocal_chop').fx]
        self.assertEqual(chop[:2], ['eq', 'compressor'])
        # chords pass the velocities (flat_dynamics): amp.velocity >= 0.7 on the chord synths
        for name in ('edm/supersaw', 'edm/future_chords'):
            self.assertGreaterEqual(patches.get(name).instrument.params['amp.velocity'], 0.7, name)


class Presets(unittest.TestCase):
    def test_every_style_builds_pumps_and_compiles(self):
        for style in STYLES:
            s, a, d = _edm_song(style)
            b = bands.make(style, s)
            self.assertEqual(b.analysis, {'profile': 'edm'}, style)
            self.assertEqual(set(b.roles), {'drums', 'bass', 'chords', 'pad', 'pluck', 'lead'}, style)
            g = b.info['grooves']
            self.assertEqual(set(g), {'intro', 'groove', 'build', 'drop', 'break'})
            self.assertTrue(all(c is None or isinstance(c, Clip) for c in g.values()))
            b.drums.plan({a: g['build'], d: g['drop']})
            b.bass.bassline('root', a, d, low='E1')
            b.chords.chords(a, d, voicing='spread', register=('C3', 'C5'))
            b.lead.play(Clip([(0, 1, 'A5', 100), (1, 1, 'C6', 90)], length=4), d)
            r = s.compile()
            ducked = {t['id'] for t in r['tracks'] if any(f['type'] == 'ducker' for f in t.get('fx', []))}
            self.assertTrue({'bass', 'chords', 'pad'} <= ducked, (style, ducked))
            self.assertEqual(r['master']['fx'][-1]['type'], 'limiter')
            self.assertEqual(r['master']['fx'][-1]['params']['gain'], edm.STYLES[style]['master_gain'])

    def test_options(self):
        s, a, d = _edm_song('house')
        b = bands.make('house', s, lead='supersaw', kit='808', sub=False, without=('pluck',))
        self.assertNotIn('pluck', b.roles)
        self.assertNotEqual(b.lead.instrument.type, 'sampler')               # the supersaw with body, no piano
        with self.assertRaises(ComposeError):
            bands.make('house', Song('t', tempo=124), lead='beep')
        with self.assertRaises(ComposeError):
            bands.make('house', Song('t', tempo=124), kit='tr999')
        with self.assertRaises(ComposeError):
            edm.grooves('dubstep')


class HouseDrummer(unittest.TestCase):
    def test_four_on_the_floor_everywhere_and_open_hats_in_the_drop(self):
        s = Song('t', tempo=124, key='A minor', seed=1)
        intro = s.section('intro', bars=4)
        drop = s.section('drop', bars=4)
        s.section('breakdown', bars=4)
        k = s.track('kit', patches.inst.drums(kit='909'))
        part = drummer.arrange(s, style='house', kit=k, seed=2)
        clip = part.clip
        kicks = sorted({round(n.start, 1) for n in clip if n.pitch == 36})   # machine-tight (+-1 ms)
        for bar in range(4):                                  # the drop: a kick on every beat
            for beat in range(4):
                self.assertIn(round(drop.start + bar * 4 + beat, 1), kicks)
        self.assertIn(round(intro.start, 1), kicks)
        plan = {p['name']: p for p in part.plan}
        self.assertEqual(plan['drop']['time'], 'hat')        # the style's hat_barks: open on every &
        self.assertEqual(plan['intro']['time'], 'hat8')


class LaneGlide(unittest.TestCase):
    def test_glide_after_a_move_stays_in_order(self):
        s = Song('t', tempo=120)
        a = s.section('a', bars=2)
        b = s.section('b', bars=2)
        c = s.section('c', bars=2)
        s.master.lane('fx.x.gain', {a: (-4, -1), b: 0, c: -3}, base=10, glide=1)
        pts = s.master._auto[-1][1]
        times = [p[0] for p in pts]
        self.assertEqual(times, sorted(times))
        self.assertIn((8.0, 10.0, 'step'), pts)                  # the move ends where b starts: b jumps
        self.assertIn((15.0, 10.0), pts)                          # c still glides in over one beat


class Chops(_Env):
    def _sung(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE, TEXT, at=s['a'], seed=4, tune='hard')
        return s, vo

    def test_slices_picks_and_errors(self):
        s, vo = self._sung()
        line = Clip([(0, 0.5, 'C5', 100), (0.5, 0.5, 'E5', 80), (1, 1, 'G5', 110)], length=4)
        ch = singer.chops(vo, line, at=s['b'], slices=['young', 0])
        self.assertEqual(ch.track.id, 'chops')
        self.assertEqual([s_['text'] for s_ in ch.slices][:2], ['hhowld', 'aan'])
        self.assertEqual([p[1] for p in ch.picks], [7, 0, 7])          # a word: its first syllable
        self.assertEqual(ch.picks[0][2], 72 - ch.slices[7]['pitch'])    # pitched to the line
        self.assertIn('chops', ch.describe())
        words = singer.chops(vo, line, at=s['b'], unit='word', track_id='chops_w')
        self.assertEqual(words.slices[2]['text'], 'tonight')
        self.assertEqual(len(singer.chops(vo, line, unit='phrase', track_id='chops_p').slices), 2)
        with self.assertRaises(singer.SingerError):
            singer.chops(vo, line, slices=['moon'])
        with self.assertRaises(singer.SingerError):
            singer.chops(vo, line, slices=[99])
        with self.assertRaises(singer.SingerError):
            singer.chops(vo, line, unit='letter')
        with self.assertRaises(singer.SingerError):
            singer.chops(vo, Clip([(0, 1, 'C8', 100)], length=4), slices=[0])     # > 36 st from the sung pitch
        with self.assertRaises(singer.SingerError):
            singer.chops(vo, line, track_id='vocal')                             # not a chops track

    def test_compile_writes_zones_from_the_takes(self):
        s, vo = self._sung()
        line = Clip([(0, 0.25, 'C5', 100), (0.5, 4.0, 'G5', 80)], length=8)
        singer.chops(vo, line, at=s['b'], slices=[3])
        calls = []
        with mock.patch.object(vb, 'run', _fake_run(calls)), mock.patch.object(vb, 'runner_ok', lambda: (True, '')):
            r = s.compile()
        t = next(x for x in r['tracks'] if x['id'] == 'chops')
        self.assertEqual(t['instrument']['type'], 'sampler')
        zones = t['instrument']['params']['samples']
        self.assertEqual(len(zones), 2)                                          # one zone per (slice, pitch)
        self.assertTrue(all(Path(z['file']).is_file() and z['end'] > z['offset'] for z in zones))
        self.assertEqual({z.get('tune', 0) for z in zones}, {(72 - vo.notes[3].pitch) * 100,
                                                            (79 - vo.notes[3].pitch) * 100})
        notes = t['notes']
        durs = [n['dur'] if isinstance(n, dict) else n[1] for n in notes]
        self.assertLess(durs[1], 4.0)                                            # a long note cut to its slice
        self.assertIn('eq', [f['type'] for f in t['fx']])
        self.assertTrue(any(x.startswith("chops 'chops': 2 chops") for x in singer.log_lines(s)))
        meta = json.loads(Path(vo.rendered[0]['path']).with_suffix('.json').read_text(encoding='utf-8'))
        self.assertIn('timeline', meta)


if __name__ == '__main__':
    unittest.main()
