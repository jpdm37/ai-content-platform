"""
Social Media Posting Service

Handles:
- OAuth connection to platforms
- Posting content (immediate and scheduled)
- Engagement tracking
- Best time to post analysis
"""
import logging
import httpx
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.social.models import (
    SocialAccount, ScheduledSocialPost, PublishingLog,
    SocialPlatform, PostStatus
)

logger = logging.getLogger(__name__)
settings = get_settings()


# ==================== Platform Clients ====================

class BaseSocialClient(ABC):
    """Base class for social media platform clients"""
    
    @abstractmethod
    async def post(
        self,
        account: SocialAccount,
        caption: str,
        media_urls: Optional[List[str]] = None,
        **kwargs
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Post content to the platform.
        Returns: (success, post_id, post_url, error_message)
        """
        pass
    
    @abstractmethod
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user info from the platform"""
        pass
    
    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """Refresh OAuth token"""
        pass


class TwitterClient(BaseSocialClient):
    """Twitter/X API client"""
    
    API_BASE = "https://api.twitter.com/2"
    
    async def post(
        self,
        account: SocialAccount,
        caption: str,
        media_urls: Optional[List[str]] = None,
        **kwargs
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        try:
            headers = {"Authorization": f"Bearer {account.access_token}"}
            
            # Upload media first if present
            media_ids = []
            if media_urls:
                for url in media_urls[:4]:  # Twitter allows max 4 images
                    media_id = await self._upload_media(account.access_token, url)
                    if media_id:
                        media_ids.append(media_id)
            
            # Create tweet
            tweet_data = {"text": caption}
            if media_ids:
                tweet_data["media"] = {"media_ids": media_ids}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_BASE}/tweets",
                    headers=headers,
                    json=tweet_data,
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    data = response.json()
                    tweet_id = data["data"]["id"]
                    tweet_url = f"https://twitter.com/{account.platform_username}/status/{tweet_id}"
                    return True, tweet_id, tweet_url, None
                else:
                    error = response.json().get("detail", response.text)
                    return False, None, None, str(error)
                    
        except Exception as e:
            logger.error(f"Twitter post error: {e}")
            return False, None, None, str(e)
    
    async def _upload_media(self, access_token: str, image_url: str) -> Optional[str]:
        """Upload media to Twitter"""
        try:
            # Download image
            async with httpx.AsyncClient() as client:
                img_response = await client.get(image_url)
                image_data = img_response.content
                
                # Upload to Twitter
                upload_response = await client.post(
                    "https://upload.twitter.com/1.1/media/upload.json",
                    headers={"Authorization": f"Bearer {access_token}"},
                    files={"media": image_data}
                )
                
                if upload_response.status_code == 200:
                    return upload_response.json()["media_id_string"]
        except Exception as e:
            logger.error(f"Twitter media upload error: {e}")
        return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/users/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"user.fields": "profile_image_url,public_metrics"}
                )
                if response.status_code == 200:
                    return response.json()["data"]
        except Exception as e:
            logger.error(f"Twitter user info error: {e}")
        return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.twitter.com/2/oauth2/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": settings.twitter_client_id
                    }
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Twitter token refresh error: {e}")
        return None


