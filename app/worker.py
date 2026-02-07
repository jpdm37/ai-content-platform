"""
Celery Worker for Background Tasks
Handles scheduled scraping and async generation
"""
from celery import Celery
from celery.schedules import crontab
import logging

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "ai_content_worker",
    broker=settings.redis_url,
    backend=settings.redis_url
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
)

# Scheduled tasks
celery_app.conf.beat_schedule = {
    # Scrape trends every 6 hours
    "scrape-trends-periodic": {
        "task": "app.worker.scrape_all_trends",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    # Cleanup expired trends daily
    "cleanup-expired-trends": {
        "task": "app.worker.cleanup_expired_trends",
        "schedule": crontab(minute=0, hour=3),  # 3 AM UTC
    },
    # Process scheduled social posts every minute
    "process-scheduled-posts": {
        "task": "app.worker.process_scheduled_posts",
        "schedule": 60.0,
    },
    # Refresh expiring OAuth tokens every hour
    "refresh-social-tokens": {
        "task": "app.worker.refresh_expiring_tokens",
        "schedule": crontab(minute=30),  # Every hour at :30
    },
    # Send weekly digests every Monday at 9 AM UTC
    "send-weekly-digests": {
        "task": "app.worker.send_weekly_digests",
        "schedule": crontab(minute=0, hour=9, day_of_week=1),  # Monday 9 AM
    },
    # Sync performance metrics every 6 hours
    "sync-performance-metrics": {
        "task": "app.worker.sync_all_performance_metrics",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
    },
}


@celery_app.task(name="app.worker.scrape_all_trends")
def scrape_all_trends():
    """Background task to scrape trends from all sources"""
    from app.core.database import SessionLocal
    from app.services.scraper import TrendScraperService
    import asyncio
    
    logger.info("Starting scheduled trend scraping...")
    
    db = SessionLocal()
    try:
        scraper = TrendScraperService(db)
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        trends = loop.run_until_complete(scraper.scrape_all())
        loop.close()
        
        logger.info(f"Scraped {len(trends)} trends")
        return {"status": "success", "trends_found": len(trends)}
    except Exception as e:
        logger.error(f"Error scraping trends: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.worker.scrape_category_trends")
def scrape_category_trends(category_id: int):
    """Background task to scrape trends for a specific category"""
    from app.core.database import SessionLocal
    from app.services.scraper import TrendScraperService
    import asyncio
    
    logger.info(f"Starting trend scraping for category {category_id}...")
    
    db = SessionLocal()
    try:
        scraper = TrendScraperService(db)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        trends = loop.run_until_complete(scraper.scrape_all(category_id=category_id))
        loop.close()
        
        logger.info(f"Scraped {len(trends)} trends for category {category_id}")
        return {"status": "success", "trends_found": len(trends), "category_id": category_id}
    except Exception as e:
        logger.error(f"Error scraping trends for category {category_id}: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.worker.cleanup_expired_trends")
def cleanup_expired_trends():
    """Background task to remove expired trends"""
    from app.core.database import SessionLocal
    from app.models import Trend
    from datetime import datetime
    
    logger.info("Starting expired trends cleanup...")
    
    db = SessionLocal()
    try:
        deleted = db.query(Trend).filter(
            Trend.expires_at < datetime.utcnow()
        ).delete()
        db.commit()
        
        logger.info(f"Deleted {deleted} expired trends")
        return {"status": "success", "deleted_count": deleted}
    except Exception as e:
        logger.error(f"Error cleaning up trends: {e}")
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.worker.generate_content_async")
def generate_content_async(
    brand_id: int,
    content_type: str,
    category_id: int = None,
    trend_id: int = None,
    custom_prompt: str = None
):
    """Background task for async content generation"""
    from app.core.database import SessionLocal
    from app.models import Brand, Category, Trend, ContentType
    from app.services.generator import ContentGeneratorService
    import asyncio
    
    logger.info(f"Starting async content generation for brand {brand_id}...")
    
    db = SessionLocal()
    try:
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if not brand:
            return {"status": "error", "message": "Brand not found"}
        
        category = None
        if category_id:
            category = db.query(Category).filter(Category.id == category_id).first()
        
        trend = None
        if trend_id:
            trend = db.query(Trend).filter(Trend.id == trend_id).first()
        
        # Map content type
        type_map = {
            "image": ContentType.IMAGE,
            "text": ContentType.TEXT,
            "video": ContentType.VIDEO
        }
        ct = type_map.get(content_type.lower(), ContentType.IMAGE)
        
        generator = ContentGeneratorService(db)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        content = loop.run_until_complete(
            generator.generate_content(
                brand=brand,
                content_type=ct,
                category=category,
                trend=trend,
                custom_prompt=custom_prompt
            )
        )
        loop.close()
        
        logger.info(f"Generated content {content.id}")
        return {
            "status": "success",
            "content_id": content.id,
            "result_url": content.result_url
        }
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.worker.process_scheduled_posts")
def process_scheduled_posts():
    """Process and publish scheduled social media posts"""
    from app.core.database import SessionLocal
    from app.social.models import ScheduledSocialPost, PostStatus
    from app.social.service import SocialPostingService
    import asyncio
    
    logger.info("Processing scheduled social posts...")
    
    db = SessionLocal()
    try:
        service = SocialPostingService(db)
        due_posts = service.get_due_posts(limit=20)
        
        published = 0
        failed = 0
        
        for post in due_posts:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(service.publish_scheduled_post(post))
                loop.close()
                
                if success:
                    published += 1
                    logger.info(f"Published post {post.id}")
                else:
                    failed += 1
                    logger.warning(f"Failed to publish post {post.id}")
            except Exception as e:
                failed += 1
                logger.error(f"Error publishing post {post.id}: {e}")
        
        return {"status": "success", "published": published, "failed": failed}
    except Exception as e:
        logger.error(f"Error processing scheduled posts: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.worker.refresh_expiring_tokens")
def refresh_expiring_tokens():
    """Refresh OAuth tokens that are about to expire"""
    from app.core.database import SessionLocal
    from app.social.models import SocialAccount
    from app.social.service import SocialPostingService
    from datetime import datetime, timedelta
    import asyncio
    
    logger.info("Refreshing expiring OAuth tokens...")
    
    db = SessionLocal()
    try:
        expiry_threshold = datetime.utcnow() + timedelta(hours=24)
        
        accounts = db.query(SocialAccount).filter(
            SocialAccount.is_active == True,
            SocialAccount.token_expires_at != None,
            SocialAccount.token_expires_at < expiry_threshold,
            SocialAccount.refresh_token != None
        ).all()
        
        refreshed = 0
        failed = 0
        
        service = SocialPostingService(db)
        
        for account in accounts:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(service.refresh_account_token(account))
                loop.close()
                
                if success:
                    refreshed += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                logger.error(f"Error refreshing token for account {account.id}: {e}")
        
        return {"status": "success", "refreshed": refreshed, "failed": failed}
    except Exception as e:
        logger.error(f"Error refreshing tokens: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.worker.send_weekly_digests")
def send_weekly_digests():
    """Send weekly email digests to all eligible users"""
    from app.core.database import SessionLocal
    from app.digest.service import EmailDigestService
    import asyncio
    
    logger.info("Starting weekly digest send...")
    
    db = SessionLocal()
    try:
        service = EmailDigestService(db)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(service.send_all_weekly_digests())
        loop.close()
        
        logger.info(f"Weekly digests sent: {results}")
        return {"status": "success", **results}
    except Exception as e:
        logger.error(f"Error sending weekly digests: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.worker.send_single_digest")
def send_single_digest(user_id: int):
    """Send weekly digest to a single user (for testing or manual trigger)"""
    from app.core.database import SessionLocal
    from app.digest.service import EmailDigestService
    from app.models.user import User
    import asyncio
    
    logger.info(f"Sending digest to user {user_id}...")
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "error", "message": "User not found"}
        
        service = EmailDigestService(db)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(service.send_weekly_digest(user))
        loop.close()
        
        return {"status": "success" if success else "skipped", "user_id": user_id}
    except Exception as e:
        logger.error(f"Error sending digest to user {user_id}: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.worker.sync_all_performance_metrics")
