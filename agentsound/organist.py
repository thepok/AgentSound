"""The organist: an organ is played without touch dynamics - its expression is ARTICULATION (how long each key stays
down against the next one: legato, ordinary touch, detache, staccato), TIME (agogic accents, breaths before cadences
and big chords, ritardandi, the room's ring), REGISTRATION (stops per section, manual changes, the echo) and the SWELL
box. This player turns written voices into that performance on the church_organ band (bandlib/orchestra.py).

    from agentsound import organist, organ_vocab as ov
    b = bands.church_organ(s, registers=('flute', 'cornet'))
    v = ov.satb(ov.harmonize(tune, chart, s.key), tune, s.key)
    organist.perform(s, b, [organist.Voice(v['S'], 'principal', name='S'), organist.Voice(v['A'], 'principal', 'A'),
                            organist.Voice(v['T'], 'principal', 'T'), organist.Voice(v['B'], 'pedal', 'B')],
                     phrases=[16, 32], seed=3)
    orch.swell(b, [(0, 0.3), (8, 1.0, 'smooth')])                      # the swell box (Svallverk roles)

A Voice is ONE line (or a stream of block chords: kind='chords', or figuration: kind='figure') on ONE role (a
registration of band.info['division']'s manual / the pedal); a voice that changes manual is two voices. Notes are
(start, dur, pitch) in song beats as WRITTEN (legato values); perform():
  * ornaments (Voice.ornaments {note index: 'trill' | 'mordent' | 'prall' | 'turn'}) realised the organist's way
    (ORNAMENTS: a cadential trill from the upper note at ~8-10 notes / s ending in a turn; a mordent / turn quick on the
    beat) - the only place where one hand runs apart from the other;
  * TIME: one body gesture (humanize.BODIES['organ'] through humanize.gesture / follow_plan - the shared primitive)
    over the top manual line that every voice and the pedal follow, an agogic accent on the bar's downbeat (the
    cluster a little late, the note sounding a little longer: AGOGIC - an organ cannot accent by velocity), a breath
    before every phrase start and every big chord (BREATH: the keys up early, the next onset a little late), every
    onset cluster struck together (one common jitter, CLUSTER_MS);
  * ARTICULATION per voice (TOUCH: the silence before the next note as a share of the note, drawn per note within the
    style's range and clamped; repeated pitches always re-struck - a key must come up), 'auto' by the voice's note
    values at the local tempo (TOUCH_AUTO);
  * REGISTRATION seams: where a voice's role changes (or a section asks for it), the keys come up the registrant's
    time before (REGISTRANT: a piston 'piston', a manual change 'hand', drawn stops 'stops');
  * the keys: one key per pitch per role (two voices meeting on a pitch hold ONE pipe), every note at ORGAN_VEL;
  * checks: two roles of one division never sound at once (one manual, one registration: ComposeError).
The played voices are recorded on the song (song.organ_voices: written + played notes per voice, for the scores and
the packets)."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from . import pianist
from .humanize import BODIES, body_profile, follow_plan, gesture
from .patterns import Clip, seed_int
from .theory import ComposeError

__all__ = ['ORGAN_VEL', 'TOUCH', 'TOUCH_AUTO', 'AGOGIC', 'BREATH', 'REGISTRANT', 'RING', 'ORNAMENTS', 'CLUSTER_MS',
           'CLUSTER_TOL_MS',
           'HAND', 'RESTRIKE_MS', 'Voice', 'perform', 'touch_of', 'articulate', 'ring_gaps', 'division_clashes',
           'parallel_motion']

_EPS = 1e-6

ORGAN_VEL = 100
"""Every key at one velocity: the organ has no touch dynamics (the pipe speaks at its level whatever the finger
does) - loudness is the registration and the swell box."""

TOUCH = {
    # style -> the silence before the next note of the voice: a share of the note's length drawn from 'share' and
    # clamped to 'ms' (lo, hi) - or, where 'share' is 0, drawn straight from 'ms' (negative = the keys overlap);
    # 'repeat' (lo, hi) ms: a repeated pitch always comes up this long at least (a key must rise to speak again)
    'legato': {'share': (0.0, 0.0), 'ms': (-8.0, 4.0), 'repeat': (75.0, 120.0)},
    'cantabile': {'share': (0.0, 0.0), 'ms': (-14.0, 0.0), 'repeat': (95.0, 150.0)},
    'fast': {'share': (0.06, 0.16), 'ms': (8.0, 45.0), 'repeat': (35.0, 70.0)},
    'ordinary': {'share': (0.12, 0.24), 'ms': (35.0, 210.0), 'repeat': (60.0, 220.0)},
    'detache': {'share': (0.3, 0.45), 'ms': (60.0, 420.0), 'repeat': (70.0, 420.0)},
    'staccato': {'share': (0.5, 0.65), 'ms': (90.0, 650.0), 'repeat': (90.0, 650.0)},
}
"""Organ articulation (Laukvik, 'Historical performance practice in organ playing'; the 'ordinary touch' of the
baroque): the keys' silences, drawn per note."""

