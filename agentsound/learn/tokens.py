"""The learned generator's token schema: an endless Tune (the composer's lead sheet, what the players get) <-> a flat
list of string tokens. Composition level only - the players (endless.perform) keep doing the left hand, voicings,
ornaments, touch and timing; no velocities here.

The sequence (one piece):

    BOS
    header   Mood_* Feel_* Form_* Meter_* Key_<tonic> Mode_* Tempo_<bpm> Swing_* Energy_<x1000>
    plan     Dyn_* SoloShape_* Double_* Shout_* EndKind_* Second_* ReharmIn_*
             OutParts Part_* ... EndList   SoloCharts Part_* ... EndList
             Climax Part_* U_<unit> Bn_<bar> Pos_<12ths> P_<pitch>      (or Climax_none)
             EndChord <chord>
    arrange  Arr [ALayout_*] [ATouch_*] (ASec_<name> <key tokens>)* EndArr   (or Arr_none; schema 2 only)
    harmony  H Part_<p> Blk_* ... <chord> L_<12ths> ... EndH            one per head part (in form order)
             HIntro IKind_* ILine_* IAppr_* IFrame_* <chord> L_* ... EndH   (or HIntro_none); HTag ... the same
             HSolo Part_<p> <chord> L_* ... EndH                       the reharm (tune.solo_changes), per part
    notes    M Part_<p> <bars> EndM                                     the head melody, per part
             MOut Part_<p> <bars> EndM                                  tune.out_melody (where it differs)
             MIntro <bars> EndM   MTag <bars> EndM
             Motif (Ref_<n> | <bars> EndM)    Counter (Ref_<part>_<n> | CRef_none | <bars> EndM)
    EOS

<chord> = Root_<roman> Q_<quality> [Bass_<roman>]: the root as a roman numeral of the key's tonic WITH its spelling
(the letter degree + accidentals: bII = the flat second spelled on the next letter, Cb in Bb major), so the symbol
comes back letter-exact. <bars> = per bar 'Bar' (BarPre first for a pickup before beat 0), then per note
Pos_<12ths in the bar> P_<pitch - tonic pc> D_<12ths>. Times are on a 1/12-beat grid (8ths, 16ths, triplets).
The levels (the arc plan per 2-bar phrase) are not tokens: the decoder computes them as the composer does (the form's
tension curve + the energy). Not tokenized: the title (drawn again), the seed (the players' dice: decode(seed=)) and
the composer's retry count.

The arrange block (schema 2, SCHEMA) is the players' arrangement record (endless.arrangement; perform.arrange draws it,
perform.build plays it): the piece's keys (ALayout_<layout>, ATouch_<lo,hi>), then per section played - in play
order - 'ASec_<name>' (a piano plan['sections'] name of the layout; jazz: intro / head:<part> / solo / out:<label> /
tag) and its keys in ARR_FIELDS order as '<prefix>_<value>' (a list key - ASw_ hairpins, AStep_ phrase steps,
AMove_ a waltz's moving bars - one token per item). Values are the arrangement's own names / numbers (arrangement.fmt: bools 1 / 0, tuples 'a,b', nested 'a-b,c-d'); the decoder admits
only the player genre's vocabulary (arrangement.values). A piano section's keys equal to its plan entry's (dyn,
figures, rit ...: arrangement.PIANO_FIXED) are left out and filled back, so the teacher data holds only the drawn ones.
decode() hangs the record on the Tune (tune.arrangement; None for Arr_none / a schema-1 sequence: the players draw
it). Schema 1 = the checkpoints from before the block (no Arr tokens in their vocabulary: grammar / decode read
both; encode(tune) without an arrangement writes schema 1).
"""
from __future__ import annotations

import math
import random
import re

LETTERS = 'CDEFGAB'
NATURAL = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
MAJOR = (0, 2, 4, 5, 7, 9, 11)
ROMANS = ('I', 'II', 'III', 'IV', 'V', 'VI', 'VII')
ACC = {-3: 'bbb', -2: 'bb', -1: 'b', 0: '', 1: '#', 2: '##', 3: '###'}
GRID = 12
_SYM = re.compile(r'^([A-G](?:bb|##|b|#)?)(.*?)(?:/([A-G](?:bb|##|b|#)?))?$')
_RN = re.compile(r'^(bbb|###|bb|##|b|#)?(VII|VI|IV|V|III|II|I)$')


