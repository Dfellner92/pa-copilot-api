"""add external_id to patient and coverage

Revision ID: b0e18a9bcd41
Revises: 7b84e83c0a80
Create Date: 2025-08-29 22:53:08.135252
"""

from alembic import op
import sqlalchemy as sa

# --- REQUIRED BY ALEMBIC ---
revision = "b0e18a9bcd41"
down_revision = "7b84e83c0a80"  # <- keep this as your previous rev id
branch_labels = None
depends_on = None
# ---------------------------

def upgrade():
    # 1) Add columns (nullable initially)
    op.add_column("patients", sa.Column("external_id", sa.String(length=64), nullable=True))
    op.add_column("coverages", sa.Column("external_id", sa.String(length=64), nullable=True))

    # 2) Create indexes (unique constraints allow multiple NULLs, so this is safe before backfill)
    op.create_index("ix_patients_external_id", "patients", ["external_id"])
    op.create_index("ix_coverages_external_id", "coverages", ["external_id"])
    op.create_unique_constraint("uq_patients_external_id", "patients", ["external_id"])
    op.create_unique_constraint("uq_coverages_external_id", "coverages", ["external_id"])

    # 3) Backfill any NULLs so NOT NULL will succeed
    #    - For patients, external_id := id::text (guaranteed unique)
    op.execute("""
        UPDATE patients
        SET external_id = id::text
        WHERE external_id IS NULL
    """)

    #    - For coverages, prefer member_id if present; otherwise id::text
    op.execute("""
        UPDATE coverages
        SET external_id = COALESCE(NULLIF(member_id, ''), id::text)
        WHERE external_id IS NULL
    """)

    # 4) Enforce NOT NULL after backfill
    op.alter_column("patients", "external_id", nullable=False)
    op.alter_column("coverages", "external_id", nullable=False)

def downgrade():
    op.drop_constraint("uq_coverages_external_id", "coverages", type_="unique")
    op.drop_constraint("uq_patients_external_id", "patients", type_="unique")
    op.drop_index("ix_coverages_external_id", table_name="coverages")
    op.drop_index("ix_patients_external_id", table_name="patients")
    op.drop_column("coverages", "external_id")
    op.drop_column("patients", "external_id")
