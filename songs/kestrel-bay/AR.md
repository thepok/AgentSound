# Kestrel Bay - A&R

## Round 1 (first full build) - verdict: revise

1. [blocker] no arc: every section -8.2..-9.2 LUFS, LRA 1.9 LU, the intro as loud as the climax (loudness.png flat):
   the wall never breathes. owner: mix-engineer. fix: ride the sections into the master (quiet sections under the
   glue / limiter), hold the band back in the solos' statements.
2. [major] the hero 7 dB over the drums and 10-17 dB over the bed (mix: drums_too_quiet, bed_too_quiet): a lead over
   a thin backing, not a band. owner: mix-engineer.
3. [major] the first solo's statement (low motif, E4-A4) buried under the full power-chord wall (spectrogram_05:
   the lead invisible in bars 29-32). owner: arranger. fix: split the solos (solo / solo2, outro / outro2), the band
   lighter while the motif is stated.
4. [minor] both solos climaxed on the same 'scream'; the outro's choices barely change with the seed. owner: arranger
   (weights per solo) / system (TODO: soloist variety).
5. [minor] the last chord held flat at full level, then a cliff at 3:26. owner: mastering-engineer.

## Round 2 (final build) - verdict: ship

summary: a singing hard-rock guitar ballad - a theme that climbs from the low verse to an octave-up climax, two solos
that grow out of its head, a held note that blooms into feedback before the first solo, and a guitar that bends,
shakes and squeals like a player, not a keyboard.

issues (most severe first):
1. [minor] the echo return sits 32.6 LU under the mix (reverb_inaudible): only the clean guitar and the piano feed it;
   the hero's echo is its own insert. owner: mix-engineer. Accepted (TODO: power_ballad's echo bus under a hero).
2. [minor] drums and bass share 60-250 Hz in the first solo (masking warn; the bass ducks under the kick only
   -2.5 dB there). owner: mix-engineer.
3. [minor] mid +3.6 dB / presence +2.0 dB vs the rock profile: the mid-forward hero; the Baker Street solo comparison
   (loudness-matched) has 125 Hz-4 kHz within +-2 dB, so kept. owner: mastering-engineer (info only).
4. [minor] judged by numbers and images only: the bends' overshoot, the up-only vibrato (5.7 Hz, 0..+50 ct in the
   stem) and the feedback bloom are measured, not heard (TODO.md "verify by ear").

checklist:
[x] a song, not a loop: the theme returns three times and grows (verse -> chorus higher and resolving -> chorus2 an
    octave up to D6), the bridge's rising answers, fills and transitions into every section, a real ending (the last
    A blooming into its twelfth, fading with the echo)
[x] no beepy lead: hero/guitar_heavy, body below 1 kHz, G3-D6
[x] lead in front: bed -6.9 dB vs the lead (whole song), per section inside the rock windows (MIX.md)
[x] real dynamics: lead note dynamics 5.4 dB (301 notes, vel 56-127), flat_dynamics 0; the song's arc LRA 5.4 LU,
    chorus 3.5 LU over the verse
[x] played, not keyboard-like: picked vs slurred notes, bends with rise / overshoot / settle and vibrato below the
    bent pitch, finger vibrato up from the note, slides, hammer-ons, strummed rhythm guitars, rolled / broken piano
[x] tricks budgeted: 2 fast figures in 72 bars (tremolo bar 37, sweep bar 63: 26 bars apart), spice 1.5 bars apart,
    every technique once or twice: feedback x3 (intro, bridge, end), pinch x2, unison bend x2, whammy dive / scoop /
    bar vibrato, ghost bend, wah, palm-muted chugs, legato flurry, sweep, tremolo, slides, bends everywhere
[x] hero sound: present (carved bed, dips on the competitors, rides in the hooks), its own echo throws
[x] produced: room / plate / hall, double-tracked wall 29 % wide, a full low end (sub +0.9, bass -0.8 vs profile)
[x] clicks 0, true peak -1.20 dBTP, silent notes 0
[x] the brief's targets: 3:33, -9.9 LUFS-I, the form as briefed

keep: the theme and its growth; the bridge's held G#5 feedback note into the solo; the solo2 burst (tremolo ->
legato) and pinch climax with the dive; the outro2 scream into the resolution; the arc rides.
