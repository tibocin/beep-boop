"""
modules.core.semantic_analyzer - Semantic analysis and context understanding

This module provides robust alternatives to brittle keyword searches by using:
- LLM-based intent understanding
- Semantic similarity analysis
- Contextual relationship mapping
- Multi-dimensional relevance scoring
- Conversation flow analysis
"""

import openai
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import numpy as np
from dataclasses import dataclass

class ContextType(Enum):
    """Types of context that can be detected"""
    PROFESSIONAL = "professional"
    PERSONAL = "personal"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    SPIRITUAL = "spiritual"
    SOCIAL = "social"
    ACADEMIC = "academic"
    ENTERTAINMENT = "entertainment"
    CAREER = "career"
    CAREER_DEVELOPMENT = "career development"
    RELATIONAL = "relational"
    MIXED = "mixed"

@dataclass
class SemanticContext:
    """Semantic context analysis result"""
    primary_context: ContextType
    secondary_contexts: List[ContextType]
    confidence: float
    reasoning: str
    key_themes: List[str]
    emotional_tone: str
    complexity_level: str
    response_style: str

@dataclass
class IntentAnalysis:
    """Intent analysis result"""
    primary_intent: str
    secondary_intents: List[str]
    context_scope: str
    audience_type: str
    urgency_level: str
    depth_preference: str
    confidence: float
    reasoning: str

class SemanticAnalyzer:
    """
    Semantic analyzer that provides robust alternatives to keyword searches
    
    Uses LLM-based understanding to analyze:
    - Intent and context
    - Semantic relationships
    - Conversation flow
    - Audience and tone
    - Response requirements
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """Initialize the semantic analyzer"""
        self.model = model
        # Use unified LLM client instead of direct OpenAI
        from .llm_client import UnifiedLLMClient
        self.client = UnifiedLLMClient(
            ollama_model="llama3.1:8b",
            enable_fallback=False  # Force Ollama only
        )
        
    async def analyze_context(self, query: str, conversation_history: List[str] = None) -> SemanticContext:
        """
        Analyze the semantic context of a query
        
        Args:
            query: User's query
            conversation_history: Previous conversation turns
            
        Returns:
            SemanticContext with detailed analysis
        """
        try:
            # Build context for analysis
            context_info = ""
            if conversation_history:
                context_info = f"\n\nConversation History:\n" + "\n".join(conversation_history[-3:])
            
            system_prompt = """You are an expert at analyzing the semantic context of user queries.

Analyze the query and determine:

1. PRIMARY CONTEXT: The main domain/context (professional, personal, technical, creative, spiritual, social, academic, entertainment, mixed)

2. SECONDARY CONTEXTS: Other relevant contexts that apply

3. KEY THEMES: Main topics and themes being discussed

4. EMOTIONAL TONE: The emotional tone appropriate for response (conversational, professional, enthusiastic, contemplative, etc.)

5. COMPLEXITY LEVEL: How complex the response should be (simple, moderate, detailed, comprehensive)

6. RESPONSE STYLE: How to approach the response (direct, storytelling, analytical, supportive, etc.)

7. CONFIDENCE: How confident you are in this analysis (0.0 to 1.0)

8. REASONING: Why you made these determinations

Focus on understanding the deeper meaning and context, not just surface-level keywords."""

            system_prompt = """You are an expert at analyzing the semantic context of user queries.

Analyze the query and return a JSON response with these fields:
- primary_context: The main domain/context (professional, personal, technical, creative, spiritual, social, academic, entertainment, career, relational, mixed)
- secondary_contexts: List of other relevant contexts from the same options
- confidence: How confident you are (0.0 to 1.0)
- reasoning: Why you made these determinations
- key_themes: List of main topics and themes
- emotional_tone: The emotional tone (conversational, professional, enthusiastic, contemplative, etc.)
- complexity_level: How complex the response should be (simple, moderate, detailed, comprehensive)
- response_style: How to approach the response (direct, storytelling, analytical, supportive, etc.)

