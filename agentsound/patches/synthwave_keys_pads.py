"""Synthwave sound library, part 'keys & pads': pads, strings, keys, stabs, reverb/group buses, master chains.

  pads/strings  synthwave/warm_pad juno_pad jupiter_strings dx_strings dream_pad dark_pad choir_pad sweep_pad
  keys/stabs    synthwave/epiano epiano_bright dx_bells marimba brass_stab dx_brass poly_stab organ
  reverbs       bus/hall bus/hall_lush bus/plate bus/plate_80s bus/shimmer      (group: bus/music)
  masters       master/synthwave master/dreamwave master/darksynth master/audition

Level calibration: every instrument patch at gain_db 0 lands at about -18 LUFS integrated (track node, dry)
playing its natural material (the `python -m agentsound audition` phrase unless the notes say otherwise), so
a mix starts balanced; the calibration lives in the instrument's own `level` param, the patch gain_db stays 0.
Each patch's notes give the measured values (width = side/mid energy of the dry track, corr = L/R correlation).

Lush pass (v5, "sound expensive by default"): every sustained synth carries its own width (Juno chorus II at the
lusher 0.6 balance plus a mono-compatible `dimension`, modes 1-2 on sources that are already wide), so the dry
beds read 60-80 % wide (correlation 0.1-0.25) instead of 30-40 %; default sends are the recipe's recommended
levels (pads/strings hall -8, keys plate -12, bells hall -10 + echo -14); the reverb returns are calibrated (an
output gain in their own chain, the bus fader stays 0 dB) so that at those sends the hall + plate land ~10-12 LU
under a full mix (recipes/synthwave.md 'Size and space'); the master chains add glue, tape, a gentle exciter and
width with a mono low end. Version: see VERSION (bump it when a sound changes audibly).
"""

from ..vamod import lfo
from . import Patch, fx, inst, register

VERSION = 5  # v3: LFOs in the va 'mods'; v4: DX7 thump high-passes removed; v5: lush pass (width, sends, returns)


def _va(**p):
    """inst.va with '__' -> '.' in the keyword names (osc1__wave -> osc1.wave)."""
    return inst.va({k.replace('__', '.'): v for k, v in p.items()})


def _hp(freq):
    """Steep (24 dB/oct) clean-up high-pass."""
    return fx.eq({'hp.freq': freq, 'hp.slope': 24})


def _dim(mode=1, **kw):
    """Dimension-D style width: adds a pure side signal above 150 Hz (the mono sum stays the dry signal)."""
    return fx.dimension(mode=mode, **kw)


# ------------------------------------------------------------------------------------- masters

register(Patch(
    'master/audition',
    fx=[fx.limiter(ceiling=-1.0, gain=0.0, release=200)],
    notes='v1. Neutral audition master: only a true-peak-safe limiter (ceiling -1 dBFS, no drive), so the '
          'audition command measures patch levels as they are (a calibrated patch never touches it).'))

register(Patch(
    'master/synthwave',
    fx=[fx.eq({'hp.freq': 25, 'peak1.freq': 380, 'peak1.gain': -2.5, 'peak1.q': 0.6,
               'peak2.freq': 1200, 'peak2.gain': -1.0, 'peak2.q': 0.8, 'high.freq': 10000, 'high.gain': 2.5}),
        fx.compressor(threshold=-14, ratio=2, knee=6, attack=30, release=300, detector='rms', keyhp=120),
        fx.tape(speed='30', drive=-2, bias=0.1, bump=1.0, wow=0.0, flutter=0.0, hiss=0.0),
        fx.exciter(freq=4000, drive=30, amount=0.35, character=0.3),
        fx.width(width=1.15, monobass=120),
        fx.limiter(ceiling=-1.2, gain=3.0, release=80)],
    notes='v2. Synthwave master chain: eq (25 Hz rumble high-pass, -2.5 dB broad low-mid dip at 380 Hz and -1 dB at '
          '1.2 kHz against the mud/honk a wall of mid-register synths builds up, +2.5 dB air shelf at 10 kHz) -> '
          'glue compressor 2:1 (rms, 30 ms attack keeps the drums punchy, 300 ms release, detector high-passed at '
          '120 Hz so the kick does not pump the mix; ~1 dB of gain reduction on a mix of -18 LUFS tracks) -> tape '
          '(30 ips mastering deck, drive -2: soft peak rounding and a +1 dB head bump, no wow/flutter/hiss) -> '
          'exciter (sheen above 4 kHz, gentle: amount 0.35, mostly 2nd harmonic) -> width 1.15 with everything below '
          '120 Hz mono -> limiter, ceiling -1.2 dBFS (true-peak aware; lands at <= -1.0 dBTP) with 3 dB drive. '
          'Measured on songs/_demo_lush (9 calibrated tracks + hall/plate/echo/shimmer/gated returns): -10.9 LUFS-I, '
          'TP -1.1 dBTP, mix width 35-39 % (correlation 0.44-0.48) in the full sections, above 150 Hz 66-77 %, '
          'sparse pad-only intros/breaks stay at correlation >= 0.05 (not phasey). Use: '
          'song.master.use("master/synthwave"). Loudness is set by the limiter drive: '
          'song.master.use(patches.get("master/synthwave").but_fx("limiter", gain=5)) -> aim at -12..-9 LUFS-I. '
          'Narrower (a very wide arrangement: pads + wide returns only): .but_fx("width", width=1.05); more glue: '
          'compressor threshold -18; more sheen: exciter amount 0.5. Softer / harder flavours: master/dreamwave, '
          'master/darksynth. Lush pass (v2): + tape, exciter, width 1.05 -> 1.15, a deeper "smile" eq.'))

