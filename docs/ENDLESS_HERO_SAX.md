# Hero Sax in the symphonic Endless generator

The guest reuses the piece's own melody, played with `hornist`'s `hero70s` gestures
and the `hero/sax` patch. It does not generate an unrelated solo or duck the master.

CLI: `python -m agentsound endless orchestra --hero-sax off|occasional|frequent`.
The default is occasional. The draw selects roughly one quarter of slots, or two
fifths with frequent, before musical eligibility. Actual appearances can be fewer.
Selected slots never immediately follow each other. All candidates for a slot
share the same draw, including rerolls; their musical suitability can differ.

Python: pass `plan={'hero_sax': 'off'}` to compose, or set a mode and
`hero_sax_enabled: True/False` for controlled comparisons. `set_plan` draws guests
with its own deterministic RNG. The CLI saves the actual plan in tune.json;
`hero_sax_events` records the chosen blocks, source roles and melody.
Archived tune.json files from before this feature replay with the sax off, so an
existing source piece does not silently acquire another guest when loaded.

The handover happens after choir planning and before ordinary solo-player
substitution. Choir blocks remain protected. Eligible monophonic lines have six
or more notes, a median note length of at least 0.3 seconds, and fit A3-G#5 by one
whole-line octave shift. No individual-note octave folding. Rapid or overlapping
lines are declined. The first entry must precede 60% of the piece; an eligible
later climax and closing statement can follow, with intervening orchestral blocks.
At most three blocks feature the sax. Opening and final blocks stay orchestral;
ordinary solos remain available elsewhere.

In a featured block the source melody and its melody doublings are removed before
performance; harmonic support is written softer, while bass foundations remain.
Other guest events reserve separate spans. The sax has its own plate/hall, no
whole-orchestra ducking, post-compression accents and a small 3.3 kHz presence cut.
Its performed notes and melodic role are registered in the candidate scoring data.
Existing render gates still check flat lead dynamics, silent notes and clicks.

Validation results and remaining limitations are recorded after the test renders.
The historical Sol-versus-Opus comparison lives separately under
`D:/tmp/orchestra-review-sol61-medium`; it tests reviewer usefulness, not whether
this new musical feature is good.

## Validation (2026-10-27)

- Relevant orchestra/solo/colour/pumping/README suite: 153 tests passed; three
  additional archive-replay/best-of-N tests passed (8 Hero Sax tests total), and the
  existing general Endless module passed 64 tests.
- Four paired score probes introduced no new hard composition-score findings;
  three pairs kept their numerical score, one changed from 51.9 to 52.4.
  This is a regression check, not a musical-quality verdict.
- Sax off: full render JSON matched the pre-feature pipeline on seeds 27100,
  27101, 27107 and 81, preserving the earlier accent/answer fixes.
- Saved tune replay reproduced tracks, buses, master and tempo map exactly.
- End-to-end two-piece CLI set (seed 27101, frequent): first piece includes sax,
  next piece omits it. Both passed the standard quality gate. The first measures
  -17.0 LUFS, -1.20 dBTP, LRA 13.1 LU, zero mix clicks; its sax has 28 audible
  notes and 5.0 dB median phrase dynamics. Normal orchestral masking warnings
  remain; no claim of direct listening.
- The render gate caught missing samples above MIDI 80 during development;
  whole-line range fitting now respects the actual sax sample ceiling. A
  regression protects that limit. The final orchestral chord is also preserved.
- Test artifacts: D:/tmp/endless-hero-sax-final (final meter-aware render),
  D:/tmp/endless-hero-sax-cli-v2 (preceding gate/replay check), and the logs/
  paired-score/off-identity JSON files under D:/tmp/endless-hero-sax-*.
- Website/WASM deployment is not part of this local generator change.
- Final render diagnostics were visually inspected in D:/tmp/endless-hero-sax-visual
  (tracks.png). A repeated render of the saved JSON produced a byte-identical WAV.
