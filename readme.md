# 🏗️ CXM (ContextMachine) - Precision Code Forge

**The Architect's Command Center for Deterministic AI Orchestration.**

CXM is a high-performance local framework designed to transform vague user intent into production-grade, secure code. It uses a **Precision Protocol** to shield against prompt injections and a **Multi-Agent Audit** system to ensure every line of generated code meets enterprise standards for efficiency and security.

---

## 🛡️ The Precision Security Stack

CXM is hardened for professional environments:
- **Injection-Proof Prompting**: Uses strict [USER_DATA] delimiters and a decoupled system-core to prevent prompt manipulation.
- **Safe System Execution**: Zero use of `shell=True`. All commands are executed via isolated argument lists.
- **Path Traversal Protection**: RAG engine rigorously validates file paths and symlinks to prevent data exfiltration.
- **Secret Management**: Sensitive keys are routed via environment variables, never stored in plaintext configuration files.

---

## ✨ Key Features (Nuclear Arsenal)

### 🧠 1. Pattern Vault & Blueprints
Stop relying on generic "Senior Dev" personas. CXM uses **Cognitive Blueprints** (YAML patterns) to force LLMs into specific architectural rails. Whether it's high-precision math or secure API design, the blueprint dictates the logic.

### 🔍 2. Advanced Selection Layer (The Gatekeeper)
Retrieved context must justify its existence. Our **Context Evaluator** performs:
- **Semantic Relevance Check**: Only highly relevant snippets pass the gate.
- **Deduplication**: Jaccard-based filtering removes redundant hits, saving massive token costs.
- **Checklist Visualization**: Interactive feedback on why each file was selected or discarded.

### 🧪 3. Multi-Agent Audit Loop
Before code reaches you, it undergoes a triple-agent review:
- **EfficiencyAudit**: Detects Big-O bottlenecks and scaling issues.
- **ComplianceAudit**: Verifies adherence to business logic and constraints.
- **SecurityAudit**: Hunts for injection vectors and malformed input handling.

### ⚡ 4. High-Performance RAG
- **HNSW Vector Search**: Graph-based search for millisecond response times on large codebases.
- **Smart Chunking**: Logical block-splitting (functions/classes) instead of blind character cuts.

---

## 🚀 Quick Start (Clean Structure)

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

### 🛠️ Basic Usage

**Build an Enhanced Prompt:**
```bash
python3 src/cli.py ask "Generate a ratio calculation function"
```

**Run the Orchestration Loop (Direct):**
```bash
python3 src/main.py
```

---

## 📂 Project Structure (Flattened)

```plaintext
partner/
├── docs/                  # Documentation & Visions
├── src/
│   ├── core/              # RAG, Audit, Diagnostics, Factory
│   ├── ml/                # Intent-Analyzer, Evaluator, Assembler
│   ├── resources/         # Coding-Patterns, Diagnostic-Templates
│   ├── engines/           # Model Geometry (JSON)
│   ├── utils/             # Paths, Logger, i18n
│   └── main.py            # Orchestration Loop
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
