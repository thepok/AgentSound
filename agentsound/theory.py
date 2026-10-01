"""Music theory: note names, scales, keys, chord symbols, roman numerals, voicings, voice leading.

Conventions used everywhere in agentsound:
  * MIDI 60 = C4 ('C#4' = 61, 'A4' = 69 = 440 Hz).
  * Scale degrees are 1-based as in music theory (1 = tonic, 8 = tonic an octave up);
    negative degrees count down from the tonic (-1 = the scale note just below it).
  * Times are in beats (quarter notes). Progression chord lengths are the one exception: bars.
"""

from __future__ import annotations

import functools
import itertools
import math
import re
from dataclasses import dataclass, replace


class ComposeError(ValueError):
    """Anything wrong in a song definition. The message says what is wrong and how to fix it."""


# --------------------------------------------------------------------------------------- notes

_LETTER_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
_ACCIDENTAL = {'#': 1, '♯': 1, 'b': -1, '♭': -1}
_NOTE_RE = re.compile(r'^([A-Ga-g])([#b♯♭]{0,2})(-?\d+)$')
_PC_RE = re.compile(r'^([A-Ga-g])([#b♯♭]{0,2})$')
SHARPS = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
FLATS = ('C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B')


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def pc(name) -> int:
    """Pitch class 0..11 of a note letter ('C', 'F#', 'Bb'), a note name ('A4') or a MIDI number."""
    if _is_int(name):
        return name % 12
    if isinstance(name, str):
        s = name.strip()
        m = _PC_RE.match(s)
        if m:
            return (_LETTER_PC[m.group(1).upper()] + sum(_ACCIDENTAL[c] for c in m.group(2))) % 12
        if _NOTE_RE.match(s):
            return note(s) % 12
    raise ComposeError(f"not a pitch class: {name!r} (use a note letter like 'C', 'F#', 'Bb')")


def note(x) -> int:
    """MIDI number of a note name: note('C4') == 60, note('C#4') == 61, note('Bb2') == 46.
    Ints (MIDI numbers) pass through after a range check."""
    if _is_int(x) or (isinstance(x, float) and x.is_integer()):
        v = int(x)
    elif isinstance(x, str):
        m = _NOTE_RE.match(x.strip())
        if not m:
            raise ComposeError(f"not a note name: {x!r} (expected letter + optional #/b + octave, "
                               f"e.g. 'C4', 'F#3', 'Bb2'; C4 = 60)")
        v = ((int(m.group(3)) + 1) * 12 + _LETTER_PC[m.group(1).upper()]
             + sum(_ACCIDENTAL[c] for c in m.group(2)))
    else:
        raise ComposeError(f"not a note: {x!r} (use a MIDI number 0..127 or a name like 'A4')")
    if not 0 <= v <= 127:
        raise ComposeError(f"note {x!r} = MIDI {v} is outside 0..127")
    return v


