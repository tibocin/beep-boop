"""
modules/core/llm_client.py - Unified LLM client with Ollama primary and OpenAI fallback

This module provides a unified async interface for LLM interactions with Ollama as the primary
model and OpenAI as fallback. It handles authentication, request formatting, response parsing,
and error handling for all LLM interactions in the beep-boop system.

Key Features:
- Ollama as primary model (local, cost-effective)
- OpenAI as fallback (cloud, reliable)
- Async support with streaming capabilities
- Unified error handling and retry logic
- Request/response logging for analytics
- Support for different model configurations
- Token usage tracking
- Automatic fallback on Ollama failure
"""

import os
import logging
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List, AsyncGenerator
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk
import time
from .model_config import get_model_config, TaskType, Environment

logger = logging.getLogger(__name__)

class UnifiedLLMClient:
    """
    Unified LLM client with Ollama primary and OpenAI fallback
    
    Provides an async interface for LLM interactions with automatic fallback
    from Ollama to OpenAI when needed.
    """
    
    def __init__(self, 
                 ollama_url: str = "http://localhost:11434",
                 ollama_model: Optional[str] = None,
                 openai_api_key: Optional[str] = None,
                 openai_model: str = "gpt-4o-mini",
                 enable_fallback: bool = True,
                 fallback_timeout: float = 300.0,
                 environment: Environment = Environment.DEVELOPMENT,
                 force_openai_only: bool = False):
        """
        Initialize unified LLM client
        
        Args:
            ollama_url: Ollama server URL
            ollama_model: Primary Ollama model to use (auto-detected if None)
            openai_api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            openai_model: Fallback OpenAI model
            enable_fallback: Whether to enable OpenAI fallback
            fallback_timeout: Timeout for Ollama requests before falling back
            environment: Environment type for model selection
        """
        self.ollama_url = ollama_url.rstrip('/')
        self.environment = environment
        
        # Get model configuration
        self.model_config = get_model_config(environment)
        
        # Set Ollama model (use default from config if not specified)
        if ollama_model is None:
            self.ollama_model = self.model_config.default_models["parser"]
        else:
            self.ollama_model = ollama_model
            
        self.openai_model = openai_model
        self.enable_fallback = enable_fallback
        self.fallback_timeout = fallback_timeout
        
        # Initialize OpenAI client for fallback
        if enable_fallback:
            self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if not self.openai_api_key:
                logger.error("OpenAI API key not found. Fallback will be disabled.")
                self.enable_fallback = False
                if force_openai_only:
                    raise ValueError("OpenAI API key is required when force_openai_only=True")
            else:
                self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
        
        # Usage statistics
        self.usage_stats = {
            "total_requests": 0,
            "ollama_requests": 0,
            "openai_requests": 0,
            "fallback_requests": 0,
            "errors": 0,
            "ollama_errors": 0,
            "openai_errors": 0
        }
        
        logger.info(f"Unified LLM client initialized with Ollama model: {self.ollama_model}")
        logger.info(f"Environment: {self.environment.value}")
        if self.enable_fallback:
            logger.info(f"OpenAI fallback enabled with model: {openai_model}")
    
    def get_model_for_task(self, task: TaskType) -> str:
        """
        Get the appropriate model for a specific task
        
        Args:
            task: The task type
            
        Returns:
            Model name for the task
        """
        return self.model_config.get_model_for_task(task)
    
    def get_fallback_model(self, task: TaskType) -> str:
        """
        Get fallback model for a task
        
        Args:
            task: The task type
            
        Returns:
            Fallback model name
        """
        return self.model_config.get_fallback_model(task)
    
    async def _check_ollama_health(self) -> bool:
        """Check if Ollama server is healthy and accessible"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags", timeout=5.0) as response:
                    return response.status == 200
        except Exception as e:
            logger.debug(f"Ollama health check failed: {str(e)}")
            return False
    
    async def _ollama_chat_completion(self, 
                                     messages: List[Dict[str, str]], 
                                     temperature: float = 0.7,
                                     max_tokens: Optional[int] = None,
                                     system_prompt: Optional[str] = None,
                                     stream: bool = False) -> Dict[str, Any]:
        """Generate chat completion using Ollama API"""
        start_time = time.time()
        
        # Prepare messages with system prompt if provided
        ollama_messages = messages.copy()
        if system_prompt:
            ollama_messages.insert(0, {"role": "system", "content": system_prompt})
        
        # Prepare request payload
        payload = {
            "model": self.ollama_model,
            "messages": ollama_messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096,  # Limit context window to reduce memory usage
                "num_thread": 4   # Limit threads to reduce CPU usage
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.fallback_timeout, connect=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.ollama_url}/api/chat",
                    json=payload
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Ollama API error: {response.status}")
                    
                    if stream:
                        return await self._handle_ollama_streaming(response, start_time)
                    else:
                        return await self._handle_ollama_regular(response, start_time)
                        
        except Exception as e:
            self.usage_stats["ollama_errors"] += 1
            self.usage_stats["errors"] += 1
            logger.error(f"Ollama chat completion failed: {str(e)}")
            logger.error(f"Ollama URL: {self.ollama_url}")
            logger.error(f"Ollama model: {self.ollama_model}")
            logger.error(f"Payload: {payload}")
            logger.error(f"Exception type: {type(e).__name__}")
            if hasattr(e, '__traceback__'):
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    async def _handle_ollama_regular(self, response: aiohttp.ClientResponse, start_time: float) -> Dict[str, Any]:
        """Handle regular (non-streaming) Ollama response"""
        data = await response.json()
        
        response_text = data.get("message", {}).get("content", "")
        response_time = time.time() - start_time
        
        # Estimate token usage (rough approximation)
        estimated_tokens = len(response_text) // 4
        
        result = {
            "text": response_text,
            "usage": {
                "total_tokens": estimated_tokens,
                "prompt_tokens": 0,  # Not available from Ollama
                "completion_tokens": estimated_tokens
            },
            "metadata": {
                "model": self.ollama_model,
                "response_time": response_time,
                "finish_reason": "stop",
                "streamed": False,
                "provider": "ollama"
            }
        }
        
        self.usage_stats["ollama_requests"] += 1
        self.usage_stats["total_requests"] += 1
        
        logger.info(f"Ollama completion successful: {estimated_tokens} tokens, {response_time:.2f}s")
        return result
    
    async def _handle_ollama_streaming(self, response: aiohttp.ClientResponse, start_time: float) -> Dict[str, Any]:
        """Handle streaming Ollama response"""
        full_response = ""
        total_tokens = 0
        
        async for line in response.content:
            if line:
                try:
                    data = json.loads(line.decode().strip())
                    if "message" in data and data["message"].get("content"):
                        chunk_content = data["message"]["content"]
                        full_response += chunk_content
                        total_tokens += len(chunk_content) // 4
                except json.JSONDecodeError:
                    continue
        
        response_time = time.time() - start_time
        
        result = {
            "text": full_response,
            "usage": {
                "total_tokens": total_tokens,
                "prompt_tokens": 0,
                "completion_tokens": total_tokens
            },
            "metadata": {
                "model": self.ollama_model,
                "response_time": response_time,
                "finish_reason": "stop",
                "streamed": True,
                "provider": "ollama"
            }
        }
        
        self.usage_stats["ollama_requests"] += 1
        self.usage_stats["total_requests"] += 1
        
        logger.info(f"Ollama streaming completion successful: {total_tokens} tokens, {response_time:.2f}s")
        return result
    
    async def _ollama_chat_completion_stream(self, 
                                           messages: List[Dict[str, str]], 
                                           temperature: float = 0.7,
                                           max_tokens: Optional[int] = None,
                                           system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream chat completion using Ollama API"""
        # Prepare messages with system prompt if provided
        ollama_messages = messages.copy()
        if system_prompt:
            ollama_messages.insert(0, {"role": "system", "content": system_prompt})
        
        payload = {
            "model": self.ollama_model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096,  # Limit context window to reduce memory usage
                "num_thread": 4   # Limit threads to reduce CPU usage
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/chat",
                    json=payload,
                    timeout=self.fallback_timeout
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Ollama API error: {response.status}")
                    
                    chunk_count = 0
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode().strip())
                                if "message" in data and data["message"].get("content"):
                                    chunk = data["message"]["content"]
                                    chunk_count += 1
                                    
                                    # Add small delay every 10 chunks to reduce CPU usage
                                    if chunk_count % 10 == 0:
                                        await asyncio.sleep(0.001)  # 1ms delay
                                    
                                    yield chunk
                                    
                                    # Check for done flag
                                    if data.get("done", False):
                                        break
                                        
                            except json.JSONDecodeError:
                                continue
                            except Exception as e:
                                logger.warning(f"Error processing chunk: {e}")
                                continue
                                
        except Exception as e:
            self.usage_stats["ollama_errors"] += 1
            self.usage_stats["errors"] += 1
            logger.error(f"Ollama streaming failed: {str(e)}")
            raise
    
    async def _openai_chat_completion(self, 
                                     messages: List[Dict[str, str]], 
                                     temperature: float = 0.7,
                                     max_tokens: Optional[int] = None,
                                     system_prompt: Optional[str] = None,
                                     stream: bool = False) -> Dict[str, Any]:
        """Generate chat completion using OpenAI API (fallback)"""
        start_time = time.time()
        
        # Prepend system prompt if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        
        try:
            # Prepare request parameters
            params = {
                "model": self.openai_model,
                "messages": messages,
                "temperature": temperature,
                "stream": stream
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            # Make API call
            if stream:
                return await self._handle_openai_streaming_completion(params, start_time)
            else:
                return await self._handle_openai_regular_completion(params, start_time)
            
        except Exception as e:
            self.usage_stats["openai_errors"] += 1
            self.usage_stats["errors"] += 1
            logger.error(f"OpenAI chat completion failed: {str(e)}")
            raise
    
    async def _handle_openai_regular_completion(self, params: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Handle regular (non-streaming) OpenAI completion"""
        response = await self.openai_client.chat.completions.create(**params)
        
        # Extract response
        response_text = response.choices[0].message.content
        usage = response.usage
        
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
                "streamed": False,
                "provider": "openai"
            }
        }
        
        self.usage_stats["openai_requests"] += 1
        self.usage_stats["total_requests"] += 1
        
        logger.info(f"OpenAI completion successful: {usage.total_tokens} tokens, {response_time:.2f}s")
        return result
    
    async def _handle_openai_streaming_completion(self, params: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Handle streaming OpenAI completion"""
        full_response = ""
        total_tokens = 0
        
        stream = await self.openai_client.chat.completions.create(**params)
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
            
            # Update token count if available
            if hasattr(chunk, 'usage') and chunk.usage:
                total_tokens = chunk.usage.total_tokens
        
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
                "streamed": True,
                "provider": "openai"
            }
        }
        
        self.usage_stats["openai_requests"] += 1
        self.usage_stats["total_requests"] += 1
        
        logger.info(f"OpenAI streaming completion successful: {total_tokens} tokens, {response_time:.2f}s")
        return result
    
    async def chat_completion(self, 
                            messages: List[Dict[str, str]], 
                            model: Optional[str] = None,
                            temperature: float = 0.7,
                            max_tokens: Optional[int] = None,
                            system_prompt: Optional[str] = None,
                            stream: bool = False,
                            force_openai: bool = False) -> Dict[str, Any]:
        """
        Generate chat completion with Ollama primary and OpenAI fallback
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (ignored in unified client)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt to prepend
            stream: Whether to stream the response
            force_openai: Force using OpenAI instead of Ollama
            
        Returns:
            Dict containing response text, usage stats, and metadata
        """
        if force_openai:
            # Force OpenAI
            return await self._openai_chat_completion(
                messages, temperature, max_tokens, system_prompt, stream
            )
        
        if not self.enable_fallback:
            # Ollama only mode
            return await self._ollama_chat_completion(
                messages, temperature, max_tokens, stream
            )
        
        # Try Ollama first
        try:
            # Check Ollama health
            if not await self._check_ollama_health():
                logger.warning("Ollama server not available, using OpenAI fallback")
                self.usage_stats["fallback_requests"] += 1
                return await self._openai_chat_completion(
                    messages, temperature, max_tokens, system_prompt, stream
                )
            
            # Try Ollama
            return await self._ollama_chat_completion(
                messages, temperature, max_tokens, system_prompt, stream
            )
            
        except Exception as e:
            logger.warning(f"Ollama failed, falling back to OpenAI: {str(e)}")
            self.usage_stats["fallback_requests"] += 1
            return await self._openai_chat_completion(
                messages, temperature, max_tokens, system_prompt, stream
            )
    
    async def chat_completion_stream(self, 
                                   messages: List[Dict[str, str]], 
                                   model: Optional[str] = None,
                                   temperature: float = 0.7,
                                   max_tokens: Optional[int] = None,
                                   system_prompt: Optional[str] = None,
                                   force_openai: bool = False) -> AsyncGenerator[str, None]:
        """
        Stream chat completion with Ollama primary and OpenAI fallback
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (ignored in unified client)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt to prepend
            force_openai: Force using OpenAI instead of Ollama
            
        Yields:
            Response text chunks as they arrive
        """
        if force_openai:
            # Force OpenAI streaming
            async for chunk in self._openai_chat_completion_stream(
                messages, temperature, max_tokens, system_prompt
            ):
                yield chunk
            return
        
        if not self.enable_fallback:
            # Ollama only mode
            async for chunk in self._ollama_chat_completion_stream(
                messages, temperature, max_tokens, system_prompt
            ):
                yield chunk
            return
        
        # Try Ollama first
        try:
            # Check Ollama health
            if not await self._check_ollama_health():
                logger.warning("Ollama server not available, using OpenAI fallback")
                self.usage_stats["fallback_requests"] += 1
                async for chunk in self._openai_chat_completion_stream(
                    messages, temperature, max_tokens, system_prompt
                ):
                    yield chunk
                return
            
            # Try Ollama streaming
            async for chunk in self._ollama_chat_completion_stream(
                messages, temperature, max_tokens, system_prompt
            ):
                yield chunk
                
        except Exception as e:
            logger.warning(f"Ollama streaming failed, falling back to OpenAI: {str(e)}")
            self.usage_stats["fallback_requests"] += 1
            async for chunk in self._openai_chat_completion_stream(
                messages, temperature, max_tokens, system_prompt
            ):
                yield chunk
    
    async def _openai_chat_completion_stream(self, 
                                           messages: List[Dict[str, str]], 
                                           temperature: float = 0.7,
                                           max_tokens: Optional[int] = None,
                                           system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream chat completion using OpenAI API"""
        # Prepend system prompt if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        
        try:
            # Prepare request parameters
            params = {
                "model": self.openai_model,
                "messages": messages,
                "temperature": temperature,
                "stream": True
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            # Stream the response
            stream = await self.openai_client.chat.completions.create(**params)
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                        
        except Exception as e:
            self.usage_stats["openai_errors"] += 1
            self.usage_stats["errors"] += 1
            logger.error(f"OpenAI streaming failed: {str(e)}")
            raise
    
    async def get_embedding(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        """
        Generate embedding for text using OpenAI API (fallback only)
        
        Args:
            text: Text to embed
            model: Embedding model to use (OpenAI only)
            
        Returns:
            List of embedding values
        """
        try:
            response = await self.openai_client.embeddings.create(
                model=model,
                input=text
            )
            
            self.usage_stats["openai_requests"] += 1
            self.usage_stats["total_requests"] += 1
            
            return response.data[0].embedding
            
        except Exception as e:
            self.usage_stats["openai_errors"] += 1
            self.usage_stats["errors"] += 1
            logger.error(f"Embedding generation failed: {str(e)}")
            raise
    
    async def get_embeddings_batch(self, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        """
        Generate embeddings for multiple texts using OpenAI API (fallback only)
        
        Args:
            texts: List of texts to embed
            model: Embedding model to use (OpenAI only)
            
        Returns:
            List of embedding lists
        """
        try:
            response = await self.openai_client.embeddings.create(
                model=model,
                input=texts
            )
            
            self.usage_stats["openai_requests"] += 1
            self.usage_stats["total_requests"] += 1
            
            return [data.embedding for data in response.data]
            
        except Exception as e:
            self.usage_stats["openai_errors"] += 1
            self.usage_stats["errors"] += 1
            logger.error(f"Batch embedding generation failed: {str(e)}")
            raise
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        return self.usage_stats.copy()
    
    def reset_usage_stats(self):
        """Reset usage statistics"""
        self.usage_stats = {
            "total_requests": 0,
            "ollama_requests": 0,
            "openai_requests": 0,
            "fallback_requests": 0,
            "errors": 0,
            "ollama_errors": 0,
            "openai_errors": 0
        }
    
    async def list_models(self) -> List[str]:
        """Get list of available models (Ollama + OpenAI)"""
        models = []
        
        # Get Ollama models
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        ollama_models = [model["name"] for model in data.get("models", [])]
                        models.extend([f"ollama:{model}" for model in ollama_models])
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {str(e)}")
        
        # Get OpenAI models (only if fallback is enabled)
        if self.enable_fallback and hasattr(self, 'openai_client'):
            try:
                openai_models = await self.openai_client.models.list()
                models.extend([f"openai:{model.id}" for model in openai_models.data])
            except Exception as e:
                logger.warning(f"Failed to list OpenAI models: {str(e)}")
        
        return models

# Backward compatibility aliases
LLMClient = UnifiedLLMClient
AsyncOpenAIClient = UnifiedLLMClient  # For backward compatibility 