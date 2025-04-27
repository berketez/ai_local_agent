# Installation Guide

This guide provides detailed instructions for installing and setting up AI Helper with Ollama and LM Studio on your macOS system.

## Prerequisites

Before installing AI Helper, ensure you have the following:

- macOS 11 (Big Sur) or newer
- Python 3.8 or higher
- At least 8GB of RAM (16GB recommended for larger models)
- At least 2GB of free disk space (more depending on model size)
- Administrator access (for installing dependencies and granting permissions)

## Step 1: Install Python (if not already installed)

1. Visit the [official Python website](https://www.python.org/downloads/macos/) and download the latest Python installer for macOS.
2. Run the installer and follow the on-screen instructions.
3. Verify the installation by opening Terminal and running:
   ```
   python3 --version
   ```

## Step 2: Install an LLM Backend

You need to install at least one of the supported LLM backends:

### Option A: Install Ollama

1. Visit [ollama.com/download](https://ollama.com/download) and download the macOS installer.
2. Open the downloaded file and follow the installation instructions.
3. After installation, open Terminal and pull a model:
   ```
   ollama pull llama3.2
   ```
   You can replace `llama3.2` with any other model available on Ollama.

### Option B: Install LM Studio

1. Visit [lmstudio.ai/download](https://lmstudio.ai/download) and download the macOS installer.
2. Open the downloaded file and follow the installation instructions.
3. Launch LM Studio and download a model through its interface.
4. For using the OpenAI compatibility API, start the local server in LM Studio.

## Step 3: Clone the Repository

1. Open Terminal.
2. Clone the repository:
   ```
   git clone https://github.com/yourusername/ai-helper.git
   cd ai-helper
   ```

## Step 4: Set Up a Virtual Environment (Recommended)

1. Create a virtual environment:
   ```
   python3 -m venv venv
   ```
2. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```

## Step 5: Install Dependencies

Install all required packages:

```
pip install -r requirements.txt
```

This will install:
- ollama (Python client for Ollama)
- lmstudio (Python SDK for LM Studio)
- openai (for LM Studio OpenAI compatibility)
- PyAutoGUI
- Pillow
- pytesseract
- rich (for enhanced terminal UI)

### Special Instructions for Apple Silicon Macs

For optimal performance on Apple Silicon (M1/M2/M3) Macs, ensure you're using the native ARM versions of the packages.

## Step 6: Set Up System Permissions

AI Helper requires certain permissions to interact with your macOS system:

### Accessibility Permissions

1. Go to System Settings > Privacy & Security > Accessibility
2. Click the lock icon to make changes (enter your password if prompted)
3. Click the "+" button and add Terminal (or your Python application)
4. Ensure the checkbox next to it is checked

### Screen Recording Permissions

1. Go to System Settings > Privacy & Security > Screen Recording
2. Click the lock icon to make changes
3. Add Terminal (or your Python application)
4. Ensure the checkbox is checked
5. You may need to restart Terminal after granting this permission

### Files and Folders Permissions

1. When AI Helper first attempts to access files, macOS will prompt you to grant permission
2. Alternatively, go to System Settings > Privacy & Security > Files and Folders
3. Add Terminal and select the folders you want to allow access to

## Step 7: Verify Installation

Run a simple test to verify that everything is working:

### For Ollama:
```
python src/main.py --backend ollama --model llama3.2 --verbose
```

### For LM Studio SDK:
```
python src/main.py --backend lmstudio_sdk --model <your_model_name> --verbose
```

### For LM Studio OpenAI API:
```
python src/main.py --backend lmstudio_openai --model <your_model_name> --verbose
```

You should see the welcome message and be able to interact with the AI Helper.

## Troubleshooting

### Ollama Issues

- Ensure Ollama service is running with `ollama serve`
- Verify model is pulled with `ollama list`
- Check Ollama logs for errors

### LM Studio Issues

- Ensure LM Studio is running and a model is loaded
- For OpenAI API mode, verify the server is running in LM Studio
- Check the server port (default is 1234)

### Permission Issues

- If permission dialogs don't appear, manually add Terminal to the required permission categories
- Restart Terminal after granting permissions
- Check Console.app for permission-related error messages

### PyAutoGUI Issues

- If PyAutoGUI fails to install or work properly, try:
  ```
  pip install --upgrade pyobjc-core pyobjc
  pip install --upgrade pyautogui
  ```

## Uninstallation

To uninstall AI Helper:

1. Delete the repository folder
2. Optionally uninstall Ollama and/or LM Studio
3. Revoke permissions in System Settings if desired
