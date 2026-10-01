"""A wind player's breath: named AIR, PITCH and MIC moves INSIDE held notes, and an arranger that places them phrase by
phrase (sax, trumpet, trombone, flute, clarinet; bowed strings reuse the air moves as bow pressure).

User feedback 2026-09-30 (lamplight-avenue, the Baker Street homage): "da spielt er eine Note und pustet mal kurz
mehr, mal kurz weniger" - a horn player does not hold a note at one level: the air moves inside it (a short push on
the beat, pulses with the groove, a swell, an fp, a bloom, a taper at the phrase end), the pitch follows the air
(vibrato that deepens as the air grows, a tiny lift with a push) - and "die bewegen das Sax gezielt und gewollt
relativ zum Mikrofon": the bell leans into the mic on the big notes (louder, fuller, drier) and swings away on the
soft endings (darker, more room). This module is both, like agentsound.pianist: every move is a function you can
use on its own, and arrange() chooses them from the line (seeded, budgeted, section-aware).

    from agentsound import hornist
    perf = hornist.arrange(melody, bpm=112, family='sax', style='hero', section='hook', peaks=(1, 9, 17), seed=3)
    perf.place(sax, riff)                    # the notes + every lane on the right targets of this track
    print(perf.summary(), perf.budget)       # what it played / what the budget dropped

    g = hornist.push(8.0, 2.5, 112, db=3)    # one move: a Gesture (shapes on abstract lanes)
    hornist.render(sax, [g], at=riff)        # write gestures on a track by hand

Moves (MOVES): air - push, pulse, swell, messa_di_voce, fp_cresc, bloom, taper, breath_release; pitch - vibrato,
scoop, fall, doit, shake, growl (a push carries its own small pitch lift); mic - lean_in, turn_away (= off_axis),
bell_swing, fade_away. A Gesture holds additive shapes on the abstract lanes (LANES): 'air' (dB of breath), 'bright'
(dB of tone that comes with the air), 'bend' (semitones), 'vib' (vibrato cents), 'mic' (dB of level from the
distance to the mic), 'prox' (dB of proximity lift ~300 Hz), 'shelf' (dB above ~3.2 kHz: on/off axis), 'room' (dB on
the reverb sends). Every shape starts and ends at its rest value with zero slope (cosine keyframes, points every
<= 20 ms): no zipper, no clicks.

Where it goes (targets(track), measured - TARGET_MEASUREMENTS): a +3 dB push on 'instrument.expression' of
layered/hero_sax comes out as +1.35 dB (its 3:1 compressor eats the rest), on 'dynamics' +0.5 dB; after the chain
+3.0 dB. On the plain samplers (sampled/alto_sax, trumpet, flute, clarinet) 'dynamics' only tilts the tone (+0.2 dB);
on the live-dynamics ones (sampled/tenor_sax, solo_trumpet, solo_flute, solo_clarinet, solo_trombone, ...) +0.25 of
'dynamics' = +3..8 dB with the timbre of the louder layer. So: on a live-dynamics sampler whose chain does not
compress, the air goes to 'dynamics' (the real layer crossfade; the home dynamics is lowered to leave headroom and the
level made good after the chain); everywhere else to the BREATH stage 'fx.air.gain' - agentsound.heroes' convention: a
utility named 'air' after every compressor (every hero/<preset> has one; air_stage() inserts it when missing). The
'mic' stage (mic_stage(): an eq named 'mic') sits where a microphone is - before the compressor (the hero's 'comp'
stage), so leaning in / turning away colours what the compressor, echo and ride work on; last only when the chain does
not compress or its output carries the air: the tone of the air and the mic moves (high shelf: axis, peak at 300 Hz:
proximity, output: distance). Vibrato: the sampler's own
('instrument.vibrato', every sampler layer of a stack), deepened by the air. Room: the track's reverb sends.
"""

from __future__ import annotations

import math
import random
import re

from .budget import Budget
from .gesture import (_EPS, LANES, Gesture, _b, _bpm, _num, _pos, _sample, accents, bell_swing, bloom,
                      breath_release, doit, fade_away, fall, fp_cresc, growl, lean_in, messa_di_voce, off_axis, pulse,
                      push, scoop, shake, swell, taper, turn_away, vibrato)
from .patterns import Clip, Note, as_clip, seed_int
from .theory import ComposeError

__all__ = ['air_stage', 'LANES', 'FAMILIES', 'STYLES', 'SECTION_ENERGY', 'MOVES', 'AIR', 'PITCH', 'MIC', 'FAST', 'SPICE',
           'TARGET_MEASUREMENTS', 'DYN_SENS', 'Gesture', 'Memory', 'Performance', 'push', 'pulse', 'swell',
           'messa_di_voce', 'fp_cresc', 'bloom', 'taper', 'breath_release', 'vibrato', 'scoop', 'fall', 'doit',
           'shake', 'growl', 'lean_in', 'turn_away', 'off_axis', 'bell_swing', 'fade_away', 'arrange', 'targets',
           'mic_stage', 'render', 'family_of', 'vocabulary']

MOVES = {'accents': accents, 'push': push, 'pulse': pulse, 'swell': swell, 'messa_di_voce': messa_di_voce, 'fp_cresc': fp_cresc,
         'bloom': bloom, 'taper': taper, 'breath_release': breath_release, 'vibrato': vibrato, 'scoop': scoop,
         'fall': fall, 'doit': doit, 'shake': shake, 'growl': growl, 'lean_in': lean_in, 'turn_away': turn_away,
         'off_axis': off_axis, 'bell_swing': bell_swing, 'fade_away': fade_away}
AIR = ('accents', 'push', 'pulse', 'swell', 'messa_di_voce', 'fp_cresc', 'bloom', 'taper', 'breath_release')
PITCH = ('vibrato', 'scoop', 'fall', 'doit', 'shake', 'growl')
MIC = ('lean_in', 'turn_away', 'off_axis', 'bell_swing', 'fade_away')
FAST = ('shake', 'growl')
"""Rare set pieces: at most one per `fast_every` bars (24-32), only at structural moments (a hook peak, climax)."""
SPICE = ('scoop', 'fall', 'doit')
"""Pitch spice at note edges: at least `spice_every` bars apart (1-4)."""


