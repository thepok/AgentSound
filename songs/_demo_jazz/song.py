"""Jazz toolkit demo: 'Last Call at the Vanguard Annex' - an original 32-bar AABA tune in Bb, medium swing (138 BPM),
tenor sax quartet (piano, upright bass, brushes), GeneralUser GS sounds. Build:
    python -m agentsound build songs/_demo_jazz --profile default

Form (82 bars, ~2:25):
  intro   4   piano block chords over a dominant pedal (iii-VI-ii-V), brushes sweeping
  head   32   AABA: tenor sax melody; bass in two through A1 / A2, walking from the bridge; piano comps in the
              melody's rests (Charleston cells, rootless A/B voicings); brushes with fills at the phrase ends
  piano  32   the piano's chorus, Red Garland style over short left-hand shells on the & of 2 and 4: the tune in
              locked-hands block chords, a bebop solo line (jazz.solo_line, opening on the head's motif) through
              A2 and the bridge, the last A as a block-chord shout with the drummer on the ride
  out     8   head out: the sax plays the last A once more, looser
  tag     4   the turnaround twice, a cymbal swell
  end     2   Cm9 F13 | Bbmaj7#11, bass on the root, the room ringing out
Shows jazz.band, comp, walking_bass (two-feel, walking, pedal), brushes / ride_pattern / brush_fill, horn_line
(swing, lay-back, legato phrases, breaths, scoops, falls, delayed vibrato, swells), paraphrase, block_chords and
solo_line.
"""
from agentsound import *
from agentsound import jazz


