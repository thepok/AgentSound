"""The orchestrator's desk: write a whole piece's parts into one Score, give it one dynamics map, perform it at the
end - plus the moves every orchestral song wrote by hand: doubling a line (colla parte), tutti hits, natural brass and
timpani on the chord tones, unison blows, held beds, a choir that speaks on time.

    from agentsound.bandlib import orchestra as orch
    o = bands.symphony_orchestra(s)
    sc = orch.Score(s, o, DYNAMICS, seed=1808)       # DYNAMICS = {'intro': [(0, 108), (2, 42, 'step'), ...], ...}
    sc.add('violins1', theme, off=8)                 # (start, dur, pitch[, vel]) notes: velocity from the map
    sc.add(h.under(theme, voicing.STRINGS), off={'violins2': -2, 'violas': -2, 'cellos': 0})   # parts dict
    sc.double(theme, {'flutes': (12, 0), 'oboes': (0, -2)}, dur=0.9)
    sc.hits(h.tutti(), [t + 3, t + 7], length=0.7, sf=True)          # hammered tutti chords
    sc.brass(h, [t, t + 4], length=0.7)                               # natural trumpets, horns, timpani
    sc.perform()                                                      # every role played (orch.perform)

Every helper is a default: each writes plain notes into the buffer, so any note can still be written, moved or
dropped by hand (sc.parts[role] is a list of (start, dur, pitch, vel, articulation)); explicit velocities win over the
map; a role's articulation, offset, length factor and transposition are per call.

DYNAMICS ARE WRITTEN ONCE. The map holds (beat, level[, 'step']) marks per section (or absolute): a level is a
velocity (40 p, 78 mf, 95 f, 115 ff - VEL) or a marking name ('pp' .. 'fff'); between two marks the level moves (a
hairpin, `curve` 'linear' or 'smooth'), a 'step' / 'subito' mark changes at once. A note's velocity = the map at its
start + its part's offset + a seeded +-`jitter` + the bar's accents (downbeat, half bar) + a phrase arc
(humanize.touch's phrasing, per role: `phrasing`), clamped to floor..127. perform() writes them as each section's
dynamics lane; with follow=True a note held through a written crescendo / diminuendo follows the map inside it (the
lane moves while it sounds - a held chord grows with the music instead of staying at its start level).
"""

from __future__ import annotations

import random

from .. import articulation as art
from ..patterns import Clip, as_clip
from ..theory import ComposeError, Key, note as _note

__all__ = ['VEL', 'PHRASING', 'FALLBACK', 'TUTTI_ROLES', 'WINDS8_ROLES', 'UNISON_OCTAVES', 'BED', 'natural_brass',
           'timpani_tuning', 'Score', 'Choir', 'bed', 'double', 'colla_parte', 'hits', 'unison', 'sing', 'swells']

VEL = {'ppp': 16, 'pp': 28, 'p': 40, 'mp': 58, 'mf': 78, 'f': 95, 'ff': 115, 'fff': 127}
"""Dynamic markings -> velocities (the levels orch.perform reads: 40 p, 78 mf, 95 f, 115 ff)."""

PHRASING = {'violins1': 0.9, 'violins2': 0.7, 'violas': 0.5, 'cellos': 0.6, 'basses': 0.4, 'flutes': 0.8,
            'oboes': 0.8, 'clarinets': 0.7, 'bassoons': 0.6, 'horns': 0.5}
"""How much of a phrase's arc (humanize.touch) each role's lines get on top of the map: k x (touch - 60)."""

FALLBACK = {'marcato': 'sustain', 'tremolo': 'sustain', 'pizzicato': 'staccato', 'spiccato': 'staccato'}
"""An articulation a role does not have -> the one it plays instead."""

TUTTI_ROLES = {'flutes': ('v1', 'v2'), 'oboes': ('v2', 'v3'), 'clarinets': ('v3', 'v4'), 'bassoons': ('v6', 'v7'),
               'violins1': ('v1', 'v2'), 'violins2': ('v3', 'v4'), 'violas': ('v5', 'v6'), 'cellos': ('v7',),
               'basses': ('v8',)}
"""Which voices of a voicing.TUTTI chord each section plays (a Classical tutti)."""

WINDS8_ROLES = {'fl1': 'flutes', 'fl2': 'flutes', 'ob1': 'oboes', 'ob2': 'oboes', 'cl1': 'clarinets',
                'cl2': 'clarinets', 'bn1': 'bassoons', 'bn2': 'bassoons'}
"""voicing.WINDS8 voices -> the wind sections (the second player of each pair a little softer)."""

UNISON_OCTAVES = {'violins1': (5, 6), 'violins2': (4, 5), 'violas': (3, 4), 'cellos': (2, 3), 'basses': (1, 2),
                  'flutes': (5, 6), 'oboes': (5,), 'clarinets': (4, 5), 'bassoons': (2, 3), 'horns': (3, 4),
                  'trumpets': (4, 5)}
"""The octaves each section takes in a unison blow (all on one pitch class)."""

_EPS = 1e-6


