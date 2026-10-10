"""Expensive Habits - an original 80s Euro synth-pop song with a cool, half-spoken male vocal (118 BPM, C minor ->
Eb major choruses -> a whole step up for the last two choruses, ~4:00).
Build: python -m agentsound build songs/expensive-habits

The user's wish: "mach mir auch einen Pet-Shop-Boys-Song" - an ORIGINAL song in that idiom (West End Girls / It's a
Sin / Heart era): sequenced octave synth bass, a LinnDrum-era 80s pop kit with gated snare and big claps, Juno pads
and a string machine, Fairlight-style orchestra hits, a DX marimba sequence, a Fairlight "aah" choir for the big
chorus, a melancholic-but-danceable minor verse that blooms into a major chorus, a dramatic orchestra-hit build into
a key change. The voice is the signature: TIGER (male) almost deadpan in the verses (low, narrow, repeated notes,
sung soft and laid back), blooming a little in the choruses (still restrained: few scoops, little vibrato, dry);
Hanami sings soft "ahs" far under him. Nothing lifted: melody, words, riff and changes are this song's own.
Brief: BRIEF.md, form and changes: ARRANGEMENT.md, words: LYRICS.md, sounds: SOUND.md.

  intro    8   the riff on the bright glass piano + brass stabs, orchestra hits on the downbeats; drums enter bar 5
  verse1  16   TIGER half-spoken, low (Eb3-Bb3); octave bass, marimba sequence, pad, a light kit
  pre1     8   the lift: string machine climbs, snare build, riser; the chord turns to G (V of C minor)
  chorus1  8   the bloom: Eb major, "Expensive habits", full kit + claps, brass, orchestra hit, choir under it
  post1    4   the riff again (C minor)
  verse2  16   new words, e-piano stabs added, the marimba busier
  pre2     8   the lift again ("nobody here is sorry")
  chorus2  8   the chorus + Hanami's "ahs" + choir
  post2    4   the riff
  bridge   8   breakdown: half-time, pads + choir + strings, the one direct line ("I'll trade it all for one slow Sunday")
  lift     4   orchestra-hit build on the dominant of F, snare roll, riser -> the key change
  chorus3  8   F major (+2): everything
  chorus4  8   again, the last line turned ("and we're running out of time"), Hanami higher
  outro    8   the riff in D minor with the vocal tag, stripping down to the pad and a last hit
"""
from agentsound import *
from agentsound import bands, drummer, mastering, patches, singer

BPM = 118
POP80 = 'samples/sampleradar-80s-pop-drums'
LINN = 'samples/hyperreal-linndrum'
ANALYSIS = {'profile': 'pop'}
METADATA = {'title': 'Expensive Habits', 'artist': 'AgentSound', 'album': 'Night Economy', 'genre': 'Synth-pop',
            'year': 2026,
            'comment': 'Original 80s Euro synth-pop in the spirit of the era (no melody, lyric or riff borrowed)'}
# the mix engineer's moves (MIX.md): the voice 2 dB down and the band up around it (it read 7-8 dB over the drums and
# the bass in the choruses: "die Stimme im Vergleich zum Rest zu laut" was nowhere-to-be's lesson), the bed down to
# stay 4+ dB under him (second pass: it read -2.4..-3.0 dB in choruses 2-4), the riff under the outro tag, the kit's
# hats / claps dipped where his words live (the kit carried 47 % of the 2.5-6 kHz band against his 28 %)
MIX = {
    'trim': {'vocal': -2.0, 'drums': 2.0, 'bass': 1.0, 'riff': -1.5, 'keys': 1.5, 'pad': -3.0, 'choir': -3.0, 'strings': -2.5},
    'eq': {'drums': [{'freq': 3300.0, 'gain': -2.5, 'q': 1.0}]},
}
COVER = {'style': 'pop', 'palette': ['#1b2a4a', '#e8c547', '#d9d9d9'], 'title': 'EXPENSIVE HABITS',
         'subtitle': 'AgentSound - Night Economy', 'seed': 118}

