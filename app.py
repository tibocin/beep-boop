#!/usr/bin/env python3
"""
app.py - Main application for the Agentic Companion

This is the main entry point that modularizes the notebook components
into a standalone application.
"""

import os
import sys
from dotenv import load_dotenv
import gradio as gr
from modules.rag import create_rag_backend
from modules.parser import RequestParser
from modules.chat import ChatEngine
import logging

# Load environment variables
load_dotenv()

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from modules.enums import Subject, Format, Tone, OutputStyle, ReqPrompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def discover_yaml_files(data_dir: str = "data") -> list:
    """
    Discover all YAML files in the data directory and subdirectories.
    
    Args:
        data_dir: Directory to search for YAML files
        
    Returns:
        list: List of full paths to YAML files found
    """
    yaml_files = []
    if os.path.exists(data_dir):
        for root, dirs, files in os.walk(data_dir):
            for file in files:
                if file.endswith('.yaml') or file.endswith('.yml'):
                    yaml_files.append(os.path.join(root, file))
    return yaml_files

def initialize_rag_with_yaml(rag_engine) -> bool:
    """
    Initialize RAG engine with all discovered YAML files.
    
    Args:
        rag_engine: The RAG engine to initialize
        
    Returns:
        bool: True if files were found and loaded, False otherwise
    """
    yaml_files = discover_yaml_files()
    
    if not yaml_files:
        print("⚠️ No YAML files found in data directory")
        return False
    
    print(f"📄 Found {len(yaml_files)} YAML files to load")
    
    # Try direct initialization first
    if hasattr(rag_engine, 'initialize_from_yaml'):
        rag_engine.initialize_from_yaml(yaml_files)
        return True
    # Try backend initialization
    elif hasattr(rag_engine, 'backend') and hasattr(rag_engine.backend, 'initialize_from_yaml'):
        rag_engine.backend.initialize_from_yaml(yaml_files)
        return True
    else:
        print("⚠️ RAG engine doesn't support YAML initialization")
        return False

def create_chat_interface():
    """Create and configure the chat interface."""
    try:
        # Initialize components
        print("🚀 Initializing RAG engine...")
        rag_engine = create_rag_backend(backend_type="auto")
        
        print("🧠 Initializing parser...")
        parser = RequestParser()
        
        print("💬 Initializing chat engine...")
        chat_engine = ChatEngine(rag_engine, parser)
        
        # Initialize RAG with YAML data
        initialize_rag_with_yaml(rag_engine)
        
        # Create Gradio interface
        with gr.Blocks(title="Agentic AI Companion") as demo:
            gr.Markdown("# 🤖 Agentic AI Companion")
            gr.Markdown("Chat with your personalized AI companion!")
            
            chatbot = gr.Chatbot(height=600)
            msg = gr.Textbox(label="Message", placeholder="Type your message here...")
            clear = gr.Button("Clear")
            
            def respond(message, history):
                response = chat_engine.chat(message, history)
                return "", history + [[message, response]]
            
            msg.submit(respond, [msg, chatbot], [msg, chatbot])
            clear.click(lambda: None, None, chatbot, queue=False)
        
        return demo
        
    except Exception as e:
        logger.error(f"Error creating chat interface: {e}")
        raise

if __name__ == "__main__":
    demo = create_chat_interface()
    demo.launch(share=False, debug=True) 