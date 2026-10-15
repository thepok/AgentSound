"""Sampling the student: genre weights (a blend) -> token sequences; the header can be constrained to the PLAYER
genre's moods / feels / forms (the genre whose players perform the piece), or forced per piece by a set SPREAD
(spread_headers: a set of N covers the player genre's moods / feels / forms / modes / tempo bands / keys evenly).
Torch is imported inside the functions that need it (the spread and the blend parser are stdlib)."""
from __future__ import annotations

import random

from .data import GENRE_NAMES

SPREAD_TOKENS = ('Mood', 'Feel', 'Form', 'Meter', 'Key', 'Mode', 'Tempo')
"""The header tokens a spread forces after BOS (grammar.HEADER's first seven, in order); the rest of the header and
the plan (swing, energy, ending, the climax) stay the model's, at --header-temp."""
ARR_SPREAD = {'layout': 'ALayout', 'climax': 'AClimax'}
"""The set-level arrangement draws a spread also forces (plan['set'] keys -> their Arr token prefix; schema-2
checkpoints): the token is masked in when the grammar reaches it, never a forced prefix (it sits after the plan)."""
TEMPO_BANDS = 3                  # a feel's tempo range in thirds (slow / middle / fast)
MIN_PAIR = 0.2                   # a form / feel pairing the composer draws rarer than this (FEEL_FORMS: the bossa
#                                  blues at 0.06) is left out of a spread: forcing it evenly would make it common


def parse_blend(spec: str) -> dict:
    """'new-age-piano=0.7,jazz-piano=0.3' or 'new-age-piano' -> {genre: weight} (normalized)."""
    out = {}
    for part in spec.split(','):
        name, _, w = part.partition('=')
        if name not in GENRE_NAMES:
            raise ValueError(f"unknown genre {name!r}")
        out[name] = float(w) if w else 1.0
    s = sum(out.values())
    return {k: v / s for k, v in out.items()}


def header_combos(genre) -> list[tuple]:
    """Every (mood, feel, form, mode) the genre's composer can draw (endless.composer.compose: the mood's feels,
    its forms - or the genre's - paired as FEEL_FORMS allows straight 8ths, at least MIN_PAIR; its modes with keys)."""
    from ..endless.genres import FEEL_FORMS, get
    g = get(genre) if isinstance(genre, str) else genre

    def pair(form, feel):
        w = FEEL_FORMS.get(form, {}).get(feel, 1.0)
        w = w[0] if isinstance(w, tuple) else w
        return 0.0 if form == 'blues' and g.feels[feel].get('meter', 4) == 3 else w
    out = []
    for m in sorted(g.moods):
        M = g.moods[m]
        for feel in sorted(f for f, w in M['feels'].items() if w > 0):
            forms = M.get('forms', g.forms)
            for form in sorted(f for f, w in forms.items() if w > 0 and pair(f, feel) >= MIN_PAIR):
                for mode in sorted(md for md, w in M['modes'].items() if w > 0 and M['keys'].get(md)):
                    out.append((m, feel, form, mode))
    return out


