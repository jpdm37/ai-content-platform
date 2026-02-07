# 🚀 AI Content Platform

A full-stack SaaS platform for AI-powered content creation and social media management.

![Version](https://img.shields.io/badge/version-1.3.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![React](https://img.shields.io/badge/react-18+-blue)

## ✨ Features

### Content Creation
- 🤖 **AI Content Generation** - Create captions, hashtags, and posts with GPT-4
- 🖼️ **AI Image Generation** - Generate images with Stable Diffusion via Replicate
- 🎬 **Video Generation** - Create short-form videos
- 🎨 **Brand Voice Training** - Train AI to write in your brand's style

### Social Media Management
- 📅 **Content Calendar** - Visual planning with drag-and-drop
- 📱 **Multi-Platform Posting** - Instagram, Twitter, LinkedIn, Facebook, TikTok
- ⏰ **Smart Scheduling** - Best time recommendations
- 📊 **Performance Tracking** - Engagement analytics from connected accounts

### Business Features
- 💳 **Stripe Billing** - 4-tier subscription system
- 📈 **A/B Testing** - Test content variations with statistical significance
- 📧 **Email Digests** - Weekly performance summaries
- 👤 **User Onboarding** - Guided setup with templates

## 🚀 Quick Start

### Option 1: One-Command Setup (Recommended)

```bash
cd ai-content-platform
python setup.py
```

### Option 2: Docker

```bash
cd ai-content-platform
cp .env.example .env
# Edit .env with your API keys
docker-compose up
```

### Option 3: Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Setup database
python -c "from app.database_setup import create_all_tables, seed_default_data; create_all_tables(); seed_default_data()"

# Start backend
uvicorn app.main:app --reload --port 8000

# Start frontend (new terminal)
cd frontend && npm run dev
```

## 📋 Requirements

- Python 3.9+
- Node.js 18+
- PostgreSQL 13+
- Redis (optional, for background tasks)

### API Keys Needed

| Service | Required | Purpose |
|---------|----------|---------|
| OpenAI | Yes | Content generation |
| Replicate | Yes | Image generation |
| Stripe | For billing | Subscriptions |
| SMTP | For emails | Verification, digests |

## 📖 Documentation

- [Quick Start Guide](QUICK-START.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Production Readiness](PRODUCTION_READINESS.md)
- [API Docs](http://localhost:8000/docs) (when running)

## 📊 What's Included

| Component | Count |
|-----------|-------|
| Python Files | 104 |
| React Components | 47 |
| API Endpoints | 200+ |
| Database Tables | 20+ |
| Celery Tasks | 7 |

## 🔧 Configuration

See `.env.example` for all configuration options.

**Minimum required:**
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
SECRET_KEY=your-secret-key
OPENAI_API_KEY=sk-...
REPLICATE_API_TOKEN=r8_...
```

---

Built with ❤️ using Claude AI
