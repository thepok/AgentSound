"""Speech for the vocoder: Windows text-to-speech (no downloads) as WAV files the sampler plays.

The vocoder 'sings' the notes of its carrier (chords on the carrier = a robot choir, a saw line = a robot lead)
while a speech track gives it the words. The speech track is only the modulator: speech.vocode() keys the
carrier's vocoder with it and mutes it, so only the robot is heard.

    from agentsound import speech
    vox = speech.words(['neon lights', 'city nights', 'midnight', 'drive'], voice='zira', rate=-1)
    voice = s.track('voice', vox.instrument())               # a one-shot sampler: word i on key root + i
    voice.play(vox.clip({0: 'neon lights', 2: 'city nights'}, length=4), verse.bar(4))
    choir = s.track('choir', 'synthwave/vocoder_choir')      # the carrier: its notes are the robot's pitches
    choir.play(s.prog('i VI').block(), verse)
    speech.vocode(choir, voice)                              # key the vocoder with the voice, mute the voice

speak() renders one text (plain or SSML) with a Windows voice: the classic SAPI desktop voices (System.Speech) and,
when PowerShell reaches them, the newer OneCore voices (Windows.Media.SpeechSynthesis). voices() lists what is
installed (`python -m agentsound voices`). Every result is trimmed (silence before / after the speech), normalised
to an active speech level of -18 dBFS (the vocoder's calibration) and cached by a hash of everything that shapes
it, by default in <song folder>/samples/speech/: a song re-renders identically from the cached WAVs on any machine
(commit them with the song), and only a changed text / voice / rate calls the synthesiser again. Without Windows
(and without the cached file) speak() raises SpeechError.
"""

from __future__ import annotations

import array
import base64
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from .patches import FX, Instrument, _ref, inst
from .patterns import Clip
from .theory import ComposeError, note

__all__ = ['SpeechError', 'Words', 'speak', 'voices', 'find_voice', 'words', 'phrase', 'vocode', 'wav_seconds',
           'LEVEL_DBFS']

LEVEL_DBFS = -18.0        # active speech level of every rendered file (the vocoder is calibrated to it)
_FORMAT = 1               # bump when the processing below changes (new cache keys)
_PRE_MS, _POST_MS = 5.0, 40.0   # silence kept before / after the speech when trimming
_FADE_MS = 2.0
_TRIM_DB = -50.0          # trim threshold re the loudest 10 ms


class SpeechError(ComposeError):
    """Text-to-speech is unavailable or failed (a ComposeError, so songs report it like any other mistake)."""


# ------------------------------------------------------------------------------------------ PowerShell

_POWERSHELL = 'powershell.exe'   # Windows PowerShell 5.1: has System.Speech and the WinRT projection

_PS_PRELUDE = r"""
$ErrorActionPreference = 'Stop'
function Await($op, [Type]$t) {
  Add-Type -AssemblyName System.Runtime.WindowsRuntime
  $m = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }
  $task = $m[0].MakeGenericMethod($t).Invoke($null, @($op))
  $null = $task.Wait(-1)
  $task.Result
}
"""

_PS_VOICES = _PS_PRELUDE + r"""
$out = @()
try {
  Add-Type -AssemblyName System.Speech
  $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
  $default = $s.Voice.Name
  foreach ($v in $s.GetInstalledVoices()) {
    if (-not $v.Enabled) { continue }
    $i = $v.VoiceInfo
    $out += [pscustomobject]@{ name = $i.Name; engine = 'sapi'; language = $i.Culture.Name; gender = "$($i.Gender)";
                               age = "$($i.Age)"; default = ($i.Name -eq $default) }
  }
  $s.Dispose()
} catch {}
try {
  $null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]
  $d = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::DefaultVoice.DisplayName
  foreach ($v in [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices) {
    $out += [pscustomobject]@{ name = $v.DisplayName; engine = 'onecore'; language = $v.Language; gender = "$($v.Gender)";
                               age = ''; default = ($v.DisplayName -eq $d) }
  }
} catch {}
[IO.File]::WriteAllText($args0, (ConvertTo-Json -InputObject @($out) -Compress), [Text.Encoding]::UTF8)
"""

