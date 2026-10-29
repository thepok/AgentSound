"""Endless orchestra-symphonic COLOUR (round ox1; HUMAN_FEEDBACK 2026-10-25: "what I miss in the orchestra are more
exotic instruments like a church organ or an acoustic guitar - that can be beautiful too", "above all increase
diversity"): per piece one GUEST colour the piece is BUILT around - idiomatically, as a few events of its form, never a
token cameo - drawn with the set's memory.

  organ        the real pipe organs (Lars Palo's Burea / Pitea, church_organ seated in the orchestra's hall): an
               organ prelude / interlude alone on soft flues with a solo stop and the soft pedal, the swell box
               opening under the build (the swell's chorus + pedal), the cathedral summit (the principal chorus with
               mixture and trumpet - full organ - and the 16' pedal reed under / with the orchestra, the climax's line
               as the chorale's soprano) and the amen (the last chord on full organ, or soft flues for a dying end)
  guitar       the classical (nylon) guitar's serenade: a quiet block in its texture - fingerpicked arpeggios on
               playable open / barre shapes (guitarist.arpeggio) under a solo wind, then the guitar takes the tune
               itself (melody + thumb bass), the strings plucked and thinned, brass / percussion / harp out; an
               opening for the guitar alone; the envoi (the soft ending's arpeggios and the final chord let ring)
  harpsichord  the baroque colour: a concertino block (the harpsichord's 16th figuration - organ_vocab.toccata's
               figures - under the tune, the orchestra reduced to its strings), the continuo (chords on the beats
               over the bass line) under the fugato / the first theme, the final chord rolled; 8' for the soli, 8'
               + 4' for the tutti
  celesta      the "magic" colour: the theme doubled high on the celesta in its quiet / dancing statements, the
               glockenspiel on the loud return / summit's line, a twinkling arpeggio into a quiet block or the end
  bells        tubular bells: the summit's downbeats rung on the line's notes, the coda's peal (rounds down the
               scale) or a tolling tonic dying away

A guest also shapes its piece's arrangement in the set plan (guest_slot): the guitar and the harpsichord pieces take
the chamber orchestra where the mood has it (lighter scoring: the guitar is heard), the guitar pieces a calmer tempo
inside the feel's range, the organ the full orchestra; the feel decides the guest (FEELS: the guitar in the andante /
river nocturnes, the harpsichord in the allegros, the celesta in the scherzos).

Everything is written with the shared primitives: choir._line / _mono / _clip / _skeleton / _chords / _voice (the
block's singable line, the chart's segments, voicing.voice), guitarist.arpeggio / let_ring (the fretboard's shapes,
p-i-m-a), organ_vocab.slots_from_chart / toccata (the harpsichord's figuration), orch.church_organ + orch.swell (the
registrations, the swell pedal 'instrument.expression'), orch.guests (the guest band seated in the orchestra's hall)
and orch.Score (the piece's own dynamics map: the guests' velocities follow it). The orchestra is thinned where the
guest needs the room (_edit: notes dropped / softened / plucked / moved to another role).
COLOUR None = off (bit-identical); genres.symphony_colour switches it with the set draw (plan['set_guest']).
Stats: colour_stats(song)."""
from __future__ import annotations

import dataclasses
import math
import random

from ..theory import ComposeError, Key, chord

COLOUR = None
COLOUR_ON = {'none': 0.3, 'cap': 4, 'memory2': 0.35, 'gain': 0.0, 'organ_gain': -1.5, 'organ_send': -14.0,
             'organ_db': {'soft': 8.0, 'flute': 8.0, 'cornet': 7.0, 'reed': 7.0, 'pedal_soft': 6.0}, 'acc_db': -5.0,
             'wind_db': 3.0,
             'guitar_tempo': 0.3, 'swell': (0.12, 1.0), 'soft_swell': (0.5, 0.85), 'inter_bars': (4, 8),
             'thin_db': -7.0, 'pizz_db': -3.0, 'pad_db': -10.0, 'rel': 0.5}
"""COLOUR on: the 'none' draw's weight; the most pieces one guest gets per set slot count (a set of n: ceil(n /
cap)); the weight for the guest two slots back; dB on every guest (over the band's 'gain'); the organ's extra dB and
its send into the orchestra's hall, the soft registrations' extra dB (the prelude / interlude alone: heard), the
guitar's arpeggio under the serenade's solo wind (dB), the solo wind's lift (dB); the guitar piece's tempo (0..1 in the feel's range: its highest); the swell box's
opening under the build (from, to) and the soft flues' breathing (closed, open); the organ interlude's bars (least,
most); the orchestra thinned under a guest (dB), the plucked bass's dB, the string pad's dB under the guitar's own
tune; the guests' accent scale (their figure's velocity pattern around the dynamics map)."""

COLOUR_POLISH = {'gap': 0.3, 'returns': 2, 'apart': 0.1, 'db': {'celesta': 2.5, 'glockenspiel': 1.5, 'guitar': 2.0},
                 'keep_size': ('guitar',), 'return_bars': 8,
                 'gestures': {'celesta': ('rise', 'fall', 'wave', 'chime'),
                              'bells': ('scale', 'rounds', 'motto', 'toll'),
                              'harpsichord': ('rolled', 'flourish', 'with', 'broken')},
                 'returns_of': {'organ': 'solo', 'guitar': 'reprise', 'harpsichord': 'continuo', 'celesta': 'sparkle',
                                'bells': 'hint'},
                 'codas': {'organ': ('amen',), 'guitar': ('envoi', 'farewell'), 'harpsichord': ('cadence',),
                           'celesta': ('twinkle',), 'bells': ('toll',)},
                 'prefer': ('dev_dialogue', 'dev_fugato', 'recap2', 't2b', 'var', 'episode', 'refrain', 'trio',
                            'river', 't2', 'recap', 't1b', 'trans', 'close', 'mid', 'mid2')}
"""Round op1's POLISH (COLOUR['polish'], genres.symphony_polish; ox1's judges: "the celesta disappears for 94 bars",
"the guitar is absent from the development, climax and coda", "the bells are not foreshadowed", the same gestures
twice a set): a stretch of more than 'gap' of the piece without the guest gets a RETURN ('returns_of': the organ's
solo stop on the tune, the guitar's own tune, the continuo, the celesta's doubled theme, a distant bell; at most
'returns', at most 'return_bars' plan bars, at least 'apart' of the piece from the guest's other events, in the
development / recap first - 'prefer'), the coda always has the guest
('codas': the guitar's envoi, or over a loud coda its farewell before the last tutti), the bells hint before the
climax (a 'hint' first), each guest's signature gesture drawn per piece with the set's memory ('gestures': the
celesta's closing arpeggio, the bells' coda peal, the harpsichord's last chord - never the variant the colour's
earlier pieces in the set used while one is left), the guitar piece keeps its drawn orchestra ('keep_size': its
climax has the brass), and the celesta / glockenspiel / guitar louder ('db': less cameo)."""

GUESTS = {
    'organ': {'w': 1.1, 'size': 'full',
              'plans': {'cathedral': (('opening', 'interlude'), 'swell', 'summit', 'amen'),
                        'chorale': ('swell', 'summit', 'amen'),
                        'voluntary': (('opening', 'interlude'), 'summit', 'amen')}},
    'guitar': {'w': 1.25, 'size': 'chamber', 'tempo': True,
               'plans': {'serenade': ('opening', 'serenade', ('envoi', 'serenade')),
                         'nocturne': ('serenade', 'serenade', ('envoi', 'opening'))}},
    'harpsichord': {'w': 0.9, 'size': 'chamber',
                    'plans': {'grosso': ('concertino', 'continuo', 'cadence'),
                              'continuo': ('continuo', 'concertino', 'continuo', 'cadence')}},
    'celesta': {'w': 0.9,
                'plans': {'magic': ('sparkle', 'sparkle', 'twinkle'),
                          'glitter': ('sparkle', 'glitter', 'twinkle')}},
    'bells': {'w': 1.0, 'plans': {'peal': ('peal', 'toll'), 'toll': ('peal_soft', 'toll')}},
}
"""The guests: the draw's weight, the orchestra size its piece takes (where the mood has it), whether its piece takes
the calmer tempo, its plans (the events in order; a tuple: the first alternative that finds a place)."""
FEELS = {'organ': {'andante': 1.3, 'allegro': 1.2, 'river': 0.9, 'vivace': 0.6, 'scherzo': 0.2},
         'guitar': {'andante': 1.7, 'river': 1.5, 'vivace': 0.5, 'allegro': 0.15, 'scherzo': 0.0},
         'harpsichord': {'allegro': 1.5, 'vivace': 1.1, 'andante': 0.6, 'river': 0.3, 'scherzo': 0.0},
         'celesta': {'scherzo': 2.0, 'vivace': 1.2, 'river': 0.8, 'andante': 0.6, 'allegro': 0.4},
         'bells': {'allegro': 1.0, 'andante': 0.9, 'river': 0.8, 'vivace': 0.6, 'scherzo': 0.5}}