class TokenError(ValueError):
    """A token sequence that does not decode to a tune (the model's invalid output)."""


def name_pc(name: str) -> int:
    return (NATURAL[name[0]] + name.count('#') - name.count('b')) % 12


def roman(name: str, tonic: str) -> str:
    """A spelled note name relative to the tonic: 'Cb' in Bb -> 'bII', 'F#' in C -> '#IV'."""
    d = (LETTERS.index(name[0]) - LETTERS.index(tonic[0])) % 7
    acc = (name_pc(name) - name_pc(tonic) - MAJOR[d]) % 12
    acc = acc - 12 if acc > 6 else acc
    if acc not in ACC:
        raise TokenError(f"cannot spell {name} against {tonic}")
    return ACC[acc] + ROMANS[d]


def unroman(rn: str, tonic: str) -> str:
    m = _RN.match(rn)
    if not m:
        raise TokenError(f"bad roman {rn!r}")
    acc = {v: k for k, v in ACC.items()}[m.group(1) or '']
    d = ROMANS.index(m.group(2))
    letter = LETTERS[(LETTERS.index(tonic[0]) + d) % 7]
    target = (name_pc(tonic) + MAJOR[d] + acc) % 12
    a = (target - NATURAL[letter]) % 12
    a = a - 12 if a > 6 else a
    if a not in ACC:
        raise TokenError(f"cannot spell {rn} in {tonic}")
    return letter + ACC[a]


def q12(x: float) -> int:
    k = round(x * GRID)
    if abs(k - x * GRID) > 1e-4:
        raise TokenError(f"{x} is off the 1/{GRID}-beat grid")
    return k


def chord_tokens(sym: str, tonic: str) -> list[str]:
    m = _SYM.match(sym)
    if not m:
        raise TokenError(f"unparsed chord {sym!r}")
    root, q, bass = m.groups()
    out = [f"Root_{roman(root, tonic)}", f"Q_{q}"]
    if bass:
        out.append(f"Bass_{roman(bass, tonic)}")
    return out


# ------------------------------------------------------------------------------------------------ encode

def _bars(notes, meter: int, tonic_pc: int) -> list[str]:
    """Notes (start, dur, pitch) -> Bar / Pos / P / D tokens (bar 0 = the part's first bar; BarPre: before it)."""
    out: list[str] = []
    bar = None
    span = meter * GRID
    for st, du, p in notes:
        k = q12(st)
        b = math.floor(k / span)
        if bar is None:
            bar = -1 if b < 0 else 0
            out.append('BarPre' if b < 0 else 'Bar')
        if b < bar:
            raise TokenError(f"melody not in time order at beat {st}")
        if b < -1:
            raise TokenError(f"pickup longer than a bar at beat {st}")
        while bar < b:
            bar += 1
            out.append('Bar')
        out += [f"Pos_{k - b * span}", f"P_{p - tonic_pc}", f"D_{q12(du)}"]
    return out


def _changes(ch, tonic: str) -> list[str]:
    out = []
    for sym, beats in ch:
        out += chord_tokens(sym, tonic) + [f"L_{q12(beats)}"]
    return out


def _ref(notes, sources: dict) -> str | None:
    """'Ref_<part>_<n>' when `notes` are the first n notes of one source melody (motif / counter), else None."""
    n = len(notes)
    for name, mel in sources.items():
        if n and list(map(tuple, mel[:n])) == list(map(tuple, notes)):
            return f"Ref_{name}_{n}"
    return None


SCHEMA = 2
"""The current schema: 2 = with the Arr block (1: the checkpoints before it - no block; decode reads both)."""
ARR_PIECE = (('layout', 'ALayout'), ('touch', 'ATouch'), ('rubato', 'ARubato'), ('inhale', 'AInhale'),
             ('lilt', 'ALilt'), ('breath', 'ABreath'), ('push', 'APush'), ('inner', 'AInner'), ('cap', 'ACap'),
             ('lh_vel', 'ALhVel'), ('pedal', 'APedal'), ('end_dyn', 'AEndDyn'), ('end_roll', 'AEndRoll'),
             ('end_hold', 'AEndHold'), ('size', 'ASize'))
