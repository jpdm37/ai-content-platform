"""Add video generation tables

Revision ID: 006_video_tables
Revises: 005_social_tables
Create Date: 2024-01-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '006_video_tables'
down_revision = '005_social_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    op.execute("CREATE TYPE videostatus AS ENUM ('pending', 'generating_audio', 'generating_avatar', 'generating_video', 'processing', 'completed', 'failed', 'cancelled')")
    op.execute("CREATE TYPE voiceprovider AS ENUM ('elevenlabs', 'openai', 'azure')")
    op.execute("CREATE TYPE videoaspectratio AS ENUM ('1:1', '9:16', '16:9', '4:5')")
    
    # Create generated_videos table
    op.create_table('generated_videos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=True),
        sa.Column('lora_model_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('script', sa.Text(), nullable=False),
        sa.Column('voice_provider', postgresql.ENUM('elevenlabs', 'openai', 'azure', name='voiceprovider', create_type=False), default='elevenlabs'),
        sa.Column('voice_id', sa.String(100), nullable=True),
        sa.Column('voice_name', sa.String(100), nullable=True),
        sa.Column('voice_settings', sa.JSON(), nullable=True),
        sa.Column('avatar_image_url', sa.Text(), nullable=True),
        sa.Column('avatar_prompt', sa.Text(), nullable=True),
        sa.Column('use_lora', sa.Boolean(), default=True),
        sa.Column('aspect_ratio', postgresql.ENUM('1:1', '9:16', '16:9', '4:5', name='videoaspectratio', create_type=False), default='9:16'),
        sa.Column('resolution', sa.String(20), default='1080x1920'),
        sa.Column('fps', sa.Integer(), default=30),
        sa.Column('background_color', sa.String(20), default='#000000'),
        sa.Column('background_image_url', sa.Text(), nullable=True),
        sa.Column('expression', sa.String(50), default='neutral'),
        sa.Column('head_movement', sa.String(50), default='natural'),
        sa.Column('eye_contact', sa.Boolean(), default=True),
        sa.Column('status', postgresql.ENUM('pending', 'generating_audio', 'generating_avatar', 'generating_video', 'processing', 'completed', 'failed', 'cancelled', name='videostatus', create_type=False), default='pending'),
        sa.Column('progress_percent', sa.Integer(), default=0),
        sa.Column('audio_url', sa.Text(), nullable=True),
        sa.Column('audio_duration_seconds', sa.Float(), nullable=True),
        sa.Column('avatar_image_generated_url', sa.Text(), nullable=True),
        sa.Column('video_url', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processing_started_at', sa.DateTime(), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(), nullable=True),
        sa.Column('replicate_audio_id', sa.String(255), nullable=True),
        sa.Column('replicate_video_id', sa.String(255), nullable=True),
        sa.Column('audio_cost_usd', sa.Float(), default=0.0),
        sa.Column('video_cost_usd', sa.Float(), default=0.0),
        sa.Column('total_cost_usd', sa.Float(), default=0.0),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lora_model_id'], ['lora_models.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_generated_videos_id'), 'generated_videos', ['id'], unique=False)
    op.create_index(op.f('ix_generated_videos_user_id'), 'generated_videos', ['user_id'], unique=False)
    
    # Create video_templates table
    op.create_table('video_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('voice_provider', postgresql.ENUM('elevenlabs', 'openai', 'azure', name='voiceprovider', create_type=False), default='elevenlabs'),
        sa.Column('voice_id', sa.String(100), nullable=True),
        sa.Column('voice_settings', sa.JSON(), nullable=True),
        sa.Column('aspect_ratio', postgresql.ENUM('1:1', '9:16', '16:9', '4:5', name='videoaspectratio', create_type=False), default='9:16'),
        sa.Column('resolution', sa.String(20), default='1080x1920'),
        sa.Column('expression', sa.String(50), default='neutral'),
        sa.Column('head_movement', sa.String(50), default='natural'),
        sa.Column('background_color', sa.String(20), default='#000000'),
        sa.Column('background_image_url', sa.Text(), nullable=True),
        sa.Column('script_template', sa.Text(), nullable=True),
        sa.Column('preview_thumbnail_url', sa.Text(), nullable=True),
        sa.Column('preview_video_url', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_templates_id'), 'video_templates', ['id'], unique=False)
    
    # Create voice_clones table
    op.create_table('voice_clones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('provider', postgresql.ENUM('elevenlabs', 'openai', 'azure', name='voiceprovider', create_type=False), default='elevenlabs'),
        sa.Column('provider_voice_id', sa.String(255), nullable=True),
        sa.Column('sample_audio_urls', sa.JSON(), nullable=True),
        sa.Column('gender', sa.String(20), nullable=True),
        sa.Column('age_range', sa.String(20), nullable=True),
        sa.Column('accent', sa.String(50), nullable=True),
        sa.Column('is_ready', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('times_used', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_voice_clones_id'), 'voice_clones', ['id'], unique=False)
    op.create_index(op.f('ix_voice_clones_user_id'), 'voice_clones', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_voice_clones_user_id'), table_name='voice_clones')
    op.drop_index(op.f('ix_voice_clones_id'), table_name='voice_clones')
    op.drop_table('voice_clones')
    
    op.drop_index(op.f('ix_video_templates_id'), table_name='video_templates')
    op.drop_table('video_templates')
    
    op.drop_index(op.f('ix_generated_videos_user_id'), table_name='generated_videos')
    op.drop_index(op.f('ix_generated_videos_id'), table_name='generated_videos')
    op.drop_table('generated_videos')
    
    op.execute('DROP TYPE IF EXISTS videostatus')
    op.execute('DROP TYPE IF EXISTS voiceprovider')
    op.execute('DROP TYPE IF EXISTS videoaspectratio')
