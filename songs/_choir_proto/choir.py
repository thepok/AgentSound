"""Neural choir prototype, stage 1: a vowel choir sample pack rendered from the licensed DiffSinger voicebanks.

    python songs/_choir_proto/make_pack.py [--parts S,A,T,B] [--quick]     # renders + packages (D:/Repos/AgentSound/local/choir)

One soloist becomes a SECTION: every part is sung by N "virtual singers" - the same voicebank, each with its own
formant (gender) offset, static detune, slow pitch drift, vibrato rate / depth / phase / onset, attack timing, a
slightly different voice-mode blend and its own diffusion seed - rendered separately (each a real DiffSinger take,
never a copy) and summed per note into one stereo section sample. The pack is an SFZ per part and vowel with the
dynamics as live CC1 crossfades (p / mf / f = the bank's soft / core / power voice modes + level), plus a 'solo'
variant (layer 0 alone) for the A/B and the phasing measure.

Parts (SATB): S = Hanami (F3-A5), A = Hanami darker (formant +), T = TIGER (A2-C#5), B = TIGER darker; the coverage
of each part's grid is measured (HNR, level) and written to INDEX.json / coverage.json.

LICENCES (read in assets/voices/<id>/): the pack is LOCAL ONLY - never into assets/samples, never committed, never
published as a pack.
  - Hanami (Team L❤VE Voicebank License + Terms of Use.pdf): the voice may be used in commercial and non-commercial
    works with credit to Lotte V; derivative voices through the synthesiser's own settings (gender) are allowed; but
    "You may not distribute ports without prior permission" and the bank's files may not be redistributed - a
    multisampled instrument of the voice is a port of the bank to a sampler engine. Its AI❤dolGAN vocoder (which
    renders every sample) is CC BY-NC-SA 4.0: anything rendered through it is non-commercial and share-alike.
  - TIGER (extra/LICENSE.md, manifest: CC BY-NC-ND 4.0 + Commons Clause): non-commercial only, never modify or
    redistribute; a sample library of the voice is a derivative of the model -> not redistributable.
  Songs / demos made WITH the pack (mixed music, not the samples): fine for private / non-commercial publishing with
  the credits (Lotte V / Hanami, tigermeat / TIGER), Hanami's no-political / no-hateful rule, the vocoder's NC-SA.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))
import choir_audio as A  # noqa: E402

ROOT = Path(os.environ.get('CHOIR_PROTO_DIR', r'D:\Repos\AgentSound\local\choir'))
PACK = ROOT / 'pack'
WORK = ROOT / 'work'
MAIN = Path(r'D:\Repos\AgentSound')          # the main checkout: the installed voicebanks / sample packs


def setup_env() -> None:
    """Worktrees have no banks / packs: point at the main checkout's (read-only use), TMP on D:."""
    if not (REPO / 'assets' / 'voices' / 'hanami' / 'dsconfig.yaml').is_file():
        os.environ.setdefault('AGENTSOUND_VOICES', str(MAIN / 'assets' / 'voices'))
    if not (REPO / 'assets' / 'samples' / 'vpo-wav').is_dir():
        os.environ.setdefault('AGENTSOUND_SAMPLES', str(MAIN / 'assets' / 'samples'))
    if not (REPO / 'build' / 'agentsound.exe').is_file() and (MAIN / 'build' / 'agentsound.exe').is_file():
        os.environ.setdefault('AGENTSOUND_ENGINE', str(MAIN / 'build' / 'agentsound.exe'))
    for k in ('TMP', 'TEMP'):
        os.environ[k] = os.environ.get('CHOIR_TMP', str(ROOT))


SR = 44100
HOP = 512
FR = HOP / SR
PROVIDER = os.environ.get('CHOIR_PROVIDER') or None
"""'cpu' runs a second render process beside the GPU one (TIGER: ~7 s a note on 12 cores)."""

# --- the parts --------------------------------------------------------------------------------------------------
# gender: the acoustic model's key-shift (formant) input, -1..1 x the bank's augmentation range. MEASURED on these
# banks: POSITIVE = DARKER (F1 / centroid down: Hanami +0.15 at D4 centroid 588 -> 427 Hz; TIGER +0.5 at G2 F1 829 ->
# 452 Hz), negative = brighter (TIGER below C3 with gender < 0: silence). spread: the virtual singers' formant spread
# (+-), in gender units.
PARTS = {
    'S': dict(bank='hanami', notes=[60, 63, 66, 69, 72, 75, 78, 81], lo=59, hi=84, gender=-0.02, spread=0.05,
              modes={'p': {'Nectar': 0.85, 'Root': 0.15}, 'mf': {'Root': 1.0}, 'f': {'Fragrance': 0.8, 'Root': 0.2}},
              pan=(-0.75, -0.15)),
    'A': dict(bank='hanami', notes=[53, 56, 59, 62, 65, 68, 71, 74], lo=50, hi=77, gender=0.13, spread=0.05,
              modes={'p': {'Nectar': 0.85, 'Root': 0.15}, 'mf': {'Root': 1.0}, 'f': {'Fragrance': 0.8, 'Root': 0.2}},
              pan=(0.15, 0.75)),
    'T': dict(bank='tiger', notes=[48, 51, 54, 57, 60, 63, 66, 69], lo=46, hi=72, gender=0.0, spread=0.07,
              modes={'p': {'tiger_disco': 0.85, 'tiger_fresh': 0.15}, 'mf': {'tiger_fresh': 1.0},
                     'f': {'tiger_electric': 0.7, 'tiger_fresh': 0.3}},
              pan=(-0.6, -0.05)),
    'B': dict(bank='tiger', notes=[40, 43, 46, 49, 52, 55, 58, 61, 64], lo=36, hi=66, gender=0.12, spread=0.06,
              modes={'p': {'tiger_disco': 0.85, 'tiger_fresh': 0.15}, 'mf': {'tiger_fresh': 1.0},
                     'f': {'tiger_electric': 0.7, 'tiger_fresh': 0.3}},
              pan=(0.05, 0.6)),
}
SATB_RANGE = {'S': (60, 81), 'A': (55, 76), 'T': (48, 69), 'B': (40, 64)}
"""The classic choral ranges (S C4-A5, A G3-E5, T C3-A4, B E2-E4) the coverage is judged against."""

