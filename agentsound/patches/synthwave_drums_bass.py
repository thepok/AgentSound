"""Synthwave sound library: drum kits, basses and the drum-group / gated-reverb buses.

Patches registered here (v3):
  drum kits  synthwave/drums_outrun drums_linn drums_808 drums_909 drums_dark
  basses     synthwave/octave_bass rolling_bass sub_bass dx_bass moog_bass dark_bass pluck_bass
  buses      bus/drums (drum group glue) bus/gated (80s gated-reverb return)

Level calibration: every instrument patch at gain_db=0 lands at -18 LUFS (+-0.5) on its own track when it
plays the standard audition material (`python -m agentsound audition <name>`: drums = 4-on-the-floor groove
with 8th hats at 100 BPM, basses = 8th-note octave line A1-A2 over Am F C G). The measured value is quoted in
each patch's notes. Calibration is done with the instrument's `level` and the last insert's output, so
gain_db stays 0 and is the composer's fader.

Drum kits carry their processing (eq -> compressor -> saturator as a soft clipper). The kit `level` param
drives that chain: change the loudness of a kit with the track's gain_db, and change `level` only to make the
kit hit its saturation harder (+) or softer (-).

v2 (review): dark_bass rebuilt for a sustained mid growl; bus/gated gets an output eq for a brighter burst;
kit notes corrected on how to tame the low end (the in-kit compressor/saturator absorbs kick.* level changes).
v3: dx_bass level re-matched to the DX7 engine's phrase-based autolevel (same -18.3 LUFS).
v4 (lush pass): the kits were re-calibrated (they had drifted to -19.6..-20.2 LUFS after engine changes; now -18.0 again,
via the last saturator's output) and spread like a mixed 80s drum machine: wider claps (clap.width 0.7), wide crash and
ride overheads (0.9 / 0.7), toms spread high-left to floor-right (0.8); kick, snare and the basses stay mono in the centre.
"""

from . import Patch, fx, inst, register

VERSION = 4

_GATED_HOWTO = (
    "Gated snare: the bus/gated gate opens at -16 dBFS on the bus input, i.e. on this kit's snare/clap/toms at "
    "a send of -8..-4 dB, not on kick or hats. For the cleanest result (and always with click-heavy kicks) play "
    "the snare/clap/toms on a second track with the same patch and send only that one: "
    "`gate = s.gated(gain_db=0)` (the return sets the effect level: -6 subtle .. +4 huge 80s), `sn = s.track('snare', '{name}', "
    "sends={{gate: -6}})`, and drop the main kit's own gated send with "
    "patches.get('{name}').with_mix(sends={{'gated': None}}).")

_SUB_TIP = (
    " Low end: the kick sits at 41-55 Hz, so a mix will read 'sub high' until other parts fill the top. The "
    "kit's own compressor/saturator absorbs part of any kick.level/kick.sub change (kick.level -3 moves the "
    "outrun kit -1.2 dB, the dark kit only -0.4 dB), so trim the lows AFTER the chain: "
    "patches.get(...).with_fx(fx.eq({'low.freq': 60, 'low.gain': -3})) (measured in 8-bar test mixes: mix sub "
    "-1.2..-2 dB), or shorten kick.decay.")

# ----------------------------------------------------------------------------------- drum kits