"""The feels' affinity per guest (x its weight)."""
PACKS = {'organ': ('lars-palo-burea-church', 'lars-palo-pitea-mhs'), 'guitar': ('freepats-spanish-classical-guitar',),
         'harpsichord': ('vcsl',), 'celesta': ('sso', 'vcsl'), 'bells': ('vcsl',)}
"""The packs a guest needs (organ: one of the two; the rest: all)."""
ORGANS = {'burea': 'lars-palo-burea-church', 'pitea': 'lars-palo-pitea-mhs'}
ORGAN_SOLO = ('cornet', 'flute', 'reed')
"""The organ prelude's solo stops (each on another division than the soft flues' Svallverk)."""
ORGAN_VOICES = {'S': (60, 81, 71), 'A': (55, 76, 65), 'T': (48, 69, 58), 'B': (36, 55, 43)}
"""The organ chorale's voices (voicing.voice): S A T on the manual, B in the pedal."""
SOFT_VOICES = {'A': (55, 74, 64), 'T': (50, 67, 58), 'B': (36, 52, 43)}
HARPSI_RH = {'h1': (62, 79, 70), 'h2': (57, 74, 65), 'h3': (53, 69, 60)}
"""The harpsichord continuo's right hand (3 voices)."""
FIGURES = ('broken_up', 'wave', 'zigzag', 'widor')
"""The harpsichord concertino's figures (organ_vocab.TOCCATA_FIGURES)."""
GTR_PATTERNS = {'duple': {'arp_pima': 1.0, 'arp_ballad': 0.8, 'arp_up': 0.6},
                'compound': {('1/8', 'B 3 2 1 2 3'): 1.0, ('1/8', 'B 2 3 1 3 2'): 0.8, ('1/8', 'B 3 1 3 2 3'): 0.6}}
"""The guitar's fingerpicking patterns per metre family (guitarist PATTERNS names, or (grid, steps))."""
QUIET = ('t2', 'trio', 'river', 'recap2', 't2b', 'source', 'mist', 'slow', 'solo', 'var', 'coda_soft')
"""The blocks a soft guest event may take (best first)."""
OPENINGS = ('mist', 'source', 'slow', 'solo', 'intro', 'river', 't1')
STRINGS = ('violins1', 'violins2', 'violas', 'cellos', 'basses')
WINDS = ('flutes', 'oboes', 'clarinets', 'bassoons')
LOUD_ROLES = ('horns', 'trumpets', 'trombones', 'low_brass', 'tuba', 'timpani', 'percussion', 'choir', 'drums')
_EPS = 1e-6


# ------------------------------------------------------------------------------------------------ the draw

def available(name: str) -> bool:
    from ..bandlib.orchestra import installed
    if name == 'organ':
        return any(installed(p) for p in PACKS['organ'])
    return all(installed(p) for p in PACKS.get(name, ()))


def guest_draw(feel: str, rng, history=(), n: int = 8) -> dict:
    """One piece's guest: {'colour': name | 'none', 'plan': its plan, 'organ': burea / pitea, 'seed'} - weighted by
    the feel (GUESTS x FEELS), never the slot before's colour (nor 'none' twice in a row), a colour at most
    ceil(n / COLOUR['cap']) times in the set, the one two back x COLOUR['memory2'] (history: the earlier slots'
    guests, oldest first), a plan not the colour's last one."""
    C = COLOUR or COLOUR_ON
    hist = [h for h in history if isinstance(h, dict)]
    last = hist[-1]['colour'] if hist else None
    back2 = hist[-2]['colour'] if len(hist) > 1 else None
    cap = max(1, int(math.ceil(max(n, len(hist) + 1) / float(C['cap']) - 1e-9)))
    count = {}
    for h in hist:
        count[h['colour']] = count.get(h['colour'], 0) + 1
    w = {}
    for name, G in GUESTS.items():
        v = G['w'] * FEELS[name].get(feel, 0.5)
        if v <= 0 or name == last or count.get(name, 0) >= cap or not available(name):
            continue
        w[name] = v * (C['memory2'] if name == back2 else 1.0)
    if last != 'none':
        w['none'] = C['none'] * (C['memory2'] if back2 == 'none' else 1.0)
    if not w:
        w = {'none': 1.0}
    keys = {x: rng.random() ** (1.0 / v) for x, v in sorted(w.items())}
    name = max(sorted(keys), key=lambda x: keys[x])
    out = {'colour': name, 'seed': rng.randrange(1 << 30)}
    if name != 'none':
        plans = sorted(GUESTS[name]['plans'])
        used = [h.get('plan') for h in hist if h['colour'] == name]
        pick = [p for p in plans if not used or p != used[-1]] or plans
        out['plan'] = pick[rng.randrange(len(pick))]
        if name == 'organ':
            orgs = [o for o in sorted(ORGANS) if available_organ(o)]
            prev = [h.get('organ') for h in hist if h['colour'] == 'organ']
            orgs = [o for o in orgs if not prev or o != prev[-1]] or orgs
            out['organ'] = orgs[rng.randrange(len(orgs))]
        P = (COLOUR or {}).get('polish')
        if P and name in P['gestures']:      # (round op1: the signature gesture with the set's memory)
            vs = P['gestures'][name]
            used_g = [h.get('gest') for h in hist if h['colour'] == name and h.get('gest')]
            pick = [v for v in vs if v not in used_g] or [v for v in vs if not used_g or v != used_g[-1]] or list(vs)
            out['gest'] = pick[rng.randrange(len(pick))]
    return out


def available_organ(o: str) -> bool:
    from ..bandlib.orchestra import installed
    return installed(ORGANS[o])


def guest_slot(genre, slot: dict, history: list, n: int, rng) -> None:
    """composer.set_plan's hook (plan['set_guest'], round ox1): the slot's guest (guest_draw with the set's memory)
    and the arrangement it asks for - the orchestra's size (the guitar / harpsichord pieces chamber, the organ full,
    where the mood has it) and the guitar's calmer tempo. Own dice: master's draws unchanged."""
    g = guest_draw(slot['feel'], rng, [x.get('guest') for x in history], n)
    slot['guest'] = g
    G = GUESTS.get(g['colour'])
    if not G:
        return
    sizes = genre.moods[slot['mood']].get('size') or {}
    keep = g['colour'] in ((COLOUR or {}).get('polish') or {}).get('keep_size', ())
    if keep and sizes.get('full', 0) > 0:     # (round op1: the guitar piece's climax keeps its trumpets / trombones)
        slot['size'] = 'full'
    elif G.get('size') and sizes.get(G['size'], 0) > 0 and not keep:
        slot['size'] = G['size']
    if G.get('tempo') and slot.get('tempo'):
        lo, hi = genre.feels[slot['feel']]['tempo']
        top = int(round(lo + (COLOUR or COLOUR_ON)['guitar_tempo'] * (hi - lo)))
        slot['tempo'] = min(int(slot['tempo']), top)


# ------------------------------------------------------------------------------------------------ the orchestra's room

