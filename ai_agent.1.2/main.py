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

    # REPL bitti — browser bağlantılarını temizle.
    try:
        agent.close()
    except Exception:
        pass


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
    # LLM factory tarafından zaten oluşturuldu; temiz constructor'a geçir.
    # (Eski __new__ + duplicate system prompt hilesi kaldırıldı.)
    agent = UnifiedAgent(
        llm_client=llm,
        verbose=args.verbose,
        auto_confirm=args.auto_confirm,
    )

    # --- Ctrl+C handler ---
    def sigint_handler(sig, frame):
        print("\nInterrupted. Bye!")
        try:
            agent.close()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, sigint_handler)

    # --- Run the REPL ---
    repl(agent, verbose=args.verbose)


if __name__ == "__main__":
    main()
