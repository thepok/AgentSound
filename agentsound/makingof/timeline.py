"""Where everything sits in the film: chapter spans, narration lines, the music under them (beds, excerpts, the
song) with their gain envelopes, and the visual scene plan of the song. Pure maths on seconds - no audio, no
rendering - so it is testable and the renderer and the soundtrack read the same numbers.

Sync: video frame f shows video time f / fps; a music segment maps video time v to song time s0 + (v - v0), so a
move at song time m is on frame round((v0 + m - s0) * fps) - frame_of() / song_time()."""

from __future__ import annotations

import math
import re

# minimum chapter lengths (s) - the narration stretches a chapter, never shortens it below these
MIN_LEN = {'cold': 15.0, 'team': 22.0, 'blueprint': 26.0, 'tracks': 16.0, 'performance': 8.0, 'crisis': 16.0,
           'tried': 10.0, 'act': 6.0, 'song': 0.0, 'end': 20.0}
LEAD = {'cold': 1.2, 'team': 1.6, 'blueprint': 1.6, 'tracks': 1.6, 'performance': 1.4, 'crisis': 1.6, 'tried': 1.6,
        'act': 2.4, 'song': 0.6, 'end': 2.0}                  # where the first line starts (after the chapter's title card)
TAIL = 1.4                           # silence after the last line before the chapter ends
BED_DB, DUCK_DB, LEADIN_DB = -11.0, -21.0, -17.0
SOLO, MIXL, XF = 4.2, 2.4, 0.9         # meet the tracks: solo seconds, band-back-in seconds, crossfade
SOLO_LUFS = -17.0                      # a soloed stem is lifted towards this (at most +9 dB)
FADE = 0.6                           # chapter crossfade through black (s)


def frame_of(t: float, fps: float) -> int:
    """The frame that shows video time t (nearest)."""
    return int(round(t * fps))


def song_time(t: float, segments: list[dict]) -> float | None:
    """Song time at video time t (the music segment playing there), None where no song audio plays."""
    for s in segments:
        if s['v0'] <= t < s['v1']:
            return s['s0'] + (t - s['v0'])
    return None


def video_time(song_t: float, seg: dict) -> float:
    return seg['v0'] + (song_t - seg['s0'])


def estimate_seconds(text: str, wpm: float = 150.0) -> float:
    """Speech length of a line without TTS (captions only): words at wpm + a little per sentence."""
    words = len(re.findall(r"[\w'’-]+", text))
    return max(1.2, words * 60.0 / wpm + 0.25 * text.count('.'))


def _env(points: list[tuple[float, float]]) -> list[list[float]]:
    """Sorted (t, dB) points, duplicates collapsed."""
    pts = sorted(points)
    out: list[list[float]] = []
    for t, g in pts:
        if out and abs(out[-1][0] - t) < 1e-6:
            out[-1][1] = g
        else:
            out.append([round(t, 4), round(g, 2)])
    return out


def duck_envelope(dur: float, base: float, duck: float, voice: list[tuple[float, float]], fade_in: float = 1.0,
                  fade_out: float = 1.2, ramp_in: float = 0.25, ramp_out: float = 0.45) -> list[list[float]]:
    """Gain points (segment-local s, dB) of music under narration: a dB-linear fade in from -60, `base`, down to
    `duck` while a voice speaks (ramp_in before it, ramp_out after it), a fade out to -60 at the end."""
    fade_in, fade_out = min(fade_in, dur / 3), min(fade_out, dur / 3)
    corners = {0.0, fade_in, max(0.0, dur - fade_out), dur}
    for a, b in voice:
        corners |= {a - ramp_in, a, b, b + ramp_out}

    def g(t):
        v = base
        for a, b in voice:
            if a - ramp_in <= t <= b + ramp_out:
                w = 1.0 if a <= t <= b else ((t - (a - ramp_in)) / ramp_in if t < a else 1.0 - (t - b) / ramp_out)
                v = min(v, base + (duck - base) * w)
        if t < fade_in:
            v = -60.0 + (v + 60.0) * (t / fade_in)
        if t > dur - fade_out:
            v = -60.0 + (v + 60.0) * ((dur - t) / fade_out)
        return v
    return _env([(t, g(t)) for t in corners if 0.0 <= t <= dur])