register(Patch(
    'master/dreamwave',
    fx=[fx.eq({'hp.freq': 25, 'peak1.freq': 350, 'peak1.gain': -1.5, 'peak1.q': 0.6,
               'high.freq': 9000, 'high.gain': 0.5}),
        fx.compressor(threshold=-16, ratio=1.6, knee=10, attack=40, release=400, detector='rms', keyhp=120),
        fx.tape(speed='7.5', drive=2, bias=0.25, bump=2.5, wow=0.12, flutter=0.06, hiss=0.0),
        fx.exciter(freq=3000, drive=25, amount=0.2, character=0.0),
        fx.width(width=1.12, monobass=120),
        fx.limiter(ceiling=-1.2, gain=1.5, release=150)],
    notes='v1 (lush pass). Dreamwave / chillsynth master (FM-84, Timecop1983): softer and warmer than '
          'master/synthwave - gentle 1.6:1 soft-knee glue (40 ms / 400 ms), more tape (7.5 ips: +2.5 dB head bump '
          'at 70 Hz, top rolled off from ~14 kHz, drive 2, slight wow 0.12 / flutter 0.06: the "VHS" drift), a '
          'smooth even-harmonic exciter (character 0), width 1.12 (mono below 120 Hz; dreamwave beds are already very '
          'wide) and a slow limiter with 1.5 dB drive (songs/_demo_lush through it: -11.8 LUFS-I, TP -1.2 dBTP; the '
          'dreamwave profile wants -14..-10). Use with the dreamwave analysis profile (python -m agentsound build ... '
          '--profile dreamwave), which also wants the reverb 2-3 LU wetter than synthwave (-11..-5 LU): make the '
          'song\'s "hall" bus/hall_lush (s.bus("hall", "bus/hall_lush")), send the beds at -6 and add '
          'bus/shimmer. Tweak: but_fx("tape", wow=0-0.3) (more or less warble), but_fx("limiter", gain=0-4).'))

register(Patch(
    'master/darksynth',
    fx=[fx.eq({'hp.freq': 28, 'low.freq': 90, 'low.gain': 1.0, 'peak1.freq': 400, 'peak1.gain': -1.5, 'peak1.q': 0.7,
               'peak3.freq': 3200, 'peak3.gain': 1.0, 'peak3.q': 0.8, 'high.freq': 10000, 'high.gain': 1.0}),
        fx.compressor(threshold=-16, ratio=3, knee=6, attack=12, release=150, detector='rms', keyhp=100),
        fx.tape(speed='15', drive=6, bias=0.2, bump=1.5, wow=0.0, flutter=0.0, hiss=0.0),
        fx.exciter(freq=2500, drive=30, amount=0.35, character=0.6),
        fx.width(width=1.05, monobass=150),
        fx.limiter(ceiling=-1.2, gain=6.0, release=50)],
    notes='v1 (lush pass). Darksynth master (Perturbator, Carpenter Brut): harder than master/synthwave - +1 dB low '
          'shelf at 90 Hz, -1.5 dB at 400 Hz, +1 dB bite at 3.2 kHz, firm 3:1 glue (12 ms attack, 150 ms release), '
          'hot tape (15 ips, drive 6: audible saturation that thickens distorted synths), an edgy odd-harmonic exciter '
          '(character 0.6 from 2.5 kHz), barely widened (1.05, mono below 150 Hz: darksynth is centred and '
          'aggressive) and a fast limiter with 6 dB drive (songs/_demo_lush through it: about -9 LUFS-I, TP -1.1 dBTP; '
          'the darksynth profile wants -10..-7 LUFS). Use with the darksynth analysis profile. Tweak: '
          'but_fx("tape", drive=3-12), but_fx("limiter", gain=3-7).'))

# ----------------------------------------------------------------------------------------- buses

register(Patch(
    'bus/hall',
    fx=[fx.reverb(type='hall', mix=1.0, size=0.85, decay=3.4, predelay=30, lowcut=250, highcut=11000,
                  damping=7500, moddepth=0.6, modrate=0.5, early=0.2, width=1.0),
        fx.eq({'peak1.freq': 450, 'peak1.gain': -1.5, 'peak1.q': 0.8, 'output': 1.5})],
    notes='v2. Big lush 80s hall return, 100 % wet: RT60 3.4 s, 30 ms pre-delay (keeps attacks dry and clear), wet '
          'high-passed at 250 Hz (no low-end wash) and low-passed at 11 kHz with 7.5 kHz damping, modulated '
          '(moddepth 0.6: no metallic ringing, a gently moving tail), natural width 1.0 (the return reads ~110 % '
          'wide at correlation about -0.05; 1.1 read -0.13, partly out of phase in mono), '
          '-1.5 dB at 450 Hz so the tail does not add low-mid mud, +1.5 dB output calibration: with the library\'s '
          'default sends (pads/strings -8, leads -10, keys -16..-18) the hall of a full mix lands 10-13 LU under the '
          'mix (songs/_demo_lush: -12.8 LU; the recipe target is 8-14). Created by song.hall(); params go to its '
          'reverb: song.hall(decay=4.5, predelay=40) for dreamwave, song.hall(decay=2.4) for faster tempos; the '
          'level with song.hall(gain_db=-3..+3) or the sends. Longer/wider/more modulated: bus/hall_lush. Typical '
          'sends: pads -6..-10, strings -8, leads -8..-12, keys -14..-18, snare -16. Lush pass (v2): brighter, '
          'more modulated, calibrated.'))

register(Patch(
    'bus/hall_lush',
    fx=[fx.reverb(type='hall', mix=1.0, size=0.95, decay=4.8, predelay=32, lowcut=260, highcut=10000,
                  damping=6500, diffusion=0.9, moddepth=0.8, modrate=0.4, early=0.15, width=1.0),
        fx.chorus(mode='I', mix=0.3),
        fx.eq({'peak1.freq': 450, 'peak1.gain': -2.0, 'peak1.q': 0.8, 'output': 1.5})],
    notes='v1 (lush pass). The long, wide, modulated hall for dreamwave, ballads, intros and breakdowns: RT60 4.8 s, '
          'size 0.95, 32 ms pre-delay, wet 260 Hz-10 kHz with 6.5 kHz damping (dark, smooth), deep delay-line '
          'modulation (0.8) plus Juno chorus I on the tail (a slowly shimmering, wide wash; ~105 % wide at return '
          'correlation ~0), -2 dB at 450 Hz, calibrated like bus/hall (+1.5 dB output): about as loud as bus/hall at the same '
          'sends (a pad at -8 gets a return ~9 dB under its dry level), but the tail rings much longer into '
          'breaks (-13 dB 0.3-0.8 s after the music stops vs -17 dB). Use: lush = s.bus("hall", "bus/hall_lush") '
          '(as the song\'s "hall", so every patch\'s default hall send feeds it) or as a second return for the bed: '
          's.bus("verb", "bus/hall_lush") with sends={"verb": -8} on the pads. Tweak: but_fx("reverb", decay=3.5-7, '
          'predelay=20-60), but_fx("chorus", mix=0-0.5).'))

