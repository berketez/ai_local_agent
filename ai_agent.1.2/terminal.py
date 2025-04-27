"""
Terminal UI - Handles terminal-based user interface

This module provides a clean terminal interface for the AI Helper application,
with support for input, output, and permission requests.
"""


class TerminalUI:
    """Terminal-based user interface for AI Helper."""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the terminal UI.
        
        Args:
            verbose: Whether to show verbose output
        """
        self.verbose = verbose
        self.use_rich = False
        
        # Try to import rich for enhanced terminal UI
        try:
            from rich.console import Console
      
            self.console = Console()
            self.use_rich = True
        except ImportError:
            # Fall back to basic terminal UI if rich is not available
            pass
    
    def display_welcome(self):
        """Display welcome message."""
        welcome_text = """
        ╭───────────────────────────────────────────╮
        │                                           │
        │             🤖 AI Helper 🤖               │
        │                                           │
        │  Run LLM locally and interact with macOS  │
        │                                           │
        ╰───────────────────────────────────────────╯
        """
        
        if self.use_rich:
            from rich.panel import Panel
            self.console.print(Panel(welcome_text, expand=False))
        else:
            print(welcome_text)
    
    def display_status(self, message: str):
        """
        Display a status message.
        
        Args:
            message: The status message to display
        """
        if self.use_rich:
            from rich.panel import Panel
            self.console.print(f"[bold blue]STATUS:[/bold blue] {message}")
        else:
            print(f"STATUS: {message}")
    
    def display_error(self, message: str):
        """
        Display an error message.
        
        Args:
            message: The error message to display
        """
        if self.use_rich:
            self.console.print(f"[bold red]ERROR:[/bold red] {message}")
        else:
            print(f"ERROR: {message}")
    
    def display_response(self, response: str):
        """
        Display the LLM's response.
        
        Args:
            response: The response text to display
        """
        if self.use_rich:
            from rich.markdown import Markdown
            from rich.panel import Panel
            
            # Try to render as markdown
            try:
                md = Markdown(response)
                self.console.print(Panel(md, title="AI Response", border_style="green"))
            except:
                # Fall back to plain text if markdown rendering fails
                self.console.print(Panel(response, title="AI Response", border_style="green"))
        else:
            print("\n--- AI Response ---")
            print(response)
            print("------------------\n")
    
    def display_result(self, result: str):
        """
        Display an action result.
        
        Args:
            result: The result text to display
        """
        if self.use_rich:
            self.console.print(f"[bold green]RESULT:[/bold green] {result}")
        else:
            print(f"RESULT: {result}")
    
    def display_retry_attempt(self, retry_count: int, error_message: str):
        """
        Hata durumunda LLM'in tekrar deneme girişimini göster.
        
        Args:
            retry_count: Kaçıncı deneme olduğu
            error_message: Hata mesajı
        """
        if self.use_rich:
            from rich.panel import Panel
            retry_message = f"Hata oluştu, {retry_count}. kez tekrar deniyorum!\nHata: {error_message}"
            self.console.print(Panel(retry_message, title="LLM Düzeltme Denemesi", border_style="yellow"))
        else:
            print(f"\n--- LLM Düzeltme Denemesi #{retry_count} ---")
            print(f"Hata oluştu, tekrar deniyorum!")
            print(f"Hata: {error_message}")
            print("----------------------------------\n")
    
    def get_input(self) -> str:
        """
        Get input from the user.
        
        Returns:
            The user's input text
        """
        if self.use_rich:
            from rich.prompt import Prompt
            return Prompt.ask("\n[bold cyan]You[/bold cyan]")
        else:
            return input("\nYou: ")
    
    def request_permission(self, message: str) -> bool:
        """
        Request permission from the user.
        
        Args:
            message: The permission request message
            
        Returns:
            True if permission granted, False otherwise
        """
        if self.use_rich:
            from rich.prompt import Confirm
            return Confirm.ask(f"[bold yellow]PERMISSION REQUEST:[/bold yellow] {message}")
        else:
            response = input(f"PERMISSION REQUEST: {message} (y/n): ")
            return response.lower() in ('y', 'yes')
