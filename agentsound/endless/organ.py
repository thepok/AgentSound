"""Endless ORGAN: a composed tune (composer.compose with the 'organ' genre's data) set in organ TEXTURES and played by
the organist (agentsound.organist) on the church_organ band - perform.build hands every plan['perform'] = 'organ'
tune here.

    python -m agentsound endless organ --count 3 --mood toccata

The arrangement (genre.plan['arrangements'][feel]) is a list of sections, each a part of the tune (its changes +
melody) or a frame (the intro's / tag's vamp + line), set in a TEXTURE on a REGISTRATION drawn once per 'verse'
(sections that share a verse keep their stops; a new verse = new stops, the registrant's gap and the church's ring
before it):
  chorale     the tune in four parts (organ_vocab.harmonize + satb), flowing 8ths by the section's 'flow' budget
              (organ_vocab.flow), a fermata on a share of the phrase ends; S A T on the manual, B in the pedal
              ('pedal': False = manuals only)
  cantus      a chorale prelude: the tune ornamented on a solo stop, ONE motif's counter-line (organ_vocab.counterline)
              and the tenor on the accompaniment manual, the bass in the pedal ('solo': False: without the cantus)
  trio        the tune on one manual, a counter-line on another, a walking pedal (organ_vocab.bass_line)
  toccata     16ths of a TOCCATA_FIGURES figure over the harmony (organ_vocab.toccata), off-beat chords, the tune in
              the pedal two octaves down ('pedal': False: the figuration alone)
  meditation  the tune on a soft solo stop (tremulant: the feel's 'tremulant'), held inner voices on the
              accompaniment, the bass in the pedal; 'planing' (a share): parallel chords under the tune (Vierne /
              Messiaen colour) instead of the inner voices
  trumpet     the tune on the trumpet, detached chords on the beats, a detached pedal
Section keys: SECTION_KEYS. Swell box lanes ('swell': SWELLS) on the enclosed roles of the section's registration.
Every rule is data: REGISTRATIONS, TEXTURES (per-texture budgets), SWELLS, RING_GAP, FERMATA_BEATS.
The song records song.organ_plan (section, texture, registration, verse, beats) and song.organ_voices (organist) for
the score (organ_metrics: the organ tells)."""
from __future__ import annotations

import math
import random

from .. import organ_vocab as ov
from .. import organist
from ..song import Song
from ..theory import ComposeError, note, note_name

__all__ = ['REGISTRATIONS', 'TEXTURES', 'SWELLS', 'RING_GAP', 'FERMATA_BEATS', 'BLOOM', 'SECTION_KEYS', 'build_organ',
           'validate_plan', 'organ_metrics']

_EPS = 1e-6

REGISTRATIONS = {
    # one manual + pedal (chorale, toccata)
    'plenum': {'manual': 'full', 'pedal': 'pedal_full'},
    'principal': {'manual': 'principal', 'pedal': 'pedal'},
    'positiv': {'manual': 'positiv', 'pedal': 'pedal_soft'},
    'flutes': {'manual': 'flute', 'pedal': 'pedal_soft'},
    'soft': {'manual': 'soft', 'pedal': 'pedal_soft'},
    'swell': {'manual': 'swell_full', 'pedal': 'pedal'},
    # a solo against an accompaniment on another manual + pedal (cantus, trio, meditation, trumpet)
    'cornet': {'solo': 'cornet', 'acc': 'flute', 'pedal': 'pedal_soft'},
    'cromorne': {'solo': 'reed', 'acc': 'soft', 'pedal': 'pedal_soft'},
    'oboe': {'solo': 'oboe', 'acc': 'flute', 'pedal': 'pedal_soft'},
    'flute_solo': {'solo': 'flute', 'acc': 'strings', 'pedal': 'pedal_soft'},
    'trumpet': {'solo': 'trumpet', 'acc': 'positiv', 'pedal': 'pedal'},
    'trio': {'solo': 'cornet', 'acc': 'flute', 'pedal': 'pedal_soft'},
    'trio_reed': {'solo': 'positiv', 'acc': 'oboe', 'pedal': 'pedal_soft'},
    'trio_great': {'solo': 'principal', 'acc': 'oboe', 'pedal': 'pedal'},
}
"""Registrations as church_organ roles per slot: 'manual' (one manual for both hands), 'solo' / 'acc' (two manuals:
the tune and its accompaniment - never two registrations of one division) and 'pedal'."""

TEXTURES = {
    # slots the registration must fill; the texture's budgets (drawn per piece / section)
    'chorale': {'slots': ('manual', 'pedal'), 'fermatas': 0.65, 'colour': 0.3, 'breath': 0.5},
    'cantus': {'slots': ('solo', 'acc', 'pedal'), 'ornaments': 0.45, 'colour': 0.3,
               'motifs': {'eighths': 1.0, 'suspirans': 0.7, 'dactyl': 0.5, 'anapaest': 0.3}},
    'trio': {'slots': ('solo', 'acc', 'pedal'), 'ornaments': 0.3, 'colour': 0.25, 'walk': 0.35,
             'motifs': {'eighths': 1.0, 'dactyl': 0.6, 'anapaest': 0.4}},
    'toccata': {'slots': ('manual', 'pedal'), 'colour': 0.2, 'rate': 2.0, 'ring': False,
                'figures': {'widor': 1.0, 'wave': 0.6, 'broken_up': 0.5, 'zigzag': 0.4, 'drum': 0.3, 'turn': 0.6,
                            'rocking': 0.5, 'broken_down': 0.3, 'turn_down': 0.3}, 'run': 0.3},
    'meditation': {'slots': ('solo', 'acc', 'pedal'), 'ornaments': 0.12, 'colour': 0.5, 'rate': 2.0},
    'trumpet': {'slots': ('solo', 'acc', 'pedal'), 'ornaments': 0.5, 'colour': 0.25, 'ring': False},
}
"""The organ textures (build_organ): the registration slots each needs, its budgets - fermatas (the share of a
chorale's phrase ends held), ornaments (the share of organ_vocab.ornament_targets realised), colour (harmonize's 7ths /
secondary dominants), rate (beats per harmony slot), motifs / figures (the piece's ONE counter-line rhythm / toccata
figure, drawn per piece; run: the share of a toccata's sections whose last bar rushes up a scale into the
cadence), walk (the trio pedal's passing 8ths), breath (a chorale's phrase-end chord is held into the
tune's rest up to this many beats before the next phrase: the breath, not a silent beat), ring (False: no pause for the church before a new verse
unless one manual's stops change - the hand moves to another manual at once; default True)."""

SWELLS = {
    'cresc': ((0.0, 0.05), (0.85, 1.0, 'smooth'), (1.0, 1.0)),       # the box opens through the section
    'close': ((0.0, 0.75), (1.0, 0.1, 'smooth')),                    # it closes into the end
    'open': ((0.0, 1.0), (1.0, 1.0)),
    'breathe': 'phrase',                                             # per phrase: (rest, peak, peak at)
}
SWELL_BREATHE = (0.45, 0.85, 0.6)
"""The meditation's swell: every phrase opens the box from 0.45 to 0.85 at 60 % of it and lets it back."""