ARR_FIELDS = (('melody', 'AMel'), ('dyn', 'ADyn'), ('figures', 'AFig'), ('harmonize', 'AHarm'),
              ('harm_share', 'AHShare'), ('tempo', 'ATempo'), ('rit', 'ARit'), ('fermata', 'AFerm'),
              ('keep_bars', 'AKeep'), ('lh_only', 'ALhOnly'), ('peak', 'APeak'), ('drums', 'ADrums'),
              ('octave', 'AOct'), ('climax', 'AClimax'), ('reharm', 'AReharm'), ('bars', 'ABars'), ('tail', 'ATail'),
              ('cadence', 'ACad'), ('bass', 'ABass'), ('octave_half', 'AOctHalf'), ('fill', 'AFill'),
              ('turn', 'ATurn'), ('swell', 'ASw'), ('cadenza', 'ACadenza'), ('moves', 'AMove'), ('lh', 'ALH'),
              ('steps', 'AStep'), ('choruses', 'AChorus'), ('opening', 'AOpen'), ('quotes', 'AQuote'),
              ('over', 'AOver'), ('window', 'AWin'), ('burst', 'ABurst'), ('vary', 'AVary'), ('key', 'AKey'),
              ('texture', 'ATex'), ('lead', 'ALead'), ('counter', 'ACtr'))
"""The Arr block's keys (endless.arrangement) in token order: the piece's, then per section (a list key: one token
per item). The orchestra's (kind 'orchestra': the piano plan's keys + the orchestrator's size / texture / lead /
counter) come last: a piano / jazz genre's vocabulary is unchanged."""
PLAN_KINDS = ('piano', 'orchestra')
"""The kinds that play a piano plan (sections from plan['sections'], keys equal to the plan entry left out)."""


def arrangement_tokens(genres) -> set[str]:
    """Every Arr-block token the genres' players can take (arrangement.values + their section names) - the student's
    vocabulary holds them all, not only those the teacher data happens to draw (a key fixed by the plan, AFig_* on a
    section, is never in the data)."""
    from ..endless.arrangement import kind_of, section_specs, values
    from ..endless.genres import FORMS
    from ..endless.genres import get as get_genre
    out = {'Arr', 'Arr_none', 'EndArr'}
    for name in genres:
        g = get_genre(name) if isinstance(name, str) else name
        if kind_of(g) not in PLAN_KINDS + ('jazz',):
            continue
        vals = values(g)
        for key, pre in ARR_PIECE + ARR_FIELDS:
            out.update(f"{pre}_{v}" for v in vals.get(key, {}))
        if kind_of(g) in PLAN_KINDS:
            out.update(f"ASec_{n}" for n in section_specs(g, None))
            for lay in vals.get('layout', {}).values():
                out.update(f"ASec_{n}" for n in section_specs(g, lay))
        else:
            out.update(f"ASec_{n}" for n in ('intro', 'solo', 'tag'))
            for form in g.forms:
                for p in FORMS[form]['parts']:
                    out.update((f"ASec_head:{p}", f"ASec_out:{p}", f"ASec_out:{p}v"))
    return out


def schema_of(tokens) -> int:
    """The schema of a token sequence or a vocabulary's tokens (2 when it has the Arr block's tokens)."""
    return 2 if any(t in ('Arr', 'Arr_none') for t in tokens) else 1