register(Patch(
    'bus/plate',
    fx=[fx.reverb(type='plate', mix=1.0, decay=2.0, predelay=18, lowcut=300, highcut=11000, damping=8000,
                  moddepth=0.4, width=1.0),
        fx.eq({'output': 7.0})],
    notes='v2. Bright dense 80s plate return, 100 % wet: RT60 2.0 s, 18 ms pre-delay, wet 300 Hz-11 kHz, light '
          'modulation, natural width (return correlation ~0), +7 dB output calibration: v1 sat 26 LU under a full '
          'mix at the recommended key sends (inaudible); now an e-piano sending -12 dB gets a plate about 9 dB under '
          'its dry level, clearly audible sheen (songs/_demo_lush: -18 LU vs the mix from one e-piano). For e-piano, '
          'keys, stabs, snares and vocal-like leads. Created by song.plate(); params go to the reverb: '
          'song.plate(decay=1.2) tighter, (decay=2.6) bigger. Typical sends: keys/e-piano -10..-14, stabs -12..-14, '
          'snare -12..-18, leads -14..-16. Brighter 80s EMT: bus/plate_80s. Lush pass (v2): calibrated so it is '
          'heard.'))

register(Patch(
    'bus/plate_80s',
    fx=[fx.eq({'hp.freq': 500, 'lp.freq': 10000}),
        fx.reverb(type='plate', mix=1.0, decay=2.4, predelay=22, lowcut=400, highcut=14000, damping=10000,
                  moddepth=0.5, width=1.0),
        fx.eq({'peak3.freq': 4500, 'peak3.gain': 2.0, 'peak3.q': 0.7, 'output': 9.0})],
    notes='v1 (lush pass). The bright 80s EMT plate (Abbey Road style): the send is filtered 500 Hz-10 kHz before '
          'the plate (only the body and bite of a part reach it, so it never muddies), RT60 2.4 s, 22 ms pre-delay, '
          'bright undamped top (14 kHz / 10 kHz damping), +2 dB at 4.5 kHz, natural width (return correlation ~0), calibrated like '
          'bus/plate (an e-piano at -12 gets a plate ~9 dB under its dry level). For snares (the 80s ballad '
          'snare), claps, e-piano, stabs, bells and vocal-like leads when bus/plate is too polite. Use: '
          'p80 = s.bus("plate", "bus/plate_80s") (as the song\'s "plate": the patch default sends feed it) or a '
          'separate s.bus("plate80", "bus/plate_80s") with sends={"plate80": -14}. params: s.bus(...) with '
          'patches.get("bus/plate_80s").but_fx("reverb", decay=1.8-3.2).'))

register(Patch(
    'bus/shimmer',
    fx=[fx.shimmer(mix=1.0, decay=8.0, shimmer=0.55, fifth=0.0, predelay=50, lowcut=300, highcut=10000,
                   damping=6500, moddepth=0.7, width=0.8),
        fx.eq({'output': 2.0})],
    notes='v1 (lush pass). Dreamy octave-up shimmer reverb return (Eventide / Valhalla idea), 100 % wet: RT60 8 s, '
          'the tail rises into a soft octave halo (shimmer 0.55), 50 ms pre-delay, wet 300 Hz-10 kHz, 6.5 kHz '
          'damping (the upper octaves stay silky), modulated, width 0.8 (mono-safe, return correlation ~0.2), '
          '+2 dB output calibration. For intros, breakdowns, outros and held pad / bell / e-piano chords: '
          'sh = s.bus("shimmer", "bus/shimmer"); pad sends={sh: -8} in the intro and -20 under a busy chorus '
          '(automate "send.shimmer": the halo blooms when the drums drop). songs/_demo_lush: pad at -8 -> shimmer '
          '9-11 LU under the intro/break. Keep it off the bass, drums and fast arps (they turn it into noise). '
          'Tweak: but_fx("shimmer", shimmer=0.3-0.9, fifth=0.2-0.5 (organ/choir bloom), decay=5-15). The report counts it '
          'as a reverb return (in the wetness numbers) and judges its audibility in its loudest section, so a '
          'shimmer that only blooms in the breaks is not called inaudible.'))

register(Patch(
    'bus/music',
    fx=[fx.compressor(threshold=-18, ratio=2, knee=8, attack=30, release=250, detector='rms', keyhp=120,
                      makeup=1.0)],
    notes='v1. Glue compressor for the non-drum music group (bass, pads, keys, arps, leads): 2:1 rms, soft '
          'knee, 30 ms attack, 250 ms release, detector high-passed at 120 Hz; with about six calibrated '
          '(-18 LUFS) tracks it averages ~1.5-2 dB of gain reduction (+1 dB makeup), which binds the parts '
          'together without audible pumping. Use: music = song.bus("music", "bus/music"); '
          'song.track(..., output=music). Keep drums outside it (or on their own drum bus), sidechain pumping '
          'belongs on the tracks (song.sidechain). More glue: .but(threshold=-22); gentler: .but(ratio=1.5). '
          'Its summed output peaks near 0 dBFS before the master (float, harmless); lower the bus gain_db '
          '(song.bus("music", "bus/music", gain_db=-3)) if the report flags node_hot and you want headroom.'))

# ------------------------------------------------------------------------------------------ pads

