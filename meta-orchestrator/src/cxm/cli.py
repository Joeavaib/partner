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
import pyperclip

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
                console.print(f"[dim]Auto-detection: GitHub Repo found ({github_url})[/dim]")

    # 1. Workspace setup
    if github_url:
        try:
            repo_path = clone_github_repo(github_url)
            workspace = get_workspace(github_url=github_url)
            console.print(f"[dim]Using GitHub-Cache for Workspace.[/dim]")
            
            # Auto-Index if index is missing
            rag = RAGEngine(workspace)
            if rag.stats()['total_documents'] == 0:
                console.print(f"🔍 [yellow]First run for this repo. Indexing...[/yellow]")
                rag.index_directory(repo_path, recursive=True)
        except Exception as e:
            console.print(f"[bold red]Aborted: Could not load GitHub repo.[/bold red]")
            return
    else:
        workspace = get_workspace(project_name)
        if project_name:
            console.print(f"[dim]Using Project-Workspace: {project_name}[/dim]")
    
    rag = RAGEngine(workspace)
    enhancer = PromptEnhancer(rag)
    
    # 1. Analysis
    console.print("[dim]Analyzing intent and gathering context...[/dim]")
    analysis = enhancer.intent_analyzer.analyze(prompt_text)
    system_context = gather_all()
    
    console.print(f"\n[cyan]Detected Intent:[/cyan] {analysis['intent']} ({analysis['confidence']:.0%})")
    
    # 2. Gaps
    gaps = enhancer.refiner.analyze_gaps(
        prompt_text, analysis['intent'], system_context
    )
    
    # 3. Show what was automatically detected
    if gaps['inferred']:
        console.print("\n[green]Automatically detected (Context Inference):[/green]")
        for key, value in gaps['inferred'].items():
            console.print(f"  {key}: [dim]{value}[/dim]")
    
    # 4. Completeness
    console.print(f"\n[yellow]Prompt Completeness: {gaps['completeness']:.0%}[/yellow]")
    
    # 5. Ask questions
    answers = {}
    
    if gaps['missing_critical']:
        console.print("\n[bold red]Critical Gaps (Missing important info):[/bold red]\n")
        
        for key, question in gaps['missing_critical']:
            suggestions = enhancer.refiner._generate_suggestions(key, gaps)
            
            hint = ""
            if suggestions:
                hint = f" [dim](Suggestions: {', '.join(suggestions)})[/dim]"
            
            answer = Prompt.ask(f"  [bold]{question}[/bold]{hint}")
            
            if answer.strip():
                answers[key] = answer
    
    if gaps['missing_optional']:
        if Confirm.ask("\n[dim]Would you like to provide optional details?[/dim]", default=False):
            for key, question in gaps['missing_optional']:
                answer = Prompt.ask(f"  [bold]{question}[/bold]")
                if answer.strip():
                    answers[key] = answer
    
    # 6. Refine prompt
    refined_prompt = enhancer.refiner.refine_prompt(
        prompt_text, analysis['intent'], answers, system_context
    )
    
    console.print(Panel(
        refined_prompt,
        title="Refined Intermediate Prompt",
        border_style="cyan"
    ))
    
    # 7. Enhance
    if Confirm.ask("\nShould this prompt be enriched by the RAG engine?", default=True):
        console.print("[dim]Searching for matching code contexts in RAG index...[/dim]")
        
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
            title="✨ Final Enhanced Prompt",
            border_style="green"
        ))
        
        try:
            pyperclip.copy(result['enhanced_prompt'])
            clipboard_msg = "[bold green]✓[/bold green] Prompt automatically copied to clipboard!"
        except Exception:
            clipboard_msg = "[yellow]! Could not copy to clipboard automatically.[/yellow]"

        console.print(f"\n{clipboard_msg}")
        console.print(f"[dim]Saved at: [cyan]{output_file}[/cyan][/dim]")

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
                print(f"Auto-detection: GitHub Repo found ({github_url})")

    if github_url:
        repo_path = clone_github_repo(github_url)
        workspace = get_workspace(github_url=github_url)
        dir_to_index = repo_path
    else:
        workspace = get_workspace(project_name)
        dir_to_index = Path(args.dir).resolve()

    rag = RAGEngine(workspace)
    print(f"Indexing directory: {dir_to_index} {'(recursive)' if args.recursive else ''}")
    
    stats = rag.index_directory(dir_to_index, recursive=args.recursive)
    print(f"\n✓ Indexing completed.")
    print(f"  Newly indexed: {stats['indexed']}")
    print(f"  Skipped: {stats['skipped']}")
    if stats['errors'] > 0:
        print(f"  Errors: {stats['errors']}")
        
    print("\nCurrent Index Status:")
    index_stats = rag.stats()
    print(f"  Total documents: {index_stats['total_documents']}")
    print(f"  Vectors in index: {index_stats['index_vectors']}")

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