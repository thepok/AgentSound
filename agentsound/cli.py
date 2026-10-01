"""Command line for composing agents.

    python -m agentsound build songs/<slug> [--section NAME | --from-beat X --to-beat Y] [--no-mp3] [--stems]
                                             [--profile default|synthwave|dreamwave|darksynth|jazz|classical|pop|rock|film]
    python -m agentsound check songs/<slug> [--profile P]   # compile + validate (engine too if built), no render
    python -m agentsound new <slug>                  # start songs/<slug>/song.py from the template
    python -m agentsound audition <patch> [--notes auto|arp|stab|rolling|roots|bass|riser|hit|phrase|chord|drums|...]
                                          [--profile P] [--out DIR]
    python -m agentsound patches [prefix] [-v]
    python -m agentsound params [type] [--json]      # engine instrument/effect parameter reference
    python -m agentsound dx7 [search]                # DX7 ROM voice names for inst.dx7('...')
    python -m agentsound sf2 [search] [--samples]    # SoundFont presets for inst.sf2('...') / raw samples for samplers
    python -m agentsound sfz FILE.sfz [--json] [--cc N=V] [--articulation A] [--pitch]   # an SFZ instrument for inst.sfz(...)
    python -m agentsound sfz --check [PACK ...]      # import every .sfz of the installed packs: ok / fragment / error
    python -m agentsound kit DIR [--json] [--map KEY=FILE] [--mic NAME=DB]   # drum-kit mapping of inst.kit(DIR);
                                                     # organ stops of inst.organ(DIR); --multisample: note names
    python -m agentsound zoom songs/<slug> --at 1:23.456 [--stem ID] [--section NAME] [--ms 40]
                                                     # sample-accurate waveform zoom PNG (also --sec X, --beat B)
    python -m agentsound compare songs/<slug> --ref <audio> [--ref-start 1:02 --ref-end 1:32] [--section chorus]
                                                     # loudness-matched comparison with a reference track:
                                                     # out/compare/<ref>/compare.json + compare.png + suggestions
    python -m agentsound mix songs/<slug> [--auto [--iterations 2] [--section NAME ...]] [--profile P] [--lead ID]
                                                     # the mix engineer (agentsound/mixer.py): findings + the plan
                                                     # from out/report.json; --auto renders, measures, adjusts and
                                                     # writes out/mixer/MIX.py (paste it into song.py)
    python -m agentsound master songs/<slug> [--ref X --ref-start --ref-end] [--section S]
                                             [--platform auto|streaming|loud|dynamic] [--render] [--check]
                                                     # the mastering engineer (agentsound/mastering.py): tonal eq,
                                                     # loudness, width, limiter -> out/master/master.json (+ the
                                                     # post-pass out/master/mastered.wav with --render)
    python -m agentsound catalog [SECTION ...] [--markdown]   # overview: engine modules, patches, DX7, SoundFonts,
                                                     # sample packs, recipes, profiles, python helpers
    python -m agentsound find WORD [WORD ...] [--in SECTION]   # search all of that at once
    python -m agentsound samples [--genre G] [--category C] [-v]   # sample packs of assets/samples/manifest.json
    python -m agentsound samples fetch ID [ID ...] | --all [--genre G] [--category C]   # download + unpack
    python -m agentsound voices [--json]             # Windows text-to-speech voices (agentsound.speech, vocoder)
    python -m agentsound speak "text" --out file.wav [--voice NAME] [--rate R] [--ssml]   # TTS to a WAV
    python -m agentsound makingof songs/<slug> [--script] [--preview] [--tts auto|breeze|sapi|none]
                                               [--song-length full|SECONDS] [--stills T,T,...]
                                                     # the making-of film: out/making-of.mp4 (the story from the
                                                     # song's files and players' logs, then the song visualized)

A song lives in songs/<slug>/song.py and defines build() -> Song (or a module-level `song`).
Analysis profile (the genre reference the report judges the mix against, docs/RENDER_FORMAT.md): a
module-level `ANALYSIS = {'profile': 'synthwave', 'loudness': [-12, -9]}` in song.py (both keys optional)
and/or --profile NAME (wins over the file) are written into the render JSON as "analysis". A module-level
`MIX = {...}` (agentsound.mixer: trims, section rides, ducks, eq dips) is applied at build / check time and printed.
Outputs go to songs/<slug>/out/: song.render.json, mix.wav, mix.mp3, report.json and the images listed
in report.json 'images' (overview, loudness, tracks, bands, stereo, spectrograms per section, clicks/), plus
credits.txt and cover.png; mix.mp3 carries ID3 tags and the cover (agentsound/delivery.py: song.py METADATA / COVER).
Engine: --engine PATH, else $AGENTSOUND_ENGINE, else <repo>/build/agentsound(.exe).
Exit codes: 0 ok, 1 song error, 2 engine rejected the render JSON, 3 engine missing, 4 engine failure.
"""

from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_ENGINE = REPO / 'build' / ('agentsound.exe' if os.name == 'nt' else 'agentsound')
FFMPEG_CANDIDATES = ('C:/Program Files (x86)/ffmpeg/bin/ffmpeg.exe', 'C:/Program Files/ffmpeg/bin/ffmpeg.exe')


class CliError(Exception):
    def __init__(self, msg: str, code: int = 1):
        super().__init__(msg)
        self.code = code


# -------------------------------------------------------------------------------- locations

def find_engine(explicit: str | None = None) -> Path:
    cand = explicit or os.environ.get('AGENTSOUND_ENGINE') or str(DEFAULT_ENGINE)
    p = Path(cand)
    if p.is_file():
        return p
    if os.name == 'nt' and p.suffix == '' and p.with_suffix('.exe').is_file():
        return p.with_suffix('.exe')
    where = 'from --engine' if explicit else 'from $AGENTSOUND_ENGINE' if os.environ.get('AGENTSOUND_ENGINE') else 'default'
    raise CliError(f"engine not found at {p} ({where}).\n"
                   f"  Build it:  cmake --preset release && cmake --build --preset release\n"
                   f"  or point to it with --engine PATH or the AGENTSOUND_ENGINE environment variable.", 3)


def find_ffmpeg() -> str | None:
    found = shutil.which('ffmpeg')
    if found:
        return found
    return next((c for c in FFMPEG_CANDIDATES if Path(c).is_file()), None)


def resolve_song(arg: str) -> Path:
    """songs/<slug>, a song.py path, or a bare slug -> path of song.py."""
    p = Path(arg)
    cands = [p, REPO / arg, REPO / 'songs' / arg]
    for c in cands:
        if c.is_file() and c.suffix == '.py':
            return c.resolve()
        if c.is_dir() and (c / 'song.py').is_file():
            return (c / 'song.py').resolve()
    raise CliError(f"no song at {arg!r}: expected a directory with song.py (e.g. songs/<slug>) or a .py file; "
                   f"start one with `python -m agentsound new <slug>`")


# ------------------------------------------------------------------------------------ songs

def _song_frame(tb, song_py: Path) -> str:
    """'file:line: code' of the deepest traceback frame inside the song file."""
    best = ''
    for fs in traceback.extract_tb(tb):
        try:
            if Path(fs.filename).resolve() == song_py:
                best = f"{song_py.name}:{fs.lineno}: {(fs.line or '').strip()}"
        except OSError:
            pass
    return best


def load_song(song_py: Path):
    """Import a song file and return its Song (build() or module-level `song`)."""
    return _load_song(song_py)[0]


def _load_song(song_py: Path):
    """(Song, the file's module-level ANALYSIS or None) of a song file."""
    from .song import Song
    from .theory import ComposeError
    name = 'agentsound_song_' + re.sub(r'\W', '_', song_py.parent.name)
    spec = importlib.util.spec_from_file_location(name, song_py)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(song_py.parent))
    try:
        spec.loader.exec_module(mod)
        if hasattr(mod, 'build'):
            song = mod.build()
        elif hasattr(mod, 'song'):
            song = mod.song
        else:
            raise CliError(f"{song_py} must define build() -> Song or a module-level `song`")
    except ComposeError as e:
        where = _song_frame(e.__traceback__, song_py)
        raise CliError(f"song error: {e}" + (f"\n  at {where}" if where else '')) from None
    except CliError:
        raise
    except Exception:
        raise CliError("the song code raised an exception:\n" + traceback.format_exc()) from None
    finally:
        try:
            sys.path.remove(str(song_py.parent))
        except ValueError:
            pass
    if not isinstance(song, Song):
        raise CliError(f"{song_py}: build() must return an agentsound.Song, got {type(song).__name__}")
    # Delivery settings (mp3 tags, cover), checked by agentsound.delivery at build / check time.
    song.delivery_settings = {'METADATA': getattr(mod, 'METADATA', None), 'COVER': getattr(mod, 'COVER', None),
                              'dir': song_py.parent}
    song.module_mix = getattr(mod, 'MIX', None)   # applied by apply_module_mix() (build / check), not here
    return song, getattr(mod, 'ANALYSIS', None)


def apply_module_mix(song) -> str | None:
    """Apply the song file's module-level MIX (agentsound.mixer) unless build() applied one itself; the line to print."""
    from . import mixer
    from .theory import ComposeError
    mod_mix = getattr(song, 'module_mix', None)
    if song.applied_mix is not None:
        return (f"mix       applied by build(): {mixer.describe_mix(song.applied_mix)}"
                + (" (module-level MIX ignored)" if mod_mix else ''))
    if not mod_mix:
        return None
    try:
        mixer.apply(song, mod_mix)
    except ComposeError as e:
        raise CliError(f"song error: {e}") from None
    return f"mix       MIX (song.py): {mixer.describe_mix(mod_mix)}"


# ------------------------------------------------------------------------- analysis profile

# The engine's analysis profiles (engine/analysis/Profiles.cpp); the engine validates them strictly too.
ANALYSIS_PROFILES = ('default', 'synthwave', 'dreamwave', 'darksynth', 'jazz', 'classical', 'piano', 'pop', 'rock',
                     'film')
_ANALYSIS_KEYS = ('profile', 'loudness')


def check_analysis(obj, where: str = 'ANALYSIS') -> dict:
    """Validate analysis settings ({'profile': name, 'loudness': [minLufs, maxLufs]}, both optional);
    returns a clean copy (loudness as floats) or raises CliError."""
    if not isinstance(obj, dict):
        raise CliError(f"{where} must be a dict like {{'profile': 'synthwave', 'loudness': [-12, -9]}}, got {obj!r}")
    extra = [k for k in obj if k not in _ANALYSIS_KEYS]
    if extra:
        raise CliError(f"{where}: unknown key(s) {', '.join(map(repr, extra))} (allowed: {', '.join(_ANALYSIS_KEYS)})")
    out: dict = {}
    if 'profile' in obj:
        prof = obj['profile']
        if prof not in ANALYSIS_PROFILES:
            close = difflib.get_close_matches(str(prof), ANALYSIS_PROFILES, n=1)
            raise CliError(f"{where}: unknown analysis profile {prof!r}" + (f" - did you mean {close[0]!r}?" if close else '') +
                           f" (profiles: {', '.join(ANALYSIS_PROFILES)})")
        out['profile'] = prof
    if 'loudness' in obj:
        lh = obj['loudness']
        ok = isinstance(lh, (list, tuple)) and len(lh) == 2 and all(
            isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in lh)
        if not ok or not -60 <= lh[0] < lh[1] <= 0:
            raise CliError(f"{where}: 'loudness' must be [minLufs, maxLufs] with -60 <= min < max <= 0, got {lh!r}")
        out['loudness'] = [float(lh[0]), float(lh[1])]
    return out