TOUCH_AUTO = ((0.2, 'fast'), (0.42, 'ordinary'), (0.95, 'ordinary'), (math.inf, 'legato'))
"""touch='auto': the voice's median note length in SECONDS -> the style (16ths in a toccata run light and connected,
8ths / quarters in ordinary touch, long notes legato). A voice of kind 'chords' plays one step more detached up to
quarter-note chords (a festive accompaniment), legato above."""

AGOGIC = {'late_ms': (6.0, 15.0), 'stretch_ms': (10.0, 24.0), 'lift_ms': (20.0, 45.0)}
"""The organist's accent: the bar's downbeat cluster `late_ms` late, the cluster after it `stretch_ms` late (the
downbeat note itself sounds longer: the agogic accent), and the voices in ordinary / detached touch lift `lift_ms`
before it (the articulation silence that makes the downbeat speak)."""

BREATH = {'phrase': (140.0, 320.0), 'big': (110.0, 240.0), 'late': 0.3}
"""Breaths: before a phrase start (perform phrases=) and a big chord (5+ keys after a thinner texture) the sounding
keys come up `phrase` / `big` ms early; the new onset comes `late` x that breath late."""

REGISTRANT = {'piston': (130.0, 280.0), 'hand': (60.0, 140.0), 'stops': (420.0, 800.0)}
"""The time the keys come up before a registration change: a combination piston, the hands moving to another
manual, stops drawn by hand (an assistant's)."""

RING = (1.4, 2.6)
"""Seconds of silence the church needs after a section's final chord before the next section begins (the plans
leave it; ring_gaps() measures it)."""

ORNAMENTS = {'trill': {'rate': (7.5, 10.0), 'start': 'upper', 'max_sec': 1.6}, 'mordent': {'ms': (55.0, 80.0)},
             'prall': {'ms': (50.0, 75.0)}, 'turn': {'ms': (75.0, 110.0)}}
"""Ornaments on the organ: pipes speak slower than strings - a trill of 7.5-10 notes / s starting from the upper
note (the baroque cadential trill) ending in a turn; a mordent / pralltriller / turn quick on the beat."""

CLUSTER_MS = 1.8
"""Every onset cluster (the notes written together, all voices) moves by ONE triangular jitter of +-this: chords are
struck as one; only ornaments run apart."""

HAND = {'sigma_ms': 3.0, 'spread_ms': (0.0, 6.0)}
"""On top of the cluster: each registration (a hand / the feet) is off by its own gaussian (sigma_ms) per onset, the
notes of a chord of 3+ in one hand spread by up to spread_ms (songs/toccata-tenebrae: hands +-2-7 ms, chords 0-10)."""

RESTRIKE_MS = 45.0
"""One pipe per key: a pitch struck again on a role while another voice still holds it releases ~this before the new
attack (the key must rise to speak again)."""


