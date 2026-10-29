# Contributing

Thanks for helping improve Orqanta-Voice.

- **Maintainer:** Gandhi Kalasi (@gandhikalasi)
- **Bugs and feature requests:** open a GitHub issue. Include the language, the voice or cloning mode, the exact text, the seed, the GPU, and the `Orqanta-Voice` commit. A short audio clip helps.
- **Pull requests:** keep them small and focused, and describe what changed and how you tested it.
  - Run the CPU tests before sending: `./run_tests.sh`.
  - Changes to the engine's hot path (`orqanta_voice/engine.py`, `serve/fast_*.py`) should come with before/after numbers from `orqanta_voice/bench/bench_engine.py` on a GPU.
- **Text normaliser:** put fixes in `orqanta_voice/text/rules.py` or `orqanta_voice/text/lexicon.py`, with a test case.
- **Style:** Python 3.10+, standard library first, no new heavy dependencies without discussion.
- **Security / misuse reports:** do not open a public issue. See [SECURITY.md](SECURITY.md).
- By contributing you agree that your contribution is licensed under the repository's license.
