"""The ORCHESTRATOR: a polyphonic score of lines with musical FUNCTIONS (independent of instruments and of the
composer that wrote them) -> parts for the sections of an orchestra, by data tables - docs/ORCHESTRA_ENDLESS.md.

    from agentsound.bandlib import orchestra as orch
    sc = orch.OrchScore('Title', key='D major', meter=4, tempo=72)
    b = sc.block('A1', start=0, length=32, chart=[(0, 4, 'D'), (4, 4, 'Bm7'), ...], texture='solo_pad')
    b.add(orch.Line('melody', notes))                      # (start, dur, pitch) in song beats, a natural register
    b.add(orch.Line('harmony', h1, voice='h1')); ...       # real parts: h1 (top) .. hN
    plan = orch.orchestrate(sc, orch.role_table('film_orchestra'), pick=my_pick)   # -> Orchestration
    plan.parts                                             # [Part(role, block, function, notes, art, off, line)]

THE SCORE (OrchScore / Block / Line): blocks are sections (name, start, length, chord timeline, key, dynamics marks,
peak / frame flags, the texture), each with Lines - function (FUNCTIONS), notes with concrete pitches, a voice name
for real parts, `of` for a doubling. Any composer writes into it: the endless lead-sheet composer (endless/orchestra.py),
later a counterpoint / fugue / development composer (function 'voice').

THE ORCHESTRATION PLANS (TEXTURES): per texture type {function: slot}; a slot names the role(s) that carry the
function - 'pick' {role: weight} (one, drawn; weights x orch.ROLE_TRAITS[role]['functions'][function]) or 'voices'
(role, ...) top-down for the function's real parts (more voices than roles: the last role plays them divisi) - and
'n' (voices to write), 'art', 'off' (velocity offset over FUNCTIONS'), 'shift' (semitones before fitting), 'double'
{role: (interval, chance)}, 'chance' (the function is present at all), 'figure' (how the composer writes it). A
'colour' slot may be a list (harp arpeggios + a timpani roll ...). Texture keys: 'peak' (only on a peak block),
'size' ('full': needs the brass), 'light' (a thin texture: intros, codas).

THE RULES (RULES, budgets / distributions): ranges (a line moves by whole octaves toward the role's sweet spot; a
note still outside its range is folded and counted - metrics range_out), spacing (the harmony's adjacent upper voices
within `spacing` semitones, no third under `low_third`), doublings by register, a role carries one function per
block (a taken role gives its voice to a free partner), the colour change at boundaries (the melody's role differs
from the block before with `colour_change`), the tutti reserved for peak blocks (at most `tutti_blocks`), the coda
thin (a 'light' texture), the texture not twice running (`texture_change`).

metrics(score) measures any orch.Score (endless or hand-written): range faults, the melody's sweet-spot share,
spacing, low thirds, the melody's margin, colour changes, the tutti share, the coda's thinning, roles per bar,
doublings, the climax place and the loudness range (note energy).
"""
from __future__ import annotations

import math
import statistics as st
from dataclasses import dataclass, field

from ..theory import ComposeError, note as _note

__all__ = ['FUNCTIONS', 'TEXTURES', 'RULES', 'Line', 'Block', 'OrchScore', 'Part', 'Orchestration', 'plan_blocks',
           'orchestrate', 'metrics', 'needs']

_EPS = 1e-6

FUNCTIONS = {
    # off: the velocity offset under the dynamics map (the balance ranks: the melody on top); art: the default
    # articulation; line: written as a LINE (orch.Score's balance keeps the accompaniment under it)
    'melody': {'off': 4.0, 'art': 'sustain', 'line': True},
    'counter': {'off': -4.0, 'art': 'sustain', 'line': True},
    'voice': {'off': 0.0, 'art': 'sustain', 'line': True},
    'doubling': {'off': -4.0, 'art': None, 'line': True},
    'harmony': {'off': -10.0, 'art': 'sustain', 'line': False},
    'inner': {'off': -8.0, 'art': 'sustain', 'line': False},
    'bass': {'off': -5.0, 'art': 'sustain', 'line': False},
    'ostinato': {'off': -8.0, 'art': 'staccato', 'line': False},
    'colour': {'off': -8.0, 'art': 'sustain', 'line': False},
    'pedal': {'off': -10.0, 'art': 'sustain', 'line': False},
}
"""The musical functions a line can have (docs/ORCHESTRA_ENDLESS.md): melody, counter (a counter-melody), voice (an
equal contrapuntal voice: fugue / canon), doubling (of another line: `of`), harmony (sustained chord voices: the pad),
inner (moving inner voices), bass, ostinato (a rhythmic repeated figure), colour (figuration, sparkle, a roll),
pedal (a held pedal point)."""
ORDER = ('melody', 'voice', 'counter', 'bass', 'harmony', 'inner', 'ostinato', 'colour', 'pedal')
"""The order the orchestrator seats the functions in (a role taken by an earlier one is not given to a later one)."""

