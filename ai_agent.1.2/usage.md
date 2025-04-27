# Usage Guide

This guide provides examples and instructions for using AI Helper with Ollama and LM Studio on your macOS system.

## Basic Usage

Start AI Helper from the terminal with your preferred LLM backend:

```bash
# Automatic backend detection
python src/main.py --backend auto --model <model_name>

# Specific backend selection
python src/main.py --backend ollama --model llama3.2
python src/main.py --backend lmstudio_sdk --model llama-3.2-1b-instruct
python src/main.py --backend lmstudio_openai --model llama-3.2-1b-instruct
```

### Command-line Options

- `--backend`: LLM backend to use (`auto`, `ollama`, `lmstudio_sdk`, `lmstudio_openai`) - Default: `auto`
- `--model`: Name of the model to use (required)
- `--context-length`: Context length for the model (default: 4096)
- `--temperature`: Temperature for text generation (default: 0.7)
- `--verbose` or `-v`: Enable verbose output

## Backend-Specific Information

### Ollama

- Models are referenced by their Ollama model name (e.g., `llama3.2`, `mistral`, `codellama`)
- You must pull models before using them: `ollama pull <model_name>`
- Ensure the Ollama service is running: `ollama serve`

### LM Studio SDK

- Models are referenced by their LM Studio model name
- Models must be downloaded through the LM Studio interface
- LM Studio must be running when using the SDK backend

### LM Studio OpenAI API

- Start the local server in LM Studio before using this backend
- The default server port is 1234
- Models are referenced by their LM Studio model name
- This backend is compatible with OpenAI API format

## Interaction Examples

Once AI Helper is running, you can interact with it using natural language. Here are some examples of what you can do:

### Web Browsing

```
> Open Safari and go to apple.com
```
AI Helper will:
1. Request permission to control applications (if not already granted)
2. Open Safari
3. Navigate to apple.com

```
> Search for "latest macOS features" on Google
```
AI Helper will:
1. Open your default browser
2. Navigate to Google
3. Search for "latest macOS features"

### File Operations

```
> Create a new text file on my desktop called todo.txt with a list of my tasks
```
AI Helper will:
1. Request permission to access files (if not already granted)
2. Create a new text file at ~/Desktop/todo.txt
3. Add the content you specified

```
> Read the contents of my ~/Documents/notes.txt file
```
AI Helper will:
1. Request permission to access files
2. Read and display the contents of the file

```
> List all files in my Downloads folder
```
AI Helper will:
1. Request permission to access files
2. List all files in your Downloads folder

### Application Control

```
> Open Calculator app
```
AI Helper will:
1. Request permission to control applications
2. Open the Calculator application

```
> Close Safari
```
AI Helper will:
1. Request permission to control applications
2. Close Safari if it's running

```
> List all running applications
```
AI Helper will:
1. Request permission to control applications
2. Show a list of currently running applications

### System Interaction

```
> Take a screenshot of my screen
```
AI Helper will:
1. Request Screen Recording permission (if not already granted)
2. Capture a screenshot
3. Save it to a temporary location and show the path

```
> Type "Hello, world!" in the current application
```
AI Helper will:
1. Request Accessibility permission (if not already granted)
2. Simulate typing "Hello, world!" in the currently active application

```
> Move my mouse to the center of the screen and click
```
AI Helper will:
1. Request Accessibility permission
2. Move the mouse cursor to the center of the screen
3. Perform a click action

### LLM-Specific Commands

```
> Switch to Ollama backend with llama3.2 model
```
AI Helper will:
1. Request permission to change LLM backend
2. Switch to the Ollama backend with the specified model

```
> List available models in LM Studio
```
AI Helper will:
1. Request permission to list models
2. Show a list of available models in LM Studio

```
> Pull the mistral model in Ollama
```
AI Helper will:
1. Request permission to pull models
2. Pull the mistral model in Ollama

## Permission Management

AI Helper will always ask for permission before performing actions that interact with your system. You can:

- Grant permission for a single action
- Grant permission for a category of actions
- Grant temporary permission that expires after a set time

Example permission dialog:
```
PERMISSION REQUEST: AI Helper needs permission to: Control applications (browser_open)
Reason: Open web browser
Grant permission? (y/n):
```

## Tips for Effective Use

1. **Be specific**: Provide clear instructions about what you want AI Helper to do
2. **Start simple**: Begin with basic commands before trying more complex tasks
3. **Watch permissions**: Only grant permissions you're comfortable with
4. **Use temporary permissions**: For sensitive operations, use temporary permissions that expire
5. **Try different backends**: Different LLM backends may perform better for different tasks

## Limitations

- AI Helper can only interact with graphical elements it can access through accessibility APIs
- Some applications may have security measures that prevent automation
- Performance depends on your Mac's specifications and the size of the LLM model
- Screen reading accuracy depends on text clarity and contrast
- Different LLM backends may have different capabilities and limitations

## Exiting AI Helper

To exit AI Helper, simply type:
```
exit
```
or
```
quit
```

This will properly close the application and clean up any resources.
