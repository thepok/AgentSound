# Unbowed - brief

## The wish

> "Create classical music for the orchestra in the style of Beethoven."

An ORIGINAL symphonic first movement in Beethoven's idiom of the middle-period symphonies (~1804-1812). No note,
theme, motif or progression lifted from Beethoven - in particular not the Fifth's short-short-short-long motto, not
the Eroica's two opening chords, not the Fifth's horn call (Bb-Eb-F in that rhythm). The idiom, not the notes.

## Frame

- Genre / profile: classical (`ANALYSIS = {'profile': 'classical'}`), a concert work: dynamics first.
- Key: C minor -> C major (the struggle-to-triumph arc). Meter 4/4. Feel: straight, a classical orchestra's pulse.
- Tempo: Adagio molto q=56 (introduction), Allegro con brio q=148, a short Adagio q=52 for the oboe cadenza.
- Length: ~6.5 min (sonata form with a slow introduction, no exposition repeat).
- Form: `intro 10 | t1 8 | t1ff 8 | trans 16 | t2 16 | closing 12 || dev1 12 | fugato 16 | storm 8 | pedal 16 ||
  rec1 8 | cadenza 2 | rec2 12 | rec3 16 | rec4 12 || coda1 16 | coda2 12 | coda3 8` (bars).
- Energy arc: ff unison blows and pp answers (intro) -> p theme -> ff counterstatement -> sforzandi -> p dolce second
  theme -> ff closing -> development rising through the fugato to the hammered storm -> subito pp -> the long
  crescendo over the dominant pedal -> ff recapitulation -> a lonely oboe -> second theme in C major -> the bVI shock
  -> coda: subito p, the chromatic climb, the C major triumph, hammered tonic chords. One climax: the coda's triumph
  (~85 %), prepared by the development's pedal crescendo (the second-highest peak).

## The hook

One terse CELL - an 8th that leaps up a sixth onto a long note struck on the off-beat (the sforzando falls between
the beats), a step down, a landing (`G4:.5 Eb5:1 D5:.5 C5:1`). Everything grows from it (motivic economy): the
first theme (a sentence), the bass under the second theme, the closing theme in major, the development's sequences
and the fugato subject, the imitations over the dominant pedal, the triumph in C major. It is carried by real
sampled orchestral sections (violins I / II, flutes, oboes in octaves) - no synth, nothing beepy.

## Sounds

`bands.symphony_orchestra` (SSO 4.0 + VPO + VSCO 2 CE in the Musikverein IR) as Beethoven scored it: strings in 5
parts, pairs of flutes, oboes, clarinets and bassoons, horns, 2 trumpets, timpani on C / G - without trombones,
tuba, harp, percussion, celesta. Solo VSCO 2 horn (the calls), clarinet (the second theme) and oboe (the cadenza),
played by `agentsound.hornist` (breath inside the held notes, no jazz vibrato).

## Shared building blocks (reuse, not copies)

- `agentsound.voicing` (new: promoted from songs/lux-perpetua/score.py `satb()` and generalised): every chord of
  the strings, the wind pairs (WINDS8) and the tutti (TUTTI) is voiced around the written lines; the fugato's free
  voices are voiced and given motion (`arpeggiate`, `passing_eighths`) and read back with `voicing.check`.
- `bandlib.orchestra`: `perform` (articulations, the dynamics lane, early long notes), `ring(back=)` (new) for the
  hall bloom on the fermatas.
- `hornist` for the horn calls, the clarinet theme and the oboe cadenza; `humanize.touch` for phrase dynamics;
  `articulation` marks (sustain, staccato, marcato, tremolo, pizzicato).

## References

None in `assets/refrences/` (no Beethoven symphony recording there): the comparison is against the `classical`
profile only. Recipe targets: recipes/classical.md "Mix targets".

## Checklist from recipes/HUMAN_FEEDBACK.md (the A&R ticks it)

- [ ] A real piece, not a loop: form, tension and release, one memorable cell that returns and grows, variation.
- [ ] No beepy lead: the theme on real sampled sections in octaves (violins, flutes, oboes), not a thin synth.
- [ ] The lead in front: the theme audible over the accompaniment in every section (bed under the lead).
- [ ] Real dynamics: `flat_dynamics` = 0; phrase arcs (touch), sforzandi, subito p, crescendi.
- [ ] Played, not keyboard-like: articulations (sustain / staccato / marcato / tremolo / pizzicato), early long
      notes, human timing, breathing winds (hornist), rubato in the introduction and the cadenza.
- [ ] Produced: one real hall (IR), seating, a full low end (basses), width.
- [ ] `clicks` = 0, no clipping, true peak <= -1 dBTP; silent notes 0.
- [ ] The brief's own targets: Beethoven fingerprints present (sf on weak beats, syncopes, hemiola, horn calls,
      timpani on I / V, long dominant pedal, bVI / Neapolitan surprises, subito p, fugato, coda as second
      development, hammered tonic chords), no borrowed Beethoven material, length 5-7 min.

## Targets

`classical` profile: -23..-16 LUFS-I (an orchestra -20..-18), PLR >= 12, LRA 8-20 LU, true peak <= -1 dBTP,
reverb 4-14 LU under the mix, width > 150 Hz 25-80 %. Master platform: `dynamic` (concert dynamics).

## Log

- producer: brief written; the voicer promoted into `agentsound/voicing.py` (lux-perpetua imports it: its render
  JSON and the requiem section render are bit-identical); `orch.ring(back=)` and the fermata-span fix done.
- arranger / sound designer / mix / master: built the movement (score.py, song.py), SOUND.md, MIX.md (hand mix: the mixer cannot judge a per-section lead), MASTER.md (dynamic, -19.6 LUFS, LRA 20.9). 0 clicks, 0 silent notes, 0 flat_dynamics warnings.
- A&R round 1: revise (4 majors: no climax, soft passages too soft, fugato bass-heavy, mechanical development; minors: Eroica-like double blow, t2 restatement drop, balance spots, timpani always ff).
- revision 1: dev1 inversion + fragmentation, pedal stretto + one-beat heads, fugato basses thinned, coda2 recoloured, single blow endings, dynamics map + the conductor's arc on the master input: -19.8 LUFS, LRA 17.3, coda3 the loudest moment (-13.0 short-term), t1 -26.6, rec3 -25.2 LUFS.
- A&R round 2: revise (3 new majors in the development: fugato's last entry under a clarinet doubling, the fugato opening in a hole, the pedal crescendo a plateau; minors: transition > counterstatement, codettas too soft, stale doc text).
- revision 2: winds double only the entering fugato subject, the pedal's held parts re-attack every bar on a reshaped map, arc rides (fugato +6 easing, pedal, transition -1, codettas up), dev1 winds +3..4 dB, coda2 cello 8ths softer: -19.8 LUFS, LRA 16.2, pedal bars 9-15 +6 LU then the G7 blow.
- A&R round 3 (final): ship. Open minors (polish): fugato horns -3 dB in its bars 13-16, the fugato subject's running bar (-38 LUFS), timpani mostly ff, coda2 bar 7 theme ~3 dB under the cellos, keyswitch collisions at tutti stabs (TODO.md).
- delivered: out/mix.mp3 (6:27, -19.8 LUFS-I, TP -1.2 dBTP, LRA 16.2 LU, 0 clicks, 0 silent notes, 0 flat_dynamics warnings). Credits: SSO 4.0 (CC Sampling Plus 1.0), VPO 3, VSCO 2 CE (CC0), Voxengo IM Reverbs.
