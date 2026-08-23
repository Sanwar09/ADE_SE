import os
import glob
from typing import Dict, List, Optional
import chromadb

SUPPORTED_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.go', '.rs', '.rb', '.php', '.sql', '.html', '.css', '.json', '.xml', '.yml', '.yaml', '.md', '.txt', '.env', '.toml', '.cfg', '.ini', '.sh', '.bat', '.ps1', 'Dockerfile', 'docker-compose.yml', 'Makefile', '.gitignore', '.dockerignore'
}

EXCLUDED_DIRS = {
    '.git', 'node_modules', 'venv', '.venv', 'env', '__pycache__', '.pytest_cache', 'build', 'dist', '.idea', '.vscode', '.next', '.nuxt', 'target', 'bin', 'obj', '.tox', '.mypy_cache', '.eggs', '*.egg-info'
}

class FileStore:
    """
    In-memory file content store with ChromaDB semantic search.
    The CORE of the system - stores actual file contents for retrieval.
    """
    
    def __init__(self):
        self.files: Dict[str, str] = {}  # {rel_path: content}
        self.file_metadata: Dict[str, dict] = {}  # {rel_path: {size, ext, language, lines}}
        # Create an ephemeral client for in-memory storage
        self.client = chromadb.EphemeralClient()
        self.collection = self.client.get_or_create_collection(name="codebase")
    
    def ingest(self, repo_path: str):
        """Walk directory, read all source files, build ChromaDB index."""
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not any(glob.fnmatch.fnmatch(d, p) for p in EXCLUDED_DIRS)]
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)
                ext = os.path.splitext(file)[1]
                if ext not in SUPPORTED_EXTENSIONS and file not in SUPPORTED_EXTENSIONS:
                    continue
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    self.files[rel_path] = content
                    self.file_metadata[rel_path] = {
                        "size": len(content),
                        "ext": ext,
                        "lines": len(content.splitlines())
                    }
                    
                    # chunking for large files
                    chunks = [content[i:i+4000] for i in range(0, len(content), 4000)]
                    for idx, chunk in enumerate(chunks):
                        chunk_id = f"{rel_path}_{idx}"
                        self.collection.add(
                            documents=[chunk],
                            metadatas=[{"path": rel_path}],
                            ids=[chunk_id]
                        )
                except Exception:
                    # Ignore encoding errors
                    pass

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Semantic search. Returns list of {path, content, score}."""
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        out = []
        if not results['documents']:
            return out
        for i in range(len(results['documents'][0])):
            doc = results['documents'][0][i]
            meta = results['metadatas'][0][i]
            dist = results['distances'][0][i] if 'distances' in results and results['distances'] else 0.0
            out.append({
                "path": meta["path"],
                "content": doc,
                "score": dist
            })
        return out

    def get_file(self, rel_path: str) -> Optional[str]:
        """Get full content of a specific file."""
        return self.files.get(rel_path)

    def get_all_paths(self) -> List[str]:
        """Get all indexed file paths."""
        return list(self.files.keys())

    def get_file_tree(self) -> str:
        """Generate formatted directory tree string."""
        paths = sorted(self.get_all_paths())
        return "\n".join(paths)

    def get_files_by_extension(self, ext: str) -> Dict[str, str]:
        """Get all files with a specific extension."""
        return {k: v for k, v in self.files.items() if k.endswith(ext)}

    def get_key_files(self) -> Dict[str, str]:
        """Get contents of key project files: README, package.json, requirements.txt, main entry points, Dockerfile, etc."""
        key_names = ['readme.md', 'package.json', 'requirements.txt', 'main.py', 'dockerfile', 'docker-compose.yml', 'index.js', 'app.py']
        return {k: v for k, v in self.files.items() if os.path.basename(k).lower() in key_names}
