#!/usr/bin/env bash
# CPU test suite: no GPU, no weights, no network. Needs the [dev] extras.
set -euo pipefail
cd "$(dirname "$0")"
CUDA_VISIBLE_DEVICES= exec "${PYTHON:-python}" -m pytest -q -p no:cacheprovider \
  orqanta_voice/tests/test_text.py orqanta_voice/tests/test_guards.py orqanta_voice/tests/test_server.py "$@"
