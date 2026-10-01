"""Phone-ready delivery of a render: sample credits, cover art and mp3 ID3v2 tags.

`python -m agentsound build` runs it after the engine:
  out/credits.txt   every sample pack / SoundFont / impulse response the render JSON references (sampler
                    zones and dirs, sf2 'file' - the default GeneralUser GS too -, any 'ir' or other file path
                    param), with license and attribution from the pack's SOURCE.json (or the manifest). The build
                    summary warns about packs that are non-commercial (NC), no-redistribution or of unclear
                    license (fine for private listening; check before publishing) and lists the attributions
                    CC-BY packs require when the song is published.
  out/cover.png     album cover (engine `cover`, deterministic; cached via out/cover.json)
  out/mix.mp3       320 kbps with ID3v2.3 tags: title, artist, album, album artist, genre, year, BPM (TBPM), key
                    (TKEY), comment (with the credits) and the cover as attached picture (JPEG) - Telegram and
                    phone players show title, performer and cover from these.

song.py may set (both optional; unknown keys are errors):
    METADATA = {'title': 'Night Drive', 'artist': 'AgentSound', 'album': 'Neon Nights', 'genre': 'Synthwave',
                'year': 2026, 'comment': 'first take', 'track': 3, 'composer': '...', 'copyright': '...'}
    COVER = {'style': 'outrun', 'palette': 'sunset', 'title': 'NIGHT DRIVE', 'subtitle': 'AgentSound', 'seed': 7}
    COVER = {'file': 'art/cover.jpg'}      # your own image (relative to the song folder)
    COVER = False                          # no cover
Defaults: title = the Song's title, artist 'AgentSound', album 'AgentSound', genre from the cover style,
year = this year, cover style from the analysis profile (synthwave / dreamwave / darksynth) or the genre, else
'synthwave'; cover title = the song title, subtitle = the artist, seed = the song seed.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSETS = Path(os.environ['AGENTSOUND_ASSETS']).resolve() if os.environ.get('AGENTSOUND_ASSETS') else REPO / 'assets'

METADATA_KEYS = ('title', 'artist', 'album', 'genre', 'year', 'comment', 'track', 'composer', 'copyright')
COVER_KEYS = ('style', 'palette', 'title', 'subtitle', 'seed', 'file', 'size')
COVER_STYLES = ('synthwave', 'outrun', 'dreamwave', 'darksynth', 'jazz', 'classical', 'rock', 'pop')
GENRE_OF_STYLE = {'synthwave': 'Synthwave', 'outrun': 'Synthwave', 'dreamwave': 'Synthwave', 'darksynth': 'Darksynth',
                  'jazz': 'Jazz', 'classical': 'Classical', 'rock': 'Rock', 'pop': 'Pop'}
DEFAULT_ARTIST = 'AgentSound'
# Analysis profiles that are not cover styles themselves (engine/analysis/Profiles.cpp).
PROFILE_STYLE = {'film': 'classical', 'piano': 'classical'}
PROFILE_GENRE = {'film': 'Soundtrack', 'piano': 'Classical'}

# SoundFonts shipped in assets/soundfonts (no SOURCE.json there).
KNOWN_SOUNDFONTS = {
    'generaluser-gs.sf2': {'title': 'GeneralUser GS v2.0', 'license': 'GeneralUser-GS-2.0',
                           'licenseText': 'free for music creation, private or commercial',
                           'attribution': 'S. Christian Collins', 'homepage': 'https://www.schristiancollins.com'},
}
_PATH_KEYS = {'file', 'dir', 'ir', 'sfz', 'path', 'folder', 'impulse', 'soundfont'}
_AUDIO_EXT = ('.wav', '.flac', '.aif', '.aiff', '.ogg', '.sf2', '.sf3', '.sfz', '.mp3')


class DeliveryError(Exception):
    pass


# ------------------------------------------------------------------------------ settings

def check_metadata(obj, where: str = 'METADATA') -> dict:
    if obj is None:
        return {}
    if not isinstance(obj, dict):
        raise DeliveryError(f"{where} must be a dict like {{'artist': 'AgentSound', 'genre': 'Synthwave'}}, got {obj!r}")
    extra = [k for k in obj if k not in METADATA_KEYS]
    if extra:
        raise DeliveryError(f"{where}: unknown key(s) {', '.join(map(repr, extra))} (allowed: {', '.join(METADATA_KEYS)})")
    out = {}
    for k, v in obj.items():
        if k in ('year', 'track'):
            if isinstance(v, bool) or not isinstance(v, int) or not (1 <= v <= 9999):
                raise DeliveryError(f"{where}: {k!r} must be a positive integer, got {v!r}")
        elif not isinstance(v, str) or not v.strip():
            raise DeliveryError(f"{where}: {k!r} must be a non-empty string, got {v!r}")
        out[k] = v.strip() if isinstance(v, str) else v
    return out


def check_cover(obj, where: str = 'COVER') -> dict | None:
    """None = no cover (COVER = False); {} = defaults."""
    if obj is False:
        return None
    if obj is None or obj is True:
        return {}
    if not isinstance(obj, dict):
        raise DeliveryError(f"{where} must be a dict like {{'style': 'outrun'}} or False, got {obj!r}")
    extra = [k for k in obj if k not in COVER_KEYS]
    if extra:
        raise DeliveryError(f"{where}: unknown key(s) {', '.join(map(repr, extra))} (allowed: {', '.join(COVER_KEYS)})")
    out = dict(obj)
    unused = [k for k in ('palette', 'title', 'subtitle', 'seed', 'size') if k in out]
    if 'file' in out and unused:
        raise DeliveryError(f"{where}: {', '.join(map(repr, unused))} only apply to a generated cover, not to 'file' "
                            f"(an own image is used as it is)")
    if 'style' in out and out['style'] not in COVER_STYLES:
        raise DeliveryError(f"{where}: unknown style {out['style']!r} (styles: {', '.join(COVER_STYLES)})")
    if 'palette' in out:
        p = out['palette']
        if isinstance(p, (list, tuple)):
            if not 1 <= len(p) <= 3 or not all(isinstance(c, str) and re.fullmatch(r'#?[0-9a-fA-F]{6}', c) for c in p):
                raise DeliveryError(f"{where}: 'palette' as a list takes 1-3 '#rrggbb' colours, got {p!r}")
            out['palette'] = ','.join(c if c.startswith('#') else '#' + c for c in p)
        elif not isinstance(p, str):
            raise DeliveryError(f"{where}: 'palette' must be a palette name or a list of '#rrggbb' colours, got {p!r}")
    for k in ('title', 'subtitle', 'file'):
        if k in out and not isinstance(out[k], str):
            raise DeliveryError(f"{where}: {k!r} must be a string")
    if 'seed' in out and (isinstance(out['seed'], bool) or not isinstance(out['seed'], int) or not 0 <= out['seed'] <= 0xFFFFFFFF):
        raise DeliveryError(f"{where}: 'seed' must be an int 0..4294967295")
    if 'size' in out and (isinstance(out['size'], bool) or not isinstance(out['size'], int) or not 256 <= out['size'] <= 4000):
        raise DeliveryError(f"{where}: 'size' must be 256..4000 px")
    return out


def id3_key(key) -> str:
    """ID3 TKEY ('Am', 'F#', 'Dbm') from a theory Key or a key name like 'A minor'."""
    tonic = getattr(key, 'tonic_name', None)
    mode = getattr(key, 'mode', None)
    if tonic is None:
        m = re.match(r'^\s*([A-Ga-g])([#b]?)\s*(.*)$', str(key))
        if not m:
            return ''
        tonic = m.group(1).upper() + m.group(2)
        rest = m.group(3).strip().lower()
        mode = 'minor' if rest in ('m', 'min', '-') else (rest or 'major')
    minor = str(mode).lower() in ('minor', 'aeolian', 'dorian', 'phrygian', 'locrian', 'harmonic_minor', 'melodic_minor',
                                  'harmonic minor', 'melodic minor', 'minor_pentatonic', 'blues')
    return f"{tonic}{'m' if minor else ''}"


def default_style(metadata: dict, profile: str | None = None) -> str:
    """The cover style a song gets without COVER['style']: its analysis profile if that is a style (or maps
    to one: film -> classical), else a style named in METADATA['genre'], else 'synthwave'."""
    if profile in COVER_STYLES:
        return profile
    if profile in PROFILE_STYLE:
        return PROFILE_STYLE[profile]
    genre = (metadata.get('genre') or '').lower()
    return next((s for s in COVER_STYLES if s in genre), 'synthwave')


def cover_spec(title: str, seed: int, metadata: dict, cover: dict, profile: str | None = None) -> dict:
    style = cover.get('style') or default_style(metadata, profile)
    if 'file' in cover:
        return {'file': cover['file'], 'style': style}
    return {'style': style, 'title': cover.get('title', metadata.get('title', title)),
            'subtitle': cover.get('subtitle', metadata.get('artist', DEFAULT_ARTIST)), 'palette': cover.get('palette', ''),
            'seed': int(cover.get('seed', seed)), 'size': int(cover.get('size', 1400))}


def tags(title: str, tempo: float, key, metadata: dict, style: str, credits_comment: str = '',
         profile: str | None = None) -> dict:
    """ffmpeg -metadata key -> value (ID3v2.3)."""
    t = {'title': metadata.get('title', title), 'artist': metadata.get('artist', DEFAULT_ARTIST),
         'album': metadata.get('album', 'AgentSound'), 'album_artist': metadata.get('artist', DEFAULT_ARTIST),
         'genre': metadata.get('genre', PROFILE_GENRE.get(profile or '', GENRE_OF_STYLE.get(style, 'Electronic'))),
         'date': str(metadata.get('year', _dt.date.today().year)), 'TBPM': str(int(round(tempo)))}
    k = id3_key(key)
    if k:
        t['TKEY'] = k
    for src, dst in (('track', 'track'), ('composer', 'composer'), ('copyright', 'copyright')):
        if src in metadata:
            t[dst] = str(metadata[src])
    comment = ' | '.join(x for x in (metadata.get('comment', ''), credits_comment) if x)
    t['comment'] = comment or 'Made with AgentSound'
    return t


# ------------------------------------------------------------------------------ credits

def license_class(lic: str) -> str:
    """free | attribution | sharealike | nc | noredist | unclear. Every Creative Commons BY license (CC-BY, BY-SA,
    BY-NC, in any spelling: 'CC BY-SA 3.0', 'Creative Commons Attribution-ShareAlike 4.0') needs an attribution."""
    l = re.sub(r'[\s_]+', '-', (lic or '').strip().lower())
    l = (l.replace('creative-commons-', 'cc-').replace('attribution-noncommercial', 'by-nc')
         .replace('attribution-sharealike', 'by-sa').replace('attribution', 'by').replace('sharealike', 'sa'))
    if l.startswith('by-') or l == 'by':
        l = 'cc-' + l

    if not l or 'unclear' in l or 'unverified' in l:
        return 'unclear'
    if re.search(r'(^|-)nc(-|$)', l) or 'noncommercial' in l or 'non-commercial' in l:
        return 'nc'
    if 'no-redistribution' in l or 'noredist' in l:
        return 'noredist'
    if l.startswith('cc-by-sa'):
        return 'sharealike'
    if l.startswith('cc-by') or 'sampling-plus' in l or 'mixed-cc0-cc-by' in l:
        return 'attribution'
    if l in ('gpl', 'gpl-2.0', 'gpl-3.0'):
        return 'unclear'
    return 'free'


def _walk_paths(obj, key: str = '', out: list | None = None) -> list:
    """(key, value) of every string in params that looks like a file / folder path."""
    out = [] if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            _walk_paths(v, str(k), out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_paths(v, key, out)
    elif isinstance(obj, str):
        s = obj.strip()
        looks = (key.lower() in _PATH_KEYS or s.lower().endswith(_AUDIO_EXT) or s.startswith(('samples/', 'soundfonts/', './', '../'))
                 or re.match(r'^[A-Za-z]:[\\/]', s) or s.startswith('/'))
        if looks and s and not s.startswith('*'):       # '*silence' / '*sine' / '*noise': sfz generators, no file
            out.append((key, s))
    return out


def asset_refs(render: dict) -> list[tuple[str, str]]:
    """(kind, path) of every asset the render references: kind 'sf2' (resolved against assets/soundfonts)
    or 'asset' (against assets/)."""
    refs = []
    nodes = list(render.get('tracks') or []) + list(render.get('buses') or []) + [render.get('master') or {}]
    def instrument(inst: dict) -> None:
        params = inst.get('params') or {}
        if inst.get('type') == 'stack':   # layered: every layer's instrument and fx chain
            for layer in params.get('layers') or []:
                instrument(layer.get('instrument') or {})
                chain(layer.get('fx') or [])
            return
        if inst.get('type') == 'sf2':
            f = params.get('file', 'GeneralUser-GS.sf2')
            refs.append(('sf2', f))
            params = {k: v for k, v in params.items() if k != 'file'}
        for _, p in _walk_paths(params):
            refs.append(('asset', p))

    def chain(fxs: list) -> None:
        for fx in fxs:
            for _, p in _walk_paths(fx.get('params') or {}):
                refs.append(('asset', p))

    for n in nodes:
        instrument(n.get('instrument') or {})
        chain(n.get('fx') or [])
    seen, out = set(), []
    for r in refs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _samples_dir() -> Path:
    from .library import SAMPLES
    return SAMPLES


def _classify(kind: str, path: str, samples: Path, assets: Path):
    """('pack', id) | ('soundfont', file name, full path) | ('file', path)."""
    p = path.replace('\\', '/')
    absolute = bool(re.match(r'^[A-Za-z]:/', p)) or p.startswith('/')
    if not absolute:
        rel = p[2:] if p.startswith('./') else p
        if kind == 'sf2' and not rel.startswith('samples/'):
            rel = 'soundfonts/' + rel
        parts = [x for x in rel.split('/') if x]
        if len(parts) >= 2 and parts[0] == 'samples' and not (len(parts) == 2 and parts[1].lower().endswith(_AUDIO_EXT)):
            return ('pack', parts[1])
        if len(parts) >= 2 and parts[0] == 'soundfonts':
            return ('soundfont', parts[-1], str(assets / rel))
        return ('file', str(assets / rel))
    ap = Path(p)
    voice = _voice_source(ap)
    if voice is not None:                    # a sung take rendered by agentsound.singer: the voicebank's licence
        return ('voice', voice['id'], voice)
    for root in (samples, assets / 'samples', REPO / 'assets' / 'samples'):
        try:
            rel = ap.resolve().relative_to(root.resolve())
            if rel.parts and not (len(rel.parts) == 1 and rel.parts[0].lower().endswith(_AUDIO_EXT)):   # a loose file is no pack
                return ('pack', rel.parts[0])
        except (ValueError, OSError):
            pass
    try:
        rel = ap.resolve().relative_to((assets / 'soundfonts').resolve())
        return ('soundfont', rel.name, str(ap))
    except (ValueError, OSError):
        pass
    return ('file', p)


def _voice_source(path: Path) -> dict | None:
    """The SOURCE.json of a voicebank next to a rendered vocal take (agentsound.singer writes it into
    <song>/samples/vocals/<voice>/), or None."""
    try:
        src = path.parent / 'SOURCE.json'
        if src.is_file():
            data = json.loads(src.read_text(encoding='utf-8'))
            if data.get('kind') == 'voice' and data.get('id'):
                return data
    except (OSError, ValueError):
        pass
    return None


def _pack_source(pack_id: str, samples: Path, manifest: dict | None) -> dict | None:
    src = samples / pack_id / 'SOURCE.json'
    try:
        return json.loads(src.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        pass
    if manifest is None:
        try:
            from .library import load_manifest
            manifest = {p['id']: p for p in load_manifest()}
        except Exception:
            manifest = {}
    return manifest.get(pack_id)


def collect_credits(render: dict, samples: Path | None = None, assets: Path | None = None, manifest: dict | None = None) -> dict:
    """{'sources': [...], 'attributions': [...], 'warnings': [...], 'comment': str}."""
    samples = samples or _samples_dir()
    assets = assets or ASSETS
    sources: dict[str, dict] = {}
    for kind, path in asset_refs(render):
        c = _classify(kind, path, samples, assets)
        if c[0] == 'pack':
            key = 'pack:' + c[1]
            if key in sources:
                continue
            info = _pack_source(c[1], samples, manifest)
            if info is None:
                sources[key] = {'kind': 'pack', 'id': c[1], 'title': c[1], 'license': 'Unknown (no SOURCE.json)',
                                'class': 'unclear'}
            else:
                lic = info.get('license', 'Unknown')
                sources[key] = {'kind': 'pack', 'id': c[1], 'title': info.get('title', c[1]), 'license': lic,
                                'licenseUrl': info.get('licenseUrl', ''), 'attribution': info.get('attribution', ''),
                                'homepage': info.get('homepage', info.get('url', '')), 'class': license_class(lic)}
        elif c[0] == 'voice':
            key = 'voice:' + c[1]
            if key in sources:
                continue
            info = c[2]
            lic = info.get('license', 'Unknown')
            cls = license_class(lic)
            if cls == 'free' and info.get('attribution'):
                cls = 'attribution'
            sources[key] = {'kind': 'voice', 'id': c[1], 'title': info.get('title', c[1]), 'license': lic,
                            'licenseUrl': info.get('licenseUrl', ''), 'attribution': info.get('attribution', ''),
                            'homepage': info.get('homepage', info.get('url', '')), 'class': cls,
                            'credit': info.get('credit', ''), 'restrictions': info.get('restrictions', '')}
        elif c[0] == 'soundfont':
            key = 'sf:' + c[1].lower()
            if key in sources:
                continue
            known = KNOWN_SOUNDFONTS.get(c[1].lower())
            if known:
                sources[key] = {'kind': 'soundfont', 'id': c[1], 'class': 'free', **known}
            else:
                sources[key] = {'kind': 'soundfont', 'id': c[1], 'title': c[1], 'license': 'Unknown (check its license file)',
                                'class': 'unclear'}
        else:
            key = 'file:' + c[1]
            if key not in sources:
                sources[key] = {'kind': 'file', 'id': c[1], 'title': Path(c[1]).name, 'license': 'Unknown (own file?)',
                                'class': 'unclear'}
    items = sorted(sources.values(), key=lambda s: (s['kind'], s['id']))
    attributions, warnings = [], []
    for s in items:
        cls = s['class']
        if cls in ('attribution', 'sharealike', 'nc') or (
                cls == 'unclear' and 'cc-by' in re.sub(r'[\s_]+', '-', s.get('license', '').lower())):

            who = s.get('attribution') or s['title']
            line = f"\"{s['title']}\" by {who}, {s['license']}" + (f" ({s['licenseUrl']})" if s.get('licenseUrl') else '')
            if cls == 'sharealike':
                line += ' - share-alike: a published song may have to carry the same license'
            attributions.append(line)
        why = {'nc': 'non-commercial license', 'noredist': 'no redistribution of the samples',
               'unclear': 'license unclear'}.get(cls)
        if s['kind'] == 'voice' and cls == 'nc':
            why = 'non-commercial voice (the voicebank or its vocoder)'
        if why:
            extra = ' (the pack notes say music made with it is fine)' if 'music-ok' in s.get('license', '').lower() else ''
            warnings.append(f"'{s['id']}' ({s['license']}): {why}{extra} - fine for private listening; check before publishing")
    comment = ''
    if items:
        parts = [f"{s['title']}" + (f" ({s['attribution']}, {s['license']})" if s.get('attribution') else f" ({s['license']})")
                 for s in items]
        comment = 'Sounds: ' + '; '.join(parts)
        if len(comment) > 900:
            comment = comment[:897] + '...'
    return {'sources': items, 'attributions': attributions, 'warnings': warnings, 'comment': comment}


def credits_text(credits: dict, title: str, artist: str) -> str:
    lines = [f"{title} - {artist}", "Made with AgentSound.", ""]
    if not credits['sources']:
        lines.append("Sounds: synthesised only (no sample packs, SoundFonts or impulse responses).")
    else:
        lines.append("Sample packs, SoundFonts, impulse responses and voicebanks used:")
        for s in credits['sources']:
            lines.append(f"- {s['title']} [{s['id']}]")
            lines.append(f"    license: {s['license']}" + (f" - {s['licenseText']}" if s.get('licenseText') else '') +
                         (f" ({s['licenseUrl']})" if s.get('licenseUrl') else ''))
            if s.get('attribution'):
                lines.append(f"    by: {s['attribution']}")
            if s.get('homepage'):
                lines.append(f"    source: {s['homepage']}")
            if s.get('credit'):
                lines.append(f"    credit: {s['credit']}")
            if s.get('restrictions'):
                lines.append(f"    terms: {s['restrictions']}")
    if credits['attributions']:
        lines += ["", "Required attributions when publishing:"] + [f"  {a}" for a in credits['attributions']]
    if credits['warnings']:
        lines += ["", "Check before publishing (fine for private listening):"] + [f"  {w}" for w in credits['warnings']]
    return '\n'.join(lines) + '\n'


# ------------------------------------------------------------------------------ cover + mp3

def make_cover(engine: Path, spec: dict, out_png: Path, song_dir: Path | None = None) -> Path:
    """Renders (or copies, for COVER['file']) the cover; skipped when out/cover.json already has this spec."""
    out_png.parent.mkdir(parents=True, exist_ok=True)
    if 'file' in spec:
        src = Path(spec['file'])
        if not src.is_absolute() and song_dir is not None:
            src = song_dir / src
        if not src.is_file():
            raise DeliveryError(f"COVER['file']: no image at {src}")
        return src
    stamp = out_png.with_suffix('.json')
    key = dict(spec, engine=hashlib.sha1(Path(engine).read_bytes()).hexdigest()[:12] if Path(engine).is_file() else '')
    try:
        if out_png.is_file() and json.loads(stamp.read_text(encoding='utf-8')) == key:
            return out_png
    except (OSError, ValueError):
        pass
    spec_file = out_png.with_name('cover.spec.json')
    spec_file.write_text(json.dumps({k: spec[k] for k in ('style', 'title', 'subtitle', 'palette', 'seed', 'size')},
                                    ensure_ascii=False), encoding='utf-8')
    proc = subprocess.run([str(engine), 'cover', '--spec', str(spec_file), '--out', str(out_png)], capture_output=True,
                          text=True, encoding='utf-8', errors='replace')
    spec_file.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise DeliveryError(f"cover failed: {(proc.stderr or proc.stdout).strip()[:300]}")
    stamp.write_text(json.dumps(key, ensure_ascii=False), encoding='utf-8')
    return out_png


def encode_mp3(ffmpeg: str, wav: Path, mp3: Path, tag_map: dict | None = None, cover: Path | None = None) -> tuple[bool, str]:
    """320 kbps mp3 with ID3v2.3 tags and the cover as front-cover picture (JPEG)."""
    cmd = [ffmpeg, '-y', '-hide_banner', '-loglevel', 'error', '-i', str(wav)]
    if cover is not None:
        # Centre-cropped to a square (an own COVER['file'] may not be one), baseline 4:2:0 JPEG (what every phone
        # and messenger decodes).
        cmd += ['-i', str(cover), '-map', '0:a', '-map', '1:v', '-c:v', 'mjpeg', '-q:v', '3',
                '-vf', "crop='min(iw,ih)':'min(iw,ih)',scale=1000:1000:flags=lanczos",
                '-pix_fmt', 'yuvj420p', '-disposition:v', 'attached_pic', '-metadata:s:v', 'title=Album cover',
                '-metadata:s:v', 'comment=Cover (front)']
    cmd += ['-codec:a', 'libmp3lame', '-b:a', '320k', '-id3v2_version', '3', '-write_id3v1', '1']
    for k, v in (tag_map or {}).items():
        cmd += ['-metadata', f"{k}={v}"]
    cmd.append(str(mp3))
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        return False, (proc.stderr or '').strip()[:300]
    return True, ''


def probe_tags(ffprobe: str, mp3: Path) -> dict:
    """{'tags': {...}, 'cover': bool} of an mp3 (ffprobe), keys lower-cased."""
    proc = subprocess.run([ffprobe, '-v', 'error', '-show_entries', 'format_tags:stream=codec_type,codec_name:stream_disposition=attached_pic',
                           '-of', 'json', str(mp3)], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        raise DeliveryError(f"ffprobe failed: {proc.stderr.strip()[:200]}")
    data = json.loads(proc.stdout or '{}')
    tagsd = {k.lower(): v for k, v in ((data.get('format') or {}).get('tags') or {}).items()}
    cover = any(s.get('codec_type') == 'video' and (s.get('disposition') or {}).get('attached_pic') == 1 for s in data.get('streams') or [])
    return {'tags': tagsd, 'cover': cover}


def find_ffprobe(ffmpeg: str | None) -> str | None:
    if not ffmpeg:
        return None
    p = Path(ffmpeg)
    cand = p.with_name('ffprobe' + p.suffix)
    return str(cand) if cand.is_file() else None
