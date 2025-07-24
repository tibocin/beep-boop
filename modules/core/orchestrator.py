"""
modules.core.orchestrator - Main pipeline orchestrator for simplified architecture

This module orchestrates the complete flow: parse → retrieve → generate → evaluate → respond,
integrating all core components for LLM-driven conversational AI.

Key Features:
- Unified pipeline management
- Voice mode support throughout
- Resume generation and explanation workflows
- Context-aware processing with memory integration
- Adaptive retry logic with evaluation feedback
"""

from typing import Dict, Any, Optional, Tuple
from .interfaces import RequestType
from .parser import LLMParser
from .rag.retriever import UnifiedRetriever
from .synthesizer import LLMSynthesizer
from .evaluator import LLMEvaluator, RetryOrchestrator
from .context_manager import LLMContextManager

class ConversationOrchestrator:
    """
    Main orchestrator for the simplified conversational AI pipeline
    
    Manages the complete flow from user input to final response,
    emphasizing LLM reasoning throughout the process.
    """
    
    def __init__(self, 
                 model: str = "gpt-4o-mini",
                 rag_backend: str = "auto",
                 enable_evaluation: bool = True,
                 enable_memory: bool = True):
        """
        Initialize the conversation orchestrator
        
        Args:
            model: LLM model to use for all components
            rag_backend: RAG backend type ("auto", "simple", "chroma")
            enable_evaluation: Whether to use evaluation and retry logic
            enable_memory: Whether to use conversation memory
        """
        self.model = model
        self.enable_evaluation = enable_evaluation
        self.enable_memory = enable_memory
        
        # Initialize core components
        print("🔄 Initializing conversation orchestrator...")
        
        self.parser = LLMParser(model=model)
        print("✅ Parser initialized")
        
        self.retriever = UnifiedRetriever(backend_type=rag_backend)
        print("✅ Retriever initialized")
        
        self.synthesizer = LLMSynthesizer(model=model)
        print("✅ Synthesizer initialized")
        
        if enable_evaluation:
            self.evaluator = LLMEvaluator(model=model)
            self.retry_orchestrator = RetryOrchestrator(self.evaluator, self.synthesizer)
            print("✅ Evaluator and retry orchestrator initialized")
        else:
            self.evaluator = None
            self.retry_orchestrator = None
        
        if enable_memory:
            self.context_manager = LLMContextManager(model=model)
            print("✅ Context manager initialized")
        else:
            self.context_manager = None
        
        print("🚀 Conversation orchestrator ready!")
    
    def process_message(self, user_input: str, voice_mode: bool = False) -> Dict[str, Any]:
        """
        Process a user message through the complete pipeline
        
        Args:
            user_input: User's input message
            voice_mode: Whether this is from voice interaction
            
        Returns:
            Dict containing response and metadata
        """
        try:
            # Step 1: Parse user request
            print(f"🔤 Parsing request: {user_input[:50]}...")
            req_prompt, objective = self.parser.parse_request(user_input, voice_mode)
            
            if voice_mode:
                req_prompt = self.parser.adapt_for_voice(req_prompt)
            
            # Step 2: Retrieve relevant context
            print(f"🔍 Retrieving context for: {req_prompt.context_scope.value}")
            contexts = self.retriever.retrieve(
                query=req_prompt.intent,
                context_scope=req_prompt.context_scope,
                top_k=5
            )
            
            # Step 3: Add conversation context if memory is enabled
            conversation_context = None
            if self.context_manager:
                conversation_context = self.context_manager.get_conversation_context()
                # Add conversation context to objective if relevant
                if conversation_context:
                    objective.success_criteria.append("Consider conversation history appropriately")
            
            # Step 4: Generate response with evaluation/retry if enabled
            if self.retry_orchestrator and self.enable_evaluation:
                print("🧠 Generating response with evaluation...")
                response, evaluation, attempts = self.retry_orchestrator.generate_with_retry(
                    req_prompt, contexts, objective, max_attempts=3
                )
                evaluation_used = True
            else:
                print("🧠 Generating response...")
                response = self.synthesizer.generate(req_prompt, contexts, objective)
                evaluation = None
                attempts = 1
                evaluation_used = False
            
            # Step 5: Optimize for voice if needed
            if voice_mode and not response.voice_friendly:
                print("🎤 Optimizing for voice...")
                response = self.synthesizer.optimize_for_voice(response)
            
            # Step 6: Update conversation memory if enabled
            if self.context_manager:
                print("💾 Updating conversation memory...")
                metadata = {
                    "request_type": req_prompt.request_type.value,
                    "context_scope": req_prompt.context_scope.value,
                    "voice_mode": voice_mode,
                    "evaluation_used": evaluation_used,
                    "attempts": attempts,
                    "confidence": response.confidence
                }
                
                self.context_manager.add_turn(user_input, response.content, metadata)
                
                # Extract insights periodically
                if len(self.context_manager.conversation_turns) % 5 == 0:
                    insights = self.context_manager.extract_insights()
                    if insights:
                        print(f"💡 Extracted insights: {list(insights.keys())}")
            
            # Step 7: Prepare final response
            final_response = {
                "content": response.content,
                "metadata": {
                    "request_type": req_prompt.request_type.value,
                    "intent": req_prompt.intent,
                    "context_scope": req_prompt.context_scope.value,
                    "key_topics": req_prompt.key_topics,
                    "voice_mode": voice_mode,
                    "voice_friendly": response.voice_friendly,
                    "confidence": response.confidence,
                    "reasoning": response.reasoning,
                    "contexts_used": len(contexts),
                    "evaluation_used": evaluation_used,
                    "attempts": attempts,
                    "generation_metadata": response.generation_metadata
                }
            }
            
            # Add evaluation info if available
            if evaluation:
                final_response["metadata"]["evaluation"] = {
                    "overall_score": evaluation.overall_score,
                    "meets_objective": evaluation.meets_objective,
                    "strengths": evaluation.strengths,
                    "improvements": evaluation.improvements
                }
            
            print(f"✅ Response generated (confidence: {response.confidence:.2f})")
            return final_response
            
        except Exception as e:
            print(f"❌ Error in orchestrator: {e}")
            return self._create_error_response(str(e), voice_mode)
    
    def process_resume_request(self, user_input: str, voice_mode: bool = False) -> Dict[str, Any]:
        """
        Specialized processing for resume generation requests
        
        Args:
            user_input: User's resume-related request
            voice_mode: Whether this is from voice interaction
            
        Returns:
            Resume-focused response
        """
        print("📝 Processing resume generation request...")
        
        # Force request type to resume generation
        try:
            req_prompt, objective = self.parser.parse_request(user_input, voice_mode)
            req_prompt.request_type = RequestType.RESUME_GENERATION
            req_prompt.context_scope = req_prompt.context_scope  # Keep user's preferred scope
            
            # Enhance objective for resume focus
            objective.primary_goal = "Help with resume/CV creation and improvement"
            objective.success_criteria.extend([
                "Focus on professional experience and skills",
                "Use professional language and formatting",
                "Highlight achievements and impact",
                "Tailor content to user's background"
            ])
            
            # Get professional context
            contexts = self.retriever.retrieve(
                query=f"professional experience work skills {req_prompt.intent}",
                context_scope=req_prompt.context_scope,
                top_k=7  # More context for resume work
            )
            
            # Generate with resume focus
            if self.retry_orchestrator:
                response, evaluation, attempts = self.retry_orchestrator.generate_with_retry(
                    req_prompt, contexts, objective, max_attempts=3
                )
            else:
                response = self.synthesizer.generate(req_prompt, contexts, objective)
                evaluation = None
                attempts = 1
            
            # Voice optimization if needed
            if voice_mode and not response.voice_friendly:
                response = self.synthesizer.optimize_for_voice(response)
            
            # Update memory with resume focus
            if self.context_manager:
                metadata = {
                    "request_type": "resume_generation",
                    "context_scope": req_prompt.context_scope.value,
                    "voice_mode": voice_mode,
                    "specialized_processing": True,
                    "confidence": response.confidence
                }
                self.context_manager.add_turn(user_input, response.content, metadata)
            
            return {
                "content": response.content,
                "metadata": {
                    "request_type": "resume_generation",
                    "specialized_processing": True,
                    "voice_mode": voice_mode,
                    "confidence": response.confidence,
                    "contexts_used": len(contexts),
                    "attempts": attempts
                }
            }
            
        except Exception as e:
            print(f"❌ Error in resume processing: {e}")
            return self._create_error_response(str(e), voice_mode, "resume_generation")
    
    def get_conversation_summary(self) -> Optional[str]:
        """Get current conversation summary"""
        if self.context_manager:
            return self.context_manager.conversation_summary
        return None
    
    def get_memory_insights(self) -> Dict[str, Any]:
        """Get current long-term memory insights"""
        if self.context_manager:
            return self.context_manager.get_long_term_memory()
        return {}
    
    def initialize_knowledge_base(self, yaml_files: Optional[list] = None) -> bool:
        """Initialize the knowledge base with YAML files"""
        try:
            return self.retriever.initialize_from_yaml(yaml_files)
        except Exception as e:
            print(f"⚠️ Knowledge base initialization failed: {e}")
            return False
    
    def _create_error_response(self, error_msg: str, voice_mode: bool = False, 
                              request_type: str = "conversation") -> Dict[str, Any]:
        """Create error response when processing fails"""
        
        if request_type == "resume_generation":
            content = "I'd be happy to help with your resume. Could you tell me more about your background and what type of position you're targeting?"
        else:
            content = "I'm here to help! Could you tell me a bit more about what you're looking for?"
        
        if voice_mode:
            content = "I'm here to help you. What would you like to talk about?"
        
        return {
            "content": content,
            "metadata": {
                "request_type": request_type,
                "voice_mode": voice_mode,
                "error": True,
                "error_message": error_msg,
                "confidence": 0.3
            }
        }