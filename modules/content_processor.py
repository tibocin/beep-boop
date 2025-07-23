"""
Content Processor Module for Agentic Companion
File: modules/content_processor.py

Purpose: Processes diverse content types (writings, PDFs, profiles, assessments) 
         into standardized chunks for RAG system integration.

Related Components: content_detector.py, chunking_strategy.py, rag_adapter.py
Tags: content-processing, chunking, metadata, rag-integration
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ContentChunk:
    """Standardized content chunk with metadata"""
    id: str
    text: str
    metadata: Dict[str, Any]
    content_type: str
    source_file: str
    chunk_index: int


@dataclass
class ProcessingResult:
    """Result of content processing operation"""
    chunks: List[ContentChunk]
    metadata: Dict[str, Any]
    processing_stats: Dict[str, Any]
    errors: List[str]


class ContentProcessor:
    """
    Main content processor that handles diverse content types
    
    Processes writings, PDFs, profile exports, and personality assessments
    into standardized chunks with rich metadata for RAG integration.
    """
    
    def __init__(self):
        """Initialize content processor with extractors and strategies"""
        self.extractors = {
            'pdf': self._extract_pdf,
            'writing': self._extract_writing,
            'profile': self._extract_profile,
            'assessment': self._extract_assessment,
            'yaml': self._extract_yaml
        }
        
        self.chunking_strategies = {
            'pdf': self._chunk_pdf,
            'writing': self._chunk_writing,
            'profile': self._chunk_profile,
            'assessment': self._chunk_assessment,
            'yaml': self._chunk_yaml
        }
    
    def process_content(self, file_path: str, content_type: Optional[str] = None, 
                       custom_metadata: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """
        Process content file into standardized chunks
        
        Args:
            file_path: Path to content file
            content_type: Type of content (auto-detected if None)
            custom_metadata: Additional metadata to include
            
        Returns:
            ProcessingResult with chunks and metadata
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Auto-detect content type if not provided
            if content_type is None:
                content_type = self._detect_content_type(file_path)
            
            logger.info(f"Processing {content_type} content from {file_path}")
            
            # Extract content
            content = self.extractors[content_type](file_path)
            
            # Prepare metadata
            metadata = self._prepare_metadata(file_path, content_type, custom_metadata)
            
            # Chunk content
            chunks = self.chunking_strategies[content_type](content, metadata)
            
            # Generate processing stats
            stats = {
                'total_chunks': len(chunks),
                'content_type': content_type,
                'file_size': file_path.stat().st_size,
                'processing_time': 0  # TODO: Add timing
            }
            
            return ProcessingResult(
                chunks=chunks,
                metadata=metadata,
                processing_stats=stats,
                errors=[]
            )
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            return ProcessingResult(
                chunks=[],
                metadata={},
                processing_stats={},
                errors=[str(e)]
            )
    
    def _detect_content_type(self, file_path: Path) -> str:
        """Auto-detect content type from file extension and content"""
        extension = file_path.suffix.lower()
        
        if extension == '.pdf':
            return 'pdf'
        elif extension in ['.txt', '.md', '.docx']:
            return 'writing'
        elif extension in ['.json', '.yaml', '.yml']:
            return 'yaml'
        elif extension in ['.csv', '.xlsx']:
            return 'profile'
        else:
            # Try to analyze content
            return self._analyze_content(file_path)
    
    def _analyze_content(self, file_path: Path) -> str:
        """Analyze file content to determine type"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(1000)  # Read first 1000 chars
            
            # Check for YAML/JSON structure
            if content.strip().startswith('{') or content.strip().startswith('['):
                return 'profile'
            elif '---' in content or ':' in content:
                return 'yaml'
            else:
                return 'writing'
        except:
            return 'writing'  # Default fallback
    
    def _extract_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Extract content from PDF files"""
        try:
            import PyPDF2
            content = {
                'text': '',
                'pages': [],
                'metadata': {}
            }
            
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                content['metadata'] = pdf_reader.metadata
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    content['pages'].append({
                        'page_num': page_num + 1,
                        'text': page_text
                    })
                    content['text'] += page_text + '\n'
            
            return content
            
        except ImportError:
            logger.warning("PyPDF2 not available, using fallback PDF extraction")
            return self._extract_pdf_fallback(file_path)
    
    def _extract_pdf_fallback(self, file_path: Path) -> Dict[str, Any]:
        """Fallback PDF extraction using system tools"""
        import subprocess
        
        try:
            # Try pdftotext if available
            result = subprocess.run(['pdftotext', str(file_path), '-'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return {
                    'text': result.stdout,
                    'pages': [{'page_num': 1, 'text': result.stdout}],
                    'metadata': {}
                }
        except:
            pass
        
        # Return minimal content if extraction fails
        return {
            'text': f"PDF content from {file_path.name}",
            'pages': [],
            'metadata': {}
        }
    
    def _extract_writing(self, file_path: Path) -> Dict[str, Any]:
        """Extract content from writing files (txt, md, docx)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                'text': content,
                'title': file_path.stem,
                'sections': self._extract_sections(content)
            }
        except Exception as e:
            logger.error(f"Error extracting writing content: {e}")
            return {'text': '', 'title': file_path.stem, 'sections': []}
    
    def _extract_profile(self, file_path: Path) -> Dict[str, Any]:
        """Extract content from profile exports (JSON, CSV)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() == '.json':
                    content = json.load(f)
                else:
                    content = {'raw_content': f.read()}
            
            return content
        except Exception as e:
            logger.error(f"Error extracting profile content: {e}")
            return {'raw_content': ''}
    
    def _extract_assessment(self, file_path: Path) -> Dict[str, Any]:
        """Extract content from personality assessments"""
        return self._extract_profile(file_path)  # Same as profile for now
    
    def _extract_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Extract content from YAML files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
            
            return content
        except Exception as e:
            logger.error(f"Error extracting YAML content: {e}")
            return {'raw_content': ''}
    
    def _prepare_metadata(self, file_path: Path, content_type: str, 
                         custom_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Prepare standardized metadata for content"""
        metadata = {
            'content_type': content_type,
            'source_file': str(file_path),
            'file_name': file_path.name,
            'file_size': file_path.stat().st_size,
            'processing_date': str(Path().cwd()),
            'confidence': 0.9
        }
        
        if custom_metadata:
            metadata.update(custom_metadata)
        
        return metadata
    
    def _extract_sections(self, content: str) -> List[Dict[str, str]]:
        """Extract sections from writing content"""
        sections = []
        lines = content.split('\n')
        current_section = {'title': 'Introduction', 'content': ''}
        
        for line in lines:
            if line.strip().startswith('#'):
                if current_section['content'].strip():
                    sections.append(current_section)
                current_section = {
                    'title': line.strip('#').strip(),
                    'content': ''
                }
            else:
                current_section['content'] += line + '\n'
        
        if current_section['content'].strip():
            sections.append(current_section)
        
        return sections
    
    def _chunk_pdf(self, content: Dict[str, Any], metadata: Dict[str, Any]) -> List[ContentChunk]:
        """Chunk PDF content by pages and sections"""
        chunks = []
        chunk_index = 0
        
        for page in content.get('pages', []):
            page_text = page.get('text', '')
            if len(page_text) > 200:
                # Split long pages into smaller chunks
                words = page_text.split()
                for i in range(0, len(words), 150):
                    chunk_words = words[i:i+150]
                    chunk_text = ' '.join(chunk_words)
                    
                    chunks.append(ContentChunk(
                        id=f"pdf_{metadata['file_name']}_{page['page_num']}_{i//150}",
                        text=chunk_text,
                        metadata={
                            **metadata,
                            'page_num': page['page_num'],
                            'chunk_type': 'page_section'
                        },
                        content_type='pdf',
                        source_file=metadata['source_file'],
                        chunk_index=chunk_index
                    ))
                    chunk_index += 1
            else:
                chunks.append(ContentChunk(
                    id=f"pdf_{metadata['file_name']}_{page['page_num']}",
                    text=page_text,
                    metadata={
                        **metadata,
                        'page_num': page['page_num'],
                        'chunk_type': 'full_page'
                    },
                    content_type='pdf',
                    source_file=metadata['source_file'],
                    chunk_index=chunk_index
                ))
                chunk_index += 1
        
        return chunks
    
    def _chunk_writing(self, content: Dict[str, Any], metadata: Dict[str, Any]) -> List[ContentChunk]:
        """Chunk writing content by sections and paragraphs"""
        chunks = []
        chunk_index = 0
        
        # Process sections if available
        for section in content.get('sections', []):
            section_text = f"{section['title']}: {section['content']}"
            
            if len(section_text) > 200:
                # Split long sections
                words = section_text.split()
                for i in range(0, len(words), 150):
                    chunk_words = words[i:i+150]
                    chunk_text = ' '.join(chunk_words)
                    
                    chunks.append(ContentChunk(
                        id=f"writing_{metadata['file_name']}_{section['title']}_{i//150}",
                        text=chunk_text,
                        metadata={
                            **metadata,
                            'section_title': section['title'],
                            'chunk_type': 'section_part'
                        },
                        content_type='writing',
                        source_file=metadata['source_file'],
                        chunk_index=chunk_index
                    ))
                    chunk_index += 1
            else:
                chunks.append(ContentChunk(
                    id=f"writing_{metadata['file_name']}_{section['title']}",
                    text=section_text,
                    metadata={
                        **metadata,
                        'section_title': section['title'],
                        'chunk_type': 'full_section'
                    },
                    content_type='writing',
                    source_file=metadata['source_file'],
                    chunk_index=chunk_index
                ))
                chunk_index += 1
        
        # If no sections, chunk by paragraphs
        if not chunks:
            paragraphs = content.get('text', '').split('\n\n')
            for i, para in enumerate(paragraphs):
                if para.strip():
                    chunks.append(ContentChunk(
                        id=f"writing_{metadata['file_name']}_para_{i}",
                        text=para.strip(),
                        metadata={
                            **metadata,
                            'chunk_type': 'paragraph'
                        },
                        content_type='writing',
                        source_file=metadata['source_file'],
                        chunk_index=chunk_index
                    ))
                    chunk_index += 1
        
        return chunks
    
    def _chunk_profile(self, content: Dict[str, Any], metadata: Dict[str, Any]) -> List[ContentChunk]:
        """Chunk profile content by sections"""
        chunks = []
        chunk_index = 0
        
        # Handle different profile structures
        if isinstance(content, dict):
            for key, value in content.items():
                if isinstance(value, (str, int, float)):
                    chunk_text = f"{key}: {value}"
                    chunks.append(ContentChunk(
                        id=f"profile_{metadata['file_name']}_{key}",
                        text=chunk_text,
                        metadata={
                            **metadata,
                            'profile_section': key,
                            'chunk_type': 'profile_field'
                        },
                        content_type='profile',
                        source_file=metadata['source_file'],
                        chunk_index=chunk_index
                    ))
                    chunk_index += 1
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            item_text = json.dumps(item, indent=2)
                        else:
                            item_text = str(item)
                        
                        chunks.append(ContentChunk(
                            id=f"profile_{metadata['file_name']}_{key}_{i}",
                            text=f"{key} item {i+1}: {item_text}",
                            metadata={
                                **metadata,
                                'profile_section': key,
                                'item_index': i,
                                'chunk_type': 'profile_item'
                            },
                            content_type='profile',
                            source_file=metadata['source_file'],
                            chunk_index=chunk_index
                        ))
                        chunk_index += 1
        
        return chunks
    
    def _chunk_assessment(self, content: Dict[str, Any], metadata: Dict[str, Any]) -> List[ContentChunk]:
        """Chunk assessment content by traits and scores"""
        return self._chunk_profile(content, metadata)  # Same strategy for now
    
    def _chunk_yaml(self, content: Dict[str, Any], metadata: Dict[str, Any]) -> List[ContentChunk]:
        """Chunk YAML content by sections"""
        return self._chunk_profile(content, metadata)  # Same strategy for structured data


def process_content_directory(directory_path: str, processor: Optional[ContentProcessor] = None) -> List[ProcessingResult]:
    """
    Process all content files in a directory
    
    Args:
        directory_path: Path to directory containing content files
        processor: ContentProcessor instance (creates new one if None)
        
    Returns:
        List of ProcessingResult objects
    """
    if processor is None:
        processor = ContentProcessor()
    
    results = []
    directory = Path(directory_path)
    
    if not directory.exists():
        logger.error(f"Directory not found: {directory_path}")
        return results
    
    # Process all files in directory
    for file_path in directory.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.txt', '.md', '.json', '.yaml', '.yml', '.docx']:
            try:
                result = processor.process_content(str(file_path))
                results.append(result)
                logger.info(f"Processed {file_path.name}: {len(result.chunks)} chunks")
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
    
    return results 