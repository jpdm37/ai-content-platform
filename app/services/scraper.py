"""
Trend Scraping Service
Scrapes trending topics from multiple sources
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import feedparser
import requests
from sqlalchemy.orm import Session

from app.models import Trend, Category, TrendCreate
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# RSS Feed sources by category
RSS_FEEDS = {
    "lifestyle": [
        "https://www.lifehacker.com/rss",
        "https://www.refinery29.com/en-us/rss.xml",
    ],
    "travel": [
        "https://www.lonelyplanet.com/news/feed",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
    "food": [
        "https://www.bonappetit.com/feed/rss",
        "https://www.seriouseats.com/feeds/main",
    ],
    "fitness": [
        "https://www.menshealth.com/rss/all.xml/",
        "https://www.self.com/feed/rss",
    ],
    "fashion": [
        "https://www.vogue.com/feed/rss",
        "https://fashionista.com/.rss/full/",
    ],
    "technology": [
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "https://www.theverge.com/rss/index.xml",
    ],
}


class TrendScraperService:
    """Service for scraping trends from multiple sources"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def scrape_all(self, category_id: Optional[int] = None) -> List[Trend]:
        """Scrape trends from all sources"""
        all_trends = []
        
        # Get categories to scrape
        if category_id:
            categories = self.db.query(Category).filter(Category.id == category_id).all()
        else:
            categories = self.db.query(Category).all()
        
        for category in categories:
            # Scrape Google Trends
            google_trends = await self.scrape_google_trends(category)
            all_trends.extend(google_trends)
            
            # Scrape RSS feeds
            rss_trends = await self.scrape_rss_feeds(category)
            all_trends.extend(rss_trends)
            
            # Scrape News API if key is available
            if settings.news_api_key:
                news_trends = await self.scrape_news_api(category)
                all_trends.extend(news_trends)
        
        return all_trends
    
    async def scrape_google_trends(self, category: Category) -> List[Trend]:
        """Scrape trending topics from Google Trends"""
        trends = []
        
        try:
            from pytrends.request import TrendReq
            
            pytrends = TrendReq(hl='en-US', tz=360)
            
            # Get keywords for this category
            keywords = category.keywords or [category.name.lower()]
            
            for keyword in keywords[:5]:  # Limit to 5 keywords
                try:
                    pytrends.build_payload([keyword], timeframe='now 7-d')
                    related = pytrends.related_queries()
                    
                    if keyword in related and related[keyword]['rising'] is not None:
                        rising = related[keyword]['rising']
                        for _, row in rising.head(5).iterrows():
                            trend = self._create_trend(
                                category_id=category.id,
                                title=row['query'],
                                description=f"Rising trend related to {keyword}",
                                source="google_trends",
                                popularity_score=int(row['value']) if row['value'] != 'Breakout' else 100,
                                related_keywords=[keyword]
                            )
                            trends.append(trend)
                except Exception as e:
                    logger.warning(f"Error fetching Google Trends for {keyword}: {e}")
                    continue
                    
        except ImportError:
            logger.warning("pytrends not installed, skipping Google Trends")
        except Exception as e:
            logger.error(f"Error scraping Google Trends: {e}")
        
        return trends
    
    async def scrape_rss_feeds(self, category: Category) -> List[Trend]:
        """Scrape trends from RSS feeds"""
        trends = []
        category_name = category.name.lower()
        
        feeds = RSS_FEEDS.get(category_name, [])
        
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:5]:  # Get top 5 from each feed
                    title = entry.get('title', '')
                    description = entry.get('summary', entry.get('description', ''))[:500]
                    link = entry.get('link', '')
                    
                    trend = self._create_trend(
                        category_id=category.id,
                        title=title,
                        description=description,
                        source="rss",
                        source_url=link,
                        popularity_score=50  # Default score for RSS
                    )
                    trends.append(trend)
                    
            except Exception as e:
                logger.warning(f"Error parsing RSS feed {feed_url}: {e}")
                continue
        
        return trends
    
    async def scrape_news_api(self, category: Category) -> List[Trend]:
        """Scrape trends from News API"""
        trends = []
        
        if not settings.news_api_key:
            return trends
        
        try:
            keywords = category.keywords or [category.name.lower()]
            query = " OR ".join(keywords[:3])
            
            response = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "sortBy": "popularity",
                    "pageSize": 10,
                    "language": "en",
                    "apiKey": settings.news_api_key
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                for article in data.get('articles', []):
                    trend = self._create_trend(
                        category_id=category.id,
                        title=article.get('title', ''),
                        description=article.get('description', ''),
                        source="news_api",
                        source_url=article.get('url', ''),
                        popularity_score=70  # News API results are generally popular
                    )
                    trends.append(trend)
                    
        except Exception as e:
            logger.error(f"Error scraping News API: {e}")
        
        return trends
    
    def _create_trend(
        self,
        category_id: int,
        title: str,
        description: str = None,
        source: str = "unknown",
        source_url: str = None,
        popularity_score: int = 0,
        related_keywords: List[str] = None
    ) -> Trend:
        """Create and save a trend to the database"""
        
        # Check if similar trend already exists
        existing = self.db.query(Trend).filter(
            Trend.category_id == category_id,
            Trend.title == title
        ).first()
        
        if existing:
            # Update existing trend
            existing.popularity_score = max(existing.popularity_score, popularity_score)
            existing.scraped_at = datetime.utcnow()
            self.db.commit()
            return existing
        
        # Create new trend
        trend = Trend(
            category_id=category_id,
            title=title,
            description=description,
            source=source,
            source_url=source_url,
            popularity_score=popularity_score,
            related_keywords=related_keywords or [],
            scraped_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        
        self.db.add(trend)
        self.db.commit()
        self.db.refresh(trend)
        
        return trend


async def get_trend_scraper(db: Session) -> TrendScraperService:
    """Factory function for TrendScraperService"""
    return TrendScraperService(db)