# vowels: phonemes per bank ('oo' = [u]; the hum: Hanami's sustained [m]; TIGER's own [m] / [n] sustains are
# silent or unstable at low pitches - see HUM)
VOWELS = {
    'ah': {'hanami': ['aa'], 'tiger': ['aa']},
    'oh': {'hanami': ['o'], 'tiger': ['oh']},
    'oo': {'hanami': ['u'], 'tiger': ['uw']},
    'mm': {'hanami': ['m'], 'tiger': ['m', 'm', 'm']},
    'ee': {'hanami': ['i'], 'tiger': ['iy', 'iy', 'iy']},
}
"""TIGER sings a sustained nasal of more than ~3 s as SILENCE (-90 dB: [m], [n], [ng], also after a vowel); split
into three [m] of 2.2 s it hums steadily (-21..-25 dB, no audible seams in the level). Hanami holds [m] 6.6 s."""
DYNAMICS = {'ah': ('p', 'mf', 'f'), 'oh': ('p', 'mf', 'f'), 'oo': ('p', 'mf'), 'mm': ('p', 'mf'), 'ee': ('p', 'mf')}
DYNAMICS_BANK = {'tiger': {'oh': ('p', 'mf')}}
"""TIGER renders ~5 s a note (its vocoder is slow on the GPU): its 'oh' has two dynamics."""


def dynamics(part: str, vowel: str) -> tuple:
    return DYNAMICS_BANK.get(PARTS[part]['bank'], {}).get(vowel, DYNAMICS[vowel])
LEVEL_DB = {'p': -25.0, 'mf': -19.5, 'f': -15.5}
"""Target RMS (dBFS) of a section sample's sustain at the part's centre pitch (+ TILT_DB per semitone above it)."""
TILT_DB = 0.15

NOTE_S = 6.6            # the sustained vowel (seconds)
PRE_S = 0.10            # silence before the earliest layer's onset
TAIL_S = 1.1            # after the vowel: the model's own release into silence
OFFSET = int((PRE_S - 0.02) * 44100)   # the SFZ regions skip the lead-in silence (the first singer starts at once)


@dataclass
class Singer:
    """One virtual singer of a section (all values deterministic from the part's seed)."""
    idx: int
    gender: float           # formant offset (gender units) on top of the part's
    detune_ct: float
    drift_ct: float         # slow drift amplitude
    drift_hz: tuple
    drift_ph: tuple
    vib_hz: float
    vib_ct: float
    vib_ph: float
    vib_delay: float        # s after the onset
    vib_ramp: float         # s to full depth
    onset_ms: float         # attack later than the section's first
    scoop_ct: float         # start this far off the note (below: -, above: +)
    scoop_ms: float
    fall_ct: float          # pitch sag over the release
    mode_tilt: float        # -0.15..0.15: towards the softer / stronger neighbour mode
    pan: float
    gain_db: float
    seed: int


def singers(part: str, n: int = 5, seed: int = 0) -> list[Singer]:
    """The part's N virtual singers: formants spread evenly over +-spread (shuffled), the rest drawn per singer."""
    P = PARTS[part]
    rng = random.Random(f'{part}-{seed}')
    sp = P['spread']
    gens = [(-sp + 2 * sp * i / (n - 1)) if n > 1 else 0.0 for i in range(n)]
    rng.shuffle(gens)
    lo, hi = P['pan']
    pans = [lo + (hi - lo) * (i + 0.5) / n for i in range(n)]
    rng.shuffle(pans)
    out = []
    for i in range(n):
        out.append(Singer(
            idx=i, gender=round(gens[i], 4), detune_ct=round(rng.gauss(0, 5.0), 2),
            drift_ct=round(rng.uniform(3.0, 7.0), 2),
            drift_hz=(round(rng.uniform(0.11, 0.23), 3), round(rng.uniform(0.29, 0.47), 3)),
            drift_ph=(round(rng.uniform(0, 2 * math.pi), 3), round(rng.uniform(0, 2 * math.pi), 3)),
            vib_hz=round(rng.uniform(4.7, 5.9), 3), vib_ct=round(rng.uniform(11.0, 24.0), 2),
            vib_ph=round(rng.uniform(0, 2 * math.pi), 3), vib_delay=round(rng.uniform(0.35, 1.1), 3),
            vib_ramp=round(rng.uniform(0.6, 1.4), 3), onset_ms=0.0 if i == 0 else round(rng.uniform(8, 70), 1),
            scoop_ct=round(rng.choice([-1, -1, -1, 1]) * rng.uniform(15, 55), 1),
            scoop_ms=round(rng.uniform(90, 200), 1), fall_ct=round(rng.uniform(-30, -8), 1),
            mode_tilt=round(rng.uniform(-0.15, 0.15), 3), pan=round(pans[i], 3),
            gain_db=round(rng.uniform(-1.5, 1.0), 2), seed=rng.randrange(1, 2 ** 30)))
    return out


N_OLD = {'S': 6, 'A': 6, 'T': 4, 'B': 4}
"""Stage 1's singers per part (rendered with singers(part, N_OLD[part]): their takes stay valid)."""
N_BIG = {'S': 14, 'A': 14, 'T': 12, 'B': 12}
"""Stage 3: the big section - the stage-1 singers plus new ones (their own takes, never copies)."""
WIDE = {'S': (7.0, 1.5), 'A': (7.5, 1.5), 'T': (9.0, 1.5), 'B': (9.0, 1.5)}
"""The new singers' static detune sd (cents) and their formant spread (x the part's spread): a wider section than
stage 1's 5 ct / 1x (measured: the SSO chorus's harmonics are 14 (SA) - 21 (TB) cents wide, stage 1's 12)."""


