"""GrandOrgue sample sets as 'sampler' instruments: pipe organs with their real attack, loop and release samples.

    inst.organ('samples/lars-palo-burea-church', stops=['Principal 8', 'Oktava 4'])          # Huvudverk plenum
    inst.organ('samples/lars-palo-burea-church', stops=['Gedakt 8'], manual='Svallverk', tremulant=True)
    inst.organ('samples/lars-palo-burea-church', stops=['Subbas 16', 'Principal 8'], manual='pedal')
    organ.stops(path) -> the manuals and their stops; python -m agentsound kit <organ folder>

A GrandOrgue sample set ('.organ' definition file + WAV / WavPack pipes, as the downloader unpacks a '.orgue'):
manuals hold stops; a stop holds pipes (inline or through ranks), one sample per key. Each pipe becomes zones of
the sampler: the attack + sustain loop (the loop points of the file's smpl chunk; the engine decodes WavPack
directly) and, when the file marks its release with a cue point, the release (trigger 'release': the real decay
into the church acoustics). Several stops layer (registration). Levels, per-pipe gains and tunings of the
definition file are applied. The expression param works as the swell pedal; tremulant=True (or a depth factor)
adds the wind tremulant (amplitude + slight pitch wobble, rate / depth from the definition's tremulant).

Notes outside a stop's compass (a bass line below the pedal's C2) play the pipe an octave inside the range
(extend='octave', the organist's way; 'stretch' transposes the pipe, 'none' leaves them silent).

Stops are chosen by name (case, spaces and foot marks ignored: 'Principal 8' finds "Principal 8'"); a name that
exists on several manuals takes `manual=` (name prefix or number), else the first manual (not the pedal) wins.
'manual: stop' picks per stop ('pedal: Subbas 16'). Unknown names list the organ's stops.
"""

from __future__ import annotations

import difflib
import os
import re
import struct
import unicodedata
from pathlib import Path

from .theory import ComposeError

__all__ = ['load', 'stops', 'describe', 'find_odf', 'format_info', 'sample_info']

_RELEASE_XFADE = 0.07     # s: sustain voice fade under the release sample
# stereo= modes -> zone channel mix of a stereo pipe. The Lars Palo sets are recorded with a spaced microphone pair:
# the phase between the two channels depends on the pipe (a low pipe can be near 180 degrees and cancel in mono);
# 'left' / 'right' take one microphone for both sides (mono, nothing cancels: pedal and bass lines).
_STEREO_MIX = {'asis': None, 'flip': [[0, 1, 0], [1, 0, -1]], 'left': [[0, 1, 1]], 'right': [[1, 1, 1]]}
_RELEASE_ATTACK = 0.025   # s: fade-in of the release sample (it starts mid-waveform)


# --------------------------------------------------------------------------------------------- ODF parsing

def _read_text(p: Path) -> str:
    raw = p.read_bytes()
    if raw.startswith(b'\xef\xbb\xbf'):
        return raw[3:].decode('utf-8', 'replace')
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('latin-1')


def _parse_ini(text: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    cur: dict[str, str] | None = None
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(';'):
            continue
        if s.startswith('[') and s.endswith(']'):
            cur = out.setdefault(s[1:-1].strip().lower(), {})
            continue
        if cur is not None and '=' in s:
            k, v = s.split('=', 1)
            cur[k.strip().lower()] = v.strip()
    return out


def _fold(text: str) -> str:
    t = unicodedata.normalize('NFKD', text)
    t = ''.join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"['`´’\"]", '', t)
    return re.sub(r'[^a-z0-9/]+', ' ', t).strip()


