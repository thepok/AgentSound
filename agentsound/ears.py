"""The learned ears: how well produced / how mechanical does a render sound to pretrained audio models?

    python -m agentsound ears songs/<slug> [--section] [--ref <audio or dir> ...] [--instrument piano]
    python -m agentsound ears a.wav b.mp3 some/dir/ [--ref refs/] [--out ears.json]

Optional dependency: the models run in a separate venv with torch (README section 6 "The learned ears"), so the
main Python never needs torch. The interpreter is $AGENTSOUND_EARS_PYTHON, else the first existing
DEFAULT_EARS_PYTHONS entry; without one the command says how to install it and exits 3 (nothing else depends on it).

Per file (up to `max_windows` 10 s windows spread over the file, averaged):
  aesthetics   Meta Audiobox Aesthetics (CC-BY-4.0): PQ production quality, PC production complexity,
               CE content enjoyment, CU content usefulness (1..10)
  clap         LAION-CLAP music (laion_clap package + lukewys/laion_clap music_audioset_epoch_15, CC0-1.0)
               zero-shot P(real): prompt pairs "a real recording of a <instrument> ..." vs "a MIDI <instrument> ..."
               (ears_worker.PROMPT_PAIRS); the instrument comes from the song's sampled tracks or --instrument
  refCos       cosine similarity of the file's mean CLAP embedding to the references' (with --ref)
  fad          Frechet distance of all files' CLAP window embeddings vs the references' (with --ref, a set)
  realism      the combined 0..100 score (REALISM below: only the signals that passed calibration)

A song dir writes songs/<slug>/out/ears.json and an `ears` block into out/report.json. The worker
(agentsound/ears_worker.py) runs in the venv; this module only plumbs JSON (and is what the tests cover).
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

ENV_PYTHON = 'AGENTSOUND_EARS_PYTHON'
DEFAULT_EARS_PYTHONS = ('D:/venvs/agentsound-ears/Scripts/python.exe',
                        str(Path.home() / 'venvs' / 'agentsound-ears' / 'Scripts' / 'python.exe'),
                        str(Path.home() / 'venvs' / 'agentsound-ears' / 'bin' / 'python'))
WORKER = Path(__file__).resolve().parent / 'ears_worker.py'
AUDIO_EXT = ('.wav', '.mp3', '.flac', '.ogg', '.opus', '.m4a')
CACHE_VARS = {'HF_HOME': 'hf', 'TORCH_HOME': 'torch', 'XDG_CACHE_HOME': 'xdg', 'PIP_CACHE_DIR': 'pip',
              'TMP': 'tmp', 'TEMP': 'tmp', 'TMPDIR': 'tmp'}

# Combined realism score (0..100): weighted mean of signals mapped to 0..1 by (value - lo) / (hi - lo), clipped.
# Only the signals that passed calibration are in it (README section 6 "The learned ears": the table and the
# verdicts): PQ, CU and P(real) ranked every degraded render (one velocity, 16th grid + one velocity, bitcrush,
# telephone band) below its original on both test songs; CE missed one (and is about the content), PC is
# arrangement density (rises for real band records, falls under bitcrush the wrong way). NONE of them tells a real
# recording from our renders, nor Shinyguitar from FSS: the score finds damage / mechanical playing, not "is it real".
# Ranges span bitcrushed (~6.5 PQ, ~0.4 P(real)) to our best piano (~8.2, ~0.85). Data: re-fit after a new calibration.
REALISM = {
    'PQ':    {'weight': 0.4, 'lo': 6.0, 'hi': 8.5},     # audiobox production quality
    'CU':    {'weight': 0.2, 'lo': 6.5, 'hi': 8.5},     # audiobox content usefulness (tracks PQ, less noisy)
    'pReal': {'weight': 0.4, 'lo': 0.3, 'hi': 0.9},     # CLAP zero-shot P(real recording of <instrument>)
}

# Track id / instrument keywords -> the noun the CLAP prompts use. Only sampled tracks count (a VA / DX7 synth
# is meant to sound synthetic: asking whether it sounds like a real recording judges nothing).
INSTRUMENT_WORDS = (
    ('piano', 'piano'), ('rhodes', 'electric piano'), ('epiano', 'electric piano'), ('guitar', 'guitar'),
    ('gtr', 'guitar'), ('strum', 'guitar'), ('bass', 'bass'), ('drum', 'drum kit'), ('kit', 'drum kit'),
    ('sax', 'saxophone'), ('trumpet', 'trumpet'), ('horn', 'horn section'), ('trombone', 'trombone'),
    ('violin', 'violin'), ('cello', 'cello'), ('strings', 'string orchestra'), ('organ', 'organ'),
    ('flute', 'flute'), ('clarinet', 'clarinet'), ('harp', 'harp'), ('vibes', 'vibraphone'),
)
SAMPLED_TYPES = ('sampler', 'sf2', 'sfz')


class EarsError(Exception):
    """A user-facing problem (bad input); the CLI prints it."""


class EarsUnavailable(EarsError):
    """The ears venv is missing: the CLI prints the install hint and exits 3."""


INSTALL_HINT = (
    "the ears need their own venv with torch (the main Python does not): see README.md 'The learned ears'.\n"
    "  py -3.12 -m venv D:/venvs/agentsound-ears\n"
    "  D:/venvs/agentsound-ears/Scripts/python -m pip install torch torchaudio "
    "--index-url https://download.pytorch.org/whl/cu126\n"
    "  D:/venvs/agentsound-ears/Scripts/python -m pip install audiobox_aesthetics fadtk "
    "--extra-index-url https://download.pytorch.org/whl/cu126\n"
    f"then set {ENV_PYTHON} to its python if it lives elsewhere")


# ------------------------------------------------------------------------------ locating the venv

def find_python(env=None) -> Path:
    """The ears interpreter: $AGENTSOUND_EARS_PYTHON (must exist), else the first existing default."""
    env = os.environ if env is None else env
    explicit = env.get(ENV_PYTHON)
    if explicit:
        p = Path(explicit)
        if not p.is_file():
            raise EarsUnavailable(f"{ENV_PYTHON}={explicit} does not exist; " + INSTALL_HINT)
        return p
    for c in DEFAULT_EARS_PYTHONS:
        if Path(c).is_file():
            return Path(c)
    raise EarsUnavailable("no ears venv found; " + INSTALL_HINT)


def worker_env(py: Path, env=None) -> dict:
    """The worker's environment: model / pip / temp caches under <venv parent>/cache/ (never the system drive's
    profile) unless the caller already set them."""
    env = dict(os.environ if env is None else env)
    venv = py.parent.parent                      # .../agentsound-ears/Scripts/python.exe -> .../agentsound-ears
    cache = Path(env.get('AGENTSOUND_EARS_CACHE') or venv.parent / 'cache')
    if cache.is_dir():
        for var, sub in CACHE_VARS.items():
            env.setdefault(var, str(cache / sub))
    env.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


# ------------------------------------------------------------------------------ inputs

def song_audio(song_dir: Path) -> Path:
    out = song_dir / 'out'
    for name in ('mix.wav', 'mix.mp3'):
        if (out / name).is_file():
            return out / name
    raise EarsError(f"{song_dir} has no out/mix.wav or out/mix.mp3: build it first "
                    f"(python -m agentsound build {song_dir})")


def song_instrument(render_json: Path) -> str | None:
    """The noun for the CLAP prompts from the render's sampled tracks: one instrument -> it, several -> 'band'."""
    if not render_json.is_file():
        return None
    try:
        tracks = json.loads(render_json.read_text(encoding='utf-8')).get('tracks', [])
    except (OSError, ValueError):
        return None
    found = []
    for t in tracks:
        inst = t.get('instrument') or {}
        if inst.get('type') not in SAMPLED_TYPES:
            continue
        samples = (inst.get('params') or {}).get('samples') or [{}]
        noun = None
        for text in (str(t.get('id', '')), str(samples[0].get('file', '')).replace('\\', '/').split('/samples/')[-1]):
            noun = noun or next((n for w, n in INSTRUMENT_WORDS if w in text.lower()), None)   # id, then the pack
        if noun and noun not in found:
            found.append(noun)
    if not found:
        return None
    return found[0] if len(found) == 1 else 'band'


