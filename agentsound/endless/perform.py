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
from .composer import Tune, _chord_fn, _pick, targets
from .genres import FORMS, Genre, get


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
    shift) and the spec's optional trims / pans / sends / eq on top. The one place the sound is set up - the pro
    reference songs (songs/pro-piano-*) call it too, so they sound like an endless tune by construction. mood: a mood
    whose 'drums' is None leaves the preset's drums out (lofi-piano's rain: the piano alone)."""
    BD = genre.band
    without = tuple(BD.get('without', ()))
    M = genre.moods.get(mood) if mood else None
    if M is not None and 'drums' in M and M['drums'] is None and 'drums' in bands.get(BD['preset']).roles:
        without += ('drums',)
    b = bands.make(BD['preset'], s, without=without, feel=feel,
                   master_gain=BD['master_gain'] + genre.feels[feel_name].get('master', 0.0))
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


def phrase_levels(tune: Tune, part: str, plan: dict, seed) -> list:
    """The phrase-to-phrase dynamics of a head part (humanize.touch levels=: [(beat, velocity shift)]): every 2-bar
    phrase moved by plan['head']['phrase_touch']['arc'] x its plan level (tune.levels) over the part's mean - the
    bridge's climb louder, the release softer - plus a step drawn per 4-bar phrase (never the same twice running, a
    quiet one after a loud one); the part's loudest phrase stays at the plan's level, the others come down by up to
    'depth' (the piece's peak stays where the plan put it). [] without the plan entry or levels."""
    pt = (plan.get('head') or {}).get('phrase_touch')
    lv = (getattr(tune, 'levels', None) or {}).get(part)
    if not pt or not lv:
        return []
    rng = random.Random(f"phrase-touch:{seed}:{part}")
    unit, mean = tune.part_beats(part) / len(lv), sum(lv) / len(lv)
    raw, step = [], 0
    for u, x in enumerate(lv):
        if u % 2 == 0:
            step = _pick(rng, {k: w for k, w in pt['steps'].items() if k != step and not (step > 0 and k > 0)})
        raw.append(pt['arc'] * (x - mean) + step)
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


def solo_arc(tune: Tune, genre: Genre) -> tuple:
    """The solo's arc (soloist stages) of the tune's drawn shape (genre.plan['solo']['shapes']): its soloist.ARCS
    entry, with a 'burst' (double-time 16ths) inserted at a drawn place in its second half when the tune goes double
    time (the solo builds to its last chorus: blind round 5)."""
    shapes = genre.plan['solo'].get('shapes') or {}
    name = shapes.get(getattr(tune, 'solo_shape', None), {}).get('arc', genre.plan['solo'].get('arc', 'build'))
    stages = list(soloist.ARCS[name])
    if getattr(tune, 'double', False):              # (before the climax: the burst builds into it)
        top = next((i for i, st in enumerate(stages) if st[0] in ('climax', 'chords')), len(stages))
        at = random.Random(f"double:{tune.seed}").randint(min(top, max(1, len(stages) // 2)), top)
        stages.insert(at, ('burst', 0.2, True))
    return tuple(stages)


def build(tune: Tune, genre: Genre | None = None, prev: Song | None = None) -> Song:
    """The Song of a Tune (deterministic: every seed derives from tune.seed). prev: the tune before it in a set (its
    Song): what it played - the pianist's fast figures, the soloist's moves - is drawn less often here (a set's
    memory: the same licks do not come back tune after tune)."""
    g = genre or get(tune.genre)
    if g.plan.get('perform', 'jazz') == 'piano':
        return build_piano(tune, g)
    F, P, BD = g.feels[tune.feel], g.plan, g.band
    meter, sd = tune.meter, tune.seed
    stretch = 2 if meter == 3 else 1
    s = Song(tune.title, tempo=tune.tempo, key=tune.key, seed=sd % 100000 + 1, tail=6, meter=(meter, 4))
    FD = FORMS[tune.form]
    letters = ''.join(p[0] for p in tune.parts)
    end_bars = P['end'] * (1 if meter == 4 else 2)
    # the solo: whole choruses (a blues: as many 12-bar choruses as fit the plan's solo seconds, up to FORMS' solo)
    unit = ['A1'] if tune.form == 'blues' else list(tune.parts)
    unit_s = tune.part_beats(tune.parts[0]) * len(unit) * 60.0 / tune.tempo
    n_solo = max(1, min(FD['solo'], round(P['solo'].get('seconds', 75) / unit_s)))
    # the solo plays the tune's chart - a blues chorus by chorus the head's first or second chorus chart (drawn:
    # tune.solo_charts, its turnarounds vary); a reharm (composer.reharm: one cadence of a head-out part) sounds in the
    # last solo chorus and the head out alike ('v' parts)
    sch = getattr(tune, 'solo_changes', None) or {}
    charts = getattr(tune, 'solo_charts', None) or []
    solo_labels = [charts[k] if tune.form == 'blues' and k < len(charts) else p for k in range(n_solo) for p in unit]
    out_labels = list(FD['out'])
    for p in sch:                                       # the reharmonized part: in the last chorus and the head out
        if tune.form == 'blues':
            solo_labels[-1] = out_labels[-1] = p + 'v'
            continue
        solo_labels[len(solo_labels) - len(unit) + unit.index(p)] = p + 'v'
        out_labels = [x + 'v' if x == p else x for x in out_labels]
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
                                levels=phrase_levels(tune, part, P, sd)) for x, part in zip(lifts, parts)])

    def arc(part, what):                             # a part's arc target (genres.ARCS) from its plan level
        return targets(g, tune.part_level(part))[what]

    # the left hand changes its figure from section to section (the feel's 'lh_plan': {where: a LH style / a
    # pianist.FIGURES figure or {name: weight}}, drawn, never twice running - shells, tenths, walking 10ths, broken
    # chords); without a plan (or a bossa's comping hand) the feel's one style everywhere, as before
    lh_plan = F.get('lh_plan') if lh else None
    lrng = random.Random(f"lh-plan:{sd}")
    lh_used: dict = {}

    def lh_of(where, default):
        """(LH style, its broken-chord figure) for a section / part."""
        name = default
        if lh_plan and lh_plan.get(where.split(':')[0]) is not None:
            prev_ = next(reversed(lh_used.values()), None) if lh_used else None
            name = _draw(lrng, lh_plan[where.split(':')[0]], prev_)
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
    solo_top = top if dyn.get('out_peak') and out_top > top else \
        top + _pick(random.Random(f"peak:{sd}"), CLIMAX['over'])
    s_lh = lh_of('solo', lh)[0] if lh_plan else lh
    voc = pianist.vocabulary(F.get('solo', 'straight'), lh_track=b.comp if lh else None, lh=s_lh, lh_vel=56,
                             memory=mem, seed=sd % 997 + 201, phrase_bars=sp.get('phrase_bars', 4) * stretch,
                             vel=tuple(shape_.get('solo_vel', dyn.get('solo_vel', sp.get('vel', (58, 110))))),
                             register=('A4', note_name(solo_top)),
                             weights=dict(sp.get('weights') or {}, **shape_.get('weights', {})))
    motif = tune.clip(tune.motif, 2 * meter)
    soloist.solo(s, b.piano, voc, at=solo, prog=solo.prog, motif=motif, budget=bud, seed=sd % 997 + 211,
                 arc=solo_arc(tune, g), energy=sp.get('energy', 0.75) + sp.get('energy_set', 0.15) * tune.energy)
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
    out_lv = [[] if i == 0 and dyn.get('out_peak') else phrase_levels(tune, n, P, sd + 1) for i, n in enumerate(names)]
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
        peak = _peak_solo(b, solo, top, solo_top, chord_fn, meter)

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
    s.endless_lh = {k: v for k, v in lh_used.items()} if lh_plan else \
        {k: (lh if k in ('head', 'solo', 'out') else lh or 'tenths') for k in ('intro', 'head', 'solo', 'out', 'tag')}
    s.endless_tune = tune                                   # what the runner logs / writes next to the mp3
    # the set's memory (what this tune played): the next tune avoids them
    s.endless_memory = mem
    s.endless_played = {k: v - seeded.get(k, 0) for k, v in bud.played.items() if v > seeded.get(k, 0)}
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


def build_piano(tune: Tune, genre: Genre | None = None) -> Song:
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
    final chord. Deterministic from tune.seed.
    (The body model - humanize, another branch - hooks in after Score.perform: one gesture per phrase over both
    hands' timing and touch; it reads s.endless_sections / the phrases here.)"""
    from .. import romantic as rom
    from ..patterns import Note
    from ..theory import Key, Progression
    g = genre or get(tune.genre)
    F, P = g.feels[tune.feel], g.plan
    meter, sd = tune.meter, tune.seed
    rng = random.Random(f"piano:{sd}")
    figs = F.get('figures') or {}
    s = Song(tune.title, tempo=tune.tempo, key=tune.key, seed=sd % 100000 + 1, tail=7, meter=(meter, 4))
    # ---- the material of every section (the chance drawn per section, in order)
    plan = []
    for sec in P['sections']:
        if sec.get('feels') and tune.feel not in sec['feels']:
            continue
        if rng.random() >= sec.get('chance', 1.0):
            continue
        if 'part' in sec:
            part = sec['part']
            ch = list(tune.changes[part])
            mel = (tune.out_melody.get(part) if sec.get('melody') == 'lift' else None) or tune.melody[part]
        else:
            fr = tune.intro if sec['frame'] == 'intro' else tune.tag
            ch, mel = list(fr['changes']), list(fr['melody'])
            if sec.get('keep_bars'):
                mel = [n for n in mel if int(n[0] // meter) in sec['keep_bars']]
        if sec.get('lh_only'):
            mel = [n for n in mel if n[0] >= sec['lh_only'] * meter - 1e-6]
        L = sum(b for _, b in ch)
        mel = [(st, min(du, L - st), p + 12 * sec.get('octave', 0)) for st, du, p in mel if st < L - 1e-6]
        plan.append((sec, ch, mel, L))
    end_bars = max(1, P.get('end', 1))
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
                                       share=1.0 if v == 2 else 0.5, floor='G4' if v == 2 else 'F4',
                                       seed=sd % 997 + len(rh)))
        if sec.get('peak') and mel:
            top = max(mel, key=lambda n: (n[2], -n[0]))
            peak_at = a + top[0]
        rh += notes
        marks += _marks(sec.get('dyn', 'mp'), a, a + L, peak_at if sec.get('peak') else None)
        k0 = int(round(a / meter)) + 1
        nb = int(round(L / meter))
        step = 4                                      # (4-bar phrases: a waltz's touch arcs too)
        for f0 in range(0, nb, step):
            phrases.append((k0 + f0, k0 + min(nb, f0 + step) - 1))
    # the final chord: the end chord rolled in the right hand over the left hand's rolled chord
    end = secs['end']
    ec = chord(tune.end_chord)
    tones = sorted({(ec.root + i) % 12 for i in ec.intervals})
    top_pc = (tune.motif[0][2] % 12) if tune.motif and tune.motif[0][2] % 12 in tones else ec.root % 12
    top = 72 + (top_pc - 72) % 12 + 12
    voicing = sorted({top} | {top - ((top - pc) % 12 or 12) for pc in tones if pc != top_pc})[-4:]
    timeline.append((end.start, end.length, tune.end_chord))
    marks.append((end.start, 'pp'))
    phrases.append((int(round(end.start / meter)) + 1, int(round(end.end / meter))))
    total = end.end
    score = rom.score(Clip._raw(rh, total), None, None, meter=f"{meter}/4", key=tune.key, phrases=phrases)
    score.events.append(rom.Event('roll', end.start, end.length - 0.25, voicing, 0.85, args=(110,)))
    # a cadenza flourish over the last dominant of a section that asks for one: a run down from above the
    # section's top into the next section's first melody note (one free gesture; the right hand's notes there go)
    cadenzas = set()
    for i, (sec, ch, mel, L) in enumerate(plan):
        if not sec.get('cadenza') or rng.random() >= sec['cadenza'] or i + 1 >= len(plan) or not plan[i + 1][2]:
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
            if sec is None:
                fig = figs.get('end', 'roll')
            elif peak_start is not None and peak_start - meter - 1e-6 <= t < peak_start - 1e-6:
                fig = figs.get('into', 'up')
            elif not lh_only and _breathes(rh, t, span):
                fig = figs.get('rest', 'half')
            else:
                fig = _draw(rng, fset, last)
                last = fig
            lh.append((t, span, sym, fig))
            used.setdefault(sec['name'] if sec else 'end', []).append(fig)
            t += span
    # ---- the tempo: phrase rubato, the sections' tempo / ritardandi / fermatas, an inhale before the peak (a
    # 'steady' feel keeps strict time - a drum loop plays along: no phrase rubato, no inhale, no lilt)
    steady = bool(F.get('steady'))
    if F.get('rubato', 0.05) > 0 and not steady:
        score.rubato(s, depth=F.get('rubato', 0.05), shapes=('breath', 'breath', 'lean'), seed='bar')
    before = {}
    for sec, *_ in plan:
        x = secs[sec['name']]
        s.set_tempo(x.start, tune.tempo * sec.get('tempo', 1.0))
        if sec.get('peak') and x.start - 2 > 0 and not before.get('rit') and not steady:   # (the inhale: unless
            s.ritardando((x.start - 2.0, x.start), to=0.85)          # the section before slows into it already)
        before = sec
        if sec.get('rit') and x.length > meter:
            s.ritardando((x.end - meter + 1.0, x.end), to=sec['rit'],
                         a_tempo=not sec.get('fermata') and sec is not plan[-1][0])
        if sec.get('fermata'):
            s.fermata(x.end - (0.5 if sec['name'] in cadenzas else min(1.5, meter - 1.0)), hold=sec['fermata'])
    if not plan[-1][0].get('rit'):
        s.ritardando((end.start - meter, end.start), to=0.8, a_tempo=False)
    s.fermata(end.start, hold=3)
    if not steady:
        s.lilt((0.0, end.start), beats={3: 0.03} if meter == 4 else {2: 0.04}, jitter=0.03, seed=sd % 997)
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
    score.dyn = [(beat, lv) for beat, lv in sorted(marks)]
    # the tempo plan is final here: the pianist reads one tempo map (song.tempo_at rebuilds it per call - thousands
    # of calls over a 4-minute piece with rubato + lilt)
    tm = s.tempo_map()
    s.tempo_at = lambda beat: tm.bpm_at(s._at(beat))
    try:
        score.perform(s, b.piano, b.comp, pedal=True, touch=dict(lo=lo, hi=hi), breath=0.35, cap=106, figures=lh,
                      inner=0.78)
    finally:
        del s.tempo_at
    if 'vinyl' in b:                                  # the vinyl bed under the whole piece (lofi_piano)
        from ..bandlib.jazz import lofi_crackle
        lofi_crackle(b, 0.0, end.end - 0.5, tail=4.0, seed=sd)
    s.endless_tune = tune
    s.endless_lh = {k: max(set(v), key=v.count) for k, v in used.items()}
    s.endless_figures = used
    s.endless_sections = [(sec['name'], secs[sec['name']].start, secs[sec['name']].end) for sec, *_ in plan]
    s.endless_memory, s.endless_played = None, {}
    return s


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


CLIMAX = {'over': {4: 1.0, 5: 1.0, 6: 0.6}, 'window': (16, 2), 'least': 3, 'vel': (110, 118)}
"""The solo's climax (blind round 6: the composed pieces put their highest note in the solo's last 8-16 bars, 60-72 %
into the piece, a 3rd-6th over the head's top, v110+, reached by a rising line and left by a descent; the head out
and the ending stay under it): 'over' {semitones over the head's top: weight} - the solo's ceiling (the soloist's
climax stage climbs to it); _peak_solo puts the solo's highest note into the window (from 'window'[0] bars before
the solo's end to 'window'[1] bars before it), at least 'least' over the head's top, struck at 'vel'."""


def _peak_solo(b, solo, top: int, ceiling: int, chord_fn, meter: int = 4):
    """The piece's highest note in the solo's last bars (CLIMAX): the solo's highest sung note (an 8th+) inside the
    window - the climax stage's top, else the highest note there raised to a tone of its chord at least
    CLIMAX['least'] over the head's top `top` (at most `ceiling`, at most a 5th up); solo notes outside the window as
    high or higher come down under it; its attack struck at CLIMAX['vel'] (the voicing under it with it). Returns
    the peak's pitch (None without one)."""
    notes = [n for n in b.piano._notes if solo.start - 1e-6 <= n.start < solo.end - 1e-6]
    if not notes:
        return None
    w0 = max(solo.start + 0.5 * solo.length, solo.end - CLIMAX['window'][0] * meter)
    w1 = solo.end - CLIMAX['window'][1] * meter
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
    b.piano._notes = out
    return P


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
                      'lofi': 'Lo-Fi'}.get(g.style, 'Instrumental'),
            'year': 2026}


