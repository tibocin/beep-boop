"""
modules.core.evaluator - LLM-powered response evaluator with reasoning

This module evaluates response quality using LLM reasoning rather than rigid metrics,
providing feedback loop for iterative improvement.

Key Features:
- Natural language evaluation criteria over numerical scores
- LLM reasoning about response quality and fit  
- Adaptive retry logic based on context
- Voice mode evaluation considerations
"""

import json
from typing import Dict, Any
from .llm_client import UnifiedLLMClient
from .interfaces import (
    BaseEvaluator, CandidateResponse, ResponseObjective, EvaluationScore
)

class LLMEvaluator(BaseEvaluator):
    """
    LLM-powered response evaluator
    
    Uses LLM reasoning to evaluate response quality against objectives
    rather than relying on rigid numerical metrics.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", max_retries: int = 2):
        """Initialize the LLM evaluator"""
        self.model = model
        self.max_retries = max_retries
        self.client = UnifiedLLMClient(openai_model=model)
    
    async def evaluate(self, response: CandidateResponse, objective: ResponseObjective,
                original_request: str) -> EvaluationScore:
        """
        Evaluate response against objective using LLM reasoning (async)
        
        Args:
            response: Generated response to evaluate
            objective: Original response objective
            original_request: User's original request
            
        Returns:
            Evaluation with reasoning and improvement suggestions
        """
        try:
            # Build evaluation prompt
            evaluation_prompt = self._build_evaluation_prompt(
                response, objective, original_request
            )
            
            # Get LLM evaluation using UnifiedLLMClient
            eval_response = await self.client.chat_completion(
                messages=[{"role": "user", "content": evaluation_prompt}],
                model=self.model,
                temperature=0.3
            )
            
            # Extract response text
            eval_text = self._extract_response_text(eval_response)
            
            # Try to parse as JSON for structured evaluation
            try:
                eval_data = json.loads(eval_text)
                return self._create_evaluation_score(eval_data, response.voice_friendly)
            except json.JSONDecodeError:
                # Fallback evaluation
                return self._create_fallback_evaluation(response, objective)
                
        except Exception as e:
            print(f"⚠️ LLM evaluation failed ({e}), using basic evaluation")
            return self._create_error_evaluation(str(e), response)
    
    def should_retry(self, evaluation: EvaluationScore, attempt_count: int) -> bool:
        """Determine if response should be regenerated"""
        
        # Don't retry if we've hit max attempts
        if attempt_count >= self.max_retries:
            return False
        
        # LLM explicitly recommended retry
        if evaluation.retry_recommended:
            return True
        
        # Overall score is very low
        if evaluation.overall_score < 0.4:
            return True
        
        # Doesn't meet core objective
        if not evaluation.meets_objective:
            return True
        
        # Voice mode but not voice appropriate
        if not evaluation.voice_mode_appropriate and "voice" in evaluation.reasoning.lower():
            return True
        
        return False
    
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
    
    def _build_evaluation_prompt(self, response: CandidateResponse, 
                                objective: ResponseObjective, original_request: str) -> str:
        """Build comprehensive evaluation prompt"""
        
        return f"""
You are evaluating a response for quality and fit against specific objectives.

ORIGINAL USER REQUEST:
{original_request}

RESPONSE OBJECTIVE:
Primary Goal: {objective.primary_goal}
Success Criteria: {', '.join(objective.success_criteria)}
Audience: {objective.audience}
Style Preference: {objective.style_preference}
Length Guidance: {objective.length_guidance}
{f"Voice Considerations: {objective.voice_considerations}" if objective.voice_considerations else ""}

GENERATED RESPONSE:
{response.content}

RESPONSE METADATA:
Confidence: {response.confidence}
Voice Friendly: {response.voice_friendly}
AI's Reasoning: {response.reasoning}

EVALUATION TASK:
Evaluate this response using natural language reasoning, considering:

1. OBJECTIVE ALIGNMENT: How well does the response achieve the primary goal?
2. SUCCESS CRITERIA: Does it meet the stated success criteria?
3. AUDIENCE FIT: Is it appropriate for the intended audience?
4. STYLE MATCH: Does the style match preferences?
5. LENGTH APPROPRIATENESS: Is the length suitable for the guidance?
6. VOICE CONSIDERATIONS: If voice-related, is it speech-friendly?
7. OVERALL QUALITY: General helpfulness, clarity, and engagement

