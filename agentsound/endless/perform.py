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
import random

from .. import bands, jazz, pianist, soloist
from ..notation import hold
from ..patches import fx
from ..patterns import Clip
from ..song import Song
from ..theory import chord, guide_tones, note_name, rootless
from .arrangement import PIANO_FIXED, Arrangement, Dice, section_specs
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


ARRANGE_KEYS = ('bars', 'tail', 'cadence', 'climax', 'reharm', 'octave_half', 'bass', 'fill', 'turn', 'vary', 'key')
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
  bars         ((first bar, end bar), ...): the part's bars played (a shortened return, a 6-bar build)
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


def _keys(tune: Tune, plan: list, meter: int, bar: float) -> None:
    """The key plan's way in and out (a section moved by _modulate, '_key'): the bar before it on the new key's
    dominant 7th (a new tonic only), its own last bar on the home dominant 7th - each bar's melody re-fitted to it.
    In place."""
    from ..theory import Key
    from .composer import Harm, _refit, spell
    t_pc = Key(tune.key).tonic % 12
    sharps = _key_sharps(tune.key)
    home = _key_pcs(tune)

    def refit(ch, mel, L, pcs, peak):
        if not mel:
            return mel
        keep = [n for n in mel if n[0] < L - bar - 1e-6]
        tail = [n for n in mel if n[0] >= L - bar - 1e-6]
        ps = [p for *_, p in mel]
        return keep + _refit(tail, Harm(ch, pcs), meter, min(ps) - 2, max(ps) - (1 if peak else 0),
                             prev=keep[-1][2] if keep else None)
    for i, (sec, ch, mel, L) in enumerate(plan):
        if not sec.get('_key') or L < 2 * bar - 1e-6:
            continue
        semis, new_t, pcs = sec['_key']
        ch2 = _last_bar(ch, L, bar, spell(t_pc + 7, sharps, 7) + '7')
        plan[i] = (sec, ch2, refit(ch2, mel, L, home, sec.get('peak')), L)
        if semis % 12 and i > 0:
            psec, pch, pmel, pL = plan[i - 1]
            if pL >= 2 * bar - 1e-6:
                off = (semis + 7) % 12
                pch2 = _last_bar(pch, pL, bar, spell(t_pc + off, sharps, off) + '7')
                plan[i - 1] = (psec, pch2, refit(pch2, pmel, pL, pcs, psec.get('peak')), pL)


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


