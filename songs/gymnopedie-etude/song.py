"""Gymnopédie No. 1 (Erik Satie, 1888) - a piano étude: the public-domain score, played like a sensitive concert
pianist, measured against a reference recording (analysis only) to find the system's weaknesses. NOTES.md holds
the method, the measurement table before/after and the weakness list.

  bars  section  what happens
  1-4   intro    the rocking Gmaj7 / Dmaj7 accompaniment alone, pp
  5-16  a1       the melody (F#5 A5 G5 F#5 C#5 B4 C#5 D5 A4 | F#4 held four bars), twice
  17-21 b1       the low answer C#4 F#4 E4 inside the chords (F#m Bm Em Em Dm)
  22-31 mid1     the dorian middle part over a D pedal (C and F naturals), mf, the widest line
  32-39 c1       G5 F#5, B A B, C# D E twice, the cadence Am7 -> D major
  40-78          the same again; from bar 72 it turns to D minor: F5, B C F, E D C twice, F4, Am7 -> D minor

Performance (the point of the étude): pp-mp, the melody ~12 dB over the chords, a soft left hand, a pedal change on
every bar that catches the bass, the tempo breathing per phrase (rubato 'breath': on through the phrase, broader
into its end; ritardandi at the big cadences, a slower second half, the final ritardando and fermata), the chord
on beat 2 lingering (song.lilt: beat 2 +0.06 beats, a seeded pulse jitter), the bass ~25 ms before the melody, the
chords rolled 8-18 ms, no ornaments at all (restraint: the pianist's moves budget stays at zero).

Two tracks of one piano (the same patch, the same pedal): 'melody' (right hand) and 'accomp' (left hand), so the
report's dynamics ear judges the melody as the lead.

ETUDE_BEFORE=1 renders the performance with the tools as they were before the étude (rubato 'arch', no lilt, the
patch sampled/studio_piano as is) - the "before" column of NOTES.md.

CREDITS: see out/credits.txt (Headroom Piano by Bengt Nilsson, CC-BY 4.0).
"""
import math
import os
import random

from agentsound import *
from agentsound import romantic as rom

import satie_score as sc

BEFORE = os.environ.get('ETUDE_BEFORE') == '1'
ANALYSIS = {'profile': 'classical' if BEFORE else 'piano'}
METADATA = {'title': 'Gymnopédie No. 1 (Satie) – Étude', 'artist': 'AgentSound', 'album': 'Études',
            'genre': 'Classical', 'composer': 'Erik Satie (1866-1925)', 'year': 2026,
            'comment': 'Satie 1888 (public domain), performed from the score by the AgentSound pianist.'}
COVER = {'style': 'classical', 'title': 'GYMNOPÉDIE No. 1', 'subtitle': 'Satie – Étude', 'seed': 1888}

PIANO = 'sampled/studio_piano' if BEFORE else 'sampled/recital_grand'
ROOM = 'bus/ir_concert_hall'
TEMPO = 75.0
TEMPO2 = 70.0                     # the second half is played a little slower (the reference: ~70 vs ~74)
SECTIONS = [('intro', 4), ('a1', 12), ('b1', 5), ('mid1', 10), ('c1', 8),
            ('intro2', 4), ('a2', 12), ('b2', 5), ('mid2', 10), ('coda', 8)]

# Dynamics per phrase: (melody lo, melody hi, left-hand level). p for the song, mf for the middle part (the
# reference plays it ~6 dB over the first theme), the coda between (+4 dB); velocities.
DYN = {(1, 4): (0, 0, 44), (5, 8): (36, 72, 46), (9, 12): (40, 52, 44), (13, 16): (38, 78, 47),
       (17, 21): (34, 62, 46), (22, 26): (44, 90, 51), (26, 31): (46, 96, 53), (32, 36): (44, 90, 50),
       (37, 39): (36, 68, 45),
       (40, 43): (0, 0, 43), (44, 47): (36, 72, 45), (48, 51): (40, 52, 44), (52, 55): (38, 78, 47),
       (56, 60): (34, 62, 46), (61, 65): (44, 90, 51), (65, 70): (46, 96, 53), (71, 75): (52, 98, 52),
       (76, 78): (36, 66, 46)}
CHORD = 0.66                      # the chord on beat 2 against the bass level: pp under the melody
BASS = 1.08                       # the bass note against the hand's level (just under the melody)
BASS_LEAD_MS = 25.0               # the left hand's bass before the melody on shared downbeats
ROLL_MS = (8.0, 18.0)             # chords rolled from the bottom
CADENCE_ROLL_MS = 32.0            # the cadence chords (bars 38-39, 77-78) rolled wider, the right hand too


SCORE = rom.score(meter='3/4', phrases=sc.PHRASES)          # the phrases: rubato, dynamics, the hand's breath
bar = SCORE.bar                                               # 1-based score bar -> beat
MELODY = Clip([(bar(n) + beat, d, p, 64) for n, (_, _, mel, _) in sc.bars().items() for beat, q, d in mel
               for p in (q if isinstance(q, tuple) else (q,))])


