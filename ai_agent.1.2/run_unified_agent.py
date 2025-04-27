# run_unified_agent.py

import sys
import argparse
from unified_agent import UnifiedAgent

def main():
    """Main entry point for the Unified Agent application."""
    parser = argparse.ArgumentParser(
        description="Unified Agent - Run LLM locally with deep research and system control capabilities"
    )
    parser.add_argument(
        "--query", "-q", 
        type=str,
        help="The query or request to process"
    )
    parser.add_argument(
        "--backend",
        type=str,
        choices=["ollama", "lmstudio", "lmstudio_sdk", "lmstudio_openai"],
        default="ollama",
        help="LLM backend to use (default: ollama)"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="llama2",
        help="Model name to use (default: llama2)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Get query from command line or user input
    query = args.query
    if not query:
        query = input("Enter your query or request: ")
    
    print(f"\n--- Initializing Unified Agent ---")
    print(f"Backend: {args.backend}")
    print(f"Model: {args.model}")
    print(f"Verbose: {args.verbose}")
    
    try:
        agent = UnifiedAgent(
            llm_backend=args.backend,
            model_name=args.model,
            verbose=args.verbose
        )
        
        print(f"\n--- Processing Request ---")
        print(f"Query: {query}")
        
        agent.run(query)
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
