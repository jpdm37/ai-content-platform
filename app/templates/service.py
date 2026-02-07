"""
Content Templates Service
=========================

Pre-built content templates for quick content generation.
Templates are categorized by use case and platform.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ==================== Template Categories ====================

TEMPLATE_CATEGORIES = [
    {
        "id": "product_launch",
        "name": "Product Launch",
        "description": "Templates for launching new products or services",
        "icon": "rocket"
    },
    {
        "id": "engagement",
        "name": "Engagement & Interaction",
        "description": "Posts designed to boost engagement and interactions",
        "icon": "message-circle"
    },
    {
        "id": "educational",
        "name": "Educational Content",
        "description": "Teach your audience something valuable",
        "icon": "book-open"
    },
    {
        "id": "promotional",
        "name": "Promotional",
        "description": "Sales, discounts, and special offers",
        "icon": "tag"
    },
    {
        "id": "storytelling",
        "name": "Brand Storytelling",
        "description": "Share your story and build connection",
        "icon": "heart"
    },
    {
        "id": "seasonal",
        "name": "Seasonal & Holiday",
        "description": "Holiday-themed and seasonal content",
        "icon": "calendar"
    },
    {
        "id": "behind_scenes",
        "name": "Behind the Scenes",
        "description": "Show the human side of your brand",
        "icon": "camera"
    },
    {
        "id": "user_generated",
        "name": "User Generated Content",
        "description": "Encourage and share customer content",
        "icon": "users"
    }
]


# ==================== Content Templates ====================

CONTENT_TEMPLATES = [
    # Product Launch Templates
    {
        "id": "product_launch_teaser",
        "category_id": "product_launch",
        "name": "Product Teaser",
        "description": "Build anticipation before a launch",
        "platforms": ["instagram", "twitter", "facebook"],
        "prompt_template": "Create a teaser post for an upcoming {product_type}. Build curiosity and excitement without revealing too much. Include a launch date or 'coming soon' message.",
        "variables": ["product_type", "launch_date"],
        "example_output": "Something big is coming... 👀\n\nWe've been working on something special that's going to change the way you {benefit}.\n\nMark your calendars: {launch_date}\n\n#ComingSoon #StayTuned",
        "best_for": ["New product announcements", "Feature updates", "Rebrands"],
        "tips": ["Use mystery and curiosity", "Include a specific date", "Create urgency"]
    },
    {
        "id": "product_launch_announcement",
        "category_id": "product_launch",
        "name": "Launch Announcement",
        "description": "Official product launch post",
        "platforms": ["instagram", "twitter", "facebook", "linkedin"],
        "prompt_template": "Create an exciting launch announcement for {product_name}. Highlight the main benefits: {benefits}. Target audience: {audience}. Include a clear call to action.",
        "variables": ["product_name", "benefits", "audience", "cta_link"],
        "example_output": "🚀 It's HERE! Introducing {product_name}\n\nWe built this for {audience} who want to {benefit_1}.\n\n✨ {benefit_1}\n✨ {benefit_2}\n✨ {benefit_3}\n\nTap the link in bio to get started!\n\n#NewLaunch #Innovation",
        "best_for": ["Product launches", "Service announcements", "App releases"],
        "tips": ["Lead with the value proposition", "Use emojis strategically", "Clear CTA"]
    },
    
    # Engagement Templates
    {
        "id": "question_post",
        "category_id": "engagement",
        "name": "Conversation Starter",
        "description": "Ask a question to drive comments",
        "platforms": ["instagram", "twitter", "facebook", "linkedin"],
        "prompt_template": "Create an engaging question post related to {topic} for a {industry} brand. The question should be easy to answer and encourage people to share their opinions or experiences.",
        "variables": ["topic", "industry"],
        "example_output": "Quick question for you... 🤔\n\nWhat's the ONE {topic} tip that changed everything for you?\n\nDrop it in the comments 👇 Let's share the knowledge!\n\n#Community #ShareYourWisdom",
        "best_for": ["Building community", "Understanding audience", "Boosting engagement"],
        "tips": ["Keep questions simple", "Make it relevant to your niche", "Engage with responses"]
    },
    {
        "id": "this_or_that",
        "category_id": "engagement",
        "name": "This or That",
        "description": "Fun comparison post for quick engagement",
        "platforms": ["instagram", "twitter"],
        "prompt_template": "Create a fun 'this or that' post comparing two options related to {topic}. Make it playful and easy to respond to.",
        "variables": ["topic", "option_a", "option_b"],
        "example_output": "This or That? 🤷‍♀️\n\n{option_a} OR {option_b}?\n\nComment your pick! No wrong answers here 😄\n\n#ThisOrThat #FunPoll",
        "best_for": ["Quick engagement", "Fun content", "Story engagement"],
        "tips": ["Keep options relatable", "Use in Stories too", "Follow up with results"]
    },
    {
        "id": "poll_post",
        "category_id": "engagement",
        "name": "Opinion Poll",
        "description": "Get audience opinions on a topic",
        "platforms": ["twitter", "linkedin"],
        "prompt_template": "Create a poll post asking the audience about {topic}. Provide 2-4 clear options and explain why their input matters.",
        "variables": ["topic", "options"],
        "example_output": "We want YOUR input! 🗳️\n\nWhat matters most to you when choosing a {topic}?\n\nA) {option_a}\nB) {option_b}\nC) {option_c}\nD) {option_d}\n\nVote below! Your feedback shapes what we build next.",
        "best_for": ["Market research", "Product decisions", "Community involvement"],
        "tips": ["Keep options balanced", "Explain the impact", "Share results later"]
    },
    
    # Educational Templates
    {
        "id": "tips_carousel",
        "category_id": "educational",
        "name": "Tips Carousel",
        "description": "Multi-slide educational content",
        "platforms": ["instagram", "linkedin"],
        "prompt_template": "Create a {number} tip carousel post about {topic} for {audience}. Each tip should be actionable and valuable. Include a hook for slide 1 and CTA for the last slide.",
        "variables": ["number", "topic", "audience"],
        "example_output": "Slide 1: {number} {topic} Tips You Need to Know 🎯\n\nSlide 2: Tip #1 - {tip_1}\n[Explanation]\n\nSlide 3: Tip #2 - {tip_2}\n[Explanation]\n\n...\n\nFinal Slide: Save this for later! ❤️ Which tip are you trying first?\n\n#Tips #Education #{topic}",
        "best_for": ["Establishing expertise", "Shareable content", "Building trust"],
        "tips": ["Start with a strong hook", "One tip per slide", "End with a CTA"]
    },
    {
        "id": "how_to_guide",
        "category_id": "educational",
        "name": "How-To Guide",
        "description": "Step-by-step instructional content",
        "platforms": ["instagram", "twitter", "linkedin"],
        "prompt_template": "Create a step-by-step guide on how to {goal} for {audience}. Break it down into {steps} simple steps. Make it actionable and beginner-friendly.",
        "variables": ["goal", "audience", "steps"],
        "example_output": "How to {goal} in {steps} Simple Steps 📝\n\nStep 1: {step_1}\nStep 2: {step_2}\nStep 3: {step_3}\n...\n\n💡 Pro tip: {bonus_tip}\n\nSave this for later and tag someone who needs to see it!\n\n#HowTo #Guide #{topic}",
        "best_for": ["Tutorials", "Problem solving", "Demonstrating expertise"],
        "tips": ["Keep steps simple", "Include visuals if possible", "Add a pro tip"]
    },
    {
        "id": "myth_buster",
        "category_id": "educational",
        "name": "Myth Buster",
        "description": "Debunk common misconceptions",
        "platforms": ["instagram", "twitter", "linkedin"],
        "prompt_template": "Create a myth-busting post about common misconceptions in {industry/topic}. Address the myth, explain why it's wrong, and share the truth.",
        "variables": ["industry", "myth", "truth"],
        "example_output": "🚫 MYTH: {myth}\n\n✅ TRUTH: {truth}\n\nHere's why this matters:\n{explanation}\n\nWhat other myths should we bust? Drop them below 👇\n\n#MythBusted #Facts #{industry}",
        "best_for": ["Building authority", "Educational content", "Sparking discussion"],
        "tips": ["Be respectful when correcting", "Back up with facts", "Invite more questions"]
    },
    
    # Promotional Templates
    {
        "id": "flash_sale",
        "category_id": "promotional",
        "name": "Flash Sale",
        "description": "Time-limited sale announcement",
        "platforms": ["instagram", "twitter", "facebook"],
        "prompt_template": "Create an urgent flash sale post for {product/service}. Discount: {discount}. Duration: {duration}. Create urgency without being pushy.",
        "variables": ["product", "discount", "duration", "code"],
        "example_output": "⚡ FLASH SALE ⚡\n\n{duration} only!\n\nGet {discount} off {product}\n\nUse code: {code}\n\n⏰ Ends {end_time}\n\nDon't sleep on this one!\n\n🔗 Link in bio\n\n#FlashSale #LimitedTime #Deal",
        "best_for": ["Quick revenue boost", "Inventory clearance", "Event promotions"],
        "tips": ["Create real urgency", "Make discount clear", "Simple checkout process"]
    },
    {
        "id": "testimonial_share",
        "category_id": "promotional",
        "name": "Customer Testimonial",
        "description": "Share customer success stories",
        "platforms": ["instagram", "twitter", "facebook", "linkedin"],
        "prompt_template": "Create a post sharing a customer testimonial about {product/service}. Customer: {customer_name}. Result: {result}. Make it feel authentic, not salesy.",
        "variables": ["product", "customer_name", "result", "quote"],
        "example_output": "What our customers say... 💬\n\n\"{quote}\" - {customer_name}\n\nWe love hearing stories like this! 🙌\n\n{customer_name} achieved {result} using {product}.\n\nWant results like this? Link in bio to get started.\n\n#CustomerLove #Testimonial #Results",
        "best_for": ["Social proof", "Building trust", "Conversion"],
        "tips": ["Use real testimonials", "Include specific results", "Get permission first"]
    },
    
    # Storytelling Templates
    {
        "id": "origin_story",
        "category_id": "storytelling",
        "name": "Brand Origin Story",
        "description": "Share how your brand started",
        "platforms": ["instagram", "linkedin"],
        "prompt_template": "Tell the origin story of {brand_name}. Why was it started? What problem did the founder want to solve? Make it personal and relatable.",
        "variables": ["brand_name", "founder", "problem", "mission"],
        "example_output": "The story behind {brand_name}... 📖\n\n{year} ago, I was struggling with {problem}.\n\nI couldn't find a solution that actually worked, so I decided to build one.\n\nToday, {brand_name} helps {audience} {benefit}.\n\nThis is just the beginning. Thank you for being part of our journey. ❤️\n\n#OurStory #WhyWeStarted #{brand}",
        "best_for": ["Brand building", "Emotional connection", "Authenticity"],
        "tips": ["Be vulnerable", "Focus on the 'why'", "Connect to customer pain points"]
    },
    {
        "id": "milestone_celebration",
        "category_id": "storytelling",
        "name": "Milestone Celebration",
        "description": "Celebrate business achievements",
        "platforms": ["instagram", "twitter", "linkedin"],
        "prompt_template": "Create a milestone celebration post for reaching {milestone}. Thank the community and share what's next.",
        "variables": ["milestone", "achievement", "next_goal"],
        "example_output": "🎉 WE DID IT!\n\n{milestone}!\n\nThis wouldn't be possible without YOU - our amazing community.\n\nWhen we started, we never imagined we'd reach this point. Every {action} from you has helped us get here.\n\nWhat's next? {next_goal}\n\nThank you from the bottom of our hearts. Here's to the next milestone! 🚀\n\n#Milestone #ThankYou #Community",
        "best_for": ["Community building", "Showing growth", "Gratitude"],
        "tips": ["Be genuinely grateful", "Include the community", "Tease what's next"]
    },
    
    # Behind the Scenes Templates
    {
        "id": "day_in_life",
        "category_id": "behind_scenes",
        "name": "Day in the Life",
        "description": "Show a typical day at your company",
        "platforms": ["instagram", "tiktok"],
        "prompt_template": "Create a 'day in the life' post showing what a typical day looks like at {company}. Make it relatable and show the human side.",
        "variables": ["company", "role", "highlights"],
        "example_output": "A day in the life at {company} ☀️\n\n7:00 AM - {morning_routine}\n9:00 AM - {work_start}\n12:00 PM - {midday}\n3:00 PM - {afternoon}\n6:00 PM - {wrap_up}\n\nNo two days are exactly the same, but we love what we do! 💪\n\nWhat does your typical day look like?\n\n#DayInTheLife #BehindTheScenes #WorkLife",
        "best_for": ["Humanizing brand", "Recruitment", "Building connection"],
        "tips": ["Keep it real", "Show personality", "Include team members"]
    },
    {
        "id": "team_spotlight",
        "category_id": "behind_scenes",
        "name": "Team Member Spotlight",
        "description": "Highlight a team member",
        "platforms": ["instagram", "linkedin"],
        "prompt_template": "Create a team spotlight post for {team_member}. Role: {role}. Include fun facts and what they love about working at {company}.",
        "variables": ["team_member", "role", "company", "fun_facts"],
        "example_output": "Meet {team_member}! 👋\n\nRole: {role}\nTime at {company}: {tenure}\n\n3 things to know about {first_name}:\n1. {fun_fact_1}\n2. {fun_fact_2}\n3. {fun_fact_3}\n\nFavorite part of the job: \"{quote}\"\n\nWe're lucky to have {first_name} on the team! 🌟\n\n#MeetTheTeam #TeamSpotlight #{company}",
        "best_for": ["Team culture", "Recruitment", "Building trust"],
        "tips": ["Get team member approval", "Include personality", "Use their actual words"]
    },
    
    # Seasonal Templates
    {
        "id": "new_year",
        "category_id": "seasonal",
        "name": "New Year Post",
        "description": "New year, fresh start content",
        "platforms": ["instagram", "twitter", "facebook", "linkedin"],
        "prompt_template": "Create a New Year post for {brand}. Reflect on the past year's achievements and share goals/excitement for the new year.",
        "variables": ["brand", "year", "achievements", "goals"],
        "example_output": "Happy New Year! 🎊\n\nWhat a year it's been!\n\nIn {past_year}, we:\n✨ {achievement_1}\n✨ {achievement_2}\n✨ {achievement_3}\n\nIn {new_year}, we're excited to:\n🎯 {goal_1}\n🎯 {goal_2}\n\nThank you for being part of our journey. Here's to an amazing year ahead! 🥂\n\n#HappyNewYear #{new_year} #NewBeginnings",
        "best_for": ["Year transitions", "Goal setting", "Community connection"],
        "tips": ["Be reflective", "Share concrete achievements", "Include community in goals"]
    },
    {
        "id": "thanksgiving",
        "category_id": "seasonal",
        "name": "Thanksgiving/Gratitude",
        "description": "Express gratitude to your community",
        "platforms": ["instagram", "twitter", "facebook", "linkedin"],
        "prompt_template": "Create a Thanksgiving/gratitude post for {brand}. Express genuine thanks to customers, team, and community.",
        "variables": ["brand", "thanks_to"],
        "example_output": "This season, we're grateful for... 🧡\n\n• Our incredible customers who believe in us\n• Our dedicated team who makes magic happen\n• The community that supports and challenges us to grow\n• Every milestone we've hit together\n\nFrom our family to yours, Happy Thanksgiving! 🦃\n\nWhat are you grateful for this year?\n\n#Thanksgiving #Grateful #ThankYou",
        "best_for": ["Building relationships", "Showing humanity", "Holiday engagement"],
        "tips": ["Be specific about gratitude", "Include team and customers", "Keep it genuine"]
    },
    
    # User Generated Content Templates
    {
        "id": "ugc_request",
        "category_id": "user_generated",
        "name": "UGC Request",
        "description": "Encourage customers to share content",
        "platforms": ["instagram", "twitter"],
        "prompt_template": "Create a post encouraging customers to share their experience with {product/brand}. Include a branded hashtag and what they might win/receive.",
        "variables": ["product", "hashtag", "incentive"],
        "example_output": "Show us your {product} setup! 📸\n\nWe love seeing how you use {product} in your daily life.\n\nShare your photo with #{hashtag} for a chance to be featured!\n\n{incentive}\n\nCan't wait to see your creativity! ✨\n\n#{hashtag} #Community #ShareYours",
        "best_for": ["Building community", "Social proof", "Content creation"],
        "tips": ["Make sharing easy", "Feature submitted content", "Offer incentives"]
    },
    {
        "id": "ugc_feature",
        "category_id": "user_generated",
        "name": "Customer Feature",
        "description": "Showcase customer-created content",
        "platforms": ["instagram", "twitter", "facebook"],
        "prompt_template": "Create a post featuring user-generated content from {customer}. Celebrate their content and thank them for sharing.",
        "variables": ["customer", "content_description"],
        "example_output": "📸 Community Spotlight!\n\nLook at this amazing {content_description} from @{customer}!\n\nWe're constantly blown away by how creative our community is. Thank you for sharing this with us! 🙌\n\nWant to be featured? Tag us in your posts and use #{hashtag}!\n\n#CommunitySpotlight #CustomerLove #UGC",
        "best_for": ["Social proof", "Community appreciation", "Authentic content"],
        "tips": ["Always credit the creator", "Get permission first", "Engage with the creator"]
    }
]


class ContentTemplatesService:
    """Service for managing and using content templates."""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all template categories."""
        return TEMPLATE_CATEGORIES
    
    def get_templates(
        self,
        category_id: str = None,
        platform: str = None,
        search: str = None
    ) -> List[Dict[str, Any]]:
        """Get templates with optional filtering."""
        templates = CONTENT_TEMPLATES.copy()
        
        if category_id:
            templates = [t for t in templates if t["category_id"] == category_id]
        
        if platform:
            templates = [t for t in templates if platform in t["platforms"]]
        
        if search:
            search_lower = search.lower()
            templates = [
                t for t in templates 
                if search_lower in t["name"].lower() 
                or search_lower in t["description"].lower()
            ]
        
        return templates
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by ID."""
        return next((t for t in CONTENT_TEMPLATES if t["id"] == template_id), None)
    
    def get_templates_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get templates grouped by category."""
        result = {}
        for category in TEMPLATE_CATEGORIES:
            result[category["id"]] = {
                "category": category,
                "templates": [t for t in CONTENT_TEMPLATES if t["category_id"] == category["id"]]
            }
        return result
    
    def generate_from_template(
        self,
        template_id: str,
        variables: Dict[str, str],
        brand_voice: str = None
    ) -> str:
        """Generate a prompt from a template with variables filled in."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        prompt = template["prompt_template"]
        
        # Fill in variables
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{key}}}", value)
        
        # Add brand voice if provided
        if brand_voice:
            prompt += f"\n\nWrite in this voice/tone: {brand_voice}"
        
        return prompt
    
    def get_popular_templates(self, limit: int = 6) -> List[Dict[str, Any]]:
        """Get popular/recommended templates."""
        # In a real implementation, this would be based on usage data
        popular_ids = [
            "question_post",
            "tips_carousel",
            "product_launch_announcement",
            "testimonial_share",
            "team_spotlight",
            "how_to_guide"
        ]
        return [t for t in CONTENT_TEMPLATES if t["id"] in popular_ids][:limit]
    
    def get_templates_for_goal(self, user_goal: str) -> List[Dict[str, Any]]:
        """Get recommended templates based on user's goal."""
        goal_to_categories = {
            "personal_brand": ["storytelling", "educational", "behind_scenes", "engagement"],
            "business_marketing": ["promotional", "product_launch", "testimonial", "educational"],
            "content_creator": ["engagement", "educational", "behind_scenes", "user_generated"],
            "agency": ["promotional", "product_launch", "storytelling", "educational"],
            "side_hustle": ["promotional", "product_launch", "educational", "engagement"]
        }
        
        recommended_categories = goal_to_categories.get(user_goal, ["engagement", "educational"])
        
        templates = []
        for cat_id in recommended_categories:
            templates.extend([t for t in CONTENT_TEMPLATES if t["category_id"] == cat_id])
        
        return templates[:12]  # Limit to 12 recommendations


def get_templates_service(db: Session = None) -> ContentTemplatesService:
    return ContentTemplatesService(db)