def spread_headers(genre, n: int, seed: int = 0) -> list[dict]:
    """n headers that cover the genre's values evenly (deterministic in genre / n / seed). Per piece, field by field
    (mood, then a feel that mood has, a form, a mode - only composable combinations, header_combos): the value the set
    has used least, overall and under the values already chosen (so the moods take turns exactly, and inside a mood
    its feels and modes take turns; the value of the piece before costs extra); then the least used tonic of that
    mood + mode (never the last piece's) and the least used third of the feel's tempo range (+ the mood's tempo shift,
    clamped to the range as the composer clamps it). Every header is one the composer itself draws:
    compose(plan=...) plays it."""
    from ..endless.genres import get
    g = get(genre) if isinstance(genre, str) else genre
    rng = random.Random(f"spread:{g.name}:{seed}")
    arng = random.Random(f"spread-arr:{g.name}:{seed}")      # (the arrangement's own dice: the headers stay as before)
    S = {k: w for k, w in sorted((g.plan.get('set') or {}).items()) if k in ARR_SPREAD}
    combos = header_combos(g)
    fields = ('mood', 'feel', 'form', 'mode')
    used = {}

    def cnt(key):
        return used.get(key, 0)
    out, prev = [], None
    for _ in range(n):
        path = ()
        for i, f in enumerate(fields):
            opts = sorted({c[i] for c in combos if c[:i] == path})
            path += (min(opts, key=lambda v: cnt((f, v)) + cnt(path + (v,)) + 0.3 * rng.random() +
                         (0.5 if prev and prev[f] == v and len(opts) > 1 else 0.0)),)
        m, feel, form, mode = path
        M, F = g.moods[m], g.feels[feel]
        tonics = [t for t in M['keys'][mode] if not prev or t != prev['key']] or M['keys'][mode]
        tonic = min(tonics, key=lambda t: cnt(('tonic', t)) + 0.5 * rng.random())
        lo, hi = F['tempo']
        band = min(range(TEMPO_BANDS), key=lambda b: cnt(('band', feel, b)) + 0.5 * rng.random())
        a = lo + (hi - lo) * band / TEMPO_BANDS
        b = lo + (hi - lo) * (band + 1) / TEMPO_BANDS
        tempo = int(round(min(hi, max(lo, rng.uniform(a, b) + M.get('tempo', 0)))))
        h = {'mood': m, 'feel': feel, 'form': form, 'meter': F.get('meter', 4), 'key': tonic, 'mode': mode,
             'tempo': tempo}
        for k, w in S.items():          # the set-level arrangement draws (plan['set']: layout, climax kind)
            top = max(w.values())
            opts = sorted((v for v, x in w.items() if x >= MIN_PAIR * top), key=str)
            h[k] = min(opts, key=lambda v: cnt(('arr', k, v)) + 0.3 * arng.random() +
                       (0.5 if prev and prev.get(k) == v and len(opts) > 1 else 0.0))
            used[('arr', k, h[k])] = cnt(('arr', k, h[k])) + 1
        keys = [(f, v) for f, v in zip(fields, path)] + [path[:i + 1] for i in range(len(path))] + \
            [('tonic', tonic), ('band', feel, band)]
        for k in keys:
            used[k] = cnt(k) + 1
        out.append(h)
        prev = h
    return out


def arr_tokens(h: dict) -> list[str]:
    """A spread header -> the Arr-block tokens it forces (schema 2): the layout, the climax kind."""
    return [f"{ARR_SPREAD[k]}_{h[k]}" for k in ARR_SPREAD if k in h]


def header_tokens(h: dict) -> list[str]:
    """A spread header -> the tokens forced after BOS (SPREAD_TOKENS order)."""
    return [f"{p}_{h[p.lower()]}" for p in SPREAD_TOKENS]


def cond_vector(blend: dict, n: int, device='cuda'):
    import torch
    c = torch.zeros((n, len(GENRE_NAMES)), device=device)
    for k, w in blend.items():
        c[:, GENRE_NAMES.index(k)] = w
    return c


def header_mask(vocab, player: str):
    """allowed(step, seq): steps 1-3 (Mood, Feel, Form) limited to the player genre's values."""
    import torch
    from ..endless.genres import get
    g = get(player)
    sets = {1: {f"Mood_{m}" for m in g.moods}, 2: {f"Feel_{f}" for f in g.feels}, 3: {f"Form_{f}" for f in g.forms}}
    masks = {}
    for k, names in sets.items():
        m = torch.zeros(len(vocab), dtype=torch.bool)
        for nme in names:
            if nme in vocab.stoi:
                m[vocab.stoi[nme]] = True
        masks[k] = m

    def allowed(step, seq):
        return masks.get(step)
    return allowed


def spread_prompts(player: str, n: int, seed: int, per: int = 1) -> list[list[str]]:
    """The forced header of every sequence for n pieces x `per` candidates (best-of: a piece's candidates share its
    header, consecutive)."""
    return [header_tokens(h) for h in spread_headers(player, n, seed) for _ in range(per)]


def spread_arr(player: str, n: int, seed: int, per: int = 1) -> list[list[str]]:
    """The Arr tokens forced per sequence (the layout, the climax kind of spread_headers), same rows as
    spread_prompts."""
    return [arr_tokens(h) for h in spread_headers(player, n, seed) for _ in range(per)]


def arr_mask(vocab, force: list[list[str]]):
    """(B, vocab) bool: per row every token allowed except the other values of a forced token's prefix (ALayout_*,
    AClimax_*) - AND-ed with the grammar it forces the value where the block asks for it. None when the vocabulary
    has no Arr block (schema 1) or nothing is forced."""
    import torch
    if 'Arr' not in vocab.stoi or not any(force):
        return None
    fam = {}
    for i, t in enumerate(vocab.itos):
        pre, sep, _ = t.partition('_')
        if sep and pre in ARR_SPREAD.values():
            fam.setdefault(pre, []).append(i)
    m = torch.ones((len(force), len(vocab)), dtype=torch.bool)
    for r, toks in enumerate(force):
        for t in toks:
            if t not in vocab.stoi:
                raise ValueError(f"forced arrangement token not in the vocabulary: {t}")
            m[r, fam[t.partition('_')[0]]] = False
            m[r, vocab.stoi[t]] = True
    return m


