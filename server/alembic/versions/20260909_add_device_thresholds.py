"""add thresholds column to devices

Revision ID: add_device_thresholds
Revises:
Create Date: 2026-09-09 01:15:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "add_device_thresholds"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "devices",
        sa.Column("thresholds", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    # backfill defaults
    op.execute("""
        UPDATE devices
        SET thresholds = jsonb_build_object('ph_min', 6.5, 'ph_max', 8.5)
        WHERE thresholds IS NULL;
        """)


def downgrade():
    op.drop_column("devices", "thresholds")
