# MIX - Lux Perpetua

Mix engineer's hand-over. Everything is code in `song.py`: the module-level `MIX` (trims, rides, eq bells), plus a
`SEATING` dict for the pans and the choir's width. `MIX` has no pan key, so `build()` applies `SEATING` just
before the master.

## Roles by the score

The mixer's own lead inference is not usable for this piece (TODO.md, "pick the lead per section"):

- Inferred: `trombone_solo` is the only lead and the choir is "bed". That judged one section (the Tuba) and skipped
  the other eight.
- With the choir voices passed as leads (`--lead choir_s ...`): it measures ONE voice track against the SUMMED
  orchestra groups. It proposes cutting every string, wind and brass section by 5-7 dB, which would make the piece
  a cappella.
- `mix --auto` was therefore not used. Its findings were read and the moves were judged per section by hand.

The leads per section, from the score:

| section | lead | what must be in front of what |
|---|---|---|
| intro | basset horns / bassoons (the sighs) | the sighs over the string pulse and the lament bass |
| requiem, kyrie, dies, tremor, ira | the choir (S A T B) | the voices over their colla-parte strings, winds and trombones; the fugue's entries equal |
| tuba | trombone_solo, then choir_oh (the answer) | the solo over the soft strings / organ |
| lacrimosa, amen | choir_oh, then S A T B for the climb | the lament over the violin sighs |

**How it was measured.** `.scratch/levels.py` (git-ignored, from `build --stems`) gives the per-section gated,
K-weighted loudness of every dry stem and of groups:

- CHOIR = the five choir tracks.
- Upper orchestra = violins, violas, basset horns, trombones, trumpets, organ: the parts in the choir's register.
- Low = cellos, basses, bassoons.

## Seating (audience view, pan -1 = left)

- **Antiphonal violins, as in Mozart's orchestra:**
  - violins I -0.5 (left);
  - violins II -0.22 -> +0.5 (right).
- **Strings, centre-right to right, as the preset had them:**
  - violas +0.2 and cellos +0.42 (centre-right);
  - basses +0.6 (right).
- **Winds, centre, behind the strings (preset):**
  - basset horns -0.08;
  - bassoons +0.16.
- **Brass and timpani, back:**
  - trumpets +0.14 -> -0.25 and timpani -0.05 -> -0.2, together at the back left;
  - trombones +0.34 -> +0.28, back right beside the lower voices they double.
- **Organ:** centre back (-0.05).
- **Choir:** behind the orchestra (hall send -3).
  - Before, the SSO chorus samples were ~95 % wide, and the recording leans: the soprano samples lean right, the
    tenors and basses left. Every voice spread over the whole stage, and the tenor measured +2.3 dB LEFT.
  - Now each voice is narrowed to 80 % (`fx.width` 0.8), and the lean is corrected by the (balance) pan: S -0.7,
    A -0.33, T +0.6, B +0.65.
  - Measured L/R: S +4.2, A +0.5, T -2.3, B -3.4 dB (+ = left). That is S A T B from left to right. Before it was
    -1.0 / -0.5 / +2.3 / +0.9.
  - The pan law of the balance pan costs S -1.8, A -0.5, T -2.1, B -1.3 dB. It is compensated in the trims.

## The moves (`MIX`)

**Trims (song-wide, dB):**

| track | trim | why |
|---|---|---|
| choir_s | +6.3 | choir from bed to lead; pan-law compensation included |
| choir_a | +5.0 | same |
| choir_t | +6.1 | same |
| choir_b | +5.8 | same |
| choir_oh | +1.0 | holds its level after its 600 Hz dip |
| violins I, violins II, violas | -1.5 | the colla-parte doubling sits under the voices |
| cellos | +1.5 | the bass line (fundament) |
| basses | +2.0 | same |
| trombones | -2.0 | colla-parte support, not a second choir: they sat level with the voices they double |
| basset horns | -1.0 | they sat above the alto / tenor they double in the Dies irae (-24.8 vs -27.7 LUFS) |

The choir trims are larger than the ~4 dB the brief distrusts:

- The role was wrong: the choir sat 2.6-4.9 dB under the orchestra in every sung section.
- About 1.5 dB of each trim only compensates the pan law.
- About 1 dB compensates the choir's own boxiness dip.

**Rides (dB per section, on top of the trims; ramp = 1 beat before the section):**

| track | rides |
|---|---|
| choir S / A / T / B | requiem +2.5, kyrie +2.0, dies +1.5, tremor +1.0, ira +1.5 |
| violins I, violas | intro +1.5, requiem +1.5 (back to the preset level where the pulse plays), kyrie -1.0 |
| violins II | intro +3.5, requiem +3.5 (the offbeat pair was 5 dB under violins I), kyrie -1.0 |
| basset horns | intro +2.5 (the sighs) |
| bassoons | intro +1.5 (the sighs) |

The ramps fall on held chords, where they are musical:

- the requiem's fermata;
- the kyrie's fermata, which swells into the attacca Dies irae;
- the intro's A7 crescendo.

**Eq bells (`mixer_eq`):**

