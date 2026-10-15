"""The sung vocal: agentsound.lyrics (G2P, syllables, alignment, the lyricist's checks), agentsound.voicebank (manifest,
consent rule, config / dictionary readers, paths), agentsound.singer (moves, the timeline - consonants before the
beat -, the cache and the compile hook with a mocked WSL backend, the vocal checks), the vocal hero preset and the
credits of a sung take. No WSL, GPU or voicebank download needed: a fake bank folder stands in for the real one."""

import json
import os
import shutil
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from agentsound import Song, heroes, lyrics, singer
from agentsound import voicebank as vb
from agentsound.patterns import Clip

ARPA = ['SP', 'AP'] + list(lyrics.VOWELS) + list(lyrics.CONSONANTS)
CMU_MINI = """\
hold  HH OW1 L D
on  AA1 N
to  T UW1
the  DH AH0
night  N AY1 T
tonight  T AH0 N AY1 T
together  T AH0 G EH1 DH ER0
city  S IH1 T IY0
will  W IH1 L
we  W IY1
were  W ER1
young  Y AH1 NG
lights  L AY1 T S
are  AA1 R
so  S OW1
out  AW1 T
loud  L AW1 D
and  AH0 N D
"""


class _Env(unittest.TestCase):
    """A temp voices folder with a mini CMUdict and a fake 'hanami' bank (dsconfig + phonemes), so nothing real is
    needed; AGENTSOUND_VOICES / AGENTSOUND_CMUDICT point at it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='agentsound_singer_'))
        (self.tmp / '_g2p').mkdir()
        (self.tmp / '_g2p' / 'cmudict.dict').write_text(CMU_MINI, encoding='utf-8')
        bank = self.tmp / 'hanami'
        (bank / 'dsmain').mkdir(parents=True)
        (bank / 'dsmain' / 'phonemes.txt').write_text('<PAD>\n' + '\n'.join(ARPA) + '\n', encoding='utf-8')
        (bank / 'dsconfig.yaml').write_text(
            "phonemes: dsmain/phonemes.txt\nacoustic: dsmain/acoustic.onnx\nhidden_size: 256\nspeakers:\n"
            "- dsmain/embeds/acoustic/Root\n- dsmain/embeds/acoustic/Fragrance\n- dsmain/embeds/acoustic/Nectar\n"
            "augmentation_args:\n  random_pitch_shifting:\n    range:\n    - -20.0\n    - 20.0\n"
            "use_key_shift_embed: true  # a comment\nsample_rate: 44100\n", encoding='utf-8')
        (bank / 'dsdur').mkdir()
        (bank / 'dsdur' / 'dsdict-en.yaml').write_text(
            'symbols:\n- {symbol: SP, type: vowel}\nentries:\n- {grapheme: "hanami", phonemes: [hh, aa, n, aa, m, iy]}\n'
            '- {grapheme: "lotte(1)", phonemes: [l, aa, t]}\n- {grapheme: "korean", phonemes: [K, i, M]}\n',
            encoding='utf-8')
        self.env = mock.patch.dict(os.environ, {'AGENTSOUND_VOICES': str(self.tmp),
                                                'AGENTSOUND_CMUDICT': str(self.tmp / '_g2p' / 'cmudict.dict')})
        self.env.start()
        lyrics._CMU = None
        vb._BANKS.clear()

    def tearDown(self):
        self.env.stop()
        lyrics._CMU = None
        vb._BANKS.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)


class Lyrics(_Env):
    def test_syllables_maximal_onset(self):
        s = lyrics.syllabify(['m', 'aa1', 'n', 's', 't', 'er0'], 'monster')
        self.assertEqual([(x.onset, x.nucleus, x.coda) for x in s], [(('m',), 'aa', ('n',)), (('s', 't'), 'er', ())])
        s = lyrics.syllabify(['eh1', 'k', 's', 't', 'r', 'ah0'], 'extra')
        self.assertEqual([x.onset for x in s], [(), ('s', 't', 'r')])
        self.assertEqual(s[0].coda, ('k',))
        self.assertEqual(len(lyrics.syllabify(['s', 't', 'r', 'eh1', 'ng', 'k', 'th'])), 1)
        s = lyrics.syllabify(['s', 'ih1', 'ng', 'er0'], 'singer')          # 'ng' never starts a syllable
        self.assertEqual(s[0].coda, ('ng',))
        self.assertEqual([x.stress for x in lyrics.syllabify(['t', 'ah0', 'n', 'ay1', 't'])], [0, 1])
        with self.assertRaises(lyrics.LyricsError):
            lyrics.syllabify(['zz', 'ah'])

    def test_g2p_sources(self):
        self.assertEqual(lyrics.g2p('Night'), (['n', 'ay1', 't'], 'cmudict'))
        self.assertEqual(lyrics.g2p("night's")[0][-1], 'z')                 # a contraction of a known stem
        ph, src = lyrics.g2p('hanami', {'hanami': ['hh', 'aa', 'n', 'aa', 'm', 'iy']})
        self.assertEqual(src, 'bank')
        self.assertEqual(ph[1], 'aa1')                                      # the first vowel carries the stress
        ph, src = lyrics.g2p('shine')
        self.assertEqual((src, ph), ('rules', ['sh', 'ay1', 'n']))         # magic e
        self.assertEqual(lyrics.g2p('glimmer')[0].count('m'), 1)           # doubled letters are one sound

    def test_parse(self):
        t = lyrics.parse('Hold - on, to-geth-er _ night{n ay1 t}. "young"!')
        self.assertEqual([x.kind for x in t], ['word', 'melisma', 'word', 'word', 'hold', 'word', 'word'])
        self.assertEqual(t[2].mark, ',')
        self.assertEqual(t[3].pieces, ['to', 'geth', 'er'])
        self.assertEqual(t[5].phonemes, ['n', 'ay1', 't'])
        self.assertEqual((t[6].text, t[6].mark), ('young', '!'))
        with self.assertRaises(lyrics.LyricsError):
            lyrics.parse('   ')

    def test_align(self):
        c = Clip([(i * 0.5, 0.5, 60 + i, 90) for i in range(9)], length=8)
        warn = []
        s = lyrics.align(c, 'Hold - on to the night, to-geth-er', warnings=warn)
        self.assertEqual([x.kind for x in s][:3], ['syllable', 'melisma', 'syllable'])
        self.assertTrue(s[1].word_end and not s[0].word_end)                # the run ends the word 'hold'
        self.assertEqual(s[5].mark, ',')
        self.assertEqual([x.syllable.word for x in s[6:]], ['together'] * 3)
        self.assertEqual(warn, [])
        with self.assertRaises(lyrics.LyricsError) as e:
            lyrics.align(c, 'Hold on to the night')
        self.assertIn('9 notes', str(e.exception))
        warn = []
        s = lyrics.align(c, 'Hold - on to the night, to-gether er', warnings=warn)   # pieces win over the dictionary
        self.assertTrue(warn and 'piece by piece' in warn[0])
        self.assertEqual(s[6].syllable.nucleus, 'uw')
        warn = []
        lyrics.align(Clip([(0, 1, 60, 90)]), 'zork', warnings=warn)
        self.assertTrue(warn and 'zork' in warn[0])

    def test_german_by_hand(self):
        # the German symbols (o1 / u1 / l1 end in a digit: not a stress), 'ee = the stressed vowel, -er off-glide
        s = lyrics.syllabify("l1 'a n d uh ng s sh t ee k".split(), 'landungssteg')
        self.assertEqual([(x.onset, x.nucleus, x.coda) for x in s],
                         [(('l1',), 'a', ('n',)), (('d',), 'uh', ('ng', 's')), (('sh', 't'), 'ee', ('k',))])
        self.assertEqual([x.stress for x in s], [1, 0, 0])
        self.assertEqual(lyrics.syllabify("ts uh rh 'yy k".split())[1].stress, 1)
        s = lyrics.syllabify(['v', 'ee', 'ex'], 'wer')                         # one syllable: wer, der, mir
        self.assertEqual((len(s), s[0].nucleus, s[0].coda), (1, 'ee', ('ex',)))
        self.assertEqual(len(lyrics.syllabify(['v', 'a', 's', 'ex'])), 2)    # Was-ser: a vocalic -er syllable
        self.assertEqual(lyrics.syllabify(['m', 'o1', 'n', 'd'])[0].nucleus, 'o1')
        self.assertEqual(lyrics.vowel_class('ax'), 'closed')
        self.assertEqual(lyrics.vowel_class('o1'), 'open')
        t = lyrics.spell('*Die Fäh-re* geht, - (( wer ))', {'die': 'd iy', 'Fähre': "f 'eh rh ax", 'geht': 'g ee t',
                                                             'wer': 'v ee ex'})
        self.assertEqual(t, "*Die{d iy} Fähre{f 'eh rh ax}* geht{g ee t}, - (( wer{v ee ex} ))")
        toks = lyrics.parse(t)
        self.assertEqual([(x.text, x.emph) for x in toks if x.kind == 'word'],
                         [('Die', 'emph'), ('Fähre', 'emph'), ('geht', ''), ('wer', 'intimate')])
        self.assertEqual(toks[2].mark, ',')
        c = Clip([(i, 1, 60 + i, 90) for i in range(6)], length=6)
        sung = lyrics.align(c, t)
        self.assertEqual([(x.kind, x.syllable.word) for x in sung],
                         [('syllable', 'Die'), ('syllable', 'Fähre'), ('syllable', 'Fähre'), ('syllable', 'geht'),
                          ('melisma', 'geht'), ('syllable', 'wer')])
        with self.assertRaises(lyrics.LyricsError) as e:
            lyrics.spell('Die Nacht', {'die': 'd iy'})
        self.assertIn("'nacht'", str(e.exception))

    def test_lyricist_checks(self):
        c = Clip([(0, 1, 60, 90), (1.5, 0.5, 62, 90), (2, 2, 64, 90)], length=4)
        w = lyrics.check(c, 'to-night will')
        self.assertTrue(any(x.startswith('stress') and 'tonight' in x for x in w))
        self.assertTrue(any(x.startswith('vowel') and "'ih'" in x for x in w))
        c2 = Clip([(0, 0.5, 60, 90), (0.5, 0.5, 62, 90), (1, 2, 64, 90)], length=4)
        self.assertFalse([x for x in lyrics.check(c2, 'we were young') if x.startswith('stress')])


class Voicebanks(_Env):
    def test_manifest_and_consent(self):
        ids = [v['id'] for v in vb.manifest()]
        self.assertIn('hanami', ids)
        self.assertIn('tiger', ids)
        for v in vb.manifest():
            self.assertIn(v['consent'], vb.CONSENT)
            for k in ('url', 'license', 'attribution', 'range', 'modes'):
                self.assertTrue(v.get(k), f"{v['id']}: {k}")
        self.assertTrue(vb.get('tiger').nc)                                  # non-commercial voice
        with self.assertRaises(vb.VoicebankError) as e:
            vb.get('some_real_singer')
        self.assertIn('no cloning', str(e.exception))
        bad = self.tmp / 'm.json'
        bad.write_text(json.dumps({'voices': [{'id': 'x', 'consent': 'scraped'}]}), encoding='utf-8')
        with mock.patch.object(vb, 'MANIFEST', bad):
            with self.assertRaises(vb.VoicebankError):
                vb.manifest()

    def test_prompt_consent(self):
        f = self.tmp / 'p.wav'
        f.write_bytes(b'RIFF')
        self.assertEqual(vb.check_prompt(f, 'licensed-render', 'hanami')['kind'], 'licensed-render')
        vb.check_prompt(f, 'own')
        for kind in ('celebrity', 'reference', ''):
            with self.assertRaises(vb.VoicebankError):
                vb.check_prompt(f, kind)
        with self.assertRaises(vb.VoicebankError):
            vb.check_prompt(f, 'licensed-render', 'not_a_bank')

    def test_bank_readers(self):
        b = vb.get('hanami')
        self.assertTrue(b.installed())
        self.assertEqual(b.speakers, ['Root', 'Fragrance', 'Nectar'])
        self.assertEqual(b.key_shift_range, 20.0)
        self.assertIn('ay', b.phonemes)
        self.assertEqual(b.mode('soft'), 'Nectar')
        self.assertEqual(b.mode('Fragrance'), 'Fragrance')
        with self.assertRaises(vb.VoicebankError):
            b.mode('falsetto')
        self.assertEqual(b.dictionary(), {'hanami': ['hh', 'aa', 'n', 'aa', 'm', 'iy']})   # English ARPAbet only
        self.assertEqual(vb.wsl_path(r'D:\Repos\x y\a.wav'), '/mnt/d/Repos/x y/a.wav')
        self.assertEqual(vb.wsl_path('/home/u/a'), '/home/u/a')
        self.assertFalse(vb.get('tiger').installed())
        with self.assertRaises(vb.VoicebankError) as e:
            vb.get('tiger').require()
        self.assertIn('not installed', str(e.exception))

    def test_runner_tokenises_per_sub_model(self):
        # TIGER: the pitch model's table lacks io / iz / rs -> its ids differ from the acoustic / duration ones
        import importlib
        with mock.patch.dict('sys.modules', {'onnxruntime': mock.MagicMock(), 'yaml': mock.MagicMock()}):
            dr = importlib.import_module('agentsound.voicebank_runner.ds_runner')
        full = ['<PAD>', 'AP', 'SP', 'a', 'ih', 'io', 'iy', 'iz', 'r', 'rs', 't', 'z', 'zh']
        root = self.tmp / 'bank'
        for sub, names in (('dsacoustic', full), ('dsdur', full),
                           ('dspitch', [n for n in full if n not in ('io', 'iz', 'rs')])):
            (root / sub).mkdir(parents=True)
            (root / sub / 'phonemes.txt').write_text('\n'.join(names) + '\n', encoding='utf-8')
            (root / sub / 'dsconfig.yaml').write_text('', encoding='utf-8')
        cfgs = {'dsconfig.yaml': {'phonemes': 'dsacoustic/phonemes.txt'},
                'dsdur/dsconfig.yaml': {'phonemes': 'phonemes.txt'},
                'dspitch/dsconfig.yaml': {'phonemes': 'phonemes.txt'}}
        r = root.as_posix()
        with mock.patch.object(dr, '_yaml', lambda p: dict(cfgs[p[len(r) + 1:]])):
            bank = dr.Bank(r, provider='cpu')
        phs = ['a', 'io', 'z', 'zh', 'rs']
        self.assertEqual(bank.tokens(phs).tolist(), [[3, 5, 11, 12, 9]])                         # acoustic
        self.assertEqual(bank.tokens(phs, bank.dur_cfg['_phonemes']).tolist(), [[3, 5, 11, 12, 9]])
        # pitch: z / zh in range of its table (the crash), io / rs fed as their stand-ins iy / t
        self.assertEqual(bank.tokens(phs, bank.pitch_cfg['_phonemes']).tolist(), [[3, 5, 8, 9, 7]])
        with self.assertRaises(ValueError):
            bank.tokens(['xx'])


def _song():
    s = Song('t', tempo=100, key='C major')
    s.section('a', bars=4)
    s.section('b', bars=4)
    return s


LINE = Clip([(0, 1, 'E4', 90), (1, 0.5, 'G4', 90), (1.5, 0.5, 'A4', 90), (2, 3, 'C5', 100),
             (8, 1, 'C5', 90), (9, 0.5, 'A4', 90), (9.5, 0.5, 'G4', 90), (10, 3, 'E4', 80)], length=16)
TEXT = 'Hold on to-night, we were so young'


class SingerPlan(_Env):
    def test_moves_and_robot(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE, TEXT, at=s['a'], seed=1)
        self.assertEqual(len(vo.phrases), 2)
        names = {n for _, n, _ in vo.moves}
        self.assertIn('vibrato', names)                                     # the long notes
        self.assertIn('breath', names)
        self.assertEqual(sum(1 for _, n, _ in vo.moves if n == 'breath'), 2)
        held = [i for i, n in enumerate(vo.notes) if n.dur >= 3]
        self.assertTrue(all('vibrato' in vo.plan[i] for i in held))         # long held notes always sing vibrato
        self.assertEqual(vo.track.id, 'vocal')
        robot = singer.sing(s, LINE, TEXT, at=s['a'], moves=False, track_id='robot')
        self.assertEqual(robot.moves, [])
        self.assertEqual(singer.sing(s, LINE, TEXT, at=s['a'], seed=1, track_id='again').moves, vo.moves)
        with self.assertRaises(singer.SingerError):
            singer.sing(s, LINE, TEXT, style='opera')
        with self.assertRaises(singer.SingerError):
            singer.sing(s, LINE, TEXT, vib_depth=3)                          # unknown STYLES key
        with self.assertRaises(lyrics.LyricsError):
            singer.sing(s, LINE, 'too few words')

    def test_slow_ballad_vibrato_and_held_notes(self):
        # the ballad style at <= 80 BPM sings the narrower, later vibrato (STYLES['ballad']['slow']); a call's own
        # value wins; at 100 BPM the style is as it was
        slow = Song('t', tempo=62, key='C major')
        slow.section('a', bars=8)
        slow._singer_dir = self.tmp
        vo = singer.sing(slow, LINE, TEXT, at=0, style='ballad')
        self.assertEqual((vo.params['vib_ct'], vo.params['vib_min_s'], vo.params['model_vib']), (13.0, 1.1, 0.35))
        self.assertNotIn('slow', vo.params)
        self.assertEqual(singer.sing(slow, LINE, TEXT, at=0, style='ballad', vib_ct=20.0,
                                     track_id='v2').params['vib_ct'], 20.0)
        s = _song()
        s._singer_dir = self.tmp
        self.assertEqual(singer.sing(s, LINE, TEXT, at=0, style='ballad').params['vib_ct'],
                         singer.STYLES['ballad']['vib_ct'])
        # held_notes: the 3-beat C5 through a fermata of 8 extra beats (~6.6 s at 62 BPM): info; 16 more: warn
        self.assertEqual(singer.held_notes(slow), [])
        slow.fermata(3, hold=8)
        self.assertEqual([f['code'] for f in singer.held_notes(slow) if f['node'] == 'vocal'], ['note_fermata'])
        long = Song('u', tempo=62, key='C major')
        long.section('a', bars=8)
        long._singer_dir = self.tmp
        singer.sing(long, LINE, TEXT, at=0, style='ballad')
        long.fermata(3, hold=16)
        f = singer.held_notes(long)
        self.assertEqual([x['code'] for x in f], ['held_note'])
        self.assertIn('through a fermata', f[0]['message'])

    def test_spice_budget_song_wide(self):
        s = _song()
        s._singer_dir = self.tmp
        mem = singer.Memory()
        a = singer.sing(s, LINE, TEXT, at=0, memory=mem, fall=1.0, doit=0.0, spice_every=8)
        b = singer.sing(s, LINE, TEXT, at=16, memory=mem, fall=1.0, doit=0.0, spice_every=8, track_id='v2')
        falls = [t for vo in (a, b) for t, n, _ in vo.moves if n == 'fall']
        self.assertTrue(falls)
        self.assertTrue(all(abs(x - y) >= 32 - 1e-6 for x in falls for y in falls if x != y))
        self.assertTrue(a.budget['dropped'] or b.budget['dropped'])

    def test_notation_line(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, 'E4/4^vib(40) G4/8 A4 C5/2.^peak', 'Hold on to night', at=0)
        self.assertEqual(len(vo.notes), 4)
        self.assertTrue(vo.plan[0]['vibrato'].get('hand'))
        self.assertTrue(vo.notes[3].hook)

    def test_range_warning(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE.transpose(-24), TEXT, at=0)
        self.assertTrue(any('outside' in w for w in vo.warnings))


def _fake_run(calls):
    """A stand-in for voicebank.run: duration -> 4 frames per phoneme; sing -> a short WAV at the job's path."""
    def run(bank, jobs, *, work, log=print, provider=None, timeout=3600):
        calls.append([j['op'] for j in jobs])
        out = []
        for j in jobs:
            if j['op'] == 'duration':
                out.append({'ok': True, 'ph_dur': [4.0] * len(j['phonemes'])})
            elif j['op'] == 'pitch':
                out.append({'ok': True, 'pitch': [60.0] * sum(j['ph_dur'])})
            else:
                p = j['out']
                if p.startswith('/mnt/') and os.name == 'nt':
                    p = p[5].upper() + ':' + p[6:]
                n = sum(j['durations']) * 512
                with wave.open(p, 'wb') as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(44100)
                    w.writeframes(b'\x00\x00' * n)
                self_check = (len(j['f0']) == sum(j['durations']) and len(j['gain_db']) == sum(j['durations'])
                              and all(len(v) == sum(j['durations']) for v in j['speaker'].values()
                                      if isinstance(v, list)))
                out.append({'ok': self_check, 'error': 'curve lengths', 'samples': n})
        bad = [x for x in out if not x['ok']]
        if bad:
            raise vb.VoicebankError('fake: curve lengths do not match the frames')
        return out
    return run


