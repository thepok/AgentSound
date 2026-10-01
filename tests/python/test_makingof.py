"""The making-of film (agentsound.makingof): reading the role files, the players' logs, the hook finder, the script
and the film builder, the timeline and its sync maths, the CLI. Rendering (Chrome / Node / ffmpeg) is exercised only
when AGENTSOUND_TEST_RENDER=1 and a built song is there."""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from agentsound import drummer  # noqa: E402
from agentsound.makingof import capture, docs, facts as factsmod, film, story, timeline  # noqa: E402
from agentsound.makingof.film import AR, Episode, Excerpt, Film, FilmError, Item, N  # noqa: E402
from agentsound.patches import inst  # noqa: E402
from agentsound.song import Song  # noqa: E402

AR_MD = """# A&R - Test Song

Judged: `song/x` @ 1a2b3c4 (mix + master).

```
verdict: revise
```

## Issues (most severe first)

1. **[blocker] The chorus buries its hook.**
   - Bar 9: the lead sits 2.1 dB under the pads.
   - **Owner:** mix-engineer.
2. **[minor] The outro is too long.**
   - Owner: arranger.

## Revision

1. **[blocker] Chorus hook -> fixed.**
   - The pads are carved: lead vs pads -2.1 -> **+3.4 dB**, width 20 / 30 % -> **35 / 41 %**.

   | measure | before | after |
   |---|---|---|
   | chorus LUFS | -14.2 | -12.9 |
2. **[minor] Outro -> unchanged.**

Verdict proposal: **ship candidate**.
"""

BRIEF_MD = """# Test Song - brief

## The wish

> "mach mal was Episches" - an epic piece

An ORIGINAL epic: something big: with parts.

## Log

- producer: brief written (wish, form). Next: arranger.
- arranger: 3 sections / 20 bars built. Open: none.
- a-and-r (AR.md): **revise** - 1 blocker.
- revision (arranger, mix-engineer; AR.md "Revision"): the hook now leads.
"""


class Docs(unittest.TestCase):
    def test_sections_tables_bullets(self):
        self.assertEqual(docs.title(AR_MD), 'A&R - Test Song')
        self.assertIn('Chorus hook', docs.section(AR_MD, 'Revision'))
        self.assertNotIn('Chorus hook', docs.section(AR_MD, 'Issues'))
        tbl = docs.tables(docs.section(AR_MD, 'Revision'))[0]
        self.assertEqual(tbl['header'], ['measure', 'before', 'after'])
        self.assertEqual(tbl['rows'], [['chorus LUFS', '-14.2', '-12.9']])

    def test_arrow_pairs(self):
        ps = docs.arrow_pairs("The pads are carved: lead vs pads -2.1 -> **+3.4 dB**, width 20 / 30 % -> **35 / 41 %**.")
        self.assertEqual([(p['label'], p['before'], p['after'], p['unit'], p['key']) for p in ps],
                         [('lead vs pads', -2.1, 3.4, 'dB', True), ('width', 20.0, 35.0, '%', True)])
        # a unit named only after the second pair is shared
        ps = docs.arrow_pairs("Bar 74 (fermata) -10.1 -> **-12.7**, bar 75 (riff) -13.7 -> **-12.6** LUFS.")
        self.assertEqual([(p['label'], p['unit']) for p in ps], [('Bar 74 (fermata)', 'LUFS'), ('bar 75 (riff)', 'LUFS')])

    def test_ar_issues_revision_verdict(self):
        self.assertEqual(docs.ar_verdict(AR_MD), 'revise')
        iss = docs.ar_issues(AR_MD)
        self.assertEqual([(i['n'], i['severity']) for i in iss], [(1, 'blocker'), (2, 'minor')])
        self.assertEqual(iss[0]['title'], 'The chorus buries its hook')
        self.assertEqual(iss[0]['owner'], 'mix-engineer')
        rev = docs.ar_revision(AR_MD)
        self.assertEqual([r['status'] for r in rev], ['fixed', 'unchanged'])
        labels = [p['label'] for p in rev[0]['pairs']]
        self.assertIn('chorus LUFS', labels)
        self.assertIn('lead vs pads', labels)
        self.assertEqual(docs.ar_proposal(AR_MD), 'ship candidate')

    def test_brief_wish_and_log(self):
        w = docs.wish(BRIEF_MD)
        self.assertIn('mach mal was Episches', w['quote'])
        self.assertTrue(w['summary'].startswith('An ORIGINAL epic'))
        log = docs.log_entries(BRIEF_MD)
        self.assertEqual([e['who'] for e in log], [['producer'], ['arranger'], ['a-and-r'], ['arranger', 'mix-engineer']])
        self.assertTrue(log[3]['revision'])


