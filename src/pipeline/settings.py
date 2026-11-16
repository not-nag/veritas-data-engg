"""Load ignored local settings without evaluating shell expressions."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def load_env():
    file = ROOT / '.env'
    if file.exists():
        for line in file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            name, value = line.split('=', 1)
            os.environ.setdefault(name.strip(), value.strip().strip('\"\''))

load_env()
