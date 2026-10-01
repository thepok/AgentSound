# BRIEF - Lux Perpetua (Requiem in D minor)

## The wish

> "cool make a real orchestral part like requim from mozart"

A REAL orchestral-choral piece in the style of Mozart's Requiem K. 626 (1791), ORIGINAL in that idiom: no note, tune,
fugue subject or progression lifted from Mozart (or from Süssmayr's completion). The idiom is what we take:

- D minor, dark harmony: Neapolitan sixths, diminished sevenths, a chromatic lament bass, suspensions and sighs.
- Counterpoint: a fugue with subject and countersubject, voice by voice.
- Homophonic choral blocks for the drama.
- The syncopated string pulse of an Introitus.
- A Dies irae storm (tremolo, running 16ths, dotted brass and timpani).
- A trombone chorale and a solo tenor trombone.
- A 12/8 Lacrimosa.
- A Picardy / open-fifth ending.

## Frame

- Genre: classical (sacred choral-orchestral).
- Analysis profile: `classical`. It is a concert work, not a film cue: a -23..-16 LUFS window, LRA 8-20 LU, a
  safety limiter only, no glue compression. The `film` profile would want -16..-10 LUFS and a denser, compressed
  sound, which is wrong for a Requiem.
- Length ~4:30, through-composed in five movements (attacca):

| movement | sections | key | meter / tempo | character |
|---|---|---|---|---|
| I Introitus | intro 6, requiem 10 | D minor -> F major -> D minor, half cadence | 4/4, Adagio q=56 (rubato, rit., fermata) | syncopated pulse, lament bass, the choir enters voice by voice |
| II Kyrie | kyrie 19 | D minor (answers in A minor, middle entry F major) | 4/4, Allegro moderato q=88, Adagio cadence | fugue, bare fifth at the end |
| III Dies irae | dies 8, tremor 8, ira 8 | D minor -> F -> D minor | 4/4, Allegro assai q=144 | tutti storm, subito pp tremor, the climax |
| IV Tuba | tuba 8 | Bb major -> A7 | 4/4, Andante q=72 | solo tenor trombone, the low voices answer |
| V Lacrimosa | lacrimosa 8, amen 4 | D minor -> D major (Picardy) | 12/8, Larghetto q.=48 | sighing violins, rising choir, plagal Amen |

## What carries it

There is no pop hook; the "lead" changes per movement, and each one is sung or bowed, never a synth:
- Introitus: the soprano line of the choir, with the strings' offbeat pulse.
- Kyrie: the fugue subject in each entering voice (D-A-Bb-A, a falling scale to the leading tone).
- Dies irae: the choir's homophonic declamation.
- Tuba: the solo tenor trombone, played by `hornist`.
- Lacrimosa: the soprano's lament and the chromatic climb A4 -> F5 over a falling bass.

The Picardy D major of the Amen is the one "light" (lux) of the piece.

## Energy arc

intro p (-31 LUFS) -> requiem f entry, then p, 'lux' f -> kyrie builds entry by entry (-19) -> dies ff (-16) ->
tremor pp then crescendo -> ira ff: the climax at ~60 % of the length (-15) -> tuba p (-26) -> lacrimosa p to its
forte climb (short-term -18) -> amen mp, dying away under the fermata.

## References

None (no recording of K. 626 in `assets/refrences/`; the piece is judged against the `classical` profile).

## HUMAN_FEEDBACK checklist (A&R ticks these)

- [x] A real piece, not a loop: five through-composed movements, fugue, transitions composed (fermatas, attacca,
      the timpani roll into the choir, the hush after the Dies irae, the A7 fermata into the Lacrimosa).
- [x] No beepy lead: choir, strings, solo trombone; no synths at all.
- [x] Real dynamics: `flat_dynamics` = 0 (a dynamics map for the whole piece, touch() phrase arcs on every line,
      live dynamics lanes on every section, the choir's lane per voice).
- [x] Realism: sampled SSO / VSCO / VPO sections with keyswitched articulations (sustain, staccato, marcato,
      tremolo, pizzicato, timpani hit / roll), early starts for slow attacks, humanized section timing, the hall.
- [x] Held wind notes breathe: the solo trombone is played by `hornist.arrange` (air, vibrato, a scoop, a taper).
- [x] Every production has its space: the Musikverein IR for everyone, depth by send / shelf, hall blooms on the
      fermatas.
- [x] `clicks` = 0 in the mix.

## Targets

- Profile `classical`: -23..-16 LUFS-I, true peak <= -1 dBTP, PLR >= 12, LRA 8-20 LU, reverb 4-14 LU under the mix,
  width 25-80 %, the band balance within +-5 dB of the classical reference.
- Master: the preset's safety limiter plus the mastering engineer's tonal eq (from `agentsound master`, taken at ~3/4
  strength), platform `auto`.

## Log

- producer: brief written; the orchestra is the symphony preset without the instruments Mozart did not use; the
  wish's five characters became five attacca movements.
- arranger: `score.py` (harmony tables, tunes, subject / countersubject, the SATB voicer) and the performance in
  `song.py`. Checked with a scratch script: non-chord tones on strong beats and semitone clashes, per section. The
  deliberate ones stay: the countersubject's chromatic passing tones, the violins' appoggiaturas. Fixed:
  - a doubled harmony step in the fugue's stretto;
  - a suspension sounding against its resolution (the episode);
  - the violins' pulse under the choir's passing tones: it now doubles the voices it follows.
  - The middle entry moved to the tenors.
- sound-designer: `SOUND.md`. Balance passes, v1 -> v8:
  - v1: the choir 10 dB too loud (-14.1 LUFS, lowmid +10.9).
  - Choir -8 dB and a steeper dynamics lane.
  - Tuba strings up, trombone -5 dB.
  - The 'oh' choir merged into one track (it was masking itself).
  - The men's unison moved from choir_male (a loop seam clicked in the mix) to the 'oh' choir.
- master: the tonal eq from `agentsound master` (classical profile, ~3/4) and monobass 120. Result: 0 warnings,
  3 info, 0 clicks in the mix. The info lines are 11 masked single-track loop seams (fermata chords) and two
  deliberate level jumps (intro -> requiem, ira -> tuba).
- mix-engineer: `MIX.md`. Roles by the score: the mixer's inference made the choir a bed; with the voices as leads
  it compares one voice track with the summed orchestra.
  - Seating: antiphonal violins (II to +0.5), trumpets and timpani back left, trombones back right. The choir is
    narrowed to 80 % and panned against the samples' lean: S A T B now read left to right (+4.2 / +0.5 / -2.3 /
    -3.4 dB).
  - Choir: +5..+6.3 dB (trims) plus rides, with its box carved (-3 dB at 600 Hz) and +1.5 dB at 3.2 kHz. Strings
    -1.5 (colla parte), trombones -2, basses +2 / cellos +1.5 (the fundament). Mud dips, and the hall return
    de-boxed and brighter.
  - Choir vs the instruments in its register: -4.5..-0.3 -> +0.5..+3.5 dB in every sung section. 0 warnings, 0
    clicks in the mix.
  - Open: a group / per-section lead in the mixer (TODO.md).
- mastering-engineer: `MASTER.md`. Platform dynamic. The first pre-master read lowmid / mid +6.5 (tone_band): sent
  back to the mix, now +4.6 / +4.8.
  - Master eq from `agentsound master`: +2.8 low shelf 100 Hz, -2.8 dB 800 Hz, +2.7 high shelf 5 kHz; limiter
    gain 1.2 -> 1.9 dB.
  - -19.6 LUFS-I, TP -2.5 dBTP, LRA 16.0, PLR 17.1. `master --check` shows no warnings. The post-pass matches the
    in-song build.
- a-and-r: `AR.md`, verdict **revise** (1 blocker, 5 major, 7 minor).
  - Blocker: the Mozart figures are written but not audible - the Introitus pulse, the Lacrimosa sighs, the storm's
    16ths and the trumpets sit 8-21 dB under the rest in their own register.
  - Majors: a legato vowel-pad choir in the Dies irae, the organ as a full pad, a mono / muddy intro, a boxy / dull
    tone, and a fugue that reads as chords.
  - Keep: the form, the drama, the vocabulary, the solo trombone and the seating.
- revision (A&R round 1): every role on its issues, `AR.md` "Revision".
  - The figures heard: the pulse, sighs, 16ths and trumpets written a dynamic level up and ridden (band-limited
    -21..-8 -> -10..+1 dB against the rest); the organ a continuo (-11 dB, bass line); the choir declaims (re-attack
    6-8 -> 22-25 dB); the fugue's entries on top, a tonal answer, free voices in quarters and 8ths; the ira the only
    ff (+1.7 LU over the Dies irae); 0 parallels; the lament swells; the tone opened (air -10.3 -> -6.9 dB).
  - -19.5 LUFS-I, TP -1.2, LRA 15.1, PLR 18.3, 0 warnings, 0 clicks in the mix. Homages named: the Lacrimosa's climb,
    the Tuba's arpeggio.
