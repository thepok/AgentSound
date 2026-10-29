"""Endless orchestra-symphonic CHOIR (round oc1; HUMAN_FEEDBACK 2026-10-24: "I think the choir will help the
orchestra to greatness - it gives goosebumps much more surely", 2026-10-19: a choir must sound like MANY people): a
real SATB choir - the vocalset-choir pack, wordless vowels summed from the 20 real VocalSet singers (CC BY 4.0) - as
a musical EVENT of the form, never a pad.

Per piece one choir PLAN (PLANS; the set plan draws it with memory - plan['set_choir'], composer.set_plan: never the
slot before's plan, rarely the one before that's, no two pieces without a choir in a row - else the piece's own draw;
'none' in about a quarter of the pieces). A plan is a sequence of EVENTS (EVENTS), each placed in the piece's blocks:

  summit     the climax arrival in the choir - the peak block's most singable line (the theme, or its augmented
             motto / counter-line when the theme runs) in the sopranos on "ah" (a quiet climax: "oh"), the harmony
             voice-led under it in alto / tenor / bass, the orchestra under it (it doubles what plays: no masking)
  lead_in    the build's last two bars: the choir enters on "oo" with the crescendo, breathes, and arrives
  acappella  the choir nearly alone for 4-8 bars before the final build: the block's own line in the sopranos,
             oo -> oh -> ah phrase by phrase, p -> mf; the orchestra drops out but for the bass line, soft
  halo       a soft "oo" halo over a quiet block (the second theme, the trio, the river, its return): held chords
             under / around the line (no voice a semitone from it), entering for the second half of a long block
  coda       the coda sung: the triumph coda's line on "ah" over the chorale (f), or the dissolving coda "oh" ->
             "oo" with the last chord held

Every event is written with the shared choir primitives: voicing.voice (SATB voice leading within the pack's ranges,
the soprano fixed to the line it sings), orch.Score.sing (the velocities from the piece's dynamics map + a phrase
arc) and orch.Choir (lane 'dynamics': the p / mf / f layers crossfaded on CC1, early speaking starts, a messa di voce
on long notes), on bandlib.orchestra.vocalset_choir's tracks (one per part and vowel, in the band's hall, its own
send). Breath gaps at the phrase ends; notes longer than the samples' sustain re-attacked, staggered per part.
CHOIR None = off (bit-identical); genres.symphony_choir switches it with the set draw. Stats: choir_stats(song).
"""
from __future__ import annotations

import dataclasses
import random

from ..theory import ComposeError

CHOIR = None
CHOIR_ON = {'gain': -7.5, 'send': -6.0, 'memory': (0.08, 0.45), 'share': 0.5, 'max_s': 5.0, 'breath_s': 0.32, 'min_s': 0.42,
            'phrase': 4, 'acap_s': (7.0, 4, 8), 'acap_bass': -8.0, 'halo_off': -3.0, 'acap_dyn': (50, 80),
            'lead_bars': 2, 'level': (0.07, 105, -12.0)}
"""CHOIR on: dB on every choir track (over the band's 'gain'), its hall send (dB), the plan draw's weight for the slot
before's / the one before that's plan (and for a plan sharing an event with the slot before's), the longest sung note (s; the samples hold ~6 s), the breath at a phrase end
(s), a sung note's least length (s: shorter line notes join the note before - the choir sings the line's long notes),
the phrase (plan bars) between breaths, the a cappella's length (s, least / most plan bars), the bass's velocity offset
under it, the halo's offset, the a cappella's velocity from / to, the lead-in's bars, the level by velocity (dB per
velocity step under the reference velocity, the least dB): the pack's p / mf / f layers are level-matched - they
change the timbre only -, so the written dynamics also move the gain ('expression', gain = value^2)."""

CHOIR_V2 = {'v2': True, 'caps': {'summit': 3, 'lead_in': 1, 'acappella': 3, 'halo': 2, 'coda': 2}, 'gesture': 0.7,
            'line_min_s': 0.2, 'tex': {'unison': 0.6, 'hymn': 0.4}, 'late': 0.4, 'under': (-12.0, -6.0),
            'halo_line': -14.0, 'halo_bars': 12, 'window': 7, 'acap_db': 3.5}
"""CHOIR v2 (round oc2 - oc1's fixes; CHOIR_ON + these): the set's GESTURE memory (an event at most caps[event] times
per set, its plans' weight x gesture per earlier use - the lead-in -> summit pair no formula), the sung line's least
note (s: the theme in its own rhythm, not its long notes held as chords), the summit's texture draw ('unison': the
theme in sopranos and tenors in octaves over alto / bass harmony by chord, 'hymn': the theme harmonised SATB), the
share of summits that enter at the peak's second half (not always on the arrival), the orchestra under the sung
theme (velocity offsets of the brass / woodwind parts doubling a line), the halo's line (the halo SINGS the quiet
block's line, its own instrument this much softer), the longest halo (plan bars; longer blocks: their second half) and
the gesture memory's window (the slots before: a set of 8), the a cappella's level (dB: alone, it is heard)."""

VOICES = {'S': (60, 79, 70), 'A': (57, 74, 65), 'T': (48, 67, 58), 'B': (45, 62, 51)}
"""The choir's voice set (voicing.voice; inside the pack's ranges - VOCALSET_PARTS: S C4-G#5, A A3-F5, T B2-G#4, B
A2-F4 - a step under their tops)."""

