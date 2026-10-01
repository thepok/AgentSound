"""The making-of film of a song: `python -m agentsound makingof songs/<slug>` -> songs/<slug>/out/making-of.mp4.

A documentary generated from the song's own files - the wish and the log (BRIEF.md), the form and the hook
(ARRANGEMENT.md, the render JSON), the sounds (SOUND.md), the players' logs (their move logs, recorded while
song.py builds), the A&R verdict and its revision (AR.md), the mix / master numbers (MIX.md, MASTER.md,
report.json), the credits (credits.txt) and the cover - then the song itself with audio-reactive scenes.

Chapters: the wish (cold open + title card) -> the team -> the blueprint (form, tempo, keys, energy, the hook) ->
meet the tracks (sound design; every part soloed from its stem, then the band back in) -> the performance (excerpts
with the players' moves popping on their frames) -> the verdict (A&R issues, before -> after) -> the song -> credits.

Pipeline (each step cached in songs/<slug>/out/makingof/):
  capture.py   the players' logs (song.py built with the placements recorded)
  facts.py     everything the film may say, read from the files
  story.py     the narration script (making-of.md: editable, --script writes it)
  narration.py the voice-over (Breeze TTS 2 in WSL / Windows SAPI / none), loudness-matched per speaker
  timeline.py  chapter spans, lines, music segments and their gain envelopes, the scene plan
  web/         the renderer: headless Chrome (WebGL2 + Canvas 2D) -> JPEG frames -> ffmpeg (H.264)
  soundtrack   ffmpeg: the song segments + stems + narration, ducked, into one AAC track

Requirements (dev tools, not the compose layer): Node >= 22, Chrome or Edge, ffmpeg (libx264); optional WSL with
Breeze TTS 2 for the narration."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import capture, facts as factsmod, narration, story, timeline

WEB = Path(__file__).resolve().parent / 'web'
REPO = Path(__file__).resolve().parents[2]


def log(msg: str) -> None:
    print(msg, flush=True)


# ------------------------------------------------------------------------------------------------ tools

def find_tool(name: str, explicit: str | None = None) -> str | None:
    if explicit:
        return explicit if Path(explicit).is_file() or shutil.which(explicit) else None
    if name == 'ffmpeg':
        from ..cli import find_ffmpeg
        return find_ffmpeg()
    return shutil.which(name)


def check_tools(ffmpeg: str | None, node: str | None, chrome: str | None) -> list[str]:
    """What is missing for a render (empty = all there)."""
    miss = []
    if not ffmpeg:
        miss.append('ffmpeg (https://ffmpeg.org, with libx264)')
    if not node:
        miss.append('Node.js >= 22 (https://nodejs.org)')
    else:
        try:
            v = subprocess.run([node, '--version'], capture_output=True, text=True, timeout=20).stdout.strip()
            if int(v.lstrip('v').split('.')[0]) < 22:
                miss.append(f'Node.js >= 22 (found {v}: needs the built-in WebSocket)')
        except (OSError, ValueError, subprocess.TimeoutExpired):
            miss.append('Node.js >= 22')
    if not chrome:
        miss.append('Chrome or Edge (or set AGENTSOUND_CHROME)')
    return miss


def find_chrome(explicit: str | None = None) -> str | None:
    cands = [explicit, os.environ.get('AGENTSOUND_CHROME'),
             'C:/Program Files/Google/Chrome/Application/chrome.exe',
             'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
             'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
             'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
             '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
             '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
    return next((c for c in cands if c and Path(c).is_file()), None)


# ------------------------------------------------------------------------------------------------ facts (cached)

def gather(song_dir: Path, work: Path, *, refresh: bool = False) -> dict:
    """The song's facts with the players' logs (song.py is built once per change of song.py / the render)."""
    song_py = song_dir / 'song.py'
    rj = song_dir / 'out' / 'song.render.json'
    key = hashlib.sha256(song_py.read_bytes() + str(rj.stat().st_mtime_ns if rj.is_file() else 0).encode()).hexdigest()
    cache = work / 'moves.json'
    data = None
    if cache.is_file() and not refresh:
        d = json.loads(cache.read_text(encoding='utf-8'))
        if d.get('key') == key:
            data = d
    if data is None:
        log('making-of: building song.py with the players recorded ...')
        song, mlog = capture.capture(song_py)
        meta = dict((getattr(song, 'delivery_settings', None) or {}).get('METADATA') or {})
        data = {'key': key, 'log': mlog, 'metadata': {k: v for k, v in meta.items() if isinstance(v, (str, int, float))}}
        cache.write_text(json.dumps(data), encoding='utf-8')

    class _Song:   # the bits of the Song collect() reads
        delivery_settings = {'METADATA': data['metadata']}
    return factsmod.collect(song_dir, moves_log=data['log'], song=_Song())


# ------------------------------------------------------------------------------------------------ project

def _fixes(facts: dict) -> list[dict]:
    out = []
    for r in facts['revision']:
        good = [p for p in r['pairs'] if len(p['label']) <= 48 and p['label'][:1].isalpha()]
        key = [p for p in good if p.get('key')] + [p for p in good if not p.get('key')]
        head = story.re.sub(r'^\[\w+\]\s*', '', r['head'])
        head = story.re.sub(r'\s*->.*$', '', head)
        head = story.re.sub(r'\s*\([^)]*\)\s*\.?$', '', head)
        if key:
            out.append({'head': head, 'status': r['status'] or 'revised', 'pairs': key[:3]})
    return out


def build_project(song_dir: Path, facts: dict, film, tl: dict, *, width: int, height: int,
                  narration_credit: str) -> dict:
    tracks = [{'id': t['id'], 'family': t['family'], 'color': t['color'], 'player': t.get('player', ''),
               'notes': t['notes']} for t in facts['tracks']]
    moves = [dict(m, label=story.move_label(m)) for m in facts['moves']]
    team = story.team_cards(facts)
    return {
        'width': width, 'height': height, 'fps': tl['fps'], 'frames': tl['frames'], 'duration': tl['duration'],
        'mixWav': str((song_dir / 'out' / 'mix.wav').resolve()),
        'cover': facts['cover'], 'title': facts['title'], 'artist': facts['artist'], 'genre': facts['genre'],
        'family': timeline.genre_family(facts),
        'song': {k: facts[k] for k in ('duration', 'sections', 'parts', 'energy', 'tempo', 'lufs', 'truePeak', 'lra',
                                       'plr', 'bars', 'meters', 'notesTotal', 'key', 'bpmRange')},
        'tracks': tracks, 'moves': moves, 'hook': facts['hook'], 'players': facts['players'],
        'chapters': tl['chapters'], 'captions': tl['captions'],
        'segments': [{k: v for k, v in s.items()} for s in tl['segments']],
        'scenes': timeline.scene_plan(facts, film.scene_map, film.highway),
        'wish': facts['wish'], 'team': team,
        'sound': {'heroes': story.hero_names(facts),
                  'measured': sorted(facts['soundMeasured'],
                                     key=lambda x: 0 if story.re.search(r'\bwon\b|\bchosen\b', x)
                                     else 1 if x.startswith('Result') else 2)},
        'crisis': {'verdict': facts['verdict'],
                   'issues': [{k: i[k] for k in ('n', 'severity', 'title', 'owner')} for i in facts['issues']],
                   'fixes': _fixes(facts), 'proposal': facts['proposal']},
        'credits': {'packs': facts['credits']['packs'], 'attribution': facts['credits']['attribution'],
                    'narration': narration_credit, 'files': facts['files'] + ['song.render.json', 'report.json',
                                                                             'the players\u2019 logs']},
        'roleColors': factsmod.ROLE_COLORS, 'roleTitles': factsmod.ROLE_TITLES,
    }


# ------------------------------------------------------------------------------------------------ soundtrack

def _vol_expr(env: list, gain_db: float = 0.0) -> str:
    """ffmpeg volume expression (t = segment-local seconds) of a dB envelope."""
    if not env:
        return f"{10 ** (gain_db / 20):.6f}"
    expr = f"{env[-1][1] + gain_db:.3f}"
    for (t0, g0), (t1, g1) in reversed(list(zip(env, env[1:]))):
        if t1 - t0 < 1e-6:
            continue
        seg = f"{g0 + gain_db:.3f}+({g1 - g0:.3f})*(t-{t0:.4f})/{t1 - t0:.4f}"
        expr = f"if(lt(t,{t1:.4f}),{seg},{expr})"
    expr = f"if(lt(t,{env[0][0]:.4f}),{env[0][1] + gain_db:.3f},{expr})"
    return f"pow(10,({expr})/20)"


def soundtrack(tl: dict, facts: dict, voice_files: dict, ffmpeg: str, out_wav: Path, stems_dir: Path) -> None:
    """Mix the film's audio: every music segment (the mix, or summed stems for a solo) cut from its file with its
    gain envelope, every narration line at its time, into one 48 kHz stereo WAV of the film's length."""
    inputs, chains, music, voices = [], [], [], []
    mix = facts.get('mixWav') or str(Path(stems_dir).parent / 'mix.wav')
    for i, s in enumerate(tl['segments']):
        dur = s['v1'] - s['v0']
        if dur <= 0.02:
            continue
        delay = int(round(s['v0'] * 1000))
        if s['kind'] == 'solo':
            files = [Path(stems_dir) / f'{x}.wav' for x in s['stems']]
            files = [f for f in files if f.is_file()]
            if not files:
                continue
            labels = []
            for f in files:
                inputs += ['-ss', f"{s['s0']:.4f}", '-t', f"{dur:.4f}", '-i', str(f)]
                labels.append(f"[{len(inputs) // 6 - 1}:a]")
            src = f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0," if len(labels) > 1 else labels[0]
            chains.append(f"{src}aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                          f"volume='{_vol_expr(s['env'], s.get('gainDb', 0.0))}':eval=frame,adelay={delay}|{delay}[m{i}]")
        else:
            inputs += ['-ss', f"{max(0.0, s['s0']):.4f}", '-t', f"{dur:.4f}", '-i', s.get('file') or mix]
            k = len(inputs) // 6 - 1
            chains.append(f"[{k}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                          f"volume='{_vol_expr(s['env'], s.get('gainDb', 0.0))}':eval=frame,"
                          f"adelay={delay}|{delay}[m{i}]")
        music.append(f"[m{i}]")
    for j, v in enumerate(tl['voices']):
        vf = voice_files.get(id(v['line']))
        if not vf:
            continue
        inputs += ['-ss', '0', '-t', f"{vf['seconds'] + 0.1:.3f}", '-i', vf['wav']]
        k = len(inputs) // 6 - 1
        delay = int(round(v['t'] * 1000))
        chains.append(f"[{k}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                      f"adelay={delay}|{delay}[v{j}]")
        voices.append(f"[v{j}]")
    total = tl['duration']
    parts = []
    if music:
        chains.append(f"{''.join(music)}amix=inputs={len(music)}:normalize=0:dropout_transition=0[mus]")
        parts.append('[mus]')
    if voices:
        chains.append(f"{''.join(voices)}amix=inputs={len(voices)}:normalize=0:dropout_transition=0[vox]")
        parts.append('[vox]')
    chains.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{total:.3f}[sil]")
    parts.append('[sil]')
    chains.append(f"{''.join(parts)}amix=inputs={len(parts)}:normalize=0:dropout_transition=0:duration=longest,"
                  f"atrim=0:{total:.3f},alimiter=limit=0.95:level=false:attack=2:release=60[out]")
    script = out_wav.with_suffix('.filter.txt')
    script.write_text(';\n'.join(chains), encoding='utf-8')
    cmd = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', *inputs, '-filter_complex_script', str(script),
           '-map', '[out]', '-c:a', 'pcm_s24le', str(out_wav)]
    r = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
    if r.returncode != 0:
        raise RuntimeError(f"soundtrack: ffmpeg failed: {r.stderr[-1500:]}")


# ------------------------------------------------------------------------------------------------ the film

def film_path(song_dir: Path) -> Path:
    return song_dir / 'film.py'


def load_film(song_dir: Path, facts: dict, work: Path, episodes: list | None, n_excerpts: int = 3):
    """(Film, from_file): songs/<slug>/film.py when there is one, else the generated draft (written to
    out/makingof/film.draft.py so it can be looked at)."""
    from . import draft
    p = film_path(song_dir)
    if p.is_file():
        return draft.load(p, facts), True
    src = draft.draft_source(facts, n_excerpts=n_excerpts, episodes=episodes)
    return draft.load_source(src, facts, work / 'film.draft.py'), False


def export_script(film, facts: dict) -> str:
    """The film's narration as Markdown (making-of.md): a read-only review copy - the film is edited in film.py."""
    out = [f"# Making of: {facts['title']} - the narration", '',
           '<!-- Generated from the film (songs/%s/film.py or the draft); edit film.py, not this file. -->'
           % facts['slug'], '']
    for c in film.chapters:
        out.append(f"## {c.id}: {c.title}")
        out.append('')
        out += [ln.md() for ln in c.lines]
        for it in c.items:
            out.append(f"- *item* {it.name} ({', '.join(it.ids)}) @ {story._ts(it.at)}")
            out += [ln.md() for ln in it.lines]
        for ex in c.excerpts:
            out.append(f"- *excerpt* {story._ts(ex.start)}-{story._ts(ex.end)} {ex.label}")
            out += [ln.md() for ln in ex.lines]
        for ep in c.episodes:
            out.append(f"- *episode* {ep.n}: before")
            out += [ln.md() for ln in ep.before_lines]
            out.append(f"- *episode* {ep.n}: after")
            out += [ln.md() for ln in ep.after_lines]
        out.append('')
    return '\n'.join(out).rstrip() + '\n'


def film_lines(film) -> list:
    out = []
    for c in film.chapters:
        out += c.lines
        for e in c.excerpts:
            out += e.lines
        for i in c.items:
            out += i.lines
        for ep in c.episodes:
            out += ep.before_lines + ep.after_lines
    return out


# ------------------------------------------------------------------------------------------------ the command

def run(args) -> int:
    from ..cli import CliError, resolve_song
    from . import draft, history
    song_py = resolve_song(args.song)
    song_dir = song_py.parent
    out_dir = song_dir / 'out'
    if not (out_dir / 'mix.wav').is_file() or not (out_dir / 'report.json').is_file():
        raise CliError(f"{song_dir}: build the song first: python -m agentsound build {song_dir.as_posix()}")
    work = out_dir / 'makingof'
    work.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    facts = gather(song_dir, work, refresh=args.refresh)
    facts['mixWav'] = str(out_dir / 'mix.wav')
    ar_md = (song_dir / 'AR.md').read_text(encoding='utf-8') if (song_dir / 'AR.md').is_file() else ''
    report = history.load_report(out_dir)
    eps_plain = history.episodes(facts, ar_md, report, None) if ar_md else []

    if args.draft:
        p = film_path(song_dir)
        if p.is_file() and not args.force:
            raise CliError(f"{p} exists (a film is kept; --force overwrites it with a new draft)")
        p.write_text(draft.draft_source(facts, n_excerpts=args.excerpts, episodes=eps_plain), encoding='utf-8')
        log(f"making-of: draft written: {p} - now make it this song's film (roles/film-director.md)")
        return 0
    try:
        film, from_file = load_film(song_dir, facts, work, eps_plain, args.excerpts)
    except Exception as e:      # noqa: BLE001 - a film.py error is the author's to fix
        raise CliError(f"film error: {e}") from None
    if args.script:
        p = song_dir / 'making-of.md'
        p.write_text(export_script(film, facts), encoding='utf-8')
        log(f"making-of: narration written: {p} (a review copy; the film is {'film.py' if from_file else 'the draft'})")
        return 0
    log(f"making-of: {'film.py' if from_file else 'the generated draft (no film.py; --draft writes it)'}: "
        f"{len(film.chapters)} chapters, {len(film_lines(film))} lines")

    ffmpeg = find_tool('ffmpeg', args.ffmpeg)
    node = find_tool('node', args.node)
    chrome = find_chrome(args.chrome)
    miss = check_tools(ffmpeg, node, chrome)
    if miss:
        raise CliError("making-of needs: " + '; '.join(miss), 3)
    only = args.chapters.split(',') if args.chapters else None
    chapters = [c for c in film.chapters if not only or c.id in only or c.kind in only]

    # before / after: the judged version, rendered once
    episodes = {}
    if any(c.kind == 'tried' for c in chapters) and ar_md:
        sha = history.judged_commit(ar_md)
        old_out = None
        if sha:
            old_out = history.old_render(REPO, song_dir, sha, REPO / 'build' / 'makingof' / 'history', log)
        old_rep = history.load_report(old_out) if old_out else None
        for e in history.episodes(facts, ar_md, report, old_rep, max_n=12):
            _, e['afterGain'] = history.clip_gain(out_dir / 'mix.wav', e['after'], e['clip'], ffmpeg)
            if old_out:
                e['beforeWav'] = str(old_out / 'mix.wav')
                _, e['beforeGain'] = history.clip_gain(old_out / 'mix.wav', e['before'], e['clip'], ffmpeg)
            e['commit'] = sha or ''
            episodes[e['n']] = e

    # stems for 'meet the tracks'
    need = {i for c in chapters for it in c.items for i in it.ids}
    if need:
        have = {p.stem for p in (out_dir / 'stems').glob('*.wav')}
        if not need <= have:
            if args.no_stems:
                log("making-of: no stems (--no-stems): 'meet the tracks' plays the full mix")
            else:
                log("making-of: rendering the stems once (python -m agentsound build --stems) ...")
                r = subprocess.run([sys.executable, '-m', 'agentsound', 'build', str(song_dir), '--stems', '--no-mp3'],
                                   cwd=str(REPO))
                if r.returncode != 0:
                    raise CliError("the stems render failed", 4)

    # narration
    lines = [ln for c in chapters for ln in film_lines(type('F', (), {'chapters': [c]})())]
    voice_files, credit = {}, 'Captions from the song’s files (no narration)'
    if args.tts != 'none':
        cache = Path(os.environ.get('AGENTSOUND_MAKINGOF_CACHE', REPO / 'build' / 'makingof' / 'tts'))
        try:
            tts = narration.backend(args.tts, cache, log)
            if tts is not None:
                voice_files = narration.synthesize(lines, tts, ffmpeg, work / 'voice', log)
                credit = tts.credit
        except narration.NarrationError as e:
            if args.tts == 'breeze':
                raise CliError(f"narration: {e}")
            log(f"narration: {e}; falling back to the Windows voices")
            tts = narration.Sapi(cache, log)
            voice_files = narration.synthesize(lines, tts, ffmpeg, work / 'voice', log)
            credit = tts.credit
    durations = {k: v['seconds'] for k, v in voice_files.items()}

    # timeline
    song_from = song_to = None
    if args.song_length and args.song_length != 'full':
        song_from, song_to = 0.0, float(args.song_length)
    if args.preview:
        loud = max(facts['sections'], key=lambda s: s['lufs'] if s['lufs'] is not None else -99)
        song_from, song_to = loud['start'], min(facts['duration'], loud['start'] + 20)
    fps = 15 if args.preview else args.fps
    tl = timeline.layout(chapters, durations, facts, fps=fps, song_from=song_from, song_to=song_to,
                         episodes=episodes)
    width, height = (960, 540) if args.preview else (args.width, args.height)
    proj = build_project(song_dir, facts, film, tl, width=width, height=height, narration_credit=credit)
    (work / 'project.json').write_text(json.dumps(proj), encoding='utf-8')
    log(f"making-of: {len(tl['chapters'])} chapters, {tl['duration'] / 60:.1f} min, {tl['frames']} frames at {fps} fps")
    log('  ' + '  '.join(f"{c['id']} {c['t0']:.0f}-{c['t1']:.0f}s" for c in tl['chapters']))

    env = dict(os.environ, AGENTSOUND_MAKINGOF_TMP=str(work / 'tmp'))
    (work / 'tmp').mkdir(exist_ok=True)
    base = [node, str(WEB / 'render.mjs'), '--project', str(work / 'project.json'), '--ffmpeg', ffmpeg,
            '--chrome', chrome, '--gpu', args.gpu]
    if args.stills:
        r = subprocess.run(base + ['--stills', args.stills, '--out', str(work / 'stills')], env=env)
        return r.returncode

    wav = work / 'soundtrack.wav'
    soundtrack(tl, facts, voice_files, ffmpeg, wav, out_dir / 'stems')
    log('making-of: soundtrack mixed')
    video = work / 'video.mp4'
    frames = args.frames or f"0:{tl['frames']}"
    r = subprocess.run(base + ['--out', str(video), '--workers', str(args.workers), '--frames', frames,
                               '--crf', str(args.crf), '--encoder', args.encoder], env=env)
    if r.returncode != 0:
        raise CliError("the frame renderer failed", 4)
    out = Path(args.out) if args.out else out_dir / ('making-of-preview.mp4' if args.preview else 'making-of.mp4')
    fa = int(frames.split(':')[0])
    cmd = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(video), '-ss', f"{fa / fps:.4f}",
           '-i', str(wav), '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-shortest',
           '-movflags', '+faststart', '-metadata', f"title=The making of {facts['title']}",
           '-metadata', f"artist={facts['artist']}", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
    if r.returncode != 0:
        raise CliError(f"mux failed: {r.stderr[-800:]}", 4)
    size = out.stat().st_size / 1e6
    log(f"making-of: {out} ({size:.0f} MB, {tl['duration'] / 60:.1f} min) in {(time.time() - t_start) / 60:.1f} min")
    return 0


def add_parser(sub) -> None:
    p = sub.add_parser('makingof', help='render the making-of film of a built song (out/making-of.mp4) from its '
                                        'film.py (or a generated draft): the story from its files and logs, then the '
                                        'song visualized')
    p.add_argument('song', help='songs/<slug> (built: out/mix.wav, out/report.json)')
    p.add_argument('--draft', action='store_true', help="write a first-draft songs/<slug>/film.py from the song's "
                                                        "facts (edit it into the song's own film) and stop")
    p.add_argument('--script', action='store_true', help="write the film's narration to songs/<slug>/making-of.md "
                                                         "(a review copy) and stop")
    p.add_argument('--force', action='store_true', help='with --draft: overwrite an existing film.py')
    p.add_argument('--tts', default='auto', choices=['auto', 'breeze', 'sapi', 'none'],
                   help='narration voice: Breeze TTS 2 in WSL (auto: when installed), Windows voices, or captions only')
    p.add_argument('--preview', action='store_true', help='a quick look: 960x540 at 15 fps, 20 s of the song')
    p.add_argument('--song-length', default='full', help="how much of the song the song chapter plays: 'full' "
                                                         "(default: film.py's choice) or seconds from the start")
    p.add_argument('--chapters', help='only these chapters (comma list of chapter ids or kinds: '
                                      'cold, team, blueprint, act, tracks, performance, tried, crisis, song, end)')
    p.add_argument('--excerpts', type=int, default=3, help='performance excerpts in a generated draft (default 3)')
    p.add_argument('--stills', help='write PNG stills at these film times (s, comma list) to out/makingof/stills/')
    p.add_argument('--frames', help='render only frames A:B (debugging)')
    p.add_argument('--no-stems', action='store_true', help="don't render stems for 'meet the tracks'")
    p.add_argument('--refresh', action='store_true', help='rebuild the players’ logs (song.py) even if cached')
    p.add_argument('--width', type=int, default=1920)
    p.add_argument('--height', type=int, default=1080)
    p.add_argument('--fps', type=int, default=30)
    p.add_argument('--workers', type=int, default=3, help='browser tabs rendering in parallel (default 3)')
    p.add_argument('--crf', type=int, default=18, help='H.264 quality (lower = better, default 18)')
    p.add_argument('--encoder', default='auto', choices=['auto', 'nvenc', 'x264'],
                   help='H.264 encoder: NVIDIA NVENC when available (auto), else libx264')
    p.add_argument('--gpu', default='high', choices=['high', 'default'], help="'high' asks Chrome for the discrete GPU")
    p.add_argument('--out', help='output mp4 (default songs/<slug>/out/making-of.mp4)')
    p.add_argument('--ffmpeg'), p.add_argument('--node'), p.add_argument('--chrome')