_PS_SPEAK = _PS_PRELUDE + r"""
$req = [IO.File]::ReadAllText($args0, [Text.Encoding]::UTF8) | ConvertFrom-Json
if ($req.engine -eq 'onecore') {
  $null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]
  $null = [Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime]
  $synth = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
  if ($req.voice) {
    $synth.Voice = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object { $_.DisplayName -eq $req.voice } | Select-Object -First 1
  }
  try { $synth.Options.SpeakingRate = [double]$req.speakingRate; $synth.Options.AudioVolume = [double]$req.audioVolume } catch {}
  if ($req.ssml) { $op = $synth.SynthesizeSsmlToStreamAsync($req.text) } else { $op = $synth.SynthesizeTextToStreamAsync($req.text) }
  $stream = Await $op ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
  $size = [uint32]$stream.Size
  $reader = New-Object Windows.Storage.Streams.DataReader($stream.GetInputStreamAt(0))
  $null = Await ($reader.LoadAsync($size)) ([uint32])
  $bytes = New-Object byte[] $size
  $reader.ReadBytes($bytes)
  [IO.File]::WriteAllBytes($req.out, $bytes)
} else {
  Add-Type -AssemblyName System.Speech
  $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
  if ($req.voice) { $s.SelectVoice($req.voice) }
  $s.Rate = [int]$req.rate
  $s.Volume = [int]$req.volume
  $s.SetOutputToWaveFile($req.out)
  if ($req.ssml) { $s.SpeakSsml($req.text) } else { $s.Speak($req.text) }
  $s.SetOutputToNull()
  $s.Dispose()
}
"""


def _run_ps(script: str, arg: str, what: str) -> None:
    if os.name != 'nt' or shutil.which(_POWERSHELL) is None:
        raise SpeechError(f"{what}: text-to-speech needs Windows (PowerShell with System.Speech); this is "
                          f"{sys.platform}. Render the speech on Windows once - the WAVs are cached next to the song - "
                          f"or give the sampler recorded WAVs.")
    code = f"$args0 = '{arg.replace(chr(39), chr(39) * 2)}'\n" + script
    enc = base64.b64encode(code.encode('utf-16-le')).decode('ascii')
    try:
        proc = subprocess.run([_POWERSHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                               '-EncodedCommand', enc], capture_output=True, text=True, encoding='utf-8',
                              errors='replace', timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise SpeechError(f"{what}: could not run PowerShell ({e})") from None
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or '').strip().splitlines()
        raise SpeechError(f"{what}: PowerShell failed: {' '.join(m.strip() for m in msg[:6]) or f'exit {proc.returncode}'}")


# ----------------------------------------------------------------------------------------------- voices

_VOICES: list[dict] | None = None