def sync_all_performance_metrics():
    """Sync performance metrics for all active users"""
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.performance.service import PerformanceTrackingService
    import asyncio
    
    logger.info("Starting performance metrics sync...")
    
    db = SessionLocal()
    try:
        # Get all active users with connected social accounts
        users = db.query(User).filter(User.is_active == True).all()
        
        total_synced = 0
        total_failed = 0
        
        for user in users:
            try:
                service = PerformanceTrackingService(db)
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(service.sync_post_metrics(user.id))
                loop.close()
                
                total_synced += result.get("synced", 0)
                total_failed += result.get("failed", 0)
                
            except Exception as e:
                logger.error(f"Error syncing metrics for user {user.id}: {e}")
                total_failed += 1
        
        logger.info(f"Performance sync complete: {total_synced} synced, {total_failed} failed")
        return {"status": "success", "synced": total_synced, "failed": total_failed}
    except Exception as e:
        logger.error(f"Error in performance sync: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.worker.sync_user_performance")
def sync_user_performance(user_id: int, platform: str = None):
    """Sync performance metrics for a single user"""
    from app.core.database import SessionLocal
    from app.performance.service import PerformanceTrackingService
    import asyncio
    
    logger.info(f"Syncing performance for user {user_id}...")
    
    db = SessionLocal()
    try:
        service = PerformanceTrackingService(db)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(service.sync_post_metrics(user_id, platform))
        loop.close()
        
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Error syncing performance for user {user_id}: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