def apply_analysis(render: dict, song_analysis=None, profile: str | None = None, where: str = 'ANALYSIS') -> dict:
    """Merge analysis settings into the render dict's "analysis" object, key by key: what the song
    compiled (a later Song(analysis=...)) < the song file's ANALYSIS dict < --profile. Returns the
    settings written ({} = none: the engine uses profile 'default'). The compiler's own "silentNotes" (the
    compile-time silent notes, agentsound.silent_notes) are kept as they are; the song file cannot set them."""
    own = dict(render['analysis']) if isinstance(render.get('analysis'), dict) else render.get('analysis')
    compiler = {k: own.pop(k) for k in ('silentNotes', 'audioOnsets') if k in own} if isinstance(own, dict) else {}
    merged = check_analysis(own, 'render "analysis"') if own is not None else {}
    if song_analysis is not None:
        merged.update(check_analysis(song_analysis, where))
    if profile is not None:
        merged.update(check_analysis({'profile': profile}, '--profile'))
    if merged or compiler:
        render['analysis'] = {**merged, **compiler}
    else:
        render.pop('analysis', None)
    return merged


def hero_lines(song) -> list[str]:
    """What the hero wrapper did in the song (agentsound.heroes: sound, space, duck, carve, dips, rides, throws),
    and what the singer sang (agentsound.singer: voice, style, moves)."""
    from . import heroes, singer
    return [f"hero      {x}" for x in heroes.log_lines(song)] + [f"singer    {x}" for x in singer.log_lines(song)]


def compile_song(song, song_py: Path | None = None) -> dict:
    from .theory import ComposeError
    try:
        return song.compile()
    except ComposeError as e:
        raise CliError(f"song error: {e}") from None


def write_render(render: dict, path: Path) -> Path:
    from .song import dumps
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(render), encoding='utf-8')
    return path


# ----------------------------------------------------------------------------------- engine

_PATH_RE = re.compile(r'\$\.(?:(tracks|buses)\[(\d+)\]|master)(?:\.fx\[(\d+)\])?')


def explain_engine_error(msg: str, render: dict | None) -> str:
    """Name the node / effect behind JSON paths in an engine error ('$.tracks[3].fx[1]' ->
    "$.tracks[3].fx[1] (track 'pad', fx #1 'chorus')") so the message points back into the song."""
    if not render:
        return msg

    def sub(m: re.Match) -> str:
        kind, idx, fx_idx = m.groups()
        if kind is None:
            node, what = render.get('master') or {}, 'master'
        else:
            nodes = render.get(kind) or []
            if not 0 <= int(idx) < len(nodes):
                return m.group(0)
            node = nodes[int(idx)]
            what = f"{'track' if kind == 'tracks' else 'bus'} {node.get('id')!r}"
        chain = node.get('fx') or []
        if fx_idx is not None and 0 <= int(fx_idx) < len(chain):
            what += f", fx #{fx_idx} {chain[int(fx_idx)].get('type')!r}"
        return f"{m.group(0)} ({what})"
    return _PATH_RE.sub(sub, msg)


def run_engine(engine: Path, render_json: Path, out_dir: Path, from_beat=None, to_beat=None,
               render: dict | None = None) -> dict:
    cmd = [str(engine), 'render', str(render_json), '--out', str(out_dir)]
    if from_beat is not None:
        cmd += ['--from-beat', f"{from_beat:g}"]
    if to_beat is not None:
        cmd += ['--to-beat', f"{to_beat:g}"]
    cmd.append('--quiet')
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    except OSError as e:
        raise CliError(f"could not run the engine {engine}: {e}", 4) from None
    wall = time.perf_counter() - t0
    if proc.returncode != 0:
        msg = explain_engine_error((proc.stderr or proc.stdout or '').strip() or f"exit code {proc.returncode}", render)
        if proc.returncode == 2:
            raise CliError(f"the engine rejected {render_json.name}:\n  {msg}", 2)
        raise CliError(f"the engine failed (exit {proc.returncode}):\n  {msg}", 4)
    info: dict = {}
    for line in reversed((proc.stdout or '').strip().splitlines()):
        try:
            info = json.loads(line)
            break
        except ValueError:
            continue
    info.setdefault('wall', wall)
    err = '\n'.join(ln for ln in (proc.stderr or '').splitlines() if ln.strip() and not re.search(r'\d+%\s*$', ln))
    if err:
        info['stderr'] = err
    return info


