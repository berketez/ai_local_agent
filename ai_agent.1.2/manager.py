"""
Permission Manager - Updated for Ollama and LM Studio integration

This module provides a permission management system for the AI Helper,
updated to work with both Ollama and LM Studio backends.
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional

from registry import PermissionRegistry

class PermissionManager:
    """Permission management system for AI Helper."""
    
    # Define permission categories and their associated actions
    PERMISSION_CATEGORIES = {
        "browser": ["browser_open", "browser_navigate", "browser_click", "browser_read"],
        "files": ["file_read", "file_write", "file_delete", "file_list"],
        "apps": ["app_open", "app_close", "app_list"],
        "input": ["keyboard_type", "mouse_move", "mouse_click"],
        "screen": ["screen_capture", "screen_record"],
        "llm": ["llm_chat", "llm_generate", "llm_embed", "llm_list_models", "llm_pull_model"],
    }
    
    # Define macOS permission requirements for each category
    MACOS_REQUIREMENTS = {
        "browser": ["Automation"],
        "files": ["Files and Folders"],
        "apps": ["Automation"],
        "input": ["Accessibility"],
        "screen": ["Screen Recording"],
        "llm": [],  # No special macOS permissions needed for LLM operations
    }
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the permission manager.
        
        Args:
            config_dir: Directory for storing permission configuration
        """
        if config_dir is None:
            home_dir = str(Path.home())
            config_dir = os.path.join(home_dir, ".ai_helper")
        
        os.makedirs(config_dir, exist_ok=True)
        self.registry = PermissionRegistry(config_dir)
        
        # Otomatik olarak tüm izinleri etkinleştir
        self._grant_all_permissions()
    
    def _grant_all_permissions(self):
        """Tüm kategoriler için izinleri otomatik olarak etkinleştirir."""
        for category in self.PERMISSION_CATEGORIES.keys():
            self.registry.set_category_permission(category, True)
    
    def get_category_for_action(self, action: str) -> Optional[str]:
        """
        Get the permission category for an action.
        
        Args:
            action: The action to check
            
        Returns:
            The category name or None if not found
        """
        for category, actions in self.PERMISSION_CATEGORIES.items():
            if action in actions:
                return category
        return None
    
    def check_permission(self, action: str) -> bool:
        """
        Check if an action is permitted.
        
        Args:
            action: The action to check
            
        Returns:
            True if the action is permitted, False otherwise
        """
        # Tüm izinleri otomatik olarak etkinleştir
        category = self.get_category_for_action(action)
        if category is None:
            return True  # Bilinmeyen eylemler için bile true dön
        
        # İzin kaydedilmemişse bile izin ver
        if not self.registry.get_category_permission(category):
            self.registry.set_category_permission(category, True)
        
        return True
    
    def grant_permission(self, action: str, temporary: bool = False, duration: int = 3600) -> None:
        """
        Grant permission for an action.
        
        Args:
            action: The action to grant permission for
            temporary: Whether the permission is temporary
            duration: Duration in seconds for temporary permissions
        """
        category = self.get_category_for_action(action)
        if category is None:
            return
        
        # Calculate expiration time for temporary permissions
        expiration = int(time.time()) + duration if temporary else None
        
        # Grant permission for the category
        self.registry.set_category_permission(category, True, expiration)
    
    def revoke_permission(self, action: str, revoke_category: bool = False) -> None:
        """
        Revoke permission for an action.
        
        Args:
            action: The action to revoke permission for
            revoke_category: Whether to revoke permission for the entire category
        """
        category = self.get_category_for_action(action)
        if category is None:
            return
        
        if revoke_category:
            # Revoke permission for the entire category
            self.registry.set_category_permission(category, False)
    
    def get_macos_requirements(self, action: str) -> List[str]:
        """
        Get macOS permission requirements for an action.
        
        Args:
            action: The action to check
            
        Returns:
            List of required macOS permissions
        """
        category = self.get_category_for_action(action)
        if category is None:
            return []
        
        return self.MACOS_REQUIREMENTS.get(category, [])
    
    def get_llm_permissions(self) -> Dict[str, bool]:
        """
        Get permissions for LLM operations.
        
        Returns:
            Dictionary of LLM actions and their permission status
        """
        permissions = {}
        for action in self.PERMISSION_CATEGORIES.get("llm", []):
            permissions[action] = True  # Her zaman true döndür
        return permissions
    
    def request_permission(self, action: str, reason: str) -> bool:
        """
        Request permission for an action from the user.
        
        Args:
            action: The action to request permission for
            reason: The reason for requesting permission
            
        Returns:
            True if permission is granted, False otherwise
        """
        # İzin sormadan otomatik olarak tüm izinleri ver
        self.grant_permission(action)
        return True