register(Patch(
    'synthwave/warm_pad',
    instrument=_va(osc1__wave='saw', osc2__wave='saw', osc2__level=0.8, osc2__fine=6,
                   cutoff=3000, resonance=0.1, filter__keytrack=0.5, filter__velocity=0, filter__env=0.8,
                   fenv__attack=0.6, fenv__decay=3.0, fenv__sustain=0.5, fenv__release=1.5,
                   amp__attack=0.45, amp__decay=2.0, amp__sustain=1.0, amp__release=1.6, amp__velocity=0.3,
                   hpf=140, drift__pitch=4, drift__cutoff=0.8, level=-8.5),
    fx=[fx.chorus(mode='II', mix=0.6),
        fx.eq({'peak1.freq': 320, 'peak1.gain': -3, 'peak1.q': 0.8}),
        _dim(1)],
    sends={'hall': -8},
    notes='v2. Juno-106 style warm pad: two saws 6 ct apart into a 24 dB ladder low-pass (3 kHz, gentle slow filter '
          'bloom over the first second), 0.45 s attack, 1.6 s release, Juno HPF at 140 Hz, analog drift, Juno chorus '
          'II (the lush one) then a Dimension-D style side layer: v1 read 34 % wide, v2 ~60 % (correlation 0.25) '
          'with a mono-compatible centre. Range: chords in C3-C5 (open/spread voicings). Use: the default synthwave '
          'bed for verses and choruses; sidechain it to the kick (depth 4-8). Tweak: cutoff 1500-5000 (automate '
          '"instrument.cutoff" with exp curves for intros/risers), amp.attack 0.05-1.5, amp.release 0.8-3, osc2.fine '
          '4-12 (more beating), chorus mode I for a subtler image, but_fx("dimension", mix=0) for the plain Juno. '
          'Sends: hall -8 (-6 for dreamier; + a shimmer send in intros). Measured -17.9 LUFS (audition chords). Lush '
          'pass (v2): chorus II 0.5 -> 0.6, + dimension mode 1, -3 dB at 320 Hz, hall -10 -> -8.'))

register(Patch(
    'synthwave/juno_pad',
    instrument=_va(osc1__wave='square', osc1__pw=0.5, osc2__wave='saw', osc2__level=0.7, osc2__fine=3,
                   mods=[lfo('triangle', hz=0.6, mode='global', id='pwm') >> ('osc1.pw', 0.2025)],
                   cutoff=5500, resonance=0.15, filter__keytrack=0.5, filter__velocity=0, filter__env=0.5,
                   fenv__attack=0.3, fenv__decay=1.5, fenv__sustain=0.6, fenv__release=1.2,
                   amp__attack=0.25, amp__decay=1.5, amp__sustain=1.0, amp__release=1.4, amp__velocity=0.3,
                   hpf=180, drift__pitch=3, level=-11.9),
    fx=[fx.chorus(mode='II', mix=0.65), _dim(1)],
    sends={'hall': -8},
    notes='v2. Brighter Juno pad: pulse-width-modulated square (LFO 0.6 Hz, depth 0.45) plus saw, as a Juno DCO '
          'outputs both, filter fairly open (5.5 kHz), HPF 180 Hz, chorus II and a dimension side layer: the '
          'shimmering Juno "strings" pad, ~66 % wide (v1 33 %). Range: C3-C5, also nice as high held notes/octaves '
          'in C5-C6. Use: brighter chorus pad, layer an octave above warm_pad (gain_db -3 each when both play), '
          'intros with a filter sweep. Tweak: mod.pwm.amount 0.1-0.27 (PWM depth), its rate 0.3-1.5 Hz '
          '(.with_mods(vamod.lfo("triangle", hz=1.0, mode="global", id="pwm") >> ("osc1.pw", 0.2))), cutoff '
          '2500-9000, amp.attack 0.05-1, hpf 120-300 (thinner to sit above keys). Sends: hall -8. Measured -17.9 '
          'LUFS (audition chords). Lush pass (v2): chorus II 0.5 -> 0.65, + dimension mode 1, hall -10 -> -8.'))

register(Patch(
    'synthwave/jupiter_strings',
    instrument=_va(osc1__wave='saw', osc2__wave='saw', osc2__level=0.9, osc2__fine=8,
                   filter__type='lp12', cutoff=3200, resonance=0.1, filter__keytrack=0.6, filter__velocity=0.3,
                   filter__env=1.0, fenv__attack=0.35, fenv__decay=1.2, fenv__sustain=0.6, fenv__release=1.0,
                   amp__attack=0.35, amp__decay=1.0, amp__sustain=1.0, amp__release=1.2, amp__velocity=0.3,
                   mods=[lfo('triangle', hz=5.2, delay=0.5, fade=1.0, mode='global', id='vib') >> ('pitch', 7)],
                   hpf=200, drift__pitch=4, level=-11.9),
    fx=[fx.chorus(mode='custom', rate=0.7, depth=2.5, delay=8, voices=3, spread=1, mix=0.6),
        fx.eq({'high.freq': 9000, 'high.gain': -2}),
        _dim(1)],
    sends={'hall': -8},
    notes='v2. Jupiter-8 / string-machine strings: two saws 8 ct apart through the 12 dB filter (brighter, more open '
          'than a ladder), delayed vibrato (7 ct at 5.2 Hz after 0.5 s), 0.35 s bow-like attack, three-voice '
          'ensemble chorus (Solina-style), HPF 200 Hz; ~72 % wide (v1 62 %). Range: C3-C6; best in the upper '
          'register (A4-A5 lines/triads over a pad). Use: chorus lift, string lines, layered with '
          'synthwave/dx_strings (dx at -4..-6 dB) for the classic analog+FM string stack; as a second bed layer over '
          'a pad give it gain_db -3. Tweak: mod.vib.amount 0-15 (vibrato, ct), amp.attack 0.1-1 (slow swells), '
          'cutoff 2000-6000, osc2.fine 5-12. Sends: hall -8 (-6 for big ballad strings). Measured -18.0 LUFS '
          '(audition chords). Lush pass (v2): + dimension mode 1 on the already wide ensemble, hall -10 -> -8.'))

