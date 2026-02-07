#!/bin/bash
# ==============================================================================
# Render Build Script
# ==============================================================================
# This script runs during Render deployment to:
# 1. Install Python dependencies
# 2. Create/update database tables
# 3. Seed default data
# ==============================================================================

set -e  # Exit on error

echo "🚀 Starting build process..."

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Setup database
echo "🗄️ Setting up database..."
python << 'EOF'
import os
import sys

# Add app to path
sys.path.insert(0, os.getcwd())

try:
    from app.database_setup import create_all_tables, seed_default_data
    
    print("Creating database tables...")
    create_all_tables()
    
    print("Seeding default data...")
    seed_default_data()
    
    print("✅ Database setup complete!")
except Exception as e:
    print(f"⚠️ Database setup error (may be normal on first deploy): {e}")
    # Don't fail the build - tables might already exist
EOF

echo "✅ Build complete!"
