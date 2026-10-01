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
        self.assertTrue(any('throws: 2 phrase ends' in x for x in vo.track.hero.compile_log))
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
