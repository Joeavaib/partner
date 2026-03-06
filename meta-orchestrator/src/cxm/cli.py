import sys
import argparse
import os
import hashlib
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
import pyperclip

# Ensure we can find the modules if we're running locally without installation
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cxm import Config, RAGEngine, PromptEnhancer
from cxm.tools.context_gatherer import gather_all
from cxm.tools.github_cloner import clone_github_repo
from cxm.utils.logger import logger
from cxm.utils.paths import format_path

def get_workspace(project_name: str = None, github_url: str = None) -> Path:
    """Find the central knowledge-base workspace."""
    if github_url:
        url_hash = hashlib.md5(github_url.encode()).hexdigest()[:10]
        repo_name = github_url.split('/')[-1].replace('.git', '')
        kb_path = Path.home() / ".cxm" / "cache" / f"{repo_name}_{url_hash}" / "knowledge-base"
        kb_path.mkdir(parents=True, exist_ok=True)
        return kb_path

    if project_name:
        kb_path = Path.home() / ".cxm" / project_name / "knowledge-base"
        kb_path.mkdir(parents=True, exist_ok=True)
        return kb_path

    local_kb = Path.cwd() / "knowledge-base"
    if local_kb.exists() or Path.cwd().name == "meta-orchestrator":
        kb_path = Path.cwd() / "knowledge-base"
        kb_path.mkdir(parents=True, exist_ok=True)
        return kb_path
        
    config = Config()
    return config.get_workspace()

def handle_ask(args):
    prompt_text = " ".join(args.prompt)
    console = Console()
    
    github_url = args.github
    project_name = args.project
    
    if not github_url and not project_name:
        from cxm.tools.context_gatherer import gather_git_context
        git_ctx = gather_git_context()
        if git_ctx and git_ctx.get('remote_url'):
            remote = git_ctx['remote_url']
            if "github.com" in remote:
                github_url = remote
                console.print(f"[dim]Auto-detection: GitHub Repo found ({github_url})[/dim]")

    workspace = get_workspace(project_name, github_url)
    
    if github_url:
        try:
            repo_path = clone_github_repo(github_url)
            console.print(f"[dim]Using GitHub-Cache for Workspace.[/dim]")
            rag = RAGEngine(workspace)
            if rag.stats()['total_documents'] == 0:
                console.print(f"🔍 [yellow]First run for this repo. Indexing...[/yellow]")
                rag.index_directory(repo_path, recursive=True)
        except Exception as e:
            console.print(f"[bold red]Aborted: Could not load GitHub repo: {e}[/bold red]")
            return
    
    rag = RAGEngine(workspace)
    
    # Auto-indexing for local project if not skipped
    if not github_url and not project_name and not getattr(args, 'no_index', False):
        console.print("[dim]Checking for code changes (Incremental Indexing)...[/dim]")
        # Index current directory. RAG handles change detection via MD5 automatically.
        stats = rag.index_directory(Path.cwd(), recursive=True)
        if stats['indexed'] > 0:
            console.print(f"[dim]Updated index: {stats['indexed']} files changed.[/dim]")

    enhancer = PromptEnhancer(rag)
    
    console.print("[dim]Analyzing intent and gathering context...[/dim]")
    analysis = enhancer.intent_analyzer.analyze(prompt_text)
    system_context = gather_all()
    
    console.print(f"\n[cyan]Detected Intent:[/cyan] {analysis['intent']} ({analysis['confidence']:.0%})")
    
    gaps = enhancer.refiner.analyze_gaps(prompt_text, analysis['intent'], system_context)
    
    if gaps['inferred']:
        console.print("\n[green]Automatically detected (Context Inference):[/green]")
        for key, value in gaps['inferred'].items():
            console.print(f"  {key}: [dim]{value}[/dim]")
    
    console.print(f"\n[yellow]Prompt Completeness: {gaps['completeness']:.0%}[/yellow]")
    
    answers = {}
    if gaps['missing_critical']:
        console.print("\n[bold red]Critical Gaps (Missing important info):[/bold red]\n")
        for key, question in gaps['missing_critical']:
            suggestions = enhancer.refiner._generate_suggestions(key, gaps)
            hint = f" [dim](Suggestions: {', '.join(suggestions)})[/dim]" if suggestions else ""
            answer = Prompt.ask(f"  [bold]{question}[/bold]{hint}")
            if answer.strip():
                answers[key] = answer
    
    if gaps['missing_optional']:
        if Confirm.ask("\n[dim]Would you like to provide optional details?[/dim]", default=False):
            for key, question in gaps['missing_optional']:
                answer = Prompt.ask(f"  [bold]{question}[/bold]")
                if answer.strip():
                    answers[key] = answer
    
    refined_prompt = enhancer.refiner.refine_prompt(prompt_text, analysis['intent'], answers, system_context)
    console.print(Panel(refined_prompt, title="Refined Intermediate Prompt", border_style="cyan"))
    
    if Confirm.ask("\nShould this prompt be enriched by the RAG engine?", default=True):
        console.print("[dim]Searching for matching code contexts in RAG index...[/dim]")
        candidates = enhancer.retriever.retrieve(query=refined_prompt, context_needs=analysis['context_needs'], k=15)
        selected = enhancer.reranker.rerank(query=refined_prompt, candidates=candidates, top_k=5, token_budget=4000)
        result = enhancer.assembler.assemble(user_prompt=prompt_text, intent=analysis['intent'], contexts=selected, system_context=system_context, max_tokens=4000)
        
        output_dir = Path.home() / ".cxm" / "sessions" / "ask"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "latest_prompt.txt"
        output_file.write_text(result['enhanced_prompt'])
        
        console.print(Panel(result['enhanced_prompt'], title="✨ Final Enhanced Prompt", border_style="green"))
        
        try:
            pyperclip.copy(result['enhanced_prompt'])
            clipboard_msg = "[bold green]✓[/bold green] Prompt automatically copied to clipboard!"
        except Exception:
            clipboard_msg = "[yellow]! Could not copy to clipboard automatically.[/yellow]"

        console.print(f"\n{clipboard_msg}")
        console.print(f"[dim]Saved at: [cyan]{format_path(str(output_file))}[/cyan][/dim]")

