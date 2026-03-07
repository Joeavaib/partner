# src/cxm/ml/context_evaluator.py

from typing import Dict, Any, List
from src.core.interfaces import BaseContextEvaluator
from src.ml.intent_analyzer import IntentAnalyzer
import re

class ContextEvaluator(BaseContextEvaluator):
    """
    Evaluates individual RAG hits against user intent and deduplicates context.
    Acting as a 'gatekeeper' to filter out noise, provide reasoning, and prevent redundancy.
    """
    
    def __init__(self):
        self.analyzer = IntentAnalyzer()
        
    def evaluate(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate context relevance based on intent and entities.
        Returns: { 'relevant': bool, 'reason': str, 'score': float }
        """
        query_analysis = self.analyzer.analyze(query)
        content = context.get('full_content', context.get('content_preview', '')).lower()
        file_name = context.get('name', '').lower()
        
        relevance_score = 0.0
        reasons = []
        
        # 1. Entity Match (High weight)
        matched_entities = [e for e in query_analysis['entities'] if e.lower() in content or e.lower() in file_name]
        if matched_entities:
            relevance_score += 0.5 * min(len(matched_entities) / 2, 1.0)
            reasons.append(f"Matches entities: {', '.join(matched_entities)}")
            
        # 2. Intent-specific check
        intent = query_analysis['intent']
        if intent == 'bug_fixing':
            if 'error' in content or 'exception' in content or 'test' in file_name:
                relevance_score += 0.3
                reasons.append("Relevant for bug fixing")
        elif intent == 'code_optimization':
            if any(kw in content for kw in ['loop', 'query', 'sort', 'map', 'async']):
                relevance_score += 0.2
                reasons.append("Contains optimization targets")
        elif intent == 'testing':
            if 'test' in file_name or 'assert' in content:
                relevance_score += 0.4
                reasons.append("Contains testing logic")

        # 3. Keyword Overlap
        matched_keywords = [kw for kw in query_analysis['keywords'] if kw in content]
        if matched_keywords:
            relevance_score += 0.2 * (len(matched_keywords) / max(len(query_analysis['keywords']), 1))
            
        # If no specific signals, but it came up high in RAG, give it a baseline chance
        if relevance_score == 0.0 and context.get('similarity', 0) > 0.6:
            relevance_score = 0.3
            reasons.append("High semantic similarity to query")
            
        # Final decision
        is_relevant = relevance_score >= 0.3 # Threshold for inclusion
        
        reason = " | ".join(reasons) if reasons else "No direct relevance signals"
        if not is_relevant:
            reason = f"Discarded (Score {relevance_score:.2f}): {reason}"
        else:
            reason = f"Accepted (Score {relevance_score:.2f}): {reason}"
            
        return {
            'relevant': is_relevant,
            'reason': reason,
            'score': relevance_score
        }

    def _calculate_overlap(self, text1: str, text2: str) -> float:
        """Calculate word-level Jaccard similarity to detect redundancy."""
        set1 = set(re.findall(r'\b\w+\b', text1.lower()))
        set2 = set(re.findall(r'\b\w+\b', text2.lower()))
        
        if not set1 or not set2:
            return 0.0
            
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union

    def evaluate_batch(self, query: str, candidates: List[Dict[str, Any]], max_overlap: float = 0.4) -> List[Dict[str, Any]]:
        """
        Evaluate a list of candidates, returning only relevant ones, 
        and actively filtering out redundant/highly similar contexts.
        """
        selected = []
        selected_texts = []
        
        for cand in candidates:
            # 1. Relevance Evaluation
            eval_res = self.evaluate(query, cand)
            
            if not eval_res['relevant']:
                continue
                
            # 2. Redundancy Evaluation (Deduplication)
            content = cand.get('full_content', cand.get('content_preview', ''))
            is_redundant = False
            
            for prev_text in selected_texts:
                overlap = self._calculate_overlap(content, prev_text)
                if overlap > max_overlap:
                    is_redundant = True
                    # Update reason for UI feedback
                    cand['_evaluation_reason'] = f"Discarded (Redundant): Overlaps {overlap:.0%} with higher-ranked hit."
                    break
                    
            if not is_redundant:
                cand['_evaluation_reason'] = eval_res['reason']
                selected.append(cand)
                selected_texts.append(content)
                
        return selected

