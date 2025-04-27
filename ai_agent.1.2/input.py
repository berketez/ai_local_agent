"""
Input Module - Handles keyboard and mouse input simulation on macOS

This module provides functionality to simulate keyboard and mouse input
on macOS using PyAutoGUI and other automation techniques.
"""
import sys
import subprocess
from typing import Optional,Dict, Any

class InputController:
    """Controls keyboard and mouse input on macOS."""
    
    def __init__(self):
        """Initialize the input controller."""
        self.pyautogui_available = self._check_pyautogui()
    
    def _check_pyautogui(self) -> bool:
        """
        Check if PyAutoGUI is available.
        
        Returns:
            True if PyAutoGUI is available, False otherwise
        """
        try:
            import pyautogui
            return True
        except ImportError:
            return False
    
    def _ensure_pyautogui(self) -> bool:
        """
        Ensure PyAutoGUI is available, attempt to install if not.
        
        Returns:
            True if PyAutoGUI is available after check/install, False otherwise
        """
        if self.pyautogui_available:
            return True
        
        try:
            # Attempt to install PyAutoGUI
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pyautogui"],
                check=True
            )
            
            # Check again
            import pyautogui
            self.pyautogui_available = True
            return True
        except (ImportError, subprocess.CalledProcessError):
            return False
    
    def type_text(self, text: str) -> Dict[str, Any]:
        """
        Type text using keyboard simulation.
        
        Args:
            text: Text to type
            
        Returns:
            Result dictionary
        """
        if not self._ensure_pyautogui():
            return {
                "success": False,
                "message": "PyAutoGUI is not available. Please install it with: pip install pyautogui"
            }
        
        try:
            import pyautogui
            pyautogui.write(text)
            return {
                "success": True,
                "message": f"Successfully typed text: {text[:20]}..." if len(text) > 20 else f"Successfully typed text: {text}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error typing text: {str(e)}"
            }
    
    def press_key(self, key: str) -> Dict[str, Any]:
        """
        Press a keyboard key.
        
        Args:
            key: Key to press (e.g., 'enter', 'tab', 'esc')
            
        Returns:
            Result dictionary
        """
        if not self._ensure_pyautogui():
            return {
                "success": False,
                "message": "PyAutoGUI is not available. Please install it with: pip install pyautogui"
            }
        
        try:
            import pyautogui
            pyautogui.press(key)
            return {
                "success": True,
                "message": f"Successfully pressed key: {key}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error pressing key: {str(e)}"
            }
    
    def mouse_move(self, x: int, y: int) -> Dict[str, Any]:
        """
        Move mouse cursor to specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Result dictionary
        """
        if not self._ensure_pyautogui():
            return {
                "success": False,
                "message": "PyAutoGUI is not available. Please install it with: pip install pyautogui"
            }
        
        try:
            import pyautogui
            pyautogui.moveTo(x, y)
            return {
                "success": True,
                "message": f"Successfully moved mouse to coordinates: ({x}, {y})"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error moving mouse: {str(e)}"
            }
    
    def mouse_click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left") -> Dict[str, Any]:
        """
        Perform mouse click at current or specified position.
        
        Args:
            x: Optional X coordinate
            y: Optional Y coordinate
            button: Mouse button to click ('left', 'right', 'middle')
            
        Returns:
            Result dictionary
        """
        if not self._ensure_pyautogui():
            return {
                "success": False,
                "message": "PyAutoGUI is not available. Please install it with: pip install pyautogui"
            }
        
        try:
            import pyautogui
            
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button)
                message = f"Successfully clicked {button} button at coordinates: ({x}, {y})"
            else:
                pyautogui.click(button=button)
                message = f"Successfully clicked {button} button at current position"
            
            return {
                "success": True,
                "message": message
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error clicking mouse: {str(e)}"
            }
    
    def get_mouse_position(self) -> Dict[str, Any]:
        """
        Get current mouse cursor position.
        
        Returns:
            Result dictionary with current coordinates
        """
        if not self._ensure_pyautogui():
            return {
                "success": False,
                "position": None,
                "message": "PyAutoGUI is not available. Please install it with: pip install pyautogui"
            }
        
        try:
            import pyautogui
            x, y = pyautogui.position()
            return {
                "success": True,
                "position": {"x": x, "y": y},
                "message": f"Current mouse position: ({x}, {y})"
            }
        except Exception as e:
            return {
                "success": False,
                "position": None,
                "message": f"Error getting mouse position: {str(e)}"
            }
    
    def execute_input_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an input action.
        
        Args:
            action: The action to perform (type, press, move, click)
            params: Parameters for the action
            
        Returns:
            Result dictionary
        """
        if action == "keyboard_type":
            text = params.get("text", "")
            return self.type_text(text)
        
        elif action == "keyboard_press":
            key = params.get("key", "")
            return self.press_key(key)
        
        elif action == "mouse_move":
            x = params.get("x", 0)
            y = params.get("y", 0)
            return self.mouse_move(x, y)
        
        elif action == "mouse_click":
            x = params.get("x")
            y = params.get("y")
            button = params.get("button", "left")
            return self.mouse_click(x, y, button)
        
        elif action == "mouse_position":
            return self.get_mouse_position()
        
        else:
            return {
                "success": False,
                "message": f"Unknown input action: {action}"
            }
