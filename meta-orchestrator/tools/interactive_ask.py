#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add src to pythonpath
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from cxm import Config, RAGEngine, PromptEnhancer
from cxm.tools.context_gatherer import gather_all
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
import pyperclip

def main():
    if len(sys.argv) < 2:
        print("Usage: python interactive_ask.py <prompt>")
        sys.exit(1)
        
    prompt = " ".join(sys.argv[1:])
    console = Console()
    
    config = Config()
    workspace = Path(__file__).resolve().parent.parent / "knowledge-base"
    
    rag = RAGEngine(workspace)
    enhancer = PromptEnhancer(rag)
    
    # 1. Analysis
    console.print("[dim]Analyzing intent and gathering context...[/dim]")
    analysis = enhancer.intent_analyzer.analyze(prompt)
    system_context = gather_all()
    
    console.print(f"\n[cyan]Detected Intent:[/cyan] {analysis['intent']} ({analysis['confidence']:.0%})")
    
    # 2. Gaps
    gaps = enhancer.refiner.analyze_gaps(
        prompt, analysis['intent'], system_context
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
        prompt, analysis['intent'], answers, system_context
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
            user_prompt=prompt,
            intent=analysis['intent'],
            contexts=selected,
            system_context=system_context,
            max_tokens=4000,
        )
        
        # Output
        output_dir = Path(__file__).resolve().parent.parent / "sessions" / "ask"
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
            console.print("\n[bold green]✓[/bold green] Prompt automatically copied to clipboard!")
        except Exception:
            console.print("\n[yellow]! Could not copy to clipboard automatically.[/yellow]")

        console.print(f"[dim]Saved at: [cyan]{output_file}[/cyan][/dim]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        sys.exit(0)