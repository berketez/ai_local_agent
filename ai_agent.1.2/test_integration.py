"""
Integration test script for AI Helper with Ollama and LM Studio backends
"""

import os
import sys
import unittest
from unittest.mock import patch


# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Import components for testing
from factory import LLMFactory
from manager import PermissionManager
from enhanced import EnhancedPermissionManager

class MockOllamaLLM:
    """Mock Ollama LLM for testing."""
    
    def __init__(self, model_name, **kwargs):
        self.model_name = model_name
        self.kwargs = kwargs
    
    def chat(self, messages, stream=False, **kwargs):
        """Simulate chat response."""
        return {
            "message": {
                "content": "This is a mock response from Ollama."
            }
        }
    
    def is_available(self):
        """Always return True for testing."""
        return True

class MockLMStudioSDK:
    """Mock LM Studio SDK for testing."""
    
    def __init__(self, model_name, **kwargs):
        self.model_name = model_name
        self.kwargs = kwargs
    
    def chat(self, messages, stream=False, **kwargs):
        """Simulate chat response."""
        return {
            "message": {
                "content": "This is a mock response from LM Studio SDK."
            }
        }
    
    def is_available(self):
        """Always return True for testing."""
        return True

class MockLMStudioOpenAI:
    """Mock LM Studio OpenAI API for testing."""
    
    def __init__(self, model_name, **kwargs):
        self.model_name = model_name
        self.kwargs = kwargs
    
    def chat(self, messages, stream=False, **kwargs):
        """Simulate chat response."""
        return {
            "message": {
                "content": "This is a mock response from LM Studio OpenAI API."
            }
        }
    
    def is_available(self):
        """Always return True for testing."""
        return True

class TestIntegration(unittest.TestCase):
    """Integration tests for AI Helper with Ollama and LM Studio backends."""
    
    def setUp(self):
        """Set up test environment."""
        # Use a temporary directory for testing
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_integration")
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Create permission manager
        self.permission_manager = PermissionManager(self.test_dir)
        self.enhanced_manager = EnhancedPermissionManager(self.permission_manager)
        
        # Grant LLM permissions for testing
        self.permission_manager.grant_permission("llm_chat")
    
    def tearDown(self):
        """Clean up after tests."""
        # Clean up test files
        permissions_file = os.path.join(self.test_dir, "permissions.json")
        if os.path.exists(permissions_file):
            os.remove(permissions_file)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)
    
    @patch('llm.factory.OllamaLLM', MockOllamaLLM)
    def test_ollama_integration(self):
        """Test integration with Ollama backend."""
        # Create LLM backend
        llm = LLMFactory.create_llm("ollama", "test-model")
        
        # Check that the correct backend was created
        self.assertIsInstance(llm, MockOllamaLLM)
        self.assertEqual(llm.model_name, "test-model")
        
        # Check that the backend has permission
        self.assertTrue(self.enhanced_manager.check_llm_backend_permission("ollama"))
        
        # Test chat functionality
        messages = [{"role": "user", "content": "Hello"}]
        response = llm.chat(messages)
        
        # Check the response
        self.assertIn("message", response)
        self.assertIn("content", response["message"])
        self.assertEqual(response["message"]["content"], "This is a mock response from Ollama.")
    
    @patch('llm.factory.LMStudioSDK', MockLMStudioSDK)
    def test_lmstudio_sdk_integration(self):
        """Test integration with LM Studio SDK backend."""
        # Create LLM backend
        llm = LLMFactory.create_llm("lmstudio_sdk", "test-model")
        
        # Check that the correct backend was created
        self.assertIsInstance(llm, MockLMStudioSDK)
        self.assertEqual(llm.model_name, "test-model")
        
        # Check that the backend has permission
        self.assertTrue(self.enhanced_manager.check_llm_backend_permission("lmstudio_sdk"))
        
        # Test chat functionality
        messages = [{"role": "user", "content": "Hello"}]
        response = llm.chat(messages)
        
        # Check the response
        self.assertIn("message", response)
        self.assertIn("content", response["message"])
        self.assertEqual(response["message"]["content"], "This is a mock response from LM Studio SDK.")
    
    @patch('llm.factory.LMStudioOpenAI', MockLMStudioOpenAI)
    def test_lmstudio_openai_integration(self):
        """Test integration with LM Studio OpenAI API backend."""
        # Create LLM backend
        llm = LLMFactory.create_llm("lmstudio_openai", "test-model")
        
        # Check that the correct backend was created
        self.assertIsInstance(llm, MockLMStudioOpenAI)
        self.assertEqual(llm.model_name, "test-model")
        
        # Check that the backend has permission
        self.assertTrue(self.enhanced_manager.check_llm_backend_permission("lmstudio_openai"))
        
        # Test chat functionality
        messages = [{"role": "user", "content": "Hello"}]
        response = llm.chat(messages)
        
        # Check the response
        self.assertIn("message", response)
        self.assertIn("content", response["message"])
        self.assertEqual(response["message"]["content"], "This is a mock response from LM Studio OpenAI API.")
    
    @patch('llm.factory.OllamaLLM', MockOllamaLLM)
    @patch('llm.factory.LMStudioSDK', MockLMStudioSDK)
    @patch('llm.factory.LMStudioOpenAI', MockLMStudioOpenAI)
    def test_auto_backend_selection(self):
        """Test automatic backend selection."""
        # Create LLM backend with auto selection
        llm = LLMFactory.create_llm("auto", "test-model")
        
        # Check that a backend was created
        self.assertIsNotNone(llm)
        
        # Test chat functionality
        messages = [{"role": "user", "content": "Hello"}]
        response = llm.chat(messages)
        
        # Check the response
        self.assertIn("message", response)
        self.assertIn("content", response["message"])
    
    def test_permission_integration(self):
        """Test integration with permission system."""
        # Check that LLM permissions are granted
        self.assertTrue(self.permission_manager.check_permission("llm_chat"))
        
        # Check that all backends are permitted
        permitted = self.enhanced_manager.get_permitted_backends()
        self.assertIn("ollama", permitted)
        self.assertIn("lmstudio_sdk", permitted)
        self.assertIn("lmstudio_openai", permitted)
        
        # Revoke permission
        self.permission_manager.revoke_permission("llm_chat", revoke_category=True)
        
        # Check that permission is revoked
        self.assertFalse(self.permission_manager.check_permission("llm_chat"))
        
        # Check that no backends are permitted
        permitted = self.enhanced_manager.get_permitted_backends()
        self.assertEqual(len(permitted), 0)

if __name__ == "__main__":
    unittest.main()
