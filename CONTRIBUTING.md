# Contributing

Thanks for your interest. Issues and pull requests are welcome.

- **Build and test** before a pull request: `cmake --preset release && cmake --build --preset release && ctest --preset release`
  and `python -m unittest discover -s tests/python` (both must pass with and without the DX7 ROM banks).
- **Engine rules** (see [CLAUDE.md](CLAUDE.md)): strict parameters (unknown keys are errors), deterministic renders
  (all randomness via `dsp::Rng`), no allocation / I/O / exceptions in `process()`. A new module declares every
  parameter as a `ParamSpec` with a `help` text, is registered in `engine/render/Registry.cpp` and gets a
  `tests/test_<name>.cpp`.
- **Docs**: [README.md](README.md) is the central overview; update it in the same commit as a user-facing change
  (`tests/python/test_readme.py` checks the basics).
- **Never commit** commercial or copyrighted audio (reference tracks stay in the gitignored `references/`), the
  Yamaha DX7 ROM files, or sample-pack contents: add a pack as an entry in `assets/samples/manifest.json` with its
  url, licence and attribution instead.
- By contributing you agree that your contribution is licensed under the MIT License of this project.
