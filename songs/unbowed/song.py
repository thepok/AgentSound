"""Unbowed - Symphony in C minor, I. Adagio molto - Allegro con brio. An original first movement in the idiom of
Beethoven's middle-period symphonies (1804-1812). Build: python -m agentsound build songs/unbowed

No note, theme, motif or progression is Beethoven's (score.py). The idiom is his: one terse cell that everything grows
from (an 8th leaping up a sixth onto a syncopated, off-beat sforzando, a step down, a landing), sonata form with a slow
introduction, sforzandi on the weak beats, syncopes and hemiolas, subito piano after a crescendo, horn calls that
announce the second theme, natural trumpets and timpani on tonic and dominant, the flat sixth and the Neapolitan as
surprises, a fugato in the development, a long dominant pedal with a crescendo into the recapitulation, a short oboe
cadenza, a coda that is a second development - and the struggle from C minor to a hammered C major.

  intro    10  Adagio molto q=56  C minor  unison C ff (fermata) -> winds pp on Ab; the cell in slow motion; unison Ab
                                           ff -> Db pp; German sixth; the dominant pedal grows (fermata)
  t1        8  Allegro con brio   C minor  first theme p in the strings (a sentence), half cadence, general pause
  t1ff      8  q=148              C minor  counterstatement ff tutti, hammered chords in the rests, Neapolitan bend
  trans    16                     -> Eb    syncopated sforzandi over a falling bass, the cell in the basses, a hemiola,
                                           the Bb pedal: the horn call and its clarinet echo, diminuendo
  t2       16                     Eb major second theme p dolce: solo clarinet, then violins + flute; the cell's rhythm
                                           in the cellos; a deceptive turn to Cb (bVI)
  closing  12                     Eb major the cell in major ff, a hemiola cadence, the codetta in the basses, two blows
  dev1     12                     Cm Ab Fm Db Bbm  the cell tossed between winds and violins through falling thirds
  fugato   16                     F minor  fugato: cellos, violas (answer), violins II, violins I
  storm     8                     -> Gb    hammered syncopated tutti into Gb major; subito pp the second theme in Gb
                                           (clarinet, flute), German sixth
  pedal    16                     G pedal  pp, the cell climbing in imitation, a long crescendo to ff
  rec1      8                     C minor  the first theme ff tutti, the half cadence held (fermata)
  cadenza   2  Adagio q=52                 the oboe alone over a held G7
  rec2     12  q=148              -> G     the transition rewritten: syncopes, hemiola, the horn call on G
  rec3     16                     C major  the second theme in C major (violins; flute + oboe)
  rec4     12                     C major  the closing in C major - G7 breaks into Ab (bVI) ff
  coda1    16                     Ab Db Cm a second development: the Neapolitan, subito p, the chromatic climb
  coda2    12                     C major  the triumph: the cell in C major ff, trumpets and horns; the horn call
  coda3     8                     C major  hammered tonic chords, the last in unison under a fermata

Sound: bands.symphony_orchestra (SSO 4.0 sections in the Musikverein IR) as Beethoven scored it: strings, pairs of
flutes, oboes, clarinets and bassoons, horns, 2 trumpets, timpani on C / G (no trombones, tuba, harp, percussion);
solo VSCO 2 horn (the calls), clarinet (the second theme) and oboe (the cadenza), played by agentsound.hornist. The
harmony is voiced by agentsound.voicing (strings, the interlocked wind pairs, the tutti) around the lines written by
hand; the fugato's free voices too. Profile 'classical'.

CREDITS: Sonatina Symphonic Orchestra 4.0 (Mattias Westlund, Peter Eastman; CC Sampling Plus 1.0), Virtual Playing
Orchestra 3 (Paul Battersby), VSCO 2 CE (Versilian Studios, CC0), Voxengo IM Reverbs (Musikvereinsaal).
"""
import random

from agentsound import *
from agentsound import articulation as art
from agentsound import bands, hornist, mastering, voicing
from agentsound.bandlib import orchestra as orch
from agentsound.humanize import touch

import score as sc

ANALYSIS = {'profile': 'classical'}
METADATA = {'title': 'Unbowed', 'artist': 'AgentSound', 'album': 'Symphony in C minor', 'genre': 'Classical',
            'comment': 'I. Adagio molto - Allegro con brio (in the style of Beethoven\'s middle period)'}
COVER = {'style': 'classical', 'palette': 'noir', 'title': 'UNBOWED', 'subtitle': 'Symphony in C minor'}

# ---------------------------------------------------------------------------------------------- mix (MIX.md)
# Balance by the score (dB): the theme carriers (violins I, the flutes / oboes doubling it) on top of their own
# accompaniment, the inner strings' drive and the low strings' 8ths under it, the basses up (the sub was -8.6 dB
# under the classical reference), the violas / violins II's low mids and the violins I's 1.2 kHz box taken down.
MIX = {
    'trim': {'violins1': 1.5, 'violas': -2.5, 'cellos': -1.5, 'basses': 3.0, 'horns': -1.5, 'timpani': -1.0},
    'ride': {'violins1': {'t1': 3.0, 't1ff': 1.5, 't2': 4.5, 'closing': 1.5, 'rec1': 1.5, 'rec3': 3.0, 'rec4': 1.5,
                          'coda2': 1.5},
             'violins2': {'t1': -2.0},
             'violas': {'t1': -2.0, 't1ff': -1.5, 'closing': -1.5, 'storm': -2.0, 'rec1': -1.5, 'rec4': -1.5,
                        'coda2': -1.5},
             'cellos': {'t1ff': -1.0, 'rec1': -1.0, 'rec3': -3.0},
             'basses': {'fugato': -4.0, 'coda2': -2.0},
             'clarinets': {'dev1': 3.0},
             'flutes': {'t1ff': 1.5, 't2': 2.5, 'rec1': 1.5, 'rec3': 2.0, 'coda2': 1.5},
             'oboes': {'t1ff': 1.0, 'dev1': 4.0, 'rec1': 1.0, 'rec3': 2.0}},
    'eq': {'violins1': [{'freq': 1200, 'gain': -1.5, 'q': 1.0}, {'freq': 3300, 'gain': -1.0, 'q': 1.0}],
           'violins2': [{'freq': 300, 'gain': -2.0, 'q': 1.0}],
           'violas': [{'freq': 300, 'gain': -2.5, 'q': 1.0}],
           'cellos': [{'freq': 400, 'gain': -1.5, 'q': 1.0}],
           'hall': [{'freq': 650, 'gain': -2.0, 'q': 0.7}]},
}

DEBUG: dict = {}
STRINGS_UNDER = {'violins1': (60, 96, 76), 'violins2': (55, 84, 67), 'violas': (48, 76, 60), 'cellos': (36, 64, 48)}
TP_NATURAL = (60, 64, 67, 72, 76, 79)          # natural trumpets in C: C4 E4 G4 C5 E5 G5
TIMP = {0: 48, 7: 43}                          # timpani tuned C3 / G2
SECTIONS = [('intro', 10), ('t1', 8), ('t1ff', 8), ('trans', 16), ('t2', 16), ('closing', 12),
            ('dev1', 12), ('fugato', 16), ('storm', 8), ('pedal', 16),
            ('rec1', 8), ('cadenza', 2), ('rec2', 12), ('rec3', 16), ('rec4', 12),
            ('coda1', 16), ('coda2', 12), ('coda3', 8)]
