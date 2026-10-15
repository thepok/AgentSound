"""`python -m agentsound endless GENRE`: compose, render, gate and deliver tunes one after another.

    python -m agentsound endless jazz-piano                      # one tune into songs/_endless_jazz_piano/out/
    python -m agentsound endless jazz-piano --count 5 --mood late-night --seed 100
    python -m agentsound endless jazz-piano --swing              # swing on (default off; --swing 0.58 = that ratio)
    python -m agentsound endless jazz-piano --play               # endless: play back-to-back, render the next ahead
    python -m agentsound endless jazz-piano --hours 1 --join     # an hour of tunes + one long mp3 with gaps

Several tunes (--count N > 1, --hours, --play) follow a SET PLAN (composer.set_plan, the genre's set arc): an
opener at medium tempo, contrast in feel / tempo / key, a ballad after an up-tempo tune, the highlight past the
middle, a quiet closer - printed at the start of every set; --mood pins the mood of the whole set. A set has
--count tunes (else the arc's 'tunes', ~40 minutes), then the next set starts.
Each tune lands in OUT/NNN-<slug>/: mix.mp3 (tagged, cover embedded), cover.png, credits.txt, report.json,
tune.json (title, key, tempo, form, feel, swing, changes, melody, seed, the plan: energy, levels, climax, the
measured shape, timing, gate) and tune.txt (the lead sheet).
The QUALITY GATE: before rendering the tune's shape (composer.shape: the single highest note in the planned climax
phrase, the hook in every A, the register following the arc), then the report: 0 clicks, no flat_dynamics on a lead,
0 silent notes, the loudness inside the genre's window - a failed tune is deleted and the next seed composed with the
same plan (logged in OUT/endless.log).
BEST-OF-N (--candidates N, default the genre's plan['candidates'] = 8): per slot N tunes are composed and performed
without audio, scored (composer.score: one number from the notes) and only the best is rendered (the next best when
the gate fails); --candidates 1 = one seed at a time. `python -m agentsound score TARGET` prints a piece's score.
"""
from __future__ import annotations

import json
import queue
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .composer import breath, compose, describe_set, mix_plan, piano_tells, score, set_plan, shape
from .genres import GENRES, STYLES, get


def add_parser(sub) -> None:
    p = sub.add_parser('endless', help='endless music generator: compose + render + gate tunes of a genre one after '
                                       'another (no LLM; agentsound.endless)')
    p.add_argument('genre', nargs='?', default='jazz-piano',
                   help=f"genre ({', '.join(GENRES)}) or 'piano' (solo piano in a --style)")
    p.add_argument('--style', choices=list(STYLES) + ['mix'],
                   help="with 'piano': jazz, new-age, classical, lofi or mix (default: a set alternating the styles)")
    p.add_argument('--seed', type=int, help='first seed (default: from the clock); tune k uses the next free seeds')
    p.add_argument('--mood', help='mood of the genre (default: rolled per tune)')
    p.add_argument('--swing', nargs='?', const=True, default=None, type=_swing_arg,
                   help="swing the 8ths (default off: straight); a number 0.5..0.75 = that ratio")
    p.add_argument('--count', type=int, help='number of tunes (default 1; endless with --play)')
    p.add_argument('--hours', type=float, help='keep going until this much music is made')
    p.add_argument('--out', help='output directory (default songs/_endless_<genre>/out)')
    p.add_argument('--play', action='store_true', help='play the tunes back-to-back (ffplay) while rendering ahead')
    p.add_argument('--join', action='store_true', help='also write one long mp3 of all tunes with gaps')
    p.add_argument('--gap', type=float, default=4.0, help='seconds of silence between tunes in --join (default 4)')
    p.add_argument('--keep', action='store_true', help='keep mix.wav and the render json')
    p.add_argument('--tries', type=int, default=5, help='seeds to try per tune before giving up (default 5)')
    p.add_argument('--candidates', type=int,
                   help="best-of-N: compose + perform N candidate tunes per slot without audio, score them "
                        "(composer.score) and render only the best (default: the genre's plan['candidates'], 8; "
                        "1 = one seed at a time, as before)")
    p.add_argument('--engine', help='engine executable (default: $AGENTSOUND_ENGINE or build/agentsound.exe)')
    p.add_argument('--list', action='store_true', help='list the genres with their moods, feels and forms')
    p.set_defaults(func=cmd_endless)
    s = sub.add_parser('score', help="the quality score 0-100 of a piano piece from its notes (composer.score: the "
                                     "blind test's tells, breath, body against the composed references) and its worst "
                                     "offenders - a songs/<slug> with a song.py or an endless tune folder (tune.json)")
    s.add_argument('target', help='songs/<slug> (song.py: build(), TUNE optional) or an endless OUT/NNN-<title> folder')
    s.add_argument('--style', choices=list(STYLES) + ['organ'], help="the score table (default: the tune's genre; a song with a "
                                                         "'solo' section: jazz, else new-age)")
    s.add_argument('--all', action='store_true', help='print every metric, not only the worst five')
    s.add_argument('--json', action='store_true', help='print the result as JSON')
    s.set_defaults(func=cmd_score)


