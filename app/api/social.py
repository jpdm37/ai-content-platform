"""
Social Media API Routes

Handles social account connections, posting, and scheduling.
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.config import get_settings
from app.models.user import User
from app.auth.dependencies import get_current_user, get_current_verified_user

from app.social.models import (
    SocialAccount, ScheduledSocialPost, PostTemplate,
    SocialPlatform, PostStatus
)
from app.social.schemas import (
    SocialAccountResponse, SocialAccountDetailResponse,
    ConnectAccountRequest, OAuthCallbackData,
    ScheduledPostCreate, ScheduledPostUpdate, ScheduledPostResponse, ScheduledPostDetailResponse,
    BulkScheduleRequest, BulkScheduleResponse,
    QuickPostRequest, QuickPostResponse,
    CalendarDayResponse, CalendarPostResponse,
    PostTemplateCreate, PostTemplateResponse,
    PostEngagementResponse, BestTimesResponse, BestTimeResponse,
    SocialPlatformEnum, PostStatusEnum
)
from app.social.service import SocialPostingService
from app.billing.service import BillingService

settings = get_settings()
router = APIRouter(prefix="/social", tags=["social-media"])


# ==================== Social Accounts ====================

@router.get("/accounts", response_model=List[SocialAccountDetailResponse])
async def list_social_accounts(
    platform: Optional[SocialPlatformEnum] = None,
    brand_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List connected social media accounts"""
    query = db.query(SocialAccount).filter(
        SocialAccount.user_id == current_user.id,
        SocialAccount.is_active == True
    )
    
    if platform:
        query = query.filter(SocialAccount.platform == SocialPlatform(platform.value))
    if brand_id:
        query = query.filter(SocialAccount.brand_id == brand_id)
    
    accounts = query.order_by(SocialAccount.created_at.desc()).all()
    
    # Add post counts
    results = []
    for account in accounts:
        posts_count = db.query(ScheduledSocialPost).filter(
            ScheduledSocialPost.social_account_id == account.id
        ).count()
        scheduled_count = db.query(ScheduledSocialPost).filter(
            ScheduledSocialPost.social_account_id == account.id,
            ScheduledSocialPost.status == PostStatus.SCHEDULED
        ).count()
        published_count = db.query(ScheduledSocialPost).filter(
            ScheduledSocialPost.social_account_id == account.id,
            ScheduledSocialPost.status == PostStatus.PUBLISHED
        ).count()
        
        results.append(SocialAccountDetailResponse(
            id=account.id,
            platform=account.platform.value,
            platform_username=account.platform_username,
            platform_display_name=account.platform_display_name,
            profile_image_url=account.profile_image_url,
            brand_id=account.brand_id,
            is_active=account.is_active,
            last_synced_at=account.last_synced_at,
            last_error=account.last_error,
            platform_data=account.platform_data,
            created_at=account.created_at,
            posts_count=posts_count,
            scheduled_count=scheduled_count,
            published_count=published_count
        ))
    
    return results


