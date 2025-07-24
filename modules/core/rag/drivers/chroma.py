"""
modules.core.rag.drivers.chroma - ChromaDB-based RAG driver

A ChromaDB-powered RAG driver for more advanced vector search capabilities.
Falls back gracefully if ChromaDB is not available.
"""

import os
import yaml
import uuid
import glob
from typing import List, Dict, Any, Optional

class ChromaDriver:
    """
    ChromaDB-based RAG driver
    
    Provides advanced vector search with ChromaDB backend.
    Gracefully degrades if ChromaDB is not available.
    """
    
    def __init__(self, 
                 collection_name: str = "knowledge_base",
                 persist_directory: str = "./chroma_db",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 data_dir: str = "./data"):
        """
        Initialize the ChromaDB driver
        
        Args:
            collection_name: Name of ChromaDB collection
            persist_directory: Directory to persist ChromaDB data
            embedding_model: Sentence transformer model name
            data_dir: Directory containing YAML knowledge files
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_model_name = embedding_model
        self.data_dir = data_dir
        self.client = None
        self.collection = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize ChromaDB and load knowledge base"""
        try:
            # Import ChromaDB
            import chromadb
            from chromadb.utils import embedding_functions
            
            # Create persistent client
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Set up embedding function
            sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model_name
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=sentence_transformer_ef
                )
                print(f"📄 Loaded existing ChromaDB collection: {self.collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=sentence_transformer_ef
                )
                print(f"🆕 Created new ChromaDB collection: {self.collection_name}")
                
                # Build knowledge base
                self._build_knowledge_base()
            
            self.initialized = True
            stats = self.get_stats()
            print(f"✅ ChromaDB initialized with {stats['documents']} documents")
            return True
            
        except ImportError:
            print("⚠️ ChromaDB not available, falling back to simple driver")
            return False
        except Exception as e:
            print(f"❌ Failed to initialize ChromaDB: {e}")
            return False
    
    def _build_knowledge_base(self):
        """Build knowledge base from YAML files"""
        print(f"🔨 Building ChromaDB knowledge base from {self.data_dir}")
        
        # Find all YAML files
        yaml_files = []
        if os.path.exists(self.data_dir):
            yaml_files = glob.glob(os.path.join(self.data_dir, "**/*.yaml"), recursive=True)
            yaml_files.extend(glob.glob(os.path.join(self.data_dir, "**/*.yml"), recursive=True))
        
        # Also check root directory
        yaml_files.extend(glob.glob("*.yaml"))
        yaml_files.extend(glob.glob("*.yml"))
        
        documents = []
        metadatas = []
        ids = []
        
        for yaml_file in yaml_files:
            try:
                chunks = self._extract_text_from_yaml(yaml_file)
                for i, chunk in enumerate(chunks):
                    documents.append(chunk)
                    metadatas.append({
                        'source': yaml_file,
                        'file': os.path.basename(yaml_file),
                        'chunk_id': i
                    })
                    ids.append(f"{os.path.basename(yaml_file)}_{i}_{uuid.uuid4().hex[:8]}")
            except Exception as e:
                print(f"⚠️ Error processing {yaml_file}: {e}")
        
        if not documents:
            print("⚠️ No documents found, adding default content")
            documents = ["I am an AI assistant ready to help with conversations, resume generation, and explanations."]
            metadatas = [{'source': 'default', 'type': 'default'}]
            ids = ['default_1']
        
        # Add to ChromaDB in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            self.collection.add(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids
            )
        
        print(f"💾 Added {len(documents)} documents to ChromaDB")
    
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
                            if len(text.strip()) > 10:
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
            
            extract_from_object(data)
            
            # Add file context
            if chunks:
                source_context = f"From {file_basename}: "
                chunks = [source_context + chunk for chunk in chunks]
            
            return chunks
            
        except Exception as e:
            print(f"⚠️ Error extracting from {yaml_file}: {e}")
            return []
    
    def query_similar(self, query_text: str, n_results: int = 5, 
                     filter_metadata: Dict = None, subject_filter: str = None) -> List[Dict[str, Any]]:
        """Query ChromaDB for similar documents"""
        if not self.initialized or not self.collection:
            return []
        
        try:
            # Build where clause from filters
            where_clause = {}
            if filter_metadata:
                where_clause.update(filter_metadata)
            if subject_filter:
                where_clause["category"] = subject_filter
            
            # Query ChromaDB
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_clause if where_clause else None
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and len(results['documents']) > 0:
                documents = results['documents'][0]  # First query result
                metadatas = results.get('metadatas', [[]])[0]
                distances = results.get('distances', [[]])[0]
                
                for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
                    # Convert distance to similarity score (ChromaDB uses L2 distance)
                    similarity = max(0.0, 1.0 - (dist / 2.0))  # Rough conversion
                    
                    formatted_results.append({
                        'content': doc,
                        'source': meta.get('source', 'unknown'),
                        'metadata': meta,
                        'score': similarity
                    })
            
            return formatted_results
            
        except Exception as e:
            print(f"⚠️ Error querying ChromaDB: {e}")
            return []
    
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Simple search interface (alias for query_similar)"""
        return self.query_similar(query, num_results)
    
    def initialize_from_yaml(self, yaml_files: List[str] = None) -> bool:
        """Initialize with specific YAML files"""
        if not self.initialized:
            success = self.initialize()
            if not success:
                return False
        
        if yaml_files and self.collection:
            # Clear existing data
            try:
                self.client.delete_collection(self.collection_name)
            except:
                pass
            
            # Recreate collection and add specific files
            try:
                import chromadb
                from chromadb.utils import embedding_functions
                
                sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=self.embedding_model_name
                )
                
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=sentence_transformer_ef
                )
                
                # Add specific YAML files
                documents = []
                metadatas = []
                ids = []
                
                for yaml_file in yaml_files:
                    if os.path.exists(yaml_file):
                        chunks = self._extract_text_from_yaml(yaml_file)
                        for i, chunk in enumerate(chunks):
                            documents.append(chunk)
                            metadatas.append({
                                'source': yaml_file,
                                'file': os.path.basename(yaml_file),
                                'chunk_id': i
                            })
                            ids.append(f"{os.path.basename(yaml_file)}_{i}_{uuid.uuid4().hex[:8]}")
                
                if documents:
                    self.collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                
                return True
                
            except Exception as e:
                print(f"⚠️ Error reinitializing with YAML files: {e}")
                return False
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get driver statistics"""
        doc_count = 0
        if self.collection:
            try:
                doc_count = self.collection.count()
            except:
                pass
                
        return {
            'type': 'chroma',
            'documents': doc_count,
            'collection_name': self.collection_name,
            'embedding_model': self.embedding_model_name,
            'initialized': self.initialized
        }