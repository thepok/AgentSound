"""SoulX-Singer (Soul-AILab, Apache-2.0) score-conditioned inference for an A/B evaluation - runs INSIDE WSL in its
own venv (torch, transformers 4.41, ...; ~/services/singing/soulx-venv) with the SoulX-Singer repo checked out at
$SOULX_DIR (default ~/services/singing/SoulX-Singer) and its SVS weights in pretrained_models/SoulX-Singer/model.pt.

    python soulx_runner.py prompt.wav prompt.json target.json out_dir [--steps 32] [--cfg 3] [--seed 0]

prompt.wav / prompt.json: the zero-shot voice prompt and its metadata (SoulX's format: duration / phoneme / note_pitch /
note_type per note). THE CONSENT RULE: the prompt must be a licensed voicebank's own render, a synthetic voice or the
user's own voice (agentsound.voicebank.check_prompt checks it before this is called) - never a real singer.
target.json: the notes + words to sing. Writes out_dir/generated.wav (24 kHz). Score control, no auto pitch shift.
"""

from __future__ import annotations

import os
import sys


def main(argv) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('prompt_wav')
    ap.add_argument('prompt_json')
    ap.add_argument('target_json')
    ap.add_argument('out_dir')
    ap.add_argument('--steps', type=int, default=32)
    ap.add_argument('--cfg', type=float, default=3.0)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--fp16', action='store_true')
    a = ap.parse_args(argv[1:])
    root = os.path.expanduser(os.environ.get('SOULX_DIR', '~/services/singing/SoulX-Singer'))
    sys.path.insert(0, root)
    os.chdir(root)
    import numpy as np
    import soundfile as sf
    import torch
    torch.manual_seed(a.seed)
    np.random.seed(a.seed)

    def load_wav(path, sample_rate):        # torchaudio 2.9 needs torchcodec for load(): read with soundfile
        import torchaudio
        x, sr = sf.read(path, dtype='float32', always_2d=True)
        w = torch.from_numpy(x.mean(axis=1, keepdims=True).T.copy())
        if sr != sample_rate:
            w = torchaudio.functional.resample(w, sr, sample_rate)
        return w

    from soulxsinger.utils import audio_utils, data_processor
    audio_utils.load_wav = load_wav
    data_processor.load_wav = load_wav
    from cli import inference
    from soulxsinger.utils.file_utils import load_config
    config = load_config('soulxsinger/config/soulxsinger.yaml')
    config.infer.n_steps = a.steps
    config.infer.cfg = a.cfg
    args = argparse.Namespace(device='cuda' if torch.cuda.is_available() else 'cpu',
                              model_path='pretrained_models/SoulX-Singer/model.pt', prompt_wav_path=a.prompt_wav,
                              prompt_metadata_path=a.prompt_json, target_metadata_path=a.target_json,
                              phoneset_path='soulxsinger/utils/phoneme/phone_set.json', save_dir=a.out_dir,
                              auto_shift=False, pitch_shift=0, control='score', use_fp16=a.fp16)
    model = inference.build_model(args.model_path, config, args.device, a.fp16)
    inference.process(args, config, model)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
