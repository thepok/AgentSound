"""Lyrics for a sung line: English words -> phonemes (G2P) -> syllables -> one syllable per note.

    from agentsound import lyrics
    sung = lyrics.align(melody, 'Hold - on to the night, we were young')
    for s in sung: print(s)                 # Sung(note 0 'hold' hh|ow|l d ...), Sung(note 1 melisma) ...
    lyrics.check(melody, 'Hold - on to the night', bpb=4)    # the lyricist's checks: stress, vowels, phrasing

THE SYNTAX (one token per note, whitespace between tokens; it is what agentsound.notation attaches to a line):
    word        a word: one note per syllable ('tonight' takes two notes, 'night' one)
    to-geth-er  a word split by hand: one piece per note (the pieces must match the word's syllables)
    -           melisma: this note continues the previous syllable's vowel on a new pitch (a run)
    _           hold: this note continues the previous syllable on the same breath (a tie across a bar)
    word{hh ah l ow}   the phonemes given by hand (ARPAbet, stress digits optional: {hh ah0 l ow1})
    ,  ;  .  !  ?      after a word: a phrase mark - a preferred breath spot (the singer breathes there when the
                       line rests; with no rest it only lifts)
Apostrophes stay ("don't", "rock'n'roll"); other punctuation is ignored.

G2P: the CMU Pronouncing Dictionary (CMUdict, ARPAbet with lexical stress; bundled: third_party/cmudict, BSD-2),
then a voicebank's own dictionary (its dsdict entries: names, special words), then letter-to-sound rules (a warning
names the guess and how to fix it: word{...}). A word split by hand (to-geth-er) whose dictionary syllables do not
match its pieces is looked up piece by piece (with a warning). Syllables: the vowels are the nuclei; the consonants between two vowels split by the maximal-onset
principle (as many as form a legal English onset go to the next syllable: 'mon-ster', 'a-gain', 'ex-tra').
Stdlib only; the dictionary is read once per process.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .theory import ComposeError

__all__ = ['VOWELS', 'CONSONANTS', 'Syllable', 'Token', 'Sung', 'LyricsError', 'g2p', 'syllabify', 'parse', 'align',
           'check', 'cmudict_path', 'melody_notes', 'vowel_class']

VOWELS = ('aa', 'ae', 'ah', 'ao', 'aw', 'ay', 'eh', 'er', 'ey', 'ih', 'iy', 'ow', 'oy', 'uh', 'uw')
CONSONANTS = ('b', 'ch', 'd', 'dh', 'f', 'g', 'hh', 'jh', 'k', 'l', 'm', 'n', 'ng', 'p', 'r', 's', 'sh', 't', 'th',
              'v', 'w', 'y', 'z', 'zh')
_PHONES = set(VOWELS) | set(CONSONANTS)

# legal English onsets (maximal onset principle); single consonants except 'ng' are all legal
_ONSETS2 = {('p', 'l'), ('b', 'l'), ('k', 'l'), ('g', 'l'), ('f', 'l'), ('s', 'l'), ('p', 'r'), ('b', 'r'),
            ('t', 'r'), ('d', 'r'), ('k', 'r'), ('g', 'r'), ('f', 'r'), ('th', 'r'), ('sh', 'r'), ('t', 'w'),
            ('d', 'w'), ('k', 'w'), ('g', 'w'), ('s', 'w'), ('th', 'w'), ('s', 'm'), ('s', 'n'), ('s', 'p'),
            ('s', 't'), ('s', 'k'), ('s', 'f'), ('p', 'y'), ('b', 'y'), ('k', 'y'), ('g', 'y'), ('m', 'y'),
            ('f', 'y'), ('v', 'y'), ('hh', 'y'), ('hh', 'w'), ('v', 'r'), ('sh', 'w')}
_ONSETS3 = {('s', 'p', 'l'), ('s', 'p', 'r'), ('s', 't', 'r'), ('s', 'k', 'r'), ('s', 'k', 'w'), ('s', 'k', 'l'),
            ('s', 'p', 'y'), ('s', 'k', 'y')}

_OPEN = {'aa', 'ao', 'ah', 'ow', 'uw', 'ay', 'aw', 'oy', 'ey', 'iy', 'er', 'eh', 'ae'}
"""Vowels that sing open on long / high notes. The short closed ones ('ih', 'uh') pinch on a long high note."""


def vowel_class(v: str) -> str:
    """'open' (aa ao ah ow uw ay aw oy ey iy er eh ae: singable on long and high notes) or 'closed' (ih uh)."""
    return 'open' if v in _OPEN else 'closed'


class LyricsError(ComposeError):
    """A lyrics problem (a ComposeError: songs report it like any other mistake)."""


# ------------------------------------------------------------------------------------------- the dictionary

def _voices_dir() -> Path:
    env = os.environ.get('AGENTSOUND_VOICES')
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / 'assets' / 'voices'


BUNDLED_CMUDICT = Path(__file__).resolve().parent.parent / 'third_party' / 'cmudict' / 'cmudict.dict'


def cmudict_path() -> Path:
    """Where CMUdict is read from: $AGENTSOUND_CMUDICT, else the bundled third_party/cmudict/cmudict.dict (BSD-2,
    Carnegie Mellon University) - bundled so a song's syllables are the same on every machine."""
    env = os.environ.get('AGENTSOUND_CMUDICT')
    return Path(env) if env else BUNDLED_CMUDICT