# ------------------------------------------------------------------------------------------------ harmony
CHANGES = {
    'riff': 'Cm Ab Eb Bb',                                       # i VI III VII under the instrumental riff
    'riff_end': 'Cm Ab Eb Bb Cm Ab Eb:0.5 Bb:0.5 Cm',            # the outro: the last bar lands on the tonic
    'verse': 'Cm7:2 Abmaj7:2 Fm7:2 Gsus4 G',                     # i VI iv V, two bars each: the cool minor walk
    'pre': 'Ab Bb Gm7 Cm Ab Bb Fm7 Gsus4:0.5 G:0.5',             # VI VII v i ... landing on V (G)
    'chorus': 'Eb Bb/D Cm7 Ab Eb Bb/D Abmaj7 Bb',                # the bloom: V of C minor -> Eb major
    'bridge': 'Fm Db Ab Eb Fm Db Bb Bb',                         # iv bII: the darker turn
    'lift': 'Gm7 Gm7/C C7sus4 C7',                               # ii-V into F major (the key change)
}

# ------------------------------------------------------------------------------------------------ the voice (TIGER)
# notation (docs/COMPOSE_API.md "Notation"): sticky values, '|' checks the bars, '~' ties (one sung syllable).
# Verses: a narrow, talky recitation around G3 (Eb3-Bb3), every 2-bar line followed by ~1.5 bars of rest (the
# marimba / riff answers) - half-spoken, never crammed. Pre-chorus climbs to Eb4/D4; the chorus blooms (G3-Eb4) with
# pickups, the title on the leap to its top note.
V1 = """G3/8 G3 G3 F3 G3/8. Eb3/16 Eb3/8 F3 | G3/8. G3/16 F3/8 Eb3/8~ Eb3/2 | r/1 | r/1 |
        F3/8 Ab3/4 F3/8 F3 Ab3/4. | G3/8 Bb3 G3/4 Ab3/8. G3/16 G3/4~ | G3/2 r/2 | r/1 |
        G3/8 G3/4 F3/8 G3 G3 Bb3/4 | G3/8 F3 G3/4 F3/8 F3 Eb3/4~ | Eb3/2 r/2 | r/1 |
        F3/8 Ab3/4 F3/8 F3 F3 Ab3/4 | G3/4 F3/8 F3 Bb3/4 Ab3/8 G3 | G3/2. r/4 | r/1"""
V2 = """F3/8 G3/4 G3/8 F3 G3/4. | Eb3/8 F3 G3/4. F3/8 Eb3/4~ | Eb3/2 r/2 | r/1 |
        F3/8 Ab3/4. F3/8 F3 Ab3/4 | G3/8 G3 Bb3/4 Ab3/8 G3/4.~ | G3/2 r/2 | r/1 |
        r/4 G3/8 G3/4 F3/8 G3/4 | Bb3/4 G3/8 G3 Bb3/4 Ab3/8 G3 | G3/2. r/4 | r/1 |
        F3/8 Ab3/4 F3/8 Ab3/4 F3/4 | Bb3/4 G3/8 G3 G3 Bb3/4 G3/8 | G3/2. r/4 | r/1"""
PRE = """C4/4. Bb3/8 Ab3 C4/4 Bb3/8 | D4/4. Bb3/8 r/2 | C4/4. Bb3/8 G3 Bb3/4 G3/8 | C4/2. r/4 |
         r/8 Bb3/8 Eb4/4. C4/8 C4 r/8 | D4/4 C4/8 Bb3 r/2 | r/4 C4/8 C4 D4/4 Eb4/8 D4 | D4/2. r/4"""
# the chorus starts with a pickup 8th ('Ex-') half a beat before the bar
CHORUS = """Bb3/8 | Eb4/4. D4/8 C4/4 Bb3/4~ | Bb3/2 r/4 Bb3/8 Bb3 | C4/4 Bb3/4. G3/8 G3 C4~ | C4/2 r/4 r/8 Bb3/8 |
            C4/4. Bb3/8 Eb4/4. D4/8 | C4/4. Bb3/8 r/4 Bb3/8 Bb3 | C4/4. Bb3/8 G3/4. Bb3/8~ | Bb3/2. r/4"""
# the last chorus's last line: "and we're run-ning out of time" (one more syllable, the last note on the downbeat)
CHORUS_END = """Bb3/8 | Eb4/4. D4/8 C4/4 Bb3/4~ | Bb3/2 r/4 Bb3/8 Bb3 | C4/4 Bb3/4. G3/8 G3 C4~ | C4/2 r/4 r/8 Bb3/8 |
                C4/4. Bb3/8 Eb4/4. D4/8 | C4/4. Bb3/8 r/4 Bb3/8 Bb3 | C4/4. Bb3/8 C4/4. Bb3/8 | Bb3/1"""
