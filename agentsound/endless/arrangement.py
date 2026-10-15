"""The players' arrangement as one plain record: every decision the endless players draw per piece above the notes
(perform.arrange draws it from the tune's seed; perform.build plays it - the same notes as before the record existed).

    from agentsound.endless import perform
    arr = perform.arrange(tune)                  # Arrangement('piano' | 'jazz'), None for an organ tune
    arr.sections['climax']['climax'] = 'step'    # any decision changed: values from the genre's own vocabulary
    song = perform.build(tune, arrangement=arr)

Arrangement(kind, piece, sections): `piece` the piece-level decisions, `sections` {name: {key: value}} in play order.

kind 'piano' (perform.build_piano: plan['sections'] of the new-age / classical / lo-fi pianos) - a section is a
plan['sections'] entry by name among the entries of the piece's layout (section_specs; the section list = which
entries are played, their 'chance' drawn), its keys:
  copied from the plan entry (the genre's texture / dynamics / tempo per section - PIANO_FIXED):
    melody ('lift'), dyn (a mark or (start, [peak,] end) marks), figures (the left hand's figure set: the feel's
    'figures' key), harmonize (1 3rds / 6ths, 2 chords), harm_share, tempo, rit, fermata, keep_bars, lh_only, peak,
    drums - an entry's {choice: weight} for one of them (lh_only, octave, dyn) is drawn
  drawn (the plan entry's {choice: weight}, perform.ARRANGE_KEYS / _arrange, PIANO_DRAWN):
    octave, climax ('lift' / 'theme' / 'climb' / 'step' / 'grow'; the tune's set-level pin, Tune.arrange, before
    the record), reharm (share), bars (the part's bar spans), tail, cadence, bass ('root' / 'walk'), octave_half,
    fill, turn, swell ([levels per 4-bar phrase]), cadenza (bool: the flourish wanted), moves ([a waltz's later bar
    of a held chord: 'hold' / 'bass' / 'sub'], perform._moving_bass), vary ([a return's development per 2-bar unit:
    genres.VARY 'keep' / 'orn' / 'rhythm' / 'seq' / 'invert'], perform._vary), key (the section's key:
    genres.KEY_SHIFTS 'home' / 'step' / 'IV' / 'bVI' / 'bIII' / 'III' / 'par' / 'rel', perform._modulate / _keys)
  piece: layout (plan['set']['layout']: the arrangement's form - the tune's set-level pin, else drawn), touch
    (plan['touch_span']: the tune's touch window shift (lo, hi))
kind 'jazz' (perform.build: intro / head / solo / head out / tag) - sections 'intro', 'head:<part>', 'solo',
'out:<label>' (a reharmonized head-out part: '<part>v'), 'tag', their keys (JAZZ_FIELDS):
    lh (the left hand: a pianist.LH_STYLES style or a FIGURES figure), steps ([the phrase-touch step per 4-bar
    phrase], perform.phrase_levels), choruses (solo choruses), opening / quotes (soloist), over (the solo's ceiling
    over the head's top), window (the climax window, bars before the solo's end), burst (the double-time burst's stage)

kind 'orchestra' (endless/orchestra.py: a piano plan orchestrated) - the piano kind's sections and keys (the same
plan draws) plus the orchestrator's (ORCH_DRAWN): texture (orchestration.TEXTURES: the section's orchestration plan),
lead (the melody's role), counter (the counter-melody's role or 'none'); piece: size (plan['sizes']: 'chamber' /
'full').

Dice: the one way the players draw a recorded decision - record mode (no record given: the dice's value is stored),
replay (a record given: the same dice are thrown - every random stream stays where it was - and the record's value
wins; a decision the record does not hold is drawn, one it holds that the players never reach is dropped). A list
decision of another length than the dice's is drawn again.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

PIANO_FIXED = ('melody', 'dyn', 'figures', 'harmonize', 'harm_share', 'tempo', 'rit', 'fermata', 'keep_bars',
               'lh_only', 'peak', 'drums')
"""A piano section's keys copied from its plan entry (the record holds them so a player can be told otherwise)."""
PIANO_DRAWN = ('octave', 'climax', 'reharm', 'bars', 'tail', 'cadence', 'bass', 'octave_half', 'fill', 'turn', 'swell',
               'cadenza', 'moves', 'vary', 'key')
