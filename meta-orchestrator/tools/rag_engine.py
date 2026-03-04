#!/usr/bin/env python3
"""
RAG Engine for CXM
- Semantic Search & Indexing
"""
import sys
import os
import subprocess

# Suppress HuggingFace/transformers logging and progress bars
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'

import json
import sqlite3
import numpy as np
import faiss
from pathlib import Path
from datetime import datetime
import warnings

warnings.filterwarnings('ignore', category=UserWarning)

from sentence_transformers import SentenceTransformer

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge-base"
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = KNOWLEDGE_DIR / "knowledge.db"
INDEX_PATH = KNOWLEDGE_DIR / "faiss.index"
MODEL_NAME = 'all-MiniLM-L6-v2'

class RAGEngine:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)
        self._init_db()
        self._init_index()

    def _init_db(self):
        """Initialize SQLite metadata storage"""
        self.db = sqlite3.connect(DB_PATH)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE,
                type TEXT,
                content TEXT,
                metadata TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        self.db.commit()

    def _init_index(self):
        """Initialize FAISS vector index"""
        if INDEX_PATH.exists():
            self.index = faiss.read_index(str(INDEX_PATH))
        else:
            # Dimension depends on model (384 for all-MiniLM-L6-v2)
            self.index = faiss.IndexFlatL2(384)

    def save_index(self):
        """Persist index to disk"""
        faiss.write_index(self.index, str(INDEX_PATH))

    def index_document(self, content, doc_type, metadata=None, path=None):
        """Index a single document"""
        if not content.strip():
            return None

        # Generate embedding
        vector = self.model.encode([content])[0]
        
        # Normalize vector for cosine similarity (if using L2 index as approx)
        faiss.normalize_L2(vector.reshape(1, -1))

        # Update Database
        now = datetime.now()
        meta_json = json.dumps(metadata or {})
        
        try:
            cursor = self.db.execute("""
                INSERT INTO documents (path, type, content, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    content=excluded.content,
                    metadata=excluded.metadata,
                    updated_at=excluded.updated_at
            """, (path or f"doc_{self.index.ntotal}", doc_type, content, meta_json, now, now))
            
            doc_id = cursor.lastrowid
            
            # Add to FAISS (assuming ID matches rowid roughly, but for simplicity we append)
            # Note: A real production system would manage IDs more strictly to allow updates/deletes in FAISS
            self.index.add(np.array([vector], dtype=np.float32))
            
            self.db.commit()
            return doc_id
        except Exception as e:
            print(f"Error indexing: {e}")
            return None

    def search(self, query, k=5, doc_type=None):
        """Semantic search"""
        vector = self.model.encode([query])[0]
        faiss.normalize_L2(vector.reshape(1, -1))
        
        # Search
        distances, indices = self.index.search(np.array([vector], dtype=np.float32), k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1: continue
            
            # Retrieve metadata from DB (This is a simplification. 
            # In a robust system, we need a mapping from FAISS ID to DB ID)
            # Here we assume FAISS ID == DB ID - 1 (0-based vs 1-based)
            # WARNING: This desyncs if we update documents. 
            # For v1.0 we stick to this or fetch by content hash? 
            # Let's just fetch by LIMIT/OFFSET strategy if we had a mapping,
            # but for now let's query by rowid.
            
            rowid = int(idx) + 1 
            cursor = self.db.execute("SELECT * FROM documents WHERE rowid=?", (rowid,))
            row = cursor.fetchone()
            
            if row:
                # Filter by type if requested
                if doc_type and row[2] != doc_type:
                    continue
                    
                results.append({
                    'id': row[0],
                    'path': row[1],
                    'type': row[2],
                    'content': row[3],
                    'metadata': json.loads(row[4]),
                    'similarity': float(1 / (1 + distances[0][i])) # Rough conversion L2->Sim
                })
        
        return results

    def index_code_file(self, file_path):
        """Index a code file"""
        path = Path(file_path)
        if not path.exists():
            print(f"File not found: {path}")
            return None
            
        try:
            content = path.read_text(encoding='utf-8')
            return self.index_document(
                content=content,
                doc_type='code',
                metadata={
                    'file_path': str(path.absolute()),
                    'file_name': path.name,
                    'language': path.suffix[1:] if path.suffix else 'unknown',
                    'size': len(content)
                },
                path=str(path.absolute())
            )
        except Exception as e:
            print(f"⚠ Error indexing {file_path}: {e}")
            return None

    def _get_git_files(self, directory: Path):
        """Try to get a list of non-ignored files using git ls-files"""
        try:
            # Check if it's a git repo
            result = subprocess.run(
                ['git', 'rev-parse', '--is-inside-work-tree'],
                cwd=directory, capture_output=True, text=True, check=False
            )
            if result.returncode != 0:
                return None
            
            # Get tracked and untracked-but-not-ignored files
            result = subprocess.run(
                ['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
                cwd=directory, capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                paths = []
                for line in result.stdout.splitlines():
                    paths.append((directory / line).resolve())
                return paths
        except Exception:
            pass
        return None

    def index_directory(self, directory, extensions=None, recursive=True):
        """Index all code files in a directory while respecting .gitignore and common patterns"""
        if extensions is None:
            extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.rs', '.go', '.java', '.c', '.cpp', '.h', '.hpp', '.md', '.txt', '.yaml', '.yml', '.json', '.toml', '.sh', '.sql'}
            
        dir_path = Path(directory).resolve()
        if not dir_path.exists():
            print(f"Directory not found: {dir_path}")
            return 0
            
        # Hardcoded skip lists (fallbacks if not in git or extra safety)
        skip_dirs = {
            '.git', '.svn', '.hg', '.bzr', '__pycache__', 'node_modules', 
            '.venv', 'venv', 'env', '.cxm', 'sessions', 'partnerenv', 
            'knowledge-base', 'build', 'dist', 'target', 'out', 'bin', 'obj', 
            '.idea', '.vscode', '.settings', '.pytest_cache', '.tox',
            'models', 'weights', 'checkpoints', 'datasets'
        }
        skip_exts = {
            # Compiled/Binary
            '.pyc', '.pyo', '.pyd', '.so', '.dylib', '.dll', '.exe', '.bin',
            '.obj', '.o', '.a', '.lib', '.out', '.app',
            # Archives
            '.zip', '.tar', '.gz', '.whl', '.egg', '.7z', '.rar', '.bz2', '.xz',
            # Images/Media
            '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.svg', '.ico', '.mp3', '.mp4', '.wav', '.mov',
            # Models/Large Data
            '.h5', '.pth', '.pt', '.tflite', '.onnx', '.weights', '.pb', '.gguf', 
            '.ckpt', '.safetensors', '.model', '.pkl', '.pickle', '.npy', '.npz',
            # Lock files
            '.lock', 'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock'
        }
        skip_names = {
            'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock', 'composer.lock',
            'Cargo.lock', 'Gemfile.lock', 'poetry.lock', 'mix.lock'
        }
        
        # 1 MB size limit for indexing to avoid models/huge data
        MAX_FILE_SIZE = 1 * 1024 * 1024 
        
        # Try to use git to get file list
        git_files = self._get_git_files(dir_path)
        
        if git_files:
            candidates = git_files
        else:
            pattern = '**/*' if recursive else '*'
            candidates = dir_path.glob(pattern)
            
        indexed = 0
        skipped = 0
        
        for file_path in candidates:
            if not file_path.is_file():
                continue
                
            # Basic filters
            if any(part in skip_dirs or part.endswith('.egg-info') for part in file_path.parts):
                skipped += 1
                continue
                
            if file_path.name.startswith('.') or file_path.name in skip_names:
                skipped += 1
                continue
                
            if file_path.suffix.lower() in skip_exts:
                skipped += 1
                continue
                
            # Size check
            try:
                size = file_path.stat().st_size
                if size < 10 or size > MAX_FILE_SIZE:
                    skipped += 1
                    continue
            except:
                skipped += 1
                continue
                
            # Extension filter
            if extensions and file_path.suffix not in extensions:
                skipped += 1
                continue
            
            if self.index_code_file(file_path):
                indexed += 1
                if indexed % 10 == 0:
                    print(f"  Indexed {indexed} files...")
            else:
                skipped += 1
        
        self.save_index()
        print(f"✓ Indexed {indexed} files, skipped {skipped}")
        return indexed

    def stats(self):
        """Get index statistics"""
        cursor = self.db.execute("""
            SELECT type, COUNT(*) as count FROM documents GROUP BY type
        """)
        stats = {
            'total_documents': self.index.ntotal,
            'by_type': {row[0]: row[1] for row in cursor.fetchall()}
        }
        return stats

def main():
    """CLI Interface"""
    if len(sys.argv) < 2:
        print("""
        Usage:
          rag_engine.py search <query> [--type TYPE] [--limit N]
          rag_engine.py index <path> [--type TYPE]
          rag_engine.py index-dir <directory> [--recursive]
          rag_engine.py stats
        """)
        return

    rag = RAGEngine()
    command = sys.argv[1]

    if command == 'search':
        query = ' '.join(arg for arg in sys.argv[2:] if not arg.startswith('--'))
        doc_type = None
        limit = 5
        
        for i, arg in enumerate(sys.argv):
            if arg == '--type' and i + 1 < len(sys.argv):
                doc_type = sys.argv[i + 1]
            elif arg == '--limit' and i + 1 < len(sys.argv):
                limit = int(sys.argv[i + 1])
                
        results = rag.search(query, k=limit, doc_type=doc_type)
        
        if not results:
            print("No results found.")
            return
            
        print(f"\nTop {len(results)} results for: {query}\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. [{result['type']}] (sim: {result['similarity']:.2f})")
            print(f"   Path: {result['path']}")
            content_preview = result['content'][:200].replace('\n', ' ')
            print(f"   {content_preview}...")
            print()

    elif command == 'index':
        if len(sys.argv) < 3:
            print("Error: Missing file path")
            return
        file_path = sys.argv[2]
        doc_id = rag.index_code_file(file_path)
        if doc_id:
            print(f"✓ Indexed as document #{doc_id}")
            rag.save_index()

    elif command == 'index-dir':
        if len(sys.argv) < 3:
            print("Error: Missing directory path")
            return
        directory = sys.argv[2]
        recursive = '--recursive' in sys.argv
        rag.index_directory(directory, recursive=recursive)

    elif command == 'stats':
        stats = rag.stats()
        print("\n📊 RAG Index Statistics\n")
        print(f"Total documents: {stats['total_documents']}")
        print("\nBy type:")
        for doc_type, count in stats['by_type'].items():
            print(f"  {doc_type}: {count}")
        print()

    else:
        print(f"Unknown command: {command}")

if __name__ == '__main__':
    main()
