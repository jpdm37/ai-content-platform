"""Add tier 1 feature tables (studio, brand voice, analytics)

Revision ID: 007_tier1_features
Revises: 006_video_tables
Create Date: 2024-01-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '007_tier1_features'
down_revision = '006_video_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========== Studio Tables ==========
    
    # Create enums
    op.execute("CREATE TYPE studioprojectstatus AS ENUM ('draft', 'generating', 'completed', 'partial', 'failed')")
    op.execute("CREATE TYPE contenttype AS ENUM ('caption', 'image', 'video', 'hashtags', 'hook', 'cta')")
    
    # Studio projects
    op.create_table('studio_projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('brief', sa.Text(), nullable=False),
        sa.Column('target_platforms', sa.JSON(), default=list),
        sa.Column('content_types', sa.JSON(), default=list),
        sa.Column('tone', sa.String(50), default='professional'),
        sa.Column('num_variations', sa.Integer(), default=3),
        sa.Column('lora_model_id', sa.Integer(), nullable=True),
        sa.Column('include_video', sa.Boolean(), default=False),
        sa.Column('video_duration', sa.String(20), default='30s'),
        sa.Column('status', postgresql.ENUM('draft', 'generating', 'completed', 'partial', 'failed', name='studioprojectstatus', create_type=False), default='draft'),
        sa.Column('progress_percent', sa.Integer(), default=0),
        sa.Column('current_step', sa.String(100), nullable=True),
        sa.Column('captions_generated', sa.Integer(), default=0),
        sa.Column('images_generated', sa.Integer(), default=0),
        sa.Column('videos_generated', sa.Integer(), default=0),
        sa.Column('total_cost_usd', sa.Float(), default=0.0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lora_model_id'], ['lora_models.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_studio_projects_user_id', 'studio_projects', ['user_id'])
    
    # Studio assets
    op.create_table('studio_assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('content_type', postgresql.ENUM('caption', 'image', 'video', 'hashtags', 'hook', 'cta', name='contenttype', create_type=False), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('media_url', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('platform_optimized', sa.JSON(), nullable=True),
        sa.Column('variation_number', sa.Integer(), default=1),
        sa.Column('is_favorite', sa.Boolean(), default=False),
        sa.Column('is_selected', sa.Boolean(), default=False),
        sa.Column('user_rating', sa.Integer(), nullable=True),
        sa.Column('ai_model_used', sa.String(100), nullable=True),
        sa.Column('prompt_used', sa.Text(), nullable=True),
        sa.Column('generation_params', sa.JSON(), nullable=True),
        sa.Column('cost_usd', sa.Float(), default=0.0),
        sa.Column('status', sa.String(20), default='completed'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['studio_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_studio_assets_project_id', 'studio_assets', ['project_id'])
    
    # Studio templates
    op.create_table('studio_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('brief_template', sa.Text(), nullable=True),
        sa.Column('target_platforms', sa.JSON(), default=list),
        sa.Column('content_types', sa.JSON(), default=list),
        sa.Column('tone', sa.String(50), default='professional'),
        sa.Column('num_variations', sa.Integer(), default=3),
        sa.Column('include_video', sa.Boolean(), default=False),
        sa.Column('preview_image_url', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('times_used', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ========== Brand Voice Tables ==========
    
    # Brand voices
    op.create_table('brand_voices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=False),
        sa.Column('is_trained', sa.Boolean(), default=False),
        sa.Column('training_status', sa.String(50), default='pending'),
        sa.Column('training_examples', sa.JSON(), default=list),
        sa.Column('example_count', sa.Integer(), default=0),
        sa.Column('characteristics', sa.JSON(), nullable=True),
        sa.Column('voice_prompt', sa.Text(), nullable=True),
        sa.Column('default_strength', sa.Float(), default=0.8),
        sa.Column('times_used', sa.Integer(), default=0),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('user_satisfaction_avg', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('trained_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('brand_id')
    )
    
    # Voice examples
    op.create_table('voice_examples',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('brand_voice_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=True),
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('analysis', sa.JSON(), nullable=True),
        sa.Column('is_high_quality', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['brand_voice_id'], ['brand_voices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Voice generations (for feedback tracking)
    op.create_table('voice_generations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('brand_voice_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('generated_content', sa.Text(), nullable=False),
        sa.Column('voice_strength', sa.Float(), default=0.8),
        sa.Column('user_rating', sa.Integer(), nullable=True),
        sa.Column('feedback_notes', sa.Text(), nullable=True),
        sa.Column('voice_match_score', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['brand_voice_id'], ['brand_voices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('voice_generations')
    op.drop_table('voice_examples')
    op.drop_table('brand_voices')
    op.drop_table('studio_templates')
    op.drop_table('studio_assets')
    op.drop_index('ix_studio_projects_user_id', table_name='studio_projects')
    op.drop_table('studio_projects')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS studioprojectstatus')
    op.execute('DROP TYPE IF EXISTS contenttype')
