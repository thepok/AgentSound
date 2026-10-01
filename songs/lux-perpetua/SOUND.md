# SOUND - Lux Perpetua

Mozart's Requiem orchestra: strings, 2 basset horns, 2 bassoons, 2 trumpets, 3 trombones, timpani, organ, SATB
choir. The ensemble is `bands.symphony_orchestra` without the instruments Mozart left out (flutes, oboes, horns,
tuba, percussion, harp, celesta): SSO 4.0 sections, levelled and calibrated at mf, seated, sharing one hall.
Everything sends to that one hall, the Voxengo Musikvereinsaal IR (~1.9 s).

| part | sound | range played | chain + sends | why |
|---|---|---|---|---|
| violins I / II | preset (SSO 1st / 2nd violins KS: sustain, staccato, marcato, tremolo) | D4-A5 | preset eq / width, hall -6 | the Introitus pulse (staccato), colla parte lines, 16th storm, sighs |
| violas | preset (SSO violas, VPO sustain) | D3-G4 | preset, hall -5.5 | tenor line, tremolo |
| cellos / basses | preset (SSO + VPO / NBO sustains; basses pizzicato in the Lacrimosa) | Eb1-C4 | preset (monobass), hall -6 | the lament bass, 8th drive, pizzicato pulse |
| basset horns | preset 'clarinets' (SSO clarinets a2), id `basset_horns` | D3-Eb5 | preset, hall -4 | no basset-horn samples: clarinets kept in the low, dark register |
| bassoons | preset (SSO bassoons a2) | G2-G4 | preset, hall -4 | the intro sigh, bass doubling |
| trumpets | preset (SSO trumpets a3) | D4, A4, D5, F#5 only | preset, hall -3.5 | natural trumpets in D: only harmonic-series notes, marcato hits, no melodies |
| trombones | preset (SSO trombones a3) | G2-C5 | preset, hall -3 | alto / tenor / bass doubling the choir in the f passages, the fugue's second half, the climb and Amen |
| timpani | preset (VSCO 2 CE hit / roll) | A2, D3 | preset, hall -2.5 | tuned D / A, rolls into arrivals, the Amen roll |
| organ | `sampled/chamber_organ` (Burea choir organ, Rorflojt 8' + Principal 4') | G2-A5 | eq -3 dB at 350 Hz, hall -12, expression lane 0.4-0.9 | continuo: the voiced harmony under the choir, soft |
| choir S / A / T / B ('ah') | `sampled/choir_mixed` `.but(start=60)` x4 | S C4-A5, A G3-C5, T C3-G4, B G2-D4 | eq -3 dB 380 Hz, -2 dB 1.1 kHz; gain -12; pan -0.38 / -0.14 / +0.14 / +0.38; hall -3 | one track per voice: its own dynamics lane and seat; clean VPO loops |
| choir 'oh' | `sampled/choir_oh` (No Budget Orchestra 2) | Bb2-F5 | eq -2.5 dB 380 Hz; gain -9.5; hall -3 | the soft vowel for the Lacrimosa lament, the Amen and the low voices' answer in the Tuba; clean loops for the long fermata |
| solo trombone | `sampled/solo_trombone` (SSO, mono legato) | A2-D4 | eq -2 dB 1 kHz, hall -7; gainDb -5 under the choir's answer | the Tuba mirum call, breath from `hornist` (targets: `instrument.dynamics` + vibrato) |

## Space and master

The mix (seating, balance) and the master have since been redone by the mix and mastering engineers:
`MIX.md`, `MASTER.md`. The master settings below and the checks further down are the sound designer's v8.

- The hall: `bands` convolution, Musikvereinsaal x1.25, predelay 18 ms, 110 Hz low cut, +2.5 dB air. The report
  reads it at -9.4 LU under the mix (target -14..-4); the verdict per section is 'lush'.
- The hall blooms: the hall send of every orchestra role rises 3-4 dB on the three fermatas (requiem, kyrie, amen)
  and returns before the music goes on. The symphony preset's `orch.ring()` keeps the raised send for the rest of
  the song, so it was not usable mid-song (TODO.md).
- The master is `mastering.apply`, from `agentsound master` against the classical profile, at ~3/4 strength:
  - +2 dB low shelf at 100 Hz;
  - -2.2 dB at 630 Hz (Q 0.5);
  - -0.8 dB at 1.25 kHz;
  - +2 dB high shelf at 4 kHz;
  - mono below 120 Hz;
  - the limiter (ceiling -1.2 dBTP, gain +1.2 dB).

  The sampled sections and the choir read boxy and dark.