BRIDGE = """r/8 C4/8 C4 Ab3/4 F3/8 Ab3 Ab3 | C4/4. Bb3/8 r/2 | Ab3/8 Ab3 C4/4. Bb3/8 Ab3 G3 | G3/2. r/4 |
            r/8 C4/8 Eb4/4 C4/8 Eb4/4 C4/8 | C4/8 F4/4 Eb4/4 Db4/4 r/8 | r/8 C4/8 D4/4 C4/8 D4 Bb3 Bb3 |
            C4/4 Bb3/8 Bb3 D4/2"""
TAG = """Bb3/8 | Eb4/4. D4/8 C4/4 Bb3/4~ | Bb3/2. r/4 | r/1 | r/2. r/8 Bb3/8 | Eb4/4. D4/8 C4/4 Bb3/4~ | Bb3/1 |
         r/1 | r/1"""

LYR_V1 = ("Tax-i at the cor-ner at a quar-ter to four, you pay with a card that's not yours an-y more. "
          "The door-man knows your name but he says it all wrong, we're fa-mous on the guest list where we nev-er be-long.")
LYR_V2 = ("Your flat has a view of a bet-ter flat, a plant you for-got and a bor-rowed cat. "
          "We read a-bout hou-ses like po-ems in bed, we can't af-ford the mor-ning, so we *dance* in-stead.")
LYR_PRE1 = "No-bo-dy here is count-ing, no-bo-dy here is old, we smile for the cam-er-as then we do what we're told."
LYR_PRE2 = "No-bo-dy here is sor-ry, no-bo-dy here is cold, we pose for the cam-er-as then we do what we're told."
# markup: *word* = the singer leans into it (the punchline words), (( line )) = an intimate, near-spoken aside
LYR_CHORUS = "Ex-pen-sive ha-bits, and a cheap view of the sky, we spend the night like mon-ey, and the mon-ey like *time*."
LYR_CHORUS_END = ("Ex-pen-sive ha-bits, and a cheap view of the sky, we spend the night like mon-ey, "
                  "and we're *run-ning* out of time.")
LYR_BRIDGE = ("All the win-dows on the wa-ter show a par-ty we don't know, "
              "I'll trade it all for one slow Sun-day, (( the phone switched off and the ra-di-o low. ))")
LYR_TAG = "Ex-pen-sive ha-bits. Ex-pen-sive ha-bits."

# the cool delivery: verses sung SOFT and laid back (the calm ballad singer: soft mode alone, small swings), almost no
# vibrato, quick glides on the talky 8ths; the choruses a little more voice (pop, but restrained: few small scoops,
# a narrow late vibrato on the long notes only, no doits, the soft mode still the base) - cool, never belting
VERSE_VOICE = dict(voice='tiger', style='ballad', vel=(60, 84), vib_other=0.15, vib_peak=0.4, vib_ct=10.0,
                   peak_vib_ct=14.0, glide_ms=60.0, late_ms=24.0, late_first_ms=10.0, swell=0.25, messa=0.1,
                   back_phrase=False, ornament=False, messa_di_voce=False,   # deadpan: no jazz phrasing,
                   mic_pull=False)        # ... and no fade on the line ends (they fell 10-16 dB under the band)
CHORUS_VOICE = dict(voice='tiger', style='pop', vel=(66, 96), scoop_first=0.12, scoop_leap=0.2, scoop_peak=0.3,
                    scoop_ct=45.0, vib_other=0.3, vib_peak=0.6, vib_ct=14.0, peak_vib_ct=20.0, vib_delay=0.45,
                    fall=0.04, doit=0.0, late_ms=18.0, late_first_ms=8.0, expr=0.6, model_vib=0.55,
                    base_soft=0.55, base_core=0.85, power_knee=0.6, accent=0.08,
                    back_phrase=False, ornament=False, messa_di_voce=False)
BREATH_S = 0.45        # rests this long (s) start a new take: every line its own breath

# Hanami's "ahs": long chord tones above him, soft and low in the mix (the 80s backing-singer pad)
AHS = 'G4/1 F4/2. r/4 | G4/1 Ab4/2. r/4 | G4/1 F4/2. r/4 | G4/1 F4/2. r/4'
AHS_HI = 'Bb4/1 A4/2. r/4 | Bb4/1 C5/2. r/4 | Bb4/1 A4/2. r/4 | Bb4/1 C5/2. r/4'   # chorus4 (after the +2): higher
LYR_AHS = 'Ah - ah - ah - ah -'
AH_VOICE = dict(voice='hanami', style='ballad', vel=(52, 72), vib_other=0.3, vib_ct=12.0, late_ms=20.0)

