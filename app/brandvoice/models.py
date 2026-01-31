"""
Brand Voice AI Models

Train AI to match your brand's unique writing style by analyzing
example content and creating a voice profile.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Boolean, Float, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class BrandVoice(Base):
    """
    Brand Voice profile trained from example content.
    
    Stores:
    - Training examples
    - Extracted style characteristics
    - Generated embeddings/prompts
    """
    __tablename__ = "brand_voices"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Training status
    is_trained = Column(Boolean, default=False)
    training_status = Column(String(50), default="pending")  # pending, training, completed, failed
    
    # Training examples (the content used to train the voice)
    training_examples = Column(JSON, default=list)  # List of example texts
    example_count = Column(Integer, default=0)
    
    # Extracted characteristics
    characteristics = Column(JSON, nullable=True)
    # Example: {
    #   "tone": "professional yet approachable",
    #   "sentence_length": "medium (15-20 words)",
    #   "vocabulary_level": "intermediate",
    #   "emoji_usage": "minimal",
    #   "punctuation_style": "standard",
    #   "common_phrases": ["Let's dive in", "Here's the thing"],
    #   "writing_patterns": ["starts with questions", "uses metaphors"],
    #   "call_to_action_style": "soft and inviting"
    # }
    
    # Generated system prompt for content generation
    voice_prompt = Column(Text, nullable=True)
    
    # Style strength (0-1, how strongly to apply the voice)
    default_strength = Column(Float, default=0.8)
    
    # Usage tracking
    times_used = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    # Quality metrics
    user_satisfaction_avg = Column(Float, nullable=True)  # Average rating of generated content
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    trained_at = Column(DateTime, nullable=True)
    
    # Relationships
    brand = relationship("Brand", backref="voice_profile")


class VoiceExample(Base):
    """
    Individual training example for brand voice.
    """
    __tablename__ = "voice_examples"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_voice_id = Column(Integer, ForeignKey('brand_voices.id', ondelete='CASCADE'), nullable=False)
    
    # Content
    content = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=True)  # social_post, blog, email, etc.
    platform = Column(String(50), nullable=True)  # twitter, instagram, linkedin, etc.
    
    # Analysis results (extracted from this example)
    analysis = Column(JSON, nullable=True)
    # Example: {
    #   "word_count": 45,
    #   "sentence_count": 3,
    #   "avg_sentence_length": 15,
    #   "emoji_count": 2,
    #   "hashtag_count": 3,
    #   "question_count": 1,
    #   "exclamation_count": 1,
    #   "detected_tone": "enthusiastic"
    # }
    
    # Quality indicator
    is_high_quality = Column(Boolean, default=True)  # User can mark low-quality examples
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    brand_voice = relationship("BrandVoice", backref="examples")


class VoiceGeneration(Base):
    """
    Track content generated using a brand voice.
    Used for quality feedback and improvement.
    """
    __tablename__ = "voice_generations"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_voice_id = Column(Integer, ForeignKey('brand_voices.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Generation details
    prompt = Column(Text, nullable=False)
    generated_content = Column(Text, nullable=False)
    voice_strength = Column(Float, default=0.8)
    
    # User feedback
    user_rating = Column(Integer, nullable=True)  # 1-5
    feedback_notes = Column(Text, nullable=True)
    voice_match_score = Column(Integer, nullable=True)  # 1-5, how well it matched brand voice
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    brand_voice = relationship("BrandVoice")
    user = relationship("User")


# Voice analysis prompts
VOICE_ANALYSIS_PROMPT = """Analyze the writing style of these examples and extract key characteristics.

Examples:
{examples}

Provide a detailed analysis in JSON format:
{{
    "overall_tone": "description of the overall tone",
    "formality_level": "formal/semi-formal/casual/very casual",
    "sentence_structure": "description of typical sentence patterns",
    "average_sentence_length": "short/medium/long",
    "vocabulary_complexity": "simple/intermediate/advanced",
    "emoji_usage": "none/minimal/moderate/heavy",
    "hashtag_style": "description if applicable",
    "punctuation_patterns": "notable punctuation habits",
    "common_phrases": ["list", "of", "recurring", "phrases"],
    "opening_patterns": "how content typically starts",
    "closing_patterns": "how content typically ends",
    "cta_style": "call-to-action approach",
    "unique_elements": ["distinctive", "style", "elements"],
    "avoid_patterns": ["things", "to", "avoid"]
}}"""

VOICE_PROMPT_TEMPLATE = """You are writing content that matches this specific brand voice:

Brand: {brand_name}
Voice Characteristics:
- Tone: {tone}
- Formality: {formality}
- Sentence Style: {sentence_style}
- Vocabulary: {vocabulary}
- Emoji Usage: {emoji_usage}

Key Patterns to Follow:
{patterns}

Common Phrases to Use:
{phrases}

Things to Avoid:
{avoid}

Voice Strength: {strength}% (higher = more strictly follow the voice)

Now generate content that authentically sounds like this brand."""
