# Kestrel Bay - brief

**The wish** (user, 2026-10-01): "Create masterful electric guitar solos, and the techniques needed for them, like we
did for the saxophone." -> one original instrumental built AROUND masterful guitar solos, in the spirit of the classic
guitar-instrumental anthems (Gary Moore "Parisienne Walkways", Gilmour, Satriani) - original, no copied melodies. The
solo must sound PLAYED, not programmed: every technique audible and used musically.

- **Genre**: melodic rock ballad / guitar-instrumental anthem. Analysis profile `rock`.
- **Frame**: 84 BPM, A minor, 4/4, straight 8ths (a half-time power-ballad feel in the big parts), 72 bars + ring-out
  = ~3:30.
- **The hook**: an 8-bar singing theme on the hero lead guitar (`layered/hero_guitar_heavy` through `hero(...,
  family='guitar_heavy')`: Strat DI zones -> Plexi lead channel -> Greenback 4x12 + the amped SampleRadar lead
  double: body below 1 kHz, sustain, velocity -> gain / tone). Its head (E4 A4 C5 - B4 A4, a held A) is the motif the
  solos develop. Not beepy: a driven guitar in the G3-D6 singing range, bends and vibrato on every long note.
- **Form**: `intro 4 | verse 8 (theme) | chorus 8 (theme, higher, resolving) | bridge 8 (rising sequence -> the held
  feedback note) | solo 16 (soloist arc 'build') | break 4 (drop) | chorus2 8 (the theme an octave up: climax) |
  outro 12 (soloist arc 'classic': burst, climax, resolution) | end 4 (the last note blooms into feedback)`.
  Energy: 2 - 3 - 4 - 3.5 rising - 4.5 - 2 - 5 - 5 -> 3 - 1.
- **Band**: `bands.power_ballad(s, without=('lead',))` (Salamander grand, VPO strings, Juno pad, Big Rusty kit in the
  big room, Growlybass) + double-tracked crunch rhythm guitars (Emily SG crunch L, FSBS Marshall R) in the big parts
  + a clean Strat arpeggio in the quiet parts.
- **Players**: drummer (rock / ballad, fills budgeted), bassist (rock), guitarist.arrange (rhythm + clean), the lead's
  themes through `guitarist.lead(gestures=True)` + hand-placed `fretwork` set pieces, the two solos through
  `soloist.solo(..., guitarist.vocabulary('rock'))`.
- **Reference**: Gerry Rafferty - Baker Street (official video), the guitar solo 3:29-4:03 (the rock recipe's tuning
  reference for the hero guitar): `compare --ref ... --ref-start 3:29 --ref-end 4:03 --section solo`.
- **Targets**: rock profile (-10..-7 LUFS-I, TP <= -1 dBTP), bed 3-5 dB under the lead in its sections, lead
  note dynamics >= 4 dB, 0 clicks, 0 silent notes.

## Checklist (HUMAN_FEEDBACK rules that apply)

- [x] A song, not a loop: a theme that returns and grows (verse -> chorus higher -> chorus2 an octave up), fills,
      transitions, a real ending.
- [x] Hero sound on the hooks and solos: present, "epic", not just loud.
- [x] Lead in front: bed >= 3 dB under the lead in its sections.
- [x] Real dynamics: `flat_dynamics` = 0; phrase arcs; the solo's dynamics follow its arc.
- [x] Tricks are spice ("zu viele von diesen schnellen Zwei-Tasten-Wechseln"): fast figures budgeted (one per 8+
      bars, only in the burst / climax), bends and vibrato are the vocabulary, not tricks.
- [x] Played, not keyboard-like: picked vs slurred notes, bends that overshoot and settle, vibrato that goes up from
      the note, rolled / strummed chords in the band.
- [x] Produced: rooms, the hero's own echo throws, width from the double-tracked guitars, a full low end.
- [x] `clicks` = 0, TP <= -1 dBTP.

## Log

- producer: brief written (system work first: fretwork, soloist, guitar vocabulary, engine harmonic / bendfollow /
  wah - branch feat/guitar-solo).
- arranger: form as briefed, solos split (solo / solo2, outro / outro2) so the statements are not buried; the
  theme performed by guitarist.lead(gestures=True), set pieces by fretwork, solos by soloist + guitarist.vocabulary
  (seeds 31 / 22, the scream saved for the outro). ARRANGEMENT.md.
- sound designer: hero(guitar_heavy, rock), crunch / Marshall wall L / R, clean Strat high-passed, power_ballad bed.
  SOUND.md (Baker Street comparison of solo2).
- mix engineer: three mix passes + the section arc into the master (LRA 1.9 -> 5.4 LU). MIX.md.
- mastering engineer: --check all ok (-9.9 LUFS-I, -1.20 dBTP), fade after the limiter. MASTER.md.
- A&R: round 1 revise (no arc, lead too far in front, buried statement), round 2 ship (4 minors). AR.md.
