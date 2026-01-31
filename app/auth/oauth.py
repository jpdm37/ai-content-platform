"""
OAuth service for Google and GitHub authentication
"""
import logging
from typing import Optional
import httpx
from authlib.integrations.starlette_client import OAuth

from app.core.config import get_settings
from app.models.auth_schemas import OAuthUserInfo, AuthProvider

settings = get_settings()
logger = logging.getLogger(__name__)

# Initialize OAuth
oauth = OAuth()

# Register Google OAuth
if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name='google',
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

# Register GitHub OAuth
if settings.github_client_id and settings.github_client_secret:
    oauth.register(
        name='github',
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        access_token_url='https://github.com/login/oauth/access_token',
        access_token_params=None,
        authorize_url='https://github.com/login/oauth/authorize',
        authorize_params=None,
        api_base_url='https://api.github.com/',
        client_kwargs={'scope': 'user:email'},
    )


class OAuthService:
    """Service for handling OAuth authentication"""
    
    @staticmethod
    def is_google_configured() -> bool:
        """Check if Google OAuth is configured"""
        return bool(settings.google_client_id and settings.google_client_secret)
    
    @staticmethod
    def is_github_configured() -> bool:
        """Check if GitHub OAuth is configured"""
        return bool(settings.github_client_id and settings.github_client_secret)
    
    @staticmethod
    def get_google_auth_url(redirect_uri: str) -> str:
        """Get Google OAuth authorization URL"""
        if not OAuthService.is_google_configured():
            raise ValueError("Google OAuth not configured")
        
        return (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={settings.google_client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope=openid%20email%20profile&"
            f"access_type=offline"
        )
    
    @staticmethod
    def get_github_auth_url(redirect_uri: str) -> str:
        """Get GitHub OAuth authorization URL"""
        if not OAuthService.is_github_configured():
            raise ValueError("GitHub OAuth not configured")
        
        return (
            f"https://github.com/login/oauth/authorize?"
            f"client_id={settings.github_client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"scope=user:email"
        )
    
    @staticmethod
    async def get_google_user_info(code: str, redirect_uri: str) -> Optional[OAuthUserInfo]:
        """Exchange code for token and get user info from Google"""
        try:
            async with httpx.AsyncClient() as client:
                # Exchange code for token
                token_response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": code,
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code"
                    }
                )
                token_data = token_response.json()
                
                if "error" in token_data:
                    logger.error(f"Google token error: {token_data}")
                    return None
                
                access_token = token_data.get("access_token")
                
                # Get user info
                user_response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                user_data = user_response.json()
                
                return OAuthUserInfo(
                    id=user_data["id"],
                    email=user_data["email"],
                    name=user_data.get("name"),
                    avatar_url=user_data.get("picture"),
                    provider=AuthProvider.GOOGLE
                )
                
        except Exception as e:
            logger.error(f"Error getting Google user info: {e}")
            return None
    
    @staticmethod
    async def get_github_user_info(code: str, redirect_uri: str) -> Optional[OAuthUserInfo]:
        """Exchange code for token and get user info from GitHub"""
        try:
            async with httpx.AsyncClient() as client:
                # Exchange code for token
                token_response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    data={
                        "code": code,
                        "client_id": settings.github_client_id,
                        "client_secret": settings.github_client_secret,
                        "redirect_uri": redirect_uri
                    },
                    headers={"Accept": "application/json"}
                )
                token_data = token_response.json()
                
                if "error" in token_data:
                    logger.error(f"GitHub token error: {token_data}")
                    return None
                
                access_token = token_data.get("access_token")
                
                # Get user info
                user_response = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                user_data = user_response.json()
                
                # Get user email (might be private)
                email = user_data.get("email")
                if not email:
                    emails_response = await client.get(
                        "https://api.github.com/user/emails",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Accept": "application/vnd.github.v3+json"
                        }
                    )
                    emails = emails_response.json()
                    # Find primary email
                    for e in emails:
                        if e.get("primary"):
                            email = e.get("email")
                            break
                    # Fallback to first verified email
                    if not email:
                        for e in emails:
                            if e.get("verified"):
                                email = e.get("email")
                                break
                
                if not email:
                    logger.error("Could not get email from GitHub")
                    return None
                
                return OAuthUserInfo(
                    id=str(user_data["id"]),
                    email=email,
                    name=user_data.get("name") or user_data.get("login"),
                    avatar_url=user_data.get("avatar_url"),
                    provider=AuthProvider.GITHUB
                )
                
        except Exception as e:
            logger.error(f"Error getting GitHub user info: {e}")
            return None


oauth_service = OAuthService()