_CMU: dict | None = None


def _cmudict() -> dict:
    """{word: [[phones with stress digits], ...]} (empty when the file is missing: the rules then guess)."""
    global _CMU
    if _CMU is None:
        _CMU = {}
        p = cmudict_path()
        if p.is_file():
            with open(p, encoding='utf-8', errors='replace') as f:
                for ln in f:
                    ln = ln.split('#', 1)[0].strip()
                    if not ln:
                        continue
                    parts = ln.split()
                    w = re.sub(r'\(\d+\)$', '', parts[0].lower())
                    _CMU.setdefault(w, []).append([x.lower() for x in parts[1:]])
    return _CMU


def _split_stress(ph: str) -> tuple[str, int | None]:
    m = re.match(r'^([a-z]+)([012])?$', ph.lower())
    if not m:
        raise LyricsError(f"phoneme {ph!r} is not ARPAbet (like 'ow1', 'hh', 'ah0')")
    return m.group(1), (int(m.group(2)) if m.group(2) is not None else None)


# letter-to-sound rules for words the dictionaries do not know (a rough guess; a warning says so)
_RULES = [
    ('tion', ['sh', 'ah0', 'n']), ('sion', ['zh', 'ah0', 'n']), ('ight', ['ay1', 't']), ('ough', ['ao1']),
    ('augh', ['ao1']), ('eigh', ['ey1']), ('tch', ['ch']), ('dge', ['jh']), ('sch', ['s', 'k']),
    ('ch', ['ch']), ('sh', ['sh']), ('th', ['th']), ('ph', ['f']), ('wh', ['w']), ('ck', ['k']), ('ng', ['ng']),
    ('qu', ['k', 'w']), ('kn', ['n']), ('wr', ['r']), ('gh', []),
    ('ee', ['iy1']), ('ea', ['iy1']), ('oo', ['uw1']), ('ou', ['aw1']), ('ow', ['ow1']), ('ai', ['ey1']),
    ('ay', ['ey1']), ('oi', ['oy1']), ('oy', ['oy1']), ('au', ['ao1']), ('aw', ['ao1']), ('ie', ['iy1']),
    ('ue', ['uw1']), ('ew', ['uw1']), ('ey', ['ey1']), ('ar', ['aa1', 'r']), ('or', ['ao1', 'r']),
    ('er', ['er0']), ('ir', ['er1']), ('ur', ['er1']),
    ('a', ['ae1']), ('e', ['eh1']), ('i', ['ih1']), ('o', ['aa1']), ('u', ['ah1']), ('y', ['iy0']),
    ('b', ['b']), ('c', ['k']), ('d', ['d']), ('f', ['f']), ('g', ['g']), ('h', ['hh']), ('j', ['jh']),
    ('k', ['k']), ('l', ['l']), ('m', ['m']), ('n', ['n']), ('p', ['p']), ('q', ['k']), ('r', ['r']),
    ('s', ['s']), ('t', ['t']), ('v', ['v']), ('w', ['w']), ('x', ['k', 's']), ('z', ['z']),
]
_MAGIC_E = {'a': 'ey1', 'i': 'ay1', 'o': 'ow1', 'u': 'uw1', 'e': 'iy1'}


