import pytest
from unittest.mock import Mock, patch, MagicMock
from ai_generator import AIGenerator
from search_tools import ToolManager, CourseSearchTool


class TestAIGenerator:
    """Test AIGenerator Claude API integration and tool calling"""
    
    def test_initialization(self):
        """Test AIGenerator initialization"""
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        
        assert generator is not None
        assert generator.model == "claude-sonnet-4-20250514"
        assert generator.base_params["model"] == "claude-sonnet-4-20250514"
        assert generator.base_params["temperature"] == 0
        assert generator.base_params["max_tokens"] == 800
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_basic_response_generation(self, mock_anthropic):
        """Test basic response generation without tools"""
        # Mock the API response
        mock_response = Mock()
        mock_response.content = [Mock(text="This is a test response")]
        mock_response.stop_reason = "end_turn"
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        # Test the generator
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        result = generator.generate_response("What is Python?")
        
        assert result == "This is a test response"
        mock_client.messages.create.assert_called_once()
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_response_with_conversation_history(self, mock_anthropic):
        """Test response generation with conversation history"""
        # Mock the API response
        mock_response = Mock()
        mock_response.content = [Mock(text="Response with history")]
        mock_response.stop_reason = "end_turn"
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        # Test with history
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        history = "User: Hello\nAssistant: Hi there!"
        result = generator.generate_response("What is Python?", conversation_history=history)
        
        assert result == "Response with history"
        
        # Verify the system prompt includes history
        call_args = mock_client.messages.create.call_args
        system_content = call_args.kwargs["system"]
        assert history in system_content
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_calling_setup(self, mock_anthropic):
        """Test that tools are properly passed to the API"""
        # Mock the API response (without tool use)
        mock_response = Mock()
        mock_response.content = [Mock(text="Direct response")]
        mock_response.stop_reason = "end_turn"
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        # Create mock tools
        mock_tools = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "input_schema": {"type": "object", "properties": {}}
            }
        ]
        
        # Create a mock tool manager
        mock_tool_manager = Mock()
        
        # Test with tools
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        result = generator.generate_response("Test query", tools=mock_tools, tool_manager=mock_tool_manager)
        
        # Verify tools were passed to API
        call_args = mock_client.messages.create.call_args
        assert "tools" in call_args.kwargs
        assert call_args.kwargs["tools"] == mock_tools
        assert call_args.kwargs["tool_choice"] == {"type": "auto"}
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_execution_flow(self, mock_anthropic):
        """Test the complete tool execution flow"""
        # Mock tool use response
        mock_tool_content = Mock()
        mock_tool_content.type = "tool_use"
        mock_tool_content.name = "search_course_content"
        mock_tool_content.input = {"query": "Python programming"}
        mock_tool_content.id = "test_tool_id"
        
        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_content]
        mock_initial_response.stop_reason = "tool_use"
        
        # Mock final response after tool execution
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final response after tool use")]
        
        mock_client = Mock()
        # First call returns tool use, second call returns final response
        mock_client.messages.create.side_effect = [mock_initial_response, mock_final_response]
        mock_anthropic.return_value = mock_client
        
        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool search results"
        
        mock_tools = [{"name": "search_course_content"}]
        
        # Test tool execution
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        result = generator.generate_response(
            "Find information about Python",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        assert result == "Final response after tool use"
        
        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="Python programming"
        )
        
        # Verify two API calls were made
        assert mock_client.messages.create.call_count == 2
    
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_api_error_handling(self, mock_anthropic):
        """Test handling of API errors"""
        # Mock API to raise an exception
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic.return_value = mock_client
        
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        
        # Should propagate the exception
        with pytest.raises(Exception, match="API Error"):
            generator.generate_response("Test query")
    
    def test_system_prompt_content(self):
        """Test that system prompt contains expected content"""
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        
        system_prompt = generator.SYSTEM_PROMPT
        
        # Check for key elements in system prompt
        assert "search_course_content" in system_prompt
        assert "get_course_outline" in system_prompt
        assert "Multi-Round Tool Usage" in system_prompt
        assert "2 sequential tool calls" in system_prompt
        assert "Brief, Concise and focused" in system_prompt
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_integration_with_real_tools(self, mock_anthropic, vector_store):
        """Test integration with actual search tools"""
        # Mock API response that uses tools
        mock_tool_content = Mock()
        mock_tool_content.type = "tool_use"
        mock_tool_content.name = "search_course_content"
        mock_tool_content.input = {"query": "Python"}
        mock_tool_content.id = "search_123"
        
        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_content]
        mock_initial_response.stop_reason = "tool_use"
        
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Here's what I found about Python")]
        
        mock_client = Mock()
        mock_client.messages.create.side_effect = [mock_initial_response, mock_final_response]
        mock_anthropic.return_value = mock_client
        
        # Setup real tool manager with test data
        from models import Course, CourseChunk
        
        course = Course(title="Python Course", lessons=[])
        vector_store.add_course_metadata(course)
        
        chunk = CourseChunk(
            content="Python is a programming language",
            course_title="Python Course",
            lesson_number=1,
            chunk_index=0
        )
        vector_store.add_course_content([chunk])
        
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(vector_store)
        tool_manager.register_tool(search_tool)
        
        # Test with real tools
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        result = generator.generate_response(
            "Tell me about Python",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )
        
        assert result == "Here's what I found about Python"
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_sequential_tool_calling(self, mock_anthropic):
        """Test sequential tool calling over 2 rounds"""
        # Mock first tool use response
        mock_tool1_content = Mock()
        mock_tool1_content.type = "tool_use"
        mock_tool1_content.name = "get_course_outline"
        mock_tool1_content.input = {"course_name": "Python Course"}
        mock_tool1_content.id = "tool1_id"
        
        mock_first_response = Mock()
        mock_first_response.content = [mock_tool1_content]
        mock_first_response.stop_reason = "tool_use"
        
        # Mock second tool use response
        mock_tool2_content = Mock()
        mock_tool2_content.type = "tool_use"
        mock_tool2_content.name = "search_course_content"
        mock_tool2_content.input = {"query": "variables"}
        mock_tool2_content.id = "tool2_id"
        
        mock_second_response = Mock()
        mock_second_response.content = [mock_tool2_content]
        mock_second_response.stop_reason = "tool_use"
        
        # Mock final response (no tools)
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Combined results from both searches")]
        mock_final_response.stop_reason = "end_turn"
        
        mock_client = Mock()
        # Three API calls: round 1, round 2, final response
        mock_client.messages.create.side_effect = [
            mock_first_response, 
            mock_second_response, 
            mock_final_response
        ]
        mock_anthropic.return_value = mock_client
        
        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Course outline results",
            "Content search results"
        ]
        
        mock_tools = [{"name": "get_course_outline"}, {"name": "search_course_content"}]
        
        # Test sequential tool calling
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        result = generator.generate_response(
            "Find lesson 4 topic in Python Course, then search for related content",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        assert result == "Combined results from both searches"
        
        # Verify two tool executions occurred
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call("get_course_outline", course_name="Python Course")
        mock_tool_manager.execute_tool.assert_any_call("search_course_content", query="variables")
        
        # Verify three API calls were made (2 tool rounds + 1 final)
        assert mock_client.messages.create.call_count == 3
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_max_rounds_termination(self, mock_anthropic):
        """Test that tool calling terminates after MAX_TOOL_ROUNDS"""
        # Mock tool use responses for all rounds
        mock_tool_content = Mock()
        mock_tool_content.type = "tool_use"
        mock_tool_content.name = "search_course_content"
        mock_tool_content.input = {"query": "test"}
        mock_tool_content.id = "tool_id"
        
        mock_tool_response = Mock()
        mock_tool_response.content = [mock_tool_content]
        mock_tool_response.stop_reason = "tool_use"
        
        # Mock final response after max rounds
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final response after max rounds")]
        mock_final_response.stop_reason = "end_turn"
        
        mock_client = Mock()
        # Responses: round 1 tool, round 2 tool, final call (no tools)
        mock_client.messages.create.side_effect = [
            mock_tool_response,
            mock_tool_response, 
            mock_final_response
        ]
        mock_anthropic.return_value = mock_client
        
        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"
        
        mock_tools = [{"name": "search_course_content"}]
        
        # Test max rounds termination
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        result = generator.generate_response(
            "Keep searching",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        assert result == "Final response after max rounds"
        
        # Should execute tools exactly 2 times (MAX_TOOL_ROUNDS)
        assert mock_tool_manager.execute_tool.call_count == 2
        
        # Should make exactly 3 API calls (2 rounds + final)
        assert mock_client.messages.create.call_count == 3
    
    @patch('ai_generator.anthropic.Anthropic') 
    def test_natural_termination_no_tools(self, mock_anthropic):
        """Test natural termination when Claude doesn't use tools"""
        # Mock response with no tool use
        mock_response = Mock()
        mock_response.content = [Mock(text="Direct response without tools")]
        mock_response.stop_reason = "end_turn"
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        mock_tool_manager = Mock()
        mock_tools = [{"name": "search_course_content"}]
        
        # Test natural termination
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        result = generator.generate_response(
            "What is 2+2?",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        assert result == "Direct response without tools"
        
        # No tool executions should occur
        mock_tool_manager.execute_tool.assert_not_called()
        
        # Only one API call should be made
        assert mock_client.messages.create.call_count == 1
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_execution_failure_handling(self, mock_anthropic):
        """Test graceful handling when tool execution fails"""
        # Mock tool use response without text content (just tool_use)
        mock_tool_content = Mock()
        mock_tool_content.type = "tool_use"
        mock_tool_content.name = "search_course_content"
        mock_tool_content.input = {"query": "test"}
        mock_tool_content.id = "tool_id"
        
        mock_response = Mock()
        mock_response.content = [mock_tool_content]
        mock_response.stop_reason = "tool_use"
        
        # Configure the mock so hasattr(response.content[0], 'text') returns False
        # and accessing response.content[0].text will not work properly
        mock_tool_content.text = Mock()
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        # Mock tool manager that fails
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = Exception("Tool failed")
        
        mock_tools = [{"name": "search_course_content"}]
        
        # Test error handling
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        result = generator.generate_response(
            "Search for something",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Should return fallback string when no text is available and tool fails
        assert isinstance(result, str)
        assert result == "No text response generated"
        
        # Tool execution may be attempted multiple times (up to max rounds) 
        # since errors are passed back to Claude
        assert mock_tool_manager.execute_tool.call_count >= 1
        
        # Should make up to max rounds API calls
        assert mock_client.messages.create.call_count <= 3  # Max 2 tool rounds + 1 final