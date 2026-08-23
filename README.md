# Agentic Digital Twin for Software Engineering (ADT-SE)

> **A Multi-Agent AI Framework for Autonomous Understanding, Testing, and Evolution of Software Repositories**

---

## 📌 Project Overview

**ADT-SE** creates a continuously synchronized **Cognitive Digital Twin** of a software repository (Source Code, AST Call Graphs, APIs, Database Schemas, Docker, and CI/CD pipelines). 

Operating over this Digital Twin is a **7-Agent Society** modeling the full Software Development Life Cycle (SDLC):

1. **Product Manager Agent**: Requirement Specification & User Story Creation.
2. **Architect Agent**: Digital Twin Impact Analysis & System Blueprinting.
3. **Security Engineer Agent**: SAST Security Scans, Secrets Audit & Vulnerability Checks.
4. **Developer Agent**: Code Modifications & AST Diffs.
5. **Tester Agent**: Sandboxed Docker Test Execution (`pytest`/`jest`) & Self-Healing Feedback.
6. **Reviewer Agent**: Code Quality, Style & AST Complexity Audit.
7. **DevOps Engineer Agent**: CI/CD Pipelines, Environment Secrets & Twin Graph Sync.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, FastAPI, LangGraph, Tree-sitter, NetworkX, ChromaDB, Docker Python SDK
- **AI Intelligence**: Google Gemini API (`gemini-2.5-flash` / `gemini-1.5-flash`)
- **Frontend**: React + Vite, TailwindCSS, Cytoscape.js / React Flow

---

## ⚡ Quick Start

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# Install dependencies:
pip install -r requirements.txt
# Copy environment configuration:
cp .env.example .env
# Start FastAPI backend:
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` to launch the **ADT-SE Dashboard**!
