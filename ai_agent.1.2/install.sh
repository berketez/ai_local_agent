#!/bin/bash
# Installation script for AI Helper with Ollama and LM Studio support

echo "AI Helper Installation Script"
echo "============================"
echo

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Error: This script is designed for macOS only."
    exit 1
fi

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3 first."
    echo "Visit https://www.python.org/downloads/macos/ to download and install."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo "Error: Python 3.8 or higher is required. You have Python $PYTHON_VERSION."
    echo "Please upgrade your Python installation."
    exit 1
fi

echo "Python $PYTHON_VERSION detected."

# Check if running on Apple Silicon
if [[ $(uname -m) == "arm64" ]]; then
    IS_APPLE_SILICON=true
    echo "Apple Silicon detected. Will optimize for Metal acceleration."
else
    IS_APPLE_SILICON=false
    echo "Intel Mac detected."
fi

# Check for LLM backends
echo
echo "Checking for LLM backends..."

# Check for Ollama
if command -v ollama &> /dev/null; then
    echo "✅ Ollama detected."
    HAS_OLLAMA=true
else
    echo "❌ Ollama not found. You can install it from https://ollama.com/download"
    HAS_OLLAMA=false
fi

# Check for LM Studio (approximate check)
if [ -d "/Applications/LM Studio.app" ]; then
    echo "✅ LM Studio detected."
    HAS_LMSTUDIO=true
else
    echo "❌ LM Studio not found. You can install it from https://lmstudio.ai/download"
    HAS_LMSTUDIO=false
fi

if [ "$HAS_OLLAMA" = false ] && [ "$HAS_LMSTUDIO" = false ]; then
    echo
    echo "Warning: No LLM backends detected. You need to install either Ollama or LM Studio."
    echo "Would you like to continue anyway? (y/n)"
    read -r CONTINUE
    if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
        echo "Installation aborted."
        exit 1
    fi
fi

# Create virtual environment
echo
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo
echo "Installing dependencies..."
pip install --upgrade pip

# Install backend-specific dependencies
if [ "$HAS_OLLAMA" = true ]; then
    echo "Installing Ollama Python library..."
    pip install ollama
fi

if [ "$HAS_LMSTUDIO" = true ]; then
    echo "Installing LM Studio dependencies..."
    pip install lmstudio openai
fi

# Install other dependencies
echo "Installing other dependencies..."
pip install pyautogui pillow pytesseract rich

# Install the package
echo
echo "Installing AI Helper..."
pip install -e .

echo
echo "Installation complete!"
echo
echo "Next steps:"
if [ "$HAS_OLLAMA" = true ]; then
    echo "- For Ollama: Pull a model with 'ollama pull llama3.2'"
    echo "- Run AI Helper with: python src/main.py --backend ollama --model llama3.2"
fi
if [ "$HAS_LMSTUDIO" = true ]; then
    echo "- For LM Studio: Download a model through the LM Studio interface"
    echo "- Run AI Helper with: python src/main.py --backend lmstudio_sdk --model <model_name>"
    echo "- Or start the server in LM Studio and run: python src/main.py --backend lmstudio_openai --model <model_name>"
fi
echo
echo "For more information, see the documentation in the docs/ directory."