def voices(refresh: bool = False) -> list[dict]:
    """Installed Windows voices: [{'name', 'engine' ('sapi' | 'onecore'), 'language', 'gender', 'age',
    'default'}]; empty on other systems. Cached per process (refresh=True asks Windows again)."""
    global _VOICES
    if _VOICES is not None and not refresh:
        return [dict(v) for v in _VOICES]
    if os.name != 'nt' or shutil.which(_POWERSHELL) is None:
        _VOICES = []
        return []
    with tempfile.TemporaryDirectory(prefix='agentsound_tts_') as tmp:
        out = os.path.join(tmp, 'voices.json')
        _run_ps(_PS_VOICES, out, 'voices()')
        try:
            data = json.loads(Path(out).read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as e:
            raise SpeechError(f"voices(): unreadable answer from PowerShell ({e})") from None
    if isinstance(data, dict):
        data = [data]
    _VOICES = [{'name': str(v.get('name', '')), 'engine': str(v.get('engine', '')), 'language': str(v.get('language', '')),
                'gender': str(v.get('gender', '')), 'age': str(v.get('age', '')), 'default': bool(v.get('default'))}
               for v in data if v.get('name')]
    return [dict(v) for v in _VOICES]


def find_voice(name: str | None, installed: list[dict] | None = None) -> dict | None:
    """The installed voice a name means: 'Microsoft Zira Desktop', 'zira', 'onecore:Hedda', 'sapi:hedda'
    (case-insensitive; a unique substring is enough; with both engines the OneCore voice wins unless the name
    says 'desktop' or 'sapi:'). None -> None (the Windows default SAPI voice)."""
    if name is None:
        return None
    if not isinstance(name, str) or not name.strip():
        raise SpeechError(f"voice must be a voice name like 'zira' or 'Microsoft Zira Desktop', got {name!r}")
    vs = voices() if installed is None else installed
    engine, _, want = name.strip().rpartition(':')
    engine = engine.lower()
    if engine and engine not in ('sapi', 'onecore'):
        raise SpeechError(f"voice {name!r}: the engine prefix must be 'sapi:' or 'onecore:'")
    pool = [v for v in vs if not engine or v['engine'] == engine]
    w = want.lower()
    exact = [v for v in pool if v['name'].lower() == w]
    hits = exact or [v for v in pool if w in v['name'].lower()]
    if len(hits) > 1 and not engine:
        prefer = 'sapi' if 'desktop' in w else 'onecore'
        hits = [v for v in hits if v['engine'] == prefer] or hits
    if len(hits) == 1:
        return dict(hits[0])
    listing = ', '.join(f"{v['engine']}:{v['name']} ({v['language']})" for v in vs) or 'none (not Windows?)'
    if not hits:
        raise SpeechError(f"no installed voice matches {name!r}; installed: {listing}")
    raise SpeechError(f"voice {name!r} is ambiguous ({', '.join(v['name'] for v in hits)}); installed: {listing}")


# ------------------------------------------------------------------------------------------------ speak

def _caller_dir() -> Path:
    """Folder of the first calling file outside the agentsound package (the song), else the working directory."""
    here = os.path.dirname(os.path.abspath(__file__))
    f = sys._getframe(1)
    while f is not None:
        fn = f.f_globals.get('__file__')
        if fn and os.path.dirname(os.path.abspath(fn)) != here:
            return Path(fn).resolve().parent
        f = f.f_back
    return Path.cwd()


def _slug(text: str) -> str:
    s = re.sub(r'<[^>]*>', ' ', text)
    return (re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_') or 'speech')[:32].strip('_')


def _num(x, what: str, lo: float, hi: float) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not lo <= x <= hi:
        raise SpeechError(f"{what} must be a number in {lo:g}..{hi:g}, got {x!r}")
    return float(x)


def speak(text: str, path=None, voice: str | None = None, rate: float = 0, volume: float = 100, ssml=None, *,
          cache_dir=None) -> Path:
    """Render `text` with a Windows voice to a WAV and return its path.

    voice: a name for find_voice() ('zira', 'onecore:Stefan', ...; None = the Windows default voice).
    rate: -10 (slow) .. 10 (fast), 0 = normal.  volume: 0..100 (before the level normalisation: shapes the voice
    a little on some engines, mostly irrelevant).  ssml: True = `text` is SSML (<speak ...> ... </speak>), or an
    SSML string to speak instead of `text` (`text` then only names the file).
    The result is trimmed, normalised to LEVEL_DBFS and cached (cache_dir, default <song folder>/samples/speech/);
    path= also copies it there. Cached results need no Windows."""
    if not isinstance(text, str) or not text.strip():
        raise SpeechError(f"speak(): text must be a non-empty string, got {text!r}")
    rate = _num(rate, 'speak(): rate', -10, 10)
    volume = _num(volume, 'speak(): volume', 0, 100)
    if ssml is not None and not isinstance(ssml, (bool, str)):
        raise SpeechError(f"speak(): ssml must be True / False or an SSML string, got {ssml!r}")
    spoken = ssml if isinstance(ssml, str) else text
    is_ssml = bool(ssml)
    key = json.dumps({'format': _FORMAT, 'text': spoken, 'ssml': is_ssml, 'voice': voice or '', 'rate': rate,
                      'volume': volume, 'level': LEVEL_DBFS}, sort_keys=True)
    digest = hashlib.sha1(key.encode('utf-8')).hexdigest()[:10]
    folder = Path(cache_dir) if cache_dir is not None else _caller_dir() / 'samples' / 'speech'
    cached = folder / f"{_slug(text)}-{digest}.wav"
    if not cached.is_file():
        _synthesize(spoken, is_ssml, voice, rate, volume, cached)
    if path is None:
        return cached
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.resolve() != cached.resolve():
        shutil.copyfile(cached, out)
    return out


def _synthesize(spoken: str, is_ssml: bool, voice, rate: float, volume: float, dest: Path) -> None:
    what = f"speak({spoken[:40]!r})"
    v = find_voice(voice) if voice is not None else None
    if is_ssml and '<speak' not in spoken:  # an SSML fragment: wrap it in the voice's language (else it may switch)
        lang = (v or {}).get('language') or 'en-US'
        spoken = (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang}">'
                  f"{spoken}</speak>")
    req = {'engine': v['engine'] if v else 'sapi', 'voice': v['name'] if v else '', 'text': spoken, 'ssml': is_ssml,
           'rate': int(round(rate)), 'volume': int(round(volume)),
           'speakingRate': max(0.5, min(6.0, 3.0 ** (rate / 10.0))), 'audioVolume': volume / 100.0}
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='agentsound_tts_') as tmp:
        raw = os.path.join(tmp, 'raw.wav')
        req['out'] = raw
        rq = os.path.join(tmp, 'request.json')
        Path(rq).write_text(json.dumps(req), encoding='utf-8')
        _run_ps(_PS_SPEAK, rq, what)
        if not os.path.isfile(raw):
            raise SpeechError(f"{what}: the synthesiser wrote no audio")
        part = dest.with_name(f"{dest.name}.{os.getpid()}.part")   # (atomic: parallel builds never see half a file)
        _process(raw, part, what)
        os.replace(part, dest)


