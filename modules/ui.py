"""
ui.py - Gradio interface components

This module handles the Gradio web interface for the agentic companion.
"""

import gradio as gr
from typing import List

class GradioInterface:
    """Gradio interface for the agentic companion."""
    
    def __init__(self, chat_engine):
        """
        Initialize the Gradio interface.
        
        Args:
            chat_engine: Chat engine for processing messages
        """
        self.chat_engine = chat_engine
        self.ui = self._create_interface()
    
    def _create_interface(self):
        """Create and return the Gradio interface."""
        
        with gr.Blocks(title="🧠 Agentic Companion", theme=gr.themes.Soft()) as ui:
            gr.Markdown("""
            # 🧠 Agentic Companion
            
            Your intelligent conversational agent with RAG-powered knowledge and learning capabilities.
            """)
            
            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(
                        label="Conversation",
                        height=400,
                        show_label=True,
                    )
                    
                    with gr.Row():
                        msg = gr.Textbox(
                            label="Your message",
                            placeholder="Ask me anything...",
                            scale=4
                        )
                        submit_btn = gr.Button("Send", variant="primary", scale=1)
                    
                    clear_btn = gr.Button("Clear Conversation")
                
                with gr.Column(scale=1):
                    gr.Markdown("### Settings")
                    model_dropdown = gr.Dropdown(
                        choices=["gpt-4o", "gpt-4o-mini"],
                        value="gpt-4o",
                        label="Model"
                    )
                    
                    gr.Markdown("### Status")
                    status_text = gr.Textbox(
                        value="Ready",
                        label="Status",
                        interactive=False
                    )
            
            # Event handlers
            def respond(message, history, model):
                """Handle user message and return response."""
                if not message.strip():
                    return "", history
                
                response = self.chat_engine.chat(message, history)
                history.append([message, response])
                return "", history
            
            def clear_history():
                """Clear the conversation history."""
                return []
            
            # Connect events
            submit_btn.click(
                respond,
                inputs=[msg, chatbot, model_dropdown],
                outputs=[msg, chatbot]
            )
            
            msg.submit(
                respond,
                inputs=[msg, chatbot, model_dropdown],
                outputs=[msg, chatbot]
            )
            
            clear_btn.click(
                clear_history,
                outputs=[chatbot]
            )
        
        return ui
    
    def launch(self, share: bool = True, debug: bool = True):
        """Launch the Gradio interface."""
        print("🚀 Launching Agentic Companion...")
        print("\nThe interface will open in your browser.")
        print("You can interact with your agentic companion through the web interface!")
        
        self.ui.launch(share=share, debug=debug) 