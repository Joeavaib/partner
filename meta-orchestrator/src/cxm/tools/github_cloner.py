import subprocess
import os
import hashlib
from pathlib import Path
from rich.console import Console

console = Console()

def clone_github_repo(repo_url: str) -> Path:
    """
    Clones a GitHub repository into ~/.cxm/cache/ and returns the path.
    If it already exists, it updates it.
    """
    # Create a unique directory name based on the URL
    url_hash = hashlib.md5(repo_url.encode()).hexdigest()[:10]
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    
    cache_dir = Path.home() / ".cxm" / "cache" / f"{repo_name}_{url_hash}"
    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    
    if cache_dir.exists():
        console.print(f"[dim]Repository bereits im Cache gefunden. Aktualisiere...[/dim]")
        try:
            subprocess.run(["git", "-C", str(cache_dir), "pull"], check=True, capture_output=True)
        except Exception as e:
            console.print(f"[yellow]Warnung: Konnte Repo nicht aktualisieren: {e}[/yellow]")
    else:
        console.print(f"📦 [cyan]Klone Repository:[/cyan] {repo_url}...")
        try:
            subprocess.run(["git", "clone", "--depth", "1", repo_url, str(cache_dir)], check=True, capture_output=True)
            console.print(f"✓ Repository erfolgreich in den Cache geladen.")
        except Exception as e:
            console.print(f"[bold red]Fehler beim Klonen:[/bold red] {e}")
            raise e
            
    return cache_dir
