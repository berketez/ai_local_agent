"""
Base LLM Interface - Abstract base class for LLM backends

This module provides an abstract base class that defines the interface
for all LLM backends (Ollama, LM Studio, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union, Iterator

class BaseLLM(ABC):
    """Abstract base class for LLM backends."""
    
    @abstractmethod
    def __init__(self, model_name: str, **kwargs):
        """
        Initialize the LLM backend.
        
        Args:
            model_name: Name of the model to use
            **kwargs: Additional backend-specific parameters
        """
        self.model_name = model_name
        self.kwargs = kwargs
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """
        Send a chat request to the LLM.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            stream: Whether to stream the response
            **kwargs: Additional parameters for the request
            
        Returns:
            Response dictionary or iterator of response chunks if streaming
        """
        pass
    
    @abstractmethod
    def generate(self, prompt: str, stream: bool = False, **kwargs) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The prompt text
            stream: Whether to stream the response
            **kwargs: Additional parameters for the request
            
        Returns:
            Response dictionary or iterator of response chunks if streaming
        """
        pass
    
    @abstractmethod
    def embed(self, text: Union[str, List[str]], **kwargs) -> List[List[float]]:
        """
        Generate embeddings for text.
        
        Args:
            text: Text or list of texts to embed
            **kwargs: Additional parameters for the request
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @abstractmethod
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models.
        
        Returns:
            List of model information dictionaries
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the backend is available.
        
        Returns:
            True if the backend is available, False otherwise
        """
        pass
    
    def extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract text from a response dictionary.
        
        Args:
            response: Response dictionary from chat or generate
            
        Returns:
            Extracted text
        """
        # Default implementation - should be overridden by subclasses if needed
        if 'message' in response and 'content' in response['message']:
            return response['message']['content']
        elif 'choices' in response and len(response['choices']) > 0:
            if 'message' in response['choices'][0]:
                return response['choices'][0]['message']['content']
            elif 'text' in response['choices'][0]:
                return response['choices'][0]['text']
        return ""
