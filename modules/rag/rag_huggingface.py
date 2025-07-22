"""
rag_huggingface.py - Hugging Face Datasets Backend Implementation

Hugging Face Datasets backend for Spaces deployment with cloud storage.
"""

import os
import yaml
import numpy as np
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from .rag_adapter import RAGBackend

try:
    from datasets import Dataset, load_dataset
    from huggingface_hub import HfApi, login
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("⚠️ Hugging Face libraries not available. Install with: pip install datasets huggingface_hub")

class HuggingFaceBackend(RAGBackend):
    """Hugging Face Datasets backend implementation for Spaces."""
    
    def __init__(self, 
                 dataset_name: str = "stephen-saunders/knowledge-base",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 use_auth_token: bool = True):
        """
        Initialize the Hugging Face backend.
        
        Args:
            dataset_name: HF dataset name (username/dataset-name)
            embedding_model: Sentence transformer model to use
            use_auth_token: Whether to use HF auth token
        """
        self.dataset_name = dataset_name
        self.embedding_model_name = embedding_model
        self.use_auth_token = use_auth_token
        self.embedding_model = None
        self.dataset = None
        self.embeddings = None
        self.initialized = False
        
        # Try to login to HF
        if use_auth_token:
            try:
                token = os.getenv("HF_TOKEN")
                if token:
                    login(token)
                    print("✅ Logged into Hugging Face")
                else:
                    print("⚠️ HF_TOKEN not found, using anonymous access")
            except Exception as e:
                print(f"⚠️ HF login failed: {e}")
    
    def initialize(self) -> bool:
        """Initialize the Hugging Face backend."""
        if not HF_AVAILABLE:
            print("❌ Hugging Face libraries not available")
            return False
        
        try:
            # Initialize embedding model
            print(f"🔄 Loading embedding model: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            
            # Try to load existing dataset
            try:
                self.dataset = load_dataset(self.dataset_name, split="train")
                print(f"✅ Loaded existing dataset: {self.dataset_name}")
                self._load_embeddings()
            except:
                # Create new dataset
                print(f"📝 Creating new dataset: {self.dataset_name}")
                self.dataset = Dataset.from_dict({
                    "id": [],
                    "text": [],
                    "metadata": [],
                    "embedding": []
                })
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Hugging Face backend: {e}")
            return False
    
    def _load_embeddings(self):
        """Load embeddings from the dataset."""
        if self.dataset and len(self.dataset) > 0:
            self.embeddings = np.array(self.dataset["embedding"])
            print(f"✅ Loaded {len(self.embeddings)} embeddings")
        else:
            self.embeddings = np.array([])
    
    def chunk_yaml_data(self, yaml_file: str) -> List[Dict]:
        """Chunk YAML data into searchable documents with enhanced metadata."""
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            chunks = []
            chunk_id = 0
            
            for section, content in data.items():
                if isinstance(content, dict):
                    for key, value in content.items():
                        if isinstance(value, list):
                            chunk_text = f"{section} - {key}: {', '.join(value)}"
                        else:
                            chunk_text = f"{section} - {key}: {value}"
                        
                        chunks.append({
                            "id": f"chunk_{chunk_id}",
                            "text": chunk_text,
                            "metadata": {
                                "section": section,
                                "key": key,
                                "source": yaml_file,
                                "type": "yaml_chunk",
                                "subject": self._infer_subject(section, key, chunk_text),
                                "content_type": "list" if isinstance(value, list) else "text"
                            }
                        })
                        chunk_id += 1
                else:
                    chunk_text = f"{section}: {content}"
                    chunks.append({
                        "id": f"chunk_{chunk_id}",
                        "text": chunk_text,
                        "metadata": {
                            "section": section,
                            "source": yaml_file,
                            "type": "yaml_chunk",
                            "subject": self._infer_subject(section, "", chunk_text),
                            "content_type": "text"
                        }
                    })
                    chunk_id += 1
            
            return chunks
        
        except FileNotFoundError:
            print(f"⚠️ {yaml_file} not found!")
            return []
        except Exception as e:
            print(f"❌ Error chunking {yaml_file}: {str(e)}")
            return []
    
    def _infer_subject(self, section: str, key: str, text: str) -> str:
        """Infer the subject category from section, key, and text."""
        text_lower = text.lower()
        section_lower = section.lower()
        key_lower = key.lower()
        
        # Subject inference logic (same as ChromaDB)
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
    
    def add_documents(self, documents: List[Dict]) -> bool:
        """Add documents to the Hugging Face dataset."""
        if not self.initialized:
            print("❌ Hugging Face backend not initialized")
            return False
        
        if not documents:
            print("⚠️ No documents to add")
            return False
        
        try:
            # Generate embeddings for new documents
            texts = [doc["text"] for doc in documents]
            embeddings = self.embedding_model.encode(texts)
            
            # Prepare data for dataset
            new_data = {
                "id": [doc["id"] for doc in documents],
                "text": texts,
                "metadata": [doc["metadata"] for doc in documents],
                "embedding": embeddings.tolist()
            }
            
            # Add to dataset
            new_dataset = Dataset.from_dict(new_data)
            if self.dataset and len(self.dataset) > 0:
                self.dataset = Dataset.concatenate_datasets([self.dataset, new_dataset])
            else:
                self.dataset = new_dataset
            
            # Update embeddings
            self._load_embeddings()
            
            print(f"✅ Added {len(documents)} documents to Hugging Face dataset")
            return True
            
        except Exception as e:
            print(f"❌ Error adding documents to Hugging Face: {e}")
            return False
    
    def query_similar(self, 
                     query_text: str, 
                     n_results: int = 3,
                     filter_metadata: Dict = None,
                     subject_filter: str = None) -> List[Dict]:
        """Query the dataset for similar documents."""
        if not self.initialized or self.embeddings is None or len(self.embeddings) == 0:
            print("❌ Hugging Face backend not initialized or no data")
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
                    metadata = self.dataset[idx]["metadata"]
                    
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
                    "text": self.dataset[idx]["text"],
                    "metadata": self.dataset[idx]["metadata"],
                    "similarity": float(similarities[idx]),
                    "rank": i + 1
                })
            
            return results
        
        except Exception as e:
            print(f"❌ Error querying Hugging Face dataset: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get Hugging Face dataset statistics."""
        if not self.initialized:
            return {"error": "Hugging Face backend not initialized"}
        
        try:
            return {
                "total_documents": len(self.dataset) if self.dataset else 0,
                "dataset_name": self.dataset_name,
                "embedding_model": self.embedding_model_name,
                "embeddings_shape": self.embeddings.shape if self.embeddings is not None else None
            }
        except Exception as e:
            return {"error": str(e)}
    
    def clear(self) -> bool:
        """Clear all data from the Hugging Face dataset."""
        if not self.initialized:
            return False
        
        try:
            self.dataset = Dataset.from_dict({
                "id": [],
                "text": [],
                "metadata": [],
                "embedding": []
            })
            self.embeddings = np.array([])
            print(f"✅ Cleared Hugging Face dataset: {self.dataset_name}")
            return True
        except Exception as e:
            print(f"❌ Error clearing Hugging Face dataset: {e}")
            return False
    
    def save_to_hub(self) -> bool:
        """Save the dataset to Hugging Face Hub."""
        if not self.initialized or not self.dataset:
            print("❌ No dataset to save")
            return False
        
        try:
            self.dataset.push_to_hub(self.dataset_name)
            print(f"✅ Saved dataset to Hugging Face Hub: {self.dataset_name}")
            return True
        except Exception as e:
            print(f"❌ Error saving to Hugging Face Hub: {e}")
            return False
    
    def initialize_from_yaml(self, yaml_files: List[str] = None):
        """Initialize the Hugging Face system with YAML data."""
        if yaml_files is None:
            yaml_files = ["projects.yaml"]
        
        print("🔄 Initializing Hugging Face backend with YAML data...")
        
        # Process each YAML file
        for yaml_file in yaml_files:
            if os.path.exists(yaml_file):
                print(f"📄 Processing {yaml_file}...")
                chunks = self.chunk_yaml_data(yaml_file)
                if chunks:
                    self.add_documents(chunks)
            else:
                print(f"⚠️ {yaml_file} not found, skipping...")
        
        # Save to Hub
        self.save_to_hub()
        
        # Print stats
        stats = self.get_stats()
        print(f"📊 Hugging Face stats: {stats}")
    
    def test_huggingface(self):
        """Test the Hugging Face backend."""
        print("🧪 Testing Hugging Face backend...")
        
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
        
        print("\n✅ Hugging Face backend tested!") 