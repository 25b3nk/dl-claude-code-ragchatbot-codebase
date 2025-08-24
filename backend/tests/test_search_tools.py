import pytest
from models import Course, CourseChunk, Lesson
from search_tools import CourseOutlineTool, CourseSearchTool, ToolManager


class TestCourseSearchTool:
    """Test CourseSearchTool functionality"""

    def test_tool_initialization(self, vector_store):
        """Test that CourseSearchTool initializes correctly"""
        tool = CourseSearchTool(vector_store)

        assert tool is not None
        assert tool.store == vector_store
        assert tool.last_sources == []

    def test_get_tool_definition(self, vector_store):
        """Test tool definition for Anthropic API"""
        tool = CourseSearchTool(vector_store)
        definition = tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["required"] == ["query"]

        properties = definition["input_schema"]["properties"]
        assert "query" in properties
        assert "course_name" in properties
        assert "lesson_number" in properties

    def test_execute_basic_search(self, vector_store):
        """Test basic search execution"""
        # Setup test data
        course = Course(title="Python Programming", lessons=[])
        vector_store.add_course_metadata(course)

        chunk = CourseChunk(
            content="Python is a versatile programming language used for many applications.",
            course_title="Python Programming",
            lesson_number=1,
            chunk_index=0,
        )
        vector_store.add_course_content([chunk])

        # Test the tool
        tool = CourseSearchTool(vector_store)
        result = tool.execute("Python programming")

        assert isinstance(result, str)
        assert "Python" in result
        assert "[Python Programming - Lesson 1]" in result

    def test_execute_with_course_filter(self, vector_store):
        """Test search with course name filter"""
        # Setup test data with multiple courses
        course1 = Course(title="Python Basics", lessons=[])
        course2 = Course(title="JavaScript Fundamentals", lessons=[])
        vector_store.add_course_metadata(course1)
        vector_store.add_course_metadata(course2)

        chunks = [
            CourseChunk(
                content="Python variables and data types",
                course_title="Python Basics",
                lesson_number=1,
                chunk_index=0,
            ),
            CourseChunk(
                content="JavaScript variables and scope",
                course_title="JavaScript Fundamentals",
                lesson_number=1,
                chunk_index=1,
            ),
        ]
        vector_store.add_course_content(chunks)

        # Test filtered search
        tool = CourseSearchTool(vector_store)
        result = tool.execute("variables", course_name="Python Basics")

        assert "Python" in result
        assert "JavaScript" not in result

    def test_execute_with_lesson_filter(self, vector_store):
        """Test search with lesson number filter"""
        course = Course(title="Programming Course", lessons=[])
        vector_store.add_course_metadata(course)

        chunks = [
            CourseChunk(
                content="Introduction to programming concepts",
                course_title="Programming Course",
                lesson_number=1,
                chunk_index=0,
            ),
            CourseChunk(
                content="Advanced programming techniques",
                course_title="Programming Course",
                lesson_number=2,
                chunk_index=1,
            ),
        ]
        vector_store.add_course_content(chunks)

        # Test lesson-filtered search
        tool = CourseSearchTool(vector_store)
        result = tool.execute("programming", lesson_number=2)

        assert "Advanced" in result
        assert "Introduction" not in result

    def test_execute_no_results(self, vector_store):
        """Test search with no matching results"""
        tool = CourseSearchTool(vector_store)
        result = tool.execute("nonexistent topic")

        assert "No relevant content found" in result

    def test_execute_nonexistent_course(self, vector_store):
        """Test search with nonexistent course name"""
        tool = CourseSearchTool(vector_store)
        result = tool.execute("anything", course_name="Nonexistent Course")

        assert "No course found matching" in result or result.startswith(
            "No course found"
        )

    def test_sources_tracking(self, vector_store):
        """Test that sources are tracked correctly"""
        # Setup test data
        course = Course(
            title="Test Course",
            lessons=[
                Lesson(
                    lesson_number=1,
                    title="Lesson 1",
                    lesson_link="https://example.com/1",
                )
            ],
        )
        vector_store.add_course_metadata(course)

        chunk = CourseChunk(
            content="Test content for tracking sources",
            course_title="Test Course",
            lesson_number=1,
            chunk_index=0,
        )
        vector_store.add_course_content([chunk])

        # Execute search
        tool = CourseSearchTool(vector_store)
        result = tool.execute("test content")

        # Check sources
        assert len(tool.last_sources) > 0
        source = tool.last_sources[0]
        assert "text" in source
        assert "link" in source
        assert "Test Course - Lesson 1" in source["text"]