def encode_mp3(wav: Path, mp3: Path) -> str:
    ff = find_ffmpeg()
    if ff is None:
        return 'mp3 skipped: ffmpeg not found (PATH or C:/Program Files (x86)/ffmpeg/bin)'
    if not wav.is_file():
        return f'mp3 skipped: {wav} missing'
    proc = subprocess.run([ff, '-y', '-hide_banner', '-loglevel', 'error', '-i', str(wav),
                           '-codec:a', 'libmp3lame', '-b:a', '320k', str(mp3)],
                          capture_output=True, text=True, encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        return f"mp3 failed: {(proc.stderr or '').strip()[:300]}"
    return f"mp3       {mp3}"


# ----------------------------------------------------------------------------------- report

_METRICS = [
    ('integrated', 'LUFS', ['integratedlufs', 'lufsintegrated', 'integrated', 'integratedloudness', 'lufs',
                            'loudnesslufs', 'loudness']),
    ('short-term max', 'LUFS', ['maxshorttermlufs', 'shorttermmaxlufs', 'maxshortterm', 'shorttermmax']),
    ('LRA', 'LU', ['lra', 'loudnessrange', 'lralu', 'loudnessrangelu']),
    ('true peak', 'dBTP', ['truepeakdbtp', 'truepeakdb', 'truepeak', 'dbtp']),
    ('sample peak', 'dBFS', ['samplepeakdbfs', 'peakdbfs', 'samplepeakdb', 'samplepeak', 'peakdb', 'peak']),
    ('RMS', 'dBFS', ['rmsdbfs', 'rmsdb', 'rms']),
    ('crest', 'dB', ['crestdb', 'crestfactordb', 'crest', 'crestfactor']),
    ('correlation', '', ['correlation', 'stereocorrelation', 'phasecorrelation']),
    ('width', '%', ['widthpct', 'width', 'stereowidth']),
]
_SUB = {'sections', 'tracks', 'stems', 'buses', 'nodes', 'timeline', 'reference', 'glossary', 'thirdoctave', 'space'}


def _norm(k) -> str:
    return re.sub(r'[^a-z0-9]', '', str(k).lower())


def _flatten(d, path=(), depth=0, skip=True) -> dict:
    out = {}
    if isinstance(d, dict) and depth < 4:
        for k, v in d.items():
            if skip and _norm(k) in _SUB:
                continue
            if isinstance(v, (dict,)):
                out.update(_flatten(v, path + (k,), depth + 1, skip))
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                out[path + (k,)] = v
    return out


def _pick(flat: dict, cands: list[str]):
    for c in cands:
        hits = [(len(p), p, v) for p, v in flat.items()
                if _norm(p[-1]) == c or (len(p) > 1 and _norm(p[-2]) + _norm(p[-1]) == c)]
        if hits:
            return min(hits, key=lambda h: h[0])[2]
    return None


def _metrics(d, labels=None) -> list[str]:
    flat = _flatten(d)
    out = []
    for label, unit, cands in _METRICS:
        if labels and label not in labels:
            continue
        v = _pick(flat, cands)
        if v is not None:
            out.append(f"{label} {v:.1f}{'' if unit == '%' else ' '}{unit}" if unit else f"{label} {v:.2f}")
    return out


def _items(x) -> list[tuple[str, dict]]:
    if isinstance(x, dict):
        return [(str(k), v) for k, v in x.items() if isinstance(v, dict)]
    if isinstance(x, list):
        out = []
        for i, v in enumerate(x):
            if isinstance(v, dict):
                name = v.get('name') or v.get('id') or v.get('section') or v.get('track') or f"#{i}"
                out.append((str(name), v))
        return out
    return []


def _warnings(report) -> list[str]:
    found = []

    def visit(d, depth):
        if not isinstance(d, dict) or depth > 2:
            return
        for k, v in d.items():
            if _norm(k) in ('warnings', 'issues', 'problems', 'hints') and isinstance(v, list):
                for w in v:
                    if isinstance(w, dict):
                        msg = w.get('message') or w.get('msg') or w.get('text') or json.dumps(w)
                        lvl = w.get('severity') or w.get('level')
                        code = w.get('code')
                        found.append((f"[{lvl}] " if lvl else '') + (f"{code}: " if code else '') + str(msg))
                    else:
                        found.append(str(w))
            elif isinstance(v, dict) and _norm(k) not in _SUB:
                visit(v, depth + 1)
    visit(report, 0)
    return found


def _click_lines(report: dict, limit: int = 8) -> list[str]:
    """'clicks' section of the summary: the worst detected clicks with time, bar/beat, part and image."""
    clicks = report.get('clicks')
    if not isinstance(clicks, list) or not clicks:
        return []
    ks = [k for k in clicks if isinstance(k, dict)]
    in_mix = sum(1 for k in ks if k.get('inMix', True))
    masked = len(ks) - in_mix
    g = report.get('global') if isinstance(report.get('global'), dict) else {}
    # The list is capped (worst 40); the global totals count every click.
    if isinstance(g.get('clicks'), int) and g['clicks'] >= in_mix:
        in_mix = g['clicks']
    if isinstance(g.get('clicksMasked'), int) and g['clicksMasked'] >= masked:
        masked = g['clicksMasked']
    head = f"  clicks ({in_mix} in the mix" + (f", {masked} masked in single parts" if masked else '') + "; worst first):"
    out = [head]
    for k in ks[:limit]:
        where = f"bar {k['bar']} beat {k['beat']:.2f}" if isinstance(k.get('bar'), int) and isinstance(k.get('beat'), (int, float)) else ''
        jump = f"jump {k['jumpDb']:.1f} dBFS" if isinstance(k.get('jumpDb'), (int, float)) else ''
        contrast = f"{k['contrastDb']:.0f} dB above context" if isinstance(k.get('contrastDb'), (int, float)) else ''
        parts = [str(k.get('time', k.get('sec', '?'))), where, repr(k['node']) if k.get('node') else '', jump, contrast,
                 f"[{k['severity']}]" if k.get('severity') else '', '' if k.get('inMix', True) else '(masked)', k.get('image', '')]
        out.append('    - ' + '  '.join(p for p in parts if p))
    shown = min(limit, len(ks))
    total = max(len(ks), in_mix + masked)
    if total > shown:
        out.append(f"    ... {total - shown} more" + (" in report.json" if total == len(ks) else f" (report.json lists the worst {len(ks)})"))
    return out


def _space_lines(report: dict) -> list[str]:
    """'space' section of the summary: the verdict (dry / narrow / ok / lush / washy), the numbers behind it
    (measured over the full sections) against the profile's targets, and the verdict per section."""
    sp = report.get('space')
    if not isinstance(sp, dict) or not isinstance(sp.get('verdict'), str):
        return []
    tg = sp.get('targets') if isinstance(sp.get('targets'), dict) else {}

    def num(key, fmt, target=None):
        v = sp.get(key)
        if not isinstance(v, (int, float)):
            return ''
        t = tg.get(target) if target else None
        rng = f" [{t[0]:g}..{t[1]:g}]" if isinstance(t, list) and len(t) == 2 else ''
        return fmt.format(v) + rng

    parts = [num('widthAbove150HzPct', 'width >150 Hz {:.0f}%', 'widthAbove150HzPct'),
             num('musicWidthPct', 'music {:.0f}%'),
             num('wetnessLu', 'reverb {:.1f} LU', 'wetnessLu') or ('no reverb return' if 'widthPct' in sp else ''),
             num('echoLu', 'echo {:.1f} LU'),
             num('bedVsLeadDb', 'bed {:+.1f} dB vs lead')]
    tails = sp.get('tails')
    if isinstance(tails, dict) and isinstance(tails.get('tailDb'), (int, float)):
        parts.append(f"tails {tails['tailDb']:.0f} dB")
    issues = [i for i in sp.get('issues', []) if isinstance(i, str)]
    head = f"  space: {sp['verdict']}" + (f" ({', '.join(issues)})" if issues else '')
    body = ' | '.join(p for p in parts if p)
    out = [head + (f" - {body}" if body else '')]
    secs = [s for s in sp.get('sections', []) if isinstance(s, dict) and 'section' in s]
    if len(secs) > 1:
        out.append('    per section: ' + ', '.join(f"{s['section']} {s.get('verdict', '?')}" + ('*' if s.get('full') else '')
                                                   for s in secs) + '  (* = full section, judged)')
    return out


def _dynamics_lines(report: dict, hide=()) -> list[str]:
    """'note dynamics' section of the summary: per track the 10-90 % spread of its note levels per phrase (median),
    FLAT under the profile's threshold, with the note count and the velocities it was given; parts that are even
    by design (arps, pulses, pads) on one line."""
    nodes = report.get('nodes')
    if not isinstance(nodes, list):
        return []
    judged, other = [], []
    thr = None
    for n in nodes:
        d = n.get('dynamics') if isinstance(n, dict) else None
        if not isinstance(d, dict) or n.get('id') in hide:
            continue
        thr = d.get('thresholdDb', thr)
        (judged if d.get('judged') else other).append((str(n.get('id', '?')), d))
    if not judged and not other:
        return []
    ref = report.get('reference') if isinstance(report.get('reference'), dict) else {}
    thr = ref.get('noteSpreadMinDb', thr)
    head = '  note dynamics (played note-to-note dynamics per phrase, 10-90 %'
    out = [head + (f"; flat under {thr:g} dB):" if isinstance(thr, (int, float)) else '):')]
    w = max((len(i) for i, _ in judged), default=8)
    for nid, d in judged:
        sp = d.get('dynamicsDb', d.get('phraseSpreadDb'))
        vel = d.get('velocity') if isinstance(d.get('velocity'), dict) else None
        extra = [f"{d.get('notes', '?')} notes" + (' (audio onsets)' if d.get('onsets') == 'audio' else '')]
        if vel:
            extra.append(f"vel {vel.get('min')}-{vel.get('max')}")
        if isinstance(d.get('phraseSpreadDb'), (int, float)) and isinstance(d.get('velocityPhraseDb'), (int, float)):
            extra.append(f"audio {d['phraseSpreadDb']:.1f} dB, from velocity {d['velocityPhraseDb']:.1f} dB")
        elif isinstance(d.get('spreadDb'), (int, float)):
            extra.append(f"song {d['spreadDb']:.1f} dB")
        if d.get('automatedDynamics'):
            extra.append('dynamics automated')
        if d.get('flatPhrases'):
            extra.append(f"{d['flatPhrases']}/{d.get('phrases', '?')} phrases flat")
        spt = f"{sp:5.1f} dB" if isinstance(sp, (int, float)) else '    - dB'
        flag = 'FLAT' if d.get('flat') else ('' if isinstance(sp, (int, float)) else '(too few notes)')
        out.append(f"    {nid:<{w}}  {str(d.get('kind', '?')):<7} {spt} {flag:<4}  ({', '.join(extra)})".rstrip())
    if other:
        out.append('    not judged: ' + ', '.join(f"{nid} ({d.get('kind', '?')} {d.get('spreadDb', 0):.1f} dB)" for nid, d in other))
    return out


def image_lines(report_path: Path, width: int = 200) -> list[str]:
    """The report's image list ('file: what it shows'); falls back to the PNGs found next to it."""
    rdir = Path(report_path).parent
    try:
        report = json.loads(Path(report_path).read_text(encoding='utf-8'))
        images = [(i['file'], i.get('shows', '')) for i in report.get('images', []) if isinstance(i, dict) and 'file' in i]
    except (OSError, ValueError, TypeError, AttributeError):
        images = []
    if not images:
        images = [(p.relative_to(rdir).as_posix(), '') for p in sorted(rdir.glob('*.png')) + sorted(rdir.glob('clicks/*.png'))]
    if not images:
        return []
    out = [f"images    {rdir}  (look at them; overview.png is the index)"]
    w = max(len(f) for f, _ in images)
    for f, shows in images:
        text = f"  {f:<{w}}  {shows}".rstrip()
        out.append(text if len(text) <= width else text[:width - 3] + '...')
    return out


def summarize_report(path: Path, max_tracks: int = 24, hide=()) -> str:
    """Compact human summary of report.json; tolerant of unknown / missing keys. Nodes in `hide`
    (the muted sidechain ghost tracks) are left out, with their 'silent' warnings."""
    hide = set(hide)
    try:
        report = json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return f"report    (none: {path} missing)"
    except ValueError as e:
        return f"report    unreadable ({e})"
    lines = [f"report    {path}"]
    if not isinstance(report, dict):
        return lines[0] + ' (unexpected format)'
    if isinstance(report.get('summary'), str):
        lines.append('  ' + report['summary'])
    else:
        m = _metrics(report)
        if m:
            lines.append('  mix: ' + ' | '.join(m))
    lines += _space_lines(report)
    for key in ('sections', 'nodes', 'tracks', 'stems', 'buses'):
        sub = next((v for k, v in report.items() if _norm(k) == key), None)
        items = [(n, d) for n, d in _items(sub) if n not in hide]
        if not items:
            continue
        lines.append(f"  {key}:")
        for name, d in items[:max_tracks]:
            mm = _metrics(d, {'integrated', 'short-term max', 'true peak', 'sample peak', 'RMS'})
            tag = ' (bus)' if d.get('bus') is True else ''
            lines.append(f"    {name + tag:<16} {' | '.join(mm) if mm else '(no metrics)'}")
        if len(items) > max_tracks:
            lines.append(f"    ... {len(items) - max_tracks} more")
    lines += _click_lines(report)
    lines += _dynamics_lines(report, hide)
    ws = [w for w in _warnings(report) if not any(f"'{h}'" in w and 'silent' in w for h in hide)]
    if ws:
        lines.append(f"  warnings ({len(ws)}):")
        lines += [f"    - {w}" for w in ws]
    sug = report.get('suggestions')
    if isinstance(sug, list) and sug:
        lines.append(f"  suggestions ({len(sug)}):")
        for x in sug:
            text = (x.get('message') or x.get('text') or json.dumps(x)) if isinstance(x, dict) else x
            lines.append(f"    - {text}")
    if len(lines) == 1:
        lines.append('  keys: ' + ', '.join(map(str, report)))
    return '\n'.join(lines)


# --------------------------------------------------------------------------------- commands

def delivery_settings(song) -> tuple[dict, dict | None]:
    """(METADATA, COVER) of a loaded song file, validated (COVER None = no cover)."""
    from . import delivery
    s = getattr(song, 'delivery_settings', None) or {}
    try:
        metadata, cover = delivery.check_metadata(s.get('METADATA')), delivery.check_cover(s.get('COVER'))
    except delivery.DeliveryError as e:
        raise CliError(str(e)) from None
    if cover and 'file' in cover:   # strict like every other file reference: a missing picture is an error up front
        src = Path(cover['file'])
        if not src.is_absolute() and s.get('dir') is not None:
            src = Path(s['dir']) / src
        if not src.is_file():
            raise CliError(f"COVER['file']: no image at {src}")
    return metadata, cover


def deliver_render(song, render: dict, engine: Path, out_dir: Path, rdir: Path, mp3: bool = True,
                   preview: str | None = None) -> list[str]:
    """credits.txt, cover.png and the tagged mp3 of a render (agentsound/delivery.py); returns summary lines."""
    from . import delivery
    metadata, cover = delivery_settings(song)
    lines = []
    credits = delivery.collect_credits(render)
    artist = metadata.get('artist', delivery.DEFAULT_ARTIST)
    title = metadata.get('title', song.title)
    (rdir / 'credits.txt').write_text(delivery.credits_text(credits, title, artist), encoding='utf-8')
    n = len(credits['sources'])
    lines.append(f"credits   {rdir / 'credits.txt'}  ({n} sample pack/SoundFont/IR source{'s' if n != 1 else ''})")
    for w in credits['warnings']:
        lines.append(f"  warning: {w}")
    if credits['attributions']:
        lines.append(f"  attributions required when publishing (CC-BY / BY-SA / BY-NC: {len(credits['attributions'])}, "
                     f"see credits.txt): " + '; '.join(credits['attributions']))

    profile = (render.get('analysis') or {}).get('profile')
    cover_png = None
    # The style also picks the default genre tag, with or without a cover (COVER = False).
    spec = delivery.cover_spec(song.title, song.seed, metadata, cover if cover is not None else {}, profile)
    style = spec.get('style', 'synthwave')
    if cover is None or 'file' in spec:   # no generated cover: a cover.png of an earlier build would be stale
        for stale in (out_dir / 'cover.png', out_dir / 'cover.json'):
            stale.unlink(missing_ok=True)
    if cover is not None:
        try:
            cover_png = delivery.make_cover(engine, spec, out_dir / 'cover.png', getattr(song, 'delivery_settings', {}).get('dir'))
            lines.append(f"cover     {cover_png}  ({'own image' if 'file' in spec else spec['style'] + ' style'})")
        except delivery.DeliveryError as e:
            lines.append(f"  warning: {e}")
    if not mp3:
        return lines
    ff = find_ffmpeg()
    if ff is None:
        return lines + ['mp3 skipped: ffmpeg not found (PATH or C:/Program Files (x86)/ffmpeg/bin)']
    # A section / range preview says so in its title (also when METADATA sets the title).
    tag_map = delivery.tags(title, song.tempo, song.key,
                            dict(metadata, title=title + (f" ({preview})" if preview else '')), style, credits['comment'],
                            profile)
    ok, err = delivery.encode_mp3(ff, rdir / 'mix.wav', rdir / 'mix.mp3', tag_map, cover_png)
    if not ok and cover_png is not None:   # an unreadable cover must not cost the mp3
        lines.append(f"  warning: embedding the cover failed ({err}); mp3 written without it")
        ok, err = delivery.encode_mp3(ff, rdir / 'mix.wav', rdir / 'mix.mp3', tag_map, None)
        cover_png = None
    if not ok:
        return lines + [f"mp3 failed: {err}"]
    lines.append(f"mp3       {rdir / 'mix.mp3'}  (tags: '{tag_map['title']}' by {tag_map['artist']}, {tag_map['genre']}, "
                 f"{tag_map['TBPM']} BPM{', key ' + tag_map['TKEY'] if 'TKEY' in tag_map else ''}"
                 f"{', cover' if cover_png else ''})")
    return lines


def _render_and_report(song, render: dict, out_dir: Path, json_name: str, args, from_beat=None, to_beat=None,
                       render_dir: Path | None = None, deliver: bool = False) -> int:
    from . import tempo as _tempo
    rj = write_render(render, out_dir / json_name)
    tempo = '' if 'tempoMap' not in render else \
        f", tempo map {min(p[1] for p in render['tempoMap']):g}..{max(p[1] for p in render['tempoMap']):g} BPM"
    print(f"render    {rj}  ({sum(len(t['notes']) for t in render['tracks'])} notes, {len(render['tracks'])} tracks, "
          f"{len(render['buses'])} buses, {_tempo.render_seconds(render, render['lengthBeats']):.1f} s{tempo})")
    # the compile-time silent notes come back in full as the report's 'silent_notes' warnings (with what the
    # render measured): one line here
    silent = (render.get('analysis') or {}).get('silentNotes') or []
    for w in song.warnings:
        if not (silent and w.startswith('silent notes: ')):
            print(f"  warning: {w}")
    if silent:
        print(f"  warning: silent notes: {sum(f['count'] for f in silent)} notes on "
              f"{', '.join(sorted({repr(f['track']) for f in silent}))} can't sound (no sample / layer): see the "
              f"report's silent_notes warnings below")
    for line in hero_lines(song):
        print(line)
    a = {k: v for k, v in (render.get('analysis') or {}).items() if k not in ('silentNotes', 'audioOnsets')}
    if a:
        print(f"analysis  profile {a.get('profile', 'default')!r}" +
              (f", loudness target {a['loudness'][0]:g}..{a['loudness'][1]:g} LUFS" if 'loudness' in a else ''))
    engine = find_engine(args.engine)
    rdir = render_dir or out_dir
    info = run_engine(engine, rj, rdir, from_beat, to_beat, render)
    secs, rsecs = info.get('seconds'), info.get('renderSeconds', info.get('wall'))
    print(f"rendered  {rdir / 'mix.wav'}" + (f"  ({secs:.1f} s audio in {rsecs:.1f} s)" if isinstance(secs, (int, float))
                                              and isinstance(rsecs, (int, float)) else ''))
    if info.get('stderr'):
        print('  engine: ' + info['stderr'].replace('\n', '\n  engine: '))
    if deliver:
        for line in deliver_render(song, render, engine, out_dir, rdir, mp3=not args.no_mp3,
                                   preview=None if rdir == out_dir else rdir.name):
            print(line)
    elif not args.no_mp3:
        print(encode_mp3(rdir / 'mix.wav', rdir / 'mix.mp3'))
    for line in image_lines(rdir / 'report.json'):
        print(line)
    print(summarize_report(rdir / 'report.json', hide=getattr(song, '_ghosts', {})))
    from . import singer
    for line in singer.report_lines(song, rdir / 'report.json'):
        print(line)
    return 0


def cmd_build(args) -> int:
    song_py = resolve_song(args.song)
    song, song_analysis = _load_song(song_py)
    line = apply_module_mix(song)
    if line:
        print(line)
    if args.stems:
        song.export(stems=True)
    render = compile_song(song, song_py)
    apply_analysis(render, song_analysis, args.profile, f"{song_py.name}: ANALYSIS")
    out_dir = Path(args.out) if args.out else song_py.parent / 'out'
    from_beat, to_beat, rdir = args.from_beat, args.to_beat, None
    if args.section:
        from .theory import ComposeError
        try:
            sec = song[args.section]
        except ComposeError as e:
            raise CliError(str(e)) from None
        from_beat, to_beat = sec.start, sec.end
        rdir = out_dir / 'sections' / re.sub(r'[^A-Za-z0-9_-]+', '_', sec.name)
        print(f"section   {sec.name}: beats {sec.start:g}-{sec.end:g}")
    elif from_beat is not None or to_beat is not None:
        rdir = out_dir / f"range_{from_beat or 0:g}_{to_beat if to_beat is not None else 'end'}"
    delivery_settings(song)   # METADATA / COVER errors before the render
    return _render_and_report(song, render, out_dir, 'song.render.json', args, from_beat, to_beat, rdir, deliver=True)


def cmd_check(args) -> int:
    song_py = resolve_song(args.song)
    song, song_analysis = _load_song(song_py)
    line = apply_module_mix(song)
    if line:
        print(line)
    delivery_settings(song)
    render = compile_song(song, song_py)
    apply_analysis(render, song_analysis, args.profile, f"{song_py.name}: ANALYSIS")
    rj = write_render(render, (Path(args.out) if args.out else song_py.parent / 'out') / 'song.render.json')
    print(song.describe())
    for w in song.warnings:
        print(f"  warning: {w}")
    for line in hero_lines(song):
        print(line)
    # The engine's own strict validation (param names, ranges, enum values) without rendering.
    try:
        engine = find_engine(args.engine)
    except CliError as e:
        print(f"ok: {rj} ({sum(len(t['notes']) for t in render['tracks'])} notes; "
              f"engine validation skipped: {str(e).splitlines()[0]})")
        return 0
    try:
        proc = subprocess.run([str(engine), 'validate', str(rj)], capture_output=True, text=True,
                              encoding='utf-8', errors='replace')
    except OSError as e:
        raise CliError(f"could not run the engine {engine}: {e}", 4) from None
    if proc.returncode != 0:
        msg = (proc.stderr or '').strip() or (proc.stdout or '').strip() or f"exit code {proc.returncode}"
        msg = explain_engine_error(msg, render)
        if proc.returncode == 2:
            raise CliError(f"the engine rejected {rj.name}:\n  {msg}", 2)
        raise CliError(f"engine validation failed (exit {proc.returncode}):\n  {msg}", 4)
    print(f"ok: {rj} ({sum(len(t['notes']) for t in render['tracks'])} notes; engine validation passed)")
    return 0


def cmd_new(args) -> int:
    slug = args.slug
    if not re.match(r'^[a-z0-9_-]+$', slug):
        raise CliError(f"slug {slug!r} must match [a-z0-9_-]+")
    dst = REPO / 'songs' / slug / 'song.py'
    if dst.exists():
        raise CliError(f"{dst} already exists")
    src = REPO / 'songs' / '_template' / 'song.py'
    dst.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding='utf-8').replace("'Template'", repr(slug.replace('-', ' ').replace('_', ' ').title()))
    dst.write_text(text, encoding='utf-8')
    print(f"created {dst}\nbuild:  python -m agentsound build songs/{slug}")
    return 0


