"""
LM Studio Integration - Implementation of the BaseLLM interface for LM Studio

This module provides implementations of the BaseLLM interface for the
LM Studio local LLM platform, supporting both the Python SDK and OpenAI API.
"""


import sys
import subprocess
from typing import Dict, List, Any, Union, Iterator

from base import BaseLLM

class LMStudioSDK(BaseLLM):
    """LM Studio SDK implementation of the BaseLLM interface."""
    
    def __init__(self, model_name: str, **kwargs):
        """
        Initialize the LM Studio SDK backend.
        
        Args:
            model_name: Name of the LM Studio model to use
            **kwargs: Additional parameters for LM Studio
        """
        super().__init__(model_name, **kwargs)
        self.lmstudio_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the LM Studio client."""
        try:
            import lmstudio
            self.lmstudio_client = lmstudio
        except ImportError:
            print("LM Studio Python SDK not found. Installing...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "lmstudio"])
                import lmstudio
                self.lmstudio_client = lmstudio
            except Exception as e:
                print(f"Failed to install LM Studio Python SDK: {str(e)}")
                self.lmstudio_client = None
    
    def is_available(self) -> bool:
        """
        Check if LM Studio SDK is available.
        
        Returns:
            True if LM Studio SDK is available, False otherwise
        """
        if self.lmstudio_client is None:
            return False
        
        try:
            # Try to access the llm method to check if SDK is working
            _ = self.lmstudio_client.llm
            return True
        except Exception:
            return False
    
    def chat(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """
        Send a chat request to LM Studio.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            stream: Whether to stream the response
            **kwargs: Additional parameters for the request
            
        Returns:
            Response dictionary or iterator of response chunks if streaming
        """
        if self.lmstudio_client is None:
            raise RuntimeError("LM Studio client not initialized")
        
        try:
            # Create LLM instance with the model
            model = self.lmstudio_client.llm(self.model_name)
            
            # Extract the last user message for respond method
            last_user_message = None
            for message in reversed(messages):
                if message["role"] == "user":
                    last_user_message = message["content"]
                    break
            
            if last_user_message is None:
                raise ValueError("No user message found in the messages list")
            
            # Use the respond method for chat
            if stream:
                # LM Studio SDK doesn't support streaming directly
                # We'll simulate it by returning a single response
                response = model.respond(last_user_message, **kwargs)
                
                # Convert to a format similar to streaming responses
                def stream_simulator():
                    yield {"message": {"content": response}}
                
                return stream_simulator()
            else:
                response = model.respond(last_user_message, **kwargs)
                return {"message": {"content": response}}
        except Exception as e:
            raise RuntimeError(f"LM Studio chat request failed: {str(e)}")
    
    def generate(self, prompt: str, stream: bool = False, **kwargs) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """
        Generate text from a prompt using LM Studio.
        
        Args:
            prompt: The prompt text
            stream: Whether to stream the response
            **kwargs: Additional parameters for the request
            
        Returns:
            Response dictionary or iterator of response chunks if streaming
        """
        if self.lmstudio_client is None:
            raise RuntimeError("LM Studio client not initialized")
        
        try:
            # Create LLM instance with the model
            model = self.lmstudio_client.llm(self.model_name)
            
            # Use the respond method for generation
            if stream:
                # LM Studio SDK doesn't support streaming directly
                # We'll simulate it by returning a single response
                response = model.respond(prompt, **kwargs)
                
                # Convert to a format similar to streaming responses
                def stream_simulator():
                    yield {"message": {"content": response}}
                
                return stream_simulator()
            else:
                response = model.respond(prompt, **kwargs)
                return {"message": {"content": response}}
        except Exception as e:
            raise RuntimeError(f"LM Studio generate request failed: {str(e)}")
    
    def embed(self, text: Union[str, List[str]], **kwargs) -> List[List[float]]:
        """
        Generate embeddings for text using LM Studio.
        
        Args:
            text: Text or list of texts to embed
            **kwargs: Additional parameters for the request
            
        Returns:
            List of embedding vectors
        """
        if self.lmstudio_client is None:
            raise RuntimeError("LM Studio client not initialized")
        
        try:
            # Create embedding model
            embed_model = self.lmstudio_client.embedding(self.model_name)
            
            # Handle both single text and list of texts
            if isinstance(text, str):
                embedding = embed_model.embed(text, **kwargs)
                return [embedding]
            else:
                embeddings = []
                for t in text:
                    embedding = embed_model.embed(t, **kwargs)
                    embeddings.append(embedding)
                return embeddings
        except Exception as e:
            raise RuntimeError(f"LM Studio embeddings request failed: {str(e)}")
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available LM Studio models.
        
        Returns:
            List of model information dictionaries
        """
        if self.lmstudio_client is None:
            raise RuntimeError("LM Studio client not initialized")
        
        try:
            # LM Studio SDK doesn't have a direct method to list models
            # We'll return a placeholder with the current model
            return [{"id": self.model_name, "name": self.model_name}]
        except Exception as e:
            raise RuntimeError(f"LM Studio list models request failed: {str(e)}")
    
    def extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract text from an LM Studio response dictionary.
        
        Args:
            response: Response dictionary from chat or generate
            
        Returns:
            Extracted text
        """
        if 'message' in response and 'content' in response['message']:
            return response['message']['content']
        return super().extract_text_from_response(response)


class LMStudioOpenAI(BaseLLM):
    """LM Studio OpenAI API implementation of the BaseLLM interface."""
    
    def __init__(self, model_name: str, base_url: str = "http://localhost:1234/v1", **kwargs):
        """
        Initialize the LM Studio OpenAI API backend.
        
        Args:
            model_name: Name of the LM Studio model to use
            base_url: Base URL for the LM Studio OpenAI API
            **kwargs: Additional parameters for the API
        """
        super().__init__(model_name, **kwargs)
        self.base_url = base_url
        self.openai_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the OpenAI client for LM Studio."""
        try:
            from openai import OpenAI
            self.openai_client = OpenAI(
                base_url=self.base_url,
                api_key="lm-studio"  # LM Studio doesn't require a real API key
            )
        except ImportError:
            print("OpenAI Python library not found. Installing...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "openai"])
                from openai import OpenAI
                self.openai_client = OpenAI(
                    base_url=self.base_url,
                    api_key="lm-studio"
                )
            except Exception as e:
                print(f"Failed to install OpenAI Python library: {str(e)}")
                self.openai_client = None
    
    def is_available(self) -> bool:
        """
        Check if LM Studio OpenAI API is available.
        
        Returns:
            True if LM Studio OpenAI API is available, False otherwise
        """
        if self.openai_client is None:
            return False
        
        try:
            # Try to list models to check if the API is available
            self.openai_client.models.list()
            return True
        except Exception:
            return False
    
    def chat(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """
        Send a chat request to LM Studio OpenAI API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            stream: Whether to stream the response
            **kwargs: Additional parameters for the request
            
        Returns:
            Response dictionary or iterator of response chunks if streaming
        """
        if self.openai_client is None:
            raise RuntimeError("OpenAI client not initialized")
        
        # Merge kwargs with default parameters
        params = {
            "model": self.model_name,
            "messages": messages,
            "stream": stream,
        }
        params.update(kwargs)
        
        try:
            response = self.openai_client.chat.completions.create(**params)
            
            if stream:
                # Convert streaming response to our expected format
                def stream_converter():
                    for chunk in response:
                        if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content'):
                            content = chunk.choices[0].delta.content
                            if content:
                                yield {"message": {"content": content}}
                
                return stream_converter()
            else:
                # Convert response to our expected format
                return {
                    "message": {
                        "content": response.choices[0].message.content
                    },
                    "choices": [
                        {
                            "message": {
                                "content": response.choices[0].message.content
                            }
                        }
                    ]
                }
        except Exception as e:
            raise RuntimeError(f"LM Studio OpenAI API chat request failed: {str(e)}")
    
    def generate(self, prompt: str, stream: bool = False, **kwargs) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """
        Generate text from a prompt using LM Studio OpenAI API.
        
        Args:
            prompt: The prompt text
            stream: Whether to stream the response
            **kwargs: Additional parameters for the request
            
        Returns:
            Response dictionary or iterator of response chunks if streaming
        """
        if self.openai_client is None:
            raise RuntimeError("OpenAI client not initialized")
        
        # Merge kwargs with default parameters
        params = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": stream,
        }
        params.update(kwargs)
        
        try:
            response = self.openai_client.completions.create(**params)
            
            if stream:
                # Convert streaming response to our expected format
                def stream_converter():
                    for chunk in response:
                        if hasattr(chunk.choices[0], 'text'):
                            text = chunk.choices[0].text
                            if text:
                                yield {"message": {"content": text}}
                
                return stream_converter()
            else:
                # Convert response to our expected format
                return {
                    "message": {
                        "content": response.choices[0].text
                    },
                    "choices": [
                        {
                            "text": response.choices[0].text
                        }
                    ]
                }
        except Exception as e:
            raise RuntimeError(f"LM Studio OpenAI API generate request failed: {str(e)}")
    
    def embed(self, text: Union[str, List[str]], **kwargs) -> List[List[float]]:
        """
        Generate embeddings for text using LM Studio OpenAI API.
        
        Args:
            text: Text or list of texts to embed
            **kwargs: Additional parameters for the request
            
        Returns:
            List of embedding vectors
        """
        if self.openai_client is None:
            raise RuntimeError("OpenAI client not initialized")
        
        # Prepare input
        input_text = [text] if isinstance(text, str) else text
        
        # Merge kwargs with default parameters
        params = {
            "model": self.model_name,
            "input": input_text,
        }
        params.update(kwargs)
        
        try:
            response = self.openai_client.embeddings.create(**params)
            
            # Extract embeddings from response
            embeddings = [item.embedding for item in response.data]
            return embeddings
        except Exception as e:
            raise RuntimeError(f"LM Studio OpenAI API embeddings request failed: {str(e)}")
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models from LM Studio OpenAI API.
        
        Returns:
            List of model information dictionaries
        """
        if self.openai_client is None:
            raise RuntimeError("OpenAI client not initialized")
        
        try:
            response = self.openai_client.models.list()
            
            # Convert response to our expected format
            models = []
            for model in response.data:
                models.append({
                    "id": model.id,
                    "name": model.id,
                })
            return models
        except Exception as e:
            raise RuntimeError(f"LM Studio OpenAI API list models request failed: {str(e)}")
    
    def extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract text from an LM Studio OpenAI API response dictionary.
        
        Args:
            response: Response dictionary from chat or generate
            
        Returns:
            Extracted text
        """
        if 'message' in response and 'content' in response['message']:
            return response['message']['content']
        return super().extract_text_from_response(response)