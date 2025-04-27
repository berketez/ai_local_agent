"""
LLM Factory - Factory for creating LLM backends

This module provides a factory for creating LLM backends based on
availability and user preferences.
"""


from typing import List

from base import BaseLLM
from ollama import OllamaLLM
from lmstudio import LMStudioSDK, LMStudioOpenAI

class LLMFactory:
    """Factory for creating LLM backends."""
    
    @staticmethod
    def create_llm(backend_type: str, model_name: str, **kwargs) -> BaseLLM:
        """
        Create an LLM backend of the specified type.
        
        Args:
            backend_type: Type of backend to create ('ollama', 'lmstudio_sdk', 'lmstudio_openai', 'auto')
            model_name: Name of the model to use
            **kwargs: Additional parameters for the backend
            
        Returns:
            An instance of the specified LLM backend
        """
        if backend_type == 'auto':
            return LLMFactory.create_auto(model_name, **kwargs)
        elif backend_type == 'ollama':
            return OllamaLLM(model_name, **kwargs)
        elif backend_type == 'lmstudio_sdk':
            return LMStudioSDK(model_name, **kwargs)
        elif backend_type == 'lmstudio_openai':
            return LMStudioOpenAI(model_name, **kwargs)
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")
    
    @staticmethod
    def create_auto(model_name: str, **kwargs) -> BaseLLM:
        """
        Automatically select and create an available LLM backend.
        
        Args:
            model_name: Name of the model to use
            **kwargs: Additional parameters for the backend
            
        Returns:
            An instance of an available LLM backend
        """
        # Try Ollama first
        try:
            ollama = OllamaLLM(model_name, **kwargs)
            if ollama.is_available():
                print("Using Ollama backend")
                return ollama
        except Exception as e:
            print(f"Ollama not available: {str(e)}")
        
        # Try LM Studio SDK next
        try:
            lmstudio_sdk = LMStudioSDK(model_name, **kwargs)
            if lmstudio_sdk.is_available():
                print("Using LM Studio SDK backend")
                return lmstudio_sdk
        except Exception as e:
            print(f"LM Studio SDK not available: {str(e)}")
        
        # Try LM Studio OpenAI API last
        try:
            lmstudio_openai = LMStudioOpenAI(model_name, **kwargs)
            if lmstudio_openai.is_available():
                print("Using LM Studio OpenAI API backend")
                return lmstudio_openai
        except Exception as e:
            print(f"LM Studio OpenAI API not available: {str(e)}")
        
        # If no backend is available, raise an error
        raise RuntimeError("No LLM backend available. Please install Ollama or LM Studio.")
    
    @staticmethod
    def list_available_backends() -> List[str]:
        """
        List available LLM backends.
        
        Returns:
            List of available backend types
        """
        available = []
        
        # Check Ollama
        try:
            ollama = OllamaLLM("placeholder")
            if ollama.is_available():
                available.append("ollama")
        except Exception:
            pass
        
        # Check LM Studio SDK
        try:
            lmstudio_sdk = LMStudioSDK("placeholder")
            if lmstudio_sdk.is_available():
                available.append("lmstudio_sdk")
        except Exception:
            pass
        
        # Check LM Studio OpenAI API
        try:
            lmstudio_openai = LMStudioOpenAI("placeholder")
            if lmstudio_openai.is_available():
                available.append("lmstudio_openai")
        except Exception:
            pass
        
        return available