def natural_brass(key) -> tuple:
    """The natural trumpet's notes in the key's tonic: partials 4 5 6 8 10 12 (in C: C4 E4 G4 C5 E5 G5)."""
    t = Key(key).tonic
    f = 36 + t if t <= 5 else 24 + t
    return tuple(f + i for i in (24, 28, 31, 36, 40, 43))


def timpani_tuning(key) -> dict:
    """Timpani on the tonic and the dominant: {tonic pc: pitch (octave 3), dominant pc: the fifth below it}."""
    t = Key(key).tonic
    tonic = 48 + t
    return {t: tonic, (t + 7) % 12: tonic - 5}


def _pos(x) -> float:
    return float(getattr(x, 'start', x))


def _P(x) -> int:
    return x if isinstance(x, int) else _note(x)


class Score:
    """A whole piece's parts for one band (orch.* presets) with one dynamics map - see the module docs.

    Score(song, band, dynamics=None, *, key=None, seed=0, jitter=3.0, accents=(5, 2), floor=14, phrasing=PHRASING,
          curve='linear', fold=True, fallback=FALLBACK, follow=True)"""

    def __init__(self, song, band, dynamics=None, *, key=None, seed=0, jitter: float = 3.0, accents=(5, 2),
                 floor: int = 14, phrasing=None, curve: str = 'linear', fold: bool = True, fallback=None,
                 follow: bool = True):
        if curve not in ('linear', 'smooth'):
            raise ComposeError(f"Score curve must be 'linear' or 'smooth', got {curve!r}")
        self.song, self.band = song, band
        self.key = Key(key) if key is not None else song.key
        self.rng = random.Random(seed)
        self.jitter, self.accents, self.floor = float(jitter), tuple(accents), int(floor)
        self.phrasing = dict(PHRASING if phrasing is None else phrasing)
        self.curve, self.fold, self.follow = curve, fold, follow
        self.fallback = dict(FALLBACK if fallback is None else fallback)
        self.parts: dict = {}          # role -> [(start, dur, pitch, vel, articulation)]
        self._marks: list = []
        self._f = None
        if dynamics is not None:
            self.mark(dynamics)

    # ------------------------------------------------------------------------------------------ dynamics
    def mark(self, marks, at=0.0) -> 'Score':
        """Add dynamics marks: {section (or name): [(beat in it, level[, 'step'])]} or [(beat, level[, 'step'])]
        relative to `at`. level: a velocity or a marking (VEL); 'step' / 'subito' = at once (else a hairpin)."""
        if isinstance(marks, dict):
            for sec, pts in marks.items():
                self.mark(pts, self.song.at(sec))
            return self
        a = float(self.song.at(at))
        for p in marks:
            if not isinstance(p, (tuple, list)) or len(p) not in (2, 3):
                raise ComposeError(f"Score dynamics: a mark is (beat, level[, 'step']), got {p!r}")
            lv = VEL.get(p[1]) if isinstance(p[1], str) else p[1]
            if lv is None or isinstance(lv, bool) or not isinstance(lv, (int, float)):
                raise ComposeError(f"Score dynamics: level {p[1]!r} is not a velocity or one of {', '.join(VEL)}")
            step = len(p) == 3 and p[2] in ('step', 'subito')
            if len(p) == 3 and not step:
                raise ComposeError(f"Score dynamics: the third element of {p!r} must be 'step' or 'subito'")
            self._marks.append((a + p[0], lv, step))
        self._marks.sort(key=lambda m: (m[0], m[2]))
        from ..romantic import dynamics_factor
        self._f = dynamics_factor(self._marks, self.curve)
        return self

    def level(self, t: float) -> float:
        """The map's level (a velocity) at beat t (mf = 78 without marks)."""
        return 78.0 if self._f is None else self._f(t)

    def phase(self, t: float) -> float:
        """Where t falls in its bar (0..1, the section's meter)."""
        for sec in self.song.sections:
            if sec.start - 1e-6 <= t < sec.end - 1e-6:
                return ((t - sec.start) % sec.beats_per_bar) / sec.beats_per_bar
        return 0.0

    def vel(self, t: float, off: float = 0.0, accent: bool = True) -> int:
        """A velocity at beat t: the map + off + the seeded jitter (+ the bar's accents), clamped floor..127."""
        v = self.level(t) + off + self.rng.uniform(-self.jitter, self.jitter)
        if accent:
            ph = self.phase(t)
            v += self.accents[0] if ph < 0.02 else self.accents[1] if abs(ph - 0.5) < 0.02 else 0
        return max(self.floor, min(127, round(v)))

    def _shape(self, notes, k):
        """Phrasing: humanize.touch's arcs as an offset of k x (touch - 60) on top of the map."""
        if len(notes) < 3 or not k:
            return lambda n: 0.0
        from ..humanize import touch
        shaped = touch(Clip([(n[0], n[1], n[2], 80) for n in notes], length=0), 40, 80, gap='1/4')
        by = {(round(m.start, 4), m.pitch): m.vel for m in shaped}
        return lambda n: k * (by.get((round(n[0], 4), n[2]), 60) - 60)

    # ------------------------------------------------------------------------------------------ writing
    def add(self, role, notes=None, art: str = 'sustain', *, off=0.0, accent: bool = True, dur=1.0, transpose=0,
            sf=(), offs=None, phrasing=None, fig=None, roles=None) -> 'Score':
        """Write notes on a role: (start, dur, pitch[, vel]) tuples or a Clip (song beats). Without a velocity a note
        gets vel(start, off + offs(note), accent) + its phrase arc; `art` its articulation; `dur` x its length (or a
        function of the note); `transpose` semitones; sf: beats of sforzandi (+16, marcato); fig: a figure of
        agentsound.figures played from the notes first ('pulse8', or ('beats', {'every': 2, 'gap': 1.2})).
        A dict {role: notes} writes several roles (a voicing's parts) - all of them, or `roles` in that order; `off`
        / `art` / `transpose` / `dur` / `fig` may then be dicts per role (missing roles: 0 / 'sustain' / 0 / 1 /
        none)."""
        if isinstance(role, dict):
            if isinstance(notes, (str, dict)):           # add(parts, 'staccato', ...): the articulation
                art, notes = notes, None

            def per(x, r, default):
                return x.get(r, default) if isinstance(x, dict) else x
            for r in (roles if roles is not None else list(role)):
                self.add(r, role[r], per(art, r, 'sustain'), off=per(off, r, 0.0), accent=accent,
                         dur=per(dur, r, 1.0), transpose=per(transpose, r, 0), sf=sf, offs=offs, phrasing=phrasing,
                         fig=fig.get(r) if isinstance(fig, dict) else fig)
            return self
        if notes is None:
            raise ComposeError(f"Score.add({role!r}): no notes")
        if fig is not None:
            from ..figures import figure
            kind, opts = (fig, {}) if isinstance(fig, str) else (fig[0], dict(fig[1]) if len(fig) > 1 else {})
            notes = figure(notes, kind, **opts)
        if isinstance(notes, Clip):
            notes = [tuple(n) for n in notes]
        buf = self.parts.setdefault(role, [])
        k = self.phrasing.get(role, 0.0) if phrasing is None else phrasing
        arc = self._shape([n for n in notes if len(n) < 4], k)
        sfs = {round(x, 3) for x in sf}
        for n in notes:
            st, du, p = n[0], n[1], n[2]
            if len(n) > 3:
                v = n[3]
            else:
                o = off + offs(n) if offs else off
                v = min(127, max(self.floor, round(self.vel(st, o, accent) + arc(n))))
            a = art
            if round(st, 3) in sfs:
                v, a = min(127, v + 16), 'marcato'
            buf.append((st, du * (dur(n) if callable(dur) else dur), _P(p) + transpose, v, a))
        return self

    def sing(self, choir, key, notes, *, off=0.0, dur=1.0, offs=None, accent: bool = True,
             phrasing: float = 0.7) -> 'Score':
        """Write a sung line into a Choir (buffered: choir.perform() sings it): velocities from the map like add()
        (off + offs(note), the bar's accents, a phrase arc of `phrasing`), dur x the length (or a function of the
        note: declaimed syllables shorter, legato lines full)."""
        arc = self._shape(notes, phrasing)
        out = []
        for n in notes:
            o = off + offs(n) if offs else off
            v = min(127, max(self.floor, round(self.vel(n[0], o, accent) + arc(n))))
            out.append((n[0], n[1] * (dur(n) if callable(dur) else dur), n[2], v))
        choir.sing(key, out)
        return self

    def double(self, line, roles: dict, *, art: str = 'sustain', at=None, **common) -> 'Score':
        """Double a line (colla parte) in several roles, each {role: shift | (shift, off) | (shift, off, {options})}:
        shift = semitones (12 = an octave up), off = its velocity offset; `common` options for all, a role's own win.
        Buffered (add() options: dur=, sf=, accent= ...) - or with at= (a beat / Section) played now: the line (a
        Clip, its own beats) transposed and vel_add(off), each role with play() (orch.perform options: shapes= ...)."""
        if at is not None:
            for r, spec in roles.items():
                spec = spec if isinstance(spec, tuple) else (spec,)
                c = as_clip(line)
                c = c.transpose(spec[0]) if spec[0] else c
                c = c.vel_add(spec[1]) if len(spec) > 1 and spec[1] else c
                self.play(r, c, at, **{**common, **(spec[2] if len(spec) > 2 else {})})
            return self
        for r, spec in roles.items():
            spec = spec if isinstance(spec, tuple) else (spec,)
            kw = dict(common)
            kw.update(spec[2] if len(spec) > 2 else {})
            self.add(r, line, kw.pop('art', art), off=spec[1] if len(spec) > 1 else kw.pop('off', 0.0),
                     transpose=spec[0], **{k: v for k, v in kw.items() if k != 'off'})
        return self

    def colla_parte(self, parts: dict, roles: dict, **common) -> 'Score':
        """The orchestra doubles the voices: roles {role: (voice | (voices...), off[, transpose[, {options}]])} -
        violins I on the soprano, the basses on the bass an octave down ... (parts: {voice: notes})."""
        for r, spec in roles.items():
            vs = spec[0] if isinstance(spec[0], (tuple, list)) else (spec[0],)
            ns = [n for v in vs for n in parts.get(v, [])]
            kw = dict(common)
            kw.update(spec[3] if len(spec) > 3 else {})
            self.add(r, ns, kw.pop('art', 'sustain'), off=spec[1] if len(spec) > 1 else 0.0,
                     transpose=spec[2] if len(spec) > 2 else 0, **kw)
        return self

    def winds(self, h, *, off=0.0, roles=None, voices=None, mapping=None, second: float = -3, top_shift: int = 12,
              art: str = 'sustain', key=None, tie: bool = True) -> dict:
        """The wind choir's chords: a Harmony voiced on voicing.WINDS8 (its tops `top_shift` up), each pair on its
        section (WINDS8_ROLES; the second player `second` softer); roles= only those sections. Returns the parts."""
        from ..voicing import WINDS8, Harmony, chorale
        h = h if isinstance(h, Harmony) else Harmony(h)
        rows = [(r[0], r[1], None if r[2] is None else _P(r[2]) + top_shift, *r[3:]) for r in h.table]
        p = chorale(rows, h.origin, voices=voices or WINDS8, key=h.key if key is None else key, tie=tie, unison=True)
        mp = mapping or WINDS8_ROLES
        for v, ns in p.items():
            role = mp[v]
            if roles is None or role in roles:
                self.add(role, ns, art, off=off + (second if v.endswith('2') else 0))
        return p

    def hits(self, parts: dict, times, length: float = 0.8, off: float = 0.0, *, roles=None, sf: bool = False,
             mapping=None) -> 'Score':
        """Tutti chords struck at `times`: each section takes its voices (mapping, TUTTI_ROLES) of the chord parts
        sounding there (Harmony.tutti() / any {voice: notes}); marcato with sf=True, else staccato (<= 0.6 beat) or
        sustain."""
        for role, vs in (mapping or TUTTI_ROLES).items():
            if roles is not None and role not in roles:
                continue
            ns = []
            for t in times:
                for v in vs:
                    p = next((n[2] for n in parts.get(v, ()) if n[0] - 1e-6 <= t < n[0] + n[1] - 1e-6), 0) or 0
                    if p:
                        ns.append((t, length, _P(p)))
            self.add(role, ns, 'marcato' if sf else 'staccato' if length <= 0.6 else 'sustain', off=off)
        return self

    def brass(self, h, times, length: float = 0.8, off: float = 0.0, *, horns: bool = True, trumpets: bool = True,
              timpani: bool = True, roll: bool = False, art=None, lead=(6, -2, -7), naturals=None, tuning=None,
              horn_range=(55, 72), horn_centre: int = 64) -> 'Score':
        """Natural brass and timpani on the chords at `times` (h: a Harmony / [(start, dur, chord)]) - only the
        notes the chord holds: the natural trumpets' two highest notes in it (natural_brass(key)), two horn chord
        tones nearest horn_centre, the timpani (tonic / dominant: timpani_tuning(key)) on the root, the tonic or the
        dominant. art: default marcato up to a beat, else sustain; roll=True rolls the timpani over the length.
        lead: velocity offsets on the downbeat / the half bar / elsewhere (the downbeat leads)."""
        from ..voicing import Harmony, info
        tp_notes = tuple(naturals or natural_brass(self.key))
        timp = dict(tuning or timpani_tuning(self.key))
        for t in times:
            sym = h.symbol_at(t + 1e-3) if isinstance(h, Harmony) else _sym_at(h, t + 1e-3)
            if sym is None:
                continue
            ci = info(sym)
            a = art or ('marcato' if length <= 1.0 else 'sustain')
            ph = self.phase(t)
            off_t = off + (lead[0] if ph < 0.02 else lead[1] if abs(ph - 0.5) < 0.02 else lead[2])
            if trumpets:
                tps = [p for p in tp_notes if p % 12 in ci.pcs][-2:]
                self.add('trumpets', [(t, length, p) for p in tps], a, off=off_t - 4)
            if horns:
                hs = sorted({p for p in range(horn_range[0], horn_range[1]) if p % 12 in ci.pcs},
                            key=lambda p: abs(p - horn_centre))[:2]
                self.add('horns', [(t, length, p) for p in hs], a, off=off_t - 2)
            if timpani:
                pcs = [pc for pc in (ci.root, self.key.tonic, (self.key.tonic + 7) % 12) if pc in timp and pc in ci.pcs]
                if pcs:
                    self.add('timpani', [(t, length if roll else 0.5, timp[pcs[0]])], 'roll' if roll else 'hit',
                             off=off_t - 6)
        return self

    def unison(self, t: float, d: float, pc, off: float = 0.0, *, octaves=None, naturals=None, tuning=None) -> 'Score':
        """Every section on one pitch class in its octaves (UNISON_OCTAVES), marcato - the trumpets only on a natural
        note, the timpani rolling when they are tuned to it."""
        pc = (_note(pc + '4') if isinstance(pc, str) else int(pc)) % 12
        tp = {p % 12 for p in (naturals or natural_brass(self.key))}
        timp = dict(tuning or timpani_tuning(self.key))
        for role, octs in (octaves or UNISON_OCTAVES).items():
            if role == 'trumpets' and pc not in tp:
                continue
            self.add(role, [(t, d, 12 * (o_ + 1) + pc) for o_ in octs], 'marcato', off=off)
        if pc in timp:
            self.add('timpani', [(t, d, timp[pc])], 'roll', off=off)
        return self

    def stabs(self, h, at, beats, vel: int = 112, *, timpani=None, low='E2', split=(67, 60, 76, 36, 48)) -> dict:
        """Orchestra stabs played now (at `at`, beats in its frame): strings staccato on the chord at each beat
        (octaves 5 and 4: violins I from split[0] up, violins II split[1]..split[2], violas under split[0]), cellos /
        basses on its bass from `low` and the octave under (split[3] / split[4]), trumpets marcato in octave 4 (vel
        - 6), trombones and horns (- 6 more) an octave lower, timpani 'hit' (+4) on timpani(chord) - a pitch, or
        default the tonic when the chord holds it, else the dominant (timpani_tuning). Returns {role: clip}."""
        rows_str, rows_br, rows_lo, rows_t = [], [], [], []
        tun = timpani_tuning(self.key)
        for t in beats:
            c = h.at(t)
            rows_str += [(t, 0.4, p, vel) for p in c.notes(5)[:3] + c.notes(4)[:3]]
            rows_br += [(t, 0.6, p, vel - 6) for p in c.notes(4)[:3]]
            b = c.bass_note(low=low)
            rows_lo += [(t, 0.5, b, vel), (t, 0.5, b - 12, vel)]
            if timpani is not None:
                tp = timpani(c)
            else:
                tp = next((p for pc, p in tun.items() if pc in c.pcs), None)
            if tp is not None:
                rows_t.append((t, 0.8, _P(tp), min(127, vel + 4)))
        ln = h.length
        parts = {'violins1': [r for r in rows_str if r[2] >= split[0]],
                 'violins2': [r for r in rows_str if split[1] <= r[2] < split[2]],
                 'violas': [r for r in rows_str if r[2] < split[0]],
                 'cellos': [r for r in rows_lo if r[2] >= split[3]],
                 'basses': [r for r in rows_lo if r[2] < split[4]],
                 'trumpets': rows_br,
                 'trombones': [(r[0], r[1], r[2] - 12, r[3]) for r in rows_br],
                 'horns': [(r[0], r[1], r[2] - 12, r[3] - 6) for r in rows_br],
                 'timpani': rows_t}
        arts = {'trumpets': 'marcato', 'trombones': 'marcato', 'horns': 'marcato', 'timpani': 'hit'}
        out = {}
        for role, rows in parts.items():
            if role in self.band.roles:
                out[role] = self.play(role, Clip(rows, length=ln), at, articulations=arts.get(role, 'staccato'))
        return out

    def bed(self, h, at, shapes='swell', *, articulations='auto', roles=None, vel: int = 60, **specs) -> dict:
        """orch.bed on this score: held harmony for several roles now (role=('G4 Eb5', 2, 42) | ('root', 'C2', 44) |
        a Clip; none: the string bed BED at `vel`)."""
        return bed(self, h, at, shapes=shapes, articulations=articulations, roles=roles, vel=vel, **specs)

    def fermata(self, chord, at, beats: float, roles: dict, *, vel: int = 100, start: float = 0.0, length=None,
                **kw) -> dict:
        """A held chord for the whole orchestra, played now (a fermata, the last chord): each role {role: spec |
        (spec, vel) | (spec, vel, {play options})} holds `beats` from `start` (beats in `at`'s frame; length = the
        clips' length): spec = a register (lo, hi) - every tone of `chord` (a symbol / Chord / pitch classes) in it
        - or the pitches themselves ('E4 G#4 B4', per-note 'C4=60'). `kw`: play options for all (shapes='dim',
        articulations= ...). Returns {role: clip}."""
        from ..automation import hold
        from ..theory import chord as _chord
        pcs = set(chord) if isinstance(chord, (set, frozenset, list, tuple)) else set(
            (_chord(chord) if isinstance(chord, str) else chord).pcs)
        out = {}
        for role, spec in roles.items():
            spec = spec if isinstance(spec, tuple) and len(spec) in (2, 3) and not isinstance(spec[0], int) \
                and not (isinstance(spec[0], str) and isinstance(spec[1], str)) else (spec,)
            what = spec[0]
            if isinstance(what, tuple):
                what = [p for p in range(_P(what[0]), _P(what[1]) + 1) if p % 12 in pcs]
            v = spec[1] if len(spec) > 1 else vel
            clip = hold(what, beats, v, at=start, length=length)
            out[role] = self.play(role, clip, at, **{**kw, **(spec[2] if len(spec) > 2 else {})})
        return out

    # ------------------------------------------------------------------------------------------ playing
    def seed(self, role: str, at=0.0) -> int:
        """The performance seed of a role placed at `at`: its name's letters + the placement beat."""
        return sum(map(ord, role)) + int(self.song.at(at))

    def play(self, role: str, clip, at=0.0, **kw) -> Clip:
        """Play a part now (orch.perform with the score's seed rule): the direct way, no buffer."""
        from .orchestra import perform
        kw.setdefault('seed', self.seed(role, at))
        return perform(self.band, role, clip, at, **kw)

    def perform(self, roles=None, *, fold=None, fallback=None, follow=None, **kw) -> dict:
        """Play the buffered parts: each role's notes grouped by articulation (one it lacks -> `fallback`), folded
        into its range by octaves (fold), performed by orch.perform at the score's seed; follow=True lets held notes
        follow the dynamics map inside them. Returns {role: the clip played}."""
        from .orchestra import perform
        fold = self.fold if fold is None else fold
        fb = self.fallback if fallback is None else fallback
        follow = self.follow if follow is None else follow
        info = self.band.info
        out = {}
        for role, notes in self.parts.items():
            if roles is not None and role not in roles:
                continue
            have = set(info.get('articulations', {}).get(role) or ())
            rng = info.get('range', {}).get(role)
            lo_, hi_ = (_note(x) for x in rng) if (fold and rng) else (0, 127)
            groups: dict = {}
            for st_, du, p, v, a in notes:
                while p > hi_:
                    p -= 12
                while p < lo_:
                    p += 12
                if fb is not False and have and a not in have:
                    a = fb.get(a, 'sustain')
                groups.setdefault(a, []).append((st_, du, p, v))
            clip = None
            for a, ns in groups.items():
                c = art.articulate(Clip(ns, length=0), a)
                clip = c if clip is None else clip | c
            if clip is None:
                continue
            opts = dict(kw)
            if follow and self._f is not None:
                opts.setdefault('follow', self.level)
            out[role] = perform(self.band, role, clip, 0, articulations=None, seed=self.seed(role), **opts)
        return out


