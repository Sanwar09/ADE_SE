import os
import json
from typing import Dict, Any, List
from app.utils.llm import call_llm_safe
from app.twin.file_store import FileStore
from app.twin.graph_builder import RepositoryDigitalTwin


class RepositoryExplainer:
    """
    Advanced System Comprehension & Digital Twin Analysis Engine.
    Combines AST graph relationships, folder hierarchy, and Gemini LLM insights
    to thoroughly explain the codebase structure, roles of folders, tech stack,
    entry points, and potential configuration/security issues.
    """

    def __init__(self, repo_path: str, twin: RepositoryDigitalTwin, file_store: FileStore):
        self.repo_path = os.path.abspath(repo_path)
        self.twin = twin
        self.file_store = file_store

    def generate_comprehension_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive repository analysis report.
        """
        repo_name = os.path.basename(self.repo_path)
        all_paths = self.file_store.get_all_paths()

        # 1. Static analysis from the graph
        api_routes = []
        db_tables = []
        classes = []
        functions = []

        for node, data in self.twin.graph.nodes(data=True):
            node_type = data.get("node_type", "")
            if node_type == "API_ROUTE":
                api_routes.append({"name": data.get("name"), "file": data.get("file"), "line": data.get("line")})
            elif node_type == "DB_TABLE":
                db_tables.append({"name": data.get("name"), "file": data.get("file"), "line": data.get("line")})
            elif node_type == "CLASS":
                classes.append({"name": data.get("name"), "file": data.get("file")})
            elif node_type == "FUNCTION":
                functions.append({"name": data.get("name"), "file": data.get("file")})

        # 2. Tech stack & folder roles
        languages = list(self.twin.metadata.get("languages", []))
        tech_stack = self._detect_tech_stack()
        folder_roles = self._detect_folder_roles()
        important_files = self._detect_important_files()
        detected_issues = self._detect_potential_issues()

        # 3. File tree & how to run
        file_tree = self.file_store.get_file_tree()
        how_to_run = self._detect_how_to_run()

        # 4. LLM-powered deep architecture summary
        architecture_summary = self._generate_llm_summary(repo_name, file_tree, tech_stack, folder_roles)

        return {
            "repo_name": repo_name,
            "repo_path": self.repo_path,
            "architecture_summary": architecture_summary,
            "tech_stack": tech_stack,
            "languages": languages,
            "metrics": {
                "total_files": self.twin.metadata.get("total_files", len(all_paths)),
                "total_functions": self.twin.metadata.get("total_functions", len(functions)),
                "total_classes": self.twin.metadata.get("total_classes", len(classes)),
                "total_routes": self.twin.metadata.get("total_routes", len(api_routes)),
                "indexed_files": len(self.file_store.files),
            },
            "folder_roles": folder_roles,
            "important_files": important_files,
            "detected_issues": detected_issues,
            "api_routes": api_routes,
            "db_tables": db_tables,
            "file_tree": file_tree,
            "how_to_run": how_to_run,
        }

    def _detect_folder_roles(self) -> List[Dict[str, str]]:
        """Identify what each top-level and second-level folder does and why."""
        all_paths = self.file_store.get_all_paths()
        roles = []
        seen_dirs = set()

        for p in all_paths:
            normalized = p.replace("\\", "/")
            parts = normalized.split("/")
            if len(parts) > 1:
                top_dir = parts[0]
                if top_dir not in seen_dirs:
                    seen_dirs.add(top_dir)
                    role_info = self._categorize_directory(top_dir, all_paths)
                    roles.append(role_info)

        return roles

    def _categorize_directory(self, dir_name: str, all_paths: List[str]) -> Dict[str, str]:
        """Categorize directory role based on name and file contents."""
        name_lower = dir_name.lower()
        matching_files = [p for p in all_paths if p.replace("\\", "/").startswith(dir_name + "/")]
        file_count = len(matching_files)

        if name_lower in ["frontend", "client", "ui", "web", "app-client"]:
            return {
                "name": dir_name,
                "role": "Frontend User Interface",
                "description": f"Contains client-side presentation code, React/Vue/HTML components, styles, and assets ({file_count} files).",
                "badge": "Frontend",
                "color": "cyan"
            }
        elif name_lower in ["backend", "server", "api", "service", "core"]:
            return {
                "name": dir_name,
                "role": "Backend Application & API",
                "description": f"Contains server business logic, REST/GraphQL endpoints, database models, and agent orchestration ({file_count} files).",
                "badge": "Backend",
                "color": "purple"
            }
        elif name_lower in ["tests", "test", "__tests__", "spec"]:
            return {
                "name": dir_name,
                "role": "Test Suite & QA",
                "description": f"Contains unit tests, integration tests, mock data, and test fixtures ({file_count} files).",
                "badge": "Tests",
                "color": "green"
            }
        elif name_lower in ["docker", "deploy", "k8s", "kubernetes", "ci", ".github"]:
            return {
                "name": dir_name,
                "role": "DevOps & CI/CD",
                "description": f"Contains container configurations, deployment scripts, workflows, and infrastructure as code ({file_count} files).",
                "badge": "DevOps",
                "color": "orange"
            }
        elif name_lower in ["docs", "doc", "documentation"]:
            return {
                "name": dir_name,
                "role": "Documentation",
                "description": f"Contains architectural designs, user guides, API specifications, and notes ({file_count} files).",
                "badge": "Docs",
                "color": "blue"
            }
        else:
            return {
                "name": dir_name,
                "role": "Module / Utilities",
                "description": f"Contains subsystem components, helpers, or shared packages ({file_count} files).",
                "badge": "Module",
                "color": "slate"
            }

    def _detect_important_files(self) -> List[Dict[str, str]]:
        """Detect the most critical entry point and config files."""
        important = []
        all_paths = self.file_store.get_all_paths()

        targets = {
            "main.py": ("Backend Entry Point", "FastAPI / Python server entry point"),
            "app.py": ("Backend Entry Point", "Flask / FastAPI application entry point"),
            "package.json": ("Frontend Package Config", "Node.js dependencies, scripts, and build configuration"),
            "requirements.txt": ("Python Dependencies", "Lists all required Python packages for the project"),
            "dockerfile": ("Container Build Spec", "Defines the Docker image runtime and dependencies"),
            "docker-compose.yml": ("Multi-Container Setup", "Orchestrates database, backend, and frontend services"),
            "vite.config.js": ("Frontend Bundler Config", "Vite build and plugin configuration"),
            "index.html": ("Web Entry Point", "Main HTML entry point for the browser client"),
            "app.jsx": ("Main React Component", "Root React application layout and navigation"),
            ".env.example": ("Environment Template", "Template of required environment variables and API keys"),
            "readme.md": ("Project Documentation", "Overview, installation steps, and guide"),
        }

        for path in all_paths:
            base = os.path.basename(path).lower()
            if base in targets:
                role, desc = targets[base]
                important.append({
                    "path": path,
                    "name": os.path.basename(path),
                    "role": role,
                    "description": desc
                })

        return important

    def _detect_potential_issues(self) -> List[Dict[str, str]]:
        """Static inspection for common repository issues / missing files."""
        issues = []
        all_paths = self.file_store.get_all_paths()
        all_paths_lower = [p.lower() for p in all_paths]

        has_backend = any(p.endswith(".py") or p.endswith(".go") or "server" in p for p in all_paths_lower)
        has_frontend = any(p.endswith(".jsx") or p.endswith(".tsx") or p.endswith(".html") for p in all_paths_lower)

        # Check for missing .env
        if has_backend and not any(p.endswith(".env") or p.endswith(".env.example") for p in all_paths_lower):
            issues.append({
                "type": "warning",
                "title": "Missing Environment Configuration",
                "description": "No .env or .env.example file found. The application may require environment variables to run."
            })

        # Check for missing README
        if not any(p.endswith("readme.md") for p in all_paths_lower):
            issues.append({
                "type": "info",
                "title": "No README.md Found",
                "description": "Project lacks a top-level README.md explaining installation and architecture."
            })

        # Check for missing test directory
        if not any("test" in p for p in all_paths_lower):
            issues.append({
                "type": "info",
                "title": "No Test Suite Detected",
                "description": "No tests/ directory or test files detected. Automated verification will rely on syntax validation."
            })

        # Check for hardcoded secrets or placeholders
        for path in all_paths:
            if path.endswith((".py", ".js", ".ts", ".json")):
                content = self.file_store.get_file(path) or ""
                if "your_api_key_here" in content or "your_secret_here" in content:
                    issues.append({
                        "type": "warning",
                        "title": f"Placeholder Secrets in {path}",
                        "description": "Placeholder API key or secret token detected in source code."
                    })
                    break

        return issues

    def _detect_tech_stack(self) -> List[str]:
        """Detect tech stack from file extensions and key files."""
        tech_stack = []
        all_paths = self.file_store.get_all_paths()

        if any(p.endswith(".py") for p in all_paths):
            key_files_content = " ".join(
                self.file_store.get_file(p) or "" for p in all_paths if p.endswith(".py")
            )[:10000].lower()
            if "fastapi" in key_files_content:
                tech_stack.append("Python FastAPI")
            elif "flask" in key_files_content:
                tech_stack.append("Python Flask")
            elif "django" in key_files_content:
                tech_stack.append("Python Django")
            else:
                tech_stack.append("Python")

        if any(p.endswith((".js", ".ts")) for p in all_paths):
            pkg_json = (self.file_store.get_file("package.json") or "").lower()
            if "express" in pkg_json:
                tech_stack.append("Node.js Express")
            elif "next" in pkg_json:
                tech_stack.append("Next.js")
            else:
                tech_stack.append("JavaScript / TypeScript")

        if any(p.endswith((".jsx", ".tsx")) for p in all_paths):
            tech_stack.append("React")
        if any(p.endswith(".vue") for p in all_paths):
            tech_stack.append("Vue.js")

        if any("sql" in p.lower() for p in all_paths):
            tech_stack.append("SQL Database")

        if any("dockerfile" in p.lower() or "docker-compose" in p.lower() for p in all_paths):
            tech_stack.append("Docker")

        if any(".github" in p for p in all_paths):
            tech_stack.append("GitHub Actions CI/CD")

        if not tech_stack:
            tech_stack.append("Custom Software Project")

        return list(dict.fromkeys(tech_stack))

    def _detect_how_to_run(self) -> List[str]:
        """Detect how to run the project from its files."""
        how_to_run = []
        all_paths = self.file_store.get_all_paths()

        # Python
        if any("requirements.txt" in p for p in all_paths):
            how_to_run.append("pip install -r requirements.txt")
        for p in all_paths:
            if p.endswith("main.py") or p.endswith("app.py"):
                content = (self.file_store.get_file(p) or "").lower()
                if "fastapi" in content or "uvicorn" in content:
                    clean_path = p.replace("\\", "/").replace(".py", "").replace("/", ".")
                    how_to_run.append(f"uvicorn {clean_path}:app --reload --port 8000")
                    break

        # Node.js
        if any("package.json" in p for p in all_paths):
            how_to_run.append("npm install && npm run dev")

        # Docker
        if any("docker-compose" in p.lower() for p in all_paths):
            how_to_run.append("docker-compose up --build")
        elif any("dockerfile" in p.lower() for p in all_paths):
            how_to_run.append("docker build -t app . && docker run -p 8000:8000 app")

        if not how_to_run:
            how_to_run.append("Review project README.md for setup instructions")

        return how_to_run

    def _generate_llm_summary(
        self,
        repo_name: str,
        file_tree: str,
        tech_stack: List[str],
        folder_roles: List[Dict[str, str]]
    ) -> str:
        """Use Gemini to generate a rich architecture and domain analysis."""
        key_files = self.file_store.get_key_files()
        key_files_text = ""
        for path, content in list(key_files.items())[:6]:
            key_files_text += f"\n--- {path} ---\n{content[:2500]}\n"

        roles_text = "\n".join(f"- {r['name']}: {r['role']} — {r['description']}" for r in folder_roles)

        prompt = f"""You are an elite Software Engineering Architect. Analyze this codebase and provide a comprehensive architecture walkthrough.

Project Name: {repo_name}
Tech Stack: {', '.join(tech_stack)}

Folder Breakdown:
{roles_text}

Project Structure:
{file_tree[:2500]}

Key Files Snippets:
{key_files_text}

Provide a well-structured analysis:
1. **Core Purpose & Domain**: What does this system do and who is it for?
2. **Architecture & Directory Structure**: Why is the code organized this way (e.g. separation of frontend UI, backend API, configuration)?
3. **Data Flow & Communication**: How do components communicate (HTTP APIs, state management, DB)?
4. **Key Entry Points**: Which files start the frontend and backend services?
5. **Software Engineering Assessment**: Highlight patterns used (modularity, error handling, extensibility).

Write in crisp markdown."""

        system_instruction = (
            "You are an expert software architect providing clear, professional codebase analysis. "
            "Explain the codebase clearly so a developer can immediately understand how the project works and where to add new features."
        )

        return call_llm_safe(prompt, system_instruction=system_instruction, max_tokens=4096)