def _swing_arg(x):
    v = float(x)
    if not 0.5 <= v <= 0.75:
        raise ValueError('swing ratio must be 0.5..0.75')
    return v


def slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:48] or 'tune'


# ------------------------------------------------------------------------------------------------ the gate

RENDER_BLOCKING = {'clicks', 'flat_dynamics', 'silent_notes', 'silent_node', 'silent_section',
                   'spiky_track', 'loudness_low', 'loudness_high', 'loudness_missing'}


def breath_gate(genre, song) -> list[str]:
    """The genre's band['breath'] minimums on composer.breath(song) (checked before rendering: cheap)."""
    out = []
    if genre.band.get('breath'):
        b = breath(song)
        for k, lo in genre.band['breath'].items():
            if (b.get(k) or 0.0) < lo:
                out.append(f"breath {k} {b.get(k)} under {lo:g}")
    return out


def gate(report: dict, genre, song=None) -> list[str]:
    """What fails the tune: clicks, a flat lead, silent notes, loudness outside the genre's window; with `song` and
    the genre's band['breath'] minimums: the playing must breathe (composer.breath: quiet1 = the share of time
    without a new right-hand onset for a beat+, att_cv4 = how much the density varies per 4 bars)."""
    out = breath_gate(genre, song) if song is not None else []
    from ..verdicts import DELIVERY, evaluate
    policy = dict(DELIVERY['endless'], loudness=list(genre.band.get('loudness', (-20.0, -10.0))))
    for f in evaluate(report, policy=policy):
        if f['code'] in RENDER_BLOCKING and (f['code'] != 'flat_dynamics' or f['severity'] in ('warn', 'error')):
            out.append(f"{f['code']}: {f['message']}"[:160])
    return sorted(set(out))


# ------------------------------------------------------------------------------------------------ one tune

def prepare(genre, seed: int, args, log, plan: dict | None = None, prev=None):
    """Compose (plan: a set_plan entry), check the shape (the arc check), build and check the breath of one tune -
    no audio: (tune, song), or None when a check rejected it (logged)."""
    from .perform import build
    tune = compose(genre, seed, mood=args.mood, swing=args.swing, plan=plan)
    form_shape = shape(tune)
    if form_shape['issues']:
        log(f"seed {seed}: '{tune.title}' REJECTED by the arc check ({'; '.join(form_shape['issues'])}) - rerolling")
        return None
    song = build(tune, genre, prev=prev)
    early = breath_gate(genre, song)
    if early:
        log(f"seed {seed}: '{tune.title}' REJECTED by the breath check ({'; '.join(early)}) - rerolling")
        return None
    return tune, song


def seeds_for(genre, n: int) -> int:
    """The seeds a best-of-n slot may use: n x the genre's plan['candidate_tries'] (default 1: n seeds, the arc /
    breath rejects lost; new-age 2: ~40 % of its seeds failed the arc check, best-of-8 saw 3-5 candidates)."""
    return max(n, int(round(n * genre.plan.get('candidate_tries', 1))))