_STR3 = ('violins2', 'violas', 'cellos')
TEXTURES = {
    # a hushed string pad; the melody (when the block has one) on the violins or a soft wind; a harp now and then
    'strings_pad': {
        'melody': {'pick': {'violins1': 1.0, 'clarinets': 0.6, 'flutes': 0.5, 'oboes': 0.4}},
        'harmony': {'voices': _STR3, 'n': 3},
        'bass': {'pick': {'basses': 1.0}, 'off': -4.0},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.35, 'figure': 'arp'}],
        'light': True},
    # a solo (oboe, flute, clarinet, horn, cello) over the strings' pad
    'solo_pad': {
        'melody': {'pick': {'oboes': 1.0, 'flutes': 0.9, 'clarinets': 0.8, 'horns': 0.6, 'cellos': 0.5}},
        'harmony': {'voices': ('violins2', 'violas', 'violas'), 'n': 3},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 0.6)}},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.45, 'figure': 'arp'}],
        'light': True},
    # a solo over harp arpeggios, a soft horn / clarinet pad, the cellos' bass
    'harp_solo': {
        'melody': {'pick': {'flutes': 1.0, 'oboes': 0.8, 'clarinets': 0.7, 'violins1': 0.5}},
        'colour': [{'pick': {'harp': 1.0}, 'figure': 'arp'}],
        'harmony': {'voices': ('horns', 'horns'), 'n': 2, 'off': -4.0},
        'bass': {'pick': {'cellos': 1.0}, 'off': -2.0},
        'light': True},
    # the violins sing, violas / cellos hold the harmony, the basses under them; a counter-melody sometimes
    'strings_melody': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'violins2': (-12, 0.6), 'flutes': (12, 0.35),
                                                         'oboes': (0, 0.2)}},
        'counter': {'pick': {'cellos': 1.0, 'horns': 0.8, 'violas': 0.4}, 'chance': 0.4,
                    'double': {'bassoons': (0, 0.3)}},
        'harmony': {'voices': ('violins2', 'violas', 'cellos'), 'n': 3},
        'bass': {'pick': {'basses': 1.0}},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.4, 'figure': 'arp'}]},
    # the cellos' tenor theme under a high string pad
    'cello_theme': {
        'melody': {'pick': {'cellos': 1.0, 'horns': 0.5}, 'double': {'bassoons': (0, 0.35), 'horns': (0, 0.35),
                                                                    'violas': (0, 0.25)}},
        'harmony': {'voices': ('violins1', 'violins2', 'violas'), 'n': 3, 'off': -2.0},
        'bass': {'pick': {'basses': 1.0}},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.5, 'figure': 'arp'}]},
    # a woodwind choir: the tune on top, clarinets / oboes inside, the bassoon's bass
    'chorale_winds': {
        'melody': {'pick': {'flutes': 1.0, 'oboes': 0.9, 'clarinets': 0.5}, 'double': {'clarinets': (-12, 0.3)}},
        'harmony': {'voices': ('oboes', 'clarinets', 'clarinets'), 'n': 3, 'off': -3.0},
        'bass': {'pick': {'bassoons': 1.0}, 'double': {'basses': (-12, 0.4)}},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.3, 'figure': 'arp'}],
        'light': True},
    # the theme with a counter-melody: violins / a wind above, cellos / horns answering
    'counter_strings': {
        'melody': {'pick': {'violins1': 1.0, 'oboes': 0.6, 'flutes': 0.6}, 'double': {'violins2': (-12, 0.4),
                                                                                      'flutes': (12, 0.3),
                                                                                      'clarinets': (0, 0.3)}},
        'counter': {'pick': {'cellos': 1.0, 'horns': 0.9, 'violas': 0.4}, 'double': {'bassoons': (0, 0.4)}},
        'harmony': {'voices': ('violins2', 'violas'), 'n': 2},
        'bass': {'pick': {'basses': 1.0}},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.3, 'figure': 'arp'}]},
    # the strings drive in 8ths, the horns (or violins / cellos) carry the tune, a timpani roll into the next block
    'horn_ostinato': {
        'melody': {'pick': {'horns': 1.0, 'violins1': 0.7, 'cellos': 0.5}, 'double': {'cellos': (0, 0.25),
                                                                                       'violins1': (12, 0.4)}},
        'ostinato': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'staccato', 'figure': 'pulse8'},
        'harmony': {'voices': ('clarinets', 'bassoons'), 'n': 2, 'off': -2.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 0.8)}},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.5, 'figure': 'roll_end'}]},
    # THE climax: violins in octaves, flutes on top, horns under, brass harmony, the basses' octaves, timpani, a crash
    'tutti': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'violins2': (-12, 0.9), 'flutes': (12, 0.8),
                                                         'horns': (-12, 0.7), 'oboes': (0, 0.4)}},
        'harmony': {'voices': ('trumpets', 'trombones', 'trombones'), 'n': 3, 'off': -6.0},
        'inner': {'voices': ('violas', 'clarinets'), 'n': 2},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.6), 'bassoons': (0, 0.6)}},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'hits'}, {'pick': {'percussion': 1.0}, 'figure': 'crash'},
                   {'pick': {'choir': 1.0}, 'chance': 0.5, 'figure': 'aah'}],
        'peak': True, 'size': 'full'},
    # the lyrical climax: the strings' unison octaves, horns holding the harmony, woodwinds doubling, harp sweeps
    'tutti_lyrical': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'violins2': (-12, 0.9), 'cellos': (-24, 0.5),
                                                         'flutes': (12, 0.8), 'oboes': (0, 0.4),
                                                         'clarinets': (-12, 0.4), 'trumpets': (0, 0.3)}},
        'counter': {'pick': {'horns': 1.0, 'cellos': 0.7}, 'chance': 0.6},   # (r2: four octaves of one line, no
        'harmony': {'voices': ('horns', 'horns', 'violas'), 'n': 3, 'off': -4.0},      # counter-line at the peak)
        'inner': {'voices': ('clarinets', 'bassoons'), 'n': 2, 'off': -2.0},
        'bass': {'pick': {'basses': 1.0}, 'double': {'bassoons': (12, 0.5)}},
        'colour': [{'pick': {'harp': 1.0}, 'figure': 'arp'}, {'pick': {'timpani': 1.0}, 'chance': 0.6,
                                                              'figure': 'roll_end'},
                   {'pick': {'choir': 1.0}, 'chance': 0.4, 'figure': 'aah'}],
        'peak': True},
}
"""The orchestration plans of the film / new-age vocabulary (the module docstring has the slot keys)."""

