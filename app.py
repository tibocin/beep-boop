#!/usr/bin/env python3
"""
app.py - Main application for the Simplified Agentic Companion

This is the main entry point using the simplified LLM-reasoning architecture
that emphasizes conversational flexibility, voice mode, and intelligent evaluation.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import simplified core components
from modules.core import ConversationOrchestrator

def main():
    """Main application entry point with simplified architecture."""
    print("🧠 Starting Simplified Agentic Companion...")
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenAI API key in .env file")
        return
    
    try:
        # Initialize the unified orchestrator
        print("🔄 Initializing simplified architecture...")
        orchestrator = ConversationOrchestrator(
            model="gpt-4o-mini",
            rag_backend="auto",
            enable_evaluation=True,
            enable_memory=True
        )
        
        # Initialize knowledge base from available YAML files
        print("📚 Initializing knowledge base...")
        kb_initialized = orchestrator.initialize_knowledge_base()
        if not kb_initialized:
            print("⚠️ Knowledge base initialization had issues, but continuing...")
        
        # Simple command-line interface for testing
        print("\n🚀 Simplified Agentic Companion ready!")
        print("💬 Type your message (or 'quit' to exit, 'voice:' prefix for voice mode):")
        print("📝 Use 'resume:' prefix for resume generation requests")
        print("=" * 60)
        
        while True:
            try:
                user_input = input("\n🤔 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Check for special prefixes
                voice_mode = False
                resume_mode = False
                
                if user_input.startswith("voice:"):
                    voice_mode = True
                    user_input = user_input[6:].strip()
                    print("🎤 Voice mode enabled")
                elif user_input.startswith("resume:"):
                    resume_mode = True
                    user_input = user_input[7:].strip()
                    print("📝 Resume generation mode")
                
                # Process the message
                if resume_mode:
                    response = orchestrator.process_resume_request(user_input, voice_mode)
                else:
                    response = orchestrator.process_message(user_input, voice_mode)
                
                # Display response
                print(f"\n🤖 Assistant: {response['content']}")
                
                # Display metadata if verbose
                metadata = response['metadata']
                print(f"\n📊 Metadata:")
                print(f"   Request Type: {metadata.get('request_type', 'unknown')}")
                print(f"   Intent: {metadata.get('intent', 'unknown')}")
                print(f"   Confidence: {metadata.get('confidence', 0):.2f}")
                print(f"   Voice Mode: {metadata.get('voice_mode', False)}")
                print(f"   Contexts Used: {metadata.get('contexts_used', 0)}")
                print(f"   Attempts: {metadata.get('attempts', 1)}")
                
                if metadata.get('evaluation'):
                    eval_info = metadata['evaluation']
                    print(f"   Evaluation Score: {eval_info.get('overall_score', 0):.2f}")
                    print(f"   Meets Objective: {eval_info.get('meets_objective', False)}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error processing message: {e}")
                import traceback
                traceback.print_exc()
        
        # Show final memory insights
        print("\n📈 Final Session Insights:")
        insights = orchestrator.get_memory_insights()
        if insights:
            for category, content in insights.items():
                if content:
                    print(f"   {category}: {str(content)[:100]}...")
        else:
            print("   No long-term insights extracted this session.")
        
        summary = orchestrator.get_conversation_summary()
        if summary:
            print(f"\n📝 Conversation Summary:\n   {summary[:200]}...")
        
    except Exception as e:
        print(f"❌ Error starting application: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 