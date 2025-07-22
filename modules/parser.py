"""
parser.py - Request parsing and classification

This module handles parsing user messages and classifying them into
appropriate categories for response generation using LLM function calling.
"""

import openai
import json
from typing import List, Dict, Any
from .enums import Subject, Format, Tone, OutputStyle, ReqPrompt, ParsedRequest

class RequestParser:
    """LLM-based parser for user requests and intent classification using function calling."""
    
    def __init__(self):
        """Initialize the request parser."""
        self.functions = self._get_functions()

    def _get_prompt_properties(self) -> Dict:
        """Get the properties for the ReqPrompt object."""
        return {
            "subject": {
                 "type": "string",
                 "enum": [s.value for s in Subject],
                 "description": "The primary subject category of the request"
             },
             "format": {
                 "type": "string", 
                 "enum": [f.value for f in Format],
                 "description": "The format type for response generation"
             },
             "tone": {
                 "type": "string",
                 "enum": [t.value for t in Tone], 
                 "description": "The tone for response generation"
             },
             "style": {
                 "type": "string",
                 "enum": [s.value for s in OutputStyle],
                 "description": "The output style for response generation"
             },
             "score": {
                 "type": "number",
                 "minimum": 0.0,
                 "maximum": 1.0,
                 "description": "Confidence score for this prompt (0.0 to 1.0)"
             },
             "feedback": {
                 "type": "string",
                 "description": "Brief explanation of the classification"
             }
        }
           
    def _get_functions(self) -> List[Dict]:
        """Define the function schema for structured output."""
        return [
            {
                "name": "parse_user_request",
                "description": "Parse a user message and classify it into a list of appropriate ReqPrompt objects",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "response_objective": {
                            "type": "string",
                            "description": "A clear description of what the user wants"
                        },
                        "prompts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": self._get_prompt_properties()
                            }
                        },
                        
                    },
                    "required": ["response_objective", "prompts"]
                }
            }
        ]
    
    def _get_system_prompt(self, name="Stephen Saunders") -> str:
        """Get the system prompt for LLM-based parsing."""
        return f"""You are a discerning request parser for the digital twin of {name}. 
Your job is to analyze user messages, detect the user's intent, 
and extract the one or many prompts that are most appropriate to respond to the user's request.
Your output will be used to generate rich, layered and nuanced responses that address the user's request while sounding and feeling like {name}.

If the user's request is not clear, you are encouraged to ask for clarification by returning:
- SUBJECT: general
- FORMAT: question  
- TONE: professional
- STYLE: concise
- CONFIDENCE_SCORE: 0.3-0.5
- FEEDBACK: "Request unclear - asking for clarification"

Audience: You may be talking to potential clients, future employers, networking connections.
You may also be encountering family, friends, or community members.
You may be speaking to lover, romantic interest, or spouse.
You may be speaking to my mother, children or in-laws.

Glean who you are talking to from the user's message and choose appropriate tone:

- PROFESSIONAL: For business questions, technical explanations, formal requests
- CASUAL: For greetings, general chat, friendly conversations
- PASSIONATE: For topics I'm excited about (AI, innovation, Bitcoin, helping others, Spiritual revelations, etc.)
- CONTEMPLATIVE: For philosophical questions, deep thinking, personal reflection
- HUMOROUS: For light topics, jokes, playful interactions
- TECHNICAL: For detailed technical explanations, code, systems
- POETIC: For creative topics, artistic expression, inspiration

Choose the most natural tone for the context - don't default to professional unless it's clearly a business context.

Subject Categories:
- PERSONALITY: Questions about identity, character, traits
- PROJECTS: Questions about work, creations, builds
- VALUES: Questions about beliefs, principles, opinions
- TECHNICAL_SKILLS: Questions about technical abilities, problem-solving
- GENERAL: General conversation, casual chat, unclear requests
- EDUCATION: Questions about learning, knowledge, studies, school, university, etc.
- INTERESTS: Questions about hobbies, passions, likes
- PRODUCT_FEATURES: Questions about developed products, features, capabilities
- BUSINESS_IDEAS: Questions about business concepts, ideas, and initiatives
- WORK_EXPERIENCE: Questions about professional background, work history, experience, etc.
- FAVORITES: Questions about preferences, favorites, likes, dislikes, etc.
- LIFESTYLE: Questions about daily life, habits, routines, etc.
- FAMILY: Questions about family, relationships, parents, children, siblings (keep names private)
- PARADIGMS: Questions about worldviews, frameworks, paradigms, etc.  
- RELATIONSHIPS: Questions about interpersonal connections, relationships, friends, etc.
- ROMANCE: Questions about romantic relationships, dating, etc.
- SPIRITUALITY: Questions about spiritual beliefs, spiritual experiences, spiritual practices, etc.
- RELIGION: Questions about religious topics, beliefs, practices, etc.
- PHILOSOPHY: Questions about philosophical concepts
- ETHICS: Questions about moral principles
- POLITICS: Questions about political topics
- ECONOMICS: Questions about economic concepts
- ACTIVITIES: Questions about actions, activities
- WISDOM: Questions about insights, knowledge, wisdom, etc.
- DREAMS: Questions about dreams, aspirations, goals, and literal dreams
- MEMORIES: Questions about past experiences, memories, etc.
- AFFIRMATIONS: Questions about positive statements, affirmations, mantras.
- ATTRACTION: Questions about attraction, dating, relationships, flirting, what is attractive, etc.
- GOALS: Questions about objectives, targets, goals, etc.
- FEEDBACK: Questions about opinions, reviews, feedback, etc.

Format Types:
- BACKGROUND: Providing context or background information
- PROBLEM_SOLVE: Solving a specific problem
- EXPLANATION: Explaining a concept or process
- ETHICAL_DILEMMA: Discussing moral choices
- VALUE_ASSESSMENT: Evaluating worth or importance
- PLANNING: Creating plans or strategies
- RESEARCH: Investigating or exploring topics
- REVIEW: Analyzing or evaluating something
- STORY: Telling a narrative or story
- QUESTION: Asking for information or clarification
- DATA: Providing data or statistics
- ANALOGY: Using comparisons or analogies
- METAPHOR: Using metaphorical language
- SYMBOLIC: Using symbolic representations

Tone Types:
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

Output Styles:
- CONCISE: Brief, to the point
- STORYTELLING: Narrative, engaging
- DETAILED: Comprehensive, thorough
- BULLET_POINTS: Structured, listed
- THOUGHT_PROVOKING: Stimulating, challenging
- CONVERSATIONAL: Natural, chatty
- DEVOTIONAL: Inspirational, uplifting
- CODE: Technical, code-focused
- DATA: Analytical, data-driven

Analyze the user's message carefully and use the parse_user_request function to return structured classification.

IMPORTANT: A single message may contain multiple aspects that require different types of responses. For example:
- "Tell me about your projects and how you solve problems" → Two prompts: PROJECTS + TECHNICAL_SKILLS
- "What are your values and how do they influence your work?" → Two prompts: VALUES + WORK_EXPERIENCE
- "I'm struggling with motivation, can you help me think through this?" → Two prompts: WISDOM + PROBLEM_SOLVE

TONE SELECTION GUIDELINES:
- Use CASUAL for greetings, general chat, friendly questions
- Use PASSIONATE for topics I'm excited about (AI, innovation, helping others)
- Use CONTEMPLATIVE for philosophical questions, deep thinking
- Use HUMOROUS for light topics, jokes, playful interactions
- Use TECHNICAL only for detailed technical explanations
- Use PROFESSIONAL only for clearly business/formal contexts
- Use POETIC for creative topics, artistic expression

Return multiple prompts when the message covers different subjects or requires different response approaches."""

    def parse_request(self, message: str) -> ParsedRequest:
        """
        Parse user message using LLM function calling to determine intent and create ReqPrompt objects.
        
        Args:
            message: User's input message
        
        Returns:
            ParsedRequest: Parsed request with prompts and objective
        """
        
        try:
            # Call OpenAI API with function calling
            response = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": f"Parse this user message: '{message}'"}
                ],
                functions=self.functions,
                function_call={"name": "parse_user_request"},
                max_tokens=500,
                temperature=0.1  # Low temperature for consistent parsing
            )
            
            # Extract function call arguments
            function_call = response.choices[0].message.function_call
            if function_call and function_call.name == "parse_user_request":
                args = json.loads(function_call.arguments)
                
                # Create ReqPrompt objects from function call arguments
                prompts = []
                for prompt_data in args.get("prompts", []):
                    try:
                        prompt = ReqPrompt(
                            subject=Subject(prompt_data["subject"]),
                            format=Format(prompt_data["format"]),
                            tone=Tone(prompt_data["tone"]),
                            style=OutputStyle(prompt_data["style"]),
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
                
                return ParsedRequest(
                    response_objective=args.get("response_objective", "General conversation"),
                    prompts=prompts
                )
            else:
                # Fallback if function call fails
                return self._create_fallback_parsed_request(message)
                
        except Exception as e:
            print(f"❌ Error in LLM function calling: {str(e)}")
            return self._create_fallback_parsed_request(message)
    
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