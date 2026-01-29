"""Tests for GET /api/profile and PATCH /api/profile."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

# conftest.py pre-loads these modules, so we can import them directly.
import api.profile_routes as profile_mod


def _mock_httpx(MockClient, instance):
    """Wire up the async context-manager protocol on a mock AsyncClient."""
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=False)
    MockClient.return_value = instance


# ---------------------------------------------------------------------------
# GET /api/profile
# ---------------------------------------------------------------------------


class TestGetProfile:
    def test_returns_existing_profile(self, client):
        """GET returns profile data when a row exists in Supabase."""
        fake_response = httpx.Response(
            200,
            json=[
                {
                    "id": "user-123",
                    "full_name": "Alice",
                    "email": "user@example.com",
                    "education": "B.Sc. CS",
                    "career_title": "SWE",
                    "avatar_url": "https://img.example.com/a.png",
                    "schema_url": None,
                    "drive_url": None,
                    "updated_at": "2026-01-30T00:00:00Z",
                }
            ],
            request=httpx.Request("GET", "https://test.supabase.co/rest/v1/profiles"),
        )

        instance = AsyncMock()
        instance.get.return_value = fake_response
        with patch.object(profile_mod.httpx, "AsyncClient") as MockClient:
            _mock_httpx(MockClient, instance)
            resp = client.get("/api/profile", headers={"Authorization": "Bearer tok-abc"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "user-123"
        assert data["display_name"] == "Alice"
        assert data["education"] == "B.Sc. CS"
        assert data["career_title"] == "SWE"
        assert data["avatar_url"] == "https://img.example.com/a.png"

    def test_returns_skeleton_when_no_row(self, client):
        """GET returns an empty skeleton when no profile row exists."""
        fake_response = httpx.Response(
            200,
            json=[],
            request=httpx.Request("GET", "https://test.supabase.co/rest/v1/profiles"),
        )

        instance = AsyncMock()
        instance.get.return_value = fake_response
        with patch.object(profile_mod.httpx, "AsyncClient") as MockClient:
            _mock_httpx(MockClient, instance)
            resp = client.get("/api/profile", headers={"Authorization": "Bearer tok-abc"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "user-123"
        assert data["email"] == "user@example.com"
        assert data["display_name"] is None
        assert data["education"] is None

    def test_upstream_error_returns_502(self, client):
        """GET returns 502 when Supabase responds with a 4xx/5xx."""
        fake_response = httpx.Response(
            500,
            json={"message": "internal"},
            request=httpx.Request("GET", "https://test.supabase.co/rest/v1/profiles"),
        )

        instance = AsyncMock()
        instance.get.return_value = fake_response
        with patch.object(profile_mod.httpx, "AsyncClient") as MockClient:
            _mock_httpx(MockClient, instance)
            resp = client.get("/api/profile", headers={"Authorization": "Bearer tok-abc"})

        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# PATCH /api/profile
# ---------------------------------------------------------------------------


class TestUpdateProfile:
    def test_patch_existing_row(self, client):
        """PATCH updates an existing profile row."""
        patched_row = {
            "id": "user-123",
            "full_name": "Bob",
            "email": "user@example.com",
            "education": "M.Sc. AI",
            "career_title": None,
            "avatar_url": None,
            "schema_url": None,
            "drive_url": None,
            "updated_at": "2026-01-30T01:00:00Z",
        }
        fake_patch = httpx.Response(
            200,
            json=[patched_row],
            request=httpx.Request("PATCH", "https://test.supabase.co/rest/v1/profiles"),
        )

        instance = AsyncMock()
        instance.patch.return_value = fake_patch
        with patch.object(profile_mod.httpx, "AsyncClient") as MockClient:
            _mock_httpx(MockClient, instance)
            resp = client.patch(
                "/api/profile",
                json={"display_name": "Bob", "education": "M.Sc. AI"},
                headers={"Authorization": "Bearer tok-abc"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "Bob"
        assert data["education"] == "M.Sc. AI"

    def test_upsert_creates_row_when_missing(self, client):
        """PATCH falls back to INSERT when no row exists."""
        fake_patch = httpx.Response(
            200,
            json=[],
            request=httpx.Request("PATCH", "https://test.supabase.co/rest/v1/profiles"),
        )
        inserted_row = {
            "id": "user-123",
            "full_name": "Carol",
            "email": "user@example.com",
            "education": None,
            "career_title": None,
            "avatar_url": None,
            "schema_url": None,
            "drive_url": None,
            "updated_at": "2026-01-30T02:00:00Z",
        }
        fake_post = httpx.Response(
            201,
            json=[inserted_row],
            request=httpx.Request("POST", "https://test.supabase.co/rest/v1/profiles"),
        )

        instance = AsyncMock()
        instance.patch.return_value = fake_patch
        instance.post.return_value = fake_post
        with patch.object(profile_mod.httpx, "AsyncClient") as MockClient:
            _mock_httpx(MockClient, instance)
            resp = client.patch(
                "/api/profile",
                json={"display_name": "Carol"},
                headers={"Authorization": "Bearer tok-abc"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "Carol"
        assert data["user_id"] == "user-123"
        instance.post.assert_called_once()

    def test_empty_payload_returns_current_profile(self, client):
        """PATCH with no changed fields returns the current profile via GET."""
        fake_get = httpx.Response(
            200,
            json=[
                {
                    "id": "user-123",
                    "full_name": "Dave",
                    "email": "user@example.com",
                    "education": None,
                    "career_title": None,
                    "avatar_url": None,
                    "schema_url": None,
                    "drive_url": None,
                    "updated_at": None,
                }
            ],
            request=httpx.Request("GET", "https://test.supabase.co/rest/v1/profiles"),
        )

        instance = AsyncMock()
        instance.get.return_value = fake_get
        with patch.object(profile_mod.httpx, "AsyncClient") as MockClient:
            _mock_httpx(MockClient, instance)
            resp = client.patch(
                "/api/profile",
                json={},
                headers={"Authorization": "Bearer tok-abc"},
            )

        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Dave"

    def test_insert_failure_returns_502(self, client):
        """PATCH returns 502 when the INSERT fallback also fails."""
        fake_patch = httpx.Response(
            200,
            json=[],
            request=httpx.Request("PATCH", "https://test.supabase.co/rest/v1/profiles"),
        )
        fake_post = httpx.Response(
            500,
            json={"message": "db error"},
            request=httpx.Request("POST", "https://test.supabase.co/rest/v1/profiles"),
        )

        instance = AsyncMock()
        instance.patch.return_value = fake_patch
        instance.post.return_value = fake_post
        with patch.object(profile_mod.httpx, "AsyncClient") as MockClient:
            _mock_httpx(MockClient, instance)
            resp = client.patch(
                "/api/profile",
                json={"display_name": "Fail"},
                headers={"Authorization": "Bearer tok-abc"},
            )

        assert resp.status_code == 502
