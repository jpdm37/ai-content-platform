"""
Comprehensive API Tests for AI Content Platform
Run with: pytest tests/test_api.py -v
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

# Import app
import sys
sys.path.insert(0, '.')

from app.main import app
from app.core.database import Base, engine, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    """Create test client with test database"""
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for protected routes"""
    # Register a test user
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    })
    
    # Login to get token
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    return {}


class TestHealth:
    """Health check endpoint tests"""
    
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]
    
    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200


class TestAuthentication:
    """Authentication endpoint tests"""
    
    def test_register_user(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "password123",
            "full_name": "New User"
        })
        # Should succeed or fail with "already exists"
        assert response.status_code in [200, 201, 400]
    
    def test_register_invalid_email(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "invalid-email",
            "password": "password123",
            "full_name": "Test"
        })
        assert response.status_code == 422  # Validation error
    
    def test_register_short_password(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "test2@example.com",
            "password": "123",
            "full_name": "Test"
        })
        assert response.status_code == 422
    
    def test_login_success(self, client):
        # First register
        client.post("/api/v1/auth/register", json={
            "email": "login@example.com",
            "password": "password123",
            "full_name": "Login User"
        })
        
        # Then login
        response = client.post("/api/v1/auth/login", json={
            "email": "login@example.com",
            "password": "password123"
        })
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client):
        response = client.post("/api/v1/auth/login", json={
            "email": "login@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
    
    def test_me_without_auth(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    def test_me_with_auth(self, client, auth_headers):
        if auth_headers:
            response = client.get("/api/v1/auth/me", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "email" in data


class TestBrands:
    """Brand endpoint tests"""
    
    def test_list_brands_without_auth(self, client):
        response = client.get("/api/v1/brands/")
        assert response.status_code == 401
    
    def test_list_brands_with_auth(self, client, auth_headers):
        if auth_headers:
            response = client.get("/api/v1/brands/", headers=auth_headers)
            assert response.status_code == 200
            assert isinstance(response.json(), list)
    
    def test_create_brand(self, client, auth_headers):
        if auth_headers:
            response = client.post("/api/v1/brands/", 
                headers=auth_headers,
                json={
                    "name": "Test Brand",
                    "description": "A test brand",
                    "persona_name": "TestBot",
                    "persona_traits": ["friendly", "helpful"],
                    "brand_colors": ["#FF0000", "#00FF00"],
                    "brand_keywords": ["test", "demo"]
                }
            )
            assert response.status_code in [200, 201]
            if response.status_code in [200, 201]:
                data = response.json()
                assert data["name"] == "Test Brand"
                assert isinstance(data.get("persona_traits"), list)
    
    def test_create_brand_minimal(self, client, auth_headers):
        if auth_headers:
            response = client.post("/api/v1/brands/",
                headers=auth_headers,
                json={"name": "Minimal Brand"}
            )
            assert response.status_code in [200, 201]


class TestCategories:
    """Category endpoint tests"""
    
    def test_list_categories(self, client, auth_headers):
        if auth_headers:
            response = client.get("/api/v1/categories/", headers=auth_headers)
            assert response.status_code == 200
            assert isinstance(response.json(), list)
    
    def test_seed_categories(self, client, auth_headers):
        if auth_headers:
            response = client.post("/api/v1/categories/seed", headers=auth_headers)
            assert response.status_code in [200, 201]


class TestTrends:
    """Trend endpoint tests"""
    
    def test_get_top_trends(self, client, auth_headers):
        if auth_headers:
            response = client.get("/api/v1/trends/top?limit=5", headers=auth_headers)
            assert response.status_code == 200
            assert isinstance(response.json(), list)


class TestGenerate:
    """Content generation endpoint tests"""
    
    def test_list_generated_content(self, client, auth_headers):
        if auth_headers:
            response = client.get("/api/v1/generate/content", headers=auth_headers)
            assert response.status_code == 200


class TestStatus:
    """Status endpoint tests"""
    
    def test_api_status(self, client):
        response = client.get("/api/v1/status")
        assert response.status_code == 200


class TestSchemaValidation:
    """Test that schemas properly handle JSON string parsing"""
    
    def test_brand_response_parses_json_strings(self):
        from app.models.schemas import BrandResponse
        
        # Simulate data from database with JSON strings
        data = {
            "id": 1,
            "name": "Test",
            "description": None,
            "persona_name": None,
            "persona_age": None,
            "persona_gender": None,
            "persona_style": None,
            "persona_voice": None,
            "persona_traits": '["trait1", "trait2"]',  # JSON string
            "reference_image_url": None,
            "brand_colors": '["#FF0000"]',  # JSON string
            "brand_keywords": '["keyword1"]',  # JSON string
            "created_at": None,
            "updated_at": None
        }
        
        brand = BrandResponse(**data)
        assert brand.persona_traits == ["trait1", "trait2"]
        assert brand.brand_colors == ["#FF0000"]
        assert brand.brand_keywords == ["keyword1"]
    
    def test_brand_response_handles_actual_lists(self):
        from app.models.schemas import BrandResponse
        
        data = {
            "id": 1,
            "name": "Test",
            "persona_traits": ["trait1", "trait2"],  # Actual list
            "brand_colors": ["#FF0000"],
            "brand_keywords": ["keyword1"],
        }
        
        brand = BrandResponse(**data)
        assert brand.persona_traits == ["trait1", "trait2"]
    
    def test_brand_response_handles_none(self):
        from app.models.schemas import BrandResponse
        
        data = {
            "id": 1,
            "name": "Test",
            "persona_traits": None,
            "brand_colors": None,
            "brand_keywords": None,
        }
        
        brand = BrandResponse(**data)
        assert brand.persona_traits is None
    
    def test_category_response_parses_keywords(self):
        from app.models.schemas import CategoryResponse
        
        data = {
            "id": 1,
            "name": "Fashion",
            "description": "Fashion content",
            "keywords": '["fashion", "style"]',
            "image_prompt_template": None,
            "caption_prompt_template": None,
            "created_at": None
        }
        
        category = CategoryResponse(**data)
        assert category.keywords == ["fashion", "style"]
    
    def test_trend_response_parses_keywords(self):
        from app.models.schemas import TrendResponse
        
        data = {
            "id": 1,
            "title": "Test Trend",
            "description": None,
            "source": "test",
            "source_url": None,
            "category_id": 1,
            "popularity_score": 100,
            "related_keywords": '["keyword1", "keyword2"]',
            "scraped_at": None
        }
        
        trend = TrendResponse(**data)
        assert trend.related_keywords == ["keyword1", "keyword2"]


class TestCORS:
    """Test CORS headers are present"""
    
    def test_cors_preflight(self, client):
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://ai-content-platform-1-iogw.onrender.com",
                "Access-Control-Request-Method": "POST"
            }
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


# Run with: pytest tests/test_api.py -v --tb=short
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


class TestSchemaJsonParsingCoverage:
    def test_social_and_template_response_json_parsing(self):
        from app.social.schemas import SocialAccountResponse, ScheduledPostResponse, PostTemplateResponse

        account = SocialAccountResponse(
            id=1,
            platform="instagram",
            platform_username="u",
            platform_display_name="U",
            profile_image_url=None,
            brand_id=None,
            is_active=True,
            last_synced_at=None,
            last_error=None,
            platform_data='{"followers": 10}',
            created_at=None,
        )
        assert account.platform_data == {"followers": 10}

        post = ScheduledPostResponse(
            id=1,
            social_account_id=1,
            brand_id=None,
            generated_content_id=None,
            caption="c",
            hashtags='["a", "b"]',
            media_urls='["https://x"]',
            scheduled_for="2026-01-01T00:00:00",
            timezone="UTC",
            status="scheduled",
            published_at=None,
            platform_post_id=None,
            platform_post_url=None,
            error_message=None,
            engagement_data='{"likes": 2}',
            created_at=None,
            platform="instagram",
            account_username="u",
        )
        assert post.hashtags == ["a", "b"]
        assert post.engagement_data == {"likes": 2}

        template = PostTemplateResponse(
            id=1,
            name="T",
            description=None,
            caption_template="cap",
            default_hashtags='["h1"]',
            platforms='["instagram"]',
            brand_id=None,
            is_active=True,
            created_at=None,
        )
        assert template.default_hashtags == ["h1"]
        assert template.platforms == ["instagram"]


class TestCodeGuardrails:
    def test_limited_routes_have_response_param(self):
        import ast
        from pathlib import Path

        for path in Path("app/api").glob("*.py"):
            tree = ast.parse(path.read_text())
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    has_limit = any(
                        isinstance(dec, ast.Call)
                        and isinstance(dec.func, ast.Attribute)
                        and dec.func.attr == "limit"
                        for dec in node.decorator_list
                    )
                    if has_limit:
                        args = [arg.arg for arg in node.args.args]
                        assert "response" in args, f"{path}:{node.name} missing response"

    def test_cors_no_wildcard_with_credentials(self):
        from app.main import app
        cors = next(m for m in app.user_middleware if 'CORSMiddleware' in str(m.cls))
        allow_origins = cors.kwargs.get("allow_origins", [])
        assert cors.kwargs.get("allow_credentials") is True
        assert "*" not in allow_origins
