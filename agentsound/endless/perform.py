"""The endless players: a composed Tune -> a Song, played by the library's players (nothing new here).

    intro      the tune's own vamp (composer.frame: bVImaj7#11-V7b9, IV-iv-ii-V, a pedal ...) with the hook over it,
               on the piano alone, rubato, ballad-style (pianist.arrange); the riff intro: the hook an octave low, in
               time, without the left hand
    head       jazz.chorus: pianist.arrange per part (the melody touched, harmonized, decorated, filled; the left hand
               by the feel), one pianist.Memory for the whole tune (the ornament budget); every part's touch (velocity
               lift) and density from its arc level (genres.ARCS targets): calm A1, the bridge / C up, home released;
               the A sections state the restated theme plainly (plan['head']['theme']) from the A1's dice
    solo       soloist.solo with pianist.vocabulary on the tune's own chart (one cadence of a head-out part played
               another way in the last chorus when the tune has a reharm; a blues chorus by chorus its first or second
               chorus chart) in the tune's drawn SHAPE (solo_arc: a slow build that leaves the peak to the head out, a
               rise to its end, an early peak then calm, less is more, a block-chord chorus, trading 4s with the left
               hand; a double-time burst only in some tunes, at a drawn place) - the hook quoted and developed; one
               chorus (three of a blues); its energy from the tune's place in the set; every fast figure and named
               lick at most once in the piece, the tune before's (prev=, a set) drawn rarely
    out        the head from the bridge (AABA) / the second half (ABAC) / again (blues), paraphrased (jazz.paraphrase);
               a shout plan (tune.dynamics, ~25 %) plays the 2 bars around its first part's lifted top note as block
               chords, loud (_shout); the rest near the head's level, the last part comes down
    tag        the intro's vamp again with a twist (a drawn approach into the end chord; a cold stop struck short),
               ballad, ritardando
    end        song.ending in the drawn style (_ending: rolled, spread, a Basie plink, a short cadenza, a fade with
               the hook's head echoed), fermata, the room rings
A bossa feel plays its left hand as bossa comping (jazz.comp style 'bossa') over a root-fifth bass line (the
band's bass when it has one); a band with bass / drums (the genre's band dict) gets walking_bass / brushes through
jazz.chorus. The feel is straight unless the tune swings (jazz.Feel ratio)."""
from __future__ import annotations

import functools
import math
import random

from .. import bands, jazz, pianist, soloist
from ..notation import hold
from ..patches import fx
from ..patterns import Clip
from ..song import Song
from ..theory import chord, guide_tones, note_name, rootless
from .arrangement import PIANO_FIXED, SIGN_KEYS, Arrangement, Dice, section_specs
from .composer import Tune, _chord_fn, _pick, targets
from .genres import FORMS, KEY_SHIFTS, VARY_END, Genre, get


END_VOICINGS = {'lh': {'r5_10': 1.0, 'r7_10': 0.8, 'r10': 0.5}, 'form': {'A': 1.0, 'B': 0.8},
                'top': {9: 1.0, 'own': 0.6, 5: 0.4, 13: 0.4}}
"""The last chord's grip, drawn per piece (blind round 5: the same rolled final chord in every piece): the left hand
root-5th-10th / root-7th-10th / root-10th, the right hand a rootless A / B voicing with the 9th, the 5th or the 13th
(6th) over it - or its own top note."""


def end_clips(sym: str, meter: int, style: str = 'roll', seed=None):
    """The last chord (its grip drawn from END_VOICINGS by the symbol and `seed`): the left hand low (root + 5th / 7th
    + 10th), the right hand a rootless voicing with a colour on top (spread: the top an octave higher, the voicing
    opened)."""
    rng = random.Random(f"end-voicing:{sym}:{seed}")
    c = chord(sym)
    r = 36 + (c.root - 36) % 12                               # C2..B2
    if r > 43:
        r -= 12                                              # G#1..G2: a dark, open bottom
    g3, g7 = guide_tones(c)
    third = r + 12 + (((c.root + (3 if c.is_minor else 4)) if g3 is None else g3) - r) % 12
    grip = _pick(rng, END_VOICINGS['lh'])
    mid = (r + 7, 50) if grip == 'r5_10' or (grip == 'r7_10' and g7 is None) else \
        (r + (g7 - r) % 12, 48) if grip == 'r7_10' else None
    lh = f"{note_name(r)}=62" + (f" {note_name(mid[0])}={mid[1]}" if mid else '') + f" {note_name(third)}=52"
    rh = rootless(c, _pick(rng, END_VOICINGS['form']), 4, register=(58, 74))
    colour = _pick(rng, END_VOICINGS['top'])
    if colour == 'own':
        top = max(rh)
        rh = sorted(rh)[:-1]
    else:
        iv = {9: 2, 5: 7, 13: 9}[colour]
        if colour == 13 and c.is_minor and 9 not in c.intervals:
            iv = 2                                           # (a minor chord's 6th only when it has one)
        top = max(rh) + ((c.root + iv) - max(rh)) % 12 or 12
        if top - max(rh) < 3:
            top += 12
    if style == 'spread':
        top += 12
        rh = sorted(rh)[:1] + [q + 12 for q in sorted(rh)[1:]] if len(rh) > 2 else rh
    rh_s = ' '.join(f"{note_name(p)}={v}" for p, v in zip(sorted(rh), (60, 62, 64, 66))) + f" {note_name(top)}=88"
    beats = 2.0 * meter
    return hold(lh, beats - 0.1, length=beats), hold(rh_s, beats - 0.4, length=beats)


