"""
Apps Module - Handles application control on macOS

This module provides functionality to open, close, and control
applications on macOS using AppleScript and other automation techniques.
"""

import subprocess
from typing import Dict, Any

class AppController:
    """Controls applications on macOS."""
    
    def __init__(self):
        """Initialize the application controller."""
        pass
    
    def open_app(self, app_name: str) -> Dict[str, Any]:
        """
        Open an application.
        
        Args:
            app_name: Name of the application to open
            
        Returns:
            Result dictionary
        """
        # Use AppleScript to open the application
        script = f'''
        tell application "{app_name}"
            activate
        end tell
        '''
        
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                check=True
            )
            return {
                "success": True,
                "message": f"Successfully opened application: {app_name}"
            }
        except subprocess.CalledProcessError:
            return {
                "success": False,
                "message": f"Failed to open application: {app_name}"
            }
    
    def close_app(self, app_name: str) -> Dict[str, Any]:
        """
        Close an application.
        
        Args:
            app_name: Name of the application to close
            
        Returns:
            Result dictionary
        """
        # Use AppleScript to quit the application
        script = f'''
        tell application "{app_name}"
            quit
        end tell
        '''
        
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                check=True
            )
            return {
                "success": True,
                "message": f"Successfully closed application: {app_name}"
            }
        except subprocess.CalledProcessError:
            return {
                "success": False,
                "message": f"Failed to close application: {app_name}"
            }
    
    def list_running_apps(self) -> Dict[str, Any]:
        """
        List all running applications.
        
        Returns:
            Result dictionary with list of running applications
        """
        # Use AppleScript to get list of running applications
        script = '''
        tell application "System Events"
            set appList to name of every process where background only is false
        end tell
        return appList
        '''
        
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse the output (comma-separated list)
            apps = [app.strip() for app in result.stdout.split(",")]
            
            return {
                "success": True,
                "apps": apps,
                "message": f"Found {len(apps)} running applications"
            }
        except subprocess.CalledProcessError:
            return {
                "success": False,
                "apps": [],
                "message": "Failed to list running applications"
            }
    
    def execute_app_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an application action.
        
        Args:
            action: The action to perform (open, close, list)
            params: Parameters for the action
            
        Returns:
            Result dictionary
        """
        if action == "app_open":
            app_name = params.get("app_name", "")
            return self.open_app(app_name)
        
        elif action == "app_close":
            app_name = params.get("app_name", "")
            return self.close_app(app_name)
        
        elif action == "app_list":
            return self.list_running_apps()
        
        else:
            return {
                "success": False,
                "message": f"Unknown application action: {action}"
            }
