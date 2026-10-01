"""One ornament budget for every player: tricks are spice, not a habit.

User feedback 2026-09-30 (perry-street-rain v3, the pianist): "etwas zu viele von diesen schnellen
Zwei-Tasten-Wechseln" - a player's flashy moves must be rare and land on structural moments. The pianist, the
guitarist, the hornist and the soloist all keep their tricks apart with this one mechanism (they used to carry three
copies of it):

    from agentsound.budget import Budget
    bud = Budget({'fast': 16 * 4, 'spice': 2 * 4}, same_every=32 * 4)          # beats between two of a class
    cands = [dict(t=6.0, cls='fast', name='trill', score=2.4), dict(t=8.0, cls='spice', name='turn', score=1.1)]
    bud.keep(cands, base=64)              # best-placed first: sets c['keep'], books the kept ones (song beats)
    bud.allows(80, 'spice', 'slide')      # would one more fit here?   bud.book(80, 'spice', 'slide')
    bud.save(120)                         # keep the fast budget free for a later moment (the climax)

A candidate is a dict: t (beats from `base`), cls (a budget class), name, score (higher = better placed: a phrase end,
the top of the line, a long note), optional slot (hashables: one candidate per slot - one move per note) and phrase
(a phrase number, for phrase_gap). Rules per class: at most one per every[cls] beats (0 / missing = never), two of the
same name at least same_every beats apart (classes in `same`), a minimum score (min_score: the FAST tricks only at
structural moments), never within phrase_gap phrases of another one of the class, and a saved moment (save()) counts
as taken for the classes in `save_cls` outside the span being decided. Deterministic: ties go to the earlier beat.
"""

from __future__ import annotations

from .theory import ComposeError

__all__ = ['Budget']

_EPS = 1e-6


class Budget:
    """A ledger of booked tricks with spacing rules. every: {class: beats}; same_every: beats between two of one
    name (classes in `same`); min_score: {class: score}; phrase_gap: {class: phrases} (1 = never in neighbouring
    phrases); save_cls: the classes a saved moment blocks. .events: [(beat, class, name, phrase)], .saved: [beat]."""

    def __init__(self, every: dict | None = None, *, same_every: float = 0.0, same=('fast',), min_score=None,
                 phrase_gap=None, save_cls=('fast',), events=None, saved=None):
        self.every = {str(k): float(v) for k, v in (every or {}).items()}
        for k, v in self.every.items():
            if v < 0:
                raise ComposeError(f"budget every[{k!r}] must be >= 0 beats, got {v:g}")
        self.same_every = float(same_every)
        self.same = tuple(same)
        self.min_score = dict(min_score or {})
        self.phrase_gap = dict(phrase_gap or {})
        self.save_cls = tuple(save_cls)
        self.events: list = [tuple(e) + (None,) * (4 - len(e)) for e in (events or [])]
        self.saved: list = [float(t) for t in (saved or [])]

    def __repr__(self) -> str:
        by: dict = {}
        for _, c, _, _ in self.events:
            by[c] = by.get(c, 0) + 1
        return f"Budget({by or 'nothing booked'}, every {self.every})"

    # ---- the rules
    def allows(self, at: float, cls: str, name=None, *, score: float | None = None, phrase=None,
               span: tuple | None = None) -> bool:
        """Would a `cls` trick named `name` fit at song beat `at`? span=(a, b): the beats being decided (a saved
        moment inside it is this call's to spend)."""
        gap = self.every.get(cls, 0.0)
        if gap <= 0:
            return False
        if score is not None and score < self.min_score.get(cls, -float('inf')):
            return False
        if any(abs(at - t) < gap - _EPS for t, c, _, _ in self.events if c == cls):
            return False
        if cls in self.save_cls:
            for t in self.saved:
                inside = span is not None and span[0] - _EPS <= t < span[1]
                if not inside and abs(at - t) < gap - _EPS:
                    return False
        if cls in self.same and self.same_every > 0 and name is not None:
            if any(abs(at - t) < self.same_every - _EPS for t, c, n, _ in self.events if n == name):
                return False
        pg = self.phrase_gap.get(cls)
        if pg is not None and phrase is not None:
            if any(abs(phrase - q) <= pg + _EPS for _, c, _, q in self.events if c == cls and q is not None):
                return False
        return True

    def book(self, at: float, cls: str, name=None, phrase=None) -> 'Budget':
        self.events.append((float(at), cls, name, phrase))
        return self

    def save(self, at: float) -> 'Budget':
        """Keep the `save_cls` budget free for song beat `at` (a climax): decisions outside a span containing it
        treat it as taken."""
        self.saved.append(float(at))
        return self

    def count(self, cls: str | None = None, span: tuple | None = None) -> int:
        return sum(1 for t, c, _, _ in self.events if (cls is None or c == cls)
                   and (span is None or span[0] - _EPS <= t < span[1]))

    def keep(self, cands: list, base: float = 0.0, span: tuple | None = None, *, slots: bool = True) -> list:
        """Decide candidates best-placed first (score high, then early): sets c['keep'] and books the kept ones
        (beat base + c['t']). One per slot (c['slot'], a tuple of hashables) when slots=True. span: the song beats
        this call decides (for saved moments). Returns the kept candidates in decision order."""
        taken: set = set()
        kept = []
        for c in sorted(cands, key=lambda c: (-c['score'], c['t'])):
            T = base + c['t']
            ok = self.allows(T, c['cls'], c.get('name'), score=c['score'], phrase=c.get('phrase'), span=span)
            if ok and slots and c.get('slot') is not None:
                ok = not (set(c['slot']) & taken)
            c['keep'] = ok
            if ok:
                self.book(T, c['cls'], c.get('name'), c.get('phrase'))
                if slots and c.get('slot') is not None:
                    taken |= set(c['slot'])
                kept.append(c)
        return kept
