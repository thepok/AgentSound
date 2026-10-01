# Kestrel Bay - master

Chain: the power_ballad / rock master (`rock.master_chain`: eq -> 2:1 glue -> tape -> width 1.12, lows mono below
150 Hz -> limiter, ceiling -1.2 dBFS), with the mix's `arc` utility in front of it (the section rides, MIX.md) and a
master-fader fade over the last chord (after the limiter: before it the limiter would give the level back).

`python -m agentsound master songs/kestrel-bay --check` (platform auto):

- ok true peak -1.20 dBTP (<= -1)
- ok loudness -9.9 LUFS-I (rock -10..-7)
- ok loudness range 5.4 LU (2.5..12): intro -16.6, verse -12.3, chorus -8.8, bridge -9.6, solo -11.5 -> solo2 -8.6,
  break -13.5, chorus2 -8.5, outro -11.7 -> outro2 -8.9, end -8.7 and fading
- ok mono compatibility: correlation 0.67 (the mono sum ~0.8 dB quieter)
- info: streaming turns it down 4.1 dB (-14) / 6.1 dB (Apple -16)
- info tone: -1.7 dB at 1.6 kHz / +1.5 dB shelf at 6.3 kHz would move it to the rock average - not applied: the
  mid-forward hero lead is the song's character (the Baker Street comparison: 125 Hz-4 kHz within +-2 dB of the
  record's guitar solo).

No post-pass master: `out/mix.mp3` is the delivery.