def _edit(plan_o, a: float, z: float, rule) -> int:
    """The orchestra in [a, z) changed part by part: rule(part) -> None (kept), 'drop' (its notes there removed - one
    held into a cut there) or {'off': dB, 'art': name, 'role': name} (its notes there as a new part so). -> notes
    changed."""
    changed = 0
    extra = []
    for p in plan_o.parts:
        act = rule(p)
        if act is None:
            continue
        inside = [n for n in p.notes if a - _EPS <= n[0] < z - _EPS]
        held = [n for n in p.notes if n[0] < a - _EPS and n[0] + n[1] > a + 0.05]
        if not inside and not (held and act == 'drop'):
            continue
        rest = [n for n in p.notes if not (a - _EPS <= n[0] < z - _EPS)]
        if act == 'drop':
            out = []
            for st, du, q in rest:
                if st < a - _EPS and st + du > a + 0.05:
                    if a - 0.05 - st > 0.1:
                        out.append((st, a - 0.05 - st, q))
                    changed += 1
                else:
                    out.append((st, du, q))
            p.notes = out
            changed += len(inside)
            continue
        p.notes = rest
        extra.append(dataclasses.replace(p, role=act.get('role', p.role), notes=inside,
                                         off=p.off + act.get('off', 0.0), art=act.get('art', p.art),
                                         line=act.get('line', p.line)))
        changed += len(inside)
    plan_o.parts.extend(extra)
    plan_o.parts[:] = [p for p in plan_o.parts if p.notes]
    plan_o.notes = sum(len(p.notes) for p in plan_o.parts)
    return changed


def _melody_parts(plan_o, block: str):
    return [p for p in plan_o.parts if p.block == block and p.function == 'melody' and p.notes]


# ------------------------------------------------------------------------------------------------ helpers

def _bar(mat, k):
    return mat['U'] * k


def _line(plan_o, b, a, z, tune, fns=('melody',)):
    """The block's tune in [a, z): its melody part(s) (the top note per onset), else choir._line's singable line."""
    from .choir import _clip, _line as cline, _mono
    ns = [n for p in plan_o.parts if p.block == b.name and p.function in fns and p.notes for n in p.notes]
    ns = _mono(_clip(ns, a, z))
    if len(ns) >= 3:
        return ns
    return cline(plan_o, b, a, z, tune)[2]


