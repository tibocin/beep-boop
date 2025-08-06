"""
modules/core/synthesizer.py - Async LLM response synthesizer using OpenAI SDK

This module generates conversational responses using OpenAI's API directly with async support.
It handles context integration, knowledge synthesis, and response formatting
for the beep-boop conversation system.

Key Features:
- Async OpenAI SDK integration with streaming support
- Context-aware response generation
- Knowledge base integration
- Voice mode optimization
- Response quality control
- Real-time streaming responses
"""

import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from .openai_client import AsyncOpenAIClient

logger = logging.getLogger(__name__)

class AsyncLLMSynthesizer:
    """
    Async LLM-powered response synthesizer using OpenAI SDK
    
    Generates conversational responses by integrating user input,
    retrieved context, and conversation history with streaming support.
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize the async LLM synthesizer
        
        Args:
            model: OpenAI model to use for response generation
        """
        self.client = AsyncOpenAIClient(model=model)
        self.model = model
        
        # Base system prompt for response generation
        self.base_system_prompt = """You are a helpful AI assistant with access to comprehensive knowledge about Stephen Saunders and his work. 

Your responses should be:
- Conversational and engaging
- Accurate and well-informed
- Tailored to the user's specific needs
- Professional when appropriate
- Creative and insightful

You have access to detailed information about:
- Stephen's professional background and technical skills
- His work experience and projects
- Personal interests and values
- Creative projects and achievements
- Technical expertise and knowledge

Use this knowledge to provide helpful, personalized responses."""
        
        logger.info(f"Async LLM Synthesizer initialized with model: {model}")
    
    async def synthesize_response(self, 
                                user_input: str,
                                retrieved_context: Optional[List[Dict[str, Any]]] = None,
                                conversation_history: Optional[List[Dict[str, str]]] = None,
                                parsed_request: Optional[Dict[str, Any]] = None,
                                voice_mode: bool = False,
                                stream: bool = False) -> Dict[str, Any]:
        """
        Synthesize a response using OpenAI API (async)
        
        Args:
            user_input: Original user input
            retrieved_context: Retrieved relevant information from knowledge base
            conversation_history: Previous conversation messages
            parsed_request: Parsed request information
            voice_mode: Whether this is for voice interaction
            stream: Whether to stream the response
            
        Returns:
            Dict containing response text and metadata
        """
        try:
            # Build system prompt
            system_prompt = self._build_system_prompt(parsed_request, voice_mode)
            
            # Build messages
            messages = self._build_messages(user_input, retrieved_context, conversation_history)
            
            # Generate response
            response = await self.client.chat_completion(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.7 if not voice_mode else 0.8,  # Slightly higher for voice
                max_tokens=1000 if voice_mode else 1500,  # Shorter for voice
                stream=stream
            )
            
            # Add metadata
            response["metadata"].update({
                "synthesizer_model": self.model,
                "voice_mode": voice_mode,
                "context_used": len(retrieved_context) if retrieved_context else 0,
                "history_length": len(conversation_history) if conversation_history else 0
            })
            
            logger.info(f"Response synthesized: {response['usage']['total_tokens']} tokens")
            return response
            
        except Exception as e:
            logger.error(f"Response synthesis failed: {str(e)}")
            return self._create_fallback_response(user_input, voice_mode)
    
    async def synthesize_response_stream(self, 
                                       user_input: str,
                                       retrieved_context: Optional[List[Dict[str, Any]]] = None,
                                       conversation_history: Optional[List[Dict[str, str]]] = None,
                                       parsed_request: Optional[Dict[str, Any]] = None,
                                       voice_mode: bool = False) -> AsyncGenerator[str, None]:
        """
        Stream response synthesis (async generator)
        
        Args:
            user_input: Original user input
            retrieved_context: Retrieved relevant information from knowledge base
            conversation_history: Previous conversation messages
            parsed_request: Parsed request information
            voice_mode: Whether this is for voice interaction
            
        Yields:
            Response text chunks as they're generated
        """
        try:
            # Build system prompt
            system_prompt = self._build_system_prompt(parsed_request, voice_mode)
            
            # Build messages
            messages = self._build_messages(user_input, retrieved_context, conversation_history)
            
            # Stream response
            async for chunk in self.client.chat_completion_stream(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.7 if not voice_mode else 0.8,
                max_tokens=1000 if voice_mode else 1500
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"Streaming response synthesis failed: {str(e)}")
            yield f"Error generating response: {str(e)}"
    
    async def generate_resume_content(self, 
                                    request_details: Dict[str, Any],
                                    user_data: Dict[str, Any],
                                    stream: bool = False) -> Dict[str, Any]:
        """
        Generate resume content using OpenAI API (async)
        
        Args:
            request_details: Details about the resume request
            user_data: User's background information
            stream: Whether to stream the response
            
        Returns:
            Dict containing generated resume content
        """
        try:
            system_prompt = """You are an expert resume writer with deep knowledge of Stephen Saunders' background.

Your task is to create compelling resume content that:
- Highlights relevant skills and experience
- Uses strong action verbs and quantifiable achievements
- Is tailored to the specific request
- Maintains professional standards
- Is concise and impactful

Focus on the most relevant aspects of Stephen's background for the given request."""
            
            # Prepare context
            context = f"""
REQUEST DETAILS:
{self._format_dict(request_details)}

USER BACKGROUND:
{self._format_dict(user_data)}
"""
            
            messages = [
                {"role": "user", "content": f"Generate resume content based on this request:\n\n{context}"}
            ]
            
            response = await self.client.chat_completion(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more consistent output
                max_tokens=2000,
                stream=stream
            )
            
            response["metadata"]["content_type"] = "resume"
            return response
            
        except Exception as e:
            logger.error(f"Resume generation failed: {str(e)}")
            return self._create_fallback_response("resume generation request", False)
    
    async def generate_resume_content_stream(self, 
                                           request_details: Dict[str, Any],
                                           user_data: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        Stream resume content generation (async generator)
        
        Args:
            request_details: Details about the resume request
            user_data: User's background information
            
        Yields:
            Resume content chunks as they're generated
        """
        try:
            system_prompt = """You are an expert resume writer with deep knowledge of Stephen Saunders' background.

Your task is to create compelling resume content that:
- Highlights relevant skills and experience
- Uses strong action verbs and quantifiable achievements
- Is tailored to the specific request
- Maintains professional standards
- Is concise and impactful

Focus on the most relevant aspects of Stephen's background for the given request."""
            
            # Prepare context
            context = f"""
REQUEST DETAILS:
{self._format_dict(request_details)}

USER BACKGROUND:
{self._format_dict(user_data)}
"""
            
            messages = [
                {"role": "user", "content": f"Generate resume content based on this request:\n\n{context}"}
            ]
            
            async for chunk in self.client.chat_completion_stream(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2000
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"Streaming resume generation failed: {str(e)}")
            yield f"Error generating resume content: {str(e)}"
    
    def _build_system_prompt(self, parsed_request: Optional[Dict[str, Any]], voice_mode: bool) -> str:
        """
        Build system prompt based on request and mode
        
        Args:
            parsed_request: Parsed request information
            voice_mode: Whether this is for voice interaction
            
        Returns:
            Formatted system prompt
        """
        prompt = self.base_system_prompt
        
        # Add voice-specific instructions
        if voice_mode:
            prompt += """

VOICE MODE CONSIDERATIONS:
- Keep responses concise and natural for speech
- Use conversational language
- Avoid complex formatting
- Structure information clearly for audio consumption"""
        
        # Add intent-specific instructions
        if parsed_request:
            intent = parsed_request.get("intent", "")
            if "search" in intent.lower():
                prompt += "\n\nSEARCH MODE: Provide comprehensive information based on the query."
            elif "explain" in intent.lower():
                prompt += "\n\nEXPLANATION MODE: Provide clear, detailed explanations with examples."
            elif "summarize" in intent.lower():
                prompt += "\n\nSUMMARIZATION MODE: Provide concise, well-structured summaries."
        
        return prompt
    
    def _build_messages(self, 
                       user_input: str,
                       retrieved_context: Optional[List[Dict[str, Any]]],
                       conversation_history: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
        """
        Build messages for OpenAI API
        
        Args:
            user_input: Original user input
            retrieved_context: Retrieved context information
            conversation_history: Previous conversation messages
            
        Returns:
            List of message dictionaries
        """
        messages = []
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history[-10:])  # Last 10 messages
        
        # Add context if available
        if retrieved_context:
            context_text = self._format_context(retrieved_context)
            messages.append({
                "role": "system",
                "content": f"RELEVANT CONTEXT:\n{context_text}\n\nUse this information to provide an informed response."
            })
        
        # Add current user input
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
    def _format_context(self, context_list: List[Dict[str, Any]]) -> str:
        """
        Format retrieved context for inclusion in messages
        
        Args:
            context_list: List of context dictionaries
            
        Returns:
            Formatted context string
        """
        formatted_parts = []
        
        for i, context in enumerate(context_list, 1):
            content = context.get("content", "")
            source = context.get("source", "unknown")
            score = context.get("score", 0)
            
            formatted_parts.append(f"{i}. {content}\n   Source: {source} (relevance: {score:.2f})")
        
        return "\n\n".join(formatted_parts)
    
    def _format_dict(self, data: Dict[str, Any]) -> str:
        """
        Format dictionary for inclusion in prompts
        
        Args:
            data: Dictionary to format
            
        Returns:
            Formatted string
        """
        formatted_parts = []
        for key, value in data.items():
            if isinstance(value, dict):
                formatted_parts.append(f"{key}:")
                for sub_key, sub_value in value.items():
                    formatted_parts.append(f"  {sub_key}: {sub_value}")
            else:
                formatted_parts.append(f"{key}: {value}")
        
        return "\n".join(formatted_parts)
    
    def _create_fallback_response(self, user_input: str, voice_mode: bool) -> Dict[str, Any]:
        """
        Create fallback response when synthesis fails
        
        Args:
            user_input: Original user input
            voice_mode: Whether this is for voice interaction
            
        Returns:
            Fallback response dictionary
        """
        fallback_text = "I apologize, but I'm having trouble generating a response right now. Could you please try rephrasing your question?"
        
        if voice_mode:
            fallback_text = "I'm sorry, I'm having some technical difficulties. Could you please repeat your question?"
        
        return {
            "text": fallback_text,
            "usage": {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0},
            "metadata": {
                "model": self.model,
                "fallback_response": True,
                "voice_mode": voice_mode,
                "error": "synthesis_failed"
            }
        }

# Backward compatibility alias
LLMSynthesizer = AsyncLLMSynthesizer