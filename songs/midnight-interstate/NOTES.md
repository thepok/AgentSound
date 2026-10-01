# Last Exit Before Dawn

- **Style:** Outrun / nightdrive synthwave (Kavinsky, Lazerhawk, Miami Nights 1984)
- **Tempo:** 112 BPM, 4/4, 112 bars (about 4:05, then the last chord and its tail). A ritardando runs over the last two bars and a fermata sits on the final chord.
- **Key:** F# minor. The final chorus and the outro are a whole step up, in G# minor.
- **Reference:** Kavinsky, "Nightcall"
- **Delivery:** `METADATA` sets the title, artist AgentSound, album Neon Archive and genre Synthwave. The cover uses the outrun style.

## The song

A lone drive down an empty neon highway at 3 a.m.

- **Intro:** a filtered pad opens, the pluck arp fades in and the glass bells play the chorus hook quietly, like something half-remembered. A vocoder robot (Windows voice "Stefan", German accent, through `synthwave/vocoder_choir`) says "last exit ... before dawn" on the F#m and A chords.
- **Verse 1:** the octave bass sits on an F# pedal with its filter closed, and the keytar lead (`synthwave/solo_lead`) sings a low melody that climbs 1-3-5. At bar 9 the backbeat, e-piano and bass roots come in.
- **Pre-chorus:** it walks the hook's head up through Bm, D, E and C#sus4 to C#. Everything stops for one beat before the chorus.
- **Chorus:** it starts on VI (D), so the V to VI move is a deceptive lift. The supersaw hook C#-F#-.-A-C#~ holds the major 7th over Dmaj7, doubled an octave lower by a pulse lead. It plays as A B A C, with an E6 peak and an F#6 climax, and a delay throw ends the chorus.
- **Chorus 2:** adds a second voice in 6ths, Jupiter strings, glass 8th arps and e-piano stabs.
- **Bridge:** a real breakdown. The drums drop out and the robot says the whole title over Dmaj7. A sampled tenor sax then plays the solo (the old keytar solo, down an octave): the hook's head a beat late, the dorian D# over B, a 16th run, and the head sequenced up a step per bar to an E5 scream. The bridge ends on D#sus4 to D#, the V of G# minor.
- **Final chorus:** after a one-beat drop, reversed swell and impact, the song comes back a whole step higher. It adds the Fairlight CMI choir, strings an octave up, bells doubling the hook an octave above, sax answer licks in the hook's held notes and three delay throws.
- **Outro:** the sax sings the head one last time. The progression ends on the song's only perfect cadence (E, F#, D#sus4, D#, G#m(add9)) under a ritardando from 112 to 87 BPM. The last chord is struck with a kick, crash and sub impact. It rings through a fermata, while the robot says "before dawn" and freezes the vowel of "dawn" (vocoder `hold`) as the chord decays into the hall.

## Production (re-production on `bands.outrun`)

**The preset (`bands.outrun`):**
- LinnDrum with the TR-909 kick, Simmons SDS-5 toms and a keyed gated snare/clap burst
- Octave bass with sub, played at 8th notes with gate 0.85
- Warm pad, DX e-piano and pluck arp
- Supersaw hook (the `lead` role, renamed `hook`)
- Lexicon 224XL concert hall and CD plate A as IR reverbs, a dotted-8th echo, and the kick pump
- `master/synthwave`

**Parts added on top of the preset:**
- Pulse double under the hook, and the keytar voice (`synthwave/solo_lead`, glide 35 ms) for the verse melody
- `synthwave/jupiter_strings`
- `sampled/fairlight_choir`
- `synthwave/arp_glass`
- `sampled/tenor_sax`. It uses the realism engine: `art.perform` for legato, live dynamics, delayed vibrato and glides into leaps, plus pitch-bend scoops into the solo's peaks, with a light chorus and microshift.
- `synthwave/vocoder_choir`. Its speech is cached in `samples/speech/`.
- Noise riser, reverse swell, impact and downlifter

