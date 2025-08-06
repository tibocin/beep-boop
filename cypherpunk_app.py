#!/usr/bin/env python3
"""
cypherpunk_app.py - Cypherpunk-themed conversation interface

This is a specialized entry point for the cypherpunk-themed interface
with simple conversation and debug mode capabilities using async OpenAI SDK.
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
    """Main application entry point with cypherpunk interface."""
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
        
        # Initialize knowledge base with all available YAML files
        print("📚 Loading knowledge matrix...")
        
        # Discover all YAML files in the data directory
        yaml_files = []
        data_dir = "data"
        if os.path.exists(data_dir):
            for root, dirs, files in os.walk(data_dir):
                for file in files:
                    if file.endswith('.yaml') or file.endswith('.yml'):
                        yaml_files.append(os.path.join(root, file))
        
        print(f"📄 Found {len(yaml_files)} YAML files:")
        for yaml_file in yaml_files:
            print(f"   - {yaml_file}")
        
        kb_initialized = orchestrator.initialize_knowledge_base(yaml_files)
        if not kb_initialized:
            print("⚠️ Knowledge base initialization had issues, but continuing...")
        else:
            print("✅ Knowledge base loaded successfully!")
        
        # Create and launch cypherpunk interface
        print("🎯 Creating neural interface...")
        interface = CypherpunkInterface(orchestrator)
        
        print("🚀 Launching beep-boop...")
        interface.launch(share=True, debug=True)
        
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