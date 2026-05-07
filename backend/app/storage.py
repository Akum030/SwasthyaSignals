"""Disk persistence for cached SwasthyaSignals snapshots."""

from __future__ import annotations

from pathlib import Path
import json


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
SNAPSHOT_PATH = DATA_DIR / "latest_snapshot.json"
HISTORY_PATH = DATA_DIR / "snapshot_history.jsonl"


def load_snapshot() -> dict[str, object] | None:
    """Load the last stored snapshot from disk if it exists."""

    if not SNAPSHOT_PATH.exists():
        return None
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def save_snapshot(snapshot: dict[str, object]) -> None:
    """Persist the current snapshot and append a small history record."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(
        json.dumps(snapshot, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    history_record = {
        "generated_at": snapshot.get("generated_at"),
        "item_count": snapshot.get("item_count"),
        "signal_count": snapshot.get("signal_count"),
    }
    with HISTORY_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, ensure_ascii=True))
        handle.write("\n")
