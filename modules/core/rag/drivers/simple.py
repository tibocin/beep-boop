"""
modules.core.rag.drivers.simple - Simple embedding-based RAG driver

A lightweight RAG driver using sentence transformers and numpy for embeddings.
Designed for reliability with minimal dependencies.
"""

import os
import yaml
import numpy as np
import pickle
import glob
from typing import List, Dict, Any, Optional

class SimpleDriver:
    """
    Simple embedding-based RAG driver
    
    Uses sentence transformers for embeddings and numpy for similarity search.
    Supports YAML knowledge base loading with automatic text extraction.
    """
    
    def __init__(self, 
                 embedding_model: str = "all-MiniLM-L6-v2",
                 embeddings_file: str = "./simple_embeddings.pkl",
                 data_dir: str = "./data"):
        """
        Initialize the simple RAG driver
        
        Args:
            embedding_model: Sentence transformer model name
            embeddings_file: File to store/load embeddings
            data_dir: Directory containing YAML knowledge files
        """
        self.embedding_model_name = embedding_model
        self.embeddings_file = embeddings_file
        self.data_dir = data_dir
        self.embedding_model = None
        self.documents = []
        self.embeddings = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize the embedding system and load knowledge base"""
        try:
            # Load embedding model
            print(f"🔄 Loading embedding model: {self.embedding_model_name}")
            try:
                from sentence_transformers import SentenceTransformer
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
            except ImportError:
                print("⚠️ sentence-transformers not available, using basic text matching")
                self.embedding_model = None
                return self._initialize_basic_mode()
            
            # Try to load existing embeddings
            if os.path.exists(self.embeddings_file):
                print(f"📄 Loading existing embeddings from {self.embeddings_file}")
                with open(self.embeddings_file, 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data['documents']
                    self.embeddings = data['embeddings']
            else:
                # Create new embeddings from data
                self._build_knowledge_base()
            
            self.initialized = True
            print(f"✅ Simple RAG initialized with {len(self.documents)} documents")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Simple RAG: {e}")
            return False
    
    def _build_knowledge_base(self):
        """Build knowledge base from YAML files in data directory"""
        print(f"🔨 Building knowledge base from {self.data_dir}")
        
        # Find all YAML files recursively
        yaml_files = []
        if os.path.exists(self.data_dir):
            yaml_files = glob.glob(os.path.join(self.data_dir, "**/*.yaml"), recursive=True)
            yaml_files.extend(glob.glob(os.path.join(self.data_dir, "**/*.yml"), recursive=True))
        
        # Also check for YAML files in root directory
        yaml_files.extend(glob.glob("*.yaml"))
        yaml_files.extend(glob.glob("*.yml"))
        
        self.documents = []
        
        for yaml_file in yaml_files:
            try:
                chunks = self._extract_text_from_yaml(yaml_file)
                for chunk in chunks:
                    self.documents.append({
                        'content': chunk,
                        'source': yaml_file,
                        'metadata': {'file': yaml_file}
                    })
            except Exception as e:
                print(f"⚠️ Error processing {yaml_file}: {e}")
        
        if not self.documents:
            print("⚠️ No documents found, creating minimal knowledge base")
            self.documents = [{
                'content': "I am an AI assistant ready to help with conversations, resume generation, and explanations.",
                'source': 'default',
                'metadata': {'type': 'default'}
            }]
        
        # Create embeddings
        print(f"🔄 Creating embeddings for {len(self.documents)} documents")
        texts = [doc['content'] for doc in self.documents]
        self.embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        
        # Save embeddings
        os.makedirs(os.path.dirname(self.embeddings_file), exist_ok=True)
        with open(self.embeddings_file, 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'embeddings': self.embeddings
            }, f)
        
        print(f"💾 Saved embeddings to {self.embeddings_file}")
    
    def _extract_text_from_yaml(self, yaml_file: str) -> List[str]:
        """Extract meaningful text chunks from YAML file"""
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            chunks = []
            file_basename = os.path.basename(yaml_file)
            
            def extract_from_object(obj, prefix=""):
                """Recursively extract text from nested objects"""
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_prefix = f"{prefix} {key}" if prefix else key
                        if isinstance(value, (dict, list)):
                            extract_from_object(value, new_prefix)
                        else:
                            text = f"{new_prefix}: {str(value)}"
                            if len(text.strip()) > 10:  # Only meaningful content
                                chunks.append(text)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        if isinstance(item, (dict, list)):
                            extract_from_object(item, prefix)
                        else:
                            text = f"{prefix}: {str(item)}" if prefix else str(item)
                            if len(text.strip()) > 10:
                                chunks.append(text)
                else:
                    text = f"{prefix}: {str(obj)}" if prefix else str(obj)
                    if len(text.strip()) > 10:
                        chunks.append(text)
            
            # Extract content
            extract_from_object(data)
            
            # Add context about the file source
            if chunks:
                source_context = f"From {file_basename}: "
                chunks = [source_context + chunk for chunk in chunks]
            
            return chunks
            
        except Exception as e:
            print(f"⚠️ Error extracting from {yaml_file}: {e}")
            return []
    
    def query_similar(self, query_text: str, n_results: int = 5, 
                     filter_metadata: Dict = None, subject_filter: str = None) -> List[Dict[str, Any]]:
        """Query for similar documents using embedding similarity or basic text matching"""
        if not self.initialized:
            return []
        
        # If embeddings are available, use them
        if self.embeddings is not None and self.embedding_model is not None:
            try:
                # Create query embedding
                query_embedding = self.embedding_model.encode([query_text], convert_to_numpy=True)
                
                # Calculate similarities
                from sklearn.metrics.pairwise import cosine_similarity
                similarities = cosine_similarity(query_embedding, self.embeddings)[0]
                
                # Get top results
                top_indices = np.argsort(similarities)[::-1][:n_results]
                
                results = []
                for idx in top_indices:
                    if similarities[idx] > 0.1:  # Minimum similarity threshold
                        doc = self.documents[idx].copy()
                        doc['score'] = float(similarities[idx])
                        results.append(doc)
                
                return results
                
            except Exception as e:
                print(f"⚠️ Error with embedding query: {e}, falling back to text matching")
        
        # Fallback to basic text matching
        return self._basic_text_search(query_text, n_results)
    
    def _basic_text_search(self, query_text: str, n_results: int) -> List[Dict[str, Any]]:
        """Basic text search using keyword matching"""
        query_words = query_text.lower().split()
        results = []
        
        for doc in self.documents:
            content = doc['content'].lower()
            score = 0.0
            
            # Simple keyword matching
            for word in query_words:
                if len(word) > 2:  # Only consider words longer than 2 chars
                    if word in content:
                        score += 1.0
            
            # Normalize score
            if len(query_words) > 0:
                score = score / len(query_words)
            
            if score > 0.1:  # Minimum relevance threshold
                doc_copy = doc.copy()
                doc_copy['score'] = score
                results.append(doc_copy)
        
        # Sort by score and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:n_results]
    
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Simple search interface (alias for query_similar)"""
        return self.query_similar(query, num_results)
    
    def initialize_from_yaml(self, yaml_files: List[str] = None) -> bool:
        """Initialize with specific YAML files"""
        if yaml_files:
            # Override data directory with specific files
            temp_docs = []
            for yaml_file in yaml_files:
                if os.path.exists(yaml_file):
                    chunks = self._extract_text_from_yaml(yaml_file)
                    for chunk in chunks:
                        temp_docs.append({
                            'content': chunk,
                            'source': yaml_file,
                            'metadata': {'file': yaml_file}
                        })
            
            if temp_docs:
                self.documents = temp_docs
                texts = [doc['content'] for doc in self.documents]
                self.embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
                return True
        
        return self.initialize()
    
    def _initialize_basic_mode(self) -> bool:
        """Initialize in basic text matching mode without embeddings"""
        print("🔧 Initializing basic text matching mode")
        
        # Build knowledge base from YAML files
        yaml_files = []
        if os.path.exists(self.data_dir):
            yaml_files = glob.glob(os.path.join(self.data_dir, "**/*.yaml"), recursive=True)
            yaml_files.extend(glob.glob(os.path.join(self.data_dir, "**/*.yml"), recursive=True))
        
        # Also check for YAML files in root directory
        yaml_files.extend(glob.glob("*.yaml"))
        yaml_files.extend(glob.glob("*.yml"))
        
        self.documents = []
        
        for yaml_file in yaml_files:
            try:
                chunks = self._extract_text_from_yaml(yaml_file)
                for chunk in chunks:
                    self.documents.append({
                        'content': chunk,
                        'source': yaml_file,
                        'metadata': {'file': yaml_file}
                    })
            except Exception as e:
                print(f"⚠️ Error processing {yaml_file}: {e}")
        
        if not self.documents:
            print("⚠️ No documents found, creating minimal knowledge base")
            self.documents = [{
                'content': "I am an AI assistant ready to help with conversations, resume generation, and explanations.",
                'source': 'default',
                'metadata': {'type': 'default'}
            }]
        
        self.initialized = True
        print(f"✅ Basic RAG initialized with {len(self.documents)} documents")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get driver statistics"""
        mode = "embedding" if self.embedding_model is not None else "basic_text"
        return {
            'type': 'simple',
            'mode': mode,
            'documents': len(self.documents) if self.documents else 0,
            'embedding_model': self.embedding_model_name if self.embedding_model else "none",
            'initialized': self.initialized
        }