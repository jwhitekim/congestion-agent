from . import congestion


REGISTRY = {
    "congestion": congestion.get_domain,
}


def load(name: str) -> dict:
    if name not in REGISTRY:
        available = ", ".join(REGISTRY)
        raise ValueError(f"Unknown domain: {name}. Available: {available}")
    return REGISTRY[name]()
