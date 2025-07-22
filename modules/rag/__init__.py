"""
rag/__init__.py - RAG Module Package

This module provides a unified interface for different RAG backends:
- ChromaDB: Local development (fast, full-featured)
- Hugging Face Datasets: Hugging Face Spaces (free, compatible)
- Pinecone: Production/cloud deployment (scalable, reliable)
- SimpleEmbeddingRAG: Lightweight local development

The adapter automatically chooses the best backend based on environment.
"""

from .rag_adapter import RAGAdapter, create_rag_backend, BackendType, RAGBackend

# Convenience imports
__all__ = [
    'RAGAdapter',
    'create_rag_backend', 
    'BackendType',
    'RAGBackend'
]

# Version info
__version__ = "1.0.0"
__author__ = "Stephen Saunders"
__description__ = "RAG Backend Adapter Pattern for Agentic Companion" 