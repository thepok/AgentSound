"""Endless orchestra-symphonic SOLO (round os1): the solo players of the symphony orchestra for expression.

A real orchestra plays an exposed woodwind or horn line on ONE player - "oboe solo", "horn solo" -, the sections a2
only in tutti and doublings; it gives a lyrical passage to the concertmaster or the principal cello as an event,
and the leader's own violin colours the violins I's soft cantilena. With SOLO on, after the orchestration (and the
techniques), symphony.build_symphony hands the parts here (solo_pass):

  1. wind solos: a woodwind / horn part carrying the theme or a counter-line (functions 'melody' / 'counter', a
     line, one note at a time) in a block that is no tutti (at most SOLO['tutti'] roles, not the climax, its
     loudest mark at most the family's cap) and not doubled at the unison / octave by another role (at most
     SOLO['doubled'] of its notes) moves to the section's solo player (orch.SOLOS: the VSCO 2 CE flute / oboe /
     clarinet / bassoon / horn, a legato player - orch.perform gives it the solo's phrase lane with swells on long
     notes, its breaths, the recorded vibrato where the set has one, its own timing);
  2. the string solo EVENT: per piece the set plan draws one ('violin' | 'cello' | 'none', slot['solo'] with the set's
     memory: never the same solo twice in a row, never three pieces without one - solo_slot); the most lyrical soft
     block where the violins I (the cellos) carry the theme gives it to the solo violin (cello), the strings under it
     softer (SOLO['event']['soft'] velocity steps), the doublings of the line left out - the solo alone on top;
  3. the concertmaster: on the violins I's slow, soft cantilena (no climax, at most mf, notes of SOLO['cm']['dur_s']
     on average) a quiet solo violin plays the same line (orch.SOLOS 'violin_concertmaster', its fader ~12 dB under
     the section, its own timing and vibrato) - the section's expressive edge;
  4. the section expression (SOLO['rules'] on the score's player): deeper, more frequent swells inside long notes,
     a smoother string legato.

SOLO None = off: nothing is called, the renders are master's bit for bit (genres.symphony_solo switches it with
the set draw, plan['set_solo'], and composer.set_plan's hook)."""
from __future__ import annotations

import random

from ..bandlib import orchestra as orch
from ..bandlib.orchestration import Part
from ..bandlib.scoring import VEL
from ..theory import note

__all__ = ['SOLO', 'SOLO_ON', 'SOLO_POLISH', 'solo_pass', 'solo_slot', 'solo_draw', 'solo_stats', 'polish_band']

_EPS = 1e-6

SOLO = None
"""None = off (bit-identical); SOLO_ON = round os1's solo players (genres.symphony_solo)."""

SOLO_POLISH = {'cm_db': 4.0, 'run': 2, 'cello_med': (52, 64), 'cello_counter_s': 0.5}
"""Round op1's POLISH (SOLO['polish'], genres.symphony_polish; os1's judges): the concertmaster's fader this many dB up
(it sat ~17 dB under the violins I, the target 10-14); at most 'run' blocks in a row with an exposed solo player (a
wind solo, the string event, the concertmaster: the "parade" of 3-4 soft solo episodes handing one phrase round - the
next block plays it on the section); the cello event (it never fired: the cellos carry no 'melody' part) sings the
violins I's theme an octave or two down (its median inside 'cello_med'), else the cellos' own counter-line (mean
notes at least 'cello_counter_s' s)."""

