# Project Structure Update

```
ai_helper_project/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py          # Abstract base class for LLM backends
│   │   ├── ollama.py        # Ollama integration
│   │   ├── lmstudio.py      # LM Studio integration
│   │   └── factory.py       # Factory for creating LLM backends
│   ├── permissions/
│   │   ├── __init__.py
│   │   ├── manager.py       # Permission management system
│   │   ├── registry.py      # Permission storage and retrieval
│   │   └── enhanced.py      # Enhanced permission features
│   ├── system/
│   │   ├── __init__.py
│   │   ├── browser.py       # Browser automation
│   │   ├── files.py         # File system operations
│   │   ├── apps.py          # Application control
│   │   ├── input.py         # Keyboard and mouse simulation
│   │   └── screen.py        # Screen capture and analysis
│   └── ui/
│       ├── __init__.py
│       └── terminal.py      # Terminal interface
├── docs/
│   ├── architecture.md      # Original architecture documentation
│   ├── architecture_updated.md # Updated architecture with Ollama and LM Studio
│   ├── installation.md      # Installation instructions
│   ├── usage.md             # Usage instructions
│   └── project_structure.md # Project structure documentation
├── tests/
│   ├── test_components.py   # Component tests
│   └── test_integration.py  # Integration tests
├── README.md                # Project overview
├── requirements.txt         # Dependencies
├── setup.py                 # Package setup
├── install.sh               # Installation script
└── run.sh                   # Run script
```
