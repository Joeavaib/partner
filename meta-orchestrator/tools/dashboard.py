#!/usr/bin/env python3
import os
import sys
import subprocess
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich import box
from datetime import datetime

console = Console()

class CXMDashboard:
    def __init__(self):
        self.workspace = os.getenv("META_CLAWD_WORKSPACE", os.getcwd())
        self.tools_path = os.path.join(self.workspace, "tools")

    def run_tool(self, cmd):
        """Führt einen Befehl aus und gibt das Ergebnis zurück"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout
        except Exception as e:
            return f"Fehler: {str(e)}"

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
        table.add_column("Aktion", style="white")

        table.add_row("1", "Kontext anzeigen (cxm-ctx)")
        table.add_row("2", "Wissen durchsuchen (cxm-rag search)")
        table.add_row("3", "Datei/Ordner indexieren (cxm-rag index)")
        table.add_row("4", "Sessions verwalten (cxm-session)")
        table.add_row("5", "System Prompt lesen (cxm-help)")
        table.add_row("6", "[bold yellow]Neuen Prompt bauen (Prompt Builder)[/bold yellow]")
        table.add_row("0", "Beenden")
        
        return Panel(table, title="[b]Hauptmenü[/b]", border_style="green")

    def display_context(self):
        with console.status("[bold green]Sammle Kontext..."):
            output = self.run_tool(f"python3 {self.tools_path}/context_gatherer.py")
            try:
                data = json.loads(output)
                # Vereinfachte Ansicht
                console.print(Panel(
                    f"Branch: {data['git']['branch']}\n"
                    f"Änderungen: {len(data['git']['uncommitted_changes'].splitlines())} Dateien\n"
                    f"Letzte Edits: {', '.join([os.path.basename(f) for f in data['files']['recent_edits'][:3]])}",
                    title="Aktueller Kontext", border_style="blue"
                ))
            except:
                console.print(output)
        input("\nDrücke Enter zum Zurückkehren...")

    def rag_search(self):
        query = Prompt.ask("\n[cyan]Wonach suchst du?[/cyan]")
        if query:
            with console.status("[bold yellow]Suche im Langzeitgedächtnis..."):
                output = self.run_tool(f"python3 {self.tools_path}/rag_engine.py search '{query}'")
                console.print(Panel(output, title=f"Ergebnisse für: {query}", border_style="yellow"))
        input("\nDrücke Enter zum Zurückkehren...")

    def manage_sessions(self):
        output = self.run_tool(f"python3 {self.tools_path}/session_manager.py list")
        console.print(Panel(output, title="Aktive Sessions", border_style="magenta"))
        
        action = Prompt.ask("\n[magenta](c)reate, (s)tart oder (Enter) zurück[/magenta]", choices=["c", "s", ""], default="")
        if action == "c":
            name = Prompt.ask("Session Name")
            prompt = Prompt.ask("Planungs-Prompt")
            self.run_tool(f"python3 {self.tools_path}/session_manager.py create '{name}' '{prompt}'")
        elif action == "s":
            sid = Prompt.ask("Session ID")
            self.run_tool(f"python3 {self.tools_path}/session_manager.py start {sid}")
        
    def main_loop(self):
        while True:
            console.clear()
            console.print(self.get_header())
            console.print(self.show_menu())
            
            choice = Prompt.ask("\n[green]Wähle eine Aktion[/green]", choices=["1", "2", "3", "4", "5", "6", "0"], default="1")
            
            if choice == "1":
                self.display_context()
            elif choice == "2":
                self.rag_search()
            elif choice == "3":
                path = Prompt.ask("Pfad (z.B. '.' für diesen Ordner oder 'app.py')")
                with console.status(f"Indexiere {path}..."):
                    # Check if it's a directory to use the correct command
                    if os.path.isdir(path):
                        cmd = f"python3 {self.tools_path}/rag_engine.py index-dir {path} --recursive"
                    else:
                        cmd = f"python3 {self.tools_path}/rag_engine.py index {path}"
                    output = self.run_tool(cmd)
                    console.print(output)
                input("\nDrücke Enter...")
            elif choice == "4":
                self.manage_sessions()
            elif choice == "5":
                output = self.run_tool(f"cat {self.workspace}/system_prompt.md")
                console.print(Panel(output, title="System Prompt", border_style="white"))
                input("\nDrücke Enter...")
            elif choice == "6":
                self.build_prompt()
            elif choice == "0":
                console.print("[yellow]Bis bald![/yellow]")
                break

    def build_prompt(self):
        console.clear()
        console.print(Panel("[bold yellow]PROMPT BUILDER[/bold yellow]\nWir bauen jetzt einen hoch-kontextuellen Prompt für deine App.", border_style="yellow"))
        
        goal = Prompt.ask("\n[cyan]1. Was ist dein Ziel? (z.B. 'Erstelle eine neue Route für User-Logins')[/cyan]")
        focus_file = Prompt.ask("[cyan]2. Welche Datei(en) betrifft das hauptsächlich? (z.B. 'app.py' oder 'auth.js')[/cyan]")
        
        with console.status("[bold green]Sammle Kontext und baue Prompt..."):
            context_raw = self.run_tool(f"python3 {self.tools_path}/context_gatherer.py")
            try:
                ctx_data = json.loads(context_raw)
                recent_files = ctx_data.get('files', {}).get('recent_edits', [])[:3]
                git_status = ctx_data.get('git', {}).get('status', 'Keine Änderungen')
            except:
                recent_files = ["Fehler beim Lesen des Kontexts"]
                git_status = "Unbekannt"

            # RAG Search for the focus file to get some insight if possible
            rag_info = ""
            if focus_file:
                 rag_result = self.run_tool(f"python3 {self.tools_path}/rag_engine.py search '{focus_file}' --limit 2")
                 rag_info = f"\n### Relevantes Wissen aus der RAG-Engine:\n{rag_result}\n"

        prompt_text = f"""[System-Anweisung]
Du bist ein KI-Assistent. Ich arbeite gerade an meinem Projekt.
Bitte analysiere den folgenden Kontext und erfülle die Aufgabe präzise.

[Aktueller Kontext]
Git Status: 
{git_status}
Zuletzt bearbeitete Dateien: 
{', '.join(recent_files)}
{rag_info}
[Aufgabe]
{goal}
"""
        
        # Save to a file so it's easy to copy or read
        prompt_file = os.path.join(self.workspace, "current_task_prompt.txt")
        with open(prompt_file, "w") as f:
            f.write(prompt_text)
            
        console.print(Panel(prompt_text, title="Fertiger Prompt", border_style="green"))
        console.print(f"\n[bold green]✓[/bold green] Prompt wurde auch gespeichert unter: [cyan]{prompt_file}[/cyan]")
        console.print("Du kannst diesen Text jetzt kopieren und in unser Gemini-Chatfenster einfügen!")
        input("\nDrücke Enter zum Zurückkehren...")

if __name__ == "__main__":
    dash = CXMDashboard()
    dash.main_loop()
