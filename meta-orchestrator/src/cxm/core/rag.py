# src/cxm/core/rag.py

from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json
import hashlib
import os
import subprocess

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from tqdm import tqdm

from cxm.utils.logger import logger

class RAGEngine:
    """
    Core indexing and retrieval
    
    - Embeddings via sentence-transformers
    - Vector storage via FAISS
    - Metadata via JSON (no external DB needed)
    - Incremental indexing with change detection
    - Optimized: Full content is not stored in metadata.json to save space
    """
    
    def __init__(self, workspace: Path, model_name: str = 'all-MiniLM-L6-v2'):
        # Suppress logging before model load
        os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
        os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
        
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        self.index_path = self.workspace / "faiss.index"
        self.metadata_path = self.workspace / "metadata.json"
        
        # Load model
        logger.info(f"Initializing RAGEngine with model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        # Load or create index
        if self.index_path.exists() and self.metadata_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                with open(self.metadata_path) as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded existing index with {len(self.metadata)} documents.")
            except Exception as e:
                logger.error(f"Failed to load index: {e}. Creating new one.")
                self.index = faiss.IndexFlatL2(self.embedding_dim)
                self.metadata = []
        else:
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.metadata = []
    
    def _file_hash(self, path: Path) -> str:
        return hashlib.md5(path.read_bytes()).hexdigest()
    
    def _is_indexed(self, path: Path) -> bool:
        """Check if file already indexed with same hash"""
        file_hash = self._file_hash(path)
        return any(
            m.get('path') == str(path.resolve()) and m.get('hash') == file_hash
            for m in self.metadata
        )
    
    def _get_content(self, metadata: Dict) -> str:
        """Retrieve full content from disk if possible, else return stored preview"""
        path = Path(metadata.get('path', ''))
        if path.exists() and path.is_file():
            try:
                return path.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                pass
        return metadata.get('full_content', metadata.get('content_preview', ''))

    def index_file(self, file_path: Path, force: bool = False) -> bool:
        """
        Index file by splitting it into overlapping chunks for better retrieval precision.
        Returns True if at least one chunk was indexed.
        """
        file_path = Path(file_path).resolve()
        
        if not file_path.exists() or not file_path.is_file():
            return False
        
        file_hash = self._file_hash(file_path)
        
        # Check if already indexed with same hash
        if not force and self._is_indexed(file_path):
            return False
            
        # If file already exists in index but hash is different (or force), 
        # we should ideally remove old chunks.
        # For simplicity in this local-first tool, we mark them as deleted.
        self._remove_file_chunks(file_path)
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            if not content.strip():
                return False
            
            # Simple chunking strategy: split by character count with overlap
            # 1200 chars is ~300 tokens, 200 char overlap
            CHUNK_SIZE = 1200 
            OVERLAP = 200
            
            chunks = []
            if len(content) <= CHUNK_SIZE:
                chunks = [content]
            else:
                start = 0
                while start < len(content):
                    end = start + CHUNK_SIZE
                    chunk = content[start:end]
                    if chunk.strip():
                        chunks.append(chunk)
                    start += (CHUNK_SIZE - OVERLAP)
            
            if not chunks:
                return False

            # Embed all chunks
            embeddings = self.model.encode(chunks)
            self.index.add(np.array(embeddings, dtype=np.float32))
            
            # Store metadata for each chunk
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                self.metadata.append({
                    'id': len(self.metadata), # ID in metadata matches FAISS index
                    'path': str(file_path),
                    'name': file_path.name,
                    'extension': file_path.suffix,
                    'size': len(content),
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'hash': file_hash,
                    'indexed_at': datetime.now().isoformat(),
                    'content_preview': chunk, # In chunk mode, preview IS the chunk
                })
            
            return True
        except Exception as e:
            logger.error(f"Error indexing {file_path}: {e}")
            return False

    def _remove_file_chunks(self, file_path: Path):
        """Mark all chunks belonging to a specific file as deleted"""
        path_str = str(file_path.resolve())
        for m in self.metadata:
            if m.get('path') == path_str:
                m['_deleted'] = True
    
    def _get_git_files(self, directory: Path) -> Optional[List[Path]]:
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
                    # Handle case where git returns paths relative to repo root
                    # but we might be indexing a subdirectory.
                    # Actually ls-files in cwd returns paths relative to cwd.
                    paths.append((directory / line).resolve())
                return paths
        except Exception:
            pass
        return None

    def index_directory(
        self,
        directory: Path,
        extensions: Optional[List[str]] = None,
        recursive: bool = True,
        force: bool = False
    ) -> Dict[str, int]:
        """Index all matching files in directory while respecting .gitignore and common patterns"""
        
        directory = Path(directory).resolve()
        if not directory.exists():
            return {'indexed': 0, 'skipped': 0, 'errors': 0}
        
        logger.info(f"Indexing directory: {directory}")
        
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
        
        # 10 MB size limit for indexing to avoid models/huge data
        MAX_FILE_SIZE = 10 * 1024 * 1024 
        
        # Try to use git to get file list
        git_files = self._get_git_files(directory)
        
        if git_files:
            logger.info(f"Using git ls-files for discovery ({len(git_files)} candidates)")
            candidates = git_files
        else:
            logger.info("Using standard directory walking (not a git repo or git failed)")
            pattern = '**/*' if recursive else '*'
            candidates = directory.glob(pattern)
            
        files = []
        for file_path in candidates:
            if not file_path.is_file():
                continue
                
            # Basic filters
            if any(part in skip_dirs or part.endswith('.egg-info') for part in file_path.parts):
                continue
                
            if file_path.name.startswith('.') or file_path.name in skip_names:
                continue
                
            if file_path.suffix.lower() in skip_exts:
                continue
                
            # Size check
            try:
                size = file_path.stat().st_size
                if size < 10 or size > MAX_FILE_SIZE:
                    continue
            except:
                continue
                
            # Extension filter (if provided)
            if extensions and file_path.suffix not in extensions:
                continue
            
            files.append(file_path)
            
        # Index
        stats = {'indexed': 0, 'skipped': 0, 'errors': 0}
        
        for f in tqdm(files, desc="Indexing", disable=len(files) < 10):
            try:
                if self.index_file(f, force=force):
                    stats['indexed'] += 1
                else:
                    stats['skipped'] += 1
            except Exception:
                stats['errors'] += 1
                
        self.save()
        logger.info(f"Indexing complete. Stats: {stats}")
        return stats
    
    def index_text(self, content: str, source: str = "manual", metadata: Dict = None) -> int:
        """
        Index arbitrary text (conversations, notes, etc.)
        Returns document ID. Here we KEEP the content as it has no file source.
        """
        if not content.strip():
            return -1
        
        embedding = self.model.encode([content])[0]
        self.index.add(np.array([embedding], dtype=np.float32))
        
        doc_id = len(self.metadata)
        
        entry = {
            'id': doc_id,
            'path': source,
            'name': source,
            'extension': '',
            'size': len(content),
            'hash': hashlib.md5(content.encode()).hexdigest(),
            'indexed_at': datetime.now().isoformat(),
            'content_preview': content[:1000],
            'full_content': content, # Keep for non-file based texts
        }
        
        if metadata:
            entry.update(metadata)
        
        self.metadata.append(entry)
        self.save()
        
        return doc_id
    
    def search(
        self,
        query: str,
        k: int = 5,
        min_similarity: float = 0.0
    ) -> List[Dict]:
        """Semantic search"""
        
        if len(self.metadata) == 0:
            return []
        
        query_emb = self.model.encode([query])[0]
        
        # Search for more than k to account for deleted items
        fetch_k = min(k * 5, len(self.metadata))
        
        distances, indices = self.index.search(
            np.array([query_emb], dtype=np.float32),
            fetch_k
        )
        
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            
            metadata = self.metadata[idx]
            if metadata.get('_deleted'):
                continue
                
            similarity = float(1 / (1 + dist))
            
            if similarity < min_similarity:
                continue
            
            result = metadata.copy()
            result['similarity'] = similarity
            result['distance'] = float(dist)
            
            # Lazy load full content for search results
            result['full_content'] = self._get_content(result)
            
            results.append(result)
            if len(results) >= k:
                break
        
        return results
    
    def get_document(self, doc_id: int) -> Optional[Dict]:
        """Get document by ID with content resolution"""
        if 0 <= doc_id < len(self.metadata):
            doc = self.metadata[doc_id].copy()
            doc['full_content'] = self._get_content(doc)
            return doc
        return None
    
    def remove_document(self, doc_id: int):
        """Mark document as removed"""
        if 0 <= doc_id < len(self.metadata):
            self.metadata[doc_id]['_deleted'] = True
            self.save()
    
    def save(self):
        """Persist to disk"""
        try:
            faiss.write_index(self.index, str(self.index_path))
            with open(self.metadata_path, 'w') as f:
                json.dump(self.metadata, f)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def stats(self) -> Dict:
        active_docs = [m for m in self.metadata if not m.get('_deleted')]
        total_size = sum(m.get('size', 0) for m in active_docs)
        
        extensions = {}
        for m in active_docs:
            ext = m.get('extension', 'unknown')
            extensions[ext] = extensions.get(ext, 0) + 1
        
        return {
            'total_documents': len(active_docs),
            'index_vectors': self.index.ntotal,
            'total_bytes': total_size,
            'by_extension': extensions,
        }
    
    def clear(self):
        """Reset entire index"""
        logger.info("Clearing entire index.")
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.metadata = []
        self.save()
