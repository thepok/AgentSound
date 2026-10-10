# Letters to the Morning - arrangement

A-flat major, 4/4, 75 BPM, 69 bars. Right hand written in notation (`RH` in song.py, played by
`romantic.score(...).perform`: touch per phrase lo 52 / hi 100, lean on long notes, cantabile, melody rubato, a
breath of 0.35 beats at every phrase end, cap 106; the notes under the melody in its chords x0.78). Left hand:
per bar a chord symbol + a broken-chord figure in 8ths (`LH`, `FIG`): the bass in Db2-C3 rings through the chord,
a ladder of chord tones above it (5th / octave / 10th / 12th), capped at G4; each figure crests on its top note, every phrase swells +-8 %.

| bars | section | harmony | right hand | left hand | dyn |
|---|---|---|---|---|---|
| 1-4 | intro | Ab(add9) Dbmaj7 Fm7 Ebsus4-Eb | rests, then the hook's head at C6-Ab6 | flow / flow / rock / held | pp-p |
| 5-12 | A1 | Ab Eb/G Fm7 Db(add9) Ab/C Db Bbm7 Ebsus4-Eb | the theme Ab4-F5 as a plain line (the contrast), 2-bar question / answer, a rest at each end, one turn (bar 11) | rock / lilt / flow, held at bars 8 and 12 | p-mp |
| 13-20 | A2 | as A1, Dbmaj7, Bbm7-Eb7 -> Ab | the answer higher (Ab5, G5) with sixths / thirds under its long notes, a turn (bar 19), cadence on I | flow / rock / lilt, colour tone + ring at bar 16, 'half' at the cadence | p-mf |
| 21-28 | B1 | Fm Db Ab Eb, then Dbmaj7 Ab/C Bbm7-Dbm6 Ebsus4-Eb | the hook: r C F G Ab~ / G F Eb F Db~, sequenced up to C6; second half with octaves under the held notes, Fb->Eb over Dbm6 (the borrowed iv) | flow / lilt / ring (bar 24) / rock, held at 28 | mp-mf |
| 29-32 | inter | Ab(add9) Dbmaj7 Fm7 Ebsus4 | two echoes of the hook head up high, two empty bars | open / quarters / a rolled chord | pp |
| 33-40 | A3 | as A1, -> Bbm7 C7/E | the theme with sixths / thirds under its first-half long notes, the pickup C5-E5 | rock / lilt / flow, 'up' climbing in bar 40 | p-mp |
| 41-48 | build | Fm Db Bbm7 C7sus4-C7 Fm Dbmaj7 Gbmaj7 Ebsus4-Eb | the melody an octave up (to Db6), Gbmaj7 = bVII colour, an inhale (rest) in bar 48 | flow / lilt, held at 44, then 'big' (bass octave, two octaves of chord) | mp-f |
| 49-56 | climax | Dbmaj7 Eb/Db Ab/C Eb/Bb (a falling bass) Fm Db Bbm7-Dbm6 Ebsus4-Eb7 | the hook in chords, peaks raised: Db6, Eb6, F6 (bar 53 ff, over vi); the Fb6 turn; a held Eb7 | big, 16th sweeps at the peaks (51, 53); rolled Eb7 under the fermata | f-ff-mf |
| 57-64 | A4 | as A1, Bbm7-Eb7 -> Fm7 (deceptive) | the theme soft, a turn on F5 (bar 59), its answer bent (Eb5-F5, a sixth) | quarters, then lilt / rock, 'half' | p-pp |
| 65-69 | coda | Dbmaj7 Dbm6 Ab/Eb Ebsus4-Eb Ab(add9) | the hook head at Ab5-F6, the Fb6 -> Eb6 sigh, the head once more in the middle, a rolled C5-Eb6 chord | open / rock / a rolled chord | pp |

Tempo: phrase rubato per phrase (`breath`, `breath`, `lean`, depth 0.05), ritardandi into every cadence (0.8) and
the half-way rests (0.9), into the interlude's end, an inhale before the climax, a big ritardando (0.72) into the
climax's fermata (Eb7, +2.5 beats), A4 at 70, the coda at 66 with a final ritardando and a fermata on the last chord.
Pedal: a change with every harmony (`rom.pedal_changes`, up 110 ms with the new bass), both hands. `s.lilt`: beat 3 lingers +0.03 beats with a seeded jitter of 0.03 (a breathing pulse, both hands).

Originality: the theme (stepwise, pickup into a dotted quarter), the hook rhythm (r + three rising 8ths into a
half note / four falling 8ths into a half note) and the left-hand figures are written for this piece; no figure of
the model (its 16th-note neighbour-tone oscillation, its A-major vi-IV-I-V loop texture) is used.

Player wish, since done in the tools (feat/endless-piano): `romantic.Score.perform(figures=[(at, beats, chord, figure)])`
plays broken-chord left-hand figures from `pianist.FIGURES` (this piece's FIG table), and `inner=0.78` voices the right
hand's own chords to the top (used here now); the song keeps its own left-hand code.
