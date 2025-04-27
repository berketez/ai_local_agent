#!/usr/bin/env python3
"""
Test script for AI Helper components
"""

import os
import sys
import unittest

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Import components for testing
from registry import PermissionRegistry
from manager import PermissionManager
from files import FileController


class TestPermissionRegistry(unittest.TestCase):
    """Test cases for the PermissionRegistry class."""
    
    def setUp(self):
        """Set up test environment."""
        # Use a temporary directory for testing
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_config")
        os.makedirs(self.test_dir, exist_ok=True)
        self.registry = PermissionRegistry(self.test_dir)
    
    def tearDown(self):
        """Clean up after tests."""
        # Clean up test files
        permissions_file = os.path.join(self.test_dir, "permissions.json")
        if os.path.exists(permissions_file):
            os.remove(permissions_file)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)
    
    def test_set_get_category_permission(self):
        """Test setting and getting category permissions."""
        # Initially permission should not be granted
        self.assertFalse(self.registry.get_category_permission("browser"))
        
        # Set permission
        self.registry.set_category_permission("browser", True)
        
        # Check if permission is granted
        self.assertTrue(self.registry.get_category_permission("browser"))
        
        # Revoke permission
        self.registry.set_category_permission("browser", False)
        
        # Check if permission is revoked
        self.assertFalse(self.registry.get_category_permission("browser"))
    
    def test_permission_expiration(self):
        """Test permission expiration."""
        # Set permission with immediate expiration
        self.registry.set_category_permission("browser", True, expiration=0)
        
        # Check if permission is expired
        self.assertTrue(self.registry.check_permission_expired("browser"))
        
        # Set permission with future expiration
        future_time = int(time.time()) + 3600  # 1 hour in the future
        self.registry.set_category_permission("browser", True, expiration=future_time)
        
        # Check if permission is not expired
        self.assertFalse(self.registry.check_permission_expired("browser"))

class TestPermissionManager(unittest.TestCase):
    """Test cases for the PermissionManager class."""
    
    def setUp(self):
        """Set up test environment."""
        # Use a temporary directory for testing
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_config")
        os.makedirs(self.test_dir, exist_ok=True)
        self.manager = PermissionManager(self.test_dir)
    
    def tearDown(self):
        """Clean up after tests."""
        # Clean up test files
        permissions_file = os.path.join(self.test_dir, "permissions.json")
        if os.path.exists(permissions_file):
            os.remove(permissions_file)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)
    
    def test_check_permission(self):
        """Test checking permissions for actions."""
        # Initially permission should not be granted
        self.assertFalse(self.manager.check_permission("browser_open"))
        
        # Grant permission
        self.manager.grant_permission("browser_open")
        
        # Check if permission is granted
        self.assertTrue(self.manager.check_permission("browser_open"))
        
        # Revoke permission
        self.manager.revoke_permission("browser_open", revoke_category=True)
        
        # Check if permission is revoked
        self.assertFalse(self.manager.check_permission("browser_open"))
    
    def test_get_macos_requirements(self):
        """Test getting macOS requirements for actions."""
        # Check browser action requirements
        requirements = self.manager.get_macos_requirements("browser_open")
        self.assertIn("Automation", requirements)
        
        # Check input action requirements
        requirements = self.manager.get_macos_requirements("keyboard_type")
        self.assertIn("Accessibility", requirements)
        
        # Check screen action requirements
        requirements = self.manager.get_macos_requirements("screen_capture")
        self.assertIn("Screen Recording", requirements)

class TestFileController(unittest.TestCase):
    """Test cases for the FileController class."""
    
    def setUp(self):
        """Set up test environment."""
        self.controller = FileController()
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_files")
        os.makedirs(self.test_dir, exist_ok=True)
        self.test_file = os.path.join(self.test_dir, "test.txt")
    
    def tearDown(self):
        """Clean up after tests."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)
    
    def test_write_read_file(self):
        """Test writing to and reading from a file."""
        # Write to file
        content = "Hello, world!"
        result = self.controller.write_file(self.test_file, content)
        self.assertTrue(result["success"])
        
        # Read from file
        result = self.controller.read_file(self.test_file)
        self.assertTrue(result["success"])
        self.assertEqual(result["content"], content)
    
    def test_append_file(self):
        """Test appending to a file."""
        # Write initial content
        initial_content = "Line 1\n"
        self.controller.write_file(self.test_file, initial_content)
        
        # Append to file
        append_content = "Line 2\n"
        result = self.controller.write_file(self.test_file, append_content, append=True)
        self.assertTrue(result["success"])
        
        # Read combined content
        result = self.controller.read_file(self.test_file)
        self.assertTrue(result["success"])
        self.assertEqual(result["content"], initial_content + append_content)
    
    def test_list_directory(self):
        """Test listing directory contents."""
        # Create a test file
        self.controller.write_file(self.test_file, "Test content")
        
        # List directory
        result = self.controller.list_directory(self.test_dir)
        self.assertTrue(result["success"])
        
        # Check if test file is in the list
        file_found = False
        for item in result["contents"]:
            if item["name"] == os.path.basename(self.test_file):
                file_found = True
                self.assertFalse(item["is_directory"])
                break
        
        self.assertTrue(file_found)

if __name__ == "__main__":
    import time  # Import here to avoid issues with TestPermissionRegistry
    unittest.main()
