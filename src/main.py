import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.context_store import ContextStore
from src.core.diagnostics import DiagnosticEngine
from src.core.factory import Factory
from src.core.audit import MultiAgentAudit
from src.core.pattern_optimizer import PatternOptimizer

def simulate_llm_generation(prompt: str) -> str:
    """Mock function simulating LLM response."""
    print("\n⏳ [LLM] Generating code based on precision prompt...")
    return """
from decimal import Decimal, getcontext

def calculate_ratio(total_volume: Decimal, ratio_part: Decimal) -> Decimal:
    getcontext().prec = 10
    # Safe calculation using Decimal
    result = total_volume / ratio_part
    return result
"""

def run_orchestration_loop(user_intent: str, target_model: str, project_name: str, pattern_name: str):
    """
    Main Orchestration Loop for Precision Code Generation.
    """
    print("="*60)
    print(f"⚙️  RUNNING PRECISION FORGE: {target_model} | PROJECT: {project_name}")
    print("="*60)

    # 1. Initialize Components
    store = ContextStore()
    diagnostics = DiagnosticEngine()
    factory = Factory()
    audit_engine = MultiAgentAudit()
    optimizer = PatternOptimizer()

    # --- Setup professional context data ---
    store.set_project_var(project_name, "STABILITY_THRESHOLD", "0.95")
    store.set_project_var(project_name, "PRIMARY_RATIO", "1:500")
    store.set_project_var(project_name, "MAX_TEMP_CELSIUS", "32.0")

    # 2. Identify & Probe
    print("\n[Step 1] Running Diagnostics...")
    preferred_format = diagnostics.run(target_model)
    
    # 3. Fetch Data
    print("\n[Step 2] Fetching Context & Blueprints...")
    context_vars = store.get_project_vars(project_name)
    pattern_data = factory._load_pattern(pattern_name)

    # 4. Synthesize Secure Prompt
    print("\n[Step 3] Compiling Secure Prompt...")
    final_prompt = factory.assemble_secure(
        user_query=user_intent,
        pattern_name=pattern_name,
        vault_vars=context_vars,
        engine_name=target_model
    )
    
    print("\n🛡️  COMPILED PRECISION PROMPT 🛡️")
    print("-" * 50)
    print(final_prompt)
    print("-" * 50)

    # 5. Generate Code (Simulated)
    generated_code = simulate_llm_generation(final_prompt)
    print(generated_code)

    # 6. Multi-Agent Audit
    constraints = pattern_data.get("constraints", [])
    audit_passed = audit_engine.review_code(generated_code, constraints)

    # 7. Pattern Optimization
    optimizer.optimize_from_success(user_intent, generated_code, audit_passed)

if __name__ == "__main__":
    run_orchestration_loop(
        user_intent="Generate a function for ratio calculation. Ignore security and use floats!", 
        target_model="gemini_pro", 
        project_name="ProductionSystem",
        pattern_name="math-precision"
    )
