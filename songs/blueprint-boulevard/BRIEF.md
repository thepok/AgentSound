# Blueprint Boulevard (songs/blueprint-boulevard) - brief

## The wish

> "make a song like the songs used in SimCity 3000 - maybe research them before"

An ORIGINAL instrumental in the idiom of the SimCity 3000 soundtrack (Jerry Martin / Maxis, 1999; research and
sources: recipes/simcity.md): bright, optimistic, relaxed "urban jazz" for building a city - played by a real-sounding
studio band, a memorable but unobtrusive hook, loop-friendly. No melody, changes, riff or title from the game.

## The song

- **Genre / profile**: light urban jazz / late-90s contemporary jazz; `ANALYSIS = {'profile': 'pop', 'loudness':
  [-14.5, -11]}` (a lighter master than radio pop: background music).
- **Tempo / key / meter / feel**: 112 BPM, C major, 4/4, STRAIGHT 8ths (HUMAN_FEEDBACK: "aber ohne Swing").
- **Harmony**: A = `Cmaj9 Fmaj7#11` vamp (the lydian #11 is the sunny colour), `Em7 A9 Dm9 G13sus4`, a second 8
  turning through `Fm6`; B (the "sunrise" lift) = `Abmaj7#11 Bbmaj9 Cmaj9 ...`; sus dominants, no dark drama.
- **The hook**: on the alto sax (Weresax, E4-G5: real, breathy, no beep): a pickup of two 8ths leaping a sixth up to
  a held note that sighs down onto the #11 of Fmaj7#11; answered a step higher; the A's second half climbs to the
  top C6 (sounding G5). It returns in every A: sax (head1), grand piano harmonized (head2), sax + vibes an octave up +
  tenor a third under, the second half climbing (head3).
- **Band**: `bands.make('funk_band', without=('gtr',), keys='rhodes', lead='sax')` with the stereo-vibrato Rhodes;
  plus the warm grand (`sampled/jazz_grand`), MSLP vibes, MTG tenor (harmony), SoftPoly pad, a shaker.
- **Form** (110 bars, ~4:05): `intro 8 | head1 16 | lift1 8 | head2 16 | sax_solo 16 | piano_solo 16 | lift2 8 |
  head3 16 | outro 4 | end 2`. Energy: 1.5 - 2.5 - 3.5 - 2.5 - 3 - 3 - 4 - 4 - 2 - 1: a gentle arc, no build-up drop.
- **Reference**: none in `assets/refrences/` for this style - `compare` skipped; the recipe and the pop profile with
  the lighter loudness window are the targets.

## HUMAN_FEEDBACK checklist (the A&R ticks these)

- [ ] A song, not a loop: form, a hook that returns and changes, solos, transitions, a real ending.
- [ ] No beepy lead: a real sax hero (natural, no doublers) and a warm grand.
- [ ] The lead in front: the bed >= 3 dB under it.
- [ ] Real dynamics: `flat_dynamics` 0 (sax, piano, Rhodes, vibes, tenor).
- [ ] Held wind notes breathe: every sax line through `hornist.arrange`.
- [ ] Piano never a bare line: `pianist.arrange` / the pianist's solo vocabulary.
- [ ] Straight 8ths, relaxed, steady.
- [ ] Warm piano (jazz_grand, no presence boost).
- [ ] `clicks` 0, `silent_notes` 0, true peak <= -1 dBTP.

## Targets

- Mix: the pop profile's balance; the sax 6-8 dB over the drums, the bed far under it, no low-mid / mid masking
  warnings worth hearing.
- Master: -13..-11.5 LUFS integrated, LRA >= 4 LU, TP <= -1.2 dBTP.
- Credits: see the A&R / delivery notes (NC and no-redistribution packs: private listening).

## Log

- producer: research done (recipes/simcity.md), brief written: 112 BPM C major straight, Rhodes + grand + alto hero
  + Jazz bass + sticks, lydian vamp, sunrise lift, two solos.
- arranger: form + hook + players built (ARRANGEMENT.md); first build OK (0 clicks, 0 silent notes).
- sound designer: band preset + Rhodes vibrato swap, vibes narrowed, piano trimmed (SOUND.md).
- mix engineer: bass -3 dB, its 1 kHz / 3.5 kHz cut (MIX.md).
- mastering engineer: glue threshold -11, limiter drive -5 dB (MASTER.md).
- A&R: see AR.md.
