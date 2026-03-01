# src/cxm/ml/prompt_refiner.py

"""
Prompt Refiner - Turns vague prompts into precise ones
through progressive questioning and context inference
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re


class PromptRefiner:
    """
    Wandelt vage Prompts in präzise um durch:
    
    1. Context Inference (automatisch Kontext erraten)
    2. Gap Detection (fehlende Info erkennen)
    3. Clarifying Questions (gezielt nachfragen)
    4. Progressive Refinement (iterativ verbessern)
    """
    
    # Was eine KI typischerweise braucht, pro Intent
    REQUIRED_CONTEXT = {
        'code_optimization': {
            'must_have': [
                ('target', 'Welche Funktion/Datei soll optimiert werden?'),
                ('current_performance', 'Wie langsam ist es aktuell?'),
                ('goal_performance', 'Was wäre akzeptable Performance?'),
            ],
            'nice_to_have': [
                ('constraints', 'Gibt es Einschränkungen? (Memory, CPU, Kompatibilität)'),
                ('tried_before', 'Was hast du schon probiert?'),
                ('measurement', 'Wie misst du Performance?'),
            ],
        },
        'bug_fixing': {
            'must_have': [
                ('error_message', 'Was ist die Fehlermeldung?'),
                ('reproduction', 'Wie reproduziert man den Fehler?'),
                ('expected', 'Was sollte stattdessen passieren?'),
            ],
            'nice_to_have': [
                ('when_started', 'Seit wann tritt der Fehler auf?'),
                ('what_changed', 'Was wurde zuletzt geändert?'),
                ('environment', 'Welche Umgebung? (OS, Python-Version, etc.)'),
            ],
        },
        'code_generation': {
            'must_have': [
                ('what', 'Was genau soll generiert werden?'),
                ('language', 'Welche Sprache/Framework?'),
                ('behavior', 'Wie soll es sich verhalten?'),
            ],
            'nice_to_have': [
                ('style', 'Code-Stil-Präferenzen?'),
                ('integration', 'Wo wird es eingebaut?'),
                ('tests', 'Sollen Tests mit generiert werden?'),
            ],
        },
        'general': {
            'must_have': [
                ('goal', 'Was genau willst du erreichen?'),
            ],
            'nice_to_have': [
                ('context', 'Was ist der Hintergrund?'),
                ('constraints', 'Gibt es Einschränkungen?'),
            ],
        },
    }
    
    def __init__(self, context_gatherer=None, rag=None):
        """
        Args:
            context_gatherer: Automatischer System-Kontext
            rag: RAG Engine für historischen Kontext
        """
        self.context_gatherer = context_gatherer
        self.rag = rag
    
    def analyze_gaps(
        self,
        prompt: str,
        intent: str,
        auto_context: Dict = None
    ) -> Dict:
        """
        Analysiert was im Prompt fehlt
        
        Returns:
            {
                'provided': {key: value},      # Was schon da ist
                'inferred': {key: value},      # Was automatisch erkannt wurde
                'missing_critical': [(key, question)],  # MUSS beantwortet werden
                'missing_optional': [(key, question)],  # Wäre hilfreich
                'completeness': float           # 0-1 wie vollständig
            }
        """
        
        requirements = self.REQUIRED_CONTEXT.get(intent, self.REQUIRED_CONTEXT['general'])
        
        provided = {}
        inferred = {}
        missing_critical = []
        missing_optional = []
        
        # 1. Check was im Prompt schon steht
        provided = self._extract_provided(prompt, intent)
        
        # 2. Was kann automatisch inferiert werden?
        if auto_context:
            inferred = self._infer_from_context(auto_context, intent)
        
        # 3. Was fehlt noch?
        all_known = {**provided, **inferred}
        
        for key, question in requirements.get('must_have', []):
            if key not in all_known:
                missing_critical.append((key, question))
        
        for key, question in requirements.get('nice_to_have', []):
            if key not in all_known:
                missing_optional.append((key, question))
        
        # Completeness score
        total_fields = len(requirements.get('must_have', [])) + len(requirements.get('nice_to_have', []))
        filled_fields = len(all_known)
        completeness = filled_fields / max(total_fields, 1)
        
        return {
            'provided': provided,
            'inferred': inferred,
            'missing_critical': missing_critical,
            'missing_optional': missing_optional,
            'completeness': completeness,
        }
    
    def _extract_provided(self, prompt: str, intent: str) -> Dict:
        """Extrahiere was der User schon gesagt hat"""
        
        provided = {}
        prompt_lower = prompt.lower()
        
        # Dateinamen
        files = re.findall(
            r'\b[\w/.-]+\.(?:py|js|ts|rs|go|md|java|c|cpp|h)\b',
            prompt
        )
        if files:
            provided['target'] = files[0]
        
        # Funktionsnamen
        funcs = re.findall(r'\b[a-zA-Z_]\w*\(\)', prompt)
        if funcs:
            provided['target'] = funcs[0]
        
        # Fehlermeldungen
        errors = re.findall(
            r'(Error|Exception|Traceback|Failed|TypeError|ValueError'
            r'|KeyError|AttributeError|ImportError|NameError).*',
            prompt
        )
        if errors:
            provided['error_message'] = errors[0]
        
        # Performance-Zahlen
        perf = re.findall(r'(\d+\.?\d*)\s*(ms|seconds?|s|minutes?|min)', prompt_lower)
        if perf:
            provided['current_performance'] = f"{perf[0][0]} {perf[0][1]}"
        
        # Sprache
        langs = re.findall(
            r'\b(python|javascript|typescript|rust|go|java|c\+\+|ruby)\b',
            prompt_lower
        )
        if langs:
            provided['language'] = langs[0]
        
        # "Ich habe schon X probiert"
        tried = re.findall(
            r'(?:tried|probiert|versucht|already)\s+(.+?)(?:\.|,|$)',
            prompt_lower
        )
        if tried:
            provided['tried_before'] = tried[0]
        
        return provided
    
    def _infer_from_context(self, context: Dict, intent: str) -> Dict:
        """Inferiere fehlende Info aus System-Kontext"""
        
        inferred = {}
        
        # Git context
        git = context.get('git')
        if git:
            if git.get('status'):
                # Welche Dateien geändert?
                changed_files = [
                    line.split()[-1]
                    for line in (git['status'] or '').split('\n')
                    if line.strip()
                ]
                if changed_files:
                    inferred['target'] = changed_files[0]
                    inferred['what_changed'] = ', '.join(changed_files)
            
            if git.get('branch'):
                inferred['branch'] = git['branch']
        
        # File context
        files = context.get('files', {})
        if files.get('cwd'):
            inferred['working_directory'] = files['cwd']
        
        if files.get('recent_edits'):
            edits = files['recent_edits']
            if edits and 'target' not in inferred:
                # Zuletzt bearbeitete Datei = wahrscheinlich das Ziel
                inferred['target'] = edits[0]
        
        # Sprache aus Datei-Endung inferieren
        target = inferred.get('target', '')
        if target.endswith('.py'):
            inferred['language'] = 'python'
        elif target.endswith('.js') or target.endswith('.ts'):
            inferred['language'] = 'javascript/typescript'
        elif target.endswith('.rs'):
            inferred['language'] = 'rust'
        
        return inferred
    
    def generate_clarifying_questions(
        self,
        gaps: Dict,
        max_questions: int = 3
    ) -> List[Dict]:
        """
        Generiere die wichtigsten Fragen
        
        Returns:
            List of {
                'key': str,
                'question': str,
                'priority': 'critical' | 'optional',
                'suggestions': List[str]  # Mögliche Antworten
            }
        """
        
        questions = []
        
        # Critical first
        for key, question in gaps['missing_critical'][:max_questions]:
            q = {
                'key': key,
                'question': question,
                'priority': 'critical',
                'suggestions': self._generate_suggestions(key, gaps),
            }
            questions.append(q)
        
        # Then optional (if space)
        remaining = max_questions - len(questions)
        for key, question in gaps['missing_optional'][:remaining]:
            q = {
                'key': key,
                'question': question,
                'priority': 'optional',
                'suggestions': self._generate_suggestions(key, gaps),
            }
            questions.append(q)
        
        return questions
    
    def _generate_suggestions(self, key: str, gaps: Dict) -> List[str]:
        """Generiere Vorschläge für Antworten basierend auf Kontext"""
        
        suggestions = []
        inferred = gaps.get('inferred', {})
        
        if key == 'target':
            # Schlage Dateien aus Kontext vor
            if 'target' in inferred:
                suggestions.append(inferred['target'])
        
        elif key == 'language':
            if 'language' in inferred:
                suggestions.append(inferred['language'])
        
        elif key == 'current_performance':
            suggestions.extend(['< 1 Sekunde', '1-5 Sekunden', '> 10 Sekunden'])
        
        elif key == 'goal_performance':
            suggestions.extend(['So schnell wie möglich', '< 100ms', '< 1 Sekunde'])
        
        elif key == 'error_message':
            suggestions.append('(Paste die Fehlermeldung)')
        
        return suggestions
    
    def refine_prompt(
        self,
        original_prompt: str,
        intent: str,
        answers: Dict,
        auto_context: Dict = None
    ) -> str:
        """
        Baue verfeinerten Prompt aus Original + Antworten + Kontext
        
        Args:
            original_prompt: Originaler vager Prompt
            intent: Erkannter Intent
            answers: Antworten auf Clarifying Questions {key: answer}
            auto_context: Automatisch gesammelter Kontext
        
        Returns:
            Verfeinerter Prompt
        """
        
        parts = [original_prompt, ""]
        
        # Kontext-Abschnitt
        context_parts = []
        
        # Automatischer Kontext
        if auto_context:
            inferred = self._infer_from_context(auto_context, intent)
            for key, value in inferred.items():
                if key not in answers and value and str(value).strip() not in ["./", "n", "none", "nein", "keine", "."]:  
                    context_parts.append(f"- {key}: {value}")
        
        # User-Antworten
        for key, answer in answers.items():
            if answer and answer.strip() and answer.lower() not in ["n", "none", "nein", "keine"]:
                context_parts.append(f"- {key}: {answer}")
        
        if context_parts:
            parts.append("Additional context:")
            parts.extend(context_parts)
        
        return "\n".join(parts)
    
    def auto_refine(
        self,
        prompt: str,
        intent: str,
        auto_context: Dict = None
    ) -> Dict:
        """
        Automatische Verfeinerung OHNE User-Interaktion
        
        Nutzt nur automatisch verfügbaren Kontext
        
        Returns:
            {
                'refined_prompt': str,
                'added_context': Dict,
                'still_missing': List,
                'completeness': float
            }
        """
        
        gaps = self.analyze_gaps(prompt, intent, auto_context)
        
        refined = self.refine_prompt(
            original_prompt=prompt,
            intent=intent,
            answers={},  # Keine manuellen Antworten
            auto_context=auto_context,
        )
        
        return {
            'refined_prompt': refined,
            'added_context': gaps['inferred'],
            'still_missing': gaps['missing_critical'],
            'completeness': gaps['completeness'],
        }