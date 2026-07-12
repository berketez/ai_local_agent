# unified_agent.py

import sys
import os
# Add the directory containing this script to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import re
from typing import Dict, Any, List, Optional

# --- LLM backends ---
try:
    from ollama_backend import OllamaLLM
except ImportError:
    print("Warning: Could not import OllamaLLM. Ollama backend might not work.")
    OllamaLLM = None
try:
    from lmstudio_backend import LMStudioOpenAI
except ImportError:
    print("Warning: Could not import LMStudioOpenAI. LMStudio backend might not work.")
    LMStudioOpenAI = None
try:
    from planner_executor import LocalModelClient
except ImportError:
    LocalModelClient = None

# --- Tool controllers ---
from deep_researcher import DeepResearcher
from secure_terminal import SecureTerminalExecutor
from command_analyzer import CommandAnalyzer
from files import FileController
from apps import AppController
from screen import ScreenController

# Permission system (manager.py + registry.py — fonksiyonel, artık bağlanıyor)
try:
    from manager import PermissionManager
except ImportError:
    PermissionManager = None

# Yeni: openclaw'dan port edilen Playwright+CDP browser (computer/ paketi)
try:
    from computer import PlaywrightBrowser, PW_AVAILABLE
except Exception:
    PlaywrightBrowser = None
    PW_AVAILABLE = False

# Eski Selenium browser — Playwright yoksa fallback
try:
    from browser_selenium import SeleniumBrowserController
except Exception:
    SeleniumBrowserController = None

# Yeni: openclaw exec-approvals güvenlik modeli (security/ paketi)
try:
    from security import ExecApprovals
except Exception:
    ExecApprovals = None


# Aksiyon adı -> izin kategorisi eşlemesi.
# manager.PermissionManager grant'leri kategori bazlı tutar; bu harita
# tüm araçlarımızı doğru kategoriye bağlar (default-deny bilinmeyen aksiyonlarda).
ACTION_CATEGORY = {
    # browser (Playwright veya Selenium — hepsi "browser" kategorisi)
    "browser_navigate": "browser",
    "browser_get_content": "browser",
    "browser_snapshot": "browser",
    "browser_click": "browser",
    "browser_type": "browser",
    "browser_fill": "browser",
    "browser_screenshot": "browser",
    "deep_research": "browser",
    # dosya
    "file_read": "files",
    "file_write": "files",
    "file_delete": "files",
    "file_list": "files",
    # uygulama
    "app_open": "apps",
    "app_close": "apps",
    "app_list": "apps",
    # ekran
    "screen_capture": "screen",
    "screen_read_text": "screen",
}

# Kullanıcıya izin sorulurken gösterilecek okunabilir açıklama üreticisi.
def _perm_details(action_name: str, params: Dict[str, Any]) -> str:
    if action_name.startswith("browser"):
        return params.get("url") or params.get("ref") or params.get("text") or ""
    if action_name.startswith("file"):
        return params.get("path", "")
    if action_name.startswith("app"):
        return params.get("app_name", "")
    return ""


