# 🏗️ CXM (ContextMachine) - Precision Code Forge

**The Architect's Command Center for Deterministic AI Orchestration & Vibecoding.**

CXM is a high-performance local framework designed to transform vague user intent ("vibes") into production-grade, secure code. It features an autonomous **Vibe Router**, a **Precision Protocol** against prompt injections, and a **Multi-Agent Audit** system to ensure every line of generated code meets enterprise standards before automatically patching it into your project.

---

## 🚀 The Vibecoding Experience (Zero-Click Coding)

Stop writing boilerplate. Just provide the "vibe" or intent, and CXM handles the rest autonomously:

1. **Vibe Routing:** You ask for a "secure login route". CXM's semantic router automatically selects the appropriate `api-security` Blueprint from your Vault. No manual configuration needed.
2. **Synthetic Blueprints:** Ask for something completely new? CXM generates a temporary set of architectural constraints on-the-fly to ensure the LLM doesn't hallucinate bad practices.
3. **Auto-Patching:** Once the code is generated and audited, CXM's `FilePatcher` applies the code directly to your local files using XML-style `<file_patch>` blocks.

---

## 🛡️ The Precision Security Stack & Guardrails

CXM is hardened for professional environments. You maintain absolute control via the `.cxm.yaml` Project Manifest:

- **Strict Write Protection:** The `FilePatcher` will *only* modify files within the `allowed_write_paths` defined in your `.cxm.yaml`. Malicious LLM outputs attempting to overwrite core files are hard-blocked.
- **Scraping Boundaries:** Define `include_paths` and `exclude_paths` in `.cxm.yaml` to ensure the RAG engine only indexes what is relevant, protecting isolated or sensitive modules.
- **Injection-Proof Prompting**: Uses strict `[USER_DATA]` delimiters to prevent prompt manipulation.
- **Safe System Execution**: Zero use of `shell=True`. All commands are executed via isolated argument lists.

---

## ✨ Key Features (Nuclear Arsenal)

### 🧠 1. Pattern Vault & Blueprints
Stop relying on generic "Senior Dev" personas. CXM uses **Cognitive Blueprints** (YAML patterns) to force LLMs into specific architectural rails.

### 🔍 2. Advanced Selection Layer (The Gatekeeper)
Retrieved context must justify its existence. Our **Context Evaluator** performs:
- **Semantic Relevance Check**: Only highly relevant snippets pass the gate.
- **Trigram Deduplication**: Advanced character-level filtering removes redundant code hits, saving massive token costs.

### 🧪 3. Multi-Agent Audit Loop
Before code reaches the `FilePatcher`, it undergoes a triple-agent review:
- **EfficiencyAudit**: Detects Big-O bottlenecks and scaling issues.
- **ComplianceAudit**: Verifies adherence to business logic and constraints.
- **SecurityAudit**: Hunts for injection vectors and malformed input handling.

### ⚡ 4. High-Performance RAG
- **HNSW Vector Search**: Graph-based search using True Cosine Similarity for millisecond response times on large codebases.
- **Reciprocal Rank Fusion (RRF)**: Industry-standard algorithm for merging keyword and semantic searches robustly.

---

## 🚀 Quick Start

### 📋 Installation

```bash
# Clone and setup
git clone https://github.com/Joeavaib/partner.git
cd partner
python3 -m venv venv
source venv/bin/activate

# Install with pinned dependencies
pip install -r requirements.txt
pip install -e .
```

### ⚙️ Setup Guardrails

Initialize your `.cxm.yaml` in your project root to control CXM's boundaries:

```yaml
scraping:
  include_paths: ["src/"]
  exclude_paths: ["tests"]
patching:
  mode: ask_first # Or 'true' for full autonomy
  allowed_write_paths: ["src/utils", "src/modules"]
```

### 🛠️ Basic Usage

**Run the Autonomous Vibecoding Loop:**
```bash
# Test the autonomous flow with a vibe (no specific pattern required)
python3 src/main.py
```

---

## 📂 Project Structure

```plaintext
partner/
├── docs/                  # Documentation
├── src/
│   ├── core/              # RAG, Audit, Patcher, Factory, ContextStore
│   ├── ml/                # Intent-Analyzer, Evaluator, Assembler
│   ├── resources/         # Coding-Patterns (Blueprints)
│   ├── engines/           # Model Geometry (JSON)
│   ├── utils/             # Paths, Logger
│   └── main.py            # Orchestration Loop
├── .cxm.yaml              # Security Guardrails & Manifest
├── tests/                 # Pytest Suite
└── pyproject.toml         # Package Configuration
```

## 🧪 Testing

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
pytest tests/
```

## 📄 License
MIT