class Hook(unittest.TestCase):
    def test_skyline_ignores_the_left_hand_under_a_held_note(self):
        notes = [(0, 1.0, 67, 80), (1, 2.0, 75, 90),       # G4, then a held Eb5
                 (1.5, 0.4, 48, 50), (2.0, 0.4, 55, 50),   # left-hand 8ths under it
                 (3, 1.0, 74, 80), (4, 1.0, 72, 80)]       # D5 C5
        self.assertEqual([n[2] for n in factsmod.top_line(notes)], [67, 75, 74, 72])

    def test_motif_text_and_finder(self):
        self.assertEqual(factsmod.motif_from_text("the curtain motif (G4 - Eb5 - D5 - C5) returns"), [67, 75, 74, 72])
        tracks = [
            {'id': 'piano', 'family': 'piano', 'notes': [[0, 0.5, 67, 80], [0.5, 1, 75, 90], [1.5, .5, 74, 80],
                                                         [2, 1, 72, 80]]},
            # a major transformation a fifth up (G4 E5 D5 C5 -> D5 B5 A5 G5) on another track, later
            {'id': 'violins', 'family': 'strings', 'notes': [[10, 0.5, 74, 80], [10.5, 1, 83, 90], [11.5, .5, 81, 80],
                                                             [12, 1, 79, 80]]},
            {'id': 'kit', 'family': 'drums', 'notes': [[0, .1, 36, 100], [0.5, .1, 44, 100], [1, .1, 43, 100],
                                                       [1.5, .1, 41, 100]]},
        ]
        occ = factsmod.find_hook(tracks, [67, 75, 74, 72])
        self.assertEqual([(o['t'], o['tracks']) for o in occ], [(0, ['piano']), (10, ['violins'])])

    def test_note_names(self):
        self.assertEqual(factsmod.note_name(63), 'Eb4')
        self.assertEqual(factsmod.midi('C#5'), 73)


class PlayersLogs(unittest.TestCase):
    def test_a_drummer_placement_is_recorded_at_its_beat(self):
        with capture.recording() as log:
            s = Song('t', tempo=120)
            s.section('intro', bars=2)
            v = s.section('verse', bars=4)
            s.section('chorus', bars=4)
            t = s.track('drums', inst.drums())
            part = drummer.arrange([v, s['chorus']], bpm=120, style='rock', seed=3)
            part.play(t)
        self.assertEqual(len(log), 1)
        self.assertEqual((log[0]['player'], log[0]['track'], log[0]['at']), ('drummer', 'drums', v.start))
        mv = capture.absolute_moves(log)
        self.assertTrue(all(m['beat'] >= v.start for m in mv))
        self.assertTrue(any(m['kind'] == 'groove' for m in mv))

    def test_patches_are_undone(self):
        from agentsound.song import Track
        before = Track.play
        with capture.recording():
            self.assertIsNot(Track.play, before)
        self.assertIs(Track.play, before)


def stub_facts() -> dict:
    secs = [{'name': 'intro', 'start': 0.0, 'end': 10.0, 'level': 0.1, 'lufs': -24.0, 'part': 'I', 'key': 'C minor',
             'bpm': 90},
            {'name': 'chorus', 'start': 10.0, 'end': 30.0, 'level': 1.0, 'lufs': -11.0, 'part': 'I', 'key': 'C minor',
             'bpm': 90},
            {'name': 'outro', 'start': 30.0, 'end': 40.0, 'level': 0.4, 'lufs': -18.0, 'part': 'II', 'key': 'C major',
             'bpm': 80}]
    return {'slug': 'test', 'title': 'Test', 'genre': 'Synthwave', 'genre_text': '', 'profile': 'synthwave',
            'duration': 42.0, 'sections': secs, 'parts': [], 'items': [], 'issues': [], 'bars': 20,
            'hook': {'occurrences': [{'t': 12.0, 'end': 14.0, 'tracks': ['lead'], 'section': 'chorus'}]},
            'tracks': [{'id': 'lead', 'family': 'piano', 'notes': [[1, 1, 60, 90]]}],
            'moves': [{'t': 12.5, 'end': 12.5, 'player': 'drummer', 'track': 'kit', 'kind': 'crash', 'name': 'crash',
                       'pop': True}],
            'barTimes': [0, 2.67, 5.33, 8, 10.67, 13.33, 16, 18.67, 21.33, 24, 26.67, 29.33, 32, 34.67, 37.33],
            'players': ['drummer'], 'soundRows': [], 'soundMeasured': [], 'log': [], 'wish': {'quote': '', 'summary': ''},
            'verdict': '', 'revision': [], 'proposal': '', 'meters': ['4/4'], 'bpmRange': [80, 90], 'key': ''}


