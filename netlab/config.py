import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def env(name, default=None):
    value = os.getenv(name, default)
    if value is None:
        raise SystemExit(f"Variable manquante : {name} (voir .env.example)")
    return value


def read(path):
    return Path(path).read_text(encoding="utf-8")
