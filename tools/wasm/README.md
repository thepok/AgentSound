# Browser / WASM tools

Run commands from the AgentSound repository root with Python 3.12+.

| Tool | Purpose |
| --- | --- |
| `runtime.py` | Restore locked runtime from pinned Pages commit or `--from` local release; `--verify` checks all files offline. |
| `build_engine.py` | Copy current `engine/`, `third_party/`, CMake into an isolated ignored build directory, apply browser patches, compile with activated Emscripten. |
| `patch_engine.py` | Add streaming PCM callback and sample-cache reset; guard Windows CLI code. Exact source anchors fail on drift. |
| `compose_web.py` | Browser adapter extracted from the actual shipped `py/repo.zip`, rather than an older experimental working copy. |
| `package_composer.py` | Repackage the pinned source/text-asset snapshot with this adapter into `build/wasm/repo.zip`. |
| `asset_version.py` | Explicit maintenance tool: regenerate sample cache hashes and `SV` in `web/app.js` after an intentional sample change. |
| `stage_site.py` | Verify and copy the runnable app to a new deployable directory, without publishing. |

## Compile the current engine

Install and activate Emscripten using its SDK, and put CMake and Ninja on PATH.
This machine's existing SDK is under `local/web/wasm-space/emsdk`; it is not tracked.
The compiler used for migration validation reports Emscripten 6.0.12.

```sh
python tools/wasm/build_engine.py --emsdk PATH_TO_EMSDK --work build/wasm-current
```

`EMSDK` can supply the SDK path. `--prepare-only` checks copying/patching without a
compiler. Choose a fresh `--work` directory for a fresh source snapshot; the tool
refuses to overwrite an existing source tree. CMake's generated build can be resumed
with `cmake --build build/wasm-current/engine --parallel 4` in the same SDK environment.
The build creates `agentsound.js` and `agentsound.wasm`; it does not replace the
locked known-working release under `web/engine/`.

## Composer packaging

```sh
python tools/wasm/package_composer.py
```

This preserves every entry of the restored release archive except the explicit
tracked browser adapter. It deliberately does not overlay current `agentsound/`:
a generator upgrade requires a new recipe version, matching banks, sample indexes,
and sample-derived lookup tables. Existing native/mirror/Pyodide replay checks are
described in `web/RELEASE_NOTES.md`; the old one-off trace and audit scripts depend
on obsolete temporary files and were not promoted as portable build tools.

The pinned archive includes the exact historical Python source and text assets,
retrievable independently of the old local workspace. Its converted audio assets
are external files covered by `web/LICENSES.md` and `web/runtime-lock.json`.
