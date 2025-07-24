"""
modules.core.rag - Unified RAG retrieval system

This module provides a consolidated RAG interface with pluggable backends
that emphasizes relevance reasoning over mechanical similarity scoring.
"""

from .retriever import UnifiedRetriever
from .drivers.simple import SimpleDriver
from .drivers.chroma import ChromaDriver

__all__ = ["UnifiedRetriever", "SimpleDriver", "ChromaDriver"]