def _arr_tokens(arr, genre) -> list[str]:
    """An arrangement record -> its Arr block; a piano section's keys equal to its plan entry's are left out (the
    decoder fills them back: arrangement.fixed)."""
    from ..endless.arrangement import LISTS, fixed, fmt, section_specs, values
    if arr is None:
        return ['Arr_none']
    vals = values(genre)
    known = {k for k, _ in ARR_PIECE + ARR_FIELDS}

    def tok(key, pre, v):
        f = fmt(v)
        if f not in vals.get(key, {}) or ' ' in f:
            raise TokenError(f"arrangement {key} = {v!r}: not in {genre.name}'s vocabulary")
        return f"{pre}_{f}"
    t = ['Arr']
    for key, pre in ARR_PIECE:
        if key in arr.piece:
            t.append(tok(key, pre, arr.piece[key]))
    for name, d in arr.sections.items():
        if arr.kind in PLAN_KINDS and name not in section_specs(genre, arr.piece.get('layout')):
            raise TokenError(f"arrangement section {name!r} not in {genre.name}")
        bad = set(d) - known
        if bad:
            raise TokenError(f"arrangement section {name}: unknown keys {sorted(bad)}")
        t.append(f"ASec_{name}")
        spec = fixed(genre, name, arr.piece.get('layout')) if arr.kind in PLAN_KINDS else {}
        for key, pre in ARR_FIELDS:
            if key not in d or (key in spec and spec[key] == d[key]):
                continue
            t += [tok(key, pre, v) for v in (d[key] if key in LISTS else [d[key]])]
    return t + ['EndArr']


def encode(tune, arrangement=None, schema: int | None = None) -> list[str]:
    """A Tune -> tokens (raises TokenError for what the schema cannot hold). arrangement: the players' record
    (endless.perform.arrange) -> the Arr block (schema 2; default schema: 2 with an arrangement, else 1 - no block;
    schema 2 without one: Arr_none)."""
    schema = schema or (2 if arrangement is not None else 1)
    tonic, mode = tune.key.split()
    tpc = name_pc(tonic)
    t = ['BOS', f"Mood_{tune.mood}", f"Feel_{tune.feel}", f"Form_{tune.form}", f"Meter_{tune.meter}",
         f"Key_{tonic}", f"Mode_{mode}", f"Tempo_{int(tune.tempo)}",
         'Swing_none' if not tune.swing else f"Swing_{round(float(tune.swing) * 100)}",
         f"Energy_{round(float(tune.energy) * 1000)}",
         f"Dyn_{tune.dynamics}", f"SoloShape_{tune.solo_shape}", f"Double_{int(bool(tune.double))}",
         f"Shout_{int(bool(tune.shout))}", f"EndKind_{tune.end_kind}", f"Second_{tune.second}",
         f"ReharmIn_{tune.reharm_in}"]
    t += ['OutParts'] + [f"Part_{p}" for p in tune.out_parts] + ['EndList']
    t += ['SoloCharts'] + [f"Part_{p}" for p in tune.solo_charts] + ['EndList']
    c = tune.climax
    if c:
        k = q12(c['beat'])
        t += ['Climax', f"Part_{c['part']}", f"U_{c['unit']}", f"Bn_{k // (tune.meter * GRID)}",
              f"Pos_{k % (tune.meter * GRID)}", f"P_{c['pitch'] - tpc}"]
    else:
        t.append('Climax_none')
    t += ['EndChord'] + chord_tokens(tune.end_chord, tonic)
    if schema >= 2:
        from ..endless.genres import get as get_genre
        t += _arr_tokens(arrangement, get_genre(tune.genre))
    for p in tune.parts:
        t += ['H', f"Part_{p}"] + [f"Blk_{b}" for b in (tune.blocks or {}).get(p, [])] + \
             _changes(tune.changes[p], tonic) + ['EndH']
    for kind, fr in (('Intro', tune.intro), ('Tag', tune.tag)):
        if fr:
            t += [f"H{kind}", f"IKind_{fr.get('kind')}", f"ILine_{fr.get('line')}", f"IAppr_{fr.get('approach')}",
                  f"IFrame_{fr.get('frame')}"] + _changes(fr['changes'], tonic) + ['EndH']
        else:
            t.append(f"H{kind}_none")
    for p in tune.parts:
        if p in (tune.solo_changes or {}):
            t += ['HSolo', f"Part_{p}"] + _changes(tune.solo_changes[p], tonic) + ['EndH']
    for p in tune.parts:
        t += ['M', f"Part_{p}"] + _bars(tune.melody[p], tune.meter, tpc) + ['EndM']
    for p in tune.parts:
        if p in (tune.out_melody or {}):
            t += ['MOut', f"Part_{p}"] + _bars(tune.out_melody[p], tune.meter, tpc) + ['EndM']
    for kind, fr in (('Intro', tune.intro), ('Tag', tune.tag)):
        if fr:
            t += [f"M{kind}"] + _bars(fr.get('melody') or [], tune.meter, tpc) + ['EndM']
    srcs = {p: tune.melody[p] for p in tune.parts}
    srcs.update({f"out{p}": m for p, m in (tune.out_melody or {}).items()})
    for kind, notes in (('Motif', tune.motif), ('Counter', tune.counter)):
        r = _ref(notes, srcs)
        if r:
            t += [kind, r]
        elif not notes:
            t += [kind, 'Ref_none']
        else:
            t += [kind] + _bars(notes, tune.meter, tpc) + ['EndM']
    t.append('EOS')
    return t