MOVES = ('hold', 'bass', 'sub', 'ped')
PLAY_KEYS = ('rubato', 'inhale', 'lilt', 'breath', 'push', 'inner', 'cap', 'lh_vel', 'pedal', 'end_dyn', 'end_roll',
             'end_hold')
"""The pianist's per-piece choices (plan['play'] {key: {value: weight}}, piece-level; perform._piano_draws /
_play_piano): rubato (x the feel's phrase rubato depth), inhale (beats of the slowing into the climax, 0: none), lilt
(the bar's weight on beat 3 / 2), breath (beats cut at a phrase end), push (ms the melody leans ahead of the bass),
inner (the notes under the melody x), cap (the right hand's top velocity), lh_vel (the left hand's level), pedal (ms
the pedal changes after the harmony), end_dyn / end_roll / end_hold (the last chord's mark, roll ms, fermata beats)."""
ORCH_DRAWN = ('texture', 'lead', 'counter')
"""An orchestra section's orchestrator draws (endless/orchestra.py RECORDED); the piece's: 'size'."""
JAZZ_FIELDS = ('lh', 'steps', 'choruses', 'opening', 'quotes', 'over', 'window', 'burst')
LISTS = ('swell', 'steps', 'moves', 'vary')
"""The list-valued keys (one value per phrase / bar)."""


@dataclass
class Arrangement:
    kind: str                                           # 'piano' | 'jazz' | 'orchestra'
    piece: dict = field(default_factory=dict)           # piece-level decisions {key: value}
    sections: dict = field(default_factory=dict)        # {section name: {key: value}}, in play order

    def get(self, section, key, default=None):
        d = self.piece if section is None else self.sections.get(section) or {}
        return d.get(key, default)

    def copy(self) -> 'Arrangement':
        return Arrangement(self.kind, dict(self.piece), {k: dict(v) for k, v in self.sections.items()})


class Dice:
    """Draws through a record (the module docstring): put / pick / chance return the decision to play."""

    def __init__(self, kind: str, given: Arrangement | None = None):
        if given is not None and given.kind != kind:
            raise ValueError(f"a {given.kind} arrangement for a {kind} player")
        self.given = given
        self.out = Arrangement(kind)

    def order(self, drawn: list) -> list:
        """The section list: the record's (replay) or the drawn one."""
        names = list(self.given.sections) if self.given is not None else list(drawn)
        for n in names:
            self.out.sections.setdefault(n, {})
        return names

    def put(self, section, key: str, value):
        """`value` = the dice's; the record's wins when it holds one (None: no decision, nothing stored)."""
        g = self.given.get(section, key) if self.given is not None else None
        if g is not None and not (isinstance(value, list) and len(g) != len(value)):
            value = g
        if value is None or (isinstance(value, list) and not value):
            return value
        (self.out.piece if section is None else self.out.sections.setdefault(section, {}))[key] = value
        return value

    def pick(self, section, key: str, rng, weights):
        from .composer import _pick
        return self.put(section, key, _pick(rng, weights))


# ------------------------------------------------------------------------------------------------ the vocabulary

def kind_of(genre) -> str:
    return genre.plan.get('perform', 'jazz')


def fmt(v, depth: int = 0) -> str:
    """A decision value as a token value: bools 1 / 0, tuples joined by ',' (nested ones by '-')."""
    if isinstance(v, bool):
        return '1' if v else '0'
    if isinstance(v, (tuple, list)):
        return (',' if depth == 0 else '-').join(fmt(x, depth + 1) for x in v)
    return str(v)


