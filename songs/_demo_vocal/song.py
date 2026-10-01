"""Vocal demo: an 8-bar pop phrase SUNG by a licensed DiffSinger voicebank (agentsound.singer), original lyrics.

    City lights are calling out,   each window gold and blue.
    Hold me close and say it loud, all the night belongs to you.

C major, 92 BPM, I V vi IV | I V IV I. 1 bar of piano, 8 bars sung, 1 bar tail. The melody is written as a Clip;
the singer places consonants before the beats, scoops, glides, grows late vibrato on the held notes, breathes in
the gaps and falls off a phrase end (the moves log is printed when the song builds).

Variants ($AGENTSOUND_VOCAL_VARIANT, see make_ab.py which builds them all into out/*.mp3):
  full     the vocal through the vocal hero chain (de-esser, compression, presence, plate + echo throws), a double
           pair and a harmony on the last line, over piano / pad / bass        -> out/vocal_demo.mp3
  dry      the sung vocal alone, no chain, no reverb                             -> out/vocal_dry.mp3
  robotic  A/B baseline: the same notes and words with no singer moves (flat pitch steps, consonants on the beat,
           no breaths, one level, one voice mode), vocal alone + a light plate   -> out/ab_robotic.mp3
  singer   A/B: with the singer moves, the same setup                           -> out/ab_singer.mp3
  model    A/B: the voicebank's own pitch model alone (no singer pitch moves)  -> out/ab_pitch_model.mp3
  player   A/B: the singer's own pitch curve alone (pitch='player': synthetic glides, no model)
                                                                                 -> out/ab_player_pitch.mp3
  (singer / dry / full / tiger use the default pitch='hybrid': the model's curve with the singer's moves on top)
  tiger    A/B: the same phrase by the TIGER voicebank (male, an octave down; NON-COMMERCIAL licence)
                                                                                 -> out/ab_tiger.mp3
  soulx    A/B: SoulX-Singer (zero-shot, prompted with one of Hanami's own takes; soulx_ab.py renders it first)
                                                                                 -> out/ab_soulx.mp3
Build: python -m agentsound build songs/_demo_vocal   (needs the voicebank + the WSL singing venv: COMPOSE_API "Vocals")
"""
import os

from agentsound import *
from agentsound import singer
from agentsound.humanize import touch

ANALYSIS = {'profile': 'pop'}
VARIANT = os.environ.get('AGENTSOUND_VOCAL_VARIANT', 'full')
METADATA = {'artist': 'AgentSound', 'album': 'Demos', 'genre': 'Pop'}

LYRICS = ("City lights are calling out -, each window gold and blue. "
          "Hold me close and say it loud -, all the night belongs to you.")

# (start beat, length, note) - one note per syllable ('-' in the lyrics: a two-note run on "out" / "loud")
MELODY = Clip([
    # City lights are calling out -
    (0.0, 0.75, 'E4'), (0.75, 0.25, 'E4'), (1.0, 1.5, 'G4'), (2.5, 0.5, 'F4'), (3.0, 0.5, 'G4'), (3.5, 0.5, 'E4'),
    (4.0, 1.5, 'E4'), (5.5, 1.0, 'D4'),
    # each window gold and blue
    (8.0, 1.0, 'E4'), (9.0, 0.5, 'G4'), (9.5, 0.5, 'A4'), (10.0, 1.5, 'C5'), (11.5, 0.5, 'B4'), (12.0, 2.5, 'A4'),
    # Hold me close and say it loud -
    (16.0, 1.0, 'G4'), (17.0, 0.5, 'A4'), (17.5, 1.0, 'C5'), (18.5, 0.5, 'B4'), (19.0, 1.0, 'D5'), (20.0, 0.5, 'C5'),
    (20.5, 1.5, 'E5'), (22.0, 1.0, 'D5'),
    # all the night belongs to you
    (24.0, 1.0, 'C5'), (25.0, 0.5, 'A4'), (25.5, 1.0, 'G4'), (26.5, 0.5, 'E4'), (27.0, 1.0, 'G4'), (28.0, 0.5, 'D4'),
    (28.5, 3.0, 'C4'),
], length=32)


