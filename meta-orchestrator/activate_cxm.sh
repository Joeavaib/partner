#!/bin/bash
# Activate CXM (ContextMachine) Environment

# Project paths
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$HOME/.cxm/venv"

# Activate Python environment
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
else
    echo "Warning: Python virtual environment not found at $VENV_PATH"
fi

# Export useful variables
export CXM_WORKSPACE="$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Aliases are no longer needed as the tool is globally installed via pip.
# The executable 'cxm' is available in your PATH.

echo "🚀 CXM (ContextMachine) Environment Ready!"
echo "--------------------------------"
echo "Workdir: $CXM_WORKSPACE"
echo "Commands available (via pip install -e .):"
echo "  cxm ask 'Deine Frage'  - Interaktiver Prompt Builder"
echo "  cxm index              - Aktualisiert den lokalen RAG-Index"
echo "  cxm ctx                - Zeigt den aktuellen Systemkontext an"
echo "  cxm --help             - Zeigt alle CLI-Befehle"