def _arrange(tune: Tune, sec: dict, ch: list, mel: list, meter: int, ar: random.Random, bar: float | None = None,
             dice=None, pins: dict | None = None):
    """The section's drawn arrangement options (ARRANGE_KEYS, through `dice`: the arrangement record) -> (section,
    changes, melody); a climax drawn 'step' marks the returned section dict ('_step') for _pivot. Bar counts (bars /
    tail / turn) are in `bar` beats (default one bar; plan['form_bars']: a form bar - a waltz, its form doubled,
    plays each as two 3/4 bars). The tune's set-level pins (`pins`, default Tune.arrange: composer.set_plan - the
    climax kind) replace that draw (the dice still roll); the record's value wins over both."""
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
    how = None
    if sec.get('climax'):
        how = pick('climax')
        if how in ('theme', 'climb'):
            # theme: the A1 an octave up (the apotheosis); climb: the section's own part (the chorus) an octave up
            # where that fits under C7, else in place - both developed: the first half kept, the second half a
            # sequence of it a step higher (_sequel)
            src = tune.parts[0] if how == 'theme' else sec['part']
            notes = tune.melody.get(src) or []
            up = 12 if how == 'theme' or (notes and max(p for _, _, p in notes) + 12 <= 93) else 0
            if not up and P_.get('peak_floor'):
                how = 'grow'                           # (round r9: the chorus in place, a copy - grown instead)
            elif notes and max(p for _, _, p in notes) + up <= 96:
                ch, mel = list(tune.changes[src]), [(st, du, p + up) for st, du, p in notes]
                mel = _sequel(ch, mel, meter, Key(tune.key).pcs, 96)
                top = max(p for _, _, p in mel)            # one peak: the top struck once (the latest one; the
                last = max(i for i, n in enumerate(mel) if n[2] == top)    # others a scale step lower)
                pcs = Key(tune.key).pcs
                mel = [(st, du, p - (2 if (p - 2) % 12 in pcs else 1)) if p == top and i != last else (st, du, p)
                       for i, (st, du, p) in enumerate(mel)]
        elif how == 'lift' and mel and max(p for _, _, p in mel) + 12 <= 91:
            mel = [(st, du, p + 12) for st, du, p in mel]     # (round r7: a low chorus's lifted line stayed under
            #                                                     the build - a climax made by velocity alone)
        elif how == 'lift' and mel and P_.get('peak_floor'):
            how = 'grow'                               # (round r9: no room for the lift - the chorus copied in place)
        elif how == 'step':
            ch = [(_transpose_sym(sym, 2, tune.key), b) for sym, b in ch]
            mel = [(st, du, p + 2) for st, du, p in mel]
            sec = dict(sec, _step=True)
    moving = None
    if sec.get('key') and not sec.get('_step') and ch:
        # the section in another key (KEY_SHIFTS; moved below, _keys leads in and back): one with a written key
        # signature; a peak section's line stays under G6 (_fold: the line moves to the nearer octave)
        top_ = max(p for *_, p in mel) if mel and sec.get('peak') and how != 'grow' else None
        w = {k: v for k, v in sec['key'][tune.key.split()[1]].items() if _key_named(tune.key, k)
             and (top_ is None or top_ + _fold(KEY_SHIFTS[k][0]) <= 91)} or {'home': 1.0}
        moving = dice.put(sec['name'], 'key', _pick(random.Random(f"key:{tune.seed}:{sec['name']}"), w))
    if how == 'grow' and ch:
        # grown from the hook over the section's own chords, to a peak over every head note (_grow) - in the key the
        # section moves to: its peak where the move puts it
        top = max(p for m_ in tune.melody.values() for _, _, p in m_)
        up = _fold(KEY_SHIFTS.get(moving, (0, None))[0]) if moving else 0
        grown = _grow(ch, tune.motif or tune.melody[tune.parts[0]], meter, _key_pcs(tune),
                      min(91, min(91, top + 2) - up))
        if grown:
            mel = grown
    if sec.get('reharm') and not sec.get('_step') and ch:
        share = pick('reharm')
        table = (get(tune.genre).harmony.get('reharm') or {}).get(tune.key.split()[1])
        if share and table:
            ch = _reharm(ch, sorted(mel), tune.key, table, share, meter, ar)
    if sec.get('peak') and P_.get('unswing') and ch and mel and not sec.get('_step'):
        # (round r10: a climax rocking between two chords, Bbm7 Abmaj7 Bbm7 Abmaj7 - the third of such a run takes
        # a substitute under its melody; its own dice)
        table = (get(tune.genre).harmony.get('reharm') or {}).get(tune.key.split()[1])
        if table:
            ch = _unswing(ch, sorted(mel), tune.key, table, meter, random.Random(f"swing:{tune.seed}:{sec['name']}"))
    if sec.get('vary') and mel and ch and how != 'grow':
        # a return developed unit by unit (VARY; its own dice: the other draws stay where they were) - a climax
        # restating the chorus / the theme too (round r9: the climax = the chorus transposed); a grown one is new
        units = int(round(sum(b for _, b in ch) / (2 * meter)))
        kinds = dice.put(sec['name'], 'vary', _vary_draw(sec, units, random.Random(f"vary:{tune.seed}:{sec['name']}")))
        mel = _vary(ch, mel, meter, _key_pcs(tune), kinds)
        if sec.get('peak') and mel:
            from .composer import Harm
            mel = _single_top(sorted(mel), Harm(ch, _key_pcs(tune)))
    if moving:
        moved = _modulate(tune, ch, mel, meter, moving, single=bool(sec.get('peak')))
        if moved:
            ch, mel, k_ = moved
            sec = dict(sec, _key=k_)
    if sec.get('bars'):
        spans, ch0, mel0 = pick('bars'), ch, mel
        ch, mel, off = [], [], 0.0
        for a, b in spans:
            ch += _slice_changes(ch0, a * bar, b * bar)
            mel += [(st - a * bar + off, du, p) for st, du, p in mel0 if a * bar - 1e-6 <= st < b * bar - 1e-6]
            off += (b - a) * bar
    if sec.get('tail'):
        n = pick('tail')
        if n and ch:                                   # (a tonic close runs on into a Vsus4 - the held tonic is its
            ch = ch + [(spell(t_pc + 7, sharps, 7) + 'sus4', n * bar)] if chord(ch[-1][0]).root % 12 == t_pc \
                else ch[:-1] + [(ch[-1][0], ch[-1][1] + n * bar)]                 # 4th; a dominant is held)
            if mel:
                last = max(mel)
                mel = [x for x in mel if x != last] + [(last[0], last[1] + n * bar, last[2])]
    if sec.get('cadence'):
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
    if sec.get('turn') and ch and pick('turn') and ch[-1][1] >= 2 * bar - 1e-6:
        # a closing chord held 2+ bars: its last bar becomes ii - V (a written cadence / turnaround into the next
        # section, not 'X | %')
        sym, b = ch[-1]
        ii = spell(t_pc + 2, sharps, 2) + ('m7b5' if minor else 'm7')
        ch = ch[:-1] + [(sym, b - bar), (ii, bar / 2), (spell(t_pc + 7, sharps, 7) + '7', bar / 2)]
    if sec.get('fill') and mel and pick('fill'):
        mel = _fill(ch, sorted(mel), meter)
    return dict(sec), ch, sorted(mel)


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