# ------------------------------------------------------------------------------------------------ players

FAMILIES = {
    'sax': dict(vib_ct=14.0, peak_vib_ct=26.0, vib_hz=5.4, vib_delay=0.28, push_db=2.6, lift=6.0, bright=0.6,
                scoop=0.45, fall=0.35, doit=0.1, shake=True, growl=True, couple=0.12),
    'trumpet': dict(vib_ct=10.0, peak_vib_ct=18.0, vib_hz=5.6, vib_delay=0.3, push_db=2.4, lift=5.0, bright=0.7,
                    scoop=0.3, fall=0.35, doit=0.2, shake=True, growl=False, couple=0.12),
    'trombone': dict(vib_ct=10.0, peak_vib_ct=16.0, vib_hz=5.0, vib_delay=0.32, push_db=2.4, lift=4.0, bright=0.6,
                     scoop=0.35, fall=0.4, doit=0.05, shake=False, growl=True, couple=0.1),
    'flute': dict(vib_ct=16.0, peak_vib_ct=22.0, vib_hz=5.0, vib_delay=0.18, push_db=2.0, lift=4.0, bright=0.3,
                  scoop=0.05, fall=0.05, doit=0.0, shake=False, growl=False, couple=0.15),
    'clarinet': dict(vib_ct=0.0, peak_vib_ct=6.0, vib_hz=5.2, vib_delay=0.4, push_db=2.0, lift=3.0, bright=0.35,
                     scoop=0.1, fall=0.05, doit=0.0, shake=False, growl=False, couple=0.1),
    'strings': dict(vib_ct=14.0, peak_vib_ct=20.0, vib_hz=5.8, vib_delay=0.12, push_db=2.2, lift=3.0, bright=0.4,
                    scoop=0.05, fall=0.0, doit=0.0, shake=False, growl=False, couple=0.1),
}
"""Per instrument family: vibrato depth (cents +-) on held notes / held peaks, its rate (Hz) and delay (s), the push
depth (dB), the pitch lift of a push (cents), how much the tone opens with the air (dB per dB), the chances of a
scoop / fall / doit at the note edges, whether a shake / growl exists, and how much the vibrato deepens per dB of
air ('couple'). Baker Street (measured, the riff's held notes): vibrato +-20-30 ct at 5.4-5.5 Hz on the peaks."""

STYLES = {
    'hero': dict(push=0.6, pulse=0.5, swell=0.55, bloom=0.3, fp=0.12, taper=0.75, release=0.5, vib_peak=0.95,
                 vib_other=0.35, pitch=1.0, lean=0.9, swing=0.45, fade=0.5, fast_every=24, spice_every=2,
                 mic_every=4, pulse_every=4),
    'pop': dict(push=0.5, pulse=0.35, swell=0.5, bloom=0.3, fp=0.08, taper=0.7, release=0.5, vib_peak=0.9,
                vib_other=0.3, pitch=0.8, lean=0.7, swing=0.35, fade=0.5, fast_every=32, spice_every=2.5,
                mic_every=6, pulse_every=6),
    'ballad': dict(push=0.3, pulse=0.2, swell=0.75, bloom=0.5, fp=0.05, taper=0.9, release=0.6, vib_peak=0.95,
                   vib_other=0.5, pitch=0.6, lean=0.6, swing=0.5, fade=0.7, fast_every=0, spice_every=3,
                   mic_every=4, pulse_every=8),
    'jazz': dict(push=0.55, pulse=0.3, swell=0.35, bloom=0.35, fp=0.1, taper=0.6, release=0.5, vib_peak=0.8,
                 vib_other=0.3, pitch=1.2, lean=0.4, swing=0.3, fade=0.4, fast_every=32, spice_every=1.5,
                 mic_every=8, pulse_every=6),
    'classical': dict(push=0.15, pulse=0.1, swell=0.7, bloom=0.4, fp=0.12, taper=0.9, release=0.3, vib_peak=0.9,
                      vib_other=0.6, pitch=0.2, lean=0.2, swing=0.2, fade=0.3, fast_every=0, spice_every=4,
                      mic_every=16, pulse_every=8),
}
"""arrange() styles: chances per held note (push, pulse on long notes, swell on the phrase peaks, bloom, fp on a
long phrase opener, taper and breath_release at phrase ends, vibrato on held peaks / other held notes, lean_in on
the hook peaks, bell_swing on long notes, fade_away on soft endings), `pitch` scales the scoop / fall / doit chances,
and the budgets in bars: fast_every (shake / growl; 0 = none), spice_every (scoop / fall / doit), mic_every
(lean_in / turn_away / bell_swing / fade_away), pulse_every (pulse, fp_cresc)."""

SECTION_ENERGY = {'intro': 0.5, 'verse': 0.55, 'pre': 0.75, 'bridge': 0.7, 'chorus': 1.0, 'hook': 1.0, 'riff': 1.0,
                  'solo': 0.9, 'trade': 0.9, 'climax': 1.15, 'outro': 0.85, 'tag': 0.8, 'ending': 0.7}
"""section= -> energy: scales every air / mic depth (x 0.8 + 0.3 x energy) and decides the mic moves (lean_in
from 0.85, turn_away / fade_away on soft sections). A name is matched by prefix ('chorus2' -> chorus)."""