def _rules(word: str) -> list[str]:
    w = re.sub(r"[^a-z]", '', word.lower())
    w = re.sub(r'([b-df-hj-np-tv-z])\1', r'\1', w)     # doubled consonant letters are one sound
    # magic e: consonant + e at the end lengthens the vowel before it (make, time, hope)
    magic = None
    m = re.search(r'([aeiou])([^aeiouy])e$', w)
    if m and len(w) > 3:
        magic = (m.start(1), _MAGIC_E[m.group(1)])
        w = w[:-1]
    out: list[str] = []
    i = 0
    while i < len(w):
        if magic is not None and i == magic[0]:
            out.append(magic[1])
            i += 1
            continue
        for g, ph in _RULES:
            if w.startswith(g, i):
                if g == 'y' and i == 0:
                    ph = ['y']
                elif g == 'c' and i + 1 < len(w) and w[i + 1] in 'eiy':
                    ph = ['s']
                elif g == 'g' and i + 1 < len(w) and w[i + 1] in 'eiy' and i > 0:
                    ph = ['jh']
                out += ph
                i += len(g)
                break
        else:
            i += 1
    if not any(_split_stress(p)[0] in VOWELS for p in out):
        out.append('ah0')
    # only one primary stress: the first vowel keeps it
    seen = False
    res = []
    for p in out:
        b, s = _split_stress(p)
        if b in VOWELS:
            res.append(b + ('1' if not seen else '0'))
            seen = True
        else:
            res.append(b)
    return res


def g2p(word: str, extra: dict | None = None) -> tuple[list[str], str]:
    """ARPAbet phonemes (lowercase, vowels with a stress digit) of one word and where they came from: 'cmudict',
    'bank' (extra: a voicebank's own entries, {word: [phonemes]}) or 'rules' (a guess)."""
    w = word.lower().strip("'")
    if not w:
        raise LyricsError(f"empty word {word!r}")
    cmu = _cmudict()
    if w in cmu:
        return list(cmu[w][0]), 'cmudict'
    if extra and w in extra:
        ph = list(extra[w])
        if not any(_split_stress(p)[0] in VOWELS for p in ph):
            raise LyricsError(f"the bank's entry for {word!r} has no vowel: {ph}")
        seen = False
        out = []
        for p in ph:
            b, s = _split_stress(p)
            if b in VOWELS and s is None:
                s = 0 if seen else 1
                seen = True
            out.append(b + ('' if s is None else str(s)))
        return out, 'bank'
    # 's / 'll / n't contractions the dictionary may lack: try the stem
    for suf, add in (("'s", ['z']), ("s", ['z']), ("'ll", ['l']), ("'d", ['d']), ("'re", ['er0']), ("'ve", ['v'])):
        if w.endswith(suf) and w[:-len(suf)] in cmu:
            return list(cmu[w[:-len(suf)]][0]) + add, 'cmudict'
    return _rules(w), 'rules'


# ------------------------------------------------------------------------------------------------ syllables

@dataclass
class Syllable:
    """One sung syllable: onset consonants, the vowel (nucleus), coda consonants (ARPAbet, lowercase), the lexical
    stress of the vowel (1 primary, 2 secondary, 0 none), the word and its place in the word."""
    onset: tuple
    nucleus: str
    coda: tuple
    stress: int = 1
    word: str = ''
    index: int = 0
    count: int = 1
    source: str = 'cmudict'

    @property
    def phonemes(self) -> list:
        return [*self.onset, self.nucleus, *self.coda]

    def __str__(self) -> str:
        return '|'.join([' '.join(self.onset), self.nucleus + ("'" if self.stress == 1 else ''), ' '.join(self.coda)])


