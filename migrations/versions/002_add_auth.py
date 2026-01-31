"""Add authentication tables and user_id to brands and content

Revision ID: 002_add_auth
Revises: 001_initial
Create Date: 2024-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_auth'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create auth_provider enum
    auth_provider_enum = sa.Enum('LOCAL', 'GOOGLE', 'GITHUB', name='authprovider')
    auth_provider_enum.create(op.get_bind(), checkfirst=True)
    
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_superuser', sa.Boolean(), nullable=True, default=False),
        sa.Column('auth_provider', sa.Enum('LOCAL', 'GOOGLE', 'GITHUB', name='authprovider'), nullable=True),
        sa.Column('oauth_id', sa.String(length=255), nullable=True),
        sa.Column('openai_api_key', sa.Text(), nullable=True),
        sa.Column('replicate_api_token', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Create refresh_tokens table
    op.create_table('refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=500), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_refresh_tokens_id'), 'refresh_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_token'), 'refresh_tokens', ['token'], unique=True)
    
    # Create email_verification_tokens table
    op.create_table('email_verification_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=500), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_verification_tokens_id'), 'email_verification_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_email_verification_tokens_token'), 'email_verification_tokens', ['token'], unique=True)
    
    # Create password_reset_tokens table
    op.create_table('password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=500), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_password_reset_tokens_id'), 'password_reset_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_password_reset_tokens_token'), 'password_reset_tokens', ['token'], unique=True)
    
    # Add user_id column to brands table
    op.add_column('brands', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_brands_user_id'), 'brands', ['user_id'], unique=False)
    op.create_foreign_key('fk_brands_user_id', 'brands', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    
    # Add user_id column to generated_content table
    op.add_column('generated_content', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_generated_content_user_id'), 'generated_content', ['user_id'], unique=False)
    op.create_foreign_key('fk_generated_content_user_id', 'generated_content', 'users', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # Remove foreign keys and columns from generated_content
    op.drop_constraint('fk_generated_content_user_id', 'generated_content', type_='foreignkey')
    op.drop_index(op.f('ix_generated_content_user_id'), table_name='generated_content')
    op.drop_column('generated_content', 'user_id')
    
    # Remove foreign keys and columns from brands
    op.drop_constraint('fk_brands_user_id', 'brands', type_='foreignkey')
    op.drop_index(op.f('ix_brands_user_id'), table_name='brands')
    op.drop_column('brands', 'user_id')
    
    # Drop auth tables
    op.drop_index(op.f('ix_password_reset_tokens_token'), table_name='password_reset_tokens')
    op.drop_index(op.f('ix_password_reset_tokens_id'), table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
    
    op.drop_index(op.f('ix_email_verification_tokens_token'), table_name='email_verification_tokens')
    op.drop_index(op.f('ix_email_verification_tokens_id'), table_name='email_verification_tokens')
    op.drop_table('email_verification_tokens')
    
    op.drop_index(op.f('ix_refresh_tokens_token'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    
    # Drop enum
    op.execute('DROP TYPE IF EXISTS authprovider')
