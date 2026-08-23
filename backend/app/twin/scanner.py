import os
from typing import Dict, Any, Tuple
from .parser import CodeParser
from .graph_builder import RepositoryDigitalTwin
from .file_store import FileStore

EXCLUDED_DIRS = {
    '.git', 'node_modules', 'venv', '.venv', 'env', '__pycache__',
    '.pytest_cache', 'build', 'dist', '.idea', '.vscode', '.next',
    '.nuxt', 'target', 'bin', 'obj', '.tox', '.mypy_cache', '.eggs'
}

# Extensions the AST parser can handle
AST_EXTENSIONS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.sql'}


class RepositoryScanner:
    """
    Scans target codebase directories, parses code ASTs, populates the
    RepositoryDigitalTwin graph, AND indexes all file contents into a FileStore
    for semantic search.
    """

    def __init__(self, target_path: str):
        self.target_path = os.path.abspath(target_path)
        self.twin = RepositoryDigitalTwin(self.target_path)
        self.file_store = FileStore()

    def scan(self) -> Tuple[RepositoryDigitalTwin, FileStore]:
        """
        Full repository scan:
        1. Walk directory tree
        2. Read all source files into FileStore (for semantic search)
        3. Parse AST for supported languages (for graph metadata)
        4. Build the Code Property Graph in RepositoryDigitalTwin
        
        Returns (twin, file_store) tuple.
        """
        if not os.path.exists(self.target_path):
            raise ValueError(f"Repository path does not exist: {self.target_path}")

        # Step 1: Ingest all file contents into FileStore for semantic search
        self.file_store.ingest(self.target_path)

        # Step 2: Walk directory and build the Code Property Graph
        for root, dirs, files in os.walk(self.target_path):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.target_path)

                # Determine language for graph node
                lang = self._detect_language(ext, file)
                if lang is None:
                    continue

                # Add file node to Digital Twin graph
                self.twin.add_file_node(full_path, language=lang)

                # AST parsing only for supported languages
                if ext in AST_EXTENSIONS or file == 'Dockerfile':
                    self._parse_and_index(full_path, rel_path)

        self.twin.metadata["test_status"] = "INITIALIZED"
        return self.twin, self.file_store

    def _detect_language(self, ext: str, filename: str) -> str:
        """Detect programming language from file extension."""
        lang_map = {
            '.py': 'python',
            '.js': 'javascript', '.jsx': 'javascript',
            '.ts': 'typescript', '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp', '.c': 'c', '.h': 'c', '.hpp': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.sql': 'sql',
            '.html': 'html', '.css': 'css',
            '.json': 'json', '.xml': 'xml',
            '.yml': 'yaml', '.yaml': 'yaml',
            '.md': 'markdown',
            '.sh': 'shell', '.bat': 'batch', '.ps1': 'powershell',
            '.toml': 'toml', '.cfg': 'config', '.ini': 'config',
            '.env': 'env',
        }
        if filename.lower() in ('dockerfile', 'makefile', '.gitignore', '.dockerignore'):
            return 'config'
        return lang_map.get(ext)

    def _parse_and_index(self, full_path: str, rel_path: str):
        """Parse AST symbols from a file and add them to the graph."""
        parsed_data = CodeParser.parse_file(full_path)
        if not parsed_data:
            return

        # Add Classes
        for cls in parsed_data.get("classes", []):
            symbol_type = "DB_TABLE" if cls.get("is_db_model") else "CLASS"
            self.twin.add_symbol_node(
                symbol_name=cls["name"],
                symbol_type=symbol_type,
                file_path=full_path,
                line_number=cls["line"],
                docstring=cls.get("docstring", "")
            )

        # Add Functions
        for fn in parsed_data.get("functions", []):
            self.twin.add_symbol_node(
                symbol_name=fn["name"],
                symbol_type="FUNCTION",
                file_path=full_path,
                line_number=fn["line"],
                docstring=fn.get("docstring", "")
            )

        # Add API Routes
        for route in parsed_data.get("routes", []):
            route_name = f"{route['method']} {route['path']}"
            self.twin.add_symbol_node(
                symbol_name=route_name,
                symbol_type="API_ROUTE",
                file_path=full_path,
                line_number=route["line"]
            )

        # Add Imports as Edges
        for imp in parsed_data.get("imports", []):
            self.twin.add_relationship(rel_path, imp, "IMPORTS")
