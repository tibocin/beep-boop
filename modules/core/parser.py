"""
modules/core/parser.py - Async LLM-powered request parser using OpenAI SDK

This module parses user requests to determine intent, extract key information,
and prepare structured prompts for the conversation pipeline.

Key Features:
- Async OpenAI SDK integration with streaming support
- Intent classification and entity extraction
- Voice mode adaptation
- Context-aware parsing
"""

import logging
import json
from typing import Dict, Any, Optional, Tuple, AsyncGenerator
from dataclasses import dataclass
from .llm_client import UnifiedLLMClient

logger = logging.getLogger(__name__)

@dataclass
class ParsedRequest:
    """Structured representation of a parsed user request"""
    intent: str
    entities: Dict[str, Any]
    context: Dict[str, Any]
    metadata: Dict[str, Any]
    confidence: float

class AsyncLLMParser:
    """
    Async LLM-powered parser using OpenAI SDK for request understanding
    
    Analyzes user input to extract intent, entities, and context
    for downstream processing in the conversation pipeline.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", ollama_model: str = "llama3.1:8b"):
        """
        Initialize the async LLM parser
        
        Args:
            model: OpenAI model to use for parsing (fallback)
            ollama_model: Ollama model to use for parsing (primary)
        """
        self.client = UnifiedLLMClient(
            ollama_model=ollama_model,
            openai_model=model
        )
        self.model = model
        self.ollama_model = ollama_model
        
        # System prompt for parsing
        self.parsing_prompt = """You are an intelligent request parser. Analyze the user's input and extract:

1. INTENT: What the user wants to accomplish
2. ENTITIES: Key information, names, topics, or parameters
3. CONTEXT: Relevant background or situational information
4. CONFIDENCE: How certain you are (0.0-1.0)

Respond in JSON format:
{
    "intent": "string",
    "entities": {"key": "value"},
    "context": {"key": "value"},
    "confidence": 0.95
}"""
        
        logger.info(f"Async LLM Parser initialized with model: {model}")
    
    async def parse_request(self, user_input: str, voice_mode: bool = False) -> Tuple[ParsedRequest, str]:
        """
        Parse user request to extract intent and structure (async)
        
        Args:
            user_input: Raw user input text
            voice_mode: Whether input is from voice (affects processing)
            
        Returns:
            Tuple of (ParsedRequest, objective_string)
        """
        try:
            # Prepare messages for parsing
            messages = [
                {"role": "user", "content": f"Parse this request: {user_input}"}
            ]
            
            # Get parsing response
            response = await self.client.chat_completion(
                messages=messages,
                system_prompt=self.parsing_prompt,
                temperature=0.1  # Low temperature for consistent parsing
            )
            
            # Parse JSON response
            parsed_data = json.loads(response["text"])
            
            # Create ParsedRequest object
            parsed_request = ParsedRequest(
                intent=parsed_data.get("intent", "general_conversation"),
                entities=parsed_data.get("entities", {}),
                context=parsed_data.get("context", {}),
                metadata={
                    "voice_mode": voice_mode,
                    "model": self.model,
                    "parsing_confidence": parsed_data.get("confidence", 0.5)
                },
                confidence=parsed_data.get("confidence", 0.5)
            )
            
            # Generate objective string
            objective = self._generate_objective(parsed_request)
            
            logger.info(f"Parsed request: {parsed_request.intent} (confidence: {parsed_request.confidence})")
            return parsed_request, objective
            
        except Exception as e:
            logger.error(f"Parsing failed: {str(e)}")
            # Fallback to basic parsing
            return self._fallback_parse(user_input, voice_mode)
    
    async def parse_request_stream(self, user_input: str, voice_mode: bool = False) -> AsyncGenerator[str, None]:
        """
        Stream parsing results as they become available (async generator)
        
        Args:
            user_input: Raw user input text
            voice_mode: Whether input is from voice
            
        Yields:
            Parsing insights as they're generated
        """
        try:
            # Prepare messages for parsing
            messages = [
                {"role": "user", "content": f"Parse this request step by step: {user_input}"}
            ]
            
            # Stream parsing response
            async for chunk in self.client.chat_completion_stream(
                messages=messages,
                system_prompt=self.parsing_prompt,
                temperature=0.1
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"Streaming parsing failed: {str(e)}")
            yield f"Parsing error: {str(e)}"
    
    def adapt_for_voice(self, parsed_request: ParsedRequest) -> ParsedRequest:
        """
        Adapt parsed request for voice interaction
        
        Args:
            parsed_request: Original parsed request
            
        Returns:
            Voice-adapted parsed request
        """
        # Voice-specific adaptations
        adapted_request = ParsedRequest(
            intent=parsed_request.intent,
            entities=parsed_request.entities,
            context=parsed_request.context,
            metadata={
                **parsed_request.metadata,
                "voice_mode": True,
                "voice_adapted": True
            },
            confidence=parsed_request.confidence
        )
        
        # Voice-specific intent adjustments
        if "search" in adapted_request.intent.lower():
            adapted_request.intent = "voice_search"
        elif "explain" in adapted_request.intent.lower():
            adapted_request.intent = "voice_explanation"
        
        return adapted_request
    
    def _generate_objective(self, parsed_request: ParsedRequest) -> str:
        """
        Generate objective string from parsed request
        
        Args:
            parsed_request: Parsed request object
            
        Returns:
            Objective string for downstream processing
        """
        intent = parsed_request.intent
        entities = parsed_request.entities
        
        if intent == "search":
            query = entities.get("query", "general information")
            return f"Search for information about: {query}"
        elif intent == "explain":
            topic = entities.get("topic", "the subject")
            return f"Explain {topic} in detail"
        elif intent == "summarize":
            content = entities.get("content", "the information")
            return f"Summarize {content}"
        else:
            return f"Engage in {intent} conversation"
    
    def _fallback_parse(self, user_input: str, voice_mode: bool) -> Tuple[ParsedRequest, str]:
        """
        Fallback parsing when LLM parsing fails
        
        Args:
            user_input: Raw user input
            voice_mode: Whether input is from voice
            
        Returns:
            Tuple of (ParsedRequest, objective_string)
        """
        # Simple keyword-based fallback
        input_lower = user_input.lower()
        
        if any(word in input_lower for word in ["search", "find", "look"]):
            intent = "search"
        elif any(word in input_lower for word in ["explain", "what is", "how"]):
            intent = "explain"
        elif any(word in input_lower for word in ["summarize", "summary"]):
            intent = "summarize"
        else:
            intent = "general_conversation"
        
        fallback_request = ParsedRequest(
            intent=intent,
            entities={"raw_input": user_input},
            context={},
            metadata={
                "voice_mode": voice_mode,
                "fallback_parsing": True,
                "model": self.model
            },
            confidence=0.3  # Low confidence for fallback
        )
        
        objective = self._generate_objective(fallback_request)
        return fallback_request, objective

# Backward compatibility alias
LLMParser = AsyncLLMParser