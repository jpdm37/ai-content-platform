"""
A/B Testing Service
===================

Enables A/B testing for content variations to optimize performance.

Features:
- Create A/B tests with multiple content variations
- Track performance metrics per variation
- Statistical significance calculation
- Auto-selection of winners
- Test templates for common scenarios
"""

import logging
import random
import math
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Float, Enum as SQLEnum
from sqlalchemy.orm import Session, relationship

from app.core.database import Base
from app.core.config import get_settings
from app.models.user import User
from app.models.models import Brand, GeneratedContent

logger = logging.getLogger(__name__)
settings = get_settings()


# ==================== Models ====================

class TestStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TestType(str, Enum):
    CAPTION = "caption"
    HASHTAGS = "hashtags"
    IMAGE = "image"
    POSTING_TIME = "posting_time"
    CTA = "cta"


class ABTest(Base):
    """A/B Test model"""
    __tablename__ = "ab_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    test_type = Column(SQLEnum(TestType), nullable=False)
    status = Column(SQLEnum(TestStatus), default=TestStatus.DRAFT)
    
    # Test configuration
    goal_metric = Column(String(50), default="engagement_rate")  # engagement_rate, clicks, conversions
    min_sample_size = Column(Integer, default=100)
    confidence_level = Column(Float, default=0.95)
    
    # Timing
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    auto_end_on_significance = Column(Boolean, default=True)
    
    # Results
    winner_variation_id = Column(Integer, nullable=True)
    is_significant = Column(Boolean, default=False)
    p_value = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    variations = relationship("ABTestVariation", back_populates="test", cascade="all, delete-orphan")


class ABTestVariation(Base):
    """Variation within an A/B test"""
    __tablename__ = "ab_test_variations"
    
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey('ab_tests.id', ondelete='CASCADE'), nullable=False)
    
    name = Column(String(100), nullable=False)  # e.g., "Control", "Variation A"
    is_control = Column(Boolean, default=False)
    
    # Content variations
    content = Column(Text)  # The actual content being tested
    content_data = Column(JSON)  # Additional data (hashtags, images, etc.)
    
    # Performance metrics
    impressions = Column(Integer, default=0)
    engagements = Column(Integer, default=0)  # likes + comments + shares
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    
    # Calculated metrics (updated periodically)
    engagement_rate = Column(Float, default=0.0)
    click_rate = Column(Float, default=0.0)
    conversion_rate = Column(Float, default=0.0)
    
    # Traffic allocation
    traffic_percent = Column(Integer, default=50)  # Percentage of traffic
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    test = relationship("ABTest", back_populates="variations")


# ==================== Test Templates ====================

AB_TEST_TEMPLATES = [
    {
        "id": "emoji_vs_no_emoji",
        "name": "Emoji vs No Emoji",
        "description": "Test if emojis improve engagement",
        "test_type": "caption",
        "variations": [
            {"name": "No Emoji", "instruction": "Write the caption without any emojis"},
            {"name": "With Emojis", "instruction": "Write the caption with relevant emojis"}
        ]
    },
    {
        "id": "short_vs_long_caption",
        "name": "Short vs Long Caption",
        "description": "Test optimal caption length",
        "test_type": "caption",
        "variations": [
            {"name": "Short (< 150 chars)", "instruction": "Write a concise caption under 150 characters"},
            {"name": "Long (300+ chars)", "instruction": "Write a detailed caption with 300+ characters"}
        ]
    },
    {
        "id": "question_vs_statement",
        "name": "Question vs Statement",
        "description": "Test if questions drive more engagement",
        "test_type": "caption",
        "variations": [
            {"name": "Statement", "instruction": "Write the caption as a statement"},
            {"name": "Question", "instruction": "Write the caption ending with a question to encourage comments"}
        ]
    },
    {
        "id": "hashtag_count",
        "name": "Few vs Many Hashtags",
        "description": "Test optimal hashtag quantity",
        "test_type": "hashtags",
        "variations": [
            {"name": "3-5 Hashtags", "instruction": "Use only 3-5 highly relevant hashtags"},
            {"name": "15-20 Hashtags", "instruction": "Use 15-20 hashtags mixing popular and niche"}
        ]
    },
    {
        "id": "cta_type",
        "name": "CTA Type",
        "description": "Test different call-to-action styles",
        "test_type": "cta",
        "variations": [
            {"name": "Soft CTA", "instruction": "Use a soft CTA like 'Learn more in our bio'"},
            {"name": "Direct CTA", "instruction": "Use a direct CTA like 'Click the link now!'"},
            {"name": "Question CTA", "instruction": "Use a question CTA like 'Ready to get started?'"}
        ]
    },
    {
        "id": "posting_time",
        "name": "Morning vs Evening",
        "description": "Test best posting time",
        "test_type": "posting_time",
        "variations": [
            {"name": "Morning (8-10 AM)", "instruction": "Schedule for 8-10 AM"},
            {"name": "Afternoon (12-2 PM)", "instruction": "Schedule for 12-2 PM"},
            {"name": "Evening (6-8 PM)", "instruction": "Schedule for 6-8 PM"}
        ]
    }
]