# ------------------------------------------------------------------------------------------------ the riff
# the instrumental hook (C minor, over i VI III VII): a syncopated climb to G5 and a fall back, answered a bar later;
# on the bright glass piano (octave-doubled, a pianist's right hand), the brass stab on its accents
RIFF = notes('C5/8 Eb5 G5/8. F5/16 Eb5/8 D5 C5/4 | r/8 C5/8 Eb5 F5 Eb5/4 C5/4 | '
             'Bb4/8 Eb5 G5/8. F5/16 Eb5/8 D5 Eb5/4 | r/8 D5/8 F5 G5 F5/4. r/8', length='bar')
# the outro's last statement: the answer climbs to the tonic and holds it (the song ends at home)
RIFF_END = notes('C5/8 Eb5 G5/8. F5/16 Eb5/8 D5 C5/4 | r/8 C5/8 Eb5 F5 Eb5/4 C5/4 | '
                 'Bb4/8 Eb5 G5/8. F5/16 Eb5/8 D5 Eb5/4 | D5/16 Eb5 G5/8 C6/2.', length='bar')
ORCH_INTRO = notes('ff [C4 C5]/4 r/2. | r/1 | mf [Eb4 Eb5]/4 r/2. | r/2 r/8 p [Bb3 Bb4]/8 r/4', length='bar')


