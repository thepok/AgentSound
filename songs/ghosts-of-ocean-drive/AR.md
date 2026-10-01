# Ghosts of Ocean Drive - A&R

Judged build: `song/synth-new-mix` @ 29e7077 (mix + master pass on top of 416c3d4), rebuilt from scratch in the A&R
worktree (bit-identical mix.mp3, 11 974 988 bytes). Evidence: `report.json` + images, `python -m agentsound mix`
(findings only), `master --check`, `compare --section chorus3` vs The Midnight "Sunset" 4:00-4:30, and a stem render
of bars 69-100 (chorus2 / breakdown / solo, `build --from-beat 272 --to-beat 400 --stems`) for the lead and sax numbers.

```
verdict: revise
summary: A real song with a hook you can hum: the little F#-G-B cell comes back all through the track and lifts
         nicely into C# minor. But from the first chorus on it sits at one level. The drums have no kick, the high
         piano hook sounds muffled, and the sax solo is buried in the band.
```

## Issues (most severe first)

1. **[major] The energy arc flattens after 1:14 and the climax never arrives.**
   Evidence: section loudness (loudness.png) chorus1 -10.0, interlude -10.6, verse2 -11.5, pre2 -11.0, chorus2 -9.7,
   solo -9.6, chorus3 -9.4 LUFS. Chorus 1 to chorus 3 is only +0.6 LU, and chorus 3 is only +0.2 LU over the solo (the
   brief planned solo 4 < chorus3 5). Verse 2 to chorus 2 is 1.8 LU (recipe and brief: 2-4 LU). Chorus 3 has a
   loudness range of 0.7 LU (Sunset 1.7), and its waveform is a brick (spectrogram_11_chorus3.png). The master drives
   the limiter up to 6.5 dB in chorus 3 (the 4.5 dB automation plus `MASTER_DRIVE` 2.0). The master pass cut the
   verse1-to-chorus3 arc from 4.8 to 3.7 dB. On top of that, the hook voice plays without a break from 0:18 to 3:32
   (tracks.png, `lead` row): verse tune, pre, chorus and interlude are all on the same hero piano. The chorus is
   never a new voice arriving; it is the same piano getting a little busier.
   Owner: **arranger** (first), **mastering-engineer**.
   Fix:
   - Arranger: thin verse 2 and pre 2 (arp out in verse 2, e-piano sparser, pad only), and give the hook voice a
     1-2 bar rest before each chorus (the choruses start from a hole).
   - Arranger: make the solo a step below chorus 3. Half-time or lighter drums, no 16th arp. Leave it to the sax,
     pad and bass.
   - Mastering: take `MASTER_DRIVE` back to about +1 dB, or keep +2 only in the three choruses and none in the
     solo / verse 2. -11.3 LUFS is inside the window. Then check chorus3 minus solo >= 1.5 LU, chorus minus verse
     >= 2.5 LU, and chorus3 minus chorus1 >= 1 LU.

2. **[major] The drums don't hit like an 80s record: a soft kick under ticky hats and a woolly low end.**
   Evidence (compare chorus3 vs Sunset, compare.png):
   - kick punch 13.6 vs 18.9 dB (-5.3); the hats stick out 15.3 vs 11.1 dB (+4.2)
   - 89-354 Hz +2.8 dB, peak +4 dB around 110-125 Hz, with the bass holding 60 % of that band
   - the drums carry 42 % of the presence band: in the chorus the only top end is hats
   - mixer: rhythm is -5.2 dB under the hook in chorus 2 and -5.7 dB in chorus 3 (window -5..-2). Its plan still
     says drums +1.0, even though MIX.md says "inside the window in every hook".
   - kick/bass masking sits on a knife edge (MIX.md).

   Faders were tried and moved these numbers by less than 1 dB. The cause is the sounds and the limiter.
   Owner: **sound-designer**, then **mix-engineer**.
   Fix:
   - A harder kick: layer a punchier 909/Linn kick transient, or put a drum bus compressor on the kit with a 20-30 ms
     attack.
   - Darker hats: another hat sample, or a low-pass / velocity-to-tone curve on the hats. Not just lower velocities
     (those were tried).
   - A 150-180 Hz dip (-2..-3 dB) on the bass itself, so the kick owns 50-60 Hz and the bass stops booming. Re-check
     the masking lines after.
   - Mix-engineer: then drums +1 dB in the hooks. The limiter relief from issue 1 gives back part of the punch.

