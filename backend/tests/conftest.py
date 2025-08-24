import pytest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import after path modification
from config import Config
from vector_store import VectorStore
from document_processor import DocumentProcessor
from rag_system import RAGSystem

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def test_config(temp_dir):
    """Create a test configuration with temporary paths"""
    config = Config()
    config.CHROMA_PATH = os.path.join(temp_dir, "test_chroma")
    config.MAX_RESULTS = 3
    config.CHUNK_SIZE = 400  # Smaller for faster testing
    config.CHUNK_OVERLAP = 50
    return config

@pytest.fixture
def sample_course_doc(temp_dir):
    """Create a sample course document for testing"""
    doc_path = os.path.join(temp_dir, "test_course.txt")
    content = """Course Title: Test Course on Programming
Course Link: https://example.com/test-course
Course Instructor: John Smith

Lesson 1: Introduction to Python
Lesson Link: https://example.com/lesson1
Welcome to Python programming. Python is a versatile programming language.
It is widely used for web development, data science, and automation.

Lesson 2: Variables and Data Types
Lesson Link: https://example.com/lesson2
In Python, variables are used to store data. There are different data types.
Strings store text, integers store numbers, and lists store collections.

Lesson 3: Control Structures
Lesson Link: https://example.com/lesson3
Control structures help control the flow of your program.
If statements make decisions, while loops repeat actions.
"""
    
    with open(doc_path, 'w') as f:
        f.write(content)
    
    return doc_path

@pytest.fixture
def vector_store(test_config):
    """Create a test vector store"""
    return VectorStore(test_config.CHROMA_PATH, test_config.EMBEDDING_MODEL, test_config.MAX_RESULTS)

@pytest.fixture
def document_processor(test_config):
    """Create a test document processor"""
    return DocumentProcessor(test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP)

@pytest.fixture
def mock_rag_system():
    """Create a mock RAG system for API testing"""
    mock = MagicMock(spec=RAGSystem)
    mock.query.return_value = ("Test answer", ["Test source"])
    mock.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Test Course 1", "Test Course 2"]
    }
    
    # Mock session manager
    mock_session_manager = MagicMock()
    mock_session_manager.create_session.return_value = "test-session-123"
    mock_session_manager.clear_session.return_value = None
    mock.session_manager = mock_session_manager
    
    return mock

@pytest.fixture
def test_app(mock_rag_system):
    """Create a test FastAPI app without static file mounting"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional, Union
    
    # Define models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None
    
    class SourceItem(BaseModel):
        text: str
        link: Optional[str] = None
    
    class QueryResponse(BaseModel):
        answer: str
        sources: List[Union[str, SourceItem]]
        session_id: str
    
    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]
    
    # Create test app
    app = FastAPI(title="Test RAG System")
    
    # Add CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # API endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()
            
            answer, sources = mock_rag_system.query(request.query, session_id)
            
            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/api/sessions/{session_id}/clear")
    async def clear_session(session_id: str):
        try:
            mock_rag_system.session_manager.clear_session(session_id)
            return {"message": "Session cleared successfully", "session_id": session_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/")
    async def root():
        return {"message": "RAG System API"}
    
    return app

@pytest.fixture
def test_client(test_app):
    """Create a test client for synchronous testing"""
    return TestClient(test_app)

@pytest.fixture
async def async_client(test_app):
    """Create an async client for async testing"""
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
def sample_query_request():
    """Sample query request data for testing"""
    return {
        "query": "What is Python?",
        "session_id": "test-session-123"
    }

@pytest.fixture
def sample_query_response():
    """Sample expected query response for testing"""
    return {
        "answer": "Test answer",
        "sources": ["Test source"],
        "session_id": "test-session-123"
    }