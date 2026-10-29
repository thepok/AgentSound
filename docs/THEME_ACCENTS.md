# Endless symphonic theme accents

Automatic theme-arrival sforzandi used to be copied unchanged into every
melodic and bass doubling. This could turn a local melodic accent into a
synchronous orchestral attack and release.

The symphonic builder now allocates these accents after orchestration, solo
substitutions and guest preparation. One melody part retains the full sfz;
a bass theme can lead when there is no melody at that arrival. Its melodic
doublings share up to eight additional velocity points, at most four each,
without forcing marcato. Supporting basses retain their original articulation.
At a marked peak, the first automatic arrival retains the collective accent;
later arrivals use the role allocation. Accents outside the automatic theme
arrival positions are unchanged. No note timing, pitch, instrument, tempo,
master gain or renderer change is involved. This is active by default and
independent of the phrase-pumping switch.

Validation on 2026-10-26: replayed the three delivered no-solo pieces (seeds
4244, 4246, 4251) against a53e6a4, verifying exact original engine inputs with
the allocation disabled. With it enabled, note/role/articulation structures,
tempo maps and master settings remain equal; full sfz counts change from
52/78/164 to 18/36/56. Repeated compilation is deterministic, also with the
default solo/colour settings at seeds 4242, 4244 and 4251.

The complete 184-second seed-4244 render passes the existing audio delivery
gate, reports no clicks, and produces a full-length MP3. The K-weighted
400 ms level rise from 44.0 to 44.8 seconds changes from 8.20 to 5.43 dB.
Removing all accents at this passage previously gave 3.86 dB; the production
change deliberately retains the melody's attack. This demonstrates reduced
stacking at the reported passage, not a guarantee against every audible dip
or an assessment of overall musical quality.

140 tests passed: new accent regressions (3), symphony (116), score (9),
solo (4), colour (4), pumping (4). Local render, comparison clips and replay
evidence: `D:/tmp/agentsound-history-listening/accent-fix/`;
reproduction script: `D:/tmp/agentsound-history-listening/validate_accent_fix.py`.
