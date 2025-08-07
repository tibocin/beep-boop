"""
modules.core.orchestrator - Async main pipeline orchestrator using OpenAI SDK

This module orchestrates the complete flow: parse → retrieve → generate → evaluate → respond,
integrating all core components for LLM-driven conversational AI with async support.

Key Features:
- Async pipeline management with OpenAI SDK
- Streaming response generation
- Voice mode support throughout
- Resume generation and explanation workflows
- Context-aware processing with memory integration
- Adaptive retry logic with evaluation feedback
"""

import asyncio
import os
from typing import Dict, Any, Optional, Tuple, AsyncGenerator
from .parser import AsyncLLMParser, ParsedRequest
from .rag.retriever import UnifiedRetriever
from .synthesizer import AsyncLLMSynthesizer
from .evaluator import LLMEvaluator, RetryOrchestrator
from .context_manager import LLMContextManager

class AsyncConversationOrchestrator:
    """
    Async main orchestrator for the simplified conversational AI pipeline
    
    Manages the complete flow from user input to final response,
    emphasizing LLM reasoning throughout the process with streaming support.
    """
    
    def __init__(self, 
                 model: str = "gpt-4o-mini",
                 rag_backend: str = "auto",
                 enable_evaluation: bool = True,
                 enable_memory: bool = True):
        """
        Initialize the async conversation orchestrator
        
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
        print("🔄 Initializing async conversation orchestrator...")
        
        self.parser = AsyncLLMParser(model=model, ollama_model="codellama:7b")
        print("✅ Async parser initialized")
        
        self.retriever = UnifiedRetriever(backend_type=rag_backend)
        print("✅ Retriever initialized")
        
        self.synthesizer = AsyncLLMSynthesizer(model=model, ollama_model="codellama:7b")
        print("✅ Async synthesizer initialized")
        
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
        
        print("🚀 Async conversation orchestrator ready!")
    
    async def process_message(self, user_input: str, voice_mode: bool = False, identity_override: str = None) -> Dict[str, Any]:
        """
        Process a user message through the complete pipeline (async)
        
        Args:
            user_input: User's input message
            voice_mode: Whether this is from voice interaction
            identity_override: Override the detected identity ("Stephen" or "Tibocin")
            
        Returns:
            Dict containing response and metadata
        """
        try:
            # Step 1: Parse user request
            print(f"🔤 Parsing request: {user_input[:50]}...")
            parsed_request, objective = await self.parser.parse_request(user_input, voice_mode)
            
            # Apply identity override if provided
            if identity_override:
                parsed_request.metadata["identity"] = identity_override
            
            if voice_mode:
                parsed_request = self.parser.adapt_for_voice(parsed_request)
            
            # Step 2: Retrieve relevant context
            print(f"🔍 Retrieving context for: {objective}")
            retrieved_context = await self.retriever.retrieve(
                query=user_input,
                context_scope=self._get_context_scope(parsed_request.intent),
                top_k=5
            )
            
            # Convert RAGContext objects to dictionaries for compatibility
            context_list = []
            for ctx in retrieved_context:
                context_list.append({
                    "content": ctx.content,
                    "source": ctx.source,
                    "score": ctx.relevance_score,
                    "reasoning": ctx.relevance_reasoning  # Fixed: use relevance_reasoning
                })
            
            retrieved_context = context_list
            
            # Step 3: Get conversation history if memory is enabled
            conversation_history = None
            if self.enable_memory and self.context_manager:
                conversation_history = self.context_manager.get_conversation_context()
            
            # Step 4: Generate response
            print("🧠 Generating response...")
            response = await self.synthesizer.synthesize_response(
                user_input=user_input,
                retrieved_context=retrieved_context,
                conversation_history=conversation_history,
                parsed_request=parsed_request.__dict__,
                voice_mode=voice_mode
            )
            
            # Step 5: Evaluate response quality if enabled
            if self.enable_evaluation and self.evaluator:
                print("📊 Evaluating response quality...")
                
                # Create CandidateResponse object for evaluation
                from .interfaces import CandidateResponse
                candidate_response = CandidateResponse(
                    content=response["text"],
                    confidence=response.get("metadata", {}).get("confidence", 0.8),
                    reasoning=response.get("metadata", {}).get("reasoning", "Generated response"),
                    voice_friendly=voice_mode
                )
                
                # Evaluate using the correct interface
                evaluation = await self.evaluator.evaluate(
                    response=candidate_response,
                    objective=objective,
                    original_request=user_input
                )
                
                # Retry if quality is poor
                if evaluation.overall_score < 0.7 and self.retry_orchestrator:
                    print("🔄 Quality below threshold, retrying...")
                    retry_response = await self.retry_orchestrator.retry_with_feedback(
                        user_input, 
                        response["text"], 
                        evaluation.reasoning,  # Use reasoning instead of feedback
                        retrieved_context,
                        conversation_history,
                        voice_mode
                    )
                    if retry_response:
                        response = retry_response
                        response["metadata"]["retry_attempt"] = True
            
            # Step 6: Update conversation memory if enabled
            if self.enable_memory and self.context_manager:
                self.context_manager.add_turn(user_input, response["text"], response.get("metadata", {}))
            
            # Step 7: Prepare final response
            final_response = {
                "response": response["text"],
                "metadata": {
                    **response["metadata"],
                    "parsed_intent": parsed_request.intent,
                    "objective": objective,
                    "context_count": len(retrieved_context),
                    "voice_mode": voice_mode,
                    "model_used": self.model
                },
                "usage": response["usage"]
            }
            
            print("✅ Response generated successfully!")
            return final_response
            
        except Exception as e:
            print(f"❌ Error in message processing: {str(e)}")
            return self._create_error_response(str(e), voice_mode, "conversation")
    
    async def process_message_stream(self, user_input: str, voice_mode: bool = False, identity_override: str = None) -> AsyncGenerator[str, None]:
        """
        Process a user message with streaming response (async generator)
        
        Args:
            user_input: User's input message
            voice_mode: Whether this is from voice interaction
            identity_override: Override the detected identity
            
        Yields:
            Response text chunks as they're generated
        """
        try:
            # Step 1: Parse user request
            status_msg = f"🔤 Parsing request: {user_input[:50]}..."
            print(status_msg)
            yield f"__STATUS__{status_msg}"
            
            parsed_request, objective = await self.parser.parse_request(user_input, voice_mode)
            
            # Apply identity override if provided
            if identity_override:
                parsed_request.metadata["identity"] = identity_override
            
            if voice_mode:
                parsed_request = self.parser.adapt_for_voice(parsed_request)
            
            # Step 2: Retrieve relevant context
            status_msg = f"🔍 Retrieving context for: {objective}"
            print(status_msg)
            yield f"__STATUS__{status_msg}"
            
            retrieved_context = await self.retriever.retrieve(
                query=user_input,
                context_scope=self._get_context_scope(parsed_request.intent),
                top_k=5
            )
            
            # Convert RAGContext objects to dictionaries for compatibility
            context_list = []
            for ctx in retrieved_context:
                context_list.append({
                    "content": ctx.content,
                    "source": ctx.source,
                    "score": ctx.relevance_score,
                    "reasoning": ctx.relevance_reasoning  # Fixed: use relevance_reasoning
                })
            
            retrieved_context = context_list
            
            # Step 3: Get conversation history if memory is enabled
            conversation_history = None
            if self.enable_memory and self.context_manager:
                conversation_history = self.context_manager.get_conversation_context()
            
            # Step 4: Stream response generation
            status_msg = "🧠 Streaming response..."
            print(status_msg)
            yield f"__STATUS__{status_msg}"
            
            full_response = ""
            async for chunk in self.synthesizer.synthesize_response_stream(
                user_input=user_input,
                retrieved_context=retrieved_context,
                conversation_history=conversation_history,
                parsed_request=parsed_request.__dict__,
                voice_mode=voice_mode
            ):
                full_response += chunk
                yield chunk
            
            # Step 5: Update conversation memory if enabled
            if self.enable_memory and self.context_manager:
                self.context_manager.add_turn(user_input, full_response, {})
            
            status_msg = "✅ Streaming response completed!"
            print(status_msg)
            yield f"__STATUS__{status_msg}"
            
        except Exception as e:
            error_msg = f"❌ Error in streaming message processing: {str(e)}"
            print(error_msg)
            yield f"__STATUS__{error_msg}"
            yield f"Error: {str(e)}"
    
    async def process_resume_request(self, user_input: str, voice_mode: bool = False) -> Dict[str, Any]:
        """
        Process resume generation request (async)
        
        Args:
            user_input: User's resume request
            voice_mode: Whether this is from voice interaction
            
        Returns:
            Dict containing generated resume content
        """
        try:
            # Parse the resume request
            parsed_request, objective = await self.parser.parse_request(user_input, voice_mode)
            
            # Retrieve relevant user data from professional context
            user_contexts = await self.retriever.retrieve(
                query="professional experience skills work background",
                context_scope=self._get_context_scope("professional"),
                top_k=10
            )
            
            # Convert to user data format
            user_data = {
                "professional_context": [ctx.content for ctx in user_contexts],
                "request": user_input,
                "objective": objective
            }
            
            # Generate resume content
            response = await self.synthesizer.generate_resume_content(
                request_details={"objective": objective, "parsed_request": parsed_request.__dict__},
                user_data=user_data
            )
            
            return {
                "response": response["text"],
                "metadata": {
                    **response["metadata"],
                    "request_type": "resume_generation",
                    "voice_mode": voice_mode,
                    "model_used": self.model
                },
                "usage": response["usage"]
            }
            
        except Exception as e:
            print(f"❌ Error in resume generation: {str(e)}")
            return self._create_error_response(str(e), voice_mode, "resume_generation")
    
    async def process_resume_request_stream(self, user_input: str, voice_mode: bool = False) -> AsyncGenerator[str, None]:
        """
        Process resume generation request with streaming (async generator)
        
        Args:
            user_input: User's resume request
            voice_mode: Whether this is from voice interaction
            
        Yields:
            Resume content chunks as they're generated
        """
        try:
            # Parse the resume request
            parsed_request, objective = await self.parser.parse_request(user_input, voice_mode)
            
            # Retrieve relevant user data
            user_data = await self.retriever.retrieve_user_data()
            
            # Stream resume content generation
            async for chunk in self.synthesizer.generate_resume_content_stream(
                request_details={"objective": objective, "parsed_request": parsed_request.__dict__},
                user_data=user_data
            ):
                yield chunk
                
        except Exception as e:
            print(f"❌ Error in streaming resume generation: {str(e)}")
            yield f"Error generating resume content: {str(e)}"
    
    def get_conversation_summary(self) -> Optional[str]:
        """Get summary of current conversation if memory is enabled"""
        if self.enable_memory and self.context_manager:
            return self.context_manager.get_conversation_summary()
        return None
    
    def get_memory_insights(self) -> Dict[str, Any]:
        """Get insights from conversation memory"""
        if self.enable_memory and self.context_manager:
            return self.context_manager.get_memory_insights()
        return {"enabled": False}
    
    def initialize_knowledge_base(self, yaml_files: Optional[list] = None) -> bool:
        """Initialize the knowledge base with Digi-Core (primary) or YAML files (fallback)"""
        try:
            # Check if Digi-Core is available and enabled
            digi_core_enabled = os.getenv('DIGI_CORE_ENABLED', 'true').lower() == 'true'
            digi_core_api_key = os.getenv('DIGI_CORE_API_KEY')
            
            if digi_core_enabled and digi_core_api_key:
                print("🧠 Using Digi-Core as primary knowledge source...")
                # Digi-Core is automatically initialized by the RAG adapter
                return True
            else:
                print("📚 Using local YAML files as knowledge source...")
                return self.retriever.initialize_from_yaml(yaml_files)
        except Exception as e:
            print(f"❌ Knowledge base initialization failed: {str(e)}")
            return False
    
    def _get_context_scope(self, intent: str):
        """Convert intent to context scope"""
        from .interfaces import ContextScope
        
        if "professional" in intent.lower() or "work" in intent.lower() or "resume" in intent.lower():
            return ContextScope.PROFESSIONAL
        elif "personal" in intent.lower():
            return ContextScope.PERSONAL
        elif "creative" in intent.lower():
            return ContextScope.CREATIVE
        else:
            return ContextScope.GENERAL
    
    def _create_error_response(self, error_msg: str, voice_mode: bool = False, 
                              request_type: str = "conversation") -> Dict[str, Any]:
        """Create error response when processing fails"""
        error_text = f"I apologize, but I encountered an error: {error_msg}. Please try again."
        
        if voice_mode:
            error_text = "I'm sorry, I'm having technical difficulties. Please try again."
        
        return {
            "response": error_text,
            "metadata": {
                "error": True,
                "error_message": error_msg,
                "request_type": request_type,
                "voice_mode": voice_mode,
                "model_used": self.model
            },
            "usage": {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
        }

# Backward compatibility alias
ConversationOrchestrator = AsyncConversationOrchestrator