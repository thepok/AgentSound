"""The token grammar as an incremental parser (one coroutine per sequence): at every step the set of tokens that can
come next - for grammar-constrained sampling (well-formed sequences only; like a JSON mode). Mirrors tokens.decode:
the header order, the head parts in the form's order (harmony, then melody), a frame's blocks only when the plan has
the frame, positions inside the bar. A set entry ending in '_' is a prefix ('P_' = any pitch)."""
from __future__ import annotations

HEADER = ('Mood_', 'Feel_', 'Form_', 'Meter_', 'Key_', 'Mode_', 'Tempo_', 'Swing_', 'Energy_', 'Dyn_', 'SoloShape_',
          'Double_', 'Shout_', 'EndKind_', 'Second_', 'ReharmIn_')


def parser(schema: int = 2):
    """A generator: send it each token after BOS, it yields the allowed set for the next one. schema: the token
    schema (tokens.SCHEMA; 1 = before the Arr block - the old checkpoints)."""
    from ..endless.genres import FORMS
    from ..endless.arrangement import LISTS
    from .tokens import ARR_FIELDS, ARR_PIECE
    form, meter = None, 4
    toks = {}
    for pre in HEADER:
        t = yield {pre}
        toks[pre] = t
        if pre == 'Form_':
            form = t[5:]
        elif pre == 'Meter_':
            meter = int(t[6:]) if t[6:].isdigit() else 4
    parts = list(FORMS.get(form, {'parts': ('A1',)})['parts'])
    pos = {f"Pos_{k}" for k in range(meter * 12)}
    for head in ('OutParts', 'SoloCharts'):
        yield {head}
        t = yield {f"Part_{p}" for p in parts} | {'EndList'}
        while t != 'EndList':
            t = yield {f"Part_{p}" for p in parts} | {'EndList'}
    t = yield {'Climax', 'Climax_none'}
    if t == 'Climax':
        yield {f"Part_{p}" for p in parts}
        yield {'U_'}
        yield {'Bn_'}
        yield pos
        yield {'P_'}
    yield {'EndChord'}

    # the end chord (no length): Root Q [Bass]
    yield {'Root_'}
    yield {'Q_'}
    nxt = {'Arr', 'Arr_none'} if schema >= 2 else {'H'}
    t = yield {'Bass_'} | nxt
    if t.startswith('Bass_'):
        t = yield nxt
    if t == 'Arr':
        # the arrangement: the piece's keys, then per section (ASec_<name>) its keys in ARR_FIELDS order (a list key
        # repeats); the values are the decoder's to check (the player genre's vocabulary)
        piece = [pre + '_' for _, pre in ARR_PIECE]
        fields = [pre + '_' for _, pre in ARR_FIELDS]
        lists = {pre + '_' for key, pre in ARR_FIELDS if key in LISTS}
        t = yield set(piece) | {'ASec_', 'EndArr'}
        while t.startswith(tuple(piece)):
            i = next(k for k, p in enumerate(piece) if t.startswith(p))
            t = yield set(piece[i + 1:]) | {'ASec_', 'EndArr'}
        while t != 'EndArr':                             # t is an ASec_
            t = yield set(fields) | {'ASec_', 'EndArr'}
            while t not in ('EndArr',) and not t.startswith('ASec_'):
                i = next(k for k, p in enumerate(fields) if t.startswith(p))
                t = yield set(fields[i + 1:]) | ({fields[i]} if fields[i] in lists else set()) | {'ASec_', 'EndArr'}
    if t in ('Arr', 'Arr_none', 'EndArr'):
        t = yield {'H'}

    def changes(first_set):
        """Chords until EndH; first_set: what may come before the first Root (Blk_ for a head part)."""
        t = yield first_set | {'Root_'}
        while t.startswith('Blk_'):
            t = yield first_set | {'Root_'}
        while True:                                      # t is a Root_
            yield {'Q_'}
            t = yield {'Bass_', 'L_'}
            if t.startswith('Bass_'):
                yield {'L_'}
            t = yield {'Root_', 'EndH'}
            if t == 'EndH':
                return

    for i, p in enumerate(parts):                         # (the first 'H' was taken above)
        if i:
            yield {'H'}
        yield {f"Part_{p}"}
        yield from changes({'Blk_'})
    frames = {}
    for kind in ('Intro', 'Tag'):
        t = yield {f"H{kind}", f"H{kind}_none"}
        frames[kind] = t == f"H{kind}"
        if frames[kind]:
            for pre in ('IKind_', 'ILine_', 'IAppr_', 'IFrame_'):
                yield {pre}
            yield from changes(set())
    left = list(parts)
    t = yield {'HSolo', 'M'}
    while t == 'HSolo':
        t = yield {f"Part_{p}" for p in left}
        left = left[left.index(t[5:]) + 1:] if t[5:] in left else []
        yield from changes(set())
        t = yield ({'HSolo'} if left else set()) | {'M'}

    def bars(also=frozenset()):
        t = yield {'Bar', 'BarPre', 'EndM'} | set(also)
        if t == 'EndM' or t.startswith('Ref_'):
            return t
        while True:
            t = yield {'Bar', 'EndM'} | pos
            if t == 'EndM':
                return t
            if t.startswith('Pos_'):
                yield {'P_'}
                yield {'D_'}

    for i, p in enumerate(parts):
        if i:
            yield {'M'}
        yield {f"Part_{p}"}
        yield from bars()
    nxt = ({'MIntro'} if frames['Intro'] else {'MTag'} if frames['Tag'] else {'Motif'})
    left = list(parts)
    t = yield {'MOut'} | nxt
    while t == 'MOut':
        t = yield {f"Part_{p}" for p in left}
        left = left[left.index(t[5:]) + 1:] if t[5:] in left else []
        yield from bars()
        t = yield ({'MOut'} if left else set()) | nxt
    if t == 'MIntro':
        yield from bars()
        t = yield {'MTag'} if frames['Tag'] else {'Motif'}
    if t == 'MTag':
        yield from bars()
        t = yield {'Motif'}
    yield from bars({'Ref_'})
    yield {'Counter'}
    yield from bars({'Ref_'})
    while True:
        yield {'EOS'}