def handle_index(args):
    github_url = args.github
    project_name = args.project
    workspace = get_workspace(project_name, github_url)
    
    if github_url:
        repo_path = clone_github_repo(github_url)
        dir_to_index = repo_path
    else:
        dir_to_index = Path(args.dir).resolve()

    rag = RAGEngine(workspace)
    print(f"Indexing directory: {format_path(str(dir_to_index))} {'(recursive)' if args.recursive else ''}")
    stats = rag.index_directory(dir_to_index, recursive=args.recursive)
    print(f"\n✓ Indexing completed. Newly indexed: {stats['indexed']}, Skipped: {stats['skipped']}, Errors: {stats['errors']}")
    
    index_stats = rag.stats()
    print(f"Current Index Status: {index_stats['total_documents']} documents, {index_stats['index_vectors']} vectors.")

def handle_search(args):
    workspace = get_workspace(args.project, args.github)
    rag = RAGEngine(workspace)
    results = rag.search(args.query, k=args.limit)
    
    console = Console()
    if not results:
        console.print("[yellow]No matching contexts found.[/yellow]")
        return

    for i, res in enumerate(results):
        console.print(f"\n[bold cyan][{i+1}] {res['name']}[/bold cyan] (Sim: {res['similarity']:.2f})")
        console.print(f"[dim]{format_path(res['path'])}[/dim]")
        content = res.get('full_content', res.get('content_preview', ''))
        console.print(Panel(content[:1000] + ("..." if len(content) > 1000 else ""), border_style="dim"))

def handle_ctx(args):
    from cxm.tools.context_gatherer import main
    main()


def handle_harvest(args):
    # Non-interactive harvesting for agentic workflows
    workspace = get_workspace(args.project, args.github)
    rag = RAGEngine(workspace)
    
    # Optional: incremental index
    if not args.no_index and not args.github and not args.project:
        rag.index_directory(Path.cwd(), recursive=True)
        
    enhancer = PromptEnhancer(rag)
    
    # Combine keywords
    query = " ".join(args.keywords)
    intent_override = args.intent
    
    analysis = enhancer.intent_analyzer.analyze(query)
    intent = intent_override if intent_override else analysis['intent']
    
    # Silent retrieval (no gap checking or prompting)
    candidates = enhancer.retriever.retrieve(query=query, context_needs=analysis['context_needs'], k=10)
    selected = enhancer.reranker.rerank(query=query, candidates=candidates, top_k=args.limit)
    
    # Build clean output for the orchestrator
    print("<!-- CXM HARVEST START -->")
    print(f"<harvest_intent>{intent}</harvest_intent>")
    if not selected:
        print("<harvest_warning>No matching context found.</harvest_warning>")
    
    for doc in selected:
        doc_path = format_path(doc['path'])
            
        print(f"\n<file_context path=\"{doc_path}\">")
        content = doc.get('full_content', doc.get('content_preview', ''))
        print(content)
        print("</file_context>")
    print("<!-- CXM HARVEST END -->")


def main():
    parser = argparse.ArgumentParser(description="CXM (ContextMachine) CLI - Your AI Partner Orchestrator")
    parser.add_argument("-p", "--project", type=str, help="Specify project name")
    parser.add_argument("-g", "--github", type=str, help="GitHub repository URL")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # ask
    ask_parser = subparsers.add_parser("ask", help="Create an enhanced RAG prompt")
    ask_parser.add_argument("prompt", nargs="+", help="The initial prompt")
    ask_parser.add_argument("--no-index", action="store_true", help="Skip automatic incremental indexing")
    
    # index
    index_parser = subparsers.add_parser("index", help="Index a directory")
    index_parser.add_argument("dir", type=str, default=".", nargs="?", help="Directory to index")
    index_parser.add_argument("--recursive", action="store_true", default=True)
    index_parser.add_argument("-g", "--github", type=str)
    
    # search
    search_parser = subparsers.add_parser("search", help="Search the knowledge base")
    search_parser.add_argument("query", type=str, help="Search query")
    search_parser.add_argument("--limit", type=int, default=5)
    

    # harvest
    harvest_parser = subparsers.add_parser("harvest", help="Non-interactive context harvesting for agents")
    harvest_parser.add_argument("keywords", nargs="+", help="Keywords or target files")
    harvest_parser.add_argument("--intent", type=str, help="Override intent (e.g. Feature, Bugfix)")
    harvest_parser.add_argument("--format", type=str, default="xml", help="Output format")
    harvest_parser.add_argument("--limit", type=int, default=5, help="Number of files to retrieve")
    harvest_parser.add_argument("--no-index", action="store_true", help="Skip incremental indexing")

    # ctx
    subparsers.add_parser("ctx", help="Print current system context")
    
    args = parser.parse_args()
    
    if args.command == "ask":
        handle_ask(args)
    elif args.command == "index":
        handle_index(args)
    elif args.command == "search":
        handle_search(args)

    elif args.command == "harvest":
        handle_harvest(args)
    elif args.command == "ctx":
        handle_ctx(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
