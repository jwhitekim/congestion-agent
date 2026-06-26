from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT_DIR / "agent_system"
WEB_DIR = ROOT_DIR / "web"
STATIC_DIR = WEB_DIR / "static"

UPLOAD_DIR = ROOT_DIR / "data" / "uploads"
OUTPUT_DIR = ROOT_DIR / "outputs"
RESULTS_DIR = OUTPUT_DIR / "results"
LOGS_DIR = ROOT_DIR / "logs"

__all__ = [
    "ROOT_DIR",
    "AGENT_DIR",
    "WEB_DIR",
    "STATIC_DIR",
    "UPLOAD_DIR",
    "OUTPUT_DIR",   
    "RESULTS_DIR",
    "LOGS_DIR",
]