def family_of(sound) -> str | None:
    """The FAMILIES name for a patch name / track (by its patch name): sax, trumpet, trombone, flute, clarinet,
    strings; None if unknown."""
    name = getattr(sound, 'patch', None) or getattr(sound, 'name', None) or (sound if isinstance(sound, str) else '')
    name = (name or '').lower()
    for fam, words in (('sax', ('sax',)), ('trumpet', ('trumpet', 'flugel', 'cornet', 'horn_section', 'brass')),
                       ('trombone', ('trombone', 'tuba', 'euphon')),
                       ('flute', ('flute', 'piccolo', 'recorder', 'pan_flute', 'whistle')),
                       ('clarinet', ('clarinet', 'oboe', 'bassoon', 'english_horn')),
                       ('strings', ('violin', 'viola', 'cello', 'string', 'fiddle'))):
        if any(w in name for w in words):
            return fam
    return None


class Memory:
    """What one wind player already played in a song: pass the same Memory to every arrange() call (memory=, at=)
    and the budgets (FAST, SPICE, mic, pulse) count song-wide. played(at, name) books a move placed by hand,
    save(at) keeps the FAST budget free for a later moment (the climax)."""

    def __init__(self):
        self.clock = 0.0
        self.booked: dict[str, list] = {'fast': [], 'spice': [], 'mic': [], 'pulse': []}
        self.saved: list = []

    def save(self, at) -> 'Memory':
        self.saved.append(_pos(at))
        return self

    def played(self, at, name: str) -> 'Memory':
        cat = _category(name)
        if cat is None:
            raise ComposeError(f"Memory.played: {name!r} is not a budgeted move "
                               f"({', '.join(FAST + SPICE + MIC + ('pulse', 'fp_cresc'))})")
        self.booked[cat].append(_pos(at))
        return self

    def __repr__(self) -> str:
        return "Memory(" + ', '.join(f"{k} {len(v)}" for k, v in self.booked.items()) + f"; clock {self.clock:g})"


def _category(name: str) -> str | None:
    if name in FAST:
        return 'fast'
    if name in SPICE:
        return 'spice'
    if name in MIC:
        return 'mic'
    if name in ('pulse', 'fp_cresc'):
        return 'pulse'
    return None


class Performance:
    """What arrange() played: clip (the notes as played: legato phrases, breaths, velocities, timing), gestures (the
    moves, positions relative to the clip), moves (a log: (start, end, kind, name)), budget ({category: every bars,
    'kept': {...}, 'dropped': [(beat, name, substitute)]}). place(track, at) plays it on a track and writes every lane
    on the targets of that track (targets()); lanes(at) the sampled abstract lanes."""

    def __init__(self, clip: Clip, gestures: list, bpm: float, family: str, log: list, budget: dict):
        self.clip, self.gestures, self.bpm, self.family = clip, gestures, bpm, family
        self.moves = log
        self.budget = budget

    def __repr__(self) -> str:
        return f"Performance({len(self.clip)} notes, {len(self.gestures)} moves: {self.summary()})"

    def add(self, *gestures) -> 'Performance':
        """Add hand-placed gestures (moves called on their own, positions relative to the clip) - they are sampled
        together with the arranged ones (one lane per target, no conflicting points)."""
        for g in gestures:
            if not isinstance(g, Gesture):
                raise ComposeError(f"Performance.add takes hornist moves (Gesture), got {g!r}")
            self.gestures.append(g)
            self.moves.append((round(g.start, 4), round(g.end, 4), g.kind, g.name))
        return self

    def summary(self) -> dict:
        out: dict = {}
        for _, _, kind, name in self.moves:
            out[f"{kind}:{name}"] = out.get(f"{kind}:{name}", 0) + 1
        return dict(sorted(out.items()))

    def shifted(self, at) -> list:
        a = _pos(at)
        return [g.shifted(a) for g in self.gestures]

    def lanes(self, at=0.0) -> dict:
        """{lane: [(beat, value[, 'step'])]} - every abstract lane sampled (points only where a move is active)."""
        gs = self.shifted(at)
        out = {}
        for lane in LANES:
            pts = _sample([s for g in gs for s in g.shapes if s.lane == lane], lambda v, lane=lane: v.get(lane, 0.0),
                          self.bpm)
            if pts:
                out[lane] = pts
        return out

    def envelope(self, lane: str, t: float, at=0.0) -> float:
        """The value of an abstract lane at beat t (the clip placed at `at`)."""
        a = _pos(at)
        return sum(g.value(lane, t - a) for g in self.gestures)

    def place(self, track, at=0.0, *, room=None, level: str | None = None, vibrato: bool = True, accents=None):
        """track.play(clip, at) + every lane on this track's targets (targets(track, room=, level=); vibrato=False
        leaves the vibrato to someone else). Returns the track."""
        a = _pos(at)
        track.play(self.clip, a)
        render(track, self.shifted(a), bpm=self.bpm, room=room, level=level, vibrato=vibrato, accents=accents)
        return track


# ------------------------------------------------------------------------------------------------ targets

TARGET_MEASUREMENTS = {
    # patch: (+3 dB push on expression -> dB out, +0.25 dynamics -> dB out / brightness dB, post-chain +3 -> dB out)
    'layered/hero_sax': (1.35, (0.53, -0.35), 2.99),
    'sampled/alto_sax': (2.99, (0.21, 0.64), 2.99),
    'sampled/tenor_sax': (2.99, (5.12, 0.76), 2.99),
    'sampled/trumpet': (2.99, (0.23, 0.56), 2.99),
    'sampled/flute': (2.99, (0.13, 0.67), 2.99),
    'sampled/solo_trumpet': (2.99, (4.08, 0.55), 2.99),
    'sampled/solo_flute': (2.99, (3.08, 0.56), 2.99),
    'sampled/solo_clarinet': (2.99, (2.64, 5.11), 2.99),
    'sampled/solo_trombone': (2.99, (4.24, 1.63), 2.99),
    'sampled/trumpet_harmon': (2.99, (3.81, 0.93), 2.99),
    'sampled/solo_violin': (2.99, (3.32, 0.56), 2.99),
    'sampled/solo_horn': (2.99, (7.92, 6.76), 2.99),
}
"""Measured (.scratch/targets.py: a 3.5 s held note at velocity 100, the stem, the push's peak vs the same note
without it): what a +3 dB breath push written on each target does to the output. The hero sax's compressor keeps
only 1.35 dB of a pre-chain push; 'dynamics' is live only on the live-dynamics samplers."""