def tempo_plan(s: Song) -> None:
    """The tempo breathes like the reference performance: phrase by phrase (rubato), broader into the D-pedal middle
    parts and at the big cadences, a slower second half, the lingering beat 2 (lilt) and the final ritardando."""
    # every phrase but the last (two phrases sharing a bar meet on its beat 3: the next one's pickup)
    SCORE.rubato(s, depth=0.04, phrase='arch' if BEFORE else 'breath', bars=(1, 75), overlap=2)
    # (the reference: ~75 BPM in the first theme, ~68 in the middle part, bar 31 -15 %, bars 36-37 -12..-20 %,
    # the second half ~64 -> 70, its middle part ~66, bar 70 -18 %, the end -30..-40 %)
    s.ritardando((bar(21), bar(22)), to=0.92)
    s.tempo_ramp(bar(23), bar(25), 69, curve='smooth')
    s.ritardando((bar(31), bar(32)), to=0.88)
    s.set_tempo(bar(32), 74)
    s.ritardando((bar(36), bar(38)), to=0.84)
    s.ritardando((bar(38) + 1, bar(40)), to=0.92)
    s.set_tempo(bar(40), 64)
    s.set_tempo(bar(44), TEMPO2)
    s.ritardando((bar(60), bar(61)), to=0.93)
    s.tempo_ramp(bar(62), bar(64), 66, curve='smooth')
    s.ritardando((bar(70), bar(71)), to=0.88)
    s.set_tempo(bar(71), 67)
    s.ritardando((bar(74), bar(78)), to=0.62, a_tempo=False)
    if not BEFORE:
        s.lilt((0, bar(78)), beats={2: 0.06}, jitter=0.05)


def build() -> Song:
    s = Song('Gymnopédie No. 1', tempo=TEMPO, key='D major', seed=7, time_sig='3/4', tail=9)
    for name, n in SECTIONS:
        s.section(name, bars=n)
    tempo_plan(s)

    # ------------------------------------------------------------------ sound and room: one piano, two hands
    s.bus('hall', ROOM)
    patch = patches.get(PIANO).with_mix(sends={'hall': -11})
    rh = s.track('melody', patch.with_fx(fx.eq({'hp.freq': 70, 'hp.slope': 12})))   # the right hand has no lows
    lh = s.track('accomp', patch)

    def ms(beat, x):                # milliseconds -> beats at the local tempo
        return x / 1000.0 * s.tempo_at(max(0.0, beat)) / 60.0

    rng = random.Random(1888)
    bars = sc.bars()

    # ------------------------------------------------------------------ the melody: touch per phrase
    for (a, b), at, shaped in SCORE.touch(MELODY, DYN, gap=16):
        for i, nt in enumerate(shaped):
            t = at + nt.start
            rank = sum(1 for o in shaped[:i] if abs(o.start - nt.start) < 1e-6)     # a chord: rolled upwards
            n = a + int((nt.start + 1e-6) // 3)
            spread = CADENCE_ROLL_MS if n in sc.CHORD_ON_ONE else 12.0
            rh.note(nt.pitch, t + ms(t, rng.uniform(-6, 6) + rank * spread), nt.dur - 0.04, nt.vel)

    # ------------------------------------------------------------------ the left hand: bass on 1, the chord on 2
    for n, (bass, chord, _, extra) in bars.items():
        a, b = SCORE.phrase_of(n)
        base = DYN[(a, b)][2]
        x = (n - a + 0.5) / (b - a + 1)                      # the hand breathes with the phrase
        f = 0.92 + 0.16 * math.sin(math.pi * x)
        t0 = bar(n)
        has_mel = any(beat == 0 for beat, _, _ in bars[n][2])
        tb = t0 - (ms(t0, BASS_LEAD_MS) if n > 1 and has_mel else 0.0)
        lh.note(bass, tb, 2.95 + (t0 - tb), round(base * f * BASS * rng.uniform(0.95, 1.05)))
        on_one = n in sc.CHORD_ON_ONE
        tc = t0 + (0.0 if on_one else 1.0)
        roll = ms(tc, CADENCE_ROLL_MS if on_one else rng.uniform(*ROLL_MS))
        cv = base * f * (0.9 if on_one else CHORD)
        for i, q in enumerate(sorted(chord, key=note)):
            lh.note(q, tc + i * roll, (3.0 - (tc - t0)) - 0.06, round(cv * rng.uniform(0.94, 1.06)))
        for beat, qs, d in extra:
            for i, q in enumerate(qs):
                lh.note(q, t0 + beat + i * roll, d - 0.05, round(base * f * 0.75))

    # ------------------------------------------------------------------ pedal: a change on every bar
    pts = [(0.0, 1.0, 'step')]
    for n in range(2, 79):
        t0 = bar(n)
        pts += [(t0 + 0.06, 0.0, 'step'), (t0 + 0.3, 1.0, 'step')]
    pts.append((bar(79) + 5.0, 0.0, 'step'))
    for t in (rh, lh):
        t.automate('instrument.pedal', pts)

    s.fermata(bar(78), hold=2, length=3)
    s.master.add(fx.limiter(ceiling=-1.0, gain=4.5))   # a safety limiter; ~-20 LUFS
    return s
