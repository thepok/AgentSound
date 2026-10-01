"""Notation: one compact, expressive text format for note data - melodies, bass lines, chords, voices, drum lines.

    lead.play(notes("vel=92 C5/8 Eb5 G5/4. F5/8 | Eb5/2 C5/4 r"), verse)
    H = phrases(a1='5:1/8 8 r 10 12:1/4.! 10:1/8', a2='11:1/4. 10:1/8 9:1/2', key='F# minor', gate=0.92)
    hook.play(H('a1 a2 a1+2d a2'), chorus)
    print(notation.format(lead))                 # any clip / track back to notation (it parses back exactly)

Compactness comes only from what can be computed: start times follow from the durations, durations and octaves
are sticky, repeats and named phrases are written once. Every per-note detail stays writable (=96 a velocity,
:0.45 a sounding length, @12.5 an exact position, ^staccato an articulation, ^gl(90) a glide); settings are
defaults a token overrides. Clips, tuples and Motifs keep working everywhere - notes() returns a Clip (a Line).

GRAMMAR (whitespace separates tokens; '%' starts a comment to the end of the line)

  pitch      C4 C#4 Db4 Fb4 B#3 Cbb5     absolute (letters A-G upper case; C4 = 60)
             C D E                        no octave: relative - the octave nearest the previous letter note (at
                                          most a 4th away, LilyPond's rule); the first one near C<oct>
             C5' C,                       ' an octave up, , an octave down (repeatable; on degrees too)
             1 3 5 8 b3 #4 -1 9           scale degrees of key= (Motif's: 1 = the tonic in octave oct=, 8 an
                                          octave up, -1 the scale note below the tonic; b / # alter)
             kick snare hat ...           drum names (patterns.DRUMS)
  duration   C5/8 C5/4. C5/16t C5/2..     note values: /N a 1/N note, '.' dotted, '..' double dotted, 't' triplet
             C5:1/8 C5:3/8 C5:1.5         ':' + a note value a/b or a number of unit= (beats by default)
             C5/8:0.45  C5:0.5:0.45       a second ':' = the sounding length only (the note still advances by
                                          the first value): a written 8th sounding 0.45 beats
                                          durations are sticky: a token without one takes the last one (dur=)
  rest       r r/4 . - r:2                '.' and '-' too: a grid line '. C#2 C#2 _ . C#2' (dur=1/16)
  tie, hold  C5/2~ C5/8   C5/2 _/8        '~' ties into the next note of that pitch (across bar lines); '_'
                                          holds the previous note / chord on (after a rest: a longer rest)
  chord      [C4 Eb4 G4]/2                notes together; the chord's duration is the advance, an inner note's
             [C2:4 G3 C4]/4               own duration is its sounding length (the C2 rings 4 beats);
             [C4 E4 G4]/1:3.9             a second ':' after the chord: the sounding length of all its notes
  tuplet     {C5 D5 E5}/4                 the group squeezed into the span: triplets, {C5 D5 E5 F5 G5}/2
             3:2{C5/8 D5 E5}              quintuplets, any free-time figure; p:q = p notes in the time of q
  slur       (C5 D5 E5 F5)                legato: each note held into the next (articulation.legato, overlap
             (C5 D5 E5)^gl(80)            slur=); ^gl after it glides into every note after the first
  grace      g:D5 E5/4  g:(B4 C5 Db5) C5  written grace notes, grace= beats each, just before the note (taken
                                          from the note before), at gracevel= x the velocity
  velocity   C5! C5!! C5? C5=96           accent (x accent=), ghost (x ghost=), an exact velocity
             pp p mp mf f ff ppp fff      dynamics from here on: x romantic.LEVELS of the base vel= (mf = 1.0)
             < ... f   > ... p            hairpins: from where they stand to the next dynamic mark (curve=)
             sf sfz fp sfp  subito        sf / sfz: the next note x sfz=; fp / sfp: it at f, then p; subito: the
                                          next mark is a step (never a hairpin's target)
  marks      C5^staccato C5^pizz          articulation marks (articulation.py: keyswitches on a sampler; any
             C5^"Short Spiccato" C5^ks(24) word that is not reserved below, a quoted label, a keyswitch key)
             C5^gl C5^gl(90)              glide (portamento) into the note, ms
             C5^peak                      a phrase peak: line.peaks (hornist.arrange(peaks=), heroes)
  ornaments  C5/2^tr ^tr(upper) ^turn ^turn(on) ^mord ^mord(upper) ^crush ^crush(-2)
             [C4 E4 G4]^roll ^roll(60, down) ^strum(30)   {Bb5 Ab5 G5 F5 D5}/2^fig(rit)
                                          romantic.trill / turn / fioritura, pianist.mordent / crush / roll,
                                          midifx.strum - played in real time, so they need bpm= (a number, or
                                          s.tempo_at with at= the line's position); keywords pass through:
                                          ^tr(start=upper, rate=14)
  gestures   C5/2^scoop ^scoop(-50) ^fall ^fall(-5) ^doit ^bend(2) ^vib ^vib(30) ^shake
                                          agentsound.gesture pitch moves: track.play() writes them on
                                          'instrument.pitchbend' (vibrato: the sampler's own vibrato) at the
                                          song's tempo where the line lands
  repeats    C5/16*4  [C4 E4]/8*3  |: C5 D5 E5 F5 :|  :|x3     an event N times; a passage twice / N times
  bars       |                            a check: each bar line must fall on a bar boundary of meter= (counted
                                          from beat 0; pickup= beats come before it) - the error names the bar
  position   @12.5                        go to beat 12.5 of the line (exact; format()'s escape hatch)
  voices     S: C5/2 D5 | A: E4/2 F4      voice labels: each voice has its own time, bar checks and dynamics;
                                          line.voices['S'] (notes({'S': ..., 'A': ...}) does the same)
  settings   vel=90 dur=1/8 gate=0.9 gap=0.1 unit=1/8 oct=5 key=F#m meter=3/4 accent=1.1 ghost=0.72
             grace=0.1 gracevel=0.72 tr=+12 st=-2 slur=0.03 curve=linear sticky=0 sfz=1.3
                                          from here on (they are also keyword arguments of notes())
  phrases    $name (refs=)                a named phrase spliced in; in the line given to H(...) of phrases(): bare
                                          names (they win over notation words there; inside a phrase's own spec only
                                          $name refers), name+12 / name-5 (semitones), name+2d (scale steps),
                                          name' / name, (octaves), name*2
"""

from __future__ import annotations

import math
import re
from fractions import Fraction

from . import articulation as _art
from .patterns import DRUMS, Clip, Note, _vel, as_clip
from .theory import ComposeError, Key, _degree_to_step, note_name

__all__ = ['notes', 'phrases', 'Line', 'Phrases', 'format', 'hold', 'realize', 'parse_tree']

DYNAMICS = ('ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff')
ONE_SHOT = ('sf', 'sfz', 'fp', 'sfp')
ORNAMENTS = ('tr', 'trill', 'turn', 'mord', 'mordent', 'prall', 'crush', 'roll', 'strum', 'fig')
GESTURES = ('scoop', 'fall', 'doit', 'bend', 'vib', 'shake')
RESERVED = ORNAMENTS + GESTURES + ('gl', 'glide', 'peak', 'ks', 'art')
"""Mark names with a meaning of their own; any other ^word is an articulation label (^"..." always is one)."""

_DEFAULTS = dict(vel=96.0, dur=Fraction(1, 2), gate=1.0, gap=0.0, unit=Fraction(1), oct=4, key=None, accent=1.2,
                 ghost=0.65, grace=0.1, gracevel=0.72, tr=0, st=0, slur=0.03, curve='smooth', sticky=True,
                 meter=(4, 4), sfz=1.3)
SETTINGS = tuple(_DEFAULTS)