register(Patch(
    'synthwave/dx_strings',
    instrument=inst.dx7('STRINGS 1', detune=9, width=0.8, level=3.0),
    fx=[_hp(100), _dim(1)],
    sends={'hall': -8},
    notes='v3. DX7 ROM1 "STRINGS 1", stereo-doubled (+-4.5 ct, width 0.8) = the glassy, bowed FM string ensemble of '
          '80s pop; each note has a bright bow attack, the sustain is smooth, the release short. High-passed at 100 '
          'Hz (keeps the bass range clear, C3 fundamentals intact); ~69 % wide (v2 58 %). Range: C3-C6. Use: on its '
          'own for a thinner digital string, or layered with synthwave/jupiter_strings / warm_pad at -4..-6 dB to '
          'add bow and shimmer. Tweak: detune 5-15 (width of the doubling), brightness -0.3..0.3, velsens 0.5-1 '
          '(velocity controls the bow bite), modwheel 0.1-0.3 (vibrato). Sends: hall -8. Measured -17.9 LUFS '
          '(audition chords). Lush pass (v3): + dimension mode 1, hall -10 -> -8.'))

register(Patch(
    'synthwave/dream_pad',
    instrument=_va(osc1__wave='saw', osc2__wave='triangle', osc2__level=0.4, osc2__semi=12,
                   unison=5, unison__detune=0.35, unison__spread=0.9,
                   cutoff=1800, resonance=0.2, filter__keytrack=0.5, filter__velocity=0, filter__env=1.2,
                   fenv__attack=2.5, fenv__decay=4.0, fenv__sustain=0.5, fenv__release=3.0,
                   mods=[lfo('sine', hz=0.07, mode='global', id='breath') >> ('cutoff', 0.4)],
                   amp__attack=1.8, amp__decay=3.0, amp__sustain=1.0, amp__release=3.5, amp__velocity=0.2,
                   hpf=160, drift__pitch=5, level=-7.6),
    fx=[fx.chorus(mode='II', mix=0.6), _dim(1)],
    sends={'hall': -6},
    notes='v2. Dreamwave pad: 5-voice lightly detuned saw stack plus a soft triangle an octave up (shimmer), very '
          'slow swell (1.8 s attack) with a 2.5 s filter bloom that keeps opening through the chord, slow breathing '
          'LFO on the cutoff (0.07 Hz), 3.5 s release so chords melt into each other, chorus II and a dimension side '
          'layer (~80 % wide, correlation ~0.1; v1 54 %). Range: C3-C5, sustained chords of 1-2 bars or longer '
          '(short notes never open up). Use: FM-84 / Timecop1983 style beds, intros, breakdowns, outros - with '
          'bus/hall_lush and a bus/shimmer send. Tweak: amp.attack 0.8-4, fenv.attack 1-5, cutoff 1000-3500, '
          'unison.detune 0.2-0.5, mod.breath.amount 0-0.8 (octaves). Sends: hall -6 (with song.hall(decay=5) or '
          'bus/hall_lush for a drenched sound). Measured -18.0 LUFS (audition chords). Lush pass (v2): chorus II '
          '0.45 -> 0.6, + dimension mode 1.'))

register(Patch(
    'synthwave/dark_pad',
    instrument=_va(osc1__wave='saw', osc2__wave='saw', osc2__level=0.4, osc2__semi=-12, osc2__fine=-9,
                   unison=3, unison__detune=0.45, unison__spread=0.8,
                   cutoff=800, resonance=0.35, filter__drive=0.5, filter__keytrack=0.3, filter__velocity=0,
                   filter__env=1.5, fenv__attack=1.2, fenv__decay=3.0, fenv__sustain=0.4, fenv__release=2.0,
                   mods=[lfo('triangle', rate=16, mode='global', id='sweep') >> ('cutoff', 0.6)],
                   amp__attack=0.5, amp__decay=2.0, amp__sustain=1.0, amp__release=2.0, amp__velocity=0.2,
                   hpf=90, drift__pitch=5, level=-7.8),
    fx=[fx.saturator(mode='tube', drive=6, mix=0.6, tone=-2),
        fx.chorus(mode='custom', rate=0.2, depth=3, delay=12, voices=2, spread=1, mix=0.5),
        fx.eq({'hp.freq': 120, 'hp.slope': 24, 'peak1.freq': 250, 'peak1.gain': -2, 'peak1.q': 0.8}),
        fx.width(width=1.1, monobass=160)],
    sends={'hall': -10},
    notes='v2. Darksynth pad: 3-voice detuned saws plus a -12 st saw (growl) into a driven, resonant ladder at 800 '
          'Hz, slow filter swell and a 4-bar synced LFO sweep on the cutoff, tube saturation, slow wide chorus; '
          'everything below 120 Hz is cut and below 160 Hz kept mono so it never fights the bass. Range: C3-C5 '
          '(chords, fifths, drones); lower (C2-C4) only without a busy bass. Use: Perturbator / Carpenter Brut '
          'menace under distorted bass, phrygian drones, tension builds. Tweak: cutoff 400-2000 (automate '
          '"instrument.cutoff"), resonance 0.2-0.6, filter.drive 0.3-0.8, mod.sweep.amount 0.3-1.2 (octaves), sweep '
          'period 8-32 beats (.with_mods(vamod.lfo("triangle", rate=32, mode="global", id="sweep") >> ("cutoff", '
          '0.6))), saturator drive 3-12 ("fx.saturator.drive"). Sends: hall -10. Measured -18.0 LUFS (audition '
          'chords C3-C5); -20.7 LUFS voiced in E2-E4. Lush pass (v2): slow chorus mix 0.35 -> 0.5, hall -12 -> -10; '
          'darksynth stays narrower than the dreamy pads: ~62 % wide, v1 49 %.'))

