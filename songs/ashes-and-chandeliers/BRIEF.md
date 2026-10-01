# BRIEF - Ashes and Chandeliers

## The wish

> "Queen hat doch so epochale Songs gemacht ... Rhapsody" -> "Jap, das wird episch" -> "wo bleibt das epische
> orchestrale Stueck?"

An ORIGINAL epic, multi-part instrumental in the spirit of Queen's "Bohemian Rhapsody" (1975) and "Who Wants to Live
Forever": through-composed, contrasting parts (ballad -> mock-operatic choir drama -> rock with a harmonized guitar
orchestra -> a huge orchestral finale that falls away to the solo piano). Nothing lifted: no melody, chords, riffs or
structure of those records - only the spirit (a piano ballad that opens, a sudden operatic switch, the band kicking
in, a guitar orchestra in thirds, an orchestral farewell with a gong).

## Frame

- Genre: symphonic rock (orchestral rock opera, instrumental). Analysis profile: `film` (orchestra + band, big
  dynamic range: LRA 5-20, -16..-10 LUFS).
- Length: ~6:00 (target 5:30-6:30).
- Through-composed, four parts with their own key, tempo and meter:

| part | key | tempo | meter | feel |
|---|---|---|---|---|
| I Ballad ("Candlelight") | C minor, middle in Eb major | 72 | 4/4 | straight, rubato breathing |
| II Opera ("The Masquerade") | E minor (3/4 interlude in G / E minor) | 112 -> 3/4 at 112 -> accel. to 138 | 4/4, 3/4 | staccato, dramatic |
| III Rock ("The Stampede") | A minor | 138 | 4/4 | straight 8ths, heavy |
| IV Finale + coda ("Curtain") | C major -> C minor/major coda | 76 -> 60 (rit., fermata) | 4/4 | half-time grandeur, then rubato |

