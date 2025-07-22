"""
parser.py - Request parsing and classification

This module handles parsing user messages and classifying them into
appropriate categories for response generation using LLM-based parsing.
"""

import openai
import json
from typing import List, Dict, Any
from .enums import Subject, Format, Tone, OutputStyle, ReqPrompt, ParsedRequest

class RequestParser:
    """LLM-based parser for user requests and intent classification."""
    
    def __init__(self):
        """Initialize the request parser."""
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self, name="Stephen Saunders") -> str:
        """Get the system prompt for LLM-based parsing."""
        return f"""You are a discerning request parser for the digital twin of {name}. 
Your job is to analyze user messages and classify them into appropriate categories.
Your output will be used to generate rich, nuanced responses that address the user's request while souding and feeling like {name}.
If the user's request is not clear, you are encouraged to ask for clarification by returning an object with
- SUBJECT: GENERAL
- FORMAT: QUESTION
- TONE: PROFESSIONAL
- STYLE: CONCISE
- SCORE: Determine how confident you are in your classification
- FEEDBACK: Provide a brief explanation of your classificat
Alternatively, you can opt to move the conversation forwa
Audience: You may talking to potential clients, future employers, networking connections.
You may also be encountering family, friends, or community members.
You may speaking to lover, romantic interest, or spouse.
You may be speaking to my mother, children or in-la
Glean who are talking to you from the user's message. If not clear, be conservative and assume you are talking to a potential client or future employer.

Available Subjects (use EXACTLY these values):
- PERSONALITY: Questions about identity, character, traits
- PROJECTS: Questions about work, creations, builds
- VALUES: Questions about beliefs, principles, opinions
- TECHNICAL_SKILLS: Questions about technical abilities, problem-solving
- GENERAL: General conversation, casual chat
- EDUCATION: Questions about learning, knowledge, studies
- INTERESTS: Questions about hobbies, passions, likes
- PRODUCT_FEATURES: Questions about product capabilities
- BUSINESS_IDEAS: Questions about business concepts
- WORK_EXPERIENCE: Questions about professional background
- FAVORITES: Questions about preferences, favorites
- LIFESTYLE: Questions about daily life, habits
- FAMILY: Questions about family, relationships
- PARADIGMS: Questions about worldviews, frameworks
- RELATIONSHIPS: Questions about interpersonal connections
- ROMANCE: Questions about romantic relationships
- SPIRITUALITY: Questions about spiritual beliefs
- RELIGION: Questions about religious topics
- PHILOSOPHY: Questions about philosophical concepts
- ETHICS: Questions about moral principles
- POLITICS: Questions about political topics
- ECONOMICS: Questions about economic concepts
- ACTIVITIES: Questions about actions, activities
- WISDOM: Questions about insights, knowledge
- DREAMS: Questions about aspirations, goals
- MEMORIES: Questions about past experiences
- AFFIRMATIONS: Questions about positive statements
- GOALS: Questions about objectives, targets
- FEEDBACK: Questions about opinions, reviews

Available Formats (use EXACTLY these values):
- BACKGROUND: Providing context or background information
- PROBLEM_SOLVE: Solving a specific problem
- EXPLANATION: Explaining a concept or process
- ETHICAL_DILEMMA: Discussing moral choices
- VALUE_ASSESSMENT: Evaluating worth or importance
- PLANNING: Creating plans or strategies
- RESEARCH: Investigating or exploring topics
- REVIEW: Analyzing or evaluating something
- STORY: Telling a narrative or story
- QUESTION: Asking for information
- DATA: Providing data or statistics
- ANALOGY: Using comparisons or analogies
- METAPHOR: Using metaphorical language
- SYMBOLIC: Using symbolic representations

Available Tones (use EXACTLY these values):
- PROFESSIONAL: Formal, business-like
- POETIC: Artistic, expressive
- CASUAL: Informal, relaxed
- TECHNICAL: Precise, technical
- FORMAL: Structured, proper
- SHAMANIC_ESOTERIC: Mystical, spiritual
- PASSIONATE: Emotional, enthusiastic
- MATTER_OF_FACT: Direct, factual
- NOETIC: Intuitive, insightful
- HUMOROUS: Funny, entertaining
- WITTY: Clever, quick-witted
- CONTEMPLATIVE: Thoughtful, reflective

Available Output Styles (use EXACTLY these values):
- CONCISE: Brief, to the point
- STORYTELLING: Narrative, engaging
- DETAILED: Comprehensive, thorough
- BULLET_POINTS: Structured, listed
- THOUGHT_PROVOKING: Stimulating, challenging
- CONVERSATIONAL: Natural, chatty
- DEVOTIONAL: Inspirational, uplifting
- CODE: Technical, code-focused
- DATA: Analytical, data-driven

Analyze the user's message and return a JSON response with:
1. response_objective: A clear description of what the user wants
2. prompts: An array of ReqPrompt objects with:
   - subject: The most appropriate subject category
   - format: The most appropriate format type
   - tone: The most appropriate tone
   - style: The most appropriate output style
   - score: Confidence score (0.0 to 1.0)
   - feedback: Brief explanation of the classification

Return ONLY valid JSON, no other text."""

    def parse_request(self, message: str) -> ParsedRequest:
        """
        Parse user message using LLM to determine intent and create ReqPrompt objects.
        
        Args:
            message: User's input message
        
        Returns:
            ParsedRequest: Parsed request with prompts and objective
        """
        
        try:
            # Create the user prompt
            user_prompt = f"Parse this user message: '{message}'"
            
            # Call OpenAI API for parsing
            response = openai.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.1  # Low temperature for consistent parsing
            )
            
            # Extract the response content
            content = response.choices[0].message.content.strip()
            
            # Parse the JSON response
            try:
                parsed_data = json.loads(content)
                
                # Extract response objective
                response_objective = parsed_data.get("response_objective", "General conversation")
                
                # Parse prompts
                prompts = []
                for prompt_data in parsed_data.get("prompts", []):
                    try:
                        # Map common variations to correct enum values
                        subject = self._map_subject(prompt_data["subject"])
                        format_type = self._map_format(prompt_data["format"])
                        tone = self._map_tone(prompt_data["tone"])
                        style = self._map_style(prompt_data["style"])
                        
                        prompt = ReqPrompt(
                            subject=subject,
                            format=format_type,
                            tone=tone,
                            style=style,
                            score=float(prompt_data["score"]),
                            feedback=prompt_data["feedback"]
                        )
                        prompts.append(prompt)
                    except (KeyError, ValueError) as e:
                        print(f"⚠️ Error parsing prompt data: {e}")
                        continue
                
                # If no valid prompts, create a fallback
                if not prompts:
                    prompts = [self._create_fallback_prompt(message)]
                
                return ParsedRequest(response_objective=response_objective, prompts=prompts)
                
            except json.JSONDecodeError as e:
                print(f"⚠️ Error parsing JSON response: {e}")
                print(f"Raw response: {content}")
                return self._create_fallback_parsed_request(message)
                
        except Exception as e:
            print(f"❌ Error in LLM parsing: {str(e)}")
            return self._create_fallback_parsed_request(message)
    
    def _create_fallback_prompt(self, message: str) -> ReqPrompt:
        """Create a fallback prompt for general conversation, clarification, or engaging topics."""
        message_lower = message.lower()
        
        # Check if it's a question that needs clarification
        if "?" in message and len(message.strip()) < 20:
            # Short question - likely needs clarification
            subject = Subject.GENERAL
            format_type = Format.QUESTION
            tone = Tone.PROFESSIONAL
            style = OutputStyle.CONCISE
            feedback = "Short question detected - asking for clarification"
        elif any(word in message_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
            # Greeting - respond warmly
            subject = Subject.GENERAL
            format_type = Format.STORY
            tone = Tone.CASUAL
            style = OutputStyle.CONVERSATIONAL
            feedback = "Greeting detected - responding warmly"
        elif any(word in message_lower for word in ["how are you", "how's it going", "how do you do"]):
            # Well-being question
            subject = Subject.GENERAL
            format_type = Format.STORY
            tone = Tone.CASUAL
            style = OutputStyle.CONVERSATIONAL
            feedback = "Well-being question - sharing positive state"
        elif len(message.strip()) < 10:
            # Very short message - bring up something interesting
            subject = Subject.INTERESTS
            format_type = Format.STORY
            tone = Tone.CASUAL
            style = OutputStyle.STORYTELLING
            feedback = "Short message - sharing something interesting"
        else:
            # General conversation - ask for clarification or share something
            subject = Subject.GENERAL
            format_type = Format.QUESTION
            tone = Tone.PROFESSIONAL
            style = OutputStyle.CONCISE
            feedback = "Unclear request - asking for clarification"
        
        return ReqPrompt(
            subject=subject,
            format=format_type,
            tone=tone,
            style=style,
            score=0.3,  # Low confidence for fallback
            feedback=feedback
        )
    
    def _create_fallback_parsed_request(self, message: str) -> ParsedRequest:
        """Create a fallback parsed request when LLM parsing fails."""
        fallback_prompt = self._create_fallback_prompt(message)
        
        # Create appropriate response objective based on the fallback prompt
        if fallback_prompt.format == Format.QUESTION:
            response_objective = "Asking for clarification or more details about the user's request"
        elif fallback_prompt.subject == Subject.INTERESTS:
            response_objective = "Sharing something interesting to engage the user"
        elif "greeting" in fallback_prompt.feedback.lower():
            response_objective = "Responding warmly to the user's greeting"
        elif "well-being" in fallback_prompt.feedback.lower():
            response_objective = "Sharing positive well-being and asking about the user"
        else:
            response_objective = "Engaging in general conversation and seeking clarification"
        
        return ParsedRequest(
            response_objective=response_objective,
            prompts=[fallback_prompt]
        )
    
    def _map_subject(self, subject_str: str) -> Subject:
        """Map subject string to Subject enum, handling common variations."""
        subject_str = subject_str.upper().strip()
        
        # Direct mapping
        try:
            return Subject(subject_str)
        except ValueError:
            pass
        
        # Common variations
        mapping = {
            "CAREER": Subject.WORK_EXPERIENCE,
            "WORK": Subject.PROJECTS,
            "TECH": Subject.TECHNICAL_SKILLS,
            "TECHNICAL": Subject.TECHNICAL_SKILLS,
            "SKILLS": Subject.TECHNICAL_SKILLS,
            "BELIEFS": Subject.VALUES,
            "OPINIONS": Subject.VALUES,
            "CHARACTER": Subject.PERSONALITY,
            "TRAITS": Subject.PERSONALITY,
            "IDENTITY": Subject.PERSONALITY,
            "HOBBIES": Subject.INTERESTS,
            "PASSIONS": Subject.INTERESTS,
            "PREFERENCES": Subject.FAVORITES,
            "LIKES": Subject.FAVORITES,
            "DAILY_LIFE": Subject.LIFESTYLE,
            "HABITS": Subject.LIFESTYLE,
            "FAMILY_MEMBERS": Subject.FAMILY,
            "RELATIVES": Subject.FAMILY,
            "WORLDVIEW": Subject.PARADIGMS,
            "FRAMEWORKS": Subject.PARADIGMS,
            "CONNECTIONS": Subject.RELATIONSHIPS,
            "FRIENDSHIPS": Subject.RELATIONSHIPS,
            "LOVE": Subject.ROMANCE,
            "DATING": Subject.ROMANCE,
            "SPIRITUAL": Subject.SPIRITUALITY,
            "RELIGIOUS": Subject.RELIGION,
            "PHILOSOPHICAL": Subject.PHILOSOPHY,
            "MORAL": Subject.ETHICS,
            "ETHICAL": Subject.ETHICS,
            "POLITICAL": Subject.POLITICS,
            "ECONOMIC": Subject.ECONOMICS,
            "ACTIONS": Subject.ACTIVITIES,
            "KNOWLEDGE": Subject.WISDOM,
            "INSIGHTS": Subject.WISDOM,
            "ASPIRATIONS": Subject.DREAMS,
            "OBJECTIVES": Subject.GOALS,
            "TARGETS": Subject.GOALS,
            "EXPERIENCES": Subject.MEMORIES,
            "PAST": Subject.MEMORIES,
            "POSITIVE": Subject.AFFIRMATIONS,
            "REVIEWS": Subject.FEEDBACK,
            "OPINIONS": Subject.FEEDBACK
        }
        
        return mapping.get(subject_str, Subject.GENERAL)
    
    def _map_format(self, format_str: str) -> Format:
        """Map format string to Format enum, handling common variations."""
        format_str = format_str.upper().strip()
        
        try:
            return Format(format_str)
        except ValueError:
            pass
        
        mapping = {
            "CONTEXT": Format.BACKGROUND,
            "PROBLEM_SOLVING": Format.PROBLEM_SOLVE,
            "EXPLAIN": Format.EXPLANATION,
            "DILEMMA": Format.ETHICAL_DILEMMA,
            "ASSESSMENT": Format.VALUE_ASSESSMENT,
            "STRATEGY": Format.PLANNING,
            "INVESTIGATION": Format.RESEARCH,
            "ANALYSIS": Format.REVIEW,
            "NARRATIVE": Format.STORY,
            "QUERY": Format.QUESTION,
            "STATISTICS": Format.DATA,
            "COMPARISON": Format.ANALOGY,
            "FIGURATIVE": Format.METAPHOR,
            "REPRESENTATION": Format.SYMBOLIC
        }
        
        return mapping.get(format_str, Format.BACKGROUND)
    
    def _map_tone(self, tone_str: str) -> Tone:
        """Map tone string to Tone enum, handling common variations."""
        tone_str = tone_str.upper().strip()
        
        try:
            return Tone(tone_str)
        except ValueError:
            pass
        
        mapping = {
            "BUSINESS": Tone.PROFESSIONAL,
            "ARTISTIC": Tone.POETIC,
            "INFORMAL": Tone.CASUAL,
            "PRECISE": Tone.TECHNICAL,
            "STRUCTURED": Tone.FORMAL,
            "MYSTICAL": Tone.SHAMANIC_ESOTERIC,
            "EMOTIONAL": Tone.PASSIONATE,
            "DIRECT": Tone.MATTER_OF_FACT,
            "INTUITIVE": Tone.NOETIC,
            "FUNNY": Tone.HUMOROUS,
            "CLEVER": Tone.WITTY,
            "THOUGHTFUL": Tone.CONTEMPLATIVE
        }
        
        return mapping.get(tone_str, Tone.PROFESSIONAL)
    
    def _map_style(self, style_str: str) -> OutputStyle:
        """Map style string to OutputStyle enum, handling common variations."""
        style_str = style_str.upper().strip()
        
        try:
            return OutputStyle(style_str)
        except ValueError:
            pass
        
        mapping = {
            "BRIEF": OutputStyle.CONCISE,
            "NARRATIVE": OutputStyle.STORYTELLING,
            "COMPREHENSIVE": OutputStyle.DETAILED,
            "LISTED": OutputStyle.BULLET_POINTS,
            "STIMULATING": OutputStyle.THOUGHT_PROVOKING,
            "NATURAL": OutputStyle.CONVERSATIONAL,
            "INSPIRATIONAL": OutputStyle.DEVOTIONAL,
            "TECHNICAL": OutputStyle.CODE,
            "ANALYTICAL": OutputStyle.DATA
        }
        
        return mapping.get(style_str, OutputStyle.CONCISE)
    
    def test_parser(self):
        """Test the LLM-based parser with sample messages."""
        test_messages = [
            "Tell me about your projects",
            "What's your personality like?",
            "How do you solve problems?",
            "What are your values?",
            "Can you explain machine learning in simple terms?",
            "What's your favorite color and why?",
            "I'm feeling lost in my career, can you help me think through this?"
        ]

        print("🧪 Testing LLM-based request parser...")
        for msg in test_messages:
            parsed_request = self.parse_request(msg)
            print(f"\nMessage: {msg}")
            print(f"Response Objective: {parsed_request.response_objective}")
            for prompt in parsed_request.prompts:
                print(f"  → {prompt}")

        print("\n✅ LLM-based request parser tested!") 