def gain_at(env: list[list[float]], t: float) -> float:
    """Linear interpolation of an envelope (dB) at local time t."""
    if not env:
        return 0.0
    if t <= env[0][0]:
        return env[0][1]
    for (t0, g0), (t1, g1) in zip(env, env[1:]):
        if t0 <= t <= t1:
            return g0 + (g1 - g0) * ((t - t0) / (t1 - t0) if t1 > t0 else 1.0)
    return env[-1][1]


# ------------------------------------------------------------------------------------------------ scenes

def genre_family(facts: dict) -> str:
    g = f"{facts.get('genre', '')} {facts.get('genre_text', '')} {facts.get('profile', '')}".lower()
    if re.search(r'synth|retro|outrun|dream|vapor|darksynth|electro|trance|house', g):
        return 'synth'
    if re.search(r'film|orchestr|symphon|classical|piano|opera|cinematic|ballad', g):
        return 'orchestral'
    if re.search(r'jazz|swing|bebop|lounge', g):
        return 'jazz'
    return 'band'


SCENES = ('nebula', 'ink', 'ring', 'grid', 'mandala', 'scope')
PLAN = {  # family -> (calm, mid, high, peak) scene choices; '+hw' = the note highway over it
    'orchestral': (('ink', 'nebula'), ('nebula+hw', 'ink'), ('ring', 'nebula+hw', 'scope'), ('mandala', 'ring')),
    'synth': (('nebula', 'scope'), ('grid', 'nebula+hw'), ('grid+hw', 'ring'), ('mandala', 'grid+hw')),
    'jazz': (('ink', 'nebula'), ('scope', 'nebula+hw'), ('ring', 'nebula+hw'), ('mandala', 'ring')),
    'band': (('nebula', 'ink'), ('ring', 'nebula+hw'), ('scope', 'ring'), ('mandala', 'ring')),
}


def scene_plan(facts: dict, scenes: dict | None = None, highway=()) -> list[dict]:
    """One visual scene per section of the song (song time): calm sections soft and slow, the loudest one or two
    explosive; the hook sections get the note highway; neighbours never repeat. scenes / highway: a film's own
    choices per section (Film.look) win."""
    fam = genre_family(facts)
    choice = PLAN[fam]
    secs = facts['sections']
    levels = sorted((s['level'] for s in secs), reverse=True)
    peak_cut = levels[min(1, len(levels) - 1)] if len(levels) > 3 else 2.0
    hook_secs = {o['section'] for o in facts['hook']['occurrences']}
    out, prev = [], ''
    for i, s in enumerate(secs):
        lv = s['level']
        tier = 3 if lv >= peak_cut and lv > 0.85 else 2 if lv >= 0.7 else 1 if lv >= 0.35 else 0
        opts = list(choice[tier])
        if s['name'] in hook_secs and tier in (1, 2):
            opts.sort(key=lambda o: 0 if '+hw' in o else 1)
        pick = next((o for o in opts if o.split('+')[0] != prev.split('+')[0]), opts[0])
        if scenes and s['name'] in scenes:
            pick = scenes[s['name']] + ('+hw' if s['name'] in highway else '')
        elif s['name'] in highway:
            pick = pick.split('+')[0] + '+hw'
        base = pick.split('+')[0]
        out.append({'s0': s['start'], 's1': s['end'], 'scene': base, 'highway': '+hw' in pick,
                    'intensity': round(lv, 3), 'section': s['name'], 'tier': tier, 'family': fam})
        prev = pick
    if out:
        out[-1]['s1'] = max(out[-1]['s1'], facts['duration'])
    return out


# ------------------------------------------------------------------------------------------------ layout