class SingerRender(_Env):
    def test_timeline_consonants_before_the_beat(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE, TEXT, at=0, seed=2)
        spec = singer._phrase_spec(vo, vo.phrases[0])
        job = singer._dur_job(spec)
        self.assertEqual(sum(job['word_div']), len(job['phonemes']))
        self.assertEqual(job['phonemes'][:2], ['SP', 'hh'])                 # word 0: SP + the first onset
        pred = [6.0] * len(job['phonemes'])
        tl = singer._timeline(spec, singer._cons_lengths(job, pred, spec), vb.get('hanami'))
        toks = tl['tokens']
        self.assertEqual(toks[0][0], 'SP')
        self.assertIn('AP', [t[0] for t in toks])                          # the breath before the phrase
        i_ow = next(i for i, t in enumerate(toks) if t[0] == 'ow')
        self.assertEqual(toks[i_ow - 1][0], 'hh')
        late = vo.plan[0]['late_ms'] / 1000.0
        self.assertAlmostEqual(toks[i_ow][1], late, places=3)              # the vowel lands on the beat (+ feel)
        self.assertLess(toks[i_ow - 1][1], 0.0)                             # the consonant before it
        self.assertEqual(sum(tl['durations']), tl['frames'])
        self.assertEqual(len(tl['midi']), tl['frames'])
        self.assertTrue(any(len(v) == tl['frames'] for v in tl['mix'].values() if isinstance(v, list)))
        # robotic: the consonant starts ON the beat, the vowel follows
        rb = singer.sing(s, LINE, TEXT, at=0, moves=False, track_id='robot')
        spec = singer._phrase_spec(rb, rb.phrases[0])
        job = singer._dur_job(spec)
        tl = singer._timeline(spec, singer._cons_lengths(job, [6.0] * len(job['phonemes']), spec), vb.get('hanami'))
        hh = next(t for t in tl['tokens'] if t[0] == 'hh')
        self.assertAlmostEqual(hh[1], 0.0, places=6)
        self.assertNotIn('AP', [t[0] for t in tl['tokens']])
        self.assertEqual(len(set(tl['gain'])), 1)                           # one level
        flat = [m for m in tl['midi']]
        self.assertTrue(all(abs(m - round(m)) < 1e-9 for m in flat))        # pitch steps, no vibrato / drift

    def test_compile_hook_cache_and_zones(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE, TEXT, at=s['a'], seed=4)
        heroes.hero(vo.track, family='vocal')
        calls = []
        with mock.patch.object(vb, 'run', _fake_run(calls)), mock.patch.object(vb, 'runner_ok', lambda: (True, '')):
            r = s.compile()
            self.assertEqual(calls, [['duration', 'duration'], ['pitch', 'pitch'], ['sing', 'sing']])
            s.compile()
            self.assertEqual(len(calls), 3)                                  # cached: no second synthesis
        t = next(x for x in r['tracks'] if x['id'] == 'vocal')
        self.assertEqual(len(t['notes']), 2)
        zones = t['instrument']['params']['samples']
        self.assertEqual(len(zones), 2)
        self.assertTrue(all(Path(z['file']).is_file() for z in zones))
        self.assertTrue((self.tmp / 'samples' / 'vocals' / 'hanami' / 'SOURCE.json').is_file())
        first = min(n['start'] if isinstance(n, dict) else n[0] for n in t['notes'])
        self.assertAlmostEqual(first, 0.0)               # the first take would start before beat 0: it starts at 0 ...
        self.assertGreater(zones[0].get('offset', 0), 0)  # ... skipping the part of the file before the song
        # the vocal's echo is deliberate: one throw on the section's last phrase end (no constant echo)
        self.assertTrue(any('throws: 1 section ends' in x for x in vo.track.hero.compile_log))
        self.assertEqual(heroes.infer(vo.track).name, 'vocal')
        fx_types = [f['type'] for f in t['fx']]
        self.assertIn('deesser', fx_types)

    def test_doubles_and_harmony_are_new_takes(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE, TEXT, at=0, seed=4)
        d = singer.double(vo, pan=-0.5)
        h = singer.harmony(vo, steps=2, key='C major')
        self.assertNotEqual(d.take, vo.take)
        self.assertGreater(d.offset_ms, 0)
        self.assertEqual(d.track.pan, -0.5)
        self.assertEqual([n.pitch for n in h.notes][:2], [67, 71])            # E4 G4 -> G4 B4 (a third up)
        self.assertNotEqual(singer._key(singer._phrase_spec(d, d.phrases[0])),
                            singer._key(singer._phrase_spec(vo, vo.phrases[0])))
        # doubles onto tracks that already exist (catch-fire: L and R per line): never the same take twice
        dl = singer.double(vo, pan=-0.8, track_id='dl')
        dr = singer.double(vo, pan=0.8, track_id='dr')
        vo2 = singer.sing(s, LINE, TEXT, at=8, seed=4)
        dl2 = singer.double(vo2, pan=-0.8, track_id='dl')
        dr2 = singer.double(vo2, pan=0.8, track_id='dr')
        self.assertEqual(len({vo.take, d.take, dl.take, dr.take}), 4)
        self.assertNotEqual(dl2.take, dr2.take)

    def test_calm_lay_back_follows_the_consonants(self):
        # jazz / ballad: the vowel lands half its onset consonants + pcentre_ms behind the beat (P-centre ~ on it)
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE, TEXT, at=0, seed=2, style='jazz')
        spec = singer._phrase_spec(vo, vo.phrases[0])
        job = singer._dur_job(spec)
        for pred in (4.0, 9.0):          # short and long consonants (frames per phoneme)
            cons = singer._cons_lengths(job, [pred] * len(job['phonemes']), spec)
            tl = singer._timeline(spec, cons, vb.get('hanami'))
            toks = tl['tokens']
            i = next(k for k, t in enumerate(toks) if t[0] == 'ow')
            onset = toks[i][1] - toks[i - 1][1]                       # 'hh' before the vowel
            S = vo.params
            want = (vo.plan[0]['late_ms'] - S['late_ms'] + S['pcentre_ms']) / 1000.0 + 0.5 * onset
            self.assertAlmostEqual(toks[i][1], want, delta=0.004)


