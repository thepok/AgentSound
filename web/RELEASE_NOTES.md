# Endless browser build

Current release: `web7-925b025c26`, page revision `p11`.

The symphonic generator includes reduced automatic phrase shaping, role-aware
theme accents, and foreground dynamics for counter-lines answering during the
melody's rests. Soloists remain enabled. Written rests, subito dynamics and
deliberate climax accents remain part of the music.

The Python source snapshot is identified in `source-version.json` and shipped
in `py/repo.zip`. The WASM audio engine and sample assets are unchanged. All 100
orchestral opening pieces were regenerated; the 600 piano opening pieces retain
their render hashes and only receive the new recipe version.

Validation: 18 pieces (three each for orchestra set seeds 4242, 7, 123456 and
piano sets new-age/4242, klassik/77, walzer/78) match between native Python,
the browser mirror and Pyodide after normalizing the local sample-root path.
Recipe replay and continuation after the bank opening pass. All opening pieces
reference available sample assets, with no missing composer lookup tables.
Muted Chrome playback was checked on desktop and a 375x812 mobile viewport;
the repeat visit used all 502 required samples from cache with no app errors.


## Playback reliability (p10)

Mobile MediaSource playback waits for a piece to finish rendering before starting it: locking the screen can throttle the render worker, invalidating its foreground speed estimate. Initial startup may take longer. Desktop progressive playback is unchanged. The Web Audio fallback and operating-system audio interruptions remain separate limitations.

A persistent error panel shows a readable explanation and the last 20 technical messages. Worker errors and encoder completion failures are surfaced; failed render completion is no longer accepted as a complete song. Recovery is manual via Skip, not an automatic repair guarantee.

Validation: mobile readiness cases, injected failure handling, JavaScript syntax and error-panel rendering at 420px width passed. A live desktop run started four pieces with three transitions over approximately 16 minutes of media time (first four minutes normal speed, then accelerated), without playback errors. Actual phone lock-screen behavior still needs device testing.


## Progressive mobile playback restored (p11)

At user request, mobile once again uses the original render-ahead speed estimate instead of waiting for complete rendering. A MediaSource buffer underrun during a started song now appears in the persistent GUI error panel. Startup, seeks and completed-song gaps are excluded; repeated waiting events are deduplicated until playback recovers. The panel records recovery without erasing the technical history. Background rendering can still be throttled by the phone OS.