# ------------------------------------------------------------------------------------------------ decode

class _Reader:
    def __init__(self, toks):
        self.t, self.i = list(toks), 0

    def peek(self, k: int = 0) -> str:
        return self.t[self.i + k] if self.i + k < len(self.t) else 'EOS'

    def take(self, prefix: str | None = None) -> str:
        if self.i >= len(self.t):
            raise TokenError(f"sequence ended, wanted {prefix}")
        x = self.t[self.i]
        if prefix is not None and not (x == prefix or x.startswith(prefix + '_')):
            raise TokenError(f"token {self.i}: wanted {prefix}, got {x}")
        self.i += 1
        return x

    def val(self, prefix: str) -> str:
        return self.take(prefix)[len(prefix) + 1:]

    def int(self, prefix: str) -> int:
        v = self.val(prefix)
        try:
            return int(v)
        except ValueError:
            raise TokenError(f"{prefix}_{v}: not a number") from None

    def opt(self, prefix: str):
        v = self.val(prefix)
        return None if v == 'None' else v


def _chord(r: _Reader, tonic: str) -> str:
    sym = unroman(r.val('Root'), tonic) + r.val('Q')
    if r.peek().startswith('Bass_'):
        sym += '/' + unroman(r.val('Bass'), tonic)
    return sym


def _read_changes(r: _Reader, tonic: str) -> list:
    out = []
    while r.peek() != 'EndH':
        sym = _chord(r, tonic)
        n = r.int('L')
        if n <= 0:
            raise TokenError('a chord of no length')
        out.append((sym, n / GRID))
    r.take('EndH')
    return out


def _read_bars(r: _Reader, meter: int, tpc: int, end: str = 'EndM') -> list:
    span = meter * GRID
    notes, bar = [], None
    while r.peek() != end:
        x = r.take()
        if x == 'BarPre':
            if bar is not None:
                raise TokenError('BarPre after the first bar')
            bar = -1
        elif x == 'Bar':
            bar = 0 if bar is None else bar + 1
        elif x.startswith('Pos_'):
            if bar is None:
                raise TokenError('a note before its bar')
            pos = int(x[4:])
            if not 0 <= pos < span:
                raise TokenError(f"position {pos} outside the bar")
            p = r.int('P') + tpc
            d = r.int('D')
            if d <= 0 or not 0 <= p <= 127:
                raise TokenError('a bad note')
            notes.append(((bar * span + pos) / GRID, d / GRID, p))
        else:
            raise TokenError(f"unexpected {x} in a melody")
    r.take(end)
    return notes