# the dynamics map (velocity 40 p, 78 mf, 95 f, 115 ff): (beat in the section, velocity[, 'step' = subito])
DYNAMICS = {
    'intro': [(0, 108), (2, 42, 'step'), (8, 44), (16, 50), (23.9, 54), (24, 110, 'step'), (26, 42, 'step'),
              (32, 46), (36, 74), (39.9, 100)],
    't1': [(0, 68), (16, 70), (20, 72), (24, 76), (28, 92), (30, 96)],
    't1ff': [(0, 108), (31.9, 110)],
    'trans': [(0, 96), (31.9, 100), (32, 106, 'step'), (47.9, 108), (48, 58, 'step'), (56, 52), (63.9, 48)],
    't2': [(0, 64), (16, 66), (28, 62), (32, 70), (48, 78), (56, 86), (60, 72), (63.9, 70)],
    'closing': [(0, 104), (31.9, 108), (32, 54, 'step'), (43.9, 50), (44, 110, 'step')],
    'dev1': [(0, 84), (16, 88), (32, 96), (47.9, 102)],
    'fugato': [(0, 80), (16, 84), (32, 92), (48, 98), (63.9, 106)],
    'storm': [(0, 110), (15.9, 112), (16, 46, 'step'), (28, 50), (31.9, 56)],
    'pedal': [(0, 46), (16, 50), (32, 58), (48, 90), (60, 122), (63.9, 124)],
    'rec1': [(0, 112), (28, 110), (31.9, 106)],
    'cadenza': [(0, 58), (7.9, 52)],
    'rec2': [(0, 96), (16, 100), (31.9, 106), (32, 56, 'step'), (47.9, 50)],
    'rec3': [(0, 66), (16, 66), (28, 64), (32, 72), (48, 80), (56, 88), (63.9, 74)],
    'rec4': [(0, 104), (31.9, 108), (32, 56, 'step'), (40, 62), (44, 96), (47.9, 112)],
    'coda1': [(0, 100), (15.9, 98), (16, 58, 'step'), (31.9, 60), (32, 54), (48, 84), (63.9, 124)],
    'coda2': [(0, 126), (47.9, 127)],
    'coda3': [(0, 127), (31.9, 127)],
}
WINDS8_ROLE = {'fl1': 'flutes', 'fl2': 'flutes', 'ob1': 'oboes', 'ob2': 'oboes', 'cl1': 'clarinets',
               'cl2': 'clarinets', 'bn1': 'bassoons', 'bn2': 'bassoons'}
TUTTI_ROLE = {'flutes': ('v1', 'v2'), 'oboes': ('v2', 'v3'), 'clarinets': ('v3', 'v4'), 'bassoons': ('v6', 'v7'),
              'violins1': ('v1', 'v2'), 'violins2': ('v3', 'v4'), 'violas': ('v5', 'v6'), 'cellos': ('v7',),
              'basses': ('v8',)}
MELODIC = {'violins1': 0.9, 'violins2': 0.7, 'violas': 0.5, 'cellos': 0.6, 'basses': 0.4, 'flutes': 0.8,
           'oboes': 0.8, 'clarinets': 0.7, 'bassoons': 0.6, 'horns': 0.5}


