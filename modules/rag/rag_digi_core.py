"""
rag_digi_core.py - Digi-Core RAG Backend Integration

This module provides complete RAG functionality through the Digi-Core API.
Digi-Core serves as the single source of truth for personal knowledge and RAG operations.

File: modules/rag/rag_digi_core.py
Purpose: Primary RAG backend using Digi-Core API for personal knowledge retrieval
Related: RAGAdapter, digi-core API integration
Tags: rag, digi-core, api, personal-knowledge
"""

import os
import requests
import time
from typing import List, Dict, Optional
from .rag_adapter import RAGBackend

class DigiCoreBackend(RAGBackend):
    """
    Digi-Core RAG Backend - Single source of truth for personal knowledge.
    
    This backend integrates with Digi-Core API to provide:
    - Personal context retrieval
    - Query history tracking
    - Real-time data processing
    - Health monitoring
    - Performance analytics
    """
    
    def __init__(self, **kwargs):
        """
        Initialize Digi-Core backend.
        
        Args:
            api_url: Digi-Core API URL (default: http://localhost:8000)
            api_key: Digi-Core API key (required)
            timeout: Request timeout in seconds (default: 10)
            min_confidence: Minimum confidence threshold (default: 0.3)
        """
        self.api_url = kwargs.get('api_url', os.getenv('DIGI_CORE_API_URL', 'http://localhost:8000'))
        self.api_key = kwargs.get('api_key', os.getenv('DIGI_CORE_API_KEY'))
        self.timeout = kwargs.get('timeout', 10)
        self.min_confidence = kwargs.get('min_confidence', 0.3)
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
        Initialize and verify Digi-Core connection.
        
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
                print("✅ Digi-Core backend initialized successfully")
                return True
            else:
                print(f"❌ Digi-Core health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Digi-Core initialization failed: {str(e)}")
            return False
    
    def add_documents(self, documents: List[Dict]) -> bool:
        """
        Process documents through Digi-Core.
        
        Note: Digi-Core handles document processing automatically.
        This method triggers a data refresh.
        
        Args:
            documents: List of document dictionaries (not used directly)
        
        Returns:
            True if data processing was triggered successfully
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
    
    def query_similar(self, 
                     query_text: str, 
                     n_results: int = 3,
                     filter_metadata: Dict = None,
                     subject_filter: str = None) -> List[Dict]:
        """
        Query Digi-Core for personal context.
        
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
                
                print(f"✅ Digi-Core query successful (confidence: {digi_core_response.get('confidence', 0):.2f})")
                return context_list
                
            else:
                self.stats['failed_queries'] += 1
                print(f"❌ Digi-Core query failed: {response.status_code}")
                return []
                
        except Exception as e:
            self.stats['failed_queries'] += 1
            print(f"❌ Digi-Core query error: {str(e)}")
            return []
    
    def _convert_digi_core_response(self, digi_core_response: Dict) -> List[Dict]:
        """
        Convert Digi-Core API response to standard RAG format.
        
        Args:
            digi_core_response: Raw response from Digi-Core API
        
        Returns:
            List of context dictionaries in standard format
        """
        confidence = digi_core_response.get('confidence', 0)
        answer = digi_core_response.get('answer', '')
        sources = digi_core_response.get('sources', [])
        
        # Only return context if confidence meets threshold
        if confidence < self.min_confidence:
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
        """Update average response time statistics."""
        if self.stats['successful_queries'] == 1:
            self.stats['avg_response_time'] = response_time
        else:
            # Calculate running average
            current_avg = self.stats['avg_response_time']
            count = self.stats['successful_queries']
            self.stats['avg_response_time'] = (current_avg * (count - 1) + response_time) / count
    
    def get_stats(self) -> Dict:
        """
        Get Digi-Core backend statistics.
        
        Returns:
            Dictionary with performance and health metrics
        """
        stats = self.stats.copy()
        stats.update({
            'backend_type': 'digi-core',
            'api_url': self.api_url,
            'health_status': self.health_status,
            'min_confidence': self.min_confidence,
            'success_rate': (
                stats['successful_queries'] / max(stats['total_queries'], 1)
            )
        })
        
        return stats
    
    def clear(self) -> bool:
        """
        Clear Digi-Core data.
        
        Note: This would require Digi-Core API support for data clearing.
        Currently returns True as Digi-Core manages its own data.
        
        Returns:
            True (Digi-Core manages data lifecycle)
        """
        print("ℹ️ Digi-Core manages its own data lifecycle")
        return True
    
    def get_query_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent query history from Digi-Core.
        
        Args:
            limit: Maximum number of queries to return
        
        Returns:
            List of recent queries
        """
        try:
            response = requests.get(
                f"{self.api_url}/query/history?limit={limit}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                history_data = response.json()
                # Ensure we return a list of dictionaries
                if isinstance(history_data, list):
                    return history_data
                elif isinstance(history_data, dict) and 'queries' in history_data:
                    return history_data['queries']
                else:
                    return []
            else:
                print(f"❌ Failed to get query history: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting query history: {str(e)}")
            return []
    
    def detect_unfamiliar_queries(self, query: str) -> Dict:
        """
        Detect if a query is unfamiliar to the knowledge base.
        
        Args:
            query: User query to analyze
        
        Returns:
            Dictionary with unfamiliar detection results
        """
        try:
            response = requests.post(
                f"{self.api_url}/query/detect-unfamiliar",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"query": query},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"is_unfamiliar": False, "confidence": 0}
                
        except Exception as e:
            print(f"❌ Error detecting unfamiliar query: {str(e)}")
            return {"is_unfamiliar": False, "confidence": 0} 