def candidates(genre, seed: int, n: int, args, log, plan: dict | None = None, prev=None) -> list[dict]:
    """BEST-OF-N: compose + perform n candidate tunes for one slot (seeds seed .. seed+n-1; the slot's plan, or - a
    single tune without one - the first candidate's mood / feel / key / tempo pinned for the others), WITHOUT
    rendering, each scored by composer.score: [{'seed', 'tune', 'song', 'score', 'plan'}] best first (the arc /
    breath rejects dropped). Logs every candidate's score and the best one's worst offenders."""
    from ..theory import ComposeError, PackMissingError
    out, slot = [], plan
    for sd in range(seed, seed + seeds_for(genre, n)):
        if len(out) >= n:                         # (a genre's candidate_tries: rejected seeds are replaced)
            break
        try:
            made = prepare(genre, sd, args, log, plan=slot, prev=prev)
        except PackMissingError:                  # an install problem: every candidate would hit it
            raise
        except ComposeError as e:
            log(f"seed {sd}: compose error ({e}) - next candidate")
            continue
        if made is None:
            continue
        tune, song = made
        used = slot
        if slot is None:                          # (the others play the first one's slot)
            slot = {'mood': tune.mood, 'feel': tune.feel, 'key': tune.key, 'tempo': tune.tempo,
                    **(getattr(tune, 'arrange', None) or {})}       # (the set-level draws: one per slot)
        sc = score(song, tune, genre)
        out.append({'seed': sd, 'tune': tune, 'song': song, 'score': sc, 'plan': used})
        log(f"  candidate seed {sd}: '{tune.title}' ({tune.form}, {tune.feel}) score {sc['score']:.1f}"
            + (f" (capped: {', '.join(sc['hard'])})" if sc['hard'] else ''))
    out.sort(key=lambda c: (-c['score']['score'], c['seed']))
    if out:
        mean = sum(c['score']['score'] for c in out) / len(out)
        best = out[0]
        log(f"best of {len(out)}: seed {best['seed']} '{best['tune'].title}' {best['score']['score']:.1f} (the "
            f"candidates' mean {mean:.1f}); its worst: " + '; '.join(_worst_line(w) for w in best['score']['worst']))
    return out


def _worst_line(w: dict) -> str:
    return f"{w['metric']} {w['value']:g} (want {w['lo']:g}..{w['hi']:g}, -{w['lost']:.1f})"


