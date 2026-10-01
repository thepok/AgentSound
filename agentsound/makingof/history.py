"""What we tried: the song's own history as before / after episodes.

The A&R judged a build (AR.md: "Judged: ... @ <commit>"), ranked its issues, and the owners revised the song
(AR.md "## Revision"). The judged song.py is still in git: it is extracted (git archive) into a cache folder and
rendered once with today's engine (python -m agentsound build --no-mp3), so the film can play the same bars before
and after the fix, loudness-matched. Every episode's words are the log's: the A&R's issue title, the revision's
head and its measured before -> after numbers.

Clip positions come from the issue's own text: a time stamp ("at 2:07"), else a bar ("Bar 74"), else the first
section it names; an episode without one is left out."""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path

from . import docs

CLIP = 6.5            # seconds per before / after clip


def judged_commit(ar_md: str) -> str | None:
    m = re.search(r'Judged[^\n@]*@\s*`?([0-9a-f]{7,40})', ar_md)
    return m.group(1) if m else None


def _git(repo: Path, *args: str, binary: bool = False):
    r = subprocess.run(['git', *args], cwd=str(repo), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.decode(errors='replace')[:300]}")
    return r.stdout if binary else r.stdout.decode('utf-8', errors='replace')


def commits(repo: Path, song_dir: Path) -> list[dict]:
    """The song folder's commits, oldest first: [{'sha', 'date', 'subject'}]."""
    rel = song_dir.resolve().relative_to(repo.resolve()).as_posix()
    out = _git(repo, 'log', '--follow', '--format=%h%x09%ad%x09%s', '--date=short', '--', f'{rel}/song.py')
    rows = [l.split('\t', 2) for l in out.splitlines() if l.strip()]
    return [{'sha': r[0], 'date': r[1], 'subject': r[2]} for r in reversed(rows) if len(r) == 3]


def old_render(repo: Path, song_dir: Path, sha: str, cache: Path, log=print) -> Path | None:
    """out/ of the song as it was at `sha`, rendered once with today's engine (None if it no longer builds)."""
    rel = song_dir.resolve().relative_to(repo.resolve()).as_posix()
    base = cache / f'{song_dir.name}-{sha}'
    old_dir = base / rel
    out = old_dir / 'out'
    if (out / 'mix.wav').is_file() and (out / 'report.json').is_file():
        return out
    fail = base / 'FAILED.txt'
    if fail.is_file():
        return None
    base.mkdir(parents=True, exist_ok=True)
    data = _git(repo, 'archive', '--format=tar', sha, rel, binary=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        tf.extractall(base, filter='data')
    log(f"history: rendering {song_dir.name} as of {sha} (once; cached in {base}) ...")
    r = subprocess.run([sys.executable, '-m', 'agentsound', 'build', str(old_dir), '--no-mp3'], cwd=str(repo),
                       capture_output=True, text=True, errors='replace')
    if r.returncode != 0 or not (out / 'mix.wav').is_file():
        fail.write_text(r.stdout[-3000:] + '\n' + r.stderr[-3000:], encoding='utf-8')
        log(f"history: the version {sha} no longer builds (see {fail}); no before clips")
        return None
    return out


def _bar_time(report: dict, bar: float) -> float | None:
    rows = report['timeline']['rows']
    cols = {c: i for i, c in enumerate(report['timeline']['columns'])}
    for r in rows:
        if r[cols['bar']] == int(bar):
            return r[cols['sec']]
    return None


def locate(text: str, report: dict) -> tuple[float, str] | None:
    """Where an issue happens: 'at M:SS' > 'bar N' > the first section it names -> (song seconds, how)."""
    t = docs.strip_md(text)
    m = re.search(r'\bat (\d+):(\d\d(?:\.\d+)?)', t)
    if m:
        return int(m.group(1)) * 60 + float(m.group(2)) - 1.0, f"at {m.group(1)}:{m.group(2)}"
    m = re.search(r'\b[Bb]ars? (\d+)', t)
    if m:
        bt = _bar_time(report, int(m.group(1)))
        if bt is not None:
            return bt - 1.5, f"bar {m.group(1)}"
    secs = sorted(report['sections'], key=lambda s: -len(s['name']))
    best = None
    for s in secs:
        mm = re.search(rf'(?<![\w-]){re.escape(s["name"])}(?![\w-])', t)
        if mm and (best is None or mm.start() < best[0]):
            best = (mm.start(), s)
    if best:
        s = best[1]
        return s['startSec'] + min(2.0, (s['endSec'] - s['startSec']) * 0.15), f"the {s['name']}"
    return None


def episodes(facts: dict, ar_md: str, report: dict, old_report: dict | None, max_n: int = 3) -> list[dict]:
    """The strongest before / after episodes: the revision items (A&R order) that name where they happen and carry
    a measured before -> after number."""
    issues = {i['n']: i for i in docs.ar_issues(ar_md)}
    out = []
    for r in docs.ar_revision(ar_md):
        iss = issues.get(r['n'])
        if not iss:
            continue
        pos = locate(iss['title'] + '. ' + iss['text'], report)
        if pos is None:
            continue
        good = [p for p in r['pairs'] if len(p['label']) <= 48 and p['label'][:1].isalpha()]
        key = [p for p in good if p.get('key')] + [p for p in good if not p.get('key')]
        if not key:
            continue
        t0 = max(0.0, min(pos[0], facts['duration'] - CLIP - 1))
        t_old = t0
        if old_report is not None:     # the same place in the old song: same section, same offset
            sec = next((s for s in report['sections'] if s['startSec'] <= t0 < s['endSec']), None)
            osec = next((s for s in old_report['sections'] if sec and s['name'] == sec['name']), None)
            if sec and osec:
                t_old = osec['startSec'] + (t0 - sec['startSec'])
        head = re.sub(r'^\[\w+\]\s*', '', r['head'])
        head = re.sub(r'\s*->.*$', '', head)
        head = re.sub(r'\s*\([^)]*\)\s*\.?$', '', head)
        out.append({'n': r['n'], 'severity': iss['severity'], 'issue': iss['title'].rstrip('.'), 'owner': iss['owner'],
                    'fix': head, 'status': r['status'] or 'revised', 'pairs': key[:3], 'where': pos[1],
                    'after': round(t0, 3), 'before': round(t_old, 3), 'clip': CLIP})
        if len(out) >= max_n:
            break
    return out


def clip_gain(wav: Path, start: float, dur: float, ffmpeg: str, target: float = -16.0) -> tuple[float, float]:
    """(measured LUFS, gain dB to the target) of a clip - A / B loudness-matched to be fair."""
    r = subprocess.run([ffmpeg, '-hide_banner', '-nostats', '-ss', f'{start:.3f}', '-t', f'{dur:.3f}', '-i', str(wav),
                        '-af', 'ebur128=framelog=quiet', '-f', 'null', '-'], capture_output=True, text=True,
                       errors='replace')
    m = re.findall(r'I:\s*(-?[\d.]+)\s*LUFS', r.stderr)
    lufs = float(m[-1]) if m else target
    return lufs, max(-12.0, min(12.0, target - lufs))


def load_report(out_dir: Path) -> dict | None:
    p = out_dir / 'report.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else None
