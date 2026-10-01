# Unbowed - arrangement

Frame: C minor -> C major, 4/4, straight. Introduction Adagio molto q=56 (rubato, three fermatas), Allegro con brio
q=148, cadenza Adagio q=52; 202 bars, ~6.5 min. Score data: `score.py`; orchestration and performance: `song.py`.

## The cell (the hook)

`G4:.5 Eb5:1 D5:.5 C5:1` - an 8th leaping up a sixth onto a quarter that starts on the off-beat (the sforzando falls
between the beats: Beethoven's weak-beat accent built into the motif), a step down, a landing. Not the Fifth's
short-short-short-long (no repeated notes, a syncopation instead of a downbeat), not the Eroica's chords.

| where | how the cell appears |
|---|---|
| intro | in slow motion on the violins pp (G4 Eb5:2 D5 / C5 B4), then its sequence |
| t1 | the first theme: cell (i) - its answer on V - the cell on iv - cadence; fragmentation into half-bar cells; Ger+6 cadence |
| t1ff | the same ff in octaves, the answer bent to the Neapolitan (Db) |
| trans | in the cellos / basses / bassoons under syncopated chords |
| t2 | its rhythm (8th, quarter, 8th, quarter) in the cellos under the restatement of the lyrical theme |
| closing | turned to Eb major: the closing theme |
| dev1 | fragmented, tossed between winds (tonic of each key) and violins (its dominant) through falling thirds |
| fugato | the subject: two cells, a running bar, a cadence |
| pedal | climbing in imitation from the cellos to the flutes over the G pedal |
| coda1 | in sequence through Ab - Db (the Neapolitan) - C minor |
| coda2 | turned to C MAJOR, ff tutti with horns doubling: the triumph |

## Form

| section | bars | tempo | key / harmony | dyn | who plays | what happens |
|---|---|---|---|---|---|---|
| intro | 10 | q=56 rubato | C minor: unison C - Ab - Db/F - G7/F - Cm/Eb - Fm G7 - Fm/Ab Bdim7 G - unison Ab - Db - Ger+6 (Ab7) - G (pedal) - G7 | ff / pp contrasts, cresc | all unison; winds pp chords (WINDS8); violins pp cell + strings; bassoon sigh; G pedal: basses / cellos tremolo, timpani roll, horns, flute + violins climb | two unison blows (fermatas) answered pp by bVI and the Neapolitan; the dominant pedal grows into a G7 fermata |
| t1 | 8 | q=148 | i - V6/5 - iv6 viio4/2 - i6/4 V i - VI III6 - iv i6 - VI Ger+6 V - V (GP) | p, cresc | violins I theme, violins II / violas 8th drive, cellos quarters, basses halves; winds + horns at the cadence | the first theme as a sentence, a half cadence, two beats of silence |
| t1ff | 8 | | i - V6/5 - N6 (Db/F) - iv6 V - VI III6 - iv i6 - VI Ger+6 V - i i | ff | tutti: theme in 3 octaves (violins I 8va, violins II, flutes 8va, oboes), violas / cellos 8ths, basses / bassoons quarters, horns, trumpets, timpani; tutti chords in the rests | the counterstatement, sforzandi on the syncopes, a long - short - long cadence on C minor |
| trans | 16 | | Cm - G7/B - C7/Bb - F/A - Fm/Ab - Eb/G - Ab - F7/A, hemiola Bb/D Eb F7 Gm Cm7 F7, Eb/Bb Bb7 (pedal) | f, ff, dim. p | strings syncopes (sf between the beats), cello / bass / bassoon cell, winds chords, trumpets + timpani on the weak beats; hemiola tutti; Bb pedal: tremolo, solo horn call, clarinet echo | weak-beat sforzandi, the hemiola (3+3+2), the horn call announces Eb |
| t2 | 16 | | Eb: I V6 I - IV V7 - V; I V7/IV - IV6 I6/4 V7 I; restatement ... V7 - bVI (Cb) - iv6 (Abm/Cb) V7 - I6/4 V7 I | p dolce, mp | solo clarinet (hornist), strings pad, cello pizz; violins I + flute 8va, violas / violins II 8ths, the cell rhythm in the cellos, winds on the Cb turn | the lyrical second theme in the relative major; the deceptive turn to Cb |
| closing | 12 | | Eb - Ab/C - Bb7/D - Eb; hemiola Ab Bb7/Ab Eb/G Ab Bb7 Eb; codetta Eb Ab/Eb Eb, one blow | ff, p, ff | violins in octaves + flutes / oboes, brass / timpani / clarinets / bassoons on beats 2 and 4; hemiola tutti; codetta: cellos / basses cell, oboe / flute answers | the cell in major, weak-beat sforzandi, a hemiola cadence, one blow and a silence |
| dev1 | 12 | | Cm G7/B - Ab Eb7/G - Fm C7/E - Db Ab7/C - Bbm F7/A - Bbm/Db C7 | mf -> f | winds (oboes + clarinets, flutes later) and violins alternate the cell; tremolo strings; brass on the syncopes | falling-third sequence through distant keys |
| fugato | 16 | | F minor / C minor (subject harmony: Fm C7/E Db Bbm7 C7 Fm Fm/C C7 Fm) | mf -> f | entries cellos (+ basses), violas (answer), violins II, violins I; bassoons, clarinets, oboes double the late voices; horns F/C; timpani roll | free voices voiced by `voicing.voice`, given motion by `arpeggiate` / `passing_eighths`, checked by `voicing.check` |
| storm | 8 | | Db - Bbm/Db - Ebm/Gb - Db7/Ab -> Gb - Db/F Gb - Ebm/Gb - Ger+6 (Ab7) | ff, subito pp | tutti syncopes, winds + brass on beats 2 / 4, cellos / basses 8ths; pp: clarinet solo then flute (second-theme head in Gb), strings pad | the hammered climax of the development a tritone from home; subito pp |
| pedal | 16 | | over G: Cm/G G7 ... Ab/G G7 Fm/G G7 Cm/G Bdim7/G ... G7 (GP) | pp -> ff | basses 8ths on G, cellos, timpani roll from bar 9, horns G, tremolo violas / violins II, winds chords from bar 9; the cell in imitation cellos -> violas -> violins -> clarinets -> oboes -> flutes | the long dominant preparation and crescendo; two hammered G7 chords, a breath |
| rec1 | 8 | | as t1 | ff | tutti as t1ff (clarinets added) | the first theme ff (it was p): varied by orchestration; the half cadence held (fermata, the hall blooms and is given back) |
| cadenza | 2 | q=52 rubato | G7 - Fm/Ab - G | p | solo oboe (hornist), strings pp | the oboe's short cadenza (fermata on its last note) |
| rec2 | 12 | q=148 | Cm G7/B C7/Bb F/A, hemiola Fm/Ab C/G D7/F# G Am D7, G pedal (C/G G7) | f, ff, p | as trans; solo horn call on G, clarinet echo | the transition rewritten to reach G |
| rec3 | 16 | | the second theme in C major (deceptive turn to Ab) | p, mp | violins I (dolce) over pad and pizz; flutes 8va + oboes + clarinets 8vb, the cell rhythm in the cellos | the lyrical theme in the tonic major |
| rec4 | 12 | | closing in C major; codetta C F/C - G7 - Ab (bVI) | ff, p, cresc, ff | as closing; the last bar tutti on Ab, sf | the shock: G7 breaks into Ab |
| coda1 | 16 | | Ab Fm/Ab Db Bbm/Db - G7/D Cm/Eb Fm/Ab G7 - Cm G/D Cm/Eb C7/E Fm F#dim7 Cm/G G7 | f, subito p, cresc -> ff | the cell in winds / violins, tremolo strings, the chromatic climbing bass (C D Eb E F F# G), trumpets + timpani roll at the end | the second development: Neapolitan, the struggle returns, the climb (a small ritardando into the arrival) |
| coda2 | 12 | | C: I V6/5 IV6 V6/5 I6/4 V I - vi IV V V7 - I6 IV V7 I; tonic pedal C G7 C | ff | tutti, the theme in C major (horns double it), then the horn call ff in horns + trumpets over tremolo strings and timpani rolls | the triumph |
| coda3 | 8 | | C C G7 C C G7 C G7 C C - unison C | ff | tutti hammered chords, timpani, trumpets | hammered tonic chords; the unison C under a fermata, the hall rings |

## Revision 1 (A&R round 1)

- dev1: bars 1-8 one cell per bar (winds on each key's tonic, violins answering on its dominant - the answers in F
  minor and Db major INVERTED: the leap falls a sixth, the steps rise); bars 9-12 fragmentation: half-bar heads
  (8th, quarter, 8th) in oboes + flutes, echoed by the violins two beats later.
- pedal: bars 1-8 one entry per bar rising through the orchestra; bars 9-12 stretto (a second entry on beat 3
  overlaps the first: oboes, violins II, flutes, violins I); bars 13-15 one-beat heads (the leap alone) tossed
  every beat between violins I, flutes, oboes, violins II - the music speeds up with the crescendo.
- fugato: the basses double only the cellos' long notes (the subject's held notes and the free voice), 8 velocity
  softer - no more running 8ths in the basses.
