"""
modules/cypherpunk_ui.py - Cypherpunk-themed conversation interface

This module provides a simple, terminal-inspired interface with cypherpunk aesthetics
and debug mode for viewing system processing logs.

Key Features:
- Simple text-based conversation interface
- Cypherpunk terminal aesthetic (black, orange, green, neon blue, hot pink)
- Debug mode with system processing logs
- Unicode symbols and cypherpunk styling
"""

import gradio as gr
import time
from typing import List, Dict, Any
from datetime import datetime

class CypherpunkInterface:
    """Cypherpunk-themed conversation interface with debug mode."""
    
    def __init__(self, orchestrator):
        """
        Initialize the cypherpunk interface.
        
        Args:
            orchestrator: ConversationOrchestrator instance
        """
        self.orchestrator = orchestrator
        self.debug_mode = False
        self.system_logs = []
        self.ui = self._create_interface()
    
    def _create_interface(self):
        """Create and return the cypherpunk-themed interface."""
        
        # Custom CSS for full black IDE theme with console formatting
        custom_css = """
        /* Global page styling - make everything black like IDE */
        body {
            background: #000000 !important;
            color: #00ff41 !important;
            font-family: 'Courier New', 'Monaco', 'Menlo', monospace !important;
        }
        
        /* Main Gradio container */
        #component-0 {
            background: #000000 !important;
            color: #00ff41 !important;
        }
        
        /* All Gradio containers */
        .gradio-container {
            background: #000000 !important;
            color: #00ff41 !important;
        }
        
        /* Main content area */
        .main {
            background: #000000 !important;
            color: #00ff41 !important;
        }
        
        /* Chat interface styling */
        .cypherpunk-container {
            background: #000000 !important;
            color: #00ff41 !important;
            font-family: 'Courier New', 'Monaco', 'Menlo', monospace !important;
            border: 2px solid #ff6b35 !important;
            border-radius: 8px !important;
            padding: 20px !important;
            margin: 10px !important;
        }
        
        /* Header styling */
        .cypherpunk-header {
            background: linear-gradient(90deg, #ff6b35, #f7931e) !important;
            color: #000000 !important;
            padding: 15px !important;
            border-radius: 5px !important;
            text-align: center !important;
            font-weight: bold !important;
            font-size: 1.2em !important;
            margin-bottom: 20px !important;
            text-shadow: 0 0 10px #ff6b35 !important;
        }
        
        /* Chat display area */
        .cypherpunk-chat {
            background: #000000 !important;
            border: 1px solid #00ff41 !important;
            border-radius: 5px !important;
            padding: 15px !important;
            margin: 10px 0 !important;
            max-height: 400px !important;
            overflow-y: auto !important;
            color: #00ff41 !important;
        }
        
        /* Input field styling */
        .cypherpunk-input {
            background: #1a1a1a !important;
            border: 2px solid #00ff41 !important;
            color: #00ff41 !important;
            border-radius: 5px !important;
            padding: 10px !important;
            font-family: 'Courier New', 'Monaco', 'Menlo', monospace !important;
        }
        
        .cypherpunk-input:focus {
            border-color: #ff6b35 !important;
            box-shadow: 0 0 10px #ff6b35 !important;
            background: #1a1a1a !important;
        }
        
        /* Button styling */
        .cypherpunk-button {
            background: linear-gradient(45deg, #ff6b35, #f7931e) !important;
            color: #000000 !important;
            border: none !important;
            border-radius: 5px !important;
            padding: 10px 20px !important;
            font-weight: bold !important;
            cursor: pointer !important;
            transition: all 0.3s ease !important;
            font-family: 'Courier New', 'Monaco', 'Menlo', monospace !important;
        }
        
        .cypherpunk-button:hover {
            background: linear-gradient(45deg, #f7931e, #ff6b35) !important;
            box-shadow: 0 0 15px #ff6b35 !important;
        }
        
        /* Console-style debug panel */
        .cypherpunk-debug {
            background: #000000 !important;
            border: 1px solid #ff0080 !important;
            border-radius: 5px !important;
            padding: 15px !important;
            margin: 10px 0 !important;
            max-height: 400px !important;
            overflow-y: auto !important;
            font-size: 0.85em !important;
            font-family: 'Courier New', 'Monaco', 'Menlo', monospace !important;
            color: #00ff41 !important;
            line-height: 1.4 !important;
        }
        
        /* Console log formatting */
        .console-log {
            color: #00ff41 !important;
            margin: 2px 0 !important;
            font-family: 'Courier New', 'Monaco', 'Menlo', monospace !important;
        }
        
        .console-error {
            color: #ff0080 !important;
        }
        
        .console-warning {
            color: #ff6b35 !important;
        }
        
        .console-info {
            color: #00bfff !important;
        }
        
        .console-success {
            color: #00ff41 !important;
        }
        
        /* JSON syntax highlighting in console */
        .json-key {
            color: #00bfff !important;
            font-weight: bold !important;
        }
        
        .json-string {
            color: #00ff41 !important;
        }
        
        .json-number {
            color: #ff6b35 !important;
        }
        
        .json-boolean {
            color: #ff0080 !important;
        }
        
        .json-null {
            color: #888888 !important;
        }
        
        /* Toggle button styling */
        .cypherpunk-toggle {
            background: linear-gradient(45deg, #ff0080, #00bfff) !important;
            color: #000000 !important;
            border: none !important;
            border-radius: 5px !important;
            padding: 8px 15px !important;
            font-weight: bold !important;
            cursor: pointer !important;
            margin: 5px !important;
            font-family: 'Courier New', 'Monaco', 'Menlo', monospace !important;
        }
        
        .cypherpunk-toggle:hover {
            box-shadow: 0 0 10px #ff0080 !important;
        }
        
        /* Override Gradio default styling */
        .gradio-container {
            background: #000000 !important;
        }
        
        .gradio-interface {
            background: #000000 !important;
        }
        
        /* Textbox overrides */
        textarea, input[type="text"] {
            background: #1a1a1a !important;
            color: #00ff41 !important;
            border: 1px solid #00ff41 !important;
            font-family: 'Courier New', 'Monaco', 'Menlo', monospace !important;
        }
        
        /* Chatbot overrides */
        .chatbot {
            background: #000000 !important;
            color: #00ff41 !important;
        }
        
        /* Row and column overrides */
        .row, .column {
            background: #000000 !important;
        }
        """
        
        # Create the interface using the same pattern as the working UI
        with gr.Blocks(title="⚡ Cypherpunk Companion", css=custom_css) as ui:
            
            # Header
            gr.HTML("""
            <div class="cypherpunk-header">
                ⚡ CYPHERPUNK COMPANION ⚡
                <br>
                <span style="font-size: 0.8em; color: #00ff41;">NEURAL INTERFACE v2.0</span>
            </div>
            """)
            
            with gr.Row():
                # Main conversation area
                with gr.Column(scale=2):
                    gr.HTML('<div class="cypherpunk-container">')
                    
                    # Chat display
                    chatbot = gr.Chatbot(
                        label="",
                        height=400,
                        show_label=False
                    )
                    
                    # Input area
                    with gr.Row():
                        msg = gr.Textbox(
                            label="",
                            placeholder="Enter your message, hacker...",
                            scale=4
                        )
                        submit_btn = gr.Button(
                            "⚡ SEND ⚡", 
                            variant="primary", 
                            scale=1
                        )
                    
                    # Control buttons
                    with gr.Row():
                        clear_btn = gr.Button("🗑️ CLEAR")
                        debug_toggle = gr.Button("🔧 DEBUG MODE")
                    
                    gr.HTML('</div>')
                
                # Debug panel
                with gr.Column(scale=1):
                    gr.HTML('<div class="cypherpunk-container">')
                    
                    gr.HTML("""
                    <div style="text-align: center; margin-bottom: 15px;">
                        <span style="color: #ff0080; font-weight: bold;">⚡ SYSTEM CONSOLE ⚡</span>
                    </div>
                    """)
                    
                    # Debug logs with console formatting
                    debug_logs = gr.Textbox(
                        label="",
                        value="System initialized...\nReady for neural interface...",
                        lines=20,
                        interactive=False
                    )
                    
                    # System info
                    status_text = gr.Textbox(
                        value="⚡ NEURAL LINK ACTIVE",
                        label="",
                        interactive=False
                    )
                    
                    gr.HTML('</div>')
            
            # Event handlers
            def respond(message, history, debug_logs):
                """Handle user message and return response with debug info."""
                if not message.strip():
                    return "", history, debug_logs
                
                # Add user message to debug
                timestamp = datetime.now().strftime("%H:%M:%S")
                new_logs = f"{debug_logs}\n[{timestamp}] 🧠 USER: {message}"
                
                try:
                    # Process message with orchestrator
                    new_logs += f"\n[{timestamp}] ⚡ PROCESSING: Parsing request..."
                    
                    response = self.orchestrator.process_message(message, voice_mode=False)
                    
                    new_logs += f"\n[{timestamp}] ✅ RESPONSE: Generated successfully"
                    
                    # Format metadata as pretty JSON for console
                    import json
                    metadata = response['metadata']
                    pretty_metadata = json.dumps(metadata, indent=2, sort_keys=True)
                    new_logs += f"\n[{timestamp}] 📊 METADATA:\n{pretty_metadata}"
                    
                    # Add response to history
                    history.append([message, response['content']])
                    
                    # Update debug logs
                    new_logs += f"\n[{timestamp}] 🎯 STATUS: Ready for next input"
                    
                except Exception as e:
                    error_msg = f"❌ ERROR: {str(e)}"
                    new_logs += f"\n[{timestamp}] {error_msg}"
                    history.append([message, f"System error: {str(e)}"])
                
                return "", history, new_logs
            
            def clear_history():
                """Clear the conversation history."""
                return [], "System cleared...\nReady for new session..."
            
            def toggle_debug():
                """Toggle debug mode."""
                self.debug_mode = not self.debug_mode
                status = "🔧 DEBUG MODE: ENABLED" if self.debug_mode else "🔧 DEBUG MODE: DISABLED"
                return status
            
            # Connect events
            submit_btn.click(
                respond,
                inputs=[msg, chatbot, debug_logs],
                outputs=[msg, chatbot, debug_logs]
            )
            
            msg.submit(
                respond,
                inputs=[msg, chatbot, debug_logs],
                outputs=[msg, chatbot, debug_logs]
            )
            
            clear_btn.click(
                clear_history,
                outputs=[chatbot, debug_logs]
            )
            
            debug_toggle.click(
                toggle_debug,
                outputs=[status_text]
            )
        
        return ui
    
    def launch(self, share: bool = True, debug: bool = True):
        """Launch the cypherpunk interface."""
        print("⚡ Launching Cypherpunk Companion...")
        print("🔧 Neural interface initializing...")
        print("🎯 Debug mode available")
        print("\nThe interface will open in your browser.")
        print("Welcome to the future, hacker...")
        
        self.ui.launch(share=share, debug=debug) 