# ==================== Service ====================

class ABTestingService:
    """Service for managing A/B tests."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== Test Management ====================
    
    def create_test(
        self,
        user_id: int,
        name: str,
        test_type: str,
        variations: List[Dict[str, Any]],
        brand_id: int = None,
        description: str = None,
        goal_metric: str = "engagement_rate",
        min_sample_size: int = 100,
        confidence_level: float = 0.95
    ) -> ABTest:
        """Create a new A/B test."""
        
        if len(variations) < 2:
            raise ValueError("A/B test requires at least 2 variations")
        
        # Create test
        test = ABTest(
            user_id=user_id,
            brand_id=brand_id,
            name=name,
            description=description,
            test_type=TestType(test_type),
            goal_metric=goal_metric,
            min_sample_size=min_sample_size,
            confidence_level=confidence_level,
            status=TestStatus.DRAFT
        )
        
        self.db.add(test)
        self.db.flush()
        
        # Calculate equal traffic split
        traffic_per_variation = 100 // len(variations)
        
        # Create variations
        for i, var_data in enumerate(variations):
            variation = ABTestVariation(
                test_id=test.id,
                name=var_data.get("name", f"Variation {chr(65 + i)}"),
                is_control=i == 0,  # First variation is control
                content=var_data.get("content"),
                content_data=var_data.get("content_data"),
                traffic_percent=traffic_per_variation
            )
            self.db.add(variation)
        
        self.db.commit()
        self.db.refresh(test)
        
        return test
    
    def create_from_template(
        self,
        user_id: int,
        template_id: str,
        name: str,
        brand_id: int = None,
        base_content: str = None
    ) -> ABTest:
        """Create a test from a template."""
        
        template = next((t for t in AB_TEST_TEMPLATES if t["id"] == template_id), None)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        variations = []
        for var_template in template["variations"]:
            variations.append({
                "name": var_template["name"],
                "content": base_content,
                "content_data": {"instruction": var_template["instruction"]}
            })
        
        return self.create_test(
            user_id=user_id,
            name=name,
            test_type=template["test_type"],
            variations=variations,
            brand_id=brand_id,
            description=template["description"]
        )
    
    def start_test(self, user_id: int, test_id: int) -> ABTest:
        """Start an A/B test."""
        
        test = self._get_test(user_id, test_id)
        
        if test.status != TestStatus.DRAFT:
            raise ValueError("Test can only be started from draft status")
        
        if len(test.variations) < 2:
            raise ValueError("Test needs at least 2 variations")
        
        test.status = TestStatus.RUNNING
        test.start_date = datetime.utcnow()
        self.db.commit()
        
        return test
    
    def pause_test(self, user_id: int, test_id: int) -> ABTest:
        """Pause a running test."""
        
        test = self._get_test(user_id, test_id)
        
        if test.status != TestStatus.RUNNING:
            raise ValueError("Can only pause running tests")
        
        test.status = TestStatus.PAUSED
        self.db.commit()
        
        return test
    
    def resume_test(self, user_id: int, test_id: int) -> ABTest:
        """Resume a paused test."""
        
        test = self._get_test(user_id, test_id)
        
        if test.status != TestStatus.PAUSED:
            raise ValueError("Can only resume paused tests")
        
        test.status = TestStatus.RUNNING
        self.db.commit()
        
        return test
    
    def end_test(self, user_id: int, test_id: int, winner_id: int = None) -> ABTest:
        """End an A/B test and optionally declare winner."""
        
        test = self._get_test(user_id, test_id)
        
        if test.status not in [TestStatus.RUNNING, TestStatus.PAUSED]:
            raise ValueError("Test is not active")
        
        # Calculate final results
        self._calculate_results(test)
        
        # Determine winner
        if winner_id:
            test.winner_variation_id = winner_id
        else:
            test.winner_variation_id = self._determine_winner(test)
        
        test.status = TestStatus.COMPLETED
        test.end_date = datetime.utcnow()
        self.db.commit()
        
        return test
    
    def _get_test(self, user_id: int, test_id: int) -> ABTest:
        """Get test with ownership check."""
        
        test = self.db.query(ABTest).filter(
            ABTest.id == test_id,
            ABTest.user_id == user_id
        ).first()
        
        if not test:
            raise ValueError("Test not found")
        
        return test
    
    # ==================== Metrics & Results ====================
    
    def record_impression(self, test_id: int, variation_id: int):
        """Record an impression for a variation."""
        
        variation = self.db.query(ABTestVariation).filter(
            ABTestVariation.id == variation_id,
            ABTestVariation.test_id == test_id
        ).first()
        
        if variation:
            variation.impressions += 1
            self._update_rates(variation)
            self.db.commit()
    
    def record_engagement(self, test_id: int, variation_id: int, engagement_type: str = "like"):
        """Record an engagement for a variation."""
        
        variation = self.db.query(ABTestVariation).filter(
            ABTestVariation.id == variation_id,
            ABTestVariation.test_id == test_id
        ).first()
        
        if variation:
            variation.engagements += 1
            self._update_rates(variation)
            self.db.commit()
            
            # Check if test should auto-end
            test = variation.test
            if test.auto_end_on_significance:
                self._check_significance(test)
    
    def record_click(self, test_id: int, variation_id: int):
        """Record a click for a variation."""
        
        variation = self.db.query(ABTestVariation).filter(
            ABTestVariation.id == variation_id,
            ABTestVariation.test_id == test_id
        ).first()
        
        if variation:
            variation.clicks += 1
            self._update_rates(variation)
            self.db.commit()
    
    def record_conversion(self, test_id: int, variation_id: int):
        """Record a conversion for a variation."""
        
        variation = self.db.query(ABTestVariation).filter(
            ABTestVariation.id == variation_id,
            ABTestVariation.test_id == test_id
        ).first()
        
        if variation:
            variation.conversions += 1
            self._update_rates(variation)
            self.db.commit()
    
    def _update_rates(self, variation: ABTestVariation):
        """Update calculated rates for a variation."""
        
        if variation.impressions > 0:
            variation.engagement_rate = (variation.engagements / variation.impressions) * 100
            variation.click_rate = (variation.clicks / variation.impressions) * 100
        
        if variation.clicks > 0:
            variation.conversion_rate = (variation.conversions / variation.clicks) * 100
    
    def _calculate_results(self, test: ABTest):
        """Calculate final results for all variations."""
        
        for variation in test.variations:
            self._update_rates(variation)
        
        # Calculate statistical significance
        if len(test.variations) >= 2:
            control = next((v for v in test.variations if v.is_control), test.variations[0])
            
            for variation in test.variations:
                if variation.id != control.id:
                    p_value = self._calculate_p_value(control, variation, test.goal_metric)
                    if p_value is not None and p_value < (1 - test.confidence_level):
                        test.is_significant = True
                        test.p_value = p_value
                        break
    
    def _calculate_p_value(
        self,
        control: ABTestVariation,
        variation: ABTestVariation,
        metric: str
    ) -> Optional[float]:
        """Calculate p-value for statistical significance using Z-test."""
        
        # Get metric values
        if metric == "engagement_rate":
            p1 = control.engagements / max(control.impressions, 1)
            p2 = variation.engagements / max(variation.impressions, 1)
            n1 = control.impressions
            n2 = variation.impressions
        elif metric == "click_rate":
            p1 = control.clicks / max(control.impressions, 1)
            p2 = variation.clicks / max(variation.impressions, 1)
            n1 = control.impressions
            n2 = variation.impressions
        else:
            return None
        
        # Need minimum sample size
        if n1 < 30 or n2 < 30:
            return None
        
        # Pooled proportion
        p_pool = (control.engagements + variation.engagements) / (n1 + n2)
        
        if p_pool == 0 or p_pool == 1:
            return None
        
        # Standard error
        se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
        
        if se == 0:
            return None
        
        # Z-score
        z = (p2 - p1) / se
        
        # Two-tailed p-value (approximation)
        p_value = 2 * (1 - self._normal_cdf(abs(z)))
        
        return p_value
    
    def _normal_cdf(self, x: float) -> float:
        """Approximate normal CDF."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    def _check_significance(self, test: ABTest):
        """Check if test has reached significance and should auto-end."""
        
        # Check minimum sample size
        total_impressions = sum(v.impressions for v in test.variations)
        if total_impressions < test.min_sample_size * len(test.variations):
            return
        
        # Calculate significance
        self._calculate_results(test)
        
        if test.is_significant:
            test.winner_variation_id = self._determine_winner(test)
            test.status = TestStatus.COMPLETED
            test.end_date = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"A/B test {test.id} auto-completed with significance")
    
    def _determine_winner(self, test: ABTest) -> int:
        """Determine the winning variation based on goal metric."""
        
        metric_attr = f"{test.goal_metric.replace('_rate', '')}_rate" if '_rate' not in test.goal_metric else test.goal_metric
        
        best_variation = max(
            test.variations,
            key=lambda v: getattr(v, metric_attr, 0) or 0
        )
        
        return best_variation.id
    
    # ==================== Queries ====================
    
    def get_tests(
        self,
        user_id: int,
        status: str = None,
        brand_id: int = None,
        limit: int = 20
    ) -> List[ABTest]:
        """Get user's A/B tests."""
        
        query = self.db.query(ABTest).filter(ABTest.user_id == user_id)
        
        if status:
            query = query.filter(ABTest.status == TestStatus(status))
        
        if brand_id:
            query = query.filter(ABTest.brand_id == brand_id)
        
        return query.order_by(ABTest.created_at.desc()).limit(limit).all()
    
    def get_test_details(self, user_id: int, test_id: int) -> Dict[str, Any]:
        """Get detailed test results."""
        
        test = self._get_test(user_id, test_id)
        
        # Calculate current results
        self._calculate_results(test)
        
        variations_data = []
        for var in test.variations:
            variations_data.append({
                "id": var.id,
                "name": var.name,
                "is_control": var.is_control,
                "content": var.content,
                "content_data": var.content_data,
                "metrics": {
                    "impressions": var.impressions,
                    "engagements": var.engagements,
                    "clicks": var.clicks,
                    "conversions": var.conversions,
                    "engagement_rate": round(var.engagement_rate, 2),
                    "click_rate": round(var.click_rate, 2),
                    "conversion_rate": round(var.conversion_rate, 2)
                },
                "traffic_percent": var.traffic_percent,
                "is_winner": var.id == test.winner_variation_id
            })
        
        return {
            "id": test.id,
            "name": test.name,
            "description": test.description,
            "test_type": test.test_type.value,
            "status": test.status.value,
            "goal_metric": test.goal_metric,
            "confidence_level": test.confidence_level,
            "start_date": test.start_date.isoformat() if test.start_date else None,
            "end_date": test.end_date.isoformat() if test.end_date else None,
            "is_significant": test.is_significant,
            "p_value": round(test.p_value, 4) if test.p_value else None,
            "winner_variation_id": test.winner_variation_id,
            "variations": variations_data,
            "total_impressions": sum(v.impressions for v in test.variations),
            "sample_size_reached": sum(v.impressions for v in test.variations) >= test.min_sample_size * len(test.variations)
        }
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """Get available test templates."""
        return AB_TEST_TEMPLATES
    
    # ==================== Variation Selection ====================
    
    def get_variation_for_user(self, test_id: int, user_identifier: str) -> ABTestVariation:
        """Get consistent variation for a user (for serving content)."""
        
        test = self.db.query(ABTest).filter(
            ABTest.id == test_id,
            ABTest.status == TestStatus.RUNNING
        ).first()
        
        if not test:
            return None
        
        # Use hash for consistent assignment
        hash_value = hash(f"{test_id}:{user_identifier}") % 100
        
        cumulative = 0
        for variation in test.variations:
            cumulative += variation.traffic_percent
            if hash_value < cumulative:
                return variation
        
        return test.variations[0]  # Fallback


def get_ab_testing_service(db: Session) -> ABTestingService:
    return ABTestingService(db)
