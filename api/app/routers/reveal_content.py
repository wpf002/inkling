"""Static content endpoints for the reveal levels (dismantle text used
in Level 4). These files are authored and committed under content/
and pass the lexicon check at build time."""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

REPO_ROOT = Path(__file__).resolve().parents[3]
DISMANTLE_PATH = REPO_ROOT / "content" / "reveal" / "dismantle.json"

router = APIRouter(prefix="/content", tags=["reveal-content"])


@router.get("/reveal-dismantle")
async def reveal_dismantle():
    try:
        return json.loads(DISMANTLE_PATH.read_text())
    except FileNotFoundError as e:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "dismantle content missing"
        ) from e