register(Patch(
    'synthwave/drums_outrun',
    instrument=inst.drums({
        'kit': 'synthwave', 'level': 9, 'velocity': 0.5, 'humanize': 0.15,
        'kick.decay': 0.4, 'kick.punch': 0.7, 'kick.pitchenv': 24, 'kick.pitchdecay': 0.04,
        'kick.click': 0.3, 'kick.drive': 0.35, 'kick.sub': 0.15, 'kick.tone': 0.5,
        'snare.tune': 190, 'snare.decay': 0.36, 'snare.tone': 0.6, 'snare.snappy': 0.75,
        'snare.bodydecay': 0.55, 'snare.hpf': 600, 'snare.lpf': 10000,
        'hat.level': -3, 'hat.decay': 0.05, 'hat.tone': 0.55, 'hat.noise': 0.45,
        'clap.width': 0.7, 'crash.width': 0.9, 'ride.width': 0.7, 'tom.spread': 0.8,
    }),
    fx=[fx.eq({'hp.freq': 30, 'peak1.freq': 400, 'peak1.gain': -2.5, 'peak1.q': 1.0}),
        fx.compressor(threshold=-14, ratio=3, attack=15, release=90, knee=6),
        fx.saturator(mode='tape', drive=6, output=2.5)],
    sends={'gated': -6},
    notes=(
        "Outrun / nightdrive kit (Kavinsky, Lazerhawk, Miami Nights 1984): tight punchy kick (~50 Hz, 0.4 s, "
        "beater click + light drive), fat 190 Hz snare built to feed the gated reverb, crisp short hats, "
        "Simmons-style pitch-drop toms, long crash. Chain: eq (-2.5 dB at 400 Hz) -> glue compressor (15 ms "
        "attack keeps the punch) -> tape soft-clip. v4: re-calibrated (+2 dB) and spread (wide claps, crash overheads, "
        "toms across the field). Measured -18.1 LUFS (track; audition mix incl. the gated return -17.3), sample peak "
        "-1.9 dBFS. Use 100-120 BPM, four-on-the-floor kick, snare/clap on 2 and 4, 8th "
        "or 16th hats (16th hats at 118 BPM measure -17.8). Tweak: kick.tune to the key root (E1 41.2, F1 43.7, F#1 46.2, "
        "G1 49, A1 55 Hz), kick.decay 0.3-0.6, kick.drive 0.2-0.6 (more = more audible on small speakers), "
        "snare.decay 0.25-0.5, snare.tune 170-220, hat.decay 0.03-0.08, hat.level -6..0, clap.level -3..0 to layer "
        "the clap under the snare in choruses. Sends: gated -6 (default), optional plate -14 for air. Sidechain "
        "the bass/pads from it with s.sidechain(..., key=kit, pitches='kick'). " + _GATED_HOWTO.format(
            name='synthwave/drums_outrun') + _SUB_TIP)))

register(Patch(
    'synthwave/drums_linn',
    instrument=inst.drums({'kit': 'linn', 'level': 9, 'velocity': 0.6, 'humanize': 0.2, 'hat.level': -2,
                           'clap.width': 0.7, 'crash.width': 0.9, 'ride.width': 0.7, 'tom.spread': 0.8}),
    fx=[fx.eq({'hp.freq': 30, 'peak1.freq': 350, 'peak1.gain': -1.5, 'lp.freq': 12500}),
        fx.compressor(threshold=-14, ratio=4, attack=10, release=100, knee=6),
        fx.saturator(mode='tape', drive=5, output=3.6)],
    sends={'plate': -10},
    notes=(
        "LinnDrum-style 80s pop kit (a-ha, Tears for Fears, Jan Hammer): short thuddy acoustic-sample kick with a "
        "beater click (62 Hz, 0.35 s), woody 3-mode snare, sampled-noise hats, 5-burst claps, acoustic toms; "
        "12.5 kHz low-pass for the LinnDrum's 28 kHz sampler bandwidth, 80s console bus compression (4:1, "
        "10 ms) and tape. v4: re-calibrated (+2.2 dB) and spread (claps, crash/ride, toms). Measured -18.0 LUFS (track), "
        "sample peak -0.7 dBFS. Use for retrowave pop / ballads "
        "100-125 BPM; it shines with busy 16th hats, claps on 2/4, tambourine (54) and cowbell (56) accents. "
        "Tweak: kick.tune 55-70, kick.decay 0.25-0.45, snare.tune 180-230, snare.decay 0.25-0.45, hat.level "
        "-5..0, velocity 0.4-0.8 (it is the most dynamic kit). Sends: plate -10 (default: the 80s plate on the "
        "whole kit). Its clicky kick opens a gate, so for a gated snare use a separate snare track: "
        + _GATED_HOWTO.format(name='synthwave/drums_linn') + _SUB_TIP)))

