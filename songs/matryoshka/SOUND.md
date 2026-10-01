# Matryoshka - sound design

| role | sound | range played | chain + sends | why | checks |
|---|---|---|---|---|---|
| hook (lead) | `hero(s.track('piano', 'hero/piano_pop'), genre='pop', bed=[strings, pad, choir], competitors=[violins], sections=[chorus1-4, coda])` + a DX glass layer (`synthwave/arp_glass`, +12 st, E5-C8, level -40 -> -16 in chorus4, -30 -> -14 over coda bars 9-12) | melody C5-E6 (intro / coda start C4-C5), LH C3-C4 in the sparse sections | the piano_pop hero chain (hp 100 Hz, -3.5 dB 350 Hz, +2.5 dB 3 kHz, +4 dB air, catch 3:1, glue 2:1, tape, width, dimension, air stage) + song eq -2 dB @ 300 Hz; plate -12, hall -20, echo throws | the user's taste: a bright, high, real sampled piano for the hook (never a beepy synth); the glass layer = the `layered/piano_glass_lead` sparkle for the last statements only | note dynamics 7.0 dB (velocity part 5.8 dB); gain -2 dB (it peaked +0.9 dBFS pre-master) |
| low | pop_band bass (Karoryfer Growlybass, finger), bassist pop | E1-E3; coda C2 A1 F1 G1 sustained | preset chain (hp 45, +5 dB 90 Hz, -8 dB 400 Hz, tube, 4:1, lp 2.8 kHz) + -3 dB @ 1 kHz; fader -5 dB | the preset's pop level sat 4 dB over the piano and masked its mids (verse1 warning) | masking warning gone |
| rhythm | pop_band drums (SampleRadar Chart Kit + a sine sub on C), drummer pop | - | preset kit eq, drum bus (4:1 parallel, tape) | subtle modern pop kit; the kick locked to the bass whose grid is the hook's rhythm | - |
| rhythm | pop_band perc (Gimme-a-Hand claps, tambourine, maracas) | shaker verse2, tamb + claps choruses 2-4, tamb 2 & 4 in the coda's second half | preset (hp 250, microshift wide, plate -8, hall -16) | lift in the later choruses | - |
| bed | pop_band pad (`synthwave/warm_pad`) | spread C3-C5 | preset (hp 280, -3.5 dB 450 Hz / 1.3 kHz, hall -3), kick sidechain 6 dB, hero duck / carve | a soft warm floor, cutoff opening in the intro | -33 dBFS RMS: a floor, not a voice |
| bed | `sampled/strings` (VPO section) | G3-G5 (4-5 voices) | hp 90, -2.5 dB 420 Hz, width 1.3, hall -8, kick sidechain 3 dB, hero duck / carve | warm cinematic section growing through the song | - |
| descant | `sampled/violins` (VPO 1st violins), played by `hornist` (strings, ballad: bow pressure) | Bb4-D6, long notes | hp 200, -2 dB 3.2 kHz, pan -0.35, hall -6, hero dip -2 dB 2.5 kHz, ducked 2 dB under the piano | the hook x4 on top of verse 2, the inversion x4 in chorus 4 | was flat (1.4 dB): now bowed (dynamics automated) |
| voice | `sampled/solo_cello` (SSO), played by `hornist` (strings, ballad) | A2-C5 | hp 75, -3 dB 320 Hz, pan 0.3, hall -8 | the minor section's voice (the hook in A minor) and the coda's x4 line - a singing string, not a synth | fader -7 dB after pass 1 (it sat over the piano); ridden +5 in minor, +2 in the coda (MIX) |
| voice | `sampled/choir_mixed` (VPO / SSO "ah") | chorus4 G3-A4 chords; coda x16 line C5+C4 (A4/A3, F4/F3, G4/G3), end C4 E4 G4 C5 | hp 120, -2 dB 350 Hz, hall -5, `dynamics` swells 0.3 -> 0.85, hero duck / carve | the x16 line - the key journey in 16 bars - sung | in range (sopranos C4-A5, tenors C3-A4): no silent notes |

Rooms: the pop_band returns - plate (224XL constant-density plate A), hall (224XL bright hall), echo (dotted 8th, the
hero's throws). Reverb -14.2 LU under the mix after pass 1 (target -16..-7), space verdict lush in most sections.

For the mixer: the lead is the piano everywhere; the cello is a second voice in `minor` and `coda` (the mixer reads it
as `low`), the choir must be heard in the coda (the concept's x16 line), the violins are a descant (bed). The glass
layer softens the attack a little in chorus4 / the coda - re-check the lead level there (HUMAN_FEEDBACK
"der Lead ist jetzt zu leise").

Licences: VPO (royalty-free, credit Paul Battersby), SSO (CC Sampling Plus: Sonatina Symphonic Orchestra), Salamander
Grand V3 (CC-BY: Alexander Holm), Karoryfer Growlybass (CC0), SampleRadar (royalty-free, no redistribution of the
samples), Gimme-a-Hand (GPL, music not a derivative), 224XL IRs (Little Devil). See out/credits.txt.
