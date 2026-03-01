import sys
import argparse
import os
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

# Ensure we can find the modules if we're running locally without installation
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cxm import Config, RAGEngine, PromptEnhancer
from cxm.tools.context_gatherer import gather_all
from cxm.tools.github_cloner import clone_github_repo

def get_workspace(project_name: str = None, github_url: str = None) -> Path:
    """Find the central knowledge-base workspace."""
    if github_url:
        # For GitHub repos, we use a specific workspace path in the cache
        url_hash = hashlib.md5(github_url.encode()).hexdigest()[:10]
        repo_name = github_url.split('/')[-1].replace('.git', '')
        kb_path = Path.home() / ".cxm" / "cache" / f"{repo_name}_{url_hash}" / "knowledge-base"
        kb_path.mkdir(parents=True, exist_ok=True)
        return kb_path

    if project_name:
        # User explicitly named a project, store it in ~/.cxm/<name>
        kb_path = Path.home() / ".cxm" / project_name / "knowledge-base"
        kb_path.mkdir(parents=True, exist_ok=True)
        return kb_path

    # Default logic: Try local first, then home
    local_kb = Path.cwd() / "knowledge-base"
    if local_kb.exists() or Path.cwd().name == "meta-orchestrator":
        kb_path = Path.cwd() / "knowledge-base"
        kb_path.mkdir(parents=True, exist_ok=True)
        return kb_path
        
    # Fallback to user home directory
    config = Config()
    return config.get_workspace()

import hashlib