register(Patch(
    'synthwave/drums_808',
    instrument=inst.drums({'kit': '808', 'level': 9, 'velocity': 0.6, 'humanize': 0.15,
                           'kick.decay': 0.9, 'hat.level': -3.5,
                           'clap.width': 0.7, 'crash.width': 0.9, 'ride.width': 0.7, 'tom.spread': 0.8}),
    fx=[fx.eq({'hp.freq': 25, 'lp.freq': 11000}),
        fx.compressor(threshold=-16, ratio=2.5, attack=20, release=120, knee=8),
        fx.saturator(mode='tube', drive=4), fx.saturator(mode='tape', drive=5, output=2.9)],
    sends={'plate': -12, 'gated': -8},
    notes=(
        "TR-808 kit for dreamwave / chillsynth (FM-84, Timecop1983, Home): round boomy kick (48 Hz, 0.9 s, pure "
        "sine sweep), snappy 238 Hz snare, the classic clap, clangy metallic hats and cowbell; softened top "
        "(11 kHz low-pass), tube warmth, gentle glue and tape. v4: re-calibrated (+1.6 dB) and spread (claps, "
        "cymbals, toms). Measured -18.1 LUFS (track), sample peak -2.0 dBFS. Use 80-100 BPM, half-time (kick on 1 and the 'and' of 2/3, snare/clap on 3) or laid-back 4/4 with "
        "track.groove('laidback'); layer clap + snare for the backbeat. Tweak: kick.tune to the key root (it is "
        "a pitched boom: A1 55, G1 49, F1 43.7 Hz), kick.decay 0.5-1.5 (shorter at faster tempos; long tails "
        "fight the bass: sidechain it), snare.snappy 0.4-0.8, hat.tone 0.3-0.6, hat.level -6..-2. Sends: plate "
        "-12 and gated -8 (default), or hall -14 for a dreamier backbeat. " + _GATED_HOWTO.format(
            name='synthwave/drums_808') + _SUB_TIP)))

register(Patch(
    'synthwave/drums_909',
    instrument=inst.drums({'kit': '909', 'level': 9, 'velocity': 0.55, 'humanize': 0.1,
                           'kick.decay': 0.5, 'kick.punch': 0.7, 'snare.decay': 0.3, 'hat.level': -3.5,
                           'clap.width': 0.7, 'crash.width': 0.9, 'ride.width': 0.7, 'tom.spread': 0.8}),
    fx=[fx.eq({'hp.freq': 30, 'peak1.freq': 380, 'peak1.gain': -2, 'peak1.q': 1.0}),
        fx.compressor(threshold=-14, ratio=4, attack=8, release=70, knee=6),
        fx.saturator(mode='tape', drive=7, output=2.4)],
    notes=(
        "TR-909 kit, driving: punchy clicky kick (53 Hz, 0.5 s, held-then-dropped envelope), bright tuned snare, "
        "sizzling 909 hats and a long open hat; firm 4:1 compression and hot tape for a pumping, forward kit. "
        "v4: re-calibrated (+1.6 dB) and spread (claps, cymbals, toms). Measured -18.1 LUFS (track), sample peak "
        "-2.4 dBFS. Use for driving outrun / synth-pop at 110-128 BPM: "
        "4-on-the-floor, 16th hats with off-beat open hats, claps on 2/4. Tweak: kick.tune 45-60, kick.decay "
        "0.3-0.7, kick.click 0.3-0.7, snare.decay 0.2-0.4, hat.opendecay 0.3-0.6, hat.level -6..0. No default "
        "sends (plate -14 suits it). Its click opens a gate, so for a gated snare use a separate snare track: "
        + _GATED_HOWTO.format(name='synthwave/drums_909') + _SUB_TIP)))

