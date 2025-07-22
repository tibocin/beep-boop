"""
rag_simple.py - Simple Embedding-based RAG

A lightweight RAG system using sentence transformers and numpy for embeddings.
No complex dependencies, works reliably on all platforms.
"""

import os
import yaml
import numpy as np
import pickle
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from .rag_adapter import RAGBackend

class SimpleEmbeddingRAG(RAGBackend):
    """Simple embedding-based RAG using sentence transformers and numpy."""
    
    def __init__(self, 
                 embedding_model: str = "all-MiniLM-L6-v2",
                 embeddings_file: str = "./embeddings.pkl",
                 yaml_file: str = "projects.yaml"):
        """
        Initialize the simple embedding RAG.
        
        Args:
            embedding_model: Sentence transformer model to use
            embeddings_file: File to store embeddings
            yaml_file: YAML file with knowledge base
        """
        self.embedding_model_name = embedding_model
        self.embeddings_file = embeddings_file
        self.yaml_file = yaml_file
        self.embedding_model = None
        self.documents = []
        self.embeddings = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize the embedding RAG system."""
        try:
            # Load embedding model
            print(f"🔄 Loading embedding model: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            
            # Try to load existing embeddings
            if os.path.exists(self.embeddings_file):
                print(f"📄 Loading existing embeddings from {self.embeddings_file}")
                with open(self.embeddings_file, 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data['documents']
                    self.embeddings = data['embeddings']
                print(f"✅ Loaded {len(self.documents)} documents with embeddings")
            else:
                # Create embeddings from YAML
                print(f"📄 Creating embeddings from {self.yaml_file}")
                self._create_embeddings_from_yaml()
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize SimpleEmbeddingRAG: {e}")
            return False
    
    def _create_embeddings_from_yaml(self):
        """Create embeddings from YAML data."""
        if not os.path.exists(self.yaml_file):
            print(f"⚠️ {self.yaml_file} not found!")
            return
        
        # Load and chunk YAML data
        with open(self.yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        self.documents = []
        chunk_id = 0
        
        for section, content in data.items():
            if isinstance(content, dict):
                for key, value in content.items():
                    if isinstance(value, list):
                        chunk_text = f"{section} - {key}: {', '.join(value)}"
                    else:
                        chunk_text = f"{section} - {key}: {value}"
                    
                    self.documents.append({
                        "id": f"chunk_{chunk_id}",
                        "text": chunk_text,
                        "metadata": {
                            "section": section,
                            "key": key,
                            "source": self.yaml_file,
                            "type": "yaml_chunk",
                            "subject": self._infer_subject(section, key, chunk_text),
                            "content_type": "list" if isinstance(value, list) else "text"
                        }
                    })
                    chunk_id += 1
            else:
                chunk_text = f"{section}: {content}"
                self.documents.append({
                    "id": f"chunk_{chunk_id}",
                    "text": chunk_text,
                    "metadata": {
                        "section": section,
                        "source": self.yaml_file,
                        "type": "yaml_chunk",
                        "subject": self._infer_subject(section, "", chunk_text),
                        "content_type": "text"
                    }
                })
                chunk_id += 1
        
        # Generate embeddings
        print(f"🔄 Generating embeddings for {len(self.documents)} documents...")
        texts = [doc["text"] for doc in self.documents]
        self.embeddings = self.embedding_model.encode(texts)
        
        # Save embeddings
        self._save_embeddings()
        print(f"✅ Created and saved embeddings for {len(self.documents)} documents")
    
    def _infer_subject(self, section: str, key: str, text: str) -> str:
        """Infer the subject category from section, key, and text."""
        text_lower = text.lower()
        section_lower = section.lower()
        key_lower = key.lower()
        
        # Subject inference logic
        if any(word in text_lower for word in ["project", "work", "build", "create"]):
            return "projects"
        elif any(word in text_lower for word in ["personality", "character", "traits"]):
            return "personality"
        elif any(word in text_lower for word in ["value", "believe", "principle"]):
            return "values"
        elif any(word in text_lower for word in ["technical", "skill", "problem", "solve"]):
            return "technical_skills"
        elif any(word in text_lower for word in ["interest", "hobby", "passion"]):
            return "interests"
        elif any(word in text_lower for word in ["education", "learn", "study"]):
            return "education"
        elif any(word in text_lower for word in ["work", "experience", "career"]):
            return "work_experience"
        elif any(word in text_lower for word in ["favorite", "like", "prefer"]):
            return "favorites"
        elif any(word in text_lower for word in ["lifestyle", "habit", "routine"]):
            return "lifestyle"
        elif any(word in text_lower for word in ["family", "relationship"]):
            return "family"
        elif any(word in text_lower for word in ["spiritual", "spirituality"]):
            return "spirituality"
        elif any(word in text_lower for word in ["philosophy", "philosophical"]):
            return "philosophy"
        elif any(word in text_lower for word in ["dream", "aspiration", "goal"]):
            return "dreams"
        elif any(word in text_lower for word in ["wisdom", "insight", "knowledge"]):
            return "wisdom"
        else:
            return "general"
    
    def _save_embeddings(self):
        """Save embeddings to file."""
        data = {
            'documents': self.documents,
            'embeddings': self.embeddings,
            'model_name': self.embedding_model_name
        }
        with open(self.embeddings_file, 'wb') as f:
            pickle.dump(data, f)
        print(f"💾 Saved embeddings to {self.embeddings_file}")
    
    def add_documents(self, documents: List[Dict]) -> bool:
        """Add documents to the knowledge base."""
        if not self.initialized:
            print("❌ SimpleEmbeddingRAG not initialized")
            return False
        
        if not documents:
            print("⚠️ No documents to add")
            return False
        
        try:
            # Generate embeddings for new documents
            texts = [doc["text"] for doc in documents]
            new_embeddings = self.embedding_model.encode(texts)
            
            # Add to existing data
            self.documents.extend(documents)
            if self.embeddings is None:
                self.embeddings = new_embeddings
            else:
                self.embeddings = np.vstack([self.embeddings, new_embeddings])
            
            # Save updated embeddings
            self._save_embeddings()
            
            print(f"✅ Added {len(documents)} documents to SimpleEmbeddingRAG")
            return True
            
        except Exception as e:
            print(f"❌ Error adding documents: {e}")
            return False
    
    def query_similar(self, 
                     query_text: str, 
                     n_results: int = 3,
                     filter_metadata: Dict = None,
                     subject_filter: str = None) -> List[Dict]:
        """Query for similar documents using cosine similarity."""
        if not self.initialized or self.embeddings is None or len(self.embeddings) == 0:
            print("❌ SimpleEmbeddingRAG not initialized or no data")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query_text])
            
            # Calculate similarities
            similarities = cosine_similarity(query_embedding, self.embeddings)[0]
            
            # Get top results
            top_indices = np.argsort(similarities)[::-1][:n_results]
            
            # Apply filters if specified
            if subject_filter or filter_metadata:
                filtered_indices = []
                for idx in top_indices:
                    metadata = self.documents[idx]["metadata"]
                    
                    # Check subject filter
                    if subject_filter and metadata.get("subject") != subject_filter:
                        continue
                    
                    # Check metadata filters
                    if filter_metadata:
                        skip = False
                        for key, value in filter_metadata.items():
                            if metadata.get(key) != value:
                                skip = True
                                break
                        if skip:
                            continue
                    
                    filtered_indices.append(idx)
                
                # If filtering removed all results, return top results without filtering
                if not filtered_indices:
                    print(f"⚠️ No results found with filters, returning top {n_results} results")
                    filtered_indices = top_indices[:n_results]
                else:
                    filtered_indices = filtered_indices[:n_results]
            else:
                filtered_indices = top_indices
            
            # Format results
            results = []
            for i, idx in enumerate(filtered_indices):
                results.append({
                    "text": self.documents[idx]["text"],
                    "metadata": self.documents[idx]["metadata"],
                    "similarity": float(similarities[idx]),
                    "rank": i + 1
                })
            
            return results
        
        except Exception as e:
            print(f"❌ Error querying SimpleEmbeddingRAG: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get SimpleEmbeddingRAG statistics."""
        if not self.initialized:
            return {"error": "SimpleEmbeddingRAG not initialized"}
        
        try:
            return {
                "total_documents": len(self.documents) if self.documents else 0,
                "embeddings_shape": self.embeddings.shape if self.embeddings is not None else None,
                "embedding_model": self.embedding_model_name,
                "embeddings_file": self.embeddings_file
            }
        except Exception as e:
            return {"error": str(e)}
    
    def clear(self) -> bool:
        """Clear all data from the SimpleEmbeddingRAG."""
        if not self.initialized:
            return False
        
        try:
            self.documents = []
            self.embeddings = None
            
            # Remove embeddings file
            if os.path.exists(self.embeddings_file):
                os.remove(self.embeddings_file)
            
            print(f"✅ Cleared SimpleEmbeddingRAG data")
            return True
        except Exception as e:
            print(f"❌ Error clearing SimpleEmbeddingRAG: {e}")
            return False
    
    def test_embeddings(self):
        """Test the embedding system."""
        print("🧪 Testing SimpleEmbeddingRAG...")
        
        # Test queries with different subjects
        test_queries = [
            ("What are your values?", "values"),
            ("Tell me about your projects", "projects"),
            ("How do you solve problems?", "technical_skills"),
            ("What's your personality like?", "personality")
        ]
        
        for query, expected_subject in test_queries:
            print(f"\n🔍 Query: {query}")
            
            # Test subject-specific search
            results = self.query_similar(query, n_results=2, subject_filter=expected_subject)
            print(f"  📚 Subject-specific results ({expected_subject}):")
            for result in results:
                print(f"    - {result['text'][:80]}... (similarity: {result['similarity']:.3f})")
            
            # Test general search
            general_results = self.query_similar(query, n_results=2)
            print(f"  📚 General results:")
            for result in general_results:
                print(f"    - {result['text'][:80]}... (similarity: {result['similarity']:.3f})")
        
        print("\n✅ SimpleEmbeddingRAG tested!") 