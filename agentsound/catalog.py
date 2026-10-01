"""Catalog: a one-page overview of everything a composing agent can use, and one search across all of it.

    python -m agentsound catalog [SECTION ...] [--markdown]
        sections: engine patches bands dx7 soundfonts samples recipes profiles helpers (default: all)
    python -m agentsound find WORD [WORD ...] [--in SECTION] [--limit N]

Read the catalog instead of walking assets/ or the source: it lists the engine's instruments and effects (with
their main params), the patch library, the band presets (agentsound.bands), the DX7 ROM voices, the SoundFont
presets of every .sf2 (bundled and downloaded), the sample packs (manifest + a structural index of each installed
pack), the genre recipes, the analysis profiles and the Python helper functions. `find` searches the same material
(names, help texts, file paths of installed packs, recipe lines) and prints how to use each hit.
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / 'assets'
SECTIONS = ('engine', 'patches', 'bands', 'dx7', 'soundfonts', 'samples', 'recipes', 'profiles', 'helpers')
AUDIO_EXT = {'.wav', '.flac', '.aif', '.aiff', '.ogg', '.mp3'}

# One line per engine module. test_catalog checks that every engine type has one (and no stale ones).
MODULES = {
    # instruments
    'va': "virtual-analog polysynth: 2 osc + sub + noise, supersaw unison, ladder/SVF filter, envelopes, drift, "
          "free per-voice mod matrix ('mods'); pads, leads, basses, arps, plucks",
    'dx7': "DX7 FM synth (msfa core) playing the 256 original ROM voices by name: e.pianos, brass, bells, basses",
    'drums': "synthesized drum machine, GM key map (36 kick 38 snare 39 clap 42 hat 46 open hat ...), kits 808 909 "
             "linn synthwave modern, every piece tweakable (kick.decay, snare.snappy ...)",
    'sf2': "SoundFont player (GeneralUser GS by default: the full GM/GS set incl. drum kits on bank 128); any .sf2 "
           "via file=",
    'sampler': "WAV sampler: a folder (GM drum names / note names), one file or explicit zones (key + velocity "
               "ranges, loops, choke groups); one-shots, multisamples, reversed hits",
    'stack': "layered instrument: 1-8 child instruments of any type on one track (inst.stack(layer(...), ...), "
             "Patch.layered; patches layered/...): per layer level, pan, transpose (octave doubles), fine detune, key "
             "range + key crossfade (splits), velocity range + equal-power velocity crossfade (soft e-piano -> hard "
             "grand), velocity curve, note delay (swell / flam), mute, own fx chain; pitchbend / pedal / expression / "
             "dynamics / modwheel forwarded (follow flags); params as layers.<id>.<param>; piano + bell + pad leads, "
             "brass + saw, octave strings, splits",
    # dynamics
    'compressor': "compressor with sidechain input, peak/rms detector, auto makeup, parallel mix",
    'ducker': "sidechain pump: keyed from a track/bus or a tempo-synced envelope (no key needed)",
    'limiter': "lookahead true-peak-safe limiter (master only adds latency)",
    'saturator': "saturation: tape, tube, hard clip, wavefolder (oversampled)",
    'amp': "tube guitar amp head: 1-4 cascaded preamp stages (gain), a Tube Screamer boost, bright cap, the Marshall / "
           "Fender bass-mid-treble tone stack, presence / resonance, a sagging push-pull power amp (master, sag); "
           "4x oversampled; put a cab IR (convolver, cab/* patches) after it - the singing, odd-harmonic lead / crunch "
           "of a real amp instead of one waveshaper",
    'bitcrush': "bit reduction + sample-rate reduction (lo-fi, 8-bit)",
    'eq': "7-band EQ: hp, low shelf, 3 peaks, high shelf, lp",
    'filter': "resonant filter lp/bp/hp/ladder with drive (sweeps, automation target)",
    'utility': "gain, pan, polarity flip per channel, mono sum",
    'width': "stereo width (mid/side) with mono-below-frequency (monobass) and balance",
    # modulation / time
    'chorus': "Juno-style chorus (modes I, II, I+II) or custom multi-voice chorus",
    'ensemble': "string-machine ensemble (Solina-style triple chorus with shimmer)",
    'dimension': "Dimension-D style stereo spreader (modes 1-4), mono-compatible",
    'microshift': "micro pitch-shift doubler (+/- cents, stereo): widens mono leads and vocals",
    'flanger': "flanger with feedback and stereo offset",
    'phaser': "phaser 2-12 stages, free or tempo-synced",
    'tremolo': "amplitude tremolo / auto-pan (sine, triangle, square), tempo-synced",
    'vowel': "formant filter (a e i o u, morph): talking synths, vocal-like pads",
    'wah': "wah pedal (resonant sweep heel..toe, automate 'pedal') or auto-wah (the playing opens it): guitar leads, funk",
    'vocoder': "robot voice: the sidechain (a speech track, agentsound.speech) talks through this track's notes; "
               "classic channel vocoder (8-40 bands) or lpc talkbox",
    'delay': "stereo / ping-pong / mono delay, tempo-synced, filtered feedback, wow/flutter, ducking",
    'reverb': "algorithmic reverb: plate, hall, room, chamber, cathedral; predelay, damping, modulation",
    'gatedreverb': "80s gated reverb (the Phil Collins snare), keyable",
    'shimmer': "shimmer reverb (octave / fifth pitch-shifted feedback): dreamy intros and pads",
    'tape': "tape machine: saturation, head bump, top roll-off, wow, flutter, hiss (cassette .. 30 ips)",
    'exciter': "harmonic exciter: air and presence without EQ harshness",
    'convolver': "convolution with an impulse-response WAV (ir=): real halls, rooms, plates, churches, guitar cabinets",
}


# -------------------------------------------------------------------------------- data sources

def _engine_json(*args: str) -> object | None:
    from .cli import find_engine, CliError
    try:
        engine = find_engine()
    except CliError:
        return None
    proc = subprocess.run([str(engine), *args, '--json'], capture_output=True, text=True, encoding='utf-8',
                          errors='replace')
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def engine_modules() -> dict:
    return _engine_json('params') or {}


DX7_NO_BANKS = "no DX7 banks installed - see assets/dx7/README.md"


def dx7_banks_installed() -> bool:
    """True when assets/dx7 holds the ROM banks (*.syx): the Yamaha cartridges are not part of the repository."""
    d = ASSETS / 'dx7'
    return d.is_dir() and any(p.suffix.lower() == '.syx' for p in d.iterdir())


def dx7_voices() -> list[dict]:
    if not dx7_banks_installed():
        return []
    return _engine_json('dx7') or []


def soundfont_files() -> list[Path]:
    files = sorted((ASSETS / 'soundfonts').glob('*.sf2'))
    from .library import SAMPLES as samples
    if samples.is_dir():
        files += sorted(p for p in samples.rglob('*') if p.suffix.lower() == '.sf2' and '.downloads' not in p.parts)
    return files


def sf2_presets(path: Path) -> list[dict]:
    return _engine_json('sf2', '--file', str(path)) or []


def asset_rel(path: Path) -> str:
    from .library import SAMPLES
    for root, prefix in ((ASSETS, ''), (SAMPLES, 'samples/')):
        try:
            return prefix + path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            pass
    return str(path)


def recipes() -> list[tuple[str, str]]:
    out = []
    for p in sorted((REPO / 'recipes').glob('*.md')):
        first = next((ln.lstrip('# ').strip() for ln in p.read_text(encoding='utf-8').splitlines() if ln.strip()), '')
        out.append((p.name, first))
    return out


HELPER_MODULES = ('theory', 'voicing', 'notation', 'patterns', 'humanize', 'automation', 'modulation', 'midifx', 'vamod', 'jazz', 'pianist', 'romantic',
                  'drummer', 'hornist', 'gesture', 'fretwork', 'soloist', 'guitar_vocab', 'horn_vocab', 'budget',
                  'bassist', 'guitarist', 'sfz', 'kits', 'organ', 'articulation', 'speech', 'tempo', 'song', 'mixer',
                  'mastering', 'heroes', 'bands', 'compare', 'delivery', 'library', 'silent_notes', 'figures',
                  'bandlib.scoring')


def helpers() -> dict[str, list[tuple[str, str]]]:
    """Public functions / classes (+ public methods of song classes) with their first docstring line."""
    out: dict[str, list[tuple[str, str]]] = {}
    for mod_name in HELPER_MODULES:
        try:
            mod = importlib.import_module(f'agentsound.{mod_name}')
        except ImportError:
            continue
        rows = []
        for name, obj in vars(mod).items():
            if name.startswith('_') or getattr(obj, '__module__', None) != mod.__name__:
                continue
            if inspect.isfunction(obj):
                rows.append((f"{name}{_sig(obj)}", _doc1(obj)))
            elif inspect.isclass(obj):
                rows.append((name, _doc1(obj)))
                if mod_name == 'song':
                    seen = set()
                    for cls in obj.__mro__:
                        if cls.__module__ != mod.__name__:
                            continue
                        for mname, m in vars(cls).items():
                            if not mname.startswith('_') and inspect.isfunction(m) and mname not in seen:
                                seen.add(mname)
                                rows.append((f"  .{mname}{_sig(m, skip_self=True)}", _doc1(m)))
        out[mod_name] = rows
    return out


def _sig(fn, skip_self: bool = False) -> str:
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return '()'
    params = list(sig.parameters.values())
    if skip_self and params and params[0].name == 'self':
        params = params[1:]
    parts = []
    for p in params:
        if p.kind is p.VAR_POSITIONAL:
            parts.append('*' + p.name)
        elif p.kind is p.VAR_KEYWORD:
            parts.append('**' + p.name)
        elif p.default is p.empty:
            parts.append(p.name)
        else:
            parts.append(f"{p.name}={p.default!r}" if len(repr(p.default)) <= 12 else f"{p.name}=...")
    text = '(' + ', '.join(parts) + ')'
    return text if len(text) <= 70 else text[:66] + ' ..)'


def _doc1(obj) -> str:
    doc = inspect.getdoc(obj) or ''
    line = doc.strip().split('\n\n')[0].replace('\n', ' ')
    return line[:140] + ('...' if len(line) > 140 else '')


# -------------------------------------------------------------------------------- sample pack index

DRUM_WORDS = ('kick', 'bd', 'snare', 'sd', 'clap', 'hat', 'hh', 'ohh', 'open', 'closed', 'ride', 'crash', 'tom',
              'rim', 'cowbell', 'tamb', 'shaker', 'perc', 'cymbal', 'brush', 'conga', 'bongo')
_NOTE_RE = re.compile(r'(?<![a-z])([a-g])(#|s|b)?(-?\d)(?!\d)', re.I)
_VEL_RE = re.compile(r'(?:^|[_\- ])(?:v|vel|velocity|dyn|p|f|pp|mf|ff)(\d{1,3})(?:$|[_\- .])', re.I)
_RR_RE = re.compile(r'(?:rr|round.?robin|_r|take)(\d{1,2})', re.I)


def _stem_mapping(stems: list[str]) -> str:
    from .patterns import DRUMS
    low = [s.lower() for s in stems]
    if low and all(s in DRUMS for s in low):
        return 'gm-drum-names'
    if low and all(re.fullmatch(r'[a-g](#|s|b)?-?\d|\d{1,3}', s) for s in low):
        return 'note-names'
    return 'custom'


def index_pack(target: Path) -> dict:
    """Structural summary of an installed pack (written to <pack>/INDEX.json by fetch and catalog --reindex)."""
    dirs: dict[str, list[Path]] = {}
    sfz, sf2, docs = [], [], []
    total = 0
    for p in sorted(target.rglob('*')):
        if not p.is_file() or p.name in ('SOURCE.json', 'INDEX.json'):
            continue
        total += p.stat().st_size
        ext = p.suffix.lower()
        rel = p.relative_to(target).as_posix()
        if ext in AUDIO_EXT:
            dirs.setdefault(p.parent.relative_to(target).as_posix(), []).append(p)
        elif ext == '.sfz':
            sfz.append(rel)
        elif ext == '.sf2':
            sf2.append(rel)
        elif ext in ('.txt', '.md', '.pdf', '.html', '.rtf') or p.stem.lower() in ('license', 'readme', 'copying'):
            docs.append(rel)
    folders = []
    for d, files in sorted(dirs.items()):
        stems = [f.stem for f in files]
        notes = sorted({_note_of(s) for s in stems} - {None})
        vel = sorted({int(m.group(1)) for s in stems for m in [_VEL_RE.search(s)] if m})
        rr = sorted({int(m.group(1)) for s in stems for m in [_RR_RE.search(s)] if m})
        words = sorted({w for s in stems for w in DRUM_WORDS if w in s.lower()})
        entry = {'dir': d, 'files': len(files), 'mapping': _stem_mapping(stems), 'examples': stems[:4]}
        if notes and entry['mapping'] != 'gm-drum-names':
            entry['notes'] = [notes[0], notes[-1], len(notes)]
        if len(vel) > 1:
            entry['velocityLayers'] = len(vel)
        if len(rr) > 1:
            entry['roundRobins'] = len(rr)
        if words:
            entry['drumWords'] = words
        exts = sorted({f.suffix.lower() for f in files})
        if exts != ['.wav']:
            entry['formats'] = exts
        folders.append(entry)
    out = {'bytes': total, 'audioFiles': sum(len(v) for v in dirs.values()), 'folders': folders[:400],
           'foldersTruncated': max(0, len(folders) - 400), 'sfz': sfz[:100], 'sf2': sf2, 'docs': docs[:20]}
    if sfz:
        out.update(sfz_index(target))
    return out


SFZ_INDEX_LIMIT = 120   # instruments summarized per pack (the others are still listed in 'sfz')


def sfz_index(target: Path) -> dict:
    """Per-.sfz summaries of a pack for INDEX.json: {'sfzPrograms': {rel: summary}, 'sfzFragments': [rel]}.
    A summary: regions, keys, velocity layers, round robin, articulations, mics, unsupported opcodes, or the error
    that keeps the file from importing (python -m agentsound sfz FILE for everything)."""
    from . import sfz as _sfz
    from .theory import ComposeError
    files, fragments = _sfz.pack_sfz_files(target)
    programs: dict[str, dict] = {}
    for f in [f for f in files if f not in fragments][:SFZ_INDEX_LIMIT]:
        rel = f.relative_to(target).as_posix()
        try:
            s = _sfz.summary(f)
        except ComposeError as e:
            programs[rel] = {'error': str(e)[:300]}
            continue
        entry = {k: s[k] for k in ('regions', 'keys', 'velocityLayers', 'roundRobin', 'randomLayers', 'releaseZones')
                 if k in s}
        if s.get('articulations'):
            entry['articulations'] = [a['label'] or a['name'] for a in s['articulations']]
            entry['articulation'] = s.get('articulation')
        if s.get('mics'):
            entry['mics'] = list(s['mics'])
        if s.get('unsupported'):
            entry['unsupported'] = list(s['unsupported'])[:8]
        if s.get('error'):
            entry['error'] = s['error'][:300]
        programs[rel] = entry
    return {'sfzPrograms': programs,
            'sfzFragments': sorted(f.relative_to(target).as_posix() for f in fragments)[:400]}


def sfz_usage(pack_id: str, rel: str, info: dict | None = None) -> str:
    """Ready-to-paste inst.sfz(...) line for an .sfz of an installed pack."""
    art = (info or {}).get('articulation')
    arts = (info or {}).get('articulations') or []
    line = f"inst.sfz('samples/{pack_id}/{rel}'" + (f", articulation={art!r}" if art and len(arts) > 1 else '') + ')'
    bits = []
    if info:
        if info.get('error'):
            return f"{line}  # cannot import: {info['error'][:160]}"
        if 'keys' in info:
            bits.append(f"keys {_note_name(info['keys'][0])}-{_note_name(info['keys'][1])}")
        for k, label in (('velocityLayers', 'vel layers'), ('roundRobin', 'rr'), ('randomLayers', 'random layers'),
                         ('releaseZones', 'release zones')):
            if info.get(k, 0) > 1 or (k == 'releaseZones' and info.get(k)):
                bits.append(f"{info[k]} {label}")
        if len(arts) > 1:
            bits.append('articulations: ' + ', '.join(arts[:8]) + (' ...' if len(arts) > 8 else ''))
        if info.get('mics'):
            bits.append('mics: ' + ', '.join(info['mics']))
        if info.get('unsupported'):
            bits.append('not played: ' + ', '.join(u.split(' (')[0] for u in info['unsupported'][:4]))
    return line + (f"  # {'; '.join(bits)}" if bits else '')


def _note_of(stem: str) -> int | None:
    m = _NOTE_RE.search(stem)
    if not m:
        return None
    pcs = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}
    pc = pcs[m.group(1).lower()] + {'#': 1, 's': 1, 'b': -1}.get((m.group(2) or '').lower(), 0)
    key = 12 * (int(m.group(3)) + 1) + pc
    return key if 0 <= key <= 127 else None


def pack_index(pack_dir: Path, rebuild: bool = False) -> dict | None:
    if not (pack_dir / 'SOURCE.json').is_file():
        return None
    f = pack_dir / 'INDEX.json'
    if f.is_file() and not rebuild:
        try:
            return json.loads(f.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            pass
    idx = index_pack(pack_dir)
    f.write_text(json.dumps(idx, indent=1) + '\n', encoding='utf-8')
    return idx


def _note_name(k: int) -> str:
    return ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'][k % 12] + str(k // 12 - 1)


# -------------------------------------------------------------------------------- overview

def _human(n) -> str:
    from .library import _human as h
    return h(n)


def overview(sections: list[str], markdown: bool = False, reindex: bool = False) -> str:
    h = (lambda t: f"\n## {t}\n") if markdown else (lambda t: f"\n=== {t} ===")
    code = (lambda t: f"`{t}`") if markdown else (lambda t: t)
    out: list[str] = []
    if markdown:
        out.append("# AgentSound catalog\n\nGenerated by `python -m agentsound catalog --markdown`. Search everything "
                   "with `python -m agentsound find WORD`.")

    if 'engine' in sections:
        mods = engine_modules()
        out.append(h('Engine: instruments and effects'))
        if not mods:
            out.append("(engine not built: cmake --build --preset release)")
        for kind in ('instrument', 'effect'):
            names = sorted(n for n, m in mods.items() if m['kind'] == kind)
            out.append(f"{kind}s ({len(names)}), full params: python -m agentsound params <type>")
            for n in names:
                ps = mods[n]['params']
                choice = next((p for p in ps if p.get('choices') and p['name'] in
                               ('mode', 'type', 'kit', 'style', 'speed', 'vowel')), None)
                extra = f" [{choice['name']}: {' '.join(choice['choices'])}]" if choice else ''
                side = ' (sidechain)' if mods[n].get('sidechain') else ''
                line = f"{n}{side}: {MODULES.get(n, '(no description)')}{extra}; {len(ps)} params"
                out.append(('- ' if markdown else '  ') + (f"**{n}**{line[len(n):]}" if markdown else line))

    if 'patches' in sections:
        from . import patches
        names = patches.list('')
        out.append(h(f'Patches ({len(names)}): inst/fx presets by name, patches.get(name) or song.track(..., patch=)'))
        groups: dict[str, list[str]] = {}
        for n in names:
            groups.setdefault(n.split('/')[0], []).append(n.split('/', 1)[-1])
        for g, ns in groups.items():
            out.append(f"{'- ' if markdown else '  '}{g}/ ({len(ns)}): {', '.join(ns)}")
        out.append(f"{'' if markdown else '  '}details: python -m agentsound patches <prefix> -v; audition: "
                   f"python -m agentsound audition <patch>")

    if 'bands' in sections:
        from . import bands
        names = bands.list()
        out.append(h(f"Band presets ({len(names)}): b = bands.make('name', song) / bands.<name>(song) - a complete, "
                     f"mixed ensemble (roles -> tracks, returns, sidechains, master, analysis profile)"))
        for n in names:
            p = bands.get(n)
            out.append(f"{'- ' if markdown else '  '}{code(n)} [{p.genre}] roles {', '.join(p.roles)}"
                       + (f": {p.description}" if p.description else '') + (f" (tuned: {p.tuned})" if p.tuned else ''))
        out.append(f"{'' if markdown else '  '}how to play each: print(b.describe()) / b.notes; list: python -m "
                   f"agentsound bands [genre]")

    if 'dx7' in sections:
        voices = dx7_voices()
        out.append(h(f"DX7 ROM voices ({len(voices)}): inst.dx7('NAME')"))
        if not dx7_banks_installed():
            out.append(f"{'' if markdown else '  '}{DX7_NO_BANKS}")
        banks: dict[str, list[str]] = {}
        for v in voices:
            banks.setdefault(v['bank'], []).append(v['name'].strip())
        for b, ns in banks.items():
            out.append(f"{'- ' if markdown else '  '}{b}: {', '.join(ns)}")

    if 'soundfonts' in sections:
        out.append(h("SoundFonts: inst.sf2('Preset Name') (GeneralUser GS) or inst.sf2(file='samples/<id>/X.sf2', "
                     "preset=...)"))
        for f in soundfont_files():
            pres = sf2_presets(f)
            melodic = [p for p in pres if p['bank'] != 128]
            kits = [p for p in pres if p['bank'] == 128]
            out.append(f"{'- ' if markdown else '  '}{code(asset_rel(f))}: {len(melodic)} melodic presets, "
                       f"{len(kits)} drum kits ({', '.join(k['name'] for k in kits[:14])}"
                       f"{' ...' if len(kits) > 14 else ''})")
        out.append(f"{'' if markdown else '  '}names: python -m agentsound sf2 [search] [--file F]; raw samples: "
                   f"--samples")

    if 'samples' in sections:
        from . import library
        try:
            packs = library.load_manifest()
        except library.LibraryError:
            packs = []
        inst = [p for p in packs if library.installed(p)]
        out.append(h(f"Sample packs: {len(inst)} installed of {len(packs)} in assets/samples/manifest.json"))
        for p in sorted(packs, key=lambda p: (p.get('category', ''), p['id'])):
            mark = 'installed' if library.installed(p) else 'available'
            out.append(f"{'- ' if markdown else '  '}{p['id']} [{p.get('category', '?')}; "
                       f"{', '.join(p.get('genres', []))}; {p['license']}; {mark}]: {p['title']}")
            idx = pack_index(library.pack_dir(p), rebuild=reindex) if library.installed(p) else None
            if idx:
                out.extend(_index_lines(p, idx, markdown))
        out.append(f"{'' if markdown else '  '}fetch: python -m agentsound samples fetch <id>; use: "
                   f"inst.sfz('samples/<id>/<file>.sfz') (SFZ instruments: python -m agentsound sfz FILE), "
                   f"inst.kit('samples/<id>/<dir>') (any drum one-shots, Hydrogen / DrumGizmo kits: python -m agentsound "
                   f"kit DIR), inst.multisample('samples/<id>/<dir>') (note-named samples), inst.organ('samples/<id>', "
                   f"stops=[...]) (GrandOrgue organs), inst.sampler(zones=[...])")

    if 'recipes' in sections:
        out.append(h('Recipes (read before composing)'))
        for name, title in recipes():
            out.append(f"{'- ' if markdown else '  '}{code('recipes/' + name)}: {title}")

    if 'profiles' in sections:
        from .cli import ANALYSIS_PROFILES
        out.append(h('Analysis profiles'))
        out.append(f"{'' if markdown else '  '}{', '.join(ANALYSIS_PROFILES)}: ANALYSIS = {{'profile': ..., "
                   f"'loudness': [lo, hi]}} in song.py or build --profile")

    if 'helpers' in sections:
        out.append(h('Python helpers (import agentsound as a; a.<module>.<name>)'))
        for mod, rows in helpers().items():
            out.append(f"{'### ' if markdown else '  '}{mod}")
            for sig, doc in rows:
                out.append(f"{'- ' if markdown else '    '}{code(sig.strip()) if markdown else sig}"
                           f"{' — ' + doc if doc else ''}")
    return '\n'.join(out).strip() + '\n'


def pack_usage(pack: dict) -> str | None:
    """Ready-to-paste line for a whole pack the kit builder / organ loader reads (Hydrogen, DrumGizmo, GrandOrgue)."""
    fmt = (pack.get('format', '') + ' ' + pack.get('title', '') + ' ' + pack['id']).lower()
    if 'grandorgue' in fmt:
        return (f"inst.organ('samples/{pack['id']}', stops=['Principal 8', ...])  # stops: python -m agentsound kit "
                f"samples/{pack['id']}")
    if 'h2drumkit' in fmt or 'hydrogen' in fmt or ('drumgizmo' in fmt and 'sfz' not in fmt):
        return (f"inst.kit('samples/{pack['id']}')  # GM drum kit (map: python -m agentsound kit samples/{pack['id']})")
    return None


def folder_usage(pack: dict, f: dict) -> str | None:
    """inst.kit(...) for a folder of drum one-shots (drum / percussion packs), inst.multisample(...) for note-named
    samples."""
    pack_id = pack['id']
    where = f"samples/{pack_id}/{f['dir']}" if f['dir'] != '.' else f"samples/{pack_id}"
    if re.search(r'bpm|loop|beat|chord|fill|phrase|groove', f['dir'], re.I):
        return None                                   # tempo-bound material, not an instrument
    if pack.get('category') in ('drums', 'percussion'):
        if f.get('drumWords') and f['files'] <= 400 and f['mapping'] != 'note-names':
            return f"inst.kit('{where}')"
        return None
    notes = f.get('notes')
    if notes and f['mapping'] != 'gm-drum-names' and notes[2] >= 3 and notes[0] >= 12 and notes[1] - notes[0] <= 72:
        return f"inst.multisample('{where}')"
    return None


def _index_lines(pack: dict, idx: dict, markdown: bool) -> list[str]:
    pad = '    ' if not markdown else '  - '
    programs = idx.get('sfzPrograms')
    sfz_text = ''
    if idx['sfz'] and not programs:
        sfz_text = f"; sfz: {', '.join(idx['sfz'][:6])}{' ...' if len(idx['sfz']) > 6 else ''}"
    elif programs:
        sfz_text = f"; {len(programs)} sfz instruments"
    lines = [f"{pad}{idx['audioFiles']} audio files, {_human(idx['bytes'])}" + sfz_text
             + (f"; sf2: {', '.join(idx['sf2'])}" if idx['sf2'] else '')]
    usage = pack_usage(pack)
    if usage:
        lines.append(f"{pad}  {usage}")
    for rel, info in list((programs or {}).items())[:8]:
        lines.append(f"{pad}  {sfz_usage(pack['id'], rel, info)}")
    if programs and len(programs) > 8:
        lines.append(f"{pad}  ... {len(programs) - 8} more .sfz (python -m agentsound find {pack['id']} --in samples)")
    shown = idx['folders'][:12]
    for f in shown:
        bits = [f"{f['files']} files", f['mapping']]
        if 'notes' in f:
            bits.append(f"{_note_name(f['notes'][0])}-{_note_name(f['notes'][1])} ({f['notes'][2]} roots)")
        if 'velocityLayers' in f:
            bits.append(f"{f['velocityLayers']} vel")
        if 'roundRobins' in f:
            bits.append(f"{f['roundRobins']} rr")
        use = folder_usage(pack, f) if not usage and not idx.get('sfz') and not idx.get('sf2') else None
        lines.append(f"{pad}  samples/{pack['id']}/{f['dir'] if f['dir'] != '.' else ''}: {', '.join(bits)}; "
                     f"e.g. {', '.join(f['examples'][:3])}" + (f"  -> {use}" if use else ''))
    rest = len(idx['folders']) - len(shown) + idx.get('foldersTruncated', 0)
    if rest > 0:
        lines.append(f"{pad}  ... {rest} more folders (python -m agentsound find <word> --in samples)")
    return lines


# -------------------------------------------------------------------------------- search

def search(words: list[str], only: str | None = None, limit: int = 25) -> str:
    terms = [w.lower() for w in words]

    def hit(*texts) -> bool:
        blob = ' '.join(t for t in texts if t).lower()
        return all(t in blob for t in terms)

    out: list[str] = []

    def section(title: str, rows: list[str]) -> None:
        if rows:
            out.append(f"=== {title} ({len(rows)}{' shown: ' + str(limit) if len(rows) > limit else ''})")
            out.extend('  ' + r for r in rows[:limit])

    want = (lambda s: only in (None, s))
    if want('engine'):
        rows = []
        for n, m in sorted(engine_modules().items()):
            if hit(n, MODULES.get(n, '')):
                rows.append(f"{n} ({m['kind']}): {MODULES.get(n, '')}")
            for p in m['params']:
                if hit(n, p['name'], p.get('help', ''), ' '.join(p.get('choices') or [])):
                    rows.append(f"{n}.{p['name']}: {p.get('help', '')[:150]}")
        section('engine modules and params', rows)
    if want('patches'):
        from . import patches
        rows = []
        for n in patches.list(''):
            p = patches.get(n)   # (sampled patches stay unexpanded: their .sfz is read when a song renders)
            if hit(n, p.notes):
                first = p.notes.strip().splitlines()[0] if p.notes.strip() else ''
                rows.append(f"{n}: {first}")
        section('patches', rows)
    if want('bands'):
        from . import bands
        rows = []
        for n in bands.list():
            p = bands.get(n)
            if hit(n, p.genre, ' '.join(p.roles), p.description, p.tuned):
                rows.append(f"{n} [{p.genre}] roles {', '.join(p.roles)}: {p.description}  -> b = bands.{n}(song)")
        section('band presets: agentsound.bands', rows)
    if want('dx7'):
        if not dx7_banks_installed():
            if only == 'dx7':
                out.append(f"=== DX7 voices: {DX7_NO_BANKS}")
        else:
            section("DX7 voices: inst.dx7('NAME')", [f"{v['name'].strip()}  ({v['id']})" for v in dx7_voices()
                                                     if hit(v['name'])])
    if want('soundfonts'):
        rows = []
        for f in soundfont_files():
            for p in sf2_presets(f):
                if hit(p['name'], 'drum kit' if p['bank'] == 128 else ''):
                    rows.append(f"{p['name']}  ({p['id']}, {asset_rel(f)})"
                                + ('  -> inst.sf2(bank=128, program=%d)' % p['program'] if p['bank'] == 128 else ''))
        section("SoundFont presets: inst.sf2('Name') / inst.sf2(file=..., preset='bank:program')", rows)
    if want('samples'):
        from . import library
        rows = []
        try:
            packs = library.load_manifest()
        except library.LibraryError:
            packs = []
        for p in packs:
            if hit(p['id'], p['title'], p.get('category', ''), ' '.join(p.get('genres', [])), p.get('notes', ''),
                   p.get('format', '')):
                rows.append(f"pack {p['id']} [{p.get('category', '?')}, {p['license']}, "
                            f"{'installed' if library.installed(p) else 'not installed'}]: {p['title']}")
                if pack_usage(p):
                    rows.append(f"  {pack_usage(p)}")
            idx = pack_index(library.pack_dir(p)) if library.installed(p) else None
            for f in (idx or {}).get('folders', []):
                if hit(p['id'], f['dir'], ' '.join(f['examples']), ' '.join(f.get('drumWords', []))):
                    use = (folder_usage(p, f) if not pack_usage(p) and not idx.get('sfz') and not idx.get('sf2')
                           else None)
                    rows.append(f"samples/{p['id']}/{f['dir']}: {f['files']} files ({f['mapping']}), e.g. "
                                f"{', '.join(f['examples'][:3])}" + (f"  -> {use}" if use else ''))
            programs = (idx or {}).get('sfzPrograms')
            fragments = set((idx or {}).get('sfzFragments') or [])
            for s in (idx or {}).get('sfz', []):
                if s in fragments or not hit(p['id'], s, ' '.join((programs or {}).get(s, {}).get('articulations', []))):
                    continue
                rows.append(sfz_usage(p['id'], s, (programs or {}).get(s)))
            for s in (idx or {}).get('sf2', []):
                if hit(p['id'], s):
                    rows.append(f"inst.sf2(file='samples/{p['id']}/{s}', preset=...)  # presets: python -m agentsound sf2 "
                                f"--file samples/{p['id']}/{s}")
        section('sample packs (assets/samples)', rows)
    if want('recipes'):
        rows = []
        for path in sorted((REPO / 'recipes').glob('*.md')):
            for i, ln in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if hit(ln):
                    rows.append(f"recipes/{path.name}:{i}: {ln.strip()[:150]}")
        section('recipes', rows)
    if want('helpers'):
        rows = [f"{mod}.{sig.strip().lstrip('.')}: {doc}" for mod, fns in helpers().items() for sig, doc in fns
                if hit(mod, sig, doc)]
        section('python helpers', rows)
    return '\n'.join(out) + '\n' if out else f"nothing found for {' '.join(words)!r}\n"