register(Patch(
    'synthwave/drums_dark',
    instrument=inst.drums({
        'kit': 'modern', 'level': 7, 'velocity': 0.5, 'humanize': 0.1,
        'kick.level': 1.5, 'kick.decay': 0.55, 'kick.punch': 0.85, 'kick.pitchenv': 36, 'kick.pitchdecay': 0.035,
        'kick.click': 0.5, 'kick.drive': 0.85, 'kick.sub': 0.3, 'kick.tone': 0.65,
        'snare.tune': 180, 'snare.decay': 0.4, 'snare.tone': 0.65, 'snare.snappy': 0.8, 'snare.hpf': 700,
        'hat.level': -3,
        'clap.width': 0.7, 'crash.width': 0.9, 'ride.width': 0.7, 'tom.spread': 0.8,
    }),
    fx=[fx.saturator(mode='tube', drive=12),
        fx.eq({'hp.freq': 30, 'peak1.freq': 450, 'peak1.gain': -3, 'peak1.q': 1.2, 'lp.freq': 14000}),
        fx.compressor(threshold=-16, ratio=6, attack=5, release=60, knee=6),
        fx.saturator(mode='tape', drive=4, output=4.4)],
    notes=(
        "Darksynth kit (Perturbator, Carpenter Brut, Dance with the Dead): hard distorted kick (deep 46 Hz sub, "
        "36-semitone zap, heavy drive), crunchy fat snare, the whole kit through tube distortion -> 450 Hz "
        "scoop -> 6:1 slam compression -> tape. v4: re-calibrated (+1.7 dB) and spread (claps, cymbals, toms). "
        "Measured -18.1 LUFS (track), sample peak -1.1 dBFS. Use 110-140 "
        "BPM: four-on-the-floor or half-time breakdowns, snare/clap on 2/4 (or 3), 16th hats. Tweak: kick.tune "
        "to the key root (41-55 Hz), kick.drive 0.6-1, kick.decay 0.4-0.8, first saturator drive 6-18 dB "
        "(patch.but_fx(0, drive=...)), snare.decay 0.3-0.6. No default sends; for the huge darksynth snare use "
        "a separate snare track into bus/gated (the distorted kick would open the gate on a whole-kit send): "
        + _GATED_HOWTO.format(name='synthwave/drums_dark') + _SUB_TIP)))

# ---------------------------------------------------------------------------------------- basses

register(Patch(
    'synthwave/octave_bass',
    instrument=inst.va({
        'osc1.wave': 'saw', 'osc2.wave': 'saw', 'osc2.level': 0.6, 'osc2.fine': 7,
        'osc.retrig': 'on', 'mode': 'mono',
        'filter.type': 'ladder', 'cutoff': 800, 'resonance': 0.3, 'filter.drive': 0.35,
        'filter.keytrack': 0.5, 'filter.env': 3.0, 'filter.velocity': 0.5,
        'fenv.attack': 0.001, 'fenv.decay': 0.16, 'fenv.sustain': 0.15, 'fenv.release': 0.06,
        'amp.attack': 0.001, 'amp.decay': 0.3, 'amp.sustain': 0.6, 'amp.release': 0.04,
        'drift.pitch': 1, 'level': 3,
    }),
    fx=[fx.saturator(mode='tape', drive=5), fx.eq({'hp.freq': 30})],
    notes=(
        "THE synthwave bass: 8th-note root/octave pulse (bassline(prog, 'octave', rate='1/8')). Two saws 7 ct "
        "apart, retriggered oscillators for an identical punchy attack, 24 dB ladder with a snappy 3-octave "
        "filter pluck (decay 0.16 s), mono (every note retriggers), tape saturation for small-speaker "
        "harmonics. Measured -18.3 LUFS (8ths at 100 BPM; 16ths ~ -17.4), true peak -5.1 dBTP. Play roots "
        "E1-A2 (the octave jumps to E2-A3). Tweak: cutoff 500-1500 (Hz at C4; the filter key-tracks at 0.5 so "
        "A1 sits at ~0.4x that), filter.env 2-4 oct (pluck amount), fenv.decay 0.1-0.3, resonance 0.1-0.5, "
        "amp.sustain 0.3-0.8 (tightness), filter.velocity 0-1 (accents brighter). Automate "
        "'instrument.cutoff' for filter builds. No reverb sends; always sidechain it from the kick "
        "(depth 6-10 dB, release ~60% of a beat).")))