@dataclass
class Voice:
    """One line on one registration (role). kind: 'line' (a contrapuntal voice), 'chords' (block chords: notes that
    start together are one gesture), 'figure' (figuration: a toccata's 16ths). touch: a TOUCH style or 'auto'.
    ornaments: {index of a note in `notes` (sorted by start): 'trill' | 'mordent' | 'prall' | 'turn'}. accel: (from,
    to) note-length factors across the voice (a run that rushes into its goal: (1.2, 0.85)), its span kept. Ornament
    keys may be beats (a float: the note starting there) instead of indices. breathe=False: the voice keeps its notes
    into a phrase start (an accompaniment's pickup under a cantus that breathes)."""
    notes: list
    role: str
    name: str = ''
    kind: str = 'line'
    touch: str = 'auto'
    ornaments: dict = field(default_factory=dict)
    accel: tuple | None = None
    breathe: bool = True

    def sorted(self) -> list:
        ns = sorted((float(a), float(b), int(c)) for a, b, c in self.notes)
        if not self.accel or len(ns) < 2:
            return ns
        starts = sorted({n[0] for n in ns})
        a0, a1 = self.accel
        t0, t1 = starts[0], max(n[0] + n[1] for n in ns)
        iois = [b - a for a, b in zip(starts, starts[1:])] + [t1 - starts[-1]]
        f = [a0 + (a1 - a0) * i / max(1, len(iois) - 1) for i in range(len(iois))]
        k = sum(iois) / sum(x * y for x, y in zip(iois, f))
        new, t = {}, t0
        for s_, x, y in zip(starts, iois, f):
            new[s_] = (t, x * y * k / x if x > _EPS else 1.0)
            t += x * y * k
        return [(new[s_][0], du * new[s_][1], p) for s_, du, p in ns]


CLUSTER_TOL_MS = 20.0
"""Played onsets this close (ms) are one chord (a spread chord, the hands' offsets): no articulation gap between
them."""


def _tri(r: random.Random) -> float:
    return r.random() + r.random() - 1.0


def _u(r: random.Random, lohi) -> float:
    lo, hi = lohi
    return lo + (hi - lo) * r.random()


