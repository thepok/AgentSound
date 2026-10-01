"""A bass player's hands: named, reusable bass MOVES and an arranger that turns a chord progression (+ an optional
kick pattern to lock with) into an idiomatic, played bass line - modelled on agentsound.pianist.

User feedback 2026-09 ("möglichst realistische, nicht keyboard-artige Instrumente") and 2026-09-30 (the pianist:
"WOW!!!"; flat velocities "sound equally loud"; too many flashy fast figures = bad, spice not habit): a bassist never
plays quantised root notes at one velocity. He locks with the kick, strikes the roots on the downbeats and the
changes, walks into the next chord (chromatic / diatonic approach notes, passing tones), leaves space in the verse and
drives the chorus, ghosts dead notes in funk, pops octaves in disco, slides into the first note of a section, fills
into the next section - and does the flashy things (slides, hammer-ons, pull-offs, octave pops, rakes) rarely. This
module is both: every move is a function you can call on its own, and arrange() chooses them bar by bar from the
context (style, song part, density, the kick, seeded, budgeted, deterministic).

    from agentsound import bassist
    line = bassist.arrange(prog, bpm=126, key=s.key, style='rock', part='verse', kick=beat, seed=3)
    line.place(b.bass, verse)            # plays it (articulations mapped to the patch, slides as glides or bends)
    line.summary(), line.moves, line.budget
    mem = bassist.Memory()               # one per bassist and song: fills / flashy moves budgeted song-wide
    bassist.arrange(vprog, ..., part='verse', memory=mem, at=verse).place(b.bass, verse)
    bassist.arrange(cprog, ..., part='chorus', memory=mem, at=chorus).place(b.bass, chorus)
    b.bass.play(bassist.slide('A1', 2.0, s.tempo), sec.bar(3))                       # one move on its own

STYLES: rock (8th roots with the pick, locked to the kick), pop (roots / 5ths / octaves, 3-3-2 syncopation), country
(two-beat root-5th, walk-ups), funk (16th grooves with dead notes and octave pops), motown (melodic 1-3-5-6 lines with
chromatic approaches), disco (octave 8ths), ballad (whole / half notes with passing tones, legato), reggae (one-drop:
space on the one, laid back), tumbao (latin: the & of 2 and the anticipated 4), synth (synthwave octave pulse) and
walking (wraps patterns.walking_bass: quarter-note jazz walking). Moves (MOVES): approach, walk_up, passing,
octave_pop, slide, slide_out, hammer_on, pull_off, ghost, rake, fill (FILL_KINDS), pedal, walk.

Playability: 4-string E1-G3 (strings=5: B0-G3), a fret-hand model (check(): no position shift faster than a hand
can move, no notes outside the instrument; arrange() re-fingers what it can't reach an octave away), the plucking
hand's tempo limits (FAST: no 16th runs past 165 bpm, no 16th pairs past 200), one note at a time except the legato
overlap of slides / hammer-ons. One gesture at a time: a flashy move never shares a bar with a fill.
Touch: downbeats and chord changes strong, off-beats lighter, dead notes 20-40, phrase arcs over 4 bars, a section's
energy sets the level (verse calmer, chorus bigger). Timing: human (a few ms of seeded jitter), laid back where the
style is (reggae, ballad, motown), on top for funk and walking, swung like the drummer (a swung kick clip's 16th swing,
or swing=) - baked into the clip (don't humanize the track too).
"""

from __future__ import annotations

import math
import random

from . import articulation as _art
from .humanize import layback_ms
from .patterns import Clip, Note, _as_prog, _pedal_spans, _vel, as_clip, seed_int, walking_bass
from .theory import Chord, ComposeError, Key, chord_scale, note

__all__ = ['MOVES', 'STYLES', 'FILL_KINDS', 'FLASH', 'PARTS', 'RANGES', 'PATCHES', 'FAST', 'Memory', 'BassLine',
           'approach', 'walk_up', 'passing', 'octave_pop', 'slide', 'slide_out', 'hammer_on', 'pull_off', 'ghost',
           'rake', 'fill', 'pedal', 'walk', 'touch', 'fingering', 'check', 'arrange']

_EPS = 1e-6
_GRID = 0.25                     # the cells' resolution: 16ths

RANGES = {4: (28, 55), 5: (23, 55)}
"""Playable range per string count (MIDI): 4-string E1-G3 (the lines stay in the first 12 frets of the G string),
5-string B0-G3. Upright basses: the 4-string range."""

_OPEN = {4: (28, 33, 38, 43), 5: (23, 28, 33, 38, 43)}
_FRETS = 20

PATCHES = {
    'rock': 'sampled/rock_bass', 'pop': 'sampled/finger_bass', 'country': 'sampled/picked_bass',
    'funk': 'sampled/finger_bass', 'motown': 'sampled/flatwound_bass', 'disco': 'sampled/finger_bass',
    'ballad': 'sampled/hollow_bass', 'reggae': 'sampled/flatwound_bass', 'tumbao': 'sampled/electric_upright',
    'synth': 'layered/synth_sub_bass', 'walking': 'sampled/upright_bass',
}
"""The curated bass patch for each style (python -m agentsound find bass): Growlybass through the rock chain,
Growlybass clean (finger), the picked 5-string, flatwounds for Motown / reggae, the hollowbody for ballads, the
electric upright for latin, Meatbass for walking. Funk slap: 'sampled/slap_bass' with technique='slap'."""

PARTS = {'intro': 0.35, 'verse': 0.45, 'pre': 0.62, 'prechorus': 0.62, 'build': 0.65, 'lift': 0.65,
         'chorus': 0.85, 'post': 0.75, 'drop': 0.9, 'bridge': 0.55, 'solo': 0.7, 'breakdown': 0.3, 'break': 0.3,
         'outro': 0.5, 'end': 0.5, 'head': 0.6, 'tag': 0.6}
"""Song part -> energy (0..1) for arrange(part=...): the verse calmer (fewer notes, shorter, softer), the chorus
bigger (driving 8ths, octaves, sustained, louder), a pre-chorus building."""

FLASH = ('slide', 'slide_out', 'hammer_on', 'pull_off', 'octave_pop', 'rake', 'walk_up')
"""The flashy moves arrange() budgets (flash_every bars apart, two of a kind 2 x flash_every apart): spice, not a
habit. Fills are budgeted on their own (fill_every); approach notes, passing tones and dead notes in a funk groove
are the language and are not budgeted."""

FILL_KINDS = ('run_up', 'run_down', 'chromatic', 'octave', 'pentatonic', 'triplet', 'walk_up', 'rake',
              'sixteenths', 'slide')
"""What fill() / arrange() play into the next downbeat (the next chord's root, which is not part of the fill):
run_up / run_down (a scale run), chromatic (a chromatic walk), octave (root-octave jumps), pentatonic (a minor
pentatonic lick down), triplet (8th-note triplet chord tones), walk_up (quarter-note diatonic walk-up: country,
ballad), rake (dead notes into the one: funk), sixteenths (a funk 16th figure with dead notes), slide (a slide up the
neck to the octave, then down into the target)."""


def _cells(**kw):
    return kw


STYLES = {
    'rock': dict(cells=_cells(half=('R-------5-------', 0.0, 0.4, 1.0), quarters=('R--.R--.R--.R--.', 0.0, 0.55, 1.0),
                              eighths=('R-R-R-R-R-R-R-R-', 0.35, 1.0, 3.0), drive=('R-R-R-R-R-R-O-R-', 0.5, 1.0, 1.2),
                              fifths=('R-R-R-R-5-5-R-R-', 0.45, 1.0, 0.8), gallop=('R-RRR-RRR-RRR-RR', 0.75, 1.0, 0.4)),
                 kick=3.0, lock=0.8, gate=(0.6, 0.95), stac=0.6, late_ms=0.0, jitter_ms=5.0, vel=(90, 118),
                 approach=0.3, insert=0.25, kinds={'chromatic': 1.0, 'diatonic': 2.0, 'fifth': 1.0},
                 flash={'slide': 2.0, 'slide_out': 1.0, 'octave_pop': 0.5}, flash_every=4,
                 fills={'run_up': 2.0, 'octave': 1.5, 'chromatic': 1.0, 'run_down': 1.0, 'pentatonic': 1.0},
                 fill_every=8, fill_len={1.0: 1.0, 2.0: 2.0}, ghost=0.04, space=0.1, blue=True, melodic=False,
                 change='strike', technique='pick'),
    'pop': dict(cells=_cells(whole=('R---------------', 0.0, 0.35, 1.0), anchor=('R-----R-R-------', 0.0, 0.6, 2.0),
                             pulse=('R---5---O---5---', 0.3, 0.7, 1.5), sync=('R--R--R-R--R--R-', 0.4, 0.8, 1.5),
                             eighths=('R-R-R-R-R-R-5-O-', 0.55, 1.0, 2.0),
                             octaves=('R-O-R-O-R-O-R-O-', 0.65, 1.0, 1.0)),
                kick=3.0, lock=0.8, gate=(0.78, 0.92), stac=0.42, late_ms=3.0, jitter_ms=4.0, vel=(88, 116),
                approach=0.45, insert=0.45, kinds={'chromatic': 1.0, 'diatonic': 2.0, 'fifth': 0.7},
                flash={'slide': 1.5, 'hammer_on': 1.0, 'octave_pop': 1.0, 'pull_off': 0.5}, flash_every=4,
                fills={'run_up': 2.0, 'run_down': 1.5, 'octave': 1.0, 'pentatonic': 0.8, 'chromatic': 0.6},
                fill_every=8, fill_len={1.0: 1.5, 2.0: 1.0}, ghost=0.08, space=0.25, blue=False, melodic=False,
                change='strike', technique='finger'),
    'country': dict(cells=_cells(two=('R-------5-------', 0.0, 0.65, 3.0), low5=('R-------L-------', 0.0, 0.65, 2.0),
                                 boom=('R---5---R---L---', 0.35, 1.0, 2.0), walk=('R---3---5---p---', 0.5, 1.0, 1.0)),
                    kick=0.0, lock=0.4, gate=(0.7, 0.82), stac=0.0, late_ms=0.0, jitter_ms=5.0, vel=(86, 112),
                    approach=0.4, insert=0.4, kinds={'chromatic': 0.7, 'diatonic': 2.0, 'fifth': 1.0},
                    flash={'walk_up': 3.0, 'slide': 1.0, 'hammer_on': 1.0}, flash_every=2,
                    fills={'walk_up': 3.0, 'run_up': 1.5, 'run_down': 1.0, 'chromatic': 0.5},
                    fill_every=8, fill_len={1.0: 1.0, 2.0: 1.5}, ghost=0.0, space=0.1, blue=False, melodic=False,
                    change='strike', technique='pick'),
    'funk': dict(cells=_cells(one=('R-..x.R...x.R.x.', 0.0, 0.45, 2.0), pocket=('R-.xR.xR..x.O.7.', 0.3, 0.8, 2.0),
                              pops=('R..R..x.R.x.OR7.', 0.4, 1.0, 1.5), busy=('R-xRx.O.R.xR7.O.', 0.6, 1.0, 1.5),
                              answer=('R-.x.xR.x.R.O.xR', 0.4, 1.0, 1.0), riff=('R-.x..O7..R-b35.', 0.0, 1.0, 2.0),
                              blues=('R-.xR.b3..5.7-O.', 0.35, 1.0, 1.5)),
                 kick=0.0, lock=0.0, interlock=True, gate=(0.72, 0.82), stac=1.1, stac_slot=0.25, late_ms=-2.0,
                 jitter_ms=3.0, vel=(94, 116),
                 approach=0.3, insert=0.2, kinds={'chromatic': 2.0, 'diatonic': 1.0, 'fifth': 0.5},
                 flash={'rake': 2.0, 'hammer_on': 1.5, 'pull_off': 1.0, 'slide': 1.0, 'octave_pop': 0.8},
                 flash_every=2, fills={'sixteenths': 2.0, 'pentatonic': 1.5, 'rake': 1.0, 'octave': 1.0,
                                       'chromatic': 0.8},
                 fill_every=4, fill_len={1.0: 2.0, 2.0: 1.0}, ghost=0.3, space=0.1, blue=True, melodic=False,
                 change='strike', technique='finger'),
    'motown': dict(cells=_cells(root5=('R-----R-5-------', 0.0, 0.4, 1.5), melodic=('R--R5-6-R--R5-6-', 0.3, 0.8, 2.0),
                                climb=('R-.R3-5-6-5-3-a-', 0.4, 1.0, 1.5), octave=('R-.5O-7-R-.5O-5-', 0.5, 1.0, 1.5)),
                   kick=1.0, lock=0.5, gate=(0.72, 0.85), stac=0.55, late_ms=4.0, jitter_ms=5.0, vel=(86, 114),
                   approach=0.7, insert=0.4, kinds={'chromatic': 2.5, 'diatonic': 1.5, 'fifth': 0.5},
                   flash={'hammer_on': 1.5, 'slide': 1.0, 'pull_off': 1.0}, flash_every=2,
                   fills={'chromatic': 2.0, 'triplet': 1.5, 'run_up': 1.0, 'run_down': 1.0},
                   fill_every=8, fill_len={1.0: 1.5, 2.0: 1.0}, ghost=0.12, space=0.1, blue=False, melodic=True,
                   change='strike', technique='finger'),
    'disco': dict(cells=_cells(quarters=('R---O---R---O---', 0.0, 0.45, 1.0),
                               octaves=('R-O-R-O-R-O-R-O-', 0.3, 1.0, 3.0),
                               gallop=('R-O-R-OOR-O-R-OO', 0.6, 1.0, 1.0)),
                  kick=0.0, lock=0.5, gate=(0.45, 0.55), stac=1.1, late_ms=0.0, jitter_ms=3.0, vel=(90, 116),
                  approach=0.2, insert=0.1, kinds={'chromatic': 1.5, 'diatonic': 1.0, 'fifth': 0.5},
                  flash={'octave_pop': 1.0, 'slide': 1.0, 'rake': 0.5}, flash_every=4,
                  fills={'octave': 2.0, 'run_up': 1.0, 'chromatic': 1.0, 'sixteenths': 0.5},
                  fill_every=8, fill_len={1.0: 1.0, 2.0: 1.0}, ghost=0.08, space=0.0, blue=True, melodic=False,
                  change='strike', technique='finger'),
    'ballad': dict(cells=_cells(whole=('R---------------', 0.0, 0.5, 2.5), halves=('R-------5-------', 0.2, 0.7, 2.0),
                                passing=('R-------p-------', 0.2, 0.8, 1.5), push=('R-----R-5---p---', 0.5, 1.0, 1.5),
                                quarters=('R---R---5---O---', 0.6, 1.0, 1.0)),
                   kick=1.0, lock=0.6, gate=(0.97, 1.0), stac=0.0, late_ms=8.0, jitter_ms=6.0, vel=(78, 108),
                   approach=0.5, insert=0.55, kinds={'chromatic': 1.0, 'diatonic': 2.5, 'fifth': 0.8},
                   flash={'slide': 2.0, 'hammer_on': 0.7, 'slide_out': 1.0}, flash_every=4,
                   fills={'walk_up': 2.0, 'run_up': 1.5, 'triplet': 1.0, 'run_down': 1.0},
                   fill_every=8, fill_len={1.0: 1.0, 2.0: 2.0}, ghost=0.0, space=0.25, blue=False, melodic=True,
                   change='strike', technique='finger'),
    'reggae': dict(cells=_cells(drop=('..R--.R-5-..3-..', 0.0, 1.0, 2.0), rootsy=('R-.R-...5-.5-...', 0.0, 1.0, 1.5),
                                space=('R-----..R-----..', 0.0, 0.5, 1.0),
                                steppers=('R---R---R---R---', 0.6, 1.0, 1.0)),
                   kick=0.0, lock=0.3, gate=(0.7, 0.8), stac=0.0, late_ms=14.0, jitter_ms=6.0, vel=(84, 106),
                   approach=0.3, insert=0.2, kinds={'chromatic': 1.0, 'diatonic': 2.0, 'fifth': 0.5},
                   flash={'slide': 1.0, 'hammer_on': 1.0}, flash_every=4,
                   fills={'run_up': 1.5, 'run_down': 1.5, 'triplet': 0.5},
                   fill_every=8, fill_len={1.0: 1.0, 2.0: 1.0}, ghost=0.05, space=0.2, blue=True, melodic=True,
                   change='keep', technique='finger'),
    'tumbao': dict(cells=_cells(tumbao=('------5-----N---', 0.0, 1.0, 3.0),
                                tumbao2=('------5---5-N---', 0.4, 1.0, 1.0)),
                   kick=0.0, lock=0.0, gate=(0.9, 0.95), stac=0.0, late_ms=0.0, jitter_ms=5.0, vel=(86, 112),
                   approach=0.0, insert=0.0, kinds={'chromatic': 1.0, 'diatonic': 1.0, 'fifth': 1.0},
                   flash={'slide': 1.0}, flash_every=8,
                   fills={'run_up': 1.0, 'run_down': 1.0, 'triplet': 1.0},
                   fill_every=8, fill_len={1.0: 1.0}, land=1.0, ghost=0.0, space=0.0, blue=False, melodic=False,
                   change='keep', technique='finger'),
    'synth': dict(cells=_cells(pulse=('R-R-R-R-R-R-R-R-', 0.0, 0.5, 1.5), octaves=('R-O-R-O-R-O-R-O-', 0.3, 1.0, 3.0),
                               sixteenths=('RORORORORORORORO', 0.92, 1.0, 0.6),
                               offbeat=('..R-..R-..R-..R-', 0.0, 0.45, 1.0)),
                  kick=0.0, lock=0.3, gate=(0.8, 0.86), stac=0.0, late_ms=0.0, jitter_ms=2.0, vel=(92, 114),
                  approach=0.1, insert=0.0, kinds={'chromatic': 1.0, 'diatonic': 1.0, 'fifth': 0.5},
                  flash={'slide': 0.5}, flash_every=8,
                  fills={'octave': 2.0, 'run_up': 1.0},
                  fill_every=8, fill_len={1.0: 1.0}, ghost=0.0, space=0.0, blue=False, melodic=False,
                  change='strike', technique='synth'),
    'walking': dict(cells=_cells(), kick=0.0, lock=0.0, gate=(1.0, 1.0), stac=0.0, late_ms=None, jitter_ms=5.0,
                    vel=(78, 104), approach=0.0, insert=0.0, kinds={'chromatic': 1.0, 'diatonic': 1.0, 'fifth': 1.0},
                    flash={'slide': 1.5, 'hammer_on': 0.5}, flash_every=4,
                    fills={'triplet': 2.0, 'chromatic': 1.0, 'run_up': 1.0},
                    fill_every=8, fill_len={1.0: 1.0}, ghost=0.0, space=0.0, blue=False, melodic=True,
                    change='strike', technique='upright'),
}
"""arrange() style presets: cells {name: (16th-grid pattern per 4/4 bar, energy from, energy to, weight)} - pattern
characters R root (the slash bass), O octave, 5 fifth, L fifth below, 3 third, b the blue minor third, 7 seventh (b7
on major triads where `blue`, else the 6th), 6 sixth, 2 second, 4 fourth, N the next bar's root (anticipation), a
approach to the next note, p passing tone, x dead note, S the same note again, '-' hold (ties over bar lines), '.'
rest; kick (the weight of the 'kick' cell that doubles the kick's rhythm at low energy, when a kick is given), lock
(0..1: how tightly the line snaps to the kick), interlock (True: the one with the kick, later kicks answered in the
gaps), gate (note length x its slot at energy 0 / 1), stac (below this energy notes of up to stac_slot beats -
default 8ths - get the 'staccato' articulation; > 1 = always), late_ms / jitter_ms (timing: + = behind the beat), vel
(the top velocity at energy 0 / 1), approach (the chance of an approach note into a chord change), insert (of an
added pickup approach before a change the line holds through), kinds (approach kinds: chromatic, diatonic, fifth),
flash (FLASH move weights) + flash_every (bars), fills (FILL_KINDS weights) + fill_every (bars) + fill_len ({beats:
weight}) + land (beats before the bar line the fills land: tumbao 1 = on the anticipated 4), ghost (the chance of a
dead note before a backbeat), space (how much a sparse part leaves out), blue (b7 on major chords), melodic (higher
notes sing out a little), change ('strike' the new root on every chord change, 'keep' a style that anticipates or
leaves space), technique (pick, finger, slap, upright, synth)."""


