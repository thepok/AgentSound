"""The voice-over: every script line spoken by a TTS backend, cached, loudness-matched per speaker.

Backends
- breeze: Breeze TTS 2 (local, WSL + GPU; research / non-commercial licence - fine for private use, named in the
  credits). One frozen voice per role (a reference WAV + its exact transcript + a stable identity instruction +
  cfg 4 + a fixed seed: the approved narrator of the local installation, a second approved voice for the A&R), a
  short delivery direction per line. Talks to its HTTP API (POST /v1/audio/speech); starts it in WSL when it is not
  running (only when the GPU is free) and stops it again afterwards.
- sapi: the Windows voices of agentsound.speech (always there on Windows; plain but instant).
- none: captions only (line lengths estimated).

Caching: one raw PCM file per line, keyed by a hash of text + voice + instruction + seed + cfg + reference: a
changed line is the only one synthesised again; a stopped run resumes. Raw files are never modified.
Loudness (the radio-play rule): every raw chunk is measured (EBU R128, ffmpeg), each speaker gets ONE fixed gain
from the median of its chunks to TARGET_LUFS; a chunk's gain is only lowered when its peak would pass the ceiling -
whispers stay quiet, emphasis stays loud."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import time
import urllib.error
import urllib.request
import wave
from array import array
from pathlib import Path

TARGET_LUFS = -18.0          # speech over music (the song itself plays at its master level)
PEAK_CEILING_DB = -1.5
# the Breeze TTS installation inside WSL; a leading '~' is the WSL user's home (expanded inside WSL, see breeze_dir())
BREEZE_DIR = os.environ.get('AGENTSOUND_BREEZE_DIR', '~/services/breeze-tts')
BREEZE_DISTRO = os.environ.get('AGENTSOUND_BREEZE_DISTRO', 'Ubuntu')
BREEZE_URL = os.environ.get('AGENTSOUND_BREEZE_URL', 'http://127.0.0.1:7860')

# role -> the installation's approved voice folder (voices/<...>/voice.json + reference.wav)
BREEZE_CAST = {
    'narrator': 'other-newspaper-approved/narrator',
    'ar': 'other-newspaper-approved/mara',
}


class NarrationError(RuntimeError):
    pass


# --------------------------------------------------------------------------------------------- wav helpers

def read_pcm16(path: Path) -> tuple[array, int, int]:
    with wave.open(str(path), 'rb') as w:
        if w.getsampwidth() != 2:
            raise NarrationError(f"{path}: 16-bit PCM expected")
        a = array('h')
        a.frombytes(w.readframes(w.getnframes()))
        return a, w.getframerate(), w.getnchannels()


def write_pcm16(path: Path, samples: array, sr: int, channels: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(samples.tobytes())


def trim_silence(a: array, sr: int, floor_db: float = -45.0, pad: float = 0.04) -> array:
    """Leading / trailing silence under floor_db (a 10 ms window) cut away, `pad` s kept."""
    if not a:
        return a
    thr = 32768 * 10 ** (floor_db / 20)
    win = max(1, sr // 100)
    n = len(a)
    first = next((i for i in range(0, n, win) if max(abs(x) for x in a[i:i + win]) > thr), 0)
    last = next((i for i in range(n - win, -1, -win) if max(abs(x) for x in a[max(0, i):i + win]) > thr), n - win)
    lo = max(0, first - int(pad * sr))
    hi = min(n, last + win + int(pad * sr))
    return a[lo:hi]


def peak_db(a: array) -> float:
    p = max((abs(x) for x in a), default=0)
    return 20 * math.log10(p / 32768) if p else -120.0


def measure_lufs(path: Path, ffmpeg: str) -> float:
    """Integrated loudness (EBU R128) of a file via ffmpeg's ebur128 filter."""
    r = subprocess.run([ffmpeg, '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128=framelog=quiet',
                        '-f', 'null', '-'], capture_output=True, text=True, errors='replace')
    m = re.findall(r'I:\s*(-?[\d.]+|-inf)\s*LUFS', r.stderr)
    if not m:
        raise NarrationError(f"could not measure {path}: {r.stderr[-300:]}")
    return -70.0 if m[-1] == '-inf' else float(m[-1])