def _fill(ch: list, mel: list, meter: int) -> list:
    """The melody with each bar that has no onset (a held note or a rest all bar) filled: the last bar before it
    with 2+ onsets again, each note moved to the nearest tone of the chord sounding under it (a written lead-in /
    echo, not a hole); a note held into the bar is cut at its bar line."""
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
        if any(a - 1e-6 <= st < a + meter - 1e-6 for st, _, _ in out):
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


def _vary_draw(sec: dict, units: int, rng: random.Random) -> list:
    """A section's 'vary' kinds, one per 2-bar unit: a phrase's second unit (its ending: every odd unit) and the
    last unit among VARY_END - a sequence or an inversion there would lose the cadence."""
    w = sec['vary']
    end = {k: v for k, v in w.items() if k in VARY_END} or {'keep': 1.0}
    return [_pick(rng, end if k % 2 or k == units - 1 else w) for k in range(units)]


def _embellish(own: list, harm, scale_of, hi: int, budget: int = 2) -> list:
    """_vary's 'orn': up to `budget` figures - a third (a quarter+ stepping on) filled by a passing tone, a 2-beat+
    note turning to its neighbour and back; none of those: an appoggiatura from the step above on the first long
    note."""
    from .composer import _scale_step
    out, done = [], 0
    for i, (st, du, p) in enumerate(own):
        nxt = own[i + 1] if i + 1 < len(own) else None
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
            if du >= 1 - 1e-6 and up < hi and (i == 0 or out[i - 1][2] != up):
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


def _vary(ch: list, mel: list, meter: int, key_pcs, kinds: list) -> list:
    """A return's melody developed per 2-bar unit (VARY: kinds[k] for unit k; the notes past the last unit stay).
    Every changed unit stays in the section's range and on its chords (composer._refit for 'seq' / 'invert')."""
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
            new = _embellish(own, harm, scale_of, hi)
        elif how == 'rhythm' and own:
            new = _rerhythm(own, a, meter, harm, key)
        elif how == 'seq' and prev:
            mean = sum(p for *_, p in own) / len(own) if own else None
            pm = sum(p for *_, p in prev) / len(prev)
            step = -1 if mean is not None and mean < pm else 1
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
            new = _refit([(st, du, p0 - (p - p0)) for st, du, p in own], harm, meter, lo, hi,
                         prev=out[-1][2] if out else None)
        out += new
        prev = new or prev
    out += [n for n in mel if n[0] >= len(kinds) * unit - 1e-6]
    out.sort()
    return [(st, min(du, out[i + 1][0] - st) if i + 1 < len(out) else du, p) for i, (st, du, p) in enumerate(out)
            if i + 1 == len(out) or out[i + 1][0] - st > 1e-6]