def render_tune(genre, seed: int, out_root: Path, index: int, args, log, plan: dict | None = None,
                prev=None, made: dict | None = None) -> dict | None:
    """Compose (plan: a set_plan entry), check the shape, build, render, deliver and gate one tune; None when the gate
    failed (the files are removed). prev: the Song of the tune before it in the set (its licks are drawn less often:
    perform.build); made: a candidates() entry (composed, built and scored already: only rendered here);
    info['_song'] is this one's; tune.json carries its score (composer.score) and the exact compose arguments."""
    from .. import cli
    from .perform import cover, metadata
    t0 = time.perf_counter()
    if made is None:
        got = prepare(genre, seed, args, log, plan=plan, prev=prev)
        if got is None:
            return None
        tune, song = got
        sc = score(song, tune, genre)
    else:
        tune, song, sc, plan, seed = made['tune'], made['song'], made['score'], made['plan'], made['seed']
    t1 = time.perf_counter()
    render = song.compile()
    cli.apply_analysis(render, {'profile': genre.band.get('profile', 'jazz')})
    t2 = time.perf_counter()
    d = (out_root / genre.style if getattr(args, 'by_style', False) else out_root) / f"{index:03d}-{slug(tune.title)}"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    rj = cli.write_render(render, d / 'song.render.json')
    engine = cli.find_engine(args.engine)
    proc = subprocess.run([str(engine), 'render', str(rj), '--out', str(d), '--no-png', '--quiet'],
                          capture_output=True, text=True, encoding='utf-8', errors='replace')
    t3 = time.perf_counter()
    if proc.returncode != 0:
        log(f"seed {seed}: the engine failed: {(proc.stderr or proc.stdout).strip()[:300]}")
        shutil.rmtree(d, ignore_errors=True)
        return None
    report = json.loads((d / 'report.json').read_text(encoding='utf-8'))
    fails = gate(report, genre, song)
    audio_s = (report.get('global') or {}).get('durationSec') or song.seconds(song.length)
    if fails:
        log(f"seed {seed}: '{tune.title}' REJECTED by the gate ({'; '.join(fails)}) - rerolling")
        shutil.rmtree(d, ignore_errors=True)
        return None
    song.delivery_settings = {'METADATA': metadata(tune, genre), 'COVER': cover(tune, genre), 'dir': d}
    lines = cli.deliver_render(song, render, engine, d, d, mp3=True)
    t4 = time.perf_counter()
    if not args.keep:
        for f in ('mix.wav', 'song.render.json'):
            (d / f).unlink(missing_ok=True)
    g = report.get('global') or {}
    timing = {'compose_s': round(t1 - t0, 2), 'build_s': round(t2 - t1, 2), 'render_s': round(t3 - t2, 2),
              'deliver_s': round(t4 - t3, 2), 'total_s': round(t4 - t0, 2), 'audio_s': round(audio_s, 1),
              'realtime_x': round(audio_s / max(1e-6, t4 - t0), 2)}
    piano = genre.plan.get('perform', 'jazz') in ('piano', 'organ', 'orchestra')
    own = genre.style in ('organ', 'orchestra')       # (their own tells: the score's parts)
    info = dict(tune.to_dict(), shape=shape(tune) if piano else shape(tune, song), style=genre.style,
                tells=piano_tells(song, tune) if not own else {k: v[0] for k, v in sc['parts'].items()},
                score={'score': sc['score'], 'style': sc['style'], 'hard': sc['hard'], 'worst': sc['worst'],
                       'parts': sc['parts'], 'candidates': (made or {}).get('candidates')},
                compose={'seed': seed, 'mood': args.mood, 'swing': args.swing, 'plan': plan},
                sections=getattr(song, 'endless_sections', None), plan=plan, timing=timing,
                lufs=g.get('lufsIntegrated'),
                lra=g.get('loudnessRange'),
                gate='pass', files={'mp3': str(d / 'mix.mp3'), 'cover': str(d / 'cover.png')},
                orchestration=(dict(getattr(song, 'orch_score').to_dict(), size=getattr(song, 'orch_size', None),
                                    roles=song.orchestration.roles())
                               if getattr(song, 'orch_score', None) is not None else None),
                piano_dynamics_db=next((n['dynamics'].get('dynamicsDb') for n in report.get('nodes') or []
                                        if n.get('id') == 'piano' and isinstance(n.get('dynamics'), dict)), None))
    (d / 'tune.json').write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding='utf-8')
    info['_song'] = song
    (d / 'tune.txt').write_text(tune.describe() + f"\n\n{audio_s:.0f} s of music, rendered in {t4 - t0:.0f} s "
                                f"({timing['realtime_x']}x real time), {g.get('lufsIntegrated')} LUFS\n",
                                encoding='utf-8')
    for ln in lines:
        if 'warning' in ln:
            log('  ' + ln.strip())
    cl = info['shape']['climax']
    log(f"seed {seed}: '{tune.title}' - {tune.key}, {tune.tempo} BPM, {tune.meter}/4 {tune.feel}"
        f"{f' swing {tune.swing:.2f}' if tune.swing else ''}, {tune.form}; {audio_s:.0f} s in {t4 - t0:.0f} s "
        f"(compose {timing['compose_s']} s, render {timing['render_s']} s); {g.get('lufsIntegrated')} LUFS; climax "
        f"{cl['pitch']} in {cl['part']} at {cl['x']:.0%} of the head; LRA {g.get('loudnessRange')} LU, breath "
        f"{info['tells'].get('quiet1')}, phrase rests {info['tells'].get('phrase_rests')}, score {sc['score']:.1f} -> {d}")
    return info