@router.get("/accounts/{account_id}", response_model=SocialAccountDetailResponse)
async def get_social_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get social account details"""
    account = db.query(SocialAccount).filter(
        SocialAccount.id == account_id,
        SocialAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    posts_count = db.query(ScheduledSocialPost).filter(
        ScheduledSocialPost.social_account_id == account.id
    ).count()
    
    return SocialAccountDetailResponse(
        id=account.id,
        platform=account.platform.value,
        platform_username=account.platform_username,
        platform_display_name=account.platform_display_name,
        profile_image_url=account.profile_image_url,
        brand_id=account.brand_id,
        is_active=account.is_active,
        last_synced_at=account.last_synced_at,
        last_error=account.last_error,
        platform_data=account.platform_data,
        created_at=account.created_at,
        posts_count=posts_count
    )


@router.get("/connect/{platform}/url")
async def get_oauth_url(
    platform: SocialPlatformEnum,
    brand_id: Optional[int] = None,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Get OAuth URL to connect a social account"""
    # Check limits
    billing = BillingService(db)
    limit_check = billing.check_limit(current_user, "social_accounts")
    if not limit_check["allowed"]:
        raise HTTPException(
            status_code=403,
            detail=f"Social account limit reached ({limit_check['used']}/{limit_check['limit']}). Upgrade to add more."
        )
    
    base_url = settings.frontend_url or "http://localhost:3000"
    redirect_uri = f"{base_url}/social/callback/{platform.value}"
    
    state = f"{current_user.id}:{brand_id or ''}"
    
    if platform == SocialPlatformEnum.TWITTER:
        if not settings.twitter_client_id:
            raise HTTPException(status_code=503, detail="Twitter not configured")
        oauth_url = (
            f"https://twitter.com/i/oauth2/authorize"
            f"?response_type=code"
            f"&client_id={settings.twitter_client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=tweet.read%20tweet.write%20users.read%20offline.access"
            f"&state={state}"
            f"&code_challenge=challenge"
            f"&code_challenge_method=plain"
        )
    elif platform == SocialPlatformEnum.INSTAGRAM:
        if not settings.instagram_app_id:
            raise HTTPException(status_code=503, detail="Instagram not configured")
        oauth_url = (
            f"https://api.instagram.com/oauth/authorize"
            f"?client_id={settings.instagram_app_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=user_profile,user_media"
            f"&response_type=code"
            f"&state={state}"
        )
    elif platform == SocialPlatformEnum.LINKEDIN:
        if not settings.linkedin_client_id:
            raise HTTPException(status_code=503, detail="LinkedIn not configured")
        oauth_url = (
            f"https://www.linkedin.com/oauth/v2/authorization"
            f"?response_type=code"
            f"&client_id={settings.linkedin_client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=r_liteprofile%20w_member_social"
            f"&state={state}"
        )
    else:
        raise HTTPException(status_code=400, detail="Platform not supported yet")
    
    return {"oauth_url": oauth_url, "platform": platform.value}


