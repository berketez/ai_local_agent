#!/bin/bash
# Run script for AI Helper with Ollama and LM Studio support

echo "AI Helper Runner Script"
echo "======================"
echo

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Error: This script is designed for macOS only."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Please run install.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Default values
BACKEND="auto"
MODEL=""
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend)
            BACKEND="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./run.sh [options]"
            echo
            echo "Options:"
            echo "  --backend <backend>    LLM backend to use (auto, ollama, lmstudio_sdk, lmstudio_openai)"
            echo "  --model <model>        Model name to use"
            echo "  --verbose, -v          Enable verbose output"
            echo "  --help, -h             Show this help message"
            exit 0
            ;;
        *)
            # Pass remaining arguments to the Python script
            break
            ;;
    esac
done

# Check if model is specified
if [ -z "$MODEL" ]; then
    echo "Error: Model name is required. Use --model to specify a model."
    echo "Examples:"
    echo "  For Ollama: --model llama3.2"
    echo "  For LM Studio: --model llama-3.2-1b-instruct"
    exit 1
fi

# Check for LLM backends based on selected backend
if [ "$BACKEND" = "ollama" ] || [ "$BACKEND" = "auto" ]; then
    if ! command -v ollama &> /dev/null; then
        if [ "$BACKEND" = "ollama" ]; then
            echo "Error: Ollama not found. Please install Ollama from https://ollama.com/download"
            exit 1
        else
            echo "Warning: Ollama not found. Will try other backends."
        fi
    else
        # Check if the model exists in Ollama
        if [ "$BACKEND" = "ollama" ]; then
            if ! ollama list | grep -q "$MODEL"; then
                echo "Warning: Model '$MODEL' not found in Ollama."
                echo "You may need to pull it first with: ollama pull $MODEL"
            fi
        fi
    fi
fi

if [ "$BACKEND" = "lmstudio_sdk" ] || [ "$BACKEND" = "lmstudio_openai" ] || [ "$BACKEND" = "auto" ]; then
    if [ ! -d "/Applications/LM Studio.app" ]; then
        if [ "$BACKEND" = "lmstudio_sdk" ] || [ "$BACKEND" = "lmstudio_openai" ]; then
            echo "Error: LM Studio not found. Please install LM Studio from https://lmstudio.ai/download"
            exit 1
        else
            echo "Warning: LM Studio not found. Will try other backends."
        fi
    fi
fi

# LM Studio model dizini
LMSTUDIO_MODELS_DIR="/Users/apple/.lmstudio/models"

# Model kontrolü
if [[ "$BACKEND" == *"lmstudio"* ]]; then
    # LM Studio modellerini kontrol et
    if [ ! -f "$MODEL" ]; then
        # Tam yol belirtilmemiş, LM Studio dizininde ara
        POSSIBLE_PATHS=(
            "$MODEL"
            "$LMSTUDIO_MODELS_DIR/$MODEL"
            "$LMSTUDIO_MODELS_DIR/lmstudio-community/$MODEL"
        )
        
        MODEL_FOUND=false
        for path in "${POSSIBLE_PATHS[@]}"; do
            if [ -f "$path" ]; then
                MODEL="$path"
                MODEL_FOUND=true
                break
            fi
        done
        
        if [ "$MODEL_FOUND" = false ]; then
            echo "Model dosyası bulunamadı: $MODEL"
            echo "LM Studio model dizininde kontrol edildi: $LMSTUDIO_MODELS_DIR"
            exit 1
        fi
    fi
fi

# Komut oluştur
CMD="python main.py --backend $BACKEND --model $MODEL"

# Add verbose flag if specified
if [ "$VERBOSE" = true ]; then
    CMD="$CMD --verbose"
fi

# Add any remaining arguments
if [ $# -gt 0 ]; then
    CMD="$CMD $@"
fi

# Çıktı filtreleme ekleniyor - uyarıları tamamen kaldırır
echo "Starting AI Helper with backend: $BACKEND, model: $MODEL"
echo
eval "$CMD"
