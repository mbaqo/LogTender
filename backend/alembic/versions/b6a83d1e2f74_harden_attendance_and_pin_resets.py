"""harden attendance notes and guardian PIN resets

Revision ID: b6a83d1e2f74
Revises: 5b91174760ea
Create Date: 2026-05-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b6a83d1e2f74"
down_revision: Union[str, Sequence[str], None] = "5b91174760ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add auditable PIN-reset throttling and one attendance note per day."""
    op.execute("ALTER TYPE resetstatuses ADD VALUE IF NOT EXISTS 'COMPLETED'")
    op.execute("ALTER TYPE resetstatuses ADD VALUE IF NOT EXISTS 'LOCKED'")
    op.add_column(
        "guardian_pin_resets",
        sa.Column(
            "failed_verification_attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "guardian_pin_resets",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_attendance_notes_student_date",
        "attendance_notes",
        ["student_id", "attendance_date"],
    )


def downgrade() -> None:
    """Remove added columns and constraint; PostgreSQL enum labels remain."""
    op.drop_constraint(
        "uq_attendance_notes_student_date",
        "attendance_notes",
        type_="unique",
    )
    op.drop_column("guardian_pin_resets", "locked_at")
    op.drop_column("guardian_pin_resets", "failed_verification_attempts")
