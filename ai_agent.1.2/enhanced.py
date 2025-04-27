"""
Enhanced Permission Manager - Updated for Ollama and LM Studio integration

This module provides enhanced permission management features for the AI Helper,
updated to work with both Ollama and LM Studio backends.
"""

from typing import List

from manager import PermissionManager

class EnhancedPermissionManager:
    """Enhanced permission management system for AI Helper."""
    
    def __init__(self, base_manager: PermissionManager):
        """
        Initialize the enhanced permission manager.
        
        Args:
            base_manager: Base permission manager instance
        """
        self.base_manager = base_manager
    
    def request_temporary_permission(self, action: str, duration: int = 300) -> bool:
        """
        Request temporary permission for an action.
        
        Args:
            action: The action to request permission for
            duration: Duration in seconds for the temporary permission
            
        Returns:
            True if permission is granted, False otherwise
        """
        category = self.base_manager.get_category_for_action(action)
        if category is None:
            return False
        
        # Format duration for display
        duration_str = f"{duration // 60} minutes" if duration >= 60 else f"{duration} seconds"
        
        # Request permission with reason
        reason = f"Temporary permission for {duration_str}"
        granted = self.base_manager.request_permission(action, reason)
        
        if granted:
            # Grant temporary permission
            self.base_manager.grant_permission(action, temporary=True, duration=duration)
        
        return granted
    
    def check_llm_backend_permission(self, backend_type: str) -> bool:
        """
        Check if a specific LLM backend is permitted.
        
        Args:
            backend_type: Type of LLM backend ('ollama', 'lmstudio_sdk', 'lmstudio_openai')
            
        Returns:
            True if the backend is permitted, False otherwise
        """
        # Map backend types to permission actions
        backend_actions = {
            "ollama": "llm_chat",
            "lmstudio_sdk": "llm_chat",
            "lmstudio_openai": "llm_chat"
        }
        
        action = backend_actions.get(backend_type)
        if action is None:
            return False
        
        return self.base_manager.check_permission(action)
    
    def request_llm_backend_permission(self, backend_type: str) -> bool:
        """
        Request permission for a specific LLM backend.
        
        Args:
            backend_type: Type of LLM backend ('ollama', 'lmstudio_sdk', 'lmstudio_openai')
            
        Returns:
            True if permission is granted, False otherwise
        """
        # Map backend types to permission actions and reasons
        backend_info = {
            "ollama": {
                "action": "llm_chat",
                "reason": "Use Ollama for local LLM inference"
            },
            "lmstudio_sdk": {
                "action": "llm_chat",
                "reason": "Use LM Studio SDK for local LLM inference"
            },
            "lmstudio_openai": {
                "action": "llm_chat",
                "reason": "Use LM Studio OpenAI API for local LLM inference"
            }
        }
        
        info = backend_info.get(backend_type)
        if info is None:
            return False
        
        return self.base_manager.request_permission(info["action"], info["reason"])
    
    def get_permitted_backends(self) -> List[str]:
        """
        Get list of permitted LLM backends.
        
        Returns:
            List of permitted backend types
        """
        permitted = []
        
        # Check each backend type
        for backend_type in ["ollama", "lmstudio_sdk", "lmstudio_openai"]:
            if self.check_llm_backend_permission(backend_type):
                permitted.append(backend_type)
        
        return permitted
