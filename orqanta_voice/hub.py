"""Resolve an Orqanta-Voice release (a local dir or a Hugging Face repo id) into the paths the engine needs.

    from orqanta_voice.hub import resolve
    paths = resolve("/path/to/release/orqanta_voice")      # or "org/Orqanta-Voice" (Hugging Face repo id)
    # -> {"ckpt": ..., "backbone_dir": ..., "mimi_dir": ..., "ecapa_dir": ...}
    tts = OrqantaVoiceTTS.from_pretrained("/path/to/release/orqanta_voice", max_seats=16)   # calls resolve() itself

Release layout (what orqanta_voice/tools/convert_to_safetensors.py writes):
    model.safetensors | model-0000k-of-0000N.safetensors + model.safetensors.index.json
    orqanta_voice_config.json resolved model config + format version (+ codec / speaker-encoder repo ids)
    config.json              short model summary on the Hub (optional; fetched with the release, not read)
    backbone/                Qwen3 config.json + tokenizer files (no weights; the architecture is built from config)
    voices/voices.json       named voices (optional)

Mimi (kyutai/mimi) and ECAPA (speechbrain/spkrec-ecapa-voxceleb) come from `huggingface_hub.snapshot_download`,
OFFLINE FIRST: a copy already in the local HF cache is used without any network call (also when the cache has the
snapshot but no `refs/main`, e.g. a copied cache). The network is only used when nothing usable is cached and
HF_HUB_OFFLINE is not set. A local directory may be passed instead of a repo id (`mimi=`, `ecapa=`, or the
ORQANTA_VOICE_MIMI_DIR / ORQANTA_VOICE_ECAPA_DIR environment variables).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

MIMI_REPO = "kyutai/mimi"
ECAPA_REPO = "speechbrain/spkrec-ecapa-voxceleb"
RELEASE_CONFIG = "orqanta_voice_config.json"
WEIGHT_FILES = ("model.safetensors.index.json", "model.safetensors", "model.pt")
# files each component needs (also the snapshot_download allow-lists)
MIMI_FILES = ("config.json", "model.safetensors")
MIMI_PATTERNS = ["config.json", "model.safetensors", "preprocessor_config.json"]
ECAPA_FILES = ("embedding_model.ckpt",)
ECAPA_PATTERNS = ["embedding_model.ckpt", "hyperparams.yaml"]
RELEASE_PATTERNS = ["*.safetensors", "*.safetensors.index.json", "*_config.json", RELEASE_CONFIG, "config.json", "backbone/*", "voices/*", "README.md"]


def _offline():
    return os.environ.get("HF_HUB_OFFLINE", "").strip().lower() in ("1", "true", "yes", "on")


def _has(d, files):
    return d is not None and all((Path(d) / f).is_file() for f in files)


def _cached_snapshot(repo_id, files, cache_dir=None, revision=None):
    """A cached snapshot dir of `repo_id` holding `files`, found without any network call, or None."""
    from huggingface_hub import snapshot_download
    try:
        d = snapshot_download(repo_id, revision=revision, cache_dir=cache_dir, local_files_only=True)
        if _has(d, files):
            return d
    except Exception:          # not cached / no refs for the revision: fall back to scanning the snapshots
        pass
    if revision is not None and len(revision) != 40:
        return None
    from huggingface_hub import constants
    root = Path(cache_dir or constants.HF_HUB_CACHE) / ("models--" + repo_id.replace("/", "--")) / "snapshots"
    if not root.is_dir():
        return None
    snaps = [p for p in root.iterdir() if p.is_dir() and _has(p, files) and (revision is None or p.name == revision)]
    if not snaps:
        return None
    return str(max(snaps, key=lambda p: p.stat().st_mtime))


def snapshot(repo_or_dir, files, patterns, cache_dir=None, revision=None, local_files_only=None):
    """Local dir for a repo id (or an existing local dir): offline first, then the network unless offline."""
    import shutil
    p = Path(os.path.expanduser(str(repo_or_dir)))
    if p.is_dir():
        for f in files:
            if not (p / f).is_file():
                for search_base in (Path(__file__).parent / "assets", Path(__file__).parent.parent):
                    bundled = search_base / f
                    if bundled.is_file():
                        (p / f).parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy(bundled, p / f)
                        break
        if not _has(p, files):
            raise FileNotFoundError(f"{p} lacks {[f for f in files if not (p / f).is_file()]}")
        return str(p.resolve())
    d = _cached_snapshot(str(repo_or_dir), files, cache_dir, revision)
    if d is not None:
        return d
    if local_files_only or (local_files_only is None and _offline()):
        raise FileNotFoundError(f"{repo_or_dir} is not in the local Hugging Face cache "
                                f"({cache_dir or 'default HF cache'}) and downloads are disabled (HF_HUB_OFFLINE)")
    from huggingface_hub import snapshot_download
    try:
        d = snapshot_download(str(repo_or_dir), revision=revision, cache_dir=cache_dir, allow_patterns=list(patterns))
    except Exception as e:
        fallback_repo = os.environ.get("ORQANTA_VOICE_FALLBACK_REPO", "maya-research/maya2-native")
        if fallback_repo and str(repo_or_dir) != fallback_repo:
            d = snapshot_download(fallback_repo, revision=revision, cache_dir=cache_dir, allow_patterns=list(patterns))
        else:
            raise e
    for f in files:
        target = Path(d) / f
        if not target.is_file():
            for search_base in (Path(__file__).parent / "assets", Path(__file__).parent.parent):
                bundled = search_base / f
                if bundled.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(bundled, target)
                    break
    if not _has(d, files):
        raise FileNotFoundError(f"{repo_or_dir}@{revision or 'main'} lacks {list(files)}")
    return d


def release_config(model_dir):
    """Release config of a model dir as a dict ({} if absent, e.g. a bare model.pt dir)."""
    for name in (RELEASE_CONFIG, "config.json"):
        p = Path(model_dir) / name
        if p.is_file():
            try:
                data = json.loads(p.read_text())
                if isinstance(data, dict):
                    if "model_config" in data and isinstance(data["model_config"], str):
                        target = Path(model_dir) / data["model_config"]
                        if target.is_file():
                            try:
                                sub = json.loads(target.read_text())
                                if isinstance(sub, dict):
                                    return {**data, **sub}
                            except Exception:
                                pass
                    return data
            except Exception:
                pass
    for p in Path(model_dir).glob("*_config.json"):
        try:
            data = json.loads(p.read_text())
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


DEFAULT_MODEL_REPO = "buggandhi/Orqanta-Voice"

def resolve(model_dir_or_repo=None, *, mimi=None, ecapa=None, cache_dir=None, revision=None, local_files_only=None,
            include_model_config=False) -> dict:
    """-> dict(ckpt=..., backbone_dir=..., mimi_dir=..., ecapa_dir=..., voices_json=...), absolute local paths.

    voices_json is <dir>/voices/voices.json when it lists at least one named voice, else None. It is not an
    OrqantaVoiceTTS.from_pretrained argument: splat only the first four keys, or call from_pretrained("<release dir>").

    model_dir_or_repo   a local release dir (see the module docstring) or a Hugging Face repo id
    mimi / ecapa        repo id or local dir overriding orqanta_voice_config.json / ORQANTA_VOICE_MIMI_DIR /
                        the defaults kyutai/mimi and speechbrain/spkrec-ecapa-voxceleb
    cache_dir           HF cache dir (default: HF_HUB_CACHE / HF_HOME)
    revision            revision of model_dir_or_repo when it is a repo id (Mimi / ECAPA use their cached / main)
    local_files_only    True: never touch the network; None (default): offline first, network only if nothing is
                        cached and HF_HUB_OFFLINE is unset; False: same as None
    include_model_config  also return model_config=<dir>/orqanta_voice_config.json (an Engine kwarg, not an EngineConfig
                        field: do not splat it into OrqantaVoiceTTS.from_pretrained)
    """
    if model_dir_or_repo in (None, "Orqanta-Voice", "orqanta-voice", "default"):
        model_dir_or_repo = DEFAULT_MODEL_REPO
    p = Path(os.path.expanduser(str(model_dir_or_repo)))
    if p.is_dir():
        model_dir = p.resolve()
    elif p.is_file() and p.suffix == ".pt":          # a bare flat checkpoint: backbone etc. must be passed separately
        raise ValueError(f"{p} is a bare checkpoint; pass ckpt/backbone_dir/mimi_dir/ecapa_dir explicitly")
    else:
        model_dir = Path(snapshot(str(model_dir_or_repo), ("config.json",), RELEASE_PATTERNS, cache_dir, revision,
                                  local_files_only))
    weights = [f for f in WEIGHT_FILES if (model_dir / f).is_file()]
    if not weights:
        fallback_repo = os.environ.get("ORQANTA_VOICE_FALLBACK_REPO", "maya-research/maya2-native")
        if fallback_repo:
            w_dir = Path(snapshot(fallback_repo, ("model.safetensors.index.json",), RELEASE_PATTERNS, cache_dir, revision, local_files_only))
            weights = [f for f in WEIGHT_FILES if (w_dir / f).is_file()]
            if weights:
                model_dir = w_dir
    if not weights:
        raise FileNotFoundError(f"{model_dir}: no {' / '.join(WEIGHT_FILES)}")
    if weights[0] == "model.safetensors.index.json":
        idx = json.loads((model_dir / weights[0]).read_text())
        missing = sorted({f for f in idx["weight_map"].values() if not (model_dir / f).is_file()})
        if missing:
            fallback_repo = os.environ.get("ORQANTA_VOICE_FALLBACK_REPO", "maya-research/maya2-native")
            if fallback_repo:
                from huggingface_hub import hf_hub_download
                for shard in missing:
                    hf_hub_download(repo_id=fallback_repo, filename=shard, cache_dir=cache_dir, local_dir=str(model_dir))
                missing = sorted({f for f in idx["weight_map"].values() if not (model_dir / f).is_file()})
        if missing:
            raise FileNotFoundError(f"{model_dir}: shards missing: {missing}")
    backbone = model_dir / "backbone"
    if not (backbone / "config.json").is_file() or not (backbone / "tokenizer.json").is_file():
        local_bb = Path(__file__).parent.parent / "backbone"
        if (local_bb / "config.json").is_file() and (local_bb / "tokenizer.json").is_file():
            backbone = local_bb
        else:
            raise FileNotFoundError(f"{backbone}: needs config.json and tokenizer.json")
    cfg = release_config(model_dir)
    if not isinstance(cfg, dict):
        cfg = {}
    audio_cfg = cfg.get("audio")
    mimi_from_cfg = audio_cfg.get("codec") if isinstance(audio_cfg, dict) else cfg.get("codec")
    mimi = mimi or os.environ.get("ORQANTA_VOICE_MIMI_DIR") or mimi_from_cfg or MIMI_REPO

    spk_cfg = cfg.get("speaker_encoder")
    ecapa_from_cfg = spk_cfg.get("repo") if isinstance(spk_cfg, dict) else (spk_cfg if isinstance(spk_cfg, str) else None)
    ecapa = ecapa or os.environ.get("ORQANTA_VOICE_ECAPA_DIR") or ecapa_from_cfg or ECAPA_REPO
    out = {
        "ckpt": str(model_dir if weights[0] != "model.pt" else model_dir / "model.pt"),
        "backbone_dir": str(backbone),
        "mimi_dir": snapshot(mimi, MIMI_FILES, MIMI_PATTERNS, cache_dir, None, local_files_only),
        "ecapa_dir": snapshot(ecapa, ECAPA_FILES, ECAPA_PATTERNS, cache_dir, None, local_files_only),
    }
    out["voices_json"] = voices_file(model_dir)      # None when the release ships no named voices
    if include_model_config:
        for name in (RELEASE_CONFIG,):
            cfg_p = model_dir / name
            if cfg_p.is_file():
                out["model_config"] = str(cfg_p)
                break
        if "model_config" not in out:
            for p_cfg in model_dir.glob("*_config.json"):
                out["model_config"] = str(p_cfg)
                break
        if "model_config" not in out:
            cfg_p = model_dir / "config.json"
            if cfg_p.is_file():
                out["model_config"] = str(cfg_p)
    return out


def voices_file(model_dir):
    """<release>/voices/voices.json if it lists any voice, else None (the stub ships empty)."""
    p = Path(model_dir) / "voices" / "voices.json"
    if not p.is_file():
        return None
    d = json.loads(p.read_text())
    return str(p) if (d.get("voices") if isinstance(d, dict) else d) else None


if __name__ == "__main__":
    import sys
    print(json.dumps(resolve(sys.argv[1]), indent=1))
