import os
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box
from datetime import datetime

from cxm import RAGEngine, PromptEnhancer
from cxm.tools.context_gatherer import gather_all
from cxm.utils.i18n import _

class CXMUI:
    def __init__(self, workspace: Path):
        self.console = Console()
        self.workspace = workspace
        self.rag = RAGEngine(workspace)
        self.enhancer = PromptEnhancer(self.rag)

    def get_header(self):
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right")
        grid.add_row(
            f"[bold blue]CXM[/bold blue] - {_('app.description')}",
            datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        )
        return Panel(grid, style="blue")

    def show_menu(self):
        table = Table(box=box.ROUNDED, expand=True, show_header=False)
        table.add_column("Key", style="cyan", width=5)
        table.add_column("Aktion", style="white")

        table.add_row("1", _('cli.ask.analyzing'))
        table.add_row("2", "Wissen durchsuchen (RAG Search)")
        table.add_row("3", "Projekt neu indexieren")
        table.add_row("4", "Systemkontext anzeigen")
        table.add_row("5", "Workspace initialisieren (Init)")
        table.add_row("0", "Beenden")
        
        return Panel(table, title=f"[b]{_('app.name')} Menu[/b]", border_style="green")

    def display_context(self):
        with self.console.status("[bold green]Sammle Kontext..."):
            data = gather_all()
            
            git_info = "N/A"
            if data.get('git'):
                git_info = f"Branch: {data['git']['branch']}"
            
            recent = "N/A"
            if data.get('files') and data['files'].get('recent_edits'):
                recent = ', '.join([os.path.basename(f) for f in data['files']['recent_edits'][:3]])

            self.console.print(Panel(
                f"{git_info}\n"
                f"Working Dir: {data['files']['cwd']}\n"
                f"Letzte Edits: {recent}",
                title="Aktueller Kontext", border_style="blue"
            ))
        input("\nDrücke Enter zum Zurückkehren...")

    def rag_search(self):
        query = Prompt.ask("\n[cyan]Wonach suchst du?[/cyan]")
        if query:
            with self.console.status("[bold yellow]Suche..."):
                results = self.rag.search(query, k=5)
                if not results:
                    self.console.print("[yellow]Nichts gefunden.[/yellow]")
                else:
                    for res in results:
                        self.console.print(f"- [green]{res['path']}[/green] (Sim: {res['similarity']:.2f})")
        input("\nDrücke Enter...")

    def run_ask(self):
        prompt_text = Prompt.ask("\n[bold yellow]Was ist dein Ziel?[/bold yellow]")
        if not prompt_text:
            return

        # We'll use a trick to reuse the logic from main.py or just implement it here.
        from cxm.main import handle_ask
        class DummyArgs:
            def __init__(self, p, proj, g):
                self.prompt = p.split()
                self.project = proj
                self.github = g
        
        handle_ask(DummyArgs(prompt_text, None, None))
        input("\nDrücke Enter zum Zurückkehren...")

    def run_init(self):
        from cxm.main import handle_init
        handle_init(None)
        input("\nDrücke Enter...")

    def main_loop(self):
        while True:
            self.console.clear()
            self.console.print(self.get_header())
            self.console.print(self.show_menu())
            
            choice = Prompt.ask("\nWähle eine Aktion", choices=["1", "2", "3", "4", "5", "0"], default="1")
            
            if choice == "1":
                self.run_ask()
            elif choice == "2":
                self.rag_search()
            elif choice == "3":
                with self.console.status("Indexiere..."):
                    self.rag.index_directory(Path.cwd())
                self.console.print("[green]Index aktualisiert![/green]")
                input("\nEnter...")
            elif choice == "4":
                self.display_context()
            elif choice == "5":
                self.run_init()
            elif choice == "0":
                self.console.print("[yellow]Bis bald![/yellow]")
                break
