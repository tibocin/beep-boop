"""
modules.core.rag.retriever - Unified RAG retriever with pluggable backends

This module provides the main retrieval interface that focuses on relevance reasoning
and supports multiple backend implementations through a driver pattern.
"""

from typing import List, Dict, Any, Optional
import openai
import json
from ..interfaces import BaseRetriever, RAGContext, ContextScope
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
        self.llm_client = openai.OpenAI()
        
        self._initialize_backend()
    
    def _initialize_backend(self):
        """Initialize the appropriate backend"""
        if self.backend_type == "auto":
            backend_type = self._detect_best_backend()
        else:
            backend_type = self.backend_type
            
        try:
            if backend_type == "chroma":
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
        try:
            import chromadb
            return "chroma"
        except ImportError:
            pass
            
        return "simple"
    
    def retrieve(self, query: str, context_scope: ContextScope, top_k: int = 5) -> List[RAGContext]:
        """
        Retrieve relevant context with reasoning
        
        Args:
            query: Search query
            context_scope: Scope of context to search (personal, professional, etc.)
            top_k: Maximum number of contexts to return
            
        Returns:
            List of relevant contexts with reasoning
        """
        # Get raw results from backend
        raw_results = self._get_raw_results(query, context_scope, top_k * 2)  # Get more for filtering
        
        # Use LLM to enhance relevance reasoning
        enhanced_contexts = self._enhance_with_reasoning(query, raw_results, context_scope)
        
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
    
    def _enhance_with_reasoning(self, query: str, raw_results: List[Dict[str, Any]], 
                               context_scope: ContextScope) -> List[RAGContext]:
        """Use LLM to enhance results with relevance reasoning"""
        if not raw_results:
            return []
            
        try:
            # Prepare context for LLM evaluation
            results_text = "\n\n".join([
                f"Result {i+1}:\nContent: {r.get('content', r.get('document', str(r)))}\nScore: {r.get('score', 0.0)}"
                for i, r in enumerate(raw_results[:10])  # Limit for LLM context
            ])
            
            system_prompt = f"""You are evaluating search results for relevance and providing reasoning.

Query: "{query}"
Context Scope: {context_scope.value}

For each result, determine:
1. How relevant it is to the query (0.0 to 1.0)
2. WHY it's relevant (reasoning)
3. What type of context it provides
4. Key topic tags

Return your evaluation as JSON."""

            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Evaluate these results:\n{results_text}"}
                ],
                functions=[{
                    "name": "evaluate_results",
                    "description": "Evaluate search results with reasoning",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "evaluations": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "result_index": {"type": "integer"},
                                        "relevance_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                        "relevance_reasoning": {"type": "string"},
                                        "context_type": {"type": "string"},
                                        "topic_tags": {"type": "array", "items": {"type": "string"}}
                                    },
                                    "required": ["result_index", "relevance_score", "relevance_reasoning", "context_type"]
                                }
                            }
                        },
                        "required": ["evaluations"]
                    }
                }],
                function_call={"name": "evaluate_results"}
            )
            
            if response.choices[0].message.function_call:
                evaluations = json.loads(response.choices[0].message.function_call.arguments)
                return self._create_rag_contexts(raw_results, evaluations["evaluations"])
            else:
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