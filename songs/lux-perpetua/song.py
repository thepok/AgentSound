"""Lux Perpetua - an original Requiem movement-cycle in D minor in the idiom of Mozart's Requiem K. 626 (1791).
Build: python -m agentsound build songs/lux-perpetua

No note is Mozart's: the harmony, tunes, fugue subject and countersubject are written for this piece (score.py);
the idiom is his: the syncopated string pulse of an Introitus over a chromatic lament bass, a double-subject fugue,
a Dies irae storm (tremolo, running 16ths, natural trumpets and timpani on D / A, trombones doubling the choir), a
solo tenor trombone call, a 12/8 Lacrimosa of sighing violins and a chromatically rising choir, a plagal Amen with a
Picardy third. Two gestures are homages to K. 626 (public domain): the Lacrimosa's chromatic soprano climb over a
falling bass and the Tuba's rising Bb-major trombone arpeggio. Late-Classical orchestra as Mozart scored it: strings,
basset horns (clarinets in their low register), bassoons, trumpets, trombones (alto / tenor / bass doubling the
choir), timpani D / A, organ continuo, SATB choir (sampled "ah" / "oh", no text).

  I    intro      6  4/4 q=56  D minor   the violins' offbeat pulse (mp-mf, on top) over D-C#-C-B-Bb-A, bassoon then
                                         basset-horn sighs, the Neapolitan (a tenuto), A7 crescendo, a timpani roll
       requiem   10            D -> F -> D the choir enters f voice by voice (B T A S a beat apart on 'Re-qui-em') with
                                         trombones, trumpets and timpani, subito p; 'lux' in F major (f), the
                                         Neapolitan turns back, the lament bass under a held D, 4-3 onto A (fermata)
  II   kyrie     19  4/4 q=88  D minor   fugue: subject B - tonal answer T - subject A - answer S (countersubject each,
                                         the entering voice on top), episode over a walking bass (circle of fifths),
                                         middle entry in F major, the last entries with trombones and timpani, Adagio
                                         cadence iv6 - N6 - V7 onto a bare fifth
  III  dies       8  4/4 q=144 D -> F    the storm, f: the choir declaims (syllables, not a vowel pad), 16th violins,
                                         tremolo; the trumpets hold back, then dotted figures on D / A
       tremor     8                      subito pp: trembling repeated chords over F-F#-G-G#-A, crescendo into the
                                         dominant pedal, deceptive Bb, the Neapolitan
       ira        8                      the climax, ff: violins in octaves, trumpet fanfares, a timpani roll into the
                                         cadence, hammered chords, a hush on a low D tremolo
  IV   tuba       8  4/4 q=72  Bb major  the solo tenor trombone's call, the low voices ('oh') answer it, trombone
                                         above, turning to A7 (fermata)
  V    lacrimosa  8  12/8 q.=48 D minor  sighing violins (mp, never on a pitch the choir sings), the soprano's lament
                                         swelling phrase by phrase over the 'oh' choir, the chromatic climb over a
                                         falling bass to the forte climax ('ah', trombones, timpani)
       amen       4                      plagal Amen (leaning into each plagal chord), the Neapolitan, the Picardy
                                         third blooming: D major under a fermata

Sound: bands.symphony_orchestra (SSO 4.0 sections in the Musikverein IR) without the instruments Mozart left out
(flutes, oboes, horns, tuba, harp, celesta, percussion); the 'clarinets' role plays the basset horns; organ
sampled/chamber_organ (Burea choir organ) as a continuo (the bass line, a light right hand in the soft chorales);
choir sampled/choir_mixed ('ah', one track per voice) and sampled/choir_oh ('oh': the lament's lower voices, the Amen
and the men's unison in the Tuba); sampled/solo_trombone (played by the hornist). Profile 'classical': a concert work
with a 15 LU dynamic range. Mix (MIX.md): seated as Mozart's orchestra (antiphonal violins, the choir S A T B behind
it from left to right), the choir in front of its colla-parte doubling, the figures (pulse, sighs, 16ths, trumpets)
heard. Master (MASTER.md): platform 'dynamic', a broad tonal eq and the safety limiter, no glue.

Measured (report, 'classical'): -19.5 LUFS-I, LRA 15.1 LU, PLR 18.3, TP -1.2 dBTP, 0 warnings, 0 clicks in the mix
(13 masked loop seams, low). Per section: intro -28.1, requiem -21.2, kyrie -20.1, dies -14.4, tremor -16.8, ira
-12.6 (the climax), tuba -25.2, lacrimosa -22.8, amen -22.0 LUFS. Reverb -11.1 LU, width >150 Hz 37 %, balance vs the
reference: lowmid +2.6, mid +2.4, presence +1.4, brilliance -3.9, air -6.9 dB.

CREDITS: Sonatina Symphonic Orchestra 4.0 (Mattias Westlund, Peter Eastman; CC Sampling Plus 1.0), Virtual Playing
Orchestra 3 (Paul Battersby), VSCO 2 CE (Versilian Studios, CC0), No Budget Orchestra 2 (CC-BY-SA 4.0: the 'oh'
choir), Burea Church choir organ sample set by Lars Palo (CC-BY-SA 2.5), Voxengo IM Reverbs (Musikvereinsaal).
"""
import random

from agentsound import *
from agentsound import articulation as art
from agentsound import bands, hornist, mastering, patches
from agentsound.bandlib import orchestra as orch
from agentsound.humanize import touch

import score as sc

ANALYSIS = {'profile': 'classical'}
METADATA = {'title': 'Lux Perpetua', 'artist': 'AgentSound', 'album': 'Sacred', 'genre': 'Classical',
            'comment': 'Requiem in D minor: Introitus - Kyrie - Dies irae - Tuba - Lacrimosa - Amen'}
COVER = {'style': 'classical', 'palette': 'noir', 'title': 'LUX PERPETUA', 'subtitle': 'Requiem in D minor'}

