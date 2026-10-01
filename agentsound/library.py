"""Sample library manager: download, verify and unpack the packs listed in assets/samples/manifest.json.

    python -m agentsound samples                      # list the manifest (installed packs marked)
    python -m agentsound samples fetch ID [ID ...]    # download + unpack (+ convert FLAC/AIFF/OGG to WAV)
    python -m agentsound samples fetch --all [--genre jazz] [--category drums]

Packs land in assets/samples/<id>/ (gitignored; only the manifest is versioned; $AGENTSOUND_SAMPLES overrides the
folder, e.g. to share one download between git worktrees). Each installed pack gets a
SOURCE.json with url, license, attribution, sha256 and the fetch date: keep the attribution when a song
uses a CC-BY pack. In songs, reference them relative to the assets folder, e.g.
inst.sampler(dir='samples/<id>/...') or inst.sf2(file='samples/<id>/X.sf2', preset='...').

Manifest entry keys (strict):
  id, title, url, license, licenseUrl       required
  category, genres, attribution, size, sha256, format, notes, homepage
  archive   zip | tar | 7z | rar | file     default: from the url's extension ('file' = no unpacking)
  filename  name of the downloaded file      default: last url path segment
  convert   list of extensions to convert to 24-bit WAV (default ['flac', 'aif', 'aiff', 'ogg']; [] = none)
  keep      true keeps converted originals (default false: the WAV replaces them)
  nested    true also unpacks zip archives found inside the download (each into a folder of its name)
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# $AGENTSOUND_SAMPLES points worktrees / other checkouts at one shared sample folder (packs are large).
SAMPLES = Path(os.environ['AGENTSOUND_SAMPLES']).resolve() if os.environ.get('AGENTSOUND_SAMPLES') else     REPO / 'assets' / 'samples'
MANIFEST = SAMPLES / 'manifest.json'
CACHE = SAMPLES / '.downloads'

_REQUIRED = {'id', 'title', 'url', 'license', 'licenseUrl'}
_OPTIONAL = {'category', 'genres', 'attribution', 'size', 'sha256', 'format', 'notes', 'homepage',
             'archive', 'filename', 'convert', 'keep', 'nested'}
_ARCHIVES = {'zip', 'tar', '7z', 'rar', 'file'}
_DEFAULT_CONVERT = ['flac', 'aif', 'aiff', 'ogg']


class LibraryError(Exception):
    pass


# -------------------------------------------------------------------------------- manifest

def load_manifest(path: Path = MANIFEST) -> list[dict]:
    if not path.is_file():
        raise LibraryError(f"no manifest at {path}")
    data = json.loads(path.read_text(encoding='utf-8'))
    packs = data.get('packs') if isinstance(data, dict) else None
    if not isinstance(packs, list):
        raise LibraryError(f"{path}: expected {{\"packs\": [...]}}")
    seen = set()
    for i, p in enumerate(packs):
        where = f"{path.name}: packs[{i}]"
        if not isinstance(p, dict):
            raise LibraryError(f"{where}: not an object")
        missing = _REQUIRED - p.keys()
        unknown = p.keys() - _REQUIRED - _OPTIONAL
        if missing:
            raise LibraryError(f"{where}: missing {sorted(missing)}")
        if unknown:
            raise LibraryError(f"{where} ({p['id']}): unknown keys {sorted(unknown)}")
        if not p['id'].replace('-', '').replace('_', '').isalnum() or p['id'] != p['id'].lower():
            raise LibraryError(f"{where}: id '{p['id']}' must be lower-case [a-z0-9_-]")
        if p['id'] in seen:
            raise LibraryError(f"{where}: duplicate id '{p['id']}'")
        seen.add(p['id'])
        if p.get('archive', archive_kind(p)) not in _ARCHIVES:
            raise LibraryError(f"{where}: archive must be one of {sorted(_ARCHIVES)}")
    return packs


def archive_kind(pack: dict) -> str:
    if 'archive' in pack:
        return pack['archive']
    name = download_name(pack).lower()
    if name.endswith('.zip'):
        return 'zip'
    if name.endswith(('.tar', '.tar.gz', '.tgz', '.tar.xz', '.txz', '.tar.bz2', '.tbz2', '.tar.zst')):
        return 'tar'
    if name.endswith('.7z'):
        return '7z'
    if name.endswith('.rar'):
        return 'rar'
    return 'file'


def download_name(pack: dict) -> str:
    if pack.get('filename'):
        return pack['filename']
    tail = urllib.parse.unquote(urllib.parse.urlparse(pack['url']).path.rstrip('/').split('/')[-1])
    return tail or f"{pack['id']}.bin"


def pack_dir(pack: dict) -> Path:
    return SAMPLES / pack['id']


def installed(pack: dict) -> bool:
    return (pack_dir(pack) / 'SOURCE.json').is_file()


# -------------------------------------------------------------------------------- download

def _human(n: float | None) -> str:
    if not n:
        return '?'
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f"{n:.0f} {unit}" if unit in ('B', 'KB') else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def download(pack: dict, log=print, attempts: int = 25) -> Path:
    """Download (resumable) into assets/samples/.downloads/<id>/<file>; verify sha256 when pinned.

    Dropped connections and timeouts are retried (up to `attempts` times, with a growing pause), resuming
    with an HTTP Range request when the server supports it - large packs over a slow line need that."""
    dest_dir = CACHE / pack['id']
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / download_name(pack)
    part = dest.with_name(dest.name + '.part')
    if dest.is_file():
        log(f"  cached {dest.name} ({_human(dest.stat().st_size)})")
    else:
        for attempt in range(1, attempts + 1):
            try:
                if _download_once(pack, part, log, announce=attempt == 1):
                    break
            except (OSError, urllib.error.URLError, TimeoutError) as e:     # HTTPError is a URLError
                if isinstance(e, urllib.error.HTTPError) and e.code not in (408, 425, 429, 500, 502, 503, 504):
                    raise LibraryError(f"{pack['id']}: HTTP {e.code} for {pack['url']}") from e
                if attempt == attempts:
                    raise LibraryError(f"{pack['id']}: download failed after {attempts} attempts ({e}); "
                                       f"run fetch again to resume") from e
                have = part.stat().st_size if part.is_file() else 0
                log(f"    connection problem ({type(e).__name__}: {str(e)[:80]}); retry {attempt}/{attempts - 1} "
                    f"from {_human(have)}")
                time.sleep(min(60, 3 * attempt))
        part.replace(dest)
    digest = sha256_file(dest)
    if pack.get('sha256') and pack['sha256'].lower() != digest:
        raise LibraryError(f"{pack['id']}: sha256 mismatch (manifest {pack['sha256']}, file {digest}); "
                           f"delete {dest} and fetch again, or update the manifest if the upstream file changed")
    return dest


def _download_once(pack: dict, part: Path, log, announce: bool) -> bool:
    """One request: append to `part` (Range resume). True when complete, raises OSError on a short read."""
    have = part.stat().st_size if part.is_file() else 0
    req = urllib.request.Request(pack['url'], headers={'User-Agent': 'AgentSound-library/1.0'})
    if have:
        req.add_header('Range', f'bytes={have}-')
    try:
        resp = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:
        if e.code == 416 and have:          # range not satisfiable: we already have everything
            return True
        raise
    with resp:
        if have and resp.status != 206:     # server ignored the range: start over
            have = 0
        total = resp.headers.get('Content-Length')
        total = int(total) + have if total else None
        if announce:
            log(f"  downloading {part.name[:-5]} ({_human(total)}) from {urllib.parse.urlparse(pack['url']).netloc}")
        done, next_report = have, have + 64 * 2**20
        with open(part, 'ab' if have else 'wb') as f:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if done >= next_report:
                    pct = f" {100 * done / total:.0f}%" if total else ''
                    log(f"    {_human(done)}{pct}")
                    next_report += 64 * 2**20
        if total and done < total:
            raise OSError(f"short read: {done} of {total} bytes")
    return True


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# -------------------------------------------------------------------------------- unpack + convert

def _bsdtar() -> str | None:
    """libarchive's bsdtar reads zip/7z/rar/tar; Windows ships it as System32/tar.exe."""
    if os.name == 'nt':
        sys_tar = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32' / 'tar.exe'
        if sys_tar.is_file():
            return str(sys_tar)
    for name in ('bsdtar', '7z', '7za'):
        if shutil.which(name):
            return shutil.which(name)
    return None


