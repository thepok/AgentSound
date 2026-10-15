"""Endless ORCHESTRA: a composed tune (composer.compose with an orchestra genre's data) written into the polyphonic
SCORE of lines with functions (bandlib/orchestration.py: OrchScore), orchestrated by data tables (TEXTURES, RULES,
orch.ROLE_TRAITS + the band's ranges) and played by the orchestral player (orch.Score -> orch.perform, ensemble.py)
on the film_orchestra band - perform.build hands every plan['perform'] = 'orchestra' tune here.
docs/ORCHESTRA_ENDLESS.md has the architecture and the roadmap.

    python -m agentsound endless orchestra-film --count 3 --mood longing

The sections are the new-age pianist's plan (perform._piano_plan: the layout, the drawn bars / climax / returns /
keys - the same composer and arrangement draws), each a Block of the score; per block the orchestrator draws its
TEXTURE ({texture: weight} in the plan entry's 'orch' key) and the melody's role, then this composer writes the lines
the texture needs (lines_from_block): the melody, the harmony as voice-led real parts under it (voicing.voice), the
bass (organ_vocab.bass_line; walking where the plan says), a counter-melody (organ_vocab.counterline against the
melody and the bass, held where the melody moves, moving where it holds), an ostinato (figures 'pulse8' on two
inner voices), colour (harp arpeggios - figures 'broken' -, a timpani roll into the next block, timpani hits and a
cymbal at the climax, the choir's 'aah' on the harmony). The orchestrator assigns them (orchestrate), orch.Score plays
them with one dynamics map (the sections' marks + a hairpin per phrase), the tempo plan is the pianist's (section
tempi, ritardandi, fermatas, an inhale before the peak).

The piece's size ('chamber' | 'full', the mood's {size: weight}) sets the roles; the band is built with only the
roles the piece uses (one track per section of the orchestra). The decisions are the Arrangement record (kind
'orchestra'): the piano keys + piece 'size' + per section 'texture', 'lead', 'counter' (ORCH_DRAWN).
The song keeps s.orch_score (the OrchScore), s.orchestration (the parts) and s.orch_scores ([the orch.Score]) for
the score (orchestra_metrics)."""
from __future__ import annotations

import random

from .. import bands, voicing
from .. import organ_vocab as ov
from ..bandlib import orchestra as orch
from ..bandlib import orchestration as orc
from ..song import Song
from ..theory import ComposeError, Key, chord, note

__all__ = ['band', 'build_orchestra', 'lines_from_block', 'orchestra_metrics', 'validate_plan', 'SECTION_KEYS', 'HARMONY_SETS',
           'COUNTER', 'RECORDED']

_EPS = 1e-6

SECTION_KEYS = {'orch'}
"""The keys an orchestra plan section adds to a 'piano' plan section: orch {texture: weight} (TEXTURES)."""
RECORDED = ('texture', 'lead', 'counter')
"""The orchestrator's draws kept in the Arrangement record (the others - colour roles, doublings - follow the seed)."""

