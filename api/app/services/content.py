import json
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SELF_REPORT_ITEMS_PATH = REPO_ROOT / "content" / "self_report" / "items.json"


@lru_cache
def load_self_report_items() -> list[dict]:
    raw = json.loads(SELF_REPORT_ITEMS_PATH.read_text())
    return raw["items"]


def valid_item_ids() -> set[str]:
    return {item["id"] for item in load_self_report_items()}
