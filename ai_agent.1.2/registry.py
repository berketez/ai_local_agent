"""
Permission Registry - Handles storage and retrieval of permission settings

This module provides functionality to store and retrieve permission settings
in a persistent way, with support for expiration and revocation.
"""

import os
import json
import time
from typing import Dict,Any, Optional

class PermissionRegistry:
    """Manages storage and retrieval of permission settings."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the permission registry.
        
        Args:
            config_dir: Directory to store permission configuration
                        (defaults to ~/.ai_helper)
        """
        if config_dir is None:
            home_dir = os.path.expanduser("~")
            self.config_dir = os.path.join(home_dir, ".ai_helper")
        else:
            self.config_dir = config_dir
            
        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
        
        self.permissions_file = os.path.join(self.config_dir, "permissions.json")
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict[str, Any]:
        """
        Load permission registry from the configuration file.
        
        Returns:
            Dictionary of permission settings
        """
        if os.path.exists(self.permissions_file):
            try:
                with open(self.permissions_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If file is corrupted or can't be read, return empty dict
                return {
                    "categories": {},
                    "actions": {},
                    "last_updated": int(time.time())
                }
        return {
            "categories": {},
            "actions": {},
            "last_updated": int(time.time())
        }
    
    def _save_registry(self):
        """Save permission registry to the configuration file."""
        try:
            # Update the last_updated timestamp
            self.registry["last_updated"] = int(time.time())
            
            with open(self.permissions_file, 'w') as f:
                json.dump(self.registry, f, indent=2)
        except IOError:
            # If file can't be written, just continue
            pass
    
    def get_category_permission(self, category: str) -> bool:
        """
        Get permission status for a category.
        
        Args:
            category: The permission category
            
        Returns:
            True if permission is granted, False otherwise
        """
        return self.registry.get("categories", {}).get(category, {}).get("granted", False)
    
    def set_category_permission(self, category: str, granted: bool, expiration: Optional[int] = None):
        """
        Set permission status for a category.
        
        Args:
            category: The permission category
            granted: Whether permission is granted
            expiration: Optional expiration time (Unix timestamp)
        """
        if "categories" not in self.registry:
            self.registry["categories"] = {}
        
        self.registry["categories"][category] = {
            "granted": granted,
            "timestamp": int(time.time()),
            "expiration": expiration
        }
        
        self._save_registry()
    
    def get_action_permission(self, action: str) -> bool:
        """
        Get permission status for a specific action.
        
        Args:
            action: The action type
            
        Returns:
            True if permission is granted, False otherwise
        """
        return self.registry.get("actions", {}).get(action, {}).get("granted", False)
    
    def set_action_permission(self, action: str, granted: bool, expiration: Optional[int] = None):
        """
        Set permission status for a specific action.
        
        Args:
            action: The action type
            granted: Whether permission is granted
            expiration: Optional expiration time (Unix timestamp)
        """
        if "actions" not in self.registry:
            self.registry["actions"] = {}
        
        self.registry["actions"][action] = {
            "granted": granted,
            "timestamp": int(time.time()),
            "expiration": expiration
        }
        
        self._save_registry()
    
    def check_permission_expired(self, category_or_action: str, is_category: bool = True) -> bool:
        """
        Check if a permission has expired.
        
        Args:
            category_or_action: The category or action to check
            is_category: Whether this is a category (True) or action (False)
            
        Returns:
            True if permission has expired, False otherwise
        """
        section = "categories" if is_category else "actions"
        item = self.registry.get(section, {}).get(category_or_action, {})
        
        if not item:
            return True
        
        expiration = item.get("expiration")
        if expiration is None:
            return False
        
        return int(time.time()) > expiration
    
    def revoke_all_permissions(self):
        """Revoke all permissions."""
        self.registry = {
            "categories": {},
            "actions": {},
            "last_updated": int(time.time())
        }
        self._save_registry()
    
    def get_all_permissions(self) -> Dict[str, Any]:
        """
        Get all permission settings.
        
        Returns:
            Dictionary of all permission settings
        """
        return self.registry
    
    def cleanup_expired_permissions(self):
        """Remove expired permissions from the registry."""
        current_time = int(time.time())
        
        # Clean up categories
        if "categories" in self.registry:
            for category, info in list(self.registry["categories"].items()):
                expiration = info.get("expiration")
                if expiration is not None and current_time > expiration:
                    del self.registry["categories"][category]
        
        # Clean up actions
        if "actions" in self.registry:
            for action, info in list(self.registry["actions"].items()):
                expiration = info.get("expiration")
                if expiration is not None and current_time > expiration:
                    del self.registry["actions"][action]
        
        self._save_registry()
