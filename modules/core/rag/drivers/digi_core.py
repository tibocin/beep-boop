"""
modules.core.rag.drivers.digi_core - Digi-Core RAG driver

A RAG driver that integrates with the Digi-Core API for personal knowledge retrieval.
Digi-Core serves as the single source of truth for personal knowledge and RAG operations.
"""

import os
import requests
import time
from typing import List, Dict, Any, Optional

class DigiCoreDriver:
    """
    Digi-Core RAG driver
    
    Integrates with Digi-Core API to provide:
    - Personal context retrieval
    - Query history tracking
    - Real-time data processing
    - Health monitoring
    - Performance analytics
    """
    
    def __init__(self, 
                 api_url: str = None,
                 api_key: str = None,
                 timeout: int = 10,
                 min_confidence: float = 0.2):
        """
        Initialize Digi-Core driver
        
        Args:
            api_url: Digi-Core API URL (defaults to environment variable)
            api_key: Digi-Core API key (defaults to environment variable)
            timeout: Request timeout in seconds
            min_confidence: Minimum confidence threshold
        """
        self.api_url = api_url or os.getenv('DIGI_CORE_API_URL', 'http://localhost:8000')
        self.api_key = api_key or os.getenv('DIGI_CORE_API_KEY')
        self.timeout = timeout
        self.min_confidence = min_confidence
        self.health_status = False
        self.stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'avg_response_time': 0,
            'last_query_time': None
        }
        
        if not self.api_key:
            raise ValueError("DIGI_CORE_API_KEY environment variable is required")
    
    def initialize(self) -> bool:
        """
        Initialize and verify Digi-Core connection
        
        Returns:
            True if Digi-Core is healthy and ready
        """
        try:
            # Check health endpoint
            response = requests.get(
                f"{self.api_url}/healthz",
                timeout=5
            )
            
            if response.status_code == 200:
                self.health_status = True
                print("✅ Digi-Core driver initialized successfully")
                return True
            else:
                print(f"❌ Digi-Core health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Digi-Core initialization failed: {str(e)}")
            return False
    
    def query_similar(self, 
                     query_text: str, 
                     n_results: int = 3,
                     filter_metadata: Dict = None,
                     subject_filter: str = None) -> List[Dict[str, Any]]:
        """
        Query Digi-Core for personal context
        
        Args:
            query_text: User query
            n_results: Number of results to return (handled by Digi-Core)
            filter_metadata: Metadata filters (not used in Digi-Core)
            subject_filter: Subject filter (not used in Digi-Core)
        
        Returns:
            List of context dictionaries with Digi-Core response
        """
        start_time = time.time()
        
        try:
            # Query Digi-Core API
            response = requests.post(
                f"{self.api_url}/query/",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"query": query_text},
                timeout=self.timeout
            )
            
            # Update stats
            self.stats['total_queries'] += 1
            self.stats['last_query_time'] = time.time()
            
            if response.status_code == 200:
                digi_core_response = response.json()
                response_time = time.time() - start_time
                
                # Update performance stats
                self.stats['successful_queries'] += 1
                self._update_avg_response_time(response_time)
                
                # Convert Digi-Core response to standard format
                context_list = self._convert_digi_core_response(digi_core_response)
                
                # Get actual confidence from metadata
                metadata = digi_core_response.get('metadata', {})
                actual_confidence = metadata.get('confidence_score', digi_core_response.get('confidence', 0))
                
                print(f"✅ Digi-Core query successful (confidence: {actual_confidence:.2f})")
                return context_list
                
            else:
                self.stats['failed_queries'] += 1
                print(f"❌ Digi-Core query failed: {response.status_code}")
                return []
                
        except Exception as e:
            self.stats['failed_queries'] += 1
            print(f"❌ Digi-Core query error: {str(e)}")
            return []
    
    def _convert_digi_core_response(self, digi_core_response: Dict) -> List[Dict[str, Any]]:
        """
        Convert Digi-Core API response to standard RAG format
        
        Args:
            digi_core_response: Raw response from Digi-Core API
        
        Returns:
            List of context dictionaries in standard format
        """
        # Extract confidence from metadata if available
        metadata = digi_core_response.get('metadata', {})
        confidence = metadata.get('confidence_score', 0)
        
        # Fallback to direct confidence field
        if confidence == 0:
            confidence = digi_core_response.get('confidence', 0)
        
        # Extract answer from results if available
        results = digi_core_response.get('results', [])
        answer = ""
        sources = []
        
        if results:
            # Get the first result's content
            first_result = results[0]
            answer = first_result.get('content', '')
            source = first_result.get('source', '')
            if source:
                sources = [source]
        
        # Fallback to direct answer field
        if not answer:
            answer = digi_core_response.get('answer', '')
        
        # Only return context if confidence meets threshold (handle negative scores)
        if confidence < self.min_confidence and confidence >= 0:
            return []
        
        # Create standard context format
        context = {
            'content': answer,
            'metadata': {
                'confidence': confidence,
                'source': 'digi-core',
                'sources': sources,
                'query_time': time.time()
            },
            'score': confidence  # Use confidence as similarity score
        }
        
        return [context]
    
    def _update_avg_response_time(self, response_time: float):
        """Update average response time statistics"""
        if self.stats['successful_queries'] == 1:
            self.stats['avg_response_time'] = response_time
        else:
            # Calculate running average
            current_avg = self.stats['avg_response_time']
            count = self.stats['successful_queries']
            self.stats['avg_response_time'] = (current_avg * (count - 1) + response_time) / count
    
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Alias for query_similar for compatibility"""
        return self.query_similar(query, num_results)
    
    def initialize_from_yaml(self, yaml_files: List[str] = None) -> bool:
        """
        Initialize from YAML files (not used in Digi-Core)
        
        Digi-Core handles data processing automatically.
        This method triggers a data refresh.
        """
        try:
            # Trigger data processing in Digi-Core
            response = requests.post(
                f"{self.api_url}/apps/process-data?incremental=true",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ Digi-Core data processing triggered successfully")
                return True
            else:
                print(f"❌ Digi-Core data processing failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error triggering Digi-Core data processing: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Digi-Core driver statistics"""
        return {
            'backend_type': 'digi-core',
            'health_status': self.health_status,
            'api_url': self.api_url,
            'stats': self.stats.copy(),
            'min_confidence': self.min_confidence
        } 