RULES = {
    'fit_octaves': (-2, -1, 0, 1, 2),   # a line moves by these octaves (as a whole, per block) toward the sweet spot
    'spacing': 12,                      # the harmony's adjacent upper voices within an octave (close in the treble)
    'low_third': 48,                    # no third (or second) between the two lowest voices under C3 (wide in the bass)
    'colour_change': 0.85,              # the melody's role differs from the block before's (a colour change)
    'texture_change': 0.75,             # the texture differs from the block before's
    'tutti_blocks': 1,                  # tutti textures: peak blocks only, at most this many per piece
    'coda_light': True,                 # the last block (and an intro) plays a 'light' texture
    'doubling_floor': 'C3',             # a doubling of a line never under this (a melody doubled into the bass)
    'dyn_peak': 1,                      # a tutti block's marks a step louder (mf -> f): the full stack's weight;
    'dyn_light': 0,                     # a light texture's (-1: p -> pp - under p the sections' samples barely move
                                        # in level: a solo's hairpins went flat, the r1 gate's flat_dynamics)
    'power_db': 6.0,                    # a powerful section (ROLE_TRAITS power > 1: brass) under the line plays
                                        # softer: off -= power_db x log2(power) (horns 1.6: -4 dB) - it never covers
}
"""The orchestration rules as budgets / distributions (see the module docstring)."""


# ------------------------------------------------------------------------------------------------ the score

@dataclass
class Line:
    """One musical line: function (FUNCTIONS), notes [(start, dur, pitch)] in song beats (concrete pitches; a chord
    stream may hold simultaneous notes), voice (a real part's name: 'h1' .. 'hN' top-down), of (a doubling: the line
    it doubles), art (an articulation wish), meta (the composer's notes: figure, register ...)."""
    function: str
    notes: list
    voice: str = ''
    of: str | None = None
    art: str | None = None
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.function not in FUNCTIONS:
            raise ComposeError(f"Line: function {self.function!r} unknown ({', '.join(FUNCTIONS)})")
        self.notes = sorted((float(a), float(d), int(p)) for a, d, p in self.notes)


