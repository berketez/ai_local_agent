"""
Files Module - Handles file system operations on macOS

This module provides functionality to interact with the file system
on macOS, including reading, writing, and managing files.
"""

import os
from typing import Dict, Any

class FileController:
    """Controls file system operations on macOS."""
    
    def __init__(self):
        """Initialize the file controller."""
        self.home_dir = os.path.expanduser("~")
    
    def read_file(self, file_path: str) -> Dict[str, Any]:
        """
        Read the contents of a file.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            Result dictionary with content if successful
        """
        # Expand ~ to user's home directory if present
        if file_path.startswith("~"):
            file_path = os.path.expanduser(file_path)
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "message": f"Successfully read file: {file_path}"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "content": None,
                "message": f"File not found: {file_path}"
            }
        except PermissionError:
            return {
                "success": False,
                "content": None,
                "message": f"Permission denied for file: {file_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "content": None,
                "message": f"Error reading file: {str(e)}"
            }
    
    def write_file(self, file_path: str, content: str, append: bool = False) -> Dict[str, Any]:
        """
        Write content to a file.
        
        Args:
            file_path: Path to the file to write
            content: Content to write to the file
            append: Whether to append to the file (default: False)
            
        Returns:
            Result dictionary
        """
        # Expand ~ to user's home directory if present
        if file_path.startswith("~"):
            file_path = os.path.expanduser(file_path)
        
        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        
        try:
            mode = 'a' if append else 'w'
            with open(file_path, mode) as f:
                f.write(content)
            
            return {
                "success": True,
                "message": f"Successfully {'appended to' if append else 'wrote'} file: {file_path}"
            }
        except PermissionError:
            return {
                "success": False,
                "message": f"Permission denied for file: {file_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error writing to file: {str(e)}"
            }
    
    def delete_file(self, file_path: str) -> Dict[str, Any]:
        """
        Delete a file.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            Result dictionary
        """
        # Expand ~ to user's home directory if present
        if file_path.startswith("~"):
            file_path = os.path.expanduser(file_path)
        
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                return {
                    "success": True,
                    "message": f"Successfully deleted file: {file_path}"
                }
            elif os.path.isdir(file_path):
                return {
                    "success": False,
                    "message": f"Cannot delete directory with this method: {file_path}"
                }
            else:
                return {
                    "success": False,
                    "message": f"File not found: {file_path}"
                }
        except PermissionError:
            return {
                "success": False,
                "message": f"Permission denied for file: {file_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error deleting file: {str(e)}"
            }
    
    def list_directory(self, dir_path: str) -> Dict[str, Any]:
        """
        List contents of a directory.
        
        Args:
            dir_path: Path to the directory to list
            
        Returns:
            Result dictionary with directory contents if successful
        """
        # Expand ~ to user's home directory if present
        if dir_path.startswith("~"):
            dir_path = os.path.expanduser(dir_path)
        
        try:
            if not os.path.isdir(dir_path):
                return {
                    "success": False,
                    "contents": None,
                    "message": f"Not a directory: {dir_path}"
                }
            
            contents = os.listdir(dir_path)
            
            # Get additional info about each item
            items = []
            for item in contents:
                item_path = os.path.join(dir_path, item)
                is_dir = os.path.isdir(item_path)
                items.append({
                    "name": item,
                    "is_directory": is_dir,
                    "type": "directory" if is_dir else "file"
                })
            
            return {
                "success": True,
                "contents": items,
                "message": f"Successfully listed directory: {dir_path}"
            }
        except PermissionError:
            return {
                "success": False,
                "contents": None,
                "message": f"Permission denied for directory: {dir_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "contents": None,
                "message": f"Error listing directory: {str(e)}"
            }
    
    def execute_file_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a file system action.
        
        Args:
            action: The action to perform (read, write, delete, list)
            params: Parameters for the action
            
        Returns:
            Result dictionary
        """
        if action == "file_read":
            file_path = params.get("path", "")
            return self.read_file(file_path)
        
        elif action == "file_write":
            file_path = params.get("path", "")
            content = params.get("content", "")
            append = params.get("append", False)
            return self.write_file(file_path, content, append)
        
        elif action == "file_delete":
            file_path = params.get("path", "")
            return self.delete_file(file_path)
        
        elif action == "file_list":
            dir_path = params.get("path", "")
            return self.list_directory(dir_path)
        
        else:
            return {
                "success": False,
                "message": f"Unknown file action: {action}"
            }
