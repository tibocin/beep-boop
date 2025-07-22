"""
rag_adapter.py - RAG Backend Adapter Pattern

This module provides a unified interface for different RAG backends:
- ChromaDB: Local development (fast, full-featured)
- Hugging Face Datasets: Hugging Face Spaces (free, compatible)
- Pinecone: Production/cloud deployment (scalable, reliable)

The adapter automatically chooses the best backend based on environment.
"""

import os
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from enum import Enum

class BackendType(Enum):
    """Available RAG backend types."""
    SIMPLE = "simple"
    CHROMA = "chroma"
    HUGGINGFACE = "huggingface"
    PINECONE = "pinecone"
    OPENAI = "openai"

class RAGBackend(ABC):
    """Abstract base class for RAG backends."""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the backend. Returns True if successful."""
        pass
    
    @abstractmethod
    def add_documents(self, documents: List[Dict]) -> bool:
        """Add documents to the knowledge base."""
        pass
    
    @abstractmethod
    def query_similar(self, 
                     query_text: str, 
                     n_results: int = 3,
                     filter_metadata: Dict = None,
                     subject_filter: str = None) -> List[Dict]:
        """Query for similar documents."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict:
        """Get backend statistics."""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Clear all data from the backend."""
        pass

class RAGAdapter:
    """Main adapter that chooses and manages the appropriate RAG backend."""
    
    def __init__(self, backend_type: str = "auto", **kwargs):
        """
        Initialize the RAG adapter.
        
        Args:
            backend_type: "auto", "chroma", "huggingface", or "pinecone"
            **kwargs: Backend-specific configuration
        """
        self.backend_type = backend_type
        self.config = kwargs
        self.backend = None
        self._initialize_backend()
    
    def _initialize_backend(self):
        """Initialize the appropriate backend based on type and environment."""
        if self.backend_type == "auto":
            backend_type = self._detect_best_backend()
        else:
            backend_type = BackendType(self.backend_type)
        
        print(f"🔄 Initializing {backend_type.value} backend...")
        
        try:
            if backend_type == BackendType.SIMPLE:
                from .rag_simple import SimpleEmbeddingRAG
                self.backend = SimpleEmbeddingRAG(**self.config)
            elif backend_type == BackendType.CHROMA:
                from .rag_chroma import ChromaDBBackend
                self.backend = ChromaDBBackend(**self.config)
            elif backend_type == BackendType.HUGGINGFACE:
                from .rag_huggingface import HuggingFaceBackend
                self.backend = HuggingFaceBackend(**self.config)
            elif backend_type == BackendType.PINECONE:
                from .rag_pinecone import PineconeBackend
                self.backend = PineconeBackend(**self.config)
            elif backend_type == BackendType.OPENAI:
                from .rag_openai import OpenAIEmbeddingRAG
                self.backend = OpenAIEmbeddingRAG(**self.config)
            
            # Initialize the backend
            if self.backend.initialize():
                print(f"✅ {backend_type.value} backend initialized successfully")
            else:
                print(f"❌ Failed to initialize {backend_type.value} backend")
                
        except ImportError as e:
            print(f"❌ Backend {backend_type.value} not available: {e}")
            # Fallback to next best option
            self._fallback_backend()
        except Exception as e:
            print(f"❌ Error initializing {backend_type.value} backend: {e}")
            self._fallback_backend()
    
    def _detect_best_backend(self) -> BackendType:
        """Detect the best backend for the current environment."""
        
        # Check if running on Hugging Face Spaces
        if os.getenv("SPACE_ID") or os.getenv("HF_SPACE_ID"):
            print("🌐 Detected Hugging Face Spaces environment")
            return BackendType.HUGGINGFACE
        
        # Check if running on other cloud platforms
        if os.getenv("PINECONE_API_KEY"):
            print("☁️ Detected Pinecone configuration")
            return BackendType.PINECONE
        
        # Try ChromaDB first (if available)
        try:
            import chromadb
            print("🎨 Using ChromaDB for local development")
            return BackendType.CHROMA
        except ImportError:
            pass
        
        # Fall back to SimpleEmbeddingRAG
        try:
            import sentence_transformers
            print("💻 Using SimpleEmbeddingRAG for local development")
            return BackendType.SIMPLE
        except ImportError:
            print("⚠️ No advanced backends available, using basic RAG")
            return BackendType.SIMPLE
    
    def _fallback_backend(self):
        """Fallback to a simpler backend if primary fails."""
        print("🔄 Attempting fallback to Hugging Face backend...")
        try:
            from .rag_huggingface import HuggingFaceBackend
            self.backend = HuggingFaceBackend(**self.config)
            if self.backend.initialize():
                print("✅ Fallback to Hugging Face backend successful")
            else:
                print("❌ All backends failed")
        except Exception as e:
            print(f"❌ Fallback failed: {e}")
    
    # Delegate all methods to the backend
    def add_documents(self, documents: List[Dict]) -> bool:
        """Add documents to the knowledge base."""
        if self.backend:
            return self.backend.add_documents(documents)
        return False
    
    def query_similar(self, 
                     query_text: str, 
                     n_results: int = 3,
                     filter_metadata: Dict = None,
                     subject_filter: str = None) -> List[Dict]:
        """Query for similar documents."""
        if self.backend:
            return self.backend.query_similar(
                query_text, n_results, filter_metadata, subject_filter
            )
        return []
    
    def get_context_for_prompts(self, 
                               query: str, 
                               prompts: List, 
                               max_chunks_per_prompt: int = 2) -> str:
        """Get context for multiple prompts, prioritizing subject-relevant content."""
        if not self.backend:
            return ""
        
        all_contexts = []
        
        for prompt in prompts:
            # Get subject-specific context
            subject_context = self.query_similar(
                query, 
                n_results=max_chunks_per_prompt,
                subject_filter=prompt.subject.value
            )
            
            # If no subject-specific results, get general context
            if not subject_context:
                subject_context = self.query_similar(
                    query, 
                    n_results=max_chunks_per_prompt
                )
            
            # Add context for this prompt
            if subject_context:
                context_texts = [result['text'] for result in subject_context]
                all_contexts.extend(context_texts)
        
        # Combine all contexts
        combined_context = " ".join(all_contexts)
        return combined_context
    
    def get_stats(self) -> Dict:
        """Get backend statistics."""
        if self.backend:
            stats = self.backend.get_stats()
            stats['backend_type'] = self.backend_type
            return stats
        return {"error": "No backend available"}
    
    def clear(self) -> bool:
        """Clear all data from the backend."""
        if self.backend:
            return self.backend.clear()
        return False
    
    def get_backend_info(self) -> Dict:
        """Get information about the current backend."""
        return {
            "backend_type": self.backend_type,
            "backend_class": self.backend.__class__.__name__ if self.backend else None,
            "available": self.backend is not None
        }

# Convenience function for easy backend creation
def create_rag_backend(backend_type: str = "auto", **kwargs) -> RAGAdapter:
    """Create a RAG backend adapter with the specified configuration."""
    return RAGAdapter(backend_type, **kwargs) 