# --------------------------------------------------------------------------------------- WAV processing

def _read_pcm16(path) -> tuple[list[float], int]:
    with wave.open(str(path), 'rb') as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        raise SpeechError(f"{path}: expected 16-bit PCM from the synthesiser, got {8 * sw}-bit")
    a = array.array('h')
    a.frombytes(raw)
    if sys.byteorder == 'big':
        a.byteswap()
    if ch == 1:
        return [v / 32768.0 for v in a], sr
    return [sum(a[i:i + ch]) / (32768.0 * ch) for i in range(0, len(a), ch)], sr


def _write_pcm16(path, x: list[float], sr: int) -> None:
    a = array.array('h', (max(-32767, min(32767, int(round(v * 32767.0)))) for v in x))
    if sys.byteorder == 'big':
        a.byteswap()
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(a.tobytes())


def _process(src, dst, what: str) -> None:
    """Trim the silence around the speech (keeping _PRE_MS / _POST_MS, short fades) and normalise the active
    speech level (RMS of the 20 ms frames within 35 dB of the loudest) to LEVEL_DBFS, peaks <= -1 dBFS."""
    x, sr = _read_pcm16(src)
    if not x:
        raise SpeechError(f"{what}: the synthesiser returned no samples")
    win = max(1, int(0.01 * sr))
    energy = [sum(v * v for v in x[i:i + win]) / win for i in range(0, len(x), win)]
    top = max(energy)
    if top <= 1e-12:
        raise SpeechError(f"{what}: the synthesiser returned silence")
    thr = top * 10 ** (_TRIM_DB / 10)
    loud = [k for k, e in enumerate(energy) if e > thr]
    a = max(0, loud[0] * win - int(_PRE_MS * 0.001 * sr))
    b = min(len(x), (loud[-1] + 1) * win + int(_POST_MS * 0.001 * sr))
    y = x[a:b]
    fade = max(1, int(_FADE_MS * 0.001 * sr))
    for i in range(min(fade, len(y))):
        g = i / fade
        y[i] *= g
        y[-1 - i] *= g
    fl = max(1, int(0.02 * sr))
    frames = [sum(v * v for v in y[i:i + fl]) / fl for i in range(0, max(1, len(y) - fl + 1), fl)] or [top]
    mx = max(frames)
    active = [f for f in frames if f > mx * 10 ** -3.5]
    level = math.sqrt(sum(active) / len(active))
    peak = max(abs(v) for v in y)
    gain = min(10 ** (LEVEL_DBFS / 20) / level, 10 ** (-1 / 20) / max(peak, 1e-9))
    _write_pcm16(dst, [v * gain for v in y], sr)


def wav_seconds(path) -> float:
    """Length of a WAV file in seconds."""
    with wave.open(str(path), 'rb') as w:
        return w.getnframes() / float(w.getframerate())


