"""rock_band demo: 'Highway Static' - 24 bars of arena rock in E minor at 126 BPM, built only from the rock_band preset
and ordinary composition code. Intro riff (palm-muted chugs), verse with the lead low, a pre-chorus lift, a chorus
with open power chords and the lead up an octave, a held rock ending.

Credits: Big Rusty Drums, Emilyguitar, Growlybass (Karoryfer, CC0), FreePats FSBS guitar / rock organ (CC0),
Voxengo IM Reverbs, Lexicon 224XL plate (Little Devil), Jester Emerald / Overdriven cabinet IRs.
"""
from agentsound import *
from agentsound import articulation as art, bands

ANALYSIS = {'profile': 'rock'}
METADATA = {'title': 'Highway Static', 'artist': 'AgentSound', 'album': 'Band Presets', 'genre': 'Rock'}


def chugs(roots, pattern, vel=100):
    """Palm-muted 8th chugs on power-chord roots, one root per bar; 'x' chug, 'X' accented open stab, '.' rest."""
    notes = []
    for bar, r in enumerate(roots):
        for i, ch in enumerate(pattern):
            if ch == '.':
                continue
            t = bar * 4 + i * 0.5
            notes.append((t, 0.45 if ch == 'x' else 0.95, note(r), vel + (12 if ch == 'X' else 0)))
    c = Clip(notes, length=len(roots) * 4).chordify('power')
    c = c.articulate('palm', where=lambda n: n.dur < 0.5)
    return c


def open_chords(roots, rhythm, vel=104):
    """Ringing power chords (root, 5th, octave) with a rhythm per bar ('x' hit, '_' hold)."""
    notes = []
    for bar, r in enumerate(roots):
        i = 0
        while i < len(rhythm):
            if rhythm[i] == 'x':
                j = i + 1
                while j < len(rhythm) and rhythm[j] == '_':
                    j += 1
                notes.append((bar * 4 + i * 0.5, (j - i) * 0.5 - 0.05, note(r), vel))
                i = j
            else:
                i += 1
    return Clip(notes, length=len(roots) * 4).chordify('power')