**Changes after compare against Nightcall (loudness-matched):**
- **Hook:** -3.5 dB at 1.2 kHz and -4 dB at 6.3 kHz. The hook carried 30-40 % of the mid and brilliance excess.
- **Bass:** +2 dB low shelf at 55 Hz, -2 dB at 82 Hz (the octave-note bump), +1.5 dB at 200 Hz, and a second 5 dB kick duck with 110 ms release (plus the preset's 3 dB).
- **Master:** the preset chain, with the low-mid dip reduced from -2.5 to -1.5 dB, -4.5 dB at 1.1 kHz, width 1.2 and limiter gain 6.5 dB instead of 8.5. The lower limiter gain gives dynamics: the first render at 8.5 had LRA 1.7 LU and a flat -9 LUFS wall.

**Dynamics:** section-level `gainDb` lanes thin the verses and the bridge: kit, bass, pad and arp are 2.5-5 dB down, and the sax is -2.5 dB in the bridge. The chorus is 2 LU louder than verse 1, and the breakdown opens about 4 LU under the choruses.

**Space:** the pad's hall send blooms in the intro and the bridge (-3 / -2 dB) and at the end (up to -1 dB). The glass, arp, sax and robot go to the echo.

**Ending:** a tempo-map ritardando and fermata, plus a master `gainDb` decay of -15 dB over the held chord into the reverb tail. There is no fade-out of the music.

## Final A&R pass (branch `song/midnight-interstate-final`)

What a listener would have heard on the first re-production, and what changed:

- **Flat energy arc.** Verse 1 was only 1.8 LU under chorus 1 (the limiter flattened the pre-limiter `gainDb` moves). Now a
  master `gainDb` lane *after* the limiter sets the section levels: verses -1 dB, the breakdown -1.5 / -0.8 dB, the builds ramp
  up to 0 into each chorus. The limiter drive went from 6.5 to 7.3 dB, so the choruses get louder while the verses drop.
  Verse 1 is now 2.4 LU under chorus 1, and the final chorus is 2.6 LU over the breakdown.
- **Hook buried by the growing bed.** The final chorus read bed +2.3 dB over the hook. The hook is now +1 / +2.5 / +3.5 dB in
  chorus 1 / 2 / final. The pad is 1.5-2 dB down in the choruses, and the choir and strings are 1.5-2 dB down in the final
  chorus. The lead now sits 1.0-1.5 dB over the bed in every chorus.
- **Chiptune verse lead.** The verse melody was on the bare pulse / square lead, the Gameboy timbre the user complained about.
  It now plays on the keytar voice: two saws, a Moog ladder, tube drive, delayed vibrato and legato glide. The pulse stays
  only as the octave double under the supersaw hook.
- **Hook foreshadowing inaudible.** The glass bells that quote the hook in the intro and in the verse-1 gap were 10 dB under
  the pad. They are now +5 / +4 dB.
- **Chorus 1 thin.** Chorus 1 had only the pad as its bed and a width of 44 %. Jupiter strings now play under it at -3 dB as a
  halo. Chorus 2 still adds the full strings, the 6ths voice, bells and keys.
- **Punch.**
  - The drum-bus compressor attack went from 4 to 20 ms, and the kit is 1 dB up.
  - The bass ducks 7 dB (was 5) plus the preset's 3 dB.
  - The kit's plate send went from -18 to -24, so the hats tick instead of hiss.
  - Result: kick punch 11.4 -> 12.0 dB, snare 9.9 -> 10.5, hats 12.0 -> 13.3.
- **Tone** (Nightcall compare, loudness-matched):
  - The master low-mid dip is almost gone (-0.5 dB), and the pad gets +1.5 dB at 330 Hz for body.
  - Broad master bells cut 1 kHz by -5.5 dB (Q 0.6) and 6.5 kHz by -2 dB (Q 0.6).
  - Air: +2 dB shelf above 13 kHz.
  - Hook: -2 dB at 850 Hz, the 1.2 kHz cut moved to 1.25 kHz / -4.5 dB, and a -1.5 dB shelf from 8 kHz.
  - Master high-pass at 30 Hz: the 25-31 Hz rumble only cost limiter headroom.
  - Spectral tilt is now -4.82 against the reference's -4.88 dB/oct (was -4.65).
- **Width, mono-safe.** The master width is 1.3 (was 1.2) with mono below 150 Hz (was 120). An automation lane holds it at
  1.1-1.15 in the drumless intro and breakdown, which are wide on their own. The intro correlation was 0.06 with red
  low-end flags; it is now 0.18 and clean.
- **Ending.** The master decay over the last chord now runs to -26 dB instead of -15. The pad's release and the hall tail
  used to drop audibly from about -37 dB; now the struck chord simply dies away.

## Final numbers (full render)

- **Loudness:** -10.7 LUFS-I, LRA 3.8 LU, true peak -1.17 dBTP, PLR 9.5 dB
- **Stereo:** width 23 % overall, 50 % above 150 Hz in the full sections; correlation 0.63, 1.00 below 120 Hz; intro 0.18
- **Space:** lush in every section; reverb -11.1 LU, echo -18.4 LU, bed -1.3 dB against the lead (chorus 1 / 2 / final:
  -1.0 / -1.5 / -1.5)
- **Report:** 0 clicks in the mix, 0 errors, 0 warnings, 3 info notes:
  - 42 masked clicks in the bass alone. They are the saw edge of the octave bass when its filter envelope opens.
  - Brilliance shared by drums and riser in build 1.
  - Brilliance shared by drums and hook in the final chorus.
- **Sections (LUFS):**

| intro | verse1 | build1 | chorus1 | verse2 | build2 | chorus2 | bridge | final | outro |
|---|---|---|---|---|---|---|---|---|---|
| -13.8 | -12.4 | -10.6 | -10.0 | -11.7 | -10.7 | -9.6 | -12.0 | -9.4 | -10.3 |

- **Compare against Nightcall** (loudness-matched, band differences in dB, mix minus reference):

| | sub | bass | lowmid | mid | presence | brilliance | air |
|---|---|---|---|---|---|---|---|
| whole song | -1.0 | +0.8 | -0.4 | +1.2 | -0.4 | +1.4 | -1.2 |
| chorus 2 | -0.9 | +0.6 | -1.2 | +1.9 | +0.7 | +2.0 | -0.5 |
| final chorus | -0.5 | -0.1 | -1.3 | +1.8 | +1.3 | +2.6 | -0.2 |

- **Other compare metrics:**
  - Tilt -4.82 vs -4.88 dB/oct.
  - Loudness range 3.8 vs 3.5 LU; crest 12.5 vs 11.0 dB.
  - Punch (mix vs reference): kick 12.0 vs 15.8 dB, snare 10.5 vs 11.7 dB, hats 13.3 vs 16.9 dB.
  - Width above 150 Hz 52 % vs 10 %. The reference is nearly mono; the user asked for lush.

## Remaining weaknesses

- **Punch:** kick and hats still stand 3.6-3.8 dB less proud than on Nightcall. It is a dense, lush wall at 7.3 dB of limiter
  drive against a sparse record, and the presets document the same 2-5 dB gap.
- **Final chorus brightness:** it is +2.6 dB brighter at 6-12 kHz (hats, tambourine, bells and hook together), which is the
  climax's sheen.
- **Robot voice:** measured, not heard. It sits about 8 dB over the bed while it speaks in the breakdown, and level with the
  pad in the intro. Intelligibility was not verified by ear.
