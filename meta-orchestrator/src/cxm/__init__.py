# src/cxm/__init__.py

"""CXM (ContextMachine) - AI Orchestrator with Intelligent Context Injection"""

__version__ = "0.1.0"

from .config import Config
from .core.rag import RAGEngine
from .core.enhancer import PromptEnhancer

__all__ = ['Config', 'RAGEngine', 'PromptEnhancer']