# ------------------------------------------------------------------------------------------ samplers

def _midi(x, what: str) -> int:
    try:
        n = note(x) if isinstance(x, str) else x
    except ComposeError as e:
        raise SpeechError(f"{what}: {e}") from None
    if isinstance(n, bool) or not isinstance(n, (int, float)) or not 0 <= n <= 127 or int(n) != n:
        raise SpeechError(f"{what} must be a MIDI note 0..127 or a note name like 'C2', got {x!r}")
    return int(n)


def _zone_path(p: Path) -> str:
    return str(Path(p).resolve()).replace(os.sep, '/')


def phrase(text: str, root='C4', *, voice=None, rate: float = 0, volume: float = 100, ssml=None, cache_dir=None,
           key=None) -> dict:
    """A sampler zone that plays one spoken phrase on one key (default: its root C4, at the original pitch):
        s.track('voice', inst.sampler(zones=[speech.phrase('midnight drive')], oneshot='on'))
    key= maps it to another key than the root (the pitch is still the original one)."""
    r = _midi(root, 'phrase(): root')
    k = r if key is None else _midi(key, 'phrase(): key')
    f = speak(text, voice=voice, rate=rate, volume=volume, ssml=ssml,
              cache_dir=cache_dir if cache_dir is not None else _caller_dir() / 'samples' / 'speech')
    return {'file': _zone_path(f), 'root': k, 'lo': k, 'hi': k}


class Words:
    """A speech sampler: every word / phrase is a TTS WAV on its own key (root, root + 1, ...), one-shot.

        vox = speech.words(['neon lights', 'city nights'], voice='zira')
        vox['city nights']            -> 37 (its MIDI key)
        vox.seconds['neon lights']    -> its length in seconds
        vox.instrument(level=-2)      -> inst.sampler(zones=..., oneshot='on', level=-2)
        vox.clip({0: 'neon lights', 2: 'city nights'}, length=4)   -> a Clip for track.play()"""

    def __init__(self, items, *, voice=None, rate: float = 0, volume: float = 100, root='C2', cache_dir=None):
        if isinstance(items, str):
            items = [items]
        items = list(items)
        if not items or not all(isinstance(t, str) and t.strip() for t in items):
            raise SpeechError(f"words(): give a list of non-empty strings, got {items!r}")
        if len(set(items)) != len(items):
            raise SpeechError(f"words(): duplicate entries in {items!r}")
        self.root = _midi(root, 'words(): root')
        if self.root + len(items) > 128:
            raise SpeechError(f"words(): {len(items)} words from key {self.root} do not fit below 128; lower root=")
        folder = Path(cache_dir) if cache_dir is not None else _caller_dir() / 'samples' / 'speech'
        self.words = items
        self.voice = voice
        self.files = {t: speak(t, voice=voice, rate=rate, volume=volume, cache_dir=folder) for t in items}
        self.keys = {t: self.root + i for i, t in enumerate(items)}
        self.seconds = {t: wav_seconds(f) for t, f in self.files.items()}

    def __getitem__(self, word: str) -> int:
        if word not in self.keys:
            raise SpeechError(f"no word {word!r} in this sampler (words: {', '.join(map(repr, self.words))})")
        return self.keys[word]

    def zones(self) -> list[dict]:
        return [{'file': _zone_path(self.files[t]), 'root': k, 'lo': k, 'hi': k} for t, k in self.keys.items()]

    def instrument(self, **params) -> Instrument:
        """The sampler (one-shot: each note plays its whole word; extra params go to the sampler)."""
        return inst.sampler(zones=self.zones(), **{'oneshot': 'on', **params})

    def beats(self, word: str, tempo: float) -> float:
        """Length of a word in beats at `tempo` BPM."""
        self[word]  # (validates the word)
        return self.seconds[word] * float(tempo) / 60.0

    def clip(self, events, length=None, vel: int = 127, tempo: float | None = None) -> Clip:
        """A Clip that fires words: events = {beat: word} or [(beat, word), (beat, word, vel), ...]. Note lengths
        are the words' lengths in beats when tempo= is given, else 1 beat (one-shot: the length does not cut).
        Velocity 127 plays the word at its calibrated level (-18 dBFS); lower velocities make the robot quieter
        (the sampler's velsens: 100 = -4 dB)."""
        items = sorted(events.items()) if isinstance(events, dict) else list(events)
        notes = []
        for ev in items:
            if not isinstance(ev, (tuple, list)) or len(ev) not in (2, 3):
                raise SpeechError(f"clip(): events are (beat, word) or (beat, word, vel), got {ev!r}")
            beat, word = ev[0], ev[1]
            v = ev[2] if len(ev) == 3 else vel
            dur = self.beats(word, tempo) if tempo else 1.0
            notes.append((beat, max(dur, 0.0625), self[word], v))
        return Clip(notes, length=length)