def section_singers(part: str, n: int | None = None) -> list[Singer]:
    """The part's singers of the big section: singers(part, N_OLD) as rendered in stage 1, then the new ones
    (idx N_OLD..n-1: formants interleaved over +-1.5 x spread, a wider detune / drift / vibrato range, later
    entries). pan / gain_db of every singer are replaced by its place in the room (room.py) in section_big()."""
    n = n or N_BIG[part]
    old = singers(part, N_OLD[part])
    if n <= len(old):
        return old[:n]
    P = PARTS[part]
    rng = random.Random(f'{part}-big')
    k = n - len(old)
    dt, fs = WIDE[part]
    sp = P['spread'] * fs
    gens = [-sp + 2 * sp * (i + 0.5) / k for i in range(k)]
    rng.shuffle(gens)
    out = list(old)
    for j in range(k):
        out.append(Singer(
            idx=len(old) + j, gender=round(gens[j], 4),
            detune_ct=round(max(-2.2 * dt, min(2.2 * dt, rng.gauss(0, dt))), 2),
            drift_ct=round(rng.uniform(3.0, 9.0), 2),
            drift_hz=(round(rng.uniform(0.08, 0.23), 3), round(rng.uniform(0.27, 0.5), 3)),
            drift_ph=(round(rng.uniform(0, 2 * math.pi), 3), round(rng.uniform(0, 2 * math.pi), 3)),
            vib_hz=round(rng.uniform(4.5, 6.2), 3), vib_ct=round(rng.uniform(8.0, 28.0), 2),
            vib_ph=round(rng.uniform(0, 2 * math.pi), 3), vib_delay=round(rng.uniform(0.3, 1.3), 3),
            vib_ramp=round(rng.uniform(0.5, 1.6), 3), onset_ms=round(rng.uniform(5, 95), 1),
            scoop_ct=round(rng.choice([-1, -1, -1, 1]) * rng.uniform(10, 60), 1),
            scoop_ms=round(rng.uniform(80, 230), 1), fall_ct=round(rng.uniform(-35, -6), 1),
            mode_tilt=round(rng.uniform(-0.2, 0.2), 3), pan=0.0, gain_db=0.0, seed=rng.randrange(1, 2 ** 30)))
    return out


def f0_curve(midi: float, sg: Singer, n_pre: int, n_vow: int, n_tail: int) -> list:
    """The singer's pitch (Hz per frame): a small scoop into the note, static detune, slow drift, a vibrato that
    starts late and grows, a sag over the release."""
    nf = n_pre + n_vow + n_tail
    t = (np.arange(nf) - n_pre) * FR                  # seconds from the vowel onset
    ct = np.full(nf, sg.detune_ct)
    ct += sg.drift_ct * (0.6 * np.sin(2 * np.pi * sg.drift_hz[0] * t + sg.drift_ph[0])
                         + 0.4 * np.sin(2 * np.pi * sg.drift_hz[1] * t + sg.drift_ph[1]))
    sc = sg.scoop_ms / 1000.0
    ct += np.where(t < sc, sg.scoop_ct * np.clip(1 - np.maximum(t, 0) / sc, 0, 1) ** 2, 0.0)
    ramp = np.clip((t - sg.vib_delay) / sg.vib_ramp, 0, 1)
    rate = sg.vib_hz * (1 + 0.03 * np.sin(2 * np.pi * 0.21 * t + sg.vib_ph))
    phase = np.cumsum(2 * np.pi * rate * FR) + sg.vib_ph
    ct += sg.vib_ct * ramp ** 1.5 * np.sin(phase)
    end = NOTE_S
    rel = np.clip((t - (end - 0.45)) / 0.6, 0, 1)
    ct += sg.fall_ct * rel ** 2
    return [round(float(440.0 * 2 ** ((midi - 69 + c / 100.0) / 12)), 3) for c in ct]


def mode_mix(modes: dict, dyn: str, tilt: float) -> dict:
    """The dynamic's voice-mode blend, tilted per singer toward the next softer (tilt < 0) / stronger mode."""
    order = ['p', 'mf', 'f']
    base = dict(modes[dyn])
    i = order.index(dyn)
    j = i - 1 if tilt < 0 else i + 1
    if 0 <= j < len(order) and abs(tilt) > 1e-6:
        nb = modes[order[j]]
        w = abs(tilt)
        base = {k: v * (1 - w) for k, v in base.items()}
        for k, v in nb.items():
            base[k] = base.get(k, 0.0) + v * w
    s = sum(base.values())
    return {k: round(v / s, 4) for k, v in base.items()}