class InstagramClient(BaseSocialClient):
    """Instagram Graph API client (via Facebook)"""
    
    API_BASE = "https://graph.facebook.com/v18.0"
    
    async def post(
        self,
        account: SocialAccount,
        caption: str,
        media_urls: Optional[List[str]] = None,
        **kwargs
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        try:
            if not media_urls:
                return False, None, None, "Instagram requires at least one image"
            
            ig_user_id = account.platform_user_id
            access_token = account.access_token
            
            async with httpx.AsyncClient() as client:
                # Single image post
                if len(media_urls) == 1:
                    # Create media container
                    container_response = await client.post(
                        f"{self.API_BASE}/{ig_user_id}/media",
                        params={
                            "image_url": media_urls[0],
                            "caption": caption,
                            "access_token": access_token
                        }
                    )
                    
                    if container_response.status_code != 200:
                        return False, None, None, container_response.text
                    
                    container_id = container_response.json()["id"]
                    
                    # Publish
                    publish_response = await client.post(
                        f"{self.API_BASE}/{ig_user_id}/media_publish",
                        params={
                            "creation_id": container_id,
                            "access_token": access_token
                        }
                    )
                    
                    if publish_response.status_code == 200:
                        post_id = publish_response.json()["id"]
                        return True, post_id, f"https://www.instagram.com/p/{post_id}", None
                
                # Carousel post (multiple images)
                else:
                    children = []
                    for url in media_urls[:10]:  # Max 10 images
                        child_response = await client.post(
                            f"{self.API_BASE}/{ig_user_id}/media",
                            params={
                                "image_url": url,
                                "is_carousel_item": True,
                                "access_token": access_token
                            }
                        )
                        if child_response.status_code == 200:
                            children.append(child_response.json()["id"])
                    
                    if not children:
                        return False, None, None, "Failed to create carousel items"
                    
                    # Create carousel container
                    carousel_response = await client.post(
                        f"{self.API_BASE}/{ig_user_id}/media",
                        params={
                            "media_type": "CAROUSEL",
                            "children": ",".join(children),
                            "caption": caption,
                            "access_token": access_token
                        }
                    )
                    
                    if carousel_response.status_code != 200:
                        return False, None, None, carousel_response.text
                    
                    container_id = carousel_response.json()["id"]
                    
                    # Publish
                    publish_response = await client.post(
                        f"{self.API_BASE}/{ig_user_id}/media_publish",
                        params={
                            "creation_id": container_id,
                            "access_token": access_token
                        }
                    )
                    
                    if publish_response.status_code == 200:
                        post_id = publish_response.json()["id"]
                        return True, post_id, f"https://www.instagram.com/p/{post_id}", None
                
                return False, None, None, "Publishing failed"
                
        except Exception as e:
            logger.error(f"Instagram post error: {e}")
            return False, None, None, str(e)
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/me",
                    params={
                        "fields": "id,username,name,profile_picture_url,followers_count",
                        "access_token": access_token
                    }
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Instagram user info error: {e}")
        return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        # Instagram long-lived tokens don't use refresh tokens
        # They need to be refreshed before expiry
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/refresh_access_token",
                    params={
                        "grant_type": "ig_refresh_token",
                        "access_token": refresh_token  # Use current token
                    }
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Instagram token refresh error: {e}")
        return None


class LinkedInClient(BaseSocialClient):
    """LinkedIn API client"""
    
    API_BASE = "https://api.linkedin.com/v2"
    
    async def post(
        self,
        account: SocialAccount,
        caption: str,
        media_urls: Optional[List[str]] = None,
        **kwargs
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        try:
            headers = {
                "Authorization": f"Bearer {account.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            author = f"urn:li:person:{account.platform_user_id}"
            
            post_data = {
                "author": author,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": caption},
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            # Add media if present
            if media_urls:
                # LinkedIn requires uploading media first
                media_assets = []
                for url in media_urls[:1]:  # LinkedIn allows 1 image for basic posts
                    asset = await self._upload_media(account, url)
                    if asset:
                        media_assets.append(asset)
                
                if media_assets:
                    post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
                    post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = media_assets
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_BASE}/ugcPosts",
                    headers=headers,
                    json=post_data,
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    post_id = response.headers.get("x-restli-id", "")
                    return True, post_id, f"https://www.linkedin.com/feed/update/{post_id}", None
                else:
                    return False, None, None, response.text
                    
        except Exception as e:
            logger.error(f"LinkedIn post error: {e}")
            return False, None, None, str(e)
    
    async def _upload_media(self, account: SocialAccount, image_url: str) -> Optional[Dict]:
        """Upload media to LinkedIn"""
        # LinkedIn media upload is complex - simplified version
        return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE}/me",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"LinkedIn user info error: {e}")
        return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://www.linkedin.com/oauth/v2/accessToken",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": settings.linkedin_client_id,
                        "client_secret": settings.linkedin_client_secret
                    }
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"LinkedIn token refresh error: {e}")
        return None


# ==================== Posting Service ====================

