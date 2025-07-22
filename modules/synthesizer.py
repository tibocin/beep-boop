"""
synthesizer.py - Response Synthesis and Evaluation

This module handles:
- Response quality evaluation
- Retry logic for failed responses
- Multi-prompt response synthesis
- Response coherence and flow
"""

import openai
from typing import List, Dict, Optional, Tuple
from .enums import ReqPrompt, Subject, Format, Tone, OutputStyle
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResponseEvaluator:
    """Evaluates response quality and coherence."""
    
    def __init__(self):
        self.quality_threshold = 0.7
        self.coherence_threshold = 0.8
        self.relevance_threshold = 0.7
    
    def evaluate_response(self, 
                         response: str, 
                         original_prompt: ReqPrompt, 
                         context: str = "",
                         response_objective: str = "") -> Dict:
        """
        Evaluate response quality and coherence.
        
        Args:
            response: The response to evaluate
            original_prompt: The original prompt used
            context: RAG context used
            response_objective: The objective of the response
            
        Returns:
            Dict with scores and feedback
        """
        try:
            evaluation_prompt = f"""
You are a response quality evaluator. Rate the following response on multiple dimensions:

RESPONSE OBJECTIVE: {response_objective if response_objective else 'No specific objective'}

ORIGINAL REQUEST:
Subject: {original_prompt.subject.value}
Format: {original_prompt.format.value}
Tone: {original_prompt.tone.value}
Style: {original_prompt.style.value}

CONTEXT: {context if context else 'No additional context'}

RESPONSE TO EVALUATE:
{response}

Rate each dimension from 0.0 to 1.0 and provide brief feedback:

1. RELEVANCE: How well does the response address the request AND the response objective?
2. COHERENCE: Is the response logically structured and clear?
3. TONE_MATCH: Does the tone match the requested tone?
4. COMPLETENESS: Does the response feel complete and satisfying?
5. ENGAGEMENT: Is the response engaging and conversational?
6. OBJECTIVE_ALIGNMENT: How well does the response serve the stated objective?

Provide scores as JSON:
{{
    "relevance": 0.8,
    "coherence": 0.7,
    "tone_match": 0.9,
    "completeness": 0.6,
    "engagement": 0.8,
    "objective_alignment": 0.8,
    "overall_score": 0.76,
    "feedback": "Good response but could be more complete",
    "needs_retry": false
}}
"""
            
            result = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": evaluation_prompt}],
                max_tokens=300,
                temperature=0.1
            )
            
            # Parse the JSON response
            import json
            evaluation = json.loads(result.choices[0].message.content)
            
            # Determine if retry is needed
            evaluation["needs_retry"] = (
                evaluation["overall_score"] < self.quality_threshold or
                evaluation["relevance"] < self.relevance_threshold or
                evaluation["coherence"] < self.coherence_threshold
            )
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating response: {e}")
            return {
                "overall_score": 0.5,
                "needs_retry": True,
                "feedback": f"Evaluation failed: {str(e)}"
            }

