# Last Table on Hudson

Original relaxed jazz trio, 92 BPM, E-flat major, 72 bars, about 3:13 including the tail.
Two versions share the same performance: DX7 E.PIANO 1 and sampled acoustic grand.
Both use DX7 BASS 1 and quiet brushed drums.

## Music
Four-bar introduction, 32-bar AABA-style theme, 16-bar piano solo, 16-bar return,
and four-bar closing tag. Rootless left-hand voicings use thirds, sevenths and ninths;
secondary dominants and the Ab-major to Ab-minor change add a late-night colour.
The bass alternates a relaxed two-feel with walking quarters during the bridge and solo.
Swing eighths, varying note velocities, loose chord attacks and phrase rests are composed
explicitly. The piano solo is authored note by note, not generated from random scale runs.

## Sounds and provenance
DX7 E.PIANO 1 and BASS 1 are synthesized by AgentSound using its existing original DX7 ROM
banks. The bass patch compensates for BASS 1's octave-down carrier with transpose +12.
The acoustic grand (GM 0) and brush kit (GM drum program 40) use GeneralUser GS 2.0.3:
https://github.com/mrbumpy409/GeneralUser-GS
SoundFont by S. Christian Collins, https://schristiancollins.com/generaluser.php
License saved alongside the bank in assets/soundfonts/GeneralUser-GS-LICENSE.txt.
FluidSynth 2.6.1 Windows binary from https://github.com/FluidSynth/fluidsynth/releases
is extracted locally under work/jazz-tools/. No system-wide installation was made.

The C++ engine is unchanged. render.py orchestrates the native DX7 renderer, external
FluidSynth sample renderer, and FFmpeg mixing/mastering. This is a song-specific integration,
not a new native AgentSound sampler instrument. The unused soundfont piano is used only
in the grand version, not layered into the DX7 version.

## Build and files
From D:/Repos/AgentSound: python songs/last-table-on-hudson/render.py
out/dx7.mp3 and out/dx7.wav: electric piano version.
out/grand.mp3 and out/grand.wav: acoustic grand version.
out/composition-dx7.mid and out/composition-grand.mid: editable MIDI performances.
Standard GM MIDI playback approximates the DX7 bass; the audio exports use the real engine.
out/master-analysis.json: measurements of both finished mixes (target -16 LUFS-I).
The ordinary out/report.json and engine images describe ONLY the native DX7 duo before
sampled drums are mixed. Its synthwave reference targets are not jazz mastering targets.
Validation uses audio-file decoding, loudness/peak measurements and visual review, not listening.

## Expressive revision
Bass fader reduced 4 dB (from -3 to -7) in both versions. Sustain pedal follows the
harmony: CC64 in the grand MIDI, equivalent held-note durations in the native DX7 part.
Pedal clears more often in the solo to avoid blurring chromatic runs. Repeated strikes
of one pitch release the previous held voice just before the new note.
A shared performed-time curve moves from relaxed 87-91 BPM into the 94 BPM bridge,
about 98 BPM in the solo, and an 86-to-66 BPM closing ritardando. Subtle phrase-end
relaxation applies to the whole trio, so stems remain synchronized. MIDI uses performed
note positions at the nominal tempo; native section markers follow that same curve.
Eight written turns/runs, a chromatic grace-note pickup and rolled opening/closing chords
add small right-hand flourishes without changing the central melody.