register(Patch(
    'synthwave/choir_pad',
    instrument=_va(osc1__wave='saw', osc2__wave='saw', osc2__level=0.8, osc2__fine=7,
                   unison=4, unison__detune=0.3, unison__spread=0.6, noise__level=0.06, noise__color='pink',
                   filter__type='bp12', cutoff=800, resonance=0.4, filter__keytrack=0, filter__velocity=0,
                   filter__env=0,
                   amp__attack=0.6, amp__decay=1.0, amp__sustain=1.0, amp__release=1.8, amp__velocity=0.2,
                   mods=[lfo('sine', hz=5.0, delay=0.4, fade=0.8, mode='global', id='vib') >> ('pitch', 8)],
                   hpf=200, drift__pitch=5, level=-12.8),
    fx=[fx.eq({'peak1.freq': 1200, 'peak1.gain': 6, 'peak1.q': 3.5,
               'peak2.freq': 2700, 'peak2.gain': 8, 'peak2.q': 3.5,
               'peak3.freq': 450, 'peak3.gain': -3, 'peak3.q': 1.5,
               'high.freq': 5000, 'high.gain': -6}),
        fx.chorus(mode='II', mix=0.6),
        _dim(1)],
    sends={'hall': -8},
    notes='v2. Synth "aah" choir: a 4-voice detuned saw ensemble plus pink breath noise through FIXED formants '
          '(band-pass 800 Hz with no key tracking = F1, eq bells at 1.2 kHz = F2 and 2.7 kHz = F3, highs shelved '
          'off), delayed vocal vibrato (8 ct, 5 Hz), 0.6 s attack, chorus II and a dimension side layer (~77 % wide, '
          'v1 36 %: a choir that surrounds you). Because the formants stay put while the pitch moves it reads as '
          'voices, not as a filtered synth. Range: C3-C5 (the vowel is most convincing in A3-A4). Use: choir swells '
          'on choruses/bridges, Vangelis-like sci-fi beds, layered quietly (-6 dB) over warm_pad. Tweak: cutoff '
          '600-1000 (the vowel: 600 "oh", 800 "ah", 1000 open "a"), resonance 0.2-0.6, mod.vib.amount 0-15 (vibrato, '
          'ct), noise.level 0-0.15 (breath), amp.attack 0.2-2. Sends: hall -8. Measured -18.1 LUFS (audition '
          'chords). Lush pass (v2): chorus II 0.4 -> 0.6, + dimension mode 1.'))

register(Patch(
    'synthwave/sweep_pad',
    instrument=_va(osc1__wave='saw', osc2__wave='saw', osc2__level=0.9, osc2__fine=7,
                   unison=3, unison__detune=0.3, unison__spread=0.8,
                   cutoff=1100, resonance=0.5, filter__keytrack=0.4, filter__velocity=0, filter__env=0,
                   mods=[lfo('triangle', rate=8, mode='global', id='sweep') >> ('cutoff', 1.5)],
                   amp__attack=0.3, amp__decay=1.0, amp__sustain=1.0, amp__release=1.5, amp__velocity=0.2,
                   hpf=150, drift__pitch=3, level=-9.3),
    fx=[fx.chorus(mode='II', mix=0.55), _dim(1)],
    sends={'hall': -8},
    notes='v2. Filter-sweep pad: detuned saw stack into a resonant (0.5) ladder whose cutoff is swept +-1.5 octaves '
          'around 1.1 kHz by a tempo-synced triangle LFO (one sweep up and down every 2 bars, locked to the song '
          'grid, peaks on beat 2 of each 2-bar cycle), chorus II and a dimension side layer (~72 % wide, v1 49 %). '
          'Range: C3-C5 sustained chords. Use: moving pad for intros, verses and builds; the sweep carries the '
          'energy when little else moves. Tweak: mod.sweep.amount 0-3 (depth, octaves; automate '
          '"instrument.mod.sweep.amount" to bring the sweep in), sweep period 4-32 beats (16 = 4 bars: '
          '.with_mods(vamod.lfo("triangle", rate=16, mode="global", id="sweep") >> ("cutoff", 1.5))), cutoff '
          '500-3000 (centre), resonance 0.2-0.8 (vowel-like peak). For a one-shot build set mod.sweep.amount 0 and '
          'automate "instrument.cutoff" with exp_ramp/riser instead. Sends: hall -8. Measured -17.6 LUFS (audition '
          'chords). Lush pass (v2): chorus II 0.4 -> 0.55, + dimension mode 1, hall -10 -> -8.'))

# ------------------------------------------------------------------------------------ keys/stabs

register(Patch(
    'synthwave/epiano',
    instrument=inst.dx7('E.PIANO 1', detune=6, width=0.6, brightness=-0.1, velsens=0.8, level=2.3),
    fx=[fx.chorus(mode='II', mix=0.5),
        fx.eq({'peak1.freq': 300, 'peak1.gain': -1.5, 'peak1.q': 0.8}),
        _dim(1)],
    sends={'plate': -12, 'hall': -18},
    notes='v3. THE 80s ballad keys: DX7 ROM1 "E.PIANO 1" (tine bell attack, warm body), stereo-doubled (+-3 ct), '
          'through Juno chorus II and a Dimension-D side layer - the classic chorused DX Rhodes, ~66 % wide (v2 40 '
          '%) with a solid mono centre - top slightly tamed (brightness -0.1), velocity range squeezed a little '
          '(velsens 0.8) so comping stays even. Range: C3-C6; comp chords in C4-C5 (drop2 / 3-4 note voicings), '
          'melodies up to C6. Use: verse/breakdown comping, ballad intros, counter-lines; pan it -0.2..-0.35 against '
          'an arp on the other side. Velocity matters: 70-90 = soft and round, 110+ = the barky tine. Tweak: chorus '
          'mix 0.3-0.6 ("fx.chorus.mix"), mode I for a cleaner image, brightness -0.4..0.3, velsens 0.5-1, detune '
          '0-12. Sends: plate -12 (the classic), hall -18. Measured -18.0 LUFS comping 1/8 chords (-19.8 with the '
          'audition whole-bar chords). Lush pass (v3): chorus I 0.35 -> II 0.5, + dimension mode 1, -1.5 dB at 300 '
          'Hz, plate -14 -> -12.'))

