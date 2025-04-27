#!/usr/bin/env python3
"""
Test script for AI Helper with Ollama and LM Studio integration
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Import components for testing
from base import BaseLLM
from ollama import OllamaLLM
from lmstudio import LMStudioSDK, LMStudioOpenAI
from factory import LLMFactory
from manager import PermissionManager
from enhanced import EnhancedPermissionManager

class TestLLMBackends(unittest.TestCase):
    """Test cases for the LLM backends."""
    
    def test_base_llm_interface(self):
        """Test that BaseLLM defines the required interface."""
        # BaseLLM is abstract, so we can't instantiate it directly
        # Instead, check that it has the required methods
        self.assertTrue(hasattr(BaseLLM, 'chat'))
        self.assertTrue(hasattr(BaseLLM, 'generate'))
        self.assertTrue(hasattr(BaseLLM, 'embed'))
        self.assertTrue(hasattr(BaseLLM, 'list_models'))
        self.assertTrue(hasattr(BaseLLM, 'is_available'))
        self.assertTrue(hasattr(BaseLLM, 'extract_text_from_response'))
    
    @patch('ollama.Client')
    def test_ollama_llm_initialization(self, mock_client):
        """Test OllamaLLM initialization."""
        # Configure the mock
        mock_client.return_value = MagicMock()
        
        # Create an OllamaLLM instance
        ollama = OllamaLLM("test-model", host="http://localhost:11434")
        
        # Check that the client was initialized correctly
        self.assertIsNotNone(ollama.ollama_client)
        mock_client.assert_called_once_with(host="http://localhost:11434")
    
    @patch('lmstudio.llm')
    def test_lmstudio_sdk_initialization(self, mock_llm):
        """Test LMStudioSDK initialization."""
        # Configure the mock
        mock_llm.return_value = MagicMock()
        
        # Create an LMStudioSDK instance
        lmstudio = LMStudioSDK("test-model")
        
        # Check that the client was initialized correctly
        self.assertIsNotNone(lmstudio.lmstudio_client)
    
    @patch('openai.OpenAI')
    def test_lmstudio_openai_initialization(self, mock_openai):
        """Test LMStudioOpenAI initialization."""
        # Configure the mock
        mock_openai.return_value = MagicMock()
        
        # Create an LMStudioOpenAI instance
        lmstudio = LMStudioOpenAI("test-model", base_url="http://localhost:1234/v1")
        
        # Check that the client was initialized correctly
        self.assertIsNotNone(lmstudio.openai_client)
        mock_openai.assert_called_once_with(base_url="http://localhost:1234/v1", api_key="lm-studio")

class TestLLMFactory(unittest.TestCase):
    """Test cases for the LLM factory."""
    
    @patch('llm.factory.OllamaLLM')
    def test_create_ollama(self, mock_ollama):
        """Test creating an Ollama backend."""
        # Configure the mock
        mock_ollama.return_value = MagicMock()
        
        # Create an Ollama backend
        llm = LLMFactory.create_llm("ollama", "test-model")
        
        # Check that the correct backend was created
        mock_ollama.assert_called_once_with("test-model")
    
    @patch('llm.factory.LMStudioSDK')
    def test_create_lmstudio_sdk(self, mock_lmstudio):
        """Test creating an LM Studio SDK backend."""
        # Configure the mock
        mock_lmstudio.return_value = MagicMock()
        
        # Create an LM Studio SDK backend
        llm = LLMFactory.create_llm("lmstudio_sdk", "test-model")
        
        # Check that the correct backend was created
        mock_lmstudio.assert_called_once_with("test-model")
    
    @patch('llm.factory.LMStudioOpenAI')
    def test_create_lmstudio_openai(self, mock_lmstudio):
        """Test creating an LM Studio OpenAI backend."""
        # Configure the mock
        mock_lmstudio.return_value = MagicMock()
        
        # Create an LM Studio OpenAI backend
        llm = LLMFactory.create_llm("lmstudio_openai", "test-model")
        
        # Check that the correct backend was created
        mock_lmstudio.assert_called_once_with("test-model")
    
    @patch('llm.factory.OllamaLLM')
    @patch('llm.factory.LMStudioSDK')
    @patch('llm.factory.LMStudioOpenAI')
    def test_create_auto(self, mock_lmstudio_openai, mock_lmstudio_sdk, mock_ollama):
        """Test automatic backend selection."""
        # Configure the mocks
        mock_ollama.return_value = MagicMock()
        mock_ollama.return_value.is_available.return_value = True
        
        mock_lmstudio_sdk.return_value = MagicMock()
        mock_lmstudio_sdk.return_value.is_available.return_value = False
        
        mock_lmstudio_openai.return_value = MagicMock()
        mock_lmstudio_openai.return_value.is_available.return_value = False
        
        # Create an auto backend
        llm = LLMFactory.create_llm("auto", "test-model")
        
        # Check that the correct backend was created
        mock_ollama.assert_called_once_with("test-model")
        mock_ollama.return_value.is_available.assert_called_once()

class TestPermissionSystem(unittest.TestCase):
    """Test cases for the permission system."""
    
    def setUp(self):
        """Set up test environment."""
        # Use a temporary directory for testing
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_config")
        os.makedirs(self.test_dir, exist_ok=True)
        self.manager = PermissionManager(self.test_dir)
        self.enhanced_manager = EnhancedPermissionManager(self.manager)
    
    def tearDown(self):
        """Clean up after tests."""
        # Clean up test files
        permissions_file = os.path.join(self.test_dir, "permissions.json")
        if os.path.exists(permissions_file):
            os.remove(permissions_file)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)
    
    def test_llm_permission_category(self):
        """Test that LLM permissions are defined."""
        # Check that the LLM category exists
        self.assertIn("llm", self.manager.PERMISSION_CATEGORIES)
        
        # Check that LLM actions are defined
        llm_actions = self.manager.PERMISSION_CATEGORIES["llm"]
        self.assertIn("llm_chat", llm_actions)
        self.assertIn("llm_generate", llm_actions)
        self.assertIn("llm_embed", llm_actions)
        self.assertIn("llm_list_models", llm_actions)
        self.assertIn("llm_pull_model", llm_actions)
    
    def test_get_llm_permissions(self):
        """Test getting LLM permissions."""
        # Initially all permissions should be false
        permissions = self.manager.get_llm_permissions()
        for action, granted in permissions.items():
            self.assertFalse(granted)
        
        # Grant a permission
        self.manager.grant_permission("llm_chat")
        
        # Check that the permission is granted
        permissions = self.manager.get_llm_permissions()
        self.assertTrue(permissions["llm_chat"])
    
    def test_check_llm_backend_permission(self):
        """Test checking LLM backend permissions."""
        # Initially all permissions should be false
        self.assertFalse(self.enhanced_manager.check_llm_backend_permission("ollama"))
        self.assertFalse(self.enhanced_manager.check_llm_backend_permission("lmstudio_sdk"))
        self.assertFalse(self.enhanced_manager.check_llm_backend_permission("lmstudio_openai"))
        
        # Grant a permission
        self.manager.grant_permission("llm_chat")
        
        # Check that the permission is granted for all backends
        self.assertTrue(self.enhanced_manager.check_llm_backend_permission("ollama"))
        self.assertTrue(self.enhanced_manager.check_llm_backend_permission("lmstudio_sdk"))
        self.assertTrue(self.enhanced_manager.check_llm_backend_permission("lmstudio_openai"))
    
    def test_get_permitted_backends(self):
        """Test getting permitted backends."""
        # Initially no backends should be permitted
        permitted = self.enhanced_manager.get_permitted_backends()
        self.assertEqual(len(permitted), 0)
        
        # Grant a permission
        self.manager.grant_permission("llm_chat")
        
        # Check that all backends are permitted
        permitted = self.enhanced_manager.get_permitted_backends()
        self.assertEqual(len(permitted), 3)
        self.assertIn("ollama", permitted)
        self.assertIn("lmstudio_sdk", permitted)
        self.assertIn("lmstudio_openai", permitted)

if __name__ == "__main__":
    unittest.main()