def _timeline(vo, k=0, pred=6.0):
    """The timeline of phrase k with a flat duration-model prediction (frames per phoneme)."""
    spec = singer._phrase_spec(vo, vo.phrases[k])
    job = singer._dur_job(spec)
    return spec, singer._timeline(spec, singer._cons_lengths(job, [pred] * len(job['phonemes']), spec),
                                  vb.get('hanami'))


# 'out' runs over two notes ('-' melisma) to a phrase end, 'loud' is held ('_') to a phrase end; a rest between
CODA_LINE = Clip([(0, 1, 'E4', 90), (1, 1, 'G4', 90), (2, 1, 'E4', 90),
                  (5, 1, 'E4', 90), (6, 1, 'G4', 90), (7, 1, 'G4', 90)], length=12)
CODA_TEXT = 'so out -, so loud _.'


class Diction(_Env):
    """Word-final consonants: at the end of the word's last note (after a run / hold), never too short, a final stop
    released, not under the phrase-end release / taper, not covered by the next breath; the diction check."""

    def _sing(self, s, **kw):
        s._singer_dir = self.tmp
        return singer.sing(s, CODA_LINE, CODA_TEXT, at=0, seed=5, release=1.0, taper=1.0, fall=1.0, spice_every=1,
                           **kw)

    def test_align_codas_after_melisma_and_hold(self):
        sung = lyrics.align(CODA_LINE, CODA_TEXT)
        self.assertEqual([x.kind for x in sung], ['syllable', 'syllable', 'melisma', 'syllable', 'syllable', 'hold'])
        self.assertEqual([x.word_end for x in sung], [True, False, True, True, False, True])
        self.assertEqual(sung[2].syllable.coda, ('t',))                     # the run carries the coda of 'out'
        self.assertEqual(sung[5].syllable.coda, ('d',))
        self.assertEqual((sung[2].mark, sung[5].mark), (',', '.'))

    def test_final_stop_at_the_end_of_the_run_released(self):
        s = _song()
        vo = self._sing(s)
        self.assertEqual(len(vo.phrases), 2)
        self.assertIn('diction', {n for _, n, _ in vo.moves})
        for k, (word, stop, last) in enumerate((('out', 't', 2), ('loud', 'd', 5))):
            spec, tl = _timeline(vo, k)
            n = vo.notes[last]
            end = s.seconds(n.start + n.dur) - s.seconds(vo.notes[vo.phrases[k][0]].start)
            toks = tl['tokens']
            i = max(j for j, t in enumerate(toks) if t[0] == stop)
            self.assertAlmostEqual(toks[i][2], end, places=3)                # the coda closes the LAST note
            self.assertEqual(toks[i - 1][0], 'SP')                             # a silent closure before the stop
            self.assertEqual(toks[i + 1][0], 'ah')                             # ... and a released burst after it
            self.assertGreater(toks[i + 1][1], end - 1e-6)                     # (in the rest after the note)
            self.assertEqual(toks[i - 2][0], 'aw')
            c = next(c for c in tl['diction'] if c['ph'] == stop)
            self.assertEqual((c['word'], c['cls'], c['at']), (word, 'stop', 'rest'))
            self.assertGreaterEqual(c['ms'], singer.DICTION['stop'][3] * 1000)
            self.assertLessEqual(toks[i][2] - toks[i][1], singer.DICTION['stop'][2] + 0.012)   # no long closure
            # the phrase-end release / taper act on the vowel: the coda keeps the vowel's level + its lift
            self.assertGreaterEqual(c['level_db'], singer.DICTION['stop'][4] - (0.5 if stop == 't' else 3.0))
            t0, nf = tl['offset_s'], tl['frames']
            fr = lambda t: max(0, min(nf - 1, int((t - t0) / singer.FR)))
            vowel_end = tl['gain'][fr(toks[i - 2][2]) - 1]
            coda = tl['gain'][fr((toks[i][1] + toks[i][2]) / 2)]
            self.assertLess(vowel_end, coda - 4.0)                             # the release ended on the vowel
            # the fall ends on the vowel too: the pitch at the vowel end is already down
            if 'fall' in vo.plan[last]:
                self.assertLess(tl['midi'][fr(toks[i - 2][2]) - 1], vo.notes[last].pitch - 0.5)

    def test_the_next_breath_never_covers_the_coda(self):
        s = _song()
        s._singer_dir = self.tmp
        for rest in (1.0, 0.25):                                              # 0.6 s, then 0.15 s (split_s=0.1)
            line = Clip([(0, 1, 'E4', 90), (1, 1, 'G4', 90), (2 + rest, 1, 'E4', 90), (3 + rest, 1, 'G4', 90)],
                        length=8)
            vo = singer.sing(s, line, 'so out, so out', at=0, seed=2, split_s=0.1, track_id=f'v{int(rest * 100)}')
            self.assertEqual(len(vo.phrases), 2)
            _, a = _timeline(vo, 0)
            _, b = _timeline(vo, 1)
            i = next(j for j, t in enumerate(a['tokens']) if t[0] == 't')
            coda_end = max(t[2] for t in a['tokens'][i:i + 2] if t[0] != 'SP')          # the stop / its release
            self.assertAlmostEqual(a['tokens'][i][2], s.seconds(2.0), places=3)          # the note end
            nxt0 = s.seconds(2 + rest)                                                     # phrase 2, song time
            first = next(t for t in b['tokens'] if t[0] not in ('SP',))                   # its breath / onset
            self.assertGreaterEqual(nxt0 + first[1], coda_end - 1e-6)
            self.assertLessEqual(coda_end - s.seconds(2.0), 0.25 * s.seconds(rest) + 1e-6)  # the release fits

    def test_legato_codas_keep_a_minimum(self):
        s = _song()
        s._singer_dir = self.tmp
        line = Clip([(0, 0.5, 'E4', 90), (0.5, 0.5, 'G4', 90), (1, 2, 'E4', 90)], length=4)
        vo = singer.sing(s, line, 'and so on', at=0, seed=2)
        _, tl = _timeline(vo, pred=30.0)                                      # long predictions: squeezed
        n, d = [c for c in tl['diction'] if c['word'] == 'and']
        self.assertEqual((n['ph'], d['ph'], d['at']), ('n', 'd', 'legato'))
        self.assertGreaterEqual(d['ms'], singer.DICTION['stop'][1] * 1000 - 12)
        self.assertGreaterEqual(n['ms'], singer.DICTION['nasal'][1] * 1000 - 12)
        _, tl = _timeline(vo, pred=0.4)                                       # tiny predictions: raised
        d = next(c for c in tl['diction'] if c['ph'] == 'd')
        self.assertGreaterEqual(d['ms'], singer.DICTION['stop'][1] * 1000 - 12)
        ph = [t[0] for t in tl['tokens']]
        i = ph.index('d')
        self.assertEqual(ph[i + 1], 's')                                      # no closure / release in legato

    def test_robot_has_minimums_but_no_moves(self):
        s = _song()
        vo = self._sing(s, moves=False, track_id='robot')
        spec, tl = _timeline(vo, 0, pred=0.4)
        self.assertEqual(len(set(tl['gain'])), 1)                            # one level, no lift
        self.assertNotIn('ah', [t[0] for t in tl['tokens']])                 # no release vowel
        t = next(c for c in tl['diction'] if c['ph'] == 't')
        self.assertGreaterEqual(t['ms'], singer.DICTION['stop'][3] * 1000)

    def test_diction_check(self):
        s = _song()
        s._singer_dir = self.tmp
        line = Clip([(0, 0.25, 'E4', 90), (0.25, 0.25, 'G4', 90), (0.5, 2, 'E4', 90)], length=4)
        vo = singer.sing(s, line, 'and so on', at=0, seed=2)                  # 'and' on a 0.15 s note: too short
        calls = []
        with mock.patch.object(vb, 'run', _fake_run(calls)), mock.patch.object(vb, 'runner_ok', lambda: (True, '')):
            s.compile()
        fs = singer.diction(s)
        self.assertTrue(any(f['code'] == 'coda_short' and "'and'" in f['message'] for f in fs))
        self.assertTrue(any(f['code'] == 'diction' for f in fs))
        self.assertEqual(singer.diction(vo), fs)
        self.assertTrue(any('coda_short' not in x and 'lasts' in x for x in
                            singer.report_lines(s, self.tmp / 'missing.json')))
        # a coda swallowed by a release (an older take / a hand-made gesture): buried
        p = Path(vo.rendered[0]['path']).with_suffix('.json')
        meta = json.loads(p.read_text(encoding='utf-8'))
        meta['timeline']['diction'][0].update(level_db=-7.0, ms=80.0)
        p.write_text(json.dumps(meta), encoding='utf-8')
        self.assertTrue(any(f['code'] == 'coda_buried' for f in singer.diction(vo)))


