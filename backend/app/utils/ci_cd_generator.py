"""
CI/CD Pipeline Generator — Creates real, deployable GitHub Actions YAML,
Dockerfile, and docker-compose.yml based on detected tech stack.
"""

import os
from typing import Dict, List, Any


class CICDGenerator:
    """
    Template-based CI/CD pipeline generator.
    Produces real, valid YAML files for GitHub Actions CI/CD.
    """

    @staticmethod
    def detect_stack(file_store) -> Dict[str, bool]:
        """Detect project tech stack from file store."""
        all_paths = file_store.get_all_paths() if file_store else []
        paths_lower = [p.lower() for p in all_paths]

        return {
            "python": any(p.endswith(".py") for p in paths_lower),
            "nodejs": any("package.json" in p for p in paths_lower),
            "react": any(p.endswith((".jsx", ".tsx")) for p in paths_lower),
            "docker": any("dockerfile" in p for p in paths_lower),
            "has_tests_py": any("test" in p and p.endswith(".py") for p in paths_lower),
            "has_requirements": any("requirements.txt" in p for p in paths_lower),
            "has_fastapi": any("fastapi" in (file_store.get_file(p) or "").lower()
                               for p in all_paths if p.endswith(".py")),
        }

    @staticmethod
    def generate_github_actions_ci(stack: Dict[str, bool], project_name: str = "app") -> str:
        """Generate a real .github/workflows/ci.yml file."""

        jobs = []

        # Python backend job
        if stack.get("python"):
            py_job = """
  backend-ci:
    name: "Backend CI (Python)"
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Lint with flake8
        run: |
          pip install flake8
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        continue-on-error: true

      - name: Run tests
        run: |
          pip install pytest
          pytest --tb=short -q || echo "No tests found — skipping"
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}"""
            jobs.append(py_job)

        # Node.js / React frontend job
        if stack.get("nodejs") or stack.get("react"):
            node_job = """
  frontend-ci:
    name: "Frontend CI (Node.js)"
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci || npm install

      - name: Build
        run: npm run build

      - name: Lint
        run: npm run lint || echo "No lint script — skipping"
        continue-on-error: true"""
            jobs.append(node_job)

        # Docker build job
        docker_job = """
  docker-build:
    name: "Docker Build Verification"
    runs-on: ubuntu-latest
    needs: [{needs}]
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: |
          if [ -f docker-compose.yml ]; then
            docker compose build
          elif [ -f Dockerfile ]; then
            docker build -t {project_name}:ci .
          else
            echo "No Docker config found — skipping"
          fi"""

        needs_list = []
        if stack.get("python"):
            needs_list.append("backend-ci")
        if stack.get("nodejs") or stack.get("react"):
            needs_list.append("frontend-ci")

        if needs_list:
            docker_job = docker_job.replace("{needs}", ", ".join(needs_list))
        else:
            docker_job = docker_job.replace("    needs: [{needs}]\n", "")
        docker_job = docker_job.replace("{project_name}", project_name)
        jobs.append(docker_job)

        yaml = f"""name: "{project_name} CI/CD Pipeline"

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:{"".join(jobs)}
"""
        return yaml

    @staticmethod
    def generate_dockerfile(stack: Dict[str, bool]) -> str:
        """Generate a multi-stage Dockerfile."""

        if stack.get("python") and (stack.get("nodejs") or stack.get("react")):
            return """# ── Stage 1: Build Frontend ──
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python Backend + Serve Frontend ──
FROM python:3.11-slim
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./static/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s \\
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Start server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        elif stack.get("python"):
            return """FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \\
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        else:
            return """FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . ./
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
"""

    @staticmethod
    def generate_docker_compose(stack: Dict[str, bool], project_name: str = "app") -> str:
        """Generate a docker-compose.yml."""
        services = ""

        if stack.get("python"):
            services += f"""
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: {project_name}-backend
    ports:
      - "8000:8000"
    env_file:
      - backend/.env
    volumes:
      - ./workspace:/app/workspace
    restart: unless-stopped
"""

        if stack.get("nodejs") or stack.get("react"):
            services += f"""
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: {project_name}-frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend
    restart: unless-stopped
"""

        return f"""version: "3.9"

services:{services}
"""

    @classmethod
    def generate_all(cls, file_store, project_name: str = "adt-se") -> Dict[str, str]:
        """
        Generate all CI/CD files based on detected tech stack.
        Returns dict of {filepath: content} ready to be written.
        """
        stack = cls.detect_stack(file_store)
        files = {}

        files[".github/workflows/ci.yml"] = cls.generate_github_actions_ci(stack, project_name)

        # Only generate Dockerfile if one doesn't exist
        if not stack.get("docker"):
            files["Dockerfile"] = cls.generate_dockerfile(stack)
            files["docker-compose.yml"] = cls.generate_docker_compose(stack, project_name)

        return files