PLANS = {'none': {'w': 1.6, 'events': ()},
         'summit': {'w': 0.8, 'events': ('lead_in', 'summit')},
         'acappella': {'w': 0.6, 'events': ('acappella', 'summit')},
         'halo_summit': {'w': 0.6, 'events': ('halo', 'summit')},
         'halo': {'w': 0.5, 'events': ('halo',)},
         'coda': {'w': 0.6, 'events': ('coda',)},
         'halo_coda': {'w': 0.6, 'events': ('halo', 'coda')}}
"""The choir's role in a piece (its events in order) and the draw's weight."""
FEELS = {'andante': {'halo_summit': 1.4, 'halo_coda': 1.5, 'halo': 1.3, 'acappella': 1.2, 'none': 0.8},
         'river': {'halo_summit': 1.3, 'halo_coda': 1.2},
         'allegro': {'summit': 1.3, 'acappella': 1.2},
         'vivace': {'summit': 1.1},
         'scherzo': {'none': 1.4, 'acappella': 0.6, 'halo_coda': 0.7}}
"""The feels' affinity per plan (x the weight; missing = 1)."""

EVENTS = {'summit': {'vowels': ('ah',), 'quiet': ('oo', 'oh'), 'off': 0.0, 'db': 0.0},
          'lead_in': {'vowels': ('oo',), 'off': -6.0, 'db': -3.0},
          'acappella': {'vowels': ('oo', 'oh', 'ah'), 'phrase': 2, 'db': 1.0},
          'halo': {'vowels': ('oo',), 'off': None, 'db': -1.0},
          'coda': {'vowels': ('ah',), 'soft': ('oh', 'oo'), 'off': 0.0, 'db': 0.0, 'soft_db': -5.0}}
"""Per event: the vowels phrase by phrase (spread over its phrases), a quiet climax's / a soft coda's, the velocity
offset on the dynamics map (None: CHOIR['halo_off']), the phrase length (plan bars) where not CHOIR['phrase'], the
level offset (dB; a soft coda's)."""

PLANS_V2 = {'none': {'w': 1.0, 'events': ()},
            'summit': {'w': 0.55, 'events': ('summit',)},
            'swell': {'w': 0.25, 'events': ('lead_in', 'summit')},
            'acappella': {'w': 1.2, 'events': ('acappella', 'summit')},
            'acappella_coda': {'w': 0.7, 'events': ('acappella', 'coda')},
            'halo_summit': {'w': 0.5, 'events': ('halo', 'summit')},
            'halo_coda': {'w': 0.5, 'events': ('halo', 'coda')},
            'halo': {'w': 0.35, 'events': ('halo',)},
            'coda': {'w': 0.4, 'events': ('coda',)}}
"""CHOIR v2's plans (round oc2: the a cappella - oc1's best event - twice as likely, also before a sung coda; the
lead-in a rare 'swell'; FEELS as v1's, a missing name 1)."""


PLANS_POLISH = {'none': {'w': 0.9, 'events': ()},
                'summit': {'w': 0.4, 'events': ('summit',)},
                'swell': {'w': 0.2, 'events': ('lead_in', 'summit')},
                'acappella': {'w': 0.9, 'events': ('acappella', 'summit')},
                'acappella_coda': {'w': 1.0, 'events': ('acappella', 'coda')},
                'acappella_only': {'w': 0.5, 'events': ('acappella',)},
                'halo_summit': {'w': 0.4, 'events': ('halo', 'summit')},
                'halo_coda': {'w': 0.8, 'events': ('halo', 'coda')},
                'halo': {'w': 0.55, 'events': ('halo',)},
                'coda': {'w': 0.6, 'events': ('coda',)}}
"""Round op1's POLISH plans (oc2's judges: the summit-only pieces lost, the a cappella / halo / coda won): the summit
rarer, the a cappella also alone, the halo / coda plans more likely."""

CHOIR_POLISH = {'caps': {'summit': 2, 'lead_in': 1, 'acappella': 3, 'halo': 3, 'coda': 3}, 'tex_keep': 0.25,
                'halo_min_bars': 4, 'leave': ('melody', 'doubling'), 'leave_share': 0.4, 'leave_off': (-6.0, -3.0),
                'summit_db': 2.0}
"""Round op1's POLISH (CHOIR['polish'], genres.symphony_polish; oc2's judges' fixes): the gesture caps per 8 slots (the
summit - the choir's climax entry - at most twice), the summit's texture with the set's memory (the slot before's
texture kept with 'tex_keep', else the other: unison / hymn about half and half), no halo shorter than
'halo_min_bars' plan bars (an intro of 2 bars is no block for it), and at the sung summit the orchestra's melody
instruments LEAVE the theme ('leave' functions sounding the sung line's pitch class on at least 'leave_share' of
their onsets: their notes there become held chord tones, the brass / the rest 'leave_off' velocity steps softer) so the
choir carries it, sung 'summit_db' dB louder."""


def plans() -> dict:
    """The plans of the switched choir version (PLANS_POLISH under POLISH, PLANS_V2 under CHOIR v2, else PLANS)."""
    C = CHOIR or {}
    return PLANS_POLISH if C.get('polish') else PLANS_V2 if C.get('v2') else PLANS


