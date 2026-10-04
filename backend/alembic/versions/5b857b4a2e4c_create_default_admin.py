"""Create default admin

Revision ID: 5b857b4a2e4c
Revises: dc9b10c40f1a
Create Date: 2026-10-03 19:53:38.476226

"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from src.core.config import settings
from src.core.security import hash_password

# revision identifiers, used by Alembic.
revision: str = "5b857b4a2e4c"
down_revision: str | Sequence[str] | None = "dc9b10c40f1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_LOGIN = settings.default_admin_login
DEFAULT_PASSWORD = settings.default_admin_password


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    count = bind.execute(sa.text("SELECT COUNT(*) FROM admin_profiles")).scalar_one()

    if count > 0:
        return

    now = datetime.now(UTC).isoformat()
    password_hash = hash_password(DEFAULT_PASSWORD)

    bind.execute(
        sa.text(
            """
        INSERT INTO admin_profiles
            (id, login, password_hash, email, is_active, is_default, created_at, updated_at)
        VALUES (:id, :login, :password_hash, NULL, :is_active, :is_default, :created_at, :updated_at)
        """
        ),
        {
            "id": uuid.uuid4().hex,
            "login": DEFAULT_LOGIN,
            "password_hash": password_hash,
            "is_active": True,
            "is_default": True,
            "created_at": now,
            "updated_at": now,
        },
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM admin_profiles "
            "WHERE login = :login AND is_default = :is_default"
        ),
        {"login": DEFAULT_LOGIN, "is_default": True},
    )
