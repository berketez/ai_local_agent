# secure_terminal.py

"""
Secure Terminal Module - Handles secure terminal command execution

This module provides functionality to execute terminal commands securely,
requesting user confirmation before execution and handling outputs.
"""

import subprocess
import shlex
from typing import Dict, Any

# Assuming TerminalUI is in a separate file or integrated elsewhere
# For now, we'll use basic print/input for confirmation

def request_confirmation_basic(command: str) -> bool:
    """Basic confirmation prompt using input()."""
    response = input(f"PERMISSION REQUEST: Execute command \"{command}\"? (y/n): ")
    return response.lower() in ("y", "yes")

class SecureTerminalExecutor:
    """Executes terminal commands securely with user confirmation."""

    def __init__(self, confirmation_callback=request_confirmation_basic):
        """Initialize the secure terminal executor."""
        self.confirmation_callback = confirmation_callback

    def execute_command(self, command: str, require_confirmation: bool = True) -> Dict[str, Any]:
        """
        Execute a terminal command after optional user confirmation.

        Args:
            command: The command string to execute.
            require_confirmation: Whether to ask for user confirmation before execution.

        Returns:
            Dictionary containing execution results (success, stdout, stderr, return_code).
        """
        
        # Basic security check: prevent obviously dangerous patterns
        # This is NOT exhaustive and should be improved
        dangerous_patterns = ["rm -rf /", "mkfs", ":(){:|:&};:"] # Example patterns
        if any(pattern in command for pattern in dangerous_patterns):
            return {
                "success": False,
                "error": "Command blocked due to potential security risk.",
                "stdout": "",
                "stderr": "Command blocked.",
                "return_code": -1
            }

        # Request confirmation if required
        if require_confirmation:
            if not self.confirmation_callback(command):
                return {
                    "success": False,
                    "error": "User denied permission.",
                    "stdout": "",
                    "stderr": "Execution cancelled by user.",
                    "return_code": -1
                }

        try:
            # Use shlex to parse the command safely
            args = shlex.split(command)
            
            # Execute the command
            process = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False, # Don't raise exception on non-zero exit code
                timeout=60 # Add a timeout for safety
            )

            return {
                "success": process.returncode == 0,
                "stdout": process.stdout.strip(),
                "stderr": process.stderr.strip(),
                "return_code": process.returncode
            }

        except FileNotFoundError:
             return {
                "success": False,
                "error": f"Command not found: {args[0]}",
                "stdout": "",
                "stderr": f"Command not found: {args[0]}",
                "return_code": -1
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out after 60 seconds.",
                "stdout": "",
                "stderr": "Timeout expired.",
                "return_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error executing command: {e}",
                "stdout": "",
                "stderr": str(e),
                "return_code": -1
            }

# Example Usage (for testing)
if __name__ == '__main__':
    print("Testing SecureTerminalExecutor...")
    executor = SecureTerminalExecutor()

    # Test 1: Simple command (requires confirmation)
    print("\nTesting 'ls -l *.py'...")
    result1 = executor.execute_command("ls -l *.py")
    print(result1)
    if result1["success"]:
        print("Command executed successfully.")
        print("Output:\n", result1["stdout"])
    else:
        print(f"Command failed: {result1['error']}")

    # Test 2: Command that might fail (requires confirmation)
    print("\nTesting 'cat non_existent_file.txt'...")
    result2 = executor.execute_command("cat non_existent_file.txt")
    print(result2)
    if not result2["success"]:
        print(f"Command failed as expected: {result2['error']}")
        print("Stderr:\n", result2["stderr"])

    # Test 3: Command without confirmation
    print("\nTesting 'echo Hello World' without confirmation...")
    result3 = executor.execute_command("echo Hello World", require_confirmation=False)
    print(result3)
    if result3["success"]:
        print("Command executed successfully.")
        print("Output:\n", result3["stdout"])

    # Test 4: Potentially dangerous command (should be blocked)
    # print("\nTesting 'rm -rf /' (should be blocked)...")
    # result4 = executor.execute_command("rm -rf /")
    # print(result4)
    # if not result4["success"] and "blocked" in result4["error"]:
    #     print("Command blocked as expected.")
    # else:
    #     print("Error: Dangerous command was not blocked!")

