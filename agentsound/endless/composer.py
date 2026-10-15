"""The endless tune composer: a seeded, rule-based lead sheet (form, key, tempo, feel, changes, melody) - no LLM.

    tune = compose(genres.get('jazz-piano'), seed=7, mood='late-night')
    print(tune.describe())                  # title, key, tempo, form, feel, the changes per part
    tune.melody_clip('A1')                  # the head's melody of a part (a Clip, part beats)

Form and feel: the form is drawn first, then a feel that suits it (genres.FEEL_FORMS: a blues swings or is a
straight-8th shuffle, a bossa wants a song form); a set plan may pin the feel or the form.
Harmony: the genre's BLOCKS (ii-V-I chains, turnarounds, backdoor, tritone, secondary dominants, IV / relative-minor /
bIII bridges, blues) assembled per part, the abstract qualities coloured from COLOURS by where each chord goes, a
dominant now and then swapped for its tritone substitute (the mood's 'tritone' chance); a blues head's second chorus
plays its turnaround / cadence another way (its second ending: variant(), a CHART_VARIANTS kind, drawn) and the solo
choruses play the one or the other chart (Tune.solo_charts).
Melody: the PERIOD PLAN first - a contour drawn per part kind (genres.CONTOURS: every 4-bar phrase its register and a
landing goal never the last phrase's, the part's top note in its peak phrase 60-75 % through it, the bridge in its own
register (BRIDGE_SHIFT) with its own rhythm: long notes against the moving lines) - then a two-bar MOTIF (a rhythm
cell of the feel's family + a contour of scale steps) fitted to the changes - the strong notes a guide-tone line
(3rds / 7ths moving by step), chord tones and safe tensions on strong beats and long notes, chord-scale steps
between, chromatic approach notes into targets, leaps recovered by a step back, inside the genre's register; the
motif developed (repeated, sequenced by the changes, answered, fragmented, climbing to the phrase peak), each phrase
ending as drawn from PHRASE_ENDS (a downbeat landing, an anticipation, a pickup into the next phrase, a short landing
that leaves the bar to the left hand's answer); nearly every fresh 4-bar phrase leans on a tension on a strong beat
resolved by step (_appoggiatura); every later A RESTATES the A1 note for note up to its cadence (re-fitted where its
changes differ), a blues chorus is AAB and its second chorus varies where SECOND_CHORUS draws it (its answer, its
second statement, or calmer with the climax in the first chorus), the last part cadences on the tonic.
melody_issues() checks every part, _style_issues() the writing (a rhythm cell at most twice per 8 bars - a blues' riff
repeat excepted -, no circling one pitch); a part with issues is recomposed (the next dice of the same seed) - so the
result is deterministic.
The plan comes first, top-down (genres.ARCS, one mechanism on every level: a curve read by arc_at, its level turned
into targets): set_plan() gives a stream of tunes an energy wave (feel, mood, tempo, key per tune); the form's tension
curve gives every two-bar phrase of the head a level -> its centre pitch, ceiling, line density and the chord colour;
the curve's maximum is the climax phrase (the tune's single highest note, approached and released); the phrases are
gestures (PLANS) filled with notes last. Identity: the A1's opening is the HOOK (restated with the theme in every A,
quoted by the solo, over the intro's vamp and in the tag), the bridge / B has its own counter-motif (one rhythm cell +
one inverted contour for the whole tune). frame() writes the intro (a vamp from genres.INTROS with a line from
INTRO_LINES over it: a fragment of the hook augmented / sequenced / answered - drawn by weight, never the head's
bars copied) and the tag (the hook's fragment over the vamp again, TAG_LINES, with a twist:
an approach into the end chord drawn from TAG_APPROACH); reharm()
gives most tunes (plan['solo']['reharm']) one cadence played another way (a CHART_VARIANTS kind) somewhere in a
head-out part (the last
solo chorus and the head out); the solo's shape (genre.plan['solo']['shapes']) and a double-time burst (in ~30 % of
the tunes) are drawn, the dynamic plan (genre.plan['dynamics'], as the shape allows) decides where the peak is and the
shout, _lift() gives a head-out peak its top note, and the final chord's style is drawn (END_STYLES).
shape() measures it all (climax place, hook recurrences, register / density following the arc); tells() the blind
test's tells.
"""
from __future__ import annotations

from collections import namedtuple
from copy import deepcopy
import random
import re
from dataclasses import dataclass, field

from ..patterns import Clip
from ..theory import (ComposeError, Key, available_tensions, chord, chord_kind, chord_scale, clash, guide_tones, note,
                      note_name, spell_above)
from .genres import (BLOCKS, BRIDGE_ENDS, BRIDGE_SHIFT, CELLS, CHART_VARIANTS, COLOURS, CONTOURS, DEVELOP_RHYTHM,
                     ENDINGS, FEEL_FORMS, FORMS, END_STYLES, INTRO_LINES, INTRO_TONIC, INTROS, OUT_PARTS, PEAK_PART,
                     PHRASE_ENDS, JAZZ_TITLES, SECOND_CHORUS, TAG_APPROACH, TAG_LINES, Genre, _land_index)

ROMAN = {'I': 0, 'II': 2, 'III': 4, 'IV': 5, 'V': 7, 'VI': 9, 'VII': 11}
ABSTRACT = ('M', 'm', '7', 'ø', 'o', 'sus')
_TOK = re.compile(r'^([b#]?)(VII|VI|IV|V|III|II|I)(.*)$')
_SHARP_KEYS = {'major': {'G', 'D', 'A', 'E', 'B', 'F#'}, 'minor': {'E', 'B', 'F#', 'C#'}}
_FLATS = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
_SHARPS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


# ------------------------------------------------------------------------------------------------ harmony

INVERSIONS = {'3': 1, '5': 2, '7': 3}


def parse_block(spec: str) -> list[tuple[int, str, float]]:
    """A block 'IIm V7 IM:2' -> [(semitones above the tonic, quality, bars)]. Abstract qualities (ABSTRACT) stay
    abstract; a written one must parse as a chord quality. '@3' / '@5' / '@7' after the quality = that chord tone in
    the bass (V@3 = Eb/G in Ab: the pop / classical inversions; the quality keeps the suffix)."""
    out = []
    for tok in spec.split():
        if tok == '|':
            continue
        name, _, bars = tok.partition(':')
        m = _TOK.match(name)
        if not m:
            raise ComposeError(f"block token {tok!r}: want a roman numeral (b / # optional) + a quality, e.g. IIm7")
        off = (ROMAN[m.group(2)] + {'': 0, 'b': -1, '#': 1}[m.group(1)]) % 12
        q = m.group(3)
        base, at_, inv = q.partition('@')
        if at_ and inv not in INVERSIONS:
            raise ComposeError(f"block token {tok!r}: an inversion is @3 / @5 / @7 (that chord tone in the bass)")
        if base not in ABSTRACT:
            chord('C' + base)                                 # raises on an unknown quality
        try:
            b = float(bars) if bars else 1.0
        except ValueError:
            raise ComposeError(f"block token {tok!r}: bars after ':' must be a number") from None
        if b <= 0 or (b * 2) % 1:
            raise ComposeError(f"block token {tok!r}: bars must be a positive multiple of 0.5")
        out.append((off, q, b))
    if not out:
        raise ComposeError('empty block')
    return out


def _pick(rng: random.Random, weights: dict):
    items = [(k, w) for k, w in weights.items() if w > 0]
    r = rng.random() * sum(w for _, w in items)
    for k, w in items:
        r -= w
        if r < 0:
            return k
    return items[-1][0]


def _rich(q: str) -> bool:
    return any(x in q for x in ('9', '11', '13', 'alt', '#', 'b'))


def colour(blocks: list, rng: random.Random, *, richness: float = 1.0, tritone: float = 0.0,
           blues: bool = False, after=None, colours: dict | None = None) -> list[tuple[int, str, float]]:
    """Abstract qualities -> written ones (`colours`, default the jazz COLOURS - Genre.harmony['colours']): tonic
    chords from the tonic tables, a dominant by where it resolves (down a fifth / a half step to a minor chord: b9 /
    b13 / alt; to a major one: 13 / 9 / #11; a blues I7 / IV7: plain colours), a resolving dominant swapped for its
    tritone substitute with chance `tritone`. after: the (offset, quality, bars) that follows the block (default: its
    own first chord, as in a loop). An inversion ('@3') stays on the coloured quality."""
    COLOURS_ = COLOURS if colours is None else colours
    out = []
    for i, (off, q, bars) in enumerate(blocks):
        nxt = blocks[i + 1] if i + 1 < len(blocks) else (after or blocks[0])
        q, at_, inv = q.partition('@')
        inv = at_ + inv
        if q not in ABSTRACT:
            out.append((off, q + inv, bars))
            continue
        if q == '7':
            resolves = (nxt[0] - off) % 12 in (5, 11)
            minor_target = nxt[1].startswith('m') or nxt[1] in ('ø', 'o')
            table = '7_blues' if blues and off in (0, 5) else '7_minor' if resolves and minor_target else '7_major'
            if resolves and table != '7_blues' and (nxt[0] - off) % 12 == 5 and rng.random() < tritone:
                off, table = (off + 6) % 12, '7_sub'
        elif q in ('M', 'm'):
            table = f"{q}_tonic" if off == 0 else q
        else:
            table = q
        w = {k: v * (richness if _rich(k) else 1.0) for k, v in COLOURS_[table].items()}
        out.append((off, _pick(rng, w) + inv, bars))
    return out


def chord_name(t_pc: int, off: int, q: str, sharps: bool) -> str:
    """The chord symbol of a block chord: its root spelled (spell), the quality, an inversion ('@3' / '@5' / '@7') as
    a slash bass ('Eb/G')."""
    base, at_, inv = q.partition('@')
    root = spell(t_pc + off, sharps, off)
    sym = root + base
    if not at_:
        return sym
    c = chord(sym)
    iv = c.intervals[min(INVERSIONS[inv], len(c.intervals) - 1)]
    steps = {'3': 2, '5': 4, '7': 6}[inv]
    if inv == '3' and iv == 5:                         # (a sus chord's '3rd' is its 4th: Bb7sus4/Eb, not /D#)
        steps = 3
    return f"{sym}/{spell_above(root, iv, steps)}"


def spell(pc_: int, sharps: bool, offset: int = 0) -> str:
    """A root name `offset` semitones above the tonic (a sharp / a flat key's tonic name), spelled by the key
    (theory.spell_above: the degree's letter - bII bIII #IV bVI bVII for the chromatic roots): Cb, not B, as the IV of
    Gb; the Neapolitan of Eb Fb; the bVI of E C."""
    tonic = (_SHARPS if sharps else _FLATS)[(pc_ - offset) % 12]
    return spell_above(tonic, offset % 12)


# ------------------------------------------------------------------------------------------------ the plan

def arc_at(curve, x: float) -> float:
    """The level of an arc curve ((x, level) points, x 0..1) at x: piecewise linear."""
    x = min(1.0, max(0.0, x))
    for (x0, y0), (x1, y1) in zip(curve, curve[1:]):
        if x <= x1 + 1e-9:
            return y0 if x1 - x0 < 1e-9 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return curve[-1][1]


def targets(genre: Genre, level: float) -> dict:
    """A level 0..1 -> the genre's arc targets (each (at 0, at 1) read linearly)."""
    return {k: lo + (hi - lo) * level for k, (lo, hi) in genre.arc['targets'].items()}


def set_plan(genre: Genre, n: int, seed: int, mood: str | None = None, prev_key: str | None = None) -> list[dict]:
    """A set of n tunes along the genre's set arc: per tune {'energy', 'feel', 'mood', 'tempo', 'key'} - the feel
    nearest the energy that is not the last tune's (no ballad after a ballad), a mood that has the feel (weighted by
    its energy; `mood` pins it), the tempo inside the feel's range by the energy, the key moved from the tune before
    by the arc's key table (related or far, never the same). compose(..., plan=entry) plays it."""
    S = genre.arc['set']
    rng = random.Random(f"set:{genre.name}:{seed}")
    if mood is not None and mood not in genre.moods:
        raise ComposeError(f"genre {genre.name!r} has no mood {mood!r}; moods: {', '.join(genre.moods)}")
    moods = {mood: genre.moods[mood]} if mood else genre.moods
    out, prev_feel = [], None
    prev_pc = Key(prev_key).tonic % 12 if prev_key else None
    drng = random.Random(f"set-draws:{genre.name}:{seed}")     # (the set-level draws: their own dice)
    for k in range(n):
        e = arc_at(S['curve'], k / (n - 1) if n > 1 else 0.0)
        slot = _slot(genre, e, rng, moods, prev_feel, prev_pc)
        slot.update(set_draws(genre, drng, history=out))
        out.append(slot)
        prev_feel, prev_pc = slot['feel'], Key(slot['key']).tonic % 12
    return out


BLOCK_PINS = ('hook', 'open', 'build')
"""The harmony block kinds a genre's plan['set'] may pin per set slot ({mode: {block: weight}}: compose takes its
mode's)."""


def set_draws(genre: Genre, rng: random.Random, prev: dict | None = None, history: list | None = None) -> dict:
    """The genre's set-level draws (genre.plan['set'] {key: {choice: weight}}: the arrangement's layout, the climax
    kind, the melody's register shift, the chorus's chord block - HUMAN_FEEDBACK 2026-10-12: a set must vary, not
    only a piece) for one slot: each drawn by weight, never a choice of the last plan['set_memory'][key] slots
    (default 1: the slot before's; `history` the slots so far, else [prev]) - a budget over the set. A key whose
    weights are per mode ({'major': {choice: weight}, 'minor': ...}: the chorus's 'hook' block) draws one choice per
    mode ({mode: choice}; compose takes its mode's). The slot pins them for every best-of-N candidate (the score
    cannot collapse a set onto its safest choice); compose() draws them itself without a set plan (the teacher
    export)."""
    hist = list(history) if history is not None else [prev] if prev else []
    mem = genre.plan.get('set_memory') or {}
    out = {}
    for k, w in sorted((genre.plan.get('set') or {}).items()):
        recent = hist[max(0, len(hist) - mem.get(k, 1)):]
        if all(isinstance(x, dict) for x in w.values()):
            out[k] = {}
            for m, wm in sorted(w.items()):
                used = {(h.get(k) or {}).get(m) for h in recent}
                out[k][m] = _pick(rng, {v: x for v, x in wm.items() if v not in used} or wm)
            continue
        used = {h.get(k) for h in recent}
        cand = {v: x for v, x in w.items() if v not in used} or w
        out[k] = _pick(rng, cand)
    return out


def _slot(genre: Genre, e: float, rng: random.Random, moods: dict, prev_feel, prev_pc) -> dict:
    """One set slot at energy e: the feel nearest the energy (not the last tune's), a mood that has it, the tempo by
    the energy, the key moved from the tune before by the set arc's key table."""
    S = genre.arc['set']
    feels = sorted({f for m in moods.values() for f in m['feels']})
    cand = [f for f in feels if f != prev_feel] or feels
    feel = min(cand, key=lambda f: abs(genre.feels[f].get('energy', 0.5) - e) + 0.04 * rng.random())
    mname = _pick(rng, {m: M['feels'][feel] * (1.25 - abs(M.get('energy', 0.5) - e))
                        for m, M in sorted(moods.items()) if feel in M['feels']})
    M, F = genre.moods[mname], genre.feels[feel]
    lo, hi = F['tempo']
    pos = min(1.0, max(0.0, 0.5 + (e - F.get('energy', 0.5)) * 1.5))
    tempo = int(round(min(hi, max(lo, lo + (hi - lo) * pos + M.get('tempo', 0)))))
    mode = _pick(rng, M['modes'])
    w = {t: (S['keys'].get((Key(f"{t} {mode}").tonic - prev_pc) % 12, 1.0) if prev_pc is not None else 1.0)
         for t in M['keys'][mode]}
    tonic = _pick(rng, w) if any(v > 0 for v in w.values()) else rng.choice(M['keys'][mode])
    return {'energy': round(e, 2), 'feel': feel, 'mood': mname, 'tempo': tempo, 'key': f"{tonic} {mode}"}


MIX_STYLES = {'new-age-piano': 1.0, 'classical-piano': 0.8, 'jazz-piano': 0.8, 'lofi-piano': 0.8}
"""`endless piano --style mix`: the styles a set alternates (weights; never the same style twice running)."""


def mix_plan(genres_: list, n: int, seed: int, prev_key: str | None = None, weights: dict | None = None) -> list[dict]:
    """A set of n tunes over several genres (endless piano --style mix): the first genre's set arc gives every slot
    its energy; each slot draws a genre (weights, x how near one of its feels sits to the energy; never the one
    before), then that genre's slot (_slot: feel, mood, tempo, key moved from the tune before). Entries carry
    'genre'."""
    from .genres import get as _get
    gs = [g if isinstance(g, Genre) else _get(g) for g in genres_]
    W = weights or MIX_STYLES
    rng = random.Random(f"mix:{','.join(g.name for g in gs)}:{seed}")
    curve = gs[0].arc['set']['curve']
    out, prev_g, prev_feel, prev_pc = [], None, None, Key(prev_key).tonic % 12 if prev_key else None
    for k in range(n):
        e = arc_at(curve, k / (n - 1) if n > 1 else 0.0)
        cand = {g.name: W.get(g.name, 1.0) * (1.2 - min(abs(f.get('energy', 0.5) - e) for f in g.feels.values()))
                for g in gs if g.name != prev_g} or {g.name: 1.0 for g in gs}
        gname = _pick(rng, cand)
        g = next(x for x in gs if x.name == gname)
        slot = dict(_slot(g, e, rng, g.moods, prev_feel, prev_pc), genre=gname)
        if g.plan.get('set'):                          # (the genre's set-level draws, against its own last slot)
            slot.update(set_draws(g, random.Random(f"set-draws:{gname}:{seed}:{k}"),
                                  next((x for x in reversed(out) if x['genre'] == gname), None)))
        out.append(slot)
        prev_g, prev_feel, prev_pc = gname, slot['feel'], Key(slot['key']).tonic % 12
    return out


def describe_set(plan: list[dict]) -> str:
    """The set plan, one line per tune (the energy as a bar)."""
    return '\n'.join(f"  {k + 1:>2}. energy {p['energy']:.2f} {'#' * round(p['energy'] * 20):<20} {p['feel']:<8} "
                     f"{p['tempo']:>3} BPM  {p['key']:<9} {p['mood']}" + (f"  ({p['genre']})" if p.get('genre') else '')
                     + (f"  {p['layout']}" if 'layout' in p else '') + (f" / {p['climax']}" if 'climax' in p else '')
                     + (f" / {p['shift']:+d}" if 'shift' in p else '')
                     for k, p in enumerate(plan))


# ------------------------------------------------------------------------------------------------ chord helpers

class RaisedPcs(set):
    """A key's pitch classes, flagged: a plain major triad over the key's minor 3rd takes the key's scale with its
    raised 3rd, and a triad's 6th is no core tone (ChordInfo; compose passes them for a genre with
    melody['raised_v'])."""
    raised = True


class ChordInfo:
    """What the melody may do over one chord: core tones (1 3 5 7 / 6), safe tensions, the chord scale (pcs).
    key_pcs: the key's pitch classes - a chord whose core is diatonic takes its tensions and scale steps from the key
    (a iii-7 is phrygian, not dorian: no D# over F#m7 in D major); a chromatic chord (a secondary dominant, a
    borrowed iv, a tritone sub) keeps its own chord scale. Written tensions always count."""

    def __init__(self, sym: str, key_pcs=None):
        self.sym = sym
        c = chord(sym)
        self.chord = c
        root = c.root % 12
        kind = chord_kind(c)
        ints = {(p - root) % 12 for p in c.pcs}
        core = {0, 3, 4, 7, 10, 11} & ints
        if kind in ('m7b5', 'dim7'):
            core |= {6} & ints
        if kind in ('6', 'm6', 'dim7'):
            core |= {9} & ints
        if kind == 'sus':
            core |= {5}
        if 7 not in ints and 8 in ints and kind != 'dom':
            core |= {8}
        g3, g7 = guide_tones(c)
        core |= {(g - root) % 12 for g in (g3, g7) if g is not None}
        if getattr(key_pcs, 'raised', False) and 9 not in ints:
            core -= {9}           # (a genre's melody['raised_v'] - new-age round r9: the jazz reading of a triad as
            #                       a 6th chord put held 6ths on its downbeats, F# over A in D minor, A over C)
        self.core = {(root + i) % 12 for i in core}
        avail = {(root + i) % 12 for i in available_tensions(c)}
        scale = {(root + i) % 12 for i in chord_scale(c)}
        if key_pcs and self.core <= set(key_pcs):
            avail &= set(key_pcs)
            scale &= set(key_pcs)
        elif getattr(key_pcs, 'raised', False) and ints == {0, 4, 7} and (root + 3) % 12 in key_pcs:
            # a plain major triad over the key's minor 3rd (V in minor, a secondary V without its 7th): the key's
            # scale with its raised 3rd (E in A minor: phrygian dominant - new-age round r7: C#, D#, F# over E in A
            # minor from E's own major scale; a genre's melody['raised_v'], RaisedPcs)
            scale = (set(key_pcs) - {(root + 3) % 12}) | self.core
            avail &= scale
        self.tensions = (avail | {p % 12 for p in c.pcs}) - self.core
        self.scale = scale | self.core | self.tensions
        self.root = root
        self.third = None if g3 is None else g3 % 12
        self.guide = {g % 12 for g in (g3, g7) if g is not None}


class Harm:
    """A part's changes as a timeline: [(start beat, beats, ChordInfo)]."""

    def __init__(self, changes: list[tuple[str, float]], key_pcs=None):
        self.items, t = [], 0.0
        for sym, beats in changes:
            self.items.append((t, beats, ChordInfo(sym, key_pcs)))
            t += beats
        self.length = t

    def at(self, t: float) -> ChordInfo:
        for st, d, ci in self.items:
            if st - 1e-6 <= t < st + d - 1e-6:
                return ci
        return self.items[-1][2]

    def under(self, st: float, du: float) -> ChordInfo:
        """The chord a note belongs to: the one it sounds over longest (an anticipation belongs to the new chord)."""
        best, ov = self.at(st), -1.0
        for s0, d, ci in self.items:
            o = min(st + du, s0 + d) - max(st, s0)
            if o > ov + 1e-6:
                best, ov = ci, o
        return best


# ------------------------------------------------------------------------------------------------ melody

def _scale_step(p: int, n: int, pcs: set) -> int:
    q, k = p, 0
    while k < abs(n):
        q += 1 if n > 0 else -1
        if q % 12 in pcs:
            k += 1
    return q


def _events(cell, t0: float, meter: int):
    """A rhythm cell -> [(start, dur, strong)] (rests left out). Strong: beat 1 (and 3 in 4/4) or a quarter+."""
    bar8 = 2 * meter
    out, t = [], 0
    for x in cell:
        if x > 0:
            pos = t % bar8
            strong = pos == 0 or (meter == 4 and pos == 4) or x >= 2
            out.append((t0 + t * 0.5, x * 0.5, strong))
        t += abs(x)
    return out


STEPS = {0: 0.12, 1: 0.5, 2: 0.28, 3: 0.06, 4: 0.04}
"""The motif / line contour's move sizes in scale steps (weights; 3+ = a leap, one per cell at most) - a genre's
melody['steps'] replaces it (a singable line: more steps)."""


def _contour(n: int, shape: str, rng: random.Random, steps: dict | None = None) -> list[int]:
    """n scale-step moves (the first relative to the note before the cell): mostly steps, one leap at most."""
    out, leaped = [], False
    S = steps or STEPS
    for i in range(n):
        x = i / max(1, n - 1)
        up = {'rise': 0.78, 'fall': 0.22, 'arch': 0.8 if x < 0.55 else 0.2, 'valley': 0.2 if x < 0.5 else 0.8,
              'flat': 0.5}[shape]
        size = _pick(rng, {k: (w if k < 3 or not leaped else 0) for k, w in S.items()})
        leaped |= size >= 3
        out.append(size if rng.random() < up else -size)
    return out


@dataclass
class _Ctx:
    harm: Harm
    meter: int
    lo: int
    hi: int
    rng: random.Random
    used: dict | None = None             # pitch -> attacks in the current 4-bar phrase (circling one pitch)
    lead: list | None = None             # [the last strong pitch]: the guide-tone line the strong notes follow
    repeat: tuple = (0.7, 0.0)           # the cost of repeating the note before (strong / landing notes, weak ones)
    chromatic: float = 0.3               # the chance of a half-step-below approach note (genre melody 'chromatic')


def _choose(ci: ChordInfo, target: int, prev: int | None, kind: str, ctx: _Ctx, land_pcs=None, also=(),
            change: bool = False) -> int:
    if kind == 'land':
        pcs = set(land_pcs) if land_pcs else ci.core
    elif kind == 'strong':
        pcs = ci.core | ci.tensions
    else:
        pcs = ci.scale
    # a note held half a beat+ into the next chord(s) fits them too (when any pitch class can)
    pcs = {x for x in pcs if all(x in c.core | c.tensions for c in also)} or pcs
    best, bc = None, 1e9
    for c in range(ctx.lo, ctx.hi + 1):
        if c % 12 not in pcs:
            continue
        cost = abs(c - target)
        if kind == 'strong' and c % 12 in ci.tensions:
            cost += 1.2
        if prev is not None:
            leap = abs(c - prev)
            cost += max(0, leap - 7) * 2.0
            if c == prev:
                cost += ctx.repeat[kind == 'weak']
        if kind != 'weak':                                # the guide-tone line first: 3rds / 7ths, moving by step
            cost -= 0.5 * (c % 12 in ci.guide)
            if ctx.lead and ctx.lead[0] is not None:
                cost += 0.25 * max(0, abs(c - ctx.lead[0]) - 2)
        if change:                                        # a new chord met by its 3rd / 7th, reached by step
            cost -= 0.6 * (c % 12 in ci.guide)
            if prev is not None:
                cost += 0.3 * max(0, abs(c - prev) - 2)
        if ctx.used:                                      # a pitch struck twice in the phrase already
            cost += 1.0 * max(0, ctx.used.get(c, 0) - 1)
        if cost < bc - 1e-9:
            best, bc = c, cost
    if best is None:                                      # nothing in range: the nearest chord tone anywhere
        best = min((c for c in range(ctx.lo - 12, ctx.hi + 13) if c % 12 in (pcs or ci.core)),
                   key=lambda c: abs(c - target))
    return best


def _fit(events, deltas, ctx: _Ctx, prev: int | None, *, first=None, land=None, land_pcs=None, goal=None) -> list:
    """Pitches for events from scale-step deltas: the first note at `first` (a target pitch) when given; `land` =
    the index of the landing note (pcs `land_pcs`, default the chord's core), aimed at `goal` (the phrase's planned
    landing pitch) when given."""
    out = []
    hist = [prev] if prev is not None else []
    for i, (st, du, strong) in enumerate(events):
        ci = ctx.harm.under(st, du)
        d = deltas[i % len(deltas)]
        if len(hist) >= 2 and abs(hist[-1] - hist[-2]) > 5:          # recover from a leap: step back
            back = -1 if hist[-1] > hist[-2] else 1
            if d == 0 or (d > 0) != (back > 0):
                d = back
        if i == 0 and first is not None:
            target = first
        elif i == land and goal is not None:
            target = goal
        elif hist:
            target = _scale_step(hist[-1], d, ci.scale)
        else:
            target = (ctx.lo + ctx.hi) // 2
        if target > ctx.hi:                     # (a planned first note over the ceiling: at the ceiling)
            target = ctx.hi if i == 0 and first is not None else \
                _scale_step(hist[-1] if hist else ctx.hi, -abs(d) or -1, ci.scale)
        elif target < ctx.lo:
            target = ctx.lo if i == 0 and first is not None else \
                _scale_step(hist[-1] if hist else ctx.lo, abs(d) or 1, ci.scale)
        kind = 'land' if i == land else 'strong' if strong else 'weak'
        also = [c for s0, d0, c in ctx.harm.items if c is not ci and min(st + du, s0 + d0) - max(st, s0) >= 0.5]
        change = kind != 'weak' and (i == 0 or ctx.harm.under(*events[i - 1][:2]) is not ci)
        p = _choose(ci, target, hist[-1] if hist else None, kind, ctx, land_pcs if i == land else None, also, change)
        if any(p % 12 not in c.core | c.tensions for c in also):      # no pitch fits both: released at the change
            du = max(0.5, min(s0 for s0, _, c in ctx.harm.items if s0 > st + 1e-6) - st)
        out.append((st, du, p))
        hist.append(p)
        if ctx.used is not None:
            ctx.used[p] = ctx.used.get(p, 0) + 1
        if kind != 'weak' and ctx.lead is not None:
            ctx.lead[0] = p
    # chromatic approach notes: a short off-beat note right before a chord tone on the beat, now and then a half step
    # below it (never into a tension, never off the beat: blind round 5)
    for i in range(len(out) - 1):
        st, du, p = out[i]
        nst, ndu, np_ = out[i + 1]
        if du <= 0.5 and not events[i][2] and abs(st + du - nst) < 1e-6 and events[i + 1][2] \
                and abs(nst - round(nst)) < 1e-6 and np_ % 12 in ctx.harm.under(nst, ndu).core \
                and ctx.rng.random() < ctx.chromatic and ctx.lo <= np_ - 1:
            out[i] = (st, du, np_ - 1)
    return out