@dataclass
class Block:
    """A section of the score: name, start / length (beats), chart [(start, beats, symbol)] in song beats, key, marks
    (dynamics: (beat, level[, 'step'])), peak / frame flags, the texture (TEXTURES), its lines, meta (the drawn
    decisions: lead, counter, colour ...)."""
    name: str
    start: float
    length: float
    chart: list = field(default_factory=list)
    key: str = ''
    marks: list = field(default_factory=list)
    peak: bool = False
    frame: str | None = None
    texture: str | None = None
    lines: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def end(self) -> float:
        return self.start + self.length

    def add(self, line: Line) -> Line:
        self.lines.append(line)
        return line

    def get(self, function: str) -> list:
        return [x for x in self.lines if x.function == function]


class OrchScore:
    """A whole piece as blocks of lines (the module docstring): composer-independent, instrument-independent."""

    def __init__(self, title: str = '', key: str = 'C major', meter: int = 4, tempo: float = 80):
        self.title, self.key, self.meter, self.tempo = title, key, int(meter), float(tempo)
        self.blocks: list[Block] = []

    def block(self, name: str, start: float, length: float, chart=(), key: str | None = None, **kw) -> Block:
        if any(b.name == name for b in self.blocks):
            raise ComposeError(f"OrchScore: block {name!r} twice")
        b = Block(name, float(start), float(length), list(chart), key or self.key, **kw)
        self.blocks.append(b)
        return b

    def lines(self, function: str | None = None):
        for b in self.blocks:
            for x in b.lines:
                if function is None or x.function == function:
                    yield b, x

    def to_dict(self) -> dict:
        """A compact summary (tune.json): per block its texture, decisions and lines (function, voice, notes)."""
        return {'key': self.key, 'meter': self.meter, 'blocks': [
            {'name': b.name, 'start': round(b.start, 3), 'length': round(b.length, 3), 'texture': b.texture,
             'peak': b.peak, 'meta': {k: v for k, v in b.meta.items() if isinstance(v, (str, int, float, bool))},
             'lines': [[x.function, x.voice, len(x.notes)] for x in b.lines]} for b in self.blocks]}


def needs(texture: str) -> dict:
    """{function: [slot, ...]} a texture asks the composer to write (a colour slot list kept as a list)."""
    T = TEXTURES[texture]
    return {f: (v if isinstance(v, list) else [v]) for f, v in T.items() if f in FUNCTIONS}


# ------------------------------------------------------------------------------------------------ planning

def _avail(slot: dict, roles) -> dict:
    return {r: w for r, w in (slot.get('pick') or {}).items() if r in roles and w > 0}


def plan_blocks(score: OrchScore, weights: dict, roles, pick, rules: dict | None = None) -> None:
    """Draw each block's texture and its roles' picks (block.texture, block.meta['lead' / 'counter' / 'colour'])
    under the RULES' budgets: weights {block name: {texture: weight}}; roles: the roles the piece's band has (a
    size); pick(block, key, {choice: weight}) -> a choice (the caller's dice: endless.arrangement.Dice)."""
    R = dict(RULES, **(rules or {}))
    roles = set(roles)
    prev_tex = prev_lead = None
    tutti = 0
    last = score.blocks[-1].name if score.blocks else None
    for b in score.blocks:
        w = dict(weights.get(b.name) or {'strings_pad': 1.0})
        for t in list(w):
            T = TEXTURES.get(t)
            if T is None:
                raise ComposeError(f"orchestration: texture {t!r} unknown ({', '.join(TEXTURES)})")
            if (T.get('peak') and (not b.peak or tutti >= R['tutti_blocks'])) or \
                    (T.get('size') == 'full' and not {'trumpets', 'trombones'} <= roles) or \
                    not _avail(needs(t).get('melody', [{}])[0], roles) and 'melody' in T:
                w.pop(t)
            elif R['coda_light'] and b.name == last and not T.get('light'):
                w.pop(t)
        if not w:
            w = {'strings_pad': 1.0}
        if prev_tex in w and len(w) > 1:
            w[prev_tex] *= (1.0 - R['texture_change'])
        tex = pick(b.name, 'texture', w)
        b.texture = tex
        if TEXTURES[tex].get('peak'):
            tutti += 1
        T = TEXTURES[tex]
        if 'melody' in T:
            from .orchestra import ROLE_TRAITS
            lw = {r: x * ROLE_TRAITS.get(r, {}).get('functions', {}).get('melody', 0.5)
                  for r, x in _avail(T['melody'], roles).items()}
            if prev_lead in lw and len(lw) > 1:
                lw[prev_lead] *= (1.0 - R['colour_change'])
            b.meta['lead'] = pick(b.name, 'lead', lw)
            prev_lead = b.meta['lead']
        if 'counter' in T:
            s = T['counter']
            cw = {r: x for r, x in _avail(s, roles).items() if r != b.meta.get('lead')}
            on = cw and _chance(pick, b.name, 'counter_on', s.get('chance', 1.0))
            b.meta['counter'] = pick(b.name, 'counter', cw) if on else 'none'
        for i, s in enumerate(needs(tex).get('colour', ())):
            on = _avail(s, roles) and _chance(pick, b.name, f'colour{i}', s.get('chance', 1.0))
            b.meta[f'colour{i}'] = pick(b.name, f'colour{i}_role', _avail(s, roles)) if on else 'none'
        step = R['dyn_peak'] if T.get('peak') else R['dyn_light'] if T.get('light') else 0
        if step:
            b.marks = [(t, _step_mark(m, step)) for t, m in b.marks]
        prev_tex = tex