# The head, concert pitch, one list per bar: (beat in the bar, length in beats, pitch). Written straight: the feel
# swings it (horn_line for the sax, the track grooves for the piano).
A_FRONT = [
    [(0.5, 0.5, 'D4'), (1.0, 0.5, 'F4'), (1.5, 2.5, 'A4')],                               # Bbmaj7
    [(0.5, 0.5, 'G4'), (1.0, 0.5, 'F4'), (1.5, 0.5, 'D4'), (2.0, 1.5, 'Bb3')],            # Gm7
    [(0.5, 0.5, 'Eb4'), (1.0, 0.5, 'G4'), (1.5, 2.5, 'Bb4')],                             # Cm7
    [(0.5, 0.5, 'A4'), (1.0, 0.5, 'G4'), (1.5, 0.5, 'Eb4'), (2.0, 1.5, 'C4')],            # F7
]
A1_BACK = [
    [(0.0, 0.5, 'F4'), (0.5, 0.5, 'E4'), (1.0, 0.5, 'F4'), (1.5, 0.5, 'A4'), (2.0, 0.5, 'Ab4'), (2.5, 1.5, 'F4')],
    [(0.0, 1.5, 'Eb4'), (1.5, 0.5, 'D4'), (2.0, 0.5, 'C4'), (2.5, 1.5, 'A3')],            # Cm7 F7
    [(0.0, 2.0, 'Bb3'), (2.5, 0.5, 'Ab4'), (3.0, 1.0, 'G4')],                             # Bbmaj7 G7alt
    [(0.0, 1.0, 'Eb4'), (1.0, 0.5, 'C4'), (1.5, 0.5, 'A3'), (2.0, 1.0, 'C4')],            # Cm7 F7
]
A2_BACK = [
    [(0.5, 0.5, 'Ab4'), (1.0, 0.5, 'G4'), (1.5, 0.5, 'F4'), (2.0, 0.5, 'D4'), (2.5, 1.5, 'Ab4')],  # Fm7 Bb7
    [(0.0, 2.0, 'G4'), (2.0, 0.5, 'Gb4'), (2.5, 1.5, 'F4')],                              # Ebmaj7 Ab7
    [(0.0, 1.0, 'F4'), (1.0, 0.5, 'E4'), (1.5, 0.5, 'D4'), (2.0, 0.5, 'B3'), (2.5, 1.5, 'Ab4')],   # Dm7 G7b9
    [(0.0, 3.0, 'F4')],                                                                   # Bb6 Bb7
]
BRIDGE = [
    [(0.0, 3.0, 'G4'), (3.0, 0.5, 'F4'), (3.5, 0.5, 'G4')],                               # Ebmaj7
    [(0.0, 1.5, 'Bb4'), (1.5, 0.5, 'Gb4'), (2.0, 2.0, 'F4')],                             # Ebm7 Ab7
    [(0.0, 3.0, 'A4'), (3.0, 0.5, 'G4'), (3.5, 0.5, 'A4')],                               # Dm7
    [(0.0, 1.5, 'B4'), (1.5, 0.5, 'Ab4'), (2.0, 2.0, 'F4')],                              # G7b9
    [(0.0, 3.0, 'G4'), (3.0, 0.5, 'F4'), (3.5, 0.5, 'G4')],                               # Cm7
    [(0.0, 1.5, 'A4'), (1.5, 0.5, 'Eb4'), (2.0, 1.5, 'C4')],                              # F7
    [(0.5, 0.5, 'D4'), (1.0, 0.5, 'F4'), (1.5, 0.5, 'A4'), (2.0, 0.5, 'B4'), (2.5, 1.5, 'F4')],    # Dm7 G7
    [(0.0, 1.0, 'Eb4'), (1.0, 0.5, 'D4'), (1.5, 0.5, 'C4'), (2.0, 0.5, 'A3'), (2.5, 1.0, 'C4')],   # Cm7 F7
]
A3_BACK = [
    [(0.0, 0.5, 'F4'), (0.5, 0.5, 'E4'), (1.0, 0.5, 'F4'), (1.5, 0.5, 'A4'), (2.0, 0.5, 'Ab4'), (2.5, 1.5, 'F4')],
    [(0.0, 1.5, 'Eb4'), (1.5, 0.5, 'D4'), (2.0, 0.5, 'C4'), (2.5, 1.5, 'A3')],            # Cm7 F7
    [(0.5, 0.5, 'C4'), (1.0, 0.5, 'D4'), (1.5, 0.5, 'Eb4'), (2.0, 0.5, 'E4'), (2.5, 1.5, 'F4')],   # Cm7 F7
    [(0.0, 4.0, 'D4')],                                                                   # Bb6
]
INTRO_RH = [   # the head's pickup figure, answered: played in drop-2 block chords
    [(0.5, 0.5, 'F4'), (1.0, 0.5, 'A4'), (1.5, 2.0, 'C5')],                               # Dm7
    [(0.5, 0.5, 'Ab4'), (1.0, 0.5, 'B4'), (1.5, 2.0, 'D5')],                              # G7b9
    [(0.5, 0.5, 'Eb5'), (1.0, 0.5, 'D5'), (1.5, 1.0, 'C5'), (2.5, 0.5, 'Bb4'), (3.0, 1.0, 'G4')],  # Cm7
    [(0.0, 2.0, 'A4')],                                                                   # F7
]
END_RH = [    # a soft arpeggio up to the #11 over the final chord
    [],
    [(0.0, 1 / 3, 'F4'), (1 / 3, 1 / 3, 'A4'), (2 / 3, 1 / 3, 'D5'), (1.0, 1 / 3, 'E5'), (4 / 3, 1 / 3, 'A5'),
     (5 / 3, 2.3, 'D6')],
]

A1_CHORDS = 'Bbmaj7 Gm7 Cm7 F7 | Dm7:0.5 G7b9:0.5 Cm7:0.5 F7:0.5 Bbmaj7:0.5 G7alt:0.5 Cm7:0.5 F7:0.5'
A2_CHORDS = 'Bbmaj7 Gm7 Cm7 F7 | Fm7:0.5 Bb7:0.5 Ebmaj7:0.5 Ab7:0.5 Dm7:0.5 G7b9:0.5 Bb6:0.5 Bb7:0.5'
B_CHORDS = 'Ebmaj7 Ebm7:0.5 Ab7:0.5 Dm7 G7b9 | Cm7 F7 Dm7:0.5 G7:0.5 Cm7:0.5 F7:0.5'
A3_CHORDS = 'Bbmaj7 Gm7 Cm7 F7 | Dm7:0.5 G7b9:0.5 Cm7:0.5 F7:0.5 Cm7:0.5 F7:0.5 Bb6'
TAG_CHORDS = 'Cm7:0.5 F7:0.5 Dm7:0.5 G7b9:0.5 Cm7:0.5 F7:0.5 Dm7:0.5 G7alt:0.5'


