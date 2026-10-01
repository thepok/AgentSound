"""Kestrel Bay - a melodic rock guitar instrumental built around two solos (the spirit of the classic guitar anthems:
Gary Moore, Gilmour, Satriani - original material). 84 BPM, A minor, ~3:30.

The hero guitar sings an 8-bar theme that returns and grows (verse -> chorus higher -> chorus2 an octave up), a bridge
climbs to a held note that blooms into feedback, and two solos develop the theme's head through the soloist's arc:
solo ('build': statement -> development -> burst -> climax) and outro ('classic': ... burst -> climax ->
resolution), played by the guitar vocabulary (bends that overshoot and settle, vibrato that goes up from the note,
legato, alternate-picked bursts, sweeps / tremolo, pinch harmonics, palm-muted chugs, whammy, wah, a unison bend,
feedback). Build:
    python -m agentsound build songs/kestrel-bay [--section solo]
Docs: BRIEF.md, ARRANGEMENT.md, SOUND.md, MIX.md, MASTER.md, AR.md.
"""
from agentsound import *
from agentsound import bands, bassist, drummer, fretwork as fw, gesture as G, guitarist as gtr, hero, soloist
from agentsound.patterns import Clip

ANALYSIS = {'profile': 'rock'}
METADATA = {'title': 'Kestrel Bay', 'artist': 'AgentSound', 'album': 'Fretwork', 'genre': 'Rock',
            'comment': 'A melodic rock guitar instrumental: two solos built by agentsound.soloist + fretwork.'}
COVER = {'style': 'rock', 'subtitle': 'Fretwork', 'seed': 7}      # seed 7: the subtitle clear of the sun

# The mix engineer's moves (python -m agentsound mix songs/kestrel-bay, two passes): the hero 1.5 dB down and the
# drums / bed up so the hero sits 2-4 dB over the band instead of 7, the bass and rhythm guitars a little down, the right rhythm guitar and the lead out of each other's
# presence band, the lead's mids pushed (+1.5 dB at 900 Hz: mid-forward like the Baker Street solo; MIX.md).
MIX = {
    'trim': {'lead': -1.5, 'lead_twin': -1.5, 'drums': 2.0, 'pad': 1.5, 'strings': 1.5, 'bass': -1.5,
             'clean': -1.5, 'gtr_l': -1.5, 'gtr_r': -1.0},
    'ride': {'strings': {'verse': 3.0}},
    'eq': {'gtr_r': [{'freq': 3300.0, 'gain': -2.0, 'q': 1.0}],
           'lead': [{'freq': 3300.0, 'gain': -1.5, 'q': 1.0}, {'freq': 900.0, 'gain': 1.5, 'q': 1.2}]},
}
# The song's loudness arc, ridden into the master chain (dB before the glue and the limiter): the intro and the break
# breathe, the solos build, the chorus2 / outro climax hits the limiter hardest.
ARC = {'intro': -8.0, 'verse': -7.0, 'chorus': -1.5, 'bridge': -4.0, 'solo': -6.0, 'solo2': 0.0, 'break': -9.0,
       'chorus2': 0.5, 'outro': -6.0, 'outro2': 0.5, 'end': 0.0}

# ------------------------------------------------------------------------------------------------ material
# The theme (beats from the section start: start, dur, pitch). Its head (bar 1-2) is the solos' motif.
THEME_A = [(0.0, 0.5, 'E4'), (0.5, 0.5, 'A4'), (1.0, 2.0, 'C5'), (3.0, 0.5, 'B4'), (3.5, 0.5, 'A4'),
           (4.0, 3.0, 'A4'), (7.5, 0.5, 'E4'),
           (8.0, 0.5, 'G4'), (8.5, 0.5, 'C5'), (9.0, 2.5, 'E5'), (11.5, 0.5, 'D5'),
           (12.0, 1.0, 'C5'), (13.0, 2.5, 'D5'),
           (16.0, 0.5, 'C5'), (16.5, 0.5, 'E5'), (17.0, 2.0, 'A5'), (19.0, 0.5, 'G5'), (19.5, 0.5, 'F5'),
           (20.0, 2.5, 'F5'), (22.5, 0.5, 'E5'), (23.0, 1.0, 'D5'),
           (24.0, 3.0, 'E5'), (27.0, 0.5, 'D5'), (27.5, 0.5, 'C5'),
           (28.0, 1.0, 'B4'), (29.0, 2.5, 'G#4')]
