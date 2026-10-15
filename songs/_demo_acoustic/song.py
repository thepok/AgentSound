"""The played acoustic guitar - sampled/acoustic_guitar + guitarist hand='acoustic' / 'fingerstyle'. Build:
    python -m agentsound build songs/_demo_acoustic --out songs/_demo_acoustic/out/strum                (this file)
    python -m agentsound build songs/_demo_acoustic/fingerpick.py --out songs/_demo_acoustic/out/fingerpick
    python -m agentsound build songs/_demo_acoustic/strum_fss.py --out songs/_demo_acoustic/out/strum_fss  (A/B)

strum       ~47 s, 96 BPM, G: let-ring intro, chuck-strummed verse, open-strummed chorus, ringing end
fingerpick  ~46 s, 76 BPM, C: ballad arpeggio intro, Travis picking, an arpeggiated bridge into a let-ring end
strum_fss   the strum passage (same seed: the same decisions) on the old sampled/steel_guitar (FSS: 2 layers, one
            sample per note, no recorded chucks / finger noises: the chucks fall back to short pitched notes)
The builders live in demo.py.
"""
from demo import strum

ANALYSIS = {'profile': 'jazz'}     # an acoustic in a small room (-16..-13 LUFS)


def build():
    return strum()