HARMONY_SETS = {
    # the harmony's real parts under the melody (voicing.voice ranges (lo, hi, centre)): close in the treble
    2: {'h1': (55, 79, 67), 'h2': (48, 72, 60)},
    3: {'h1': (55, 81, 69), 'h2': (50, 76, 63), 'h3': (48, 69, 57)},       # (no voice under C3: the violas' /
    4: {'h1': (57, 81, 70), 'h2': (52, 76, 65), 'h3': (50, 72, 61), 'h4': (48, 67, 55)},  # horns' floor)
}
HARMONY_HIGH = {
    # the harmony OVER a tenor melody (a cello / horn / bassoon / viola lead: the high string pad of 'cello_theme' -
    # blind round r1: the violins held low pedal notes under the violas' tune)
    2: {'h1': (64, 84, 74), 'h2': (57, 79, 67)},
    3: {'h1': (64, 86, 76), 'h2': (59, 81, 70), 'h3': (55, 76, 64)},
    4: {'h1': (67, 88, 77), 'h2': (62, 84, 72), 'h3': (57, 79, 67), 'h4': (55, 74, 62)},
}
TENOR_LEADS = ('cellos', 'horns', 'bassoons', 'violas', 'trombones')
OSTINATO_SET = {'o1': (57, 76, 67), 'o2': (50, 69, 60)}
"""The ostinato's two inner voices (repeated 8ths on them: figures 'pulse8')."""
BASS_RANGE = ('C2', 'D3')
COUNTER = {'lo': 'G3', 'hi': 'E5', 'gap': 2, 'motif': 'quarter', 'rest': 0.1, 'hold': 0.3, 'max_hold': 4.0}
"""The counter-melody: its register (under the melody by `gap` at least), counterline's motif / budgets, and a held
note's longest span while the melody moves (beats)."""
HARP = {'low': 'G2', 'top': 'G5', 'figures': {('broken', 0.5): 1.0, ('broken', 1.0): 0.5, ('alberti', 0.5): 0.5}}
"""The harp's band and its figures {(chord figure, step): weight}, one drawn per block (blind round r1: one
up-down 8th pattern in every bar of every piece)."""
OSTINATO = {'rock': 1.0, 'arp': 0.8, 'pulse': 0.3}
"""The string ostinato's figure, drawn per block: 'rock' (the upper part rocks between the two chord tones in 8ths,
the lower part on the beats / syncopated), 'arp' (the upper part arpeggiates the two tones and the octave in 8ths,
the lower part holds), 'pulse' (both parts repeat their note in 8ths) - blind rounds r1 / r2: one pitch hammered per
bar, then one rocking cell in every generated piece."""
"""The harp's arpeggio band (figures 'broken')."""
END_HOLD = 3.0
"""The final chord's fermata (beats held)."""


def validate_plan(genre, bad) -> None:
    """An 'orchestra' plan: the piano plan's sections (validated as a piano plan) each with an 'orch' {texture:
    weight} of known textures; plan['sizes'] {size: roles of the band}; every mood's 'size' {size: weight}."""
    sizes = genre.plan.get('sizes')
    table = orch.role_table(genre.band['preset'])
    if not isinstance(sizes, dict) or not sizes:
        bad("an 'orchestra' plan needs plan['sizes'] {size: (roles of the band)}")
    for name, roles in sizes.items():
        miss = set(roles) - set(table)
        if miss:
            bad(f"plan sizes[{name!r}]: {sorted(miss)} are no {genre.band['preset']} roles")
    for m, d in genre.moods.items():
        sw = d.get('size')
        if not isinstance(sw, dict) or not sw or set(sw) - set(sizes) or any(w < 0 for w in sw.values()):
            bad(f"mood {m!r}: size {{one of {', '.join(sizes)}: weight}}")
    for sd in genre.plan.get('sections') or ():
        w = sd.get('orch')
        if not isinstance(w, dict) or not w or any(t not in orc.TEXTURES or x <= 0 for t, x in w.items()):
            bad(f"plan section {sd.get('name')!r}: orch {{texture: weight > 0}} of {', '.join(orc.TEXTURES)}")
    if genre.band.get('style', 'film') not in ('film', 'romantic', 'classical', 'baroque'):
        bad("band['style']: the orchestral player's style (ensemble.STYLES)")


# ------------------------------------------------------------------------------------------------ the composer

def _key_name(home: str, moved) -> str:
    """A section's key: home, or the key a section moved into (perform._modulate's (semitones, tonic pc, pcs))."""
    if not moved:
        return home
    from .perform import _transpose_sym
    semis, t_pc, pcs = moved
    root = _transpose_sym(home.split()[0], semis, home) if semis else home.split()[0]
    return f"{root} {'major' if (t_pc + 4) % 12 in pcs else 'minor'}"


def _chart_abs(ch, a: float) -> list:
    out, t = [], a
    for sym, b in ch:
        out.append((t, b, sym))
        t += b
    return out


def _tie(notes) -> list:
    """Repeated pitches running on merged into held notes."""
    out = []
    for a, d, p in sorted(notes):
        if out and out[-1][2] == p and abs(out[-1][0] + out[-1][1] - a) < 1e-4:
            out[-1] = (out[-1][0], out[-1][1] + d, p)
        else:
            out.append((a, d, p))
    return out


