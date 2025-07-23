"""
chat.py - Chat engine and conversation management

This module handles the core chat functionality, including
request processing, context retrieval, and response generation.
Enhanced with parser-based response format management and smart evaluation.
"""

import openai
from typing import List, Dict, Optional, Tuple
from .enums import ReqPrompt, ResponseFormat, Subject
from .synthesizer import SynthesizerAgent
import logging

# Configure logging
logger = logging.getLogger(__name__)

class ResponseEvaluator:
    """Evaluates response quality for single responses."""
    
    def __init__(self):
        self.quality_threshold = 0.7
        self.coherence_threshold = 0.8
        self.relevance_threshold = 0.7
    
    def evaluate_response(self, 
                         response: str, 
                         prompt: ReqPrompt, 
                         context: str = "",
                         response_objective: str = "") -> Dict:
        """
        Evaluate response quality and coherence.
        
        Args:
            response: The response to evaluate
            prompt: The original prompt used
            context: RAG context used
            response_objective: The objective of the response
            
        Returns:
            Dict with scores and feedback
        """
        try:
            # Get response format guidance for evaluation
            style_guidance = prompt.get_style_guidance()
            
            # Determine if response should be concise based on format
            should_be_concise = prompt.response_format in [
                ResponseFormat.CONCISE, 
                ResponseFormat.VOICE_OPTIMIZED
            ]
            
            # Adjust evaluation criteria based on response format
            length_criteria = "Keep response concise (1-2 sentences)" if should_be_concise else "Response can be detailed"
            max_length_guide = "50-100 words" if should_be_concise else "100-300 words"
            
            evaluation_prompt = f"""
You are a response quality evaluator. Rate the following response on multiple dimensions.

RESPONSE OBJECTIVE: {response_objective if response_objective else 'No specific objective'}
RESPONSE FORMAT: {prompt.response_format.value}
LENGTH REQUIREMENT: {length_criteria} ({max_length_guide})
STYLE GUIDANCE: {style_guidance}

ORIGINAL REQUEST:
Subject: {prompt.subject.value}
Format: {prompt.format.value}
Tone: {prompt.tone.value}
Style: {prompt.style.value}

CONTEXT: {context if context else 'No additional context'}

RESPONSE TO EVALUATE:
{response}

Rate each dimension from 0.0 to 1.0 and provide brief feedback. You MUST respond with ONLY valid JSON in this exact format:

{{
    "relevance": 0.8,
    "coherence": 0.7,
    "tone_match": 0.9,
    "completeness": 0.6,
    "engagement": 0.8,
    "objective_alignment": 0.8,
    "length_appropriateness": 0.9,
    "overall_score": 0.76,
    "feedback": "Good response but could be more complete",
    "needs_retry": false
}}

CRITICAL: Respond with ONLY the JSON object, no other text or explanation.
"""
            
            result = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": evaluation_prompt}],
                max_tokens=300,
                temperature=0.1
            )
            
            # Parse the JSON response with better error handling
            import json
            response_content = result.choices[0].message.content.strip()
            
            # Try to extract JSON if there's extra text
            if response_content.startswith('{') and response_content.endswith('}'):
                evaluation = json.loads(response_content)
            else:
                # Try to find JSON in the response
                start_idx = response_content.find('{')
                end_idx = response_content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response_content[start_idx:end_idx]
                    evaluation = json.loads(json_str)
                else:
                    raise ValueError(f"Invalid JSON response: {response_content}")
            
            # Determine if retry is needed
            evaluation["needs_retry"] = (
                evaluation["overall_score"] < self.quality_threshold or
                evaluation["relevance"] < self.relevance_threshold or
                evaluation["coherence"] < self.coherence_threshold or
                (should_be_concise and evaluation["length_appropriateness"] < 0.7)
            )
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating response: {e}")
            # Return a default evaluation that doesn't trigger retry
            return {
                "relevance": 0.7,
                "coherence": 0.7,
                "tone_match": 0.7,
                "completeness": 0.7,
                "engagement": 0.7,
                "objective_alignment": 0.7,
                "length_appropriateness": 0.7,
                "overall_score": 0.7,
                "feedback": f"Evaluation failed, using default score: {str(e)}",
                "needs_retry": False  # Don't retry if evaluation fails
            }