def build() -> Song:
    s = Song('Unbowed', tempo=56, key='C minor', seed=1808, tail=7)
    S = {name: s.section(name, bars=b) for name, b in SECTIONS}
    intro, t1, rec1, cad, rec2, coda3 = S['intro'], S['t1'], S['rec1'], S['cadenza'], S['rec2'], S['coda3']

    # ------------------------------------------------------------------------------------------ tempo
    s.rubato((intro.bar(2), intro.bar(6)), depth=0.05, phrase='breath')
    s.fermata(intro.start, hold=2.5, length=2)                              # the unison C
    s.fermata(intro.bar(6), hold=1.5, length=2)                             # the unison Ab
    s.fermata(intro.bar(9), hold=3, length=4)                               # G7, into the Allegro
    s.set_tempo(t1, 148)
    s.fermata(rec1.bar(7), hold=2.5, length=2)                              # the half cadence before the cadenza
    s.set_tempo(cad, 52)
    s.rubato((cad.start, cad.bar(1) + 2), depth=0.08, phrase='breath')
    s.fermata(cad.bar(1) + 3, hold=2, length=1)
    s.set_tempo(rec2, 148)
    s.ritardando((S['coda1'].bar(15) + 2, S['coda1'].end), to=0.9, a_tempo=True)
    s.fermata(coda3.bar(6), hold=4, length=6)                               # the last chord

    # ------------------------------------------------------------------------------------------ the ensemble
    o = bands.symphony_orchestra(s, without=('trombones', 'tuba', 'percussion', 'harp', 'celesta'))
    hall = o.buses['hall']
    # sound design (SOUND.md): the hall's air (the SSO sections are dark on top: the return opened to 20 kHz and
    # lifted above 9 kHz), the violins' steel taken off at 3.2 kHz (the recipe: -1..-3 dB when the top is steely)
    hall.automate('fx.convolver.highcut', [(0, 20000.0)])
    hall.add_fx(fx.eq({'high.freq': 9000, 'high.gain': 2.0, 'high.q': 0.7071}))
    for role in ('violins1', 'violins2'):
        o[role].add_fx(fx.eq({'peak1.freq': 3200, 'peak1.gain': -2.5, 'peak1.q': 0.9}, name='steel'))
    horn =s.track('horn_solo', 'sampled/solo_horn', pan=-0.3, gain_db=-1.0, sends={hall: -4})
    clar = s.track('clarinet_solo', 'sampled/solo_clarinet', pan=-0.05, gain_db=-2.0, sends={hall: -6})
    oboe = s.track('oboe_solo', 'sampled/solo_oboe', pan=0.1, gain_db=-1.0, sends={hall: -7})

    # ------------------------------------------------------------------------------------------ dynamics
    K = []
    for name, pts in DYNAMICS.items():
        a = float(S[name].start)
        K.extend((a + p[0], p[1]) + tuple(p[2:]) for p in pts)
    K.sort(key=lambda p: (p[0], len(p)))

    def dyn(t: float) -> float:
        prev = K[0]
        for p in K:
            if p[0] > t:
                if len(p) == 3:
                    return prev[1]
                span = p[0] - prev[0]
                return prev[1] + (p[1] - prev[1]) * ((t - prev[0]) / span if span > 0 else 1.0)
            prev = p
        return prev[1]

    rnd = random.Random(1808)

    def phase(t: float) -> float:
        for sec in s.sections:
            if sec.start - 1e-6 <= t < sec.end - 1e-6:
                return ((t - sec.start) % sec.beats_per_bar) / sec.beats_per_bar
        return 0.0

    def vel(t: float, off: float = 0.0, accent: bool = True) -> int:
        v = dyn(t) + off + rnd.uniform(-3, 3)
        if accent:
            ph = phase(t)
            v += 5 if ph < 0.02 else 2 if abs(ph - 0.5) < 0.02 else 0
        return max(14, min(127, round(v)))

    # ------------------------------------------------------------------------------------------ part buffers
    parts: dict = {}           # role -> [(start, dur, pitch, vel, articulation)]

    def shape(notes, k):
        if len(notes) < 3 or not k:
            return lambda n: 0.0
        shaped = touch(Clip([(n[0], n[1], n[2], 80) for n in notes], length=0), 40, 80, gap='1/4')
        by = {(round(m.start, 4), m.pitch): m.vel for m in shaped}
        return lambda n: k * (by.get((round(n[0], 4), n[2]), 60) - 60)

    def add(role, notes, art_name='sustain', off=0.0, accent=True, dur_f=1.0, transpose=0, sf=()):
        """Notes [(start, dur, pitch[, vel])] onto a role; sf: beats of a sforzando (+16 velocity, marcato)."""
        buf = parts.setdefault(role, [])
        arc = shape([n for n in notes if len(n) < 4], MELODIC.get(role, 0.0))
        sfs = {round(x, 3) for x in sf}
        for n in notes:
            st, du, p = n[0], n[1], n[2]
            v = n[3] if len(n) > 3 else min(127, max(14, round(vel(st, off, accent) + arc(n))))
            a = art_name
            if round(st, 3) in sfs:
                v, a = min(127, v + 16), 'marcato'
            buf.append((st, du * dur_f, p + transpose, v, a))

    def window(notes, a, b):
        return [n for n in notes if a - 1e-6 <= n[0] < b - 1e-6]

    def mel(spec, t0, shift=0):
        return sc.line(spec, float(t0), shift)

    def tl(table, t0):
        return voicing.timeline(table, float(t0))

    def chord_at(harm, t):
        return voicing.harmony_at(harm, t)

    # textures --------------------------------------------------------------------------------------------
    def pulse(notes, step=0.5, gap=0.42):
        """Repeated notes every `step` beats inside each note (the string drive)."""
        out = []
        for a, d, p in notes:
            k = a
            while k < a + d - 1e-6:
                out.append((k, min(gap, a + d - k), p))
                k += step
        return out

    def syncopes(notes, gap=0.85):
        """Off-beat attacks held across the beat: a sforzando between the beats."""
        out = []
        for a, d, p in notes:
            k = a + 0.5
            while k < a + d - 1e-6:
                out.append((k, min(gap, a + d - k), p))
                k += 1.0
        return out

    def beats_of(notes, every=1.0, gap=0.8, offset=0.0):
        out = []
        for a, d, p in notes:
            k = a + offset
            while k < a + d - 1e-6:
                out.append((k, min(gap, a + d - k), p))
                k += every
        return out

    def voiced(table, t0, voices, **kw):
        return voicing.chorale(table, float(t0), voices=voices, key=kw.pop('key', 'C minor'), **kw)

    def under(table, t0, melody, voices=STRINGS_UNDER, top='violins1', tie=True, **kw):
        """The voices under a written melody: each chord voiced with the melody's sounding note (else the table's
        top) as the fixed top voice and the melody's other notes avoided; returns the lower voices."""
        rows = []
        t = float(t0)
        for row in table:
            dur, sym, ttop, bass, *more = row
            if sym is not None:
                now = [n[2] for n in melody if n[0] - 1e-6 <= t < n[0] + n[1] - 1e-6]
                rows.append((dur, sym, now[0] if now else ttop, bass, *more))
            else:
                rows.append(row)
            t += dur
        p = voicing.chorale(rows, float(t0), voices=voices, key=kw.pop('key', 'C minor'), tie=tie, **kw)
        p.pop(top, None)
        return p

    def tutti(table, t0, top_shift=12, bass_shift=-12, key='C minor'):
        """The full orchestra's chord: TUTTI voices (v1 = the table's top + top_shift, v8 = its bass + bass_shift)."""
        rows = []
        for dur, sym, ttop, bass, *more in table:
            rows.append((dur, sym, None if ttop is None else voicing.N(ttop) + top_shift,
                         None if bass is None else voicing.N(bass) + bass_shift))
        return voicing.chorale(rows, float(t0), voices=voicing.TUTTI, key=key, unison=True)

    def tutti_hits(tp, times, length=0.8, off=0.0, roles=None, sf=False):
        """Hammered tutti chords at the given beats from TUTTI parts tp (the chord sounding there)."""
        for role, vs in TUTTI_ROLE.items():
            if roles is not None and role not in roles:
                continue
            ns = []
            for t in times:
                for v in vs:
                    p = sc.N(next((n[2] for n in tp[v] if n[0] - 1e-6 <= t < n[0] + n[1] - 1e-6), 0) or 0)
                    if p:
                        ns.append((t, length, p))
            add(role, ns, 'marcato' if sf else 'staccato' if length <= 0.6 else 'sustain', off=off)

    def brass(harm, times, length=0.8, off=0.0, horns=True, trumpets=True, timpani=True, roll=False, art_name=None):
        """Natural trumpets (C / E / G), horns (two chord tones C3-C5) and timpani (C3 / G2) on the chords at
        `times` - only the notes the chord holds."""
        for t in times:
            sym = chord_at(harm, t + 1e-3)
            if sym is None:
                continue
            ci = voicing.info(sym)
            a = art_name or ('marcato' if length <= 1.0 else 'sustain')
            ph = phase(t)
            off_t = off + (6 if ph < 0.02 else -2 if abs(ph - 0.5) < 0.02 else -7)   # the downbeat leads
            if trumpets:
                tps = [p for p in TP_NATURAL if p % 12 in ci.pcs][-2:]
                add('trumpets', [(t, length, p) for p in tps], a, off=off_t - 4)
            if horns:
                hs = sorted({p for p in range(55, 72) if p % 12 in ci.pcs}, key=lambda p: abs(p - 64))[:2]
                add('horns', [(t, length, p) for p in hs], a, off=off_t - 2)
            if timpani:
                pcs = [pc for pc in (ci.root, 0, 7) if pc in TIMP and pc in ci.pcs]
                if pcs:
                    add('timpani', [(t, length if roll else 0.5, TIMP[pcs[0]])], 'roll' if roll else 'hit',
                        off=off_t - 6)

    def wind_chords(table, t0, off=0.0, roles=None, key='C minor', art_name='sustain', tie=True, top_shift=12):
        rows = [(r[0], r[1], None if r[2] is None else voicing.N(r[2]) + top_shift, *r[3:]) for r in table]
        p = voicing.chorale(rows, float(t0), voices=voicing.WINDS8, key=key, tie=tie, unison=True)
        for v, notes in p.items():
            role = WINDS8_ROLE[v]
            if roles is None or role in roles:
                add(role, notes, art_name, off=off + (-3 if v.endswith('2') else 0))
        return p

    def unison(t, d, pc_name, off=0.0):
        """Every section on one pitch class, in octaves (Beethoven's unison blow)."""
        pc = voicing.N(pc_name + '4') % 12
        oct_ = {'violins1': (5, 6), 'violins2': (4, 5), 'violas': (3, 4), 'cellos': (2, 3), 'basses': (1, 2),
                'flutes': (5, 6), 'oboes': (5,), 'clarinets': (4, 5), 'bassoons': (2, 3), 'horns': (3, 4),
                'trumpets': (4, 5)}
        for role, octs in oct_.items():
            ns = [(t, d, 12 * (o_ + 1) + pc) for o_ in octs]
            if role == 'trumpets' and pc not in (0, 7, 4):
                continue
            add(role, ns, 'marcato', off=off)
        if pc in TIMP:
            add('timpani', [(t, d, TIMP[pc])], 'roll', off=off)

    def solo(track, spec, t0, family, section, vel_rng, seed, **kw):
        notes = sc.line(spec)
        clip = Clip([(a, d, p, 80) for a, d, p in notes], length=voicing.length(spec))
        perf = hornist.arrange(clip, s.tempo_at(float(t0)), family=family, style='classical', section=section,
                               vel=vel_rng, seed=seed, at=float(t0), **kw)
        perf.place(track, float(t0))
        return perf

    performances = {}

    # ================================================================================== INTRODUCTION
    t0 = float(intro.start)
    unison(t0, 2, 'C')
    intro_h = tl(sc.INTRO, t0)
    wind_chords(sc.INTRO[:3], t0, off=0)                                    # winds pp: Ab, Db/F, G7/F
    vln = mel(sc.INTRO_VIOLIN, t0)
    add('violins1', [n for n in vln if n[0] < t0 + 24], off=8)
    low = under(sc.INTRO[3:9], t0 + 8, vln)
    add('violins2', low['violins2'], off=-2)
    add('violas', low['violas'], off=-2)
    add('cellos', low['cellos'], off=0)
    add('basses', window(low['cellos'], t0 + 12, t0 + 24), off=-4, transpose=-12)
    add('bassoons', mel(sc.INTRO_BASSOON, t0), off=4)
    unison(t0 + 24, 2, 'Ab')
    wind_chords(sc.INTRO[11:15], t0 + 26, off=0)                            # Db pp, Fm/Ab, the German sixth
    low = voiced(sc.INTRO[13:15], t0 + 28, STRINGS_UNDER, tie=True)
    for r in ('violins2', 'violas', 'cellos'):
        add(r, low[r], off=-4)
    # the dominant pedal: basses and cellos tremble on G, the timpani roll, horns, the violins and the flute climb
    ped = t0 + 32
    add('basses', [(ped, 8, 31)], 'tremolo', off=-2)
    add('cellos', [(ped, 8, 43)], 'tremolo', off=-2)
    add('timpani', [(ped, 7.5, 43)], 'roll', off=-6)
    add('horns', [(ped, 8, 55), (ped, 8, 67)], off=-6)
    add('violins1', window(vln, ped, ped + 8), off=4)
    add('flutes', mel(sc.INTRO_FLUTE, t0), off=0)
    pad = under(sc.INTRO[15:], ped, window(vln, ped, ped + 8))
    add('violins2', pad['violins2'], 'tremolo', off=-4)
    add('violas', pad['violas'], 'tremolo', off=-4)
    wind_chords(sc.INTRO[15:], ped, off=-6, roles=('oboes', 'clarinets', 'bassoons'))
    brass(intro_h, [ped + 4], length=4, horns=False, timpani=False, art_name='sustain')

    # ================================================================================== EXPOSITION
    # t1: the first theme p in the strings, the 8th-note drive in the inner strings
    t0 = float(t1.start)
    m = mel(sc.T1_MEL, t0)
    add('violins1', m, off=10, dur_f=0.92)
    acc = under(sc.T1, t0, m)
    add('violins2', pulse(acc['violins2']), 'staccato', off=-4, accent=False)
    add('violas', pulse(acc['violas']), 'staccato', off=-6, accent=False)
    add('cellos', beats_of(acc['cellos'], gap=0.7), 'staccato', off=0)
    add('basses', beats_of(acc['cellos'], every=2, gap=1.2), off=-2, transpose=-12)
    h = tl(sc.T1, t0)
    wind_chords(sc.T1[11:14], t0 + 24, off=-6, roles=('oboes', 'clarinets', 'bassoons'))
    brass(h, [t0 + 28], length=2, trumpets=False)

    # t1ff: the counterstatement, ff tutti
    sec = S['t1ff']
    t0 = float(sec.start)
    m = mel(sc.T1FF_MEL, t0)
    h = tl(sc.T1FF, t0)
    tp = tutti(sc.T1FF, t0)
    sync = [t0 + x for x in (0.5, 4.5, 8.5, 12.5, 16.5, 18.5, 20.5, 22.5)]   # the cell's off-beat long notes
    add('violins1', m, off=4, dur_f=0.92, transpose=12, sf=sync)
    add('violins2', m, off=2, dur_f=0.92, sf=sync)
    add('flutes', m, off=0, transpose=12, dur_f=0.9)
    add('oboes', m, off=-2, dur_f=0.9)
    add('violas', pulse(tp['v5']), 'staccato', off=-2, accent=False)
    add('cellos', pulse(tp['v7']), 'staccato', off=0, accent=False)
    add('basses', beats_of(tp['v8'], gap=0.7), 'staccato', off=0)
    add('bassoons', beats_of(tp['v7'], gap=0.7), 'staccato', off=-2)
    add('clarinets', tp['v4'], off=-6, dur_f=0.9)
    stabs = [t0 + x for x in sc.T1FF_STABS] + [t0 + 28, t0 + 29.5, t0 + 30]
    tutti_hits(tp, stabs, length=0.7, off=4, sf=True)
    brass(h, [t0 + b for b in range(0, 28, 4)] + stabs, length=0.7)
    brass(h, [t0 + 24], length=2, timpani=False)

    # trans: syncopated sforzandi, the cell in the basses, the hemiola, the Bb pedal with the horn call
    sec = S['trans']
    t0 = float(sec.start)
    h = tl(sc.TRANS, t0)
    st = voiced(sc.TRANS[:8], t0, voicing.STRINGS, tie=True)
    for r, off in (('violins1', 6), ('violins2', 4), ('violas', 2)):
        add(r, syncopes(st[r]), 'marcato', off=off, accent=False)
    add('cellos', beats_of(window(st['cellos'], t0, t0 + 16), gap=0.75), 'staccato', off=2)
    add('basses', beats_of(window(st['cellos'], t0, t0 + 16), gap=0.75), 'staccato', off=0, transpose=-12)
    cell_b = mel(sc.TRANS_BASS_CELL, t0)
    add('cellos', cell_b, off=8, sf=[n[0] for n in cell_b if n[1] == 1 and abs((n[0] - t0) % 1 - 0.5) < 1e-6])
    add('basses', cell_b, off=4, transpose=-12)
    add('bassoons', cell_b, off=4)
    wind_chords(sc.TRANS[:8], t0, off=-4, roles=('flutes', 'oboes', 'clarinets'))
    brass(h, [t0 + b for b in range(0, 32, 4)], length=3.5, timpani=False, off=-6)
    brass(h, [t0 + b + 1 for b in range(0, 32, 2)], length=0.6, horns=False, off=-2)   # sforzandi on the weak beats
    hem = sc.TRANS[8:14]
    tp = tutti(hem, t0 + 32)
    hem_t = [t0 + 32 + x for x in (0, 3, 6, 8, 11, 14)]
    hem_len = [3, 3, 2, 3, 3, 2]
    for t, L in zip(hem_t, hem_len):
        tutti_hits(tp, [t], length=L - 0.25, off=6, sf=True)
    brass(h, hem_t, length=1.5, off=4)
    # the Bb pedal: the strings tremble pp, the horn calls, the clarinets echo
    ped = voiced(sc.TRANS[14:], t0 + 48, STRINGS_UNDER, key='Eb major', tie=True)
    add('violins2', ped['violins2'], 'tremolo', off=-2)
    add('violas', ped['violas'], 'tremolo', off=-2)
    add('cellos', [(t0 + 48, 16, sc.N('Bb2'))], off=0)
    add('basses', [(t0 + 48, 16, sc.N('Bb1'))], off=-2)
    performances['call1'] = solo(horn, sc.HORN_CALL_EB, t0 + 48, 'trumpet', 'verse', (62, 92), 31,
                                 vib_ct=0.0, peak_vib_ct=4.0)
    add('clarinets', mel(sc.CLAR_ECHO_EB, t0 + 56), off=0)

    # t2: the second theme - the solo clarinet, then violins I + flute; the cell's rhythm in the cellos
    sec = S['t2']
    t0 = float(sec.start)
    h = tl(sc.T2, t0)
    m1 = mel(sc.T2_MEL1, t0)
    performances['t2_clar'] = solo(clar, sc.T2_MEL1, t0, 'clarinet', 'verse', (52, 92), 41)
    pad = under(sc.T2[:12], t0, m1, key='Eb major')
    add('violins2', pad['violins2'], off=-6)
    add('violas', pad['violas'], off=-6)
    add('cellos', beats_of(window(pad['cellos'], t0, t0 + 32), every=2, gap=0.6), 'pizzicato', off=6)
    add('basses', beats_of(window(pad['cellos'], t0, t0 + 32), every=4, gap=0.6), 'pizzicato', off=4,
        transpose=-12)
    add('bassoons', window(pad['cellos'], t0 + 16, t0 + 32), off=-6)
    m2 = mel(sc.T2_MEL2, t0 + 32)
    add('violins1', m2, off=8, dur_f=0.95)
    add('flutes', m2, off=0, transpose=12, dur_f=0.95)
    acc = under(sc.T2[12:], t0 + 32, m2, key='Eb major')
    add('violins2', pulse(acc['violins2'], gap=0.45), 'staccato', off=-8, accent=False)
    add('violas', pulse(acc['violas'], gap=0.45), 'staccato', off=-8, accent=False)
    cc = mel(sc.T2_CELLO_CELL, t0)
    add('cellos', cc, off=2)
    add('cellos', window(acc['cellos'], t0 + 48, t0 + 64), off=-2)
    add('basses', beats_of(window(acc['cellos'], t0 + 32, t0 + 64), every=2, gap=0.6), 'pizzicato', off=4,
        transpose=-12)
    wind_chords(sc.T2[18:], t0 + 48, off=-4, roles=('oboes', 'clarinets', 'bassoons'), key='Eb major')
    brass(h, [t0 + 56, t0 + 60], length=3.5, trumpets=False, timpani=False, off=-10)

    # closing: the cell in major ff, the weak-beat sforzandi, the hemiola cadence, the codetta, two blows
    sec = S['closing']
    t0 = float(sec.start)
    h = tl(sc.CLOSING, t0)
    m = mel(sc.CLOSING_MEL, t0)
    tp = tutti(sc.CLOSING, t0, key='Eb major')
    add('violins1', m, off=4, transpose=12, dur_f=0.92)
    add('violins2', m, off=2, dur_f=0.92)
    add('flutes', m, off=0, transpose=12)
    add('oboes', m, off=-2)
    add('violas', pulse(window(tp['v5'], t0, t0 + 16)), 'staccato', off=-2, accent=False)
    add('cellos', pulse(window(tp['v7'], t0, t0 + 16)), 'staccato', off=0, accent=False)
    add('basses', beats_of(window(tp['v8'], t0, t0 + 16), gap=0.7), 'staccato', off=0)
    add('bassoons', beats_of(window(tp['v7'], t0, t0 + 16), gap=0.7), 'staccato', off=-2)
    weak = [t0 + b + o_ for b in range(0, 16, 4) for o_ in (1, 3)]
    tutti_hits(tp, weak, length=0.6, off=2, roles=('clarinets', 'bassoons'), sf=True)
    brass(h, weak, length=0.6, off=2)
    hem_t = [t0 + 16 + x for x in (0, 3, 6, 8, 10, 12)]
    hem_len = [3, 3, 2, 2, 2, 4]
    for t, L in zip(hem_t, hem_len):
        tutti_hits(tp, [t], length=L - 0.25, off=6, sf=True)
    brass(h, hem_t, length=1.5, off=4)
    cb = mel(sc.CLOSING_BASS_CELL, t0)
    add('cellos', cb, off=6)
    add('basses', cb, off=2, transpose=-12)
    cod = voiced(sc.CLOSING[10:13], t0 + 32, STRINGS_UNDER, key='Eb major', tie=True)
    add('violins2', cod['violins2'], off=-8)
    add('violas', cod['violas'], off=-8)
    ans = mel(sc.CLOSING_WIND_ANSWER, t0)
    add('oboes', ans, off=4)
    add('flutes', ans, off=0, transpose=12)
    tutti_hits(tp, [t0 + 44], length=1.6, off=6, sf=True)              # one blow, then the silence
    brass(h, [t0 + 44], length=1.6, off=6)

    # ================================================================================== DEVELOPMENT
    # dev1: the cell through falling thirds, tossed between winds (tonic) and violins (dominant)
    sec = S['dev1']
    t0 = float(sec.start)
    h = tl(sc.DEV1, t0)
    st = voiced(sc.DEV1, t0, STRINGS_UNDER, tie=True)
    for k, ps in enumerate(sc.DEV1_CELLS):
        a = t0 + 4 * k
        q = [sc.N(x) for x in ps]
        if k < 8:
            if k % 2 == 0:                       # the cell on the key's tonic: the winds
                c = sc.cell(*q, a)
                add('oboes', c, off=10, sf=[a + 0.5])
                add('clarinets', c, off=6, transpose=-12, sf=[a + 0.5])
                if k >= 6:
                    add('flutes', c, off=4, transpose=12)
                add('violins1', window(st['violins1'], a, a + 4), 'tremolo', off=-10)
            else:                                # the answer on its dominant: the violins (inverted in Fm / Db)
                if 4 <= k < 8:
                    c = sc.cell(q[1], q[0], q[0] + (q[1] - q[2]), q[0] + (q[1] - q[3]), a)
                else:
                    c = sc.cell(*q, a)
                add('violins1', c, off=8, sf=[a + 0.5])
                add('violins2', c, off=4, transpose=-12, sf=[a + 0.5])
        else:                                    # fragmentation: half-bar heads tossed every 2 beats
            frag = [(a, 0.5, q[0]), (a + 0.5, 1.0, q[1]), (a + 1.5, 0.5, q[2])]
            echo = [(x + 2, d, p_) for x, d, p_ in frag]
            add('oboes', frag, off=10, sf=[a + 0.5])
            add('flutes', frag, off=6, transpose=12, sf=[a + 0.5])
            add('violins1', echo, off=8, sf=[a + 2.5])
            add('violins2', echo, off=4, transpose=-12, sf=[a + 2.5])
    add('violas', [n for n in st['violas']], 'tremolo', off=-6)
    add('violins2', [n for n in st['violins2'] if int((n[0] - t0) // 4) % 2 == 0], 'tremolo', off=-8)
    add('cellos', beats_of(st['cellos'], gap=0.8), 'staccato', off=0)
    add('basses', beats_of(st['cellos'], every=2, gap=1.5), off=-2, transpose=-12)
    add('bassoons', st['cellos'], off=-6)
    brass(h, [t0 + 4 * k for k in range(12)], length=3.5, off=-6, timpani=False)
    brass(h, [t0 + 4 * k + 0.5 for k in range(12)], length=0.6, horns=False, off=-2)

    # fugato: the subject in F minor, entries cellos - violas - violins II - violins I, free counterpoint voiced
    sec = S['fugato']
    t0 = float(sec.start)
    order = ('violins1', 'violins2', 'violas', 'cellos')
    fixed = {v: [] for v in order}
    harm = []
    for role, at_, shift in sc.FUGATO_ENTRIES:
        fixed[role] += sc.line(sc.SUBJECT, t0 + at_, shift)
        for a, d, sym in sc.SUBJECT_H:
            harm.append((t0 + at_ + a, d, _tr(sym, shift)))
    entry = {role: t0 + at_ for role, at_, _ in sc.FUGATO_ENTRIES}
    steps = []
    for a, d, sym in harm:
        active = [v for v in order if entry[v] <= a + 1e-6]
        fx_ = {}
        for v in active:
            for n in fixed[v]:
                if n[0] - 1e-6 <= a < n[0] + n[1] - 1e-6:
                    fx_[v] = n[2]
        avoid = {n[2] for v in active for n in fixed[v] if a - 1e-6 <= n[0] < a + d - 1e-6}
        steps.append({'chord': sym, 'fixed': fx_, 'active': active, 'avoid': avoid})
    vo = voicing.voice(steps, voices=STRINGS_UNDER, key='F minor')
    fg = {v: [] for v in order}
    for v in order:
        fg[v] = [(n[0], n[1], n[2]) for n in fixed[v]]
    free = set()
    for (a, d, sym), stp, vc in zip(harm, steps, vo):
        for v in stp['active']:
            if v in stp['fixed']:
                continue
            p = vc[v]
            last = fg[v][-1] if fg[v] else None
            if last and last[2] == p and abs(last[0] + last[1] - a) < 1e-6 and (v, round(last[0], 4)) in free:
                fg[v][-1] = (last[0], last[1] + d, p)
            else:
                fg[v].append((a, d, p))
                free.add((v, round(a, 4)))
    for v in order:
        fg[v].sort()

    def fkey(t):
        k = 'F minor' if (t // 16) % 2 == 0 else 'C minor'
        kk = Key(k)
        pcs = {p % 12 for p in kk.notes(60, 71)}
        return pcs, kk.tonic, (kk.tonic - 1) % 12
    voicing.arpeggiate(fg, free, [(a - t0, d, c) for a, d, c in harm], t0, voices=STRINGS_UNDER)
    voicing.passing_eighths(fg, free, t0, fkey, order=order)
    DEBUG['fugato'] = (fg, harm, voicing.check(fg, harm, voices=STRINGS_UNDER, order=order))

    def lead_off(v):
        return lambda n: 0

    for v in order:
        subj = {(round(n[0], 4)) for n in fixed[v]}
        notes = []
        for n in fg[v]:
            notes.append((n[0], n[1], n[2], vel(n[0], 8 if round(n[0], 4) in subj else -4)))
        add(v, notes, off=0, dur_f=0.94)
    add('basses', [(n[0], n[1], n[2] - 12, vel(n[0], -8)) for n in fg['cellos'] if n[1] >= 1 - 1e-6], dur_f=0.94)
    def subj(shift, a):
        return [(n[0], n[1], n[2], vel(n[0], -6)) for n in sc.line(sc.SUBJECT, a, shift)]

    # the winds double the ENTERING subject (violins II's, then violins I's), never a free voice
    add('bassoons', subj(12, t0 + 32), dur_f=0.94)
    add('clarinets', subj(12 + sc.ANSWER_SHIFT, t0 + 48), dur_f=0.94)
    add('oboes', subj(12 + sc.ANSWER_SHIFT, t0 + 48), dur_f=0.94)
    add('horns', [(t0 + 48, 8, sc.N('F3')), (t0 + 48, 8, sc.N('C4')), (t0 + 56, 8, sc.N('G3')),
                  (t0 + 56, 8, sc.N('C4'))], off=-10)
    add('timpani', [(t0 + 60, 4, 48)], 'roll', off=-14)

    # storm: hammered syncopated tutti into Gb, subito pp the second theme in Gb, the German sixth
    sec = S['storm']
    t0 = float(sec.start)
    h = tl(sc.DEV3, t0)
    tp = tutti(sc.DEV3[:4], t0, key='Db major')
    for r in ('violins1', 'violins2', 'violas'):
        vs = TUTTI_ROLE[r]
        add(r, syncopes([n for v in vs for n in tp[v]]), 'marcato', off=6, accent=False)
    add('cellos', pulse(tp['v7'], gap=0.4), 'staccato', off=2, accent=False)
    add('basses', pulse(tp['v8'], gap=0.4), 'staccato', off=0, accent=False)
    tutti_hits(tp, [t0 + b + o_ for b in range(0, 16, 4) for o_ in (1, 3)], length=0.6, off=4,
               roles=('flutes', 'oboes', 'clarinets', 'bassoons'), sf=True)
    brass(h, [t0 + b + o_ for b in range(0, 16, 4) for o_ in (1, 3)], length=0.6, off=4, timpani=False)
    quiet = under(sc.DEV3[4:], t0 + 16, mel(sc.DEV3_CLAR, t0) + mel(sc.DEV3_FLUTE, t0), key='Gb major')
    add('violins2', quiet['violins2'], off=-4)
    add('violas', quiet['violas'], off=-4)
    add('cellos', quiet['cellos'], off=-2)
    add('basses', window(quiet['cellos'], t0 + 24, t0 + 32), off=-4, transpose=-12)
    performances['storm_clar'] = solo(clar, sc.DEV3_CLAR.replace('r:16 | ', ''), t0 + 16, 'clarinet', 'verse',
                                      (36, 66), 43)
    add('flutes', mel(sc.DEV3_FLUTE, t0), off=8)

    # pedal: the dominant pedal on G, the cell climbing in imitation, the long crescendo
    sec = S['pedal']
    t0 = float(sec.start)
    h = tl(sc.DEV4, t0)
    add('basses', pulse([(t0, 62, 31)], gap=0.45), 'staccato', off=-2, accent=False)
    # the crescendo is played: every held part re-attacks each bar (a new bow, a new breath) at the map's rising level
    add('timpani', [(t0 + 32 + 4 * i, 4 if i < 7 else 1.5, 43) for i in range(8)], 'roll', off=-8)
    add('horns', [(t0 + 16 + 4 * i, 3.9, p) for i in range(11) for p in (55, 67)] + [(t0 + 60, 2, 55), (t0 + 60, 2, 67)],
        off=-8)
    pd = voiced(sc.DEV4[:-1], t0, STRINGS_UNDER, tie=False)
    add('violas', pd['violas'], 'tremolo', off=-6)
    add('violins2', window(pd['violins2'], t0 + 32, t0 + 62), 'tremolo', off=-8)
    add('cellos', pulse([(t0 + 4, 58, 43)], gap=0.45), 'staccato', off=-4, accent=False)
    wind_chords(sc.DEV4[8:-1], t0 + 32, off=-8, roles=('clarinets', 'bassoons', 'oboes'), tie=False)
    cmin = [0, 2, 3, 5, 7, 8, 11]

    def pcell(k):
        sym = chord_at(h, t0 + 4 * k + 0.01)
        top = sc.N(sc.DEV4[k][2])
        ci = voicing.info(sym)
        p1 = next((top - i for i in (8, 9, 7, 10) if (top - i) % 12 in ci.pcs), top - 7)
        dn = [q for q in range(top - 1, top - 6, -1) if q % 12 in cmin]
        return p1, top, dn[0], dn[1]

    def fit(role, shift, top):
        if role in ('cellos', 'violas') and top + shift > 70:
            shift -= 12
        return shift - 12 if top + shift > 96 else shift

    second = ('oboes', 'violins2', 'flutes', 'violins1')
    frag_roles = ('violins1', 'flutes', 'oboes', 'violins2')
    for k, (role, shift) in enumerate(sc.DEV4_IMITATION):
        a = t0 + 4 * k
        p1, top, p3, p4 = pcell(k)
        if k < 8:                                   # one entry per bar, rising through the orchestra
            add(role, sc.cell(p1, top, p3, p4, a, fit(role, shift, top)), off=10, sf=[a + 0.5])
        elif k < 12:                                # stretto: a second entry on beat 3 overlaps the first
            add(role, sc.cell(p1, top, p3, p4, a, fit(role, shift, top)), off=10, sf=[a + 0.5])
            r2 = second[k - 8]
            add(r2, sc.cell(p1, top, p3, p4, a + 2, fit(r2, 12 if r2 in ('flutes',) else 0, top)), off=8,
                sf=[a + 2.5])
        elif k < 15:                                # one-beat heads (the leap alone), tossed every beat
            for j in range(4):
                r = frag_roles[j]
                sh = fit(r, 12 if r == 'flutes' else 0, top)
                add(r, [(a + j, 0.5, p1 + sh), (a + j + 0.5, 0.45, top + sh)], 'marcato', off=8,
                    accent=False)
    hits = [t0 + 60, t0 + 60.5, t0 + 61, t0 + 61.5]
    tp = tutti(sc.DEV4[-2:-1], t0 + 60)
    tutti_hits(tp, [t0 + 60, t0 + 61], length=0.4, off=8, sf=True)
    brass(h, [t0 + 60, t0 + 61], length=0.4, off=8)

    # ================================================================================== RECAPITULATION
    # rec1: the first theme ff tutti, the half cadence held
    sec = rec1
    t0 = float(sec.start)
    m = mel(sc.REC1_MEL, t0)
    h = tl(sc.REC1, t0)
    tp = tutti(sc.REC1, t0)
    sync = [t0 + x for x in (0.5, 4.5, 8.5, 12.5, 16.5, 18.5, 20.5, 22.5)]
    add('violins1', m, off=4, dur_f=0.92, transpose=12, sf=sync)
    add('violins2', m, off=2, dur_f=0.92, sf=sync)
    add('flutes', m, off=0, transpose=12, dur_f=0.9)
    add('oboes', m, off=-2, dur_f=0.9)
    add('clarinets', m, off=-4, dur_f=0.9, transpose=-12)
    add('violas', pulse(window(tp['v5'], t0, t0 + 28)), 'staccato', off=-2, accent=False)
    add('cellos', pulse(window(tp['v7'], t0, t0 + 28)), 'staccato', off=0, accent=False)
    add('basses', beats_of(window(tp['v8'], t0, t0 + 28), gap=0.7), 'staccato', off=0)
    add('bassoons', beats_of(window(tp['v7'], t0, t0 + 28), gap=0.7), 'staccato', off=-2)
    tutti_hits(tp, [t0 + x for x in sc.T1FF_STABS], length=0.7, off=4, sf=True)
    brass(h, [t0 + b for b in range(0, 28, 4)] + [t0 + x for x in sc.T1FF_STABS], length=0.7)
    tutti_hits(tp, [t0 + 28], length=1.9, off=0)
    brass(h, [t0 + 28], length=1.9, roll=True)

    # cadenza: the oboe alone over a held G7, pp
    t0 = float(cad.start)
    hold = voiced(sc.CADENZA, t0, STRINGS_UNDER, tie=True)
    for r in ('violins2', 'violas', 'cellos'):
        add(r, hold[r], off=-14)
    add('basses', [(t0, 4, 31)], off=-14)
    performances['cadenza'] = solo(oboe, sc.OBOE_CADENZA, t0, 'clarinet', 'verse', (42, 96), 51,
                                   vib_ct=8.0, peak_vib_ct=14.0)

    # rec2: the transition to G - syncopes, the hemiola, the horn call on G and its echo
    sec = rec2
    t0 = float(sec.start)
    h = tl(sc.REC2, t0)
    st = voiced(sc.REC2[:4], t0, voicing.STRINGS, tie=True)
    for r, off in (('violins1', 6), ('violins2', 4), ('violas', 2)):
        add(r, syncopes(st[r]), 'marcato', off=off, accent=False)
    add('cellos', beats_of(st['cellos'], gap=0.75), 'staccato', off=2)
    add('basses', beats_of(st['cellos'], gap=0.75), 'staccato', off=0, transpose=-12)
    wind_chords(sc.REC2[:4], t0, off=-4, roles=('flutes', 'oboes', 'clarinets', 'bassoons'))
    brass(h, [t0 + b + 1 for b in range(0, 16, 2)], length=0.6, horns=False, off=-2)
    tp = tutti(sc.REC2[4:10], t0 + 16, key='C major')
    hem_t = [t0 + 16 + x for x in (0, 3, 6, 8, 11, 14)]
    for t, L in zip(hem_t, [3, 3, 2, 3, 3, 2]):
        tutti_hits(tp, [t], length=L - 0.25, off=6, sf=True)
    brass(h, hem_t, length=1.5, off=4)
    ped = voiced(sc.REC2[10:], t0 + 32, STRINGS_UNDER, key='C major', tie=True)
    add('violins2', ped['violins2'], 'tremolo', off=-2)
    add('violas', ped['violas'], 'tremolo', off=-2)
    add('cellos', [(t0 + 32, 16, sc.N('G2'))], off=0)
    add('basses', [(t0 + 32, 16, sc.N('G1'))], off=-2)
    performances['call2'] = solo(horn, sc.HORN_CALL_C, t0 + 32, 'trumpet', 'verse', (62, 92), 33,
                                 vib_ct=0.0, peak_vib_ct=4.0)
    add('clarinets', mel(sc.CLAR_ECHO_C, t0 + 40), off=0)

    # rec3: the second theme in C major - violins I, then flute + oboe in octaves
    sec = S['rec3']
    t0 = float(sec.start)
    h = tl(sc.REC3, t0)
    m1 = mel(sc.REC3_MEL1, t0, -3)
    add('violins1', m1, off=6, dur_f=0.96)
    pad = under(sc.REC3[:12], t0, m1, key='C major')
    add('violins2', pad['violins2'], off=-8)
    add('violas', pad['violas'], off=-8)
    add('cellos', beats_of(window(pad['cellos'], t0, t0 + 32), every=2, gap=0.6), 'pizzicato', off=6)
    add('basses', beats_of(window(pad['cellos'], t0, t0 + 32), every=4, gap=0.6), 'pizzicato', off=4,
        transpose=-12)
    add('horns', [(t0 + 16, 16, sc.N('G3')), (t0 + 16, 16, sc.N('C4'))], off=-14)
    m2 = mel(sc.REC3_MEL2, t0 + 32, -3)
    add('flutes', m2, off=4, transpose=12, dur_f=0.95)
    add('oboes', m2, off=2, dur_f=0.95)
    add('clarinets', m2, off=-4, dur_f=0.95, transpose=-12)
    acc = under(sc.REC3[12:], t0 + 32, [(n[0], n[1], n[2] + 12) for n in m2], key='C major')
    add('violins1', pulse(acc['violins2'], gap=0.45), 'staccato', off=-10, accent=False)
    add('violas', pulse(acc['violas'], gap=0.45), 'staccato', off=-10, accent=False)
    add('cellos', mel(sc.REC3_CELLO_CELL, t0, -3), off=2)
    add('cellos', window(acc['cellos'], t0 + 48, t0 + 64), off=-2)
    add('basses', beats_of(window(acc['cellos'], t0 + 32, t0 + 64), every=2, gap=0.6), 'pizzicato', off=4,
        transpose=-12)
    brass(h, [t0 + 56, t0 + 60], length=3.5, trumpets=False, timpani=False, off=-10)

    # rec4: the closing in C major, the codetta - and G7 breaks into Ab
    sec = S['rec4']
    t0 = float(sec.start)
    h = tl(sc.REC4, t0)
    m = mel(sc.REC4_MEL, t0, -3)
    tp = tutti(sc.REC4, t0, key='C major')
    add('violins1', m, off=4, transpose=12, dur_f=0.92)
    add('violins2', m, off=2, dur_f=0.92)
    add('flutes', m, off=0, transpose=12)
    add('oboes', m, off=-2)
    add('violas', pulse(window(tp['v5'], t0, t0 + 16)), 'staccato', off=-2, accent=False)
    add('cellos', pulse(window(tp['v7'], t0, t0 + 16)), 'staccato', off=0, accent=False)
    add('basses', beats_of(window(tp['v8'], t0, t0 + 16), gap=0.7), 'staccato', off=0)
    add('bassoons', beats_of(window(tp['v7'], t0, t0 + 16), gap=0.7), 'staccato', off=-2)
    weak = [t0 + b + o_ for b in range(0, 16, 4) for o_ in (1, 3)]
    tutti_hits(tp, weak, length=0.6, off=2, roles=('clarinets', 'bassoons'), sf=True)
    brass(h, weak, length=0.6, off=2)
    hem_t = [t0 + 16 + x for x in (0, 3, 6, 8, 10, 12)]
    for t, L in zip(hem_t, [3, 3, 2, 2, 2, 4]):
        tutti_hits(tp, [t], length=L - 0.25, off=6, sf=True)
    brass(h, hem_t, length=1.5, off=4)
    cb = mel(sc.REC4_BASS_CELL, t0)
    add('cellos', cb, off=6)
    add('basses', cb, off=2, transpose=-12)
    cod = voiced(sc.REC4[10:13], t0 + 32, STRINGS_UNDER, key='C major', tie=True)
    for r in ('violins2', 'violas'):
        add(r, cod[r], 'tremolo', off=-6)
    add('violins1', window(cod['violins2'], t0 + 40, t0 + 44), 'tremolo', off=-4, transpose=12)
    tutti_hits(tp, [t0 + 44], length=3.5, off=8, sf=True)
    brass(h, [t0 + 40], length=3.5, off=-2, roll=True)
    brass(h, [t0 + 44], length=3.5, off=8, timpani=False)

    # ================================================================================== CODA
    # coda1: the second development - the Neapolitan, subito p, the chromatic climb
    sec = S['coda1']
    t0 = float(sec.start)
    h = tl(sc.CODA1, t0)
    st = voiced(sc.CODA1, t0, STRINGS_UNDER, tie=True)
    for k, ps in enumerate(sc.CODA1_CELLS):
        a = t0 + 4 * k
        c = sc.cell(*ps, a)
        if k < 4:
            role, sh = ('oboes', 0) if k % 2 == 0 else ('violins1', 12)
            add(role, c, off=6, sf=[a + 0.5], transpose=sh)
            add('clarinets' if k % 2 == 0 else 'violins2', c, off=0, sf=[a + 0.5])
        else:
            add('violins1', c, off=8)
            if k >= 6:
                add('flutes', c, off=-2, transpose=12)
    add('violas', st['violas'], 'tremolo', off=-6)
    add('violins2', window(st['violins2'], t0 + 16, t0 + 64), 'tremolo', off=-6)
    add('violins1', window(st['violins1'], t0 + 32, t0 + 64), 'tremolo', off=-2)
    add('cellos', beats_of(window(st['cellos'], t0, t0 + 32), gap=0.8), 'staccato', off=0)
    add('cellos', window(st['cellos'], t0 + 32, t0 + 64), off=4)
    add('basses', [(n[0], n[1], n[2]) for n in st['cellos']], off=0, transpose=-12)
    add('bassoons', window(st['cellos'], t0 + 32, t0 + 64), off=-2)
    wind_chords(sc.CODA1[8:], t0 + 32, off=-6, roles=('flutes', 'oboes', 'clarinets'))
    brass(h, [t0 + 4 * k for k in range(4)], length=3.5, off=-4, timpani=False)
    brass(h, [t0 + 48, t0 + 52], length=3.5, off=-4, timpani=False)
    add('timpani', [(t0 + 56, 8, 43)], 'roll', off=-6)
    add('trumpets', [(t0 + 56, 4, 67), (t0 + 60, 4, 67), (t0 + 56, 4, 72)], off=-8)

    # coda2: the triumph - the cell in C major ff, then the horn call hammered out over a tonic pedal
    sec = S['coda2']
    t0 = float(sec.start)
    m = mel(sc.CODA2_MEL, t0)
    h = tl(sc.CODA2, t0)
    tp = tutti(sc.CODA2, t0, key='C major')
    sync = [t0 + x for x in (0.5, 4.5, 8.5, 12.5, 16.5, 20.5)]
    add('violins1', m, off=4, dur_f=0.92, transpose=12, sf=sync)
    add('violins2', m, off=2, dur_f=0.92, sf=sync)
    add('flutes', m, off=0, transpose=12, dur_f=0.9)
    add('oboes', m, off=-2, dur_f=0.9)
    add('clarinets', m, off=-2, dur_f=0.9)
    # new colours for the triumph: the horns, cellos and bassoons sing the theme an octave under the violins II,
    # the natural trumpets take its C / E / G notes, the flutes ride an octave above the violins I
    head = window(m, t0, t0 + 16)
    add('horns', head, off=-2, transpose=-12, dur_f=0.9)
    add('cellos', head, off=2, transpose=-12, dur_f=0.92, sf=sync)
    add('bassoons', head, off=0, transpose=-12, dur_f=0.92)
    add('trumpets', [n for n in m if n[2] % 12 in (0, 4, 7) and 60 <= n[2] <= 79 and n[1] >= 0.5], 'marcato',
        off=-2, dur_f=0.85)
    add('violas', pulse(window(tp['v5'], t0, t0 + 32)), 'staccato', off=-2, accent=False)
    add('cellos', pulse(window(tp['v7'], t0 + 16, t0 + 32)), 'staccato', off=-4, accent=False)
    add('basses', beats_of(window(tp['v8'], t0, t0 + 32), gap=0.7), 'staccato', off=0)
    add('bassoons', beats_of(window(tp['v7'], t0 + 16, t0 + 32), gap=0.7), 'staccato', off=-2)
    tutti_hits(tp, [t0 + x for x in sc.T1FF_STABS] + [t0 + 30], length=0.7, off=4, sf=True)
    brass(h, [t0 + b for b in range(0, 32, 4) if b != 24] + [t0 + x for x in sc.T1FF_STABS], length=0.7,
          horns=False, trumpets=False)
    call = mel(sc.CODA2_HORNS, t0)
    add('horns', call, 'marcato', off=4)
    add('horns', [(n[0], n[1], n[2] + 12) for n in call if n[2] + 12 <= 77], off=0)
    add('trumpets', [(n[0], n[1], n[2] + 12) for n in call if n[2] + 12 in TP_NATURAL], 'marcato', off=0)
    tr = window(tp['v1'], t0 + 32, t0 + 48)
    for r, vs in (('violins1', ('v1', 'v2')), ('violins2', ('v3', 'v4')), ('violas', ('v5', 'v6'))):
        add(r, [n for v in vs for n in window(tp[v], t0 + 32, t0 + 48)], 'tremolo', off=0)
    add('cellos', pulse(window(tp['v7'], t0 + 32, t0 + 48)), 'staccato', off=2, accent=False)
    add('basses', pulse(window(tp['v8'], t0 + 32, t0 + 48)), 'staccato', off=0, accent=False)
    wind_chords(sc.CODA2[15:], t0 + 32, off=0, roles=('flutes', 'oboes', 'clarinets', 'bassoons'), key='C major')
    add('timpani', [(t0 + 32, 7.5, 48), (t0 + 40, 3.5, 43), (t0 + 44, 3.5, 48)], 'roll', off=-8)

    # coda3: the hammered tonic chords, the last held in unison
    t0 = float(coda3.start)
    h = tl(sc.CODA3, t0)
    tp = tutti(sc.CODA3[:-2], t0, key='C major')
    hits = [a for a, d, c in h if a < t0 + 24]
    for a, d, c in h:
        if a >= t0 + 24:
            break
        tutti_hits(tp, [a], length=min(d, 2) * 0.85, off=6, sf=True)
    brass(h, hits, length=0.8, off=6)
    last = t0 + 24
    unison(last, 6, 'C', off=4)
    add('trumpets', [(last, 6, 67), (last, 6, 72)], off=0)
    add('violins2', [(last, 6, 67)], off=-2)
    add('violas', [(last, 6, 55)], off=-2)

    # ------------------------------------------------------------------------------------------ perform
    DEBUG.update(parts=parts, song=s, performances=performances)
    fallback = {'marcato': 'sustain', 'tremolo': 'sustain', 'pizzicato': 'staccato', 'spiccato': 'staccato'}
    for role, notes in parts.items():
        have = set(o.info['articulations'].get(role) or ())
        groups: dict = {}
        lo_, hi_ = (sc.N(x) for x in o.info['range'][role])
        for st_, du, p, v, a in notes:
            while p > hi_:                                  # an octave double above the instrument folds down
                p -= 12
            while p < lo_:
                p += 12
            if have and a not in have:
                a = fallback.get(a, 'sustain')
            groups.setdefault(a, []).append((st_, du, p, v))
        clip = None
        for a, ns in groups.items():
            c = art.articulate(Clip(ns, length=0), a)
            clip = c if clip is None else clip | c
        orch.perform(o, role, clip, 0, articulations=None, seed=sum(map(ord, role)))

    # the hall rings on the fermatas and gives the bloom back where the music goes on
    orch.ring(o, intro.start + 1, length=1, db=3, back=intro.start + 2.75, back_beats=0.5)
    orch.ring(o, rec1.bar(7) + 0.5, length=1.5, db=3, back=cad.start, back_beats=0.5)
    orch.ring(o, coda3.bar(6) + 2, length=4, db=4)
    # the conductor's arc (the mix engineer, MIX.md): section rides on the master input, before the limiter - the
    # soft passages up (they sat at -31..-41 LUFS: too soft for a phone), the earlier fortissimos a little under the
    # coda, so the triumph is the loudest moment
    s.master.add_fx(fx.utility(gain=0.0, name='arc'), first=True)
    ride = {'t1': 3.5, 'trans': -1.0, 't2': 1.0, 'closing': -2.5, 'storm': -1.5, 'pedal': 0.0, 'rec1': -0.5,
            'cadenza': 1.5, 'rec3': 3.0, 'rec4': -2.0, 'coda1': 0.5, 'coda2': 1.0, 'coda3': 1.0, 't1ff': -1.0,
            'fugato': 6.0}
    pts = [(0.0, -1.5), (S['intro'].start + 2, -1.5), (S['intro'].start + 2.5, 3.0, 'smooth'),
           (S['intro'].bar(6) - 0.25, 3.0), (S['intro'].bar(6), -1.5, 'smooth'), (S['intro'].bar(6) + 2, -1.5),
           (S['intro'].bar(6) + 2.5, 3.0, 'smooth'), (S['intro'].bar(9), 1.0, 'smooth')]
    for name, _ in SECTIONS[1:]:
        g = ride.get(name, 0.0)
        a = float(S[name].start)
        pts += [(a - 0.5, pts[-1][1]), (a, g, 'smooth')]
        if name == 'pedal':                                    # pp at the start of the pedal, the crescendo is ours
            pts += [(a + 0.5, 3.0, 'smooth'), (a + 16, 2.5, 'smooth'), (a + 32, 1.5, 'smooth'),
                    (a + 48, 0.0, 'smooth')]
        if name == 'fugato':                                   # the first entries alone, then the counterpoint fills
            pts += [(a + 8, 6.0), (a + 16, 4.5, 'smooth'), (a + 48, 0.0, 'smooth')]
        if name in ('closing', 'rec4'):                        # the codetta is soft: not pulled down with the ff
            back = 0.0 if name == 'rec4' else -2.5
            pts += [(a + 31.5, g), (a + 32, 1.5, 'smooth'), (a + 43.5, 1.5 if name == 'closing' else 0.5),
                    (a + 44, back, 'smooth')]
        if name == 'coda1':                                    # subito p, then the climb
            pts += [(a + 15.5, 0.5), (a + 16, 2.5, 'smooth'), (a + 40, 2.0), (a + 60, 0.5, 'smooth')]
        if name == 'trans':                                    # the hemiola leads, the horn call's pedal is soft
            pts += [(a + 31.5, 0.0), (a + 32, 0.5, 'smooth'), (a + 47.5, 0.5), (a + 48, 2.0, 'smooth')]
    s.master.automate('fx.arc.gain', sorted(pts, key=lambda p: p[0]))
    # master (the mastering engineer, MASTER.md): `agentsound master --platform dynamic` on the finished mix, profile
    # classical: broad tone only (the SSO sections read boxy around 1.6 kHz and light in the lows), the safety
    # limiter, -19.5 LUFS-I (the middle of the concert window), true peak <= -1 dBTP
    mastering.apply(s, eq={'low.freq': 100, 'low.gain': 3.0, 'low.q': 0.7071, 'high.freq': 8000, 'high.gain': 1.2,
                           'high.q': 0.7071, 'peak1.freq': 1600, 'peak1.gain': -2.8, 'peak1.q': 0.7},
                    limiter={'ceiling': -1.2, 'release': 250.0}, loudness_change=-1.4)
    return s


def _tr(sym: str, semis: int) -> str:
    return sym if not semis % 12 else chord(sym).transpose(semis).symbol