class ResponseSynthesizer:
    """Synthesizes multiple prompt responses into coherent output."""
    
    def __init__(self):
        self.evaluator = ResponseEvaluator()
    
    def synthesize_responses(self, 
                           responses: List[Tuple[ReqPrompt, str]], 
                           original_message: str,
                           context: str = "",
                           response_objective: str = "") -> str:
        """
        Synthesize multiple responses into a coherent final response.
        
        Args:
            responses: List of (prompt, response) tuples
            original_message: Original user message
            context: RAG context used
            response_objective: The objective of the response
            
        Returns:
            Synthesized response
        """
        if not responses:
            return "I apologize, but I couldn't generate a response."
        
        if len(responses) == 1:
            # Single response - just evaluate and return
            prompt, response = responses[0]
            evaluation = self.evaluator.evaluate_response(response, prompt, context, response_objective)
            
            if evaluation["needs_retry"]:
                return self._retry_response(prompt, original_message, context, response_objective)
            
            return response
        
        # Multiple responses - synthesize them
        try:
            synthesis_prompt = f"""
You are synthesizing multiple responses into one coherent response.

RESPONSE OBJECTIVE: {response_objective if response_objective else 'Provide a helpful and engaging response'}

ORIGINAL USER MESSAGE: {original_message}

CONTEXT: {context if context else 'No additional context'}

RESPONSES TO SYNTHESIZE:
"""
            
            for i, (prompt, response) in enumerate(responses, 1):
                synthesis_prompt += f"""
Response {i} (Subject: {prompt.subject.value}, Tone: {prompt.tone.value}):
{response}
"""
            
            synthesis_prompt += f"""
Create a single, coherent response that:
1. Addresses the original user message
2. Serves the response objective: {response_objective}
3. Incorporates insights from all responses naturally
4. Maintains a conversational, engaging tone
5. Flows logically from one point to the next
6. Feels like a single, unified response

SYNTHESIZED RESPONSE:
"""
            
            result = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": synthesis_prompt}],
                max_tokens=800,
                temperature=0.7
            )
            
            synthesized_response = result.choices[0].message.content.strip()
            
            # Evaluate the synthesized response
            # Use the first prompt as reference for evaluation
            first_prompt = responses[0][0]
            evaluation = self.evaluator.evaluate_response(
                synthesized_response, first_prompt, context, response_objective
            )
            
            if evaluation["needs_retry"]:
                logger.warning("Synthesized response needs retry, attempting...")
                return self._retry_synthesis(responses, original_message, context, response_objective)
            
            return synthesized_response
            
        except Exception as e:
            logger.error(f"Error synthesizing responses: {e}")
            # Fallback: return the best individual response
            return self._get_best_response(responses, context)
    
    def _retry_response(self, 
                       prompt: ReqPrompt, 
                       message: str, 
                       context: str,
                       response_objective: str = "",
                       max_retries: int = 2) -> str:
        """Retry generating a response with different approaches."""
        
        for attempt in range(max_retries):
            try:
                # Adjust the prompt for retry
                retry_prompt = f"""
You are {prompt.subject.value} expert. The user asked: "{message}"

RESPONSE OBJECTIVE: {response_objective if response_objective else 'Provide a helpful and engaging response'}

Previous response was not satisfactory. Please provide a better response that is:
- More relevant and specific to the objective
- Better structured and coherent
- More engaging and conversational
- Complete and satisfying
- Aligned with the response objective

Context: {context if context else 'No additional context'}

Please respond in a {prompt.tone.value} tone with {prompt.style.value} style.
"""
                
                result = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": retry_prompt}],
                    max_tokens=600,
                    temperature=0.8  # Slightly higher for variety
                )
                
                retry_response = result.choices[0].message.content.strip()
                
                # Evaluate the retry
                evaluation = self.evaluator.evaluate_response(retry_response, prompt, context, response_objective)
                
                if not evaluation["needs_retry"]:
                    logger.info(f"Retry {attempt + 1} successful")
                    return retry_response
                
            except Exception as e:
                logger.error(f"Retry {attempt + 1} failed: {e}")
        
        # If all retries fail, return a fallback response
        return self._generate_fallback_response(prompt, message)
    
    def _retry_synthesis(self, 
                        responses: List[Tuple[ReqPrompt, str]], 
                        message: str, 
                        context: str,
                        response_objective: str = "") -> str:
        """Retry synthesis with a different approach."""
        
        try:
            # Try a simpler synthesis approach
            synthesis_prompt = f"""
Combine these responses into one clear, engaging response:

RESPONSE OBJECTIVE: {response_objective if response_objective else 'Provide a helpful response'}

User: {message}

Responses:
"""
            
            for prompt, response in responses:
                synthesis_prompt += f"- {response}\n"
            
            synthesis_prompt += "\nCombined response:"
            
            result = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": synthesis_prompt}],
                max_tokens=600,
                temperature=0.5
            )
            
            return result.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Synthesis retry failed: {e}")
            return self._get_best_response(responses, context, response_objective)
    
    def _get_best_response(self, 
                          responses: List[Tuple[ReqPrompt, str]], 
                          context: str,
                          response_objective: str = "") -> str:
        """Get the best individual response based on evaluation."""
        
        best_response = None
        best_score = 0
        
        for prompt, response in responses:
            evaluation = self.evaluator.evaluate_response(response, prompt, context, response_objective)
            if evaluation["overall_score"] > best_score:
                best_score = evaluation["overall_score"]
                best_response = response
        
        return best_response or "I apologize, but I couldn't generate a satisfactory response."
    
    def _generate_fallback_response(self, prompt: ReqPrompt, message: str) -> str:
        """Generate a simple fallback response."""
        
        fallback_responses = {
            Subject.VALUES: "I'd be happy to discuss my values and principles. Could you ask me about something specific?",
            Subject.PROJECTS: "I'm working on several interesting projects. What would you like to know more about?",
            Subject.TECHNICAL_SKILLS: "I have experience with various technical approaches. What specific problem are you trying to solve?",
            Subject.PERSONALITY: "I'm curious about what aspects of my personality interest you most.",
            Subject.INTERESTS: "I have many interests and passions. What would you like to explore together?"
        }
        
        return fallback_responses.get(prompt.subject, 
            "I'd love to continue our conversation. What would you like to discuss?")

class SynthesizerAgent:
    """Main synthesizer agent that orchestrates evaluation and synthesis."""
    
    def __init__(self):
        self.synthesizer = ResponseSynthesizer()
        self.evaluator = ResponseEvaluator()
    
    def process_responses(self, 
                         responses: List[Tuple[ReqPrompt, str]], 
                         original_message: str,
                         context: str = "",
                         response_objective: str = "") -> Dict:
        """
        Process multiple responses with evaluation and synthesis.
        
        Args:
            responses: List of (prompt, response) tuples
            original_message: Original user message
            context: RAG context used
            response_objective: The objective of the response
            
        Returns:
            Dict with final response and metadata
        """
        logger.info(f"Processing {len(responses)} responses for synthesis")
        logger.info(f"Response objective: {response_objective}")
        
        # Evaluate each individual response
        evaluations = []
        for prompt, response in responses:
            evaluation = self.evaluator.evaluate_response(response, prompt, context, response_objective)
            evaluations.append({
                "prompt": prompt,
                "response": response,
                "evaluation": evaluation
            })
        
        # Synthesize responses
        final_response = self.synthesizer.synthesize_responses(
            [(e["prompt"], e["response"]) for e in evaluations],
            original_message,
            context,
            response_objective
        )
        
        # Evaluate final response
        final_evaluation = self.evaluator.evaluate_response(
            final_response, 
            evaluations[0]["prompt"] if evaluations else None,
            context,
            response_objective
        )
        
        return {
            "final_response": final_response,
            "individual_evaluations": evaluations,
            "final_evaluation": final_evaluation,
            "response_count": len(responses),
            "synthesis_used": len(responses) > 1
        } 