class UnifiedAgent:
    """
    LLM + browser + terminal + files/apps/screen araçlarını izin denetimiyle
    birleştiren yerel agent. openclaw'dan port edilen Playwright+CDP browser ve
    exec-approvals güvenlik modelini kullanır.
    """

    system_prompt_template = """
You are a highly capable AI assistant. Your goal is to help the user achieve their objectives by utilizing the tools available to you.
You can browse the web, perform deep research, execute terminal commands, manage files, control apps, and read the screen.

Available Tools:
{tool_descriptions}

Instructions:
1.  Think step-by-step: break the request into small steps.
2.  Tool selection: choose the single most appropriate tool for the current step.
3.  Action format: respond with a JSON object containing the action and its parameters, enclosed in ```json ... ```.
    Example: ```json {{"action": "browser_navigate", "params": {{"url": "https://example.com"}}}} ```
4.  Browser workflow: to interact with a page, first `browser_navigate`, then `browser_snapshot` to get element refs (e1, e2...), then `browser_click`/`browser_type`/`browser_fill` using those refs. Refs come only from the latest snapshot.
5.  Observation: after each action the system returns an observation. Analyze it.
6.  Permissions: side-effectful actions may prompt the user; you do not need to ask for confirmation yourself.
7.  Error handling: if an action fails, analyze the error and try an alternative.
8.  Final answer: once the task is complete, respond WITHOUT the action format, starting with "FINAL ANSWER:".

Conversation History:
{history}

User Request: {user_request}

Your Response (next action in JSON, or FINAL ANSWER):
"""

    def __init__(self, llm_backend="ollama", model_name="llama2", verbose=False,
                 llm_client=None, auto_confirm=False):
        self.verbose = verbose
        self.history: List[Dict[str, Any]] = []
        self.max_retries = 3
        self.auto_confirm = auto_confirm
        self.ui_print = print

        # LLM: dışarıdan verildiyse (factory) onu kullan, yoksa kendin kur.
        if llm_client is not None:
            self.llm_client = llm_client
        else:
            self.llm_client = self._initialize_llm(llm_backend, model_name)
        if not self.llm_client:
            raise ValueError("Failed to initialize LLM client.")

        # --- İzin sistemi (default-deny) ---
        self.perm = None
        if PermissionManager is not None:
            self.perm = PermissionManager()
            # Tüm araçlarımızı doğru kategoriye bağla (instance-level, manager.py'ye dokunmadan).
            self.perm.ACTION_TYPE_TO_CATEGORY = {
                **PermissionManager.ACTION_TYPE_TO_CATEGORY,
                **ACTION_CATEGORY,
            }
            if auto_confirm:
                # Test modu: tüm kategorilere oturum grant'i.
                self.perm._session_grants |= {
                    "browser", "files", "apps", "input", "screen", "llm",
                }

        # --- Browser: Playwright (tercih) veya Selenium (fallback) ---
        self.browser = None            # Playwright browser (lazy)
        self.browser_controller = None  # Selenium fallback
        self._browser_kind = None
        if PW_AVAILABLE and PlaywrightBrowser is not None:
            self._browser_kind = "playwright"
        elif SeleniumBrowserController is not None:
            self._browser_kind = "selenium"

        # --- Diğer controller'lar ---
        self.file_controller = FileController()
        self.app_controller = AppController()
        self.screen_controller = ScreenController()

        # --- Terminal: exec-approvals modeliyle güvenli çalıştırma ---
        self.exec_approvals = ExecApprovals() if ExecApprovals is not None else None
        self.terminal_executor = SecureTerminalExecutor(
            confirmation_callback=self._request_confirmation,
            exec_approvals=self.exec_approvals,
            auto_confirm=auto_confirm,
        )
        self.command_analyzer = CommandAnalyzer()

        # Deep research eski Selenium controller'a bağlı; lazy kur.
        self.deep_researcher = None

        self.tools = self._define_tools()

    # ------------------------------------------------------------------ #
    # Browser lazy-init (yalnız ilk browser aksiyonunda başlatılır)
    # ------------------------------------------------------------------ #
    def _ensure_browser(self):
        """Browser'ı ihtiyaç anında başlatır. Playwright tercih, Selenium fallback."""
        if self._browser_kind == "playwright":
            if self.browser is None:
                self.browser = PlaywrightBrowser()
                res = self.browser.start()
                if isinstance(res, dict) and not res.get("success", True):
                    self.ui_print(f"Playwright başlatılamadı: {res.get('error')}")
                    # Selenium'a düş
                    self._browser_kind = "selenium" if SeleniumBrowserController else None
                    self.browser = None
        if self._browser_kind == "selenium" and self.browser_controller is None:
            if SeleniumBrowserController is not None:
                self.browser_controller = SeleniumBrowserController()
        return self._browser_kind

    def _ensure_deep_researcher(self):
        if self.deep_researcher is None:
            # DeepResearcher Selenium controller ister.
            if self.browser_controller is None and SeleniumBrowserController is not None:
                self.browser_controller = SeleniumBrowserController()
            self.deep_researcher = DeepResearcher(browser_controller=self.browser_controller)
        return self.deep_researcher

    def _initialize_llm(self, backend, model_name):
        self.ui_print(f"Initializing LLM backend: {backend} with model: {model_name}")
        try:
            if backend == "ollama":
                if not OllamaLLM:
                    raise ImportError("OllamaLLM class not available.")
                return OllamaLLM(model_name=model_name)
            elif backend in ("lmstudio", "lmstudio_sdk", "lmstudio_openai"):
                if not LMStudioOpenAI:
                    raise ImportError("LMStudioOpenAI class not available.")
                return LMStudioOpenAI(model_name=model_name)
            else:
                if OllamaLLM:
                    self.ui_print("Attempting to use Ollama as default.")
                    return OllamaLLM(model_name=model_name)
                elif LocalModelClient:
                    return LocalModelClient(model_name=model_name)
                raise ValueError(f"Unsupported LLM backend '{backend}'.")
        except Exception as e:
            self.ui_print(f"Error initializing LLM client {backend}: {e}")
            return None

    # ------------------------------------------------------------------ #
    # Araç tanımları
    # ------------------------------------------------------------------ #
    def _define_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "deep_research",
                "description": "Performs in-depth research on a topic (web search, multiple sources, synthesis).",
                "params": {"topic": "The topic to research.", "depth": "(Optional int 1-5, default 3).", "sources": "(Optional int, default 5)."},
            },
            {
                "name": "browser_navigate",
                "description": "Navigate the browser to a URL.",
                "params": {"url": "The URL to navigate to."},
            },
            {
                "name": "browser_snapshot",
                "description": "Get an accessibility snapshot of the current page with element refs (e1, e2...) for clicking/typing. Use before interacting.",
                "params": {"interactive": "(Optional bool, default true) only interactive elements."},
            },
            {
                "name": "browser_click",
                "description": "Click an element by its ref from the latest snapshot.",
                "params": {"ref": "Element ref, e.g. e5."},
            },
            {
                "name": "browser_type",
                "description": "Type text into an element by ref.",
                "params": {"ref": "Element ref.", "text": "Text to type."},
            },
            {
                "name": "browser_fill",
                "description": "Fill an input field by ref (clears then sets value).",
                "params": {"ref": "Element ref.", "text": "Value to fill."},
            },
            {
                "name": "browser_get_content",
                "description": "Get the current page content as text or html.",
                "params": {"format": "(Optional 'text' or 'html', default 'text')."},
            },
            {
                "name": "browser_screenshot",
                "description": "Take a screenshot of the current page. Returns a saved file path.",
                "params": {"full_page": "(Optional bool, default false)."},
            },
            {
                "name": "terminal_execute",
                "description": "Execute a shell command. Subject to the exec-approvals security policy.",
                "params": {"command": "The shell command to execute."},
            },
            {
                "name": "file_read",
                "description": "Read the content of a file.",
                "params": {"path": "Absolute path to the file."},
            },
            {
                "name": "file_write",
                "description": "Write content to a file (creates parent dirs).",
                "params": {"path": "Absolute path.", "content": "Content to write.", "append": "(Optional bool)."},
            },
            {
                "name": "file_delete",
                "description": "Delete a file.",
                "params": {"path": "Absolute path."},
            },
            {
                "name": "file_list",
                "description": "List the contents of a directory.",
                "params": {"path": "Absolute directory path."},
            },
            {
                "name": "app_open",
                "description": "Open a macOS application by name.",
                "params": {"app_name": "Application name, e.g. Safari."},
            },
            {
                "name": "app_close",
                "description": "Close a macOS application by name.",
                "params": {"app_name": "Application name."},
            },
            {
                "name": "app_list",
                "description": "List running applications.",
                "params": {},
            },
            {
                "name": "screen_capture",
                "description": "Take a screenshot of the whole screen (or a region).",
                "params": {"left": "(Optional int)", "top": "(Optional int)", "width": "(Optional int)", "height": "(Optional int)"},
            },
            {
                "name": "screen_read_text",
                "description": "OCR the screen (or a region) and return the text.",
                "params": {"left": "(Optional int)", "top": "(Optional int)", "width": "(Optional int)", "height": "(Optional int)"},
            },
        ]

    def _get_tool_descriptions(self) -> str:
        desc = ""
        for tool in self.tools:
            if tool["params"]:
                params_desc = ", ".join([f"{name}: {details}" for name, details in tool["params"].items()])
            else:
                params_desc = "none"
            desc += f"- {tool['name']}: {tool['description']} Parameters: {{{params_desc}}}\n"
        return desc

    def _request_confirmation(self, command: str) -> bool:
        if self.auto_confirm:
            return True
        response = input(f"CONFIRM: Execute command \"{command}\"? (y/n): ")
        return response.lower() in ("y", "yes")

    def _check_permission(self, action_name: str, params: Dict[str, Any]) -> bool:
        """İzin denetimi. Perm sistemi yoksa (import başarısız) izin ver."""
        if self.perm is None:
            return True
        details = _perm_details(action_name, params)
        return self.perm.check_permission(action_name, details)

    # ------------------------------------------------------------------ #
    # Aksiyon yürütme
    # ------------------------------------------------------------------ #
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        action = None
        final_answer = None
        if "FINAL ANSWER:" in response:
            final_answer = response.split("FINAL ANSWER:", 1)[1].strip()
        else:
            match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
            if match:
                try:
                    action = json.loads(match.group(1))
                    if "action" not in action:
                        action = {"action": "error", "params": {"error": "Invalid action format.", "response": response}}
                    elif "params" not in action:
                        action["params"] = {}
                except json.JSONDecodeError as e:
                    action = {"action": "error", "params": {"error": f"Failed to decode JSON: {e}", "response": response}}
            else:
                action = {"action": "error", "params": {"error": "No valid action or final answer found.", "response": response}}
        return {"action": action, "final_answer": final_answer}

    def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_name = action.get("action")
        params = action.get("params", {}) or {}
        observation = {"action_name": action_name, "params": params}

        self.ui_print(f"Executing action: {action_name} with params: {params}")

        # --- İzin kapısı (terminal hariç; onun kendi exec-approvals akışı var) ---
        if action_name in ACTION_CATEGORY:
            if not self._check_permission(action_name, params):
                observation.update({"success": False, "error": "Permission denied by user."})
                return observation

        try:
            # ---------------- deep research ----------------
            if action_name == "deep_research":
                dr = self._ensure_deep_researcher()
                result = dr.research_topic(
                    topic=params.get("topic"),
                    depth=params.get("depth", 3),
                    sources=params.get("sources", 5),
                )
                observation.update(result)

            # ---------------- browser ----------------
            elif action_name in ("browser_navigate", "browser_snapshot", "browser_click",
                                 "browser_type", "browser_fill", "browser_get_content",
                                 "browser_screenshot"):
                observation.update(self._execute_browser_action(action_name, params))

            # ---------------- terminal ----------------
            elif action_name == "terminal_execute":
                command = params.get("command")
                if command:
                    result = self.terminal_executor.execute_command(command, require_confirmation=True)
                    observation.update(result)
                    if not result.get("success", False):
                        analysis = self.command_analyzer.analyze_command_result(command, result)
                        observation["analysis"] = analysis
                else:
                    observation.update({"success": False, "error": "Missing 'command' parameter."})

            # ---------------- files ----------------
            elif action_name in ("file_read", "file_write", "file_delete", "file_list"):
                observation.update(self.file_controller.execute_file_action(action_name, params))

            # ---------------- apps ----------------
            elif action_name in ("app_open", "app_close", "app_list"):
                observation.update(self.app_controller.execute_app_action(action_name, params))

            # ---------------- screen ----------------
            elif action_name in ("screen_capture", "screen_read_text"):
                observation.update(self.screen_controller.execute_screen_action(action_name, params))

            elif action_name == "error":
                observation.update({"success": False, "error": params.get("error", "Unknown error.")})
            else:
                observation.update({"success": False, "error": f"Unknown action: {action_name}"})

        except Exception as e:
            self.ui_print(f"Error executing action {action_name}: {e}")
            observation.update({"success": False, "error": f"Exception during action execution: {e}"})

        return observation

    def _execute_browser_action(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Browser aksiyonlarını aktif motora (Playwright/Selenium) yönlendirir."""
        kind = self._ensure_browser()
        if kind is None:
            return {"success": False, "error": "No browser engine available (install playwright or selenium)."}

        # ---- Playwright yolu (tam yetenek) ----
        if kind == "playwright" and self.browser is not None:
            if action_name == "browser_navigate":
                return self.browser.navigate(params.get("url"))
            if action_name == "browser_snapshot":
                return self.browser.snapshot(interactive=params.get("interactive", True))
            if action_name == "browser_click":
                return self.browser.act("click", ref=params.get("ref"))
            if action_name == "browser_type":
                return self.browser.act("type", ref=params.get("ref"), text=params.get("text"))
            if action_name == "browser_fill":
                return self.browser.act("fill", ref=params.get("ref"), text=params.get("text"))
            if action_name == "browser_get_content":
                return self.browser.get_content(params.get("format", "text"))
            if action_name == "browser_screenshot":
                return self.browser.screenshot(full_page=params.get("full_page", False))
            return {"success": False, "error": f"Unsupported browser action: {action_name}"}

        # ---- Selenium fallback (dar: navigate + get_content) ----
        bc = self.browser_controller
        if bc is None or not getattr(bc, "driver", None):
            return {"success": False, "error": "Browser not available."}
        if action_name == "browser_navigate":
            return bc.open_url(params.get("url"))
        if action_name == "browser_get_content":
            return bc.get_page_content(params.get("format", "text"))
        return {"success": False,
                "error": f"'{action_name}' requires Playwright; only navigate/get_content available with Selenium."}

    # ------------------------------------------------------------------ #
    # Ana döngü (oturum hafızası korunur)
    # ------------------------------------------------------------------ #
    def run(self, user_request: str):
        # Oturum hafızası: history sıfırlanmaz, kullanıcı turu eklenir.
        self.history.append({"role": "user", "content": user_request})
        retries = 0

        while retries <= self.max_retries:
            history_str = self._format_history()
            tool_desc_str = self._get_tool_descriptions()
            current_prompt = self.system_prompt_template.format(
                tool_descriptions=tool_desc_str,
                history=history_str,
                user_request=user_request,
            )

            if self.verbose:
                self.ui_print("--- Sending Prompt to LLM ---")
                self.ui_print(current_prompt)
                self.ui_print("-----------------------------")

            try:
                if hasattr(self.llm_client, "generate"):
                    response_obj = self.llm_client.generate(current_prompt)
                    if isinstance(response_obj, dict):
                        llm_response_content = self.llm_client.extract_text_from_response(response_obj)
                    else:
                        llm_response_content = str(response_obj)
                elif hasattr(self.llm_client, "chat_completion"):
                    llm_response_obj = self.llm_client.chat_completion(self.history)
                    llm_response_content = llm_response_obj.choices[0].message.content
                else:
                    raise NotImplementedError("LLM client has no generate/chat_completion method.")
            except Exception as e:
                self.ui_print(f"Error getting LLM response: {e}")
                self.history.append({"role": "system", "content": f"LLM Error: {e}"})
                break

            self.history.append({"role": "assistant", "content": llm_response_content})
            self.ui_print(f"\nASSISTANT:\n{llm_response_content}")

            parsed = self._parse_llm_response(llm_response_content)
            action = parsed["action"]
            final_answer = parsed["final_answer"]

            if final_answer:
                self.ui_print(f"\nFINAL ANSWER:\n{final_answer}")
                break

            if action:
                observation = self._execute_action(action)
                self.history.append({"role": "system", "content": f"OBSERVATION: {json.dumps(observation)}"})
                self.ui_print(f"\nOBSERVATION:\n{json.dumps(observation, indent=2, ensure_ascii=False)}")

                if not observation.get("success", False):
                    retries += 1
                    self.ui_print(f"Action failed. Retry {retries}/{self.max_retries}.")
                    if retries >= self.max_retries:
                        msg = f"FINAL ANSWER: Failed after {self.max_retries} retries. Last error: {observation.get('error', 'Unknown')}"
                        self.ui_print(msg)
                        break
                else:
                    retries = 0
            else:
                self.history.append({"role": "system", "content": "System: Provide a valid JSON action or a FINAL ANSWER."})
                retries += 1
                if retries >= self.max_retries:
                    self.ui_print("Max retries reached. Aborting task.")
                    break

    def _format_history(self) -> str:
        formatted = []
        for msg in self.history:
            role = msg.get("role")
            content = msg.get("content")
            if not isinstance(content, str):
                continue
            if role == "system" and content.startswith("OBSERVATION:"):
                try:
                    obs = json.loads(content[len("OBSERVATION: "):])
                    for k in ("content", "stdout", "snapshot"):
                        if isinstance(obs.get(k), str) and len(obs[k]) > 500:
                            obs[k] = obs[k][:500] + "... (truncated)"
                    obs.pop("research_notes", None)
                    formatted.append(f"OBSERVATION: {json.dumps(obs, ensure_ascii=False)}")
                except Exception:
                    formatted.append(content[:1000])
            else:
                trimmed = content if len(content) <= 1000 else content[:1000] + "... (truncated)"
                formatted.append(f"{role.upper()}: {trimmed}")
        return "\n".join(formatted)

    def close(self):
        """Agent kapanışında browser bağlantılarını temizler."""
        try:
            if self.browser is not None:
                self.browser.close()
        except Exception:
            pass
        try:
            if self.browser_controller is not None:
                self.browser_controller.close_browser()
        except Exception:
            pass
        self.ui_print("Agent finished.")
