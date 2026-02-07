"""
Trend Scraping Service
Scrapes trending topics from multiple sources including Google News RSS
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import feedparser
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
import hashlib
import re

from app.models import Trend, Category, TrendCreate
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Google News RSS feeds by category
GOOGLE_NEWS_RSS = {
    "lifestyle": "https://news.google.com/rss/search?q=lifestyle+wellness+self-improvement&hl=en-US&gl=US&ceid=US:en",
    "travel": "https://news.google.com/rss/search?q=travel+destinations+tourism&hl=en-US&gl=US&ceid=US:en",
    "food": "https://news.google.com/rss/search?q=food+recipes+restaurants+culinary&hl=en-US&gl=US&ceid=US:en",
    "fitness": "https://news.google.com/rss/search?q=fitness+workout+health+exercise&hl=en-US&gl=US&ceid=US:en",
    "fashion": "https://news.google.com/rss/search?q=fashion+style+trends+clothing&hl=en-US&gl=US&ceid=US:en",
    "technology": "https://news.google.com/rss/search?q=technology+tech+AI+innovation&hl=en-US&gl=US&ceid=US:en",
}

# Additional RSS Feed sources by category
RSS_FEEDS = {
    "lifestyle": [
        "https://www.lifehacker.com/rss",
        "https://www.refinery29.com/en-us/rss.xml",
        "https://www.mindbodygreen.com/rss",
    ],
    "travel": [
        "https://www.lonelyplanet.com/news/feed",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.cntraveler.com/feed/rss",
    ],
    "food": [
        "https://www.bonappetit.com/feed/rss",
        "https://www.seriouseats.com/feeds/main",
        "https://www.foodnetwork.com/fn-dish/rss",
    ],
    "fitness": [
        "https://www.menshealth.com/rss/all.xml/",
        "https://www.self.com/feed/rss",
        "https://www.shape.com/rss/all.xml/",
    ],
    "fashion": [
        "https://www.vogue.com/feed/rss",
        "https://fashionista.com/.rss/full/",
        "https://www.harpersbazaar.com/rss/all.xml/",
    ],
    "technology": [
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
        "https://www.wired.com/feed/rss",
    ],
}


class TrendScraperService:
    """Service for scraping trends from multiple sources"""
    
    def __init__(self, db: Session):
        self.db = db
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    async def scrape_all(self, category_id: Optional[int] = None) -> List[Trend]:
        """Scrape trends from all sources"""
        all_trends = []
        
        # Get categories to scrape
        if category_id:
            categories = self.db.query(Category).filter(Category.id == category_id).all()
        else:
            categories = self.db.query(Category).all()
        
        for category in categories:
            logger.info(f"Scraping trends for category: {category.name}")
            
            # 1. Scrape Google News RSS (primary source)
            google_news_trends = await self.scrape_google_news_rss(category)
            all_trends.extend(google_news_trends)
            logger.info(f"  - Google News RSS: {len(google_news_trends)} trends")
            
            # 2. Scrape Google Trends (rising topics)
            google_trends = await self.scrape_google_trends(category)
            all_trends.extend(google_trends)
            logger.info(f"  - Google Trends: {len(google_trends)} trends")
            
            # 3. Scrape category-specific RSS feeds
            rss_trends = await self.scrape_rss_feeds(category)
            all_trends.extend(rss_trends)
            logger.info(f"  - RSS Feeds: {len(rss_trends)} trends")
            
            # 4. Scrape News API if key is available
            if settings.news_api_key:
                news_trends = await self.scrape_news_api(category)
                all_trends.extend(news_trends)
                logger.info(f"  - News API: {len(news_trends)} trends")
        
        logger.info(f"Total trends scraped: {len(all_trends)}")
        return all_trends
    
    async def scrape_google_news_rss(self, category: Category) -> List[Trend]:
        """Scrape trending topics from Google News RSS feeds"""
        trends = []
        category_name = category.name.lower().replace(" & ", "_").replace(" ", "_")
        
        # Check for custom Google News query first (for custom niches)
        if hasattr(category, 'custom_google_news_query') and category.custom_google_news_query:
            query = category.custom_google_news_query.replace(" ", "+")
            feed_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        else:
            # Get predefined Google News RSS URL for this category
            feed_url = GOOGLE_NEWS_RSS.get(category_name)
            
            # If no predefined URL, create from keywords
            if not feed_url and category.keywords:
                keywords = "+".join(category.keywords[:5])
                feed_url = f"https://news.google.com/rss/search?q={keywords}&hl=en-US&gl=US&ceid=US:en"
        
        if not feed_url:
            return trends
        
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:15]:  # Get top 15 from Google News
                title = entry.get('title', '')
                
                # Clean up title (remove source suffix like " - CNN")
                title = re.sub(r'\s*-\s*[^-]+$', '', title).strip()
                
                description = entry.get('summary', entry.get('description', ''))
                # Clean HTML from description
                if description:
                    soup = BeautifulSoup(description, 'html.parser')
                    description = soup.get_text()[:500]
                
                link = entry.get('link', '')
                published = entry.get('published_parsed')
                
                # Calculate popularity based on recency
                popularity = 80  # Base score for Google News
                if published:
                    pub_date = datetime(*published[:6])
                    hours_old = (datetime.utcnow() - pub_date).total_seconds() / 3600
                    if hours_old < 6:
                        popularity = 95
                    elif hours_old < 12:
                        popularity = 90
                    elif hours_old < 24:
                        popularity = 85
                
                trend = self._create_trend(
                    category_id=category.id,
                    title=title,
                    description=description,
                    source="google_news",
                    source_url=link,
                    popularity_score=popularity,
                    related_keywords=category.keywords[:5] if category.keywords else []
                )
                if trend:
                    trends.append(trend)
                    
        except Exception as e:
            logger.warning(f"Error parsing Google News RSS for {category.name}: {e}")
        
        return trends
    
    async def scrape_google_trends(self, category: Category) -> List[Trend]:
        """Scrape trending topics from Google Trends"""
        trends = []
        
        try:
            from pytrends.request import TrendReq
            
            pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))
            
            # Get keywords for this category
            keywords = category.keywords or [category.name.lower()]
            
            for keyword in keywords[:3]:  # Limit to 3 keywords to avoid rate limiting
                try:
                    pytrends.build_payload([keyword], timeframe='now 7-d')
                    related = pytrends.related_queries()
                    
                    if keyword in related and related[keyword]['rising'] is not None:
                        rising = related[keyword]['rising']
                        for _, row in rising.head(5).iterrows():
                            score = int(row['value']) if row['value'] != 'Breakout' else 100
                            trend = self._create_trend(
                                category_id=category.id,
                                title=row['query'],
                                description=f"Rising search trend related to {keyword}",
                                source="google_trends",
                                popularity_score=min(score, 100),
                                related_keywords=[keyword]
                            )
                            if trend:
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
        """Scrape trends from category-specific RSS feeds"""
        trends = []
        category_name = category.name.lower().replace(" & ", "_").replace(" ", "_")
        
        # Get default feeds for this category
        feeds = RSS_FEEDS.get(category_name, [])
        
        # Add custom RSS feeds if this is a custom niche
        if hasattr(category, 'custom_rss_feeds') and category.custom_rss_feeds:
            feeds = feeds + category.custom_rss_feeds
        
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:5]:  # Get top 5 from each feed
                    title = entry.get('title', '')
                    description = entry.get('summary', entry.get('description', ''))
                    
                    # Clean HTML from description
                    if description:
                        soup = BeautifulSoup(description, 'html.parser')
                        description = soup.get_text()[:500]
                    
                    link = entry.get('link', '')
                    
                    trend = self._create_trend(
                        category_id=category.id,
                        title=title,
                        description=description,
                        source="rss",
                        source_url=link,
                        popularity_score=60  # Default score for RSS
                    )
                    if trend:
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
            
            response = self.session.get(
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
                        popularity_score=75
                    )
                    if trend:
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
    ) -> Optional[Trend]:
        """Create and save a trend to the database"""
        
        if not title or len(title.strip()) < 5:
            return None
        
        title = title.strip()[:255]  # Limit title length
        
        # Create a unique identifier based on title and category
        trend_hash = hashlib.md5(f"{category_id}:{title.lower()}".encode()).hexdigest()[:16]
        
        # Check if similar trend already exists
        existing = self.db.query(Trend).filter(
            Trend.category_id == category_id,
            Trend.title == title
        ).first()
        
        if existing:
            # Update existing trend with higher score if applicable
            if popularity_score > existing.popularity_score:
                existing.popularity_score = popularity_score
            existing.scraped_at = datetime.utcnow()
            existing.expires_at = datetime.utcnow() + timedelta(days=2)
            self.db.commit()
            return existing
        
        # Create new trend
        trend = Trend(
            category_id=category_id,
            title=title,
            description=description[:1000] if description else None,
            source=source,
            source_url=source_url,
            popularity_score=popularity_score,
            related_keywords=related_keywords or [],
            scraped_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=2)
        )
        
        try:
            self.db.add(trend)
            self.db.commit()
            self.db.refresh(trend)
            return trend
        except Exception as e:
            logger.error(f"Error saving trend: {e}")
            self.db.rollback()
            return None
    
    async def get_content_suggestions(
        self, 
        brand_id: int, 
        limit: int = 5
    ) -> List[Dict]:
        """
        Generate content suggestions based on trending topics relevant to a brand.
        This helps brands stay timely without constant manual monitoring.
        """
        from app.models import Brand
        
        brand = self.db.query(Brand).filter(Brand.id == brand_id).first()
        if not brand:
            return []
        
        suggestions = []
        
        # Get brand's categories
        brand_categories = brand.categories if hasattr(brand, 'categories') else []
        category_ids = [c.id for c in brand_categories] if brand_categories else []
        
        # If no categories, get all recent trends
        query = self.db.query(Trend).filter(
            Trend.expires_at > datetime.utcnow()
        )
        
        if category_ids:
            query = query.filter(Trend.category_id.in_(category_ids))
        
        # Get top trends by popularity
        top_trends = query.order_by(
            Trend.popularity_score.desc(),
            Trend.scraped_at.desc()
        ).limit(limit * 2).all()
        
        for trend in top_trends[:limit]:
            suggestion = {
                "trend_id": trend.id,
                "trend_title": trend.title,
                "trend_source": trend.source,
                "popularity_score": trend.popularity_score,
                "content_ideas": [
                    f"Share your take on: {trend.title}",
                    f"How {brand.name} relates to {trend.title}",
                    f"Tips inspired by trending topic: {trend.title}",
                ],
                "suggested_hashtags": self._generate_hashtags(trend),
                "best_post_times": ["9:00 AM", "12:00 PM", "6:00 PM"],
                "expires_at": trend.expires_at.isoformat() if trend.expires_at else None
            }
            suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_hashtags(self, trend: Trend) -> List[str]:
        """Generate relevant hashtags for a trend"""
        hashtags = []
        
        # Create hashtag from title
        title_words = re.sub(r'[^\w\s]', '', trend.title).split()
        if len(title_words) <= 3:
            hashtags.append("#" + "".join(w.capitalize() for w in title_words))
        else:
            # Use first 2-3 significant words
            significant = [w for w in title_words if len(w) > 3][:3]
            if significant:
                hashtags.append("#" + "".join(w.capitalize() for w in significant))
        
        # Add keywords as hashtags
        if trend.related_keywords:
            for kw in trend.related_keywords[:3]:
                hashtag = "#" + kw.replace(" ", "").capitalize()
                if hashtag not in hashtags:
                    hashtags.append(hashtag)
        
        # Add generic trending hashtags
        hashtags.extend(["#Trending", "#Viral", "#MustSee"])
        
        return hashtags[:7]  # Return max 7 hashtags


async def get_trend_scraper(db: Session) -> TrendScraperService:
    """Factory function for TrendScraperService"""
    return TrendScraperService(db)