class SingerMicPull(_Env):
    """mic_pull: the singer slowly pulls back from the mic on long held notes (automation after the compressor)."""

    def _compiled(self, s):
        calls = []
        with mock.patch.object(vb, 'run', _fake_run(calls)), mock.patch.object(vb, 'runner_ok', lambda: (True, '')):
            return s.compile()

    def test_plan_long_notes_only_and_by_style(self):
        s = _song()
        s._singer_dir = self.tmp
        bal = singer.sing(s, LINE, TEXT, at=0, seed=4, style='ballad')
        # only the two held phrase ends (3 beats at 100 bpm = 1.8 s): 'night' and 'young', never the short notes
        self.assertEqual(sorted(bal.mic), [3, 7])
        self.assertTrue(all(p['role'] == 'end' for p in bal.mic.values()))
        self.assertTrue(all(-6.0 <= p['db'] <= -4.0 for p in bal.mic.values()))
        self.assertEqual(sum(1 for _, n, _ in bal.moves if n == 'mic_pull'), 2)
        jaz = singer.sing(s, LINE, TEXT, at=0, seed=4, style='jazz', track_id='j')
        self.assertEqual(sorted(jaz.mic), [3, 7])
        self.assertLess(sum(p['db'] for p in bal.mic.values()), sum(p['db'] for p in jaz.mic.values()))  # deeper
        # pop / rock: off unless asked for; a number is the depth in dB
        self.assertEqual(singer.sing(s, LINE, TEXT, at=0, seed=4, track_id='p').mic, {})
        self.assertEqual(singer.sing(s, LINE, TEXT, at=0, seed=4, style='rock', track_id='r').mic, {})
        pop = singer.sing(s, LINE, TEXT, at=0, seed=4, track_id='p2', mic_pull=True)
        self.assertTrue(pop.mic)
        deep = singer.sing(s, LINE, TEXT, at=0, seed=4, track_id='p3', mic_pull=7)
        self.assertTrue(all(-8.1 <= p['db'] <= -5.9 for p in deep.mic.values()))
        self.assertEqual(singer.sing(s, LINE, TEXT, at=0, style='jazz', track_id='off', mic_pull=False).mic, {})
        self.assertEqual(singer.sing(s, LINE, TEXT, at=0, style='jazz', track_id='rb', moves=False).mic, {})
        with self.assertRaises(singer.SingerError):
            singer.sing(s, LINE, TEXT, track_id='bad', mic_pull={'depth': 3})
        # the takes do not change: the pull is not part of what is sung (no new cache keys)
        plain = singer.sing(s, LINE, TEXT, at=0, seed=4, style='ballad', track_id='plain', mic_pull=False)
        self.assertEqual([singer._key(singer._phrase_spec(bal, ph)) for ph in bal.phrases],
                         [singer._key(singer._phrase_spec(plain, ph)) for ph in plain.phrases])

    def test_budget_ends_first(self):
        s = Song('t', tempo=60, key='C major')
        s.section('a', bars=8)
        s._singer_dir = self.tmp
        line = Clip([(0, 2, 'E4', 90), (2, 2, 'G4', 90), (4, 2, 'A4', 90), (6, 3, 'C5', 90)], length=12)
        vo = singer.sing(s, line, 'we were so young', at=0, seed=1, style='ballad', mic_pull={'other': 1.0})
        beats = sorted(vo.notes[p['at']].start for p in vo.mic.values())
        self.assertTrue(all(b - a >= 4 - 1e-6 for a, b in zip(beats, beats[1:])))     # one per bar at most
        self.assertIn(3, vo.mic)                                                        # the phrase end always
        self.assertEqual(vo.mic[3]['role'], 'end')
        self.assertLess(len(vo.mic), 4)                                                 # not every long note
        free = singer.sing(s, line, 'we were so young', at=0, seed=1, style='ballad', track_id='v2',
                           mic_pull={'other': 1.0, 'every': 0})
        self.assertEqual(len(free.mic), 4)
        self.assertLess(free.mic[3]['db'], free.mic[0]['db'])                           # the end the deepest

    def test_lanes_on_long_notes_codas_kept(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE, TEXT, at=0, seed=4, style='ballad')
        heroes.hero(vo.track, family='vocal')
        r = self._compiled(s)
        r2 = self._compiled(s)                                       # idempotent: a second compile writes the same
        t = next(x for x in r2['tracks'] if x['id'] == 'vocal')
        self.assertEqual(t['automation'], next(x for x in r['tracks'] if x['id'] == 'vocal')['automation'])
        names = [f.name for f in vo.track.fx]
        air, mic = names.index('air'), names.index('mic')
        comp = next(i for i, f in enumerate(vo.track.fx) if f.type == 'compressor')
        self.assertLess(comp, air)                                   # the level after the compressor
        self.assertLess(mic, comp)                                   # the proximity where the microphone is
        auto = {a['target']: a['points'] for a in t['automation']}
        lvl = auto[f'fx.{air}.gain']
        self.assertIn(f'fx.{mic}.peak1.gain', auto)
        self.assertNotIn(f'fx.{mic}.output', auto)
        self.assertTrue(any(k.startswith('send.') for k in auto))   # a touch more room
        self.assertEqual(len(vo.mic_pulls), 2)
        for p in vo.mic_pulls:
            inside = [v for b, v, *_ in lvl if p['beat'] - 1e-6 <= b <= p['end_beat'] + 1e-6]
            self.assertAlmostEqual(min(inside), p['db'], delta=0.3)  # down by the pull at the vowel's end ...
            self.assertAlmostEqual(inside[0], 0.0, delta=0.05)       # ... from the bloomed onset at full level
            mid = (p['beat'] + p['end_beat']) / 2
            vm = min((abs(b - mid), v) for b, v, *_ in lvl)[1]
            self.assertGreater(vm, p['db'] / 2)                      # shaped: less than half way at half time
            self.assertIsNotNone(p['coda'])
            self.assertGreater(p['coda_vs_vowel_db'], -3.0)          # the consonant keeps its level
        # only on the long notes: nothing moves outside the pulls
        spans = [(p['beat'], p['end_beat'] + 1.5) for p in vo.mic_pulls]
        self.assertTrue(all(abs(v) < 1e-9 or any(a - 1e-6 <= b <= e for a, e in spans) for b, v, *_ in lvl))
        self.assertFalse([f for f in singer.diction(s) if f['code'] == 'coda_buried'])
        self.assertTrue(any('mic pull' in x for x in singer.report_lines(s, self.tmp / 'missing.json')))
        self.assertIn('mic pulls 2', ' '.join(singer.log_lines(s)))

    def test_doubles_inherit(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE, TEXT, at=0, seed=4, style='pop', mic_pull=True)
        self.assertTrue(singer.double(vo).mic)
        vo2 = singer.sing(s, LINE, TEXT, at=0, seed=4, style='jazz', mic_pull=False, track_id='v2')
        self.assertEqual(singer.harmony(vo2).mic, {})
        # a harmony pulls back with the lead: the same notes, the same depth
        vo3 = singer.sing(s, LINE, TEXT, at=0, seed=4, style='ballad', track_id='v3')
        h = singer.harmony(vo3, steps=-2, key='C major', track_id='v3_harm')
        self.assertTrue(vo3.mic)
        self.assertEqual(h.mic, vo3.mic)


