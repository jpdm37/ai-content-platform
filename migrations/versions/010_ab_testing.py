"""Add AB testing tables

Revision ID: 010_ab_testing
Revises: 009_onboarding_templates
Create Date: 2024-02-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_ab_testing'
down_revision = '009_onboarding_templates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create AB tests table
    op.create_table(
        'ab_tests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('test_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), server_default='draft'),
        sa.Column('goal_metric', sa.String(50), server_default='engagement_rate'),
        sa.Column('min_sample_size', sa.Integer(), server_default='100'),
        sa.Column('confidence_level', sa.Float(), server_default='0.95'),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('auto_end_on_significance', sa.Boolean(), server_default='true'),
        sa.Column('winner_variation_id', sa.Integer(), nullable=True),
        sa.Column('is_significant', sa.Boolean(), server_default='false'),
        sa.Column('p_value', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ab_tests_user_id', 'ab_tests', ['user_id'])
    op.create_index('ix_ab_tests_status', 'ab_tests', ['status'])
    
    # Create AB test variations table
    op.create_table(
        'ab_test_variations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('test_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('is_control', sa.Boolean(), server_default='false'),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('content_data', sa.JSON(), nullable=True),
        sa.Column('impressions', sa.Integer(), server_default='0'),
        sa.Column('engagements', sa.Integer(), server_default='0'),
        sa.Column('clicks', sa.Integer(), server_default='0'),
        sa.Column('conversions', sa.Integer(), server_default='0'),
        sa.Column('engagement_rate', sa.Float(), server_default='0.0'),
        sa.Column('click_rate', sa.Float(), server_default='0.0'),
        sa.Column('conversion_rate', sa.Float(), server_default='0.0'),
        sa.Column('traffic_percent', sa.Integer(), server_default='50'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['test_id'], ['ab_tests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ab_test_variations_test_id', 'ab_test_variations', ['test_id'])


def downgrade() -> None:
    # Drop tables
    op.drop_index('ix_ab_test_variations_test_id', 'ab_test_variations')
    op.drop_table('ab_test_variations')
    
    op.drop_index('ix_ab_tests_status', 'ab_tests')
    op.drop_index('ix_ab_tests_user_id', 'ab_tests')
    op.drop_table('ab_tests')