# Audition material (4 bars over i VI III VII in the audition key), by canonical name:
AUDITION_MATERIAL = {
    'arp': '16th arpeggio, 2 octaves up and down (arps, plucks, marimba, sequences)',
    'stab': "syncopated chord stabs, 3-3-2 8ths played as 16ths (stabs)",
    'bass': '8th-note root/octave pulse (basses)',
    'rolling': '16th-note root/octave bass (rolling basses)',
    'roots': 'held whole-bar roots (sub and Moog basses)',
    'riser': "one long note with the patch's intended automation (risers, downlifters, sweeps)",
    'hit': 'single hits on bars 1 and 3 (impacts, booms, lasers)',
    'phrase': 'a 4-bar melody (leads, bells, anything else)',
    'chord': 'held 4-note chords (pads, strings, keys, organ, brass)',
    'drums': 'a 3-bar groove, a fill and a crash (kits)',
}
# Other --notes names (patch categories) -> material.
AUDITION_ALIASES = {
    'arps': 'arp', 'pluck': 'arp', 'plucks': 'arp', 'marimba': 'arp', 'seq': 'arp', 'sequence': 'arp',
    'stabs': 'stab', 'pulse': 'bass', 'sub': 'roots', 'moog': 'roots', 'held': 'roots',
    'downlifter': 'riser', 'uplifter': 'riser', 'sweep': 'riser', 'impact': 'hit', 'hits': 'hit', 'boom': 'hit',
    'lead': 'phrase', 'melody': 'phrase', 'pad': 'chord', 'pads': 'chord', 'chords': 'chord', 'groove': 'drums',
}
_AUDITION_HINT_KEYS = ('notes', 'automate', 'pitch', 'length', 'octave')


def audition_material(name: str) -> str:
    """Canonical material for a --notes name (material or patch category), or CliError."""
    n = str(name).lower()
    if n in AUDITION_MATERIAL:
        return n
    if n in AUDITION_ALIASES:
        return AUDITION_ALIASES[n]
    names = list(AUDITION_MATERIAL) + list(AUDITION_ALIASES)
    close = difflib.get_close_matches(n, names, n=1)
    raise CliError(f"unknown --notes {name!r}" + (f" - did you mean {close[0]!r}?" if close else '') +
                   f"; use auto or one of {', '.join(AUDITION_MATERIAL)} (also: {', '.join(AUDITION_ALIASES)})")


def _has(n: str, *words) -> bool:
    """Any of `words` in the name; the short ambiguous ones must start a word of the name, so 'hit'
    does not match 'white_noise', 'arp' not 'harp', 'kit' not 'skittle' (other words: substrings, e.g.
    'minimoog_bass', 'hihat')."""
    return any((re.search(r'(?:^|[^a-z])' + w, n) if w in _WORD_START else w in n) for w in words)


_WORD_START = frozenset({'hit', 'arp', 'kit', 'seq', 'zap', 'perc', 'boom'})


def _guess_kind(p) -> str:
    """Natural audition material for a patch from its name (and instrument type)."""
    n = p.name.lower().rsplit('/', 1)[-1]
    t = p.instrument.type if p.instrument else ''
    if t == 'drums' or _has(n, 'drum', 'kit', 'perc', 'kick', 'snare', 'hat'):
        return 'drums'
    if _has(n, 'riser', 'lifter', 'whoosh', 'noise_sweep'):
        return 'riser'
    if _has(n, 'impact', 'boom', 'hit', 'laser', 'zap'):
        return 'hit'
    if 'bass' in n:
        if 'rolling' in n:
            return 'rolling'
        if _has(n, 'sub', 'moog'):
            return 'roots'
        return 'bass'
    if 'stab' in n:
        return 'stab'
    if _has(n, 'arp', 'pluck', 'marimba', 'mallet', 'seq'):
        return 'arp'
    if 'lead' in n:
        return 'phrase'
    if _has(n, 'pad', 'string', 'chord', 'keys', 'piano', 'organ', 'choir', 'brass'):
        return 'chord'
    return 'phrase'


