"""add settings, app units, announcements and weather cache

Revision ID: 9f1c2d3e4a5b
Revises: d83393f0361c
Create Date: 2026-11-15 10:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from src.models.types import UTCDateTime

# revision identifiers, used by Alembic.
revision: str = "9f1c2d3e4a5b"
down_revision: str | Sequence[str] | None = "d83393f0361c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("updated_at", UTCDateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "app_units",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", UTCDateTime(timezone=True), nullable=False),
        sa.Column("updated_at", UTCDateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
        sa.UniqueConstraint("order"),
    )

    op.create_table(
        "announcements",
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("TICKER", "FEED", "BOTH", name="announcementkind"),
            nullable=False,
        ),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("starts_at", UTCDateTime(timezone=True), nullable=True),
        sa.Column("expires_at", UTCDateTime(timezone=True), nullable=True),
        sa.Column("author_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", UTCDateTime(timezone=True), nullable=False),
        sa.Column("updated_at", UTCDateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_id"], ["admin_profiles.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("announcements", schema=None) as batch_op:
        batch_op.create_index(
            "ix_announcements_active_priority",
            ["is_active", "priority"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_announcements_expires_at"),
            ["expires_at"],
            unique=False,
        )

    op.create_table(
        "weather_forecasts",
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("api", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("fetched_at", UTCDateTime(timezone=True), nullable=False),
        sa.Column("expires_at", UTCDateTime(timezone=True), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "location",
            "api",
            name="ux_weather_forecast_location_api",
        ),
    )
    with op.batch_alter_table("weather_forecasts", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_weather_forecasts_expires_at"),
            ["expires_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("weather_forecasts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_weather_forecasts_expires_at"))
    op.drop_table("weather_forecasts")

    with op.batch_alter_table("announcements", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_announcements_expires_at"))
        batch_op.drop_index("ix_announcements_active_priority")
    op.drop_table("announcements")

    op.drop_table("app_units")
    op.drop_table("app_settings")
