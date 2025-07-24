"""
modules.core.parser - Simplified request parser using LLM reasoning

This module converts natural language requests into structured prompts and objectives
by leveraging LLM understanding rather than rigid categorization rules.

Key Features:
- Intent-based parsing over category fitting
- Voice mode optimization
- Natural language objectives
- Flexible, conversational understanding
"""

import openai
import json
from typing import Dict, Any
from .interfaces import (
    BaseParser, ReqPrompt, ResponseObjective, RequestType, ContextScope
)

class LLMParser(BaseParser):
    """
    LLM-powered parser that understands user intent naturally
    
    Replaces complex enum-based categorization with flexible LLM reasoning
    to support voice mode, resume generation, and deep explanations.
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """Initialize the LLM parser"""
        self.model = model
        self.client = openai.OpenAI()
    
    def parse_request(self, text: str, voice_mode: bool = False) -> tuple[ReqPrompt, ResponseObjective]:
        """
        Parse user request using LLM reasoning for intent understanding
        
        Args:
            text: User's natural language request
            voice_mode: Whether this is from voice interaction
            
        Returns:
            Tuple of (structured prompt, response objective)
        """
        system_prompt = self._get_parsing_system_prompt(voice_mode)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                functions=[self._get_parse_function()],
                function_call={"name": "parse_user_request"}
            )
            
            function_call = response.choices[0].message.function_call
            if function_call and function_call.name == "parse_user_request":
                parsed_data = json.loads(function_call.arguments)
                return self._create_structured_objects(text, parsed_data, voice_mode)
            else:
                # Fallback to simple parsing
                return self._fallback_parse(text, voice_mode)
                
        except Exception as e:
            print(f"Warning: LLM parsing failed ({e}), using fallback")
            return self._fallback_parse(text, voice_mode)
    
    def adapt_for_voice(self, req_prompt: ReqPrompt) -> ReqPrompt:
        """Adapt request for voice-friendly processing"""
        # Mark as voice mode and adjust for speech patterns
        req_prompt.voice_mode = True
        req_prompt.metadata["original_voice_mode"] = True
        
        # Voice mode tends to be more conversational and less formal
        if req_prompt.emotional_tone is None:
            req_prompt.emotional_tone = "conversational"
            
        return req_prompt
    
    def _get_parsing_system_prompt(self, voice_mode: bool) -> str:
        """Get system prompt for LLM parsing"""
        voice_context = """
This is a VOICE interaction. Consider:
- Natural speech patterns and filler words
- Conversational tone and casual language
- Possible speech-to-text errors
- Need for voice-friendly responses
""" if voice_mode else ""
        
        return f"""You are an expert at understanding user intent from natural language.
{voice_context}

Your task is to parse the user's request and understand:

1. INTENT: What does the user actually want? (in natural language)
2. REQUEST TYPE: What kind of request is this?
   - conversation: General chat, questions, discussions
   - resume_generation: Creating/updating resumes, CV work
   - explanation: Wanting to understand concepts, processes
   - voice_interaction: Spoken conversation (if voice_mode=True)
   - analysis: Deep analysis of topics, situations
   - creative: Creative writing, brainstorming, artistic work

3. CONTEXT SCOPE: What domain of knowledge is relevant?
   - personal: Personal traits, personality, private life
   - professional: Work experience, skills, career
   - creative: Artistic projects, creative endeavors
   - general: Broad knowledge, general conversation
   - all: Multiple domains needed

4. KEY TOPICS: What are the main topics/themes?

5. EMOTIONAL TONE: What emotional tone is appropriate?
   - conversational, professional, enthusiastic, contemplative, etc.

6. RESPONSE OBJECTIVE: What would make this response successful?
   - What should the response achieve?
   - Who is the audience?
   - What style would work best?
   - Length guidance (brief, detailed, comprehensive)

