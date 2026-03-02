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

# Package imports
from cxm import Config

console = Console()

class CXMDashboard:
    def __init__(self):
        # Default workspace logic
        config = Config()
        self.workspace = config.get_workspace().parent # Parent of knowledge-base is usually the project root
        
        # If we are in a specific project via env
        if os.getenv("META_CLAWD_WORKSPACE"):
            self.workspace = Path(os.getenv("META_CLAWD_WORKSPACE"))
            
        self.tools_path = self.workspace / "tools"
        self.config = config
        
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
                'path_prompt': 'Path (e.g. '.' for this folder or 'app.py')',
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
                'path_prompt': 'Pfad (z.B. '.' für diesen Ordner oder 'app.py')',
                'session_action': '(c)reate, (s)tart oder (Enter) zurück'
            }
        }

    def t(self, key):
        lang = self.config.get('language', 'en')
        return self.translations.get(lang, self.translations['en']).get(key, key)

    def run_tool(self, tool_name, args=""):
        """Runs a tool from the tools directory or via cxm CLI if available"""
        # Try finding the tool in the project tools dir first
        tool_file = self.tools_path / f"{tool_name}.py"
        
        if tool_file.exists():
            cmd = f"python3 {tool_file} {args}"
        else:
            # Fallback to cxm CLI commands for some actions
            if tool_name == "context_gatherer":
                cmd = "cxm ctx"
            elif tool_name == "rag_engine" and "search" in args:
                query = args.replace("search", "").strip("' ")
                cmd = f"cxm ask --dry-run '{query}'" # Simplification
            else:
                return f"Error: Tool {tool_name} not found at {tool_file}"

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout
        except Exception as e:
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

        table.add_row("1", self.t('ctx'))
        table.add_row("2", self.t('rag_search'))
        table.add_row("3", self.t('rag_index'))
        table.add_row("4", self.t('sessions'))
        table.add_row("5", self.t('language'))
        table.add_row("6", self.t('prompt_builder'))
        table.add_row("0", self.t('exit'))
        
        return Panel(table, title=self.t('menu_title'), border_style="green")

    def display_context(self):
        with console.status("[bold green]" + ( "Gathering context..." if self.config.get('language') == 'en' else "Sammle Kontext..." )):
            # We try to use the direct module call if possible, or fallback to run_tool
            try:
                from cxm.tools.context_gatherer import gather_all
                data = gather_all()
            except ImportError:
                output = self.run_tool("context_gatherer")
                try:
                    data = json.loads(output)
                except:
                    console.print(output)
                    input("
" + self.t('back'))
                    return

            # Simplified view
            recent_edits = ', '.join([os.path.basename(f) for f in data['files']['recent_edits'][:3]])
            if self.config.get('language') == 'de':
                title = "Aktueller Kontext"
                content = f"Branch: {data['git']['branch']}
Änderungen: {len(data['git']['uncommitted_changes'].splitlines())} Dateien
Letzte Edits: {recent_edits}"
            else:
                title = "Current Context"
                content = f"Branch: {data['git']['branch']}
Changes: {len(data['git']['uncommitted_changes'].splitlines())} files
Recent Edits: {recent_edits}"
            
            console.print(Panel(content, title=title, border_style="blue"))
            
        input("
" + self.t('back'))

    def settings_language(self):
        console.clear()
        console.print(Panel("[bold cyan]Language Settings / Spracheinstellungen[/bold cyan]", border_style="cyan"))
        
        choices = ["en", "de"]
        current = self.config.get('language', 'en')
        
        new_lang = Prompt.ask(
            f"
Select language / Sprache wählen (current: [bold]{current}[/bold])",
            choices=choices,
            default="en" if current == "de" else "de"
        )
        
        self.config.set('language', new_lang)
        console.print(f"
[green]Language set to: {new_lang}[/green]")
        input("
" + self.t('back'))

    def rag_search(self):
        query = Prompt.ask("
[cyan]" + self.t('search_query') + "[/cyan]")
        if query:
            status_text = "[bold yellow]Searching long-term memory..." if self.config.get('language') == 'en' else "[bold yellow]Suche im Langzeitgedächtnis..."
            with console.status(status_text):
                output = self.run_tool("rag_engine", f"search '{query}'")
                console.print(Panel(output, title=f"{query}", border_style="yellow"))
        input("
" + self.t('back'))

    def manage_sessions(self):
        output = self.run_tool("session_manager", "list")
        title = "Active Sessions" if self.config.get('language') == 'en' else "Aktive Sessions"
        console.print(Panel(output, title=title, border_style="magenta"))
        
        choices = ["c", "s", ""]
        action = Prompt.ask("
[magenta]" + self.t('session_action') + "[/magenta]", choices=choices, default="")
        if action == "c":
            name = Prompt.ask("Session Name")
            prompt = Prompt.ask("Planning Prompt" if self.config.get('language') == 'en' else "Planungs-Prompt")
            self.run_tool("session_manager", f"create '{name}' '{prompt}'")
        elif action == "s":
            sid = Prompt.ask("Session ID")
            self.run_tool("session_manager", f"start {sid}")
        
    def main_loop(self):
        while True:
            console.clear()
            console.print(self.get_header())
            console.print(self.show_menu())
            
            choice = Prompt.ask("
[green]" + self.t('choose') + "[/green]", choices=["1", "2", "3", "4", "5", "6", "0"], default="1")
            
            if choice == "1":
                self.display_context()
            elif choice == "2":
                self.rag_search()
            elif choice == "3":
                path = Prompt.ask(self.t('path_prompt'))
                status_text = f"Indexing {path}..." if self.config.get('language') == 'en' else f"Indexiere {path}..."
                with console.status(status_text):
                    # Check if it's a directory
                    if os.path.isdir(path):
                        cmd_args = f"index-dir {path} --recursive"
                    else:
                        cmd_args = f"index {path}"
                    output = self.run_tool("rag_engine", cmd_args)
                    console.print(output)
                input("
" + self.t('back'))
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
        subtitle = "Building a high-context prompt for your app." if not is_de else "Wir bauen jetzt einen hoch-kontextuellen Prompt für deine App."
        console.print(Panel(f"[bold yellow]{title}[/bold yellow]
{subtitle}", border_style="yellow"))
        
        goal_q = "
[cyan]1. What is your goal? (e.g. 'Create a new route for user logins')[/cyan]" if not is_de else "
[cyan]1. Was ist dein Ziel? (z.B. 'Erstelle eine neue Route für User-Logins')[/cyan]"
        focus_q = "[cyan]2. Which file(s) are mainly affected? (e.g. 'app.py' or 'auth.js')[/cyan]" if not is_de else "[cyan]2. Welche Datei(en) betrifft das hauptsächlich? (z.B. 'app.py' oder 'auth.js')[/cyan]"
        
        goal = Prompt.ask(goal_q)
        focus_file = Prompt.ask(focus_q)
        
        status_text = "[bold green]Gathering context and building prompt..." if not is_de else "[bold green]Sammle Kontext und baue Prompt..."
        with console.status(status_text):
            try:
                from cxm.tools.context_gatherer import gather_all
                ctx_data = gather_all()
                recent_files = ctx_data.get('files', {}).get('recent_edits', [])[:3]
                git_status = ctx_data.get('git', {}).get('status', 'No changes' if not is_de else 'Keine Änderungen')
            except:
                recent_files = ["Error reading context" if not is_de else "Fehler beim Lesen des Kontexts"]
                git_status = "Unknown" if not is_de else "Unbekannt"

            # RAG Search for the focus file
            rag_info = ""
            if focus_file:
                 rag_result = self.run_tool("rag_engine", f"search '{focus_file}' --limit 2")
                 rag_title = "
### Relevant knowledge from RAG engine:
" if not is_de else "
### Relevantes Wissen aus der RAG-Engine:
"
                 rag_info = f"{rag_title}{rag_result}
"

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
        
        # Save to a file
        prompt_file = self.workspace / "current_task_prompt.txt"
        prompt_file.write_text(prompt_text)
            
        final_title = "Finished Prompt" if not is_de else "Fertiger Prompt"
        save_msg = f"
[bold green]✓[/bold green] Prompt also saved at: [cyan]{prompt_file}[/cyan]" if not is_de else f"
[bold green]✓[/bold green] Prompt wurde auch gespeichert unter: [cyan]{prompt_file}[/cyan]"
        copy_msg = "You can now copy this text and paste it into our Gemini chat window!" if not is_de else "Du kannst diesen Text jetzt kopieren und in unser Gemini-Chatfenster einfügen!"
        
        console.print(Panel(prompt_text, title=final_title, border_style="green"))
        console.print(save_msg)
        console.print(copy_msg)
        input("
" + self.t('back'))

def main():
    try:
        dash = CXMDashboard()
        dash.main_loop()
    except KeyboardInterrupt:
        print("
Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
