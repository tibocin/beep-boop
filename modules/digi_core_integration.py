"""
digi_core_integration.py - Digi-Core Integration for Beep-Boop

This module provides high-level integration functions for using Digi-Core
as the primary knowledge source for Beep-Boop responses.

File: modules/digi_core_integration.py
Purpose: High-level digi-core integration functions for response enhancement
Related: RAGAdapter, DigiCoreBackend, response generation
Tags: digi-core, integration, response-enhancement, personal-context
"""

import os
import time
from typing import Dict, Optional, List
from .rag.rag_digi_core import DigiCoreBackend

class DigiCoreIntegration:
    """
    High-level Digi-Core integration for Beep-Boop.
    
    This class provides simplified interfaces for:
    - Personal context retrieval
    - Response enhancement
    - Health monitoring
    - Performance tracking
    """
    
    def __init__(self, api_key: str = None, api_url: str = None):
        """
        Initialize Digi-Core integration.
        
        Args:
            api_key: Digi-Core API key (defaults to environment variable)
            api_url: Digi-Core API URL (defaults to environment variable)
        """
        self.api_key = api_key or os.getenv('DIGI_CORE_API_KEY')
        self.api_url = api_url or os.getenv('DIGI_CORE_API_URL', 'http://localhost:8000')
        self.min_confidence = float(os.getenv('DIGI_CORE_MIN_CONFIDENCE', '0.3'))
        self.enabled = os.getenv('DIGI_CORE_ENABLED', 'true').lower() == 'true'
        
        # Initialize backend
        self.backend = None
        if self.api_key and self.enabled:
            self.backend = DigiCoreBackend(
                api_key=self.api_key,
                api_url=self.api_url,
                min_confidence=self.min_confidence
            )
    
    def is_available(self) -> bool:
        """
        Check if Digi-Core integration is available and healthy.
        
        Returns:
            True if Digi-Core is ready to use
        """
        if not self.enabled or not self.backend:
            return False
        
        return self.backend.initialize()
    
    def get_personal_context(self, query: str) -> Dict:
        """
        Retrieve personal context for a user query.
        
        Args:
            query: User's question or input
        
        Returns:
            Dictionary with personal context and metadata
        """
        if not self.is_available():
            return {
                'answer': '',
                'confidence': 0.0,
                'sources': [],
                'error': 'Digi-Core not available'
            }
        
        try:
            # Query Digi-Core backend
            results = self.backend.query_similar(query, n_results=1)
            
            if results:
                result = results[0]
                return {
                    'answer': result['content'],
                    'confidence': result['metadata']['confidence'],
                    'sources': result['metadata'].get('sources', []),
                    'query_time': result['metadata']['query_time']
                }
            else:
                return {
                    'answer': '',
                    'confidence': 0.0,
                    'sources': [],
                    'error': 'No relevant personal context found'
                }
                
        except Exception as e:
            return {
                'answer': '',
                'confidence': 0.0,
                'sources': [],
                'error': f'Digi-Core query failed: {str(e)}'
            }
    
    def enhance_response(self, 
                        user_query: str, 
                        base_response: str,
                        include_context: bool = True) -> str:
        """
        Enhance Beep-Boop's response with personal context.
        
        Args:
            user_query: Original user input
            base_response: Beep-Boop's base response
            include_context: Whether to include personal context
        
        Returns:
            Enhanced response with personal context
        """
        if not include_context or not self.is_available():
            return base_response
        
        # Get personal context
        context = self.get_personal_context(user_query)
        
        if context.get('error') or context['confidence'] < self.min_confidence:
            return base_response
        
        # Enhance response with personal context
        enhanced_response = f"""
{base_response}

Personal Context (Confidence: {context['confidence']:.1%}):
{context['answer']}
        """.strip()
        
        return enhanced_response
    
    def detect_unfamiliar_query(self, query: str) -> Dict:
        """
        Detect if a query is unfamiliar to the knowledge base.
        
        Args:
            query: User query to analyze
        
        Returns:
            Dictionary with unfamiliar detection results
        """
        if not self.is_available():
            return {"is_unfamiliar": False, "confidence": 0}
        
        return self.backend.detect_unfamiliar_queries(query)
    
    def get_query_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent query history for debugging and analysis.
        
        Args:
            limit: Maximum number of queries to return
        
        Returns:
            List of recent queries
        """
        if not self.is_available():
            return []
        
        return self.backend.get_query_history(limit)
    
    def refresh_data(self) -> bool:
        """
        Trigger processing of updated personal data.
        
        Returns:
            True if data refresh was successful
        """
        if not self.is_available():
            return False
        
        return self.backend.add_documents([])  # Empty list triggers refresh
    
    def get_performance_stats(self) -> Dict:
        """
        Get Digi-Core performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.backend:
            return {
                'enabled': False,
                'error': 'Digi-Core not initialized'
            }
        
        stats = self.backend.get_stats()
        stats['enabled'] = self.enabled
        stats['min_confidence'] = self.min_confidence
        
        return stats
    
    def health_check(self) -> Dict:
        """
        Perform comprehensive health check.
        
        Returns:
            Dictionary with health status and details
        """
        health_status = {
            'enabled': self.enabled,
            'api_key_configured': bool(self.api_key),
            'api_url': self.api_url,
            'backend_available': False,
            'health_check_passed': False,
            'last_check': time.time()
        }
        
        if not self.enabled:
            health_status['error'] = 'Digi-Core integration disabled'
            return health_status
        
        if not self.api_key:
            health_status['error'] = 'DIGI_CORE_API_KEY not configured'
            return health_status
        
        if not self.backend:
            health_status['error'] = 'Backend not initialized'
            return health_status
        
        # Test backend health
        try:
            health_status['backend_available'] = True
            health_status['health_check_passed'] = self.backend.initialize()
            
            if health_status['health_check_passed']:
                health_status['status'] = 'healthy'
            else:
                health_status['error'] = 'Backend health check failed'
                
        except Exception as e:
            health_status['error'] = f'Health check error: {str(e)}'
        
        return health_status

# Convenience functions for easy integration
def get_digi_core_integration() -> DigiCoreIntegration:
    """
    Get a configured Digi-Core integration instance.
    
    Returns:
        Configured DigiCoreIntegration instance
    """
    return DigiCoreIntegration()

def enhance_beep_boop_response(user_query: str, base_response: str) -> str:
    """
    Convenience function to enhance Beep-Boop response with personal context.
    
    Args:
        user_query: Original user input
        base_response: Beep-Boop's base response
    
    Returns:
        Enhanced response with personal context
    """
    integration = get_digi_core_integration()
    return integration.enhance_response(user_query, base_response)

def check_digi_core_health() -> Dict:
    """
    Convenience function to check Digi-Core health.
    
    Returns:
        Health status dictionary
    """
    integration = get_digi_core_integration()
    return integration.health_check() 