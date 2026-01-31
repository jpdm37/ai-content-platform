"""Add LoRA training tables

Revision ID: 003_lora_tables
Revises: 002_auth_tables
Create Date: 2024-01-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003_lora_tables'
down_revision = '002_auth_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create training status enum
    op.execute("CREATE TYPE trainingstatus AS ENUM ('pending', 'validating', 'uploading', 'training', 'completed', 'failed', 'cancelled')")
    op.execute("CREATE TYPE imagevalidationstatus AS ENUM ('pending', 'valid', 'invalid', 'processing')")
    
    # Create lora_models table
    op.create_table('lora_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('trigger_word', sa.String(length=100), nullable=False),
        sa.Column('base_model', sa.String(length=100), default='flux-dev'),
        sa.Column('training_steps', sa.Integer(), default=1000),
        sa.Column('learning_rate', sa.Float(), default=0.0004),
        sa.Column('lora_rank', sa.Integer(), default=16),
        sa.Column('resolution', sa.Integer(), default=1024),
        sa.Column('replicate_training_id', sa.String(length=255), nullable=True),
        sa.Column('replicate_model_owner', sa.String(length=255), nullable=True),
        sa.Column('replicate_model_name', sa.String(length=255), nullable=True),
        sa.Column('replicate_version', sa.String(length=255), nullable=True),
        sa.Column('lora_weights_url', sa.Text(), nullable=True),
        sa.Column('lora_weights_size_mb', sa.Float(), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'validating', 'uploading', 'training', 'completed', 'failed', 'cancelled', name='trainingstatus', create_type=False), default='pending'),
        sa.Column('progress_percent', sa.Integer(), default=0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('consistency_score', sa.Float(), nullable=True),
        sa.Column('test_images_generated', sa.Integer(), default=0),
        sa.Column('training_cost_usd', sa.Float(), nullable=True),
        sa.Column('training_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('training_started_at', sa.DateTime(), nullable=True),
        sa.Column('training_completed_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=False),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lora_models_id'), 'lora_models', ['id'], unique=False)
    op.create_index(op.f('ix_lora_models_user_id'), 'lora_models', ['user_id'], unique=False)
    op.create_index(op.f('ix_lora_models_brand_id'), 'lora_models', ['brand_id'], unique=False)
    
    # Create lora_reference_images table
    op.create_table('lora_reference_images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lora_model_id', sa.Integer(), nullable=False),
        sa.Column('original_url', sa.Text(), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('original_size_bytes', sa.Integer(), nullable=True),
        sa.Column('processed_url', sa.Text(), nullable=True),
        sa.Column('processed_width', sa.Integer(), nullable=True),
        sa.Column('processed_height', sa.Integer(), nullable=True),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('custom_caption', sa.Text(), nullable=True),
        sa.Column('face_detected', sa.Boolean(), default=False),
        sa.Column('face_confidence', sa.Float(), nullable=True),
        sa.Column('face_bbox', sa.JSON(), nullable=True),
        sa.Column('validation_status', postgresql.ENUM('pending', 'valid', 'invalid', 'processing', name='imagevalidationstatus', create_type=False), default='pending'),
        sa.Column('validation_errors', sa.JSON(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('image_type', sa.String(length=50), nullable=True),
        sa.Column('is_included_in_training', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['lora_model_id'], ['lora_models.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lora_reference_images_id'), 'lora_reference_images', ['id'], unique=False)
    op.create_index(op.f('ix_lora_reference_images_lora_model_id'), 'lora_reference_images', ['lora_model_id'], unique=False)
    
    # Create lora_generated_samples table
    op.create_table('lora_generated_samples',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lora_model_id', sa.Integer(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('negative_prompt', sa.Text(), nullable=True),
        sa.Column('seed', sa.Integer(), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=False),
        sa.Column('consistency_score', sa.Float(), nullable=True),
        sa.Column('face_similarity_score', sa.Float(), nullable=True),
        sa.Column('style_score', sa.Float(), nullable=True),
        sa.Column('lora_scale', sa.Float(), default=1.0),
        sa.Column('guidance_scale', sa.Float(), default=3.5),
        sa.Column('num_inference_steps', sa.Integer(), default=28),
        sa.Column('user_rating', sa.Integer(), nullable=True),
        sa.Column('user_feedback', sa.Text(), nullable=True),
        sa.Column('is_test_sample', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['lora_model_id'], ['lora_models.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lora_generated_samples_id'), 'lora_generated_samples', ['id'], unique=False)
    op.create_index(op.f('ix_lora_generated_samples_lora_model_id'), 'lora_generated_samples', ['lora_model_id'], unique=False)
    
    # Create lora_training_queue table
    op.create_table('lora_training_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lora_model_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('priority', sa.Integer(), default=0),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('queued_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('estimated_completion', sa.DateTime(), nullable=True),
        sa.Column('is_processing', sa.Boolean(), default=False),
        sa.ForeignKeyConstraint(['lora_model_id'], ['lora_models.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lora_model_id')
    )
    op.create_index(op.f('ix_lora_training_queue_user_id'), 'lora_training_queue', ['user_id'], unique=False)
    
    # Create lora_usage_logs table
    op.create_table('lora_usage_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lora_model_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('usage_type', sa.String(length=50), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('result_url', sa.Text(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('compute_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['lora_model_id'], ['lora_models.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lora_usage_logs_id'), 'lora_usage_logs', ['id'], unique=False)
    op.create_index(op.f('ix_lora_usage_logs_user_id'), 'lora_usage_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_lora_usage_logs_user_id'), table_name='lora_usage_logs')
    op.drop_index(op.f('ix_lora_usage_logs_id'), table_name='lora_usage_logs')
    op.drop_table('lora_usage_logs')
    
    op.drop_index(op.f('ix_lora_training_queue_user_id'), table_name='lora_training_queue')
    op.drop_table('lora_training_queue')
    
    op.drop_index(op.f('ix_lora_generated_samples_lora_model_id'), table_name='lora_generated_samples')
    op.drop_index(op.f('ix_lora_generated_samples_id'), table_name='lora_generated_samples')
    op.drop_table('lora_generated_samples')
    
    op.drop_index(op.f('ix_lora_reference_images_lora_model_id'), table_name='lora_reference_images')
    op.drop_index(op.f('ix_lora_reference_images_id'), table_name='lora_reference_images')
    op.drop_table('lora_reference_images')
    
    op.drop_index(op.f('ix_lora_models_brand_id'), table_name='lora_models')
    op.drop_index(op.f('ix_lora_models_user_id'), table_name='lora_models')
    op.drop_index(op.f('ix_lora_models_id'), table_name='lora_models')
    op.drop_table('lora_models')
    
    op.execute('DROP TYPE IF EXISTS imagevalidationstatus')
    op.execute('DROP TYPE IF EXISTS trainingstatus')
