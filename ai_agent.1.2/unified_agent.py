# unified_agent.py

import sys
import os
# Add the directory containing this script to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import time
import re
from typing import Dict, Any, List, Optional

# Import LLM client (assuming a refactored/unified client)
# from llm_client import LLMClient # Placeholder for unified LLM client
# Ensure ollama.py and lmstudio.py are in the same directory or PYTHONPATH
# Attempting relative import assuming flat structure for now
try:
    # Use the OllamaLLM class from the provided ollama.py
    from ollama import OllamaLLM 
except ImportError:
    print("Warning: Could not import OllamaLLM from ollama.py. Ollama backend might not work.")
    OllamaLLM = None
try:
    from lmstudio import LMStudioClient # Using existing LM Studio client for now
except ImportError:
    print("Warning: Could not import LMStudioClient from lmstudio.py. LMStudio backend might not work.")
    LMStudioClient = None

# Import LocalModelClient from planner_executor.py
try:
    from planner_executor import LocalModelClient
except ImportError:
    print("Warning: Could not import LocalModelClient from planner_executor.py.")
    LocalModelClient = None

# Import tool controllers
from browser_selenium import SeleniumBrowserController
from deep_researcher import DeepResearcher
from secure_terminal import SecureTerminalExecutor
from command_analyzer import CommandAnalyzer
# Import other controllers if needed (files, apps, screen - adapt/create as needed)
# from files import FileController # Placeholder
# from apps import AppController # Placeholder - macOS specific, needs adaptation
# from screen import ScreenController # Placeholder - macOS specific, needs adaptation

# Import UI (assuming a refactored UI)
# from terminal_ui import EnhancedTerminalUI # Placeholder for enhanced UI