Focus on whether the response would genuinely help the user achieve their goals.
Consider both what works well and what could be improved.
"""
    
    def _get_evaluation_function(self) -> Dict[str, Any]:
        """Define function schema for structured evaluation"""
        return {
            "name": "evaluate_response",
            "description": "Evaluate response quality with reasoning",
            "parameters": {
                "type": "object",
                "properties": {
                    "overall_score": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Overall quality score (0.0 to 1.0)"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Natural language explanation of the evaluation"
                    },
                    "strengths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "What works well in this response"
                    },
                    "improvements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific areas for improvement"
                    },
                    "meets_objective": {
                        "type": "boolean",
                        "description": "Whether the response meets the primary objective"
                    },
                    "voice_mode_appropriate": {
                        "type": "boolean",
                        "description": "Whether the response is suitable for voice interaction"
                    },
                    "retry_recommended": {
                        "type": "boolean",
                        "description": "Whether the response should be regenerated"
                    },
                    "retry_guidance": {
                        "type": "string",
                        "description": "If retry recommended, specific guidance for improvement"
                    },
                    "evaluation_details": {
                        "type": "object",
                        "properties": {
                            "objective_alignment": {"type": "string"},
                            "success_criteria_met": {"type": "string"},
                            "audience_fit": {"type": "string"},
                            "style_match": {"type": "string"},
                            "length_appropriateness": {"type": "string"},
                            "voice_considerations": {"type": "string"}
                        },
                        "description": "Detailed evaluation of each dimension"
                    }
                },
                "required": [
                    "overall_score", "reasoning", "strengths", "improvements",
                    "meets_objective", "voice_mode_appropriate", "retry_recommended"
                ]
            }
        }
    
    def _create_evaluation_score(self, eval_data: Dict[str, Any], 
                                voice_friendly: bool) -> EvaluationScore:
        """Create EvaluationScore from LLM evaluation data"""
        
        return EvaluationScore(
            overall_score=eval_data["overall_score"],
            reasoning=eval_data["reasoning"],
            strengths=eval_data["strengths"],
            improvements=eval_data["improvements"],
            meets_objective=eval_data["meets_objective"],
            voice_mode_appropriate=eval_data.get("voice_mode_appropriate", voice_friendly),
            retry_recommended=eval_data["retry_recommended"],
            retry_guidance=eval_data.get("retry_guidance")
        )
    
    def _create_fallback_evaluation(self, response: CandidateResponse, 
                                   objective: ResponseObjective) -> EvaluationScore:
        """Create basic evaluation when LLM evaluation fails"""
        
        # Basic heuristics
        content_length = len(response.content)
        
        # Length appropriateness
        length_ok = True
        if objective.length_guidance == "brief" and content_length > 500:
            length_ok = False
        elif objective.length_guidance == "detailed" and content_length < 200:
            length_ok = False
        
        # Use response confidence as baseline
        score = response.confidence if response.confidence > 0 else 0.7
        
        # Adjust based on basic checks
        if not length_ok:
            score *= 0.8
        
        return EvaluationScore(
            overall_score=score,
            reasoning="Basic evaluation due to LLM evaluation failure",
            strengths=["Response was generated successfully"],
            improvements=["Could not perform detailed evaluation"],
            meets_objective=score > 0.6,
            voice_mode_appropriate=response.voice_friendly,
            retry_recommended=score < 0.5,
            retry_guidance="Consider adjusting length and content based on objective" if score < 0.5 else None
        )
    
    def _create_error_evaluation(self, error_msg: str, 
                                response: CandidateResponse) -> EvaluationScore:
        """Create evaluation when evaluation process fails"""
        
        return EvaluationScore(
            overall_score=0.5,  # Neutral score
            reasoning=f"Evaluation failed: {error_msg}",
            strengths=["Response exists"],
            improvements=["Could not evaluate properly"],
            meets_objective=True,  # Assume it's okay if we can't evaluate
            voice_mode_appropriate=response.voice_friendly,
            retry_recommended=False,  # Don't retry on evaluation errors
            retry_guidance=None
        )

class RetryOrchestrator:
    """
    Orchestrates the retry logic with evaluation feedback
    
    Manages the cycle of generation → evaluation → retry with
    adaptive improvements based on LLM feedback.
    """
    
    def __init__(self, evaluator: LLMEvaluator, synthesizer):
        """Initialize retry orchestrator"""
        self.evaluator = evaluator
        self.synthesizer = synthesizer
    
    def generate_with_retry(self, req_prompt, contexts, objective, max_attempts: int = 3):
        """
        Generate response with retry loop based on evaluation
        
        Args:
            req_prompt: Structured user request
            contexts: RAG contexts
            objective: Response objective
            max_attempts: Maximum generation attempts
            
        Returns:
            Tuple of (best_response, final_evaluation, attempt_count)
        """
        best_response = None
        best_evaluation = None
        
        for attempt in range(max_attempts):
            # Generate response
            if attempt == 0:
                # First attempt - normal generation
                response = self.synthesizer.generate(req_prompt, contexts, objective)
            else:
                # Retry with improvement guidance
                improved_objective = self._enhance_objective_with_feedback(
                    objective, best_evaluation
                )
                response = self.synthesizer.generate(req_prompt, contexts, improved_objective)
            
            # Evaluate response
            evaluation = self.evaluator.evaluate(response, objective, req_prompt.original_text)
            
            # Keep track of best response
            if best_response is None or evaluation.overall_score > best_evaluation.overall_score:
                best_response = response
                best_evaluation = evaluation
            
            # Check if we should stop retrying
            if not self.evaluator.should_retry(evaluation, attempt + 1):
                break
            
            print(f"🔄 Retry {attempt + 1}: {evaluation.reasoning}")
        
        return best_response, best_evaluation, attempt + 1
    
    def _enhance_objective_with_feedback(self, original_objective: ResponseObjective, 
                                        evaluation: EvaluationScore) -> ResponseObjective:
        """Enhance objective with feedback from previous evaluation"""
        
        # Add improvement suggestions to success criteria
        enhanced_criteria = original_objective.success_criteria.copy()
        if evaluation.retry_guidance:
            enhanced_criteria.append(f"Address feedback: {evaluation.retry_guidance}")
        
        # Add specific improvements
        for improvement in evaluation.improvements:
            enhanced_criteria.append(f"Improve: {improvement}")
        
        # Create enhanced objective
        return ResponseObjective(
            primary_goal=original_objective.primary_goal,
            success_criteria=enhanced_criteria,
            audience=original_objective.audience,
            style_preference=original_objective.style_preference,
            length_guidance=original_objective.length_guidance,
            avoid_patterns=original_objective.avoid_patterns + [
                "Repeat previous weaknesses"
            ],
            voice_considerations=original_objective.voice_considerations
        )
    
    async def retry_with_feedback(self, user_input: str, original_response: str, 
                                 feedback: str, retrieved_context: list, 
                                 conversation_history: list, voice_mode: bool) -> dict:
        """
        Retry response generation with feedback from evaluation
        
        Args:
            user_input: Original user input
            original_response: Previous response that was evaluated
            feedback: Evaluation feedback to improve upon
            retrieved_context: Retrieved context for the request
            conversation_history: Previous conversation history
            voice_mode: Whether this is for voice interaction
            
        Returns:
            Improved response dict or None if retry fails
        """
        try:
            # Create enhanced prompt with feedback
            enhanced_prompt = f"""
Previous response to "{user_input}" was: {original_response}

Feedback for improvement: {feedback}

Please generate an improved response that addresses the feedback while maintaining the original intent.
"""
            
            # Generate improved response
            retry_response = await self.synthesizer.synthesize_response(
                user_input=enhanced_prompt,
                retrieved_context=retrieved_context,
                conversation_history=conversation_history,
                parsed_request={"intent": "improve_response", "voice_mode": voice_mode},
                voice_mode=voice_mode
            )
            
            # Add retry metadata
            retry_response["metadata"]["retry_attempt"] = True
            retry_response["metadata"]["original_response"] = original_response
            retry_response["metadata"]["feedback_addressed"] = feedback
            
            return retry_response
            
        except Exception as e:
            print(f"⚠️ Retry generation failed: {str(e)}")
            return None