DYN_SENS = {k: round(v[1][0] / 0.25, 1) for k, v in TARGET_MEASUREMENTS.items() if v[1][0] > 1.0}
"""dB of output per 1.0 of 'dynamics' around the home value, for the live-dynamics samplers (measured)."""

_ROOM = re.compile(r'plate|hall|room|reverb|verb|space|chamber', re.I)
_GAIN_PARAM = {'utility': 'gain', 'eq': 'output'}
HEADROOM = 4.0
"""dB the air may rise over the home level on 'dynamics' (the home is lowered by it and made good after the chain)."""


def _fx_named(track, name):
    return next((f for f in track.fx if getattr(f, 'name', None) == name), None)


def mic_stage(track, before_comp: bool = True):
    """The track's 'mic' stage: an eq named 'mic' (flat: peak1 at 300 Hz for the proximity lift, a gentle high shelf
    from 3.2 kHz for the axis, output for the level), inserted where a microphone sits - before the chain's
    compressor (the hero 'comp' stage, else the first un-keyed compressor), so the player leaning in / turning away
    colours what the compressor, the echo and the ride then work on (it used to be appended after all of them);
    appended when the chain has no compressor, or with before_comp=False (the mic stage's output then carries the
    air itself: targets(level='mic'), which must not be squashed). Returns the FX."""
    from .patches import fx
    st = _fx_named(track, 'mic')
    if st is None:
        new = fx.eq({'peak1.freq': 300, 'peak1.q': 0.7, 'high.freq': 3200, 'high.q': 0.6}, name='mic')
        at = next((i for i, f in enumerate(track.fx) if getattr(f, 'name', None) == 'comp'), None)
        if at is None:
            at = next((i for i, f in enumerate(track.fx) if f.type == 'compressor' and f.sidechain is None), None)
        if at is None or not before_comp:
            track.add_fx(new)
        else:
            track.fx.insert(at, new)
        st = _fx_named(track, 'mic')
    return st


def air_stage(track):
    """The track's breath stage: an fx named 'air' with a gain (agentsound.heroes' convention: a utility named 'air'
    after every compressor and the saturation, before the instrument's own echo - every hero/<preset> has one; an eq
    named 'air' works through its output). Inserted when missing: after the last level-dependent stage, before an
    echo / hero ride / a 'mic' stage that follows all of them (else at the end). Returns (FX, param), or (None, None)
    when an fx named 'air' without a gain is in the way (then the mic stage's output carries the air)."""
    from .patches import FX
    st = _fx_named(track, 'air')
    if st is None:
        new = FX('utility', {'gain': 0.0}, name='air')
        dyn = max((i for i, f in enumerate(track.fx) if f.type in ('compressor', 'limiter', 'saturator', 'amp', 'tape')
                   and getattr(f, 'sidechain', None) is None), default=-1)
        at = next((i for i, f in enumerate(track.fx) if i > dyn and (getattr(f, 'name', None) in ('mic', 'hero_ride')
                                                                    or (f.type == 'delay' and f.name == 'echo'))), None)
        if at is None:
            track.fx.append(new)
        else:
            track.fx.insert(at, new)
        st = _fx_named(track, 'air')
    p = _GAIN_PARAM.get(st.type) or next((q for q in ('gain', 'output') if q in (st.params or {})), None)
    return (st, p) if p is not None else (None, None)


def targets(track, *, room=None, level: str | None = None) -> dict:
    """Where this track's lanes go: {'level': target of the air, 'kind': 'air' | 'dynamics' | 'mic', 'home': rest
    value, 'per_db': value per dB (dynamics), 'comp': dB the mic stage makes good, 'tone': True when the air also
    opens the mic shelf (not on 'dynamics': the layers carry the tone), 'compressed': the chain compresses, 'room':
    [(bus, base dB)], 'vibrato': [prefixes], 'mic': 'fx.mic'}.
    The air: on a live-dynamics sampler with no compressor in its chain 'instrument.dynamics' (the real layer
    crossfade), else the breath stage 'fx.air.gain' (air_stage(): the hero chain's own, else inserted at the end of
    the chain - after the compressor, so a 3 dB push stays 3 dB). level= forces 'air' | 'dynamics' | 'mic' (the mic
    stage's output). The mic stage (mic_stage()) sits before the compressor (where a microphone is: in front of the
    chain), last only when its output carries the air (kind 'mic') or the chain does not compress."""
    from .articulation import live_dynamics, vibrato_prefixes
    out = {'mic': 'fx.mic', 'room': [], 'vibrato': vibrato_prefixes(track), 'tone': True, 'comp': 0.0,
           'compressed': any(getattr(f, 'type', None) in ('compressor', 'limiter') and not getattr(f, 'sidechain', None)
                             for f in track.fx)}
    ins = track.instrument
    kind = level
    if kind is None:
        kind = 'dynamics' if not out['compressed'] and live_dynamics(track) else 'air'
    if kind == 'air':
        st_air, air_p = air_stage(track)
        if st_air is None:
            kind = 'mic'
        else:
            out.update(level=f'fx.air.{air_p}', kind=kind, home=float((st_air.params or {}).get(air_p, 0.0)),
                       per_db=1.0)
    st = mic_stage(track, before_comp=kind != 'mic')
    if kind == 'dynamics':
        if getattr(ins, 'type', None) not in ('sampler', 'stack'):
            raise ComposeError(f"track {track.id!r}: level='dynamics' needs a sampler (or a stack of them)")
        d0 = float(ins.params.get('dynamics', 1.0))
        sens = DYN_SENS.get(track.patch or '')
        if sens is None:
            dr = ins.params.get('dynrange')
            sens = float(dr) + 4.0 if isinstance(dr, (int, float)) and dr > 0 else 16.0
        home = min(d0, 1.0 - HEADROOM / sens)
        out.update(level='instrument.dynamics', kind=kind, home=round(home, 4), per_db=1.0 / sens,
                   comp=round((d0 - home) * sens, 2), tone=False)
    elif kind == 'mic':
        out.update(level='fx.mic.output', kind=kind, home=0.0, per_db=1.0)
    elif kind != 'air':
        raise ComposeError(f"level must be 'air', 'dynamics' or 'mic', got {level!r}")
    if out['comp'] and abs(float((st.params or {}).get('output', 0.0)) - out['comp']) > 1e-6:
        st.params['output'] = out['comp']
    out['comp'] = float((st.params or {}).get('output', 0.0))
    sends = dict(getattr(track, '_patch_sends', {}) or {})
    sends.update(track.sends)
    auto = {t for t, _ in track._auto}
    have = set(getattr(track._song, 'buses', {}) or {})
    mine = track.__dict__.setdefault('_hornist_room', None)
    if room is None and mine is not None:
        buses = list(mine)
    elif room is None:     # the reverb sends that exist in the song and nobody else automates (decided once)
        buses = [b_ for b_ in sends if _ROOM.search(b_) and b_ in have and f'send.{b_}' not in auto
                 and sends[b_] is not None]
        track._hornist_room = tuple(buses)
    else:
        buses = [getattr(r, 'id', r) for r in (room if isinstance(room, (list, tuple)) else [room])]
    out['room'] = [(b_, float(sends.get(b_, -60.0) if sends.get(b_) is not None else -60.0)) for b_ in buses]
    return out


