import contextlib
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import cli, patches
from agentsound.patches import Patch
from dx7_banks import needs_dx7

SONG = '''
from agentsound import *

def build():
    s = Song('Cli Test', tempo=110, key='E minor', seed=2)
    a = s.section('a', bars=2)
    b = s.section('b', bars=2)
    t = s.track('keys', inst.dx7('E.PIANO 1'))
    t.play(s.prog('i iv').block(), a)
    t.play(s.prog('VI VII').block(), b)
    s.master.add(fx.limiter())
    return s
'''

BAD_SONG = '''
from agentsound import *

def build():
    s = Song('Bad', tempo=110)
    s.section('a', bars=1)
    s.track('t', inst.va()).play(chord('Hm7'), 0)
    return s
'''


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


class SongCommands(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_cli_'))
        (self.dir / 'good').mkdir()
        (self.dir / 'good' / 'song.py').write_text(SONG, encoding='utf-8')
        (self.dir / 'bad').mkdir()
        (self.dir / 'bad' / 'song.py').write_text(BAD_SONG, encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_check_writes_render_json(self):
        code, out, err = run(['check', str(self.dir / 'good'), '--engine', str(self.dir / 'missing.exe')])
        self.assertEqual(code, 0, err)
        self.assertIn('engine validation skipped', out)
        rj = self.dir / 'good' / 'out' / 'song.render.json'
        data = json.loads(rj.read_text(encoding='utf-8'))
        self.assertEqual(data['title'], 'Cli Test')
        self.assertEqual(data['lengthBeats'], 16.0)
        self.assertIn('ok:', out)

    def test_build_without_engine_is_clear(self):
        code, out, err = run(['build', str(self.dir / 'good'), '--engine', str(self.dir / 'missing.exe'), '--no-mp3'])
        self.assertEqual(code, 3)
        self.assertIn('engine not found', err)
        self.assertTrue((self.dir / 'good' / 'out' / 'song.render.json').is_file())

    def test_song_error_points_at_line(self):
        code, out, err = run(['check', str(self.dir / 'bad')])
        self.assertEqual(code, 1)
        self.assertIn("Hm7", err)
        self.assertIn('song.py:7', err)

    def test_missing_song(self):
        code, out, err = run(['check', str(self.dir / 'nothing')])
        self.assertEqual(code, 1)
        self.assertIn('no song at', err)

    def test_unknown_section(self):
        code, out, err = run(['build', str(self.dir / 'good'), '--section', 'chorus', '--engine', 'x'])
        self.assertEqual(code, 1)
        self.assertIn("no section 'chorus'", err)


class Audition(unittest.TestCase):
    def tearDown(self):
        for n in [n for n in patches._REGISTRY if n.startswith('test/')]:
            del patches._REGISTRY[n]

    def test_audition_songs_compile(self):
        patches.register(Patch('test/bass', {'type': 'va'}, sends={'hall': -12, 'echo': -20}))
        patches.register(Patch('test/kit', {'type': 'drums'}))
        patches.register(Patch('test/pad', {'type': 'va'}))
        for name, kind, expect in (('test/bass', 'auto', 'bass'), ('test/kit', 'auto', 'drums'),
                                   ('test/pad', 'auto', 'chord'), ('test/pad', 'phrase', 'phrase'),
                                   ('test/pad', 'arp', 'arp')):
            song = cli.audition_song(name, kind)
            r = song.compile()
            self.assertEqual(r['lengthBeats'], 16.0)
            notes = r['tracks'][0]['notes']
            self.assertTrue(notes, (name, kind))
            if expect == 'drums':
                self.assertIn(36, {n[2] for n in notes})
            if name == 'test/bass':
                self.assertEqual(sorted(b['id'] for b in r['buses']), ['echo', 'hall'])

    def _notes(self, name, kind='auto'):
        r = cli.audition_song(name, kind).compile()
        self.assertEqual(r['lengthBeats'], 16.0)
        return r['tracks'][0]

    def test_audition_material_per_name(self):
        riser_notes = ('Play: one long note.\nAutomate (required):\n'
                       '  instrument.cutoff  riser(drop, length=L, lo=300, hi=12000)   (the sweep)\n'
                       '  instrument.hpf     riser(drop, length=L, lo=20, hi=1500)\n'
                       "Example: r.automate('instrument.cutoff', riser(chorus, length=16, lo=1, hi=2))")
        for n in ('rolling_bass', 'sub_bass', 'moog_bass', 'octave_bass', 'arp_pluck', 'marimba', 'seq_pulse',
                  'poly_stab', 'brass_stab', 'downlifter', 'impact', 'laser', 'supersaw_lead', 'brass_lead', 'warm_pad',
                  'epiano'):
            patches.register(Patch(f'test/{n}', {'type': 'va'}))
        patches.register(Patch('test/noise_riser', {'type': 'va'}, notes=riser_notes))
        patches.register(Patch('test/kit', {'type': 'drums'}))
        expect = {'rolling_bass': 'rolling', 'sub_bass': 'roots', 'moog_bass': 'roots', 'octave_bass': 'bass',
                  'arp_pluck': 'arp', 'marimba': 'arp', 'seq_pulse': 'arp', 'poly_stab': 'stab', 'brass_stab': 'stab',
                  'noise_riser': 'riser', 'downlifter': 'riser', 'impact': 'hit', 'laser': 'hit', 'supersaw_lead': 'phrase',
                  'brass_lead': 'phrase', 'warm_pad': 'chord', 'epiano': 'chord', 'kit': 'drums'}
        for n, kind in expect.items():
            self.assertEqual(cli._guess_kind(patches.get(f'test/{n}')), kind, n)
        # Short category words match only at a word start: no 'hit' in 'white', no 'arp' in 'harp'.
        for n, kind in (('white_noise_pad', 'chord'), ('harp', 'phrase'), ('stranger_arp', 'arp'), ('big_hit', 'hit'),
                        ('minimoog_bass', 'roots'), ('hihat', 'drums'), ('808_perc', 'drums')):
            self.assertEqual(cli._guess_kind(Patch(f'test/{n}', {'type': 'va'})), kind, n)

        starts = lambda t: sorted({n[0] for n in t['notes']})
        t = self._notes('test/rolling_bass')                       # 16ths, root/octave
        self.assertEqual(len(t['notes']), 64)
        self.assertEqual(starts(t)[:3], [0.0, 0.25, 0.5])
        t = self._notes('test/octave_bass')                        # 8th pulse
        self.assertEqual(len(t['notes']), 32)
        self.assertEqual(starts(t)[:3], [0.0, 0.5, 1.0])
        for n in ('sub_bass', 'moog_bass'):                        # held whole-bar roots
            t = self._notes(f'test/{n}')
            self.assertEqual(starts(t), [0.0, 4.0, 8.0, 12.0])
            self.assertTrue(all(x[1] >= 3.5 and x[2] < 48 for x in t['notes']), t['notes'])
        for n in ('arp_pluck', 'marimba'):                         # 16th arpeggio, one note per step
            t = self._notes(f'test/{n}')
            self.assertEqual(len(t['notes']), 64)
            self.assertEqual(len(starts(t)), 64)
        t = self._notes('test/poly_stab')                          # 3-3-2 stabs: short 3-note chords
        self.assertEqual(starts(t)[:3], [0.0, 1.5, 3.0])
        self.assertEqual(len(t['notes']), 3 * 3 * 4)
        self.assertTrue(all(x[1] <= 0.25 for x in t['notes']))
        t = self._notes('test/noise_riser')                        # one long note + the automation its notes prescribe
        self.assertEqual(t['notes'], [[0.0, 16.0, 57, 100]])
        lanes = {a['target']: a['points'] for a in t['automation']}
        self.assertEqual(lanes, {'instrument.cutoff': [[0.0, 300.0], [16.0, 12000.0, 'exp']],
                                 'instrument.hpf': [[0.0, 20.0], [16.0, 1500.0, 'exp']]})
        t = self._notes('test/downlifter')                         # self-contained: no automation
        self.assertEqual((len(t['notes']), t['automation']), (1, []))
        t = self._notes('test/impact')                             # single hits at the key root, octave 1
        self.assertEqual([(n[0], n[2]) for n in t['notes']], [(0.0, 33), (8.0, 33)])
        t = self._notes('test/laser')                              # short high shots
        self.assertEqual([(n[0], n[1], n[2]) for n in t['notes']], [(0.0, 0.5, 81), (8.0, 0.5, 81)])
        self.assertEqual(len(self._notes('test/supersaw_lead')['notes']), 15)    # the 4-bar phrase
        t = self._notes('test/warm_pad')                           # held 4-note chords
        self.assertEqual(len(t['notes']), 16)
        self.assertTrue(all(x[1] > 3.5 for x in t['notes']))
        self.assertIn(36, {n[2] for n in self._notes('test/kit')['notes']})

    def test_audition_notes_override_and_aliases(self):
        patches.register(Patch('test/pad', {'type': 'va'}))
        for name, material in (('riser', 'riser'), ('downlifter', 'riser'), ('impact', 'hit'), ('hit', 'hit'),
                               ('rolling', 'rolling'), ('sub', 'roots'), ('moog', 'roots'), ('roots', 'roots'),
                               ('pulse', 'bass'), ('bass', 'bass'), ('pluck', 'arp'), ('marimba', 'arp'), ('arp', 'arp'),
                               ('stab', 'stab'), ('lead', 'phrase'), ('pad', 'chord'), ('groove', 'drums'), ('Riser', 'riser')):
            self.assertEqual(cli.audition_material(name), material, name)
        self.assertEqual(self._notes('test/pad', 'impact')['notes'][0][2], 33)
        self.assertEqual(len(self._notes('test/pad', 'rolling')['notes']), 64)
        self.assertEqual(len(self._notes('test/pad', 'sub')['notes']), 4)
        self.assertEqual(len(self._notes('test/pad', 'downlifter')['notes']), 1)
        with self.assertRaisesRegex(cli.CliError, "unknown --notes 'riserr' - did you mean 'riser'"):
            cli.audition_song('test/pad', 'riserr')
        args = cli.build_parser().parse_args(['audition', 'test/pad', '--notes', 'Downlifter'])
        self.assertEqual(args.notes, 'downlifter')
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.build_parser().parse_args(['audition', 'test/pad', '--notes', 'bogus'])

    def test_audition_hint(self):
        hint = {'notes': 'riser', 'automate': {'instrument.cutoff': [[0, 200], [16, 8000, 'exp']]}}
        p = patches.register(Patch('test/whoosh', {'type': 'va'}, audition=hint))
        hint['notes'] = 'chord'                                    # the patch keeps its own copy
        q = patches.get('test/whoosh')
        self.assertEqual(q.audition['notes'], 'riser')
        self.assertEqual(q.copy().audition, q.audition)
        self.assertEqual(q.to_dict()['audition'], q.audition)
        self.assertNotIn('audition', Patch('test/x', {'type': 'va'}).to_dict())
        self.assertEqual(p, q)
        t = self._notes('test/whoosh')                             # hint picks the material and the automation
        self.assertEqual(len(t['notes']), 1)
        self.assertEqual(t['automation'], [{'target': 'instrument.cutoff', 'points': [[0, 200], [16, 8000, 'exp']]}])
        t = self._notes('test/whoosh', 'chord')                    # --notes wins; the patch's automation stays
        self.assertEqual(len(t['notes']), 16)
        self.assertEqual(len(t['automation']), 1)
        patches.register(Patch('test/boom', {'type': 'va'}, audition={'notes': 'impact', 'pitch': 'E1', 'length': 4}))
        t = self._notes('test/boom')
        self.assertEqual([n[:3] for n in t['notes']], [[0.0, 4.0, 28], [8.0, 4.0, 28]])
        from agentsound.theory import ComposeError
        with self.assertRaises(ComposeError):
            Patch('test/bad', {'type': 'va'}, audition='riser')
        patches.register(Patch('test/bad1', {'type': 'va'}, audition={'note': 'riser'}))
        with self.assertRaisesRegex(cli.CliError, "unknown key\\(s\\) 'note'"):
            cli.audition_song('test/bad1')
        patches.register(Patch('test/bad2', {'type': 'va'}, audition={'notes': 'riser', 'length': 99}))
        with self.assertRaisesRegex(cli.CliError, "'length' must be beats"):
            cli.audition_song('test/bad2')

    def test_patches_listing(self):
        patches.register(Patch('test/lead', {'type': 'va'}, notes='Bright lead'))
        code, out, err = run(['patches', 'test/'])
        self.assertEqual(code, 0)
        self.assertIn('test/lead', out)
        self.assertIn('Bright lead', out)
        code, out, err = run(['patches', 'nothing/'])
        self.assertIn('no patches', out)


class AnalysisSettings(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_prof_'))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def song(self, extra: str) -> pathlib.Path:
        (self.dir / 'song.py').write_text(SONG + extra, encoding='utf-8')
        return self.dir

    def render_json(self) -> dict:
        return json.loads((self.dir / 'out' / 'song.render.json').read_text(encoding='utf-8'))

    def test_check_analysis(self):
        self.assertEqual(cli.check_analysis({}), {})
        self.assertEqual(cli.check_analysis({'profile': 'synthwave', 'loudness': (-12, -9)}),
                         {'profile': 'synthwave', 'loudness': [-12.0, -9.0]})
        for bad, msg in (('synthwave', 'must be a dict'), ({'profil': 'synthwave'}, "unknown key\\(s\\) 'profil'"),
                         ({'profile': 'synthwav'}, "unknown analysis profile 'synthwav' - did you mean 'synthwave'"),
                         ({'profile': 'outrun'}, 'profiles: default, synthwave, dreamwave, darksynth'),
                         ({'loudness': [-9, -12]}, 'min < max'), ({'loudness': [-12]}, 'minLufs, maxLufs'),
                         ({'loudness': [-80, -9]}, '-60 <= min'), ({'loudness': [-12, True]}, 'minLufs'),
                         ({'loudness': [-12, float('nan')]}, 'minLufs')):
            with self.assertRaisesRegex(cli.CliError, msg):
                cli.check_analysis(bad)

    def test_apply_analysis_precedence(self):
        r = {'analysis': {'profile': 'dreamwave', 'loudness': [-14, -10]}}
        self.assertEqual(cli.apply_analysis(r, {'profile': 'synthwave'}), {'profile': 'synthwave', 'loudness': [-14.0, -10.0]})
        self.assertEqual(cli.apply_analysis(r, {'loudness': [-11, -8]}, 'darksynth'),
                         {'profile': 'darksynth', 'loudness': [-11.0, -8.0]})
        self.assertEqual(r['analysis'], {'profile': 'darksynth', 'loudness': [-11.0, -8.0]})
        r = {}
        self.assertEqual(cli.apply_analysis(r, None, None), {})
        self.assertNotIn('analysis', r)
        self.assertEqual(cli.apply_analysis(r, {}, None), {})
        self.assertNotIn('analysis', r)
        with self.assertRaisesRegex(cli.CliError, 'my.py: ANALYSIS: unknown analysis profile'):
            cli.apply_analysis({}, {'profile': 'x'}, None, 'my.py: ANALYSIS')
        # the compiler's own keys (silent notes, a singer's phrase-trigger tracks) pass through untouched
        r = {'analysis': {'audioOnsets': ['vocal'], 'silentNotes': [{'track': 'x'}]}}
        self.assertEqual(cli.apply_analysis(r, {'profile': 'jazz'}), {'profile': 'jazz'})
        self.assertEqual(r['analysis'], {'profile': 'jazz', 'audioOnsets': ['vocal'], 'silentNotes': [{'track': 'x'}]})

    def test_song_file_analysis_and_profile_flag(self):
        d = self.song("\nANALYSIS = {'profile': 'synthwave', 'loudness': [-12, -9]}\n")
        missing = str(self.dir / 'missing.exe')
        code, out, err = run(['check', str(d), '--engine', missing])
        self.assertEqual(code, 0, err)
        self.assertEqual(self.render_json()['analysis'], {'profile': 'synthwave', 'loudness': [-12.0, -9.0]})
        code, out, err = run(['check', str(d), '--engine', missing, '--profile', 'darksynth'])
        self.assertEqual(code, 0, err)
        self.assertEqual(self.render_json()['analysis'], {'profile': 'darksynth', 'loudness': [-12.0, -9.0]})
        code, out, err = run(['build', str(d), '--engine', missing, '--no-mp3', '--profile', 'dreamwave'])
        self.assertEqual(code, 3)                                  # no engine, but the render JSON is written first
        self.assertEqual(self.render_json()['analysis']['profile'], 'dreamwave')
        self.assertIn("analysis  profile 'dreamwave', loudness target -12..-9 LUFS", out)
        d = self.song('')                                          # no ANALYSIS, no flag: no "analysis" key
        code, out, err = run(['check', str(d), '--engine', missing])
        self.assertEqual(code, 0, err)
        self.assertNotIn('analysis', self.render_json())
        d = self.song("\nANALYSIS = {'profile': 'outrun'}\n")
        code, out, err = run(['check', str(d), '--engine', missing])
        self.assertEqual(code, 1)
        self.assertIn("song.py: ANALYSIS: unknown analysis profile 'outrun'", err)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.build_parser().parse_args(['build', str(d), '--profile', 'outrun'])


class ReportSummary(unittest.TestCase):
    def write(self, obj) -> pathlib.Path:
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_rep_'))
        self.addCleanup(shutil.rmtree, d, True)
        p = d / 'report.json'
        p.write_text(json.dumps(obj) if not isinstance(obj, str) else obj, encoding='utf-8')
        return p

    def test_engine_style_report(self):
        rep = {'format': 'agentsound.report', 'summary': '1:00 | -12.0 LUFS-I',
               'global': {'lufsIntegrated': -12.0, 'truePeakDbtp': -1.1},
               'sections': [{'name': 'intro', 'lufs': -16.2, 'peakDb': -6.0, 'rmsDb': -18.0}],
               'nodes': [{'id': 'bass', 'lufs': -20.0, 'peakDb': -9.0}, {'id': 'hall', 'bus': True, 'rmsDb': -30.0}],
               'warnings': [{'severity': 'warn', 'code': 'dull', 'message': 'too dark'}],
               'suggestions': ['open the filters']}
        s = cli.summarize_report(self.write(rep))
        self.assertIn('-12.0 LUFS-I', s)
        self.assertIn('intro', s)
        self.assertIn('-16.2 LUFS', s)
        self.assertIn('hall (bus)', s)
        self.assertIn('[warn] dull: too dark', s)
        self.assertIn('open the filters', s)

    def test_clicks_and_images(self):
        rep = {'summary': 'x', 'warnings': [],
               'clicks': [{'severity': 'high', 'time': '1:23.456', 'sec': 83.456, 'bar': 35, 'beat': 2.31, 'node': 'bass',
                           'inMix': True, 'jumpDb': -28.1, 'contrastDb': 34.0, 'channel': 'both', 'image': 'clicks/click_01.png'},
                          {'severity': 'low', 'time': '0:10.000', 'sec': 10.0, 'bar': 5, 'beat': 1.0, 'node': 'pad',
                           'inMix': False, 'jumpDb': -47.0, 'contrastDb': 15.0, 'channel': 'L'}],
               'images': [{'file': 'overview.png', 'shows': 'dashboard and index'},
                          {'file': 'clicks/click_01.png', 'shows': 'click #1 at 1:23.456'}]}
        p = self.write(rep)
        s = cli.summarize_report(p)
        self.assertIn('clicks (1 in the mix, 1 masked in single parts', s)
        self.assertIn("1:23.456  bar 35 beat 2.31  'bass'  jump -28.1 dBFS", s)
        self.assertIn('clicks/click_01.png', s)
        self.assertIn('(masked)', s)
        lines = cli.image_lines(p)
        self.assertIn('overview.png is the index', lines[0])
        self.assertTrue(any('clicks/click_01.png' in ln and 'click #1' in ln for ln in lines))
        # No 'images' key: the PNGs next to the report are listed.
        q = self.write({'summary': 'x'})
        (q.parent / 'spectrogram.png').write_bytes(b'png')
        (q.parent / 'clicks').mkdir()
        (q.parent / 'clicks' / 'click_01.png').write_bytes(b'png')
        lines = cli.image_lines(q)
        self.assertTrue(any('spectrogram.png' in ln for ln in lines) and any('clicks/click_01.png' in ln for ln in lines))
        self.assertEqual(cli.image_lines(self.write({'summary': 'x'})), [])
        self.assertNotIn('clicks (', cli.summarize_report(self.write({'summary': 'x', 'clicks': []})))
        # The engine lists the worst 40 clicks; the global totals count all of them.
        many = dict(rep, clicks=[dict(rep['clicks'][0], time=f'0:{i:02d}.000') for i in range(40)],
                    **{'global': {'clicks': 55, 'clicksMasked': 3}})
        s = cli.summarize_report(self.write(many))
        self.assertIn('clicks (55 in the mix, 3 masked in single parts', s)
        self.assertIn('... 50 more (report.json lists the worst 40)', s)

    def test_note_dynamics(self):
        rep = {'summary': 'x', 'reference': {'noteSpreadMinDb': 3.0},
               'nodes': [{'id': 'hook', 'dynamics': {'kind': 'lead', 'judged': True, 'flat': True, 'onsets': 'notes', 'notes': 112,
                                                     'spreadDb': 5.1, 'phraseSpreadDb': 4.8, 'dynamicsDb': 0.6,
                                                     'velocityPhraseDb': 0.6, 'phrases': 5, 'flatPhrases': 5,
                                                     'thresholdDb': 3.0, 'velocity': {'min': 81, 'max': 103, 'p10': 84, 'p90': 101}}},
                         {'id': 'sax', 'dynamics': {'kind': 'lead', 'judged': True, 'flat': False, 'onsets': 'notes', 'notes': 64,
                                                    'spreadDb': 9.0, 'phraseSpreadDb': 7.9, 'phrases': 4, 'flatPhrases': 0,
                                                    'thresholdDb': 3.0}},
                         {'id': 'arp', 'dynamics': {'kind': 'even', 'judged': False, 'flat': False, 'notes': 512, 'spreadDb': 0.4}},
                         {'id': 'ghost', 'dynamics': {'kind': 'lead', 'judged': True, 'flat': True, 'notes': 9, 'spreadDb': 0.1}},
                         {'id': 'kick'}]}
        s = cli.summarize_report(self.write(rep), hide={'ghost'})
        self.assertIn('note dynamics (played note-to-note dynamics per phrase, 10-90 %; flat under 3 dB):', s)
        self.assertRegex(s, r"hook\s+lead\s+0\.6 dB FLAT\s+\(112 notes, vel 81-103, audio 4\.8 dB, from velocity 0\.6 dB, "
                            r"5/5 phrases flat\)")
        self.assertRegex(s, r"sax\s+lead\s+7\.9 dB\s+\(64 notes")
        self.assertIn('not judged: arp (even 0.4 dB)', s)
        self.assertNotIn('ghost', s)
        self.assertNotIn('note dynamics', cli.summarize_report(self.write({'summary': 'x', 'nodes': [{'id': 'kick'}]})))

    def test_unknown_or_partial_reports(self):
        s = cli.summarize_report(self.write({'loudness': {'integrated': -14.5, 'truePeak': -0.9}, 'x': 1}))
        self.assertIn('integrated -14.5 LUFS', s)
        self.assertIn('true peak -0.9 dBTP', s)
        s = cli.summarize_report(self.write({'weird': 'stuff'}))
        self.assertIn('keys: weird', s)
        self.assertIn('unreadable', cli.summarize_report(self.write('{not json')))
        self.assertIn('missing', cli.summarize_report(pathlib.Path(tempfile.gettempdir()) / 'nope' / 'report.json'))
        s = cli.summarize_report(self.write([1, 2]))
        self.assertIn('unexpected', s)


class Zoom(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_zoom_'))
        self.addCleanup(shutil.rmtree, self.dir, True)
        (self.dir / 'song.py').write_text(SONG, encoding='utf-8')

    def test_targets(self):
        with self.assertRaisesRegex(cli.CliError, 'no render at .*mix.wav: build it first'):
            cli.zoom_target(str(self.dir))
        out = self.dir / 'out'
        (out / 'stems').mkdir(parents=True)
        (out / 'mix.wav').write_bytes(b'RIFF')
        (out / 'stems' / 'bass.wav').write_bytes(b'RIFF')
        wav, rdir = cli.zoom_target(str(self.dir))
        self.assertEqual((wav.name, rdir), ('mix.wav', out))
        self.assertEqual(cli.zoom_target(str(self.dir), stem='bass')[0], out / 'stems' / 'bass.wav')
        with self.assertRaisesRegex(cli.CliError, "no stem 'pad'.*stems there: bass"):
            cli.zoom_target(str(self.dir), stem='pad')
        with self.assertRaisesRegex(cli.CliError, r'--section my part'):
            cli.zoom_target(str(self.dir), section='my part')
        sec = out / 'sections' / 'my_part'
        sec.mkdir(parents=True)
        (sec / 'mix.wav').write_bytes(b'RIFF')
        self.assertEqual(cli.zoom_target(str(self.dir), section='my part')[1], sec)
        self.assertEqual(cli.zoom_target(str(out / 'mix.wav'))[0], (out / 'mix.wav').resolve())
        with self.assertRaisesRegex(cli.CliError, 'no WAV file'):
            cli.zoom_target(str(out / 'nope.wav'))

    def test_render_info_and_arguments(self):
        out = self.dir / 'out' / 'sections' / 'b'
        out.mkdir(parents=True)
        (out / 'report.json').write_text(json.dumps({'render': {'tempo': 110, 'fromBeat': 8.0}}), encoding='utf-8')
        self.assertEqual(cli._render_info(out), {'tempo': 110.0, 'fromBeat': 8.0})
        (self.dir / 'out' / 'song.render.json').write_text(json.dumps({'tempo': 96}), encoding='utf-8')
        self.assertEqual(cli._render_info(self.dir / 'out'), {'tempo': 96.0})
        (out / 'mix.wav').write_bytes(b'RIFF')
        code, _, err = run(['zoom', str(self.dir), '--section', 'b', '--engine', str(self.dir / 'missing.exe')])
        self.assertEqual(code, 1)
        self.assertIn('exactly one of --at', err)
        code, _, err = run(['zoom', str(self.dir), '--section', 'b', '--at', '0:01', '--engine', str(self.dir / 'missing.exe')])
        self.assertEqual(code, 3)
        self.assertIn('engine not found', err)


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


@unittest.skipIf(_engine() is None, 'engine not built (set AGENTSOUND_TEST_ENGINE or build build/agentsound.exe)')
class EngineIntegration(unittest.TestCase):
    @needs_dx7      # the template's keys are a DX7 e-piano
    def test_render_template_section(self):
        out = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_int_'))
        self.addCleanup(shutil.rmtree, out, True)
        code, stdout, err = run(['build', str(cli.REPO / 'songs' / '_template'), '--section', 'verse', '--no-mp3',
                                 '--out', str(out), '--engine', str(_engine())])
        self.assertEqual(code, 0, err)
        self.assertTrue((out / 'sections' / 'verse' / 'mix.wav').is_file())
        self.assertIn('report', stdout)
        self.assertNotIn('drums-key', stdout)  # the muted sidechain ghost is hidden from the summary
        # The image set is listed with what each image shows, and every listed file exists.
        self.assertIn('overview.png is the index', stdout)
        report = json.loads((out / 'sections' / 'verse' / 'report.json').read_text(encoding='utf-8'))
        files = [i['file'] for i in report['images']]
        self.assertEqual(files[:6], ['overview.png', 'loudness.png', 'tracks.png', 'bands.png', 'stereo.png', 'spectrogram.png'])
        self.assertIn('spectrogram_01_verse.png', files)
        for f in files:
            self.assertTrue((out / 'sections' / 'verse' / f).is_file(), f)
        self.assertEqual(report['clicks'], [])  # the template renders click-free

        # Zoom into the section render: by time and by song beat (the render starts at beat 32).
        wav = out / 'sections' / 'verse' / 'mix.wav'
        png = out / 'z.png'
        code, stdout, err = run(['zoom', str(wav), '--at', '0:01.5', '--out', str(png), '--engine', str(_engine())])
        self.assertEqual(code, 0, err)
        self.assertTrue(png.is_file() and png.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n')
        self.assertIn('no clicks detected in view', stdout)
        code, stdout, err = run(['zoom', str(wav), '--beat', '34', '--ms', '20', '--channel', 'L', '--engine', str(_engine())])
        self.assertEqual(code, 0, err)
        self.assertTrue(list((out / 'sections' / 'verse' / 'zooms').glob('zoom_beat34_mix.png')))
        code, stdout, err = run(['zoom', str(wav), '--sec', '9999', '--engine', str(_engine())])
        self.assertEqual(code, 2)
        self.assertIn('outside the file', err)

    @needs_dx7
    def test_analysis_profiles_match_engine(self):
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_profiles_'))
        self.addCleanup(shutil.rmtree, d, True)
        (d / 'song.py').write_text(SONG, encoding='utf-8')
        for prof in cli.ANALYSIS_PROFILES:
            code, out, err = run(['check', str(d), '--engine', str(_engine()), '--profile', prof])
            self.assertEqual(code, 0, prof + err)
            self.assertIn('engine validation passed', out)
        # The engine's own list (from its error for an unknown profile) is the CLI's.
        rj = d / 'out' / 'song.render.json'
        data = json.loads(rj.read_text(encoding='utf-8'))
        data['analysis'] = {'profile': 'bogus'}
        rj.write_text(json.dumps(data), encoding='utf-8')
        import subprocess
        proc = subprocess.run([str(_engine()), 'validate', str(rj)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        listed = proc.stderr.split('(profiles: ')[1].split(')')[0].split(', ')
        self.assertEqual(tuple(listed), cli.ANALYSIS_PROFILES)

    def test_audition_riser_with_profile(self):
        out = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_aud_'))
        self.addCleanup(shutil.rmtree, out, True)
        code, stdout, err = run(['audition', 'synthwave/noise_riser', '--no-mp3', '--out', str(out), '--profile', 'synthwave',
                                 '--engine', str(_engine())])
        self.assertEqual(code, 0, err)
        render = json.loads((out / 'audition.render.json').read_text(encoding='utf-8'))
        self.assertEqual(len(render['tracks'][0]['notes']), 1)
        self.assertIn('instrument.cutoff', [a['target'] for a in render['tracks'][0]['automation']])
        report = json.loads((out / 'report.json').read_text(encoding='utf-8'))
        self.assertEqual(report['reference']['profile'], 'synthwave')
        self.assertIn('profile synthwave', stdout)

    @needs_dx7
    def test_check_runs_engine_validation(self):
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_val_'))
        self.addCleanup(shutil.rmtree, d, True)
        (d / 'song.py').write_text(SONG.replace("inst.dx7('E.PIANO 1')", "inst.va(cutof=300)"), encoding='utf-8')
        code, out, err = run(['check', str(d), '--engine', str(_engine())])
        self.assertEqual(code, 2, out + err)
        self.assertIn("(track 'keys')", err)       # engine JSON path explained with the track id
        self.assertIn('cutof', err)
        (d / 'song.py').write_text(SONG, encoding='utf-8')
        code, out, err = run(['check', str(d), '--engine', str(_engine())])
        self.assertEqual(code, 0, err)
        self.assertIn('engine validation passed', out)


if __name__ == '__main__':
    unittest.main()