RING_GAP = (1.4, 2.4)
"""Seconds of silence before a new verse (another registration): the registrant draws the stops, the church rings."""
FERMATA_BEATS = (0.6, 1.4)
"""A chorale phrase end's fermata: extra beats held (drawn)."""
BLOOM = {'beats': 2.0, 'db': 3.0}
"""The church blooms into a silence (orch.ring): the hall send up by db over the held chord before a new verse and
the end (songs/toccata-tenebrae), back before the next verse."""

SECTION_KEYS = {'name', 'part', 'frame', 'texture', 'reg', 'verse', 'chance', 'rit', 'fermata', 'flow', 'pedal',
                'solo', 'swell', 'figure', 'planing', 'register', 'descant', 'bars', 'pedal_line', 'lh', 'lift'}
"""An organ section: name; part (a form part) or frame ('intro' / 'tag'); texture (TEXTURES); reg {registration:
weight} (drawn once per verse); verse (sections sharing it keep the registration; default its name); chance (the share
of pieces that play it); rit (the last bar slows to x); fermata (beats held on the last chord); flow (a chorale's
passing 8ths per bar); pedal / solo (False: without the pedal / the cantus); swell (SWELLS); figure (a toccata's 1st,
2nd or 3rd drawn figure); planing (a meditation's share of parallel chords); register (a toccata's figuration band
(low, high) - the bands climb to the climax); descant (a chorale's last verse: a descant over the tune in
quarters, up to A5 - the climax at the end, blind round 1); bars (a pedal point's length: {bars: weight}).
pedal_line (a toccata's pedal: 'theme' - the tune in long notes, default - or 'bass' - a bass line in halves);
lh (a toccata's left hand: 'offbeat' chords, default, or 'beat'); lift (12: the tune an octave up where it fits under
the solo's top - the reprise as the climax).
A frame 'pedal_point' is the retransition before a return: the dominant held in the pedal for `bars` bars under
PEDAL_POINT's chords (tonic 6/4, subdominant, V7 over it) in the section's texture, no tune - it breaks the 8-bar grid
and builds the tension of the return (blind round 1)."""

PEDAL_POINT = {2: ('I', 'V7'), 3: ('I', 'IV', 'V7'), 4: ('I', 'IV', 'I', 'V7')}
"""The chords over a dominant pedal point per length in bars (one a bar; slash chords over the dominant)."""

VARY = 2.0
"""A tune part heard again (another verse, the A's repeats) is re-harmonized: the chord of the earlier hearing at the
same slot costs this much more (organ_vocab.harmonize avoid / vary; the cadence goals stay) - variations, not copies
(blind round 1: verses that only changed stops)."""
PEDAL_RANGE = {'meditation': (36, 52), 'cantus': (36, 55), 'trumpet': (36, 55), 'chorale': (36, 57)}
"""The pedal's bass range per texture over a solo (satb ranges['B']): the 16' line stays under the hands (blind round 1:
a pedal in the tenor, above the left hand)."""
TRUMPET_ACC = {'quarters': 1.0, 'half_quarters': 0.9, 'halves': 0.6}
"""The trumpet tune's detached chords per bar (drawn per section): on every beat, a half then two quarters, halves -
three-note chords (the third voice fills the chord), never one dyad struck four times."""
FINAL_BARS = 1
"""The coda ends on the tonic (tune.end_chord: the Picardy third drawn by the genre's endings): its last chord becomes
the dominant (V7) under the tune's 2nd degree and FINAL_BARS of the tonic are added (blind round 1: every piece ended
on the tag's plagal IVm6 or a dominant)."""


# ------------------------------------------------------------------------------------------------ validation

def validate_plan(genre, bad) -> None:
    """The organ genre's plan: arrangements per feel, sections with SECTION_KEYS, known textures and registrations
    that fill the texture's slots."""
    arr = genre.plan.get('arrangements')
    if not isinstance(arr, dict) or set(genre.feels) - set(arr):
        bad("an 'organ' plan needs plan['arrangements'] {feel: [sections]} for every feel")
    for feel, secs in arr.items():
        if feel not in genre.feels:
            bad(f"plan arrangements: {feel!r} is no feel of the genre")
        names = set()
        for sd in secs:
            extra = set(sd) - SECTION_KEYS
            if extra or 'name' not in sd or ('part' in sd) == ('frame' in sd):
                bad(f"organ section {sd!r}: a name, a 'part' or a 'frame', keys {', '.join(sorted(SECTION_KEYS))}")
            if sd['name'] in names:
                bad(f"organ section name {sd['name']!r} twice in {feel!r}")
            names.add(sd['name'])
            if sd.get('frame') not in (None, 'intro', 'tag', 'pedal_point'):
                bad(f"organ section {sd['name']!r}: frame 'intro', 'tag' or 'pedal_point'")
            if (sd.get('frame') == 'pedal_point') != ('bars' in sd) or \
                    any(b not in PEDAL_POINT or w <= 0 for b, w in (sd.get('bars') or {}).items()):
                bad(f"organ section {sd['name']!r}: a pedal_point (only) has bars {{n: weight}}, n in "
                    f"{sorted(PEDAL_POINT)}")
            for f in genre.forms:
                from .genres import FORMS
                if 'part' in sd and sd['part'] not in FORMS[f]['parts']:
                    bad(f"organ section {sd['name']!r}: part {sd['part']!r} is not in form {f!r}")
            tx = sd.get('texture')
            if tx not in TEXTURES:
                bad(f"organ section {sd['name']!r}: texture one of {', '.join(TEXTURES)}")
            reg = sd.get('reg')
            if not isinstance(reg, dict) or not reg or any(w <= 0 for w in reg.values()):
                bad(f"organ section {sd['name']!r}: reg {{registration: weight > 0}}")
            for r in reg:
                if r not in REGISTRATIONS:
                    bad(f"organ section {sd['name']!r}: registration {r!r} (one of {', '.join(REGISTRATIONS)})")
                miss = set(TEXTURES[tx]['slots']) - set(REGISTRATIONS[r])
                if miss:
                    bad(f"organ section {sd['name']!r}: registration {r!r} has no {sorted(miss)} for a {tx}")
            if sd.get('swell') is not None and sd['swell'] not in SWELLS:
                bad(f"organ section {sd['name']!r}: swell one of {', '.join(SWELLS)}")
            for k, lo, hi in (('chance', 0, 1), ('rit', 0.3, 1), ('fermata', 0, 8), ('flow', 0, 4),
                              ('planing', 0, 1)):
                if k in sd and not lo <= sd[k] <= hi:
                    bad(f"organ section {sd['name']!r}: {k} must be {lo}..{hi}")
            if sd.get('figure', 1) not in (1, 2, 3):
                bad(f"organ section {sd['name']!r}: figure 1, 2 or 3 (the piece's drawn toccata figures)")
            if 'register' in sd:
                try:
                    lo_, hi_ = (note(x) for x in sd['register'])
                except Exception:
                    lo_, hi_ = 0, -1
                if not 12 <= hi_ - lo_ <= 24:
                    bad(f"organ section {sd['name']!r}: register (low, high) note names an octave or two apart")


