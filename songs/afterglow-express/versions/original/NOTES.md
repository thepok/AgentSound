# Afterglow Express

Original instrumental outrun / nightdrive synthwave, composed from recipes/synthwave.md.
110 BPM, D minor, 96 bars, approximately 3:33 including the effect tail.

## Composition
A syncopated eight-bar pulse-lead theme develops from a rising fifth-to-tonic cell.
Verses use Dm9 - Bbmaj7 - Fadd9 - C. Builds reach A major, the harmonic-minor
 dominant, before the chorus opens on Bb. The chorus answer climbs to F5;
its last bar uses C# over A7 to lead back into the next phrase.
The bridge introduces G major (a Dorian colour), with E-piano and glass melody.
The second chorus adds strings and a supersaw double; the final twelve-bar
chorus has a new four-bar resolution. The outro settles into D minor.

## Production
Linn-style drums, snare-triggered gated reverb, octave bass, Juno-style pads,
DX7 E-piano and glass, dotted-eighth echo, pulse lead and supersaw.
Kick-keyed sidechain keeps bass and pads out of the kick attack. The arpeggio
is high-passed to separate it from the warm pad. Bass frequencies remain mono.
Deliberate quiet intro, bridge and outro contrast with the driving choruses.

## Files
song.py: editable composition.
out/mix.mp3 and out/mix.wav: finished audio.
out/report.json and out/*.png: engine measurements and visual review.
Rebuild from the repository root: python -m agentsound build songs/afterglow-express

Validation is based on the engine report and rendered analysis images, not a listening review.

Final render: 212.7 s, -11.5 LUFS-I, -1.12 dBTP, correlation 0.84, low-band correlation 1.00. Zero errors, warnings or clicks. Six informational notes cover deliberate section contrasts and moderate spectral overlap.