# ------------------------------------------------------------------------------------------------ helpers

def _num(x, what: str, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ComposeError(f"{what} must be a finite number, got {x!r}")
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        rng = f"{lo:g}.." if hi is None else f"..{hi:g}" if lo is None else f"{lo:g}..{hi:g}"
        raise ComposeError(f"{what} = {x:g} is outside {rng}")
    return float(x)


def _bpm(bpm) -> float:
    return _num(bpm, 'bpm', 20, 400)


def _pos(at) -> float:
    if hasattr(at, 'start') and not isinstance(at, (int, float)):
        return float(at.start)
    return _num(at, 'at (beats)', 0)


def _sec(seconds: float, bpm: float) -> float:
    return seconds * bpm / 60.0


def _key(key) -> Key | None:
    if key is None or isinstance(key, Key):
        return key
    return Key(key)


def _chord(ch) -> Chord | None:
    return None if ch is None else Chord.parse(ch)


def _vels(vel) -> tuple[float, float]:
    if isinstance(vel, (tuple, list)):
        if len(vel) != 2:
            raise ComposeError(f"vel must be a number or (from, to), got {vel!r}")
        return _num(vel[0], 'vel', 1, 127), _num(vel[1], 'vel', 1, 127)
    v = _num(vel, 'vel', 1, 127)
    return v, v


def _range(strings) -> tuple[int, int]:
    if strings not in RANGES:
        raise ComposeError(f"bass strings must be 4 or 5, got {strings!r}")
    return RANGES[strings]


def _scale_pcs(ch=None, key=None) -> set[int]:
    """The notes a bass line walks through over `ch`: the key's scale when the chord fits it, else the chord scale,
    else the key, else C major."""
    c, k = _chord(ch), _key(key)
    if c is not None:
        tones = {(c.root + i) % 12 for i in c.intervals if i < 12} | {c.bass_pc}
        if k is not None and tones <= set(k.pcs) and len(k.pcs) >= 7:
            return set(k.pcs)
        return {(c.root + i) % 12 for i in chord_scale(c)} | tones
    if k is not None:
        return set(k.pcs)
    return {0, 2, 4, 5, 7, 9, 11}


def _step(p: int, pcs, n: int) -> int:
    """`n` scale steps from p (positive = up) inside pitch classes pcs."""
    pcs = set(pcs)
    q, d = p, (1 if n > 0 else -1)
    for _ in range(abs(n)):
        q += d
        while q % 12 not in pcs:
            q += d
    return q


def _fold(p: int, lo: int, hi: int) -> int:
    while p > hi:
        p -= 12
    while p < lo:
        p += 12
    return p if p <= hi else p - 12


def _pick(rng: random.Random, weights: dict, avoid=None):
    items = [(k, w * (0.3 if k == avoid else 1.0)) for k, w in weights.items() if w > 0]
    if not items:
        return None
    tot = sum(w for _, w in items)
    x = rng.random() * tot
    for k, w in items:
        x -= w
        if x <= 0:
            return k
    return items[-1][0]


def _n(start, dur, pitch, vel, art=None, glide=None) -> Note:
    """A note with an articulation / glide mark (articulation.note)."""
    return _art.note(float(start), float(max(0.02, dur)), int(pitch), _vel(vel), art=art, glide_ms=glide)


def _clip(notes, at: float = 0.0) -> Clip:
    ns = list(notes)
    end = max((n.start + n.dur for n in ns), default=at)
    return Clip._raw(ns, float(math.ceil(end - _EPS)) if end > 0 else 0.0)


# ------------------------------------------------------------------------------------------------ moves

def approach(target, bpm, *, kind: str = 'chromatic', above: bool = False, notes: int = 1, grid: float = 0.5,
             chord=None, key=None, vel=(78, 88), at=0.0) -> Clip:
    """Approach note(s) into `target` (not played): `notes` notes, `grid` beats each, the last one a half step
    (kind='chromatic'), a scale step (diatonic: the key's / the chord's scale) or the target's 5th (fifth: the
    dominant, from above with above=True else a 4th below) away, from below (above=False) or above; more notes walk
    towards it the same way. The target lands at at + notes x grid."""
    t = note(target)
    b = _bpm(bpm)
    a = _pos(at)
    del b
    g = _num(grid, 'approach grid', 0.05, 4)
    k = int(_num(notes, 'approach notes', 1, 8))
    if kind not in ('chromatic', 'diatonic', 'fifth'):
        raise ComposeError(f"approach kind must be 'chromatic', 'diatonic' or 'fifth', got {kind!r}")
    pcs = _scale_pcs(chord, key)
    d = 1 if above else -1
    ps = []
    for i in range(k, 0, -1):
        if kind == 'chromatic':
            ps.append(t + d * i)
        elif kind == 'diatonic':
            ps.append(_step(t, pcs, d * i))
        else:
            first = t + 7 if above else t - 5
            ps.append(first if i == 1 else _step(first, pcs, d * (i - 1)))
    v0, v1 = _vels(vel)
    out = [_n(a + i * g, g * 0.92, q, v0 + (v1 - v0) * (i / max(1, k - 1))) for i, q in enumerate(ps)]
    return _clip(out, a)


def walk_up(target, bpm, *, steps: int = 3, grid: float = 1.0, direction: str = 'up', chord=None, key=None,
            vel=(80, 94), at=0.0) -> Clip:
    """Walk-up (country, gospel, ballads): `steps` notes of the scale walking up (direction='down': down) into
    `target` (not played), one per `grid` beats (quarters), a small crescendo; the target lands at at + steps x
    grid."""
    if direction not in ('up', 'down'):
        raise ComposeError(f"walk_up direction must be 'up' or 'down', got {direction!r}")
    t = note(target)
    _bpm(bpm)
    a = _pos(at)
    g = _num(grid, 'walk_up grid', 0.1, 4)
    n = int(_num(steps, 'walk_up steps', 1, 8))
    pcs = _scale_pcs(chord, key)
    d = -1 if direction == 'up' else 1
    ps = [_step(t, pcs, d * i) for i in range(n, 0, -1)]
    v0, v1 = _vels(vel)
    return _clip([_n(a + i * g, g * 0.9, q, v0 + (v1 - v0) * i / max(1, n - 1)) for i, q in enumerate(ps)], a)


def passing(start, end, dur, bpm, *, chord=None, key=None, chromatic: bool = False, vel=(88, 76), at=0.0) -> Clip:
    """`start` struck, then the scale (chromatic=True: every half step) between it and `end` (not played) evenly
    over `dur` - the passing tones a bassist puts between two chord tones (e.g. a half note root, then the step
    towards the next root)."""
    s, e = note(start), note(end)
    _bpm(bpm)
    a = _pos(at)
    D = _num(dur, 'passing dur', 0.1)
    pcs = set(range(12)) if chromatic else _scale_pcs(chord, key)
    d = 1 if e >= s else -1
    ps = [s]
    q = s
    while True:
        q = _step(q, pcs, d)
        if (e - q) * d <= 0:
            break
        ps.append(q)
    g = D / len(ps)
    v0, v1 = _vels(vel)
    return _clip([_n(a + i * g, g * 0.95, q, v0 + (v1 - v0) * i / max(1, len(ps) - 1)) for i, q in enumerate(ps)], a)


def octave_pop(pitch, bpm, *, dur: float = 0.5, grid: float = 0.25, slap: bool = False, vel=100, at=0.0) -> Clip:
    """Octave pop: the root (thumb) then its octave popped `grid` beats later (a 16th), both short - the funk / disco
    figure. slap=True: thumb at 104-115 and the pop at 116-127 (the slap bass's slap / pop layers)."""
    p = note(pitch)
    _bpm(bpm)
    a = _pos(at)
    D = _num(dur, 'octave_pop dur', 0.1)
    g = _num(grid, 'octave_pop grid', 0.05, D)
    v0, _ = _vels(vel)
    vt, vp = (min(115.0, max(104.0, v0)), min(127.0, max(116.0, v0 + 12))) if slap else (v0, min(127.0, v0 * 1.08))
    return _clip([_n(a, g * 0.8, p, vt, 'staccato'), _n(a + g, max(0.1, (D - g) * 0.7), p + 12, vp, 'staccato')], a)


def slide(pitch, dur, bpm, *, by: int = -2, ms: float = 80.0, vel=96, at=0.0) -> Clip:
    """Slide INTO a note: the string is plucked `by` semitones away (default a whole step below, -3..-1 or +1..+3
    from above) on the beat and the finger slides to `pitch` (a glide of `ms`, 50-150), which holds for the rest of
    `dur`. A legato pair: the target carries a glide mark - on a mono='legato' sampler it glides; BassLine.place()
    turns it into a pitch bend on other instruments."""
    p = note(pitch)
    b = _bpm(bpm)
    a = _pos(at)
    D = _num(dur, 'slide dur', 0.2)
    if not 1 <= abs(int(by)) <= 7:
        raise ComposeError(f"slide by must be 1..7 semitones away (+-), got {by!r}")
    g = _num(ms, 'slide ms', 20, 600)
    d0 = min(_sec(0.02, b), D * 0.2)       # the target enters 20 ms after the pluck, gliding for `ms`
    v0, _ = _vels(vel)
    return _clip([_n(a, d0 + 0.03, p + int(by), v0), _n(a + d0, D - d0, p, v0, glide=g)], a)


def slide_out(pitch, dur, bpm, *, drop: int = -7, ms: float = 220.0, vel=92, at=0.0) -> Clip:
    """A note that slides OUT at its end: held, then in its last `ms` the finger slides `drop` semitones down the
    string (-3..-12; + = up) and lets go - the fall at a phrase or section end. A glide into a short, soft end note
    (BassLine.place() turns it into a pitch bend where the instrument can't glide)."""
    p = note(pitch)
    b = _bpm(bpm)
    a = _pos(at)
    D = _num(dur, 'slide_out dur', 0.25)
    if not 1 <= abs(int(drop)) <= 12:
        raise ComposeError(f"slide_out drop must be 1..12 semitones (+-), got {drop!r}")
    g = _num(ms, 'slide_out ms', 40, 800)
    tail = min(_sec(g / 1000.0, b), D * 0.5)
    v0, _ = _vels(vel)
    t1 = a + D - tail
    return _clip([_n(a, D - tail + 0.03, p, v0), _n(t1, tail, p + int(drop), v0 * 0.7, glide=g)], a)


def hammer_on(lower, upper, dur, bpm, *, grid: float = 0.25, vel=96, at=0.0) -> Clip:
    """Hammer-on: `lower` plucked, `upper` (1-4 semitones above) sounded by the fretting finger `grid` beats later
    without a new pluck (softer, legato: the notes overlap - a legato transition on a mono='legato' sampler), held
    for the rest of `dur`."""
    lo, hi = note(lower), note(upper)
    if not 1 <= hi - lo <= 4:
        raise ComposeError(f"hammer_on: upper must be 1-4 semitones above lower, got {lo} -> {hi}")
    _bpm(bpm)
    a = _pos(at)
    D = _num(dur, 'hammer_on dur', 0.2)
    g = _num(grid, 'hammer_on grid', 0.05, D * 0.8)
    v0, _ = _vels(vel)
    return _clip([_n(a, g + 0.03, lo, v0), _n(a + g, D - g, hi, v0 * 0.78)], a)


def pull_off(upper, lower, dur, bpm, *, grid: float = 0.25, vel=96, at=0.0) -> Clip:
    """Pull-off: `upper` plucked, the finger pulls off to `lower` (1-4 semitones below) `grid` beats later without a
    new pluck (softer, legato), held for the rest of `dur`."""
    hi, lo = note(upper), note(lower)
    if not 1 <= hi - lo <= 4:
        raise ComposeError(f"pull_off: lower must be 1-4 semitones below upper, got {hi} -> {lo}")
    _bpm(bpm)
    a = _pos(at)
    D = _num(dur, 'pull_off dur', 0.2)
    g = _num(grid, 'pull_off grid', 0.05, D * 0.8)
    v0, _ = _vels(vel)
    return _clip([_n(a, g + 0.03, hi, v0), _n(a + g, D - g, lo, v0 * 0.75)], a)


def ghost(pitch, bpm, *, dur: float = 0.12, vel=32, at=0.0) -> Clip:
    """A dead (ghost) note: the string muted by the fretting hand and plucked - a percussive thud with little pitch,
    velocity 20-40, marked with the 'mute' articulation (place() maps it to the patch's mute / ghost)."""
    p = note(pitch)
    _bpm(bpm)
    a = _pos(at)
    v0, _ = _vels(vel)
    return _clip([_n(a, _num(dur, 'ghost dur', 0.03, 1.0), p, v0, 'mute')], a)


def rake(target, dur, bpm, *, grid: float = 0.25, vel=(24, 44), at=0.0) -> Clip:
    """Rake: dead notes (16ths) raked into a downbeat, crescendo - the funk pickup into the one; the target (not
    played) lands at at + dur."""
    t = note(target)
    _bpm(bpm)
    a = _pos(at)
    D = _num(dur, 'rake dur', 0.1)
    g = _num(grid, 'rake grid', 0.05, D)
    n = max(1, int(D / g + _EPS))
    v0, v1 = _vels(vel)
    s0 = a + D - n * g
    return _clip([_n(s0 + i * g, g * 0.5, t, v0 + (v1 - v0) * i / max(1, n - 1), 'mute') for i in range(n)], a)


def pedal(pitch, dur, bpm, *, grid: float = 0.5, octave: float = 0.0, accent: float = 1.15, vel=86, seed=0,
          at=0.0) -> Clip:
    """Pedal point: `pitch` repeated every `grid` beats for `dur` (the pulse under changing chords), the beats
    accented (x accent), now and then (octave = chance per off-beat) the octave above."""
    p = note(pitch)
    _bpm(bpm)
    a = _pos(at)
    D = _num(dur, 'pedal dur', 0.1)
    g = _num(grid, 'pedal grid', 0.1, 8)
    rng = random.Random(seed_int(seed))
    v0, _ = _vels(vel)
    out = []
    n = max(1, int(D / g + _EPS))
    for i in range(n):
        t = i * g
        on = abs(t - round(t)) < _EPS
        q = p + 12 if (not on and rng.random() < octave) else p
        out.append(_n(a + t, g * 0.85, q, v0 * (accent if on else 1.0) * (1.0 + (rng.random() - 0.5) * 0.06)))
    return _clip(out, a)


def fill(kind, target, dur, bpm, *, chord=None, key=None, grid: float | None = None, low='E1', high='G3',
         vel=(76, 100), seed=0, at=0.0) -> Clip:
    """A fill (FILL_KINDS) over `dur` beats leading into `target` (the next chord's root, not played, landing at at +
    dur): run_up / run_down (scale), chromatic, octave (root-octave jumps then an approach), pentatonic (minor
    pentatonic down), triplet (8th-note triplets up the chord), walk_up (quarters), rake (dead notes), sixteenths (funk
    16ths with dead notes), slide (up the neck to the octave, then down into the target). `chord` = the chord the fill
    plays over (default the target's), grid = the note value (8ths; 16ths for sixteenths / rake, 1/3 for triplets,
    quarters for walk_up); crescendo vel[0] -> vel[1]; everything stays inside low..high."""
    if kind not in FILL_KINDS:
        raise ComposeError(f"fill kind must be one of {', '.join(FILL_KINDS)}, got {kind!r}")
    t = note(target)
    b = _bpm(bpm)
    a = _pos(at)
    D = _num(dur, 'fill dur', 0.25)
    lo, hi = note(low), note(high)
    rng = random.Random(seed_int(seed))
    c = _chord(chord)
    pcs = _scale_pcs(c, key)
    v0, v1 = _vels(vel)
    default_grid = {'triplet': 1.0 / 3.0, 'walk_up': 1.0, 'rake': 0.25, 'sixteenths': 0.25}.get(kind, 0.5)
    g = _num(grid if grid is not None else default_grid, 'fill grid', 0.1, 2)
    n = max(1, int(D / g + _EPS))
    s0 = a + D - n * g

    def line(ps, arts=None, gate=0.92):
        out = []
        for i, q in enumerate(ps):
            x = i / max(1, len(ps) - 1)
            ar = arts[i] if arts else None
            v = v0 + (v1 - v0) * x
            if ar == 'mute':
                v = min(44.0, 24.0 + 20.0 * x)
            out.append(_n(s0 + i * g, g * (0.45 if ar == 'mute' else gate), _fold(q, lo, hi), v, ar))
        return _clip(out, a)

    root = _fold((c.bass_pc if c is not None else t % 12) + 12 * (lo // 12), lo, hi)
    while root + 12 <= t and root + 12 <= hi:
        root += 12
    if kind in ('run_up', 'walk_up'):
        start = _step(t, pcs, -n)
        if start < lo:
            kind = 'run_down'
        else:
            return line([_step(t, pcs, -i) for i in range(n, 0, -1)], gate=0.9 if kind == 'walk_up' else 0.92)
    if kind == 'run_down':
        start = _step(t, pcs, n)
        if start > hi:
            return line([_step(t, pcs, -i) for i in range(n, 0, -1)])
        return line([_step(t, pcs, i) for i in range(n, 0, -1)])
    if kind == 'chromatic':
        d = -1 if t - n >= lo else 1
        return line([t + d * i for i in range(n, 0, -1)])
    if kind == 'octave':
        ps = []
        base = root if root + 12 <= hi else root - 12
        for i in range(n - 1):
            ps.append(base + (12 if i % 2 else 0))
        ps.append(t - 1 if t - 1 >= lo else t + 1)
        return line(ps, gate=0.8)
    if kind == 'pentatonic':
        # a minor-pentatonic lick stepping down into the target: it starts n scale steps above it, so every
        # interval is a pentatonic step (no leap at the end) - where the neck has no room above, it climbs instead
        r = c.root if c is not None else t % 12
        pent = {(r + i) % 12 for i in (0, 3, 5, 7, 10)}
        if _step(t, pent, n) <= hi:
            ps = [_step(t, pent, i) for i in range(n, 0, -1)]
        else:
            ps = [_step(t, pent, -i) for i in range(n, 0, -1)]
        return line(ps, gate=0.85)
    if kind == 'triplet':
        # chord tones arpeggiated towards the target (up into it from below, else down into it from above), the
        # last one a half step away: the line lands, it never leaps an octave at the end
        base_pc = c.root if c is not None else root
        pcs_ = {(base_pc + i) % 12 for i in (c.intervals if c is not None else (0, 4, 7))} | {root % 12}
        tones = [q for q in range(lo, hi + 1) if q % 12 in pcs_]
        below = [q for q in tones if q < t - 1]
        above = [q for q in tones if q > t + 1]
        if len(below) >= n - 1 and t - 1 >= lo:
            ps = below[len(below) - (n - 1):] + [t - 1]
        elif len(above) >= n - 1 and t + 1 <= hi:
            ps = above[:n - 1][::-1] + [t + 1]
        else:
            ps = [t - 1 if t - 1 >= lo else t + 1] * n
        return line(ps[-n:], gate=0.95)
    if kind == 'rake':
        return rake(t, D, b, grid=g, at=a)
    if kind == 'sixteenths':
        r = root
        seven = r + (11 if c is not None and 11 in c.intervals and 10 not in c.intervals else 10)
        up = r + 12 if r + 12 <= hi else r
        fig = [(r, None), (r, 'mute'), (seven if seven <= hi else seven - 12, None), (up, None), (up, 'mute'),
               (r + 7 if r + 7 <= hi else r - 5, None), (r, 'mute'), (t - 1 if t - 1 >= lo else t + 1, None)]
        seq = fig[-n:] if n <= len(fig) else [fig[i % len(fig)] for i in range(n - 1)] + [fig[-1]]
        return line([q for q, _ in seq], [x for _, x in seq], gate=0.6)
    if kind == 'slide':
        up = root + 12 if root + 12 <= hi else root
        half = max(g, D * 0.5)
        g_ms = min(400.0, max(120.0, half * 0.6 * 60000.0 / b))
        out = [_n(a, 0.12, root, v0), _n(a + 0.08, half - 0.05, up, v0 * 1.05, glide=g_ms)]
        rest = D - half
        m = max(1, int(rest / 0.5 + _EPS))
        for i in range(m):
            q = _step(t, pcs, m - i) if i < m - 1 else (t + 1 if t + 1 <= hi else t - 1)
            out.append(_n(a + half + i * rest / m, rest / m * 0.9, _fold(q, lo, hi), v0 + (v1 - v0) * (i + 1) / m))
        return _clip(out, a)
    del rng
    return _clip([], a)


def walk(prog, bpm, *, key=None, feel: str = 'four', low='E1', high='G3', vel: float = 90, seed=0, skip: float = 0.12,
         approach: str = 'mixed', pedal=None, length=4.0) -> Clip:
    """A walking line: patterns.walking_bass (the planned quarter-note walk: roots on the one, chord tones on 3,
    approaches into every change - wrapped, not duplicated) with the bassist's touch (the one and the changes
    stronger, approaches lighter, the skip notes as dead notes at 25-40) - straight 8ths (swing it with the feel)."""
    b = _bpm(bpm)
    c = walking_bass(prog, key=key, feel=feel, low=low, high=high, seed=seed, vel=vel, skip=skip, approach=approach,
                     pedal=pedal, length=length)
    p = _as_prog(prog, key, length)
    starts = {round(st, 4) for st, _, ch in p if ch is not None}
    out = []
    for n in c:
        if n.vel <= vel * 0.6:
            out.append(_n(n.start, n.dur, n.pitch, max(24, min(40, n.vel * 0.6)), 'mute'))
        else:
            w = 1.0 if round(n.start, 4) in starts else 0.9 if abs(n.start % 2) < _EPS else 0.84
            out.append(_n(n.start, n.dur, n.pitch, vel * w * (n.vel / vel) ** 0.5))
    del b
    return Clip._raw(out, c.length)


MOVES = {'approach': approach, 'walk_up': walk_up, 'passing': passing, 'octave_pop': octave_pop, 'slide': slide,
         'slide_out': slide_out, 'hammer_on': hammer_on, 'pull_off': pull_off, 'ghost': ghost, 'rake': rake,
         'fill': fill, 'pedal': pedal, 'walk': walk}
"""Every bass move by name -> its function (each returns a Clip starting at `at`; call it on its own or let
arrange() choose)."""


# ------------------------------------------------------------------------------------------------ touch

def touch(clip, lo: float = 76, hi: float = 112, *, beats_per_bar: float = 4, phrase: float = 4, melodic: bool = False,
          kick=(), changes=(), ghost=(22, 40), seed=0) -> Clip:
    """A bassist's touch: the velocities written from the groove instead of one level (the bass counterpart of
    humanize.touch, which shapes a melody). Metric weight per note - the one hi, beat 3 ~0.85, beats 2 / 4 ~0.78, off
    8ths ~0.66, 16ths ~0.56 of the way from lo to hi - plus the chord changes (+0.08) and the notes on the kick
    (`kick` onsets, +0.06); an arc over each `phrase` bars (+-3 %); melodic=True: higher notes sing out (0.5 velocity
    per semitone over the bar's mean, at most +-6). Dead notes (the 'mute' mark) get `ghost` (20-40). Seeded +-2."""
    c = as_clip(clip)
    lo_, hi_ = _num(lo, 'touch lo', 1, 127), _num(hi, 'touch hi', 1, 127)
    if hi_ < lo_:
        raise ComposeError(f"bass touch hi ({hi_:g}) must be >= lo ({lo_:g})")
    bpb = _num(beats_per_bar, 'beats_per_bar', 1, 16)
    ph = _num(phrase, 'phrase (bars)', 1, 64) * bpb
    g0, g1 = _vels(ghost)
    rng = random.Random(seed_int(seed))
    ks = [round(float(k), 3) for k in kick]
    chs = [round(float(x), 3) for x in changes]
    bars: dict[int, list[int]] = {}
    for n in c:
        bars.setdefault(int(n.start // bpb), []).append(n.pitch)
    out = []
    for n in c:
        if _art.articulation_of(n) == 'mute':
            out.append(n._replace(vel=_vel(g0 + (g1 - g0) * rng.random())))
            continue
        w = _metric(n.start, bpb)
        if any(abs(n.start - x) < 0.02 for x in chs):
            w += 0.08
        if any(abs(n.start - x) < 0.02 for x in ks):
            w += 0.06
        v = lo_ + (hi_ - lo_) * min(1.05, w)
        x = (n.start % ph) / ph
        v *= 1.0 + 0.06 * (math.sin(math.pi * x) - 0.5)
        if melodic:
            ps = bars[int(n.start // bpb)]
            v += max(-6.0, min(6.0, 0.5 * (n.pitch - sum(ps) / len(ps))))
        v += (rng.random() - 0.5) * 4.0
        out.append(n._replace(vel=_vel(min(127.0, v))))
    return Clip._raw(out, c.length)


def _metric(t: float, bpb: float) -> float:
    pos = t % bpb
    if pos < 0.02 or bpb - pos < 0.02:
        return 1.0
    b = round(pos)
    if abs(pos - b) < 0.02:
        return 0.86 if (abs(bpb - 4.0) < _EPS and b == 2) else 0.78
    if abs(pos * 2 - round(pos * 2)) < 0.04:
        return 0.66
    return 0.56


# ------------------------------------------------------------------------------------------------ playability

def _hand_time(d: int) -> float:
    """Seconds the fretting hand needs to shift `d` frets (0: none)."""
    return 0.0 if d <= 0 else 0.06 + 0.012 * d


def _fingering(notes, bpm: float, strings: int):
    """(plan, breaks): the fingering DP of fingering(); breaks = indices of notes no fingering reaches in time from
    the note before (the plan restarts there)."""
    opens = _OPEN.get(strings)
    if opens is None:
        raise ComposeError(f"bass strings must be 4 or 5, got {strings!r}")
    def opts(p):
        out = []
        for s, o in enumerate(opens):
            f = p - o
            if 0 <= f <= _FRETS:
                out.extend((s, f, h) for h in ([None] if f == 0 else range(max(1, f - 3), f + 1)))
        return out
    hist: list = []           # per note: {state: (cost, hand, previous state)}
    breaks: list = []
    prev_t = None
    for i, n in enumerate(notes):
        cand = opts(n.pitch)
        dt = 1e9 if prev_t is None else (n.start - prev_t) * 60.0 / bpm
        states = hist[-1] if hist else {}
        new: dict = {}
        for st in cand:
            s, f, h = st
            if not states:
                new[st] = ((0.3 * (f - 7) if f > 7 else 0.0), h, None)
                continue
            best = None
            for st0, (c0, hand0, _) in states.items():
                d = 0 if (h is None or hand0 is None) else abs(h - hand0)
                if _hand_time(d) > dt + 1e-9:
                    continue
                cost = c0 + d * 0.5 + abs(s - st0[0]) * 0.15 + (0.3 * (f - 7) if f > 7 else 0.0)
                if best is None or cost < best[0]:
                    best = (cost, h if h is not None else hand0, st0)
            if best is not None:
                new[st] = best
        if not new and cand:
            if states:
                breaks.append(i)
            new = {st: (0.0, st[2], None) for st in cand}
        hist.append(new)
        prev_t = n.start
    plan: list = [None] * len(notes)
    cur = None
    for i in range(len(notes) - 1, -1, -1):
        if not hist[i]:
            cur = None
            continue
        if cur is None or cur not in hist[i]:
            cur = min(hist[i], key=lambda k: hist[i][k][0])
        plan[i] = (cur[0], cur[1])
        cur = hist[i][cur][2]
    return plan, breaks


def fingering(clip, bpm, *, strings: int = 4) -> list:
    """A fretting-hand plan for a bass line: [(string index 0 = lowest, fret)] per note (in time order), found by a
    dynamic programme that keeps the hand in position (a 4-fret span, open strings free) and only shifts as far as
    the time between the notes allows (a shift of d frets takes ~60 ms + 12 ms per fret). None for a note out of
    range; check() lists the jumps no fingering can make."""
    c = sorted(as_clip(clip), key=lambda n: (n.start, n.pitch))
    return _fingering(c, _bpm(bpm), strings)[0]


def check(clip, bpm, *, strings: int = 4, low=None, high=None, max_overlap: float = 0.08) -> list[str]:
    """Playability problems of a bass line ([] = playable): notes outside the instrument's range (RANGES, or
    low..high), more than one note at a time beyond a legato overlap of `max_overlap` beats (slides and hammer-ons tie
    their notes by ~0.03), and position jumps the fretting hand can't make in time (fingering())."""
    c = sorted(as_clip(clip), key=lambda n: (n.start, n.pitch))
    b = _bpm(bpm)
    lo, hi = _range(strings)
    lo = note(low) if low is not None else lo
    hi = note(high) if high is not None else hi
    out = []
    for n in c:
        if not lo <= n.pitch <= hi:
            out.append(f"beat {n.start:.2f}: pitch {n.pitch} outside {lo}..{hi}")
    for a, n in zip(c, c[1:]):
        if n.start - a.start < 0.02 and n.pitch != a.pitch:
            out.append(f"beat {n.start:.2f}: two notes at once ({a.pitch}, {n.pitch})")
        elif a.start + a.dur > n.start + max_overlap:
            out.append(f"beat {n.start:.2f}: note {a.pitch} still sounding {a.start + a.dur - n.start:.2f} beats "
                       f"into the next")
    _, breaks = _fingering(c, b, strings)
    for i in breaks:
        dt = (c[i].start - c[i - 1].start) * 60.0 / b
        out.append(f"beat {c[i].start:.2f}: jump {c[i - 1].pitch} -> {c[i].pitch} in {dt * 1000:.0f} ms: no fingering "
                   f"reaches it in time")
    return out


# ------------------------------------------------------------------------------------------------ budget memory

class Memory:
    """What one bassist already played in a song. Pass the same Memory to every arrange() call of the song
    (memory=, with at= the clip's position in beats; without at= each call follows the previous one) and the budgets
    count song-wide: a fill into the chorus keeps the next fill fill_every bars away, a slide in the verse keeps the
    chorus from sliding at once. played(at, kind) books a move placed by hand. .fills / .flash: [(beat, kind)]."""

    def __init__(self):
        self.fills: list = []
        self.flash: list = []
        self.clock = 0.0

    def played(self, at, kind: str) -> 'Memory':
        """Book a move played outside arrange() at beat `at` (a FILL_KINDS name / 'fill', or a FLASH move)."""
        t = _pos(at)
        if kind in FLASH:
            self.flash.append((t, kind))
        elif kind in FILL_KINDS or kind == 'fill':
            self.fills.append((t, kind))
        else:
            raise ComposeError(f"Memory.played: {kind!r} is not a budgeted move ({', '.join(FLASH)}, fill)")
        return self

    def __repr__(self) -> str:
        return (f"Memory({len(self.fills)} fills: {', '.join(f'{k}@{t:g}' for t, k in self.fills)}; "
                f"{len(self.flash)} flash; clock {self.clock:g})")


# ------------------------------------------------------------------------------------------------ the result

class BassLine:
    """What arrange() played: clip (the notes, relative to the clip start, with articulation marks 'staccato' /
    'mute' and glide marks on slides), moves (a log: (start, end, kind, name) with kind 'groove' | 'approach' | 'fill'
    | 'move' | 'ghost' | 'space' | 'pedal' | 'ending'), budget (fill_every / flash_every, the fills and flashy moves
    kept, the ones dropped), locked (the share of kick onsets the bass plays with), problems (check()), swing (the
    16th swing played, None = straight).
    place(track, at) plays it on a track: articulations mapped to what the patch has, slides as glides (mono='legato'
    samplers) or pitch bends (other samplers, sf2, dx7, stacks). summary() counts what was used."""

    def __init__(self, clip: Clip, moves: list, budget: dict, bpm: float, locked: float | None, problems: list):
        self.clip, self.moves, self.budget, self.bpm = clip, moves, budget, bpm
        self.locked, self.problems = locked, problems
        self.swing: float | None = None

    def __repr__(self) -> str:
        lk = '' if self.locked is None else f", {self.locked:.0%} of the kick locked"
        return f"BassLine({len(self.clip)} notes{lk}, {self.summary()})"

    def summary(self) -> dict:
        out: dict = {}
        for _, _, kind, name in self.moves:
            out[f"{kind}:{name}"] = out.get(f"{kind}:{name}", 0) + 1
        return dict(sorted(out.items()))

    @property
    def fills(self) -> list:
        return [(a, b, n) for a, b, k, n in self.moves if k == 'fill']

    @property
    def flashy(self) -> list:
        return [(a, b, n) for a, b, k, n in self.moves if k == 'move']

    def adapted(self, track) -> tuple[Clip, list]:
        """(clip, pitch-bend points) for `track`: articulation marks mapped to the track's keyswitches ('staccato'
        -> its staccato, 'mute' -> its mute / ghost / dead note; dropped where it has none), and slides kept as glide
        marks on a mono='legato' sampler, else merged into one plucked note + 'instrument.pitchbend' points (samplers,
        sf2, dx7, stacks) or dropped (instruments without a pitch bend). Points are relative to the clip start."""
        ins = getattr(track, 'instrument', None)
        typ = getattr(ins, 'type', None)
        params = getattr(ins, 'params', {}) or {}
        names = _art.available(track) if typ == 'sampler' else []
        amap = {'staccato': _find_art(names, ('staccato', 'stac', 'short')),
                'mute': _find_art(names, ('mute', 'ghost', 'dead'))}
        ns = []
        for n in self.clip:
            a = _art.articulation_of(n)
            if a in amap:
                ns.append(_art._mark(n, art=amap[a]))
            else:
                ns.append(n)
        clip = Clip._raw(ns, self.clip.length)
        if typ == 'sampler' and params.get('mono') == 'legato':
            return clip, []
        return _slides_to_bends(clip, self.bpm, bend=typ in ('sampler', 'sf2', 'dx7', 'stack'))

    def place(self, track, at=0.0):
        """track.play(the adapted clip, at) + the slide bends at `at`. Returns the track."""
        a = _pos(at)
        clip, pts = self.adapted(track)
        track.play(clip, a)
        if pts:
            track.automate('instrument.pitchbend', [(p[0] + a,) + tuple(p[1:]) for p in pts])
        return track


def _find_art(names, words):
    low = [(n, n.lower()) for n in names]
    for w in words:
        for n, l in low:
            if l == w or l.split()[0:1] == [w]:
                return n
    for w in words:
        for n, l in low:
            if l.startswith(w) or f' {w}' in l:
                return n
    return None


def _slides_to_bends(clip: Clip, bpm: float, bend: bool = True) -> tuple[Clip, list]:
    """Merge glide-marked notes into the plucked note before them and return (clip, pitch-bend points): the plucked
    note is held through the glided ones, the bend moves to each glided pitch over its glide time and steps back to 0
    once the chain has ended. bend=False drops the glides (the target notes stay, unmarked; slide-in grace notes and
    slide-out tails go)."""
    ns = sorted(clip, key=lambda n: (n.start, n.pitch))
    out: list = []
    pts: list = []
    i = 0
    while i < len(ns):
        n = ns[i]
        chain = [n]
        j = i + 1
        while j < len(ns) and _art.glide_of(ns[j]) and ns[j].start < chain[-1].start + chain[-1].dur + 1e-6:
            chain.append(ns[j])
            j += 1
        if len(chain) == 1:
            out.append(n if not _art.glide_of(n) else _art._mark(n, gl=None))
            i += 1
            continue
        if not bend:
            main = max(chain, key=lambda x: x.dur)
            out.append(_art._mark(main, gl=None)._replace(start=chain[0].start,
                                                           dur=main.start + main.dur - chain[0].start))
            i = j
            continue
        base = chain[0]
        end = chain[-1].start + chain[-1].dur
        out.append(_art._mark(base, gl=None)._replace(dur=end - base.start))
        off = 0.0
        pts.append((round(max(0.0, base.start), 6), 0.0))
        for x in chain[1:]:
            g = _sec(_art.glide_of(x) / 1000.0, bpm)
            tgt = float(x.pitch - base.pitch)
            s0 = x.start
            pts.append((round(s0, 6), off))
            pts.append((round(s0 + min(g, max(0.02, x.dur * 0.9)), 6), tgt, 'smooth'))
            off = tgt
        nxt = ns[j].start if j < len(ns) else end + 0.25
        r = max(pts[-1][0] + 0.005, min(end + 0.02, nxt - 0.01))
        pts.append((round(r - 0.004, 6), off))
        pts.append((round(r, 6), 0.0, 'step'))
        i = j
    # strictly increasing beats (a later point on the same beat wins)
    clean: list = []
    for p in pts:
        if clean and p[0] <= clean[-1][0] + 1e-9:
            if abs(p[0] - clean[-1][0]) < 1e-9:
                clean[-1] = p
            continue
        clean.append(p)
    return Clip._raw(out, clip.length), clean


# ------------------------------------------------------------------------------------------------ the arranger

def _keep_pairs(new: Clip, old: Clip) -> Clip:
    """After humanize_starts (which moves every onset on its own): a note tied into the next one (a slide's pluck
    into its glide, a hammer-on / pull-off pair) moves with it - the pair keeps its written distance and overlap."""
    olds = sorted(old, key=lambda n: (n.start, n.pitch))
    pool = list(new)
    used = [False] * len(pool)
    match = []
    for n in olds:
        best, bi = None, -1
        for i, m in enumerate(pool):
            if used[i] or m.pitch != n.pitch:
                continue
            d = abs(m.start - n.start)
            if best is None or d < best:
                best, bi = d, i
        if bi < 0:
            return new
        used[bi] = True
        match.append(pool[bi])
    out = list(match)
    for i in range(1, len(olds)):
        a, n = olds[i - 1], olds[i]
        if a.start + a.dur > n.start + 1e-3 and n.start - a.start < 0.5:
            s = out[i - 1].start + (n.start - a.start)
            out[i] = out[i]._replace(start=s, dur=n.dur)
            keep = s + (a.start + a.dur - n.start) - out[i - 1].start
            out[i - 1] = out[i - 1]._replace(dur=max(out[i - 1].dur, keep))
    return Clip._raw(out, new.length)


def _drop(p: int, lo: int, hi: int, rng: random.Random) -> int:
    """How far a slide-out travels from p: down the string (-7, -5, -12, -3) while it stays on the instrument, else up
    the neck (+5, +7) - a real finger can't slide below the open string."""
    downs = [d for d in (-7, -5, -12, -3) if p + d >= lo]
    if downs:
        return rng.choice(downs[:3] if len(downs) >= 3 else downs)
    ups = [d for d in (5, 7) if p + d <= hi]
    return rng.choice(ups) if ups else 0


def _kick_onsets(kick, L: float, bpb: float) -> tuple[list[float], float | None]:
    """(kick onsets on the 16th grid over 0..L, the kick's 16th swing or None). A drum clip that is swung or
    humanized is read on its grid (each kick snapped to the nearest 16th within a 32nd), so the bass locks /
    interlocks with the kick it hears; the swing is the mean delay of the kicks on the off 16ths (the e / a),
    as a humanize.swing amount (0.55 = 0.025 beats late). Kicks further than 0.07 beats off the grid (triplets,
    a shuffle) stay where they are."""
    if kick is None:
        return [], None
    sw = None
    if isinstance(kick, str):
        cells = [ch for ch in kick if ch not in ' |']
        if not cells or set(cells) - set('xXo.-_'):
            raise ComposeError(f"kick pattern must be a 16th grid of x / . (e.g. 'x.....x.x.......'), got {kick!r}")
        on = [i * _GRID for i, ch in enumerate(cells) if ch in 'xXo']
        span = len(cells) * _GRID
    else:
        c = as_clip(kick)
        ks = [n.start for n in c if n.pitch in (35, 36)]
        raw = sorted(set(ks if ks else [n.start for n in c]))
        on, late = [], []
        for x in raw:
            j = round(x / _GRID)
            if abs(x - j * _GRID) <= 0.07:
                on.append(j * _GRID)
                if j % 2 == 1:
                    late.append(x - j * _GRID)
            else:
                on.append(x)
        if late and sum(late) / len(late) > 0.01:            # (humanize jitter alone stays under it)
            sw = min(0.8, 0.5 + (sum(late) / len(late)) / (2 * _GRID))
        on = sorted(set(round(x, 4) for x in on))
        span = c.length or bpb
    out = []
    t = 0.0
    while t < L - _EPS:
        out += [t + x for x in on if t + x < L - _EPS]
        t += span
    return sorted(set(round(x, 4) for x in out)), sw


def _swing(clip: Clip, amount: float, grid: float = _GRID) -> Clip:
    """The line's 16ths swung like the drummer's: a time warp inside every 8th (the first 16th stretched to
    amount x the 8th, the second squeezed), applied to note starts AND ends - so an off-16th note moves by the
    swing delay (as humanize.swing), and the pairs of a slide / hammer-on (a pluck and a note 20-40 ms later)
    move together instead of crossing."""
    a = float(amount)
    if abs(a - 0.5) < 1e-9:
        return clip

    def warp(t):
        cell = math.floor(t / (2 * grid) + 1e-9)
        x = t - cell * 2 * grid
        y = x * 2 * a if x <= grid else 2 * a * grid + (x - grid) * (2 - 2 * a)
        return cell * 2 * grid + y

    out = []
    for n in clip:
        s = warp(n.start)
        e = warp(n.start + n.dur)
        out.append(n._replace(start=s, dur=max(0.02, e - s)))
    return Clip._raw(out, clip.length)


FAST = {3: 165.0, 2: 200.0}
"""Tempo limits of a bass player's plucking hand (fingers, pick, thumb): a groove cell with a run of 3+ 16th-note
attacks (dead notes count) only up to 165 bpm (16ths every ~90 ms), 16th pairs (a gallop, an octave pop) only up to
200 bpm. arrange() leaves out the cells that break them (not for technique='synth')."""


def _fast_ok(pat: str, bpm: float) -> bool:
    run = best = 0
    for ch in pat + pat:                 # the bar repeats: a run can cross the bar line
        run = run + 1 if ch not in '-.' else 0
        best = max(best, run)
    return all(bpm <= lim + _EPS for n, lim in FAST.items() if best >= n)


def _bar_pattern(pat: str, bpb: float) -> str:
    n = int(round(bpb / _GRID))
    return pat[:n] if len(pat) >= n else (pat * (n // len(pat) + 1))[:n]


def _deg(ch: Chord, tok: str, blue: bool) -> int:
    iv = {i % 12 for i in ch.intervals}
    third = 3 if (3 in iv and 4 not in iv) else 4 if 4 in iv else 5 if 5 in iv else 2 if 2 in iv else 4
    fifth = 7 if 7 in iv else 6 if 6 in iv else 8 if 8 in iv else 7
    if 10 in iv:
        sev = 10
    elif 11 in iv:
        sev = 11
    elif 9 in iv:
        sev = 9
    else:
        sev = 10 if (third == 3 or blue) else 9
    sc = set(chord_scale(ch))
    six = 9 if 9 in sc else 8
    return {'3': third, '5': fifth, 'L': fifth - 12, '7': sev, '6': six, '2': 2 if 2 in sc else 1, '4': 5,
            'O': 12, 'b': 3}[tok]


def _reach(evs: list, bpm: float, strings: int, lo: int, hi: int, changes, bpb: float) -> list:
    """Fast tempos: where the fretting hand can't reach a note in time (the fingering() model, with a 15 % margin
    for the timing jitter), the line moves an octave the way a player re-fingers it - the chord span that starts
    with the unreachable note (an octave figure moves as one; the approach note into it too), else the span before
    it, else the single note (not an approach); kept only when it leaves fewer unreachable jumps. evs: time-ordered
    events with pitches, one onset each."""
    def breaks():
        return _fingering([_Pt(ev.t, ev.p) for ev in evs], bpm * 1.15, strings)[1]

    def span(t):
        a = max([c for c in changes if c <= t + _EPS] + [math.floor(t / bpb + _EPS) * bpb])
        z = min([c for c in changes if c > t + _EPS] + [(math.floor(t / bpb + _EPS) + 1) * bpb])
        js = [j for j, ev in enumerate(evs) if a - _EPS <= ev.t < z - _EPS]
        if js and js[0] > 0 and evs[js[0] - 1].kind == 'approach' and evs[js[0]].t - evs[js[0] - 1].t <= 1.0 + _EPS:
            js.insert(0, js[0] - 1)          # the approach note moves with the note it leads into
        return js

    br = breaks()
    for _ in range(4 * len(br) + 4):
        if not br:
            break
        i = br[0]
        fixed = None
        singles = [[j] for j in (i, i - 1) if evs[j].kind != 'approach']
        for grp in [span(evs[i].t), span(evs[i - 1].t)] + singles:
            for sh in (12, -12):
                if not all(lo <= evs[j].p + sh <= hi for j in grp):
                    continue
                for j in grp:
                    evs[j].p += sh
                nb = breaks()
                if len(nb) < len(br):
                    fixed = nb
                    break
                for j in grp:
                    evs[j].p -= sh
            if fixed is not None:
                break
        if fixed is None:
            break
        br = fixed
    return evs


def _pluck_limit(evs: list, bpm: float, changes) -> list:
    """The plucking hand's tempo limit (FAST) as a last guard: above FAST[3] bpm no three plucked attacks in a row
    a 16th apart, above FAST[2] no two - the weakest note of such a run goes (a dead note first, then an approach /
    passing note, then an off-beat note; never a note on a beat or a chord change, never a fill / move note). Legato
    notes (a glide target, a hammer-on / pull-off's second note) are not plucked and don't count."""
    if bpm <= FAST[3] + _EPS:
        return evs

    def plucked(ev):
        return not ev.glide and ev.w != 'legato'

    def rank(ev):                      # higher = goes first; None = keep
        if ev.fixed or ev.t % 1.0 < 0.02 or any(abs(ev.t - c) < 0.02 for c in changes):
            return None
        return 3 if ev.kind == 'ghost' else 2 if ev.kind == 'approach' else 1

    out = list(evs)
    stuck: set = set()                 # runs of protected notes only: left as they are
    for _ in range(2 * len(evs) + 1):
        ps = [ev for ev in out if plucked(ev)]
        run = None
        for i in range(len(ps) - 1):
            if bpm > FAST[2] + _EPS and ps[i + 1].t - ps[i].t < _GRID + 0.02:
                r = ps[i:i + 2]
            elif i + 2 < len(ps) and ps[i + 2].t - ps[i].t < 2 * _GRID + 0.02:
                r = ps[i:i + 3]
            else:
                continue
            if tuple(id(x) for x in r) not in stuck:
                run = r
                break
        if run is None:
            break
        cand = [(rank(ev), -ev.t) for ev in run]
        best = max((c for c in cand if c[0] is not None), default=None)
        if best is None:
            stuck.add(tuple(id(x) for x in run))
            continue
        victim = run[cand.index(best)]
        out = [ev for ev in out if ev is not victim]
    return out


class _Pt:
    __slots__ = ('start', 'pitch')

    def __init__(self, start, pitch):
        self.start, self.pitch = start, pitch


class _Ev:
    __slots__ = ('t', 'd', 'tok', 'p', 'kind', 'art', 'glide', 'tie', 'w', 'vel', 'fixed')

    def __init__(self, t, d, tok, kind='note'):
        self.t, self.d, self.tok, self.p, self.kind = t, d, tok, None, kind
        self.art = self.glide = None
        self.tie = False
        self.w = None           # a metric-weight override (fills, approaches)
        self.vel = None         # a fixed velocity (ghosts, slap)
        self.fixed = False      # pitch fixed by a move / fill

    def __repr__(self):
        return f"_Ev({self.t:g}, {self.d:g}, {self.tok!r}, {self.p}, {self.kind})"


def arrange(prog, *, bpm, key=None, style: str = 'rock', part: str | None = None, energy: float | None = None,
            density: float = 0.5, seed=0, kick=None, lock: float | None = None, interlock: bool | None = None,
            strings: int = 4, low='E1', high=None,
            technique: str | None = None, cells: dict | None = None, approach: float | None = None,
            fills: dict | None = None, flash: dict | None = None, fill_every: float | None = None,
            flash_every: float | None = None, section_end: bool = True, into=None, pedal=None,
            ending: str | None = None, late_ms: float | None = None, timing_ms: float | None = None,
            timing: bool = True, swing: float | None = None, memory: Memory | None = None, at=None,
            length=None) -> BassLine:
    """A bassist's line over a progression -> BassLine (.clip, .place(track, at), .moves, .budget, .summary()).

    Bar by bar the bassist plays a groove CELL of the style (STYLES; one main cell per clip, a variation at the end
    of 4-bar phrases; energy picks the cells: sparse and short in a verse, driving and sustained in a chorus), strikes
    the new root on every chord change (the slash bass), locks with the kick (kick= a drum Clip - its kick notes 35 /
    36 - or a 16th pattern 'x.....x.x.......': notes near a kick snap onto it, missing kick hits are doubled, and at
    low energy the 'kick' cell doubles the kick's rhythm; lock= 0..1; interlock=True - funk's default - plays the one
    with the kick and answers in its gaps instead), approaches chord changes (chromatic,
    diatonic or the dominant; approach= the chance), adds pickups and passing tones, leaves space at low density, and
    decorates - BUDGETED: fills (FILL_KINDS) at the section end (section_end=True, into= the next section's first
    chord; default the progression's first) and at 4 / 8-bar phrase ends at most one per fill_every bars; FLASH moves
    (slides into a section / a change, slide-outs before a rest, hammer-ons, pull-offs, octave pops, rakes,
    walk-ups) at most one per flash_every bars, the same kind 2 x flash_every apart; memory= a Memory to count
    song-wide (at= this clip's beat in the song). pedal='E1' or [(start, end, 'E1')]: a pedal point (the line keeps
    its rhythm on the pedal note). ending='ring' (the last bar: the root on the one, held) or 'slide' (held, then
    a slide out).

    part= a PARTS name (verse, chorus, ...) sets the energy (or energy= 0..1): the level (velocity range), the cells,
    the note lengths (a rock verse staccato, the chorus sustained). density 0..1 scales approaches, fills, flashy
    moves and dead notes (and space when low). Touch: touch() (the one and the changes strong, off-beats lighter,
    dead notes 20-40, phrase arcs); technique='slap' (with sampled/slap_bass) plays thumb roots at 104-115 and popped
    octaves at 116-127. Timing baked in: the style's lay-back (late_ms: reggae +14, ballad +8, motown +4, funk -2,
    walking on top) + seeded jitter (timing_ms), note ends kept (articulation.humanize_starts); timing=False leaves
    the grid. Feel: swing= the line's 16th swing (a humanize.swing amount, 0.5 straight .. 0.8, or 50..80 %); by
    default the bassist follows the kick: a swung (or humanized) drum clip given as kick= is read on its 16th grid
    and its swing is played (.swing: what was played, None = straight). Range: strings=4 E1-G3 (5: B0-G3), roots
    from `low`; check() runs on the result (.problems). Tempo limits (FAST) and re-fingering at fast tempos; one
    gesture at a time (no flashy move in a fill's bar). Deterministic by seed."""
    if style not in STYLES:
        raise ComposeError(f"bassist style must be one of {', '.join(STYLES)}, got {style!r}")
    S = STYLES[style]
    b = _bpm(bpm)
    if part is not None and part not in PARTS:
        raise ComposeError(f"bassist part must be one of {', '.join(PARTS)}, got {part!r}")
    e = _num(energy, 'bassist energy', 0, 1) if energy is not None else (PARTS[part] if part else 0.6)
    dens = _num(density, 'bassist density', 0, 1)
    rng = random.Random(seed_int(seed))
    p = _as_prog(prog, key, 4.0 if length is None else length)
    L = float(p.length if length is None else _num(length, 'length (beats)', 0.25))
    bpb = p.beats_per_bar
    k = _key(key) if key is not None else p.key
    rlo, rhi = _range(strings)
    lo = note(low)
    hi = note(high) if high is not None else rhi
    if not rlo <= lo < hi <= rhi or hi - lo < 12:
        raise ComposeError(f"bassist range {lo}..{hi} must lie in {rlo}..{rhi} and span an octave")
    tech = technique or S['technique']
    if tech not in ('pick', 'finger', 'slap', 'upright', 'synth'):
        raise ComposeError(f"bassist technique must be pick, finger, slap, upright or synth, got {tech!r}")
    if ending not in (None, 'ring', 'slide'):
        raise ComposeError(f"bassist ending must be None, 'ring' or 'slide', got {ending!r}")
    lk = _num(lock if lock is not None else S['lock'], 'bassist lock', 0, 1)
    il = bool(S.get('interlock', False) if interlock is None else interlock)
    p_app = min(1.0, _num(approach if approach is not None else S['approach'], 'bassist approach', 0, 1)
                * (0.5 + dens))
    fill_w = dict(fills if fills is not None else S['fills'])
    flash_w = dict(flash if flash is not None else S['flash'])
    for name in fill_w:
        if name not in FILL_KINDS:
            raise ComposeError(f"unknown fill {name!r}; use {', '.join(FILL_KINDS)}")
    for name in flash_w:
        if name not in FLASH:
            raise ComposeError(f"unknown flashy move {name!r}; use {', '.join(FLASH)}")
    fe = _num(fill_every if fill_every is not None else S['fill_every'], 'bassist fill_every (bars)', 0)
    fle = _num(flash_every if flash_every is not None else S['flash_every'], 'bassist flash_every (bars)', 0)
    if memory is not None and not isinstance(memory, Memory):
        raise ComposeError(f"bassist memory must be a bassist.Memory(), got {memory!r}")
    base = _pos(at) if at is not None else (memory.clock if memory is not None else 0.0)
    cell_w = dict(cells) if cells is not None else None
    into_ch = _chord(into) if into is not None else next((c for _, _, c in p if c is not None), None)

    def chord_at(t):
        return p.at(min(max(t, 0.0), L - 1e-6)) if t < L - 1e-6 else into_ch

    changes = [st for st, _, c in p if c is not None and st < L - _EPS]
    # chords that repeat (the same symbol) are not changes for the line
    real_changes = []
    prev_sym = None
    for st, _, c in p:
        if c is None or st >= L - _EPS:
            continue
        if c.symbol != prev_sym:
            real_changes.append(st)
        prev_sym = c.symbol
    if L > p.length + _EPS:            # a progression shorter than the clip loops
        t = p.length
        while t < L - _EPS:
            for st, _, c in p:
                if c is not None and t + st < L - _EPS:
                    changes.append(t + st)
                    real_changes.append(t + st)
            t += p.length
    changes = sorted(set(round(x, 6) for x in changes))
    real_changes = sorted(set(round(x, 6) for x in real_changes))
    kicks, kick_swing = _kick_onsets(kick, L, bpb)
    moves: list = []
    n_bars = max(1, int(math.ceil(L / bpb - _EPS)))

    # ------------------------------------------------------------------ 1. the groove: cells -> events
    if style == 'walking':
        feel = 'four' if e >= 0.45 else 'two'
        wc = walk(p, b, key=k, feel=feel, low=lo, high=hi, vel=100, seed=rng.randrange(1 << 30),
                  skip=0.08 + 0.1 * dens, pedal=pedal, length=L)
        evs = []
        for n in wc:
            ev = _Ev(n.start, n.dur, 'W', 'note')
            ev.p = n.pitch
            if _art.articulation_of(n) == 'mute':
                ev.kind, ev.art = 'ghost', 'mute'
            evs.append(ev)
        for bi in range(n_bars):
            moves.append((bi * bpb, min(L, (bi + 1) * bpb), 'groove', f'walk_{feel}'))
    else:
        # tempo limits of the plucking hand: no 16th runs it can't play cleanly at this tempo (synths excepted)
        fast_ok = {nm: tech == 'synth' or _fast_ok(c_[0], b) for nm, c_ in S['cells'].items()}
        pool = cell_w if cell_w is not None else {nm: w for nm, (_, e0, e1, w) in S['cells'].items()
                                                  if e0 <= e <= e1 and fast_ok[nm]}
        if cell_w is not None:
            for nm in cell_w:
                if nm not in S['cells'] and nm != 'kick':
                    raise ComposeError(f"unknown {style} cell {nm!r}; use {', '.join(S['cells'])} or 'kick'")
        if not pool:
            ok = [nm for nm in S['cells'] if fast_ok[nm]] or list(S['cells'])
            pool = {min(ok, key=lambda nm: min(abs(e - S['cells'][nm][1]), abs(e - S['cells'][nm][2]))): 1.0}
        if kicks and S['kick'] > 0 and cell_w is None and e <= 0.6:
            pool['kick'] = S['kick']
        if 'kick' in pool and not kicks:
            pool.pop('kick')
            if not pool:
                raise ComposeError("bassist cell 'kick' needs kick= (a drum clip or a 16th pattern)")
        main = _pick(rng, pool)
        alt_pool = {nm: w for nm, w in pool.items() if nm != main}
        alt = _pick(rng, alt_pool) if alt_pool else main
        chars: list[str] = []
        bar_cell: list[str] = []
        for bi in range(n_bars):
            use = main
            if bi % 4 == 3 and bi != n_bars - 1 and rng.random() < 0.35 + 0.4 * dens:
                use = alt
            elif bi == n_bars - 1 and n_bars > 1 and rng.random() < 0.5:
                use = alt
            bar_cell.append(use)
            nslots = int(round(bpb / _GRID))
            if use == 'kick':
                row = ['.'] * nslots
                bar_k = [x - bi * bpb for x in kicks if bi * bpb - _EPS <= x < (bi + 1) * bpb - _EPS]
                for x in bar_k:
                    j = int(round(x / _GRID))
                    if 0 <= j < nslots:
                        row[j] = 'R'
                for j in range(nslots):
                    if row[j] == '.' and j > 0 and row[j - 1] in 'R-':
                        row[j] = '-'
                if row[0] == '.':
                    row[0] = 'R'
                chars += row
            else:
                pat = S['cells'][use][0]
                if len(pat) > nslots and len(pat) % nslots == 0:
                    pat = pat[(bi % (len(pat) // nslots)) * nslots:][:nslots]
                chars += list(_bar_pattern(pat, bpb))
            moves.append((bi * bpb, min(L, (bi + 1) * bpb), 'groove', use))
        evs = []
        cur = None
        for j, ch in enumerate(chars):
            t = j * _GRID
            if t >= L - _EPS:
                break
            if ch == '-':
                if cur is not None:
                    cur.d += _GRID
                elif j == 0:
                    cur = _Ev(0.0, _GRID, 'R')
                    evs.append(cur)
                continue
            if ch == '.':
                cur = None
                continue
            cur = _Ev(t, _GRID, ch, 'ghost' if ch == 'x' else 'note')
            evs.append(cur)
        for ev in evs:
            ev.d = min(ev.d, L - ev.t)

    # ------------------------------------------------------------------ 2. lock to the kick
    locked = None
    if kicks and style != 'walking' and lk > 0:
        for x in kicks:
            near = [ev for ev in evs if abs(ev.t - x) < 0.26 and ev.kind != 'ghost']
            if any(abs(ev.t - x) < 0.02 for ev in near):
                continue
            dead = [ev for ev in evs if abs(ev.t - x) < 0.02 and ev.kind == 'ghost']
            if dead:                       # a dead note on the kick: play it for real, with the kick
                if rng.random() < lk:
                    dead[0].kind, dead[0].tok = 'note', 'S'
                continue
            mov = [ev for ev in near if abs(ev.t % 1.0) > 0.02 and abs(ev.t - x) <= 0.25 + _EPS]
            if mov and rng.random() < lk:
                ev = min(mov, key=lambda ev: abs(ev.t - x))
                end = ev.t + ev.d
                ev.t = x
                ev.d = max(_GRID, end - x)
                continue
            if rng.random() < lk ** (2.0 - e):          # lock=1: every kick is doubled
                sounding = [ev for ev in evs if ev.t < x - _EPS and ev.t + ev.d > x + _EPS]
                nxt = min((ev.t for ev in evs if ev.t > x + _EPS), default=L)
                if sounding:
                    s0 = sounding[0]
                    dur = s0.t + s0.d - x
                    s0.d = x - s0.t
                    new = _Ev(x, dur, 'S')
                else:
                    new = _Ev(x, min(nxt - x, 1.0), 'S')
                evs.append(new)
        evs.sort(key=lambda ev: ev.t)
        ons = [ev.t for ev in evs if ev.kind != 'ghost']
        locked = sum(1 for x in kicks if any(abs(o - x) < 0.02 for o in ons)) / len(kicks)
    # interlock (funk): the one together with the kick, then the bass answers in its gaps - a note on a later kick
    # moves a 16th off it (after it, else before it), so bass and kick alternate instead of masking each other;
    # where both neighbours are taken it stays with the kick; dead notes leave the later kicks too (a 16th later,
    # else they go)
    if kicks and il and style != 'walking':
        def free(t_, me):
            if not 0.0 <= t_ < L - _EPS or any(abs(t_ - k_) < 0.02 for k_ in kicks):
                return False
            return not any(x is not me and x.t - 0.02 < t_ < x.t + max(x.d, 0.02) - 0.02 for x in evs)
        drop_ids = set()
        for ev in sorted(evs, key=lambda x: x.t):
            if not any(abs(ev.t - x) < 0.02 for x in kicks):
                continue
            if ev.kind == 'ghost':
                # a dead note is a thud in the low end too: off the later kicks (the one keeps its partner)
                if ev.t % bpb >= 0.02:
                    if free(ev.t + _GRID, ev):
                        ev.t += _GRID
                    else:
                        drop_ids.add(id(ev))
                continue
            if ev.t % bpb < 0.02 or any(abs(ev.t - c_) < 0.02 for c_ in changes) or rng.random() >= 0.85:
                continue
            nxt = min((x.t for x in evs if x.t > ev.t + 0.02), default=L)
            if free(ev.t + _GRID, ev) and ev.t + _GRID < nxt - 0.02:
                ev.t, ev.d = ev.t + _GRID, max(_GRID, min(ev.d - _GRID, nxt - ev.t - _GRID))
            elif free(ev.t - _GRID, ev) and (ev.t - _GRID) // bpb == ev.t // bpb:
                ev.t, ev.d = ev.t - _GRID, min(ev.d + _GRID, nxt - ev.t + _GRID)
        evs = sorted((ev for ev in evs if id(ev) not in drop_ids), key=lambda ev: ev.t)

    # ------------------------------------------------------------------ 3. pitches
    prev_root = None
    prev_p = None
    ped = _pedal_spans(pedal, L) if style != 'walking' else []

    def root_at(ch, ref):
        pc_ = ch.bass_pc
        cands = [q for q in range(lo, min(hi, lo + 16) + 1) if q % 12 == pc_]
        if ref is None:
            return cands[0]
        return min(cands, key=lambda q: (abs(q - ref) + 0.6 * max(0, q - (lo + 11)), q))

    def resolve(ev):
        nonlocal prev_root, prev_p
        ch = chord_at(ev.t)
        if ch is None:
            return False
        if ev.tok == 'W':
            prev_p = ev.p
            return True
        r = root_at(ch, prev_root)
        if ev.tok == 'N':
            nxt_bar = (math.floor(ev.t / bpb + _EPS) + 1) * bpb
            nc = chord_at(nxt_bar) or ch
            q = root_at(nc, prev_root)
            prev_root = q
        elif ev.tok in ('R', 'S', 'x'):
            q = r if ev.tok == 'R' or prev_p is None else prev_p
            if ev.tok == 'x':
                q = prev_p if prev_p is not None else r
            if ev.tok == 'R':
                prev_root = r
            if ev.tok == 'S' and any(abs(ev.t - c_) < 0.02 for c_ in changes):
                q = r
                prev_root = r
        elif ev.tok in ('a', 'p'):
            ev.p = None
            return True
        else:
            q = r + _deg(ch, ev.tok, S['blue'])
            if q > hi:
                q -= 12
            if q < lo:
                q += 12
        for a0, a1, pp in ped:
            if a0 - _EPS <= ev.t < a1 - _EPS:
                q = pp + (12 if ev.tok == 'O' and pp + 12 <= hi else 0)
        ev.p = _fold(q, lo, hi)
        prev_p = ev.p
        return True

    evs = [ev for ev in evs if resolve(ev)]
    if ped:
        moves += [(a0, a1, 'pedal', 'pedal') for a0, a1, _ in ped]

    # chord changes: strike the new root where the line holds through (or rests, in a striking style)
    if style != 'walking':
        for tc in changes:
            if tc < _EPS and any(ev.t < 0.02 for ev in evs):
                continue
            if any(abs(ev.t - tc) < 0.02 for ev in evs):
                continue
            ch = chord_at(tc)
            if ch is None:
                continue
            sounding = [ev for ev in evs if ev.t < tc - _EPS and ev.t + ev.d > tc + _EPS]
            if sounding:
                s0 = sounding[0]
                if s0.p is not None and s0.p % 12 == ch.bass_pc:
                    continue
                dur = s0.t + s0.d - tc
                s0.d = tc - s0.t
            elif S['change'] == 'keep':
                continue
            else:
                nxt = min((ev.t for ev in evs if ev.t > tc + _EPS), default=L)
                dur = min(nxt - tc, 1.0)
            new = _Ev(tc, dur, 'R')
            ref = max((ev for ev in evs if ev.t < tc and ev.p is not None), key=lambda ev: ev.t, default=None)
            prev_root = ref.p if ref is not None else None
            new.p = root_at(ch, prev_root)
            if ped:
                for a0, a1, pp in ped:
                    if a0 - _EPS <= tc < a1 - _EPS:
                        new.p = pp
            evs.append(new)
        evs.sort(key=lambda ev: ev.t)

    # ------------------------------------------------------------------ 4. approaches into the changes
    appr_kinds = S['kinds']
    if style != 'walking' and p_app > 0:
        for tc in real_changes + ([L] if section_end and into_ch is not None and ending is None else []):
            if tc < _EPS or any(a0 - _EPS <= tc < a1 + _EPS for a0, a1, _ in ped):
                continue
            if ending is not None and tc > (n_bars - 1) * bpb + _EPS:
                continue
            if rng.random() >= p_app:
                continue
            before = [ev for ev in evs if tc - 1.0 - _EPS <= ev.t < tc - _EPS and ev.kind == 'note']
            last = max(before, key=lambda ev: ev.t, default=None)
            if last is not None and last.t >= tc - 0.5 - _EPS and last.t > _EPS and \
                    not any(abs(last.t - c_) < 0.02 for c_ in changes) and last.t % bpb > 0.02:
                # the pitch is re-chosen below (relative to the note it leads into)
                last.tok, last.kind, last.p = 'a', 'approach', None
                moves.append((last.t, last.t + last.d, 'approach', _pick(rng, appr_kinds)))
                last.w = moves[-1][3]
                continue
            if rng.random() < S['insert'] * (0.5 + dens):
                sounding = [ev for ev in evs if ev.t < tc - 0.5 - _EPS and ev.t + ev.d > tc - 0.5 + _EPS
                            and ev.kind == 'note']
                g = 1.0 if style in ('ballad', 'country') and b < 110 else 0.5
                if sounding and sounding[0].t <= tc - g - 0.25 - _EPS:
                    s0 = sounding[0]
                    s0.d = tc - g - s0.t
                    new = _Ev(tc - g, g, 'a', 'approach')
                    kind_ = _pick(rng, appr_kinds)
                    new.w = kind_
                    evs.append(new)
                    moves.append((new.t, tc, 'approach', kind_))
        evs.sort(key=lambda ev: ev.t)

    # relative tokens (approach / passing), right to left: the next note is known
    for i in range(len(evs) - 1, -1, -1):
        ev = evs[i]
        if ev.p is not None:
            continue
        nxt = next((x for x in evs[i + 1:] if x.kind != 'ghost' and x.p is not None), None)
        tgt_t = nxt.t if nxt is not None else L
        tch = chord_at(tgt_t) or chord_at(ev.t)
        tgt = nxt.p if nxt is not None else root_at(tch, prev_root)
        prv = next((x.p for x in reversed(evs[:i]) if x.p is not None and x.kind != 'ghost'), None)
        if ev.tok == 'p' and prv is not None and abs(tgt - prv) >= 2:
            pcs = _scale_pcs(chord_at(ev.t), k)
            d = 1 if tgt > prv else -1
            mid = _step(prv, pcs, d)
            if (tgt - mid) * d <= 0:
                mid = prv + d
            ev.p = _fold(mid, lo, hi)
            ev.kind = 'approach'
            continue
        kind_ = ev.w if isinstance(ev.w, str) else _pick(rng, appr_kinds)
        above = prv is not None and prv > tgt
        pcs = _scale_pcs(tch, k)
        if kind_ == 'chromatic':
            q = tgt + (1 if above else -1)
        elif kind_ == 'diatonic':
            q = _step(tgt, pcs, 1 if above else -1)
        else:                          # the dominant: a 5th above or a 4th below, whichever the neck has
            opts = [tgt + 7, tgt - 5] if above else [tgt - 5, tgt + 7]
            q = next((x for x in opts if lo <= x <= hi), opts[0])
        if not lo <= q <= hi:
            q = tgt + (1 if q < lo else -1)
        ev.p = q
        ev.w = None
        ev.kind = 'approach'

    # ------------------------------------------------------------------ 5. space (sparse parts leave notes out)
    if S['space'] > 0 and style != 'walking':
        p_sp = S['space'] * (1.0 - dens) * (1.2 - e)
        kept = []
        for ev in evs:
            weak = ev.t % bpb > 0.02 and not any(abs(ev.t - x) < 0.02 for x in kicks + changes) and \
                ev.kind == 'note' and abs(ev.t % 1.0) > 0.02
            if weak and rng.random() < p_sp:
                prev = kept[-1] if kept else None
                if prev is not None and abs(prev.t + prev.d - ev.t) < _EPS and prev.p == ev.p:
                    prev.d += ev.d
                moves.append((ev.t, ev.t + ev.d, 'space', 'rest'))
                continue
            kept.append(ev)
        evs = kept

    # ------------------------------------------------------------------ 6. budgets: memory
    booked_fill = list(memory.fills) if memory is not None else []
    booked_flash = list(memory.flash) if memory is not None else []
    dropped: list = []

    # ------------------------------------------------------------------ 7. fills into the next downbeat
    fwin: list = []                  # (start, end) of the fills played
    # the 16th-note funk figure and the rake are 3+ runs of 16th attacks: not above the plucking hand's limit
    fill_w_ok = {kk: w for kk, w in fill_w.items()
                 if kk not in ('sixteenths', 'rake') or tech == 'synth' or b <= FAST[3]}
    if fill_w:
        cands = []
        for bi in range(n_bars):
            bar_end = min(L, (bi + 1) * bpb)
            if bar_end - bi * bpb < bpb - _EPS:
                continue
            last = bi == n_bars - 1
            if last and (not section_end or ending is not None):     # an ending replaces the last bar
                continue
            score = 3.0 if last else 2.0 if (bi + 1) % 8 == 0 else 1.0 if (bi + 1) % 4 == 0 else 0.0
            if score <= 0:
                continue
            if not last and rng.random() >= 0.35 * (0.4 + dens) * (0.6 + e):
                continue
            if last and rng.random() >= 0.55 + 0.4 * dens:
                continue
            fl = _pick(rng, S['fill_len'])
            if style == 'funk' and b > 120:
                fl = 1.0
            cands.append((score, bi, bar_end, fl))
        for score, bi, bar_end, fl in sorted(cands, key=lambda c_: (-c_[0], -c_[1])):
            land = bar_end - S.get('land', 0.0)     # tumbao: the fill lands on the anticipated 4, not the one
            w0 = land - fl
            if any(a0 - _EPS <= w0 < a1 for a0, a1, _ in ped):
                continue
            t_abs = base + w0
            if fe > 0 and any(abs(t_abs - x) < fe * bpb - _EPS for x, _ in booked_fill):
                dropped.append((round(w0, 4), 'fill'))
                continue
            kind_ = _pick(rng, fill_w_ok)
            if kind_ is None:
                continue
            tgt_ch = chord_at(bar_end) or chord_at(w0)
            prev_ev = max((ev for ev in evs if ev.t < w0 - _EPS and ev.p is not None), key=lambda ev: ev.t,
                          default=None)
            tgt = root_at(tgt_ch, prev_ev.p if prev_ev else None)
            at_land = [ev for ev in evs if abs(ev.t - land) < 0.02 and ev.p is not None and ev.kind != 'ghost']
            if land < bar_end - _EPS and at_land:
                tgt = at_land[0].p                 # into the anticipation as it is played
            grid = None
            if kind_ in ('run_up', 'run_down', 'chromatic', 'pentatonic') and e >= 0.7 and b <= 105:
                grid = 0.25
            fc = fill(kind_, tgt, fl, b, chord=chord_at(w0), key=k, grid=grid, low=lo, high=hi,
                      vel=(80, 100), seed=rng.randrange(1 << 30), at=w0)
            if not len(fc):
                continue
            fs = sorted(fc, key=lambda n: n.start)
            if kind_ in ('run_up', 'walk_up') and fs[0].pitch > fs[-1].pitch:
                kind_ = 'run_down'                 # no room below the target: the run came down into it
            elif kind_ == 'run_down' and fs[0].pitch < fs[-1].pitch:
                kind_ = 'run_up'
            keep = []                      # cut what the fill replaces
            for ev in evs:
                if w0 - _EPS <= ev.t < land - _EPS:
                    continue
                if ev.t < w0 and ev.t + ev.d > w0:
                    ev.d = max(0.1, w0 - ev.t)
                    ev.tie = False
                keep.append(ev)
            evs = keep
            # the log keeps only what is still played: approaches / rests the fill replaced go
            moves = [m for m in moves if not (m[2] in ('approach', 'space') and w0 - _EPS <= m[0] < land - _EPS)]
            nfill = len(fc)
            for i, n in enumerate(fc):
                ev = _Ev(n.start, n.dur, 'F', 'fill')
                ev.p = n.pitch
                ev.art = _art.articulation_of(n)
                ev.glide = _art.glide_of(n)
                ev.fixed = True
                ev.w = 0.62 + 0.33 * i / max(1, nfill - 1)
                if ev.art == 'mute':
                    ev.kind = 'ghost'
                evs.append(ev)
            # an approach note that led into the (now replaced) change leads into the fill's first note instead
            f0 = min(fc, key=lambda n: n.start)
            ap = [ev for ev in evs if ev.kind == 'approach' and w0 - 1.0 - _EPS <= ev.t < w0 - _EPS]
            if ap and _art.articulation_of(f0) != 'mute':
                a_ev = max(ap, key=lambda ev: ev.t)
                if abs(a_ev.p - f0.pitch) > 2 or a_ev.p == f0.pitch:
                    q = f0.pitch + (1 if a_ev.p > f0.pitch else -1)
                    a_ev.p = q if lo <= q <= hi else f0.pitch - (1 if a_ev.p > f0.pitch else -1)
                    moves = [(m[0], m[1], m[2], 'chromatic') if m[2] == 'approach' and abs(m[0] - a_ev.t) < _EPS
                             else m for m in moves]
            moves.append((w0, land, 'fill', kind_))
            booked_fill.append((t_abs, kind_))
            fwin.append((w0, land))
        evs.sort(key=lambda ev: ev.t)

    # ------------------------------------------------------------------ 8. flashy moves (budgeted)
    inside_fill = lambda t: any(a0 - _EPS <= t < a1 + _EPS for a0, a1 in fwin)  # noqa: E731
    flash_c: list = []
    p_flash = min(0.95, 0.4 * (0.4 + dens))
    end_bar = (n_bars - 1) * bpb if ending is not None else None
    slow3 = tech == 'synth' or b <= FAST[3]           # 16th runs (a rake) still clean at this tempo
    slow2 = tech == 'synth' or b <= FAST[2]           # 16th pairs (a popped octave a 16th after the root)

    def near_fill(t_abs):
        """A flashy move never shares a bar with a fill (the bar before it, the fill, the bar it lands in): one
        gesture at a time."""
        return any(-bpb + _EPS < t_abs - x < bpb + 2.0 - _EPS for x, _ in booked_fill)

    for i, ev in enumerate(evs):
        if ev.kind != 'note' or ev.p is None or inside_fill(ev.t) or ev.glide:
            continue
        if end_bar is not None and ev.t >= end_bar - _EPS:
            continue
        if near_fill(base + ev.t):
            continue
        on_change = any(abs(ev.t - x) < 0.02 for x in real_changes)
        nxt = evs[i + 1] if i + 1 < len(evs) else None
        gap_after = (nxt.t if nxt is not None else L) - (ev.t + ev.d)
        room = (nxt.t if nxt is not None else L) - ev.t
        prv = evs[i - 1] if i else None
        after_approach = prv is not None and prv.kind == 'approach' and ev.t - prv.t <= 1.0 + _EPS
        for kind_, w in flash_w.items():
            score = 0.0
            if kind_ == 'slide' and (on_change or ev.t < _EPS) and room >= 0.5 and ev.p - 2 >= lo and \
                    not after_approach and (prv is None or prv.t + prv.d <= ev.t - 0.05 or prv.p != ev.p):
                score = 2.0 if ev.t < _EPS else 1.0 + (0.5 if ev.t % (4 * bpb) < 0.02 else 0.0)
            elif kind_ == 'slide_out' and ev.d >= 0.75 and (gap_after >= 0.5 or nxt is None):
                score = 2.0 if nxt is None or ev.t + ev.d >= L - 1.0 else 1.0
            elif kind_ in ('hammer_on', 'pull_off') and room >= 0.5 and ev.d >= 0.4 and ev.t % bpb > 0.02 and \
                    not on_change and not any(abs(ev.t - x) < 0.02 for x in changes):
                score = 0.8
            elif kind_ == 'octave_pop' and room >= (0.5 if slow2 else 1.0) and ev.tok in ('R', 'S') and \
                    ev.p + 12 <= hi and ev.t % 1.0 < 0.02:
                score = 0.9
            elif kind_ == 'rake' and on_change and slow3 and prv is not None and \
                    ev.t - (prv.t + prv.d) >= 0.5 - _EPS:
                score = 1.2
            elif kind_ == 'walk_up' and on_change and ev.t >= 3.0 - _EPS and ev.t % bpb < 0.02 and \
                    not near_fill(base + ev.t - 3.0):
                score = 1.3
            if score > 0 and rng.random() < p_flash * w / max(flash_w.values()):
                flash_c.append((score + rng.random() * 0.2, ev, kind_))
    kept_flash: list = []
    for score, ev, kind_ in sorted(flash_c, key=lambda x: (-x[0], x[1].t)):
        t_abs = base + ev.t
        allb = booked_flash + [(base + x.t, kk) for x, kk in kept_flash]
        if fle > 0 and any(abs(t_abs - x) < fle * bpb - _EPS for x, _ in allb):
            dropped.append((round(ev.t, 4), kind_))
            continue
        if fle > 0 and any(kk == kind_ and abs(t_abs - x) < 2 * fle * bpb - _EPS for x, kk in allb):
            dropped.append((round(ev.t, 4), kind_))
            continue
        if any(x is ev for x, _ in kept_flash):
            continue
        kept_flash.append((ev, kind_))
    new_evs: list = []
    removed: set = set()
    for ev, kind_ in kept_flash:
        i = evs.index(ev)
        nxt = evs[i + 1] if i + 1 < len(evs) else None
        room = (nxt.t if nxt is not None else L) - ev.t
        if kind_ == 'slide':
            by = -2 if ev.p - 2 >= lo and rng.random() < 0.8 else (2 if ev.p + 2 <= hi else -1)
            c_ = slide(ev.p, max(0.25, ev.d), b, by=by, ms=rng.uniform(60, 110), at=ev.t)
            g0, t0 = c_[0], c_[1]
            ev.d = t0.start - ev.t + 0.03
            ev.p = g0.pitch
            ev.tie = True
            tgt = _Ev(t0.start, t0.dur, 'M', 'note')
            tgt.p, tgt.glide, tgt.fixed = t0.pitch, _art.glide_of(t0), True
            tgt.w = 'inherit'
            new_evs.append(tgt)
            moves.append((ev.t, ev.t + max(0.25, t0.start + t0.dur - ev.t), 'move', 'slide'))
        elif kind_ == 'slide_out':
            dr = _drop(ev.p, rlo, hi, rng)
            if dr == 0:
                continue
            c_ = slide_out(ev.p, ev.d, b, drop=dr, ms=rng.uniform(160, 260), at=ev.t)
            a0, t0 = c_[0], c_[1]
            ev.d = a0.dur
            ev.tie = True
            tail = _Ev(t0.start, t0.dur, 'M', 'note')
            tail.p, tail.glide, tail.fixed, tail.w = t0.pitch, _art.glide_of(t0), True, 0.35
            new_evs.append(tail)
            moves.append((ev.t, ev.t + ev.d + t0.dur, 'move', 'slide_out'))
        elif kind_ in ('hammer_on', 'pull_off'):
            ch = chord_at(ev.t)
            pcs = _scale_pcs(ch, k)
            if kind_ == 'hammer_on':
                other = _step(ev.p, pcs, -1)
                if ev.p - other > 4 or other < lo:
                    other = ev.p - 2 if ev.p - 2 >= lo else None
            else:
                other = _step(ev.p, pcs, 1)
                if other - ev.p > 4 or other > hi:
                    other = ev.p + 2 if ev.p + 2 <= hi else None
            if other is None:
                continue
            gd = 0.25 if room >= 0.5 else room / 2
            second = _Ev(ev.t + gd, max(0.1, ev.d - gd), 'M', 'note')
            second.p, second.fixed, second.w = ev.p, True, 'legato'
            ev.p, ev.d, ev.tie = other, gd + 0.03, True
            new_evs.append(second)
            moves.append((ev.t, second.t + second.d, 'move', kind_))
        elif kind_ == 'octave_pop':
            gd = 0.5 if not slow2 else 0.25 if room < 1.0 else 0.5 if rng.random() < 0.5 else 0.25
            pop = _Ev(ev.t + gd, min(0.25, room - gd) if room - gd > 0.1 else 0.1, 'O', 'note')
            pop.p, pop.fixed, pop.w, pop.art = ev.p + 12, True, 0.95, 'staccato'
            ev.d = min(ev.d, gd)
            new_evs.append(pop)
            moves.append((ev.t, pop.t + pop.d, 'move', 'octave_pop'))
        elif kind_ == 'rake':
            prv = evs[i - 1]
            n_r = 3 if ev.t - (prv.t + prv.d) >= 0.75 - _EPS else 2
            for j in range(n_r):
                g_ = _Ev(ev.t - (n_r - j) * 0.25, 0.12, 'x', 'ghost')
                g_.p, g_.art, g_.fixed = ev.p, 'mute', True
                g_.vel = 24 + 7 * j
                new_evs.append(g_)
            moves.append((ev.t - n_r * 0.25, ev.t, 'move', 'rake'))
        elif kind_ == 'walk_up':
            prv_ev = [x for x in evs if x.t < ev.t - _EPS]
            w0 = ev.t - 3.0
            c_ = walk_up(ev.p, b, steps=3, grid=1.0, chord=chord_at(ev.t), key=k, at=w0)
            if min(n.pitch for n in c_) < lo:
                continue
            for x in prv_ev:
                if x.t >= w0 - _EPS:
                    removed.add(id(x))
                elif x.t + x.d > w0:
                    x.d = w0 - x.t
            for n in c_:
                wv = _Ev(n.start, n.dur, 'M', 'approach')
                wv.p, wv.fixed, wv.w = n.pitch, True, 0.7
                new_evs.append(wv)
            moves = [m for m in moves if not (m[2] in ('approach', 'space') and w0 - _EPS <= m[0] < ev.t - _EPS)]
            moves.append((w0, ev.t, 'move', 'walk_up'))
        booked_flash.append((base + ev.t, kind_))
    evs = sorted([ev for ev in evs if id(ev) not in removed] + new_evs, key=lambda ev: (ev.t, ev.p or 0))

    # ------------------------------------------------------------------ 9. dead notes before the backbeats
    if S['ghost'] > 0 and style != 'walking':
        p_g = S['ghost'] * (0.4 + dens)
        ons = [ev.t for ev in evs]
        add = []
        for bi in range(n_bars):
            for bt in (1.0, 3.0) if bpb >= 4 else (1.0,):
                t = bi * bpb + bt - 0.25
                if t >= L - _EPS or inside_fill(t):
                    continue
                sounding = [ev for ev in evs if ev.t < t - _EPS and ev.t + ev.d > t - 0.05]
                if any(abs(o - t) < 0.12 for o in ons) or rng.random() >= p_g or \
                        (il and any(abs(t - k_) < 0.02 for k_ in kicks)):
                    continue
                if any(x.tie or x.glide or x.fixed or x.t > t - 0.25 for x in sounding):
                    continue
                ref = sounding[0].p if sounding else next((ev.p for ev in reversed(evs) if ev.t < t and ev.p), None)
                if ref is None:
                    continue
                for s0 in sounding:
                    s0.d = max(0.1, t - s0.t - 0.02)
                    s0.tie = False
                g_ = _Ev(t, 0.12, 'x', 'ghost')
                g_.p, g_.art = ref, 'mute'
                add.append(g_)
                moves.append((t, t + 0.12, 'ghost', 'dead_note'))
        evs = sorted(evs + add, key=lambda ev: (ev.t, ev.p or 0))

    # ------------------------------------------------------------------ 10. the ending
    if ending is not None:
        last_bar = (n_bars - 1) * bpb
        ch = chord_at(last_bar)
        if ch is not None:
            prev_ev = max((ev for ev in evs if ev.t < last_bar - _EPS), key=lambda ev: ev.t, default=None)
            evs = [ev for ev in evs if ev.t < last_bar - _EPS]
            moves = [m for m in moves if not (m[2] in ('approach', 'space', 'ghost') and m[0] >= last_bar - _EPS)]
            for ev in evs:
                if ev.t + ev.d > last_bar:
                    ev.d = last_bar - ev.t
            r = root_at(ch, prev_ev.p if prev_ev else None)
            d = L - last_bar - 0.1
            if ending == 'ring':
                end_ev = _Ev(last_bar, d, 'R', 'note')
                end_ev.p, end_ev.w, end_ev.fixed = r, 1.05, True
                evs.append(end_ev)
            else:
                c_ = slide_out(r, d, b, drop=_drop(r, rlo, hi, rng) or 5, ms=280, at=last_bar)
                a0, t0 = c_[0], c_[1]
                e1 = _Ev(a0.start, a0.dur, 'R', 'note')
                e1.p, e1.w, e1.fixed, e1.tie = a0.pitch, 1.05, True, True
                e2 = _Ev(t0.start, t0.dur, 'M', 'note')
                e2.p, e2.glide, e2.fixed, e2.w = t0.pitch, _art.glide_of(t0), True, 0.35
                evs += [e1, e2]
            moves.append((last_bar, L, 'ending', ending))
            evs.sort(key=lambda ev: (ev.t, ev.p or 0))

    # one note at a time: notes that ended up on the same onset keep the most important one (a move / fill note,
    # else a played note over a dead one)
    evs = [ev for ev in evs if ev.p is not None]
    evs.sort(key=lambda ev: (ev.t, 0 if ev.fixed else 1 if ev.kind != 'ghost' else 2))
    mono: list = []
    for ev in evs:
        if mono and ev.t - mono[-1].t < 0.02:
            continue
        mono.append(ev)
    if tech != 'synth':
        mono = _pluck_limit(mono, b, changes)
    evs = _reach(mono, b, strings, lo, hi, changes, bpb)
    # the log keeps only approach / dead notes that are still played
    ons_ = [ev.t for ev in evs]
    moves = [m for m in moves if m[2] not in ('approach', 'ghost') or any(abs(m[0] - o) < 1e-6 for o in ons_)]

    # ------------------------------------------------------------------ 11. lengths, articulations
    g_lo, g_hi = S['gate']
    gate = g_lo + (g_hi - g_lo) * e
    stac = e < S['stac']
    for i, ev in enumerate(evs):
        nxt_t = next((x.t for x in evs[i + 1:] if x.t > ev.t + _EPS), L)
        nxt_e = next((x for x in evs[i + 1:] if x.t > ev.t + _EPS), None)
        if nxt_e is not None and (nxt_e.glide or nxt_e.w == 'legato') and ev.kind != 'ghost':
            ev.d = max(ev.d, nxt_e.t - ev.t + 0.03)
            ev.tie = True
        slot = min(ev.d, nxt_t - ev.t)
        if ev.kind == 'ghost':
            ev.d = min(0.12, max(0.05, slot * 0.6))
            ev.art = 'mute'
            continue
        if ev.tie:
            ev.d = max(0.05, min(ev.d, nxt_t - ev.t + 0.03))
            continue
        if ev.glide or ev.w == 'legato':
            ev.d = max(0.05, min(ev.d, nxt_t - ev.t - 0.02))
            continue
        if ev.kind == 'fill':
            ev.d = max(0.05, min(ev.d, nxt_t - ev.t - 0.02))
            continue
        length_ = slot * gate if slot <= 2.0 else slot - (1.0 - gate) * 1.0
        ev.d = max(0.08, min(length_, nxt_t - ev.t - 0.02))
        if ev.art is None and stac and slot <= S.get('stac_slot', 0.5) + _EPS:
            ev.art = 'staccato'

    if kicks:
        ons = [ev.t for ev in evs if ev.kind != 'ghost' and ev.p is not None]
        locked = sum(1 for x in kicks if any(abs(o - x) < 0.02 for o in ons)) / len(kicks)

    # ------------------------------------------------------------------ 12. touch: velocities
    hi_v = S['vel'][0] + (S['vel'][1] - S['vel'][0]) * e
    lo_v = hi_v - {'ballad': 30, 'walking': 30}.get(style, 36)
    arc = {'walking': 0.2, 'ballad': 0.14, 'motown': 0.1, 'reggae': 0.1}.get(style, 0.06)
    tc_ = [x for x in real_changes]
    notes = []
    prev_v = hi_v
    for ev in evs:
        if ev.p is None:
            continue
        if ev.kind == 'ghost':
            v = ev.vel if ev.vel is not None else 22 + 16 * e + (rng.random() - 0.5) * 6
            if tech == 'slap':
                v = max(v, 30 + 12 * rng.random())
        else:
            if isinstance(ev.w, (int, float)):
                w = ev.w
            else:
                w = _metric(ev.t, bpb)
                if any(abs(ev.t - x) < 0.02 for x in tc_):
                    w += 0.08
                if any(abs(ev.t - x) < 0.02 for x in kicks):
                    w += 0.06
                if ev.kind == 'approach':
                    w *= 0.85
                if ev.tok == 'O' and style == 'funk':
                    w += 0.06                   # the popped octave speaks
                elif ev.tok == 'O':
                    w *= 0.92                   # a fingered octave sits under the root (disco, pop, synth)
                if ev.tok == 'N':               # the anticipated root (tumbao's 4) is pushed
                    w += 0.14
            if ev.w == 'inherit':
                v = prev_v
            elif ev.w == 'legato':
                v = prev_v * 0.78
            else:
                v = lo_v + (hi_v - lo_v) * min(1.05, w)
                ph = 4 * bpb
                x = (ev.t % ph) / ph
                v *= 1.0 + arc * (math.sin(math.pi * x) - 0.5)
                v += (rng.random() - 0.5) * 5.0
            if tech == 'slap' and ev.w not in ('inherit', 'legato'):
                if ev.tok == 'O' or (ev.fixed and ev.tok == 'O'):
                    v = 116 + 9 * rng.random()
                elif abs(ev.t % 1.0) < 0.02 and ev.kind == 'note':
                    v = 104 + 11 * min(1.0, w)
                else:
                    v = 62 + 34 * min(1.0, w)
        prev_v = v
        cap = 127.0 if tech == 'slap' else min(127.0, hi_v + 3.0)      # accents stop at the style's top layer
        notes.append((ev, min(cap, max(12.0, v))))
    if S['melodic']:
        bars_p: dict[int, list[int]] = {}
        for ev, _ in notes:
            if ev.kind != 'ghost':
                bars_p.setdefault(int(ev.t // bpb), []).append(ev.p)
        adj = []
        for ev, v in notes:
            if ev.kind != 'ghost' and ev.w not in ('inherit', 'legato'):
                ps = bars_p[int(ev.t // bpb)]
                v += max(-6.0, min(6.0, 0.5 * (ev.p - sum(ps) / len(ps))))
            adj.append((ev, min(127.0, hi_v + 6.0, max(12.0, v))))
        notes = adj
    out = [_n(ev.t, ev.d, ev.p, v, ev.art, ev.glide) for ev, v in notes if ev.t < L - _EPS]
    clip = Clip._raw(out, L)

    # ------------------------------------------------------------------ 13. feel and timing
    # the drummer's 16th swing (measured from a swung kick clip) or swing= (0.5 straight): the line is written on
    # the straight grid (locks / interlocks against the kick's grid) and played with the band's feel
    if swing is None:
        sw = kick_swing
    else:
        sw = _num(swing, 'bassist swing', 0.5, 80)
        sw = _num(sw / 100.0 if sw > 1.0 else sw, 'bassist swing', 0.5, 0.8)
    if sw is not None and sw > 0.5 + 1e-6:
        clip = _swing(clip, sw)
    if timing:
        lm = late_ms if late_ms is not None else (S['late_ms'] if S['late_ms'] is not None
                                                  else layback_ms('bass', b))
        jm = timing_ms if timing_ms is not None else S['jitter_ms']
        clip = _keep_pairs(_art.humanize_starts(clip, b, ms=_num(jm, 'timing_ms', 0, 30),
                                                late_ms=_num(lm, 'late_ms', -30, 40), seed=seed_int(seed) + 11), clip)

    # ------------------------------------------------------------------ 14. budget record, memory
    budget = {'fill_every': fe, 'flash_every': fle, 'at': base,
              'fills': [(round(t - base, 4), kk) for t, kk in sorted(booked_fill) if base - _EPS <= t < base + L],
              'flash': [(round(t - base, 4), kk) for t, kk in sorted(booked_flash) if base - _EPS <= t < base + L],
              'dropped': sorted(set(dropped))}
    if memory is not None:
        memory.fills, memory.flash = sorted(booked_fill), sorted(booked_flash)
        memory.clock = base + L
    probs = check(clip, b, strings=strings, low=rlo, high=max(hi, rhi))
    out = BassLine(clip, sorted(moves, key=lambda m: (m[0], m[2])), budget, b, locked, probs)
    out.swing = sw if sw is not None and sw > 0.5 + 1e-6 else None
    return out

