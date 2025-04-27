# test_unified_agent.py

import sys
from unified_agent import UnifiedAgent

def main():
    """Runs test scenarios for the UnifiedAgent."""
    
    # --- Configuration ---
    # Ensure Ollama is running and the model is pulled (e.g., ollama pull llama3)
    llm_backend = "ollama" 
    model_name = "llama3" # Or llama2, mistral, etc. - make sure it's pulled
    verbose_mode = True
    # ---------------------

    print(f"--- Initializing Unified Agent (Backend: {llm_backend}, Model: {model_name}) ---")
    try:
        agent = UnifiedAgent(llm_backend=llm_backend, model_name=model_name, verbose=verbose_mode)
    except Exception as e:
        print(f"Error initializing agent: {e}")
        print("Please ensure the LLM backend is running and the model is available.")
        sys.exit(1)

    print("--- Agent Initialized ---")

    # --- Test Scenarios ---
    test_scenarios = [
        {
            "name": "Deep Research Test",
            "request": "Perform deep research on the benefits of using Python for web development. Analyze at least 2 sources."
        },
        {
            "name": "Terminal Command Test (Success)",
            "request": "List all python files in the current directory using the terminal."
        },
        {
            "name": "Terminal Command Test (Failure & Retry)",
            "request": "Show the content of a non-existent file named 'imaginary_notes.txt' using the terminal cat command."
        },
        # Add more scenarios as needed
        # {
        #     "name": "Combined Browser and Terminal Test",
        #     "request": "Find the latest stable version of Node.js on nodejs.org and then check the installed node version using the terminal."
        # },
    ]

    for i, scenario in enumerate(test_scenarios):
        print(f"\n--- Running Test Scenario {i+1}: {scenario['name']} ---")
        print(f"User Request: {scenario['request']}")
        try:
            agent.run(scenario["request"])
        except Exception as e:
            print(f"An error occurred during scenario execution: {e}")
        print(f"--- Finished Test Scenario {i+1} ---")

    print("\n--- All Test Scenarios Completed ---")

if __name__ == "__main__":
    main()

