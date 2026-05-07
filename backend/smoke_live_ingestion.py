"""Run a live ingestion smoke test against public sources."""

from __future__ import annotations

import json

from app.snapshot import collect_snapshot


def main() -> None:
    """Print a compact snapshot summary for smoke validation."""

    snapshot = collect_snapshot()
    summary = {
        "generated_at": snapshot["generated_at"],
        "item_count": snapshot["item_count"],
        "signal_count": snapshot["signal_count"],
        "sources": [
            {
                "name": status["name"],
                "ok": status["ok"],
                "item_count": status["item_count"],
                "message": status["message"],
            }
            for status in snapshot["source_status"]
        ],
        "top_signal_titles": [
            signal["title"] for signal in snapshot["signals"][:5]
        ],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