Return ONLY valid JSON, no other text."""

            response = await self.client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this query: '{query}'{context_info}"}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            response_text = self._extract_response_text(response)
            print(f"🔍 LLM Response: {response_text[:100]}...")
            
            # Try to parse as JSON
            try:
                data = json.loads(response_text)
                print(f"✅ JSON parsed successfully: {list(data.keys())}")
                
                # Safely convert context types with fallback
                def safe_context_type(context_str: str) -> ContextType:
                    try:
                        return ContextType(context_str)
                    except ValueError:
                        # Try to find a close match
                        context_lower = context_str.lower()
                        for ctx_type in ContextType:
                            if ctx_type.value.lower() in context_lower or context_lower in ctx_type.value.lower():
                                print(f"🔄 Mapped '{context_str}' to '{ctx_type.value}'")
                                return ctx_type
                        print(f"⚠️ Unknown context type '{context_str}', using MIXED")
                        return ContextType.MIXED
                
                return SemanticContext(
                    primary_context=safe_context_type(data.get("primary_context", "mixed")),
                    secondary_contexts=[safe_context_type(ctx) for ctx in data.get("secondary_contexts", [])],
                    confidence=float(data.get("confidence", 0.5)),
                    reasoning=data.get("reasoning", ""),
                    key_themes=data.get("key_themes", []),
                    emotional_tone=data.get("emotional_tone", "conversational"),
                    complexity_level=data.get("complexity_level", "moderate"),
                    response_style=data.get("response_style", "direct")
                )
                
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing failed: {e}")
                print(f"   Raw response: {response_text}")
                return self._fallback_context_analysis(query)
            
        except Exception as e:
            print(f"⚠️ Error in semantic context analysis: {e}")
            # Fallback to basic analysis
            return self._fallback_context_analysis(query)
    
    async def analyze_intent(self, query: str, conversation_history: List[str] = None) -> IntentAnalysis:
        """
        Analyze the intent and requirements of a query
        
        Args:
            query: User's query
            conversation_history: Previous conversation turns
            
        Returns:
            IntentAnalysis with detailed intent understanding
        """
        try:
            context_info = ""
            if conversation_history:
                context_info = f"\n\nConversation History:\n" + "\n".join(conversation_history[-3:])
            
            system_prompt = """You are an expert at understanding user intent from natural language.

Analyze the query and determine:

1. PRIMARY INTENT: What the user actually wants (in natural language)

2. SECONDARY INTENTS: Other aspects of what they're asking for

3. CONTEXT SCOPE: What domain of knowledge is relevant (personal, professional, creative, general, all)

4. AUDIENCE TYPE: Who they might be (employer, client, friend, family, etc.)

5. URGENCY LEVEL: How urgent this is (low, normal, high)

6. DEPTH PREFERENCE: How detailed they want the response (brief, moderate, comprehensive)

7. CONFIDENCE: How confident you are in this analysis (0.0 to 1.0)

8. REASONING: Why you made these determinations

Focus on understanding the deeper intent, not just surface-level requests."""

            system_prompt = """You are an expert at understanding user intent from natural language.

Analyze the query and return a JSON response with these fields:
- primary_intent: What the user actually wants (in natural language)
- secondary_intents: List of other aspects they're asking for
- context_scope: What domain of knowledge is relevant (personal, professional, creative, general, all)
- audience_type: Who they might be (employer, client, friend, family, etc.)
- urgency_level: How urgent this is (low, normal, high)
- depth_preference: How detailed they want the response (brief, moderate, comprehensive)
- confidence: How confident you are in this analysis (0.0 to 1.0)
- reasoning: Why you made these determinations

