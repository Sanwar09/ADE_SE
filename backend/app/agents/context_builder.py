import os
from typing import List, Dict, Optional, Any
from app.twin.file_store import FileStore
from app.twin.graph_builder import RepositoryDigitalTwin


class ContextBuilder:
    """
    Builds rich context for each agent by querying the FileStore and Digital Twin.
    This is what makes agents AWARE of the actual codebase.
    
    The key insight: every LLM call needs REAL file contents to generate
    code that actually fits the project.
    """

    def __init__(self, file_store: FileStore, twin: RepositoryDigitalTwin):
        self.file_store = file_store
        self.twin = twin

    def build_task_context(self, task_prompt: str, max_files: int = 15) -> str:
        """
        Build comprehensive context for a task:
        1. File tree of entire project
        2. Key project files (README, configs)
        3. Semantic search results for the task
        
        Returns a formatted string ready to be sent to the LLM.
        """
        sections = []

        # 1. Project file tree
        tree = self.file_store.get_file_tree()
        sections.append(f"=== PROJECT FILE TREE ===\n{tree}")

        # 2. Key project files
        key_files = self.file_store.get_key_files()
        if key_files:
            key_section = "=== KEY PROJECT FILES ==="
            for path, content in list(key_files.items())[:5]:
                key_section += f"\n\n--- {path} ---\n{content[:4000]}"
            sections.append(key_section)

        # 3. Semantic search results relevant to the task
        search_results = self.file_store.search(task_prompt, top_k=max_files)
        if search_results:
            search_section = "=== RELEVANT CODE (Semantic Search) ==="
            seen_paths = set()
            for res in search_results:
                path = res['path']
                if path not in seen_paths:
                    seen_paths.add(path)
                    # Get the FULL file content, not just the chunk
                    full_content = self.file_store.get_file(path)
                    if full_content:
                        search_section += f"\n\n--- {path} ---\n{full_content[:6000]}"
            sections.append(search_section)

        # 4. Graph metadata
        meta = self.twin.metadata
        meta_section = (
            f"=== PROJECT METRICS ===\n"
            f"Total Files: {meta.get('total_files', 0)}\n"
            f"Total Functions: {meta.get('total_functions', 0)}\n"
            f"Total Classes: {meta.get('total_classes', 0)}\n"
            f"Total API Routes: {meta.get('total_routes', 0)}\n"
            f"Languages: {', '.join(meta.get('languages', []))}"
        )
        sections.append(meta_section)

        return "\n\n".join(sections)

    def get_architect_context(self, task_prompt: str) -> str:
        """
        Extended context for architect: file tree + all key files + relevant code.
        The architect needs to understand the FULL project structure to decide
        which files to create/modify.
        """
        context = self.build_task_context(task_prompt, max_files=20)

        # Add API route information from the graph
        api_routes = []
        for node, data in self.twin.graph.nodes(data=True):
            if data.get("node_type") == "API_ROUTE":
                api_routes.append(f"  {data.get('name', node)} → {data.get('file', 'unknown')}")

        if api_routes:
            context += "\n\n=== EXISTING API ROUTES ===\n" + "\n".join(api_routes)

        return context

    def get_developer_context(
        self,
        task_prompt: str,
        files_to_modify: List[str],
        files_to_create: List[str]
    ) -> str:
        """
        Developer context: FULL contents of files to modify + related files.
        This is THE MOST CRITICAL context builder - the developer MUST see
        the complete contents of every file it needs to change.
        """
        sections = [f"=== TASK ===\n{task_prompt}"]

        # 1. FULL contents of every file to modify
        if files_to_modify:
            modify_section = "=== FILES TO MODIFY (FULL CONTENTS - Generate complete updated versions) ==="
            for path in files_to_modify:
                content = self.file_store.get_file(path)
                if content:
                    modify_section += f"\n\n--- {path} ---\n{content}"
                else:
                    # Try with different separators
                    normalized = path.replace("/", os.sep).replace("\\", os.sep)
                    content = self.file_store.get_file(normalized)
                    if content:
                        modify_section += f"\n\n--- {path} ---\n{content}"
                    else:
                        modify_section += f"\n\n--- {path} ---\n[FILE NOT FOUND IN INDEX]"
            sections.append(modify_section)

        # 2. New files to create - provide related files as style reference
        if files_to_create:
            create_section = "=== FILES TO CREATE ==="
            for path in files_to_create:
                create_section += f"\n- {path}"

            # Find related existing files for style reference
            for path in files_to_create:
                ext = os.path.splitext(path)[1]
                if ext:
                    similar_files = self.file_store.get_files_by_extension(ext)
                    if similar_files:
                        create_section += f"\n\n--- Style Reference (existing {ext} files) ---"
                        for ref_path, ref_content in list(similar_files.items())[:3]:
                            create_section += f"\n\n--- {ref_path} ---\n{ref_content[:4000]}"
                        break
            sections.append(create_section)

        # 3. Project file tree for context
        tree = self.file_store.get_file_tree()
        sections.append(f"=== PROJECT FILE TREE ===\n{tree}")

        return "\n\n".join(sections)

    def get_reviewer_context(
        self,
        original_files: Dict[str, str],
        modified_files: Dict[str, str]
    ) -> str:
        """
        Reviewer context: original code vs modified code side by side.
        Allows the reviewer to check for regressions and style issues.
        """
        sections = ["=== CODE REVIEW: ORIGINAL vs MODIFIED ==="]

        for path, modified_content in modified_files.items():
            original_content = original_files.get(path, "[NEW FILE - No original]")
            section = f"\n\n--- {path} ---\n"
            section += f"\n>> ORIGINAL:\n{original_content[:5000]}\n"
            section += f"\n>> MODIFIED:\n{modified_content[:5000]}\n"
            sections.append(section)

        return "\n".join(sections)

    def get_security_context(self, architecture_plan: Dict[str, Any]) -> str:
        """
        Security context: architecture plan + any auth/security related files.
        """
        sections = [f"=== ARCHITECTURE PLAN TO REVIEW ===\n{architecture_plan.get('summary', '')}"]

        # Search for security-related files
        security_results = self.file_store.search("authentication security login password token", top_k=5)
        if security_results:
            sec_section = "=== EXISTING SECURITY-RELATED CODE ==="
            seen = set()
            for res in security_results:
                if res['path'] not in seen:
                    seen.add(res['path'])
                    content = self.file_store.get_file(res['path'])
                    if content:
                        sec_section += f"\n\n--- {res['path']} ---\n{content[:3000]}"
            sections.append(sec_section)

        return "\n\n".join(sections)
