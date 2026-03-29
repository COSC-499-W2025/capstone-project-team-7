from __future__ import annotations

import logging
import os
from typing import List, Dict, Any, Optional, cast
from uuid import UUID

from supabase.client import create_client

from api.models.portfolio_item_models import PortfolioItem, PortfolioItemCreate, PortfolioItemUpdate
from services.services.supabase_keys import (
    apply_client_access_token,
    create_postgrest_client,
    is_jwt_like,
    resolve_supabase_api_key,
)
from services.services import local_store

logger = logging.getLogger(__name__)


class PortfolioItemServiceError(Exception):
    """Raised when portfolio item operations fail."""


class PortfolioItemService:
    """Service for managing portfolio items in Supabase."""

    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None) -> None:
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = resolve_supabase_api_key(
            supabase_key,
            prefer_anon_for_python_client=True,
        )

        if not self.supabase_url or not self.supabase_key:
            raise PortfolioItemServiceError("Supabase credentials not configured.")

        self._use_local_store = os.getenv("CAPSTONE_LOCAL_STORE") == "1"

        self.client: Any = None
        self._requires_user_token_client = False

        if self._use_local_store:
            return

        try:
            self.client = create_client(cast(str, self.supabase_url), cast(str, self.supabase_key))
        except Exception as exc:
            if (self.supabase_key or "").startswith("sb_publishable_"):
                self._requires_user_token_client = True
                try:
                    self.client = create_postgrest_client(
                        cast(str, self.supabase_url),
                        cast(str, self.supabase_key),
                    )
                    self._requires_user_token_client = False
                except Exception:
                    self.client = None
            else:
                raise PortfolioItemServiceError(f"Failed to initialize Supabase client: {exc}") from exc

    def apply_access_token(self, token: Optional[str]) -> None:
        if token and not is_jwt_like(token) and self.client is not None:
            return

        if self.client is None and token and is_jwt_like(token):
            try:
                self.client = create_client(cast(str, self.supabase_url), token)
            except Exception as exc:
                try:
                    self.client = create_postgrest_client(
                        cast(str, self.supabase_url),
                        cast(str, self.supabase_key),
                    )
                except Exception:
                    raise PortfolioItemServiceError(f"Failed to initialize user-scoped Supabase client: {exc}") from exc

        if self.client is None and token and not is_jwt_like(token) and self._requires_user_token_client:
            raise PortfolioItemServiceError("JWT access token is required for Supabase operations.")

        if self.client is None and self._requires_user_token_client:
            raise PortfolioItemServiceError("Authenticated user token is required for Supabase operations.")

        if self._use_local_store:
            return

        apply_client_access_token(self.client, token)

    def _handle_response(self, response: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Handle Supabase response data."""
        if response is not None:
            return response
        logger.error("Supabase operation returned None")
        raise PortfolioItemServiceError("Supabase operation returned None")

    def get_all_portfolio_items(self, user_id: UUID) -> List[PortfolioItem]:
        if self._use_local_store:
            rows = local_store.list_portfolio_items(str(user_id))
            return [PortfolioItem(**item) for item in rows]
        try:
            response = self.client.from_('portfolio_items').select('*').eq('user_id', str(user_id)).execute()
            data = self._handle_response(response.data)
            return [PortfolioItem(**item) for item in data]
        except Exception as exc:
            raise PortfolioItemServiceError(f"Failed to retrieve portfolio items for user {user_id}: {exc}") from exc

    def get_portfolio_item(self, user_id: UUID, item_id: UUID) -> Optional[PortfolioItem]:
        if self._use_local_store:
            row = local_store.get_portfolio_item(str(user_id), str(item_id))
            return PortfolioItem(**row) if row else None
        try:
            response = self.client.from_('portfolio_items').select('*').eq('user_id', str(user_id)).eq('id', str(item_id)).execute()
            data = self._handle_response(response.data)
            if data:
                return PortfolioItem(**data[0])
            return None
        except Exception as exc:
            raise PortfolioItemServiceError(f"Failed to retrieve portfolio item {item_id} for user {user_id}: {exc}") from exc

    def create_portfolio_item(self, user_id: UUID, item: PortfolioItemCreate) -> PortfolioItem:
        if self._use_local_store:
            new_item_data = item.model_dump()
            row = local_store.upsert_portfolio_item(str(user_id), new_item_data)
            return PortfolioItem(**row)
        try:
            new_item_data = item.model_dump()
            new_item_data['user_id'] = str(user_id)
            response = self.client.from_('portfolio_items').insert(new_item_data).execute()
            data = self._handle_response(response.data)
            return PortfolioItem(**data[0])
        except Exception as exc:
            raise PortfolioItemServiceError(f"Failed to create portfolio item for user {user_id}: {exc}") from exc

    def update_portfolio_item(self, user_id: UUID, item_id: UUID, item: PortfolioItemUpdate) -> Optional[PortfolioItem]:
        if self._use_local_store:
            existing = local_store.get_portfolio_item(str(user_id), str(item_id))
            if existing is None:
                return None
            update_data = item.model_dump(exclude_unset=True)
            if not update_data:
                return PortfolioItem(**existing)
            row = local_store.upsert_portfolio_item(str(user_id), update_data, str(item_id))
            return PortfolioItem(**row)
        try:
            update_data = item.model_dump(exclude_unset=True)
            if not update_data:
                return self.get_portfolio_item(user_id, item_id) # No data to update, return current item

            response = self.client.from_('portfolio_items').update(update_data).eq('user_id', str(user_id)).eq('id', str(item_id)).execute()
            data = self._handle_response(response.data)
            if data:
                return PortfolioItem(**data[0])
            return None
        except Exception as exc:
            raise PortfolioItemServiceError(f"Failed to update portfolio item {item_id} for user {user_id}: {exc}") from exc

    def delete_portfolio_item(self, user_id: UUID, item_id: UUID) -> bool:
        if self._use_local_store:
            return local_store.delete_portfolio_item(str(user_id), str(item_id))
        try:
            response = self.client.from_('portfolio_items').delete().eq('user_id', str(user_id)).eq('id', str(item_id)).execute()
            data = self._handle_response(response.data)
            return bool(data)
        except Exception as exc:
            raise PortfolioItemServiceError(f"Failed to delete portfolio item {item_id} for user {user_id}: {exc}") from exc