Focus on understanding the user's true intent rather than fitting into rigid categories.
For voice mode, be especially attentive to conversational patterns and speech nuances."""

    def _get_parse_function(self) -> Dict[str, Any]:
        """Define the function schema for LLM parsing"""
        return {
            "name": "parse_user_request",
            "description": "Parse and understand user request intent",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "description": "Natural language description of what the user wants"
                    },
                    "request_type": {
                        "type": "string",
                        "enum": ["conversation", "resume_generation", "explanation", 
                                "voice_interaction", "analysis", "creative"],
                        "description": "Type of request"
                    },
                    "context_scope": {
                        "type": "string",
                        "enum": ["personal", "professional", "creative", "general", "all"],
                        "description": "Domain of knowledge needed"
                    },
                    "key_topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Main topics or themes in the request"
                    },
                    "emotional_tone": {
                        "type": "string",
                        "description": "Appropriate emotional tone for response"
                    },
                    "urgency_level": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                        "description": "How urgent or time-sensitive this request is"
                    },
                    "response_objective": {
                        "type": "object",
                        "properties": {
                            "primary_goal": {
                                "type": "string",
                                "description": "What the response should achieve"
                            },
                            "success_criteria": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "What would make this response successful"
                            },
                            "audience": {
                                "type": "string", 
                                "description": "Who this response is for"
                            },
                            "style_preference": {
                                "type": "string",
                                "description": "Communication style (conversational, formal, technical, etc.)"
                            },
                            "length_guidance": {
                                "type": "string",
                                "description": "How long the response should be (brief, detailed, comprehensive, etc.)"
                            },
                            "voice_considerations": {
                                "type": "string",
                                "description": "Special considerations for voice output (if applicable)"
                            }
                        },
                        "required": ["primary_goal", "success_criteria", "audience", "style_preference", "length_guidance"]
                    }
                },
                "required": ["intent", "request_type", "context_scope", "key_topics", "response_objective"]
            }
        }
    
    def _create_structured_objects(self, original_text: str, parsed_data: Dict[str, Any], 
                                  voice_mode: bool) -> tuple[ReqPrompt, ResponseObjective]:
        """Create structured objects from parsed LLM response"""
        
        # Create ReqPrompt
        req_prompt = ReqPrompt(
            original_text=original_text,
            intent=parsed_data["intent"],
            request_type=RequestType(parsed_data["request_type"]),
            context_scope=ContextScope(parsed_data["context_scope"]),
            key_topics=parsed_data["key_topics"],
            emotional_tone=parsed_data.get("emotional_tone"),
            urgency_level=parsed_data.get("urgency_level", "normal"),
            voice_mode=voice_mode,
            metadata={"parsing_method": "llm", "model": self.model}
        )
        
        # Create ResponseObjective
        objective_data = parsed_data["response_objective"]
        response_objective = ResponseObjective(
            primary_goal=objective_data["primary_goal"],
            success_criteria=objective_data["success_criteria"],
            audience=objective_data["audience"],
            style_preference=objective_data["style_preference"],
            length_guidance=objective_data["length_guidance"],
            voice_considerations=objective_data.get("voice_considerations")
        )
        
        return req_prompt, response_objective
    
    def _fallback_parse(self, text: str, voice_mode: bool) -> tuple[ReqPrompt, ResponseObjective]:
        """Simple fallback parsing when LLM fails"""
        
        # Simple heuristics for basic understanding
        text_lower = text.lower().strip()
        
        # Detect request type
        if any(word in text_lower for word in ["resume", "cv", "curriculum vitae"]):
            request_type = RequestType.RESUME_GENERATION
            context_scope = ContextScope.PROFESSIONAL
        elif any(word in text_lower for word in ["explain", "how does", "what is", "why"]):
            request_type = RequestType.EXPLANATION  
            context_scope = ContextScope.GENERAL
        elif voice_mode:
            request_type = RequestType.VOICE_INTERACTION
            context_scope = ContextScope.GENERAL
        else:
            request_type = RequestType.CONVERSATION
            context_scope = ContextScope.GENERAL
        
        # Create basic structures
        req_prompt = ReqPrompt(
            original_text=text,
            intent=f"User wants to {text_lower[:50]}..." if len(text) > 50 else text,
            request_type=request_type,
            context_scope=context_scope,
            key_topics=[],
            emotional_tone="conversational",
            urgency_level="normal",
            voice_mode=voice_mode,
            metadata={"parsing_method": "fallback"}
        )
        
        response_objective = ResponseObjective(
            primary_goal="Provide helpful response to user query",
            success_criteria=["Answer the user's question", "Be conversational and helpful"],
            audience="The user",
            style_preference="conversational",
            length_guidance="appropriate to question",
            voice_considerations="Keep response natural for speech" if voice_mode else None
        )
        
        return req_prompt, response_objective