def unpack(pack: dict, archive: Path, target: Path, log=print) -> None:
    kind = archive_kind(pack)
    target.mkdir(parents=True, exist_ok=True)
    if kind == 'file':
        shutil.copy2(archive, target / archive.name)
        return
    if kind == 'zip':
        import zipfile
        with zipfile.ZipFile(archive) as z:
            _check_members(pack, z.namelist())
            z.extractall(target)
        return
    if kind == 'tar' and not archive.name.endswith('.zst'):
        import tarfile
        with tarfile.open(archive) as t:
            _check_members(pack, t.getnames())
            t.extractall(target, filter='data')
        return
    tool = _bsdtar()
    if not tool:
        raise LibraryError(f"{pack['id']}: need bsdtar or 7z to unpack a {kind} archive")
    if Path(tool).stem.startswith('7z'):
        cmd = [tool, 'x', '-y', f'-o{target}', str(archive)]
    else:
        cmd = [tool, '-xf', str(archive), '-C', str(target)]
    proc = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
    if proc.returncode != 0:
        raise LibraryError(f"{pack['id']}: unpacking failed: {(proc.stderr or proc.stdout).strip()[:500]}")


def _check_members(pack: dict, names: list[str]) -> None:
    for n in names:
        p = n.replace('\\', '/')
        if p.strip('/') == '':          # a bare root entry ('/', Dropbox folder zips): nothing to extract
            continue
        if p.startswith('/') or '..' in p.split('/') or (len(p) > 1 and p[1] == ':'):
            raise LibraryError(f"{pack['id']}: archive member escapes the target folder: {n}")


