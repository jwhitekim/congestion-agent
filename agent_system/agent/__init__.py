from importlib import import_module

from .agent import ClaudeAgent, DEFAULT_MODEL, MODEL_ALIASES

__all__ = ["ClaudeAgent", "DEFAULT_MODEL", "MODEL_ALIASES", "domains"]


def __getattr__(name: str):
    if name == "domains":
        return import_module(".domains", __name__)
    raise AttributeError(f"module 'agent' has no attribute {name!r}")
