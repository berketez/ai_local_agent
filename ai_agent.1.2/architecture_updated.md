# AI Helper Architecture Update

## Overview
The AI Helper is a terminal-based application that allows users to run an LLM locally on their macOS computer and interact with their system through natural language commands. The application asks for appropriate permissions before performing actions on the user's computer.

## Core Components

### 1. LLM Integration Layer
- **Abstraction Layer**: Provides a unified interface for different LLM backends
- **Ollama Integration**: Uses the Ollama Python library for local LLM inference
- **LM Studio Integration**: Supports both the LM Studio Python SDK and OpenAI compatibility API
- **Model Management**: Handles model loading, configuration, and inference

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

## LLM Backend Architecture

### Ollama Backend
- Uses the official Ollama Python library (`ollama`)
- Supports chat-based interactions with streaming capabilities
- Handles model management (list, pull, create, delete)
- Provides embeddings for semantic search

### LM Studio Backend
- **Option 1: Python SDK**
  - Uses the official LM Studio Python SDK (`lmstudio`)
  - Provides direct access to LLM functionality
  - Supports chat responses and text completions
  
- **Option 2: OpenAI Compatibility API**
  - Uses the OpenAI Python library with a custom base URL
  - Compatible with existing OpenAI client code
  - Supports chat completions, text completions, and embeddings

### Backend Selection
- Automatic detection of available backends
- User-configurable preference for backend selection
- Fallback mechanisms if preferred backend is unavailable

## Data Flow

1. User provides input through terminal
2. Command is processed by the selected LLM backend to understand intent
3. System determines required permissions and capabilities
4. If new permissions are needed, user is prompted for consent
5. Actions are executed with appropriate feedback
6. Results are presented to the user
7. Context is maintained for follow-up interactions

## Technology Stack

- **Python**: Core programming language
- **Ollama Python Library**: For Ollama integration
- **LM Studio Python SDK/OpenAI Library**: For LM Studio integration
- **PyAutoGUI**: System interaction (requires Accessibility permissions)
- **AppleScript** (via Python): macOS-specific automation
- **Selenium/Playwright**: Browser automation
- **Rich**: Terminal UI enhancements

## Security Considerations

- All permissions are explicitly requested and can be revoked
- No data is sent to external servers (fully local operation)
- Clear logging of all actions performed
- Sandboxed execution where possible
