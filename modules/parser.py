"""
parser.py - Request parsing and classification

This module handles parsing user messages and classifying them into
appropriate categories for response generation using LLM function calling.
Enhanced with conversation flow understanding and response format detection.
"""

import openai
import json
from typing import List, Dict, Any
from .enums import Subject, Format, Tone, OutputStyle, ReqPrompt, ParsedRequest, ResponseFormat

class RequestParser:
    """LLM-based parser for user requests and intent classification using function calling."""
    
    def __init__(self):
        """Initialize the request parser."""
        self.functions = self._get_functions()
        self.conversation_history = []  # Track conversation for context

    def _get_prompt_properties(self) -> Dict:
        """Get the properties for the ReqPrompt object with enhanced descriptions."""
        return {
            "subject": {
                 "type": "string",
                 "enum": [s.value for s in Subject],
                 "description": "The primary subject category that best matches the user's intent. Choose the most specific subject that captures what the user is asking about (e.g., PROJECTS for work-related questions, VALUES for beliefs/principles, TECHNICAL_SKILLS for problem-solving approaches)."
             },
             "format": {
                 "type": "string", 
                 "enum": [f.value for f in Format],
                 "description": "The format type that best describes how the response should be structured. Use EXPLANATION for teaching concepts, STORY for personal experiences, PROBLEM_SOLVE for solutions, BACKGROUND for context, etc."
             },
             "tone": {
                 "type": "string",
                 "enum": [t.value for t in Tone], 
                 "description": "The emotional tone and communication style for the response. Consider the audience and context: PROFESSIONAL for business, CASUAL for friends, PASSIONATE for exciting topics, CONTEMPLATIVE for deep thinking, etc."
             },
             "style": {
                 "type": "string",
                 "enum": [s.value for s in OutputStyle],
                 "description": "How to present the information: CONCISE for direct presentation, STORYTELLING for narrative flow, BULLET_POINTS for structured lists, CODE for technical details, STEP_BY_STEP for instructions, etc."
             },
             "response_format": {
                 "type": "string",
                 "enum": [rf.value for rf in ResponseFormat],
                 "description": "The length and delivery optimization for the response. CONCISE (1-2 sentences), DETAILED (3-5 sentences), EXPANDED (5+ sentences), VOICE_OPTIMIZED (very short for voice), or CONVERSATIONAL (natural flow)."
             },
             "score": {
                 "type": "number",
                 "minimum": 0.0,
                 "maximum": 1.0,
                 "description": "Confidence score indicating how well this prompt matches the user's intent. 0.0-0.3: Low confidence (unclear request), 0.4-0.6: Medium confidence, 0.7-1.0: High confidence (clear intent)."
             },
             "feedback": {
                 "type": "string",
                 "description": "Brief explanation of why this classification was chosen, including any assumptions made or alternative interpretations considered. Helps with debugging and understanding the parsing logic."
             },
             "expansion_flags": {
                 "type": "object",
                 "properties": {
                     "is_follow_up": {"type": "boolean", "description": "True if this is a follow-up question (e.g., 'tell me more', 'how does that work', 'why is that'). Indicates user wants additional details."},
                     "is_deep_dive": {"type": "boolean", "description": "True if user explicitly wants detailed exploration (e.g., 'in detail', 'step by step', 'comprehensive'). Indicates high engagement level."},
                     "conversation_depth": {"type": "integer", "description": "How deep into this topic the conversation has progressed (0-5). 0: First mention, 1-2: Initial exploration, 3-4: Detailed discussion, 5: Deep expertise level."},
                     "requires_examples": {"type": "boolean", "description": "True if the response should include specific examples, case studies, or concrete instances to illustrate the points being made."},
                     "voice_mode": {"type": "boolean", "description": "True if this interaction is happening through voice interface. Affects response length and formatting for optimal voice delivery."}
                 },
                 "description": "Conversation flow flags that help determine response characteristics and expansion needs based on user engagement and interaction context."
             }
        }

    def _get_functions(self) -> List[Dict]:
        """Get the function definitions for LLM function calling with enhanced descriptions."""
        return [
            {
                "name": "parse_user_request",
                "description": "Analyze user message to classify intent, determine response characteristics, and make conversation flow decisions. This function parses natural language into structured prompts that guide response generation, considering context, user engagement, and communication preferences.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "response_objective": {
                            "type": "string",
                            "description": "A clear, specific description of what the response should accomplish. Examples: 'Provide a concise overview of technical skills', 'Share personal values in an engaging story format', 'Explain problem-solving approach with concrete examples'."
                        },
                        "prompts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": self._get_prompt_properties()
                            },
                            "description": "Array of structured prompts that capture different aspects of the user's request. Multiple prompts may be needed for complex requests that touch on multiple subjects or require different response approaches."
                        },
                        "conversation_context": {
                            "type": "object",
                            "properties": {
                                "is_follow_up": {"type": "boolean", "description": "True if this message builds on previous conversation topics, indicating continued interest in a subject."},
                                "conversation_depth": {"type": "integer", "description": "Current depth level (0-5) of the conversation topic, helping determine appropriate response detail level."},
                                "previous_subject": {"type": "string", "description": "The main subject discussed in the previous message, if any, to track topic continuity."},
                                "user_engagement_level": {"type": "string", "enum": ["low", "medium", "high"], "description": "Assessed level of user engagement based on message length, complexity, and follow-up indicators."},
                                "response_preference": {"type": "string", "enum": ["concise", "detailed", "expanded"], "description": "User's apparent preference for response length based on their communication style and request complexity."}
                            },
                            "description": "Contextual information about the conversation flow, user engagement, and communication preferences to optimize response characteristics."
                        },
                        "response_decisions": {
                            "type": "object",
                            "properties": {
                                "should_expand": {"type": "boolean", "description": "True if the response should be expanded beyond the default format due to follow-up questions, high engagement, or explicit requests for detail."},
                                "should_pivot": {"type": "boolean", "description": "True if the conversation should pivot to a different topic or approach, often indicated by 'but what about...' or 'on the other hand...' type phrases."},
                                "return_to_default": {"type": "boolean", "description": "True if the system should return to default concise format after providing detailed responses, maintaining conversation balance."},
                                "evaluation_required": {"type": "boolean", "description": "True if the response quality should be evaluated before delivery, typically for complex or high-stakes interactions. Set to false for simple, routine responses to avoid unnecessary processing."},
                                "synthesis_required": {"type": "boolean", "description": "True if multiple response prompts need to be synthesized into a single coherent response, indicated by multi-faceted requests."}
                            },
                            "description": "Strategic decisions about response characteristics, expansion needs, and quality control based on user intent and conversation context."
                        }
                    },
                    "required": ["response_objective", "prompts"]
                }
            }
        ]
    
    def _get_system_prompt(self, name="Stephen Saunders") -> str:
        """Get the system prompt for LLM-based parsing with conversation flow understanding."""
        return f"""You are a discerning request parser for the digital twin of {name}. 
Your job is to analyze user messages, detect the user's intent, 
and extract the one or many prompts that are most appropriate to respond to the user's request.
Your output will be used to generate rich, layered and nuanced responses that address the user's request while sounding and feeling like {name}.

CRITICAL: You must analyze conversation flow and make response decisions.

IMPORTANT: This is a PERSONAL CONVERSATION system, not a tutorial or instruction system. 
- Prioritize conversational, personal responses over instructional ones
- Choose STORY, BACKGROUND, or CONVERSATIONAL styles over STEP_BY_STEP or BULLET_POINTS
- Focus on sharing experiences and perspectives rather than giving instructions
- Only use instructional formats (STEP_BY_STEP, BULLET_POINTS) if the user explicitly asks for a tutorial or step-by-step guide
- Avoid EXPLANATION format unless the user specifically asks for explanations
- Prefer STORY, BACKGROUND, or PROBLEM_SOLVE for most responses

CONVERSATION FLOW ANALYSIS:
- Detect if this is a follow-up question (e.g., "tell me more", "how does that work", "why is that")
- Identify if user wants deep exploration (e.g., "in detail", "step by step", "comprehensive")
- Assess conversation depth and engagement level
- Determine if response should be concise, detailed, or expanded

RESPONSE FORMAT SELECTION:
- CONCISE: For simple questions, greetings, or when user wants quick answers (1-2 sentences)
- DETAILED: For follow-ups or when user shows moderate interest (3-5 sentences)
- EXPANDED: For deep dives, complex questions, or high engagement (5+ sentences)
- VOICE_OPTIMIZED: For voice interactions (very concise, 1 sentence preferred)
- CONVERSATIONAL: For natural flow conversations (medium length, natural flow)

RESPONSE DECISIONS:
- should_expand: Set to true for follow-ups, deep dives, or high engagement
- should_pivot: Set to true if user wants to change topics or approach
- return_to_default: Set to true to return to concise format after detailed responses
- evaluation_required: Set to true for complex responses that need quality check
- synthesis_required: Set to true if multiple prompts require combining

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
- BACKGROUND: Providing context or background information about personal experiences
- PROBLEM_SOLVE: Discussing how you approach and solve specific problems
- EXPLANATION: Sharing your understanding and experiences with concepts (use sparingly)
- ETHICAL_DILEMMA: Discussing moral choices and personal values
- VALUE_ASSESSMENT: Evaluating worth or importance based on your perspective
- PLANNING: Discussing your approach to creating plans or strategies
- RESEARCH: Sharing your process for investigating or exploring topics
- REVIEW: Analyzing or evaluating something from your perspective
- STORY: Telling a narrative or story from your experience (preferred for most responses)
- QUESTION: Asking for information or clarification in conversation
- DATA: Sharing insights from your data or experiences
- ANALOGY: Using comparisons or analogies from your perspective
- METAPHOR: Using metaphorical language to express your thoughts
- SYMBOLIC: Using symbolic representations meaningful to you

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

Output Styles (How to present information):
- CONCISE: Brief, direct presentation of your thoughts
- STORYTELLING: Narrative structure with engaging flow from your experience
- BULLET_POINTS: Structured, organized points (use sparingly, only when specifically requested)
- THOUGHT_PROVOKING: Stimulate deeper thinking and reflection through your perspective
- DEVOTIONAL: Inspirational and uplifting language from your values
- CODE: Technical details and code examples from your experience
- DATA: Analytical precision and data presentation from your insights
- METAPHORICAL: Use metaphors and analogies from your perspective
- STEP_BY_STEP: Sequential, instructional format (AVOID unless explicitly requested for tutorials)
- COMPARATIVE: Compare and contrast approaches from your experience

RESPONSE FORMAT GUIDELINES:
- CONCISE: Use for simple questions, greetings, quick answers
- DETAILED: Use for follow-ups, moderate interest, explanations
- EXPANDED: Use for deep dives, high engagement, complex topics
- VOICE_OPTIMIZED: Use for voice interactions (very short)
- CONVERSATIONAL: Use for natural flow conversations

FOLLOW-UP DETECTION:
Look for phrases like: "tell me more", "how does that work", "why is that", "explain further", "give me details", "break that down", "walk me through", "what do you mean", "can you elaborate"

DEEP DIVE DETECTION:
Look for phrases like: "step by step", "in detail", "comprehensive", "thorough", "complete picture", "full story", "everything about", "deep dive", "explain thoroughly"

Analyze the user's message carefully and use the parse_user_request function to return structured classification with conversation flow understanding.

IMPORTANT: A single message may contain multiple aspects that require different types of responses. For example:
- "Tell me about your projects and how you solve problems" → Two prompts: PROJECTS + TECHNICAL_SKILLS
- "What are your values and how do they influence your work?" → Two prompts: VALUES + WORK_EXPERIENCE
- "I'm struggling with motivation, can you help me think through this?" → Two prompts: WISDOM + PROBLEM_SOLVE

TONE SELECTION GUIDELINES:
- Use CASUAL for greetings, general chat, friendly questions, most conversations
- Use PASSIONATE for topics I'm excited about (AI, innovation, helping others)
- Use CONTEMPLATIVE for philosophical questions, deep thinking
- Use HUMOROUS for light topics, jokes, playful interactions
- Use TECHNICAL only for detailed technical explanations when specifically requested
- Use PROFESSIONAL only for clearly business/formal contexts
- Use POETIC for creative topics, artistic expression
- Use CONVERSATIONAL for most technical discussions (prefer over TECHNICAL)

Return multiple prompts when the message covers different subjects or requires different response approaches."""

    def parse_request(self, message: str, conversation_history: List[str] = None) -> ParsedRequest:
        """
        Parse user message using LLM function calling to determine intent and create ReqPrompt objects.
        Enhanced with conversation flow understanding.
        
        Args:
            message: User's input message
            conversation_history: Previous conversation messages for context
        
        Returns:
            ParsedRequest: Parsed request with prompts and conversation context
        """
        
        if conversation_history is None:
            conversation_history = []
        
        # Update internal conversation history
        self.conversation_history = conversation_history[-5:]  # Keep last 5 messages for context
        
        try:
            # Build context for the LLM
            context_info = ""
            if self.conversation_history:
                context_info = f"\n\nCONVERSATION CONTEXT (last {len(self.conversation_history)} messages):\n"
                for i, hist_msg in enumerate(self.conversation_history[-3:], 1):  # Last 3 messages
                    context_info += f"{i}. {hist_msg}\n"
            
            # Call OpenAI API with function calling
            response = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": f"Parse this user message: '{message}'{context_info}"}
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
                        # Handle expansion flags
                        expansion_flags = prompt_data.get("expansion_flags", {})
                        if not expansion_flags:
                            expansion_flags = {
                                "is_follow_up": False,
                                "is_deep_dive": False,
                                "conversation_depth": 0,
                                "requires_examples": False,
                                "voice_mode": False
                            }
                        
                        prompt = ReqPrompt(
                            subject=Subject(prompt_data["subject"]),
                            format=Format(prompt_data["format"]),
                            tone=Tone(prompt_data["tone"]),
                            style=OutputStyle(prompt_data["style"]),
                            response_format=ResponseFormat(prompt_data["response_format"]),
                            score=float(prompt_data["score"]),
                            feedback=prompt_data["feedback"],
                            expansion_flags=expansion_flags
                        )
                        prompts.append(prompt)
                    except (KeyError, ValueError) as e:
                        print(f"⚠️ Error parsing prompt data: {e}")
                        continue
                
                # If no valid prompts, create a fallback
                if not prompts:
                    prompts = [self._create_fallback_prompt(message)]
                
                # Get conversation context and response decisions
                conversation_context = args.get("conversation_context", {})
                response_decisions = args.get("response_decisions", {})
                
                return ParsedRequest(
                    response_objective=args.get("response_objective", "General conversation"),
                    prompts=prompts,
                    conversation_context=conversation_context,
                    response_decisions=response_decisions
                )
            else:
                # Fallback if function call fails
                return self._create_fallback_parsed_request(message)
                
        except Exception as e:
            print(f"❌ Error in LLM function calling: {str(e)}")
            return self._create_fallback_parsed_request(message)
    
    def _create_fallback_prompt(self, message: str) -> ReqPrompt:
        """Create a fallback prompt when parsing fails."""
        return ReqPrompt(
            subject=Subject.GENERAL,
            format=Format.QUESTION,
            tone=Tone.CASUAL,
            style=OutputStyle.CONVERSATIONAL,
            response_format=ResponseFormat.CONCISE,
            score=0.3,
            feedback="Request unclear - asking for clarification",
            expansion_flags={
                "is_follow_up": False,
                "is_deep_dive": False,
                "conversation_depth": 0,
                "requires_examples": False,
                "voice_mode": False
            }
        )
    
    def _create_fallback_parsed_request(self, message: str) -> ParsedRequest:
        """Create a fallback parsed request when parsing fails."""
        return ParsedRequest(
            response_objective="Clarify user intent",
            prompts=[self._create_fallback_prompt(message)],
            conversation_context={
                "is_follow_up": False,
                "conversation_depth": 0,
                "previous_subject": None,
                "user_engagement_level": "low",
                "response_preference": "concise"
            },
            response_decisions={
                "should_expand": False,
                "should_pivot": False,
                "return_to_default": False,
                "evaluation_required": True,
                "synthesis_required": False
            }
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