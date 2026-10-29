# Kingsway After Rain (songs/kingsway-after-rain) - brief

## The wish

> A NEW ORIGINAL instrumental inspired by the late-70s soft-rock sax-anthem style of "Baker Street" - like our
> private cover's instrument version (which the user loved), but no melody, riff, chord sequence or lyric from it or
> the record. Plus: "great songs have a few famous moments - cool moves": 2-3 signature moments that recur / pay off.

## The song

- **Genre / profile**: late-70s soft rock; `ANALYSIS = {'profile': 'pop', 'loudness': [-12.5, -9]}` (a 70s record:
  dynamics over a radio-loud master).
- **Tempo / key / feel**: 114 BPM, E major with mixolydian / bluesy colour (D/E, C - D - E = bVI-bVII-I, G6, the blue
  G crushed into G#), 4/4, straight 8ths.
- **The hook**: the alto-sax riff on the user's 70s hero chain (`hero(sax, family='sax')`, played by
  `hornist.arrange(style='hero70s')`): a blues-scale climb B-D-E-G that grinds the blue third up into a held G#5 (the
  horn's top), a turn, an answer falling an octave to a sighing G#4, a rise over C - D, the grind again.
- **Verse lead**: a stage Rhodes played by the pianist (harmonized, decorated) - warm, round, no beep; the user loved
  the Rhodes on the cover's instrument version, and keeping the sax out of the verses makes every riff an event.
- **Band**: `bands.power_ballad` (Salamander grand, VPO strings, Juno pad, Big Rusty kit, Growlybass fingered, the
  hero guitar) + two acoustic guitars (songwriter strum L, steel double R) + the Rhodes + the hero sax.
- **Form** (148 bars, 5:18): `intro 8 | riff1 16 | verse1 16 | chorus1 10 | riff2 16 | verse2 16 | chorus2 10 |
  riff3 8 | bridge 8 | gsolo 16 | outro 24 (fade)`.
- **Signature moves**: (1) the UNISON BREAK - sax + guitar + bass in octaves with the kit on every note, the last
  bar of each chorus and of the solo (x3); (2) THE STOP - riff3 opens with one band hit, then the sax grinds into its
  G#5 alone over two bars of air, a tom pickup, the band slams back; (3) THE TRADE - outro, sax and guitar answering
  two bars each.
- **Reference**: none compared (style model only; covers/ stays private).

## HUMAN_FEEDBACK checklist

- [x] A song, not a loop: form, a riff that returns 4x, variation (riff A / riff B, verse 2 climbs), fills, signature moves.
- [x] No beepy lead: hero sax, Rhodes, hero guitar.
- [x] Lead in front: bed -7.5 dB vs lead (report), the band ducks 4 dB under the sax.
- [x] Real dynamics: flat_dynamics 0 (sax 3.7, Rhodes 6.2, guitar 6.0 dB per phrase).
- [x] Held wind notes breathe: every sax line through hornist.arrange.
- [x] Piano / Rhodes never a bare line: pianist.arrange.
- [x] The cover's mix lessons: bass -5 dB, drums not hot, the bed present and wider without negative correlation.
- [x] clicks 0, silent_notes 0, true peak <= -1 dBTP.

## Log

- producer: brief (above); slug kingsway-after-rain, 114 BPM E major.
- arranger: form + riff + Rhodes melodies + solo + outro trade; players: drummer / bassist / guitarist / pianist /
  hornist (ARRANGEMENT.md). Signature moves added on the user's extra wish.
- sound designer: power_ballad + acoustics + Rhodes + hero sax / hero guitar; guitar notes kept <= D6 (the DI's top;
  17 silent notes in the first build) (SOUND.md).
- mix engineer: MIX dict over three `mix` passes, findings down to info only (MIX.md).
- mastering engineer: -11.9 LUFS-I, TP -1.19, LRA 4.4 (MASTER.md).
- A&R: ship (AR.md).