class UnifiedAgent:
    """
    An AI agent that integrates LLM, browser, terminal, and other tools
    to perform tasks with enhanced capabilities like deep research,
    secure execution, and error handling.
    """

    def __init__(self, llm_backend="ollama", model_name="llama2", verbose=False):
        self.verbose = verbose
        self.history = [] # To store conversation/action history
        self.max_retries = 3

        # Initialize UI (using basic print for now)
        # self.ui = EnhancedTerminalUI(verbose=verbose)
        self.ui_print = print # Replace with actual UI calls later

        # Initialize LLM Client based on backend
        self.llm_client = self._initialize_llm(llm_backend, model_name)
        if not self.llm_client:
            raise ValueError("Failed to initialize LLM client.")

        # Initialize Tool Controllers
        self.browser_controller = SeleniumBrowserController() # Uses Chrome by default, handles Firefox fallback
        if not self.browser_controller.driver:
             self.ui_print("Warning: Browser controller failed to initialize.")
             # Decide how to handle this - maybe disable browser actions?
        self.deep_researcher = DeepResearcher(browser_controller=self.browser_controller)
        self.terminal_executor = SecureTerminalExecutor(confirmation_callback=self._request_confirmation)
        self.command_analyzer = CommandAnalyzer()
        # self.file_controller = FileController() # Placeholder
        # self.app_controller = AppController() # Placeholder - needs adaptation for Linux
        # self.screen_controller = ScreenController() # Placeholder - needs adaptation for Linux

        # Define available tools for the LLM
        self.tools = self._define_tools()

        self.system_prompt_template = """
You are a highly capable AI assistant. Your goal is to help the user achieve their objectives by utilizing the tools available to you.
You can browse the web, perform deep research, execute terminal commands, manage files, and interact with the system.

Available Tools:
{tool_descriptions}

Instructions:
1.  **Think Step-by-Step:** Break down the user's request into smaller, manageable steps.
2.  **Tool Selection:** Choose the most appropriate tool for the current step. Only use one tool at a time.
3.  **Action Format:** Respond with a JSON object containing the action and its parameters, enclosed in ```json ... ```.
    Example: ```json {{"action": "deep_research", "params": {{"topic": "Python benefits"}}}} ```
4.  **User Confirmation:** For potentially impactful actions like terminal commands or file modifications, the system will ask the user for confirmation. You don't need to explicitly ask for confirmation in your response.
5.  **Observation:** After you specify an action, the system will execute it and provide an observation. Analyze the observation carefully.
6.  **Error Handling:** If an action fails or the observation indicates an error, analyze the error using the provided information (e.g., command output analysis). Try to formulate an alternative approach or a corrected action. Do not give up easily. Explain the failure and your retry attempt.
7.  **Deep Research:** When asked to research, use the `deep_research` tool to gather information from multiple sources and synthesize the findings. Don't just provide links.
8.  **Interpretation vs. Hallucination:** Provide interpretations and summaries based *only* on the information gathered from tools or previous context. Do not invent information. Cite sources when possible.
9.  **Task Completion:** Ensure the user's overall goal is met before providing a final answer. If you need more steps, continue the process.
10. **Final Answer:** Once the task is complete, provide a comprehensive final answer to the user *without* using the action format. Start the final answer with "FINAL ANSWER:".

Conversation History:
{history}

User Request: {user_request}

Your Response (Think step-by-step and respond with the next action in JSON format, or provide the FINAL ANSWER):
"""

    def _initialize_llm(self, backend, model_name):
        """Initializes the appropriate LLM client."""
        self.ui_print(f"Initializing LLM backend: {backend} with model: {model_name}")
        try:
            if backend == "ollama":
                if not OllamaLLM:
                    raise ImportError("OllamaLLM class not available.")
                # Use the OllamaLLM class from the provided ollama.py
                return OllamaLLM(model_name=model_name) # Assuming host defaults correctly or add it
            elif backend == "lmstudio" or backend == "lmstudio_sdk" or backend == "lmstudio_openai":
                 if not LMStudioClient:
                     raise ImportError("LMStudioClient class not available.")
                 # Assuming LMStudioClient takes model_name and potentially api_base/port
                 # Need to check the actual LMStudioClient implementation from lmstudio.py
                 # Let's assume it provides a compatible generate/chat method
                 return LMStudioClient(model=model_name) # Adapt based on actual LMStudioClient implementation
            else:
                 # Fallback or error for unsupported backend
                 self.ui_print(f"Error: Unsupported or unavailable LLM backend 	'{backend}\' specified.")
                 # Optionally try a default if available
                 if OllamaLLM:
                     self.ui_print("Attempting to use Ollama as default.")
                     return OllamaLLM(model_name=model_name)
                 elif LocalModelClient: # Check if LocalModelClient from planner_executor is available as fallback
                     self.ui_print("Attempting to use LocalModelClient (planner_executor) as default.")
                     return LocalModelClient(model_name=model_name)
                 else:
                     raise ValueError(f"Unsupported LLM backend '{backend}' and no fallback available.")
        except Exception as e:
            self.ui_print(f"Error initializing LLM client {backend}: {e}")
            return None

    def _define_tools(self) -> List[Dict[str, Any]]:
        """Defines the tools available to the agent."""
        # Descriptions should be clear for the LLM
        return [
            {
                "name": "deep_research",
                "description": "Performs in-depth research on a given topic using web searches, visiting multiple sources, analyzing content, and synthesizing findings. Use this for complex questions requiring information gathering.",
                "params": {"topic": "The topic or question to research.", "depth": "(Optional[int]) How deep to analyze each source (1-5, default 3).", "sources": "(Optional[int]) How many sources to analyze (default 5)."}
            },
            {
                "name": "browser_navigate",
                "description": "Navigates the web browser to a specific URL.",
                "params": {"url": "The URL to navigate to."}
            },
            {
                "name": "browser_get_content",
                "description": "Retrieves the content (text or HTML) of the current browser page.",
                "params": {"format": "(Optional[str]) The format of the content ('text' or 'html', default 'text')."}
            },
            {
                "name": "terminal_execute",
                "description": "Executes a shell command in the terminal. Requires user confirmation.",
                "params": {"command": "The shell command to execute."}
            },
            # Add other tools here (file operations, etc.)
            # {
            #     "name": "file_read",
            #     "description": "Reads the content of a specified file.",
            #     "params": {"path": "The absolute path to the file."}
            # },
            # {
            #     "name": "file_write",
            #     "description": "Writes content to a specified file. Requires user confirmation.",
            #     "params": {"path": "The absolute path to the file.", "content": "The content to write."}
            # },
        ]

    def _get_tool_descriptions(self) -> str:
        """Formats tool descriptions for the system prompt."""
        desc = ""
        for tool in self.tools:
            params_desc = ", ".join([f"{name}: {details}" for name, details in tool["params"].items()])
            desc += f"- {tool['name']}: {tool['description']} Parameters: {{{params_desc}}}\n"
        return desc

    def _request_confirmation(self, command: str) -> bool:
        """Handles user confirmation requests via UI."""
        # Replace with actual UI call
        response = input(f"CONFIRM: Execute command \"{command}\"? (y/n): ")
        return response.lower() in ('y', 'yes')

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parses the LLM response to extract action or final answer."""
        action = None
        final_answer = None

        if "FINAL ANSWER:" in response:
            final_answer = response.split("FINAL ANSWER:", 1)[1].strip()
        else:
            # Try to extract JSON action
            match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
            if match:
                try:
                    action_json = match.group(1)
                    action = json.loads(action_json)
                    if "action" not in action or "params" not in action:
                         # Invalid action format
                         action = {"action": "error", "params": {"error": "Invalid action format in LLM response.", "response": response}}
                except json.JSONDecodeError as e:
                    action = {"action": "error", "params": {"error": f"Failed to decode JSON action: {e}", "response": response}}
            else:
                 # No valid action or final answer found
                 action = {"action": "error", "params": {"error": "No valid action or final answer found in LLM response.", "response": response}}

        return {"action": action, "final_answer": final_answer}

    def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the action specified by the LLM."""
        action_name = action.get("action")
        params = action.get("params", {})
        observation = {"action_name": action_name, "params": params}

        self.ui_print(f"Executing action: {action_name} with params: {params}")

        try:
            if action_name == "deep_research":
                result = self.deep_researcher.research_topic(
                    topic=params.get("topic"),
                    depth=params.get("depth", 3),
                    sources=params.get("sources", 5)
                )
                observation.update(result)
            elif action_name == "browser_navigate":
                if self.browser_controller.driver:
                    result = self.browser_controller.open_url(params.get("url"))
                    observation.update(result)
                else:
                    observation.update({"success": False, "error": "Browser not available."})
            elif action_name == "browser_get_content":
                 if self.browser_controller.driver:
                    result = self.browser_controller.get_page_content(params.get("format", "text"))
                    observation.update(result)
                 else:
                    observation.update({"success": False, "error": "Browser not available."})
            elif action_name == "terminal_execute":
                command = params.get("command")
                if command:
                    # Secure executor handles confirmation internally
                    result = self.terminal_executor.execute_command(command, require_confirmation=True)
                    observation.update(result)
                    # Analyze the result if it failed
                    if not result.get("success", False):
                        analysis = self.command_analyzer.analyze_command_result(command, result)
                        observation["analysis"] = analysis
                else:
                    observation.update({"success": False, "error": "Missing 'command' parameter."})
            # Add other action handlers here
            # elif action_name == "file_read":
            #     result = self.file_controller.read_file(params.get("path")) # Assuming FileController exists
            #     observation.update(result)
            # elif action_name == "file_write":
            #     # Add confirmation logic here or in the controller
            #     result = self.file_controller.write_file(params.get("path"), params.get("content")) # Assuming FileController exists
            #     observation.update(result)
            elif action_name == "error":
                 observation.update({"success": False, "error": params.get("error", "Unknown error in LLM response processing.")})
            else:
                observation.update({"success": False, "error": f"Unknown action: {action_name}"})

        except Exception as e:
            self.ui_print(f"Error executing action {action_name}: {e}")
            observation.update({"success": False, "error": f"Exception during action execution: {e}"})

        return observation


    def run(self, user_request: str):
        """Runs the agent interaction loop."""
        self.history = [{
            "role": "user", 
            "content": user_request
        }]
        retries = 0

        while retries <= self.max_retries:
            # Prepare context for LLM
            # Format history for the prompt
            formatted_history = []
            for msg in self.history:
                role = msg.get("role")
                content = msg.get("content")
                if role == "system" and isinstance(content, str) and content.startswith("OBSERVATION:"):
                     # Keep observations concise for the prompt if they are too long
                     try:
                         obs_data = json.loads(content.replace("OBSERVATION: ", ""))
                         # Shorten potentially long fields like content or stdout
                         if "content" in obs_data and isinstance(obs_data["content"], str) and len(obs_data["content"]) > 500:
                             obs_data["content"] = obs_data["content"][:500] + "... (truncated)"
                         if "stdout" in obs_data and isinstance(obs_data["stdout"], str) and len(obs_data["stdout"]) > 500:
                             obs_data["stdout"] = obs_data["stdout"][:500] + "... (truncated)"
                         if "research_notes" in obs_data: # Don't include full notes in history prompt
                             obs_data.pop("research_notes")
                         formatted_history.append(f"OBSERVATION: {json.dumps(obs_data)}")
                     except:
                          formatted_history.append(content[:1000] + "... (truncated)" if len(content) > 1000 else content)
                elif isinstance(content, str):
                    formatted_history.append(f"{role.upper()}: {content[:1000] + '... (truncated)' if len(content) > 1000 else content}")
            history_str = "\n".join(formatted_history)
            
            tool_desc_str = self._get_tool_descriptions()
            
            # Construct the prompt using the template
            current_prompt = self.system_prompt_template.format(
                tool_descriptions=tool_desc_str,
                history=history_str,
                user_request=user_request # Keep original request for context
            )
            
            if self.verbose:
                self.ui_print("--- Sending Prompt to LLM ---")
                self.ui_print(current_prompt)
                self.ui_print("-----------------------------")

            # Get LLM response
            try:
                # Adapt this call based on the actual LLM client interface
                # Assuming LocalModelClient has a 'generate' or similar method
                # The planner_executor.LocalModelClient uses chat_completion which takes messages list
                # Let's adapt to use chat_completion if possible, otherwise generate
                if hasattr(self.llm_client, 'chat_completion'):
                     # Need to structure history correctly for chat_completion
                     llm_response_obj = self.llm_client.chat_completion(self.history)
                     # Assuming response object has structure like OpenAI's
                     llm_response_content = llm_response_obj.choices[0].message.content
                     # Handle tool calls if the client supports it directly (like planner_executor tried)
                     # tool_calls = llm_response_obj.choices[0].message.tool_calls
                elif hasattr(self.llm_client, 'generate'):
                     llm_response_content = self.llm_client.generate(current_prompt) # Adapt this call
                else:
                     raise NotImplementedError("LLM client does not have a compatible generate/chat_completion method.")
                     
            except Exception as e:
                 self.ui_print(f"Error getting LLM response: {e}")
                 llm_response_content = f"Error: Could not get response from LLM. {e}"
                 self.history.append({"role": "system", "content": f"LLM Error: {e}"})
                 break # Exit loop on LLM error

            self.history.append({"role": "assistant", "content": llm_response_content})
            self.ui_print(f"\nASSISTANT:\n{llm_response_content}")

            # Parse LLM response
            parsed_response = self._parse_llm_response(llm_response_content)
            action = parsed_response["action"]
            final_answer = parsed_response["final_answer"]

            if final_answer:
                self.ui_print(f"\nFINAL ANSWER:\n{final_answer}")
                break # Task complete

            if action:
                # Execute action
                observation = self._execute_action(action)
                observation_str = json.dumps(observation)

                self.history.append({"role": "system", "content": f"OBSERVATION: {observation_str}"}) # Use full observation in history
                self.ui_print(f"\nOBSERVATION:\n{json.dumps(observation, indent=2)}") # Print formatted observation

                # Check if action failed and max retries reached
                if not observation.get("success", False):
                    retries += 1
                    self.ui_print(f"Action failed. Retry {retries}/{self.max_retries}.")
                    if retries >= self.max_retries:
                        self.ui_print("Max retries reached. Aborting task.")
                        failure_message = f"FINAL ANSWER: Failed to complete the task after {self.max_retries} retries. Last error: {observation.get('error', 'Unknown error')}"
                        self.ui_print(failure_message)
                        break
                    # Error analysis is included in the observation for the next LLM step
                else:
                    # Reset retries on successful action
                    retries = 0
            else:
                # No action and no final answer - LLM might be stuck
                self.ui_print("LLM did not provide a valid action or final answer. Asking to clarify or try again.")
                self.history.append({"role": "system", "content": "System: Please provide a valid action in JSON format or a final answer."})
                retries += 1 # Count this as a retry attempt
                if retries >= self.max_retries:
                     self.ui_print("Max retries reached. Aborting task.")
                     break

        # Cleanup
        if self.browser_controller:
            self.browser_controller.close_browser()
        self.ui_print("Agent finished.")

# Need to adapt main.py or create a new entry point to use this UnifiedAgent class.
# Also need to refine LLM client initialization and calls based on actual implementations.
# Need to implement/adapt FileController, AppController, ScreenController for Linux if needed.
# Need to integrate a proper TerminalUI class.

