"""
rag_pinecone.py - Pinecone Backend Implementation

Pinecone backend for production deployment with cloud vector database.
"""

import os
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from .rag_adapter import RAGBackend

try:
    import pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    print("⚠️ Pinecone not available. Install with: pip install pinecone-client")

class PineconeBackend(RAGBackend):
    """Pinecone backend implementation for production deployment."""
    
    def __init__(self, 
                 index_name: str = "agentic-companion",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 dimension: int = 384):
        """
        Initialize the Pinecone backend.
        
        Args:
            index_name: Pinecone index name
            embedding_model: Sentence transformer model to use
            dimension: Embedding dimension
        """
        self.index_name = index_name
        self.embedding_model_name = embedding_model
        self.dimension = dimension
        self.embedding_model = None
        self.index = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize the Pinecone backend."""
        if not PINECONE_AVAILABLE:
            print("❌ Pinecone not available")
            return False
        
        try:
            # Initialize Pinecone
            api_key = os.getenv("PINECONE_API_KEY")
            if not api_key:
                print("❌ PINECONE_API_KEY not found")
                return False
            
            pinecone.init(api_key=api_key)
            
            # Initialize embedding model
            print(f"🔄 Loading embedding model: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            
            # Get or create index
            if self.index_name in pinecone.list_indexes():
                self.index = pinecone.Index(self.index_name)
                print(f"✅ Connected to existing index: {self.index_name}")
            else:
                # Create new index
                pinecone.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine"
                )
                self.index = pinecone.Index(self.index_name)
                print(f"✅ Created new index: {self.index_name}")
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Pinecone: {e}")
            return False
    
    def add_documents(self, documents: List[Dict]) -> bool:
        """Add documents to the Pinecone index."""
        if not self.initialized:
            print("❌ Pinecone not initialized")
            return False
        
        if not documents:
            print("⚠️ No documents to add")
            return False
        
        try:
            # Generate embeddings
            texts = [doc["text"] for doc in documents]
            embeddings = self.embedding_model.encode(texts)
            
            # Prepare vectors for Pinecone
            vectors = []
            for i, doc in enumerate(documents):
                vectors.append({
                    "id": doc["id"],
                    "values": embeddings[i].tolist(),
                    "metadata": doc["metadata"]
                })
            
            # Upsert to Pinecone
            self.index.upsert(vectors=vectors)
            
            print(f"✅ Added {len(documents)} documents to Pinecone")
            return True
            
        except Exception as e:
            print(f"❌ Error adding documents to Pinecone: {e}")
            return False
    
    def query_similar(self, 
                     query_text: str, 
                     n_results: int = 3,
                     filter_metadata: Dict = None,
                     subject_filter: str = None) -> List[Dict]:
        """Query the Pinecone index for similar documents."""
        if not self.initialized:
            print("❌ Pinecone not initialized")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query_text])
            
            # Build filter
            filter_dict = None
            if subject_filter or filter_metadata:
                filter_dict = {}
                if subject_filter:
                    filter_dict["subject"] = subject_filter
                if filter_metadata:
                    filter_dict.update(filter_metadata)
            
            # Query Pinecone
            results = self.index.query(
                vector=query_embedding[0].tolist(),
                top_k=n_results,
                include_metadata=True,
                filter=filter_dict
            )
            
            # Format results
            formatted_results = []
            for i, match in enumerate(results.matches):
                formatted_results.append({
                    "text": match.metadata.get("text", ""),
                    "metadata": match.metadata,
                    "similarity": match.score,
                    "rank": i + 1
                })
            
            return formatted_results
        
        except Exception as e:
            print(f"❌ Error querying Pinecone: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get Pinecone index statistics."""
        if not self.initialized:
            return {"error": "Pinecone not initialized"}
        
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "index_name": self.index_name,
                "embedding_model": self.embedding_model_name,
                "dimension": self.dimension
            }
        except Exception as e:
            return {"error": str(e)}
    
    def clear(self) -> bool:
        """Clear all data from the Pinecone index."""
        if not self.initialized:
            return False
        
        try:
            # Delete and recreate index
            pinecone.delete_index(self.index_name)
            pinecone.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine"
            )
            self.index = pinecone.Index(self.index_name)
            print(f"✅ Cleared Pinecone index: {self.index_name}")
            return True
        except Exception as e:
            print(f"❌ Error clearing Pinecone index: {e}")
            return False
    
    def test_pinecone(self):
        """Test the Pinecone backend."""
        print("🧪 Testing Pinecone backend...")
        
        # Test queries
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
        
        print("\n✅ Pinecone backend tested!") 