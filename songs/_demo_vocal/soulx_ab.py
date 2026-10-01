"""A/B evaluation of SoulX-Singer (Soul-AILab, zero-shot singing voice synthesis, Apache-2.0) on the demo phrase.

    python songs/_demo_vocal/soulx_ab.py          # -> samples/soulx/generated.wav; then make_ab.py soulx

The prompt (the voice SoulX imitates) is one of HANAMI's OWN takes of this song - a licensed voicebank's render
(voicebank.check_prompt: the consent rule; never a real singer, never SoulX's bundled prompts). Its metadata (notes,
words, note types) comes from the singer's own timeline of that take; the target is the demo's score with the same
lyrics. SoulX runs in WSL (~/services/singing/soulx-venv + the SoulX-Singer checkout; see
agentsound/voicebank_runner/soulx_runner.py). Build the 'singer' variant first so the Hanami takes exist.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from agentsound import lyrics as ly          # noqa: E402
from agentsound import voicebank as vb       # noqa: E402

PROMPT_PHRASE = 1          # "each window gold and blue" (about 4 s)
OUT = HERE / 'samples' / 'soulx'


def _word_token(syls) -> str:
    phs = []
    for s in syls:
        for p in s.onset:
            phs.append(p.upper())
        phs.append(s.nucleus.upper() + str(s.stress))
        for p in s.coda:
            phs.append(p.upper())
    return 'en_' + '-'.join(phs)


def _words(line, text):
    """Per note: (word token, note type 2 = first note of a word / 3 = more notes of it)."""
    sung = ly.align(line, text)
    toks = []
    i = 0
    while i < len(sung):                    # word -> its syllables (to spell the whole word on its first note)
        j = i
        syls = [sung[i].syllable]
        while j + 1 < len(sung) and not (sung[j + 1].kind == 'syllable' and sung[j + 1].word_start):
            j += 1
            if sung[j].kind == 'syllable':
                syls.append(sung[j].syllable)
        tok = _word_token(syls)
        for k in range(i, j + 1):
            toks.append((tok, 2 if k == i else 3))
        i = j + 1
    return toks


def _meta(index, notes, total_s):
    """SoulX metadata: notes = [(start s, dur s, token, pitch, type)] with rests filled by <SP>."""
    seg, t = [], 0.0
    for st, du, tok, pitch, typ in notes:
        if st > t + 0.02:
            seg.append((st - t, '<SP>', 0, 1))
        seg.append((du, tok, pitch, typ))
        t = st + du
    if total_s > t + 0.02:
        seg.append((total_s - t, '<SP>', 0, 1))
    return [{'index': index, 'language': 'English', 'time': [0, int(round(total_s * 1000))],
             'duration': ' '.join(f"{d:.3f}" for d, _, _, _ in seg),
             'text': ' '.join('<SP>' if tok == '<SP>' else tok for _, tok, _, _ in seg),
             'phoneme': ' '.join(tok for _, tok, _, _ in seg),
             'note_pitch': ' '.join(str(p) for _, _, p, _ in seg),
             'note_type': ' '.join(str(ty) for _, _, _, ty in seg)}]


def main() -> int:
    os.environ.setdefault('AGENTSOUND_VOCAL_VARIANT', 'singer')
    import importlib.util
    spec = importlib.util.spec_from_file_location('demo_song', HERE / 'song.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    song = mod.build()
    song.compile()                           # renders / finds the Hanami takes
    vo = song.tracks['vocal']._singer['parts'][0]
    take = vo.rendered[PROMPT_PHRASE]
    wav = Path(take['path'])
    vb.check_prompt(wav, 'licensed-render', 'hanami')     # the consent rule
    info = json.loads(wav.with_suffix('.json').read_text(encoding='utf-8'))
    tl, sp = info['timeline'], info['spec']
    t0 = tl['offset_s']
    toks = tl['tokens']                       # (phoneme, start, end) in phrase seconds
    ph = vo.phrases[PROMPT_PHRASE]
    clip_notes = [vo.notes[i] for i in ph]
    from agentsound.patterns import Clip
    pline = Clip([(n.start, n.dur, n.pitch, n.vel) for n in clip_notes])
    words = _words(pline, ' '.join(_text_of(vo, ph)))
    # note starts in the take: a syllable from its first onset consonant, a run note from its own onset
    vowels = [i for i, (p, a, b) in enumerate(toks) if p in ly.VOWELS]
    starts, k = [], 0
    for n, (tok, typ), sn in zip(clip_notes, words, sp['notes']):
        if sn['k'] == 'syllable':
            vi = vowels[k]
            k += 1
            j = vi
            while j - 1 >= 0 and toks[j - 1][0] not in ('SP', 'AP') and toks[j - 1][0] not in ly.VOWELS:
                j -= 1
            starts.append(toks[j][1] - t0)
        else:
            starts.append(sn['t'] + sn['plan'].get('late_ms', 0) / 1000 - t0)
    ends = starts[1:] + [toks[-1][1] - t0]    # the last note ends where the tail silence starts
    pnotes = []
    for st, en, (tok, typ), n in zip(starts, ends, words, clip_notes):
        pnotes.append((st, max(0.05, en - st), tok, n.pitch, typ))
    total = sum(tl['durations']) * 512 / 44100
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'prompt.json').write_text(json.dumps(_meta('prompt', pnotes, total), indent=1), encoding='utf-8')
    import shutil
    shutil.copyfile(wav, OUT / 'prompt.wav')
    # the target: the whole line from the score (seconds at the song tempo, from the verse start)
    sec = 60.0 / song.tempo
    twords = _words(mod.MELODY, mod.LYRICS)
    tn = [(n.start * sec, n.dur * sec, tok, n.pitch, typ) for n, (tok, typ) in zip(ly.melody_notes(mod.MELODY), twords)]
    ttotal = tn[-1][0] + tn[-1][1] + 0.5
    (OUT / 'target.json').write_text(json.dumps(_meta('target', tn, ttotal), indent=1), encoding='utf-8')
    py = '$HOME/services/singing/soulx-venv/bin/python'
    runner = vb.wsl_path(HERE.parent.parent / 'agentsound' / 'voicebank_runner' / 'soulx_runner.py')
    cmd = (f'{py} "{runner}" "{vb.wsl_path(OUT / "prompt.wav")}" "{vb.wsl_path(OUT / "prompt.json")}" '
           f'"{vb.wsl_path(OUT / "target.json")}" "{vb.wsl_path(OUT)}" --fp16')
    r = subprocess.run(['wsl.exe', '-d', vb.DISTRO, '--', 'bash', '-c', cmd])
    print(f"SoulX-Singer -> {OUT / 'generated.wav'} (exit {r.returncode})")
    return r.returncode


def _text_of(vo, ph):
    """The lyrics tokens of one phrase, rebuilt from the sung notes (words, '-' for runs, '_' for holds)."""
    out = []
    for i in ph:
        n = vo.notes[i]
        if n.kind != 'syllable':
            out.append('-' if n.kind == 'melisma' else '_')
        elif n.word_start:
            out.append(n.syl.word)
    return out


if __name__ == '__main__':
    sys.exit(main())