register(Patch(
    'synthwave/epiano_bright',
    instrument=inst.dx7('E.PIANO 1', detune=8, width=0.7, brightness=1.0, velsens=0.5, level=2.0),
    fx=[fx.eq({'hp.freq': 180, 'hp.slope': 24, 'low.freq': 400, 'low.gain': -3,
               'peak2.freq': 3000, 'peak2.gain': 4, 'peak2.q': 0.7}),
        fx.chorus(mode='II', mix=0.45),
        _dim(1)],
    sends={'plate': -12},
    notes='v3. Bright, cutting DX e-piano: "E.PIANO 1" with full air tilt (brightness 1 = +6 dB above 2.5 kHz), +4 '
          'dB tine presence at 3 kHz, body thinned (-3 dB low shelf at 400 Hz, 24 dB high-pass at 180 Hz), velocity '
          'pulled toward the tine (velsens 0.5), wider doubling (+-4 ct), chorus II and a dimension side layer (~68 '
          '% wide). Clearly brighter and thinner than synthwave/epiano (spectral centroid ~700 Hz vs ~440 Hz on the '
          'same comping), so it sits on top of pads and bass instead of inside them. Range: C4-C6. Use: '
          'pop-synthwave chord stabs on the off-beats, bright arps/riffs, a part that must cut through a full '
          'chorus; for warm ballad comping use synthwave/epiano. Tweak: brightness 0.3-1, eq peak2.gain 0-6 '
          '("fx.eq.peak2.gain"), velsens 0.3-0.8, chorus mix 0.2-0.6, velocity 110+ for the bark. Sends: plate -12 '
          '(echo -16 for riffs). Measured -17.7 LUFS comping 1/8 chords (-20.0 on the audition whole-bar chords, '
          '-16.6 on 1/16 stabs in G3-G5). Lush pass (v3): chorus II 0.35 -> 0.45, + dimension mode 1, plate -14 -> '
          '-12.'))

register(Patch(
    'synthwave/dx_bells',
    instrument=inst.dx7('TUB BELLS', detune=5, width=0.8, brightness=-0.25, level=7.0),
    fx=[fx.chorus(mode='I', mix=0.25), _dim(1)],
    sends={'hall': -10, 'echo': -14},
    notes='v3. DX7 ROM1 "TUB BELLS": inharmonic FM tubular bell with a long ring, stereo-doubled, glassy top tamed '
          '(brightness -0.25), gentle chorus and a dimension side layer (~70 % wide: chimes that float around the '
          'lead). Range: C4-C6 (C5-C6 = glassy chimes, C4 = real tubular bells); single notes or sparse two-note '
          'intervals (it rings long: leave space). Use: melodic hooks doubled with the lead an octave up, '
          'intro/outro motifs, sparse answers in a verse, accents on section downbeats. Tweak: brightness -0.5..0 '
          '(lower = softer), detune 0-10, velsens 0.5-1. Sends: hall -10, echo -14 (the dotted-8th repeats sparkle). '
          'Measured -19.2 LUFS on a C5-C6 bell melody (-16.3 on the audition phrase in C4). Lush pass (v3): + '
          'dimension mode 1, hall -12 -> -10, + echo -14.'))

register(Patch(
    'synthwave/marimba',
    instrument=inst.dx7('MARIMBA', detune=4, width=0.6, transpose=12, level=-1.6),
    fx=[_dim(2)],
    sends={'plate': -14, 'echo': -12},
    notes='v4. DX7 ROM1 "MARIMBA": woody mallet pluck with a short resonant decay, lightly doubled. The ROM voice '
          'runs its carriers at frequency ratio 0.5 (it sounds an octave BELOW the key on a real DX7); this patch '
          'adds transpose=12 so the written note is the sounding note. Range: A3-C6 sounding (C4-C5 sweet spot); '
          'below A3 it turns into low-mid mud that fights the bass. Use: plucky 1/16 arpeggios (Stranger Things / '
          'sequenced 80s feel), counter-melodies, poly-rhythmic ostinatos; pan it (+-0.3) against the arp synth. '
          'Tweak: velsens 0.5-1 (mallet hardness), brightness -0.3..0.4, detune 0-8, transpose 0 for the original '
          'octave-down woody register. Sends: plate -14, echo -12 (dotted-1/8 repeats). Measured -18.3 LUFS on the '
          '1/16 arp (audition with --notes arp; the default audition phrase reads -23 because it is sparse). Lush '
          'pass (v4): + dimension mode 2 (~30 % wide; v3 was nearly mono), plate -16 -> -14, + echo -12.'))

register(Patch(
    'synthwave/brass_stab',
    instrument=_va(osc1__wave='saw', osc2__wave='saw', osc2__level=0.9, osc2__fine=8,
                   unison=3, unison__detune=0.2, unison__spread=0.6,
                   filter__type='lp12', cutoff=700, resonance=0.15, filter__keytrack=0.5, filter__velocity=1.0,
                   filter__env=2.5, fenv__attack=0.06, fenv__decay=0.45, fenv__sustain=0.45, fenv__release=0.3,
                   amp__attack=0.015, amp__decay=0.5, amp__sustain=0.85, amp__release=0.25, amp__velocity=0.5,
                   hpf=120, drift__pitch=3, level=-7.7),
    fx=[fx.saturator(mode='tape', drive=4, mix=0.5), _hp(130), fx.chorus(mode='II', mix=0.4), _dim(1)],
    sends={'hall': -12, 'plate': -14},
    notes='v2. Analog brass (OB-Xa / Jupiter-8 style): detuned saw stack through the 12 dB (SEM-like) filter with a '
          'fast 60 ms filter "blat" that settles, velocity opens the filter (up to 1 oct), light tape saturation, '
          'chorus II and a dimension side layer (a wide brass section). Range: C3-C5 chords/fifths/octaves. Use: '
          'short stabs on the off-beats or syncopated hits, and held brass swells (longer notes sustain at 85%). '
          'Tweak: filter.env 1.5-4 (blat), fenv.decay 0.2-0.8, cutoff 400-1500, fenv.attack 0.02-0.15 (slower = '
          'swell), velocity 80-127 for dynamics. Sends: hall -12, plate -14. Measured -19.9 LUFS playing 1/16 stabs '
          '(-16.0 on the audition whole-bar chords: pull gain_db -3 for long held brass). Lush pass (v2): chorus I '
          '0.25 -> II 0.4, + dimension mode 1 (~47 % wide, v1 20 %), hall -14 -> -12, + plate -14.'))

