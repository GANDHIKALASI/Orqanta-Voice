"""Orqanta-Voice inference: fast streaming engine, voice registry with cached prefix KV, engine-internal guards, public API."""
__all__ = ["OrqantaVoiceTTS", "Engine", "EngineConfig", "Voice"]


def __getattr__(name):
    if name == "OrqantaVoiceTTS":
        from orqanta_voice.api import OrqantaVoiceTTS
        return OrqantaVoiceTTS
    if name in ("Engine", "EngineConfig"):
        from orqanta_voice import engine
        return getattr(engine, name)
    if name == "Voice":
        from orqanta_voice.prompt import Voice
        return Voice
    raise AttributeError(name)
