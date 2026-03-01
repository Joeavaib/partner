#!/usr/bin/env python3
"""
Context Gatherer
- Collects system context for CXM
"""
import json
import subprocess
import os
import sys
from pathlib import Path
from datetime import datetime

def run_command(cmd, timeout=5):
    """Run shell command safely"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except Exception:
        return None

def get_git_context():
    """Git repository context"""
    # Check if in git repo
    if run_command("git rev-parse --git-dir 2>/dev/null") is None:
        return None
        
    return {
        'repo': Path.cwd().name,
        'branch': run_command("git branch --show-current"),
        'status': run_command("git status --short"),
        'recent_commits': run_command("git log --oneline -n 5"),
        'diff_stats': run_command("git diff --stat"),
        'uncommitted_changes': run_command("git diff --name-only") or ""
    }

def get_file_context():
    """Recently edited files"""
    # Files modified in last hour
    recent = run_command(
        "find . -type f -mmin -60 -name '*.py' -o -name '*.js' -o -name '*.md' 2>/dev/null | head -10"
    )
    
    # Open files (via lsof) - might need adjustment based on OS/User permissions
    user = os.getenv('USER')
    open_files = run_command(
        rf"lsof -u {user} 2>/dev/null | grep -E '\.(py|js|md|txt)$' | awk '{{print $NF}}' | head -10"
    )
    
    return {
        'cwd': str(Path.cwd()),
        'recent_edits': recent.split('\n') if recent else [],
        'open_files': open_files.split('\n') if open_files else []
    }

def get_shell_context():
    """Shell history and environment"""
    history_file = Path.home() / ".bash_history"
    last_commands = []
    
    if history_file.exists():
        try:
            # Read last 20 lines
            with open(history_file, 'r', errors='ignore') as f:
                 lines = f.readlines()
                 last_commands = [cmd.strip() for cmd in lines[-20:]]
        except Exception:
            pass
            
    return {
        'last_commands': last_commands,
        'shell': os.getenv('SHELL', '/bin/bash'),
        'user': os.getenv('USER'),
        'home': str(Path.home())
    }

def get_system_context():
    """System resources"""
    load = run_command("uptime | awk -F'load average:' '{print $2}'")
    mem = run_command("free -h | awk 'NR==2{print $7}'")
    disk = run_command("df -h . | awk 'NR==2{print $4}'")
    
    return {
        'load_average': load.strip() if load else "unknown",
        'memory_available': mem,
        'disk_available': disk,
        'hostname': run_command("hostname")
    }

def gather_all():
    """Gather complete context"""
    context = {
        'timestamp': datetime.now().isoformat(),
        'git': get_git_context(),
        'files': get_file_context(),
        'shell': get_shell_context(),
        'system': get_system_context()
    }
    return context

def main():
    """CLI Interface"""
    context = gather_all()
    # Pretty print
    print(json.dumps(context, indent=2))

if __name__ == '__main__':
    main()