def _flatten_single_root(target: Path) -> None:
    """An archive holding one top folder: move its content up (assets/samples/<id>/<files>)."""
    entries = [e for e in target.iterdir() if e.name not in ('SOURCE.json', '__MACOSX')]
    if len(entries) == 1 and entries[0].is_dir():
        inner = entries[0]
        tmp = target / ('.flatten-' + inner.name)
        inner.rename(tmp)
        for e in tmp.iterdir():
            e.rename(target / e.name)
        tmp.rmdir()
    _remove_junk(target)


_JUNK_FILES = {'.ds_store', 'thumbs.db', 'desktop.ini'}


def _remove_junk(target: Path) -> None:
    """macOS / Windows metadata that archives often carry: __MACOSX folders, AppleDouble '._x' files, .DS_Store."""
    for p in sorted(target.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        if p.is_dir() and p.name == '__MACOSX':
            shutil.rmtree(p, ignore_errors=True)
        elif p.is_file() and (p.name.startswith('._') or p.name.lower() in _JUNK_FILES):
            p.unlink()


def convert_audio(pack: dict, target: Path, log=print) -> int:
    exts = {e.lower().lstrip('.') for e in pack.get('convert', _DEFAULT_CONVERT)}
    if not exts:
        return 0
    files = [p for p in target.rglob('*') if p.is_file() and p.suffix.lower().lstrip('.') in exts]
    if not files:
        return 0
    from .cli import find_ffmpeg
    ff = find_ffmpeg()
    if not ff:
        raise LibraryError(f"{pack['id']}: {len(files)} {'/'.join(sorted(exts))} files need ffmpeg to convert to WAV")
    log(f"  converting {len(files)} files to WAV ({', '.join(sorted({f.suffix.lower() for f in files}))})")
    broken: list[str] = []
    for i, src in enumerate(files, 1):
        dst = src.with_suffix('.wav')
        if dst.exists():
            dst = src.with_name(src.stem + '.' + src.suffix.lower().lstrip('.') + '.wav')
        proc = subprocess.run([ff, '-v', 'error', '-y', '-i', str(src), '-map_metadata', '-1', '-c:a', 'pcm_s24le',
                               str(dst)], capture_output=True, text=True, errors='replace')
        if proc.returncode != 0:
            # A few corrupt files in a big library should not sink the pack: skip and record them (too many: fail).
            broken.append(src.relative_to(target).as_posix())
            dst.unlink(missing_ok=True)
            log(f"    unreadable, skipped: {src.name} ({proc.stderr.strip().splitlines()[-1][:120] if proc.stderr.strip() else '?'})")
            if len(broken) > max(3, len(files) // 100):
                raise LibraryError(f"{pack['id']}: ffmpeg failed on {len(broken)} files (e.g. {broken[0]}): "
                                   f"{proc.stderr.strip()[:300]}")
            continue
        if not pack.get('keep'):
            src.unlink()
        if i % 500 == 0:
            log(f"    {i}/{len(files)}")
    for b in broken:                        # unusable sources would only confuse the index and the importers
        (target / b).unlink(missing_ok=True)
    if broken:
        (target / 'CONVERT_SKIPPED.txt').write_text(''.join(b + chr(10) for b in broken), encoding='utf-8')
    return len(files) - len(broken)


# -------------------------------------------------------------------------------- commands

def fetch(pack: dict, force: bool = False, log=print) -> None:
    target = pack_dir(pack)
    if installed(pack) and not force:
        log(f"{pack['id']}: already installed ({target})")
        return
    log(f"{pack['id']}: {pack['title']} [{pack['license']}]")
    archive = download(pack, log)
    if target.exists():
        shutil.rmtree(target)
    unpack(pack, archive, target, log)
    if archive_kind(pack) != 'file':
        _flatten_single_root(target)
    if pack.get('nested'):
        import zipfile
        for inner in sorted(target.rglob('*.zip')):
            dest = inner.with_suffix('')
            if dest.exists() and not dest.is_dir():      # e.g. 'X.sfz.zip' next to 'X.sfz'
                dest = inner.with_name(inner.name.replace('.', '_'))
            with zipfile.ZipFile(inner) as z:
                _check_members(pack, z.namelist())
                z.extractall(dest)
            inner.unlink()
            log(f"  unpacked nested {inner.name}")
        _remove_junk(target)
    converted = convert_audio(pack, target, log)
    files = [p for p in target.rglob('*') if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    source = {k: pack[k] for k in ('id', 'title', 'url', 'license', 'licenseUrl', 'attribution', 'homepage')
              if k in pack}
    source.update({'sha256': sha256_file(archive), 'fetched': _dt.date.today().isoformat(),
                   'files': len(files), 'bytes': size, 'converted': converted})
    (target / 'SOURCE.json').write_text(json.dumps(source, indent=2) + '\n', encoding='utf-8')
    from .catalog import pack_index
    pack_index(target, rebuild=True)
    if not pack.get('sha256'):
        log(f"  sha256 {source['sha256']} (not pinned in the manifest yet)")
    log(f"  installed {len(files)} files, {_human(size)} -> {target.relative_to(REPO)}")


def select(packs: list[dict], ids: list[str], all_: bool, genre: str | None, category: str | None) -> list[dict]:
    by_id = {p['id']: p for p in packs}
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        raise LibraryError(f"unknown pack id(s): {', '.join(unknown)} (see `python -m agentsound samples`)")
    chosen = [by_id[i] for i in ids] if ids else (list(packs) if all_ or genre or category else [])
    if genre:
        chosen = [p for p in chosen if genre in p.get('genres', [])]
    if category:
        chosen = [p for p in chosen if p.get('category') == category]
    return chosen


def list_packs(packs: list[dict], genre: str | None = None, category: str | None = None, verbose: bool = False) -> str:
    rows = [p for p in packs if (not genre or genre in p.get('genres', [])) and
            (not category or p.get('category') == category)]
    lines = []
    total = 0
    for p in sorted(rows, key=lambda p: (p.get('category', ''), p['id'])):
        total += p.get('size') or 0
        mark = '*' if installed(p) else ' '
        lines.append(f"{mark} {p['id']:<28} {p.get('category', ''):<12} {_human(p.get('size')):>9}  {p['license']:<14} "
                     f"{p['title']}")
        if verbose:
            for k in ('genres', 'format', 'attribution', 'notes', 'url'):
                if p.get(k):
                    v = ', '.join(p[k]) if isinstance(p[k], list) else p[k]
                    lines.append(f"      {k}: {v}")
    lines.append(f"{len(rows)} packs, {_human(total)} total download; * = installed in assets/samples/<id>/")
    return '\n'.join(lines)
