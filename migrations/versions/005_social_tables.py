"""Add social media tables

Revision ID: 005_social_tables
Revises: 004_billing_tables
Create Date: 2024-01-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005_social_tables'
down_revision = '004_billing_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    op.execute("CREATE TYPE socialplatform AS ENUM ('twitter', 'instagram', 'linkedin', 'tiktok', 'facebook', 'threads')")
    op.execute("CREATE TYPE poststatus AS ENUM ('draft', 'scheduled', 'publishing', 'published', 'failed', 'cancelled')")
    
    # Create social_accounts table
    op.create_table('social_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=True),
        sa.Column('platform', postgresql.ENUM('twitter', 'instagram', 'linkedin', 'tiktok', 'facebook', 'threads', name='socialplatform', create_type=False), nullable=False),
        sa.Column('platform_user_id', sa.String(255), nullable=False),
        sa.Column('platform_username', sa.String(255), nullable=True),
        sa.Column('platform_display_name', sa.String(255), nullable=True),
        sa.Column('profile_image_url', sa.Text(), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('platform_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_social_accounts_id'), 'social_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_social_accounts_user_id'), 'social_accounts', ['user_id'], unique=False)
    op.create_index(op.f('ix_social_accounts_brand_id'), 'social_accounts', ['brand_id'], unique=False)
    
    # Create scheduled_social_posts table
    op.create_table('scheduled_social_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('social_account_id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=True),
        sa.Column('generated_content_id', sa.Integer(), nullable=True),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('hashtags', sa.JSON(), nullable=True),
        sa.Column('media_urls', sa.JSON(), nullable=True),
        sa.Column('platform_specific', sa.JSON(), nullable=True),
        sa.Column('scheduled_for', sa.DateTime(), nullable=False),
        sa.Column('timezone', sa.String(50), default='UTC'),
        sa.Column('status', postgresql.ENUM('draft', 'scheduled', 'publishing', 'published', 'failed', 'cancelled', name='poststatus', create_type=False), default='scheduled'),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('platform_post_id', sa.String(255), nullable=True),
        sa.Column('platform_post_url', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), default=0),
        sa.Column('engagement_data', sa.JSON(), nullable=True),
        sa.Column('last_engagement_sync', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['social_account_id'], ['social_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['generated_content_id'], ['generated_content.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scheduled_social_posts_id'), 'scheduled_social_posts', ['id'], unique=False)
    op.create_index(op.f('ix_scheduled_social_posts_user_id'), 'scheduled_social_posts', ['user_id'], unique=False)
    op.create_index(op.f('ix_scheduled_social_posts_social_account_id'), 'scheduled_social_posts', ['social_account_id'], unique=False)
    op.create_index(op.f('ix_scheduled_social_posts_scheduled_for'), 'scheduled_social_posts', ['scheduled_for'], unique=False)
    
    # Create post_templates table
    op.create_table('post_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('caption_template', sa.Text(), nullable=True),
        sa.Column('default_hashtags', sa.JSON(), nullable=True),
        sa.Column('platforms', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_post_templates_id'), 'post_templates', ['id'], unique=False)
    op.create_index(op.f('ix_post_templates_user_id'), 'post_templates', ['user_id'], unique=False)
    
    # Create publishing_logs table
    op.create_table('publishing_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scheduled_post_id', sa.Integer(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), default=1),
        sa.Column('attempted_at', sa.DateTime(), nullable=True),
        sa.Column('success', sa.Boolean(), default=False),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['scheduled_post_id'], ['scheduled_social_posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_publishing_logs_id'), 'publishing_logs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_publishing_logs_id'), table_name='publishing_logs')
    op.drop_table('publishing_logs')
    
    op.drop_index(op.f('ix_post_templates_user_id'), table_name='post_templates')
    op.drop_index(op.f('ix_post_templates_id'), table_name='post_templates')
    op.drop_table('post_templates')
    
    op.drop_index(op.f('ix_scheduled_social_posts_scheduled_for'), table_name='scheduled_social_posts')
    op.drop_index(op.f('ix_scheduled_social_posts_social_account_id'), table_name='scheduled_social_posts')
    op.drop_index(op.f('ix_scheduled_social_posts_user_id'), table_name='scheduled_social_posts')
    op.drop_index(op.f('ix_scheduled_social_posts_id'), table_name='scheduled_social_posts')
    op.drop_table('scheduled_social_posts')
    
    op.drop_index(op.f('ix_social_accounts_brand_id'), table_name='social_accounts')
    op.drop_index(op.f('ix_social_accounts_user_id'), table_name='social_accounts')
    op.drop_index(op.f('ix_social_accounts_id'), table_name='social_accounts')
    op.drop_table('social_accounts')
    
    op.execute('DROP TYPE IF EXISTS poststatus')
    op.execute('DROP TYPE IF EXISTS socialplatform')
