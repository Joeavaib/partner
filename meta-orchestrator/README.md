# 🏗️ CXM (ContextMachine)

**The Developer's Context Machine for AI Orchestration.**

CXM is a powerful local tool designed to bridge the gap between vague user intent and high-quality AI prompts. It automatically gathers system context (Git, local files, active CLI sessions) and uses RAG (Retrieval-Augmented Generation) to inject relevant code snippets into your prompts.

## ✨ Features (Secret Weapons)

- **🧠 ML-Driven Intent Analysis**: Automatically detects if you're trying to fix a bug, optimize code, or generate a new feature.
- **🔍 Optimized Hybrid RAG**: Combines semantic search (embeddings) and keyword search (BM25). Lazy loading ensures high performance even with large codebases.
- **💬 Interactive Prompt Refinement**: The CLI/Dashboard asks clarifying questions to build a perfect prompt.
- **🌍 Full I18n Support**: Switch between German and English in the Dashboard.
- **📋 Automatic Clipboard Sync**: Generated prompts are automatically copied to your clipboard—no manual terminal copying needed.
- **🛡️ 100% Local & Private**: Your code index and logic stay on your machine. No cloud tracking.

## 🚀 Quick Start (One-Click)

### 📋 Installation (Linux/macOS)

**1. Clone and Setup:**
```bash
git clone https://github.com/Joeavaib/partner.git
cd partner/partner
chmod +x install.sh
./install.sh
```

**2. Launch Dashboard:**
```bash
source partnerenv/bin/activate
cxmd
```

## 🛠️ Usage

### Dashboard (Recommended)
Launch the interactive TUI (Terminal User Interface) to manage everything:
```bash
cxmd
```

### CLI Commands
- **Index your project**: `cxm index`
- **Ask a question**: `cxm ask "optimize my route handler in api.py"`
- **Search Knowledge**: `cxm search "your query"`
- **Check Context**: `cxm ctx`

## 📂 Configuration

Customize paths and behavior in `~/.cxm/config.yaml`.
Logs are stored at `~/.cxm/logs/cxm.log`.

## 📄 License

MIT
