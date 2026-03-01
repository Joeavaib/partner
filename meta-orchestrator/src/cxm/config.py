# src/cxm/config.py

from pathlib import Path
from typing import Any, Optional
import yaml
import os

class Config:
    """
    Configuration management
    
    Priority:
    1. CXM_CONFIG env var
    2. ./cxm.yaml (project-local)
    3. ~/.cxm/config.yaml (global)
    """
    
    DEFAULT_CONFIG = {
        'workspace': str(Path.home() / ".cxm" / "workspace"),
        'gemini_chats_dir': str(Path.home() / ".gemini" / "tmp" / "partner" / "chats"),
        'model': 'all-MiniLM-L6-v2',
        'index_extensions': [
            '.py', '.js', '.ts', '.md', '.txt',
            '.rs', '.go', '.java', '.c', '.cpp', '.h'
        ],
        'max_contexts': 5,
        'token_budget': 4000,
        'min_similarity': 0.0,
        'semantic_weight': 0.7,
        'keyword_weight': 0.3,
        'recency_boost': True,
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = self._find_config_path(config_path)
        self.data = self._load()
        
        # Ensure workspace
        Path(self.get('workspace')).mkdir(parents=True, exist_ok=True)
    
    def _find_config_path(self, explicit: Optional[Path]) -> Path:
        if explicit:
            return Path(explicit)
        
        env = os.getenv('CXM_CONFIG')
        if env:
            return Path(env)
        
        local = Path.cwd() / "cxm.yaml"
        if local.exists():
            return local
        
        return Path.home() / ".cxm" / "config.yaml"
    
    def _load(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path) as f:
                loaded = yaml.safe_load(f) or {}
            merged = self.DEFAULT_CONFIG.copy()
            merged.update(loaded)
            return merged
        else:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            data = self.DEFAULT_CONFIG.copy()
            self._save(data)
            return data
    
    def _save(self, data: dict):
        with open(self.config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any):
        self.data[key] = value
        self._save(self.data)
    
    def get_workspace(self) -> Path:
        return Path(self.get('workspace'))