# ---------------------------------------------------------------------------------------------- mix (MIX.md)
# Seating, audience view (pan -1 = left): Mozart's orchestra with antiphonal violins - I left, II right; violas and
# cellos centre-right, basses behind them on the right; basset horns / bassoons centre behind the strings; trumpets
# with the timpani at the back left, the trombones back right beside the lower voices they double; the organ centre
# back; the choir behind the orchestra S A T B from left to right, each voice narrowed to 80 % so it keeps its seat
# (the chorus samples are recorded ~95 % wide: every voice spread over the whole stage).
SEATING = {
    'pan': {'violins2': 0.5, 'trumpets': -0.25, 'timpani': -0.2, 'trombones': 0.28,
            'choir_s': -0.7, 'choir_a': -0.33, 'choir_t': 0.6, 'choir_b': 0.65},
    'width': {'choir_s': 0.8, 'choir_a': 0.8, 'choir_t': 0.8, 'choir_b': 0.8},
}
_STRINGS = ('violins1', 'violins2', 'violas', 'cellos', 'basses')
_SATB = ('choir_s', 'choir_a', 'choir_t', 'choir_b')
# Balance by the score (dB): the choir is the lead of every sung section (it was treated as a bed: 2.6-4.9 dB under
# the orchestra in the Requiem, Kyrie and Dies irae); the fugue's voices sit on top of their colla-parte strings; the
# sighs of the Introitus (basset horns, bassoons) over the string pulse.
MIX = {
    'trim': {'choir_s': 6.3, 'choir_a': 5.0, 'choir_t': 6.1, 'choir_b': 5.8, 'choir_oh': 1.0,
             'violas': -1.5, 'cellos': 1.5, 'basses': 2.0, 'trombones': -2.0, 'basset_horns': -1.0, 'organ': -6.0},
    'ride': {**{v: {'requiem': 3.0, 'kyrie': 3.0, 'dies': 4.0, 'tremor': 2.5, 'ira': 3.5} for v in _SATB},
             'choir_s': {'requiem': 3.0, 'kyrie': 3.0, 'dies': 4.0, 'tremor': 2.5, 'ira': 3.5, 'lacrimosa': 3.5},
             'choir_oh': {'tuba': 1.0, 'lacrimosa': 0.5, 'amen': 2.5},
             'violins1': {'intro': 3.5, 'requiem': 5.0, 'kyrie': -1.0, 'dies': 0.0, 'ira': 0.5, 'lacrimosa': 2.5},
             'violins2': {'intro': 5.5, 'requiem': 5.5, 'kyrie': -1.0, 'dies': -1.0, 'lacrimosa': 2.5},
             'violas': {'intro': 1.5, 'requiem': 1.5, 'kyrie': -1.0},
             'cellos': {'intro': -3.0, 'kyrie': -2.0}, 'basses': {'intro': -2.0, 'kyrie': -2.0},
             'trumpets': {'dies': 2.0, 'ira': 1.0},
             'basset_horns': {'intro': 2.5, 'dies': -2.0}},
    'eq': {'choir_s': [{'freq': 600, 'gain': -3.0, 'q': 0.6}, {'freq': 3200, 'gain': 1.5, 'q': 1.0}],
           'choir_a': [{'freq': 600, 'gain': -3.0, 'q': 0.6}, {'freq': 3200, 'gain': 1.0, 'q': 1.0},
                       {'freq': 1500, 'gain': -2.5, 'q': 1.0}],
           **{v: [{'freq': 600, 'gain': -3.0, 'q': 0.6}, {'freq': 3200, 'gain': -0.5, 'q': 1.0},
                  {'freq': 300, 'gain': -1.5, 'q': 1.0}] for v in ('choir_t', 'choir_b')},
           'choir_oh': [{'freq': 600, 'gain': -2.0, 'q': 0.7}],
           'violins1': [{'freq': 3500, 'gain': -1.5, 'q': 1.0}, {'freq': 10000, 'gain': 1.5, 'q': 0.7},
                        {'freq': 1200, 'gain': -1.0, 'q': 1.0}],
           'violins2': [{'freq': 10000, 'gain': 1.5, 'q': 0.7}],
           'trumpets': [{'freq': 1500, 'gain': -2.5, 'q': 1.0}],
           'violas': [{'freq': 400, 'gain': -1.5, 'q': 1.0}],
           'cellos': [{'freq': 400, 'gain': -1.5, 'q': 1.0}, {'freq': 120, 'gain': 1.0, 'q': 0.8}],
           'basses': [{'freq': 90, 'gain': 1.5, 'q': 0.8}],
           'bassoons': [{'freq': 350, 'gain': -1.5, 'q': 1.0}],
           'trombones': [{'freq': 1000, 'gain': -1.5, 'q': 0.8}],
           'organ': [{'freq': 300, 'gain': -2.0, 'q': 1.0}],
           'hall': [{'freq': 650, 'gain': -2.5, 'q': 0.6}, {'freq': 8000, 'gain': 2.0, 'q': 0.5},
                    {'freq': 1600, 'gain': -1.5, 'q': 0.8}]},
}

SPEAK = 116              # the choir sings at a speaking velocity; its dynamics live on the 'dynamics' lane
CHOIR_PAN = {'S': -0.38, 'A': -0.14, 'T': 0.14, 'B': 0.38}   # the sound designer's; SEATING re-seats the voices
DEBUG: dict = {}           # the written parts and the harmony (for checks outside the build)
STRINGS_RANGE = {'S': (62, 84), 'A': (55, 76), 'T': (48, 69), 'B': (36, 62)}