def words(items, *, voice=None, rate: float = 0, volume: float = 100, root='C2', cache_dir=None) -> Words:
    """A word sampler (see Words): each entry of `items` is spoken once and mapped to its own key from root."""
    return Words(items, voice=voice, rate=rate, volume=volume, root=root,
                 cache_dir=cache_dir if cache_dir is not None else _caller_dir() / 'samples' / 'speech')


# --------------------------------------------------------------------------------------------- audition

AUDITION_TEXT = 'Neon lights, city nights. Midnight drive.'


def audition_voice(song, carrier, section, *, cache_dir=None, text: str = AUDITION_TEXT):
    """Key `carrier`'s vocoder with a talking modulator for an audition (`python -m agentsound audition`): `text`
    spoken by the first English Windows voice (else the default voice) on bars 1 and 3 of `section`; without
    text-to-speech a synthetic one (a saw through the 'vowel' filter, morphing on syllables, with breath noise).
    Returns the (muted) voice track."""
    try:
        eng = [v for v in voices() if v['language'].lower().startswith('en')]
        eng.sort(key=lambda v: v['engine'] != 'onecore')
        name = f"{eng[0]['engine']}:{eng[0]['name']}" if eng else None
        zone = phrase(text, 'C4', voice=name, cache_dir=cache_dir)
        voice = song.track('voice', inst.sampler(zones=[zone], oneshot='on'), mute=True)
        for bar in (0, 2):
            voice.note(60, section.bar(bar), 4.0, vel=127)
    except SpeechError:
        from .modulation import lfo
        voice = song.track('voice', inst.va(osc1__wave='saw', noise__level=0.25, noise__color='pink', cutoff=7000,
                                            filter__env=0, amp__attack=0.01, amp__release=0.06),
                           fx=[FX('vowel', {'vowel': 'a', 'resonance': 0.65, 'presence': 0.7})], mute=True)
        voice.modulate('fx.0.morph', lfo('triangle', rate='1/2', min=0, max=4))
        syllables = Clip([(b, 0.35, 48, 115) for b in (0, 0.5, 1, 2, 2.5, 3.5, 4, 4.5, 6, 6.5, 7)], length=8)
        voice.play(syllables, section, times=2)
    vocode(carrier, voice)
    return voice


# ----------------------------------------------------------------------------------------------- vocode

def vocode(carrier, voice, *, mute: bool = True, **params):
    """Key the vocoder(s) in `carrier`'s fx chain with `voice` (the modulator track / bus); without one, append
    fx.vocoder(**params). params also update the existing vocoders (e.g. shift=-4, mode='lpc'). mute=True mutes
    the voice track: it still plays (the renderer runs muted tracks and feeds them to sidechains) but is not heard
    in the mix and not analysed. Returns the carrier."""
    if not hasattr(carrier, 'fx') or not hasattr(carrier, 'id'):
        raise SpeechError(f"vocode(): the carrier must be a track or bus, got {carrier!r}")
    vid = _ref(voice)
    if vid == carrier.id:
        raise SpeechError(f"vocode(): {carrier.id!r} can't be its own modulator")
    hits = [i for i, f in enumerate(carrier.fx) if f.type == 'vocoder']
    if not hits:
        carrier.fx.append(FX('vocoder', params, sidechain=vid))
    for i in hits:
        carrier.fx[i] = carrier.fx[i].but(**params).keyed(vid)
    if mute:
        if not hasattr(voice, 'mute'):
            raise SpeechError(f"vocode(mute=True) needs the voice track object (not its id {vid!r}) to mute it; "
                              f"or create it with mute=True and pass mute=False here")
        voice.mute = True
    return carrier