- coda2: new colours for the triumph - horns, cellos and bassoons sing the theme an octave under the violins II,
  the natural trumpets take its C / E / G notes, flutes an octave above the violins I; no brass hit under the
  theme's bar 7.
- t1ff ends long - short - long (C minor, quarter, 8th, quarter) instead of two blows; the exposition's closing
  ends with ONE Eb blow and a silence (two Eb tutti chords a beat apart read as the Eroica's opening gesture).
- Dynamics map: the earlier fortissimos at velocity 104-112, the coda at 126-127, the pp floor 42-58; the
  mix engineer's conductor's arc (MIX.md) carries the rest.

## Revision 2 (A&R round 2)

- fugato: the winds double the ENTERING subject only - bassoons with the violins II's entry (bars 9-12), clarinets
  and oboes with the violins I's (bars 13-16) - never a free voice (the clarinets had buried the last entry).
- pedal: the crescendo is played - every held part (tremolo strings, horns, wind chords, timpani rolls) re-attacks
  each bar at the map's rising level (held notes kept their first level: bars 9-15 climbed only ~2 LU); the map
  58 -> 90 -> 122 over bars 9-16; the one-beat heads marcato. Bars 1-8 -34.9 -> -30.9 LUFS, bars 9-15 -24.4 ->
  -18.5, the hammered G7 -15.5.

## Transitions

- intro -> t1: G7 fermata (the hall rings), then the Allegro begins p in the strings.
- t1 -> t1ff: two beats of general pause, ff entry.
- trans -> t2: the horn call and the clarinet echo on the Bb pedal, diminuendo.
- closing -> dev1: one ff blow and a silence, then the cell starts the sequence.
- fugato -> storm: the fugato's crescendo breaks into the syncopated tutti.
- storm -> pedal: subito pp, the German sixth resolves onto the G pedal.
- pedal -> rec1: two hammered G7 chords, a breath, ff.
- rec1 -> cadenza -> rec2: the held half cadence (fermata), the oboe alone, a tempo f.
- rec4 -> coda1: G7 breaks into Ab ff.
- coda1 -> coda2: a ritardando on the last two beats of G7 (a tempo), ff C major.

## Players

- `orch.perform` for every orchestral role: articulation marks per note (sustain, staccato, marcato for the
  sforzandi, tremolo, pizzicato; missing ones fall back), velocities -> the dynamics lane, long notes early.
- Dynamics: one map for the whole piece (`DYNAMICS`), `touch()` phrase arcs per melodic role on top, sforzandi +16
  velocity, downbeat accents; brass / timpani accents on the downbeats.
- `hornist.arrange(..., style='classical')`: the horn calls (family trumpet, no vibrato), the clarinet's second
  theme and its Gb echo (family clarinet), the oboe cadenza (family clarinet with a light vibrato).
- `voicing`: chorale() for the string pads (STRINGS with a melody-aware top), the wind pairs (WINDS8, unison
  doublings allowed), the tutti chords (TUTTI, 8 voices distributed over the sections); voice() + arpeggiate() +
  passing_eighths() for the fugato.

## Needs from sound design

Sections with live dynamics (the SSO / VPO lanes) and articulations sustain / staccato / marcato / tremolo /
pizzicato for the strings; winds sustain / staccato; horns / trumpets sustain / marcato / staccato; timpani hit /
roll on C3 / G2; solo horn, clarinet, oboe as legato players. Ranges: violins I up to C7 (octave doubling), flutes to
C7 (doublings above fold down), basses E1 and up.