def _read_arr(r: _Reader, g, parts: list):
    """The Arr block -> an Arrangement (None for Arr_none / no block: schema 1), strictly: every value one of the
    player genre's (arrangement.values), every section one its players know, the keys in ARR_FIELDS order; a piano
    section's keys its tokens leave out filled from its plan entry."""
    from ..endless.arrangement import LISTS, Arrangement, fixed, kind_of, section_ok, values
    if r.peek() == 'Arr_none':
        r.take()
        return None
    if r.peek() != 'Arr':
        return None
    r.take('Arr')
    kind = kind_of(g)
    if kind not in PLAN_KINDS + ('jazz',):
        raise TokenError(f"{g.name}'s players take no arrangement")
    vals = values(g)
    arr = Arrangement(kind)

    def value(key, pre):
        v = r.val(pre)
        if v not in vals.get(key, {}):
            raise TokenError(f"{pre}_{v}: not a {g.name} {key}")
        return vals[key][v]
    for key, pre in ARR_PIECE:
        if r.peek().startswith(pre + '_'):
            arr.piece[key] = value(key, pre)
    order = [pre for _, pre in ARR_FIELDS]
    while r.peek() != 'EndArr':
        name = r.val('ASec')
        if name in arr.sections or not section_ok(g, parts, name, arr.piece.get('layout')):
            raise TokenError(f"arrangement section {name!r}: unknown to {g.name} or twice")
        d = arr.sections[name] = {}
        last = -1
        while r.peek() not in ('EndArr', 'EOS') and not r.peek().startswith('ASec_'):
            pre = r.peek().partition('_')[0]
            if pre not in order:
                raise TokenError(f"token {r.i}: {r.peek()} in the arrangement")
            i = order.index(pre)
            key = ARR_FIELDS[i][0]
            if i < last or (i == last and key not in LISTS):
                raise TokenError(f"token {r.i}: {pre} out of order")
            last = i
            v = value(key, pre)
            if key in LISTS:
                d.setdefault(key, []).append(v)
            else:
                d[key] = v
        if kind in PLAN_KINDS:
            for k, v in fixed(g, name, arr.piece.get('layout')).items():
                d.setdefault(k, v)
    r.take('EndArr')
    return arr


def levels_for(genre, form: str, meter: int, energy: float, second) -> dict:
    """The arc level of every 2-bar phrase per part, as composer.compose computes them (the form's tension curve +
    the energy bias; a blues' 'early' second chorus reads the curve with its choruses swapped)."""
    from ..endless.composer import arc_at, phrase_plans
    from ..endless.genres import FORMS
    order = list(FORMS[form]['parts'])
    pl = phrase_plans(genre, meter)
    plans = {p: pl['blues' if form == 'blues' else p[0]] for p in order}
    curve = genre.arc['forms'][form]
    bias = (energy - 0.5) * genre.arc['set'].get('energy_bias', 0.0)
    swap = 0.5 if second == 'early' else 0.0
    return {p: [min(1.0, max(0.0, arc_at(curve, ((i + (u + 0.5) / len(plans[p])) / len(order) + swap) % 1.0) + bias))
                for u in range(len(plans[p]))] for i, p in enumerate(order)}


