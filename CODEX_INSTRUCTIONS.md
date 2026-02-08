# AI Content Platform - Codex/Copilot Instructions

## Project Overview
Full-stack AI content generation platform with:
- **Backend**: FastAPI (Python 3.11) at `/app`
- **Frontend**: React + Vite at `/frontend`
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Deployment**: Render.com (Backend: Web Service, Frontend: Static Site)

## Architecture

```
ai-content-platform/
├── app/
│   ├── api/          # FastAPI route handlers
│   ├── models/       # SQLAlchemy models + Pydantic schemas
│   ├── core/         # Config, database, security
│   ├── services/     # Business logic
│   └── main.py       # FastAPI app entry point
├── frontend/
│   └── src/
│       ├── pages/    # React components
│       ├── services/ # API client (api.js)
│       └── contexts/ # Auth context
└── tests/            # Pytest test suite
```

## Common Issues & Fixes

### 1. JSON String Parsing in Schemas
**Problem**: PostgreSQL stores JSON as TEXT strings, but Pydantic expects lists.
**Solution**: Add `@field_validator` with `parse_json_list()` helper.

```python
# In app/models/schemas.py
import json

def parse_json_list(v):
    if v is None: return None
    if isinstance(v, list): return v
    if isinstance(v, str):
        try: return json.loads(v)
        except: return []
    return []

class BrandResponse(BaseModel):
    persona_traits: Optional[List[str]] = None
    
    @field_validator('persona_traits', mode='before')
    @classmethod
    def parse_json(cls, v):
        return parse_json_list(v)
```

**Affected fields**: `persona_traits`, `brand_colors`, `brand_keywords`, `keywords`, `related_keywords`, `hashtags`, `generation_params`

### 2. CORS Configuration
**Problem**: 500 errors don't include CORS headers, appearing as CORS errors in browser.
**Solution**: Ensure proper CORS setup in `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,  # Must be set in environment
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Never use**: `allow_origins=["*"]` with `allow_credentials=True`

### 3. Rate Limiter Response Parameter
**Problem**: SlowAPI requires `response: Response` parameter in decorated functions.
**Solution**: Add parameter or disable rate limiting:

```python
# Option A: Add parameter
@limiter.limit("10/minute")
async def endpoint(request: Request, response: Response):
    pass

# Option B: Disable in config
rate_limit_enabled: bool = False
```

### 4. Frontend API Trailing Slashes
**Problem**: FastAPI redirects `/brands` to `/brands/`, losing CORS headers on POST.
**Solution**: Use trailing slashes in frontend API calls:

```javascript
// In frontend/src/services/api.js
export const brandsApi = {
  getAll: () => api.get('/brands/'),  // Note trailing slash
  create: (data) => api.post('/brands/', data),
};
```

### 5. Database Schema Mismatches
**Problem**: SQLAlchemy model has columns that don't exist in PostgreSQL.
**Solution**: Use `/fix-db` endpoint or Alembic migrations to add missing columns.

Common missing columns pattern:
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE brands ADD COLUMN IF NOT EXISTS persona_traits TEXT;
```

## Testing Commands

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Type checking
mypy app/ --ignore-missing-imports

# Linting
flake8 app/ --max-line-length=127
```

## Environment Variables Required

```
DATABASE_URL=postgresql://...
SECRET_KEY=your-secret-key
FRONTEND_URL=https://your-frontend.onrender.com
OPENAI_API_KEY=sk-...
REPLICATE_API_TOKEN=r8_...
```

## When Reviewing Code, Check For:

1. [ ] All Response schemas have JSON field validators
2. [ ] CORS allows the frontend URL
3. [ ] Rate-limited endpoints have `response: Response` parameter
4. [ ] Frontend API calls use correct paths (with trailing slashes for collections)
5. [ ] All database columns in models exist in actual tables
6. [ ] Authentication middleware properly validates tokens
7. [ ] Error handlers return proper HTTP status codes
8. [ ] Datetime fields have proper defaults or are Optional

## Auto-Fix Script

Run `python scripts/auto_fix.py --check` to detect common issues automatically.
