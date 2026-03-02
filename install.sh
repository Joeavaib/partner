#!/bin/bash

# CXM (ContextMachine) - One-Click Installer
# "Because manual setup is for people without Secret Weapons."

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏗️  CXM (ContextMachine) Installer starting...${NC}"

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python3 is not installed.${NC}"
    exit 1
fi

# 2. Install System Dependencies (Linux specific)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "${BLUE}📦 Checking system dependencies (xclip)...${NC}"
    if ! command -v xclip &> /dev/null; then
        echo -e "${YELLOW}Notice: xclip is missing (needed for clipboard support).${NC}"
        if command -v apt-get &> /dev/null; then
            echo "Installing xclip via apt..."
            sudo apt-get update && sudo apt-get install -y xclip
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y xclip
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm xclip
        fi
    fi
fi

# 3. Create Virtual Environment
if [ ! -d "partnerenv" ]; then
    echo -e "${BLUE}🐍 Creating virtual environment (partnerenv)...${NC}"
    python3 -m venv partnerenv
else
    echo -e "${BLUE}✅ partnerenv already exists.${NC}"
fi

# 4. Install Package
echo -e "${BLUE}🛠️  Installing CXM and dependencies...${NC}"
source partnerenv/bin/activate
pip install --upgrade pip setuptools
pip install -e meta-orchestrator

# 5. Finalize
echo -e "
${GREEN}✨ Installation successful!${NC}"
echo -e "${YELLOW}--------------------------------------------------${NC}"
echo -e "To start your Secret Weapon, run:"
echo -e "  ${BLUE}source partnerenv/bin/activate${NC}"
echo -e "  ${BLUE}cxmd${NC}"
echo -e "${YELLOW}--------------------------------------------------${NC}"