def audio_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob('*') if p.suffix.lower() in AUDIO_EXT and p.is_file())


def collect(paths, section: bool = False, instrument: str | None = None, repo: Path | None = None):
    """Inputs -> (worker file entries, song dirs). A song dir (with song.py) contributes its mix (and with
    section=True one entry per out/report.json section); any other dir all its audio files; a file itself."""
    files, songs = [], []
    for raw in paths:
        p = Path(raw)
        if not p.exists() and repo is not None:
            for c in (repo / raw, repo / 'songs' / raw):
                if c.exists():
                    p = c
                    break
        if not p.exists():
            raise EarsError(f"no such song, file or folder: {raw}")
        if p.is_dir() and (p / 'song.py').is_file():
            mix = song_audio(p)
            inst = instrument or song_instrument(p / 'out' / 'song.render.json')
            songs.append(p)
            base = {'path': str(mix), 'instrument': inst, 'song': str(p)}
            files.append({**base, 'id': p.name, 'start': None, 'end': None})
            if section:
                rep = p / 'out' / 'report.json'
                secs = json.loads(rep.read_text(encoding='utf-8')).get('sections', []) if rep.is_file() else []
                for i, s in enumerate(secs, 1):
                    if s.get('endSec', 0) - s.get('startSec', 0) >= 3.0:
                        files.append({**base, 'id': f"{p.name}:{i:02d}_{s['name']}", 'section': s['name'],
                                      'start': s['startSec'], 'end': s['endSec']})
            continue
        found = audio_files(p)
        if not found:
            raise EarsError(f"{p} holds no audio files ({', '.join(AUDIO_EXT)})")
        for f in found:
            name = f.parent.name if f.stem == 'mix' else f.stem       # .../<slug>/out/mix.wav, .../<tune>/mix.mp3
            if name == 'out':
                name = f.parent.parent.name
            files.append({'id': name, 'path': str(f), 'start': None, 'end': None,       # a render: its own tracks
                          'instrument': instrument or song_instrument(f.parent / 'song.render.json')})
    seen = {}
    for f in files:                                                  # ids key the results: keep them unique
        n = seen[f['id']] = seen.get(f['id'], 0) + 1
        if n > 1:
            f['id'] = f"{f['id']}#{n}"
    return files, songs


