"""
rag.py - RAG (Retrieval-Augmented Generation) engine

This module handles context retrieval from knowledge bases
and provides relevant information for response generation.
"""

import yaml
from typing import List, Dict, Optional
import os

class RAGEngine:
    """RAG engine for context retrieval."""
    
    def __init__(self, yaml_files: List[str] = None):
        """
        Initialize the RAG engine.
        
        Args:
            yaml_files: List of YAML files to load as knowledge base
        """
        if yaml_files is None:
            yaml_files = ["projects.yaml"]
        
        self.yaml_files = yaml_files
        self.chunks = self._load_all_chunks()
    
    def _load_yaml_chunks(self, path: str) -> List[str]:
        """Load YAML data and convert to text chunks for RAG."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            
            chunks = []
            for section, content in data.items():
                if isinstance(content, dict):
                    for key, value in content.items():
                        if isinstance(value, list):
                            chunks.append(f"{section} - {key}: {', '.join(value)}")
                        else:
                            chunks.append(f"{section} - {key}: {value}")
                else:
                    chunks.append(f"{section}: {content}")
            
            return chunks
        
        except FileNotFoundError:
            print(f"⚠️ {path} not found!")
            return []
        except Exception as e:
            print(f"❌ Error loading {path}: {str(e)}")
            return []
    
    def _load_all_chunks(self) -> List[str]:
        """Load chunks from all YAML files."""
        all_chunks = []
        for yaml_file in self.yaml_files:
            if os.path.exists(yaml_file):
                print(f"📄 Loading {yaml_file}...")
                chunks = self._load_yaml_chunks(yaml_file)
                all_chunks.extend(chunks)
            else:
                print(f"⚠️ {yaml_file} not found, skipping...")
        
        print(f"📚 Loaded {len(all_chunks)} total chunks")
        return all_chunks
    
    def get_relevant_context(self, query: str, subject: str = None, max_chunks: int = 3) -> str:
        """
        Get relevant context for a query.
        
        Args:
            query: The user's query
            subject: Optional subject filter
            max_chunks: Maximum number of chunks to return
        
        Returns:
            str: Relevant context as text
        """
        if not self.chunks:
            return ""
        
        # Simple keyword-based relevance scoring
        relevant_chunks = []
        query_lower = query.lower()
        
        for chunk in self.chunks:
            score = 0
            chunk_lower = chunk.lower()
            
            # Score based on keyword overlap
            for word in query_lower.split():
                if word in chunk_lower:
                    score += 1
            
            # Bonus for subject match
            if subject and subject.lower() in chunk_lower:
                score += 2
            
            if score > 0:
                relevant_chunks.append((chunk, score))
        
        # Sort by relevance score and take top chunks
        relevant_chunks.sort(key=lambda x: x[1], reverse=True)
        top_chunks = relevant_chunks[:max_chunks]
        
        # Return concatenated context
        context = " ".join([chunk for chunk, score in top_chunks])
        return context
    
    def get_chunks_by_subject(self, subject: str) -> List[str]:
        """Get chunks filtered by subject."""
        if not subject:
            return self.chunks
        
        filtered_chunks = []
        subject_lower = subject.lower()
        
        for chunk in self.chunks:
            if subject_lower in chunk.lower():
                filtered_chunks.append(chunk)
        
        return filtered_chunks
    
    def get_stats(self) -> Dict:
        """Get statistics about the RAG engine."""
        return {
            "total_chunks": len(self.chunks),
            "yaml_files": self.yaml_files,
            "loaded_files": [f for f in self.yaml_files if os.path.exists(f)]
        }
    
    def test_rag(self):
        """Test the RAG engine with sample queries."""
        test_queries = [
            "What are your values?",
            "Tell me about your projects",
            "How do you solve problems?"
        ]
        
        print("🧪 Testing RAG engine...")
        for query in test_queries:
            print(f"\n🔍 Query: {query}")
            context = self.get_relevant_context(query)
            print(f"📚 Context: {context[:100]}...")
        
        print("\n✅ RAG engine tested!") 