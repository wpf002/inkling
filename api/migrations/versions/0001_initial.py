"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-11

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anonymous_token", sa.String(length=64), nullable=False),
        sa.Column("consent", postgresql.JSONB(), nullable=False),
        sa.Column(
            "age_attested",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("anonymous_token", name="uq_sessions_anonymous_token"),
    )
    op.create_index(
        "ix_sessions_anonymous_token", "sessions", ["anonymous_token"], unique=False
    )

    op.create_table(
        "self_reports",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_id", sa.String(length=32), nullable=False),
        sa.Column("response", sa.Integer(), nullable=False),
        sa.Column(
            "answered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_self_reports_session_id", "self_reports", ["session_id"], unique=False
    )

    op.create_table(
        "round_events",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("round", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("t_ms", sa.BigInteger(), nullable=False),
    )
    op.create_index(
        "ix_round_events_session_id", "round_events", ["session_id"], unique=False
    )

    op.create_table(
        "inferences",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("construct", sa.String(length=64), nullable=False),
        sa.Column("tier", sa.String(length=16), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_inferences_session_id", "inferences", ["session_id"], unique=False
    )

    op.create_table(
        "share_cards",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("image_path", sa.String(length=512), nullable=False),
        sa.Column("headline", sa.String(length=256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_share_cards_session_id", "share_cards", ["session_id"], unique=False
    )

    op.create_table(
        "research_optins",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opted_in_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_research_optins_session_id",
        "research_optins",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_research_optins_session_id", table_name="research_optins")
    op.drop_table("research_optins")
    op.drop_index("ix_share_cards_session_id", table_name="share_cards")
    op.drop_table("share_cards")
    op.drop_index("ix_inferences_session_id", table_name="inferences")
    op.drop_table("inferences")
    op.drop_index("ix_round_events_session_id", table_name="round_events")
    op.drop_table("round_events")
    op.drop_index("ix_self_reports_session_id", table_name="self_reports")
    op.drop_table("self_reports")
    op.drop_index("ix_sessions_anonymous_token", table_name="sessions")
    op.drop_table("sessions")
