"""create video_jobs table

Revision ID: ea1fedd1683a
Revises: 
Create Date: 2026-10-12 12:40:11.022765

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel  # noqa: F401 — necessário para sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ea1fedd1683a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "video_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("prompt", sa.String(length=2000), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "PROCESSING", "COMPLETED", "FAILED", name="jobstatus"),
            nullable=False,
        ),
        sa.Column("output_path", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("video_jobs")