def syllabify(phones, word: str = '', source: str = 'cmudict') -> list[Syllable]:
    """Syllables of a word's phonemes (vowels with or without stress digits)."""
    base, stress = [], []
    for p in phones:
        b, s = _split_stress(p)
        if b not in _PHONES:
            raise LyricsError(f"{word or 'word'}: unknown English phoneme {p!r} (ARPAbet: {' '.join(VOWELS)} | "
                              f"{' '.join(CONSONANTS)})")
        base.append(b)
        stress.append(s)
    nuclei = [i for i, b in enumerate(base) if b in VOWELS]
    if not nuclei:
        raise LyricsError(f"{word or 'word'}: no vowel in {' '.join(phones)}")
    if all(stress[i] is None for i in nuclei):           # given by hand without stress: the first vowel
        stress[nuclei[0]] = 1
    bounds = []                                          # where each syllable starts
    prev_end = 0
    for k, v in enumerate(nuclei):
        if k == 0:
            bounds.append(0)
            prev_end = v + 1
            continue
        cl = base[prev_end:v]                            # the consonants between two vowels
        split = len(cl)                                  # all to the coda ...
        for n in range(len(cl), -1, -1):                 # ... unless an onset can take them (maximal onset)
            on = tuple(cl[len(cl) - n:])
            if n == 0 or (n == 1 and on[0] != 'ng') or (n == 2 and on in _ONSETS2) or (n == 3 and on in _ONSETS3):
                split = len(cl) - n
                break
        bounds.append(prev_end + split)
        prev_end = v + 1
    bounds.append(len(base))
    out = []
    for k, v in enumerate(nuclei):
        a, b = bounds[k], bounds[k + 1]
        out.append(Syllable(tuple(base[a:v]), base[v], tuple(base[v + 1:b]),
                            stress[v] if stress[v] is not None else 0, word, k, len(nuclei), source))
    return out


# ------------------------------------------------------------------------------------------------ tokens

@dataclass
class Token:
    """One lyrics token: kind 'word' | 'melisma' | 'hold'; text; pieces (a hand-split word); phonemes (given by
    hand); mark (a phrase mark after it: ',' '.' ...)."""
    kind: str
    text: str = ''
    pieces: list = field(default_factory=list)
    phonemes: list | None = None
    mark: str = ''


_TOKEN = re.compile(r'^(?P<word>[^{}]*?)(?:\{(?P<ph>[^{}]*)\})?(?P<mark>[,;.!?:]*)$')


def parse(text: str) -> list[Token]:
    """Tokens of a lyrics string (see the module docstring for the syntax)."""
    if not isinstance(text, str) or not text.strip():
        raise LyricsError(f"lyrics must be a non-empty string, got {text!r}")
    out: list[Token] = []
    for raw in re.findall(r'[^\s{}]*\{[^{}]*\}\S*|\S+', text):     # word{ph ph} stays one token
        if raw in ('-', '–', '—'):
            out.append(Token('melisma', '-'))
            continue
        if raw == '_':
            out.append(Token('hold', '_'))
            continue
        lead = re.match(r'^[\"(\[]+', raw)
        if lead:
            raw = raw[lead.end():]
        raw = re.sub(r'[\")\]]+(?=[,;.!?:]*$)', '', raw)
        m = _TOKEN.match(raw)
        if not m:
            raise LyricsError(f"lyrics token {raw!r}: braces give phonemes after a word, like night{{n ay t}}")
        word, ph, mark = m.group('word'), m.group('ph'), m.group('mark')
        if mark and out and not word and ph is None:      # a lone ',' after a space
            out[-1].mark = out[-1].mark + mark
            continue
        if word in ('-', '_'):
            out.append(Token('melisma' if word == '-' else 'hold', word, mark=mark))
            continue
        word = re.sub(r"[^A-Za-z'\-]", '', word)
        pieces = [x for x in word.split('-') if x] if '-' in word.strip('-') else []
        word = word.replace('-', '')
        if not word and ph is None:
            raise LyricsError(f"lyrics token {raw!r} has no word")
        phon = ph.split() if ph is not None else None
        if phon is not None and not phon:
            raise LyricsError(f"lyrics token {raw!r}: empty phonemes {{}}")
        out.append(Token('word', word or ''.join(phon), pieces, phon, mark))
    return out


# ------------------------------------------------------------------------------------------------ alignment

