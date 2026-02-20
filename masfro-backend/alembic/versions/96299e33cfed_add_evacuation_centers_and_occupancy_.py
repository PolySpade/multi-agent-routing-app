"""add evacuation_centers and occupancy_log tables

Revision ID: 96299e33cfed
Revises: 6643d7a3d4a9
Create Date: 2026-02-09 19:08:57.051280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96299e33cfed'
down_revision: Union[str, Sequence[str], None] = '6643d7a3d4a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create evacuation_centers and evacuation_occupancy_log tables."""
    op.create_table(
        'evacuation_centers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_occupancy', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('type', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('suitability', sa.String(200), nullable=True),
        sa.Column('barangay', sa.String(100), nullable=True),
        sa.Column('operator', sa.String(200), nullable=True),
        sa.Column('contact', sa.String(200), nullable=True),
        sa.Column('facilities', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('idx_center_name', 'evacuation_centers', ['name'])
    op.create_index('idx_center_barangay', 'evacuation_centers', ['barangay'])
    op.create_index('idx_center_status', 'evacuation_centers', ['status'])

    op.create_table(
        'evacuation_occupancy_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('center_id', sa.Integer(), nullable=False),
        sa.Column('occupancy', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(30), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['center_id'], ['evacuation_centers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_occupancy_center_recorded', 'evacuation_occupancy_log', ['center_id', sa.text('recorded_at DESC')])


def downgrade() -> None:
    """Drop evacuation tables."""
    op.drop_index('idx_occupancy_center_recorded', table_name='evacuation_occupancy_log')
    op.drop_table('evacuation_occupancy_log')
    op.drop_index('idx_center_status', table_name='evacuation_centers')
    op.drop_index('idx_center_barangay', table_name='evacuation_centers')
    op.drop_index('idx_center_name', table_name='evacuation_centers')
    op.drop_table('evacuation_centers')
