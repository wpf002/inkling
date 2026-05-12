import json
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SELF_REPORT_ITEMS_PATH = REPO_ROOT / "content" / "self_report" / "items.json"
ROUNDS_DIR = REPO_ROOT / "content" / "rounds"
ROUND_MANIFEST_PATH = ROUNDS_DIR / "manifest.json"


@lru_cache
def load_self_report_items() -> list[dict]:
    raw = json.loads(SELF_REPORT_ITEMS_PATH.read_text())
    return raw["items"]


def valid_item_ids() -> set[str]:
    return {item["id"] for item in load_self_report_items()}


@lru_cache
def load_round_manifest() -> dict:
    return json.loads(ROUND_MANIFEST_PATH.read_text())


def valid_round_ids() -> set[str]:
    return {r["id"] for r in load_round_manifest()["rounds"]}


@lru_cache
def load_round_gambles(round_id: str) -> dict:
    """Load the gambles definition for a round.

    Round-agnostic: any round may publish a `gambles.json` here. Raises
    FileNotFoundError if the round has none.
    """
    path = ROUNDS_DIR / round_id / "gambles.json"
    return json.loads(path.read_text())


def round_content_filename(round_id: str) -> str | None:
    for r in load_round_manifest()["rounds"]:
        if r["id"] == round_id:
            return r.get("content_file")
    return None


@lru_cache
def load_round_content(round_id: str) -> dict:
    """Load whatever content file the manifest declares for a round.

    Round-agnostic: the manifest names the file (e.g. `gambles.json`,
    `trials.json`); this just reads it. Raises FileNotFoundError if the
    manifest does not name one or the file is missing.
    """
    fname = round_content_filename(round_id)
    if not fname:
        raise FileNotFoundError(round_id)
    return json.loads((ROUNDS_DIR / round_id / fname).read_text())


def manifest_rounds_in_order() -> list[dict]:
    return list(load_round_manifest()["rounds"])


def constructs_for_round(round_id: str) -> list[str]:
    for r in load_round_manifest()["rounds"]:
        if r["id"] == round_id:
            return list(r.get("constructs", []))
    return []