_MARKS = ('ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff')


def _step_mark(m, step: int):
    """A dynamic mark `step` marks louder (negative: softer); louder never past f (a mark already over it stays: an
    ff tutti saturates the velocities - the phrase arcs flatten, the r1 gate's flat_dynamics), softer never under ppp;
    anything else (a number) unchanged."""
    if m not in _MARKS:
        return m
    i = _MARKS.index(m)
    return _MARKS[min(i + step, max(i, _MARKS.index('f'))) if step > 0 else max(0, i + step)]


def _chance(pick, block, key, p: float) -> bool:
    if p >= 1.0:
        return True
    if p <= 0.0:
        return False
    return bool(pick(block, key, {1: p, 0: 1.0 - p}))


# ------------------------------------------------------------------------------------------------ orchestrating

@dataclass
class Part:
    """One role's share of one line in one block: notes [(start, dur, pitch)] as fitted, articulation, velocity offset,
    LINE or accompaniment."""
    role: str
    block: str
    function: str
    voice: str
    notes: list
    art: str
    off: float
    line: bool
    shift: int = 0


@dataclass
class Orchestration:
    parts: list = field(default_factory=list)
    folded: int = 0                       # notes still outside their role's range after the octave fit (folded)
    notes: int = 0

    def roles(self) -> list:
        seen = []
        for p in self.parts:
            if p.role not in seen:
                seen.append(p.role)
        return seen

    def by_block(self, block: str) -> list:
        return [p for p in self.parts if p.block == block]


def _n(x) -> int:
    return x if isinstance(x, int) else _note(x)


def _fit(notes, rng_: tuple, sweet: tuple, octaves) -> int:
    """The octave shift (semitones) that puts a line best into a role: no note outside the range first, then the most
    notes in the sweet spot, then the smallest move."""
    lo, hi = _n(rng_[0]), _n(rng_[1])
    slo, shi = _n(sweet[0]), _n(sweet[1])
    best = None
    for k in octaves:
        s = 12 * k
        out = sum(1 for _, _, p in notes if not lo <= p + s <= hi)
        swt = sum(1 for _, _, p in notes if slo <= p + s <= shi)
        cost = (out, -swt, abs(k))
        if best is None or cost < best[0]:
            best = (cost, s)
    return best[1] if best else 0


def _free_partner(role: str, function: str, taken: set, roles) -> str | None:
    from .orchestra import ROLE_TRAITS
    for r in ROLE_TRAITS.get(role, {}).get('partners', ()):
        if r in roles and r not in taken and ROLE_TRAITS.get(r, {}).get('functions', {}).get(function):
            return r
    return None