THEME_B = [(0.0, 0.5, 'E4'), (0.5, 0.5, 'A4'), (1.0, 2.0, 'C5'), (3.0, 0.5, 'B4'), (3.5, 0.5, 'A4'),
           (4.0, 2.0, 'A4'), (6.0, 0.5, 'C5'), (6.5, 0.5, 'D5'), (7.0, 1.0, 'E5'),
           (8.0, 0.5, 'C5'), (8.5, 0.5, 'E5'), (9.0, 2.5, 'G5'), (11.5, 0.5, 'F5'),
           (12.0, 1.0, 'E5'), (13.0, 2.5, 'D5'),
           (16.0, 0.5, 'C5'), (16.5, 0.5, 'D5'), (17.0, 2.0, 'F5'), (19.0, 0.5, 'E5'), (19.5, 0.5, 'D5'),
           (20.0, 2.0, 'D5'), (22.0, 1.0, 'B4'), (23.0, 1.0, 'D5'),
           (24.0, 3.0, 'E5'), (27.0, 0.5, 'D5'), (27.5, 0.5, 'B4'),
           (28.0, 3.5, 'A4')]
BRIDGE = [(0.0, 1.0, 'A4'), (1.0, 0.5, 'C5'), (1.5, 2.5, 'F5'),
          (4.0, 0.5, 'G5'), (4.5, 0.5, 'F5'), (5.0, 1.0, 'D5'), (6.0, 1.75, 'B4'),
          (8.0, 1.0, 'B4'), (9.0, 0.5, 'D5'), (9.5, 2.5, 'G5'),
          (12.0, 0.5, 'A5'), (12.5, 0.5, 'G5'), (13.0, 1.0, 'E5'), (14.0, 1.75, 'C5'),
          (16.0, 1.0, 'D5'), (17.0, 0.5, 'F5'), (17.5, 2.5, 'A5'),
          (20.0, 0.5, 'B5'), (20.5, 0.5, 'A5'), (21.0, 1.0, 'G5'), (22.0, 1.75, 'D5')]
THEME_C = [(0.0, 0.5, 'E5'), (0.5, 0.5, 'A5'), (1.0, 2.0, 'C6'), (3.0, 0.5, 'B5'), (3.5, 0.5, 'A5'),
           (4.0, 3.0, 'A5'), (7.5, 0.5, 'E5'),
           (8.0, 0.5, 'G5'), (8.5, 0.5, 'A5'), (9.0, 2.5, 'C6'), (11.5, 0.5, 'B5'),
           (12.0, 1.0, 'A5'), (13.0, 2.5, 'B5'),
           (16.0, 0.5, 'A5'), (16.5, 0.5, 'C6'), (17.0, 2.0, 'D6'), (19.0, 0.5, 'C6'), (19.5, 0.5, 'A5'),
           (20.0, 2.5, 'A5'), (22.5, 0.5, 'G5'), (23.0, 1.0, 'F5')]
MOTIF = [(0.0, 0.5, 'E4'), (0.5, 0.5, 'A4'), (1.0, 2.0, 'C5'), (3.0, 0.5, 'B4'), (3.5, 0.5, 'A4'), (4.0, 2.5, 'A4')]


def clip(notes, length, vel=92):
    return Clip([(a, d, p, vel) for a, d, p in notes], length=length)