def _grow(ch: list, hook: list, meter: int, key_pcs, peak: int) -> list | None:
    """The 'grow' climax (the learned generator's blind round 2: the climax was B1 replayed or A an octave up, never a
    new idea derived from the motif; new-age round r8: the piece read composed restated the hook and extended it to a
    new peak): per 2-bar unit over the section's chords - the hook (`hook`: A1's first unit) restated at a new
    pitch level, then sequenced a scale step higher per unit (every other statement answered: its second half turned
    over), the unit at ~60 % climbing its head twice into the single peak (the highest chord tone / tension at or
    under `peak`, held), then released (the hook's contour turned, falling) and landed (its head turned, a long chord
    tone). None when the hook has under 3 notes."""
    from .composer import Harm, _refit, _scale_step
    harm = Harm(ch, key_pcs)
    unit = 2 * meter
    n = int(round(harm.length / unit))
    hook = sorted(x for x in hook if x[0] < unit - 1e-6)
    if len(hook) < 3 or n < 3:
        return None
    key = set(key_pcs)
    top_h = max(p for *_, p in hook)
    pu = max(1, min(n - 2, int(round(0.6 * n))))

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
        if k < pu:                                     # the statements: a step higher per unit
            notes = at(d0 + rise(k), hook, t)
            if k >= 2 and k % 2 == 0:                  # (a sequence breaks after two steps - new-age round r11: the
                h0 = head[0][0]                        # hook five times up the scale): the head, then a step higher
                a_ = at(d0 + rise(k), [(st - h0, du, p) for st, du, p in head], t)            # and held
                b_ = at(d0 + rise(k) + 1, [(st - h0, du, p) for st, du, p in head], t + meter)
                b_[-1] = (b_[-1][0], max(b_[-1][1], t + unit - 0.5 - b_[-1][0]), b_[-1][2])
                notes = a_ + b_
            elif k % 2:                                # (every other one answered: its second half turned over -
                half = [i for i, x in enumerate(notes) if x[0] >= t + meter - 1e-6]     # where it stays under the
                if half and half[0] > 0:                                               # statement's top)
                    piv = notes[half[0] - 1][2]
                    turned = [(st, du, piv - (p - piv)) if i in half else (st, du, p)
                              for i, (st, du, p) in enumerate(notes)]
                    if max(p for *_, p in turned) <= max(p for *_, p in notes):
                        notes = turned
        elif k == pu:                                  # the climb: the head twice, then the peak held
            h0 = head[0][0]
            one = at(d0 + rise(pu - 1) + 1, [(st - h0, du, p) for st, du, p in head], t)
            two = at(d0 + rise(pu - 1) + 3, [(st - h0, du, p) for st, du, p in head], t + meter)
            last = two[-1]
            two[-1] = (last[0], max(last[1], t + unit - 0.5 - last[0]), peak)
            peak_at = last[0]
            notes = one + two
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
            if k < n - 1:
                notes = [(t + 2 * (st - h0), 2 * du, _scale_step(p, lv, key)) for st, du, p in head]
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


def _modulate(tune: Tune, ch: list, mel: list, meter: int, how: str, single: bool = False):
    """A section moved into another key (KEY_SHIFTS[how]) -> (changes, melody, (semitones, new tonic pc, its pcs)) or
    None when it stays home: the chords transposed and spelled in the new key (_transpose_sym), the melody moved the
    same way (_fold: to the nearer octave), a minor section turned major ('par' / 'rel': its 3rd raised, its 6th /
    7th where the chord under it has them) and re-fitted to its chords; single: its top note struck once (the
    others a scale step under it)."""
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
    if out:
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
                 weights=None) -> list:
    """A waltz's changes with each chord held 2+ whole bars split into bars, each later bar drawn (blind round r6:
    'every chord exactly 2 bars, X | %'; r7: 'X | X/3rd' in every pair read as a slot-filling rule): held, over its
    3rd / 5th in the bass (F | F/A), or a substitute under the melody (_reharm's table: F | Dm7); sus chords and the
    closing chord stay held. take: the drawn moves (one per later bar, in order) -> the moves played (the
    arrangement record's 'moves': dice.put). weights: the moves' {move: weight} (plan['moves']; given, a closing
    chord held 3+ bars moves too, all but its last bar - the learned generator's blind round 2: 4-bar one-chord
    stretches at a section's end)."""
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
    kp = set(Key(key).pcs) if key else None
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
            if how == 'ped':
                out.append((ped(sym, m.group(1), t_ + k * bar) or fifth, bar))      # (else over its 5th)
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