# two phrases of the same melody: a held peak (C5, 1.2 s at 100 bpm) inside, a held phrase end (G4)
XLINE = Clip([(0, 1, 'E4', 80), (1, 0.5, 'G4', 80), (1.5, 0.5, 'A4', 80), (2, 2, 'C5', 96), (4, 0.5, 'B4', 84),
              (4.5, 0.5, 'A4', 80), (5, 2, 'G4', 76)], length=8)
XTEXT = 'Hold on to night, we were young.'


def _xsong(bars=8):
    s = Song('Night Young', tempo=100, key='C major')
    s.section('a', bars=bars)
    return s


class SingerExpression(_Env):
    """back_phrase, ornament (on repeats), messa_di_voce, emphasis - the four expression techniques."""

    def _compiled(self, s):
        calls = []
        with mock.patch.object(vb, 'run', _fake_run(calls)), mock.patch.object(vb, 'runner_ok', lambda: (True, '')):
            return s.compile()

    def test_back_phrase_lays_back_and_lands(self):
        s = _xsong()
        s._singer_dir = self.tmp
        vo = singer.sing(s, XLINE, XTEXT, at=0, seed=3, style='jazz', back_phrase={'chance': 1.0}, ornament=False,
                         messa_di_voce=False)
        bp = vo.expression['back_phrase']
        self.assertEqual(len(bp), 1)
        st = [n.start for n in vo.notes]
        d = st[0] - 0.0
        self.assertTrue(0.12 - 1e-6 <= d <= 0.25 + 1e-6)                         # late by 1/8 .. 1/4 beat
        self.assertAlmostEqual(st[4], 4.0)                                        # caught up on the bar line
        self.assertEqual(st[5:], [4.5, 5.0])                                      # after it as written
        offs = [a - b for a, b in zip(st[:4], [0, 1, 1.5, 2])]
        self.assertTrue(all(x >= y - 1e-9 for x, y in zip(offs, offs[1:])))      # decreasing: the middle compressed
        self.assertTrue(all(o > 0 for o in offs))                                 # never early in a calm style
        self.assertTrue(80 <= bp[0]['ms'] <= 155)                                 # ms at 100 bpm
        self.assertIn('back_phrase', {n for _, n, _ in vo.moves})
        # a harmony follows the lead's phrasing note for note
        h = singer.harmony(vo, steps=2, key='C major')
        self.assertEqual([round(n.start, 6) for n in h.notes], [round(x, 6) for x in st])
        self.assertTrue(h.expression['follow'])
        # pop: off by default; asked for, it may push ahead (early) - a calm style never does
        pop = singer.sing(s, XLINE, XTEXT, at=16, seed=3, track_id='p')
        self.assertEqual(pop.notes[0].start, 16.0)
        early = singer.sing(s, XLINE, XTEXT, at=24, seed=3, track_id='p2', back_phrase={'chance': 1.0, 'early': 1.0})
        self.assertLess(early.notes[0].start, 24.0)
        with self.assertRaises(singer.SingerError):
            singer.sing(s, XLINE, XTEXT, at=0, style='ballad', track_id='b', back_phrase={'early': 0.5})
        with self.assertRaises(singer.SingerError):
            singer.sing(s, XLINE, XTEXT, at=0, style='jazz', track_id='b2', back_phrase={'late_ms': 3})

    def test_ornaments_only_on_repeats_and_words_stay(self):
        s = _xsong(16)
        s._singer_dir = self.tmp
        mem = singer.Memory()
        kw = dict(style='jazz', memory=mem, back_phrase=False, messa_di_voce=False,
                  ornament={'amount': 1.0, 'every': 0.5, 'same_every': 0})
        first = singer.sing(s, XLINE, XTEXT, at=0, seed=5, **kw)
        self.assertEqual(first.expression['statement'], 0)
        self.assertEqual(first.expression['ornaments'], [])                       # the first statement plain
        self.assertEqual(len(first.notes), 7)
        again = singer.sing(s, XLINE, XTEXT, at=32, seed=5, track_id='v2', **kw)
        self.assertEqual(again.expression['statement'], 1)
        orn = again.expression['ornaments']
        self.assertTrue(orn)
        self.assertTrue(all(o['kind'] in singer.ORNAMENT_KINDS for o in orn))
        self.assertEqual(len(mem.used), len(orn))
        # the words stay: the same syllables in the same order, the ornaments are melisma notes of their syllable
        syl = [(n.syl.word, n.syl.nucleus) for n in again.notes if n.kind == 'syllable']
        self.assertEqual(syl, [(n.syl.word, n.syl.nucleus) for n in first.notes])
        self.assertTrue(all(n.kind in ('syllable', 'melisma') for n in again.notes))
        self.assertGreater(len(again.notes), 7 - 1 + sum(1 for o in orn if o['kind'] == 'blue'))
        self.assertEqual(sum(1 for n in again.notes if n.word_end), sum(1 for n in first.notes if n.word_end))
        ends = [n.start + n.dur for n in again.notes]
        self.assertAlmostEqual(max(ends), 32 + 7.0)                               # the line still ends where written
        self.assertTrue(all(b.start >= a.start for a, b in zip(again.notes, again.notes[1:])))
        # renders: the timeline holds every ornament note
        spec = singer._phrase_spec(again, again.phrases[0])
        job = singer._dur_job(spec)
        tl = singer._timeline(spec, singer._cons_lengths(job, [6.0] * len(job['phonemes']), spec), vb.get('hanami'))
        self.assertEqual(sum(tl['durations']), tl['frames'])
        # off: none; a double sings the same ornaments, a harmony none
        off = singer.sing(s, XLINE, XTEXT, at=32, seed=5, track_id='v3', style='jazz', ornament=False,
                          back_phrase=False)
        self.assertEqual(off.expression['ornaments'], [])
        d = singer.double(again)
        self.assertEqual([n.pitch for n in d.notes], [n.pitch for n in again.notes])
        self.assertEqual(singer.harmony(again, steps=2, key='C major').expression['ornaments'], [])

    def test_messa_on_peaks_mic_pull_on_ends(self):
        s = _xsong()
        s._singer_dir = self.tmp
        vo = singer.sing(s, XLINE, XTEXT, at=0, seed=2, style='ballad', back_phrase=False, ornament=False,
                         messa_di_voce={'chance': 1.0})
        self.assertEqual(len(vo.expression['messa']), 1)
        self.assertIn('messa', vo.plan[3])                                        # the held peak C5 ...
        self.assertNotIn(3, vo.mic)                                               # ... never pulled back
        self.assertIn(6, vo.mic)                                                  # the phrase-end hold is
        self.assertNotIn('messa', vo.plan[6])
        self.assertNotIn('swell', vo.plan[3])
        m = vo.plan[3]['messa']
        self.assertTrue(m['lo'] < 0 < m['peak'] and m['end'] < 0)
        spec = singer._phrase_spec(vo, vo.phrases[0])
        job = singer._dur_job(spec)
        tl = singer._timeline(spec, singer._cons_lengths(job, [6.0] * len(job['phonemes']), spec), vb.get('hanami'))
        core = tl['mix'].get('Root')
        self.assertIsInstance(core, list)                                        # sung soft + core at the swell's top
        self.assertGreater(max(core), 0.15)
        self.assertAlmostEqual(min(core), 0.0)
        heroes.hero(vo.track, family='vocal')
        r = self._compiled(s)
        t = next(x for x in r['tracks'] if x['id'] == 'vocal')
        air = [f.name for f in vo.track.fx].index('air')
        lvl = next(a['points'] for a in t['automation'] if a['target'] == f'fx.{air}.gain')
        post = [p for p in vo.expression['post'] if p['kind'] == 'messa']
        self.assertEqual(len(post), 1)
        inside = [v for b, v, *_ in lvl if post[0]['beat'] - 1e-6 <= b <= post[0]['end_beat'] + 1e-6]
        self.assertAlmostEqual(max(inside), m['peak'], delta=0.2)                 # swells after the compressor
        self.assertLess(min(inside), 0.0)
        self.assertTrue(vo.mic_pulls)                                             # the mic pull still written
        self.assertFalse([f for f in singer.diction(s) if f['severity'] == 'warn'])
        self.assertTrue(any('messa' in x for x in singer.expression_lines(s)))

    def test_emphasis_markup_and_intimate(self):
        s = _xsong()
        s._singer_dir = self.tmp
        text = 'Hold on to *night*, (( we were young. ))'
        vo = singer.sing(s, XLINE, text, at=0, seed=2, style='jazz', back_phrase=False, ornament=False,
                         messa_di_voce=False)
        self.assertEqual(vo.plan[3]['emph']['kind'], 'emph')
        self.assertTrue(all(vo.plan[i]['emph']['kind'] == 'intimate' for i in (4, 5, 6)))
        self.assertEqual([e['word'] for e in vo.expression['emphasis']], ['night', 'we', 'were', 'young'])
        spec = singer._phrase_spec(vo, vo.phrases[0])
        job = singer._dur_job(spec)
        tl = singer._timeline(spec, singer._cons_lengths(job, [6.0] * len(job['phonemes']), spec), vb.get('hanami'))
        n_tok = next(t for t in tl['tokens'] if t[0] == 'n' and t[2] <= tl['vowels'][3] + 1e-6
                     and t[1] >= tl['vowels'][2])
        f = int((n_tok[1] + n_tok[2]) / 2 / singer.FR - tl['offset_s'] / singer.FR)
        self.assertGreater(tl['gain'][f], 1.0)                                    # the crisper onset of 'night'
        heroes.hero(vo.track, family='vocal')
        r = self._compiled(s)
        kinds = [p['kind'] for p in vo.expression['post']]
        self.assertEqual(sorted(kinds), ['emphasis', 'intimate'])
        t = next(x for x in r['tracks'] if x['id'] == 'vocal')
        air = [f.name for f in vo.track.fx].index('air')
        lvl = next(a['points'] for a in t['automation'] if a['target'] == f'fx.{air}.gain')
        em = next(p for p in vo.expression['post'] if p['kind'] == 'emphasis')
        self.assertTrue(any(v >= 1.4 for b, v, *_ in lvl if em['beat'] <= b <= em['end_beat']))
        it = next(p for p in vo.expression['post'] if p['kind'] == 'intimate')
        self.assertTrue(any(v <= -1.9 for b, v, *_ in lvl if it['beat'] <= b <= it['end_beat']))
        self.assertFalse([f for f in singer.diction(s) if f['severity'] == 'warn'])  # the codas still sung
        # emphasis=False: the markup is ignored - the same takes (cache keys) as the plain words
        a = singer.sing(s, XLINE, text, at=0, seed=2, style='jazz', track_id='a', emphasis=False,
                        back_phrase=False, ornament=False, messa_di_voce=False)
        b = singer.sing(s, XLINE, XTEXT, at=0, seed=2, style='jazz', track_id='b',
                        back_phrase=False, ornament=False, messa_di_voce=False)
        self.assertEqual([singer._key(singer._phrase_spec(a, ph)) for ph in a.phrases],
                         [singer._key(singer._phrase_spec(b, ph)) for ph in b.phrases])
        # auto: the title words ('Night Young')
        au = singer.sing(s, XLINE, XTEXT, at=0, seed=2, style='jazz', track_id='au', emphasis='auto',
                         back_phrase=False, ornament=False, messa_di_voce=False)
        self.assertEqual(len(au.expression['emphasis']), 1)                      # at most one per phrase
        self.assertIn(au.expression['emphasis'][0]['word'], ('night', 'young'))
        self.assertTrue(au.expression['emphasis'][0]['auto'])

    def test_all_off_sings_as_before(self):
        s = _xsong()
        s._singer_dir = self.tmp
        off = dict(back_phrase=False, ornament=False, messa_di_voce=False, emphasis=False)
        vo = singer.sing(s, XLINE, 'Hold on to *night*, we were young.', at=0, seed=2, style='jazz', **off)
        self.assertEqual([(n.start, n.dur, n.pitch) for n in vo.notes],
                         [(n.start, n.dur, n.pitch) for n in XLINE])
        self.assertFalse(any(k in p for p in vo.plan.values() for k in ('emph', 'messa', 'blue')))
        self.assertEqual(singer.expression_lines(s), [])
        pop = singer.sing(s, XLINE, XTEXT, at=0, seed=2, track_id='pop')       # pop: none of them by default
        self.assertFalse(pop.expression['back_phrase'] or pop.expression['ornaments'] or pop.expression['messa'])

    def test_markup_in_the_lyrics(self):
        toks = lyrics.parse('Hold on to *night*, (( we were young. ))')
        self.assertEqual([(x.text, x.emph) for x in toks],
                         [('Hold', ''), ('on', ''), ('to', ''), ('night', 'emph'), ('we', 'intimate'),
                          ('were', 'intimate'), ('young', 'intimate')])
        self.assertEqual(toks[3].mark, ',')                                      # the phrase mark survives the markup
        glued = lyrics.parse('((Let you be,)) *two words* (maybe) now')
        self.assertEqual([x.emph for x in glued], ['intimate'] * 3 + ['emph'] * 2 + ['', ''])
        sung = lyrics.align(XLINE, 'Hold on to *night*, ((we were young.))')
        self.assertEqual([x.emph for x in sung], ['', '', '', 'emph', 'intimate', 'intimate', 'intimate'])
        plain = lyrics.align(XLINE, XTEXT)
        self.assertEqual([(a.syllable.word, a.syllable.phonemes, a.word_end, a.mark) for a in sung],
                         [(b.syllable.word, b.syllable.phonemes, b.word_end, b.mark) for b in plain])
        # the lyricist's checks read the same words with or without the markup
        self.assertEqual(lyrics.check(XLINE, 'Hold on to *night*, ((we were young.))'), lyrics.check(XLINE, XTEXT))
        for bad in ('(( never closed', 'closed )) only', 'an *open star', '(( a (( b )) c ))'):
            with self.assertRaises(lyrics.LyricsError):
                lyrics.parse(bad)

    def test_lean_gesture(self):
        from agentsound import gesture
        g = gesture.lean(8.0, 2.0, 100, air=1.5, shelf=1.5, ms=60.0, name='emphasis')
        self.assertEqual(g.name, 'emphasis')
        self.assertEqual(sorted(s.lane for s in g.shapes), ['air', 'shelf'])     # only the lanes asked for
        air = next(s for s in g.shapes if s.lane == 'air')
        self.assertEqual([round(v, 3) for _, v in air.keys], [0.0, 1.5, 1.5, 0.0])
        self.assertEqual((air.keys[1][0], air.keys[2][0]), (8.0, 10.0))      # the plateau covers the whole span
        self.assertAlmostEqual(8.0 - air.keys[0][0], 0.1)                      # 60 ms at 100 bpm, before it

    def test_codas_keep_their_length_off_the_grid(self):
        """A back-phrased / ornamented phrase puts notes off the frame grid: no word-final consonant may lose a frame
        to the rounding (it would warn coda_short)."""
        bank = vb.get('hanami')
        for seed in range(1, 9):
            s = _xsong()
            s._singer_dir = self.tmp
            vo = singer.sing(s, XLINE, 'Hold on to night, we want young.', at=0, seed=seed, style='jazz',
                             back_phrase={'chance': 1.0}, ornament=False, messa_di_voce=False)
            for ph in vo.phrases:
                spec = singer._phrase_spec(vo, ph)
                job = singer._dur_job(spec)
                tl = singer._timeline(spec, singer._cons_lengths(job, [6.0] * len(job['phonemes']), spec), bank)
                self.assertEqual(sum(tl['durations']), tl['frames'])
                for c in tl['diction']:
                    if c['cls'] != 'release':
                        self.assertGreaterEqual(c['ms'], singer.DICTION[c['cls']][3] * 1000 - 1e-6, (seed, c))