# ------------------------------------------------------------------------------------------------ helpers

def _pick(rng: random.Random, weights: dict):
    items = sorted(weights.items())
    tot = sum(w for _, w in items)
    x = rng.random() * tot
    for k, w in items:
        x -= w
        if x <= 0:
            return k
    return items[-1][0]


def _chart(ch) -> list:
    out, t = [], 0.0
    for sym, b in ch:
        out.append((t, b, sym))
        t += b
    return out


def _ends(mel, L: float) -> list:
    """Beats where a phrase's last note starts: a note followed by a rest (half a beat+) or the last one."""
    out = []
    for i, (st, du, p) in enumerate(mel):
        nxt = mel[i + 1][0] if i + 1 < len(mel) else None
        if nxt is None or nxt > st + du + 0.45:
            out.append(st)
    return out


def _slots(mel, chart, key, meter, rs, *, colour, rate=1.0, fill=False, piece=None):
    """The harmony slots under the tune (organ_vocab.harmonize); fill=True: the tune's rests get the chart's chords
    too (the accompaniment goes on through the cantus' rests - a chorale prelude's interludes)."""
    L = sum(b for _, b, _ in chart)
    if not mel:
        return ov.slots_from_chart(chart, key, rate=max(rate, 2.0), ends=[chart[-1][0]])
    seen = piece.setdefault('harm', {}) if piece is not None else {}
    sig = (tuple(mel), rate)
    sl = ov.harmonize(mel, chart, key, meter=meter, rate=rate, ends=_ends(mel, L), colour=colour, seed=rs,
                      avoid=seen.get(sig), vary=VARY)
    seen[sig] = {round(x.start, 3): x.chord.name for x in sl}
    if not fill:
        return sl
    out, t = [], 0.0
    for s_ in sorted(sl, key=lambda x: x.start) + [None]:
        until = s_.start if s_ is not None else L
        if until - t > 0.49:                           # a gap: the chart's chords in it, a beat at a time
            part = [(max(a, t), min(a + b, until) - max(a, t), sym) for a, b, sym in chart
                    if a < until - _EPS and a + b > t + _EPS]
            out += ov.slots_from_chart(part, key, rate=rate)
        if s_ is not None:
            out.append(s_)
            t = s_.start + s_.dur
    return sorted(out, key=lambda x: x.start)


def _hold_ends(v: dict, mel, keep: float) -> dict:
    """Every voice's phrase-end chord held into the tune's rest, `keep` beats of breath left before the next phrase."""
    if not mel:
        return v
    holds = []
    for i, (st, du, p) in enumerate(mel[:-1]):
        end, nx = st + du, mel[i + 1][0]
        if nx - end >= keep + 0.4:
            holds.append((end, nx - end - keep))
    out = {}
    for k, ns in v.items():
        new = []
        for st, du, p in ns:
            ext = next((x for e, x in holds if abs(st + du - e) < 0.05), 0.0)
            new.append((st, du + ext, p))
        out[k] = new
    return out


def _satb(slots, mel, key: str, bass=None) -> dict:
    """organ_vocab.satb, the bass in `bass` (PEDAL_RANGE) where a voicing fits, else in the default ranges; a tune
    under the soprano's range: every voice's range widened down by as much."""
    d = max(0, ov.RANGES['S'][0] - min(p for _, _, p in mel)) if mel else 0
    rng_ = {v: (max(36, lo - d), hi) for v, (lo, hi) in ov.RANGES.items()} if d else {}
    for extra in ([{'B': bass}] if bass else []) + [{}]:
        try:
            return ov.satb(slots, mel or None, key, ranges=dict(rng_, **extra))
        except ComposeError:
            if not extra:
                raise
    raise ComposeError("organ: no four-part voicing")


def _ornaments(line, meter, ends, share, rng) -> dict:
    return {i: k for i, k in ov.ornament_targets(line, meter, ends=ends) if rng.random() < share}


def _beats_of(notes) -> list:
    return sorted({round(n[0], 4) for n in notes})


_ACC_RHYTHM = {'quarters': ((0, 1), (1, 1), (2, 1), (3, 1)), 'half_quarters': ((0, 2), (2, 1), (3, 1)),
               'halves': ((0, 2), (2, 2))}


