"""Insert-chain order checks: a nonlinear stage after a time / modulation effect, and anything after the master
limiter. Song.compile() turns the findings into warnings (docs/COMPOSE_API.md "Chain order").

A compressor, saturator, amp, bitcrush or driven tape AFTER a delay, reverb, chorus, dimension, micro-pitch double,
flanger, phaser or tremolo works on the repeats, tails and modulation too: an echo's repeats come out as loud as the
note (the compressor brings them up), a chorus's beating gets squashed and distorted into a grainy wobble, a
reverb tail pumps. Drive and compression belong in front of the time / modulation stages: Song.track(pre=[...]),
track.add_fx(..., first=True), a band role's pre_fx, the hero ORDER.

Not flagged (correct as they are):
  - keyed dynamics (a compressor / ducker with a sidechain: a duck or a carve, not a level-dependent stage);
  - processing after a 100 %-wet time effect on a bus (a return: bus/tape_echo's delay -> tape, a room -> crush);
  - a fully wet convolver on a track (a guitar cabinet: a filter, amp -> cab -> mic);
  - wah before an amp, per-zone amps, linear stages (eq, filter, width, utility) anywhere;
  - the patches in ALLOW (intentional: e.g. one-shot fx whose reverb is part of the sound) and nodes marked with
    node.allow_order('why').
"""

from __future__ import annotations

TIME_MOD = {'delay', 'reverb', 'gatedreverb', 'shimmer', 'convolver', 'chorus', 'ensemble', 'dimension', 'microshift',
            'flanger', 'phaser', 'tremolo'}
"""Time / modulation effects: their output is repeats, tails or a moving copy of the input."""
NONLINEAR = {'compressor', 'saturator', 'amp', 'bitcrush', 'tape'}
"""Level-dependent effects (gain reduction or harmonics follow the level)."""

_HERO_SYNTH = ("a quiet doubling layer (the halo's micro-pitch double / the piano layer's chorus, 6-10 dB under the "
               "lead voice) summed before the hero's slow 2:1 compressor / light tape: no audible pumping or grain, "
               "measured in children-of-neon / ghosts-of-ocean-drive (patches/hero_synth.py)")
ALLOW: dict[str, str] = {
    'hero/synth_lead': _HERO_SYNTH, 'hero/synth': _HERO_SYNTH,
    'hero/synth_piano': _HERO_SYNTH, 'hero/piano_synth': _HERO_SYNTH,
}
"""Patch name -> why its own chain may put a nonlinear stage after a time / modulation effect (only pairs inside the
patch's own chain are excused; effects the song adds are still checked)."""

MASTER_AFTER_LIMITER = {'utility'}
"""What may follow the last limiter on the master (level / width / mono utilities: no gain beyond the ceiling is
meant there - a meter, a mono check). Anything else after it undoes the limiting or overshoots the ceiling."""


def _wet(f) -> float:
    return float((f.params or {}).get('mix', 1.0 if f.type == 'convolver' else 0.0))


def _time(f, node_kind: str) -> bool:
    if f.type not in TIME_MOD:
        return False
    if f.type == 'convolver' and _wet(f) >= 1.0 and node_kind == 'track':
        return False                     # a cabinet IR on a track: a filter
    return True


def _nonlinear(f) -> bool:
    if f.type not in NONLINEAR or f.sidechain is not None:
        return False
    if f.type == 'tape':                # tape without drive is a wow / flutter / tone stage
        return float((f.params or {}).get('drive', 3.0)) > 0.0
    return True


def findings(node) -> list[str]:
    """Order findings of one track / bus chain (strings, without the node prefix); a stack's layers are checked
    through their own fx and then the track's (a layer's chorus feeds the track's saturator too)."""
    patch = getattr(node, 'patch', None)
    allowed_upto = 0
    if patch is not None and patch in ALLOW:
        from . import patches
        if patches.has(patch):
            allowed_upto = len(patches.get(patch).fx)
    out = _scan(list(node.fx), node.kind, allowed_upto)
    ins = getattr(node, 'instrument', None)
    if ins is not None and ins.type == 'stack' and not (patch is not None and patch in ALLOW):
        for lay in ins.params.get('layers', ()):
            lfx = list(getattr(lay, 'fx', ()) or ())
            if any(_time(f, 'track') for f in lfx):
                out += [f"layer {lay.id or '?'}: {m}" for m in _scan(lfx + list(node.fx), 'track', 0)]
    return out


def _scan(chain, kind: str, allowed_upto: int) -> list[str]:
    node_kind = kind
    out = []
    first_time = None
    for j, f in enumerate(chain):
        if first_time is None:
            if _time(f, node_kind):
                if node_kind == 'bus' and _wet(f) >= 1.0:
                    break                 # a return: what follows processes the return
                first_time = j
            continue
        if _nonlinear(f) and not (j < allowed_upto):
            t = chain[first_time]
            out.append(f"{f.name or f.type} (fx #{j}, {f.type}) after {t.name or t.type} (fx #{first_time}, {t.type}): the "
                       f"{'drive' if f.type in ('saturator', 'amp', 'bitcrush', 'tape') else 'compression'} works on the "
                       f"{'repeats / tails' if t.type in ('delay', 'reverb', 'gatedreverb', 'shimmer', 'convolver') else 'modulation'} "
                       f"too - put it first (track(pre=[...]), add_fx(..., first=True), a band role's pre_fx) or, when "
                       f"intended, node.allow_order('why')")
            break
    return out


def master_findings(master) -> list[str]:
    chain = list(master.fx)
    lim = [i for i, f in enumerate(chain) if f.type == 'limiter']
    out = []
    if len(lim) > 1:
        out.append(f"master: {len(lim)} limiters (fx #{', #'.join(str(i) for i in lim)}) - two master chains stacked "
                   f"(a second band preset or the song added one): keep one (bands.master_chain() keeps the first)")
    if lim:
        after = [f"{f.name or f.type} (fx #{i})" for i, f in enumerate(chain) if i > lim[-1]
                 and f.type not in MASTER_AFTER_LIMITER]
        if after:
            out.append(f"master: {', '.join(after)} after the last limiter - it undoes the limiting / overshoots the "
                       f"ceiling (true peak); move it before the limiter")
    return out
