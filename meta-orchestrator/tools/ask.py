#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add src to pythonpath
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from cxm import Config, RAGEngine, PromptEnhancer

def main():
    if len(sys.argv) < 2:
        print("Usage: python ask.py <prompt>")
        sys.exit(1)
        
    prompt = " ".join(sys.argv[1:])
    
    config = Config()
    # Explicitly point to the knowledge-base so it shares index with other tools
    workspace = Path(__file__).resolve().parent.parent / "knowledge-base"
    
    rag = RAGEngine(workspace)
    enhancer = PromptEnhancer(rag)
    
    # Generate enhanced prompt
    result = enhancer.enhance(prompt)
    
    # Save the prompt to a file for easy copying
    output_dir = Path(__file__).resolve().parent.parent / "sessions" / "ask"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Clean old ones or just overwrite the single current one
    output_file = output_dir / "latest_prompt.txt"
    output_file.write_text(result['enhanced'])
    
    print(result['enhanced'])
    print("\n--------------------------------------------------------")
    print(f"📁 Gespeichert in: {output_file}")

if __name__ == "__main__":
    main()