def choir_slot(slot: dict, history: list, rng) -> None:
    """composer.set_plan's POLISH hook (round op1): the summit's texture with the set's memory - the last sung summit's
    texture kept with CHOIR['polish']['tex_keep'], else the other (slot['choir_tex'])."""
    P = (CHOIR or {}).get('polish')
    if not P or 'summit' not in plans().get(slot.get('choir'), {}).get('events', ()):
        return
    prev = next((h.get('choir_tex') for h in reversed(history) if h.get('choir_tex')), None)
    texs = sorted(CHOIR['tex'])
    if prev is None:
        slot['choir_tex'] = texs[rng.randrange(len(texs))]
    else:
        slot['choir_tex'] = prev if rng.random() < P['tex_keep'] else next(t for t in texs if t != prev)


QUIET_KINDS = ('t2', 'trio', 'river', 'recap2', 't2b', 'source', 'mist', 'slow')
"""The blocks a halo may sound over, best first (non-peak, the block's dynamics at most mf)."""
LINE_FNS = ('melody', 'counter', 'voice', 'doubling')
_EPS = 1e-6


def choir_draw(feel: str, rng, history=()) -> str:
    """One piece's choir plan: a weighted draw (PLANS x FEELS), x CHOIR['memory'] for the slot before's / the one
    before that's plan, x CHOIR['share'] for a plan sharing an event with the slot before's (the summit not in every
    piece); never 'none' after 'none' (history: the earlier slots' plans, newest last)."""
    C = CHOIR or CHOIR_ON
    P = plans()
    m1, m2 = C['memory']
    w = {}
    last = history[-1] if history else None
    used = {}
    if C.get('v2'):                          # (v2: the gestures' memory over the set so far - 'window' slots)
        for h in history[-C['window']:]:
            for e in P.get(h, {}).get('events', ()):
                used[e] = used.get(e, 0) + 1
    for name, x in P.items():
        v = x['w'] * FEELS.get(feel, {}).get(name, 1.0)
        if last == name:
            v *= 0.0 if name == 'none' else m1
        elif len(history) > 1 and history[-2] == name:
            v *= m2
        if last in P and last != name and set(x['events']) & set(P[last]['events']):
            v *= C['share']
        for e in x['events'] if C.get('v2') else ():
            v *= 0.0 if used.get(e, 0) >= C['caps'][e] else C['gesture'] ** used.get(e, 0)
        if v > 0:
            w[name] = v
    if not w:
        return 'none'
    tot = sum(w.values())
    r = rng.random() * tot
    for name in sorted(w):
        r -= w[name]
        if r <= 0:
            return name
    return sorted(w)[-1]


# ------------------------------------------------------------------------------------------------ placing

def _bar(mat: dict, k: float) -> float:
    return mat['U'] * k


def _span_s(tune, a: float, z: float) -> float:
    return (z - a) * 60.0 / float(tune.tempo)