# ------------------------------------------------------------------------------------------------ playback, join

def _ffplay() -> str | None:
    from ..cli import find_ffmpeg
    ff = find_ffmpeg()
    if ff:
        cand = Path(ff).with_name('ffplay' + Path(ff).suffix)
        if cand.is_file():
            return str(cand)
    return shutil.which('ffplay')


class Player(threading.Thread):
    """Plays queued mp3s back-to-back (ffplay -nodisp -autoexit) while the next tune renders."""

    def __init__(self, exe: str, log):
        super().__init__(daemon=True)
        self.exe, self.log, self.q = exe, log, queue.Queue(maxsize=1)

    def run(self):
        while True:
            item = self.q.get()
            if item is None:
                return
            self.log(f"playing   {item}")
            subprocess.run([self.exe, '-nodisp', '-autoexit', '-loglevel', 'quiet', str(item)])


def join(mp3s: list, out: Path, gap: float) -> str:
    from ..cli import find_ffmpeg
    ff = find_ffmpeg()
    if ff is None or not mp3s:
        return 'join skipped: ffmpeg not found' if ff is None else 'join skipped: no tunes'
    args = [ff, '-y', '-hide_banner', '-loglevel', 'error']
    for m in mp3s:
        args += ['-i', str(m)]
    pads = ''.join(f"[{i}:a]apad=pad_dur={gap:g}[a{i}];" for i in range(len(mp3s)))
    flt = pads + ''.join(f"[a{i}]" for i in range(len(mp3s))) + f"concat=n={len(mp3s)}:v=0:a=1[out]"
    proc = subprocess.run(args + ['-filter_complex', flt, '-map', '[out]', '-codec:a', 'libmp3lame', '-b:a', '256k',
                                  str(out)], capture_output=True, text=True, encoding='utf-8', errors='replace')
    return f"joined    {out}" if proc.returncode == 0 else f"join failed: {proc.stderr.strip()[:300]}"


# ------------------------------------------------------------------------------------------------ the command

def describe_genres() -> str:
    lines = []
    for g in GENRES.values():
        lines.append(f"{g.name:<16} {g.description}")
        lines.append(f"{'':<16} style {g.style} | moods: {', '.join(g.moods)} | feels: {', '.join(g.feels)} | "
                     f"forms: {', '.join(g.forms)} | swing: off (--swing = {g.swing})")
    lines.append(f"{'piano':<16} solo piano: --style {' | '.join(STYLES)} (= {', '.join(STYLES.values())}) or mix "
                 f"(a set alternating them) -> songs/_endless_piano/out/<style>/")
    return '\n'.join(lines)


