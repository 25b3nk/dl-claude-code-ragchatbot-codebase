import pytest
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import after path modification
from config import Config
from vector_store import VectorStore
from document_processor import DocumentProcessor

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