def admits(allowed: set, tok: str) -> bool:
    return tok in allowed or any(a.endswith('_') and tok.startswith(a) for a in allowed)


def check(tokens: list[str]) -> int | None:
    """The index of the first token the grammar does not admit (None: all admitted). tokens start with BOS; their
    schema read off them (tokens.schema_of)."""
    from .tokens import schema_of
    p = parser(schema_of(tokens))
    cur = next(p)
    for i, t in enumerate(tokens[1:], 1):
        if not admits(cur, t):
            return i
        if t == 'EOS':
            return None
        cur = p.send(t)
    return None


class Masks:
    """Allowed sets -> (vocab,) bool masks (cached)."""

    def __init__(self, vocab):
        import torch
        self.vocab, self.cache, self.torch = vocab, {}, torch
        self.prefix_ids = {}

    def mask(self, allowed: set):
        key = frozenset(allowed)
        m = self.cache.get(key)
        if m is None:
            torch = self.torch
            m = torch.zeros(len(self.vocab), dtype=torch.bool)
            for a in allowed:
                if a.endswith('_'):
                    for i, t in enumerate(self.vocab.itos):
                        if t.startswith(a):
                            m[i] = True
                elif a in self.vocab.stoi:
                    m[self.vocab.stoi[a]] = True
            if not bool(m.any()):
                m[self.vocab.eos] = True
            self.cache[key] = m
        return m


def batch_allowed(vocab, B: int, device, header=None):
    """allowed(step, seq) for model.sample: per-row masks from one parser per row (header: {step: extra mask}, e.g.
    the player genre's moods / feels / forms, AND-ed). The schema is the vocabulary's (a checkpoint from before the
    Arr block samples without one)."""
    import torch
    from .tokens import schema_of
    masks = Masks(vocab)
    schema = schema_of(vocab.itos)
    ps = [parser(schema) for _ in range(B)]
    cur = [next(p) for p in ps]
    every = torch.ones(len(vocab), dtype=torch.bool)

    def allowed(step, seq):
        if step >= 2:
            last = seq[:, -1].tolist()
            for i, p in enumerate(ps):
                if cur[i] is None:
                    continue
                try:
                    cur[i] = p.send(vocab.itos[last[i]])
                except StopIteration:
                    cur[i] = None
        rows = [masks.mask(c) if c is not None else every for c in cur]
        m = torch.stack(rows)
        if header and step in header:
            m = m & header[step][None, :]
        return m.to(device)
    return allowed
