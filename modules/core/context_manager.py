"""
modules.core.context_manager - Conversation history and memory management

This module manages conversation history with intelligent summarization and
supports sliding window with long-term memory integration.

Key Features:
- Sliding window conversation history
- LLM-powered intelligent summarization
- Long-term memory persistence
- Context-aware memory retrieval
- Voice mode conversation tracking
- Async LLM integration with UnifiedLLMClient
"""

import json
import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from .llm_client import UnifiedLLMClient
from .interfaces import BaseContextManager

class LLMContextManager(BaseContextManager):
    """
    LLM-powered context manager with intelligent summarization
    
    Manages conversation history using sliding windows with LLM-based
    summarization for efficient long-term memory.
    
    Now uses async UnifiedLLMClient for all LLM operations.
    """
    
    def __init__(self, 
                 sliding_window_size: int = 6,
                 summarize_threshold: int = 10,
                 memory_file: str = "./conversation_memory.json",
                 model: str = "gpt-4o-mini",
                 llm_client: Optional[UnifiedLLMClient] = None):
        """
        Initialize the context manager
        
        Args:
            sliding_window_size: Number of recent turns to keep in active memory
            summarize_threshold: Number of turns before triggering summarization
            memory_file: File to persist long-term memory
            model: LLM model for summarization
            llm_client: Optional UnifiedLLMClient instance (auto-created if None)
        """
        self.sliding_window_size = sliding_window_size
        self.summarize_threshold = summarize_threshold
        self.memory_file = memory_file
        self.model = model
        
        # Initialize UnifiedLLMClient if not provided
        if llm_client is None:
            self.client = UnifiedLLMClient(openai_model=model)
        else:
            self.client = llm_client
        
        # In-memory conversation state
        self.conversation_turns = []
        self.conversation_summary = ""
        self.long_term_memory = {}
        self.session_metadata = {}
        
        # Load existing memory
        self._load_memory()
    
    def get_conversation_context(self, turns_back: int = 6) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        # Use sliding window size if turns_back not specified
        if turns_back is None:
            turns_back = self.sliding_window_size
        
        # Return recent turns
        recent_turns = self.conversation_turns[-turns_back:] if self.conversation_turns else []
        
        # Add summary context if available
        context = []
        if self.conversation_summary and len(self.conversation_turns) > self.sliding_window_size:
            context.append({
                "type": "summary",
                "content": self.conversation_summary,
                "timestamp": datetime.now().isoformat(),
                "note": "Summary of earlier conversation"
            })
        
        # Add recent turns
        context.extend(recent_turns)
        
        return context
    
    def add_turn(self, user_input: str, assistant_response: str, metadata: Dict[str, Any]):
        """Add conversation turn to history"""
        
        turn = {
            "type": "conversation_turn",
            "user_input": user_input,
            "assistant_response": assistant_response,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata.copy() if metadata else {}
        }
        
        # Add to conversation history
        self.conversation_turns.append(turn)
        
        # Update session metadata
        self._update_session_metadata(turn)
        
        # Check if summarization is needed
        if len(self.conversation_turns) >= self.summarize_threshold:
            # Trigger async summarization (fire and forget)
            asyncio.create_task(self._trigger_summarization())
    
    async def summarize_history(self, keep_recent: int = 6) -> str:
        """Create intelligent summary of older conversation history (async)"""
        
        if len(self.conversation_turns) <= keep_recent:
            return "No history to summarize yet."
        
        # Get turns to summarize (exclude recent ones)
        turns_to_summarize = self.conversation_turns[:-keep_recent]
        
        if not turns_to_summarize:
            return self.conversation_summary or "No history to summarize."
        
        try:
            # Build summarization prompt
            summary_prompt = self._build_summarization_prompt(turns_to_summarize)
            
            # Get LLM summary using UnifiedLLMClient
            response = await self.client.chat_completion(
                messages=[{"role": "user", "content": summary_prompt}],
                model=self.model,
                max_tokens=500,
                temperature=0.3
            )
            
            # Extract text from response (handles both unified and OpenAI formats)
            new_summary = self._extract_response_text(response).strip()
            
            # Update conversation summary
            if self.conversation_summary:
                # Merge with existing summary
                merge_prompt = f"""
Merge these two conversation summaries into one coherent summary:

EXISTING SUMMARY:
{self.conversation_summary}

NEW SUMMARY:
{new_summary}

Create a comprehensive summary that captures the key themes, insights, and progression of the conversation.
"""
                merge_response = await self.client.chat_completion(
                    messages=[{"role": "user", "content": merge_prompt}],
                    model=self.model,
                    max_tokens=600,
                    temperature=0.3
                )
                self.conversation_summary = self._extract_response_text(merge_response).strip()
            else:
                self.conversation_summary = new_summary
            
            # Remove summarized turns (keep recent ones)
            self.conversation_turns = self.conversation_turns[-keep_recent:]
            
            return self.conversation_summary
            
        except Exception as e:
            print(f"⚠️ Summarization failed ({e}), keeping all turns")
            return self.conversation_summary or "Summarization failed."
    
    def get_long_term_memory(self) -> Dict[str, Any]:
        """Retrieve persistent user preferences and insights"""
        return self.long_term_memory.copy()
    
    def update_long_term_memory(self, key: str, value: Any):
        """Update long-term memory with new insights"""
        self.long_term_memory[key] = value
        self._save_memory()
    
    async def extract_insights(self) -> Dict[str, Any]:
        """Extract insights from recent conversation for long-term memory (async)"""
        
        if len(self.conversation_turns) < 3:
            return {}
        
        try:
            # Build insight extraction prompt
            recent_conversation = self._format_conversation_for_insights()
            
            insight_prompt = f"""
Analyze this conversation and extract key insights about the user:

{recent_conversation}

Extract insights in these categories:
1. PREFERENCES: User preferences, likes, dislikes
2. GOALS: User goals, aspirations, objectives
3. CONTEXT: Important context about user's situation
4. COMMUNICATION_STYLE: How the user prefers to communicate
5. TOPICS_OF_INTEREST: What the user is interested in discussing

Return as JSON with these keys. Only include insights that are clearly evident.
"""
            
            response = await self.client.chat_completion(
                messages=[{"role": "user", "content": insight_prompt}],
                model=self.model,
                max_tokens=400,
                temperature=0.3
            )
            
            insights_text = self._extract_response_text(response).strip()
            
            # Try to parse as JSON
            try:
                insights = json.loads(insights_text)
                
                # Update long-term memory with insights
                for category, content in insights.items():
                    if content:  # Only update if there's actual content
                        existing = self.long_term_memory.get(category, {})
                        if isinstance(existing, dict) and isinstance(content, dict):
                            existing.update(content)
                        else:
                            self.long_term_memory[category] = content
                
                self._save_memory()
                return insights
                
            except json.JSONDecodeError:
                print("⚠️ Could not parse insights as JSON")
                return {}
                
        except Exception as e:
            print(f"⚠️ Insight extraction failed ({e})")
            return {}
    
    def _extract_response_text(self, response: Dict[str, Any]) -> str:
        """
        Extract text content from LLM response
        
        Handles both UnifiedLLMClient dict format and OpenAI object format
        """
        # Check if it's a unified client response (dict with 'text' key)
        if isinstance(response, dict) and 'text' in response:
            return response['text']
        
        # Check if it's OpenAI response object with choices
        if hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content
        
        # Fallback: try to access as dict with choices
        if isinstance(response, dict) and 'choices' in response:
            choices = response['choices']
            if choices and len(choices) > 0:
                return choices[0].get('message', {}).get('content', '')
        
        # Last resort: try to get any text-like content
        if isinstance(response, str):
            return response
        
        print(f"⚠️ Could not extract text from response: {type(response)}")
        return ""
    
    def _load_memory(self):
        """Load persistent memory from file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                
                self.conversation_summary = data.get("conversation_summary", "")
                self.long_term_memory = data.get("long_term_memory", {})
                self.session_metadata = data.get("session_metadata", {})
                
                # Don't load conversation turns (they're session-specific)
                print(f"📄 Loaded memory from {self.memory_file}")
            
        except Exception as e:
            print(f"⚠️ Could not load memory ({e}), starting fresh")
    
    def _save_memory(self):
        """Save persistent memory to file"""
        try:
            memory_data = {
                "conversation_summary": self.conversation_summary,
                "long_term_memory": self.long_term_memory,
                "session_metadata": self.session_metadata,
                "last_updated": datetime.now().isoformat()
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            
            with open(self.memory_file, 'w') as f:
                json.dump(memory_data, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Could not save memory ({e})")
    
    def _update_session_metadata(self, turn: Dict[str, Any]):
        """Update session-level metadata from conversation turn"""
        
        # Track voice mode usage
        if turn.get("metadata", {}).get("voice_mode"):
            self.session_metadata["voice_interactions"] = self.session_metadata.get("voice_interactions", 0) + 1
        
        # Track request types
        request_type = turn.get("metadata", {}).get("request_type")
        if request_type:
            type_counts = self.session_metadata.get("request_types", {})
            type_counts[request_type] = type_counts.get(request_type, 0) + 1
            self.session_metadata["request_types"] = type_counts
        
        # Update conversation count
        self.session_metadata["total_turns"] = len(self.conversation_turns)
        self.session_metadata["last_interaction"] = turn["timestamp"]
    
    async def _trigger_summarization(self):
        """Trigger automatic summarization when threshold is reached (async)"""
        print(f"🔄 Triggering summarization (threshold: {self.summarize_threshold} turns)")
        summary = await self.summarize_history(self.sliding_window_size)
        if summary:
            print(f"📝 Updated conversation summary: {summary[:100]}...")
    
    def _build_summarization_prompt(self, turns: List[Dict[str, Any]]) -> str:
        """Build prompt for conversation summarization"""
        
        conversation_text = ""
        for turn in turns:
            user_input = turn["user_input"]
            assistant_response = turn["assistant_response"]
            conversation_text += f"User: {user_input}\nAssistant: {assistant_response}\n\n"
        
        return f"""