def audition_hint(p) -> dict:
    """The patch's optional audition hint (Patch(..., audition={...})), validated: 'notes' (material
    name), 'automate' ({target: points}, beats from the audition start), 'pitch' (MIDI or note name,
    riser/hit), 'length' (beats of the riser note / each hit), 'octave' (the phrase's octave, default 4 = B4-B5; the
    chord and arp registers move with it: 2 = a phrase B2-B3 for a bassoon, tuba or bass trombone)."""
    h = getattr(p, 'audition', None)
    if not h:
        return {}
    where = f"patch {p.name!r} audition hint"
    if not isinstance(h, dict):
        raise CliError(f"{where} must be a dict, got {h!r}")
    extra = [k for k in h if k not in _AUDITION_HINT_KEYS]
    if extra:
        raise CliError(f"{where}: unknown key(s) {', '.join(map(repr, extra))} (allowed: {', '.join(_AUDITION_HINT_KEYS)})")
    out = dict(h)
    if 'notes' in out:
        out['notes'] = audition_material(out['notes'])
    auto = out.get('automate')
    if auto is not None and (not isinstance(auto, dict) or not all(isinstance(k, str) and isinstance(v, (list, tuple))
                                                                  for k, v in auto.items())):
        raise CliError(f"{where}: 'automate' must be {{target: [[beat, value], [beat, value, curve], ...]}}, got {auto!r}")
    length = out.get('length')
    if length is not None and (isinstance(length, bool) or not isinstance(length, (int, float)) or not 0 < length <= 16):
        raise CliError(f"{where}: 'length' must be beats in (0, 16], got {length!r}")
    octave = out.get('octave')
    if octave is not None and (isinstance(octave, bool) or not isinstance(octave, int) or not 0 <= octave <= 7):
        raise CliError(f"{where}: 'octave' must be an int 0..7 (the phrase octave, default 4), got {octave!r}")
    return out


# 'instrument.cutoff  riser(drop, length=L, lo=300, hi=12000)' lines in a patch's notes.
_RISER_NOTE_RE = re.compile(r'\b((?:instrument|fx)\.[A-Za-z0-9_.]+|gainDb)[ \t]+riser\([^)]*?\blo=(-?[\d.]+)[^)]*?\bhi=(-?[\d.]+)')


def riser_automation_from_notes(notes: str, length: float) -> dict:
    """The automation a riser patch's notes prescribe ('<target>  riser(..., lo=A, hi=B)'), as
    {target: points} ramping lo -> hi over `length` beats ('exp' when both ends are > 0)."""
    out: dict = {}
    for target, lo, hi in _RISER_NOTE_RE.findall(notes or ''):
        if target in out:
            continue
        a, b = float(lo), float(hi)
        out[target] = [[0.0, a], [float(length), b] + (['exp'] if a > 0 and b > 0 else [])]
    return out


