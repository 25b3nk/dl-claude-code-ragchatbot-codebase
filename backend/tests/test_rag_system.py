import pytest
import os
from unittest.mock import Mock, patch
from rag_system import RAGSystem
from models import Course, Lesson


class TestRAGSystem:
    """Test end-to-end RAG system integration"""
    
    def test_initialization(self, test_config):
        """Test RAG system initialization"""
        rag = RAGSystem(test_config)
        
        assert rag is not None
        assert rag.config == test_config
        assert rag.document_processor is not None
        assert rag.vector_store is not None
        assert rag.ai_generator is not None
        assert rag.session_manager is not None
        assert rag.tool_manager is not None
        assert rag.search_tool is not None
        assert rag.outline_tool is not None
    
    def test_add_course_document(self, test_config, sample_course_doc):
        """Test adding a single course document"""
        rag = RAGSystem(test_config)
        
        course, chunk_count = rag.add_course_document(sample_course_doc)
        
        assert course is not None
        assert course.title == "Test Course on Programming"
        assert chunk_count > 0
        
        # Verify course was added to vector store
        existing_titles = rag.vector_store.get_existing_course_titles()
        assert "Test Course on Programming" in existing_titles
    
    def test_add_course_document_error_handling(self, test_config):
        """Test error handling when adding invalid document"""
        rag = RAGSystem(test_config)
        
        # Try to add nonexistent file
        course, chunk_count = rag.add_course_document("/nonexistent/file.txt")
        
        assert course is None
        assert chunk_count == 0
    
    def test_add_course_folder(self, test_config, temp_dir, sample_course_doc):
        """Test adding documents from a folder"""
        rag = RAGSystem(test_config)
        
        # Create a test folder with the sample document
        test_folder = os.path.join(temp_dir, "test_docs")
        os.makedirs(test_folder)
        
        # Copy sample doc to test folder
        import shutil
        target_path = os.path.join(test_folder, "course1.txt")
        shutil.copy2(sample_course_doc, target_path)
        
        # Add the folder
        course_count, chunk_count = rag.add_course_folder(test_folder)
        
        assert course_count == 1
        assert chunk_count > 0
        
        # Verify course was added
        existing_titles = rag.vector_store.get_existing_course_titles()
        assert len(existing_titles) == 1
    
    def test_add_course_folder_skip_existing(self, test_config, temp_dir, sample_course_doc):
        """Test that existing courses are skipped when adding folder"""
        rag = RAGSystem(test_config)
        
        # Create test folder
        test_folder = os.path.join(temp_dir, "test_docs")
        os.makedirs(test_folder)
        
        import shutil
        target_path = os.path.join(test_folder, "course1.txt")
        shutil.copy2(sample_course_doc, target_path)
        
        # Add folder first time
        course_count1, chunk_count1 = rag.add_course_folder(test_folder)
        assert course_count1 == 1
        
        # Add folder second time - should skip existing
        course_count2, chunk_count2 = rag.add_course_folder(test_folder)
        assert course_count2 == 0  # No new courses added
        assert chunk_count2 == 0
    
    def test_add_course_folder_clear_existing(self, test_config, temp_dir, sample_course_doc):
        """Test clearing existing data when adding folder"""
        rag = RAGSystem(test_config)
        
        # Add a course first
        course, chunk_count = rag.add_course_document(sample_course_doc)
        assert course is not None
        
        # Create test folder with different course
        test_folder = os.path.join(temp_dir, "test_docs")
        os.makedirs(test_folder)
        
        # Create a different course document
        different_doc = os.path.join(test_folder, "different_course.txt")
        with open(different_doc, 'w') as f:
            f.write("""Course Title: Different Course
Course Instructor: Jane Doe

Lesson 1: Introduction
This is different course content.
""")
        
        # Add folder with clear_existing=True
        course_count, chunk_count = rag.add_course_folder(test_folder, clear_existing=True)
        
        assert course_count == 1
        
        # Verify old course is gone, new course exists
        existing_titles = rag.vector_store.get_existing_course_titles()
        assert "Test Course on Programming" not in existing_titles
        assert "Different Course" in existing_titles
    
    def test_add_course_folder_nonexistent(self, test_config):
        """Test adding from nonexistent folder"""
        rag = RAGSystem(test_config)
        
        course_count, chunk_count = rag.add_course_folder("/nonexistent/folder")
        
        assert course_count == 0
        assert chunk_count == 0
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_query_without_session(self, mock_anthropic, test_config, sample_course_doc):
        """Test querying without session ID"""
        # Mock the API response
        mock_response = Mock()
        mock_response.content = [Mock(text="This is a test response")]
        mock_response.stop_reason = "end_turn"
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        # Setup RAG system with test data
        rag = RAGSystem(test_config)
        course, chunk_count = rag.add_course_document(sample_course_doc)
        
        # Test query
        response, sources = rag.query("What is Python?")
        
        assert response == "This is a test response"
        assert isinstance(sources, list)
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_query_with_session(self, mock_anthropic, test_config, sample_course_doc):
        """Test querying with session ID"""
        # Mock the API response
        mock_response = Mock()
        mock_response.content = [Mock(text="Response with session")]
        mock_response.stop_reason = "end_turn"
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        # Setup RAG system
        rag = RAGSystem(test_config)
        course, chunk_count = rag.add_course_document(sample_course_doc)
        
        # Test query with session
        session_id = "test_session"
        response, sources = rag.query("What is Python?", session_id=session_id)
        
        assert response == "Response with session"
        
        # Verify conversation was recorded
        history = rag.session_manager.get_conversation_history(session_id)
        assert history is not None
        assert "What is Python?" in history
        assert "Response with session" in history
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_query_with_tool_execution(self, mock_anthropic, test_config, sample_course_doc):
        """Test query that triggers tool execution"""
        # Mock tool use response
        mock_tool_content = Mock()
        mock_tool_content.type = "tool_use"
        mock_tool_content.name = "search_course_content"
        mock_tool_content.input = {"query": "Python programming"}
        mock_tool_content.id = "tool_123"
        
        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_content]
        mock_initial_response.stop_reason = "tool_use"
        
        # Mock final response
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Based on the course content, Python is...")]
        
        mock_client = Mock()
        mock_client.messages.create.side_effect = [mock_initial_response, mock_final_response]
        mock_anthropic.return_value = mock_client
        
        # Setup RAG system with real data
        rag = RAGSystem(test_config)
        course, chunk_count = rag.add_course_document(sample_course_doc)
        
        # Test query that should trigger search
        response, sources = rag.query("Tell me about Python programming")
        
        assert response == "Based on the course content, Python is..."
        assert len(sources) > 0  # Should have sources from search
    
    def test_get_course_analytics(self, test_config, sample_course_doc):
        """Test getting course analytics"""
        rag = RAGSystem(test_config)
        
        # Initially should be empty
        analytics = rag.get_course_analytics()
        assert analytics["total_courses"] == 0
        assert len(analytics["course_titles"]) == 0
        
        # Add a course
        course, chunk_count = rag.add_course_document(sample_course_doc)
        
        # Should now show the course
        analytics = rag.get_course_analytics()
        assert analytics["total_courses"] == 1
        assert "Test Course on Programming" in analytics["course_titles"]
    
    def test_tool_manager_integration(self, test_config):
        """Test that tools are properly registered with tool manager"""
        rag = RAGSystem(test_config)
        
        # Verify tools are registered
        definitions = rag.tool_manager.get_tool_definitions()
        assert len(definitions) == 2
        
        tool_names = [d["name"] for d in definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names
        
        # Verify tools can be executed
        result = rag.tool_manager.execute_tool("search_course_content", query="test")
        assert isinstance(result, str)
        
        result = rag.tool_manager.execute_tool("get_course_outline", course_name="test")
        assert isinstance(result, str)
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_sources_reset_after_query(self, mock_anthropic, test_config, sample_course_doc):
        """Test that sources are reset after each query"""
        # Mock tool use to generate sources
        mock_tool_content = Mock()
        mock_tool_content.type = "tool_use"
        mock_tool_content.name = "search_course_content"
        mock_tool_content.input = {"query": "test"}
        mock_tool_content.id = "tool_123"
        
        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_content]
        mock_initial_response.stop_reason = "tool_use"
        
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Response")]
        
        mock_client = Mock()
        mock_client.messages.create.side_effect = [mock_initial_response, mock_final_response]
        mock_anthropic.return_value = mock_client
        
        # Setup RAG system
        rag = RAGSystem(test_config)
        course, chunk_count = rag.add_course_document(sample_course_doc)
        
        # First query
        response1, sources1 = rag.query("First query")
        
        # Second query - sources should be reset
        mock_client.messages.create.side_effect = [mock_initial_response, mock_final_response]
        response2, sources2 = rag.query("Second query")
        
        # Sources should be independent between queries
        assert len(rag.tool_manager.get_last_sources()) == 0  # Should be reset
    
    def test_prompt_format(self, test_config):
        """Test that query is properly formatted as prompt"""
        rag = RAGSystem(test_config)
        
        # Mock AI generator to capture the prompt
        rag.ai_generator.generate_response = Mock(return_value="test response")
        
        query = "What is machine learning?"
        response, sources = rag.query(query)
        
        # Verify AI generator was called with formatted prompt
        rag.ai_generator.generate_response.assert_called_once()
        call_args = rag.ai_generator.generate_response.call_args
        
        prompt = call_args.kwargs["query"]
        assert query in prompt
        assert "Answer this question about course materials:" in prompt