def decode(tokens, genre, seed: int = 0, title: str | None = None):
    """Tokens -> a Tune for `genre` (an endless Genre or its name: whose players perform it; its forms / feels /
    moods must hold the header's). seed: the players' dice. Raises TokenError for an invalid sequence."""
    from ..endless.composer import Tune
    from ..endless.composer import title as draw_title
    from ..endless.genres import FORMS
    from ..endless.genres import get as get_genre
    g = get_genre(genre) if isinstance(genre, str) else genre
    r = _Reader(tokens)
    r.take('BOS')
    mood, feel, form = r.val('Mood'), r.val('Feel'), r.val('Form')
    meter = r.int('Meter')
    tonic, mode = r.val('Key'), r.val('Mode')
    if tonic[:1] not in NATURAL or mode not in ('major', 'minor'):
        raise TokenError(f"bad key {tonic} {mode}")
    tpc = name_pc(tonic)
    tempo = r.int('Tempo')
    sw = r.val('Swing')
    swing = None if sw == 'none' else int(sw) / 100
    energy = r.int('Energy') / 1000
    if form not in FORMS or form not in g.forms:
        raise TokenError(f"form {form} not in {g.name}")
    if feel not in g.feels:
        raise TokenError(f"feel {feel} not in {g.name}")
    if mood not in g.moods:
        raise TokenError(f"mood {mood} not in {g.name}")
    parts = list(FORMS[form]['parts'])
    dyn, solo_shape = r.val('Dyn'), r.opt('SoloShape')
    double, shout = bool(r.int('Double')), bool(r.int('Shout'))
    end_kind, second, reharm_in = r.val('EndKind'), r.opt('Second'), r.val('ReharmIn')

    def plist(head):
        r.take(head)
        out = []
        while r.peek() != 'EndList':
            out.append(r.val('Part'))
        r.take('EndList')
        return out
    out_parts, solo_charts = plist('OutParts'), plist('SoloCharts')
    climax = {}
    if r.peek() == 'Climax_none':
        r.take()
    else:
        r.take('Climax')
        cp, cu, cb = r.val('Part'), r.int('U'), r.int('Bn')
        pos = r.int('Pos')
        climax = {'part': cp, 'unit': cu, 'beat': (cb * meter * GRID + pos) / GRID, 'pitch': r.int('P') + tpc}
    r.take('EndChord')
    end_chord = _chord(r, tonic)
    arrangement = _read_arr(r, g, parts)
    changes, blocks = {}, {}
    while r.peek() == 'H':
        r.take('H')
        p = r.val('Part')
        blocks[p] = []
        while r.peek().startswith('Blk_'):
            blocks[p].append(r.val('Blk'))
        changes[p] = _read_changes(r, tonic)
    if list(changes) != parts:
        raise TokenError(f"harmony parts {list(changes)} != the form's {parts}")
    frames = {}
    for kind in ('Intro', 'Tag'):
        if r.peek() == f"H{kind}_none":
            r.take()
            frames[kind] = {}
            continue
        r.take(f"H{kind}")
        fr = {'kind': r.opt('IKind'), 'line': r.opt('ILine')}
        fr['changes'] = None
        appr, frame = r.opt('IAppr'), r.opt('IFrame')
        fr = {'kind': fr['kind'], 'line': fr['line'], 'changes': _read_changes(r, tonic), 'approach': appr,
              'frame': frame}
        frames[kind] = fr
    solo_changes = {}
    while r.peek() == 'HSolo':
        r.take('HSolo')
        p = r.val('Part')
        solo_changes[p] = _read_changes(r, tonic)
    melody = {}
    while r.peek() == 'M':
        r.take('M')
        p = r.val('Part')
        melody[p] = _read_bars(r, meter, tpc)
    if list(melody) != parts:
        raise TokenError(f"melody parts {list(melody)} != the form's {parts}")
    out_melody = {}
    while r.peek() == 'MOut':
        r.take('MOut')
        p = r.val('Part')
        out_melody[p] = _read_bars(r, meter, tpc)
    for kind in ('Intro', 'Tag'):
        if frames[kind]:
            r.take(f"M{kind}")
            frames[kind]['melody'] = _read_bars(r, meter, tpc)
            fr = frames[kind]
            frames[kind] = {'kind': fr['kind'], 'line': fr['line'], 'changes': fr['changes'],
                            'approach': fr['approach'], 'frame': fr['frame'], 'melody': fr['melody']}
    srcs = dict(melody)
    srcs.update({f"out{p}": m for p, m in out_melody.items()})
    refs = {}
    for kind in ('Motif', 'Counter'):
        r.take(kind)
        if r.peek().startswith('Ref_'):
            v = r.val('Ref')
            if v == 'none':
                refs[kind] = []
            else:
                src, _, n = v.rpartition('_')
                if src not in srcs or not n.isdigit():
                    raise TokenError(f"bad reference {v}")
                refs[kind] = list(srcs[src][:int(n)])
        else:
            refs[kind] = _read_bars(r, meter, tpc)
    r.take('EOS')
    for p in list(out_parts) + list(solo_charts) + list(solo_changes) + list(out_melody) + \
            ([climax['part']] if climax else []):
        if p not in parts:
            raise TokenError(f"part {p} not in the form")
    key = f"{tonic} {mode}"
    tt = title or draw_title(random.Random(f"learn-title:{seed}"), feel, form, g.titles, key)
    tune = Tune(genre=g.name, seed=seed, mood=mood, title=tt, key=key, mode=mode, tempo=tempo, meter=meter,
                feel=feel, swing=swing, form=form, parts=parts, changes=changes, melody=melody,
                motif=refs['Motif'], intro=frames['Intro'], tag=frames['Tag'], end_chord=end_chord, blocks=blocks,
                retries=0, energy=energy, levels=levels_for(g, form, meter, energy, second), climax=climax,
                counter=refs['Counter'], solo_changes=solo_changes, out_melody=out_melody, shout=shout,
                dynamics=dyn, solo_shape=solo_shape, double=double, solo_charts=solo_charts, end_kind=end_kind,
                second=second, out_parts=out_parts, reharm_in=reharm_in)
    tune.arrangement = arrangement             # (the Arr block's record, None without one: perform.build plays it)
    return tune


