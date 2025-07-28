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
from .semantic_analyzer import SemanticAnalyzer, SemanticContext, IntentAnalysis

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
        self.semantic_analyzer = SemanticAnalyzer(model=model)
    
    def parse_request(self, text: str, voice_mode: bool = False) -> tuple[ReqPrompt, ResponseObjective]:
        """
        Parse user request using semantic analysis and LLM reasoning
        
        Args:
            text: User's natural language request
            voice_mode: Whether this is from voice interaction
            
        Returns:
            Tuple of (structured prompt, response objective)
        """
        try:
            # Step 1: Semantic analysis for robust context understanding
            semantic_context = self.semantic_analyzer.analyze_context(text)
            intent_analysis = self.semantic_analyzer.analyze_intent(text)
            
            # Step 2: Use semantic analysis to enhance LLM parsing
            enhanced_prompt = self._enhance_with_semantic_analysis(text, semantic_context, intent_analysis)
            
            # Step 3: LLM parsing with semantic context
            system_prompt = self._get_parsing_system_prompt(voice_mode)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enhanced_prompt}
                ],
                functions=[self._get_parse_function()],
                function_call={"name": "parse_user_request"}
            )
            
            function_call = response.choices[0].message.function_call
            if function_call and function_call.name == "parse_user_request":
                parsed_data = json.loads(function_call.arguments)
                
                # Enhance parsed data with semantic analysis
                enhanced_data = self._enhance_parsed_data(parsed_data, semantic_context, intent_analysis)
                
                return self._create_structured_objects(text, enhanced_data, voice_mode)
            else:
                # Fallback to semantic analysis only
                return self._fallback_with_semantic_analysis(text, voice_mode, semantic_context, intent_analysis)
                
        except Exception as e:
            print(f"Warning: Enhanced parsing failed ({e}), using semantic fallback")
            return self._fallback_with_semantic_analysis(text, voice_mode)
    
    def adapt_for_voice(self, req_prompt: ReqPrompt) -> ReqPrompt:
        """Adapt request for voice-friendly processing"""
        # Mark as voice mode and adjust for speech patterns
        req_prompt.voice_mode = True
        req_prompt.metadata["original_voice_mode"] = True
        
        # Voice mode tends to be more conversational and less formal
        if req_prompt.emotional_tone is None:
            req_prompt.emotional_tone = "conversational"
            
        return req_prompt
    
    def _enhance_with_semantic_analysis(self, text: str, semantic_context: SemanticContext, 
                                       intent_analysis: IntentAnalysis) -> str:
        """Enhance the user query with semantic analysis context"""
        enhanced = f"""
ORIGINAL QUERY: {text}

SEMANTIC ANALYSIS:
- Primary Context: {semantic_context.primary_context.value}
- Key Themes: {', '.join(semantic_context.key_themes)}
- Emotional Tone: {semantic_context.emotional_tone}
- Complexity Level: {semantic_context.complexity_level}
- Response Style: {semantic_context.response_style}

INTENT ANALYSIS:
- Primary Intent: {intent_analysis.primary_intent}
- Context Scope: {intent_analysis.context_scope}
- Audience Type: {intent_analysis.audience_type}
- Depth Preference: {intent_analysis.depth_preference}
- Confidence: {intent_analysis.confidence}

Please parse this query considering the semantic context and intent analysis above.
"""
        return enhanced
    
    def _enhance_parsed_data(self, parsed_data: Dict[str, Any], semantic_context: SemanticContext,
                            intent_analysis: IntentAnalysis) -> Dict[str, Any]:
        """Enhance parsed data with semantic analysis insights"""
        enhanced = parsed_data.copy()
        
        # Use semantic analysis to improve context scope detection
        if semantic_context.primary_context.value in ["professional", "technical"]:
            enhanced["context_scope"] = "professional"
        elif semantic_context.primary_context.value in ["personal", "spiritual"]:
            enhanced["context_scope"] = "personal"
        elif semantic_context.primary_context.value in ["creative", "entertainment"]:
            enhanced["context_scope"] = "creative"
        
        # Enhance key topics with semantic themes
        if semantic_context.key_themes:
            enhanced["key_topics"] = list(set(enhanced.get("key_topics", []) + semantic_context.key_themes))
        
        # Use semantic analysis for emotional tone
        if semantic_context.emotional_tone:
            enhanced["emotional_tone"] = semantic_context.emotional_tone
        
        return enhanced
    
    def _fallback_with_semantic_analysis(self, text: str, voice_mode: bool, 
                                        semantic_context: SemanticContext = None,
                                        intent_analysis: IntentAnalysis = None) -> tuple[ReqPrompt, ResponseObjective]:
        """Fallback parsing using semantic analysis when LLM fails"""
        
        # Get semantic analysis if not provided
        if semantic_context is None:
            semantic_context = self.semantic_analyzer.analyze_context(text)
        if intent_analysis is None:
            intent_analysis = self.semantic_analyzer.analyze_intent(text)
        
        # Create enhanced fallback using semantic analysis
        text_lower = text.lower()
        
        # Determine request type based on semantic context
        if semantic_context.primary_context.value == "professional":
            request_type = RequestType.CONVERSATION
            context_scope = ContextScope.PROFESSIONAL
        elif "resume" in text_lower or "cv" in text_lower:
            request_type = RequestType.RESUME_GENERATION
            context_scope = ContextScope.PROFESSIONAL
        elif "explain" in text_lower or "how" in text_lower:
            request_type = RequestType.EXPLANATION
            context_scope = ContextScope.GENERAL
        elif voice_mode:
            request_type = RequestType.VOICE_INTERACTION
            context_scope = ContextScope.GENERAL
        else:
            request_type = RequestType.CONVERSATION
            context_scope = ContextScope.GENERAL
        
        # Create ReqPrompt with semantic insights
        req_prompt = ReqPrompt(
            original_text=text,
            intent=intent_analysis.primary_intent,
            request_type=request_type,
            context_scope=context_scope,
            key_topics=semantic_context.key_themes,
            emotional_tone=semantic_context.emotional_tone,
            urgency_level=intent_analysis.urgency_level,
            voice_mode=voice_mode,
            metadata={
                "parsing_method": "semantic_fallback",
                "semantic_confidence": semantic_context.confidence,
                "intent_confidence": intent_analysis.confidence
            }
        )
        
        # Create ResponseObjective with semantic insights
        response_objective = ResponseObjective(
            primary_goal=intent_analysis.primary_intent,
            success_criteria=[
                f"Address the {semantic_context.primary_context.value} context appropriately",
                f"Use {semantic_context.response_style} response style",
                f"Match {semantic_context.emotional_tone} emotional tone",
                f"Provide {intent_analysis.depth_preference} level of detail"
            ],
            audience=intent_analysis.audience_type,
            style_preference=semantic_context.response_style,
            length_guidance=intent_analysis.depth_preference,
            voice_considerations="Optimize for voice output" if voice_mode else None
        )
        
        return req_prompt, response_objective
    
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
   - explanation: Explaining concepts, teaching, clarifying
   - voice_interaction: Voice-specific interactions
   - analysis: Analyzing data, situations, or problems
   - creative: Creative writing, brainstorming, artistic tasks