def _sequenced(notes, harm: Harm, meter: int, t0: float, lo: int, hi: int) -> list:
    """A 2-bar unit's notes as a 1-bar cell and its sequence: the first bar's rhythm and intervals again in the second
    bar, moved by the root motion between the two bars (folded to a 5th or less: a chromatic root walk a half step, a
    ii-V a 4th up / 5th down) and re-fitted to the chord there (_refit); the sequence's last note held to the bar's
    last 8th. Unchanged when the first bar has fewer than 2 notes or the second bar's chord is the first's."""
    one = [n for n in notes if n[0] < t0 + meter - 1e-6]
    if len(one) < 2:
        return notes
    c1, c2 = harm.under(t0, 0.5), harm.under(t0 + meter, 0.5)
    if c1 is c2 or c1.root is None or c2.root is None:
        return notes
    d = (c2.root - c1.root) % 12
    d = d - 12 if d > 6 else d
    two = [(st + meter, min(du, t0 + 2 * meter - st - meter), q + d) for st, du, q in one]
    end = t0 + 2 * meter - 0.5
    two[-1] = (two[-1][0], max(two[-1][1], end - two[-1][0]), two[-1][2])
    two = _refit(two, harm, meter, lo, hi, prev=one[-1][2])
    if max(abs(b[2] - a[2]) for a, b in zip(one + two, (one + two)[1:])) > 9:
        return notes
    return one + two


def _refit(notes, harm: Harm, meter: int, lo: int, hi: int, release: bool = True, prev: int | None = None) -> list:
    """Notes moved onto other chords, their rhythm and contour kept (a restatement, a sequence, the hook over a vamp):
    a pitch that fits the chord it now meets stays, another moves to the nearest that fits (strong beats / long notes:
    chord tones + safe tensions; the rest: the chord scale), keeping the step's direction from the note before (and
    no leap of more than a fifth the original did not have); a note then held half a beat+ into a chord it does not fit
    is released at the change (release=False: a frame's last note rings into its end chord)."""
    strong_pos = (0, 2) if meter == 4 else (0,)
    out = []
    for i, (st, du, p) in enumerate(notes):
        ci = harm.under(st, du)
        pos = st % meter
        strong = du >= 1.0 - 1e-6 or any(abs(pos - x) < 1e-6 for x in strong_pos)
        pcs = ci.core | ci.tensions if strong else ci.scale
        if p % 12 in pcs and lo <= p <= hi:
            out.append((st, du, p))
            continue
        want = _sign(p - notes[i - 1][2]) if i else 0

        def cost(c):
            moved = 0 if not out or not want else (_sign(c - out[-1][2]) != want) * 2.5
            ref = out[-1][2] if out else prev            # (no leap the original did not have; `prev`: the note before)
            leap = max(0, abs(c - ref) - 7) if ref is not None else 0
            return abs(c - p) + moved + (0.3 if c > p else 0) + 1.5 * leap
        cand = [c for c in range(lo, hi + 1) if c % 12 in pcs] or \
            [c for c in range(lo - 12, hi + 13) if c % 12 in (pcs or ci.core)]
        out.append((st, du, min(cand, key=cost)))
    _smooth_leaps(out, harm, meter, lo, hi)
    for i, (st, du, p) in enumerate(out if release else ()):     # held half a beat+ into a misfit: released
        for s0, d0, cj in harm.items:
            if st + 1e-6 < s0 and min(st + du, s0 + d0) - s0 >= 0.5 and p % 12 not in cj.core | cj.tensions:
                out[i] = (st, max(0.5, s0 - st), p)
                break
    return out


def _smooth_leaps(out, harm: Harm, meter: int, lo: int, hi: int, keep=()) -> None:
    """A leap over a 5th the next note does not step back from (a re-fit, a restated unit meeting new material):
    the leaping note moves to the nearest fitting pitch within a 5th of the note before it - the line stays
    singable. In place; indices in `keep` (the climax) stay."""
    strong_pos = (0, 2) if meter == 4 else (0,)
    for i in range(1, len(out) - 1):
        st, du, p = out[i]
        leap, nxt = p - out[i - 1][2], out[i + 1][2] - p
        if i in keep or not (abs(leap) > 7 and (nxt == 0 or (nxt > 0) == (leap > 0) or abs(nxt) > 4)):
            continue
        ci = harm.under(st, du)
        pos = st % meter
        strong = du >= 1.0 - 1e-6 or any(abs(pos - x) < 1e-6 for x in strong_pos)
        pcs = ci.core | ci.tensions if strong else ci.scale
        cand = [c for c in range(out[i - 1][2] - 7, out[i - 1][2] + 8) if c % 12 in pcs and lo <= c <= hi]
        if cand:
            out[i] = (st, du, min(cand, key=lambda c: (abs(c - p), c)))


def _approach(notes, k: int, harm: Harm, first: int = 0) -> None:
    """Around a peak note (index k, in place): the approach climbs to it and the release falls from it in steps of a
    fifth at most (notes lower than that are pulled up to a chord tone / tension under their neighbour); notes before
    index `first` stay (a restated phrase is not touched)."""
    for ks in (range(k - 1, first - 1, -1), range(k + 1, len(notes))):
        for j in ks:
            ref = notes[j + 1 if j < k else j - 1][2]
            if ref - notes[j][2] <= 7:
                break
            ci = harm.under(notes[j][0], notes[j][1])
            fits = [c for c in range(ref - 5, ref) if c % 12 in ci.core | ci.tensions]
            notes[j] = (notes[j][0], notes[j][1], max(fits))


def _ending_cell(cells: dict, kind: str, rng: random.Random, bar8: int) -> tuple:
    """A land cell for a phrase ending of `kind` (genres.PHRASE_ENDS): 'down' a cell landing on the downbeat, 'antic'
    one anticipating it an 8th early (or a downbeat cell whose landing moves an 8th earlier), 'pickup' the landing held
    shorter and two 8ths at the cell's end leading into the next phrase, 'lh' the landing a dotted quarter at most and
    the right hand resting (the left hand's answer has the bar), 'breath' the landing held, then half a bar of
    silence (it rings: the phrase breathes before the next), 'tail' the landing held a dotted quarter (a waltz: a
    quarter), then two notes stepping away from it and a quarter's rest (the phrase answers itself - blind round 7:
    one-note landing bars every other bar)."""
    names = sorted(cells)

    def at(n):
        return sum(abs(x) for x in cells[n][:_land_index(cells[n], bar8)])
    if kind == 'antic':
        own = [n for n in names if at(n) == bar8 - 1]
        if own:
            return cells[rng.choice(own)]
    c = list(cells[rng.choice([n for n in names if at(n) == bar8] or names)])
    i = _land_index(c, bar8)
    rest = c[i] + sum(abs(x) for x in c[i + 1:])          # the landing + what follows it, in 8ths
    if kind == 'antic' and i and abs(c[i - 1]) >= 2:
        c[i - 1] += -1 if c[i - 1] > 0 else 1
        c[i] += 1
    elif kind == 'pickup' and rest >= 5:
        c[i:] = [rest - 3, -1, 1, 1]
    elif kind == 'lh' and rest >= 5:
        c[i:] = [3, -(rest - 3)]
    elif kind == 'breath' and rest >= 6:
        c[i:] = [rest - 4, -4]
    elif kind == 'tail' and rest >= 6:
        c[i:] = [rest - 5, 1, 2, -2] if rest >= 7 else [rest - 4, 1, 1, -2]
    return tuple(c)


