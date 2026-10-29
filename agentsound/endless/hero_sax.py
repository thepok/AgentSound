"""A rare, thematic Hero Sax guest; selection precedes orchestra performance.

The draw belongs to the saved tune plan, never the candidate-ranking RNG.
No global switches, master ducking or new melodic material.
"""
import random
import statistics

from ..theory import ComposeError

MODES = ('off', 'occasional', 'frequent')
SINGING_RANGE = (57, 80)  # hero/sax's actual Weresax sample coverage ends at G#5


def draw(mode, seed, history=()):
    if mode not in MODES:
        raise ComposeError(f'hero_sax must be one of {MODES}, got {mode!r}')
    if mode == 'off' or (history and history[-1]):
        return False
    # With a mandatory intervening piece: about 1/4 and 2/5 selected slots.
    return random.Random(f'hero-sax:{seed}').random() < (1/3 if mode == 'occasional' else 2/3)


def slot(plan, seed, mode='occasional', history=()):
    plan['hero_sax'] = mode
    plan['hero_sax_enabled'] = draw(mode, seed, history)


def fit(notes, tempo):
    """Keep the whole contour in a singing register; decline fast/polyphonic lines."""
    ns = sorted(notes)
    if len(ns) < 6 or statistics.median(d for _, d, _ in ns) * 60/tempo < .3:
        return []
    if any(a+d > b+.04 for (a,d,_),(b,_,_) in zip(ns, ns[1:])):
        return []
    if sum(d * 60/tempo < .16 for _,d,_ in ns) / len(ns) > .15:
        return []
    lo,hi = SINGING_RANGE
    shifts = [s for s in range(-36, 37, 12) if all(lo <= q+s <= hi for _,_,q in ns)]
    if not shifts:
        return []
    shift = min(shifts, key=lambda s: abs(statistics.median(q+s for _,_,q in ns)-72))
    return [(a,d,q+shift) for a,d,q in ns]


def prepare(plan, score, tune, choir=None, colour=None):
    """Transfer at most three separated melody blocks, retaining existing other solos."""
    if not (tune.arrange or {}).get('hero_sax_enabled'):
        return []
    # A featured choir/guest owns its block; don't displace it with another solo.
    occupied = {e['block'] for prepared in (choir, colour) if prepared
                for e in prepared.get('events', [])}
    candidates = []
    for i,b in enumerate(score.blocks):
        if i in (0, len(score.blocks)-1) or b.name in occupied:
            continue
        parts = plan.by_block(b.name)
        if any(p.notes and ('solo' in p.role or 'concertmaster' in p.role) for p in parts):
            continue
        melodies = [p for p in parts if p.notes and p.function == 'melody']
        if len(melodies) != 1:
            continue
        line = fit(melodies[0].notes, float(tune.tempo))
        if line:
            candidates.append((i,b,line,melodies[0].role))
    if not candidates:
        return []
    # Establish the voice before the summit. A peak alone is no guest story.
    quiet = [c for c in candidates if not c[1].peak and c[1].start < score.blocks[-1].end * .6]
    if not quiet:
        return []
    first = quiet[0]
    selected = [first]
    later = [c for c in candidates if c[0] > first[0]+1]
    peak = next((c for c in later if c[1].peak), None)
    if peak:
        selected.append(peak)
    last = next((c for c in reversed(later) if not c[1].peak and c[0] > selected[-1][0]+1), None)
    if last:
        selected.append(last)
    events = []
    for _,b,line,source in selected:
        for p in plan.by_block(b.name):
            if p.function == 'melody' or (p.function == 'doubling' and p.voice == 'melody'):
                p.notes = []
            elif p.notes and p.function not in ('bass', 'pedal'):
                # Written balance, not a synchronized gain envelope on the ensemble.
                p.off -= 10 if b.peak else 5
        events.append(dict(block=b.name, start=b.start, end=b.end, peak=b.peak,
                           source=source, notes=line))
    plan.notes = sum(len(p.notes) for p in plan.parts)
    return events


def play(song, tune, events):
    from .. import Clip, hero, hornist, fx
    from ..bandlib.orchestration import Part
    if not events:
        return
    sax = hero(song.track('hero_sax', 'hero/sax', gain_db=-3.5), family='sax', genre='film',
               double=False, octave=False, duck=False, carve=False, dips=False, ride=False, throws=False)
    sax.sends.pop('echo', None)
    sax.fx.append(fx.eq({'peak3.freq': 3300, 'peak3.gain': -2, 'peak3.q': 1}))
    memory = hornist.Memory()
    played = []
    for i,e in enumerate(events):
        a,z = e['start'],e['end']
        clip = Clip([(on-a,min(d,z-on),q,96) for on,d,q in e['notes']], length=z-a)
        perf = hornist.arrange(clip, tune.tempo, family='sax', style='hero70s',
            section='chorus' if e['peak'] else 'verse', vel=(86,123) if e['peak'] else (78,119),
            seed=tune.seed+i, memory=memory, at=a, climax=e['peak'], max_phrase=8,
            bpb=song.beats_per_bar, depth=.8, accent=.28)
        perf.place(sax,a)
        played.extend((n.start+a, n.dur, n.pitch, n.vel, 'sustain') for n in perf.clip)
        song.orchestration.parts.append(Part('hero_sax', e['block'], 'melody', '',
                                             list(e['notes']), 'sustain', 0, True))
    peaks = [(e['start'],e['end']) for e in events if e['peak']]
    if peaks:
        sax.feature(*peaks, db=5, glide=2)
    song.lead_hint['hero_sax'] = sorted({s.name for s in song.sections for e in events
                                       if s.start < e['end'] and s.end > e['start']})
    song.hero_sax_events = events
    # The candidate score must see the new lead too, not a hole left by its source.
    sc = song.orch_scores[0]
    sc.parts['hero_sax'] = played
    sc.lines['hero_sax'] = {(round(a,4),q) for a,_,q,_,_ in played}
    for key,value in [('range', SINGING_RANGE), ('sweet', (62,78)), ('kind', 'sustain')]:
        sc.band.info.setdefault(key,{})['hero_sax'] = value
    song.orchestration.notes = sum(len(p.notes) for p in song.orchestration.parts)