def build() -> Song:
    s = Song('Highway Static', tempo=126, key='E minor', seed=7)
    intro = s.section('intro', bars=4)
    verse = s.section('verse', bars=8)
    pre = s.section('pre', bars=2)
    chorus = s.section('chorus', bars=8)
    end = s.section('end', bars=2)

    b = bands.rock_band(s)

    # --- drums
    groove = drums({'kick': 'x.....x.x.......', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'}, vel=100)
    groove2 = drums({'kick': 'x.....x.x.x.....', 'snare': '....x.......x..o', 'hat': 'x.x.x.x.x.x.x.xo'}, vel=100)
    big = drums({'kick': 'x.....x.x.....x.', 'snare': '....X.......X...', 'ride': 'x.x.x.x.x.x.x.x.'}, vel=106)
    b.drums.play(drums({'kick': 'x.....x.x.......', 'hat': 'x.x.x.x.x.x.x.x.'}, vel=90), intro, times=3)
    b.drums.play(snare_roll(4, build=True), intro.bar(3))
    b.drums.play(crash(), verse)
    b.drums.loop(groove + groove2, verse, vel=0.72)
    b.drums.play(tom_fill(1), verse.bar(-1, 3), replace=True)
    b.drums.loop(drums({'kick': 'x.x.x.x.x.x.x.x.', 'snare': '....x.......x...', 'ohh': 'x.x.x.x.x.x.x.x.'},
                       vel=104), pre)
    b.drums.play(snare_roll(2, build=True), pre.bar(1, 2), replace=True)
    b.drums.play(crash(), chorus).play(crash(), chorus.bar(4))
    b.drums.loop(big, chorus)
    b.drums.play(tom_fill(2), chorus.bar(-1, 2), replace=True)
    b.drums.play(drums({'kick': 'x...............', 'crash': 'x...............'}, vel=108), end)
    b.drums.play(snare_roll(4, vel=(60, 110)).only(38), end.bar(0, 1))

    # --- guitars: the same part on both sides (two takes: different guitars, amps and humanize seeds)
    riff_roots = ['E2', 'E2', 'C3', 'D3']
    riff = chugs(riff_roots, 'x.x.xxX.', vel=98)
    verse_part = chugs(['E2', 'C3', 'G2', 'D3'], 'xxxxxxxX', vel=96)
    pre_part = open_chords(['A2', 'B2'], 'x_x_x_x_', vel=100)
    chorus_part = open_chords(['C3', 'G2', 'D3', 'E2'], 'x___x_x_', vel=108)
    ending = open_chords(['E2', 'E2'], 'x_______', vel=112).slice(0, 4)
    for t, ms in ((b.gtr_l, 11), (b.gtr_r, 13)):
        t.play(riff.strum(ms=ms, bpm=s.tempo), intro)
        t.loop(verse_part.strum(ms=ms, bpm=s.tempo, direction='alternate'), verse)
        t.play(pre_part.strum(ms=ms, bpm=s.tempo, direction='alternate'), pre)
        t.loop(chorus_part.strum(ms=ms + 4, bpm=s.tempo, direction='alternate'), chorus)
        t.play(ending.strum(ms=ms + 10, bpm=s.tempo), end)
        # loud-quiet: the palm-muted verse sits under the open chorus wall
        t.automate('gainDb', per_section({intro: -2, verse: -7, pre: -2, chorus: 0, end: 0}, glide=0.5))

    # --- bass: 8ths locked to the kick, staccato in the riff
    b.bass.play(riff.only(*[note(r) for r in riff_roots]).transpose(-12).articulate('staccato'), intro)
    b.bass.loop(s.prog('Em C G D').bass('pulse', rate='1/8', low='E1', vel=80), verse)
    b.bass.play(s.prog('A B').bass('pulse', rate='1/8', low='E1'), pre)
    b.bass.loop(s.prog('C G D Em').bass('pulse', rate='1/8', low='E1', vel=108), chorus)
    b.bass.note('E1', end.start, 7.5, 110)

    # --- organ: pads in the verse, pushed chords in the chorus, swell into the end
    b.keys.play(s.prog('Em C G D').block(voicing='spread', register=('E3', 'E5'), vel=74), verse.bar(4))
    b.keys.play(s.prog('A B').block(voicing='spread', register=('E3', 'E5'), vel=82), pre)
    b.keys.loop(s.prog('C G D Em').block(voicing='drop2', register=('G3', 'G5'), vel=88), chorus)
    b.keys.play(s.prog('Em').block(register=('E3', 'B4'), vel=90).stretch(2), end)
    # the final hit rings into the plate
    b.drums.automate('send.plate', hold(intro.start, end.start, -20), ramp(end.start, end.bar(1), -20, -8))
    b.keys.automate('send.plate', hold(intro.start, end.start, -16), ramp(end.start, end.bar(1), -16, -6))
    b.keys.automate('fx.tremolo.rate', hold(verse.start, pre.start, 0.9), ramp(pre.start, chorus.start, 0.9, 6.4),
                    hold(chorus.start, end.end, 6.4))

    # --- lead: verse melody low, chorus an octave up, legato slides, vibrato, a bend
    # (durations in beats: 0.5 = an 8th)
    v_line = s.motif('5:1 5:0.5 6:0.5 5:1 3:1 | 2:1 3:0.5 2:0.5 1:2 | 5:1 5:0.5 6:0.5 8:1 7:1 | 5:3 r:1'
                     ).clip(octave=4, vel=96)
    c_line = s.motif('8:1.5 7:0.5 8:1 10:1 | 9:2 8:1 7:1 | 5:1.5 6:0.5 7:1 8:1 | 8:3 r:1').clip(octave=4, vel=108)
    v_line = art.legato(v_line, overlap=0.03).glide(90, where=art.leaps(3))
    c_line = art.legato(c_line, overlap=0.03).glide(110, where=art.leaps(3))
    b.lead.play(v_line, verse.bar(0)).play(v_line, verse.bar(4))
    b.lead.play(c_line, chorus.bar(0)).play(c_line, chorus.bar(4))
    for at, line in ((verse.bar(0), v_line), (verse.bar(4), v_line), (chorus.bar(0), c_line),
                     (chorus.bar(4), c_line)):
        art.vibrato(b.lead, line, at, depth=28, rate=5.6, delay=0.3)
    bend = chorus.bar(7, 0.5)          # the last held note of the chorus: bend up a whole step and back
    b.lead.automate('instrument.pitchbend', [(bend, 0), (bend + 0.4, 2, 'smooth'), (bend + 1.6, 2),
                                             (bend + 2.0, 0, 'smooth')])
    b.lead.automate('send.echo', hold(verse.start, chorus.bar(3, 3), -11), ramp(chorus.bar(3, 3), chorus.bar(4), -11,
                                                                                -4),
                    hold(chorus.bar(4, 0.5), end.end, -11))
    return s
