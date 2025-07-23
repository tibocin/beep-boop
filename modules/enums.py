"""
enums.py - Enums and data structures for the Agentic Companion

This module contains all the enums and data structures used throughout
the application, extracted from the notebook.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
from pydantic import BaseModel, Field

class Subject(Enum):
    """Subject categories for request classification."""
    PERSONALITY = "personality"
    PROJECTS = "projects"
    VALUES = "values"
    TECHNICAL_SKILLS = "technical_skills"
    GENERAL = "general"
    EDUCATION = "education"
    INTERESTS = "interests"
    PRODUCT_FEATURES = "product_features"
    BUSINESS_IDEAS = "business_ideas"
    WORK_EXPERIENCE = "work_experience"
    FAVORITES = "favorites"
    LIFESTYLE = "lifestyle"
    FAMILY = "family"
    PARADIGMS = "paradigms"
    RELATIONSHIPS = "relationships"
    ROMANCE = "romance"
    SPIRITUALITY = "spirituality"
    RELIGION = "religion"
    PHILOSOPHY = "philosophy"
    ETHICS = "ethics"
    POLITICS = "politics"
    ECONOMICS = "economics"
    ACTIVITIES = "activities"
    WISDOM = "wisdom"
    DREAMS = "dreams"
    MEMORIES = "memories"
    AFFIRMATIONS = "affirmations"
    GOALS = "goals"
    FEEDBACK = "feedback"
    ATTRACTION = "attraction"

class Format(Enum):
    """Format types for response generation."""
    BACKGROUND = "background"
    PROBLEM_SOLVE = "problem_solve"
    EXPLANATION = "explanation"
    ETHICAL_DILEMMA = "ethical_dilemma"
    VALUE_ASSESSMENT = "value_assessment"
    PLANNING = "planning"
    RESEARCH = "research"
    REVIEW = "review"
    STORY = "story"
    QUESTION = "question"
    DATA = "data"
    ANALOGY = "analogy"
    METAPHOR = "metaphor"
    SYMBOLIC = "symbolic"

class Tone(Enum):
    """Tone types for response generation."""
    PROFESSIONAL = "professional"
    POETIC = "poetic"
    CASUAL = "casual"
    TECHNICAL = "technical"
    FORMAL = "formal"
    SHAMANIC_ESOTERIC = "shamanic_esoteric"
    PASSIONATE = "passionate"
    MATTER_OF_FACT = "matter_of_fact"
    NOETIC = "noetic"
    HUMOROUS = "humorous"
    WITTY = "witty"
    CONTEMPLATIVE = "contemplative"
    CONVERSATIONAL = "conversational"

class OutputStyle(Enum):
    """Output style types for response presentation and structure."""
    CONCISE = "concise"           # Brief, to the point
    STORYTELLING = "storytelling" # Narrative, engaging
    BULLET_POINTS = "bullet_points" # Structured, listed
    THOUGHT_PROVOKING = "thought_provoking" # Stimulating, challenging
    DEVOTIONAL = "devotional"     # Inspirational, uplifting
    CODE = "code"                 # Technical, code-focused
    DATA = "data"                 # Analytical, data-driven
    METAPHORICAL = "metaphorical" # Using metaphors and analogies
    STEP_BY_STEP = "step_by_step" # Sequential, instructional
    COMPARATIVE = "comparative"   # Comparing and contrasting

class ResponseFormat(Enum):
    """Response format types for length and delivery optimization."""
    CONCISE = "concise"           # 1-2 sentences, voice-friendly
    DETAILED = "detailed"         # 3-5 sentences, comprehensive
    EXPANDED = "expanded"         # 5+ sentences, deep dive
    VOICE_OPTIMIZED = "voice_optimized"  # Concise with voice-specific formatting
    CONVERSATIONAL = "conversational"    # Natural flow, medium length

@dataclass
class ReqPrompt:
    """Request prompt data structure with enhanced response format control."""
    subject: Subject
    format: Format
    tone: Tone
    style: OutputStyle          # How to present the information (storytelling, bullet points, etc.)
    response_format: ResponseFormat  # Length and delivery optimization (concise, detailed, etc.)
    score: float  # Confidence score 0-1
    feedback: str
    expansion_flags: Optional[dict] = None  # New: flags for conversation flow
    
    def __post_init__(self):
        """Initialize expansion flags if not provided."""
        if self.expansion_flags is None:
            self.expansion_flags = {
                "is_follow_up": False,
                "is_deep_dive": False,
                "conversation_depth": 0,
                "requires_examples": False,
                "voice_mode": False
            }
    
    def __str__(self):
        return f"{self.subject.value} | {self.format.value} | {self.tone.value} | {self.style.value} | {self.response_format.value} | Score: {self.score:.2f}"
    
    def get_max_tokens(self) -> int:
        """Get appropriate max_tokens based on response format."""
        token_limits = {
            ResponseFormat.CONCISE: 150,
            ResponseFormat.DETAILED: 300,
            ResponseFormat.EXPANDED: 500,
            ResponseFormat.VOICE_OPTIMIZED: 120,
            ResponseFormat.CONVERSATIONAL: 250
        }
        return token_limits.get(self.response_format, 200)
    
    def get_style_guidance(self) -> str:
        """Get style guidance based on response format and output style."""
        # Length guidance from response format
        length_guidance = {
            ResponseFormat.CONCISE: "Keep response concise and digestible (1-2 sentences)",
            ResponseFormat.DETAILED: "Provide comprehensive response with context and examples",
            ResponseFormat.EXPANDED: "Provide detailed, thorough response with extensive context",
            ResponseFormat.VOICE_OPTIMIZED: "Keep response very concise and voice-friendly (1 sentence preferred)",
            ResponseFormat.CONVERSATIONAL: "Provide natural, conversational response with good flow"
        }
        
        # Presentation guidance from output style
        presentation_guidance = {
            OutputStyle.CONCISE: "Present information in a brief, direct manner",
            OutputStyle.STORYTELLING: "Use narrative structure with engaging flow",
            OutputStyle.BULLET_POINTS: "Structure response with clear, organized points",
            OutputStyle.THOUGHT_PROVOKING: "Stimulate deeper thinking and reflection",
            OutputStyle.DEVOTIONAL: "Use inspirational and uplifting language",
            OutputStyle.CODE: "Include technical details and code examples",
            OutputStyle.DATA: "Present information with analytical precision",
            OutputStyle.METAPHORICAL: "Use metaphors and analogies to illustrate points",
            OutputStyle.STEP_BY_STEP: "Present information in sequential, instructional format",
            OutputStyle.COMPARATIVE: "Compare and contrast different approaches or concepts"
        }
        
        length = length_guidance.get(self.response_format, "Provide appropriate response")
        presentation = presentation_guidance.get(self.style, "Present information clearly")
        
        return f"{length}. {presentation}."

class ParsedRequest(BaseModel):
    """Parsed request structure with conversation context and response decisions."""
    response_objective: str = Field(description="The objective of the response")
    prompts: List[ReqPrompt] = Field(description="The prompts to be used to generate the response")
    conversation_context: Optional[dict] = Field(
        default_factory=dict,
        description="Conversation context including depth, follow-ups, etc."
    )
    response_decisions: Optional[dict] = Field(
        default_factory=dict,
        description="Response decisions including expansion, pivot, and default return flags"
    )
    
    def __post_init__(self):
        """Initialize response decisions if not provided."""
        if self.response_decisions is None:
            self.response_decisions = {
                "should_expand": False,
                "should_pivot": False,
                "return_to_default": False,
                "evaluation_required": True,
                "synthesis_required": False
            } 