class Timeline(unittest.TestCase):
    def test_sync_maths(self):
        self.assertEqual(timeline.frame_of(1.0, 30), 30)
        self.assertEqual(timeline.frame_of(1.0166, 30), 30)
        self.assertEqual(timeline.frame_of(1.0170, 30), 31)
        segs = [{'kind': 'song', 'v0': 100.0, 'v1': 142.0, 's0': 0.0}]
        self.assertEqual(timeline.song_time(112.5, segs), 12.5)
        self.assertIsNone(timeline.song_time(99.0, segs))
        self.assertEqual(timeline.video_time(12.5, segs[0]), 112.5)

    def test_duck_envelope(self):
        env = timeline.duck_envelope(10.0, -11, -21, [(2.0, 4.0)], 1.0, 1.0)
        self.assertEqual(timeline.gain_at(env, 0.0), -60)
        self.assertAlmostEqual(timeline.gain_at(env, 1.5), -11)
        self.assertAlmostEqual(timeline.gain_at(env, 3.0), -21)
        self.assertAlmostEqual(timeline.gain_at(env, 6.0), -11)
        self.assertEqual(timeline.gain_at(env, 10.0), -60)

    def test_layout_chapters_captions_and_moves_on_their_frame(self):
        f = Film(stub_facts())
        f.cold_open(N("It started with a wish."))
        f.act(['chorus'], N("The chorus."), scene='grid', play=6)
        f.song(N("And now, Test."))
        f.credits()
        durations = {id(ln): 2.0 for c in f.chapters for ln in c.lines}
        tl = timeline.layout(f.chapters, durations, stub_facts(), fps=30)
        chs = tl['chapters']
        self.assertEqual([c['kind'] for c in chs], ['cold', 'act', 'song', 'end'])
        for a, b in zip(chs, chs[1:]):
            self.assertEqual(a['t1'], b['t0'])
        for cap in tl['captions']:
            ch = next(c for c in chs if c['id'] == cap['chapter'])
            self.assertTrue(ch['t0'] <= cap['t0'] < cap['t1'] <= ch['t1'], cap)
        song = next(s for s in tl['segments'] if s['kind'] == 'song')
        self.assertEqual(song['v1'] - song['v0'], 42.0)
        sync = timeline.check_sync(tl, stub_facts()['moves'])
        crash = [x for x in sync if abs(x['video'] - (song['v0'] + 12.5)) < 1e-9]
        self.assertEqual(len(crash), 1)
        self.assertEqual(crash[0]['frame'], round((song['v0'] + 12.5) * 30))
        act = next(s for s in tl['segments'] if s['kind'] == 'act')
        self.assertEqual(act['s0'], 10.0)
        self.assertEqual(tl['frames'], -(-tl['duration'] * 30 // 1))

    def test_scene_plan_and_overrides(self):
        plan = timeline.scene_plan(stub_facts())
        self.assertEqual([p['section'] for p in plan], ['intro', 'chorus', 'outro'])
        self.assertTrue(all(p['scene'] in timeline.SCENES for p in plan))
        self.assertEqual(plan[-1]['s1'], 42.0)
        plan = timeline.scene_plan(stub_facts(), {'chorus': 'mandala'}, {'chorus'})
        self.assertEqual((plan[1]['scene'], plan[1]['highway']), ('mandala', True))


class FilmBuilder(unittest.TestCase):
    def test_validation(self):
        f = Film(stub_facts())
        with self.assertRaises(FilmError):
            f.act('nope')
        with self.assertRaises(FilmError):
            f.cold_open(N('x' * 300))
        with self.assertRaises(FilmError):
            f.look(scenes={'intro': 'fireworks'})
        with self.assertRaises(FilmError):
            f.tracks(items=[Item('x', ['nope'], 1.0)])
        c = f.act('I', AR("Loud."), scene='ring+hw')
        self.assertEqual((c.kind, c.opts['sections'], c.opts['highway']), ('act', ['intro', 'chorus'], True))
        self.assertEqual(c.lines[0].voice, 'ar')
        c2 = f.act('outro')
        self.assertEqual(c2.id, 'act2')
        ep = f.tried(episodes=[1, Episode(2, before_lines=["before"])])
        self.assertEqual([e.n for e in ep.episodes], [1, 2])
        self.assertEqual(ep.episodes[1].before_lines[0].voice, 'narrator')

    def test_speakable(self):
        s = story.speakable("-12.6 LUFS, +5 dB at 5:52 in 3/4: G4, Eb5 -> 31.7 %, -14.9..-12.9 A&R")
        self.assertIn('minus 12.6 LUFS', s)
        self.assertIn('plus 5 decibels', s)
        self.assertIn('5 minutes 52', s)
        self.assertIn('three-four', s)
        self.assertIn('G, E flat', s)
        self.assertIn('31.7 percent', s)
        self.assertIn('14.9 to minus 12.9', s)
        self.assertIn('A and R', s)


BUILT = REPO / 'songs' / 'ashes-and-chandeliers' / 'out' / 'report.json'


@unittest.skipUnless(BUILT.is_file() and os.environ.get('AGENTSOUND_SAMPLES') or BUILT.is_file(),
                     'the pilot song is not built')
class BuiltSong(unittest.TestCase):
    """On a built song: facts, the generated draft (it must load), the CLI's --script."""

    @classmethod
    def setUpClass(cls):
        cache = REPO / 'songs' / 'ashes-and-chandeliers' / 'out' / 'makingof' / 'moves.json'
        log = json.loads(cache.read_text(encoding='utf-8'))['log'] if cache.is_file() else []
        cls.facts = factsmod.collect(REPO / 'songs' / 'ashes-and-chandeliers', moves_log=log)

    def test_facts(self):
        f = self.facts
        self.assertEqual(f['title'], 'Ashes and Chandeliers')
        self.assertEqual(len(f['sections']), 19)
        self.assertEqual(f['hook']['names'], ['G4', 'Eb5', 'D5', 'C5'])
        self.assertGreaterEqual(len(f['hook']['occurrences']), 9)
        self.assertEqual(f['verdict'], 'revise')
        self.assertTrue(f['credits']['attribution'])

    def test_the_draft_loads(self):
        from agentsound.makingof import draft
        with tempfile.TemporaryDirectory() as d:
            fl = draft.load_source(draft.draft_source(self.facts), self.facts, pathlib.Path(d) / 'film.py')
        kinds = [c.kind for c in fl.chapters]
        self.assertEqual(kinds[0], 'cold')
        self.assertIn('song', kinds)
        self.assertEqual(kinds[-1], 'end')

    def test_cli_script(self):
        if not (REPO / 'songs' / 'ashes-and-chandeliers' / 'out' / 'makingof' / 'moves.json').is_file():
            self.skipTest('the players’ logs are not cached (run makingof once)')
        md = REPO / 'songs' / 'ashes-and-chandeliers' / 'making-of.md'
        existed = md.is_file()
        r = subprocess.run([sys.executable, '-m', 'agentsound', 'makingof', 'songs/ashes-and-chandeliers', '--script'],
                           cwd=REPO, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        text = md.read_text(encoding='utf-8')
        self.assertIn('## cold', text)
        if not existed:
            md.unlink()


@unittest.skipUnless(os.environ.get('AGENTSOUND_TEST_RENDER') == '1' and BUILT.is_file()
                     and shutil.which('node') and shutil.which('ffmpeg'), 'rendering not requested / tools missing')
class Render(unittest.TestCase):
    def test_stills(self):
        r = subprocess.run([sys.executable, '-m', 'agentsound', 'makingof', 'songs/ashes-and-chandeliers', '--tts',
                            'none', '--preview', '--stills', '5,60'], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)


class Cli(unittest.TestCase):
    def test_parser(self):
        from agentsound import cli
        ap = cli.build_parser()
        a = ap.parse_args(['makingof', 'songs/x', '--draft', '--tts', 'none', '--stills', '1,2'])
        self.assertTrue(a.draft)
        self.assertEqual((a.tts, a.stills, a.workers), ('none', '1,2', 3))


if __name__ == '__main__':
    unittest.main()
