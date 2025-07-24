"""
modules.core - Core architecture interfaces for the Agentic Companion

This package provides the foundational interfaces for the simplified architecture:
- parser: Request parsing to structured prompts and objectives
- retriever: Unified RAG interface with pluggable backends
- synthesizer: LLM response generation
- evaluator: Response evaluation and feedback loop
- context_manager: Conversation history and memory management

Design Philosophy:
- Favor LLM reasoning over brittle code checks
- Support voice mode and conversational flexibility
- Enable resume generation and deep explanations
- Maintain clear separation of concerns
"""

from .interfaces import (
    BaseParser,
    BaseRetriever, 
    BaseSynthesizer,
    BaseEvaluator,
    BaseContextManager,
    ReqPrompt,
    ResponseObjective,
    RAGContext,
    CandidateResponse,
    EvaluationScore
)

__version__ = "0.1.0"
__all__ = [
    "BaseParser",
    "BaseRetriever", 
    "BaseSynthesizer",
    "BaseEvaluator",
    "BaseContextManager",
    "ReqPrompt",
    "ResponseObjective", 
    "RAGContext",
    "CandidateResponse",
    "EvaluationScore"
]