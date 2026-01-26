from fastapi.testclient import TestClient
from uuid import UUID
import datetime

from backend.src.main import app
import api.portfolio_routes as portfolio_routes
import api.dependencies as dependencies


class FakeAuthContext:
    def __init__(self, user_id: str = "11111111-1111-1111-1111-111111111111"):
        self.user_id = user_id
        self.access_token = "fake-token"


class FakePortfolioService:
    def __init__(self):
        self.items = {}

    def get_all_portfolio_items(self, user_id: UUID):
        return list(self.items.values())

    def get_portfolio_item(self, user_id: UUID, item_id: UUID):
        return self.items.get(item_id)

    def create_portfolio_item(self, user_id: UUID, item_create):
        import uuid
        now = datetime.datetime.utcnow()
        item_id = uuid.uuid4()
        # normalize user_id to UUID instance
        user_uuid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))

        item = {
            "id": item_id,
            "user_id": user_uuid,
            "title": item_create.title,
            "summary": item_create.summary,
            "role": getattr(item_create, "role", None),
            "evidence": getattr(item_create, "evidence", None),
            "thumbnail": getattr(item_create, "thumbnail", None),
            "created_at": now,
            "updated_at": now,
        }
        self.items[item_id] = item
        return item

    def update_portfolio_item(self, user_id: UUID, item_id: UUID, item_update):
        item = self.items.get(item_id)
        if not item:
            return None
        for field in ("title", "summary", "role", "evidence", "thumbnail"):
            if getattr(item_update, field, None) is not None:
                item[field] = getattr(item_update, field)
        item["updated_at"] = datetime.datetime.utcnow()
        self.items[item_id] = item
        return item

    def delete_portfolio_item(self, user_id: UUID, item_id: UUID):
        return self.items.pop(item_id, None) is not None


def test_portfolio_crud_flow():
    client = TestClient(app)

    fake_service = FakePortfolioService()

    # override dependencies
    app.dependency_overrides[portfolio_routes.get_portfolio_item_service] = lambda: fake_service
    app.dependency_overrides[dependencies.get_auth_context] = lambda: FakeAuthContext()

    # Create
    resp = client.post("/api/portfolio/items", json={"title": "Test Item", "summary": "initial"})
    assert resp.status_code == 201
    created = resp.json()
    assert created["title"] == "Test Item"
    item_id = created["id"]

    # List
    resp = client.get("/api/portfolio/items")
    assert resp.status_code == 200
    items = resp.json()
    assert any(i["id"] == item_id for i in items)

    # Get
    resp = client.get(f"/api/portfolio/items/{item_id}")
    assert resp.status_code == 200
    one = resp.json()
    assert one["summary"] == "initial"

    # Update
    resp = client.patch(f"/api/portfolio/items/{item_id}", json={"summary": "updated"})
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["summary"] == "updated"

    # Delete
    resp = client.delete(f"/api/portfolio/items/{item_id}")
    assert resp.status_code == 204

    # Ensure gone
    resp = client.get("/api/portfolio/items")
    assert resp.status_code == 200
    items = resp.json()
    assert all(i["id"] != item_id for i in items)
