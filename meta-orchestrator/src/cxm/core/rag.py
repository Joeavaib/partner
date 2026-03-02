# src/cxm/core/rag.py

from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json
import hashlib
import os

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
        Index single file
        Returns True if indexed, False if skipped
        """
        file_path = Path(file_path).resolve()
        
        if not file_path.exists() or not file_path.is_file():
            return False
        
        if not force and self._is_indexed(file_path):
            return False
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            if not content.strip():
                return False
            
            # Embed
            embedding = self.model.encode([content])[0]
            self.index.add(np.array([embedding], dtype=np.float32))
            
            # Store metadata (WITHOUT full_content for file-based docs)
            self.metadata.append({
                'id': len(self.metadata),
                'path': str(file_path),
                'name': file_path.name,
                'extension': file_path.suffix,
                'size': len(content),
                'hash': self._file_hash(file_path),
                'indexed_at': datetime.now().isoformat(),
                'content_preview': content[:1000], # Keep a larger preview but not all
                # 'full_content': content, <-- REMOVED for space optimization
            })
            
            return True
        except Exception as e:
            logger.error(f"Error indexing {file_path}: {e}")
            return False
    
    def index_directory(
        self,
        directory: Path,
        extensions: Optional[List[str]] = None,
        recursive: bool = True,
        force: bool = False
    ) -> Dict[str, int]:
        """Index all matching files in directory"""
        
        directory = Path(directory)
        if not directory.exists():
            return {'indexed': 0, 'skipped': 0, 'errors': 0}
        
        logger.info(f"Indexing directory: {directory}")
        
        # Collect files
        files = []
        pattern = '**/*' if recursive else '*'
        
        skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.cxm', 'sessions', 'partnerenv', 'knowledge-base', 'build', 'dist'}
        skip_exts = {'.pyc', '.so', '.dylib', '.dll', '.exe', '.bin',
                     '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip',
                     '.tar', '.gz', '.whl', '.egg'}
        
        for file_path in directory.glob(pattern):
            if not file_path.is_file():
                continue
            
            # Skip hidden/ignored dirs and egg-info
            if any(part in skip_dirs or part.endswith('.egg-info') for part in file_path.parts):
                continue
            
            if file_path.name.startswith('.'):
                continue
            
            if file_path.suffix.lower() in skip_exts:
                continue

            # Skip tiny files (e.g. top_level.txt which is often just one word)
            try:
                if file_path.stat().st_size < 10:
                    continue
            except:
                continue
            
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
        
        distances, indices = self.index.search(
            np.array([query_emb], dtype=np.float32),
            min(k, len(self.metadata))
        )
        
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            
            similarity = float(1 / (1 + dist))
            
            if similarity < min_similarity:
                continue
            
            result = self.metadata[idx].copy()
            result['similarity'] = similarity
            result['distance'] = float(dist)
            
            # Lazy load full content for search results
            result['full_content'] = self._get_content(result)
            
            results.append(result)
        
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
