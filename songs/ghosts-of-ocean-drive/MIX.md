# Ghosts of Ocean Drive - mix

Mix engineer pass on the delivered build (commit 416c3d4), `python -m agentsound mix` + manual builds (a full build
takes ~3 min; `--auto` was not needed: its plan had one move, drums +0.8 dB). Profile `synthwave`, hooks chorus1-3,
lead = the hero synth-piano hook (`lead`), the sax leads the solo.

## The moves (added to the song's existing MIX)

| move | value | why |
|---|---|---|
| ride drums | chorus1 +0.6, chorus2 +0.8, chorus3 +1.0, solo -0.5 dB | `drums_too_quiet`: rhythm -5.8 dB under the hook in chorus2 (target -5..-2). A song-wide +0.8 trim was tried first: it made the kick / bass masking warn-level again (verse1, solo, chorus3), so the lift only goes into the hooks. The solo steps back so the sax stays in front (and the drums' share of the solo's bass band stays under the masking threshold) |
| eq drums | + bell 10 kHz -2 dB Q 0.8 (next to the existing -1.5 dB at 3.3 kHz) | the hats' tick / air: Sunset chorus 2 had +2.0 dB air and hat punch 18 vs 11 dB |
| duck | bass under the kick (`pitches='kick'`), depth 4 dB, attack 1, hold 30, release 110 ms | a short second duck on the kick hits only, on top of the song's slower 9 dB ducker: the low-end separation in chorus3 was 2.0 dB (warn-level masking in the sub band) -> 3.6 dB (info, "they alternate"); verse1 3.7 -> 5.0 dB |
| eq lead | bell 800 Hz -1.5 dB Q 2 | the hook's honk: a narrow +5.3 dB (chorus2) / +4.0 dB (chorus3) 1/3-octave peak at 800 Hz vs Sunset -> +4.4 / +3.2 dB |
| trim lead | +1.0 dB | the honk dip took 0.9 dB of the hook's K-weighted level (bed vs lead chorus3 fell to -3.6 dB): the fader gives it back, now with less honk and more of the attack in front. Lead pre-master peak -1.6 dBFS (< -0.5) |

Tried and dropped: drums trim +0.8 song-wide (kick / bass masking came back as warnings); chorus3 drum ride +0.3 / +0.6
without the kick duck (sub-band masking stayed warn-level). Not done: a 3 kHz dip on the drums (`harsh` info vs the
genre profile) - Sunset reads our presence 3-4 dB short, so the references disagree; the dip that is there stays.

## Before / after (dB vs the section's lead; `bed` = report.space bedVsLeadDb)

| section | rhythm | low | bed | section LUFS (after the master) |
|---|---|---|---|---|
| verse1 | -4.0 -> -4.4 | -1.3 -> -1.4 | -5.9 -> -5.8 | -14.5 -> -13.1 |
| pre1 | -3.6 -> -3.9 | -1.0 -> -1.0 | -5.1 -> -5.1 | -12.6 -> -11.5 |
| chorus1 | -5.3 -> -4.8 | -2.0 -> -2.2 | -5.5 -> -5.6 | -10.5 -> -10.0 |
| interlude | -3.6 -> -3.6 | -0.8 -> -0.5 | -4.0 -> -4.2 | -11.5 -> -10.6 |
| verse2 | -3.8 -> -4.0 | -1.2 -> -1.1 | -5.2 -> -5.4 | -12.6 -> -11.5 |
| pre2 | -4.5 -> -4.9 | -1.6 -> -1.6 | -5.3 -> -5.2 | -12.1 -> -11.0 |
| chorus2 | -5.8 -> -5.2 | -2.8 -> -2.9 | -4.7 -> -4.9 | -10.2 -> -9.7 |
| breakdown | -4.2 -> -4.8 | -1.2 -> -1.4 | -4.5 -> -4.7 | -15.0 -> -13.6 |
| solo (sax) | -3.5 -> -4.1 | -1.3 -> -1.2 | -3.9 -> -3.9 | -10.3 -> -9.6 |
| chorus3 | -5.7 -> -5.7 | -3.2 -> -3.6 | -4.3 -> -4.6 | -9.7 -> -9.4 |