def _sym_at(harm, t):
    for s, d, c in harm:
        if s - 1e-6 <= t < s + d - 1e-6:
            return c if isinstance(c, str) or c is None else c.symbol
    return None


# ---------------------------------------------------------------------------------------------- beds

BED = {'violins1': ('G4 D5', 2), 'violins2': ('D4 A4', 2), 'violas': ('A3 E4', 2), 'cellos': ('root', 'C3'),
       'basses': ('root', 'C2')}
"""orch.bed's default string bed: two divisi voices per violin / viola section in their middle registers, cellos and
basses on the roots."""


def bed(score, h, at, *, shapes='swell', articulations='auto', roles=None, vel: int = 60, **specs) -> dict:
    """Held harmony for several roles in one call (a section's pad / the strings' bed), each role=
      ('G4 Eb5', 2, 42)         h.voice(register, voices, vel): divisi chord tones in a register
      ('root', 'C2', 44)        h.bass('root', low=, vel=): the chord roots
      a Clip                    as written
    played with score.play(role, clip, at, shapes=, articulations=) in the order given; without specs the roles
    (default the five string sections) take BED at `vel`. score: an orch.Score (or a band: a Score is made for it).
    Returns {role: clip}."""
    if not isinstance(score, Score):
        score = Score(score.song, score)
    if not specs:
        names = roles if roles is not None else tuple(BED)
        specs = {r: BED[r] + (vel,) for r in names if r in BED and r in score.band.roles}
    out = {}
    for role, spec in specs.items():
        if isinstance(spec, Clip):
            c = spec
        elif isinstance(spec, tuple) and spec and spec[0] == 'root':
            c = h.bass('root', low=spec[1], vel=spec[2])
        elif isinstance(spec, tuple) and len(spec) == 3:
            reg = spec[0].split() if isinstance(spec[0], str) else spec[0]
            c = h.voice(reg, spec[1], spec[2])
        else:
            raise ComposeError(f"bed: {role}= takes ('G4 Eb5', voices, vel), ('root', low, vel) or a Clip, "
                               f"got {spec!r}")
        out[role] = c
        score.play(role, c, at, shapes=shapes, articulations=articulations)
    return out


