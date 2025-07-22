"""
parser.py - Request parsing and classification

This module handles parsing user messages and classifying them into
appropriate categories for response generation.
"""

from typing import List
from .enums import Subject, Format, Tone, OutputStyle, ReqPrompt, ParsedRequest

class RequestParser:
    """Parser for user requests and intent classification."""
    
    def __init__(self):
        """Initialize the request parser."""
        pass
    
    def parse_request(self, message: str) -> ParsedRequest:
        """
        Parse user message to determine intent and create ReqPrompt objects.
        
        Args:
            message: User's input message
        
        Returns:
            ParsedRequest: Parsed request with prompts and objective
        """
        
        # TODO: Replace with actual LLM-based parsing
        # For now, use simple keyword-based classification
        
        message_lower = message.lower()
        
        # Simple keyword classification
        if any(word in message_lower for word in ["project", "work", "build", "create"]):
            subject = Subject.PROJECTS
            format_type = Format.BACKGROUND
            feedback = "User is asking about projects or work."
            response_objective = "The user is asking about projects or work."
        elif any(word in message_lower for word in ["personality", "who are you", "describe yourself"]):
            subject = Subject.PERSONALITY
            format_type = Format.STORY
            feedback = "User is asking about personality or identity."
            response_objective = "The user is asking about personality or identity."
        elif any(word in message_lower for word in ["value", "believe", "think", "opinion"]):
            subject = Subject.VALUES
            format_type = Format.EXPLANATION
            feedback = "User is asking about values or beliefs."
            response_objective = "The user is asking about values or beliefs."
        elif any(word in message_lower for word in ["how", "explain", "what is", "technical"]):
            subject = Subject.TECHNICAL_SKILLS
            format_type = Format.EXPLANATION
            feedback = "User is asking for technical explanation."
            response_objective = "The user is asking for technical explanation."
        else:
            subject = Subject.GENERAL
            format_type = Format.BACKGROUND
            feedback = "General conversation detected."
            response_objective = "General conversation detected."
        
        # Determine tone and style based on message characteristics
        if "?" in message:
            tone = Tone.PROFESSIONAL
            style = OutputStyle.CONCISE
        else:
            tone = Tone.CASUAL
            style = OutputStyle.STORYTELLING
        
        # Create ReqPrompt object
        prompt = ReqPrompt(
            subject=subject,
            format=format_type,
            tone=tone,
            style=style,
            score=0.8,  # Placeholder confidence score
            feedback=feedback
        )

        return ParsedRequest(response_objective=response_objective, prompts=[prompt])
    
    def test_parser(self):
        """Test the parser with sample messages."""
        test_messages = [
            "Tell me about your projects",
            "What's your personality like?",
            "How do you solve problems?",
            "What are your values?"
        ]

        print("🧪 Testing request parser...")
        for msg in test_messages:
            parsed_request = self.parse_request(msg)
            print(f"\nMessage: {msg}")
            print(f"Response Objective: {parsed_request.response_objective}")
            for prompt in parsed_request.prompts:
                print(f"  → {prompt}")

        print("\n✅ Request parser tested!") 