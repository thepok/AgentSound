# Until the Credits Roll

- **Style:** Retrowave pop anthem, instrumental (The Midnight / Gunship)
- **Tempo:** 118 BPM, 4/4, 123 bars, about 4:12 plus the ring-out (4:19 file). The outro slows to 94 BPM.
- **Key:** E minor. The final chorus and outro go up a whole step to F# minor, and the song ends on an F# **major** chord.
- **Sound:** built on the band preset `bands.retrowave`, calibrated against The Midnight's "Sunset", plus extra players.
- **Delivery:** `METADATA` sets album *Neon Archive*, genre Synthwave. `COVER` uses the synthwave style with the sunset palette.
- **Folder:** `songs/skyline-heartbeat/`. The robot's speech cache is committed under `samples/speech/`.

## The song

This is the last scene of an 80s movie. The hero drives into the sunrise and the credits start to roll.

The whole piece grows from one phrase, "E . D E G":
- **Intro:** glassy DX bells play the phrase.
- **Choruses:** it becomes the brass/saw anthem hook. The hook has pushed notes, gaps where the brass and sax
  answer, an 8th-note run and a long held B5 peak.
- **Sax:** a tenor sax (sampled and played with legato, glides, swells and delayed vibrato) is the song's second
  voice:
  - it carries the verse-2 melody;
  - it answers the hook in chorus 2;
  - it plays an 8-bar solo in the breakdown, over new chords (Cmaj7, Dadd9, Bm7, Em9) with the pads blooming into
    the shimmer. The solo climbs to its E5 peak as a half-time pulse comes back;
  - it opens the outro.
- **Vocoder:** a robot choir speaks the title twice. The first time is in the breakdown over Em9, before the sax
  enters. The second time is over the final F# major chord, where the vocoder freezes on "roll".