class VocalEars(unittest.TestCase):
    def test_check(self):
        rep = {'nodes': [
            {'id': 'vocal', 'mixSharePct': {'presence': 30.0}, 'bandsPct': {'presence': 30.0},
             'sections': [{'section': 'verse', 'rmsDb': -22.0}]},
            {'id': 'guitar', 'mixSharePct': {'presence': 45.0}, 'bandsPct': {'presence': 10.0},
             'sections': [{'section': 'verse', 'rmsDb': -18.0}]}],
            'sections': [{'name': 'verse', 'active': [{'id': 'guitar', 'rmsDb': -18.0}, {'id': 'vocal', 'rmsDb': -22.0}]}],
            'warnings': []}
        codes = {f['code'] for f in singer.check(rep)}
        self.assertEqual(codes, {'vocal_intelligibility', 'vocal_masked', 'vocal_harsh', 'vocal_buried'})
        rep['nodes'][0]['mixSharePct']['presence'] = 70.0
        rep['nodes'][0]['bandsPct']['presence'] = 8.0
        rep['nodes'][1]['mixSharePct']['presence'] = 12.0
        rep['sections'][0]['active'][0]['rmsDb'] = -26.0
        self.assertEqual(singer.check(rep), [])

    def test_wetness_from_the_send_shares(self):
        # a plate fed by the vocal and a pad at equal power: half of it is the vocal's (-3 dB); the echo only by the
        # vocal, sounding a quarter of the song (its song-long energy -6 dB)
        rep = {'nodes': [{'id': 'vocal', 'lufs': -20.0, 'activePct': 100.0},
                         {'id': 'pad', 'lufs': -20.0, 'activePct': 100.0},
                         {'id': 'plate', 'lufs': -30.0, 'activePct': 100.0, 'role': 'return', 'returnKind': 'reverb'},
                         {'id': 'echo', 'lufs': -30.0, 'activePct': 25.0, 'role': 'return', 'returnKind': 'delay'}]}
        render = {'tracks': [{'id': 'vocal', 'sends': {'plate': -12.0, 'echo': {'db': -20.0, 'tap': 'pre:air'}}},
                             {'id': 'pad', 'sends': {'plate': -12.0}}], 'buses': []}
        w = singer.wetness(rep, render, ['vocal', 'pad', 'missing'])
        self.assertEqual(w['vocal']['returnsLu'], {'plate': -13.0, 'echo': -16.0})
        self.assertEqual(w['vocal']['wetLu'], -11.2)
        self.assertEqual(w['pad'], {'wetLu': -13.0, 'returnsLu': {'plate': -13.0}})
        self.assertNotIn('missing', w)

    def test_check_where_the_voice_sings_by_genre(self):
        # 30 % of the song's presence band, all of it in the verse; the instrumental solo holds the rest: in the
        # sections she sings she owns 60 % - no intelligibility warning. Rock allows the voice in the band.
        sec = lambda n, a, b, db: {'name': n, 'startSec': a, 'endSec': b, 'rmsDb': db, 'bandsPct': {'presence': 20.0}}
        rep = {'reference': {'profile': 'pop'}, 'warnings': [],
               'sections': [sec('verse', 0, 10, -20.0), sec('solo', 10, 20, -20.0)],
               'nodes': [{'id': 'vocal', 'mixSharePct': {'presence': 30.0}, 'bandsPct': {'presence': 10.0},
                          'sections': [{'section': 'verse', 'rmsDb': -22.0}, {'section': 'solo', 'rmsDb': -90.0}]}]}
        self.assertEqual(singer.check(rep), [])
        rep['nodes'][0]['mixSharePct']['presence'] = 16.0                  # 32 % where she sings
        self.assertEqual({f['code'] for f in singer.check(rep)}, {'vocal_intelligibility'})
        rep['reference']['profile'] = 'rock'                               # rock: >= 30 %
        self.assertEqual(singer.check(rep), [])

    def test_wordless_and_backing_parts_are_not_judged(self):
        from types import SimpleNamespace as NS
        part = lambda text: NS(lyrics_text=text)
        self.assertTrue(singer.wordless(part('whoa, oh - oh, hey!')))
        self.assertFalse(singer.wordless(part('hold on, hey')))
        song = NS(tracks={
            'vocal': NS(id='vocal', _singer={'parts': [part('hold on to the night')]}),
            'gang': NS(id='gang', _singer={'parts': [part('whoa oh'), part('hey!')]}),
            'vocal_dbl1': NS(id='vocal_dbl1', _singer={'parts': [part('hold on to the night')]}),
            'vocal_prism2': NS(id='vocal_prism2', _singer={'parts': [part('hold on')]})})
        self.assertEqual(singer.lead_tracks(song), ['vocal'])