SOLO_ON = {
    'winds': {'flutes': 'flute_solo', 'oboes': 'oboe_solo', 'clarinets': 'clarinet_solo',
              'bassoons': 'bassoon_solo', 'horns': 'horn_solo'},
    'fns': ('melody', 'counter'),
    'arts': ('sustain', 'legato', 'staccato'),
    'cap': {'woodwinds': 'f', 'horns': 'mf'},
    'tutti': 10,
    'doubled': 0.5,
    'chords': 0.1,
    'min_notes': 4,
    'fast_s': 0.1,
    'cm': {'cap': 'mf', 'dur_s': 0.45, 'min_notes': 6},
    'event': {'kinds': {'violin': 1.0, 'cello': 0.8, 'none': 0.8}, 'cap': 'mf', 'dur_s': 0.5, 'min_notes': 6,
              'tutti': 8, 'avoid': ('tutti', 'drive', 'hammer', 'march', 'pulse', 'walk'),
              'soft': -10.0, 'roles': {'violin': ('violins1', 'violin_solo'), 'cello': ('cellos', 'cello_solo')},
              'prefer': ('t2', 't2b', 'slow', 'intro', 'mist', 'solo', 'coda_soft', 'end_soft', 'close', 'mid',
                         'mid2', 'episode', 'recap2', 'var', 'false', 'river')},
    'rules': {'dynamics': {'swell_s': 1.0, 'swell_db': (2.0, 1.2, 7.0), 'swell_share': 0.85},
              'legato': {'overlap_ms': {'strings': (55.0, 90.0)}}},
}
"""Round os1's solo players: 'winds' the section -> its solo player; a part of 'fns' in 'arts' with at least
'min_notes' notes inside the player's range (orch.SOLO_RANGE), none written shorter than 'fast_s' seconds (a legato
player's transition swallows a faster note: round os1's gate, a clarinet's 32nd turns silent), at most 'chords' of
them struck together (one player: the top note kept), at most 'doubled' of them
doubled at the unison / octave by another role, in a block of at most 'tutti' roles whose loudest mark is at most
'cap' of the family, not the climax. 'cm' the concertmaster's line (cap, the mean note length in seconds, notes);
'event' the string solo: the draw's weights, the block's cap, the line's mean note length (s) and notes, the block's
roles at most ('tutti') and no texture named with an 'avoid' word (a driving tutti is no place for it), the strings
under it 'soft' velocity steps, the section / solo roles per kind, the block kinds preferred (most lyrical first);
'rules' the orchestra player's rules (ensemble.RULES) for the whole score: the section expression - a long note
swells from 1.0 s (ensemble 1.2), deeper (2 dB + 1.2 dB/s, at most 7) and more often (0.85), the strings' legato
overlaps 55-90 ms (40-70)."""


def _lv(m) -> float:
    return float(VEL.get(m, 78) if isinstance(m, str) else m)


def _top(b) -> float:
    return max((_lv(m[1]) for m in b.marks), default=78.0)


def _family(role: str) -> str:
    return 'horns' if role == 'horns' else 'woodwinds'


def _chords(notes) -> float:
    ons = [round(a, 3) for a, _, _ in notes]
    return sum(1 for i, x in enumerate(ons) if ons.count(x) > 1 and ons.index(x) != i) / max(1, len(ons))


def _mono(notes) -> list:
    """One player: the top note of the notes struck together."""
    by = {}
    for a, d, p in notes:
        k = round(a, 3)
        if k not in by or p > by[k][2]:
            by[k] = (a, d, p)
    return sorted(by.values())


def _doubled(p, others) -> float:
    """The share of p's notes another part sounds at the same onset in the same pitch class (unison / octave)."""
    if not p.notes:
        return 0.0
    best = 0.0
    for x in others:
        ons = {}
        for a, _, q in x.notes:
            ons.setdefault(round(a, 2), set()).add(q % 12)
        hit = sum(1 for a, _, q in p.notes if q % 12 in ons.get(round(a, 2), ()))
        best = max(best, hit / len(p.notes))
    return best


def _secs(notes, tempo: float) -> float:
    return sum(d for _, d, _ in notes) / max(1, len(notes)) * 60.0 / max(1.0, tempo)


def solo_draw(rng, history=()) -> str:
    """One piece's string solo event ('violin' | 'cello' | 'none'): never the same solo as the piece before, never a
    third piece in a row without one (history: the earlier slots' draws, oldest first)."""
    w = dict(SOLO_ON['event']['kinds'] if SOLO is None else SOLO['event']['kinds'])
    hist = [h for h in history if h]
    if hist and hist[-1] != 'none':
        w.pop(hist[-1], None)
    if len(hist) >= 2 and hist[-1] == 'none' and hist[-2] == 'none':
        w.pop('none', None)
    names = sorted(w)
    x = rng.random() * sum(w[n] for n in names)
    for n in names:
        x -= w[n]
        if x <= 0:
            return n
    return names[-1]


def solo_slot(slot: dict, history: list, rng) -> None:
    """composer.set_plan's hook (plan['set_solo']): the slot's string solo event with the set's memory."""
    slot['solo'] = solo_draw(rng, [h.get('solo') for h in history])


