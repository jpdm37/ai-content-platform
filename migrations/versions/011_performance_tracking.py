"""Add performance tracking fields

Revision ID: 011_performance_tracking
Revises: 010_ab_testing
Create Date: 2024-02-06

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011_performance_tracking'
down_revision = '010_ab_testing'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to publishing_logs table for performance tracking
    op.add_column('publishing_logs', sa.Column('user_id', sa.Integer(), nullable=True))
    op.add_column('publishing_logs', sa.Column('account_id', sa.Integer(), nullable=True))
    op.add_column('publishing_logs', sa.Column('platform', sa.String(50), nullable=True))
    op.add_column('publishing_logs', sa.Column('platform_post_id', sa.String(255), nullable=True))
    op.add_column('publishing_logs', sa.Column('post_url', sa.Text(), nullable=True))
    op.add_column('publishing_logs', sa.Column('caption', sa.Text(), nullable=True))
    op.add_column('publishing_logs', sa.Column('published_at', sa.DateTime(), nullable=True))
    op.add_column('publishing_logs', sa.Column('engagement_data', sa.JSON(), nullable=True))
    op.add_column('publishing_logs', sa.Column('metrics_updated_at', sa.DateTime(), nullable=True))
    
    # Add foreign keys
    op.create_foreign_key(
        'fk_publishing_logs_user_id',
        'publishing_logs', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_publishing_logs_account_id',
        'publishing_logs', 'social_accounts',
        ['account_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add index for user_id
    op.create_index('ix_publishing_logs_user_id', 'publishing_logs', ['user_id'])


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_publishing_logs_user_id', 'publishing_logs')
    
    # Remove foreign keys
    op.drop_constraint('fk_publishing_logs_account_id', 'publishing_logs', type_='foreignkey')
    op.drop_constraint('fk_publishing_logs_user_id', 'publishing_logs', type_='foreignkey')
    
    # Remove columns
    op.drop_column('publishing_logs', 'metrics_updated_at')
    op.drop_column('publishing_logs', 'engagement_data')
    op.drop_column('publishing_logs', 'published_at')
    op.drop_column('publishing_logs', 'caption')
    op.drop_column('publishing_logs', 'post_url')
    op.drop_column('publishing_logs', 'platform_post_id')
    op.drop_column('publishing_logs', 'platform')
    op.drop_column('publishing_logs', 'account_id')
    op.drop_column('publishing_logs', 'user_id')