def bars_to_clip(bars, vel=92) -> Clip:
    notes = [(i * 4 + t, d, p, vel) for i, bar in enumerate(bars) for t, d, p in bar]
    return Clip(notes, length=len(bars) * 4)


def build() -> Song:
    s = Song('Last Call at the Vanguard Annex', tempo=138, key='Bb major', seed=11)
    intro = s.section('intro', bars=4)
    a1, a2, bridge, a3 = (s.section(n, bars=8) for n in ('A1', 'A2', 'bridge', 'A3'))
    p1, p2, pb, p3 = (s.section(n, bars=8) for n in ('piano A1', 'piano A2', 'piano bridge', 'piano A3'))
    out = s.section('out', bars=8)
    tag = s.section('tag', bars=4)
    end = s.section('end', bars=2)

    b = jazz.band(s, sax=True, sampled_sounds=False)   # GeneralUser piano / bass / brush kit / tenor, room + plate,
                                                        # swing by tempo (the GM brush keymap below)

    # material
    prog = {'A1': s.prog(A1_CHORDS), 'A2': s.prog(A2_CHORDS), 'B': s.prog(B_CHORDS), 'A3': s.prog(A3_CHORDS)}
    intro_prog = s.prog('Dm7 G7b9 Cm7 F7')
    tag_prog = s.prog(TAG_CHORDS)
    end_prog = s.prog('Cm9:0.5 F13:0.5 Bbmaj7#11')
    mel = {'A1': bars_to_clip(A_FRONT + A1_BACK), 'A2': bars_to_clip(A_FRONT + A2_BACK),
           'B': bars_to_clip(BRIDGE), 'A3': bars_to_clip(A_FRONT + A3_BACK)}

    # --- tenor sax: the head (A3 already a little looser) and the last A again as the head out
    head = (mel['A1'].velocity(0.9) + mel['A2'].velocity(0.92) + mel['B']
            + jazz.paraphrase(mel['A3'], seed=3, key=s.key).velocity(1.04))
    # GeneralUser's tenor has its own delayed vibrato (+-19 ct at ~5 Hz from 0.4 s): no second one on top
    # ('expression' replaces 'level' once the sampler update brings the expression control)
    jazz.horn_line(head, s.tempo, param='level', vibrato=False, seed=5).place(b.sax, a1)
    head_out = jazz.paraphrase(mel['A3'], seed=9, anticipate=0.4, embellish=0.3, key=s.key)
    jazz.horn_line(head_out, s.tempo, param='level', vibrato=False, seed=6).place(b.sax, out)

    # --- piano right hand: block-chord intro, the piano chorus, a last arpeggio
    b.piano.play(jazz.block_chords(bars_to_clip(INTRO_RH, 40), intro_prog, style='drop2'), intro)
    # the piano's chorus: the tune in locked hands (Shearing / Garland: 4-way close + the melody doubled an octave
    # down), then two A-B solo phrases built on the head's opening motif, then the last A as a block-chord shout
    for sec, part, seed, vel in ((p1, 'A1', 11, 38), (p3, 'A3', 14, 50)):
        line = jazz.paraphrase(mel[part], seed=seed, anticipate=0.35, embellish=0.25, key=s.key).octave(1)
        b.piano.play(jazz.block_chords(line.with_vel(vel), prog[part], style='locked', min_dur=0.5, vel=0.78), sec)
    motif = bars_to_clip(A_FRONT[:1]).octave(1)
    for sec, part, seed, dens, inten, vel in ((p2, 'A2', 21, 0.55, 0.45, 48), (pb, 'B', 22, 0.7, 0.6, 52)):
        b.piano.play(jazz.solo_line(prog[part], key=s.key, register=('D4', 'D6'), density=dens, intensity=inten,
                                    motif=motif, motif_prob=0.5, vel=vel, seed=seed), sec)
    b.piano.play(bars_to_clip(END_RH, 56), end)

    # --- piano left hand: comping (rootless under the sax, answering its phrases; shells under the block chords)
    under = ('A2', 'G4')
    # (no left hand in the intro: the block chords carry the harmony)
    for sec, part, style, dens, inten, seed in ((a1, 'A1', 'charleston', 0.4, 0.4, 2), (a2, 'A2', 'charleston', 0.4,
                                                0.42, 3), (bridge, 'B', 'swing', 0.55, 0.5, 4),
                                                (a3, 'A3', 'charleston', 0.55, 0.55, 5)):
        answer = head.slice(sec.start - a1.start, sec.end - a1.start)
        b.comp.play(jazz.comp(prog[part], style=style, density=dens, intensity=inten, answer=answer, seed=seed,
                              register=under), sec)
    for sec, part, seed, inten in ((p1, 'A1', 6, 0.35), (p2, 'A2', 7, 0.42), (pb, 'B', 8, 0.48), (p3, 'A3', 9, 0.55)):
        b.comp.play(jazz.comp(prog[part], style='garland', voicing='shell', density=0.55, intensity=inten,
                              seed=seed, register=('D3', 'D5')), sec)
    b.comp.play(jazz.comp(prog['A3'], style='charleston', density=0.5, intensity=0.5, answer=head_out, seed=10,
                          register=under), out)
    b.comp.play(jazz.comp(tag_prog, style='garland', density=0.6, intensity=0.55, seed=11, register=under), tag)
    b.comp.play(jazz.comp(end_prog, style='ballad', density=0.3, intensity=0.35, seed=12, register=('C3', 'C5')), end)

    # --- bass: pedal under the intro, two-feel for A1 / A2, then walking to the end
    b.bass.play(jazz.walking_bass(intro_prog, key=s.key, feel='two', pedal=[(0, 12, 'F2')], vel=72, seed=1), intro)
    b.bass.play(jazz.walking_bass(prog['A1'] + prog['A2'], key=s.key, feel='two', skip=0.15, vel=86, seed=2), a1)
    walk = (prog['B'] + prog['A3'] + prog['A1'] + prog['A2'] + prog['B'] + prog['A3'] + prog['A3'] + tag_prog)
    b.bass.play(jazz.walking_bass(walk, key=s.key, vel=92, seed=3), bridge)
    b.bass.note('Bb1', end, dur=7, vel=76)

    # --- drums: brushes all the way (fills at the phrase ends), the ride for the piano's last A, a swell at the end
    b.drums.play(jazz.brushes(4, style='two', fills=False, vel=0.6, seed=1), intro)
    b.drums.play(jazz.brushes(16, style='two', phrase=8, vel=0.9, seed=2), a1)
    b.drums.play(jazz.brushes(16, style='medium', phrase=8, vel=1.0, seed=3), bridge)
    b.drums.play(jazz.brushes(8, style='medium', phrase=8, vel=0.85, seed=4), p1)
    b.drums.play(jazz.brushes(16, style='medium', phrase=8, vel=0.95, seed=41), p2)
    b.drums.play(jazz.brushes(8, style='medium', phrase=8, ride=0.9, vel=1.1, seed=5), p3)
    b.drums.play(jazz.brushes(8, style='medium', phrase=8, vel=1.0, seed=6), out)
    b.drums.play(jazz.brushes(4, style='medium', fills=False, vel=0.95, seed=7), tag)
    b.drums.play(jazz.brush_fill('swell', 2, vel=(20, 70)), tag.bar(-1, 2))
    b.drums.play(jazz.brushes(2, style='ballad', fills=False, kick=None, vel=0.7, seed=8), end)

    # --- let the room ring out over the final chord
    for t in (b.comp, b.piano):
        t.automate('send.room', ramp(end.start, end.bar(1), -15, -5))
    b.piano.automate('send.plate', ramp(end.start, end.bar(1), -20, -8))

    s.master.add(fx.tape(speed='15', drive=1.5, wow=0.05, flutter=0.05),
                 fx.eq({'high.freq': 10000, 'high.gain': 1.5}),
                 fx.limiter(gain=3.0, release=200, ceiling=-1.2))
    return s