def build() -> Song:
    s = Song('Gold and Blue (vocal demo)', tempo=92, key='C major', seed=7)
    intro = s.section('intro', bars=1)
    verse = s.section('verse', bars=8)
    s.section('tail', bars=1)
    prog = s.prog('I V vi IV I V IV I')

    if VARIANT == 'soulx':     # SoulX-Singer's take of the same line (soulx_ab.py renders it), the same plate
        wav = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'samples', 'soulx', 'generated.wav')
        if not os.path.isfile(wav):
            raise ComposeError("no SoulX take yet: run python songs/_demo_vocal/soulx_ab.py first")
        sx = s.track('soulx', inst.sampler(file=wav, root=60, oneshot='on', velsens=0))
        sx.note(60, verse, 32, vel=127)
        sx.send(s.plate('plate', decay=1.8), -16)
        return s

    if VARIANT in ('robotic', 'singer', 'model', 'player', 'tiger', 'dry'):
        moves = VARIANT != 'robotic'
        voice = 'tiger' if VARIANT == 'tiger' else 'hanami'
        vox = singer.sing(s, MELODY, LYRICS, at=verse, voice=voice, style='pop', seed=3, moves=moves,
                          pitch={'model': 'model', 'player': 'player'}.get(VARIANT, 'hybrid'),
                          transpose=-12 if voice == 'tiger' else 0)
        if VARIANT != 'dry':
            plate = s.plate('plate', decay=1.8)
            vox.track.send(plate, -16)
        print(vox.describe())
        return s

    # --- full: the vocal produced over a small band (piano, pad, fretless bass)
    hall = s.hall(decay=2.6)
    s.master.add(fx.limiter(gain=3.0, ceiling=-1.0))
    piano = s.track('piano', 'gm/grand_piano', gain_db=-9, pan=-0.1, sends={hall: -12},
                    fx=[fx.eq({'peak1.freq': 330, 'peak1.gain': -4, 'peak1.q': 0.9})])
    pad = s.track('pad', 'gm/warm_pad', gain_db=-15, fx=[fx.eq({'hp.freq': 180, 'peak1.freq': 400, 'peak1.gain': -3})])
    bass = s.track('bass', 'gm/fretless', gain_db=-7)
    comp = touch(prog.block(voicing='spread', rhythm='x..x..x.', register=('E3', 'C5')), 58, 92)
    piano.play(comp, intro)
    piano.loop(comp, verse)
    piano.humanize(timing_ms=7, vel=12, seed=4)
    pad.loop(prog.block(register=('G3', 'D5')), verse)
    bass.loop(prog.bass('root', rate='1/2'), verse)
    mem = singer.Memory()
    vox = singer.sing(s, MELODY, LYRICS, at=verse, voice='hanami', style='pop', seed=3, memory=mem)
    hero(vox.track, family='vocal', bed=[pad], competitors=[piano])
    for dbl in (singer.double(vox, pan=-0.55), singer.double(vox, pan=0.55)):
        hero(dbl.track, family='vocal', ride=False, throws=False, duck=False, carve=False, dips=False)
    # a harmony a third above on the last line, sung (not shifted), under the lead
    harm = singer.sing(s, MELODY.slice(24, 32).transpose_scale(2, 'C major'), 'all the night belongs to you.',
                       at=verse.beat(24), voice='hanami', style='pop', seed=3, take=21, formant=0.25,
                       track_id='vocal_harm', pan=0.3, gain_db=-7, memory=mem, vib_ct=18, peak_vib_ct=26, fall=0)
    hero(harm.track, family='vocal', ride=False, throws=False, duck=False, carve=False, dips=False)
    print(vox.describe())
    return s