| track | bells | why |
|---|---|---|
| choir S / A / T / B | -3 dB 600 Hz Q 0.6, +1.5 dB 3.2 kHz Q 1 | carve the box before pushing; a little diction / presence so the lead reads in front without adding low mids |
| choir T / B | also -1.5 dB 300 Hz | the biggest low-mid contributors (the mixer's mud finding: choir_t 16 %) |
| choir_oh | -2 dB 600 Hz Q 0.7 | its box |
| violins I / II | +1.5 dB 7 kHz Q 0.7 | let the violins speak (the top is dark) |
| violas | -1.5 dB 400 Hz | mud |
| cellos | -1.5 dB 400 Hz, +1 dB 120 Hz | mud; body |
| basses | +1.5 dB 90 Hz | body |
| bassoons | -1.5 dB 350 Hz | mud: 8.5 % of the song's low mids |
| trombones | -1.5 dB 1 kHz | honk |
| organ | -2 dB 300 Hz | the continuo sits under |
| hall (return) | -2.5 dB 650 Hz Q 0.6, +2 dB 8 kHz Q 0.5 | the hall collected 11-16 % of the low mids / mids; a brighter, less boxy room |

No ducks: a concert mix has no sidechain pumping.

## Before / after

Dry stems, gated K-weighted LUFS per section. The lead is the choir, except the intro (basset horns) and the tuba
(trombone_solo).

| section | lead vs upper orchestra | lead vs whole orchestra | low vs lead | section LUFS (mix) |
|---|---|---|---|---|
| intro | -2.1 -> -1.5 | -3.5 -> -3.0 | +1.0 -> +0.9 | -31.1 -> -29.3 |
| requiem | -3.5 -> +1.2 | -2.6 -> +1.2 | -1.5 -> -3.9 | -24.7 -> -22.5 |
| kyrie | -4.5 -> +0.5 | -4.9 -> -1.1 | -0.5 -> -2.3 | -19.4 -> -18.2 |
| dies | -3.2 -> +0.9 | -4.3 -> -0.9 | -3.5 -> -5.0 | -15.7 -> -14.8 |
| tremor | -0.3 -> +3.5 | -1.1 -> +2.2 | -6.5 -> -8.2 | -16.8 -> -15.7 |
| ira | -2.7 -> +1.5 | -3.8 -> -0.4 | -3.6 -> -5.1 | -15.1 -> -14.1 |
| tuba | +6.0 -> +7.6 | +4.2 -> +4.6 | -7.6 -> -6.5 | -26.5 -> -25.9 |
| lacrimosa | -1.7 -> +0.7 | +0.3 -> +2.2 | -8.4 -> -7.5 | -23.8 -> -23.1 |
| amen | +2.5 -> +3.6 | +1.0 -> +0.9 | -5.7 -> -3.9 | -23.4 -> -23.1 |

**Reading the table:**

- The choir now leads its sections: 0.5-3.5 dB over the instruments in its register.
- In the tuttis it is level with the whole orchestra, 0.4-1.1 dB under it. That is a storm, not a buried lead:
  the whole orchestra includes the bass line, timpani and brass hits.
- The bass line is 2-8 dB under, inside the classical low window of -9..-1.

**Whole song:**

| measure | before | after | note |
|---|---|---|---|
| LUFS-I | -20.7 | -19.6 | with the new master |
| LRA (LU) | 16.3 | 16.0 | |
| PLR (dB) | 17.1 | 17.1 | |
| true peak (dBTP) | -3.6 | -2.5 | |
| width >150 Hz | 44 % | 41 % | |
| low-end correlation | 0.96 | 0.97 | |
| reverb vs mix (LU) | -9.4 | -10.4 | |
| L/R (dB) | -0.6 | -0.8 | |
| space verdict | lush | lush | |
| flat dynamics | 0 | 0 | note dynamics unchanged (violins I 8.1, basses 8.9, solo trombone 16.6 dB) |
| clicks in the mix | 0 | 0 | |
| masked single-track clicks | 11 | 11 | the same loop seams in the Kyrie's fermata chord (TODO.md) |
| warnings | 0 | 0 | 3 info: the same two deliberate level jumps and the masked seams |

**The master's input.** An intermediate pass through the old master chain read -20.5 LUFS (was -20.7). The final
mix without a master eq reads -18.8 LUFS, with the limiter at its old +1.2 dB. So the MIX raises the master's input
by roughly 0.2-0.5 LU. The mastering engineer re-set the drive.

**Pre-master tone.** Without the master eq, the tone vs the classical reference reads lowmid +4.6 / mid +4.8. That
is under the +5 limit. The first choir push had read +6.5 / +6.6: two `tone_band` warnings, "fix it in the mix". It
is inside the limit after:

- the dips above;
- the stronger bass line. The band balance is judged against the median band, which is the bass band here.

## Open issues

- **The mixer tooling.**
  - It needs a group lead: a choir split into voice tracks, measured as one.
  - It needs a per-section lead (TODO.md).
- **The SSO chorus samples lean by voice range.** Seating S A T B needs a balance pan against the lean, and that
  costs ~1.5 dB of pan law (TODO.md).
- **The top stays dark before the master** (6-20 kHz -8.4 dB, an info). The master's high shelf takes it to -5.7 /
  -10.3 (brilliance / air), and the info is gone.
- **Nobody has listened.** Everything above is from the analysis and the stems.

## Revision (A&R round 1)

The A&R found (by numbers) choir and organ pads over low strings: the figures that make it Mozart were written but
not heard, and the organ doubled the whole choir. The arranger rewrote the figures a dynamic level up and the organ
as a continuo; the mix then moved:

**Trims:** violins I / II 0 (the -1.5 dB colla-parte trim is gone: they carry figures); organ -6 dB; the rest as
before.

**Rides (dB, on top of the trims):**

| track | rides | why |
|---|---|---|
| choir S A T B | requiem +3, kyrie +3, dies +4, tremor +2.5, ira +3.5 (S also lacrimosa +3.5) | the choir stays the lead with the figures up; S carries the lament in the Lacrimosa |
| choir_oh | tuba +1, lacrimosa +0.5, amen +2.5 | the swells lower its average; the Amen is its movement |
| violins I | intro +3.5, requiem +5, kyrie -1, dies 0, ira +0.5, lacrimosa +2.5 | the pulse and the sighs on top in their octave |
| violins II | intro +5.5, requiem +5.5, kyrie -1, dies -1, lacrimosa +2.5 | the offbeat pair and the lower sighs |
| cellos / basses | intro -3 / -2, kyrie -2 / -2 | the intro's mud; the fugue's entries over the bass line |
| trumpets | dies +2, ira +1 | the dotted figures |
| basset horns | intro +2.5, dies -2 | the intro's sighs lead; in the storm they doubled the alto / tenor too loudly |

**Eq:** choir S +1.5 dB at 3.2 kHz (the lead's diction), A +1 dB at 3.2 kHz and -2.5 dB at 1.5 kHz, T / B -0.5 dB at
3.2 kHz (was +1.5: they carried 30 % of the presence band); violins I -1.5 dB at 3.5 kHz, -1 dB at 1.2 kHz and +1.5 dB
at 10 kHz (was +1.5 dB at 7 kHz: 30 % of the presence band), violins II +1.5 dB at 10 kHz; trumpets -2.5 dB at
1.5 kHz; the hall return also -1.5 dB at 1.6 kHz. The pre-master tone: mid +5.7 -> +4.9, presence +3.2 -> +1.7
(limits +5 / +3, 0 warnings).

**Figures, band-limited against the sum of all other stems (dB; 500-1000 / 1000-2000 / 2000-4000 Hz):**

| passage | part | before (A&R) | after |
|---|---|---|---|
| intro pulse | violins I | -15.7 / -7.7 / -9.3 | -8.6 / -0.6 / -3.8 |
| requiem pulse | violins I | -20.9 / -19.2 / -12.9 | -9.8 / -9.7 / -5.9 |
| Lacrimosa bars 1-2 | violins I sighs | -8.7 / -7.9 / +1.4 | +1.4 / -0.3 / +5.1 |
| Lacrimosa with the choir | violins I sighs | -15.6 / -19.8 / -4.6 | -6.8 / -10.7 / +2.4 |
| Dies irae | violins I 16ths | -13.4 / -10.8 / -6.7 | -9.5 / -7.2 / -4.2 |
| Dies irae (2nd phrase) | trumpets | -18.1 / -13.5 / -13.7 | -10.5 / -6.8 / -5.9 |
| ira | trumpets | - | -8.5 / -3.9 / -4.0; -12.7 dB under the mix (was -21) |

Where the choir sings, the figures stop at about -7..-10 dB in the 500-2000 Hz band: the choir is the lead and sings
in the same octave. Pushing them to the A&R's -6 would put the violins over the voices.

**The choir vs the whole orchestra** (gated K-weighted LUFS of the dry stems; before -> after): requiem +1.2 -> -0.7,
kyrie -1.1 -> -1.4, dies -0.9 -> -1.7, tremor +2.2 -> +0.5, ira -0.4 -> -1.9, lacrimosa +2.2 -> +0.7, amen +0.9 ->
+0.7. The choir's sum is still 3-5 dB over the loudest orchestral section in every sung section (dies: choir -20.2,
violins I -24.8; ira: -18.5 vs violins I -22.9 / trumpets -23.3); the orchestra's sum grew by the figures it now plays.

**The organ:** -42..-48 dBFS RMS per section, 9-11 dB under the soprano (Kyrie S entry: organ -45.1 vs S -34.1; it
was -33.6 vs -35.3), the quietest track in the Lacrimosa (-46.3; it was the loudest at -35.5).

**The fugue's entries** (dry RMS over the entry's first two beats, the entering voice vs the loudest other voice /
organ / cellos): T +2.2, A +4.4, S +1.5, T (F major) +8.5, B +3.3, A +3.6 dB. Every entry is on top (before: none).

`python -m agentsound mix songs/lux-perpetua`: no moves; 1 info, mud 200-400 Hz +2.9 dB (was +3.3).