def double(score, line, roles: dict, **kw) -> 'Score':
    """orch.double(sc, line, {role: shift | (shift, off[, {options}])}, at=None, ...) = Score.double."""
    return score.double(line, roles, **kw)


def colla_parte(score, parts: dict, roles: dict, **kw) -> 'Score':
    """orch.colla_parte(sc, parts, {role: (voice(s), off[, transpose[, {options}]])}) = Score.colla_parte."""
    return score.colla_parte(parts, roles, **kw)


def hits(score, parts: dict, times, length: float = 0.8, off: float = 0.0, **kw) -> 'Score':
    """orch.hits(sc, h.tutti(), times, ...) = Score.hits: tutti chords struck at `times`."""
    return score.hits(parts, times, length, off, **kw)


def unison(score, t: float, d: float, pc, off: float = 0.0, **kw) -> 'Score':
    """orch.unison(sc, t, d, 'C', ...) = Score.unison: every section on one pitch class in octaves."""
    return score.unison(t, d, pc, off, **kw)


# ---------------------------------------------------------------------------------------------- the choir

class Choir:
    """A sampled choir made to speak on time. Choir samples answer slowly at low velocity (the VPO choirs' attack is
    ~0.6 s x (1 - vel / 127): a p answer needs 0.4 s), so the notes SING at a speaking velocity and the written
    dynamics move to a lane - every note keeps its written level and its arc, only the onset changes:
      lane='expression' (the epic's): velocity `speak` for every note, the written level as speak-relative gain
        (vel / speak, at least `floor`) on 'instrument.expression', moved over the `ramp_ms` before each onset;
      lane='dynamics' (the requiem's): velocity speak + (vel - 70) x `spread` (within `vel_range`), the level
        ((vel / 127) ** curve) on 'instrument.dynamics' `pre_s` before each onset, a messa di voce on notes of
        `swell_s` and more; notes start `lead_s` early (long / short) and are humanized (humanize_ms); `gate`
        (a span (a, b)) parts the syllables there on 'expression' (declaimed, not a vowel pad).
    speak(track, notes) plays at once (song beats); sing(key, notes) buffers for perform(); lane(key, points) adds
    expression points (entries, swells); write() / perform() writes the lanes (one automation per lane and track).
    """

    def __init__(self, song, tracks=None, *, lane: str = 'expression', speak: int = 120, spread: float = 0.15,
                 centre: int = 70, vel_range=(96, 124), floor: float = 0.12, ramp_ms: float = 80.0,
                 lead_s=(0.07, 0.035), long_s: float = 0.35, humanize_ms: float = 10.0, pre_s: float = 0.12,
                 curve: float = 1.6, low: float = 0.08, swell_s: float = 2.4, gate=None):
        if lane not in ('expression', 'dynamics'):
            raise ComposeError(f"Choir lane must be 'expression' or 'dynamics', got {lane!r}")
        self.song, self.tracks, self.mode = song, dict(tracks or {}), lane
        self.speak_vel, self.spread, self.centre, self.vel_range = speak, spread, centre, tuple(vel_range)
        self.floor, self.ramp_ms, self.lead_s, self.long_s = floor, ramp_ms, tuple(lead_s), long_s
        self.humanize_ms, self.pre_s, self.curve, self.low, self.swell_s = humanize_ms, pre_s, curve, low, swell_s
        self.gate = gate
        self.sung: dict = {}          # key -> [(start, dur, pitch, vel)] (buffered)
        self.expr: dict = {}          # key -> expression points

    def _track(self, key):
        return self.tracks.get(key, key) if not hasattr(key, 'automate') else key

    def _key(self, track):
        if hasattr(track, 'automate'):
            self.tracks.setdefault(track.id, track)
        return getattr(track, 'id', track)

    def speak(self, track, notes) -> 'Choir':
        """Play notes (song beats) now at the speaking velocity; their written levels go to the expression lane."""
        notes = sorted(as_clip(notes) if not isinstance(notes, (list, tuple)) else as_clip(Clip(notes, length=0)),
                       key=lambda n: n.start)
        tr = self._track(track)
        tr.play(Clip([(n.start, n.dur, n.pitch, self.speak_vel) for n in notes], length=0), 0)
        lane = self.expr.setdefault(self._key(tr), [])
        onsets: dict = {}
        for n in notes:
            onsets[round(n.start, 4)] = max(onsets.get(round(n.start, 4), 0), n.vel)
        for t, v in sorted(onsets.items()):
            d = self.ramp_ms / 1000.0 * self.song.tempo_at(t) / 60.0
            e = max(self.floor, min(1.0, v / self.speak_vel))
            if lane and t - d <= lane[-1][0] + 1e-4:
                continue                                 # chords / humanized voices of one onset: the first rules
            lane += [(t - d, lane[-1][1] if lane else e), (t - 0.3 * d, e)]
        return self

    def lane(self, key, points) -> 'Choir':
        """Add expression points (beat, value[, curve]) to a voice's lane (an entry's lift, a swell)."""
        self.expr.setdefault(self._key(key), []).extend(points)
        return self

    def swell(self, key, notes, a: float, b: float, period: float, lo: float = 0.65) -> 'Choir':
        """A sung line that breathes (swells(): one swell per `period` beats from a to b) on a voice's lane."""
        return self.lane(key, swells(notes, a, b, period, lo))

    def last(self, key) -> float:
        """The lane's last value (1.0 when empty)."""
        ex = self.expr.get(self._key(key))
        return ex[-1][1] if ex else 1.0

    def sing(self, key, notes, *, voice=None) -> 'Choir':
        """Buffer written notes (start, dur, pitch, vel) for perform() (a Score's sing() does it with the map)."""
        self.sung.setdefault(key, []).extend(tuple(n[:4]) for n in notes)
        return self

    def write(self) -> 'Choir':
        """Write the expression lanes of the tracks spoken so far (speak())."""
        for key, ex in self.expr.items():
            if ex:
                self._track(key).automate('instrument.expression', ex)
        return self

    def perform(self) -> 'Choir':
        """Play the buffered (sing()) notes - started early, humanized, at the speaking velocity - and write each
        track's lanes: expression (the lane() points + the syllable gate) and dynamics (the written levels)."""
        s = self.song
        for key, notes in self.sung.items():
            tr = self._track(key)
            notes.sort()
            played = []
            for st, du, p, v in notes:
                bpm = s.tempo_at(st)
                lead = (self.lead_s[0] if du * 60 / bpm >= self.long_s else self.lead_s[1]) * bpm / 60.0
                a = max(0.0, st - lead)
                sv = self.speak_vel + round((v - self.centre) * self.spread)
                played.append((a, du + (st - a), p, max(self.vel_range[0], min(self.vel_range[1], sv))))
            pc = art.humanize_starts(Clip(played, length=0), s.tempo, self.humanize_ms, seed=len(key))
            tr.play(pc, 0)
            ex = list(self.expr.get(key, []))
            if self.gate is not None:
                ex += _gate_points(s, pc, self.gate)
            if ex:
                ex.sort(key=lambda p: p[0])
                tr.automate('instrument.expression', ex)
            tr.automate('instrument.dynamics', self._levels(notes))
        return self

    def _levels(self, notes) -> list:
        s = self.song
        lane: list = []
        onsets: dict = {}
        for st, du, p, v in notes:
            k = round(st, 3)
            if k not in onsets or onsets[k][1] < v:
                onsets[k] = (du, v)
        for st in sorted(onsets):
            du, v = onsets[st]
            x = max(self.low, min(1.0, (v / 127.0) ** self.curve))
            bpm = s.tempo_at(st)
            pre = self.pre_s * bpm / 60.0
            if lane and st - pre <= lane[-1][0] + 1e-4:
                continue
            lane.append((st - pre, x, 'smooth'))
            if du * 60 / bpm >= self.swell_s:                   # messa di voce on the long notes
                lane.append((st + du * 0.5, min(1.0, x + 0.07), 'smooth'))
                lane.append((st + du * 0.9, max(self.low, x - 0.08), 'smooth'))
        return lane


