# Foreground answers in Endless orchestral dialogues

The orchestration function table deliberately puts melody at +4 velocity
steps and counterpoint at -4. In a call-and-response passage, however, the
counter-line is the foreground melody during the call's rests. Applying the
counterpoint reduction there caused an unintended eight-step level penalty,
including after replacement by a solo player.

The symphonic builder now removes this functional penalty for counter notes
whose entire written span lies in a gap in all melody parts of that block.
Any overlap retains the counterpoint balance; parts without a melody in their
block are unaffected. Instrument-specific offsets and explicit dynamics remain.
Doublings retain their support level. Detection uses written note spans before
performance timing, so humanized legato does not randomly change the decision.

## Investigation, 2026-10-26

Two delivered pieces, with soloists and the theme-accent correction enabled:

* Seed 4261, The Hidden Forests: the 104-107 s fluctuations primarily come from
  the a cappella choir and its written rests. At 120-123 s, violin and timpani
  build toward the next section. The deceptive retransition explicitly writes
  forte, subito piano, then a crescendo. These are retained.
* Seed 4267, Bright Tides: at 24-27 s the orchestral attack includes timpani,
  clarinet and solo oboe; it is not evidence of a solo-only fault. At 242-246 s,
  the violins alternate with solo-oboe answers. The latter received the
  counterpoint penalty even when no melody sounded against them. This is fixed.

Full matched renders preserve orchestration parts (notes, roles, articulations,
offsets, sf marks), tempo maps and master settings. Both pass the existing audio
delivery gate. On 400 ms K-weighted windows, the smaller of the two flank drops
at the original 242.2/245.3 s peaks changes from 6.63/6.92 dB to 5.33/5.73 dB.
The 95th percentile of absolute one-second changes changes from 6.04 to 5.88 dB
in Bright Tides and from 5.18 to 5.09 dB in The Hidden Forests. Remaining swings
are not claimed fixed or all unintended. No compression or post-render level
normalization was added.

Reproduction/evidence: `D:/tmp/orchester-solisten-akzentfix-20261026/`
(`diagnose.py`, `stem_levels.py`, `validate_answers.py`, `answer-validation.json`,
per-song `diagnostic/` stems and `corrected/` full WAV/MP3 files).