def orchestrate(score: OrchScore, table: dict, pick, rules: dict | None = None) -> Orchestration:
    """The parts of every block's lines (each block's texture and picks drawn: plan_blocks): table = the band's role
    table {role: {'range', 'sweet', ...}} (orch.role_table(preset) or band.info's); pick(block, key, weights) the
    dice for the doublings. Lines move by whole octaves into their role (RULES fit_octaves: the range first, then the
    sweet spot); a role carries one function per block (a voice whose role is taken goes to a free partner, else to
    the voice above's role as divisi); doublings by the slot's 'double' {role: (interval, chance)} on free roles, never
    under RULES doubling_floor."""
    R = dict(RULES, **(rules or {}))
    roles = set(table)
    out = Orchestration()
    floor = _n(R['doubling_floor'])
    for b in score.blocks:
        if b.texture is None:
            continue
        taken: set = set()
        for fn in ORDER:
            slots = needs(b.texture).get(fn)
            if not slots:
                continue
            lines = b.get(fn)
            if fn == 'colour':
                for i, s in enumerate(slots):
                    role = b.meta.get(f'colour{i}', 'none')
                    mine = [x for x in lines if x.meta.get('slot') == i]
                    if role == 'none' or role not in roles or not mine:
                        continue
                    for x in mine:
                        _place(out, b, x, role, s, table, R, fit=s.get('figure') not in ('hits', 'roll_end', 'crash'))
                    taken.add(role)
                continue
            slot = slots[0]
            if not lines:
                continue
            if 'pick' in slot and 'voices' not in slot:
                role = b.meta.get('lead') if fn == 'melody' else b.meta.get('counter') if fn == 'counter' else None
                if role is None:
                    av = {r: w for r, w in _avail(slot, roles).items() if r not in taken}
                    if not av and fn == 'bass':           # (the bass's roles all busy - the cellos sing: the
                        av = {r: _fn_weight(r, fn) for r in sorted(roles)       # free role best at it)
                              if r not in taken and _fn_weight(r, fn) >= 0.8}
                    role = pick(b.name, f'{fn}_role', av) if av else None
                if role in (None, 'none') or role not in roles:
                    continue
                placed = []
                for x in lines:
                    _place(out, b, x, role, slot, table, R)
                    placed.append(out.parts[-1].shift)
                taken.add(role)
                for dr, (iv, ch) in sorted((slot.get('double') or {}).items()):
                    if dr not in roles or dr in taken or not _chance(pick, b.name, f'{fn}_dbl_{dr}', ch):
                        continue
                    for x, sh in zip(lines, placed):          # (the interval from the line as its role plays it:
                        ns = [(a, d, p + sh + iv) for a, d, p in x.notes]   # r1 - 2nd violins over the 1st)
                        if ns and min(p for _, _, p in ns) < floor:
                            continue
                        lo, hi = (_n(v) for v in table[dr]['range'])
                        if any(not lo <= p <= hi for _, _, p in ns):      # (a doubling is never folded)
                            continue
                        dbl = Line('doubling', ns, voice=x.voice or fn, of=fn, art=x.art)
                        _place(out, b, dbl, dr, {'off': slot.get('off', 0.0)}, table, R, fit=False,
                               base=fn)
                    taken.add(dr)
                continue
            # real parts: voices top-down onto the slot's roles
            vroles = []
            for r in slot['voices']:
                if r not in roles or r in taken:
                    r2 = _free_partner(r, fn, taken | set(vroles), roles)
                    r = r2 if r2 is not None else (vroles[-1] if vroles else None)
                vroles.append(r)
            ordered = sorted(lines, key=lambda x: x.voice)
            used: list = []
            for i, x in enumerate(ordered):
                r = vroles[min(i, len(vroles) - 1)] if vroles else None
                if r is not None and not _covers(table[r], x.notes):
                    # the voice lies outside the role: another free role of the function that holds it (a
                    # partner first), else divisi on a role already playing this slot that holds it
                    alts = [q for q in _partners(r) + sorted(roles)
                            if q in roles and q not in taken and q not in vroles and q not in used
                            and _fn_weight(q, fn) and _covers(table[q], x.notes)]
                    alts += [q for q in used if _covers(table[q], x.notes)]
                    r = alts[0] if alts else r
                if r is None:
                    continue
                used.append(r)
                _place(out, b, x, r, slot, table, R, fit=False)
            taken.update(r for r in vroles + used if r)
        out.notes = sum(len(p.notes) for p in out.parts)
    return out


def _covers(t: dict, notes) -> bool:
    lo, hi = (_n(v) for v in t['range'])
    return all(lo <= p <= hi for _, _, p in notes)


def _partners(role) -> list:
    from .orchestra import ROLE_TRAITS
    return list(ROLE_TRAITS.get(role, {}).get('partners', ()))


def _fn_weight(role, fn) -> float:
    from .orchestra import ROLE_TRAITS
    return ROLE_TRAITS.get(role, {}).get('functions', {}).get(fn, 0.0)


