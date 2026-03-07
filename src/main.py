import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.context_store import ContextStore
from src.core.diagnostics import DiagnosticEngine
from src.core.factory import Factory
from src.core.audit import MultiAgentAudit
from src.core.pattern_optimizer import PatternOptimizer
from src.core.patcher import FilePatcher

def simulate_llm_generation(prompt: str) -> str:
    """Mock function simulating an autonomous LLM response with file patches."""
    print("\n⏳ [LLM] Autonomously generating code based on vibe...")
    return """
<file_patch path="src/utils/math_utils.py">
```python
from decimal import Decimal, getcontext

def calculate_ratio(total_volume: Decimal, ratio_part: Decimal) -> Decimal:
    getcontext().prec = 10
    # Safe calculation using Decimal (Enforced by Blueprint)
    result = total_volume / ratio_part
    return result
```
</file_patch>

<file_patch path="src/experimental/dangerous_math.py">
```python
# This should be blocked by guardrails!
def quick_ratio(v, p): return v/p
```
</file_patch>
"""

def run_orchestration_loop(user_intent: str, target_model: str, project_name: str, pattern_name: str = None):
    """
    Main Orchestration Loop for Autonomous Vibe-to-Code Generation.
    """
    print("="*60)
    print(f"⚙️  RUNNING AUTONOMOUS FORGE: {target_model} | PROJECT: {project_name}")
    print("="*60)

    # 1. Initialize Components
    store = ContextStore()
    diagnostics = DiagnosticEngine()
    factory = Factory()
    audit_engine = MultiAgentAudit()
    optimizer = PatternOptimizer()
    patcher = FilePatcher()

    # --- Setup professional context data ---
    store.set_project_var(project_name, "STABILITY_THRESHOLD", "0.95")
    store.set_project_var(project_name, "PRIMARY_RATIO", "1:500")
    store.set_project_var(project_name, "MAX_TEMP_CELSIUS", "32.0")

    # 2. Identify & Probe
    print("\n[Step 1] Running Diagnostics...")
    preferred_format = diagnostics.run(target_model)
    
    # 3. Fetch Data
    print("\n[Step 2] Fetching Context...")
    context_vars = store.get_project_vars(project_name)

    # 4. Synthesize Secure Prompt & Auto-Route Vibe
    print("\n[Step 3] Routing Vibe & Compiling Secure Prompt...")
    final_prompt = factory.assemble_secure(
        user_query=user_intent,
        pattern_name=pattern_name,
        vault_vars=context_vars,
        engine_name=target_model
    )
    
    print("\n🛡️  COMPILED AUTONOMOUS PROMPT 🛡️")
    print("-" * 50)
    print(final_prompt)
    print("-" * 50)

    # 5. Generate Code (Simulated)
    generated_code = simulate_llm_generation(final_prompt)
    print(generated_code)

    # 6. Multi-Agent Audit
    audit_passed = audit_engine.review_code(generated_code, ["Must use safe logic"])

    # 7. Apply Patches (If Audit passed)
    if audit_passed:
        print("\n[Step 4] Applying Code Patches (with Guardrails)...")
        patcher.parse_and_apply(generated_code)
    else:
        print("\n[Step 4] ❌ Patching aborted due to failed Audit.")

    # 8. Pattern Optimization
    optimizer.optimize_from_success(user_intent, generated_code, audit_passed)

if __name__ == "__main__":
    # Vibecoding Test: Notice we do NOT pass a pattern_name! 
    # The system will figure it out.
    run_orchestration_loop(
        user_intent="I need a module to calculate the primary ratio for our production mix. Watch out for float errors.", 
        target_model="gemini_pro", 
        project_name="ProductionSystem"
    )