_PALETTES = {'late-night': ['#1f3b57', '#d9a441'], 'bright': ['#2f7a6b', '#f0c75e'], 'blue': ['#22336b', '#8fb3d9'],
             'tender': ['#6b3b4f', '#e8c4a0'], 'morning': ['#f3e3c8', '#8fa9c4'], 'longing': ['#d8c8d8', '#5b6f8f'],
             'hopeful': ['#f4ead2', '#d98c5f'], 'rain': ['#c9d3da', '#4f6372'], 'reverie': ['#ece3d0', '#6d5a7e'],
             'melancholy': ['#d6d2cc', '#3f4a5c'], 'salon': ['#f1e4d4', '#9a4f5a'], 'study': ['#3b4a5a', '#e8b98a'],
             'sunday': ['#e9dcc4', '#c27a5c']}
_LOFI_PALETTES = {'late-night': ['#2a2540', '#c9a0dc'], 'rain': ['#3e4a52', '#a9c1c9']}
"""lofi-piano's own colours where a mood name is shared with another genre (late-night) or its look differs."""


def cover(tune: Tune, genre: Genre | None = None) -> dict:
    g = genre or get(tune.genre)
    title = tune.title.lower() if g.style in ('jazz', 'lofi') else tune.title.upper()
    pal = (_LOFI_PALETTES.get(tune.mood) if g.style == 'lofi' else None) or _PALETTES.get(tune.mood)
    return {'style': 'jazz' if g.style in ('jazz', 'lofi') else 'classical',
            'palette': pal or ['#2b5d7a', '#d9a441'], 'title': title,
            'subtitle': f"AgentSound - {g.album}", 'seed': tune.seed % 1000}