register(Patch(
    'synthwave/rolling_bass',
    instrument=inst.va({
        'osc1.wave': 'saw', 'osc2.wave': 'saw', 'osc2.level': 0.3, 'osc2.semi': 12, 'osc2.fine': 4,
        'osc.retrig': 'on', 'mode': 'mono',
        'filter.type': 'ladder', 'cutoff': 700, 'resonance': 0.25, 'filter.drive': 0.3,
        'filter.keytrack': 0.5, 'filter.env': 3.5, 'filter.velocity': 0.8,
        'fenv.attack': 0.001, 'fenv.decay': 0.07, 'fenv.sustain': 0.1, 'fenv.release': 0.03,
        'amp.attack': 0.001, 'amp.decay': 0.12, 'amp.sustain': 0.4, 'amp.release': 0.025,
        'drift.pitch': 1, 'level': 8,
    }),
    fx=[fx.saturator(mode='tape', drive=5), fx.eq({'hp.freq': 30})],
    notes=(
        "Rolling 16th-note bass (Mitch Murder, Lazerhawk, Dance with the Dead): saw plus a quiet saw an octave "
        "up for definition in fast lines, very short filter blip (70 ms) and amp decay so 16ths stay separated "
        "at 110-130 BPM, velocity-to-cutoff 0.8 so accents bite. Measured -18.1 LUFS (8ths at 100 BPM; 16ths "
        "at 115 BPM -17.1), true peak -4.6 dBTP. Play bassline(prog, 'octave' | 'pulse' | 'gallop', "
        "rate='1/16') or pattern='R.ro rRor' with accents, roots E1-A2. Tweak: cutoff 400-1200 (at C4, "
        "key-tracked 0.5), fenv.decay 0.05-0.12, amp.decay 0.08-0.2, filter.env 2.5-4.5, osc2.level 0-0.5 "
        "(octave bite). Sidechain from the kick (depth 6-10 dB); no reverb.")))

register(Patch(
    'synthwave/sub_bass',
    instrument=inst.va({
        'osc1.wave': 'sine', 'osc2.wave': 'triangle', 'osc2.level': 0.25,
        'mode': 'mono', 'filter.type': 'lp12', 'cutoff': 700, 'resonance': 0.0, 'filter.drive': 0.0,
        'filter.keytrack': 0.5, 'filter.env': 0.0, 'filter.velocity': 0.0,
        'amp.attack': 0.004, 'amp.decay': 0.5, 'amp.sustain': 1.0, 'amp.release': 0.08, 'amp.velocity': 0.2,
        'drift.pitch': 0, 'drift.cutoff': 0, 'level': -4.5,
    }),
    fx=[fx.eq({'hp.freq': 25})],
    notes=(
        "Clean sub layer: sine plus a little triangle (faint odd harmonics so it is still traceable on small "
        "speakers), free-running oscillators with a 4 ms attack and mono retrigger (no clicks, measured "
        "smooth), no filter movement, no drift. Measured -18.1 LUFS (8ths at 100 BPM; held roots -17.5), true "
        "peak -12 dBTP. Use under a mid/top bass (pluck_bass, dx_bass, octave_bass with an eq hp.freq "
        "100-150 on that layer) or alone for dreamwave ballads; play roots E1-A2 (below E1 it is felt, not "
        "heard). Tweak: osc2.level 0-0.5 (harmonics), amp.release 0.05-0.3, glide 0.03-0.1 for slides. Keep "
        "it mono, no sends, sidechain it harder than the other layers (depth 8-14 dB).")))