def layer_job(part: str, vowel: str, dyn: str, midi: int, sg: Singer, out: Path) -> dict:
    """The DiffSinger 'sing' job of one virtual singer on one note."""
    from agentsound import voicebank as vb
    P = PARTS[part]
    ph = VOWELS[vowel][P['bank']]
    n_pre = int(round((PRE_S + sg.onset_ms / 1000.0) / FR))
    n_vow = int(round(NOTE_S / FR))
    n_tail = int(round(TAIL_S / FR))
    f0 = f0_curve(midi, sg, n_pre, n_vow, n_tail)
    nf = n_pre + n_vow + n_tail
    # the level: the release tapers over the vowel's last 0.5 s (a singer lets the note go; the model's own
    # SP release follows)
    g = np.zeros(nf)
    k0 = n_pre + n_vow - int(0.5 / FR)
    g[k0:] = -9.0 * np.clip((np.arange(nf - k0)) / (0.5 / FR + n_tail), 0, 1) ** 1.3
    k = len(ph)                         # a sustain split into k equal phonemes (TIGER's hum: m m m)
    durs = [n_pre] + [n_vow // k + (1 if i < n_vow % k else 0) for i in range(k)] + [n_tail]
    return {'op': 'sing', 'phonemes': ['SP', *ph, 'SP'], 'durations': durs, 'f0': f0,
            'gender': round(P['gender'] + sg.gender, 4), 'velocity': 1.0,
            'speaker': mode_mix(P['modes'], dyn, sg.mode_tilt), 'steps': 20,
            'gain_db': [round(float(x), 2) for x in g], 'out': str(out), 'seed': sg.seed}


def layer_path(part, vowel, dyn, midi, i) -> Path:
    return WORK / 'layers' / part / f'{part}_{vowel}_{dyn}_{midi}_L{i}.wav'


STEPS = int(os.environ.get('CHOIR_STEPS', '10'))
"""Diffusion steps of new takes (stage 3: 10 - measured on Hanami: the same HNR / centroid as 20 at half the time;
TIGER is vocoder-bound either way). Stage 1's takes were rendered at 20."""


def render_layers(part: str, vowels, n: int, *, notes=None, dyns=None, log=print, chunk: int = 60) -> float:
    """Render every missing layer of `part` (cached by file) -> seconds spent."""
    import time
    from agentsound import voicebank as vb
    P = PARTS[part]
    bank = vb.get(P['bank'])
    sgs = section_singers(part, n)
    todo = []
    for v in vowels:
        for d in (dyns or dynamics(part, v)):
            if d not in dynamics(part, v):
                continue
            for m in (notes or P['notes']):
                for sg in sgs:
                    p = layer_path(part, v, d, m, sg.idx)
                    if not p.is_file():
                        p.parent.mkdir(parents=True, exist_ok=True)
                        todo.append(dict(layer_job(part, v, d, m, sg, p), steps=STEPS))
    t0 = time.time()
    for i in range(0, len(todo), chunk):
        batch = todo[i:i + chunk]
        run_jobs(bank, batch, log=log)
        # a take that came out silent / noise (the model is unstable on some sustained consonants and low notes):
        # sing it again with another seed and a nudged formant, twice at most
        for attempt in range(2):
            bad = []
            for j in batch:
                x, _ = A.read_wav(Path(j['out']))
                seg = A.mono(x)[int(0.6 * SR):int((NOTE_S - 0.5) * SR)]
                if A.rms_db(seg) < -48.0:
                    bad.append(dict(j, seed=j['seed'] + 7 + attempt, gender=round(j['gender'] + 0.03, 4)))
            if not bad:
                break
            log(f"  {part}: {len(bad)} silent take(s), singing them again")
            run_jobs(bank, bad, log=log)
            batch = bad
        log(f"  {part}: {min(i + chunk, len(todo))}/{len(todo)} layers ({time.time() - t0:.0f} s)")
    return time.time() - t0


STAGE_UNC = Path(r'\\wsl.localhost\Ubuntu\home\richt\choir_stage')
STAGE = '/home/richt/choir_stage'
"""Stage 3: WSL's /mnt drives answer with I/O errors on this machine (the 9p drvfs mounts are wedged; restarting WSL
would kill the user's services in it), so the runner, the two banks' acoustic + vocoder models and every request /
take live in the WSL home (Windows reaches it over \\\\wsl.localhost); $CHOIR_STAGE=0 = agentsound.voicebank.run."""


VOCODER_CPU = {b: int(n) for b, n in (kv.split(':') for kv in
                                     os.environ.get('CHOIR_VOCODER_CPU', '').split(',') if kv)}
"""$CHOIR_VOCODER_CPU='tiger:4': that bank's vocoder on the CPU with 4 threads (the acoustic model stays on the GPU)."""


def run_jobs(bank, jobs: list, *, log=print, timeout: float = 7200) -> list:
    """Run 'sing' jobs whose 'out' are Windows paths (through the WSL-home stage unless $CHOIR_STAGE is '0')."""
    import shutil
    import subprocess
    import time
    import uuid
    from agentsound import voicebank as vb
    if os.environ.get('CHOIR_STAGE', '1') == '0':
        return vb.run(bank, [dict(j, out=vb.wsl_path(j['out'])) for j in jobs], work=WORK / 'req', log=log,
                      provider=PROVIDER)
    tag = uuid.uuid4().hex[:10]
    sj = [dict(j, out=f'{STAGE}/out/{tag}/{i}.wav') for i, j in enumerate(jobs)]
    req = STAGE_UNC / f'req_{tag}.json'
    voc = VOCODER_CPU.get(bank.id)
    req.write_text(json.dumps({'bank': f'{STAGE}/banks/{bank.id}', 'provider': PROVIDER or vb.PROVIDER, 'jobs': sj,
                               **({'vocoder_provider': 'cpu', 'cpu_threads': voc} if voc else {})}),
                   encoding='utf-8')
    t0 = time.time()
    cmd = f'"{vb._python()}" {STAGE}/ds_runner.py {STAGE}/req_{tag}.json {STAGE}/resp_{tag}.json'
    resp = STAGE_UNC / f'resp_{tag}.json'
    # wsl.exe sometimes never returns after the runner is done (seen once: a 2 h hang with the response written):
    # wait for the response file instead, then let the client go
    pr = subprocess.Popen(['wsl.exe', '-d', 'Ubuntu', '--cd', '~', '--', 'bash', '-c', cmd],
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    out = None
    while time.time() - t0 < timeout:
        if resp.is_file():
            try:
                out = json.loads(resp.read_text(encoding='utf-8'))
                break
            except (OSError, ValueError):
                pass                                   # still being written
        if pr.poll() is not None and not resp.is_file():
            time.sleep(1.0)
            if not resp.is_file():
                err = pr.stderr.read().decode('utf-8', 'replace')[-800:] if pr.stderr else ''
                raise RuntimeError(f"staged runner failed ({pr.returncode}): {err}")
        time.sleep(1.0)
    if pr.poll() is None:
        try:
            pr.wait(timeout=20)
        except subprocess.TimeoutExpired:
            pr.kill()                                  # our own wsl.exe client only
    if out is None:
        raise RuntimeError(f"staged runner: no response after {timeout:.0f} s")
    req.unlink(missing_ok=True)
    resp.unlink(missing_ok=True)
    res = out['results']
    bad = [(i, x.get('error')) for i, x in enumerate(res) if not x.get('ok')]
    if bad:
        raise RuntimeError(f"{bank.id}: {len(bad)} job(s) failed: {bad[:3]}")
    for i, j in enumerate(jobs):
        Path(j['out']).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(STAGE_UNC / 'out' / tag / f'{i}.wav'), j['out'])
    try:
        (STAGE_UNC / 'out' / tag).rmdir()
    except OSError:
        pass
    if log:
        log(f"singer: {bank.id} - {len(jobs)} job(s) in {time.time() - t0:.1f} s "
            f"({'/'.join(out.get('providers', []))})")
    return res


def _win(p: str) -> str:
    """/mnt/d/x -> D:/x"""
    if p.startswith('/mnt/') and len(p) > 6:
        return f"{p[5].upper()}:/{p[7:]}"
    return p


def pan_gains(p: float) -> tuple[float, float]:
    a = (p + 1) * math.pi / 4
    return math.cos(a), math.sin(a)


def section(part: str, vowel: str, dyn: str, midi: int, n: int, *, solo: bool = False,
            copies: bool = False) -> np.ndarray:
    """Sum the layers into the stereo section sample (solo: layer 0 alone, centred; copies: layer 0 N times with
    the section's onsets / pans / gains - the naive 'one take x N' section, for the phasing A/B)."""
    sgs = singers(part, n)
    xs = []
    for sg in sgs:
        x, _ = A.read_wav(layer_path(part, vowel, dyn, midi, 0 if (solo or copies) else sg.idx))
        x = A.mono(x)
        # every singer at the same sustain level first (TIGER's takes differ by up to ~14 dB with the formant
        # offset: one quiet layer would leave a section of four); then the singer's own small gain offset
        a, b = int((PRE_S + 0.4) * SR), int((PRE_S + NOTE_S - 0.6) * SR)
        x = x * 10 ** ((-20.0 - A.rms_db(x[a:b])) / 20)
        if copies and sg.idx:
            x = np.concatenate([np.zeros(int(sg.onset_ms / 1000 * SR)), x])
        xs.append(x)
        if solo:
            break
    m = max(x.size for x in xs)
    out = np.zeros((m, 2))
    for sg, x in zip(sgs, xs):
        gl, gr = pan_gains(0.0 if solo else sg.pan)
        g = 10 ** (sg.gain_db / 20) if not solo else 1.0
        out[:x.size, 0] += g * gl * x
        out[:x.size, 1] += g * gr * x
    return out


MIX_DETUNE_CT = {'S': 3.0, 'A': 5.0, 'T': 9.0, 'B': 9.0}
"""Stage 3, at mix time: every singer's take is varispeeded by its own static detune (sd, cents) plus a slow drift
(2-5 ct) - widens the section's pitch spread over the already rendered takes without singing them again (a few
cents of resampling: no audible formant shift)."""
BREATH_DB = {'S': -38.0, 'A': -36.0, 'T': -26.0, 'B': -25.0}
"""Each singer's breath: noise in its own vowel colour (the take's smooth spectral envelope, emphasis 1-5 kHz) that
follows the take's level, this far under the take (dB). The SSO men's chorus reads HNR ~22 dB, stage 1's 32."""
NFFT = 1 << 19


def mix_params(part: str, idx: int) -> dict:
    rng = random.Random(f'mix-{part}-{idx}')
    sd = MIX_DETUNE_CT[part]
    return {'static_ct': max(-2.5 * sd, min(2.5 * sd, rng.gauss(0, sd))), 'drift_ct': rng.uniform(2.0, 5.0),
            'drift_hz': rng.uniform(0.05, 0.16), 'drift_ph': rng.uniform(0, 2 * math.pi),
            'gain_db': rng.uniform(-1.5, 1.0), 'breath_db': BREATH_DB[part] + rng.uniform(-3.0, 3.0),
            'noise_seed': rng.randrange(1, 2 ** 31)}


def varispeed(x: np.ndarray, static_ct: float, drift_ct: float, drift_hz: float, drift_ph: float) -> np.ndarray:
    """Resample x by 2^(cents(t)/1200) (cubic Hermite): a static detune + a slow sine drift."""
    t = np.arange(x.size) / SR
    r = 2 ** ((static_ct + drift_ct * np.sin(2 * np.pi * drift_hz * t + drift_ph)) / 1200.0)
    pos = np.concatenate([[0.0], np.cumsum(r[:-1])])
    pos = pos[pos < x.size - 3]
    i = pos.astype(np.int64)
    u = pos - i
    xp = np.concatenate([[x[0]], x, [x[-1], x[-1]]])
    xm1, x0, x1, x2 = xp[i], xp[i + 1], xp[i + 2], xp[i + 3]
    c1 = 0.5 * (x1 - xm1)
    c2 = xm1 - 2.5 * x0 + 2 * x1 - 0.5 * x2
    c3 = 0.5 * (x2 - xm1) + 1.5 * (x0 - x1)
    return ((c3 * u + c2) * u + c1) * u + x0


def breath(x: np.ndarray, level_db: float, seed: int) -> np.ndarray:
    """Breath noise for one take: white noise through the take's smooth spectral envelope (+ a 1-5 kHz emphasis),
    following the take's level (50 ms), at level_db under the take's sustain."""
    a, b = int((PRE_S + 0.4) * SR), int((PRE_S + NOTE_S - 0.6) * SR)
    fr, env = A.envelope(x[a:b])
    rng = np.random.default_rng(seed)
    n = 1 << int(np.ceil(np.log2(x.size + 1)))
    f = np.fft.rfftfreq(n, 1 / SR)
    mag = 10 ** (np.interp(f, fr, env) / 20)
    mag *= (f / (f + 900.0)) / np.sqrt(1 + (f / 6000.0) ** 2)
    N = np.fft.irfft(mag * np.exp(2j * np.pi * rng.random(f.size)), n)[:x.size]
    k = int(0.05 * SR)
    c = np.concatenate([[0.0], np.cumsum(x ** 2)])          # a centred 50 ms moving mean of the power
    i = np.arange(x.size)
    lo, hi = np.clip(i - k // 2, 0, x.size), np.clip(i + k // 2, 0, x.size)
    lv = np.sqrt((c[hi] - c[lo]) / np.maximum(hi - lo, 1) + 1e-20)
    sus = np.sqrt(np.mean(x[a:b] ** 2)) + 1e-20
    N *= lv / sus
    N *= sus * 10 ** (level_db / 20) / (np.sqrt(np.mean(N[a:b] ** 2)) + 1e-20)
    return N


def section_big(part: str, vowel: str, dyn: str, midi: int, n: int | None = None, *, place: bool = True,
                widen: bool = True, breathe: bool = True) -> np.ndarray:
    """Stage 3's section sample: the part's N_BIG singers (section_singers), each take level-matched, varispeeded
    by its own detune / drift (widen), with its own breath (breathe), placed in the hall (room.py: direct sound +
    early reflections to an A-B pair; place=False: the stage-1 pans), summed in stereo."""
    import room
    n = n or N_BIG[part]
    sgs = section_singers(part, n)
    H = room.impulse_spectra(part, n, NFFT) if place else None
    a, b = int((PRE_S + 0.4) * SR), int((PRE_S + NOTE_S - 0.6) * SR)
    out = np.zeros((NFFT, 2))
    acc = np.zeros((2, NFFT // 2 + 1), np.complex128)          # the placed singers, summed as spectra
    m = 0
    for sg in sgs:
        x = A.mono(A.read_wav(layer_path(part, vowel, dyn, midi, sg.idx))[0])
        x = x * 10 ** ((-20.0 - A.rms_db(x[a:b])) / 20)
        mp = mix_params(part, sg.idx)
        if widen:
            x = varispeed(x, mp['static_ct'], mp['drift_ct'], mp['drift_hz'], mp['drift_ph'])
        if breathe:
            x = x + breath(x, mp['breath_db'], mp['noise_seed'])
        x = x * 10 ** (mp['gain_db'] / 20)
        m = max(m, x.size)
        if place:
            X = np.fft.rfft(x, NFFT)
            acc += X[None, :] * H[sg.idx]
        else:
            gl, gr = pan_gains(sg.pan if sg.idx < N_OLD[part] else
                               PARTS[part]['pan'][0] + (PARTS[part]['pan'][1] - PARTS[part]['pan'][0]) *
                               random.Random(f'pan-{part}-{sg.idx}').random())
            out[:x.size, 0] += gl * x
            out[:x.size, 1] += gr * x
    if place:
        out[:, 0] = np.fft.irfft(acc[0], NFFT)
        out[:, 1] = np.fft.irfft(acc[1], NFFT)
    return out[:m + int(0.25 * SR)]


CLONES = 3
"""Stage 3 'clones': each stage-1 singer (N_OLD a part) heard CLONES times - itself plus clones changed mechanically
so they never comb with it (the user's idea; no new renders)."""


def clone_layers(part: str, vowel: str, dyn: str, midi: int, k: int = CLONES) -> list:
    """-> [mono take] of N_OLD[part] * k: each stage-1 take (level-matched like section()) and k-1 clones of it.
    A clone gets, all drawn from its own seed:
      - a static detune of 3-8 cents (alternating sign) + a slow pitch LFO (0.1-0.5 Hz, 3-12 ct), by resampling;
      - its own pre-delay (3-25 ms) that itself moves slowly (+-0.6-2 ms at 0.05-0.3 Hz) - never a fixed tiny delay;
      - a random-phase all-pass (the phase a smooth random walk over frequency, ~1 rad per 40 Hz: decorrelates
        the copy without smearing the attack) and a timbre change (a +-1.5 dB tilt and two +-2.5 dB peaks at
        random frequencies 300-4000 Hz), in one zero-latency FFT filter;
      - a slow level wobble (+-0.8 dB at 0.05-0.2 Hz) and its own breath.
    Clone 0 of each singer is the take itself (with the same mix-time widening as section_big)."""
    a, b = int((PRE_S + 0.4) * SR), int((PRE_S + NOTE_S - 0.6) * SR)
    out = []
    for sg in singers(part, N_OLD[part]):
        x0 = A.mono(A.read_wav(layer_path(part, vowel, dyn, midi, sg.idx))[0])
        x0 = x0 * 10 ** ((-20.0 - A.rms_db(x0[a:b])) / 20)
        for c in range(k):
            rng = random.Random(f'clone-{part}-{sg.idx}-{c}')
            x = x0
            if c == 0:
                mp = mix_params(part, sg.idx)
                x = varispeed(x, mp['static_ct'], mp['drift_ct'], mp['drift_hz'], mp['drift_ph'])
                out.append(x + breath(x, mp['breath_db'], mp['noise_seed']))
                continue
            sign = 1 if (c + sg.idx) % 2 else -1
            static = sign * rng.uniform(3.0, 8.0)
            lfo_hz, lfo_ct, lfo_ph = rng.uniform(0.1, 0.5), rng.uniform(3.0, 12.0), rng.uniform(0, 2 * math.pi)
            d0, dd = rng.uniform(0.003, 0.025), rng.uniform(0.0006, 0.002)
            dhz, dph = rng.uniform(0.05, 0.3), rng.uniform(0, 2 * math.pi)
            t = np.arange(x.size + int(0.03 * SR)) / SR
            r = 2 ** ((static + lfo_ct * np.sin(2 * np.pi * lfo_hz * t + lfo_ph)) / 1200.0)
            pos = np.concatenate([[0.0], np.cumsum(r[:-1])]) - (d0 + dd * np.sin(2 * np.pi * dhz * t + dph)) * SR
            xp = np.concatenate([np.zeros(2), x, np.zeros(3)])
            pos = np.clip(pos + 1.0, 0, xp.size - 3.001)
            i = pos.astype(np.int64)
            u = pos - i
            xm1, xa, x1, x2 = xp[np.maximum(i - 1, 0)], xp[i], xp[i + 1], xp[i + 2]
            c1 = 0.5 * (x1 - xm1)
            c2 = xm1 - 2.5 * xa + 2 * x1 - 0.5 * x2
            c3 = 0.5 * (x2 - xm1) + 1.5 * (xa - x1)
            y = ((c3 * u + c2) * u + c1) * u + xa
            # the all-pass + timbre filter
            n = 1 << int(np.ceil(np.log2(y.size + 1)))
            f = np.fft.rfftfreq(n, 1 / SR)
            nr = np.random.default_rng(rng.randrange(1, 2 ** 31))
            step = 40.0 / (SR / n)                              # bins per 40 Hz
            knots = np.cumsum(nr.normal(0, 1.0, int(f.size / step) + 3))
            phase = np.interp(np.arange(f.size) / step, np.arange(knots.size), knots)
            phase -= phase[0]
            gdb = rng.uniform(-1.5, 1.5) * np.log2(np.maximum(f, 50) / 1000.0) / 4.3
            for _ in range(2):
                fc, gp, q = math.exp(rng.uniform(math.log(300), math.log(4000))), rng.uniform(-2.5, 2.5), 1.2
                gdb += gp / (1 + ((f - fc) / (fc / q)) ** 2)
            y = np.fft.irfft(np.fft.rfft(y, n) * 10 ** (gdb / 20) * np.exp(1j * phase), n)[:y.size]
            wob = 10 ** (rng.uniform(0.3, 0.8) * np.sin(2 * np.pi * rng.uniform(0.05, 0.2) * t[:y.size]
                                                         + rng.uniform(0, 6.3)) / 20)
            y = y * wob
            out.append(y + breath(y, BREATH_DB[part] + rng.uniform(-3, 3), rng.randrange(1, 2 ** 31)))
    return out


def section_clones(part: str, vowel: str, dyn: str, midi: int, k: int = CLONES) -> np.ndarray:
    """The clone section: clone_layers(), each on its own seat of the hall (room.py, like section_big)."""
    import room
    L = clone_layers(part, vowel, dyn, midi, k)
    H = room.impulse_spectra(part, len(L), NFFT)
    acc = np.zeros((2, NFFT // 2 + 1), np.complex128)
    m = 0
    for i, x in enumerate(L):
        x = x[:NFFT] * 10 ** (random.Random(f'cg-{part}-{i}').uniform(-1.5, 1.0) / 20)
        m = max(m, x.size)
        acc += np.fft.rfft(x, NFFT)[None, :] * H[i]
    out = np.stack([np.fft.irfft(acc[0], NFFT), np.fft.irfft(acc[1], NFFT)], axis=1)
    return out[:m + int(0.25 * SR)]


SSO_CHORUS = MAIN / 'assets' / 'samples' / 'sso' / 'Sonatina Symphonic Orchestra' / 'Samples' / 'Chorus'
BASS_OLD = {40: ('g2', -300.0), 43: ('g2', 0.0), 46: ('a#2', 0.0)}
"""The bass's bottom (TIGER under ~C3 is breath over weak harmonics: HNR 11-19 dB at E2-Bb2): the SSO men's chorus
(the recording behind sampled/choir_male / choir_mixed; chromatic G2-F4, so E2 is its G2 three semitones down) is
layered under the new section. (source note, shift in cents) per bass grid note."""
BASS_W = {'mm': {40: 0.95, 43: 0.5}, None: {40: 1.0, 43: 0.95, 46: 0.75}}
BASS_REF = 49
"""The vowel colour the old choir is matched to: the new section's own smooth envelope at C#3 (clean takes; under
it the takes' envelope is mostly their breath noise)."""
"""The old choir's share (amplitude; the new section gets sqrt(1 - w^2): the two are uncorrelated) per grid note -
the hum keeps TIGER's own [m] down to G2 (it holds HNR 28 there)."""


def bass_bottom(new: np.ndarray, vowel: str, dyn: str, midi: int, ref: np.ndarray | None = None) -> np.ndarray:
    """Layer the SSO men's chorus under a bass section sample (B notes <= Bb2): pitched to the note, its onset at the
    section's, its release shaped like the takes', its smooth spectral envelope matched to the section's (the vowel:
    'ah' as sung; 'oh' / 'oo' / 'ee' / the hum imposed through the envelope, +-15 dB), level-matched, kept on the
    bass's side; then mixed in at BASS_W."""
    w = BASS_W.get(vowel, BASS_W[None]).get(midi, 0.0)
    if w <= 0 or midi not in BASS_OLD:
        return new
    name, shift = BASS_OLD[midi]
    x, _ = A.read_wav(SSO_CHORUS / f'chorus-male-{name}.wav')
    if shift:
        x = np.stack([varispeed(x[:, c], shift, 0.0, 0.1, 0.0) for c in (0, 1)], axis=1)
    # onset: the SSO notes start at once - put it at the section's first sound
    on = int(np.argmax(A.mono(np.abs(new)) > 0.05 * np.max(np.abs(new))))
    y = np.zeros_like(new)
    k = min(new.shape[0] - on, x.shape[0])
    y[on:on + k] = x[:k]
    # the takes' release: hold to the vowel's last 0.5 s, then -9 dB and out over ~1.3 s
    t = np.arange(y.shape[0]) / SR
    r0 = PRE_S + NOTE_S - 0.5
    g = np.where(t < r0, 1.0, np.clip(1 - (t - r0) / 1.4, 0, 1) ** 1.6)
    y *= g[:, None]
    # the vowel / colour: the section's smooth envelope over the old one's
    a, b = int((PRE_S + 0.6) * SR), int((PRE_S + NOTE_S - 0.8) * SR)
    fr, en = A.envelope(A.mono((new if ref is None else ref)[a:b]), lifter=120)   # ~370 Hz resolution
    _, eo = A.envelope(A.mono(y[a:b]), lifter=120)
    n = 1 << int(np.ceil(np.log2(y.shape[0] + 1)))
    f = np.fft.rfftfreq(n, 1 / SR)
    # only the vowel's formant region (150-3500 Hz, its mean offset removed, -24..+6 dB) - above it the old recording
    # keeps its own (darker, cleaner) top: matching that to the takes made it as hissy as TIGER's (HNR 15 -> 11)
    band = (fr >= 150) & (fr <= 3500)
    diff = en - eo
    diff = diff - np.mean(diff[band])
    taper = np.clip(np.minimum((fr - 100) / 50, (5000 - fr) / 1000), 0, 1)
    amt = 0.4 if vowel == 'ah' else 1.0               # the SSO chorus sings "ah" itself
    d = np.clip(diff, -24.0, 6.0)
    d = np.where(d > 0, d * taper, d * (fr >= 120))  # boosts in the formant band only; cuts anywhere (oo / hum)
    gd = np.interp(f, fr, d * amt)
    G = 10 ** (gd / 20)
    y = np.stack([np.fft.irfft(np.fft.rfft(y[:, c], n) * G, n)[:y.shape[0]] for c in (0, 1)], axis=1)
    if dyn == 'p':                                    # the soft layer: a little darker, like the takes' soft mode
        Y = np.fft.rfft(y, n, axis=0) / np.sqrt(1 + (f / 2500.0) ** 2)[:, None]
        y = np.fft.irfft(Y, n, axis=0)[:y.shape[0]]
    y[:, 0] *= 0.8                                    # on the bass's side (right of centre)
    y *= 10 ** ((A.rms_db(new[a:b]) - A.rms_db(y[a:b])) / 20)
    return np.sqrt(max(0.0, 1 - w * w)) * new + w * y


def normalise(x: np.ndarray, part: str, dyn: str, midi: int) -> tuple[np.ndarray, float]:
    """Scale to the dynamic's target RMS (measured over the sustain), tilted by pitch; a 40 ms fade at the end."""
    P = PARTS[part]
    centre = sum(P['notes']) / len(P['notes'])
    target = LEVEL_DB[dyn] + TILT_DB * (midi - centre)
    a, b = int((PRE_S + 0.4) * SR), int((PRE_S + NOTE_S - 0.6) * SR)
    cur = A.rms_db(x[a:b])
    g = 10 ** ((target - cur) / 20)
    y = x * g
    f = int(0.04 * SR)
    y[-f:] *= np.linspace(1, 0, f)[:, None]
    return y, round(target - cur, 2)


def quality(x: np.ndarray, midi: int) -> dict:
    """HNR (dB) and raw level of a layer's sustain - the coverage measure."""
    a, b = int((PRE_S + 0.5) * SR), int((PRE_S + NOTE_S - 0.8) * SR)
    seg = A.mono(x)[a:b]
    return {'hnr_db': round(A.hnr_db(seg, 440 * 2 ** ((midi - 69) / 12)), 1), 'rms_db': round(A.rms_db(seg), 1)}


SOURCE = {
    'hanami': 'Hoshino Hanami ~AI❤dol~ DiffSinger voicebank by Lotte V (lottev.moe)',
    'tiger': 'TIGER DiffSinger voicebank by tigermeat (tigermeat.xyz)',
}


def note_name(k: int) -> str:
    return ['C', 'Cs', 'D', 'Ds', 'E', 'F', 'Fs', 'G', 'Gs', 'A', 'As', 'B'][k % 12] + str(k // 12 - 1)


XF = {3: {'p': (None, (40, 80)), 'mf': ((40, 80), (85, 120)), 'f': ((85, 120), None)},
      2: {'p': (None, (45, 95)), 'mf': ((45, 95), None)},
      1: {'p': (None, None), 'mf': (None, None), 'f': (None, None)}}
"""The live dynamics crossfades on CC1 (the sampler's 'dynamics' x 127): (xfin lo/hi, xfout lo/hi) per layer."""


def write_sfz(part: str, vowel: str, variant: str, files: dict) -> Path:
    """One .sfz per part / vowel / variant ('section' | 'solo' | 'copies'): the grid's keys split half way between
    neighbours, the dynamics as CC1 crossfades (default CC1 = 80: mf), velocity -> level (amp_veltrack 35)."""
    P = PARTS[part]
    notes = sorted({m for (d, m) in files})
    dyns = [d for d in ('p', 'mf', 'f') if any(k[0] == d for k in files)]
    xf = XF[len(dyns)]
    lines = [f'// AgentSound neural-choir prototype: {part} "{vowel}" ({variant}), {P["bank"]} voicebank - LOCAL ONLY',
             '<control>', 'set_cc1=80',
             '<global>', 'amp_veltrack=35', 'ampeg_attack=0.004', 'ampeg_release=0.55', 'loop_mode=no_loop']
    for d in dyns:
        xin, xout = xf[d]
        g = ['<group>']
        if xin:
            g += [f'xfin_locc1={xin[0]}', f'xfin_hicc1={xin[1]}']
        if xout:
            g += [f'xfout_locc1={xout[0]}', f'xfout_hicc1={xout[1]}']
        lines.append(' '.join(g))
        for i, m in enumerate(notes):
            lo = P['lo'] if i == 0 else (notes[i - 1] + m) // 2 + 1
            hi = P['hi'] if i == len(notes) - 1 else (m + notes[i + 1]) // 2
            lines.append(f'<region> sample={files[(d, m)].name} lokey={lo} hikey={hi} pitch_keycenter={m} '
                         f'offset={OFFSET}')
    path = PACK / f'{part}_{vowel}{"" if variant == "section" else "_" + variant}.sfz'
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


def package(parts, vowels, n: int, variants=('section', 'solo', 'copies'), log=print) -> dict:
    """Mix the layers into section / solo / copies samples, write the SFZ files, SOURCE.json, INDEX.json and the
    coverage / phasing measures -> the coverage dict."""
    PACK.mkdir(parents=True, exist_ok=True)
    cov: dict = {}
    for part in parts:
        P = PARTS[part]
        for v in vowels:
            for variant in variants:
                files = {}
                nn = N_BIG[part] if variant in ('big', 'big_nobass') else N_OLD[part]  # clones: the stage-1 takes
                refs = {}
                for d in dynamics(part, v):
                    for m in P['notes']:
                        if not all(layer_path(part, v, d, m, i).is_file() for i in range(nn)):
                            continue
                        if variant == 'clones':
                            x = section_clones(part, v, d, m)
                            if part == 'B' and m in BASS_OLD:
                                if (v, d) not in refs:
                                    refs[(v, d)] = section_clones(part, v, d, BASS_REF)
                                x = bass_bottom(x, v, d, m, refs[(v, d)])
                        elif variant in ('big', 'big_nobass'):
                            x = section_big(part, v, d, m)
                            if part == 'B' and variant == 'big' and m in BASS_OLD:
                                if (v, d) not in refs:
                                    refs[(v, d)] = section_big(part, v, d, BASS_REF)
                                x = bass_bottom(x, v, d, m, refs[(v, d)])
                        else:
                            x = section(part, v, d, m, nn, solo=variant == 'solo', copies=variant == 'copies')
                        y, gain = normalise(x, part, d, m)
                        f = PACK / 'samples' / variant / part / f'{part}_{v}_{d}_{note_name(m)}.wav'
                        A.write_wav(f, y)
                        files[(d, m)] = f
                        if variant in ('big', 'big_nobass', 'clones'):
                            cov.setdefault(f'{part}:{variant}', {}).setdefault(v, {})[f'{d}_{m}'] = {
                                **quality(y, m), 'gain_db': gain}
                        if variant == 'section':
                            q = [quality(A.read_wav(layer_path(part, v, d, m, i))[0], m) for i in range(nn)]
                            cov.setdefault(part, {}).setdefault(v, {})[f'{d}_{m}'] = {
                                'hnr_db': round(float(np.median([x['hnr_db'] for x in q])), 1),
                                'raw_rms_db': round(float(np.median([x['rms_db'] for x in q])), 1),
                                'gain_db': gain}
                if files:
                    rel = {k: Path(f'samples/{variant}/{part}') / f.name for k, f in files.items()}
                    sfz = write_sfz(part, v, variant, {k: PACK / r for k, r in rel.items()})
                    # sample= relative to the sfz's folder
                    txt = sfz.read_text(encoding='utf-8')
                    for k, r in rel.items():
                        txt = txt.replace(f'sample={r.name} ', f'sample={r.as_posix()} ')
                    sfz.write_text(txt, encoding='utf-8')
                    log(f"  {sfz.name}: {len(files)} samples")
    return cov


def write_source(parts) -> None:
    from agentsound import voicebank as vb
    banks = sorted({PARTS[p]['bank'] for p in parts})
    src = {
        'id': 'choir-proto',
        'title': 'AgentSound neural choir prototype (vowel choir rendered from DiffSinger voicebanks)',
        'url': '', 'homepage': '',
        'license': ' + '.join(vb.get(b).entry['license'] for b in banks),
        'licenseUrl': ' ; '.join(vb.get(b).entry.get('licenseUrl', '') for b in banks),
        'attribution': '; '.join(SOURCE[b] for b in banks),
        'restrictions': ('LOCAL ONLY: rendered from licensed voicebanks whose terms forbid redistributing the bank and '
                         'its ports / derivatives (Hanami: no distribution of ports without permission, vocoder CC '
                         'BY-NC-SA 4.0; TIGER: non-commercial, no derivatives / redistribution). Songs made with it: '
                         'non-commercial, credit the voicebanks. Never publish this pack.'),
        'voices': {b: vb.get(b).source() for b in banks},
        'generated_by': 'songs/_choir_proto/make_pack.py',
    }
    (PACK / 'SOURCE.json').write_text(json.dumps(src, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
