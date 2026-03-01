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
from pathlib import Path

# Add src to pythonpath
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from cxm import Config

console = Console()

class CXMDashboard:
    def __init__(self):
        self.workspace = os.getenv("META_CLAWD_WORKSPACE", os.getcwd())
        self.tools_path = os.path.join(self.workspace, "tools")
        self.config = Config()
        self.translations = {
            'en': {
                'menu_title': '[b]Main Menu[/b]',
                'ctx': 'Show Context (cxm-ctx)',
                'rag_search': 'Search Knowledge (cxm-rag search)',
                'rag_index': 'Index File/Folder (cxm-rag index)',
                'sessions': 'Manage Sessions (cxm-session)',
                'language': 'Language (English)',
                'prompt_builder': '[bold yellow]Build New Prompt (Prompt Builder)[/bold yellow]',
                'exit': 'Exit',
                'choose': 'Choose an action',
                'bye': 'Goodbye!',
                'back': 'Press Enter to return...',
                'search_query': 'What are you looking for?',
                'indexing': 'Indexing...',
                'path_prompt': 'Path (e.g. \'.\' for this folder or \'app.py\')',
                'session_action': '(c)reate, (s)tart or (Enter) back'
            },
            'de': {
                'menu_title': '[b]Hauptmenü[/b]',
                'ctx': 'Kontext anzeigen (cxm-ctx)',
                'rag_search': 'Wissen durchsuchen (cxm-rag search)',
                'rag_index': 'Datei/Ordner indexieren (cxm-rag index)',
                'sessions': 'Sessions verwalten (cxm-session)',
                'language': 'Sprache (Deutsch)',
                'prompt_builder': '[bold yellow]Neuen Prompt bauen (Prompt Builder)[/bold yellow]',
                'exit': 'Beenden',
                'choose': 'Wähle eine Aktion',
                'bye': 'Bis bald!',
                'back': 'Drücke Enter zum Zurückkehren...',
                'search_query': 'Wonach suchst du?',
                'indexing': 'Indexiere...',
                'path_prompt': 'Pfad (z.B. \'.\' für diesen Ordner oder \'app.py\')',
                'session_action': '(c)reate, (s)tart oder (Enter) zurück'
            }
        }

    def t(self, key):
        lang = self.config.get('language', 'en')
        return self.translations.get(lang, self.translations['en']).get(key, key)

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

        table.add_row("1", self.t('ctx'))
        table.add_row("2", self.t('rag_search'))
        table.add_row("3", self.t('rag_index'))
        table.add_row("4", self.t('sessions'))
        table.add_row("5", self.t('language'))
        table.add_row("6", self.t('prompt_builder'))
        table.add_row("0", self.t('exit'))
        
        return Panel(table, title=self.t('menu_title'), border_style="green")

    def display_context(self):
        with console.status("[bold green]" + ( "Sammle Kontext..." if self.config.get('language') == 'de' else "Gathering context..." )):
            output = self.run_tool(f"python3 {self.tools_path}/context_gatherer.py")
            try:
                data = json.loads(output)
                # Vereinfachte Ansicht
                recent_edits = ', '.join([os.path.basename(f) for f in data['files']['recent_edits'][:3]])
                if self.config.get('language') == 'de':
                    title = "Aktueller Kontext"
                    content = f"Branch: {data['git']['branch']}\nÄnderungen: {len(data['git']['uncommitted_changes'].splitlines())} Dateien\nLetzte Edits: {recent_edits}"
                else:
                    title = "Current Context"
                    content = f"Branch: {data['git']['branch']}\nChanges: {len(data['git']['uncommitted_changes'].splitlines())} files\nRecent Edits: {recent_edits}"
                
                console.print(Panel(content, title=title, border_style="blue"))
            except:
                console.print(output)
        input("\n" + self.t('back'))

    def settings_language(self):
        console.clear()
        console.print(Panel("[bold cyan]Language Settings / Spracheinstellungen[/bold cyan]", border_style="cyan"))
        
        choices = ["en", "de"]
        current = self.config.get('language', 'en')
        
        new_lang = Prompt.ask(
            f"\nSelect language / Sprache wählen (current: [bold]{current}[/bold])",
            choices=choices,
            default="en" if current == "de" else "de"
        )
        
        self.config.set('language', new_lang)
        console.print(f"\n[green]Language set to: {new_lang}[/green]")
        input("\n" + self.t('back'))

    def rag_search(self):
        query = Prompt.ask("\n[cyan]" + self.t('search_query') + "[/cyan]")
        if query:
            status_text = "[bold yellow]Suche im Langzeitgedächtnis..." if self.config.get('language') == 'de' else "[bold yellow]Searching long-term memory..."
            with console.status(status_text):
                output = self.run_tool(f"python3 {self.tools_path}/rag_engine.py search '{query}'")
                console.print(Panel(output, title=f"{query}", border_style="yellow"))
        input("\n" + self.t('back'))

    def manage_sessions(self):
        output = self.run_tool(f"python3 {self.tools_path}/session_manager.py list")
        title = "Aktive Sessions" if self.config.get('language') == 'de' else "Active Sessions"
        console.print(Panel(output, title=title, border_style="magenta"))
        
        choices = ["c", "s", ""]
        action = Prompt.ask("\n[magenta]" + self.t('session_action') + "[/magenta]", choices=choices, default="")
        if action == "c":
            name = Prompt.ask("Session Name")
            prompt = Prompt.ask("Planungs-Prompt" if self.config.get('language') == 'de' else "Planning Prompt")
            self.run_tool(f"python3 {self.tools_path}/session_manager.py create '{name}' '{prompt}'")
        elif action == "s":
            sid = Prompt.ask("Session ID")
            self.run_tool(f"python3 {self.tools_path}/session_manager.py start {sid}")
        
    def main_loop(self):
        while True:
            console.clear()
            console.print(self.get_header())
            console.print(self.show_menu())
            
            choice = Prompt.ask("\n[green]" + self.t('choose') + "[/green]", choices=["1", "2", "3", "4", "5", "6", "0"], default="1")
            
            if choice == "1":
                self.display_context()
            elif choice == "2":
                self.rag_search()
            elif choice == "3":
                path = Prompt.ask(self.t('path_prompt'))
                status_text = f"Indexiere {path}..." if self.config.get('language') == 'de' else f"Indexing {path}..."
                with console.status(status_text):
                    # Check if it's a directory to use the correct command
                    if os.path.isdir(path):
                        cmd = f"python3 {self.tools_path}/rag_engine.py index-dir {path} --recursive"
                    else:
                        cmd = f"python3 {self.tools_path}/rag_engine.py index {path}"
                    output = self.run_tool(cmd)
                    console.print(output)
                input("\n" + self.t('back'))
            elif choice == "4":
                self.manage_sessions()
            elif choice == "5":
                self.settings_language()
            elif choice == "6":
                self.build_prompt()
            elif choice == "0":
                console.print(f"[yellow]{self.t('bye')}[/yellow]")
                break

    def build_prompt(self):
        console.clear()
        is_de = self.config.get('language') == 'de'
        title = "PROMPT BUILDER"
        subtitle = "Wir bauen jetzt einen hoch-kontextuellen Prompt für deine App." if is_de else "Building a high-context prompt for your app."
        console.print(Panel(f"[bold yellow]{title}[/bold yellow]\n{subtitle}", border_style="yellow"))
        
        goal_q = "\n[cyan]1. Was ist dein Ziel? (z.B. 'Erstelle eine neue Route für User-Logins')[/cyan]" if is_de else "\n[cyan]1. What is your goal? (e.g. 'Create a new route for user logins')[/cyan]"
        focus_q = "[cyan]2. Welche Datei(en) betrifft das hauptsächlich? (z.B. 'app.py' oder 'auth.js')[/cyan]" if is_de else "[cyan]2. Which file(s) are mainly affected? (e.g. 'app.py' or 'auth.js')[/cyan]"
        
        goal = Prompt.ask(goal_q)
        focus_file = Prompt.ask(focus_q)
        
        status_text = "[bold green]Sammle Kontext und baue Prompt..." if is_de else "[bold green]Gathering context and building prompt..."
        with console.status(status_text):
            context_raw = self.run_tool(f"python3 {self.tools_path}/context_gatherer.py")
            try:
                ctx_data = json.loads(context_raw)
                recent_files = ctx_data.get('files', {}).get('recent_edits', [])[:3]
                git_status = ctx_data.get('git', {}).get('status', 'Keine Änderungen' if is_de else 'No changes')
            except:
                recent_files = ["Fehler beim Lesen des Kontexts" if is_de else "Error reading context"]
                git_status = "Unbekannt" if is_de else "Unknown"

            # RAG Search for the focus file to get some insight if possible
            rag_info = ""
            if focus_file:
                 rag_result = self.run_tool(f"python3 {self.tools_path}/rag_engine.py search '{focus_file}' --limit 2")
                 rag_title = "\n### Relevantes Wissen aus der RAG-Engine:\n" if is_de else "\n### Relevant knowledge from RAG engine:\n"
                 rag_info = f"{rag_title}{rag_result}\n"

        if is_de:
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
        else:
            prompt_text = f"""[System Instruction]
You are an AI assistant. I am currently working on my project.
Please analyze the following context and fulfill the task precisely.

[Current Context]
Git Status: 
{git_status}
Recently edited files: 
{', '.join(recent_files)}
{rag_info}
[Task]
{goal}
"""
        
        # Save to a file so it's easy to copy or read
        prompt_file = os.path.join(self.workspace, "current_task_prompt.txt")
        with open(prompt_file, "w") as f:
            f.write(prompt_text)
            
        final_title = "Fertiger Prompt" if is_de else "Finished Prompt"
        save_msg = f"\n[bold green]✓[/bold green] Prompt wurde auch gespeichert unter: [cyan]{prompt_file}[/cyan]" if is_de else f"\n[bold green]✓[/bold green] Prompt also saved at: [cyan]{prompt_file}[/cyan]"
        copy_msg = "Du kannst diesen Text jetzt kopieren und in unser Gemini-Chatfenster einfügen!" if is_de else "You can now copy this text and paste it into our Gemini chat window!"
        
        console.print(Panel(prompt_text, title=final_title, border_style="green"))
        console.print(save_msg)
        console.print(copy_msg)
        input("\n" + self.t('back'))

if __name__ == "__main__":
    dash = CXMDashboard()
    dash.main_loop()