- **Key change:**
  - The lift plays the pre-chorus melody in E minor and pushes up to C# major only in its last bar.
  - The final chorus then lands a whole step higher on its downbeat.
  - The last chorus is the only place the hook reaches E6 (F#6 after the key change).
- **Ending:** the outro climbs D-E to F# major through a tempo-map ritardando (118 to 94 BPM). One last hit and a
  crash follow, then bells, choir and the robot ring out while the band fades like the closing credits.

## What changed against v1 (and against CRITIQUE_v1.md)

### Sound

The sound was rebuilt on `bands.retrowave`:
- the 80s pop kit with a Linn clap into the keyed gated reverb;
- the preset's octave bass, Juno pad, bright DX e-piano and brass stabs;
- the Fairlight CMI choir;
- a brass lead;
- 224XL IR hall and plate, the dotted-8th echo, and the preset's master.

Extra tracks on top of the preset:
- **sax:** the MTG tenor sax, played with `articulation.perform`;
- **saw:** a supersaw double of the hook (only in the second half of chorus 1);
- **harm:** a brass-lead harmony line;
- **brass2:** a DX brass layer panned against the analog brass;
- **Strings and descant:** Jupiter strings plus a string descant above the hook;
- **Arps:** two pluck arps and a glass arp;
- **perc:** a Forzee kit for real crash cymbals and tambourine (the pop kit has no cymbals);
- **Low end:** a sub for the breakdown and the last chord;
- **robot:** the vocoder choir;
- **Transitions:** riser, impact and downlifter.

### Composition fixes from the critique

The v1 score had already taken the hook rewrite, the key change on the downbeat and the kick under the tom fills.
Kept:
- the rewritten hook: pushed notes, bars of space, the 8th-note run and a long B5;
- the key change on the downbeat (C# to D);
- the tom fills only into bars 8 and 16, with the kick under them;
- the brass answering in the gaps.

New in this version:
- **Chorus 1 is held back.** The saw double and the tambourine come in at its half. Strings only play its second half.
- **Chorus 2 is different:**
  - its bar 12 run keeps climbing (`d3`);
  - the bass gallops;
  - the e-piano comps;
  - the sax answers the held F# in the D-bar gap (the brass leaves that gap to it);
  - there is a harmony line, and the choir and descant join in the second half.
- **The final chorus is the biggest:**
  - key change, 16th octave bass, choir all the way through;
  - an octave-up double of the hook at -10 dB (it replaces the old octave-down double);
  - the one-off E6 (F#6) peak;
  - brass2 panned against the brass, both arps;
  - it measures +1.2 LU over chorus 1.
- **The breakdown is a real bridge:** the robot says the title, then the sax solo plays, and drums come back for the
  last 4 bars.
- **Verse 2 is a new voice:** the sax takes the melody.
- **The ending uses the tempo map** (ritardando into the last chord) and the band fades, instead of a flat plateau.

### Mix moves on top of the preset

These come from the loudness-matched compare against "Sunset".
- **Energy arc:** `gainDb` automation on plain `music` and `drumbus` group buses. The verses sit 3.5–4.5 dB back,
  the breakdown 6 dB back, and the intro swells in. LRA went from 3.4 to 5.4 LU.
- **Kick punch:**
  - kit compressor attack 10 to 25 ms and ratio 3.5 to 2.5;
  - accented kicks;
  - bass ducker depth 5 to 14 dB (hold 60 ms, curve 0.5). The kick/bass low-end separation went from 1.2 dB
    (a masking warning) to 3.0 dB (they alternate);
  - pad ducker 5 to 7 dB;
  - limiter drive 3.5 to 3.8 dB.
- **Tone:**
  - bass low shelf and a 70 Hz bell for low-end weight;
  - high shelves on the crash/tambourine, riser and impact;
  - kit air shelf off and a 3.5 kHz dip on the kit;
  - no presence lift on the lead and a 3.5 kHz dip on the e-piano. The profile's "harsh presence" warning was at
    +4.0 dB before and reads +3.4 dB now;
  - master high shelf +5.5 to +4.0 dB.

## Final pass (A&R review)

What a listener heard, and what changed in `song.py`:

- **The backbeat was buried.** Zoomed into a chorus-2 snare, the hit did not show above the synth wall at all
  (the mix waveform stayed flat through it). Fixes:
  - the snare +2.5 dB and the Linn clap +1 dB inside the pop kit (the kit's `gains`);
  - the drum bus +1 dB and the music bus -1 dB across the whole energy arc;
  - the kit's tape saturator drive 5 to 2.5 (it rounded the kick's attack off);
  - brass, brass2, e-piano, saw, harmony, violin and glass now also duck 3 dB under the kick (the melodies - lead,
    soft lead, sax, robot - stay steady), so each kick opens a hole in the chorus wall.
- **The bass was the loudest part** (-17 dB RMS, 3 dB over the kit) and its weight sat at 40-50 Hz (+3 dB against
  "Sunset") while 56-90 Hz was 2 dB light. Fixes: the bass -1 dB more, its 50 Hz low shelf removed and its bell
  moved to 80 Hz +3.5 dB; the kit gets an 80 Hz bell +2.5 dB and its low shelf goes from -1.5 to +1 dB. The bass and
  kit high-passes open down to 27 / 25 Hz.
- **The builds were as loud as the choruses they lead into** (pre-chorus 1 -10.9 vs chorus 1 -10.2 LUFS). The
  pre-choruses start 1 dB lower and ramp only to -2.5 / -3 dB before the drop, and the risers play 2 dB lower. The
  lift now starts low (-5 dB) and climbs, instead of jumping +3.4 LU out of the breakdown. The verses, the intro and
  the breakdown sit 1 dB further back. Every chorus now arrives +1.0 / +1.1 / +1.9 LU above its build.
- **The gated snare reverb was out of phase** (return correlation -0.17, 142 % wide: the 80s burst partly cancelled
  in mono). Its width is 0.9 now (correlation +0.12, 79 %).
- **The sax answers in chorus 2 were an aside** (-23.5 dB RMS in their gap). They are played harder (velocity 114:
  the brighter, forte samples), +2.7 dB.
- **Air**: the master's high shelf +4 to +3 dB.
- **Loudness**: the limiter drive 3.8 to 5.2 dB brings the song back to -10.8 LUFS after the quieter bass and wall.

Tried and dropped: a 3 dB kick+snare ducker on the whole music bus (it pumped the lead too; the per-part ducker is
cleaner), drums +2 / music -1.5 dB (the kick then drove the limiter and its punch fell to 12.9 dB), and 2 dB less
limiter drive (only +0.7 dB snare punch for -0.9 LU).

## Final numbers

Whole song, `python -m agentsound build`, profile synthwave:

| measure | value |
|---|---|
| loudness | -10.8 LUFS integrated |
| loudness range | 5.1 LU |
| true peak | -1.10 dBTP |
| width (whole mix) | 30 % |
| width above 150 Hz | 66 % |
| correlation | 0.54 |
| correlation below 120 Hz | 0.99 (lows mono) |
| reverb | -10.7 LU |
| echo | -16.6 LU |
| bed vs lead | -2.5 dB |
| clicks in the mix | 0 |
| warnings | 0 |
| info notes | 5 |

The 5 info notes:
- clicks: 7 masked clicks in single parts. They are the octave-bass saw's own waveform edges, and none of them is
  audible in the mix.
- masking (2): kick and bass share the sub and bass bands but alternate (ducking 3.3 dB).
- node_hot (2): the `music` and `drumbus` group buses peak at +0.6 / +0.5 dBFS in float before the master (not
  clipped).

Section loudness (LUFS):

| section | loudness | vs previous |
|---|---|---|
| intro | -16.1 | |
| verse 1 | -11.9 | +4.2 |
| pre 1 | -11.1 | +0.8 |
| chorus 1 | -10.0 | +1.0 |
| verse 2 | -12.2 | -2.2 |
| pre 2 | -10.8 | +1.4 |
| chorus 2 | -9.7 | +1.1 |
| breakdown | -14.1 | -4.4 |
| lift | -11.1 | +3.1 |
| final chorus | -9.2 | +1.9 |
| outro | -10.4 | -1.2 |

Compare against The Midnight "Sunset" (whole song, loudness-matched):

| measure | ours (before this pass) | ours | Sunset |
|---|---|---|---|
| loudness | -10.8 LUFS | -10.8 LUFS | -9.7 LUFS |
| width above 150 Hz | 71 % | 69 % | 65 % |
| correlation | 0.52 | 0.54 | 0.35 |
| crest | 13.7 dB | 13.7 dB | 14.8 dB |
| crest below 150 Hz | 13.2 dB | 14.1 dB | 15.4 dB |
| loudness range | 5.4 LU | 5.1 LU | 7.4 LU |
| kick punch | 13.3 dB | 14.8 dB | 19.2 dB |
| snare punch | 8.8 dB | 8.6 dB | 12.7 dB |
| hat punch | 15.2 dB | 15.5 dB | 15.6 dB |
| after-hit energy | -0.8 dB | -1.4 dB | -1.8 dB |
| tilt | -3.60 dB/oct | -3.6 dB/oct | -3.51 dB/oct |

Tone per region, ours minus Sunset: sub -1.3, bass -0.9, low mids -0.2, mids +1.2, presence -0.4, brilliance +0.1,
air (12-20 kHz) +2.7 dB (mostly above the Opus reference's ~16 kHz roll-off). In 1/3 octaves everything from 35 Hz
to 11 kHz is within about +-2 dB; the 40-50 Hz bump (+3 dB) is gone. 22-35 Hz stays 3 dB light (sub-sonic).

## Remaining weaknesses

- **Punch:** the kick sticks out 15 dB (the record 19), the snare 9 (13). The mid-band measure is set by the
  continuous chorus wall (16th gallop bass, brass, arps) and a -1 dBTP ceiling, while the record peaks at +1.6 dBTP;
  louder snares only drove the limiter (+2.5 dB snare moved the measure by 0). Audibly the backbeat now cuts
  through.
- **Low end:** mono (the record is slightly stereo down there); 22-35 Hz about 3 dB light (not heard on a phone).
- **Loudness:** 1.1 LU under the record, on purpose (profile range, crest kept).
- **The robot voice** is Windows TTS (Zira) through the vocoder: intelligible, robotic by design.
- **Credits:** the committed speech file is listed as "Unknown (own file?)" with an absolute path - a gap in the
  credits tool (it does not know speech caches are own TTS renders), not in the song.