# ------------------------------------------------------------------------------------------------ helpers

def same_arrangement(a, b) -> bool:
    """Two arrangement records equal, the section order included."""
    return a == b and (a is None or list(a.sections) == list(b.sections))


def diff(a, b, tol: float = 1e-6) -> list[str]:
    """What differs between two tunes at composition level ([] = note-identical): header, plan, every chord, every
    melody note (times within tol)."""
    out = []
    for k in ('mood', 'key', 'mode', 'tempo', 'meter', 'feel', 'form', 'parts', 'end_chord', 'shout', 'dynamics',
              'solo_shape', 'double', 'solo_charts', 'end_kind', 'second', 'out_parts', 'reharm_in', 'blocks'):
        if getattr(a, k) != getattr(b, k):
            out.append(f"{k}: {getattr(a, k)!r} != {getattr(b, k)!r}")
    if (a.swing or None) != (b.swing or None) and abs((a.swing or 0) - (b.swing or 0)) > 0.005:
        out.append(f"swing {a.swing} != {b.swing}")
    if abs(a.energy - b.energy) > 1e-9:
        out.append(f"energy {a.energy} != {b.energy}")

    def notes_eq(x, y):
        return len(x) == len(y) and all(abs(p[0] - q[0]) < tol and abs(p[1] - q[1]) < tol and p[2] == q[2]
                                        for p, q in zip(x, y))

    def ch_eq(x, y):
        return len(x) == len(y) and all(p[0] == q[0] and abs(p[1] - q[1]) < tol for p, q in zip(x, y))
    for p in a.parts:
        if not ch_eq(a.changes[p], b.changes.get(p, [])):
            out.append(f"changes {p}")
        if not notes_eq(a.melody[p], b.melody.get(p, [])):
            out.append(f"melody {p}")
    for name in ('solo_changes', 'out_melody'):
        da, db = getattr(a, name) or {}, getattr(b, name) or {}
        if set(da) != set(db):
            out.append(f"{name} parts {sorted(da)} != {sorted(db)}")
        for p in da:
            if p in db and not (ch_eq if name == 'solo_changes' else notes_eq)(da[p], db[p]):
                out.append(f"{name} {p}")
    for name in ('intro', 'tag'):
        fa, fb = getattr(a, name) or {}, getattr(b, name) or {}
        if bool(fa) != bool(fb):
            out.append(f"{name} present {bool(fa)} != {bool(fb)}")
        elif fa:
            for k in ('kind', 'line', 'approach', 'frame'):
                if fa.get(k) != fb.get(k):
                    out.append(f"{name}.{k}")
            if not ch_eq(fa['changes'], fb['changes']) or not notes_eq(fa.get('melody') or [], fb.get('melody') or []):
                out.append(f"{name} notes")
    for name in ('motif', 'counter'):
        if not notes_eq(getattr(a, name) or [], getattr(b, name) or []):
            out.append(name)
    ca, cb = a.climax or {}, b.climax or {}
    if set(ca) != set(cb) or any(ca[k] != cb[k] if k != 'beat' else abs(ca[k] - cb[k]) > tol for k in ca):
        out.append(f"climax {ca} != {cb}")
    ra, rb = getattr(a, 'arrangement', None), getattr(b, 'arrangement', None)
    if ra is not None and rb is not None and not same_arrangement(ra, rb):
        out.append(f"arrangement {ra} != {rb}")
    for p in a.parts:
        la, lb = (a.levels or {}).get(p, []), (b.levels or {}).get(p, [])
        if len(la) != len(lb) or any(abs(x - y) > 1e-3 for x, y in zip(la, lb)):
            out.append(f"levels {p}")
    return out