register(Patch(
    'synthwave/dx_bass',
    instrument=inst.dx7('BASS 1', {'polyphony': 1, 'transpose': 12, 'level': 4.4}),
    fx=[fx.eq({'hp.freq': 30})],
    notes=(
        "DX7 ROM 'BASS 1', the 80s FM slap/funk bass (the synth-pop workhorse): woody attack, metallic twang "
        "around 1 kHz that follows velocity (velsens 1 = authentic; accents get brighter, not just louder). "
        "BASS 1's carrier sits an octave below the key, so the patch transposes +12: play it in the same "
        "register as the other basses, roots E1-A2, lines up to A3. Mono (polyphony 1, 4 ms steal fade) "
        "keeps fast lines clean. Measured -18.3 LUFS (8ths at 100 BPM), true peak -8.3 dBTP. Use for funky "
        "retrowave-pop lines: syncopated 16ths, octave pops, walk/fifth styles, pattern='R.oR .rOr'. Tweak: "
        "velsens 0.5-1 (0.6 evens a sequencer part), brightness -0.3..0.3, detune 0 (keep the bass mono). "
        "Layer synthwave/sub_bass underneath for modern weight. No reverb; sidechain from the kick.")))

register(Patch(
    'synthwave/moog_bass',
    instrument=inst.va({
        'osc1.wave': 'saw', 'osc2.wave': 'saw', 'osc2.level': 0.8, 'osc2.fine': -6,
        'mode': 'legato', 'glide': 0.04,
        'filter.type': 'ladder', 'cutoff': 600, 'resonance': 0.3, 'filter.drive': 0.55,
        'filter.keytrack': 0.4, 'filter.env': 2.5, 'filter.velocity': 0.5,
        'fenv.attack': 0.002, 'fenv.decay': 0.45, 'fenv.sustain': 0.35, 'fenv.release': 0.15,
        'amp.attack': 0.002, 'amp.decay': 0.8, 'amp.sustain': 0.9, 'amp.release': 0.12,
        'drift.pitch': 2, 'level': 0.5,
    }),
    fx=[fx.saturator(mode='tube', drive=3), fx.eq({'hp.freq': 28})],
    notes=(
        "Minimoog-style fat bass for long notes: two saws 6 ct apart with the mixer overdriving a 24 dB "
        "ladder (filter.drive 0.55), a slow 'bwow' filter envelope (2.5 oct, 0.45 s, sustain 0.35) that "
        "blooms and settles on held notes, legato mode with a 40 ms glide on overlapping notes, tube warmth. "
        "Measured -18.4 LUFS (8ths at 100 BPM; held whole-bar roots -17.0), true peak -6.7 dBTP. Use in dreamwave / "
        "ballads / soundtrack pieces: whole and half notes, pedal tones, slow walking lines "
        "(bassline(prog, 'root' | 'walk')), overlapping notes (clip.legato(0.05)) for slides. Play "
        "roots E1-A2. Tweak: cutoff 300-1200 (at C4, key-tracked 0.4), filter.env 1.5-4, fenv.decay 0.3-1, "
        "resonance 0.1-0.5, filter.drive 0.3-0.9, glide 0-0.15. No reverb; light sidechain (depth 4-8 dB).")))

