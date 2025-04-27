"""
Command Analyzer Module - Analyzes command outputs and suggests alternatives

This module provides functionality to analyze terminal command outputs,
detect errors, and suggest alternative commands when needed.
"""

import re
from typing import Dict, Any, List, Optional

class CommandAnalyzer:
    """Analyzes command outputs and suggests alternatives."""
    
    def __init__(self):
        """Initialize the command analyzer."""
        # Common error patterns and their potential solutions
        self.error_patterns = {
            # Command not found
            r"command not found": self._handle_command_not_found,
            r"is not recognized as": self._handle_command_not_found,
            
            # Permission errors
            r"permission denied": self._handle_permission_denied,
            r"Access is denied": self._handle_permission_denied,
            
            # File not found
            r"No such file or directory": self._handle_file_not_found,
            r"cannot find the path specified": self._handle_file_not_found,
            
            # Syntax errors
            r"syntax error": self._handle_syntax_error,
            r"invalid option": self._handle_invalid_option,
            r"unknown option": self._handle_invalid_option,
            
            # Package errors
            r"package .* not found": self._handle_package_not_found,
            r"module .* not found": self._handle_module_not_found,
            
            # Network errors
            r"network is unreachable": self._handle_network_error,
            r"connection refused": self._handle_network_error,
            r"could not resolve host": self._handle_network_error,
            
            # Disk space
            r"no space left on device": self._handle_disk_space,
            
            # Generic errors
            r"failed with exit code": self._handle_generic_error,
            r"error:": self._handle_generic_error,
            r"exception": self._handle_generic_error,
        }
    
    def analyze_command_result(self, command: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze command execution result and provide insights.
        
        Args:
            command: The original command that was executed
            result: The execution result dictionary
            
        Returns:
            Dictionary with analysis and suggestions
        """
        analysis = {
            "success": result.get("success", False),
            "command": command,
            "has_error": not result.get("success", False),
            "error_type": None,
            "suggestions": [],
            "alternative_commands": []
        }
        
        # If command was successful, provide basic analysis
        if result.get("success", True):
            analysis["summary"] = "Command executed successfully."
            
            # Check if output is empty
            stdout = result.get("stdout", "").strip()
            if not stdout:
                analysis["summary"] = "Command executed successfully with no output."
            else:
                # Estimate output size
                lines = stdout.count('\n') + 1
                analysis["output_lines"] = lines
                if lines > 20:
                    analysis["summary"] = f"Command executed successfully with {lines} lines of output."
                    analysis["suggestions"].append("Consider using pagination (e.g., | less) for large outputs.")
            
            return analysis
        
        # Command failed, analyze errors
        stderr = result.get("stderr", "").strip()
        stdout = result.get("stdout", "").strip()
        return_code = result.get("return_code", -1)
        
        # Combine stdout and stderr for analysis if stderr is empty
        error_text = stderr if stderr else stdout
        
        # Identify error type and get suggestions
        for pattern, handler in self.error_patterns.items():
            if re.search(pattern, error_text, re.IGNORECASE):
                handler_result = handler(command, error_text, return_code)
                
                analysis["error_type"] = handler_result.get("error_type", "Unknown error")
                analysis["suggestions"].extend(handler_result.get("suggestions", []))
                analysis["alternative_commands"].extend(handler_result.get("alternative_commands", []))
                
                # Only use the first matching error pattern to avoid conflicting suggestions
                break
        
        # If no specific error pattern matched, provide generic analysis
        if not analysis["error_type"]:
            analysis["error_type"] = "Unknown error"
            analysis["suggestions"].append("Check the command syntax and try again.")
            analysis["suggestions"].append("Search for the specific error message online.")
        
        return analysis
    
    def _handle_command_not_found(self, command: str, error_text: str, return_code: int) -> Dict[str, Any]:
        """Handle 'command not found' errors."""
        cmd_parts = command.split()
        cmd_name = cmd_parts[0]
        
        result = {
            "error_type": "Command not found",
            "suggestions": [
                f"The command '{cmd_name}' was not found. Check if it's installed.",
                "Make sure the command name is spelled correctly."
            ],
            "alternative_commands": []
        }
        
        # Suggest installation commands based on common packages
        common_packages = {
            "python": "sudo apt-get install python3",
            "pip": "sudo apt-get install python3-pip",
            "node": "sudo apt-get install nodejs",
            "npm": "sudo apt-get install npm",
            "java": "sudo apt-get install default-jre",
            "git": "sudo apt-get install git",
            "docker": "sudo apt-get install docker.io",
            "wget": "sudo apt-get install wget",
            "curl": "sudo apt-get install curl",
            "gcc": "sudo apt-get install build-essential",
            "make": "sudo apt-get install build-essential",
        }
        
        if cmd_name in common_packages:
            result["suggestions"].append(f"Try installing it with: {common_packages[cmd_name]}")
            result["alternative_commands"].append(common_packages[cmd_name])
        else:
            result["suggestions"].append(f"Try installing it with: sudo apt-get install {cmd_name}")
            result["alternative_commands"].append(f"sudo apt-get install {cmd_name}")
        
        # Check for typos in common commands
        common_commands = ["ls", "cd", "mkdir", "rm", "cp", "mv", "cat", "grep", "find", "echo", "touch"]
        for common_cmd in common_commands:
            if self._levenshtein_distance(cmd_name, common_cmd) <= 2:
                result["suggestions"].append(f"Did you mean '{common_cmd}' instead of '{cmd_name}'?")
                corrected_cmd = command.replace(cmd_name, common_cmd, 1)
                result["alternative_commands"].append(corrected_cmd)
                break
        
        return result
    
    def _handle_permission_denied(self, command: str, error_text: str, return_code: int) -> Dict[str, Any]:
        """Handle permission denied errors."""
        result = {
            "error_type": "Permission denied",
            "suggestions": [
                "You don't have sufficient permissions to run this command.",
                "Try running the command with 'sudo' for elevated privileges."
            ],
            "alternative_commands": [f"sudo {command}"]
        }
        
        # Check if it's a file permission issue
        if "file" in error_text.lower() or "/" in command:
            result["suggestions"].append("Check file permissions with 'ls -l' and modify if needed.")
            result["alternative_commands"].append(f"ls -l {command.split()[-1]}")
            result["alternative_commands"].append(f"chmod +x {command.split()[-1]}")
        
        return result
    
    def _handle_file_not_found(self, command: str, error_text: str, return_code: int) -> Dict[str, Any]:
        """Handle file not found errors."""
        cmd_parts = command.split()
        
        # Try to identify the file that wasn't found
        file_path = None
        for part in cmd_parts[1:]:
            if not part.startswith("-") and "/" in part:
                file_path = part
                break
            elif not part.startswith("-") and "." in part:
                file_path = part
                break
        
        result = {
            "error_type": "File not found",
            "suggestions": [
                "The specified file or directory does not exist.",
                "Check the file path and try again."
            ],
            "alternative_commands": []
        }
        
        if file_path:
            result["suggestions"].append(f"Check if '{file_path}' exists.")
            result["alternative_commands"].append(f"ls -la {file_path}")
            
            # If it looks like a directory path
            if not "." in file_path.split("/")[-1]:
                result["suggestions"].append(f"Try creating the directory: mkdir -p {file_path}")
                result["alternative_commands"].append(f"mkdir -p {file_path}")
            else:
                # Check the directory containing the file
                dir_path = "/".join(file_path.split("/")[:-1])
                if dir_path:
                    result["suggestions"].append(f"Check the directory: ls -la {dir_path}")
                    result["alternative_commands"].append(f"ls -la {dir_path}")
        
        return result
    
    def _handle_syntax_error(self, command: str, error_text: str, return_code: int) -> Dict[str, Any]:
        """Handle syntax errors."""
        cmd_parts = command.split()
        cmd_name = cmd_parts[0]
        
        result = {
            "error_type": "Syntax error",
            "suggestions": [
                "There's a syntax error in your command.",
                f"Check the correct usage of '{cmd_name}' with: {cmd_name} --help"
            ],
            "alternative_commands": [f"{cmd_name} --help"]
        }
        
        # For shell syntax errors
        if cmd_name in ["bash", "sh"] or "bash" in error_text.lower():
            result["suggestions"].append("Check for missing quotes, brackets, or semicolons.")
        
        return result
    
    def _handle_invalid_option(self, command: str, error_text: str, return_code: int) -> Dict[str, Any]:
        """Handle invalid option errors."""
        cmd_parts = command.split()
        cmd_name = cmd_parts[0]
        
        # Try to identify the invalid option
        invalid_option = None
        for part in cmd_parts[1:]:
            if part.startswith("-") and part in error_text:
                invalid_option = part
                break
        
        result = {
            "error_type": "Invalid option",
            "suggestions": [
                f"The command '{cmd_name}' doesn't recognize one of the options you provided.",
                f"Check the correct usage with: {cmd_name} --help"
            ],
            "alternative_commands": [f"{cmd_name} --help"]
        }
        
        if invalid_option:
            result["suggestions"].append(f"The option '{invalid_option}' appears to be invalid.")
            
            # Try to suggest a corrected command
            corrected_cmd = command
            if invalid_option.startswith("--"):
                # For long options, just remove the invalid one
                corrected_cmd = " ".join([p for p in cmd_parts if p != invalid_option])
            elif invalid_option.startswith("-") and len(invalid_option) > 2:
                # For combined short options like -abc, try to remove just the problematic one
                result["suggestions"].append("For combined short options, try separating them.")
                corrected_cmd = " ".join([p if p != invalid_option else "-" + "".join([c for c in p[1:] if c not in error_text]) for p in cmd_parts])
            
            if corrected_cmd != command:
                result["suggestions"].append(f"Try: {corrected_cmd}")
                result["alternative_commands"].append(corrected_cmd)
        
        return result
    
    def _handle_package_not_found(self, command: str, error_text: str, return_code: int) -> Dict[str, Any]:
        """Handle package not found errors."""
        # Try to identify the package name
        package_match = re.search(r"package ['\"]?([^'\"]+)['\"]? not found", error_text, re.IGNORECASE)
        package_name = package_match.group(1) if package_match else None
        
        result = {
            "error_type": "Package not found",
            "suggestions": [
                "The specified package could not be found."
            ],
            "alternative_commands": []
        }
        
        if "apt" in command or "apt-get" in command:
            result["suggestions"].append("Try updating the package list: sudo apt-get update")
            result["alternative_commands"].append("sudo apt-get update")
            
            if package_name:
                result["suggestions"].append(f"Search for similar packages: apt search {package_name}")
                result["alternative_commands"].append(f"apt search {package_name}")
        
        elif "pip" in command:
            if package_name:
                result["suggestions"].append(f"Check the package name on PyPI: https://pypi.org/project/{package_name}/")
                result["suggestions"].append(f"Search for similar packages: pip search {package_name}")
                result["alternative_commands"].append(f"pip search {package_name}")
        
        elif "npm" in command:
            if package_name:
                result["suggestions"].append(f"Check the package name on npm: https://www.npmjs.com/package/{package_name}")
                result["suggestions"].append(f"Search for similar packages: npm search {package_name}")
                result["alternative_commands"].append(f"npm search {package_name}")
        
        return result
    
    def _handle_module_not_found(self, command: str, error_text: str, return_code: int) -> Dict[str, Any]:
        """Handle module not found errors."""
        # Try to identify the module name
        module_match = re.search(r"module ['\"]?([^'\"]+)['\"]? not found", error_text, re.IGNORECASE)
        module_name = module_match.group(1) if module_match else None
        
        result = {
            "error_type": "Module not found",
            "suggestions": [
                "The specified module or library could not be found."
            ],
            "alternative_commands": []
        }
        
        if "python" in command or "python3" in command:
            if module_name:
                result["suggestions"].append(f"Try installing the module: pip install {module_name}")
                result["alternative_commands"].append(f"pip install {module_name}")
        
        elif "node" in command:
            if module_name:
                result["suggestions"].append(f"Try installing the module: npm install {module_name}")
                result["alternative_commands"].append(f"npm install {module_name}")
        
        return result
    
    def _handle_network_error(self, command: str, error_text: str, return_code: int) -> Dict[str, Any]:
        """Handle network-related errors."""
        result = {
            "error_type": "Network error",
            "suggestions": [
                "There was a problem with the network connection.",
                "Check your internet connection and try again."
            ],
            "alternative_commands": []
        }
        
        if "could not resolve host" in error_text.lower():
            result["suggestions"].append("The hostname could not be resolved. Check the URL or domain name.")
            result["suggestions"].append("Try checking your DNS settings.")
            result["alternative_commands"].append("ping 8.8.8.8")
        
        elif "connection refused" in error_text.lower():
            result["suggestions"].append("The connection was refused. The server might be down or not accepting connections.")
            result["suggestions"].append("Check if the service is running and the port is correct.")
            
            # Try to extract host/port from command
            url_match = re.search(r"https?://([^:/]+)(?::(\d+))?", command)
            if url_match:
                host = url_match.group(1)
                port = url_match.group(2) or "80"
                result["suggestions"].append(f"Try checking if the host is reachable: ping {host}")
                result["alternative_commands"].append(f"ping {host}")
                result["suggestions"].append(f"Try checking if the port is open: telnet {host} {port}")
                result["alternative_commands"].append(f"telnet {host} {port}")
        
        elif "network is unreachable" in error_text.lower():
            result["suggestions"].append("The network is unreachable. Check your network connection.")
            result["suggestions"].append("Try checking your network configuration.")
            result["alternative_commands"].append("ip addr show")
            result["alternative_commands"].append("route -n")
        
        return result
    
    def _handle_disk_space(self, command: str, error_text: str, return_code: int) -> Dict[str, Any]:
        """Handle disk space errors."""
        result = {
            "error_type": "Disk space error",
            "suggestions": [
                "There is no space left on the device.",
                "Try freeing up some disk space."
            ],
            "alternative_commands": [
                "df -h",
                "du -sh /* | sort -hr"
            ]
        }
        
        return result
    
    def _handle_generic_error(self, command: str, error_text: str, return_code: int) -> Dict[str, Any]:
        """Handle generic errors."""
        result = {
            "error_type": "Generic error",
            "suggestions": [
                f"The command failed with return code {return_code}.",
                "Check the error message for details."
            ],
            "alternative_commands": []
        }
        
        # Try to extract meaningful information from the error message
        error_lines = error_text.split("\n")
        if error_lines:
            main_error = error_lines[0].strip()
            result["suggestions"].append(f"Error message: {main_error}")
        
        return result
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Calculate the Levenshtein distance between two strings.
        Used for suggesting corrections for typos.
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

# Example Usage (for testing)
if __name__ == '__main__':
    print("Testing CommandAnalyzer...")
    analyzer = CommandAnalyzer()
    
    # Test 1: Command not found
    print("\nTesting 'command not found' error...")
    result1 = {
        "success": False,
        "stdout": "",
        "stderr": "bash: pythno: command not found",
        "return_code": 127
    }
    analysis1 = analyzer.analyze_command_result("pythno script.py", result1)
    print(f"Error type: {analysis1['error_type']}")
    print("Suggestions:")
    for suggestion in analysis1['suggestions']:
        print(f"- {suggestion}")
    print("Alternative commands:")
    for cmd in analysis1['alternative_commands']:
        print(f"- {cmd}")
    
    # Test 2: Permission denied
    print("\nTesting 'permission denied' error...")
    result2 = {
        "success": False,
        "stdout": "",
        "stderr": "bash: ./script.sh: Permission denied",
        "return_code": 126
    }
    analysis2 = analyzer.analyze_command_result("./script.sh", result2)
    print(f"Error type: {analysis2['error_type']}")
    print("Suggestions:")
    for suggestion in analysis2['suggestions']:
        print(f"- {suggestion}")
    print("Alternative commands:")
    for cmd in analysis2['alternative_commands']:
        print(f"- {cmd}")
    
    # Test 3: Successful command
    print("\nTesting successful command...")
    result3 = {
        "success": True,
        "stdout": "Hello, World!",
        "stderr": "",
        "return_code": 0
    }
    analysis3 = analyzer.analyze_command_result("echo 'Hello, World!'", result3)
    print(f"Success: {analysis3['success']}")
    print(f"Summary: {analysis3['summary']}")
