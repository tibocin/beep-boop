"""
modules.core.rag.retriever - Unified RAG retriever with pluggable backends

This module provides the main retrieval interface that focuses on relevance reasoning
and supports multiple backend implementations through a driver pattern.
"""

from typing import List, Dict, Any, Optional
import openai
import json
from ..interfaces import BaseRetriever, RAGContext, ContextScope
from ..semantic_analyzer import SemanticAnalyzer
from .drivers.simple import SimpleDriver
from .drivers.chroma import ChromaDriver

class UnifiedRetriever(BaseRetriever):
    """
    Unified RAG retriever with pluggable backends
    
    Emphasizes relevance reasoning over mechanical similarity scoring
    and supports multiple retrieval strategies.
    """
    
    def __init__(self, backend_type: str = "auto", **config):
        """
        Initialize the unified retriever
        
        Args:
            backend_type: "auto", "simple", "chroma", etc.
            **config: Backend-specific configuration
        """
        self.backend_type = backend_type
        self.config = config
        self.backend = None
        # Use unified LLM client instead of direct OpenAI
        from ..llm_client import UnifiedLLMClient
        self.llm_client = UnifiedLLMClient(
            ollama_model="llama3.1:8b",
            enable_fallback=False  # Force Ollama only
        )
        self.semantic_analyzer = SemanticAnalyzer(model="llama3.1:8b")
        
        self._initialize_backend()
    
    def _initialize_backend(self):
        """Initialize the appropriate backend"""
        if self.backend_type == "auto":
            backend_type = self._detect_best_backend()
        else:
            backend_type = self.backend_type
            
        try:
            if backend_type == "digi-core":
                from .drivers.digi_core import DigiCoreDriver
                self.backend = DigiCoreDriver(**self.config)
            elif backend_type == "chroma":
                self.backend = ChromaDriver(**self.config)
            elif backend_type == "simple":
                self.backend = SimpleDriver(**self.config)
            else:
                # Default to simple
                self.backend = SimpleDriver(**self.config)
                
            # Initialize the backend
            if hasattr(self.backend, 'initialize'):
                success = self.backend.initialize()
                if not success:
                    print(f"⚠️ Backend {backend_type} failed to initialize, falling back to simple")
                    self.backend = SimpleDriver(**self.config)
                    self.backend.initialize()
                    
        except Exception as e:
            print(f"⚠️ Error initializing {backend_type} backend ({e}), using simple")
            self.backend = SimpleDriver(**self.config)
            self.backend.initialize()
    
    def _detect_best_backend(self) -> str:
        """Detect the best available backend for current environment"""
        # Check if Digi-Core is available and enabled
        import os
        digi_core_enabled = os.getenv('DIGI_CORE_ENABLED', 'true').lower() == 'true'
        digi_core_api_key = os.getenv('DIGI_CORE_API_KEY')
        
        if digi_core_enabled and digi_core_api_key:
            print("🧠 Digi-Core detected - using as primary RAG backend")
            return "digi-core"
        
        # Fallback to ChromaDB if available
        try:
            import chromadb
            return "chroma"
        except ImportError:
            pass
            
        return "simple"
    
    async def retrieve(self, query: str, context_scope: ContextScope, top_k: int = 5) -> List[RAGContext]:
        """
        Retrieve relevant context with semantic analysis and reasoning
        
        Args:
            query: Search query
            context_scope: Scope of context to search (personal, professional, etc.)
            top_k: Maximum number of contexts to return
            
        Returns:
            List of relevant contexts with reasoning
        """
        # Step 1: Semantic analysis for robust context understanding
        semantic_context = await self.semantic_analyzer.analyze_context(query)
        intent_analysis = await self.semantic_analyzer.analyze_intent(query)
        
        # Step 2: Enhanced retrieval based on semantic analysis
        if context_scope == ContextScope.PROFESSIONAL or semantic_context.primary_context.value in ["professional", "technical"]:
            # Get more comprehensive results for professional contexts
            raw_results = self._get_raw_results(query, context_scope, top_k * 3)
            
            # Use semantic themes to get related context
            if semantic_context.key_themes:
                for theme in semantic_context.key_themes[:3]:  # Top 3 themes
                    theme_results = self._get_raw_results(theme, context_scope, top_k)
                    raw_results.extend(theme_results)
        else:
            # Standard retrieval for other contexts
            raw_results = self._get_raw_results(query, context_scope, top_k * 2)
            
            # Add context based on semantic themes
            if semantic_context.key_themes:
                for theme in semantic_context.key_themes[:2]:  # Top 2 themes
                    theme_results = self._get_raw_results(theme, context_scope, top_k // 2)
                    raw_results.extend(theme_results)
        
        # Step 3: Use LLM to enhance relevance reasoning with semantic context
                    enhanced_contexts = await self._enhance_with_semantic_reasoning(query, raw_results, context_scope, semantic_context, intent_analysis)
        
        # Return top_k results
        return enhanced_contexts[:top_k]
    
    def _get_raw_results(self, query: str, context_scope: ContextScope, num_results: int) -> List[Dict[str, Any]]:
        """Get raw similarity results from backend"""
        if not self.backend:
            return []
            
        try:
            # Convert context scope to filter if backend supports it
            scope_filter = self._context_scope_to_filter(context_scope)
            
            if hasattr(self.backend, 'query_similar'):
                return self.backend.query_similar(
                    query_text=query,
                    n_results=num_results,
                    filter_metadata=scope_filter
                )
            else:
                # Fallback for basic backends
                return self.backend.search(query, num_results)
                
        except Exception as e:
            print(f"⚠️ Error retrieving from backend: {e}")
            return []
    
    def _context_scope_to_filter(self, scope: ContextScope) -> Dict[str, Any]:
        """Convert context scope to backend filter"""
        # For now, return empty filter to avoid ChromaDB filtering issues
        # The LLM reasoning will handle relevance filtering instead
        return {}
    
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
    
    async def _enhance_with_semantic_reasoning(self, query: str, raw_results: List[Dict[str, Any]], 
                                        context_scope: ContextScope, semantic_context, intent_analysis) -> List[RAGContext]:
        """Use LLM to enhance results with semantic reasoning"""
        if not raw_results:
            return []
            
        try:
            # Prepare context for LLM evaluation with semantic analysis
            results_text = "\n\n".join([
                f"Result {i+1}:\nContent: {r.get('content', r.get('document', str(r)))}\nScore: {r.get('score', 0.0)}"
                for i, r in enumerate(raw_results[:10])  # Limit for LLM context
            ])
            
            # Add semantic context to the evaluation
            semantic_info = f"""
SEMANTIC ANALYSIS:
- Primary Context: {semantic_context.primary_context.value}
- Key Themes: {', '.join(semantic_context.key_themes)}
- Emotional Tone: {semantic_context.emotional_tone}
- Complexity Level: {semantic_context.complexity_level}

INTENT ANALYSIS:
- Primary Intent: {intent_analysis.primary_intent}
- Context Scope: {intent_analysis.context_scope}
- Audience Type: {intent_analysis.audience_type}
- Depth Preference: {intent_analysis.depth_preference}
"""
            
            system_prompt = f"""You are evaluating search results for relevance and providing reasoning.

Query: "{query}"
Context Scope: {context_scope.value}

{semantic_info}

For each result, determine:
1. How relevant it is to the query (0.0 to 1.0)
2. WHY it's relevant (reasoning)
3. What type of context it provides
4. Key topic tags
5. How well it matches the semantic context and intent

Return your evaluation as JSON."""

            response = await self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Evaluate these results:\n{results_text}"}
                ],
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=300  # Limit response length for faster processing
            )
            
            # Extract response text
            result_text = self._extract_response_text(response)
            
            # Try to parse as JSON, fallback to basic contexts
            try:
                evaluations = json.loads(result_text)
                if "evaluations" in evaluations:
                    return self._create_rag_contexts(raw_results, evaluations["evaluations"])
                else:
                    return self._create_basic_contexts(raw_results)
            except json.JSONDecodeError:
                # Fallback without LLM reasoning
                return self._create_basic_contexts(raw_results)
                
        except Exception as e:
            print(f"⚠️ LLM reasoning failed ({e}), using basic contexts")
            return self._create_basic_contexts(raw_results)
    
    def _create_rag_contexts(self, raw_results: List[Dict[str, Any]], 
                            evaluations: List[Dict[str, Any]]) -> List[RAGContext]:
        """Create RAGContext objects from results and LLM evaluations"""
        contexts = []
        
        for eval_data in evaluations:
            try:
                idx = eval_data["result_index"]
                if idx < len(raw_results):
                    raw_result = raw_results[idx]
                    
                    context = RAGContext(
                        content=raw_result.get('content', raw_result.get('document', str(raw_result))),
                        source=raw_result.get('source', 'knowledge_base'),
                        relevance_score=eval_data["relevance_score"],
                        relevance_reasoning=eval_data["relevance_reasoning"],
                        context_type=eval_data["context_type"],
                        topic_tags=eval_data.get("topic_tags", []),
                        metadata=raw_result.get('metadata', {})
                    )
                    contexts.append(context)
            except Exception as e:
                print(f"⚠️ Error creating context {idx}: {e}")
                continue
        
        # Sort by relevance score
        contexts.sort(key=lambda x: x.relevance_score, reverse=True)
        return contexts
    
    def _create_basic_contexts(self, raw_results: List[Dict[str, Any]]) -> List[RAGContext]:
        """Create basic RAGContext objects without LLM reasoning"""
        contexts = []
        
        for i, result in enumerate(raw_results):
            try:
                context = RAGContext(
                    content=result.get('content', result.get('document', str(result))),
                    source=result.get('source', 'knowledge_base'),
                    relevance_score=result.get('score', 0.5),
                    relevance_reasoning="Retrieved based on similarity matching",
                    context_type="general",
                    topic_tags=[],
                    metadata=result.get('metadata', {})
                )
                contexts.append(context)
            except Exception as e:
                print(f"⚠️ Error creating basic context {i}: {e}")
                continue
        
        return contexts
    
    def get_available_backends(self) -> List[str]:
        """Return list of available backend implementations"""
        available = ["simple"]
        
        try:
            import chromadb
            available.append("chroma")
        except ImportError:
            pass
            
        return available
    
    def initialize_from_yaml(self, yaml_files: List[str] = None):
        """Initialize backend with YAML data"""
        if self.backend and hasattr(self.backend, 'initialize_from_yaml'):
            return self.backend.initialize_from_yaml(yaml_files)
        return False