def _harmony(chart, mel, n: int, key: str, ranges=None, above: bool = False) -> dict:
    """The chart's chords as n real parts under the melody (voicing.voice: smallest motion, no crossing, the
    melody's lowest note in each chord as a fixed top voice above them, RULES spacing) -> {voice: notes}; above=True
    (a tenor melody): the parts over it in HARMONY_HIGH, its notes avoided."""
    rng_ = dict(ranges or (HARMONY_HIGH if above else HARMONY_SETS)[n])
    vs = dict(rng_) if above else {'m': (36, 108, 76), **rng_}
    steps = []
    for a, b, sym in chart:
        under = [p for st, du, p in mel if st < a + b - _EPS and st + du > a + _EPS]
        st_ = {'chord': sym}
        if above:
            st_['active'] = tuple(rng_)
            if under:
                st_['avoid'] = tuple(under)
        elif under:
            st_['fixed'] = {'m': min(under)}
            st_['avoid'] = tuple(under)
        else:
            st_['active'] = tuple(rng_)
        steps.append(st_)
    try:
        got = voicing.voice(steps, voices=vs, key=key, spacing=orc.RULES['spacing'], bass_gap=19)
    except ComposeError:
        steps = [{'chord': s_['chord'], 'active': tuple(rng_)} for s_ in steps]
        got = voicing.voice(steps, voices=vs, key=key, spacing=orc.RULES['spacing'], bass_gap=19)
    out = {v: [] for v in rng_}
    for (a, b, _), v in zip(chart, got):
        for name in rng_:
            if v.get(name) is not None:
                out[name].append((a, b, v[name]))
    return {k: _tie(x) for k, x in out.items()}


def _bass(chart, key: str, walk: float, seed) -> list:
    """The bass line (organ_vocab.bass_line over one slot per chord: the chord's bass - a slash chord's - voice-led in
    BASS_RANGE; `walk` of the steps a 3rd apart get a passing 8th)."""
    slots = []
    for a, b, sym in chart:
        slots += ov.slots_from_chart([(a, b, sym)], key, rate=b)
    if not slots:
        return []
    return ov.bass_line(slots, key, lo=BASS_RANGE[0], hi=BASS_RANGE[1], walk=walk, octave_leaps=0.0, seed=seed)


def _counter(chart, mel, bass, key: str, meter: int, seed) -> list:
    """A counter-melody under the melody (organ_vocab.counterline against melody and bass, COUNTER's register and
    budgets), its rhythm complementing the melody's: a beat where the melody strikes holds the counter's note on
    (up to COUNTER max_hold), a beat where the melody holds or rests lets the counter move."""
    C = COUNTER
    if not mel:
        return []
    top = min(p for _, _, p in mel) - C['gap']
    hi = min(note(C['hi']), max(note(C['lo']) + 9, top))
    slots = []
    for a, b, sym in chart:
        slots += ov.slots_from_chart([(a, b, sym)], key, rate=1.0)
    if not slots:
        return []
    raw = ov.counterline([[(a, d, p) for a, d, p in mel], bass], slots, key, lo=C['lo'], hi=hi, motif=C['motif'],
                         rest=C['rest'], hold=C['hold'], above=mel, below=bass or None, meter=meter, seed=seed)
    ons = sorted(a for a, _, _ in mel)
    out = []
    for a, d, p in sorted(raw):
        busy = any(a - _EPS <= o < a + d - _EPS for o in ons)
        if out and busy and out[-1][0] + out[-1][1] >= a - 0.01 and out[-1][1] + d <= C['max_hold']:
            q = out[-1]
            out[-1] = (q[0], a + d - q[0], q[2])
        else:
            out.append((a, d, p))
    return _tie(out)


