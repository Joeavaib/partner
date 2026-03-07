# src/cxm/ml/intent_analyzer.py

from typing import Dict, List, Any
import re
from src.core.interfaces import BaseIntentAnalyzer

class IntentAnalyzer(BaseIntentAnalyzer):
    """
    Detect user intent and required context types
    
    Rule-based for v0.1 (fast, no training needed)
    Can be replaced with trained model later
    """
    
    INTENT_PATTERNS = {
        'code_optimization': [
            r'\b(optimi[zs]e|faster|slow|performance|speed|efficient)\b',
            r'\b(improve|enhance)\b.*\b(performance|speed)\b',
            r'\b(too slow|takes too long|bottleneck)\b',
        ],
        'bug_fixing': [
            r'\b(bug|error|fix|issue|problem|broken|crash)\b',
            r'\b(debug|troubleshoot|diagnose)\b',
            r'(Error|Exception|Traceback|Failed)',
        ],
        'code_generation': [
            r'\b(generate|create|write|build|make|implement)\b.*\b(function|class|code|script|module)\b',
            r'\b(add|implement|create)\b.*\b(feature|endpoint|handler)\b',
        ],
        'refactoring': [
            r'\b(refactor|clean|reorgani[zs]e|restructure|simplify)\b',
            r'\b(improve|better)\b.*\b(code|structure|readability)\b',
        ],
        'documentation': [
            r'\b(document|comment|docstring|readme)\b',
            r'\bwrite\b.*\b(docs|documentation)\b',
        ],
        'explanation': [
            r'\b(explain|what does|how does|why does|understand)\b',
            r'\b(walk me through|break down)\b',
        ],
        'testing': [
            r'\b(test|unittest|pytest|spec)\b',
            r'\bwrite\b.*\btests?\b',
            r'\b(coverage|assert)\b',
        ],
        'research': [
            r'\b(how to|best practice|pattern|approach|compare)\b',
            r'\b(what is the best|recommend)\b',
            r'\b(find|search|look up)\b',
        ],
    }
    
    CONTEXT_NEEDS = {
        'code_optimization': ['similar_code', 'benchmarks', 'past_solutions'],
        'bug_fixing': ['error_logs', 'similar_code', 'past_solutions', 'tests'],
        'code_generation': ['similar_code', 'documentation', 'dependencies'],
        'refactoring': ['similar_code', 'tests', 'dependencies'],
        'documentation': ['documentation', 'similar_code'],
        'explanation': ['documentation', 'dependencies'],
        'testing': ['tests', 'similar_code', 'dependencies'],
        'research': ['documentation', 'similar_code', 'past_solutions'],
    }
    
    def analyze(self, prompt: str) -> Dict:
        """
        Analyze prompt for intent and context needs
        
        Returns:
            {
                'intent': str,
                'confidence': float,
                'context_needs': List[str],
                'entities': List[str],
                'keywords': List[str]
            }
        """
        
        prompt_lower = prompt.lower()
        
        # Score each intent
        scores = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = sum(1 for p in patterns if re.search(p, prompt_lower))
            if score > 0:
                scores[intent] = score
        
        # Best intent
        if scores:
            best = max(scores.items(), key=lambda x: x[1])
            intent = best[0]
            confidence = min(best[1] / 3.0, 1.0)
        else:
            intent = 'general'
            confidence = 0.3
        
        # Context needs
        context_needs = list(self.CONTEXT_NEEDS.get(intent, ['similar_code']))
        
        # Also add needs based on keyword detection
        extra_needs = self._detect_extra_needs(prompt_lower)
        for need in extra_needs:
            if need not in context_needs:
                context_needs.append(need)
        
        # Entities
        entities = self._extract_entities(prompt)
        
        # Keywords (most relevant terms)
        keywords = self._extract_keywords(prompt)
        
        return {
            'intent': intent,
            'confidence': confidence,
            'context_needs': context_needs,
            'entities': entities,
            'keywords': keywords,
        }
    
    def _detect_extra_needs(self, prompt: str) -> List[str]:
        """Detect additional context needs from keywords"""
        
        need_keywords = {
            'error_logs': ['error', 'exception', 'traceback', 'log', 'crash'],
            'tests': ['test', 'spec', 'assert', 'coverage'],
            'benchmarks': ['benchmark', 'perf', 'profile', 'timing'],
            'documentation': ['doc', 'readme', 'guide', 'tutorial'],
            'dependencies': ['import', 'require', 'depend', 'module'],
        }
        
        needs = []
        for need, keywords in need_keywords.items():
            if any(kw in prompt for kw in keywords):
                needs.append(need)
        
        return needs
    
    def _extract_entities(self, prompt: str) -> List[str]:
        """Extract file names, function names, etc."""
        
        entities = []
        
        # File patterns: word.ext
        files = re.findall(r'\b[\w/.-]+\.(?:py|js|ts|rs|go|md|txt|java|c|cpp|h)\b', prompt)
        entities.extend(files)
        
        # Function/method: word()
        funcs = re.findall(r'\b[a-zA-Z_]\w*\(\)', prompt)
        entities.extend(funcs)
        
        # Class-like: CamelCase words
        classes = re.findall(r'\b[A-Z][a-zA-Z0-9]+(?:[A-Z][a-z]+)+\b', prompt)
        entities.extend(classes)
        
        # Paths: /something/something or ./something
        paths = re.findall(r'[./~][\w/.-]+', prompt)
        entities.extend(paths)
        
        return list(set(entities))
    
    def _extract_keywords(self, prompt: str) -> List[str]:
        """Extract most relevant keywords"""
        
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'shall', 'can',
            'need', 'dare', 'ought', 'used', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
            'during', 'before', 'after', 'above', 'below', 'between',
            'and', 'but', 'or', 'nor', 'not', 'so', 'yet', 'both',
            'either', 'neither', 'each', 'every', 'all', 'any', 'few',
            'more', 'most', 'other', 'some', 'such', 'no', 'only',
            'own', 'same', 'than', 'too', 'very', 'just', 'because',
            'this', 'that', 'these', 'those', 'i', 'me', 'my', 'mine',
            'we', 'our', 'you', 'your', 'he', 'she', 'it', 'they',
            'them', 'their', 'what', 'which', 'who', 'whom', 'how',
            'when', 'where', 'why', 'if', 'then', 'else', 'about',
        }
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', prompt.lower())
        return [w for w in words if w not in stopwords][:10]