3. **[major] The hook has no top: the "high piano key" sounds muffled and boxy.**
   Evidence:
   - lead stem, chorus 2 (bars 69-84): 0.9 % of its energy in 2.5-6 kHz and 0 % above; lowmid 51.5 %, mid 47.5 %;
     centroid 837 Hz (report nodes). The breakdown is the same (0.5 % presence).
   - whole mix: the 1/3 octave at 800 Hz is +5.5 dB vs the synthwave profile, and the mids +2.5 (chorus 3 +4.8,
     bands.png), even after the mix engineer's -1.5 dB honk dip.
   - Sunset reads our presence -2.1 dB (peak -2.8 dB at about 2.5 kHz).

   The user asked for "lieber eine hohe Piano-Taste". The recipe's piano hook is "high-passed, presence + air". The
   master refused the presence lift on the strength of the perry-street "es klingt hart" rule, but that rule is about
   a Salamander jazz grand in a trio. It does not justify a synthwave hook with no energy above 2.5 kHz. The fix
   belongs on the hook, not on the master.
   Owner: **sound-designer**.
   Fix:
   - Remove the hero tone's -1.5 dB at 3.3 kHz on the lead.
   - Open the saw layer's cutoff, or add +2..+3 dB of shelf from 3 kHz on the lead.
   - Thin the octave-below / sixth doubles: play them about x0.7, or high-pass their energy at about 350 Hz, so the
     top note leads.
   - Then LOOK at a spectrogram zoom of the loudest hook hits (they must bloom, not bite) and re-check bed vs lead.
   - Once the hook carries the chorus presence, the hats can go down (issue 2).

4. **[major] The sax solo is not "epic / present": it sits under the band** (the lamplight-avenue rule).
   Evidence: stems, bars 93-100, crude K-weighting: the sax is -2.3 dB under the rest of the mix. The HUMAN_FEEDBACK
   hero-sax target is +0.8..+1.7 dB over the band. Mixer (solo): bed -3.9 dB under the sax (hero sax rule 6-8 dB),
   bass only -1.2 dB under it. Width above 150 Hz in the solo is 40 %, the bottom of the window. Behind the sax the
   full band keeps playing: four on the floor, 16th arp, e-piano, strings, pad, riser. Sax note dynamics in the solo
   are 3.1 dB (flat threshold 3.0; lamplight 3.8), and 0.0 dB of that comes from velocity. The sax is trimmed -3 dB
   and ridden up only +1.5. Pushing the sax as it stands would make the solo even louder than chorus 3 (issue 1), so
   the room has to come from the backing.
   Owner: **arranger** (backing), **mix-engineer** (level).
   Fix:
   - Arranger: arp out in the solo and e-piano out or on long chords; drums lighter (see issue 1).
   - Mix-engineer: then sax +2..+3 dB in the solo, bed keyed 6 dB under it (`song.carve(..., key=sax, depth=4)` is
     already there, deepen it), the bass -1.5 dB in the solo.
   - Target: sax >= +1 dB over the band, bed 6-8 dB under it.
   - Hornist: raise the air-push depth so the held peaks move >= 3.5 dB.

5. **[minor] Width is below the brief's own target.**
   Evidence: width above 150 Hz is 50-55 % in the full sections and 40 % in the solo. The brief and recipe want
   60-80 %; Sunset reads 59 % against our 51 %. Per octave, 250 Hz is about 25 % wide vs Sunset's about 95 %
   (compare.png): the recipe's "width lives in the low mids" is not there.
   Owner: **sound-designer** / **mix-engineer**.
   Fix: widen the pad and strings in the low mids (dimension / chorus, less pad narrowing), pan the e-piano and the
   pluck arp further apart, and give the solo a wide bed layer.