def _colour(fig: str, chart, harm: dict, key: str, b, meter: int, seed) -> list:
    """A colour line of a figure: 'arp' (harp arpeggios: figures 'broken' in HARP's band), 'roll_end' (a timpani roll
    over the block's last bar on the tonic / dominant), 'hits' (timpani on the chord changes that are tonic /
    dominant), 'crash' (a cymbal crash on the block's downbeat, a suspended-cymbal roll into it), 'aah' (the choir on
    the harmony's parts) -> [(notes, articulation)]."""
    from .. import figures
    if fig == 'arp':
        rows = [(bb, sym, None, None) for _, bb, sym in chart]
        if not rows:
            return []
        h = voicing.Harmony(rows, key=key, at=chart[0][0], beats_per_bar=meter)
        kind, step = _pick_w(HARP['figures'], random.Random(seed))
        if kind == 'alberti':
            c = figures.figure(h, 'alberti', octave=4, step=step, gap=step * 1.6)
        else:
            c = figures.figure(h, 'broken', low=HARP['low'], top=HARP['top'], seed=seed, step=step)
        seen, out = set(), []
        for n in c:                                   # (one string per pitch at a time: no doubled bass note)
            k = (round(n.start, 3), n.pitch)
            if k not in seen:
                seen.add(k)
                out.append((n.start + chart[0][0], n.dur, n.pitch))
        return [(out, 'sustain')]
    tun = orch.timpani_tuning(key)
    if fig == 'roll_end':
        z = b.end
        sym = next((sy for a, bb, sy in chart if a < z - _EPS and a + bb > z - meter + _EPS), None) \
            if chart else None
        c = chord(sym) if sym else None
        pcs = [(c.root + i) % 12 for i in c.intervals] if c else [Key(key).tonic]
        # the roll on a tuned drum that is a tone of the chord over the last bar (its root first) - none if no
        # drum fits (blind round r1: a Db roll under a C chord)
        p = next((tun[x] for x in pcs if x in tun), None)
        return [([(z - meter, meter, p)], 'roll')] if p is not None else []
    if fig == 'hits':
        out = []
        for a, bb, sym in chart:
            r = chord(sym).root % 12
            if r in tun:
                out.append((a, 1.0, tun[r]))
        return [(out, 'hit')] if out else []
    if fig == 'crash':
        k = orch.PERCUSSION_KEYS
        out = [(b.start, 4.0, k['crash'])]
        lead = 6.0
        if b.start >= lead:
            out.append((b.start - lead, lead, k['cymbal_roll']))
        return [(out, 'sustain')]
    if fig == 'aah':
        ns = [n for v in harm.values() for n in v]
        return [(ns, 'sustain')] if ns else []
    raise ComposeError(f"orchestra colour figure {fig!r} unknown")


def _pick_w(weights: dict, rng):
    ks = list(weights)
    return rng.choices(ks, weights=[weights[k] for k in ks])[0]


def _ostinato(o: dict, kind: str, rs) -> dict:
    """The string ostinato from its two held parts o1 / o2: 'pulse' (each part's note in 8ths) or 'rock' (o1's part
    rocks o1 - o2 in 8ths, o2's part on the beats or syncopated - drawn)."""
    from .. import figures
    if kind == 'pulse' or not o.get('o1') or not o.get('o2'):
        return {v: figures.repeat(ns, step=0.5, gap=0.42) for v, ns in o.items()}
    lo = o['o2']

    def low_at(t):
        return next((p for a, d, p in lo if a - _EPS <= t < a + d - _EPS), None)
    up = []
    floor = OSTINATO_SET['o1'][0]
    for a, d, p in o['o1']:
        k = 0
        while k < d - _EPS:
            q = low_at(a + k) if k % 1.0 > 0.25 else None
            if q is not None:     # (the other chord tone in another octave, nearest o1 - a 3rd / 6th rock, never
                q = min((x for x in (q + 12, q + 24, q - 12) if x != p and abs(x - p) <= 9 and x >= floor),
                        key=lambda x: (abs(x - p), x), default=None)      # the lower part's unison)
            up.append((a + k, min(0.42, d - k), q if q is not None else p))
            k += 0.5
    if kind == 'arp':                                 # low - o1 - high - o1 over each held o1 note, the o2 part held
        up = []
        for a, d, p in o['o1']:
            q = low_at(a)
            q = p - 12 if q is None else q
            while q < floor:
                q += 12
            hi = q + 12 if q + 12 > p else q + 24
            cyc = (q, p, hi, p) if q < p else (p, hi, p, hi)
            k, j = 0.0, 0
            while k < d - _EPS:
                up.append((a + k, min(0.45, d - k), cyc[j % 4]))
                k += 0.5
                j += 1
        return {'o1': up, 'o2': list(lo)}
    under = figures.repeat(lo, **({'step': 1.0, 'gap': 0.8} if rs.random() < 0.6 else
                                  {'step': 1.0, 'gap': 0.85, 'offset': 0.5}))
    return {'o1': up, 'o2': under}


