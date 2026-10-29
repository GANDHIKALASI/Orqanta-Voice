# Changelog

## 1.0 (2026-10-25)

First public release of Orqanta-Voice.

- Orqanta-Voice weights on Hugging Face: [buggandhi/Orqanta-Voice](https://huggingface.co/buggandhi/Orqanta-Voice) (bf16 safetensors).
- 12 languages: as bn en gu hi kn ml mr or pa ta te.
- 20 named voices, plus zero-shot and cross-lingual voice cloning.
- Streaming engine: continuous batching, CUDA graphs, cached voice prefixes, built-in duration and loop guards.
- Python API (`generate`, `stream`, `astream`), an OpenAI-compatible HTTP server and a multi-context WebSocket server.
- Bundled text normaliser for numbers, currency, dates, times, URLs and e-mail addresses in every language.
