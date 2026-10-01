# Kestrel Bay - sound

| role | sound | range | chain + sends | why | checks |
|---|---|---|---|---|---|
| lead | `hero(s.track('lead', 'layered/hero_guitar_heavy'), family='guitar_heavy', genre='rock', bed=[strings, pad], competitors=[piano, gtr_l, gtr_r, clean], throws=False)` -> `hero/guitar_heavy` | G3-D6 (theme to D6) | FSBS Strat DI in 4 velocity zones (sustainer -> Plexi lead channel, bright cap -> Greenback 4x12) + the SampleRadar amped lead double (sustain); tone eq, tape, microshift double, its own dotted-8th / quarter echo, the `air` stage; hall -13, plate -18. fretwork adds per zone: the sampler `harmonic` (pinch / feedback), `bendfollow`, a `wah` ahead of each amp (switched in by moves) | a hero, not a beepy lead: body below 1 kHz, velocity = gain + tone + level (~1.6 dB / 10 velocity), long held peaks keep singing (the double) | note dynamics 5.4 dB (301 notes, vel 56-127); vibrato on a held B5 in the stem: 5.7 Hz, 0..+50 ct (up from the note); the whammy dive B5 -> B4 over 1.3 s; pinch: partial 6 over E4 visible at 2 kHz with the vibrato on it |
| lead_twin | the same hero (twin_track): the held string of the unison bends | E5 | the lead's chain and sends, -1.5 dB, pan +0.12 | a mono lead cannot hold one string while bending another | 2 notes |
| lead_noise | `fretwork.noise_track`: va noise, 12 dB band-pass following the note, portamento | - | crunch amp + cab (`_amp('lead')`), the lead's sends | pick scrapes / finger squeaks (aux of the moves; inaudible here: the solos chose no scrape - noted) | |
| gtr_l / gtr_r | `sampled/crunch_guitar` (Emily SG -> 2x12 V30 crunch) hard left, `sampled/dist_guitar` (FSBS dist) hard right | E2-E4 power chords | the patches' amps; -3 dB; gtr_r -2 dB at 3.3 kHz (out of the lead's presence) | the double-tracked wall: width without phasing (two guitars, two amps, two takes) | width >150 Hz 29 % |
| clean | `sampled/clean_guitar` (FSBS clean) | A2-E5 arpeggios | + a 170 Hz high-pass (the low strings belong to the bass), plate -16, echo -6 | the quiet parts' shimmer, 80s ballad echoes | |
| piano | power_ballad: Salamander grand | A1-E5 | the preset's chain, hall -15, plate -22, echo -14 | broken chords under the theme | |
| strings, pad | power_ballad: VPO section, Juno pad | E3-A5, C3-C5 | carved under the lead (song.carve at 2 kHz, -2.5 dB), hall | the bed, swelling with the form | bed -6.8 dB vs lead |
| drums, bass | power_ballad: Big Rusty kit (big room, drum bus), Growlybass | | the preset | | |

Rooms: room (drums, guitars), plate, hall (the hero, strings), echo (clean / piano), the lead's own stereo echo with
throws (the bridge's held note, the scream, the last note) on `fx.echo.mix` (fretwork 'echo' lane; the hero wrapper's
automatic throws off - one lane per target).

Hero log (build): source = the guitar_heavy hero's own 5 layers; carve strings / pad -2.5 dB at 2 kHz while it plays;
dips piano, gtr_l, gtr_r, clean -2 dB at 2 kHz; ride +1 dB in chorus / chorus2; duck off (rock profile).

Reference check (`compare --ref "Baker Street" --ref-start 3:29 --ref-end 4:03 --section solo2`, loudness-matched):
125 Hz - 4 kHz within +-2 dB of the record (the guitar region); -1.9 dB at 0.7-1.1 kHz -> the lead's +1.5 dB at
900 Hz (MIX); +14.7 dB sub and +10.7 dB above 3.6 kHz are the 1978 mono rip's (codec low-pass, no sub) vs a modern rock
master - not chased.