def lines_from_block(b, sec: dict, mel: list, key: str, meter: int, seed) -> None:
    """The lines the block's texture needs (orchestration.needs), written into the block from the lead sheet: mel =
    the section's melody in song beats, b.chart its chords (see the module docstring)."""
    need = orc.needs(b.texture)
    rs = random.Random(f"orch-lines:{seed}:{b.name}")
    if mel and 'melody' in need:
        b.add(orc.Line('melody', mel))
    harm = {}
    tenor = b.meta.get('lead') in TENOR_LEADS
    if 'harmony' in need:
        n = max(2, min(4, need['harmony'][0].get('n', 3)))
        harm = _harmony(b.chart, mel, n, key, above=tenor)
        for v, ns in harm.items():
            if ns:
                b.add(orc.Line('harmony', ns, voice=v))
    if 'inner' in need:
        inner = _harmony(b.chart, mel, 2, key, ranges={'i1': (55, 76, 64), 'i2': (48, 69, 57)})
        for v, ns in inner.items():
            if ns:
                b.add(orc.Line('inner', ns, voice=v))
    bass = []
    if 'bass' in need or 'counter' in need:
        walk = 0.5 if sec.get('bass') == 'walk' else 0.0
        bass = _bass(b.chart, key, walk, rs.random())
        if 'bass' in need and bass:
            b.add(orc.Line('bass', bass))
    if 'counter' in need and b.meta.get('counter', 'none') != 'none' and mel:
        cl = _counter(b.chart, mel, bass, key, meter, rs.random())
        if cl:
            b.add(orc.Line('counter', cl))
    if 'ostinato' in need:
        o = _harmony(b.chart, mel, 2, key, ranges=OSTINATO_SET)
        art = need['ostinato'][0].get('art', 'staccato')
        for v, ns in _ostinato(o, _pick_w(OSTINATO, rs), rs).items():
            if ns:
                b.add(orc.Line('ostinato', ns, voice=v, art=art))
    for i, slot in enumerate(need.get('colour', ())):
        if b.meta.get(f'colour{i}', 'none') == 'none':
            continue
        for ns, art in _colour(slot.get('figure', 'arp'), b.chart, harm or _harmony(b.chart, mel, 3, key), key, b,
                               meter, rs.random()):
            if ns:
                b.add(orc.Line('colour', ns, art=art, meta={'slot': i, 'figure': slot.get('figure')}))


# ------------------------------------------------------------------------------------------------ the build

def _end_lines(b, last_mel: list, end_chord: str, key: str) -> None:
    """The final block: the end chord held - the melody's last note resolved to the chord tone nearest it, the
    harmony's parts and the bass."""
    c = chord(end_chord)
    pcs = {(c.root + i) % 12 for i in c.intervals}
    a, L = b.start, b.length
    if last_mel:
        lp = last_mel[-1][2]
        top = min((q for q in range(lp - 5, lp + 6) if q % 12 in pcs), key=lambda q: (abs(q - lp), q))
        b.add(orc.Line('melody', [(a, L, top)]))
        mel = [(a, L, top)]
    else:
        mel = []
    harm = _harmony([(a, L, end_chord)], mel, 3, key)
    for v, ns in harm.items():
        if ns:
            b.add(orc.Line('harmony', ns, voice=v))
    root = next(q for q in range(36, 48) if q % 12 == c.root % 12)
    b.add(orc.Line('bass', [(a, L, root)]))