def solo_pass(plan_o, score, mat: dict, tune, bpb: float, log: list | None = None) -> list:
    """Round os1 (the module docstring): the parts moved to / added on the solo players. Returns the events
    [{'what', 'role', 'block', 'kind', 'bars'}] (bars: the block's, 1-based)."""
    S = SOLO
    tempo = float(tune.tempo)
    kinds = {b['name']: b['kind'] for b in mat['blocks']}
    blocks = {b.name: b for b in score.blocks}
    events = []
    by_block = {}
    for p in plan_o.parts:
        by_block.setdefault(p.block, []).append(p)

    def roles_in(name):
        return {x.role for x in by_block.get(name, ()) if x.notes}

    def bars(b):
        return (int(b.start // bpb) + 1, int(round(b.end / bpb)))

    def playable(p, solo):
        lo, hi = (note(x) for x in orch.SOLO_RANGE[solo])
        return all(lo <= q <= hi for _, _, q in p.notes) and \
            min(d for _, d, _ in p.notes) * 60.0 / max(1.0, tempo) >= S['fast_s'] - _EPS

    def open_(b, cap, p, solo):
        return not b.peak and _top(b) <= _lv(cap) + _EPS and len(roles_in(b.name)) <= S['tutti'] and \
            p.art in S['arts'] and len(p.notes) >= S['min_notes'] and _chords(p.notes) <= S['chords'] and \
            playable(p, solo) and \
            _doubled(p, [x for x in by_block[b.name] if x is not p and x.role != p.role and x.notes]) <= S['doubled']
    if S.get('polish'):                       # (round op1: the POLISH pass - _polish)
        events = _polish(S, plan_o, score, kinds, blocks, by_block, tune, tempo, roles_in, open_, playable, bars)
        plan_o.notes = sum(len(x.notes) for x in plan_o.parts)
        if log is not None:
            log.extend(events)
        return events
    # ---- 2. the string solo event (first: its block keeps no concertmaster)
    E = S['event']
    want = (getattr(tune, 'arrange', None) or {}).get('solo') or 'none'
    ev_block = None
    if want in E['roles']:
        order = [want] + [k for k in E['roles'] if k != want]
        for kind in order:
            sec, solo = E['roles'][kind]
            cands = []
            for p in plan_o.parts:
                b = blocks.get(p.block)
                if b is None or p.role != sec or p.function != 'melody' or not p.line:
                    continue
                if len(p.notes) < E['min_notes'] or _secs(p.notes, tempo) < E['dur_s'] or \
                        not open_(b, E['cap'], p, solo) or len(roles_in(b.name)) > E['tutti'] or \
                        any(w in (b.texture or '') for w in E['avoid']):
                    continue
                k_ = kinds.get(p.block, '')
                pref = E['prefer'].index(k_) if k_ in E['prefer'] else len(E['prefer'])
                cands.append((pref, -_secs(p.notes, tempo), -len(p.notes), b.start, p))
            if not cands:
                continue
            cands.sort(key=lambda c: c[:4])
            p = cands[0][-1]
            b = blocks[p.block]
            p.role, p.notes = solo, _mono(p.notes)
            gone = [x for x in by_block[b.name] if x is not p and x.function == 'doubling' and x.line and
                    _doubled(x, [p]) >= 0.5]
            for x in gone:
                plan_o.parts.remove(x)
                by_block[b.name].remove(x)
            for x in by_block[b.name]:
                if x is not p and x.role in orch.STRINGS:
                    x.off += E['soft']
            ev_block = b.name
            events.append({'what': 'event', 'role': solo, 'block': b.name, 'kind': kinds.get(b.name, ''),
                           'bars': bars(b), 'drawn': want, 'dropped': [x.role for x in gone]})
            break
    # ---- 1. the wind solos
    for p in list(plan_o.parts):
        solo = S['winds'].get(p.role)
        b = blocks.get(p.block)
        if solo is None or b is None or p.function not in S['fns'] or not p.line or not p.notes:
            continue
        if not open_(b, S['cap'][_family(p.role)], p, solo):
            continue
        events.append({'what': 'wind', 'role': solo, 'block': b.name, 'kind': kinds.get(b.name, ''),
                       'bars': bars(b), 'fn': p.function})
        p.role, p.notes = solo, _mono(p.notes)
    # ---- 3. the concertmaster on the violins I's soft cantilena
    C = S['cm']
    for p in list(plan_o.parts):
        b = blocks.get(p.block)
        if b is None or p.role != 'violins1' or p.function != 'melody' or not p.line or p.block == ev_block:
            continue
        if b.peak or _top(b) > _lv(C['cap']) + _EPS or p.art not in S['arts'] or len(p.notes) < C['min_notes'] or \
                _secs(p.notes, tempo) < C['dur_s'] or not playable(p, 'violin_concertmaster'):
            continue
        plan_o.parts.append(Part('violin_concertmaster', p.block, 'doubling', p.voice, _mono(p.notes), 'sustain',
                                 p.off, False, p.shift, ()))
        events.append({'what': 'concertmaster', 'role': 'violin_concertmaster', 'block': b.name,
                       'kind': kinds.get(b.name, ''), 'bars': bars(b)})
    plan_o.notes = sum(len(x.notes) for x in plan_o.parts)
    if log is not None:
        log.extend(events)
    return events


def _cello_shift(p, lo: int, hi: int, med_rng) -> int | None:
    """The octave shift (-12 / -24) that moves a violins I line into the cello solo's singing register (its median
    inside med_rng, every note inside lo..hi), or None."""
    ps = sorted(q for _, _, q in p.notes)
    for sh in sorted((-12, -24), key=lambda x: abs(ps[len(ps) // 2] + x - sum(med_rng) / 2.0)):
        if med_rng[0] <= ps[len(ps) // 2] + sh <= med_rng[1] and lo <= ps[0] + sh and ps[-1] + sh <= hi:
            return sh
    return None


def _polish(S, plan_o, score, kinds, blocks, by_block, tune, tempo, roles_in, open_, playable, bars) -> list:
    """solo_pass with round op1's POLISH (SOLO_POLISH): the string event first (the cello's theme an octave or two
    down, else its counter-line), then the wind solos and the concertmaster collected per block and kept so that at
    most P['run'] consecutive blocks expose a solo player (the event's block always kept)."""
    P = S['polish']
    E = S['event']
    events = []
    want = (getattr(tune, 'arrange', None) or {}).get('solo') or 'none'
    ev_block = None
    if want in E['roles']:
        order = [want] + [k for k in E['roles'] if k != want]
        for kind in order:
            sec, solo = E['roles'][kind]
            lo, hi = (note(x) for x in orch.SOLO_RANGE[solo])
            cands = []
            for p in plan_o.parts:
                b = blocks.get(p.block)
                if b is None or not p.line or len(p.notes) < E['min_notes'] or \
                        len(roles_in(b.name)) > E['tutti'] or any(w in (b.texture or '') for w in E['avoid']):
                    continue
                src, sh = None, 0
                if p.role == sec and p.function == 'melody':
                    src = 'theme'
                elif kind == 'cello' and p.role == 'violins1' and p.function == 'melody':
                    sh = _cello_shift(p, lo, hi, P['cello_med'])
                    src = 'theme' if sh is not None else None
                elif kind == 'cello' and p.role == 'cellos' and p.function == 'counter':
                    src = 'counter'
                if src is None:
                    continue
                need = E['dur_s'] if src == 'theme' else P['cello_counter_s']
                if _secs(p.notes, tempo) < need:
                    continue
                if sh:                                 # (the range checked on the line as the cello plays it)
                    if b.peak or _top(b) > _lv(E['cap']) + _EPS or p.art not in S['arts'] or \
                            _chords(p.notes) > S['chords'] or \
                            min(d for _, d, _ in p.notes) * 60.0 / max(1.0, tempo) < S['fast_s'] - _EPS:
                        continue
                elif not open_(b, E['cap'], p, solo):
                    continue
                k_ = kinds.get(p.block, '')
                pref = E['prefer'].index(k_) if k_ in E['prefer'] else len(E['prefer'])
                cands.append((0 if src == 'theme' else 1, pref, -_secs(p.notes, tempo), -len(p.notes), b.start,
                              id(p), p, sh, src))
            if not cands:
                continue
            cands.sort(key=lambda c: c[:6])
            *_, p, sh, src = cands[0]
            b = blocks[p.block]
            p.role, p.notes = solo, _mono([(a, d, q + sh) for a, d, q in p.notes])
            gone = [x for x in by_block[b.name] if x is not p and x.function == 'doubling' and x.line and
                    _doubled(x, [p]) >= 0.5]          # (by pitch class: the octave shift keeps it)
            if solo == 'cello_solo':                   # (the section's own line under the solo: out - one cello sings)
                gone += [x for x in by_block[b.name] if x is not p and x.role == 'cellos' and x.line and
                         x.function in ('counter', 'melody', 'doubling') and x not in gone]
            for x in gone:
                plan_o.parts.remove(x)
                by_block[b.name].remove(x)
            for x in by_block[b.name]:
                if x is not p and x.role in orch.STRINGS:
                    x.off += E['soft']
            ev_block = b.name
            events.append({'what': 'event', 'role': solo, 'block': b.name, 'kind': kinds.get(b.name, ''),
                           'bars': bars(b), 'drawn': want, 'dropped': [x.role for x in gone], 'src': src,
                           **({'shift': sh} if sh else {})})
            break
    # the wind solos and the concertmaster: collected per block
    want_w, want_c = {}, {}
    for p in plan_o.parts:
        solo = S['winds'].get(p.role)
        b = blocks.get(p.block)
        if solo is None or b is None or p.function not in S['fns'] or not p.line or not p.notes:
            continue
        if open_(b, S['cap'][_family(p.role)], p, solo):
            want_w.setdefault(b.name, []).append((p, solo))
    C = S['cm']
    for p in plan_o.parts:
        b = blocks.get(p.block)
        if b is None or p.role != 'violins1' or p.function != 'melody' or not p.line or p.block == ev_block:
            continue
        if b.peak or _top(b) > _lv(C['cap']) + _EPS or p.art not in S['arts'] or len(p.notes) < C['min_notes'] or \
                _secs(p.notes, tempo) < C['dur_s'] or not playable(p, 'violin_concertmaster'):
            continue
        want_c.setdefault(b.name, []).append(p)
    # no parade: at most P['run'] solo blocks in a row (the event's block kept: the drop pattern's phase moved)
    names = [b.name for b in score.blocks]
    solo_b = [n for n in names if n == ev_block or n in want_w or n in want_c]
    drop, run = set(), []
    for n in names + [None]:
        if n is not None and n in solo_b:
            run.append(n)
            continue
        if len(run) > P['run']:
            per = P['run'] + 1
            phase = next((ph for ph in range(per) if not any(
                (i - ph) % per == P['run'] and x == ev_block for i, x in enumerate(run))), 0)
            drop |= {x for i, x in enumerate(run) if (i - phase) % per == P['run'] and x != ev_block}
        run = []
    for p in plan_o.parts:
        for q, solo in want_w.get(p.block, ()):
            if q is p and p.block not in drop:
                b = blocks[p.block]
                events.append({'what': 'wind', 'role': solo, 'block': b.name, 'kind': kinds.get(b.name, ''),
                               'bars': bars(b), 'fn': p.function})
                p.role, p.notes = solo, _mono(p.notes)
    for p in list(plan_o.parts):
        if p in want_c.get(p.block, ()) and p.block not in drop:
            b = blocks[p.block]
            plan_o.parts.append(Part('violin_concertmaster', p.block, 'doubling', p.voice, _mono(p.notes), 'sustain',
                                     p.off, False, p.shift, ()))
            events.append({'what': 'concertmaster', 'role': 'violin_concertmaster', 'block': b.name,
                           'kind': kinds.get(b.name, ''), 'bars': bars(b)})
    for n in sorted(drop, key=names.index):
        events.append({'what': 'section', 'block': n, 'kind': kinds.get(n, ''), 'bars': bars(blocks[n])})
    return events


def polish_band(band) -> None:
    """Round op1 (SOLO['polish']): the concertmaster's fader up by P['cm_db'] (symphony.build_symphony's hook)."""
    P = (SOLO or {}).get('polish')
    if P and 'violin_concertmaster' in band.roles:
        band['violin_concertmaster'].gain_db += P['cm_db']


def solo_stats(song) -> dict:
    """Where the solo players play: {'events': song.solo_events, 'notes': {solo role: notes}, 'share': solo notes /
    all line notes}."""
    po = getattr(song, 'orchestration', None)
    ev = list(getattr(song, 'solo_events', None) or [])
    notes, lines = {}, 0
    for p in (po.parts if po else ()):
        if p.role in orch.SOLOS:
            notes[p.role] = notes.get(p.role, 0) + len(p.notes)
        if p.line:
            lines += len(p.notes)
    return {'events': ev, 'notes': notes, 'share': round(sum(notes.values()) / max(1, lines), 3)}