Return ONLY valid JSON, no other text."""

            response = await self.client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this query: '{query}'{context_info}"}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            response_text = self._extract_response_text(response)
            print(f"🎯 LLM Response: {response_text[:100]}...")
            
            # Try to parse as JSON
            try:
                data = json.loads(response_text)
                print(f"✅ JSON parsed successfully: {list(data.keys())}")
                
                return IntentAnalysis(
                    primary_intent=data.get("primary_intent", ""),
                    secondary_intents=data.get("secondary_intents", []),
                    context_scope=data.get("context_scope", "general"),
                    audience_type=data.get("audience_type", "general"),
                    urgency_level=data.get("urgency_level", "normal"),
                    depth_preference=data.get("depth_preference", "moderate"),
                    confidence=float(data.get("confidence", 0.5)),
                    reasoning=data.get("reasoning", "")
                )
                
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing failed: {e}")
                print(f"   Raw response: {response_text}")
                return self._fallback_intent_analysis(query)
            
        except Exception as e:
            print(f"⚠️ Error in intent analysis: {e}")
            return self._fallback_intent_analysis(query)
    
    async def calculate_semantic_similarity(self, query: str, contexts: List[str]) -> List[Tuple[str, float]]:
        """
        Calculate semantic similarity between query and contexts
        
        Args:
            query: User's query
            contexts: List of context strings to compare against
            
        Returns:
            List of (context, similarity_score) tuples
        """
        try:
            # Use UnifiedLLMClient embeddings for semantic similarity
            query_embedding = await self.client.get_embedding(query, model="text-embedding-3-small")
            
            context_embeddings = await self.client.get_embeddings_batch(contexts, model="text-embedding-3-small")
            
            similarities = []
            for i, context_embedding in enumerate(context_embeddings):
                similarity = self._cosine_similarity(query_embedding, context_embedding.embedding)
                similarities.append((contexts[i], similarity))
            
            # Sort by similarity score
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities
            
        except Exception as e:
            print(f"⚠️ Error calculating semantic similarity: {e}")
            return [(context, 0.5) for context in contexts]  # Fallback
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def _extract_response_text(self, response: Dict[str, Any]) -> str:
        """
        Extract text content from LLM response
        
        Handles both UnifiedLLMClient dict format and OpenAI object format
        """
        # Check if it's a unified client response (dict with 'text' key)
        if isinstance(response, dict) and 'text' in response:
            return response['text']
        
        # Check if it's OpenAI response object with choices
        if hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content
        
        # Fallback: try to access as dict with choices
        if isinstance(response, dict) and 'choices' in response:
            choices = response['choices']
            if choices and len(choices) > 0:
                return choices[0].get('message', {}).get('content', '')
        
        # Last resort: try to get any text-like content
        if isinstance(response, str):
            return response
        
        print(f"⚠️ Could not extract text from response: {type(response)}")
        return ""
    
    def _fallback_context_analysis(self, query: str) -> SemanticContext:
        """Fallback context analysis when LLM fails"""
        query_lower = query.lower()
        
        # Simple heuristics
        if any(word in query_lower for word in ["work", "job", "career", "project", "technical", "skill"]):
            primary_context = ContextType.PROFESSIONAL
        elif any(word in query_lower for word in ["spiritual", "meditation", "prayer", "values"]):
            primary_context = ContextType.SPIRITUAL
        elif any(word in query_lower for word in ["creative", "art", "music", "writing"]):
            primary_context = ContextType.CREATIVE
        else:
            primary_context = ContextType.PERSONAL
        
        return SemanticContext(
            primary_context=primary_context,
            secondary_contexts=[],
            confidence=0.6,
            reasoning="Fallback analysis using simple heuristics",
            key_themes=["general"],
            emotional_tone="conversational",
            complexity_level="moderate",
            response_style="direct"
        )
    
    def _fallback_intent_analysis(self, query: str) -> IntentAnalysis:
        """Fallback intent analysis when LLM fails"""
        return IntentAnalysis(
            primary_intent=f"User wants to {query[:50]}...",
            secondary_intents=[],
            context_scope="general",
            audience_type="general",
            urgency_level="normal",
            depth_preference="moderate",
            confidence=0.5,
            reasoning="Fallback analysis using simple heuristics"
        ) 