#!/usr/bin/env python3
"""
app.py - Gradio deployment entry point for Cypherpunk Companion

This file serves as the main entry point for Gradio Spaces deployment.
It initializes the Cypherpunk Companion interface and launches it.
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
    """Main application entry point for Gradio deployment."""
    print("⚡ Starting Cypherpunk Companion...")
    print("🔧 Initializing neural interface...")
    
    try:
        # Import core components
        from modules.core import ConversationOrchestrator
        from modules.cypherpunk_ui import CypherpunkInterface
        from modules.digi_core_integration import check_digi_core_health
        
        # Check Digi-Core health
        print("🧠 Checking Digi-Core integration...")
        digi_core_health = check_digi_core_health()
        if digi_core_health.get('status') == 'healthy':
            print("✅ Digi-Core integration ready - using as primary RAG backend")
            rag_backend = "digi-core"
        else:
            print(f"⚠️ Digi-Core not available: {digi_core_health.get('error', 'Unknown error')}")
            print("🔄 Falling back to auto-detected RAG backend")
            rag_backend = "auto"
        
        # Initialize the orchestrator
        print("🔄 Loading conversation orchestrator...")
        orchestrator = ConversationOrchestrator(
            model="gpt-4o-mini",
            rag_backend=rag_backend,
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
        
        print("🚀 Launching Cypherpunk Companion...")
        interface.launch(share=False, debug=False)  # No sharing for deployment
        
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