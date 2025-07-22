"""
chat.py - Chat engine and conversation management

This module handles the core chat functionality, including
request processing, context retrieval, and response generation.
"""

import openai
from typing import List, Dict, Optional
from .enums import ReqPrompt

class ChatEngine:
    """Main chat engine that coordinates all components."""
    
    def __init__(self, rag_engine, parser):
        """
        Initialize the chat engine.
        
        Args:
            rag_engine: RAG engine for context retrieval
            parser: Request parser for intent classification
        """
        self.rag_engine = rag_engine
        self.parser = parser
    
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
You are an intelligent conversational agent. Respond to the user's message with the following characteristics:

Subject: {prompt.subject.value}
Format: {prompt.format.value}
Tone: {prompt.tone.value}
Style: {prompt.style.value}

Context: {context if context else 'No additional context available.'}

Provide a helpful, engaging response that matches these specifications.
"""
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
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
            # Step 1: Parse the request
            parsed_request = self.parser.parse_request(message)
            
            # Step 2: Get relevant context from RAG
            context = self.rag_engine.get_relevant_context(message)
            
            # Step 3: Process with the most confident prompt
            if parsed_request.prompts:
                best_prompt = max(parsed_request.prompts, key=lambda p: p.score)
                response = self.process_prompt(best_prompt, message, context)
            else:
                response = "I'm not sure how to respond to that. Could you rephrase?"
            
            return response
        
        except Exception as e:
            return f"I encountered an error: {str(e)}"
    
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