@router.post("/connect/{platform}/callback")
async def handle_oauth_callback(
    platform: SocialPlatformEnum,
    data: OAuthCallbackData,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Handle OAuth callback and connect account"""
    service = SocialPostingService(db)
    
    # Parse state for brand_id
    brand_id = None
    if data.state:
        parts = data.state.split(":")
        if len(parts) > 1 and parts[1]:
            brand_id = int(parts[1])
    
    base_url = settings.frontend_url or "http://localhost:3000"
    redirect_uri = f"{base_url}/social/callback/{platform.value}"
    
    # Exchange code for tokens (platform-specific)
    try:
        import httpx
        
        if platform == SocialPlatformEnum.TWITTER:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.twitter.com/2/oauth2/token",
                    data={
                        "code": data.code,
                        "grant_type": "authorization_code",
                        "client_id": settings.twitter_client_id,
                        "redirect_uri": redirect_uri,
                        "code_verifier": "challenge"
                    }
                )
                tokens = response.json()
                
        elif platform == SocialPlatformEnum.INSTAGRAM:
            async with httpx.AsyncClient() as client:
                # Get short-lived token
                response = await client.post(
                    "https://api.instagram.com/oauth/access_token",
                    data={
                        "client_id": settings.instagram_app_id,
                        "client_secret": settings.instagram_app_secret,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                        "code": data.code
                    }
                )
                short_token = response.json()
                
                # Exchange for long-lived token
                response = await client.get(
                    "https://graph.instagram.com/access_token",
                    params={
                        "grant_type": "ig_exchange_token",
                        "client_secret": settings.instagram_app_secret,
                        "access_token": short_token["access_token"]
                    }
                )
                tokens = response.json()
                tokens["user_id"] = short_token.get("user_id")
                
        elif platform == SocialPlatformEnum.LINKEDIN:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://www.linkedin.com/oauth/v2/accessToken",
                    data={
                        "grant_type": "authorization_code",
                        "code": data.code,
                        "redirect_uri": redirect_uri,
                        "client_id": settings.linkedin_client_id,
                        "client_secret": settings.linkedin_client_secret
                    }
                )
                tokens = response.json()
        else:
            raise HTTPException(status_code=400, detail="Platform not supported")
        
        if "error" in tokens:
            raise HTTPException(status_code=400, detail=tokens.get("error_description", "OAuth failed"))
        
        # Calculate token expiry
        expires_at = None
        if tokens.get("expires_in"):
            expires_at = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])
        
        # Connect account
        account = await service.connect_account(
            user_id=current_user.id,
            platform=SocialPlatform(platform.value),
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
            token_expires_at=expires_at,
            brand_id=brand_id
        )
        
        return {"success": True, "account_id": account.id, "username": account.platform_username}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/accounts/{account_id}")
async def disconnect_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect a social account"""
    account = db.query(SocialAccount).filter(
        SocialAccount.id == account_id,
        SocialAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    service = SocialPostingService(db)
    await service.disconnect_account(account)
    
    return {"success": True, "message": "Account disconnected"}


@router.put("/accounts/{account_id}/brand")
async def update_account_brand(
    account_id: int,
    brand_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Associate account with a brand"""
    account = db.query(SocialAccount).filter(
        SocialAccount.id == account_id,
        SocialAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account.brand_id = brand_id
    db.commit()
    
    return {"success": True}


# ==================== Scheduled Posts ====================

@router.post("/posts", response_model=ScheduledPostResponse)
async def create_scheduled_post(
    data: ScheduledPostCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create a scheduled post"""
    # Verify account ownership
    account = db.query(SocialAccount).filter(
        SocialAccount.id == data.social_account_id,
        SocialAccount.user_id == current_user.id,
        SocialAccount.is_active == True
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")
    
    # Check limits
    billing = BillingService(db)
    limit_check = billing.check_limit(current_user, "scheduled_posts")
    if not limit_check["allowed"]:
        raise HTTPException(status_code=403, detail="Scheduled post limit reached. Upgrade to schedule more.")
    
    service = SocialPostingService(db)
    post = service.create_scheduled_post(
        user_id=current_user.id,
        social_account_id=data.social_account_id,
        caption=data.caption,
        scheduled_for=data.scheduled_for,
        media_urls=data.media_urls,
        hashtags=data.hashtags,
        brand_id=data.brand_id,
        generated_content_id=data.generated_content_id,
        timezone=data.timezone,
        platform_specific=data.platform_specific
    )
    
    return ScheduledPostResponse(
        id=post.id,
        social_account_id=post.social_account_id,
        brand_id=post.brand_id,
        generated_content_id=post.generated_content_id,
        caption=post.caption,
        hashtags=post.hashtags,
        media_urls=post.media_urls,
        scheduled_for=post.scheduled_for,
        timezone=post.timezone,
        status=post.status.value,
        published_at=post.published_at,
        platform_post_id=post.platform_post_id,
        platform_post_url=post.platform_post_url,
        error_message=post.error_message,
        engagement_data=post.engagement_data,
        created_at=post.created_at,
        platform=account.platform.value,
        account_username=account.platform_username
    )


@router.get("/posts", response_model=List[ScheduledPostResponse])
async def list_scheduled_posts(
    status_filter: Optional[PostStatusEnum] = None,
    account_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List scheduled posts"""
    query = db.query(ScheduledSocialPost).filter(
        ScheduledSocialPost.user_id == current_user.id
    )
    
    if status_filter:
        query = query.filter(ScheduledSocialPost.status == PostStatus(status_filter.value))
    if account_id:
        query = query.filter(ScheduledSocialPost.social_account_id == account_id)
    if brand_id:
        query = query.filter(ScheduledSocialPost.brand_id == brand_id)
    if from_date:
        query = query.filter(ScheduledSocialPost.scheduled_for >= from_date)
    if to_date:
        query = query.filter(ScheduledSocialPost.scheduled_for <= to_date)
    
    posts = query.order_by(ScheduledSocialPost.scheduled_for).offset(skip).limit(limit).all()
    
    results = []
    for post in posts:
        account = post.social_account
        results.append(ScheduledPostResponse(
            id=post.id,
            social_account_id=post.social_account_id,
            brand_id=post.brand_id,
            generated_content_id=post.generated_content_id,
            caption=post.caption,
            hashtags=post.hashtags,
            media_urls=post.media_urls,
            scheduled_for=post.scheduled_for,
            timezone=post.timezone,
            status=post.status.value,
            published_at=post.published_at,
            platform_post_id=post.platform_post_id,
            platform_post_url=post.platform_post_url,
            error_message=post.error_message,
            engagement_data=post.engagement_data,
            created_at=post.created_at,
            platform=account.platform.value if account else None,
            account_username=account.platform_username if account else None
        ))
    
    return results


@router.get("/posts/{post_id}", response_model=ScheduledPostDetailResponse)
async def get_scheduled_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get scheduled post details"""
    post = db.query(ScheduledSocialPost).filter(
        ScheduledSocialPost.id == post_id,
        ScheduledSocialPost.user_id == current_user.id
    ).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    account = post.social_account
    
    return ScheduledPostDetailResponse(
        id=post.id,
        social_account_id=post.social_account_id,
        brand_id=post.brand_id,
        generated_content_id=post.generated_content_id,
        caption=post.caption,
        hashtags=post.hashtags,
        media_urls=post.media_urls,
        scheduled_for=post.scheduled_for,
        timezone=post.timezone,
        status=post.status.value,
        published_at=post.published_at,
        platform_post_id=post.platform_post_id,
        platform_post_url=post.platform_post_url,
        error_message=post.error_message,
        engagement_data=post.engagement_data,
        created_at=post.created_at,
        platform=account.platform.value if account else None,
        account_username=account.platform_username if account else None,
        social_account=SocialAccountResponse.model_validate(account) if account else None,
        retry_count=post.retry_count
    )


@router.put("/posts/{post_id}", response_model=ScheduledPostResponse)
async def update_scheduled_post(
    post_id: int,
    data: ScheduledPostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a scheduled post"""
    post = db.query(ScheduledSocialPost).filter(
        ScheduledSocialPost.id == post_id,
        ScheduledSocialPost.user_id == current_user.id
    ).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.status not in [PostStatus.DRAFT, PostStatus.SCHEDULED]:
        raise HTTPException(status_code=400, detail="Cannot edit post that has been published or is publishing")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)
    
    db.commit()
    db.refresh(post)
    
    account = post.social_account
    return ScheduledPostResponse(
        id=post.id,
        social_account_id=post.social_account_id,
        brand_id=post.brand_id,
        generated_content_id=post.generated_content_id,
        caption=post.caption,
        hashtags=post.hashtags,
        media_urls=post.media_urls,
        scheduled_for=post.scheduled_for,
        timezone=post.timezone,
        status=post.status.value,
        published_at=post.published_at,
        platform_post_id=post.platform_post_id,
        platform_post_url=post.platform_post_url,
        error_message=post.error_message,
        engagement_data=post.engagement_data,
        created_at=post.created_at,
        platform=account.platform.value if account else None,
        account_username=account.platform_username if account else None
    )


@router.delete("/posts/{post_id}")
async def delete_scheduled_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a scheduled post"""
    post = db.query(ScheduledSocialPost).filter(
        ScheduledSocialPost.id == post_id,
        ScheduledSocialPost.user_id == current_user.id
    ).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    db.delete(post)
    db.commit()
    
    return {"success": True}


@router.post("/posts/{post_id}/cancel")
async def cancel_scheduled_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a scheduled post"""
    post = db.query(ScheduledSocialPost).filter(
        ScheduledSocialPost.id == post_id,
        ScheduledSocialPost.user_id == current_user.id
    ).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.status not in [PostStatus.SCHEDULED, PostStatus.DRAFT]:
        raise HTTPException(status_code=400, detail="Can only cancel scheduled or draft posts")
    
    post.status = PostStatus.CANCELLED
    db.commit()
    
    return {"success": True}


# ==================== Quick Post (Immediate) ====================

@router.post("/posts/now", response_model=QuickPostResponse)
async def post_now(
    data: QuickPostRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Post immediately to a social account"""
    account = db.query(SocialAccount).filter(
        SocialAccount.id == data.social_account_id,
        SocialAccount.user_id == current_user.id,
        SocialAccount.is_active == True
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")
    
    service = SocialPostingService(db)
    success, post_id, post_url, error = await service.post_now(
        account=account,
        caption=data.caption,
        media_urls=data.media_urls,
        hashtags=data.hashtags,
        **(data.platform_specific or {})
    )
    
    # Record usage
    if success:
        billing = BillingService(db)
        billing.record_usage(current_user, "social_post")
    
    return QuickPostResponse(
        success=success,
        post_id=post_id,
        post_url=post_url,
        error=error
    )


# ==================== Bulk Scheduling ====================

@router.post("/posts/bulk", response_model=BulkScheduleResponse)
async def bulk_schedule_posts(
    data: BulkScheduleRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Schedule same content to multiple accounts"""
    service = SocialPostingService(db)
    
    scheduled = []
    errors = []
    
    for account_id in data.social_account_ids:
        try:
            account = db.query(SocialAccount).filter(
                SocialAccount.id == account_id,
                SocialAccount.user_id == current_user.id,
                SocialAccount.is_active == True
            ).first()
            
            if not account:
                errors.append({"account_id": account_id, "error": "Account not found"})
                continue
            
            post = service.create_scheduled_post(
                user_id=current_user.id,
                social_account_id=account_id,
                caption=data.caption,
                scheduled_for=data.scheduled_for,
                media_urls=data.media_urls,
                hashtags=data.hashtags,
                brand_id=data.brand_id,
                timezone=data.timezone
            )
            
            scheduled.append(ScheduledPostResponse(
                id=post.id,
                social_account_id=post.social_account_id,
                brand_id=post.brand_id,
                generated_content_id=post.generated_content_id,
                caption=post.caption,
                hashtags=post.hashtags,
                media_urls=post.media_urls,
                scheduled_for=post.scheduled_for,
                timezone=post.timezone,
                status=post.status.value,
                published_at=None,
                platform_post_id=None,
                platform_post_url=None,
                error_message=None,
                engagement_data=None,
                created_at=post.created_at,
                platform=account.platform.value,
                account_username=account.platform_username
            ))
            
        except Exception as e:
            errors.append({"account_id": account_id, "error": str(e)})
    
    return BulkScheduleResponse(
        scheduled=len(scheduled),
        failed=len(errors),
        posts=scheduled,
        errors=errors
    )


# ==================== Calendar View ====================

@router.get("/calendar")
async def get_calendar(
    year: int,
    month: int,
    account_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get calendar view of scheduled posts"""
    from calendar import monthrange
    
    start_date = datetime(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = datetime(year, month, last_day, 23, 59, 59)
    
    query = db.query(ScheduledSocialPost).filter(
        ScheduledSocialPost.user_id == current_user.id,
        ScheduledSocialPost.scheduled_for >= start_date,
        ScheduledSocialPost.scheduled_for <= end_date
    )
    
    if account_id:
        query = query.filter(ScheduledSocialPost.social_account_id == account_id)
    if brand_id:
        query = query.filter(ScheduledSocialPost.brand_id == brand_id)
    
    posts = query.order_by(ScheduledSocialPost.scheduled_for).all()
    
    # Group by day
    calendar_data = {}
    for post in posts:
        day_key = post.scheduled_for.strftime("%Y-%m-%d")
        if day_key not in calendar_data:
            calendar_data[day_key] = []
        
        account = post.social_account
        calendar_data[day_key].append(CalendarPostResponse(
            id=post.id,
            scheduled_for=post.scheduled_for,
            status=post.status.value,
            platform=account.platform.value if account else "unknown",
            account_username=account.platform_username if account else None,
            caption_preview=post.caption[:100] if post.caption else None,
            media_count=len(post.media_urls) if post.media_urls else 0
        ))
    
    return [
        CalendarDayResponse(date=date, posts=posts, total=len(posts))
        for date, posts in sorted(calendar_data.items())
    ]


# ==================== Best Time to Post ====================

@router.get("/accounts/{account_id}/best-times", response_model=BestTimesResponse)
async def get_best_posting_times(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get best times to post for an account"""
    account = db.query(SocialAccount).filter(
        SocialAccount.id == account_id,
        SocialAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    service = SocialPostingService(db)
    times = service.get_best_posting_times(account)
    
    return BestTimesResponse(
        account_id=account_id,
        platform=account.platform.value,
        times=[BestTimeResponse(**t) for t in times],
        timezone="UTC"
    )


# ==================== Templates ====================

@router.post("/templates", response_model=PostTemplateResponse)
async def create_template(
    data: PostTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a post template"""
    template = PostTemplate(
        user_id=current_user.id,
        brand_id=data.brand_id,
        name=data.name,
        description=data.description,
        caption_template=data.caption_template,
        default_hashtags=data.default_hashtags,
        platforms=[p.value for p in data.platforms] if data.platforms else None
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return template


@router.get("/templates", response_model=List[PostTemplateResponse])
async def list_templates(
    brand_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List post templates"""
    query = db.query(PostTemplate).filter(
        PostTemplate.user_id == current_user.id,
        PostTemplate.is_active == True
    )
    
    if brand_id:
        query = query.filter(PostTemplate.brand_id == brand_id)
    
    return query.order_by(PostTemplate.created_at.desc()).all()


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a template"""
    template = db.query(PostTemplate).filter(
        PostTemplate.id == template_id,
        PostTemplate.user_id == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    
    return {"success": True}
