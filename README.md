<p align="center">
  <h1 align="center">AI Local Agent</h1>
  <p align="center">
    <strong>Control your Mac with natural language — powered by local LLMs</strong>
  </p>
  <p align="center">
    <a href="#quick-start">Quick Start</a> &bull;
    <a href="#features">Features</a> &bull;
    <a href="#demo">Demo</a> &bull;
    <a href="#architecture">Architecture</a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/Platform-macOS-000?style=flat-square&logo=apple" alt="macOS">
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/LLM-Ollama%20%7C%20LM%20Studio-FF6B35?style=flat-square" alt="LLM">
    <img src="https://img.shields.io/badge/Privacy-100%25%20Local-00C853?style=flat-square&logo=shieldsdotio&logoColor=white" alt="Local">
    <img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" alt="MIT">
  </p>
</p>

---

No cloud APIs. No data leaving your machine. Just a local LLM connected to real system tools — terminal, browser, files, apps, screen.

## Features

| Capability | What It Does | Powered By |
|:----------:|:------------|:-----------|
| **Terminal** | Execute commands, run scripts, manage packages | `secure_terminal.py` with blocklist + confirmation |
| **Browser** | Navigate sites, extract content, fill forms | Selenium (headless Chrome) |
| **Files** | Read, write, create, delete files/directories | Native Python I/O |
| **Apps** | Open, close, list macOS applications | AppleScript |
| **Screen** | Screenshots, OCR text extraction | pyautogui + Tesseract |
| **Research** | Multi-source web research + analysis | Deep researcher pipeline |

## Demo

### Terminal: Create, Run, Delete

```
You> Create a Python file /tmp/hello.py that prints "Hello!", run it, then delete it

[1/3] terminal_execute: echo 'print("Hello!")' > /tmp/hello.py     ✓ Created
[2/3] terminal_execute: python3 /tmp/hello.py                      ✓ Hello!
[3/3] terminal_execute: rm /tmp/hello.py                           ✓ Deleted

FINAL ANSWER: Created, executed, and deleted the file successfully.
```

### Browser: Navigate + Extract Content

```
You> Go to wikipedia.org and tell me today's featured article

[1/4] browser_navigate: https://www.wikipedia.org/                 ✓ Opened
[2/4] browser_get_content: text                                    ✓ Turkish version
[3/4] browser_navigate: https://en.wikipedia.org/wiki/Main_Page    ✓ Redirected to English
[4/4] browser_get_content: text                                    ✓ Content extracted

FINAL ANSWER: Today's featured article is about Ojos del Salado — a dormant
complex volcano in the Andes, the highest volcano on Earth (6,893m).
```

> The agent autonomously decided to navigate to the English Wikipedia after detecting the Turkish version didn't have the featured article section.

## Quick Start

```bash
# Clone
git clone https://github.com/berketez/ai_local_agent.git
cd ai_local_agent/ai_agent.1.2

# Install dependencies
pip install -r requirements.txt

# Optional: OCR support
brew install tesseract

# Run with Ollama
python main.py --backend ollama --model gemma4:31b

# Run with LM Studio
python main.py --backend lmstudio_openai --model your-model-name

# Auto-detect backend
python main.py --backend auto --model gemma4:31b
```

### CLI Options

```
Usage: python main.py [OPTIONS]

Options:
  --backend       auto | ollama | lmstudio_openai | lmstudio_sdk  [default: auto]
  --model, -m     Model name (e.g. gemma4:31b, gemma3:12b)        [required]
  --context-length Context window size                              [default: 4096]
  --temperature   Generation temperature                            [default: 0.7]
  --verbose, -v   Show full prompts and debug output
  --auto-confirm  Skip permission prompts (testing only)
```

## Architecture

```
                    ┌─────────────────────────────┐
                    │       Natural Language       │
                    │         User Input           │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │         main.py              │
                    │                              │
                    │   argparse → LLMFactory      │
                    │         → UnifiedAgent       │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────┴───────────────┐
                    │                              │
              ┌─────▼─────┐              ┌────────▼────────┐
              │    LLM    │              │  UnifiedAgent   │
              │  Backend  │              │                  │
              │           │◄────────────►│  prompt → JSON   │
              │ ○ Ollama  │   generate   │  action → exec   │
              │ ○ LMStudio│              │  observe → loop  │
              └───────────┘              └────────┬─────────┘
                                                  │
                          ┌──────────┬────────────┼────────────┬──────────┐
                          ▼          ▼            ▼            ▼          ▼
                    ┌──────────┐┌─────────┐┌──────────┐┌──────────┐┌─────────┐
                    │ Selenium ││ Secure  ││  File    ││   App    ││ Screen  │
                    │ Browser  ││Terminal ││Controller││Controller││  + OCR  │
                    │          ││         ││          ││          ││         │
                    │navigate  ││blocklist││read/write││open/close││capture  │
                    │content   ││confirm  ││create/del││list apps ││OCR text │
                    │forms     ││execute  ││          ││          ││         │
                    └──────────┘└─────────┘└──────────┘└──────────┘└─────────┘
```

## How It Works

1. You type a natural language request
2. The LLM analyzes the request and selects the appropriate tool
3. It generates a JSON action: `{"action": "tool_name", "params": {...}}`
4. The agent executes the action and collects the observation
5. The observation is fed back to the LLM for the next step
6. Repeat until the task is complete or max retries reached

## Security

| Layer | Protection |
|-------|-----------|
| **Permission System** | Every system action requires `y/n/always` confirmation |
| **Command Blocklist** | 14 dangerous patterns blocked (`rm -rf /`, fork bombs, `curl\|sh`, etc.) |
| **Shell Safety** | Simple commands: `shlex.split()` + `shell=False`. Redirects/pipes: `shell=True` with blocklist |
| **100% Local** | Zero network calls to AI providers — Ollama/LM Studio run on your machine |
| **Timeout** | All commands have 60s timeout to prevent hangs |

## Tested Models

| Model | Backend | Hardware | Result |
|-------|---------|----------|--------|
| **Gemma 4 31B** | Ollama | M4 Max 36GB | Terminal + Browser working |
| **GLM-4.7 Flash** | LM Studio | M4 Max 36GB | Working (reasoning model, slower) |
| **Gemma 3 12B** | Ollama | M4 Max 36GB | Working |

## Requirements

- **macOS** (AppleScript for app control)
- **Python 3.11+**
- **Ollama** or **LM Studio** with a loaded model
- **Chrome/Chromium** (for browser automation)
- **Tesseract** (optional, for OCR): `brew install tesseract`

## License

MIT
