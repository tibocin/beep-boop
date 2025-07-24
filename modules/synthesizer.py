"""
synthesizer.py - Response Synthesis

This module handles:
- Multi-prompt response synthesis
- Response coherence and flow
- Parser-based response format management
"""

import openai
from typing import List, Dict, Optional, Tuple
from .enums import ReqPrompt, Subject, Format, Tone, OutputStyle, ResponseFormat
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResponseSynthesizer:
    """Synthesizes multiple prompt responses into coherent output."""
    
    def synthesize_responses(self, 
                           responses: List[Tuple[ReqPrompt, str]], 
                           original_message: str,
                           context: str = "",
                           response_objective: str = "") -> str:
        """
        Synthesize multiple responses into a coherent final response.
        
        Args:
            responses: List of (prompt, response) tuples
            original_message: Original user message
            context: RAG context used
            response_objective: The objective of the response
            
        Returns:
            Synthesized response
        """
        if not responses:
            return "I apologize, but I couldn't generate a response."
        
        if len(responses) == 1:
            # Single response - just return it
            return responses[0][1]
        
        # Multiple responses - synthesize them
        try:
            # Determine synthesis approach based on response formats
            response_formats = [prompt.response_format for prompt, _ in responses]
            
            # Use the most detailed format as the target for synthesis
            format_priority = {
                ResponseFormat.EXPANDED: 5,
                ResponseFormat.DETAILED: 4,
                ResponseFormat.CONVERSATIONAL: 3,
                ResponseFormat.CONCISE: 2,
                ResponseFormat.VOICE_OPTIMIZED: 1
            }
            
            target_format = max(response_formats, key=lambda f: format_priority.get(f, 0))
            target_prompt = next(prompt for prompt, _ in responses if prompt.response_format == target_format)
            
            max_tokens = target_prompt.get_max_tokens()
            style_guidance = target_prompt.get_style_guidance()
            
            synthesis_prompt = f"""
You are synthesizing multiple responses into one coherent response.

RESPONSE OBJECTIVE: {response_objective if response_objective else 'Provide a helpful and engaging response'}
TARGET FORMAT: {target_format.value}
LENGTH GUIDANCE: {style_guidance}

ORIGINAL USER MESSAGE: {original_message}

CONTEXT: {context if context else 'No additional context'}

RESPONSES TO SYNTHESIZE:
"""
            
            for i, (prompt, response) in enumerate(responses, 1):
                synthesis_prompt += f"""
Response {i} (Subject: {prompt.subject.value}, Tone: {prompt.tone.value}, Format: {prompt.response_format.value}):
{response}
"""
            
            synthesis_prompt += f"""
Create a single, coherent response that:
1. Addresses the original user message
2. Serves the response objective: {response_objective}
3. Incorporates insights from all responses naturally
4. Maintains a conversational, engaging tone
5. Flows logically from one point to the next
6. Feels like a single, unified response
7. {style_guidance}

SYNTHESIZED RESPONSE:
"""
            
            result = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": synthesis_prompt}],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            synthesized_response = result.choices[0].message.content.strip()
            return synthesized_response
            
        except Exception as e:
            logger.error(f"Error synthesizing responses: {e}")
            # Fallback: return the best individual response
            return self._get_best_response(responses, context, response_objective)
    
    def _get_best_response(self, 
                          responses: List[Tuple[ReqPrompt, str]], 
                          context: str,
                          response_objective: str = "") -> str:
        """Get the best individual response based on format priority."""
        
        # Use format priority to select the best response
        format_priority = {
            ResponseFormat.EXPANDED: 5,
            ResponseFormat.DETAILED: 4,
            ResponseFormat.CONVERSATIONAL: 3,
            ResponseFormat.CONCISE: 2,
            ResponseFormat.VOICE_OPTIMIZED: 1
        }
        
        best_response = None
        best_priority = 0
        
        for prompt, response in responses:
            priority = format_priority.get(prompt.response_format, 0)
            if priority > best_priority:
                best_priority = priority
                best_response = response
        
        return best_response or "I apologize, but I couldn't generate a satisfactory response."

class SynthesizerAgent:
    """Main synthesizer agent that orchestrates synthesis."""
    
    def __init__(self):
        self.synthesizer = ResponseSynthesizer()
    
    def synthesize_responses(self, 
                           responses: List[Tuple[ReqPrompt, str]], 
                           original_message: str,
                           context: str = "",
                           response_objective: str = "") -> Dict:
        """
        Synthesize multiple responses.
        
        Args:
            responses: List of (prompt, response) tuples
            original_message: Original user message
            context: RAG context used
            response_objective: The objective of the response
            
        Returns:
            Dict with final response and metadata
        """
        logger.info(f"Synthesizing {len(responses)} responses")
        logger.info(f"Response objective: {response_objective}")
        
        # Log response formats
        for i, (prompt, _) in enumerate(responses):
            logger.info(f"Response {i+1} format: {prompt.response_format.value}")
        
        # Synthesize responses
        final_response = self.synthesizer.synthesize_responses(
            responses,
            original_message,
            context,
            response_objective
        )
        
        return {
            "final_response": final_response,
            "response_count": len(responses),
            "synthesis_used": len(responses) > 1,
            "response_formats": [prompt.response_format.value for prompt, _ in responses]
        } 