def render(track, gestures, *, bpm=None, room=None, level: str | None = None, vibrato: bool = True,
           accents=None) -> dict:
    """Write gestures (absolute beats) on a track: the air on its level target (targets()), the air's tone and the
    mic moves on the mic stage, the room on the reverb sends, bend on 'instrument.pitchbend', vibrato on the
    sampler's vibrato (depth deepened by the air), its rate on 'vibratorate'. accents (the note-to-note 'accents'
    gestures): None = only on a compressed chain (targets()['compressed']: there the velocities alone are squeezed
    flat), True / False. Returns the targets plan."""
    b = _bpm(bpm if bpm is not None else track._song.tempo)
    plan = targets(track, room=room, level=level)
    acc = plan['compressed'] if accents is None else bool(accents)
    shapes = [s for g in gestures if acc or g.name != 'accents' for s in g.shapes]
    by = {ln: [s for s in shapes if s.lane == ln] for ln in LANES}
    fam = FAMILIES.get(family_of(track) or 'sax')

    def write(target, sel, fn):
        pts = _sample(sel, fn, b)
        if pts:
            track.automate(target, pts)
        return pts

    comp, home, per = plan['comp'], plan['home'], plan['per_db']
    if plan['kind'] == 'mic':
        write('fx.mic.output', by['air'] + by['mic'], lambda v: comp + v.get('air', 0.0) + v.get('mic', 0.0))
    else:
        if plan['kind'] == 'dynamics':
            write(plan['level'], by['air'],
                  lambda v: min(1.0, max(0.0, home + min(HEADROOM, v.get('air', 0.0)) * per)))
        else:
            write(plan['level'], by['air'], lambda v: home + v.get('air', 0.0))
        write('fx.mic.output', by['mic'], lambda v: comp + v.get('mic', 0.0))
    tone = by['shelf'] + (by['bright'] if plan['tone'] else [])
    write('fx.mic.high.gain', tone, lambda v: max(-24.0, min(24.0, v.get('shelf', 0.0) + v.get('bright', 0.0))))
    write('fx.mic.peak1.gain', by['prox'], lambda v: v.get('prox', 0.0))
    for bus, base in plan['room']:
        write(f'send.{bus}', by['room'], lambda v, base=base: max(-60.0, min(12.0, base + v.get('room', 0.0))))
    write('instrument.pitchbend', by['bend'], lambda v: max(-24.0, min(24.0, v.get('bend', 0.0))))
    if vibrato and by['vib']:
        cp = fam['couple']
        vib_shapes = by['vib'] + by['air']
        fn = lambda v: max(0.0, min(200.0, v.get('vib', 0.0) * min(1.6, max(0.5, 1.0 + cp * v.get('air', 0.0)))))  # noqa: E731
        # only where a vibrato runs: the air shapes outside the vibrato windows would add zero points
        vwins = [(s.t0, s.t1) for s in by['vib']]
        sel = by['vib'] + [s for s in by['air'] if any(s.t0 < e and s.t1 > a for a, e in vwins)]
        pts = _sample(sel, fn, b) if vib_shapes else []
        rate = sorted((r for g in gestures for r in g.rate), key=lambda r: r[0])
        prefixes = plan['vibrato']
        if prefixes:
            for pre in prefixes:
                if pts:
                    track.automate(pre + '.vibrato', [(t, round(v, 3)) + tuple(r) for t, v, *r in pts])
                if rate:
                    track.automate(pre + '.vibratorate', rate)
        elif pts:
            from .modulation import lfo as _lfo
            hz = rate[0][1] if rate else 5.4
            if 'instrument.pitchbend' not in {t for t, _ in track._auto}:
                track.automate('instrument.pitchbend', [(max(0.0, pts[0][0]), 0.0)])
            track.modulate('instrument.pitchbend', _lfo('sine', rate=round(b / 60.0 / hz, 6),
                                                         depth=[(t, round(v / 100.0, 4)) for t, v, *_ in pts]))
    return plan


# ------------------------------------------------------------------------------------------------ the arranger

def _energy(section, energy) -> float:
    if energy is not None:
        return _num(energy, 'energy', 0, 1.5)
    if section is None:
        return 0.8
    name = getattr(section, 'name', section)
    if not isinstance(name, str):
        raise ComposeError(f"section must be a name or a Section, got {section!r}")
    n = name.lower()
    for k in sorted(SECTION_ENERGY, key=len, reverse=True):
        if n.startswith(k):
            return SECTION_ENERGY[k]
    return 0.8


