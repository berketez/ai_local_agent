#!/usr/bin/env python3
"""
AI Local Agent - Entry point

Uses the API-based backend system (Ollama / LM Studio) via LLMFactory,
then runs UnifiedAgent for the interactive REPL loop.
"""

import os
import sys
import argparse
import signal

# Ensure the package directory is on sys.path so relative imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from factory import LLMFactory
from unified_agent import UnifiedAgent


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="AI Local Agent - Run a local LLM agent with browser, terminal, and research tools"
    )
    parser.add_argument(
        "--backend",
        type=str,
        choices=["auto", "ollama", "lmstudio", "lmstudio_sdk", "lmstudio_openai"],
        default="auto",
        help="LLM backend to use (default: auto — tries Ollama first, then LM Studio)",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="llama2",
        help="Model name to use, e.g. llama2, mistral, gemma (default: llama2)",
    )
    parser.add_argument(
        "--context-length",
        type=int,
        default=4096,
        help="Context length for the model (default: 4096)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Temperature for text generation (default: 0.7)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--auto-confirm",
        action="store_true",
        help="Auto-confirm all permission prompts (for testing only)",
    )
    return parser.parse_args()


def create_llm(args):
    """Create an LLM backend using LLMFactory.

    Maps the user-facing --backend flag to factory backend_type strings
    and passes through model name and extra kwargs.
    """
    # Normalise the backend name for the factory
    backend_map = {
        "auto": "auto",
        "ollama": "ollama",
        "lmstudio": "lmstudio_openai",  # default LM Studio mode
        "lmstudio_sdk": "lmstudio_sdk",
        "lmstudio_openai": "lmstudio_openai",
    }
    backend_type = backend_map.get(args.backend, "auto")

    return LLMFactory.create_llm(
        backend_type=backend_type,
        model_name=args.model,
    )


def print_banner():
    """Print a short welcome banner."""
    print("=" * 60)
    print("  AI Local Agent")
    print("  Type your request and press Enter.")
    print("  Type 'exit' or 'quit' to stop.  Ctrl+C also works.")
    print("=" * 60)
    print()


def repl(agent, verbose=False):
    """Read-eval-print loop: read user input, run the agent, print the result."""
    while True:
        try:
            user_input = input("You> ").strip()
        except EOFError:
            # stdin closed
            print("\nBye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Bye!")
            break

        if verbose:
            print(f"[verbose] Sending to agent: {user_input!r}")

        try:
            agent.run(user_input)
        except KeyboardInterrupt:
            print("\n[Interrupted — returning to prompt]")
        except Exception as exc:
            print(f"Error: {exc}")
            if verbose:
                import traceback
                traceback.print_exc()


def main():
    args = parse_arguments()

    print_banner()

    # --- Create LLM backend via factory ---
    print(f"Initialising backend={args.backend}, model={args.model} ...")
    try:
        llm = create_llm(args)
    except Exception as exc:
        print(f"Failed to create LLM backend: {exc}")
        sys.exit(1)
    print("LLM backend ready.\n")

    # --- Build the agent ---
    # UnifiedAgent expects (llm_backend, model_name, verbose).
    # We already created the llm instance via the factory, so we
    # monkey-patch it into the agent to avoid double-initialisation.
    agent = UnifiedAgent.__new__(UnifiedAgent)
    agent.verbose = args.verbose
    agent.history = []
    agent.max_retries = 3
    agent.ui_print = print
    agent.llm_client = llm

    # Initialise tool controllers (same as UnifiedAgent.__init__)
    try:
        from browser_selenium import SeleniumBrowserController
        agent.browser_controller = SeleniumBrowserController()
    except Exception:
        agent.browser_controller = None
        print("Warning: Browser controller not available.")

    try:
        from deep_researcher import DeepResearcher
        agent.deep_researcher = DeepResearcher(browser_controller=agent.browser_controller)
    except Exception:
        agent.deep_researcher = None

    try:
        from secure_terminal import SecureTerminalExecutor
        if args.auto_confirm:
            agent.terminal_executor = SecureTerminalExecutor(
                confirmation_callback=lambda cmd: True
            )
        else:
            agent.terminal_executor = SecureTerminalExecutor(
                confirmation_callback=agent._request_confirmation
            )
    except Exception:
        agent.terminal_executor = None

    try:
        from command_analyzer import CommandAnalyzer
        agent.command_analyzer = CommandAnalyzer()
    except Exception:
        agent.command_analyzer = None

    agent.tools = agent._define_tools()
    # Re-use the system prompt template from the class
    agent.system_prompt_template = UnifiedAgent.__dict__.get(
        "system_prompt_template",
        UnifiedAgent("ollama", "dummy", verbose=False).system_prompt_template
        if False else ""
    )
    # Copy template from class body (set during __init__ in original code)
    # We read it from a temporary instance-less approach:
    agent.system_prompt_template = """
You are a highly capable AI assistant. Your goal is to help the user achieve their objectives by utilizing the tools available to you.
You can browse the web, perform deep research, execute terminal commands, manage files, and interact with the system.

Available Tools:
{tool_descriptions}

Instructions:
1.  Think step-by-step: Break down the user's request into smaller, manageable steps.
2.  Tool Selection: Choose the most appropriate tool for the current step.
3.  Action Format: Respond with a JSON object containing the action and its parameters, enclosed in ```json ... ```.
    Example: ```json {{"action": "deep_research", "params": {{"topic": "Python benefits"}}}} ```
4.  Observation: After you specify an action, the system will execute it and provide an observation.
5.  Error Handling: If an action fails, analyze the error and try an alternative approach.
6.  Final Answer: Once the task is complete, provide a comprehensive final answer starting with "FINAL ANSWER:".

Conversation History:
{history}

User Request: {user_request}

Your Response:
"""

    # --- Ctrl+C handler ---
    def sigint_handler(sig, frame):
        print("\nInterrupted. Bye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, sigint_handler)

    # --- Run the REPL ---
    repl(agent, verbose=args.verbose)


if __name__ == "__main__":
    main()
