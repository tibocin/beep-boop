#!/usr/bin/env python3
"""
app.py - Gradio deployment entry point for beep-boop

This file serves as the main entry point for Gradio Spaces deployment.
It initializes the beep-boop interface and launches it using async OpenAI SDK.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Main application entry point for Gradio deployment."""
    print("⚡ Starting beep-boop...")
    print("🔧 Initializing async OpenAI SDK interface...")
    
    try:
        # Import core components
        from modules.core import AsyncConversationOrchestrator
        from modules.cypherpunk_ui import CypherpunkInterface
        
        # Initialize the async orchestrator
        print("🔄 Loading async conversation orchestrator...")
        orchestrator = AsyncConversationOrchestrator(
            model="gpt-4o-mini",
            rag_backend="auto",
            enable_evaluation=True,
            enable_memory=True
        )
        
        # Initialize knowledge base (Digi-Core or YAML fallback)
        print("📚 Loading knowledge matrix...")
        
        kb_initialized = orchestrator.initialize_knowledge_base()
        if not kb_initialized:
            print("⚠️ Knowledge base initialization had issues, but continuing...")
        else:
            print("✅ Knowledge base loaded successfully!")
        
        # Create and launch cypherpunk interface
        print("🎯 Creating neural interface...")
        interface = CypherpunkInterface(orchestrator)
        
        print("🚀 Launching beep-boop...")
        interface.launch(share=False, debug=False)  # No sharing for deployment
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("🔧 Please ensure all dependencies are installed:")
        print("   pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        print("🔧 Please check your environment and try again")
        return 1

if __name__ == "__main__":
    asyncio.run(main()) 