"""
Ollama LLM Integration - Implementation of the BaseLLM interface for Ollama

This module provides an implementation of the BaseLLM interface for the
Ollama local LLM platform.
"""


import sys

import subprocess
from typing import Dict, List, Any, Optional, Union, Iterator

from base import BaseLLM

class OllamaLLM(BaseLLM):
    """Ollama implementation of the BaseLLM interface."""
    
    def __init__(self, model_name: str, host: str = "http://localhost:11434", **kwargs):
        """
        Initialize the Ollama LLM backend.
        
        Args:
            model_name: Name of the Ollama model to use
            host: Host URL for the Ollama server
            **kwargs: Additional parameters for Ollama
        """
        super().__init__(model_name, **kwargs)
        self.host = host
        self.ollama_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Ollama client."""
        try:
            import ollama
            # Create a client with the specified host
            self.ollama_client = ollama.Client(host=self.host)
        except ImportError:
            print("Ollama Python library not found. Installing...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "ollama"])
                import ollama
                self.ollama_client = ollama.Client(host=self.host)
            except Exception as e:
                print(f"Failed to install Ollama Python library: {str(e)}")
                self.ollama_client = None
    
    def is_available(self) -> bool:
        """
        Check if Ollama is available.
        
        Returns:
            True if Ollama is available, False otherwise
        """
        if self.ollama_client is None:
            return False
        
        try:
            # Try to list models to check if Ollama server is running
            self.ollama_client.list()
            return True
        except Exception:
            return False
    
    def chat(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """
        Send a chat request to Ollama.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            stream: Whether to stream the response
            **kwargs: Additional parameters for the request
            
        Returns:
            Response dictionary or iterator of response chunks if streaming
        """
        if self.ollama_client is None:
            raise RuntimeError("Ollama client not initialized")
        
        # Merge kwargs with default parameters
        params = {
            "model": self.model_name,
            "messages": messages,
            "stream": stream,
        }
        params.update(kwargs)
        
        try:
            return self.ollama_client.chat(**params)
        except Exception as e:
            raise RuntimeError(f"Ollama chat request failed: {str(e)}")
    
    def generate(self, prompt: str, stream: bool = False, **kwargs) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """
        Generate text from a prompt using Ollama.
        
        Args:
            prompt: The prompt text
            stream: Whether to stream the response
            **kwargs: Additional parameters for the request
            
        Returns:
            Response dictionary or iterator of response chunks if streaming
        """
        if self.ollama_client is None:
            raise RuntimeError("Ollama client not initialized")
        
        # Merge kwargs with default parameters
        params = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": stream,
        }
        params.update(kwargs)
        
        try:
            return self.ollama_client.generate(**params)
        except Exception as e:
            raise RuntimeError(f"Ollama generate request failed: {str(e)}")
    
    def embed(self, text: Union[str, List[str]], **kwargs) -> List[List[float]]:
        """
        Generate embeddings for text using Ollama.
        
        Args:
            text: Text or list of texts to embed
            **kwargs: Additional parameters for the request
            
        Returns:
            List of embedding vectors
        """
        if self.ollama_client is None:
            raise RuntimeError("Ollama client not initialized")
        
        # Merge kwargs with default parameters
        params = {
            "model": self.model_name,
            "prompt": text if isinstance(text, str) else None,
            "input": text if isinstance(text, list) else None,
        }
        params.update(kwargs)
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        try:
            response = self.ollama_client.embeddings(**params)
            
            # Handle both single text and list of texts
            if isinstance(text, str):
                return [response["embedding"]]
            else:
                return response["embeddings"]
        except Exception as e:
            raise RuntimeError(f"Ollama embeddings request failed: {str(e)}")
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available Ollama models.
        
        Returns:
            List of model information dictionaries
        """
        if self.ollama_client is None:
            raise RuntimeError("Ollama client not initialized")
        
        try:
            response = self.ollama_client.list()
            return response["models"]
        except Exception as e:
            raise RuntimeError(f"Ollama list models request failed: {str(e)}")
    
    def pull_model(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Pull a model from Ollama.
        
        Args:
            model_name: Name of the model to pull (defaults to self.model_name)
            
        Returns:
            Response dictionary
        """
        if self.ollama_client is None:
            raise RuntimeError("Ollama client not initialized")
        
        model = model_name or self.model_name
        
        try:
            return self.ollama_client.pull(model)
        except Exception as e:
            raise RuntimeError(f"Ollama pull model request failed: {str(e)}")
    
    def extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract text from an Ollama response dictionary.
        
        Args:
            response: Response dictionary from chat or generate
            
        Returns:
            Extracted text
        """
        if 'message' in response and 'content' in response['message']:
            return response['message']['content']
        elif 'response' in response:
            return response['response']
        return super().extract_text_from_response(response)
