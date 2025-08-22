# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Create environment file (required)
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Running the Application
```bash
# Quick start (recommended)
chmod +x run.sh
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

### Development
```bash
# Server runs on http://localhost:8000 (serves both API and frontend)
# API docs available at http://localhost:8000/docs

# Add new packages (use uv, not pip)
uv add package-name
```

## Architecture Overview

This is a RAG (Retrieval-Augmented Generation) chatbot system that answers questions about course materials using semantic search and Claude AI.

### Core Flow
1. **Frontend** (`frontend/`) - Simple HTML/CSS/JS interface
2. **FastAPI Backend** (`backend/app.py`) - API endpoints and static file serving  
3. **RAG System** (`backend/rag_system.py`) - Main orchestrator
4. **AI Generator** (`backend/ai_generator.py`) - Claude API integration with tool calling
5. **Search Tools** (`backend/search_tools.py`) - Semantic search via tool interface
6. **Vector Store** (`backend/vector_store.py`) - ChromaDB for embeddings

### Key Architectural Patterns

**Tool-Based Search**: The system uses Claude's tool calling feature. The AI decides when to search course materials via `CourseSearchTool`, rather than always performing retrieval.

**Session Management**: Conversations are tracked via `SessionManager` with configurable history limits (default 2 exchanges).

**Document Processing Pipeline**: 
- Course documents (`docs/`) → `DocumentProcessor` → Text chunks → `VectorStore` (ChromaDB)
- Documents are processed into chunks (800 chars, 100 overlap) with course/lesson metadata

**Unified Search Interface**: `VectorStore.search()` supports both semantic similarity and metadata filtering (course name, lesson number).

### Configuration

All settings centralized in `backend/config.py`:
- `ANTHROPIC_MODEL`: "claude-sonnet-4-20250514" 
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2"
- `CHUNK_SIZE`: 800 characters
- `CHROMA_PATH`: "./chroma_db" (ChromaDB storage)

### API Endpoints

- `POST /api/query` - Main chat endpoint (requires `query`, optional `session_id`)
- `GET /api/courses` - Course statistics and titles
- `/` - Serves frontend static files

### Document Structure Expected

Course documents should be in `docs/` folder as `.txt`, `.pdf`, or `.docx` files. The system extracts course titles and lesson numbers from document structure.

### Dependencies

- **FastAPI + Uvicorn** - Web server
- **ChromaDB** - Vector database  
- **Anthropic** - Claude AI API
- **sentence-transformers** - Text embeddings
- **uv** - Python package manager