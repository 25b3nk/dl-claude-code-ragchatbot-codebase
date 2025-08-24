from typing import Dict, List, Optional

import anthropic
from config import config


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search and outline tools for course information.

Multi-Round Tool Usage:
- You can make up to 2 sequential tool calls to gather comprehensive information
- Use tools strategically: broad search first, then refined searches based on initial results
- Combine results from multiple tool calls into your final response

Tool Usage Guidelines:
- Use the **search_course_content** tool for questions about specific course content or detailed educational materials
- Use the **get_course_outline** tool for questions about course structure, outlines, lesson lists, or course overviews
- **Sequential strategy**: Consider using outline tool first to understand structure, then search for specific content
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

For Course Outline Queries:
- When users ask for course outlines, overviews, or lesson lists, use the get_course_outline tool
- Always include the complete information returned: course title, course link (if available), and all lesson details
- Present lessons in numerical order with both lesson numbers and titles
- Include lesson links when provided in the tool output

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course-specific content questions**: Use tools strategically - may require multiple searches
- **Complex queries**: Break down into multiple tool calls if needed (e.g., get outline first, then search specific content)
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the outline tool"


All responses must be:
1. **Comprehensive** - Leverage multiple searches when beneficial
2. **Brief, Concise and focused** - Get to the point quickly
3. **Educational** - Maintain instructional value
4. **Clear** - Use accessible language
5. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with up to 2 rounds of sequential tool usage.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize conversation state
        round_counter = 0
        max_rounds = config.MAX_TOOL_ROUNDS
        messages = [{"role": "user", "content": query}]

        # Sequential tool calling loop
        while round_counter < max_rounds:
            round_counter += 1

            # Make API call with tools if available and within limits
            response = self._make_api_call(
                messages, system_content, tools if tools and tool_manager else None
            )

            # Add assistant response to conversation
            messages.append({"role": "assistant", "content": response.content})

            # Check termination conditions
            if response.stop_reason != "tool_use" or not tool_manager:
                return self._extract_text_response(response)

            # Execute tools
            tool_results = self._execute_tools_with_error_handling(
                response, tool_manager
            )
            if not tool_results:
                # Tool execution failed - return current response if possible
                return self._extract_text_response(response)

            # Add tool results to conversation
            messages.append({"role": "user", "content": tool_results})

        # Max rounds reached - make final call without tools
        try:
            final_response = self._make_api_call(messages, system_content, tools=None)
            return self._extract_text_response(final_response)
        except Exception as e:
            return f"Error in final response generation: {str(e)}"

    def _make_api_call(
        self, messages: List[Dict], system_content: str, tools: Optional[List] = None
    ):
        """
        Make a single API call to Claude with given messages and tools.

        Args:
            messages: List of conversation messages
            system_content: System prompt content
            tools: Optional list of available tools

        Returns:
            API response object
        """
        api_params = {
            **self.base_params,
            "messages": messages.copy(),
            "system": system_content,
        }

        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        return self.client.messages.create(**api_params)

    def _execute_tools_with_error_handling(
        self, response, tool_manager
    ) -> Optional[List[Dict]]:
        """
        Execute all tool calls from a response with comprehensive error handling.

        Args:
            response: API response containing tool use requests
            tool_manager: Manager to execute tools

        Returns:
            List of tool results or None if all failed
        """
        tool_results = []

        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": result,
                        }
                    )
                except Exception as e:
                    # Log error but continue with partial results
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"Tool execution failed: {str(e)}",
                        }
                    )

        return tool_results if tool_results else None

    def _extract_text_response(self, response) -> str:
        """
        Extract text content from API response.

        Args:
            response: API response object

        Returns:
            Text content from response
        """
        for content in response.content:
            if hasattr(content, "text") and isinstance(content.text, str):
                return content.text
            elif (
                hasattr(content, "type")
                and content.type == "text"
                and hasattr(content, "text")
                and isinstance(content.text, str)
            ):
                return content.text

        # Fallback for backward compatibility - but check it's actually a string
        if hasattr(response.content[0], "text") and isinstance(
            response.content[0].text, str
        ):
            return response.content[0].text
        return "No text response generated"
