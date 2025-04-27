"""
Screen Module - Handles screen capture and analysis on macOS

This module provides functionality to capture and analyze screen content
on macOS using various libraries and techniques.
"""

import os
import subprocess
from typing import Optional, List, Dict, Any, Tuple
import sys

class ScreenController:
    """Controls screen capture and analysis on macOS."""
    
    def __init__(self):
        """Initialize the screen controller."""
        self.pyautogui_available = self._check_pyautogui()
        self.pillow_available = self._check_pillow()
        self.pytesseract_available = self._check_pytesseract()
    
    def _check_pyautogui(self) -> bool:
        """Check if PyAutoGUI is available."""
        try:
            import pyautogui
            return True
        except ImportError:
            return False
    
    def _check_pillow(self) -> bool:
        """Check if Pillow (PIL) is available."""
        try:
            from PIL import Image
            return True
        except ImportError:
            return False
    
    def _check_pytesseract(self) -> bool:
        """Check if pytesseract is available."""
        try:
            import pytesseract
            return True
        except ImportError:
            return False
    
    def _ensure_dependencies(self) -> Dict[str, bool]:
        """
        Ensure dependencies are available, attempt to install if not.
        
        Returns:
            Dictionary of dependency availability status
        """
        dependencies = {
            "pyautogui": self.pyautogui_available,
            "pillow": self.pillow_available,
            "pytesseract": self.pytesseract_available
        }
        
        if not self.pyautogui_available:
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "pyautogui"],
                    check=True
                )
                import pyautogui
                dependencies["pyautogui"] = True
                self.pyautogui_available = True
            except:
                pass
        
        if not self.pillow_available:
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "Pillow"],
                    check=True
                )
                from PIL import Image
                dependencies["pillow"] = True
                self.pillow_available = True
            except:
                pass
        
        if not self.pytesseract_available:
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "pytesseract"],
                    check=True
                )
                import pytesseract
                dependencies["pytesseract"] = True
                self.pytesseract_available = True
            except:
                pass
        
        return dependencies
    
    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        """
        Capture the screen or a region of it.
        
        Args:
            region: Optional tuple of (left, top, width, height) to capture
            
        Returns:
            Result dictionary with image data if successful
        """
        dependencies = self._ensure_dependencies()
        
        if not dependencies["pyautogui"] or not dependencies["pillow"]:
            return {
                "success": False,
                "image": None,
                "message": "Required dependencies not available. Please install PyAutoGUI and Pillow."
            }
        
        try:
            import pyautogui
            from PIL import Image
            
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()
            
            # Save to a temporary file
            temp_path = os.path.expanduser("~/screenshot_temp.png")
            screenshot.save(temp_path)
            
            return {
                "success": True,
                "image_path": temp_path,
                "message": f"Successfully captured {'region' if region else 'screen'}"
            }
        except Exception as e:
            return {
                "success": False,
                "image": None,
                "message": f"Error capturing screen: {str(e)}"
            }
    
    def read_text_from_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        """
        Capture the screen and extract text using OCR.
        
        Args:
            region: Optional tuple of (left, top, width, height) to capture
            
        Returns:
            Result dictionary with extracted text if successful
        """
        dependencies = self._ensure_dependencies()
        
        if not dependencies["pyautogui"] or not dependencies["pillow"] or not dependencies["pytesseract"]:
            return {
                "success": False,
                "text": None,
                "message": "Required dependencies not available. Please install PyAutoGUI, Pillow, and pytesseract."
            }
        
        try:
            # First capture the screen
            capture_result = self.capture_screen(region)
            
            if not capture_result["success"]:
                return {
                    "success": False,
                    "text": None,
                    "message": f"Failed to capture screen: {capture_result['message']}"
                }
            
            # Now extract text using pytesseract
            import pytesseract
            from PIL import Image
            
            image_path = capture_result["image_path"]
            image = Image.open(image_path)
            
            text = pytesseract.image_to_string(image)
            
            return {
                "success": True,
                "text": text,
                "message": "Successfully extracted text from screen"
            }
        except Exception as e:
            return {
                "success": False,
                "text": None,
                "message": f"Error extracting text from screen: {str(e)}"
            }
    
    def execute_screen_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a screen action.
        
        Args:
            action: The action to perform (capture, read_text)
            params: Parameters for the action
            
        Returns:
            Result dictionary
        """
        if action == "screen_capture":
            region = None
            if all(k in params for k in ["left", "top", "width", "height"]):
                region = (
                    params["left"],
                    params["top"],
                    params["width"],
                    params["height"]
                )
            return self.capture_screen(region)
        
        elif action == "screen_read_text":
            region = None
            if all(k in params for k in ["left", "top", "width", "height"]):
                region = (
                    params["left"],
                    params["top"],
                    params["width"],
                    params["height"]
                )
            return self.read_text_from_screen(region)
        
        else:
            return {
                "success": False,
                "message": f"Unknown screen action: {action}"
            }