def build() -> Song:
    s = Song('Lux Perpetua', tempo=56, key='D minor', seed=626, tail=9)
    intro = s.section('intro', bars=6)
    req = s.section('requiem', bars=10)
    kyrie = s.section('kyrie', bars=19)
    dies = s.section('dies', bars=8)
    tremor = s.section('tremor', bars=8)
    ira = s.section('ira', bars=8)
    tuba = s.section('tuba', bars=8)
    lacr = s.section('lacrimosa', bars=8, meter=(12, 8))
    amen = s.section('amen', bars=4, meter=(12, 8))

    # ------------------------------------------------------------------------------------------ tempo
    # the phrases breathe (+-5.5 %: they move on and broaden into their ends), a small tenuto on each Neapolitan
    s.rubato((intro.start, intro.bar(4)), depth=0.055, phrase='breath')
    s.fermata(intro.bar(4) + 2, hold=0.35, length=2)                     # Eb/G, the Neapolitan
    s.rubato((req.start, req.bar(4)), depth=0.05, phrase='arch')
    s.rubato((req.bar(4), req.bar(6)), depth=0.055, phrase='breath')
    s.fermata(req.bar(6) + 2, hold=0.35, length=2)                       # Eb/G
    s.rubato((req.bar(7), req.bar(9)), depth=0.055, phrase='breath')
    s.ritardando((req.bar(9), req.bar(9) + 2), to=0.78, a_tempo=False)
    s.fermata(req.bar(9) + 2, hold=2.5, length=2)
    s.set_tempo(kyrie, 88)
    s.ritardando((kyrie.bar(16) + 2, kyrie.bar(18)), to=0.55, a_tempo=False)
    s.fermata(kyrie.bar(18), hold=3, length=4)
    s.set_tempo(dies, 144)
    s.set_tempo(tuba, 72)
    s.rubato((tuba.start, tuba.bar(4)), depth=0.055, phrase='breath')
    s.rubato((tuba.bar(4), tuba.bar(7)), depth=0.05, phrase='breath')
    s.ritardando((tuba.bar(7), tuba.bar(7) + 2), to=0.85, a_tempo=False)
    s.fermata(tuba.bar(7) + 2, hold=2.5, length=2)
    s.set_tempo(lacr, 72)
    s.rubato((lacr.start, lacr.bar(4)), depth=0.055, phrase='breath')
    s.rubato((lacr.bar(4), lacr.bar(8)), depth=0.05, phrase='arch')
    s.fermata(amen.bar(1), hold=0.4, length=1.5)                          # Eb/G
    s.ritardando((amen.bar(2), amen.bar(3)), to=0.72, a_tempo=False)
    s.fermata(amen.bar(3), hold=4, length=6)

    # ------------------------------------------------------------------------------------------ the ensemble
    o = bands.symphony_orchestra(s, without=('flutes', 'oboes', 'horns', 'tuba', 'percussion', 'harp', 'celesta'),
                                 ids={'clarinets': 'basset_horns'})
    hall = o.buses['hall']
    # the hall's air: the return is opened to 20 kHz and lifted above 9 kHz (the sections and the choir are dark)
    hall.automate('fx.convolver.highcut', [(0, 20000.0)])
    hall.add_fx(fx.eq({'high.freq': 9000, 'high.gain': 2.5, 'high.q': 0.7071}))
    # the winds get a seat in the room: a short stereo early-reflection insert (the SSO bassoons are mono)
    for role in ('bassoons', 'clarinets'):
        o[role].add_fx(fx.convolver(ir='samples/voxengo-im-reverbs/Musikvereinsaal.wav', mix=0.22, length=0.12,
                                    predelay=6, lowcut=180, width=1.6))
    # the intro's low mids: the low strings and winds dip 4 dB at 300 Hz under the violins' pulse, then open
    for role in ('cellos', 'violas', 'bassoons', 'clarinets'):
        o[role].add_fx(fx.eq({'peak1.freq': 300, 'peak1.gain': -4.0, 'peak1.q': 0.9}, name='intro_dip'))
        o[role].automate('fx.intro_dip.peak1.gain', [(req.start - 1, -4.0), (req.start, 0.0, 'smooth')])
    organ = s.track('organ', 'sampled/chamber_organ', pan=-0.05, gain_db=-4.0, sends={hall: -12},
                    fx=[fx.eq({'peak1.freq': 350, 'peak1.gain': -3.0, 'peak1.q': 0.8})])
    # the choir's box cut at the source (380 Hz, 600 Hz, 1.1 kHz)
    ah = {v: s.track(f'choir_{v.lower()}', patches.get('sampled/choir_mixed').but(start=60), pan=CHOIR_PAN[v],
                     gain_db=-12.0, fx=[fx.eq({'peak1.freq': 380, 'peak1.gain': -3.0, 'peak1.q': 0.8,
                                              'peak2.freq': 1100, 'peak2.gain': -2.0, 'peak2.q': 0.8,
                                              'peak3.freq': 600, 'peak3.gain': -2.5, 'peak3.q': 1.0})],
                     sends={hall: -3})
          for v in sc.ORDER}
    oh = s.track('choir_oh', 'sampled/choir_oh', pan=0.0, gain_db=-9.5, sends={hall: -3},
                 fx=[fx.eq({'peak1.freq': 380, 'peak1.gain': -2.5, 'peak1.q': 0.8,
                            'peak2.freq': 600, 'peak2.gain': -2.5, 'peak2.q': 1.0})])
    tbn = s.track('trombone_solo', 'sampled/solo_trombone', pan=0.3, gain_db=-5.0, sends={hall: -7},
                  fx=[fx.eq({'peak2.freq': 1000, 'peak2.gain': -2.0, 'peak2.q': 0.8})])

    # ------------------------------------------------------------------------------------------ dynamics map
    # one curve for the whole piece (velocity 40 = p, 78 = mf, 95 = f, 115 = ff): (beat, velocity[, 'step'])
    # The arc holds back: the Kyrie closes f, the Dies irae is f, the tremor's crescendo stops short of the ira,
    # which alone is ff (the climax).
    K = []

    def dmap(sec, pts):
        a = float(sec.start)
        for p in pts:
            K.append((a + p[0], p[1]) + tuple(p[2:]))

    dmap(intro, [(0, 56), (8, 64), (12, 70), (16, 60), (20, 66), (23.8, 96)])
    dmap(req, [(0, 98), (7.9, 100), (8, 56, 'step'), (12, 60), (15.9, 70), (16, 88, 'step'), (23.9, 92),
               (24, 58, 'step'), (28, 54), (32, 62), (36, 52), (40, 40)])
    dmap(kyrie, [(0, 64), (8, 68), (16, 74), (24, 80), (32, 76), (40, 80), (47.9, 84), (48, 92, 'step'),
                 (56, 98), (64, 104), (68, 108), (72, 108), (76, 100)])
    dmap(dies, [(0, 110), (15.9, 108), (16, 108), (31.9, 114)])
    dmap(tremor, [(0, 34, 'step'), (15.9, 58), (16, 80, 'step'), (24, 106), (32, 110)])
    dmap(ira, [(0, 122), (16, 124), (24, 118), (25, 40, 'step'), (32, 28)])
    dmap(tuba, [(0, 60), (8, 64), (16, 52), (24, 60), (29.9, 56), (32, 44)])
    dmap(lacr, [(0, 50), (12, 54), (18, 58), (24, 56), (35.9, 100), (36, 106), (42, 80), (48, 64)])
    dmap(amen, [(0, 60), (6, 68), (12, 64), (15, 78), (18, 70), (24, 46)])
    K.sort(key=lambda p: (p[0], len(p)))

    def dyn(t: float) -> float:
        prev = K[0]
        for p in K:
            if p[0] > t:
                if len(p) == 3:                    # a subito change: hold until it
                    return prev[1]
                span = p[0] - prev[0]
                return prev[1] + (p[1] - prev[1]) * ((t - prev[0]) / span if span > 0 else 1.0)
            prev = p
        return prev[1]

    rnd = random.Random(626)

    def vel(t: float, off: float = 0.0, accent: bool = True) -> int:
        v = dyn(t) + off + rnd.uniform(-3, 3)
        if accent:
            ph = _phase(t)
            if ph < 0.02:
                v += 5
            elif abs(ph - 0.5) < 0.02:
                v += 2
        return max(12, min(127, round(v)))

    def _phase(t: float) -> float:
        """Position inside the bar, 0..1."""
        for sec in s.sections:
            if sec.start - 1e-6 <= t < sec.end - 1e-6:
                bl = sec.beats_per_bar
                return ((t - sec.start) % bl) / bl
        return 0.0

    # ------------------------------------------------------------------------------------------ part buffers
    parts: dict = {}          # role / track id -> [(start, dur, pitch, vel, articulation)]

    def shape(notes, k):
        """Phrasing: humanize.touch's phrase arcs (rise to the phrase's goal, relax after it, higher notes sing out,
        passing notes lighter) as an offset of k x (touch - 60) velocity steps on top of the dynamics map."""
        if len(notes) < 3 or not k:
            return lambda n: 0.0
        shaped = touch(Clip([(n[0], n[1], n[2], 80) for n in notes], length=0), 40, 80, gap='1/4')
        by = {(round(m.start, 4), m.pitch): m.vel for m in shaped}
        return lambda n: k * (by.get((round(n[0], 4), n[2]), 60) - 60)

    MELODIC = {'violins1': 0.9, 'violins2': 0.9, 'violas': 0.5, 'cellos': 0.5, 'trombones': 0.8, 'clarinets': 0.7,
               'bassoons': 0.5, 'basses': 0.4}

    def add(role, notes, art_name='sustain', off=0.0, accent=True, dur_f=1.0, transpose=0, offs=None):
        buf = parts.setdefault(role, [])
        arc = shape(notes, MELODIC.get(role, 0.0))
        for n in notes:
            st, du, p = n[0], n[1], n[2]
            o = off + (offs(n) if offs else 0.0)
            v = n[3] if len(n) > 3 else min(127, max(12, round(vel(st, o, accent) + arc(n))))
            buf.append((st, du * dur_f, p + transpose, v, art_name))

    sung: dict = {}           # choir track -> [(start, dur, pitch, written velocity)]
    voices: dict = {v: [] for v in sc.ORDER}      # the four voices as written, whatever track sings them
    expr: dict = {}           # choir track -> expression points (entry lifts, syllable gaps, phrase swells)

    def sing(key, notes, off=0.0, dur_f=1.0, voice=None, offs=None):
        buf = sung.setdefault(key, [])
        arc = shape(notes, 0.7)
        for n in notes:
            o = off + (offs(n) if offs else 0.0)
            v = min(127, max(12, round(vel(n[0], o, accent=True) + arc(n))))
            d = n[1] * (dur_f(n) if callable(dur_f) else dur_f)
            buf.append((n[0], d, n[2], v))
            voices[voice or key].append((n[0], d, n[2], v))

    def window(notes, a, b):
        return [n for n in notes if a - 1e-6 <= n[0] < b - 1e-6]

    def at(notes, t0):
        return [(n[0] + t0,) + tuple(n[1:]) for n in notes]

    def offbeats(notes, gap=0.42):
        """Offbeat 8ths on the notes' pitches (the Introitus pulse)."""
        out = []
        for st, du, p in notes:
            k = st + 0.5
            while k < st + du - 1e-6:
                out.append((k, gap, p))
                k += 1.0
        return out

    def beats(notes, gap=0.8, step=1.0):
        out = []
        for st, du, p in notes:
            k = st
            while k < st + du - 1e-6:
                out.append((k, min(gap, st + du - k), p))
                k += step
        return out

    def voices_of(ch, *vs):
        return [n for v in vs for n in ch.get(v, [])]

    def sounding(notes, t):
        return [n[2] for n in notes if n[0] - 1e-6 <= t < n[0] + n[1] - 1e-6]

    organ_notes = []          # the continuo: the bass line, a light right hand in the soft chorales

    def continuo(bass, rh=(), soft=()):
        """The organ: the bass line throughout (tasto solo), the right hand (rh notes) only inside the soft spans."""
        organ_notes.extend((a, d, p) for a, d, p in bass)
        for a, d, p in rh:
            if any(x - 1e-6 <= a < y - 1e-6 for x, y in soft):
                organ_notes.append((a, d, p))

    # ================================================================================== I. INTROITUS
    t0 = float(intro.start)
    st_intro = sc.chorale(sc.INTRO, t0, ranges=STRINGS_RANGE)
    # the pulse is the figure: violins mp-mf staccato over the chords, the low strings detached quarters under it
    add('violins1', offbeats(st_intro['S']), 'staccato', off=24)
    add('violins2', offbeats(st_intro['A']), 'staccato', off=22)
    add('violas', beats(st_intro['T'], gap=0.6), off=-4)
    add('cellos', beats(st_intro['B'], gap=0.7), off=-2)
    add('basses', beats(window(st_intro['B'], t0 + 8, t0 + 24), gap=0.7), off=-2, transpose=-12)
    add('bassoons', sc.line(sc.INTRO_BASSOON, t0), off=6)
    add('bassoons', window(st_intro['T'], t0 + 16, t0 + 24), off=-6)
    add('clarinets', sc.line(sc.INTRO_BASSET1, t0) + sc.line(sc.INTRO_BASSET2, t0), off=4)
    add('timpani', [(t0 + 20, 4, sc.N('A2'), 50)], 'roll')

    # requiem: the choir enters voice by voice (B T A S, a beat apart, each on 'Re-qui-em'), f, then subito p
    t0 = float(req.start)
    ch = sc.chorale(sc.REQUIEM, t0, tie=True)
    ch['S'] = sc.line(sc.REQUIEM_SOPRANO, t0)
    for v in sc.ORDER:
        body = []
        for a, d, p in ch[v]:
            if a + d <= t0 + 4 + 1e-6:
                continue
            if a < t0 + 4:
                a, d = t0 + 4, a + d - (t0 + 4)
            body.append((a, d, p))
        ch[v] = sc.line(sc.REQUIEM_ENTRY[v], t0) + body
    for v in sc.ORDER:
        sing(v, ch[v], off={'S': 2, 'A': -3, 'T': -2, 'B': 0}[v])
    st_req = sc.chorale(sc.REQUIEM, t0, ranges=STRINGS_RANGE)
    vn1 = window(st_req['S'], t0, t0 + 4) + [n for n in ch['S'] if n[0] >= t0 + 4 - 1e-6]
    vn2 = window(st_req['A'], t0, t0 + 4) + [n for n in ch['A'] if n[0] >= t0 + 4 - 1e-6]
    add('violins1', offbeats(vn1), 'staccato', off=24)             # the pulse follows the voices it doubles
    add('violins2', offbeats(vn2), 'staccato', off=22)
    add('violas', beats(st_req['T'], gap=0.6), off=-4)
    add('cellos', beats(st_req['B'], gap=0.7), off=-2)
    add('basses', beats(st_req['B'], gap=0.7), off=-4, transpose=-12)
    trb_spans = [(t0, t0 + 8), (t0 + 16, t0 + 28)]
    for a, b in trb_spans:
        add('trombones', window(voices_of(ch, 'A', 'T', 'B'), a, b), off=-12)
    for a, b in ((t0 + 8, t0 + 16), (t0 + 28, t0 + 40)):
        add('clarinets', window(voices_of(ch, 'A', 'T'), a, b), off=-6)
    add('bassoons', ch['B'], off=-8)
    add('trumpets', [(t0, 0.9, sc.N('D4')), (t0, 0.9, sc.N('D5'))], 'marcato', off=-2)
    add('trumpets', [(t0 + 16, 0.9, sc.N('A4'))], off=-10)
    add('timpani', [(t0, 1.5, sc.N('D3'), 100), (t0 + 16, 1.0, sc.N('A2'), 80)], 'hit')
    add('timpani', [(t0 + 36, 4, sc.N('A2'), 46)], 'roll')
    soft_req = [(t0 + 8, t0 + 16), (t0 + 24, t0 + 40)]
    continuo(ch['B'], voices_of(sc.chorale(sc.REQUIEM, t0, tie=True), 'A', 'T'), soft_req)

    # ================================================================================== II. KYRIE (fugue)
    t0 = float(kyrie.start)
    fixed = sc.KYRIE_FIXED
    steps = []
    for st, du, sym in sc.KYRIE_HARMONY:
        active = [v for v in sc.ORDER if sc.KYRIE_ENTRY[v] <= st]
        fx_ = {}
        for v in active:
            if st >= 72:
                fx_[v] = sc.N(sc.KYRIE_FINAL[v])
                continue
            for n in fixed[v]:
                if n[0] - 1e-6 <= st < n[0] + n[1] - 1e-6:
                    fx_[v] = n[2]
        avoid = {n[2] for v in active for n in fixed[v] if st - 1e-6 <= n[0] < st + du - 1e-6 and st < 72}
        steps.append({'chord': sym, 'fixed': fx_, 'active': active, 'lt': sc.KYRIE_LT.get(int(st), 1),
                      'avoid': avoid})
    voiced = sc.satb(steps)
    ky = {v: [] for v in sc.ORDER}
    for v in sc.ORDER:
        for n in fixed[v]:
            if n[0] < 72:
                ky[v].append((n[0] + t0, n[1], n[2]))
    free_notes = set()
    for (st, du, sym), stp, vc in zip(sc.KYRIE_HARMONY, steps, voiced):
        for v in stp['active']:
            if v in stp['fixed'] and st < 72:
                continue
            p = vc[v]
            last = ky[v][-1] if ky[v] else None
            if last and last[2] == p and abs(last[0] + last[1] - (st + t0)) < 1e-6 and st < 72 \
                    and (v, round(last[0], 4)) in free_notes:
                ky[v][-1] = (last[0], last[1] + du, p)
            else:
                ky[v].append((st + t0, du, p))
                free_notes.add((v, round(st + t0, 4)))
    for v in sc.ORDER:
        ky[v].sort()
    # counterpoint for the free voices: passing 8ths into the next harmony note (a third away), where they make no
    # parallels and rub no semitone against another voice
    kyrie_passing = (sc.arpeggiate(ky, free_notes, sc.KYRIE_HARMONY, t0)
                     + sc.passing_eighths(ky, free_notes, t0))
    # each entering voice leads for its first two bars (a level above the others, which drop back)
    EMPH = [('B', 0, 8), ('T', 8, 16), ('A', 16, 24), ('S', 24, 32), ('A', 32, 36), ('S', 36, 40), ('T', 40, 44),
            ('S', 44, 48), ('T', 48, 56), ('B', 56, 64), ('A', 60, 68)]

    def lead_state(v, t):
        on = [w for w, a, b in EMPH if t0 + a - 1e-6 <= t < t0 + b - 1e-6]
        return 1 if v in on else (-1 if on else 0)

    def ky_off(v):
        return lambda n: {1: 8, -1: -6, 0: 0}[lead_state(v, n[0])]

    for v in sc.ORDER:
        sing(v, ky[v], off={'S': 0, 'A': -2, 'T': -1, 'B': 1}[v], dur_f=0.97, offs=ky_off(v))
        bounds = sorted({t0 + a for _, a, b in EMPH} | {t0 + b for _, a, b in EMPH})
        pts = [(t0 - 0.5, 1.0)]
        level = {1: 1.0, -1: 0.8, 0: 1.0}
        for i, b in enumerate(bounds):
            x = level[lead_state(v, b + 0.01)]
            pts.append((max(pts[-1][0] + 0.01, b - 0.25), pts[-1][1]))
            pts.append((b, x))
        pts.append((float(kyrie.end) - 0.5, pts[-1][1]))
        pts.append((float(kyrie.end), 1.0))
        expr.setdefault(v, []).extend(pts)
    # colla parte (Mozart's Kyrie: the strings and winds double the voices, the entering voice's doubling in front)
    add('violins1', ky['S'], off=-8, dur_f=0.97, offs=ky_off('S'))
    add('violins2', ky['A'], off=-10, dur_f=0.97, offs=ky_off('A'))
    add('violas', ky['T'], off=-10, dur_f=0.97, offs=ky_off('T'))
    add('cellos', ky['B'], off=-8, dur_f=0.97, offs=ky_off('B'))
    add('basses', ky['B'], off=-10, transpose=-12, dur_f=0.97, offs=ky_off('B'))
    add('bassoons', ky['B'], off=-10, dur_f=0.97, offs=ky_off('B'))
    add('clarinets', window(ky['A'], t0 + 16, t0 + 76), off=-12, dur_f=0.97, offs=ky_off('A'))
    add('trombones', window(voices_of(ky, 'A', 'T', 'B'), t0 + 48, t0 + 76), off=-16, dur_f=0.97)
    tr = [(t0 + 56, 0.9, 'D4'), (t0 + 56, 0.9, 'D5'), (t0 + 60, 0.9, 'D4'), (t0 + 70, 2, 'A4'),
          (t0 + 72, 4, 'D4'), (t0 + 72, 4, 'A4'), (t0 + 72, 4, 'D5')]
    add('trumpets', [(a, d, sc.N(p)) for a, d, p in tr], off=-10)
    add('timpani', [(t0 + 56, 1, sc.N('D3'), 84), (t0 + 60, 1, sc.N('D3'), 78), (t0 + 64, 1, sc.N('A2'), 80)],
        'hit')
    add('timpani', [(t0 + 70, 2, sc.N('A2'), 76), (t0 + 72, 4, sc.N('D3'), 90)], 'roll')
    continuo(ky['B'])                                      # tasto solo: the bass line under the fugue

    # ================================================================================== III. DIES IRAE
    t0 = float(dies.start)
    table = sc.DIES + sc.TREMOR + sc.IRA
    ch = sc.chorale(table, t0)
    tl = sc.timeline(table, t0)
    trem_a, trem_b = float(tremor.start), float(ira.start)

    def declaim(n):
        """Syllables, not a vowel pad: the chords are sung detached, with a real gap before the next word."""
        a, d = n[0], n[1]
        if trem_a <= a < trem_a + 16:
            return 0.55
        return 0.8 if d <= 0.5 else 0.6 if d <= 1 else 0.72 if d <= 2 else 0.85

    for v in sc.ORDER:
        sing(v, ch[v], off={'S': 0, 'A': -2, 'T': -2, 'B': 0}[v], dur_f=declaim)
    storm = [(t0, trem_a), (trem_b, trem_b + 25)]
    # violins I: running 16ths between the soprano and the alto of each chord (the storm), f and on top; violins II
    # repeat the alto in measured 16ths in the Dies irae and double violins I an octave down in the ira (the climax)
    for (a, d, p_s), (_, _, p_a), (_, _, p_t), (_, _, p_b) in zip(ch['S'], ch['A'], ch['T'], ch['B']):
        stormy = any(x <= a < y for x, y in storm)
        if stormy:
            v1, v2 = [], []
            k = 0
            while k < d - 1e-6:
                acc = 10 if abs(k - round(k)) < 1e-6 else -5
                pitch = p_s if int(round(k * 4)) % 2 == 0 else p_a
                v1.append((a + k, 0.22, pitch, vel(a + k, 6 + acc, False)))
                if a >= trem_b:
                    low = pitch - 12 if pitch - 12 >= 55 else pitch
                    v2.append((a + k, 0.22, low, vel(a + k, 2 + acc, False)))
                else:
                    v2.append((a + k, 0.22, p_a, vel(a + k, -2 + 1.3 * acc, False)))
                k += 0.25
            add('violins1', v1, 'staccato', accent=False)
            add('violins2', v2, 'staccato', accent=False)
            add('violas', [(a, d, p_t)], 'tremolo', off=-6)
            add('cellos', beats([(a, d, p_b)], gap=0.4, step=0.5), 'staccato', off=-2, accent=False)
            add('basses', beats([(a, d, p_b)], gap=0.4, step=0.5), 'staccato', off=-4, transpose=-12, accent=False)
        else:   # tremor: everything trembles
            add('violins1', [(a, d, p_s)], 'tremolo', off=-2)
            add('violins2', [(a, d, p_a)], 'tremolo', off=-4)
            add('violas', [(a, d, p_t)], 'tremolo', off=-4)
            add('cellos', [(a, d * 0.6, p_b)], 'staccato', off=0)
            add('basses', [(a, d, p_b - 12)], 'tremolo', off=-4)
    for a, b in storm + [(trem_a + 16, trem_b)]:
        add('trombones', window(voices_of(ch, 'A', 'T', 'B'), a, b), off=-10, dur_f=0.6)
        add('clarinets', window(voices_of(ch, 'A', 'T'), a, b), off=-12, dur_f=0.6)
        add('bassoons', window(ch['B'], a, b), off=-6, dur_f=0.6)
    # natural trumpets (D harmonics: D4 A4 D5) and timpani (D3 / A2): held back in the first phrase, then the dotted
    # figures (dotted 8th, 16th, quarter) on D / A where the chord allows; the ira ff with a timpani roll into its
    # cadence
    D_CH = {'Dm', 'Dm/F', 'Dm/A', 'Bb', 'Gm/Bb', 'Gm'}
    A_CH = {'A', 'A7', 'A7/C#', 'F', 'F/A'}
    roll_in = trem_b + 10
    for a, d, sym in tl:
        if trem_a <= a < trem_a + 16:
            continue
        if sym in D_CH:
            tp, tim = ['D4', 'D5'] if sym.startswith('D') else ['D4'], 'D3'
        elif sym in A_CH:
            tp, tim = ['A4'], 'A2'
        else:
            continue
        if abs(a - roll_in) > 1e-6:
            add('timpani', [(a, 0.5, sc.N(tim), vel(a, 4 if _phase(a) < 0.02 else -14))], 'hit')
        if a < t0 + 16:
            continue
        loud = 10 if a >= trem_b else 4
        for p in tp:
            if d >= 2 - 1e-6:
                fig = [(a, 0.6, sc.N(p), vel(a, loud + 4, False), 'marcato'),
                       (a + 0.75, 0.2, sc.N(p), vel(a, loud - 4, False), 'staccato'),
                       (a + 1.0, min(d - 1.0, 1.0) * 0.85, sc.N(p), vel(a, loud, False), 'marcato')]
            else:
                fig = [(a, min(d * 0.7, 0.8), sc.N(p), vel(a, loud, False), 'marcato')]
            for st_, du_, p_, v_, a_ in fig:
                add('trumpets', [(st_, du_, p_, v_)], a_)
    add('timpani', [(roll_in, 2, sc.N('A2'), 108)], 'roll')
    add('timpani', [(trem_a + 12, 4, sc.N('A2'), 70)], 'roll')
    add('timpani', [(trem_a + 28, 4, sc.N('A2'), 100)], 'roll')
    # the hush after the last hammer blow: a low D trembling pp into the Tuba
    hush = trem_b + 25
    add('cellos', [(hush + 0.5, 6.5, sc.N('D3'))], 'tremolo', off=-2)
    add('basses', [(hush + 0.5, 6.5, sc.N('D2'))], 'tremolo', off=-2)
    add('timpani', [(hush + 0.5, 5, sc.N('D3'), 34)], 'roll')
    continuo([(a, d * 0.85, p) for a, d, p in ch['B']])     # tasto solo in the storm

    # ================================================================================== IV. TUBA
    t0 = float(tuba.start)
    st_tuba = sc.chorale(sc.TUBA, t0, ranges=STRINGS_RANGE, lt=9, tie=True)
    add('violins1', st_tuba['S'], off=-14)
    add('violins2', st_tuba['A'], off=-14)
    add('violas', st_tuba['T'], off=-14)
    add('cellos', st_tuba['B'], off=-10)
    add('basses', window(st_tuba['B'], t0 + 16, t0 + 32), off=-10, transpose=-12)
    add('bassoons', window(st_tuba['T'], t0 + 16, t0 + 32), off=-12)
    continuo(st_tuba['B'], voices_of(st_tuba, 'A', 'T'), [(t0, t0 + 32)])
    call = Clip([(a, d, p, 80) for a, d, p in sc.line(sc.TUBA_TROMBONE)], length=32)
    perf = hornist.arrange(call, s.tempo_at(t0), family='trombone', style='classical', section='verse',
                           peaks=(2, 4, 12, 20), vel=(66, 104), seed=11, at=t0)
    perf.place(tbn, tuba)
    tbn.automate('gainDb', [(tuba.bar(4) - 0.5, 0.0), (tuba.bar(4) + 0.5, -5.0, 'smooth')])   # under the men's answer
    men = at(sc.line(sc.TUBA_MEN), t0)
    sing('oh', men, off=8, voice='B')                             # the men answer (the 'oh' choir loops cleanly)
    expr.setdefault('oh', []).extend(sc.swells(men, t0 + 16, t0 + 32, 8, lo=0.72))

    # ================================================================================== V. LACRIMOSA + AMEN
    t0 = float(lacr.start)
    table = sc.LACRIMOSA + sc.AMEN
    full = sc.chorale(table, t0, tie=False)
    tl = sc.timeline(table, t0)
    choir_from = t0 + 12
    lac = {v: window(full[v], choir_from, t0 + 72) for v in ('A', 'T', 'B')}
    lac['S'] = sc.line(sc.LACRIMOSA_SOPRANO, t0) + sc.line(sc.AMEN_SOPRANO, float(amen.start))
    # tie the lower voices' repeated pitches (sustained under the soprano's lament)
    for v in ('A', 'T', 'B'):
        merged = []
        for n in lac[v]:
            if merged and merged[-1][2] == n[2] and abs(merged[-1][0] + merged[-1][1] - n[0]) < 1e-6:
                merged[-1] = (merged[-1][0], merged[-1][1] + n[1], n[2])
            else:
                merged.append(n)
        lac[v] = merged
    climb, amen_t = t0 + 24, float(amen.start)
    for v in sc.ORDER:
        soft = [n for n in lac[v] if n[0] < climb]
        loud = [n for n in lac[v] if climb <= n[0] < amen_t]
        close = [n for n in lac[v] if n[0] >= amen_t]
        if v == 'S':        # the lament's soprano (up to F5) sings 'ah': the 'oh' samples stop at C#5
            sing('S', soft + loud, off=2)
            sing('oh', close, off=2, voice='S')
        else:
            sing('oh', soft + close, off={'A': -2, 'T': -2, 'B': 0}[v], voice=v)
            sing(v, loud, off={'A': -3, 'T': -2, 'B': 0}[v])
    # the lament breathes: a swell on each 'Lacrimosa' phrase (p < mp > p, ~7 dB), the Amen leans into its plagal
    # chords and blooms into the Picardy third
    expr['oh'].extend(sc.swells(lac['S'], choir_from, climb, 6, lo=0.64))
    expr.setdefault('S', []).extend(sc.swells(lac['S'], choir_from, climb, 6, lo=0.64))
    expr['oh'].extend([(amen_t - 0.5, 1.0), (amen_t, 0.8), (amen_t + 1.5, 1.0, 'smooth'), (amen_t + 3, 0.8, 'smooth'),
                       (amen_t + 4.5, 0.95, 'smooth'), (amen_t + 6, 0.85, 'smooth'), (amen_t + 7.5, 1.0, 'smooth'),
                       (amen_t + 12, 0.8, 'smooth'), (amen_t + 13.5, 0.95, 'smooth'), (amen_t + 15, 0.78, 'smooth'),
                       (amen_t + 16.5, 1.0, 'smooth')])
    # violins: the sighs (8th rest, appoggiatura from the step above, resolution) until the Amen, mp over the p choir
    # and off any pitch the choir sings at that moment
    choir_now = [n for v in sc.ORDER for n in lac[v]]
    scale = [2, 4, 5, 7, 9, 10, 0]

    def above(p, ci):
        """The scale step above p, coloured by the chord (C# on A chords, B on E7, Eb on the Neapolitan ...)."""
        for q in range(p + 1, p + 3):
            pc = q % 12
            alt = {1: 0, 11: 10, 3: 4, 6: 5, 8: 7}                    # chromatic pcs and the diatonic ones they replace
            if pc in ci.pcs and pc in alt:
                return q
            if pc in scale and not any(c in ci.pcs and alt[c] == pc for c in alt):
                return q
        return p + 2

    def rubs(p, t1, t2):
        return any(abs(p - q) % 12 in (1, 11) for t in (t1, t2) for q in sounding(choir_now, t))

    def sigh(a, cands, ci):
        for top in cands:
            app = above(top, ci)
            if not rubs(app, a + 0.5, a + 0.9) and not rubs(top, a + 1.0, a + 1.4):
                return [(a + 0.5, 0.5, app, 5), (a + 1.0, 0.45, top, -4)]
        top = cands[0]
        return [(a + 0.5, 0.95, top, 0)] if not rubs(top, a + 0.5, a + 1.4) else []

    for (a, d, sym), p_s in zip(tl, full['S']):
        if a >= amen_t:
            break
        ci = sc.info(sym)
        tones = sorted(q for q in range(67, 87) if q % 12 in ci.pcs)
        high = [q for q in tones if q >= max(p_s[2] + 3, 74)] or [tones[-1]]
        s1 = sigh(a, high, ci)
        top = s1[-1][2] if s1 else high[0]
        s2 = sigh(a, [q for q in reversed(tones) if q < top - 2], ci)
        add('violins1', [(t, du, p, vel(a, 14 + x, False)) for t, du, p, x in s1])
        add('violins2', [(t, du, p, vel(a, 10 + x, False)) for t, du, p, x in s2])
    add('violins1', window(full['S'], amen_t, amen_t + 24), off=-12)
    add('violins2', window(full['A'], amen_t, amen_t + 24), off=-12)
    add('violas', [(a, d, p) for a, d, p in full['T'] if a < amen_t], off=-14)
    add('violas', window(full['T'], amen_t, amen_t + 24), off=-10)
    add('cellos', [(a, 0.9, p) for a, d, p in full['B'] if a < amen_t], off=-6)
    add('cellos', window(full['B'], amen_t, amen_t + 24), off=-6)
    add('basses', [(a, 0.9, p - 12) for a, d, p in full['B'] if a < climb], 'pizzicato', off=-2)
    add('basses', [(a, 0.9, p - 12) for a, d, p in full['B'] if climb <= a < amen_t], off=-8)
    add('basses', [(a, d, p - 12) for a, d, p in window(full['B'], amen_t, amen_t + 24)], off=-8)
    for a, b in ((t0, t0 + 24), (amen_t, amen_t + 24)):
        add('clarinets', window(voices_of(full, 'A', 'T'), a, b), off=-12)
        add('bassoons', window(full['B'], a, b), off=-12)
    for a, b in ((climb, amen_t), (amen_t, amen_t + 24)):
        add('trombones', window(voices_of(lac, 'A', 'T', 'B'), a, b), off=-16)
    add('timpani', [(t0 + 30, 6, sc.N('A2'), 62)], 'roll')
    add('timpani', [(t0 + 36, 1, sc.N('D3'), 104)], 'hit')
    add('timpani', [(amen_t + 15, 9, sc.N('D3'), 40)], 'roll')
    add('trumpets', [(t0 + 36, 0.9, sc.N('D4')), (t0 + 36, 0.9, sc.N('D5'))], 'marcato', off=-4)
    add('trumpets', [(amen_t + 15, 9, sc.N(p)) for p in ('D4', 'A4', 'D5', 'F#5')], off=-20)
    continuo([(a, d, p) for a, d, p in full['B']], voices_of(full, 'A', 'T'), [(amen_t, amen_t + 24)])

    harm = (sc.timeline(sc.INTRO, intro.start) + sc.timeline(sc.REQUIEM, req.start)
            + [(a + kyrie.start, d, c) for a, d, c in sc.KYRIE_HARMONY]
            + sc.timeline(sc.DIES + sc.TREMOR + sc.IRA, dies.start) + sc.timeline(sc.TUBA, tuba.start)
            + sc.timeline(sc.LACRIMOSA + sc.AMEN, lacr.start))
    DEBUG.update(parts=parts, sung=sung, voices=voices, harmony=harm, song=s, passing=kyrie_passing)

    # ------------------------------------------------------------------------------------------ perform
    for role, notes in parts.items():
        groups: dict = {}
        for st, du, p, v, a in notes:
            groups.setdefault(a, []).append((st, du, p, v))
        clip = None
        for a, ns in groups.items():
            c = art.articulate(Clip(ns, length=0), a)
            clip = c if clip is None else clip | c
        orch.perform(o, role, clip, 0, articulations=None, seed=sum(map(ord, role)))

    # the choir: sung at the speaking velocity, the written dynamics on each track's live 'dynamics' lane, the
    # syllables of the Dies irae parted on its 'expression' lane (the samples' 1.25 s release would join them)
    tracks = {**{v: ah[v] for v in sc.ORDER}, 'oh': oh}
    gate_span = (float(dies.start), float(ira.end))
    for key, notes in sung.items():
        tr_ = tracks[key]
        notes.sort()
        played = []
        for st, du, p, v in notes:
            bpm = s.tempo_at(st)
            lead = (0.07 if du * 60 / bpm >= 0.35 else 0.035) * bpm / 60.0
            a = max(0.0, st - lead)
            played.append((a, du + (st - a), p, max(96, min(124, SPEAK + round((v - 70) * 0.15)))))
        pc = art.humanize_starts(Clip(played, length=0), s.tempo, 10, seed=len(key))
        tr_.play(pc, 0)
        ex = list(expr.get(key, []))
        ons = sorted({round(n.start, 4) for n in pc if gate_span[0] <= n.start < gate_span[1]})
        for i, a in enumerate(ons[:-1]):
            end = max(n.start + n.dur for n in pc if round(n.start, 4) == a)
            nxt = ons[i + 1]
            spb = s.tempo_at(a) / 60.0                         # beats per second
            if nxt - end < 0.09 * spb:                         # legato: no gap to part
                continue
            fall = min(0.05 * spb, 0.4 * (nxt - end))
            ex += [(end, 1.0), (end + fall, 0.4, 'smooth'), (nxt - 0.004 * spb, 0.4),
                   (nxt + 0.02 * spb, 1.0, 'smooth')]
        if ex:
            ex.sort(key=lambda p: p[0])
            tr_.automate('instrument.expression', ex)
        lane, last = [], None
        onsets: dict = {}
        for st, du, p, v in notes:
            k = round(st, 3)
            if k not in onsets or onsets[k][1] < v:
                onsets[k] = (du, v)
        for st in sorted(onsets):
            du, v = onsets[st]
            x = max(0.08, min(1.0, (v / 127.0) ** 1.6))
            bpm = s.tempo_at(st)
            pre = 0.12 * bpm / 60.0
            if lane and st - pre <= lane[-1][0] + 1e-4:
                continue
            lane.append((st - pre, x, 'smooth'))
            if du * 60 / bpm >= 2.4:                          # messa di voce on the long notes
                lane.append((st + du * 0.5, min(1.0, x + 0.07), 'smooth'))
                lane.append((st + du * 0.9, max(0.08, x - 0.08), 'smooth'))
        tr_.automate('instrument.dynamics', lane)

    # the organ: a continuo - the bass line throughout, a light right hand only in the soft chorales
    organ_notes.sort()
    seen, org = set(), []
    for a, d, p in organ_notes:
        k = (round(a, 3), p)
        if k in seen:
            continue
        seen.add(k)
        org.append((a, d * 0.98, p, 80))
    organ.play(Clip(org, length=0), 0)
    organ.automate('instrument.expression', [(0, 0.5), (req.start, 0.55), (kyrie.start, 0.6),
                                             (kyrie.bar(12), 0.68, 'smooth'), (dies.start, 0.75, 'step'),
                                             (tremor.start, 0.4, 'step'), (tremor.bar(4), 0.7, 'smooth'),
                                             (ira.start, 0.8), (ira.bar(6), 0.8), (ira.bar(6) + 1, 0.3, 'smooth'),
                                             (tuba.start, 0.45), (lacr.start, 0.45), (lacr.bar(4), 0.6, 'smooth'),
                                             (lacr.bar(6), 0.75, 'smooth'), (amen.start, 0.55, 'smooth'),
                                             (amen.bar(3), 0.45, 'smooth')])
    # the hall blooms on the fermatas (and gives it back before the music goes on)
    for role in o.roles:
        base = o.info['seating'][role]['hall_send']
        o[role].automate('send.hall', [(req.bar(9) + 2, base), (req.bar(9) + 4, base + 3, 'smooth'),
                                       (kyrie.start - 0.25, base + 3), (kyrie.start, base, 'smooth'),
                                       (kyrie.bar(18), base), (kyrie.bar(18) + 3, base + 3, 'smooth'),
                                       (dies.start - 0.25, base + 3), (dies.start, base, 'smooth'),
                                       (amen.bar(3), base), (amen.bar(3) + 3, base + 4, 'smooth')])
    # seating (the mix engineer, MIX.md): Mozart's orchestra, audience view
    for tid, pan in SEATING['pan'].items():
        s.tracks[tid].pan = pan
    for tid, w in SEATING['width'].items():
        s.tracks[tid].add_fx(fx.width(width=w))
    # master (the mastering engineer, MASTER.md): `agentsound master --platform dynamic` on the finished mix (MIX, no
    # master eq), classical profile: broad tone only (the sampled sections and the choir read boxy around 800 Hz and
    # dark on top), mono lows, the safety limiter; -19.5 LUFS-I (the middle of the concert window), true peak <= -1 dBTP
    mastering.apply(s, eq={'low.freq': 100, 'low.gain': 3.0, 'low.q': 0.7071, 'peak1.freq': 800, 'peak1.gain': -3.0,
                           'peak1.q': 0.7, 'high.freq': 5000, 'high.gain': 3.0, 'high.q': 0.7071},
                    monobass=120, limiter={'ceiling': -1.2, 'release': 250.0}, loudness_change=2.8)
    return s