6. **[minor] The outro drops out of the key change without a pivot.**
   Evidence: chorus 3 ends on C#m (bar 116), and the outro opens on G major in B minor (bar 117, 4:28). That is a
   tritone jump in the root that deflates the lift instead of landing it.
   Owner: **arranger**.
   Fix: end chorus 3's last bar on A (VI in C#m, which is VII in Bm) as a pivot into the outro, or play the outro and
   the sax farewell in C# minor.

7. **[minor] Hygiene.**
   The `GOD_LEAD` A/B switch is still in `song.py`: an environment variable can silently change the delivered hook.
   Remove it once the sound is final. Publishing is blocked by the credits (80s pop drums are no-redistribution;
   LinnDrum, Fairlight and 224XL IR are unclear; the MTG sax and Salamander are CC-BY and need credit lines). That is
   fine for private listening.
   Owner: **producer**.

## HUMAN_FEEDBACK checklist

- [x] A song, not a loop. There is a form of 12 sections. The hook returns and grows: intro tease, interlude, the
      half-speed G-to-G# recolour in the breakdown, up a step in chorus 3, the sax farewell. The drummer plays fills
      (6 tom fills, 2 builds, a stop), and every chorus adds something. The shape of the arc is the problem, see
      issue 1.
- [x] No beepy lead. The hook is the hero synth-piano (Salamander attack plus the saw layer), 74-86 % voiced in
      octaves / sixths / thirds. It is dull rather than beepy (issue 3).
- [x] Lead in front. The bed is 4.6-5.8 dB under the hook in every lead section (report `bedVsLeadDb`; stems
      chorus 2: 5.7 dB).
- [x] Real dynamics. `flat_dynamics` is 0. Lead 7.1 dB (velocities 31-121), keys 3.8, brass 5.2, sax 3.9 dB.
- [x] Played, not keyboard-like. Pianist, drummer, bassist and hornist all play (7 pushes, 5 swells, 6 vibratos,
      1 shake). The final chord is rolled.
- [x] Piano is harmonized and decorated, and fast figures are budgeted (0 trills played, crush / restrike / roll
      only). It is warm, not hard. If anything it is too warm (issue 3).
- [-] Jazz rules: n/a.
- [ ] Hero sounds are present and "epic". The sax sits under the band in its own solo (issue 4). The hook reads in
      front by level but has no presence (issue 3).
- [x] Produced, not Gameboy. 224XL hall and plate at -10.7 LU, echo -17 LU, shimmer blooms, "lush" in every
      section. Width is a little short (issue 5).
- [x] `clicks` 0 in the mix (1 masked in the bass stem, info). True peak -1.12 dBTP, no clipping, `master --check`
      ok.
- [ ] The brief's own targets: chorus minus verse is 1.8 LU in verse 2 to chorus 2 (2-4 wanted), width above
      150 Hz is 50-55 % (60-80 wanted), and the planned energy order solo < chorus 3 is not audible (issues 1 and 5).

## Keep (must survive the revision)

- The hook cell (F# G B, B A G), its sequence and its whole journey: the intro tease, the interlude, the E-major
  recolour of the breakdown, the sax landing on G#7 into C# minor, the sax farewell with the piano's answer.
- The pianist's hook voicings (octaves / sixths / locked hands in chorus 3) and the restrained ornament budget.
- The bed balance under the hook (4.6-5.8 dB), the lush rooms and echo levels, and the one-beat breath before
  choruses 1 and 2.
- The hornist's breathing sax, the drummer's form (fills, builds, the breakdown stop, the ending hit), and the rolled
  Bm(add9) ending.
- 0 clicks, true peak -1.12 dBTP, the loudness window.

## Revision

Owners wore their hats in the A&R's order (arranger -> sound designer -> mix engineer -> mastering engineer ->
producer). Rebuilt on `song/synth-new` after `git merge master`. Before = the judged build rebuilt in this worktree,
after = the delivered build. Numbers come from the report, `compare --section chorus3` against Sunset 4:00-4:30, and a
stem render of bars 69-100 (K-weighted, `.scratch`, not versioned).

