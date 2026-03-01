# src/cxm/tools/context_gatherer.py

import subprocess
import os
from pathlib import Path
from typing import Dict, Optional


def run_cmd(cmd: str, timeout: int = 3) -> Optional[str]:
    """Run shell command, return stdout or None"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def gather_git_context(cwd: Path = None) -> Optional[Dict]:
    """Git repository context"""
    
    if cwd:
        os.chdir(cwd)
    
    if not run_cmd("git rev-parse --git-dir 2>/dev/null"):
        return None
    
    # We only want git status for the current path ('.')
    # and we limit the lines so it doesn't blow up the prompt.
    git_status = run_cmd("git status --short .")
    if git_status and len(git_status.splitlines()) > 20:
        lines = git_status.splitlines()
        git_status = "\n".join(lines[:20]) + f"\n... and {len(lines)-20} more files"

    return {
        'repo': Path.cwd().name,
        'branch': run_cmd("git branch --show-current"),
        'remote_url': run_cmd("git config --get remote.origin.url"),
        'status': git_status,
        'recent_commits': run_cmd("git log --oneline -5"),
        'diff_stats': run_cmd("git diff --stat ."),
    }


def gather_file_context() -> Dict:
    """Recently edited files and CWD"""
    
    recent = run_cmd(
        r"find . -type f -mmin -60 "
        r"\( -name '*.py' -o -name '*.js' -o -name '*.ts' -o -name '*.md' \) "
        r"2>/dev/null | head -10"
    )
    
    return {
        'cwd': str(Path.cwd()),
        'recent_edits': recent.split('\n') if recent else [],
    }


def gather_shell_context() -> Dict:
    """Shell history"""
    
    history_file = Path.home() / ".bash_history"
    commands = []
    
    if history_file.exists():
        try:
            with open(history_file, errors='ignore') as f:
                commands = [l.strip() for l in f.readlines()[-10:] if l.strip()]
        except Exception:
            pass
    
    return {
        'last_commands': commands,
        'user': os.getenv('USER', 'unknown'),
        'shell': os.getenv('SHELL', '/bin/bash'),
    }


def gather_system_context() -> Dict:
    """System resources"""
    
    return {
        'hostname': run_cmd("hostname"),
        'load': run_cmd("uptime | awk -F'load average:' '{print $2}'"),
        'memory_available': run_cmd("free -h 2>/dev/null | awk 'NR==2{print $7}'"),
        'disk_available': run_cmd("df -h . 2>/dev/null | awk 'NR==2{print $4}'"),
    }


import json
import glob
import re

def gather_multi_ai_context() -> Dict[str, Dict]:
    """
    Gather context from multiple AI sources (Gemini CLI, Claude, Ollama, etc.)
    """
    results = {}
    
    # 1. Gemini CLI (Existing)
    try:
        from ..config import Config
        config = Config()
        chats_dir = Path(config.get('gemini_chats_dir'))
        if chats_dir.exists():
            session_files = glob.glob(str(chats_dir / "session-*.json"))
            if session_files:
                latest_file = max(session_files, key=os.path.getmtime)
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                messages = data.get('messages', [])
                user_msgs = [m for m in messages if m.get('type') == 'user']
                recent = []
                for msg in user_msgs[-2:]:
                    content = msg.get('content', [])
                    if isinstance(content, list) and content:
                        text = content[0].get('text', '')
                        if text: recent.append(text[:200])
                
                results['gemini_cli'] = {
                    'session_id': data.get('sessionId'),
                    'recent_prompts': recent
                }
    except: pass

    # 2. Claude Desktop (Potential location)
    claude_path = Path.home() / ".config" / "Claude" / "logs"
    if claude_path.exists():
        results['claude_desktop'] = {'status': 'found', 'path': str(claude_path)}
        # Extraction logic for Claude's sqlite or logs could go here

    # 3. Ollama (Local API check)
    ollama_history = Path.home() / ".ollama" / "history" # (Placeholder for future Ollama log support)
    if ollama_history.exists():
        results['ollama'] = {'status': 'history_found'}

    return results

def gather_all(cwd: Path = None) -> Dict:
    """Gather complete context"""
    from datetime import datetime
    
    multi_ai = gather_multi_ai_context()
    
    return {
        'timestamp': datetime.now().isoformat(),
        'git': gather_git_context(cwd),
        'files': gather_file_context(),
        'shell': gather_shell_context(),
        'system': gather_system_context(),
        'ai_sessions': multi_ai,
    }

def main():
    """CLI Interface for debugging"""
    context = gather_all()
    print(json.dumps(context, indent=2))

if __name__ == '__main__':
    main()