def _pick_beds(facts: dict) -> dict[str, float]:
    """Song positions of the music under each talking chapter: calm sections in song order (the cold open gets the
    very beginning), the verdict the section its first issue names."""
    secs = facts['sections']
    calm = [s for s in secs if s['level'] < 0.55] or secs
    beds = {'cold': 0.0}
    order = ['team', 'blueprint', 'tracks', 'end']
    for i, cid in enumerate(order):
        s = calm[(i + 1) % len(calm)] if len(calm) > 1 else calm[0]
        beds[cid] = s['start']
    names = {s['name']: s for s in secs}
    beds['crisis'] = beds['tracks']
    if facts.get('issues'):
        text = (facts['issues'][0]['title'] + ' ' + facts['issues'][0]['text']).lower()
        hit = next((s for n, s in names.items() if re.search(rf'\b{re.escape(n.lower())}\b', text)), None)
        if hit:
            beds['crisis'] = hit['start']
    return beds


def layout(chapters, durations: dict, facts: dict, *, fps: int = 30, song_from: float | None = None,
           song_to: float | None = None, only: list | None = None, episodes: dict | None = None) -> dict:
    """The film's timeline.

    chapters: story.Chapter list (a Film's); durations: {id(line): seconds} of each narrated line (TTS or
    estimate); song_from / song_to: override the song chapter's span (previews); only: chapter ids to keep;
    episodes: {revision item n: history episode} for 'tried' chapters (clip positions, files, gains)."""
    total_song = facts['duration']
    beds = _pick_beds(facts)
    t = 0.0
    out_ch, captions, segments, voices = [], [], [], []
    for c in chapters:
        if only and c.id not in only and c.kind not in only:
            continue
        kind = c.kind
        t0 = t
        cur = t0 + LEAD.get(kind, 1.6)
        line_spans = []

        def say(ln, at, _c=c):
            d = durations.get(id(ln), estimate_seconds(ln.text))
            captions.append({'t0': round(at, 3), 't1': round(at + d, 3), 'text': ln.text, 'voice': ln.voice,
                             'chapter': _c.id})
            voices.append({'line': ln, 't': round(at, 3), 'dur': d})
            line_spans.append((at, at + d))
            return at + d + ln.pause_ms / 1000.0

        extra: dict = {'kind': kind, **{k: v for k, v in c.opts.items() if isinstance(v, (int, float, str, list,
                                                                                        bool, type(None)))}}
        if kind == 'performance':
            for ln in c.lines:
                cur = say(ln, cur)
            exs = []
            for ex in c.excerpts:
                lead_start = cur
                for ln in ex.lines:
                    cur = say(ln, cur)
                v_s0 = lead_start + max(2.5, cur - lead_start + 0.3)   # the excerpt proper starts here
                lead = min(v_s0 - lead_start, ex.start)                  # song audio before it (none before 0:00)
                seg = {'kind': 'excerpt', 'v0': round(v_s0 - lead, 4),
                       'v1': round(v_s0 + (ex.end - ex.start) + 0.9, 4), 's0': round(ex.start - lead, 4)}
                dur = seg['v1'] - seg['v0']
                spans = [(a - seg['v0'], b - seg['v0']) for a, b in line_spans if a >= lead_start - 1e-6]
                speech_end = max([b for _, b in spans] + [0.0])
                up = max(lead, speech_end + 0.1)
                quiet = LEADIN_DB if lead > 0.3 else 0.0
                seg['env'] = _env([(0.0, -60.0 if lead > 0.3 else 0.0), (min(0.5, lead), quiet),
                                   (max(min(0.5, lead), up - 0.6), quiet), (up, 0.0), (dur - 0.9, 0.0),
                                   (dur, -60.0)])
                segments.append(seg)
                exs.append({'v0': seg['v0'], 'vs': round(v_s0, 4), 'v1': seg['v1'], 's0': ex.start, 's1': ex.end,
                            'label': ex.label})
                cur = seg['v1'] + 0.2
            extra['excerpts'] = exs
            t1 = max(cur + 0.4, t0 + MIN_LEN.get(kind, 8.0))
        elif kind == 'tracks':
            for ln in c.lines:
                cur = say(ln, cur)
            intro_end = max(cur + 0.4, t0 + 7.0)
            d = intro_end - t0
            spans = [(a - t0, b - t0) for a, b in line_spans]
            s0 = min(beds.get('tracks', 0.0), max(0.0, total_song - d))
            segments.append({'kind': 'bed', 'v0': round(t0, 4), 'v1': round(intro_end, 4), 's0': round(s0, 4),
                             'env': duck_envelope(d, BED_DB, DUCK_DB, spans, 1.0, 1.0)})
            cur = intro_end
            items = []
            known = {tuple(sorted(i['ids'])): i for i in facts.get('items', [])}
            for it in c.items:
                lead_start = cur
                for ln in it.lines:
                    cur = say(ln, cur)
                v0 = cur + (0.3 if it.lines else 0.0)
                info = known.get(tuple(sorted(it.ids)), {})
                solo, mixl = info.get('solo', SOLO), info.get('mix', MIXL)
                lufs = info.get('lufs')
                makeup = 0.0 if lufs is None else max(0.0, min(9.0, SOLO_LUFS - lufs))
                s_at = max(0.0, min(it.at, total_song - solo - mixl - 0.5))
                segments.append({'kind': 'solo', 'stems': list(it.ids), 'v0': round(v0, 4),
                                 'v1': round(v0 + solo + XF, 4), 's0': round(s_at, 4), 'gainDb': round(makeup, 2),
                                 'env': _env([(0.0, -60.0), (0.06, 0.0), (solo, 0.0), (solo + XF, -60.0)])})
                segments.append({'kind': 'excerpt', 'v0': round(v0 + solo, 4), 'v1': round(v0 + solo + mixl, 4),
                                 's0': round(s_at + solo, 4),
                                 'env': _env([(0.0, -60.0), (XF, -2.0), (mixl - 0.7, -2.0), (mixl, -60.0)])})
                items.append({'name': it.name, 'ids': list(it.ids), 'v0': round(v0, 4), 'vs': round(v0 + solo, 4),
                              'v1': round(v0 + solo + mixl, 4), 's0': round(s_at, 4), 'lead0': round(lead_start, 4),
                              'lines': info.get('lines', []), 'color': info.get('color', '#c7cbd6'),
                              'players': info.get('players', []), 'lead': info.get('lead', False)})
                cur = v0 + solo + mixl + 0.1
            extra['items'] = items
            t1 = max(cur + 0.3, t0 + MIN_LEN.get(kind, 8.0))
        elif kind == 'tried':
            for ln in c.lines:
                cur = say(ln, cur)
            eps = []
            for ep in c.episodes:
                info = (episodes or {}).get(ep.n)
                if not info:
                    continue
                e0 = cur
                for ln in ep.before_lines:
                    cur = say(ln, cur)
                vb = cur + 0.25
                dur = info['clip']
                if info.get('beforeWav'):
                    segments.append({'kind': 'clip', 'file': info['beforeWav'], 'features': False,
                                     'v0': round(vb, 4), 'v1': round(vb + dur, 4), 's0': info['before'],
                                     'gainDb': info.get('beforeGain', 0.0),
                                     'env': _env([(0.0, -60.0), (0.2, 0.0), (dur - 0.5, 0.0), (dur, -60.0)])})
                cur = vb + dur + 0.35
                for ln in ep.after_lines:
                    cur = say(ln, cur)
                va = cur + 0.25
                segments.append({'kind': 'clip', 'v0': round(va, 4), 'v1': round(va + dur, 4), 's0': info['after'],
                                 'gainDb': info.get('afterGain', 0.0),
                                 'env': _env([(0.0, -60.0), (0.2, 0.0), (dur - 0.5, 0.0), (dur, -60.0)])})
                cur = va + dur + 0.5
                eps.append({**{k: v for k, v in info.items() if k not in ('beforeWav',)}, 'v0': round(e0, 4),
                            'vb': round(vb, 4), 'va': round(va, 4), 'v1': round(cur, 4),
                            'hasBefore': bool(info.get('beforeWav'))})
            extra['episodes'] = eps
            t1 = max(cur + 0.4, t0 + MIN_LEN.get(kind, 8.0))
        elif kind == 'act':
            for ln in c.lines:
                cur = say(ln, cur)
            start = c.opts['start']
            play = c.opts.get('play', 10.0)
            v0 = t0 + 0.4
            t1 = max(cur, t0 + 3.0) + play
            if start + (t1 - v0) > total_song:
                t1 = v0 + (total_song - start)
            d = t1 - v0
            spans = [(a - v0, b - v0) for a, b in line_spans]
            segments.append({'kind': 'act', 'v0': round(v0, 4), 'v1': round(t1, 4), 's0': round(start, 4),
                             'env': duck_envelope(d, 0.0, -13.0, spans, 1.0, 1.4, 0.3, 0.8)})
            extra['act'] = {'v0': round(v0, 4), 'v1': round(t1, 4), 's0': start}
        elif kind == 'song':
            for ln in c.lines:
                cur = say(ln, cur)
            a = c.opts.get('start', 0.0) if song_from is None else song_from
            ln_ = c.opts.get('length')
            b = song_to if song_to is not None else (total_song if ln_ is None else min(total_song, a + float(ln_)))
            start = max(t0 + 3.0, cur + 0.2)
            seg = {'kind': 'song', 'v0': round(start, 4), 'v1': round(start + (b - a), 4), 's0': round(a, 4)}
            d = seg['v1'] - seg['v0']
            fin = 0.02 if a <= 0.01 else 1.5
            fout = 0.05 if b >= total_song - 0.01 else 3.0
            seg['env'] = _env([(0.0, -60.0 if fin > 0.05 else 0.0), (fin, 0.0), (d - fout, 0.0),
                               (d, -60.0 if fout > 0.1 else 0.0)])
            segments.append(seg)
            extra['song'] = {'v0': seg['v0'], 'v1': seg['v1'], 's0': a, 's1': b}
            t1 = seg['v1'] + 1.0
        else:
            for ln in c.lines:
                cur = say(ln, cur)
            t1 = max(cur + TAIL, t0 + MIN_LEN.get(kind, 12.0))
            bed_key = {'cold': 'cold', 'team': 'team', 'blueprint': 'blueprint', 'crisis': 'crisis',
                       'end': 'end'}.get(kind)
            if bed_key in beds:
                s0 = beds[bed_key]
                d = t1 - t0
                if total_song - s0 < d:
                    s0 = max(0.0, total_song - d)
                spans = [(a - t0, b - t0) for a, b in line_spans]
                segments.append({'kind': 'bed', 'v0': round(t0, 4), 'v1': round(t1, 4), 's0': round(s0, 4),
                                 'env': duck_envelope(d, BED_DB, DUCK_DB, spans, 1.6 if kind == 'cold' else 1.0,
                                                      1.2)})
        out_ch.append({'id': c.id, 'title': c.title, 't0': round(t0, 4), 't1': round(t1, 4), **extra})
        t = t1
    duration = t
    return {'fps': fps, 'duration': round(duration, 4), 'frames': int(math.ceil(duration * fps)),
            'chapters': out_ch, 'captions': captions, 'segments': segments, 'voices': voices}


def check_sync(tl: dict, moves: list[dict]) -> list[dict]:
    """Every move inside a music segment -> {'t' (song), 'video', 'frame'}: where the renderer pops its label."""
    out = []
    for seg in tl['segments']:
        if seg['kind'] not in ('excerpt', 'song', 'act', 'clip', 'solo') or seg.get('features') is False:
            continue
        for m in moves:
            v = video_time(m['t'], seg)
            if seg['v0'] <= v < seg['v1']:
                out.append({'t': m['t'], 'video': v, 'frame': frame_of(v, tl['fps'])})
    return out