class SocialPostingService:
    """Service for managing social media posting"""
    
    def __init__(self, db: Session):
        self.db = db
        self.clients = {
            SocialPlatform.TWITTER: TwitterClient(),
            SocialPlatform.INSTAGRAM: InstagramClient(),
            SocialPlatform.LINKEDIN: LinkedInClient(),
        }
    
    def get_client(self, platform: SocialPlatform) -> Optional[BaseSocialClient]:
        """Get the appropriate client for a platform"""
        return self.clients.get(platform)
    
    # ==================== Account Management ====================
    
    async def connect_account(
        self,
        user_id: int,
        platform: SocialPlatform,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
        brand_id: Optional[int] = None
    ) -> SocialAccount:
        """Connect a new social media account"""
        client = self.get_client(platform)
        if not client:
            raise ValueError(f"Platform {platform.value} not supported")
        
        # Get user info from platform
        user_info = await client.get_user_info(access_token)
        if not user_info:
            raise ValueError("Failed to get user info from platform")
        
        # Check if account already exists
        existing = self.db.query(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            SocialAccount.platform == platform,
            SocialAccount.platform_user_id == str(user_info.get("id"))
        ).first()
        
        if existing:
            # Update tokens
            existing.access_token = access_token
            existing.refresh_token = refresh_token
            existing.token_expires_at = token_expires_at
            existing.is_active = True
            existing.last_error = None
            self.db.commit()
            return existing
        
        # Create new account
        account = SocialAccount(
            user_id=user_id,
            brand_id=brand_id,
            platform=platform,
            platform_user_id=str(user_info.get("id")),
            platform_username=user_info.get("username") or user_info.get("screen_name"),
            platform_display_name=user_info.get("name"),
            profile_image_url=user_info.get("profile_image_url"),
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            platform_data=user_info
        )
        
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        
        return account
    
    async def disconnect_account(self, account: SocialAccount):
        """Disconnect a social media account"""
        account.is_active = False
        account.access_token = None
        account.refresh_token = None
        self.db.commit()
    
    async def refresh_account_token(self, account: SocialAccount) -> bool:
        """Refresh OAuth token for an account"""
        if not account.refresh_token:
            return False
        
        client = self.get_client(account.platform)
        if not client:
            return False
        
        new_tokens = await client.refresh_token(account.refresh_token)
        if not new_tokens:
            account.is_active = False
            account.last_error = "Token refresh failed"
            self.db.commit()
            return False
        
        account.access_token = new_tokens.get("access_token")
        if new_tokens.get("refresh_token"):
            account.refresh_token = new_tokens["refresh_token"]
        if new_tokens.get("expires_in"):
            account.token_expires_at = datetime.utcnow() + timedelta(seconds=new_tokens["expires_in"])
        
        self.db.commit()
        return True
    
    # ==================== Posting ====================
    
    async def post_now(
        self,
        account: SocialAccount,
        caption: str,
        media_urls: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        **kwargs
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """Post immediately to a social account"""
        # Check if token needs refresh
        if account.token_expires_at and account.token_expires_at < datetime.utcnow():
            refreshed = await self.refresh_account_token(account)
            if not refreshed:
                return False, None, None, "Token expired and refresh failed"
        
        client = self.get_client(account.platform)
        if not client:
            return False, None, None, "Platform not supported"
        
        # Add hashtags to caption
        full_caption = caption
        if hashtags:
            hashtag_str = " ".join(f"#{tag.strip('#')}" for tag in hashtags)
            full_caption = f"{caption}\n\n{hashtag_str}"
        
        return await client.post(account, full_caption, media_urls, **kwargs)
    
    async def publish_scheduled_post(self, post: ScheduledSocialPost) -> bool:
        """Publish a scheduled post"""
        post.status = PostStatus.PUBLISHING
        self.db.commit()
        
        account = post.social_account
        
        success, post_id, post_url, error = await self.post_now(
            account=account,
            caption=post.caption or "",
            media_urls=post.media_urls,
            hashtags=post.hashtags
        )
        
        # Log the attempt
        log = PublishingLog(
            scheduled_post_id=post.id,
            attempt_number=post.retry_count + 1,
            success=success,
            error_message=error
        )
        self.db.add(log)
        
        if success:
            post.status = PostStatus.PUBLISHED
            post.published_at = datetime.utcnow()
            post.platform_post_id = post_id
            post.platform_post_url = post_url
        else:
            post.retry_count += 1
            if post.retry_count >= 3:
                post.status = PostStatus.FAILED
                post.error_message = error
            else:
                post.status = PostStatus.SCHEDULED  # Will retry
        
        self.db.commit()
        return success
    
    # ==================== Scheduling ====================
    
    def create_scheduled_post(
        self,
        user_id: int,
        social_account_id: int,
        caption: str,
        scheduled_for: datetime,
        media_urls: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        brand_id: Optional[int] = None,
        generated_content_id: Optional[int] = None,
        timezone: str = "UTC",
        platform_specific: Optional[Dict] = None
    ) -> ScheduledSocialPost:
        """Create a new scheduled post"""
        post = ScheduledSocialPost(
            user_id=user_id,
            social_account_id=social_account_id,
            brand_id=brand_id,
            generated_content_id=generated_content_id,
            caption=caption,
            hashtags=hashtags,
            media_urls=media_urls,
            scheduled_for=scheduled_for,
            timezone=timezone,
            platform_specific=platform_specific,
            status=PostStatus.SCHEDULED
        )
        
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        
        return post
    
    def get_due_posts(self, limit: int = 50) -> List[ScheduledSocialPost]:
        """Get posts that are due to be published"""
        now = datetime.utcnow()
        
        return self.db.query(ScheduledSocialPost).filter(
            ScheduledSocialPost.status == PostStatus.SCHEDULED,
            ScheduledSocialPost.scheduled_for <= now
        ).order_by(ScheduledSocialPost.scheduled_for).limit(limit).all()
    
    # ==================== Best Time Analysis ====================
    
    def get_best_posting_times(
        self,
        account: SocialAccount
    ) -> List[Dict[str, Any]]:
        """Analyze engagement data to suggest best posting times"""
        # Get published posts with engagement
        posts = self.db.query(ScheduledSocialPost).filter(
            ScheduledSocialPost.social_account_id == account.id,
            ScheduledSocialPost.status == PostStatus.PUBLISHED,
            ScheduledSocialPost.engagement_data != None
        ).all()
        
        if not posts:
            # Return default recommendations
            return self._default_best_times(account.platform)
        
        # Analyze by hour and day
        time_engagement = {}
        for post in posts:
            if not post.published_at or not post.engagement_data:
                continue
            
            day = post.published_at.strftime("%A")
            hour = post.published_at.hour
            key = f"{day}-{hour}"
            
            engagement = sum([
                post.engagement_data.get("likes", 0),
                post.engagement_data.get("comments", 0) * 2,
                post.engagement_data.get("shares", 0) * 3
            ])
            
            if key not in time_engagement:
                time_engagement[key] = {"total": 0, "count": 0}
            time_engagement[key]["total"] += engagement
            time_engagement[key]["count"] += 1
        
        # Calculate averages and sort
        results = []
        for key, data in time_engagement.items():
            day, hour = key.rsplit("-", 1)
            avg_engagement = data["total"] / data["count"]
            results.append({
                "day_of_week": day,
                "hour": int(hour),
                "engagement_score": avg_engagement,
                "recommendation": "high" if avg_engagement > 100 else "medium" if avg_engagement > 50 else "low"
            })
        
        results.sort(key=lambda x: x["engagement_score"], reverse=True)
        return results[:10]
    
    def _default_best_times(self, platform: SocialPlatform) -> List[Dict[str, Any]]:
        """Default best posting times by platform"""
        defaults = {
            SocialPlatform.TWITTER: [
                {"day_of_week": "Tuesday", "hour": 9, "engagement_score": 85, "recommendation": "high"},
                {"day_of_week": "Wednesday", "hour": 12, "engagement_score": 82, "recommendation": "high"},
                {"day_of_week": "Thursday", "hour": 9, "engagement_score": 80, "recommendation": "high"},
            ],
            SocialPlatform.INSTAGRAM: [
                {"day_of_week": "Tuesday", "hour": 11, "engagement_score": 90, "recommendation": "high"},
                {"day_of_week": "Wednesday", "hour": 11, "engagement_score": 88, "recommendation": "high"},
                {"day_of_week": "Friday", "hour": 10, "engagement_score": 85, "recommendation": "high"},
            ],
            SocialPlatform.LINKEDIN: [
                {"day_of_week": "Tuesday", "hour": 10, "engagement_score": 88, "recommendation": "high"},
                {"day_of_week": "Wednesday", "hour": 12, "engagement_score": 85, "recommendation": "high"},
                {"day_of_week": "Thursday", "hour": 9, "engagement_score": 82, "recommendation": "high"},
            ],
        }
        return defaults.get(platform, defaults[SocialPlatform.TWITTER])


def get_social_posting_service(db: Session) -> SocialPostingService:
    return SocialPostingService(db)
