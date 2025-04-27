# Project Structure

```
ai_helper_project/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── model_loader.py  # LLM loading and configuration
│   │   └── inference.py     # LLM inference handling
│   ├── permissions/
│   │   ├── __init__.py
│   │   ├── manager.py       # Permission management system
│   │   └── registry.py      # Permission storage and retrieval
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
│   ├── architecture.md      # Architecture documentation
│   └── usage.md             # Usage instructions
└── README.md                # Project overview
```