def _place(out: Orchestration, b: Block, x: Line, role: str, slot: dict, table: dict, R: dict, fit: bool = True,
           base: str | None = None) -> None:
    """A line on a role: shifted (slot 'shift'), fitted by octaves (fit), folded where still outside the range."""
    t = table[role]
    sh = int(slot.get('shift', 0))
    ns = [(a, d, p + sh) for a, d, p in x.notes]
    if fit and ns:
        k = _fit(ns, t['range'], t['sweet'], R['fit_octaves'])
        ns = [(a, d, p + k) for a, d, p in ns]
        sh += k
    lo, hi = (_n(v) for v in t['range'])
    folded = []
    for a, d, p in ns:
        q = p
        while q > hi:
            q -= 12
        while q < lo:
            q += 12
        if q != p:
            out.folded += 1
        folded.append((a, d, q))
    F = FUNCTIONS[x.function]
    fn = base or x.function
    art = slot.get('art') or x.art or F['art'] or FUNCTIONS[fn]['art'] or 'sustain'
    if not t.get('arts'):                         # (a role without articulations - harp, percussion, choir: none)
        art = None
    elif art not in t['arts'] and art in ('hit', 'roll'):
        art = None
    line = F['line'] and FUNCTIONS[fn]['line']   # (a doubled bass / harmony stays accompaniment, 2 dB under it)
    off = (F['off'] if line or fn == x.function else FUNCTIONS[fn]['off'] - 2.0) + float(slot.get('off', 0.0))
    if not line:
        from .orchestra import ROLE_TRAITS
        off -= R.get('power_db', 0.0) * max(0.0, math.log2(ROLE_TRAITS.get(role, {}).get('power', 1.0)))
    out.parts.append(Part(role, b.name, x.function, x.voice, folded, art, off, line, sh))


# ------------------------------------------------------------------------------------------------ metrics

def _db(v: float) -> float:
    from .ensemble import db_of
    return db_of(max(1, v) / 127.0)


