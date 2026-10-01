# Children of Neon - production notes (re-production v2 + final A&R pass v3)

Dream-trance x retrowave tribute to Robert Miles' "Children": 122 BPM, F# minor, ~4:07 including the ritardando
and the reverb tail. The mood and production language are borrowed (lone-piano intro, plaintive piano riff,
pads, four-on-the-floor lift); the melodies and progressions are original.

Build: `python -m agentsound build songs/children-of-neon` (needs `AGENTSOUND_SAMPLES` pointing at the sample library).
Reference: The Midnight - "Sunset" (loose reference for tone and width).

## What changed against the first draft

Composition
- Form: intro 16 | theme 8 | verse 16 | build 8 | drop1 16 | breakdown 8 | rise 8 | drop2 16 | **lift 8** | outro 16.
  The flat 'reprise' became a **lift a whole step up (G# minor)**, entered over the VII->VI pivot (E major) with a
  riser, snare roll and impact.
- The verse has its **own calmer melody** (long notes rising to A5, leaning back into the hook's C#5), so the hook's
  return in bar 9 of the verse is a lift; the hook no longer plays three times in a row.
- The hook still never closes (it hangs on B over E) - until the **very last phrase**: B-A-G# resolves to F# on the
  final F#m(add9) chord. Ending: ritardando 122 -> 98 BPM over the last bars, rolled final chord on the sustain
  pedal, beds fading under it, 9 s reverb tail (no hard cut).
- New layers: violin **descant** (C#6-D6-C#6-B5 sigh) in the second half of drop 2 and the lift; supersaw doubled
  in diatonic thirds there; Fairlight choir; real string section; a **vocoder robot choir** singing "children of
  neon" (whisper in the intro, the breakdown with a frozen 'neon' vowel into the rise, a last whisper on the final chord).
- Build: trance off-beat bass, and the low end drops out in its last bar (only the snare roll + riser lead in).
- Every repeat changes: theme (piano alone) -> verse (new melody, tonic pedal bass) -> verse B (hook + high octave,
  16th left hand, strings, glass arp) -> drop1 (supersaw, rolling bass; octaves in the 2nd half) -> breakdown
  (augmented hook over new colours VImaj7-VII6-v7-i9, robot choir) -> drop2 (the climb to C#6; thirds, choir,
  descant, 16th arps in the 2nd half) -> lift (G# minor, everything) -> outro (soft hook, lone cells, resolution).

Sound
- Built on `bands.retrowave(lead='supersaw', without=('keys', 'brass'))`: 80s pop kit with a TR-909 kick, 909 open
  hat / crash / ride and Linn clap + tambourine mapped in (the preset kit has no cymbals), keyed gated snare, octave
  bass, Juno pad, Fairlight choir, supersaw, 224XL IR hall + plate, dotted-8th echo, master chain.
- The DX7 piano became the **Salamander grand** (sampled/grand_piano) with sustain-pedal automation (re-pressed
  after every chord change), compression, a presence lift, and hall/echo/shimmer sends that bloom where the beat
  is gone. Real strings (VPO section + violins), dream pad with shimmer, glass + pluck arps with the echo.
- Mix moves on top of the preset (measured with `compare` against Sunset): kit compressor attack 25 ms, kit air
  shelf -5 dB at 8 kHz, snare +6 / clap +1 / kick +2; bass ducked 10 dB by the kick and 6 dB by the snare, low shelf
  -4 dB < 48 Hz, +3 dB at 68 Hz, -3.5 / -2.5 dB at 160 / 210 Hz; supersaw -2.5 dB (the piano leads); pad and strings
  cut at 480 Hz / 1.3 kHz for the piano; master air shelf 5.5 -> 4 dB, exciter 0.75 -> 0.55; piano stereo width
  0.7 and the gated return narrowed to 0.6 (mono-safe on a phone speaker); energy arc via limiter drive per section.

## Final A&R pass (v3)

Judged the v2 render by the numbers, images, stems and against "Sunset"; what a listener would have heard and the fix:
- **Drop 1 was an anticlimax**: the build (snare roll + riser) read louder (short-term max -9.6) than drop 1 itself
  (-10.4). Limiter drive now pulls back in the build (3.2 dB) and steps up at the drop (4.8); the rise holds back the
  same way before drop 2. Build -12.2 -> drop 1 -10.6, rise -13.0 -> drop 2 -9.6 LUFS.
- **The solo-piano theme collapsed in mono** (piano stem correlation -0.34..+0.1: the AB pair + Juno chorus): piano
  width 0.7 -> 0.55, chorus mix 0.12 -> 0.08; the hall return widened 0.7 -> 0.85 to keep the space. Theme
  correlation 0.57 -> 0.69.
- **Pad masked the piano's left hand in the theme** (the only warning): the theme now opens on the piano alone, the
  bed arrives with the bass in bar 5.
- **Players, not a keyboard**: right hand phrased with an arch per phrase and heavier downbeats
  (humanize.phrase_dynamics), left-hand broken chords with a pulse under the fingers; the string section enters a
  few ms apart per voice and breathes on CC11 at every chord; the violin descant is doubled by a VSCO solo violin
  played with legato, swells, delayed vibrato and bow changes (articulation.perform), +3 dB so it is heard.
- **Groove**: a Linn cabasa 16th shaker (ghosted) in verse B and the drops; the kit's tape drive 5 -> 2.5 and a 185 Hz
  dip so the hits are less rounded.
- **Kick room**: plate, shimmer and supersaw duck 4 dB and the hall 2.5 dB on every kick, the piano 1.5 dB.
- Tone vs Sunset: kit air shelf -6.5 dB, supersaw -3.5 dB above 8 kHz (air read +2 dB), piano presence +3 -> +2 dB,
  master exciter 0.55 -> 0.45 and the preset's 3.5 kHz lift 1.5 -> 0.8 dB (presence read +4 dB vs the synthwave
  profile), bass low shelf -5.5 dB below 46 Hz (the F#1/E1 roots read +3 dB at 36-45 Hz).
- Vocoder attack 5 -> 20 ms, sibilance 0.25: the words read, the 'ch' is soft; in the breakdown the Fairlight choir
  steps back 4 dB and the robot choir forward 2.5 dB.

## Final numbers (last build)

- -11.9 LUFS-I (profile synthwave, target -12..-9), true peak -1.18 dBTP, LRA 8.3 LU, PLR 10.7 dB.
- Sections (LUFS): intro -16.7, theme -14.3, verse -12.6, build -12.2, drop1 -10.6, breakdown -13.5, rise -13.0,
  drop2 -9.6, lift -9.0, outro -13.5 (then the ritardando and the 9 s tail).
- Stereo: correlation 0.60, width >150 Hz 56 % (Sunset 65 %), low end mono (1.00); section correlation >= 0.46
  except the pad/rain intro (0.20). Space lush in every section, reverb -12.4 LU, echo -20 LU.
- 0 errors, **0 warnings**, 0 clicks in the mix (info: 7 masked note-start transients in the bass stem).
- Compare vs The Midnight "Sunset", loudness-matched, whole song: 50 Hz - 16 kHz within +-1.5 dB except a +3 dB bump
  at 40 Hz (909 kick + low roots); below 35 Hz -3..-5 dB (the master's 25 Hz high-pass; inaudible on a phone);
  crest 14.4 vs 14.8 dB; LRA 8.3 vs 7.4 LU. Drop 2 vs Sunset: -9.6 vs -9.7 LUFS, no tone suggestion above 30 Hz,
  width 60 vs 65 %, crest 12.1 vs 14.8 dB.

## Remaining weaknesses

- Punch stays under the reference: kick 12 (drop 2: 14) vs 19 dB, snare 8-9 vs 13 dB. Sunset peaks at +1.6 dBTP
  (it clips); at our -1.2 dB ceiling every dB of drive is a dB of transient lost. Raising the kick only pushed the
  limiter harder (tested: kick +2.5 dB -> punch 11.5, loudness -0.3 LU).
- The whole song is 2.2 LU quieter than Sunset (long quiet intro/theme/outro); the drops match it.
- The vocoder words (Windows voice Zira through a 20-band vocoder) are more texture than lyric.
- Licences: 80s pop drums (no redistribution), Fairlight / 224XL / TR-909 / LinnDrum (unclear) - fine for private
  listening; the Salamander piano needs its CC-BY credit when published (out/credits.txt).

- **Piano pass (v4, user: the synth hook sounded "piepsig"):** the hook from verse B on (verse B, drops, rise, lift) now plays on the high melody piano (`sampled/piano_lead`, C#5-C#7, octave-doubled right hand, vel 96-112, re-struck B/G# instead of held notes, pedal steps, A-B pickups into the drops); the supersaw only sustains ~10 dB under it; the grand keeps the left hand and the solo-piano parts. -11.8 LUFS, width 56 %, 0 warnings, 0 clicks, sections within 0.5 LU of v3.
- **Dynamics pass (user on polaroid-summer: "sind alle Lead-Noten gleich laut?"):** the melody piano is played, not triggered: bar downbeats x1.08, 8th passing notes x0.86, grace / 16th pickups x0.7, a 4-bar arch (+-12 %, peak note x1.1, phrase ends x0.8), soft top limit at 118, the lower octave at ~70 %; first statement (verse B) vel 88 -> drops 96/104 and 100/108 -> lift 114. Top line vel 44-116; the piano_lead compressor loosened (-13 dB 3:1 -> -10 dB 2:1) so the accents survive: drop 2 onset peaks spread 15.9 dB (p10-p90 8.1 dB), r = 0.61 with velocity. Supersaw amp.velocity 0.3 -> 0.7.
