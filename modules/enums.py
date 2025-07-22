"""
enums.py - Enums and data structures for the Agentic Companion

This module contains all the enums and data structures used throughout
the application, extracted from the notebook.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List
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

class OutputStyle(Enum):
    """Output style types for response generation."""
    CONCISE = "concise"
    STORYTELLING = "storytelling"
    DETAILED = "detailed"
    BULLET_POINTS = "bullet_points"
    THOUGHT_PROVOKING = "thought_provoking"
    CONVERSATIONAL = "conversational"
    DEVOTIONAL = "devotional"
    CODE = "code"
    DATA = "data"

@dataclass
class ReqPrompt:
    """Request prompt data structure."""
    subject: Subject
    format: Format
    tone: Tone
    style: OutputStyle
    score: float  # Confidence score 0-1
    feedback: str
    
    def __str__(self):
        return f"{self.subject.value} | {self.format.value} | {self.tone.value} | {self.style.value} | Score: {self.score:.2f}"

class ParsedRequest(BaseModel):
    """Parsed request structure."""
    response_objective: str = Field(description="The objective of the response")
    prompts: List[ReqPrompt] = Field(description="The prompts to be used to generate the response") 