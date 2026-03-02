# 🏗️ CXM (ContextMachine)

**The Developer's Context Machine for AI Orchestration.**

CXM is a powerful local tool designed to bridge the gap between vague user intent and high-quality AI prompts. It automatically gathers system context (Git, local files, active CLI sessions) and uses RAG (Retrieval-Augmented Generation) to inject relevant code snippets into your prompts.

## ✨ Features

- **🧠 ML-Driven Intent Analysis**: Automatically detects if you're trying to fix a bug, optimize code, or generate a new feature.
- **🔍 Hybrid RAG**: Combines semantic search (embeddings) and keyword search (BM25) to find the most relevant parts of your codebase.
- **💬 Interactive Prompt Refinement**: If your request is too vague, the CLI will ask clarifying questions to build a perfect prompt.
- **🔄 Session Awareness**: Plugs into your active Gemini CLI chat history to maintain continuity.
- **🛡️ 100% Local**: Your code index and logic stay on your machine.

## 🚀 Quick Start

### 📋 Installation

CXM is designed for **Linux** and **Windows**.

**1. Clone the repository:**
```bash
git clone https://github.com/Joeavaib/partner.git
cd partner
```

**2. Setup environment (Linux):**
```bash
python3 -m venv partnerenv
source partnerenv/bin/activate
pip install -e meta-orchestrator
```

**3. Setup environment (Windows):**
```powershell
python -m venv partnerenv
.\partnerenv\Scripts\Activate.ps1
pip install -e meta-orchestrator
```

> **Detailed Installation Guide**: For system-specific prerequisites like `xclip` or FAISS build tools, please refer to our **[INSTALL.md](./INSTALL.md)**.

## 🛠️ Usage

### 1. Index your project
Before starting, create a local knowledge base of your current project:
```bash
cxm index
```

### 2. Ask a question
Use the interactive builder to generate an optimized prompt:
```bash
cxm ask "mach meine funktion in app.py schneller"
```
The tool will analyze your intent, ask missing questions, and output a fully-formed prompt that you can paste into Gemini.

### 3. Check Context
See what CXM currently knows about your environment:
```bash
cxm ctx
```

## 📂 Configuration

You can customize paths and behavior in `~/.cxm/config.yaml` or a local `cxm.yaml`.

## 📄 License

MIT
