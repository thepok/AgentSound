# Vendored MSFA DX7 DSP subset

This directory contains only the narrow Apache-2.0 MSFA DSP dependency set
needed by `dsp/dx7/Dx7EngineAdapter.cpp`. It was imported from Dexed `v0.9.4`
at commit `618b318792e74386b7afc910d1365827e770222e`; it contains no Dexed app,
JUCE, librarian, UI, preset, or GPL wrapper source.

Every imported source/header carried its own Apache-2.0 header and was checked
individually. `controllers.h`, `env.cc`, `env.h`, `dx7note.cc`, `dx7note.h`,
`fm_core.cc`, `fm_op_kernel.cc`, `fm_op_kernel.h`, `synth.h`, and
`aligned_buf.h` carry prominent local modification notices. See
`PROVENANCE.json` for the exact
per-file paths and changes, and `LICENSE-APACHE-2.0.txt` for the licence text.

The Apache licence text is copied from Google's original Music Synthesizer for
Android at pinned commit `f67d41d313b7dc85f6fb99e79e515cc9d208cfff`.