def find_odf(folder: Path, odf: str | None = None) -> Path | None:
    """The .organ definition file of a sample-set folder (odf: name substring; default: organindex.ini's first
    organ, else the shortest name)."""
    if folder.is_file():
        return folder if folder.suffix.lower() == '.organ' else None
    if not folder.is_dir():
        return None
    files = sorted(folder.glob('*.organ'), key=lambda p: (len(p.name), p.name))
    if not files:
        return None
    if odf:
        pick = [f for f in files if odf.lower() in f.name.lower()]
        if not pick:
            raise ComposeError(f"organ: no .organ file matching {odf!r} in {folder} ({', '.join(f.name for f in files)})")
        return pick[0]
    idx = folder / 'organindex.ini'
    if idx.is_file():
        ini = _parse_ini(_read_text(idx))
        first = ini.get('organ001', {}).get('filename')
        if first and (folder / first).is_file():
            return folder / first
    return files[0]


class _Organ:
    def __init__(self, odf: Path):
        self.odf = odf
        self.base = odf.parent
        self.s = _parse_ini(_read_text(odf))
        org = self.s.get('organ', {})
        self.name = org.get('churchname', odf.stem)
        self.gain_db = _db(org)
        self.manuals: list[dict] = []
        n = _int(org.get('numberofmanuals'), 1)
        first = 0 if org.get('haspedals', 'N').upper().startswith('Y') else 1
        for m in range(first, n + 1):
            sec = self.s.get(f'manual{m:03d}')
            if sec is None:
                continue
            stops = [_int(sec.get(f'stop{i:03d}'), 0) for i in range(1, _int(sec.get('numberofstops'), 0) + 1)]
            self.manuals.append({'index': m, 'name': sec.get('name', f'Manual {m}'), 'section': sec,
                                 'firstMidi': _int(sec.get('firstaccessiblekeymidinotenumber'), 36),
                                 'firstKey': _int(sec.get('firstaccessiblekeylogicalkeynumber'), 1),
                                 'keys': _int(sec.get('numberofaccessiblekeys'), 61),
                                 'stops': [s for s in stops if s > 0]})

    def stop(self, idx: int) -> dict:
        sec = self.s.get(f'stop{idx:03d}')
        if sec is None:
            raise ComposeError(f"organ {self.odf.name}: [Stop{idx:03d}] is missing")
        return sec

    def manual_of(self, idx: int) -> dict:
        return next(m for m in self.manuals if idx in m['stops'])

    def pipes(self, idx: int) -> list[dict]:
        """[{key, file, gain, tune, percussive, releases, loop, cue}] of a stop (REF / DUMMY resolved)."""
        sec = self.stop(idx)
        man = self.manual_of(idx)
        out: list[dict] = []
        stop_db = _db(sec)
        tune = _float(sec.get('pitchtuning'), 0.0)
        perc = sec.get('percussive', 'N').upper().startswith('Y')
        if 'pipe001' in sec or _int(sec.get('numberofranks'), 0) == 0:
            first_pipe = _int(sec.get('firstaccessiblepipelogicalpipenumber'), 1)
            first_key = _int(sec.get('firstaccessiblepipelogicalkeynumber'), 1)
            count = _int(sec.get('numberofaccessiblepipes'), _int(sec.get('numberoflogicalpipes'), 0))
            for i in range(count):
                p = first_pipe + i
                key = man['firstMidi'] + (first_key + i - man['firstKey'])
                pipe = self._pipe(sec, p, f"Stop{idx:03d}", 0)
                if pipe:
                    pipe.update(key=key, gain=pipe['gain'] + stop_db, tune=pipe['tune'] + tune,
                                percussive=pipe['percussive'] or perc)
                    out.append(pipe)
            return out
        first_key0 = _int(sec.get('firstaccessiblepipelogicalkeynumber'), 1)
        naccess = _int(sec.get('numberofaccessiblepipes'), man['keys'])
        for r in range(1, _int(sec.get('numberofranks'), 0) + 1):
            ridx = _int(sec.get(f'rank{r:03d}'), 0)
            rsec = self.s.get(f'rank{ridx:03d}')
            if rsec is None:
                continue
            rfirst = _int(sec.get(f'rank{r:03d}firstpipenumber'), 1)
            rcount = _int(sec.get(f'rank{r:03d}pipecount'), _int(rsec.get('numberoflogicalpipes'), 0) - rfirst + 1)
            rkey = _int(sec.get(f'rank{r:03d}firstaccessiblekeynumber'), first_key0)
            rank_db = _db(rsec)
            rperc = rsec.get('percussive', 'N').upper().startswith('Y')
            rtune = _float(rsec.get('pitchtuning'), 0.0)
            for i in range(min(rcount, naccess)):
                pipe = self._pipe(rsec, rfirst + i, f"Rank{ridx:03d}", 0)
                if pipe:
                    pipe.update(key=man['firstMidi'] + (rkey + i - man['firstKey']), gain=pipe['gain'] + stop_db + rank_db,
                                tune=pipe['tune'] + tune + rtune, percussive=pipe['percussive'] or perc or rperc)
                    out.append(pipe)
        return out

    def _pipe(self, sec: dict, p: int, where: str, depth: int) -> dict | None:
        k = f'pipe{p:03d}'
        v = sec.get(k)
        if not v or v.upper() == 'DUMMY':
            return None
        if v.upper().startswith('REF:'):
            if depth > 4:
                return None
            try:
                _, m, s, q = v.split(':')
                man = next(x for x in self.manuals if x['index'] == int(m))
                target = self.stop(man['stops'][int(s) - 1])
            except (ValueError, StopIteration, IndexError):
                raise ComposeError(f"organ {self.odf.name}: [{where}] {k}={v} does not resolve") from None
            ref = self._pipe(target, int(q), f"REF {v}", depth + 1)
            if ref:
                ref['gain'] += _db(sec, k)
            return ref
        path = self._file(v)
        if path is None:
            raise ComposeError(f"organ {self.odf.name}: [{where}] {k}: sample {v!r} not found under {self.base}")
        releases = []     # (file, MaxKeyPressTime ms; -1 = any length)
        for r in range(1, _int(sec.get(k + 'releasecount'), 0) + 1):
            rv = sec.get(f'{k}release{r:03d}')
            rp = self._file(rv) if rv else None
            if rp:
                releases.append((rp, _int(sec.get(f'{k}release{r:03d}maxkeypresstime'), -1)))
        return {'file': path, 'gain': _db(sec, k), 'tune': _float(sec.get(k + 'pitchtuning'), 0.0),
                'percussive': sec.get(k + 'percussive', 'N').upper().startswith('Y'), 'releases': releases,
                'loadRelease': sec.get(k + 'loadrelease', 'Y').upper().startswith('Y'),
                'cue': _int(sec.get(k + 'cuepoint'), -1)}

    def _file(self, rel: str) -> str | None:
        from .sfz import _FINDER
        return _FINDER.find(os.path.normpath(os.path.join(str(self.base), rel.replace('\\', '/'))))

    def tremulant(self) -> tuple[float, float]:
        """(rate Hz, depth fraction) of the first synthetic tremulant (defaults 6 Hz, 15 %)."""
        t = self.s.get('tremulant001', {})
        period = _float(t.get('period'), 160.0)
        depth = _float(t.get('ampmoddepth'), 15.0)
        return 1000.0 / max(period, 20.0), max(0.0, depth) / 100.0

    def listing(self) -> list[dict]:
        rows = []
        for m in self.manuals:
            for idx in m['stops']:
                sec = self.stop(idx)
                rows.append({'manual': m['name'], 'manualIndex': m['index'], 'stop': sec.get('name', f'Stop {idx}'),
                             'index': idx, 'percussive': sec.get('percussive', 'N').upper().startswith('Y')})
        return rows