@dataclass
class Sung:
    """What one note sings: kind 'syllable' (a new syllable: its consonants and vowel), 'melisma' (the previous
    vowel continues on this note's pitch) or 'hold' (the previous syllable continues, same breath); syllable (the
    syllable this note belongs to - for a melisma / hold the one it continues), word_start / word_end (the first /
    last note of a word), mark (a phrase mark after this note), note (index into the line's notes)."""
    note: int
    kind: str
    syllable: Syllable
    word_start: bool = False
    word_end: bool = False
    mark: str = ''
    guessed: bool = False

    def __str__(self) -> str:
        if self.kind != 'syllable':
            return f"Sung(note {self.note} {self.kind} of {self.syllable.word!r})"
        return f"Sung(note {self.note} {self.syllable.word!r} {self.syllable})"


def melody_notes(line) -> list:
    """The sung line's notes: the top note of every onset, sorted (a chord on the line sings its top note)."""
    from .patterns import as_clip
    c = as_clip(line)
    ns = []
    for n in sorted(c, key=lambda n: (n.start, -n.pitch)):
        if not ns or n.start > ns[-1].start + 1e-6:
            ns.append(n)
    return ns


def _word_syllables(tok: Token, extra) -> tuple[list[Syllable], bool, str]:
    if tok.phonemes is not None:
        return syllabify(tok.phonemes, tok.text, 'hand'), False, 'hand'
    ph, src = g2p(tok.text, extra)
    syl = syllabify(ph, tok.text.lower(), src)
    return syl, src == 'rules', src


def align(line, text: str, *, extra: dict | None = None, warnings: list | None = None) -> list[Sung]:
    """One Sung per note of `line` (a Clip / notes: its top line) from the lyrics `text`. extra: a voicebank's own
    dictionary ({word: [phonemes]}). warnings (a list): G2P guesses are appended to it. Raises LyricsError when the
    syllables and the notes do not match (and says where)."""
    notes = melody_notes(line)
    toks = parse(text)
    out: list[Sung] = []
    pending_warn = warnings if warnings is not None else []
    i = 0
    last: Syllable | None = None
    for t in toks:
        if t.kind in ('melisma', 'hold'):
            if last is None:
                raise LyricsError(f"lyrics: '{t.text}' ({t.kind}) needs a syllable before it to continue")
            if i >= len(notes):
                raise LyricsError(_mismatch(notes, toks, i, f"'{t.text}' has no note left"))
            if out:
                out[-1].word_end = False if t.kind == 'hold' and not out[-1].word_end else out[-1].word_end
            out.append(Sung(i, t.kind, last, mark=t.mark))
            # a melisma / hold on the last syllable of a word keeps the word end on the last note of the run
            if out[-2].word_end:
                out[-2].word_end = False
                out[-1].word_end = True
            i += 1
            continue
        syl, guessed, src = _word_syllables(t, extra)
        if guessed:
            pending_warn.append(f"lyrics: {t.text!r} is not in the dictionary; guessed /{' . '.join(str(s) for s in syl)}/ - "
                                f"give the phonemes if it sounds wrong: {t.text}{{{' '.join(p for s in syl for p in s.phonemes)}}}")
        if t.pieces and len(t.pieces) != len(syl):
            # the pieces win (the writer said how many notes): each piece is looked up / guessed on its own
            per = []
            for k, piece in enumerate(t.pieces):
                ph, src = g2p(piece, extra)
                ps = syllabify(ph, t.text.lower(), src)
                if len(ps) != 1:      # a piece with no / several vowels: one syllable around its first vowel
                    ph1 = [p for p in ph]
                    vi = [i for i, p in enumerate(ph1) if _split_stress(p)[0] in VOWELS]
                    keep = ph1[:vi[0] + 1] + [p for p in ph1[vi[0] + 1:] if _split_stress(p)[0] not in VOWELS]
                    ps = syllabify(keep, t.text.lower(), src)
                ps[0].index, ps[0].count = k, len(t.pieces)
                per.append(ps[0])
            pending_warn.append(f"lyrics: {'-'.join(t.pieces)!r} has {len(syl)} syllable(s) in the dictionary "
                                f"({' . '.join(str(s) for s in syl)}); sung piece by piece as "
                                f"{' . '.join(str(s) for s in per)} - give the phonemes if it sounds wrong: "
                                f"{t.text}{{...}}")
            syl = per
        for k, s in enumerate(syl):
            if i >= len(notes):
                raise LyricsError(_mismatch(notes, toks, i, f"{t.text!r} syllable {k + 1} has no note left"))
            out.append(Sung(i, 'syllable', s, word_start=k == 0, word_end=k == len(syl) - 1,
                            mark=t.mark if k == len(syl) - 1 else '', guessed=guessed))
            i += 1
        last = syl[-1]
    if i != len(notes):
        raise LyricsError(_mismatch(notes, toks, i, f"{len(notes) - i} note(s) have no syllable"))
    return out


