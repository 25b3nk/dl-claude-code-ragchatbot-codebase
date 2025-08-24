import os

import pytest
from document_processor import DocumentProcessor
from models import Course, CourseChunk, Lesson
from vector_store import SearchResults, VectorStore


class TestVectorStore:
    """Test vector store document loading and ChromaDB operations"""

    def test_vector_store_initialization(self, test_config):
        """Test that VectorStore initializes correctly"""
        store = VectorStore(
            test_config.CHROMA_PATH,
            test_config.EMBEDDING_MODEL,
            test_config.MAX_RESULTS,
        )

        assert store is not None
        assert store.max_results == test_config.MAX_RESULTS
        assert store.client is not None
        assert store.course_catalog is not None
        assert store.course_content is not None

    def test_add_course_metadata(self, vector_store):
        """Test adding course metadata to catalog"""
        course = Course(
            title="Test Course",
            course_link="https://example.com",
            instructor="Test Instructor",
            lessons=[
                Lesson(
                    lesson_number=1,
                    title="Lesson 1",
                    lesson_link="https://example.com/1",
                ),
                Lesson(
                    lesson_number=2,
                    title="Lesson 2",
                    lesson_link="https://example.com/2",
                ),
            ],
        )

        # Should not raise an exception
        vector_store.add_course_metadata(course)

        # Verify course was added
        titles = vector_store.get_existing_course_titles()
        assert "Test Course" in titles
        assert vector_store.get_course_count() == 1

    def test_add_course_content(self, vector_store):
        """Test adding course content chunks"""
        chunks = [
            CourseChunk(
                content="This is a test chunk about Python programming.",
                course_title="Test Course",
                lesson_number=1,
                chunk_index=0,
            ),
            CourseChunk(
                content="This is another chunk about variables and functions.",
                course_title="Test Course",
                lesson_number=2,
                chunk_index=1,
            ),
        ]

        # Should not raise an exception
        vector_store.add_course_content(chunks)

        # Try to search for the content
        results = vector_store.search("Python programming")
        assert not results.is_empty()
        assert len(results.documents) > 0

    def test_search_basic(self, vector_store):
        """Test basic search functionality"""
        # Add some test content first
        course = Course(title="Programming Course", lessons=[])
        vector_store.add_course_metadata(course)

        chunks = [
            CourseChunk(
                content="Python is a programming language used for web development.",
                course_title="Programming Course",
                lesson_number=1,
                chunk_index=0,
            ),
            CourseChunk(
                content="JavaScript is used for frontend web development.",
                course_title="Programming Course",
                lesson_number=2,
                chunk_index=1,
            ),
        ]
        vector_store.add_course_content(chunks)

        # Test search
        results = vector_store.search("Python programming")
        assert not results.is_empty()
        assert len(results.documents) > 0
        assert "Python" in results.documents[0]

    def test_search_with_course_filter(self, vector_store):
        """Test search with course name filtering"""
        # Add two different courses
        course1 = Course(title="Python Course", lessons=[])
        course2 = Course(title="JavaScript Course", lessons=[])
        vector_store.add_course_metadata(course1)
        vector_store.add_course_metadata(course2)

        chunks = [
            CourseChunk(
                content="Python basics and syntax",
                course_title="Python Course",
                lesson_number=1,
                chunk_index=0,
            ),
            CourseChunk(
                content="JavaScript basics and DOM manipulation",
                course_title="JavaScript Course",
                lesson_number=1,
                chunk_index=1,
            ),
        ]
        vector_store.add_course_content(chunks)

        # Test filtered search
        results = vector_store.search("basics", course_name="Python Course")
        assert not results.is_empty()
        assert all("Python" in doc for doc in results.documents)

    def test_search_with_lesson_filter(self, vector_store):
        """Test search with lesson number filtering"""
        course = Course(title="Test Course", lessons=[])
        vector_store.add_course_metadata(course)

        chunks = [
            CourseChunk(
                content="Lesson 1 content about variables",
                course_title="Test Course",
                lesson_number=1,
                chunk_index=0,
            ),
            CourseChunk(
                content="Lesson 2 content about functions",
                course_title="Test Course",
                lesson_number=2,
                chunk_index=1,
            ),
        ]
        vector_store.add_course_content(chunks)

        # Test lesson-filtered search
        results = vector_store.search(
            "content", course_name="Test Course", lesson_number=2
        )
        assert not results.is_empty()
        assert all("functions" in doc for doc in results.documents)

    def test_search_nonexistent_course(self, vector_store):
        """Test search with nonexistent course name"""
        results = vector_store.search("anything", course_name="Nonexistent Course")
        assert results.error is not None
        assert "No course found" in results.error

    def test_document_processing_integration(
        self, document_processor, vector_store, sample_course_doc
    ):
        """Test integration between document processor and vector store"""
        # Process the sample document
        course, chunks = document_processor.process_course_document(sample_course_doc)

        assert course is not None
        assert course.title == "Test Course on Programming"
        assert len(chunks) > 0

        # Add to vector store
        vector_store.add_course_metadata(course)
        vector_store.add_course_content(chunks)

        # Test search
        results = vector_store.search("Python programming")
        assert not results.is_empty()
        assert len(results.documents) > 0

    def test_course_resolution(self, vector_store):
        """Test course name resolution with partial matches"""
        # Add a course with a specific name
        course = Course(title="Machine Learning with Python", lessons=[])
        vector_store.add_course_metadata(course)

        # Test that partial course name resolves correctly
        resolved = vector_store._resolve_course_name("Machine Learning")
        assert resolved == "Machine Learning with Python"

        resolved = vector_store._resolve_course_name("Python")
        assert resolved == "Machine Learning with Python"

    def test_get_lesson_link(self, vector_store):
        """Test getting lesson links"""
        course = Course(
            title="Test Course",
            lessons=[
                Lesson(
                    lesson_number=1, title="Intro", lesson_link="https://example.com/1"
                ),
                Lesson(
                    lesson_number=2,
                    title="Advanced",
                    lesson_link="https://example.com/2",
                ),
            ],
        )
        vector_store.add_course_metadata(course)

        link = vector_store.get_lesson_link("Test Course", 1)
        assert link == "https://example.com/1"

        link = vector_store.get_lesson_link("Test Course", 2)
        assert link == "https://example.com/2"

        # Test nonexistent lesson
        link = vector_store.get_lesson_link("Test Course", 99)
        assert link is None

    def test_clear_all_data(self, vector_store):
        """Test clearing all data from vector store"""
        # Add some data
        course = Course(title="Test Course", lessons=[])
        vector_store.add_course_metadata(course)

        chunk = CourseChunk(
            content="Test content",
            course_title="Test Course",
            lesson_number=1,
            chunk_index=0,
        )
        vector_store.add_course_content([chunk])

        # Verify data exists
        assert vector_store.get_course_count() > 0

        # Clear data
        vector_store.clear_all_data()

        # Verify data is cleared
        assert vector_store.get_course_count() == 0
