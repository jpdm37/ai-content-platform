# AI Content Platform

A full-stack SaaS platform for AI-powered content creation, featuring talking head video generation, LoRA avatar training, and social media scheduling.

## ✨ Features

- **AI Image Generation** - DALL-E and Flux models
- **LoRA Avatar Training** - 95%+ consistent AI avatars
- **Talking Head Videos** - Lip-synced AI presenter videos
- **Social Media Scheduling** - Twitter, Instagram, LinkedIn
- **Stripe Subscriptions** - 4-tier pricing

## 🚀 Quick Start

```bash
# Backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Fill in your API keys
alembic upgrade head
uvicorn app.main:app --reload

# Worker (new terminal)
celery -A app.worker worker --loglevel=info

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

## 📦 Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

See [DEPLOYMENT.md](DEPLOYMENT.md) for full deployment instructions.

## 🏗️ Tech Stack

- **Backend:** FastAPI, PostgreSQL, Redis, Celery
- **Frontend:** React 18, Tailwind CSS
- **AI:** OpenAI, Replicate, ElevenLabs
- **Payments:** Stripe

## 📄 License

MIT License
