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
heard. Master (MASTER.md): platform 'dynamic', a broad tonal eq and the safety limiter, no glue. The parts are written
into one orch.Score (one dynamics map), the choir into an orch.Choir (speaking velocity, dynamics on its lane).

Measured (report, 'classical'): -19.5 LUFS-I, LRA 15.1 LU, PLR 18.3, TP -1.2 dBTP, 0 warnings, 0 clicks in the mix
(13 masked loop seams, low). Per section: intro -28.1, requiem -21.2, kyrie -20.1, dies -14.4, tremor -16.8, ira
-12.6 (the climax), tuba -25.2, lacrimosa -22.8, amen -22.0 LUFS. Reverb -11.1 LU, width >150 Hz 37 %, balance vs the
reference: lowmid +2.6, mid +2.4, presence +1.4, brilliance -3.9, air -6.9 dB.

CREDITS: Sonatina Symphonic Orchestra 4.0 (Mattias Westlund, Peter Eastman; CC Sampling Plus 1.0), Virtual Playing
Orchestra 3 (Paul Battersby), VSCO 2 CE (Versilian Studios, CC0), No Budget Orchestra 2 (CC-BY-SA 4.0: the 'oh'
choir), Burea Church choir organ sample set by Lars Palo (CC-BY-SA 2.5), Voxengo IM Reverbs (Musikvereinsaal).
"""
from agentsound import *
from agentsound import bands, hornist, mastering, patches, voicing
from agentsound.bandlib import orchestra as orch
from agentsound.figures import figure as fig
from agentsound.voicing import line, merge_ties, trim, window

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
DEBUG: dict = {}           # the score, the choir and the Kyrie (for checks outside the build)
STRINGS_RANGE = {'S': (62, 84), 'A': (55, 76), 'T': (48, 69), 'B': (36, 62)}
# one dynamics curve for the whole piece (velocity 40 = p, 78 = mf, 95 = f, 115 = ff): (beat, velocity[, 'step']).
# The arc holds back: the Kyrie closes f, the Dies irae is f, the tremor's crescendo stops short of the ira, which
# alone is ff (the climax).
DYNAMICS = {
    'intro': [(0, 56), (8, 64), (12, 70), (16, 60), (20, 66), (23.8, 96)],
    'requiem': [(0, 98), (7.9, 100), (8, 56, 'step'), (12, 60), (15.9, 70), (16, 88, 'step'), (23.9, 92),
                (24, 58, 'step'), (28, 54), (32, 62), (36, 52), (40, 40)],
    'kyrie': [(0, 64), (8, 68), (16, 74), (24, 80), (32, 76), (40, 80), (47.9, 84), (48, 92, 'step'),
              (56, 98), (64, 104), (68, 108), (72, 108), (76, 100)],
    'dies': [(0, 110), (15.9, 108), (16, 108), (31.9, 114)],
    'tremor': [(0, 34, 'step'), (15.9, 58), (16, 80, 'step'), (24, 106), (32, 110)],
    'ira': [(0, 122), (16, 124), (24, 118), (25, 40, 'step'), (32, 28)],
    'tuba': [(0, 60), (8, 64), (16, 52), (24, 60), (29.9, 56), (32, 44)],
    'lacrimosa': [(0, 50), (12, 54), (18, 58), (24, 56), (35.9, 100), (36, 106), (42, 80), (48, 64)],
    'amen': [(0, 60), (6, 68), (12, 64), (15, 78), (18, 70), (24, 46)],
}
PHRASING = {'violins1': 0.9, 'violins2': 0.9, 'violas': 0.5, 'cellos': 0.5, 'trombones': 0.8, 'clarinets': 0.7,
            'bassoons': 0.5, 'basses': 0.4}


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

    # the score (orch.Score: one dynamics map, the bar's accents, a seeded +-3, each line's phrase arc) and the choir
    # (orch.Choir: sung at the speaking velocity, the written dynamics on each track's live 'dynamics' lane, the
    # syllables of the Dies irae parted on its 'expression' lane - the samples' 1.25 s release would join them)
    sc_ = orch.Score(s, o, DYNAMICS, seed=626, floor=12, phrasing=PHRASING, follow=False)
    ch_ = orch.Choir(s, {**ah, 'oh': oh}, lane='dynamics', speak=SPEAK, gate=(float(dies.start), float(ira.end)))
    add = sc_.add

    def sing(key, notes, **kw):
        sc_.sing(ch_, key, notes, **kw)

    def satb(parts, *vs):
        return [n for v in vs for n in parts.get(v, [])]

    organ_notes = []          # the continuo: the bass line, a light right hand in the soft chorales

    def continuo(bass, rh=(), soft=()):
        """The organ: the bass line throughout (tasto solo), the right hand (rh notes) only inside the soft spans."""
        organ_notes.extend((a, d, p) for a, d, p in bass)
        organ_notes.extend((a, d, p) for a, d, p in rh if any(x - 1e-6 <= a < y - 1e-6 for x, y in soft))

    # ================================================================================== I. INTROITUS
    t0 = float(intro.start)
    st = sc.chorale(sc.INTRO, t0, ranges=STRINGS_RANGE)
    # the pulse is the figure: violins mp-mf staccato over the chords, the low strings detached quarters under it
    sc_.colla_parte(st, {'violins1': ('S', 24), 'violins2': ('A', 22)}, art='staccato', fig='offbeats')
    add('violas', fig(st['T'], 'beats', gap=0.6), off=-4)
    add('cellos', fig(st['B'], 'beats', gap=0.7), off=-2)
    add('basses', fig(window(st['B'], t0 + 8, t0 + 24), 'beats', gap=0.7), off=-2, transpose=-12)
    add('bassoons', line(sc.INTRO_BASSOON, t0), off=6)
    add('bassoons', window(st['T'], t0 + 16, t0 + 24), off=-6)
    add('clarinets', line(sc.INTRO_BASSET1, t0) + line(sc.INTRO_BASSET2, t0), off=4)
    add('timpani', [(t0 + 20, 4, sc.N('A2'), 50)], 'roll')

    # requiem: the choir enters voice by voice (B T A S, a beat apart, each on 'Re-qui-em'), f, then subito p
    t0 = float(req.start)
    ch = sc.chorale(sc.REQUIEM, t0, tie=True)
    ch['S'] = line(sc.REQUIEM_SOPRANO, t0)
    for v in sc.ORDER:
        ch[v] = line(sc.REQUIEM_ENTRY[v], t0) + trim(ch[v], t0 + 4)
        sing(v, ch[v], off={'S': 2, 'A': -3, 'T': -2, 'B': 0}[v])
    st = sc.chorale(sc.REQUIEM, t0, ranges=STRINGS_RANGE)
    vn = {'S': window(st['S'], t0, t0 + 4) + window(ch['S'], t0 + 4), 'A': window(st['A'], t0, t0 + 4) +
          window(ch['A'], t0 + 4)}                                    # the pulse follows the voices it doubles
    sc_.colla_parte(vn, {'violins1': ('S', 24), 'violins2': ('A', 22)}, art='staccato', fig='offbeats')
    add('violas', fig(st['T'], 'beats', gap=0.6), off=-4)
    sc_.double(fig(st['B'], 'beats', gap=0.7), {'cellos': (0, -2), 'basses': (-12, -4)})
    for a, b in ((t0, t0 + 8), (t0 + 16, t0 + 28)):
        add('trombones', window(satb(ch, 'A', 'T', 'B'), a, b), off=-12)
    for a, b in ((t0 + 8, t0 + 16), (t0 + 28, t0 + 40)):
        add('clarinets', window(satb(ch, 'A', 'T'), a, b), off=-6)
    add('bassoons', ch['B'], off=-8)
    add('trumpets', [(t0, 0.9, sc.N('D4')), (t0, 0.9, sc.N('D5'))], 'marcato', off=-2)
    add('trumpets', [(t0 + 16, 0.9, sc.N('A4'))], off=-10)
    add('timpani', [(t0, 1.5, sc.N('D3'), 100), (t0 + 16, 1.0, sc.N('A2'), 80)], 'hit')
    add('timpani', [(t0 + 36, 4, sc.N('A2'), 46)], 'roll')
    continuo(ch['B'], satb(sc.chorale(sc.REQUIEM, t0, tie=True), 'A', 'T'), [(t0 + 8, t0 + 16), (t0 + 24, t0 + 40)])

    # ================================================================================== II. KYRIE (fugue)
    # the entries as written (score.py), the free voices voiced around them, passing 8ths where they make no
    # parallels and rub no semitone; each entering voice leads for its first two bars (the others drop back)
    t0 = float(kyrie.start)
    ky = voicing.fugue(sc.KYRIE_ENTRIES, voices=sc.CHOIR, center=sc.CENTER, at=t0, harmony=sc.KYRIE_HARMONY,
                       lt=lambda t: sc.KYRIE_LT.get(int(t), 1), final=sc.KYRIE_FINAL, final_at=72, until=68,
                       key_at=sc.KYRIE_KEYS)
    for v in sc.ORDER:
        sing(v, ky[v], off={'S': 0, 'A': -2, 'T': -1, 'B': 1}[v], dur=0.97, offs=ky.offset(v))
        ch_.lane(v, ky.emphasis(v, kyrie.end))
    # colla parte (Mozart's Kyrie: the strings and winds double the voices, the entering voice's doubling in front)
    for role, v, off, tr in (('violins1', 'S', -8, 0), ('violins2', 'A', -10, 0), ('violas', 'T', -10, 0),
                             ('cellos', 'B', -8, 0), ('basses', 'B', -10, -12), ('bassoons', 'B', -10, 0)):
        add(role, ky[v], off=off, transpose=tr, dur=0.97, offs=ky.offset(v))
    add('clarinets', window(ky['A'], t0 + 16, t0 + 76), off=-12, dur=0.97, offs=ky.offset('A'))
    add('trombones', window(satb(ky.parts, 'A', 'T', 'B'), t0 + 48, t0 + 76), off=-16, dur=0.97)
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
        sing(v, ch[v], off={'S': 0, 'A': -2, 'T': -2, 'B': 0}[v], dur=declaim)
    storm = [(t0, trem_a), (trem_b, trem_b + 25)]
    # violins I: running 16ths between the soprano and the alto of each chord (the storm), f and on top; violins II
    # repeat the alto in measured 16ths in the Dies irae and double violins I an octave down in the ira (the climax)
    vel = sc_.vel
    for (a, d, p_s), (_, _, p_a), (_, _, p_t), (_, _, p_b) in zip(ch['S'], ch['A'], ch['T'], ch['B']):
        if any(x <= a < y for x, y in storm):
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
            sc_.double(fig([(a, d, p_b)], 'beats', every=0.5, gap=0.4), {'cellos': (0, -2), 'basses': (-12, -4)},
                       art='staccato', accent=False)
        else:   # tremor: everything trembles
            add('violins1', [(a, d, p_s)], 'tremolo', off=-2)
            add('violins2', [(a, d, p_a)], 'tremolo', off=-4)
            add('violas', [(a, d, p_t)], 'tremolo', off=-4)
            add('cellos', [(a, d * 0.6, p_b)], 'staccato', off=0)
            add('basses', [(a, d, p_b - 12)], 'tremolo', off=-4)
    for a, b in storm + [(trem_a + 16, trem_b)]:
        add('trombones', window(satb(ch, 'A', 'T', 'B'), a, b), off=-10, dur=0.6)
        add('clarinets', window(satb(ch, 'A', 'T'), a, b), off=-12, dur=0.6)
        add('bassoons', window(ch['B'], a, b), off=-6, dur=0.6)
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
            add('timpani', [(a, 0.5, sc.N(tim), vel(a, 4 if sc_.phase(a) < 0.02 else -14))], 'hit')
        if a < t0 + 16:
            continue
        loud = 10 if a >= trem_b else 4
        for p in tp:
            if d >= 2 - 1e-6:
                fig_ = [(a, 0.6, sc.N(p), vel(a, loud + 4, False), 'marcato'),
                        (a + 0.75, 0.2, sc.N(p), vel(a, loud - 4, False), 'staccato'),
                        (a + 1.0, min(d - 1.0, 1.0) * 0.85, sc.N(p), vel(a, loud, False), 'marcato')]
            else:
                fig_ = [(a, min(d * 0.7, 0.8), sc.N(p), vel(a, loud, False), 'marcato')]
            for st_, du_, p_, v_, a_ in fig_:
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
    st = sc.chorale(sc.TUBA, t0, ranges=STRINGS_RANGE, lt=9, tie=True)
    sc_.colla_parte(st, {'violins1': ('S', -14), 'violins2': ('A', -14), 'violas': ('T', -14), 'cellos': ('B', -10)})
    add('basses', window(st['B'], t0 + 16, t0 + 32), off=-10, transpose=-12)
    add('bassoons', window(st['T'], t0 + 16, t0 + 32), off=-12)
    continuo(st['B'], satb(st, 'A', 'T'), [(t0, t0 + 32)])
    call = Clip([(a, d, p, 80) for a, d, p in line(sc.TUBA_TROMBONE)], length=32)
    perf = hornist.arrange(call, s.tempo_at(t0), family='trombone', style='classical', section='verse',
                           peaks=(2, 4, 12, 20), vel=(66, 104), seed=11, at=t0)
    perf.place(tbn, tuba)
    tbn.automate('gainDb', [(tuba.bar(4) - 0.5, 0.0), (tuba.bar(4) + 0.5, -5.0, 'smooth')])   # under the men's answer
    men = [(n[0] + t0,) + tuple(n[1:]) for n in line(sc.TUBA_MEN)]
    sing('oh', men, off=8)                                        # the men answer (the 'oh' choir loops cleanly)
    ch_.swell('oh', men, t0 + 16, t0 + 32, 8, lo=0.72)

    # ================================================================================== V. LACRIMOSA + AMEN
    t0 = float(lacr.start)
    table = sc.LACRIMOSA + sc.AMEN
    full = sc.chorale(table, t0, tie=False)
    tl = sc.timeline(table, t0)
    choir_from = t0 + 12
    lac = {v: merge_ties(window(full[v], choir_from, t0 + 72)) for v in ('A', 'T', 'B')}   # sustained under the lament
    lac['S'] = line(sc.LACRIMOSA_SOPRANO, t0) + line(sc.AMEN_SOPRANO, float(amen.start))
    climb, amen_t = t0 + 24, float(amen.start)
    for v in sc.ORDER:
        soft = [n for n in lac[v] if n[0] < climb]
        loud = [n for n in lac[v] if climb <= n[0] < amen_t]
        close = [n for n in lac[v] if n[0] >= amen_t]
        if v == 'S':        # the lament's soprano (up to F5) sings 'ah': the 'oh' samples stop at C#5
            sing('S', soft + loud, off=2)
            sing('oh', close, off=2)
        else:
            sing('oh', soft + close, off={'A': -2, 'T': -2, 'B': 0}[v])
            sing(v, loud, off={'A': -3, 'T': -2, 'B': 0}[v])
    # the lament breathes: a swell on each 'Lacrimosa' phrase (p < mp > p, ~7 dB), the Amen leans into its plagal
    # chords and blooms into the Picardy third
    ch_.swell('oh', lac['S'], choir_from, climb, 6, lo=0.64).swell('S', lac['S'], choir_from, climb, 6, lo=0.64)
    ch_.lane('oh', [(amen_t - 0.5, 1.0), (amen_t, 0.8), (amen_t + 1.5, 1.0, 'smooth'), (amen_t + 3, 0.8, 'smooth'),
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
        return any(abs(p - q) % 12 in (1, 11) for t in (t1, t2)
                   for q in [n[2] for n in choir_now if n[0] - 1e-6 <= t < n[0] + n[1] - 1e-6])

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
    sc_.colla_parte({v: window(full[v], amen_t, amen_t + 24) for v in sc.ORDER},
                    {'violins1': ('S', -12), 'violins2': ('A', -12)})
    add('violas', [n for n in full['T'] if n[0] < amen_t], off=-14)
    add('violas', window(full['T'], amen_t, amen_t + 24), off=-10)
    add('cellos', [(a, 0.9, p) for a, d, p in full['B'] if a < amen_t], off=-6)
    add('cellos', window(full['B'], amen_t, amen_t + 24), off=-6)
    add('basses', [(a, 0.9, p - 12) for a, d, p in full['B'] if a < climb], 'pizzicato', off=-2)
    add('basses', [(a, 0.9, p - 12) for a, d, p in full['B'] if climb <= a < amen_t], off=-8)
    add('basses', [(a, d, p - 12) for a, d, p in window(full['B'], amen_t, amen_t + 24)], off=-8)
    for a, b in ((t0, t0 + 24), (amen_t, amen_t + 24)):
        add('clarinets', window(satb(full, 'A', 'T'), a, b), off=-12)
        add('bassoons', window(full['B'], a, b), off=-12)
    for a, b in ((climb, amen_t), (amen_t, amen_t + 24)):
        add('trombones', window(satb(lac, 'A', 'T', 'B'), a, b), off=-16)
    add('timpani', [(t0 + 30, 6, sc.N('A2'), 62)], 'roll')
    add('timpani', [(t0 + 36, 1, sc.N('D3'), 104)], 'hit')
    add('timpani', [(amen_t + 15, 9, sc.N('D3'), 40)], 'roll')
    add('trumpets', [(t0 + 36, 0.9, sc.N('D4')), (t0 + 36, 0.9, sc.N('D5'))], 'marcato', off=-4)
    add('trumpets', [(amen_t + 15, 9, sc.N(p)) for p in ('D4', 'A4', 'D5', 'F#5')], off=-20)
    continuo(full['B'], satb(full, 'A', 'T'), [(amen_t, amen_t + 24)])
    DEBUG.update(score=sc_, choir=ch_, kyrie=ky, song=s)

    # ------------------------------------------------------------------------------------------ perform
    sc_.perform()
    ch_.perform()
    # the organ: a continuo - the bass line throughout, a light right hand only in the soft chorales
    organ_notes.sort()
    seen, org = set(), []
    for a, d, p in organ_notes:
        if (round(a, 3), p) not in seen:
            seen.add((round(a, 3), p))
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
    orch.ring(o, req.bar(9) + 2, length=2, db=3, back=kyrie.start)
    orch.ring(o, kyrie.bar(18), length=3, db=3, back=dies.start)
    orch.ring(o, amen.bar(3), length=3, db=4)
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
