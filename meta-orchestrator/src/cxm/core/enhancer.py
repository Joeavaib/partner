# src/cxm/core/enhancer.py

from typing import Dict, List, Optional
from pathlib import Path

from .rag import RAGEngine
from .retriever import HybridRetriever
from .reranker import Reranker
from ..ml.intent_analyzer import IntentAnalyzer
from ..ml.prompt_assembler import PromptAssembler
from ..ml.prompt_refiner import PromptRefiner
from ..tools.context_gatherer import gather_all


class PromptEnhancer:
    """
    Main orchestrator pipeline:
    
    User Prompt
      → Intent Analysis
      → System Context Gathering
      → Prompt Refinement (Gap Analysis)
      → Hybrid Retrieval (semantic + keyword)
      → Neural Reranking
      → Prompt Assembly with Citations
      → Enhanced Prompt
    """
    
    def __init__(
        self,
        rag: RAGEngine,
        use_cross_encoder: bool = False
    ):
        self.rag = rag
        self.intent_analyzer = IntentAnalyzer()
        self.retriever = HybridRetriever(rag)
        self.reranker = Reranker(use_cross_encoder=use_cross_encoder)
        self.assembler = PromptAssembler()
        self.refiner = PromptRefiner(rag=rag)
    
    def enhance(
        self,
        prompt: str,
        max_contexts: int = 5,
        token_budget: int = 4000,
        include_system_context: bool = True,
        min_similarity: float = 0.0,
    ) -> Dict:
        """
        Full enhancement pipeline
        
        Args:
            prompt: User's original prompt
            max_contexts: Maximum contexts to include
            token_budget: Token limit for enhanced prompt
            include_system_context: Gather git/file/shell context
            min_similarity: Minimum relevance threshold
        
        Returns:
            {
                'original': str,
                'refined': str,
                'enhanced': str,
                'refinement': Dict,
                'analysis': Dict,
                'contexts': List[Dict],
                'citations': List[Dict],
                'system_context': Dict,
                'metadata': Dict
            }
        """
        
        # 1. Analyze intent
        analysis = self.intent_analyzer.analyze(prompt)
        
        # 2. Gather system context
        system_context = {}
        if include_system_context:
            system_context = gather_all()
            
        # 3. Prompt Refinement (Auto)
        refinement = self.refiner.auto_refine(
            prompt=prompt,
            intent=analysis['intent'],
            auto_context=system_context,
        )
        
        search_prompt = refinement['refined_prompt']
        
        # 4. Retrieve candidates (get more than needed)
        candidates = self.retriever.retrieve(
            query=search_prompt,
            context_needs=analysis['context_needs'],
            k=max_contexts * 3,
            min_similarity=min_similarity,
        )
        
        # 5. Rerank and select best within budget
        selected = self.reranker.rerank(
            query=search_prompt,
            candidates=candidates,
            top_k=max_contexts,
            token_budget=token_budget,
        )
        
        # 6. Assemble enhanced prompt
        result = self.assembler.assemble(
            user_prompt=prompt,
            intent=analysis['intent'],
            contexts=selected,
            system_context=system_context,
            max_tokens=token_budget,
        )
        
        # 7. Return complete result
        return {
            'original': prompt,
            'refined': search_prompt,
            'enhanced': result['enhanced_prompt'],
            'refinement': refinement,
            'analysis': analysis,
            'contexts': selected,
            'citations': result['citations'],
            'system_context': system_context,
            'metadata': {
                **result['metadata'],
                'intent': analysis['intent'],
                'confidence': analysis['confidence'],
                'context_needs': analysis['context_needs'],
                'keywords': analysis['keywords'],
                'entities': analysis['entities'],
            }
        }
    
    def enhance_for_agent(
        self,
        prompt: str,
        agent_type: str = 'general',
        **kwargs
    ) -> str:
        """
        Simplified: returns only the enhanced prompt string
        Useful for piping into other tools/agents
        """
        result = self.enhance(prompt, **kwargs)
        return result['enhanced']
    
    def index_conversation(
        self,
        messages: List[Dict],
        session_name: str = "conversation"
    ) -> int:
        """
        Index a conversation for future retrieval
        """
        
        text = "\n\n".join([
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in messages
        ])
        
        return self.rag.index_text(
            content=text,
            source=f"conversation:{session_name}",
            metadata={
                'type': 'conversation',
                'session': session_name,
                'num_messages': len(messages),
            }
        )

    def interactive_enhance(self, prompt: str):
        """
        Interaktive Version: Fragt User bei Lücken
        
        Returns:
            Generator der Fragen stellt und am Ende
            den fertigen Prompt liefert
        """
        
        # 1. Analyse
        analysis = self.intent_analyzer.analyze(prompt)
        system_context = gather_all()
        
        # 2. Lücken finden
        gaps = self.refiner.analyze_gaps(
            prompt=prompt,
            intent=analysis['intent'],
            auto_context=system_context,
        )
        
        # 3. Result objekt das wir füllen
        answers = {}
        
        # 4. Yield questions
        if gaps['missing_critical'] or gaps['missing_optional']:
            questions = self.refiner.generate_clarifying_questions(gaps)
            yield {
                'type': 'questions',
                'questions': questions,
                'completeness': gaps['completeness'],
                'inferred': gaps['inferred'],
                'gaps': gaps
            }
            # The user interacts and the wrapper passes the answers back.
        
        # We need a way to receive the answers in the real implementation,
        # but for the CLI loop, it is easier to implement the CLI layer directly.
        # This generator approach is a placeholder. The CLI will drive the questions.
        pass