def cmd_endless(args) -> int:
    from ..cli import REPO, CliError
    from ..theory import ComposeError, PackMissingError
    if args.list:
        print(describe_genres())
        return 0
    style = getattr(args, 'style', None)
    try:
        if args.genre == 'piano':
            style = style or 'mix'
            pool = [get(STYLES[s]).validate() for s in STYLES] if style == 'mix' else [get(STYLES[style]).validate()]
            if style == 'mix' and args.mood:
                raise ComposeError("--mood pins one genre's mood; with --style mix the set plan draws them")
        else:
            if style:
                raise ComposeError(f"--style goes with 'endless piano' (genre {args.genre!r} is one style already)")
            pool = [get(args.genre).validate()]
        genre = pool[0]
        if args.mood and args.mood not in genre.moods:
            raise ComposeError(f"genre {genre.name!r} has no mood {args.mood!r}; moods: {', '.join(genre.moods)}")
    except ComposeError as e:
        raise CliError(str(e)) from None
    mix = len(pool) > 1
    args.by_style = args.genre == 'piano'
    name = 'piano' if args.by_style else genre.name.replace('-', '_')
    out_root = Path(args.out) if args.out else REPO / 'songs' / f"_endless_{name}" / 'out'
    out_root.mkdir(parents=True, exist_ok=True)
    logf = (out_root / 'endless.log').open('a', encoding='utf-8')

    def log(msg):
        line = time.strftime('%H:%M:%S ') + msg
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    seed = args.seed if args.seed is not None else int(time.time()) % 1_000_000
    count = args.count if args.count is not None else (None if (args.play or args.hours) else 1)
    # a stream of several tunes plays sets: the set arc picks each tune's mood / feel / tempo / key
    set_n = (1 if mix else None) if count == 1 else (count or genre.arc['set']['tunes'])
    plan, set_k = [], 0
    player = None
    if args.play:
        exe = _ffplay()
        if exe is None:
            log('--play: ffplay not found next to ffmpeg or on PATH - rendering only')
        else:
            player = Player(exe, log)
            player.start()
    dirs = [out_root] + ([p for p in out_root.iterdir() if p.is_dir()] if args.by_style else [])
    index = 1 + max([int(m.group(1)) for d_ in dirs for p in d_.iterdir() if (m := re.match(r'(\d{3})-', p.name))]
                    or [0])
    log(f"endless {'piano --style ' + style if args.by_style else genre.name}: seed {seed}, mood {args.mood or 'rolled'}, swing {args.swing or 'off'}, "
        f"{count if count is not None else 'endless'} tune(s){f', {args.hours:g} h' if args.hours else ''} -> {out_root}")
    made, total_s, prev = [], 0.0, None
    try:
        while (count is None or len(made) < count) and (not args.hours or total_s < args.hours * 3600):
            info = None
            if set_n and set_k >= len(plan):          # a new set: its plan, from the key the last one ended in
                prev = None                            # a new set: no memory of the last one's licks
                prev_key = made[-1]['key'] if made else None
                plan, set_k = (mix_plan(pool, set_n, seed, prev_key=prev_key) if mix else
                               set_plan(genre, set_n, seed, mood=args.mood, prev_key=prev_key)), 0
                log(f"set plan ({set_n} tunes, seed {seed}):\n{describe_set(plan)}")
            slot = plan[set_k] if set_n else None
            g_ = get(slot['genre']) if slot and slot.get('genre') else genre
            if prev is not None and getattr(prev, 'endless_tune', None) is not None and \
                    prev.endless_tune.genre != g_.name:
                prev = None                            # (the licks' memory is one genre's)
            n_cand = args.candidates if args.candidates is not None else g_.plan.get('candidates', 8)
            if n_cand > 1:                             # best-of-N: score without audio, render the best (the next
                ranked = candidates(g_, seed, n_cand, args, log, plan=slot, prev=prev)   # on a failed gate)
                seed += seeds_for(g_, n_cand)
                summary = {'n': len(ranked), 'mean': round(sum(c['score']['score'] for c in ranked) /
                                                           max(1, len(ranked)), 1),
                           'scores': {c['seed']: c['score']['score'] for c in ranked}}
                for rank, c in enumerate(ranked[:max(1, args.tries)]):
                    info = render_tune(g_, c['seed'], out_root, index, args, log, prev=prev,
                                       made=dict(c, candidates=dict(summary, rank=rank + 1)))
                    if info:
                        break
            else:
                for _ in range(max(1, args.tries)):
                    try:
                        info = render_tune(g_, seed, out_root, index, args, log, plan=slot, prev=prev)
                    except PackMissingError:
                        raise
                    except ComposeError as e:
                        log(f"seed {seed}: compose error ({e}) - rerolling")
                    seed += 1
                    if info:
                        break
            if not info:
                log(f"no tune passed the gate in {args.tries} {'candidates' if n_cand > 1 else 'seeds'} - stopping")
                break
            song_ = info.pop('_song', None)
            prev = song_ if set_n else None             # the set's memory: the next tune avoids its licks
            made.append(info)
            set_k += 1
            total_s += info['timing']['audio_s']
            index += 1
            if player is not None:
                player.q.put(Path(info['files']['mp3']))
    except KeyboardInterrupt:
        log('stopped')
    if args.join and made:
        log(join([Path(i['files']['mp3']) for i in made],
                 out_root / f"endless-{name.replace('_', '-')}-{made[0]['seed']}-{len(made)}.mp3", args.gap))
    if made:
        r = sum(i['timing']['audio_s'] for i in made) / max(1e-6, sum(i['timing']['total_s'] for i in made))
        log(f"done: {len(made)} tune(s), {total_s / 60:.1f} min of music, {r:.1f}x real time")
    if player is not None:
        player.q.put(None)
        player.join()
    logf.close()
    return 0 if made else 1


