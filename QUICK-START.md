# 🚀 AI Content Platform - Quick Start Guide

## One-Command Setup

```bash
# Clone/extract the project, then:
cd ai-content-platform
python setup.py
```

That's it! The setup wizard will guide you through everything.

---

## Manual Setup (if you prefer)

### 1. Prerequisites

- **Python 3.9+**
- **PostgreSQL** (local or cloud like Supabase, Neon, Railway)
- **Redis** (optional, for background tasks)
- **Node.js 18+** (for frontend)

### 2. Create Database

```sql
-- In PostgreSQL
CREATE DATABASE ai_content_platform;
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

**Minimum required settings:**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/ai_content_platform
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=sk-...
REPLICATE_API_TOKEN=r8_...
```

### 4. Install Dependencies & Setup Database

```bash
# Backend
pip install -r requirements.txt

# Create all tables
python -c "from app.database_setup import create_all_tables, seed_default_data; create_all_tables(); seed_default_data()"

# Frontend
cd frontend
npm install
cd ..
```

### 5. Start the Application

**Terminal 1 - Backend:**
```bash
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - Background Workers (optional):**
```bash
celery -A app.worker worker --loglevel=info &
celery -A app.worker beat --loglevel=info
```

### 6. Access the Platform

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |
| Admin Panel | http://localhost:5173/admin |

---

## API Keys Needed

### Required for Core Features

| Service | Purpose | Get it from |
|---------|---------|-------------|
| OpenAI | AI content generation | https://platform.openai.com/api-keys |
| Replicate | Image generation | https://replicate.com/account/api-tokens |

### Required for Billing

| Service | Purpose | Get it from |
|---------|---------|-------------|
| Stripe | Payments | https://dashboard.stripe.com/apikeys |

### Optional Enhancements

| Service | Purpose | Get it from |
|---------|---------|-------------|
| Sentry | Error tracking | https://sentry.io |
| AWS S3 | File storage | https://aws.amazon.com |
| Google OAuth | Social login | https://console.cloud.google.com |
| Social APIs | Auto-posting | Platform developer portals |

---

## First Steps After Setup

### 1. Create Your First User

Visit http://localhost:5173/register and create an account.

### 2. Verify Email (Development)

In development, check the terminal output for the verification link, or use the API:

```bash
# Manually verify a user (replace user_id)
curl -X POST http://localhost:8000/api/v1/auth/verify-email?token=TOKEN
```

### 3. Create a Brand

1. Go to **Brands** in the sidebar
2. Click **Create Brand**
3. Fill in your brand details

### 4. Generate Content

1. Go to **Content Studio**
2. Click **Create Project**
3. Use AI to generate content

### 5. Connect Social Accounts (Optional)

1. Go to **Social Accounts**
2. Connect your platforms
3. Schedule posts from the **Calendar**

---

## Common Issues

### Database Connection Failed

```
Error: connection refused
```

**Solution:** Make sure PostgreSQL is running and the DATABASE_URL is correct.

### Module Not Found

```
ModuleNotFoundError: No module named 'xxx'
```

**Solution:** Run `pip install -r requirements.txt`

### Frontend Won't Start

```
Error: Cannot find module...
```

**Solution:** Run `cd frontend && npm install`

### Celery Tasks Not Running

Background tasks like email sending won't work without Celery.

**Solution:** Start Redis and Celery workers (see step 5).

---

## Production Deployment

See `DEPLOYMENT.md` for detailed deployment instructions for:
- Render
- Railway
- AWS
- DigitalOcean
- Heroku

---

## Support

- 📖 Full documentation in `PRODUCTION_READINESS.md`
- 🗺️ Feature roadmap in `ROADMAP.md`
- 🐛 Report issues via GitHub

---

## Quick Reference

### Useful Commands

```bash
# Start everything
uvicorn app.main:app --reload --port 8000  # Backend
cd frontend && npm run dev                  # Frontend

# Database
python -c "from app.database_setup import create_all_tables; create_all_tables()"
python -c "from app.database_setup import seed_default_data; seed_default_data()"

# Celery
celery -A app.worker worker --loglevel=info
celery -A app.worker beat --loglevel=info

# Create admin user
python -c "
from app.core.database import SessionLocal
from app.admin.models import AdminUser
from app.auth.security import get_password_hash

db = SessionLocal()
admin = AdminUser(
    email='admin@example.com',
    hashed_password=get_password_hash('admin123'),
    role='super_admin'
)
db.add(admin)
db.commit()
print('Admin created!')
"
```

### API Endpoints Overview

| Endpoint | Description |
|----------|-------------|
| `/api/v1/auth/*` | Authentication |
| `/api/v1/brands/*` | Brand management |
| `/api/v1/generate/*` | Content generation |
| `/api/v1/studio/*` | Content studio |
| `/api/v1/social/*` | Social media |
| `/api/v1/calendar/*` | Content calendar |
| `/api/v1/performance/*` | Analytics |
| `/api/v1/ab-tests/*` | A/B testing |
| `/api/v1/billing/*` | Subscriptions |

Full API docs at http://localhost:8000/docs