1. **Arc (arranger, mastering engineer).**
   - Verse 2 is thinner: the arp is out and the e-piano plays two chords a bar.
   - The arp enters in the second half of pre 2.
   - The hook voice rests before the choruses: pre 1 loses its last bar, pre 2 its last two.
   - The solo is lighter: half-time drums, no arp, e-piano on long chords, strings soft and then swelling.
   - The master drive now changes per section (`MASTER_DRIVE`): +0.5 in chorus 1, +1.0 in chorus 2, +1.3 in chorus 3,
     -1.3 in the solo and +0.5 elsewhere. It was +2 everywhere.
   - The drummer now has a crash. Kit A has none, so its 18 crashes had been silent; they are now played by the
     same pack's kit C.

   | measure | before | after |
   |---|---|---|
   | section LUFS (v1 / c1 / v2 / c2 / brk / solo / c3) | -13.1 / -10.0 / -11.5 / -9.7 / -13.6 / -9.6 / -9.4 | -15.0 / -10.8 / -13.8 / -10.2 / -15.6 / -11.1 / -9.6 |
   | chorus 3 minus chorus 1 | +0.6 LU | +1.2 LU |
   | chorus 3 minus solo | +0.2 LU | +1.5 LU |
   | chorus 2 minus verse 2 | 1.8 LU | 3.6 LU |
   | verse 1 to chorus 3 | 3.7 dB | 5.4 dB |
   | chorus 3 limiter drive | 6.5 dB | 5.8 dB |
   | chorus 3 LRA | 0.7 LU | 1.1 LU (Sunset 1.7) |
   | song LRA | 4.7 LU | 6.8 LU |
   | LUFS-I | -10.9 | -11.9 |

2. **Drums (sound designer, mix engineer).**
   - Kick:
     - The LinnDrum kick is layered under kit A's kick at -3 dB, low-passed at 3 kHz.
     - The kit compressor opens later (28 ms), with less tape.
     - The low end is split between kick and bass: the kit takes -3 dB at 160 Hz and the bass -3 dB at 150 Hz.
     - The bass ducks deeper under the kick (the kick duck is now 10 dB with 50 ms hold).
   - The drums come up in the hooks: +1.2 / +1.5 / +1.8 dB.
   - The drum presence dip is deeper (-4 dB at 3.3 kHz) and the dip at 10 kHz is -4 dB.
   - Tried and dropped:
     - a 5:1 kit compressor: punch 12.5 dB
     - a kit cut at 125 Hz without the Linn layer: 13.3 dB
     - a 70 Hz kit shelf: masking warnings in every section
     - less master drive: +0.3 dB of punch
   - Hats: measured on their own track, they sat 35 dB under the kit (-54 LUFS, nearly inaudible), so the "hats"
     punch is the snare and clap crack. They now have their own track and are a little darker and +2 dB. At +6 dB
     the air read +2.6 dB over Sunset and the top got more transient.

   | chorus 3 vs Sunset | before | after | Sunset |
   |---|---|---|---|
   | kick punch | 13.6 dB | 18.7 dB | 18.9 dB |
   | top punch | 15.3 dB | 15.0 dB | 11.1 dB |
   | bass | 89-354 Hz +2.8 dB | 111-224 Hz +2.2 dB (7-band bass -0.4) | |

   | mixer, rhythm vs hook | before | after | window |
   |---|---|---|---|
   | chorus 2 | -5.2 dB | -4.4 dB | -5..-2 |
   | chorus 3 | -5.7 dB | -4.4 dB | -5..-2 |

   The top-band punch stays about 4 dB over Sunset. Its cause is the snare and clap transients over a less dense
   top. It is info, not a warning.