def _places(name: str, mat: dict, score, tune, k: float, taken: list) -> list:
    """Where an event goes -> [(block, a, z, extra)] (song beats), [] when the piece has no place for it."""
    from .symphony import _vmax
    from ..bandlib.scoring import VEL
    C = CHOIR or CHOIR_ON
    bl = list(zip(mat['blocks'], score.blocks))
    bar = _bar(mat, k)
    ip = next((i for i, (x, _) in enumerate(bl) if x['peak']), None)

    def free(a, z):
        return all(z <= x0 + _EPS or a >= x1 - _EPS for x0, x1 in taken)
    if name == 'summit' and ip is not None:
        b = bl[ip][1]
        return [(b, b.start, b.end, {'quiet': mat.get('climax') == 'quiet'})]
    if name == 'lead_in' and ip is not None and ip > 0:
        b = bl[ip - 1][1]
        n = C['lead_bars']
        if b.length >= (n + 1) * bar - _EPS and free(b.end - n * bar, b.end):
            return [(b, b.end - n * bar, b.end - 0.25, {})]
        return []
    if name == 'acappella' and ip is not None and ip > 0:
        i = ip - 2 if ip >= 2 and bl[ip - 1][0]['kind'] == 'retrans' else ip - 1
        if i < 0 or bl[i][0]['kind'] in ('intro', 'slow', 'solo', 'mist', 'source') or bl[i][0]['peak']:
            return []
        b = bl[i][1]
        bar_s = _span_s(tune, 0, bar)
        lo, hi = C['acap_s'][1], C['acap_s'][2]
        n = max(lo, min(hi, int(-(-C['acap_s'][0] // bar_s))))
        n = min(n, int(round(b.length / bar)) - 2)
        if n < lo:
            return []
        a = b.end - n * bar
        return [(b, a, b.end, {})] if free(a, b.end) else []
    if name == 'halo':
        out = []
        for kd in QUIET_KINDS:
            for i, (x, b) in enumerate(bl):
                if x['kind'] != kd or x['peak'] or _vmax(b) > VEL['mf']:
                    continue
                n = int(round(b.length / bar))
                a = b.start + (n // 2) * bar if n >= 8 else b.start
                if free(a, b.end):
                    out.append((b, a, b.end, {'before_peak': ip is None or i < ip}))
        return out
    if name == 'coda':
        for i, (x, b) in enumerate(bl):
            if x['kind'] in ('coda', 'coda_soft'):
                z = b.end
                soft = x['kind'] == 'coda_soft'
                if i + 1 < len(bl) and bl[i + 1][0]['kind'] in ('end', 'end_soft'):
                    z = bl[i + 1][1].end
                    soft = soft or bl[i + 1][0]['kind'] == 'end_soft'
                if free(b.start, z):
                    return [(b, b.start, z, {'soft': soft})]
        return []
    return []


# ------------------------------------------------------------------------------------------------ the notes

def _clip(notes, a: float, z: float) -> list:
    out = []
    for st, du, p in notes:
        e = st + du
        if e <= a + _EPS or st >= z - _EPS:
            continue
        st2, e2 = max(st, a), min(e, z)
        if e2 - st2 > 0.05:
            out.append((st2, e2 - st2, p))
    return out


def _mono(notes) -> list:
    """The top note at each onset, each cut at the next onset."""
    by = {}
    for st, du, p in notes:
        k = round(st, 4)
        if k not in by or p > by[k][2]:
            by[k] = (st, du, p)
    xs = [by[k] for k in sorted(by)]
    return [(st, min(du, xs[i + 1][0] - st) if i + 1 < len(xs) else du, p) for i, (st, du, p) in enumerate(xs)]


def _line(plan_o, b, a: float, z: float, tune, melody: bool = False, relaxed: bool = False) -> tuple:
    """The block's most singable line in [a, z): (role, function, notes) - the longest median note (s), the melody
    first at a tie, covering at least 40 % of the span - or (None, None, []). melody: a melody that qualifies wins
    (v2: the choir sings the theme); relaxed: any line or upper part but the bass / pedal, 25 % cover (v2's fallback:
    a sung phrase, never held vowels)."""
    bps = 60.0 / float(tune.tempo)
    groups = {}
    for p in plan_o.parts:
        ok = p.function in LINE_FNS and p.line if not relaxed else \
            p.function not in ('bass', 'pedal') and p.role not in ('timpani', 'percussion', 'basses')
        if p.block == b.name and ok and p.notes:
            groups.setdefault((p.role, p.function), []).extend(p.notes)
    if melody and any(fn == 'melody' for _, fn in groups):
        got = _line_of({k_: v for k_, v in groups.items() if k_[1] == 'melody'}, a, z, bps, 0.4)
        if got[0]:
            return got
    return _line_of(groups, a, z, bps, 0.25 if relaxed else 0.4)


def _line_of(groups: dict, a: float, z: float, bps: float, least: float) -> tuple:
    """_line's choice among groups {(role, function): notes}: the best covering at least `least` of [a, z)."""
    best = None
    for (role, fn), ns in sorted(groups.items()):
        ns = _mono(_clip(ns, a, z))
        if len(ns) < 2:
            continue
        cover = sum(d for _, d, _ in ns) / max(_EPS, z - a)
        if cover < least:
            continue
        ds = sorted(d for _, d, _ in ns)
        med = ds[len(ds) // 2] * bps
        sc = med * (1.25 if fn == 'melody' else 1.0) * min(1.0, cover / 0.7)
        if best is None or sc > best[0] + 1e-9:
            best = (sc, role, fn, ns)
    return (best[1], best[2], best[3]) if best else (None, None, [])


def _skeleton(ns, tune) -> list:
    """The line's long notes: a note shorter than CHOIR['min_s'] (v2: 'line_min_s') joins the note before (its pitch
    held over it)."""
    C = CHOIR or CHOIR_ON
    mn = C['line_min_s' if C.get('v2') else 'min_s'] * float(tune.tempo) / 60.0
    out = []
    for st, du, p in ns:
        if out and du < mn - _EPS and st - (out[-1][0] + out[-1][1]) < 0.3:
            o = out[-1]
            out[-1] = (o[0], st + du - o[0], o[2])
        else:
            out.append((st, du, p))
    return out


def _soprano(ns, centre: float = 70.0) -> list:
    """The line transposed by octaves for the sopranos: the shift that puts its median nearest `centre`, then every
    note in the range (VOICES['S']) at the octave nearest the note before (the contour kept, an octave fold only at
    the range's edges)."""
    lo, hi = VOICES['S'][0], VOICES['S'][1]
    ps = sorted(p for _, _, p in ns)
    med = ps[len(ps) // 2]
    sh = min((12, 0, -12, -24), key=lambda x: (abs(med + x - centre), -x))
    res, prev, prev_p = [], None, None
    for st, du, p in ns:
        cands = [q for q in range(p + sh - 36, p + sh + 37, 12) if lo <= q <= hi]
        ref = p + sh if prev is None else prev + (p - prev_p)
        q = min(cands, key=lambda x: (abs(x - ref), -x))
        res.append((st, du, q))
        prev, prev_p = q, p
    return res


def _chords(chart, a: float, z: float, gmin: float) -> list:
    """The chart in [a, z) as (start, end, symbol), a change shorter than gmin joined to the chord before."""
    rows = []
    for st, du, sym in chart:
        e = st + du
        if e <= a + _EPS or st >= z - _EPS or not sym:
            continue
        st2, e2 = max(st, a), min(e, z)
        if rows and (e2 - st2 < gmin - _EPS):
            rows[-1] = (rows[-1][0], e2, rows[-1][2])
        else:
            rows.append((st2, e2, sym))
    if rows and rows[0][0] > a + _EPS:
        rows[0] = (a, rows[0][1], rows[0][2])
    return rows


def _voice(steps, key, voices) -> list:
    """voicing.voice step by step (the voicing before carried): a step it cannot voice with the soprano fixed is voiced
    free, one it cannot voice at all is a rest (None)."""
    from .. import voicing as vc
    out, prev = [], {}
    for st in steps:
        got = None
        for fixed in ((st.get('fixed') or {}), {}):
            try:
                got = vc.voice([dict(st, fixed=fixed)], voices=voices, key=key, prev=prev or None)[0]
                break
            except ComposeError:
                continue
        out.append(got)
        if got:
            prev = dict(got)
    return out


def _write(ev: dict, b, mat: dict, k: float, tune, plan_o) -> dict:
    """An event's SATB notes: {part: [(start, dur, pitch, vowel)]} (song beats)."""
    C = CHOIR or CHOIR_ON
    E = EVENTS[ev['event']]
    a, z = ev['start'], ev['end']
    bar = _bar(mat, k)
    beat_s = 60.0 / float(tune.tempo)
    gmin = max(1.0, 0.45 / beat_s)
    voices = dict(VOICES)
    role = fn = None
    line = []
    v2 = bool(C.get('v2'))
    if ev['event'] in ('summit', 'acappella', 'coda') or v2:
        role, fn, line = _line(plan_o, b, a, min(z, b.end), tune, melody=v2)
        if not line and v2:
            role, fn, line = _line(plan_o, b, a, min(z, b.end), tune, relaxed=True)
    if line:
        sop = _soprano(_skeleton(line, tune), {'summit': 72.0, 'halo': 67.0}.get(ev['event'], 69.0) if v2 else
                       72.0 if ev['event'] == 'summit' else 69.0)
    else:
        sop = []
    avoid = []
    if ev['event'] == 'halo' and not sop:
        _, _, mel = _line(plan_o, b, a, z, tune)
        avoid = mel
        if mel:
            ps = sorted(p for _, _, p in mel)
            if ps[len(ps) // 2] >= 72:                       # (a high line: the halo under it)
                cap = max(66, ps[0] - 2)
                voices['S'] = (60, min(79, cap), min(68, cap - 3))
                voices['A'] = (57, min(74, cap - 3), 63)
    # the segments: every soprano onset and every chord change (the end block's chart too)
    charts = [(st, du, sym) for x in ev['blocks'] for st, du, sym in x.chart]
    rows = _chords(charts, a, z, gmin)
    cuts = {round(r[0], 4) for r in rows} | {round(r[1], 4) for r in rows}
    if sop:
        for st, du, _ in sop:
            cuts.add(round(st, 4))
            cuts.add(round(st + du, 4))
    ts = sorted(x for x in cuts if a - _EPS <= x <= z + _EPS)
    segs = []
    for t0, t1 in zip(ts, ts[1:]):
        if t1 - t0 < 0.05:
            continue
        sym = next((r[2] for r in rows if r[0] - _EPS <= t0 < r[1] - _EPS), None)
        if sym is None:
            continue
        s_p = None
        if sop:
            s_p = next((p for st, du, p in sop if st - _EPS <= t0 < st + du - _EPS), None)
            if s_p is None:
                continue                                       # (the line rests: the choir breathes)
        segs.append((t0, t1, sym, s_p))
    if not segs:
        return {}
    steps = [{'chord': sym, 'fixed': {'S': s_p} if s_p is not None else {},
              'avoid': sorted({p for st, du, p in avoid if st < t1 - _EPS and st + du > t0 + _EPS})}
             for t0, t1, sym, s_p in segs]
    voiced = _voice(steps, b.key, voices)
    # the phrases: vowels phrase by phrase, a breath at every phrase end
    ph = E.get('phrase', C['phrase']) * bar
    n_ph = max(1, int(round((z - a) / ph)))
    vowels = E['vowels']
    if ev.get('quiet') and E.get('quiet'):
        vowels = E['quiet']
    if ev.get('soft') and E.get('soft'):
        vowels = E['soft']

    def vowel(t):
        i = min(n_ph - 1, int((t - a + _EPS) // ph))
        return vowels[round(i * (len(vowels) - 1) / (n_ph - 1)) if n_ph > 1 else 0]
    br = C['breath_s'] / beat_s
    bounds = [a + i * ph for i in range(1, n_ph)]
    if v2 and sop and ev.get('tex') == 'unison':
        voiced = _unison(segs, voiced, rows, b.key, sop)
    parts = {v: [] for v in VOICES}
    for (t0, t1, _, _), vc_ in zip(segs, voiced):
        if not vc_:
            continue
        w = vowel(t0)
        for v, p in vc_.items():
            ns = parts[v]
            last = ns[-1] if ns else None
            joined = last and abs(last[0] + last[1] - t0) < 1e-4 and last[3] == w and \
                not any(abs(t0 - x) < 1e-4 for x in bounds)
            if joined and last[2] == p:
                ns[-1] = (last[0], t1 - last[0], p, w)
            else:
                ns.append((t0, t1 - t0, p, w))
    for v, ns in parts.items():                              # (the breaths: before a new phrase or vowel, at the end)
        out = []
        for i, (st, du, p, w) in enumerate(ns):
            e = st + du
            nxt = ns[i + 1] if i + 1 < len(ns) else None
            if nxt and abs(e - nxt[0]) < 1e-4 and (nxt[3] != w or any(abs(nxt[0] - x) < 1e-4 for x in bounds)):
                e -= min(br, 0.4 * du)
            out.append((st, e - st, p, w))
        parts[v] = out
    ev['line'] = f"{role}:{fn}" if role else None
    ev['line_role'] = role
    return {v: ns for v, ns in parts.items() if ns}


def _unison(segs, voiced, rows, key, sop) -> list:
    """v2's 'unison' summit: the tenors sing the sopranos' theme an octave under, alto and bass the harmony - voiced
    once per chord (under the theme's note at the chord's start), held through the chord while the theme moves."""
    vs = {v: VOICES[v] for v in ('S', 'A', 'B')}
    steps = []
    for r0, r1, sym in rows:
        s_p = next((p for st, du, p in sop if st - _EPS <= r0 < st + du - _EPS), None)
        if s_p is None:
            s_p = next((p for st, du, p in sop if r0 - _EPS <= st < r1 - _EPS), None)
        steps.append({'chord': sym, 'fixed': {'S': s_p} if s_p is not None else {}})
    low = _voice(steps, key, vs)
    out = []
    for (t0, t1, _, s_p), vc_ in zip(segs, voiced):
        if not vc_:
            out.append(vc_)
            continue
        i = next((j for j, r in enumerate(rows) if r[0] - _EPS <= t0 < r[1] - _EPS), None)
        lo = (low[i] if i is not None else None) or vc_
        got = {'S': vc_['S'], 'T': vc_['S'] - 12 if vc_['S'] - 12 >= VOICES['T'][0] else vc_['S'],
               'A': lo['A'], 'B': lo['B']}
        if got['A'] >= got['S'] or got['A'] <= got['T']:
            got['A'] = vc_['A'] if vc_['A'] > got['T'] else None
        if got['B'] >= got['T']:
            got['B'] = vc_['B'] if vc_['B'] < got['T'] else None
        out.append({v: p for v, p in got.items() if p is not None})
    return out


def _soften(plan_o, a: float, z: float, pick) -> int:
    """v2: the parts pick(part) -> a velocity offset (or None) get it on their notes starting in [a, z) (the part
    split, as _thin does). -> notes softened."""
    n, extra = 0, []
    for p in plan_o.parts:
        d = pick(p)
        if not d:
            continue
        inside = [x for x in p.notes if a - _EPS <= x[0] < z - _EPS]
        if not inside:
            continue
        p.notes = [x for x in p.notes if not (a - _EPS <= x[0] < z - _EPS)]
        sf_in = tuple(t_ for t_ in p.sf if a - _EPS <= t_ < z - _EPS)
        p.sf = tuple(t_ for t_ in p.sf if t_ not in sf_in)
        extra.append(dataclasses.replace(p, notes=inside, off=p.off + d, sf=sf_in))
        n += len(inside)
    plan_o.parts.extend(extra)
    plan_o.parts[:] = [p for p in plan_o.parts if p.notes]
    plan_o.notes = sum(len(p.notes) for p in plan_o.parts)
    return n


def _thin(plan_o, a: float, z: float) -> int:
    """The a cappella: the orchestra leaves [a, z) - every part's notes there removed, the notes held into it cut at a
    - but for the bass line (basses / cellos 'bass' / 'pedal'), which stays, softer (CHOIR['acap_bass']). -> notes
    removed."""
    C = CHOIR or CHOIR_ON
    gone = 0
    extra = []
    for p in plan_o.parts:
        keep = p.role in ('basses', 'cellos') and p.function in ('bass', 'pedal')
        new, inside = [], []
        for st, du, q in p.notes:
            if st >= z - _EPS or st + du <= a + _EPS:
                new.append((st, du, q))
            elif keep:
                inside.append((st, du, q)) if st >= a - _EPS else new.append((st, du, q))
            elif st < a - _EPS:
                if a - 0.05 - st > 0.1:
                    new.append((st, a - 0.05 - st, q))
                else:
                    gone += 1
            else:
                gone += 1
        p.notes = new
        if inside:
            extra.append(dataclasses.replace(p, notes=inside, off=p.off + C['acap_bass'], sf=()))
    plan_o.parts.extend(extra)
    plan_o.parts[:] = [p for p in plan_o.parts if p.notes]
    plan_o.notes = sum(len(p.notes) for p in plan_o.parts)
    return gone


def _density(plan_o, a: float, z: float) -> int:
    """The roles sounding in [a, z) (the brass count twice)."""
    from ..bandlib.orchestra import BRASS
    rs = {p.role for p in plan_o.parts if any(st < z - _EPS and st + du > a + _EPS for st, du, _ in p.notes)}
    return len(rs) + sum(1 for r in rs if r in BRASS)


def prepare(plan_o, score, mat: dict, tune, k: float) -> dict | None:
    """CHOIR after the orchestration: the piece's plan (tune.arrange['choir'], else its own draw), its events placed
    and written (SATB notes), the a cappella's orchestra thinned. -> {'plan', 'events'} or None (no choir)."""
    C = CHOIR or CHOIR_ON
    P = plans()
    name = (tune.arrange or {}).get('choir') or choir_draw(tune.feel, random.Random(f"sym-choir:{tune.seed}"))
    if name not in P:
        raise ComposeError(f"choir plan {name!r}: one of {', '.join(P)}")
    taken, events = [], []
    order = list(score.blocks)
    rng = random.Random(f"sym-choir-v2:{tune.seed}")
    for evn in P[name]['events']:
        cands = _places(evn, mat, score, tune, k, taken)
        if C.get('v2') and evn == 'halo':     # (v2: the halo sings a line - a block that has one; at most halo_bars)
            bar = _bar(mat, k)
            cands = [(b, (b.start if b.length <= C['halo_bars'] * bar + _EPS else
                          b.start + int(round(b.length / bar)) // 2 * bar), b.end, x) for b, _, _, x in cands]
            cands = [c for c in cands if _line(plan_o, c[0], c[1], c[2], tune, melody=True)[0]] or cands
            if C.get('polish'):              # (round op1: no halo shorter than halo_min_bars - not a 2-bar intro)
                cands = [c for c in cands if c[2] - c[1] >= C['polish']['halo_min_bars'] * bar - _EPS]
        if C.get('v2') and evn == 'summit' and cands:
            b, a, z, x = cands[0]
            n = int(round((z - a) / _bar(mat, k)))
            x = dict(x, tex=_pick(C['tex'], rng))
            if C.get('polish') and (tune.arrange or {}).get('choir_tex') in C['tex']:
                x['tex'] = tune.arrange['choir_tex']     # (round op1: the set's texture memory - choir_slot)
            if rng.random() < C['late'] and n >= 8:
                a = a + (n // 2) * _bar(mat, k)          # (the theme's second statement in the peak, not the arrival)
                x['late'] = True
            cands = [(b, a, z, x)]
        if evn == 'halo' and name == 'halo_summit':
            cands = [c for c in cands if c[3].get('before_peak')] or cands
        if evn == 'halo':                    # (the sparsest quiet block first: the halo heard, not buried)
            cands = sorted(cands, key=lambda c: _density(plan_o, c[1], c[2]))
        if not cands:
            continue
        b, a, z, extra = cands[0]
        i = order.index(b)
        blocks = [x for x in order[i:] if x.start < z - _EPS]
        ev = dict(event=evn, block=b.name, start=a, end=z, blocks=blocks, **extra)
        notes = _write(ev, b, mat, k, tune, plan_o)
        if not notes:
            continue
        ev['notes'] = notes
        taken.append((a, z))
        if evn == 'acappella':
            ev['thinned'] = _thin(plan_o, a, z)
        elif C.get('polish') and evn == 'summit':     # (round op1: the orchestra leaves the sung theme)
            ev['left'] = _leave(plan_o, a, z, ev, tune)
        elif C.get('v2') and evn in ('summit', 'coda', 'halo'):
            ev['softened'] = _soften(plan_o, a, z, _under(evn, ev.get('line_role')))
        events.append(ev)
    return {'plan': name, 'events': events}


def _leave(plan_o, a: float, z: float, ev: dict, tune) -> list:
    """POLISH (round op1): at the sung summit the orchestra's melody instruments leave the theme - a part of
    CHOIR['polish']['leave'] functions sounding the sopranos' pitch class on at least 'leave_share' of its onsets in
    [a, z) (or the line the choir took) holds chord tones there instead (one per chord, voice-led from its own median,
    never the sung note's pitch class where it can, only where it played; 'sustain', no line), the brass / the rest
    'leave_off' velocity steps softer. -> the roles that left."""
    from ..bandlib.orchestra import BRASS
    from ..theory import chord
    P = CHOIR['polish']
    sop = ev['notes'].get('S') or []
    if not sop:
        return []
    beat_s = 60.0 / float(tune.tempo)
    rows = _chords([(st, du, sym) for x in ev['blocks'] for st, du, sym in x.chart], a, z, max(1.0, 0.45 / beat_s))

    def sung(t):
        return next((p % 12 for st, du, p, _ in sop if st - 0.3 <= t < st + du - _EPS), None)
    left, extra = [], []
    for p in plan_o.parts:
        if p.function not in P['leave'] or not p.line or not p.notes:
            continue
        inside = [x for x in p.notes if a - _EPS <= x[0] < z - _EPS]
        if len(inside) < 2:
            continue
        hit = sum(1 for st, _, q in inside if sung(st) == q % 12)
        if p.role != ev.get('line_role') and hit < P['leave_share'] * len(inside):
            continue
        lo, hi = min(q for _, _, q in inside), max(q for _, _, q in inside)
        prev = sorted(q for _, _, q in inside)[len(inside) // 2]
        held = []
        for r0, r1, sym in rows:
            if not any(st < r1 - _EPS and st + du > r0 + _EPS for st, du, _ in inside):
                continue
            pcs = set(chord(sym).pcs)
            s_pc = sung(r0)
            cands = [q for q in range(lo - 2, hi + 1) if q % 12 in pcs and q % 12 != s_pc]
            cands = cands or [q for q in range(lo - 2, hi + 1) if q % 12 in pcs]
            if not cands:
                continue
            q = min(cands, key=lambda x: (abs(x - prev), x))
            held.append((r0, r1 - r0, q))
            prev = q
        p.notes = [x for x in p.notes if not (a - _EPS <= x[0] < z - _EPS)]
        sf_in = tuple(t_ for t_ in p.sf if a - _EPS <= t_ < z - _EPS)
        p.sf = tuple(t_ for t_ in p.sf if t_ not in sf_in)
        if held:
            off = P['leave_off'][0] if p.role in BRASS else P['leave_off'][1]
            extra.append(dataclasses.replace(p, notes=held, function='harmony', art='sustain', line=False,
                                             off=p.off + off, sf=()))
        left.append(p.role)
    plan_o.parts.extend(extra)
    plan_o.parts[:] = [p for p in plan_o.parts if p.notes]
    plan_o.notes = sum(len(p.notes) for p in plan_o.parts)
    return sorted(set(left))


def _under(evn: str, line_role):
    """v2: who plays softer under the sung theme -> pick(part) for _soften: under a halo the line's own instrument
    (CHOIR['halo_line']: the choir takes the line), under the summit / coda the brass / woodwind parts doubling a line
    (CHOIR['under'])."""
    from ..bandlib.orchestra import BRASS
    C = CHOIR or CHOIR_ON
    br, ww = C['under']

    def pick(p):
        if evn == 'halo':
            return C['halo_line'] if p.role == line_role and p.line else None
        if p.function in ('melody', 'doubling', 'counter') and p.line:
            return br if p.role in BRASS else ww if p.role in ('flutes', 'oboes', 'clarinets', 'bassoons') else None
        return None
    return pick


def _pick(w: dict, rng) -> str:
    """A weighted draw from {name: weight}."""
    r = rng.random() * sum(w.values())
    for k_ in sorted(w):
        r -= w[k_]
        if r <= 0:
            return k_
    return sorted(w)[-1]


# ------------------------------------------------------------------------------------------------ the sound

def _split(notes, part: str, tm, max_s: float) -> list:
    """Notes longer than max_s seconds re-attacked (equal pieces, a 0.1 s breath; the parts staggered)."""
    stag = {'S': 0.0, 'A': 0.09, 'T': 0.05, 'B': 0.13}.get(part, 0.0)
    out = []
    for st, du, p, w in notes:
        sec = tm.seconds_between(st, st + du)
        n = int(sec // max_s) + 1 if sec > max_s else 1
        if n == 1:
            out.append((st, du, p, w))
            continue
        piece = du / n
        cuts = [st] + [st + piece * (i + stag) for i in range(1, n)] + [st + du]
        gap = 0.1 * du / sec
        for i, (x0, x1) in enumerate(zip(cuts, cuts[1:])):
            out.append((x0, x1 - x0 - (gap if i < n - 1 else 0.0), p, w))
    return out


def sing(s, band, sc, ch: dict, gain: float = 0.0) -> None:
    """Sing the prepared events (prepare) on vocalset-choir tracks in the band's hall: per part and vowel Score.sing
    (the dynamics map + the event's offset / the a cappella's target), orch.Choir.perform. Sets s.choir_plan and
    s.choir_events (choir_stats)."""
    from ..bandlib import orchestra as orch
    C = CHOIR or CHOIR_ON
    s.choir_plan = ch['plan']
    s.choir_events = []
    if not ch['events']:
        return
    vowels = sorted({w for ev in ch['events'] for ns in ev['notes'].values() for *_, w in ns})
    choir = orch.vocalset_choir(s, band, vowels, gain_db=gain + C['gain'], send=C['send'])
    tm = s.tempo_map()
    for ev in ch['events']:
        E = EVENTS[ev['event']]
        a, z = ev['start'], ev['end']
        off = C['halo_off'] if E.get('off', 0.0) is None else E.get('off', 0.0)
        offs = _ramp(sc, a, z, *C['acap_dyn']) if ev['event'] == 'acappella' else None
        if offs is not None:
            off = 0.0
        db = E.get('soft_db', E['db']) if ev.get('soft') else E['db']
        if ev['event'] == 'acappella' and C.get('v2'):
            db = C['acap_db']
        if ev['event'] == 'summit' and C.get('polish'):
            db += C['polish']['summit_db']
        cnt = 0
        for part, ns in ev['notes'].items():
            ns = _split(ns, part, tm, C['max_s'])
            for w in sorted({x[3] for x in ns}):
                grp = [(st, du, p) for st, du, p, w_ in ns if w_ == w]
                key = f'{part}_{w}'
                n0 = len(choir.sung.get(key, ()))
                sc.sing(choir, key, grp, off=off, offs=offs, accent=False)
                choir.lane(key, _levels(choir.sung[key][n0:], db))
                cnt += len(grp)
        s.choir_events.append({'event': ev['event'], 'block': ev['block'], 'start': round(a, 3), 'end': round(z, 3),
                               'vowels': sorted({x[3] for ns in ev['notes'].values() for x in ns}),
                               'line': ev.get('line'), 'notes': cnt, 'thinned': ev.get('thinned', 0),
                               **{x: ev[x] for x in ('tex', 'late', 'softened', 'left') if x in ev}})
    choir.perform()


def _ramp(sc, a: float, z: float, v0: float, v1: float):
    """Score.sing's offs for a velocity ramp v0 -> v1 over [a, z) (instead of the dynamics map)."""
    def offs(n):
        return v0 + (v1 - v0) * (n[0] - a) / max(_EPS, z - a) - sc.vel(n[0], 0.0, False)
    return offs


def _levels(notes, db: float) -> list:
    """The expression points of sung notes (start, dur, pitch, vel): per onset the gain of its velocity (CHOIR
    ['level']) + db, reached a quarter beat before the note (its early start), held through it."""
    C = CHOIR or CHOIR_ON
    k, ref, lo = C['level']
    out = []
    for st, du, p, v in sorted(notes):
        g = max(lo, min(0.0, (v - ref) * k)) + db
        e = min(1.0, 10 ** (g / 40.0))
        if out and st - 0.25 <= out[-1][0] + 1e-4:
            continue
        out.append((st - 0.25, e, 'smooth'))
        out.append((st + du, e, 'smooth'))
    return out


def choir_stats(song) -> dict:
    """The choir of a built piece: its plan, its events (event, block, beats, vowels, the line it sang, notes) and
    the sung notes per part."""
    evs = list(getattr(song, 'choir_events', None) or [])
    per = {}
    for t in getattr(song, 'tracks', {}).values():
        tid = getattr(t, 'id', '')
        if tid.startswith('choir_') and tid.count('_') == 2:
            per.setdefault(tid.split('_')[1].upper(), 0)
    return {'plan': getattr(song, 'choir_plan', None), 'events': evs, 'parts': sorted(per)}
