"""
rag_chroma.py - ChromaDB Backend Implementation

ChromaDB backend for local development with full vector search capabilities.
"""

import chromadb
from chromadb.config import Settings
import yaml
import os
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from .rag_adapter import RAGBackend

class ChromaDBBackend(RAGBackend):
    """ChromaDB backend implementation for local development."""
    
    def __init__(self, 
                 collection_name: str = "agentic_companion",
                 persist_directory: str = "./chroma_db",
                 embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize the ChromaDB backend.
        
        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist ChromaDB data
            embedding_model: Sentence transformer model to use
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_model_name = embedding_model
        self.client = None
        self.collection = None
        self.embedding_model = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize the ChromaDB backend."""
        try:
            # Initialize ChromaDB client with new API
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Initialize embedding model
            print(f"🔄 Loading embedding model: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(self.collection_name)
                print(f"✅ Loaded existing collection: {self.collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Agentic companion knowledge base"}
                )
                print(f"✅ Created new collection: {self.collection_name}")
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize ChromaDB: {e}")
            return False
    
    def chunk_yaml_data(self, yaml_file: str) -> List[Dict]:
        """Chunk YAML data into searchable documents with enhanced metadata."""
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            chunks = []
            chunk_id = 0
            
            def process_value(value, section, key):
                """Process a value and convert it to text."""
                if isinstance(value, str):
                    return value
                elif isinstance(value, list):
                    # Handle list of strings
                    if all(isinstance(item, str) for item in value):
                        return ', '.join(value)
                    # Handle list of dictionaries
                    elif all(isinstance(item, dict) for item in value):
                        texts = []
                        for item in value:
                            if isinstance(item, dict):
                                item_texts = []
                                for k, v in item.items():
                                    if isinstance(v, str):
                                        item_texts.append(f"{k}: {v}")
                                    elif isinstance(v, list) and all(isinstance(x, str) for x in v):
                                        item_texts.append(f"{k}: {', '.join(v)}")
                                    elif isinstance(v, (int, float)):
                                        item_texts.append(f"{k}: {v}")
                                    elif isinstance(v, dict):
                                        # Handle nested dictionaries
                                        nested_texts = []
                                        for nk, nv in v.items():
                                            if isinstance(nv, str):
                                                nested_texts.append(f"{nk}: {nv}")
                                            elif isinstance(nv, (int, float)):
                                                nested_texts.append(f"{nk}: {nv}")
                                        if nested_texts:
                                            item_texts.append(f"{k}: {'; '.join(nested_texts)}")
                                if item_texts:
                                    texts.append('; '.join(item_texts))
                        return ' | '.join(texts) if texts else str(value)
                    # Mixed list - convert all items to strings
                    else:
                        return ', '.join([str(item) for item in value])
                elif isinstance(value, dict):
                    texts = []
                    for k, v in value.items():
                        if isinstance(v, str):
                            texts.append(f"{k}: {v}")
                        elif isinstance(v, list) and all(isinstance(x, str) for x in v):
                            texts.append(f"{k}: {', '.join(v)}")
                        elif isinstance(v, (int, float)):
                            texts.append(f"{k}: {v}")
                        elif isinstance(v, dict):
                            # Handle nested dictionaries
                            nested_texts = []
                            for nk, nv in v.items():
                                if isinstance(nv, str):
                                    nested_texts.append(f"{nk}: {nv}")
                                elif isinstance(nv, (int, float)):
                                    nested_texts.append(f"{nk}: {nv}")
                            if nested_texts:
                                texts.append(f"{k}: {'; '.join(nested_texts)}")
                    return '; '.join(texts) if texts else str(value)
                else:
                    return str(value)
            
            for section, content in data.items():
                if section == 'metadata':
                    continue  # Skip metadata section
                
                if isinstance(content, dict):
                    for key, value in content.items():
                        chunk_text = process_value(value, section, key)
                        if chunk_text and chunk_text.strip():
                            chunks.append({
                                "id": f"chunk_{chunk_id}",
                                "text": f"{section} - {key}: {chunk_text}",
                                "metadata": {
                                    "section": section,
                                    "key": key,
                                    "source": yaml_file,
                                    "type": "yaml_chunk",
                                    "subject": self._infer_subject(section, key, chunk_text),
                                    "content_type": "complex"
                                }
                            })
                            chunk_id += 1
                else:
                    chunk_text = process_value(content, section, "")
                    if chunk_text and chunk_text.strip():
                        chunks.append({
                            "id": f"chunk_{chunk_id}",
                            "text": f"{section}: {chunk_text}",
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
    
    def add_documents(self, documents: List[Dict]) -> bool:
        """Add documents to the ChromaDB collection."""
        if not self.initialized:
            print("❌ ChromaDB not initialized")
            return False
        
        if not documents:
            print("⚠️ No documents to add")
            return False
        
        try:
            # Extract data for ChromaDB
            ids = [doc["id"] for doc in documents]
            texts = [doc["text"] for doc in documents]
            metadatas = [doc["metadata"] for doc in documents]
            
            # Add to collection
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            print(f"✅ Added {len(documents)} documents to ChromaDB")
            return True
            
        except Exception as e:
            print(f"❌ Error adding documents to ChromaDB: {e}")
            return False
    
    def query_similar(self, 
                     query_text: str, 
                     n_results: int = 3,
                     filter_metadata: Dict = None,
                     subject_filter: str = None) -> List[Dict]:
        """Query the collection for similar documents with enhanced filtering."""
        if not self.initialized:
            print("❌ ChromaDB not initialized")
            return []
        
        try:
            # Build where clause for filtering
            where_clause = {}
            if filter_metadata:
                where_clause.update(filter_metadata)
            if subject_filter:
                where_clause["subject"] = subject_filter
            
            # Query ChromaDB
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_clause if where_clause else None
            )
            
            if results['documents'] and results['documents'][0]:
                documents = results['documents'][0]
                metadatas = results['metadatas'][0]
                distances = results['distances'][0]
                
                # Format results
                formatted_results = []
                for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
                    formatted_results.append({
                        "text": doc,
                        "metadata": metadata,
                        "similarity": 1 - distance,  # Convert distance to similarity
                        "rank": i + 1
                    })
                
                return formatted_results
            else:
                return []
        
        except Exception as e:
            print(f"❌ Error querying ChromaDB: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get ChromaDB collection statistics."""
        if not self.initialized:
            return {"error": "ChromaDB not initialized"}
        
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection.name,
                "embedding_model": self.embedding_model_name,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            return {"error": str(e)}
    
    def clear(self) -> bool:
        """Clear all data from the ChromaDB collection."""
        if not self.initialized:
            return False
        
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Agentic companion knowledge base"}
            )
            print(f"✅ Cleared ChromaDB collection: {self.collection_name}")
            return True
        except Exception as e:
            print(f"❌ Error clearing ChromaDB: {e}")
            return False
    
    def initialize_from_yaml(self, yaml_files: List[str] = None):
        """Initialize the ChromaDB system with YAML data."""
        
        print("🔄 Initializing ChromaDB with YAML data...")
        
        # Process each YAML file
        for yaml_file in yaml_files:
            if os.path.exists(yaml_file):
                print(f"📄 Processing {yaml_file}...")
                chunks = self.chunk_yaml_data(yaml_file)
                if chunks:
                    self.add_documents(chunks)
            else:
                print(f"⚠️ {yaml_file} not found, skipping...")
        
        # Print stats
        stats = self.get_stats()
        print(f"📊 ChromaDB stats: {stats}")
    
    def test_chromadb(self):
        """Test the ChromaDB backend."""
        print("🧪 Testing ChromaDB backend...")
        
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
        
        print("\n✅ ChromaDB backend tested!") 