# ------------------------------------------------------------------------------------------------ score

def load_scored(target: Path):
    """(song, tune or None, genre or None) of a score target: an endless tune folder (tune.json: the tune composed
    again from its 'compose' arguments - or seed / plan / swing / mood for older folders - and built WITHOUT the set's
    memory of the tune before it) or a song folder / song.py (build(), its module-level TUNE when it has one)."""
    import importlib.util
    import sys
    from ..cli import CliError
    from .perform import build
    target = Path(target)
    tj = target / 'tune.json'
    if tj.is_file():
        d = json.loads(tj.read_text(encoding='utf-8'))
        g = get(d['genre'])
        c = d.get('compose') or {'seed': d['seed'], 'swing': d.get('swing'), 'plan': d.get('plan'), 'mood': None}
        tries = [c['mood']] if 'compose' in d else [None, d.get('mood')]
        for mood in tries:
            tune = compose(g, c['seed'], mood=mood, swing=c.get('swing'), plan=c.get('plan'))
            if tune.title == d['title']:
                return build(tune, g), tune, g
        raise CliError(f"{tj}: seed {c['seed']} composes '{tune.title}', not '{d['title']}' (made by other code?)")
    py = target if target.suffix == '.py' else target / 'song.py'
    if not py.is_file():
        raise CliError(f"score: {target} has neither a tune.json nor a song.py")
    spec = importlib.util.spec_from_file_location('agentsound_score_' + re.sub(r'\W', '_', py.parent.name), py)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(py.parent))
    try:
        spec.loader.exec_module(mod)
        song = mod.build() if hasattr(mod, 'build') else getattr(mod, 'song', None)
    finally:
        sys.path.remove(str(py.parent))
    if song is None:
        raise CliError(f"{py} must define build() -> Song or a module-level `song`")
    tune = getattr(mod, 'TUNE', None)
    return song, tune, (get(tune.genre) if tune is not None and getattr(tune, 'genre', None) in GENRES else None)


def format_score(sc: dict, every: bool = False) -> str:
    """The score, why it is capped, and its worst offenders (every metric with every=True)."""
    from .genres import SCORES
    t = SCORES[sc['style']]
    head = f"score {sc['score']:.1f} / 100 ({sc['style']} table, {len(sc['parts'])} metrics"
    head += f"; capped from {sc['mean']:.1f} by the hard rule(s) {', '.join(sc['hard'])})" if sc['hard'] else ')'
    lines = [head]
    rows = sorted(sc['parts'], key=lambda k: sc['parts'][k][1]) if every else [w['metric'] for w in sc['worst']]
    lines.append('every metric (worst first):' if every else 'worst offenders:')
    for k in rows:
        v, sub, w = sc['parts'][k]
        lo, hi = t[k][0], t[k][1]
        lines.append(f"  {k:<16} {v:>8.3g}   want {lo:g}..{hi:g}   sub {sub:.2f}  weight {w:g}"
                     + ('  HARD' if t[k][3] else ''))
    if sc['missing']:
        lines.append(f"not measured: {', '.join(sc['missing'])}")
    return '\n'.join(lines)


def cmd_score(args) -> int:
    from ..cli import CliError
    from ..theory import ComposeError
    try:
        song, tune, g = load_scored(Path(args.target))
        if args.style:
            g = get(STYLES.get(args.style, args.style))
        sc = score(song, tune, g)
    except ComposeError as e:
        raise CliError(str(e)) from None
    if args.json:
        print(json.dumps(sc, indent=1))
    else:
        print(f"{Path(args.target)}: {song.title}" + (f" ({tune.genre}, seed {tune.seed})" if tune is not None else ''))
        print(format_score(sc, args.all))
    return 0