def build() -> Song:
    s = Song('Kestrel Bay', tempo=84, key='A minor', seed=29, tail=7)
    intro = s.section('intro', bars=4)
    verse = s.section('verse', bars=8)
    chorus = s.section('chorus', bars=8)
    bridge = s.section('bridge', bars=8)
    solo = s.section('solo', bars=8)            # the first solo: the band holds back while it states the motif ...
    solo2 = s.section('solo2', bars=8)          # ... and drives once it develops, bursts and climbs
    brk = s.section('break', bars=4)
    chorus2 = s.section('chorus2', bars=8)
    outro = s.section('outro', bars=4)          # the second solo: a drop for its statement ...
    outro2 = s.section('outro2', bars=8)        # ... then the full band under the burst, the climax and the resolution
    end = s.section('end', bars=4)
    t = s.tempo

    P = {intro: 'Am F C G', verse: 'Am F C G Am Dm Esus4 E', chorus: 'Am F C G F G Am Am',
         bridge: 'F G Em Am Dm G Esus4 E', solo: 'Am F C G Am F C G', solo2: 'Am F C G F G Esus4 E',
         brk: 'F G Esus4 E', chorus2: 'Am F C G Am Dm Esus4 E', outro: 'Am F C G', outro2: 'Am F C G Dm Am E Am',
         end: 'Am Am Am Am'}
    prog = {sec: s.prog(spec) for sec, spec in P.items()}
    order = [intro, verse, chorus, bridge, solo, solo2, brk, chorus2, outro, outro2, end]

    # ------------------------------------------------------------------------------------------- the band
    b = bands.power_ballad(s, without=('lead',))
    gtr_l = s.track('gtr_l', 'sampled/crunch_guitar', pan=-0.85, gain_db=-3)
    gtr_r = s.track('gtr_r', 'sampled/dist_guitar', pan=0.85, gain_db=-3)
    clean = s.track('clean', 'sampled/clean_guitar', pan=0.35, gain_db=-5, sends={'echo': -6})
    clean.add_fx(fx.eq({'hp.freq': 170, 'hp.slope': 12}, name='lowcut'))   # the low strings belong to the bass
    b.piano.sends['echo'] = -14                                              # the quiet parts' echoes
    lead = hero(s.track('lead', 'layered/hero_guitar_heavy'), family='guitar_heavy', genre='rock',
                bed=[b.strings, b.pad], competitors=[b.piano, gtr_l, gtr_r, clean], throws=False)

    # drums: the whole form from the verse on (the intro is the guitars and a cymbal swell)
    dr = drummer.arrange(order[1:], bpm=t, style='ballad', density=0.55, seed=7, kit=b.drums, ending='hit',
                         plan={'verse': {'energy': 0.35}, 'chorus': {'style': 'halftime', 'energy': 0.75},
                               'bridge': {'energy': 0.55}, 'solo': {'role': 'verse', 'energy': 0.5},
                               'solo2': {'role': 'solo', 'style': 'halftime', 'energy': 0.88},
                               'chorus2': {'style': 'halftime', 'energy': 0.95},
                               'outro': {'role': 'verse', 'energy': 0.45},
                               'outro2': {'role': 'outro', 'style': 'halftime', 'energy': 0.95}})
    dr.play(b.drums)
    b.drums.play(drummer.swell(4, t, kit=b.drums), intro.bar(2))

    # bass
    bmem = bassist.Memory()
    for sec, part in ((verse, 'verse'), (chorus, 'chorus'), (bridge, 'bridge'), (solo, 'verse'), (solo2, 'chorus'),
                      (brk, 'break'), (chorus2, 'chorus'), (outro, 'verse'), (outro2, 'chorus')):
        bassist.arrange(prog[sec], bpm=t, key=s.key, style='rock', part=part, seed=3, memory=bmem,
                        at=sec).place(b.bass, sec)
    b.bass.note('A1', end.start, 10.0, 104)

    # piano: broken chords in the quiet parts, chords on the beat in the big ones (pedalled with the harmony)
    for sec in (intro, verse, bridge, solo, brk, outro):
        pv = prog[sec].block(voicing='spread', register=('A2', 'E5'), vel=60 if sec in (intro, brk) else 66)
        b.piano.play(pv.arpeggiate('pinky', rate='1/8', gate=1.6), sec)
    for sec in (chorus, solo2, chorus2, outro2):
        b.piano.play(prog[sec].block(voicing='spread', register=('A2', 'A4'), rhythm='x...x...', vel=72), sec)
    b.piano.play(s.prog('Am').block(voicing='spread', register=('A1', 'E5'), vel=84).stretch(3), end)
    ped = []
    for sec in order:
        x = sec.start
        while x < sec.end - 0.01:
            ped += [(x, 0, 'step'), (x + 0.08, 1, 'step')]
            x += 4
    b.piano.automate('instrument.pedal', ped)

    # strings and pad: the bed, swelling with the form
    for sec, vel in ((verse, 64), (chorus, 80), (bridge, 76), (solo, 62), (solo2, 76), (brk, 66), (chorus2, 92),
                     (outro, 64), (outro2, 84)):
        b.strings.play(prog[sec].block(voicing='spread', register=('E3', 'A5'), vel=vel), sec)
    b.strings.play(s.prog('Am').block(voicing='spread', register=('A3', 'E5'), vel=84).stretch(4), end)
    b.strings.automate('gainDb', ramp(verse.start, verse.bar(4), -12, -4), hold(verse.bar(4), bridge.start, -2),
                       ramp(bridge.start, solo.start, -4, 0), hold(solo.start, end.bar(1), 0),
                       ramp(end.bar(1), end.end, 0, -30))
    for sec in (chorus, solo, solo2, brk, chorus2, outro, outro2):
        b.pad.play(prog[sec].block(voicing='open', register=('C3', 'C5'), vel=74), sec)
    b.pad.play(s.prog('Am').block(register=('A2', 'E4'), vel=70).stretch(4), end)
    b.pad.automate('gainDb', hold(chorus.start, end.bar(1), 0), ramp(end.bar(1), end.end, 0, -30))

    # rhythm guitars: a double-tracked wall in the big parts, a clean Strat in the quiet ones
    rmem = gtr.Memory()
    for sec, tech in ((chorus, 'ring'), (solo, 'ring'), (solo2, 'power'), (chorus2, 'power'), (outro2, 'power')):
        arr = gtr.arrange(prog[sec], bpm=t, key=s.key, style='rock', section=sec, technique=tech, sound=gtr_l,
                          memory=rmem, seed=11)
        arr.play(gtr_l, sec)
        arr.take(2).play(gtr_r, sec)
    for g in (gtr_l, gtr_r):     # the first solo's statement: the wall held back, then in
        g.automate('gainDb', hold(chorus.start, solo.start, 0), ramp(solo.start, solo.bar(1), -6, -6),
                   ramp(solo.bar(6), solo2.start, -6, 0), hold(solo2.start, end.end, 0))
    gtr_l.play(Clip([(0, 7.5, n, 104) for n in ('A2', 'E3', 'A3')], length=8).strum(ms=14, bpm=t), end)
    gtr_r.play(Clip([(0, 7.5, n, 102) for n in ('A2', 'E3', 'A3')], length=8).strum(ms=16, bpm=t), end)
    cmem = gtr.Memory()
    for sec in (intro, verse, bridge, brk, outro):
        gtr.arrange(prog[sec], bpm=t, key=s.key, style='ballad', section=sec, technique='arpeggio', sound=clean,
                    memory=cmem, seed=5).play(clean, sec)

    # the loudness arc: a utility first in the master chain, ridden per section
    from agentsound.patches import FX
    s.master.fx.insert(0, FX('utility', {'gain': 0.0}, name='arc'))
    s.master.automate('fx.arc.gain', per_section({sec: ARC[sec.name] for sec in order}, glide=2.0),
                      [(end.bar(1), 0.0), (end.end + 6, -14.0, 'smooth')])
    # the last chord dies away after the limiter (before it, the limiter would only give the level back)
    s.master.automate('gainDb', hold(0, end.bar(1), 0.0), ramp(end.bar(1), end.end + 8, 0.0, -24.0))

    # ------------------------------------------------------------------------------------------- the lead
    lmem = gtr.Memory()
    parts = []

    def theme(notes, sec, length, *, style='ballad', climax=False, vel=(70, 112), seed=1):
        arr = gtr.lead(clip(notes, length), prog[sec], bpm=t, key=s.key, style=style, section=sec, seed=seed,
                       touch=vel, mono=True, articulations={}, memory=lmem, at=sec, climax=climax, gestures=True,
                       vib_style='wide' if style == 'ballad' else 'rock')
        parts.append(arr.part().shifted(sec.start))
        return arr

    # intro: the guitar swells in on a long E5 (the volume knob) that blooms into its octave - then the theme
    p = fw.feedback('E5', 9.0, t, partial=2, start=0.4, bloom_s=2.2, amount=0.8, vib='wide', vel=96, seed=3)
    p.gestures.append(G.swell(0.0, 9.0, t, lo=-16.0, peak=0.5, end=-3.0, peak_at=0.35, bright=0.0))
    parts.append(p.shifted(intro.bar(0, 2)))
    theme(THEME_A, verse, 32, seed=11)
    theme(THEME_B, chorus, 32, style='rock', vel=(76, 116), seed=12)
    theme(BRIDGE, bridge, 24, style='rock', vel=(74, 116), seed=13)
    # the bridge's set piece: bend up into A5, then G#5 held over Esus4 -> E, blooming into feedback
    parts.append(fw.bend('A5', 2.0, t, amount=2, vib='wide', vel=112, seed=4).shifted(bridge.bar(6)))
    hold_ = fw.feedback('G#5', 5.75, t, partial=2, start=0.25, bloom_s=1.6, amount=0.75, vib='wide', vel=114, seed=5)
    hold_.gestures.append(G.Gesture('throw', 'tone', 5.0, 9.0, [G._Shape('echo', [(5.0, 0.0), (5.75, 0.22),
                                                                                (9.0, 0.0)])]))
    parts.append(hold_.shifted(bridge.bar(6, 2)))

    # the solos: one budget for both, the theme's head as the motif
    bud = soloist.Budget(spice_every=1.5, fast_every=8, same_every=16)
    vocab = gtr.vocabulary('rock', vel=(66, 124))
    motif = clip(MOTIF, 8)
    # the first solo saves the big unison scream for the outro: it climbs to a held feedback note / a dive instead
    s1 = soloist.solo(s, lead, gtr.vocabulary('rock', vel=(66, 124), weights={'scream': 0.15}), at=[solo, solo2], arc='build', motif=motif, budget=bud,
                      prog=s.prog(P[solo] + ' ' + P[solo2]), seed=31,
                      place=False)
    s2 = soloist.solo(s, lead, vocab, at=[outro, outro2], arc='classic', motif=motif, budget=bud,
                      prog=s.prog(P[outro] + ' ' + P[outro2]), seed=22,
                      place=False)

    # break: a ghost bend sighing down, then a scooped E5 with a bar vibrato
    parts.append(fw.ghost_bend('D5', 3.5, t, amount=2, vel=90, seed=6).shifted(brk.start))
    sc = fw.whammy_scoop('E5', 3.0, t, semis=-1.5, vel=94)
    sc.gestures += fw.whammy_vibrato('E5', 3.0, t, depth=30, seed=6).gestures      # the scooped note, a bar vibrato
    parts.append(sc.shifted(brk.bar(1)))
    parts.append(fw.pinch('E4', 2.5, t, vel=114, seed=7).shifted(brk.bar(2, 2)))
    parts.append(fw.palm_mute(['E3', 'E3', 'G3', 'E3', 'A3', 'E3'], 2.0, t, vel=(84, 104)).shifted(brk.bar(3)))
    parts.append(fw.slide_in('B4', 2.0, t, frm=-5, vel=100).shifted(brk.bar(3, 2)))

    # chorus2: the theme an octave up - the climax - and a unison bend to close it
    theme(THEME_C, chorus2, 24, style='rock', climax=True, vel=(84, 124), seed=14)
    parts.append(fw.unison_bend('E5', 3.5, t, amount=2, vib='wide', vel=120, seed=8).shifted(chorus2.bar(6)))
    parts.append(fw.picked_run(['D5', 'C5', 'B4', 'A4', 'G4', 'A4', 'B4', 'C5'], 2.0, t, group=4,
                               vel=(96, 112)).shifted(chorus2.bar(7)))
    parts.append(fw.vibrato('E5', 1.8, t, style='rock', vel=110).shifted(chorus2.bar(7, 2)))

    # end: the last A blooms into feedback (the twelfth) and dies away; the echo carries it
    last = fw.feedback('A5', 14.0, t, partial=3, start=0.3, bloom_s=2.6, amount=0.7, vib='wide', vel=116, seed=9)
    last.gestures.append(G.taper(0.0, 14.0, t, db=-9.0, frac=0.4))
    last.gestures.append(G.Gesture('throw', 'tone', 9.0, 20.0, [G._Shape('echo', [(9.0, 0.0), (14.0, 0.3),
                                                                                (20.0, 0.0)])]))
    parts.append(last.shifted(end.start))

    fw.render(lead, parts + [p for *_, p in s1.parts] + [p for *_, p in s2.parts])
    s.advice += [f"soloist: {w}" for w in s1.warnings + s2.warnings]
    print('solo  :', s1.summary(), s1.budget['kept'])
    print('outro :', s2.summary(), s2.budget['kept'])
    return s