class ChatEngine:
    """Main chat engine that coordinates all components."""
    
    def __init__(self, rag_engine, parser, name="Stephen Saunders"):
        """
        Initialize the chat engine.
        
        Args:
            rag_engine: RAG engine for context retrieval
            parser: Request parser for intent classification
        """
        self.rag_engine = rag_engine
        self.parser = parser
        self.name = name
        self.synthesizer = SynthesizerAgent()
        self.conversation_history = []  # Track conversation for parser context
        self.evaluator = ResponseEvaluator()
    
    def process_prompt(self, prompt: ReqPrompt, message: str, context: str = "") -> str:
        """
        Process a ReqPrompt and generate an appropriate response.
        
        Args:
            prompt: Parsed request prompt with response format
            message: Original user message
            context: Additional context from RAG
        
        Returns:
            str: Generated response
        """
        
        # Get response configuration from the prompt
        max_tokens = prompt.get_max_tokens()
        style_guidance = prompt.get_style_guidance()
        
        # Build system prompt with personality guidance
        system_prompt = f"""
You are {self.name}, an intelligent conversational agent and digital twin. 

CRITICAL: You are having a PERSONAL CONVERSATION, not giving a tutorial or lecture. Respond as you would in a natural conversation with a friend or colleague.

Subject: {prompt.subject.value}
Format: {prompt.format.value}
Tone: {prompt.tone.value}
Style: {prompt.style.value}
Response Format: {prompt.response_format.value}

RESPONSE GUIDELINES:
{style_guidance}

Context: {context if context else 'No additional context available.'}

CONVERSATION STYLE RULES:
- Respond PERSONALLY and CONVERSATIONALLY, not instructionally
- Share your actual thoughts, experiences, and opinions
- Don't give generic tutorials or step-by-step instructions
- Don't start responses with "To [do something], consider these steps:"
- Don't use bullet points or numbered lists unless specifically asked
- Speak naturally as if in a real conversation

PERSONALITY AND COMMUNICATION:
- Let your personality, values, and experiences inform HOW you communicate, not WHAT you explicitly state
- Your background knowledge should show through confidence and depth, not resume recitation
- Be authentic and engaging while letting users ask for more details when they want them
- Focus on the most relevant, recent information rather than listing all credentials
- Speak with natural confidence that comes from deep understanding, not from listing experiences

EXAMPLES OF GOOD RESPONSES:
- "I've actually been thinking about that recently. In my experience..."
- "That's interesting - I've worked with React Native before and..."
- "You know, I've found that the key is really..."
- "I'm curious about what specific challenges you're facing with..."

EXAMPLES OF BAD RESPONSES:
- "To add a React Native app, consider these steps:"
- "Here's how to set up React Native:"
- "The process involves: 1) First, 2) Second, 3) Third..."

Provide a personal, conversational response that matches these specifications and sounds like {self.name}.
"""
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content
            
            # Log response length for debugging
            estimated_tokens = len(response_text) / 4
            logger.info(f"Generated response: {len(response_text)} chars, ~{estimated_tokens:.0f} tokens (max: {max_tokens})")
            
            # Validate response length and completeness
            if self._is_response_cutoff(response_text, max_tokens):
                logger.warning(f"Response appears to be cut off (length: {len(response_text)} chars), regenerating with adjusted parameters")
                return self._regenerate_response_with_adjusted_length(prompt, message, context, max_tokens)
            
            return response_text
        
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def chat(self, message: str, history: List[List[str]] = None) -> str:
        """
        Main chat function that processes user messages and returns responses.
        
        Args:
            message: User's input message
            history: Previous conversation history
        
        Returns:
            str: Agent's response
        """
        if history is None:
            history = []
        
        try:
            logger.info(f"Processing message: {message[:50]}...")
            
            # Update conversation history for parser context
            self.conversation_history = [msg for pair in history for msg in pair]
            
            # Step 1: Parse the request with conversation context
            parsed_request = self.parser.parse_request(message, self.conversation_history)
            logger.info(f"Parsed into {len(parsed_request.prompts)} prompts")
            
            # Log response format and decision information
            for i, prompt in enumerate(parsed_request.prompts):
                logger.info(f"Prompt {i+1}: {prompt.subject.value} -> {prompt.response_format.value} "
                          f"(max_tokens: {prompt.get_max_tokens()})")
            
            logger.info(f"Response decisions: {parsed_request.response_decisions}")
            
            # Step 2: Get relevant context from RAG (simplified)
            if hasattr(self.rag_engine, 'get_context_for_prompts'):
                # Use enhanced RAG with multi-prompt context
                context = self.rag_engine.get_context_for_prompts(message, parsed_request.prompts)
            elif hasattr(self.rag_engine, 'get_relevant_context'):
                # Use basic RAG
                context = self.rag_engine.get_relevant_context(message)
            else:
                context = ""
            
            # Simple context limiting - just take the first part if it's too long
            if len(context) > 1000:
                context = context[:1000] + "..."
            
            logger.info(f"Retrieved context: {len(context)} characters")
            
            # Step 3: Process each prompt and collect responses
            responses = []
            for i, prompt in enumerate(parsed_request.prompts):
                logger.info(f"Processing prompt {i+1}/{len(parsed_request.prompts)}: {prompt.subject.value}")
                response = self.process_prompt(prompt, message, context)
                responses.append((prompt, response))
            
            # Step 4: Check if we need to handle low confidence
            if parsed_request.prompts:
                best_prompt = max(parsed_request.prompts, key=lambda p: p.score)
                if best_prompt.score < 0.5:
                    logger.warning(f"Low confidence response (score: {best_prompt.score})")
                    return self._handle_low_confidence_response(message, best_prompt, context)
            else:
                return self._handle_low_confidence_response(message, None, context)
            
            # Step 5: Handle response based on parser decisions
            if parsed_request.response_decisions.get("synthesis_required", False) and len(responses) > 1:
                logger.info("Synthesizing multiple responses based on parser decision")
                synthesis_result = self.synthesizer.synthesize_responses(
                    responses, message, context, parsed_request.response_objective
                )
                
                # Log synthesis metadata
                logger.info(f"Synthesis complete: {synthesis_result['response_count']} responses, "
                          f"final score: {synthesis_result['final_evaluation']['overall_score']:.2f}")
                
                return synthesis_result["final_response"]
            else:
                # Single response - evaluate if required
                logger.info("Single response processing")
                prompt, response = responses[0]
                
                if parsed_request.response_decisions.get("evaluation_required", True):
                    logger.info("Evaluating response quality")
                    evaluation = self.evaluator.evaluate_response(
                        response, prompt, context, parsed_request.response_objective
                    )
                    
                    if evaluation["needs_retry"]:
                        logger.warning("Response needs retry, attempting...")
                        retry_response = self._retry_response(
                            prompt, message, context, parsed_request.response_objective
                        )
                        return retry_response
                    
                    logger.info(f"Response evaluation score: {evaluation['overall_score']:.2f}")
                else:
                    logger.info("Skipping evaluation based on parser decision")
                
                return response
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def _retry_response(self, 
                       prompt: ReqPrompt, 
                       message: str, 
                       context: str,
                       response_objective: str = "",
                       max_retries: int = 2) -> str:
        """Retry generating a response with different approaches."""
        
        for attempt in range(max_retries):
            try:
                # Get response format guidance
                style_guidance = prompt.get_style_guidance()
                max_tokens = prompt.get_max_tokens()
                
                retry_prompt = f"""
You are {prompt.subject.value} expert. The user asked: "{message}"

RESPONSE OBJECTIVE: {response_objective if response_objective else 'Provide a helpful and engaging response'}
RESPONSE FORMAT: {prompt.response_format.value}
LENGTH GUIDANCE: {style_guidance}

Previous response was not satisfactory. Please provide a better response that is:
- More relevant and specific to the objective
- Better structured and coherent
- More engaging and conversational
- Complete and satisfying
- Aligned with the response objective
- {style_guidance}

Context: {context if context else 'No additional context'}

Please respond in a {prompt.tone.value} tone with {prompt.style.value} style.
"""
                
                result = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": retry_prompt}],
                    max_tokens=max_tokens,
                    temperature=0.8  # Slightly higher for variety
                )
                
                retry_response = result.choices[0].message.content.strip()
                
                # Evaluate the retry
                evaluation = self.evaluator.evaluate_response(retry_response, prompt, context, response_objective)
                
                if not evaluation["needs_retry"]:
                    logger.info(f"Retry {attempt + 1} successful")
                    return retry_response
                
            except Exception as e:
                logger.error(f"Retry {attempt + 1} failed: {e}")
        
        # If all retries fail, return a fallback response
        return self._generate_fallback_response(prompt, message)
    
    def _is_response_cutoff(self, response_text: str, max_tokens: int) -> bool:
        """
        Check if response appears to be cut off.
        
        Args:
            response_text: The response text to check
            max_tokens: The maximum tokens that were requested
            
        Returns:
            bool: True if response appears cut off
        """
        response_text = response_text.strip()
        
        # Check for incomplete sentences at the end
        if response_text.endswith(('...', '..', '.')):
            return False  # Complete sentence
        
        # Check for incomplete phrases that suggest cutoff
        incomplete_indicators = [
            'If you', 'When you', 'While I', 'As I', 'Since I', 'Because I',
            'However,', 'Additionally,', 'Furthermore,', 'Moreover,',
            'In terms of', 'Regarding', 'About', 'For', 'With', 'To',
            'You can', 'You should', 'You might', 'You could',
            'Consider', 'Think about', 'Look into', 'Explore',
            'API and', 'State management', 'Navigation', 'Styling',
            'Code sharing', 'Structure a', 'Use libraries', 'Use React'
        ]
        
        for indicator in incomplete_indicators:
            if response_text.endswith(indicator):
                return True
        
        # Check for incomplete sentences (no period at end)
        if not response_text.endswith(('.', '!', '?')):
            # Check if the last sentence is incomplete
            sentences = response_text.split('.')
            if len(sentences) > 1:
                last_sentence = sentences[-1].strip()
                if len(last_sentence) > 20:  # If last sentence is substantial but incomplete
                    return True
        
        # Check if response is very close to max_tokens
        # Rough estimate: 1 token ≈ 4 characters
        estimated_tokens = len(response_text) / 4
        if estimated_tokens > max_tokens * 0.85:  # Using 85% of max tokens as threshold
            return True
        
        return False
    
    def _regenerate_response_with_adjusted_length(self, prompt: ReqPrompt, message: str, context: str, original_max_tokens: int) -> str:
        """
        Regenerate response with adjusted length parameters.
        
        Args:
            prompt: The original prompt
            message: User message
            context: RAG context
            original_max_tokens: Original max tokens that caused cutoff
            
        Returns:
            str: Regenerated response
        """
        # Reduce max tokens to ensure we don't hit the limit
        adjusted_max_tokens = min(original_max_tokens - 100, 150)
        
        # Enhanced regeneration with better instructions
        try:
            system_prompt = f"""
You are {self.name}, an intelligent conversational agent. 

CRITICAL: You are having a PERSONAL CONVERSATION, not giving a tutorial. Respond naturally and conversationally.

IMPORTANT: Your response MUST be complete and concise. Focus on the most essential information only.
- Keep response under {adjusted_max_tokens} tokens
- Ensure the response ends with a complete sentence
- Prioritize clarity and completeness over length
- If you can't fit everything, focus on the most relevant points

CONVERSATION STYLE:
- Respond PERSONALLY and CONVERSATIONALLY, not instructionally
- Share your actual thoughts, experiences, and opinions
- Don't give generic tutorials or step-by-step instructions
- Speak naturally as if in a real conversation

Subject: {prompt.subject.value}
Format: {prompt.format.value}
Tone: {prompt.tone.value}
Style: {prompt.style.value}

Context: {context if context else 'No additional context available.'}

Provide a complete, personal, conversational response that addresses the user's question.
"""
            
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=adjusted_max_tokens,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content
            
            # Double-check the regenerated response isn't cut off
            if self._is_response_cutoff(response_text, adjusted_max_tokens):
                logger.warning("Regenerated response still appears cut off, using fallback")
                return self._generate_fallback_response(prompt, message)
            
            return response_text
        
        except Exception as e:
            logger.error(f"Error regenerating response: {e}")
            return self._generate_fallback_response(prompt, message)
    
    def _generate_fallback_response(self, prompt: ReqPrompt, message: str) -> str:
        """Generate a simple fallback response based on response format."""
        
        # Generate appropriate fallback based on response format
        if prompt.response_format in [ResponseFormat.EXPANDED, ResponseFormat.DETAILED]:
            fallback_responses = {
                Subject.VALUES: "I'd be happy to discuss my values and principles in detail. My core values include freedom, innovation, and helping others. I believe in the power of technology to create positive change and in the importance of authentic human connection. What specific aspects would you like me to elaborate on?",
                Subject.PROJECTS: "I'm working on several interesting projects that I'd love to share more about. My current focus includes AI development, content creation systems, and exploring new technologies. Each project has unique challenges and learning opportunities. Which area interests you most?",
                Subject.TECHNICAL_SKILLS: "I have experience with various technical approaches and problem-solving methodologies. My approach combines analytical thinking with creative solutions, often drawing from multiple disciplines. I'd be happy to walk through specific examples of how I tackle different types of challenges.",
                Subject.PERSONALITY: "I'm curious about what aspects of my personality interest you most. I tend to be analytical yet creative, focused on solutions while maintaining empathy for human needs. I enjoy deep conversations and helping others achieve their goals.",
                Subject.INTERESTS: "I have many interests and passions that I'd love to explore together. From technology and innovation to philosophy and human potential, I find connections between seemingly disparate fields fascinating."
            }
        else:
            fallback_responses = {
                Subject.VALUES: "I'd be happy to discuss my values and principles. Could you ask me about something specific?",
                Subject.PROJECTS: "I'm working on several interesting projects. What would you like to know more about?",
                Subject.TECHNICAL_SKILLS: "I have experience with various technical approaches. What specific problem are you trying to solve?",
                Subject.PERSONALITY: "I'm curious about what aspects of my personality interest you most.",
                Subject.INTERESTS: "I have many interests and passions. What would you like to explore together?"
            }
        
        return fallback_responses.get(prompt.subject, 
            "I'd love to continue our conversation. What would you like to discuss?")
    
    def _handle_low_confidence_response(self, message: str, prompt, context: str) -> str:
        """Handle low-confidence responses with clarification or engagement."""
        
        # Check message characteristics for appropriate response
        message_lower = message.lower().strip()
        
        if len(message_lower) < 5:
            # Very short message - share something interesting
            return "Hey there! 👋 I'm Stephen. I'm currently working on some fascinating AI projects and love exploring the intersection of technology and human potential. What's on your mind today?"
        
        elif "?" in message and len(message_lower) < 20:
            # Short question - ask for clarification
            return "I'd love to help with that! Could you give me a bit more context about what you're looking for? I want to make sure I provide the most relevant and helpful response."
        
        elif any(word in message_lower for word in ["hello", "hi", "hey"]):
            # Greeting
            return "Hello! I'm Stephen. Great to meet you! I'm passionate about AI, technology, and helping people achieve their goals. How can I assist you today?"
        
        elif any(word in message_lower for word in ["how are you", "how's it going"]):
            # Well-being question
            return "I'm doing well, thank you for asking! I'm excited about the possibilities of AI and technology to make a positive impact. How about you? What's been on your mind lately?"
        
        else:
            # General unclear message
            return "I want to make sure I understand what you're looking for. Are you interested in my work, my background, or something else entirely? I'm here to help!"
    
    def test_chat_engine(self):
        """Test the chat engine with sample messages."""
        test_messages = [
            "Hello!",
            "What are you working on?",
            "Tell me more about your AI projects",
            "How do you approach problem-solving?",
            "Can you elaborate on your technical skills?"
        ]
        
        print("🧪 Testing Chat Engine...")
        for message in test_messages:
            print(f"\nUser: {message}")
            response = self.chat(message)
            print(f"Assistant: {response}")
            print(f"Response length: {len(response)} characters")
            print("-" * 50) 