def _shout(s: Song, b, part, mel, peak_vel: float, meter: int, mem, sd: int) -> None:
    """The shout: the 2 bars around the lifted top note of the head out's first part (`mel`, its paraphrased melody)
    re-voiced in block chords / octaves (locked hands) and played loud (its peak note at `peak_vel`), the left hand with it - the one
    loud moment of the head out, at a melodic peak (blind round 3: a whole shout chorus in every tune read as a
    formula)."""
    from ..patterns import Clip, Note
    from ..theory import Progression
    peak = max(mel, key=lambda n: (n.pitch, -n.start))
    k = int(peak.start // meter + 1e-6)
    k0 = max(0, min(int(round(part.bars)) - 2, k - 1 if peak.start - k * meter < meter / 2 and k else k))
    a, z = k0 * meter, (k0 + 2) * meter
    A = part.start + a
    played = sorted((n for n in b.piano._notes if A - 0.15 <= n.start < part.start + z - 0.05),
                    key=lambda n: (n.start, -n.pitch))
    line = []
    t0 = None
    for n in played:                                  # the melody as played (its touch), the top of every onset
        if line and n.start - t0 < 0.1:               # (a rolled voicing: its top note is the melody)
            if n.pitch > line[-1].pitch:
                line[-1] = n
            continue
        line.append(n)
        t0 = n.start
    line = [n for n in line if any(abs(n.start - (part.start + m.start)) < 0.6 and n.pitch == m.pitch for m in mel)]
    if not line:
        return
    items, t = [], 0.0
    for c, d in part.prog.items:                      # the changes of the two bars
        lo_, hi_ = max(t, a), min(t + d, z)
        if hi_ - lo_ > 1e-6:
            items.append((c, hi_ - lo_))
        t += d
    prog = Progression._from(items, part.prog.key, part.prog.beats_per_bar)
    factor = max(1.0, peak_vel / max(n.vel for n in line))
    clip = Clip._raw([Note(max(0.0, n.start - A), n.dur, n.pitch, min(124, round(n.vel * factor))) for n in line],
                     z - a)
    arr = pianist.arrange(clip, prog, bpm=s.tempo_at(A), key=s.key, style='straight', density=1.0, climax=True,
                          devices={'octave': 2.0, 'locked': 2.0, 'drop2': 1.5}, ornaments={'restrike': 1.0},
                          fill=0.0, embellish=0.0, quick=0.0, lead_in=False, section_end=False, seed=sd % 997 + 361,
                          memory=mem, at=A, doubles=0.82)
    b.piano.clear(A - 0.15, part.start + z - 0.05)
    b.piano.play(arr.rh, A)
    lf = factor ** 0.5
    b.comp._notes = [n._replace(vel=min(118, round(n.vel * lf))) if A - 0.6 <= n.start < part.start + z else n
                     for n in b.comp._notes]


def band(s: Song, genre: Genre, feel_name: str, feel: jazz.Feel, mood: str | None = None):
    """The genre's band on song s: its preset (band['preset'], without=, the master drive + the feel's 'master'
    shift, band['options']: the preset's own options, e.g. jazz_trio voicing='smooth') and the spec's optional
    trims / pans / sends / eq on top. The one place the sound is set up - the pro
    reference songs (songs/pro-piano-*) call it too, so they sound like an endless tune by construction. mood: a mood
    whose 'drums' is None leaves the preset's drums out (lofi-piano's rain: the piano alone)."""
    BD = genre.band
    without = tuple(BD.get('without', ()))
    M = genre.moods.get(mood) if mood else None
    if M is not None and 'drums' in M and M['drums'] is None and 'drums' in bands.get(BD['preset']).roles:
        without += ('drums',)
    b = bands.make(BD['preset'], s, without=without, feel=feel,
                   master_gain=BD['master_gain'] + genre.feels[feel_name].get('master', 0.0),
                   **(BD.get('options') or {}))
    for role, db in (BD.get('trims') or {}).items():
        b[role].gain_db += db
    for role, pan in (BD.get('pans') or {}).items():
        b[role].instrument = b[role].instrument.but(pan=pan)
    for role, sends in (BD.get('sends') or {}).items():
        for bus, db in sends.items():
            b[role].sends[bus] += db
    for role, params in (BD.get('eq') or {}).items():
        b[role].add_fx(fx.eq(dict(params)))
    if BD.get('master_eq'):
        s.master.fx['eq'].set(**BD['master_eq'])
    return b


def phrase_steps(tune: Tune, part: str, plan: dict, seed) -> list | None:
    """phrase_levels' drawn step per 4-bar phrase of a part (None without the plan entry or levels)."""
    pt = (plan.get('head') or {}).get('phrase_touch')
    lv = (getattr(tune, 'levels', None) or {}).get(part)
    if not pt or not lv:
        return None
    rng = random.Random(f"phrase-touch:{seed}:{part}")
    out, step = [], 0
    for _ in range(0, len(lv), 2):
        step = _pick(rng, {k: w for k, w in pt['steps'].items() if k != step and not (step > 0 and k > 0)})
        out.append(step)
    return out


def phrase_levels(tune: Tune, part: str, plan: dict, seed, steps: list | None = None) -> list:
    """The phrase-to-phrase dynamics of a head part (humanize.touch levels=: [(beat, velocity shift)]): every 2-bar
    phrase moved by plan['head']['phrase_touch']['arc'] x its plan level (tune.levels) over the part's mean - the
    bridge's climb louder, the release softer - plus a step drawn per 4-bar phrase (never the same twice running, a
    quiet one after a loud one); the part's loudest phrase stays at the plan's level, the others come down by up to
    'depth' (the piece's peak stays where the plan put it). [] without the plan entry or levels. steps: the drawn
    steps (phrase_steps; the arrangement record's)."""
    pt = (plan.get('head') or {}).get('phrase_touch')
    lv = (getattr(tune, 'levels', None) or {}).get(part)
    if not pt or not lv:
        return []
    if steps is None or len(steps) != (len(lv) + 1) // 2:      # (the record's steps, else drawn)
        steps = phrase_steps(tune, part, plan, seed)
    unit, mean = tune.part_beats(part) / len(lv), sum(lv) / len(lv)
    raw = [pt['arc'] * (x - mean) + steps[u // 2] for u, x in enumerate(lv)]
    top = max(raw)                              # the part's loudest phrase keeps the plan's level, the others breathe
    return [(u * unit, round(max(-pt['depth'], x - top), 1)) for u, x in enumerate(raw)]


def section_dynamics(s: Song, tracks: list, spec: dict, *, power: float = 0.6) -> None:
    """Written dynamics per section on a played song: spec {section name: a mark ('p') | (start, end) | (start,
    peak, end)} (romantic.LEVELS; _marks: the end mark a quarter of the section before its end, the peak at 60 %),
    smooth hairpins between; every note's velocity x the level at its start - the first track (the melody) fully,
    the others at `power` (the accompaniment's gentler slope). In place; sections without a mark follow the curve."""
    from ..romantic import LEVELS, dynamics_factor
    from ..patterns import _vel
    pts, spans = [], []
    for sec in s.sections:
        if sec.name in spec:
            pts += [(b_, LEVELS[lv], False) for b_, lv in _marks(spec[sec.name], sec.start, sec.end)]
            spans.append((sec.start, sec.end))
    if not pts:
        return
    f = dynamics_factor(pts, 'smooth')
    a0, z0 = min(a for a, _ in spans), max(z for _, z in spans)
    for i, tr in enumerate(tracks):
        p_ = 1.0 if i == 0 else power
        tr._notes = [n._replace(vel=_vel(min(124.0, n.vel * f(n.start) ** p_))) if a0 - 1e-6 <= n.start < z0 else n
                     for n in tr._notes]


def burst_at(tune: Tune, genre: Genre) -> int | None:
    """Where solo_arc inserts a double-time tune's burst (a stage index, drawn; None: no burst)."""
    if not getattr(tune, 'double', False):
        return None
    stages = _solo_stages(tune, genre)
    top = next((i for i, st in enumerate(stages) if st[0] in ('climax', 'chords')), len(stages))
    return random.Random(f"double:{tune.seed}").randint(min(top, max(1, len(stages) // 2)), top)


def _solo_stages(tune: Tune, genre: Genre) -> list:
    shapes = genre.plan['solo'].get('shapes') or {}
    name = shapes.get(getattr(tune, 'solo_shape', None), {}).get('arc', genre.plan['solo'].get('arc', 'build'))
    return list(soloist.ARCS[name])


def solo_arc(tune: Tune, genre: Genre, at: int | None = None) -> tuple:
    """The solo's arc (soloist stages) of the tune's drawn shape (genre.plan['solo']['shapes']): its soloist.ARCS
    entry, with a 'burst' (double-time 16ths) inserted at a drawn place in its second half when the tune goes double
    time (the solo builds to its last chorus: blind round 5); at: its place (burst_at's draw: the record's)."""
    stages = _solo_stages(tune, genre)
    if getattr(tune, 'double', False):              # (before the climax: the burst builds into it)
        stages.insert(burst_at(tune, genre) if at is None else at, ('burst', 0.2, True))
    return tuple(stages)


def _jazz_labels(tune: Tune, n_solo: int) -> tuple:
    """(solo labels, head-out labels, the solo's chorus unit): the solo plays the tune's chart - a blues chorus by
    chorus the head's first or second chorus chart (drawn: tune.solo_charts, its turnarounds vary); a reharm
    (composer.reharm: one cadence of a head-out part) sounds in the last solo chorus and the head out alike ('v'
    parts)."""
    FD = FORMS[tune.form]
    unit = ['A1'] if tune.form == 'blues' else list(tune.parts)
    sch = getattr(tune, 'solo_changes', None) or {}
    charts = getattr(tune, 'solo_charts', None) or []
    solo_labels = [charts[k] if tune.form == 'blues' and k < len(charts) else p for k in range(n_solo) for p in unit]
    out_labels = list(getattr(tune, 'out_parts', None) or FD['out'])
    in_solo = getattr(tune, 'reharm_in', 'both') != 'out'    # (drawn: the head out alone may play the reharm)
    for p in sch:                                       # the reharmonized part: in the last chorus and the head out
        if tune.form == 'blues':
            if in_solo:
                solo_labels[-1] = p + 'v'
            out_labels = [x + 'v' if x == p else x for x in out_labels]
            continue
        if in_solo:
            solo_labels[len(solo_labels) - len(unit) + unit.index(p)] = p + 'v'
        out_labels = [x + 'v' if x == p else x for x in out_labels]
    return solo_labels, out_labels, unit


def _jazz_arrangement(tune: Tune, g: Genre, dice: Dice) -> Arrangement:
    """A jazz piece's recorded decisions (endless.arrangement, kind 'jazz'), drawn as build plays them: the left hand
    per section (the feel's 'lh_plan', never twice running), the phrase-touch steps of the head / head-out parts, the
    solo's choruses (as many as fit the plan's solo seconds), opening, quotes, ceiling over the head's top, climax
    window and double-time burst. Every draw has its own dice: drawing them first changes no other stream."""
    F, P = g.feels[tune.feel], g.plan
    meter, sd = tune.meter, tune.seed
    stretch = 2 if meter == 3 else 1
    FD = FORMS[tune.form]
    unit = ['A1'] if tune.form == 'blues' else list(tune.parts)
    unit_s = tune.part_beats(tune.parts[0]) * len(unit) * 60.0 / tune.tempo
    n_solo = max(1, min(FD['solo'], round(P['solo'].get('seconds', 75) / unit_s)))
    _, out_labels, _ = _jazz_labels(tune, n_solo)
    dice.order(['intro'] + [f"head:{p}" for p in tune.parts] + ['solo'] + [f"out:{x}" for x in out_labels] + ['tag'])
    lh = F.get('lh')
    lh_plan = F.get('lh_plan') if lh else None
    lrng = random.Random(f"lh-plan:{sd}")
    used: dict = {}

    def lh_at(where, default):
        name = default
        if lh_plan and lh_plan.get(where.split(':')[0]) is not None:
            prev_ = next(reversed(used.values()), None) if used else None
            name = _draw(lrng, lh_plan[where.split(':')[0]], prev_)
        used[where] = dice.put(where, 'lh', name)
    riff = tune.intro.get('kind') == 'riff'
    if len(tune.clip(tune.intro['melody'], P['intro'] * stretch * meter)) and not riff:
        lh_at('intro', lh or 'tenths')
    if lh_plan:
        for p in tune.parts:
            lh_at(f"head:{p}", lh)
        lh_at('solo', lh)
        for x in out_labels:
            lh_at(f"out:{x}", lh)
    if not F.get('comp'):
        lh_at('tag', lh or 'tenths')
    dyn = (P.get('dynamics') or {}).get(getattr(tune, 'dynamics', 'solo'), {})
    for p in tune.parts:
        dice.put(f"head:{p}", 'steps', phrase_steps(tune, p, P, sd))
    for i, x in enumerate(out_labels):
        if not (i == 0 and dyn.get('out_peak')):
            dice.put(f"out:{x}", 'steps', phrase_steps(tune, x.rstrip('v'), P, sd + 1))
    n_solo = dice.put('solo', 'choruses', n_solo)
    sp = P['solo']
    orng = random.Random(f"solo-opening:{sd}")
    dice.put('solo', 'opening', _pick(orng, sp.get('opening') or {'motif': 1.0}))
    dice.put('solo', 'quotes', _pick(orng, sp.get('quotes') or {2: 1.0}))
    top = max(n[2] for p in tune.parts for n in tune.melody[p])
    om = getattr(tune, 'out_melody', None) or {}
    out_top = max((n[2] for n in om.get(out_labels[0].rstrip('v'), ())), default=0)
    if not (dyn.get('out_peak') and out_top > top):
        if dice.put('solo', 'over', _pick(random.Random(f"peak:{sd}"), CLIMAX['over'])) > 0:
            dice.put('solo', 'window', _pick(random.Random(f"climax-window:{sd}"), CLIMAX['window']))
    dice.put('solo', 'burst', burst_at(tune, g))
    arr = dice.out
    arr.sections = {k: v for k, v in arr.sections.items() if v}       # (a section without a decision: not recorded)
    return arr


def build(tune: Tune, genre: Genre | None = None, prev: Song | None = None,
          arrangement: Arrangement | None = None) -> Song:
    """The Song of a Tune (deterministic: every seed derives from tune.seed). prev: the tune before it in a set (its
    Song): what it played - the pianist's fast figures, the soloist's moves - is drawn less often here (a set's
    memory: the same licks do not come back tune after tune). arrangement: the players' decisions above the notes
    (endless.arrangement; default tune.arrangement - a decoded student piece's - else drawn: arrange())."""
    g = genre or get(tune.genre)
    if g.plan.get('perform', 'jazz') == 'piano':
        return build_piano(tune, g, arrangement)
    if g.plan.get('perform') == 'organ':                # (the organ: endless/organ.py's textures + the organist)
        from .organ import build_organ
        return build_organ(tune, g)
    if g.plan.get('perform') == 'orchestra':            # (the orchestra: endless/orchestra.py - the score of lines,
        from .orchestra import build_orchestra          # the orchestrator, orch.Score)
        return build_orchestra(tune, g, arrangement)
    if g.plan.get('perform') == 'symphony':             # (the symphonic composer's score: endless/symphony.py)
        from .symphony import build_symphony
        return build_symphony(tune, g, arrangement)
    F, P, BD = g.feels[tune.feel], g.plan, g.band
    meter, sd = tune.meter, tune.seed
    stretch = 2 if meter == 3 else 1
    if arrangement is None:
        arrangement = getattr(tune, 'arrangement', None) or arrange(tune, g)
    A = _jazz_arrangement(tune, g, Dice('jazz', arrangement))     # (the record's decisions; the dice fill any gap)
    s = Song(tune.title, tempo=tune.tempo, key=tune.key, seed=sd % 100000 + 1, tail=6, meter=(meter, 4))
    letters = ''.join(p[0] for p in tune.parts)
    end_bars = P['end'] * (1 if meter == 4 else 2)
    # the solo: whole choruses (a blues: as many 12-bar choruses as fit the plan's solo seconds, up to FORMS' solo -
    # the record's choruses)
    n_solo = A.get('solo', 'choruses')
    sch = getattr(tune, 'solo_changes', None) or {}
    solo_labels, out_labels, unit = _jazz_labels(tune, n_solo)
    form = (f"intro:{P['intro'] * stretch} head:{letters} solo:{','.join(solo_labels)} "
            f"out:{','.join(out_labels)} tag:{P['tag'] * stretch} end:{end_bars}")
    parts = {p: tune.changes_str(p) for p in tune.parts}
    parts.update({p + 'v': tune.changes_str(changes=ch) for p, ch in sch.items()})
    parts.update(A=tune.changes_str(tune.parts[0]), intro=tune.changes_str(changes=tune.intro['changes']),
                 tag=tune.changes_str(changes=tune.tag['changes']), end=f"{tune.end_chord}:{end_bars}")
    intro, head, solo, out, tag, end = s.form(form, parts=parts)

    # ---- the band: the genre's preset, the tune's feel (straight 8ths unless it swings)
    if tune.swing:
        feel = jazz.Feel(tune.tempo, ratio=tune.swing, beats_per_bar=meter)
    else:
        feel = jazz.Feel(tune.tempo, ratio=0.5, layback={'piano': 8, 'comp': 4, 'bass': -2, 'drums': 0},
                         beats_per_bar=meter)
    b = band(s, g, tune.feel, feel)
    has_bass, has_drums = 'bass' in b.roles, 'drums' in b.roles
    bass_opts = BD.get('bass') if has_bass else None
    drum_opts = BD.get('drums') if has_drums else None
    if tune.swing and bass_opts:                         # a swung tune walks
        bass_opts = {'feel': 'four', 'vel': bass_opts.get('vel', 84)}
    if tune.swing and drum_opts:
        drum_opts = {'style': 'medium', 'vel': drum_opts.get('vel', 0.6)}
    kit = b.info.get('kit')
    lh = F.get('lh')
    rng = random.Random(f"perform:{sd}")
    # each fast figure (a run, a sweep, a trill) at most once in the piece, and what the tune before played less often
    mem = pianist.Memory.after(getattr(prev, 'endless_memory', None))
    lo, hi = F['touch']
    # the head's top note is the ceiling of every fill / voicing: the tune's peak is a melody note (the climax, the
    # shout's lifted top, the solo's end), never a run in the intro
    top = max(n[2] for p in tune.parts for n in tune.melody[p])
    orn = P['head'].get('ornaments')
    play = functools.partial(jazz.chorus, b, memory=mem, defaults=dict(
        piano=dict(lh=lh, lh_vel=54, style=F['style'], ceiling=note_name(top),
                   **({'ornaments': orn} if orn else {})),
        bass=bass_opts, drums=drum_opts))

    bossa = bool(F.get('comp'))

    def bossa_left(section, vel=1.0, seed=0, pedal_end=None):
        """The bossa left hand: rootless bossa comping + the root-fifth bass (the band's bass when it has one); vel:
        a level for the section or a list, one per part."""
        vels = list(vel) if isinstance(vel, (list, tuple)) else [vel] * len(section.parts)
        comp = dict(F['comp'])
        roll = comp.pop('roll', None)
        comp['vel'] = jazz.each(*[comp.get('vel', 54) * v for v in vels])
        play(section, None, piano=None, bass=None, drums=None, pedal_end=pedal_end,
             comp=dict(comp, answer=False, seed=seed, **({'roll': roll, 'roll_seed': rng} if roll else {})))
        bt = b.bass if has_bass else b.comp
        for i, (part, v) in enumerate(zip(section.parts, vels)):
            blo, bhi = F.get('bass_vel', (64, 92))
            line = part.prog.bass(pattern=F['bass_pattern'], rate='1/8', low='C2', vel=(blo + bhi) / 2 * v,
                                  gate=0.85)
            bt.play(jazz.bass_touch(line, blo * v, bhi * v, accent='1-3', seed=seed + i), part)

    def touches(lifts, drop=0, parts=None):
        return jazz.each(*[dict(lo=lo + round(x / 2) + drop, hi=hi + round(x) + drop,
                                levels=phrase_levels(tune, part, P, sd, A.get(f"head:{part}", 'steps')))
                           for x, part in zip(lifts, parts)])

    def arc(part, what):                             # a part's arc target (genres.ARCS) from its plan level
        return targets(g, tune.part_level(part))[what]

    # the left hand changes its figure from section to section (the feel's 'lh_plan': {where: a LH style / a
    # pianist.FIGURES figure or {name: weight}}, drawn, never twice running - shells, tenths, walking 10ths, broken
    # chords); without a plan (or a bossa's comping hand) the feel's one style everywhere, as before (drawn: the
    # arrangement record's 'lh', _jazz_arrangement)
    lh_plan = F.get('lh_plan') if lh else None
    lh_used: dict = {}

    def lh_of(where, default):
        """(LH style, its broken-chord figure) for a section / part."""
        name = A.get(where, 'lh', default)
        lh_used[where] = name
        if name is None or name in pianist.LH_STYLES:
            return name, 'tenths'
        return 'broken', name

    # ---- intro: piano alone - a vamp rubato (a ballad pianist's lead-in), the riff in time without the left hand
    intro_mel = tune.clip(tune.intro['melody'], intro.length)
    riff = tune.intro.get('kind') == 'riff'
    if len(intro_mel):
        i_lh, i_fig = lh_of('intro', lh or 'tenths') if not riff else (None, 'tenths')
        play(intro, intro_mel, bass=None, drums=None,
             piano=dict(style='sparse', density=0.45, seed=sd % 997 + 11, lead_in=False, touch=(lo - 8, hi - 12),
                        lh=None, section_end=False) if riff else
             dict(style='ballad', density=0.5, seed=sd % 997 + 11, lead_in=True, touch=(lo - 8, hi - 14),
                  lh=i_lh, lh_figure=i_fig, lh_vel=44, section_end=False))     # no run into the head
    if not riff:
        s.rubato(intro, depth=F.get('rubato', 0.05), phrase='lean')

    # ---- head
    dens = F.get('density', 0.55)
    head_mel = [tune.melody_clip(p) for p in tune.parts]
    # the theme is restated: every A is played from the A1's dice (the same melody gets the same hands; only the
    # budget and the cadence bars differ)
    d_a1 = min(0.9, max(0.2, dens + arc(tune.parts[0], 'density')))
    theme = P['head'].get('theme', {})                  # the A's decoration (fills, ornaments): a theme sounds plain
    per_part = {p: dict(theme, seed=sd % 997 + 101, density=d_a1) for p in tune.parts[1:] if p[0] == 'A'}
    per_part[tune.parts[0]] = dict(theme, lead_in=False)
    for p in tune.parts:                                # the bridge / C's decoration (plan['head']['bridge'])
        if p[0] != 'A' and P['head'].get('bridge'):
            per_part.setdefault(p, {}).update(P['head']['bridge'])
    if lh_plan:
        for p in tune.parts:
            st_, fg_ = lh_of(f"head:{p}", lh)
            per_part.setdefault(p, {}).update(lh=st_, lh_figure=fg_)
    play(head, head_mel, piano=dict(seed=sd % 997 + 101, lead_in=True,
                                    touch=touches([arc(p, 'touch') for p in tune.parts], parts=tune.parts),
                                    # the left hand breathes with the arc too: the first statement quiet
                                    lh_vel=jazz.each(*[50 + round(arc(p, 'touch') / 2) for p in tune.parts]),
                                    density=jazz.each(*[min(0.9, max(0.2, dens + arc(p, 'density')))
                                                        for p in tune.parts]),
                                    **per_part),
         lh_pedal=not bossa, bass=dict(seed=sd % 997 + 131) if bass_opts and not F.get('bass_pattern') else None,
         drums=dict(seed=sd % 997 + 141) if drum_opts else None)
    if bossa:
        bossa_left(head, 0.8, seed=sd % 997 + 151)
    if kit is not None:
        b.drums.play(jazz.brush_fill('swell', 2, kit=kit, vel=(14, 44)), head.beat(-2))

    # ---- solo: the soloist plays the arc with the pianist's vocabulary; the head's motif is its seed
    sp = dict(P['solo'])
    shape_ = (sp.get('shapes') or {}).get(getattr(tune, 'solo_shape', None), {})
    dyn = (P.get('dynamics') or {}).get(getattr(tune, 'dynamics', 'solo'), {})    # the piece's dynamic plan
    # the ornament / figure budget: one fast figure per chorus (blind round 3: trills / runs piled up)
    # (a move's name at most once per piece: same_every spans the song; the tune before's moves start counted)
    bud = soloist.Budget(spice_every=2, fast_every=solo.parts[0].bars * len(unit), same_every=10000, bpb=meter)
    seeded = {k: 3 for k in getattr(prev, 'endless_played', {})}
    bud.played = dict(seeded)
    bud.save(solo.parts[-1].start + 2 * meter)
    # the solo's top: over the head's highest note - its end is THE climax (60-75 % into the piece); a plan with its
    # peak in the head out (out_peak: its first part's top note lifted over the head's) keeps the solo under that
    om = getattr(tune, 'out_melody', None) or {}
    out_top = max((n[2] for n in om.get(out.parts[0].name.rstrip('v'), ())), default=0)
    solo_top = top if dyn.get('out_peak') and out_top > top else top + A.get('solo', 'over')    # (drawn: CLIMAX)
    s_lh = lh_of('solo', lh)[0] if lh_plan else lh
    voc = pianist.vocabulary(F.get('solo', 'straight'), lh_track=b.comp if lh else None, lh=s_lh, lh_vel=56,
                             memory=mem, seed=sd % 997 + 201, phrase_bars=sp.get('phrase_bars', 4) * stretch,
                             vel=tuple(shape_.get('solo_vel', dyn.get('solo_vel', sp.get('vel', (58, 110))))),
                             register=('A4', note_name(solo_top)), sixteenths=F.get('sixteenths'),
                             weights=dict(sp.get('weights') or {}, **shape_.get('weights', {})))
    motif = tune.clip(tune.motif, 2 * meter)
    # (the opening and the literal quotes, the burst's place: drawn per tune, the record's)
    soloist.solo(s, b.piano, voc, at=solo, prog=solo.prog, motif=motif, budget=bud, seed=sd % 997 + 211,
                 arc=solo_arc(tune, g, A.get('solo', 'burst')),
                 energy=sp.get('energy', 0.75) + sp.get('energy_set', 0.15) * tune.energy,
                 opening=A.get('solo', 'opening'), quotes=A.get('solo', 'quotes'))
    if bossa:
        bossa_left(solo, [0.9 + 0.25 * i / max(1, len(solo.parts) - 1) for i in range(len(solo.parts))],
                   seed=sd % 997 + 221)                  # the comping builds with the solo
    if bass_opts or drum_opts:
        play(solo, None, piano=None, bass=dict(seed=sd % 997 + 231) if bass_opts and not F.get('bass_pattern')
             else None, drums=dict(seed=sd % 997 + 241, vel=(drum_opts or {}).get('vel', 0.6) * 1.2)
             if drum_opts else None)

    # ---- the head out: paraphrased, from the bridge / the second half, near the head's level (the plan's 'out' lift);
    # a shout plan puts block chords / octaves under the 2 bars around the lifted top note of its first part and
    # plays them loud (dyn['shout']); every tune's last part comes down
    op = P.get('out', {})
    om = getattr(tune, 'out_melody', None) or {}
    shout = bool(getattr(tune, 'shout', False)) and bool(dyn.get('shout'))
    names = [p.name.rstrip('v') for p in out.parts]
    out_mel = [jazz.paraphrase(tune.clip(om[n], tune.part_beats(n)) if n in om else tune.melody_clip(n),
                               seed=sd % 997 + 301 + i, anticipate=op.get('paraphrase', 0.25), delay=0.1,
                               embellish=0.15, key=s.key)
               for i, n in enumerate(names)]
    drop = op.get('touch_drop', -4) + dyn.get('out', 0)
    end_lo, end_hi, end_dens = op.get('last', (-4, -12, 0.45))      # the last part comes down
    last_i = len(names) - 1
    # a plan with its peak in the head out ('out_peak': late, shout) lifts the head out's first part from the head's
    # loudest part's level, not its own (a solo without a climax leaves the peak to it)
    peak_t = max(arc(p, 'touch') for p in tune.parts)
    lift = [peak_t if i == 0 and dyn.get('out_peak') else arc(n, 'touch') for i, n in enumerate(names)]
    # (the phrases breathe as in the head - but a head-out part that carries the piece's peak keeps its level)
    out_lv = [[] if i == 0 and dyn.get('out_peak') else
              phrase_levels(tune, n, P, sd + 1, A.get(f"out:{out.parts[i].name}", 'steps'))
              for i, n in enumerate(names)]
    out_touch = [dict(lo=lo + end_lo, hi=hi + end_hi, levels=lv_) if i == last_i
                 else dict(lo=lo + round(x / 2) + drop, hi=hi + round(x) + drop, levels=lv_)
                 for i, (x, lv_) in enumerate(zip(lift, out_lv))]
    out_dens = [end_dens if i == last_i else min(0.9, max(0.2, dens + arc(n, 'density'))) for i, n in enumerate(names)]
    per_out = {out.parts[last_i].name: dict(style='ballad')}         # the last part settles (ballad voicings)
    if lh_plan:
        for part in out.parts:
            st_, fg_ = lh_of(f"out:{part.name}", lh)
            per_out.setdefault(part.name, {}).update(lh=st_, lh_figure=fg_)
    play(out, out_mel, lh_pedal=not bossa, piano=dict(seed=sd % 997 + 311, lead_in=True,
                                                      touch=jazz.each(*out_touch), density=jazz.each(*out_dens),
                                                      lh_vel=jazz.each(*[44 if i == last_i else 54
                                                                         for i in range(len(names))]),
                                                      **per_out),
         bass=dict(seed=sd % 997 + 321) if bass_opts and not F.get('bass_pattern') else None,
         drums=dict(seed=sd % 997 + 331) if drum_opts else None)
    if bossa:
        bossa_left(out, [0.75 if i == last_i else 0.9 for i in range(len(names))], seed=sd % 997 + 341)
    # the written dynamics per section (plan['dyn'], a feel's 'dyn' over it): quiet statements, the solo / head out
    # building to the piece's one peak, a soft tag - x the velocities both hands already have (the left hand at a
    # gentler slope); room for a loudness range like letters-to-the-morning's (the user, r6: one level throughout).
    # The body before the shout (the shout sets its own peak velocity), the tag / end after the ending is played
    dyn_spec = dict(P.get('dyn') or {}, **(F.get('dyn') or {}))
    if dyn.get('out_peak'):                              # (the plan's peak in the head out: the solo leaves it room)
        dyn_spec.update(P.get('dyn_out_peak') or {})
    dyn_tracks = [b.piano] + [t_ for t_ in (b.comp, b.bass if has_bass else None) if t_ is not None]
    section_dynamics(s, dyn_tracks, {k: v for k, v in dyn_spec.items() if k in ('intro', 'head', 'solo', 'out')})
    if shout and len(out_mel[0]):
        _shout(s, b, out.parts[0], out_mel[0], dyn['shout'], meter, mem, sd)

    chord_fn = _chord_fn(s)
    _land_solo(b, solo, out, chord_fn, random.Random(f"land:{sd}"), meter)    # the solo ends on a target
    peak = None
    if solo_top > top:                                   # the solo carries the piece's peak: its highest note
        peak = _peak_solo(b, solo, top, solo_top, chord_fn, meter,
                          window=A.get('solo', 'window'))                  # (drawn: CLIMAX['window'])

    # ---- tag + ending (a cold stop: the pedal comes up with the short last chord)
    tag_mel = tune.clip(tune.tag['melody'], tag.length)
    cold = (tune.tag or {}).get('approach') == 'cold'
    last_at = end.start - tune.tag['changes'][-1][1]
    pedal_up = last_at + 0.45 if cold else end.start - 0.1
    t_lh, t_fig = (None, 'tenths') if bossa else lh_of('tag', lh or 'tenths')
    play(tag, tag_mel, pedal_end=pedal_up, lh_pedal=not bossa, piano=dict(
        touch=(lo - 6, hi - 12), style='ballad', density=0.5, seed=sd % 997 + 401, lead_in=True,
        lh=t_lh, lh_figure=t_fig, lh_vel=44, bpm=tune.tempo * 0.85, section_end=False),
        bass=dict(seed=sd % 997 + 411, vel=76) if bass_opts and not F.get('bass_pattern') else None,
        drums=[(max(1, tag.bars - 1), dict(seed=sd % 997 + 421, vel=0.45, fills=False))] if drum_opts else None)
    if bossa:
        bossa_left(tag, 0.8, seed=sd % 997 + 431, pedal_end=pedal_up)
    if kit is not None:
        b.drums.play(jazz.brush_fill('swell', 2, kit=kit, vel=(12, 40)), tag.beat(-2))
    if cold:
        # a cold stop: the last chord struck short by both hands, then silence until the end chord
        for tr in [b.piano, b.comp] + ([b.bass] if has_bass else []):
            tr._notes = [n._replace(dur=min(n.dur, max(0.1, last_at + 0.45 - n.start)))
                         if n.start < end.start and n.start + n.dur > last_at + 0.45 else n for n in tr._notes
                         if not last_at + 0.3 < n.start < end.start - 1e-6]
    if peak is None:                                     # (a shout: its lifted top is the piece's peak)
        peak = max((n.pitch for n in b.piano._notes if out.start - 1e-6 <= n.start < out.end - 1e-6), default=None)
    _ending(s, b, tune, end, tag, meter, has_bass, has_drums, kit, ceiling=peak)
    # (the tag and the final chord: their written dynamics now that they are played)
    section_dynamics(s, dyn_tracks, {k: v for k, v in dyn_spec.items() if k in ('tag', 'end')})
    _lh_under(b, (head, solo, out), meter, random.Random(f"lh-under:{sd}"))
    s.endless_lh = {k: v for k, v in lh_used.items()} if lh_plan else \
        {k: (lh if k in ('head', 'solo', 'out') else lh or 'tenths') for k in ('intro', 'head', 'solo', 'out', 'tag')}
    s.endless_tune = tune                                   # what the runner logs / writes next to the mp3
    # the set's memory (what this tune played): the next tune avoids them
    s.endless_memory = mem
    s.endless_played = {k: v - seeded.get(k, 0) for k, v in bud.played.items() if v > seeded.get(k, 0)}
    s.endless_arrangement = A                               # (what was played: the record)
    return s


# ------------------------------------------------------------------------------------------------ the piano arrangement

def _draw(rng: random.Random, weights, last=None) -> str:
    """A figure from a figure set (a name, or {name: weight}): never the one before when there is another."""
    if isinstance(weights, str):
        return weights
    cand = {k: w for k, w in weights.items() if k != last} or dict(weights)
    return _pick(rng, cand)


def _breathes(rh, t: float, span: float) -> bool:
    """The melody breathes in the bar [t, t + span): no new right-hand onset in its second half and a beat or
    more there with nothing sounding (a phrase's landing and its rest - a held note keeps the hand flowing)."""
    a, z = t + span / 2, t + span
    if any(a - 1e-6 <= n.start < z - 1e-6 for n in rh):
        return False
    held = max((n.start + n.dur for n in rh if n.start < a), default=t)
    return z - max(a, held) >= 1.0 - 1e-6


def _marks(dyn, a: float, z: float, peak_at: float | None = None) -> list:
    """A section's dynamics (a mark, (start, end) or (start, peak, end)) -> [(beat, level)]: the start mark at the
    section start, the end mark a bar before its end (the hairpin), the peak at `peak_at` (the climax note) or 60 %."""
    if isinstance(dyn, str):
        return [(a, dyn)]
    if len(dyn) == 2:
        return [(a, dyn[0]), (max(a, z - 0.25 * (z - a)), dyn[1])]
    p = peak_at if peak_at is not None and a < peak_at < z else a + 0.6 * (z - a)
    return [(a, dyn[0]), (p, dyn[1]), (max(p + 0.5, z - 0.12 * (z - a)), dyn[2])]


_DYN = ('ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff')


def _dyn_order(marks: list, spans: list, two_bars: float) -> list:
    """The dynamic marks [(beat, level)] in order (blind round g4: B1 entering at climax strength in bar 8, a build
    louder than the climax): the climax (the peak section of `spans` [(start, end, section)]) is the loudest - every
    mark outside it at least a level under its loudest mark (a phrase's swell, a subito forte too) - and the first
    chorus enters at mf at most, two levels under the climax, for its first `two_bars` beats."""
    pk = [(a, z) for a, z, sec in spans if sec.get('peak')]
    if not pk:
        return marks
    a, z = pk[0]
    cmax = max((_DYN.index(lv) for t, lv in marks if a - 1e-6 <= t < z - 1e-6 and lv in _DYN), default=None)
    if cmax is None:
        return marks
    b1 = next(((a_, z_) for a_, z_, sec in spans if sec['name'] == 'B1'), None)
    out = []
    for t, lv in marks:
        if lv in _DYN and not a - 1e-6 <= t < z - 1e-6:
            cap = cmax - 1
            if b1 and b1[0] - 1e-6 <= t < min(b1[1], b1[0] + two_bars) - 1e-6:
                cap = min(cap - 1, _DYN.index('mf'))
            lv = _DYN[max(0, min(_DYN.index(lv), cap))]
        out.append((t, lv))
    return out


def _swell(own: list, mel: list, a: float, pa: float, pz: float, amp: int) -> list:
    """One phrase's hairpin over the section's dynamics (plan['swell'] {levels: weight}, drawn per phrase; new-age
    round r3: the references mark every phrase - p, mp at its high note, p at its end - the generated pieces one mark
    per section, 6.5-7 dB within a phrase against 8.7-9.6): marks at the phrase start, its highest note (`amp` levels
    over the section's level there, never over the section's own loudest mark - a quiet section up to mp) and a beat
    before its end, back on the section's level. `own` = the section's marks [(beat, level)], mel its melody (beats
    from the section start a)."""
    ns = [n for n in mel if pa - 1e-6 <= n[0] < pz - 1e-6]
    if not amp or len(ns) < 3:
        return []
    top = min(max(max(ns, key=lambda n: (n[2], n[0]))[0], pa + 1.0), pz - 2.0)
    pts = sorted((t, _DYN.index(lv)) for t, lv in own)

    def at(t):
        if t <= pts[0][0]:
            return pts[0][1]
        for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
            if t0 <= t <= t1:
                return v0 + (v1 - v0) * (t - t0) / max(1e-9, t1 - t0)
        return pts[-1][1]
    cap = max(max(v for _, v in pts), _DYN.index('mp'))     # (round r4: a swell over the section's own peak put
    out = []                                                # the chorus's loudest note over the climax)
    for t, up in ((a + pa, 0), (a + top, amp), (a + pz - 1.0, 0)):
        base = round(at(t))
        out.append((t, _DYN[max(0, min(len(_DYN) - 1, max(base, min(cap, base + up))))]))
    return out


ARRANGE_KEYS = ('bars', 'tail', 'cadence', 'climax', 'reharm', 'octave_half', 'bass', 'fill', 'turn', 'vary', 'key',
                'close')
"""A 'piano' plan section's drawn arrangement options (new-age blind round N0: every generated piece had one grid,
the climax = the chorus louder, the last A = A2 closing on the tonic) - each {choice: weight}, drawn per section with
its own dice (_arrange):
  climax       the peak section's material: 'lift' (its part, one note lifted: Tune.out_melody), 'theme' (the A1
               theme an octave up over its own chords, its second half a sequence of its first a step higher -
               _sequel: the apotheosis), 'climb' (its own part - the chorus - an octave up where it fits, developed
               by _sequel alike), 'step' (its part a whole step up; the bar
               before it pivots into the new key, its own last bar is the home dominant again: _pivot)
  reharm       {share: weight}: that share of the section's chords swapped for substitutes the melody still sings
               over (_reharm, harmony 'reharm'; round r3: the climax on A1's chord chart cell for cell)
  bars         ((first bar, end bar), ...): the part's bars played (a shortened return, a 6-bar build); a span
               played again is an extension: its melody varied (_vary: an ornament / a new rhythm) and half its
               chords reharmonised - a 10- / 12-bar phrase, not a copy
  close        how a section ending on the dominant closes (_close: 'keep', 'I' full, 'vi' deceptive, 'IV' plagal
               half, 'bVII' backdoor, 'ii' open; blind round g2: Vsus4 -> V at every section end)
  tail         bars added at the end, the melody's last note held into them (a 9-bar phrase): a tonic close runs on
               into Vsus4 (a turn into the next section), another chord (the climax's dominant) is held longer
  cadence      'home' / 'vi' / 'IV': the part's closing tonic replaced (a deceptive close the coda resolves)
  octave_half  0 / 1: the first half of the melody an octave up (a return high and soft, then home)
  bass         'root' / 'walk': the chords over a stepwise bass (_walk_bass: a reharmonized return)
  fill         0 / 1: every bar without a right-hand onset (a tail bar, a hole in the build / climax) echoes the last
               bar with 2+ notes on its own chord tones, a held note cut at its bar line (_fill; round r1: whole-bar
               rests and 6-7 beat holds at the peak)
  turn         0 / 1: a closing chord held 2+ bars gets ii - V in its last bar (round r2: every A ended 'X | %')
  vary         {kind: weight}: a return's 2-bar units developed, one kind drawn per unit (VARY, _vary)
  key          {mode: {key: weight}}: the section in another key (KEY_SHIFTS, _modulate; _keys pivots in and out)
  climax 'grow': the hook restated at a new level, sequenced up to the single peak, released (_grow)"""


def _key_pcs(tune: Tune):
    """The tune's key pcs as the composer reads them (RaisedPcs for a genre with melody['raised_v'])."""
    from ..theory import Key
    from .composer import RaisedPcs
    return (RaisedPcs if get(tune.genre).melody.get('raised_v') else set)(Key(tune.key).pcs)


def _key_spans(tune: Tune, plan: list, secs: dict, meter: int, bar: float) -> list:
    """The local key over time [(start, end, pcs)] (the last span over a beat wins - _local_scale): the home key's
    (_key_pcs), a section moved by _modulate ('_key') in its key but for its own last `bar` (home's dominant, _keys)
    and with the bar before it (the new key's dominant), a 'step' climax a whole step up but for its last bar and with
    the bar before it (_pivot). Blind round g1: the hand-off runs, the cadenza and the turns drew on the home key's
    scale over a section in another key."""
    home = _key_pcs(tune)
    x0 = secs[plan[0][0]['name']]
    out = [(x0.start, secs[plan[-1][0]['name']].end + 64 * meter, home)]
    for i, (sec, *_) in enumerate(plan):
        x = secs[sec['name']]
        prev = secs[plan[i - 1][0]['name']] if i else None
        if sec.get('_step'):
            up = {(p + 2) % 12 for p in home}
            out.append((x.start, x.end - meter, up))
            if prev is not None:
                out.append((prev.end - meter, prev.end, up))
        elif sec.get('_key'):
            semis, _, pcs = sec['_key']
            out.append((x.start, x.end - bar, set(pcs)))
            if prev is not None and semis % 12:
                out.append((prev.end - bar, prev.end, set(pcs)))
    return out


def _local_key(spans: list, t: float):
    """The local key's pcs at beat t (_key_spans)."""
    return next((p for a, z, p in reversed(spans) if a - 1e-6 <= t < z - 1e-6), spans[0][2])


def _orn_steps(e, kind: str, kspans: list, timeline: list, key: str):
    """A turn's / mordent's neighbours of event e in the local chord scale: {'upper', 'lower'} semitones for a turn;
    {} for a mordent whose key neighbour (the pianist's: a scale step of `key`) is in it; None when it does not fit
    there (blind round g1: C# as the turn's upper neighbour of C over Cadd9 in E major)."""
    from ..theory import Key
    at = max(e.at, e.at + e.dur - 0.25) if kind == 'turn' else e.at     # (a turn sits late in its note's value)
    sym = _bar_chord(timeline, at, at + 1e-3)
    if sym is None:
        return None
    sc = _local_scale(kspans, at, sym)
    p = e.pitch
    up = next((q for q in (p + 1, p + 2) if q % 12 in sc), None)
    lo = next((q for q in (p - 1, p - 2) if q % 12 in sc), None)
    if up is None or lo is None or p % 12 not in sc:
        return None
    if kind == 'turn':
        return {'upper': up - p, 'lower': lo - p}
    k = Key(key)
    nb = next((q for q in (p - 1, p - 2) if k.contains(q)), None)
    return {} if nb is not None and nb % 12 in sc else None


def _local_scale(spans: list, t: float, sym: str):
    """The pitch classes a figure may use over chord `sym` at beat t: its chord scale in the local key (ChordInfo -
    a borrowed / secondary chord keeps its own scale), with the chord's tones."""
    from .composer import ChordInfo
    ci = ChordInfo(sym, _local_key(spans, t))
    return ci.scale | ci.core


def _last_bar(ch: list, L: float, bar: float, sym: str) -> list:
    """The changes with their last `bar` beats one chord `sym`."""
    out, t = [], 0.0
    for s_, b in ch:
        if t + b <= L - bar + 1e-6:
            out.append((s_, b))
        elif t < L - bar - 1e-6:
            out.append((s_, L - bar - t))
        t += b
    return out + [(sym, bar)]


PIVOTS = {'in': ((2, 'm7'), (9, 'm7'), (5, 'maj7'), (4, 'm7')),
          'out': ((5, 'maj7'), (2, 'm7'), (5, 'm7'), (9, 'm7'), (8, 'maj7'), (3, 'maj7'))}
"""The pivot chords of a key move (_keys; blind round g3, the judges' first fix: 'the climax lurches to an
unprepared remote key and stays there'): (degree over the target tonic, quality) in order of preference - into the
new key its ii / vi / IV / iii, back home the home IV / ii / iv / vi / bVI / bIII - the first whose triad is diatonic
to both keys (the home key with its parallel mode's tones: Fm is the pivot from C into Ab)."""


def _pivot_chord(t_to: int, to_pcs, other_pcs, sharps: bool, way: str):
    """The first PIVOTS[way] chord over the target tonic t_to whose triad lies in both to_pcs and other_pcs, spelled
    (composer.spell); None when there is none."""
    from .composer import spell
    for off, q in PIVOTS[way]:
        r = (t_to + off) % 12
        tri = {r, (r + (3 if q.startswith('m') and not q.startswith('maj') else 4)) % 12, (r + 7) % 12}
        if tri <= set(to_pcs) and tri <= set(other_pcs):
            return spell(r, sharps, (r - t_to) % 12) + q
    return None


def _keys(tune: Tune, plan: list, meter: int, bar: float) -> None:
    """The key plan's way in and out (a section moved by _modulate, '_key'): the bar before it on the new key's
    dominant 7th (a new tonic or a new mode: A minor -> A major on E7 too), its own last bar on the home dominant 7th -
    each bar's melody re-fitted to it. Where the sections are long enough (2+ bars before it, 4+ in it) the bar before
    each dominant is a pivot chord (_pivot_chord: in both keys) - a prepared move over two bars and a prepared way
    home. In place."""
    from ..theory import Key
    from .composer import Harm, _refit, spell
    t_pc = Key(tune.key).tonic % 12
    sharps = _key_sharps(tune.key)
    home = _key_pcs(tune)
    minor = tune.key.split()[1] == 'minor'
    mix = set(home) | {(t_pc + i) % 12 for i in ((4, 9, 11) if minor else (3, 8, 10))}

    def refit(ch, mel, L, pcs, peak, n=1):
        if not mel:
            return mel
        keep = [x for x in mel if x[0] < L - n * bar - 1e-6]
        tail = [x for x in mel if x[0] >= L - n * bar - 1e-6]
        ps = [p for *_, p in mel]
        return keep + _refit(tail, Harm(ch, pcs), meter, min(ps) - 2, max(ps) - (1 if peak else 0),
                             prev=keep[-1][2] if keep else None)
    for i, (sec, ch, mel, L) in enumerate(plan):
        if not sec.get('_key') or L < 2 * bar - 1e-6:
            continue
        semis, new_t, pcs = sec['_key']
        n = 1
        if L >= 4 * bar - 1e-6:
            pv = _pivot_chord(t_pc, mix, pcs, sharps, 'out')
            if pv:
                ch, n = _last_bar(ch, L, 2 * bar, pv), 2
        ch2 = _last_bar(ch, L, bar, spell(t_pc + 7, sharps, 7) + '7')
        plan[i] = (sec, ch2, refit(ch2, mel, L, home, sec.get('peak'), n), L)
        if (semis % 12 or set(pcs) != set(home)) and i > 0:
            # (blind round g4: FBKR's A minor -> A major climax had no dominant - a mode change gets its lead-in too;
            # the pivot after a 2-bar section as well: NYVX's "abrupt" move)
            psec, pch, pmel, pL = plan[i - 1]
            if pL >= 2 * bar - 1e-6:
                off = (semis + 7) % 12
                # (blind round g5: F#7 -> G#m7, the new key's V7 into a section opening on its vi, read as
                # unprepared - the judges: "prepare it with its own dominant, D#7": the lead-in is the dominant of
                # the section's first chord)
                c0 = chord(ch2[0][0]) if ch2 else None
                if c0 is not None and (c0.root - new_t) % 12 not in (0, 7):
                    off = (c0.root + 7 - t_pc) % 12
                n = 1
                if pL >= 2 * bar - 1e-6:
                    pv = _pivot_chord(new_t, pcs, mix, sharps, 'in')
                    if pv:
                        pch, n = _last_bar(pch, pL, 2 * bar, pv), 2
                pch2 = _last_bar(pch, pL, bar, spell(t_pc + off, sharps, off) + '7')
                plan[i - 1] = (psec, pch2, refit(pch2, pmel, pL, pcs, psec.get('peak'), n), pL)


def _key_sharps(key: str) -> bool:
    from .composer import _SHARP_KEYS
    tonic, mode = key.split()
    return tonic in _SHARP_KEYS[mode]


def _transpose_sym(sym: str, semis: int, key: str) -> str:
    """A chord symbol moved by semis: its root spelled by its degree in the new key (composer.spell; the new tonic
    with a '#' when the home key or the new tonic is a sharp key: G# minor, not Ab minor), a slash bass by its
    interval over the root (theory.spell_above: C7/E, not C7/Fb)."""
    import re as _re
    from ..theory import Key, spell_above
    from .composer import _FLATS, _SHARP_KEYS, _SHARPS, spell
    t_pc = Key(key).tonic % 12
    new_t = (t_pc + semis) % 12
    mode = key.split()[1]
    tonic = _SHARPS[new_t] if _key_sharps(key) or _SHARPS[new_t] in _SHARP_KEYS[mode] else _FLATS[new_t]
    sharps = '#' in tonic or tonic in _SHARP_KEYS[mode]
    m = _re.match(r'^([A-G][b#]?)(.*?)(?:/([A-G][b#]?))?$', sym)
    c = chord(sym)
    pc = (c.root + semis) % 12
    root = spell(pc, sharps, (pc - new_t) % 12)
    if not m.group(3):
        return root + m.group(2)
    iv = (chord(m.group(3)).root - c.root) % 12
    steps = {3: 2, 4: 2, 7: 4, 6: 4, 8: 4, 5: 3, 2: 1, 10: 6, 11: 6, 9: 5, 1: 1}.get(iv)
    return root + m.group(2) + '/' + spell_above(root, iv, steps)


def _sung(P: dict) -> bool:
    """A genre with the sung climax (perform._anthem: plan['peak_floor'] and plan['set']['anthem'] - new-age): its
    climax, its returns and its loudness plan follow the new-age judges' rounds (g4 on)."""
    return bool(P.get('peak_floor') and (P.get('set') or {}).get('anthem'))


def _arrange(tune: Tune, sec: dict, ch: list, mel: list, meter: int, ar: random.Random, bar: float | None = None,
             dice=None, pins: dict | None = None, prior=()):
    """The section's drawn arrangement options (ARRANGE_KEYS, through `dice`: the arrangement record) -> (section,
    changes, melody); a climax drawn 'step' marks the returned section dict ('_step') for _pivot. Bar counts (bars /
    tail / turn) are in `bar` beats (default one bar; plan['form_bars']: a form bar - a waltz, its form doubled,
    plays each as two 3/4 bars). The tune's set-level pins (`pins`, default Tune.arrange: composer.set_plan - the
    climax kind) replace that draw (the dice still roll); the record's value wins over both. prior: the theme's
    statements played before this section (a return varies against them too: _vary_changed)."""
    from ..theory import Key
    from .composer import _slice_changes, spell
    t_pc = Key(tune.key).tonic % 12
    minor = tune.key.split()[1] == 'minor'
    sharps = _key_sharps(tune.key)
    bar = bar or meter
    dice = dice or Dice('piano')
    pins = (getattr(tune, 'arrange', None) or {}) if pins is None else pins
    P_ = get(tune.genre).plan

    def pick(k):
        v = _pick(ar, sec[k])
        if k in pins and pins[k] in sec[k]:
            v = pins[k]
        return dice.put(sec['name'], k, v)
    how, step_key = None, False
    # the register's ceiling (plan['ceiling']; HUMAN_FEEDBACK 2026-10-15: "too many very high notes"): an octave-up
    # climax / theme only where its line stays at or under 'peak' (else grown from the hook), every peak under it
    cap = (P_.get('ceiling') or {}).get('peak')
    # (the sung theme, _anthem: a genre with plan['set']['anthem'] - new-age; the others keep the octave-up theme
    # and the grown fallback)
    sung_ok = _sung(P_)
    if sec.get('climax'):
        how = pick('climax')
        if how in ('lift', 'grow', 'climb') and sung_ok:
            how = 'theme'                              # (blind round g5: BGME's 'lift' left the key with the
            #                                            chorus, no theme - the sung theme is this genre's lift;
            #                                            round g10: KVRY's grown climax "new material", all five)
        step_key = how == 'step' and sung_ok
        if step_key:                                   # (round g7: GVPE's 'step' climax a new tune in G#m - the
            how = 'theme'                              # sung theme, moved a whole step up by the key plan: _keys
            #                                            prepares the move in and the way home)
        if how == 'theme' and sung_ok:
            # (blind round g4: the theme at the climax - the A1's chords, its head phrase and its head at the peak:
            # _anthem below, once the key is drawn)
            ch = list(tune.changes[tune.parts[0]])
            if sec.get('part') == tune.parts[0] and bar == meter and sum(b for _, b in ch) <= 8 * meter + 1e-6:
                # (round g9: LXAN's variation climax, 8 bars with no build before it - "short, low, no build": a
                # climax on the theme itself - the layout without a build - sings 12 bars, its statements climbing
                # over the whole theme before the head's peak: ANTHEM_GROW)
                ch = ch + _slice_changes(ch, 0, ANTHEM_GROW * meter)
        elif how in ('theme', 'climb'):
            # theme: the A1 an octave up (the apotheosis); climb: the section's own part (the chorus) an octave up
            # where that fits under C7, else in place - both developed: the first half kept, the second half a
            # sequence of it a step higher (_sequel)
            src = tune.parts[0] if how == 'theme' else sec['part']
            notes = tune.melody.get(src) or []
            top_ = max((p for _, _, p in notes), default=0)
            up = 12 if (how == 'theme' and (cap is None or top_ + 14 <= cap)) or                 (notes and top_ + 12 <= (cap - 2 if cap else 93)) else 0
            if not up and P_.get('peak_floor'):
                how = 'theme' if sung_ok else 'grow'   # (round r9: the chorus in place, a copy - grown instead;
                if sung_ok:                            # round g4: the theme instead)
                    ch = list(tune.changes[tune.parts[0]])
            elif notes and top_ + up <= (cap or 96):
                ch, mel = list(tune.changes[src]), [(st, du, p + up) for st, du, p in notes]
                mel = _sequel(ch, mel, meter, Key(tune.key).pcs, cap or 96)
                top = max(p for _, _, p in mel)            # one peak: the top struck once (the latest one; the
                last = max(i for i, n in enumerate(mel) if n[2] == top)    # others a scale step lower)
                pcs = Key(tune.key).pcs
                mel = [(st, du, p - (2 if (p - 2) % 12 in pcs else 1)) if p == top and i != last else (st, du, p)
                       for i, (st, du, p) in enumerate(mel)]
        elif how == 'lift' and mel and max(p for _, _, p in mel) + 12 <= (cap or 91):
            mel = [(st, du, p + 12) for st, du, p in mel]     # (round r7: a low chorus's lifted line stayed under
            #                                                     the build - a climax made by velocity alone)
        elif how == 'lift' and mel and P_.get('peak_floor'):
            how = 'theme' if sung_ok else 'grow'       # (round r9: no room for the lift - the chorus copied in place;
            if sung_ok:                                # round g4: the theme instead)
                ch = list(tune.changes[tune.parts[0]])
        elif how == 'step':
            ch = [(_transpose_sym(sym, 2, tune.key), b) for sym, b in ch]
            mel = [(st, du, p + 2) for st, du, p in mel]
            sec = dict(sec, _step=True)
    moving = None
    if how == 'theme' and sung_ok and sec.get('climax') and step_key and _key_named(tune.key, 'step'):
        moving = 'step'                                # (derived from the recorded climax kind, not a key draw)
    elif sec.get('key') and not sec.get('_step') and ch:
        # the section in another key (KEY_SHIFTS; moved below, _keys leads in and back): one with a written key
        # signature; a peak section's line stays under G6 (_fold: the line moves to the nearer octave)
        top_ = max(p for *_, p in mel) if mel and sec.get('peak') and how != 'grow' and \
            not (how == 'theme' and sung_ok) else None
        w = {k: v for k, v in sec['key'][tune.key.split()[1]].items() if _key_named(tune.key, k)
             and (top_ is None or top_ + _fold(KEY_SHIFTS[k][0]) <= (cap or 91))} or {'home': 1.0}
        arr = pins.get('arrival') if sung_ok and sec.get('peak') else None
        if sung_ok and sec.get('peak') and how == 'theme':
            # (round g13: SUNG_KEYS - the sung head keeps its own degrees, a step up or the parallel major)
            near = {k: 1.0 for k in SUNG_KEYS[tune.key.split()[1]] if _key_named(tune.key, k)}
            w = ({k: v for k, v in w.items() if k == 'home'} or {'home': 1.0}) | \
                ({k: v for k, v in w.items() if k in near} or ({} if arr != 'key' else near))
        if arr == 'key':                               # (round g9: the climax's arrival a set draw - ARRIVALS: the
            w = {k: v for k, v in w.items() if k != 'home'} or w      # key move is this piece's way in; the
        elif arr in ARRIVALS and 'home' in w:                         # others arrive at home)
            w = {'home': 1.0}
        moving = dice.put(sec['name'], 'key', _pick(random.Random(f"key:{tune.seed}:{sec['name']}"), w))
    if how == 'grow' and ch:
        # grown from the hook over the section's own chords, to a peak over every head note (_grow) - in the key the
        # section moves to: its peak where the move puts it
        top = max(p for m_ in tune.melody.values() for _, _, p in m_)
        up = _fold(KEY_SHIFTS.get(moving, (0, None))[0]) if moving else 0
        aug = random.Random(f"grow-aug:{tune.seed}").random() < P_.get('grow_aug', 0.0)
        g_at = pins.get('_pdiv_at') or _pick(random.Random(f"grow-at:{tune.seed}"), P_.get('grow_at') or {0.6: 1.0})
        grown = _grow(ch, tune.motif or tune.melody[tune.parts[0]], meter, _key_pcs(tune),
                      min(cap or 91, top + 2) - up, aug=aug, at=g_at)
        if grown:
            mel = grown
    treat = None
    if how == 'theme' and ch and sung_ok:
        # the theme stated at the climax (_anthem; blind round g4) - how: the set slot's draw (plan['set']['anthem'])
        top = max(p for m_ in tune.melody.values() for _, _, p in m_)
        up = _fold(KEY_SHIFTS.get(moving, (0, None))[0]) if moving else 0
        treat = pins.get('anthem') if pins.get('anthem') in ANTHEMS else             _pick(random.Random(f"anthem:{tune.seed}"), (P_.get('set') or {}).get('anthem') or {'octaves': 1.0})
        g_at = pins.get('_pdiv_at') or _pick(random.Random(f"grow-at:{tune.seed}"), P_.get('grow_at') or {0.6: 1.0})
        # (blind round g5, every judge's first fix: the theme sung in A1's own register - the whole climax line an
        # octave over the theme where its head fits under plan['ceiling']['sung'], the C6 band)
        sung_cap = (P_.get('ceiling') or {}).get('sung')
        head_top = max((p for st_, _, p in tune.melody[tune.parts[0]] if st_ < 2 * meter - 1e-6), default=None)
        octave = 12 if sung_cap and head_top is not None and head_top + 12 <= sung_cap - up else 0
        # (the peak a step or two over the sung theme's own top, not the ceiling every time)
        a_top = max(p for _, _, p in tune.melody[tune.parts[0]])
        # (round g11: the set's peaks spread under the ceiling - plan['set']['peak'], semitones; nine of eleven g10
        # climaxes peaked on A6 / Ab6)
        drop = pins.get('peak') if isinstance(pins.get('peak'), int) else 0
        if octave:                                     # (as far as the head sung an octave up stays under it)
            drop = max(0, min(drop, sung_cap - up - head_top - 12))
        sung = _anthem(ch, tune.melody[tune.parts[0]], meter, _key_pcs(tune),
                       (min(sung_cap - drop, a_top + 14) if octave else min(cap or 91, top + 2)) - up, how=treat,
                       at=g_at,
                       ceiling=(sung_cap if octave else cap or 91) - up, octave=octave, arrive=pins.get('arrival'),
                       shift=up, second=pins.get('second'),
                       out_units=2 if pins.get('_pdiv_at') and pins['_pdiv_at'] < 0.5 else None)
        if sung:
            ch, mel = sung
            sec = dict(sec, _anthem=treat)
            table = (get(tune.genre).harmony.get('reharm') or {}).get(tune.key.split()[1])
            if ANTHEM_HEAD['open'] == 'reharm' and not up and table and ch:
                # (round g14: at home the head opens the climax over new chords - "A1 replayed louder" at A1's
                # pitches over A1's chords, MYUS / GALR / CPED / QTNU; after a key move the key is the change)
                t_, first = 0.0, set()
                for i_, (_, b_) in enumerate(ch):
                    if t_ < 2 * meter - 1e-6:
                        first.add(i_)
                    t_ += b_
                ch = _reharm(ch, sorted(mel), tune.key, table, 1.0, meter, random.Random(f"clx-open:{tune.seed}"),
                             only=first)
        else:
            grown = _grow(ch, tune.motif or tune.melody[tune.parts[0]], meter, _key_pcs(tune),
                          min(cap or 91, top + 2) - up, at=g_at)
            how, mel = 'grow', grown or mel
    if sec.get('reharm') and not sec.get('_step') and ch:
        share = pick('reharm')
        if sec.get('_post') or sec.get('_pre'):        # (the return after the climax on new chords: POST_RETURN;
            share = max(share or 0.0, POST_RETURN['reharm'])    # round g8: a return before it too - LXCD 24-26)
        if sec.get('_anthem') == 'reharm':
            share = 1.0                                # (the theme over new chords: every chord the line allows)
        table = (get(tune.genre).harmony.get('reharm') or {}).get(tune.key.split()[1])
        if share and table:
            new_ch = _reharm(ch, sorted(mel), tune.key, table, share, meter, ar)
            if sec.get('_anthem') and mel:
                # (round g7: QNFS's reharmonised theme in a new key heard as "an arpeggio, not the theme" - the
                # head's own chords kept where it is stated first and at the peak)
                u_ = 2 * meter
                top = max(mel, key=lambda x: (x[2], -x[0]))
                keep = {0, int(top[0] // u_)}
                n_ = int(round(sum(b for _, b in ch) / u_))
                spans = [c for k in range(n_) for c in _slice_changes(ch if k in keep else new_ch, k * u_,
                                                                       (k + 1) * u_)]
                spans += _slice_changes(new_ch, n_ * u_, sum(b for _, b in ch))
                new_ch = []
                for sym, b in spans:                   # (a chord split at a unit's bar line: one chord again)
                    if new_ch and new_ch[-1][0] == sym:
                        new_ch[-1] = (sym, new_ch[-1][1] + b)
                    else:
                        new_ch.append((sym, b))
            ch = new_ch
    if (sec.get('peak') or sung_ok and sec['name'][0] == 'B') and P_.get('unswing') and ch and mel             and not sec.get('_step'):
        # (round r10: a climax rocking between two chords, Bbm7 Abmaj7 Bbm7 Abmaj7 - the third of such a run takes
        # a substitute under its melody; its own dice; round g12, three judges: WNTP / CNWE's chorus "long notes
        # over a two-chord seesaw" - a sung genre's chorus too)
        table = (get(tune.genre).harmony.get('reharm') or {}).get(tune.key.split()[1])
        if table:
            ch = _unswing(ch, sorted(mel), tune.key, table, meter, random.Random(f"swing:{tune.seed}:{sec['name']}"))
    if sec.get('vary') and mel and ch and how != 'grow' and not sec.get('_anthem'):
        # a return developed unit by unit (VARY; its own dice: the other draws stay where they were) - a climax
        # restating the chorus / the theme too (round r9: the climax = the chorus transposed); a grown one is new
        units = int(round(sum(b for _, b in ch) / (2 * meter)))
        kinds = _vary_draw(sec, units, random.Random(f"vary:{tune.seed}:{sec['name']}"))
        sung_ret = sung_ok and sec['name'] in RETURNS
        if sec.get('_post') and kinds:
            kinds[0] = POST_RETURN['head']             # (the return after the climax: its head changed too)
        elif (sec.get('_pre') or sung_ret) and kinds and kinds[0] in ('keep', 'orn'):
            kinds[0] = 'rhythm'                        # (round g8: a return before the climax - LXCD 24-26 = 4-6 -
            #                                            its head re-rhythmed, no bar copied; round g9: ZACW's A2 /
            #                                            A3 heads "note for note" with an ornament - every sung return)
        kinds = dice.put(sec['name'], 'vary', kinds)
        src_mel = mel
        whole = sec.get('_post') or sec.get('_pre') or sung_ret
        if sec['name'] in RETURNS and (units >= 3 or whole):     # (a return's second half audibly rewritten:
            mel = _vary_changed(ch, mel, meter, _key_pcs(tune), kinds,      # _vary_changed; the whole of it around
                                only=range(1 if sung_ret and sec.get('_post') else 0 if whole else units // 2,
                                           units), land=True,                                # the climax)
                                size=1 + RETURNS.index(sec['name']) // 2,
                                head=bool(sec.get('_pre')) or sung_ret, prior=prior if sung_ret else ())
            # (round g10: a sung genre's return after the climax states the head - ornamented over its new chords,
            # FCJZ / JRCY's A2 "filler instead of the head", three judges: POST_RETURN)
        else:
            mel = _vary(ch, mel, meter, _key_pcs(tune), kinds)
        if sung_ret and mel and sec['name'] in HEAD_RETURN:    # (round g13: the head's own bars vary on return)
            mel = _head_turn(ch, mel, src_mel, meter, _key_pcs(tune), HEAD_RETURN[sec['name']])
        if sec.get('peak') and mel:
            from .composer import Harm
            mel = _single_top(sorted(mel), Harm(ch, _key_pcs(tune)))
    if moving:
        moved = _modulate(tune, ch, mel, meter, moving, single=bool(sec.get('peak')), refit=not sec.get('_anthem'))
        if moved:
            ch, mel, k_ = moved
            sec = dict(sec, _key=k_)
    if sec.get('bars'):
        if bar > meter and isinstance(sec['bars'], dict):
            # (a waltz plays its form bars twice as long: no extension - blind round g5, QJUG 129 bars, a 20-bar
            # build vamping Asus4 | A)
            plain = {k: w for k, w in sec['bars'].items()
                     if all(a_ >= max((b_ for _, b_ in k[:i]), default=0) for i, (a_, _) in enumerate(k))}
            sec = dict(sec, bars=plain or sec['bars'])
        spans, ch0, mel0 = pick('bars'), ch, mel
        ch, mel, off, seen = [], [], 0.0, 0.0
        for a, b in spans:
            c_ = _slice_changes(ch0, a * bar, b * bar)
            m_ = [(st - a * bar, du, p) for st, du, p in mel0 if a * bar - 1e-6 <= st < b * bar - 1e-6]
            if a * bar < seen - 1e-6 and c_:
                # an extension (bars played again): varied and half reharmonised (blind round g2: 8 + 1 bars in
                # every section) - its own dice
                xr = random.Random(f"extend:{tune.seed}:{sec['name']}:{a}")
                table = (get(tune.genre).harmony.get('reharm') or {}).get(tune.key.split()[1])
                if table and m_:
                    c_ = _reharm(c_, sorted(m_), tune.key, table, 0.5, meter, xr)
                units = int(round((b - a) * bar / (2 * meter)))
                # (blind round g3: 'orn' / 'rhythm' left 4-bar blocks verbatim or one note changed - PBQV 46-49 =
                # 50-53: a unit turned over or sequenced, each unit audibly changed - _vary_changed)
                kinds = [xr.choice(('invert', 'rhythm') if k == 0 else ('seq', 'invert')) for k in range(units)]
                m_ = _vary_changed(c_, m_, meter, _key_pcs(tune), kinds) if m_ else m_
            ch += c_
            mel += [(st + off, du, p) for st, du, p in m_]
            off += (b - a) * bar
            seen = max(seen, b * bar)
    if sec.get('tail') and not sec.get('_final'):
        n = pick('tail')
        if n and ch:                                   # (a tonic close runs on into a Vsus4 - the held tonic is its
            ch = ch + [(spell(t_pc + 7, sharps, 7) + 'sus4', n * bar)] if chord(ch[-1][0]).root % 12 == t_pc \
                else ch[:-1] + [(ch[-1][0], ch[-1][1] + n * bar)]                 # 4th; a dominant is held)
            if mel:
                last = max(mel)
                mel = [x for x in mel if x != last] + [(last[0], last[1] + n * bar, last[2])]
    if sec.get('close') and ch:
        ch, mel = _close(tune, ch, mel, pick('close'), meter, bar)
    if sec.get('_final') and ch:                       # (round g11: the last A cadences home - FINAL_A)
        ch, mel = _close(tune, ch, mel, FINAL_A['close'], meter, bar, force=True)
    elif sec.get('cadence'):
        how = pick('cadence')
        if how != 'home' and ch and chord(ch[-1][0]).root % 12 == t_pc:
            off = {'vi': 8 if minor else 9, 'IV': 5}[how]
            q = {'vi': 'maj7' if minor else 'm7', 'IV': 'm7' if minor else 'maj7'}[how]
            ch = ch[:-1] + [(spell(t_pc + off, sharps, off) + q, ch[-1][1])]
    if sec.get('bass') and pick('bass') == 'walk':
        ch = _walk_bass(ch)
    if sec.get('octave_half') and mel and pick('octave_half'):
        half = sum(b for _, b in ch) / 2
        mel = [(st, du, p + 12 if st < half - 1e-6 else p) for st, du, p in mel]
    if sec.get('turn') and not sec.get('_final') and ch and pick('turn') and ch[-1][1] >= 2 * bar - 1e-6:
        # a closing chord held 2+ bars: its last bar becomes ii - V (a written cadence / turnaround into the next
        # section, not 'X | %')
        sym, b = ch[-1]
        ii = spell(t_pc + 2, sharps, 2) + ('m7b5' if minor else 'm7')
        ch = ch[:-1] + [(sym, b - bar), (ii, bar / 2), (spell(t_pc + 7, sharps, 7) + '7', bar / 2)]
    if sung_ok and 'part' in sec and ch and not sec.get('peak'):    # (round g9: no 3+ bars on one chord - ZACW
        #                                                                 15-18; the sung climax keeps its chords)
        ch, mel = _destall(tune, ch, mel, meter, bar)
    if sec.get('fill') and mel:
        if pick('fill'):
            mel = _fill(ch, sorted(mel), meter)
        elif sung_ok:                                  # (round g8: a sung genre fills the holes inside a phrase -
            mel = _fill(ch, sorted(mel), meter, ends=8 if bar > meter else 4)   # KTBL 20 / 22; its ends breathe)
    if sec.get('peak') and mel and ch:
        # (round g10: NMPC's / LMUP's sung head opened on beat 2 - moved onto the downbeat, its pickup and first step
        # were lost, "a new cell": the sung theme keeps an entry within its bar's first half)
        mel = _downbeats(ch, sorted(mel), meter, late=meter / 2 if sec.get('_anthem') else 1.0)
    return dict(sec), ch, sorted(mel)


def _downbeats(ch: list, mel: list, meter: int, late: float = 1.0) -> list:
    """The climax's melody on its downbeats (blind round g3, all five judges: the right hand entered on beat 4 of
    every other climax bar while the left hand's 16ths carried the peak): every bar whose first onset comes `late`
    beats or more after its downbeat gets that note on the downbeat (lengthened by as much; a tone of the chord there,
    the nearest one when it was none); a note held into the bar is cut at the bar line. Bars without an onset stay
    (_fill)."""
    total = sum(b for _, b in ch)
    starts, t = [], 0.0
    for sym, b in ch:
        starts.append((t, b, chord(sym)))
        t += b

    def tones(x):
        c = next((c for a, b, c in starts if a - 1e-6 <= x < a + b - 1e-6), starts[-1][2])
        return {(c.root + i) % 12 for i in c.intervals}
    out = sorted(mel)
    for k in range(int(round(total / meter))):
        a = k * meter
        inbar = [i for i, n in enumerate(out) if a - 1e-6 <= n[0] < a + meter - 1e-6]
        if not inbar or out[inbar[0]][0] < a + late - 1e-6:
            continue
        i = inbar[0]
        st, du, p = out[i]
        pcs = tones(a + 1e-3)
        if p % 12 not in pcs:
            p = min((q for q in range(p - 4, p + 5) if q % 12 in pcs), key=lambda q: (abs(q - p), -q), default=p)
        out[i] = (a, du + (st - a), p)
        out = [(s_, a - s_ if s_ < a < s_ + d_ - 1e-6 else d_, p_) if j < i else (s_, d_, p_)
               for j, (s_, d_, p_) in enumerate(out)]
    return out


def _vary_changed(ch: list, mel: list, meter: int, key_pcs, kinds: list, only=None, land: bool = False,
                  size: int = 1, head: bool = False, prior=()) -> list:
    """_vary with every unit audibly changed (an extension - bars played again: blind round g3, 4-bar blocks copied
    verbatim or with one note changed): a unit whose notes (onset, pitch) still match the source in 3 of 4 tries the
    other kinds ('invert', 'seq', 'rhythm', 'orn') until one moves it; kinds unchanged where none does. only: the
    units checked (default all); land / size: _vary's; head: the first unit is the theme's head - only its rhythm or
    its ornaments change (its pitches recognisable: round g8). A unit that sinks - its mean pitch more than RETURN_SINK
    semitones under the source's - tries the other kinds too (round g8: JTQL's A3 at F#4-G4, a sequence down).
    prior: the theme's statements played before it (melodies from their sections' starts): a unit past the head with
    a bar that copies one of their bars - at any place, its top line on an 8th grid (VARIED) - is changed too, by
    the other kinds and then a wider sequence (round g11: HJJR's A3 / A4 = A2's bars, the g10 statistician's copies
    in five pieces - each return varied against its source alone came out as the return before it)."""
    unit = 2 * meter

    def mean_p(ns, k):
        ps = [p for st, du, p in ns if k * unit - 1e-6 <= st < (k + 1) * unit - 1e-6]
        return sum(ps) / len(ps) if ps else None

    def sunk(ns, k):
        x, y = mean_p(ns, k), mean_p(mel, k)
        return x is not None and y is not None and x < y - RETURN_SINK

    def sig(ns, k):
        return {(round(4 * st), p) for st, du, p in ns if k * unit - 1e-6 <= st < (k + 1) * unit - 1e-6}

    def same(x, y):
        return bool(y) and len(x & y) >= 0.75 * max(len(x), len(y))

    def bar(ns, b):
        return {(round(4 * st), p) for st, du, p in ns if b * meter - 1e-6 <= st < (b + 1) * meter - 1e-6}

    def top8(ns, b):                                   # (a bar's top line from its downbeat, 8th grid: the tells')
        tops = {}
        for st, du, p in ns:
            if b * meter - 0.1 <= st < (b + 1) * meter - 0.1:
                tops[round(2 * (st - b * meter))] = max(p, tops.get(round(2 * (st - b * meter)), 0))
        return set(tops.items())
    seen = [x for ns in prior for b in range(int(max((st for st, *_ in ns), default=0) // meter) + 1)
            for x in [top8(ns, b)] if len(x) >= 2]

    def copied(ns, k):                                 # (round g8: a bar of the unit as written - LXCD 24-26 = 4-6,
        if same(sig(ns, k), sig(mel, k)) or any(      # a unit whose other bar moved)
                len(bar(mel, b)) >= 2 and same(bar(ns, b), bar(mel, b)) for b in (2 * k, 2 * k + 1)):
            return True
        return bool(seen) and not (head and k == 0) and any(    # (round g11: a bar of a statement before it)
            len(x) >= 2 and any(len(x & y) >= VARIED * len(x | y) for y in seen)
            for x in (top8(ns, 2 * k), top8(ns, 2 * k + 1)))
    sizes = [size] * len(kinds)
    out = _vary(ch, mel, meter, key_pcs, kinds, land=land, size=size, head=head)
    for k in (range(len(kinds)) if only is None else only):
        if not copied(out, k) and not sunk(out, k):
            continue
        alts = [(a_, size) for a_ in (('rhythm', 'orn') if head and k == 0 else ('invert', 'seq', 'rhythm', 'orn'))]
        if seen and not (head and k == 0):
            alts += [('seq', size + 1), ('seq', size + 2)]
        for alt, sz in alts:
            ks, ss = list(kinds), list(sizes)
            ks[k], ss[k] = alt, sz
            new = _vary(ch, mel, meter, key_pcs, ks, land=land, size=ss, head=head)
            if not copied(new, k) and not sunk(new, k):
                out, kinds, sizes = new, ks, ss
                break
    return out


VARIED = 0.7
"""_vary_changed's copy of an earlier statement's bar: the top lines' (onset on an 8th grid, pitch) Jaccard at least
this (the blind tells' measure, songs/_blind/tells_newage.py ret_bars_copy)."""


STALL = 3
"""Bars on one chord root a sung section plays at most before its harmony moves (_destall; round g9, four judges:
ZACW's A2 on Am/C for four bars, the same cell twice - an extension replaying a cadence's 'Vsus4 | V')."""


def _destall(tune: Tune, ch: list, mel: list, meter: int, bar: float) -> tuple:
    """The changes with no run of STALL+ bars on one root (a sus / inversion / 7th counts as the same chord): every
    second bar inside such a run (never its last) takes the key's chord a fifth over the root (V - ii - V, I - V - I),
    the melody there re-fitted to it -> (changes, melody)."""
    from ..theory import Key
    from .composer import Harm, _refit, _slice_changes, spell
    total = sum(b for _, b in ch)
    nb = int(round(total / bar))
    if nb < STALL or not ch:
        return ch, mel

    def root(k):
        cs = _slice_changes(ch, k * bar, (k + 1) * bar)
        rs = {chord(s_.split('/')[0]).root % 12 for s_, _ in cs}
        return next(iter(rs)) if len(rs) == 1 else None
    roots = [root(k) for k in range(nb)]
    swap, k = set(), 0
    while k < nb:
        j = k
        while j + 1 < nb and roots[k] is not None and roots[j + 1] == roots[k]:
            j += 1
        if roots[k] is not None and j - k + 1 >= STALL:
            swap |= set(range(k + 1, j, 2))
        k = j + 1
    if not swap:
        return ch, mel
    pcs = set(_key_pcs(tune))
    t_pc = Key(tune.key).tonic % 12
    sharps = _key_sharps(tune.key)
    out = []
    for k in range(nb):
        if k in swap:
            r = (roots[k] + 7) % 12
            q = 'm7' if (r + 3) % 12 in pcs and (r + 4) % 12 not in pcs else ''
            out.append((spell(r, sharps, (r - t_pc) % 12) + q, bar))
        else:
            out += _slice_changes(ch, k * bar, (k + 1) * bar)
    out += _slice_changes(ch, nb * bar, total)
    new = []
    for s_, b in out:                                  # (a chord split at a bar line: one chord again)
        if new and new[-1][0] == s_:
            new[-1] = (s_, new[-1][1] + b)
        else:
            new.append((s_, b))
    if mel:
        harm = Harm(new, _key_pcs(tune))
        lo, hi = min(p for *_, p in mel) - 2, max(p for *_, p in mel)
        mel = sorted(mel)
        for k in sorted(swap):
            idx = [i for i, n in enumerate(mel) if k * bar - 1e-6 <= n[0] < (k + 1) * bar - 1e-6]
            if idx:
                fit = _refit([mel[i] for i in idx], harm, meter, lo, hi, prev=mel[idx[0] - 1][2] if idx[0] else None)
                for i, n in zip(idx, fit):
                    mel[i] = n
    return new, mel


RETURN_SINK = 3.0
"""A varied unit's mean pitch at most this many semitones under the unit as written (_vary_changed; round g8: the
returns sinking to the 4th octave - JTQL A3 F#4-G4, VJGT)."""


def _close(tune: Tune, ch: list, mel: list, how: str, meter: int, bar: float, force: bool = False) -> tuple:
    """A section's close (ARRANGE_KEYS 'close'): when its last chord is the dominant, its last bar becomes the drawn
    close - 'I' V7 then the tonic, 'vi' V7 then vi (minor: bVI), 'IV' the subdominant (minor: iv7), 'bVII' the
    flat seventh, 'ii' ii7 (minor: iiø) - and the melody in that bar is re-fitted to it. Else unchanged. force: the
    close whatever the last chord is (but the tonic already: FINAL_A)."""
    from ..theory import Key
    from .composer import Harm, _refit, spell
    t_pc = Key(tune.key).tonic % 12
    minor = tune.key.split()[1] == 'minor'
    sharps = _key_sharps(tune.key)
    L = sum(b for _, b in ch)
    last = chord(ch[-1][0].split('/')[0]).root % 12
    if how == 'keep' or L < 2 * bar - 1e-6 or (last != (t_pc + 7) % 12 if not force else last == t_pc):
        return ch, mel

    def nm(off, q):
        return spell(t_pc + off, sharps, off) + q
    v7, half = nm(7, '7'), bar / 2
    new = {'I': [(v7, half), (nm(0, 'm' if minor else ''), bar - half)],
           'vi': [(v7, half), (nm(8, 'maj7') if minor else nm(9, 'm7'), bar - half)],
           'IV': [(nm(5, 'm7') if minor else nm(5, 'maj7'), bar)],
           'bVII': [(nm(10, '') if minor else nm(10, 'add9'), bar)],
           'ii': [(nm(2, 'm7b5') if minor else nm(2, 'm7'), bar)]}[how]
    ch2 = _last_bar(ch, L, bar, new[0][0])[:-1] + new
    keep = [n for n in mel if n[0] < L - bar - 1e-6]
    tail = [n for n in mel if n[0] >= L - bar - 1e-6]
    if not tail:
        return ch2, mel
    ps = [p for *_, p in mel]
    pcs = set(_key_pcs(tune)) | ({(t_pc + 10) % 12} if how == 'bVII' and not minor else set())
    return ch2, keep + _refit(tail, Harm(ch2, pcs), meter, min(ps) - 2, max(ps),
                              prev=keep[-1][2] if keep else None)


_DEGREES = {0: 'I', 1: 'bII', 2: 'II', 3: 'bIII', 4: 'III', 5: 'IV', 6: '#IV', 7: 'V', 8: 'bVI', 9: 'VI', 10: 'bVII',
            11: 'VII'}


def _reharm(ch: list, mel: list, key: str, table: dict, share: float, meter: int, rng: random.Random,
            only=None) -> list:
    """The section's chords re-chosen under its melody (new-age round r3: the climax = A1's chord chart cell for cell,
    the references' climax brings its own harmony): each chord but the closing ones (the last bar, a sus4 cadence)
    with chance `share` swapped for a substitute of its degree (harmony 'reharm' {mode: {'VIm': {token: weight}}},
    a source = its degree + 'M' / 'm'), drawn among those under which the melody still sings: every note struck on a
    beat or held a beat+ (and a note held into the chord) a chord tone or tension of the substitute. Never on the root
    of the chord before or after it (but a sus4's resolution may move: Gsus4 G/B), never a third time in the section.
    The melody stays. only: the indices of the chords that may change (None: every chord)."""
    from ..theory import Key
    from .composer import ChordInfo, chord_name, parse_block
    k = Key(key)
    t_pc, pcs, sharps = k.tonic % 12, k.pcs, _key_sharps(key)
    total = sum(b for _, b in ch)
    spans, t = [], 0.0
    for sym, b in ch:
        spans.append((t, b, sym))
        t += b
    out = []
    for i, (t0, b, sym) in enumerate(spans):
        c = chord(sym)
        src = _DEGREES[(c.root - t_pc) % 12] + ('m' if c.is_minor else 'M')
        cand = table.get(src)
        nxt = spans[i + 1][2] if i + 1 < len(spans) else None
        if not cand or 'sus' in sym or t0 >= total - meter - 1e-6 or (only is not None and i not in only) \
                or rng.random() >= share:
            out.append((sym, b))
            continue
        ok = {}
        for tok, w in cand.items():
            off, q, _ = parse_block(tok)[0]
            new = chord_name(t_pc, off, q, sharps)
            near = [x for x in ([out[-1][0]] if out else []) + ([nxt] if nxt else []) if 'sus' not in x]
            if new == sym or chord(new).root % 12 in {chord(x).root % 12 for x in near}:
                continue
            if [x for x, _ in out].count(new) + [x for _, _, x in spans[i + 1:]].count(new) >= 2:
                continue                               # (round r4: C/E three times in five climax bars)
            ci = ChordInfo(new, pcs)
            good = ci.core | ci.tensions
            sing = True
            for st, du, p in mel:
                if st + du <= t0 + 0.5 or st >= t0 + b - 1e-6:
                    continue
                strong = st < t0 + 1e-6 or abs(st - round(st)) < 0.05 or du >= 1.0 - 1e-6
                if p % 12 not in (good if strong else ci.scale):
                    sing = False
                    break
            if sing:
                ok[new] = w
        out.append((_pick(rng, ok), b) if ok else (sym, b))
    return out


def _unswing(ch: list, mel: list, key: str, table: dict, meter: int, rng: random.Random) -> list:
    """No two chords rocking back and forth (X Y X Y by root): the third chord of such a run - else the fourth - takes
    a substitute under the melody (_reharm, only that chord); a run with no substitute stays."""
    def root(s):
        return chord(s).root % 12
    for _ in range(len(ch)):
        run = next((i for i in range(len(ch) - 3) if root(ch[i][0]) == root(ch[i + 2][0]) != root(ch[i + 1][0])
                    == root(ch[i + 3][0])), None)
        if run is None:
            return ch
        new = _reharm(ch, mel, key, table, 1.0, meter, rng, only={run + 2})
        if new == ch:
            new = _reharm(ch, mel, key, table, 1.0, meter, rng, only={run + 3})
        if new == ch:
            return ch
        ch = new
    return ch


def _sequel(ch: list, mel: list, meter: int, key_pcs, ceiling: int) -> list:
    """The theme's apotheosis developed (new-age round r2: the climax = A1 an octave up, note for note): its first
    half kept, its second half the first half's notes again a scale step higher (a sequence climbing to a new peak),
    each note on a beat moved to the nearest tone of the chord under it, the others to the nearest key tone; unchanged
    when the sequence would pass `ceiling`."""
    total = sum(b for _, b in ch)
    half = total / 2
    starts, t = [], 0.0
    for sym, b in ch:
        starts.append((t, b, chord(sym)))
        t += b

    def under(x):
        return next((c for a, b, c in starts if a - 1e-6 <= x < a + b - 1e-6), starts[-1][2])
    head = [n for n in mel if n[0] < half - 1e-6]
    if len(head) < 3:
        return mel
    out, prev = list(head), None
    for st, du, p in head:
        st2 = st + half
        target = p + (2 if (p + 2) % 12 in key_pcs else 1)
        on_beat = abs(st2 - round(st2)) < 1e-6
        c = under(st2 + 1e-3)
        pcs = {(c.root + i) % 12 for i in c.intervals} if on_beat else set(key_pcs)
        q = min([x for x in range(target - 6, target + 7) if x % 12 in pcs] or [target],
                key=lambda x: (abs(x - target), x))
        if prev is not None and q == prev[1] and p != prev[0]:      # (keep the head's motion: no new unisons)
            q = min([x for x in range(target - 6, target + 7) if x % 12 in pcs and x != prev[1]] or [q],
                    key=lambda x: (abs(x - target), x))
        out.append((st2, du, q))
        prev = (p, q)
    if max(p for _, _, p in out) > ceiling:
        return mel
    return [(st, min(du, total - st), p) for st, du, p in out]


def _fill(ch: list, mel: list, meter: int, ends: int | None = None) -> list:
    """The melody with each bar that has no onset (a held note or a rest all bar) filled: the last bar before it
    with 2+ onsets again, each note moved to the nearest tone of the chord sounding under it (a written lead-in /
    echo, not a hole); a note held into the bar is cut at its bar line. ends: a phrase's length in bars - its last
    bar and the section's last bar left as they are (the breath)."""
    total = sum(b for _, b in ch)
    n_bars = int(round(total / meter))
    starts, t = [], 0.0
    for sym, b in ch:
        starts.append((t, b, chord(sym)))
        t += b

    def under(x):
        return next((c for a, b, c in starts if a - 1e-6 <= x < a + b - 1e-6), starts[-1][2])
    out, filled = list(mel), set()
    top = max(p for _, _, p in mel)                    # (an echo stays under the section's peak: one climax note)
    for k in range(1, n_bars):
        a = k * meter
        if any(a - 1e-6 <= st < a + meter - 1e-6 for st, _, _ in out) or \
                (ends and ((k + 1) % ends == 0 or k == n_bars - 1)):
            continue
        src = None
        for j in range(k - 1, -1, -1):
            cand = [n for n in out if j * meter - 1e-6 <= n[0] < (j + 1) * meter - 1e-6]
            if len(cand) >= 2:
                src = (j, cand)
                break
        if src is None:
            continue
        out = [(st, min(du, a - st) if st < a <= st + du else du, p) for st, du, p in out]
        j, cand = src
        fall = j in filled                             # (an echo of an echo falls: no 3-bar vamp - round r3)
        filled.add(k)
        last = None
        for st, du, p in cand:
            st2 = st + (k - j) * meter
            c = under(st2 + 1e-3)
            pcs = {(c.root + i) % 12 for i in c.intervals}
            opts = [q for q in range(p - 6, p + 7) if q % 12 in pcs and q < top and (not fall or q < p)] or \
                [q for q in range(p - 6, p + 7) if q % 12 in pcs and q < top] or [p]
            if fall:
                p -= 2
            p2 = min(opts, key=lambda q: (abs(q - p), q))
            if last is not None and p2 == last[1] and p != last[0]:     # (the echo keeps the bar's motion: a
                p2 = min([q for q in opts if q != p2] or [p2],          # moving line does not become one pitch
                         key=lambda q: (abs(q - p) + (0 if (q - p2) * (p - last[0]) > 0 else 3), q))   # repeated)
            last = (p, p2)
            out.append((st2, min(du, a + meter - st2), p2))
    return out


HEAD_RETURN = {'A2': 1, 'A3': -1, 'A4': 1}
"""A sung return's head (round g12, the statistician: VQXW's head four times as written, JQTJ's A4 = A1's bars 3-4,
ZSTD 11-12 / 47-48 - _vary_changed varied the bodies, the head's own bars came back as played): its second bar's line
moved this many scale steps (re-fitted to the return's chords; the other way where that leaves it a copy) wherever it
still copies the source's second bar (VARIED) - its first bar as played (rhythm / ornament: _vary), recognisable."""


def _head_turn(ch: list, mel: list, src: list, meter: int, key_pcs, step: int) -> list:
    """HEAD_RETURN: a return's melody `mel` with its head's second bar moved `step` scale steps (re-fitted) where it
    still copies `src`'s (the theme as the section got it) - its top line on an 8th grid, Jaccard >= VARIED."""
    from .composer import Harm, _refit, _scale_step
    b0, b1 = meter, 2 * meter

    def bar2(ns):
        return [n for n in ns if b0 - 1e-6 <= n[0] < b1 - 1e-6]

    def sig(ns):
        return {(round(2 * st), p) for st, du, p in bar2(ns)}
    a, b = sig(mel), sig(src)
    if len(a) < 2 or len(a & b) < VARIED * len(a | b) or not ch:
        return mel
    key, harm = set(key_pcs), Harm(ch, key_pcs)
    ps = [p for *_, p in mel]
    before = [n for n in mel if n[0] < b0 - 1e-6]
    rest = [n for n in mel if not b0 - 1e-6 <= n[0] < b1 - 1e-6]
    for d in (step, -step):
        moved = _refit([(st, du, _scale_step(p, d, key)) for st, du, p in bar2(mel)], harm, meter, min(ps) - 2,
                       max(ps), prev=before[-1][2] if before else None)
        new = sorted(rest + moved)
        if len(sig(new) & b) < VARIED * len(sig(new) | b):
            return new
    return mel


RETURNS = ('A2', 'A3', 'A4')
"""The theme's returns (_vary_draw: the head kept, the second half rewritten)."""

POST_RETURN = {'head': 'orn', 'reharm': 0.7}
"""The theme's first return after the climax (round g7: WHKZ / QNFS / GVPE's A3 = A1 note for note - "a return
changed by the climax"): its head unit re-rhythmed ('head', a _vary kind: its pitches kept, recognisable), every unit
checked as changed (_vary_changed), at least 'reharm' of its chords swapped (_reharm). Round g10 (the g9 judges: FCJZ /
JRCY's return after the climax "without the head"): a sung genre's head there ornamented ('orn': its rhythm and
contour kept, a connecting note or a turn), its new chords the change; the units after it rewritten."""


def _vary_draw(sec: dict, units: int, rng: random.Random) -> list:
    """A section's 'vary' kinds, one per 2-bar unit: a phrase's second unit (its ending: every odd unit) and the
    last unit among VARY_END - a sequence or an inversion there would lose the cadence. A return of the theme
    (RETURNS; blind round g4: ZKYC's theme four times almost note for note) keeps its head (the first unit as written
    or ornamented) and rewrites its second half: a sequence or an inversion (the cadence unit too - _vary keeps its
    landing note), never the unit as written."""
    w = sec['vary']
    end = {k: v for k, v in w.items() if k in VARY_END} or {'keep': 1.0}
    if sec['name'] in RETURNS and units >= 3:
        # (the returns of one part rewrite it differently: the sequence and the inversion alternate unit by unit,
        # each return starting on the other one - A2 / A4 of one part were one copy in round g4, ANQT)
        i = RETURNS.index(sec['name'])
        head = {k: v for k, v in w.items() if k in ('keep', 'orn')} or {'keep': 1.0}
        out = [_pick(rng, head if k == 0 else end if k % 2 else w) for k in range(units)]
        return [('seq', 'invert')[(k + i) % 2] if k >= units // 2 else x for k, x in enumerate(out)]
    return [_pick(rng, end if k % 2 or k == units - 1 else w) for k in range(units)]


def _embellish(own: list, harm, scale_of, hi: int, budget: int = 2, keep=()) -> list:
    """_vary's 'orn': up to `budget` figures - a third (a quarter+ stepping on) filled by a passing tone, a 2-beat+
    note turning to its neighbour and back; none of those: an appoggiatura from the step above on the first long
    note. keep: the notes left as written (round g8: the theme head's held top note)."""
    from .composer import _scale_step
    out, done = [], 0
    for i, (st, du, p) in enumerate(own):
        nxt = own[i + 1] if i + 1 < len(own) else None
        if (st, du, p) in keep:
            out.append((st, du, p))
            continue
        joined = nxt is not None and nxt[0] - (st + du) < 0.25
        if done < budget and joined and du >= 1 - 1e-6 and 3 <= abs(nxt[2] - p) <= 4:
            h = 0.5 if du < 2 - 1e-6 else 1.0
            sc = scale_of(st + du - h, h)
            mid = [q for q in range(min(p, nxt[2]) + 1, max(p, nxt[2])) if q % 12 in sc]
            if mid:
                q = min(mid, key=lambda x: (abs(2 * x - p - nxt[2]), x))
                out += [(st, du - h, p), (st + du - h, h, q)]
                done += 1
                continue
        if done < budget and joined and du >= 2 - 1e-6 and nxt[2] != p:
            sc = scale_of(st + du - 1, 0.5)
            up = _scale_step(p, 1, sc)
            nb = up if up < hi else _scale_step(p, -1, sc)
            out += [(st, du - 1, p), (st + du - 1, 0.5, nb), (st + du - 0.5, 0.5, p)]
            done += 1
            continue
        out.append((st, du, p))
    if not done:
        for i, (st, du, p) in enumerate(out):
            up = _scale_step(p, 1, scale_of(st, du))
            if du >= 1 - 1e-6 and up < hi and (i == 0 or out[i - 1][2] != up) and (st, du, p) not in keep:
                h = 0.5 if du < 2 - 1e-6 else 1.0
                out[i:i + 1] = [(st, h, up), (st + h, du - h, p)]
                break
    return out


def _rerhythm(own: list, a: float, meter: int, harm, key) -> list:
    """_vary's 'rhythm': a pickup start (the unit's downbeat silent, its first note within the first beat and a half)
    moved onto the downbeat; the second bar's downbeat note - a short key tone of its own chord - anticipated an 8th
    (the note before it shortened); neither: the first pair of even 8ths on a beat dotted."""
    out = list(own)
    moved = False
    if out and 0.5 - 1e-6 <= out[0][0] - a <= 1.5 + 1e-6:
        st, du, p = out[0]
        out[0] = (a, du + (st - a), p)
        moved = True
    b = a + meter                                      # (the second bar's downbeat first, then any beat)
    for i in sorted(range(1, len(out)), key=lambda i: (abs(out[i][0] - b) > 1e-6, out[i][0])):
        st, du, p = out[i]
        pst, pdu, pp = out[i - 1]
        if abs(st - round(st)) < 1e-6 and pst + pdu >= st - 1e-6 and pdu >= 1 - 1e-6 and pp != p \
                and du <= 1.5 + 1e-6 and p % 12 in key and p % 12 in harm.under(st, du).core:
            out[i - 1] = (pst, pdu - 0.5, pp)
            out[i] = (st - 0.5, du + 0.5, p)
            moved = True
            break
    if not moved:
        for i in range(len(out) - 1):
            (st, du, p), (st2, du2, p2) = out[i], out[i + 1]
            if abs(du - 0.5) < 1e-6 and abs(du2 - 0.5) < 1e-6 and abs(st2 - st - 0.5) < 1e-6 \
                    and abs(st - round(st)) < 1e-6:
                out[i], out[i + 1] = (st, 0.75, p), (st + 0.75, 0.25, p2)
                break
    return out


def _vary(ch: list, mel: list, meter: int, key_pcs, kinds: list, land: bool = False, size: int = 1,
          head: bool = False) -> list:
    """A return's melody developed per 2-bar unit (VARY: kinds[k] for unit k; the notes past the last unit stay).
    Every changed unit stays in the section's range and on its chords (composer._refit for 'seq' / 'invert'). land:
    a sequenced / inverted last unit keeps its last note as written (the cadence's landing); size: the sequence's
    step in scale steps (a later return sequences by a third; a list: per unit); head: the first unit is the theme's head - an 'orn'
    there keeps its top note held (round g10: the return after the climax, its head's held top cut by a passing
    tone)."""
    from .composer import Harm, _refit, _scale_step
    if not mel or not ch:
        return mel
    harm = Harm(ch, key_pcs)
    unit = 2 * meter
    mel = sorted(mel)
    lo, hi = min(p for *_, p in mel) - 2, max(p for *_, p in mel)
    key = set(key_pcs)

    def scale_of(st, du):
        return harm.under(st, du).scale
    out, prev = [], None
    for k, how in enumerate(kinds):
        a, z = k * unit, (k + 1) * unit
        own = [n for n in mel if a - 1e-6 <= n[0] < z - 1e-6]
        new = own
        if how == 'orn' and own:
            new = _embellish(own, harm, scale_of, hi,
                             keep={n for n in own if n[2] == max(x[2] for x in own)} if head and k == 0 else ())
        elif how == 'rhythm' and own:
            new = _rerhythm(own, a, meter, harm, key)
        elif how == 'seq' and prev:
            mean = sum(p for *_, p in own) / len(own) if own else None
            pm = sum(p for *_, p in prev) / len(prev)
            step = (-1 if mean is not None and mean < pm else 1) * (size[k] if isinstance(size, list) else size)
            new, last = [], None
            for st, du, p in prev:
                q = _scale_step(p, step, key)
                if last is not None and q == last[1] and p != last[0]:     # (the source moved: so does the copy)
                    q = _scale_step(q, 1 if p > last[0] else -1, key)
                new.append((st + unit, min(du, z - st - unit), q))
                last = (p, q)
            new = _refit(new, harm, meter, lo, hi, prev=out[-1][2] if out else None)
        elif how == 'invert' and len(own) >= 3:
            p0 = own[0][2]
            inv = [(st, du, p0 - (p - p0)) for st, du, p in own]
            d = max(0, max(p for *_, p in inv) - hi)   # (moved under the range's top: clamped there, a falling
            new = _refit([(st, du, p - d) for st, du, p in inv], harm, meter, lo, hi,     # line became one
                         prev=out[-1][2] if out else None)                              # pitch 4 times)
            if len({p for *_, p in new}) < max(2, len(new) // 2):
                new = own
        if land and k == len(kinds) - 1 and how in ('seq', 'invert') and own and new:
            last = own[-1]                             # (the landing as written: the cadence stays a cadence)
            new = [x for x in new if x[0] < last[0] - 1e-6] + [last]
        out += new
        prev = new or prev
    out += [n for n in mel if n[0] >= len(kinds) * unit - 1e-6]
    out.sort()
    return [(st, min(du, out[i + 1][0] - st) if i + 1 < len(out) else du, p) for i, (st, du, p) in enumerate(out)
            if i + 1 == len(out) or out[i + 1][0] - st > 1e-6]


def _grow(ch: list, hook: list, meter: int, key_pcs, peak: int, aug: bool = False, at: float = 0.6) -> list | None:
    """The 'grow' climax (the learned generator's blind round 2: the climax was B1 replayed or A an octave up, never a
    new idea derived from the motif; new-age round r8: the piece read composed restated the hook and extended it to a
    new peak): per 2-bar unit over the section's chords - the hook (`hook`: A1's first unit) restated at a new
    pitch level, then sequenced a scale step higher per unit (every other statement answered: its second half turned
    over), the unit at ~60 % climbing its head twice into the single peak (the highest chord tone / tension at or
    under `peak`, held), then released (the hook's contour turned, falling) and landed (its head turned, a long chord
    tone). aug: the first statement the hook augmented (twice as slow, over two units: the theme's rhythm and contour
    carried into the climax - blind round g1, the pieces that fooled the judges built the climax so; plan['grow_aug'],
    drawn per piece). at: where the climb sits (share of the units; drawn per piece).
    (Blind round g2: the climax tiled the hook's 3-note head cell bar after bar - 'x, upper neighbour, x' on one
    grid, four bars of F5: the even statements now EXTEND the hook - its first bar, then a stepwise line on into
    the next level in its second bar's rhythm -, the climb runs up by step to the peak (held a bar at most), the
    release is the whole hook turned upside down, falling - a descending answer, not the head again.)
    None when the hook has under 3 notes."""
    from .composer import Harm, _refit, _scale_step
    harm = Harm(ch, key_pcs)
    unit = 2 * meter
    n = int(round(harm.length / unit))
    hook = sorted(x for x in hook if x[0] < unit - 1e-6)
    if len(hook) < 3 or n < 3:
        return None
    key = set(key_pcs)
    top_h = max(p for *_, p in hook)
    pu = max(1, min(n - 2, int(round(at * n))))
    scale = [q for q in range(24, 112) if q % 12 in key_pcs]

    def idx(p):
        return min(range(len(scale)), key=lambda i: abs(scale[i] - p))

    def upside(notes, start):                          # (the notes' contour upside down, diatonic, from `start`)
        if not notes:
            return []
        i0 = idx(notes[0][2])
        j0 = idx(start)
        return [(st, du, scale[max(0, min(len(scale) - 1, j0 - (idx(p) - i0)))]) for st, du, p in notes]

    def line_on(first, rhythm, t, up=1):               # (a stepwise line on from the first bar's last note)
        out_, q = [], first[-1][2] if first else None
        for st, du, _ in rhythm:
            if q is None:
                break
            q = _scale_step(q, up, key)
            out_.append((t + st, du, q))
        return out_
    aug = aug and len(hook) >= 4                       # (a hook of long notes augmented: tiled long tones)

    def rise(k):                                       # (a long section - a waltz's 8 units - climbs every 2nd unit)
        return k if n < 6 else k // 2
    want = peak - 3 - 2 * rise(pu - 1)
    d0 = 0
    while _scale_step(top_h, d0 + 1, key) <= want and d0 < 14:
        d0 += 1
    while _scale_step(top_h, d0, key) > want and d0 > -14:
        d0 -= 1

    def at(level, notes, t):
        return [(t + st, du, _scale_step(p, level, key)) for st, du, p in notes]
    head = [x for x in hook if x[0] < hook[0][0] + meter - 1e-6][:3]
    if len(head) < 2:
        head = hook[:2]
    out, peak_at = [], 0.0
    for k in range(n):
        t = k * unit
        if aug and k < min(2, pu):                     # the augmented statement: the hook twice as slow, from the
            h0 = hook[0][0] - hook[0][0] % 1           # unit's start (its pickup's offset kept)
            notes = at(d0 + rise(0), [(2 * (st - h0) - k * unit, 2 * du, p) for st, du, p in hook
                                      if k * unit - 1e-6 <= 2 * (st - h0) < (k + 1) * unit - 1e-6], t)
        elif k < pu:                                   # the statements: a step higher per unit
            notes = at(d0 + rise(k), hook, t)
            if k >= 2 and k % 2 == 0:                  # (a sequence breaks after two steps - new-age round r11: the
                # hook five times up the scale): the extension - the hook's first bar, then a line rising by step
                # in its second bar's rhythm (blind round g2: the head cell twice, bar after bar)
                first = [x for x in notes if x[0] < t + meter - 1e-6]
                rhythm = [(st - meter, du, p) for st, du, p in hook if st >= meter - 1e-6] or \
                    [(0.0, 1.0, 0), (1.0, 1.0, 0), (2.0, meter - 2.0, 0)]
                notes = first + line_on(first, rhythm, t + meter)
            elif k % 2:                                # (every other one answered: its second half turned over -
                half = [i for i, x in enumerate(notes) if x[0] >= t + meter - 1e-6]     # where it stays under the
                if half and half[0] > 0:                                               # statement's top)
                    piv = notes[half[0] - 1][2]
                    turned = [(st, du, piv - (p - piv)) if i in half else (st, du, p)
                              for i, (st, du, p) in enumerate(notes)]
                    if max(p for *_, p in turned) <= max(p for *_, p in notes):
                        notes = turned
        elif k == pu:                                  # the climb: the hook's first bar a step up, then by step
            first = [x for x in at(d0 + rise(pu - 1) + 1, hook, t) if x[0] < t + meter - 1e-6]     # to the peak
            q = first[-1][2] if first else peak - 5
            run = []
            while q < peak - 2 and len(run) < 6:
                q = _scale_step(q, 1, key)
                run.append(q)
            g_ = 0.5 if len(run) <= 4 else (meter - 1.0) / max(1, len(run))
            notes = first + [(t + meter + i * g_, g_, x) for i, x in enumerate(run)]
            pk_t = t + meter + len(run) * g_
            notes.append((pk_t, max(1.0, min(meter, t + unit - 0.5 - pk_t)), peak))
            peak_at = pk_t
        else:
            # the release: the head augmented (twice as slow), a step lower each time; the landing: the head, then a
            # long chord tone - each under the note before it
            h0 = head[0][0]
            ref = out[-1][2] if out else peak - 2
            top_ = max(p for *_, p in head)
            lv = 0
            while _scale_step(top_, lv, key) >= ref and lv > -14:
                lv -= 1
            while _scale_step(top_, lv + 1, key) < ref and lv < 14:
                lv += 1
            if k < n - 1:                              # (the release: the whole hook turned over, falling from
                src = [(t + st, du, p) for st, du, p in hook]                     # under the note before)
                notes = upside(src, _scale_step(ref, -1, key)) if k == pu + 1 else \
                    [(t + st, du, _scale_step(p, lv, key)) for st, du, p in hook]
            else:
                notes = [(t + st - h0, du, _scale_step(p, lv, key)) for st, du, p in head]
                ci = harm.under(t + meter, meter)
                r_ = notes[-1][2] if notes else ref
                land = max((c for c in range(r_ - 7, r_) if c % 12 in ci.core), default=r_ - 2)
                notes = [x for x in notes if x[0] < t + meter - 1e-6]
                notes.append((t + meter, meter + meter / 2 if meter == 4 else meter, land))
        out += [x for x in notes if t - 1e-6 <= x[0] < t + unit - 1e-6]
    out.sort()
    out = [(st, min(du, out[i + 1][0] - st) if i + 1 < len(out) else min(du, harm.length - st), p)
           for i, (st, du, p) in enumerate(out) if i + 1 == len(out) or out[i + 1][0] - st > 1e-6]
    lo = min(p for *_, p in out) - 2
    out = _refit(out, harm, meter, max(48, lo), peak)
    pk = min(range(len(out)), key=lambda i: abs(out[i][0] - peak_at))     # the single peak: the climb's long note
    st, du, _ = out[pk]
    ci = harm.under(st, du)
    best = max((c for c in range(peak - 4, peak + 1) if c % 12 in ci.core | ci.tensions), default=out[pk][2])
    out[pk] = (st, du, best)
    for i, (s_, d_, p_) in enumerate(out):
        if i != pk and p_ >= best:                     # (under the peak, never the note before it again: mirrored
            cj = harm.under(s_, d_)                    # under it - round r11: five bars parked on one tone under the
            before = out[i - 1][2] if i else None      # peak)
            want_ = 2 * best - p_ - 2
            out[i] = (s_, d_, max((c for c in range(want_ - 4, min(want_, best - 1) + 1)
                                   if c % 12 in cj.scale and c != before), default=best - 2))
    return out


ANTHEMS = ('octaves', 'chords', 'augment', 'sequence', 'reharm', 'canon')
"""How the 'theme' climax states the theme (_anthem; plan['set']['anthem'], drawn per set slot): 'octaves' / 'chords'
its head phrase as written, the right hand in octaves / chords (_texture); 'augment' its first unit twice as slow;
'sequence' its first unit twice, a third apart, then the theme on; 'reharm' as written over new chords (every chord
swapped where the line allows, the head's own units kept: _reharm); 'canon' as written, the head answered a bar later
an octave under it by the hand's inner voice (_canon; round g10, four judges cluster "A1 an octave up at the climax"
as the set's one payoff). Round g13: every anthem but 'augment' opens with the head at its own degrees and then the
head a third higher, the 'sequence' plan (ANTHEM_HEAD) - the kinds now differ by texture and chords."""

CANON = {'delay': 1, 'min_dur': 0.5, 'floor': 60, 'gap': 3, 'touch': 0.72}
"""The 'canon' climax's inner voice (_canon): the sung statements before the peak's unit echoed 'delay' bars later an
octave under, their notes of 'min_dur' beats+ that stay at or over 'floor' (C4) and 'gap' semitones under the melody
sounding over them (no crossing) - the theme's imitation inside the right hand, played at 'touch' x the velocity
the pianist gives it (an inner voice, never over the line)."""


def _canon(mel: list, meter: int, a: float) -> list:
    """The 'canon' climax's echo notes [(start, dur, pitch)] (absolute beats; CANON) of a climax line `mel` (section
    beats) starting at `a`: up to its peak note's unit."""
    if not mel:
        return []
    C, unit = CANON, 2 * meter
    pk = max(mel, key=lambda n: (n[2], -n[0]))
    end = unit * int(pk[0] // unit + 1e-9)
    d = C['delay'] * meter
    out = []
    for st, du, p in mel:
        q, t = p - 12, st + d
        if du < C['min_dur'] - 1e-6 or q < C['floor'] or t >= end - 1e-6:
            continue
        over = [x for x in mel if x[0] <= t + 1e-6 and x[0] + x[1] > t + 1e-6]
        if any(x[2] - q < C['gap'] or abs(x[0] - t) < 1e-6 and x[2] == q for x in over) or not over:
            continue
        out.append((a + t, min(du, end - t, max(x[0] + x[1] for x in over) - t), q))   # (under the line only)
    return out

ARRIVALS = ('direct', 'pause', 'key', 'dominant', 'fragment')
"""How a sung climax arrives (plan['set']['arrival'], a set draw; round g9, four judges: "the theme returns at the
climax" heard as the set's one plan): 'direct' straight in, 'pause' after the suspended pause (the signature move at
the climax seam: composer.arrival_pause), 'key' after a key move (its climax key drawn off home; the others stay home),
'dominant' over a held dominant (_arrive: the section before it closes V7sus4 - V7, held), 'fragment' its head, then
the head's first bar twice, rising, then the theme on (_anthem; round g12: the fragment first made the climax open
on two notes, KTGG / ERDL "not the head")."""


SUNG_KEYS = {'major': ('step',), 'minor': ('par', 'step')}
"""The keys a sung climax may move to (KEY_SHIFTS; round g12, four judges: ZSTD's climax a 4th up over IV, F#5-B5-G5-A5
against the head's C#5-F#5-D5-E5, "new melody"): a whole step up or the parallel major, where the head keeps its own
degrees at its own height (CNWE's whole-step climax, WNTP's key lift: round g11's convincing moves). Others: home."""


def _arrive(tune: Tune, plan: list, meter: int, bar: float, how: str | None) -> None:
    """The climax's 'dominant' arrival (ARRIVALS): the section before a sung climax at home closes on the home
    dominant held two bars - V7sus4, then V7, a fermata on it - its melody re-fitted there. In place."""
    from ..theory import Key
    from .composer import Harm, _refit, spell
    pk = next((i for i, (s_, *_) in enumerate(plan) if s_.get('peak')), None)
    if how != 'dominant' or not pk or plan[pk][0].get('_key') or plan[pk][0].get('_step'):
        return
    sec, ch, mel, L = plan[pk - 1]
    if L < 3 * bar - 1e-6 or not ch:
        return
    t_pc = Key(tune.key).tonic % 12
    v = spell(t_pc + 7, _key_sharps(tune.key), 7)
    ch2 = _last_bar(_last_bar(ch, L, 2 * bar, v + '7sus4'), L, bar, v + '7')
    keep = [x for x in mel if x[0] < L - 2 * bar - 1e-6]
    tail = [x for x in mel if x[0] >= L - 2 * bar - 1e-6]
    if tail:
        ps = [p for *_, p in mel]
        tail = _refit(tail, Harm(ch2, _key_pcs(tune)), meter, min(ps) - 2, max(ps), prev=keep[-1][2] if keep else None)
    plan[pk - 1] = (dict(sec, fermata=max(sec.get('fermata') or 0.0, 1.5), _arrive='dominant'), ch2, keep + tail, L)


ANTHEM_GROW = 4
"""Bars a sung climax on the theme's own part (the 'variations' layout: no build before it) adds to its 8 (_arrange;
round g9, LXAN: "a short, low climax without a build - extend it to 12 bars")."""

ANTHEM_OUT = {'units': 1, 'land': 0}
"""The sung climax's way out (_anthem; round g10, the g9 judges: QKNJ's A6 -> C#5 in one bar, FCJZ's 16-bar waltz
climax sagging six bars after its peak, LMUP's last climax bar empty): at most 'units' 2-bar units after the peak's
unit (the peak moves later in a long climax), the line coming down to the statements' level over them, the last
'land' bar at that level; a tail of chords past the units gets a falling link (a chord tone under the note before,
held)."""

ANTHEM_BAND = {'band': 84, 'share': 0.15, 'lifts': (4, 2)}
"""Where the sung climax's statements sit (_anthem; round g7 - the user's "too many very high notes", the g6
performer: SGVL's climax 55 % at C6+ for nine bars, "start in the 5th octave, save the octave for the peak"): the
theme a fifth / a third over A1 ('lifts', scale steps, the highest first) where at most 'share' of its notes reach
'band' (C6), else as written; only the peak unit sings the octave."""


ANTHEM_HEAD = {'second': True, 'step': 2, 'open': 'reharm'}
"""The sung climax's first two units (_anthem; round g12: VQXW five judges, EXWH / ZEFU two - "A1 replayed louder", the
head and A1's own continuation at A1's pitches; ZSTD four - the head a 4th up, "new melody"; GZAT, the model, four
judges: its head as written, then a third up, then the peak): the head at its own degrees ('floor': A1's, or the key
move's), then the head again 'step' scale steps higher - a new second phrase - in every anthem but 'augment' (the
'sequence' anthem's plan, now the rule); the theme goes on from its second unit after them. Round g14 (the g13
judges: "A1 replayed louder" again where the head opened at A1's pitches over A1's chords - MYUS 5, GALR 4, CPED 3,
QTNU 3; the head-first climax the set's one shared plan, all seven): 'open' 'reharm' - at home the head's first unit
sings over new chords (_reharm, every chord its line allows), a change heard at once; after a key move the key is
the change and the head keeps its chords - and the second phrase a set draw (ANTHEM_SECOND)."""

ANTHEM_SECOND = {'third': (2, False), 'fifth': (4, False), 'mirror': (2, True)}
"""The sung climax's second phrase, right after the head (plan['set']['second'], drawn per set slot; _anthem): (scale
steps over the head's level, mirrored) - the head a third higher (GZAT's plan), a fifth higher (under the peak unit's
top, else a third), or the head mirrored (its intervals turned over) a third higher, re-fitted to its chords."""


def _anthem(ch: list, theme: list, meter: int, key_pcs, peak: int, how: str = 'octaves', at: float = 0.6,
            ceiling: int = 91, octave: int = 0, arrive: str | None = None, shift: int = 0, second: str | None = None,
            out_units: int | None = None) -> tuple | None:
    """The 'theme' climax (blind round g4, all five judges: 7 of 8 climaxes had no theme - chord stabs, held
    mid-register notes, a cascade; both references state their theme at the peak: the chorale two octaves up, the
    theme's arpeggio sequenced up). Per 2-bar unit, `ch` the theme's own chords (A1's):
      - the statements, up to ~`at` of the section, over A1 (ANTHEM_BAND: a fifth / third up in the 5th octave, the
        unit before the peak a third higher still): 'octaves' / 'chords' / 'reharm' the theme's units over their
        chords; 'augment' its first unit twice as slow over two units (its chords stretched alike), then the theme on;
        'sequence' its first unit twice, the second a third higher, then the theme on (round g7: FUKP's head cell
        looped 8-12 times at one pitch - the climb had no room under the sung octave);
      - the peak: the first unit (the head) again, a third / fifth / octave up the scale and `octave` over it (12:
        blind round g5, the climax wants the C6 band - round g7, only here), over the first unit's chords - its top
        note the piece's peak, at or under `peak`;
      - the theme's next units falling a step each from a third over the statements (re-fitted to their chords), and
        its own last unit, at the statements' level, as the landing.
    Only the falling continuation is re-fitted: the theme keeps its appoggiaturas. arrive 'fragment' (ARRIVALS): the
    head, then its first bar twice, the second a step higher (re-fitted), the theme on from the next unit;
    a head whose first bar has under 3 notes arrives directly (round g12: KTGG's two-note fragment, C5-D5 | D5-Eb5,
    heard as "a stepwise climb, not the theme"). shift: the semitones the climax moves by afterwards (its key move,
    _modulate): its statements sit at least that much higher, the head opening the climax at A1's register or over
    it (round g12: PTCV's head moved down into C, G4-E5 at v54 - "new material", all five judges).
    -> (changes, melody), None when the theme has under 4 notes or 2 units, or the section under 3 units."""
    from .composer import Harm, _refit, _scale_step, _slice_changes
    unit = 2 * meter
    total = sum(b for _, b in ch)
    n = int(round(total / unit))
    theme = sorted(theme)
    if len(theme) < 4 or n < 3:
        return None
    units = [[(st - k * unit, du, p) for st, du, p in theme if k * unit - 1e-6 <= st < (k + 1) * unit - 1e-6]
             for k in range(int(theme[-1][0] // unit) + 1)]
    if len(units) < 2 or len(units[0]) < 3:
        return None
    units = [u or units[0] for u in units]
    key = set(key_pcs)
    head = units[0]
    top_h = max(p for *_, p in head)
    pu = max(1, min(n - 2, int(round(at * n))))
    pu = max(pu, n - 1 - (ANTHEM_OUT['units'] if out_units is None else out_units))   # (round g10: FCJZ's 16-bar
    #                                                    climax sagging six bars after it; PIANO_DIVERSE's early peak:
    #                                                    out_units 2)
    hi = min(peak, ceiling)

    def chords(k):                                    # (the theme's chords of its unit k)
        return _slice_changes(ch, k * unit, (k + 1) * unit) or _slice_changes(ch, 0, unit)

    def lift(level, notes, t, oc=0):
        return [(t + st, min(du, unit - st), _scale_step(p, level, key) + oc) for st, du, p in notes]
    # the peak's level: a third / fifth / octave (+ a third) up - the highest whose top stays at or under the peak
    # (over the sung octave: there a third / fifth at most)
    ups = [d for d in (2, 4, 7, 9, 11, 14) if _scale_step(top_h, d, key) + octave <= hi]
    d_pk = max(ups) if ups else max([d for d in (1,) if _scale_step(top_h, d, key) + octave <= hi] or [0])
    pk_top = _scale_step(top_h, d_pk, key) + octave
    # the statements' level (ANTHEM_BAND): over A1, few notes at C6+, under the peak with room for the climb
    body = [p for u in units for *_, p in u]
    B = ANTHEM_BAND
    def high(d, ps):
        return sum(_scale_step(p, d, key) >= B['band'] for p in ps) > B['share'] * len(ps)
    base = next((d for d in B['lifts'] if not high(d, body) and _scale_step(max(body), d + 2, key) < pk_top), 0)
    # (the head's first statement at A1's register or over it once the climax has moved: the lowest level that
    # keeps its top within a semitone of A1's head's top after `shift`)
    floor = next((d for d in range(8) if _scale_step(top_h, d, key) + shift >= top_h - 1), 0)
    if floor > base and _scale_step(max(body), floor + 2, key) < pk_top:
        base = floor
    climb = pu >= 2 and not high(base + 2, [p for *_, p in units[min(pu - 1, len(units) - 1)]])
    # (round g10: QKNJ fell A6 -> C#5 in one bar, FCJZ Gb6 -> Eb5 - the theme's units after the peak came back at the
    # statements' level at once): after the peak the line comes down over the rest of the climax - each note from
    # the peak's register (a third under its level, the octave on) to the statements' level, by its place in the way
    # down (ANTHEM_OUT), re-fitted to its chords
    t_out, t_end = (pu + 1) * unit, n * unit
    span_out = max(meter, t_end - t_out - ANTHEM_OUT['land'] * meter)

    def down(notes, t):
        res = []
        for st, du, p in notes:
            f = min(1.0, max(0.0, (t + st - t_out) / span_out))
            p_hi, p_lo = _scale_step(p, max(base, d_pk - 2), key) + octave, _scale_step(p, base, key)
            q = int(round(p_hi + (p_lo - p_hi) * f))
            q = min((c for c in range(q - 2, q + 3) if c % 12 in key), key=lambda c: (abs(c - q), c), default=q)
            res.append((t + st, min(du, unit - st), q))
        return res
    new_ch, out, fit = [], [], []
    cell = [(st, min(du, meter - st), p) for st, du, p in head if st < meter - 1e-6]
    frag = arrive == 'fragment' and len(cell) >= 3 and pu >= 2
    for k in range(n):
        t = k * unit
        c_ = chords(min(k, len(units) - 1))
        if k < pu:
            lv = base + (2 if climb and k == pu - 1 else 0)    # (the unit before the peak a third up, in the band)
            if ANTHEM_HEAD['second'] and (k == 0 or frag and k == 1):
                lv = floor                             # (round g13: the head - and its fragment - at its own degrees)
            if frag and k == 1:                        # (round g9: the head's first bar, then again a step higher;
                s0 = lv                                # round g12: after the head whole - KTGG / ERDL's climaxes
                #                                        opened on the fragment, "not the head")
                second = [(t + meter + st, du, _scale_step(p, s0 + 1, key)) for st, du, p in cell]
                notes, c_ = lift(s0, cell, t) + second, chords(0)
                fit += second
            elif how == 'augment' and k < min(2, pu):
                h0 = head[0][0] - head[0][0] % 1
                notes = [(t + 2 * (st - h0) - k * unit, 2 * du, _scale_step(p, base, key)) for st, du, p in head
                         if k * unit - 1e-6 <= 2 * (st - h0) < (k + 1) * unit - 1e-6]
                c_ = [(s_, 2 * b) for s_, b in _slice_changes(ch, k * unit / 2, (k + 1) * unit / 2)]
            elif k < 2 and not frag and (how == 'sequence' or ANTHEM_HEAD['second'] and how != 'augment'):
                # the head at its own degrees (A1's, or the key move's: `floor`), then the head a third higher -
                # then the theme goes on (round g13: ANTHEM_HEAD - every anthem's second phrase; it was 'sequence's)
                s0 = floor if ANTHEM_HEAD['second'] else max(base - 2 if base >= 2 else base, min(floor, base))
                # (round g14: the second phrase a set draw - ANTHEM_SECOND: a third / a fifth up, or mirrored)
                d2, mir = ANTHEM_SECOND.get(second, (ANTHEM_HEAD['step'], False)) if k else (0, False)
                if d2 > ANTHEM_HEAD['step'] and _scale_step(top_h, s0 + d2, key) + 1 >= pk_top:
                    d2 = ANTHEM_HEAD['step']           # (a fifth up reaching the peak unit's top: a third)
                c2_ = min(p for *_, p in head) + max(p for *_, p in head)     # (mirrored in the head's own span)
                src_ = [(st, du, c2_ - p) for st, du, p in head] if mir else head
                notes, c_ = lift(s0 + d2, src_, t), chords(0)
                if mir:                                # (the mirror's notes onto the chords: re-fitted)
                    fit += [x for x in notes if t - 1e-6 <= x[0] < t + unit - 1e-6]
            else:
                back = 1 if how in ('augment', 'sequence') or frag and k > 1 or \
                    ANTHEM_HEAD['second'] and not frag and pu >= 2 else 0
                src = min(max(0, k - back), len(units) - 1)
                notes, c_ = lift(lv, units[src], t), chords(src)
        elif k == pu:                                  # the head at the peak, over its own chords
            notes, c_ = lift(d_pk, head, t, octave), chords(0)
        else:                                          # the way down: the theme's next units, its last the landing
            src = min(k - pu, len(units) - 1) if k < n - 1 else len(units) - 1
            notes, c_ = down(units[src], t), chords(src)
            fit += notes
        new_ch += c_
        out += [x for x in notes if t - 1e-6 <= x[0] < t + unit - 1e-6]
    L = sum(b for _, b in new_ch)
    tail = []
    if abs(L - total) > 1e-6:                          # (a section longer than n units: its tail chords as written)
        tail = _slice_changes(ch, n * unit, total) if L < total else []
        new_ch += tail
    harm = Harm(new_ch, key_pcs)
    if fit:
        fitted = dict(zip(fit, _refit(fit, harm, meter, max(48, min(p for *_, p in fit) - 2), hi)))
        out = [fitted.get(x, x) for x in out]
    out.sort()
    if tail and out:                                   # (round g10: LMUP's climax ended on an empty right-hand bar -
        t, prev = L, out[-1][2]                        # a falling link over the tail chords: each a tone of its chord
        for sym, b in tail:                            # under the note before, held)
            cj = harm.under(t, b)
            q = max((c for c in range(prev - 5, prev) if c % 12 in cj.core), default=prev)
            out.append((t, b, q))
            t, prev = t + b, q
    out = [(st, min(du, out[i + 1][0] - st) if i + 1 < len(out) else min(du, harm.length - st), p)
           for i, (st, du, p) in enumerate(out) if i + 1 == len(out) or out[i + 1][0] - st > 1e-6]
    # the single peak: the head's top at pu (the head's own repeats of it kept), every note outside it under it
    span = [i for i, x in enumerate(out) if pu * unit - 1e-6 <= x[0] < (pu + 1) * unit - 1e-6]
    if span:
        top = max(out[i][2] for i in span)
        # (sung an octave up the head's repeats of its top became two peak strikes a beat apart: the longest one
        # is the peak, a repeat within a bar of it steps under it)
        reps = [i for i in span if out[i][2] == top]
        keep = max(reps, key=lambda i: (out[i][1], -i)) if len(reps) > 1 else None
        near = {i for i in reps if octave and keep is not None and i != keep and abs(out[i][0] - out[keep][0]) <= meter}
        if near:                                       # (round g10: NMPC's E-F#-E-F# head at the peak became
            b0 = meter * int(out[min(near)][0] // meter + 1e-9)     # F#6 F#6 F#6 G#6, the peak hammered - the
            for i in [i for i in span if b0 - 1e-6 <= out[i][0] < out[keep][0] - 1e-6]:   # head's notes in the
                s_, d_, p_ = out[i]                    # first repeat's bar before the kept one a scale step lower:
                #                                        the cell kept, rising into the one peak)
                out[i] = (s_, d_, _scale_step(p_, -1, harm.under(s_, d_).scale))
        for i, (s_, d_, p_) in enumerate(out):
            # (a repeat after the kept one: under it; round g12 - the head's own repeat of its top, sung in place
            # under the lower ceiling, struck the peak twice: every other strike of it under it)
            if (i not in span or keep is not None and i != keep) and p_ >= top:
                cj = harm.under(s_, d_)
                out[i] = (s_, d_, max((c for c in range(top - 5, top) if c % 12 in cj.scale), default=top - 2))
    return new_ch, out


KEY_NAMES = {'major': {'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb'},
             'minor': {'A', 'E', 'B', 'F#', 'C#', 'G#', 'D', 'G', 'C', 'F', 'Bb', 'Eb'}}
"""The keys a section may move to (_key_named): the common written key signatures (Ab's bVI is Fb major: none)."""


def _key_named(key: str, how: str) -> bool:
    """A KEY_SHIFTS move from `key` lands on a key a composer writes (KEY_NAMES), spelled by its degree."""
    from ..theory import spell_above
    tonic, mode = key.split()
    semis, to = KEY_SHIFTS[how]
    name = spell_above(tonic, semis % 12, {0: 0, 2: 1, 3: 2, 4: 2, 5: 3, 7: 4, 8: 5, 9: 5}.get(semis % 12))
    return name in KEY_NAMES[to or mode]


def _major_sym(sym: str, t_pc: int) -> str:
    """A minor key's chord turned to the parallel major (tonic pc t_pc): i / iv major, ii-half-diminished a minor 7th;
    a slash bass on the minor 3rd moves to the major 3rd."""
    import re as _re
    from ..theory import spell_above
    m = _re.match(r'^([A-G][b#]?)(.*?)(?:/([A-G][b#]?))?$', sym)
    root, q, bass = m.group(1), m.group(2), m.group(3)
    c = chord(sym)
    deg = (c.root - t_pc) % 12
    if deg in (0, 5) and q.startswith('m') and not q.startswith('maj'):
        q2 = {'m': '', 'm7': 'maj7', 'm9': 'maj9', 'madd9': 'add9', 'm6': '6', 'm11': 'maj9', 'mmaj7': 'maj7'}.get(q, '')
        iv = (chord(bass).root - c.root) % 12 if bass else None
        return root + q2 + (('/' + spell_above(root, 4, 2)) if iv == 3 else ('/' + bass) if bass else '')
    if deg == 2 and q == 'm7b5':
        return root + 'm7' + (('/' + bass) if bass else '')
    return sym


def _fold(semis: int) -> int:
    """A key move's semitones for the line: the nearer octave (a 5th up, a 4th down)."""
    return semis if semis <= 6 else semis - 12


def _modulate(tune: Tune, ch: list, mel: list, meter: int, how: str, single: bool = False, refit: bool = True):
    """A section moved into another key (KEY_SHIFTS[how]) -> (changes, melody, (semitones, new tonic pc, its pcs)) or
    None when it stays home: the chords transposed and spelled in the new key (_transpose_sym), the melody moved the
    same way (_fold: to the nearer octave), a minor section turned major ('par' / 'rel': its 3rd raised, its 6th /
    7th where the chord under it has them) and re-fitted to its chords (refit=False: the sung theme, _anthem - its
    intervals kept, it already sits on its own chords; round g9: NSFY's bVI climax re-fitted heard as a new tune);
    single: its top note struck once (the others a scale step under it)."""
    from ..theory import Key
    from .composer import Harm, _refit
    semis, mode = KEY_SHIFTS.get(how, (0, None))
    minor = tune.key.split()[1] == 'minor'
    if mode == 'major' and not minor:
        mode = None
    if not semis and not mode:
        return None
    t_pc = Key(tune.key).tonic % 12
    new_t = (t_pc + semis) % 12
    ch2 = [(_transpose_sym(sym, semis, tune.key) if semis else sym, b) for sym, b in ch]
    if mode == 'major':
        ch2 = [(_major_sym(sym, new_t), b) for sym, b in ch2]
    pcs = {(new_t + i) % 12 for i in ((0, 2, 4, 5, 7, 9, 11) if mode == 'major' or not minor
                                      else (0, 2, 3, 5, 7, 8, 10))}
    up = _fold(semis)
    harm = Harm(ch2, pcs)
    out = []
    for st, du, p in mel:
        q = p + up
        if mode == 'major':
            r = (q - new_t) % 12
            tones = {(x - new_t) % 12 for x in harm.under(st, du).chord.pcs}
            q += 1 if r == 3 or (r == 8 and 9 in tones) or (r == 10 and 11 in tones) else 0
        out.append((st, du, q))
    if out and refit:
        out = _refit(out, harm, meter, min(p for *_, p in out) - 2, max(p for *_, p in out))
    if single and out:
        out = _single_top(out, harm)
    return ch2, out, (semis, new_t, pcs)


def _single_top(mel: list, harm) -> list:
    """A peak line's top note struck once (the longest, the latest of equals); its other strikes come down to the
    nearest tone of their chord's scale below it that is not a neighbour's pitch."""
    out = list(mel)
    top = max(p for *_, p in out)
    keep = max((i for i, n in enumerate(out) if n[2] == top), key=lambda i: (out[i][1], i))
    for i, (st, du, p) in enumerate(out):
        if p == top and i != keep:
            ci = harm.under(st, du)
            near = {out[j][2] for j in (i - 1, i + 1) if 0 <= j < len(out)}
            out[i] = (st, du, max((c for c in range(top - 5, top) if c % 12 in ci.scale and c not in near),
                                  default=top - 2))
    return out


def _walk_bass(ch: list) -> list:
    """The changes over a stepwise bass (blind round N0: the references' returns reharmonized over a walking /
    descending bass): each chord in the inversion (root / 3rd / 5th in the bass) whose bass lies closest to a step
    from the one before (a step of 1-2 semitones best, the root on the first and the last chord) -> slash chords."""
    import re as _re
    from ..theory import spell_above
    out, prev = [], None
    for i, (sym, b) in enumerate(ch):
        c = chord(sym)
        m = _re.match(r'^([A-G][b#]?)(.*?)(?:/[A-G][b#]?)?$', sym)
        root, q = m.group(1), m.group(2)
        opts = [(iv, (c.root + iv) % 12) for iv in c.intervals[:3]]
        if prev is None or i == len(ch) - 1:
            pick = opts[0]
        else:
            def cost(o):
                d = min((o[1] - prev) % 12, (prev - o[1]) % 12)
                return (0 if d in (1, 2) else 1 if d == 0 else 2 + d) + (0.5 if o[0] else 0.0)
            pick = min(opts, key=cost)
        prev = pick[1]
        steps = {0: 0, 3: 2, 4: 2, 7: 4, 6: 4, 8: 4, 5: 3, 2: 1}.get(pick[0], None)
        out.append((root + q + (f"/{spell_above(root, pick[0], steps)}" if pick[0] else ''), b))
    return out


def _moving_bass(ch: list, bar: float, mel=(), key=None, table=None, rng=None, take=None,
                 weights=None, key_pcs=None) -> list:
    """A waltz's changes with each chord held 2+ whole bars split into bars, each later bar drawn (blind round r6:
    'every chord exactly 2 bars, X | %'; r7: 'X | X/3rd' in every pair read as a slot-filling rule): held, over its
    3rd / 5th in the bass (F | F/A), or a substitute under the melody (_reharm's table: F | Dm7); sus chords and the
    closing chord stay held. take: the drawn moves (one per later bar, in order) -> the moves played (the
    arrangement record's 'moves': dice.put). weights: the moves' {move: weight} (plan['moves']; given, a closing
    chord held 3+ bars moves too, all but its last bar - the learned generator's blind round 2: 4-bar one-chord
    stretches at a section's end). key_pcs: the section's own key (a section moved to another key; default `key`'s)."""
    import re as _re
    from ..theory import Key, spell_above
    rng = rng or random.Random(0)
    end = len(ch) - 1

    def later(i, b):
        n = int(round(b / bar))
        return range(1, n - 1) if i == end else range(1, n)

    def held(i, sym, b):
        n = b / bar
        return not ((i == end and (not weights or n < 3 - 1e-6)) or 'sus' in sym or '/' in sym or n < 2 - 1e-6
                    or abs(n - round(n)) > 1e-6)
    w = dict(weights or {'hold': 0.3, 'bass': 0.35, 'sub': 0.35})           # (plan['moves'])
    w['sub'] = w.get('sub', 0.0) if table else 0.0
    moves = [_pick(rng, w)
             for i, (sym, b) in enumerate(ch) if held(i, sym, b) for _ in later(i, b)]
    moves = iter(take(moves) if take else moves)
    kp = set(key_pcs) if key_pcs else set(Key(key).pcs) if key else None
    mel_ = sorted(mel)

    def ped(sym, root, t0):
        """The chord a 4th up over the held root ('F | Bb/F': a neighbour chord over a pedal, new-age round r11: 'X |
        X/3rd' in 85 % of the pairs), its quality from the key; None when the melody's strong / long notes in the
        bar are not its tones."""
        if kp is None:
            return None
        r4 = (chord(sym).root + 5) % 12
        if r4 not in kp:
            return None
        q = '' if (r4 + 4) % 12 in kp and (r4 + 7) % 12 in kp else 'm' if (r4 + 3) % 12 in kp and             (r4 + 7) % 12 in kp else None
        if q is None:
            return None
        pcs = {r4, (r4 + (4 if q == '' else 3)) % 12, (r4 + 7) % 12}
        for st, du, p in mel_:
            if t0 - 1e-6 <= st < t0 + bar - 1e-6 and (du >= 2.0 - 1e-6 or abs(st - t0) < 1e-6) and p % 12 not in pcs:
                return None
        return f"{spell_above(root, 5, 3)}{q}/{root}"
    out, subs, t_ = [], set(), 0.0
    for i, (sym, b) in enumerate(ch):
        if not held(i, sym, b):
            out.append((sym, b))
            t_ += b
            continue
        m = _re.match(r'^([A-G][b#]?)(.*)$', sym)
        c = chord(sym)
        third = f"{m.group(1)}{m.group(2)}/{spell_above(m.group(1), c.intervals[1], 2)}"
        fifth = f"{m.group(1)}{m.group(2)}/{spell_above(m.group(1), 7, 4)}" if 7 in c.intervals else sym
        out.append((sym, bar))
        for k in later(i, b):
            how = next(moves)
            if how == 'sub':
                subs.add(len(out))
            if how == 'ped':                           # (else a substitute under the melody, else held - blind
                pd = ped(sym, m.group(1), t_ + k * bar)    # round g1: the 5th-bass fallback made 'X | X/inversion'
                if pd is None:                             # pairs, 8-11 a waltz)
                    subs.add(len(out))
                out.append((pd or sym, bar))
                continue
            out.append((sym if how != 'bass' else (third if k % 2 else fifth), bar))
        if i == end:
            out.append((sym, bar))
        t_ += b
    if subs and table and key:
        out = _reharm(out, list(mel), key, table, 1.0, bar, rng, only=subs)
    merged = []                                        # (a held bar merges back: 'X' over two bars)
    for sym, b in out:
        if merged and merged[-1][0] == sym:
            merged[-1] = (sym, merged[-1][1] + b)
        else:
            merged.append((sym, b))
    return merged


def _re_triad(sym: str) -> bool:
    """A plain major triad symbol (C, F#, Bb)."""
    import re as _re
    return bool(_re.match(r'^[A-G][b#]?$', sym))


def _pivot(tune: Tune, plan: list, meter: int) -> None:
    """A climax played a step up ('_step'): the last bar of the section before it moves up with it (the pivot into
    the new key), the climax's own last bar comes back home (its dominant leads the return). In place."""
    for i, (sec, ch, mel, L) in enumerate(plan):
        if not sec.get('_step') or i == 0:
            continue
        home = tune.changes[sec['part']]
        t, new_ch = 0.0, []
        for (sym, b), (hsym, _) in zip(ch, home):
            new_ch.append((hsym if t >= L - meter - 1e-6 else sym, b))
            t += b
        plan[i] = (sec, new_ch, [(st, du, p - 2 if st >= L - meter - 1e-6 else p) for st, du, p in mel], L)
        psec, pch, pmel, pL = plan[i - 1]
        t, out = 0.0, []
        for sym, b in pch:
            out.append((_transpose_sym(sym, 2, tune.key) if t >= pL - meter - 1e-6 else sym, b))
            t += b
        if out and _re_triad(out[-1][0]):              # the pivot lands on the new key's dominant 7th (round r1:
            out[-1] = (out[-1][0] + '7', out[-1][1])   # a bare major chord a step up read as unprepared)
        plan[i - 1] = (psec, out, [(st, du, p + 2 if st >= pL - meter - 1e-6 else p) for st, du, p in pmel], pL)


PRE_TOP = 3
"""The sections before the climax stay this many semitones under its peak note at least (round g11, two judges:
CDSQ's B1 at F#6 under a G#6 climax, "its register used up"; _under_peak, a genre with plan['peak_floor'])."""


def _under_peak(plan: list, key_pcs=None, floor: int = 64, margin: int = 0) -> None:
    """The peak section's top note is the piece's highest: another section reaching it (an octave-up return, a
    frame's line) comes down an octave - unless that drops its line under `floor` (E4: new-age round r9, the chorus
    an octave down in the left hand's register, F#3 under its C#4): then only its notes at the peak come down to the
    key tone below it (key_pcs given) - unless that is more than a quarter of its notes (the sweep of 2026-10-13: an
    octave-up return held on one pitch for 8 bars): then the octave comes down after all. margin (a sung genre:
    PRE_TOP): the sections before the peak's also stay that far under it (their notes over it to the key tone below,
    key_pcs given). In place."""
    tops = [max((p for _, _, p in mel), default=0) for sec, _, mel, _ in plan if sec.get('peak')]
    if not tops:
        return
    top = tops[0]
    for i, (sec, ch, mel, L) in enumerate(plan):
        if not sec.get('peak') and mel and max(p for _, _, p in mel) >= top:
            if key_pcs is None or min(p for _, _, p in mel) - 12 >= floor or                     sum(p >= top for _, _, p in mel) > len(mel) / 4:
                plan[i] = (sec, ch, [(st, du, p - 12) for st, du, p in mel], L)
            else:
                below = max(x for x in range(top - 4, top) if x % 12 in key_pcs)
                plan[i] = (sec, ch, [(st, du, below if p >= top else p) for st, du, p in mel], L)
    pk_i = next(i for i, (sec, *_) in enumerate(plan) if sec.get('peak'))
    cap = top - margin
    for i, (sec, ch, mel, L) in enumerate(plan[:pk_i]):  # (round g11: the register saved for the climax - PRE_TOP)
        if margin and key_pcs is not None and mel and max(p for _, _, p in mel) > cap:
            below = max(x for x in range(cap - 4, cap + 1) if x % 12 in key_pcs)
            plan[i] = (sec, ch, [(st, du, below if p > cap else p) for st, du, p in mel], L)


GOOSE = {'major': {'bVI': (8, ''), 'iv': (5, 'm'), 'bIII': (3, ''), 'II': (2, ''), 'III': (4, ''), 'bVII': (10, '')},
         'minor': {'VI': (8, ''), 'IV': (5, ''), 'bII': (1, ''), 'VofV': (2, '7')}}
"""The goosebump chords (docs/PIANO_MOVES.md 5.4): degree -> (semitones over the local tonic, quality) - the borrowed
bVI / iv / bIII / bVII, the chromatic-mediant III, the major II; in minor the VI, the major IV, the Neapolitan, V/V."""


def _signature(tune: Tune, g: Genre, dice: Dice, pins: dict) -> dict:
    """The piece's signature moves (plan['signature']; the set slot's pins - composer.signature_draw): {move: its
    parameters}; the record holds which move plays (SIGN_KEYS: its kind, or 'none' - a record's 'none' drops it)."""
    if not g.plan.get('signature'):
        return {}
    sig = dict(pins.get('signature') or {})
    out = {}
    for mv, key, par in SIGN_KEYS:
        v = dice.put(None, key, sig[mv][par] if mv in sig else 'none')
        if mv in sig and v != 'none':
            out[mv] = sig[mv]
    return out


def _splice(ch: list, a: float, z: float, sym: str) -> list:
    """The changes with [a, z) one chord `sym`."""
    out, t = [], 0.0
    for s_, b in ch:
        if t < a - 1e-6:
            out.append((s_, min(t + b, a) - t))
        t += b
    out.append((sym, z - a))
    t = 0.0
    for s_, b in ch:
        if t + b > z + 1e-6:
            out.append((s_, t + b - max(t, z)))
        t += b
    return out


def _chord_at(ch: list, t: float) -> str | None:
    x = 0.0
    for s_, b in ch:
        if x - 1e-6 <= t < x + b - 1e-6:
            return s_
        x += b
    return ch[-1][0] if ch else None


def _tones(sym: str) -> set:
    c = chord(sym)
    return {(c.root + i) % 12 for i in c.intervals}


def _snap(p: int, sym: str | None) -> int:
    """p, or the nearest tone of chord sym within a whole step (a long note rests on the harmony)."""
    if sym is None:
        return p
    tn = _tones(sym)
    if p % 12 in tn:
        return p
    return min((q for q in range(p - 2, p + 3) if q % 12 in tn), key=lambda q: (abs(q - p), -q), default=p)


MOTTO_PAYOFF = {'after': 4}
"""Where the motto's payoff enters a sung climax (_sign): 'after' bars into it (a 2-bar unit: the head's first
statement first, after the fragment too in a 'fragment' arrival; round g12 - the payoff at the climax's first beat
replaced the head there, ERDL / NKTZ / LESU: "the climax is not the head"); when it would reach the peak note, it
answers the peak instead: as planted, from the bar after the peak note's (round g13: the payoff was dropped in 11 % of
the set slots with a motto). Its last note leaves no empty bar: the line note it covered, sounding a beat+ past it,
is struck again there, else a falling chord tone holds to the line (round g12: VYDA's bar 38, all seven judges).
Round g14 (the g13 judges: the head-first climax's new second phrase "comes late" where the payoff took its bars -
RFZC 29-30 buried, TCMN 38): after the head and its second phrase, 4 bars in."""

MOTTO_HELD = 1.0
"""The motto payoff's last note held this many beats or more past a bar line gets an inner voice struck under it
there (_sign's put: a tone of the chord, 3-9 semitones under; round g13, four judges: TCMN 38 "empty until 3.67")."""

PAUSE_EXIT = ('sus_hold',)
"""The pause kinds the climax's own last bar may play (_sign: a pause at the 'return' seam right after the climax;
round g13, six judges: CNCJ 46 - the 'rest' pause left one C5 over a lone F2 - "the climax stops dead", "a hole, not
a phrase"): the held V7sus4 with its melody; another drawn kind plays the first of these."""

OST_UNDER = {4: 8, 3: 6}
"""The signature ostinato's grid under an A statement at most (tokens a bar; round g9, all five judges: DMZT's 16ths,
14-16 attacks a bar under the theme - "thin it to 8ths, save the motion"): a faster figure plays thinned there (every
other token held), whole in the intro."""


def _sign(tune: Tune, g: Genre, plan: list, sig: dict, meter: int, bar: float, arrival: str | None = None) -> None:
    """The signature moves written into the plan (docs/PIANO_MOVES.md 5.1-5.5; in place): each section's '_sig'
    {'motto': [(from, to, role, notes)], 'lh': [(from, to, figure or None = silent, longest span)], 'ost': the
    ostinato's tokens, 'marks': [(beat, level)], 'pause': ..., 'goose': ..., 'cascade': ..., 'dry': [(from, to)]}
    (beats from the section start; _play_piano plays them). The motto planted alone in the intro (its left hand
    silent or one held bass), back at the start of up to two seams (interlude / build / the second B / the variation
    / the return: sequenced, an octave away or reharmonised), paid off at the climax's start (augmented / an octave up)
    and as a fragment in the coda's last bars, its long notes on the chord tones; the ostinato the intro's left hand
    alone and the A sections' figure, thinned in the coda; the pause the last bar before its seam (a held V7sus4, a
    silence, a high note, the bass alone - a fermata after a ritardando / subito / a diminuendo, the next section
    subito p / forte); the goosebump chord under the climax's peak note (or a return's first long note); the cascade
    the bars after the peak note on one chord."""
    from ..theory import Key
    from .composer import MOTTO_BANDS, _scale_step, motto_anchor, motto_cell, spell
    from ..pianist import ostinato_figure
    sd = tune.seed
    t_pc = Key(tune.key).tonic % 12
    minor = tune.key.split()[1] == 'minor'
    sharps = _key_sharps(tune.key)
    home = _key_pcs(tune)
    srng = random.Random(f"signature:{sd}")
    names = [s_['name'] for s_, *_ in plan]
    pk = next((i for i, (s_, *_) in enumerate(plan) if s_.get('peak')), None)
    top = max((p for *_, p in plan[pk][2]), default=96) if pk is not None and plan[pk][2] else 96
    for s_, *_ in plan:
        s_['_sig'] = {}
    plan[0][0]['_moves'] = sig
    octave = '0' if (g.plan.get('lh') or {}).get('bass_lo') else 'o'     # (the bass in octaves: not under a raised
    #                                                                     bass_lo - the e-piano's hand)

    def entry(i):
        return plan[i][0]['_sig']

    def tonic_of(sec):
        return sec['_key'][1] % 12 if sec.get('_key') else t_pc

    def pcs_of(sec):
        return set(sec['_key'][2]) if sec.get('_key') else set(home)

    def put(i, r0, cell, role, ceiling):
        """The cell's notes at r0 of section i over its line (the notes there go; one before held at most to r0)."""
        sec, ch, mel, L = plan[i]
        if sec.get('_key'):
            sh = _fold(sec['_key'][0] % 12)
            pcs = pcs_of(sec)
            cell = [(st, du, p + sh if (p + sh) % 12 in pcs else _scale_step(p + sh, -1, pcs)) for st, du, p in cell]
        while cell and max(p for *_, p in cell) >= ceiling:
            cell = [(st, du, p - 12) for st, du, p in cell]
        if cell and min(p for *_, p in cell) < 64 and max(p for *_, p in cell) + 12 < ceiling:
            cell = [(st, du, p + 12) for st, du, p in cell]     # (over the left hand's register: round g4)
        notes = []
        for st, du, p in cell:
            if r0 + st >= L - 1e-6:
                break
            du = min(du, L - r0 - st)
            if du >= 1.0 - 1e-6:
                p = _snap(p, _chord_at(ch, r0 + st))
            notes.append((r0 + st, du, p))
        if len(notes) < 3:
            return False
        if max(p for *_, p in notes) >= ceiling and min(p for *_, p in notes) - 12 >= 60:
            notes = [(st, du, p - 12) for st, du, p in notes]    # (snapped onto the ceiling: round g12, 64039's
            #                                                     build motto on the climax's peak note)
        z = max(st + du for st, du, _ in notes)
        keep = [(st, min(du, r0 - st), p) if st < r0 - 1e-6 else (st, du, p) for st, du, p in mel
                if st < r0 - 1e-6 or st >= z - 1e-6]
        # (round g12, all seven judges: VYDA's climax bar 38 empty - the payoff's last note ended on beat 2, the line's
        # note under it was cut: a line note the cell covered that sounds a beat+ past it is struck again at its end)
        nxt = min((st for st, *_ in keep if st >= z - 1e-6), default=L)
        late = [(z, min(st + du, nxt) - z, _snap(p, _chord_at(ch, z))) for st, du, p in mel
                if r0 - 1e-6 <= st < z - 1e-6 and min(st + du, nxt) - z >= 1.0 - 1e-6]
        if late and nxt - z >= 1.0 - 1e-6:
            keep.append(max(late, key=lambda n: (n[1], n[2])))
        elif nxt - z >= meter - 1e-6 and role == 'payoff' and _chord_at(ch, z):   # (none: a falling link, a tone
            tn = _tones(_chord_at(ch, z))              # of the chord there under the cell's last note, held to the line)
            q = max((c for c in range(notes[-1][2] - 5, notes[-1][2]) if c % 12 in tn), default=None)
            if q is not None:
                keep.append((z, nxt - z, q))
        # (round g13, four judges: TCMN 38 - the payoff's last note held 4 beats over the bar line, the bar "empty
        # until 3.67": an inner voice under it at the bar line, a tone of the chord there - MOTTO_HELD)
        st_, du_, p_ = notes[-1]
        b_ = meter * (int(st_ // meter + 1e-6) + 1)
        if role == 'payoff' and st_ + du_ - b_ >= MOTTO_HELD - 1e-6 and _chord_at(ch, b_):
            tn = _tones(_chord_at(ch, b_))
            q = max((c for c in range(p_ - 9, p_ - 2) if c % 12 in tn and c >= 60), default=None)
            if q is not None and not any(b_ - 1e-6 <= x[0] < b_ + 1.0 for x in keep):
                keep.append((b_, st_ + du_ - b_, q))
        plan[i] = (sec, ch, sorted(keep + notes), L)
        entry(i).setdefault('motto', []).append((r0, z, role, notes))
        return True
    # ---- the signature ostinato: the intro's left hand alone, the A sections' figure, thinned in the coda
    if 'ostinato' in sig:
        x = sig['ostinato']
        toks = ostinato_figure(x['grid'], x['contour'], x['span'], x['colour'], x['bass'] if octave == 'o' else 'one')
        thin = ' '.join(t if k % 2 == 0 or t in ('0', 'o') else '-' for k, t in enumerate(toks.split()))
        # (round g9, all five judges: DMZT's 16th ostinato under every A statement, 14-16 attacks a bar, "crowds the
        # tune" - a figure faster than OST_UNDER is planted whole in the intro, the theme's statements play it thinned)
        fast = x['grid'] > OST_UNDER.get(meter, 99)
        for i, (sec, ch, mel, L) in enumerate(plan):
            n = sec['name']
            if n == 'intro':
                sec['lh_only'] = x['lh_only']
                plan[i] = (sec, ch, [m for m in mel if m[0] >= x['lh_only'] * bar - 1e-6], L)
                entry(i)['ost'] = toks
            elif 'part' in sec and n.startswith('A') and not sec.get('peak'):
                entry(i)['ost'] = thin if fast else toks
            elif n == 'coda':
                entry(i)['ost'] = thin
    # ---- the motto: planted, recurring at the seams, paid off at the climax, closing the coda
    if 'motto' in sig:
        x = sig['motto']
        a1 = sorted(tune.melody.get('A1') or tune.melody.get('A') or [])
        lo_, hi_ = MOTTO_BANDS.get(x.get('register'), (67, 81))
        anchor = motto_anchor(x['kind'], a1[:4], home, t_pc, lo_, hi_, x.get('anchor', 'head'), minor)
        cell = motto_cell(x['kind'], x, anchor, home, t_pc, minor)
        span = max(st + du for st, du, _ in cell)
        if 'intro' in names:
            i = names.index('intro')
            sec = plan[i][0]
            r0 = (sec.get('lh_only') or 0) * bar if 'ostinato' in sig else 0.0
            if 'ostinato' not in sig:
                sec['lh_only'] = 0
            if put(i, r0, cell, 'plant', top):
                z = entry(i)['motto'][-1][1]
                if 'ostinato' not in sig:              # (over the ostinato: the piece's two identities together)
                    entry(i).setdefault('lh', []).append((r0, z, None if x['exposure'] == 'alone' else '0', None))
                entry(i).setdefault('marks', []).append((r0, x['dyn']))
        # (round g10: the theme's first return after the climax states the head - POST_RETURN - not the motto)
        post = next((n for n in names[pk + 1:] if n in RETURNS), None) if pk is not None and _sung(g.plan) else None
        seams = [n for n in ('inter', 'build', 'B2') if n in names] + \
            [n for n in ('A3', 'A4') if n in names and (pk is None or names.index(n) < pk or n == 'A4') and n != post]
        srng.shuffle(seams)
        for n in seams[:2]:
            tf = srng.choice(('sequence', 'octave', 'reharm'))
            c2 = cell
            if tf == 'sequence':
                c2 = [(st, du, _scale_step(p, 1, home)) for st, du, p in cell]
            elif tf == 'octave':                       # (an octave down only over the left hand's register:
                up_ = 12 if max(q for *_, q in cell) + 12 < top else -12        # round g4, HNGF 27 D4)
                if min(q for *_, q in cell) + up_ < 64:
                    up_, tf = 0, 'sequence'
                c2 = [(st, du, p + up_) if up_ else (st, du, _scale_step(p, 1, home)) for st, du, p in cell]
            put(names.index(n), 0.0, c2, 'recur:' + tf,       # (before a sung climax: PRE_TOP under its peak)
                top - (PRE_TOP if _sung(g.plan) and pk is not None and names.index(n) < pk else 0))
        if pk is not None:
            how = x['payoff']
            # (augmented within two bars: no holes; round g9 - ECYA's waltz climax opened on two notes held two bars
            # each: no augmented note longer than a bar)
            aug = 'augment' in how and 2 * span <= 2 * bar + 1e-6 and 2 * max(du for _, du, _ in cell) <= meter + 1e-6
            c2 = [(2 * st, 2 * du, p) for st, du, p in cell] if aug else list(cell)
            while max(p for *_, p in c2) + 12 < top - (0 if 'octave' in how else 2):
                c2 = [(st, du, p + 12) for st, du, p in c2]          # (in the climax's register, under its peak)
            pmel = plan[pk][2]
            pst = min((st for st, du, p in pmel if p == top), default=1e9)
            # (round g12: the payoff at the climax's start displaced the head there - ERDL, NKTZ, LESU "the climax is
            # not the head", three judges and more: a sung climax opens with the head, the payoff after its first
            # statement - MOTTO_PAYOFF - or none at the climax)
            r0 = MOTTO_PAYOFF['after'] * meter * (2 if arrival == 'fragment' else 1) if _sung(g.plan) else 0.0
            if r0 + max(st + du for st, du, _ in c2) > pst - 1e-6:
                c2 = list(cell)                      # (the peak note comes first: the motto as planted)
            if r0 + max(st + du for st, du, _ in c2) <= pst - 1e-6:
                put(pk, r0, c2, 'payoff', top)
            elif pst < 1e8:                            # (round g13: no room before the peak - 11 % of the set
                r1 = meter * (int(pst // meter) + 1)   # slots lost the payoff: it answers the peak, the bar after it)
                if r1 + span <= plan[pk][3] - 1e-6:
                    put(pk, r1, list(cell), 'payoff', top)
        if 'coda' in names:
            i = names.index('coda')
            L = plan[i][3]
            frag = cell[:4]
            frag[-1] = (frag[-1][0], max(2.0, frag[-1][1]), frag[-1][2])
            if L >= 2 * bar - 1e-6:
                put(i, L - 2 * bar, frag, 'close', top)
    # ---- the suspended pause: the last bar before its seam
    if 'pause' in sig and pk is not None:
        x = sig['pause']
        j = {'climax': pk,
             'return': next((k for k in range(pk + 1, len(plan)) if names[k].startswith('A')), None),
             'coda': names.index('coda') if 'coda' in names else None}[x['seam']]
        if (j is None or j == 0) and x['seam'] == 'return' and 'coda' in names:
            j = names.index('coda')                    # (round g9: a pause moved off the climax seam stays off it -
        if j is None or j == 0:                        # composer.arrival_pause)
            j = pk
        i = j - 1
        if i >= 0:
            sec, ch, mel, L = plan[i]
            tsec = plan[j][0]
            z0 = L - bar
            sec['fermata'] = x['hold']
            sec.pop('cadenza', None)
            if x['approach'] == 'rit':
                sec['rit'] = sec.get('rit') or 0.8
            else:
                sec.pop('rit', None)
            if x['approach'] == 'dim':
                entry(i).setdefault('marks', []).append((z0, 'pp'))
            kind = x['kind']
            if i == pk and kind not in PAUSE_EXIT:     # (round g13: CNCJ 46, six judges - "the climax stops dead":
                kind = PAUSE_EXIT[0]                   # one C5 over a lone F2, then A3 at v42)
            if kind == 'sus_hold' and sec.get('_final'):
                kind = 'rest'                          # (round g11: the theme's last statement keeps its home
            last = _chord_at(ch, z0)                   # cadence - FINAL_A: the tonic struck, then the silence)
            if kind == 'sus_hold':
                tt = tonic_of(tsec)
                sym = spell((tt + 7) % 12, sharps, 7) + '7sus4'
                ch = _last_bar(ch, L, bar, sym)
                q = next(q for q in range(72, 84) if q % 12 == tt)
                v = next(v for v in range(q - 1, q - 12, -1) if v % 12 == (tt + 7) % 12)
                mel = [m for m in mel if m[0] < z0 - 1e-6] + [(z0, bar, v), (z0, bar, q)]
                entry(i).setdefault('lh', []).append((z0, L, 'R', None))
            elif kind == 'rest':
                mel = [(st, min(du, z0 + 1.0 - st), p) for st, du, p in mel if st < z0 + 1.0 - 1e-6]
                entry(i).setdefault('lh', []).append((z0, L, '0 1 3 2', 1.0))
                entry(i)['dry'] = [(z0 + 1.0, L + 0.25)]
            elif kind == 'high_note':
                tn = _tones(last)
                q = max((q for q in range(76, top - 1) if q % 12 in tn), default=None)
                if q is not None:
                    mel = [(st, min(du, z0 - st), p) for st, du, p in mel if st < z0 - 1e-6] + [(z0, bar, q)]
                    entry(i).setdefault('lh', []).append((z0, L, None, None))
            else:                                    # bass_only
                mel = [(st, min(du, z0 - st), p) for st, du, p in mel if st < z0 - 1e-6]
                entry(i).setdefault('lh', []).append((z0, L, octave, None))
            plan[i] = (sec, ch, mel, L)
            entry(i)['pause'] = dict(x, at=z0, target=names[j])
            # (round g10: AHVN's climax after its pause entered subito p, under the build - four judges; KNUB's coda
            # at v88-96 after its pause: a pause into the climax is followed by a forte entry, one after it by a
            # soft one)
            entry(j)['after'] = 'f' if j == pk else 'p' if pk is not None and j > pk else \
                'p' if x['after'] == 'subito_p' else 'f'
    # ---- the goosebump chord: under the climax's peak note (or the return's first long note)
    if 'goose' in sig and pk is not None:
        x = sig['goose']
        i = pk
        if x['where'] == 'return':
            i = next((k for k in range(pk + 1, len(plan)) if names[k].startswith('A') and plan[k][2]), pk)
        sec, ch, mel, L = plan[i]
        if i == pk:
            cands = sorted(mel, key=lambda m: (-m[2], m[0]))
            cands = cands[:1] + [m for m in cands[1:] if m[1] >= 1.0 - 1e-6]
        else:
            cands = [m for m in mel if m[1] >= 1.0 - 1e-6][:6]
        mode = 'minor' if minor else 'major'
        degs = [x['degree']] + [d for d in GOOSE[mode] if d != x['degree']]
        tt = tonic_of(sec)
        hit = None
        for d in degs:
            off, q = GOOSE[mode][d]
            r = (tt + off) % 12
            sym = spell(r, sharps, off) + q
            ok = _tones(sym) | {(r + 2) % 12}
            m = next((m for m in cands if m[2] % 12 in ok and m[0] < L - 0.5), None)
            if m is not None:
                hit = (d, sym, m)
                break
        if hit:
            d, sym, m = hit
            a, z = m[0], min(L, m[0] + max(m[1], 2.0))
            ch = _splice(ch, a, z, sym)
            plan[i] = (sec, ch, mel, L)
            entry(i)['goose'] = dict(x, degree_played=d, sym=sym, at=a, end=z, pitch=m[2])
            entry(i).setdefault('lh', []).append((a, z, 'R' if x['voicing'] == 'rolled' else '0+3 - - - 1 - 3 -',
                                                  None))
            if x['dyn'] == 'accent':
                entry(i).setdefault('marks', []).append((a, 'ff'))
            else:
                entry(i).setdefault('marks', []).extend([(a, 'p'), (z, 'mf')])
    # ---- the cascade: the link out of the climax - its last bar, one chord, under a held melody note, the hands
    # leapfrogging down (blind round g4: the cascade after the peak note read as "mechanical", "texture, not music" -
    # it took the bars after the peak from the melody; now the melody holds over it and the peak keeps its theme)
    if 'cascade' in sig and pk is not None:
        x = sig['cascade']
        sec, ch, mel, L = plan[pk]
        w1 = L - (bar if entry(pk).get('pause') else 0.0)      # (the pause's bar stays the pause's)
        w0 = w1 - bar
        # (the melody note struck in the bar's first beat, or the one ringing into it from the beat before: held)
        held = [m for m in sorted(mel) if w0 - 1.0 - 1e-6 <= m[0] < w0 + 1.0 - 1e-6]
        if w0 >= bar - 1e-6 and held and held[-1][2] >= 67:
            hst, _, hp = held[-1]
            sym = _chord_at(ch, w0)
            ch = _splice(ch, w0, w1, sym)
            mel = [(st, w1 - st, p) if st == hst else (st, du, p) for st, du, p in mel
                   if st <= hst + 1e-6 or st >= w1 - 1e-6]
            plan[pk] = (sec, ch, mel, L)
            a0 = max(w0, hst + 0.5)
            entry(pk)['cascade'] = dict(x, at=a0, end=w1, sym=sym, top=min(89, hp - 2))
            entry(pk).setdefault('lh', []).append((a0, w1, '0', None))
            land = {'roll': 'R', 'bass': octave}.get(x['landing'])
            if land:
                k = pk if w1 < L - 1e-6 else pk + 1
                if k < len(plan):
                    r = w1 if k == pk else 0.0
                    entry(k).setdefault('lh', []).append((r, r + bar, land, None))


def _cascade_notes(c: dict, a: float, meter: int, floor: int = 31) -> tuple[list, list]:
    """The cascade's notes from beat a (docs/PIANO_MOVES.md 5.5): its chord's tones from c['top'] down 2.5-3.5
    octaves, in groups of c['group'] played by the hands in turn (c['pattern'] 'RL' / 'RRL'), each group starting
    a little lower than the last - the waterfall - on c['grid'], the touch falling about two levels, each group's
    first note leaning; nothing under `floor` (the genre's left-hand bass_lo). A group starting under `split` (C4) is
    the left hand's whatever the pattern (blind round g4: the right hand fell into the left hand's register).
    -> (right hand, left hand) [Note]."""
    from ..patterns import Note
    tn = _tones(c['sym'])
    hi = max(q for q in range(c['top'] - 11, c['top'] + 1) if q % 12 in tn)
    lo = max(floor, hi - 32)
    T = [q for q in range(hi, lo - 1, -1) if q % 12 in tn]
    split = 60
    D = c['end'] - c['at']
    n = max(c['group'] * 2, int(round(D / c['grid'])))
    G = max(2, -(-n // c['group']))
    hands = list(c['pattern'])
    rh, lh = [], []
    k = 0
    for gi in range(G):
        s0 = int(round(gi * (len(T) - c['group']) / max(1, G - 1)))
        for j in range(c['group']):
            if k >= n:
                break
            t = a + k * c['grid']
            p = T[min(len(T) - 1, s0 + j)]
            v = 86 - 26 * k / max(1, n - 1) + (5 if j == 0 else 0)
            nt = Note(t, c['grid'] * 2.5, p, int(round(v)))
            (rh if hands[gi % len(hands)] == 'R' and T[min(len(T) - 1, s0)] >= split else lh).append(nt)
            k += 1
    return rh, lh


# ------------------------------------------------------------------------------------------------ PIANO_DIVERSE

PIANO_DIVERSE = None
"""Round p-div's switch (genres.piano_diverse; off = None: every piece bit-identical to the code before it): the
anti-template draws below in build_piano and, in run.candidates, the score as a gate with the set's memory choosing
among the near-ties."""

PIANO_DIVERSE_ON = {
    'genres': ('new-age-piano',),
    # run.candidates: the candidates within 'gate' points of the slot's best pass (the best-of-N blind test,
    # 2026-10-24: the judges follow the score only for gaps over ~2.6; ties within ~1.5 are noise), the one most
    # different from the set so far is played (run.diverse_pick, run.DIVERSE_FEATURES)
    # (round p-div2: p-div's 1.5 picked heads ~0.9 points weaker that the judges heard - 0.8, and inside it the
    # distance pays 'weigh' per point under the best: a near-tie wins only by being clearly more different)
    # (round p-div3: at 0.8 the pick kept the best in 23 of 28 slots and the set win went - 1.2 and 0.02 a point:
    # another tune in 12 of 28 slots with a memory, 4 sets measured)
    'gate': 1.2,
    'weigh': 0.02,
    # the candidates' dynamics metrics (composer.score parts): the pick's sub-scores on them never under the best's
    # by more than 'dyn_slack' summed (p-div: 4 flat_dynamics render rejects vs 1, two of them the diverse pick)
    'dyn_metrics': ('ph_vel', 'ph_vspread', 'vel_jump12'), 'dyn_slack': 0.05,
    # the climax's left hand, one pattern per piece per meter ({name: ({figure: weight}, weight)}; the blind test's
    # first tell: 'broad' - the octave on 1, the chord on 2 and 4, its 10th on 3 - in 4-6 of 6 pieces)
    # (round p-div: the sparse hands - rolled2, broad2, the waltz's rolled / open bar - "the climax sags, 2.1 attacks
    # a bar"; the octave pairs on every beat (walk10) and the low octave on 1 and 3 (octdrive) the sets' tells: only
    # running 8ths / triplets now, the bass octave at most once a bar)
    'climax_lh': {4: {'big': ({'big': 1.0, 'arc8': 0.3}, 0.8), 'nocturne': ({'nocturne': 1.0, 'big': 0.3}, 1.0),
                      'arc': ({'arc8': 1.0, 'big': 0.4}, 1.0), 'rise': ({'rise8': 1.0, 'nocturne': 0.4}, 0.8)},
                  3: {'arp': ({'waltz_arp': 1.0, 'barcarolle': 0.5}, 1.0), 'barc': ({'barcarolle': 1.0, 'waltz_arp': 0.4}, 0.8),
                      'arc': ({'waltz_arc': 1.0, 'waltz_arp': 0.5}, 0.8)}},
    # the quiet peak's hand (a summit at mf: the hand stays a ballad's)
    'quiet_lh': {4: {'tenths': 1.0, 'flow': 0.6, 'rolled2': 0.5}, 3: {'waltz_open': 1.0, 'waltz_arp': 0.6}},
    # where the climax's peak falls (share of the piece, as planned: optional sections moved before / after it, the
    # peak's place inside the climax 'at'); the blind test: every peak at 64-73 %
    # (round p-div2: p-div's early peak dropped / shortened the sections before it - "no build": now the build and
    # everything before the climax stay as drawn, the material after it grows - longer bars, an optional section)
    # (round p-div3: without dropping the build the early place hardly moved the peak (median 0.68) and its long
    # tail lost NDBW - out)
    'place': {'golden': ((0.63, 0.72), 1.0), 'late': ((0.75, 0.85), 0.9)},
    'at': {'golden': 0.6, 'late': 0.75},
    # (round p-div3 drew the sung climax's statement instead of the set slot's octaves / chords - sequenced,
    # reharmonised, in canon: it thinned the climax, "2.2 right-hand attacks a bar", per piece -0.40 - reverted in
    # p-div4: the set slot's anthem plays)
    # the arc's kind: one summit; a first wave in the chorus (B1 to f, a level under the climax); (p-div's quiet
    # summit at mf went: the climax sagged, the dynamics flat)
    'kind': {'single': 1.0, 'double': 0.35},
    # the bloom's second stage (the sets' tell: every build ends in left-hand 16ths / triplets): as drawn (16ths /
    # triplets from its reach), 'eighths' - the first stage's 8ths throughout, rising in register instead, 'late' -
    # the 16ths only in its last quarter
    'bloom2': {'run': 1.0, 'eighths': 0.8, 'late': 0.6},
    'bloom_eighths': {4: {'flow': 1.0, 'color': 0.6, 'up': 0.3}, 3: {'waltz_arp': 1.0, 'barcarolle': 0.6, 'waltz2': 0.4}},
    # the ending gesture (the blind test: a ritardando to ~50 BPM, then a 4-note root-position left-hand chord under a
    # held right-hand chord, in every piece): the rolled chord; an open chord (no third, the bass octave); a plagal
    # bar (IV / iv) before it; a deceptive bar (vi / VI) then the tonic; the theme's opening cell alone, dying on one
    # note over one low note; an arpeggio up the keyboard into the last chord
    'ending': {'roll': 0.5, 'open': 1.0, 'plagal': 0.9, 'deceptive': 0.8, 'line': 0.8, 'arpeggio': 0.9},
    'end_rit': {'roll': 0.8, 'open': 0.86, 'plagal': 0.84, 'deceptive': 0.84, 'line': 0.9, 'arpeggio': 0.72},
    # the interlude from the theme instead of the intro's last bars: its opening cell, then the cell a step down and a
    # held tone (fragment); its first bar over two (augment); its answer bars (answer) - over the intro's link chords
    'interlude': {'fragment': 1.0, 'augment': 0.8, 'answer': 0.8},
}
"""PIANO_DIVERSE's tables (genres.piano_diverse(True) copies them in). Every draw per piece from its own dice
(f"pdiv:{seed}"): the candidates of a slot differ in them, run.diverse_pick plays the one the set has heard least."""


def _diverse(tune: Tune, g: Genre) -> dict | None:
    """The piece's PIANO_DIVERSE draws {climax_lh, place, kind, ending, interlude} (None: off, another genre)."""
    D = PIANO_DIVERSE
    if not D or g.name not in D['genres']:
        return None
    r = random.Random(f"pdiv:{tune.seed}")
    hands = D['climax_lh'][3 if tune.meter == 3 else 4]
    return {'climax_lh': _pick(r, {k: w for k, (_, w) in hands.items()}),
            'place': _pick(r, {k: w for k, (_, w) in D['place'].items()}),
            'kind': _pick(r, D['kind']), 'ending': _pick(r, D['ending']), 'interlude': _pick(r, D['interlude']),
            'bloom2': _pick(r, D['bloom2'])}


def _peak_est(tune: Tune, spec: dict, drawn: list, meter: int, stretch: int, at: float = 0.65) -> float | None:
    """Where the climax's peak falls as planned (share of the piece: the sections' mean bars, the peak at `at` of the
    climax) - _tail_cap's estimate."""
    def beats(n):
        x = spec[n]
        b = x.get('bars')
        if isinstance(b, dict) and b:
            return meter * stretch * sum(w * sum(z - a for a, z in k) for k, w in b.items()) / sum(b.values())
        if 'part' in x:
            return tune.part_beats(x['part'])
        fr = tune.intro if x.get('frame') == 'intro' else tune.tag
        return sum(b_ for _, b_ in fr.get('changes') or [])
    pk = next((i for i, n in enumerate(drawn) if spec[n].get('peak')), None)
    if pk is None:
        return None
    tot = sum(beats(n) for n in drawn)
    return (sum(beats(n) for n in drawn[:pk]) + at * beats(drawn[pk])) / max(1e-9, tot)


PEAK_DROP = {'early': (), 'late': ('B2',)}
"""The body sections _place_peak may leave out for a drawn place (PIANO_DIVERSE): a late peak the chorus's reprise
after it, any 'chance' section after the peak; an early one nothing (round p-div2: p-div's early peak left out a
theme statement / the interlude before the climax - "no build" - the material before the peak stays as drawn, an
optional section after it comes in)."""


def _place_peak(tune: Tune, spec: dict, drawn: list, meter: int, stretch: int, dv: dict, waltz: bool) -> list:
    """`drawn` with its climax moved toward the drawn place (PIANO_DIVERSE_ON['place'], the measured climax_x; the
    plan's estimate runs ~0.03 over it): a section dropped - an optional one, or PEAK_DROP's before the peak (early) /
    after it (late) - or an optional one the dice left out added, greedily the move nearest the range's middle, until
    the estimate is inside it (a waltz only drops)."""
    lo, hi = (x + 0.03 for x in PIANO_DIVERSE['place'][dv['place']][0])
    names = [n for n in spec if not (spec[n].get('feels') and tune.feel not in spec[n]['feels'])]
    cur = list(drawn)
    for _ in range(4):
        x = _peak_est(tune, spec, cur, meter, stretch)
        if x is None or lo - 1e-9 <= x <= hi + 1e-9:
            break
        pk = next(i for i, n in enumerate(cur) if spec[n].get('peak'))
        opts = []
        for i, n in enumerate(cur):                    # (drop a section - never one before the peak)
            if n == 'intro' or spec[n].get('peak') or i < pk:
                continue
            if spec[n].get('chance', 1.0) < 1.0 or (dv['place'] == 'late' and n in PEAK_DROP['late']):
                opts.append([m for m in cur if m != n])
        if not waltz:
            for n in names:                            # (add one the dice left out, at its place in the plan)
                if n not in cur and n != 'intro' and spec[n].get('chance', 1.0) < 1.0:
                    want = set(cur) | {n}
                    opts.append([m for m in names if m in want])
        best, bd = None, abs(x - (lo + hi) / 2)
        for o in opts:
            if not any(spec[m].get('peak') for m in o):
                continue
            y = _peak_est(tune, spec, o, meter, stretch)
            if y is not None and abs(y - (lo + hi) / 2) < bd - 1e-9:
                best, bd = o, abs(y - (lo + hi) / 2)
        if best is None:
            break
        cur = best
    return cur


def _bias_bars(sec: dict, side: str, place: str) -> dict:
    """A section's drawn 'bars' pinned to its shortest / longest choice so the peak moves toward its drawn place
    (PIANO_DIVERSE): an early peak - the sections after it long (the ones before it as drawn); a late peak the ones
    before it long, after it short."""
    b = sec.get('bars')
    if place == 'golden' or not isinstance(b, dict) or len(b) < 2:
        return sec
    size = lambda k: sum(z - a for a, z in k)
    if place == 'early' and side == 'before':          # (round p-div2: the build keeps its drawn length)
        return sec
    short = (side == 'before') == (place == 'early')
    k = (min if short else max)(b, key=lambda k: (size(k), str(k)))
    return dict(sec, bars={k: 1.0})


def _diverse_sec(sec: dict, dv: dict, order: list, pk_i: int | None, name: str) -> dict:
    """A section with the arc's kind (PIANO_DIVERSE_ON['kind']): a quiet summit at mf (one voice under the line), a
    first wave - the chorus before the climax (else the build) rising to f; the coda's ritardando by the ending
    ('end_rit': no slowing to ~50 BPM before every last chord)."""
    if name == 'coda' and isinstance(sec.get('rit'), float) and dv['ending'] != 'roll':
        sec = dict(sec, rit=max(sec['rit'], PIANO_DIVERSE['end_rit'][dv['ending']]))   # (the ending's own breadth)
    if pk_i is None:
        return sec
    if name in order and not sec.get('peak'):
        sec = _bias_bars(sec, 'before' if order.index(name) < pk_i else 'after', dv['place'])
    if dv['kind'] == 'quiet' and sec.get('peak'):
        sec = dict(sec, dyn=('mp', 'mf', 'p'), **({'harmonize': 1} if sec.get('harmonize') else {}))
    elif dv['kind'] == 'double' and name in order[:pk_i]:
        wave = 'B1' if 'B1' in order[:pk_i] else 'build' if 'build' in order[:pk_i] else None
        if name == wave:
            sec = dict(sec, dyn=('mp', 'mf', 'mp'))     # (round p-div3: at f it left the climax no headroom)
    return sec


def _inter_theme(tune: Tune, ch: list, keep: tuple, meter: int, bar: float, kind: str) -> list | None:
    """The interlude's line from the theme (PIANO_DIVERSE_ON['interlude']) over the intro's bars `keep` (its link
    chords): 'fragment' the head's opening cell, then the cell a step down ending on a held tone; 'augment' the head's
    first bar over two; 'answer' the theme's bars 3-4 - refitted to the chords, in the theme's register."""
    from .composer import Harm, _refit, _scale_step, _slice_changes
    src = sorted(tune.melody.get(tune.parts[0]) or [])
    if not src or not keep:
        return None
    a, z = min(keep) * bar, (max(keep) + 1) * bar
    L = z - a
    key = set(_key_pcs(tune))
    if kind == 'answer':
        notes = [(st - 2 * bar, du, p) for st, du, p in src if 2 * bar - 1e-6 <= st < 2 * bar + L - 1e-6]
        kind = kind if notes else 'augment'
    if kind == 'augment':
        notes = [(2 * st, 2 * du, p) for st, du, p in src if st < L / 2 - 1e-6]
    elif kind == 'fragment':
        cell = [n for n in src if n[0] < bar - 1e-6][:3]
        c0 = cell[0][0]
        one = [(st - c0, du, p) for st, du, p in cell]
        two = [(bar + st, du, _scale_step(p, -1, key)) for st, du, p in one]
        end = two[-1][0]
        notes = one + two[:-1] + [(end, L - end, two[-1][2])]
    notes = [(st, min(du, L - st), p) for st, du, p in sorted(notes) if 0 <= st < L - 1e-6]
    if not notes:
        return None
    lo, hi = min(p for *_, p in src), max(p for *_, p in src)
    fit = _refit(notes, Harm(_slice_changes(ch, a, z), key), meter, lo, hi)
    return [(a + st, du, p) for st, du, p in fit if du > 1e-6]


def _climax_hand(dv: dict, meter: int) -> dict:
    """The climax's left-hand figure set (PIANO_DIVERSE_ON['climax_lh'] / ['quiet_lh'] for a quiet summit)."""
    m = 3 if meter == 3 else 4
    if dv['kind'] == 'quiet':
        return dict(PIANO_DIVERSE['quiet_lh'][m])
    return dict(PIANO_DIVERSE['climax_lh'][m][dv['climax_lh']][0])


def _end_pre(tune: Tune, ending: str, at: float, meter: int, top: int, rh: list) -> dict:
    """The bar before the last chord (PIANO_DIVERSE_ON['ending']): {'sym' its chord, 'notes' right-hand notes,
    'voicing' a rolled right-hand chord or None} - plagal IV / iv (the top a common tone where it can), deceptive vi /
    VI, the single line (the head's opening cell over the tonic, alone), the arpeggio (the left hand only)."""
    from ..patterns import Note
    from .composer import Harm, _refit
    T, mode = tune.key.split()[0], tune.key.split()[1]
    minor = mode == 'minor'
    out = {'sym': tune.end_chord, 'notes': [], 'voicing': None}
    if ending in ('plagal', 'deceptive'):
        if ending == 'plagal':
            sym = _transpose_sym(T + ('m7' if minor else 'add9'), 5, tune.key)
        else:
            sym = _transpose_sym(T + ('maj7' if minor else 'm7'), 8 if minor else 9, tune.key)
        c = chord(sym)
        pcs = sorted({(c.root + i) % 12 for i in c.intervals if i < 12})      # (no 9th in the grip: no cluster)
        tp = min((q for q in range(top - 4, top + 3) if q % 12 in pcs), key=lambda q: (abs(q - top), q), default=top)
        out['sym'] = sym
        out['voicing'] = sorted({tp} | {tp - ((tp - pc) % 12 or 12) for pc in pcs if pc != tp % 12})[-4:]
    elif ending == 'line':
        src = sorted(tune.motif or tune.melody.get(tune.parts[0]) or [])
        cell = [n for n in src if n[0] < src[0][0] + meter - 1e-6][:4] if src else []
        if cell:
            c0 = cell[0][0]
            notes = [(st - c0, min(du, meter - 0.25 - (st - c0)), p) for st, du, p in cell]
            notes = [n for n in notes if n[1] > 0.1]
            fit = _refit(notes, Harm([(tune.end_chord, meter)], _key_pcs(tune)), meter, top - 7, top + 4)
            out['notes'] = [Note(at + st, du, p, 80) for st, du, p in fit if du > 1e-6]
    return out


def _end_hand(ending: str, final: bool, meter: int, voicing: list, pre: dict | None) -> tuple:
    """The left hand of the end bars (PIANO_DIVERSE_ON['ending']): (figure or None = silent, its options)."""
    if not final:
        if ending in ('plagal', 'deceptive'):
            return ('waltz_held' if meter == 3 else 'half'), None
        if ending == 'arpeggio':
            return ('end_arp3' if meter == 3 else 'end_arp'), {'cap': max(voicing) - 1, 'mirror': True}   # (up into
            #                                                                                   the last chord)
        return None, None                              # (the single line: no left hand)
    return ('end_bass' if ending in ('open', 'line', 'arpeggio') else 'roll'), None


def build_piano(tune: Tune, genre: Genre | None = None, arrangement: Arrangement | None = None) -> Song:
    """The Song of a tune of a 'piano' genre (plan['perform'] = 'piano'): plan['sections'] in order - each a part of
    the tune (its changes + melody; 'lift': the climax melody, Tune.out_melody) or a frame (the intro's / tag's vamp
    and line; keep_bars: only those bars of its line - the interlude's echoes; lh_only: the left hand alone first),
    drawn by its 'chance' - played by the ROMANTIC pianist: romantic.Score from the composed notes (touch per phrase,
    lean on long notes, cantabile, melody rubato over the left hand's time, a breath at every phrase end, the inner
    notes of its chords softer: inner=0.78), 3rds / 6ths under long notes or chords at the climax
    (romantic.harmonize), a broken-chord LEFT HAND per bar from the feel's figure set of the section (pianist.FIGURES,
    drawn, never twice running; the 'rest' figure where the melody breathes, 'into' the bar before the peak, 'end'
    under the last chord), the section's written dynamics (both hands, the left at a gentler slope), phrase rubato,
    a ritardando into every section end that asks for one, an inhale before the peak, a fermata after it, a calmer
    return (tempo), a cadenza flourish over the last dominant (romantic.fioritura, by the section's chance), a rolled
    final chord. Deterministic from tune.seed. The decisions above the notes are the arrangement record (arrange():
    the sections played, their options, hairpins, cadenzas, the touch window - endless.arrangement): `arrangement`
    (else tune.arrangement, a decoded student piece's) plays another one.
    (The body model - humanize, another branch - hooks in after Score.perform: one gesture per phrase over both
    hands' timing and touch; it reads s.endless_sections / the phrases here.)"""
    g = genre or get(tune.genre)
    meter, sd = tune.meter, tune.seed
    rng = random.Random(f"piano:{sd}")
    s = Song(tune.title, tempo=tune.tempo, key=tune.key, seed=sd % 100000 + 1, tail=7, meter=(meter, 4))
    # ---- the arrangement first (drawn from the seed unless given), then the material of every section played from it
    # (the record's decisions replayed over the same dice: every random stream stays where it was)
    if arrangement is None:
        arrangement = getattr(tune, 'arrangement', None) or arrange(tune, g)
    dice = Dice('piano', arrangement)
    plan = _piano_plan(tune, g, rng, dice)
    _piano_draws(tune, g, plan, rng, dice)
    A = dice.out
    return _play_piano(tune, g, s, plan, rng, A)


def _set_pins(tune: Tune, g: Genre) -> dict:
    """The tune's set-level draws (Tune.arrange: composer.set_plan / compose); a tune without them - a decoded learned
    tune - gets the draws compose() makes for its seed."""
    if g.plan.get('set') and not getattr(tune, 'arrange', None):
        from .composer import set_draws
        return set_draws(g, random.Random(f"set-draws:{g.name}:{tune.seed}"),
                         ctx={'key': tune.key, 'tempo': tune.tempo, 'feel': tune.feel})
    return getattr(tune, 'arrange', None) or {}


WALTZ_FORM = {'chance': 0.3, 'short': ('A2', 'A3', 'A4', 'B1', 'B2', 'build'), 'after_a1': ('A2',),
              'bars': {((0, 4), (6, 8)): 1.0, ((0, 7),): 0.6}, 'most': 86, 'least': ((0, 2), (6, 8))}
"""A waltz's length (plan['form_bars']: every form bar two 3/4 bars; blind round g6, FUKP: 99 bars, "too long for
its material"; 104 bars a waltz on average): an optional section (a 'chance' one but the intro) by 'chance' x its own,
no 'after_a1' section right after A1 (its 8 form bars are a 16-bar period: the theme twice), the chorus, the returns
and the build ('short') a 6- or 7-bar form phrase ('bars', _arrange) - ~80-90 bars. Round g11 (three judges: ELNQ's
95-bar waltz "goes on too long"): at most 'most' 3/4 bars as planned - the optional sections (a 'chance' one: the
interlude first, then the latest) dropped until it fits, then the short sections at their shortest (_waltz_cap). Round
g14 (all seven judges: PPHK's 93-bar waltz "outstays its material"; the waltzes played 80-94 bars under 95 planned): 86
planned, and where every short section at its shortest is still over, the build, the return before the climax, then
the chorus play 'least' (the phrase's first two form bars and its cadence)."""


CLIMAX_STILL = ('hold',)
"""The waltz bar moves (plan['moves'], _moving_bass) its climax does not draw (round g13, six judges: PPHK's 16-bar
waltz climax "holds one chord per 2-4 bars", F#add9 four bars - every held chord's later bar moves there)."""

FINAL_A = {'bars': {4: 8, 3: 6}, 'close': 'I'}
"""The theme's last statement after the climax (round g11, four judges: ZVNR's / HABQ's A3 of 6 bars without a home
cadence, the tonic only in the coda): 'bars' form bars at least (per meter: a waltz's form bar is two 3/4 bars) and
its last bar the 'close' (_close: V7 then the tonic) - no tail, no deceptive cadence, no turnaround out of it."""

CODA = {'bars': {4: 0.7, 6: 1.0, 8: 0.5}, 'share': 0.1, 'least': 4}
"""The coda's bars at least (round g11: VBJZ's 3-bar coda after a rest, two judges; CDSQ's coda "a fade over new
pads", the head never back): a shorter tag is preceded by the theme's head, as many 2-bar units as it takes
(_coda_head). Round g12 (the g11 statistician: six codas copied A1's bars 3-8 note for note): the head comes back
changed, as a return does - augmented (its first bar over two, its chords stretched; a second unit its second bar so),
then liquidated (its opening cell a step lower, then one held chord tone: the theme dissolving into the tag). Round g13
(the g12 statistician: seven codas of exactly 7 bars): the bars at least a draw per tune ({bars: weight}, its own
dice). Round g14 (the g13 judges: MYUS / CPED's 9-bar codas "drag", the statistician: 15-21 bars after the peak, "codas
of 4-6 bars"): at most 'share' of the piece's bars before it (never under 'least') - a coda relative to the piece."""


def _final_a(sec: dict, bar: float, meter: int) -> dict:
    """The section dict of the theme's last statement (FINAL_A): '_final' marked, its drawn bars only the spans of
    FINAL_A['bars'] form bars or more (none: the whole part)."""
    need = FINAL_A['bars'].get(meter, 8)
    out = dict(sec, _final=True)
    if isinstance(sec.get('bars'), dict):
        ok = {k: w for k, w in sec['bars'].items() if sum(b - a for a, b in k) >= need}
        if ok:
            out['bars'] = ok
        else:
            out.pop('bars')
    return out


def _coda_head(tune: Tune, ch: list, mel: list, meter: int, bar: float, before: float = 0.0) -> tuple:
    """The coda (the tag's chords / melody) with the theme's head before it until it is CODA['bars'] bars long - the
    head varied (CODA: augmented, then liquidated; never A1's bars as played)."""
    L = sum(b for _, b in ch)
    unit = 2 * meter
    from .composer import Harm, _refit, _scale_step, _slice_changes
    a1 = tune.parts[0]
    k = 0
    need = _pick(random.Random(f"coda-bars:{tune.seed}"), CODA['bars'])
    if before:                                         # (round g14: relative to the piece - CODA['share'])
        need = min(need, max(CODA['least'], int(round(CODA['share'] * before / meter))))
    while L + k * unit < need * meter - 1e-6 and (k + 1) * unit <= tune.part_beats(a1) + 1e-6:
        k += 1
    if not k:
        return ch, mel
    src, chs = sorted(tune.melody[a1]), tune.changes[a1]
    key = _key_pcs(tune)
    h_ch, h_mel = [], []
    for j in range(k):
        t = j * unit
        if j < 2:                                      # (the head's bar j over two bars, its chords stretched)
            b0 = j * meter
            h_ch += [(sym, 2 * b) for sym, b in _slice_changes(chs, b0, b0 + meter)]
            h_mel += [(t + 2 * (st - b0), min(2 * du, unit - 2 * (st - b0)), p) for st, du, p in src
                      if b0 - 1e-6 <= st < b0 + meter - 1e-6]
            continue
        c_ = _slice_changes(chs, (j - 1) * unit, j * unit) or _slice_changes(chs, 0, unit)
        h_ch += c_                                     # (liquidated: the opening cell a step down, then held)
        cell = [n for n in src if n[0] < meter / 2 + 1e-6][:2] or src[:1]
        notes = [(st - cell[0][0], min(du, meter / 2), _scale_step(p, -1, set(key))) for st, du, p in cell]
        end = notes[-1][0] + notes[-1][1]
        notes.append((end, unit - end, notes[-1][2]))
        lo, hi = min(p for *_, p in src) - 2, max(p for *_, p in src)
        h_mel += [(t + st, du, p) for st, du, p in _refit(notes, Harm(c_, key), meter, lo, hi,
                                                          prev=h_mel[-1][2] if h_mel else None)]
    h_mel = [(st, du, p) for st, du, p in sorted(h_mel) if du > 1e-6]
    return h_ch + list(ch), h_mel + [(st + k * unit, du, p) for st, du, p in mel]


A_CAP = {'most': 3, 'minutes': 4.0}
"""The theme's statements by the piece's length (round g11, all five judges: HJJR's four near-identical A statements
in 4:48 at 59 BPM): more than 'most' A sections only in a piece under 'minutes' (its parts' and frames' beats at its
tempo) - else the theme's optional return before the climax goes (the song / late layouts' A3)."""


def _a_cap(tune: Tune, spec: dict, drawn: list) -> list:
    """`drawn` (the section names in order) with A_CAP's statements (a sung genre)."""
    def beats(n):
        x = spec[n]
        if 'part' in x:
            return tune.part_beats(x['part'])
        fr = tune.intro if x.get('frame') == 'intro' else tune.tag
        return sum(b for _, b in fr.get('changes') or [])
    As = [n for n in drawn if n[0] == 'A']
    if len(As) <= A_CAP['most'] or sum(beats(n) for n in drawn) / max(1, tune.tempo) <= A_CAP['minutes']:
        return drawn
    peak = next((i for i, n in enumerate(drawn) if spec[n].get('peak')), len(drawn))
    cut = next((n for n in reversed(drawn[:peak]) if n in As[1:] and spec[n].get('chance', 1.0) < 1.0), None)
    return [n for n in drawn if n != cut] if cut else drawn


TAIL = {'at': 0.66, 'drop': ('B2',)}
"""The tail after an early climax (round g12, two judges: WNTP's arch peaked at 59 % with 19 bars after it - "the
peak spent, then a long walk home"): where the climax's peak, as planned (the sections' mean bars, the peak at
_anthem's ~0.65 of the climax), falls before 'at' of the piece (the plan's mean bars run ~4 % over the played: a
peak under ~62 % as heard), the 'drop' sections after it go (the arch's B': A B C A' with the coda)."""


def _tail_cap(tune: Tune, spec: dict, drawn: list, meter: int, stretch: int) -> list:
    """`drawn` (the section names in order) without TAIL['drop']'s sections after an early climax (a sung genre)."""
    def beats(n):
        x = spec[n]
        b = x.get('bars')
        if isinstance(b, dict) and b:
            return meter * stretch * sum(w * sum(z - a for a, z in k) for k, w in b.items()) / sum(b.values())
        if 'part' in x:
            return tune.part_beats(x['part'])
        fr = tune.intro if x.get('frame') == 'intro' else tune.tag
        return sum(b_ for _, b_ in fr.get('changes') or [])
    pk = next((i for i, n in enumerate(drawn) if spec[n].get('peak')), None)
    drop = [n for n in drawn[pk + 1:] if n in TAIL['drop']] if pk is not None else []
    if not drop:
        return drawn
    at = sum(beats(n) for n in drawn[:pk]) + 0.65 * beats(drawn[pk])
    return [n for n in drawn if n not in drop] if at / sum(beats(n) for n in drawn) < TAIL['at'] else drawn


def _waltz_cap(tune: Tune, spec: dict, drawn: list, meter: int) -> tuple:
    """(`drawn`, {section: its bars}: the short sections') with a waltz's length under WALTZ_FORM['most'] bars as
    planned (a 'short' section's mean bars): the optional sections dropped, then the short sections and the intro at
    their shortest."""
    W = WALTZ_FORM
    bars_ = W['bars']
    short = sum(sum(b - a for a, b in k) * w for k, w in bars_.items()) / sum(bars_.values())

    def beats(n):
        x = spec[n]
        if 'part' in x:
            if x.get('_least'):
                return 2 * meter * sum(b - a for a, b in W['least'])
            return 2 * meter * short if n in W['short'] else tune.part_beats(x['part'])
        fr = tune.intro if x.get('frame') == 'intro' else tune.tag
        return sum(b for _, b in fr.get('changes') or [])
    out = list(drawn)
    opt = [n for n in out if spec[n].get('chance', 1.0) < 1.0 and n != 'intro']
    opt = [n for n in opt if n == 'inter'] + [n for n in reversed(opt) if n != 'inter']
    while opt and sum(beats(n) for n in out) / meter > W['most']:
        out.remove(opt.pop(0))
    pins = {n: bars_ for n in W['short']}
    if sum(beats(n) for n in out) / meter > W['most']:
        k = min(bars_, key=lambda k: sum(b - a for a, b in k))
        pins = {n: {k: 1.0} for n in W['short']}
        ib = spec.get('intro', {}).get('bars')
        if isinstance(ib, dict) and ib:
            pins['intro'] = {min(ib, key=lambda k: sum(b - a for a, b in k)): 1.0}
        # (round g14: PPHK 93 bars with every short section at its shortest - the shortest 'least' then, the
        # pre-climax sections first: the build, then the return before it, then the chorus)
        short = sum(b - a for a, b in k)
        for n in [x for x in ('build', 'A2', 'A3', 'B1', 'B2') if x in out and x in W['short']]:
            if sum(beats(x) for x in out) / meter <= W['most']:
                break
            pins[n] = {W['least']: 1.0}
            spec = dict(spec)
            spec[n] = dict(spec[n], _least=True)
    return out, pins


def _piano_plan(tune: Tune, g: Genre, rng: random.Random, dice: Dice) -> list:
    """The sections played and their material [(section, changes, melody, length)]: the arrangement's layout
    (plan['set']['layout'] {name: weight}; a section's 'layouts' names those it plays in - the tune's set-level pin or
    drawn), the chance drawn per plan['sections'] entry of the layout, in order; the record's keys over each entry
    (arrangement.PIANO_FIXED), the drawn arrangement options (_arrange), a waltz's moving bars, the drawn left hand
    alone, the octave."""
    P, meter, sd = g.plan, tune.meter, tune.seed
    pins = _set_pins(tune, g)
    lays = (P.get('set') or {}).get('layout') or {}
    layout = pins.get('layout')
    if lays and layout not in lays:
        layout = _pick(random.Random(f"layout:{sd}"), lays)
    layout = dice.put(None, 'layout', layout)
    sig = _signature(tune, g, dice, pins)
    # (plan['form_bars']: the sections' bar counts are form bars - a waltz plays each as two 3/4 bars)
    stretch = 2 if meter == 3 and P.get('form_bars') else 1
    spec = section_specs(g, layout)
    # (a waltz: an optional section - the third A, the interlude - rarer: blind round g5, QJUG 129 bars "too long
    # for its material"; round g7, FUKP 99 bars: WALTZ_FORM)
    W = WALTZ_FORM if stretch > 1 else {}
    drawn = [x['name'] for x in spec.values() if not (x.get('feels') and tune.feel not in x['feels'])
             and rng.random() < x.get('chance', 1.0) * (W['chance'] if W and 'chance' in x and x['name'] != 'intro'
                                                       else 1)]
    if W and 'A1' in drawn and drawn.index('A1') + 1 < len(drawn) and drawn[drawn.index('A1') + 1] in W['after_a1']:
        drawn.remove(drawn[drawn.index('A1') + 1])     # (a waltz's A1 is a 16-bar period already: no A A)
    if ('motto' in sig or 'ostinato' in sig) and 'intro' in spec and 'intro' not in drawn:
        drawn.insert(0, 'intro')                       # (the motto / the ostinato is planted in the intro)
    dv = _diverse(tune, g)
    if _sung(P):
        if dv is None:
            drawn = _tail_cap(tune, spec, _a_cap(tune, spec, drawn), meter, stretch)
        else:                                          # (PIANO_DIVERSE: the peak's place drawn - an early peak
            drawn = _a_cap(tune, spec, drawn)          # keeps its tail)
            if dv['place'] != 'early':
                drawn = _tail_cap(tune, spec, drawn, meter, stretch)
            drawn = _place_peak(tune, spec, drawn, meter, stretch, dv, bool(W))
            pins = dict(pins, _pdiv_at=PIANO_DIVERSE['at'][dv['place']])
    wbars = {}
    if W:
        drawn, wbars = _waltz_cap(tune, spec, drawn, meter)
    plan = []
    order = dice.order(drawn)
    pk_i = next((i for i, n in enumerate(order) if n in spec and spec[n].get('peak')), None)
    final_a = next((n for n in reversed(order[pk_i + 1:]) if n in RETURNS), None) \
        if _sung(P) and pk_i is not None else None
    for name in order:
        if name not in spec:
            from ..theory import ComposeError
            raise ComposeError(f"arrangement: {g.name} has no section {name!r} (plan['sections'], layout {layout})")
        base = spec[name]
        if name in wbars:                              # (a waltz's return / build: a 6- or 7-bar form phrase)
            base = dict(base, bars=wbars[name])
        sec = dict(base)
        for k in PIANO_FIXED:
            if isinstance(base.get(k), dict):                # (lh_only: below; another {value: weight} - a section's
                if k != 'lh_only':                           # dynamics - drawn here with its own dice)
                    sec[k] = dice.put(name, k, _pick(random.Random(f"{k}:{sd}:{name}"), base[k]))
                continue
            v = dice.put(name, k, base.get(k))
            if v is not None:
                sec[k] = v
        if name == final_a:                            # (round g11: the theme's last statement closes home -
            sec = _final_a(sec, meter * stretch, meter)    # FINAL_A)
        if 'part' in sec:
            part = sec['part']
            ch = list(tune.changes[part])
            mel = (tune.out_melody.get(part) if sec.get('melody') == 'lift' else None) or tune.melody[part]
        else:
            fr = tune.intro if sec['frame'] == 'intro' else tune.tag
            ch, mel = list(fr['changes']), list(fr['melody'])
            if stretch > 1 and mel and max(st + du for st, du, _ in mel) <= sum(b for _, b in ch) / 2 + meter + 1e-6:
                mel = [(2 * st, 2 * du, p) for st, du, p in mel]   # (a waltz's frame line written for half its
                #                                                     bars: augmented - blind round g1, the right
                #                                                     hand silent 4 bars in the coda, an interlude
                #                                                     without a line)
            if sec.get('keep_bars'):
                mel = [n for n in mel if int(n[0] // (meter * stretch)) in sec['keep_bars']]
                if dv is not None and name == 'inter':     # (PIANO_DIVERSE: the interlude from the theme)
                    mel = _inter_theme(tune, ch, sec['keep_bars'], meter, meter * stretch, dv['interlude']) or mel
        if dv is not None:
            sec = _diverse_sec(sec, dv, order, pk_i, name)
        if _sung(P) and sec.get('vary') and sec['name'] in RETURNS and any(s_.get('peak') for s_, *_ in plan) \
                and not any(s_.get('_post') for s_, *_ in plan):
            sec = dict(sec, _post=True)                # (the theme's first return after the climax: POST_RETURN)
        elif _sung(P) and sec.get('vary') and sec['name'] in RETURNS and not any(s_.get('peak') for s_, *_ in plan):
            sec = dict(sec, _pre=True)                 # (round g8: a return before the climax - no bar copied)
        if any(k in sec for k in ARRANGE_KEYS):        # (drawn arrangement options: their own dice per section)
            sec, ch, mel = _arrange(tune, sec, ch, mel, meter, random.Random(f"arrange:{sd}:{sec['name']}"),
                                    bar=meter * stretch, dice=dice, pins=pins,
                                    prior=[m_ for s_, _, m_, _ in plan if s_['name'] in ('A1',) + RETURNS])
        if stretch > 1 and ch and ('part' in sec or P.get('moves')):     # (a waltz: its long chords move bar
            ch = _moving_bass(ch, meter, sorted(mel), tune.key,             # by bar; with plan['moves'] its frames
                              None if sec.get('_key') or 'part' not in sec else    # too - a section in another key /
                              (get(tune.genre).harmony.get('reharm') or {}).get(tune.key.split()[1]),   # a frame: no
                              #                                                     home substitutes)
                              random.Random(f"waltz-bars:{sd}:{sec['name']}"),
                              take=lambda v, _n=name: dice.put(_n, 'moves', v),
                              weights={k: w for k, w in (P.get('moves') or {}).items()
                                       if not sec.get('peak') or k not in CLIMAX_STILL} or P.get('moves'),
                              key_pcs=sec['_key'][2] if sec.get('_key') else None)
        if _sung(P) and sec.get('frame') == 'tag' and ch:     # (round g11: a coda of CODA['bars'] at least - the
            ch, mel = _coda_head(tune, ch, mel, meter, meter * stretch,    # theme's head before the tag)
                                 before=sum(x[3] for x in plan))
        if isinstance(base.get('lh_only'), dict):      # (the intro's left hand alone: drawn bars)
            sec = dict(sec, lh_only=dice.put(name, 'lh_only',
                                             _pick(random.Random(f"lh-only:{sd}:{sec['name']}"), base['lh_only'])))
        if sec.get('lh_only'):
            mel = [n for n in mel if n[0] >= sec['lh_only'] * meter * stretch - 1e-6]
        L = sum(b for _, b in ch)
        octave = base.get('octave')
        if isinstance(octave, dict):
            octave = _pick(random.Random(f"octave:{sd}:{sec['name']}"), octave)
        line = (P.get('ceiling') or {}).get('line')
        if octave and line and mel and max(p for *_, p in mel) + 12 * octave > line:
            octave = 0                                 # (an octave-up return only where it stays under the ceiling)
        octave = dice.put(name, 'octave', octave) or 0
        mel = [(st, min(du, L - st, P.get('max_hold', L)), p + 12 * octave) for st, du, p in mel if st < L - 1e-6]
        plan.append((sec, ch, mel, L))
    if any(k in sec for sec, *_ in plan for k in ARRANGE_KEYS):
        _pivot(tune, plan, meter)                      # a climax a step up: the bar before it pivots into its key
        _keys(tune, plan, meter, meter * stretch)      # a section in another key: in on its dominant, out on home's
        if _sung(P):                                   # (the climax over a held dominant: ARRIVALS)
            _arrive(tune, plan, meter, meter * stretch, pins.get('arrival'))
        _under_peak(plan, _key_pcs(tune) if P.get('peak_floor') else None,    # nothing outside the climax as
                    P.get('peak_floor') or 64, margin=PRE_TOP if _sung(P) else 0)    # high as its peak
    if sig:
        _sign(tune, g, plan, sig, meter, meter * stretch, arrival=pins.get('arrival'))
    return plan


def _piano_draws(tune: Tune, g: Genre, plan: list, rng: random.Random, dice: Dice) -> None:
    """The rest of a piano piece's recorded decisions, drawn as the player did: a hairpin's levels per 4-bar phrase
    of a part section (plan['swell'], its own dice), the cadenza flourishes wanted (the shared piano dice, right after
    the section draws), the tune's touch window (plan['touch_span'])."""
    P, meter, sd = g.plan, tune.meter, tune.seed
    for sec, _, _, L in plan:
        if P.get('swell') and 'part' in sec and not sec.get('peak'):
            sw = random.Random(f"swell:{sd}:{sec['name']}")
            dice.put(sec['name'], 'swell', [_pick(sw, P['swell']) for _ in range(0, int(round(L / meter)), 4)])
    for sec, *_ in plan:
        dice.put(sec['name'], 'cadenza', rng.random() < sec['cadenza'] if sec.get('cadenza') else None)
    if P.get('touch_span'):
        dice.put(None, 'touch', _pick(random.Random(f"touch:{sd}"), P['touch_span']))
    for k, w in sorted((P.get('play') or {}).items()):     # the pianist's own per-piece choices (PLAY_KEYS: each
        dice.put(None, k, _pick(random.Random(f"play:{sd}:{k}"), w))   # its own dice)


def arrange(tune: Tune, genre: Genre | None = None) -> Arrangement | None:
    """The players' arrangement of a tune, drawn from its seed (endless.arrangement; None for an organ tune; an
    orchestra tune's: the piano plan's draws + the orchestrator's, made by building it): what
    build(tune) plays - build(tune, arrangement=arrange(tune)) gives the same notes."""
    g = genre or get(tune.genre)
    kind = g.plan.get('perform', 'jazz')
    if kind == 'piano':
        dice, rng = Dice('piano'), random.Random(f"piano:{tune.seed}")
        _piano_draws(tune, g, _piano_plan(tune, g, rng, dice), rng, dice)
        return dice.out
    if kind == 'jazz':
        return _jazz_arrangement(tune, g, Dice('jazz'))
    if kind == 'orchestra':                            # (the orchestrator's draws ride on the piano's: the build
        from .orchestra import build_orchestra         # draws them - composing lines costs no audio)
        return build_orchestra(tune, g).endless_arrangement
    if kind == 'symphony':
        from .symphony import build_symphony
        return build_symphony(tune, g).endless_arrangement
    return None


ORNAMENT_LAND = 1.5
"""A turn (plan['ornaments']) never sits on the note before one held this many beats or more - a phrase's landing
(round g13, all seven judges: GALR 13-14 / 27-28, MYUS 7-8 - the turn late in the note before the cadence note, four
notes of 1/8 beat leaning into it, read as "a 32nd flick, then a 0.08-beat stab and an empty bar"); a mordent on the
beat stays."""


def _play_piano(tune: Tune, g: Genre, s: Song, plan: list, rng: random.Random, A: Arrangement) -> Song:
    """build_piano's performance of its plan (the sections' material) and arrangement A (the dice `rng` after the
    section and cadenza draws: the left hand's figures)."""
    from .. import romantic as rom
    from ..patterns import Note
    F, P = g.feels[tune.feel], g.plan
    meter, sd = tune.meter, tune.seed
    figs = F.get('figures') or {}
    pins = _set_pins(tune, g) if _sung(P) else {}
    end_bars = max(1, P.get('end', 1))
    dv = _diverse(tune, g)                            # (PIANO_DIVERSE: the climax hand, the ending gesture)
    ending = dv['ending'] if dv else None
    if ending in ('plagal', 'deceptive', 'line', 'arpeggio'):
        end_bars = max(end_bars, 2)                   # (a bar before the last chord: _end_pre)

    def play(k, default):                             # (a per-piece choice of plan['play'], the record's; else the
        v = A.get(None, k)                            # constant every other genre plays)
        return default if v is None else v
    bl = _bloom(tune, g, plan)                        # the bloom: its section breathes lightly into the next one
    if bl and dv and dv.get('bloom2', 'run') != 'run':  # (PIANO_DIVERSE: not every build ends in 16ths / triplets)
        if dv['bloom2'] == 'eighths':
            m_ = 3 if meter == 3 else 4
            bl = dict(bl, figures={**bl['figures'], m_: [bl['figures'][m_][0],
                                                         dict(PIANO_DIVERSE['bloom_eighths'][m_])]})
        else:
            bl = dict(bl, reach=max(bl['reach'], 0.75))
    TX = P.get('texture')
    if TX:                                            # the right hand's texture per section and its connecting
        plan = _texture(tune, plan, TX, meter)        # notes (HUMAN_FEEDBACK 2026-10-15: "one finger")
    if bl:                                            # (a blooming climax keeps its broad end)
        plan = [(dict(sec, rit=bl['rit']) if sec['name'] == bl['name'] and sec.get('rit') and not sec.get('peak')
                 else sec, ch, mel, L) for sec, ch, mel, L in plan]
    for sec, _, _, L in plan:
        s.section(sec['name'], bars=L / meter)
    s.section('end', bars=end_bars)
    secs = {x.name: x for x in s.sections}
    kspans = _key_spans(tune, plan, secs, meter, meter * (2 if meter == 3 and P.get('form_bars') else 1))
    # ---- the notes: the right hand (harmonized), the chord timeline, the dynamic marks, the phrases
    rh, timeline, marks, phrases, echo = [], [], [], [], []
    peak_at = None
    for sec, ch, mel, L in plan:
        a = secs[sec['name']].start
        t = a
        for sym, b_ in ch:
            timeline.append((t, b_, sym))
            t += b_
        notes = [Note(a + st, du, p, 80) for st, du, p in mel]
        if sec.get('harmonize'):
            def chord_at(x, _a=a, _ch=ch):
                tt = _a
                for sym_, b2 in _ch:
                    if tt - 1e-6 <= x < tt + b2 - 1e-6:
                        return sym_
                    tt += b2
                return None
            v = sec['harmonize']
            md = sec.get('_min_dur') or (0.9 if v >= 2 else 1.0)
            notes = list(rom.harmonize(Clip._raw(notes, a + L), chord_at, voices=v, min_dur=md,
                                       share=sec.get('harm_share', 1.0 if v == 2 else 0.5),
                                       floor='G4' if v >= 2 else 'F4',
                                       seed=sd % 997 + len(rh), move=sec.get('_move', 0.0),
                                       long_share=sec.get('_long'),
                                       scale_at=lambda x, _c=chord_at: _local_scale(kspans, x, _c(x)) if _c(x)
                                       else None,
                                       still=lambda x0, x1, _a=a: (x1 - _a) % ((8 if meter == 3 else 4) * meter)
                                       > (8 if meter == 3 else 4) * meter - meter - 1e-6 or x1 >= _a + L - 1.0))
            if (sec.get('peak') or sec['name'] in SECTION_NOTES) and _sung(P):
                notes = _thin(notes, {(round(a + st, 3), p) for st, du, p in mel}, a, L, meter,
                              cap=None if sec.get('peak') else SECTION_NOTES[sec['name']].get(meter))
        if sec.get('_anthem') == 'canon':              # (the head answered under the sung line: _canon)
            ec = _canon(mel, meter, a)
            notes += [Note(st, du, p, 72) for st, du, p in ec]
            echo += [(st, p) for st, du, p in ec]
        if sec.get('peak') and mel:
            top = max(mel, key=lambda n: (n[2], -n[0]))
            peak_at = a + top[0]
        rh += notes
        own = _marks(sec.get('dyn', 'mp'), a, a + L, peak_at if sec.get('peak') else None)
        marks += own
        k0 = int(round(a / meter)) + 1
        nb = int(round(L / meter))
        step = 4                                      # (4-bar phrases: a waltz's touch arcs too)
        amps = A.get(sec['name'], 'swell')                 # (the hairpins' levels: the record's)
        for f0 in range(0, nb, step):
            phrases.append((k0 + f0, k0 + min(nb, f0 + step) - 1))
            if P.get('swell') and 'part' in sec and not sec.get('peak') and amps:
                marks += _swell(own, mel, a, f0 * meter, min(L, (f0 + step) * meter), amps[f0 // step])
    # the signature moves' marks (a subito level at a section start replaces its marks there), the pedal's dry windows
    dry = []

    def mark(at, lv):
        marks[:] = [m for m in marks if abs(m[0] - at) > 1e-6] + [(at, lv)]
    for sec, ch, mel, L in plan:
        a = secs[sec['name']].start
        S_ = sec.get('_sig') or {}
        if S_.get('after'):
            mark(a, S_['after'])
        for r, lv in S_.get('marks', ()):
            mark(a + r, lv)
        dry += [(a + r0, a + r1) for r0, r1 in S_.get('dry', ())]
    marks[:] = _dyn_order(marks, [(secs[sec['name']].start, secs[sec['name']].end, sec) for sec, *_ in plan],
                          2 * meter * (2 if meter == 3 and P.get('form_bars') else 1))
    over = sorted([(secs[sec['name']].start + r0, secs[sec['name']].start + r1, f, cut)
                   for sec, *_ in plan for r0, r1, f, cut in (sec.get('_sig') or {}).get('lh', ())],
                  key=lambda v: (v[0], v[1]))
    # the final chord: the end chord rolled in the right hand over the left hand's rolled chord
    end = secs['end']
    ec = chord(tune.end_chord)
    tones = sorted({(ec.root + i) % 12 for i in ec.intervals})
    top_pc = (tune.motif[0][2] % 12) if tune.motif and tune.motif[0][2] % 12 in tones else ec.root % 12
    top = 72 + (top_pc - 72) % 12 + 12
    if P.get('end_top') == 'line' and rh:            # the final chord resolves the last melody note: its top the
        last = max(rh, key=lambda n: (n.start, n.pitch)).pitch      # chord tone at or just above that note
        top = min((q for q in range(max(last, 67), max(last, 67) + 12) if q % 12 in tones), default=top)
        top_pc = top % 12
    if ending == 'open':                              # (PIANO_DIVERSE: an open chord - the root or fifth on top,
        top = min((q for q in range(top, top + 8) if q % 12 in (ec.root % 12, (ec.root + 7) % 12)), default=top)
        top_pc = top % 12                             # no third under it)
    voicing = sorted({top} | {top - ((top - pc) % 12 or 12) for pc in tones if pc != top_pc})[-4:]
    ev = play('end_voice', 'full')                    # (the last grip per piece - blind round g2: one 4-note grip
    if ev == 'open':                                  # under the tune's last note in every piece: an open 6th /
        voicing = [p for p in voicing if top - p >= 5][-1:] + [top]       # 5th under it, or the note alone)
    elif ev == 'single':
        voicing = [top]
    if ending == 'open':
        voicing = sorted({top - 12, top} | {top - ((top - pc) % 12 or 12) for pc in (ec.root % 12, (ec.root + 7) % 12)
                                             if pc != top_pc})
    elif ending == 'line':
        voicing = [top]
    fin = end.start + (meter if end_bars > 1 and ending else 0.0)    # (the last chord's bar)
    pre = _end_pre(tune, ending, end.start, meter, top, rh) if ending and end_bars > 1 else None
    if pre:
        timeline.append((end.start, fin - end.start, pre['sym']))
        rh += pre['notes']
    timeline.append((fin, end.end - fin, tune.end_chord) if ending else (end.start, end.length, tune.end_chord))
    marks.append((end.start, play('end_dyn', 'pp')))
    phrases.append((int(round(end.start / meter)) + 1, int(round(end.end / meter))))
    total = end.end
    score = rom.score(Clip._raw(rh, total), None, None, meter=f"{meter}/4", key=tune.key, phrases=phrases)
    if pre and pre.get('voicing'):
        score.events.append(rom.Event('roll', end.start, fin - end.start - 0.25, pre['voicing'], 0.8,
                                      args=(play('end_roll', 110),)))
    score.events.append(rom.Event('roll', fin, (end.end - fin if ending else end.length) - 0.25, voicing, 0.85,
                                  args=(play('end_roll', 110),)))
    # ornaments (plan['ornaments'] {kind: chance per part section}; new-age blind round N0: no turn anywhere, the
    # references one per theme statement): a turn / mordent on a held note that steps on to the next one
    peak_p = max((n.pitch for n in rh), default=128)
    for sec, *_ in plan:
        if 'part' not in sec or not P.get('ornaments'):
            continue
        x = secs[sec['name']]
        # (round g9: a turn on the theme head's held top note cut it - composer.HEAD_PROFILE: an A statement's head
        # as written)
        h0 = x.start + (2 * meter if sec['part'][0] == 'A' else 0)
        evs = [e for e in score.events if x.start - 1e-6 <= e.at < x.end - 1e-6]
        ro = random.Random(f"ornament:{sd}:{sec['name']}")
        for kind, chance in P['ornaments'].items():
            if ro.random() >= chance:
                continue
            # (round g13, all seven judges: GALR 13-14 / 27-28, MYUS 7-8 - a turn late in the note before a phrase's
            # landing read as "a 32nd flick, then a 0.08-beat stab": a turn leads on inside the line, never into a
            # landing - ORNAMENT_LAND)
            ok = [e for e, nx in zip(evs, evs[1:]) if e.kind == 'note' and 0.9 <= e.dur <= 2.5 and e.at >= h0 - 1e-6
                  and nx.kind in ('note', 'chord') and 0 < abs(nx.pitches[-1] - e.pitch) <= 2
                  and (kind != 'turn' or nx.dur < ORNAMENT_LAND - 1e-6)
                  and e.pitch + 2 < peak_p and _orn_steps(e, kind, kspans, timeline, tune.key) is not None]
            if ok:                                     # (its upper neighbour never strikes the climax note again; its
                e = ro.choice(ok)                      # neighbours in the local chord scale - _orn_steps)
                e.kw.update(_orn_steps(e, kind, kspans, timeline, tune.key))
                e.kind = kind
    # a cadenza flourish over the last dominant of a section that asks for one: a run down from above the
    # section's top into the next section's first melody note (one free gesture; the right hand's notes there go)
    cadenzas = set()
    for i, (sec, ch, mel, L) in enumerate(plan):
        if not A.get(sec['name'], 'cadenza') or i + 1 >= len(plan) or not plan[i + 1][2]:   # (drawn: _piano_draws)
            continue
        if sec.get('peak') and _sung(P):               # (round g11, two judges: VBJZ's G6-Db5 16th run out of the
            continue                                   # climax "a stock flourish" - the sung climax holds its note)
        z = secs[sec['name']].end
        a0 = z - min(2.0, meter)
        nxt = plan[i + 1][2][0][2]
        hi_ = min(max(n[2] for n in mel) + 3, peak_p - 1)   # (under the piece's peak: the sung climax's top is
        #                                                       the ceiling - no C7 flourish, no second peak)
        dom = chord(ch[-1][0])                     # the local key's scale, the dominant's own tones (its leading
        pcs = ({q % 12 for q in _local_key(kspans, a0)} -                                   # tone)
               ({(dom.root + 3) % 12} if not dom.is_minor else set())) | {(dom.root + i) % 12 for i in dom.intervals}
        run = [p for p in range(hi_, nxt, -1) if p % 12 in pcs][:14]
        if len(run) >= 6:
            score.events = [e for e in score.events if not a0 - 1e-6 <= e.at < z - 1e-6]
            score.events.append(rom.Event('fig', a0, z - a0, run, 0.9, args=('arch',)))
            cadenzas.add(sec['name'])
    score.events.sort(key=lambda e: e.at)
    # the hand-to-hand figures (the left hand climbs, the right carries it on over a held note) and the bloom
    hands, woven = _handoffs(score, plan, secs, timeline, rh, meter, bl, kspans, P.get('lh') or {},
                             random.Random(f"handoff:{sd}")) if bl else ({}, [])
    from ..theory import note as _note
    lh_cap = _note((P.get('lh') or {}).get('cap', 67))
    brng, blast = random.Random(f"bloom-lh:{sd}"), None
    # ---- the left hand: a figure per bar from the section's set; held still where the melody breathes
    lh, last, used = [], None, {}
    sec_of = [(secs[sec['name']].start, secs[sec['name']].end, sec) for sec, *_ in plan]
    peak_start = next((a for a, z, sec in sec_of if sec.get('peak')), None)
    for t0, b_, sym in timeline:
        t = t0
        while t < t0 + b_ - 1e-6:
            pos = t % meter
            pos = 0.0 if pos < 1e-6 or meter - pos < 1e-6 else pos
            span = min(meter - pos, t0 + b_ - t)
            sec = next((x for a, z, x in sec_of if a - 1e-6 <= t < z - 1e-6), None)
            fset = figs.get(sec.get('figures', 'flow'), 'flow') if sec else None
            if sec is not None and sec.get('peak') and isinstance(fset, dict) and pins.get('big') in fset:
                fset = {k: w * (BIG_PIN if k == pins['big'] else 1.0) for k, w in fset.items()}   # (round g11)
            if dv and sec is not None and sec.get('peak') and sec.get('figures') == 'big':
                fset = _climax_hand(dv, meter)         # (PIANO_DIVERSE: the piece's own climax hand)
            lh_only = sec is not None and sec.get('lh_only') and \
                t < secs[sec['name']].start + sec['lh_only'] * meter - 1e-6
            own = None
            blooms = bool(bl) and sec is not None and sec['name'] == bl['name'] and not lh_only
            ov = next((v for v in over if v[0] - 1e-6 <= t < v[1] - 1e-6), None)
            if ov is not None:                         # (a signature move's left hand: silent, a bass, a roll)
                if ov[2] is not None:
                    lh.append((t, min(span, ov[3]) if ov[3] else span, sym, ov[2]))
                    used.setdefault(sec['name'] if sec else 'end', []).append(ov[2])
                t += span
                continue
            if round(t, 4) in hands:
                fig, own = hands[round(t, 4)]
            elif blooms and not (t + span > secs[sec['name']].end - 1e-6 and _breathes(rh, t, span)):
                # the bloom: triplets / 8ths, then 16ths (from bl['reach'] of the section) over two and a half
                # octaves, one figure per 2-bar unit, turning a whole step under the melody - under the woven right
                # hand at its usual cap
                x_ = secs[sec['name']]
                unit2 = int((t - x_.start + 1e-6) // (2 * meter))
                if blast is None or blast[0] != (sec['name'], unit2):
                    stage = bl['figures'][meter][1 if t - x_.start >= bl['reach'] * x_.length - 1e-6 else 0]
                    blast = ((sec['name'], unit2), _draw(brng, stage, blast[1] if blast else None))
                fig = blast[1]
                wov = [lo_ for a_, z_, lo_ in woven if a_ < t + span - 1e-6 and z_ > t + 1e-6]
                own = {'cap': min([lh_cap] + [lo_ - 1 for lo_ in wov]) if wov else
                       _lh_reach(rh, t, t + span, lh_cap, bl['lift']), 'mirror': True}
            elif sec is None and ending:
                fig, own = _end_hand(ending, t >= fin - 1e-6, meter, voicing, pre)
                if fig is None:                        # (the single line's bar: the left hand silent)
                    t += span
                    continue
            elif sec is None:
                fig = _fixed_or_drawn(rng, figs.get('end', 'roll'))
            elif peak_start is not None and peak_start - meter - 1e-6 <= t < peak_start - 1e-6:
                fig = _fixed_or_drawn(rng, figs.get('into', 'up'))
            elif not lh_only and _breathes(rh, t, span):
                fig = _fixed_or_drawn(rng, figs.get('rest', 'half'))
            elif bl and sec.get('peak') and last and int((t - secs[sec['name']].start + 1e-6) // meter) % 2 and \
                    lh and lh[-1][3] == last and lh[-1][0] >= t - meter - 1e-6:
                fig = last          # (a blooming genre's climax: one figure per 2-bar unit - the blind judge, 2026-10-15:
                #                      16ths / 8ths toggling strictly bar by bar read as a machine)
            else:
                fig = _draw(rng, fset, last)
                last = fig
                if sec is not None and (sec.get('_sig') or {}).get('ost'):
                    fig = sec['_sig']['ost']           # (the signature ostinato)
            lh.append((t, span, sym, fig) + ((own,) if own else ()))
            used.setdefault(sec['name'] if sec else 'end', []).append(fig)
            t += span
    # ---- the tempo: phrase rubato, the sections' tempo / ritardandi / fermatas, an inhale before the peak (a
    # 'steady' feel keeps strict time - a drum loop plays along: no phrase rubato, no inhale, no lilt)
    steady = bool(F.get('steady'))
    if F.get('rubato', 0.05) > 0 and not steady:
        score.rubato(s, depth=F.get('rubato', 0.05) * play('rubato', 1.0), seed='bar')
    before = {}
    names = [sec['name'] for sec, *_ in plan]
    for sec, *_ in plan:
        x = secs[sec['name']]
        bpm = tune.tempo * sec.get('tempo', 1.0)
        if bl and sec.get('peak') and bl['name'] in names[:names.index(sec['name'])]:
            bpm *= 1.0 + (bl['push'] - 1.0) * bl['carry']      # the climax keeps part of the bloom's push
        s.set_tempo(x.start, bpm)
        if bl and sec['name'] == bl['name'] and not steady:
            # the bloom pushes forward: an accelerando to bl['push'] over bl['reach'] of the section (up to the
            # peak note in a blooming climax), held there - its end breathes lightly (bl['rit']), the peak broadens
            z = x.end - meter + 1.0 if sec.get('rit') and x.length > meter else x.end
            if sec.get('peak') and peak_at is not None and x.start < peak_at < x.end:
                z = min(z, peak_at - 1.0)
            r = x.start + (z - x.start) * bl['reach']
            if r - x.start >= 1.0:
                s.accelerando((x.start, r), to=bl['push'], curve='smooth')
        inhale = play('inhale', 2.0)
        if sec.get('peak') and inhale and x.start - inhale > 0 and not before.get('rit') and not steady:   # (the
            s.ritardando((x.start - inhale, x.start), to=0.85)    # inhale: unless the section before slows already)
        before = sec
        if sec.get('rit') and x.length > meter:
            s.ritardando((x.end - meter + 1.0, x.end), to=sec['rit'],
                         a_tempo=not sec.get('fermata') and sec is not plan[-1][0])
        if sec.get('fermata'):
            s.fermata(x.end - (0.5 if sec['name'] in cadenzas else min(1.5, meter - 1.0)), hold=sec['fermata'])
        c_ = (sec.get('_sig') or {}).get('cascade')
        if c_ and not steady and not (sec.get('rit') and c_['end'] > x.length - meter - 1e-6):
            s.ritardando((x.start + (c_['at'] + c_['end']) / 2, x.start + c_['end']), to=0.85)   # (the cascade
            #                                                                                     lands broadening)
    if not plan[-1][0].get('rit'):
        s.ritardando((end.start - meter, end.start), to=0.8, a_tempo=False)
    if fin > end.start + 1e-6:                        # (PIANO_DIVERSE: the bar before the last chord broadens)
        s.ritardando((end.start + 0.5, fin), to=0.72 if ending == 'arpeggio' else 0.88, a_tempo=False)
    s.fermata(fin, hold=play('end_hold', 3))
    if not steady:
        lilt = play('lilt', None)
        beats_ = {3: lilt or 0.03} if meter == 4 else {2: (lilt + 0.01) if lilt else 0.04}
        score.lilt(s, (0.0, end.start), beats=beats_, jitter=0.03, seed=sd % 997)
    # ---- the band and the pianist (the tune's swing, if it swings: lofi's lazy 8ths)
    feel = jazz.Feel(tune.tempo, ratio=tune.swing or 0.5, beats_per_bar=meter)
    b = band(s, g, tune.feel, feel, mood=tune.mood)
    _piano_drums(s, b, tune, g, plan, secs)
    # the pianist's body (humanize body=, the feel's profile): one gesture per phrase over both hands - the right hand
    # leads, the left follows. Set before Score.perform, which marks its phrases on the track and leaves the leaps /
    # motor noise to the body; the tempo lanes here (rubato, ritardandi, fermatas, lilt) own the time, so the body
    # adds the leaps, the breaths, the weight in the bar and dynamics that follow the lanes' tempo
    if F.get('body'):
        b.piano.humanize(body=F['body'])
        b.comp.humanize(body=F['body'], lead=b.piano.id if F['body'] != 'none' else None)
    lo, hi = F.get('touch', (52, 100))
    if A.get(None, 'touch'):                         # the tune's own dynamic budget (round r2: one ~17 LU range,
        dlo, dhi = A.get(None, 'touch')              # velocity p10/p90 41/93 in every piece; drawn: _piano_draws)
        lo, hi = lo + dlo, hi + dhi
    score.dyn = [(beat, lv) for beat, lv in sorted(marks)]
    # the tempo plan is final here: the pianist reads one tempo map (song.tempo_at rebuilds it per call - thousands
    # of calls over a 4-minute piece with rubato + lilt)
    tm = s.tempo_map()
    s.tempo_at = lambda beat: tm.bpm_at(s._at(beat))
    try:
        po = P.get('pedal')
        if A.get(None, 'pedal') is not None:
            po = dict(po or {}, delay_ms=A.get(None, 'pedal'))
        if dry:
            po = dict(po or {}, dry=dry)
        ro = None if not P.get('play') else dict(seed=sd % 9973, **({'lean_ms': A.get(None, 'push')}
                                                                     if A.get(None, 'push') is not None else {}))
        bal = _balance(tune, plan, secs, phrases, rh, meter, bl['name'] if bl else None, play)
        score.perform(s, b.piano, b.comp, pedal=True, touch=dict(lo=lo, hi=hi), breath=play('breath', 0.35),
                      cap=play('cap', P.get('cap', 106)), figures=lh, inner=play('inner', 0.78),
                      accent_cap=play('cap', P.get('cap', 106)) + P.get('accent_over', 12),
                      figure_vel=play('lh_vel', 41), figure_opts=P.get('lh'), pedal_opts=po, rubato=ro,
                      balance=bal, line=P.get('line'))
    finally:
        del s.tempo_at
    if echo:                                           # (the canon's inner voice under the line: CANON['touch'])
        ek = {}
        for st, p in echo:
            ek.setdefault(p, []).append(st)
        b.piano._notes = [n._replace(vel=max(1, int(round(n.vel * CANON['touch']))))
                          if any(abs(n.start - x) < 0.15 for x in ek.get(n.pitch, ())) else n for n in b.piano._notes]
    stm = []
    for sec, ch, mel, L in plan:                       # the signature moves: the cascade's notes, the statements
        a = secs[sec['name']].start
        S_ = sec.get('_sig') or {}
        c_ = S_.get('cascade')
        if c_:
            bass_lo = (P.get('lh') or {}).get('bass_lo')
            r_, l_ = _cascade_notes(c_, a + c_['at'], meter, _note(bass_lo) if bass_lo else 31)
            for tr, ns in ((b.piano, r_), (b.comp, l_)):
                if ns:
                    tr.play(Clip._raw(ns, max(n.start + n.dur for n in ns)), 0)
        for r0, r1, role, ns in S_.get('motto', ()):
            stm.append({'move': 'motto', 'role': role, 'at': a + r0, 'end': a + r1,
                        'notes': [(a + st, du, p) for st, du, p in ns]})
        if S_.get('ost'):
            stm.append({'move': 'ostinato', 'role': sec['name'], 'at': a, 'end': a + L, 'figure': S_['ost']})
        for mv in ('pause', 'goose', 'cascade'):
            if S_.get(mv):
                x_ = S_[mv]
                stm.append({'move': mv, 'role': x_.get('target', sec['name']), 'at': a + x_['at'],
                            'end': a + x_.get('end', L), **{k: v for k, v in x_.items() if k not in ('at', 'end')}})
    _loud_order([b.piano, b.comp], [(secs[sec['name']].start, secs[sec['name']].end, sec) for sec, *_ in plan],
                meter, shape=_sung(P))
    for d in stm:
        d['bars'] = (int(d['at'] // meter + 1e-6) + 1, int((d['end'] - 1e-6) // meter) + 1)
    s.endless_signature = {'moves': plan[0][0].get('_moves') or {}, 'statements': stm}
    if 'vinyl' in b:                                  # the vinyl bed under the whole piece (lofi_piano)
        from ..bandlib.jazz import lofi_crackle
        lofi_crackle(b, 0.0, end.end - 0.5, tail=4.0, seed=sd)
    s.endless_tune = tune
    s.endless_lh = {k: max(v, key=v.count) for k, v in used.items()}
    s.endless_diverse = dict(dv, inter='inter' in names, anthem_played=next(
        (x[0]['_anthem'] for x in plan if x[0].get('_anthem')), None)) if dv else None
    s.endless_figures = used
    s.endless_bloom = None if not bl else {'section': bl['name'], 'push': bl['push'], 'handoffs': len(hands),
                                           'woven': len(woven)}
    s.endless_sections = [(sec['name'], secs[sec['name']].start, secs[sec['name']].end) for sec, *_ in plan]
    s.endless_timeline = [(t, b_, sym) for t, b_, sym in timeline]     # (beat, beats, chord): the chart as played
    s.endless_keys = [(a, z, sorted(p)) for a, z, p in kspans]           # the local key's pcs over time
    s.endless_memory, s.endless_played = None, {}
    s.endless_arrangement = A        # (what was played: the record - the layout, every section's drawn options)
    s.endless_balance = bal
    return s


LOUD_ORDER = {'margin': 1.0, 'floor': 0.8, 'peak_under': 6, 'knee': 14, 'swell_from': 0.84, 'mean_under': 8,
              'intro_under': 6, 'intro_top': 72, 'tail_under': 2.0, 'around': 0.95, 'accent': 6, 'taper_to': 0.85, 'build_over': 1.0, 'lh_under': 6,
              'reentry': 8, 'enter': 0.5, 'pre_under': 12, 'build_mel': 0.0, 'pre_floor': 0.85,
              'after_in': 4, 'ramp': {'in': 3, 'jump': 12, 'under': 4, 'over': 6}}
"""The climax the loudest section (_loud_order; blind round g4: a build / B1 louder than the climax - FBKR's build
+2.5 LU over its climax's +1.2): every other part section's note energy per beat at least 'margin' dB under the
climax's, its velocities scaled down for it, by 'floor' (x0.8, -2.4 dB of energy) at most. Blind round g5: single
phrases still struck as hard as the climax (QTZG B1 v108, AZTL B1 v115 at bar 24, its coda v105) - every other
section's loudest note per hand at least 'peak_under' velocity steps under that hand's loudest in the climax: the
notes over 'knee' steps under that cap pressed into it (the phrase's shape kept, its quieter notes untouched).
Round g7 (blind round g6: XUMB's climax flat at v98 - the player's cap levels its mf -> ff; FUKP's waltz B1 at
climax level, mean v86; TLTG's intro at v88): the climax swells into its peak - its notes before the peak note's bar
scaled from 'swell_from' at its start up to 1; every other part section's mean melody velocity at least 'mean_under'
under the climax's (scaled, by 'floor' at most); the intro's loudest note per hand at least 'intro_under' under A1's
(and at most 'intro_top'; a soft knee as above). Round g8 (blind round g7: KTBL's A after the climax louder than its
B1 - "a long louder tail"): every part section after the climax at least 'tail_under' dB (note energy per beat) under
the loudest part section before it, the climax out (scaled, by 'floor' at most). Round g10 (the g9 judges):
- one peak, shaped (NMPC's peak hammered at v108-114 four bars, the player's cap levelling the bars round it): from
  the bar before the peak's bar the climax's notes 'around' x, the peak note struck 'accent' steps over them, the
  notes after it tapering to 'taper_to' x by the climax's end;
- the build builds (JRCY's B1 +2.3 LU over its build's +1.0): every part section before the build at least
  'build_over' dB under it (scaled, by 'floor' at most);
- the melody over its accompaniment (JRCY's B1 left hand at v92-99, its climax bass octaves v102-106, all five
  judges): in the chorus, the build and the climax no left-hand note within 'lh_under' steps of the right hand's
  loudest in its bar (a soft knee);
- after the climax no loud re-entry (KNUB's A2 / coda at v94-106 after a soft B2, four judges): a section's notes over
  the right hand's loudest in the section before's last 2 bars + 'reentry' pressed into it (a soft knee);
- the climax enters over the build (AHVN after its pause, four judges): its first 2 bars at least 'enter' dB over
  the last 2 sounding bars before it (its opening raised, fading out over 4 bars).
Round g11 (the g10 judges: CDSQ's A2 at v105 under a climax at ~v115, XWPQ's build "does not build", its melody
6.5 velocity steps under A2's):
- the energy saved for the climax: before the build (no build: the climax) the right hand's loudest note at least
  'pre_under' steps under the climax's (a soft knee);
- the build's melody (its mean velocity) at least 'build_mel' over every part section's before it - those scaled
  down to it, by 'pre_floor' at most;
- after the climax a section (the coda's head too: CODA) enters at most 'after_in' over the mean velocity of the
  section before's last 2 bars (scaled, by 'floor' at most; g10: post_jump up to 26).
Round g12 (the g11 judges: PTCV's climax entering at v54-64 after a v68 build, LESU's sinking to v47 after its first
bar, KTGG's v93 -> v120 in two bars): the climax's bars up to its peak's bar follow a crescendo - a ramp from 'in'
to 'jump' over the right hand's mean in the last 2 sounding bars before it (the first bar's own level in that range;
after a silent pause bar no upper limit; never over the peak bar's) to the peak bar's mean;
a bar whose melody (each onset's top note, runs out) is more than 'under' under the ramp is raised to it, one more than 'over'
over it pressed to it (both hands by one factor a bar: their balance kept; _ramp)."""


def _loud_order(tracks: list, spans: list, bar: float = 4.0, shape: bool = False) -> None:
    """A section louder than the climax (the summed note energy per beat of both hands, romantic.ENERGY_EXP 2.5 -
    the bloom's 16ths, a blooming build) played softer: its notes' velocities x the factor that puts it LOUD_ORDER
    ['margin'] dB under the climax (never under 'floor') - touch, not a fader. spans: [(start, end, section)] of
    the plan (the climax: 'peak'; the frames left as they are). shape (a genre with the sung climax, _sung): the
    climax's swell, the other sections' mean and the soft intro too (round g7). In place on the tracks' notes."""
    pk = [(a, z) for a, z, sec in spans if sec.get('peak')]
    if not pk:
        return

    def energy(a, z):
        e = sum((n.vel / 127.0) ** 2.5 for t in tracks for n in t._notes if a - 1e-6 <= n.start < z - 1e-6)
        return 10 * math.log10(e / max(1e-9, z - a)) if e > 0 else None
    a0, z0 = pk[0]
    top = max((n for n in tracks[0]._notes if a0 - 1e-6 <= n.start < z0 - 1e-6), key=lambda n: (n.pitch, -n.start),
              default=None)
    if top is not None and shape:                      # the climax's own swell into its peak bar
        p0 = a0 + bar * int((top.start + 0.12 - a0) // bar) - bar      # (the bar before the peak's bar)
        if p0 > a0 + 1e-6:
            for t in tracks:
                t._notes = [n._replace(vel=max(1, int(round(n.vel * (LOUD_ORDER['swell_from'] + (1 - LOUD_ORDER[
                    'swell_from']) * (n.start - a0) / (p0 - a0)))))) if a0 - 1e-6 <= n.start < p0 - 1e-6 else n
                            for n in t._notes]
        # (round g10: one peak, shaped - the player's cap flattened two or three bars round it to one velocity,
        # NMPC v108-114 four bars: the notes round the peak note 'around' x, the peak struck 'accent' over them, the
        # rest of the climax tapering to 'taper_to' x)
        pk_t, L_ = top.start, LOUD_ORDER

        def arch(n):
            if abs(n.start - pk_t) < 0.06:
                return n._replace(vel=min(127, n.vel + L_['accent']))
            if n.start < pk_t:
                return n._replace(vel=max(1, int(round(n.vel * L_['around']))))
            f = L_['around'] - (L_['around'] - L_['taper_to']) * (n.start - pk_t) / max(1e-9, z0 - pk_t)
            return n._replace(vel=max(1, int(round(n.vel * f))))
        for t in tracks:
            t._notes = [arch(n) if max(a0, p0) - 1e-6 <= n.start < z0 - 1e-6 else n for n in t._notes]

    def mean_vel(a, z):
        vs = [n.vel for n in tracks[0]._notes if a - 1e-6 <= n.start < z - 1e-6]
        return sum(vs) / len(vs) if vs else None
    mc = mean_vel(a0, z0) if shape else None
    for a, z, sec in spans:                            # (every other part section's melody under the climax's)
        mv = mean_vel(a, z) if 'part' in sec and not sec.get('peak') else None
        if mc is None or mv is None or mv <= mc - LOUD_ORDER['mean_under']:
            continue
        f = max(LOUD_ORDER['floor'], (mc - LOUD_ORDER['mean_under']) / mv)
        for t in tracks:
            t._notes = [n._replace(vel=max(1, int(round(n.vel * f)))) if a - 1e-6 <= n.start < z - 1e-6 else n
                        for n in t._notes]
    ec = energy(*pk[0])
    if ec is None:
        return
    pre = [energy(a, z) for a, z, sec in spans if 'part' in sec and not sec.get('peak') and z <= a0 + 1e-6] \
        if shape else []
    pre = [e for e in pre if e is not None]
    for a, z, sec in spans:                            # (round g8: the sections after the climax under the ones
        e = energy(a, z) if pre and 'part' in sec and a >= z0 - 1e-6 else None      # before it - no louder tail)
        cap = max(pre) - LOUD_ORDER['tail_under'] if pre else None
        if e is None or e <= cap:
            continue
        f = max(LOUD_ORDER['floor'], 10 ** (-(e - cap) / 25.0))
        for t in tracks:
            t._notes = [n._replace(vel=max(1, int(round(n.vel * f)))) if a - 1e-6 <= n.start < z - 1e-6 else n
                        for n in t._notes]
    for a, z, sec in spans:
        e = energy(a, z) if 'part' in sec and not sec.get('peak') else None
        if e is None or e <= ec - LOUD_ORDER['margin']:
            continue
        f = max(LOUD_ORDER['floor'], 10 ** (-(e - ec + LOUD_ORDER['margin']) / 25.0))
        for t in tracks:
            t._notes = [n._replace(vel=max(1, int(round(n.vel * f)))) if a - 1e-6 <= n.start < z - 1e-6 else n
                        for n in t._notes]
    bld = next(((a, z) for a, z, sec in spans if sec['name'] == 'build' and z <= a0 + 1e-6), None) if shape else None
    eb = energy(*bld) if bld else None
    for a, z, sec in spans:                            # (round g10: the build over every part section before it)
        e = energy(a, z) if eb is not None and 'part' in sec and z <= bld[0] + 1e-6 else None
        if e is None or e <= eb - LOUD_ORDER['build_over']:
            continue
        f = max(LOUD_ORDER['floor'], 10 ** (-(e - eb + LOUD_ORDER['build_over']) / 25.0))
        for t in tracks:
            t._notes = [n._replace(vel=max(1, int(round(n.vel * f)))) if a - 1e-6 <= n.start < z - 1e-6 else n
                        for n in t._notes]
    # (blind round g5: one phrase as loud as the climax's peak) every hand's loudest note outside the climax under
    # the climax's loudest by 'peak_under' - the notes near it pressed under it (a soft knee)
    a1 = next(((a, z) for a, z, sec in spans if sec['name'] == 'A1'), None) if shape else None
    for t in tracks:
        if a1 is None:
            break
        for a, z, sec in spans:                        # (round g7: a soft intro - under A1's loudest)
            if sec['name'] != 'intro':
                continue
            ref = max((n.vel for n in t._notes if a1[0] - 1e-6 <= n.start < a1[1] - 1e-6), default=None)
            hi = max((n.vel for n in t._notes if a - 1e-6 <= n.start < z - 1e-6), default=0)
            if ref is None or hi <= min(ref - LOUD_ORDER['intro_under'], LOUD_ORDER['intro_top']):
                continue
            cap = min(ref - LOUD_ORDER['intro_under'], LOUD_ORDER['intro_top'])
            knee = cap - LOUD_ORDER['knee']
            k = (cap - knee) / max(1, hi - knee)
            t._notes = [n._replace(vel=max(1, int(round(knee + (n.vel - knee) * k))))
                        if a - 1e-6 <= n.start < z - 1e-6 and n.vel > knee else n for n in t._notes]
    for t in tracks:
        top = max((n.vel for n in t._notes if a0 - 1e-6 <= n.start < z0 - 1e-6), default=None)
        if top is None:
            continue
        cap = top - LOUD_ORDER['peak_under']
        knee = cap - LOUD_ORDER['knee']
        for a, z, sec in spans:
            if sec.get('peak'):
                continue
            hi = max((n.vel for n in t._notes if a - 1e-6 <= n.start < z - 1e-6), default=0)
            if hi <= cap:
                continue
            k = (cap - knee) / max(1, hi - knee)
            t._notes = [n._replace(vel=int(round(knee + (n.vel - knee) * k)))
                        if a - 1e-6 <= n.start < z - 1e-6 and n.vel > knee else n for n in t._notes]
    if shape:
        _loud_g10(tracks, spans, bar, pk[0], energy)


BIG_PIN = 4.0
"""The climax's left hand per piece (round g11, the g10 statistician: six of eight climaxes on one figure - the octave
bass, a chord, its 10th, a chord): the set slot's plan['set']['big'] figure weighs this many times its own weight in
the climax's figure set (where the set has it: a waltz keeps its own)."""

CLIMAX_NOTES = {4: 8, 3: 6}
"""The sung climax's right-hand notes a bar at most (_thin; round g10, the g9 statistician / performer / composerB:
QKNJ 11.6 a bar, KNUB / JRCY 10+, "+2 under almost every attack" - texture, not hammering)."""


SECTION_NOTES = {'B1': {4: 7, 3: 5}, 'B2': {4: 7, 3: 5}, 'build': {4: 8, 3: 6}}
"""The harmonized right hand's notes a bar at most outside the climax (_thin; round g11, the g10 statistician /
performer / composerB: VEAS's B1 at 11.9 notes a bar - "texture, not a second tune" - ZVNR's build 9.7, HJJR's 9.4):
the chorus a melody and one voice under it, the build a little fuller; the climax keeps CLIMAX_NOTES."""


def _thin(notes: list, melody: set, a: float, L: float, meter: int, cap: int | None = None) -> list:
    """The harmonized climax thinned to CLIMAX_NOTES a bar (cap: another limit - SECTION_NOTES): the notes under its
    shortest melody notes (the latest first) let go until the bar fits; melody notes {(start, pitch)} stay."""
    cap = cap or CLIMAX_NOTES.get(meter, 8)
    out = list(notes)
    for k in range(int(round(L / meter))):
        b0, b1 = a + k * meter - 1e-6, a + (k + 1) * meter - 1e-6
        inbar = [n for n in out if b0 <= n.start < b1]
        if len(inbar) <= cap:
            continue
        mel = sorted((n for n in inbar if (round(n.start, 3), n.pitch) in melody), key=lambda n: (n.dur, -n.start))
        drop, left = set(), len(inbar)
        for m_ in mel:
            if left <= cap:
                break
            under = [n for n in inbar if abs(n.start - m_.start) < 1e-6 and n.pitch < m_.pitch
                     and (round(n.start, 3), n.pitch) not in melody]
            drop |= {id(n) for n in under}
            left -= len(under)
        out = [n for n in out if id(n) not in drop]
    return out


def _press(notes: list, a: float, z: float, cap: float, knee: float) -> list:
    """The notes in [a, z) over `knee` pressed so the loudest reaches `cap` at most (a soft knee: the shape kept)."""
    hi = max((n.vel for n in notes if a - 1e-6 <= n.start < z - 1e-6), default=0)
    if hi <= cap:
        return notes
    knee = min(knee, cap - 1)
    k = (cap - knee) / max(1, hi - knee)
    return [n._replace(vel=max(1, int(round(knee + (n.vel - knee) * k)))) if a - 1e-6 <= n.start < z - 1e-6
            and n.vel > knee else n for n in notes]


def _loud_g10(tracks: list, spans: list, bar: float, pk: tuple, energy) -> None:
    """LOUD_ORDER's round-g10 rules (a sung genre: _loud_order shape=True): the left hand under the melody in the
    chorus / the build / the climax, no loud re-entry after the climax, the climax entering over the build."""
    rh, lh = tracks[0], tracks[1]
    L = LOUD_ORDER
    a0, z0 = pk
    bld = next(((a, z) for a, z, sec in spans if sec['name'] == 'build' and z <= a0 + 1e-6), None)
    pre_end = bld[0] if bld else a0
    top = max((n.vel for n in rh._notes if a0 - 1e-6 <= n.start < z0 - 1e-6), default=None)
    if top is not None:                                # (round g11: no section before the build peaking like it)
        rh._notes = _press(rh._notes, 0.0, pre_end, top - L['pre_under'], top - L['pre_under'] - L['knee'])

    def mean_v(a, z):
        vs = [n.vel for n in rh._notes if a - 1e-6 <= n.start < z - 1e-6]
        return sum(vs) / len(vs) if vs else None
    mb = mean_v(*bld) if bld else None
    for a, z, sec in spans:                            # (round g11: the build's melody over every section before it)
        mv = mean_v(a, z) if mb is not None and 'part' in sec and z <= bld[0] + 1e-6 else None
        if mv is None or mv <= mb - L['build_mel']:
            continue
        f = max(L['pre_floor'], (mb - L['build_mel']) / mv)
        for t in tracks:
            t._notes = [n._replace(vel=max(1, int(round(n.vel * f)))) if a - 1e-6 <= n.start < z - 1e-6 else n
                        for n in t._notes]
    for a, z, sec in spans:                            # the left hand under the melody, bar by bar
        if 'part' not in sec or sec['name'].startswith('A'):
            continue
        t = a
        while t < z - 1e-6:
            top = max((n.vel for n in rh._notes if t - 1e-6 <= n.start < t + bar - 1e-6), default=None)
            if top is not None:
                lh._notes = _press(lh._notes, t, t + bar, top - L['lh_under'], top - L['lh_under'] - L['knee'])
            t += bar

    def last_top(a, z):
        return max((n.vel for n in rh._notes if max(a, z - 2 * bar) - 1e-6 <= n.start < z - 1e-6), default=None)
    prev = (a0, z0)
    for a, z, sec in spans:                            # after the climax: no loud re-entry
        if a < z0 - 1e-6 or sec['name'] == 'end':
            continue
        ref = last_top(*prev)
        if ref is not None:
            cap = ref + L['reentry']
            for t in tracks:
                t._notes = _press(t._notes, a, z, cap, cap - L['knee'])
        m0 = mean_v(max(prev[0], prev[1] - 2 * bar), prev[1])    # (round g11: no section after the climax
        m1 = mean_v(a, min(z, a + 2 * bar))                     # entering far over the last bars before it)
        if m0 is not None and m1 is not None and m1 > m0 + L['after_in']:
            f = max(L['floor'], (m0 + L['after_in']) / m1)
            for t in tracks:
                t._notes = [n._replace(vel=max(1, int(round(n.vel * f)))) if a - 1e-6 <= n.start < z - 1e-6
                            else n for n in t._notes]
        prev = (a, z)
    b = a0                                             # the climax over the build: its first 2 bars
    while b > bar and energy(b - bar, b) is None:      # (a pause's silent bar skipped)
        b -= bar
    e0, e1 = energy(b - 2 * bar, b), energy(a0, a0 + 2 * bar)
    if not (e0 is None or e1 is None or e1 >= e0 + L['enter']):
        need = 10 ** ((e0 + L['enter'] - e1) / 25.0)
        top = max((n.vel for t in tracks for n in t._notes if a0 - 1e-6 <= n.start < z0 - 1e-6), default=127)
        fade = a0 + 4 * bar                            # (raised by `need` at its start, fading to 1 over 4 bars)
        for t in tracks:
            t._notes = [n._replace(vel=min(top, max(1, int(round(n.vel * (need - (need - 1) * (n.start - a0)
                                                                             / (fade - a0)))))))
                        if a0 - 1e-6 <= n.start < fade - 1e-6 else n for n in t._notes]
    _ramp(tracks, a0, z0, b, bar)


def _ramp(tracks: list, a0: float, z0: float, b: float, bar: float) -> None:
    """The climax's crescendo into its peak bar (LOUD_ORDER['ramp']; b: the end of the last sounding bar before it).
    In place."""
    R = LOUD_ORDER['ramp']
    rh = tracks[0]
    inn = [n for n in rh._notes if a0 - 1e-6 <= n.start < z0 - 1e-6]
    if not inn:
        return
    pk = max(inn, key=lambda n: (n.pitch, -n.start))
    pb = int((pk.start + 0.12 - a0) // bar)
    top = max(n.vel for n in inn)

    def mean_v(a, z):                                  # (the melody's: each onset's top note - the chord /
        ns = sorted((n for n in rh._notes if a - 0.12 <= n.start < z - 0.12 and n.dur > 0.34),    # octave notes
                    key=lambda n: n.start)             # under it are quieter by design; a run's notes left out)
        tops = []
        for n in ns:
            if tops and n.start - tops[-1][0] < 0.08:
                tops[-1] = (tops[-1][0], max(tops[-1][1], n, key=lambda x: x.pitch))
            else:
                tops.append((n.start, n))
        vs = [n.vel for _, n in tops]
        return sum(vs) / len(vs) if vs else None
    v_pk, v_pre = mean_v(a0 + pb * bar, a0 + (pb + 1) * bar), mean_v(b - 2 * bar, b)
    if pb < 1 or v_pk is None:
        return
    m0 = mean_v(a0, a0 + bar) or 0.0
    if v_pre is not None:
        m0 = max(m0, v_pre + R['in']) if b < a0 - 1e-6 else min(max(m0, v_pre + R['in']), v_pre + R['jump'])
    v_in = min(v_pk, m0)
    for k in range(pb):
        a, z = a0 + k * bar - 0.12, a0 + (k + 1) * bar - 0.12
        m_ = mean_v(a + 0.12, z + 0.12)
        if m_ is None:
            continue
        want = v_in + (v_pk - v_in) * k / pb
        f = (want - R['under']) / m_ if m_ < want - R['under'] else (want + R['over']) / m_             if m_ > want + R['over'] else 1.0
        if abs(f - 1.0) < 1e-3:
            continue
        for t in tracks:
            t._notes = [n._replace(vel=min(top, max(1, int(round(n.vel * f))))) if a <= n.start < z else n
                        for n in t._notes]


BALANCE = {'A1': 1.5, 'A': 0.5, 'B': 0.5, 'intro': -1.0, 'inter': -1.0, 'build': -0.5, 'bloom': -1.0,
           'climax': 1.0, 'coda': -1.0, 'jitter': 2.0, 'lead': 1.0, 'lead_from': ('A', 'B'), 'climax_min': 4.0,
           'a_min': 4.0, 'a_lead': 2.5}
"""The hands' balance per section (HUMAN_FEEDBACK 2026-10-15: "the right hand always feels louder than the left -
it should be dynamic"): dB the right hand's phrase sits over the left hand's (summed note energy,
romantic.ENERGY_EXP: about the stems' RMS; the fixed budget before measured 4.2-6.7 per piece), as an offset to the
piece's play('balance') - a theme's first statement keeps a clear melody (A1), a return less, the B / bridge less,
the build and the bloom near equal (the left hand carries the motion), the climax both strong, the coda close;
x U(-jitter, jitter) per section. play('lh_lead') phrases of the 'lead_from' roles (not the first A) are the left
hand's: the melody's quietest-moving phrases (the fewest onsets, drawn among the three), at 'lead' dB - the left
hand the voice, answering a held tune (the held melody notes decay: in the render the left hand leads such a
phrase by a few dB - balance_v0 at -0.5 measured 5-7 dB, too much). The role of a section: _role. Blind round
g3 (all five judges): the melody absent at the peak, the hands within 0-2 dB in the climaxes while the left hand's
16ths ran at v100+ - the climax's melody LEADS: its offset over the base, never under 'climax_min' dB (a blooming
climax too: its role stays 'climax'). Round g8 (blind round g7: the right hand only +1.2-2.7 dB over the left in
B1 / the build - AARM, JTQL, FBHB): the chorus +0.5, the build -0.5, the bloom -1.0 (were -0.5 / -1.5 / -3.0) - the
melody clearly over its accompaniment there too (~+4-5 dB); the jitter 1.5 -> 2.0 (the sections' spread kept), the
left hand's lead phrases as before. Round g9 (blind round g8: the A statements only +1.7-3 dB over a busy left
hand - every judge): an A statement of a sung genre never under 'a_min' dB, its left-hand lead phrases at 'a_lead'
(the A's lead phrases drawn 1-3, rarely none: genres play('lh_lead')) - the A sections' minimum 3.9 -> 4.2 dB, the
sections' spread kept (hand_bal_sd 1.55 -> 1.50)."""


def _role(sec: dict, bloom: str | None) -> str:
    """A piano section's balance role (BALANCE): 'bloom' / 'climax' (the peak) / 'A1' / 'A' (a return) / 'B' (B, C,
    bridge) / its frame name."""
    name = sec['name']
    if sec.get('peak'):
        return 'climax'
    if bloom and name == bloom:
        return 'bloom'
    base = name.rstrip('0123456789b') if name not in ('A1', 'A1b') else 'A1'
    if base in ('B', 'C', 'bridge'):
        return 'B'
    return base if base in BALANCE else 'A'


def _balance(tune: Tune, plan: list, secs: dict, phrases: list, rh: list, meter: int, bloom, play) -> list:
    """The piece's balance plan for Score.perform(balance=): [(from beat, to beat, dB)] per section (BALANCE over
    play('balance')), then the left hand's lead phrases (play('lh_lead') of them) - 'lead' marks those spans."""
    rng = random.Random(f"balance:{tune.seed}")
    base = play('balance', 4.5)
    # (round g9: a sung genre's A statements at least 'a_min' - DMZT A2 +3.0, JKGC A3 +2.3, NSFY A2 +1.7, the theme
    # under its accompaniment; the jitter still moves them over it)
    a_min = BALANCE['a_min'] if _sung(get(tune.genre).plan) else -99.0
    out = []
    for sec, *_ in plan:
        x = secs[sec['name']]
        r = _role(sec, bloom)
        db = base + BALANCE[r] + rng.uniform(-1, 1) * BALANCE['jitter']
        db = max(db, BALANCE['climax_min']) if r == 'climax' else max(db, a_min) if r in ('A1', 'A') else db
        out.append((x.start, x.end, round(db, 2), r))
    cands = []
    for k0, k1 in phrases:
        a, z = (k0 - 1) * meter, k1 * meter
        r = next((r for s0, s1, _, r in out if s0 - 1e-6 <= a < s1 - 1e-6), None)
        if r not in BALANCE['lead_from']:              # (A1, the theme's first statement: the melody's)
            continue
        n_ = sum(1 for n in rh if a - 1e-6 <= n.start < z - 1e-6)
        if n_:
            # (round g9: in a sung genre's A statement the left hand comes forward to 'a_lead' only - the theme
            # stays over it, the section near a_min)
            cands.append((n_ / max(1e-9, z - a), a, z, BALANCE['a_lead'] if r == 'A' and a_min > 0 else BALANCE['lead']))
    lead, picked = int(play('lh_lead', 1)), []
    cands.sort()
    while cands and len(picked) < lead:
        c = rng.choice(cands[:3])
        picked.append(c)
        cands = [d for d in cands if abs(d[1] - c[1]) > 4 * meter + 1e-6]      # (never two running)
    return [(a, z, d) for a, z, d, _ in out] + [(a, z, d) for _, a, z, d in sorted(picked, key=lambda c: c[1])]


def _bloom(tune: Tune, g: Genre, plan: list) -> dict | None:
    """The piece's bloom (plan['bloom'], genres._NA_BLOOM), drawn from its own seed: the section that blooms (one of
    'at' the piece plays), its push / reach / carry / rit / fill grid; None without plan['bloom'] or a meter other
    than 3 / 4. Not in the arrangement record (a texture decision, like the left hand's figures): a student's
    decoded tune blooms by its seed too."""
    B = g.plan.get('bloom')
    if not B or tune.meter not in (3, 4):
        return None
    names = [sec['name'] for sec, *_ in plan]
    at = {k: w for k, w in B['at'].items() if k in names}
    if not at:
        return None
    rng = random.Random(f"bloom:{tune.seed}")
    out = dict(B, name=_pick(rng, at))
    for k in ('push', 'reach', 'carry', 'rit', 'grid'):
        out[k] = _pick(rng, B[k])
    # the right hand's texture under its held notes in the bloom, per piece (blind round g2: the soft 16th broken
    # chord under a held note in 8 of 10 pieces): its own dice - the other draws stay where they were
    out['texture'] = _pick(random.Random(f"bloom-texture:{tune.seed}"), B['texture'])
    if out['texture'] == 'none':
        out['weave'] = 0.0
    return out


TEXTURE_ROLES = ('A1', 'A', 'B', 'climax', 'frame')
"""plan['texture']'s section kinds (_texture): the theme's first statement, a return, the chorus / build, the
climax, the intro / interlude / coda."""


TEXTURE_PLAIN = ('A1',)
"""The section kinds (TEXTURE_ROLES) that keep their drawn companion share under held notes too (no plan['texture']
['long'] boost) and no moving inner voice (HUMAN_FEEDBACK 2026-10-15: "mostly a single line with an occasional dyad
in an intimate first statement, inner motion under held notes in the returns and the chorus"; round g13, the
statistician: 8+ inner voices struck under held notes a generated piece from A1's first bar, 0 in the references -
"start A1 as a bare line, then thicken it")."""


def _texture(tune: Tune, plan: list, TX: dict, meter: int) -> list:
    """The right hand's texture (plan['texture']; HUMAN_FEEDBACK 2026-10-15: "note by note, as if he had only one
    finger" - 91-96 % of the right hand's onsets single notes): per section, drawn from its own seed, TX[role]
    {(voices, share): weight} - voices 0 the line alone, 1 thirds / sixths, 2 chords, 3 octaves (romantic.harmonize)
    under that share of its notes of TX['min_dur'] beats+ - the theme intimate, the returns and the chorus with
    dyads and inner motion, the climax in chords and octaves; TX['move'] {share: weight} (per piece): held notes whose
    inner voice moves; TX['connect'] {per 2 bars: weight} (per piece): connecting notes written into a part
    section's line (_embellish: a passing tone through a third, a long note turning to its neighbour) - the melody
    moving on in 8ths between its structural notes. Returns the plan with the sections' harmonize / harm_share /
    _min_dur / _move set and their lines connected."""
    from .composer import Harm
    sd = tune.seed
    move = _pick(random.Random(f"texture-move:{sd}"), TX.get('move') or {0.0: 1.0})
    conn = _pick(random.Random(f"texture-connect:{sd}"), TX.get('connect') or {0.0: 1.0})
    if meter == 3:                                    # (a waltz's held dotted halves are its breath: half as many
        move, conn = move / 2, 0.0                    # inner moves, no connecting notes - its quiet1 fell to 0.14)
    pcs = _key_pcs(tune)
    out = []
    for sec, ch, mel, L in plan:
        name = sec['name']
        role = 'frame' if 'part' not in sec else 'climax' if sec.get('peak') else \
            'A1' if name == 'A1' else 'A' if name.startswith('A') else 'B'
        w = TX.get(role)
        if w:
            v, share = _pick(random.Random(f"texture:{sd}:{name}"), w)
            if role == 'climax' and sec.get('_anthem') in ('octaves', 'chords', 'canon'):
                v, share = {'octaves': (3, 0.9), 'chords': (2, 1.0), 'canon': (1, 0.5)}[sec['_anthem']]
                #                                (the theme sung in octaves / in chords / over its own echo: _anthem)
            sec = dict(sec, harmonize=v, harm_share=share, _min_dur=TX.get('min_dur', 1.0),
                       # (the sung theme's long notes stay still; A1 intimate: TEXTURE_PLAIN)
                       _move=0.0 if sec.get('_anthem') or role in TEXTURE_PLAIN else move,
                       _long=None if role in TEXTURE_PLAIN else TX.get('long')) if v \
                else {k: x for k, x in sec.items() if k not in ('harmonize', 'harm_share')}
        if conn and 'part' in sec and mel and ch and not sec.get('peak'):
            # per phrase (4 bars; a waltz 8), its last two notes kept - the landing and its breath stay (a motto
            # statement as it is)
            ms = [(a_, z_) for a_, z_, *_ in (sec.get('_sig') or {}).get('motto', ())]

            def inm(n, _ms=ms):
                return any(a_ - 1e-6 <= n[0] < z_ - 1e-6 for a_, z_ in _ms)
            harm = Harm(ch, pcs)
            hi = max(p for *_, p in mel)
            ph = (8 if meter == 3 else 4) * meter
            new = [n for n in mel if inm(n)]
            # (round g8: a theme statement's head keeps its held top note - composer.HEAD_PROFILE, the head's
            # profile; a connecting note in its tail cut it to an 8th)
            # (round g9: half the played heads still lost the profile - a connecting note in the head widened its
            # band: the head's notes all kept as written)
            top_ = {n for n in mel if n[0] < 2 * meter - 1e-6} if sec['part'][0] == 'A' else set()
            for a in range(0, int(round(L)), int(ph)):
                chunk = sorted(n for n in mel if a - 1e-6 <= n[0] < a + ph - 1e-6 and not inm(n))
                head, tail = chunk[:-2], chunk[-2:]
                if head:
                    head = _embellish(head, harm, lambda st, du: harm.under(st, du).scale, hi,
                                      budget=int(round(conn * min(ph, L - a) / (2 * meter))), keep=top_)
                new += head + tail
            mel = sorted(new)
        out.append((sec, ch, mel, L))
    return out


def _bar_chord(timeline: list, t: float, z: float):
    """The chord symbol sounding over all of [t, z), else None."""
    return next((sym for t0, b_, sym in timeline if t0 - 1e-6 <= t and t0 + b_ + 1e-6 >= z), None)


def _lh_reach(rh, t: float, z: float, base: int, lift: int) -> int:
    """The left hand's cap in a bar of the bloom: a whole step under the lowest right-hand note sounding there,
    between its usual cap and `lift` over it."""
    low = min((n.pitch for n in rh if n.start < z - 1e-6 and n.start + n.dur > t + 1e-6), default=base + lift + 2)
    return max(base, min(base + lift, low - 2))


def _climb(fig: str, meter: int) -> float:
    """Beats a FIGURES figure moves before its trailing hold (the whole bar when it never holds)."""
    from ..pianist import FIGURES
    toks = FIGURES[fig].split()
    j = len(toks)
    while j > 0 and toks[j - 1] == '-':
        j -= 1
    return j * meter / len(toks)


def _handoffs(score, plan: list, secs: dict, timeline: list, rh: list, meter: int, bl: dict, kspans: list,
              lh_opts: dict, rng: random.Random) -> tuple:
    """The hand-to-hand figure (Für Elise's A section; HUMAN_FEEDBACK 2026-10-15): in a bar whose melody note is
    struck by the half bar and held to the next downbeat (no right-hand onset after the half bar, the next note
    on the downbeat, no phrase end there - phrase_rests' 4-bar / waltz 8-bar unit), by bl['handoff'] (the bloom's
    chance, else the part letter's) the left hand climbs (bl['bloom_hand'] / bl['hand'] - a figure ending in a
    hold) and holds, and the right hand carries the figure on from just above the left hand's top into the next
    melody note: the chord's tones (its chord scale in the local key when it has too few there - _local_scale; blind
    round g1: the home key's scale over a borrowed chord / a section in another key), in 16ths / triplets
    (bl['grid']), softer than the tune (x0.85). The melody note sounds a beat at least before the figure takes over,
    a beat at least before the downbeat (the figures that fit: _climb). The bloom's last bar runs on into the next
    section with bl['link'] (its breath goes). The held note is let go where the figure starts (the pedal holds
    it). Then the bloom's woven right hand (bl['weave']). Adds the 'fig' events to `score`; returns ({bar start:
    (left-hand figure, its figure() options)}, [the woven spans (start, end)])."""
    from .. import romantic as rom
    from ..pianist import figure
    from ..theory import note
    out: dict = {}
    base = note(lh_opts.get('cap', 67))
    fo = {k: v for k, v in lh_opts.items() if k in ('bass_lo',)}
    unit = (8 if meter == 3 else 4) * meter
    for i, (sec, ch, mel, L) in enumerate(plan):
        if 'part' not in sec or sec.get('lh_only'):
            continue
        x = secs[sec['name']]
        bloom = sec['name'] == bl['name']
        chance = bl['handoff'].get('bloom', 0.0) if bloom else bl['handoff'].get(sec['part'][0], 0.0)
        if sec.get('peak') and not bloom and i and plan[i - 1][0]['name'] == bl['name']:
            # (a climax right after the bloom keeps part of its motion, as of its push: bl['carry'] - blind round g1,
            # a waltz's climax thinner and quieter than its build)
            chance = max(chance, bl['handoff'].get('bloom', 0.0) * bl['carry'])
        if sec.get('peak'):                            # (blind round g3: the end-of-bar 16th run in 7 climaxes of 8
            chance = min(chance, bl['handoff'].get('peak', chance))      # - the melody leads there: rarer)
        figs = bl['bloom_hand' if bloom else 'hand'].get(meter)
        if not chance or not figs:
            continue
        nb = int(round(L / meter))
        ph, last_k = int(round(unit / meter)), -9
        for k in range(nb):
            t, z = x.start + k * meter, x.start + (k + 1) * meter
            link = k == nb - 1 and bloom and i + 1 < len(plan)
            if (k == nb - 1 and not link) or (not link and (z - x.start) % unit < 1e-6):
                continue                               # (a phrase end breathes)
            sym = _bar_chord(timeline, t, z)
            first = [n for n in rh if t - 1e-6 <= n.start < t + meter / 2 + 1e-6]
            nxt = [n for n in rh if abs(n.start - z) < 0.05]
            if sym is None or not first or not nxt or \
                    any(t + meter / 2 + 1e-6 <= n.start < z - 0.05 for n in rh) or \
                    any(e.kind == 'fig' and t - 1e-6 <= e.at < z for e in score.events):
                continue
            # the left hand's figures that climb while the melody note sounds a beat and hand over a beat+ before
            # the downbeat
            held_at = max(n.start for n in first) - t
            ok = {f: w for f, w in figs.items() if held_at + 1.0 - 1e-6 <= _climb(f, meter) <= meter - 1.0 + 1e-6}
            # phrase-shaped (blind round g1: the same run on beat 4 of every build / climax bar read as 'a texture
            # switched on'): full chance in the bars leading into the phrase's half and its goal (bl['goal']), less
            # elsewhere, much less right after another one
            j = k % ph
            w_ = 1.0 if j in (ph // 2 - 1, ph - 2) else bl['goal']
            if last_k == k - 1:
                w_ *= bl['goal'] / 2
            if not ok or rng.random() >= (bl['link'] if link else chance * w_):
                continue
            last_k = k
            fig = _pick(rng, ok)
            f0 = t + _climb(fig, meter)
            grid = bl['grid'] if rng.random() >= bl['regrid'] else _pick(rng, bl['grids'])
            cap = _lh_reach(rh, t, f0, base, bl['lift']) if bloom else base
            lh_top = max(n.pitch for n in figure(sym, fig, t, meter, bar=meter, cap=cap, mirror=True, **fo))
            target = max(n.pitch for n in nxt)
            c = chord(sym)
            tones = {(c.root + iv) % 12 for iv in c.intervals}
            held = {n.pitch for n in first}
            slots = max(2, int(round((z - f0) / grid)))
            run = [p for p in range(lh_top + 1, target) if p % 12 in tones and p not in held]
            if len(run) < 0.75 * slots:                # (too few chord tones there: the chord scale carries it)
                scale = _local_scale(kspans, f0, sym)
                run = [p for p in range(lh_top + 1, target) if p % 12 in scale | tones and p not in held]
            run = run[-slots:]
            if len(run) < 3:
                continue
            for e in score.events:                     # the held note lets go where the figure takes over
                if e.kind in ('note', 'chord') and t - 1e-6 <= e.at < f0 and e.at + e.dur > f0:
                    e.dur = max(0.25, f0 - e.at)
            score.events.append(rom.Event('fig', f0, z - f0, run, 0.85, args=('even',)))
            out[round(t, 4)] = (fig, {'cap': cap, 'mirror': True})
    score.events.sort(key=lambda e: e.at)
    # the bloom's woven right hand, once it has grown (from bl['reach'] of the section, with the left hand's 16ths):
    # under a melody note held a beat or more (at a phrase end a beat of air left), the chord's tones below it,
    # softer (bl['weave']), down to a 5th under the left hand's usual cap (the left hand turns under it there)
    i = next((i for i, (sec, *_) in enumerate(plan) if sec['name'] == bl['name']), None)
    woven = []
    if i is None or not bl['weave']:
        return out, woven
    x = secs[bl['name']]
    evs = [e for e in score.events if x.start - 1e-6 <= e.at < x.end - 1e-6]
    ons = sorted({round(e.at, 4) for e in score.events})
    bounds = [x.start + k * unit for k in range(1, int(round(x.length / unit)) + 1)]
    g = bl['grid']
    grown = x.start + (bl['reach'] * x.length if x.length > 6 * meter + 1e-6 else 0.0)   # (a short bloom: at once)
    for e in evs:
        if e.kind not in ('note', 'chord') or e.at < grown - 1e-6 or max(e.pitches) - min(e.pitches) > 9:
            continue                                   # (round g9: under a held octave the hand has no fingers left -
            #                                            PKCG 34-36 Gb6 / Db5 Bb4 / Ab6, "two-octave jumps in a beat")
        nx = min(x.end, next((o for o in ons if o > e.at + 1e-3), x.end))
        if any(f.kind == 'fig' and e.at - 1e-6 <= f.at < nx - 1e-6 for f in evs):
            continue
        air = 1.0 if any(e.at + 1e-6 < b_ <= nx + 1e-6 for b_ in bounds + [x.end]) else 0.0   # (a phrase end
        g0 = e.at + g * max(2, int(round(0.5 / g)))       # keeps a beat of breath; an 8th after the melody note)
        n = int(round((nx - air - g0) / g))
        sym = _bar_chord(timeline, g0, g0 + 1e-3)
        cz = next((t0 + b_ for t0, b_, s_ in timeline if t0 - 1e-6 <= g0 < t0 + b_ - 1e-6), g0)
        n = min(n, int((cz - g0) / g + 1e-6))          # (it stops where its chord does - blind round g1: a C
        if n < 2 or sym is None:                       # arpeggio carried over the bar line into Gm)
            continue
        kb = int((g0 - x.start + 1e-6) // meter)       # (right after a woven bar by bl['goal'] only: blind round
        if woven and int((woven[-1][0] - x.start + 1e-6) // meter) >= kb - 1 and rng.random() >= bl['goal']:
            continue                                   # g1, the same figure on beat 4 of every bar)
        c = chord(sym)
        tones = {(c.root + iv) % 12 for iv in c.intervals}
        mel = min(e.pitches)
        under = [p for p in range(max(base - 7, mel - 12), mel) if p % 12 in tones]
        if bl.get('texture') == 'pulse':               # (8th dyads of the chord under the held note, rocking
            low = [p for p in under if mel - p >= 3]   # between two - round g8: one dyad struck 3+ times a bar read
            pairs = [low[-2:], low[-3:-1]]             # as repeated-chord comping, JTQL 41 / VJGT 32)
            if len(low) < 3:
                continue
            g8 = 0.5
            k0, j = e.at + g8, 0
            while k0 < nx - air - 1e-6 and k0 < cz - 1e-6:
                score.events.append(rom.Event('chord', k0, g8 * 0.9, pairs[j % 2], bl['weave'] * 0.95))
                k0 += g8
                j += 1
            woven.append((e.at + g8, k0, min(low[-3:])))
            continue
        if len(under) < 3:                             # (two tones would rock: a tremolo, not a figure)
            continue
        seq, k, d = [], len(under) - 1, -1             # down from under the melody and back, bouncing
        for _ in range(n):
            seq.append(under[k])
            if not 0 <= k + d < len(under):
                d = -d
            k += d
        score.events.append(rom.Event('fig', g0, n * g, seq, bl['weave'], args=('even',)))
        woven.append((g0, g0 + n * g, min(seq)))
    score.events.sort(key=lambda e: e.at)
    return out, woven


def _fixed_or_drawn(rng: random.Random, v):
    """A figure name, or one drawn from {name: weight} (the feel's 'rest' / 'into' / 'end' figures)."""
    return _pick(rng, v) if isinstance(v, dict) else v


def _piano_drums(s: Song, b, tune: Tune, g: Genre, plan: list, secs: dict) -> None:
    """A 'piano' plan's drums: the mood's 'drums' ({'style', 'density', 'vel'}; None or a band without drums: none)
    played by the drummer over every run of consecutive sections without 'drums': False (lofi-piano: in after the
    intro, out in the bridge, the coda the piano's alone) - the tune's swing, the A sections calmer than the B's, no
    crashes, a pickup into a new run; the velocities x 'vel'. In place on b.drums."""
    from .. import drummer
    D = (g.moods.get(tune.mood) or {}).get('drums')
    if not D or 'drums' not in b:
        return
    runs, cur = [], []
    for sec, *_ in plan:
        if sec.get('drums', True):
            cur.append(sec)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    vel = float(D.get('vel', 1.0))
    for k, run in enumerate(runs):
        sections = [secs[x['name']] for x in run]
        dplan = {x['name']: {'role': 'chorus' if x.get('part', 'A')[0] == 'B' else 'verse',
                             'energy': 0.55 if x.get('peak') else 0.45 if x.get('part', 'A')[0] == 'B' else 0.35,
                             'crash': False} for x in run}
        perf = drummer.arrange(sections, bpm=tune.tempo, style=D.get('style', 'lofi'),
                               density=float(D.get('density', 0.4)), seed=tune.seed % 9973 + 31 * k,
                               kit=b.drums, swing=tune.swing or 0.5, plan=dplan, crash_every=64.0)
        clip = Clip._raw([n._replace(vel=max(1, min(127, round(n.vel * vel)))) for n in perf.clip], perf.clip.length)
        b.drums.play(clip, perf.start)


CLIMAX = {'over': {4: 1.0, 5: 1.0, 6: 0.6}, 'window': {(16, 2): 0.5, (10, 1): 0.3, (16, 7): 0.2}, 'least': 3,
          'vel': (110, 118),
          'ladder': {'bars': 3, 'step': (5, 9)}}
"""The solo's climax (blind round 6: the composed pieces put their highest note in the solo's last 8-16 bars, 60-72 %
into the piece, a 3rd-6th over the head's top, v110+, reached by a rising line and left by a descent; the head out
and the ending stay under it): 'over' {semitones over the head's top: weight} - the solo's ceiling (the soloist's
climax stage climbs to it); _peak_solo puts the solo's highest note into the window (from 'window'[0] bars before
the solo's end to 'window'[1] bars before it; drawn per tune - blind round 7: the peak at the same place in every
piece), at least 'least' over the head's top, struck at 'vel' - and
climbed into by a velocity ladder: the loudest attack of each of the 'ladder' bars before it a drawn 'step' under the
next (blind round 7: a velocity step into the climax, v70 then v115, instead of a ladder)."""


def _peak_solo(b, solo, top: int, ceiling: int, chord_fn, meter: int = 4, window=(16, 2)):
    """The piece's highest note in the solo's last bars (CLIMAX): the solo's highest sung note (an 8th+) inside the
    window - the climax stage's top, else the highest note there raised to a tone of its chord at least
    CLIMAX['least'] over the head's top `top` (at most `ceiling`, at most a 5th up); solo notes outside the window as
    high or higher come down under it; its attack struck at CLIMAX['vel'] (the voicing under it with it). Returns
    the peak's pitch (None without one)."""
    notes = [n for n in b.piano._notes if solo.start - 1e-6 <= n.start < solo.end - 1e-6]
    if not notes:
        return None
    w0 = max(solo.start + 0.5 * solo.length, solo.end - window[0] * meter)
    w1 = solo.end - window[1] * meter
    inside = [n for n in notes if w0 - 1e-6 <= n.start < w1 and n.dur >= 0.5 - 1e-6]
    if not inside:
        return None
    best = max(inside, key=lambda n: (n.pitch, n.dur, n.start))
    if best.pitch < top + CLIMAX['least']:
        for cand in sorted(inside, key=lambda n: (-n.pitch, -n.dur, -n.start))[:8]:
            c = chord_fn(cand.start + 1e-3)
            pcs = {(c.root + i) % 12 for i in c.intervals} if c is not None else {cand.pitch % 12}
            up = next((p for p in range(top + CLIMAX['least'], max(ceiling, top + CLIMAX['least']) + 1)
                       if p % 12 in pcs and p - cand.pitch <= 9), None)
            if up is not None:
                new_ = cand._replace(pitch=up)
                b.piano._notes = [new_ if x is cand else x for x in b.piano._notes]
                best = new_
                break
        else:
            return None
    P = best.pitch
    v0, v1 = CLIMAX['vel']
    f = max(1.0, min(v1, max(v0, best.vel)) / max(1, best.vel))
    out = []
    for n in b.piano._notes:
        if solo.start - 1e-6 <= n.start < solo.end - 1e-6 and n is not best and n.pitch >= P \
                and abs(n.start - best.start) >= 0.1:
            n = n._replace(pitch=n.pitch - 12 if n.pitch - 12 >= P - 14 else n.pitch - 2)   # (under the peak)
            while n.pitch >= P:
                n = n._replace(pitch=n.pitch - 1)
        if abs(n.start - best.start) < 0.1:
            n = n._replace(vel=min(124, round(n.vel * f)))
        out.append(n)
    # the ladder: each bar before the peak's a step under the next (lifted, never softened)
    lad = CLIMAX['ladder']
    rng = random.Random(f"ladder:{best.start:.3f}:{P}")
    kb = solo.start + int((best.start - solo.start + 1e-6) // meter) * meter
    goal = min(124, round(best.vel * f))
    for k in range(1, lad['bars'] + 1):
        goal -= rng.randint(*lad['step'])
        a = kb - k * meter
        here = [n for n in out if a - 1e-6 <= n.start < min(a + meter, best.start - 0.05) and n.start >= solo.start]
        loud = max((n.vel for n in here), default=0)
        if not here or loud >= goal:
            break
        g = min(1.35, goal / max(1, loud))
        ids = {id(n) for n in here}
        out = [n._replace(vel=min(124, round(n.vel * g))) if id(n) in ids else n for n in out]
    b.piano._notes = out
    return P


LH_UNDER = (2, 7)
"""The melody leads (_lh_under): in a body bar whose left-hand attack is louder than every right-hand attack, the left
hand comes down to a drawn 2..7 velocity under the right hand's loudest (blind round 7: the left hand louder than the
melody in places)."""


def _lh_under(b, sections, meter: int, rng) -> None:
    """LH_UNDER over the head / solo / head out (in place on the comping track)."""
    if 'comp' not in b.roles:
        return
    rh = b.piano._notes
    lh = list(b.comp._notes)
    for sec in sections:
        for k in range(int(round(sec.length / meter))):
            a, z = sec.start + k * meter, sec.start + (k + 1) * meter
            top = max((n.vel for n in rh if a - 1e-6 <= n.start < z - 1e-6), default=None)
            idx = [i for i, n in enumerate(lh) if a - 1e-6 <= n.start < z - 1e-6]
            if top is None or not idx:
                continue
            loud = max(lh[i].vel for i in idx)
            if loud <= top:
                continue
            f = max(1, top - rng.randint(*LH_UNDER)) / loud
            for i in idx:
                lh[i] = lh[i]._replace(vel=max(1, round(lh[i].vel * f)))
    b.comp._notes = lh


def _land_solo(b, solo, out, chord_fn, rng, meter: int) -> None:
    """The solo ends on a target (blind round 5: a solo ending in a chromatic run): the last right-hand attack, when its
    top note is no tone of the head out's first chord and does not step into the head out's first note, moves to a
    tone the two chords share (a common tone within a minor 3rd: the line resolves by holding) - or, drawn, and when
    there is none, an anticipation of the new chord follows it: its nearest tone struck an 8th before the head out
    (the last note released before it). A breath before the head out stays a breath (the last note rings into it)."""
    nxt = chord_fn(out.start + 1e-3)

    def tones(c):
        return {(c.root + i) % 12 for i in c.intervals} if c is not None else set()

    notes = [n for n in b.piano._notes if solo.start - 1e-6 <= n.start < out.start - 1e-6]
    if not notes or nxt is None:
        return
    t_last = max(n.start for n in notes)
    top = max((n for n in notes if n.start > t_last - 0.1), key=lambda n: n.pitch)
    after = [n for n in b.piano._notes if n.start >= out.start - 1e-6]
    t1 = min((n.start for n in after), default=None)     # the head out's first attack: its top note (the melody)
    first = max((n for n in after if n.start < t1 + 0.1), key=lambda n: n.pitch) if after else None
    if top.pitch % 12 in tones(nxt) or (first is not None and abs(first.pitch - top.pitch) <= 2
                                        and first.pitch % 12 in tones(nxt)):
        return
    cur = chord_fn(top.start + 1e-3)
    common = [q for q in range(top.pitch - 3, top.pitch + 4) if q % 12 in tones(nxt) & tones(cur)]
    if common and rng.random() < 0.7:
        q = min(common, key=lambda q: (abs(q - top.pitch), q))
        b.piano._notes = [n._replace(pitch=q) if n is top else n for n in b.piano._notes
                          if not (n.start > t_last - 0.1 and n is not top and n.start < out.start and n.pitch >= q)]
        return
    at = out.start - 0.5
    if at < t_last + 0.25:
        return
    q = min((q for q in range(top.pitch - 2, top.pitch + 3) if q % 12 in tones(nxt) and q != top.pitch),
            key=lambda q: (abs(q - top.pitch), q), default=None)
    if q is None:
        return
    b.piano._notes = [n._replace(dur=min(n.dur, max(0.1, at - 0.05 - n.start)))
                      if t_last - 0.1 < n.start < out.start - 1e-6 else n for n in b.piano._notes]
    b.piano.play(Clip([(0.0, 0.5, q, max(30, top.vel - 4))], length=0.5), at)


END_ROLL = {'roll': ((55, 90), (60, 95), (0.15, 0.4)), 'spread': ((105, 150), (110, 140), (0.4, 0.6)),
            'plink': ((35, 50), (40, 55), (0.1, 0.2)), 'cadenza': ((50, 75), (60, 80), (1.75, 1.75)),
            'fade': ((80, 110), (90, 115), (1.5, 1.5))}
"""The final chord's roll per END_STYLES style: (left hand ms per note, right hand ms per note, the right hand's
delay in beats) - each a range drawn per piece (blind round 6: one roll stagger in every piece read as a shared
gesture)."""


def _ending(s: Song, b, tune: Tune, end, tag, meter: int, has_bass: bool, has_drums: bool, kit,
            ceiling: int | None = None) -> None:
    """The final chord in the tune's drawn style (genres.END_STYLES, tune.end_kind), its roll drawn (END_ROLL): roll
    (the left hand rolled, the right hand after it), spread (slower and wider), plink (a quick roll crowned by a Basie
    plink: two soft high notes struck with it), cadenza (a short run down over the chord into its top note before the
    right hand's voicing), fade (the hook's head played softly into the voicing). Nothing sounds after the chord (blind
    round 6: notes after the final chord); `ceiling`: the piece's peak - every note of the ending stays under it."""
    style = getattr(tune, 'end_kind', 'roll') or 'roll'
    rng = random.Random(f"end:{tune.seed}")
    lh_end, rh_end = end_clips(tune.end_chord, meter, style, seed=tune.seed)
    root = chord(tune.end_chord).root % 12
    (l0, l1), (r0, r1), (d0, d1) = END_ROLL[style]
    ms_l, ms_r, delay = rng.uniform(l0, l1), rng.uniform(r0, r1), round(rng.uniform(d0, d1) * 4) / 4
    vel = {'spread': 0.95, 'cadenza': 0.95}.get(style, 1.0)
    if ceiling is not None and max(n.pitch for n in rh_end) >= ceiling:       # (under the piece's peak)
        rh_end = Clip._raw([n._replace(pitch=n.pitch - 12) if n.pitch >= ceiling else n for n in rh_end],
                           rh_end.length)
    if vel != 1.0:
        lh_end = Clip._raw([n._replace(vel=max(1, round(n.vel * vel))) for n in lh_end], lh_end.length)
        rh_end = Clip._raw([n._replace(vel=max(1, round(n.vel * vel))) for n in rh_end], rh_end.length)
    top = max(n.pitch for n in rh_end)
    lim = ceiling - 1 if ceiling is not None else 127
    if style == 'cadenza':                    # a run down from above the voicing's top into it, then the voicing
        run = pianist.run(min(lim, top + rng.choice((7, 9, 12))), top + 1, 1.5, s.tempo_at(end.start) * 0.6,
                          chord=tune.end_chord, key=s.key, vel=(70, 52), seed=tune.seed % 997 + 471)
        b.piano.play(run, end.start + 0.15)
    elif style == 'fade':                     # the hook's head an octave up leading into the soft voicing
        head = sorted(tune.motif)[:4]
        if head:
            sh = 12 * max(0, (top + 3 - head[0][2]) // 12)
            while head and max(q for _, _, q in head) + sh > lim:
                sh -= 12
            t0, span = head[0][0], max(0.5, head[-1][0] - head[0][0])
            k = 1.25 / span                       # (squeezed into the beat and a quarter before the voicing)
            b.piano.play(Clip([((s_ - t0) * k, 0.5, q + sh, max(44, 60 - 4 * i))
                               for i, (s_, d, q) in enumerate(head)], length=1.5), end.start + 0.1)
    elif style == 'plink':                    # two soft high notes struck with the chord: the 5th and the root above
        r_ = top + ((root + 7) - top) % 12 or 12
        if r_ + 5 > lim:
            r_ -= 12
        rh_end = Clip._raw(sorted(list(rh_end) + [rh_end[0]._replace(start=0.35, dur=1.2, pitch=r_, vel=50),
                                                  rh_end[0]._replace(start=0.6, dur=1.0, pitch=r_ + 5, vel=44)]),
                           rh_end.length)
    s.ending(end, chords=[(b.comp, lh_end, ms_l), (b.piano, rh_end, ms_r, delay)],
             bass=(b.bass, note_name(28 + (root - 28) % 12), 2 * meter - 1, 86) if has_bass else None,
             drums=(b.drums, jazz.last_stir(kit, 2 * meter, last=3)) if has_drums and kit is not None else None,
             rit=tag.bar(tag.bars // 2), to=0.75, hold=2, length=4, room=(-13, -8))


def metadata(tune: Tune, genre: Genre | None = None) -> dict:
    g = genre or get(tune.genre)
    return {'title': tune.title, 'artist': 'AgentSound', 'album': g.album,
            'genre': {'jazz': 'Jazz', 'new-age': 'New Age', 'classical': 'Classical',
                      'lofi': 'Lo-Fi', 'organ': 'Classical'}.get(g.style, 'Instrumental'),
            'year': 2026}


_PALETTES = {'late-night': ['#1f3b57', '#d9a441'], 'bright': ['#2f7a6b', '#f0c75e'], 'blue': ['#22336b', '#8fb3d9'],
             'tender': ['#6b3b4f', '#e8c4a0'], 'morning': ['#f3e3c8', '#8fa9c4'], 'longing': ['#d8c8d8', '#5b6f8f'],
             'hopeful': ['#f4ead2', '#d98c5f'], 'rain': ['#c9d3da', '#4f6372'], 'reverie': ['#ece3d0', '#6d5a7e'],
             'melancholy': ['#d6d2cc', '#3f4a5c'], 'salon': ['#f1e4d4', '#9a4f5a'], 'study': ['#3b4a5a', '#e8b98a'],
             'sunday': ['#e9dcc4', '#c27a5c'],
             # the organ's moods (endless organ)
             'chorale': ['#e8dcc0', '#5a3e2b'], 'meditation': ['#1e2a3a', '#c9b47a'], 'trio': ['#efe6d2', '#3d5a6c'],
             'toccata': ['#2a1a1a', '#d4a33b'], 'festive': ['#f2e2b8', '#8a2f2f']}
_LOFI_PALETTES = {'late-night': ['#2a2540', '#c9a0dc'], 'rain': ['#3e4a52', '#a9c1c9']}
"""lofi-piano's own colours where a mood name is shared with another genre (late-night) or its look differs."""


def cover(tune: Tune, genre: Genre | None = None) -> dict:
    g = genre or get(tune.genre)
    title = tune.title.lower() if g.style in ('jazz', 'lofi') else tune.title.upper()
    pal = (_LOFI_PALETTES.get(tune.mood) if g.style == 'lofi' else None) or _PALETTES.get(tune.mood)
    return {'style': 'jazz' if g.style in ('jazz', 'lofi') else 'classical',
            'palette': pal or ['#2b5d7a', '#d9a441'], 'title': title,
            'subtitle': f"AgentSound - {g.album}", 'seed': tune.seed % 1000}
