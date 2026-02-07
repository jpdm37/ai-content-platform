# 🚀 Pre-Deploy Checklist

Before deploying to Render, make sure you have these ready:

## ✅ Required API Keys (Get these BEFORE deploying)

### 1. OpenAI API Key (REQUIRED for AI features)
- Go to: https://platform.openai.com/api-keys
- Create a new API key
- Save as: `OPENAI_API_KEY`

### 2. Replicate API Token (REQUIRED for image generation)
- Go to: https://replicate.com/account/api-tokens
- Create a new token
- Save as: `REPLICATE_API_TOKEN`

### 3. Stripe Keys (REQUIRED for billing - can use test keys)
- Go to: https://dashboard.stripe.com/apikeys
- Get your **Secret key** → `STRIPE_SECRET_KEY`
- Get your **Publishable key** → `STRIPE_PUBLISHABLE_KEY`

### 4. Create Stripe Products (for subscriptions)
1. Go to: https://dashboard.stripe.com/products
2. Create 3 products:
   - **Creator** - $19/month → Save price ID as `STRIPE_PRICE_CREATOR`
   - **Pro** - $49/month → Save price ID as `STRIPE_PRICE_PRO`
   - **Agency** - $149/month → Save price ID as `STRIPE_PRICE_AGENCY`

---

## 📋 Deployment Steps

### Step 1: Push to GitHub
```bash
cd ai-content-platform
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/ai-content-platform.git
git push -u origin main
```

### Step 2: Deploy on Render
1. Go to https://render.com/dashboard
2. Click **New +** → **Blueprint**
3. Connect your GitHub repo
4. Select `ai-content-platform`
5. Click **Apply**

### Step 3: Add Environment Variables (CRITICAL!)
After Render creates the services, go to each service and add your API keys:

**For `ai-content-api` service:**
| Variable | Value |
|----------|-------|
| `OPENAI_API_KEY` | sk-... |
| `REPLICATE_API_TOKEN` | r8_... |
| `STRIPE_SECRET_KEY` | sk_test_... |
| `STRIPE_PUBLISHABLE_KEY` | pk_test_... |
| `STRIPE_PRICE_CREATOR` | price_... |
| `STRIPE_PRICE_PRO` | price_... |
| `STRIPE_PRICE_AGENCY` | price_... |
| `FRONTEND_URL` | https://ai-content-app.onrender.com |

**For `ai-content-worker` service:**
Copy the same variables from above.

### Step 4: Create Admin Account
After deployment, create your admin account:
```bash
curl -X POST https://ai-content-api.onrender.com/api/v1/admin/setup \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "your-secure-password", "name": "Admin"}'
```

### Step 5: Test the Deployment
1. Visit your frontend: https://ai-content-app.onrender.com
2. Register a new user
3. Try creating a brand
4. Test content generation

---

## ⚠️ Optional (Can add later)

### Email (for verification & digests)
| Variable | Value |
|----------|-------|
| `SMTP_HOST` | smtp.gmail.com |
| `SMTP_PORT` | 587 |
| `SMTP_USER` | your-email@gmail.com |
| `SMTP_PASSWORD` | your-app-password |

### Error Tracking
| Variable | Value |
|----------|-------|
| `SENTRY_DSN` | https://xxx@sentry.io/xxx |

### OAuth (Google/GitHub login)
| Variable | Value |
|----------|-------|
| `GOOGLE_CLIENT_ID` | ... |
| `GOOGLE_CLIENT_SECRET` | ... |
| `GITHUB_CLIENT_ID` | ... |
| `GITHUB_CLIENT_SECRET` | ... |

---

## 🔧 Troubleshooting

### "Module not found" error
- Check the build logs in Render
- Make sure requirements.txt is complete

### Database connection failed
- The DATABASE_URL is auto-configured by Render
- Check if the database service is running

### Frontend can't reach backend
- Verify VITE_API_URL is set correctly
- Check CORS in backend allows frontend URL

### Stripe webhooks not working
1. Go to Stripe Dashboard → Webhooks
2. Add endpoint: `https://ai-content-api.onrender.com/api/v1/billing/webhook`
3. Select events: `checkout.session.completed`, `customer.subscription.*`
4. Copy signing secret → `STRIPE_WEBHOOK_SECRET`

---

## 📊 Expected Services After Deploy

| Service | Type | URL |
|---------|------|-----|
| ai-content-db | PostgreSQL | (internal) |
| ai-content-redis | Redis | (internal) |
| ai-content-api | Web Service | https://ai-content-api.onrender.com |
| ai-content-worker | Background Worker | (no URL) |
| ai-content-scheduler | Background Worker | (no URL) |
| ai-content-app | Static Site | https://ai-content-app.onrender.com |

---

## 🎉 You're Ready!

Once deployed, your platform will have:
- ✅ User authentication (email + OAuth)
- ✅ 4-tier subscription billing
- ✅ AI content generation
- ✅ AI image generation
- ✅ Social media scheduling
- ✅ Content calendar
- ✅ Performance analytics
- ✅ Admin dashboard with feature flags

**Admin Dashboard:** https://ai-content-app.onrender.com/admin
