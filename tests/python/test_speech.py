"""agentsound.speech (Windows TTS for the vocoder), the vocoder patches and the voices / speak commands."""

import array
import json
import math
import os
import shutil
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from agentsound import Song, cli, inst, patches, speech
from agentsound.song import dumps

INSTALLED = [
    {'name': 'Microsoft Zira Desktop', 'engine': 'sapi', 'language': 'en-US', 'gender': 'Female', 'age': 'Adult', 'default': False},
    {'name': 'Microsoft Hedda Desktop', 'engine': 'sapi', 'language': 'de-DE', 'gender': 'Female', 'age': 'Adult', 'default': True},
    {'name': 'Microsoft Hedda', 'engine': 'onecore', 'language': 'de-DE', 'gender': 'Female', 'age': '', 'default': False},
    {'name': 'Microsoft Stefan', 'engine': 'onecore', 'language': 'de-DE', 'gender': 'Male', 'age': '', 'default': True},
    {'name': 'Microsoft Katja', 'engine': 'onecore', 'language': 'de-DE', 'gender': 'Female', 'age': '', 'default': False},
]


def write_wav(path, samples, sr=16000):
    a = array.array('h', (max(-32767, min(32767, int(round(v * 32767)))) for v in samples))
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(a.tobytes())


def read_wav(path):
    with wave.open(str(path), 'rb') as w:
        sr = w.getframerate()
        a = array.array('h', w.readframes(w.getnframes()))
    return [v / 32768.0 for v in a], sr


def fake_speech(sr=16000, pre=0.3, dur=0.5, post=0.4, amp=0.05):
    """Silence, a 'word' (a 150 Hz buzz with a few harmonics), silence."""
    x = [0.0] * int(pre * sr)
    for i in range(int(dur * sr)):
        t = i / sr
        x.append(amp * sum(math.sin(2 * math.pi * 150 * h * t) / h for h in range(1, 6)))
    return x + [0.0] * int(post * sr)


def active_level_db(x, sr):
    fl = int(0.02 * sr)
    frames = [sum(v * v for v in x[i:i + fl]) / fl for i in range(0, len(x) - fl + 1, fl)]
    mx = max(frames)
    act = [f for f in frames if f > mx * 10 ** -3.5]
    return 10 * math.log10(sum(act) / len(act))