def handle_ask(args):
    prompt_text = " ".join(args.prompt)
    console = Console()
    
    github_url = args.github
    project_name = args.project
    
    # 0. Auto-detect GitHub Repo if no project/github is specified
    if not github_url and not project_name:
        from cxm.tools.context_gatherer import gather_git_context
        git_ctx = gather_git_context()
        if git_ctx and git_ctx.get('remote_url'):
            remote = git_ctx['remote_url']
            if "github.com" in remote:
                github_url = remote
                console.print(f"[dim]Auto-Erkennung: GitHub Repo gefunden ({github_url})[/dim]")

    # 1. Workspace setup
    if github_url:
        try:
            repo_path = clone_github_repo(github_url)
            workspace = get_workspace(github_url=github_url)
            console.print(f"[dim]Nutze GitHub-Cache für Workspace.[/dim]")
            
            # Auto-Index if index is missing
            rag = RAGEngine(workspace)
            if rag.stats()['total_documents'] == 0:
                console.print(f"🔍 [yellow]Erster Lauf für dieses Repo. Indexiere...[/yellow]")
                rag.index_directory(repo_path, recursive=True)
        except Exception as e:
            console.print(f"[bold red]Abbruch: GitHub Repo konnte nicht geladen werden.[/bold red]")
            return
    else:
        workspace = get_workspace(project_name)
        if project_name:
            console.print(f"[dim]Nutze Projekt-Workspace: {project_name}[/dim]")
    
    rag = RAGEngine(workspace)
    enhancer = PromptEnhancer(rag)
    
    # 1. Analyse
    console.print("[dim]Analysiere Intent und sammle Kontext...[/dim]")
    analysis = enhancer.intent_analyzer.analyze(prompt_text)
    system_context = gather_all()
    
    console.print(f"\n[cyan]Erkannter Intent:[/cyan] {analysis['intent']} ({analysis['confidence']:.0%})")
    
    # 2. Lücken
    gaps = enhancer.refiner.analyze_gaps(
        prompt_text, analysis['intent'], system_context
    )
    
    # 3. Zeige was automatisch erkannt wurde
    if gaps['inferred']:
        console.print("\n[green]Automatisch erkannt (Context Inference):[/green]")
        for key, value in gaps['inferred'].items():
            console.print(f"  {key}: [dim]{value}[/dim]")
    
    # 4. Completeness
    console.print(f"\n[yellow]Prompt-Vollständigkeit: {gaps['completeness']:.0%}[/yellow]")
    
    # 5. Fragen stellen
    answers = {}
    
    if gaps['missing_critical']:
        console.print("\n[bold red]Fehlende wichtige Infos (Critical Gaps):[/bold red]\n")
        
        for key, question in gaps['missing_critical']:
            suggestions = enhancer.refiner._generate_suggestions(key, gaps)
            
            hint = ""
            if suggestions:
                hint = f" [dim](Vorschläge: {', '.join(suggestions)})[/dim]"
            
            answer = Prompt.ask(f"  [bold]{question}[/bold]{hint}")
            
            if answer.strip():
                answers[key] = answer
    
    if gaps['missing_optional']:
        if Confirm.ask("\n[dim]Möchtest du noch optionale Details angeben?[/dim]", default=False):
            for key, question in gaps['missing_optional']:
                answer = Prompt.ask(f"  [bold]{question}[/bold]")
                if answer.strip():
                    answers[key] = answer
    
    # 6. Prompt verfeinern
    refined_prompt = enhancer.refiner.refine_prompt(
        prompt_text, analysis['intent'], answers, system_context
    )
    
    console.print(Panel(
        refined_prompt,
        title="Verfeinerter Zwischen-Prompt",
        border_style="cyan"
    ))
    
    # 7. Enhance
    if Confirm.ask("\nSoll dieser Prompt nun in der RAG-Engine angereichert werden?", default=True):
        console.print("[dim]Suche passende Code-Kontexte im RAG-Index...[/dim]")
        
        # Search parameters
        search_prompt = refined_prompt
        candidates = enhancer.retriever.retrieve(
            query=search_prompt,
            context_needs=analysis['context_needs'],
            k=15,
        )
        
        selected = enhancer.reranker.rerank(
            query=search_prompt,
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
        
        # Output
        output_dir = Path.cwd() / "sessions" / "ask"
        
        # fallback if run from meta-orchestrator root
        if Path.cwd().name == "meta-orchestrator":
             output_dir = Path.cwd() / "sessions" / "ask"
        else:
             output_dir = Path.home() / ".cxm" / "sessions" / "ask"
             
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "latest_prompt.txt"
        output_file.write_text(result['enhanced_prompt'])
        
        console.print(Panel(
            result['enhanced_prompt'],
            title="✨ Fertiger Enhanced Prompt",
            border_style="green"
        ))
        
        console.print(f"\n[bold green]✓[/bold green] Gespeichert in: [cyan]{output_file}[/cyan]")
        console.print("Du kannst diesen Prompt nun kopieren und an mich übergeben.")

def handle_index(args):
    github_url = args.github
    project_name = args.project
    
    # Auto-detect GitHub if nothing specified
    if not github_url and not project_name:
        from cxm.tools.context_gatherer import gather_git_context
        git_ctx = gather_git_context()
        if git_ctx and git_ctx.get('remote_url'):
            remote = git_ctx['remote_url']
            if "github.com" in remote:
                github_url = remote
                print(f"Auto-Erkennung: GitHub Repo gefunden ({github_url})")

    if github_url:
        repo_path = clone_github_repo(github_url)
        workspace = get_workspace(github_url=github_url)
        dir_to_index = repo_path
    else:
        workspace = get_workspace(project_name)
        dir_to_index = Path(args.dir).resolve()

    rag = RAGEngine(workspace)
    print(f"Indexiere Verzeichnis: {dir_to_index} {'(rekursiv)' if args.recursive else ''}")
    
    stats = rag.index_directory(dir_to_index, recursive=args.recursive)
    print(f"\n✓ Indexierung abgeschlossen.")
    print(f"  Neu indiziert: {stats['indexed']}")
    print(f"  Übersprungen: {stats['skipped']}")
    if stats['errors'] > 0:
        print(f"  Fehler: {stats['errors']}")
        
    print("\nAktueller Index-Status:")
    index_stats = rag.stats()
    print(f"  Dokumente gesamt: {index_stats['total_documents']}")
    print(f"  Vektoren im Index: {index_stats['index_vectors']}")

def handle_ctx(args):
    from cxm.tools.context_gatherer import main
    main()

def main():
    parser = argparse.ArgumentParser(description="CXM (ContextMachine) CLI - Your AI Partner Orchestrator")
    parser.add_argument("-p", "--project", type=str, help="Specify project name to use a separate knowledge base")
    parser.add_argument("-g", "--github", type=str, help="Link a GitHub repository (URL) to clone and index it automatically")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # ask command
    ask_parser = subparsers.add_parser("ask", help="Interactively create an enhanced RAG prompt")
    ask_parser.add_argument("prompt", nargs="+", help="The initial vague prompt")
    
    # index command
    index_parser = subparsers.add_parser("index", help="Index a directory for the RAG engine")
    index_parser.add_argument("dir", type=str, default=".", nargs="?", help="Directory to index (default: current)")
    index_parser.add_argument("--recursive", action="store_true", default=True, help="Index recursively")
    index_parser.add_argument("-g", "--github", type=str, help="Link a GitHub repository (URL) to index it automatically")
    
    # ctx command
    ctx_parser = subparsers.add_parser("ctx", help="Print current system context")
    
    args = parser.parse_args()
    
    if args.command == "ask":
        handle_ask(args)
    elif args.command == "index":
        handle_index(args)
    elif args.command == "ctx":
        handle_ctx(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()