3. **Hook top (sound designer).**
   - The hero tone's -1.5 dB at 3.3 kHz is gone; there is now a +3 dB shelf from 5 kHz.
   - The saw layer is opened to 2 kHz and kept from A4 up, so the doubles below stay piano.
   - A DX glass layer (`synthwave/arp_glass`) plays an octave up at -13 dB from E5. Moving the shelf alone changed the
     mix by less than 0.1 dB.
   - The doubles under the melody play at 75 %.
   - The pad's +2 dB of presence is gone, and keys and arp take -2 dB at 3-3.5 kHz, so the hook owns the band.
   - Loud hook hits in the chorus 3 spectrogram show no glassy smear.

   | measure | before | after |
   |---|---|---|
   | lead stem, chorus 2: 2.5-6 kHz share | 0.9 % | 2.7 % |
   | lead stem, chorus 2: centroid | 972 Hz | 1087 Hz |
   | chorus 3 vs Sunset, 2.5-6 kHz | -3.1 dB | -2.0 dB |
   | lead note dynamics | 7.1 dB | 8.2 dB |

   The 1.8-7.1 kHz gap to Sunset is no longer flagged. The mixer still reports `harsh` as info: 2-5 kHz is +3.2 dB
   over the profile, with the lead at 28 %. This is deliberate, since Sunset still reads 2 dB more there.

4. **Sax solo (arranger, mix engineer).**
   - The backing is thinned (see 1).
   - The sax is ridden +4 dB in the solo (was +1.5).
   - The bed ducks 4 dB and is carved -4.5 dB at 2.5 kHz under the sax.
   - The hero plate send is -11 (was -14).
   - The bass takes -2.5 dB and the drums -1.5 dB in the solo; the pad is ridden +1.5 there.
   - The wind player breathes deeper (depth 1.35, accent 0.18).

   | measure (stems, bars 93-100, K-weighted) | before | after |
   |---|---|---|
   | sax vs band, without its own plate | -2.9 dB | +2.4 dB |
   | sax vs band, with its own plate | -3.3 dB | +0.4 dB |
   | bed vs sax | -4.4 dB | -6.3 dB (mixer -6.0) |
   | bass vs sax | -1.6 dB | -6.6 dB |

   Sax note dynamics went from 3.9 to 4.4 dB, and the solo width from 40 to 45 %.

5. **Width.**
   - Strings `width` 1.35.
   - Pad `width` 1.2 (monobass 150), opening from verse 1 so the intro stays mono-safe (low-end correlation 0.85;
     it was 0.83, and 0.35 with the pad wide from the start).
   - E-piano and arp panned -0.45 / +0.45.

   | measure | before | after |
   |---|---|---|
   | width above 150 Hz, whole song | 52 % | 58 % |
   | width above 150 Hz, full sections | 50-55 % | 55-64 % (solo 45 %) |
   | width above 150 Hz, chorus 3 vs Sunset | 51 % | 58 % (Sunset 59) |
   | 250 Hz octave | ~25 % | ~38 % |

6. **Pivot (arranger).** The last bar of chorus 3 is now A, which is VI of C# minor and VII of B minor. The outro's G
   arrives a step down, not a tritone away.

7. **Housekeeping (producer).**
   - The `GOD_LEAD` switch is removed.
   - Licences are unchanged. The kick layer and crashes come from packs already used (LinnDrum: unclear; SampleRadar
     80s pop: no redistribution), so private listening is fine and publishing needs a check.

**Kept:**
- the hook cell and its whole journey
- the key change on the sax's G#7
- the pianist's voicings and ornament budget
- the rooms and echoes (reverb -9.8 LU, echo -17 LU)
- the sax's breathing
- the drummer's form
- the rolled final chord
- the bed under the hook: 4.5-5.3 dB in the choruses, 4.8 overall

**Delivery checks:**

| check | result |
|---|---|
| report | 0 warnings, 4 info |
| clicks | 0 in the mix |
| true peak | -1.13 dBTP |
| `master --check` | ok (true peak, loudness, LRA, mono) |
| `mix` findings | 1 info (`harsh`, deliberate, see 3) |

Ready for the A&R again.