Summarize this conversation, focusing on:
- Key topics discussed
- Important decisions or insights
- User preferences or goals mentioned
- Overall conversation flow and context

Conversation:
{conversation_text}

Provide a concise but comprehensive summary that captures the essential elements.
"""
    
    def _format_conversation_for_insights(self) -> str:
        """Format recent conversation for insight extraction"""
        
        recent_turns = self.conversation_turns[-5:]  # Last 5 turns
        
        conversation_text = ""
        for turn in recent_turns:
            user_input = turn["user_input"]
            assistant_response = turn["assistant_response"]
            conversation_text += f"User: {user_input}\nAssistant: {assistant_response}\n\n"
        
        return conversation_text
    
    def get_context_for_request(self, request_type: str) -> Dict[str, Any]:
        """Get relevant context for a specific request type"""
        
        context = {
            "conversation_history": self.get_conversation_context(),
            "long_term_memory": self.get_long_term_memory(),
            "session_metadata": self.session_metadata.copy()
        }
        
        # Add request-specific context
        if request_type == "resume_generation":
            context["professional_context"] = self.long_term_memory.get("professional", {})
        elif request_type == "voice_interaction":
            context["voice_preferences"] = self.long_term_memory.get("communication_style", {})
        
        return context
    
    def get_conversation_summary(self) -> Optional[str]:
        """Get the current conversation summary"""
        return self.conversation_summary if self.conversation_summary else None
    
    def get_memory_insights(self) -> Dict[str, Any]:
        """Get insights from long-term memory"""
        return {
            "enabled": True,
            "long_term_memory": self.get_long_term_memory(),
            "session_metadata": self.session_metadata.copy(),
            "conversation_summary": self.conversation_summary
        }