"""
modules.core.interfaces - Base interfaces for simplified architecture

This module defines the core abstractions that enable flexible,
LLM-driven reasoning for conversational AI, resume generation,
and deep explanations.

Key Design Principles:
- LLM reasoning over rigid code logic
- Voice-mode friendly interfaces
- Conversational context awareness
- Extensible and pluggable components
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from enum import Enum

# =============================================================================
# Data Structures
# =============================================================================

class RequestType(Enum):
    """Types of user requests the system can handle"""
    CONVERSATION = "conversation"
    RESUME_GENERATION = "resume_generation"  
    EXPLANATION = "explanation"
    VOICE_INTERACTION = "voice_interaction"
    ANALYSIS = "analysis"
    CREATIVE = "creative"

class ContextScope(Enum):
    """Scope for context retrieval"""
    PERSONAL = "personal"
    PROFESSIONAL = "professional"
    CREATIVE = "creative"
    GENERAL = "general"
    ALL = "all"

@dataclass
class ReqPrompt:
    """
    Structured representation of a user request
    
    Focuses on intent and context rather than rigid categorization,
    supporting natural language flexibility for voice mode.
    """
    original_text: str
    intent: str  # Natural language description of user intent
    request_type: RequestType
    context_scope: ContextScope
    key_topics: List[str] = field(default_factory=list)
    emotional_tone: Optional[str] = None  # For voice mode sensitivity
    urgency_level: str = "normal"  # low, normal, high
    voice_mode: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass  
class ResponseObjective:
    """
    Describes what makes a good response for this request
    
    Uses natural language descriptions rather than rigid constraints,
    enabling LLM reasoning about response quality.
    """
    primary_goal: str  # What the response should achieve
    success_criteria: List[str]  # Natural language success indicators
    audience: str  # Who the response is for
    style_preference: str  # Conversational, formal, technical, etc.
    length_guidance: str  # Brief, detailed, comprehensive, etc.
    avoid_patterns: List[str] = field(default_factory=list)
    voice_considerations: Optional[str] = None  # For voice-friendly responses
    
@dataclass
class RAGContext:
    """
    Context retrieved from knowledge base
    
    Includes relevance reasoning to help LLM understand
    why this context was selected.
    """
    content: str
    source: str
    relevance_score: float
    relevance_reasoning: str  # Why this context is relevant
    context_type: str  # personal, professional, creative, etc.
    topic_tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CandidateResponse:
    """
    A generated response with metadata for evaluation
    """
    content: str
    confidence: float  # LLM's confidence in response quality
    reasoning: str  # Why this response was generated
    voice_friendly: bool = False
    estimated_tokens: Optional[int] = None
    generation_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EvaluationScore:
    """
    Evaluation of response quality using LLM reasoning
    
    Avoids rigid scoring in favor of reasoned assessment.
    """
    overall_score: float  # 0.0 to 1.0
    reasoning: str  # Natural language explanation of score
    strengths: List[str]  # What works well
    improvements: List[str]  # Suggested improvements
    meets_objective: bool
    voice_mode_appropriate: bool = True
    retry_recommended: bool = False
    retry_guidance: Optional[str] = None

# =============================================================================
# Base Interfaces
# =============================================================================

class BaseParser(ABC):
    """
    Converts natural language requests into structured prompts and objectives
    
    Emphasizes understanding user intent over rigid parsing rules.
    """
    
    @abstractmethod
    def parse_request(self, text: str, voice_mode: bool = False) -> tuple[ReqPrompt, ResponseObjective]:
        """
        Parse user request into structured format
        
        Args:
            text: User's request text
            voice_mode: Whether this is from voice interaction
            
        Returns:
            Tuple of (structured prompt, response objective)
        """
        pass
    
    @abstractmethod 
    def adapt_for_voice(self, req_prompt: ReqPrompt) -> ReqPrompt:
        """Adapt request for voice-friendly processing"""
        pass

class BaseRetriever(ABC):
    """
    Unified interface for context retrieval with pluggable backends
    
    Focuses on relevance reasoning over mechanical similarity scoring.
    """
    
    @abstractmethod
    def retrieve(self, query: str, context_scope: ContextScope, top_k: int = 5) -> List[RAGContext]:
        """
        Retrieve relevant context with reasoning
        
        Args:
            query: Search query
            context_scope: Scope of context to search
            top_k: Maximum number of contexts to return
            
        Returns:
            List of relevant contexts with reasoning
        """
        pass
    
    @abstractmethod
    def get_available_backends(self) -> List[str]:
        """Return list of available backend implementations"""
        pass

class BaseSynthesizer(ABC):
    """
    Generates responses using LLM with context awareness
    
    Supports multiple response modes including voice-optimized output.
    """
    
    @abstractmethod
    def generate(self, req_prompt: ReqPrompt, contexts: List[RAGContext], 
                objective: ResponseObjective) -> CandidateResponse:
        """
        Generate response using prompt, context, and objective
        
        Args:
            req_prompt: Structured user request
            contexts: Relevant context information
            objective: Response requirements and goals
            
        Returns:
            Generated response with metadata
        """
        pass
    
    @abstractmethod
    def optimize_for_voice(self, response: CandidateResponse) -> CandidateResponse:
        """Optimize response for voice output"""
        pass

class BaseEvaluator(ABC):
    """
    Evaluates response quality using LLM reasoning
    
    Provides feedback loop for iterative improvement.
    """
    
    @abstractmethod
    def evaluate(self, response: CandidateResponse, objective: ResponseObjective,
                original_request: str) -> EvaluationScore:
        """
        Evaluate response against objective using LLM reasoning
        
        Args:
            response: Generated response to evaluate
            objective: Original response objective
            original_request: User's original request
            
        Returns:
            Evaluation with reasoning and improvement suggestions
        """
        pass
    
    @abstractmethod
    def should_retry(self, evaluation: EvaluationScore, attempt_count: int) -> bool:
        """Determine if response should be regenerated"""
        pass

class BaseContextManager(ABC):
    """
    Manages conversation history and long-term memory
    
    Supports sliding window with intelligent summarization.
    """
    
    @abstractmethod
    def get_conversation_context(self, turns_back: int = 6) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        pass
    
    @abstractmethod
    def add_turn(self, user_input: str, assistant_response: str, metadata: Dict[str, Any]):
        """Add conversation turn to history"""
        pass
    
    @abstractmethod
    def summarize_history(self, keep_recent: int = 6) -> str:
        """Create intelligent summary of older conversation history"""
        pass
    
    @abstractmethod
    def get_long_term_memory(self) -> Dict[str, Any]:
        """Retrieve persistent user preferences and insights"""
        pass