Key path: C minor -> (Ab major chord = G#) -> E minor (chromatic-mediant shock) -> E major (V) -> A minor -> C major
(relative) -> C minor coda with a Picardy C major last chord.

## The hook

The main theme (8 bars): an upbeat G4 leaping a sixth to a held Eb5, then a stepwise sigh down (D5 C5) - the
"curtain" motif. It carries the whole piece:
- Part I: on the hero piano (sampled/hero_piano, the ballad hero, played by the pianist: harmonized, rolled, touch
  dynamics), C4-C6 - not beepy: a sampled grand with body.
- Part II: fragments of it in the choir calls (augmented, in E minor).
- Part III: the guitar orchestra (layered/hero_guitar x3) plays it in A minor, 2 then 3 voices in diatonic thirds.
- Part IV: the major-key transformation (G4 -> E5, a major sixth) in violins + choir + horns + the lead guitar on top.
- Coda: the opening motif alone on the piano in C minor, then the final rolled C major chord.

## Form (one line) and energy arc

`intro 4 | theme 8 | theme2 8 | middle 8 | return 6 || stab 4 | calls 16 | masque(3/4) 12 | ascent 8 || riff 4 |
anthem 8 | anthem2 8 | solo 8 | riff2 4 | break 2 || finale 8 | summit 4 | fall 2 | coda 6`

Energy (1-5): ballad 1 -> 2 -> 2.5 (middle) -> 2 | opera 3 (stab, subito) -> 3.5 with ff/pp extremes -> 3 (waltz)
-> 4.5 (ascent, fermata) | rock 4 -> 4.5 -> 5 (solo) | finale 5 (the peak, ~75 % of the length) -> tam-tam ->
1 (coda, intimate end).

## References

None to compare against (the Queen records are the spirit, not a target; no reference audio in the repo).

## HUMAN_FEEDBACK checklist (A&R ticks these)

- [ ] A real song, not a loop: through-composed, one theme that returns and grows (ballad -> guitars -> finale),
      transitions composed (piano pickup, timpani roll, accelerando, fermata, drum break, tam-tam).
- [ ] No beepy lead: piano hero, choirs, guitar orchestra, violins - no synth leads at all.
- [ ] The lead in front: bed >= 2-3 dB under the lead per section (carve: hero_piano.carve / sidechains keyed by the
      guitars).
- [ ] Real dynamics: `flat_dynamics` = 0 (touch() on every melody, live dynamics lanes on the orchestra, velocity arcs
      on choirs and guitars).
- [ ] Piano through `pianist.arrange` (never a bare line), rolled chords, pedal with the harmony; fast two-key figures
      budgeted (one `pianist.Memory` for the whole song; the big figure saved for the coda).
- [ ] Realism: sampled orchestra / choirs / guitars / kit, articulations (staccato, marcato, tremolo, rolls), players
      for drums / bass / guitars.
- [ ] Hero sounds for the hooks: hero_piano, hero_guitar (x3), full production (IR hall, plates, echoes).
- [ ] Warm piano (no presence push), not hard.
- [ ] `clicks` = 0 in the mix.

## Targets

- Profile `film`: -16..-10 LUFS-I, true peak <= -1 dBTP, LRA 5-20 LU, PLR >= 8.
- Per section: ballad around -26..-20 LUFS, opera -22..-13 with extremes, rock -14..-11, finale the loudest, coda
  back to ~-26.
- Mix profile `film` (bed -7..-1 dB under the lead). Master: the film orchestra master chain (mid dip, air, 1-2 dB
  glue, -1.2 dBTP limiter); platform `auto`.

## Log

- producer: brief written (4 parts, key path, hook, form, checklist). Next: arranger.
- arranger: ARRANGEMENT.md + song.py - 19 sections / 132 bars / 4 parts, tempo map (rubato, 3 ritardandi, an
  accelerando 112 -> 138, 3 fermatas), 3/4 masque; the curtain motif in 9 transformations; players: pianist
  (ballad, one Memory, big figure saved for the coda), orch.perform on every orchestra part, drummer rock + ballad,
  bassist rock + ballad, guitarist rock rhythm (2 takes), hero.lead solo (guitarist.lead, climax), hero.play for the
  harmonized guitar orchestra. Build 1: 0 clicks, no flat_dynamics warning (info only on 2-3 violins2 / horns pad
  phrases). Open: the rock sections quieter than the opera (fixed by the sound designer's levels).
- sound-designer: SOUND.md - film orchestra + rock band (lead left out) + hero piano + 3 choirs + 3 hero guitars in
  one song; 5 renders: band / guitar-orchestra levels, masque rides, mid / presence cuts at the sources, centred
  lows (taiko width, master monobass 120 Hz), the solo into the band's echo. Open: see the final report below.
- producer: build 5 (film profile) - 5:52, -15.4 LUFS-I, TP -1.19 dBTP, LRA 15.5 LU, PLR 14.2, lows corr 0.96,
  0 clicks in the mix (5 masked low-level ones in the basses), no flat_dynamics warning; arc: ballad -25.6 -> -20.7,
  opera -17.9 / -16.1 (ff/pp dips), masque -20.7, ascent -13.0, rock -14.9..-13.1, finale -11.3, summit -10.1,
  fall -22.3, coda -27.1. Open (for the mix / master stages, not run here): mid +4.3 dB (limit +4) and presence
  +3.5 dB (limit +3) vs the film reference - the rock + choir tutti is mid-forward; rock sections narrow (15-19 %
  above 150 Hz). METADATA / COVER set (classical, noir). Mix / master / A&R stages not run in this pass.
- mix-engineer: MIX (module level) + MIX.md - the tune judged per part (the single-lead mixer read the oboes /
  gtr1 as the only lead and asked to cut the finale's melody doublings: refused). Riff guitars +2.5 in riff / riff2
  (riff -14.9 -> -14.1 LUFS, guitars 2.9 dB over the kit), gtr1 presence dip + fader up (kit 1.7 -> 2.4 dB under it in
  anthem2), finale piano -2.5 / bass -1.5 / choir_m -1..-1.5, summit brass -1, calls choir_m +1, mid / presence carved
  (hall return 1.2 + 4 kHz, gtr2/3, violins1, choir, rhythm guitars, bass fizz), Part III returns ridden up (reverb
  -15..-18 -> -10..-13.5 LU). Mid +4.3 -> +3.9, presence +3.5 -> +2.9, 0 warnings. Open: anthem / solo 0.1-0.5 LU
  under the film "wet" line, anthem / anthem2 narrow (gtr2/3 panning, sound designer), 5 masked basses clicks.
- mastering-engineer: MASTER.md - film profile, platform auto (no fitting reference): +1.9 dB low shelf 60 Hz,
  -1.4 dB bell 1.25 kHz Q 0.5, limiter -1.2 / 200 ms / +0.6 dB. Delivered build: -15.6 LUFS-I, TP -1.19 dBTP,
  LRA 14.8, PLR 14.4, mid +3.0 / presence +2.7 / sub -0.9, 0 warnings, 0 clicks. Next: A&R.
- a-and-r: AR.md - verdict REVISE. 1 blocker: the finale's C major theme buried in a root-heavy tutti (tune 1.7-3.8 dB
  under the rest, cellos' roots the loudest stem, bed +5.5 / +7.0 dB vs gtr1). 3 majors: the band enters 3.6 LU
  under the E major fermata and Part III stays flat (-14.7..-13.1, solo under anthem2); no guitar wall (rhythm pair
  2.3-4 dB under the kit, width >150 Hz 23-28 %); choir calls speak too slowly (250-350 ms onsets swallow the
  pickups). 3 minors (pp dropouts, veiled ballad piano, masked basses clicks). Next: arranger (1, 2, 4), then
  sound-designer / mix-engineer, then A&R again.
- arranger + sound-designer + mix-engineer (revision, AR.md "## Revision"): finale / summit re-voiced as a film
  tutti (the tune in three octaves, chords on violas + guitars, no root wall: doublings +5.6 / +4.4 dB over the rest,
  gtr1 the loudest part); the fermata dies into the pickup and the riff arrives with the orchestra (bar 74 / 75:
  -12.7 / -12.6 LUFS, was -10.1 / -13.7), Part III built by layers (-12.6..-14.2, above the opera); guitar wall
  (pair +2.8..+5.4 dB over the kit, width >150 Hz 31.7 / 40.3 %); choir lines at a speaking velocity + expression
  lanes (onset -7..-14 dB at 40 ms, was -26..-40); pp answers +5-6 LU; piano left hand softer + air (partial).
  -15.4 LUFS-I, TP -1.18, LRA 15.3, 0 warnings, 0 clicks in the mix. Master unchanged. Next: A&R again.