_NUM = r'(?:\d+(?:\.\d*)?|\.\d+)(?:e-?\d+)?'
_VALUE_RE = re.compile(rf'^(?:/(\d+)(\.{{0,2}})(t?)|:(?:(\d+)/(\d+)(\.{{0,2}})(t?)|({_NUM})))')
_LETTER_RE = re.compile(r'^([A-G])(##|#|bb|b)?(-?\d+)?')
_DEGREE_RE = re.compile(r'^(##|#|bb|b)?(-?\d+)')
_DRUM_RE = re.compile(r'^([a-z][a-z_]*)')
_SETTING_RE = re.compile(r'^([a-z]+)=(.+)$')
_VOICE_RE = re.compile(r'^([A-Za-z][A-Za-z0-9_]*):$')
_REF_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)((?:[+-]\d+d?|['’,])*)(?:\*(\d+))?$")
_LETTERS = 'CDEFGAB'
_LETTER_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
_ACC = {None: 0, '': 0, '#': 1, '##': 2, 'b': -1, 'bb': -2}


class _Tok:
    __slots__ = ('text', 'line')

    def __init__(self, text: str, line: int):
        self.text, self.line = text, line

    def __repr__(self) -> str:
        return f"_Tok({self.text!r})"


def _err(msg: str, tok=None) -> ComposeError:
    where = f" (at {tok.text!r}, line {tok.line})" if isinstance(tok, _Tok) else ''
    return ComposeError(f"notation: {msg}{where}")


# ================================================================================================ tokenizer

class _Group:
    """A bracketed group: kind '[' chord, '{' tuplet, '(' slur, 'g' grace, '|:' repeat (prefix = times)."""
    __slots__ = ('kind', 'prefix', 'items', 'suffix', 'tok')

    def __init__(self, kind, prefix, items, suffix, tok):
        self.kind, self.prefix, self.items, self.suffix, self.tok = kind, prefix, items, suffix, tok


def _scan(text: str) -> list:
    """Characters -> a flat list of _Tok and ('open', kind, prefix, tok) / ('close', kind, suffix, tok)."""
    out: list = []
    i, n, line = 0, len(text), 1
    buf, start_line = '', 1

    def flush():
        nonlocal buf
        if buf:
            out.append(_Tok(buf, start_line))
            buf = ''

    def upto(j: int, ch: str) -> int:
        k = text.find(ch, j + 1)
        if k < 0:
            raise _err(f"unclosed {text[j]!r} in line {line}")
        return k

    def read_suffix(j: int) -> tuple[str, int]:
        """The duration / modifiers glued to a closing bracket (up to whitespace; quotes and (...) kept)."""
        s = ''
        while j < n and not text[j].isspace() and text[j] not in '[]{})':
            if text[j] == '"' or (text[j] == '(' and s.rsplit('^', 1)[-1].isidentifier()):
                k = upto(j, '"' if text[j] == '"' else ')')
                s += text[j:k + 1]
                j = k + 1
                continue
            s += text[j]
            j += 1
        return s, j

    while i < n:
        c = text[i]
        if c == '%':
            while i < n and text[i] != '\n':
                i += 1
            continue
        if c.isspace():
            flush()
            if c == '\n':
                line += 1
            i += 1
            continue
        if not buf:
            start_line = line
        if c == '"':
            k = upto(i, '"')
            buf += text[i:k + 1]
            i = k + 1
            continue
        if c == '(' and buf and buf != 'g:':                   # ^mark(args) / name=(...) belong to the token
            k = upto(i, ')')
            buf += text[i:k + 1]
            i = k + 1
            continue
        if c in '[{(':
            prefix = buf
            if prefix and not (c == '{' and re.match(r'^\d+:\d+$', prefix)) and not (c == '(' and prefix == 'g:'):
                raise _err(f"{prefix!r} directly before {c!r} in line {line}: separate them with a space (only "
                           f"p:q{{...}} tuplets and g:(...) grace groups take a prefix)")
            buf = ''
            out.append(('open', 'g' if prefix == 'g:' else c, prefix, _Tok(prefix + c, line)))
            i += 1
            continue
        if c in ']})':
            flush()
            suffix, j = read_suffix(i + 1)
            out.append(('close', {']': '[', '}': '{', ')': '('}[c], suffix, _Tok(c + suffix, line)))
            i = j
            continue
        buf += c
        i += 1
    flush()
    return out


def _tree(flat: list) -> list:
    """Nest the scanned markers into _Group objects; repeats |: ... :| become groups too."""
    stack: list = [['root', None, [], None]]
    for x in flat:
        if isinstance(x, tuple) and x[0] == 'open':
            stack.append([x[1], x[2], [], x[3]])
            continue
        if isinstance(x, tuple) and x[0] == 'close':
            top = stack[-1]
            want = x[1]
            if len(stack) == 1 or not (top[0] == want or (top[0] == 'g' and want == '(')):
                what = 'nothing' if len(stack) == 1 else (
                    'an open repeat |:' if top[0] == '|:' else f"a {top[0]!r} group")
                raise _err(f"{x[3].text[0]!r} closes {what}", x[3])
            stack.pop()
            stack[-1][2].append(_Group(top[0], top[1], top[2], x[2], top[3]))
            continue
        t = x.text
        if t == '|:':
            stack.append(['|:', None, [], x])
            continue
        m = re.match(r'^:\|(?:x(\d+))?$', t)
        if m:
            top = stack[-1]
            if top[0] != '|:':
                raise _err("':|' without a matching '|:'", x)
            times = int(m.group(1) or 2)
            if times < 1:
                raise _err("a repeat plays x1 or more", x)
            stack.pop()
            stack[-1][2].append(_Group('|:', times, top[2], '', top[3]))
            continue
        stack[-1][2].append(x)
    if len(stack) > 1:
        kind, _, _, tok = stack[-1]
        raise _err("unclosed repeat |:" if kind == '|:' else f"unclosed {kind!r} group", tok)
    return stack[0][2]


def parse_tree(text: str) -> list:
    """The notation's token tree (raises on bracket / quote errors)."""
    if not isinstance(text, str):
        raise ComposeError(f"notation must be a string, got {type(text).__name__}")
    return _tree(_scan(text))


# ================================================================================================ values

def _value(m, unit: Fraction) -> Fraction:
    """A match of _VALUE_RE -> beats."""
    if m.group(1) is not None:                          # /N
        n = int(m.group(1))
        if n <= 0:
            raise ComposeError("a note value /0 does not exist")
        v = Fraction(4, n)
        dots, trip = m.group(2), m.group(3)
    elif m.group(4) is not None:                        # :a/b
        if int(m.group(5)) <= 0:
            raise ComposeError("a note value a/0 does not exist")
        v = Fraction(4 * int(m.group(4)), int(m.group(5)))
        dots, trip = m.group(6), m.group(7)
    else:                                               # :number of units
        return Fraction(m.group(8)) * unit
    v *= {'': 1, '.': Fraction(3, 2), '..': Fraction(7, 4)}[dots]
    if trip:
        v *= Fraction(2, 3)
    return v


def _duration(v, what: str) -> Fraction:
    """A duration given in Python: beats (number), a note value ('1/8', '1/8.', '1/8t', '/8') or a Fraction."""
    if isinstance(v, Fraction):
        return v
    if isinstance(v, bool):
        raise ComposeError(f"{what}: not a duration: {v!r}")
    if isinstance(v, (int, float)):
        if not math.isfinite(v) or v < 0:
            raise ComposeError(f"{what}: a duration must be a finite number >= 0, got {v!r}")
        return Fraction(repr(float(v)))
    if isinstance(v, str):
        s = v.strip()
        s2 = s if s[:1] in '/:' else ':' + s
        m = _VALUE_RE.match(s2)
        if m and m.end() == len(s2):
            return _value(m, Fraction(1))
    raise ComposeError(f"{what}: not a duration: {v!r} (beats like 0.5, or a note value '1/8', '/8.', '1/8t')")


def _setting_value(name: str, raw: str, tok=None):
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] == '"':
        v = v[1:-1]
    try:
        if name in ('vel', 'gate', 'gap', 'accent', 'ghost', 'grace', 'gracevel', 'slur', 'sfz'):
            return float(Fraction(v))
        if name in ('oct', 'tr', 'st'):
            return int(v)
        if name in ('dur', 'unit'):
            if name == 'unit' and v == 'meter':
                return 'meter'
            return _duration(v, name)
        if name == 'key':
            return None if v in ('', 'none', 'None') else Key(v.replace('_', ' '))
        if name == 'meter':
            from .tempo import parse_meter
            return parse_meter(v, 'meter')
        if name == 'curve':
            if v not in ('smooth', 'linear'):
                raise ValueError
            return v
        if name == 'sticky':
            if v not in ('0', '1', 'true', 'false', 'True', 'False'):
                raise ValueError
            return v in ('1', 'true', 'True')
    except ComposeError as e:
        raise _err(f"setting {name}={raw}: {e}", tok) from None
    except (ValueError, ZeroDivisionError):
        raise _err(f"setting {name}={raw}: bad value", tok) from None
    raise _err(f"unknown setting {name!r}; settings: {', '.join(SETTINGS)}", tok)


def _meter_beats(meter) -> Fraction:
    return Fraction(4 * meter[0], meter[1])


def _args(text: str, tok=None) -> tuple[list, dict]:
    """'60, down, rate=14' -> ([60, 'down'], {'rate': 14})."""
    pos, kw = [], {}
    if not text.strip():
        return pos, kw
    for part in text.split(','):
        p = part.strip()
        if not p:
            raise _err(f"empty argument in ({text})", tok)
        k = None
        if '=' in p:
            k, _, p = p.partition('=')
            k, p = k.strip(), p.strip()
        if len(p) >= 2 and p[0] == p[-1] == '"':
            v = p[1:-1]
        else:
            try:
                v = int(p)
            except ValueError:
                try:
                    v = float(p)
                except ValueError:
                    v = {'true': True, 'false': False, 'none': None}.get(p.lower(), p)
        if k is None:
            if kw:
                raise _err(f"positional argument {p!r} after keyword arguments in ({text})", tok)
            pos.append(v)
        else:
            kw[k] = v
    return pos, kw


# ================================================================================================ modifiers

class _Mods:
    __slots__ = ('acc', 'ghost', 'vel', 'marks', 'times', 'tie')

    def __init__(self):
        self.acc, self.ghost, self.vel, self.marks, self.times, self.tie = 0, 0, None, [], 1, False

    def empty(self) -> bool:
        return not (self.acc or self.ghost or self.vel is not None or self.marks or self.tie)


_MOD_RE = re.compile(r'^(?:(!)|(\?)|=(\d+)|\*(\d+)|(~)|\^"([^"]*)"|\^([A-Za-z_][A-Za-z0-9_]*|\d+)(?:\(([^)]*)\))?)')


def _mods(s: str, tok) -> _Mods:
    md = _Mods()
    i = 0
    while i < len(s):
        m = _MOD_RE.match(s[i:])
        if not m:
            raise _err(f"can't read {s[i:]!r}: after a pitch and its duration come ! ? =VEL ~ *N ^mark ^mark(args) "
                       f"^\"label\"", tok)
        if m.group(1):
            md.acc += 1
        elif m.group(2):
            md.ghost += 1
        elif m.group(3):
            v = int(m.group(3))
            if not 1 <= v <= 127:
                raise _err(f"velocity ={v} is outside 1..127", tok)
            md.vel = v
        elif m.group(4):
            if int(m.group(4)) < 1:
                raise _err("*N needs N >= 1", tok)
            md.times *= int(m.group(4))
        elif m.group(5):
            md.tie = True
        elif m.group(6) is not None:
            md.marks.append(('art', [m.group(6)], {}))
        else:
            name = m.group(7)
            pos, kw = _args(m.group(8) or '', tok)
            if name.isdigit():
                md.marks.append(('art', [int(name)], {}))
            elif name in RESERVED:
                canon = {'gl': 'glide', 'tr': 'trill', 'mord': 'mordent'}.get(name, name)
                md.marks.append((canon, pos, kw))
            else:
                if m.group(8) is not None:
                    raise _err(f"^{name}(...): an articulation label takes no arguments (ornaments: "
                               f"{', '.join(ORNAMENTS)}; gestures: {', '.join(GESTURES)})", tok)
                md.marks.append(('art', [name], {}))
        i += m.end()
    return md


def _is_rest(t: str) -> bool:
    return t[:1] in ('r', '.', '-', '_') and (len(t) == 1 or t[1] in '/:*~!?=^')


# ================================================================================================ the evaluator

class _Rec:
    """One note while the line is built (start / written in exact beats)."""
    __slots__ = ('start', 'written', 'length', 'pitch', 'base', 'acc', 'vel', 'lvl', 'art', 'glide', 'orn', 'gest',
                 'peak', 'tie', 'gate', 'gap', 'group', 'tok', 'grace', 'voice')

    def __init__(self, start, written, pitch, st, tok, voice):
        self.start, self.written, self.length, self.pitch = start, written, None, pitch
        self.base, self.acc, self.vel, self.lvl = st['vel'], 1.0, None, None
        self.art, self.glide, self.orn, self.gest, self.peak, self.tie = None, None, None, [], False, False
        self.gate, self.gap, self.group, self.tok, self.grace = st['gate'], st['gap'], None, tok, None
        self.voice = voice


class _Voice:
    def __init__(self, name: str, st: dict, start: Fraction, tuplet: bool = False):
        self.name = name
        self.st = dict(st)
        self.t = start
        self.t0 = start
        self.bar0 = Fraction(0)          # the last bar line (bar 1 starts at beat 0)
        self.barno = 1                   # the bar starting at bar0
        self.checked = False             # a bar line was seen
        self.recs: list[_Rec] = []
        self.last: list[_Rec] = []       # the notes the last event started ('_' holds them)
        self.last_rest = False
        self.ref_step = None             # diatonic index of the last letter note (relative octaves)
        self.marks: list = []            # dynamics: (beat, level, step)
        self.hairpin = None              # (beat, '<' | '>', tok)
        self.subito = False
        self.pending = None              # ('sf' | 'sfz' | 'fp' | 'sfp', factor) for the next event
        self.graces: list = []
        self.tuplet = tuplet


class _Ctx:
    def __init__(self, settings: dict, refs, pickup: Fraction, bpm, at: float):
        self.base = settings
        self.refs = refs or {}
        self.pickup = pickup
        self.bpm = bpm
        self.at = at
        self.voices: dict[str, _Voice] = {}
        self.order: list[str] = []
        self.ref_stack: list[str] = []
        self.bare = False                # bare phrase names resolve (phrases(): only in the line given to H(...))
        self.slurs: list[list[_Rec]] = []
        self.expand = True               # notes(expand=False): ornaments listed in line.ornaments, not played

    def voice(self, name: str) -> _Voice:
        v = self.voices.get(name)
        if v is None:
            v = _Voice(name, self.base, -self.pickup)
            self.voices[name] = v
            self.order.append(name)
        return v


def _f(x) -> str:
    return f"{float(x):g}"


def _bar_check(v: _Voice, tok) -> None:
    """A bar line at v.t: it must fall on a bar boundary (bars counted from beat 0 in the meter; a bar line may be
    left out, the next one is checked against the same grid)."""
    if v.tuplet:
        raise _err("a bar line inside a tuplet", tok)
    bpb = _meter_beats(v.st['meter'])
    t = v.t
    meter = f"{v.st['meter'][0]}/{v.st['meter'][1]}"
    if t < v.bar0 or (t == v.bar0 and (v.checked or t == v.t0)):
        if t == 0 and not v.checked and v.t0 < 0:        # the end of the pickup
            v.checked = True
            return
        if t < 0 and v.t0 < 0 and not v.checked:
            raise _err(f"the pickup ends at beat {_f(t)}, not on the downbeat (pickup= is {_f(-v.t0)} beats)", tok)
        raise _err(f"a bar line at beat {_f(t)} with no music since the last one", tok)
    d = t - v.bar0
    k = d // bpb
    rem = d - k * bpb
    if rem:
        if not v.checked and v.t0 >= 0 and k == 0 and v.bar0 == 0:
            raise _err(f"bar 1 holds {_f(rem)} beats, the meter {meter} wants {_f(bpb)} (a pickup? "
                       f"notes(..., pickup={_f(rem)}))", tok)
        if k >= 1 and rem * 2 < bpb:
            raise _err(f"bar {v.barno + int(k) - 1} is {_f(rem)} beats too long (the meter {meter} wants "
                       f"{_f(bpb)})", tok)
        raise _err(f"bar {v.barno + int(k)} holds {_f(rem)} beats at the bar line, the meter {meter} wants "
                   f"{_f(bpb)} ({_f(bpb - rem)} missing)", tok)
    v.barno += int(k)
    v.bar0 = t
    v.checked = True


class _Builder:
    def __init__(self, ctx: _Ctx):
        self.ctx = ctx

    # --- the walk
    def run(self, items: list, v: _Voice, top: bool) -> _Voice:
        for x in items:
            if isinstance(x, _Group):
                self.group(x, v)
                continue
            m = _VOICE_RE.match(x.text)
            if m:
                if not top:
                    raise _err("a voice label belongs at the top level of a line, not inside a group or phrase", x)
                if v.graces:
                    raise _err("grace notes before a voice label lead into nothing", x)
                v = self.ctx.voice(m.group(1))
                continue
            self.word(x, v)
        return v

    def word(self, tok: _Tok, v: _Voice) -> None:
        t = tok.text
        if t == '|':
            _bar_check(v, tok)
            return
        if t.startswith('@'):
            try:
                v.t = Fraction(t[1:])
            except (ValueError, ZeroDivisionError):
                raise _err(f"{t!r}: @ takes a beat number like @12.5", tok) from None
            if v.graces:
                raise _err("grace notes before a jump lead into nothing", tok)
            v.last, v.last_rest = [], False
            return
        if t in DYNAMICS or t in ONE_SHOT or t in ('<', '>', 'subito'):
            self.dynamic(t, v, tok)
            return
        if t.startswith('$'):
            self.ref(t[1:], v, tok)
            return
        m = _SETTING_RE.match(t)
        if m and m.group(1) in SETTINGS:
            name = m.group(1)
            val = _setting_value(name, m.group(2), tok)
            if name == 'unit' and val == 'meter':
                val = Fraction(4, v.st['meter'][1])
            v.st[name] = val
            return
        if m and m.group(1) not in DRUMS:
            raise _err(f"unknown setting {m.group(1)!r}; settings: {', '.join(SETTINGS)}", tok)
        rm = _REF_RE.match(t)
        if self.ctx.bare and rm and rm.group(1) in self.ctx.refs and rm.group(1) not in DRUMS:
            self.ref(t, v, tok)
            return
        self.event(tok, v)

    # --- dynamics
    def dynamic(self, t: str, v: _Voice, tok) -> None:
        from .romantic import LEVELS
        if t in ('<', '>'):
            if v.hairpin is not None:
                raise _err("a hairpin is already open: end it with a dynamic mark first", tok)
            v.marks.append((v.t, self.level_at(v, v.t), True))
            v.hairpin = (v.t, t, tok)
            return
        if t == 'subito':
            v.subito = True
            return
        if t in ONE_SHOT:
            v.pending = (t, v.st['sfz'])
            return
        lv = LEVELS[t]
        if v.hairpin is not None:
            if v.subito:
                raise _err(f"subito {t}: the hairpin from beat {_f(v.hairpin[0])} needs a target mark first", tok)
            h0, kind, _ = v.hairpin
            cur = self.level_at(v, h0)
            if (kind == '<' and lv < cur - 1e-9) or (kind == '>' and lv > cur + 1e-9):
                raise _err(f"the {'crescendo' if kind == '<' else 'diminuendo'} from beat {_f(h0)} ends on {t!r}, "
                           f"which is {'softer' if kind == '<' else 'louder'}", tok)
            v.marks.append((v.t, lv, False))
            v.hairpin = None
        else:
            v.marks.append((v.t, lv, True))
        v.subito = False

    @staticmethod
    def level_at(v: _Voice, b) -> float:
        lv = 1.0
        for t, level, _ in v.marks:
            if t <= b:
                lv = level
        return lv

    # --- named phrases
    def ref(self, text: str, v: _Voice, tok) -> None:
        m = _REF_RE.match(text)
        if not m or m.group(1) not in self.ctx.refs:
            raise _err(f"unknown phrase {text!r} (phrases: {', '.join(sorted(self.ctx.refs)) or 'none'})", tok)
        name = m.group(1)
        if name in self.ctx.ref_stack:
            raise _err(f"phrase {name!r} refers to itself ({' -> '.join(self.ctx.ref_stack + [name])})", tok)
        tr = st = 0
        for part in re.findall(r"[+-]\d+d?|['’,]", m.group(2)):
            if part in ("'", '’'):
                tr += 12
            elif part == ',':
                tr -= 12
            elif part.endswith('d'):
                st += int(part[:-1])
            else:
                tr += int(part)
        items = self.ctx.refs[name]
        items = parse_tree(items) if isinstance(items, str) else items
        self.ctx.ref_stack.append(name)
        bare, self.ctx.bare = self.ctx.bare, False          # inside a phrase only $name refers to another one
        try:
            for _ in range(int(m.group(3) or 1)):
                old = (v.st['tr'], v.st['st'])
                v.st['tr'], v.st['st'] = old[0] + tr, old[1] + st
                try:
                    self.run(items, v, top=False)
                finally:
                    v.st['tr'], v.st['st'] = old
        finally:
            self.ctx.ref_stack.pop()
            self.ctx.bare = bare

    # --- pitches
    def pitch(self, text: str, v: _Voice, tok) -> tuple[int, str]:
        """(MIDI pitch, the rest of the token) of the pitch at the start of `text`."""
        st = v.st
        m = _LETTER_RE.match(text)
        if m:
            letter, acc, octv = m.group(1), m.group(2) or '', m.group(3)
            idx = _LETTERS.index(letter)
            if octv is not None:
                o = int(octv)
            else:
                ref = v.ref_step if v.ref_step is not None else st['oct'] * 7
                o = min(range(-2, 11), key=lambda oo: (abs(oo * 7 + idx - ref), oo))
            rest, shift = self.octave_marks(text[m.end():])
            v.ref_step = (o + shift) * 7 + idx
            p = (o + 1 + shift) * 12 + _LETTER_PC[letter] + _ACC[acc]
            if st['st']:
                p = self.key(v, tok, f"st={st['st']} (scale steps)").transpose(p, st['st'])
            return p + st['tr'], rest
        m = _DEGREE_RE.match(text)
        if m:
            d = int(m.group(2))
            if d == 0:
                raise _err("scale degree 0 does not exist (1 = tonic, 8 = octave, -1 = below the tonic)", tok)
            k = self.key(v, tok, f"degree {text[:m.end()]!r}")
            rest, shift = self.octave_marks(text[m.end():])
            p = k.step(_degree_to_step(d) + st['st'], st['oct'] + shift) + _ACC[m.group(1) or '']
            return p + st['tr'], rest
        m = _DRUM_RE.match(text)
        if m and m.group(1) in DRUMS:
            return DRUMS[m.group(1)] + st['tr'], text[m.end():]
        raise _err(f"not a pitch: {text!r} (C4, Eb5, F#3, D (relative), a degree like 5 / b3 / #4 with key=, a drum "
                   f"name; r . - rest, _ hold)", tok)

    @staticmethod
    def octave_marks(rest: str) -> tuple[str, int]:
        shift = 0
        while rest[:1] in ("'", '’', ','):
            shift += -1 if rest[0] == ',' else 1
            rest = rest[1:]
        return rest, shift

    @staticmethod
    def key(v: _Voice, tok, what: str) -> Key:
        k = v.st['key']
        if k is None:
            raise _err(f"{what} needs a key: notes(..., key='F# minor') or key=F#m in the line", tok)
        return k

    # --- durations
    def durs(self, rest: str, v: _Voice, tok) -> tuple[Fraction | None, float | None, str]:
        """(advance, sounding length, the rest) of a duration part like '/8', ':1.5', '/8:0.45'."""
        adv = length = None
        try:
            m = _VALUE_RE.match(rest)
            if m:
                adv = _value(m, v.st['unit'])
                rest = rest[m.end():]
                if rest.startswith(':'):
                    m2 = _VALUE_RE.match(rest)
                    if m2:
                        length = float(_value(m2, v.st['unit']))
                        if length <= 0:
                            raise ComposeError("a sounding length must be > 0")
                        rest = rest[m2.end():]
        except ComposeError as e:
            raise _err(str(e), tok) from None
        return adv, length, rest

    def take(self, v: _Voice, adv, tok) -> Fraction:
        if adv is None:
            return v.st['dur']
        if adv <= 0:
            raise _err("a duration must be > 0", tok)
        if v.st['sticky']:
            v.st['dur'] = adv
        return adv

    # --- events
    def event(self, tok: _Tok, v: _Voice) -> None:
        t = tok.text
        if t.startswith('g:'):
            p, rest = self.pitch(t[2:], v, tok) if t[2:] else (None, None)
            if p is None or rest:
                raise _err(f"g: takes a bare pitch (g:D5) or a group (g:(B4 C5)), got {t!r}", tok)
            v.graces.append((p, tok))
            return
        if _is_rest(t):
            head = t[0]
            adv, length, rest = self.durs(t[1:], v, tok)
            md = _mods(rest, tok)
            if length is not None:
                raise _err("a rest / hold has no sounding length", tok)
            if not md.empty():
                raise _err("a rest / hold takes no marks, ties or velocity", tok)
            for _ in range(md.times):
                d = self.take(v, adv, tok)
                if head == '_':
                    if v.last:
                        for r in v.last:
                            r.written += d
                    elif not v.last_rest:
                        raise _err("'_' holds the previous note, but there is none", tok)
                else:
                    if v.graces:
                        raise _err("grace notes lead into a rest", tok)
                    v.last, v.last_rest = [], True
                v.t += d
            return
        p, rest = self.pitch(t, v, tok)
        adv, length, rest = self.durs(rest, v, tok)
        md = _mods(rest, tok)
        for _ in range(md.times):
            d = self.take(v, adv, tok)
            r = self.new(v, p, d, tok)
            r.length = length
            self.apply(r, md, tok, v)
            self.pending(v, [r])
            self.lead_in(v, [r])
            v.recs.append(r)
            v.last, v.last_rest = [r], False
            v.t += d

    def new(self, v: _Voice, pitch: int, written: Fraction, tok) -> _Rec:
        if not 0 <= pitch <= 127:
            raise _err(f"pitch {pitch} is outside MIDI 0..127", tok)
        return _Rec(v.t, written, pitch, v.st, tok, v.name)

    def pending(self, v: _Voice, recs: list) -> None:
        """sf / fp written before this event."""
        if v.pending is None or not recs:
            return
        from .romantic import LEVELS
        kind, factor = v.pending
        for r in recs:
            r.lvl = (kind, factor)
        if kind in ('fp', 'sfp'):
            v.marks.append((recs[0].start, LEVELS['p'], True))
        v.pending = None

    def apply(self, r: _Rec, md: _Mods, tok, v: _Voice, group: bool = False) -> None:
        if md.acc or md.ghost:
            r.acc *= (v.st['accent'] ** md.acc) * (v.st['ghost'] ** md.ghost)
        if md.vel is not None:
            r.vel = md.vel
        if md.tie:
            r.tie = True
        for name, pos, kw in md.marks:
            if name == 'art':
                r.art = _art._art_name(pos[0])
            elif name == 'glide':
                ms = pos[0] if pos else kw.get('ms', 120.0)
                if isinstance(ms, bool) or not isinstance(ms, (int, float)) or not 0 < ms <= 2000:
                    raise _err(f"^gl({ms!r}): glide ms must be 0..2000", tok)
                r.glide = float(ms)
            elif name == 'ks':
                if len(pos) != 1 or not isinstance(pos[0], int):
                    raise _err("^ks(N) takes a keyswitch key number", tok)
                r.art = _art._art_name(pos[0])
            elif name == 'art':
                r.art = _art._art_name(pos[0])
            elif name == 'peak':
                r.peak = True
            elif name in GESTURES:
                r.gest.append((name, pos, kw))
            elif name in ('roll', 'strum'):
                if not group:
                    raise _err(f"^{name} belongs on a chord: [C4 E4 G4]^{name}", tok)
            elif name == 'fig':
                if not group:
                    raise _err("^fig belongs on a figure group: {Bb5 Ab5 G5 F5}/2^fig(arch)", tok)
            else:
                if r.orn is not None:
                    raise _err(f"one ornament per note (^{r.orn[0]} and ^{name})", tok)
                r.orn = (name, pos, kw)

    def lead_in(self, v: _Voice, recs: list) -> None:
        """Grace notes written before this event: grace= beats each, taken from the note before."""
        if not v.graces:
            return
        g = v.st['grace']
        k = len(v.graces)
        t = float(v.t)
        prev = next((r for r in reversed(v.recs) if r.grace is None), None)
        if prev is not None:
            pe = float(prev.start) + (prev.length if prev.length is not None else float(prev.written))
            if pe > t - g * k:
                prev.length = max(0.08, t - g * k - float(prev.start))
        lvl = recs[0].lvl if recs else None
        for i, (p, gtok) in enumerate(v.graces):
            r = _Rec(None, Fraction(0), p, v.st, gtok, v.name)
            r.grace = (t - g * (k - i), g)
            r.acc = v.st['gracevel']
            r.lvl = lvl if lvl and lvl[0] in ('sf', 'sfz') else None
            v.recs.append(r)
        v.graces = []

    # --- groups
    def group(self, g: _Group, v: _Voice) -> None:
        if g.kind == 'g':
            for x in g.items:
                if isinstance(x, _Group):
                    raise _err("a grace group holds pitches only", g.tok)
                p, rest = self.pitch(x.text, v, x)
                if rest:
                    raise _err(f"a grace note is a bare pitch, got {x.text!r}", x)
                v.graces.append((p, x))
            if g.suffix:
                raise _err(f"a grace group takes nothing after ')': {g.suffix!r}", g.tok)
            return
        if g.kind == '|:':
            if v.t != v.t0 or v.checked:
                _bar_check(v, g.tok)
            for _ in range(g.prefix):
                self.run(g.items, v, top=False)
                _bar_check(v, g.tok)
            return
        if g.kind == '[':
            self.chord(g, v)
        elif g.kind == '{':
            self.tuplet(g, v)
        elif g.kind == '(':
            self.slur(g, v)
        else:
            raise _err(f"unknown group {g.kind!r}", g.tok)

    def slur(self, g: _Group, v: _Voice) -> None:
        md = _mods(g.suffix, g.tok)
        if md.times != 1:
            raise _err("*N after a slur: repeat inside it, or use |: ... :|", g.tok)
        n0 = len(v.recs)
        self.run(g.items, v, top=False)
        recs = [r for r in v.recs[n0:] if r.grace is None]
        rest = _Mods()
        rest.acc, rest.ghost, rest.vel, rest.tie = md.acc, md.ghost, md.vel, md.tie
        rest.marks = [m for m in md.marks if m[0] != 'glide']
        for j, r in enumerate(recs):
            self.apply(r, md if j else rest, g.tok, v)
        self.ctx.slurs.append(recs)

    def chord(self, g: _Group, v: _Voice) -> None:
        inner = []
        ref0 = None
        for x in g.items:
            if isinstance(x, _Group) or x.text.startswith(('g:', '@', '$')) or x.text == '|' or _is_rest(x.text):
                raise _err("a chord holds notes only", x.tok if isinstance(x, _Group) else x)
            p, rest = self.pitch(x.text, v, x)
            if ref0 is None:
                ref0 = v.ref_step
            own, length, rest = self.durs(rest, v, x)
            if length is not None:
                raise _err("a chord note has one duration: its sounding length ([C2:4 G3 C4]/4)", x)
            md = _mods(rest, x)
            if md.times != 1:
                raise _err("*N on a chord note: repeat the chord instead", x)
            inner.append((p, own, md, x))
        if not inner:
            raise _err("an empty chord", g.tok)
        if ref0 is not None:
            v.ref_step = ref0
        adv, length, rest = self.durs(g.suffix, v, g.tok)          # [..]/4:3.9 = every note sounds 3.9
        md = _mods(rest, g.tok)
        mark = next((m for m in md.marks if m[0] in ('roll', 'strum')), None)
        for _ in range(md.times):
            d = self.take(v, adv, g.tok)
            recs = []
            gid = object() if mark else None
            for p, own, imd, x in inner:
                r = self.new(v, p, d if own is None else own, x)
                if own is not None:
                    r.gate, r.gap = 1.0, 0.0
                elif length is not None:
                    r.length = length
                self.apply(r, md, g.tok, v, group=True)
                self.apply(r, imd, x, v)
                if mark:
                    r.group = (gid, mark)
                recs.append(r)
            self.pending(v, recs)
            self.lead_in(v, recs)
            v.recs.extend(recs)
            v.last, v.last_rest = recs, False
            v.t += d

    def tuplet(self, g: _Group, v: _Voice) -> None:
        adv, length, rest = self.durs(g.suffix, v, g.tok)
        if length is not None:
            raise _err("a tuplet has a span, not a sounding length", g.tok)
        md = _mods(rest, g.tok)
        fig = next((m for m in md.marks if m[0] == 'fig'), None)
        if g.prefix:
            p_, q_ = (int(x) for x in g.prefix.split(':'))
            if p_ <= 0 or q_ <= 0:
                raise _err(f"tuplet ratio {g.prefix}: both numbers must be > 0", g.tok)
            if adv is not None:
                raise _err(f"a {g.prefix} tuplet takes no span: the ratio sets it", g.tok)
        elif adv is None:
            raise _err("a tuplet needs its span: {C5 D5 E5}/4 (or a ratio: 3:2{C5/8 D5 E5})", g.tok)
        if adv is not None and v.st['sticky']:
            v.st['dur'] = adv
        for _ in range(md.times):
            sub = _Voice(v.name, v.st, Fraction(0), tuplet=True)
            sub.ref_step = v.ref_step
            self.run(g.items, sub, top=False)
            if sub.graces:
                raise _err("grace notes at the end of a tuplet lead into nothing", g.tok)
            if sub.marks or sub.hairpin is not None or sub.pending:
                raise _err("dynamics inside a tuplet: write them before or after the group", g.tok)
            if sub.t <= 0:
                raise _err("an empty tuplet", g.tok)
            span = sub.t * Fraction(q_, p_) if g.prefix else adv
            f = span / sub.t
            recs = []
            for r in sub.recs:
                if r.grace is not None:
                    r.grace = (float(v.t) + r.grace[0] * float(f), r.grace[1] * float(f))
                else:
                    r.start = v.t + r.start * f
                    r.written = r.written * f
                    if r.length is not None:
                        r.length = r.length * float(f)
                r.voice = v.name
                self.apply(r, md, g.tok, v, group=True)
                recs.append(r)
            notes_ = [r for r in recs if r.grace is None]
            if fig:
                if any(r.group or r.grace for r in recs):
                    raise _err("^fig takes a plain run of notes", g.tok)
                gid = object()
                for r in notes_:
                    r.group = (gid, fig, span)
            self.pending(v, notes_[:1])
            self.lead_in(v, notes_[:1])
            v.recs.extend(recs)
            v.ref_step = sub.ref_step
            v.last, v.last_rest = notes_[-1:], False
            v.t += span


# ================================================================================================ Line

class Line(Clip):
    """A Clip parsed from notation (or composed from phrases), plus what the notation knows about it: voices
    ({label: Line}), gestures (pitch moves track.play() writes), peaks (beats of ^peak notes), meter, pickup, the
    spec and ornaments (notes(expand=False): the ornaments as written, for a player to realize). shift / transpose /
    octave / velocity / with_length keep them; other Clip transforms return plain Clips."""

    __slots__ = ('voices', 'gestures', 'peaks', 'meter', 'pickup', 'spec', 'ornaments')

    @classmethod
    def _make(cls, notes, length, voices=None, gestures=(), peaks=(), meter=(4, 4), pickup=0.0, spec='',
              ornaments=()):
        c = cls.__new__(cls)
        c._notes = tuple(sorted(notes, key=lambda n: (n.start, n.pitch)))
        c.length = float(length)
        c.voices = dict(voices or {})
        c.gestures = list(gestures)
        c.peaks = list(peaks)
        c.meter = meter
        c.pickup = float(pickup)
        c.spec = spec
        c.ornaments = list(ornaments)
        return c

    def __repr__(self) -> str:
        v = f", voices {', '.join(self.voices)}" if self.voices else ''
        return f"Line({len(self._notes)} notes, length={self.length:g}{v})"

    def _carry(self, c: Clip, shift: float = 0.0) -> 'Line':
        return Line._make(c._notes, c.length, {}, [dict(g, start=g['start'] + shift) for g in self.gestures],
                          [p + shift for p in self.peaks], self.meter, self.pickup, self.spec,
                          [dict(o, start=o['start'] + shift, notes=[n._replace(start=n.start + shift)
                                                                     for n in o['notes']]) for o in self.ornaments])

    def shift(self, by: float) -> 'Line':
        return self._carry(super().shift(by), by)

    def transpose(self, semitones: int) -> 'Line':
        return self._carry(super().transpose(semitones))

    def octave(self, n: int = 1) -> 'Line':
        return self.transpose(12 * n)

    def velocity(self, factor: float) -> 'Line':
        return self._carry(super().velocity(factor))

    def with_length(self, length) -> 'Line':
        return self._carry(super().with_length(length))

    def bars(self, a: int, b: int | None = None) -> Clip:
        """Bars a..b (1-based, inclusive; bar 1 starts at beat 0, after any pickup) as a Clip from 0."""
        bpb = float(_meter_beats(self.meter))
        b = a if b is None else b
        if not isinstance(a, int) or not isinstance(b, int) or a < 1 or b < a:
            raise ComposeError(f"bars({a}, {b}): bars are 1-based ints and b >= a")
        return self.slice((a - 1) * bpb, b * bpb)

    def bar(self, n: int) -> Clip:
        """Bar n (1-based) as a Clip from 0."""
        return self.bars(n, n)

    def gestures_at(self, at: float) -> list:
        """The line's gesture specs moved to beat `at`."""
        return [dict(g, start=g['start'] + at) for g in self.gestures]


# ================================================================================================ notes()

def _settings(kw: dict, where: str = 'notes') -> dict:
    st = dict(_DEFAULTS)
    for k, v in kw.items():
        if k not in _DEFAULTS:
            raise ComposeError(f"{where}(): unknown setting {k!r}; settings: {', '.join(SETTINGS)}")
        if k == 'key':
            st[k] = None if v is None else Key(v)
        elif k in ('dur', 'unit'):
            st[k] = 'meter' if (k == 'unit' and v == 'meter') else _duration(v, f"{where}() {k}")
            if st[k] != 'meter' and st[k] <= 0:
                raise ComposeError(f"{where}(): {k} must be > 0")
        elif k == 'meter':
            from .tempo import parse_meter
            st[k] = parse_meter(v, f"{where}() meter")
        elif k in ('oct', 'tr', 'st'):
            if isinstance(v, bool) or not isinstance(v, int):
                raise ComposeError(f"{where}(): {k} must be an int, got {v!r}")
            st[k] = v
        elif k == 'curve':
            if v not in ('smooth', 'linear'):
                raise ComposeError(f"{where}(): curve must be 'smooth' or 'linear', got {v!r}")
            st[k] = v
        elif k == 'sticky':
            st[k] = bool(v)
        else:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ComposeError(f"{where}(): {k} must be a number, got {v!r}")
            st[k] = float(v)
    if st['unit'] == 'meter':
        st['unit'] = Fraction(4, st['meter'][1])
    if st['vel'] <= 0:
        raise ComposeError(f"{where}(): vel must be > 0, got {st['vel']!r}")
    return st


def notes(spec, *, length=None, pickup=0, bpm=None, at=0.0, refs=None, transpose: int = 0, steps: int = 0,
          expand: bool = True, **settings) -> Line:
    """Notation -> a Line (a Clip; grammar: the module docstring / docs/COMPOSE_API.md "Notation"). spec: a string,
    or {voice label: string}. Settings (inline too, as name=value): vel (base velocity = 'mf', 96), dur (the first
    duration, 1/8), gate (sounding x written), gap (beats off every note), unit (what a bare number counts: beats;
    '1/8' eighths; 'meter' the meter's note value), oct (octave of degree 1 and the relative start), key (degrees,
    st=), accent / ghost (! and ? factors), grace / gracevel (written grace notes), slur (legato overlap), curve
    (hairpins), meter (bar checks), sfz (the sf factor), sticky (durations carry over). length: the clip length
    (default: where the line ends; 'bar': up to whole bars); pickup: beats before bar 1 (they start at -pickup, so
    the downbeat lands where the line is placed); bpm (a number or a function of the beat, e.g. s.tempo_at) and at
    (the line's position) for ornaments; refs: named phrases for $name; transpose / steps move the whole line
    (semitones / scale steps of key=). expand=False: the ornaments (^tr ^turn ^mord ^crush, ^roll / ^strum chords,
    ^fig groups) are not played - their notes are left out of the line and listed in line.ornaments (dicts: kind,
    start, dur, pitch, pitches, vel, args, kw, voice, notes = the written notes) for a player to realize in its own
    way (romantic.score); no bpm needed."""
    if 'tr' in settings or 'st' in settings:
        raise ComposeError("notes(): transpose= / steps= move the whole line (tr= / st= are the inline settings)")
    st = _settings(settings)
    if isinstance(transpose, bool) or not isinstance(transpose, int) or isinstance(steps, bool) \
            or not isinstance(steps, int):
        raise ComposeError(f"notes(): transpose / steps must be ints, got {transpose!r} / {steps!r}")
    st['tr'], st['st'] = transpose, steps
    pk = _duration(pickup, 'notes() pickup')
    if isinstance(spec, dict):
        for k in spec:
            if not isinstance(k, str) or not _VOICE_RE.match(k + ':'):
                raise ComposeError(f"notes(): voice label {k!r} must be a name like 'S', 'rh', 'v1'")
        text = '\n'.join(f"{k}: {s}" for k, s in spec.items())
    elif isinstance(spec, str):
        text = spec
    else:
        raise ComposeError(f"notes() takes a notation string or {{voice: string}}, got {type(spec).__name__}")
    ref_map = dict(refs.specs if isinstance(refs, Phrases) else (refs or {}))
    if refs is not None and not isinstance(refs, (dict, Phrases)):
        raise ComposeError(f"notes(): refs must be a phrases(...) object or {{name: spec}}, got {type(refs).__name__}")
    if bpm is not None and not callable(bpm):
        if isinstance(bpm, bool) or not isinstance(bpm, (int, float)) or not 20 <= bpm <= 400:
            raise ComposeError(f"notes(): bpm must be 20..400 or a function of the beat, got {bpm!r}")
    ctx = _Ctx(st, ref_map, pk, bpm, float(getattr(at, 'start', at)))
    ctx.bare = isinstance(refs, Phrases)                    # H('a1 a2'): bare names; refs={...}: $name only
    ctx.expand = bool(expand)
    _Builder(ctx).run(parse_tree(text), ctx.voice(''), top=True)
    return _finish(ctx, length, text)


def _finish(ctx: _Ctx, length, text: str) -> Line:
    from .romantic import LEVELS
    voices = [ctx.voices[n] for n in ctx.order]
    if len(voices) > 1 and voices[0].name == '' and not voices[0].recs and voices[0].t == voices[0].t0:
        voices = voices[1:]                                  # only labelled voices
    for vv in voices:
        if vv.graces:
            raise _err("grace notes at the end lead into nothing", vv.graces[0][1])
        if vv.hairpin is not None:
            raise _err(f"the hairpin at beat {_f(vv.hairpin[0])} has no target mark (end it with p, f, ...)",
                       vv.hairpin[2])
        if vv.pending:
            raise _err(f"{vv.pending[0]!r} at the end leads into no note")
    # ties: a tied note continues into the next note of its pitch starting where it ends
    for vv in voices:
        recs, drop = vv.recs, set()
        for i, r in enumerate(recs):
            if r.grace is not None or id(r) in drop:
                continue
            while r.tie:
                end = r.start + r.written
                nxt = next((x for x in recs[i + 1:] if x.grace is None and id(x) not in drop and x.pitch == r.pitch
                            and x.start == end), None)
                if nxt is None:
                    raise _err(f"the tie from {note_name(r.pitch)} at beat {_f(r.start)} finds no "
                               f"{note_name(r.pitch)} starting at beat {_f(end)}", r.tok)
                r.written += nxt.written
                r.length = None if nxt.length is None else float(nxt.start - r.start) + nxt.length
                r.tie = nxt.tie
                r.gest += nxt.gest
                r.peak = r.peak or nxt.peak
                drop.add(id(nxt))
        vv.recs = [r for r in recs if id(r) not in drop]
    # notes: lengths, velocities, marks
    out: list = []              # (voice, Note)
    pend: list = []             # (rec, Note) with an ornament
    gestures, peaks = [], []
    for vv in voices:
        fn = _factor_fn(vv.marks, vv.st['curve']) if vv.marks else None
        for r in vv.recs:
            if r.grace is not None:
                start, dur = r.grace
            else:
                start = float(r.start)
                if r.length is not None:
                    dur = r.length
                elif r.gate != 1.0 or r.gap:
                    dur = float(r.written) * r.gate
                    dur = max(dur - r.gap if r.gap else dur, 1e-3)
                else:
                    dur = float(r.written)
            if r.vel is not None:
                vel = r.vel
            else:
                v = r.base
                if fn is not None:
                    v = v * fn(start)
                if r.lvl is not None:
                    kind, factor = r.lvl
                    if kind in ('sf', 'sfz'):
                        v = v * factor
                    else:
                        v = r.base * LEVELS['f'] * (factor if kind == 'sfp' else 1.0)
                vel = _vel(v * r.acc)
            n = _art._mark(Note(start, dur, r.pitch, vel), art=r.art, gl=r.glide)
            if r.peak:
                peaks.append(start)
            for name, pos, kw in r.gest:
                gestures.append({'kind': name, 'start': start, 'dur': dur, 'pitch': r.pitch, 'args': list(pos),
                                 'kw': dict(kw), 'voice': vv.name})
            if r.orn is not None or r.group is not None:
                pend.append((r, n))
            else:
                out.append((vv.name, n, r))
    # slurs: legato inside each slur (articulation.legato)
    if ctx.slurs:
        where = {id(r): i for i, (_, _, r) in enumerate(out)}
        for recs in ctx.slurs:
            idx = sorted((where[id(r)] for r in recs if id(r) in where),
                         key=lambda i: (out[i][1].start, out[i][1].pitch))
            if len(idx) < 2:
                continue
            leg = _art.legato(Clip._raw([out[i][1] for i in idx], 0.0),
                              overlap=ctx.voices[out[idx[0]][0]].st['slur'], max_gap=1e9)
            for i, n2 in zip(idx, leg):
                out[i] = (out[i][0], n2, out[i][2])
    unexpanded = []
    if pend and ctx.expand:
        out += _ornaments(ctx, pend)
    elif pend:
        unexpanded = _written_ornaments(pend)
    end = max((vv.t for vv in voices), default=Fraction(0))
    meter = voices[0].st['meter'] if voices else (4, 4)
    if length is None:
        L = float(end)
    elif length == 'bar':
        bpb = _meter_beats(meter)
        L = float(max(bpb, -(-end // bpb) * bpb))
    else:
        from .patterns import beats as _b
        L = _b(length)
    line = Line._make([n for _, n, _ in out], L, None, gestures, peaks, meter, float(ctx.pickup), text, unexpanded)
    if any(vv.name for vv in voices):
        line.voices = {vv.name or 'main': Line._make([n for name, n, _ in out if name == vv.name], L, None,
                                                     [g for g in gestures if g['voice'] == vv.name],
                                                     [], vv.st['meter'], float(ctx.pickup), '',
                                                     [o for o in unexpanded if o['voice'] == vv.name])
                       for vv in voices}
    return line


def _written_ornaments(pend: list) -> list:
    """notes(expand=False): the ornaments as written (one dict per ornament, by start)."""
    out, groups = [], {}
    for r, n in pend:
        if r.group is not None:
            groups.setdefault(id(r.group[0]), []).append((r, n))
            continue
        name, pos, kw = r.orn
        out.append({'kind': name, 'start': n.start, 'dur': n.dur, 'pitch': n.pitch, 'pitches': [n.pitch],
                    'vel': n.vel, 'args': list(pos), 'kw': dict(kw), 'voice': r.voice, 'notes': [n]})
    for members in groups.values():
        r0 = members[0][0]
        name, pos, kw = r0.group[1]
        ns = sorted((n for _, n in members), key=lambda n: (n.start, n.pitch))
        dur = float(r0.group[2]) if len(r0.group) > 2 else max(n.dur for n in ns)
        out.append({'kind': name, 'start': ns[0].start, 'dur': dur, 'pitch': ns[0].pitch,
                    'pitches': [n.pitch for n in ns], 'vel': max(n.vel for n in ns), 'args': list(pos),
                    'kw': dict(kw), 'voice': r0.voice, 'notes': ns})
    return sorted(out, key=lambda o: o['start'])


def _factor_fn(marks: list, curve: str):
    """The dynamics factor at a beat (romantic.dynamics' curve: the same mechanism); before the first mark mf."""
    from .romantic import dynamics_factor
    return dynamics_factor([(-1e18, 1.0, True)] + [(float(b), lv, step) for b, lv, step in marks], curve)


def _ornaments(ctx: _Ctx, pend: list) -> list:
    """Expand ornaments (romantic / pianist / midifx moves) at the line's tempo; (voice, Note, None) tuples."""
    from . import midifx, pianist, romantic
    out, groups = [], {}
    for r, n in pend:
        if r.group is not None:
            groups.setdefault(id(r.group[0]), []).append((r, n))
            continue
        name, pos, kw = r.orn[0], list(r.orn[1]), dict(r.orn[2])
        bpm = _need_bpm(ctx, f"^{name}", r.tok)
        a = ctx.at + n.start
        key = ctx.voices[r.voice].st['key']
        try:
            if name == 'trill':
                if pos:
                    kw.setdefault('start', pos[0])
                c = romantic.trill(n.pitch, n.dur, bpm, at=a, key=key, vel=n.vel, **kw)
            elif name == 'turn':
                if pos:
                    kw.setdefault('where', pos[0])
                c = romantic.turn(n.pitch, n.dur, bpm, at=a, key=key, vel=n.vel, **kw)
            elif name in ('mordent', 'prall'):
                kw.setdefault('upper', name == 'prall' or (bool(pos) and pos[0] == 'upper'))
                c = pianist.mordent(n.pitch, n.dur, _bpm_num(bpm, a), key=key, vel=n.vel, at=a, **kw)
            elif name == 'crush':
                if pos:
                    kw.setdefault('grace', int(pos[0]))
                c = pianist.crush(n.pitch, n.dur, _bpm_num(bpm, a), vel=n.vel, at=a, **kw)
            else:
                raise _err(f"unknown ornament ^{name}", r.tok)
        except TypeError as e:
            raise _err(f"^{name}: {e}", r.tok) from None
        out += [(r.voice, x._replace(start=x.start - ctx.at), None) for x in c]
    for members in groups.values():
        r0 = members[0][0]
        name, pos, kw = r0.group[1][0], list(r0.group[1][1]), dict(r0.group[1][2])
        bpm = _need_bpm(ctx, f"^{name}", r0.tok)
        ns = sorted((n for _, n in members), key=lambda n: (n.start, n.pitch))
        a = ctx.at + ns[0].start
        num = next((p for p in pos if isinstance(p, (int, float)) and not isinstance(p, bool)), None)
        word = next((p for p in pos if isinstance(p, str)), None)
        try:
            if name == 'roll':
                if num is not None:
                    kw.setdefault('ms', num)
                if word is not None:
                    kw.setdefault('direction', word)
                c = pianist.roll([n.pitch for n in ns], max(n.dur for n in ns), _bpm_num(bpm, a),
                                 vel=max(n.vel for n in ns), at=a, **kw)
                c = [x._replace(start=x.start - ctx.at) for x in c]
            elif name == 'strum':
                c = list(midifx.strum(Clip._raw(ns, 0.0), 30.0 if num is None else num, word or 'down',
                                      bpm=_bpm_num(bpm, a), **kw))
            else:   # fig
                if word is not None:
                    kw.setdefault('shape', word)
                kw.setdefault('vel', (ns[0].vel, ns[0].vel))
                c = romantic.fioritura([n.pitch for n in ns], float(r0.group[2]), bpm, at=a, **kw)
                c = [x._replace(start=x.start - ctx.at) for x in c]
        except TypeError as e:
            raise _err(f"^{name}: {e}", r0.tok) from None
        out += [(r0.voice, x, None) for x in c]
    return out


def _need_bpm(ctx: _Ctx, what: str, tok):
    if ctx.bpm is None:
        raise _err(f"{what} is played in real time: give the tempo - notes(..., bpm=112) or "
                   f"notes(..., bpm=s.tempo_at, at=verse)", tok)
    return ctx.bpm


def _bpm_num(bpm, at: float) -> float:
    return float(bpm(at)) if callable(bpm) else float(bpm)


# ================================================================================================ phrases

class Phrases:
    """Named phrases composed into lines: H = phrases(a1='...', a2='...', key='F# minor', gate=0.92);
    H('a1 a2 | a1 b2') -> a Line - the phrases spliced in as if written there (holds and ties run across, bar
    checks see the whole line, settings written inside a phrase carry on). References: name, name+12 / name-5
    (semitones), name+2d (scale steps), name' / name, (octaves), name*2; plain notation may sit between them.
    H['a1'] is one phrase as a Line; H.add(b1='...') adds; H.variant('a3x', 'a3', {8: '...'}) copies a phrase with
    bars replaced. Settings given here are the defaults of every line; H('...', vel=110) overrides them."""

    _CALL = ('length', 'pickup', 'bpm', 'at', 'transpose', 'steps')

    def __init__(self, specs: dict | None = None, **kw):
        self.specs: dict[str, str] = {}
        self.settings = {k: kw.pop(k) for k in list(kw) if k in _DEFAULTS or k in self._CALL}
        _settings({k: v for k, v in self.settings.items() if k in _DEFAULTS}, 'phrases')
        self.add(**dict(specs or {}), **kw)

    def add(self, **named) -> 'Phrases':
        for k, s in named.items():
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', k):
                raise ComposeError(f"phrases(): name {k!r} must be an identifier (a1, hook, verse_b)")
            if k in DRUMS or k in DYNAMICS or k in ONE_SHOT or k in SETTINGS or k in ('r', 'g', 'subito'):
                raise ComposeError(f"phrases(): {k!r} is a word of the notation (a drum, dynamic or setting); pick "
                                   f"another name")
            if not isinstance(s, str):
                raise ComposeError(f"phrases(): phrase {k!r} must be a notation string, got {type(s).__name__}")
            parse_tree(s)
            self.specs[k] = s
        return self

    def __contains__(self, name) -> bool:
        return name in self.specs

    def __getitem__(self, name: str) -> Line:
        if name not in self.specs:
            raise ComposeError(f"no phrase {name!r}; phrases: {', '.join(self.specs) or 'none'}")
        return self(name)

    def __call__(self, text: str, **overrides) -> Line:
        kw = dict(self.settings)
        kw.update(overrides)
        return notes(text, refs=self, **kw)

    def variant(self, name: str, base: str, bars: dict) -> Line:
        """A copy of phrase `base` with bars replaced ({bar number (1-based, as separated by '|'): notation}),
        added as `name`: H.variant('a3_end', 'a3', {8: 'Ab4/2 r/4 Gb4/8 E4'})."""
        if base not in self.specs:
            raise ComposeError(f"variant(): no phrase {base!r}")
        segs = _split_bars(self.specs[base])
        for k, s in bars.items():
            if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(segs):
                raise ComposeError(f"variant(): phrase {base!r} has bars 1..{len(segs)}, got {k!r}")
            segs[k - 1] = s
        self.add(**{name: ' | '.join(segs)})
        return self[name]

    def __repr__(self) -> str:
        return f"Phrases({', '.join(self.specs)})"


def _split_bars(spec: str) -> list[str]:
    """A spec split at its top-level bar lines."""
    segs, depth, cur = [], 0, []
    for tok in re.split(r'(\s+)', spec):
        depth += sum(tok.count(c) for c in '[{(') - sum(tok.count(c) for c in ']})')
        if tok == '|' and depth == 0:
            segs.append(''.join(cur).strip())
            cur = []
        else:
            cur.append(tok)
    segs.append(''.join(cur).strip())
    return segs


def phrases(specs: dict | None = None, **kw) -> Phrases:
    """Named phrases: phrases(a1='...', a2='...', key=..., vel=...) -> Phrases; call it with a line of names:
    H('a1 a2 | a1+2d b2')."""
    return Phrases(specs, **kw)


# ================================================================================================ hold()

def hold(pitches, beats=4.0, vel=None, *, at=0.0, strum=None, bpm=None, direction: str = 'up', length=None,
         **settings) -> Line:
    """One held chord: hold('F#2 C#3 A3 E4', 8, 70) - every pitch for `beats` beats (per-note velocities:
    'Ab2=60 Eb3=48 G3=50'; marks too), at = where it starts inside the clip (beats), strum=ms rolls it (needs bpm=;
    direction 'up' / 'down'), length = the clip length (default at + beats). Settings as for notes()."""
    d = _duration(beats, 'hold() beats')
    if d <= 0:
        raise ComposeError("hold(): beats must be > 0")
    if not isinstance(pitches, str):
        pitches = ' '.join(p if isinstance(p, str) else note_name(int(p)) for p in pitches)
    kw = dict(settings)
    if vel is not None:
        kw['vel'] = vel
    line = notes(f"[{pitches}]:{_dec(d)}", **kw)
    c: Clip = line
    if strum:
        if bpm is None:
            raise ComposeError("hold(strum=ms) needs bpm= (the tempo where the chord lands)")
        c = c.strum(ms=strum, direction=direction, bpm=bpm)
    from .patterns import beats as _b
    a = _b(at)
    if a:
        c = c.shift(a)
    return Line._make(c._notes, a + float(d) if length is None else _b(length))


# ================================================================================================ format()

_DRUM_NAMES = ('kick', 'rim', 'snare', 'clap', 'tom_lo', 'hat', 'pedal', 'tom_mid', 'open_hat', 'tom_hi', 'crash',
               'ride', 'tamb', 'cowbell')
_NAME_OF_DRUM = {DRUMS[k]: k for k in _DRUM_NAMES}


def _nice_value(d: Fraction) -> str | None:
    for n in (1, 2, 4, 8, 16, 32, 64):
        base = Fraction(4, n)
        if d == base:
            return f"/{n}"
        if d == base * Fraction(3, 2):
            return f"/{n}."
        if d == base * Fraction(7, 4):
            return f"/{n}.."
        if d == base * Fraction(2, 3):
            return f"/{n}t"
    return None


_NICE = sorted({Fraction(4, n) * f for n in (1, 2, 4, 8, 16, 32, 64)
                for f in (Fraction(1), Fraction(3, 2), Fraction(7, 4), Fraction(2, 3))}, reverse=True)


def _dec(d: Fraction) -> str:
    """Exact decimal text of a Fraction with a terminating expansion (else a/b of beats as a note value)."""
    q = d.denominator
    for p in (2, 5):
        while q % p == 0:
            q //= p
    if q != 1:
        raise ComposeError(f"notation: {d} beats has no exact decimal")
    if d.denominator == 1:
        return str(d.numerator)
    sign = '-' if d < 0 else ''
    d = abs(d)
    whole = d.numerator // d.denominator
    rem = d - whole
    digits = ''
    while rem:
        rem *= 10
        digit = rem.numerator // rem.denominator
        digits += str(digit)
        rem -= digit
    return f"{sign}{whole}.{digits}"


def _dur_token(d: Fraction) -> str:
    return _nice_value(d) or ':' + _dec(d)


def _num_str(x: float) -> str:
    s = repr(float(x))
    return s[:-2] if s.endswith('.0') else s


def _as_frac(x: float) -> Fraction:
    return Fraction(repr(float(x)))


def _pitch_text(p: int, drums: bool, key) -> str:
    if drums and p in _NAME_OF_DRUM:
        return _NAME_OF_DRUM[p]
    if key is not None:
        return f"{key.spell(p % 12)}{p // 12 - 1}"
    return note_name(p)


def _mark_text(n) -> str:
    out = ''
    a = _art.articulation_of(n)
    if a is not None:
        if isinstance(a, int):
            out += f"^ks({a})"
        elif re.match(r'^[a-z_][a-z0-9_]*$', a) and a not in RESERVED:
            out += '^' + a
        else:
            if '"' in a:
                raise ComposeError(f"format(): articulation {a!r} contains a quote")
            out += f'^"{a}"'
    g = _art.glide_of(n)
    if g:
        out += f"^gl({_num_str(g)})"
    return out


def format(clip, *, key=None, drums: bool | None = None, meter=(4, 4), bars: bool = True, wrap: int | None = 4,
           vel: int | None = None, gate: float | None = None) -> str:
    """A clip (or a track) as notation that notes() parses back to the same notes - starts, durations, pitches,
    velocities, articulation and glide marks - and the same length. Sequential where the times allow it (note
    values, rests, bar lines where an event ends on one), '@beat' where they don't (humanized times), chords for
    notes together ([C4:4 E4 G4]/4: per-note sounding lengths), '=vel' where a velocity differs from the line's
    vel= (the most common one), 'C5/8:0.46' where a note sounds shorter / longer than it advances, a gate= setting
    when most notes share one. key= spells pitches in the key; drums=True writes drum names (a track of the
    'drums' instrument does by default); wrap = bars per text line; meter = where the bar lines go."""
    if hasattr(clip, '_song') and hasattr(clip, '_notes') and not isinstance(clip, Clip):    # a Track
        c = Clip._raw(list(clip._notes), clip._song.length)
        if drums is None:
            drums = getattr(clip.instrument, 'type', None) == 'drums'
    else:
        c = as_clip(clip)
    drums = bool(drums)
    k = None if key is None else Key(key)
    from .tempo import parse_meter
    m = parse_meter(meter, 'format meter')
    bpb = _meter_beats(m)
    ns = sorted(c, key=lambda n: (n.start, n.pitch))
    L = c.length
    groups: list[list] = []
    for n in ns:
        if groups and groups[-1][0].start == n.start:
            groups[-1].append(n)
        else:
            groups.append([n])
    if vel is None:
        counts: dict = {}
        for n in ns:
            counts[n.vel] = counts.get(n.vel, 0) + 1
        vel = max(sorted(counts), key=lambda v_: counts[v_]) if counts else 96
    if gate is None:
        gate = _guess_gate(groups, L)
    head = [f"vel={vel}"]
    if gate != 1.0:
        head.append(f"gate={_num_str(gate)}")
    if m != (4, 4):
        head.append(f"meter={m[0]}/{m[1]}")
    toks: list[str] = []
    state = {'cur': Fraction(0), 'dflt': Fraction(1, 2), 'bars': 0}

    def adv_tok(adv: Fraction, force: bool = False) -> str:
        if adv == state['dflt'] and not force:
            return ''
        state['dflt'] = adv
        return _dur_token(adv)

    def step(adv: Fraction) -> None:
        state['cur'] += adv
        cur = state['cur']
        if bars and cur > 0 and cur % bpb == 0:
            toks.append('|')
            state['bars'] += 1
            if wrap and state['bars'] % wrap == 0:
                toks.append('\n')

    def sounds(adv: Fraction, n) -> bool:
        """Does a note written with advance `adv` (gate applied) sound exactly n.dur?"""
        w = float(adv)
        return (max(w * gate, 1e-3) if gate != 1.0 else w) == n.dur

    for gi, grp in enumerate(groups):
        s = grp[0].start
        if float(state['cur']) != s:
            gap = _as_frac(s) - state['cur']
            if gap > 0 and (_nice_value(gap) or gap.denominator <= 20):
                toks.append('r' + adv_tok(gap))
                step(gap)
            else:
                toks.append('@' + _num_str(s))
                state['cur'] = _as_frac(s)
        nxt = groups[gi + 1][0].start if gi + 1 < len(groups) else None
        if nxt is None:
            nxt = L if L > s else s + max(x.dur for x in grp)
        adv = _as_frac(nxt) - state['cur']
        rest_after = None
        if len(grp) == 1 and not sounds(adv, grp[0]):      # a note then a rest reads better than a long advance
            for d0 in _NICE:
                if 0 < d0 < adv and sounds(d0, grp[0]) and _nice_value(adv - d0):
                    rest_after, adv = adv - d0, d0
                    break
        if len(grp) == 1:
            n = grp[0]
            pt = _pitch_text(n.pitch, drums, k)
            tok = pt + adv_tok(adv) if sounds(adv, n) else pt + adv_tok(adv, force=True) + ':' + _dec(_as_frac(n.dur))
            if n.vel != vel:
                tok += f"={n.vel}"
            toks.append(tok + _mark_text(n))
        else:
            inner = []
            for n in grp:
                t_ = _pitch_text(n.pitch, drums, k)
                if not sounds(adv, n):
                    t_ += ':' + _dec(_as_frac(n.dur))
                if n.vel != vel:
                    t_ += f"={n.vel}"
                inner.append(t_ + _mark_text(n))
            toks.append('[' + ' '.join(inner) + ']' + adv_tok(adv))
        step(adv)
        if rest_after is not None:
            toks.append('r' + adv_tok(rest_after))
            step(rest_after)
    if L > float(state['cur']):
        gap = _as_frac(L) - state['cur']
        if float(state['cur'] + gap) == L:
            toks.append('r' + adv_tok(gap))
            state['cur'] += gap
    body = ' '.join(toks).replace(' \n ', '\n').replace(' \n', '\n').strip()
    return ' '.join(head) + '\n' + body


def _guess_gate(groups: list, L: float) -> float:
    """The gate most single notes share (their sounding length / the time to the next onset), else 1."""
    counts: dict = {}
    for gi, grp in enumerate(groups):
        if len(grp) != 1:
            continue
        nxt = groups[gi + 1][0].start if gi + 1 < len(groups) else None
        if nxt is None:
            continue
        adv = nxt - grp[0].start
        if adv <= 0:
            continue
        g = round(grp[0].dur / adv, 3)
        if 0.05 <= g < 1.0 and float(_as_frac(adv)) * g == grp[0].dur:
            counts[g] = counts.get(g, 0) + 1
    if not counts:
        return 1.0
    g = max(sorted(counts), key=lambda x: counts[x])
    singles = sum(1 for grp in groups if len(grp) == 1)
    return g if counts[g] * 2 > singles else 1.0


# ================================================================================================ gestures

def realize(track, gestures: list, at: float = 0.0) -> list:
    """Write gesture specs of a Line (scoop, fall, doit, bend, vib, shake: agentsound.gesture moves) on a track
    with the line placed at `at`, at the song's tempo there: the pitch lane on 'instrument.pitchbend', the
    vibrato on the sampler's own vibrato (articulation.vibrato_prefixes; on other instruments on the pitch lane).
    track.play() does this for a Line. Returns the Gesture objects."""
    from . import gesture as G
    if not gestures:
        return []
    song = track._song
    prefixes = _art.vibrato_prefixes(track)
    made = []
    for g in gestures:
        a = at + g['start']
        bpm = song.tempo_at(max(0.0, a))
        pos, kw, kind = list(g['args']), dict(g['kw']), g['kind']
        try:
            if kind == 'scoop':
                if pos:
                    kw.setdefault('cents', float(pos[0]))
                obj = G.scoop(a, bpm, **kw)
            elif kind in ('fall', 'doit'):
                if pos:
                    kw.setdefault('semis', float(pos[0]))
                kw.setdefault('air', 0.0)
                obj = (G.fall if kind == 'fall' else G.doit)(a + g['dur'], bpm, **kw)
            elif kind == 'bend':
                if pos:
                    kw.setdefault('semis', float(pos[0]))
                obj = G.bend(a, g['dur'], bpm, **kw)
            elif kind == 'vib':
                if pos:
                    kw.setdefault('depth', float(pos[0]))
                if not prefixes:
                    kw.setdefault('lane', 'bend')
                obj = G.vibrato(a, g['dur'], bpm, **kw)
            else:
                if pos:
                    kw.setdefault('interval', float(pos[0]))
                obj = G.shake(a, g['dur'], bpm, **kw)
        except TypeError as e:
            raise ComposeError(f"notation ^{kind}: {e}") from None
        made.append((obj, bpm))
    bpm = max(b for _, b in made)
    bend = [s for o, _ in made for s in o.shapes if s.lane == 'bend']
    if bend:
        pts = G._sample(bend, lambda v: max(-24.0, min(24.0, v.get('bend', 0.0))), bpm)
        if pts:
            track.automate('instrument.pitchbend', [(0.0, 0.0)] + pts if pts[0][0] > 0 else pts)
    vib = [s for o, _ in made for s in o.shapes if s.lane == 'vib']
    if vib:
        pts = G._sample(vib, lambda v: max(0.0, min(200.0, v.get('vib', 0.0))), bpm)
        rate = sorted((r for o, _ in made for r in o.rate), key=lambda r: r[0])
        for pre in prefixes:
            if pts:
                track.automate(pre + '.vibrato', [(t, round(v_, 3)) + tuple(r) for t, v_, *r in pts])
            if rate:
                track.automate(pre + '.vibratorate', rate)
    return [o for o, _ in made]
