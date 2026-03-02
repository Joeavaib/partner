#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import pyperclip
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich import box
from datetime import datetime
from pathlib import Path

# Package imports
from cxm import Config, RAGEngine, PromptEnhancer
from cxm.utils.i18n import i18n, _
from cxm.utils.logger import logger

console = Console()

class CXMDashboard:
    def __init__(self):
        # Default workspace logic
        self.config = Config()
        self.workspace = self.config.get_workspace().parent
        
        if os.getenv("META_CLAWD_WORKSPACE"):
            self.workspace = Path(os.getenv("META_CLAWD_WORKSPACE"))
            
        # Tool location logic: check if running from source or installed package
        self.src_root = Path(__file__).parent.parent.parent
        self.tools_path = self.src_root / "tools"
        
        # Initialize i18n
        self.lang = self.config.get('language', 'en')
        i18n.load(self.lang)
        logger.info(f"Dashboard started in {self.lang} mode.")

    def t(self, key):
        """Translate key using central i18n system"""
        return i18n.t(f"dashboard.{key}")

    def run_tool(self, tool_name, args=None):
        """Runs a tool or CLI command securely."""
        if args is None:
            args = []
            
        # Mapping for core functionalities to CLI
        if tool_name == "context_gatherer":
            cmd = ["cxm", "ctx"]
        elif tool_name == "rag_engine":
            if args and args[0] in ["search", "index", "index-dir"]:
                action = args[0]
                if action == "index-dir": action = "index"
                cmd = ["cxm", action] + args[1:]
            else:
                return f"Error: Unknown RAG action {args}"
        elif tool_name == "session_manager":
            # If tool exists in tools/ dir, run it
            tool_file = self.tools_path / f"{tool_name}.py"
            if tool_file.exists():
                cmd = [sys.executable, str(tool_file)] + args
            else:
                return f"Error: Tool {tool_name} not found."
        else:
            return f"Error: Unknown tool {tool_name}"

        try:
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error(f"Command failed: {result.stderr}")
                return f"Error: {result.stderr}"
            return result.stdout
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return f"Error: {str(e)}"

    def get_header(self):
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right")
        grid.add_row(
            "[b]CXM[/b] ORCHESTRATOR",
            datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        )
        return Panel(grid, style="blue")

    def show_menu(self):
        table = Table(box=box.ROUNDED, expand=True, show_header=False)
        table.add_column("Key", style="cyan", width=5)
        table.add_column("Action", style="white")

        table.add_row("1", self.t('prompt_builder'))
        table.add_row("2", self.t('ctx'))
        table.add_row("3", self.t('rag_search'))
        table.add_row("4", self.t('rag_index'))
        table.add_row("5", self.t('sessions'))
        table.add_row("6", self.t('language'))
        table.add_row("0", self.t('exit'))
        
        return Panel(table, title=self.t('menu_title'), border_style="green")

    def display_changes(self):
        with console.status("[bold green]" + self.t('status.gathering_ctx')):
            try:
                from cxm.tools.context_gatherer import gather_all
                data = gather_all()
            except Exception as e:
                logger.warning(f"Direct import of gather_all failed: {e}. Falling back to CLI.")
                output = self.run_tool("context_gatherer")
                try:
                    data = json.loads(output)
                except:
                    console.print(output)
                    input("\n" + self.t('back'))
                    return

            git_data = data.get('git')
            if git_data:
                branch = git_data.get('branch', 'unknown')
                status_raw = git_data.get('status', 'No changes.')
                diff_stats = git_data.get('diff_stats', 'No diff stats available.')
                
                # Layout for changes
                console.print(Panel(f"[b]Branch:[/b] {branch}", border_style="blue"))
                
                status_panel = Panel(status_raw, title="[yellow]Git Status (Short)[/yellow]", border_style="yellow")
                diff_panel = Panel(diff_stats, title="[cyan]Diff Statistics[/cyan]", border_style="cyan")
                
                console.print(status_panel)
                console.print(diff_panel)
            else:
                console.print(Panel("No Git Repository found.", title="Error", border_style="red"))
            
        input("\n" + self.t('back'))

    def settings_language(self):
        console.clear()
        console.print(Panel(f"[bold cyan]{self.t('settings.lang_title')}[/bold cyan]", border_style="cyan"))
        choices = ["en", "de"]
        current = self.config.get('language', 'en')
        new_lang = Prompt.ask(f"\n{self.t('settings.lang_select')} ({self.t('settings.lang_current')}: [bold]{current}[/bold])", choices=choices, default="en" if current == "de" else "de")
        self.config.set('language', new_lang)
        self.lang = new_lang
        i18n.load(new_lang)
        console.print(f"\n[green]{self.t('settings.lang_set')}: {new_lang}[/green]")
        input("\n" + self.t('back'))

    def rag_search(self):
        query = Prompt.ask("\n[cyan]" + self.t('search_query') + "[/cyan]")
        if query:
            with console.status("[bold yellow]" + self.t('status.searching_rag')):
                output = self.run_tool("rag_engine", ["search", query])
                console.print(Panel(output, title=f"{query}", border_style="yellow"))
        input("\n" + self.t('back'))

    def manage_sessions(self):
        output = self.run_tool("session_manager", ["list"])
        console.print(Panel(output, title=self.t('sessions_ui.title'), border_style="magenta"))
        choices = ["c", "s", ""]
        action = Prompt.ask("\n[magenta]" + self.t('session_action') + "[/magenta]", choices=choices, default="")
        if action == "c":
            name = Prompt.ask(self.t('sessions_ui.name'))
            prompt = Prompt.ask(self.t('sessions_ui.plan_prompt'))
            self.run_tool("session_manager", ["create", name, prompt])
        elif action == "s":
            sid = Prompt.ask("Session ID")
            self.run_tool("session_manager", ["start", sid])
        
    def main_loop(self):
        while True:
            console.clear()
            console.print(self.get_header())
            console.print(self.show_menu())
            choice = Prompt.ask("\n[green]" + self.t('choose') + "[/green]", choices=["1", "2", "3", "4", "5", "6", "0"], default="1")
            if choice == "1": self.build_prompt()
            elif choice == "2": self.display_changes()
            elif choice == "3": self.rag_search()
            elif choice == "4":
                path = Prompt.ask(self.t('path_prompt'))
                status_text = self.t('indexing').replace("...", f" {path}...")
                with console.status(f"[bold]{status_text}[/bold]"):
                    cmd_args = ["index", path, "--recursive"] if os.path.isdir(path) else ["index", path]
                    output = self.run_tool("rag_engine", cmd_args)
                    console.print(output)
                input("\n" + self.t('back'))
            elif choice == "5": self.manage_sessions()
            elif choice == "6": self.settings_language()
            elif choice == "0":
                console.print(f"[yellow]{self.t('bye')}[/yellow]")
                break

    def build_prompt(self):
        console.clear()
        console.print(Panel(f"[bold yellow]{self.t('builder.title')}[/bold yellow]\n{self.t('builder.subtitle')}", border_style="yellow"))
        
        # 1. Get initial goal
        prompt_text = Prompt.ask(f"\n[cyan]{self.t('builder.goal_q')}[/cyan]")
        if not prompt_text:
            return

        # Initialize Enhancer logic
        from cxm.tools.context_gatherer import gather_all
        kb_path = self.config.get_workspace()
        rag = RAGEngine(kb_path)
        enhancer = PromptEnhancer(rag)

        # 1. Analysis
        with console.status("[bold green]" + i18n.t('cli.ask.analyzing')):
            analysis = enhancer.intent_analyzer.analyze(prompt_text)
            system_context = gather_all()
        
        console.print(f"\n[cyan]{i18n.t('cli.ask.intent_found')}:[/cyan] {analysis['intent']} ({analysis['confidence']:.0%})")
        
        # 2. Gaps
        gaps = enhancer.refiner.analyze_gaps(prompt_text, analysis['intent'], system_context)
        
        # 3. Show inferred
        if gaps['inferred']:
            console.print(f"\n[green]{i18n.t('cli.ask.inference')}:[/green]")
            for key, value in gaps['inferred'].items():
                console.print(f"  {key}: [dim]{value}[/dim]")
        
        # 4. Completeness
        console.print(f"\n[yellow]{i18n.t('cli.ask.completeness')}: {gaps['completeness']:.0%}[/yellow]")
        
        # 5. Ask questions
        answers = {}
        if gaps['missing_critical']:
            console.print(f"\n[bold red]{i18n.t('cli.ask.critical_gaps')}:[/bold red]\n")
            for key, question in gaps['missing_critical']:
                suggestions = enhancer.refiner._generate_suggestions(key, gaps)
                hint = f" [dim](Suggestions: {', '.join(suggestions)})[/dim]" if suggestions else ""
                answer = Prompt.ask(f"  [bold]{question}[/bold]{hint}")
                if answer.strip():
                    answers[key] = answer
        
        if gaps['missing_optional']:
            if Confirm.ask(f"\n[dim]{i18n.t('cli.ask.optional_ask')}[/dim]", default=False):
                for key, question in gaps['missing_optional']:
                    answer = Prompt.ask(f"  [bold]{question}[/bold]")
                    if answer.strip():
                        answers[key] = answer
        
        # 6. Refine
        with console.status("[bold cyan]Refining prompt..."):
            refined_prompt = enhancer.refiner.refine_prompt(
                prompt_text, analysis['intent'], answers, system_context
            )
        
        # 7. Enhance via RAG
        if Confirm.ask(f"\n{i18n.t('cli.ask.rag_confirm')}", default=True):
            with console.status("[bold yellow]" + i18n.t('cli.ask.searching_rag')):
                candidates = enhancer.retriever.retrieve(
                    query=refined_prompt,
                    context_needs=analysis['context_needs'],
                    k=15,
                )
                selected = enhancer.reranker.rerank(
                    query=refined_prompt,
                    candidates=candidates,
                    top_k=5,
                    token_budget=4000,
                )
                result = enhancer.assembler.assemble(
                    user_prompt=prompt_text,
                    intent=analysis['intent'],
                    contexts=selected,
                    system_context=system_context,
                    max_tokens=4000,
                )
                final_prompt = result['enhanced_prompt']
        else:
            final_prompt = refined_prompt

        # Output & Save
        prompt_file = Path.home() / ".cxm" / "current_task_prompt.txt"
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        prompt_file.write_text(final_prompt, encoding='utf-8')
        
        # Automatic Clipboard Copy
        try:
            pyperclip.copy(final_prompt)
            clipboard_msg = "[bold green]✓ Prompt automatically copied to clipboard![/bold green]"
        except Exception:
            clipboard_msg = "[yellow]! Could not copy to clipboard automatically.[/yellow]"

        console.print(f"\n[bold green]✓[/bold green] {self.t('builder.saved')} [cyan]{prompt_file}[/cyan]")
        console.print(f"{clipboard_msg}")
        
        console.print("\n[bold yellow]--- " + self.t('builder.finished').upper() + " (START) ---[/bold yellow]")
        console.print(final_prompt)
        console.print("[bold yellow]--- " + self.t('builder.finished').upper() + " (END) ---[/bold yellow]")
        
        input("\n" + self.t('back'))

def main():
    try:
        dash = CXMDashboard()
        dash.main_loop()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