def sing(track, notes, *, lane: str = 'expression', song=None, swell=None, **opts) -> 'Choir':
    """One sung line on a choir track in one call (an orch.Choir for it, lanes written): lane='expression' speaks it
    now (the epic's recipe: velocity `speak`, the written level on 'expression'); lane='dynamics' sings it with the
    requiem's (speaking velocity +- spread, the level on 'dynamics', early starts, `gate=(a, b)` syllables).
    swell=(a, b, period[, lo]) lets it breathe. notes: (start, dur, pitch, vel) in song beats / a Clip. Choir options
    (speak=, ramp_ms=, lead_s= ...) pass through. Several calls on one track: use a Choir (one lane per track)."""
    ch = Choir(song or track._song, {track.id: track}, lane=lane, **opts)
    if lane == 'expression':
        ch.speak(track, notes)
    else:
        ch.sing(track.id, [tuple(n)[:4] for n in notes])
    if swell:
        ch.swell(track.id, [tuple(n) for n in notes], *swell)
    return ch.write() if lane == 'expression' else ch.perform()


def swells(notes, a: float, b: float, period: float, lo: float = 0.65) -> list:
    """Expression points for a line that breathes: from `a` to `b`, one swell per `period` beats - soft at the start,
    full on the phrase's highest note, soft again at its end (lo 0.65 = ~7.5 dB of swell) - then back to 1."""
    pts = [(a - 0.3, 1.0), (a - 0.05, lo)]
    w = a
    while w < b - 1e-6:
        e = min(b, w + period)
        inside = [n for n in notes if w - 1e-6 <= n[0] < e - 1e-6]
        peak = max(inside, key=lambda n: (n[2], -n[0]))[0] if inside else (w + e) / 2
        peak = min(max(peak, w + 0.25 * (e - w)), w + 0.75 * (e - w))
        pts += [(peak, 1.0, 'smooth'), (e - 0.05, lo, 'smooth')]
        w = e
    pts.append((b + 0.2, 1.0, 'smooth'))
    return pts


def _gate_points(s, pc, span, *, legato_s: float = 0.09, fall_s: float = 0.05, depth: float = 0.4) -> list:
    """Syllables, not a vowel pad: between two onsets in `span` with a gap, the expression falls to `depth` over
    `fall_s` after the note ends and opens again on the next attack (the sample's release would join them)."""
    ex = []
    ons = sorted({round(n.start, 4) for n in pc if span[0] <= n.start < span[1]})
    for i, a in enumerate(ons[:-1]):
        end = max(n.start + n.dur for n in pc if round(n.start, 4) == a)
        nxt = ons[i + 1]
        spb = s.tempo_at(a) / 60.0                         # beats per second
        if nxt - end < legato_s * spb:                     # legato: no gap to part
            continue
        fall = min(fall_s * spb, 0.4 * (nxt - end))
        ex += [(end, 1.0), (end + fall, depth, 'smooth'), (nxt - 0.004 * spb, depth), (nxt + 0.02 * spb, 1.0, 'smooth')]
    return ex