register(Patch(
    'synthwave/dark_bass',
    instrument=inst.va({
        'osc1.wave': 'saw', 'osc2.wave': 'saw', 'osc2.level': 0.8, 'osc2.fine': 14,
        'osc.retrig': 'on', 'mode': 'mono',
        'filter.type': 'ladder', 'cutoff': 1800, 'resonance': 0.45, 'filter.drive': 0.8,
        'filter.keytrack': 0.5, 'filter.env': 2.0, 'filter.velocity': 0.5,
        'fenv.attack': 0.002, 'fenv.decay': 0.3, 'fenv.sustain': 0.5, 'fenv.release': 0.1,
        'amp.attack': 0.002, 'amp.decay': 0.4, 'amp.sustain': 0.8, 'amp.release': 0.06,
        'drift.pitch': 2, 'level': 1.2,
    }),
    fx=[fx.saturator(mode='tube', drive=18),
        fx.eq({'hp.freq': 30, 'peak1.freq': 300, 'peak1.gain': -3, 'peak2.freq': 1000, 'peak2.gain': 3,
               'lp.freq': 7000})],
    notes=(
        "Darksynth growl bass (Perturbator, Carpenter Brut): two saws 14 ct apart for a beating, snarling "
        "tone, hot ladder drive and resonance with a half-open sustained filter (the growl stays on held "
        "notes instead of dying into a sub thump), then 18 dB of tube distortion, a 300 Hz mud cut, a +3 dB "
        "1 kHz growl lift and a 7 kHz fizz low-pass: dense sustained harmonics up to ~2 kHz, so it reads on "
        "small speakers and sounds clearly nastier than octave_bass (v2: 6-10 dB more 0.8-2.5 kHz than v1). "
        "Measured -18.4 LUFS (8ths at 100 BPM), true peak -6.6 dBTP. Use in "
        "darksynth at 110-140 BPM: 8th/16th root pulses, octave riffs, phrygian bII moves, roots E1-A2. "
        "Tweak: cutoff 900-2500 (at C4, key-tracked 0.5; lower = rounder), resonance 0.2-0.6, saturator drive 8-24 "
        "(but_fx('saturator', drive=...)), osc2.fine 8-25 (beating), a rhythmic wobble .with_mods(vamod.lfo('sine', "
        "rate='1/8', mode='global') >> ('cutoff', 1.0)) (0.5-1.5 octaves, rate 1/8-1/4). For a clean deep sub under it layer synthwave/sub_bass and "
        "raise this patch's eq hp.freq to 80-100. No reverb; sidechain from the kick (depth 8-12 dB).")))

register(Patch(
    'synthwave/pluck_bass',
    instrument=inst.va({
        'osc1.wave': 'square', 'osc1.pw': 0.3, 'osc2.wave': 'square', 'osc2.level': 0.5, 'osc2.fine': 6,
        'osc.retrig': 'on', 'mode': 'mono',
        'filter.type': 'ladder', 'cutoff': 400, 'resonance': 0.35, 'filter.drive': 0.3,
        'filter.keytrack': 0.5, 'filter.env': 4.0, 'filter.velocity': 0.8,
        'fenv.attack': 0.001, 'fenv.decay': 0.15, 'fenv.sustain': 0.0, 'fenv.release': 0.1,
        'amp.attack': 0.001, 'amp.decay': 0.5, 'amp.sustain': 0.0, 'amp.release': 0.1,
        'drift.pitch': 1, 'level': 7,
    }),
    fx=[fx.saturator(mode='tape', drive=4), fx.eq({'hp.freq': 30})],
    notes=(
        "Plucked pulse bass: 30 % pulse + square (hollow, woody), a big fast 4-octave resonant filter pluck and "
        "a percussive amp envelope that decays to silence (0.5 s), so it never smears. Measured -18.0 LUFS "
        "(8ths at 100 BPM), true peak -3.1 dBTP (plucks peak high for their loudness). Use for syncopated "
        "retro-pop and dreamwave lines, off-beat and 'gallop' patterns, bass arps, melodic fills E1-A3. "
        "Tweak: cutoff 250-800 (at C4, key-tracked 0.5), filter.env 3-5 (pluck), fenv.decay 0.08-0.25, "
        "resonance 0.2-0.6 (quack), amp.decay 0.25-0.8 (length), osc1.pw 0.15-0.5. Pair with "
        "synthwave/sub_bass for weight. No reverb (a short echo send -18 on fills is fine); sidechain from the "
        "kick.")))

