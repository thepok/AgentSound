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
hand; the fugato's free voices too. The parts are written into one orch.Score (one dynamics map, performed at the
end). Profile 'classical'.

CREDITS: Sonatina Symphonic Orchestra 4.0 (Mattias Westlund, Peter Eastman; CC Sampling Plus 1.0), Virtual Playing
Orchestra 3 (Paul Battersby), VSCO 2 CE (Versilian Studios, CC0), Voxengo IM Reverbs (Musikvereinsaal).
"""
from agentsound import *
from agentsound import bands, hornist, mastering, voicing
from agentsound.bandlib import orchestra as orch
from agentsound.figures import figure as fig
from agentsound.voicing import line, window

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
STR = {'violins1': (60, 96, 76), 'violins2': (55, 84, 67), 'violas': (48, 76, 60), 'cellos': (36, 64, 48)}
UNDER = ('violins2', 'violas', 'cellos')                 # the strings under violins I's line
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
# the conductor's arc (the mix engineer, MIX.md): section rides on the master input, before the limiter - the soft
# passages up (they sat at -31..-41 LUFS: too soft for a phone), the earlier fortissimos a little under the coda, so
# the triumph is the loudest moment; inside a section (beat, dB): the intro's unison blows and fermata, the pedal's
# crescendo is ours, the fugato's first entries alone, the codettas soft (not pulled down with the ff), coda1's subito
# p and climb, the hemiola leads and the horn call's pedal is soft
ARC = {'intro': -1.5, 't1': 3.5, 'trans': -1.0, 't2': 1.0, 'closing': -2.5, 'storm': -1.5, 'pedal': 0.0, 'rec1': -0.5,
       'cadenza': 1.5, 'rec3': 3.0, 'rec4': -2.0, 'coda1': 0.5, 'coda2': 1.0, 'coda3': 1.0, 't1ff': -1.0, 'fugato': 6.0}
ARC_IN = {'intro': [(2, -1.5), (2.5, 3.0, 'smooth'), (23.75, 3.0), (24, -1.5, 'smooth'), (26, -1.5),
                    (26.5, 3.0, 'smooth'), (36, 1.0, 'smooth')],
          'pedal': [(0.5, 3.0, 'smooth'), (16, 2.5, 'smooth'), (32, 1.5, 'smooth'), (48, 0.0, 'smooth')],
          'fugato': [(8, 6.0), (16, 4.5, 'smooth'), (48, 0.0, 'smooth')],
          'closing': [(31.5, -2.5), (32, 1.5, 'smooth'), (43.5, 1.5), (44, -2.5, 'smooth')],
          'rec4': [(31.5, -2.0), (32, 1.5, 'smooth'), (43.5, 0.5), (44, 0.0, 'smooth')],
          'coda1': [(15.5, 0.5), (16, 2.5, 'smooth'), (40, 2.0), (60, 0.5, 'smooth')],
          'trans': [(31.5, 0.0), (32, 0.5, 'smooth'), (47.5, 0.5), (48, 2.0, 'smooth')]}
TP_NATURAL = orch.natural_brass('C')           # natural trumpets in C: C4 E4 G4 C5 E5 G5


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
    horn = s.track('horn_solo', 'sampled/solo_horn', pan=-0.3, gain_db=-1.0, sends={hall: -4})
    clar = s.track('clarinet_solo', 'sampled/solo_clarinet', pan=-0.05, gain_db=-2.0, sends={hall: -6})
    oboe = s.track('oboe_solo', 'sampled/solo_oboe', pan=0.1, gain_db=-1.0, sends={hall: -7})

    # the score: every part written into one buffer, velocities from the dynamics map (+ the bar's accents, a seeded
    # +-3 and each line's phrase arc), performed at the end; the pedal's crescendo is re-attacked by hand (follow=False)
    sc_ = orch.Score(s, o, DYNAMICS, seed=1808, follow=False)
    add, brass, hits = sc_.add, sc_.brass, sc_.hits

    def H(table, at, key=None):
        return s.harmony(table, at, key=key)

    def solo(track, spec, t0, family, section, vel_rng, seed, **kw):
        clip = Clip([(a, d, p, 80) for a, d, p in line(spec)], length=voicing.length(spec))
        perf = hornist.arrange(clip, s.tempo_at(float(t0)), family=family, style='classical', section=section,
                               vel=vel_rng, seed=seed, at=float(t0), **kw)
        perf.place(track, float(t0))
        return perf

    def theme_ff(m, sync, clar=None):
        """The theme ff: violins in octaves (sforzandi on the syncopes), flute an octave up, oboe at pitch."""
        S1, D9 = {'sf': sync, 'dur': 0.92}, {'dur': 0.9}
        sc_.double(m, {'violins1': (12, 4, S1), 'violins2': (0, 2, S1), 'flutes': (12, 0, D9), 'oboes': (0, -2, D9),
                       **({'clarinets': clar + (D9,)} if clar else {})})

    def drive(tp, a, b, bassoons=True):
        """The ff drive under it: violas and cellos in 8ths, basses (and bassoons) on the beats."""
        add('violas', fig(window(tp['v5'], a, b), 'pulse8'), 'staccato', off=-2, accent=False)
        add('cellos', fig(window(tp['v7'], a, b), 'pulse8'), 'staccato', off=0, accent=False)
        add('basses', fig(window(tp['v8'], a, b), 'beats', gap=0.7), 'staccato', off=0)
        if bassoons:
            add('bassoons', fig(window(tp['v7'], a, b), 'beats', gap=0.7), 'staccato', off=-2)

    def hemiola(tp, h, t0, at, lens):
        for t, L in zip([t0 + x for x in at], lens):
            hits(tp, [t], length=L - 0.25, off=6, sf=True)
        brass(h, [t0 + x for x in at], length=1.5, off=4)

    def closing(t0, h, m, bass_cell):
        """The closing theme ff (the cell in major): violins in octaves, the drive, weak-beat sforzandi, the hemiola
        cadence, the codetta's cell in the basses. Returns the tutti chords."""
        tp = h.tutti()
        sc_.double(m, {'violins1': (12, 4, {'dur': 0.92}), 'violins2': (0, 2, {'dur': 0.92}), 'flutes': (12, 0),
                       'oboes': (0, -2)})
        drive(tp, t0, t0 + 16)
        weak = [t0 + b + o_ for b in range(0, 16, 4) for o_ in (1, 3)]
        hits(tp, weak, length=0.6, off=2, roles=('clarinets', 'bassoons'), sf=True)
        brass(h, weak, length=0.6, off=2)
        hemiola(tp, h, t0 + 16, (0, 3, 6, 8, 10, 12), [3, 3, 2, 2, 2, 4])
        sc_.double(line(bass_cell, t0), {'cellos': (0, 6), 'basses': (-12, 2)})
        return tp

    def syncopes(table, t0):
        """Syncopated string chords (sforzandi between the beats) over the low strings' quarters (16 beats)."""
        st = H(table, t0).chorale(voicing.STRINGS, tie=True)
        add(st, 'marcato', fig='syncope', off={'violins1': 6, 'violins2': 4, 'violas': 2}, accent=False,
            roles=('violins1', 'violins2', 'violas'))
        sc_.double(fig(window(st['cellos'], t0, t0 + 16), 'beats', gap=0.75), {'cellos': (0, 2), 'basses': (-12, 0)},
                   art='staccato')

    def horn_pedal(table, at, key, bass, call, echo, name, seed):
        """A dominant pedal: the strings tremble, cellos / basses hold it, the solo horn calls, the clarinets echo."""
        add(H(table, at, key).chorale(STR, tie=True), 'tremolo', off=-2, roles=UNDER[:2])
        add('cellos', [(at, 16, sc.N(bass + '2'))], off=0)
        add('basses', [(at, 16, sc.N(bass + '1'))], off=-2)
        performances[name] = solo(horn, call, at, 'trumpet', 'verse', (62, 92), seed, vib_ct=0.0, peak_vib_ct=4.0)
        add('clarinets', line(echo, at + 8), off=0)

    performances = {}

    # ================================================================================== INTRODUCTION
    t0 = float(intro.start)
    sc_.unison(t0, 2, 'C')
    intro_h = H(sc.INTRO, t0)
    sc_.winds(H(sc.INTRO[:3], t0), off=0)                                    # winds pp: Ab, Db/F, G7/F
    vln = line(sc.INTRO_VIOLIN, t0)
    add('violins1', [n for n in vln if n[0] < t0 + 24], off=8)
    low = H(sc.INTRO[3:9], t0 + 8).under(vln, STR)
    add(low, off={'violins2': -2, 'violas': -2, 'cellos': 0})
    add('basses', window(low['cellos'], t0 + 12, t0 + 24), off=-4, transpose=-12)
    add('bassoons', line(sc.INTRO_BASSOON, t0), off=4)
    sc_.unison(t0 + 24, 2, 'Ab')
    sc_.winds(H(sc.INTRO[11:15], t0 + 26), off=0)                            # Db pp, Fm/Ab, the German sixth
    add(H(sc.INTRO[13:15], t0 + 28).chorale(STR, tie=True), off=-4, roles=UNDER)
    # the dominant pedal: basses and cellos tremble on G, the timpani roll, horns, the violins and the flute climb
    ped = t0 + 32
    add('basses', [(ped, 8, 31)], 'tremolo', off=-2)
    add('cellos', [(ped, 8, 43)], 'tremolo', off=-2)
    add('timpani', [(ped, 7.5, 43)], 'roll', off=-6)
    add('horns', [(ped, 8, 55), (ped, 8, 67)], off=-6)
    add('violins1', window(vln, ped, ped + 8), off=4)
    add('flutes', line(sc.INTRO_FLUTE, t0), off=0)
    add(H(sc.INTRO[15:], ped).under(window(vln, ped, ped + 8), STR), 'tremolo', off=-4, roles=UNDER[:2])
    sc_.winds(H(sc.INTRO[15:], ped), off=-6, roles=('oboes', 'clarinets', 'bassoons'))
    brass(intro_h, [ped + 4], length=4, horns=False, timpani=False, art='sustain')

    # ================================================================================== EXPOSITION
    # t1: the first theme p in the strings, the 8th-note drive in the inner strings
    t0 = float(t1.start)
    m = line(sc.T1_MEL, t0)
    add('violins1', m, off=10, dur=0.92)
    acc = H(sc.T1, t0).under(m, STR)
    add(acc, 'staccato', fig='pulse8', off={'violins2': -4, 'violas': -6}, accent=False, roles=UNDER[:2])
    add('cellos', fig(acc['cellos'], 'beats', gap=0.7), 'staccato', off=0)
    add('basses', fig(acc['cellos'], 'beats', every=2, gap=1.2), off=-2, transpose=-12)
    h = H(sc.T1, t0)
    sc_.winds(H(sc.T1[11:14], t0 + 24), off=-6, roles=('oboes', 'clarinets', 'bassoons'))
    brass(h, [t0 + 28], length=2, trumpets=False)

    # t1ff: the counterstatement, ff tutti
    t0 = float(S['t1ff'].start)
    m, h = line(sc.T1FF_MEL, t0), H(sc.T1FF, t0)
    tp = h.tutti()
    theme_ff(m, [t0 + x for x in (0.5, 4.5, 8.5, 12.5, 16.5, 18.5, 20.5, 22.5)])     # the cell's off-beat long notes
    drive(tp, t0, t0 + 32)
    add('clarinets', tp['v4'], off=-6, dur=0.9)
    stabs = [t0 + x for x in sc.T1FF_STABS] + [t0 + 28, t0 + 29.5, t0 + 30]
    hits(tp, stabs, length=0.7, off=4, sf=True)
    brass(h, [t0 + b for b in range(0, 28, 4)] + stabs, length=0.7)
    brass(h, [t0 + 24], length=2, timpani=False)

    # trans: syncopated sforzandi, the cell in the basses, the hemiola, the Bb pedal with the horn call
    t0 = float(S['trans'].start)
    h = H(sc.TRANS, t0)
    syncopes(sc.TRANS[:8], t0)
    cell_b = line(sc.TRANS_BASS_CELL, t0)
    add('cellos', cell_b, off=8, sf=[n[0] for n in cell_b if n[1] == 1 and abs((n[0] - t0) % 1 - 0.5) < 1e-6])
    add('basses', cell_b, off=4, transpose=-12)
    add('bassoons', cell_b, off=4)
    sc_.winds(H(sc.TRANS[:8], t0), off=-4, roles=('flutes', 'oboes', 'clarinets'))
    brass(h, [t0 + b for b in range(0, 32, 4)], length=3.5, timpani=False, off=-6)
    brass(h, [t0 + b + 1 for b in range(0, 32, 2)], length=0.6, horns=False, off=-2)   # sforzandi on the weak beats
    hemiola(H(sc.TRANS[8:14], t0 + 32).tutti(), h, t0 + 32, (0, 3, 6, 8, 11, 14), [3, 3, 2, 3, 3, 2])
    horn_pedal(sc.TRANS[14:], t0 + 48, 'Eb major', 'Bb', sc.HORN_CALL_EB, sc.CLAR_ECHO_EB, 'call1', 31)  # Bb pedal

    # t2: the second theme - the solo clarinet, then violins I + flute; the cell's rhythm in the cellos
    t0 = float(S['t2'].start)
    h = H(sc.T2, t0)
    m1 = line(sc.T2_MEL1, t0)
    performances['t2_clar'] = solo(clar, sc.T2_MEL1, t0, 'clarinet', 'verse', (52, 92), 41)
    pad = H(sc.T2[:12], t0, 'Eb major').under(m1, STR)
    add(pad, off=-6, roles=UNDER[:2])
    add('cellos', fig(window(pad['cellos'], t0, t0 + 32), 'beats', every=2, gap=0.6), 'pizzicato', off=6)
    add('basses', fig(window(pad['cellos'], t0, t0 + 32), 'beats', every=4, gap=0.6), 'pizzicato', off=4,
        transpose=-12)
    add('bassoons', window(pad['cellos'], t0 + 16, t0 + 32), off=-6)
    m2 = line(sc.T2_MEL2, t0 + 32)
    sc_.double(m2, {'violins1': (0, 8), 'flutes': (12, 0)}, dur=0.95)
    acc = H(sc.T2[12:], t0 + 32, 'Eb major').under(m2, STR)
    add(acc, 'staccato', fig=('pulse8', {'gap': 0.45}), off=-8, accent=False, roles=UNDER[:2])
    add('cellos', line(sc.T2_CELLO_CELL, t0), off=2)
    add('cellos', window(acc['cellos'], t0 + 48, t0 + 64), off=-2)
    add('basses', fig(window(acc['cellos'], t0 + 32, t0 + 64), 'beats', every=2, gap=0.6), 'pizzicato', off=4,
        transpose=-12)
    sc_.winds(H(sc.T2[18:], t0 + 48, 'Eb major'), off=-4, roles=('oboes', 'clarinets', 'bassoons'))
    brass(h, [t0 + 56, t0 + 60], length=3.5, trumpets=False, timpani=False, off=-10)

    # closing: the cell in major ff, the weak-beat sforzandi, the hemiola cadence, the codetta, two blows
    t0 = float(S['closing'].start)
    h = H(sc.CLOSING, t0, 'Eb major')
    tp = closing(t0, h, line(sc.CLOSING_MEL, t0), sc.CLOSING_BASS_CELL)
    add(H(sc.CLOSING[10:13], t0 + 32, 'Eb major').chorale(STR, tie=True), off=-8, roles=UNDER[:2])
    ans = line(sc.CLOSING_WIND_ANSWER, t0)
    sc_.double(ans, {'oboes': (0, 4), 'flutes': (12, 0)})
    hits(tp, [t0 + 44], length=1.6, off=6, sf=True)                     # one blow, then the silence
    brass(h, [t0 + 44], length=1.6, off=6)

    # ================================================================================== DEVELOPMENT
    # dev1: the cell through falling thirds, tossed between winds (tonic) and violins (dominant)
    t0 = float(S['dev1'].start)
    h = H(sc.DEV1, t0)
    st = h.chorale(STR, tie=True)
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
    add('violas', st['violas'], 'tremolo', off=-6)
    add('violins2', [n for n in st['violins2'] if int((n[0] - t0) // 4) % 2 == 0], 'tremolo', off=-8)
    add('cellos', fig(st['cellos'], 'beats', gap=0.8), 'staccato', off=0)
    add('basses', fig(st['cellos'], 'beats', every=2, gap=1.5), off=-2, transpose=-12)
    add('bassoons', st['cellos'], off=-6)
    brass(h, [t0 + 4 * k for k in range(12)], length=3.5, off=-6, timpani=False)
    brass(h, [t0 + 4 * k + 0.5 for k in range(12)], length=0.6, horns=False, off=-2)

    # fugato: the subject in F minor, entries cellos - violas - violins II - violins I, free counterpoint voiced
    t0 = float(S['fugato'].start)
    fg = voicing.fugue([(r, at_, 'subject', sh) for r, at_, sh in sc.FUGATO_ENTRIES], voices=STR, at=t0,
                       subject=sc.SUBJECT, subject_harmony=sc.SUBJECT_H, key='F minor',
                       key_at=[(0, 'F minor'), (16, 'C minor'), (32, 'F minor'), (48, 'C minor')])
    DEBUG['fugato'] = (fg, fg.check())
    for v in STR:                                # the entering subject leads, the free voices drop back
        w = {round(n[0], 4) for n in fg.written[v]}
        add(v, [(n[0], n[1], n[2], sc_.vel(n[0], 8 if round(n[0], 4) in w else -4)) for n in fg[v]], dur=0.94)
    add('basses', [(n[0], n[1], n[2] - 12, sc_.vel(n[0], -8)) for n in fg['cellos'] if n[1] >= 1 - 1e-6], dur=0.94)

    def subj(shift, a):
        return [(n[0], n[1], n[2], sc_.vel(n[0], -6)) for n in line(sc.SUBJECT, a, shift)]

    # the winds double the ENTERING subject (violins II's, then violins I's), never a free voice
    add('bassoons', subj(12, t0 + 32), dur=0.94)
    add('clarinets', subj(12 + sc.ANSWER_SHIFT, t0 + 48), dur=0.94)
    add('oboes', subj(12 + sc.ANSWER_SHIFT, t0 + 48), dur=0.94)
    add('horns', [(t0 + 48, 8, sc.N('F3')), (t0 + 48, 8, sc.N('C4')), (t0 + 56, 8, sc.N('G3')),
                  (t0 + 56, 8, sc.N('C4'))], off=-10)
    add('timpani', [(t0 + 60, 4, 48)], 'roll', off=-14)

    # storm: hammered syncopated tutti into Gb, subito pp the second theme in Gb, the German sixth
    t0 = float(S['storm'].start)
    h = H(sc.DEV3, t0)
    tp = H(sc.DEV3[:4], t0, 'Db major').tutti()
    for r in ('violins1', 'violins2', 'violas'):
        add(r, fig([n for v in orch.TUTTI_ROLES[r] for n in tp[v]], 'syncope'), 'marcato', off=6, accent=False)
    add('cellos', fig(tp['v7'], 'pulse8', gap=0.4), 'staccato', off=2, accent=False)
    add('basses', fig(tp['v8'], 'pulse8', gap=0.4), 'staccato', off=0, accent=False)
    weak = [t0 + b + o_ for b in range(0, 16, 4) for o_ in (1, 3)]
    hits(tp, weak, length=0.6, off=4, roles=('flutes', 'oboes', 'clarinets', 'bassoons'), sf=True)
    brass(h, weak, length=0.6, off=4, timpani=False)
    quiet = H(sc.DEV3[4:], t0 + 16, 'Gb major').under(line(sc.DEV3_CLAR, t0) + line(sc.DEV3_FLUTE, t0), STR)
    add(quiet, off={'violins2': -4, 'violas': -4, 'cellos': -2})
    add('basses', window(quiet['cellos'], t0 + 24, t0 + 32), off=-4, transpose=-12)
    performances['storm_clar'] = solo(clar, sc.DEV3_CLAR.replace('r:16 | ', ''), t0 + 16, 'clarinet', 'verse',
                                      (36, 66), 43)
    add('flutes', line(sc.DEV3_FLUTE, t0), off=8)

    # pedal: the dominant pedal on G, the cell climbing in imitation, the long crescendo
    t0 = float(S['pedal'].start)
    h = H(sc.DEV4, t0)
    add('basses', fig([(t0, 62, 31)], 'pulse8', gap=0.45), 'staccato', off=-2, accent=False)
    # the crescendo is played: every held part re-attacks each bar (a new bow, a new breath) at the map's rising level
    add('timpani', [(t0 + 32 + 4 * i, 4 if i < 7 else 1.5, 43) for i in range(8)], 'roll', off=-8)
    add('horns', [(t0 + 16 + 4 * i, 3.9, p) for i in range(11) for p in (55, 67)] + [(t0 + 60, 2, 55), (t0 + 60, 2, 67)],
        off=-8)
    pd = H(sc.DEV4[:-1], t0).chorale(STR, tie=False)
    add('violas', pd['violas'], 'tremolo', off=-6)
    add('violins2', window(pd['violins2'], t0 + 32, t0 + 62), 'tremolo', off=-8)
    add('cellos', fig([(t0 + 4, 58, 43)], 'pulse8', gap=0.45), 'staccato', off=-4, accent=False)
    sc_.winds(H(sc.DEV4[8:-1], t0 + 32), off=-8, roles=('clarinets', 'bassoons', 'oboes'), tie=False)
    cmin = [0, 2, 3, 5, 7, 8, 11]

    def pcell(k):
        ci = h.info_at(t0 + 4 * k + 0.01)
        top = sc.N(sc.DEV4[k][2])
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
        if k < 12:                                  # one entry per bar, rising through the orchestra
            add(role, sc.cell(p1, top, p3, p4, a, fit(role, shift, top)), off=10, sf=[a + 0.5])
        if 8 <= k < 12:                             # stretto: a second entry on beat 3 overlaps the first
            r2 = second[k - 8]
            add(r2, sc.cell(p1, top, p3, p4, a + 2, fit(r2, 12 if r2 in ('flutes',) else 0, top)), off=8,
                sf=[a + 2.5])
        elif 12 <= k < 15:                          # one-beat heads (the leap alone), tossed every beat
            for j in range(4):
                r = frag_roles[j]
                sh = fit(r, 12 if r == 'flutes' else 0, top)
                add(r, [(a + j, 0.5, p1 + sh), (a + j + 0.5, 0.45, top + sh)], 'marcato', off=8, accent=False)
    tp = H(sc.DEV4[-2:-1], t0 + 60).tutti()
    hits(tp, [t0 + 60, t0 + 61], length=0.4, off=8, sf=True)
    brass(h, [t0 + 60, t0 + 61], length=0.4, off=8)

    # ================================================================================== RECAPITULATION
    # rec1: the first theme ff tutti, the half cadence held
    t0 = float(rec1.start)
    m, h = line(sc.REC1_MEL, t0), H(sc.REC1, t0)
    tp = h.tutti()
    theme_ff(m, [t0 + x for x in (0.5, 4.5, 8.5, 12.5, 16.5, 18.5, 20.5, 22.5)], clar=(-12, -4))
    drive(tp, t0, t0 + 28)
    hits(tp, [t0 + x for x in sc.T1FF_STABS], length=0.7, off=4, sf=True)
    brass(h, [t0 + b for b in range(0, 28, 4)] + [t0 + x for x in sc.T1FF_STABS], length=0.7)
    hits(tp, [t0 + 28], length=1.9, off=0)
    brass(h, [t0 + 28], length=1.9, roll=True)

    # cadenza: the oboe alone over a held G7, pp
    t0 = float(cad.start)
    add(H(sc.CADENZA, t0).chorale(STR, tie=True), off=-14, roles=UNDER)
    add('basses', [(t0, 4, 31)], off=-14)
    performances['cadenza'] = solo(oboe, sc.OBOE_CADENZA, t0, 'clarinet', 'verse', (42, 96), 51,
                                   vib_ct=8.0, peak_vib_ct=14.0)

    # rec2: the transition to G - syncopes, the hemiola, the horn call on G and its echo
    t0 = float(rec2.start)
    h = H(sc.REC2, t0)
    syncopes(sc.REC2[:4], t0)
    sc_.winds(H(sc.REC2[:4], t0), off=-4, roles=('flutes', 'oboes', 'clarinets', 'bassoons'))
    brass(h, [t0 + b + 1 for b in range(0, 16, 2)], length=0.6, horns=False, off=-2)
    hemiola(H(sc.REC2[4:10], t0 + 16, 'C major').tutti(), h, t0 + 16, (0, 3, 6, 8, 11, 14), [3, 3, 2, 3, 3, 2])
    horn_pedal(sc.REC2[10:], t0 + 32, 'C major', 'G', sc.HORN_CALL_C, sc.CLAR_ECHO_C, 'call2', 33)

    # rec3: the second theme in C major - violins I, then flute + oboe in octaves
    t0 = float(S['rec3'].start)
    h = H(sc.REC3, t0)
    m1 = line(sc.REC3_MEL1, t0, -3)
    add('violins1', m1, off=6, dur=0.96)
    pad = H(sc.REC3[:12], t0, 'C major').under(m1, STR)
    add(pad, off=-8, roles=UNDER[:2])
    add('cellos', fig(window(pad['cellos'], t0, t0 + 32), 'beats', every=2, gap=0.6), 'pizzicato', off=6)
    add('basses', fig(window(pad['cellos'], t0, t0 + 32), 'beats', every=4, gap=0.6), 'pizzicato', off=4,
        transpose=-12)
    add('horns', [(t0 + 16, 16, sc.N('G3')), (t0 + 16, 16, sc.N('C4'))], off=-14)
    m2 = line(sc.REC3_MEL2, t0 + 32, -3)
    sc_.double(m2, {'flutes': (12, 4), 'oboes': (0, 2), 'clarinets': (-12, -4)}, dur=0.95)
    acc = H(sc.REC3[12:], t0 + 32, 'C major').under([(n[0], n[1], n[2] + 12) for n in m2], STR)
    add('violins1', fig(acc['violins2'], 'pulse8', gap=0.45), 'staccato', off=-10, accent=False)
    add('violas', fig(acc['violas'], 'pulse8', gap=0.45), 'staccato', off=-10, accent=False)
    add('cellos', line(sc.REC3_CELLO_CELL, t0, -3), off=2)
    add('cellos', window(acc['cellos'], t0 + 48, t0 + 64), off=-2)
    add('basses', fig(window(acc['cellos'], t0 + 32, t0 + 64), 'beats', every=2, gap=0.6), 'pizzicato', off=4,
        transpose=-12)
    brass(h, [t0 + 56, t0 + 60], length=3.5, trumpets=False, timpani=False, off=-10)

    # rec4: the closing in C major, the codetta - and G7 breaks into Ab
    t0 = float(S['rec4'].start)
    h = H(sc.REC4, t0, 'C major')
    tp = closing(t0, h, line(sc.REC4_MEL, t0, -3), sc.REC4_BASS_CELL)
    cod =H(sc.REC4[10:13], t0 + 32, 'C major').chorale(STR, tie=True)
    add(cod, 'tremolo', off=-6, roles=UNDER[:2])
    add('violins1', window(cod['violins2'], t0 + 40, t0 + 44), 'tremolo', off=-4, transpose=12)
    hits(tp, [t0 + 44], length=3.5, off=8, sf=True)
    brass(h, [t0 + 40], length=3.5, off=-2, roll=True)
    brass(h, [t0 + 44], length=3.5, off=8, timpani=False)

    # ================================================================================== CODA
    # coda1: the second development - the Neapolitan, subito p, the chromatic climb
    t0 = float(S['coda1'].start)
    h = H(sc.CODA1, t0)
    st = h.chorale(STR, tie=True)
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
    add('cellos', fig(window(st['cellos'], t0, t0 + 32), 'beats', gap=0.8), 'staccato', off=0)
    add('cellos', window(st['cellos'], t0 + 32, t0 + 64), off=4)
    add('basses', st['cellos'], off=0, transpose=-12)
    add('bassoons', window(st['cellos'], t0 + 32, t0 + 64), off=-2)
    sc_.winds(H(sc.CODA1[8:], t0 + 32), off=-6, roles=('flutes', 'oboes', 'clarinets'))
    brass(h, [t0 + 4 * k for k in range(4)], length=3.5, off=-4, timpani=False)
    brass(h, [t0 + 48, t0 + 52], length=3.5, off=-4, timpani=False)
    add('timpani', [(t0 + 56, 8, 43)], 'roll', off=-6)
    add('trumpets', [(t0 + 56, 4, 67), (t0 + 60, 4, 67), (t0 + 56, 4, 72)], off=-8)

    # coda2: the triumph - the cell in C major ff, then the horn call hammered out over a tonic pedal
    t0 = float(S['coda2'].start)
    m, h = line(sc.CODA2_MEL, t0), H(sc.CODA2, t0, 'C major')
    tp = h.tutti()
    sync = [t0 + x for x in (0.5, 4.5, 8.5, 12.5, 16.5, 20.5)]
    theme_ff(m, sync, clar=(0, -2))
    # new colours for the triumph: the horns, cellos and bassoons sing the theme an octave under the violins II,
    # the natural trumpets take its C / E / G notes, the flutes ride an octave above the violins I
    sc_.double(window(m, t0, t0 + 16), {'horns': (-12, -2, {'dur': 0.9}), 'cellos': (-12, 2, {'sf': sync}),
                                        'bassoons': (-12, 0)}, dur=0.92)
    add('trumpets', [n for n in m if n[2] % 12 in (0, 4, 7) and 60 <= n[2] <= 79 and n[1] >= 0.5], 'marcato',
        off=-2, dur=0.85)
    add('violas', fig(window(tp['v5'], t0, t0 + 32), 'pulse8'), 'staccato', off=-2, accent=False)
    add('cellos', fig(window(tp['v7'], t0 + 16, t0 + 32), 'pulse8'), 'staccato', off=-4, accent=False)
    add('basses', fig(window(tp['v8'], t0, t0 + 32), 'beats', gap=0.7), 'staccato', off=0)
    add('bassoons', fig(window(tp['v7'], t0 + 16, t0 + 32), 'beats', gap=0.7), 'staccato', off=-2)
    hits(tp, [t0 + x for x in sc.T1FF_STABS] + [t0 + 30], length=0.7, off=4, sf=True)
    brass(h, [t0 + b for b in range(0, 32, 4) if b != 24] + [t0 + x for x in sc.T1FF_STABS], length=0.7,
          horns=False, trumpets=False)
    call = line(sc.CODA2_HORNS, t0)
    add('horns', call, 'marcato', off=4)
    up = [(n[0], n[1], n[2] + 12) for n in call]                      # the call an octave up: horns, trumpets
    add('horns', [n for n in up if n[2] <= 77], off=0)
    add('trumpets', [n for n in up if n[2] in TP_NATURAL], 'marcato', off=0)
    for r, vs in (('violins1', ('v1', 'v2')), ('violins2', ('v3', 'v4')), ('violas', ('v5', 'v6'))):
        add(r, [n for v in vs for n in window(tp[v], t0 + 32, t0 + 48)], 'tremolo', off=0)
    add('cellos', fig(window(tp['v7'], t0 + 32, t0 + 48), 'pulse8'), 'staccato', off=2, accent=False)
    add('basses', fig(window(tp['v8'], t0 + 32, t0 + 48), 'pulse8'), 'staccato', off=0, accent=False)
    sc_.winds(H(sc.CODA2[15:], t0 + 32, 'C major'), off=0, roles=('flutes', 'oboes', 'clarinets', 'bassoons'))
    add('timpani', [(t0 + 32, 7.5, 48), (t0 + 40, 3.5, 43), (t0 + 44, 3.5, 48)], 'roll', off=-8)

    # coda3: the hammered tonic chords, the last held in unison
    t0 = float(coda3.start)
    h = H(sc.CODA3, t0)
    tp = H(sc.CODA3[:-2], t0, 'C major').tutti()
    tl = h.timeline()
    for a, d, c in tl:
        if a >= t0 + 24:
            break
        hits(tp, [a], length=min(d, 2) * 0.85, off=6, sf=True)
    brass(h, [a for a, d, c in tl if a < t0 + 24], length=0.8, off=6)
    last = t0 + 24
    sc_.unison(last, 6, 'C', off=4)
    add('trumpets', [(last, 6, 67), (last, 6, 72)], off=0)
    add('violins2', [(last, 6, 67)], off=-2)
    add('violas', [(last, 6, 55)], off=-2)

    # ------------------------------------------------------------------------------------------ perform
    DEBUG.update(score=sc_, song=s, performances=performances)
    sc_.perform()
    # the hall rings on the fermatas and gives the bloom back where the music goes on
    orch.ring(o, intro.start + 1, length=1, db=3, back=intro.start + 2.75, back_beats=0.5)
    orch.ring(o, rec1.bar(7) + 0.5, length=1.5, db=3, back=cad.start, back_beats=0.5)
    orch.ring(o, coda3.bar(6) + 2, length=4, db=4)
    s.arc(ARC, within=ARC_IN)
    # master (the mastering engineer, MASTER.md): `agentsound master --platform dynamic` on the finished mix, profile
    # classical: broad tone only (the SSO sections read boxy around 1.6 kHz and light in the lows), the safety
    # limiter, -19.5 LUFS-I (the middle of the concert window), true peak <= -1 dBTP
    mastering.apply(s, eq={'low.freq': 100, 'low.gain': 3.0, 'low.q': 0.7071, 'high.freq': 8000, 'high.gain': 1.2,
                           'high.q': 0.7071, 'peak1.freq': 1600, 'peak1.gain': -2.8, 'peak1.q': 0.7},
                    limiter={'ceiling': -1.2, 'release': 250.0}, loudness_change=-1.4)
    return s
