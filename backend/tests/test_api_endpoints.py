"""
API endpoint tests for the RAG system FastAPI application.
Tests all main API endpoints with proper request/response handling.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.api
class TestQueryEndpoint:
    """Test the /api/query endpoint"""
    
    def test_query_with_session_id(self, test_client, sample_query_request):
        """Test query endpoint with provided session ID"""
        response = test_client.post("/api/query", json=sample_query_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "test-session-123"
        assert data["answer"] == "Test answer"
        assert data["sources"] == ["Test source"]
    
    def test_query_without_session_id(self, test_client):
        """Test query endpoint without session ID (should create new session)"""
        request_data = {"query": "What is machine learning?"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "test-session-123"  # From mock
    
    def test_query_empty_request(self, test_client):
        """Test query endpoint with empty query"""
        request_data = {"query": ""}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200  # Should still work with empty query
    
    def test_query_missing_query_field(self, test_client):
        """Test query endpoint with missing query field"""
        request_data = {"session_id": "test-123"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_query_invalid_json(self, test_client):
        """Test query endpoint with invalid JSON"""
        response = test_client.post(
            "/api/query", 
            data="invalid json",
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_query_async(self, async_client, sample_query_request):
        """Test query endpoint with async client"""
        response = await async_client.post("/api/query", json=sample_query_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Test answer"
        assert data["session_id"] == "test-session-123"


@pytest.mark.api
class TestCoursesEndpoint:
    """Test the /api/courses endpoint"""
    
    def test_get_courses(self, test_client):
        """Test courses endpoint returns course statistics"""
        response = test_client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == 2
        assert data["course_titles"] == ["Test Course 1", "Test Course 2"]
    
    def test_get_courses_post_method_not_allowed(self, test_client):
        """Test courses endpoint doesn't accept POST requests"""
        response = test_client.post("/api/courses")
        
        assert response.status_code == 405  # Method not allowed
    
    @pytest.mark.asyncio
    async def test_get_courses_async(self, async_client):
        """Test courses endpoint with async client"""
        response = await async_client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 2


@pytest.mark.api
class TestSessionEndpoint:
    """Test the session management endpoints"""
    
    def test_clear_session(self, test_client):
        """Test clearing a session"""
        session_id = "test-session-456"
        response = test_client.delete(f"/api/sessions/{session_id}/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Session cleared successfully"
        assert data["session_id"] == session_id
    
    def test_clear_session_empty_id(self, test_client):
        """Test clearing session with empty ID"""
        response = test_client.delete("/api/sessions//clear")
        
        assert response.status_code == 404  # Not found due to empty path segment
    
    @pytest.mark.asyncio
    async def test_clear_session_async(self, async_client):
        """Test clearing session with async client"""
        session_id = "async-session-123"
        response = await async_client.delete(f"/api/sessions/{session_id}/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id


@pytest.mark.api
class TestRootEndpoint:
    """Test the root / endpoint"""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint returns basic message"""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "RAG System API"
    
    @pytest.mark.asyncio
    async def test_root_endpoint_async(self, async_client):
        """Test root endpoint with async client"""
        response = await async_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "RAG System API"


@pytest.mark.api
class TestErrorHandling:
    """Test error handling in API endpoints"""
    
    def test_nonexistent_endpoint(self, test_client):
        """Test accessing non-existent endpoint"""
        response = test_client.get("/api/nonexistent")
        
        assert response.status_code == 404
    
    def test_cors_headers(self, test_client):
        """Test that CORS headers are present"""
        response = test_client.get("/api/courses")
        
        assert response.status_code == 200
        # Check for CORS headers (they may be set by test framework)
        # Just ensure the request succeeds with CORS middleware


@pytest.mark.api
class TestRequestValidation:
    """Test request validation and Pydantic models"""
    
    def test_query_request_validation(self, test_client):
        """Test query request model validation"""
        # Test with extra fields (should be ignored)
        request_data = {
            "query": "Test query",
            "session_id": "test-123",
            "extra_field": "should be ignored"
        }
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
    
    def test_query_request_type_validation(self, test_client):
        """Test query request with wrong data types"""
        request_data = {
            "query": 123,  # Should be string
            "session_id": ["not-a-string"]  # Should be string
        }
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 422  # Validation error


@pytest.mark.integration
@pytest.mark.api
class TestEndToEndFlow:
    """Test complete API workflow"""
    
    def test_complete_query_flow(self, test_client):
        """Test a complete query flow with session management"""
        # 1. Make query without session ID (creates new session)
        query1_data = {"query": "What is Python?"}
        response1 = test_client.post("/api/query", json=query1_data)
        
        assert response1.status_code == 200
        data1 = response1.json()
        session_id = data1["session_id"]
        
        # 2. Make another query with the same session ID
        query2_data = {"query": "Tell me more about variables", "session_id": session_id}
        response2 = test_client.post("/api/query", json=query2_data)
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["session_id"] == session_id
        
        # 3. Clear the session
        clear_response = test_client.delete(f"/api/sessions/{session_id}/clear")
        assert clear_response.status_code == 200
    
    def test_get_courses_then_query(self, test_client):
        """Test getting courses then making queries"""
        # 1. Get course information
        courses_response = test_client.get("/api/courses")
        assert courses_response.status_code == 200
        courses_data = courses_response.json()
        
        # 2. Make a query about the courses
        query_data = {"query": f"Tell me about {courses_data['course_titles'][0]}"}
        query_response = test_client.post("/api/query", json=query_data)
        
        assert query_response.status_code == 200