def _keep(cands: list, booked: list, saved: list, every_beats: float, base: float, L: float) -> None:
    """Best-first: keep a candidate when it is at least every_beats from every booked one (and from a saved moment
    outside this clip); sets c['keep'] and books it in `booked` (beats). The shared mechanism:
    agentsound.budget.Budget."""
    bud = Budget({'x': every_beats}, save_cls=('x',), events=[(t, 'x') for t in booked], saved=saved)
    for c in cands:
        c['cls'] = 'x'
    booked += [base + c['t'] for c in bud.keep(cands, base, (base, base + L), slots=False)]


def arrange(melody, bpm, *, family: str = 'sax', style: str = 'hero', section=None, energy: float | None = None,
            seed=0, peaks=None, vel=None, legato: bool = True, breath_ms: float = 160.0, max_phrase: float = 8.0,
            humanize_ms: float = 4.0, late_ms: float = 0.0, climax: bool = False, memory: Memory | None = None,
            at=None, bpb: float = 4.0, depth: float = 1.0, held: float = 0.45, accent: float = 0.12,
            **overrides) -> Performance:
    """A wind player's performance of a written line -> Performance (.clip, .gestures, .moves, .budget,
    .place(track, at)).

    Phrasing: velocities (vel=(lo, hi): humanize.touch arcs; None keeps the melody's), legato inside phrases
    (articulation.legato: legato transitions on a mono='legato' sampler), breaths of breath_ms before rests and in
    phrases longer than max_phrase beats (jazz.breathe), a player's timing (humanize_ms, late_ms).
    Accents: every phrase's note-to-note dynamics as air (accents(): (vel - the phrase mean) x `accent` dB per
    velocity step; place() writes them only on a compressed chain, where the velocities alone are squeezed flat).
    Then, for every HELD note (>= `held` s and >= 3/4 beat of sound), seeded and budgeted:
      - the phrase's peak (its highest held note) and the hook peaks (peaks=: beats in the clip) get the most air:
        a swell (or a bloom), often a push on a beat inside it, vibrato (FAMILIES peak_vib_ct), lean_in (energy >=
        0.85, mic budget); with climax=True / the last hook peak a shake or growl may happen (FAST budget: once per
        fast_every bars, structural moments only);
      - long notes (>= 2.5 beats, 1.6 s): pulse - 2-4 pushes on the beats (pulse budget), else a swell / a push;
        a long phrase opener now and then an fp_cresc (pulse budget); a bell_swing (mic budget);
      - other held notes: a push (style 'push' chance) or a bloom or nothing - not every note breathes the same;
        a gentle vibrato on some (vib_other);
      - phrase ends: taper + breath_release, fade_away on soft sections (mic budget), a fall / doit (SPICE budget);
        phrase openers and leaps up: a scoop (SPICE) - the hook peaks nearly always (a sax / brass signature).
    section= a name (SECTION_ENERGY: verse 0.55 .. chorus / hook 1.0, climax 1.15) or energy= 0..1.5 scales every
    depth (x (0.8 + 0.3 energy) x depth); style: STYLES ('hero', 'pop', 'ballad', 'jazz', 'classical'); family:
    FAMILIES ('sax', 'trumpet', 'trombone', 'flute', 'clarinet', 'strings'); overrides= any STYLES / FAMILIES key
    (push=0.8, peak_vib_ct=30, mic_every=8 ...). memory= a Memory shared by a song's calls (at= the clip's beat)
    counts the budgets song-wide. Deterministic by seed."""
    from . import articulation as art
    from .humanize import touch
    from .jazz import breathe
    if style not in STYLES:
        raise ComposeError(f"hornist style must be one of {', '.join(STYLES)}, got {style!r}")
    if family not in FAMILIES:
        raise ComposeError(f"hornist family must be one of {', '.join(FAMILIES)}, got {family!r}")
    S, F = dict(STYLES[style]), dict(FAMILIES[family])
    for k, v in overrides.items():
        if k in S:
            S[k] = v
        elif k in F:
            F[k] = v
        else:
            raise ComposeError(f"arrange(): unknown option {k!r} (a STYLES key: {', '.join(S)}; a FAMILIES key: "
                               f"{', '.join(F)})")
    b = _bpm(bpm)
    rng = random.Random(seed_int(seed))
    e = _energy(section, energy)
    k = (0.8 + 0.3 * e) * _num(depth, 'depth', 0, 3)
    if memory is not None and not isinstance(memory, Memory):
        raise ComposeError(f"hornist memory must be a hornist.Memory(), got {memory!r}")
    c = as_clip(melody)
    L = c.length
    base = _pos(at) if at is not None else (memory.clock if memory is not None else 0.0)
    if vel is not None:
        if not isinstance(vel, (tuple, list)) or len(vel) != 2:
            raise ComposeError(f"vel must be (lo, hi) for humanize.touch, got {vel!r}")
        c = touch(c, vel[0], vel[1])
    if legato:
        c = art.legato(c, overlap=0.03)
    if breath_ms:
        c = breathe(c, b, breath_ms, max_phrase)
    if humanize_ms or late_ms:
        c = art.humanize_starts(c, b, humanize_ms, late_ms, seed=seed)
    # the line (top note of every onset) and its phrases
    ns: list[Note] = []
    for n in sorted(c, key=lambda n: (n.start, -n.pitch)):
        if not ns or n.start > ns[-1].start + 0.02:
            ns.append(n)
    hooks = [_num(p, 'peaks (beats)') for p in (peaks or ())]
    info = []
    phrase = 0
    for i, n in enumerate(ns):
        prev = ns[i - 1] if i else None
        nxt = ns[i + 1] if i + 1 < len(ns) else None
        tied = prev is not None and prev.start + prev.dur > n.start + _EPS
        if prev is not None and n.start - (prev.start + prev.dur) >= 0.25 - _EPS:
            phrase += 1
        sound = min(n.dur, nxt.start - n.start) if nxt is not None and nxt.start < n.start + n.dur else n.dur
        rest = (nxt.start - (n.start + n.dur)) if nxt is not None else math.inf
        info.append(dict(n=n, i=i, tied=tied, phrase=phrase, sound=sound, secs=sound * 60 / b, rest=rest,
                         nxt=nxt.start if nxt is not None else None, prev=prev,
                         hook=any(abs(n.start - h) < 0.2 for h in hooks)))
    nphr = phrase + 1
    for ph in range(nphr):
        mem = [x for x in info if x['phrase'] == ph]
        held_ = [x for x in mem if x['secs'] >= held and x['sound'] >= 0.75 - _EPS]
        if held_:
            top = max(held_, key=lambda x: (x['n'].pitch, x['sound']))
            top['peak'] = True
        mem[0]['first'] = True
        mem[-1]['last'] = True
    last_hook = max((x['n'].start for x in info if x['hook']), default=None)
    fixed: list = []                # the note-to-note accents of every phrase (not budgeted)
    if accent:
        starts = [min(x['n'].start for x in info if x['phrase'] == ph) for ph in range(nphr)]
        for ph in range(nphr):
            mem = [x for x in info if x['phrase'] == ph]
            g = accents([(x['n'].start, x['sound'], x['n'].vel) for x in mem], b, db_per_vel=accent,
                        back=starts[ph + 1] if ph + 1 < nphr else None)
            if g.shapes:
                fixed.append(g)

    plan: list[dict] = []          # candidates: dict(name, t, score, cat, make, alt)
    vel_mean = sum(x['n'].vel for x in info) / len(info) if info else 80

    def cand(name, x, score, make, alt=None, cat=None):
        plan.append(dict(name=name, t=x['n'].start, score=score, cat=cat or _category(name), make=make, alt=alt,
                         phrase=x['phrase']))

    def jit(v, spread=0.2):
        return v * (1.0 + spread * (2 * rng.random() - 1))

    for x in info:
        n, s, d, secs = x['n'], x['n'].start, x['sound'], x['secs']
        is_held = secs >= held and d >= 0.75 - _EPS
        phrase_end = x.get('last') and x['rest'] >= 0.5 - _EPS
        back = x['nxt']
        pk, hk = x.get('peak', False), x['hook']
        score = 1.0 + 0.5 * pk + 1.0 * hk + 0.5 * bool(climax) + (0.8 if hk and s == last_hook else 0.0)
        # pitch spice at the edges
        leap = x['prev'] is not None and n.pitch - x['prev'].pitch >= 3
        p_scoop = max(F['scoop'], 0.85 if F['scoop'] >= 0.3 else F['scoop']) if hk else F['scoop']
        if is_held and (x.get('first') or leap or hk) and rng.random() < p_scoop * S['pitch']:
            cents = -jit(70, 0.3)
            cand('scoop', x, score, lambda s=s, cents=cents: scoop(s, b, cents=cents, ms=jit(90, 0.25)))
        if phrase_end and x['rest'] >= 1.0 - _EPS and not hk and d >= 0.45:
            r = rng.random()
            if r < F['doit'] * S['pitch']:
                cand('doit', x, score, lambda s=s, d=d, back=back: doit(s + d, b, semis=jit(3, 0.2), back=back))
            elif r < (F['doit'] + F['fall']) * S['pitch']:
                cand('fall', x, score, lambda s=s, d=d, back=back: fall(s + d, b, semis=-jit(3, 0.3), back=back))
        if not is_held:
            continue
        pdb = F['push_db'] * k
        # the main air shape
        if pk or hk:
            if rng.random() < S['swell'] or hk:
                lo, pkv = -jit(1.8) * k, jit(1.4) * k * (1.15 if hk else 1.0)
                cand('swell', x, score, lambda s=s, d=d, lo=lo, pkv=pkv, x=x: swell(
                    s, d, b, lo=lo, peak=pkv, end=-jit(1.2) * k, peak_at=jit(0.55, 0.15), tied=x['tied'],
                    back=x['nxt'] if x.get('last') else s + d + _b(0.05, b), bright=F['bright']))
            else:
                cand('bloom', x, score, lambda s=s, d=d, x=x: bloom(s, d, b, under=-jit(3.0) * k, ms=jit(320, 0.25),
                                                                     tied=x['tied'], bright=F['bright']))
            if secs >= 0.9 and rng.random() < S['push']:
                w = jit(170, 0.25)
                cand('push', x, score, lambda s=s, d=d, w=w: push(s, d, b, db=jit(pdb * 0.8), ms=w, lift=F['lift'],
                                                                   bright=F['bright']))
        elif d >= 2.5 - _EPS and secs >= 1.6 and rng.random() < S['pulse']:
            every = 1.0 if b <= 132 else 2.0
            cand('pulse', x, score + 0.3, lambda s=s, d=d, every=every: pulse(
                s, d, b, every=every, db=jit(pdb * 0.8), ms=jit(150, 0.2), lift=F['lift'] * 0.6, bright=F['bright'],
                jitter=(rng, 12.0)),
                alt=lambda s=s, d=d: push(s, d, b, db=jit(pdb), ms=jit(170, 0.25), lift=F['lift'], bright=F['bright']))
        elif x.get('first') and d >= 2.0 - _EPS and rng.random() < S['fp']:
            cand('fp_cresc', x, score, lambda s=s, d=d, x=x: fp_cresc(s, d, b, dip=-jit(5.5) * k, bloom=jit(2.0) * k,
                                                                        back=x['nxt'], bright=F['bright']),
                 alt=lambda s=s, d=d, x=x: bloom(s, d, b, under=-jit(3.0) * k, tied=x['tied'], bright=F['bright']))
        else:
            r = rng.random()
            if r < S['push']:
                cand('push', x, score, lambda s=s, d=d: push(s, d, b, db=jit(pdb), ms=jit(160, 0.3), lift=F['lift'],
                                                              bright=F['bright']))
            elif r < S['push'] + S['bloom'] * (1 - S['push']):
                cand('bloom', x, score, lambda s=s, d=d, x=x: bloom(s, d, b, under=-jit(2.5) * k, ms=jit(300, 0.3),
                                                                     tied=x['tied'], bright=F['bright']))
        # vibrato
        vp = S['vib_peak'] if (pk or hk) else S['vib_other']
        vdepth = F['peak_vib_ct'] if (pk or hk) else F['vib_ct']
        if vdepth > 0 and secs >= 0.7 and rng.random() < vp:
            dep = jit(vdepth, 0.15) * (0.85 + 0.15 * min(e, 1.1))
            hz = jit(F['vib_hz'], 0.04)
            cand('vibrato', x, score, lambda s=s, d=d, dep=dep, hz=hz: vibrato(
                s, d, b, depth=dep, hz=hz, delay=jit(F['vib_delay'], 0.2), grow=jit(0.5, 0.2)))
        # phrase ends
        if phrase_end:
            if rng.random() < S['taper']:
                cand('taper', x, score, lambda s=s, d=d, x=x: taper(s, d, b, db=-jit(4.5) * k, frac=jit(0.45, 0.2),
                                                                     back=x['nxt'], bright=F['bright']))
            if x['rest'] >= 1.0 - _EPS and rng.random() < S['release']:
                cand('breath_release', x, score, lambda s=s, d=d, x=x: breath_release(
                    s + d, b, db=-jit(8.0), ms=jit(110, 0.25), back=x['nxt']))
            soft = e < 0.8 or n.vel < vel_mean - 4
            if soft and secs >= 0.8 and rng.random() < S['fade']:
                cand('fade_away', x, score + 0.2, lambda s=s, d=d, x=x: fade_away(s, d, b, shelf=-jit(5.0), db=-jit(2.5),
                                                                                  room=jit(3.0), back=x['nxt']))
        # the mic
        if hk and e >= 0.85 and rng.random() < S['lean']:
            pre = min(_b(0.35, b), 1.0)
            cand('lean_in', x, score + 0.5, lambda s=s, d=d, pre=pre: lean_in(
                max(0.0, s - pre), d + pre, b, db=jit(2.0) * k, prox=jit(2.5), bright=jit(1.8), room=-jit(3.0)))
        elif d >= 2.0 - _EPS and secs >= 1.8 and not phrase_end and rng.random() < S['swing']:
            cand('bell_swing', x, score, lambda s=s, d=d: bell_swing(s, d, b, seconds=jit(1.2, 0.3), shelf=-jit(3.0),
                                                                     room=jit(2.0), at=jit(0.4, 0.3)))
        elif e <= 0.6 and pk and secs >= 1.0 and rng.random() < S['fade']:
            cand('turn_away', x, score, lambda s=s, d=d: turn_away(s + 0.3 * d, 0.7 * d, b, shelf=-jit(4.0),
                                                                    room=jit(2.5)))
        # fast set pieces (a hook peak / climax)
        if (hk or (pk and climax)) and secs >= 1.2 and S['fast_every'] > 0:
            if F['shake'] and (climax or s == last_hook):
                cand('shake', x, score + 0.3, lambda s=s, d=d: shake(s + 0.45 * d, 0.5 * d, b, interval=3.0,
                                                                   hz=jit(6.5, 0.08)))
            elif F['growl'] and (climax or s == last_hook):
                cand('growl', x, score, lambda s=s, d=d: growl(s + 0.2 * d, 0.6 * d, b))

    # ---- budgets (song-wide with a Memory)
    booked = memory.booked if memory is not None else {'fast': [], 'spice': [], 'mic': [], 'pulse': []}
    saved = memory.saved if memory is not None else []
    every = {'fast': S['fast_every'], 'spice': S['spice_every'], 'mic': S['mic_every'], 'pulse': S['pulse_every']}
    budget = {f'{k}_every': v for k, v in every.items()}
    kept_before = {k: len(v) for k, v in booked.items()}
    for cat in ('fast', 'pulse', 'mic', 'spice'):
        cs = [p for p in plan if p['cat'] == cat]
        if cat == 'fast':
            cs = [p for p in cs if p['score'] >= 2.5]
            for p in plan:
                if p['cat'] == 'fast' and p not in cs:
                    p['keep'] = False
        _keep(cs, booked[cat], saved if cat == 'fast' else [], every[cat] * bpb, base, L)
    # one fast set piece per note at most (a shake OR a growl)
    gestures, log, dropped = list(fixed), [(round(g.start, 4), round(g.end, 4), g.kind, g.name) for g in fixed], []
    for p in sorted(plan, key=lambda p: p['t']):
        keep = p.get('keep', True)
        if keep:
            g = p['make']()
        elif p['alt'] is not None:
            g = p['alt']()
            dropped.append((round(p['t'], 4), p['name'], g.name))
        else:
            dropped.append((round(p['t'], 4), p['name'], None))
            continue
        if not g.shapes:
            continue
        gestures.append(g)
        log.append((round(g.start, 4), round(g.end, 4), g.kind, g.name))
    budget['kept'] = {k: len(v) - kept_before[k] for k, v in booked.items()}
    budget['dropped'] = dropped
    if memory is not None:
        memory.saved = [t for t in memory.saved if not base - _EPS <= t < base + L]
        memory.clock = base + L
    return Performance(c, gestures, b, family, log, budget)


def vocabulary(family: str = 'sax', **kw):
    """The wind player's solo vocabulary for agentsound.soloist (agentsound.horn_vocab.vocabulary): phrases from the
    soloist's shared material lines, breathed by arrange() - swells, pushes, air-coupled vibrato, scoops / falls, mic
    moves, a shake or growl at the climax.

        perf = soloist.solo(s, sax, hornist.vocabulary('sax', style='hero'), at=solo, prog=PROG, motif=HOOK)"""
    from .horn_vocab import vocabulary as _v
    return _v(family, **kw)
