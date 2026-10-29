# After Hours piano visualization

Run `py -3.12 -m http.server 8775 --bind 127.0.0.1 --directory tools/piano-stage` from the repository, then open http://127.0.0.1:8775/.

88 MIDI keys (21–108), independent replaceable background, pause, seek, playback speed, brightness and fullscreen. With `demo/song.json` present the page plays its corresponding `demo/mix.mp3` and follows the audio clock. Without it the silent random-note prototype remains available. Gold is accompaniment (`comp`); champagne is melody (`piano`). Keys release at actual note-off even if sustain continues.

The single sustain pedal follows recorded `instrument.pedal` events, including half pedal. No una-corda or sostenuto motion is invented. Notes fade from transparent at the top to full rendered opacity at two thirds of the fall; the final third stays visible.

Prepare an existing kept endless tune:

```
py -3.12 tools/piano-stage/prepare_song.py TUNE_FOLDER tools/piano-stage/demo
```

Preparation uses the existing TempoMap, rounds note events to engine samples, quantizes step pedal changes to the engine's 32-sample automation boundary, and verifies both hands use the same pedal. It preserves key release timing separately from pedal sustain. Master latency is already compensated by the audio renderer. Arbitrary non-step pedal lanes or mismatched hands fail explicitly.

Render a whole song, with the local server running:

```
py -3.12 tools/piano-stage/render_video.py TUNE_FOLDER --out D:/tmp/piano-song-preview/song.mp4
```

1080p, default 30 fps, H.264 CRF 18 / AAC 256k from the original WAV. Fixed timestamps drive the same browser drawing code. The static backdrop and title are captured once; note and keyboard canvases are composited with the same spatial opacity mask. Exports include preview, timeline, progress, render manifest and ffmpeg log. `--limit 5` renders a short check. Browser controls are omitted in export mode.

`assets/after-hours.png` was derived from concept A with built-in Imagegen; prompt and provenance are in `assets/provenance.json`. Background uploads remain local to the browser.


Fast export: `render_fast.py TUNE_FOLDER --out OUTPUT.mp4 --url http://127.0.0.1:8775/` uses Pillow for all video frames and sends raw RGB directly to FFmpeg. The browser only bakes static approved artwork, keyboard states and stretchable note sprites once; it is closed before frame rendering. Timing, resolution, frame rate and encoder quality stay the same. The default artwork cache is `art-cache/` beside the output; `--cache` selects another reusable artwork cache; `--limit 10` benchmarks a short excerpt.

Both exporters tag standard limited-range BT.601 video consistently; browser JPEG frames explicitly convert full to limited range before encoding. This avoids a brightness jump when concatenating browser and Python segments.