# ------------------------------------------------------------------------------ the combined score

def realism(row: dict, table=None) -> float | None:
    """0..100 from the signals REALISM weighs (None when none of them is present)."""
    table = REALISM if table is None else table
    vals = {**(row.get('aesthetics') or {}), 'pReal': (row.get('clap') or {}).get('pReal')}
    total = wsum = 0.0
    for k, spec in table.items():
        v = vals.get(k)
        if v is None:
            continue
        x = min(1.0, max(0.0, (float(v) - spec['lo']) / (spec['hi'] - spec['lo'])))
        total += spec['weight'] * x
        wsum += spec['weight']
    return round(100.0 * total / wsum, 1) if wsum else None


def summary_lines(resp: dict) -> list[str]:
    lines = []
    for r in resp.get('files', []):
        a = r.get('aesthetics') or {}
        c = r.get('clap') or {}
        s = (f"{r['id']}: realism {r.get('realism')}  |  PQ {a.get('PQ')} PC {a.get('PC')} CE {a.get('CE')} "
             f"CU {a.get('CU')}  |  P(real {c.get('instrument')}) {c.get('pReal')}")
        if 'refCos' in r:
            s += f"  |  refCos {r['refCos']}"
        lines.append(s)
    if resp.get('fad') is not None:
        lines.append(f"FAD (CLAP) vs refs: {resp['fad']}")
    return lines


