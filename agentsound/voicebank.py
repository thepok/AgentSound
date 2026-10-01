"""Singing voicebanks: the licensed DiffSinger voices a song can sing with, and the WSL backend that renders them.

    from agentsound import voicebank
    voicebank.voices()                        # the manifest (assets/voices/manifest.json) + what is installed
    bank = voicebank.get('hanami')            # a Voicebank: phonemes, modes (core / soft / power), range, credit
    bank.mode('soft')                         # -> 'Nectar' (the bank's own voice-mode embedding)

THE CONSENT RULE (enforced here and in agentsound.singer): AgentSound never clones a real singer. A voice is used
only when its manifest entry says what gives the right to synthesise it - consent = 'licensed' (a voicebank whose
voice provider licensed it for synthesis: Hanami, TIGER), 'synthetic' (a voice that belongs to no person) or 'own'
(the user's own recorded voice). A reference / prompt recording for a zero-shot singer (SoulX-Singer) must be one of
the same: a licensed voicebank's own rendered output, a synthetic voice or the user's own voice - never a recording
of another singer (check_prompt()).

The banks are OpenUtau DiffSinger packages (ONNX: acoustic, duration, pitch models and the bank's own vocoder). They
live in assets/voices/<id>/ ($AGENTSOUND_VOICES overrides the folder, e.g. to share one download between git
worktrees), never in git (their licences forbid redistribution); SOURCE.json next to each one records url, licence and
attribution. The heavy side - numpy + onnxruntime(-gpu) - runs in WSL in its own venv ($AGENTSOUND_SINGING_DIR, default
~/services/singing; agentsound/voicebank_runner/ds_runner.py is the runner, called with a JSON request), the way the
making-of narration drives Breeze TTS: agentsound itself stays stdlib only. run() batches jobs into one WSL call.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .theory import ComposeError, note

__all__ = ['VoicebankError', 'Voicebank', 'voices', 'get', 'voices_dir', 'manifest', 'check_prompt', 'run',
           'wsl_path', 'CONSENT', 'FRAME_HOP', 'runner_ok', 'write_source']

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / 'assets' / 'voices' / 'manifest.json'
RUNNER = Path(__file__).resolve().parent / 'voicebank_runner' / 'ds_runner.py'
SINGING_DIR = os.environ.get('AGENTSOUND_SINGING_DIR', '~/services/singing')
DISTRO = os.environ.get('AGENTSOUND_SINGING_DISTRO', os.environ.get('AGENTSOUND_BREEZE_DISTRO', 'Ubuntu'))
CONSENT = ('licensed', 'synthetic', 'own')
"""What may be synthesised: a licensed voicebank, a synthetic voice, the user's own voice. Never a real singer's
voice cloned from recordings."""
FRAME_HOP = 512
GPU_BUSY_MB = 3000
"""Above this much GPU memory held by other processes (e.g. a Breeze narration) the runner uses the CPU."""


class VoicebankError(ComposeError):
    """A voicebank / backend problem (a ComposeError: the build reports it like any other mistake)."""


def voices_dir() -> Path:
    env = os.environ.get('AGENTSOUND_VOICES')
    return Path(env) if env else REPO / 'assets' / 'voices'


def manifest() -> list[dict]:
    try:
        data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise VoicebankError(f"cannot read {MANIFEST}: {e}") from None
    out = data.get('voices', [])
    for v in out:
        if v.get('consent') not in CONSENT:
            raise VoicebankError(f"voice {v.get('id')!r}: consent must be one of {CONSENT} (the consent rule: no "
                                 f"cloning of real singers), got {v.get('consent')!r}")
    return out


# ------------------------------------------------------------------------------------------- tiny YAML readers

def _yaml_flat(path: Path) -> dict:
    """The block subset of YAML the DiffSinger configs use: nested `key: value` mappings, `- item` lists (also at the
    key's own indent), flow lists `[a, b]`, quoted / plain scalars, comments."""
    rows = []
    for raw in path.read_text(encoding='utf-8', errors='replace').splitlines():
        ln = re.sub(r'\s+#.*$', '', raw) if not raw.lstrip().startswith('#') else ''
        if ln.strip():
            rows.append((len(ln) - len(ln.lstrip()), ln.strip()))

    def block(i: int, ind: int):
        if i < len(rows) and rows[i][1].startswith('- ') or (i < len(rows) and rows[i][1] == '-'):
            out = []
            while i < len(rows) and rows[i][0] == ind and rows[i][1].startswith('-'):
                out.append(_scalar(rows[i][1][1:].strip()))
                i += 1
            return out, i
        out: dict = {}
        while i < len(rows) and rows[i][0] == ind:
            m = re.match(r'^([^:]+?):(?:\s+(.*))?$', rows[i][1])
            if not m:
                i += 1
                continue
            k, v = m.group(1).strip().strip('"\''), (m.group(2) or '').strip()
            i += 1
            if v:
                out[k] = _scalar(v)
            elif i < len(rows) and (rows[i][0] > ind or (rows[i][0] == ind and rows[i][1].startswith('-'))):
                out[k], i = block(i, rows[i][0])
            else:
                out[k] = None
        return out, i

    if not rows:
        return {}
    val, _ = block(0, rows[0][0])
    return val if isinstance(val, dict) else {}


def _scalar(v: str):
    v = v.strip()
    if v.startswith('[') and v.endswith(']'):
        return [_scalar(x) for x in v[1:-1].split(',') if x.strip()]
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    if v in ('true', 'True'):
        return True
    if v in ('false', 'False'):
        return False
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


_ENTRY = re.compile(r'^\s*-\s*\{\s*grapheme:\s*("([^"]*)"|\'([^\']*)\'|([^,]*?))\s*,\s*phonemes:\s*\[([^\]]*)\]\s*\}')


def read_dsdict(path: Path, phones: set | None = None) -> dict:
    """{word: [phonemes]} of a DiffSinger dsdict (its `entries:`); phones: keep only entries made of these
    phonemes (English ARPAbet), else all."""
    out: dict = {}
    if not path.is_file():
        return out
    for ln in path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = _ENTRY.match(ln)
        if not m:
            continue
        g = (m.group(2) if m.group(2) is not None else m.group(3) if m.group(3) is not None else m.group(4)).strip()
        ph = [x.strip().strip('"\'') for x in m.group(5).split(',') if x.strip()]
        if not g or not ph or re.search(r'\(\d+\)$', g):
            continue
        if phones is not None and not all(p in phones for p in ph):
            continue
        out.setdefault(g.lower(), ph)
    return out


# ------------------------------------------------------------------------------------------- a voicebank

class Voicebank:
    """One installed (or known) voicebank: id, entry (its manifest entry), path, phonemes, speakers (voice-mode
    embeddings), modes ({'core', 'soft', 'power'} -> speaker), range (MIDI lo, hi), credit, nc (non-commercial)."""

    def __init__(self, entry: dict):
        self.entry = dict(entry)
        self.id = entry['id']
        self.title = entry.get('title', self.id)
        self.path = voices_dir() / self.id
        self.range = tuple(note(x) for x in entry.get('range', ['C3', 'C6']))
        self.modes = dict(entry.get('modes') or {})
        self.credit = entry.get('credit') or f"Vocals: {self.title}"
        lic = entry.get('license', '')
        self.nc = bool(re.search(r'(^|[-\s])nc([-\s]|$)', lic.lower())) or 'non-commercial' in lic.lower()
        self._cfg = None
        self._phonemes = None
        self._dict = None

    def __repr__(self) -> str:
        return f"Voicebank({self.id!r}, {'installed' if self.installed() else 'not installed'})"

    def installed(self) -> bool:
        return (self.path / 'dsconfig.yaml').is_file()

    def require(self) -> 'Voicebank':
        if not self.installed():
            raise VoicebankError(
                f"voicebank {self.id!r} is not installed in {self.path}: download it from its official source "
                f"({self.entry.get('url') or self.entry.get('page')}), unpack it so that {self.path / 'dsconfig.yaml'} "
                f"exists (see docs/COMPOSE_API.md 'Vocals'), or set AGENTSOUND_VOICES to the folder that holds it")
        return self

    @property
    def config(self) -> dict:
        if self._cfg is None:
            self.require()
            self._cfg = _yaml_flat(self.path / 'dsconfig.yaml')
        return self._cfg

    @property
    def phonemes(self) -> set:
        if self._phonemes is None:
            p = self.path / str(self.config.get('phonemes', 'phonemes.txt'))
            if p.suffix == '.json':
                self._phonemes = set(json.loads(p.read_text(encoding='utf-8')))
            else:
                self._phonemes = {ln.strip() for ln in p.read_text(encoding='utf-8').splitlines() if ln.strip()}
        return self._phonemes

    @property
    def speakers(self) -> list:
        return [str(s).rstrip('/').split('/')[-1] for s in (self.config.get('speakers') or [])]

    @property
    def key_shift_range(self) -> float:
        aug = self.config.get('augmentation_args') or {}
        rng = aug.get('random_pitch_shifting') if isinstance(aug, dict) else None
        try:
            return float(max(abs(x) for x in rng['range'])) if isinstance(rng, dict) else 5.0
        except (KeyError, TypeError, ValueError):
            return 5.0

    def dictionary(self) -> dict:
        """The bank's own English dictionary entries ({word: [phonemes]}, English ARPAbet only)."""
        if self._dict is None:
            from .lyrics import CONSONANTS, VOWELS
            d = self.entry.get('dictionary')
            self._dict = read_dsdict(self.path / d, set(VOWELS) | set(CONSONANTS)) if d and self.installed() else {}
        return self._dict

    def mode(self, name: str) -> str:
        """The speaker embedding for a mode: 'core' / 'soft' / 'power' (the manifest's mapping) or a speaker name
        of the bank itself ('Nectar', 'tiger_glam')."""
        if name in self.modes:
            return self.modes[name]
        if self.installed() and name in self.speakers:
            return name
        names = list(self.modes) + (self.speakers if self.installed() else [])
        raise VoicebankError(f"voicebank {self.id!r} has no mode {name!r}; modes: {', '.join(names)}")

    def check_phonemes(self, phs) -> None:
        bad = sorted({p for p in phs if p not in self.phonemes})
        if bad:
            raise VoicebankError(f"voicebank {self.id!r} has no phoneme(s) {bad}")

    def source(self) -> dict:
        """The SOURCE.json content (url, licence, attribution) for this bank."""
        e = self.entry
        return {'id': self.id, 'kind': 'voice', 'title': self.title, 'url': e.get('url', ''),
                'homepage': e.get('homepage', e.get('page', '')), 'license': e.get('license', 'Unknown'),
                'licenseUrl': e.get('licenseUrl', ''), 'attribution': e.get('attribution', ''),
                'credit': self.credit, 'restrictions': e.get('restrictions', ''), 'consent': e.get('consent'),
                'commercial': e.get('commercial', ''), 'sha256': e.get('sha256', ''), 'size': e.get('size', 0)}


_BANKS: dict = {}


def voices() -> list[dict]:
    """Every voice of the manifest with 'installed' (bool) and 'path'."""
    out = []
    for e in manifest():
        b = get(e['id'])
        out.append({**e, 'installed': b.installed(), 'path': str(b.path)})
    return out


def get(voice) -> Voicebank:
    """A Voicebank by id ('hanami', 'tiger') or the Voicebank itself."""
    if isinstance(voice, Voicebank):
        return voice
    if voice in _BANKS and _BANKS[voice].path == voices_dir() / voice:
        return _BANKS[voice]
    for e in manifest():
        if e['id'] == voice:
            _BANKS[voice] = Voicebank(e)
            return _BANKS[voice]
    ids = ', '.join(e['id'] for e in manifest())
    raise VoicebankError(f"unknown voice {voice!r}; voices: {ids} (assets/voices/manifest.json). Only licensed "
                         f"voicebanks, synthetic voices or your own voice - no cloning of real singers.")


def write_source(bank: Voicebank, folder: Path) -> Path:
    """SOURCE.json of a voice into `folder` (the bank's install folder, or a song's vocal cache: the credits of a
    build find it there)."""
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / 'SOURCE.json'
    data = bank.source()
    try:
        if json.loads(p.read_text(encoding='utf-8')) == data:
            return p
    except (OSError, ValueError):
        pass
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    return p


def check_prompt(path, kind: str, source: str = '') -> dict:
    """The consent rule for a reference / prompt recording (zero-shot singers like SoulX-Singer clone the voice of
    their prompt): kind must be 'licensed-render' (a licensed voicebank's own output, e.g. a Hanami render; source=
    the voicebank id), 'synthetic' or 'own' (the user's own voice). Anything else - a recording of a real singer - is
    refused. Returns {'path', 'kind', 'source'}."""
    kinds = ('licensed-render', 'synthetic', 'own')
    if kind not in kinds:
        raise VoicebankError(f"prompt kind must be one of {kinds}: AgentSound never clones a real singer's voice "
                             f"(got {kind!r} for {path})")
    if kind == 'licensed-render':
        get(source)                       # a voicebank of the manifest (consent: licensed)
    if not Path(path).is_file():
        raise VoicebankError(f"prompt file {path} does not exist")
    return {'path': str(path), 'kind': kind, 'source': source}


# ------------------------------------------------------------------------------------------- the WSL backend

def wsl_path(p) -> str:
    """A Windows path as WSL sees it (D:\\x\\y -> /mnt/d/x/y); POSIX paths pass through."""
    s = str(Path(p).resolve()) if not str(p).startswith('/') else str(p)
    m = re.match(r'^([A-Za-z]):[\\/](.*)$', s)
    if not m:
        return s.replace('\\', '/')
    return f"/mnt/{m.group(1).lower()}/" + m.group(2).replace('\\', '/')


def _wsl(*cmd: str, timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(['wsl.exe', '-d', DISTRO, '--', *cmd], capture_output=True, timeout=timeout)


def _python() -> str:
    d = SINGING_DIR
    if d.startswith('~/'):
        return f"$HOME/{d[2:]}/.venv/bin/python"
    return f"{d}/.venv/bin/python"


def runner_ok() -> tuple[bool, str]:
    """(True, '') when WSL and the singing venv are there; else (False, why)."""
    if shutil.which('wsl.exe') is None:
        return False, "no WSL (wsl.exe) on this machine"
    try:
        r = _wsl('bash', '-c', f'test -x "{_python()}" && echo ok', timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"WSL did not answer ({e})"
    if b'ok' not in r.stdout:
        return False, (f"no singing venv in WSL at {SINGING_DIR}/.venv (install: see docs/COMPOSE_API.md 'Vocals'; "
                       f"AGENTSOUND_SINGING_DIR points elsewhere)")
    return True, ''


PROVIDER = os.environ.get('AGENTSOUND_SINGING_PROVIDER', 'cuda')
"""Where the voicebank runs ($AGENTSOUND_SINGING_PROVIDER): 'cuda' (default: ~3.5x faster; a take rendered again
differs slightly - the diffusion's noise is drawn on the GPU; the CPU is used while other processes hold more than
GPU_BUSY_MB of the GPU) or 'cpu' (bit-reproducible takes: the runner seeds the noise per job, which onnxruntime honours
on the CPU). Either way a song re-renders identically from its cached takes."""


def _provider() -> str:
    if PROVIDER != 'cuda':
        return 'cpu'
    try:
        from .makingof.narration import gpu_busy_mb
        busy = gpu_busy_mb()
    except Exception:  # noqa: BLE001 - unknown: try the GPU, the runner falls back to the CPU itself
        busy = 0
    return 'cpu' if busy > GPU_BUSY_MB else 'cuda'


def run(bank: Voicebank, jobs: list[dict], *, work: Path, log=print, provider: str | None = None,
        timeout: float = 3600) -> list[dict]:
    """Run DiffSinger jobs (see ds_runner.py: info / duration / pitch / sing) for `bank` in ONE WSL call; `work`
    is a folder for the request / response files (a song's vocal cache). Returns the results (each {'ok': ...});
    raises VoicebankError when the backend fails as a whole or any job fails."""
    bank.require()
    if not jobs:
        return []
    ok, why = runner_ok()
    if not ok:
        raise VoicebankError(f"singing backend unavailable: {why}")
    work.mkdir(parents=True, exist_ok=True)
    prov = provider or _provider()
    fd, req = tempfile.mkstemp(prefix='ds_req_', suffix='.json', dir=str(work))
    os.close(fd)
    resp = req[:-5] + '_resp.json'
    Path(req).write_text(json.dumps({'bank': wsl_path(bank.path), 'provider': prov, 'jobs': jobs}), encoding='utf-8')
    t0 = time.time()
    try:
        cmd = f'"{_python()}" "{wsl_path(RUNNER)}" "{wsl_path(req)}" "{wsl_path(resp)}"'
        r = _wsl('bash', '-c', cmd, timeout=timeout)
        if r.returncode != 0 or not Path(resp).is_file():
            err = (r.stderr or b'').decode('utf-8', errors='replace').strip().splitlines()
            err = [x for x in err if 'onnxruntime' not in x or 'Error' in x][-8:]
            raise VoicebankError(f"the DiffSinger runner failed (exit {r.returncode}): {' | '.join(err)[-1200:]}")
        out = json.loads(Path(resp).read_text(encoding='utf-8'))
    finally:
        for p in (req, resp):
            try:
                os.remove(p)
            except OSError:
                pass
    res = out.get('results', [])
    bad = [(i, x.get('error')) for i, x in enumerate(res) if not x.get('ok')]
    if bad:
        raise VoicebankError(f"DiffSinger ({bank.id}): {len(bad)} job(s) failed: " +
                             '; '.join(f"job {i} ({jobs[i].get('op')}): {e}" for i, e in bad[:4]))
    if log:
        log(f"singer: {bank.id} - {len(jobs)} job(s) in {time.time() - t0:.1f} s "
            f"({'/'.join(out.get('providers', [])) or prov})")
    return res
