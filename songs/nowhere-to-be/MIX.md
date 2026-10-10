# Nowhere to Be - mix (roles/mix-engineer.md)

Profile `jazz` (the mixer's windows around the lead: rhythm -16..-13 dB, low group -6.5..-3 dB). The lead is the voice
in the sung sections, the tenor in intro / inter / solo.

## Moves (module-level `MIX` in song.py)

| move | why |
|---|---|
| trim bass -2.5, piano -2.5, pad -2.5 | the low group sat -2..-4 dB under the voice in the sung sections (window -6.5..-3); the voice clearly in front, a smooth record |
| trim sax +2.0, ride sax intro -1.5 / inter +3.0 | the tenor was not in front where it leads (the band +2..+4.7 dB over its window in the inter / solo) |
| trim drums -1, rim -1; ride drums / rim -1.5 in the solo; ride bass -3 / piano -2 in the intro | second pass: the kit -11.6 under the tenor in its solo (window -16..-13), the bass only 1.5 dB under the low tenor's hook in the intro |
| eq piano -4.5 dB at 150 Hz (q 0.7), -1.5 dB at 450 Hz | the Rhodes and the upright shared the 60-250 Hz band; the Rhodes and the tenor the 450 Hz |
| eq vocal -1.5 dB at 380 Hz | low mids +4.7 dB over the profile, 66 % of it her low register |
| (song) sax.feature(solo, +2 dB), the comping sparser / softer under the solo | the solo's lead without making it the loudest moment (it peaked at -10.4 LUFS short-term with +3.5 dB) |
| (song) the arc on the master input: intro -3, verses -2.5 / -2, choruses -0.5 / 0 / +1.2, bridge +0.5, tag -1.5, end -2.5 | LRA 3.6 -> 5.1 LU (the profile wants >= 5): the verses breathe, the last chorus is the warmest |

## Before / after (section balance vs the lead, `python -m agentsound mix`)

| section | lead | rhythm before -> after | low before -> after |
|---|---|---|---|
| verse1 | vocal | -14.9 -> -14.9 | -3.7 -> -7.4 |
| chorus1 | vocal | -14.7 -> -14.8 | -2.2 -> -5.9 |
| inter | sax | -8.3 -> -13.3 | +5.4 -> -4.0 |
| verse2 | vocal | -14.4 -> -14.4 | -2.0 -> -6.0 |
| chorus2 | vocal | -14.0 -> -14.1 | -2.1 -> -5.7 |
| solo | sax | -11.0 -> -13.2 | +0.9 -> -4.9 |
| bridge | vocal | -13.4 -> -13.5 | -0.9 -> -4.6 |
| chorus3 | vocal | -13.8 -> -14.1 | -1.8 -> -5.6 |

After: "moves: none - the balance is inside the targets". Wetness of the voice (`wetness.py` numbers): returns 20.5 LU
under the dry voice, 30 dB down 0.1 s after a phrase end. Note dynamics: voice 16.2 dB, Rhodes 4.2, bass 6.6, pad 4.1,
tenor 5.4 per phrase; `flat_dynamics` warnings 0.

## Open

- `masking` (warn): the Rhodes and the upright still both carry the 60-250 Hz band in the sparse sections (intro,
  verses, inter, tag) - the Rhodes' left hand lives at D3-G3 (147-196 Hz); cut -4.5 dB at 150 Hz and the comping moved up
  from C3 to D3. Natural for a two-feel ballad; left as minor.
- `narrow`: fixed on the master (x1.6, 23 % above 150 Hz); the sung sections alone read 9-15 % (a dry centred voice).
