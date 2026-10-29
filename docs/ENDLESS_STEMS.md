# Optional individual audio tracks

```powershell
python -m agentsound endless orchestra --count 1 --seed 100 --stems --out D:/tmp/orchestra-stems
```

`--stems` enables the existing renderer's stem export in the same render pass. Each accepted tune gets `stems/<track-id>.wav` and `stems/<bus-id>.wav` beside its normal mix MP3. It works with all Endless genres. Without the flag, output and generation behavior remain unchanged.

Stems are retained even without `--keep`; that separate option retains `mix.wav` and `song.render.json`. Failed candidates and their stems are discarded by the existing quality gate. Disk usage increases with the number of tracks and duration.

Every stem shares the same start time and duration with the other stems, including rests and the render tail. Starts also align with the latency-compensated mix; stems can extend past its end by the master latency (`report.json.render.latencySamples`, e.g. 288 samples / 6 ms). Use the mix duration for video and trim only the extra stem tail if equal lengths are needed. These are the renderer's post-processing/post-fader node outputs, before the master chain: track effects, pan and gain are included. Shared reverb and other bus processing live in separate bus stems. Do not sum every track and bus indiscriminately: routed buses can contain the same audio again, and the master processing is not baked into the individual tracks. No source separation or separate solo re-renders are involved.

`tune.json` lists the files under `files.stems.tracks` and `files.stems.buses`, keyed by the original renderer IDs. This allows a visualization to associate a waveform with e.g. `violins1`, `oboe_solo` or `hero_sax` without guessing from display names. The feature only exports audio; it does not calculate live levels or alter composition.
