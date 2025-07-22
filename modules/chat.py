"""
chat.py - Chat engine and conversation management

This module handles the core chat functionality, including
request processing, context retrieval, and response generation.
"""

import openai
from typing import List, Dict, Optional, Tuple
from .enums import ReqPrompt
from .synthesizer import SynthesizerAgent
import logging

# Configure logging
logger = logging.getLogger(__name__)

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
    
    def process_prompt(self, prompt: ReqPrompt, message: str, context: str = "") -> str:
        """
        Process a ReqPrompt and generate an appropriate response.
        
        Args:
            prompt: Parsed request prompt
            message: Original user message
            context: Additional context from RAG
        
        Returns:
            str: Generated response
        """
        
        # Build system prompt based on ReqPrompt
        system_prompt = f"""
You are an aspect of {self.name}, an intelligent conversational agent and digital twin. 
Respond to the user's message with the following characteristics:

Subject: {prompt.subject.value}
Format: {prompt.format.value}
Tone: {prompt.tone.value}
Style: {prompt.style.value}

Context: {context if context else 'No additional context available.'}

IMPORTANT: If this is a fallback response (low confidence score), focus on:
- Casually asking for clarification if the request is unclear
- Sharing something interesting, noetic and thought-provoking about yourself or your interests
- Engaging in warm, professional conversation
- Nudge the conversation forward positively, but not obviously, more invitingly.

Provide a helpful, engaging response that matches these specifications and sounds like {self.name}.
"""
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        
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
            
            # Step 1: Parse the request
            parsed_request = self.parser.parse_request(message)
            logger.info(f"Parsed into {len(parsed_request.prompts)} prompts")
            
            # Step 2: Get relevant context from RAG
            if hasattr(self.rag_engine, 'get_context_for_prompts'):
                # Use enhanced RAG with multi-prompt context
                context = self.rag_engine.get_context_for_prompts(message, parsed_request.prompts)
            elif hasattr(self.rag_engine, 'get_relevant_context'):
                # Use basic RAG
                context = self.rag_engine.get_relevant_context(message)
            else:
                context = ""
            
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
            
            # Step 5: Synthesize responses using the synthesizer agent
            if len(responses) > 1:
                logger.info("Synthesizing multiple responses")
                synthesis_result = self.synthesizer.process_responses(
                    responses, message, context, parsed_request.response_objective
                )
                
                # Log synthesis metadata
                logger.info(f"Synthesis complete: {synthesis_result['response_count']} responses, "
                          f"final score: {synthesis_result['final_evaluation']['overall_score']:.2f}")
                
                return synthesis_result["final_response"]
            else:
                # Single response - just evaluate and return
                logger.info("Single response, evaluating quality")
                evaluation = self.synthesizer.evaluator.evaluate_response(
                    responses[0][1], responses[0][0], context, parsed_request.response_objective
                )
                
                if evaluation["needs_retry"]:
                    logger.warning("Response needs retry, attempting...")
                    retry_response = self.synthesizer.synthesizer._retry_response(
                        responses[0][0], message, context, parsed_request.response_objective
                    )
                    return retry_response
                
                return responses[0][1]
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
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
            "What are your values?",
            "Tell me about your projects",
            "How do you solve problems?"
        ]
        
        print("🧪 Testing chat engine...")
        for msg in test_messages:
            print(f"\n--- Testing: {msg} ---")
            response = self.chat(msg)
            print(f"Response: {response[:150]}...")
        
        print("\n✅ Chat engine tested!") 