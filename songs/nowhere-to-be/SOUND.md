# Nowhere to Be - sound design (roles/sound-designer.md)

| part | sound | why / chain |
|---|---|---|
| voice | Hanami (DiffSinger) via `agentsound.singer`, style `jazz` | sung soft (the soft mode alone: 100 % of the vowels, power 0 %), make-up gain; the vocal hero clean (`drive=False`: no tube), its jazz space = its own short plate (`vocal_plate`, 1.0 s, 60 ms pre-delay) at -25 dB send: the return 20.5 LU under the dry voice, no echo, no throws, no band room. Mix: -1.5 dB at 380 Hz (her low register carries the low mids) |
| harmony | Hanami, take 3, formant +0.2, pan +0.25, -8 dB | the same dry hero chain without rides / ducks / dips |
| keys | `sampled/rhodes_vibrato` (jRhodes3d stereo-vibrato set) through the bossa preset's piano chain | the suitcase swirl is in the samples (the stereo field without a chorus); pan -0.05 (the preset's -0.5 balance threw the stereo Rhodes left; at -0.15 the mix leaned 1 dB left); velocities 27-87 = the warm bell layers, never the bark; the preset chain: low-mid cut, a soft-knee attack rounder, tape. KEYS_TRIM -3 dB (comped 8 velocity steps hotter for a bell tone with body) |
| bass | Meatbass upright (`sampled/upright_bass`, the preset) | long two-feel notes; BASS_TRIM +12 dB (the preset's bossa fader is set for an accented root-fifth 8th pattern at velocity 85-117; this line plays 64-74 so the peak catcher hardly touches it: 6.6 dB note dynamics) |
| drums | Swirly brush kit (the preset) | stirs one per beat (the preset's `swirly_sweep` at 72), taps on 2 and 4, a feathered kick; DRUM_TRIM +9 dB (the stirs read 24 dB under the voice at the bossa fader; now ~15) |
| cross-stick | Blonde Bop side stick (the preset's rim) | RIM_TRIM +11 dB; velocity 34-38: a soft click |
| tenor | `sampled/tenor_sax` (MTG, legato, live dynamics) as a SOFT hero: `hero(sax, family='sax', genre='jazz', drive=False, exciter=False, comp={'threshold': -26, 'ratio': 2.0, 'attack': 30, 'release': 160}, presence={3 kHz 0 dB, 9 kHz shelf +1 dB}, throws=False, echo=False)` | the hero's tone eq (honk out), a gentle 2:1 (the default 3:1 squeezed the note dynamics to 3.6 dB: `flat_dynamics`; now 5.4 dB), no tube grit, no exciter, a micro-pitch double, the breath stage (the hornist's air lands after the compressor), its plate; the bed (pad, Rhodes) ducks 1.5 dB and is carved at 2.5 kHz while it plays. Created before the hornist places its lanes (an earlier order put two 'air' stages on the track) |
| pad | `sampled/soft_poly` (SampleRadar analogue poly) | soft, slow, dark; ducked 1.5 dB and carved at 3 kHz under the voice (her hero), 4-bar velocity arches |
| space | the bossa preset's salon IR (0.8 s, close) for the band, the 224XL plate (keys -18), the tenor's hero plate, the voice's own short plate | dry and close: the band's room -33 LUFS, the voice not in it |

Credits that matter: Hanami (voicebank by Lotte V; the AI-dolGAN vocoder CC BY-NC-SA 4.0: non-commercial), jRhodes3d
(CC-BY-NC 4.0, Jeff Learman), MTG saxophones (CC-BY 4.0), Blonde Bop (CC-BY-SA 3.0, Glen MacArthur), Meatbass / Swirly
(CC0, Karoryfer), SampleRadar poly (no redistribution), the 224XL plate IR (licence unclear). Private listening: fine.
