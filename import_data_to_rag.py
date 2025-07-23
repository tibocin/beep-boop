#!/usr/bin/env python3
"""
import_data_to_rag.py - Comprehensive Data Import Script

This script imports all YAML data files into the RAG system:
- Processes all YAML files from the modular data structure
- Chunks data with enhanced metadata
- Adds to ChromaDB for vector search
- Provides detailed import statistics

File: import_data_to_rag.py
Purpose: Import all YAML data into RAG system for knowledge retrieval
Related Components: modules/rag/, data/ directory
Tags: data-import, rag-integration, chunking, embeddings
"""

import os
import yaml
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
from modules.rag import RAGAdapter
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataImporter:
    """Comprehensive data importer for RAG system."""
    
    def __init__(self, data_dir: str = "data", rag_backend: str = "chroma"):
        """
        Initialize the data importer.
        
        Args:
            data_dir: Directory containing YAML data files
            rag_backend: RAG backend to use ("chroma", "simple", "auto")
        """
        self.data_dir = Path(data_dir)
        self.rag_adapter = RAGAdapter(backend_type=rag_backend)
        self.import_stats = {
            "total_files": 0,
            "total_chunks": 0,
            "successful_imports": 0,
            "failed_imports": 0,
            "file_details": {}
        }
    
    def discover_yaml_files(self) -> List[Path]:
        """Discover all YAML files in the data directory structure."""
        yaml_files = []
        
        # Search recursively for all YAML files
        for yaml_file in self.data_dir.rglob("*.yaml"):
            if yaml_file.is_file():
                yaml_files.append(yaml_file)
        
        # Sort by category and filename for consistent processing
        yaml_files.sort(key=lambda x: (x.parent.name, x.name))
        
        logger.info(f"📁 Discovered {len(yaml_files)} YAML files")
        return yaml_files
    
    def load_yaml_data(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load YAML data from file with error handling."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if data is None:
                logger.warning(f"⚠️ Empty YAML file: {file_path}")
                return None
            
            return data
            
        except yaml.YAMLError as e:
            logger.error(f"❌ YAML parsing error in {file_path}: {e}")
            return None
        except FileNotFoundError:
            logger.error(f"❌ File not found: {file_path}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error loading {file_path}: {e}")
            return None
    
    def chunk_yaml_data(self, data: Dict[str, Any], file_path: Path) -> List[Dict[str, Any]]:
        """Chunk YAML data into searchable documents with enhanced metadata."""
        chunks = []
        chunk_id = 0
        
        # Determine category from file path
        category = file_path.parent.name
        filename = file_path.name
        
        # Handle case where data is a list (not a dict)
        if isinstance(data, list):
            chunk = self._create_chunk(
                "list_content", "", data, file_path, category, chunk_id
            )
            if chunk:
                chunks.append(chunk)
                chunk_id += 1
            return chunks
        
        for section, content in data.items():
            if isinstance(content, dict):
                # Handle nested dictionary structure
                for key, value in content.items():
                    chunk = self._create_chunk(
                        section, key, value, file_path, category, chunk_id
                    )
                    if chunk:
                        chunks.append(chunk)
                        chunk_id += 1
            elif isinstance(content, list):
                # Handle list content
                chunk = self._create_chunk(
                    section, "", content, file_path, category, chunk_id
                )
                if chunk:
                    chunks.append(chunk)
                    chunk_id += 1
            else:
                # Handle simple key-value content
                chunk = self._create_chunk(
                    section, "", content, file_path, category, chunk_id
                )
                if chunk:
                    chunks.append(chunk)
                    chunk_id += 1
        
        return chunks
    
    def _create_chunk(self, section: str, key: str, value: Any, 
                     file_path: Path, category: str, chunk_id: int) -> Optional[Dict[str, Any]]:
        """Create a single chunk with enhanced metadata."""
        try:
            # Create chunk text
            if key:
                if isinstance(value, list):
                    chunk_text = f"{section} - {key}: {', '.join(str(item) for item in value)}"
                else:
                    chunk_text = f"{section} - {key}: {value}"
            else:
                if isinstance(value, list):
                    chunk_text = f"{section}: {', '.join(str(item) for item in value)}"
                else:
                    chunk_text = f"{section}: {value}"
            
            # Infer subject from content
            subject = self._infer_subject(section, key, chunk_text, category)
            
            # Create metadata
            metadata = {
                "section": section,
                "key": key if key else "",
                "source": str(file_path),
                "category": category,
                "filename": file_path.name,
                "type": "yaml_chunk",
                "subject": subject,
                "content_type": self._get_content_type(value),
                "chunk_id": chunk_id,
                "cross_references": self._extract_cross_references(value),
                "confidence": self._calculate_confidence(chunk_text)
            }
            
            return {
                "id": f"{category}_{file_path.name}_{chunk_id}",
                "text": chunk_text,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating chunk for {section}/{key}: {e}")
            return None
    
    def _infer_subject(self, section: str, key: str, text: str, category: str) -> str:
        """Infer the subject category from content."""
        text_lower = text.lower()
        section_lower = section.lower()
        key_lower = key.lower()
        category_lower = category.lower()
        
        # Category-based inference
        if category_lower == "personal":
            if any(word in text_lower for word in ["personality", "character", "traits"]):
                return "personality"
            elif any(word in text_lower for word in ["interest", "hobby", "passion"]):
                return "interests"
            elif any(word in text_lower for word in ["goal", "aspiration", "dream"]):
                return "goals"
            elif any(word in text_lower for word in ["value", "believe", "principle"]):
                return "values"
            elif any(word in text_lower for word in ["project", "work", "build"]):
                return "projects"
        
        elif category_lower == "career":
            if any(word in text_lower for word in ["work", "experience", "career", "job"]):
                return "work_experience"
            elif any(word in text_lower for word in ["technical", "skill", "problem", "solve"]):
                return "technical_skills"
        
        elif category_lower == "preferences":
            if any(word in text_lower for word in ["favorite", "like", "prefer", "movie", "book", "music"]):
                return "favorites"
        
        elif category_lower == "projects":
            return "projects"
        
        # Content-based inference
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
    
    def _get_content_type(self, value: Any) -> str:
        """Determine the content type of a value."""
        if isinstance(value, list):
            return "list"
        elif isinstance(value, dict):
            return "dict"
        elif isinstance(value, str):
            return "text"
        elif isinstance(value, (int, float)):
            return "numeric"
        else:
            return "other"
    
    def _extract_cross_references(self, value: Any) -> str:
        """Extract cross-references from content and return as string."""
        cross_refs = []
        
        if isinstance(value, str):
            # Look for cross-reference patterns
            if "cross_references:" in value:
                # Extract cross-references from string
                lines = value.split('\n')
                for line in lines:
                    if line.strip().startswith('- '):
                        cross_refs.append(line.strip()[2:])
        
        elif isinstance(value, list):
            # Check if list contains cross-references
            for item in value:
                if isinstance(item, str) and item.startswith('cross_references:'):
                    cross_refs.extend(item.split(':')[1].strip().split(', '))
        
        return ', '.join(cross_refs) if cross_refs else ""
    
    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence score for chunk quality."""
        # Simple confidence scoring based on text characteristics
        if len(text) < 10:
            return 0.3  # Very short text
        elif len(text) < 50:
            return 0.6  # Short text
        elif len(text) < 200:
            return 0.8  # Good length
        else:
            return 0.9  # Long, detailed text
    
    def import_file(self, file_path: Path) -> bool:
        """Import a single YAML file into the RAG system."""
        logger.info(f"📄 Processing {file_path}")
        
        try:
            # Load YAML data
            data = self.load_yaml_data(file_path)
            if data is None:
                self.import_stats["failed_imports"] += 1
                self.import_stats["file_details"][str(file_path)] = {
                    "status": "failed",
                    "reason": "Failed to load YAML data",
                    "chunks": 0
                }
                return False
            
            # Chunk the data
            chunks = self.chunk_yaml_data(data, file_path)
            if not chunks:
                logger.warning(f"⚠️ No chunks created for {file_path}")
                self.import_stats["failed_imports"] += 1
                self.import_stats["file_details"][str(file_path)] = {
                    "status": "failed",
                    "reason": "No chunks created",
                    "chunks": 0
                }
                return False
            
            # Add to RAG system
            success = self.rag_adapter.add_documents(chunks)
            
            if success:
                self.import_stats["successful_imports"] += 1
                self.import_stats["total_chunks"] += len(chunks)
                self.import_stats["file_details"][str(file_path)] = {
                    "status": "success",
                    "chunks": len(chunks),
                    "subjects": list(set(chunk["metadata"]["subject"] for chunk in chunks))
                }
                logger.info(f"✅ Successfully imported {len(chunks)} chunks from {file_path}")
                return True
            else:
                self.import_stats["failed_imports"] += 1
                self.import_stats["file_details"][str(file_path)] = {
                    "status": "failed",
                    "reason": "Failed to add to RAG system",
                    "chunks": len(chunks)
                }
                logger.error(f"❌ Failed to add chunks to RAG system: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error importing {file_path}: {e}")
            self.import_stats["failed_imports"] += 1
            self.import_stats["file_details"][str(file_path)] = {
                "status": "failed",
                "reason": str(e),
                "chunks": 0
            }
            return False
    
    def import_all_data(self) -> Dict[str, Any]:
        """Import all YAML data files into the RAG system."""
        logger.info("🚀 Starting comprehensive data import...")
        
        # Discover all YAML files
        yaml_files = self.discover_yaml_files()
        self.import_stats["total_files"] = len(yaml_files)
        
        if not yaml_files:
            logger.warning("⚠️ No YAML files found in data directory")
            return self.import_stats
        
        # Process each file
        for file_path in yaml_files:
            self.import_file(file_path)
        
        # Print summary statistics
        self._print_import_summary()
        
        return self.import_stats
    
    def _print_import_summary(self):
        """Print detailed import summary."""
        logger.info("\n" + "="*60)
        logger.info("📊 DATA IMPORT SUMMARY")
        logger.info("="*60)
        
        logger.info(f"📁 Total files discovered: {self.import_stats['total_files']}")
        logger.info(f"✅ Successful imports: {self.import_stats['successful_imports']}")
        logger.info(f"❌ Failed imports: {self.import_stats['failed_imports']}")
        logger.info(f"📝 Total chunks created: {self.import_stats['total_chunks']}")
        
        # Category breakdown
        categories = {}
        for file_path, details in self.import_stats["file_details"].items():
            if details["status"] == "success":
                category = Path(file_path).parent.name
                if category not in categories:
                    categories[category] = {"files": 0, "chunks": 0}
                categories[category]["files"] += 1
                categories[category]["chunks"] += details["chunks"]
        
        logger.info("\n📂 Category Breakdown:")
        for category, stats in categories.items():
            logger.info(f"  {category}: {stats['files']} files, {stats['chunks']} chunks")
        
        # Subject breakdown
        subjects = {}
        for file_path, details in self.import_stats["file_details"].items():
            if details["status"] == "success" and "subjects" in details:
                for subject in details["subjects"]:
                    if subject not in subjects:
                        subjects[subject] = 0
                    subjects[subject] += 1
        
        logger.info("\n🎯 Subject Breakdown:")
        for subject, count in sorted(subjects.items()):
            logger.info(f"  {subject}: {count} chunks")
        
        # Failed files
        failed_files = [f for f, d in self.import_stats["file_details"].items() 
                       if d["status"] == "failed"]
        if failed_files:
            logger.info("\n❌ Failed Files:")
            for file_path in failed_files:
                reason = self.import_stats["file_details"][file_path]["reason"]
                logger.info(f"  {file_path}: {reason}")
        
        logger.info("="*60)
    
    def test_rag_system(self):
        """Test the RAG system with sample queries."""
        logger.info("\n🧪 Testing RAG system with sample queries...")
        
        test_queries = [
            ("What are your values?", "values"),
            ("Tell me about your projects", "projects"),
            ("How do you solve problems?", "technical_skills"),
            ("What's your personality like?", "personality"),
            ("What are your interests?", "interests"),
            ("What's your work experience?", "work_experience"),
            ("What are your favorite movies?", "favorites")
        ]
        
        for query, expected_subject in test_queries:
            logger.info(f"\n🔍 Query: {query}")
            
            # Test subject-specific search
            results = self.rag_adapter.query_similar(
                query, n_results=2, subject_filter=expected_subject
            )
            
            if results:
                logger.info(f"  📚 Results for {expected_subject}:")
                for i, result in enumerate(results[:2]):
                    text_preview = result['text'][:80] + "..." if len(result['text']) > 80 else result['text']
                    logger.info(f"    {i+1}. {text_preview} (similarity: {result['similarity']:.3f})")
            else:
                logger.warning(f"  ⚠️ No results found for {expected_subject}")


def main():
    """Main function to run the data import process."""
    print("🚀 Agentic Companion - Data Import to RAG System")
    print("="*60)
    
    # Initialize importer
    importer = DataImporter(data_dir="data", rag_backend="chroma")
    
    # Import all data
    stats = importer.import_all_data()
    
    # Test the system
    if stats["successful_imports"] > 0:
        importer.test_rag_system()
    
    print("\n✅ Data import process completed!")
    print(f"📊 Total chunks available: {stats['total_chunks']}")


if __name__ == "__main__":
    main() 