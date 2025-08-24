import os
from unittest.mock import Mock, patch

import pytest
from config import Config, config
from rag_system import RAGSystem


class TestSystemHealth:
    """Test system configuration and health checks"""

    def test_config_initialization(self):
        """Test that configuration loads correctly"""
        test_config = Config()

        # Check required settings exist
        assert hasattr(test_config, "ANTHROPIC_API_KEY")
        assert hasattr(test_config, "ANTHROPIC_MODEL")
        assert hasattr(test_config, "EMBEDDING_MODEL")
        assert hasattr(test_config, "CHUNK_SIZE")
        assert hasattr(test_config, "CHUNK_OVERLAP")
        assert hasattr(test_config, "MAX_RESULTS")
        assert hasattr(test_config, "MAX_HISTORY")
        assert hasattr(test_config, "CHROMA_PATH")

        # Check default values
        assert test_config.ANTHROPIC_MODEL == "claude-sonnet-4-20250514"
        assert test_config.EMBEDDING_MODEL == "all-MiniLM-L6-v2"
        assert test_config.CHUNK_SIZE == 800
        assert test_config.CHUNK_OVERLAP == 100
        assert test_config.MAX_RESULTS == 5
        assert test_config.MAX_HISTORY == 2
        assert test_config.CHROMA_PATH == "./chroma_db"

    def test_api_key_configuration(self):
        """Test API key configuration"""
        # Check if API key is set in the actual config
        assert config.ANTHROPIC_API_KEY != ""
        assert config.ANTHROPIC_API_KEY != "your-anthropic-api-key-here"
        assert config.ANTHROPIC_API_KEY.startswith("sk-ant-")

    def test_documents_folder_exists(self):
        """Test that documents folder exists and has content"""
        docs_path = "../docs"

        assert os.path.exists(docs_path), "Documents folder should exist"

        # Check for course files
        files = os.listdir(docs_path)
        course_files = [f for f in files if f.endswith((".txt", ".pdf", ".docx"))]

        assert len(course_files) > 0, "Should have course documents"

        # Verify files have content
        for file_name in course_files:
            file_path = os.path.join(docs_path, file_name)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                assert len(content) > 0, f"Course file {file_name} should not be empty"

    def test_document_format_validation(self):
        """Test that documents follow expected format"""
        docs_path = "../docs"

        if not os.path.exists(docs_path):
            pytest.skip("Documents folder not found")

        from document_processor import DocumentProcessor

        processor = DocumentProcessor(800, 100)

        files = os.listdir(docs_path)
        course_files = [f for f in files if f.endswith(".txt")]

        for file_name in course_files[:2]:  # Test first 2 files
            file_path = os.path.join(docs_path, file_name)
            try:
                course, chunks = processor.process_course_document(file_path)
                assert course is not None, f"Could not parse course from {file_name}"
                assert course.title != "", f"Course title empty in {file_name}"
                assert len(chunks) > 0, f"No chunks generated from {file_name}"
            except Exception as e:
                pytest.fail(f"Failed to process {file_name}: {e}")

    @patch("ai_generator.anthropic.Anthropic")
    def test_anthropic_client_initialization(self, mock_anthropic):
        """Test that Anthropic client can be initialized"""
        from ai_generator import AIGenerator

        # Mock successful client creation
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        generator = AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)

        assert generator.client is not None
        mock_anthropic.assert_called_once_with(api_key=config.ANTHROPIC_API_KEY)

    def test_vector_store_initialization(self, temp_dir):
        """Test that vector store can be initialized"""
        from vector_store import VectorStore

        # Use temporary directory for test
        chroma_path = os.path.join(temp_dir, "test_chroma")
        store = VectorStore(chroma_path, config.EMBEDDING_MODEL, config.MAX_RESULTS)

        assert store is not None
        assert store.client is not None
        assert store.course_catalog is not None
        assert store.course_content is not None

    def test_sentence_transformer_loading(self):
        """Test that sentence transformer model can be loaded"""
        from sentence_transformers import SentenceTransformer

        # This will download the model if not already present
        try:
            model = SentenceTransformer(config.EMBEDDING_MODEL)
            assert model is not None

            # Test encoding
            embeddings = model.encode(["Test sentence"])
            assert len(embeddings) > 0
            assert len(embeddings[0]) > 0
        except Exception as e:
            pytest.fail(f"Could not load embedding model: {e}")

    def test_chromadb_functionality(self, temp_dir):
        """Test basic ChromaDB functionality"""
        import chromadb
        from chromadb.config import Settings

        chroma_path = os.path.join(temp_dir, "test_chroma")

        try:
            client = chromadb.PersistentClient(
                path=chroma_path, settings=Settings(anonymized_telemetry=False)
            )

            # Create a test collection
            collection = client.get_or_create_collection("test_collection")

            # Test basic operations
            collection.add(
                documents=["This is a test document"],
                ids=["test_id"],
                metadatas=[{"test": "metadata"}],
            )

            results = collection.get(ids=["test_id"])
            assert len(results["documents"]) == 1
            assert results["documents"][0] == "This is a test document"

        except Exception as e:
            pytest.fail(f"ChromaDB test failed: {e}")

    def test_full_system_initialization(self):
        """Test that the full RAG system can be initialized"""
        try:
            rag_system = RAGSystem(config)
            assert rag_system is not None

            # Test all components are initialized
            assert rag_system.document_processor is not None
            assert rag_system.vector_store is not None
            assert rag_system.ai_generator is not None
            assert rag_system.session_manager is not None
            assert rag_system.tool_manager is not None
            assert rag_system.search_tool is not None
            assert rag_system.outline_tool is not None

        except Exception as e:
            pytest.fail(f"Full system initialization failed: {e}")

    def test_document_loading_health(self):
        """Test that documents can be loaded into the system"""
        docs_path = "../docs"

        if not os.path.exists(docs_path):
            pytest.skip("Documents folder not found")

        try:
            # Use a temporary config to avoid affecting real data
            import tempfile
            from dataclasses import replace

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_config = replace(
                    config, CHROMA_PATH=os.path.join(temp_dir, "test_chroma")
                )
                rag_system = RAGSystem(temp_config)

                # Try to load first document
                files = [f for f in os.listdir(docs_path) if f.endswith(".txt")]
                if files:
                    test_file = os.path.join(docs_path, files[0])
                    course, chunk_count = rag_system.add_course_document(test_file)

                    assert course is not None, f"Could not load document {files[0]}"
                    assert chunk_count > 0, f"No chunks created from {files[0]}"

                    # Test search functionality
                    results = rag_system.vector_store.search("test query")
                    assert results is not None

        except Exception as e:
            pytest.fail(f"Document loading health check failed: {e}")

    def test_tool_definitions_health(self):
        """Test that tools provide valid definitions"""
        import tempfile

        from search_tools import CourseOutlineTool, CourseSearchTool, ToolManager
        from vector_store import VectorStore

        with tempfile.TemporaryDirectory() as temp_dir:
            chroma_path = os.path.join(temp_dir, "test_chroma")
            vector_store = VectorStore(chroma_path, config.EMBEDDING_MODEL)

            # Test search tool
            search_tool = CourseSearchTool(vector_store)
            search_def = search_tool.get_tool_definition()

            assert search_def["name"] == "search_course_content"
            assert "description" in search_def
            assert "input_schema" in search_def
            assert "properties" in search_def["input_schema"]
            assert "required" in search_def["input_schema"]

            # Test outline tool
            outline_tool = CourseOutlineTool(vector_store)
            outline_def = outline_tool.get_tool_definition()

            assert outline_def["name"] == "get_course_outline"
            assert "description" in outline_def
            assert "input_schema" in outline_def

            # Test tool manager
            manager = ToolManager()
            manager.register_tool(search_tool)
            manager.register_tool(outline_tool)

            definitions = manager.get_tool_definitions()
            assert len(definitions) == 2

    def test_session_manager_health(self):
        """Test session manager functionality"""
        from session_manager import SessionManager

        session_manager = SessionManager(max_history=2)
        assert session_manager is not None

        # Test session creation
        session_id = session_manager.create_session()
        assert session_id is not None
        assert len(session_id) > 0

        # Test conversation handling
        session_manager.add_exchange(session_id, "Test question", "Test response")
        history = session_manager.get_conversation_history(session_id)

        assert history is not None
        assert "Test question" in history
        assert "Test response" in history

    @patch("ai_generator.anthropic.Anthropic")
    def test_api_connection_simulation(self, mock_anthropic):
        """Test simulated API connection"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.stop_reason = "end_turn"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        from ai_generator import AIGenerator

        generator = AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)

        response = generator.generate_response("Test query")
        assert response == "Test response"

        # Verify API was called with correct parameters
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args

        assert call_args.kwargs["model"] == config.ANTHROPIC_MODEL
        assert call_args.kwargs["temperature"] == 0
        assert call_args.kwargs["max_tokens"] == 800