# ------------------------------------------------------------------------------ running

def run_worker(request: dict, py: Path | None = None, timeout: float = 3600) -> dict:
    py = py or find_python()
    with tempfile.TemporaryDirectory(prefix='ears-') as td:
        req, resp = Path(td) / 'request.json', Path(td) / 'response.json'
        req.write_text(json.dumps(request), encoding='utf-8')
        p = subprocess.run([str(py), '-I', str(WORKER), str(req), str(resp)], env=worker_env(py),
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        if not resp.is_file():
            tail = (p.stderr or p.stdout or '').strip().splitlines()[-8:]
            raise EarsUnavailable(f"the ears worker failed (exit {p.returncode}) with {py}:\n  " + '\n  '.join(tail)
                                  + "\n" + INSTALL_HINT)
        out = json.loads(resp.read_text(encoding='utf-8'))
    if not out.get('ok'):
        raise EarsError(f"the ears worker failed: {out.get('error')}")
    return out


def attach(resp: dict, files: list[dict]) -> dict:
    """Adds realism + the song / section of each request entry to the worker's rows."""
    meta = {f['id']: f for f in files}
    for r in resp.get('files', []):
        r['realism'] = realism(r)
        m = meta.get(r['id'], {})
        for k in ('song', 'section'):
            if m.get(k):
                r[k] = m[k]
    resp['realismTable'] = REALISM
    return resp


def write_song_outputs(resp: dict, songs: list[Path]) -> list[Path]:
    """out/ears.json per song (its rows only) and the `ears` block of out/report.json."""
    written = []
    for song in songs:
        rows = [r for r in resp.get('files', []) if r.get('song') == str(song)]
        if not rows:
            continue
        data = {k: v for k, v in resp.items() if k != 'files'}
        data['files'] = rows
        out = song / 'out' / 'ears.json'
        out.write_text(json.dumps(data, indent=1), encoding='utf-8')
        written.append(out)
        rep = song / 'out' / 'report.json'
        if rep.is_file():
            report = json.loads(rep.read_text(encoding='utf-8'))
            whole = next((r for r in rows if not r.get('section')), rows[0])
            report['ears'] = {'realism': whole.get('realism'), 'aesthetics': whole.get('aesthetics'),
                              'pReal': (whole.get('clap') or {}).get('pReal'),
                              'instrument': (whole.get('clap') or {}).get('instrument'),
                              'refCos': whole.get('refCos'), 'fad': resp.get('fad'),
                              'sections': [{'name': r['section'], 'realism': r.get('realism')}
                                           for r in rows if r.get('section')],
                              'file': 'ears.json'}
            rep.write_text(json.dumps(report, indent=1), encoding='utf-8')
    return written


def run(paths, refs=(), section=False, instrument=None, ffmpeg=None, out=None, repo=None, max_windows=12,
        device='auto', py=None) -> dict:
    if not ffmpeg:
        raise EarsError("ears needs ffmpeg to decode audio (PATH or C:/Program Files (x86)/ffmpeg/bin)")
    py = py or find_python()                     # fail fast, before any decoding
    files, songs = collect(paths, section=section, instrument=instrument, repo=repo)
    ref_files = []
    for r in refs:
        rp = Path(r)
        if not rp.exists():
            raise EarsError(f"no such reference: {r}")
        ref_files += [{'path': str(f)} for f in audio_files(rp)]
    request = {'files': files, 'refs': ref_files, 'ffmpeg': ffmpeg, 'window': 10.0, 'max_windows': max_windows,
               'device': device, 'fad': bool(ref_files)}
    resp = attach(run_worker(request, py=py), files)
    resp['written'] = [str(p) for p in write_song_outputs(resp, songs)]
    if out:
        Path(out).write_text(json.dumps(resp, indent=1), encoding='utf-8')
        resp['written'].append(str(out))
    return resp