def apply_gain(a: array, gain_db: float) -> array:
    k = 10 ** (gain_db / 20)
    out = array('h', (max(-32768, min(32767, int(round(x * k)))) for x in a))
    return out


# --------------------------------------------------------------------------------------------- breeze

def _wsl(*cmd: str, input_bytes: bytes | None = None, timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(['wsl.exe', '-d', BREEZE_DISTRO, '--', *cmd], input=input_bytes, capture_output=True,
                          timeout=timeout)


_BREEZE_DIR_RESOLVED: str | None = None


def breeze_dir() -> str:
    """BREEZE_DIR as an absolute WSL path: a leading '~' becomes the WSL user's $HOME (asked once, then cached)."""
    global _BREEZE_DIR_RESOLVED
    if _BREEZE_DIR_RESOLVED is None:
        d = BREEZE_DIR
        if d == '~' or d.startswith('~/'):
            try:
                r = _wsl('sh', '-c', 'printf %s "$HOME"', timeout=30)
                home = r.stdout.decode('utf-8', errors='replace').strip() if r.returncode == 0 else ''
            except (OSError, subprocess.TimeoutExpired):
                home = ''
            if not home:
                return d          # WSL not reachable: callers fail with their own message
            d = home + d[1:]
        _BREEZE_DIR_RESOLVED = d
    return _BREEZE_DIR_RESOLVED


def _health(url: str = BREEZE_URL, timeout: float = 3) -> bool:
    try:
        with urllib.request.urlopen(url.rstrip('/') + '/health', timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8')).get('status') == 'ok'
    except (urllib.error.URLError, OSError, ValueError):
        return False


def breeze_installed() -> bool:
    if shutil.which('wsl.exe') is None:
        return False
    try:
        r = _wsl('test', '-f', f'{breeze_dir()}/app/breeze_infer/api.py', timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


def gpu_busy_mb() -> int:
    """MiB of GPU memory held by compute processes (nvidia-smi), 0 if none / unknown."""
    exe = shutil.which('nvidia-smi')
    if not exe:
        return 0
    try:
        r = subprocess.run([exe, '--query-compute-apps=used_memory', '--format=csv,noheader,nounits'],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return 0
    return sum(int(x) for x in re.findall(r'\d+', r.stdout))


class Breeze:
    """The Breeze TTS 2 client: a frozen cast in <cache>/cast/, raw PCM per line in <cache>/raw/."""

    name = 'breeze'
    credit = 'Narration: Breeze TTS 2 (local; research / non-commercial licence)'

    def __init__(self, cache: Path, log=print):
        self.cache = Path(cache)
        self.log = log
        self.started = None
        self.cast = self._freeze_cast()

    def _freeze_cast(self) -> dict:
        """Copy each role's approved voice (reference WAV + transcript + instruction + cfg + seed) into the cache
        once: cast.json there is the frozen cast every later render uses."""
        cdir = self.cache / 'cast'
        cfile = cdir / 'cast.json'
        if cfile.is_file():
            cast = json.loads(cfile.read_text(encoding='utf-8'))
            if all(k in cast and Path(cast[k]['reference_wav']).is_file() for k in BREEZE_CAST):
                return cast
        cdir.mkdir(parents=True, exist_ok=True)
        cast = {}
        for role, folder in BREEZE_CAST.items():
            base = f'{breeze_dir()}/voices/{folder}'
            r = _wsl('cat', f'{base}/voice.json')
            if r.returncode != 0:
                raise NarrationError(f"breeze voice {folder!r} not found: {r.stderr.decode(errors='replace')[:200]}")
            meta = json.loads(r.stdout.decode('utf-8'))
            w = _wsl('cat', f'{base}/reference.wav', timeout=120)
            if w.returncode != 0 or len(w.stdout) < 1000:
                raise NarrationError(f"breeze voice {folder!r}: no reference.wav")
            wav = cdir / f'{role}.wav'
            wav.write_bytes(w.stdout)
            cast[role] = {'source': f'{base}', 'name': meta.get('name', role), 'reference_wav': str(wav),
                          'reference_text': meta['reference_text'],
                          'instruction': meta.get('instruction') or meta.get('design_instruction', ''),
                          'cfg_scale': float(meta.get('cfg_scale', 4)), 'seed': int(meta.get('seed', 42)),
                          'sha256': hashlib.sha256(w.stdout).hexdigest()}
        cfile.write_text(json.dumps(cast, indent=2), encoding='utf-8')
        return cast

    # ---- the API
    def ensure_api(self, wait: float = 420) -> None:
        if _health():
            return
        busy = gpu_busy_mb()
        if busy > 1500:
            raise NarrationError(f"the GPU is busy ({busy} MiB held by other processes): not starting Breeze")
        self.log(f"narration: starting the Breeze API in WSL ({breeze_dir()}) ...")
        cmd = (f"cd {breeze_dir()}/app && exec .venv/bin/python -m breeze_infer.api ../model --host 127.0.0.1 "
               f"--port {BREEZE_URL.rsplit(':', 1)[-1].strip('/')}")
        self.started = subprocess.Popen(['wsl.exe', '-d', BREEZE_DISTRO, '--', 'bash', '-lc', cmd],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0 = time.time()
        while time.time() - t0 < wait:
            if self.started.poll() is not None:
                raise NarrationError("the Breeze API exited while starting")
            if _health():
                self.log(f"narration: Breeze API up after {time.time() - t0:.0f} s")
                return
            time.sleep(3)
        raise NarrationError("the Breeze API did not come up")

    def stop(self) -> None:
        """Stop the API if this run started it (never one that was already running)."""
        if self.started is None:
            return
        try:
            _wsl('pkill', '-f', 'breeze_infer.api ../model --host 127.0.0.1', timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            pass
        try:
            self.started.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.started.kill()
        self.started = None

    # ---- one line
    def fingerprint(self, text: str, voice: str, direction: str) -> tuple[str, dict]:
        v = self.cast[voice]
        instruction = v['instruction'] + (f" Delivery for this passage: {direction}" if direction else '')
        seed = v['seed'] + int(hashlib.sha1(text.encode('utf-8')).hexdigest(), 16) % 97
        req = {'text': text, 'instruction': instruction, 'cfg_scale': v['cfg_scale'], 'seed': seed,
               'ref_text': v['reference_text'], 'ref_sha256': v['sha256'], 'voice': voice}
        fp = hashlib.sha256(json.dumps(req, sort_keys=True).encode('utf-8')).hexdigest()[:24]
        return fp, req

    def raw(self, text: str, voice: str, direction: str) -> Path:
        """The cached raw 24 kHz mono PCM16 WAV of a line (synthesised when missing)."""
        fp, req = self.fingerprint(text, voice, direction)
        out = self.cache / 'raw' / f'{voice}-{fp}.wav'
        if out.is_file():
            return out
        self.ensure_api()
        v = self.cast[voice]
        boundary = '----agentsound' + fp
        parts = []
        for k in ('text', 'instruction', 'ref_text'):
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{req[k]}\r\n'
                         .encode('utf-8'))
        for k in ('cfg_scale', 'seed'):
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{req[k]}\r\n'
                         .encode('utf-8'))
        ref = Path(v['reference_wav']).read_bytes()
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="ref_audio"; filename="reference.wav"'
                     f'\r\nContent-Type: audio/wav\r\n\r\n'.encode('utf-8') + ref + b'\r\n')
        parts.append(f'--{boundary}--\r\n'.encode('utf-8'))
        body = b''.join(parts)
        http = urllib.request.Request(BREEZE_URL.rstrip('/') + '/v1/audio/speech', data=body, method='POST',
                                      headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
        t0 = time.time()
        for attempt in range(40):
            try:
                with urllib.request.urlopen(http, timeout=1800) as r:
                    sr = int(r.headers.get('X-Sample-Rate', '24000'))
                    pcm = r.read()
                break
            except urllib.error.HTTPError as e:
                if e.code == 409:                  # another request is running: wait for it
                    time.sleep(5)
                    continue
                raise NarrationError(f"Breeze: HTTP {e.code}: {e.read()[:300]!r}") from None
        else:
            raise NarrationError("Breeze stayed busy")
        a = array('h')
        a.frombytes(pcm[:len(pcm) // 2 * 2])
        tmp = out.with_suffix('.part')
        write_pcm16(tmp, a, sr)
        tmp.replace(out)
        (out.with_suffix('.json')).write_text(json.dumps({**req, 'sample_rate': sr, 'seconds': len(a) / sr,
                                                          'generation_s': round(time.time() - t0, 1)}, indent=1),
                                              encoding='utf-8')
        self.log(f"narration: {voice} {len(a) / sr:.1f} s in {time.time() - t0:.0f} s: {text[:60]}")
        return out


class Sapi:
    """Windows voices (agentsound.speech): the fallback."""

    name = 'sapi'
    credit = 'Narration: Windows text-to-speech'

    def __init__(self, cache: Path, log=print):
        from .. import speech
        self.speech = speech
        self.cache = Path(cache)
        self.log = log
        vs = [v for v in speech.voices() if str(v.get('culture', v.get('language', ''))).lower().startswith('en')]
        if not vs:
            raise NarrationError("no English Windows voice installed")
        self.voices = {'narrator': vs[0]['name'], 'ar': (vs[1] if len(vs) > 1 else vs[0])['name']}

    def raw(self, text: str, voice: str, direction: str) -> Path:
        fp = hashlib.sha256(f"{voice}|{self.voices[voice]}|{text}".encode('utf-8')).hexdigest()[:24]
        out = self.cache / 'raw' / f'sapi-{voice}-{fp}.wav'
        if not out.is_file():
            out.parent.mkdir(parents=True, exist_ok=True)
            self.speech.speak(text, out, voice=self.voices[voice], rate=-1, cache_dir=self.cache / 'sapi-cache')
        return out

    def ensure_api(self):
        pass

    def stop(self):
        pass


def backend(name: str, cache: Path, log=print):
    """'breeze' | 'sapi' | 'auto' (breeze when installed, else sapi) | 'none' -> a backend or None."""
    if name == 'none':
        return None
    if name in ('breeze', 'auto'):
        try:
            if breeze_installed():
                return Breeze(cache, log)
            if name == 'breeze':
                raise NarrationError(f"Breeze TTS not found in WSL at {breeze_dir()} (set AGENTSOUND_BREEZE_DIR)")
        except NarrationError as e:
            if name == 'breeze':
                raise
            log(f"narration: Breeze unavailable ({e}); using the Windows voices")
    return Sapi(cache, log)


# --------------------------------------------------------------------------------------------- the whole script

def synthesize(lines: list, tts, ffmpeg: str, out_dir: Path, log=print) -> dict:
    """Speak every line (story.Line) -> {id(line): {'wav': processed 48 kHz path, 'seconds': length}}.
    Raw chunks cached by the backend; the processed files (trimmed, one gain per speaker) are rebuilt each run."""
    from .story import speakable
    raws = []
    try:
        for ln in lines:
            raws.append((ln, tts.raw(speakable(ln.text), ln.voice, ln.direction)))
    finally:
        tts.stop()
    # loudness: one gain per speaker from the median of its chunks
    meas: dict[str, list[float]] = {}
    lufs_of = {}
    for ln, p in raws:
        side = p.with_suffix('.lufs')
        if side.is_file():
            v = float(side.read_text())
        else:
            v = measure_lufs(p, ffmpeg)
            side.write_text(str(v))
        lufs_of[p] = v
        meas.setdefault(ln.voice, []).append(v)
    gains = {voice: TARGET_LUFS - statistics.median(vals) for voice, vals in meas.items()}
    out_dir.mkdir(parents=True, exist_ok=True)
    res = {}
    for i, (ln, p) in enumerate(raws):
        a, sr, ch = read_pcm16(p)
        if ch != 1:
            a = array('h', a[::ch])
        a = trim_silence(a, sr)
        g = min(gains[ln.voice], PEAK_CEILING_DB - peak_db(a))
        a = apply_gain(a, g)
        dst = out_dir / f'line_{i:03d}.wav'
        write_pcm16(dst, a, sr)
        res[id(ln)] = {'wav': str(dst), 'seconds': len(a) / sr, 'gain_db': round(g, 2), 'raw': str(p),
                       'lufs_raw': lufs_of[p]}
    log(f"narration: {len(raws)} lines, speaker gains " +
        ', '.join(f"{v} {g:+.1f} dB" for v, g in gains.items()))
    return res
