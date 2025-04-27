"""
Model Loader - Handles loading and configuration of LLM models

This module provides functionality to load and configure LLM models
using llama-cpp-python, optimized for macOS.
"""

import os
from typing import Dict, Any
class ModelLoader:
    """Handles loading and configuration of LLM models."""
    
    def __init__(
        self,
        model_path: str,
        context_length: int = 4096,
        temperature: float = 0.7,
        n_gpu_layers: int = 1,
        n_batch: int = 512,
        verbose: bool = False
    ):
        """
        Initialize the model loader.
        
        Args:
            model_path: Path to the model file (GGUF format)
            context_length: Context length for the model
            temperature: Temperature for text generation
            n_gpu_layers: Number of GPU layers to use (for Metal acceleration)
            n_batch: Batch size for processing
            verbose: Whether to enable verbose output
        """
        self.model_path = model_path
        self.context_length = context_length
        self.temperature = temperature
        self.n_gpu_layers = n_gpu_layers
        self.n_batch = n_batch
        self.verbose = verbose
        self.Llama = None
        
    def load_model(self):
        """
        Load the LLM model using llama-cpp-python.
        
        Returns:
            The loaded LLM model
        
        Raises:
            ImportError: If llama-cpp-python is not installed
            FileNotFoundError: If the model file is not found
            Exception: For other loading errors
        """
        # Only import when actually loading the model
        if self.Llama is None:
            try:
                from llama_cpp import Llama
                self.Llama = Llama
            except ImportError:
                raise ImportError(
                    "llama-cpp-python is not installed. "
                    "Please install it with: pip install llama-cpp-python"
                )
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        # Check if running on macOS with Apple Silicon
        is_apple_silicon = False
        try:
            import platform
            is_apple_silicon = (
                platform.system() == "Darwin" and 
                platform.processor() == "arm"
            )
        except:
            pass
        
        # Configure model parameters
        model_params = {
            "model_path": self.model_path,
            "n_ctx": self.context_length,
            "verbose": self.verbose
        }
        
        # Add Metal acceleration for Apple Silicon
        if is_apple_silicon:
            model_params["n_gpu_layers"] = self.n_gpu_layers
            model_params["n_batch"] = self.n_batch
        
        # Load the model
        try:
            model = self.Llama(**model_params)
            return model
        except Exception as e:
            raise Exception(f"Failed to load model: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.
        
        Returns:
            Dict containing model information
        """
        return {
            "model_path": self.model_path,
            "context_length": self.context_length,
            "temperature": self.temperature,
            "n_gpu_layers": self.n_gpu_layers,
            "n_batch": self.n_batch
        }