def section_specs(genre, layout=None) -> dict:
    """{name: plan entry} of a piano genre's sections in the layout (an entry without 'layouts' plays in every
    layout), in plan order - a name is unique within a layout (Genre's check)."""
    return {s['name']: s for s in genre.plan.get('sections') or ()
            if not s.get('layouts') or layout in s['layouts']}


def fixed(genre, name: str, layout=None) -> dict:
    """A piano section's keys as its plan entry (in the layout) has them - the fixed ones; a drawn {choice: weight}
    (octave, lh_only) is not."""
    sec = section_specs(genre, layout).get(name)
    if sec is None:
        return {}
    return {k: sec[k] for k in PIANO_FIXED + ('octave',) if k in sec and not isinstance(sec[k], dict)}


def values(genre) -> dict:
    """{key: {token value: value}} every decision the genre's players can take ('sections': the section names) - the
    decoder's strict vocabulary (a value is decoded to the plan's own object)."""
    P = genre.plan
    out: dict = {}

    def add(key, vals):
        d = out.setdefault(key, {})
        for v in vals:
            d.setdefault(fmt(v), v)
    if kind_of(genre) in ('piano', 'orchestra'):
        secs = P.get('sections') or []
        add('sections', [s['name'] for s in secs])
        add('layout', (P.get('set') or {}).get('layout') or {})
        add('touch', P.get('touch_span') or {})
        for k in PIANO_FIXED + PIANO_DRAWN:
            if k in ('swell', 'cadenza', 'moves', 'vary', 'key'):      # (below)
                continue
            for s in secs:
                v = s.get(k)
                add(k, v if isinstance(v, dict) else [] if v is None else [v])
        add('climax', (P.get('set') or {}).get('climax') or {})
        add('figures', [n for F in genre.feels.values() for n in (F.get('figures') or {})])
        add('swell', P.get('swell') or {})
        add('cadenza', (True, False))
        add('moves', MOVES)
        if any(s.get('vary') for s in secs):
            from .genres import VARY
            add('vary', VARY)
        add('key', [k for s in secs for w in (s.get('key') or {}).values() for k in w])
        for k in PLAY_KEYS:
            add(k, (P.get('play') or {}).get(k) or {})
        if kind_of(genre) == 'orchestra':
            from ..bandlib.orchestration import TEXTURES
            roles = sorted({r for rs in (P.get('sizes') or {}).values() for r in rs})
            add('size', sorted(P.get('sizes') or {}))
            add('texture', sorted(TEXTURES))
            add('lead', roles)
            add('counter', roles + ['none'])
    elif kind_of(genre) == 'jazz':
        from .perform import CLIMAX
        lh = {'tenths'}
        for F in genre.feels.values():
            if F.get('lh'):
                lh.add(F['lh'])
            for v in (F.get('lh_plan') or {}).values():
                lh.update([v] if isinstance(v, str) else v)
        add('lh', sorted(lh))
        add('steps', ((P.get('head') or {}).get('phrase_touch') or {}).get('steps') or {})
        add('choruses', range(1, 9))
        sp = P.get('solo') or {}
        add('opening', sp.get('opening') or {'motif': 1.0})
        add('quotes', sp.get('quotes') or {2: 1.0})
        add('over', CLIMAX['over'])
        add('window', CLIMAX['window'])
        add('burst', range(0, 16))
    return out


def section_ok(genre, form_parts, name: str, layout=None) -> bool:
    """A section name the genre's players know (piano: a plan['sections'] entry of the layout; jazz: intro / head:<part> / solo /
    out:<part>[v] / tag)."""
    if kind_of(genre) in ('piano', 'orchestra'):
        return name in section_specs(genre, layout)
    if name in ('intro', 'solo', 'tag'):
        return True
    m = re.match(r'^(head|out):(.+?)(v?)$', name)
    return bool(m) and m.group(2) in form_parts and not (m.group(1) == 'head' and m.group(3))