3. IDENTITY: Which identity should respond?
   - Stephen: Default identity for personal, professional, and general conversations
   - Tibocin: Use for creative, technical, or AI/agent-focused discussions
   
   Choose Tibocin if the user mentions AI, agents, creative work, or technical deep-dives.
   Default to Stephen for most other interactions.
   - explanation: Wanting to understand concepts, processes
   - voice_interaction: Spoken conversation (if voice_mode=True)
   - analysis: Deep analysis of topics, situations
   - creative: Creative writing, brainstorming, artistic work

3. CONTEXT SCOPE: What domain of knowledge is relevant?
   - personal: Personal traits, personality, private life
   - professional: Work experience, skills, career, projects, technical expertise
   - creative: Artistic projects, creative endeavors
   - general: Broad knowledge, general conversation
   - all: Multiple domains needed
   
   PROFESSIONAL CONTEXT INDICATORS:
   - Work, job, career, employment, experience
   - Technical skills, programming, development
   - Projects, achievements, responsibilities
   - Employer, client, business, company
   - Resume, CV, portfolio, background

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
                    "identity": {
                        "type": "string",
                        "enum": ["Stephen", "Tibocin"],
                        "description": "Which identity should respond: Stephen (default) or Tibocin (creative/technical agent)"
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
            metadata={
                "parsing_method": "llm", 
                "model": self.model,
                "identity": parsed_data.get("identity", "Stephen")
            }
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
        
        # Detect request type and context
        professional_keywords = ["work", "experience", "job", "career", "project", "technical", "skill", "employer", "client", "business", "company", "resume", "cv", "curriculum vitae"]
        
        if any(word in text_lower for word in ["resume", "cv", "curriculum vitae"]):
            request_type = RequestType.RESUME_GENERATION
            context_scope = ContextScope.PROFESSIONAL
        elif any(word in text_lower for word in professional_keywords):
            request_type = RequestType.CONVERSATION
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