def build_orchestra(tune, genre=None, arrangement=None) -> Song:
    """The Song of an orchestra tune (the module docstring). Deterministic from tune.seed; arrangement: an
    Arrangement record (kind 'orchestra') to replay (default tune.arrangement, else drawn)."""
    from .arrangement import Dice
    from .composer import _pick
    from .genres import get
    from .perform import _marks, _piano_draws, _piano_plan, _swell
    g = genre or get(tune.genre)
    P, BD = g.plan, g.band
    meter, sd = tune.meter, tune.seed
    if arrangement is None:
        arrangement = getattr(tune, 'arrangement', None)
    dice = Dice('orchestra', arrangement)
    rng = random.Random(f"orchestra:{sd}")
    plan = _piano_plan(tune, g, rng, dice)
    _piano_draws(tune, g, plan, rng, dice)
    sizes = P['sizes']
    size = dice.pick(None, 'size', random.Random(f"orch-size:{sd}"), g.moods[tune.mood]['size'])
    table = orch.role_table(BD['preset'])
    roles = [r for r in sizes[size] if r in table]

    def pick(block, key, weights):
        if not weights:
            return None
        r_ = random.Random(f"orch:{sd}:{block}:{key}")
        if key in RECORDED:
            return dice.pick(block, key, r_, weights)
        return _pick(r_, weights)
    # ---- the song's sections and the score's blocks (the chart, the melody, the dynamics marks)
    s = Song(tune.title, tempo=tune.tempo, key=tune.key, seed=sd % 100000 + 1, tail=8, meter=(meter, 4))
    for sec, _, _, L in plan:
        s.section(sec['name'], bars=L / meter)
    end_bars = max(1, P.get('end', 1))
    s.section('end', bars=end_bars)
    secs = {x.name: x for x in s.sections}
    score = orc.OrchScore(tune.title, tune.key, meter, tune.tempo)
    mels = {}
    amps_all = dice.out
    for sec, ch, mel, L in plan:
        a = secs[sec['name']].start
        m_abs = [(a + st, du, p) for st, du, p in mel]
        peak_at = None
        if sec.get('peak') and mel:
            top = max(mel, key=lambda n: (n[2], -n[0]))
            peak_at = a + top[0]
        own = _marks(sec.get('dyn', 'mp'), a, a + L, peak_at if sec.get('peak') else None)
        marks = list(own)
        amps = amps_all.get(sec['name'], 'swell')
        nb = int(round(L / meter))
        for f0 in range(0, nb, 4):
            if P.get('swell') and 'part' in sec and not sec.get('peak') and amps:
                marks += _swell(own, mel, a, f0 * meter, min(L, (f0 + 4) * meter), amps[f0 // 4])
        b = score.block(sec['name'], a, L, _chart_abs(ch, a), key=_key_name(tune.key, sec.get('_key')), marks=marks,
                        peak=bool(sec.get('peak')), frame=sec.get('frame'))
        mels[sec['name']] = m_abs
    weights = {sec['name']: sec.get('orch') or {'strings_pad': 1.0} for sec, *_ in plan}
    orc.plan_blocks(score, weights, roles, pick)
    for (sec, ch, mel, L), b in zip(plan, score.blocks):
        lines_from_block(b, sec, mels[sec['name']], b.key, meter, sd)
    # ---- the end: the final chord on the last block's colours
    end = secs['end']
    last = score.blocks[-1]
    eb = score.block('end', end.start, end.length, [(end.start, end.length, tune.end_chord)], key=tune.key,
                     marks=[(end.start, 'pp')], frame='end',
                     texture=last.texture if 'harmony' in orc.TEXTURES[last.texture] else 'strings_pad')
    eb.meta = {'lead': last.meta.get('lead') if last.meta.get('lead') in roles else 'violins1'}
    last_mel = next((mels[x.name] for x in reversed(score.blocks[:-1]) if mels.get(x.name)), [])
    _end_lines(eb, last_mel, tune.end_chord, tune.key)
    plan_o = orc.orchestrate(score, {r: table[r] for r in roles}, pick)
    used = plan_o.roles()
    # ---- the band: only the roles the piece plays (one track per section of the orchestra)
    b_ = band(s, used, g)
    marks = sorted(m for x in score.blocks for m in x.marks)
    sc = orch.Score(s, b_, marks, key=tune.key, seed=sd % 9973, style=BD.get('style', 'film'))
    lp = BD.get('line_phrasing')          # (a line's phrase arc at least this deep: no flat solo on any role)
    for p in plan_o.parts:
        if p.role in b_.roles and p.notes:
            ph = max(sc.phrasing.get(p.role, 0.0), lp) if (p.line and lp) else None
            sc.add(p.role, [(a, d, q) for a, d, q in p.notes], p.art, off=p.off, line=p.line, phrasing=ph)
    # ---- the tempo: the sections' tempi, an inhale before the peak, ritardandi, fermatas, the final hold
    before = {}
    for sec, *_ in plan:
        x = secs[sec['name']]
        s.set_tempo(x.start, tune.tempo * sec.get('tempo', 1.0))
        if sec.get('peak') and x.start - 2.0 > 0 and not before.get('rit'):
            s.ritardando((x.start - 2.0, x.start), to=0.85)
        before = sec
        if sec.get('rit') and x.length > meter:
            s.ritardando((x.end - meter + 1.0, x.end), to=sec['rit'], a_tempo=not sec.get('fermata'))
        if sec.get('fermata'):
            s.fermata(x.end - min(1.5, meter - 1.0), hold=sec['fermata'])
    if not plan[-1][0].get('rit'):
        s.ritardando((end.start - meter, end.start), to=0.8, a_tempo=False)
    s.fermata(end.start, hold=END_HOLD)
    tm = s.tempo_map()
    s.tempo_at = lambda beat: tm.bpm_at(s._at(beat))
    try:
        sc.perform(follow=True)     # (a held note follows the hairpins: the lines breathe)
    finally:
        del s.tempo_at
    orch.ring(b_, end.start, length=2.0, db=3.0)
    s.endless_tune = tune
    s.endless_sections = [(sec['name'], secs[sec['name']].start, secs[sec['name']].end) for sec, *_ in plan]
    s.endless_timeline = [(a, bb, sym) for x in score.blocks for a, bb, sym in x.chart]
    s.endless_arrangement = dice.out
    s.orch_score = score
    s.orchestration = plan_o
    s.orch_size = size
    return s


# ------------------------------------------------------------------------------------------------ the score

def band(s, roles, genre='orchestra-film'):
    """The genre's orchestra on song s with only `roles` (one track per section): its master chain (band 'master':
    set first, the preset keeps it), bands.make(preset, options), 'gain' dB on every role, the 'trims'. The one place
    the sound is set up - the hand-written references (songs/pro-orch-*) call it too, so they sound like an endless
    piece by construction."""
    from .genres import get
    g = get(genre) if isinstance(genre, str) else genre
    BD = g.band
    table = orch.role_table(BD['preset'])
    bad = sorted(set(roles) - set(table))
    if bad:
        raise ComposeError(f"orchestra band: unknown roles {bad}; roles: {', '.join(table)}")
    if BD.get('master'):
        s.master.use(BD['master'])
    b_ = bands.make(BD['preset'], s, without=tuple(r for r in table if r not in roles), **(BD.get('options') or {}))
    for role in b_.roles:
        b_[role].gain_db += BD.get('gain', 0.0)
    for role, db in (BD.get('trims') or {}).items():
        if role in b_.roles:
            b_[role].gain_db += db
    return b_


def _reduction(song):
    """A two-track song of the orchestral score for the piano metrics: 'piano' = the melody line (per onset the line
    note of the role that carries the most line notes in its section), 'comp' = every other note."""
    from ..patches import inst
    scs = getattr(song, 'orch_scores', None) or []
    r = Song(song.title or 'reduction', tempo=song.tempo, key=song.key, seed=1, meter=(int(song.beats_per_bar), 4))
    for x in song.sections:
        r.section(x.name, bars=x.length / song.beats_per_bar)
    r.endless_timeline = getattr(song, 'endless_timeline', None)   # (the chord measures; a written piece: its chart)
    mel, acc = [], []
    for sc in scs:
        for role, ns in sc.parts.items():
            ln = sc.lines.get(role, set())
            for n in ns:
                (mel if (round(n[0], 4), n[2]) in ln else acc).append((role, n))
    main = {}
    for x in song.sections:
        cnt: dict = {}
        for role, n in mel:
            if x.start - _EPS <= n[0] < x.end - _EPS:
                c = cnt.setdefault(role, [0, 0])
                c[0] += 1
                c[1] += n[2]
        if cnt:      # the line's role; of its octave doublings (as many notes) the top one - the heard line
            top_n = max(c[0] for c in cnt.values())
            main[x.name] = max(sorted(k for k in cnt if cnt[k][0] >= 0.8 * top_n),
                               key=lambda k: cnt[k][1] / cnt[k][0])
    top, rest = [], []
    for role, n in mel:
        sec = next((x for x in song.sections if x.start - _EPS <= n[0] < x.end - _EPS), None)
        (top if sec is not None and main.get(sec.name) == role else rest).append(n)
    piano = r.track('piano', inst.va())
    comp = r.track('comp', inst.va())
    from ..patterns import Clip
    end = max([n[0] + n[1] for _, n in mel + acc] or [1.0])
    if top:
        piano.play(Clip([(n[0], n[1], n[2], n[3]) for n in top], length=end), 0)
    other = [(n[0], n[1], n[2], n[3]) for n in rest] + [(n[0], n[1], n[2], n[3]) for _, n in acc]
    if other:
        comp.play(Clip(other, length=end), 0)
    return r


MELODIC = ('climax_x', 'peak_x', 'phrase_rests', 'quiet1', 'rest_bar', 'long_share', 'ph_reg', 'ph_den',
           'hook', 'hook_sections', 'mel_issues', 'mel_style', 'climax_copy', 'block_copy', 'rep_pitch',
           'frame_pitches', 'chords_n', 'chord_rep4', 'climax_lift', 'peak_holes', 'long_holds', 'a1_copy',
           'climax_chart', 'arc_pitch_r', 'att_bar', 'climax_single')
"""The new-age composer metrics measured on the reduction (composer.score_metrics 'new-age'): the melodic /
harmonic layer of the score - the pianist's touch, ornaments, left-hand figures and body are not."""


def orchestra_metrics(song, tune=None) -> dict:
    """The orchestra's score metrics: the melodic layer (MELODIC, on the reduction: _reduction) prefixed 'm_' where
    the name clashes, and the orchestration (orchestration.metrics over the song's orch.Score parts) - {name: number}."""
    from .composer import score_metrics
    scs = getattr(song, 'orch_scores', None) or []
    if not scs:
        raise ComposeError("orchestra score: the song has no orch.Score (s.orch_scores)")
    red = _reduction(song)
    try:
        mm = score_metrics(red, tune, 'new-age')
    except (ComposeError, ValueError, ZeroDivisionError, IndexError, KeyError):
        mm = {}
    out = {k: mm[k] for k in MELODIC if k in mm}
    out['peak_x'] = out.pop('peak_x', None)
    merged = _merge(scs)
    om = orc.metrics(merged)
    out.update({('o_' + k if k in out else k): v for k, v in om.items()})
    return {k: v for k, v in out.items() if v is not None}


class _Merged:
    """Several orch.Score objects of one song as one (their parts and lines joined)."""

    def __init__(self, scs):
        self.song, self.band = scs[0].song, scs[0].band
        self.parts, self.lines = {}, {}
        info = {'range': {}, 'sweet': {}, 'kind': {}}
        for sc in scs:
            for r, ns in sc.parts.items():
                self.parts.setdefault(r, []).extend(ns)
            for r, ls in sc.lines.items():
                self.lines.setdefault(r, set()).update(ls)
            for k in info:
                info[k].update(sc.band.info.get(k, {}))
        self.band = type('B', (), {'info': info})()


def _merge(scs):
    return scs[0] if len(scs) == 1 else _Merged(scs)
