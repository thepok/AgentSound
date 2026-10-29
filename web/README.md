# Endless browser app

This is the maintainable source of the existing GitHub Pages app, imported from
`thepok/thepok.github.io` commit `5b44e5175ba86d72a59b2aa46ce6c011d7befeb2`,
directory `music/endless`. App revision **p11**, composer release **web7-925b025c26**.
The previous `local/web/ghpages` checkout is retained but is no longer the editing location.

## Run locally (from the AgentSound root)

```sh
python tools/wasm/runtime.py
python -m http.server 8778 --bind 127.0.0.1 --directory web
```

Open http://127.0.0.1:8778/. The first command downloads the pinned runtime files
from the exact Pages commit and verifies every SHA-256 and file size. Existing
correct files are reused; changed files are refused, not silently overwritten.
Pyodide 314.0.7 is loaded separately from the version-pinned CDN by the app.

On the original development machine, restore without downloading:

```sh
python tools/wasm/runtime.py --from local/web/ghpages/music/endless
python tools/wasm/runtime.py --verify
```

## What belongs in Git

- HTML/JS, workers, service worker, manifest and icons here.
- Sample indexes, mapping metadata and attribution/license text under `samples/`.
- `runtime-lock.json`: the exact 6,206 runtime files, hashes, sizes and immutable source URL.
- `tools/wasm/`: the browser composer adapter and portable build/restore/staging tools.

The roughly 472 MiB runtime payload is present locally after restore but ignored:
compiled `engine/`, `py/repo.zip`, compressed opening-piece banks, and audio samples.
SDKs, compiler caches, old working copies and historical experiments remain in ignored `local/` or `build/`.
No large audio files or SDK installation are added to Git.

## Builds and releases

See [the WASM tools](../tools/wasm/README.md). A current-engine build goes to `build/`,
not over the pinned browser runtime. The native generator has evolved since this
browser release: replacing its source snapshot alone would invalidate the banks,
recipe version, sample lookup tables and reproducibility checks. This migration
preserves the existing working release; it does not silently upgrade its music.

Prepare a verified standalone site in a new directory:

```sh
python tools/wasm/stage_site.py --out build/pages-endless
```

The output can be copied to `music/endless/` in the Pages repository. This command
does not push, publish, or overwrite an existing checkout.

Retain [LICENSES.md](LICENSES.md), `samples/ir/license.txt` and choir attribution
when distributing. Samples retain their individual licenses; they are not
relicensed under AgentSound's code license. Existing release/audit notes are in
[RELEASE_NOTES.md](RELEASE_NOTES.md). `source-version.json` records the composer's
earlier p9 metadata; the actual UI revision is p11 in `app.js` and the runtime lock.