def touch_of(voice: Voice, bpm_at) -> str:
    """The voice's articulation style (TOUCH_AUTO by its median note length in seconds when touch='auto')."""
    if voice.touch != 'auto':
        if voice.touch not in TOUCH:
            raise ComposeError(f"organist: touch must be 'auto' or one of {', '.join(TOUCH)}, got {voice.touch!r}")
        return voice.touch
    ns = voice.sorted()
    if not ns:
        return 'legato'
    starts = sorted({n[0] for n in ns})
    iois = [b - a for a, b in zip(starts, starts[1:]) if b - a > _EPS] or [ns[0][1]]
    iois.sort()
    med = iois[len(iois) // 2]
    sec = med * 60.0 / bpm_at(starts[len(starts) // 2])
    style = next(s for lim, s in TOUCH_AUTO if sec < lim)
    if voice.kind == 'chords' and sec < 1.2:
        style = {'fast': 'ordinary', 'ordinary': 'detache', 'legato': 'ordinary'}.get(style, style)
    return style


def articulate(notes, style: str, bpm_at, rng: random.Random, next_onsets=None) -> list:
    """The sounding lengths of a voice's notes (start, dur, pitch) in `style` (TOUCH): each note ends the drawn
    silence before the next onset of the voice (a chord's notes: the next chord), a repeated pitch at least the
    'repeat' silence; the last note keeps its written end. next_onsets: the PLAYED onsets (beats) the silences are
    measured to (default the notes' own)."""
    T = TOUCH[style]
    ns = list(notes)
    starts = sorted({round(n[0], 6) for n in ns})
    out = []
    for st, du, p in ns:                              # (the input's order kept)
        tol = CLUSTER_TOL_MS / 60000.0 * bpm_at(st)    # (a spread chord's notes: one onset)
        later = [x for x in starts if x > st + tol]
        nxt = later[0] if later else None
        end = st + du
        if nxt is None or nxt > end + 0.26:
            out.append((st, du, p))                  # a phrase end / a held note: as written (breaths do the rest)
            continue
        bpm = bpm_at(st)
        note_ms = (nxt - st) * 60000.0 / bpm
        if T['share'][1] > 0:
            gap = min(max(_u(rng, T['share']) * note_ms, T['ms'][0]), T['ms'][1])
        else:
            gap = _u(rng, T['ms'])
        rep = any(abs(n[0] - nxt) < tol and n[2] == p for n in ns)
        if rep:
            gap = max(gap, _u(rng, T['repeat']))
        gap = min(gap, 0.7 * note_ms)
        e = nxt - gap / 60000.0 * bpm
        out.append((st, max(0.03, e - st), p))
    return out


def _realise(v: Voice, bpm_at, key, rng) -> list:
    """The voice's notes with its ornaments written out (pianist's moves, the organ's rates): [(start, dur, pitch,
    ornament?)] - ornament notes carry True (they keep their own small timing)."""
    ns = v.sorted()
    out = []
    orn = {}
    for k, kind in v.ornaments.items():          # (an int: the note's index; a float: the beat it starts on)
        if isinstance(k, float):
            beat = k
            k = next((i for i, n in enumerate(ns) if abs(n[0] - beat) < 1e-3), None)
            if k is None:
                raise ComposeError(f"organist: voice {v.name!r} has no note starting at beat {beat:g} to ornament")
        orn[k] = kind
    for i, (st, du, p) in enumerate(ns):
        kind = orn.get(i)
        if kind is None:
            out.append((st, du, p, False))
            continue
        bpm = bpm_at(st)
        try:
            if kind == 'trill':
                O = ORNAMENTS['trill']
                c = pianist.trill(p, du, bpm, key=key, rate=_u(rng, O['rate']), start=O['start'],
                                  max_sec=O['max_sec'], legato=1.0, wobble_ms=3.0, seed=rng.random(), at=st)
            elif kind in ('mordent', 'prall'):
                c = pianist.mordent(p, du, bpm, upper=kind == 'prall', key=key, ms=_u(rng, ORNAMENTS[kind]['ms']),
                                    at=st)
            elif kind == 'turn':
                c = pianist.turn(p, du, bpm, key=key, chromatic=False, ms=_u(rng, ORNAMENTS['turn']['ms']), at=st)
            else:
                raise ComposeError(f"organist: unknown ornament {kind!r} (trill, mordent, prall, turn)")
        except ComposeError:
            out.append((st, du, p, False))           # (too short for the figure: the plain note)
            continue
        cn = sorted(c, key=lambda n: n.start)
        for j, n in enumerate(cn):
            out.append((n.start, n.dur, n.pitch, j > 0))
    return out


def division_clashes(band, voices) -> list:
    """[(role a, role b, beat)] where two roles of one division (band.info['division']) sound at once."""
    div = band.info.get('division') or {}
    spans = {}
    for v in voices:
        for st, du, p in v.notes:
            spans.setdefault(v.role, []).append((st, st + du))
    out = []
    roles = sorted(spans)
    for i, a in enumerate(roles):
        for b in roles[i + 1:]:
            if div.get(a) is None or div.get(a) != div.get(b):
                continue
            for s0, e0 in spans[a]:
                hit = next((s1 for s1, e1 in spans[b] if s1 < e0 - 0.05 and e1 > s0 + 0.05), None)
                if hit is not None:
                    out.append((a, b, max(s0, hit)))
                    break
    return out


def perform(song, band, voices, *, body='organ', phrases=(), seams=None, key=None, seed=0, check: bool = True,
            agogic: bool = True, record: bool = True) -> dict:
    """Play written voices on the organ band (see the module docstring): returns {role: [played Note]} and records
    song.organ_voices (+= one entry per voice: name, role, kind, touch, written, played). phrases: beats where
    phrases start (a breath before each; the body's phrase marks); seams: {beat: 'piston' | 'hand' | 'stops'} - a
    registration change there (default: every beat where a role starts or stops sounding, 'piston' on the same
    division, 'hand' between manuals). Deterministic from seed. Call it once per song with every voice (the gesture
    and the clusters are the whole texture's), after the tempo plan is set."""
    voices = [v for v in voices if v.notes]
    for v in voices:
        if v.role not in band.roles:
            raise ComposeError(f"organist: band has no role {v.role!r} (roles: {', '.join(band.roles)}; "
                               f"church_organ(registers=...) adds more)")
    if check:
        bad = division_clashes(band, voices)
        if bad:
            a, b, t = bad[0]
            raise ComposeError(f"organist: '{a}' and '{b}' are registrations of one manual "
                               f"({band.info['division'][a]}) and sound together at beat {t:g} - put one on another "
                               f"manual")
    rng = random.Random(seed_int(f"organist:{seed}"))
    key = key or getattr(song, 'key', None)
    tm = song.tempo_map()

    def bpm_at(b):
        return tm.bpm_at(b)
    B = body_profile(body) if body is not None else None
    # ---- ornaments written out; the clusters (onset times over every voice)
    real = [_realise(v, bpm_at, key, random.Random(seed_int(f"orn:{seed}:{i}"))) for i, v in enumerate(voices)]
    onsets = sorted({round(n[0], 4) for r in real for n in r if not n[3]})
    shift = {t: 0.0 for t in onsets}                 # ms late per written onset
    # the body: a gesture over the top manual line, every voice follows it
    if B is not None and onsets:
        div = band.info.get('division') or {}
        top = {}
        for v, r in zip(voices, real):
            if div.get(v.role) == 'pedal':
                continue
            for st, du, p, orn in r:
                if not orn and p > top.get(round(st, 4), (-1, 0))[0]:
                    top[round(st, 4)] = (p, du)
        if top:
            lead = Clip._raw([_note(t, du, p) for t, (p, du) in sorted(top.items())], max(top) + 4)
            mg = song.meter_grid()

            def bar_of(beat):
                kk = math.floor(mg.bar_at(beat) + 1e-6)
                from . import tempo as _tempo
                return beat - mg.bar_start(kk), _tempo.beats_per_bar(mg.meter_at(beat))
            ends = [x.end for x in song.sections]
            _, motion = gesture(lead, B, bpm_at, marks=list(phrases), ends=ends, busy=song._tempo_plan.shapes,
                                bar_of=bar_of)
            allc = Clip._raw([_note(t, 1.0, 60) for t in onsets], onsets[-1] + 4)
            plan = follow_plan(allc, motion, B, bpm_at, bar_of=bar_of)
            for t, (ms, _) in zip(onsets, plan):
                shift[t] += ms
    # agogic accents on the downbeats; breaths before phrases and big chords; one jitter per cluster
    mg = song.meter_grid()
    density = {}
    for r in real:
        for st, du, p, orn in r:
            if not orn:
                density[round(st, 4)] = density.get(round(st, 4), 0) + 1
    breath_at = {}
    ph = sorted(float(x) for x in phrases)
    for i, t in enumerate(onsets):
        kk = mg.bar_at(t)
        on_bar = abs(kk - round(kk)) < 1e-4
        if agogic and on_bar and i:
            shift[t] += _u(rng, AGOGIC['late_ms'])
            if i + 1 < len(onsets):
                nxt = onsets[i + 1]
                if (nxt - t) * 60000.0 / bpm_at(t) < 900.0:
                    shift[nxt] += _u(rng, AGOGIC['stretch_ms'])
        is_phrase = any(abs(t - x) < 0.02 for x in ph) and i
        big = i and density.get(t, 0) >= 5 and density.get(onsets[i - 1], 0) <= 3
        if is_phrase or big:
            br = _u(rng, BREATH['phrase'] if is_phrase else BREATH['big'])
            breath_at[t] = br
            shift[t] += BREATH['late'] * br
        shift[t] += _tri(rng) * CLUSTER_MS
    # registration seams: where a role starts sounding while another of the voices' roles stops, or as given
    seam_at = dict(seams or {})
    if seams is None:
        first = {}
        last = {}
        for v in voices:
            ns = v.sorted()
            first[v.role] = min(first.get(v.role, math.inf), ns[0][0])
            last[v.role] = max(last.get(v.role, -math.inf), ns[-1][0] + ns[-1][1])
        div = band.info.get('division') or {}
        for a in first:
            for b in last:
                if a != b and abs(first[a] - last[b]) < 0.3:
                    kind = 'piston' if div.get(a) == div.get(b) else 'hand'
                    if seam_at.get(round(first[a], 4)) != 'piston':
                        seam_at[round(first[a], 4)] = kind
    # ---- the played notes: onsets moved, then the articulation measured to the played onsets
    played = {}
    rec = []
    per_hand = {}                                   # (role, onset) -> notes struck there (the chord's size)
    for v, r in zip(voices, real):
        for st, du, p, orn in r:
            if not orn:
                per_hand[(v.role, round(st, 4))] = per_hand.get((v.role, round(st, 4)), 0) + 1
    hand_ms = {}
    hrng = random.Random(seed_int(f"hands:{seed}"))
    for k in sorted(per_hand):
        hand_ms[k] = hrng.gauss(0.0, HAND['sigma_ms'])
    for vi, (v, r) in enumerate(zip(voices, real)):
        vr = random.Random(seed_int(f"touch:{seed}:{vi}"))
        style = touch_of(v, bpm_at)

        def move(st, orn, _role=v.role, _vr=vr):
            if orn:
                base = max((t for t in onsets if t <= st + 1e-4), default=None)
                ms = shift.get(base, 0.0) if base is not None else 0.0
            else:
                k = (_role, round(st, 4))
                ms = shift.get(round(st, 4), 0.0) + hand_ms.get(k, 0.0)
                if per_hand.get(k, 0) >= 3:
                    ms += _u(_vr, HAND['spread_ms'])
            return st + ms / 60000.0 * bpm_at(st)
        moved = [(move(st, orn), du, p, orn, st) for st, du, p, orn in r]
        main = [(m, du + (st0 - m), p) for m, du, p, orn, st0 in moved if not orn]   # ends kept as written
        art = articulate(main, style, bpm_at, vr) if style else main
        # lift before a downbeat (ordinary / detached voices): the note before the accented cluster ends earlier
        out = []
        for (m, du, p), (_, _, _, _, st0) in zip(art, [x for x in moved if not x[3]]):
            end = m + du
            nxt_written = min((t for t in onsets if t > st0 + 1e-4), default=None)
            if nxt_written is not None:
                end_target = nxt_written
                kk = mg.bar_at(end_target)
                near = abs((st0 + _orig_dur(r, st0, p)) - end_target) < 0.02
                if near and agogic and abs(kk - round(kk)) < 1e-4 and style in ('ordinary', 'detache'):
                    end -= _u(vr, AGOGIC['lift_ms']) / 60000.0 * bpm_at(m)
                if near and end_target in breath_at and v.breathe:
                    end = min(end, move(end_target, False) - breath_at[end_target] / 60000.0 * bpm_at(m))
                if near and round(end_target, 4) in seam_at:
                    g = _u(vr, REGISTRANT[seam_at[round(end_target, 4)]])
                    end = min(end, move(end_target, False) - g / 60000.0 * bpm_at(m))
            out.append((m, max(0.03, end - m), p))
        orn = [(m, du, p) for m, du, p, o, _ in moved if o]
        notes = sorted(out + orn)
        played.setdefault(v.role, []).extend(notes)
        rec.append({'name': v.name, 'role': v.role, 'kind': v.kind, 'touch': style,
                    'written': v.sorted(), 'played': notes, 'ornaments': dict(v.ornaments)})
    # ---- one key per pitch per role; write the tracks
    result = {}
    for role, ns in played.items():
        keys = _merge(ns, bpm_at)
        clip = Clip._raw([_note(max(0.0, st), du, p) for st, du, p in keys], max(st + du for st, du, p in keys) + 1)
        band[role].play(clip, 0)
        result[role] = list(clip)
    if record:
        if not hasattr(song, 'organ_voices') or song.organ_voices is None:
            song.organ_voices = []
        song.organ_voices.extend(rec)
    return result


def _orig_dur(r, st0, p):
    for st, du, q, orn in r:
        if not orn and abs(st - st0) < 1e-6 and q == p:
            return du
    return 0.0


def _note(st, du, p):
    from .patterns import Note
    return Note(float(st), float(du), int(p), ORGAN_VEL)


def _merge(notes, bpm_at=None) -> list:
    """One key per pitch: overlapping notes of one pitch on one role share ONE key - struck together (within a 16th's
    third) they are one held key; a later attack inside a held key re-strikes it, the held note released RESTRIKE_MS
    before (songs/toccata-tenebrae's rule)."""
    by = {}
    for st, du, p in sorted(notes):
        by.setdefault(p, []).append([st, st + du])
    out = []
    for p, spans in by.items():
        cur = None
        for a, b in spans:
            if cur is not None and a < cur[1] - 0.01:
                if a - cur[0] < 0.08 or bpm_at is None:
                    cur[1] = max(cur[1], b)
                    continue
                rel = a - RESTRIKE_MS / 60000.0 * bpm_at(a)
                if rel - cur[0] < 0.04:
                    cur[1] = max(cur[1], b)
                    continue
                held, cur[1] = cur[1], rel
                out.append((cur[0], cur[1] - cur[0], p))
                cur = [a, max(b, held)]                 # (the key stays down to the longer note's end)
                continue
            if cur is not None:
                out.append((cur[0], cur[1] - cur[0], p))
            cur = [a, b]
        if cur is not None:
            out.append((cur[0], cur[1] - cur[0], p))
    return sorted(out)


def ring_gaps(song, min_s: float = RING[0], changes_only: bool = True) -> dict:
    """The church's ring at the section seams: per section end, the seconds of silence (no key down on any track)
    before the next section's first onset - {'gaps': {section: s}, 'short': [sections under min_s]}. changes_only:
    only the seams where the stops change (a role sounding before goes silent after it; a voice entering is no
    change) - where the registrant needs the time and the church rings."""
    tm = song.tempo_map()
    notes = sorted((n.start, n.start + n.dur) for t in song.tracks.values() for n in t.notes)
    roles = {sec.name: {name for name, t in song.tracks.items()
                        if any(sec.start - 1e-6 <= n.start < sec.end - 1e-6 for n in t.notes)}
             for sec in song.sections}
    out = {}
    secs = list(song.sections)
    for a, b in zip(secs, secs[1:]):
        if changes_only and roles[a.name] <= roles[b.name]:
            continue
        before = [e for s, e in notes if s < b.start - 1e-6]
        after = [s for s, e in notes if s >= b.start - 0.25]
        if not before or not after:
            continue
        last = max(before)
        nxt = min(after)
        out[a.name] = round(max(0.0, tm.seconds_at(nxt) - tm.seconds_at(last)), 2)
    return {'gaps': out, 'short': [k for k, v in out.items() if v < min_s]}


def parallel_motion(voices) -> list:
    """Parallel 5ths / octaves between written 'line' voices (organist.Voice or (name, notes)): [(beat, voice a,
    voice b)] at every onset where two sounding voices move into the same perfect interval in the same direction
    (organ_vocab.parallels) - the counterpoint check a hand-written piece runs before perform()."""
    from .organ_vocab import parallels, sounding
    ls = [(v.name, v.sorted()) if isinstance(v, Voice) else (v[0], sorted(v[1])) for v in voices
          if not isinstance(v, Voice) or v.kind == 'line']
    onsets = sorted({round(n[0], 4) for _, ns in ls for n in ns})
    out, prev = [], None
    for t in onsets:
        cur = [sounding(ns, t) for _, ns in ls]
        if prev is not None:
            for i in range(len(ls)):
                for j in range(i + 1, len(ls)):
                    if parallels([prev[i], prev[j]], [cur[i], cur[j]]):
                        out.append((t, ls[i][0], ls[j][0]))
        prev = cur
    return out


_ = BODIES