def _restrike(voices, L: float, meter: int, slots=(), pattern: str = 'quarters') -> list:
    """Block chords from held inner voices in a TRUMPET_ACC rhythm (the trumpet tune's detached accompaniment), a
    third tone between / under them where the slot's chord misses one (three-note chords)."""
    out = []
    rhythm = list(_ACC_RHYTHM[pattern]) if meter == 4 else [(o, 1) for o in range(meter)]
    for bar in range(int(math.ceil(L / meter - _EPS))):
        for o, d in rhythm:
            b = bar * meter + o
            if b >= L - _EPS:
                continue
            ps = [q for v in voices for st, du, q in v if st - _EPS <= b < st + du - _EPS][:2]
            if not ps:
                continue
            h = next((x.chord for x in slots if x.start - _EPS <= b < x.start + x.dur - _EPS), None)
            pcs = set(h.pcs) if h is not None else set()
            miss = sorted(pcs - {q % 12 for q in ps})
            if miss and len(ps) == 2:
                lo_, hi_ = min(ps), max(ps)
                inner = [q for q in range(lo_ + 1, hi_) if q % 12 in miss]
                under = [q for q in range(max(52, lo_ - 9), lo_) if q % 12 in pcs]
                if inner:
                    ps.append(inner[len(inner) // 2])
                elif under:
                    ps.append(under[-1])
            dur = min(float(d), L - b)
            out += [(float(b), dur, q) for q in sorted(set(ps))]
    return out


def _pedal_tune(mel) -> list:
    """The tune moved into the pedal (two octaves down, or one where it would fall under C2)."""
    if not mel:
        return []
    hi_ok = note('D4')
    for k in (2, 1, 3):
        sh = [(st, du, p - 12 * k) for st, du, p in mel]
        if all(note('C2') <= p <= hi_ok for _, _, p in sh):
            return sh
    return [(st, du, min(hi_ok, max(note('C2'), p - 24))) for st, du, p in mel]


# ------------------------------------------------------------------------------------------------ textures

def texture(name: str, sec: dict, chart, mel, key: str, meter: int, rng: random.Random, piece: dict) -> list:
    """The voices of one section in its texture: [(slot, notes, voice name, kind, touch, ornaments)] (section
    beats)."""
    T = TEXTURES[name]
    L = sum(b for _, b, _ in chart)
    rs = rng.random()
    ends = _ends(mel, L) if mel else []
    pedal = sec.get('pedal', True)
    solo = sec.get('solo', True)
    out = []
    if name == 'chorale':
        slots = _slots(mel, chart, key, meter, rs, colour=T['colour'], piece=piece)
        v = _satb(slots, mel, key, PEDAL_RANGE['chorale'] if pedal else None)
        if sec.get('flow'):
            v = ov.flow(v, slots, key, per_bar=sec['flow'], meter=meter, seed=rs)
        v = _hold_ends(v, mel, T['breath'])
        if sec.get('descant') and mel:
            out.append(('manual', ov.counterline([v[x] for x in 'SATB'], slots, key, lo='C5', hi='A5', motif='quarter',
                                                 below=v['S'], hold=0.3, rest=0.05, meter=meter, seed=rs + 2),
                        'descant', 'line', 'auto', {}))
        for nm in 'SAT':
            out.append(('manual', v[nm], nm, 'line', 'legato' if nm in 'AT' else 'auto', {}))  # (inner voices tied over)
        out.append(('pedal' if pedal else 'manual', v['B'], 'B', 'line', 'auto', {}))
    elif name == 'cantus':
        slots = _slots(mel, chart, key, meter, rs, colour=T['colour'], fill=True, piece=piece)
        v = _satb(slots, mel, key, PEDAL_RANGE['cantus'])
        cl = ov.counterline([v['S'], v['T'], v['B']], slots, key, lo='A3', hi='E5', motif=piece['motif'],
                            above=v['S'], below=v['T'], meter=meter, seed=rs)
        if solo and mel:
            out.append(('solo', v['S'], 'cantus', 'line', 'auto',
                        _ornaments(v['S'], meter, ends, T['ornaments'], rng)))
        out.append(('acc', cl, 'counter', 'line', 'auto', {}))
        out.append(('acc', v['T'], 'tenor', 'line', 'auto', {}))
        out.append(('pedal', v['B'], 'bass', 'line', 'auto', {}))
    elif name == 'trio':
        slots = _slots(mel, chart, key, meter, rs, colour=T['colour'], fill=True, piece=piece)
        bass = ov.bass_line(slots, key, lo='C2', hi='D3', walk=T['walk'], against=mel or None, seed=rs)
        ctx = ([mel] if mel else []) + [bass]
        cl = ov.counterline(ctx, slots, key, lo='G3', hi='C5', motif=piece['motif'], above=mel or None,
                            below=bass, meter=meter, seed=rs + 1)
        if solo and mel:
            out.append(('solo', list(mel), 'rh', 'line', 'auto', _ornaments(mel, meter, ends, T['ornaments'], rng)))
        out.append(('acc', cl, 'lh', 'line', 'auto', {}))
        out.append(('pedal', bass, 'pedal', 'line', 'auto', {}))
    elif name == 'toccata':
        slots = _slots(mel, chart, key, meter, rs, colour=T['colour'], rate=T['rate'], fill=True, piece=piece)
        fig = piece['figures'][sec.get('figure', 1) - 1]
        reg_ = tuple(sec.get('register', ('C5', 'C6')))
        lh = sec.get('lh', 'offbeat')
        # the last bar: a scale run rushing into the cadence (a share of the sections)
        cut_ = L - meter if rng.random() < T['run'] and L > 2 * meter else L
        main = [x for x in slots if x.start < cut_ - _EPS]
        f = ov.toccata(main, key, figure=fig, register=reg_, lh=lh, lh_register=('G3', 'G4'), seed=rs)
        rh, lhn = list(f['rh']), list(f['lh'])
        if cut_ < L:
            g_ = ov.toccata([x for x in slots if x.start >= cut_ - _EPS], key, figure='scale',
                            register=(note_name(note(reg_[0]) - 7), reg_[1]), lh=lh, lh_register=('G3', 'G4'),
                            seed=rs)
            rh += g_['rh']
            lhn += g_['lh']
        rh = [n for n in rh if n[0] < L - _EPS]
        out.append(('manual', rh, 'figure', 'figure', 'auto', {}))
        out.append(('manual', lhn, 'chords', 'chords', 'detache', {}))
        if pedal and mel and sec.get('pedal_line', 'theme') == 'theme':
            out.append(('pedal', _pedal_tune(mel), 'theme', 'line', 'auto', {}))
        elif pedal:
            out.append(('pedal', ov.bass_line(slots, key, lo='C2', hi='D3', walk=0.2, against=None, seed=rs),
                        'bass', 'line', 'auto', {}))
    elif name == 'meditation':
        slots = _slots(mel, chart, key, meter, rs, colour=T['colour'], rate=T['rate'], fill=True, piece=piece)
        v = _satb(slots, mel, key, PEDAL_RANGE['meditation'])
        if solo and mel:
            out.append(('solo', v['S'], 'solo', 'line', 'legato',
                        _ornaments(v['S'], meter, ends, T['ornaments'], rng)))
        if mel and rng.random() < sec.get('planing', 0.0):
            out.append(('acc', ov.planing(mel, key, lo=note('E3')), 'planing', 'chords', 'legato', {}))
        else:
            out.append(('acc', v['A'], 'alto', 'line', 'legato', {}))
            out.append(('acc', v['T'], 'tenor', 'line', 'legato', {}))
        out.append(('pedal', v['B'], 'bass', 'line', 'legato', {}))
    elif name == 'trumpet':
        slots = _slots(mel, chart, key, meter, rs, colour=T['colour'], fill=True, piece=piece)
        v = _satb(slots, mel, key, PEDAL_RANGE['trumpet'])
        if solo and mel:
            out.append(('solo', v['S'], 'trumpet', 'line', 'auto',
                        _ornaments(v['S'], meter, ends, T['ornaments'], rng)))
        out.append(('acc', _restrike([v['A'], v['T']], L, meter, slots, _pick(rng, TRUMPET_ACC)), 'chords', 'chords',
                    'detache', {}))
        # (a walking bass of its own under the tune - not the chords' roots)
        out.append(('pedal', ov.bass_line(slots, key, lo='C2', hi='D3', walk=0.45, against=mel or None, seed=rs),
                    'bass', 'line', 'detache', {}))
    else:
        raise ComposeError(f"organ texture {name!r} unknown")
    return out


def _clip(notes, a: float, cut: float, hold: float | None = None) -> list:
    """The notes from section beats to song beats, cut at `cut`; hold: the chord sounding at that beat (song beats)
    is held on to the cut (the last chord before the ring, not a stop in the middle of the bar)."""
    out = []
    for st, du, p in notes:
        s_ = a + st
        if s_ >= cut - 0.05:
            continue
        e_ = min(s_ + du, cut)
        if hold is not None and s_ < hold - _EPS and e_ >= hold - 0.6:
            e_ = cut
        out.append((s_, e_ - s_, p))
    return out


def _final_cadence(ch, mel, key: str, meter: int, end_chord: str):
    """The coda's end (FINAL_BARS): its last chord the dominant 7th under the tune's 2nd degree, then the tonic
    (end_chord) - the tune landing on the tonic nearest its last note. Returns (changes, melody, beats)."""
    k = ov._key(key)
    L0 = sum(b for _, b in ch)
    pen_b = ch[-1][1]
    pen = L0 - pen_b
    fin = meter * FINAL_BARS
    ch = list(ch[:-1]) + [(ov._degree_sym(k, 7, True), pen_b), (end_chord, fin)]
    out = [(st, min(du, pen - st), p) for st, du, p in mel if st < pen - 0.24]
    if mel:
        last = mel[-1][2]
        lo_, hi_ = max(ov.RANGES['S'][0], min(n[2] for n in mel) - 2), ov.RANGES['S'][1] - 2
        cand = [q for q in range(last - 7, last + 8) if q % 12 == k.tonic % 12]
        f = min([q for q in cand if lo_ <= q <= hi_] or cand, key=lambda q: (abs(q - last), q))
        out += [(pen, pen_b, f + 2), (L0, fin, f)]
    return ch, out, L0 + fin


def _pedal_point(key: str, bars: int, meter: int) -> tuple:
    """A pedal point's chart (PEDAL_POINT over the dominant) and the dominant's pitch in C2..B2."""
    k = ov._key(key)
    dom = (k.tonic + 7) % 12
    rel = {'I': 0, 'IV': 5, 'V7': 7}
    ch = []
    for r in PEDAL_POINT[bars]:
        sym = ov._degree_sym(k, rel[r], seventh=(r == 'V7'))
        ch.append((sym if r == 'V7' else f"{sym}/{ov._name(dom, k)}", float(meter)))
    return ch, next(q for q in range(36, 48) if q % 12 == dom)


def _final_chord(end_chord: str, key: str, top: int) -> tuple:
    """The held final chord of a figuration texture: the right hand's four tones under `top`, the left hand's three
    in G3..G4, the pedal's root in C2..B2."""
    h = ov._from_symbol(end_chord, ov._key(key))
    rh = sorted(q for q in range(top - 14, top + 1) if q % 12 in h.pcs)[-4:]
    lh = sorted(q for q in range(55, 68) if q % 12 in h.pcs)[:3]
    ped = next(q for q in range(36, 48) if q % 12 == h.root % 12)
    return rh, lh, ped


# ------------------------------------------------------------------------------------------------ the build

def build_organ(tune, genre=None) -> Song:
    """The Song of an organ tune (see the module docstring). Deterministic from tune.seed."""
    from .. import bands
    from .genres import get
    g = genre or get(tune.genre)
    P = g.plan
    F = g.feels[tune.feel]
    meter, sd = tune.meter, tune.seed
    rng = random.Random(f"organ:{sd}")
    key = tune.key
    # ---- the piece's own draws: the counter-line motif, the toccata figures
    tex_all = {sec['texture'] for sec in P['arrangements'][tune.feel]}
    prng = random.Random(f"organ-piece:{sd}")
    motifs = dict(TEXTURES['cantus']['motifs']) if 'cantus' in tex_all else dict(TEXTURES['trio']['motifs'])
    figs = dict(TEXTURES['toccata']['figures'])
    f1 = _pick(prng, figs)
    figs.pop(f1)
    f2 = _pick(prng, figs)
    figs.pop(f2)
    piece = {'motif': _pick(prng, motifs), 'figures': (f1, f2, _pick(prng, figs) if figs else f1)}
    # ---- the material of every section (the chance drawn per section, in order)
    plan = []
    for sec in P['arrangements'][tune.feel]:
        if rng.random() >= sec.get('chance', 1.0):
            continue
        if 'part' in sec:
            ch, mel = list(tune.changes[sec['part']]), list(tune.melody[sec['part']])
        elif sec['frame'] == 'pedal_point':
            n_ = _pick(random.Random(f"organ-pp:{sd}:{sec['name']}"), sec['bars'])
            ch, mel = list(_pedal_point(key, n_, meter)[0]), []
        else:
            fr = tune.intro if sec['frame'] == 'intro' else tune.tag
            ch, mel = list(fr['changes']), list(fr['melody'])
        L = sum(b for _, b in ch)
        mel = sorted((st, min(du, L - st), p) for st, du, p in mel if st < L - _EPS)
        if sec.get('frame') == 'tag' and ch:           # the coda lands on the tonic
            ch, mel, L = _final_cadence(ch, mel, key, meter, tune.end_chord)
            mel = [n for n in mel if n[1] > 0.1]
        plan.append((sec, ch, mel, L))
    # ---- registrations: one per verse (drawn from its first section's weights)
    vreg, regs = {}, {}
    last_reg = None
    for sec, *_ in plan:
        v = sec.get('verse', sec['name'])
        if v not in vreg:                              # (a new verse: other stops than the verse before, if it may)
            w = {r: x for r, x in sec['reg'].items() if r != last_reg} or sec['reg']
            vreg[v] = _pick(random.Random(f"organ-reg:{sd}:{v}"), w)
            last_reg = vreg[v]
        r = vreg[v] if vreg[v] in sec['reg'] else _pick(random.Random(f"organ-reg:{sd}:{sec['name']}"), sec['reg'])
        regs[sec['name']] = r
    roles = set()
    for sec, *_ in plan:
        R = REGISTRATIONS[regs[sec['name']]]
        roles |= {R[k] for k in TEXTURES[sec['texture']]['slots'] if k != 'solo' or sec.get('solo', True)}
    s = Song(tune.title, tempo=tune.tempo, key=key, seed=sd % 100000 + 1, tail=8, meter=(meter, 4))
    for sec, _, _, L in plan:
        s.section(sec['name'], bars=L / meter)
    secs = {x.name: x for x in s.sections}
    from ..bandlib import orchestra as orch
    classic = ('soft', 'principal', 'full', 'pedal', 'pedal_full')
    b = bands.make('church_organ', s, organ=g.band.get('organ', 'burea'), tremulant=bool(F.get('tremulant')),
                   registers=tuple(r for r in orch.ORGAN_REGISTERS if r in roles),
                   without=tuple(r for r in classic if r not in roles))
    # ---- the voices, section by section; the tempo plan (rit, fermatas, the ring before a new verse)
    voices, phrases, rec = [], [], []
    fermatas = set()

    def fermata(at, ons=(), **kw):
        k = round(at, 3)
        if k not in fermatas:
            fermatas.add(k)
            nxt = min((o for o in ons if o > at + 0.25), default=None)
            if nxt is not None:                        # (it holds up to the next onset: never into another fermata)
                kw['length'] = round(nxt - at, 4)
            s.fermata(at, **kw)
    for i, (sec, ch, mel, L) in enumerate(plan):
        a = secs[sec['name']].start
        chart = _chart(ch)
        R = REGISTRATIONS[regs[sec['name']]]
        srng = random.Random(f"organ-sec:{sd}:{sec['name']}")
        if sec.get('lift') and mel and max(p for _, _, p in mel) + sec['lift'] <= ov.RANGES['S'][1]:
            mel = [(st, du, p + sec['lift']) for st, du, p in mel]
        vs = texture(sec['texture'], sec, chart, mel, key, meter, srng, piece)
        if sec.get('frame') == 'pedal_point':          # the dominant held in the pedal under the chords
            vs = [v for v in vs if v[0] != 'pedal']
            vs.append(('pedal', [(0.0, L, _pedal_point(key, 2, meter)[1])], 'pedal_point', 'line', 'legato', {}))
        if i + 1 == len(plan) and sec.get('frame') == 'tag' and sec['texture'] != 'toccata':
            # the final bar: every voice holds the note it strikes on the downbeat (no line runs on over the end)
            # (struck on it: a tone of the final chord, the nearest)
            fin = L - meter * FINAL_BARS
            pcs = ov._from_symbol(tune.end_chord, ov._key(key)).pcs

            def _tone(st, p, _pcs=pcs, _fin=fin):
                if st < _fin - 0.01 or p % 12 in _pcs:
                    return p
                return min((q for q in range(p - 6, p + 7) if q % 12 in _pcs), key=lambda q: (abs(q - p), q))
            vs = [(sl, [(st, (L - st) if st <= fin + 0.01 and st + du > fin + 0.01 else du, _tone(st, p))
                        for st, du, p in ns if st <= fin + 0.01], nm, kd, tc, o) for sl, ns, nm, kd, tc, o in vs]
        if i + 1 == len(plan) and sec.get('frame') == 'tag' and sec['texture'] == 'toccata':
            # the figuration stops on the final bar: a held full chord (both hands), the pedal's tonic
            fin = L - meter * FINAL_BARS
            vs = [(sl, [(st, min(du, fin - st), p) for st, du, p in ns if st < fin - _EPS], nm, kd, tc, o)
                  for sl, ns, nm, kd, tc, o in vs]
            rh, lh, ped = _final_chord(tune.end_chord, key, note(tuple(sec.get('register', ('C5', 'C6')))[1]))
            vs.append(('manual', [(fin, meter * FINAL_BARS, q) for q in rh + lh], 'final', 'chords', 'legato', {}))
            if sec.get('pedal', True):
                vs.append(('pedal', [(fin, meter * FINAL_BARS, ped)], 'final_pedal', 'line', 'legato', {}))
        ons_sec = sorted({a + st for _, notes, *_ in vs for st, _, _ in notes})
        nxt = plan[i + 1][0] if i + 1 < len(plan) else None
        new_verse = nxt is not None and (nxt.get('verse', nxt['name']) != sec.get('verse', sec['name'])
                                         and regs[nxt['name']] != regs[sec['name']])
        if new_verse and not TEXTURES[sec['texture']].get('ring', True):
            # (a toccata / trumpet tune runs on: the hand moves to a manual already drawn - a pause only where one
            # manual's stops must change)
            div = b.info.get('division') or {}
            mine = {div.get(r): r for r in REGISTRATIONS[regs[sec['name']]].values()}
            theirs = {div.get(r): r for r in REGISTRATIONS[regs[nxt['name']]].values()}
            new_verse = any(d in mine and mine[d] != r for d, r in theirs.items() if d != 'pedal')
        last_end = max((st + du for st, du, _ in mel), default=L)
        cut, hold = a + L, None
        if new_verse:                                  # the ring: the last chord held to the last beat, then silence
            cut = a + (last_end if L - 1.0 < last_end < L - 0.5 else L - 1.0)
            hold = a + min(last_end, L - 1.0)
        for slot, notes, nm, kind, touch, orn in vs:
            ns = _clip(notes, a, cut, hold)
            if not ns:
                continue
            o = {}
            if orn:                                     # (ornament indices of the sorted, clipped line)
                keep = sorted(notes)
                idx = {round(keep[j][0], 4): k for j, k in orn.items() if j < len(keep)}
                o = {j: idx[round(n[0] - a, 4)] for j, n in enumerate(sorted(ns)) if round(n[0] - a, 4) in idx}
            # only the tune breathes (a chorale / toccata: every voice); the accompaniment keeps its pickups
            breathe = slot in ('solo', 'manual') or sec['texture'] in ('chorale', 'toccata')
            voices.append(organist.Voice(ns, R[slot], f"{sec['name']}:{nm}", kind=kind, touch=touch, ornaments=o,
                                         breathe=breathe))
        # phrases: the section's start and every tune onset after a rest
        phrases.append(a)
        for j in range(1, len(mel)):
            if mel[j][0] > mel[j - 1][0] + mel[j - 1][1] + 0.45:
                phrases.append(a + mel[j][0])
        # fermatas on a share of a chorale's phrase ends; the last chord's
        if sec['texture'] == 'chorale' and mel:
            share = TEXTURES['chorale']['fermatas']
            for e in _ends(mel, L)[:-1]:
                if srng.random() < share:
                    fermata(a + e, ons_sec, hold=FERMATA_BEATS[0] + (FERMATA_BEATS[1] - FERMATA_BEATS[0]) * srng.random())
        if sec.get('rit'):
            last = i + 1 == len(plan)
            s.ritardando((a + L - meter, a + L), to=sec['rit'], a_tempo=not last)
        if sec.get('fermata'):
            ons = [st + a for _, notes, *_ in vs for st, _, _ in notes if a + st < cut - 0.05]
            if ons:
                fermata(max(ons), ons_sec, hold=sec['fermata'])
        if new_verse:
            bpm = s.tempo_map().bpm_at(cut)
            have = (a + L - cut) * 60.0 / bpm
            want = RING_GAP[0] + (RING_GAP[1] - RING_GAP[0]) * srng.random()
            if want - have > 0.1:
                fermata(cut, seconds=round(want - have, 2))
        last_on = max((st + a for _, notes, *_ in vs for st, _, _ in notes if a + st < cut - 0.05), default=None)
        rec.append({'section': sec['name'], 'texture': sec['texture'], 'reg': regs[sec['name']],
                    'verse': sec.get('verse', sec['name']), 'start': a, 'end': a + L, 'cut': cut,
                    'bloom': last_on if (new_verse or nxt is None) and last_on is not None else None})
    organist.perform(s, b, voices, phrases=sorted(set(round(x, 4) for x in phrases)), key=key, seed=sd)
    # ---- the church blooms into the silences: the hall send up on the held chord before a new verse / the end
    for k, r in enumerate(rec):
        if r['bloom'] is not None:
            back = rec[k + 1]['start'] if k + 1 < len(rec) else None
            orch.ring(b, r['bloom'], length=max(0.5, min(BLOOM['beats'], r['cut'] - r['bloom'])), db=BLOOM['db'],
                      back=back, back_beats=0.25)
    # ---- the swell box on the enclosed roles of each section's registration
    enclosed = set(b.info.get('swell') or ())
    for (sec, ch, mel, L), r in zip(plan, rec):
        sw = sec.get('swell')
        if not sw:
            continue
        R = REGISTRATIONS[r['reg']]
        rs_ = sorted({R[k] for k in TEXTURES[sec['texture']]['slots']} & enclosed)
        if not rs_:
            continue
        a = r['start']
        if SWELLS[sw] == 'phrase':
            lo, hi, at = SWELL_BREATHE
            starts = [a] + [a + mel[j][0] for j in range(1, len(mel))
                            if mel[j][0] > mel[j - 1][0] + mel[j - 1][1] + 0.45]
            pts = []
            for k, st in enumerate(starts):
                en = starts[k + 1] if k + 1 < len(starts) else a + L
                pts += [(st, lo), (st + at * (en - st), hi, 'smooth'), (en - 0.05, lo, 'smooth')]
        else:
            pts = [(a + x * L, o) + tuple(c) for x, o, *c in SWELLS[sw]]
        orch.swell(b, pts, roles=rs_)
    s.endless_tune = tune
    s.endless_sections = [(r['section'], r['start'], r['end']) for r in rec]
    s.organ_plan = rec
    s.organ_piece = dict(piece)
    return s


# ------------------------------------------------------------------------------------------------ the organ tells

PEDAL_PREFIX = 'pedal'
"""Tracks whose name starts with this are the pedal (church_organ's pedal roles)."""


def _voices(song) -> list:
    """[(name, kind, written, played, ornaments)] - the organist's record, else one voice per track."""
    rec = getattr(song, 'organ_voices', None)
    if rec:
        return [(r['name'], r['kind'], r['written'], r['played'], r.get('ornaments') or {}) for r in rec]
    out = []
    for name, t in song.tracks.items():
        ns = sorted((n.start, n.dur, n.pitch) for n in t.notes)
        if ns:
            out.append((name, 'line', ns, ns, {}))
    return out


def _at(notes, t):
    for st, du, p in notes:
        if st - _EPS <= t < st + du - _EPS:
            return p
        if st > t:
            break
    return None


def organ_metrics(song, tune=None) -> dict:
    """The ORGAN TELLS from the notes (no audio) - composer.score_metrics(style='organ'): the written voices
    (song.organ_voices: the organist's record; a song without it: one voice per track) and the played tracks.
      par58        parallel 5ths / octaves between the line voices per 100 onsets (the voice-leading rule)
      inner_leap   the share of moves over a 4th in the inner lines (neither the top nor the bass line)
      top_leap     the share of moves over a 5th in the top line
      cad_kinds    distinct cadence kinds at the top line's phrase ends (by the bass: authentic V-I, half -V,
                   plagal IV-I, deceptive V-vi)
      cad_auth     the share of those cadences that are authentic
      pedal_idle   the share of bars without a pedal note
      reg_sets     distinct registrations (the set of roles sounding per section)
      reg_run_s    the longest stretch on one registration (s) - registration monotony
      reg_min      registration changes per minute
      ring_min     the shortest silence (s) before a new registration
      legato       the share of a line's consecutive notes that overlap or touch (< 15 ms apart)
      gap_ms       the median silence between a line's detached notes (ms)
      time_sd_ms   the played onsets' deviation from the written (sd, ms)
      chord_ms     the median spread of a written chord's played onsets (ms)
      orn_min      ornaments per minute
      rest_share   the share of the piece without a key down
      onsets_s     distinct onsets per second
      textures     distinct voice kinds x roles (the texture's variety)
      dur_min      minutes
      rep_run      the longest run of one repeated pitch in a top line (a tune stuck on one key - blind round 2)
      bar_copy     the share of bars (3+ notes) whose written notes, all voices, repeat an earlier bar exactly (verses
                   that only change stops - blind round 1)
      end_tonic    1 when the chord sounding at the end is the tonic triad (or part of it, the tonic in it) over its root
                   or 5th (a manuals-only fade on the 6/4), else 0
      top_at       where the manuals' highest note first sounds (0..1 of the piece: a climax late, not in bar 2)
      pedal_high   the share of the pedal's bass notes above D3 (a 16' line in the tenor)"""
    import statistics as st_
    from ..theory import Key
    vs = _voices(song)
    tm = song.tempo_map()
    total = song.seconds(song.length) if hasattr(song, 'seconds') else tm.seconds_at(song.length)
    out = {}
    lines = [(nm, sorted(w)) for nm, kind, w, _, _ in vs if kind == 'line' and len(w) > 1]
    # ---- voice leading: parallels, leaps (top / inner by how often the line is the highest / lowest sounding)
    onsets = sorted({round(n[0], 4) for _, w in lines for n in w})
    par = 0
    prev = None
    top_votes = {nm: [0, 0, 0] for nm, _ in lines}
    for t in onsets:
        cur = [_at(w, t) for _, w in lines]
        if prev is not None:
            par += ov.parallels(prev, cur)
        act = [(p, i) for i, p in enumerate(cur) if p is not None]
        if len(act) >= 2:
            hi_i, lo_i = max(act)[1], min(act)[1]
            for j, (p, i) in enumerate(act):
                top_votes[lines[i][0]][0] += 1
                if i == hi_i:
                    top_votes[lines[i][0]][1] += 1
                if i == lo_i:
                    top_votes[lines[i][0]][2] += 1
        prev = cur
    out['par58'] = round(100.0 * par / max(1, len(onsets)), 2)
    inner_m = inner_l = top_m = top_l = 0
    tops = []
    for nm, w in lines:
        n_, hi_, lo_ = top_votes[nm]
        role = 'top' if n_ and hi_ >= 0.5 * n_ else 'bass' if n_ and lo_ >= 0.5 * n_ else 'inner'
        moves = [abs(b[2] - a[2]) for a, b in zip(w, w[1:]) if b[0] - (a[0] + a[1]) < 0.3 and b[2] != a[2]]
        if role == 'inner':
            inner_m += len(moves)
            inner_l += sum(1 for m in moves if m > 5)
        elif role == 'top':
            top_m += len(moves)
            top_l += sum(1 for m in moves if m > 7)
            tops.append(w)
    out['inner_leap'] = round(inner_l / inner_m, 3) if inner_m else 0.0
    out['top_leap'] = round(top_l / top_m, 3) if top_m else 0.0
    run_, best_ = 1, 1
    for w in tops:
        for a_, b_ in zip(w, w[1:]):
            run_ = run_ + 1 if b_[2] == a_[2] else 1
            best_ = max(best_, run_)
        run_ = 1
    out['rep_run'] = best_ if tops else 0
    # ---- cadences at the top line's phrase ends, read from the lowest sounding line
    try:
        tonic = Key(song.key).tonic % 12
    except Exception:
        tonic = 0
    kinds = []
    for w in tops:
        for i, (s0, d0, p0) in enumerate(w):
            nxt = w[i + 1][0] if i + 1 < len(w) else None
            if nxt is not None and nxt <= s0 + d0 + 0.45:
                continue
            t = s0 + 0.01
            bass = [_at(lw, t) for _, lw in lines]
            bass = [p for p in bass if p is not None]
            if not bass:
                continue
            b1 = min(bass)
            before = None
            for _, lw in lines:
                for s1, d1, p1 in lw:
                    if s1 < s0 - 0.05 and s1 >= s0 - 4 and (p1 - b1) % 12 != 0 and p1 <= b1 + 7:
                        if before is None or s1 > before[0]:
                            before = (s1, p1)
            d1 = (b1 - tonic) % 12
            d0 = (before[1] - tonic) % 12 if before else None
            kinds.append('half' if d1 == 7 else 'auth' if d1 == 0 and d0 in (7, 11) else
                         'plagal' if d1 == 0 and d0 == 5 else 'deceptive' if d0 == 7 and d1 in (8, 9) else 'other')
    real = [k for k in kinds if k != 'other']
    out['cad_kinds'] = len(set(real))
    out['cad_auth'] = round(real.count('auth') / len(real), 3) if real else 0.0
    # ---- the pedal, the registrations, the ring
    mg = song.meter_grid()
    ped = sorted((n.start, n.dur) for name, t in song.tracks.items() if name.startswith(PEDAL_PREFIX)
                 for n in t.notes)
    busy = set()
    for s0, d0 in ped:
        k0, k1 = int(math.floor(mg.bar_at(s0) + _EPS)), int(math.floor(mg.bar_at(s0 + d0 - 0.01) + _EPS))
        busy.update(range(k0, k1 + 1))
    music_end = max((n.start + n.dur for t in song.tracks.values() for n in t.notes), default=0.0)
    n_bars = max(1, int(math.ceil(mg.bar_at(music_end) - _EPS)))
    out['pedal_idle'] = round(1.0 - len([k for k in busy if k < n_bars]) / n_bars, 3)
    sets = []
    for sec in song.sections:
        rs = frozenset(name for name, t in song.tracks.items()
                       if any(sec.start - _EPS <= n.start < sec.end - _EPS for n in t.notes))
        if rs:
            sets.append((sec, rs))
    out['reg_sets'] = len({r for _, r in sets})
    runs, cur, cur_s = [], None, 0.0
    changes, rings = 0, []
    notes_all = sorted((n.start, n.start + n.dur) for t in song.tracks.values() for n in t.notes)
    for k, (sec, rs) in enumerate(sets):
        dur = tm.seconds_at(sec.end) - tm.seconds_at(sec.start)
        if cur is not None and (rs == cur or cur < rs):  # (a stop change retires a role; a voice entering is none)
            cur_s += dur
            cur = cur | rs
        else:
            if cur is not None:
                runs.append(cur_s)
                changes += 1
                last = max((e for s_, e in notes_all if s_ < sec.start - 0.25), default=None)
                first = min((s_ for s_, e in notes_all if s_ >= sec.start - 0.25), default=None)
                if last is not None and first is not None:
                    rings.append(max(0.0, tm.seconds_at(first) - tm.seconds_at(last)))
            cur, cur_s = rs, dur
    runs.append(cur_s)
    out['reg_run_s'] = round(max(runs), 1) if runs else 0.0
    out['reg_min'] = round(changes / max(0.5, total / 60.0), 2)
    out['ring_min'] = round(min(rings), 2) if rings else 0.0
    # ---- articulation, timing (the played record)
    leg = det = 0
    gaps = []
    devs, spreads = [], []
    orn = 0
    by_written = {}
    for nm, kind, w, pl, o in vs:
        orn += len(o)
        if kind != 'line':
            continue
        ps = sorted(pl)
        for a, b2 in zip(ps, ps[1:]):
            g = (b2[0] - (a[0] + a[1])) * 60000.0 / tm.bpm_at(a[0])
            if g < 15:
                leg += 1
            else:
                det += 1
                if g < 1500:
                    gaps.append(g)
        for s0, d0, p0 in w:
            m = min((x for x in ps if x[2] == p0 and abs(x[0] - s0) < 0.3), key=lambda x: abs(x[0] - s0),
                    default=None)
            if m is not None:
                ms = (m[0] - s0) * 60000.0 / tm.bpm_at(s0)
                devs.append(ms)
                by_written.setdefault(round(s0, 4), []).append(ms)
    out['legato'] = round(leg / max(1, leg + det), 3)
    out['gap_ms'] = round(st_.median(gaps), 1) if gaps else 0.0
    out['time_sd_ms'] = round(st_.pstdev(devs), 1) if len(devs) > 1 else 0.0
    spreads = [max(v) - min(v) for v in by_written.values() if len(v) > 1]
    out['chord_ms'] = round(st_.median(spreads), 1) if spreads else 0.0
    out['orn_min'] = round(orn / max(0.5, total / 60.0), 2)
    # ---- silence, density, variety, length
    sil, reach = 0.0, 0.0
    for s0, e0 in notes_all:
        if s0 > reach:
            sil += tm.seconds_at(s0) - tm.seconds_at(reach)
        reach = max(reach, e0)
    out['rest_share'] = round(sil / max(1e-6, tm.seconds_at(reach)), 3)
    ons = {round(n.start, 3) for t in song.tracks.values() for n in t.notes}
    out['onsets_s'] = round(len(ons) / max(1e-6, tm.seconds_at(reach)), 2)
    out['textures'] = len({(kind, r['role']) for (nm, kind, *_), r in zip(vs, getattr(song, 'organ_voices', None)
                                                                             or [{'role': x[0]} for x in vs])})
    out['dur_min'] = round(tm.seconds_at(reach) / 60.0, 2)
    # ---- copies, the end, the climax, the pedal's register
    bars = {}
    for nm, kind, w, _, _ in vs:
        for s0, d0, p0 in w:
            x = mg.bar_at(s0 + 1e-6)
            k0 = int(math.floor(x))
            bars.setdefault(k0, set()).add((round((x - k0) * 8) / 8, round(d0 * 4) / 4, p0))
    seen, copies, counted = set(), 0, 0
    for k0 in sorted(bars):
        sig = frozenset(bars[k0])
        if len(sig) < 3:
            continue
        counted += 1
        if sig in seen:
            copies += 1
        seen.add(sig)
    out['bar_copy'] = round(copies / counted, 3) if counted else 0.0
    tr_notes = [(n.start, n.dur, n.pitch, name) for name, t in song.tracks.items() for n in t.notes]
    if tr_notes:
        t_end = max(n[0] + n[1] for n in tr_notes) - 0.3
        fin = [n for n in tr_notes if n[0] <= t_end < n[0] + n[1]] or tr_notes[-1:]
        pcs = {n[2] % 12 for n in fin}
        root = min(n[2] for n in fin) % 12
        out['end_tonic'] = int(tonic in pcs and root in (tonic, (tonic + 7) % 12)
                               and pcs <= {tonic, (tonic + 3) % 12, (tonic + 4) % 12, (tonic + 7) % 12})
        man = [n for n in tr_notes if not n[3].startswith(PEDAL_PREFIX)]
        if man:
            hi = max(n[2] for n in man)
            first = min(n[0] for n in man if n[2] == hi)
            out['top_at'] = round(first / max(1e-6, music_end), 3)
        else:
            out['top_at'] = 0.0
    else:
        out['end_tonic'], out['top_at'] = 0, 0.0
    bass = [n for n in tr_notes if n[3].startswith(PEDAL_PREFIX) and n[3] != 'pedal_cantus']
    out['pedal_high'] = round(sum(1 for n in bass if n[2] > 50) / len(bass), 3) if bass else 0.0
    return out
