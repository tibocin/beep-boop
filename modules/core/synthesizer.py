"""
modules.core.synthesizer - Simplified response synthesizer with LLM reasoning

This module generates responses using LLM with context awareness, supporting
multiple response modes including voice-optimized output.

Key Features:
- Natural LLM generation over rigid templates
- Voice mode optimization
- Context-aware response generation
- Support for resume generation and deep explanations
"""

import openai
import json
from typing import List, Dict, Any
from .interfaces import (
    BaseSynthesizer, ReqPrompt, RAGContext, ResponseObjective, 
    CandidateResponse, RequestType
)

class LLMSynthesizer(BaseSynthesizer):
    """
    LLM-powered response synthesizer
    
    Focuses on natural language generation guided by LLM reasoning
    rather than complex template-based approaches.
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """Initialize the LLM synthesizer"""
        self.model = model
        self.client = openai.OpenAI()
    
    def generate(self, req_prompt: ReqPrompt, contexts: List[RAGContext], 
                objective: ResponseObjective) -> CandidateResponse:
        """
        Generate response using LLM with context awareness
        
        Args:
            req_prompt: Structured user request
            contexts: Relevant context information  
            objective: Response requirements and goals
            
        Returns:
            Generated response with metadata
        """
        try:
            # Build context-aware system prompt
            system_prompt = self._build_system_prompt(req_prompt, objective)
            
            # Prepare context information
            context_text = self._format_contexts(contexts)
            
            # Build user message
            user_message = self._build_user_message(req_prompt, context_text, objective)
            
            # Generate response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                functions=[self._get_generation_function()],
                function_call={"name": "generate_response"}
            )
            
            if response.choices[0].message.function_call:
                result_data = json.loads(response.choices[0].message.function_call.arguments)
                return self._create_candidate_response(result_data, req_prompt)
            else:
                # Fallback to direct response
                content = response.choices[0].message.content.strip()
                return self._create_fallback_response(content, req_prompt)
                
        except Exception as e:
            print(f"⚠️ LLM generation failed ({e}), using fallback")
            return self._create_error_response(str(e), req_prompt)
    
    def optimize_for_voice(self, response: CandidateResponse) -> CandidateResponse:
        """Optimize response for voice output"""
        if response.voice_friendly:
            return response  # Already optimized
        
        try:
            voice_prompt = f"""
Optimize this response for voice/speech output:

ORIGINAL RESPONSE:
{response.content}

Make it more voice-friendly by:
1. Using shorter, conversational sentences
2. Removing complex punctuation that's hard to speak
3. Adding natural speech patterns and flow
4. Making it sound more conversational and human
5. Ensuring it's easy to listen to and understand when spoken

VOICE-OPTIMIZED RESPONSE:
"""
            
            voice_response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": voice_prompt}],
                max_tokens=600,
                temperature=0.7
            )
            
            optimized_content = voice_response.choices[0].message.content.strip()
            
            # Create optimized response
            return CandidateResponse(
                content=optimized_content,
                confidence=response.confidence * 0.95,  # Slight confidence decrease for optimization
                reasoning=f"Voice-optimized version: {response.reasoning}",
                voice_friendly=True,
                estimated_tokens=self._estimate_tokens(optimized_content),
                generation_metadata={
                    **response.generation_metadata,
                    "voice_optimized": True,
                    "original_content": response.content
                }
            )
            
        except Exception as e:
            print(f"⚠️ Voice optimization failed ({e}), returning original")
            return response
    
    def _build_system_prompt(self, req_prompt: ReqPrompt, objective: ResponseObjective) -> str:
        """Build context-aware system prompt"""
        
        # Base prompt emphasizing LLM reasoning
        base_prompt = """You are an intelligent, conversational AI assistant focused on providing helpful, authentic responses.

Your responses should be:
- Natural and conversational
- Contextually appropriate  
- Helpful and informative
- Authentic to your knowledge and capabilities"""
        
        # Add voice mode considerations
        if req_prompt.voice_mode:
            base_prompt += """

VOICE MODE: This is a voice interaction. Make your response:
- Easy to speak and listen to
- Conversational and natural
- Free of complex formatting
- Appropriate for spoken conversation"""
        
        # Add request type specific guidance
        if req_prompt.request_type == RequestType.RESUME_GENERATION:
            base_prompt += """