def build() -> Song:
    s = Song('Expensive Habits', tempo=BPM, key='C minor', seed=118, tail=5)
    R, V, P, C, B, L = (s.prog(CHANGES[k]) for k in ('riff', 'verse', 'pre', 'chorus', 'bridge', 'lift'))
    R_END = s.prog(CHANGES['riff_end'])
    up = lambda p: p.transpose(2)                                       # the key change: C minor -> D minor
    intro = s.section('intro', 8, prog=R)
    verse1 = s.section('verse1', 16, prog=V)
    pre1 = s.section('pre1', 8, prog=P)
    chorus1 = s.section('chorus1', 8, prog=C)
    post1 = s.section('post1', 4, prog=R)
    verse2 = s.section('verse2', 16, prog=V)
    pre2 = s.section('pre2', 8, prog=P)
    chorus2 = s.section('chorus2', 8, prog=C)
    post2 = s.section('post2', 4, prog=R)
    bridge = s.section('bridge', 8, prog=B)
    lift = s.section('lift', 4, prog=L)
    chorus3 = s.section('chorus3', 8, prog=up(C))
    chorus4 = s.section('chorus4', 8, prog=up(C))
    outro = s.section('outro', 8, prog=up(R_END))
    choruses = (chorus1, chorus2, chorus3, chorus4)

    # ============================================================== the band: the retrowave preset as an 80s pop band
    # 80s pop kit + Linn claps through the keyed gated snare, the octave bass, the Juno pad, the bright DX e-piano,
    # brass stabs, the Fairlight choir; no lead - the voice is the lead
    # the preset's kit (SampleRadar 80s pop kit A + the LinnDrum clap) with the LinnDrum's crash, ride and tambourine
    # mapped in (kit A has no cymbals: the drummer's crashes fell on the open hat)
    kit_sound = inst.kit(f'{POP80}/Drum Kits/Kit A', map={'clap': f'{LINN}/clap.wav', 'crash': f'{LINN}/crash.wav',
                                                          'ride': f'{LINN}/ride.wav', 'tamb': f'{LINN}/tamb.wav'},
                         gains={'hats': -12, 'shaker': -10, 'clap': -1, 'cymbals': -9, 'tamb': -10},
                         lazy=True, level=-3.0)
    b = bands.retrowave(s, without=('lead',), sounds={'drums': kit_sound})
    kit, bass, pad, keys, brass, choir = b.drums, b.bass, b.pad, b.keys, b.brass, b.choir
    hall, plate = b.buses['hall'], b.buses['plate']
    echo = s.bus('echo', 'bus/echo')                      # (the preset's echo goes with its lead)
    strings = s.track('strings', 'synthwave/jupiter_strings', gain_db=-6, pan=0.0, sends={hall: -8},
                      fx=[fx.eq({'hp.freq': 180, 'peak1.freq': 420, 'peak1.gain': -3.0, 'peak1.q': 0.9})])
    marimba = s.track('marimba', 'synthwave/marimba', gain_db=-7, pan=0.5, sends={echo: -14, hall: -12})
    # the riff's glass piano with its compressor opened (-10 dB 2:1, children-of-neon's: the patch's flattened the
    # accents) and wider; e-piano / brass with a fuller velocity response (the preset's 0.5 read 0 dB per phrase)
    riff = s.track('riff', patches.get('layered/piano_glass_lead').but(**{
                       'layers.piano.fx.compressor.threshold': -10, 'layers.piano.fx.compressor.ratio': 2.0,
                       'layers.piano.fx.dimension.width': 1.15}),
                   gain_db=-2, sends={plate: -14, hall: -12, echo: -14})
    keys.instrument.params['velsens'] = 0.85
    brass.instrument.params['amp.velocity'] = 1.0
    bass.instrument.params['osc.retrig'] = 'off'          # free-running saws: the retriggered mono voice clicked (bar 65)
    for bed_t, w in ((pad, 1.25), (strings, 1.25), (choir, 1.3)):
        bed_t.add_fx(fx.width(width=w))                   # the bed wide around the centred voice (choruses read narrow)
    keys.pan, brass.pan = 0.45, -0.4
    strings.pan, choir.pan = -0.35, 0.35                  # the string machine left, the choir right: width from placement
    choir.send(hall, -3.5); strings.send(hall, -3.5); keys.send(hall, -7)   # the chorus's width: the bed's hall, not its level
    hall.fx['width'].set(width=1.0)                       # the hall carries the width the centred voice gives up
    bass.gain_db -= 1.5                                   # the octave bass read louder than the voice in the verses
    bass.add_fx(fx.eq({'peak1.freq': 220, 'peak1.gain': -2.5, 'peak1.q': 1.0}))  # out of his low register (60-250 Hz)
    bass.fx['ducker'].set(depth=9)                        # the kick owns the sub (kick + bass overlapped: -1.6 dB)
    pad.add_fx(fx.eq({'peak1.freq': 1100, 'peak1.gain': -2.5, 'peak1.q': 0.9}))   # pad vs his words (800 Hz-2.5 kHz)
    orch = s.track('orch', 'gm/orchestra_hit', gain_db=-3, sends={hall: -8})
    riser_t = s.track('riser', 'synthwave/noise_riser', gain_db=-12)
    impact = s.track('impact', 'synthwave/impact', gain_db=-2)
    down = s.track('down', 'synthwave/downlifter', gain_db=-12)

    # ============================================================== the riff (intro, posts, outro)
    def riff_part(vel=100, dbl=0.7, line=RIFF):
        # a pianist's touch: the beat leaned into, the 8ths between lighter, 16ths lighter still, a 2-bar arch
        c = line.with_vel(vel).vel_pattern([1.12, 0.74, 0.92, 0.78], grid='1/8').arch(bars=2, depth=0.4)
        return c.octave_double(-12, vel=dbl).strum(ms=6, direction='up', bpm=BPM)

    riff.play(riff_part(84, 0.62), intro).play(riff_part(98), intro.bar(4))
    riff.play(riff_part(102), post1).play(riff_part(104), post2)
    riff.play(riff_part(106).transpose(2), outro).play(riff_part(96, 0.65, RIFF_END).transpose(2), outro.bar(4))
    riff.automate('instrument.pedal', [(0, 0), (s.at(outro.bar(7)) - 0.05, 0), (s.at(outro.bar(7)), 1)])  # the last chord rings
    brass.play(RIFF.with_vel(88).vel_pattern([1.25, 0.6, 0.95, 0.66], grid='1/8').arch(bars=2, depth=0.45)
               .octave(-1), intro.bar(4))                # the brass doubles it, lower
    for sec, tr in ((post1, 0), (post2, 0), (outro, 2)):
        brass.play(RIFF.with_vel(92).vel_pattern([1.25, 0.6, 0.95, 0.66], grid='1/8').arch(bars=2, depth=0.45)
                   .octave(-1).transpose(tr), sec)

    # orchestra hits: intro downbeats, chorus downbeats, the build before the key change, the last hit
    orch.play(ORCH_INTRO.velocity(0.92), intro).play(ORCH_INTRO, intro.bar(4))
    for sec in choruses:
        t = 'F' if sec in (chorus3, chorus4) else 'Eb'            # the chorus's tonic
        orch.play(notes(f'ff [{t}4 {t}5]/4 r/2. | r/1 | r/1 | r/1 | mp [{t}4 {t}5]/4 r/2.', length='bar'), sec)
    # the build before the key change: the hits get denser and louder (on G, then C: the dominant of F)
    orch.play(notes('pp [G3 G4]/4 r/2. | mp [C4 C5]/4 r/4 r/8 [C4 C5]/8 r/4 | mf [C4 C5]/4. [C4 C5]/4. [C4 C5]/4 | '
                    'f [C4 C5]/8 [C4 C5] [C4 C5] [C4 C5] ff [C4 C5]/4 [E4 E5]/4', length='bar', vel=100), lift)
    orch.play(notes('r/1 | r/1 | r/1 | r/1 | r/1 | r/1 | r/1 | [D4 D5]/4 r/2.', length='bar', vel=112), outro)

    # ============================================================== the voice
    vmem = singer.Memory()
    VOX = []

    def sing(line, words, at, voice, take=0, transpose=0, **kw):
        v = singer.sing(s, line, words, at=at, seed=118, take=take, memory=vmem, split_s=BREATH_S,
                        transpose=transpose, **{**voice, **kw})
        VOX.append(v)
        return v

    def chorus_line(spec):
        return notes(spec, pickup=0.5)

    lead = sing(notes(V1), LYR_V1, verse1, VERSE_VOICE)
    sing(notes(PRE), LYR_PRE1, pre1, VERSE_VOICE, take=1)
    sing(chorus_line(CHORUS), LYR_CHORUS, chorus1, CHORUS_VOICE)
    sing(notes(V2), LYR_V2, verse2, VERSE_VOICE, take=2)
    sing(notes(PRE), LYR_PRE2, pre2, VERSE_VOICE, take=3)
    sing(chorus_line(CHORUS), LYR_CHORUS, chorus2, CHORUS_VOICE, take=1)
    sing(notes(BRIDGE), LYR_BRIDGE, bridge, VERSE_VOICE, take=4)
    sing(chorus_line(CHORUS), LYR_CHORUS, chorus3, CHORUS_VOICE, take=2, transpose=2)
    sing(chorus_line(CHORUS_END), LYR_CHORUS_END, chorus4, CHORUS_VOICE, take=3, transpose=2)
    sing(chorus_line(TAG), LYR_TAG, outro, VERSE_VOICE, take=5, transpose=2)

    # Hanami's "ahs" (pre2's last half, choruses 2-4), far under him
    ahs = None
    for sec, spec, tr, take in ((chorus2, AHS, 0, 0), (chorus3, AHS, 2, 1), (chorus4, AHS_HI, 0, 2)):
        ahs = singer.sing(s, notes(spec), LYR_AHS, at=sec, seed=7, take=take, transpose=tr, track_id='ahs',
                          pan=-0.55, gain_db=-10.5, split_s=BREATH_S, **AH_VOICE)

    # ============================================================== pads, strings, choir, keys
    spread = dict(voicing='spread', register=('C3', 'C5'))
    pad.chords(intro, verse1, pre1, chorus1, post1, verse2, pre2, chorus2, post2, bridge, lift, chorus3, chorus4,
               outro, **spread, bars={intro: 4},
               vel={'*': 72, intro: 64, verse1: 66, chorus1: 80, chorus2: 82, bridge: 76, chorus3: 86, chorus4: 86,
                    outro: 70})
    strings.chords(pre1, pre2, chorus1, chorus2, bridge, lift, chorus3, chorus4, register=('G3', 'G5'), voices=3,
                   vel={'*': 74, pre1: 66, pre2: 70, chorus3: 84, chorus4: 86},
                   crescendo={pre1: (0.6, 1.0), pre2: (0.6, 1.0), lift: (0.6, 1.0)}, bars={pre1: (4, 8)})
    choir.chords(chorus1, chorus2, bridge, chorus3, chorus4, register=('C3', 'C5'), voices=4,
                 vel={'*': 74, chorus1: 66, bridge: 70, chorus3: 82, chorus4: 84})
    keys.chords(verse2, chorus1, chorus2, chorus3, chorus4, voicing='drop2', register=('C4', 'C5'),
                rhythm={'*': 'x..x..x.', verse2: '..x...x.'}, vel={'*': 80, verse2: 70, chorus3: 86, chorus4: 86},
                then=[lambda c: c.vel_pattern([1.1, 0.8, 0.9]).arch(bars=4, depth=0.35)])
    bass.levels({'verse1': -3.0, 'verse2': -2.5, 'bridge': -2.5, 'pre1': -1.0, 'pre2': -1.0}, default=0.0)     # cooler verses
    pad.levels({'verse1': -2.0, 'verse2': -1.5, 'bridge': -1.5}, default=0.0)       # the verse bed under his words
    choir.levels({'bridge': -1.5}, default=0.0)                                      # ... and under the bridge's aside
    riff.levels({'outro': -6.5}, default=0.0)                                        # the riff under the outro tag

    # ============================================================== the sequences: marimba + octave bass
    marimba.arp({'*': 'updown', verse2: 'up'}, verse1, verse2, chorus3, chorus4, rate='1/16',
                register=('C4', 'C5'), vel={'*': 70, verse1: 64, chorus3: 66, chorus4: 66},
                pattern=[0, 2, 1, None], bars={verse1: (4, 16)})
    bass.bassline('octave', intro, verse1, pre1, chorus1, post1, verse2, pre2, chorus2, post2, lift, chorus3,
                  chorus4, outro, rate='1/8', gate=0.85, bars={intro: (4, 8), outro: (0, 6)},
                  vel={'*': 96, verse1: 86, verse2: 90, lift: 100})
    bass.bassline('root', bridge, rate='1/2', vel=84)
    bass.play(notes('D2/2', vel=82), outro.bar(7))                # the last bar: the tonic under the last hit

    # ============================================================== drums: the 80s machine drummer
    part = drummer.arrange(s, style='synthpop', density=0.55, seed=118, kit=kit,
                           plan={'intro': {'role': 'intro', 'energy': 0.45}, 'bridge': 'half',
                                 'lift': {'role': 'pre'}, 'outro': {'role': 'outro'}},
                           ending='hit')      # (the kit has no choked crash)
    part.play(kit)
    kit.clear(intro.start, intro.bar(4))                 # the intro's first half: riff + hits alone

    # ============================================================== transitions
    fxh = s.transitions(riser=riser_t, impact=impact, down=down, pitch='C4')
    for sec in (chorus1, chorus2):
        fxh.into(sec, riser=dict(beats=15, end=-1), impact=('C2', 110))
    fxh.into(chorus3, riser=dict(beats=15, end=-1), impact=('D2', 124), breath=1)
    fxh.into(bridge, down=('C4', 8, 90))

    # ============================================================== production
    # the voice: the vocal hero, clean (no tube) and DRY (the pop space: a short plate ~16 LU under it, echo only as
    # throws at section ends); the bed steps aside, the e-piano / marimba / riff dip under his words
    hero(lead.track, family='vocal', genre='pop', bed=[pad, choir, strings], competitors=[keys, marimba, riff],
         drive=False, deess={'freq': 5500}, ride=0.5)       # ride +0.5 (not 1.5): IN the band, not on top of it
    lead.track.hero.throw_db = -15.0                        # the section-end throws 5 dB lower: DRY (they read -15.8 LU)
    # the kit's hats / claps step aside in his consonant band only while he sings (it carried 37 % of 2.5-6 kHz
    # against his 35 %): the words, without turning him up
    s.carve(kit, key=lead.track, freq=3500, q=0.8, depth=3.0)
    hero(ahs.track, family='vocal', genre='pop', drive=False, ride=False, duck=False, carve=False, dips=False,
         throws=False)

    # the arc: a cool verse, the choruses bigger, the last two the biggest
    s.arc({'intro': -1.5, 'verse1': -2.5, 'pre1': -1.6, 'chorus1': 0.0, 'post1': -0.5, 'verse2': -2.0,
           'pre2': -1.1, 'chorus2': 0.5, 'post2': 0.0, 'bridge': -2.0, 'lift': -0.5, 'chorus3': 1.0,
           'chorus4': 1.2, 'outro': -0.5})
    # the master (MASTER.md): no tonal eq (the mix sits within 1 dB of the pop profile), the limiter driven +2.8 dB
    # for ~-10.8 LUFS (inside the pop window -11..-8; more drive only cost LRA), ceiling -1.2 dBFS for <= -1 dBTP
    mastering.apply(s, limiter={'ceiling': -1.2, 'release': 120.0}, loudness_change=+2.8)
    return s
