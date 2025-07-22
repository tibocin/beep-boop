#!/usr/bin/env python3
"""
test_llm_parser.py - Test script for LLM-based parser

This script tests the refactored parser to ensure it works correctly
with LLM-based intent classification.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.parser import RequestParser

def test_llm_parser():
    """Test the LLM-based parser."""
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenAI API key in .env file")
        return
    
    print("🧪 Testing LLM-based parser...")
    
    # Initialize parser
    parser = RequestParser()
    
    # Test messages with varying complexity
    test_messages = [
        # Simple queries
        "Tell me about your projects",
        "What's your personality like?",
        "How do you solve problems?",
        "What are your values?",
        
        # More complex queries
        "Can you explain machine learning in simple terms?",
        "What's your favorite color and why?",
        "I'm feeling lost in my career, can you help me think through this?",
        
        # Technical queries
        "How would you approach building a recommendation system?",
        "What's the best way to learn Python?",
        
        # Personal/emotional queries
        "I'm struggling with motivation, any advice?",
        "What do you think about the meaning of life?",
        
        # Creative queries
        "Tell me a story about innovation",
        "What would you do if you had unlimited resources?"
    ]
    
    print(f"\n📝 Testing {len(test_messages)} messages...")
    
    for i, msg in enumerate(test_messages, 1):
        print(f"\n--- Test {i}: {msg} ---")
        try:
            parsed_request = parser.parse_request(msg)
            print(f"✅ Response Objective: {parsed_request.response_objective}")
            for j, prompt in enumerate(parsed_request.prompts, 1):
                print(f"  📋 Prompt {j}: {prompt}")
        except Exception as e:
            print(f"❌ Error parsing message: {str(e)}")
    
    print("\n🎉 LLM-based parser testing complete!")

if __name__ == "__main__":
    test_llm_parser() 