def _fold(ns, lo: int, hi: int, centre: float) -> list:
    """The line moved by octaves to centre its median, every note then folded into lo..hi."""
    if not ns:
        return []
    ps = sorted(p for _, _, p in ns)
    med = ps[len(ps) // 2]
    sh = min(range(-48, 49, 12), key=lambda x: (abs(med + x - centre), -x))
    out = []
    for st, du, p in ns:
        q = p + sh
        while q > hi:
            q -= 12
        while q < lo:
            q += 12
        out.append((st, du, q))
    return out


def _rows(blocks, a, z, gmin=1.0):
    from .choir import _chords
    return _chords([(st, du, sym) for x in blocks for st, du, sym in x.chart], a, z, gmin)


def _segs(rows, sop, a, z):
    """The chart's chords cut at every soprano onset: [(t0, t1, symbol, soprano pitch | None)]; a soprano rest drops
    the segment."""
    cuts = {round(r[0], 4) for r in rows} | {round(r[1], 4) for r in rows}
    for st, du, _ in sop:
        cuts.add(round(st, 4))
        cuts.add(round(st + du, 4))
    ts = sorted(x for x in cuts if a - _EPS <= x <= z + _EPS)
    out = []
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
                continue
        out.append((t0, t1, sym, s_p))
    return out


def _chorale(rows, sop, a, z, key, voices) -> dict:
    """Voice-led chords (voicing.voice through choir._voice) over the chart, the soprano fixed to `sop` where given:
    {voice: [(start, dur, pitch)]}, a voice's repeated pitch tied (legato)."""
    from .choir import _voice
    segs = _segs(rows, sop, a, z)
    top = next(iter(voices))
    steps = [{'chord': sym, 'fixed': {top: s_p} if s_p is not None else {}} for _, _, sym, s_p in segs]
    voiced = _voice(steps, key, voices)
    out = {v: [] for v in voices}
    for (t0, t1, _, _), vc in zip(segs, voiced):
        if not vc:
            continue
        for v, p in vc.items():
            ns = out[v]
            if ns and abs(ns[-1][0] + ns[-1][1] - t0) < 1e-4 and ns[-1][2] == p:
                ns[-1] = (ns[-1][0], t1 - ns[-1][0], p)
            else:
                ns.append((t0, t1 - t0, p))
    return {v: ns for v, ns in out.items() if ns}


def _bass_pc(sym: str) -> int:
    c = chord(sym)
    return (c.bass if c.bass is not None else c.root) % 12


def _simple(sym: str) -> str:
    """A chord the fretboard surely has: the root triad (minor / diminished / major) of a symbol."""
    c = chord(sym)
    iv = set(c.intervals)
    q = 'dim' if (3 in iv and 6 in iv) else 'm' if 3 in iv else ''
    return f"{c.root_name}{q}"


# ------------------------------------------------------------------------------------------------ placing

def _blocks(mat, score):
    return list(zip(mat['blocks'], score.blocks))


def _free(taken, a, z):
    return all(z <= x0 + _EPS or a >= x1 - _EPS for x0, x1 in taken)


def _quiet(x, b) -> bool:
    from .symphony import _vmax
    from ..bandlib.scoring import VEL
    return not x['peak'] and _vmax(b) <= VEL['mf']


def _places(ev: str, mat, score, tune, k, taken, plan_o) -> list:
    """Where an event goes -> [(block, a, z, extra)] (song beats), best first; [] when the piece has no place."""
    from .symphony import _vmax
    from ..bandlib.scoring import VEL
    C = COLOUR or COLOUR_ON
    bl = _blocks(mat, score)
    bar = _bar(mat, k)
    ip = next((i for i, (x, _) in enumerate(bl) if x['peak']), None)
    out = []
    kinds = [x['kind'] for x, _ in bl]
    if ev == 'opening':
        x, b = bl[0]
        if x['kind'] in OPENINGS and (x['kind'] != 'intro' or _vmax(b) <= VEL['mf']) and not x['peak'] \
                and b.length >= 2 * bar - _EPS and _free(taken, b.start, b.end):
            if x['kind'] in ('t1', 'river') and b.length > 8 * bar + _EPS:
                return [(b, b.start, b.start + 8 * bar, {'first': True})]
            return [(b, b.start, b.end, {'first': True})]
        return []
    if ev in ('interlude', 'serenade', 'concertino', 'sparkle'):
        order = QUIET if ev != 'concertino' else ('t2', 'trio', 'episode', 'var', 'refrain', 't1', 'river', 't2b',
                                                    'recap2', 'close')
        if ev == 'sparkle':
            order = ('t1', 'trio', 't2', 'river', 'refrain', 'recap2', 't2b', 'var', 'source', 'episode', 'coda_soft')
        for kd in order:
            for i, (x, b) in enumerate(bl):
                if x['kind'] != kd or x['peak'] or b.length < 4 * bar - _EPS:
                    continue
                if ev in ('serenade', 'interlude') and not _quiet(x, b):
                    continue
                if ev == 'sparkle' and _vmax(b) > VEL['f']:
                    continue
                if ev == 'interlude':
                    lo, hi = C['inter_bars']
                    nb = int(round(b.length / bar))
                    m = max(lo, min(hi, nb // 2))
                    if nb - m < 2:
                        continue
                    a, z = b.start, b.start + m * bar
                elif ev == 'concertino' and b.length > 12 * bar + _EPS:
                    a, z = b.start, b.start + 12 * bar
                else:
                    a, z = b.start, b.end
                if _free(taken, a, z) and (ev not in ('serenade', 'sparkle') or _line(plan_o, b, a, z, tune)):
                    out.append((b, a, z, {}))
        return out
    if ev == 'glitter':
        cands = [i for i, (x, b) in enumerate(bl) if x['peak']] + \
            [i for i, (x, b) in enumerate(bl) if x['kind'] in ('recap', 'coda', 'close', 't1b') and not x['peak']]
        for i in cands:
            b = bl[i][1]
            z = min(b.end, b.start + 8 * bar)
            if _free(taken, b.start, z) and _line(plan_o, b, b.start, z, tune):
                out.append((b, b.start, z, {}))
        return out
    if ev == 'swell' and ip is not None and ip > 0:
        b = bl[ip - 1][1]
        n = int(round(b.length / bar))
        m = min(n, 8 if n >= 8 else max(2, n))
        a = b.end - m * bar
        if m >= 2 and _free(taken, a, b.end):
            return [(b, a, b.end, {})]
        return []
    if ev == 'summit' and ip is not None:
        b = bl[ip][1]
        return [(b, b.start, b.end, {'quiet': mat.get('climax') == 'quiet'})] if _free(taken, b.start, b.end) else []
    if ev == 'hint' and ip is not None and ip > 0:          # (round op1: the build's distant bell)
        x, b = bl[ip - 1]
        z = min(b.end, b.start + 4 * bar)
        if not x['peak'] and z - b.start >= 2 * bar - _EPS and _free(taken, b.start, z):
            return [(b, b.start, z, {})]
        return []
    if ev in ('peal', 'peal_soft') and ip is not None:
        b = bl[ip][1]
        z = min(b.end, b.start + 8 * bar)
        return [(b, b.start, z, {'soft': ev == 'peal_soft'})] if _free(taken, b.start, z) else []
    if ev == 'continuo':
        order = ('dev_fugato', 't1', 'recap', 'refrain', 'close', 'episode', 'trans', 't1b', 'var')
        for kd in order:
            for i, (x, b) in enumerate(bl):
                if x['kind'] != kd or b.length < 4 * bar - _EPS:
                    continue
                z = min(b.end, b.start + 16 * bar)
                if _free(taken, b.start, z):
                    out.append((b, b.start, z, {'tutti': _vmax(b) >= VEL['f']}))
        return out
    if ev in ('amen', 'envoi', 'cadence', 'toll', 'twinkle'):
        ends = [i for i, kd in enumerate(kinds) if kd in ('coda', 'coda_soft', 'end', 'end_soft')]
        if not ends:
            return []
        i0 = ends[0]
        x, b = bl[i0]
        last = bl[-1][1]
        soft = any(bl[i][0]['kind'] in ('coda_soft', 'end_soft') for i in ends) or \
            str((tune.arrange or {}).get('coda')) == 'dissolve'
        if ev == 'envoi' and not soft:
            return []
        if ev == 'cadence':
            a = max(b.start, last.end - 2 * bar)
            return [(last, a, last.end, {'soft': soft})] if _free(taken, a, last.end) else []
        if ev == 'twinkle':
            for i, (x2, b2) in enumerate(bl):
                if i and _quiet(x2, b2) and not _quiet(*bl[i - 1]) and _free(taken, b2.start, b2.start + bar):
                    out.append((b2, b2.start, b2.start + bar, {'soft': True}))
            out.append((last, max(last.start, last.end - bar), last.end, {'soft': soft, 'last': True}))
            return [c for c in out if _free(taken, c[1], c[2])][-1:] + [c for c in out if _free(taken, c[1], c[2])][:-1]
        a = b.start
        if ev == 'amen' and not soft and b.length > 6 * bar + _EPS:
            a = b.end - 4 * bar
        if ev == 'toll' and b.length > 8 * bar + _EPS:
            a = b.end - 8 * bar
        return [(b, a, last.end, {'soft': soft})] if _free(taken, a, last.end) else []
    return out


# ------------------------------------------------------------------------------------------------ writing: the organ

def _organ(ev, b, blocks, a, z, tune, plan_o, rng, solo) -> dict:
    """{role: [(start, dur, pitch, rel)]} + 'swell' points of an organ event."""
    from .choir import _skeleton
    rows = _rows(blocks, a, z)
    key = b.key
    out = {}
    if ev['event'] in ('opening', 'interlude'):
        line = _skeleton(_fold(_line(plan_o, b, a, z, tune, ('melody', 'voice', 'counter')), 60, 81, 70), tune)
        ch = _chorale(rows, [], a, z, key, SOFT_VOICES)
        if line:
            top = max(p for _, _, p in line)
            ch = {v: [(st, du, p) for st, du, p in ns if p < top] or ns for v, ns in ch.items()}
            out[solo] = line
        out['soft'] = ch.get('A', []) + ch.get('T', [])
        out['pedal_soft'] = ch.get('B', [])
        ev['swell'] = {'soft': 'breathe'}
        ev['thin'] = 'all'
        ev['solo'] = solo if line else None
        return out
    if ev['event'] == 'solo':                  # (round op1's return: the tune on the solo stop, soft flues under it)
        line = _skeleton(_fold(_line(plan_o, b, a, z, tune), 60, 81, 70), tune)
        if len(line) < 3:
            return {}
        ch = _chorale(rows, [], a, z, key, SOFT_VOICES)
        top = max(p for _, _, p in line)
        out[solo] = line
        out['soft'] = [n for v in ('A', 'T') for n in ch.get(v, []) if n[2] < top]
        ev['swell'] = {'soft': 'breathe'}
        ev['thin'] = 'hand'
        ev['solo'] = solo
        return out
    if ev['event'] == 'swell':
        ch = _chorale(rows, [], a, z, key, {'S': (62, 79, 70), 'A': (55, 74, 65), 'T': (50, 67, 58),
                                             'B': (36, 52, 43)})
        out['swell_full'] = [n for v in ('S', 'A', 'T') for n in ch.get(v, [])]
        out['pedal'] = ch.get('B', [])
        ev['swell'] = {'swell_full': 'open'}
        return out
    if ev['event'] in ('summit', 'amen'):
        soft = ev.get('soft') or ev.get('quiet')
        line = _skeleton(_fold(_line(plan_o, b, a, z, tune), 60, 81, 72), tune) if not soft else []
        ch = _chorale(rows, line, a, z, key, ORGAN_VOICES)
        man, ped = ('soft', 'pedal_soft') if ev.get('soft') else ('principal', 'pedal') if ev.get('quiet') else \
            ('full', 'pedal_full')
        out[man] = [n for v in ('S', 'A', 'T') for n in ch.get(v, [])]
        out[ped] = ch.get('B', [])
        if ev['event'] == 'amen' and out[man]:
            end = max(st + du for st, du, _ in out[man])          # (the last chord held into the church's ring)
            out[man] = [(st, du + (1.0 if abs(st + du - end) < 1e-4 else 0.0), p) for st, du, p in out[man]]
            out[ped] = [(st, du + (1.0 if abs(st + du - end) < 1e-4 else 0.0), p) for st, du, p in out[ped]]
        if man == 'soft':
            ev['swell'] = {'soft': 'breathe'}
        return out
    return out


# ------------------------------------------------------------------------------------------------ writing: the guitar

def _gtr_arp(rows, tune, meter_fam: str, rng) -> list:
    """guitarist.arpeggio over the rows (fingerstyle, a drawn pattern): [(start, dur, pitch, rel)]."""
    from .. import guitarist as gtr
    from ..theory import Progression
    from .composer import _pick
    if not rows:
        return []
    a = rows[0][0]
    pat = _pick(rng, GTR_PATTERNS[meter_fam])
    seq = [(sym, (z - st) / 4.0) for st, z, sym in rows]
    for simple in (False, True):
        try:
            prog = Progression([(_simple(s) if simple else s, d) for s, d in seq], key=None)
            c = gtr.arpeggio(prog, float(tune.tempo), pattern=pat, hand='fingerstyle', seed=rng.randrange(1 << 20))
            break
        except ComposeError:
            c = None
    if c is None:
        return []
    C = COLOUR or COLOUR_ON
    return [(n.start + a, n.dur, n.pitch, (n.vel - 70) * C['rel']) for n in c]


def _gtr_melody(line, rows, a, z, tune) -> list:
    """The guitar's own tune: the line (E3-A5, centred on F#4 / G4: the guitar's singing register), the thumb's bass
    at every chord change (E2-E3, ringing to the next), an inner chord tone under a long melody note."""
    mel = _fold(line, 52, 81, 67)
    out = [(st, du, p, 6.0) for st, du, p in mel]
    prev = 45
    for i, (st, zz, sym) in enumerate(rows):
        pc = _bass_pc(sym)
        cands = [p for p in range(40, 53) if p % 12 == pc]
        q = min(cands, key=lambda x: (abs(x - prev), x))
        prev = q
        out.append((st, max(0.5, zz - st), q, 2.0))
        c = chord(sym)
        for st2, du2, p2 in mel:
            if st - _EPS <= st2 < zz - _EPS and du2 >= 1.5 - _EPS:
                inner = [x for x in range(q + 7, p2 - 2) if x % 12 in c.pcs and 50 <= x <= 66]
                if inner:
                    out.append((st2 + min(1.0, du2 / 2), du2 - min(1.0, du2 / 2), inner[-1], -8.0))
    return sorted(out)


def _guitar(ev, b, blocks, a, z, tune, plan_o, rng, fam) -> dict:
    rows = _rows(blocks, a, z)
    line = _line(plan_o, b, a, z, tune)
    bar = ev['bar']
    out = {'guitar': []}
    if ev['event'] == 'opening':
        if line and len(line) >= 4:
            out['guitar'] = _gtr_melody(line, rows, a, z, tune)
            ev['mode'] = 'tune'
        else:
            out['guitar'] = _gtr_arp(rows, tune, fam, rng)
            ev['mode'] = 'arpeggio'
        ev['thin'] = 'all'
        return out
    if ev['event'] == 'serenade':
        nb = int(round((z - a) / bar))
        split = a + (nb // 2) * bar if nb >= 8 else z
        ev['split'] = split
        acc = (COLOUR or COLOUR_ON)['acc_db'] if ev.get('wind') else 0.0      # (under the solo wind: an accompaniment)
        out['guitar'] = [(st, du, p, r_ + acc) for st, du, p, r_ in _gtr_arp(_rows(blocks, a, split), tune, fam, rng)]
        if split < z - _EPS:
            out['guitar'] += _gtr_melody(_line(plan_o, b, split, z, tune), _rows(blocks, split, z), split, z, tune)
        ev['thin'] = 'serenade'
        ev['mode'] = 'arpeggio + tune' if split < z - _EPS else 'arpeggio'
        return out
    if ev['event'] == 'reprise':               # (round op1's return: the guitar's own tune, the strings a pad)
        if line and len(line) >= 4:
            out['guitar'] = _gtr_melody(line, rows, a, z, tune)
            ev['split'] = a
            ev['thin'] = 'serenade'
            ev['mode'] = 'tune'
        else:
            out['guitar'] = _gtr_arp(rows, tune, fam, rng)
            ev['thin'] = 'soft'
            ev['mode'] = 'arpeggio'
        return out
    if ev['event'] == 'farewell':              # (round op1: over a loud coda, the guitar before the last tutti)
        out['guitar'] = _gtr_arp(rows, tune, fam, rng)
        ev['thin'] = 'soft'
        ev['mode'] = 'arpeggio'
        return out
    if ev['event'] == 'envoi':
        out['guitar'] = _gtr_arp(rows, tune, fam, rng)
        last = rows[-1] if rows else None
        if last:
            from .. import guitarist as gtr
            sym = last[2]
            try:
                c = gtr.let_ring(sym, max(2.0, last[1] - last[0] + 2.0), float(tune.tempo), ms=90.0,
                                 seed=rng.randrange(1 << 20))
            except ComposeError:
                c = gtr.let_ring(_simple(sym), max(2.0, last[1] - last[0] + 2.0), float(tune.tempo), ms=90.0,
                                 seed=rng.randrange(1 << 20))
            out['guitar'] = [n for n in out['guitar'] if n[0] < last[0] - _EPS] + \
                [(n.start + last[0], n.dur, n.pitch, 0.0) for n in c]
        ev['thin'] = 'soft'
        ev['mode'] = 'arpeggio'
        return out
    return out


# ------------------------------------------------------------------------------------------------ writing: harpsichord

def _bass_of(plan_o, block: str, a, z) -> list:
    from .choir import _clip
    ns = [n for p in plan_o.parts if p.block == block and p.function == 'bass' and p.notes for n in p.notes]
    low = {}
    for st, du, p in _clip(ns, a, z):
        k_ = round(st, 4)
        if k_ not in low or p < low[k_][2]:
            low[k_] = (st, du, p)
    return [low[x] for x in sorted(low)]


def _harpsichord(ev, b, blocks, a, z, tune, plan_o, rng, meter) -> dict:
    from .. import organ_vocab as ov
    rows = _rows(blocks, a, z)
    key = b.key
    bass = [(st, du, _fold([(0, 0, p)], 29, 55, 41)[0][2]) for st, du, p in _bass_of(plan_o, b.name, a, z)]
    if not bass:
        bass = [(st, zz - st, min((p for p in range(29, 48) if p % 12 == _bass_pc(sym)), default=41))
                for st, zz, sym in rows]
    out = {}
    if ev['event'] == 'continuo':
        ch = _chorale(rows, [], a, z, key, HARPSI_RH)
        rh = []
        step = 1.0
        for v, ns in ch.items():
            for st, du, p in ns:
                t = st
                while t < st + du - _EPS:
                    rh.append((t, min(0.6, st + du - t), p, 2.0 if abs((t - a) % meter) < _EPS else -2.0))
                    t += step
        out['harpsichord'] = sorted(rh + [(st, du, p, 3.0) for st, du, p in bass])
        ev['reg'] = 'full' if ev.get('tutti') else '8ft'
        ev['thin'] = 'continuo'
        return out
    if ev['event'] == 'concertino':
        slots = ov.slots_from_chart([(st, zz - st, sym) for st, zz, sym in rows], key, rate=1.0)
        fig = FIGURES[rng.randrange(len(FIGURES))]
        t = ov.toccata(slots, key, figure=fig, register=('C4', 'C6'), lh=None, seed=rng.randrange(1 << 20))
        out['harpsichord'] = sorted([(st, du, p, 0.0 if abs((st - a) % 1.0) < _EPS else -4.0)
                                     for st, du, p in t['rh']] + [(st, du, p, 3.0) for st, du, p in bass])
        ev['reg'] = '8ft'
        ev['figure'] = fig
        ev['thin'] = 'concertino'
        return out
    if ev['event'] == 'cadence':
        if not rows:
            return {}
        st, zz, sym = rows[-1]
        ch = _chorale([(st, zz, sym)], [], st, zz, key, dict(HARPSI_RH, b1=(41, 55, 48)))
        notes = sorted(p for ns in ch.values() for _, _, p in ns)
        ev['reg'] = 'full' if not ev.get('soft') else '8ft'
        if ev.get('gest') and ev['gest'] != 'rolled' and notes:   # (round op1: the last chord drawn per piece)
            out['harpsichord'] = _cadence(ev['gest'], notes, rows, a, z, st, zz, key, meter, bass)
            return out
        out['harpsichord'] = [(st + 0.04 * i, zz - st + 1.0 - 0.04 * i, p, 4.0) for i, p in enumerate(notes)]
        return out
    return out


def _cadence(gest: str, notes, rows, a, z, st, zz, key, meter: float, bass) -> list:
    """POLISH's harpsichord endings other than the lone rolled chord: 'flourish' (a scale run of 16ths up into the
    chord's top, the chord struck with the orchestra - no ring after it), 'with' (the continuo's chords on the beats
    through the last bars, ending with the orchestra), 'broken' (the chord broken downwards, slowly, the bass last,
    let ring)."""
    top = notes[-1]
    if gest == 'flourish':
        K = Key(key) if isinstance(key, str) else key
        scale = [p for p in range(top - 14, top) if p % 12 in {x % 12 for x in K.pcs}][-8:]
        t0 = st - 0.25 * len(scale)
        run = [(t0 + 0.25 * i, 0.25, p, -2.0 + 0.5 * i) for i, p in enumerate(scale) if t0 + 0.25 * i >= a - _EPS]
        return run + [(st, zz - st, p, 4.0) for p in notes]
    if gest == 'with':
        out = []
        for ns in _chorale(rows, [], a, z, key, HARPSI_RH).values():
            for n0, nd, p in ns:
                t = n0
                while t < n0 + nd - _EPS:
                    last = t >= st - _EPS
                    out.append((t, (n0 + nd - t) if last else min(0.6, n0 + nd - t), p,
                                2.0 if abs((t - a) % meter) < _EPS else -2.0))
                    if last:
                        break
                    t += 1.0
        if not out:
            out = [(st, zz - st, p, 3.0) for p in notes]
        return sorted(out + [(b0, bd, bp, 3.0) for b0, bd, bp in bass if b0 >= a - _EPS])
    return [(st + 0.09 * i, zz - st + 1.0 - 0.09 * i, p, 4.0 - 0.3 * i) for i, p in enumerate(reversed(notes))]


# ------------------------------------------------------------------------------------------------ writing: celesta

def _thin_fast(ns, tune, max_per_s: float = 6.0) -> list:
    """A line's notes thinned for a bell: a note closer than 1 / max_per_s s after the one kept before is left out."""
    gap = float(tune.tempo) / 60.0 / max_per_s
    out = []
    for n in ns:
        if out and n[0] - out[-1][0] < gap - _EPS:
            continue
        out.append(n)
    return out


def _celesta(ev, b, blocks, a, z, tune, plan_o, rng) -> dict:
    rows = _rows(blocks, a, z)
    if ev['event'] == 'sparkle':
        line = _thin_fast(_line(plan_o, b, a, z, tune), tune, 7.0)
        return {'celesta': [(st, du, p, 4.0) for st, du, p in _fold(line, 72, 96, 84)]}
    if ev['event'] == 'glitter':
        line = [n for n in _thin_fast(_line(plan_o, b, a, z, tune), tune, 3.0) if n[1] >= 0.5 - _EPS]
        return {'glockenspiel': [(st, du, p, 2.0) for st, du, p in _fold(line, 79, 103, 91)]}
    if ev['event'] == 'twinkle':
        if not rows:
            return {}
        st, zz, sym = rows[-1] if ev.get('last') else rows[0]
        c = chord(sym)
        if ev.get('gest') and ev['gest'] != 'rise':          # (round op1: the closing gesture drawn per piece)
            return {'celesta': _twinkle(ev['gest'], c, st, zz, tune, ev.get('last'), rng)}
        tones = [p for p in range(72, 97) if p % 12 in c.pcs][:8]
        step = 0.25 if float(tune.tempo) < 120 else 0.5 / 3
        if ev.get('last'):
            st = max(st, zz - len(tones) * step - 1.0)
        return {'celesta': [(st + i * step, max(0.5, zz - st - i * step + 1.0), p, 1.0 + 1.0 * i)
                            for i, p in enumerate(tones)]}
    return {}


def _twinkle(gest: str, c, st: float, zz: float, tune, last: bool, rng) -> list:
    """POLISH's celesta gestures other than the rising arpeggio: 'fall' (from the top down, the low note held),
    'wave' (up five, down to the third), 'chime' (a high broken triad struck twice, the top held) - the register
    drawn (from C5 or from G5)."""
    lo = (72, 79)[rng.randrange(2)]
    tones = [p for p in range(lo, 97) if p % 12 in c.pcs]
    step = 0.25 if float(tune.tempo) < 120 else 0.5 / 3
    if gest == 'fall':
        seq = list(reversed(tones[:8]))
    elif gest == 'wave':
        up = tones[:6]
        seq = up + list(reversed(up[1:-1]))[:3]
    else:
        hi3 = [p for p in range(81, 97) if p % 12 in c.pcs][:3] or tones[-3:]
        seq = hi3 + hi3 + [hi3[0] + 12 if hi3[0] + 12 <= 96 else hi3[-1]]
        step *= 1.5
    if last:
        st = max(st, zz - len(seq) * step - 1.0)
    n = len(seq)
    return [(st + i * step, max(0.5, zz - st - i * step + 1.0) if i >= n - 3 else max(0.4, 3 * step), p,
             1.0 + (6.0 * i / max(1, n - 1) if gest != 'fall' else 4.0 - 4.0 * i / max(1, n - 1)))
            for i, p in enumerate(seq)]


# ------------------------------------------------------------------------------------------------ writing: bells

def _bells(ev, b, blocks, a, z, tune, plan_o, rng, mat, k) -> dict:
    bar = _bar(mat, k)
    key = Key(tune.key)
    ton = next(p for p in range(60, 72) if p % 12 == key.tonic % 12)
    if ev['event'] in ('peal', 'peal_soft'):
        line = _line(plan_o, b, a, z, tune)
        out = []
        t = a
        i = 0
        while t < z - _EPS:
            p = next((q for st, du, q in line if st - _EPS <= t < st + du - _EPS), None)
            if p is not None or i == 0:
                q = _fold([(0, 0, p if p is not None else ton)], 60, 79, 70)[0][2]
                out.append((t, 2 * bar, q, 4.0 if i == 0 else 0.0))
                if i == 0:
                    out.append((t, 2 * bar, ton if ton != q else ton + 12, 0.0))
            i += 1
            t += bar if (i < 4 or ev['event'] == 'peal') else 2 * bar
        return {'bells': out}
    if ev['event'] == 'hint':                  # (round op1: a distant bell before the climax - the line's first note)
        line = _line(plan_o, b, a, z, tune)
        p1 = _fold([(0, 0, line[0][2] if line else ton)], 60, 79, 70)[0][2]
        out = [(a, 2 * bar, p1, -6.0)]
        if z - a >= 3 * bar - _EPS:
            out.append((a + 2 * bar, 2 * bar, ton if ton != p1 else ton + 7, -9.0))
        return {'bells': out}
    if ev['event'] == 'toll' and ev.get('gest') and ev['gest'] != 'scale':
        return {'bells': _peal(ev['gest'], ev, b, a, z, tune, plan_o, key, ton, bar)}
    if ev['event'] == 'toll':
        out = []
        last_end = z
        scale = sorted({p for p in range(ton, ton + 13) if (p - key.tonic) % 12 in
                        {(x - key.tonic) % 12 for x in key.pcs}}, reverse=True)
        beat_s = 60.0 / float(tune.tempo)
        if ev.get('soft'):
            t, i = a, 0
            while t < last_end - bar + _EPS:
                out.append((t, 2 * bar, ton if i % 2 == 0 else ton - 5 if ton - 5 >= 60 else ton + 7,
                            -2.0 * i))
                i += 1
                t += bar if i < 4 else 2 * bar
        else:
            step = max(1.0, math.ceil(0.55 / beat_s))
            t = a
            while t < last_end - bar - _EPS:
                for p in scale:
                    if t >= last_end - bar - _EPS:
                        break
                    out.append((t, 2 * step, p, 0.0))
                    t += step
            out.append((max(a, last_end - bar), 2 * bar, ton, 6.0))
        return {'bells': out}
    return {}


def _peal(gest: str, ev, b, a, z, tune, plan_o, key, ton: int, bar: float) -> list:
    """POLISH's coda peals other than the descending scale on a lone bell: 'rounds' (four bells in plain-hunt
    changes, the last row struck together), 'motto' (the coda's tune head rung slowly, then tonic and fifth together),
    'toll' (tonic and the fifth below alternating, the last stroke tonic + octave); a soft ending rings them softer and
    slower."""
    soft = bool(ev.get('soft'))
    beat_s = 60.0 / float(tune.tempo)
    step = max(1.0, math.ceil((0.8 if soft else 0.55) / beat_s))
    third = ton + (3 if (ton + 3 - key.tonic) % 12 in {(x - key.tonic) % 12 for x in key.pcs} else 4)
    end = max(a, z - bar)
    base = -3.0 if soft else 0.0
    out = []
    if gest == 'rounds':
        bells = [ton + 12, ton + 7, third, ton]
        row, t, swap = [0, 1, 2, 3], a, 0
        while t < end - _EPS:
            for i in row:
                if t >= end - _EPS:
                    break
                out.append((t, 2 * step, bells[i], base))
                t += step
            t += step                                         # (the handstroke gap)
            row = [row[1], row[0], row[3], row[2]] if swap == 0 else [row[0], row[2], row[1], row[3]]
            swap ^= 1
        out += [(end, 2 * bar, p, base + 4.0) for p in bells]
        return out
    if gest == 'motto':
        line = _line(plan_o, b, a, z, tune)[:5] or [(a, 1.0, ton)]
        head = [q for _, _, q in _fold(line, 60, 79, 69)]
        t = a
        while t < end - _EPS:
            for q in head:
                if t >= end - _EPS:
                    break
                out.append((t, 2 * step, q, base))
                t += 2 * step
            t += 2 * step
        out += [(end, 2 * bar, ton, base + 4.0), (end, 2 * bar, ton + 7, base + 2.0)]
        return out
    t, i = a, 0
    low5 = ton - 5 if ton - 5 >= 55 else ton + 7
    while t < end - _EPS:
        out.append((t, 2 * bar, ton if i % 2 == 0 else low5, base - 1.0 * min(i, 6)))
        i += 1
        t += bar
    out += [(end, 2 * bar, ton, base + 3.0), (end, 2 * bar, ton + 12, base + 1.0)]
    return out


# ------------------------------------------------------------------------------------------------ the thinning

def _thin(plan_o, ev, a, z, roles_of) -> int:
    """The orchestra under a guest event (ev['thin']): 'all' - out (a guest alone); 'serenade' - the guitar's room
    (brass / percussion / harp / choir out, the tune to a solo wind in the arpeggio half and out in the guitar's own
    half, the bass plucked, the strings' harmony a soft pad, figures out); 'soft' - the soft ending (brass and
    percussion out, the rest softer); 'continuo' / 'concertino' - the baroque band (the trombones / tuba /
    percussion out; the concertino: the strings and the tune only, softer)."""
    C = COLOUR or COLOUR_ON
    kind = ev.get('thin')
    if not kind:
        return 0
    if kind == 'all':
        return _edit(plan_o, a, z, lambda p: 'drop')
    if kind == 'hand':                         # (round op1: the orchestra hands the tune to the guest, softer under it)
        return _edit(plan_o, a, z, lambda p: 'drop' if p.function in ('melody', 'doubling') and p.line or
                     p.role in ('trumpets', 'trombones', 'tuba', 'low_brass', 'percussion', 'drums') else
                     {'off': C['thin_db'] / 2})
    if kind == 'soft':
        return _edit(plan_o, a, z, lambda p: 'drop' if p.role in LOUD_ROLES or p.role == 'harp' else
                     {'off': C['thin_db']} if p.function == 'bass' else      # (the guitar's own bass: no masking)
                     {'off': C['thin_db'] / 2} if p.function not in ('melody',) else None)
    if kind in ('continuo', 'concertino'):
        def rule(p):
            if p.role in ('trombones', 'tuba', 'low_brass', 'percussion', 'choir', 'drums', 'harp'):
                return 'drop'
            if kind == 'concertino':
                if p.function == 'melody':
                    return None
                if p.role in STRINGS and p.function in ('bass', 'harmony', 'pedal', 'doubling', 'counter'):
                    return {'off': C['thin_db'] / 2}
                return 'drop'
            if p.role in ('horns', 'trumpets', 'timpani') and p.function not in ('melody', 'doubling'):
                return {'off': C['thin_db'] / 2}
            return None
        return _edit(plan_o, a, z, rule)
    if kind == 'serenade':
        split = ev.get('split', z)
        wind = ev.get('wind')
        n = 0

        def rule(half):
            def r(p):
                if p.role in LOUD_ROLES or p.role in ('harp',) or p.function in ('ostinato', 'figuration', 'colour'):
                    return 'drop'
                if p.function == 'melody':
                    if half == 'arp' and wind and p.role == ev.get('mel_role'):
                        return {'role': wind, 'line': True, 'off': C['wind_db']}
                    return 'drop'
                if p.function in ('bass',) and p.role in STRINGS:
                    return {'art': 'pizzicato', 'off': C['pizz_db']}
                if p.role in STRINGS and p.function in ('harmony', 'pedal', 'inner'):
                    return {'off': C['thin_db'] if half == 'arp' else C['pad_db']}
                return 'drop'
            return r
        n += _edit(plan_o, a, split, rule('arp'))
        if split < z - _EPS:
            n += _edit(plan_o, split, z, rule('tune'))
        return n
    return 0


def _wind(plan_o, b, roles, rng) -> tuple:
    """The serenade's solo wind: the block's melody role when it is a woodwind, else one of the piece's woodwinds
    (clarinet, oboe, flute - drawn) -> (wind role, the melody's role)."""
    mel = _melody_parts(plan_o, b.name)
    mr = mel[0].role if mel else None
    if mr in WINDS:
        return mr, mr
    ws = [w for w in ('clarinets', 'oboes', 'flutes') if w in roles] or ['clarinets']
    return ws[rng.randrange(len(ws))], mr


# ------------------------------------------------------------------------------------------------ prepare / play

def prepare(plan_o, score, mat: dict, tune, k: float, roles=(), reserved=()) -> dict | None:
    """COLOUR after the orchestration (and the choir): the piece's guest (tune.arrange['guest'], else its own draw),
    its events placed and written, the orchestra thinned where the guest needs the room. -> {'colour', 'plan',
    'organ', 'events'} or None (no guest)."""
    g = (tune.arrange or {}).get('guest') or guest_draw(tune.feel, random.Random(f"sym-guest:{tune.seed}"))
    name = g.get('colour', 'none')
    if name == 'none':
        return {'colour': 'none', 'plan': None, 'events': []}
    if name not in GUESTS:
        raise ComposeError(f"guest colour {name!r}: one of {', '.join(GUESTS)}")
    G = GUESTS[name]
    plan = g.get('plan') if g.get('plan') in G['plans'] else sorted(G['plans'])[0]
    rng = random.Random(f"colour:{tune.seed}:{g.get('seed', 0)}")
    fam = 'compound' if mat.get('family') == 'compound' or tuple(getattr(tune, 'time_sig', (4, 4)))[1] == 8 else \
        'duple'
    bar = _bar(mat, k)
    meter = float(score.meter)
    solo = ORGAN_SOLO[rng.randrange(len(ORGAN_SOLO))]
    taken, events = list(reserved), []
    order = list(score.blocks)
    P = (COLOUR or {}).get('polish')
    wants = list(G['plans'][plan])
    if P and name == 'bells':                  # (round op1: the bells hinted before the climax)
        wants = ['hint'] + wants
    for want in wants:
        alts = want if isinstance(want, tuple) else (want,)
        for evn in alts:
            cands = _places(evn, mat, score, tune, k, taken, plan_o)
            if not cands:
                continue
            ev = _write1(name, evn, cands[0], order, bar, g, tune, plan_o, rng, solo, fam, meter, mat, k, roles,
                         taken)
            if ev is None:
                continue
            events.append(ev)
            break
    if P:                                      # (round op1: the coda kept, the returns in the long silences)
        _polish_events(P, name, events, mat, score, tune, k, taken, plan_o, order, bar, g, rng, solo, fam, meter,
                       roles)
    return {'colour': name, 'plan': plan, 'organ': g.get('organ', 'burea'), 'events': events}


def _write1(name, evn, cand, order, bar, g, tune, plan_o, rng, solo, fam, meter, mat, k, roles, taken):
    """One placed event written (its notes, the orchestra thinned, its span taken) -> the event or None (no notes)."""
    b, a, z, extra = cand
    i = order.index(b)
    blocks = [x for x in order[i:] if x.start < z - _EPS]
    ev = dict(event=evn, block=b.name, start=a, end=z, bar=bar, **extra)
    if g.get('gest') and evn in ('twinkle', 'toll', 'cadence'):     # (round op1: the signature gesture's variant)
        ev['gest'] = g['gest']
    if name == 'organ':
        notes = _organ(ev, b, blocks, a, z, tune, plan_o, rng, solo)
    elif name == 'guitar':
        if evn == 'serenade':
            ev['wind'], ev['mel_role'] = _wind(plan_o, b, roles, rng)
        notes = _guitar(ev, b, blocks, a, z, tune, plan_o, rng, fam)
    elif name == 'harpsichord':
        notes = _harpsichord(ev, b, blocks, a, z, tune, plan_o, rng, meter)
    elif name == 'celesta':
        notes = _celesta(ev, b, blocks, a, z, tune, plan_o, rng)
    else:
        notes = _bells(ev, b, blocks, a, z, tune, plan_o, rng, mat, k)
    notes = {r: ns for r, ns in notes.items() if ns}
    if not notes:
        return None
    ev['notes'] = {r: [tuple(n) if len(n) == 4 else tuple(n) + (0.0,) for n in ns] for r, ns in notes.items()}
    ev['thinned'] = _thin(plan_o, ev, a, z, roles)
    taken.append((a, z))
    return ev


def _polish_events(P, name, events, mat, score, tune, k, taken, plan_o, order, bar, g, rng, solo, fam, meter,
                   roles) -> None:
    """POLISH (round op1, COLOUR_POLISH): the guest in the coda (P['codas'] when no event reaches the last block),
    then up to P['returns'] RETURNS (P['returns_of']) in the longest stretches without it (more than P['gap'] of the
    piece) - events appended, sorted by time."""
    from .symphony import _vmax
    from ..bandlib.scoring import VEL
    bl = _blocks(mat, score)
    last = order[-1]
    if not any(ev['end'] > last.start + _EPS for ev in events):
        for evn in P['codas'][name]:
            cands = _places(evn, mat, score, tune, k, taken, plan_o) if evn != 'farewell' else \
                _farewell(bl, bar, taken)
            ev = _write1(name, evn, cands[0], order, bar, g, tune, plan_o, rng, solo, fam, meter, mat, k, roles,
                         taken) if cands else None
            if ev is not None:
                ev['added'] = 'coda'
                events.append(ev)
                break
    L0, L1 = order[0].start, last.end
    evn = P['returns_of'][name]
    for _ in range(P['returns']):
        spans = sorted((ev['start'], ev['end']) for ev in events)
        edges = [L0] + [x for s_ in spans for x in s_] + [L1]
        gaps = sorted(((edges[i + 1] - edges[i], edges[i], edges[i + 1]) for i in range(0, len(edges), 2)),
                      reverse=True)
        placed = False
        for size, g0, g1 in gaps:
            if size < P['gap'] * (L1 - L0) - _EPS:
                break
            best = None
            for i, (x, b) in enumerate(bl):
                if x['peak'] or b is last or x['kind'] in ('coda', 'coda_soft', 'end', 'end_soft') or \
                        b.start < g0 - _EPS or b.start >= g1 - _EPS:
                    continue
                need = 2 if name == 'bells' else 4
                if b.length < need * bar - _EPS:
                    continue
                v = _vmax(b)
                if name in ('organ', 'guitar') and not _quiet(x, b) or name == 'celesta' and v > VEL['f']:
                    continue
                z = min(b.end, g1, b.start + (4 if name == 'bells' else P['return_bars']) * bar)
                if z - b.start < need * bar - _EPS or not _free(taken, b.start, z):
                    continue
                apart = P['apart'] * (L1 - L0)             # (a return is no echo of the event next to it)
                if any(b.start < e1 + apart - _EPS and z > s1 - apart + _EPS for s1, e1 in spans):
                    continue
                if name in ('celesta', 'guitar', 'organ') and not _line(plan_o, b, b.start, z, tune):
                    continue
                pref = P['prefer'].index(x['kind']) if x['kind'] in P['prefer'] else len(P['prefer'])
                mid = abs((b.start + z) / 2 - (g0 + g1) / 2) / max(_EPS, g1 - g0)
                key_ = (pref + 6 * mid, b.start)
                if best is None or key_ < best[0]:
                    best = (key_, (b, b.start, z, {'tutti': v >= VEL['f']} if name == 'harpsichord' else {}))
            if best is None:
                continue
            ev = _write1(name, evn, best[1], order, bar, g, tune, plan_o, rng, solo, fam, meter, mat, k, roles,
                         taken)
            if ev is not None:
                ev['added'] = 'return'
                events.append(ev)
                placed = True
                break
        if not placed:
            break
    events.sort(key=lambda e: e['start'])


def _farewell(bl, bar, taken) -> list:
    """The guitar's farewell over a loud coda: the coda's first two bars (the coda at least 6 bars)."""
    for x, b in bl:
        if x['kind'] in ('coda', 'coda_soft') and b.length >= 6 * bar - _EPS and _free(taken, b.start, b.start + 2 * bar):
            return [(b, b.start, b.start + 2 * bar, {})]
    return []


def _swell_points(kind: str, a: float, z: float, bar: float) -> list:
    C = COLOUR or COLOUR_ON
    if kind == 'open':
        lo, hi = C['swell']
        return [(a, lo), (z - 0.5, hi, 'smooth')]
    lo, hi = C['soft_swell']
    pts = [(a, lo)]
    t = a
    while t + 2 * bar <= z + _EPS:                  # (the soft flues breathe phrase by phrase: 4 bars up and down)
        pts.append((min(z, t + 2 * bar), hi, 'smooth'))
        pts.append((min(z, t + 4 * bar), lo, 'smooth'))
        t += 4 * bar
    return pts


def play(s, host, marks, tune, cl: dict, gain: float = 0.0, style: str = 'romantic') -> None:
    """Play the prepared events (prepare) on the guest band seated in the host band's hall: the organ
    (orch.church_organ: the used registrations, its swell lanes) or orch.guests; one orch.Score with the piece's
    dynamics marks (the guests' velocities follow the map + their figure's accents). Sets s.colour_plan /
    s.colour_events (colour_stats)."""
    from ..bandlib import orchestra as orch
    C = COLOUR or COLOUR_ON
    s.colour_plan = {'colour': cl['colour'], 'plan': cl.get('plan'),
                     **({'organ': cl.get('organ')} if cl['colour'] == 'organ' else {})}
    s.colour_events = []
    if not cl['events']:
        return
    used = sorted({r for ev in cl['events'] for r in ev['notes']})
    hall = host.buses.get('hall')
    if cl['colour'] == 'organ':
        regs = tuple(r for r in used if r in orch.ORGAN_REGISTERS)
        allr = ('soft', 'principal', 'full', 'pedal', 'pedal_full') + regs
        band = orch.church_organ(s, organ=cl.get('organ') or 'burea', registers=regs,
                                 without=tuple(r for r in allr if r not in used),
                                 ids={r: f'organ_{r}' for r in allr}, hall=hall)
        for r in band.roles:
            band[r].gain_db += gain + C['gain'] + C['organ_gain'] + C['organ_db'].get(r, 0.0)
            if hall is not None:
                band[r].send(hall, C['organ_send'])
    else:
        band = orch.guests(s, used, hall=hall, gain_db=gain + C['gain'])
        for r in band.roles if C.get('polish') else ():      # (round op1: the cameo guests more present)
            band[r].gain_db += C['polish']['db'].get(r, 0.0)
        if 'harpsichord' in band.roles:          # (no touch dynamics: the report judges its registration, as an organ's)
            band['harpsichord']._registration = True
    sc = orch.Score(s, band, marks, key=tune.key, seed=(tune.seed % 9973) + 11, style=style)
    if isinstance(getattr(s, 'orch_scores', None), list) and sc in s.orch_scores:
        s.orch_scores.remove(sc)                   # (the orchestration metrics read the orchestra's own score)
    for ev in cl['events']:
        for role, ns in sorted(ev['notes'].items()):
            rel = {(round(st, 4), p): r_ for st, du, p, r_ in ns}
            art_ = ev.get('reg', '8ft') if role == 'harpsichord' else None
            line = role in ('guitar',) and ev.get('mode', '') != 'arpeggio' or role == 'celesta' and \
                ev['event'] == 'sparkle' or (cl['colour'] == 'organ' and role == ev.get('solo'))
            sc.add(role, [(st, du, p) for st, du, p, _ in ns], art_, offs=lambda n, rel=rel: rel.get(
                (round(n[0], 4), n[2]), 0.0), line=bool(line))
        if cl['colour'] == 'organ' and ev.get('swell'):
            for role, kind in ev['swell'].items():
                if role in band.roles and role in (band.info.get('swell') or ()):
                    orch.swell(band, _swell_points(kind, ev['start'], ev['end'], ev['bar']), roles=[role])
        s.colour_events.append({'event': ev['event'], 'block': ev['block'], 'start': round(ev['start'], 3),
                                'end': round(ev['end'], 3), 'roles': sorted(ev['notes']),
                                'notes': sum(len(x) for x in ev['notes'].values()), 'thinned': ev.get('thinned', 0),
                                **{x: ev[x] for x in ('mode', 'wind', 'reg', 'figure', 'solo', 'gest', 'added')
                                   if ev.get(x)}})
    sc.perform(follow=True)


def colour_stats(song) -> dict:
    """The guest of a built piece: its colour / plan (organ), its events (event, block, beats, roles, notes, the
    orchestra's notes changed, the guitar's mode, the serenade's wind, the harpsichord's registration / figure, the
    organ's solo stop)."""
    return {'plan': getattr(song, 'colour_plan', None), 'events': list(getattr(song, 'colour_events', None) or [])}
