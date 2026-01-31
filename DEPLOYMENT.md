# AI Content Platform - Complete Deployment Guide

This guide covers deploying the full-stack AI content platform to production using Render (recommended), with alternatives for other platforms.

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [External Service Setup](#2-external-service-setup)
3. [Deploy to Render (Recommended)](#3-deploy-to-render)
4. [Deploy to Railway (Alternative)](#4-deploy-to-railway)
5. [Deploy to VPS (DigitalOcean/AWS)](#5-deploy-to-vps)
6. [Post-Deployment Configuration](#6-post-deployment-configuration)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Prerequisites

### Required Accounts

Create accounts on these services (all have free tiers):

| Service | Purpose | Sign Up |
|---------|---------|---------|
| **Render** | Hosting | https://render.com |
| **OpenAI** | Content generation | https://platform.openai.com |
| **Replicate** | Image/video AI | https://replicate.com |
| **Stripe** | Payments | https://stripe.com |
| **ElevenLabs** | Text-to-speech | https://elevenlabs.io |
| **Resend** or **SendGrid** | Email | https://resend.com |

### Optional (for Social Media)

| Service | Purpose | Sign Up |
|---------|---------|---------|
| Twitter Developer | Twitter posting | https://developer.twitter.com |
| Meta Developer | Instagram/Facebook | https://developers.facebook.com |
| LinkedIn Developer | LinkedIn posting | https://developer.linkedin.com |

---

## 2. External Service Setup

### 2.1 OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Click **"Create new secret key"**
3. Name it "AI Content Platform"
4. Copy and save the key (starts with `sk-`)

**Cost:** ~$0.01-0.03 per generation

### 2.2 Replicate API Token

1. Go to https://replicate.com/account/api-tokens
2. Click **"Create token"**
3. Copy the token (starts with `r8_`)

**Cost:** ~$0.003-0.05 per image/video

### 2.3 Stripe Setup

#### Create Products & Prices

1. Go to https://dashboard.stripe.com/products
2. Click **"Add product"** for each tier:

**Creator Plan ($19/month)**
```
Name: Creator Plan
Price: $19.00 USD / month
```

**Pro Plan ($49/month)**
```
Name: Pro Plan  
Price: $49.00 USD / month
```

**Agency Plan ($149/month)**
```
Name: Agency Plan
Price: $149.00 USD / month
```

3. After creating each, copy the **Price ID** (starts with `price_`)

#### Get API Keys

1. Go to https://dashboard.stripe.com/apikeys
2. Copy:
   - **Publishable key** (starts with `pk_`)
   - **Secret key** (starts with `sk_`)

#### Create Webhook (after deployment)

1. Go to https://dashboard.stripe.com/webhooks
2. Click **"Add endpoint"**
3. URL: `https://your-domain.com/api/v1/billing/webhook`
4. Select events:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
   - `invoice.payment_failed`
5. Copy the **Webhook signing secret** (starts with `whsec_`)

### 2.4 ElevenLabs API Key

1. Go to https://elevenlabs.io/app/settings/api-keys
2. Click **"Create API Key"**
3. Copy the key

**Cost:** ~$0.30 per 1000 characters

### 2.5 Email Service (Resend)

1. Go to https://resend.com/api-keys
2. Click **"Create API Key"**
3. Copy the key

**Or use SendGrid:**
1. Go to https://app.sendgrid.com/settings/api_keys
2. Create key with "Mail Send" permissions

---

## 3. Deploy to Render (Recommended)

Render offers the easiest deployment with a free tier.

### 3.1 Prepare Your Repository

1. Create a new GitHub repository
2. Upload the project files:

```bash
# Clone or extract the project
unzip ai-content-platform.zip
cd ai-content-platform

# Initialize git
git init
git add .
git commit -m "Initial commit"

# Push to GitHub
git remote add origin https://github.com/YOUR_USERNAME/ai-content-platform.git
git branch -M main
git push -u origin main
```

### 3.2 Create Render Services

#### Option A: One-Click Deploy (Blueprint)

1. Go to https://render.com/deploy
2. Connect your GitHub repository
3. Render will detect `render.yaml` and create all services

#### Option B: Manual Setup

**Step 1: Create PostgreSQL Database**

1. Go to Render Dashboard → **New** → **PostgreSQL**
2. Configure:
   ```
   Name: ai-content-db
   Database: ai_content
   User: ai_content_user
   Region: Oregon (US West)
   Plan: Free (or Starter $7/mo for production)
   ```
3. Click **Create Database**
4. Copy the **Internal Database URL** (for backend)
5. Copy the **External Database URL** (for migrations)

**Step 2: Create Redis Instance**

1. Go to Render Dashboard → **New** → **Redis**
2. Configure:
   ```
   Name: ai-content-redis
   Region: Oregon (US West)
   Plan: Free (or Starter $10/mo)
   ```
3. Copy the **Internal Redis URL**

**Step 3: Create Backend Web Service**

1. Go to Render Dashboard → **New** → **Web Service**
2. Connect your GitHub repository
3. Configure:
   ```
   Name: ai-content-api
   Region: Oregon (US West)
   Branch: main
   Root Directory: (leave empty)
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   Plan: Free (or Starter $7/mo)
   ```

4. Add Environment Variables (click **Advanced** → **Add Environment Variable**):

```bash
# Database (use Internal URL from Step 1)
DATABASE_URL=postgresql://ai_content_user:PASSWORD@ai-content-db.internal:5432/ai_content

# Redis (use Internal URL from Step 2)
REDIS_URL=redis://ai-content-redis.internal:6379

# Security
SECRET_KEY=generate-a-64-char-random-string-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AI Services
OPENAI_API_KEY=sk-your-openai-key
REPLICATE_API_TOKEN=r8_your-replicate-token
ELEVENLABS_API_KEY=your-elevenlabs-key

# Stripe
STRIPE_SECRET_KEY=sk_live_your-stripe-secret
STRIPE_PUBLISHABLE_KEY=pk_live_your-stripe-publishable
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret
STRIPE_PRICE_ID_CREATOR=price_creator_id
STRIPE_PRICE_ID_PRO=price_pro_id
STRIPE_PRICE_ID_AGENCY=price_agency_id

# Email
RESEND_API_KEY=re_your-resend-key
# Or for SendGrid:
# SENDGRID_API_KEY=SG.your-sendgrid-key
EMAIL_FROM=noreply@yourdomain.com

# Frontend URL (update after frontend deploy)
FRONTEND_URL=https://ai-content-app.onrender.com

# Environment
ENVIRONMENT=production
```

5. Click **Create Web Service**

**Step 4: Create Celery Worker**

1. Go to Render Dashboard → **New** → **Background Worker**
2. Connect the same repository
3. Configure:
   ```
   Name: ai-content-worker
   Region: Oregon (US West)
   Branch: main
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: celery -A app.worker worker --loglevel=info
   Plan: Free (or Starter $7/mo)
   ```
4. Add the **same environment variables** as the backend
5. Click **Create Background Worker**

**Step 5: Create Frontend Static Site**

1. Go to Render Dashboard → **New** → **Static Site**
2. Connect the same repository
3. Configure:
   ```
   Name: ai-content-app
   Branch: main
   Root Directory: frontend
   Build Command: npm install && npm run build
   Publish Directory: frontend/dist
   ```

4. Add Environment Variable:
   ```
   VITE_API_URL=https://ai-content-api.onrender.com/api/v1
   ```

5. Click **Create Static Site**

### 3.3 Run Database Migrations

After the backend deploys successfully:

1. Go to your backend service → **Shell**
2. Run:
   ```bash
   alembic upgrade head
   ```

Or use the External Database URL locally:
```bash
DATABASE_URL="postgresql://user:pass@host:5432/db" alembic upgrade head
```

### 3.4 Update Stripe Webhook

1. Go to Stripe Dashboard → Webhooks
2. Update endpoint URL to: `https://ai-content-api.onrender.com/api/v1/billing/webhook`

### 3.5 Configure Custom Domain (Optional)

**Backend:**
1. Go to your API service → **Settings** → **Custom Domains**
2. Add: `api.yourdomain.com`
3. Add DNS CNAME record pointing to Render

**Frontend:**
1. Go to your frontend service → **Settings** → **Custom Domains**
2. Add: `app.yourdomain.com`
3. Add DNS CNAME record pointing to Render

---

## 4. Deploy to Railway (Alternative)

Railway is another excellent option with a simpler UX.

### 4.1 Setup

1. Go to https://railway.app
2. Click **"Start a New Project"**
3. Select **"Deploy from GitHub repo"**
4. Connect your repository

### 4.2 Add Services

Railway will auto-detect the project. Add:

1. **PostgreSQL** - Click "New" → "Database" → "PostgreSQL"
2. **Redis** - Click "New" → "Database" → "Redis"

### 4.3 Configure Backend

1. Click on the main service
2. Go to **Variables** tab
3. Add all environment variables (same as Render)
4. Railway auto-injects `DATABASE_URL` and `REDIS_URL`

### 4.4 Add Frontend

1. Click **"New"** → **"GitHub Repo"**
2. Set Root Directory: `frontend`
3. Add variable: `VITE_API_URL=https://your-backend.up.railway.app/api/v1`

---

## 5. Deploy to VPS (DigitalOcean/AWS)

For more control, deploy to a VPS.

### 5.1 Create Server

**DigitalOcean:**
1. Create Droplet: Ubuntu 22.04, $12/mo (2GB RAM)
2. Add SSH key

**AWS EC2:**
1. Launch t3.small instance with Ubuntu 22.04
2. Configure security group (ports 22, 80, 443)

### 5.2 Initial Server Setup

SSH into your server:

```bash
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3-pip python3-venv postgresql postgresql-contrib redis-server nginx certbot python3-certbot-nginx nodejs npm git

# Create app user
adduser --disabled-password appuser
usermod -aG sudo appuser
```

### 5.3 Setup PostgreSQL

```bash
sudo -u postgres psql

CREATE DATABASE ai_content;
CREATE USER ai_content_user WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE ai_content TO ai_content_user;
\q
```

### 5.4 Deploy Application

```bash
# Switch to app user
su - appuser

# Clone repository
git clone https://github.com/YOUR_USERNAME/ai-content-platform.git
cd ai-content-platform

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
cat > .env << 'EOF'
DATABASE_URL=postgresql://ai_content_user:your-secure-password@localhost:5432/ai_content
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-64-char-secret-key
OPENAI_API_KEY=sk-your-key
REPLICATE_API_TOKEN=r8_your-token
ELEVENLABS_API_KEY=your-key
STRIPE_SECRET_KEY=sk_live_your-key
STRIPE_PUBLISHABLE_KEY=pk_live_your-key
STRIPE_WEBHOOK_SECRET=whsec_your-secret
STRIPE_PRICE_ID_CREATOR=price_xxx
STRIPE_PRICE_ID_PRO=price_xxx
STRIPE_PRICE_ID_AGENCY=price_xxx
RESEND_API_KEY=re_your-key
EMAIL_FROM=noreply@yourdomain.com
FRONTEND_URL=https://yourdomain.com
ENVIRONMENT=production
EOF

# Run migrations
alembic upgrade head

# Build frontend
cd frontend
npm install
npm run build
cd ..
```

### 5.5 Setup Systemd Services

**Backend Service:**
```bash
sudo cat > /etc/systemd/system/ai-content-api.service << 'EOF'
[Unit]
Description=AI Content Platform API
After=network.target postgresql.service redis.service

[Service]
User=appuser
Group=appuser
WorkingDirectory=/home/appuser/ai-content-platform
Environment="PATH=/home/appuser/ai-content-platform/venv/bin"
EnvironmentFile=/home/appuser/ai-content-platform/.env
ExecStart=/home/appuser/ai-content-platform/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```

**Worker Service:**
```bash
sudo cat > /etc/systemd/system/ai-content-worker.service << 'EOF'
[Unit]
Description=AI Content Platform Worker
After=network.target postgresql.service redis.service

[Service]
User=appuser
Group=appuser
WorkingDirectory=/home/appuser/ai-content-platform
Environment="PATH=/home/appuser/ai-content-platform/venv/bin"
EnvironmentFile=/home/appuser/ai-content-platform/.env
ExecStart=/home/appuser/ai-content-platform/venv/bin/celery -A app.worker worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```

**Start Services:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-content-api ai-content-worker
sudo systemctl start ai-content-api ai-content-worker
```

### 5.6 Setup Nginx

```bash
sudo cat > /etc/nginx/sites-available/ai-content << 'EOF'
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Frontend
    location / {
        root /home/appuser/ai-content-platform/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/ai-content /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5.7 Setup SSL

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## 6. Post-Deployment Configuration

### 6.1 Verify Deployment

1. **Backend Health:** Visit `https://your-api-url/health`
2. **Frontend:** Visit `https://your-app-url`
3. **API Docs:** Visit `https://your-api-url/docs`

### 6.2 Create Admin User

Use the API or database directly:

```bash
# Via API - register normally then update in DB
psql $DATABASE_URL -c "UPDATE users SET is_superuser = true WHERE email = 'admin@yourdomain.com';"
```

### 6.3 Test Key Flows

1. **Registration:** Create a new account
2. **Email Verification:** Check email delivery
3. **Subscription:** Test Stripe checkout (use test mode first)
4. **Content Generation:** Generate an image
5. **Video Creation:** Create a talking head video
6. **Social Posting:** Connect a social account

### 6.4 Setup Monitoring (Recommended)

**Sentry (Error Tracking):**
1. Create account at https://sentry.io
2. Add to requirements.txt: `sentry-sdk[fastapi]`
3. Add to app/main.py:
```python
import sentry_sdk
sentry_sdk.init(dsn="your-sentry-dsn", environment="production")
```

**Uptime Monitoring:**
- Use https://uptimerobot.com (free)
- Monitor: `https://your-api-url/health`

---

## 7. Troubleshooting

### Common Issues

**Database Connection Failed:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

**Migrations Failed:**
```bash
# Check current revision
alembic current

# Reset if needed (CAUTION: loses data)
alembic downgrade base
alembic upgrade head
```

**Celery Worker Not Processing:**
```bash
# Check Redis connection
redis-cli ping

# Check worker logs
sudo journalctl -u ai-content-worker -f
```

**Stripe Webhooks Failing:**
1. Check webhook signing secret is correct
2. Verify endpoint URL is accessible
3. Check Stripe webhook logs in dashboard

**Email Not Sending:**
1. Verify API key is correct
2. Check sender domain is verified
3. Review email service logs

### Logs

**Render:**
- Go to service → **Logs** tab

**VPS:**
```bash
# API logs
sudo journalctl -u ai-content-api -f

# Worker logs
sudo journalctl -u ai-content-worker -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Support

If you encounter issues:
1. Check the logs first
2. Search error messages
3. Review API documentation at `/docs`
4. Check external service status pages

---

## Quick Reference

### Environment Variables Checklist

```bash
# Required
DATABASE_URL=✓
REDIS_URL=✓
SECRET_KEY=✓
OPENAI_API_KEY=✓
REPLICATE_API_TOKEN=✓
STRIPE_SECRET_KEY=✓
STRIPE_PUBLISHABLE_KEY=✓
STRIPE_WEBHOOK_SECRET=✓
STRIPE_PRICE_ID_CREATOR=✓
STRIPE_PRICE_ID_PRO=✓
STRIPE_PRICE_ID_AGENCY=✓

# Optional but Recommended
ELEVENLABS_API_KEY=✓
RESEND_API_KEY=✓
EMAIL_FROM=✓
FRONTEND_URL=✓

# Social Media (as needed)
TWITTER_CLIENT_ID=
TWITTER_CLIENT_SECRET=
INSTAGRAM_APP_ID=
INSTAGRAM_APP_SECRET=
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
```

### Useful Commands

```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Start dev server
uvicorn app.main:app --reload

# Start Celery worker
celery -A app.worker worker --loglevel=info

# Start Celery beat (scheduler)
celery -A app.worker beat --loglevel=info
```

---

## Estimated Costs

### Render (Recommended)

| Service | Free Tier | Production |
|---------|-----------|------------|
| Web Service | Free (750 hrs/mo) | $7/mo |
| Background Worker | Free | $7/mo |
| PostgreSQL | Free (90 days) | $7/mo |
| Redis | Free | $10/mo |
| Static Site | Free | Free |
| **Total** | **Free** | **~$31/mo** |

### External Services

| Service | Free Tier | Typical Usage |
|---------|-----------|---------------|
| OpenAI | $5 credit | $10-50/mo |
| Replicate | $5 credit | $20-100/mo |
| ElevenLabs | 10k chars/mo | $5-22/mo |
| Stripe | Free | 2.9% + $0.30/txn |

**Total Estimated:** $30-100/month for a small-medium deployment

---

Congratulations! Your AI Content Platform is now deployed! 🚀