def note_name(midi: int, flats: bool = False) -> str:
    """'C#4' for 61 (or 'Db4' with flats=True)."""
    m = int(midi)
    return (FLATS if flats else SHARPS)[m % 12] + str(m // 12 - 1)


def hz(midi: float) -> float:
    """Frequency of a (fractional) MIDI note, A4 = 440 Hz."""
    return 440.0 * 2.0 ** ((float(midi) - 69.0) / 12.0)


# -------------------------------------------------------------------------------------- scales

SCALES: dict[str, tuple[int, ...]] = {
    'major': (0, 2, 4, 5, 7, 9, 11),
    'minor': (0, 2, 3, 5, 7, 8, 10),
    'dorian': (0, 2, 3, 5, 7, 9, 10),
    'phrygian': (0, 1, 3, 5, 7, 8, 10),
    'lydian': (0, 2, 4, 6, 7, 9, 11),
    'mixolydian': (0, 2, 4, 5, 7, 9, 10),
    'locrian': (0, 1, 3, 5, 6, 8, 10),
    'harmonic_minor': (0, 2, 3, 5, 7, 8, 11),
    'melodic_minor': (0, 2, 3, 5, 7, 9, 11),
    'phrygian_dominant': (0, 1, 4, 5, 7, 8, 10),
    'hungarian_minor': (0, 2, 3, 6, 7, 8, 11),
    'major_pentatonic': (0, 2, 4, 7, 9),
    'minor_pentatonic': (0, 3, 5, 7, 10),
    'blues': (0, 3, 5, 6, 7, 10),
    'major_blues': (0, 2, 3, 4, 7, 9),
    'whole_tone': (0, 2, 4, 6, 8, 10),
    'chromatic': tuple(range(12)),
}
_SCALE_ALIASES = {
    'ionian': 'major', 'maj': 'major', 'aeolian': 'minor', 'natural_minor': 'minor', 'min': 'minor',
    'm': 'minor', 'harmonic': 'harmonic_minor', 'melodic': 'melodic_minor', 'pentatonic': 'major_pentatonic',
    'minor_blues': 'blues', 'spanish': 'phrygian_dominant',
}
# Seven-note parent used for roman numerals / diatonic chords in non-heptatonic scales.
_PARENT = {'major_pentatonic': 'major', 'minor_pentatonic': 'minor', 'blues': 'minor',
           'major_blues': 'major', 'whole_tone': 'major', 'chromatic': 'major'}


def scale(name: str) -> tuple[int, ...]:
    """Semitone intervals of a scale/mode by name ('dorian', 'harmonic minor', 'minor_pentatonic')."""
    key = re.sub(r'[\s\-]+', '_', str(name).strip().lower())
    key = _SCALE_ALIASES.get(key, key)
    if key not in SCALES:
        raise ComposeError(f"unknown scale {name!r}; known: {', '.join(SCALES)}")
    return SCALES[key]


def _scale_name(name: str) -> str:
    key = re.sub(r'[\s\-]+', '_', str(name).strip().lower())
    key = _SCALE_ALIASES.get(key, key)
    scale(key)
    return key


# -------------------------------------------------------------------------------------- chords

_QUALITY_SPELL_FLAT = {1: 'Db', 3: 'Eb', 6: 'F#', 8: 'Ab', 10: 'Bb'}
_MINOR_SPELL = {1: 'C#', 3: 'Eb', 6: 'F#', 8: 'G#', 10: 'Bb'}


def _spell(p: int, minorish: bool = False) -> str:
    p %= 12
    if p in (0, 2, 4, 5, 7, 9, 11):
        return SHARPS[p]
    return (_MINOR_SPELL if minorish else _QUALITY_SPELL_FLAT)[p]


# Modifiers after the base quality, longest tokens first.
_MODIFIERS = [
    ('sus2', 'sus2'), ('sus4', 'sus4'), ('sus', 'sus4'),
    ('add13', 'add13'), ('add11', 'add11'), ('add9', 'add9'), ('add6', 'add6'), ('add4', 'add4'),
    ('add2', 'add2'), ('omit3', 'no3'), ('omit5', 'no5'), ('no3', 'no3'), ('no5', 'no5'),
    ('b13', 'b13'), ('-13', 'b13'), ('#11', '#11'), ('+11', '#11'),
    ('b9', 'b9'), ('-9', 'b9'), ('#9', '#9'), ('+9', '#9'),
    ('b5', 'b5'), ('-5', 'b5'), ('#5', '#5'), ('+5', '#5'),
    # bare tensions after the chord number, as in 'Cm7(11)', 'C7(13)', 'Cmaj7(9)' (checked after b13/#11/...)
    ('13', 'add13'), ('11', 'add11'), ('9', 'add9'),
]


def _apply_modifier(ivs: set[int], mod: str) -> None:
    def swap(remove, add):
        ivs.difference_update(remove)
        ivs.add(add)
    if mod == 'sus2':
        swap({3, 4}, 2)
    elif mod == 'sus4':
        swap({3, 4}, 5)
    elif mod.startswith('add'):
        ivs.add({'add2': 2, 'add4': 5, 'add6': 9, 'add9': 14, 'add11': 17, 'add13': 21}[mod])
    elif mod == 'no3':
        ivs.difference_update({3, 4})
    elif mod == 'no5':
        ivs.difference_update({6, 7, 8})
    elif mod == 'b5':
        swap({7}, 6)
    elif mod == '#5':
        swap({7}, 8)
    elif mod == 'b9':
        swap({14}, 13)
    elif mod == '#9':
        swap({14}, 15)
    elif mod == '#11':
        swap({17}, 18)
    elif mod == 'b13':
        swap({21}, 20)


def _normalize_quality(q: str) -> str:
    s = re.sub(r'[\s(),]', '', q)
    s = re.sub(r'^dom(?=\d|$)', '', s)            # 'Cdom7' = 'C7'
    s = re.sub(r'^2$', 'sus2', s)                  # chart shorthand 'C2' = Csus2
    s = re.sub(r'^7?alt$', '7b9#9b13no5', s)       # altered dominant: 1 3 b7 b9 #9 b13
    s = re.sub(r'ø(9|11)', r'm\1b5', s)             # half-diminished 9th / 11th: 'Cø9' = Cm9b5
    s = re.sub(r'ø7?', 'm7b5', s)
    s = re.sub(r'[Δ△](?=\d)', 'maj', s)
    s = re.sub(r'[Δ△]', 'maj7', s)
    s = s.replace('°', 'dim')
    s = re.sub(r'^o(?=\d|$)', 'dim', s)
    s = re.sub(r'^\+', 'aug', s)
    s = re.sub(r'^(mMaj|mM|m/maj|minmaj|-maj|-M)', 'mmaj', s)
    s = re.sub(r'^(Maj|MAJ|M(?=\d|$))', 'maj', s)
    s = re.sub(r'^(min|mi(?!n)|-)', 'm', s)
    s = re.sub(r'^ma(?=\d)', 'maj', s)
    s = s.replace('6/9', '69')
    return s


@functools.lru_cache(maxsize=4096)
def _parse_quality(quality: str) -> tuple[int, ...]:
    s = _normalize_quality(quality)
    ivs: set[int]
    third = 4
    if s.startswith('maj'):
        ivs = {0, 4, 7}
    elif s.startswith('m'):
        ivs, third, s = {0, 3, 7}, 3, s[1:]
    elif s.startswith('dim'):
        ivs, third, s = {0, 3, 6}, 3, s[3:]
    elif s.startswith('aug'):
        ivs, s = {0, 4, 8}, s[3:]
    elif s.startswith('5'):
        ivs, s = {0, 7}, s[1:]
        if s:
            raise ComposeError(f"power chord quality '5' takes no extensions, got {quality!r}")
        return (0, 7)
    else:
        ivs = {0, 4, 7}
    dim = ivs == {0, 3, 6}
    has_maj = s.startswith('maj')
    if has_maj:
        s = s[3:]
    m = re.match(r'^(69|13|11|9|7|6)', s)
    num = m.group(1) if m else ''
    s = s[len(num):]
    if has_maj and num in ('', '6', '69'):
        if num == '':
            has_maj = False  # plain 'maj' = major triad
    if num in ('7', '9', '11', '13'):
        ivs.add(11 if has_maj else (9 if dim else 10))
        if num in ('9', '11', '13'):
            ivs.add(14)
        if num == '11' or (num == '13' and third == 3):
            ivs.add(17)
        if num == '13':
            ivs.add(21)
    elif num == '6':
        ivs.add(9)
    elif num == '69':
        ivs.update({9, 14})
    while s:
        for token, mod in _MODIFIERS:
            if s.startswith(token):
                _apply_modifier(ivs, mod)
                s = s[len(token):]
                break
        else:
            raise ComposeError(
                f"can't parse chord quality {quality!r}: unexpected {s!r}. Supported: '', m, dim, aug, 5, 6, "
                f"m6, 69, 7, maj7, m7, mMaj7, m7b5, dim7, 9, maj9, m9, 11, m11, 13, sus2, sus4, 7sus4, 2, "
                f"add9, add11, 7alt, alterations b5 #5 b9 #9 #11 b13, no3/no5, slash bass /E")
    return tuple(sorted(ivs))


_CHORD_RE = re.compile(r'^([A-G])([#b♯♭]?)(.*)$')
_SLASH_RE = re.compile(r'^(.*)/([A-G][#b♯♭]?)$')


@dataclass(frozen=True)
class Chord:
    """A chord: root pitch class, intervals above the root, optional slash-bass pitch class.

    Chord.parse('Fmaj7/A'), chord('E7b9'), key.chord('iv7'). Immutable."""

    root: int
    intervals: tuple[int, ...]
    bass: int | None = None
    quality: str = ''
    root_name: str = ''
    bass_name: str | None = None

    @staticmethod
    def parse(symbol) -> 'Chord':
        """Parse a chord symbol ('Am9', 'Fmaj7/A', 'E7b9', 'Gsus4', 'C5', 'Bdim', 'Dm11', 'Cadd9')."""
        if isinstance(symbol, Chord):
            return symbol
        if not isinstance(symbol, str) or not symbol.strip():
            raise ComposeError(f"not a chord symbol: {symbol!r} (e.g. 'Am', 'Fmaj7/A', 'E7b9')")
        return _parse_chord(symbol.strip())

    # --- properties
    @property
    def symbol(self) -> str:
        return self.root_name + self.quality + (f'/{self.bass_name}' if self.bass_name else '')

    @property
    def pcs(self) -> frozenset[int]:
        """Pitch classes of the chord tones (without slash bass)."""
        return frozenset((self.root + i) % 12 for i in self.intervals)

    @property
    def bass_pc(self) -> int:
        """Pitch class the bass should play: the slash bass if any, else the root."""
        return self.root if self.bass is None else self.bass

    @property
    def is_minor(self) -> bool:
        return 3 in self.intervals and 4 not in self.intervals

    def __str__(self) -> str:
        return self.symbol

    def __repr__(self) -> str:
        return f"Chord({self.symbol!r})"

    # --- pitches
    def notes(self, octave: int = 4) -> list[int]:
        """Root-position pitches with the root in `octave` (Am, 4 -> [69, 72, 76]).
        A slash bass goes at least a fourth below the root: C/E, 4 -> [52, 60, 64, 67]."""
        r = (octave + 1) * 12 + self.root
        out = [r + i for i in self.intervals]
        if self.bass is not None:
            out.insert(0, _bass_below(self.bass, r))
        return out

    def bass_note(self, low='E1') -> int:
        """The bass pitch (slash bass or root) in the octave starting at `low`."""
        return _at_or_above(self.bass_pc, note(low))

    def priority(self) -> list[int]:
        """Intervals ordered by importance for voicing: root, 3rd/sus, 7th/6th, alterations,
        tensions, 5th last (a power chord keeps its 5th)."""
        if self.intervals == (0, 7):
            return [0, 7]

        def rank(i: int) -> int:
            if i == 0:
                return 0
            if i in (3, 4) or (i in (2, 5) and not ({3, 4} & set(self.intervals))):
                return 1
            if i in (9, 10, 11):
                return 2
            if i in (6, 8, 13, 15, 18, 20):
                return 3
            if i in (14, 17, 21, 2, 5):
                return 4
            return 5
        return sorted(self.intervals, key=lambda i: (rank(i), i))

    def transpose(self, semitones: int) -> 'Chord':
        r = (self.root + semitones) % 12
        b = None if self.bass is None else (self.bass + semitones) % 12
        return replace(self, root=r, bass=b, root_name=_spell(r, self.is_minor),
                       bass_name=None if b is None else _spell(b))

    def over(self, bass) -> 'Chord':
        """Same chord over another bass note: chord('C').over('E') == C/E."""
        b = pc(bass)
        return replace(self, bass=b, bass_name=_spell(b))

    def voice(self, style: str = 'close', octave: int = 4, **kw) -> list[int]:
        """See theory.voice()."""
        return voice(self, style, octave=octave, **kw)


@functools.lru_cache(maxsize=4096)
def _parse_chord(symbol: str) -> Chord:
    s = symbol
    bass = bass_name = None
    m = _SLASH_RE.match(s)
    if m:
        s, bass_name = m.group(1), m.group(2)
        bass = pc(bass_name)
    m = _CHORD_RE.match(s)
    if not m:
        raise ComposeError(f"can't parse chord {symbol!r}: must start with a root A-G (uppercase), "
                           f"e.g. 'Am7', 'Bb', 'F#m7b5', 'C/E'")
    root_name = m.group(1) + m.group(2)
    try:
        ivs = _parse_quality(m.group(3))
    except ComposeError as e:
        raise ComposeError(f"chord {symbol!r}: {e}") from None
    return Chord(pc(root_name), ivs, bass, m.group(3), root_name, bass_name)


def chord(symbol) -> Chord:
    """Parse a chord symbol: chord('Am9'), chord('Fmaj7/A'), chord('E7b9'), chord('C5')."""
    return Chord.parse(symbol)


def _below(p: int, ref: int) -> int:
    """Highest pitch with pitch class p strictly below ref."""
    x = ref - 1
    return x - ((x - p) % 12)


def _bass_below(p: int, lowest: int) -> int:
    """Bass pitch class p placed at least a fourth under `lowest` (no seconds/thirds clusters)."""
    return _below(p, lowest - 4)


def _at_or_above(p: int, ref: int) -> int:
    return ref + ((p - ref) % 12)


# ------------------------------------------------------------------------------------ voicings

VOICINGS = ('close', 'open', 'drop2', 'drop3', 'spread', 'smooth')


def _select(ch: Chord, voices: int | None) -> list[int]:
    """Intervals to voice: all distinct pitch classes, or the `voices` most important ones
    (doubling root, then fifth, when more voices than tones are asked for)."""
    prio, seen = [], set()
    for i in ch.priority():
        if i % 12 not in seen:
            seen.add(i % 12)
            prio.append(i)
    if voices is None or voices == len(prio):
        return prio
    if voices < 1:
        raise ComposeError(f"voices must be >= 1, got {voices}")
    if voices < len(prio):
        return prio[:voices]
    dbl = [0] + ([7] if 7 in ch.intervals else []) + [i for i in prio if i not in (0, 7)]
    out = list(prio)
    k = 0
    while len(out) < voices:
        out.append(dbl[k % len(dbl)] + 12 * (1 + k // len(dbl)))
        k += 1
    return out


def voice(ch, style: str = 'close', octave: int = 4, inversion: int = 0, voices: int | None = None,
          register: tuple | None = None, bass: bool = True) -> list[int]:
    """Voice one chord. Styles:
      close  - all tones inside one octave (extensions folded in), `inversion` rotates the bottom up
      open   - close root position with the 2nd and 4th voices raised an octave
      drop2  - close voicing with the 2nd-highest voice dropped an octave (drop3: 3rd-highest)
      spread - root an octave lower, then 5th, 3rd, 7th, tensions stacked upward with wide gaps
    `register=(lo, hi)` shifts the result by octaves to sit best inside that range.
    A slash bass is added below unless bass=False.
    Jazz styles (JAZZ_VOICINGS: rootless rootless_a rootless_b shell shell37 shell73 quartal sowhat ust) go to
    jazz_voice(); their register defaults to the left-hand zone C3..C5."""
    ch = Chord.parse(ch) if not isinstance(ch, Chord) else ch
    if style in JAZZ_VOICINGS:
        out = jazz_voice(ch, style, register=register if register is not None else LH_REGISTER, voices=voices)
        if bass and ch.bass is not None:
            out.insert(0, _bass_below(ch.bass, min(out)))
        return out
    ivs = _select(ch, voices)
    root = (octave + 1) * 12 + ch.root
    if style == 'spread':
        base = root - 12
        out = [base]
        prio = ch.priority()
        rest = [i for i in ivs if i % 12 != 0]
        rest.sort(key=lambda i: (0 if i % 12 == 7 else 1, prio.index(i) if i in prio else 9))
        cur = base
        for i in rest:
            cur = _at_or_above((ch.root + i) % 12, cur + 3)
            out.append(cur)
        for k in range(sum(1 for i in ivs if i % 12 == 0) - 1):  # doubled roots
            out.append(base + 12 * (k + 1))
        out.sort()
    elif style in ('close', 'open', 'drop2', 'drop3', 'drop24'):
        rel = []
        for i in ivs:
            r = i % 12
            while r in rel:
                r += 12
            rel.append(r)
        out = sorted(root + r for r in rel)
        for _ in range(inversion % max(1, len(out))):
            out = out[1:] + [out[0] + 12]
        if style == 'open' and len(out) >= 3:
            out = sorted(p + (12 if k in (1, 3) else 0) for k, p in enumerate(out))
        elif style in ('drop2', 'drop24') and len(out) >= 3:
            out[-2] -= 12
            if style == 'drop24' and len(out) >= 4:
                out[-4] -= 12
            out.sort()
        elif style == 'drop3' and len(out) >= 4:
            out[-3] -= 12
            out.sort()
    else:
        raise ComposeError(f"unknown voicing {style!r}; use one of {', '.join(VOICINGS)}, or a jazz style "
                           f"{', '.join(JAZZ_VOICINGS)} ('smooth' only works on progressions)")
    if register is not None:
        lo, hi = _register(register)
        center = (lo + hi) / 2

        def fit(k):
            ps = [p + 12 * k for p in out]
            outside = sum(max(0, lo - p) + max(0, p - hi) for p in ps)
            return outside * 10 + abs(sum(ps) / len(ps) - center)
        k = min(range(-5, 6), key=lambda k: (fit(k), abs(k)))
        out = [p + 12 * k for p in out]
    if bass and ch.bass is not None:
        out.insert(0, _bass_below(ch.bass, min(out)))
    return [p for p in out if 0 <= p <= 127]


def _register(reg) -> tuple[int, int]:
    try:
        lo, hi = reg
    except (TypeError, ValueError):
        raise ComposeError(f"register must be a (low, high) pair like (52, 76) or ('E3', 'E5'), got {reg!r}") from None
    lo, hi = note(lo), note(hi)
    if hi - lo < 11:
        raise ComposeError(f"register {reg!r} must span at least 11 semitones so every pitch class fits")
    return lo, hi


def _spacing_penalty(c: tuple[int, ...]) -> float:
    pen = 0.0
    for a, b in zip(c, c[1:]):
        d = b - a
        if d == 1:
            pen += 3.0          # minor-second cluster
        if a < 55 and d < 3:
            pen += 2.0          # low-register mud
        if a < 48 and d < 7:
            pen += 3.0
    span = c[-1] - c[0]
    if span > 19:
        pen += (span - 19) * 0.5
    return pen


def _double_cost(ch: Chord, interval: int) -> float:
    """Voice-leading penalty for doubling one chord tone: root 0, fifth 0.4, third / sus tone 1.0,
    seventh / sixth 1.6, tensions and alterations 2.2 (a doubled tension or leading tone sounds heavy)."""
    i = interval % 12
    if i == 0:
        return 0.0
    ivs = {x % 12 for x in ch.intervals}
    if i == 7 or (i in (6, 8) and 7 not in ivs):
        return 0.4
    if i in (3, 4) or (i in (2, 5) and not ivs & {3, 4}):
        return 1.0
    if i in (9, 10, 11) and interval < 12:
        return 1.6
    return 2.2


_MAX_CANDIDATES = 20000


def _candidates(ch: Chord, lo: int, hi: int, voices: int, near: list[int] | None) -> list[tuple[tuple[int, ...], float]]:
    """Every voicing of `ch` as `voices` distinct pitches in lo..hi, with its doubling cost.

    The most important distinct tones are always present (all of them when voices >= the number of pitch
    classes; else the `voices` most important: root, 3rd, 7th, tensions, 5th last). Extra voices double ANY
    chord tone - root preferred, then fifth, then third, ... (_double_cost) - so a narrow register that has
    room for only one root can still double the third or fifth (Am -> F in 55..76: A3 C4 F4 A4)."""
    if voices < 1:
        raise ComposeError(f"voices must be >= 1, got {voices}")
    prio, seen = [], set()
    for i in ch.priority():
        if i % 12 not in seen:
            seen.add(i % 12)
            prio.append(i)
    req = prio[:voices]
    extra = voices - len(req)
    options = [[p for p in range(lo, hi + 1) if p % 12 == (ch.root + i) % 12] for i in req]
    if any(not o for o in options):
        raise ComposeError(f"register {lo}..{hi} can't hold every pitch class of {ch.symbol}")
    plans = []
    for plan in itertools.combinations_with_replacement(range(len(req)), extra):
        counts = [1] * len(req)
        for j in plan:
            counts[j] += 1
        plans.append((counts, sum(_double_cost(ch, req[j]) for j in plan)))

    def size(opts) -> int:
        return sum(math.prod(math.comb(len(o), c) for o, c in zip(opts, counts)) for counts, _ in plans)
    ref = near if near else [(lo + hi) // 2]
    for keep in (6, 5, 4, 3):  # keep the enumeration bounded for huge registers / many voices
        if size(options) <= _MAX_CANDIDATES:
            break
        options = [sorted(sorted(o, key=lambda p: (min(abs(p - r) for r in ref), p))[:keep]) for o in options]
    cands: dict[tuple[int, ...], float] = {}
    for counts, cost in plans:
        if any(c > len(o) for o, c in zip(options, counts)):
            continue
        for combo in itertools.product(*(itertools.combinations(o, c) for o, c in zip(options, counts))):
            v = tuple(sorted(p for grp in combo for p in grp))
            if cost < cands.get(v, math.inf):
                cands[v] = cost
    if not cands:
        raise ComposeError(f"can't voice {ch.symbol} with {voices} voices in {lo}..{hi} (not enough distinct "
                           f"chord-tone pitches); widen the register or use fewer voices")
    return sorted(cands.items())


def voice_lead(chords, register=(52, 76), voices: int | None = 4, bass: bool = False,
               start: list[int] | None = None) -> list[list[int]]:
    """Voice a chord sequence so each voice moves as little as possible (smooth pads/keys).

    Every chord gets `voices` notes inside `register` (the most important tones first: root, 3rd,
    7th, tensions, 5th last). Extra voices double a chord tone - any tone may double, the root is
    preferred, then the fifth - whichever gives the smoothest motion that fits the register. The first
    chord is a compact voicing near the middle of the register (or closest to `start`). With bass=True
    the slash bass / root is added below each voicing."""
    lo, hi = _register(register)
    center = (lo + hi) / 2
    prev = sorted(start) if start else None
    out = []
    for c in chords:
        ch = Chord.parse(c) if not isinstance(c, Chord) else c
        n = voices if voices is not None else len({i % 12 for i in ch.intervals})
        best, best_cost = None, math.inf
        for cand, dbl in _candidates(ch, lo, hi, n, prev):
            mean = sum(cand) / len(cand)
            if prev is None:
                cost = abs(mean - center) * 0.75 + (cand[-1] - cand[0]) * 0.15
            elif len(prev) == len(cand):
                cost = sum(abs(a - b) for a, b in zip(cand, prev)) + 0.5 * abs(cand[-1] - prev[-1])
            else:
                cost = (sum(min(abs(c - p) for p in prev) for c in cand)
                        + sum(min(abs(c - p) for c in cand) for p in prev))
            cost += _spacing_penalty(cand) + 0.08 * abs(mean - center) + dbl
            if cost < best_cost - 1e-9:
                best, best_cost = cand, cost
        v = list(best)
        prev = v
        if bass:
            v = [_bass_below(ch.bass_pc, v[0])] + v
        out.append(v)
    return out


# -------------------------------------------------------------------------------- jazz harmony

LH_REGISTER = (48, 72)
"""C3..C5: the left-hand comping zone (rootless voicings, shells) - the default register of the jazz voicings."""

JAZZ_VOICINGS = ('rootless', 'rootless_a', 'rootless_b', 'shell', 'shell37', 'shell73', 'quartal', 'sowhat', 'ust')
"""Jazz voicing styles for voice() / jazz_voice() / jazz_voicings() / Progression.voiced() / chords():
rootless (A or B form, whichever sits better; in sequences they alternate), rootless_a (3-5-7-9, 13 for 5 on
dominants), rootless_b (7-9-3-5), shell (3+7 or 7+3), shell37, shell73, quartal (stacked 4ths from the chord
scale), sowhat (three 4ths + a major 3rd), ust (upper-structure triad over the 3/7 tritone, altered dominants)."""

LOW_INTERVAL_LIMITS = {1: 52, 2: 51, 3: 48, 4: 46, 5: 45, 6: 47, 7: 34, 8: 43, 9: 41, 10: 41, 11: 41,
                       13: 40, 14: 39, 15: 36, 16: 34}
"""Low interval limits (Berklee): semitones between two adjacent voices -> the lowest MIDI pitch the LOWER note may
have before the interval turns to mud (minor 2nd E3, major 2nd Eb3, minor 3rd C3, major 3rd Bb2, 4th A2,
tritone B2, 5th Bb1, 6ths / 7ths F2, 9ths Eb2..E2, 10ths C2..Bb1)."""

CHORD_KINDS = ('maj', 'maj7', '6', 'dom', 'sus', 'min', 'm7', 'm6', 'mmaj7', 'm7b5', 'dim', 'dim7', 'aug', 'power')

CHORD_SCALES: dict[str, tuple[int, ...]] = {
    'ionian': (0, 2, 4, 5, 7, 9, 11), 'lydian': (0, 2, 4, 6, 7, 9, 11), 'lydian_aug': (0, 2, 4, 6, 8, 9, 11),
    'dorian': (0, 2, 3, 5, 7, 9, 10), 'aeolian': (0, 2, 3, 5, 7, 8, 10), 'phrygian': (0, 1, 3, 5, 7, 8, 10),
    'melodic_minor': (0, 2, 3, 5, 7, 9, 11), 'mixolydian': (0, 2, 4, 5, 7, 9, 10),
    'lydian_dominant': (0, 2, 4, 6, 7, 9, 10), 'mixolydian_b6': (0, 2, 4, 5, 7, 8, 10),
    'phrygian_dominant': (0, 1, 4, 5, 7, 8, 10), 'altered': (0, 1, 3, 4, 6, 8, 10),
    'half_whole': (0, 1, 3, 4, 6, 7, 9, 10), 'whole_half': (0, 2, 3, 5, 6, 8, 9, 11), 'whole_tone': (0, 2, 4, 6, 8, 10),
    'locrian': (0, 1, 3, 5, 6, 8, 10), 'locrian_2': (0, 2, 3, 5, 6, 8, 10),
}
"""Chord scales (intervals above the chord root) used for jazz colour tones, quartal voicings and tension checks."""


def mud(pitches) -> list[tuple[int, int]]:
    """Adjacent voice pairs (low, high) whose interval sits below its low interval limit (LOW_INTERVAL_LIMITS:
    a minor 2nd needs its lower note at E3 or higher, a 3rd around C3 / Bb2, a 5th Bb1 ...). [] = clear."""
    ps = sorted(note(p) for p in pitches)
    return [(a, b) for a, b in zip(ps, ps[1:]) if (b - a) in LOW_INTERVAL_LIMITS and a < LOW_INTERVAL_LIMITS[b - a]]


def chord_kind(ch) -> str:
    """Harmonic family of a chord (one of CHORD_KINDS): maj, maj7 (incl. maj9, maj7#11, maj7#5), 6 (6, 6/9),
    dom (every dominant 7th: 9, 13, 7b9, 7#9, 7alt, 7#5, 7b5 ...), sus (7sus4 family and sus triads), min, m7
    (m9, m11 ...), m6, mmaj7, m7b5, dim, dim7, aug, power."""
    c = Chord.parse(ch)
    iv = set(c.intervals)
    if iv <= {0, 7}:
        return 'power'
    third = 4 if 4 in iv else 3 if 3 in iv else None
    if third == 3 and 6 in iv and 7 not in iv:
        return 'm7b5' if 10 in iv else 'dim7' if 9 in iv else 'dim'
    if third is None:
        return 'sus'
    if 10 in iv:
        return 'dom' if third == 4 else 'm7'
    if 11 in iv:
        return 'mmaj7' if third == 3 else 'maj7'
    if 9 in iv:
        return 'm6' if third == 3 else '6'
    if third == 4 and 8 in iv and 7 not in iv:
        return 'aug'
    return 'min' if third == 3 else 'maj'


def guide_tones(ch) -> tuple[int, int | None]:
    """(3rd, 7th) of a chord as pitch classes - the two tones that define its quality. A sus chord's 4th stands in
    for the 3rd (so does the 11 of a dominant '11' chord); 6th chords and dim7 use the 6th / bb7; a triad has no
    7th (None) - except that jazz reads a plain major triad as a 6th chord, minor as m7, dim as dim7, sus as 7sus4
    (the rootless voicings do the same)."""
    c = Chord.parse(ch)
    s = _slots(c)
    return (c.root + s['3']) % 12, (None if s['7'] is None else (c.root + s['7']) % 12)


def chord_scale_name(ch, resolve_minor: bool = False) -> str:
    """Name of the chord scale (CHORD_SCALES) that fits a chord: major-type ionian (lydian with #11), minor dorian
    (aeolian with b13, phrygian with b9), m6 dorian, m(maj7) melodic minor, m7b5 locrian (locrian #2 with a 9),
    dim / dim7 whole-half, aug whole tone, sus mixolydian; dominants: mixolydian, lydian dominant (#11), mixolydian
    b6 (b13), half-whole diminished (b9 / #9 with natural 13), altered (b9 / #9 with b13, 7alt), whole tone (7#5, 7b5).
    resolve_minor=True: a dominant resolving to a minor chord takes b9 / b13 (phrygian dominant / altered) unless
    its symbol asks for natural tensions."""
    c = Chord.parse(ch)
    iv = set(c.intervals)
    k = chord_kind(c)
    b9, n9, s9, n11, s11, b13, n13 = (x in iv for x in (13, 14, 15, 17, 18, 20, 21))
    if k in ('maj', 'maj7', '6', 'power'):
        if 8 in iv and k == 'maj7':
            return 'lydian_aug'
        return 'lydian' if s11 or 6 in iv else 'ionian'
    if k in ('min', 'm7'):
        return 'phrygian' if b9 else 'aeolian' if b13 else 'dorian'
    if k == 'm6':
        return 'dorian'
    if k == 'mmaj7':
        return 'melodic_minor'
    if k == 'm7b5':
        return 'locrian_2' if n9 else 'locrian'
    if k in ('dim', 'dim7'):
        return 'whole_half'
    if k == 'aug':
        return 'whole_tone'
    if k == 'sus':
        return 'phrygian' if b9 else 'mixolydian'
    # dominant
    sharp5 = 8 in iv and 7 not in iv
    if (b9 or s9) and (b13 or sharp5):
        return 'altered'
    if sharp5 or (6 in iv and 7 not in iv and not n13):
        return 'whole_tone'
    if b9 or s9:
        if resolve_minor and not n13:
            return 'altered' if s9 else 'phrygian_dominant'
        return 'half_whole'
    if b13:
        return 'mixolydian_b6'
    if s11 or 6 in iv:
        return 'lydian_dominant'
    if resolve_minor and not (n9 or n13 or n11):
        return 'phrygian_dominant'
    return 'mixolydian'


def chord_scale(ch, resolve_minor: bool = False) -> tuple[int, ...]:
    """Intervals of the chord scale above the chord root (see chord_scale_name): chord_scale('Dm7') = dorian."""
    return CHORD_SCALES[chord_scale_name(ch, resolve_minor)]


def available_tensions(ch, resolve_minor: bool = False) -> frozenset[int]:
    """Intervals (0..11 above the root) that may colour a chord without clashing: its chord scale minus the chord
    tones minus avoid notes (a half step above a chord tone: the 11 over a major 3rd, b13 over a minor chord's 5th,
    b9 over minor chords), plus every tension written in the symbol. On dominants the altered tones b9 #9 #11 b13 of
    the chord scale are never avoided; on sus chords the major 3rd is."""
    c = Chord.parse(ch)
    k = chord_kind(c)
    s = _slots(c, resolve_minor)
    tones = {x % 12 for x in c.intervals} | {v % 12 for key, v in s.items() if key in ('3', '7') and v is not None}
    out = set()
    for x in chord_scale(c, resolve_minor):
        if x in tones:
            continue
        if k == 'dom' and x in (1, 3, 6, 8):
            out.add(x)
            continue
        if (x - 1) % 12 in tones:
            continue
        if k == 'sus' and x in (3, 4):
            continue
        out.add(x)
    return frozenset(out | {x % 12 for x in c.intervals if x >= 12})


def _slots(c: Chord, resolve_minor: bool = False) -> dict[str, int | None]:
    """Intervals (0..11) of the four rootless slots of a chord: '3' (3rd / sus 4th), '5' (5th, or on dominants the
    13th / its alteration), '7' (7th / 6th), '9' (9th / its alteration; root or 11 on m7b5, root on dim7). Tensions
    written in the symbol win; missing colour comes from the chord scale (natural 9 and 13 on plain dominants,
    b9 / b13 when resolving to minor, #9 / b13 on 7alt)."""
    iv = set(c.intervals)
    k = chord_kind(c)
    sc = set(chord_scale(c, resolve_minor))
    if k == 'power':
        return {'3': 7, '5': 2, '7': 0, '9': None}
    if k == 'sus' or (k == 'dom' and 17 in iv):   # jazz reads C11 as C9sus4: the 11 replaces the 3rd
        t3 = 5 if (5 in iv or 17 in iv or 2 not in iv) else 2
    else:
        t3 = 4 if 4 in iv else 3
    t7 = {'dom': 10, 'm7': 10, 'm7b5': 10, 'maj7': 11, 'mmaj7': 11, '6': 9, 'm6': 9, 'dim7': 9, 'dim': 9,
          'maj': 9, 'min': 10, 'aug': 0}.get(k)
    if k == 'sus':
        t7 = 10 if 10 in iv or 9 not in iv else 9
    # 9-slot
    if k == 'm7b5':
        n9 = 2 if 14 in iv else 5 if 17 in iv else 0
    elif k in ('dim', 'dim7'):
        n9 = 0
    else:
        written = [x for x in (15, 13, 14) if x in iv]
        if written:
            n9 = written[0] % 12
        elif k in ('dom', 'sus'):
            n9 = 3 if (1 in sc and 3 in sc and 2 not in sc and 4 in sc and 8 in sc and 9 not in sc) else \
                1 if (1 in sc and 2 not in sc) else 2
        else:
            n9 = 2
    # 5-slot
    if k == 'dom':
        if 20 in iv or 8 in iv:
            n5 = 8
        elif 18 in iv or 6 in iv:
            n5 = 6
        elif 21 in iv:
            n5 = 9
        elif 17 in iv:                  # C11 (= C9sus4): the fifth under the 11
            n5 = 7
        else:
            n5 = 8 if (8 in sc and 9 not in sc) else 9 if 9 in sc else 7
    elif k == 'sus':
        n5 = 9 if 21 in iv else 7
    elif k == 'maj7':
        n5 = 6 if (18 in iv or 6 in iv) else 8 if 8 in iv else 9 if 21 in iv else 7
    elif k in ('m7', 'min'):
        n5 = 9 if 21 in iv else 5 if 17 in iv else 7
    elif k in ('m7b5', 'dim', 'dim7'):
        n5 = 6
    elif k == 'aug':
        n5 = 8
    else:
        n5 = 7
    return {'3': t3, '5': n5, '7': t7, '9': n9}


_FORMS = {'A': ('3', '5', '7', '9'), 'B': ('7', '9', '3', '5')}
_FORMS3 = {'A': ('3', '7', '9'), 'B': ('7', '3', '5')}
_FORMS3_DIM = {'A': ('3', '5', '7'), 'B': ('7', '3', '5')}


def _stack(pcs: list[int], base: int = 48) -> list[int]:
    """Pitch classes stacked upward in the given order (each voice the nearest pitch above the previous one)."""
    out = [_at_or_above(pcs[0], base)]
    for p in pcs[1:]:
        out.append(out[-1] + 1 + ((p - out[-1] - 1) % 12))
    return out


def _reg_cost(ps: list[int], lo: int, hi: int, center: float) -> float:
    outside = sum(max(0, lo - p) + max(0, p - hi) for p in ps)
    return outside * 4.0 + len(mud(ps)) * 12.0 + abs(sum(ps) / len(ps) - center)


def _center(lo: int, hi: int) -> float:
    return lo + (hi - lo) * 0.45


def _place(stack: list[int], register) -> list[int]:
    """Shift a stacked voicing by octaves to sit best in the register (inside, clear of mud, near its centre)."""
    lo, hi = _register(register)
    c = _center(lo, hi)
    cands = [[p + 12 * k for p in stack] for k in range(-8, 9)]
    cands = [x for x in cands if min(x) >= 0 and max(x) <= 127]
    return min(cands, key=lambda x: (_reg_cost(x, lo, hi, c), abs(x[0] - lo)))


def _placements(stack: list[int], register, slack: int = 5) -> list[list[int]]:
    """Every octave shift of a stack that stays within `slack` semitones of the register (at least the best one)."""
    lo, hi = _register(register)
    out = []
    for k in range(-8, 9):
        ps = [p + 12 * k for p in stack]
        if min(ps) < 0 or max(ps) > 127:
            continue
        if sum(max(0, lo - p) + max(0, p - hi) for p in ps) <= slack:
            out.append(ps)
    return out or [_place(stack, register)]


def _form_pcs(c: Chord, form: str, voices: int, resolve_minor: bool) -> list[int]:
    s = _slots(c, resolve_minor)
    if voices not in (3, 4):
        raise ComposeError(f"rootless voicings have 3 or 4 voices, got {voices!r}")
    k = chord_kind(c)
    if k == 'power':        # no 3rd to voice: 5-1-9 / 1-9-5 (open, modal)
        r = c.root
        return [(r + 7) % 12, r, (r + 2) % 12] if form == 'A' else [r, (r + 2) % 12, (r + 7) % 12]
    order =(_FORMS if voices == 4 else _FORMS3_DIM if k in ('m7b5', 'dim', 'dim7') else _FORMS3)[form]
    pcs = [(c.root + s[x]) % 12 for x in order if s[x] is not None]
    seen, out = set(), []
    for p in pcs:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def rootless(ch, form: str = 'A', voices: int = 4, register=LH_REGISTER, resolve_minor: bool = False) -> list[int]:
    """Bill Evans rootless voicing (no root: the bassist plays it). form 'A' stacks 3-5-7-9 from the 3rd, 'B'
    7-9-3-5 from the 7th; dominants take the 13th for the 5th (3-13-b7-9 / b7-9-3-13), alterations written in the
    symbol win (7b9, 7#9, 7alt = 3-b13-b7-#9, 7#11, 7b13), m7b5 uses the root (or its 9 / 11) as the top colour,
    6 / 6-9 / m6 chords put the 6th in the 7th's place, triads read as 6/9 (major), m9 (minor), dim7, 7sus4.
    voices=3: A = 3-7-9, B = 7-3-5 (m7b5 / dim keep the b5). Placed by octaves inside `register` (default C3..C5),
    clear of low-interval mud. resolve_minor=True colours a dominant for a minor resolution (b9, b13).
        rootless('Dm7', 'A') -> F3 A3 C4 E4    rootless('G7', 'B') -> F3 A3 B3 E4    rootless('Cmaj7') -> E3 G3 B3 D4"""
    c = Chord.parse(ch)
    f = str(form).upper()
    if f not in _FORMS:
        raise ComposeError(f"rootless form must be 'A' (3-5-7-9) or 'B' (7-9-3-5), got {form!r}")
    return _place(_stack(_form_pcs(c, f, 4 if voices is None else voices, resolve_minor)), register)


def shell(ch, form: str = '37', register=LH_REGISTER, root: bool = False, tension: bool = False) -> list[int]:
    """Shell voicing: the guide tones only - '37' (3rd below the 7th) or '73' (7th below the 3rd); m7b5 adds its b5
    (else it would be m7), 6th chords use the 6th. tension=True adds the chord's 9-slot colour on top (a 3-note
    'shell + 1'). root=True is the Bud Powell shell for piano without a bassist: the root in the bass zone (E2..D#3)
    with the 7th (+ tension) and the 10th above it (G7: G2 F3 B3), `form` and `register` then don't apply."""
    c = Chord.parse(ch)
    s = _slots(c)
    if form not in ('37', '73'):
        raise ComposeError(f"shell form must be '37' (3rd below 7th) or '73', got {form!r}")
    if s['7'] is None or chord_kind(c) == 'power':
        raise ComposeError(f"{c.symbol}: a power chord has no 3rd / 7th for a shell voicing")
    t3, t7 = (c.root + s['3']) % 12, (c.root + s['7']) % 12
    pcs = [t3, t7] if form == '37' else [t7, t3]
    if chord_kind(c) in ('m7b5', 'dim', 'dim7'):
        pcs.insert(1 if form == '37' else 2, (c.root + 6) % 12)
    if tension:
        pcs.append((c.root + s['9']) % 12)
    if root:        # root in the bass zone, then 7th (+ tension) and 10th above it: G2 F3 B3 (clear of mud)
        r = _at_or_above(c.root, 40)
        up = [t7] + [p for p in pcs if p not in (t3, t7)] + [t3]
        return _stack([c.root] + up, r)
    return _place(_stack(pcs), register)


def quartal(ch, voices: int = 4, register=LH_REGISTER, resolve_minor: bool = False) -> list[int]:
    """Quartal voicing: `voices` notes stacked in 4ths (perfect, or one augmented 4th where the scale needs it)
    taken from the chord scale, choosing the stack that holds the 3rd and 7th, the symbol's alterations and no avoid
    notes: Dm7 -> D G C F, G7 -> F B E A, Cmaj7 -> B E A D, G7alt -> B F Bb Eb."""
    c = Chord.parse(ch)
    if not 2 <= voices <= 6:
        raise ComposeError(f"quartal voicings take 2..6 voices, got {voices!r}")
    return _place(_quartal_stack(c, voices, resolve_minor), register)


def _quartal_stack(c: Chord, voices: int, resolve_minor: bool = False) -> list[int]:
    sc = [(c.root + i) % 12 for i in chord_scale(c, resolve_minor)]
    spcs = set(sc)
    g3, g7 = guide_tones(c)
    tens = available_tensions(c, resolve_minor)
    chord_pcs = {(c.root + i) % 12 for i in c.intervals}
    allowed = chord_pcs | {(c.root + t) % 12 for t in tens} | {g3} | ({g7} if g7 is not None else set())
    alters = {(c.root + i) % 12 for i in c.intervals if i in (6, 8, 13, 15, 18, 20)}
    best, best_key = None, None
    for start in sc:
        stack, tritones, ok = [start], 0, True
        for _ in range(voices - 1):
            p = stack[-1]
            if (p + 5) % 12 in spcs:
                stack.append(p + 5)
            elif (p + 6) % 12 in spcs and tritones == 0:
                stack.append(p + 6)
                tritones += 1
            else:
                ok = False
                break
        if not ok:
            continue
        pcs = {x % 12 for x in stack}
        score = (3.0 * (g3 in pcs) + 3.0 * (g7 in pcs) - 5.0 * len(pcs - allowed) + 1.0 * min(2, len(pcs & alters))
                 - 0.4 * tritones - 0.3 * (c.root in pcs))
        key = (score, -tritones, -((start - c.root) % 12))
        if best_key is None or key > best_key:
            best, best_key = stack, key
    if best is None:
        raise ComposeError(f"{c.symbol}: its chord scale ({chord_scale_name(c, resolve_minor)}) has no stack of "
                           f"{voices} fourths")
    return _stack([p % 12 for p in best])


def so_what(ch, register=LH_REGISTER) -> list[int]:
    """The 'So What' voicing (Bill Evans on Kind of Blue): three perfect 4ths and a major 3rd on top. Minor chords
    stack it from the root (Dm7: D G C F A); other chords from the chord-scale note whose So What shape holds the
    3rd and 7th without avoid notes (Cmaj7: E A D G B); dominants fall back to a 5-note quartal stack."""
    c = Chord.parse(ch)
    shape = (0, 5, 10, 15, 19)
    k = chord_kind(c)
    if k in ('m7', 'min'):          # (not m6: the root shape holds the b7, which a 6th chord doesn't have)
        return _place([c.root + x for x in shape], register)
    sc = [(c.root + i) % 12 for i in chord_scale(c)]
    g3, g7 = guide_tones(c)
    avoid_free = ({(c.root + i) % 12 for i in c.intervals} | {(c.root + t) % 12 for t in available_tensions(c)}
                  | {g3} | ({g7} if g7 is not None else set()))    # a triad's implied 6th / 7th counts too
    for x in sc:
        pcs = {(x + d) % 12 for d in shape}
        if pcs <= set(sc) and g3 in pcs and (g7 is None or g7 in pcs) and pcs <= avoid_free:
            return _place([x + d for d in shape], register)
    return _place(_quartal_stack(c, 5), register)


BLOCK_STYLES = ('close', 'drop2', 'drop24', 'locked')


def _block_set(c: Chord, mel: int) -> list[int]:
    """The 4-note chord (intervals 0..11) under a block-chord melody note: 6th chords on major (maj7 when the melody
    is the 7th), dominant / minor / m6 / m7b5 / dim7 sets; written alterations replace the tone they alter; a melody
    tension replaces the chord tone just below it (9 for the root, 11 for the 3rd on minor, 13 / b13 / #11 for 5)."""
    iv = set(c.intervals)
    k = chord_kind(c)
    m = (mel - c.root) % 12
    if k in ('maj', 'maj7', '6', 'power'):
        base = [0, 4, 7, 11] if (k == 'maj7' and m == 11) else [0, 4, 7, 9]
        if 18 in iv or 6 in iv:
            base = [6 if x == 7 else x for x in base]
        if 8 in iv and 7 not in iv:
            base = [8 if x == 7 else x for x in base]
    elif k in ('dom', 'aug'):
        base = [0, 4, 7, 10]
        if 13 in iv:
            base[0] = 1
        elif 15 in iv:
            base[0] = 3
        if 20 in iv or 8 in iv:
            base[2] = 8
        elif 6 in iv or 18 in iv:
            base[2] = 6
        elif 21 in iv:
            base[2] = 9
        if 17 in iv:                    # C11 = C9sus4
            base[1] = 5
    elif k == 'sus':
        base = [0, 5, 7, 10 if 10 in iv or 9 not in iv else 9]
    elif k in ('m7', 'min'):
        base = [0, 3, 7, 10]
    elif k == 'm6':
        base = [0, 3, 7, 9]
    elif k == 'mmaj7':
        base = [0, 3, 7, 11]
    elif k == 'm7b5':
        base = [0, 3, 6, 10]
    else:                               # dim, dim7
        base = [0, 3, 6, 9]
    if m in base:
        return base
    tens = available_tensions(c)
    if m in tens or m in {x % 12 for x in iv}:
        # tension substitution: 9 (b9, #9) for the root, 11 for the 3rd, #11 / b13 / 13 for the 5th, 7 for the 6th
        third = next((x for x in base if x in (3, 4, 5)), None)
        repl = {1: 0, 2: 0, 3: 0, 5: third, 6: 7, 8: 7, 9: 7, 10: 9, 11: 9}.get(m)
        if repl is None or repl not in base:
            repl = max((x for x in base if x < m), default=max(base))
        return sorted([x for x in base if x != repl] + [m])
    return []        # a non-chord tone: the caller harmonizes it with a diminished 7th


def block(ch, melody, style: str = 'drop2') -> list[int]:
    """Block chord under one melody note (the melody stays on top): a 4-way close voicing of the chord's 4-note set
    (6th chord on major, maj7 if the melody is the 7th; dominant, m7, m6, m7b5, dim7), a melody tension replacing the
    chord tone below it, and a non-chord (passing) melody note harmonized with the diminished 7th built down from it
    (Shearing / Barry Harris). style: close (4-way close), drop2 (2nd voice from the top an octave down: the
    guitar-friendly spread), drop24, locked (locked hands: 4-way close + the melody doubled an octave below)."""
    c = Chord.parse(ch)
    m = note(melody)
    if style not in BLOCK_STYLES:
        raise ComposeError(f"block style must be one of {', '.join(BLOCK_STYLES)}, got {style!r}")
    base = _block_set(c, m)
    rel = sorted({(m - (c.root + x)) % 12 for x in base} - {0}) if base else [3, 6, 9]
    close = sorted([m] + [m - d for d in rel[:3]])
    if style == 'close':
        out = close
    elif style == 'drop2':
        out = sorted(close[:-2] + [close[-2] - 12, close[-1]])
    elif style == 'drop24':
        out = sorted([close[0] - 12, close[1], close[2] - 12, close[3]]) if len(close) == 4 else close
    else:
        out = sorted(close + [m - 12])
    if min(out) < 0:
        raise ComposeError(f"block chord under melody {m} goes below MIDI 0; use a higher melody")
    return out


UPPER_STRUCTURES = {'II': (2, 'maj'), 'bIII': (3, 'maj'), 'bV': (6, 'maj'), 'bVI': (8, 'maj'), 'VI': (9, 'maj'),
                    'bIIm': (1, 'min'), '#IVm': (6, 'min')}
"""Upper-structure triads over a dominant (name: triad root above the chord root, quality) and what they add:
II = 9 #11 13 (13#11), bIII = #9 5 b7 (7#9), bV = b5 b7 b9 (7b9b5), bVI = b13 1 #9 (7#5#9 / alt), VI = 13 b9 3
(13b9), bIIm = b9 3 b13 (7b9b13), #IVm = #11 13 b9 (13b9#11)."""


def _ust_auto(c: Chord, resolve_minor: bool = False) -> str | None:
    iv = set(c.intervals)
    b9, s9, s11, b13, n13 = 13 in iv, 15 in iv, (18 in iv or (6 in iv and 7 not in iv)), (20 in iv or 8 in iv), 21 in iv
    if (b9 and s9) or (s9 and b13):
        return 'bVI'
    if b9 and b13:
        return 'bIIm'
    if b9 and s11:
        return '#IVm' if n13 else 'bV'
    if b9:
        return 'bIIm' if resolve_minor else 'VI'
    if s9:
        return 'bVI' if resolve_minor else 'bIII'
    if b13:
        return 'bVI'
    if s11:
        return 'II'
    return None


def upper_structure(ch, triad: str = 'auto', register=(52, 84), top=None, resolve_minor: bool = False) -> list[int]:
    """Upper-structure voicing of a dominant: the 3rd and b7 (a tritone) in the left hand and a major / minor triad
    on top that spells the tensions (UPPER_STRUCTURES): G7alt -> F3 B3 | Eb4 G4 Bb4 (bVI). triad='auto' picks it from
    the symbol's alterations: alt / #9b13 -> bVI, b9b13 -> bIIm, b9#11 -> bV, 7b9 -> VI, 7#9 -> bIII, #11 -> II
    (resolve_minor=True prefers bIIm / bVI). top= a melody pitch the triad's top note should sit at or just below."""
    c = Chord.parse(ch)
    if chord_kind(c) != 'dom':
        raise ComposeError(f"upper structures are for dominant 7th chords; {c.symbol} is a {chord_kind(c)} chord")
    name = _ust_auto(c, resolve_minor) if triad == 'auto' else triad
    if name is None:
        raise ComposeError(f"{c.symbol}: triad='auto' needs an altered dominant (b9, #9, #11, b13, alt); for a natural "
                           f"dominant say which: triad='II' (13#11) or 'VI' (13b9)")
    if name not in UPPER_STRUCTURES:
        raise ComposeError(f"unknown upper structure {name!r}; use one of {', '.join(UPPER_STRUCTURES)} or 'auto'")
    lo, hi = _register(register)
    off, q = UPPER_STRUCTURES[name]
    t3, t7 = (c.root + 4) % 12, (c.root + 10) % 12
    lhs = [_stack([t3, t7]), _stack([t7, t3])]
    lh = min(([p + 12 * k for p in s] for s in lhs for k in range(-3, 4)),
             key=lambda x: (abs(x[0] - (lo + 3)) + 10 * max(0, lo - x[0]), x[0]))
    r = (c.root + off) % 12
    tri = [r, (r + (4 if q == 'maj' else 3)) % 12, (r + 7) % 12]
    target = note(top) if top is not None else min(hi, lh[-1] + 12)
    best = None
    for inv in range(3):
        order = tri[inv:] + tri[:inv]
        st = _stack(order, lh[-1] + 1)
        while st[-1] + 12 <= target:
            st = [p + 12 for p in st]
        key = (abs(st[-1] - target) + 10 * max(0, st[-1] - hi), st[-1])
        if best is None or key < best[0]:
            best = (key, st)
    return lh + best[1]


def jazz_voice(ch, style: str = 'rootless', register=LH_REGISTER, voices: int | None = None,
               resolve_minor: bool = False) -> list[int]:
    """One chord in a jazz style (JAZZ_VOICINGS). 'rootless' / 'shell' pick the form that sits best in the register;
    use jazz_voicings() for a voice-led sequence (A/B forms alternate, guide tones move by step)."""
    c = Chord.parse(ch)
    if style not in JAZZ_VOICINGS:
        raise ComposeError(f"unknown jazz voicing {style!r}; use one of {', '.join(JAZZ_VOICINGS)}")
    cands = _jazz_candidates(c, style, register, 4 if voices is None else voices, resolve_minor)
    lo, hi = _register(register)
    cen = _center(lo, hi)
    return list(min(cands, key=lambda x: (_reg_cost(x[0], lo, hi, cen), x[1]))[0])


def _jazz_candidates(c: Chord, style: str, register, voices: int, resolve_minor: bool) -> list[tuple[list[int], str]]:
    k = chord_kind(c)
    if style == 'ust':
        if k == 'dom' and _ust_auto(c, resolve_minor) is not None:
            lo, hi = _register(register)
            ust_reg = (max(lo, 50), max(hi, lo + 30))
            return [(upper_structure(c, register=ust_reg, resolve_minor=resolve_minor), 'U')]
        style = 'rootless'
    if style.startswith('rootless'):
        if k == 'power':
            return [(p, 'P') for p in _placements(_stack([(c.root + 7) % 12, c.root, (c.root + 2) % 12]), register)]
        forms = ['A', 'B'] if style == 'rootless' else [style[-1].upper()]
        v = 4 if voices not in (3, 4) else voices
        return [(p, f) for f in forms for p in _placements(_stack(_form_pcs(c, f, v, resolve_minor)), register)]
    try:
        if style.startswith('shell'):
            forms = ['37', '73'] if style == 'shell' else [style[-2:]]
            out = []
            for f in forms:
                base = shell(c, f, register, tension=voices == 3)
                out += [(p, f) for p in _placements(base, register)]
            return out
        if style == 'quartal':
            n = voices if 2 <= voices <= 6 else 4
            return [(p, 'Q') for p in _placements(_quartal_stack(c, n, resolve_minor), register)]
        return [(p, 'S') for p in _placements(so_what(c, register), register)]   # sowhat
    except ComposeError:        # no shell for a power chord, no stack of 4ths in a diminished scale
        return _jazz_candidates(c, 'rootless', register, 4, resolve_minor)


def jazz_voicings(chords, style: str = 'rootless', register=LH_REGISTER, voices: int | None = 4,
                  start: list[int] | None = None) -> list[list[int]]:
    """Voice-led jazz voicings for a chord sequence (a dynamic programme over every form and octave of each chord):
    minimal total motion, top voice kept smooth, no low-interval mud, the sequence centred in `register` (default
    C3..C5). For rootless voicings the A and B forms alternate where the roots move by 4ths / 5ths, so the guide
    tones move by step (ii-V-I in C: F3 A3 C4 E4 -> F3 A3 B3 E4 -> E3 G3 B3 D4). A dominant resolving down a 5th (or a
    half step) to a minor chord gets b9 / b13 colour unless its symbol asks otherwise. style: JAZZ_VOICINGS."""
    chs = [Chord.parse(c) for c in chords]
    if not chs:
        return []
    if style not in JAZZ_VOICINGS:
        raise ComposeError(f"unknown jazz voicing {style!r}; use one of {', '.join(JAZZ_VOICINGS)}")
    lo, hi = _register(register)
    cen = _center(lo, hi)
    n = 4 if voices is None else voices
    layers = []
    for i, c in enumerate(chs):
        nxt = chs[i + 1] if i + 1 < len(chs) else None
        rm = (chord_kind(c) == 'dom' and nxt is not None and chord_kind(nxt) in ('min', 'm7', 'm6', 'mmaj7', 'm7b5')
              and (nxt.root - c.root) % 12 in (5, 11))
        layers.append(_jazz_candidates(c, style, register, n, rm))

    def node_cost(v):
        # free drift within a few semitones of the centre, then a firm pull back (an octave shift of the hand
        # beats a long crawl out of the comping zone)
        dev = abs(sum(v) / len(v) - cen)
        outside = sum(max(0, lo - p) + max(0, p - hi) for p in v)
        return outside * 10.0 + len(mud(v)) * 6.0 + 0.15 * dev + 1.5 * max(0.0, dev - 4.0)

    def edge_cost(a, fa, b, fb, ca, cb):
        if len(a) == len(b):
            move = sum(abs(x - y) for x, y in zip(a, b))
        else:
            move = sum(min(abs(x - y) for y in b) for x in a) + sum(min(abs(x - y) for x in a) for y in b)
        cost = move + 0.35 * abs(a[-1] - b[-1])
        if style.startswith('rootless') and fa in 'AB' and fb in 'AB' and (cb.root - ca.root) % 12 in (5, 7) \
                and fa == fb and chord_kind(ca) != 'power':
            cost += 1.5
        return cost

    prev = [(node_cost(v) + (sum(min(abs(x - y) for y in start) for x in v) if start else 0.0), None)
            for v, _ in layers[0]]
    back = [prev]
    for i in range(1, len(layers)):
        cur = []
        for v, f in layers[i]:
            best = None
            for j, (u, g) in enumerate(layers[i - 1]):
                cost = back[-1][j][0] + edge_cost(u, g, v, f, chs[i - 1], chs[i])
                if best is None or cost < best[0] - 1e-9:
                    best = (cost, j)
            cur.append((best[0] + node_cost(v), best[1]))
        back.append(cur)
    j = min(range(len(back[-1])), key=lambda k: back[-1][k][0])
    out = []
    for i in range(len(layers) - 1, -1, -1):
        out.append(list(layers[i][j][0]))
        j = back[i][j][1] if back[i][j][1] is not None else 0
    return out[::-1]


def check_voicing(ch, pitches, rootless_ok: bool = True) -> list[str]:
    """Problems of a voicing against its chord symbol ([] = fine): a pitch that is neither a chord tone nor an
    available tension (see available_tensions), a missing 3rd (or sus 4th) or 7th / 6th, low-interval mud, and - if
    rootless_ok is False - a missing root."""
    c = Chord.parse(ch)
    ps = [note(p) for p in pitches]
    pcs = {p % 12 for p in ps}
    tones = {(c.root + i) % 12 for i in c.intervals}
    g3, g7 = guide_tones(c)
    ok = tones | {(c.root + t) % 12 for t in available_tensions(c)} | {g3} | ({g7} if g7 is not None else set())
    probs = []
    for p in ps:
        if p % 12 not in ok:
            probs.append(f"{note_name(p, flats=True)} is not a chord tone or available tension of {c.symbol}")
    if g3 not in pcs and chord_kind(c) != 'power':
        probs.append(f"missing the {'4th' if chord_kind(c) == 'sus' else '3rd'} ({FLATS[g3]}) of {c.symbol}")
    if g7 is not None and g7 not in pcs and len(ps) >= 3:
        probs.append(f"missing the 7th/6th ({FLATS[g7]}) of {c.symbol}")
    if not rootless_ok and c.root not in pcs:
        probs.append(f"missing the root ({FLATS[c.root]}) of {c.symbol}")
    for a, b in mud(ps):
        probs.append(f"{note_name(a, flats=True)}-{note_name(b, flats=True)} is muddy (below its low interval limit)")
    return probs


# ----------------------------------------------------------------------------------------- key

_KEY_RE = re.compile(r'^\s*([A-Ga-g])([#b♯♭]?)\s*(.*?)\s*$')
_MAJOR = SCALES['major']
_ROMAN_RE = re.compile(r'^([b#♭♯]*)(VII|VI|IV|V|III|II|I|vii|vi|iv|v|iii|ii|i)(.*)$')
_ROMAN_VAL = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7}


def is_roman(sym: str) -> bool:
    return isinstance(sym, str) and bool(_ROMAN_RE.match(sym.strip()))


class Key:
    """A tonic + scale/mode: Key('A minor'), Key('Am'), Key('F# dorian'), Key('Eb'), Key('C', 'lydian').

    key.degree(5) -> MIDI of the 5th degree in octave 4; key.chord('iv7'); key.prog('i VI III VII')."""

    def __init__(self, spec='C major', mode: str | None = None):
        if isinstance(spec, Key):
            self.tonic, self.tonic_name, self.mode = spec.tonic, spec.tonic_name, spec.mode
            self.intervals = spec.intervals
            return
        m = _KEY_RE.match(str(spec)) if isinstance(spec, str) else None
        if not m:
            raise ComposeError(f"can't parse key {spec!r}; use e.g. 'A minor', 'Am', 'F# dorian', 'Eb major'")
        letter, acc, rest = m.groups()
        self.tonic_name = letter.upper() + acc
        self.tonic = pc(self.tonic_name)
        if mode is None:
            mode = {'': 'major', 'm': 'minor', 'M': 'major', '-': 'minor'}.get(rest, rest)
        try:
            self.mode = _scale_name(mode)
        except ComposeError:
            raise ComposeError(f"unknown mode {mode!r} in key {spec!r}; known: {', '.join(SCALES)}") from None
        self.intervals = SCALES[self.mode]

    # --- identity
    @property
    def name(self) -> str:
        return f"{self.tonic_name} {self.mode.replace('_', ' ')}"

    def __repr__(self) -> str:
        return f"Key({self.name!r})"

    def __eq__(self, other) -> bool:
        return isinstance(other, Key) and (self.tonic, self.intervals) == (other.tonic, other.intervals)

    def __hash__(self) -> int:
        return hash((self.tonic, self.intervals))

    @property
    def minorish(self) -> bool:
        return 3 in self.intervals and 4 not in self.intervals

    @property
    def pcs(self) -> frozenset[int]:
        return frozenset((self.tonic + i) % 12 for i in self.intervals)

    @property
    def heptatonic(self) -> tuple[int, ...]:
        """Seven-note scale used for roman numerals (pentatonic/blues keys use their parent mode)."""
        return self.intervals if len(self.intervals) == 7 else SCALES[_PARENT.get(self.mode, 'major')]

    # --- pitches
    def step(self, s: int, octave: int = 4) -> int:
        """MIDI pitch of 0-based scale step `s` counted from the tonic in `octave` (s may be negative)."""
        n = len(self.intervals)
        o, i = divmod(int(s), n)
        return (octave + 1 + o) * 12 + self.tonic + self.intervals[i]

    def degree(self, d: int, octave: int = 4, alter: int = 0) -> int:
        """MIDI pitch of 1-based scale degree `d` (1 = tonic in `octave`, 8 = octave above, -1 = step below)."""
        return self.step(_degree_to_step(d), octave) + alter

    def step_of(self, pitch: int, octave: int = 4) -> tuple[int, int]:
        """(step, alteration) such that step(step, octave) + alteration == pitch; alteration >= 0."""
        rel = note(pitch) - ((octave + 1) * 12 + self.tonic)
        o, r = divmod(rel, 12)
        i = max(k for k, iv in enumerate(self.intervals) if iv <= r)
        return o * len(self.intervals) + i, r - self.intervals[i]

    def contains(self, pitch) -> bool:
        return note(pitch) % 12 in self.pcs

    def snap(self, pitch, direction: int = 0) -> int:
        """Nearest scale pitch (direction -1: at or below, +1: at or above, 0: nearest, ties go down)."""
        p = note(pitch)
        for d in range(12):
            for cand in ((p - d, p + d) if direction == 0 else ((p + d,) if direction > 0 else (p - d,))):
                if cand % 12 in self.pcs:
                    return cand
        return p

    def spell(self, p: int, hint: str = '') -> str:
        """Name of pitch class p in this key: diatonic notes follow the key signature,
        chromatic ones follow `hint` ('b' -> flat, '#' -> sharp) or the signature."""
        p %= 12
        if p in (0, 2, 4, 5, 7, 9, 11) and (p in self.pcs or not hint):
            return SHARPS[p]
        if hint:
            flat = hint[0] in 'b♭'
        else:
            offs = {'major': 0, 'dorian': 2, 'phrygian': 4, 'lydian': 5, 'mixolydian': 7, 'minor': 9,
                    'locrian': 11, 'harmonic_minor': 9, 'melodic_minor': 9}
            rel = (self.tonic - offs.get(self.mode, 9 if self.minorish else 0)) % 12
            if '#' in self.tonic_name or '♯' in self.tonic_name:
                flat = False                     # C# major, F# minor ... are sharp keys
            elif 'b' in self.tonic_name or '♭' in self.tonic_name:
                flat = True
            else:
                flat = rel in (5, 10, 3, 8, 1) or (rel == 0 and p not in self.pcs)
        return (FLATS if flat else SHARPS)[p]

    def transpose(self, pitch, steps: int) -> int:
        """Move a pitch by `steps` scale steps, keeping any chromatic alteration."""
        s, a = self.step_of(pitch)
        return self.step(s + int(steps)) + a

    def notes(self, low='C3', high='C6') -> list[int]:
        """All scale pitches in [low, high]."""
        lo, hi = note(low), note(high)
        return [p for p in range(lo, hi + 1) if p % 12 in self.pcs]

    # --- harmony
    def triad(self, degree: int, size: int = 3) -> Chord:
        """Diatonic chord built by stacking scale thirds on a degree (size 3 triad, 4 seventh, 5 ninth)."""
        sc = self.heptatonic
        s0 = _degree_to_step(degree)
        pitches = [_step_in(sc, s0 + 2 * k) for k in range(size)]
        root = pitches[0]
        ivs = tuple(sorted(p - root for p in pitches))
        r = (self.tonic + root) % 12
        sym = _name_intervals(ivs)
        ch = Chord.parse(self.spell(r) + sym) if sym is not None else None
        if ch is None or set(ch.intervals) != set(ivs):
            return Chord(r, ivs, None, '?', self.spell(r), None)
        return ch

    def chord(self, numeral) -> Chord:
        """Chord for a roman numeral in this key, or a plain chord symbol.

        Case gives the quality (V major, v minor); suffixes: ° dim, ø half-dim, + aug, then any chord
        extension (7, maj7, 9, sus4, add9, b9 ...). Plain numerals use this key's own scale degrees
        (in A minor: VI = F, VII = G), except that a diminished / half-diminished vii is always the
        leading-tone chord (vii°7 in A minor = G#dim7); an explicit b/# is relative to the MAJOR scale
        of the tonic (bVII in C major = Bb; bVI in A minor = F). Secondary chords: V7/V, vii°/ii."""
        if isinstance(numeral, Chord):
            return numeral
        s = str(numeral).strip()
        m = _ROMAN_RE.match(s)
        if not m:
            return Chord.parse(s)
        acc, num, rest = m.groups()
        target = None
        if '/' in rest:
            q, _, of = rest.rpartition('/')
            if is_roman(of):
                target, rest = of, q
        if target is not None:
            t = self.chord(target)
            sub = Key(t.root_name or _spell(t.root), 'minor' if t.is_minor else 'major')
            return sub.chord(acc + num + rest)
        deg = _ROMAN_VAL[num.lower()]
        if acc:
            root = self.tonic + _MAJOR[deg - 1] + sum(_ACCIDENTAL[c] for c in acc)
        else:
            root = self.tonic + self.heptatonic[deg - 1]
        root %= 12
        q = rest
        if num.islower() and re.match(r'^(m(?!aj)|min|-)', q):
            q = re.sub(r'^(min|m|-)', '', q, count=1)   # 'iim7', 'ivm7', 'im(maj7)': the case already says minor
        if q.startswith(('°', 'dim')) or (q.startswith('o') and not q.startswith('omit')):
            q = q[3:] if q.startswith('dim') else q[1:]
            base = 'dim7' if q.startswith('7') else 'dim'
            q = q[1:] if q.startswith('7') else q
        elif q.startswith('ø'):
            q = q[1:]
            q = q[1:] if q.startswith('7') else q
            base = 'm7b5'
        elif q.startswith(('+', 'aug')):
            q = q[3:] if q.startswith('aug') else q[1:]
            base = 'aug'
        else:
            base = 'm' if num.islower() else ''
        try:
            ch = Chord.parse(self.spell(root, acc) + base + q)
            # A diminished / half-diminished chord on a plain 7th degree is the leading-tone chord:
            # vii° / vii°7 / viiø7 in A minor (or dorian, mixolydian) = G#, not the subtonic G.
            if (deg == 7 and not acc and (self.heptatonic[6] == 10)
                    and 3 in ch.intervals and 6 in ch.intervals and 7 not in ch.intervals):
                root = (root + 1) % 12
                ch = Chord.parse(self.spell(root, '#') + base + q)
            return ch
        except ComposeError:
            raise ComposeError(f"can't parse roman numeral {numeral!r} (in {self.name}): suffix {rest!r} "
                               f"is not a chord extension; e.g. 'V7', 'iv7', 'bVIImaj7', 'ii°', 'V7/V'") from None

    def chords(self, seventh: bool = False) -> list[Chord]:
        """The diatonic chords on degrees 1..7 (triads, or sevenths with seventh=True)."""
        return [self.triad(d, 4 if seventh else 3) for d in range(1, 8)]

    def prog(self, spec, bars: float = 1, beats_per_bar: float = 4) -> 'Progression':
        """Progression in this key: key.prog('i VI III VII') or key.prog('i:2 iv:2 V7'). Lengths are bars."""
        return Progression(spec, key=self, bars=bars, beats_per_bar=beats_per_bar)

    def motif(self, spec, dur=0.5):
        """Motif (degree melody) in this key, see patterns.Motif."""
        from .patterns import Motif
        return Motif(spec, self, dur=dur)


def _degree_to_step(d) -> int:
    if not _is_int(d):
        raise ComposeError(f"scale degree must be an int, got {d!r}")
    if d == 0:
        raise ComposeError("scale degree 0 does not exist: degrees are 1-based (1 = tonic, 8 = octave up, "
                           "-1 = the scale note just below the tonic)")
    return d - 1 if d > 0 else d


def _step_in(sc: tuple[int, ...], s: int) -> int:
    o, i = divmod(s, len(sc))
    return o * 12 + sc[i]


def _name_intervals(ivs: tuple[int, ...]) -> str | None:
    table = {
        (0, 4, 7): '', (0, 3, 7): 'm', (0, 3, 6): 'dim', (0, 4, 8): 'aug',
        (0, 4, 7, 11): 'maj7', (0, 3, 7, 10): 'm7', (0, 4, 7, 10): '7', (0, 3, 6, 10): 'm7b5',
        (0, 3, 6, 9): 'dim7', (0, 3, 7, 11): 'mMaj7', (0, 4, 8, 11): 'augmaj7', (0, 4, 8, 10): 'aug7',
        (0, 4, 7, 11, 14): 'maj9', (0, 3, 7, 10, 14): 'm9', (0, 4, 7, 10, 14): '9',
        (0, 3, 7, 10, 13): 'm7b9', (0, 4, 7, 10, 13): '7b9', (0, 3, 6, 10, 13): 'm7b5b9',
        (0, 3, 6, 10, 14): 'm7b5add9', (0, 4, 7, 11, 18): 'maj7#11', (0, 3, 7, 11, 14): 'mMaj9',
        (0, 4, 8, 11, 14): 'augmaj9', (0, 3, 6, 9, 14): 'dim7add9',
    }
    return table.get(ivs)


# --------------------------------------------------------------------------------- progression

class Progression:
    """A sequence of chords with lengths. Chord lengths are in BARS (everything else is in beats).

        Progression('Am F C G')                      # one bar each
        key.prog('i VI III VII')                     # roman numerals need a key
        key.prog('i:2 VI:2 III VII | iv:0.5 V7:1.5')  # ':n' = n bars; '|' is ignored
        Progression('Am % F G')                      # '%' extends the previous chord one bar; 'r'/'NC' = no chord
        Progression([('Am', 2), 'F', key.chord('V7')], key=key)

    Turn it into notes with .block() / .arp() / .bass(), or play it directly on a track."""

    def __init__(self, spec, key=None, bars: float = 1, beats_per_bar: float = 4):
        self.key = None if key is None else Key(key)
        self.beats_per_bar = float(beats_per_bar)
        if self.beats_per_bar <= 0:
            raise ComposeError(f"beats_per_bar must be > 0, got {beats_per_bar}")
        self.items: list[tuple[Chord | None, float]] = []
        if isinstance(spec, Progression):
            self.items = list(spec.items)
            self.key = self.key or spec.key
            return
        if isinstance(spec, str):
            tokens = [t.rstrip(',') for t in spec.replace('|', ' ').split()]
        elif isinstance(spec, (Chord,)):
            tokens = [spec]
        else:
            tokens = list(spec)
        for tok in tokens:
            if tok == '':
                continue
            self._add(tok, bars)
        if not self.items:
            raise ComposeError(f"empty progression: {spec!r}")

    def _add(self, tok, default_bars) -> None:
        n_bars = default_bars
        if isinstance(tok, tuple):
            if len(tok) != 2:
                raise ComposeError(f"progression item {tok!r} must be (chord, bars)")
            tok, n_bars = tok
        elif isinstance(tok, str) and ':' in tok:
            tok, _, b = tok.rpartition(':')
            try:
                n_bars = float(b)
            except ValueError:
                raise ComposeError(f"bad chord length in {tok + ':' + b!r}: ':{b}' must be a number of bars") from None
        if not isinstance(n_bars, (int, float)) or isinstance(n_bars, bool) or n_bars <= 0:
            raise ComposeError(f"chord length must be a positive number of bars, got {n_bars!r}")
        beats = float(n_bars) * self.beats_per_bar
        if isinstance(tok, str) and tok.strip() in ('%', '-'):
            if not self.items:
                raise ComposeError("'%' (repeat previous chord) can't start a progression")
            c, d = self.items[-1]
            self.items[-1] = (c, d + beats)
            return
        if isinstance(tok, str) and tok.strip().lower() in ('r', 'nc', 'n.c.', 'rest'):
            self.items.append((None, beats))
            return
        self.items.append((self._chord(tok), beats))

    def _chord(self, tok) -> Chord:
        if isinstance(tok, Chord):
            return tok
        if not isinstance(tok, str):
            raise ComposeError(f"progression item {tok!r} is not a chord symbol / roman numeral / Chord")
        if is_roman(tok):
            if self.key is None:
                raise ComposeError(f"roman numeral {tok!r} needs a key: use key.prog(...), song.prog(...) "
                                   f"or Progression(..., key='A minor')")
            return self.key.chord(tok)
        return Chord.parse(tok)

    @classmethod
    def _from(cls, items, key, bpb) -> 'Progression':
        p = cls.__new__(cls)
        p.items, p.key, p.beats_per_bar = list(items), key, bpb
        return p

    # --- queries
    @property
    def length(self) -> float:
        """Total length in beats."""
        return sum(d for _, d in self.items)

    @property
    def chords(self) -> list[Chord | None]:
        return [c for c, _ in self.items]

    def __iter__(self):
        """Yields (start_beat, dur_beats, chord_or_None)."""
        t = 0.0
        for c, d in self.items:
            yield t, d, c
            t += d

    def __len__(self) -> int:
        return len(self.items)

    def __repr__(self) -> str:
        body = ' '.join((c.symbol if c else 'NC') + (f':{d / self.beats_per_bar:g}' if d != self.beats_per_bar else '')
                        for c, d in self.items)
        return f"Progression('{body}')"

    def at(self, beat: float) -> Chord | None:
        """Chord sounding at `beat` (wraps around the progression length)."""
        b = beat % self.length if self.length else 0.0
        for s, d, c in self:
            if s <= b + 1e-9 < s + d:
                return c
        return self.items[-1][0]

    # --- transforms
    def __add__(self, other: 'Progression') -> 'Progression':
        return Progression._from(self.items + Progression(other, key=self.key, beats_per_bar=self.beats_per_bar).items,
                                 self.key, self.beats_per_bar)

    def __mul__(self, n: int) -> 'Progression':
        return Progression._from(self.items * int(n), self.key, self.beats_per_bar)

    __rmul__ = __mul__

    def transpose(self, semitones: int) -> 'Progression':
        return Progression._from([(None if c is None else c.transpose(semitones), d) for c, d in self.items],
                                 self.key, self.beats_per_bar)

    def stretch(self, factor: float) -> 'Progression':
        return Progression._from([(c, d * factor) for c, d in self.items], self.key, self.beats_per_bar)

    # --- voicing
    def voiced(self, voicing: str = 'smooth', register=(52, 76), voices: int | None = 4, bass: bool = False,
               octave: int = 4, inversion: int = 0) -> list[tuple[float, float, list[int]]]:
        """[(start, dur, pitches)] for every chord (rests skipped). voicing='smooth' voice-leads."""
        segs = [(s, d, c) for s, d, c in self if c is not None]
        if voicing == 'smooth':
            vs = voice_lead([c for _, _, c in segs], register=register, voices=voices, bass=bass)
        elif voicing in JAZZ_VOICINGS:
            vs = jazz_voicings([c for _, _, c in segs], voicing, register=register, voices=voices)
            if bass:
                vs = [[_bass_below(c.bass_pc, min(v))] + v for (_, _, c), v in zip(segs, vs)]
        else:
            vs = [voice(c, voicing, octave=octave, inversion=inversion, voices=voices, register=register, bass=bass)
                  for _, _, c in segs]
        return [(s, d, v) for (s, d, _), v in zip(segs, vs)]

    def roots(self, low='E1') -> list[tuple[float, float, int]]:
        """[(start, dur, bass_pitch)]: slash bass or root of each chord in the octave from `low`."""
        return [(s, d, c.bass_note(low)) for s, d, c in self if c is not None]

    # --- note generators (see patterns.py for all options)
    def block(self, **kw):
        """Block chords as a Clip: patterns.chords(self, **kw)."""
        from .patterns import chords
        return chords(self, **kw)

    def arp(self, mode: str = 'up', **kw):
        """Arpeggio Clip: patterns.arp(self, mode, **kw)."""
        from .patterns import arp
        return arp(self, mode, **kw)

    def bass(self, style: str = 'octave', **kw):
        """Bassline Clip: patterns.bassline(self, style, **kw)."""
        from .patterns import bassline
        return bassline(self, style, **kw)


PROGRESSIONS = {
    'synthwave': 'i VI III VII',
    'nightdrive': 'i VI VII i',
    'outrun': 'vi IV I V',
    'heroic': 'I V vi IV',
    'andalusian': 'i VII VI V',
    'epic': 'i VI VII v',
    'lament': 'i v VI III iv i iv V',
    'dorian_vamp': 'i IV',
    'lydian_float': 'I II',
    'mixo_rock': 'I bVII IV I',
    'sad_pop': 'vi IV I V',
    'jazz_turnaround': 'ii7 V7 Imaj7 VI7',
}
"""Common progressions as roman numerals (use with key.prog(PROGRESSIONS['synthwave']))."""