class Voices(unittest.TestCase):
    def test_find_voice(self):
        f = lambda n: speech.find_voice(n, INSTALLED)
        self.assertEqual(f('zira')['name'], 'Microsoft Zira Desktop')
        self.assertEqual(f('Microsoft Zira Desktop')['engine'], 'sapi')
        self.assertEqual(f('hedda')['engine'], 'onecore')              # both engines: OneCore wins ...
        self.assertEqual(f('hedda desktop')['engine'], 'sapi')         # ... unless the name says desktop
        self.assertEqual(f('sapi:hedda')['name'], 'Microsoft Hedda Desktop')
        self.assertEqual(f('onecore:STEFAN')['name'], 'Microsoft Stefan')
        self.assertIsNone(f(None))
        with self.assertRaisesRegex(speech.SpeechError, 'no installed voice matches'):
            f('david')
        with self.assertRaisesRegex(speech.SpeechError, 'ambiguous'):
            f('microsoft')
        with self.assertRaisesRegex(speech.SpeechError, "engine prefix"):
            f('azure:zira')

    def test_without_powershell(self):  # (non-Windows systems take the same path)
        with mock.patch.object(speech.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(speech.SpeechError, 'needs Windows'):
                speech._run_ps('', 'x', 'speak()')
            self.assertEqual(speech.voices(refresh=True), [])
            d = Path(tempfile.mkdtemp())
            self.addCleanup(shutil.rmtree, d, True)
            with self.assertRaisesRegex(speech.SpeechError, 'cached next to the song'):
                speech.speak('uncached words', cache_dir=d)
        speech._VOICES = None


class Speak(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.calls = []

        def synth(spoken, is_ssml, voice, rate, volume, dest):
            self.calls.append((spoken, is_ssml, voice, rate))
            raw = self.dir / 'raw.wav'
            write_wav(raw, fake_speech())
            dest.parent.mkdir(parents=True, exist_ok=True)
            speech._process(raw, dest, 'test')
        p = mock.patch.object(speech, '_synthesize', side_effect=synth)
        p.start()
        self.addCleanup(p.stop)

    def test_cache_and_processing(self):
        a = speech.speak('Neon lights', voice='zira', cache_dir=self.dir / 'c')
        b = speech.speak('Neon lights', voice='zira', cache_dir=self.dir / 'c')
        self.assertEqual(a, b)
        self.assertEqual(len(self.calls), 1, 'the second call is served from the cache')
        self.assertTrue(a.name.startswith('neon_lights-') and a.suffix == '.wav', a.name)
        speech.speak('Neon lights', voice='zira', rate=-2, cache_dir=self.dir / 'c')
        speech.speak('Neon lights', voice='stefan', cache_dir=self.dir / 'c')
        self.assertEqual(len(self.calls), 3, 'rate and voice are part of the cache key')
        x, sr = read_wav(a)
        self.assertAlmostEqual(active_level_db(x, sr), speech.LEVEL_DBFS, delta=0.3)
        self.assertLess(len(x) / sr, 0.5 + 0.1, 'leading / trailing silence trimmed')
        self.assertGreater(len(x) / sr, 0.5)
        self.assertEqual(x[0], 0.0)  # faded in from zero
        # path= copies the cached file
        out = speech.speak('Neon lights', self.dir / 'copy.wav', voice='zira', cache_dir=self.dir / 'c')
        self.assertEqual(out.read_bytes(), a.read_bytes())
        self.assertEqual(len(self.calls), 3)

    def test_ssml(self):
        speech.speak('hi <emphasis>there</emphasis>', ssml=True, cache_dir=self.dir)
        self.assertEqual(self.calls[-1][:2], ('hi <emphasis>there</emphasis>', True))
        p = speech.speak('label', ssml='<speak version="1.0" xml:lang="en-US"><break time="100ms"/>hi</speak>', cache_dir=self.dir)
        self.assertTrue(p.name.startswith('label-'))
        self.assertIn('break', self.calls[-1][0])

    def test_validation(self):
        for kw in ({'rate': 11}, {'volume': -1}, {'rate': True}, {'ssml': 3}):
            with self.assertRaises(speech.SpeechError):
                speech.speak('x', cache_dir=self.dir, **kw)
        with self.assertRaises(speech.SpeechError):
            speech.speak('   ', cache_dir=self.dir)

    def test_silence_is_an_error(self):
        raw = self.dir / 'silent.wav'
        write_wav(raw, [0.0] * 1000)
        with self.assertRaisesRegex(speech.SpeechError, 'silence'):
            speech._process(raw, self.dir / 'o.wav', 'test')

    def test_words(self):
        vox = speech.words(['neon lights', 'city nights', 'drive'], voice='zira', root='C2', cache_dir=self.dir)
        self.assertEqual((vox['neon lights'], vox['city nights'], vox['drive']), (36, 37, 38))
        zones = vox.zones()
        self.assertEqual([(z['root'], z['lo'], z['hi']) for z in zones], [(36, 36, 36), (37, 37, 37), (38, 38, 38)])
        self.assertTrue(all(os.path.isabs(z['file']) and '\\' not in z['file'] for z in zones))
        i = vox.instrument(level=-2)
        self.assertEqual((i.type, i.params['oneshot'], i.params['level']), ('sampler', 'on', -2))
        self.assertAlmostEqual(vox.beats('drive', 120), vox.seconds['drive'] * 2)
        c = vox.clip({0: 'neon lights', 2: 'city nights'}, length=4)
        self.assertEqual([(n.start, n.pitch, n.vel) for n in c], [(0.0, 36, 127), (2.0, 37, 127)])
        self.assertEqual(c.length, 4)
        c2 = vox.clip([(1, 'drive', 90)], tempo=120)
        self.assertAlmostEqual(c2.notes[0].dur, vox.beats('drive', 120))
        self.assertEqual(c2.notes[0].vel, 90)
        with self.assertRaisesRegex(speech.SpeechError, "no word 'nope'"):
            vox['nope']
        with self.assertRaises(speech.SpeechError):
            speech.words(['a', 'a'], cache_dir=self.dir)
        with self.assertRaises(speech.SpeechError):
            speech.words(['a', 'b'], root=127, cache_dir=self.dir)
        z = speech.phrase('midnight drive', 'C4', cache_dir=self.dir)
        self.assertEqual((z['root'], z['lo'], z['hi']), (60, 60, 60))

    def test_default_cache_is_next_to_the_calling_file(self):
        here = Path(__file__).resolve().parent
        with mock.patch.object(speech, '_caller_dir', return_value=self.dir / 'song'):
            p = speech.speak('x')
        self.assertEqual(p.parent, self.dir / 'song' / 'samples' / 'speech')
        self.assertEqual(speech._caller_dir(), here)


class Request(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_request_to_powershell(self):
        """_synthesize: voice resolution, rate mapping and SSML fragments wrapped in the voice's language."""
        seen = {}

        def fake_ps(script, arg, what):
            req = json.loads(Path(arg).read_text(encoding='utf-8'))
            seen.update(req)
            write_wav(req['out'], fake_speech())
        with mock.patch.object(speech, '_run_ps', side_effect=fake_ps), \
             mock.patch.object(speech, 'voices', return_value=[dict(v) for v in INSTALLED]):
            speech._synthesize('hallo <break time="200ms"/> welt', True, 'stefan', -5, 80, self.dir / 'x.wav')
        self.assertEqual((seen['engine'], seen['voice'], seen['ssml']), ('onecore', 'Microsoft Stefan', True))
        self.assertIn('xml:lang="de-DE"', seen['text'])
        self.assertTrue(seen['text'].startswith('<speak') and seen['text'].endswith('</speak>'))
        self.assertEqual((seen['rate'], seen['volume']), (-5, 80))
        self.assertAlmostEqual(seen['speakingRate'], 3 ** -0.5)
        self.assertTrue((self.dir / 'x.wav').is_file())


def _voice_song():
    s = Song('Vocoder', tempo=100, key='A minor')
    sec = s.section('a', bars=2)
    voice = s.track('voice', inst.va(osc1__wave='saw', noise__level=0.2))
    voice.note('A2', sec.start, 4)
    return s, sec, voice


class Vocode(unittest.TestCase):
    def test_vocode_keys_and_mutes(self):
        s, sec, voice = _voice_song()
        choir = s.track('choir', 'synthwave/vocoder_choir')
        choir.play(s.prog('i VI').block(), sec)
        self.assertIs(speech.vocode(choir, voice, shift=-4), choir)
        voc = [f for f in choir.fx if f.type == 'vocoder']
        self.assertEqual(len(voc), 1)
        self.assertEqual((voc[0].sidechain, voc[0].params['shift']), ('voice', -4))
        self.assertTrue(voice.mute)
        r = s.compile()
        tracks = {t['id']: t for t in r['tracks']}
        self.assertTrue(tracks['voice']['mute'])
        self.assertEqual(tracks['choir']['fx'][0]['sidechain'], 'voice')
        # a track without a vocoder gets one appended
        lead = s.track('lead', inst.va())
        speech.vocode(lead, voice, mode='lpc')
        self.assertEqual((lead.fx[-1].type, lead.fx[-1].params, lead.fx[-1].sidechain), ('vocoder', {'mode': 'lpc'}, 'voice'))
        with self.assertRaises(speech.SpeechError):
            speech.vocode(lead, lead)
        with self.assertRaisesRegex(speech.SpeechError, 'track object'):
            speech.vocode(lead, 'voice')
        speech.vocode(lead, 'voice', mute=False)

    def test_patches(self):
        self.assertEqual(patches.list('synthwave/vocoder') + patches.list('synthwave/talkbox'),
                         ['synthwave/vocoder_choir', 'synthwave/vocoder_lead', 'synthwave/talkbox'])
        for n in ('synthwave/vocoder_choir', 'synthwave/vocoder_lead', 'synthwave/talkbox'):
            p = patches.get(n)
            self.assertEqual(p.fx[0].type, 'vocoder', n)
            self.assertIsNone(p.fx[0].sidechain, n)
            self.assertIn('speech.vocode', p.notes, n)
            self.assertIn('-18 LUFS', p.notes, n)
        self.assertEqual(patches.get('synthwave/talkbox').fx[0].params['mode'], 'lpc')

    def test_audition_songs_get_a_voice(self):
        with mock.patch.object(speech, 'voices', return_value=[]), \
             mock.patch.object(speech, 'phrase', side_effect=speech.SpeechError('no tts here')):
            for n in ('synthwave/vocoder_choir', 'synthwave/talkbox'):
                r = cli.audition_song(n).compile()
                tracks = {t['id']: t for t in r['tracks']}
                self.assertTrue(tracks['voice']['mute'], n)
                self.assertTrue(tracks['voice']['notes'], n)
                self.assertEqual(tracks['patch']['fx'][0]['sidechain'], 'voice', n)


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


@unittest.skipIf(_engine() is None, 'engine not built')
class EngineValidation(unittest.TestCase):
    def validate(self, song):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        rj = d / 'song.render.json'
        rj.write_text(dumps(song.compile()), encoding='utf-8')
        return subprocess.run([str(_engine()), 'validate', str(rj)], capture_output=True, text=True)

    def test_keyed_vocoder_patches_pass(self):
        s, sec, voice = _voice_song()
        for n in ('synthwave/vocoder_choir', 'synthwave/vocoder_lead', 'synthwave/talkbox'):
            t = s.track(n.split('/')[1], n)
            t.note('A3', sec.start, 4)
            speech.vocode(t, voice)
        proc = self.validate(s)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_unkeyed_vocoder_is_rejected(self):
        s, sec, voice = _voice_song()
        s.track('choir', 'synthwave/vocoder_choir').note('A3', sec.start, 4)
        proc = self.validate(s)
        self.assertEqual(proc.returncode, 2)
        self.assertIn('needs a "sidechain"', proc.stderr)


class Cli(unittest.TestCase):
    def test_parser(self):
        a = cli.build_parser().parse_args(['speak', 'hello robot', '--out', 'x.wav', '--voice', 'zira', '--rate', '-2', '--ssml'])
        self.assertEqual((a.text, a.out, a.voice, a.rate, a.ssml, a.func), ('hello robot', 'x.wav', 'zira', -2.0, True, cli.cmd_speak))
        v = cli.build_parser().parse_args(['voices', '--json'])
        self.assertTrue(v.json)

    def test_voices_json(self):
        with mock.patch.object(speech, 'voices', return_value=INSTALLED):
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(cli.main(['voices', '--json']), 0)
            self.assertEqual(json.loads(buf.getvalue())[0]['name'], 'Microsoft Zira Desktop')


@unittest.skipUnless(os.name == 'nt' and shutil.which('powershell.exe'), 'Windows text-to-speech only')
class RealTts(unittest.TestCase):
    def test_speak_a_word(self):
        vs = speech.voices(refresh=True)
        if not vs:
            self.skipTest('no voices installed')
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        p = speech.speak('robot', voice=f"{vs[0]['engine']}:{vs[0]['name']}", cache_dir=d)
        x, sr = read_wav(p)
        self.assertGreater(len(x) / sr, 0.15)
        level, peak = active_level_db(x, sr), 20 * math.log10(max(abs(v) for v in x))
        # -18 dBFS active level, unless the -1 dBFS peak limit holds it lower
        self.assertTrue(abs(level - speech.LEVEL_DBFS) < 0.3 or (level < speech.LEVEL_DBFS and peak > -1.2),
                        f"level {level:.1f} dBFS, peak {peak:.1f} dBFS")
        self.assertLess(peak, -0.9)


if __name__ == '__main__':
    unittest.main()