## Checks (build v8)

- Loudness: -20.7 LUFS-I, true peak -3.6 dBTP, LRA 16.3 LU, PLR ~17 dB.
- Width above 150 Hz: 44 %; low-end correlation 0.96.
- Balance vs the classical reference: bass 0.0, lowmid +3.8, mid +3.5, presence +0.2, brilliance -7.3, air -11.5.
  Before the choir cut and the master eq it was lowmid +10.9, mid +9.7.
- Clicks: 0 in the mix. 11 are masked in single tracks: loop seams of held notes in the long fermata chord at the
  end of the Kyrie (trumpets, violins II, choir B / S).
- `sampled/choir_male` clicked in the mix on a held D3 (a loop seam, v1-v5), so the men's line moved to
  `sampled/choir_oh`.
- Note dynamics (10-90 % per phrase):
  - violins I 8.0 dB, violins II 10.7, cellos 5.5, basses 8.0;
  - basset horns 9.8, bassoons 7.3;
  - trumpets 7.9, trombones 7.7, timpani 7.3;
  - solo trombone 16.6.

  No flat_dynamics.
- Section levels (LUFS):
  - intro -31.1, requiem -24.7, kyrie -19.4;
  - dies -15.7, tremor -16.8, ira -15.1;
  - tuba -26.5, lacrimosa -23.8, amen -23.4.

## Licenses (credits.txt)

- Sonatina Symphonic Orchestra (CC Sampling Plus 1.0: credit, no advertising use).
- Virtual Playing Orchestra (royalty-free).
- VSCO 2 CE (CC0).
- No Budget Orchestra 2 (CC-BY-SA 4.0: the 'oh' choir).
- Lars Palo's Burea choir organ (CC-BY-SA 2.5).
- Voxengo IM Reverbs.

Nothing is non-commercial or no-redistribution. The CC-BY-SA packs need their attribution when published.

## Revision (A&R round 1)

- **The choir's box, at the source:** a third bell, -2.5 dB at 600 Hz (Q 1), on the four 'ah' tracks and on the
  'oh' track (A&R issue 5). With the mix's -3 dB at 600 Hz the choir now dips 5.5 dB there.
- **The hall's air:** the return's convolver is opened to 20 kHz (it was high-cut at 14 kHz) and gets a +2.5 dB
  shelf at 9 kHz. Air went -10.3 -> -6.9 dB and brilliance -5.7 -> -3.9 dB vs the classical reference, with the
  master's shelf.
- **The winds get a seat:** the SSO bassoons (and the basset horns) are mono samples, a point in the middle of the
  intro. A short stereo early-reflection insert (the Musikverein IR, first 120 ms, mix 0.22, width 1.6, low cut
  180 Hz) spreads them. Intro width 11 % -> 26 %.
- **Declamation (A&R issue 2):** the VPO choir's zones carry their own 1.25 s release, which the track's `release`
  cannot shorten (TODO.md). The syllables of the Dies irae, tremor and ira are parted on each voice's `expression`
  lane instead: after every sung note it falls to 0.4 (-8 dB) within 50 ms and opens again on the next attack.
  Re-attack depth per written soprano note: dies 8.0 -> 22.3 dB, tremor 5.9 -> 24.3 dB, ira 8.0 -> 25.1 dB (median,
  10 ms RMS on the dry stem; the timpani read 24-28).
- **The 'oh' range (A&R issue 12):** the No Budget Orchestra 'oh' set has samples D2-C#5, one every 2-3 semitones
  (the patch note said "C3-C6"; corrected). Its low notes (G2 / A2 / Bb2) are recorded samples within a semitone,
  like every other note of the set, and stay. Its real stretch was at the TOP: the lament's soprano sang D5-F5,
  1-4 semitones above the last sample. The Lacrimosa soprano now sings on the 'ah' soprano track (samples to C6);
  the 'oh' keeps the lament's lower voices, the Amen and the Tuba's men.
- **The intro's low mids:** cellos, violas, bassoons and basset horns dip 4 dB at 300 Hz (Q 0.9) in the intro only
  (`intro_dip`, opening over the last beat before the choir). Intro lowmid +10.4 -> +7.5, bass +9.1 -> +2.2 dB.
