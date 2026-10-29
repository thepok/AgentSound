# Orchestra stage UI

Orchestra visualization with interchangeable backgrounds, 32 instrument voices and 23 transparent illustrations. The design page uses manually controlled example levels. The optional video exporter measures real individual audio tracks.

From the repository root:

```powershell
py -3.12 -m http.server 8772 --bind 127.0.0.1 --directory tools/orchestra-stage
```

Open http://127.0.0.1:8772/. Choose a preset, add voices from the catalogue or use **All voices on stage**. The **Layout test** slider fills the stage with 1–80 dummy instruments; zero returns to the song ensemble. Local background images stay on the computer. Clean view hides the controls.

`layout.js` provides the reusable `layoutStacks()` geometry function. Each region selects the row/column arrangement with the largest fitting scale. Icons, labels, meters and gaps scale together, with no minimum size that could force overflow. `orchestraPlan` supplies separate stage regions, keeping soloists clear of the strings. Other settings can supply their own non-overlapping regions. At very dense settings, labels necessarily become small.

`catalog.js` maps visual voices to artwork, including solo variants, Hero Sax, choir and organ registration aliases. `stage.js` connects controls and exposes `window.orchestraStage` (`setBackground`, `setInstrumentState`, `addVoice`, `setScene`, `getScene`, `getLayout`) for future integration. Icon generation prompts are preserved beside the assets.

The orchestra arrangement anchors artwork feet to curved terrace surfaces. Upper and middle terraces use one row when the nominal icons fit at 78% size or larger, otherwise two staggered rows. Broad middle rows retain their side positions when scaled; the lowest terrace has separate left/right groups and an empty center. Each terrace scales independently: a crowded middle row cannot shrink a sparse upper row. A collision check reduces only affected regions. Icons are displayed using their visible alpha bounds (the original PNGs are unchanged), so transparent margins do not waste cell space. Images, labels and meters stay upright.

Real export ensembles are available in the scene selector via `review-scenes.json`. The dummy-count slider deliberately tests varied layouts; equal counts do not imply the same family distribution. Use a real ensemble preset to reproduce a particular exported song.

Two generated transparent stage floors (walnut and oak) can be selected independently of the background. Assets and exact built-in Imagegen prompts are in `assets/stages/`.

The preview checks `revision.json` periodically and reloads when it changes.

## One-song video

Generate a song with `endless orchestra --stems --keep`, then keep the preview server running and execute:

```powershell
py -3.12 tools/orchestra-stage/render_video.py D:/tmp/my-song/001-title --out D:/tmp/stage.mp4
```

Requires numpy, scipy, Playwright, system Microsoft Edge and ffmpeg. Output is 1920×1080 at 12 fps by default, with the original mastered mix as AAC audio. `--preview` renders a still only. The exporter uses fixed -60 to -12 dBFS RMS levels with a 220 ms release; choir and organ registrations combine powers into one visual group. Shared bus stems are excluded. Gold means an active solo voice, not inferred musical lead. Video duration follows the mix, trimming the small extra stem tail. A preview PNG, encoding log and metadata JSON accompany the video.

For longer sets, `render_video_fast.py` exports the same UI using cached browser-rendered instrument states. It supports `--background PATH`, streams WAV/FLAC analysis using soundfile, and needs no running HTTP server. It verifies representative frames against the live browser before encoding. Example:

```powershell
py -3.12 tools/orchestra-stage/render_video_fast.py D:/tmp/my-song/001-title --background D:/tmp/autumn.png --out D:/tmp/stage.mp4
```