def audition_song(patch_name: str, notes: str = 'auto', tempo: float = 100.0, key: str = 'A minor'):
    """A 4-bar song playing `patch_name` with material that suits it (AUDITION_MATERIAL): chosen from
    the patch's audition hint, else its name (auto), or forced with `notes` (a material or alias)."""
    from . import patches
    from .patches import FX
    from .patterns import arp, bassline, chords, crash, drums, snare_roll, tom_fill
    from .song import Song
    from .theory import note as note_pitch
    p = patches.get(patch_name)
    if p.instrument is None:
        raise CliError(f"patch {patch_name!r} is an fx chain; audition needs an instrument patch")
    hint = audition_hint(p)
    kind = (hint.get('notes') or _guess_kind(p)) if notes == 'auto' else audition_material(notes)
    s = Song(f"audition {patch_name}", tempo=tempo, key=key, seed=1, tail=6.0)
    sec = s.section('audition', bars=4)
    for bus_id in p.sends:
        b = bus_id.lower()
        if any(w in b for w in ('echo', 'delay', 'dly')):
            s.echo(bus_id)
        elif any(w in b for w in ('gate',)):
            s.gated(bus_id)
        elif any(w in b for w in ('plate', 'room')):
            s.plate(bus_id)
        else:
            s.hall(bus_id)
    t = s.track('patch', p)
    if any(f.type == 'vocoder' for f in t.fx):  # a vocoder patch needs a voice to key it (the modulator)
        from . import speech
        speech.audition_voice(s, t, sec, cache_dir=REPO / 'auditions' / '_speech')
    prog = s.prog('i VI III VII')
    shift = 12 * (int(hint.get('octave', 4)) - 4)    # the register of phrase / chord / arp material
    if kind == 'drums':
        beat = drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.xo',
                      'ohh': '..............x.'})
        t.play(beat, 0, times=3).play(beat.slice(0, 2) + tom_fill(1) + snare_roll(1), sec.bar(3))
        t.play(crash(), sec)
    elif kind == 'bass':
        t.play(bassline(prog, 'octave', rate='1/8'), sec)
    elif kind == 'rolling':
        t.play(bassline(prog, 'octave', rate='1/16'), sec)
    elif kind == 'roots':
        t.play(bassline(prog, 'root'), sec)                       # one held root per bar
    elif kind == 'chord':
        t.play(chords(prog, voicing='smooth', register=(52 + shift, 76 + shift), gate=0.95), sec)
    elif kind == 'stab':
        t.play(chords(prog, voicing='close', register=(55, 76), voices=3, vel=104, rhythm='x..x..x.', gate=0.5), sec)
    elif kind == 'arp':
        t.play(arp(prog, 'updown', rate='1/16', octaves=2, register=(57 + shift, 76 + shift)), sec)
    elif kind == 'phrase':
        m = s.motif('5:1/4 8:1/4 7:1/8 5:1/8 3:1/4 | 4:1/8 5:1/8 3:1/4 2:1/2 '
                    '| 5:1/4 8:1/4 9:1/8 8:1/8 7:1/4 | 8:1/2. r:1/4')   # exactly 4 bars
        t.play(m.clip(octave=4 + shift // 12, vel=100), sec)
    elif kind in ('riser', 'hit'):
        try:
            pitch = note_pitch(hint['pitch']) if 'pitch' in hint else None
        except Exception as e:
            raise CliError(f"patch {patch_name!r} audition hint: bad 'pitch' {hint['pitch']!r} ({e})") from None
        if kind == 'riser':   # one note over the whole audition (4 bars), ending on the downbeat after it
            length = float(hint.get('length', sec.length))
            t.note(pitch if pitch is not None else s.key.degree(1, octave=3), sec.start, length, vel=100)
            if 'automate' not in hint:
                for target, pts in riser_automation_from_notes(p.notes, length).items():
                    t.automate(target, pts)
        else:                 # single hits on bars 1 and 3: booms at the key root in octave 1, lasers/zaps up high
            high = _has(p.name.lower(), 'laser', 'zap')
            pitch = pitch if pitch is not None else s.key.degree(1, octave=5 if high else 1)
            length = float(hint.get('length', 0.5 if high else 2.0))
            for bar in (0, 2):
                t.note(pitch, sec.bar(bar), length, vel=120)
    else:
        raise CliError(f"unknown audition material {kind!r}; use one of {', '.join(AUDITION_MATERIAL)}")
    for target, pts in (hint.get('automate') or {}).items():
        t.automate(target, [list(pt) for pt in pts])
    if patches.has('master/audition'):
        s.master.use('master/audition')
    else:
        s.master.add(FX('limiter'))
    return s


def cmd_audition(args) -> int:
    from .theory import ComposeError
    try:
        song = audition_song(args.patch, args.notes, args.tempo, args.key)
        render = song.compile()
    except ComposeError as e:
        raise CliError(str(e)) from None
    apply_analysis(render, None, args.profile)
    slug = re.sub(r'[^a-z0-9_-]+', '_', args.patch.lower()).strip('_')
    out_dir = Path(args.out) if args.out else REPO / 'auditions' / slug
    return _render_and_report(song, render, out_dir, 'audition.render.json', args)


def cmd_patches(args) -> int:
    from . import patches
    names = patches.list(args.prefix or '')
    if not names:
        print(f"no patches{' under ' + repr(args.prefix) if args.prefix else ''} "
              f"(the sound library lives in agentsound/patches/*.py)")
        return 0
    for n in names:
        p = patches.get(n)
        if args.verbose:
            print(patches.describe(n))
        else:
            kind = p.instrument.type if p.instrument else 'chain'
            first = p.notes.strip().splitlines()[0] if p.notes.strip() else ''
            print(f"{n:<40} {kind:<6} {first}")
    return 0


def cmd_params(args) -> int:
    engine = find_engine(args.engine)
    cmd = [str(engine), 'params'] + (['--json'] if args.json else ['--markdown']) + ([args.type] if args.type else [])
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        raise CliError(f"engine params failed: {proc.stderr.strip()}", 4)
    return 0


def _section_dir_name(name: str) -> str:
    return re.sub(r'[^A-Za-z0-9_-]+', '_', name)   # same folder name as `build --section`


def zoom_target(target: str, stem: str | None = None, section: str | None = None) -> tuple[Path, Path]:
    """(wav, render dir) for `zoom`: a .wav path, or a song (songs/<slug>, song.py, slug) whose last
    render in out/ (or out/sections/<name>/ with --section) provides mix.wav or stems/<stem>.wav."""
    p = Path(target)
    if p.suffix.lower() == '.wav':
        if not p.is_file():
            raise CliError(f"no WAV file at {target}")
        return p.resolve(), p.resolve().parent
    rdir = resolve_song(target).parent / 'out'
    if section:
        rdir = rdir / 'sections' / _section_dir_name(section)
    wav = rdir / 'stems' / f'{stem}.wav' if stem else rdir / 'mix.wav'
    if not wav.is_file():
        if stem:
            have = sorted(x.stem for x in (rdir / 'stems').glob('*.wav'))
            hint = f"stems there: {', '.join(have)}" if have else "render the stems first: python -m agentsound build ... --stems"
            raise CliError(f"no stem '{stem}' at {wav} ({hint})")
        raise CliError(f"no render at {wav}: build it first (python -m agentsound build {target}"
                       f"{' --section ' + section if section else ''})")
    return wav, rdir


def _render_files(rdir: Path):
    """(path, render block) of report.json 'render', song.render.json of the render in rdir, then the song's."""
    for f in (rdir / 'report.json', rdir / 'song.render.json', rdir.parent.parent / 'song.render.json'):
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        r = data.get('render', data) if isinstance(data, dict) else {}
        if isinstance(r, dict):
            yield f, r


def _render_info(rdir: Path) -> dict:
    """tempo (the start tempo with a tempo map) and fromBeat of the render in rdir (report.json 'render', else
    song.render.json)."""
    info: dict = {}
    for _, r in _render_files(rdir):
        tempo = r.get('tempo')
        if not isinstance(tempo, (int, float)) and isinstance(r.get('tempoMap'), list) and r['tempoMap']:
            tempo = r['tempoMap'][0][1]
        if isinstance(tempo, (int, float)):
            info.setdefault('tempo', float(tempo))
            if isinstance(r.get('fromBeat'), (int, float)):
                info.setdefault('fromBeat', float(r['fromBeat']))
        if 'tempo' in info and 'fromBeat' in info:
            break
    return info


def _timing_file(rdir: Path) -> Path | None:
    """The file with the render's song time (tempo / tempo map, meter) for the engine's zoom --song."""
    return next((f for f, r in _render_files(rdir) if 'tempo' in r or 'tempoMap' in r), None)


def cmd_zoom(args) -> int:
    wav, rdir = zoom_target(args.target, args.stem, args.section)
    given = [x for x in (args.at, args.sec, args.beat) if x is not None]
    if len(given) != 1:
        raise CliError("zoom needs exactly one of --at m:ss.sss, --sec X or --beat B")
    info = _render_info(rdir)
    cmd = [str(find_engine(args.engine)), 'zoom', str(wav), '--ms', f"{args.ms:g}", '--channel', args.channel]
    if args.at is not None:
        cmd += ['--at', args.at]
    elif args.sec is not None:
        cmd += ['--sec', f"{args.sec:.6f}"]
    else:
        if 'tempo' not in info:
            raise CliError(f"--beat needs the song tempo: no report.json / song.render.json in {rdir}")
        cmd += ['--beat', f"{args.beat:g}", '--start-beat', f"{info.get('fromBeat', 0.0):g}"]
    timing = _timing_file(rdir)
    if timing is not None:  # the song's tempo (map) + meter: exact --beat and the bar/beat in the title
        cmd += ['--song', str(timing)]
    elif 'tempo' in info:
        cmd += ['--tempo', f"{info['tempo']:g}"]
    if 'tempo' in info and args.beat is None:
        cmd += ['--start-beat', f"{info.get('fromBeat', 0.0):g}"]
    if args.out:
        out = Path(args.out)
    else:
        label = args.at.replace(':', 'm') + 's' if args.at else f"{args.sec:g}s" if args.sec is not None else f"beat{args.beat:g}"
        out = rdir / 'zooms' / f"zoom_{re.sub(r'[^A-Za-z0-9._-]+', '_', label)}_{wav.stem}.png"
    cmd += ['--out', str(out)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    except OSError as e:
        raise CliError(f"could not run the engine: {e}", 4) from None
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or '').strip() or f"exit code {proc.returncode}"
        raise CliError(f"zoom failed: {msg}", 2 if proc.returncode == 2 else 4)
    result: dict = {}
    for line in reversed((proc.stdout or '').strip().splitlines()):
        try:
            result = json.loads(line)
            break
        except ValueError:
            continue
    print(f"zoom      {result.get('png', out)}")
    clicks = result.get('clicks') or []
    if clicks:
        print(f"  clicks in view: " + ', '.join(f"{c['offsetMs']:+.2f} ms (jump {c['jumpDb']:.0f} dBFS)" for c in clicks))
    else:
        print("  no clicks detected in view")
    return 0


def cmd_compare(args) -> int:
    from . import compare
    song_py = resolve_song(args.song)
    engine = find_engine(args.engine)
    ff = find_ffmpeg()
    if ff is None:
        raise CliError("compare needs ffmpeg to decode the reference (PATH or C:/Program Files (x86)/ffmpeg/bin)", 3)
    try:
        res = compare.run(song_py.parent, Path(args.ref), engine, ff, ref_start=args.ref_start, ref_end=args.ref_end,
                          section=args.section, mix_start=args.mix_start, mix_end=args.mix_end,
                          out=Path(args.out) if args.out else None, images=not args.no_images, png=not args.no_png)
    except compare.CompareError as e:
        raise CliError(str(e)) from None
    for line in compare.summary_lines(res['compare'], res['png'], res['json']):
        print(line)
    return 0


def cmd_mix(args) -> int:
    """The mix engineer: findings + plan from the last render, or --auto: render, measure, adjust (logged)."""
    from . import mixer
    from .theory import ComposeError
    song_py = resolve_song(args.song)
    explicit = {'lead': args.lead or None, 'bed': args.bed or None, 'rhythm': args.rhythm or None,
                'low': args.low or None}
    try:
        if args.auto:
            song, _ = _load_song(song_py)
            if song.applied_mix is not None:
                raise CliError("build() applies a MIX itself (s.mix(...)); mix --auto manages the MIX: move it to a "
                               "module-level MIX = {...}")
            res = mixer.auto(song_py.parent, profile=args.profile, iterations=args.iterations, sections=args.section,
                             out=Path(args.out) if args.out else None, engine=args.engine, **explicit)
            print(res.describe())
            print(f"MIX       {res.out / 'MIX.py'}  (paste it into song.py; the CLI applies a module-level MIX at build)")
            print(res.code())
            return 0
        rdir = song_py.parent / 'out'
        report = mixer.load_report(rdir / 'report.json')
        song, _ = _load_song(song_py)
        apply_module_mix(song)
        p = mixer.plan(song, report, profile=args.profile, **explicit)
        print(p.describe())
        findings = mixer.check(report, profile=args.profile, song=song, **{k: v for k, v in explicit.items() if k == 'lead'})
        print(f"findings ({len(findings)}):")
        for f in findings:
            print('  ' + str(f).replace('\n', '\n  '))
        if p.moves:
            print("the plan as a MIX (on top of the song's own):")
            print(mixer.to_code(p.mix()))
        return 0
    except ComposeError as e:
        raise CliError(str(e)) from None


def cmd_master(args) -> int:
    from . import mastering
    target = Path(args.song)
    if not (target.is_file() and target.suffix.lower() == '.wav'):
        target = resolve_song(args.song).parent
    try:
        if args.check:
            report = target
            if target.is_file():   # a bare WAV: its analysis (a render folder's report.json, else analyze it now)
                report = target.parent / 'report.json'
                if target.name != 'mix.wav' or not report.is_file():
                    report = mastering.analyze_wav(target, profile=args.profile or 'default', engine=args.engine)
            findings = mastering.check(report, platform=args.platform,
                                       compare=Path(args.compare) if args.compare else None)
            print(f"master check  {target}  (platform {mastering.get_platform(args.platform).name})")
            for line in mastering.check_lines(findings):
                print(line)
            return 0
        plan = mastering.match(target, ref=args.ref, ref_start=args.ref_start, ref_end=args.ref_end,
                               section=args.section, profile=args.profile, platform=args.platform,
                               strength=args.strength, max_db=args.max_db, engine=args.engine,
                               out=Path(args.out) if args.out else None)
        print(plan.describe())
        if args.render:
            res = mastering.render(plan, engine=args.engine, mp3=not args.no_mp3)
            for line in mastering.result_lines(res):
                print(line)
            for line in mastering.check_lines(mastering.check(res['afterReport'], platform=args.platform)):
                print(line)
    except mastering.MasteringError as e:
        raise CliError(str(e)) from None
    return 0


def cmd_dx7(args) -> int:
    engine = find_engine(args.engine)
    cmd = [str(engine), 'dx7'] + (['--json'] if args.json else []) + ([args.search] if args.search else [])
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        raise CliError(f"engine dx7 failed: {proc.stderr.strip()}", 4)
    if proc.stderr.strip():   # e.g. "no DX7 banks installed - see assets/dx7/README.md"
        print(proc.stderr.strip(), file=sys.stderr if args.json else sys.stdout)
    return 0


def cmd_sf2(args) -> int:
    engine = find_engine(args.engine)
    cmd = [str(engine), 'sf2'] + (['--json'] if args.json else []) + (['--samples'] if args.samples else []) + \
          (['--file', args.file] if args.file else []) + list(args.search or [])
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        raise CliError(f"engine sf2 failed: {(proc.stderr or proc.stdout).strip()}", 2 if proc.returncode == 2 else 4)
    return 0


def cmd_samples(args) -> int:
    from . import library
    try:
        packs = library.load_manifest()
        if args.action == 'list':
            if args.ids:
                raise CliError("pack ids only go with 'fetch' (list filters: --genre, --category)")
            print(library.list_packs(packs, args.genre, args.category, args.verbose))
            return 0
        chosen = library.select(packs, args.ids, args.all, args.genre, args.category)
        if not chosen:
            raise CliError("fetch what? give pack ids, --all, --genre or --category")
        failed = []
        for p in chosen:
            try:
                library.fetch(p, force=args.force)
            except (library.LibraryError, OSError) as e:
                failed.append(p['id'])
                print(f"  FAILED: {e}", file=sys.stderr)
        if failed:
            raise CliError(f"{len(failed)} of {len(chosen)} packs failed: {', '.join(failed)}", 4)
        return 0
    except library.LibraryError as e:
        raise CliError(str(e)) from e


def cmd_voices(args) -> int:
    from . import speech
    try:
        vs = speech.voices(refresh=True)
    except speech.SpeechError as e:
        raise CliError(str(e)) from None
    if args.json:
        print(json.dumps(vs, indent=1))
        return 0
    if not vs:
        print("no text-to-speech voices found (Windows only: System.Speech / OneCore via PowerShell)")
        return 0
    for v in vs:
        tag = f"{v['engine']}:{v['name']}"
        print(f"{tag:<36} {v['language']:<7} {v['gender']:<7}" + ('  (default)' if v['default'] else ''))
    print("use: speech.words([...], voice='<name or unique part>') / speak \"text\" --voice NAME "
          "(prefix sapi: / onecore: to pick the engine)")
    return 0


def cmd_voicebanks(args) -> int:
    from . import voicebank as vb
    try:
        vs = vb.voices()
    except vb.VoicebankError as e:
        raise CliError(str(e)) from None
    if args.json:
        print(json.dumps(vs, indent=1, ensure_ascii=False))
        return 0
    from .delivery import license_class
    for v in vs:
        cls = license_class(v.get('license', ''))
        print(f"{v['id']:<8} {'installed' if v['installed'] else 'MISSING  '} {v.get('gender', ''):<7} "
              f"{'-'.join(v.get('range', [])):<8} modes {', '.join(f'{k}={m}' for k, m in v.get('modes', {}).items())}")
        print(f"         {v['title']}  [{cls}{' - NON-COMMERCIAL' if cls == 'nc' else ''}]  consent: {v['consent']}")
        print(f"         licence: {v.get('license', '?')}")
        if not v['installed']:
            print(f"         install: download {v.get('url')} (official source: {v.get('page')}), unpack so that "
                  f"{v['path']}/dsconfig.yaml exists")
    print(f"voices folder: {vb.voices_dir()} ($AGENTSOUND_VOICES); singing backend: WSL {vb.SINGING_DIR}/.venv "
          f"($AGENTSOUND_SINGING_DIR); use: singer.sing(s, line, lyrics, voice='<id>')")
    if args.check:
        ok, why = vb.runner_ok()
        print(f"backend: {'ok' if ok else 'UNAVAILABLE - ' + why}")
        if ok:
            for v in vs:
                if not v['installed']:
                    continue
                bank = vb.get(v['id'])
                try:
                    info = vb.run(bank, [{'op': 'info'}], work=REPO / '.scratch' / 'voicebanks', log=None)[0]
                except vb.VoicebankError as e:
                    print(f"{v['id']}: FAILED - {e}")
                    continue
                print(f"{v['id']}: {len(info['phonemes'])} phonemes, speakers {', '.join(info['speakers'])}, "
                      f"{info['sample_rate']} Hz, models {', '.join(k for k, x in info['has'].items() if x)}")
    return 0


def cmd_lyrics(args) -> int:
    from . import lyrics as ly
    from . import voicebank as vb
    extra = None
    if args.voice:
        b = vb.get(args.voice)
        extra = b.dictionary() if b.installed() else None
    if not ly.cmudict_path().is_file():
        print(f"(no CMUdict at {ly.cmudict_path()}: words are guessed by letter-to-sound rules)")
    try:
        for t in ly.parse(args.text):
            if t.kind != 'word':
                print(f"{t.text:<16} {t.kind}: 1 note")
                continue
            ph, src = (t.phonemes, 'hand') if t.phonemes is not None else ly.g2p(t.text, extra)
            syl = ly.syllabify(ph, t.text, src)
            if t.pieces and len(t.pieces) != len(syl):
                print(f"{t.text:<16} ERROR: split into {len(t.pieces)} pieces but it has {len(syl)} syllables")
                continue
            print(f"{t.text + t.mark:<16} {len(syl)} note(s)  {' . '.join(str(x) for x in syl):<40} ({src})")
    except ly.LyricsError as e:
        raise CliError(str(e)) from None
    return 0


def cmd_speak(args) -> int:
    from . import speech
    try:
        out = speech.speak(args.text, args.out, voice=args.voice, rate=args.rate, volume=args.volume,
                           ssml=True if args.ssml else None, cache_dir=REPO / '.scratch' / 'speech')
        seconds = speech.wav_seconds(out)
    except speech.SpeechError as e:
        raise CliError(str(e)) from None
    print(f"wrote {Path(out).resolve()}  ({seconds:.2f} s, trimmed, {speech.LEVEL_DBFS:g} dBFS active level)")
    return 0


def cmd_sfz(args) -> int:
    from . import sfz
    from .theory import ComposeError
    cc = {}
    for item in args.cc or []:
        m = re.fullmatch(r'\s*(\d+)\s*=\s*([0-9.]+)\s*', item)
        if not m:
            raise CliError(f"--cc takes NUMBER=VALUE (e.g. --cc 64=127), got {item!r}")
        cc[int(m.group(1))] = float(m.group(2))
    try:
        if args.check is not None:
            rows = sfz.check(args.check or None, log=None if args.json else
                             lambda r: print(f"{r['status']:<8} {r['file']}"
                                             + (f"  ({r['zones']} zones{', unsupported: ' + ', '.join(r['unsupported']) if r['unsupported'] else ''})"
                                                if r['status'] == 'ok' else f"  {r['error']}" if r['status'] == 'error' else '')))
            if args.json:
                print(json.dumps(rows, indent=1))
            else:
                by = {}
                for r in rows:
                    by.setdefault(r['status'], 0)
                    by[r['status']] += 1
                print(f"{len(rows)} .sfz files: " + ', '.join(f"{v} {k}" for k, v in sorted(by.items()))
                      + " (fragment = #included by another .sfz of the pack)")
            return 0
        if not args.file:
            raise CliError("give an .sfz file (e.g. samples/salamander-grand/SalamanderGrandPianoV3.sfz) or --check [PACK ...]")
        if args.articulation:   # a wrong articulation is an error, not a summary
            sfz.load(args.file, articulation=args.articulation, cc=cc or None)
        s = sfz.summary(args.file, cc=cc or None, articulation=args.articulation)
        if args.pitch:
            s['pitch'] = sfz.pitch_check(args.file, cc=cc or None, articulation=args.articulation, count=args.pitch)
    except ComposeError as e:
        raise CliError(str(e)) from None
    print(json.dumps(s, indent=1) if args.json else sfz.format_summary(s))
    return 0


def cmd_kit(args) -> int:
    """The mapping inst.kit(...) makes of a folder (one-shots, Hydrogen, DrumGizmo), inst.organ(...)'s stops of a
    GrandOrgue sample set, or inst.multisample(...)'s notes."""
    from . import kits
    from .theory import ComposeError
    mapping = {}
    for item in args.map or []:
        k, sep, v = item.partition('=')
        if not sep or not k.strip():
            raise CliError(f"--map takes KEY=FILE (e.g. --map snare=Snare03 --map 40='Gated*'), got {item!r}")
        k = k.strip()
        mapping[int(k) if k.isdigit() else k] = None if v.strip().lower() in ('', 'none') else v.strip()
    mics = {}
    for item in args.mic or []:
        k, sep, v = item.partition('=')
        if not sep:
            raise CliError(f"--mic takes NAME=DB or NAME=off (e.g. --mic room=-6), got {item!r}")
        try:
            mics[k.strip()] = None if v.strip().lower() in ('off', 'none', 'mute') else float(v)
        except ValueError:
            raise CliError(f"--mic {item!r}: the gain must be a number of dB or 'off'") from None
    try:
        from . import organ
        target = kits.resolve(args.path, what='kit')
        if args.multisample:
            zones, info = kits.multisample(args.path, octave=args.octave)
            info['zoneList'] = zones if args.json else None
            if args.json:
                print(json.dumps(info, indent=1))
            else:
                from .theory import note_name
                print(f"multisample {info['path']}: {info['zones']} zones, roots "
                      + ' '.join(note_name(r) for r in info['roots'])
                      + (f"; {info['layers']} velocity layers" if info['layers'] > 1 else '')
                      + (f"\n  no note in the name: {', '.join(info['unmapped'])}" if info['unmapped'] else ''))
            return 0
        if organ.find_odf(target) is not None:
            info = organ.describe(args.path, odf=args.odf)
            print(json.dumps(info, indent=1) if args.json else organ.format_info(info))
            return 0
        _, info = kits.build(args.path, mapping or None, numbered=args.numbered, kit=args.kit, mics=mics or None)
    except ComposeError as e:
        raise CliError(str(e)) from None
    print(json.dumps(info, indent=1) if args.json else kits.format_info(info))
    return 0


def cmd_catalog(args) -> int:
    from . import catalog
    unknown = [s for s in args.sections if s not in catalog.SECTIONS]
    if unknown:
        raise CliError(f"unknown section(s) {', '.join(unknown)}; choose from {', '.join(catalog.SECTIONS)}")
    sys.stdout.write(catalog.overview(args.sections or list(catalog.SECTIONS), args.markdown, args.reindex))
    return 0


def cmd_bands(args) -> int:
    from . import bands
    print(bands.describe_all(args.genre))
    return 0


def cmd_find(args) -> int:
    from . import catalog
    sys.stdout.write(catalog.search(args.words, args.only, args.limit))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog='python -m agentsound', description='AgentSound: compose songs as Python.')
    sub = ap.add_subparsers(dest='cmd', required=True)

    def profile_opt(p):
        p.add_argument('--profile', choices=ANALYSIS_PROFILES,
                       help="analysis profile the report judges the mix against (wins over the song's ANALYSIS dict): "
                            "default | synthwave (outrun/retrowave, strong 40-60 Hz) | dreamwave (softer) | darksynth (louder) "
                            "| jazz (acoustic club trio/quartet, -16..-13 LUFS) | classical (orchestra/chamber in a hall, "
                            "-23..-16 LUFS, very dynamic) | pop (-11..-8, strong lows, bright) | rock (-10..-7, mids "
                            "forward) | film (orchestral hybrid score, -16..-10)")

    def engine_opts(p, render=True):
        p.add_argument('--engine', help='engine executable (default: $AGENTSOUND_ENGINE or build/agentsound.exe)')
        if render:
            p.add_argument('--no-mp3', action='store_true', help="don't encode mix.mp3")
            p.add_argument('--out', help='output directory')

    b = sub.add_parser('build', help='compile, render, encode mp3, summarize the report')
    b.add_argument('song', help='songs/<slug>, a song.py path or a slug')
    b.add_argument('--section', help='render only this section')
    b.add_argument('--from-beat', type=float, dest='from_beat')
    b.add_argument('--to-beat', type=float, dest='to_beat')
    b.add_argument('--stems', action='store_true', help='also write one WAV per track and bus')
    profile_opt(b)
    engine_opts(b)
    b.set_defaults(func=cmd_build)

    c = sub.add_parser('check', help='compile + validate (compose layer, then the engine if built); no render')
    c.add_argument('song')
    c.add_argument('--out')
    c.add_argument('--engine')
    profile_opt(c)
    c.set_defaults(func=cmd_check)

    n = sub.add_parser('new', help='create songs/<slug>/song.py from the template')
    n.add_argument('slug')
    n.set_defaults(func=cmd_new)

    a = sub.add_parser('audition', help='render a short test phrase with a patch')
    a.add_argument('patch')
    a.add_argument('--notes', default='auto', metavar='MATERIAL', type=str.lower,
                   choices=['auto'] + list(AUDITION_MATERIAL) + list(AUDITION_ALIASES),
                   help='auto (from the patch hint / name) or: ' + '; '.join(f"{k} = {v}" for k, v in AUDITION_MATERIAL.items()) +
                        '; aliases: ' + ', '.join(f"{k}={v}" for k, v in AUDITION_ALIASES.items()))
    a.add_argument('--tempo', type=float, default=100.0)
    a.add_argument('--key', default='A minor')
    profile_opt(a)
    engine_opts(a)
    a.set_defaults(func=cmd_audition)

    p = sub.add_parser('patches', help='list registered patches')
    p.add_argument('prefix', nargs='?', default='')
    p.add_argument('-v', '--verbose', action='store_true')
    p.set_defaults(func=cmd_patches)

    q = sub.add_parser('params', help="print the engine's instrument/effect parameter reference")
    q.add_argument('type', nargs='?', help="only this instrument/effect type, e.g. 'va' or 'ducker'")
    q.add_argument('--json', action='store_true')
    q.add_argument('--engine')
    q.set_defaults(func=cmd_params)

    z = sub.add_parser('zoom', help='sample-accurate waveform zoom PNG of a render (mix or a stem) at a moment')
    z.add_argument('target', help='songs/<slug> (uses out/mix.wav), a song.py or slug, or a .wav file')
    z.add_argument('--at', help='song time m:ss.sss (as in report.clicks[].time)')
    z.add_argument('--sec', type=float, help='time in seconds from the start of the render')
    z.add_argument('--beat', type=float, help='song beat (0-based; needs the render report for the tempo)')
    z.add_argument('--stem', help='zoom into out/stems/<id>.wav instead of the mix (build with --stems)')
    z.add_argument('--section', help='use the render of `build --section NAME` (out/sections/<name>/)')
    z.add_argument('--ms', type=float, default=40.0, help='width of the view in ms (default 40)')
    z.add_argument('--channel', default='both', choices=['L', 'R', 'both'])
    z.add_argument('--out', help='output PNG (default: <render dir>/zooms/zoom_<time>_<wav>.png)')
    z.add_argument('--engine')
    z.set_defaults(func=cmd_zoom)

    k = sub.add_parser('compare', help='compare the mix with a reference track, loudness-matched (spectrum, width, '
                                       'dynamics, punch, tails) -> out/compare/<ref>/compare.json + compare.png + suggestions')
    k.add_argument('song', help='songs/<slug> (its last full render out/mix.wav), a song.py path or a slug')
    k.add_argument('--ref', required=True, help='reference audio: mp3, wav, flac, m4a, ogg ... (decoded with ffmpeg)')
    k.add_argument('--ref-start', dest='ref_start', help='reference excerpt start, m:ss.s or seconds (e.g. the chorus)')
    k.add_argument('--ref-end', dest='ref_end', help='reference excerpt end')
    k.add_argument('--section', help="compare this section of the song's full render (out/report.json sections)")
    k.add_argument('--mix-start', dest='mix_start', help='mix excerpt start (instead of --section)')
    k.add_argument('--mix-end', dest='mix_end', help='mix excerpt end')
    k.add_argument('--out', help='output folder (default songs/<slug>/out/compare/<reference name>/)')
    k.add_argument('--no-images', action='store_true', help="skip the reference's own analysis images (ref/*.png)")
    k.add_argument('--no-png', action='store_true', help="skip compare.png")
    k.add_argument('--engine')
    k.set_defaults(func=cmd_compare)

    m = sub.add_parser('mix', help="the mix engineer: findings + mix plan from out/report.json; --auto renders, measures "
                                   "and adjusts trims / rides / ducks / dips toward the genre targets (out/mixer/MIX.py)")
    m.add_argument('song', help='songs/<slug>, a song.py path or a slug')
    m.add_argument('--auto', action='store_true', help='render -> measure -> adjust, --iterations times, then verify')
    m.add_argument('--iterations', type=int, default=2)
    m.add_argument('--section', action='append', help='--auto: render only these sections (a preview; repeatable)')
    m.add_argument('--profile', choices=ANALYSIS_PROFILES, help="the genre targets (default: the report's / ANALYSIS)")
    m.add_argument('--lead', action='append', help='the lead track id(s) (default: inferred)')
    m.add_argument('--bed', action='append', help='bed track ids (default: inferred)')
    m.add_argument('--rhythm', action='append', help='drum / percussion track ids (default: inferred)')
    m.add_argument('--low', action='append', help='bass track ids (default: inferred)')
    m.add_argument('--out', help='--auto: where the passes render (default songs/<slug>/out/mixer/)')
    m.add_argument('--engine')
    m.set_defaults(func=cmd_mix)

    ms = sub.add_parser('master', help='the mastering engineer: match the mix to a reference / the genre profile '
                                       '(tonal eq, loudness, width, limiter -> out/master/master.json), --render the '
                                       'post-pass (out/master/mastered.wav), --check a master against delivery targets')
    ms.add_argument('song', help='songs/<slug> (its out/mix.wav), a song.py path, a slug or any .wav')
    ms.add_argument('--ref', help='reference audio (decoded with ffmpeg): its tone, width and loudness become the target')
    ms.add_argument('--ref-start', dest='ref_start', help='reference excerpt start, m:ss.s or seconds')
    ms.add_argument('--ref-end', dest='ref_end', help='reference excerpt end')
    ms.add_argument('--section', help="judge the tone on this section of the song (compare like with like)")
    ms.add_argument('--platform', default='auto',
                    help='auto (genre profile / reference) | streaming (-14 LUFS, -1 dBTP) | loud (club: top of the '
                         'genre window) | dynamic (classical / jazz: dynamics first); aliases club, classical, jazz')
    ms.add_argument('--profile', choices=ANALYSIS_PROFILES, help="analysis profile (default: the song's)")
    ms.add_argument('--strength', type=float, default=0.75, help='share of the tonal difference to correct (0..1)')
    ms.add_argument('--max-db', dest='max_db', type=float, default=3.0, help='limit of every eq move, dB (default 3)')
    ms.add_argument('--render', action='store_true', help='also render the post-pass: out/master/mastered.wav/.mp3, '
                                                          'before/after numbers and warnings')
    ms.add_argument('--check', action='store_true', help="only check the song's report (true peak, loudness, LRA, "
                                                         "tone, mono, DC ...) against the platform")
    ms.add_argument('--compare', help='with --check: a compare.json to judge the tone against a reference too')
    ms.add_argument('--no-mp3', action='store_true')
    ms.add_argument('--out', help='output folder (default songs/<slug>/out/master/)')
    ms.add_argument('--engine')
    ms.set_defaults(func=cmd_master)

    x = sub.add_parser('dx7', help='list/search the DX7 ROM voice names (for inst.dx7(...))')
    x.add_argument('search', nargs='?')
    x.add_argument('--json', action='store_true')
    x.add_argument('--engine')
    x.set_defaults(func=cmd_dx7)

    f = sub.add_parser('sf2', help="list/search SoundFont presets (for inst.sf2('...')) or, with --samples, raw samples "
                                   "(for sampler zones)")
    f.add_argument('search', nargs='*', help="words of a preset name, or 'bank:program'")
    f.add_argument('--samples', action='store_true', help='list the raw samples instead of the presets')
    f.add_argument('--file', help='SoundFont in assets/soundfonts/ (default GeneralUser-GS.sf2) or an absolute path')
    f.add_argument('--json', action='store_true')
    f.add_argument('--engine')
    f.set_defaults(func=cmd_sf2)

    k = sub.add_parser('kit', help="the drum-kit mapping inst.kit() builds from a folder of one-shots, a Hydrogen or "
                                   "DrumGizmo kit (keys, velocity layers, round robins, unrecognized files); the stops "
                                   "of a GrandOrgue organ (inst.organ); --multisample: note-named samples")
    k.add_argument('path', help="'samples/<pack>/<folder>', a path relative to assets/, or absolute")
    k.add_argument('--json', action='store_true')
    k.add_argument('--map', action='append', metavar='KEY=FILE', help="override: --map snare=Snare03 --map 40='Gated*' "
                                                                       "--map clap=none (repeatable)")
    k.add_argument('--numbered', default='auto', choices=['auto', 'variants', 'layers', 'rr', 'random'],
                   help="numbered files of one name: measured (auto), different sounds, velocity layers, round robins")
    k.add_argument('--kit', help='DrumGizmo: which kit file of the folder (name substring)')
    k.add_argument('--mic', action='append', metavar='NAME=DB',
                   help="DrumGizmo mic mix: --mic room=-6 --mic overheads=off")
    k.add_argument('--odf', help='GrandOrgue: which .organ file of the folder (name substring)')
    k.add_argument('--multisample', action='store_true', help='map note-named samples (inst.multisample) instead')
    k.add_argument('--octave', type=int, default=0, help='--multisample: shift the parsed notes by octaves')
    k.set_defaults(func=cmd_kit)

    s = sub.add_parser('sfz', help="what an .sfz instrument holds (regions, keys, velocity layers, round robin, "
                                   "articulations, mics, controllers, unsupported opcodes) or --check every .sfz of the packs")
    s.add_argument('file', nargs='?', help="an .sfz: 'samples/<pack>/...', a path relative to assets/, or absolute")
    s.add_argument('--json', action='store_true')
    s.add_argument('--cc', action='append', metavar='N=V', help='controller value for the summary (repeatable), e.g. --cc 64=127')
    s.add_argument('--articulation', help='keyswitch articulation (label or key) to summarize')
    s.add_argument('--pitch', type=int, nargs='?', const=5, metavar='N',
                   help='render N notes (default 5) and compare their measured pitch with the MIDI note: catches '
                        'octave-shifted sample sets (a pack an octave off: play it with transpose=+-12)')
    s.add_argument('--check', nargs='*', metavar='PACK', help='import every .sfz of these installed packs (all without '
                                                             'names) and report ok / fragment / error with the reason')
    s.set_defaults(func=cmd_sfz)

    g = sub.add_parser('catalog', help='overview of everything usable: engine modules, patches, DX7, SoundFonts, '
                                       'sample packs, recipes, analysis profiles, python helpers')
    g.add_argument('sections', nargs='*', help='only these: engine patches bands dx7 soundfonts samples recipes profiles '
                                               'helpers')
    g.add_argument('--markdown', action='store_true', help='markdown (docs/CATALOG.md is generated with this)')
    g.add_argument('--reindex', action='store_true', help='rebuild the INDEX.json of every installed sample pack')
    g.set_defaults(func=cmd_catalog)

    bd = sub.add_parser('bands', help='list the band presets (agentsound.bands): name, genre, roles, what each is tuned '
                                      'against, missing sample packs')
    bd.add_argument('genre', nargs='?', help='only presets of this genre (synthwave, jazz, ...)')
    bd.set_defaults(func=cmd_bands)

    h = sub.add_parser('find', help='search engine params, patches, DX7 voices, SoundFont presets, sample packs, '
                                    'recipes and helpers (all words must match)')
    h.add_argument('words', nargs='+')
    h.add_argument('--in', dest='only', choices=['engine', 'patches', 'bands', 'dx7', 'soundfonts', 'samples',
                                                 'recipes', 'helpers'])
    h.add_argument('--limit', type=int, default=25, help='hits shown per section (default 25)')
    h.set_defaults(func=cmd_find)

    m = sub.add_parser('samples', help='list / download the sample packs of assets/samples/manifest.json')
    m.add_argument('action', nargs='?', default='list', choices=['list', 'fetch'])
    m.add_argument('ids', nargs='*', help='pack ids to fetch')
    m.add_argument('--all', action='store_true', help='fetch every pack (combine with --genre / --category)')
    m.add_argument('--genre', help='only packs tagged with this genre (jazz, synthwave, classical, pop, rock, ...)')
    m.add_argument('--category', help='only packs of this category (drums, piano, bass, strings, ir, ...)')
    m.add_argument('--force', action='store_true', help='re-unpack an installed pack')
    m.add_argument('-v', '--verbose', action='store_true')
    m.set_defaults(func=cmd_samples)

    v = sub.add_parser('voices', help='list the installed Windows text-to-speech voices (for speech.words / speak)')
    v.add_argument('--json', action='store_true')
    v.set_defaults(func=cmd_voices)

    vbp = sub.add_parser('voicebanks', help='the singing voicebanks (assets/voices/manifest.json): installed?, '
                                            'licence, range, modes; --check runs the WSL backend')
    vbp.add_argument('--check', action='store_true', help='check the WSL singing backend and load every bank')
    vbp.add_argument('--json', action='store_true')
    vbp.set_defaults(func=cmd_voicebanks)

    ly = sub.add_parser('lyrics', help='how lyrics are sung: words -> syllables (phonemes, stress) -> notes')
    ly.add_argument('text', help="lyrics in the singer's syntax ('Hold - on to the night', to-geth-er, word{ph ...})")
    ly.add_argument('--voice', help="also use this voicebank's own dictionary (e.g. hanami)")
    ly.set_defaults(func=cmd_lyrics)

    k = sub.add_parser('speak', help='render text with a Windows voice to a WAV (trimmed, -18 dBFS: vocoder-ready)')
    k.add_argument('text', help="the words, or SSML with --ssml")
    k.add_argument('--out', required=True, help='WAV file to write')
    k.add_argument('--voice', help="voice name or a unique part of it ('zira', 'onecore:Stefan'); default: Windows default")
    k.add_argument('--rate', type=float, default=0, help='-10 (slow) .. 10 (fast), default 0')
    k.add_argument('--volume', type=float, default=100, help='0..100, default 100')
    k.add_argument('--ssml', action='store_true', help='the text is SSML (<speak> ... </speak> or a fragment)')
    k.set_defaults(func=cmd_speak)

    from .makingof import add_parser as _mo_parser
    _mo_parser(sub)
    sub.choices['makingof'].set_defaults(func=cmd_makingof)
    return ap


def cmd_makingof(args) -> int:
    from . import makingof
    return makingof.run(args)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except CliError as e:
        sys.stdout.flush()
        print(f"error: {e}", file=sys.stderr)
        return e.code