def _mismatch(notes, toks, i, what) -> str:
    words = ' '.join(t.text for t in toks)
    return (f"lyrics and notes do not match: {what} (the line has {len(notes)} notes; the lyrics give {i}+ "
            f"syllables / continuations: {words!r}). One token per note: a word takes one note per syllable, '-' "
            f"continues a vowel on the next note (melisma), '_' holds it; split words by hand like to-geth-er.")


# ------------------------------------------------------------------------------------------------ the lyricist's checks

def check(line, text: str, *, bpb: float = 4.0, extra: dict | None = None, long: float = 1.5,
          high=None) -> list[str]:
    """The lyricist's checks of a line + its lyrics (warnings, none = fine):
    - stress: a stressed syllable of a word of 2+ syllables on a weaker beat than an unstressed syllable of the same
      word ('to-NIGHT' sung 'TO-night');
    - vowels: a closed short vowel (ih, uh) on a long note (>= `long` beats) or on the line's top notes (>= high,
      default the top 3 semitones of the line) pinches - open it ('feel' not 'fill', 'go' not 'good');
    - a run (melisma) on a closed vowel;
    - G2P guesses (words not in the dictionary)."""
    notes = melody_notes(line)
    warn: list[str] = []
    sung = align(line, text, extra=extra, warnings=warn)
    top = max(n.pitch for n in notes) if notes else 0
    hi = top - 2 if high is None else high

    def weight(beat: float) -> int:
        pos = beat % bpb
        if abs(pos) < 1e-6:
            return 4
        if abs(pos - bpb / 2) < 1e-6 and bpb % 2 == 0:
            return 3
        if abs(pos - round(pos)) < 1e-6:
            return 2
        if abs(pos * 2 - round(pos * 2)) < 1e-6:
            return 1
        return 0

    # syllable -> its notes
    words: list[list] = []
    for s in sung:
        if s.kind == 'syllable' and s.word_start:
            words.append([])
        if s.kind == 'syllable' and words:
            words[-1].append(s)
    for w in words:
        if len(w) < 2:
            continue
        ws = [(s.syllable.stress, weight(notes[s.note].start), s) for s in w]
        prim = [x for x in ws if x[0] == 1]
        unst = [x for x in ws if x[0] == 0]
        if prim and unst and max(u[1] for u in unst) > prim[0][1]:
            p = prim[0][2]
            u = max(unst, key=lambda x: x[1])[2]
            warn.append(f"stress: {p.syllable.word!r} - the stressed syllable '{p.syllable}' (beat "
                        f"{notes[p.note].start:g}) sits weaker than '{u.syllable}' (beat {notes[u.note].start:g}); "
                        f"move the stressed syllable onto the stronger beat or choose another word")
    for s in sung:
        n = notes[s.note]
        v = s.syllable.nucleus
        if vowel_class(v) != 'closed':
            continue
        span = n.dur
        j = s.note + 1
        while j < len(sung) and sung[j].kind != 'syllable':
            span += notes[j].dur
            j += 1
        if s.kind == 'syllable' and (span >= long or n.pitch >= hi):
            why = f"a long note ({span:g} beats)" if span >= long else f"a top note ({n.pitch})"
            warn.append(f"vowel: {s.syllable.word!r} sings the closed vowel '{v}' on {why} at beat {n.start:g} - "
                        f"open vowels (ah, oh, oo, ay, ee) carry long and high notes")
        if s.kind == 'melisma':
            warn.append(f"vowel: a run on the closed vowel '{v}' of {s.syllable.word!r} at beat {n.start:g} - "
                        f"runs sing on open vowels")
    return list(dict.fromkeys(warn))