def _int(v, default: int) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


def _float(v, default: float) -> float:
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return default


def _db(sec: dict, prefix: str = '') -> float:
    """AmplitudeLevel (percent) and Gain (dB) of a section / pipe -> dB."""
    import math
    amp = _float(sec.get(prefix + 'amplitudelevel'), 100.0)
    return 20.0 * math.log10(max(amp, 1e-3) / 100.0) + _float(sec.get(prefix + 'gain'), 0.0)


# --------------------------------------------------------------------------------------------- sample files

_INFO: dict[tuple, dict | None] = {}


def sample_info(path: str) -> dict | None:
    """frames / rate / channels / loop (start, end exclusive) / cue of a WAV or WavPack file (header data only)."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = (path, st.st_mtime_ns, st.st_size)
    if key in _INFO:
        return _INFO[key]
    with open(path, 'rb') as f:
        magic = f.read(4)
    if magic == b'wvpk':
        info = _wavpack_info(path)
    else:
        from .kits import wav_header
        h = wav_header(path)
        info = None if h is None else {'frames': h['frames'], 'rate': h['rate'], 'channels': h['channels'],
                                       'loop': h['loop'][:2] if h['loop'] else None, 'cue': h['cue']}
    _INFO[key] = info
    return info


def _wavpack_info(path: str) -> dict | None:
    rates = [6000, 8000, 9600, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000, 64000, 88200, 96000, 192000]
    out = {'frames': 0, 'rate': 0, 'channels': 0, 'loop': None, 'cue': None}
    size = os.path.getsize(path)
    riff = bytearray()
    with open(path, 'rb') as f:
        off, first, blocks = 0, True, []
        while off + 32 <= size:
            f.seek(off)
            h = f.read(32)
            if h[:4] != b'wvpk':
                break
            ck, ver, idx_u8, tot_u8, total, bidx, bsamp, flags = struct.unpack('<IHBBIIII', h[4:28])
            blocks.append((off, ck, bsamp, flags))
            if first:
                out['frames'] = total + (tot_u8 << 32) if total != 0xFFFFFFFF else 0
                sr = (flags >> 23) & 0xF
                out['rate'] = rates[sr] if sr < 15 else 0
                first = False
            off += 8 + ck
        for off, ck, _, _ in (blocks[:1] + blocks[-2:]) if len(blocks) > 2 else blocks:
            f.seek(off + 32)
            meta = f.read(ck - 24)
            p = 0
            while p + 2 <= len(meta):
                i, n = meta[p], meta[p + 1]
                p += 2
                if i & 0x80:
                    n += (meta[p] << 8) + (meta[p + 1] << 16)
                    p += 2
                ln = n * 2
                if (i & 0x3f) in (0x21, 0x22):
                    riff += meta[p:p + ln - (1 if i & 0x40 else 0)]
                p += ln
    if not out['frames']:
        out['frames'] = sum(b[2] for b in blocks if b[3] & 0x800)
    # the embedded RIFF chunks
    p = 12 if riff[:4] == b'RIFF' else 0
    while p + 8 <= len(riff):
        cid = bytes(riff[p:p + 4])
        n = struct.unpack('<I', riff[p + 4:p + 8])[0]
        if cid == b'data':
            p += 8
            if riff[p:p + 4] == b'RIFF':
                p += 12
            continue
        body = bytes(riff[p + 8:p + 8 + n])
        if cid == b'fmt ' and len(body) >= 8:
            out['channels'], out['rate'] = struct.unpack('<HI', body[2:8])
        elif cid in (b'smpl', b'cue '):
            from .kits import _parse_cue, _parse_smpl
            tmp: dict = {'loop': None, 'cue': None, 'unity': None}
            (_parse_smpl if cid == b'smpl' else _parse_cue)(body, tmp)
            if tmp['loop']:
                out['loop'] = tmp['loop'][:2]
            if tmp['cue'] is not None:
                out['cue'] = tmp['cue']
        p += 8 + n + (n & 1)
    return out


# --------------------------------------------------------------------------------------------- public

def _open(path, caller_file: str | None, odf: str | None) -> _Organ:
    from .kits import resolve
    root = resolve(path, caller_file, 'organ')
    f = find_odf(root, odf)
    if f is None:
        orgue = sorted(root.glob('*.orgue')) if root.is_dir() else []
        raise ComposeError(f"organ: no GrandOrgue definition (.organ) in {root}"
                           + (f" (only the packed {orgue[0].name}: the sample downloader unpacks it)" if orgue else ''))
    return _Organ(f)


def stops(path, caller_file: str | None = None, odf: str | None = None) -> list[dict]:
    """[{'manual', 'manualIndex', 'stop', 'index', 'percussive'}] of an organ sample set."""
    return _open(path, caller_file, odf).listing()


def _pick_manual(o: _Organ, text, where: str) -> dict:
    if isinstance(text, int) or (isinstance(text, str) and text.strip().isdigit()):
        m = next((x for x in o.manuals if x['index'] == int(text)), None)
        if m:
            return m
    elif isinstance(text, str):
        t = _fold(text)
        for cand in o.manuals:
            n = _fold(cand['name'])
            if n == t or n.startswith(t) or (t in ('pedal', 'ped', 'p') and cand['index'] == 0):
                return cand
        initials = [x for x in o.manuals if ''.join(w[0] for w in re.findall(r'[A-Z][a-z]*', x['name'])).lower() == t]
        if len(initials) == 1:
            return initials[0]
    raise ComposeError(f"{where}: no manual {text!r}; manuals: "
                       + ', '.join(f"{m['index']} {m['name']}" for m in o.manuals))


def _pick_stop(o: _Organ, query, manual, where: str) -> int:
    man = None
    q = query
    if isinstance(query, (tuple, list)) and len(query) == 2:
        man, q = _pick_manual(o, query[0], where), query[1]
    elif isinstance(query, str) and ':' in query:
        a, b = query.split(':', 1)
        man, q = _pick_manual(o, a.strip(), where), b
    elif manual is not None:
        man = _pick_manual(o, manual, where)
    if not isinstance(q, str) or not q.strip():
        raise ComposeError(f"{where}: a stop is a name like 'Principal 8' (or 'manual: name'), got {query!r}")
    t = _fold(q)
    rows = o.listing()
    pool = [r for r in rows if man is None or r['manualIndex'] == man['index']]
    exact = [r for r in pool if _fold(r['stop']) == t]
    part = exact or [r for r in pool if _fold(r['stop']).startswith(t)] or [r for r in pool if t in _fold(r['stop'])]
    if not part:
        close = difflib.get_close_matches(t, [_fold(r['stop']) for r in pool], n=6, cutoff=0.4)
        names = [f"{r['manual']}: {r['stop']}" for r in pool if _fold(r['stop']) in close] or \
                [f"{r['manual']}: {r['stop']}" for r in pool][:40]
        raise ComposeError(f"{where}: no stop {q!r}" + (f" on {man['name']}" if man else '')
                           + f"; {'close' if close else 'stops'}: {', '.join(names)}")
    if len({r['manualIndex'] for r in part}) > 1:
        non_pedal = [r for r in part if r['manualIndex'] != 0]
        first = min(r['manualIndex'] for r in non_pedal) if non_pedal else part[0]['manualIndex']
        part = [r for r in part if r['manualIndex'] == first]
    if len(part) > 1 and not exact:
        raise ComposeError(f"{where}: {q!r} matches several stops: "
                           + ', '.join(f"{r['manual']}: {r['stop']}" for r in part) + " (give the full name)")
    return part[0]['index']


def load(path, stops=None, *, manual=None, tremulant=False, release: bool = True, stereo: str = 'asis',
         extend: str = 'octave', odf: str | None = None, caller_file: str | None = None) -> tuple[list[dict], dict]:
    """(zones, info) of the chosen stops of a GrandOrgue sample set (module docstring). stereo: 'asis' (the
    recording), 'flip' (right channel inverted), 'left' / 'right' (one microphone on both sides: mono), or a dict
    {stop: mode} per stop (the others 'asis'). A spaced-pair recording puts some low pipes near 180 degrees between
    the channels (they cancel in mono: the report's low-end correlation turns negative); 'left' keeps a pedal / bass
    stop solid in mono."""
    o = _open(path, caller_file, odf)
    where = f"organ {o.odf.name}"
    if extend not in ('octave', 'stretch', 'none'):
        raise ComposeError(f"{where}: extend= must be 'octave', 'stretch' or 'none', got {extend!r}")
    modes = ('asis', 'flip', 'left', 'right')
    if isinstance(stereo, dict):
        bad = [v for v in stereo.values() if v not in modes]
        if bad or not stereo:
            raise ComposeError(f"{where}: stereo= per stop must map stop names to {' / '.join(modes)}, got {stereo!r}")
    elif stereo not in modes:
        raise ComposeError(f"{where}: stereo= must be 'asis', 'flip', 'left', 'right' or {{stop: mode}}, got {stereo!r}")
    if stops is None:
        raise ComposeError(f"{where}: choose stops=[...]; " + format_info(describe_organ(o)).split('\n', 1)[-1])
    if isinstance(stops, (str, tuple)):
        stops = [stops]
    if not stops:
        raise ComposeError(f"{where}: stops= is empty")
    if isinstance(tremulant, bool):
        trem = 1.0 if tremulant else 0.0
    elif isinstance(tremulant, (int, float)) and 0 <= tremulant <= 3:
        trem = float(tremulant)
    else:
        raise ComposeError(f"{where}: tremulant= must be True / False or a depth factor 0..3, got {tremulant!r}")
    chosen = []
    for q in stops:
        idx = _pick_stop(o, q, manual, where)
        if idx not in chosen:
            chosen.append(idx)
    stop_mode = {idx: stereo if isinstance(stereo, str) else 'asis' for idx in chosen}
    if isinstance(stereo, dict):
        for q, mode in stereo.items():
            idx = _pick_stop(o, q, manual, f"{where} stereo=")
            if idx not in chosen:
                raise ComposeError(f"{where}: stereo= names {q!r}, which is not one of the chosen stops")
            stop_mode[idx] = mode
    rate, depth = o.tremulant()
    zones: list[dict] = []
    names = []
    missing_loops = 0
    for idx in chosen:
        sec = o.stop(idx)
        man = o.manual_of(idx)
        names.append(f"{man['name']}: {sec.get('name', idx)}")
        first = len(zones)
        for p in o.pipes(idx):
            info = sample_info(p['file'])
            if not info or not info['frames']:
                raise ComposeError(f"{where}: pipe sample {p['file']} is not a readable WAV / WavPack file")
            key = p['key']
            if not 0 <= key <= 127:
                continue
            gain = round(p['gain'] + o.gain_db, 3)
            base = {'file': p['file'], 'lo': key, 'hi': key, 'root': key}
            mix = _STEREO_MIX[stop_mode[idx]]
            if mix and info['channels'] == 2:
                base['channels'] = mix
            if abs(gain) > 1e-6:
                base['gain'] = max(-144.0, min(48.0, gain))
            if abs(p['tune']) > 1e-6:
                base['tune'] = round(p['tune'], 3)
            loop = info['loop']
            cue = p['cue'] if p['cue'] >= 0 else info['cue']
            z = dict(base)
            in_file = bool(loop) and cue is not None and loop[1] <= cue < info['frames'] - 32 and p['loadRelease'] \
                and release
            rel_files = _pick_release(p['releases'], in_file) if release and loop and not p['percussive'] else []
            if p['percussive'] or not loop:
                if not p['percussive']:
                    missing_loops += 1
                z['release'] = 0.3
            elif in_file:
                z.update(loop='forward', end=int(cue), release=_RELEASE_XFADE)
            else:       # no release in the file: a separate release sample takes over, else the file's tail
                z.update(loop='sustain', release=_RELEASE_XFADE if rel_files or not release else 2.5)
            if trem > 0 and not p['percussive']:
                z['tremolo'] = [round(0.5 * 8.7 * depth * trem, 3), round(rate, 3), 0.0, 0.15]
                z['vibrato'] = [round(6.0 * depth / 0.15 * trem, 2) if depth > 0 else 0.0, round(rate, 3), 0.0, 0.15]
            zones.append(z)
            if not release or p['percussive'] or not loop:
                continue
            if z.get('end') is not None:
                r = dict(base)
                r.update(trigger='release', offset=int(cue), attack=_RELEASE_ATTACK, release=0.2)
                zones.append(r)
            for rf in rel_files:
                r = dict(base)
                r['file'] = rf
                r.update(trigger='release', attack=_RELEASE_ATTACK, release=0.2)
                ri = sample_info(rf)
                if 'channels' in r and not (ri and ri['channels'] == 2):
                    del r['channels']
                zones.append(r)
        if extend != 'none':
            zones += _extend(zones[first:], extend)
    info = {'kind': 'organ', 'organ': o.name, 'odf': str(o.odf), 'stops': names, 'zones': len(zones),
            'keys': sorted({z['lo'] for z in zones}), 'tremulant': trem, 'unlooped': missing_loops,
            'stereo': {n: stop_mode[i] for n, i in zip(names, chosen)},
            'extend': extend}
    return zones, info


def _pick_release(releases: list[tuple[str, int]], in_file: bool) -> list[str]:
    """The release sample(s) of a pipe to play on every note-off. Sets with several releases per pipe choose one by
    how long the key was held (MaxKeyPressTime: the short-note releases of 'MultipleReleases' definitions); the
    sampler plays every release zone it has, so one release is kept - the one for held notes: the pipe file's own
    release (in_file), else a release for any length, else the one for the longest key press."""
    if in_file or not releases:
        return []
    anylen = [f for f, t in releases if t <= 0]
    if anylen:
        return anylen[:1]
    return [max(releases, key=lambda r: r[1])[0]]


def _extend(stop_zones: list[dict], mode: str) -> list[dict]:
    """Keys outside a stop's compass: 'octave' plays the pipe an octave (or two) inside the range at its own pitch
    (what an organist does with a low bass line), 'stretch' transposes the nearest octave's pipe to the key."""
    by_key: dict[int, list[dict]] = {}
    for z in stop_zones:
        by_key.setdefault(z['lo'], []).append(z)
    if not by_key:
        return []
    lo, hi = min(by_key), max(by_key)
    out = []
    for k in range(0, 128):
        if k in by_key:
            continue
        src = k
        while src < lo:
            src += 12
        while src > hi:
            src -= 12
        if src not in by_key or not lo <= src <= hi:
            continue
        for z in by_key[src]:
            c = dict(z)
            c['lo'] = c['hi'] = k
            c['root'] = k if mode == 'octave' else src
            out.append(c)
    return out


def describe_organ(o: _Organ) -> dict:
    return {'kind': 'organ', 'organ': o.name, 'odf': str(o.odf),
            'odfs': sorted(p.name for p in o.base.glob('*.organ')),
            'manuals': [{'index': m['index'], 'name': m['name'], 'firstMidi': m['firstMidi'], 'keys': m['keys'],
                         'stops': [o.stop(i).get('name', str(i)) for i in m['stops']]} for m in o.manuals],
            'tremulant': dict(zip(('rate', 'depth'), o.tremulant()))}


def describe(path, caller_file: str | None = None, odf: str | None = None) -> dict:
    """Manuals and stops of an organ sample set."""
    return describe_organ(_open(path, caller_file, odf))


def format_info(info: dict) -> str:
    from .theory import note_name
    out = [f"organ: {info['organ']} ({os.path.basename(info['odf'])}"
           + (f"; other definitions: {', '.join(n for n in info['odfs'] if n != os.path.basename(info['odf']))}"
              if len(info.get('odfs', [])) > 1 else '') + ')']
    for m in info['manuals']:
        out.append(f"  manual {m['index']} {m['name']} ({note_name(m['firstMidi'])}-{note_name(m['firstMidi'] + m['keys'] - 1)}): "
                   + ', '.join(m['stops']))
    out.append(f"  tremulant {info['tremulant']['rate']:.2f} Hz; use: inst.organ('<path>', stops=['Principal 8', ...], "
               f"manual='...', tremulant=False)")
    return '\n'.join(out)
