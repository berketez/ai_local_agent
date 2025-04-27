# AI Helper Architecture

## Overview
The AI Helper is a terminal-based application that allows users to run an LLM locally on their macOS computer and interact with their system through natural language commands. The application asks for appropriate permissions before performing actions on the user's computer.

## Core Components

### 1. LLM Integration
- Uses `llama.cpp` through the Python bindings (`llama-cpp-python`)
- Optimized for macOS with Metal support for Apple Silicon
- Allows loading various open-source models from local storage

### 2. Permission System
- Implements a robust permission management system
- Requests explicit user consent before performing system actions
- Maintains a permission registry for previously approved actions
- Handles macOS-specific permission requirements (Accessibility, File Access, etc.)

### 3. System Interaction Layer
- Browser automation capabilities
- File system operations
- Application control
- Input simulation (keyboard and mouse)
- Screen capture and analysis

### 4. Command Interpreter
- Parses natural language commands
- Maps commands to appropriate system actions
- Handles error cases and provides helpful feedback

### 5. Terminal Interface
- Clean, user-friendly terminal UI
- Command history and context management
- Progress indicators for long-running tasks

## Data Flow

1. User provides input through terminal
2. Command is processed by the LLM to understand intent
3. System determines required permissions and capabilities
4. If new permissions are needed, user is prompted for consent
5. Actions are executed with appropriate feedback
6. Results are presented to the user
7. Context is maintained for follow-up interactions

## Technology Stack

- **Python**: Core programming language
- **llama-cpp-python**: Local LLM integration
- **PyAutoGUI**: System interaction (requires Accessibility permissions)
- **AppleScript** (via Python): macOS-specific automation
- **Selenium/Playwright**: Browser automation
- **Rich**: Terminal UI enhancements

## Security Considerations

- All permissions are explicitly requested and can be revoked
- No data is sent to external servers (fully local operation)
- Clear logging of all actions performed
- Sandboxed execution where possible