RESUME FOCUS: Help with resume/CV creation by:
- Highlighting relevant experience and skills
- Using professional language and formatting  
- Focusing on achievements and impact
- Tailoring content to the user's background"""
            
        elif req_prompt.request_type == RequestType.EXPLANATION:
            base_prompt += """

EXPLANATION FOCUS: Provide clear explanations by:
- Breaking down complex concepts step by step
- Using examples and analogies when helpful
- Adjusting complexity to the audience
- Ensuring understanding over brevity"""
        
        # Add emotional tone guidance
        if req_prompt.emotional_tone:
            base_prompt += f"""

TONE: Adopt a {req_prompt.emotional_tone} tone in your response."""
        
        return base_prompt
    
    def _format_contexts(self, contexts: List[RAGContext]) -> str:
        """Format RAG contexts for inclusion in prompt"""
        if not contexts:
            return "No specific context available."
        
        formatted = "RELEVANT CONTEXT:\n"
        for i, context in enumerate(contexts, 1):
            formatted += f"\n{i}. {context.content}"
            if context.relevance_reasoning:
                formatted += f" (Relevant because: {context.relevance_reasoning})"
        
        return formatted
    
    def _build_user_message(self, req_prompt: ReqPrompt, context_text: str, 
                           objective: ResponseObjective) -> str:
        """Build the user message for LLM generation"""
        
        message = f"""
ORIGINAL REQUEST: {req_prompt.original_text}

USER INTENT: {req_prompt.intent}

{context_text}

RESPONSE OBJECTIVE: {objective.primary_goal}

SUCCESS CRITERIA:
{chr(10).join(f"- {criteria}" for criteria in objective.success_criteria)}

AUDIENCE: {objective.audience}
STYLE: {objective.style_preference}  
LENGTH: {objective.length_guidance}
"""
        
        if objective.voice_considerations:
            message += f"\nVOICE CONSIDERATIONS: {objective.voice_considerations}"
        
        message += "\n\nGenerate a response that meets these requirements."
        
        return message
    
    def _get_generation_function(self) -> Dict[str, Any]:
        """Define function schema for structured response generation"""
        return {
            "name": "generate_response",
            "description": "Generate a response with metadata",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The main response content"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Confidence in response quality (0.0 to 1.0)"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why this response was generated and how it meets the objective"
                    },
                    "voice_friendly": {
                        "type": "boolean",
                        "description": "Whether this response is optimized for voice output"
                    },
                    "key_topics_covered": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Main topics covered in the response"
                    }
                },
                "required": ["content", "confidence", "reasoning"]
            }
        }
    
    def _create_candidate_response(self, result_data: Dict[str, Any], 
                                  req_prompt: ReqPrompt) -> CandidateResponse:
        """Create CandidateResponse from LLM function call result"""
        
        content = result_data["content"]
        
        return CandidateResponse(
            content=content,
            confidence=result_data.get("confidence", 0.8),
            reasoning=result_data.get("reasoning", "Generated using LLM reasoning"),
            voice_friendly=result_data.get("voice_friendly", req_prompt.voice_mode),
            estimated_tokens=self._estimate_tokens(content),
            generation_metadata={
                "model": self.model,
                "request_type": req_prompt.request_type.value,
                "context_scope": req_prompt.context_scope.value,
                "key_topics": req_prompt.key_topics,
                "generated_topics": result_data.get("key_topics_covered", []),
                "voice_mode": req_prompt.voice_mode
            }
        )
    
    def _create_fallback_response(self, content: str, req_prompt: ReqPrompt) -> CandidateResponse:
        """Create response when function calling fails"""
        return CandidateResponse(
            content=content,
            confidence=0.7,  # Lower confidence for fallback
            reasoning="Generated using direct LLM response (function calling unavailable)",
            voice_friendly=req_prompt.voice_mode,
            estimated_tokens=self._estimate_tokens(content),
            generation_metadata={
                "model": self.model,
                "generation_method": "fallback",
                "voice_mode": req_prompt.voice_mode
            }
        )
    
    def _create_error_response(self, error_msg: str, req_prompt: ReqPrompt) -> CandidateResponse:
        """Create response when generation fails completely"""
        
        # Simple error handling based on request type
        if req_prompt.request_type == RequestType.RESUME_GENERATION:
            content = "I'd be happy to help with your resume. Could you tell me more about your background and the type of position you're targeting?"
        elif req_prompt.request_type == RequestType.EXPLANATION:
            content = "I'd like to help explain that for you. Could you provide a bit more detail about what specifically you'd like me to explain?"
        else:
            content = "I'm here to help! Could you tell me a bit more about what you're looking for?"
        
        return CandidateResponse(
            content=content,
            confidence=0.3,  # Low confidence for error response
            reasoning=f"Error fallback due to: {error_msg}",
            voice_friendly=req_prompt.voice_mode,
            estimated_tokens=self._estimate_tokens(content),
            generation_metadata={
                "generation_method": "error_fallback",
                "error": error_msg,
                "voice_mode": req_prompt.voice_mode
            }
        )
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 characters ≈ 1 token)"""
        return len(text) // 4