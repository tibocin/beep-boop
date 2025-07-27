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
        
        /* Main blocks container */
        .main {
            background: #000000 !important;
        }
        
        /* All Gradio blocks */
        .blocks-container {
            background: #000000 !important;
        }
        
        /* Row and column overrides */
        .row, .column {
            background: #000000 !important;
        }
        
        /* Textbox overrides */
        textarea, input[type="text"] {
            background: #1a1a1a !important;
            color: #ffffff !important;
            border: 2px solid #ff0080 !important;
            font-family: 'Courier New', 'Monaco', 'Menlo', monospace !important;
            border-radius: 5px !important;
        }
        
        /* Chatbot overrides */
        .chatbot {
            background: #000000 !important;
            color: #ffffff !important;
            border: 2px solid #ff0080 !important;
            border-radius: 5px !important;
            padding: 10px !important;
            margin: 10px 0 !important;
        }
        
        /* Chatbot message styling */
        .chatbot .message {
            background: #1a1a1a !important;
            border: 1px solid #00ff41 !important;
            border-radius: 5px !important;
            margin: 5px 0 !important;
            padding: 10px !important;
        }
        
        /* User message styling */
        .chatbot .user-message {
            background: #1a1a1a !important;
            color: #ffffff !important;
            border-left: 3px solid #ff0080 !important;
        }
        
        /* Bot message styling */
        .chatbot .bot-message {
            background: #0a0a0a !important;
            color: #ffffff !important;
            border-left: 3px solid #00bfff !important;
            display: flex !important;
        }
        
        /* System console styling */
        .system-console {
            background: #000000 !important;
            border: 2px solid #ff0080 !important;
            border-radius: 5px !important;
            padding: 10px !important;
            margin: 10px 0 !important;
            color: #00ff41 !important;
        }
        
        /* Hide system console by default */
        .system-console {
            display: none !important;
        }
        
        /* Show system console when debug mode is enabled */
        .system-console.visible {
            display: block !important;
        }
        
        /* Remove any default Gradio borders */
        .gradio-container * {
            border-color: transparent !important;
        }
        
        /* Override any white backgrounds */
        .gradio-container, .gradio-container * {
            background: #000000 !important;
        }
        
        /* Specific overrides for common Gradio elements */
        .form, .form-container {
            background: #000000 !important;
        }
        
        /* Target specific Gradio components */
        .block {
            background: #000000 !important;
            border-color: #ff0080 !important;
        }
        
        /* Target all div elements within gradio container */
        .gradio-container div {
            background: #000000 !important;
        }
        
        /* Target specific component types */
        .row, .column {
            background: #000000 !important;
        }
        
        /* Override Gradio's CSS variables */
        :root {
            --background-fill-primary: #000000 !important;
            --background-fill-secondary: #000000 !important;
            --background-fill-tertiary: #000000 !important;
            --border-color-primary: #ff0080 !important;
            --border-color-secondary: #ff0080 !important;
            --text-color-primary: #ffffff !important;
            --text-color-secondary: #00ff41 !important;
        }
        
        /* Remove orange border rectangles */
        .gradio-container div[style*="border"] {
            border: none !important;
        }
        
        /* Override specific component backgrounds */
        .chatbot {
            background: #000000 !important;
        }
        
        .chatbot .message {
            background: #1a1a1a !important;
            border: 1px solid #ff0080 !important;
        }
        
        .chatbot .user-message {
            background: #1a1a1a !important;
            border-left: 3px solid #ff0080 !important;
        }
        
        .chatbot .bot-message {
            background: #0a0a0a !important;
            border-left: 3px solid #00bfff !important;
        }
        
        /* Button styling */
        .lg.secondary {
            background: #1a1a1a !important;
            color: #ffffff !important;
            border: 2px solid #ff0080 !important;
        }
        
        .lg.primary {
            background: linear-gradient(45deg, #ff6b35, #f7931e) !important;
            color: #000000 !important;
            border: none !important;
        }
        
        /* Textbox styling */
        textarea, input[type="text"] {
            background: #1a1a1a !important;
            color: #ffffff !important;
            border: 2px solid #ff0080 !important;
        }
        
        /* System console styling */
        .system-console {
            background: #000000 !important;
            border: 2px solid #ff0080 !important;
            display: block !important;
            color: #00ff41 !important;
        }
        
        .system-console.hidden {
            display: none !important;
        }
        
        .system-console.visible {
            display: block !important;
        }
        
        .system-console .block {
            background: #000000 !important;
            color: #00ff41 !important;
        }
        
        /* System console text elements */
        .system-console textarea {
            background: #000000 !important;
            color: #00ff41 !important;
            border: 1px solid #00ff41 !important;
        }
        
        .system-console * {
            color: #00ff41 !important;
        }
        
        /* Target specific HTML elements from the structure */
        .html-container {
            background: #000000 !important;
        }
        
        .prose {
            background: #000000 !important;
            color: #ffffff !important;
            border: none !important;
        }
        
        /* Override any remaining white backgrounds */
        .html-container,.prose {
            background: #000000 !important;
        }
        
        /* Remove the orange border rectangles */
        .wrap.center.full {
            display: none !important;
        }
        
        /* Ensure all text is white */
        .chatbot .md {
            color: #ffffff !important;
        }
        
        .chatbot .prose {
            color: #ffffff !important;
        }
        
        /* Target message content specifically */
        .message-content {
            background: #1a1a1a !important;
            color: #ffffff !important;
            display: flex !important;

        }
        
        .user .message-content {
            border-left: 3px solid #ff0080 !important;
        }
        
        .bot .message-content {
            border-left: 3px solid #00bfff !important;
        }
        
        /* Override any inline styles */
        [style*="background"] {
            background: #000000 !important;
        }
        
        /* Target the main container specifically */
        #component-0, #component-1, #component-2, #component-3, #component-4 {
            background: #000000 !important;
        }
        
        /* Remove any default borders */
        [style*="border"] {
            border-color: #ff0080 !important;
        }
        
        /* Input area styling */
        .input-area {
            display: flex !important;
            flex-direction: column !important;
            align-items: stretch !important;
            width: 100% !important;
        }
        
        .input-area .row {
            display: flex !important;
            align-items: center !important;
            width: 100% !important;
        }
        
        .input-area textarea {
            flex: 1 !important;
            width: 100% !important;
        }
        
        /* Chatbot area styling */
        .chatbot-area {
            background: #000000 !important;
            color: #ffffff !important;
            border: 2px solid #ff0080 !important;
            border-radius: 5px !important;
            padding: 10px !important;
            margin: 10px 0 !important;
            display: block !important;
        }
        
        .chatbot-area .message {
            background: transparent !important;
            border: none !important;
            color: #ffffff !important;
        }
        
        .chatbot-area .user .message {
            border-left: 3px solid #ff0080 !important;
            border-top: 3px solid #ff0080 !important;
            padding: 10px !important;
            margin: 5px 0 !important;
            border-radius: 5px !important;
        }
        
        .chatbot-area .bot .message {
            border-left: 3px solid #00bfff !important;
            border-top: 3px solid #00bfff !important;
            padding: 10px !important;
            margin: 5px 0 !important;
            border-radius: 5px !important;
        }
        
        .chatbot-area .message-content {
            background: transparent !important;
            border: none !important;
            color: #ffffff !important;
        }
        
        .chatbot-area .md, .chatbot-area .prose {
            color: #ffffff !important;
            background: transparent !important;
        }
        
        /* Force all text in chatbot to be white */
        .chatbot-area * {
            color: #ffffff !important;
        }
        
        .chatbot-area p, .chatbot-area span, .chatbot-area div {
            color: #ffffff !important;
        }
        
        /* Fix collapsed text boxes */
        .input-area textarea, .message-input textarea {
            flex: 1 !important;
            width: 100% !important;
            min-height: 40px !important;
            height: auto !important;
            resize: vertical !important;
            background: #1a1a1a !important;
            color: #ffffff !important;
            border: 2px solid #ff0080 !important;
            border-radius: 5px !important;
            padding: 10px !important;
        }
        
        /* Fix processing text colors */
        .processing-text {
            color: #00ff41 !important;
        }
        
        /* Ensure debug button works */
        .debug-toggle {
            cursor: pointer !important;
            background: #1a1a1a !important;
            color: #ffffff !important;
            border: 2px solid #00bfff !important;
        }
        
        /* Force all text elements to be white */
        .chatbot-area .message-content * {
            color: #ffffff !important;
        }
        
        .chatbot-area .md * {
            color: #ffffff !important;
        }
        
        /* Override any green text that should be white */
        .chatbot-area .text-green {
            color: #ffffff !important;
        }
        
        /* Ensure processing text is green */
        .processing-text, [class*="processing"] {
            color: #00ff41 !important;
        }
        """
        
        # Create the interface using the same pattern as the working UI
        with gr.Blocks(title="⚡ Cypherpunk Companion", css=custom_css) as ui:
            
            # Header
            gr.HTML("""
            <div class="cypherpunk-header">
                ⚡🤖 AGENT TIBOCIN 🤖⚡
                <br>
                <span style="font-size: 0.8em; color: #00ff41;">Interactive Knowledge Base v0.0.1ALPHA</span>
            </div>
            """)
            
            with gr.Row():
                # Main conversation area
                with gr.Column(scale=2):
                    
                    # Chat display
                    chatbot = gr.Chatbot(
                        label="INTERACTION LOG",
                        height=400,
                        show_label=True,
                        elem_classes=["chatbot-area"],
                        type="messages"
                    )
                    
                    # Input area
                    with gr.Row(elem_classes=["input-area"]):
                        msg = gr.Textbox(
                            label="",
                            placeholder="Enter your message...",
                            scale=4,
                            elem_classes=["message-input"]
                        )
                        submit_btn = gr.Button(
                            "⚡ SEND ⚡", 
                            variant="primary", 
                            scale=1
                        )
                    
                    # Control buttons
                    with gr.Row():
                        clear_btn = gr.Button("🗑️ CLEAR")
                        debug_toggle = gr.Button("🔧 DEBUG MODE", elem_classes=["debug-toggle"])
                
                # Debug panel
                with gr.Column(scale=1, elem_classes=["system-console"], visible=False) as debug_panel:
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
                    
                    # Add response to history (using new message format)
                    history.append({"role": "user", "content": message})
                    history.append({"role": "assistant", "content": response['content']})
                    
                    # Update debug logs
                    new_logs += f"\n[{timestamp}] 🎯 STATUS: Ready for next input"
                    
                except Exception as e:
                    error_msg = f"❌ ERROR: {str(e)}"
                    new_logs += f"\n[{timestamp}] {error_msg}"
                    history.append({"role": "user", "content": message})
                    history.append({"role": "assistant", "content": f"System error: {str(e)}"})
                
                return "", history, new_logs
            
            def clear_history():
                """Clear the conversation history."""
                return [], "System cleared...\nReady for new session..."
            
            def toggle_debug():
                """Toggle debug mode."""
                self.debug_mode = not self.debug_mode
                status = "🔧 DEBUG MODE: ENABLED" if self.debug_mode else "🔧 DEBUG MODE: DISABLED"
                
                print(f"Debug mode toggled: {self.debug_mode}")
                print(f"Status: {status}")
                
                # Return visibility state for the debug panel
                return gr.update(visible=self.debug_mode), status
            
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
                outputs=[debug_panel, status_text]
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