def generate(model, vocab, blend: dict, n: int, *, player: str | None = None, temperature: float = 1.0,
             top_p: float = 1.0, constrain: bool = False, batch: int = 48, prompt=None, seed: int = 0,
             grammar: bool = False, blend_mode: str = 'embed', header_temp: float | None = None,
             arr_force: list | None = None) -> list:
    """n token sequences (lists of strings) for a genre blend. constrain: the header's mood / feel / form from the
    player genre's; grammar: grammar-constrained decoding (agentsound.learn.grammar); blend_mode 'embed' (one
    conditioning vector, the weighted genre embeddings) or 'logits' (each genre's next-token log-probs mixed).
    prompt: tokens forced after BOS - one list for every sequence, or one list per sequence (n of them, equal length:
    spread_prompts). header_temp: the temperature of the header + plan (everything before the first 'H'), the notes
    keep `temperature`. A blend or constrain also keeps the Arr block in the player genre's arrangement vocabulary
    (player_arr_mask). arr_force: per sequence the Arr tokens it must take where the block asks for their key
    (spread_arr: the layout, the climax kind; arr_mask)."""
    import torch

    from .model import sample
    gen = torch.Generator(device='cuda')
    gen.manual_seed(seed)
    head = header_mask(vocab, player or max(blend, key=blend.get)) if constrain else None
    per_row = bool(prompt) and isinstance(prompt[0], (list, tuple))
    if per_row and len(prompt) != n:
        raise ValueError(f"{len(prompt)} prompts for {n} sequences")

    def ids(toks):
        bad = [t for t in toks if t not in vocab.stoi]
        if bad:
            raise ValueError(f"forced tokens not in the vocabulary: {bad}")
        return [vocab.stoi[t] for t in toks]
    pr = ([ids(p) for p in prompt] if per_row else ids(prompt)) if prompt else None
    out = []
    while len(out) < n:
        k = min(batch, n - len(out))
        if grammar:
            from .grammar import batch_allowed
            hm = {s: head(s, None) for s in (1, 2, 3)} if head else None
            allowed = batch_allowed(vocab, k, 'cuda', header=hm)
        else:
            allowed = head
        mix = [(cond_vector({g: 1.0}, k), w) for g, w in blend.items()] if blend_mode == 'logits' and \
            len(blend) > 1 else None
        p = pr[len(out):len(out) + k] if per_row else pr
        am = arr_mask(vocab, arr_force[len(out):len(out) + k]) if arr_force else None
        if am is not None:
            allowed = _with_arr(allowed, am)
        if constrain or len(blend) > 1:     # (the arrangement in the player's vocabulary, as the header)
            pm = player_arr_mask(vocab, player or max(blend, key=blend.get))
            if pm is not None:
                allowed = _with_arr(allowed, pm)
        got = sample(model, cond_vector(blend, k), vocab.bos, vocab.eos, model.c.ctx, temperature=temperature,
                     top_p=top_p, allowed=allowed, prompt=p, generator=gen, mix=mix, header_temp=header_temp,
                     head_end=vocab.stoi.get('H'))
        out += [vocab.decode(s) for s in got]
    return out


def player_arr_mask(vocab, player: str):
    """(vocab,) bool: every token except the Arr-block tokens the PLAYER genre's players cannot take (another student
    genre's: a jazz left hand in a new-age piece) - a blend or a constrained header keeps the arrangement in the
    player's vocabulary as header_mask keeps its moods. None for a schema-1 vocabulary."""
    import torch
    from .tokens import arrangement_tokens
    if 'Arr' not in vocab.stoi:
        return None
    foreign = arrangement_tokens(GENRE_NAMES) - arrangement_tokens([player])
    m = torch.ones(len(vocab), dtype=torch.bool)
    for t in foreign:
        if t in vocab.stoi:
            m[vocab.stoi[t]] = False
    return m


def _with_arr(allowed, am):
    """allowed AND the arrangement mask, per row; a row the AND would leave empty (a forced value the grammar does not
    allow there) keeps its own mask."""
    def f(step, seq):
        m = allowed(step, seq) if allowed is not None else None
        a = am.to(seq.device)
        if m is None:
            return a
        m = m.to(seq.device)
        if a.dim() == 1:
            a = a[None, :].expand(seq.shape[0], -1)
        m = m if m.dim() == 2 else m[None, :].expand_as(a)
        both = m & a
        empty = ~both.any(dim=1)
        if bool(empty.any()):
            both[empty] = m[empty]
        return both
    return f
