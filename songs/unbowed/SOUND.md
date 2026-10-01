# Unbowed - sound

The orchestra Beethoven wrote for in 1804-1812, from the shared preset: `bands.symphony_orchestra(s, without=
('trombones', 'tuba', 'percussion', 'harp', 'celesta'))` - its levelled SSO 4.0 / VPO / VSCO sections, articulation
keyswitches, live dynamics lanes, seating and the Musikverein IR hall - plus three solo players.

| role | sound | range played | chain + sends | why | checks (last full build) |
|---|---|---|---|---|---|
| violins1 / violins2 | SSO 4.0 1st / 2nd violins KS (sustain, staccato, marcato, tremolo, pizzicato) | G3-C7 (octave doublings above fold down) | preset eq + `steel` dip -2.5 dB at 3.2 kHz; hall -6 | the theme carriers; the recipe: -1..-3 dB at 2.5-4 kHz when the top is steely (presence was +6.1 dB vs the classical reference) | note dynamics 12.0 / 14.8 dB per phrase |
| violas / cellos / basses | SSO KS + VPO re-looped sustains | C3-C6 / C2-E4 / C1-D3 | preset | the drive (8ths), syncopes, tremolo, pizzicato, the fugato | 9.7 / 9.1 / 6.4 dB |
| flutes, oboes, clarinets, bassoons | SSO a2 (oboe sustain: VSCO 2) | the pairs voiced by `voicing.WINDS8` | preset | colour and doubling; the oboes have no marcato / tremolo: those marks fall back to sustain | 8.5-10.1 dB |
| horns | SSO horns a4 (the section) | G3-F5 | preset | chords on I / V, the theme doubled in the coda, the horn call ff in the coda | 6.2 dB |
| trumpets | SSO trumpets, natural notes only (C4 E4 G4 C5 E5 G5) | C4-G5 | preset | natural trumpets in C: only the chord tones the instrument had | 6.5 dB |
| timpani | VSCO 2 timpani hit / roll on C3 / G2 | C3, G2 | preset | Beethoven's two drums, tonic and dominant | 3.6 dB (info: the hits are ff; the rolls carry the crescendi) |
| horn_solo | `sampled/solo_horn` (VSCO 2, CC0) | G3-Bb4 | pan -0.3, hall -4 | the calls that announce the second theme (Eb, then G); hornist family 'trumpet', style 'classical', no vibrato (vib_ct 0, peak 4 ct) | 9.7 dB |
| clarinet_solo | `sampled/solo_clarinet` (VSCO 2, CC0) | Ab4-Gb5 | pan -0.05, hall -6 | the lyrical second theme and its pp echo in Gb (the best pianissimo of the winds) | 25 dB over the piece (p dolce vs pp) |
| oboe_solo | `sampled/solo_oboe` (VSCO 2, CC0) | G4-G5 | pan 0.1, hall -7 | the recapitulation's cadenza; hornist family 'clarinet' with a light vibrato (8 / 14 ct) | 6.0 dB |

Rooms: the preset's Musikverein IR hall (one room for everyone), its return opened to 20 kHz and lifted +2 dB above
9 kHz (the SSO sections are dark on top: air was -4.4 dB). The hall blooms on the three fermatas
(`orch.ring(..., back=)`: given back where the music goes on) and on the final chord. Reverb -10.5 LU under the mix,
width > 150 Hz 34 %, lows correlation 0.92.

For the mixer: the lead changes per section (no single lead track): violins I (t1, rec1, rec3 first half, closing,
coda2), the solo clarinet (t2), violins I + flute (t2 second half), the entering voice of the fugato, the solo horn
(trans, rec2 calls), the solo oboe (cadenza). The tutti doublings (violins I / II / flutes / oboes in octaves,
cellos / basses in octaves) are intended: the masking warnings between them are the orchestra, not a fault.

Credits: Sonatina Symphonic Orchestra 4.0 (CC Sampling Plus 1.0), Virtual Playing Orchestra 3, VSCO 2 CE (CC0),
Voxengo IM Reverbs.
