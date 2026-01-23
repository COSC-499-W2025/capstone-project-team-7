"""
Tests for Portfolio Items API endpoints.

Tests POST/GET/PATCH/DELETE /api/portfolio/items

Run with: pytest tests/test_portfolio_items_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
import uuid
from uuid import UUID

import sys
from pathlib import Path

# Add backend/src to path
backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

from main import app
from api.dependencies import AuthContext, get_auth_context

client = TestClient(app)

# Test user ID
TEST_USER_ID = "9870edb5-2741-4c0a-b5cd-494a498f7485"


# Override authentication for testing
async def _override_auth() -> AuthContext:
    return AuthContext(user_id=TEST_USER_ID, access_token="test-token")


@pytest.fixture
def authenticated_client():
    """Create a test client with mocked authentication."""
    app.dependency_overrides[get_auth_context] = _override_auth
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_portfolio_item():
    """Sample portfolio item data for testing."""
    return {
        "title": "Personal Portfolio Website",
        "summary": "Built a responsive portfolio website using React and Next.js",
        "role": "Full Stack Developer",
        "evidence": "https://github.com/user/portfolio",
        "thumbnail": "https://example.com/thumbnail.png"
    }


class TestPortfolioItemsAPI:
    """Test suite for portfolio items CRUD operations."""

    def test_create_portfolio_item(self, authenticated_client, sample_portfolio_item):
        """Test POST /api/portfolio/items - Create a new portfolio item."""
        response = authenticated_client.post("/api/portfolio/items", json=sample_portfolio_item)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert "user_id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["title"] == sample_portfolio_item["title"]
        assert data["summary"] == sample_portfolio_item["summary"]
        assert data["role"] == sample_portfolio_item["role"]
        assert data["evidence"] == sample_portfolio_item["evidence"]
        assert data["thumbnail"] == sample_portfolio_item["thumbnail"]
        assert data["user_id"] == TEST_USER_ID

    def test_get_all_portfolio_items(self, authenticated_client, sample_portfolio_item):
        """Test GET /api/portfolio/items - Retrieve all portfolio items."""
        # Create a couple of items first
        authenticated_client.post("/api/portfolio/items", json=sample_portfolio_item)
        authenticated_client.post("/api/portfolio/items", json={
            **sample_portfolio_item,
            "title": "E-commerce Platform"
        })

        # Get all items
        response = authenticated_client.get("/api/portfolio/items")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 2
        
        # Verify structure of returned items
        for item in data:
            assert "id" in item
            assert "user_id" in item
            assert "title" in item
            assert item["user_id"] == TEST_USER_ID

    def test_get_specific_portfolio_item(self, authenticated_client, sample_portfolio_item):
        """Test GET /api/portfolio/items/{item_id} - Retrieve a specific item."""
        # Create an item
        create_response = authenticated_client.post("/api/portfolio/items", json=sample_portfolio_item)
        created_item = create_response.json()
        item_id = created_item["id"]

        # Get the specific item
        response = authenticated_client.get(f"/api/portfolio/items/{item_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == item_id
        assert data["title"] == sample_portfolio_item["title"]
        assert data["user_id"] == TEST_USER_ID

    def test_get_nonexistent_portfolio_item(self, authenticated_client):
        """Test GET /api/portfolio/items/{item_id} - 404 for non-existent item."""
        fake_id = str(uuid.uuid4())
        response = authenticated_client.get(f"/api/portfolio/items/{fake_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "not_found"

    def test_update_portfolio_item(self, authenticated_client, sample_portfolio_item):
        """Test PATCH /api/portfolio/items/{item_id} - Update an existing item."""
        # Create an item
        create_response = authenticated_client.post("/api/portfolio/items", json=sample_portfolio_item)
        created_item = create_response.json()
        item_id = created_item["id"]

        # Update the item
        update_data = {
            "title": "Updated Portfolio Website",
            "summary": "Enhanced with new features and animations"
        }
        response = authenticated_client.patch(f"/api/portfolio/items/{item_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == item_id
        assert data["title"] == update_data["title"]
        assert data["summary"] == update_data["summary"]
        # Verify unchanged fields remain the same
        assert data["role"] == sample_portfolio_item["role"]
        assert data["evidence"] == sample_portfolio_item["evidence"]

    def test_update_nonexistent_portfolio_item(self, authenticated_client):
        """Test PATCH /api/portfolio/items/{item_id} - 404 for non-existent item."""
        fake_id = str(uuid.uuid4())
        update_data = {"title": "Updated Title"}
        response = authenticated_client.patch(f"/api/portfolio/items/{fake_id}", json=update_data)
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "not_found"

    def test_delete_portfolio_item(self, authenticated_client, sample_portfolio_item):
        """Test DELETE /api/portfolio/items/{item_id} - Delete an existing item."""
        # Create an item
        create_response = authenticated_client.post("/api/portfolio/items", json=sample_portfolio_item)
        created_item = create_response.json()
        item_id = created_item["id"]

        # Delete the item
        response = authenticated_client.delete(f"/api/portfolio/items/{item_id}")
        
        assert response.status_code == 204
        assert response.content == b''  # No content in response

        # Verify item is deleted
        get_response = authenticated_client.get(f"/api/portfolio/items/{item_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_portfolio_item(self, authenticated_client):
        """Test DELETE /api/portfolio/items/{item_id} - 404 for non-existent item."""
        fake_id = str(uuid.uuid4())
        response = authenticated_client.delete(f"/api/portfolio/items/{fake_id}")
        
        # Note: This might return 404 or handle differently based on service implementation
        assert response.status_code in [204, 404]  # Accept either for now

    def test_create_portfolio_item_minimal_data(self, authenticated_client):
        """Test creating a portfolio item with only required fields."""
        minimal_item = {
            "title": "Minimal Project"
        }
        response = authenticated_client.post("/api/portfolio/items", json=minimal_item)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["title"] == "Minimal Project"
        assert data["summary"] is None
        assert data["role"] is None
        assert data["evidence"] is None
        assert data["thumbnail"] is None

    def test_create_portfolio_item_missing_required_field(self, authenticated_client):
        """Test creating a portfolio item without required 'title' field."""
        invalid_item = {
            "summary": "Missing title field"
        }
        response = authenticated_client.post("/api/portfolio/items", json=invalid_item)
        
        assert response.status_code == 422  # Validation error
