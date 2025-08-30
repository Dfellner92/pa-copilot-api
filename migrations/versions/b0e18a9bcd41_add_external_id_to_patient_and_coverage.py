"""add external_id to patient and coverage

Revision ID: b0e18a9bcd41
Revises: 7b84e83c0a80
Create Date: 2025-08-29 22:53:08.135252

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('patients', sa.Column('external_id', sa.String(length=64), nullable=True))
    op.add_column('coverages', sa.Column('external_id', sa.String(length=64), nullable=True))
    op.create_index('ix_patients_external_id', 'patients', ['external_id'])
    op.create_index('ix_coverages_external_id', 'coverages', ['external_id'])
    op.create_unique_constraint('uq_patients_external_id', 'patients', ['external_id'])
    op.create_unique_constraint('uq_coverages_external_id', 'coverages', ['external_id'])
    op.alter_column('patients', 'external_id', nullable=False)
    op.alter_column('coverages', 'external_id', nullable=False)

def downgrade():
    op.drop_constraint('uq_coverages_external_id', 'coverages', type_='unique')
    op.drop_constraint('uq_patients_external_id', 'patients', type_='unique')
    op.drop_index('ix_coverages_external_id', table_name='coverages')
    op.drop_index('ix_patients_external_id', table_name='patients')
    op.drop_column('coverages', 'external_id')
    op.drop_column('patients', 'external_id')