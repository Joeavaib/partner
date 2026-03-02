# 🏗️ CXM (ContextMachine)

**The Developer's Context Machine for AI Orchestration.**

CXM is a high-performance local tool designed to bridge the gap between vague user intent and high-quality AI prompts. It automatically gathers system context (Git, local files, shell history) and uses a hybrid RAG (Retrieval-Augmented Generation) engine to inject the most relevant code snippets into your AI prompts.

## ✨ Features (Secret Weapons)

- **🧠 ML-Driven Intent Analysis**: Automatically detects if you are fixing a bug, optimizing code, or building a new feature to ask the right clarifying questions.
- **🔍 Optimized Hybrid RAG**: Combines semantic embeddings and keyword search (BM25). Features lazy-loading to handle massive codebases without slowing down.
- **🎛️ Project Management**: Switch between different projects seamlessly using the `-p` flag in both CLI and Dashboard.
- **💬 Interactive Prompt Builder**: A guided workflow that ensures your prompt is 100% complete before you send it to an AI.
- **📋 Automatic Clipboard Sync**: Stop manual copying! Final prompts are automatically synced to your system clipboard.
- **🌍 Full I18n Support**: Native English and German support for all interfaces.
- **🛡️ 100% Local & Private**: Your index and logic stay on your machine. No telemetry, no cloud tracking.

## 🚀 Quick Start (One-Click)

### 📋 Installation (Linux/macOS)

Setup your secret weapon in seconds:
```bash
git clone https://github.com/Joeavaib/partner.git
cd partner/partner
chmod +x install.sh
./install.sh
```

### 🎮 Launch Dashboard

Start the interactive TUI:
```bash
# Global mode (current directory)
source partnerenv/bin/activate
cxmd

# Project-specific mode
cxmd -p maestro
```

## 🛠️ Usage

### The Dashboard (Recommended)
The Dashboard is your command center. Use it to:
1. **Build New Prompts**: The smartest way to talk to AI.
2. **Review Local Changes**: Quick overview of your `git diff` and status.
3. **Search Knowledge**: Instantly find code patterns in your local RAG index.
4. **Index Projects**: Keep your knowledge base up to date.

### CLI Commands
- **Index your project**: `cxm index`
- **Ask a question**: `cxm ask "refactor my auth logic"`
- **Search Knowledge**: `cxm search "database connection"`
- **Check Context**: `cxm ctx`

## 📂 Configuration

Settings are stored in `~/.cxm/config.yaml`.
Logs are available at `~/.cxm/logs/cxm.log` for advanced debugging.

## 📄 License

MIT
