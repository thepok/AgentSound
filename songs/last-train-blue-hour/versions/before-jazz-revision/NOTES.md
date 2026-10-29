# Last Train, Blue Hour

Original cinematic piano / trip-hop. Nominal 78 BPM, D minor, 64 bars.
Created after the requested concept: intimate solo piano, a lazy groove, a distant synth
space, a four-bar flash of virtuosity, and the opening idea returned with a brighter harmony.

## Composition and performance
- Empty Platform: solo sampled grand, open ninth voicings and the D-A-E melodic cell.
- Engine Starts: restrained DX7 bass and a dry, syncopated rim/hat beat enter.
- Window Lights: the piano theme and a falling answer trade space over Dm9-Bbmaj9-Fmaj9-Cadd9.
- Blue Hour: the first wide analog pad arrives behind the piano with a 5.1-second modulated hall.
- Between Stations: drums and bass leave; Gm9/A7 tension hangs under sparse piano replies.
- A Private Smile: four hand-authored bars of turns, chromatic approaches and rising arpeggios.
- Homeward: the band returns with the original theme.
- Last Train: the band falls away; D minor turns to D major 9, with F# in the final piano answer.

CC64 sustain follows the harmony, with more frequent clearing in the four-bar flourish.
Rolled chord attacks, purposeful rests and varying velocities shape the piano part.
The entire ensemble follows one performed-time curve: about 73 BPM at the opening,
77-80 through the groove, 82 in the short flourish and a gradual final ritardando toward 62.
Bass stays behind the piano; drums have no clap layer or gated noise reverb.

## Rendering and provenance
Piano: GeneralUser GS acoustic grand (GM 0).
Drums: GeneralUser GS Room kit (GM percussion program 8), subdued sampled kick/snare/rim/hats.
Source: https://github.com/mrbumpy409/GeneralUser-GS, S. Christian Collins.
License: assets/soundfonts/GeneralUser-GS-LICENSE.txt.
Samples are rendered by the local FluidSynth 2.6.1 executable under work/jazz-tools/.
Bass: AgentSound's original DX7 BASS 1 ROM patch, with octave compensation.
Pad and hall: native AgentSound VA / reverb engine. No C++ engine changes.

Build from D:/Repos/AgentSound:
python songs/last-train-blue-hour/render.py

out/mix.mp3 and out/mix.wav are the finished mix.
out/piano.mid, drums.mid and performance.mid are editable performed-note exports.
performance.mid substitutes GM bass for the native DX7 and does not include the analog pad.
out/master-analysis.json describes the final combined master and stem gain calibration.
The native out/report.json and native analysis images describe ONLY the synth/bass bed;
the silent intro and synthwave loudness warnings there are expected for that partial stem.
Audio validation uses decoding, master loudness/peak readings, click detection and waveform
inspection; it is not a direct listening review.

Final validation: 207.49 seconds, -15.50 LUFS-I, -1.95 dBTP, 5.3 LU loudness range, zero detected clicks. MP3 decodes without errors. Pad entry 1:15.2; four-bar piano flourish 2:04.2; solo-piano coda 2:52.5.
