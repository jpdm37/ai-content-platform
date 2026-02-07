"""Add onboarding and template fields

Revision ID: 009_onboarding_templates
Revises: 008_admin_tables
Create Date: 2024-02-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_onboarding_templates'
down_revision = '008_admin_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add onboarding fields to users table
    op.add_column('users', sa.Column('onboarding_data', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('onboarding_completed', sa.Boolean(), default=False))
    op.add_column('users', sa.Column('email_preferences', sa.JSON(), nullable=True))
    
    # Add template fields to brands table
    op.add_column('brands', sa.Column('target_audience', sa.Text(), nullable=True))
    op.add_column('brands', sa.Column('is_demo', sa.Boolean(), default=False))
    op.add_column('brands', sa.Column('is_template', sa.Boolean(), default=False))
    op.add_column('brands', sa.Column('template_id', sa.String(100), nullable=True))


def downgrade() -> None:
    # Remove brand template fields
    op.drop_column('brands', 'template_id')
    op.drop_column('brands', 'is_template')
    op.drop_column('brands', 'is_demo')
    op.drop_column('brands', 'target_audience')
    
    # Remove user onboarding fields
    op.drop_column('users', 'email_preferences')
    op.drop_column('users', 'onboarding_completed')
    op.drop_column('users', 'onboarding_data')
