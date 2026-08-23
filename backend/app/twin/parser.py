import re
import ast
import os
from typing import Dict, List, Any

class CodeParser:
    """
    Multi-language AST and static code analyzer.
    Extracts functions, classes, imports, API routes, DB tables, and dependencies.
    """

    @staticmethod
    def parse_python_file(file_path: str, content: str) -> Dict[str, Any]:
        result = {
            "classes": [],
            "functions": [],
            "routes": [],
            "imports": [],
            "db_models": []
        }

        # 1. Regex search for FastAPI / Flask routes
        route_pattern = r'@(?:app|router)\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(route_pattern, content):
            method, path = match.groups()
            result["routes"].append({
                "method": method.upper(),
                "path": path,
                "line": content[:match.start()].count('\n') + 1
            })

        # 2. AST parsing for Python symbols
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        result["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        result["imports"].append(f"{module}.{alias.name}")
                elif isinstance(node, ast.ClassDef):
                    is_db_model = any(
                        isinstance(b, ast.Name) and b.id in ["Base", "Model"] or
                        isinstance(b, ast.Attribute) and b.attr in ["Model", "Base"]
                        for b in node.bases
                    )
                    class_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "docstring": ast.get_docstring(node) or "",
                        "is_db_model": is_db_model
                    }
                    result["classes"].append(class_info)
                    if is_db_model:
                        result["db_models"].append(node.name)
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    result["functions"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "docstring": ast.get_docstring(node) or ""
                    })
        except SyntaxError:
            pass  # Fallback gracefully if file has syntax errors

        return result

    @staticmethod
    def parse_javascript_file(content: str) -> Dict[str, Any]:
        result = {
            "functions": [],
            "imports": [],
            "routes": []
        }

        # Imports
        import_pattern = r'import\s+.*?from\s+["\']([^"\']+)["\']'
        for match in re.finditer(import_pattern, content):
            result["imports"].append(match.group(1))

        # Functions & Components
        fn_pattern = r'(?:function\s+([A-Za-z0-9_]+)|const\s+([A-Za-z0-9_]+)\s*=\s*(?:\([^)]*\)|[A-Za-z0-9_]+)\s*=>)'
        for match in re.finditer(fn_pattern, content):
            name = match.group(1) or match.group(2)
            if name:
                result["functions"].append({
                    "name": name,
                    "line": content[:match.start()].count('\n') + 1
                })

        # Express / API Routes
        route_pattern = r'(?:app|router)\.(get|post|put|delete)\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(route_pattern, content):
            method, path = match.groups()
            result["routes"].append({
                "method": method.upper(),
                "path": path,
                "line": content[:match.start()].count('\n') + 1
            })

        return result

    @staticmethod
    def parse_sql_file(content: str) -> Dict[str, Any]:
        tables = []
        table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_"\.]+)'
        for match in re.finditer(table_pattern, content, re.IGNORECASE):
            tables.append(match.group(1).replace('"', ''))
        return {"tables": tables}

    @classmethod
    def parse_file(cls, file_path: str) -> Dict[str, Any]:
        ext = os.path.splitext(file_path)[1].lower()
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            return {}

        if ext == '.py':
            return cls.parse_python_file(file_path, content)
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            return cls.parse_javascript_file(content)
        elif ext == '.sql':
            return cls.parse_sql_file(content)
        return {}
