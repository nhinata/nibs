import os
from pathlib import Path


def cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "nibs"


def usage_log():
    if os.environ.get("NIBS_LOG"):
        return Path(os.environ["NIBS_LOG"])
    base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(base) / "nibs" / "usage.jsonl"