The hook stays in front: the bed 3.9-5.8 dB under it in every lead section (>= 2.5), the drums and bass inside the
synthwave windows. Mixer findings: before 1 (drums_too_quiet, info) -> after 1 (info: drums / pad share the presence
band in the pad-only intro, they alternate). Report: 0 warnings (the two kick / bass masking lines are info: "they
alternate"), 0 clicks in the mix (the one masked click in the bass stem alone is unchanged, info). Note dynamics: lead
7.5 -> 7.1 dB, sax 3.9, keys 3.8, brass 5.2 dB - no `flat_dynamics`.

Against Sunset 4:00-4:30 (loudness-matched, after the master): chorus2 punch low (kick) 13.0 -> 12.7 dB (ref 18.9),
punch high (hats) 18.0 -> 17.2 (ref 11.1), 800 Hz +5.3 -> +4.4, air +2.0 -> +1.2, mid +1.6 -> +1.0; chorus3 kick
14.4 -> 13.6, hats 16.2 -> 15.3, presence -3.4 -> -3.1 dB.

## Into the master

The mix moves barely move the master's input: the drum rides, the hat dip and the kick duck took the song from -11.6
to -11.7 LUFS-I with the old master; the lead's honk dip + trim (built after the master change) moved the final
-11.0 -> -10.9. The mastering engineer's drive change is in MASTER.md.

## Open issues

- Kick punch stays 5-6 dB under Sunset and the hats 4-6 dB "punchier": gain, EQ and the extra duck move these numbers
  by < 1 dB. The cause is the sound and the master limiter (the kit's own compressor, the preset's 3.5-4.5 dB of
  limiter drive in the choruses) - a sound-designer / arrangement question (a harder kick sample or a drum bus
  with a slow attack, busier sustained top end around the hats), not a fader one.
- The kick / bass masking check is on a knife edge: small drum or bass level changes flip it between info and warn
  (the drums' share of the bass band sits at 35-41 %). Keep the kick duck when editing the bass.
- 89-354 Hz stays ~+2.8 dB vs Sunset, but the synthwave profile reads the bass band at 0.0 and the sub -2.5 dB: the
  references disagree, nothing was cut.

## Revision (A&R issues 1, 2, 4)

The MIX on top of the new sounds and arrangement:

| move | value | why |
|---|---|---|
| ride drums | chorus1 +1.2, chorus2 +1.5, chorus3 +1.8, breakdown -2.0, solo -1.5 | Before the revision, rhythm sat -5.2 / -5.7 under the hook in chorus 2 / 3, outside the window. It is now -4.0 / -4.4 / -4.4. In the breakdown the drums masked the hook's new presence. |
| ride sax | solo +4.0 (was +1.5) | The sax now sits over a thinned band. |
| ride bass | solo -2.5 | Bass vs sax is now -6.6 dB (was -1.6). |
| ride pad | verse1 -1.0, pre2 -1.2, solo +1.5 | `thin_bed` in pre2 (6.1 dB) and verse1. In the solo the bed is 6.0 dB under the sax: inside the hero-sax 6-8 dB rule, and the mixer no longer flags it. |
| duck | bass under the kick: depth 10, hold 50 (was 4 / 30) | Low-end ducking was 2.5 dB with masking warnings; it is now 4.8 dB, info only. |
| eq drums | 3.3 kHz -4 dB, Q 0.9 (was -1.5); 10 kHz -4 dB (was -2) | The hook now owns 2.5-6 kHz (the drums / lead presence masking warning). Air was +2.6 dB over Sunset. |
| eq keys | + 3 kHz -2 dB | Presence room for the hook. |
| eq arp | 3.5 kHz -2 dB | Presence room for the hook. |

After:
- Report: 0 warnings.
- `mix`: 1 info, deliberate. `harsh` says 2-5 kHz is +3.2 dB over the profile, with the lead at 28 %. The A&R asked
  for the hook's top, and Sunset still reads 2 dB more there.
- Bed under the hook: chorus 1 -5.3, chorus 2 -4.8, chorus 3 -4.5 dB.
- Kick punch in chorus 3: 18.7 dB (Sunset 18.9).
- Still open: the top-band punch is 15.0 vs 11.1 dB. It comes from the snare / clap crack.
