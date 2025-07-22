#!/usr/bin/env python3
"""
app.py - Main application for the Agentic Companion

This is the main entry point that modularizes the notebook components
into a standalone application.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from modules.enums import Subject, Format, Tone, OutputStyle, ReqPrompt
from modules.chat import ChatEngine
from modules.parser import RequestParser
from modules.rag import create_rag_backend
from modules.ui import GradioInterface

def main():
    """Main application entry point."""
    print("🧠 Starting Agentic Companion...")
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenAI API key in .env file")
        return
    
    try:
        # Initialize components
        print("📦 Initializing components...")
        
        # Initialize RAG engine with adapter (auto-detects best backend)
        rag_engine = create_rag_backend(backend_type="auto")
        
        # If no advanced backend is available, use basic RAG
        if not rag_engine.backend:
            print("⚠️ No advanced RAG backend available, using basic RAG")
            from modules.rag import RAGEngine
            rag_engine = RAGEngine()
        
        # Initialize with YAML data if backend supports it
        if hasattr(rag_engine, 'initialize_from_yaml'):
            rag_engine.initialize_from_yaml()
        elif hasattr(rag_engine, 'backend') and hasattr(rag_engine.backend, 'initialize_from_yaml'):
            rag_engine.backend.initialize_from_yaml()
        
        # Initialize request parser
        parser = RequestParser()
        
        # Initialize chat engine
        chat_engine = ChatEngine(rag_engine, parser)
        
        # Initialize and launch Gradio interface
        print("🚀 Launching Gradio interface...")
        interface = GradioInterface(chat_engine)
        interface.launch()
        
    except Exception as e:
        print(f"❌ Error starting application: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 