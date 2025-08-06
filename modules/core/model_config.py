"""
modules/core/model_config.py - Model configuration for development and production environments

This module provides centralized model configuration for both development and production
environments, aligning with the Digi-Core model architecture.

Key Features:
- Development models (lightweight, ~18GB RAM total)
- Production models (full precision, ~50GB RAM total)
- Task-specific model assignments
- Resource optimization
- Fallback configurations
"""

import os
from typing import Dict, List, Optional
from enum import Enum

class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class TaskType(Enum):
    """Task types for model assignment"""
    ENTITY_EXTRACTION = "entity_extraction"
    CYPHER_GENERATION = "cypher_generation"
    ANSWER_SYNTHESIS = "answer_synthesis"
    FEEDBACK_PROCESSING = "feedback_processing"
    QUERY_CLASSIFICATION = "query_classification"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"

class ModelConfig:
    """
    Centralized model configuration for development and production environments
    
    Provides task-specific model assignments and resource optimization
    based on the environment and available resources.
    """
    
    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        """
        Initialize model configuration
        
        Args:
            environment: Development or production environment
        """
        self.environment = environment
        self._load_configuration()
    
    def _load_configuration(self):
        """Load environment-specific model configuration"""
        if self.environment == Environment.DEVELOPMENT:
            self._load_dev_config()
        else:
            self._load_prod_config()
    
    def _load_dev_config(self):
        """Load development configuration (lightweight models)"""
        self.models = {
            # Core RAG Models (Lightweight for Limited Resources)
            "llama3.1:8b": {
                "ram_gb": 4.0,
                "tasks": [TaskType.ENTITY_EXTRACTION, TaskType.ANSWER_SYNTHESIS, TaskType.FEEDBACK_PROCESSING],
                "description": "General purpose, ~4GB RAM"
            },
            "codellama:7b": {
                "ram_gb": 4.0,
                "tasks": [TaskType.CYPHER_GENERATION, TaskType.QUERY_CLASSIFICATION, TaskType.CODE_GENERATION],
                "description": "Code generation, ~4GB RAM"
            },
            "qwen2.5-coder:latest": {
                "ram_gb": 4.7,
                "tasks": [TaskType.CODE_GENERATION, TaskType.CYPHER_GENERATION],
                "description": "Code generation, ~4.7GB RAM"
            },
            "deepseek-r1:latest": {
                "ram_gb": 5.2,
                "tasks": [TaskType.REASONING, TaskType.FEEDBACK_PROCESSING],
                "description": "Reasoning, ~5.2GB RAM"
            }
        }
        
        # Task assignments for development
        self.task_assignments = {
            TaskType.ENTITY_EXTRACTION: "llama3.1:8b",
            TaskType.CYPHER_GENERATION: "codellama:7b",
            TaskType.ANSWER_SYNTHESIS: "llama3.1:8b",
            TaskType.FEEDBACK_PROCESSING: "llama3.1:8b",
            TaskType.QUERY_CLASSIFICATION: "codellama:7b",
            TaskType.CODE_GENERATION: "qwen2.5-coder:latest",
            TaskType.REASONING: "deepseek-r1:latest"
        }
        
        # Default models for different components
        self.default_models = {
            "parser": "llama3.1:8b",
            "synthesizer": "llama3.1:8b",
            "reasoning": "deepseek-r1:latest",
            "code_generation": "codellama:7b"
        }
        
        # Total RAM requirement
        self.total_ram_gb = sum(model["ram_gb"] for model in self.models.values())
    
    def _load_prod_config(self):
        """Load production configuration (full precision models)"""
        self.models = {
            # Core RAG Models (Full Precision for 128GB RAM)
            "gpt-oss:20b": {
                "ram_gb": 16.0,
                "tasks": [TaskType.ENTITY_EXTRACTION, TaskType.ANSWER_SYNTHESIS],
                "description": "Structured output, 16GB RAM"
            },
            "qwen2.5-coder": {
                "ram_gb": 4.7,
                "tasks": [TaskType.CODE_GENERATION, TaskType.CYPHER_GENERATION],
                "description": "Code generation, 4.7GB RAM"
            },
            "deepseek-r1": {
                "ram_gb": 5.2,
                "tasks": [TaskType.REASONING, TaskType.FEEDBACK_PROCESSING],
                "description": "Fast processing, 5.2GB RAM"
            },
            # Speech Models
            "whisper": {
                "ram_gb": 1.0,
                "tasks": [TaskType.SPEECH_TO_TEXT],
                "description": "Basic STT, 1GB RAM"
            },
            "whisper-large": {
                "ram_gb": 3.0,
                "tasks": [TaskType.SPEECH_TO_TEXT],
                "description": "High accuracy STT, 3GB RAM"
            },
            "whisper-multilingual": {
                "ram_gb": 2.0,
                "tasks": [TaskType.SPEECH_TO_TEXT],
                "description": "Multilingual STT, 2GB RAM"
            },
            "coqui-tts": {
                "ram_gb": 2.0,
                "tasks": [TaskType.TEXT_TO_SPEECH],
                "description": "TTS, 2GB RAM"
            },
            "bark": {
                "ram_gb": 4.0,
                "tasks": [TaskType.TEXT_TO_SPEECH],
                "description": "High quality TTS, 4GB RAM"
            },
            "bark-small": {
                "ram_gb": 2.0,
                "tasks": [TaskType.TEXT_TO_SPEECH],
                "description": "Fast TTS, 2GB RAM"
            }
        }
        
        # Task assignments for production
        self.task_assignments = {
            TaskType.ENTITY_EXTRACTION: "gpt-oss:20b",
            TaskType.CYPHER_GENERATION: "qwen2.5-coder",
            TaskType.ANSWER_SYNTHESIS: "gpt-oss:20b",
            TaskType.FEEDBACK_PROCESSING: "deepseek-r1",
            TaskType.QUERY_CLASSIFICATION: "qwen2.5-coder",
            TaskType.CODE_GENERATION: "qwen2.5-coder",
            TaskType.REASONING: "deepseek-r1",
            TaskType.SPEECH_TO_TEXT: "whisper",
            TaskType.TEXT_TO_SPEECH: "coqui-tts"
        }
        
        # Default models for different components
        self.default_models = {
            "parser": "gpt-oss:20b",
            "synthesizer": "gpt-oss:20b",
            "reasoning": "deepseek-r1",
            "code_generation": "qwen2.5-coder",
            "speech_to_text": "whisper",
            "text_to_speech": "coqui-tts"
        }
        
        # Total RAM requirement
        self.total_ram_gb = sum(model["ram_gb"] for model in self.models.values())
    
    def get_model_for_task(self, task: TaskType) -> str:
        """
        Get the appropriate model for a specific task
        
        Args:
            task: The task type
            
        Returns:
            Model name for the task
        """
        return self.task_assignments.get(task, self.default_models.get("parser"))
    
    def get_models_for_tasks(self, tasks: List[TaskType]) -> List[str]:
        """
        Get models for multiple tasks
        
        Args:
            tasks: List of task types
            
        Returns:
            List of model names
        """
        return [self.get_model_for_task(task) for task in tasks]
    
    def get_available_models(self) -> List[str]:
        """Get list of available models for current environment"""
        return list(self.models.keys())
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """Get information about a specific model"""
        return self.models.get(model_name)
    
    def get_resource_requirements(self) -> Dict:
        """Get resource requirements for current environment"""
        return {
            "environment": self.environment.value,
            "total_ram_gb": self.total_ram_gb,
            "models": len(self.models),
            "task_assignments": {task.value: model for task, model in self.task_assignments.items()}
        }
    
    def validate_model_availability(self, model_name: str) -> bool:
        """
        Validate if a model is available in current environment
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            True if model is available
        """
        return model_name in self.models
    
    def get_fallback_model(self, task: TaskType) -> str:
        """
        Get fallback model for a task (usually a lighter model)
        
        Args:
            task: The task type
            
        Returns:
            Fallback model name
        """
        # For development, fallback to llama3.1:8b for most tasks
        if self.environment == Environment.DEVELOPMENT:
            return "llama3.1:8b"
        
        # For production, use task-specific fallbacks
        fallback_map = {
            TaskType.ENTITY_EXTRACTION: "deepseek-r1",
            TaskType.ANSWER_SYNTHESIS: "deepseek-r1",
            TaskType.CODE_GENERATION: "deepseek-r1",
            TaskType.REASONING: "qwen2.5-coder",
            TaskType.SPEECH_TO_TEXT: "whisper",
            TaskType.TEXT_TO_SPEECH: "bark-small"
        }
        
        return fallback_map.get(task, "deepseek-r1")

# Global configuration instance
def get_model_config(environment: Environment = None) -> ModelConfig:
    """
    Get model configuration for specified environment
    
    Args:
        environment: Environment type (defaults to DEVELOPMENT)
        
    Returns:
        ModelConfig instance
    """
    if environment is None:
        # Auto-detect environment based on environment variable
        env_str = os.getenv("ENVIRONMENT", "development").lower()
        environment = Environment.PRODUCTION if env_str == "production" else Environment.DEVELOPMENT
    
    return ModelConfig(environment)

# Convenience functions
def get_model_for_task(task: TaskType, environment: Environment = None) -> str:
    """Get model for specific task"""
    config = get_model_config(environment)
    return config.get_model_for_task(task)

def get_available_models(environment: Environment = None) -> List[str]:
    """Get available models for environment"""
    config = get_model_config(environment)
    return config.get_available_models()

def get_resource_requirements(environment: Environment = None) -> Dict:
    """Get resource requirements for environment"""
    config = get_model_config(environment)
    return config.get_resource_requirements() 