class VocalFx(_Env):
    """The processed-voice effects: pitch correction (sing(tune=)), the prism / harmoniser of re-sung takes
    (singer.prism) and the talk box's mouth (singer.mouth + speech.talkbox)."""

    def test_tune_curve_hard_steps_and_soft_keeps_some_vibrato(self):
        import math
        fr = singer.FR
        m = []
        for f in range(200):              # C4, a 150 ms glide up a fifth, G4; a 30 ct vibrato all along
            t = f * fr
            b = 60 if t < 0.5 else 67 if t > 0.65 else 60 + 7 * (t - 0.5) / 0.15
            m.append(b + 0.3 * math.sin(2 * math.pi * 5.5 * t))
        major = [0, 2, 4, 5, 7, 9, 11]
        hard = singer.tune_curve(m, {'pcs': major, 'retune_ms': 0.0, 'hold': 0.06})
        self.assertEqual(sorted(set(hard)), [60, 62, 64, 65, 67])         # stair steps through the scale, no vibrato
        steps = [i for i in range(1, len(hard)) if hard[i] != hard[i - 1]]
        self.assertEqual(len(steps), 4)                                      # one flip per scale step, no chatter
        soft = singer.tune_curve(m, {'pcs': major, 'retune_ms': 40.0, 'hold': 0.15})
        span = max(soft[100:]) - min(soft[100:])
        self.assertTrue(0.1 < span < 0.6 - 0.05)                             # some of the vibrato survives
        self.assertAlmostEqual(sum(soft[150:]) / 50, 67.0, delta=0.08)       # centred on the note
        # pentatonic: F (65) is not in C major pentatonic -> E or G
        pent = singer.tune_curve([65.1] * 5, {'pcs': [0, 2, 4, 7, 9], 'retune_ms': 0.0, 'hold': 0.0})
        self.assertIn(pent[0], (64, 67))
        # a consonant's 2-frame pitch dip on a held G is no 23 ms blip onto F; a real note change stays on time
        dip = [67.0] * 10 + [65.4, 65.6] + [67.0] * 10 + [69.0] * 10
        out = singer.tune_curve(dip, dict(singer.TUNE['hard'], pcs=major))
        self.assertEqual(out, [67.0] * 22 + [69.0] * 10)

    def test_sing_tune_options_spec_and_inheritance(self):
        s = _song()
        s._singer_dir = self.tmp
        plain = singer.sing(s, LINE, TEXT, at=0, seed=2)
        self.assertIsNone(plain.tune)
        self.assertNotIn('tune', singer._phrase_spec(plain, plain.phrases[0]))   # untuned takes keep their cache keys
        vo = singer.sing(s, LINE, TEXT, at=0, seed=2, tune='hard', track_id='vocal_t')
        self.assertEqual(vo.tune['mode'], 'hard')
        self.assertEqual(vo.tune['retune_ms'], 0.0)
        self.assertEqual(vo.tune['pcs'], [0, 2, 4, 5, 7, 9, 11])                  # the song's key (C major)
        self.assertNotEqual(singer._key(singer._phrase_spec(vo, vo.phrases[0])),
                            singer._key(singer._phrase_spec(plain, plain.phrases[0])))
        so = singer.sing(s, LINE, TEXT, at=0, tune='soft', retune_ms=25, scale='notes', track_id='vocal_s')
        self.assertEqual(so.tune['retune_ms'], 25.0)
        self.assertEqual(so.tune['pcs'], [0, 4, 7, 9])                            # the line's own pitch classes
        mp = singer.sing(s, LINE, TEXT, at=0, tune={'mode': 'hard', 'scale': 'minor_pentatonic'}, key='A minor',
                         track_id='vocal_p')
        self.assertEqual(mp.tune['pcs'], [0, 2, 4, 7, 9])                         # A C D E G
        d = singer.double(vo, pan=-0.5)
        self.assertEqual(d.tune, vo.tune)                                         # doubles inherit the correction
        with self.assertRaises(singer.SingerError):
            singer.sing(s, LINE, TEXT, at=0, tune='robot', track_id='vocal_x')
        with self.assertRaises(singer.SingerError):
            singer.sing(s, LINE, TEXT, at=0, retune_ms=10, track_id='vocal_y')

    def test_tuned_take_gets_the_corrected_f0(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE, TEXT, at=0, seed=4, tune='hard', pitch='player')
        calls, jobs = [], []
        fake = _fake_run(calls)

        def run(bank, js, **kw):
            jobs.extend(js)
            return fake(bank, js, **kw)
        with mock.patch.object(vb, 'run', run), mock.patch.object(vb, 'runner_ok', lambda: (True, '')):
            s.compile()
        import math
        for j in (j for j in jobs if j['op'] == 'sing'):
            midi = [69 + 12 * math.log2(f / 440.0) for f in j['f0']]
            self.assertTrue(all(abs(m - round(m)) < 1e-3 for m in midi))         # every frame on a semitone ...
            self.assertTrue(all(round(m) % 12 in (0, 2, 4, 5, 7, 9, 11) for m in midi))   # ... of C major
        meta = json.loads(Path(vo.rendered[0]['path']).with_suffix('.json').read_text(encoding='utf-8'))
        self.assertIn('midi_sung', meta['timeline'])                             # the curve before the correction

    def test_prism_voices_on_chord_tones(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE, TEXT, at=0, seed=4)
        h = s.harmony('C Am F G', at=0)
        pr = singer.prism(vo, h)
        self.assertEqual(len(pr.voices), 4)
        self.assertEqual(sum(1 for L in pr.pitches if sum(L) / len(L) < 72), 3)  # 3 below the lead, 1 above
        src = vo.src
        for L in pr.pitches:
            self.assertEqual(len(L), len(src))
            for (st, _, lead, _), p in zip(src, L):
                c = h.at(st)
                self.assertIn(p % 12, set(c.pcs))                                 # a chord tone of the harmony there
                self.assertGreaterEqual(abs(p - lead), 2)                          # no unison / second on the lead
                self.assertTrue(53 <= p <= 81)                                     # Hanami's range F3-A5
        # each voice is a real take: its own track, take, pan, formant; all on the bus 'vocal_prism'
        self.assertEqual(len({v.take for v in pr.voices}), 4)
        self.assertEqual(len({v.track.pan for v in pr.voices}), 4)
        self.assertTrue(max(v.track.pan for v in pr.voices) > 0 > min(v.track.pan for v in pr.voices))
        self.assertTrue(all(v.track.output == 'vocal_prism' for v in pr.voices))
        self.assertIsNone(pr.voices[0].tune)                                      # choir-of-one: natural pitch
        z = singer.prism(vo, h, preset='prismizer')
        self.assertEqual(len(z.voices), 5)                                        # 4 + the octave under
        self.assertTrue(all(abs(p - q) == 12 for (_, _, p, _), q in zip(src, z.pitches[-1])))
        lo = singer.prism(singer.sing(s, LINE.transpose(5), TEXT, at=0, track_id='vocal_hi'), h, preset='prismizer')
        self.assertEqual(lo.pitches[-1], [n.pitch - 12 for n in LINE.transpose(5)])     # the whole line under
        self.assertTrue(all(v.tune and v.tune['mode'] == 'hard' for v in z.voices))
        self.assertTrue(max(abs(v.formant) for v in z.voices) > 0.8)
        # voice leading: no voice jumps more than a fifth between two notes of the same chord
        for L in pr.pitches:
            for (a, _, _, _), (b, _, _, _), p, q in zip(src, src[1:], L, L[1:]):
                if h.symbol_at(a) == h.symbol_at(b):
                    self.assertLessEqual(abs(p - q), 7)
        # the prism voices are backing: the vocal checks do not take them for the lead
        self.assertRegex('vocal_prism3', singer._BACKING)

    def test_mouth_is_flat_and_talkbox_keys_the_guitar(self):
        from agentsound import speech
        from agentsound.patches import inst
        s = _song()
        s._singer_dir = self.tmp
        m = singer.mouth(s, LINE, TEXT, at=0, voice='hanami')
        self.assertEqual({n.pitch for n in m.notes}, {53 + 5})                      # one low pitch
        self.assertNotIn('vibrato', {name for _, name, _ in m.moves})
        self.assertNotIn('scoop', {name for _, name, _ in m.moves})
        self.assertEqual(m.pitch_mode, 'player')
        gtr = s.track('talkbox', 'sampled/lead_guitar')
        types = [f.type for f in gtr.fx]
        self.assertEqual(types[:2], ['amp', 'convolver'])
        speech.talkbox(gtr, m)
        types = [f.type for f in gtr.fx]
        self.assertEqual(types[:2], ['amp', 'vocoder'])                              # the horn replaces the cabinet
        self.assertNotIn('convolver', types)
        v = gtr.fx[1]
        self.assertEqual(v.sidechain, 'talkbox_mouth')
        self.assertEqual(v.params['mode'], 'lpc')
        self.assertTrue(m.track.mute)
        speech.talkbox(gtr, m, shift=-3)                                             # again: re-keyed, updated
        self.assertEqual([f.type for f in gtr.fx].count('vocoder'), 1)
        self.assertEqual(gtr.fx[1].params['shift'], -3)
        syn = s.track('syn', inst.va(osc1__wave='saw'), fx=[speech.FX('eq', {'hp.freq': 100})])
        speech.talkbox(syn, m.track, mute=False)
        self.assertEqual(syn.fx[0].type, 'vocoder')                                  # a synth: first in the chain
        with self.assertRaises(speech.SpeechError):
            speech.talkbox(m.track, m)


class Credits(_Env):
    def test_voice_credit(self):
        from agentsound import delivery
        d = self.tmp / 'song' / 'samples' / 'vocals' / 'tiger'
        vb.write_source(vb.get('tiger'), d)
        wav = d / 'vocal-x.wav'
        wav.write_bytes(b'')
        render = {'tracks': [{'id': 'vocal', 'instrument': {'type': 'sampler', 'params': {
            'samples': [{'file': str(wav).replace(os.sep, '/'), 'root': 0, 'lo': 0, 'hi': 0}]}}, 'fx': []}],
            'buses': [], 'master': {'fx': []}}
        c = delivery.collect_credits(render)
        src = [x for x in c['sources'] if x['kind'] == 'voice']
        self.assertEqual(len(src), 1)
        self.assertEqual(src[0]['class'], 'nc')
        self.assertTrue(any('non-commercial voice' in w for w in c['warnings']))
        self.assertIn('TIGER', delivery.credits_text(c, 'T', 'A'))


if __name__ == '__main__':
    unittest.main()
