"""Phase 3 schema changes

Adds:
  - `daily_spend` table for the Overreach cost cap (one row per UTC date)
  - `share_cards`: drops `image_path`, adds `image_dimensions` and
    `inference_id` (nullable FK to inferences, ON DELETE SET NULL)

share_cards is reshaped because Phase 3 generates the card client-side
via html2canvas — no server-side image bytes, no object storage. We
record metadata only.

Revision id is intentionally short: alembic_version.version_num is
VARCHAR(32) by default, and a longer name overflows on Postgres
(sqlite silently truncates, so the engine tests do not catch it).

Revision ID: 0002_phase3_reveal
Revises: 0001_initial
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_phase3_reveal"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_spend",
        sa.Column("date", sa.Date(), primary_key=True, nullable=False),
        sa.Column(
            "total_usd",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("call_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    with op.batch_alter_table("share_cards") as batch:
        batch.drop_column("image_path")
        batch.add_column(
            sa.Column("image_dimensions", sa.String(length=16), nullable=False, server_default="1080x1920")
        )
        batch.add_column(
            sa.Column("inference_id", sa.BigInteger(), nullable=True)
        )
        batch.create_foreign_key(
            "fk_share_cards_inference_id",
            "inferences",
            ["inference_id"],
            ["id"],
            ondelete="SET NULL",
        )
    # Drop the server_default once data is in — keep the column NOT NULL
    # but rely on application code to set the dimensions explicitly.
    with op.batch_alter_table("share_cards") as batch:
        batch.alter_column("image_dimensions", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("share_cards") as batch:
        batch.drop_constraint("fk_share_cards_inference_id", type_="foreignkey")
        batch.drop_column("inference_id")
        batch.drop_column("image_dimensions")
        batch.add_column(sa.Column("image_path", sa.String(length=512), nullable=False, server_default=""))
    with op.batch_alter_table("share_cards") as batch:
        batch.alter_column("image_path", server_default=None)
    op.drop_table("daily_spend")