register(Patch(
    'synthwave/dx_brass',
    instrument=inst.dx7('BRASS 1', detune=7, width=0.7, brightness=-0.15, velsens=0.8, level=1.4),
    fx=[_hp(150), fx.chorus(mode='I', mix=0.3), _dim(1)],
    sends={'hall': -12},
    notes='v3. DX7 ROM1 "BRASS 1": the classic 80s FM brass section (bright bite that settles into a horn-like '
          'body), doubled +-3.5 ct, brightness -0.15 against fizz, high-passed at 150 Hz: the voice has a carrier at '
          'frequency ratio 0.5 (a real sub-octave body, authentic to the ROM, strongest in the attack of short '
          'stabs) that muddies a mix below ~150 Hz. Range: C3-C5, best as 3-4 note chords from G3 up (lower chords '
          'push that sub-octave into the bass). Use: fanfare hits, chord stabs, pop-brass riffs; layer under '
          'synthwave/brass_stab for a hybrid analog+FM section. Tweak: velsens 0.5-1 (velocity = bite), brightness '
          '-0.4..0.2, detune 0-12, modwheel 0.1-0.3 (vibrato for held notes). Sends: hall -12. Measured -18.2 LUFS '
          '(audition chords, peaks -4.1 dBFS); short chord stabs on the 8ths in G3-G5 -18.0 LUFS with peaks -2.9 '
          'dBFS (the FM bite), so give stab parts gain_db -2 when several stabs stack. Lush pass (v3): + chorus I '
          '0.3 and dimension mode 1 (~53 % wide, v2 34 %), hall -14 -> -12.'))

register(Patch(
    'synthwave/poly_stab',
    instrument=_va(osc1__wave='saw', osc2__wave='square', osc2__level=0.6, osc2__fine=5,
                   unison=3, unison__detune=0.35, unison__spread=0.8,
                   cutoff=1000, resonance=0.25, filter__keytrack=0.5, filter__velocity=1.0, filter__env=3.0,
                   fenv__attack=0.001, fenv__decay=0.18, fenv__sustain=0.15, fenv__release=0.15,
                   amp__attack=0.002, amp__decay=0.3, amp__sustain=0.5, amp__release=0.2, amp__velocity=0.5,
                   hpf=150, drift__pitch=2, level=-2),
    fx=[_hp(150), fx.chorus(mode='II', mix=0.45), _dim(1)],
    sends={'plate': -12, 'echo': -14},
    notes='v2. Short bright poly stab: saw + square unison stack, snappy 3-octave filter envelope (180 ms) over a 1 '
          'kHz ladder, 0.2 s release, chorus II and a dimension side layer; the note length sets the stab length '
          '(sustain 50%). Range: C4-C6 triads/7ths (C4-G5 is the sweet spot). Use: syncopated chord stabs (1/16-1/8 '
          'notes), off-beat "house" stabs, chord hits into drops; the dotted-1/8 echo and the plate make the space. '
          'Tweak: filter.env 2-4.5 (snap), fenv.decay 0.08-0.4, cutoff 500-2500, resonance 0.1-0.5, amp.release '
          '0.1-0.5. Sends: plate -12, echo -14. Measured -20.0 LUFS playing 1/16 stabs with peaks -2 dBFS (short '
          'hits read low in LUFS; they sound as loud as the -18 pads); -18.2 on the audition whole-bar chords. Lush '
          'pass (v2): chorus I 0.3 -> II 0.45, + dimension mode 1 (~58 % wide, v1 37 %), plate -14 -> -12, '
          '+ echo -14.'))

register(Patch(
    'synthwave/organ',
    instrument=_va(osc1__wave='sine', osc2__wave='sine', osc2__semi=7, osc2__level=0.6,
                   sub__level=0.45, sub__octave=-1,
                   filter__type='lp12', cutoff=4500, resonance=0.0, filter__keytrack=0.5, filter__velocity=0,
                   filter__env=0, filter__drive=0.3,
                   amp__attack=0.004, amp__decay=0.1, amp__sustain=1.0, amp__release=0.06, amp__velocity=0,
                   hpf=60, drift__pitch=1, level=-14.2),
    fx=[fx.saturator(mode='tube', drive=3, mix=0.35, tone=-1),
        _hp(60),
        fx.chorus(mode='II', mix=0.45),
        fx.tremolo(name='leslie', rate=6.2, depth=0.18, stereo=180),
        _dim(1)],
    sends={'hall': -14},
    notes='v2. Drawbar-style synth organ ("888" registration): 16\' (sub square), 5 1/3\' (sine a fifth up) and 8\' '
          '(sine) with organ-gate envelope (4 ms on, 60 ms off, no velocity), a touch of tube drive, chorus II, a '
          'fast rotary-style stereo tremolo (6.2 Hz, named "leslie") and a dimension side layer (the 16\' stays '
          'centred below 150 Hz). Range: C3-C5 chords (the 16\' adds weight: keep the left hand above C3). Use: '
          'gospel-pop / Italo organ beds, bridge colour, stabbed off-beat chords. Tweak: osc2.level 0-1 and '
          'sub.level 0-0.8 (the drawbars), cutoff 2500-8000, "fx.leslie.rate" 0.8 (slow rotor) .. 6.5 (fast; '
          'automate for the classic ramp), saturator drive 0-9. Sends: hall -14. Measured -17.8 LUFS (audition '
          'chords). Lush pass (v2): chorus I 0.4 -> II 0.45, + dimension mode 1 (~37 % wide, v1 23 %), '
          'hall -16 -> -14.'))
