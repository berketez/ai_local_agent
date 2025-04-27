AI Helper

AI Helper is a locally running LLM (Large Language Model) powered artificial intelligence assistant that allows you to interact with your macOS system through natural language commands.

## Features

- **Native LLM Integration**: Using local LLM models via Ollama or LM Studio
- **System Interaction**: File operations, web browser control, application management and screen control
- **Permission System**: Request user permission before system operations
- **Terminal Interface**: User-friendly terminal-based interface

## Requirements

- Python 3.8 or newer
- macOS operating system
- The following Python packages:
  - llama-cpp-python
  - pyautogui
  - pillow
  - pytesseract
  - rich

## Installation

To install dependencies:

```bash
pip install -r requirements.txt
```

Or run the installation script:

```bash
./install.sh
```

## Usage

To start AI Helper from the terminal:

```bash
# With automatic backend detection
python src/main.py --backend auto --model <model_name>

# With a specific backend selection
python src/main.py --backend ollama --model llama3.2
python src/main.py --backend lmstudio_sdk --model llama-3.2-1b-instruct
```

### Command Line Options

- `-backend`: LLM backend to use (`auto`, `ollama`, `lmstudio_sdk`, `lmstudio_openai`) - Default: `auto`
- `--model`: Model name to use (mandatory)
- `--context-length`: Context length for the model (default: 4096)
- `-temperature`: Temperature value for text generation (default: 0.7)
- `--verbose` or `-v`: Enabling detailed output

## Interaction Examples

When AI Helper is running, you can interact using natural language:

### Web Browsing
```
> Open Safari and go to apple.com
> Search Google for ‘latest macOS features’
```

### File Operations
```
> Create a new text file called todo.txt on the desktop
> Read the contents of ~/Documents/notes.txt
> List all files in my Downloads folder
```

### Application Control
```
> Open the Calculator app
> Close Safari
> List all running applications
```

### System Interaction
```
> Take a screenshot of my screen
> In the current application, write ‘Hello world!’
> Move my mouse to the centre of the screen and click
```

## Architecture

AI Helper consists of the following main components:

1. **LLM Integration**: Loads and uses local models
2. **Permission System**: Requests user permission before system actions
3. **System Interaction Layer**: Performs system operations
4. **Command Interpreter**: Interprets natural language commands
5. **Terminal Interface**: Manages user interaction

## Security

- All permits are expressly requested and can be cancelled
- Data is not sent to external servers (works completely locally)
- A clear record of all actions performed is kept
- Protected operation as far as possible

## Permission Management

AI Helper always asks for permission before processes that interact with your system. You can do the following

- Allow for a single action
- Allow for a category of action
- Grant temporary leave that expires after a certain period of time

## Exit

To exit AI Helper, type one of the following:
```
exit
```
or
```
quit
```

## Licence

See the LICENSE file for this project licence.

Translated with www.DeepL.com/Translator (free version)
