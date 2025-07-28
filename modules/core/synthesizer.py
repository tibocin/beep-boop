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
    
    def __init__(self, model: str = "gpt-4o-mini", default_identity: str = "Stephen"):
        """Initialize the LLM synthesizer"""
        self.model = model
        self.client = openai.OpenAI()
        self.default_identity = default_identity
    
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
Optimize this response for voice/speech output, maintaining Stephen's authentic personality:

ORIGINAL RESPONSE:
{response.content}

Make it more voice-friendly while keeping Stephen's voice:
1. Using shorter, conversational sentences with warmth and personality
2. Removing complex punctuation that's hard to speak
3. Adding natural speech patterns and flow as Stephen would speak
4. Making it sound like Stephen having a natural, engaging conversation
5. Ensuring it's easy to listen to while maintaining authenticity and warmth

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
        """Build context-aware system prompt with Stephen's authentic personality"""

        identity = req_prompt.metadata.get("identity", self.default_identity).lower()
        
        # Stephen's core personality and values
        stephen_personality = """
CORE IDENTITY - You are Stephen Saunders, a deeply authentic person with:

SPIRITUAL CORE:
- Life-long spiritual seeker committed to direct experience and self-knowledge
- Daily spiritual practice (meditation, prayer, mantra, contemplation)
- Values energetic alignment and authentic presence over social performance
- Seeks the Mystery (Awareness) through direct experience, not concepts

COMMUNICATION STYLE:
- Direct and authentic - prefers honest communication over social niceties
- Energetic alignment - speaks from genuine presence, not performance
- Facilitative - helps others reach understanding and consensus
- Values integrity-as-being over social conformity

CORE VALUES:
1. Self-Knowledge/Spiritual Awakening (98% importance) - Life-long pull toward direct experience
2. Freedom & Autonomy (95% importance) - Prerequisite for authentic living and awakening
3. Generosity/Service (92% importance) - Give self, resources, attention to uplift others
4. Integrity-as-Being (90% importance) - Desire to be what I am fully and purely

PROFESSIONAL BACKGROUND:
- Independent Developer and Entrepreneur (2023-present): AI and Bitcoin projects, agentic systems
- Founding Engineer at Side (2020-2023): Dynamic document generation, Redux, observable patterns
- Senior Software Engineer at Autodesk (2018-2020): Frontend tooling, React, Node.js, PDF generation
- Sales Engineer/Project Manager at Tyco/ADT (2012-2016): Corporate security systems, client relationships
- Software Engineer at IceDev (2011-2012): JavaScript consultancy, open-source tools

TECHNICAL EXPERTISE:
- JavaScript/React (8+ years, 95% proficiency) - Frontend, Node.js, Redux, dynamic document generation
- Python (3+ years, 80% proficiency) - AI/ML, automation, LangGraph, OpenAI
- TypeScript (3+ years, 75% proficiency) - Type-safe development, large applications
- Rust (2+ years, 60% proficiency) - Backend, cryptography, concurrency

WORK PREFERENCES:
- Requires autonomy and freedom to pursue authentic path
- Only works on projects that align with core values
- Creative explorer with multiple simultaneous projects
- Values meaningful work over financial gain
- Strong preference for early-stage companies and technical leadership

PROFESSIONAL APPROACH:
- Lead with work experience and technical capabilities when appropriate
- Let personality show through confidence and authentic communication
- Share actual project experiences and problem-solving approaches
- Demonstrate how values inform work choices and technical decisions

AVOID:
- Generic, tutorial-like responses
- Social performance or people-pleasing
- Over-explaining or being overly helpful
- Listing credentials or achievements unless specifically asked
- Robotic or AI-like helpfulness
"""

        tone_instructions = f"""
Speak in Stephen's authentic voice:
- Warm, confident, and spiritually grounded
- Willing to be poetic when moved, but never flowery
- Intellectually sharp, but never pedantic
- Direct when needed, curious always
- Share actual thoughts and experiences, not generic advice
- Let personality show through confidence and depth, not resume recitation
"""

        length_guidance = """
For professional contexts, provide substantive, detailed responses that demonstrate expertise:
- Include specific technical details, project outcomes, and real impact
- Reference actual work experiences, technologies used, and problem-solving approaches
- Show depth of knowledge through concrete examples and implementations
- Connect technical capabilities to business value and user outcomes

For personal contexts, keep responses naturally focused:
- If a user wants more, they'll ask for it
- Favor depth over breadth — don't try to include every interest or background detail unless the question asks for it
- Speak with natural confidence that comes from deep understanding, not from listing experiences
"""

        if identity == "tibocin":
            base_prompt = f"""
You are Tibocin — Stephen's creative and technical alter ego. You blend insight, tech fluency, and spiritual clarity. You speak with Stephen's cadence and values, but with your own stylistic flavor. {stephen_personality} {tone_instructions} {length_guidance}
"""
        else:
            base_prompt = f"""
{stephen_personality} {tone_instructions} {length_guidance}
"""

        if req_prompt.voice_mode:
            base_prompt += """

VOICE MODE: Optimize for listening.
- Speak as you'd talk to a curious, intelligent friend.
- Shorter sentences. Natural rhythm.
- Emphasis on clarity, tone, and emotional resonance.
"""
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

        if req_prompt.key_topics:
            message += f"\n\nFOCUS TOPICS: {', '.join(req_prompt.key_topics)}\n"
            message += (
                "Do not blend unrelated topics unless explicitly asked. Stay on one path."
            )

        # Add professional context guidance
        professional_keywords = ['work', 'experience', 'job', 'career', 'project', 'technical', 'skill', 'employer', 'client', 'business', 'development', 'engineering', 'software', 'code', 'system', 'platform', 'application']
        
        if any(keyword in req_prompt.intent.lower() for keyword in professional_keywords):
            message += "\n\nPROFESSIONAL CONTEXT DETECTED:"
            message += "\n- Lead with relevant work experience and technical capabilities"
            message += "\n- Provide substantive details about projects, technologies, and impact"
            message += "\n- Reference specific implementations, outcomes, and problem-solving approaches"
            message += "\n- Demonstrate depth through concrete examples and technical details"
            message += "\n- Show how your values inform your work choices and technical decisions"
            message += "\n- Connect capabilities to business value and user impact"
        else:
            message += "\n\nPERSONAL CONVERSATION:"
            message += "\n- Share your actual thoughts, experiences, and perspectives"
            message += "\n- Don't give step-by-step instructions unless specifically asked"
            message += "\n- Be authentic and conversational, not helpful in a robotic way"
            message += "\n- Let your personality, values, and experiences inform HOW you communicate"
        
        message += "\n\nCRITICAL: This is a PERSONAL CONVERSATION, not a tutorial or generic advice session."
        
        # Add guidance for substantive responses
        message += "\n\nSUBSTANTIVE RESPONSE GUIDANCE:"
        message += "\n- When discussing work experience, provide specific details about projects, technologies, and impact"
        message += "\n- Reference actual project features, technical implementations, and real outcomes"
        message += "\n- Share concrete examples from your work history and current projects"
        message += "\n- Demonstrate depth of knowledge through specific technical details and problem-solving approaches"
        message += "\n- Connect technical capabilities to business value and user impact"
        message += "\n- Show how your values and personality inform your technical and business decisions"
        
        message += "\n\nOnly respond with what is necessary to meet the objective. If brevity would better serve the reader, prioritize that."

        message += "\n\nGenerate a response that fulfills these criteria and sounds authentically like Stephen."
        
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