class TestCourseOutlineTool:
    """Test CourseOutlineTool functionality"""

    def test_tool_initialization(self, vector_store):
        """Test that CourseOutlineTool initializes correctly"""
        tool = CourseOutlineTool(vector_store)

        assert tool is not None
        assert tool.store == vector_store

    def test_get_tool_definition(self, vector_store):
        """Test tool definition for Anthropic API"""
        tool = CourseOutlineTool(vector_store)
        definition = tool.get_tool_definition()

        assert definition["name"] == "get_course_outline"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["required"] == ["course_name"]

        properties = definition["input_schema"]["properties"]
        assert "course_name" in properties

    def test_execute_course_outline(self, vector_store):
        """Test getting course outline"""
        # Setup test course with lessons
        course = Course(
            title="Complete Programming Course",
            course_link="https://example.com/course",
            instructor="Jane Doe",
            lessons=[
                Lesson(
                    lesson_number=1,
                    title="Introduction",
                    lesson_link="https://example.com/1",
                ),
                Lesson(
                    lesson_number=2,
                    title="Variables",
                    lesson_link="https://example.com/2",
                ),
                Lesson(
                    lesson_number=3,
                    title="Functions",
                    lesson_link="https://example.com/3",
                ),
            ],
        )
        vector_store.add_course_metadata(course)

        # Test the tool
        tool = CourseOutlineTool(vector_store)
        result = tool.execute("Complete Programming Course")

        assert "Complete Programming Course" in result
        assert "Jane Doe" in result
        assert "https://example.com/course" in result
        assert "1. Introduction" in result
        assert "2. Variables" in result
        assert "3. Functions" in result

    def test_execute_partial_course_name(self, vector_store):
        """Test getting outline with partial course name"""
        course = Course(
            title="Machine Learning with Python",
            lessons=[
                Lesson(
                    lesson_number=1, title="Intro", lesson_link="https://example.com/1"
                )
            ],
        )
        vector_store.add_course_metadata(course)

        tool = CourseOutlineTool(vector_store)
        result = tool.execute("Machine Learning")

        assert "Machine Learning with Python" in result
        assert "1. Intro" in result

    def test_execute_nonexistent_course(self, vector_store):
        """Test getting outline for nonexistent course"""
        tool = CourseOutlineTool(vector_store)
        result = tool.execute("Nonexistent Course")

        assert "No course found matching" in result


class TestToolManager:
    """Test ToolManager functionality"""

    def test_tool_manager_initialization(self):
        """Test ToolManager initialization"""
        manager = ToolManager()

        assert manager is not None
        assert manager.tools == {}

    def test_register_tool(self, vector_store):
        """Test registering tools"""
        manager = ToolManager()
        search_tool = CourseSearchTool(vector_store)

        manager.register_tool(search_tool)

        assert "search_course_content" in manager.tools
        assert manager.tools["search_course_content"] == search_tool

    def test_get_tool_definitions(self, vector_store):
        """Test getting tool definitions for API"""
        manager = ToolManager()
        search_tool = CourseSearchTool(vector_store)
        outline_tool = CourseOutlineTool(vector_store)

        manager.register_tool(search_tool)
        manager.register_tool(outline_tool)

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 2
        names = [d["name"] for d in definitions]
        assert "search_course_content" in names
        assert "get_course_outline" in names

    def test_execute_tool(self, vector_store):
        """Test executing tools through manager"""
        # Setup test data
        course = Course(title="Test Course", lessons=[])
        vector_store.add_course_metadata(course)

        chunk = CourseChunk(
            content="Test content for manager execution",
            course_title="Test Course",
            lesson_number=1,
            chunk_index=0,
        )
        vector_store.add_course_content([chunk])

        # Setup manager
        manager = ToolManager()
        search_tool = CourseSearchTool(vector_store)
        manager.register_tool(search_tool)

        # Execute tool through manager
        result = manager.execute_tool("search_course_content", query="test content")

        assert isinstance(result, str)
        assert "Test Course" in result

    def test_execute_nonexistent_tool(self, vector_store):
        """Test executing nonexistent tool"""
        manager = ToolManager()

        result = manager.execute_tool("nonexistent_tool", query="test")

        assert "Tool 'nonexistent_tool' not found" in result

    def test_get_last_sources(self, vector_store):
        """Test getting sources from tools"""
        # Setup with test data that will generate sources
        course = Course(
            title="Source Test Course",
            lessons=[
                Lesson(
                    lesson_number=1,
                    title="Test Lesson",
                    lesson_link="https://example.com/1",
                )
            ],
        )
        vector_store.add_course_metadata(course)

        chunk = CourseChunk(
            content="Content for source testing",
            course_title="Source Test Course",
            lesson_number=1,
            chunk_index=0,
        )
        vector_store.add_course_content([chunk])

        # Setup manager and execute search
        manager = ToolManager()
        search_tool = CourseSearchTool(vector_store)
        manager.register_tool(search_tool)

        # Execute search to generate sources
        manager.execute_tool("search_course_content", query="content")

        # Get sources
        sources = manager.get_last_sources()
        assert len(sources) > 0
        assert "text" in sources[0]
        assert "link" in sources[0]

    def test_reset_sources(self, vector_store):
        """Test resetting sources"""
        # Setup and generate sources first
        course = Course(title="Reset Test Course", lessons=[])
        vector_store.add_course_metadata(course)

        chunk = CourseChunk(
            content="Content for reset testing",
            course_title="Reset Test Course",
            lesson_number=1,
            chunk_index=0,
        )
        vector_store.add_course_content([chunk])

        manager = ToolManager()
        search_tool = CourseSearchTool(vector_store)
        manager.register_tool(search_tool)

        # Generate sources
        manager.execute_tool("search_course_content", query="content")
        assert len(manager.get_last_sources()) > 0

        # Reset sources
        manager.reset_sources()
        assert len(manager.get_last_sources()) == 0
