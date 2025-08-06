"""
modules/core/openai_client.py - Async OpenAI SDK client wrapper with streaming

This module provides an async interface to OpenAI's API using the official SDK.
It handles authentication, request formatting, response parsing, and error handling
for all LLM interactions in the beep-boop system.

Key Features:
- Async OpenAI SDK integration with streaming support
- Chunk-based response processing
- Unified error handling and retry logic
- Request/response logging for analytics
- Support for different model configurations
- Token usage tracking
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk
import time

logger = logging.getLogger(__name__)

class AsyncOpenAIClient:
    """
    Async wrapper for OpenAI SDK client with enhanced functionality
    
    Provides an async interface for all OpenAI API interactions including
    chat completions, embeddings, and model management with streaming support.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize async OpenAI client
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Default model to use for completions
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.default_model = model
        self.usage_stats = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "requests": 0,
            "errors": 0
        }
        
        logger.info(f"Async OpenAI client initialized with model: {model}")
    
    async def chat_completion(self, 
                            messages: List[Dict[str, str]], 
                            model: Optional[str] = None,
                            temperature: float = 0.7,
                            max_tokens: Optional[int] = None,
                            system_prompt: Optional[str] = None,
                            stream: bool = False) -> Dict[str, Any]:
        """
        Generate chat completion using OpenAI API (async)
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to self.default_model)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt to prepend
            stream: Whether to stream the response
            
        Returns:
            Dict containing response text, usage stats, and metadata
        """
        start_time = time.time()
        model = model or self.default_model
        
        # Prepend system prompt if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        
        try:
            # Prepare request parameters
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": stream
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            # Make API call
            if stream:
                return await self._handle_streaming_completion(params, start_time)
            else:
                return await self._handle_regular_completion(params, start_time)
            
        except Exception as e:
            self.usage_stats["errors"] += 1
            logger.error(f"Chat completion failed: {str(e)}")
            raise
    
    async def chat_completion_stream(self, 
                                   messages: List[Dict[str, str]], 
                                   model: Optional[str] = None,
                                   temperature: float = 0.7,
                                   max_tokens: Optional[int] = None,
                                   system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        Stream chat completion chunks (async generator)
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to self.default_model)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt to prepend
            
        Yields:
            Response text chunks as they arrive
        """
        model = model or self.default_model
        
        # Prepend system prompt if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        
        try:
            # Prepare request parameters
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": True
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            # Stream the response
            stream = await self.client.chat.completions.create(**params)
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                        
        except Exception as e:
            self.usage_stats["errors"] += 1
            logger.error(f"Streaming chat completion failed: {str(e)}")
            raise
    
    async def _handle_regular_completion(self, params: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Handle regular (non-streaming) completion"""
        response = await self.client.chat.completions.create(**params)
        
        # Extract response
        response_text = response.choices[0].message.content
        usage = response.usage
        
        # Update usage stats
        self.usage_stats["total_tokens"] += usage.total_tokens
        self.usage_stats["prompt_tokens"] += usage.prompt_tokens
        self.usage_stats["completion_tokens"] += usage.completion_tokens
        self.usage_stats["requests"] += 1
        
        # Calculate response time
        response_time = time.time() - start_time
        
        result = {
            "text": response_text,
            "usage": {
                "total_tokens": usage.total_tokens,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens
            },
            "metadata": {
                "model": params["model"],
                "response_time": response_time,
                "finish_reason": response.choices[0].finish_reason,
                "streamed": False
            }
        }
        
        logger.info(f"Chat completion successful: {usage.total_tokens} tokens, {response_time:.2f}s")
        return result
    
    async def _handle_streaming_completion(self, params: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Handle streaming completion and collect full response"""
        full_response = ""
        total_tokens = 0
        
        stream = await self.client.chat.completions.create(**params)
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
            
            # Update token count if available
            if hasattr(chunk, 'usage') and chunk.usage:
                total_tokens = chunk.usage.total_tokens
        
        # Update usage stats (approximate for streaming)
        self.usage_stats["total_tokens"] += total_tokens
        self.usage_stats["completion_tokens"] += total_tokens
        self.usage_stats["requests"] += 1
        
        # Calculate response time
        response_time = time.time() - start_time
        
        result = {
            "text": full_response,
            "usage": {
                "total_tokens": total_tokens,
                "prompt_tokens": 0,  # Not available in streaming
                "completion_tokens": total_tokens
            },
            "metadata": {
                "model": params["model"],
                "response_time": response_time,
                "finish_reason": "stop",
                "streamed": True
            }
        }
        
        logger.info(f"Streaming completion successful: {total_tokens} tokens, {response_time:.2f}s")
        return result
    
    async def get_embedding(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        """
        Generate embedding for text using OpenAI API (async)
        
        Args:
            text: Text to embed
            model: Embedding model to use
            
        Returns:
            List of embedding values
        """
        try:
            response = await self.client.embeddings.create(
                model=model,
                input=text
            )
            
            # Update usage stats
            self.usage_stats["total_tokens"] += response.usage.total_tokens
            self.usage_stats["requests"] += 1
            
            return response.data[0].embedding
            
        except Exception as e:
            self.usage_stats["errors"] += 1
            logger.error(f"Embedding generation failed: {str(e)}")
            raise
    
    async def get_embeddings_batch(self, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        """
        Generate embeddings for multiple texts (async batch)
        
        Args:
            texts: List of texts to embed
            model: Embedding model to use
            
        Returns:
            List of embedding lists
        """
        try:
            response = await self.client.embeddings.create(
                model=model,
                input=texts
            )
            
            # Update usage stats
            self.usage_stats["total_tokens"] += response.usage.total_tokens
            self.usage_stats["requests"] += 1
            
            return [data.embedding for data in response.data]
            
        except Exception as e:
            self.usage_stats["errors"] += 1
            logger.error(f"Batch embedding generation failed: {str(e)}")
            raise
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        return self.usage_stats.copy()
    
    def reset_usage_stats(self):
        """Reset usage statistics"""
        self.usage_stats = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "requests": 0,
            "errors": 0
        }
    
    async def list_models(self) -> List[str]:
        """Get list of available models (async)"""
        try:
            models = await self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"Failed to list models: {str(e)}")
            return []

# Backward compatibility alias
OpenAIClient = AsyncOpenAIClient 