def _under_peak(plan: list, key_pcs=None, floor: int = 64) -> None:
    """The peak section's top note is the piece's highest: another section reaching it (an octave-up return, a
    frame's line) comes down an octave - unless that drops its line under `floor` (E4: new-age round r9, the chorus
    an octave down in the left hand's register, F#3 under its C#4): then only its notes at the peak come down to the
    key tone below it (key_pcs given) - unless that is more than a quarter of its notes (the sweep of 2026-10-13: an
    octave-up return held on one pitch for 8 bars): then the octave comes down after all. In place."""
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
        return set_draws(g, random.Random(f"set-draws:{g.name}:{tune.seed}"))
    return getattr(tune, 'arrange', None) or {}


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
    # (plan['form_bars']: the sections' bar counts are form bars - a waltz plays each as two 3/4 bars)
    stretch = 2 if meter == 3 and P.get('form_bars') else 1
    spec = section_specs(g, layout)
    drawn = [x['name'] for x in spec.values() if not (x.get('feels') and tune.feel not in x['feels'])
             and rng.random() < x.get('chance', 1.0)]
    plan = []
    for name in dice.order(drawn):
        if name not in spec:
            from ..theory import ComposeError
            raise ComposeError(f"arrangement: {g.name} has no section {name!r} (plan['sections'], layout {layout})")
        base = spec[name]
        sec = dict(base)
        for k in PIANO_FIXED:
            if isinstance(base.get(k), dict):                # (lh_only: below; another {value: weight} - a section's
                if k != 'lh_only':                           # dynamics - drawn here with its own dice)
                    sec[k] = dice.put(name, k, _pick(random.Random(f"{k}:{sd}:{name}"), base[k]))
                continue
            v = dice.put(name, k, base.get(k))
            if v is not None:
                sec[k] = v
        if 'part' in sec:
            part = sec['part']
            ch = list(tune.changes[part])
            mel = (tune.out_melody.get(part) if sec.get('melody') == 'lift' else None) or tune.melody[part]
        else:
            fr = tune.intro if sec['frame'] == 'intro' else tune.tag
            ch, mel = list(fr['changes']), list(fr['melody'])
            if sec.get('keep_bars'):
                mel = [n for n in mel if int(n[0] // (meter * stretch)) in sec['keep_bars']]
        if any(k in sec for k in ARRANGE_KEYS):        # (drawn arrangement options: their own dice per section)
            sec, ch, mel = _arrange(tune, sec, ch, mel, meter, random.Random(f"arrange:{sd}:{sec['name']}"),
                                    bar=meter * stretch, dice=dice, pins=pins)
        if stretch > 1 and ch and ('part' in sec or P.get('moves')):     # (a waltz: its long chords move bar
            ch = _moving_bass(ch, meter, sorted(mel), tune.key,             # by bar; with plan['moves'] its frames
                              None if sec.get('_key') or 'part' not in sec else    # too - a section in another key /
                              (get(tune.genre).harmony.get('reharm') or {}).get(tune.key.split()[1]),   # a frame: no
                              #                                                     home substitutes)
                              random.Random(f"waltz-bars:{sd}:{sec['name']}"),
                              take=lambda v, _n=name: dice.put(_n, 'moves', v), weights=P.get('moves'))
        if isinstance(base.get('lh_only'), dict):      # (the intro's left hand alone: drawn bars)
            sec = dict(sec, lh_only=dice.put(name, 'lh_only',
                                             _pick(random.Random(f"lh-only:{sd}:{sec['name']}"), base['lh_only'])))
        if sec.get('lh_only'):
            mel = [n for n in mel if n[0] >= sec['lh_only'] * meter * stretch - 1e-6]
        L = sum(b for _, b in ch)
        octave = base.get('octave')
        if isinstance(octave, dict):
            octave = _pick(random.Random(f"octave:{sd}:{sec['name']}"), octave)
        octave = dice.put(name, 'octave', octave) or 0
        mel = [(st, min(du, L - st, P.get('max_hold', L)), p + 12 * octave) for st, du, p in mel if st < L - 1e-6]
        plan.append((sec, ch, mel, L))
    if any(k in sec for sec, *_ in plan for k in ARRANGE_KEYS):
        _pivot(tune, plan, meter)                      # a climax a step up: the bar before it pivots into its key
        _keys(tune, plan, meter, meter * stretch)      # a section in another key: in on its dominant, out on home's
        _under_peak(plan, _key_pcs(tune) if P.get('peak_floor') else None,    # nothing outside the climax as
                    P.get('peak_floor') or 64)                                 # high as its peak
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
    return None


def _play_piano(tune: Tune, g: Genre, s: Song, plan: list, rng: random.Random, A: Arrangement) -> Song:
    """build_piano's performance of its plan (the sections' material) and arrangement A (the dice `rng` after the
    section and cadenza draws: the left hand's figures)."""
    from .. import romantic as rom
    from ..patterns import Note
    from ..theory import Key
    F, P = g.feels[tune.feel], g.plan
    meter, sd = tune.meter, tune.seed
    figs = F.get('figures') or {}
    end_bars = max(1, P.get('end', 1))

    def play(k, default):                             # (a per-piece choice of plan['play'], the record's; else the
        v = A.get(None, k)                            # constant every other genre plays)
        return default if v is None else v
    bl = _bloom(tune, g, plan)                        # the bloom: its section breathes lightly into the next one
    if bl:                                            # (a blooming climax keeps its broad end)
        plan = [(dict(sec, rit=bl['rit']) if sec['name'] == bl['name'] and sec.get('rit') and not sec.get('peak')
                 else sec, ch, mel, L) for sec, ch, mel, L in plan]
    for sec, _, _, L in plan:
        s.section(sec['name'], bars=L / meter)
    s.section('end', bars=end_bars)
    secs = {x.name: x for x in s.sections}
    # ---- the notes: the right hand (harmonized), the chord timeline, the dynamic marks, the phrases
    rh, timeline, marks, phrases = [], [], [], []
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
            notes = list(rom.harmonize(Clip._raw(notes, a + L), chord_at, voices=v, min_dur=0.9 if v == 2 else 1.0,
                                       share=sec.get('harm_share', 1.0 if v == 2 else 0.5),
                                       floor='G4' if v == 2 else 'F4',
                                       seed=sd % 997 + len(rh)))
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
    voicing = sorted({top} | {top - ((top - pc) % 12 or 12) for pc in tones if pc != top_pc})[-4:]
    timeline.append((end.start, end.length, tune.end_chord))
    marks.append((end.start, play('end_dyn', 'pp')))
    phrases.append((int(round(end.start / meter)) + 1, int(round(end.end / meter))))
    total = end.end
    score = rom.score(Clip._raw(rh, total), None, None, meter=f"{meter}/4", key=tune.key, phrases=phrases)
    score.events.append(rom.Event('roll', end.start, end.length - 0.25, voicing, 0.85,
                                  args=(play('end_roll', 110),)))
    # ornaments (plan['ornaments'] {kind: chance per part section}; new-age blind round N0: no turn anywhere, the
    # references one per theme statement): a turn / mordent on a held note that steps on to the next one
    peak_p = max((n.pitch for n in rh), default=128)
    for sec, *_ in plan:
        if 'part' not in sec or not P.get('ornaments'):
            continue
        x = secs[sec['name']]
        evs = [e for e in score.events if x.start - 1e-6 <= e.at < x.end - 1e-6]
        ro = random.Random(f"ornament:{sd}:{sec['name']}")
        for kind, chance in P['ornaments'].items():
            if ro.random() >= chance:
                continue
            ok = [e for e, nx in zip(evs, evs[1:]) if e.kind == 'note' and 0.9 <= e.dur <= 2.5
                  and nx.kind in ('note', 'chord') and 0 < abs(nx.pitches[-1] - e.pitch) <= 2
                  and e.pitch + 2 < peak_p]            # (its upper neighbour never strikes the climax note again)
            if ok:
                ro.choice(ok).kind = kind
    # a cadenza flourish over the last dominant of a section that asks for one: a run down from above the
    # section's top into the next section's first melody note (one free gesture; the right hand's notes there go)
    cadenzas = set()
    for i, (sec, ch, mel, L) in enumerate(plan):
        if not A.get(sec['name'], 'cadenza') or i + 1 >= len(plan) or not plan[i + 1][2]:   # (drawn: _piano_draws)
            continue
        z = secs[sec['name']].end
        a0 = z - min(2.0, meter)
        nxt = plan[i + 1][2][0][2]
        hi_ = max(n[2] for n in mel) + 3
        dom = chord(ch[-1][0])                     # the key's scale, the dominant's own tones (its leading tone)
        pcs = ({q % 12 for q in Key(tune.key).pcs} - ({(dom.root + 3) % 12} if not dom.is_minor else set())) | \
            {(dom.root + i) % 12 for i in dom.intervals}
        run = [p for p in range(hi_, nxt, -1) if p % 12 in pcs][:14]
        if len(run) >= 6:
            score.events = [e for e in score.events if not a0 - 1e-6 <= e.at < z - 1e-6]
            score.events.append(rom.Event('fig', a0, z - a0, run, 0.9, args=('arch',)))
            cadenzas.add(sec['name'])
    score.events.sort(key=lambda e: e.at)
    # the hand-to-hand figures (the left hand climbs, the right carries it on over a held note) and the bloom
    hands, woven = _handoffs(score, plan, secs, timeline, rh, meter, bl, tune.key, P.get('lh') or {},
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
            lh_only = sec is not None and sec.get('lh_only') and \
                t < secs[sec['name']].start + sec['lh_only'] * meter - 1e-6
            own = None
            blooms = bool(bl) and sec is not None and sec['name'] == bl['name'] and not lh_only
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
    if not plan[-1][0].get('rit'):
        s.ritardando((end.start - meter, end.start), to=0.8, a_tempo=False)
    s.fermata(end.start, hold=play('end_hold', 3))
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
        ro = None if not P.get('play') else dict(seed=sd % 9973, **({'lean_ms': A.get(None, 'push')}
                                                                     if A.get(None, 'push') is not None else {}))
        score.perform(s, b.piano, b.comp, pedal=True, touch=dict(lo=lo, hi=hi), breath=play('breath', 0.35),
                      cap=play('cap', P.get('cap', 106)), figures=lh, inner=play('inner', 0.78),
                      figure_vel=play('lh_vel', 41), figure_opts=P.get('lh'), pedal_opts=po, rubato=ro)
    finally:
        del s.tempo_at
    if 'vinyl' in b:                                  # the vinyl bed under the whole piece (lofi_piano)
        from ..bandlib.jazz import lofi_crackle
        lofi_crackle(b, 0.0, end.end - 0.5, tail=4.0, seed=sd)
    s.endless_tune = tune
    s.endless_lh = {k: max(set(v), key=v.count) for k, v in used.items()}
    s.endless_figures = used
    s.endless_bloom = None if not bl else {'section': bl['name'], 'push': bl['push'], 'handoffs': len(hands),
                                           'woven': len(woven)}
    s.endless_sections = [(sec['name'], secs[sec['name']].start, secs[sec['name']].end) for sec, *_ in plan]
    s.endless_timeline = [(t, b_, sym) for t, b_, sym in timeline]     # (beat, beats, chord): the chart as played
    s.endless_memory, s.endless_played = None, {}
    s.endless_arrangement = A        # (what was played: the record - the layout, every section's drawn options)
    return s


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


def _handoffs(score, plan: list, secs: dict, timeline: list, rh: list, meter: int, bl: dict, key: str,
              lh_opts: dict, rng: random.Random) -> tuple:
    """The hand-to-hand figure (Für Elise's A section; HUMAN_FEEDBACK 2026-10-15): in a bar whose melody note is
    struck by the half bar and held to the next downbeat (no right-hand onset after the half bar, the next note
    on the downbeat, no phrase end there - phrase_rests' 4-bar / waltz 8-bar unit), by bl['handoff'] (the bloom's
    chance, else the part letter's) the left hand climbs (bl['bloom_hand'] / bl['hand'] - a figure ending in a
    hold) and holds, and the right hand carries the figure on from just above the left hand's top into the next
    melody note: the chord's tones (the key's scale when the chord has too few there), in 16ths / triplets
    (bl['grid']), softer than the tune (x0.85). The melody note sounds a beat at least before the figure takes over,
    a beat at least before the downbeat (the figures that fit: _climb). The bloom's last bar runs on into the next
    section with bl['link'] (its breath goes). The held note is let go where the figure starts (the pedal holds
    it). Then the bloom's woven right hand (bl['weave']). Adds the 'fig' events to `score`; returns ({bar start:
    (left-hand figure, its figure() options)}, [the woven spans (start, end)])."""
    from .. import romantic as rom
    from ..pianist import figure
    from ..theory import Key, note
    out: dict = {}
    base = note(lh_opts.get('cap', 67))
    fo = {k: v for k, v in lh_opts.items() if k in ('bass_lo',)}
    unit = (8 if meter == 3 else 4) * meter
    scale = set(Key(key).pcs)
    for i, (sec, ch, mel, L) in enumerate(plan):
        if 'part' not in sec or sec.get('lh_only'):
            continue
        x = secs[sec['name']]
        bloom = sec['name'] == bl['name']
        chance = bl['handoff'].get('bloom', 0.0) if bloom else bl['handoff'].get(sec['part'][0], 0.0)
        figs = bl['bloom_hand' if bloom else 'hand'].get(meter)
        if not chance or not figs:
            continue
        nb = int(round(L / meter))
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
            if not ok or rng.random() >= (bl['link'] if link else chance):
                continue
            fig = _pick(rng, ok)
            f0 = t + _climb(fig, meter)
            cap = _lh_reach(rh, t, f0, base, bl['lift']) if bloom else base
            lh_top = max(n.pitch for n in figure(sym, fig, t, meter, bar=meter, cap=cap, mirror=True, **fo))
            target = max(n.pitch for n in nxt)
            c = chord(sym)
            tones = {(c.root + iv) % 12 for iv in c.intervals}
            held = {n.pitch for n in first}
            slots = max(2, int(round((z - f0) / bl['grid'])))
            run = [p for p in range(lh_top + 1, target) if p % 12 in tones and p not in held]
            if len(run) < 0.75 * slots:                # (too few chord tones there: the scale carries it)
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
        if e.kind not in ('note', 'chord') or e.at < grown - 1e-6:
            continue
        nx = min(x.end, next((o for o in ons if o > e.at + 1e-3), x.end))
        if any(f.kind == 'fig' and e.at - 1e-6 <= f.at < nx - 1e-6 for f in evs):
            continue
        air = 1.0 if any(e.at + 1e-6 < b_ <= nx + 1e-6 for b_ in bounds + [x.end]) else 0.0   # (a phrase end
        g0 = e.at + g * max(2, int(round(0.5 / g)))       # keeps a beat of breath; an 8th after the melody note)
        n = int(round((nx - air - g0) / g))
        sym = _bar_chord(timeline, g0, g0 + 1e-3)
        if n < 2 or sym is None:
            continue
        c = chord(sym)
        tones = {(c.root + iv) % 12 for iv in c.intervals}
        mel = min(e.pitches)
        under = [p for p in range(max(base - 7, mel - 12), mel) if p % 12 in tones]
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
