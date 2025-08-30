"""add external_id to patient and coverage

Revision ID: b0e18a9bcd41
Revises: 7b84e83c0a80
Create Date: 2025-08-29 22:53:08.135252
"""

from alembic import op
import sqlalchemy as sa

# REQUIRED Alembic identifiers
revision = "b0e18a9bcd41"
down_revision = "7b84e83c0a80"
branch_labels = None
depends_on = None


def upgrade():
    # 1) Add columns as NULLABLE first
    op.add_column("patients", sa.Column("external_id", sa.String(length=64), nullable=True))
    op.add_column("coverages", sa.Column("external_id", sa.String(length=64), nullable=True))

    # 2) Backfill with guaranteed-unique values so uniqueness/NOT NULL will succeed
    #    - patients.external_id := id::text (unique)
    op.execute("UPDATE patients SET external_id = id::text WHERE external_id IS NULL")
    #    - coverages.external_id := id::text (unique)  <-- do NOT use member_id (can have duplicates)
    op.execute("UPDATE coverages SET external_id = id::text WHERE external_id IS NULL")

    # 3) Make columns NOT NULL (now that everything is populated)
    op.alter_column("patients", "external_id", nullable=False)
    op.alter_column("coverages", "external_id", nullable=False)

    # 4) Add indexes + unique constraints AFTER backfill
    op.create_index("ix_patients_external_id", "patients", ["external_id"])
    op.create_index("ix_coverages_external_id", "coverages", ["external_id"])
    op.create_unique_constraint("uq_patients_external_id", "patients", ["external_id"])
    op.create_unique_constraint("uq_coverages_external_id", "coverages", ["external_id"])

    # (Optional) If you want faster lookup by member_id for coverages, add a non-unique index:
    # op.create_index("ix_coverages_member_id", "coverages", ["member_id"], unique=False)


def downgrade():
    # Drop constraints/indexes first
    op.drop_constraint("uq_coverages_external_id", "coverages", type_="unique")
    op.drop_constraint("uq_patients_external_id", "patients", type_="unique")
    op.drop_index("ix_coverages_external_id", table_name="coverages")
    op.drop_index("ix_patients_external_id", table_name="patients")

    # Then drop columns
    op.drop_column("coverages", "external_id")
    op.drop_column("patients", "external_id")
