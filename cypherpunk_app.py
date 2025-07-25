#!/usr/bin/env python3
"""
cypherpunk_app.py - Cypherpunk-themed conversation interface

This is a specialized entry point for the cypherpunk-themed interface
with simple conversation and debug mode capabilities.
"""

import os
import sys
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main application entry point with cypherpunk interface."""
    print("⚡ Starting Cypherpunk Companion...")
    print("🔧 Initializing neural interface...")
    
    try:
        # Import core components
        from modules.core import ConversationOrchestrator
        from modules.cypherpunk_ui import CypherpunkInterface
        
        # Initialize the orchestrator
        print("🔄 Loading conversation orchestrator...")
        orchestrator = ConversationOrchestrator(
            model="gpt-4o-mini",
            rag_backend="auto",
            enable_evaluation=True,
            enable_memory=True
        )
        
        # Initialize knowledge base
        print("📚 Loading knowledge matrix...")
        kb_initialized = orchestrator.initialize_knowledge_base()
        if not kb_initialized:
            print("⚠️ Knowledge base initialization had issues, but continuing...")
        
        # Create and launch cypherpunk interface
        print("🎯 Creating neural interface...")
        interface = CypherpunkInterface(orchestrator)
        
        print("🚀 Launching Cypherpunk Companion...")
        interface.launch(share=True, debug=True)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("🔧 Please ensure all dependencies are installed:")
        print("   pip install gradio openai python-dotenv")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        print("🔧 Please check your environment and try again")
        return 1

if __name__ == "__main__":
    main() 