def _cell_ending(cell, kind: str, bar8: int) -> tuple | None:
    """A phrase ending GROWN FROM THE HOOK (blind round 7: heads that pad with one-note bars and never grow from one
    cell): the hook cell's first bar (its rhythm), then the landing on the next downbeat as the ending `kind` wants
    (genres.PHRASE_ENDS: down - held; breath - half a bar, then silence; lh - short, the left hand answers; pickup -
    two 8ths into the next phrase; antic - an 8th early). None when the first bar holds fewer than two notes."""
    head, s = [], 0
    for x in cell:
        if s + abs(x) >= bar8:
            r = bar8 - s
            if r:
                head.append(r if x > 0 else -r)
            s = bar8
            break
        head.append(x)
        s += abs(x)
    if s < bar8:
        head.append(-(bar8 - s))
    if sum(1 for x in head if x > 0) < 2:
        return None
    if kind == 'antic' and head[-1] >= 2:
        return tuple(head[:-1] + [head[-1] - 1, bar8 - 1, -2])
    land = {'breath': [bar8 // 2, -(bar8 - bar8 // 2)], 'lh': [3, -(bar8 - 3)],
            'pickup': [bar8 - 3, -1, 1, 1],
            'tail': [bar8 - 5, 1, 2, -2] if bar8 >= 7 else [bar8 - 4, 1, 1, -2]}.get(kind, [bar8 - 2, -2])
    return tuple(head + land)


def _vary_cell(cell, how: str, bar8: int) -> tuple:
    """A two-bar rhythm cell (8ths, rests negative) developed (genres.DEVELOP_RHYTHM): 'same'; 'displace' an 8th
    later (its tail an 8th shorter); 'truncate' its first bar, then one long note and a breath; 'augment' its first bar
    twice as slow. The cell itself when the variant would keep fewer than two notes."""
    total = sum(abs(x) for x in cell)
    out = list(cell)
    if how == 'displace':
        out = ([out[0] - 1] + out[1:]) if out[0] < 0 else [-1] + out
        x = out[-1]
        out[-1:] = [x + 1] if x < -1 else [x - 1] if x > 1 else []
    elif how in ('truncate', 'augment'):
        head, s = [], 0
        for x in cell:
            if s + abs(x) > bar8:
                break
            head.append(x)
            s += abs(x)
        if how == 'augment':
            out = [2 * x for x in head] + ([-(total - 2 * s)] if total > 2 * s else [])
        else:
            r = total - s
            out = head + ([r - 2, -2] if r >= 4 else [r])
    if sum(abs(x) for x in out) != total or sum(1 for x in out if x > 0) < 2:
        return tuple(cell)
    return tuple(out)


def _appoggiatura(notes, harm: Harm, meter: int, a: float, b: float, lo: int, hi: int, rng: random.Random,
                  keep=()) -> None:
    """A tension on a strong beat (1 / 3, a waltz 1) or held a beat+, resolved by step to a chord tone, in [a, b):
    when the phrase has none, one strong note before a step to a chord tone becomes the tension a step above it
    (mostly) or below - an appoggiatura (a suspension when the note before already had that pitch). Which note is
    drawn. In place; indices in `keep` (the climax) stay."""
    def strong(st, du):
        pos = st % meter
        return du >= 1.0 - 1e-6 or abs(pos) < 1e-6 or (meter == 4 and abs(pos - 2) < 1e-6)
    idx = [i for i in range(len(notes) - 1) if a - 1e-6 <= notes[i][0] < b - 1e-6]
    cands = []
    for i in idx:
        st, du, p = notes[i]
        nst, ndu, q = notes[i + 1]
        if not strong(st, du) or nst - (st + du) > 0.6:
            continue
        ci, cj = harm.under(st, du), harm.under(nst, ndu)
        if q % 12 not in cj.core:
            continue
        if p % 12 not in ci.core and 0 < abs(q - p) <= 2:
            return                                        # the phrase has one
        if i in keep or i + 1 in keep:
            continue
        if i and abs(notes[i - 1][2] - p) == 1 and notes[i - 1][2] % 12 not in harm.under(*notes[i - 1][:2]).scale:
            continue                                      # (a chromatic approach into it stays resolved)
        for d, w in ((1, 2.0), (2, 1.5), (-1, 1.0), (-2, 0.6)):
            x = q + d
            if x % 12 in ci.tensions and lo <= x <= hi and (i == 0 or abs(x - notes[i - 1][2]) <= 7):
                cands.append(((i, x), w))
    if cands:
        i, x = _pick(rng, dict(cands))
        notes[i] = (notes[i][0], notes[i][1], x)


def _style_issues(notes, meter: int, beats: float, skip=(), span: int = 0, lands=None,
                  pads: float = 0.125) -> list[str]:
    """The writing rules of a head part (blind rounds 4-5), checked like melody_issues but weighed lower: a rhythm
    cell (a bar of 3+ notes) at most twice per 8 bars, a plainer bar (2 notes: half + half, a waltz's half + quarter)
    three times (bars in `skip` - a riff's repeat - left out); per 4-bar phrase no pitch struck more than about a third
    of the time (max(2, 30 %)) and a range of a 4th+ (no circling one pitch); the part's whole range at least `span`
    semitones (an A: an octave - blind round 5: an A inside A4-Eb5). lands= the bars where a phrase lands (a set of
    bar indices): the other bars may strike one note or none in `pads` of them at most (blind round 7: heads padding
    with a one-note bar every other bar)."""
    out = []
    if lands is not None:
        per = [0] * int(round(beats / meter))
        for s_, _, _ in notes:
            b_ = int((s_ + 1e-6) // meter)
            if 0 <= b_ < len(per):
                per[b_] += 1
        free = [b_ for b_ in range(len(per)) if b_ not in lands and b_ not in skip]
        thin = [b_ for b_ in free if per[b_] <= 1]
        for b_ in thin[int(pads * len(free) + 1e-6):]:
            out.append(f"bar {b_ + 1}: one note or none (a pad)")
    if span and notes and max(n[2] for n in notes) - min(n[2] for n in notes) < span:
        out.append(f"range {max(n[2] for n in notes) - min(n[2] for n in notes)} under {span}")
    rs = _bar_rhythms(notes, meter, beats)
    for w0 in range(0, len(rs), 8):
        cnt: dict = {}
        for b in range(w0, min(len(rs), w0 + 8)):
            if b not in skip and len(rs[b]) >= 2:
                cnt[rs[b]] = cnt.get(rs[b], 0) + 1
        over = [r for r, k in cnt.items() if k > (2 if len(r) >= 3 else 3)]
        if over:
            out.append(f"one bar rhythm {cnt[over[0]]}x in bars {w0 + 1}-{w0 + 8}")
    ph = 4 * meter
    for k in range(int(round(beats / ph))):
        ns = [n[2] for n in notes if k * ph - 1e-6 <= n[0] < (k + 1) * ph - 1e-6]
        if len(ns) < 4:
            continue
        top = max(set(ns), key=ns.count)
        if ns.count(top) > max(2, round(0.3 * len(ns))):
            out.append(f"circles {note_name(top)} ({ns.count(top)} of {len(ns)}) in bars {4 * k + 1}-{4 * k + 4}")
        if max(ns) - min(ns) < 5:
            out.append(f"bars {4 * k + 1}-{4 * k + 4} inside a 4th")
    return out


def melody_issues(notes, harm: Harm, lo: int, hi: int, *, meter: int = 4, final_pcs=None) -> list[str]:
    """The cheap musical checks: no strong-beat (1, and 3 in 4/4) / long (a beat+) note outside chord tones + safe
    tensions (nor held half a beat+ into a chord it does not fit), the register, no leap over an octave, a leap over a
    fifth followed by a step back, the last note on
    `final_pcs` when given (and the chord under it is the tonic's)."""
    out = []
    strong_pos = (0, 2) if meter == 4 else (0,)
    for i, (st, du, p) in enumerate(notes):
        ci = harm.under(st, du)
        pos = st % meter
        on_strong = any(abs(pos - x) < 1e-6 for x in strong_pos)
        if (du >= 1.0 or on_strong) and p % 12 not in ci.core | ci.tensions:
            out.append(f"clash {note_name(p)} over {ci.sym} at beat {st:g}")
        for s0, d0, cj in harm.items:                    # held over a change: it must fit the next chord too
            if cj is not ci and min(st + du, s0 + d0) - max(st, s0) >= 0.5 and p % 12 not in cj.core | cj.tensions:
                out.append(f"{note_name(p)} held into {cj.sym} at beat {s0:g}")
        if not lo <= p <= hi:
            out.append(f"range {note_name(p)} at beat {st:g}")
        if i:
            leap = p - notes[i - 1][2]
            if abs(leap) > 12:
                out.append(f"leap {abs(leap)} at beat {st:g}")
            if abs(leap) > 7 and i + 1 < len(notes):
                nxt = notes[i + 1][2] - p
                if nxt == 0 or (nxt > 0) == (leap > 0) or abs(nxt) > 4:
                    out.append(f"unrecovered leap at beat {st:g}")
    last_ci = harm.under(notes[-1][0], notes[-1][1]) if notes else None
    if final_pcs and notes and last_ci.root in final_pcs and notes[-1][2] % 12 not in final_pcs:
        out.append(f"last note {note_name(notes[-1][2])} not on the tonic chord")
    return out


# ------------------------------------------------------------------------------------------------ the tune

@dataclass
class Tune:
    """A composed lead sheet (what the players get). Beats are quarter notes; parts in head order."""
    genre: str
    seed: int
    mood: str
    title: str
    key: str
    mode: str
    tempo: int
    meter: int
    feel: str
    swing: float | None
    form: str
    parts: list
    changes: dict                        # part -> [(symbol, beats)]
    melody: dict                         # part -> [(start, dur, pitch)]
    motif: list                          # the A1 motif notes [(start, dur, pitch)]
    intro: dict = field(default_factory=dict)   # {'changes': [...], 'melody': [...]}
    tag: dict = field(default_factory=dict)
    end_chord: str = ''
    blocks: dict = field(default_factory=dict)  # part -> block names (for the log)
    retries: int = 0
    energy: float = 0.5                  # the tune's place in the set (0 calm .. 1 the highlight)
    levels: dict = field(default_factory=dict)  # part -> the arc level of every two-bar phrase
    climax: dict = field(default_factory=dict)  # {'part', 'unit', 'beat', 'pitch'}: the planned highest note
    counter: list = field(default_factory=list)  # the bridge's counter-motif notes (part beats of its part)
    solo_changes: dict = field(default_factory=dict)  # part -> its reharm (reharm()): the last solo chorus + head out
    out_melody: dict = field(default_factory=dict)    # part -> the head out's melody where it differs (reharm, shout)
    shout: bool = False                  # the first head-out part is the shout chorus (the tune's peak)
    dynamics: str = 'solo'               # the whole piece's dynamic plan (genre.plan['dynamics'])
    solo_shape: str | None = None        # the solo's shape (genre.plan['solo']['shapes'], drawn)
    double: bool = False                 # the solo goes double time once (a 'burst' of 16ths at a drawn place)
    solo_charts: list = field(default_factory=list)   # a blues: the head chorus (part) each solo chorus plays
    end_kind: str = 'roll'               # the final chord's style (genres.END_STYLES)
    second: str | None = None            # a blues head's second chorus variation (genres.SECOND_CHORUS)
    out_parts: list = field(default_factory=list)   # the head out's parts (genres.OUT_PARTS; [] = FORMS' 'out')
    reharm_in: str = 'both'              # where the reharm sounds: 'both' (last solo chorus + head out) / 'out'
    arrange: dict = field(default_factory=dict)   # the set-level draws (genre.plan['set']: layout / climax kind /
    #                                               register shift; composer.set_draws) the players read

    def part_level(self, part: str) -> float:
        """The mean arc level of a part (0.5 when the tune has no plan)."""
        lv = self.levels.get(part)
        return sum(lv) / len(lv) if lv else 0.5

    @property
    def bar_beats(self) -> int:
        return self.meter

    def part_beats(self, part: str) -> float:
        return sum(b for _, b in self.changes[part])

    def changes_str(self, part: str | None = None, changes=None) -> str:
        """The song.form parts string ('Dm9:0.5 G13:0.5 | ...', lengths in bars)."""
        ch = changes if changes is not None else self.changes[part]
        return ' '.join(f"{s}:{b / self.meter:g}" for s, b in ch)

    def clip(self, notes, length: float, vel: int = 80) -> Clip:
        return Clip([(st, du, p, vel) for st, du, p in notes], length=length)

    def melody_clip(self, part: str, vel: int = 80) -> Clip:
        return self.clip(self.melody[part], self.part_beats(part), vel)

    def lead_sheet(self) -> list[str]:
        """One line per part: | bar | bar | ... with '%' where the chord holds on, '(0.5)' for half bars."""
        lines = []
        for p in self.parts:
            bars, cur, t = [], [], 0.0
            for s, b in self.changes[p]:
                left, first = b, True
                while left > 1e-6:
                    take = min(left, self.meter - t)
                    cur.append((s if first else '%') + ('' if abs(take - self.meter) < 1e-6
                                                       else f"({take / self.meter:g})"))
                    left, t, first = left - take, t + take, False
                    if t >= self.meter - 1e-6:
                        bars.append(' '.join(cur))
                        cur, t = [], 0.0
            if cur:
                bars.append(' '.join(cur))
            lines.append(f"{p:<4} | " + ' | '.join(bars) + ' |')
        return lines

    def describe(self) -> str:
        sw = f"swing {self.swing:.2f}" if self.swing else 'straight 8ths'
        head = [f"{self.title}  ({self.genre}, mood {self.mood}, seed {self.seed})",
                f"{self.key}, {self.tempo} BPM, {self.meter}/4, {self.feel} ({sw}), form {self.form} "
                f"({len(self.parts)} x {self.part_beats(self.parts[0]) / self.meter:g} bars)"]
        return '\n'.join(head + self.lead_sheet())

    def to_dict(self) -> dict:
        return {'title': self.title, 'genre': self.genre, 'mood': self.mood, 'seed': self.seed, 'key': self.key,
                'tempo': self.tempo, 'meter': f"{self.meter}/4", 'feel': self.feel, 'swing': self.swing,
                'form': self.form, 'parts': list(self.parts), 'blocks': self.blocks,
                'changes': {p: self.changes_str(p) for p in self.parts}, 'lead_sheet': self.lead_sheet(),
                'melody': {p: [[round(s, 3), round(d, 3), note_name(n)] for s, d, n in self.melody[p]]
                           for p in self.parts},
                'composer_retries': self.retries, 'energy': self.energy,
                'levels': {p: [round(x, 2) for x in v] for p, v in self.levels.items()},
                'climax': dict(self.climax, pitch=note_name(self.climax['pitch'])) if self.climax else None,
                'solo_changes': {p: self.changes_str(changes=ch) for p, ch in self.solo_changes.items()},
                'intro': {'kind': self.intro.get('kind'), 'changes': self.changes_str(changes=self.intro['changes'])}
                if self.intro else None,
                'tag': {'kind': self.tag.get('kind'), 'changes': self.changes_str(changes=self.tag['changes'])}
                if self.tag else None, 'shout': self.shout, 'dynamics': self.dynamics, 'solo_shape': self.solo_shape,
                'double': self.double, 'solo_charts': list(self.solo_charts), 'end_kind': self.end_kind,
                'second': self.second, 'out_parts': list(self.out_parts), 'reharm_in': self.reharm_in,
                'tag_approach': (self.tag or {}).get('approach'), 'tag_frame': (self.tag or {}).get('frame'),
                **({'arrange': dict(self.arrange)} if self.arrange else {})}


# ------------------------------------------------------------------------------------------------ titles

def key_words(key: str) -> str:
    """'Db major' -> 'D-flat major' (a classical title's key)."""
    tonic, mode = key.split()
    return tonic[0] + {'b': '-flat', '#': '-sharp'}.get(tonic[1:], '') + ' ' + mode


def title(rng: random.Random, feel: str, form: str, table: dict | None = None, key: str | None = None) -> str:
    """A title from the genre's words (Genre.titles, default genres.JAZZ_TITLES): each word list drawn once (sorted
    by name), a shape (a list, or {feel: [shapes]}) filled; {suffix} by the feel / form ('waltz' before the form),
    {key} the key spelled out."""
    T = table or JAZZ_TITLES
    S = T.get('suffix', {})
    suffix = S[feel] if feel == 'waltz' and feel in S else S.get(form) or S.get(feel) or S.get('', '')
    shapes = T['shapes'].get(feel, T['shapes'].get('', [])) if isinstance(T['shapes'], dict) else T['shapes']
    shape = _pick(rng, {s: 1.0 for s in shapes})
    words = {k: rng.choice(v) for k, v in sorted(T.items()) if k not in ('shapes', 'suffix')}
    t = shape.format(suffix=suffix, key=key_words(key) if key else '', **words)
    if form == 'blues' and 'Blues' not in t and rng.random() < 0.6:
        t += ' Blues'
    elif feel == 'waltz' and 'Waltz' not in t and 'Valse' not in t and rng.random() < 0.5:
        t += ' Waltz'
    return t


# ------------------------------------------------------------------------------------------------ compose

# The phrase level of the plan: the gestures per part kind, one entry per two-bar unit (4/4; a waltz plays each
# unit as two 3/4 bars of the doubled form, so it gets the WALTZ plans): (role, contour shape). Roles: motif (the
# hook stated), develop (the hook sequenced), answer (the hook's rhythm, the contour turned), line (a continuation
# cell: rise / arch - steered toward the phrase's target centre), contrast (the bridge's counter-motif), land (a
# cadence cell; 'land' ends a part, 'half' a phrase inside it), again (the part's unit <n> restated, re-fitted to the
# chords here: a blues' AAB). The later A sections restate the A1 up to their cadence (compose: copied).
PLANS = {
    # an A is a PERIOD: antecedent (the hook + a continuing line) / consequent (the hook sequenced + the cadence); the
    # B its own: the counter-motif, a line, the counter-motif sequenced (its rhythm, not the A's), a half cadence
    'A': [('motif', None), ('line', 'arch'), ('develop', None), ('land', 'fall')],
    'B': [('contrast', None), ('line', 'rise'), ('contrast', None), ('half', 'fall')],
    'C': [('motif', None), ('line', 'rise'), ('line', 'arch'), ('land', 'fall')],
    # a blues chorus is AAB: the 4-bar statement, the same again over the IV (re-fitted), the answer
    'blues': [('motif', None), ('half', 'fall'), ('again', 0), ('again', 1), ('line', 'arch'), ('land', 'fall')],
}
WALTZ_PLANS = {
    'A': [('motif', None), ('line', 'arch'), ('develop', None), ('half', 'fall'), ('motif', None),
          ('line', 'rise'), ('answer', None), ('land', 'fall')],
    'B': [('contrast', None), ('line', 'rise'), ('contrast', None), ('half', 'fall'), ('contrast', None),
          ('line', 'arch'), ('line', 'rise'), ('half', 'fall')],
    'C': [('motif', None), ('line', 'arch'), ('develop', None), ('half', 'fall'), ('line', 'arch'),
          ('line', 'rise'), ('line', 'arch'), ('land', 'fall')],
}


def phrase_plans(genre: Genre, meter: int) -> dict:
    """The phrase plans of a genre: PLANS / WALTZ_PLANS with the genre's plan['phrases'] / plan['waltz_phrases'] on
    top (a singable genre: [motif, half, develop, land] - a breath at every 4-bar phrase end)."""
    base = dict(WALTZ_PLANS if meter == 3 else PLANS)
    base.update(genre.plan.get('waltz_phrases' if meter == 3 else 'phrases') or {})
    return base


def _sus_budget(changes: dict, order: list, H: dict, t_pc: int, sharps: bool, minor: bool,
                rng: random.Random) -> dict:
    """A tune's dominant arrivals spelled more than one way (a genre's harmony 'sus_budget' {kept: weight} and
    'sus_swap' {'7' / 'ii' / 'IV': weight}; new-age round r10: every phrase of a minor piece closing Vsus4 - V,
    eleven times in 60 bars): of the dominant's sus4 chords (Vsus4 - V, or a lone Vsus4) a drawn number stays, each
    other one becomes V7 (the pair merged), ii - V or IV - V (the sus4's span the predominant's)."""
    dom = (t_pc + 7) % 12
    spots = [(p, i) for p in order for i, (sym, _) in enumerate(changes[p])
             if 'sus4' in sym and chord(sym).root % 12 == dom]
    keep = set(rng.sample(spots, min(len(spots), _pick(rng, H['sus_budget']))))
    out = {}
    for p in order:
        items, new, i = changes[p], [], 0
        while i < len(items):
            sym, b = items[i]
            if (p, i) not in spots or (p, i) in keep:
                new.append((sym, b))
                i += 1
                continue
            nxt = items[i + 1] if i + 1 < len(items) else None
            pair = nxt is not None and 'sus' not in nxt[0] and chord(nxt[0]).root % 12 == dom
            how = _pick(rng, H.get('sus_swap') or {'7': 1.0})
            v = spell(dom, sharps, 7)
            if new and how != '7' and chord(new[-1][0]).root % 12 == (t_pc + (2 if how == 'ii' else 5)) % 12:
                how = '7'                              # (no ii - ii - V)
            if how == '7' or not pair:
                new.append((v + '7', b + (nxt[1] if pair else 0.0)))
            elif how == 'ii':
                new += [(spell(t_pc + 2, sharps, 2) + ('m7b5' if minor else 'm7'), b), nxt]
            else:
                new += [(spell(t_pc + 5, sharps, 5) + ('m' if minor else ''), b), nxt]
            i += 2 if pair else 1
        out[p] = new
    return out


def _choose_from(rng, table: dict, avoid=()):
    names = [n for n in table if n not in avoid] or list(table)
    return rng.choice(sorted(names))


def compose(genre: Genre, seed: int, mood: str | None = None, swing: float | bool | None = None,
            plan: dict | None = None) -> Tune:
    """A tune for `genre` from `seed` (deterministic). mood: one of the genre's moods (None: rolled). swing: None /
    False = straight (the default: HUMAN_FEEDBACK), True = the genre's swing ratio, a number = that ratio - only where
    the rolled feel allows swing (a bossa stays straight); None and a feel with its own 'groove' ratio (lofi's lazy
    swing): that ratio (False keeps it straight). plan: a set_plan() entry pinning the tune's mood / feel /
    tempo / key / energy - or its form (each optional; the rest is rolled)."""
    plan = dict(plan or {})
    rng = random.Random(f"endless:{genre.name}:{seed}")
    mood = mood or plan.get('mood') or _pick(rng, {m: 1.0 for m in sorted(genre.moods)})
    if mood not in genre.moods:
        raise ComposeError(f"genre {genre.name!r} has no mood {mood!r}; moods: {', '.join(genre.moods)}")
    M = genre.moods[mood]
    forms = dict(M.get('forms', genre.forms))

    def pair(form_, feel_):                  # the feel / form pairing (FEEL_FORMS: (even, swung) or one weight)
        w = FEEL_FORMS.get(form_, {}).get(feel_, 1.0)
        w = w[1 if swing else 0] if isinstance(w, tuple) else w
        return 0.0 if form_ == 'blues' and genre.feels[feel_].get('meter', 4) == 3 else w
    feel = plan.get('feel')
    if feel and feel not in genre.feels:
        raise ComposeError(f"genre {genre.name!r} has no feel {feel!r}; feels: {', '.join(genre.feels)}")
    if plan.get('form'):
        form = plan['form']
        if form not in FORMS:
            raise ComposeError(f"plan form {form!r}: one of {', '.join(FORMS)}")
        fw = {x: v * pair(form, x) for x, v in M['feels'].items()}
        feel = feel or _pick(rng, fw if any(v > 0 for v in fw.values()) else M['feels'])
    elif feel:
        fw = {f: w * pair(f, feel) for f, w in forms.items()}
        form = _pick(rng, fw if any(v > 0 for v in fw.values()) else forms)
    else:
        tot = sum(M['feels'].values())
        form = _pick(rng, {f: w * min(1.0, 2 * sum(v * pair(f, x) for x, v in M['feels'].items()) / tot)
                           for f, w in forms.items()})
        feel = _pick(rng, {x: v * pair(form, x) for x, v in M['feels'].items()})
    F = genre.feels[feel]
    meter = F.get('meter', 4)
    if plan.get('key'):
        tonic, mode = plan['key'].split()
    else:
        mode = _pick(rng, M['modes'])
        tonic = rng.choice(M['keys'][mode])
    key = f"{tonic} {mode}"
    sharps = tonic in _SHARP_KEYS[mode]
    t_pc = Key(key).tonic % 12
    key_pcs = (RaisedPcs if genre.melody.get('raised_v') else set)(Key(key).pcs)
    lo_t, hi_t = F['tempo']
    tempo = int(plan['tempo']) if plan.get('tempo') else \
        int(round(min(hi_t, max(lo_t, rng.uniform(lo_t, hi_t) + M.get('tempo', 0)))))
    energy = float(plan.get('energy', (F.get('energy', 0.5) + M.get('energy', 0.5)) / 2))
    sw = None
    if swing and F.get('swing', True):
        sw = genre.swing if swing is True else float(swing)
    elif swing is None and F.get('groove'):              # the feel's own swing (lofi's lazy 8ths)
        sw = float(F['groove'])
    stretch = 2 if meter == 3 else 1
    FD = FORMS[form]
    B = genre.harmony['blocks'][mode]
    richness, trit = M.get('colour', 1.0), M.get('tritone', 0.0)

    # ---- the plan: a level per two-bar phrase from the form's tension curve (+ the tune's energy), the climax phrase
    order = list(FD['parts'])
    PL = phrase_plans(genre, meter)
    # a genre's plan['phrase_variants'] {'common' / 'waltz': {part kind: [(plan, weight)]}}: the period plan per part
    # kind drawn per tune (new-age audit 2026-10-13: one plan per kind in every piece - the A always peaking in its
    # third phrase, the chorus breathing every 4 bars)
    PV = (genre.plan.get('phrase_variants') or {}).get('waltz' if meter == 3 else 'common') or {}
    if PV:
        PL = dict(PL)
        for kind_ in sorted(PV):
            i_ = _pick(random.Random(f"phrases:{genre.name}:{seed}:{kind_}"),
                       {i: w for i, (_, w) in enumerate(PV[kind_])})
            PL[kind_] = PV[kind_][i_][0]
    plans = {p: PL['blues' if form == 'blues' else p[0]] for p in order}
    curve = genre.arc['forms'][form]
    bias = (energy - 0.5) * genre.arc['set'].get('energy_bias', 0.0)
    # a blues head's second chorus varies by phrase function (SECOND_CHORUS, drawn): which of its 2-bar units are
    # rewritten (the rest repeats the first chorus) and where the climax goes ('early': the first chorus's answer -
    # the tension curve read with its choruses swapped)
    vary = _pick(random.Random(f"second:{genre.name}:{seed}"), SECOND_CHORUS) if form == 'blues' else None
    fresh = {'answer': {4, 5}, 'early': {4, 5}, 'second': {2, 3, 5}}.get(vary)
    swap = 0.5 if vary == 'early' else 0.0
    raw = {p: [arc_at(curve, ((i + (u + 0.5) / len(plans[p])) / len(order) + swap) % 1.0)
               for u in range(len(plans[p]))] for i, p in enumerate(order)}
    levels = {p: [min(1.0, max(0.0, v + bias)) for v in raw[p]] for p in order}

    # where the single climax goes (PEAK_PART, drawn): the form's last section, or where its tension curve peaks
    peak_last = form == 'AABA' and _pick(random.Random(f"peak:{genre.name}:{seed}"), PEAK_PART) == 'last'
    # a genre's melody['restate'] {units: weight}: how many 2-bar units a later A restates (drawn per tune; new-age
    # round r2: A2 = A1's first 6 bars, the references leave the theme after 2-4)
    keep_units = _pick(random.Random(f"restate:{genre.name}:{seed}"), genre.melody['restate']) \
        if genre.melody.get('restate') and form != 'blues' else None

    def copied(p, u):
        # a theme is RESTATED: every later A plays the A1 note for note (re-fitted where its changes differ) up to its
        # cadence - the last two bars (a waltz: four) are its own; a blues head's second chorus repeats the first but
        # for its drawn units; an AABA's last A carrying the climax restates only its first phrase
        if p == order[0] or p[0] != 'A':
            return False
        if peak_last and p == order[-1]:
            return u < max(1, len(plans[p]) // 2 - 1)      # (its first phrase: room to climb to the peak)
        return u not in fresh if form == 'blues' else \
            u < min(len(plans[p]) - stretch, keep_units if keep_units is not None else len(plans[p]))

    # a genre's melody['half_line'] {part kind: share}: an inner half cadence of that part kind runs on as a rising line
    # (drawn per tune and unit; new-age round r5: a lone held note in every chorus's 4th bar)
    HL = genre.melody.get('half_line') or {}
    hl_rng = random.Random(f"half-line:{genre.name}:{seed}")
    half_line = {(p, u) for p in order if p[0] in HL for u, (r_, _) in enumerate(plans[p])
                 if r_ == 'half' and u < len(plans[p]) - 1 and hl_rng.random() < HL[p[0]]}

    def role_of(p, u):                       # a rewritten 'again' unit of a blues' second chorus: its own material
        if (p, u) in half_line:
            return 'line', 'rise'
        role, shape_ = plans[p][u]
        if role == 'again' and p != order[0] and not copied(p, u):
            return ('develop', None) if shape_ == 0 else ('half', 'fall')
        return role, shape_

    def source(p, u):                        # an A1 unit a later A restates: the single climax cannot sit there
        return p == order[0] and any(copied(q, u) for q in order[1:])
    cands = [(raw[p][u], -i, -u, p, u) for i, p in enumerate(order) for u in range(len(plans[p]))
             if role_of(p, u)[0] in genre.arc['climax'] and not copied(p, u) and not source(p, u)
             and (u > 0 or role_of(p, u)[0] != 'motif')]
    if vary:
        want = order[0] if vary == 'early' else order[1]
        cands = [c for c in cands if c[3] == want] or cands
    if peak_last:
        cands = [c for c in cands if c[3] == order[-1]] or cands
        cands = [c for c in cands if -c[2] > len(plans[order[-1]]) // 2] or cands     # (room to climb to it)
    climax_part, climax_unit = max(cands)[3:]
    # a genre's (or mood's) melody 'climax_parts' {part: weight}: where the head's climax goes is drawn per tune - the
    # part, then its phrase weighted by the curve's level (the learned generator's finding 2026-10-12: every new-age
    # climax in part C bar 4-5, 87-91 % of the head - the curve's maximum alone)
    cparts = M.get('climax_parts', genre.melody.get('climax_parts'))
    if cparts and not vary and not peak_last:
        crng = random.Random(f"climax-part:{genre.name}:{seed}")
        have = {p: w for p, w in sorted(cparts.items()) if w > 0 and any(c[3] == p for c in cands)}
        if have:
            want = _pick(crng, have)
            pool = sorted(c for c in cands if c[3] == want)
            climax_part, climax_unit = _pick(crng, {(c[3], c[4]): max(1e-3, c[0]) ** 2 for c in pool})

    # the set-level draws (genre.plan['set']: layout / climax kind / register shift / the chorus's block) - a set
    # plan's pins, else drawn here with their own dice (set_draws); the hook block (per mode) is the harmony's, not
    # the players' (Tune.arrange keeps the others)
    arrange = {k: plan.get(k, v) for k, v in set_draws(genre, random.Random(f"set-draws:{genre.name}:{seed}")).items()}
    block_pins = {}
    for k_ in BLOCK_PINS:                              # (the set's chord blocks: the harmony's, not the players')
        v_ = arrange.pop(k_, None)
        block_pins[k_] = v_.get(mode) if isinstance(v_, dict) else v_

    # ---- the changes: blocks per part
    blocks: dict = {}
    if FD.get('blocks'):
        # a form that names its blocks per part (FORMS 'verse'): an 'open' is drawn once (every A opens alike), the
        # other kinds per part, not twice the same
        drawn: dict = {}
        for p_ in order:
            bl = []
            for k in FD['blocks'][p_]:
                n = drawn[k][0] if k == 'open' and k in drawn else \
                    _choose_from(rng, B[k], avoid=drawn.get(k, ()))
                if block_pins.get(k) in B[k] and not (k == 'open' and len(drawn.get(k, ())) > 0):
                    n = block_pins[k]                  # (the set's draw: rng thrown as before, the pin wins)
                drawn.setdefault(k, []).append(n)
                bl.append((k, n))
            blocks[p_] = bl
    elif form == 'blues':
        bl = _choose_from(rng, B['blues'])
        blocks = {'A1': [('blues', bl)], 'A2': [('blues', bl)]}
    else:
        opener = _choose_from(rng, B['open'])
        if form == 'AABA':
            closes = [_choose_from(rng, B['turn']), _choose_from(rng, B['to_bridge']), _choose_from(rng, B['final'])]
            bridge = _choose_from(rng, B['bridge'])
            # the A2 leads into the bridge: a ii-V into IV when the bridge opens on IV, else it cadences home
            into = ('to_bridge', closes[1]) if parse_block(B['bridge'][bridge])[0][0] == 5 else \
                ('final', _choose_from(rng, B['final'], avoid=(closes[2],)))
            blocks = {'A1': [('open', opener), ('turn', closes[0])], 'A2': [('open', opener), into],
                      'B': [('bridge', bridge)], 'A3': [('open', opener), ('final', closes[2])]}
        else:
            turn = _choose_from(rng, B['turn'])
            blocks = {'A1': [('open', opener), ('turn', turn)], 'B': [('contrast', _choose_from(rng, B['contrast']))],
                      'A2': [('open', opener), ('turn', _choose_from(rng, B['turn'], avoid=(turn,)))],
                      'C': [('climb', _choose_from(rng, B['climb'])), ('final', _choose_from(rng, B['final']))]}
    # colour once per distinct block text, so equal openings stay equal in every A
    crng = random.Random(rng.random())
    coloured: dict = {}
    changes: dict = {}
    for i, p in enumerate(order):
        out = []
        rich_p = richness * targets(genre, sum(levels[p]) / len(levels[p]))['colour']   # tenser parts colour richer
        for j, (k, n) in enumerate(blocks[p]):
            # what follows the block: the next block of the part, else the next part's first chord (the form loops);
            # an opening is coloured once, in the A1's context, so every A starts alike
            nb = blocks[p][j + 1] if j + 1 < len(blocks[p]) else blocks[order[(i + 1) % len(order)]][0]
            nxt = parse_block(B[nb[0]][nb[1]])[0]
            ck = (k, n) if k in ('open', 'blues') else (k, n, nxt[:2])
            if ck not in coloured:
                coloured[ck] = colour(parse_block(B[k][n]), crng, richness=rich_p, tritone=trit,
                                      blues=form == 'blues', after=nxt, colours=genre.harmony['colours'])
            out += coloured[ck]
        changes[p] = [(chord_name(t_pc, off, q, sharps), b * meter * stretch) for off, q, b in out]
    if genre.harmony.get('sus_budget'):
        changes = _sus_budget(changes, order, genre.harmony, t_pc, sharps, mode == 'minor',
                              random.Random(f"sus:{genre.name}:{seed}"))
    solo_charts = []
    if form == 'blues':
        # the head's second chorus ends another way (its second ending: a turnaround / the cadence before it played
        # as a CHART_VARIANTS variant, drawn) - the melody is written over it; the solo's choruses play the first or
        # the second chorus's chart, drawn chorus by chorus
        vr = random.Random(f"second-ending:{genre.name}:{seed}")
        if vr.random() < 0.75:
            items, kinds = changes['A2'], dict(CHART_VARIANTS)
            late = [i for i in _cadences(items) if _beats(items[:i]) >= 8 * meter - 1e-6]
            at_ = vr.choice(late) if late else None
            while kinds and at_ is not None:
                k = _pick(vr, kinds)
                v = variant(items, k, t_pc, sharps, meter * stretch, at=at_)
                if v:
                    changes['A2'] = v
                    break
                kinds.pop(k)
        solo_charts = [vr.choice(order) for _ in range(FD['solo'])]
    for p in FD['parts']:
        bars = sum(b for _, b in changes[p]) / meter
        if abs(bars - FD['bars'] * stretch) > 1e-6:
            raise ComposeError(f"internal: part {p} has {bars:g} bars, the form wants {FD['bars'] * stretch}")

    # ---- the melody: the notes fill the plan (every unit's centre / ceiling from its level)
    # (the register shift moves the whole line, and so the climax pitch)
    sh = int(arrange.get('shift', 0))
    reg = M.get('register', genre.melody['register'])
    lo, hi = note(reg[0]) + sh, note(reg[1]) + sh
    peak = note(M.get('peak', genre.melody.get('peak', reg[1]))) + sh   # (a mood may move the centre / peak too)
    center = note(M.get('center', genre.melody.get('center', note_name((lo - sh + hi - sh) // 2)))) + sh
    fam = CELLS[F['cells']]
    mrng = random.Random(rng.random())
    # a genre's melody['openings'] {motif cell: weight} (default 1): how the theme and the chorus open, drawn by
    # weight (new-age round r10: a chorus on three empty beats and a beat-4 pickup in three of four pieces)
    OW = genre.melody.get('openings')

    def opening(avoid=()):
        if not OW:
            return _choose_from(mrng, fam['motif'], avoid=avoid)
        return _pick(mrng, {k: OW.get(k, 1.0) for k in sorted(fam['motif']) if k not in avoid}
                     or {k: OW.get(k, 1.0) for k in sorted(fam['motif'])})
    motif_cell = fam['motif'][opening()]
    line_cell = fam['line'][_choose_from(mrng, fam['line'])]
    contrast_cell = fam['motif'][opening(avoid=[k for k, v in fam['motif'].items() if v == motif_cell])]
    motif_shape = _pick(mrng, {'arch': 3, 'rise': 2, 'valley': 1, 'fall': 1})
    n_motif = sum(1 for x in motif_cell if x > 0)
    steps = genre.melody.get('steps')                    # the contour's move sizes (STEPS; a singable genre: steps)
    motif_deltas = _contour(n_motif, motif_shape, mrng, steps)
    cum = [sum(motif_deltas[1:k + 1]) for k in range(n_motif)]
    hook_lift = round(1.7 * sum(cum) / n_motif)          # how far the hook's mean sits above its first note
    seq_step = mrng.choice([-2, -1, 1, 2])
    # the hook as a 1-bar cell and its sequence along the root motion (genre.melody['hook_seq'] of the tunes; blind
    # round 6: composed heads state one cell and sequence it - diatonic or chromatic - with the chords)
    hook_seq = random.Random(f"hook-seq:{genre.name}:{seed}").random() < genre.melody.get('hook_seq', 0.0)
    arng = random.Random(f"arc:{genre.name}:{seed}")           # the plan's own dice (the rest of the tune unchanged)
    # the bridge's counter-motif: its own rhythm, the hook's contour turned upside down, one for the whole tune
    # (a genre's melody['counter'] {'mirror' / 'own': weight}: the hook's shape upside down, or a shape of its own)
    cshape = motif_shape
    if genre.melody.get('counter') and _pick(arng, genre.melody['counter']) == 'own':
        cshape = _pick(arng, {'arch': 3, 'rise': 2, 'valley': 1, 'fall': 1})
    counter_deltas = [-d for d in _contour(sum(1 for x in contrast_cell if x > 0), cshape, arng, steps)]
    counter_off = arng.choice([1, 2, 3])
    b_line_cell = fam['line'][_choose_from(arng, fam['line'], avoid=[k for k, v in fam['line'].items()
                                                                      if v == line_cell])]
    # the bridge's own rhythm, one for the whole tune: mostly long notes (CELLS 'long') against the moving lines,
    # sometimes its counter-motif cell
    lrng = random.Random(f"bridge-cell:{genre.name}:{seed}")
    bridge_cell = fam['long'][_choose_from(lrng, fam['long'])] if fam.get('long') and \
        lrng.random() < genre.melody.get('bridge_long', 0.7) \
        else contrast_cell
    by_n = sorted(fam['line'], key=lambda k: (sum(1 for x in fam['line'][k] if x > 0), k))
    sparse_cell, dense_cell = fam['line'][by_n[0]], fam['line'][by_n[-1]]
    unit_beats = 2 * meter
    tonic_info = ChordInfo(spell(t_pc, sharps) + ('maj7' if mode == 'major' else 'm7'))
    final_pcs = {tonic_info.root, tonic_info.third, (tonic_info.root + 7) % 12} - {None}
    under = peak - 4                                     # every phrase but the climax stays at or under this
    T = {p: [targets(genre, v) for v in levels[p]] for p in order}

    # the period plan (CONTOURS, drawn per part kind): every 4-bar phrase gets its own register and goal, the part
    # peaks 60-75 % through it, the bridge sits in its own register (BRIDGE_SHIFT) - before a single note is chosen
    krng = random.Random(f"contour:{genre.name}:{seed}")
    # (a genre's melody['contours'] / ['shift'] add part kinds and registers: verse's hook B and build C)
    CT = dict(CONTOURS, **(genre.melody.get('contours') or {}))
    SH = dict({'B': BRIDGE_SHIFT}, **(genre.melody.get('shift') or {}))
    ckind = {p: 'blues' if form == 'blues' else 'B' if p[0] == 'B' and form in ('AABA', 'verse') else
             'C' if p[0] == 'C' and 'C' in CT else 'A' for p in order}
    shapes, lifts = {}, {}
    for k in sorted(set(ckind.values())):
        cname = _pick(krng, {n: w for n, (_, w) in CT[k].items()})
        amp, shift = krng.uniform(0.8, 1.25), (_pick(krng, SH[k]) if k in SH else 0)
        lifts[k] = max(0, shift)                         # (the bridge's ceiling rises with its register)
        shapes[k] = [(x, y * amp + shift) for x, y in CT[k][cname][0]]

    def contour(p, u):
        return arc_at(shapes[ckind[p]], (u + 0.5) / len(plans[p]))

    def u_center(p, u):
        return center + round(T[p][u]['center'] + contour(p, u))
    peak_u = {p: max(range(len(plans[p])), key=lambda u: (contour(p, u), -u)) for p in order}

    def u_hi(p, u):
        # the climax phrase is filled under `under` too, then its top note raised; every other phrase stays under its
        # part's ceiling by as much as the contour sits under its peak (the part's top note in its peak phrase)
        if (p, u) == (climax_part, climax_unit):
            return under
        drop = max(contour(p, x) for x in range(len(plans[p]))) - contour(p, u)
        return min(under, hi + round(T[p][u]['ceiling']) + lifts[ckind[p]]) - round(drop)

    def toward(prev, p, u, off, most):
        """A phrase's first target: from the note before, at most `most` semitones toward its centre (+ off)."""
        c = u_center(p, u) + off
        return c if prev is None else prev + max(-most, min(most, c - prev))
    melody: dict = {}
    retries = 0
    hook_start = None                      # the hook's planned first pitch (A1)
    climax_pitch = None
    for p in FD['parts']:
        plan_p = plans[p]
        harm = Harm(changes[p], key_pcs)
        last_part = p == FD['parts'][-1]
        p_hi = peak if p == climax_part else under
        # the bars that repeat a riff (a blues' AAB 'again'): the rhythm budget counts the riff once
        riff_bars = {b for u, (r_, _) in enumerate(plan_p) if role_of(p, u)[0] == 'again'
                     for b in (2 * u, 2 * u + 1)}
        best, best_n = None, 1e9
        for attempt in range(80):
            prng = random.Random(f"{seed}:{p}:{attempt}")
            notes, prev = [], None
            motif_start = hook_start if hook_start is not None else \
                u_center(p, 0) - hook_lift + prng.choice([-2, -1, 0, 1])          # the hook centred on its target
            hook_c = u_center(order[0], 0)
            peak_at = None
            lead, goals, used = [None], [], {}
            starts = []                          # the index of every unit's first note
            for u in range(len(plan_p)):
                role, shape = role_of(p, u)
                t0 = u * unit_beats
                starts.append(len(notes))
                if u % 2 == 0:
                    used = {}                    # a 4-bar phrase's pitches (circling one pitch is a tell)
                ctx = _Ctx(harm, meter, lo, u_hi(p, u), prng, used, lead,
                           tuple(genre.melody.get('repeat', (0.7, 0.0))), genre.melody.get('chromatic', 0.3))
                lv = levels[p][u]
                restate = copied(p, u)
                if restate or role == 'again':
                    # the A1's unit restated (a blues' AAB: this part's own unit `shape` again, re-fitted on the IV)
                    k = u if restate else shape
                    src = melody[order[0]] if restate else notes
                    out = [(s_ + (u - k) * unit_beats, d_, n_) for s_, d_, n_ in src
                           if k * unit_beats - 1e-6 <= s_ < (k + 1) * unit_beats - 1e-6]
                    same = restate and _slice_changes(changes[p], t0, t0 + unit_beats) == \
                        _slice_changes(changes[order[0]], t0, t0 + unit_beats)
                    notes += out if same else _refit(out, harm, meter, lo, under, prev=notes[-1][2] if notes else None)
                    prev = notes[-1][2] if notes else prev
                    continue
                if role in ('land', 'half'):
                    # the phrase's ending (PHRASE_ENDS, drawn; the tune's final cadence lands on the downbeat) and its
                    # GOAL: a landing pitch planned from the contour, never the last phrase's landing again
                    final = role == 'land' and last_part
                    ends = BRIDGE_ENDS if p[0] == 'B' and u == len(plan_p) - 1 and form != 'verse' else \
                        genre.melody.get('ends', PHRASE_ENDS)
                    e_kind = 'down' if final else _pick(prng, ends)
                    # (a half cadence of an A grows from the hook: its cell's first bar, then the landing - drawn,
                    # genre.melody['half_cell'] of them)
                    grown = _cell_ending(_vary_cell(motif_cell, _pick(prng, {'same': 1.0, 'displace': 1.0}),
                                                    2 * meter), e_kind, 2 * meter) \
                        if role == 'half' and p[0] == 'A' and genre.melody.get('half_cell') and \
                        prng.random() < genre.melody['half_cell'] else None
                    cell = grown or _ending_cell(fam['land'], e_kind, prng, 2 * meter)
                    li = _land_index(cell, 2 * meter)
                    ev = _events(cell, t0, meter)
                    land_at = ev[sum(1 for x in cell[:li] if x > 0)]
                    tonic_there = harm.under(*land_at[:2]).root == t_pc
                    pcs = final_pcs if (final and tonic_there) else None
                    goal = u_center(p, u) - (1 if role == 'half' else 3)
                    if goals and abs(goal - goals[-1]) < 2:
                        goal += prng.choice((-3, 3))
                    goals.append(goal)
                    dl = _contour(len(ev), shape or 'fall', prng, steps)
                    if grown:                    # the hook's intervals (now and then turned over), then the landing
                        k_ = min(len(ev) - 1, n_motif)
                        sgn = -1 if prng.random() < 0.35 else 1
                        dl = [sgn * d for d in motif_deltas[:k_]] + dl[k_:]
                    out = _fit(ev, dl, ctx, prev, first=toward(prev, p, u, -2, 3),
                               land=ev.index(land_at), land_pcs=pcs, goal=goal)
                elif role in ('motif', 'develop', 'answer'):
                    # the hook's rhythm, developed in a 'develop' / 'answer' phrase (DEVELOP_RHYTHM, drawn)
                    ev = _events(motif_cell if role == 'motif' else
                                 _vary_cell(motif_cell, _pick(prng, DEVELOP_RHYTHM), 2 * meter), t0, meter)
                    dl = list(motif_deltas)
                    first = motif_start + u_center(p, u) - hook_c          # the hook follows the phrase's register
                    if prev is not None and abs(first - prev) > 7:      # (an octave nearer the note before it)
                        first -= 12 * round((first - prev) / 12)
                    if role == 'develop':                            # the hook sequenced a step up / down
                        first = _scale_step(first, seq_step, harm.under(ev[0][0], ev[0][1]).scale)
                    elif role == 'answer':
                        dl = dl[:len(dl) // 2] + [-d for d in dl[len(dl) // 2:]]
                    out = _fit(ev, dl, ctx, prev, first=first)
                    if role != 'answer' and hook_seq:
                        out = _sequenced(out, harm, meter, t0, ctx.lo, ctx.hi)
                elif role == 'contrast':
                    k_ = sum(1 for r_, _ in plan_p[:u] if r_ == 'contrast')       # its return: sequenced, its
                    rc = _vary_cell(bridge_cell, _pick(prng, genre.melody['bridge_return']), 2 * meter) \
                        if k_ and genre.melody.get('bridge_return') else bridge_cell      # rhythm varied
                    ev = _events(rc, t0, meter)
                    first = u_center(p, u) + counter_off
                    if k_:
                        first = _scale_step(first, (1 if k_ % 2 else -1) * (1 + k_ // 2),
                                            harm.under(ev[0][0], ev[0][1]).scale)
                    out = _fit(ev, counter_deltas, ctx, prev, first=first)
                    if hook_seq:                 # (its own cell sequenced along the bridge's root motion)
                        out = _sequenced(out, harm, meter, t0, ctx.lo, ctx.hi)
                else:                                            # line: its density and direction from the plan
                    lo_c, hi_c = genre.arc['targets']['cells']
                    own = b_line_cell if p[0] == 'B' else line_cell
                    cell = sparse_cell if lv < lo_c else dense_cell if lv > hi_c else \
                        own if prng.random() < 0.7 else fam['line'][_choose_from(prng, fam['line'])]
                    ev = _events(cell, t0, meter)
                    if prev is not None and u_center(p, u) - prev > 2:
                        shape = 'rise'
                    elif prev is not None and prev - u_center(p, u) > 4:
                        shape = 'fall'
                    out = _fit(ev, _contour(len(ev), shape or 'arch', prng, steps), ctx, prev, first=toward(prev, p, u, 0, 4))
                back = u and not copied(p, u - 1) and role_of(p, u - 1)[0] != 'again'
                if u == peak_u[p] and (p, u) != (climax_part, climax_unit) and len(out) >= 4:
                    # the part's own peak (its contour's top phrase): its top note in the phrase's second half - the
                    # period rises to it 60-75 % through, then falls
                    h = len(out) // 2
                    j = max(range(h, len(out)), key=lambda k: (out[k][2], out[k][1]))
                    m0 = max(n[2] for n in notes + out[:h])
                    ci = harm.under(out[j][0], out[j][1])
                    up = [c for c in range(m0 + 1, min(ctx.hi, m0 + 4) + 1) if c % 12 in ci.core | ci.tensions]
                    if out[j][2] <= m0 and up and abs(up[0] - out[j - 1][2]) <= 7 and \
                            (j + 1 == len(out) or abs(up[0] - out[j + 1][2]) <= 5):
                        out[j] = (out[j][0], out[j][1], up[0])
                if (p, u) == (climax_part, climax_unit) and out:
                    # THE climax: the phrase's top note raised to the highest chord tone / tension under the peak -
                    # after restated material not its first note (the approach climbs inside the phrase), and not its
                    # last when it can be helped (the release falls inside the phrase)
                    j0 = 0 if back else min(3, max(1, len(out) - 2))
                    j = max(range(j0, len(out) - 1 if len(out) - 1 > j0 else len(out)),
                            key=lambda k: (out[k][2], out[k][1]))
                    st, du, _ = out[j]
                    ci = harm.under(st, du)
                    top = [c for c in range(peak - 3, peak + 1) if c % 12 in ci.core | ci.tensions]
                    if top:
                        out[j] = (st, du, max(top))
                    peak_at = len(notes) + j
                notes += out
                if peak_at is not None and u == climax_unit:
                    # the approach may reach back into the phrase before (not into restated material)
                    _approach(notes, peak_at, harm, first=starts[u - 1] if back else peak_at - j)
                prev = notes[-1][2] if notes else prev
            if peak_at is not None:                  # the release reaches into the phrase after the climax
                _approach(notes, peak_at, harm, first=peak_at)
            # a tension on a strong beat resolved by step in (nearly) every fresh 4-bar phrase: an appoggiatura or
            # a suspension, drawn where it goes (blind round 4: chord tones re-pitched per chord)
            ph = 4 * meter
            # (a restated unit stays the A1's notes: the tension goes into the part's own bars)
            fixed = {j for u in range(len(plan_p)) if copied(p, u)
                     for j in range(starts[u], starts[u + 1] if u + 1 < len(starts) else len(notes))}
            if peak_at is not None:
                fixed.add(peak_at)
            # (a genre's melody['plain_head']: the first notes of every hook statement stay chord tones - new-age
            # round r5: the theme's head on non-chord tones, G over Dm)
            for u in range(len(plan_p)):
                if role_of(p, u)[0] == 'motif' and u < len(starts):
                    fixed.update(range(starts[u], starts[u] + genre.melody.get('plain_head', 0)))
            for k in range(int(round(harm.length / ph))):
                us = (2 * k, 2 * k + 1)
                if all(copied(p, x) or role_of(p, x)[0] == 'again' for x in us if x < len(plan_p)) \
                        or prng.random() >= 0.78:
                    continue
                _appoggiatura(notes, harm, meter, k * ph, (k + 1) * ph, lo, p_hi, prng, keep=fixed)
            _smooth_leaps(notes, harm, meter, lo, p_hi, keep={peak_at} if peak_at is not None else ())
            issues = melody_issues(notes, harm, lo - 2, p_hi + 2, meter=meter,
                                   final_pcs=final_pcs if last_part else None)
            if p == climax_part:
                if peak_at is None or notes[peak_at][2] < peak - 3:
                    issues.append('no climax')
                elif any(n[2] >= notes[peak_at][2] for k, n in enumerate(notes) if k != peak_at):
                    issues.append('climax not the single top')
                elif peak_at + 1 < len(notes) and notes[peak_at + 1][2] >= notes[peak_at][2]:
                    issues.append('climax not released')
                elif peak_at and notes[peak_at][2] - notes[peak_at - 1][2] > 7:
                    issues.append('climax leapt to')
            elif any(n[2] > under for n in notes):
                issues.append('over the climax')
            # the style rules weigh less than the hard ones (a clash): the best attempt keeps the hard rules
            lands = {2 * u + 1 for u in range(len(plan_p)) if role_of(p, u)[0] in ('land', 'half')} \
                if 'pads' in genre.melody else None
            soft = _style_issues(notes, meter, harm.length, riff_bars, span=12 if p[0] == 'A' else 0, lands=lands,
                                 pads=genre.melody.get('pads', 0.125))
            score = len(issues) + 0.3 * len(soft)
            if score < best_n:
                best, best_n = notes, score
                if p == climax_part and peak_at is not None:
                    climax_pitch = (notes[peak_at][0], notes[peak_at][2])
            if not issues and not soft:
                break
            retries += 1
            if attempt >= 39 and best_n < 1:      # (40 tries for the style rules; up to 80 for a hard one)
                break
        melody[p] = best
        if p == order[0]:
            hook_start = best[0][2] if best else center

    # ---- the frame: the intro is its own material (a vamp from INTROS with the hook over it), the tag reprises it with
    # a twist (the tritone sub into the end chord, whose colour comes from ENDINGS)
    a1, last = order[0], order[-1]
    end_q = _pick(random.Random(rng.random()), genre.harmony['endings'][mode])
    motif = [n for n in melody[a1] if n[0] < unit_beats]
    top = max(n[2] for p in order for n in melody[p])
    intro, tag = frame(changes[a1], melody[a1], mode, t_pc, sharps, meter, stretch, key_pcs, top,
                       random.Random(f"frame:{genre.name}:{seed}"), genre.harmony)
    counter = [n for n in melody['B'] if n[0] < unit_beats] if 'B' in order else []   # the bridge's motif
    # the solo plays the tune's own chart; plan['solo']['reharm'] of the tunes reharmonize ONE dominant of a head-out
    # part (drawn: the slot is not always the last cadence) - in the last solo chorus and the head out alike, the
    # melody given a colour of the substitute (perform: the 'v' parts); a blues: its last chorus
    srng = random.Random(f"solo-changes:{genre.name}:{seed}")
    # the head out's parts (OUT_PARTS, a jazz plan's: drawn - the whole head, from the bridge, the last A)
    out_parts = list(_pick(random.Random(f"out-parts:{genre.name}:{seed}"), OUT_PARTS[form])) \
        if genre.plan.get('solo') and form in OUT_PARTS else list(FD['out'])
    reharm_in = _pick(random.Random(f"reharm-in:{genre.name}:{seed}"),
                      (genre.plan.get('solo') or {}).get('reharm_in') or {'both': 1.0})
    solo_changes, out_melody = {}, {}
    if genre.plan.get('solo') and srng.random() < genre.plan['solo'].get('reharm', 0.5):   # (a jazz plan's reharm)
        rp = last if form == 'blues' else srng.choice(out_parts)
        fp = final_pcs if rp == last else None
        ch = reharm(changes[rp], t_pc, sharps, meter * stretch, srng)
        mel = _new_note(melody[rp], changes[rp], ch, meter, lo, under, key_pcs, fp) if ch else None
        if mel and mel != melody[rp]:                  # (the substitute heard in the line, or no reharm)
            solo_changes[rp], out_melody[rp] = ch, mel
    # the whole piece's dynamic plan (genre.plan['dynamics'], drawn by weight): a shout plan lifts the first head-out
    # part's top note over the head's climax, approached and released (perform: the 2 bars around it are the shout)
    # the solo's shape (genre.plan['solo']['shapes'], drawn per tune) and whether it goes double time once (in at most
    # ~40 % of the tunes, at a drawn place: perform.solo_arc); a shape may ask for its dynamic plans (a slow build
    # leaves the peak to the head out)
    S_ = genre.plan.get('solo') or {}
    shapes_s = S_.get('shapes') or {}
    shrng = random.Random(f"solo-shape:{genre.name}:{seed}")
    solo_shape = _pick(shrng, {k: v['weight'] for k, v in shapes_s.items()}) if shapes_s else None
    sh = shapes_s.get(solo_shape, {})
    double = bool(sh.get('double', True)) and shrng.random() < S_.get('double', 0.0)
    plans_d = genre.plan.get('dynamics') or {'solo': {'weight': 1.0}}
    dyn = _pick(random.Random(f"dynamics:{genre.name}:{seed}"),
                {k: v['weight'] for k, v in plans_d.items() if not sh.get('dynamics') or k in sh['dynamics']})
    shout = bool(plans_d[dyn].get('shout'))
    if shout or plans_d[dyn].get('out_peak'):          # (a plan with its peak in the head out: its top note too)
        sp = out_parts[0]
        lifted = _lift(out_melody.get(sp, melody[sp]), Harm(solo_changes.get(sp, changes[sp]), key_pcs), top, meter,
                       lo)
        if lifted:
            out_melody[sp] = lifted
    # a piano arrangement's climax section (plan['sections'] with melody 'lift'): its part with one top note lifted
    # over the head's highest note, approached and released (_lift) - the piece's single peak
    for sd in genre.plan.get('sections') or []:
        if sd.get('melody') == 'lift' and sd.get('part') in melody and sd['part'] not in out_melody:
            lifted = _lift(melody[sd['part']], Harm(changes[sd['part']], key_pcs), top, meter, lo)
            if lifted:
                out_melody[sd['part']] = lifted
    return Tune(genre=genre.name, seed=seed, mood=mood, title=title(rng, feel, form, genre.titles, key), key=key,
                mode=mode,
                tempo=tempo, meter=meter, feel=feel, swing=sw, form=form, parts=list(FD['parts']), changes=changes,
                melody=melody, motif=motif, intro=intro, tag=tag, end_chord=spell(t_pc, sharps) + end_q,
                blocks={p: [n for _, n in blocks[p]] for p in FD['parts']}, retries=retries,
                energy=round(energy, 3), levels=levels, counter=counter, solo_changes=solo_changes,
                out_melody=out_melody, shout=shout, dynamics=dyn, solo_shape=solo_shape, double=double,
                solo_charts=solo_charts, end_kind=_pick(random.Random(f"end:{genre.name}:{seed}"),
                                                     genre.plan.get('end_styles', END_STYLES)),
                second=vary, out_parts=out_parts, reharm_in=reharm_in, arrange=arrange,
                climax={'part': climax_part, 'unit': climax_unit, 'beat': climax_pitch[0],
                        'pitch': climax_pitch[1]} if climax_pitch else {})


def frame(changes_a1, mel_a1, mode: str, t_pc: int, sharps: bool, meter: int, stretch: int, key_pcs, top: int,
          rng: random.Random, harmony: dict | None = None) -> tuple[dict, dict]:
    """The intro and the tag (4 bars; a waltz 8): a vamp from INTROS (the head opening on the tonic allows the tonic
    vamps) with a line from INTRO_LINES over it (drawn - a fragment of the hook developed, never the head's bars:
    its first bar augmented and sequenced, its first notes as a cell sequenced bar by bar, its rhythm with the contour
    turned and the fragment augmented, or the voicings alone; the riff vamp: the hook itself an octave down, the left
    hand out), an octave up where that stays under the head's top note `top`, and the tag reprising the hook's
    fragment over the vamp (TAG_LINES, drawn) with a twist: the second half of its last bar an approach into the end
    chord drawn from TAG_APPROACH (the tritone sub, the backdoor bVII9, the minor plagal IVm6, a deceptive V-bVI, a
    cold stop on V7alt), its second half an octave up (where it fits), its last note held (a cold stop: struck
    short). Every line is re-fitted to the vamp's chords.
    {'kind', 'line', 'changes', 'melody', 'approach' (the tag's)}."""
    bar, ub = meter * stretch, 2 * meter
    H = harmony or {'intros': INTROS, 'intro_tonic': INTRO_TONIC, 'tag_approach': TAG_APPROACH}
    table = H['intros'][mode]
    on_tonic = chord(changes_a1[0][0]).root % 12 == t_pc
    kind = _pick(rng, {k: w for k, (_, w) in table.items() if on_tonic or k not in H.get('intro_tonic', ())})
    ch = []
    for tok in table[kind][0].split():
        if tok.startswith('head:'):
            ch += _slice_changes(changes_a1, 0, float(tok[5:]) * bar)
        else:
            ch += [(chord_name(t_pc, off, q, sharps), b * bar) for off, q, b in parse_block(tok)]
    # the tag's last half bar leads into the end chord (TAG_APPROACH, drawn: the dice after the intro's)
    approach = _pick(random.Random(f"{kind}:{rng.random()}"), H.get('tag_approach', TAG_APPROACH))
    # what the tag plays (H['tag_frames'], drawn - a genre without them reprises the intro): the intro's vamp, another
    # vamp, or the A's last four bars (the classic tag)
    frng = random.Random(f"tag-frame:{kind}:{approach}:{changes_a1}")
    tag_frame = _pick(frng, H['tag_frames']) if H.get('tag_frames') else 'reprise'
    base = ch
    if tag_frame == 'vamp':
        other = {k: w for k, (blk, w) in table.items() if k != kind and 'head:' not in blk
                 and (on_tonic or k not in H.get('intro_tonic', ()))}
        if other:
            base = [(chord_name(t_pc, off, q, sharps), b * bar) for off, q, b in
                    parse_block(table[_pick(frng, other)][0])]
        else:
            tag_frame = 'reprise'
    elif tag_frame == 'turnaround':
        total = _beats(changes_a1)
        base = _slice_changes(changes_a1, total - 4 * bar, total) if total >= 4 * bar - 1e-6 else ch
        if abs(_beats(base) - 4 * bar) > 1e-6:
            base, tag_frame = ch, 'reprise'
    v_, bvi = t_pc + 7, t_pc + 8

    def nm(off, q):
        return spell(t_pc + off, sharps, off) + q
    via = {'tritone': [(nm(1, '7#11'), 1.0)], 'backdoor': [(nm(10, '9'), 1.0)], 'plagal': [(nm(5, 'm6'), 1.0)],
           'deceptive': [(nm(7, '7b9'), 0.5), (nm(8, 'maj7#11'), 0.5)], 'cold': [(nm(7, '7alt'), 1.0)],
           'sus': [(nm(7, 'sus4'), 0.5), (nm(7, ''), 0.5)], 'IV': [(nm(5, ''), 1.0)],
           'ii': [(nm(2, 'm7'), 0.5), (nm(7, 'sus4'), 0.5)], 'IV_iv': [(nm(5, ''), 0.5), (nm(5, 'm6'), 0.5)],
           'vi': [(nm(9, 'm7'), 0.5), (nm(7, 'sus4'), 0.5)]}[approach]
    if mode == 'minor' and approach in ('ii', 'vi'):  # (the minor key's own degrees - new-age round r11: Am7 Gsus4
        via = [((nm(2, 'm7b5') if approach == 'ii' else nm(8, 'maj7')), 0.5), (nm(7, 'sus4'), 0.5)]  # in C minor)
    s_, b_ = base[-1]
    ap = H.get('tag_span', 0.5) * bar                  # (the approach's length: half a bar, a genre's whole bar)
    keep = b_ > ap + 1e-6 and chord(s_).root % 12 not in {chord(x).root % 12 for x, _ in via}   # (round r6: no
    # 'Vsus4 | ii Vsus4' split bar - the approach takes the whole held chord when it returns to its root)
    span = ap if keep else b_
    tag_ch = base[:-1] + ([(s_, b_ - ap)] if keep else []) + [(sym_, f * span) for sym_, f in via]
    L = 4 * bar
    units = [[(s - k * ub, d, p) for s, d, p in mel_a1 if k * ub - 1e-6 <= s < (k + 1) * ub - 1e-6] for k in (0, 1)]
    pitches = [p for u in units for _, _, p in u] or [top - 12]
    up = 12 if max(pitches) + 12 <= top - 2 else 0
    hook = sorted(units[0])                            # the A1's first phrase: the hook
    cell = [n for n in hook if n[0] < hook[0][0] + meter - 1e-6] if hook else []    # its first bar's worth
    if len(cell) < 3:
        cell = hook[:3]
    frag = [(s - hook[0][0], d, p) for s, d, p in hook[:3]]                          # its head: 3 notes
    # the lines over the vamps (INTRO_LINES / TAG_LINES, drawn): a fragment of the hook developed - augmented,
    # sequenced, its contour turned - never the head's bars copied onto new chords (blind round 5); the riff vamp
    # plays the hook itself
    lines = {'intro': 'hook' if kind == 'riff' else _pick(rng, H.get('intro_lines', INTRO_LINES)),
             'tag': _pick(random.Random(f"tag-line:{rng.random()}"), H.get('tag_lines', TAG_LINES))}

    def develop_line(how, name_='intro'):
        n = max(2, int(round(L / ub)))
        if how == 'augment':                           # the first bar twice as slow, again a step up ..., landed
            a = [(s * 2, d * 2, p) for s, d, p in [(s - cell[0][0], d, p) for s, d, p in cell]]
            out_ = []
            for k in range(n):
                st_ = [(s + k * ub, d, p + 2 * k) for s, d, p in a if s < ub - 0.5]
                out_ += st_ if k < n - 1 else st_[:2]
            return out_
        if how == 'fragment':                          # its first notes as a cell, sequenced up bar by bar, landed
            out_ = []
            for j in range(int(round(L / meter))):
                o, ph = j * meter, j % 4
                if ph == 3:
                    out_.append((o, meter - 0.5, frag[0][2] - 2 + 2 * (j // 4)))
                else:
                    out_ += [(s + o, d, p + 2 * ph) for s, d, p in (frag if ph < 2 else frag[:2])]
            return out_
        if how == 'head':                              # the hook's head (its first two bars) and its echo: the
            # intro plays the echo (its first bar a third up), the interlude the head; the tag the head, then the
            # head again in the home register over the approach (refitted) - the last note held under a bar (round
            # r1: an octave-low echo with a 5-beat hold was the stock ending; r2: a silent right hand over it)
            h = [(s - hook[0][0] + (hook[0][0] % 1.0), d, p) for s, d, p in hook]
            # (round r4: the intro's echo of one bar after the left hand's bars read as two placeholder notes - it
            # sings the whole head a third up)
            echo = [(s + ub, d, p + (4 if name_ == 'intro' else 0)) for s, d, p in h if s < ub - 1e-6]
            if echo:
                s, d, p = echo[-1]
                echo[-1] = (s, min(L - s, meter - 0.5), p)
            return [n for n in h if n[0] < ub - 1e-6] + echo
        # 'answer': the hook's rhythm with its contour turned (from its last note), then its fragment augmented
        f0, l0 = hook[0][2], hook[-1][2]
        out_ = [(s, d, l0 + (f0 - p)) for s, d, p in hook]
        for k in range(1, n):
            out_ += [(s * 2 + k * ub, d * 2, p + 2 * (k - 1)) for s, d, p in frag if s * 2 < ub - 0.5]
        return out_
    out = {}
    for name, changes in (('intro', ch), ('tag', tag_ch)):
        how = lines[name]
        reg = (lambda s: -12) if how == 'hook' else (lambda s: up) if name == 'intro' else \
            (lambda s: up if s >= L / 2 - 1e-6 else 0)
        if how == 'hook':                            # the riff: the hook alone, an octave low
            notes = [(s + k * ub, d, p) for k in range(int(round(L / ub))) for s, d, p in units[k % 2]]
        else:
            notes = develop_line(how, name) if hook else []
        notes = sorted((s, d, p + reg(s)) for s, d, p in notes)
        while notes and max(p for _, _, p in notes) >= top:      # (a sequence climbing over the head's top: lower)
            notes = [(s, d, p - 12) for s, d, p in notes]
        notes = [(s, min(d, notes[i + 1][0] - s) if i + 1 < len(notes) else d, p) for i, (s, d, p) in enumerate(notes)
                 if i + 1 == len(notes) or notes[i + 1][0] - s > 0.1]
        notes = [(s, min(d, L - s), p) for s, d, p in notes if s < L - 0.5]
        if name == 'tag' and notes:
            # the last note held into the end chord - a cold stop: struck short on the last chord, then silence
            if approach == 'cold':
                stop = L - span + 0.5
                notes = [n for n in notes if n[0] < stop - 0.25] or notes[:1]
                notes = [(s, min(d, stop - s), p) for s, d, p in notes]
            elif how != 'head':                      # (the head's echo breathes before the end chord)
                s, d, p = notes[-1]
                notes[-1] = (s, L - s, p)
        if name == 'intro' and notes:
            s, d, p = notes[-1]
            notes[-1] = (s, max(0.5, min(d, L - 0.5 - s)), p)    # a breath before the head
        ps = [p for _, _, p in notes] or [top - 12]
        out[name] = {'kind': kind, 'line': lines[name], 'changes': changes,
                     'approach': approach if name == 'tag' else None, 'frame': tag_frame if name == 'tag' else None,
                     'melody': _refit(notes, Harm(changes, key_pcs), meter, min(ps) - 2, max(ps) + 2,
                                      release=False)}
    return out['intro'], out['tag']


def _new_note(mel, old_changes, new_changes, meter, lo, hi, key_pcs, final_pcs):
    """The melody over a reharmonized part: re-fitted, and over each new chord the note struck with it (on its
    downbeat or anticipating it; else its longest note) moved to a COLOUR of the substitute - a tension (9 / #11 / 13 /
    b9), one the old chord did not have when it can (blind round 6: the melody ignored the reharms; the composed
    heads sing the substitute's #11 / b9 / 13), else a tone the old chord did not have. None when the result breaks
    the melody rules."""
    old, new = Harm(old_changes, key_pcs), Harm(new_changes, key_pcs)
    notes = _refit(mel, new, meter, lo, hi)
    for st0, d0, ci in new.items:
        if ci.sym == old.at(st0 + d0 / 2).sym:
            continue
        under_ = [k for k, (s, d, p) in enumerate(notes) if new.under(s, d) is ci]
        on = [k for k, (s, d, p) in enumerate(notes) if st0 - 0.5 - 1e-6 <= s < st0 + 1.0 - 1e-6 and s + d > st0 + 0.25]
        if not under_ and not on:
            continue
        k = on[0] if on else max(under_, key=lambda k: notes[k][1])
        s, d, p = notes[k]
        oc = old.under(s, d)
        near = range(max(lo, p - 4), min(hi, p + 4) + 1)
        tens = ci.tensions | ({(ci.root + 6) % 12} if (ci.root + 10) % 12 in ci.core and (ci.root + 4) % 12 in ci.core
                              else set())                     # (a dominant substitute: its #11 too, lydian b7)
        colour = [c for c in near if c % 12 in tens and c % 12 not in oc.core]
        fresh = [c for c in near if c % 12 in ci.core | ci.tensions and c % 12 not in oc.core | oc.tensions]
        # (the first that keeps the melody rules)
        for c in sorted(colour, key=lambda c: (c % 12 in oc.tensions, abs(c - p))) + \
                sorted(fresh, key=lambda c: abs(c - p)):
            trial = notes[:k] + [(s, d, c)] + notes[k + 1:]
            if not melody_issues(trial, new, lo - 2, hi + 2, meter=meter, final_pcs=final_pcs):
                notes = trial
                break
    return None if melody_issues(notes, new, lo - 2, hi + 2, meter=meter, final_pcs=final_pcs) else notes


def _lift(notes, harm: Harm, top: int, meter: int, lo: int):
    """A shout chorus's melody: one of the part's highest notes in its second half (or anywhere; a quarter+ first)
    raised to the nearest chord tone / tension over `top` (the head's highest note), approached and released
    (_approach). None when no choice keeps the melody rules."""
    if not notes:
        return None
    end = max(s + d for s, d, _ in notes)
    late = [k for k, n in enumerate(notes) if n[0] >= 0.4 * end] or list(range(len(notes)))
    for j in sorted(late, key=lambda k: (notes[k][1] < 1.0, -notes[k][2], -notes[k][1]))[:4]:
        s, d, p = notes[j]
        ci = harm.under(s, d)
        for c in [c for c in range(top + 1, top + 6) if c % 12 in ci.core | ci.tensions]:
            out = list(notes)
            out[j] = (s, d, c)
            _approach(out, j, harm)
            single = all(n[2] < c for k, n in enumerate(out) if k != j)
            if single and not melody_issues(out, harm, lo - 2, c + 2, meter=meter):
                return out
    return None


_ROOT = re.compile(r'^([A-G][b#]?)(.*)$')


def _cadences(items) -> list:
    """Indices of the dominants resolving down a fifth (the next chord, the part looping)."""
    out = []
    for i, (sym, _) in enumerate(items):
        c, nxt = chord(sym), chord(items[(i + 1) % len(items)][0])
        if chord_kind(c) == 'dom' and (nxt.root - c.root) % 12 == 5:
            out.append(i)
    return out


def variant(changes, kind: str, t_pc: int, sharps: bool, bar: float, at: int | None = None):
    """A cadence of a part played another way (genres.CHART_VARIANTS) - the dominant at index `at` (default the part's
    last one resolving down a fifth) and the ii before it:
      tritone   the V -> its tritone substitute (bII7 / 9 / 13)
      backdoor  the ii-V -> IVm7 bVII9 (into a major chord; a V alone -> bVII9)
      pedal     the ii -> V9sus4 over the dominant's root (a dominant pedal); a V alone of a bar+ -> V9sus4 + V
      plagal    the ii-V -> IVmaj7 IVm6 (into a major chord; into a minor one IVm7 IVm6): the minor-plagal cadence
      iiV       a dominant of a bar+ (4/4) / two bars (3/4) split into its ii-V
    The changes (a new list) or None when the cadence cannot take it."""
    items = list(changes)
    doms = _cadences(items)
    i = (doms[-1] if doms else None) if at is None else at
    if i is None or i not in doms:
        return None
    sym, beats = items[i]
    root = chord(sym).root % 12
    target = chord(items[(i + 1) % len(items)][0])
    to_major = not target.is_minor
    pre = chord(items[i - 1][0]) if i else None
    ii = i - 1 if pre is not None and chord_kind(pre) in ('m7', 'min', 'm7b5') and (pre.root - root) % 12 == 7 \
        else None
    q = _ROOT.match(sym).group(2)
    t_ = target.root % 12

    def name(r_, qual):
        return spell(r_, sharps, (r_ - t_pc) % 12) + qual
    if kind == 'tritone':
        nq = q if q in ('7', '9', '13') else '7' if any(x in q for x in ('alt', 'b9', '#9', 'b13', '#5')) else '9'
        items[i] = (name(root + 6, nq), beats)
    elif kind == 'backdoor':
        if not to_major:
            return None
        items[i] = (name(t_ + 10, '9'), beats)
        if ii is not None:
            items[ii] = (name(t_ + 5, 'm7'), items[ii][1])
    elif kind == 'pedal':
        if ii is not None:
            items[ii] = (name(root, '9sus4'), items[ii][1])
        elif beats >= bar - 1e-6:
            items[i:i + 1] = [(name(root, '9sus4'), beats / 2), (sym, beats / 2)]
        else:
            return None
    elif kind == 'plagal':
        if ii is None:
            return None
        items[ii] = (name(t_ + 5, 'maj7' if to_major else 'm7'), items[ii][1])
        items[i] = (name(t_ + 5, 'm6'), beats)
    elif kind == 'iiV':
        if not (beats >= 2 * bar - 1e-6 or (beats >= bar - 1e-6 and bar >= 4)):
            return None
        items[i:i + 1] = [(name(root + 7, 'm7'), beats / 2), (sym, beats / 2)]
    else:
        raise ComposeError(f"chart variant {kind!r}: one of tritone, backdoor, pedal, plagal, iiV")
    return items


def reharm(changes, t_pc: int, sharps: bool, bar: float, rng: random.Random):
    """A part's reharm (the last solo chorus and the head out play it - perform's 'v' parts): ONE cadence played
    another way (variant(): the kind drawn from CHART_VARIANTS) at a dominant resolving down a fifth anywhere in the
    part (drawn: the cadence is not a fixed slot). None when nothing applies."""
    items = list(changes)
    doms = _cadences(items)
    if not doms:
        return None
    i = rng.choice(doms)
    kinds = dict(CHART_VARIANTS)
    while kinds:
        k = _pick(rng, kinds)
        out = variant(items, k, t_pc, sharps, bar, at=i)
        if out:
            return out
        kinds.pop(k)
    return None


# ------------------------------------------------------------------------------------------------ measuring the shape

def _corr(xs, ys) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    if sx < 1e-9 or sy < 1e-9:
        return None
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy), 3)


def top_line(notes, tol: float = 0.06) -> list:
    """The top voice of (start, dur, pitch[, vel]) notes: per onset (within tol beats) the highest note."""
    out, t0 = [], None
    for n in sorted(notes, key=lambda n: (n[0], -n[2])):
        if out and n[0] - t0 < tol:                       # the same onset (a rolled / anticipated chord)
            if n[2] > out[-1][2]:
                out[-1] = tuple(n)
            continue
        out.append(tuple(n))
        t0 = n[0]
    return out


def _sign(x) -> int:
    return (x > 0) - (x < 0)


def hook_matches(line, hook, scales=(1.0, 2.0), share: float = 1.0, contour: float = 0.75, tol: float = 0.1) -> list:
    """Where the hook's shape recurs in a line of (start, dur, pitch, ...) notes (sorted; a played line: top_line):
    from an onset, at least `share` of the hook's notes found at its onsets x a scale (2 = augmented; within tol
    beats x the scale: ornaments and rolled chords in between are fine) and the found notes' contour (up / down /
    same) agreeing with the hook's for at least `contour` of their steps - at any transposition. Returns
    [(start, scale)], non-overlapping."""
    k = len(hook)
    if k < 3:
        return []
    h0 = hook[0][0]
    sg = [_sign(hook[j + 1][2] - hook[j][2]) for j in range(k - 1)]
    out, busy = [], -1e9
    for i, a in enumerate(line):
        if a[0] < busy:
            continue
        for f in scales:
            got = []
            for h in hook:
                t, best = a[0] + f * (h[0] - h0), None
                for n in line[i:]:
                    if n[0] > t + tol * f:
                        break
                    if abs(n[0] - t) <= tol * f and (best is None or abs(n[0] - t) < abs(best[0] - t)):
                        best = n
                got.append(best)
            if got[0] is not a or sum(g is not None for g in got) < share * k - 1e-9:
                continue
            found = [g for g in got if g is not None]
            steps = [j for j in range(k - 1) if got[j] is not None and got[j + 1] is not None]
            if len(steps) < 2 or sum(_sign(got[j + 1][2] - got[j][2]) == sg[j] for j in steps) < contour * len(steps):
                continue
            out.append((a[0], f))
            busy = found[-1][0] + 1e-6
            break
    return out


def plan_levels(tune, genre: Genre | None = None) -> dict:
    """The arc level of every two-bar phrase of the head (the tune's own; the form curve's for a tune without one)."""
    if getattr(tune, 'levels', None):
        return tune.levels
    from .genres import get
    g = genre or get(tune.genre)
    plans = {p: phrase_plans(g, tune.meter)['blues' if tune.form == 'blues' else p[0]]
             for p in tune.parts}
    return {p: [arc_at(g.arc['forms'][tune.form], (i + (u + 0.5) / len(plans[p])) / len(tune.parts))
                for u in range(len(plans[p]))] for i, p in enumerate(tune.parts)}


def shape(tune, song=None, genre: Genre | None = None) -> dict:
    """Measure the long-range shape of a tune (and of its performance, when `song` = endless.song(tune)):
      climax   the head's highest note: pitch, part, beat, x (its place 0..1 in the head), single (no other note as
               high), planned (it sits in the plan's climax phrase)
      hook     the hook's shape (hook_matches) in the head, its head (3 notes) in the tag (in time or augmented) and -
               with a song - the hook in the solo
      arc      per two-bar phrase the planned level against the melody's mean pitch / notes: their correlations
               (pitch_r, density_r) and the per-part means
      played   (with a song) per head part the piano's top-line pitch, onsets per bar, velocity (of its notes of an
               8th and longer: the sung line) and their
               correlation with the part levels; the solo in thirds (onsets per bar, pitch, velocity: the build)
      issues   what breaks the plan (the gate's arc check)"""
    m, ub = tune.meter, 2 * tune.meter
    levels = plan_levels(tune, genre)
    allnotes = [(p, k, n) for k, p in enumerate(tune.parts) for n in tune.melody[p]]
    top = max(n[2] for _, _, n in allnotes)
    tops = [(p, k, n) for p, k, n in allnotes if n[2] == top]
    p0, k0, n0 = tops[0]
    total = sum(tune.part_beats(p) for p in tune.parts)
    x = (sum(tune.part_beats(q) for q in tune.parts[:k0]) + n0[0]) / total
    cl = tune.climax or {}
    climax = {'pitch': note_name(top), 'part': p0, 'beat': n0[0], 'x': round(x, 3), 'single': len(tops) == 1,
              'planned': bool(cl) and p0 == cl.get('part') and int(n0[0] // ub) == cl.get('unit')}
    hook = tune.motif
    head_hits = sum(len(hook_matches(tune.melody[p], hook, scales=(1.0,))) for p in tune.parts)
    # the tag develops the hook's head (its first notes, in time or augmented: composer.frame)
    tag_hits = len(hook_matches(tune.tag.get('melody', []), sorted(hook)[:3], scales=(1.0, 2.0)))
    lv, pitch, dens, per_part, pl, pp = [], [], [], {}, [], []
    for p in tune.parts:
        for u, level in enumerate(levels[p]):
            ns = [n for n in tune.melody[p] if u * ub <= n[0] < (u + 1) * ub]
            if ns:
                lv.append(level)
                pitch.append(sum(n[2] for n in ns) / len(ns))
                dens.append(len(ns))
        ns = tune.melody[p]
        per_part[p] = {'level': round(sum(levels[p]) / len(levels[p]), 2),
                       'pitch': round(sum(n[2] for n in ns) / max(1, len(ns)), 1),
                       'notes_per_bar': round(len(ns) / (tune.part_beats(p) / m), 2)}
        pl.append(per_part[p]['level'])
        pp.append(per_part[p]['pitch'])
    # the parts' mean register follows the arc: the tensest part sits highest, the register rises with the level
    r_parts = _corr(pl, pp)
    follows = pp[pl.index(max(pl))] == max(pp) and (r_parts is None or r_parts > 0)
    from .genres import get as _get
    g_ = genre or (_get(tune.genre) if getattr(tune, 'genre', None) else None)
    if not follows and cl and g_ is not None and g_.melody.get('climax_parts') and cl.get('part') in tune.parts:
        # (a drawn climax part - melody['climax_parts']: the part holding the climax may sit highest instead, the
        # register still rising with the level over the others)
        k_ = tune.parts.index(cl['part'])
        rest = [(a, b) for i, (a, b) in enumerate(zip(pl, pp)) if i != k_]
        r_rest = _corr([a for a, _ in rest], [b for _, b in rest])
        follows = pp[k_] == max(pp) and (r_rest is None or r_rest > 0) and \
            pp[pl.index(max(pl))] == max(b for _, b in rest)
    out = {'climax': climax, 'hook': {'notes': len(hook), 'head': head_hits, 'tag': tag_hits},
           'arc': {'part_pitch_r': r_parts, 'follows': follows, 'phrase_pitch_r': _corr(lv, pitch),
                   'phrase_density_r': _corr(lv, dens), 'parts': per_part}}
    issues = []
    if cl:
        if not climax['single']:
            issues.append(f"the top note {climax['pitch']} occurs {len(tops)} times")
        if not climax['planned']:
            issues.append(f"the top note sits in {p0} beat {n0[0]:g}, not the planned climax ({cl.get('part')} "
                          f"phrase {cl.get('unit')})")
        n_a = sum(1 for p in tune.parts if p[0] == 'A')
        if head_hits < n_a:
            issues.append(f"the hook recurs {head_hits}x in the head (want {n_a}: every A)")
        if not follows:
            issues.append("the parts' mean register does not follow the arc (the tensest part highest, rising with "
                          "the level)")
    if song is not None:
        notes = [(n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes]
        head = song['head']
        played, pl, pv, pp, pd = {}, [], [], [], []
        for part in head.parts:
            line = top_line([n for n in notes if part.start <= n[0] < part.end])
            if not line:
                continue
            bars = (part.end - part.start) / m
            sung = [n for n in line if n[1] >= 0.45] or line
            d = {'level': round(sum(levels.get(part.name, [0.5])) / len(levels.get(part.name, [0.5])), 2),
                 'pitch': round(sum(n[2] for n in line) / len(line), 1),
                 'onsets_per_bar': round(len(line) / bars, 2),
                 # the sung line's level: the top notes of an 8th and longer (not the grace notes / fills)
                 'vel': round(sum(n[3] for n in sung) / len(sung), 1)}
            played[part.name] = d
            pl.append(d['level'])
            pv.append(d['vel'])
            pp.append(d['pitch'])
            pd.append(d['onsets_per_bar'])
        solo = song['solo']
        third = (solo.end - solo.start) / 3
        thirds = []
        for k in range(3):
            a, b = solo.start + k * third, solo.start + (k + 1) * third
            line = top_line([n for n in notes if a <= n[0] < b])
            thirds.append({'onsets_per_bar': round(len(line) / (third / m), 2),
                           'pitch': round(sum(n[2] for n in line) / max(1, len(line)), 1),
                           'vel': round(sum(n[3] for n in line) / max(1, len(line)), 1)})
        solo_line = top_line([n for n in notes if solo.start <= n[0] < solo.end])
        quotes = hook_matches(solo_line, hook, scales=(1.0,), share=0.8, tol=0.25)
        out['hook']['solo'] = len(quotes)
        out['hook']['solo_first'] = round((quotes[0][0] - solo.start) / m, 1) if quotes else None
        out['played'] = {'parts': played, 'vel_r': _corr(pl, pv), 'pitch_r': _corr(pl, pp),
                         'density_r': _corr(pl, pd), 'solo': thirds}
    out['issues'] = issues
    return out


def _clusters(notes, tol: float = 0.1) -> list:
    """(start, dur, pitch, vel) notes -> [(start, top note, size)] per onset (notes within tol beats of the first:
    a rolled chord is one attack)."""
    out = []
    for n in sorted(notes, key=lambda n: (n[0], -n[2])):
        if out and n[0] - out[-1][0] < tol:
            top = out[-1][1]
            out[-1] = (out[-1][0], n if n[2] > top[2] else top, out[-1][2] + 1)
        else:
            out.append((n[0], n, 1))
    return out


class NoteView(namedtuple('_NoteView', 'song melody accompaniment sections secs m rh lh cl lcl energies')):
    """Immutable note snapshot with explicit hands, cached onset groups and energies.

    Retain track/note summation order; window origins belong to the metrics. Section
    references and source-song metadata are read only during measurement.
    """
    __slots__ = ()

    def __new__(cls, song, melody='piano', accompaniment=('comp',)):
        from types import MappingProxyType
        accompaniment = tuple(accompaniment)
        rh = tuple((n.start, n.dur, n.pitch, n.vel) for n in song.tracks[melody]._notes)
        lh = tuple((n.start, n.dur, n.pitch, n.vel) for name in accompaniment if name in song.tracks
                   for n in song.tracks[name]._notes)
        sections = tuple(song.sections)
        return super().__new__(cls, song, melody, accompaniment, sections,
                               MappingProxyType({x.name: x for x in sections}), float(song.beats_per_bar),
                               rh, lh, tuple(_clusters(rh)), tuple(_clusters(lh)),
                               tuple((n[0], (n[3] / 127.0) ** 2.5) for n in rh + lh))

    @staticmethod
    def of(song):
        return song if isinstance(song, NoteView) else NoteView(song)

    def db(self, spans):
        """Note energy per bar over a union of spans (overlaps count each note once)."""
        import math
        e = sum(e for t, e in self.energies if any(a - 1e-6 <= t < b - 1e-6 for a, b in spans))
        return 10 * math.log10(max(e, 1e-4) / max(1e-9, sum(b - a for a, b in spans) / self.m))

    def onsets(self, a, b, notes=None):
        return [c for c in (self.cl if notes is None else notes) if a - 1e-6 <= c[0] < b - 1e-6]

    def dynamics(self, origin, end):
        """2-bar energy spread and loudest 4-bar centre, normalized to this origin."""
        m, span = self.m, max(1e-9, end - origin)
        w2 = sorted(self.db([(a, a + 2 * m)]) for a in
                    (origin + k * 2 * m for k in range(int(span // (2 * m)))))
        spread = w2[min(len(w2) - 1, int(0.95 * len(w2)))] - w2[int(0.1 * len(w2))] if w2 else 0.0
        w4 = [(self.db([(a, a + 4 * m)]), a) for a in
              (origin + k * m for k in range(max(1, int(span // m) - 3)))]
        return round(spread, 1), round((max(w4)[1] + 2 * m - origin) / span, 2) if w4 else None


def tells(song, tune=None) -> dict:
    """The blind test's tells (songs/_blind/ROUNDS.md) measured on a performance: a Song with a 'piano' (right hand)
    and optionally a 'comp' (left hand) track and 'head' / 'solo' sections (endless.song(tune), or a composed piece).
    Measured on the right hand's onsets (a rolled chord is one attack; its top note the line), before the groove:
      silent_bars      solo bars without a right-hand attack; both_silent: without an attack of either hand
      starts_on_one    share of the solo's phrase starts (after a beat's rest) on a downbeat
      wraps            octave wraps inside the solo's fast lines (top notes <= half a beat apart): a leap of a 9th+,
                       or out by a 7th+ and straight back
      repeats          solo bars (3+ onsets) repeating one of the last 8 bars verbatim (positions, pitches, lengths);
                       over_chord: of them over another chord
      density          the solo's onsets per bar / the head's (overall; peak: its densest third); vel: the solo's mean
                       top velocity - the head's; peak: where the solo's strongest 2-bar window sits (0..1)
      figures          fast figures (4+ onsets 0.26 beat apart or less) in the head and the solo; figure_repeats: those
                       whose shape (bar position, notes, rate) repeats one of the 8 bars before
      harmonized_fast  share of the solo's notes inside fast lines (an 8th or less to both neighbours) struck with more
                       right-hand notes
      quotes           literal quotes of the hook (its rhythm and intervals) in the solo (with tune=)
    Round 2 (the composer's tells):
      head_5gram       share of the head's 5-attack shapes (4 intervals + 4 onset gaps in 12ths of a beat) that recur
                       elsewhere in the head: a theme restated (composed 0.08-0.38, a re-rolled head ~0)
      solo_entropy     Shannon entropy (bits) of the solo's top-line durations in 12ths of a beat (composed ~1.7-2.2)
      dyn_range        a loudness range from the notes (dB of sum vel^2.5 per 2-bar window, its 10-95 % spread, the
                       ending left out; the rendered LRA is the real one); peak_x / top_x: where the loudest 4-bar
                       window / the highest right-hand note sits (0..1 of the piece's beats)
      lh_silent        head / solo / head-out bars without a left-hand attack (a waltz LH resting every second bar)
      reharms          solo parts whose changes are not the head's same part; isolated: of them those the head out
                       does not play the same way (a one-off substitution)
      intro_copy / tag_copy  (with tune=) 1 when the intro / tag is a copy of a head part's bars (its changes and
                       half of its melody note for note); cell_max: the most common bar rhythm's share of the head's
                       bars;
                       quarter_runs: runs of 4+ on-beat quarter notes in the head melody"""
    view = NoteView.of(song)
    m, rh, lh = view.m, view.rh, view.lh
    head, solo = view.secs['head'], view.secs['solo']
    cl = view.cl

    within = view.onsets

    def sounding(notes, a, b):                       # an attack in the bar (what a reader of the notation sees)
        return any(a - 1e-6 <= n[0] < b - 1e-6 for n in notes)
    nb = int(round((solo.end - solo.start) / m))
    bars = [(solo.start + k * m, solo.start + (k + 1) * m) for k in range(nb)]
    silent = sum(1 for a, b in bars if not sounding(rh, a, b))
    both = sum(1 for a, b in bars if not sounding(rh, a, b) and not sounding(lh, a, b))
    sc = within(solo.start, solo.end)
    # phrase starts: an onset after a beat or more of nothing sounding
    starts, end = [], -1e9
    for t, top, _ in sc:
        if t - end >= 1.0 - 1e-6:
            starts.append(t)
        end = max(end, max(n[0] + n[1] for n in rh if abs(n[0] - t) < 0.1))
    on_one = sum(1 for t in starts if abs((t - solo.start) / m - round((t - solo.start) / m)) * m < 0.08)
    # wraps in fast lines
    wraps = 0
    k = 1
    while k < len(sc):
        (t0, a, _), (t1, b_, _) = sc[k - 1], sc[k]
        if t1 - t0 <= 0.5 + 1e-6 and a[1] <= 0.6:
            d = b_[2] - a[2]
            if abs(d) >= 13:
                wraps += 1
            elif abs(d) >= 10 and k + 1 < len(sc) and sc[k + 1][0] - t1 <= 0.5 + 1e-6:
                d2 = sc[k + 1][1][2] - b_[2]
                if abs(d2) >= 10 and (d > 0) != (d2 > 0):
                    wraps += 1
                    k += 1
        k += 1

    def sig(a, b):
        return tuple((round((t - a) * 12), top[2], round(top[1] * 4)) for t, top, _ in within(a, b))

    def chord_at(t):
        c = solo.prog.at(min(max(t - solo.start, 0.0), solo.prog.length - 1e-6)) if solo.prog else None
        return None if c is None else (c.root % 12, tuple(c.intervals))
    sigs = [sig(a, b) for a, b in bars]
    reps = over = 0
    for j, s_ in enumerate(sigs):
        if len(s_) < 3:
            continue
        same = [i for i in range(max(0, j - 8), j) if sigs[i] == s_]
        if same:
            reps += 1
            over += any(chord_at(bars[i][0]) != chord_at(bars[j][0]) for i in same)
    hc = within(head.start, head.end)
    h_bars = (head.end - head.start) / m

    def mean_vel(cs):
        vs = [top[3] for _, top, _ in cs if top[1] >= 0.12]
        return sum(vs) / len(vs) if vs else 0.0
    third = (solo.end - solo.start) / 3
    dens_third = [len(within(solo.start + i * third, solo.start + (i + 1) * third)) / (third / m) for i in range(3)]
    h_dens = len(hc) / h_bars
    win = [(sum(top[3] for _, top, _ in within(a, a + 2 * m)), i) for i, (a, _) in enumerate(bars[:-1])]
    peak = (max(win)[1] + 1) / max(1, nb) if win else None
    # fast figures in the head and the solo
    figs = []
    for sec in (head, solo):
        cs = within(sec.start, sec.end)
        i = 0
        while i < len(cs):
            j = i
            while j + 1 < len(cs) and cs[j + 1][0] - cs[j][0] <= 0.26 + 1e-6:
                j += 1
            if j - i + 1 >= 4:
                t = cs[i][0]
                rate = (cs[j][0] - t) / (j - i)
                figs.append((t, (round(((t - sec.start) % m) * 12), j - i + 1, round(rate * 24))))
            i = j + 1
    fig_rep = sum(1 for k_, (t, s_) in enumerate(figs) if any(s2 == s_ and t - t2 <= 8 * m for t2, s2 in figs[:k_]))
    fast = harm = 0
    for i in range(1, len(sc) - 1):
        if sc[i][0] - sc[i - 1][0] <= 0.5 + 1e-6 and sc[i + 1][0] - sc[i][0] <= 0.5 + 1e-6 and sc[i][1][1] <= 0.6:
            fast += 1
            harm += sc[i][2] > 1
    out = {'silent_bars': silent, 'both_silent': both, 'solo_bars': nb,
           'starts_on_one': round(on_one / max(1, len(starts)), 2), 'wraps': wraps, 'repeats': reps,
           'over_chord': over, 'density': round((len(sc) / nb) / max(1e-9, h_dens), 2),
           'density_peak': round(max(dens_third) / max(1e-9, h_dens), 2),
           'vel': round(mean_vel(sc) - mean_vel(hc), 1), 'peak': round(peak, 2) if peak is not None else None,
           'figures': len(figs), 'figure_repeats': fig_rep,
           'harmonized_fast': round(harm / fast, 2) if fast else 0.0}
    if tune is not None and len(tune.motif) >= 3:
        hk = sorted(tune.motif)
        line = [(t, top[2]) for t, top, _ in sc]
        q = 0
        for i, (t, p) in enumerate(line):
            ok = True
            for s0, _, p0 in hk[1:]:
                tt = t + s0 - hk[0][0]
                hit = [pp for u, pp in line[i:i + 12] if abs(u - tt) < 0.1]
                if not hit or hit[0] - p != p0 - hk[0][2]:
                    ok = False
                    break
            q += ok
        out['quotes'] = q
    out.update(_tells_r2(view, tune))
    out.update(_tells_r3(view, tune))
    out.update(_tells_r4(view, tune))
    out.update(_tells_r5(view, tune))
    out.update(_tells_r6(view, tune))
    out.update(_tells_r7(view, tune))
    return out


def _entropy(xs) -> float:
    import math
    n = len(xs)
    if not n:
        return 0.0
    cnt: dict = {}
    for x in xs:
        cnt[x] = cnt.get(x, 0) + 1
    return -sum(c / n * math.log2(c / n) for c in cnt.values())


def _bar_rhythms(notes, meter: float, beats: float) -> list:
    """Per bar the onset positions (8ths) of written melody notes."""
    out = []
    for b in range(int(round(beats / meter))):
        a, z = b * meter - 1e-6, (b + 1) * meter - 1e-6
        out.append(tuple(round((s - b * meter) * 2) for s, _, _ in notes if a <= s < z))
    return out


def _copy_of(notes, changes, tune) -> int:
    """1 when (changes, notes) of an intro / tag are a head part's bars: the same changes as some bar-aligned stretch
    of a part and half of its notes found there note for note (shifted by whole bars)."""
    if not notes and not changes:
        return 0
    m = tune.meter
    L = _beats(changes)
    for p in tune.parts:
        ch, mel = tune.changes[p], tune.melody[p]
        total = _beats(ch)
        for off in range(0, int(round(total - L)) + 1, m):
            seg = _slice_changes(ch, off, off + L)
            if [(s, round(b, 3)) for s, b in seg] != [(s, round(b, 3)) for s, b in changes]:
                continue
            win = {(round(s - off, 3), round(d, 3), n) for s, d, n in mel if off - 1e-6 <= s < off + L - 1e-6}
            if not notes or sum((round(s, 3), round(d, 3), n) in win for s, d, n in notes) >= 0.5 * len(notes):
                return 1
    return 0


def _slice_changes(changes, a: float, b: float) -> list:
    out, t = [], 0.0
    for s, d in changes:
        lo, hi = max(t, a), min(t + d, b)
        if hi - lo > 1e-6:
            out.append((s, hi - lo))
        t += d
    return out


def _tells_r2(view, tune) -> dict:
    """The round-2 measures of tells() (see its docstring)."""
    m, rh, lh, cl = view.m, view.rh, view.lh, view.cl
    head, solo = view.secs['head'], view.secs['solo']
    out_sec = view.secs.get('out')
    end0 = view.secs['end'].start if 'end' in view.secs else max(n[0] + n[1] for n in rh)
    piece0 = view.sections[0].start
    span = max(1e-9, end0 - piece0)
    # the head's 5-attack shapes
    line = [(t, top[2]) for t, top, _ in cl if head.start - 1e-6 <= t < head.end - 1e-6]
    shapes = [tuple(line[i + k + 1][1] - line[i + k][1] for k in range(4)) +
              tuple(round((line[i + k + 1][0] - line[i + k][0]) * 12) for k in range(4)) for i in range(len(line) - 4)]
    cnt: dict = {}
    for s_ in shapes:
        cnt[s_] = cnt.get(s_, 0) + 1
    rec = sum(1 for s_ in shapes if cnt[s_] > 1) / len(shapes) if shapes else 0.0
    # the solo's durations
    durs = [max(1, round(top[1] * 12)) for t, top, _ in cl if solo.start - 1e-6 <= t < solo.end - 1e-6]
    # loudness from the notes: 2-bar windows (range) and 4-bar windows (the peak)
    rng_, peak_x = view.dynamics(piece0, end0)
    top = max((n for n in rh if n[0] < end0), key=lambda n: (n[2], -n[0]), default=None)
    # the left hand's silent bars
    lh_sil = 0
    for sec in (head, solo, out_sec):
        if sec is None:
            continue
        for k in range(int(round(sec.length / m))):
            a = sec.start + k * m
            if not any(a - 1e-6 <= n[0] < a + m - 1e-6 for n in lh):
                lh_sil += 1
    # reharms in the solo vs the head's chart, and whether the head out plays them too

    def items(p):
        return [(None if c is None else (c.root % 12, tuple(c.intervals)), round(d, 3)) for c, d in p.prog.items]
    base = {p.name: items(p) for p in head.parts}
    outs = [items(p) for p in out_sec.parts] if out_sec is not None else []
    reh = iso = 0
    for p in solo.parts:
        nm = p.name.rstrip('v')
        if nm in base and items(p) != base[nm]:
            reh += 1
            iso += items(p) not in outs
    res = {'head_5gram': round(rec, 2), 'solo_entropy': round(_entropy(durs), 2), 'dyn_range': round(rng_, 1),
           'peak_x': round(peak_x, 2) if peak_x is not None else None,
           'top_x': round((top[0] - piece0) / span, 2) if top else None, 'lh_silent': lh_sil,
           'reharms': reh, 'isolated': iso}
    if tune is not None:
        res['intro_copy'] = _copy_of(tune.intro.get('melody', []), tune.intro.get('changes', []), tune)
        res['tag_copy'] = _copy_of(tune.tag.get('melody', []), tune.tag.get('changes', []), tune)
        bars = [r for p in tune.parts for r in _bar_rhythms(tune.melody[p], tune.meter, tune.part_beats(p)) if r]
        cnt = {}
        for r in bars:
            cnt[r] = cnt.get(r, 0) + 1
        res['cell_max'] = round(max(cnt.values()) / len(bars), 2) if bars else 0.0
        runs = 0
        for p in tune.parts:
            k = 0
            mel = sorted(tune.melody[p])
            for i, (s, d, _) in enumerate(mel):
                on_beat = abs(s - round(s)) < 1e-6 and abs(d - 1.0) < 1e-6
                nxt_ok = i == 0 or abs(mel[i - 1][0] + mel[i - 1][1] - s) < 1e-6
                k = k + 1 if on_beat and (k == 0 or nxt_ok) else (1 if on_beat else 0)
                if k == 4:
                    runs += 1
        res['quarter_runs'] = runs
    return res


def _lines(cl, a: float, b: float) -> list:
    """Runs of 4+ right-hand attacks (cluster tops) in [a, b) 0.2 .. 0.55 beat apart: the 8th / triplet / 16th lines
    (the faster ornament figures - trills, turns, grace notes, glissandi - are not lines)."""
    cs = [c for c in cl if a - 1e-6 <= c[0] < b - 1e-6]
    out, cur = [], cs[:1]
    for p_, c in zip(cs, cs[1:]):
        if 0.2 - 1e-6 <= c[0] - p_[0] <= 0.55 + 1e-6 and p_[1][1] <= 0.6:
            cur.append(c)
        else:
            out.append(cur)
            cur = [c]
    out.append(cur)
    return [r for r in out if len(r) >= 4]


def _tells_r3(view, tune) -> dict:
    """The round-3 measures of tells() (the shared players' tells):
      vel_onoff     in the 8th / 16th lines (_lines) the mean velocity of the on-beat tops - the off-beat ones
                    (composed ~1, round 3 +7..+14); vel_zigzag: share of turns among neighbouring velocity steps (a
                    line alternating loud / soft: 1; random: ~0.67; composed ~0.45-0.55); vel_jumps: share of
                    neighbour steps over 15
      rep_notes     share of the lines' neighbouring attacks on the same top pitch (composed 0-1 %)
      rev_cells     4-note scale cells reversing at once (4 steps one way, 4 the other) in the solo per 32 bars;
                    arp_bars: share of solo bars that are one arpeggio sweep (4+ tops, every step a 3rd / 4th, one
                    direction); guide_land: share of the solo's chord changes struck on a 3rd / 7th of the new chord
      clashes       {rule: count} of theory.clash() over the head / solo / head out's top notes on beat 1 / 3 (a waltz:
                    1) or longer than half a beat (an anticipation: against the chord it anticipates); held: notes
                    still sounding a quarter beat into a chord they clash with; clash_total
      empty_64      solo bars without a right-hand attack per 64 solo bars
      solo_db / out_db  the solo's / the head out's note energy (dB per bar) - the head's
      orn           trills / tremolos (4+ attacks 0.2 beat apart or closer on two tops) and runs / sweeps (6+ attacks 0.26
                    apart, 5+ pitches, one direction) in the piece; orn_chorus: the most in one chorus (head / solo
                    chorus / out);
                    orn_loud: of them in bars at 100+ mean top velocity; orn_intro_end: in the intro's last bar
      lh_per_bar    left-hand attacks per bar (head / solo / out); lh_rootless: share of its 2+ note attacks without
                    the chord's root; lh_antic: share of its attacks on the & of 2 / 4 (a waltz: the & of 2 / 3)
      with tune=:   intro_kind (the vamp), intro_line (how its melody was made), cell_run (the longest run of one
                    bar rhythm in the intro / tag melody), reharm_at (the reharm's part and chord index from its
                    end, or None), shout, dynamics (the drawn plan)"""
    m, rh, lh, cl = view.m, view.rh, view.lh, view.cl
    import math
    head, solo, out_sec = view.secs['head'], view.secs['solo'], view.secs.get('out')
    body = [x for x in (head, solo, out_sec) if x is not None]
    beats_in = 3 if abs(m - 3) < 1e-6 else 2 if abs(m - 4) < 1e-6 else 1      # strong beats: 1 and 3 (waltz: 1)
    changes = sorted({round(s_.start + t, 6) for s_ in view.sections if s_.prog is not None for t, _, _ in s_.prog})

    chord_at = _chord_fn(view)
    # ---- velocity in the lines
    on, off, steps, turns, jumps, rep, pairs, n_lines = [], [], 0, 0, 0, 0, 0, 0
    for sec in body:
        for r in _lines(cl, sec.start, sec.end):
            n_lines += 1
            vs = [c[1][3] for c in r]
            for c in r:
                (on if abs(c[0] - round(c[0])) < 0.05 else off).append(c[1][3])
            ds = [b_ - a_ for a_, b_ in zip(vs, vs[1:])]
            jumps += sum(abs(d) > 15 for d in ds)
            steps += len(ds)
            turns += sum(1 for d0, d1 in zip(ds, ds[1:]) if d0 * d1 < 0)
            rep += sum(1 for a_, b_ in zip(r, r[1:]) if a_[1][2] == b_[1][2])
            pairs += len(r) - 1
    res = {'vel_onoff': round(sum(on) / len(on) - sum(off) / len(off), 1) if on and off else 0.0,
           'vel_zigzag': round(turns / max(1, steps - n_lines), 2), 'vel_jumps': round(jumps / max(1, steps), 2),
           'rep_notes': round(rep / max(1, pairs), 3)}
    # ---- the solo's line shapes
    nb = int(round(solo.length / m))
    rev = 0
    for r in _lines(cl, solo.start, solo.end):
        ps = [c[1][2] for c in r]
        i = 0
        while i + 6 < len(ps):
            d1 = [ps[i + k + 1] - ps[i + k] for k in range(3)]
            d2 = [ps[i + k + 4] - ps[i + k + 3] for k in range(3)]
            if all(1 <= abs(d) <= 2 for d in d1 + d2) and len({_sign(d) for d in d1}) == 1 \
                    and len({_sign(d) for d in d2}) == 1 and _sign(d1[0]) != _sign(d2[0]):
                rev += 1
                i += 6
            else:
                i += 1
    arp = 0
    for k in range(nb):
        a = solo.start + k * m
        tops = [c[1][2] for c in cl if a - 1e-6 <= c[0] < a + m - 1e-6]
        ds = [b_ - a_ for a_, b_ in zip(tops, tops[1:])]
        if len(tops) >= 4 and all(3 <= abs(d) <= 5 for d in ds) and len({_sign(d) for d in ds}) == 1:
            arp += 1
    land = hit = 0
    for t in (x for x in changes if solo.start + 0.5 < x < solo.end - 1e-6):
        c = next((c for c in cl if abs(c[0] - t) < 0.06), None)
        ch = chord_at(t + 1e-3)
        if c is None or ch is None:
            continue
        land += 1
        g3, g7 = guide_tones(ch)
        hit += c[1][2] % 12 in {x for x in (g3, g7) if x is not None}
    res.update(rev_cells=round(rev * 32 / max(1, nb), 2), arp_bars=round(arp / max(1, nb), 3),
               guide_land=round(hit / max(1, land), 2))
    # ---- clashes on the strong beats / long notes, and notes held into a clashing chord
    cnt = {k: 0 for k in ('nat11', 'maj3_minor', 'maj7_dom', 'min3_major', 'held')}
    for sec in body:
        for t, n, _ in (c for c in cl if sec.start - 1e-6 <= c[0] < sec.end - 1e-6):
            pos = (t - sec.start) % m
            strong = n[1] > 0.15 and ((abs(pos - round(pos)) < 0.05 and int(round(pos)) % m % beats_in == 0)
                                      or n[1] > 0.5 + 1e-6)              # (a grace note is deliberate)
            # an anticipation (struck up to an 8th before a change and held over it) belongs to the next chord
            ant = next((x for x in changes if t < x <= t + 0.55 and t + n[1] > x + 0.1), None)
            ch = chord_at((ant if ant is not None else t) + 1e-3)
            if strong and ch is not None:
                why = clash(ch, n[2])
                if why:
                    cnt[why] += 1
            for ct in (x for x in changes if t + 0.25 < x < t + n[1] - 0.25 and x != ant):
                ch2 = chord_at(ct + 1e-3)
                if ch2 is not None and clash(ch2, n[2]):
                    cnt['held'] += 1
                    break
    res['clashes'] = cnt
    res['clash_total'] = sum(cnt.values())
    res['empty_64'] = round(sum(1 for k in range(nb) if not any(
        solo.start + k * m - 1e-6 <= n[0] < solo.start + (k + 1) * m - 1e-6 for n in rh)) * 64 / max(1, nb), 1)
    # ---- the dynamic plan from the notes
    head_db = view.db([(head.start, head.end)])
    res['solo_db'] = round(view.db([(solo.start, solo.end)]) - head_db, 1)
    res['out_db'] = round(view.db([(out_sec.start, out_sec.end)]) - head_db, 1) if out_sec is not None else None
    # ---- ornaments: two-key alternations and runs
    figs = []
    i = 0
    while i < len(cl):
        j = i
        while j + 1 < len(cl) and cl[j + 1][0] - cl[j][0] <= 0.26 + 1e-6:
            j += 1
        grp = cl[i:j + 1]
        tops_ = {c[1][2] for c in grp}
        fast2 = len(grp) >= 4 and len(tops_) <= 2 and all(b_[0] - a_[0] <= 0.2 + 1e-6 for a_, b_ in zip(grp, grp[1:]))
        ds = {_sign(b_[1][2] - a_[1][2]) for a_, b_ in zip(grp, grp[1:])}
        if fast2 or (len(grp) >= 6 and len(tops_) >= 5 and len(ds - {0}) == 1):      # a run / sweep: one way
            figs.append(grp[0][0])
        i = j + 1
    chor = [(head.start, head.end)]
    if tune is not None and tune.form == 'blues':
        chor += [(solo.start + k * 12 * m, min(solo.end, solo.start + (k + 1) * 12 * m)) for k in range(nb // 12)]
    else:
        chor.append((solo.start, solo.end))
    if out_sec is not None:
        chor.append((out_sec.start, out_sec.end))
    loud = 0
    for t in figs:
        b0 = math.floor(t / m) * m
        vs = [c[1][3] for c in cl if b0 - 1e-6 <= c[0] < b0 + m - 1e-6]
        loud += bool(vs) and sum(vs) / len(vs) >= 100
    intro = view.secs.get('intro')
    res.update(orn=len(figs), orn_chorus=max((sum(1 for t in figs if a <= t < b) for a, b in chor), default=0),
               orn_loud=loud, orn_intro_end=sum(1 for t in figs if intro is not None and
                                                intro.end - m - 1e-6 <= t < intro.end))
    # ---- the left hand
    in_body = [c for c in view.lcl if any(s_.start - 1e-6 <= c[0] < s_.end - 1e-6 for s_ in body)]
    bars_body = sum(s_.length for s_ in body) / m
    multi = [c for c in in_body if c[2] >= 2]
    rootless_ = 0
    for t, _, _ in multi:
        ch = chord_at(t + 0.06)
        if ch is not None and not any(n[2] % 12 == ch.root % 12 for n in lh if abs(n[0] - t) < 0.1):
            rootless_ += 1
    antic_pos = (1.5, 2.5) if beats_in == 3 else (1.5, 3.5)
    antic = sum(1 for c in in_body if any(abs((c[0] % m) - x) < 0.06 for x in antic_pos))
    res.update(lh_per_bar=round(len(in_body) / max(1, bars_body), 2),
               lh_rootless=round(rootless_ / max(1, len(multi)), 2), lh_antic=round(antic / max(1, len(in_body)), 2))
    if tune is not None:
        res['intro_kind'] = tune.intro.get('kind')
        res['intro_line'] = tune.intro.get('line', 'head')
        run_max = 0
        for fr in (tune.intro, tune.tag):
            rs = _bar_rhythms(fr.get('melody', []), tune.meter, _beats(fr.get('changes', [])))
            k = 0
            for a_, b_ in zip([None] + rs, rs):
                k = k + 1 if a_ == b_ and b_ else 1
                run_max = max(run_max, k)
        res['cell_run'] = run_max
        res['reharm_at'] = None
        for p, ch in (getattr(tune, 'solo_changes', None) or {}).items():
            diff = [i for i, (x, y) in enumerate(zip(ch, tune.changes[p])) if x != y]
            res['reharm_at'] = f"{p}:{diff[0] - len(ch)}" if diff else None
        res['shout'], res['dynamics'] = bool(getattr(tune, 'shout', False)), getattr(tune, 'dynamics', None)
    return res


def _beats(changes) -> float:
    return sum(b for _, b in changes)


def licks(cl, a: float, b: float) -> list:
    """The fast cells of a right hand's attacks (_clusters) in [a, b): windows of 5 attacks at most half a beat
    apart with at least one gap of a triplet 8th or less - [(start, signature)], the signature transposition-free
    (the 4 intervals of the top line + the 4 onset gaps in 12ths of a beat): what a listener hears as 'that lick
    again'."""
    cs = [c for c in cl if a - 1e-6 <= c[0] < b - 1e-6]
    out = []
    for i in range(len(cs) - 4):
        w = cs[i:i + 5]
        gaps = [y[0] - x[0] for x, y in zip(w, w[1:])]
        if max(gaps) > 0.5 + 1e-6 or min(gaps) > 0.34:
            continue
        out.append((w[0][0], tuple(y[1][2] - x[1][2] for x, y in zip(w, w[1:])) +
                    tuple(round(g * 12) for g in gaps)))
    return out


def _chord_fn(view):
    def chord_at(t):
        for s_ in view.sections:
            if s_.start - 1e-6 <= t < s_.end - 1e-6 and s_.prog is not None and s_.prog.length > 0:
                return s_.prog.at(min(t - s_.start, s_.prog.length - 1e-6))
        return None
    return chord_at


def _tells_r4(view, tune) -> dict:
    """The round-4 measures of tells():
      solo lines (_lines)  dir_run: mean length (notes) of the one-direction stretches, dir_run_max; ct_run5: stretches
                    of 5+ chord tones in one direction per 32 solo bars; onbeat_ct: share of the lines' on-beat tops
                    that are tones of the written chord (round 4: 0.93-0.99; composed ~0.80-0.88)
      dt_bars       solo bars with 6+ attacks a 16th apart (double time); dt_x: where the first sits (0..1 of the solo)
      peak_climb    1 when the solo's highest note is reached by 4+ rising attacks an 8th apart or closer (a sweep /
                    scale climb into the peak); block_run: the longest run of 4+ note attacks in the solo
      lick_rep      fast cells (licks) of the solo whose shape recurs later in the solo
      with tune=:   (the head as written, per 4-bar phrase - a waltz: 4 bars of 3/4)
      circle        mean share of a phrase's attacks on its most common pitch; circle_max
      ph_peak_sd / ph_mean_sd   spread (semitones) of the phrases' top notes / mean pitches (goals, registers)
      period_peak   where a part's highest note sits (0..1 of the part), mean over the parts
      bridge_reg / bridge_long / bridge_cells   the B's mean pitch - the A1's; its share of notes of 1.5 beats+ - the
                    A1's; the share of its bar rhythms the A1 has too (no B: None)
      cell8 / cell8_max the most common bar rhythm's uses per 8 bars (bars of 2+ notes), mean / max over the windows
      nct_ph        share of phrases with a tension on a strong beat (1 / 3, a waltz 1) or held a beat+, resolved by
                    step to a chord tone
      endings       {how a phrase's last long note lands: down / antic / mid, + '+pickup' when notes follow it}
      vary_bar      the first bar where the second chorus / A2 differs from the A1 (None: no second A)
      chart_vars    chart variants: the distinct changes a part label is played with over head / solo / head out,
                    minus one per label
      solo_shape, double, tag_approach, end_kind, feel_form (the drawn plan, when the tune has it)"""
    m, rh, lh, cl = view.m, view.rh, view.lh, view.cl
    head, solo, out_sec = view.secs['head'], view.secs['solo'], view.secs.get('out')
    chord_at = _chord_fn(view)
    nb = int(round(solo.length / m))
    res: dict = {}
    # ---- the solo's lines
    stretches, ct5, on_n, on_ct = [], 0, 0, 0
    for r in _lines(cl, solo.start, solo.end):
        ps = [c[1][2] for c in r]
        ds = [_sign(y - x) for x, y in zip(ps, ps[1:])]
        i = 0
        while i < len(ds):
            j = i
            while j + 1 < len(ds) and ds[j + 1] == ds[i] and ds[i] != 0:
                j += 1
            if ds[i] != 0:
                stretches.append(j - i + 2)
                run = best = 0
                for k in range(i, j + 2):
                    ch = chord_at(r[k][0] + 1e-3)
                    ok = ch is not None and r[k][1][2] % 12 in {(ch.root + x) % 12 for x in ch.intervals}
                    run = run + 1 if ok else 0
                    best = max(best, run)
                ct5 += best >= 5
            i = j + 1
        for c in r:
            if abs(c[0] - round(c[0])) < 0.05:
                ch = chord_at(c[0] + 1e-3)
                if ch is not None:
                    on_n += 1
                    on_ct += c[1][2] % 12 in {(ch.root + x) % 12 for x in ch.intervals}
    res.update(dir_run=round(sum(stretches) / len(stretches), 2) if stretches else 0.0,
               dir_run_max=max(stretches, default=0), ct_run5=round(ct5 * 32 / max(1, nb), 2),
               onbeat_ct=round(on_ct / max(1, on_n), 2))
    sc = [c for c in cl if solo.start - 1e-6 <= c[0] < solo.end - 1e-6]
    dt = []
    for k in range(nb):
        a = solo.start + k * m
        bar = [c for c in sc if a - 1e-6 <= c[0] < a + m - 1e-6]
        if sum(1 for x, y in zip(bar, bar[1:]) if y[0] - x[0] <= 0.26 + 1e-6) >= 5:
            dt.append(k)
    res['dt_bars'] = len(dt)
    res['dt_x'] = round(dt[0] / max(1, nb), 2) if dt else None
    climb = 0
    if sc:
        j = max(range(len(sc)), key=lambda i: (sc[i][1][2], -i))
        w = sc[max(0, j - 4):j + 1]
        climb = int(len(w) == 5 and all(y[1][2] > x[1][2] and y[0] - x[0] <= 0.5 + 1e-6 for x, y in zip(w, w[1:])))
    run = brun = 0
    for c in sc:
        run = run + 1 if c[2] >= 4 else 0
        brun = max(brun, run)
    seen, rep = {}, set()
    for t, sig in licks(cl, solo.start, solo.end):
        if sig in seen and t - seen[sig] >= 1.0:
            rep.add(sig)
        seen.setdefault(sig, t)
    res.update(peak_climb=climb, block_run=brun, lick_rep=len(rep))
    if tune is None:
        return res
    # ---- the head as written: 4-bar phrases
    P = 4 * tune.meter
    key_pcs = set(Key(tune.key).pcs)
    phr, peaks, means, circ, nct, ends = [], [], [], [], [], {}
    for p in tune.parts:
        mel = sorted(tune.melody[p])
        harm = Harm(tune.changes[p], key_pcs)
        for k in range(int(round(tune.part_beats(p) / P))):
            ns = [n for n in mel if k * P - 1e-6 <= n[0] < (k + 1) * P - 1e-6]
            if len(ns) < 3:
                continue
            phr.append(ns)
            peaks.append(max(n[2] for n in ns))
            means.append(sum(n[2] for n in ns) / len(ns))
            cnt: dict = {}
            for n in ns:
                cnt[n[2]] = cnt.get(n[2], 0) + 1
            circ.append(max(cnt.values()) / len(ns))
            hit = 0
            for i, (st, du, q) in enumerate(ns[:-1]):
                pos = st % tune.meter
                strong = du >= 1.0 - 1e-6 or abs(pos) < 1e-6 or (tune.meter == 4 and abs(pos - 2) < 1e-6)
                ci, cj = harm.under(st, du), harm.under(*ns[i + 1][:2])
                if strong and q % 12 not in ci.core and 0 < abs(ns[i + 1][2] - q) <= 2 and ns[i + 1][2] % 12 in cj.core:
                    hit = 1
            nct.append(hit)
            longs = [n for n in ns if n[1] >= 1.0 - 1e-6] or ns[-1:]
            st, du, _ = longs[-1]
            pos = st % tune.meter
            kind = 'down' if abs(pos) < 1e-6 else 'antic' if abs(pos - (tune.meter - 0.5)) < 1e-6 else 'mid'
            if any(n[0] > st + 1e-6 for n in ns):
                kind += '+pickup'
            ends[kind] = ends.get(kind, 0) + 1

    def sd(xs):
        mu = sum(xs) / len(xs)
        return round((sum((x - mu) ** 2 for x in xs) / len(xs)) ** 0.5, 2)
    pp = []
    for p in tune.parts:
        mel = tune.melody[p]
        if mel:
            top = max(mel, key=lambda n: (n[2], -n[0]))
            pp.append(top[0] / tune.part_beats(p))
    res.update(circle=round(sum(circ) / len(circ), 3) if circ else 0.0, circle_max=round(max(circ, default=0), 2),
               ph_peak_sd=sd(peaks) if peaks else 0.0, ph_mean_sd=sd(means) if means else 0.0,
               period_peak=round(sum(pp) / len(pp), 2) if pp else None,
               nct_ph=round(sum(nct) / len(nct), 2) if nct else 0.0, endings=ends)
    a1 = tune.parts[0]
    bars = {p: _bar_rhythms(tune.melody[p], tune.meter, tune.part_beats(p)) for p in tune.parts}
    if 'B' in tune.parts:
        A, Bm = tune.melody[a1], tune.melody['B']
        res['bridge_reg'] = round(sum(n[2] for n in Bm) / len(Bm) - sum(n[2] for n in A) / len(A), 1)
        res['bridge_long'] = round(sum(n[1] >= 1.5 for n in Bm) / len(Bm) - sum(n[1] >= 1.5 for n in A) / len(A), 2)
        own = [r for r in bars['B'] if len(r) >= 2]
        res['bridge_cells'] = round(sum(r in set(bars[a1]) for r in own) / max(1, len(own)), 2)
    else:
        res['bridge_reg'] = res['bridge_long'] = res['bridge_cells'] = None
    win = []
    for p in tune.parts:
        rs = bars[p]
        for w0 in range(0, len(rs), 8):
            cnt = {}
            for r in rs[w0:w0 + 8]:
                if len(r) >= 2:
                    cnt[r] = cnt.get(r, 0) + 1
            if cnt:
                win.append(max(cnt.values()))
    res['cell8'] = round(sum(win) / len(win), 2) if win else 0.0
    res['cell8_max'] = max(win, default=0)
    second = next((p for p in tune.parts[1:] if p[0] == 'A'), None)
    res['vary_bar'] = None
    if second is not None:
        for b in range(len(bars[a1])):
            w1 = sorted((round(s - b * tune.meter, 3), round(d, 3), q) for s, d, q in tune.melody[a1]
                        if b * tune.meter - 1e-6 <= s < (b + 1) * tune.meter - 1e-6)
            w2 = sorted((round(s - b * tune.meter, 3), round(d, 3), q) for s, d, q in tune.melody[second]
                        if b * tune.meter - 1e-6 <= s < (b + 1) * tune.meter - 1e-6)
            if w1 != w2:
                res['vary_bar'] = b + 1
                break
    labels: dict = {}
    for sec in (head, solo, out_sec):
        if sec is None:
            continue
        for p in sec.parts:
            base = p.name.rstrip('v').rstrip('0123456789') if tune.form == 'blues' else p.name.rstrip('v')
            if p.prog is not None:
                labels.setdefault(base, set()).add(tuple((None if c is None else (c.root % 12, tuple(c.intervals)),
                                                          round(d, 3)) for c, d in p.prog.items))
    res['chart_vars'] = sum(len(v) - 1 for v in labels.values())
    res.update(solo_shape=getattr(tune, 'solo_shape', None), double=getattr(tune, 'double', None),
               tag_approach=(tune.tag or {}).get('approach'), end_kind=getattr(tune, 'end_kind', None),
               feel_form=f"{tune.feel}/{tune.form}/{'swing' if tune.swing else 'even'}")
    return res


def _hook_cells(motif) -> list:
    """The hook's 4-note cells worth developing: (onset gaps in 12ths, intervals) of every 4 consecutive notes - not
    a plain run (equal gaps and only steps), which any line has."""
    hk = sorted(motif)
    out = []
    for i in range(len(hk) - 3):
        w = hk[i:i + 4]
        gaps = tuple(round((b[0] - a[0]) * 12) for a, b in zip(w, w[1:]))
        ivs = tuple(b[2] - a[2] for a, b in zip(w, w[1:]))
        if len(set(gaps)) == 1 and all(abs(x) <= 2 for x in ivs):
            continue
        out.append((gaps, ivs))
    return out


def developed(window, cells) -> bool:
    """A 4-attack window [(start, pitch)] is a development of one of the hook's cells (_hook_cells): its onset gaps the
    cell's in time, augmented or diminished (x1 / x2 / x0.5), and its contour the cell's or its inversion (every step
    the same direction, within 2 semitones of the cell's: a sequence re-fitted to new chords) - at any transposition,
    anywhere in the bar (displaced)."""
    gaps = [round((b[0] - a[0]) * 12) for a, b in zip(window, window[1:])]
    ivs = [b[1] - a[1] for a, b in zip(window, window[1:])]
    for cg, ci in cells:
        if not any(all(abs(g - c * f) <= 0.5 for g, c in zip(gaps, cg)) for f in (1.0, 2.0, 0.5)):
            continue
        for s in (1, -1):
            if all(_sign(a) == _sign(s * b) and abs(a - s * b) <= 2 for a, b in zip(ivs, ci)):
                return True
    return False


def _arp_bar(tops, chord_at, least: int = 4) -> bool:
    """A bar that is a pure chord arpeggio: `least`+ attacks [(start, pitch)], every one a tone of the chord written
    there, most steps a 3rd or more (the chord spelled out, not a line)."""
    if len(tops) < least:
        return False
    for t, p in tops:
        ch = chord_at(t + 1e-3)
        if ch is None or p % 12 not in {(ch.root + x) % 12 for x in ch.intervals}:
            return False
    ds = [abs(b[1] - a[1]) for a, b in zip(tops, tops[1:])]
    return sum(d >= 3 for d in ds) >= 0.6 * len(ds)


def _tells_r5(view, tune) -> dict:
    """The round-5 measures of tells() (the composer judge's advice, in his order):
      arp5          share of solo bars that are a pure chord arpeggio (_arp_bar: 4+ attacks, all tones of the written
                    chord, mostly 3rds+; the judge: <= ~1 in 4); ct_bars: share of its bars of 4+ attacks with 85 %+
                    chord tones
      motif_ph     share of the solo's phrases (split at a beat+ of nothing struck) holding a development of a hook
                    cell (developed(): sequenced / inverted / displaced / augmented, with tune=); ph_beats: the
                    phrases' mean length (beats), ph_cross: the share crossing a bar line
      onset_max32   the most uses of one bar onset pattern (3-6 right-hand attacks) in any 32-bar window of the piece
                    (the judge: <= ~4, then displaced / augmented variants)
      head_guide    (tune=) share of the head's chord changes met by a 3rd / 7th of the new chord reached by step (or
                    held over); head_arp: share of its bars (3+ notes) that are a chord arpeggio
      chrom / chrom_bad   chromatic right-hand top notes (outside the chord's own scale, its tones and tensions) in the
                    head / solo / out per 32 bars; chrom_bad: of them not a single 8th or shorter resolving by half
                    step to a chord tone on the next beat (harmonized, held, unresolved)
      solo_db2      the solo's note energy from its 2nd chorus on (a one-chorus solo: its second half) - the head's
                    (dB); solo_vel2: its mean top velocity - the head's; solo_last_peak: 1 when the last chorus / half
                    is the solo's loudest; single_run: the longest run of solo bars with one right-hand attack or none
      frame_copy    (tune=) share of the intro / tag melody bars that copy a head bar (its onsets and intervals at any
                    transposition)
      bridge_end    the fewest sung right-hand attacks (an 8th+) in the last two bars of a bridge (head / out; no B:
                    None); peak_last: (tune=) share of the head's choruses whose highest note sits in the chorus's last
                    section (a blues: bars 9-12) and only there
      a_range       (tune=) the smallest melody range (semitones) of an A section (a blues: a chorus); a_range_mean
      solo_end      1 when the solo's last attack is a chord tone of the next section's first chord, or steps into
                    the next section's first note on one - and not the end of a chromatic run"""
    m, rh, lh, cl = view.m, view.rh, view.lh, view.cl
    import math
    from ..theory import chord_scale as _cscale
    head, solo, out_sec = view.secs['head'], view.secs['solo'], view.secs.get('out')
    chord_at = _chord_fn(view)
    nb = int(round(solo.length / m))
    res: dict = {}
    sc = [c for c in cl if solo.start - 1e-6 <= c[0] < solo.end - 1e-6]
    # ---- 1: arpeggio bars, motif-derived phrases
    bars = [[(c[0], c[1][2]) for c in sc if solo.start + k * m - 1e-6 <= c[0] < solo.start + (k + 1) * m - 1e-6]
            for k in range(nb)]
    res['arp5'] = round(sum(_arp_bar(b, chord_at) for b in bars) / max(1, nb), 3)

    def tones(t):
        ch = chord_at(t + 0.06)
        return set() if ch is None else {(ch.root + x) % 12 for x in ch.intervals}
    full = [b for b in bars if len(b) >= 4]
    res['ct_bars'] = round(sum(sum(p % 12 in tones(t) for t, p in b) >= 0.85 * len(b) for b in full)
                           / max(1, len(full)), 2)
    phrases, end = [], -1e9
    for t, top, _ in sc:
        if t - end >= 1.0 - 1e-6 or not phrases:
            phrases.append([])
        phrases[-1].append((t, top[2]))
        end = max(end, max(n[0] + n[1] for n in rh if abs(n[0] - t) < 0.1))
    phrases = [p for p in phrases if len(p) >= 3]
    if tune is not None and len(tune.motif) >= 4:
        cells = _hook_cells(tune.motif)
        res['motif_ph'] = round(sum(any(developed(p[i:i + 4], cells) for i in range(len(p) - 3)) for p in phrases)
                                / max(1, len(phrases)), 2) if cells else None
    lens = [p[-1][0] - p[0][0] + 0.5 for p in phrases]
    res['ph_beats'] = round(sum(lens) / len(lens), 1) if lens else 0.0
    res['ph_cross'] = round(sum(math.floor((p[0][0] - solo.start) / m + 1e-6) !=
                                math.floor((p[-1][0] - solo.start) / m + 1e-6) for p in phrases) / max(1, len(phrases)), 2)
    # ---- 2: one onset pattern per 32 bars
    piece0, end0 = view.sections[0].start, (view.secs['end'].start if 'end' in view.secs else max(n[0] for n in rh) + m)
    pats = []
    for k in range(int(round((end0 - piece0) / m))):
        a = piece0 + k * m
        on = tuple(round((c[0] - a) * 12) for c in cl if a - 1e-6 <= c[0] < a + m - 1e-6)
        pats.append(on if 3 <= len(on) <= 6 else None)
    best = 0
    for w0 in range(0, max(1, len(pats) - 31), 4):
        cnt: dict = {}
        for p_ in pats[w0:w0 + 32]:
            if p_ is not None:
                cnt[p_] = cnt.get(p_, 0) + 1
        best = max(best, max(cnt.values(), default=0))
    res['onset_max32'] = best
    # ---- 4: chromatic notes in the right hand's top line
    body = [x for x in (head, solo, out_sec) if x is not None]
    chrom = bad = 0
    cs = [c for c in cl if any(s_.start - 1e-6 <= c[0] < s_.end - 1e-6 for s_ in body)]
    changes = sorted({round(s_.start + t, 6) for s_ in view.sections if s_.prog is not None for t, _, _ in s_.prog})
    for j, (t, top, size) in enumerate(cs):
        # a note struck a hair early (the touch) or anticipating a change by up to an 8th belongs to the next chord
        ant = next((x for x in changes if t < x <= t + 0.55 and t + top[1] > x + 0.1), None)
        ch = chord_at((ant if ant is not None else t + 0.06) + 1e-3)
        if ch is None or top[1] <= 0.15:
            continue
        x = (top[2] - ch.root) % 12
        own = set(_cscale(ch)) | {i % 12 for i in ch.intervals} | set(available_tensions(ch))
        if x in own:
            continue
        chrom += 1
        nx = cs[j + 1] if j + 1 < len(cs) else None
        ok = top[1] <= 0.55 and size == 1 and nx is not None and 0 < nx[0] - t <= 1.0 + 1e-6 \
            and abs(nx[1][2] - top[2]) == 1 and abs(nx[0] - round(nx[0])) < 0.05
        if ok:
            ch2 = chord_at(nx[0] + 1e-3)
            ok = ch2 is not None and nx[1][2] % 12 in {(ch2.root + i) % 12 for i in ch2.intervals}
        bad += not ok
    body_bars = sum(s_.length for s_ in body) / m
    res['chrom'] = round(chrom * 32 / max(1, body_bars), 2)
    res['chrom_bad'] = round(bad * 32 / max(1, body_bars), 2)
    # ---- 5: the solo's intensity arc

    def vel(spans):
        vs = [c[1][3] for c in cl if c[1][1] >= 0.12 and any(a - 1e-6 <= c[0] < b - 1e-6 for a, b in spans)]
        return sum(vs) / len(vs) if vs else 0.0
    ch_beats = 12 * m if tune is not None and tune.form == 'blues' else head.length
    n_ch = int(round(solo.length / ch_beats))
    segs = [(solo.start + k * ch_beats, solo.start + (k + 1) * ch_beats) for k in range(n_ch)] if n_ch >= 2 else \
        [(solo.start, solo.start + solo.length / 2), (solo.start + solo.length / 2, solo.end)]
    hs = [(head.start, head.end)]
    res['solo_db2'] = round(view.db(segs[1:]) - view.db(hs), 1)
    res['solo_vel2'] = round(vel(segs[1:]) - vel(hs), 1)
    dbs = [view.db([s_]) for s_ in segs]
    res['solo_last_peak'] = int(dbs[-1] >= max(dbs) - 0.05)
    run = best = 0
    for k, b in enumerate(bars):            # (a traded bar's comping chord is not a single note)
        a = solo.start + k * m
        run = run + 1 if len(b) <= 1 and not any(a - 1e-6 <= c[0] < a + m - 1e-6 and c[2] >= 3 for c in sc) else 0
        best = max(best, run)
    res['single_run'] = best
    # ---- 7: the bridge keeps a line into its turnaround
    ends = []
    for sec in (head, out_sec):
        for p in (sec.parts if sec is not None else []):
            if p.name.rstrip('v') != 'B':
                continue
            a, z = p.end - 2 * m, p.end
            ends.append(sum(1 for c in cl if a - 1e-6 <= c[0] < z - 1e-6 and c[1][1] >= 0.4))
    res['bridge_end'] = min(ends) if ends else None
    # ---- 9: the solo ends on a target
    res['solo_end'] = None
    if sc and out_sec is not None:
        nxt_ch = chord_at(out_sec.start + 1e-3)
        first = next((c for c in cl if c[0] >= out_sec.start - 1e-6), None)
        tones = {(nxt_ch.root + i) % 12 for i in nxt_ch.intervals} if nxt_ch is not None else set()
        last = sc[-1][1][2]
        tail = [c[1][2] for c in sc[-4:]]
        chromatic = len(tail) == 4 and all(abs(b - a) == 1 for a, b in zip(tail, tail[1:])) and \
            len({_sign(b - a) for a, b in zip(tail, tail[1:])}) == 1
        steps_in = first is not None and abs(first[1][2] - last) <= 2 and first[1][2] % 12 in tones
        res['solo_end'] = int((last % 12 in tones or steps_in) and not chromatic)
    if tune is None:
        return res
    # ---- the head as written: guide tones, arpeggios, the peak per chorus, the A's range
    key_pcs = set(Key(tune.key).pcs)
    hits = n_chg = arp_b = n_b = 0
    for p in tune.parts:
        mel = sorted(tune.melody[p])
        harm = Harm(tune.changes[p], key_pcs)
        for st0, _, ci in harm.items[1:]:
            held_ = [n for n in mel if n[0] < st0 - 1e-6 and st0 + 1e-6 < n[0] + n[1]]
            new = [n for n in mel if st0 - 1e-6 <= n[0] < st0 + 1.0 - 1e-6]
            if held_:
                n_chg += 1
                hits += held_[-1][2] % 12 in ci.guide
            elif new:
                n_chg += 1
                before = [n for n in mel if n[0] < new[0][0] - 1e-6]
                hits += new[0][2] % 12 in ci.guide and (not before or abs(new[0][2] - before[-1][2]) <= 2)
        for b in range(int(round(tune.part_beats(p) / tune.meter))):
            tops = [(n[0], n[2]) for n in mel if b * tune.meter - 1e-6 <= n[0] < (b + 1) * tune.meter - 1e-6]
            if len(tops) >= 3:
                n_b += 1
                arp_b += _arp_bar(tops, lambda t, h=harm: h.at(t).chord, least=3)
    res['head_guide'] = round(hits / max(1, n_chg), 2)
    res['head_arp'] = round(arp_b / max(1, n_b), 2)

    def sig(notes):
        ns = sorted(notes)
        return tuple(round(n[0] * 12) for n in ns) + tuple(b[2] - a[2] for a, b in zip(ns, ns[1:]))
    hb = set()
    for p in tune.parts:
        for b in range(int(round(tune.part_beats(p) / tune.meter))):
            ns = [(s - b * tune.meter, d, q) for s, d, q in tune.melody[p]
                  if b * tune.meter - 1e-6 <= s < (b + 1) * tune.meter - 1e-6]
            if len(ns) >= 2:
                hb.add(sig(ns))
    fb = fc = 0
    for fr in (tune.intro, tune.tag):
        mel = fr.get('melody', [])
        for b in range(int(round(_beats(fr.get('changes', [])) / tune.meter))):
            ns = [(s - b * tune.meter, d, q) for s, d, q in mel
                  if b * tune.meter - 1e-6 <= s < (b + 1) * tune.meter - 1e-6]
            if len(ns) >= 2:
                fb += 1
                fc += sig(ns) in hb
    res['frame_copy'] = round(fc / max(1, fb), 2)
    choruses = [[p] for p in tune.parts] if tune.form == 'blues' else [list(tune.parts)]
    ok = 0
    for chs in choruses:
        notes = [(p, n) for p in chs for n in tune.melody[p]]
        top = max(n[2] for _, n in notes)
        where = {(p, n[0] >= 8 * tune.meter - 1e-6 if tune.form == 'blues' else p == chs[-1]) for p, n in notes
                 if n[2] == top}
        ok += all(last for _, last in where)
    res['peak_last'] = round(ok / max(1, len(choruses)), 2)
    rngs = [max(n[2] for n in tune.melody[p]) - min(n[2] for n in tune.melody[p]) for p in tune.parts
            if (p[0] == 'A' or tune.form == 'blues') and tune.melody[p]]
    res['a_range'] = min(rngs, default=None)
    res['a_range_mean'] = round(sum(rngs) / len(rngs), 1) if rngs else None
    return res


def _tells_r6(view, tune) -> dict:
    """The round-6 measures of tells() (four composer / pianist judges and a statistician, 8/8, against the pro2
    references; the r6 breath fix overshot in the solo and the form's end):
      solo continuity   solo_att / head_att: right-hand attacks per bar (refs: solo 4.3-6.2), dens_ratio solo / head
                    (>= 1.3); sil_ch / sil_ch_max: silent right-hand solo bars per chorus (mean / most; <= 1);
                    sil_cad: of them in a part's last 2 bars (the cadence / turnaround: 0); both_mid: head / solo /
                    head-out bars where neither hand strikes
      solo phrases      (split at a beat+ with nothing sounding) ph_len / ph_sd / ph_max beats (refs 12.5-46, heavy
                    tailed), long16: share of the solo choruses holding a line of 16+ beats, upbeat: share of the
                    phrases starting off the beat, eighths: share of the in-phrase steps an 8th apart
      solo line         dir_chg: direction changes per step (refs 0.30-0.42), leap5: steps of 5+ semitones (7-15 %),
                    rep_p: repeated pitches (0-3 %); vel_p10: the right hand's 10th-percentile velocity (refs 47-52)
      form              out_db: the head out's note energy - the head's (tells r3); end_db: the tag + ending's - the
                    body's (head, solo, head out); final_vel: the softest note of the final chord; after_final: attacks
                    struck after the final chord (its roll / cadenza included)
      climax            top_sec: the section of the highest right-hand note (before the ending), top_solo_end: 1 when
                    it sits in the solo's last 16 bars, top_over_head: its height over the head's highest note
                    (semitones), top_vel, top_rise: 1 when the 3 bars before climb into it (each bar's highest note
                    higher than the one before), out_below: 1 when the head out / tag / ending stay under it
      head              head_centre: the median pitch of the head's top line (MIDI; refs ~G5-C6 = 79-84), head_span:
                    its 10-90 % range, head_vel: its mean top velocity; head_rise8: the mean rise (semitones) of an
                    8-bar window's highest note over its first; a_ends: (tune=) 1 when the A1 and A2 end differently
      reharm            reharm_col: share of the head out's substituted chords (against the head's same part) whose
                    first sung top note (an 8th+ struck in its first beat or anticipating it) is a colour tone (9 / #11
                    / 13 / b9 / #9 / b13)
      loops             cell_loop: the longest run of one bar (3+ attacks) repeated literally over changing chords
      left hand         lh_bare: head / solo / head-out bars with 4+ single-note left-hand attacks (bare roots);
                    lh_alt: the longest run of bars alternating struck / empty; lh_jump: section / part boundaries where
                    the attacks per bar jump by 4+ (the 2 bars before vs after)
      frame             frame_hold: the most chords one right-hand top pitch spans in the intro / tag (held, or struck
                    again and again with no other top note: a pad); frame_hook: (tune=) statements of the hook in the
                    intro + tag
      gestures          scoops: quick 4-note groups (onsets <= 0.2 beat apart) in the head out's last two bars; end_kind
                    the final chord's style (tune=)"""
    m, rh, lh, cl = view.m, view.rh, view.lh, view.cl
    import statistics as st
    head, solo, out_sec = view.secs['head'], view.secs['solo'], view.secs.get('out')
    body = [x for x in (head, solo, out_sec) if x is not None]
    res: dict = {}

    onsets = view.onsets
    hb = head.length / m
    sb = solo.length / m
    res['head_att'] = round(len(onsets(head.start, head.end)) / hb, 2)
    res['solo_att'] = round(len(onsets(solo.start, solo.end)) / sb, 2)
    res['dens_ratio'] = round(res['solo_att'] / max(1e-9, res['head_att']), 2)
    # choruses / parts of the solo
    blues = len({p.name[0] for p in head.parts}) == 1
    ch_beats = head.parts[0].length if blues else head.length
    n_ch = max(1, int(round(solo.length / ch_beats)))
    sil = [0] * n_ch
    cad = 0
    for k in range(int(round(sb))):
        a = solo.start + k * m
        if onsets(a, a + m):
            continue
        sil[min(n_ch - 1, int((a - solo.start + 1e-6) // ch_beats))] += 1
        part = next((p for p in solo.parts if p.start - 1e-6 <= a < p.end - 1e-6), None)
        cad += part is not None and a >= part.end - 2 * m - 1e-6
    res['sil_ch'] = round(sum(sil) / n_ch, 2)
    res['sil_ch_max'] = max(sil)
    res['sil_cad'] = cad
    lcl = view.lcl
    both = 0
    for sec in body:
        for k in range(int(round(sec.length / m))):
            a = sec.start + k * m
            both += not onsets(a, a + m) and not onsets(a, a + m, lcl)
    res['both_mid'] = both
    # ---- the solo's phrases and line
    sc = onsets(solo.start, solo.end)
    phrases, end = [], -1e9
    for t, top, _ in sc:
        if t - end >= 1.0 - 1e-6 or not phrases:
            phrases.append([])
        phrases[-1].append((t, top[2], top[1]))
        end = max(end, max(n[0] + n[1] for n in rh if abs(n[0] - t) < 0.1))
    lens = [p[-1][0] + min(p[-1][2], 1.0) - p[0][0] for p in phrases if len(p) >= 2]
    res['ph_len'] = round(st.mean(lens), 1) if lens else 0.0
    res['ph_sd'] = round(st.pstdev(lens), 1) if len(lens) > 1 else 0.0
    res['ph_max'] = round(max(lens), 1) if lens else 0.0
    longs = {int((p[0][0] - solo.start + 1e-6) // ch_beats) for p in phrases if len(p) >= 2
             and p[-1][0] + min(p[-1][2], 1.0) - p[0][0] >= 16 - 1e-6}
    res['long16'] = round(len(longs) / n_ch, 2)
    starts = [p[0][0] for p in phrases if len(p) >= 2]
    res['upbeat'] = round(sum(abs(t - round(t)) > 0.1 for t in starts) / max(1, len(starts)), 2)
    steps = [(b[0] - a[0], b[1] - a[1]) for p in phrases for a, b in zip(p, p[1:])]
    res['eighths'] = round(sum(0.4 <= d <= 0.6 for d, _ in steps) / max(1, len(steps)), 2)
    moves = [iv for _, iv in steps]
    dirs = [x for x in moves if x]
    res['dir_chg'] = round(sum(_sign(a) != _sign(b) for a, b in zip(dirs, dirs[1:])) / max(1, len(dirs) - 1), 2)
    res['leap5'] = round(sum(abs(x) >= 5 for x in moves) / max(1, len(moves)), 3)
    res['rep_p'] = round(sum(x == 0 for x in moves) / max(1, len(moves)), 3)
    vs = sorted(c[1][3] for c in cl if any(s_.start - 1e-6 <= c[0] < s_.end - 1e-6 for s_ in body))
    res['vel_p10'] = vs[int(0.1 * (len(vs) - 1))] if vs else None
    # ---- the form's dynamics
    frame_end = [(x.start, x.end) for x in view.sections if x.name in ('tag', 'end')]
    res['end_db'] = round(view.db(frame_end) - view.db([(x.start, x.end) for x in body]), 1) if frame_end else None
    end = view.secs.get('end')
    if end is not None:
        lh_end = [n for n in lh if n[0] >= end.start - 0.3]
        tf = min((n[0] for n in lh_end), default=end.start)
        fin = [n for n in rh + lh if tf - 0.3 <= n[0] <= tf + 2.0]
        res['final_vel'] = min((n[3] for n in fin), default=None)
        res['after_final'] = len(_clusters([n for n in rh + lh if n[0] > tf + 2.0]))
    # ---- the climax
    end0 = end.start if end is not None else max(n[0] for n in rh) + m
    pre = [n for n in rh if n[0] < end0 - 0.25]
    top = max(pre, key=lambda n: (n[2], -n[0]))
    tsec = next((x for x in view.sections if x.start - 1e-6 <= top[0] < x.end - 1e-6), None)
    res['top_sec'] = tsec.name if tsec else None
    res['top_solo_end'] = int(solo.end - 16 * m - 1e-6 <= top[0] < solo.end)
    h_top = max((n[2] for n in rh if head.start - 1e-6 <= n[0] < head.end - 1e-6), default=0)
    res['top_over_head'] = top[2] - h_top
    res['top_vel'] = top[3]
    kb = int((top[0] + 1e-6) // m)
    bmax = [max((n[2] for n in rh if (kb - j) * m - 1e-6 <= n[0] < (kb - j + 1) * m - 1e-6), default=None)
            for j in (3, 2, 1)]
    res['top_rise'] = int(all(x is not None for x in bmax) and bmax[0] < bmax[1] < bmax[2] < top[2] + 1)
    later = [n[2] for n in rh if n[0] > top[0] + m and n[0] >= (out_sec.start if out_sec else solo.end) - 1e-6]
    res['out_below'] = int(max(later, default=0) < top[2])
    # ---- the head as played
    hl = sorted(onsets(head.start, head.end), key=lambda c: c[0])
    hp = sorted(c[1][2] for c in hl if c[1][1] >= 0.2)
    if hp:
        res['head_centre'] = hp[len(hp) // 2]
        res['head_span'] = hp[int(0.9 * (len(hp) - 1))] - hp[int(0.1 * (len(hp) - 1))]
        res['head_vel'] = round(st.mean(c[1][3] for c in hl if c[1][1] >= 0.2), 1)
    rises = []
    for k in range(0, int(round(hb)) - 7, 8):
        w = [c[1][2] for c in hl if head.start + k * m - 1e-6 <= c[0] < head.start + (k + 8) * m - 1e-6]
        if len(w) >= 3:
            rises.append(max(w) - w[0])
    res['head_rise8'] = round(st.mean(rises), 1) if rises else None
    if tune is not None and len(tune.parts) > 1 and tune.parts[1][0] == tune.parts[0][0]:
        a1, a2 = tune.parts[0], tune.parts[1]
        z1, z2 = tune.part_beats(a1), tune.part_beats(a2)

        def tail(p, z):
            return sorted((round(s - z, 3), q) for s, _, q in tune.melody[p] if s >= z - 2 * tune.meter - 1e-6)
        res['a_ends'] = int(tail(a1, z1) != tail(a2, z2))
    # ---- the reharms: the downbeat melody on a substituted chord
    chord_at = _chord_fn(view)
    base = {}
    for p in head.parts:
        t = 0.0
        for c, d in p.prog.items:
            base[(p.name.rstrip('v'), round(t, 3))] = None if c is None else (c.root % 12, tuple(c.intervals))
            t += d
    col = n_sub = 0
    for sec in (out_sec,):
        for p in (sec.parts if sec is not None else []):
            t = 0.0
            for c, d in p.prog.items:
                key_ = (p.name.rstrip('v'), round(t, 3))
                me = None if c is None else (c.root % 12, tuple(c.intervals))
                if key_ in base and me is not None and base[key_] != me:
                    at = p.start + t
                    hit = [c_ for c_ in cl if at - 0.55 <= c_[0] < at + 1.0 and c_[1][1] >= 0.4
                           and c_[0] + c_[1][1] > at + 0.25]
                    sounding = [n for n in rh if n[0] <= at + 0.1 and n[0] + n[1] > at + 0.05]
                    q = (hit[0][1][2] if hit else max((n[2] for n in sounding), default=None))
                    if q is not None:
                        n_sub += 1
                        x_ = (q - c.root) % 12
                        col += x_ in (1, 2, 6, 8, 9) or (x_ == 3 and not c.is_minor) or (x_ == 5 and c.is_minor)
                t += d
    res['reharm_col'] = round(col / n_sub, 2) if n_sub else None
    # ---- literal cell loops over changing chords
    total = int(round((end0 - view.sections[0].start) / m))
    sigs = []
    for k in range(total):
        a = view.sections[0].start + k * m
        on = onsets(a, a + m)
        c = chord_at(a + 1e-3)
        sigs.append((tuple((round((x[0] - a) * 12), x[1][2]) for x in on) if len(on) >= 3 else None,
                     None if c is None else (c.root % 12, tuple(c.intervals))))
    run = best = 0
    for k in range(1, total):
        if sigs[k][0] is not None and sigs[k][0] == sigs[k - 1][0] and sigs[k][1] != sigs[k - 1][1]:
            run = run + 1 if run else 2
        elif sigs[k][0] is None or sigs[k][0] != sigs[k - 1][0]:
            run = 0
        best = max(best, run)
    res['cell_loop'] = best
    # ---- the left hand
    bare = 0
    lbars = []
    bounds = sorted({round(p.start, 3) for x in body for p in x.parts} | {round(x.start, 3) for x in body})
    for sec in body:
        for k in range(int(round(sec.length / m))):
            a = sec.start + k * m
            lc = onsets(a, a + m, lcl)
            lbars.append((a, len(lc)))
            single = [c for c in lc if c[2] == 1]
            if len(single) >= 4:
                ch = chord_at(a + 1e-3)
                bare += ch is not None and sum((c[1][2] - ch.root) % 12 == 0 for c in single) >= 3
    res['lh_bare'] = bare
    run = best = 0
    for (_, x), (_, y) in zip(lbars, lbars[1:]):
        run = run + 1 if (x == 0) != (y == 0) else 0
        best = max(best, run)
    res['lh_alt'] = best + 1 if best else 0
    cnt = dict(lbars)
    jumps = 0
    for b0 in bounds[1:]:
        bef = [cnt.get(round(b0 - j * m, 3)) for j in (1, 2)]
        aft = [cnt.get(round(b0 + j * m, 3)) for j in (0, 1)]
        if None not in bef + aft and abs(sum(aft) - sum(bef)) / 2 >= 4:
            jumps += 1
    res['lh_jump'] = jumps
    # ---- the frame: a held note over changing chords, the hook stated
    hold = 0
    for x in view.sections:
        if x.name not in ('intro', 'tag') or x.prog is None:
            continue
        fx_ = onsets(x.start, x.end)
        chg = [x.start + t for t, _, _ in x.prog]
        j = 0
        while j < len(fx_):                  # one top pitch held or struck again and again (a pad's top)
            k = j
            while k + 1 < len(fx_) and fx_[k + 1][1][2] == fx_[j][1][2]:
                k += 1
            nxt = fx_[k + 1][0] if k + 1 < len(fx_) else x.end
            z = min(fx_[k][0] + fx_[k][1][1], nxt)
            hold = max(hold, sum(1 for t in chg if fx_[j][0] + 0.1 < t < z - 0.1) + 1)
            j = k + 1
    res['frame_hold'] = hold
    if tune is not None and len(tune.motif) >= 3:
        fr = [n for n in rh if any(x.name in ('intro', 'tag') and x.start - 1e-6 <= n[0] < x.end - 1e-6
                                   for x in view.sections)]
        res['frame_hook'] = len(hook_matches(top_line(fr, tol=0.08), sorted(tune.motif), scales=(1.0, 2.0),
                                             share=0.8, contour=0.75, tol=0.2))
    # ---- shared gestures
    if out_sec is not None:
        a = out_sec.end - 2 * m
        on = [c[0] for c in cl if a - 1e-6 <= c[0] < out_sec.end + 0.5]      # (a rolled chord is one attack)
        sc4 = 0
        j = 0
        while j + 3 < len(on):
            if all(on[i + 1] - on[i] <= 0.2 for i in range(j, j + 3)):
                sc4 += 1
                j += 4
            else:
                j += 1
        res['scoops'] = sc4
    if tune is not None:
        res['end_kind'] = getattr(tune, 'end_kind', None)
    return res


def _tells_r7(view, tune) -> dict:
    """The round-7 measures of tells() (three composer judges 5/8 5/8 7/8, the statistician 8/8; ROUNDS.md 'Round 7'):
      licks         lick_near: solo windows of 5 top-line attacks whose pitches (as struck, not transposed) recur in a
                    window starting within the 4 bars before, per 32 solo bars (round 7: a chromatic D-Eb-F-F#-G cell
                    4x in 4 bars); lick_max: the most uses of one such 5-note cell in the solo
      16ths         run16: the longest run of solo bars in 16th motion (4+ steps of a 16th or less, half the bar's
                    steps); solo16: the share of the solo's bars in 16ths (round 7: a bossa solo in 16ths for 7 bars)
      head pads     head_one: share of the head's bars with one right-hand attack or none; head_alt: the longest run of
                    head bars alternating 2+ attacks / one or none ("a one-note bar every other bar")
      bridge        bridge_one: share of the bridge's bars (the head's B) with one attack or none (no B: None)
      quotes        head_quote: solo windows of 6 top-line attacks equal to a window of the head's (pitches and onset
                    gaps: the head pasted into the solo); open_quote: (tune=) 1 when the hook is stated in the solo's
                    first two bars
      touch         vel_pitch: share of the solo's steps (attacks a beat or less apart, both pitch and velocity moving)
                    whose velocity moves with the pitch (round 7: 74-84 %, the references ~50-60 %); climb_step: the
                    largest bar-to-bar rise of the loudest top velocity over the 4 bars into the piece's highest note
                    (a step instead of a ladder); lh_over: share of the body's bars (both hands striking) where the
                    left hand's loudest attack is louder than the right hand's loudest
      skeleton      (per tune; the set's spread is the tell) out_from: the share of the head the head out skips
                    (0: all of it, 0.5: its second half); tag_intro: 1 when the tag opens on the intro's first chord;
                    out_reharm: 1 when the head out plays a substituted part"""
    m, cl = view.m, view.cl
    head, solo, out_sec = view.secs['head'], view.secs['solo'], view.secs.get('out')
    onsets = view.onsets
    res: dict = {}
    sc = onsets(solo.start, solo.end)
    nb = max(1, int(round(solo.length / m)))
    # ---- licks: one 5-note cell (its pitches as struck) again within 4 bars
    ps = [(c[0], c[1][2]) for c in sc]
    wins = [(ps[i][0], tuple(p for _, p in ps[i:i + 5]), i) for i in range(len(ps) - 4)]
    near = 0
    count: dict = {}
    for t, sig, i in wins:
        count[sig] = count.get(sig, 0) + 1
        if any(s2 == sig and t - t2 <= 4 * m + 1e-6 and i - j >= 5 for t2, s2, j in wins if j < i):
            near += 1
    res['lick_near'] = round(near * 32 / nb, 2)
    res['lick_max'] = max(count.values(), default=0)
    # ---- 16th motion
    sixteen = []
    for k in range(nb):
        a = solo.start + k * m
        ts = [c[0] for c in onsets(a, a + m)]
        gaps = [y - x for x, y in zip(ts, ts[1:])]
        fast = sum(g <= 0.3 for g in gaps)
        sixteen.append(fast >= 4 and fast >= 0.5 * len(gaps))
    run = best = 0
    for x in sixteen:
        run = run + 1 if x else 0
        best = max(best, run)
    res['run16'] = best
    res['solo16'] = round(sum(sixteen) / nb, 2)
    # ---- the head: one-note bars, every other bar
    hb = int(round(head.length / m))
    per = [len(onsets(head.start + k * m, head.start + (k + 1) * m)) for k in range(hb)]
    res['head_one'] = round(sum(x <= 1 for x in per) / max(1, hb), 2)
    run = best = 0
    for x, y in zip(per, per[1:]):
        run = run + 1 if (x <= 1) != (y <= 1) else 0
        best = max(best, run)
    res['head_alt'] = best + 1 if best else 0
    bp = [p for p in head.parts if p.name[0] == 'B']
    if bp and len({p.name[0] for p in head.parts}) > 1:
        bb = [len(onsets(p.start + k * m, p.start + (k + 1) * m)) for p in bp for k in range(int(round(p.length / m)))]
        res['bridge_one'] = round(sum(x <= 1 for x in bb) / max(1, len(bb)), 2)
    else:
        res['bridge_one'] = None
    # ---- the head pasted into the solo
    hl = onsets(head.start, head.end)

    def sig6(cs, i):
        w = cs[i:i + 6]
        return tuple(c[1][2] for c in w) + tuple(round((y[0] - x[0]) * 12) for x, y in zip(w, w[1:]))
    hs = {sig6(hl, i) for i in range(len(hl) - 5)}
    q, i = 0, 0
    while i < len(sc) - 5:
        if sig6(sc, i) in hs:
            q += 1
            i += 6
        else:
            i += 1
    res['head_quote'] = q
    if tune is not None and len(tune.motif) >= 3:
        first = top_line([n for n in view.rh if solo.start - 1e-6 <= n[0] < solo.start + 2 * m], tol=0.08)
        res['open_quote'] = int(bool(hook_matches(first, sorted(tune.motif), scales=(1.0,), share=0.8, contour=0.75,
                                                  tol=0.2)))
    # ---- touch: velocity with the pitch, the climb into the peak, the left hand over the melody
    same = tot = 0
    for x, y in zip(sc, sc[1:]):
        if y[0] - x[0] > 1.0 + 1e-6:
            continue
        dp, dv = y[1][2] - x[1][2], y[1][3] - x[1][3]
        if dp and dv:
            tot += 1
            same += _sign(dp) == _sign(dv)
    res['vel_pitch'] = round(same / tot, 2) if tot else None
    end = view.secs.get('end')
    end0 = end.start if end is not None else max(n[0] for n in view.rh) + m
    pre = [n for n in view.rh if n[0] < end0 - 0.25]
    top = max(pre, key=lambda n: (n[2], -n[0]))
    kb = int((top[0] + 1e-6) // m)
    bv = [max((c[1][3] for c in onsets((kb - j) * m, (kb - j + 1) * m)), default=None) for j in (4, 3, 2, 1)]
    bv = [v for v in bv if v is not None] + [top[3]]
    res['climb_step'] = max((y - x for x, y in zip(bv, bv[1:])), default=0)
    lcl = view.lcl
    over = n_b = 0
    for sec in [x for x in (head, solo, out_sec) if x is not None]:
        for k in range(int(round(sec.length / m))):
            a = sec.start + k * m
            r_, l_ = onsets(a, a + m), onsets(a, a + m, lcl)
            if r_ and l_:
                n_b += 1
                over += max(c[1][3] for c in l_) > max(c[1][3] for c in r_)
    res['lh_over'] = round(over / max(1, n_b), 2)
    # ---- the skeleton
    if out_sec is not None and out_sec.parts:
        names = [p.name.rstrip('v') for p in head.parts]
        first = out_sec.parts[0].name.rstrip('v')
        res['out_from'] = round(names.index(first) / len(names), 2) if first in names else None
        res['out_reharm'] = int(any(p.name.endswith('v') for p in out_sec.parts))
    intro, tag = view.secs.get('intro'), view.secs.get('tag')
    if intro is not None and tag is not None and intro.prog is not None and tag.prog is not None \
            and intro.prog.items and tag.prog.items:
        c0, c1 = intro.prog.items[0][0], tag.prog.items[0][0]
        res['tag_intro'] = int(c0 is not None and c1 is not None and c0.root % 12 == c1.root % 12
                               and tuple(c0.intervals) == tuple(c1.intervals))
    return res


FRAME_SECTIONS = ('intro', 'tag', 'end', 'coda', 'inter')
"""A piano arrangement's frame sections (breath / piano_tells measure the others: the body)."""


def phrase_rests(song) -> float:
    """Share of the 4-bar phrase ends (counted from every body section's start; a waltz: 8 bars) where the right hand
    breathes: a beat or more between its last onset before the phrase boundary (within two bars) and its first after
    it - the singer's breath at every phrase end (letters-to-the-morning: every one)."""
    view = NoteView.of(song)
    m = view.m
    ons = sorted({round(n[0], 3) for n in view.rh})
    span = (8 if abs(m - 3) < 1e-6 else 4) * m
    hit = tot = 0
    for sec in view.sections:
        if sec.name in FRAME_SECTIONS:
            continue
        k = sec.start + span
        while k <= sec.end + 1e-6:
            before = [t for t in ons if k - 2 * m <= t < k - 1e-6]
            if before:
                tot += 1
                nxt = next((t for t in ons if t >= k - 1e-6), k + 2 * m)
                hit += nxt - before[-1] >= 1.0 - 1e-6
            k += span
    return round(hit / max(1, tot), 2)


def lh_variety(song) -> dict:
    """The left hand's figures per section (perform records song.endless_lh: the section's main figure / style):
    distinct (how many different ones), changes (between consecutive sections), all_figures (distinct figures in
    the whole piece, song.endless_figures)."""
    lh = getattr(song, 'endless_lh', None) or {}
    vals = [v for v in lh.values() if v]
    figs = getattr(song, 'endless_figures', None) or {}
    return {'distinct': len(set(vals)), 'changes': sum(1 for a, b in zip(vals, vals[1:]) if a != b),
            'all_figures': len({f for v in figs.values() for f in v}) if figs else len(set(vals)), 'plan': lh}


def piano_tells(song, tune=None, *, breath_metrics=None) -> dict:
    """The tells of a through-composed piano piece (perform.build_piano; what made generated tunes sound generated,
    songs/_blind/ROUNDS.md, plus the user's 'breathe' / 'a moving player'):
      hook        statements of the hook's shape in the performed right hand's top line (hook_matches, rubato
                  tolerant) and in how many body sections
      phrase_rests  share of phrase ends with a breath (phrase_rests)
      lh          left-hand figure variety (lh_variety)
      climax_x / climax_single  where the piece's highest right-hand note in its body (not the intro / coda / tag)
                  sits (0..1 of the music before the final chord) and whether it is struck once; peak_x: the loudest 4-bar window's centre (0..1)
      quiet1 / att_cv4 / rest_bar / long_share  the breath measures (breath)
      dyn_range   the note-energy spread per 2-bar window (dB, 10-95 %)"""
    view = NoteView.of(song)
    song = view.song
    m, rh, lh = view.m, view.rh, view.lh
    end0 = view.secs['end'].start if 'end' in view.secs else max(n[0] for n in rh)
    body = [x for x in view.sections if x.name not in FRAME_SECTIONS]
    out: dict = {}
    if tune is not None and len(tune.motif) >= 3:
        line = top_line([n for n in rh if n[0] < end0], tol=0.08)
        hits = hook_matches(line, sorted(tune.motif), scales=(1.0,), share=0.8, contour=0.75, tol=0.2)
        out['hook'] = len(hits)
        out['hook_sections'] = len({x.name for t, _ in hits for x in body if x.start - 0.5 <= t < x.end})
    out['phrase_rests'] = phrase_rests(view)
    out['lh'] = lh_variety(song)
    before = [n for n in rh if n[0] < end0 - 0.25]     # (the final chord's roll may start a hair before 'end')
    # (the climax is the body's: a high bell figure in the intro - letters-to-the-morning's G#6 - is not it)
    before = [n for n in before if any(x.start - 1e-6 <= n[0] < x.end - 1e-6 for x in body)] or before
    top = max(n[2] for n in before)
    tops = [n for n in before if n[2] == top]
    out['climax_x'] = round(tops[0][0] / max(1e-9, end0), 2)
    out['climax_single'] = len({round(n[0], 1) for n in tops}) == 1
    out['dyn_range'], out['peak_x'] = view.dynamics(0.0, end0)
    b = breath(view) if breath_metrics is None else breath_metrics
    out.update({k: b[k] for k in ('quiet1', 'att_cv4', 'rest_bar', 'long_share', 'lh_still', 'ph_vel')})
    return out


def newage_tells(song) -> dict:
    """The new-age blind rounds' tells (songs/_blind/ROUNDS.md "New-age"), measured on a performance whose chord
    timeline is song.endless_timeline [(beat, beats, chord symbol)] (perform.build_piano; a written piece sets it from
    its chart) - without one the chord measures are left out:
      rep_pitch     share of the right hand's top-line steps (inside a phrase: under 2 beats apart) that repeat the
                    pitch (round N0: repeated-note pickups, one-pitch codas)
      block_copy / climax_copy  how much of a body section repeats an earlier one bar for bar (the same top-line
                    pitches over the same chords; the max over the earlier sections), the mean over the body
                    sections after the first / for the climax section (round N0: the climax = B1 louder, A4 = A2)
      climax_chart  share of the climax's bars on the same chords as an earlier body section's same bar (the max
                    over the sections; round r3: the climax on A1's chart cell for cell)
      final_jump    semitones from the last melody note to the final chord's top (round N0: a top two octaves over
                    the line); final_top: 1 when that final chord holds the piece's highest note
      frame_pitches distinct right-hand pitches in the intro / interlude / coda before the final chord (round N0:
                    two- or three-note scraps)
      chords_n / chord_rep4  distinct chord symbols, and the share of 4-chord windows heard before (the same
                    loop everywhere)
      ret_tonic     1 when the last body section before the coda closes on the tonic (the references end their
                    last return deceptively)
      a1_range      the first body section's top-line range (semitones)
      a1_copy       share of the later body bars (3+ onsets) whose top line is the first body section's same bar at
                    any transposition (round r2: the climax / A4 = A1 an octave up note for note)
      climax_lift   the climax section's mean top-line pitch over the first body section's (round r1: the generated
                    climax +5-7 semitones, the references +9-14)
      peak_holes    bars without a right-hand onset in the climax and the section before it (round r1: rests at
                    the peak)
      off_chord32   top-line notes outside the chord's scale / tones / tensions per 32 body bars
      long_holds    top-line notes held 4+ beats before the final chord (round r1: 4.5-7 beat holds)
      ph_vspread    the top line's velocity spread (p90 - p10) inside a 4-bar phrase of a body section, the mean
                    (round r3: 6.5-7 dB within a phrase, the references 8.7-9.6)
      vel_jump12    share of the bar-to-bar steps inside a body section whose mean top-line velocity moves 12+
                    (round r4: the chorus jumping v64 -> v111 in two bars, peaks dropped onto notes)"""
    view = NoteView.of(song)
    song = view.song
    m = view.m
    out: dict = {}
    line = top_line(view.rh, tol=0.08)
    steps = [(a, b) for a, b in zip(line, line[1:]) if b[0] - a[0] < 2.0]
    out['rep_pitch'] = round(sum(a[2] == b[2] for a, b in steps) / max(1, len(steps)), 3)
    # the final chord: the last right-hand onset group
    cl = view.cl
    if len(cl) >= 2:
        last_t = cl[-1][0]
        prev = [n for n in line if n[0] < last_t - 0.25]
        out['final_jump'] = cl[-1][1][2] - prev[-1][2] if prev else 0
        out['final_top'] = int(cl[-1][1][2] >= max(n[2] for n in view.rh))
    else:
        last_t = float('inf')
    frames = [x for x in view.sections if x.name in FRAME_SECTIONS and x.name != 'end']
    out['frame_pitches'] = len({n[2] for n in line if n[0] < last_t - 0.25
                                and any(x.start - 1e-6 <= n[0] < x.end - 1e-6 for x in frames)})
    tl = getattr(song, 'endless_timeline', None)
    if not tl:
        return out
    tl = sorted(tl)

    def chords_in(a, z):
        return tuple(sym for t, b, sym in tl if t < z - 1e-6 and t + b > a + 1e-6)

    def sig(a):                                          # one bar: its top-line pitches + its chords
        return tuple(n[2] for n in line if a - 0.25 <= n[0] < a + m - 0.25), chords_in(a, a + m)
    body = [x for x in view.sections if x.name not in FRAME_SECTIONS]
    bars = {x.name: [sig(x.start + k * m) for k in range(int(round((x.end - x.start) / m)))] for x in body}
    copies = {}
    for i, x in enumerate(body):
        best = 0.0
        for y in body[:i]:
            n = min(len(bars[x.name]), len(bars[y.name]))
            same = sum(1 for k in range(n) if bars[x.name][k] == bars[y.name][k] and bars[x.name][k][0])
            best = max(best, same / max(1, len(bars[x.name])))
        copies[x.name] = best
    later = [copies[x.name] for x in body[1:]]
    out['block_copy'] = round(sum(later) / max(1, len(later)), 3)
    peak = 'climax' if 'climax' in copies else max(body, key=lambda x: max(
        [n[2] for n in line if x.start <= n[0] < x.end] or [0])).name
    out['climax_copy'] = round(copies.get(peak, 0.0), 3)
    pk_i = next((i for i, x in enumerate(body) if x.name == peak), 0)
    chart = 0.0                                          # round r3: the climax on an earlier section's chart
    for y in body[:pk_i]:
        n = min(len(bars[peak]), len(bars[y.name]))
        chart = max(chart, sum(bars[peak][k][1] == bars[y.name][k][1] for k in range(n)) / max(1, len(bars[peak])))
    out['climax_chart'] = round(chart, 3)
    seq = [sym for _, _, sym in tl]
    seq = [s for i, s in enumerate(seq) if i == 0 or s != seq[i - 1]]
    out['chords_n'] = len(set(seq))
    wins = [tuple(seq[i:i + 4]) for i in range(len(seq) - 3)]
    out['chord_rep4'] = round(sum(w in wins[:i] for i, w in enumerate(wins)) / max(1, len(wins)), 3)
    # the last return: the last body section before the frame sections at the end
    ret = body[-1] if body else None
    if ret is not None:
        ch = chords_in(ret.end - 1.0, ret.end)
        k = Key(song.key.name if hasattr(song.key, 'name') else str(song.key))
        c = chord(ch[-1]) if ch else None
        out['ret_tonic'] = int(c is not None and c.root % 12 == k.tonic % 12 and (c.bass is None or
                                                                                  c.bass == c.root % 12))
    # round r1: the climax barely above the theme, holes in the build / climax, off-chord neighbours, long holds
    first = body[0] if body else None
    pk = next((x for x in body if x.name == peak), None)

    def mean_top(x):
        ps = [n[2] for n in line if x.start - 1e-6 <= n[0] < x.end - 1e-6]
        return sum(ps) / len(ps) if ps else None
    if first is not None:
        ps = [n[2] for n in line if first.start - 1e-6 <= n[0] < first.end - 1e-6]
        out['a1_range'] = max(ps) - min(ps) if ps else 0

        def shape(a):                                    # one bar's top line at any transposition: its steps (the
            ns = [n for n in line if a - 0.25 <= n[0] < a + m - 0.25]       # onsets are played - rubato)
            return tuple(b[2] - a_[2] for a_, b in zip(ns, ns[1:]))
        a1 = [shape(first.start + k * m) for k in range(int(round((first.end - first.start) / m)))]
        hits = tot = 0
        for x in body[1:]:
            for k in range(int(round((x.end - x.start) / m))):
                sh = shape(x.start + k * m)
                if len(sh) >= 2:
                    tot += 1
                    hits += k < len(a1) and sh == a1[k]
        out['a1_copy'] = round(hits / max(1, tot), 3)
    if first is not None and pk is not None and pk is not first and mean_top(first) and mean_top(pk):
        out['climax_lift'] = round(mean_top(pk) - mean_top(first), 1)
    i_pk = body.index(pk) if pk is not None else -1
    holes = 0
    for x in body[max(0, i_pk - 1):i_pk + 1] if i_pk >= 0 else []:
        for k_ in range(int(round((x.end - x.start) / m))):
            a = x.start + k_ * m
            holes += not any(a - 0.25 <= n[0] < a + m - 0.25 for n in line)
    out['peak_holes'] = holes
    from ..theory import chord_scale as _cscale

    def chord_at(t):
        for t0, b, sym in tl:
            if t0 - 1e-6 <= t < t0 + b - 1e-6:
                return chord(sym)
        return None
    off = 0
    body_beats = sum(x.end - x.start for x in body)
    for n in line:
        if n[1] < 0.12 or not any(x.start - 1e-6 <= n[0] < x.end - 1e-6 for x in body):
            continue
        c = chord_at(n[0] + 0.06)
        if c is None:
            continue
        own = set(_cscale(c)) | {i % 12 for i in c.intervals} | set(available_tensions(c))
        off += (n[2] - c.root) % 12 not in own
    out['off_chord32'] = round(off * 32 * m / max(1.0, body_beats), 2)
    out['long_holds'] = sum(1 for n in line if n[1] >= 4.0 and n[0] < last_t - 0.25)
    spreads = []                                         # round r3: one dynamic per phrase
    for x in body:
        for k_ in range(0, int(round((x.end - x.start) / m)) - 3, 4):
            vs = sorted(n[3] for n in line if x.start + k_ * m - 1e-6 <= n[0] < x.start + (k_ + 4) * m - 1e-6)
            if len(vs) >= 5:
                spreads.append(vs[int(0.9 * (len(vs) - 1))] - vs[int(0.1 * (len(vs) - 1))])
    if spreads:
        out['ph_vspread'] = round(sum(spreads) / len(spreads), 1)
    jumps = []                                           # round r4: dynamic peaks dropped onto single notes
    for x in body:
        row = []
        for k_ in range(int(round((x.end - x.start) / m))):
            a = x.start + k_ * m
            vs = [n[3] for n in line if a - 0.25 <= n[0] < a + m - 0.25]
            row.append(sum(vs) / len(vs) if vs else None)
        jumps += [abs(b - a) >= 12 for a, b in zip(row, row[1:]) if a is not None and b is not None]
    if jumps:
        out['vel_jump12'] = round(sum(jumps) / len(jumps), 3)
    return out


BLOOM_RUN = {'ioi': 0.6, 'step': (1, 9), 'span': 24, 'group': 0.06}
"""bloom_tells' continuous figure: onsets at most `ioi` beats apart (8ths or faster), each step `step` semitones in
one direction, spanning `span`+ semitones (two octaves) with notes of both hands; onsets within `group` beats are
one moment (the hands' asynchrony)."""


def bloom_tells(song) -> dict:
    """The bloom and the flow (HUMAN_FEEDBACK 2026-10-15: "no blossoming where the tempo gets faster and more
    happens; they ripple along; bass and lead always very clearly separated; nothing played across the whole
    keyboard like Für Elise"), measured on a performance's notes and its tempo map:
      tempo_push    the tempo the fastest body section holds (its beats' median: past its ritardando and fermata)
                    over the first body section's: a bloom pushing forward > 1, a piece that never presses ~1
      climax_tempo  the mean tempo of the section holding the body's top note over the first body section's (the
                    measured new-age pieces: 0.89-0.93 - every climax slower than the theme)
      rh_peak_den   right-hand onsets per beat in the body's densest 4-bar window (a melody that never moves
                    faster than 8ths stays under ~1.7)
      flow32        continuous figures per 32 body bars (BLOOM_RUN: one direction, 8ths or faster, two octaves+)
                    whose notes come from both hands - a figure passing between the hands (Für Elise's A section)
      hand_meet     share of the body bars where the left hand's top reaches the right hand's lowest note (within
                    a whole step, or above it): the hands share a register instead of a fixed split"""
    import statistics as st
    view = NoteView.of(song)
    song, m = view.song, view.m
    body = [x for x in view.sections if x.name not in FRAME_SECTIONS]
    out: dict = {}
    if not body:
        return out
    try:
        tm = song.tempo_map()
    except Exception:                                   # (a song without notes placed: no tempo measure)
        tm = None
    if tm is not None:
        def bpm_over(a, b):
            return 60.0 * (b - a) / max(1e-9, tm.seconds_at(b) - tm.seconds_at(a))

        def held(x):                                    # (the tempo a section holds: its beats' median)
            return st.median(bpm_over(x.start + k, x.start + k + 1) for k in range(max(1, int(x.end - x.start))))
        out['tempo_push'] = round(max(held(x) for x in body) / held(body[0]), 3)
        top = max(view.rh, key=lambda n: (n[2], -n[0]), default=None)
        sec = next((x for x in body if top and x.start - 1e-6 <= top[0] < x.end - 1e-6), None)
        if sec is not None:
            out['climax_tempo'] = round(bpm_over(sec.start, sec.end) / bpm_over(body[0].start, body[0].end), 3)
    dens = []
    for x in body:
        nb = int(round((x.end - x.start) / m))
        for k in range(max(1, nb - 3)):
            a, z = x.start + k * m, x.start + min(nb, k + 4) * m
            dens.append(len(view.onsets(a, z)) / max(1e-9, z - a))
    out['rh_peak_den'] = round(max(dens), 2)
    # the continuous figures: a longest-path walk over the onset moments of both hands
    R = BLOOM_RUN
    notes = sorted([(n[0], n[2], 0) for n in view.rh] + [(n[0], n[2], 1) for n in view.lh])
    notes = [n for n in notes if any(x.start - 1e-6 <= n[0] < x.end - 1e-6 for x in body)]
    moments: list = []
    for n in notes:
        if moments and n[0] - moments[-1][0][0] < R['group']:
            moments[-1].append(n)
        else:
            moments.append([n])
    runs = []
    best: dict = {}                                     # (moment, index, direction) -> (start t, start pitch, hands)
    for i, mo in enumerate(moments):
        for j, n in enumerate(mo):
            for d in (1, -1):
                cand = [(n[0], n[1], 1 << n[2])]
                for i0 in (i - 1, i - 2):
                    if i0 < 0 or n[0] - moments[i0][0][0] > R['ioi']:
                        continue
                    for j0, p in enumerate(moments[i0]):
                        step = (n[1] - p[1]) * d
                        if R['step'][0] <= step <= R['step'][1] and (i0, j0, d) in best:
                            t0, p0, h = best[(i0, j0, d)]
                            cand.append((t0, p0, h | (1 << n[2])))
                t0, p0, h = max(cand, key=lambda c: (abs(n[1] - c[1]), -c[0]))
                best[(i, j, d)] = (t0, p0, h)
                if abs(n[1] - p0) >= R['span'] and h == 3:
                    runs.append((t0, n[0]))
    merged = []
    for a, z in sorted(runs):
        if merged and a <= merged[-1][1] + 1e-6:
            merged[-1][1] = max(merged[-1][1], z)
        else:
            merged.append([a, z])
    bars = sum(int(round((x.end - x.start) / m)) for x in body)
    out['flow32'] = round(len(merged) * 32 / max(1, bars), 2)
    meet = tot = 0
    for x in body:
        for k in range(int(round((x.end - x.start) / m))):
            a, z = x.start + k * m - 0.05, x.start + (k + 1) * m - 0.05
            r = [n[2] for n in view.rh if a <= n[0] < z]
            lh = [n[2] for n in view.lh if a <= n[0] < z]
            if r and lh:
                tot += 1
                meet += max(lh) >= min(r) - 2
    out['hand_meet'] = round(meet / max(1, tot), 2)
    return out


def breath(song) -> dict:
    """Does the playing BREATHE (the user, r6: "sounds like an endless monotone line of notes")? Measured on the right
    hand's onsets (a rolled chord is one attack) and the left hand's attacks over the head, the solo and the head out:
      att_bar       right-hand attacks per bar, per section {'head', 'solo', 'out'}; att_sd: their spread per bar;
                    att_cv4: the coefficient of variation of the attacks per 4-bar window over the three (sparse
                    statements, dense builds: high; one density everywhere: low)
      quiet1        share of the time in which the right hand has struck nothing new for a beat or more (a line of
                    quarters has none; room between the phrases); quiet1_sec: per section; quiet1_both: neither hand
      rest_half     right-hand rests of half a bar or more (no new onset; the last note may ring) per 8 bars;
                    rest_bar: rests of a whole bar or more per 32 bars; rest_max: the longest (beats)
      ph_on         right-hand onsets per phrase (phrases split where two beats or more pass without an onset);
                    ph_beats: their length
      long_share    share of the right hand's attacks held a beat and a half or longer (sustained notes)
      lh_bar        left-hand attacks per bar; lh_still: share of the left hand's bars with one attack or none
                    (it rests or lets the chord ring)
      orn32         ornament notes (right-hand onsets less than a 16th before the next: grace notes, turns, trills,
                    sextuplet runs) per 32 bars
      ph_reg / ph_vel / ph_den  the mean change from one phrase to the next of its mean pitch (semitones), mean
                    velocity and onsets per beat (contrast between phrases)"""
    import statistics as st
    view = NoteView.of(song)
    m = view.m
    body = [view.secs[k] for k in ('head', 'solo', 'out') if k in view.secs] or \
        [x for x in view.sections if x.name not in FRAME_SECTIONS]      # (a piano arrangement: its sections)
    cl, lcl = view.cl, view.lcl
    res: dict = {'att_bar': {}, 'att_sd': {}}
    gaps_in = total = rest_max = 0.0
    q_sec: dict = {}
    rests = rest_bar = orn = n_bars = 0
    phrases, wins, lh_counts = [], [], []
    for sec in body:
        a0, z0 = sec.start, sec.end
        nb = max(1, int(round((z0 - a0) / m)))
        n_bars += nb
        on = view.onsets(a0, z0)
        per = [sum(1 for c in on if a0 + k * m - 1e-6 <= c[0] < a0 + (k + 1) * m - 1e-6) for k in range(nb)]
        res['att_bar'][sec.name] = round(sum(per) / nb, 2)
        res['att_sd'][sec.name] = round(st.pstdev(per), 2) if nb > 1 else 0.0
        wins += [sum(per[k:k + 4]) for k in range(0, nb - 3, 4)]
        lh_counts += [sum(1 for c in lcl if a0 + k * m - 1e-6 <= c[0] < a0 + (k + 1) * m - 1e-6) for k in range(nb)]
        prev = None
        for t in [c[0] for c in on] + [z0]:
            if prev is not None:
                g = t - prev
                gaps_in += max(0.0, g - 1.0)
                q_sec[sec.name] = q_sec.get(sec.name, 0.0) + max(0.0, g - 1.0) / (z0 - a0)
                if t < z0:
                    rests += g >= m / 2 - 1e-6
                    rest_bar += g >= m - 1e-6
                    rest_max = max(rest_max, g)
            prev = t
        total += z0 - a0
        cur = []
        for j, c in enumerate(on):
            if cur and c[0] - cur[-1][0] >= 2.0 - 1e-6:
                phrases.append(cur)
                cur = []
            cur.append(c)
            if j + 1 < len(on) and on[j + 1][0] - c[0] < 0.2 - 1e-6:
                orn += 1
        if cur:
            phrases.append(cur)
    res['att_cv4'] = round(st.pstdev(wins) / max(1e-9, st.mean(wins)), 2) if len(wins) > 1 else 0.0
    res['quiet1'] = round(gaps_in / max(1e-9, total), 3)
    res['quiet1_sec'] = {k: round(v, 3) for k, v in q_sec.items()}
    both = sorted({round(c[0], 3) for c in cl + lcl})
    q = 0.0
    for sec in body:
        ts = [sec.start] + [t for t in both if sec.start - 1e-6 <= t < sec.end - 1e-6] + [sec.end]
        q += sum(max(0.0, b - a - 1.0) for a, b in zip(ts, ts[1:]))
    res['quiet1_both'] = round(q / max(1e-9, total), 3)
    res['rest_half'] = round(rests * 8 / max(1, n_bars), 2)
    res['rest_bar'] = round(rest_bar * 32 / max(1, n_bars), 2)
    res['rest_max'] = round(rest_max, 2)
    res['ph_on'] = round(st.mean(len(p) for p in phrases), 1) if phrases else 0.0
    res['ph_beats'] = round(st.mean(p[-1][0] - p[0][0] + 0.5 for p in phrases), 1) if phrases else 0.0
    alln = [c for c in cl if any(s.start - 1e-6 <= c[0] < s.end - 1e-6 for s in body)]
    res['long_share'] = round(sum(c[1][1] >= 1.5 for c in alln) / max(1, len(alln)), 3)
    res['lh_bar'] = round(sum(lh_counts) / max(1, len(lh_counts)), 2)
    res['lh_still'] = round(sum(x <= 1 for x in lh_counts) / max(1, len(lh_counts)), 2)
    res['orn32'] = round(orn * 32 / max(1, n_bars), 1)
    big = [p for p in phrases if len(p) >= 2]
    pm = [st.mean(c[1][2] for c in p) for p in big]
    pv = [st.mean(c[1][3] for c in p) for p in big]
    pd = [len(p) / max(0.5, p[-1][0] - p[0][0] + 0.5) for p in big]
    for k, xs in (('ph_reg', pm), ('ph_vel', pv), ('ph_den', pd)):
        res[k] = round(st.mean(abs(b - a) for a, b in zip(xs, xs[1:])), 2) if len(xs) > 1 else 0.0
    return res


# ------------------------------------------------------------------------------------------------ the score

HANDS = (('piano', 'comp'), ('rh', 'lh'), ('melody', 'accomp'))
"""The (right hand, left hand) track names score() looks for (the endless / pro songs, the etudes)."""


def score_style(song=None, tune=None, genre: Genre | None = None) -> str:
    """The score table's style: the genre's (or the tune's genre's) style; else 'jazz' for a song with a solo
    section, 'new-age' for any other piano piece."""
    from .genres import get
    if genre is None and tune is not None and getattr(tune, 'genre', None):
        genre = get(tune.genre)
    if genre is not None:
        return genre.style
    if song is not None and getattr(song, 'organ_voices', None):     # (played by the organist)
        return 'organ'
    if song is not None and getattr(song, 'orch_scores', None):      # (an orchestra through orch.Score)
        return 'orchestra'
    return 'jazz' if song is not None and 'solo' in {s.name for s in song.sections} else 'new-age'


def score_metrics(song, tune=None, style: str = 'jazz') -> dict:
    """Every notes-level measure the score can weigh, flat {name: number} (no audio): for 'jazz' tells() (rounds 1-6)
    + breath() + phrase_rests(), for the through-composed styles piano_tells() + breath(); for both the body's
    coupling (humanize.body_stats 'heard': faster where louder) and - with a tune - the lead sheet's own checks:
    mel_issues (melody_issues per part: clashes on strong / long notes, notes held into a chord they do not fit,
    leaps over an octave, unrecovered leaps), mel_style (_style_issues: a rhythm cell over-used, a pitch circled) and
    shape()'s arc: arc_pitch_r / arc_dens_r (the 2-bar phrases' pitch / notes against the plan's level), hook_head /
    hook_tag (the hook's statements in the head / the tag)."""
    from ..humanize import body_stats
    if style == 'organ':                                # (the organ: its own tells - endless/organ.py)
        from .organ import organ_metrics
        return organ_metrics(song, tune)
    if style == 'orchestra':                            # (the orchestra: the melodic layer on its reduction + the
        from .orchestra import orchestra_metrics        # orchestration - endless/orchestra.py)
        return orchestra_metrics(song, tune)
    rh_name, lh_name = next(((a, b) for a, b in HANDS if a in song.tracks), (None, None))
    if rh_name is None:
        raise ComposeError(f"score: no right-hand track ({' / '.join(a for a, _ in HANDS)}) in the song")
    view = NoteView(song, melody=rh_name, accompaniment=(lh_name,))
    b = breath(view)
    if style == 'jazz':
        raw = dict(tells(view, tune))
        raw.update({k: b[k] for k in ('quiet1', 'att_cv4', 'orn32', 'ph_vel', 'ph_den', 'long_share')})
        raw['phrase_rests'] = phrase_rests(view)
    else:
        raw = dict(piano_tells(view, tune, breath_metrics=b))
        lh = raw.pop('lh', None) or {}
        if getattr(song, 'endless_lh', None):      # (perform records the figures; a hand-written song: none)
            raw['lh_distinct'], raw['lh_figures'] = lh.get('distinct'), lh.get('all_figures')
        raw.update({k: b[k] for k in ('orn32', 'ph_reg', 'ph_den', 'rest_half', 'rest_max')})
        raw['att_bar'] = round(sum(b['att_bar'].values()) / max(1, len(b['att_bar'])), 2)
        if style == 'new-age':                          # the new-age blind rounds' tells (the other styles: as before)
            raw.update(newage_tells(view))
            raw.update(bloom_tells(view))                # (the bloom: HUMAN_FEEDBACK 2026-10-15)
    try:
        raw['body_heard'] = body_stats(deepcopy(song), rh_name)['coupling'].get('heard')
    except Exception:                                   # (a track without a played body: no body measure)
        raw['body_heard'] = None
    if tune is not None and getattr(tune, 'melody', None):
        kp = set(Key(tune.key).pcs)
        mi = ms = 0
        for p in tune.parts:
            notes = tune.melody[p]
            if notes:
                harm = Harm(tune.changes[p], kp)
                mi += len(melody_issues(notes, harm, 0, 127, meter=tune.meter))
                ms += len(_style_issues(notes, tune.meter, harm.length))
        raw['mel_issues'], raw['mel_style'] = mi, ms
        try:                                            # the lead sheet's long-range shape (shape(): the arc)
            sh = shape(tune)
            raw['arc_pitch_r'] = sh['arc']['phrase_pitch_r']
            raw['arc_dens_r'] = sh['arc']['phrase_density_r']
            raw['hook_head'] = sh['hook']['head']
            raw['hook_tag'] = sh['hook']['tag']
        except (KeyError, ValueError, ZeroDivisionError, ComposeError):
            pass
    return {k: int(v) if isinstance(v, bool) else v for k, v in raw.items()
            if isinstance(v, (int, float)) and not (isinstance(v, float) and v != v)}


def score(song, tune=None, genre: Genre | None = None, metrics: dict | None = None, table: dict | None = None,
          style: str | None = None) -> dict:
    """ONE quality number 0-100 for a piano performance from the notes alone (no audio): score_metrics() weighed by
    the style's table genres.SCORES[style] {metric: (lo, hi, weight, hard[, unit])} - the target range measured on
    the composed references (songs/_blind/ROUNDS.md; provisional where the table says so). A metric inside its range
    scores 1, outside 1 / (1 + d^2) with d the distance in units (the range's width unless the entry gives one); the
    score is the weighted mean x 100; a 'hard' metric outside its range scales it into 0 .. SCORE_HARD_CAP x its
    sub-score (the worst one: an octave wrap, a verbatim repeat over another chord, a silent cadence bar ... can never
    be outweighed - and the capped tunes keep their order).
    metrics: score_metrics() already measured (song may then be None); table: another {metric: spec} table (a
    learned one, a subset); style: the table's style (default: score_style()). Returns {'score', 'style', 'mean'
    (before the cap), 'hard' (the
    capping metrics), 'parts': {metric: (value, sub, weight)}, 'worst': the 5 that cost the most points
    [{'metric', 'value', 'lo', 'hi', 'sub', 'lost'}], 'missing': table metrics not measured}.
    What it cannot see: the audio (the mix, the piano's sound, clicks - the render gate's job) and taste (whether
    the tune is memorable); it rewards closeness to OUR references - the user's ears and the blind judges stay the
    final check."""
    from .genres import SCORE_HARD_CAP, SCORES
    style = style or score_style(song, tune, genre)
    table = table if table is not None else SCORES[style]
    m = metrics if metrics is not None else score_metrics(song, tune, style)
    parts, lost, missing, hard = {}, {}, [], []
    num = den = 0.0
    cap = 100.0
    for k, spec in table.items():
        lo, hi, w, is_hard = spec[:4]
        v = m.get(k)
        if v is None:
            missing.append(k)
            continue
        unit = spec[4] if len(spec) > 4 else ((hi - lo) or 1.0)
        d = max(lo - v, v - hi, 0.0) / unit
        sub = 1.0 / (1.0 + d * d)
        parts[k] = (v, round(sub, 3), w)
        num += w * sub
        den += w
        lost[k] = w * (1.0 - sub)
        if is_hard and sub < 1.0:
            hard.append(k)
            cap = min(cap, SCORE_HARD_CAP * sub)
    mean = 100.0 * num / den if den else 0.0
    worst = sorted((k for k in lost if lost[k] > 1e-9), key=lambda k: (k not in hard, -lost[k]))[:5]
    return {'score': round(mean * cap / 100.0, 1), 'style': style, 'mean': round(mean, 1), 'hard': hard,
            'parts': parts, 'missing': missing,
            'worst': [{'metric': k, 'value': parts[k][0], 'lo': table[k][0], 'hi': table[k][1], 'sub': parts[k][1],
                       'lost': round(100.0 * lost[k] / den, 1)} for k in worst]}