# ------------------------------------------------------------------------------------------ buses

register(Patch(
    'bus/drums',
    fx=[fx.compressor(threshold=-12, ratio=3, attack=20, release=100, knee=6, keyhp=80, makeup=2),
        fx.saturator(mode='tape', drive=3),
        fx.eq({'hp.freq': 25, 'peak1.freq': 350, 'peak1.gain': -1, 'peak1.q': 0.8,
               'high.freq': 10000, 'high.gain': 1})],
    notes=(
        "Drum group glue for several drum tracks (kit + separate snare/perc tracks): 3:1 bus compressor with a "
        "20 ms attack (transients pass, the body is glued), 100 ms release and an 80 Hz key high-pass so the "
        "kick does not pump the group, +2 dB makeup, tape soft-clip, then a 25 Hz high-pass, -1 dB at 350 Hz "
        "and +1 dB air at 10 kHz. With two kit tracks at -18 LUFS it takes about 2 dB off the peaks at equal "
        "loudness (measured: -17.5 LUFS / -0.3 dBFS peak in -> -17.3 LUFS / -2.4 dBFS out). Use: "
        "drums = s.bus('drums', patches.get('bus/drums')); kit.to(drums); snare.to(drums). Reverb sends stay "
        "on the drum tracks (post-fader). Tweak: but_fx('compressor', threshold=-18..-8, ratio=2..4), "
        "but_fx('saturator', drive=0..6).")))

register(Patch(
    'bus/gated',
    fx=[fx.eq({'hp.freq': 200, 'hp.slope': 24, 'peak3.freq': 3800, 'peak3.gain': -9, 'peak3.q': 0.9,
               'lp.freq': 7000}),
        fx.gatedreverb(mix=1.0, threshold=-16, hold=280, release=25, predelay=8, size=0.4, decay=3.0,
                       tone=0.7, lowcut=200, width=1.2),
        fx.eq({'peak1.freq': 250, 'peak1.gain': -4, 'peak1.q': 0.9, 'high.freq': 2500, 'high.gain': 5})],
    notes=(
        "80s gated-reverb return (Phil Collins / Hugh Padgham, AMS non-lin): 100 % wet, a flat dense burst that "
        "holds 280 ms and is cut dead in 25 ms, 8 ms predelay, 200 Hz low cut, slightly wide. The input eq "
        "(24 dB high-pass at 200 Hz, -9 dB dip at 3.8 kHz, 7 kHz low-pass) keeps kick lows, beater clicks and "
        "hats from opening the gate; the gate threshold is -16 dBFS on that filtered bus input. An output eq "
        "(-4 dB at 250 Hz, +5 dB shelf from 2.5 kHz; after the gate, so it does not change what opens it) "
        "gives back the bright 'whoosh' the input filtering takes away: v2 burst centroid ~750 Hz instead of "
        "~310 Hz (boxy) on the synthwave snare, same loudness. Calibrated for "
        "the synthwave kits in this library (tracks at -18 LUFS): their snare/clap/toms open it at sends of "
        "-8..-4 dB, kick and hats do not (outrun and 808 kits even on a whole-kit send). Set the effect "
        "level with the return (s.gated(gain_db=-6..+3)), not by lowering the send below -8, or raise "
        "threshold by the same amount you raise the send (rule: threshold ~ send - 10 dB). For the tightest "
        "result put snare/clap/toms on their own track (same kit patch) and send only that. Tweak: hold "
        "150-400 ms (about an 8th note: 60000/bpm/2), predelay 0-20, decay 1-4 (shorter = decaying burst), "
        "tone 0.4-0.8, width 0.8-1.5: s.gated(hold=250) passes params to the gatedreverb.")))