def metrics(sc, sections=None) -> dict:
    """The orchestration measures of an orch.Score (its written parts sc.parts and lines sc.lines, the band's
    ranges; any hand-written piece through orch.Score or an endless one) - {name: number}:
      range_out   notes outside their role's range per 100 notes (before the Score folds them)
      sweet_mel   share of the LINE notes inside their role's sweet spot
      gap_hi      share of beats whose sounding pitches above C4 leave a gap of more than an octave between
                  neighbours (close in the treble)
      low_thirds  share of beats whose two lowest sounding pitches (both under C3) are a 3rd or closer (wide in the bass)
      mel_db      median margin (dB, the lane's scale) of a line note over the loudest accompaniment note sounding with it
      colour_chg  share of section boundaries where the roles carrying the lines change
      tutti       share of bars where 75 %+ of the piece's roles sound
      coda_thin   roles in the last section / the most roles in any section
      roles_bar   mean roles sounding per bar; roles_sd its spread over the bars
      dbl_share   share of line notes doubled (unison / octave) by another role at the same onset
      dbl_low     share of those doublings under C3 (a melody doubled into the bass register)
      peak_x      the loudest 4-bar window's centre (0..1 of the piece, note energy)
      dyn_rng     note-energy range over 2-bar windows (p95 - p10, dB)
      textures    distinct role sets over the sections"""
    info = sc.band.info
    song = sc.song
    secs = list(sections if sections is not None else song.sections)
    meter = float(song.beats_per_bar)
    allp = [(role, n) for role, ns in sc.parts.items() for n in ns]
    if not allp:
        return {}
    total = len(allp)
    rng_ = {r: tuple(_n(x) for x in info.get('range', {}).get(r, ('C0', 'C9'))) for r in sc.parts}
    swt = {r: tuple(_n(x) for x in info.get('sweet', {}).get(r, info.get('range', {}).get(r, ('C0', 'C9'))))
           for r in sc.parts}
    out_n = sum(1 for r, n in allp if not rng_[r][0] <= n[2] <= rng_[r][1])
    lines = {r: s for r, s in sc.lines.items() if s}
    line_notes = [(r, n) for r, n in allp if (round(n[0], 4), n[2]) in lines.get(r, ())]
    sweet = [1 if swt[r][0] <= n[2] <= swt[r][1] else 0 for r, n in line_notes]
    end = max(n[0] + n[1] for _, n in allp)
    # sounding pitches on the beat grid (sustained notes; shorts count on their beat)
    by_beat: dict = {}
    for r, n in allp:
        a, d, p = n[0], max(n[1], 0.25), n[2]
        t = math.ceil(a - _EPS)
        while t < a + d - _EPS:
            by_beat.setdefault(t, set()).add(p)
            t += 1
    gap_hi = low3 = nb = 0
    for t, ps in by_beat.items():
        ps = sorted(ps)
        if len(ps) < 2:
            continue
        nb += 1
        hi_ = [p for p in ps if p >= 60]
        if any(b_ - a_ > 12 for a_, b_ in zip(hi_, hi_[1:])):
            gap_hi += 1
        if ps[0] < 48 and ps[1] < 48 and ps[1] - ps[0] <= 4:
            low3 += 1
    # the melody's margin
    acc = [(n[0], n[0] + n[1], n[3], r) for r, n in allp if (round(n[0], 4), n[2]) not in lines.get(r, ())
           and n[4] not in ('staccato', 'spiccato', 'pizzicato', 'marcato')
           and info.get('kind', {}).get(r, 'sustain') == 'sustain']
    acc.sort()
    margins = []
    import bisect
    starts = [x[0] for x in acc]
    longest = max((e - a for a, e, _, _ in acc), default=0.0)
    for r, n in line_notes:
        k = bisect.bisect_right(starts, n[0] + _EPS)
        vs = [v for a, e, v, r2 in acc[bisect.bisect_left(starts, n[0] - longest - _EPS):k]
              if r2 != r and a <= n[0] + _EPS < e]
        if vs:
            margins.append(_db(n[3]) - _db(max(vs)))
    # roles per section / bar
    def roles_in(a, z):
        return {r for r, n in allp if n[0] < z - _EPS and n[0] + n[1] > a + _EPS}
    sec_roles = [(s.name, roles_in(s.start, s.end), {r for r, n in line_notes if s.start - _EPS <= n[0] < s.end - _EPS})
                 for s in secs if s.length > 0]
    chg = [1 if a[2] and b_[2] and a[2] != b_[2] else 0 for a, b_ in zip(sec_roles, sec_roles[1:])
           if a[2] and b_[2]]
    used = {r for r, _ in allp}
    nbar = max(1, int(math.ceil(end / meter - _EPS)))
    per_bar = [len(roles_in(i * meter, (i + 1) * meter)) for i in range(nbar)]
    sounding = [x for x in per_bar if x]
    tutti = sum(1 for x in sounding if x >= 0.75 * len(used)) / max(1, len(sounding))
    maxr = max((len(x[1]) for x in sec_roles), default=1)
    coda = len(sec_roles[-1][1]) / max(1, maxr) if sec_roles else 1.0
    # doublings
    onset = {}
    for r, n in allp:
        onset.setdefault(round(n[0], 2), []).append((r, n[2]))
    dbl = dlow = 0
    for r, n in line_notes:
        others = [(r2, p) for r2, p in onset.get(round(n[0], 2), ()) if r2 != r and p % 12 == n[2] % 12]
        if others:
            dbl += 1
            if min(p for _, p in others) < 48:
                dlow += 1
    # energy: the climax place and the range
    e_bar = [0.0] * nbar
    for r, n in allp:
        i = min(nbar - 1, int(n[0] // meter))
        e_bar[i] += (n[3] / 127.0) ** 2.5
    db_bar = [10 * math.log10(max(e, 1e-4)) for e in e_bar]
    w4 = [(sum(e_bar[i:i + 4]), i) for i in range(max(1, nbar - 3))]
    peak_i = max(w4)[1] if w4 else 0
    w2 = sorted(10 * math.log10(max(1e-4, sum(e_bar[i:i + 2]) / 2)) for i in range(0, max(1, nbar - 1), 2))
    rngdb = w2[min(len(w2) - 1, int(0.95 * len(w2)))] - w2[int(0.1 * len(w2))] if w2 else 0.0
    sets = {frozenset(x[1]) for x in sec_roles}
    return {
        'range_out': round(100.0 * out_n / total, 2),
        'sweet_mel': round(sum(sweet) / len(sweet), 3) if sweet else None,
        'gap_hi': round(gap_hi / max(1, nb), 3),
        'low_thirds': round(low3 / max(1, nb), 3),
        'mel_db': round(st.median(margins), 2) if margins else None,
        'colour_chg': round(sum(chg) / len(chg), 3) if chg else None,
        'tutti': round(tutti, 3),
        'coda_thin': round(coda, 3),
        'roles_bar': round(st.mean(sounding), 2) if sounding else 0.0,
        'roles_sd': round(st.pstdev(sounding), 2) if len(sounding) > 1 else 0.0,
        'dbl_share': round(dbl / max(1, len(line_notes)), 3),
        'dbl_low': round(dlow / max(1, dbl), 3),
        'peak_x': round((peak_i * meter + 2 * meter) / max(meter, end), 3),
        'dyn_rng': round(rngdb, 1),
        'textures': len(sets),
        'roles_used': len(used),
        'db_bar_sd': round(st.pstdev(db_bar), 2) if len(db_bar) > 1 else 0.0,
    }
